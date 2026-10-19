"""Google Cloud Batch backend.

One Batch job per run of a study; one Batch *task* per case
(BATCH_TASK_INDEX picks the case). Each task runs the solver image on Spot
VMs, works on local disk, and copies the finished case to the bucket (mounted
with Cloud Storage FUSE) at runs/<study>/<run id>/<case>/. The run id is the
UTC submit time; the job is named after it.

    iomcfd gcp submit foil2d/keel-sections [--machine c3d-standard-16] [--dry-run]
    iomcfd gcp status [JOB]
    iomcfd gcp fetch  foil2d/keel-sections [--run-id ID]   # latest run -> runs/<study>/<run id>/ + collect

`fetch` downloads only what the report and the findings need: each case's
results (params.json, result.json, surface.csv) and one mesh per mesh level
(for the report's mesh figure), a few MB per hundred cases. Everything else
stays in the bucket and is fetched on demand: `--logs` (solver logs of
failed and not-converged cases), `--fields` (whole cases, field data
included, of the study's highlights), `--only CASE...` (whole cases).

Configuration: cloud/gcp/config.env (copy config.env.example). One-time
infrastructure: cloud/gcp/setup.sh. Image: `make push`.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .. import config

MOUNT = "/mnt/disks/data"

def keep_pattern(full=(), mesh=(), logs=()) -> str:
    """Regex of the run-relative paths `fetch` downloads: the run's own files
    (study.yaml, run.json, report/, viz/), every case's results (LIGHT_FILES)
    and images, all of the `full` cases, mesh and checkMesh log of the
    `mesh` cases, logs of the `logs` cases."""
    from ..runner import LIGHT_FILES

    names = lambda cases: "|".join(re.escape(c) for c in cases)  # noqa: E731
    alts = [r"[^/]+", r"(?:report|viz)/.*", r"[^/]+/(?:%s)" % "|".join(map(re.escape, LIGHT_FILES)), r"[^/]+/viz/.*"]
    if full:
        alts.append(rf"(?:{names(full)})/.*")
    if mesh:
        alts.append(rf"(?:{names(mesh)})/(?:constant/polyMesh/.*|log\.checkMesh(?:\.gz)?)")
    if logs:
        alts.append(rf"(?:{names(logs)})/log\.[^/]*")
    return "|".join(alts)


def exclude_pattern(keep: str) -> str:
    """`gcloud storage rsync --exclude` regex for everything but `keep`.
    gcloud applies re.match to the path relative to the source. The flag is a
    gcloud list: a comma would split it and a leading '^' would be read as a
    custom delimiter, hence no '^' (re.match anchors anyway)."""
    if "," in keep:
        raise ValueError("gcloud would split the exclude pattern at a comma")
    return rf"(?!(?:{keep})$).*"

# vCPUs per physical core. CFD is memory-bandwidth bound: give each MPI rank
# a whole core, i.e. 2 vCPUs on SMT machine families.
_SMT_FAMILIES = ("c2-", "c2d-", "c3-", "c3d-", "c4-", "c4d-", "n2-", "n2d-", "n4-", "e2-", "n1-")


def vcpus_per_rank(machine: str) -> int:
    return 2 if machine.startswith(_SMT_FAMILIES) else 1


def machine_vcpus(machine: str) -> int:
    m = re.search(r"-(\d+)$", machine)
    if not m:
        raise SystemExit(f"cannot infer vCPU count from machine type '{machine}'")
    return int(m.group(1))


def load_config() -> dict[str, str]:
    path = config.home() / "cloud" / "gcp" / "config.env"
    if not path.is_file():
        raise SystemExit(f"{path} not found: copy config.env.example and fill it in")
    cfg = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0]  # inline comments
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("GCP_PROJECT", "GCP_REGION", "GCS_BUCKET", "AR_REPO", "BATCH_SA"):
        if not cfg.get(key):
            raise SystemExit(f"config.env: {key} is not set")
    cfg.setdefault("IMAGE_NAME", "iom-cfd")
    cfg.setdefault("IMAGE_TAG", "latest")
    cfg.setdefault("DEFAULT_MACHINE", "c3d-standard-16")
    return cfg


def image_uri(cfg: dict[str, str], tag: str | None = None) -> str:
    return (
        f"{cfg['GCP_REGION']}-docker.pkg.dev/{cfg['GCP_PROJECT']}/{cfg['AR_REPO']}/"
        f"{cfg['IMAGE_NAME']}:{tag or cfg['IMAGE_TAG']}"
    )


def _gcloud(*args: str, capture: bool = False, dry: bool = False) -> str:
    cmd = ["gcloud", *args]
    print("+ " + shlex.join(cmd), file=sys.stderr)
    if dry:
        return ""
    if not shutil.which("gcloud"):
        raise SystemExit("gcloud CLI not found (https://cloud.google.com/sdk/docs/install)")
    res = subprocess.run(cmd, check=True, text=True, capture_output=capture)
    return res.stdout if capture else ""


# VM states that hold quota (a TERMINATED, i.e. stopped, VM holds none).
_LIVE_STATES = {"PROVISIONING", "STAGING", "RUNNING", "STOPPING", "REPAIRING", "SUSPENDING"}
# Without the quota APIs (no permission, no gcloud beta): at most this many VMs.
FALLBACK_MAX_VMS = 8


def parallelism_from_quotas(n_tasks: int, per_node: int, constraints: list[tuple[str, float, float, int]]
                            ) -> tuple[int, str]:
    """Tasks a job may run at once so that its VMs fit the quotas' headroom.

    constraints: (name, limit, usage, amount one VM uses), e.g. ("instances",
    24, 8, 1) or ("C3D vCPUs", 150, 116, 16). Batch otherwise asks for every
    task's VM at once; over a quota its instance group fails to create VMs
    and the job stays queued for good (bulb-section, 2026-10-19: 39 VMs
    against 24 instances, then 12 c3d-16 against 150 C3D vCPUs with 116 in
    use). At least one VM: with no headroom now, the job waits in the queue.
    Returns (parallelism, explanation)."""
    vms = None
    notes = []
    for name, limit, usage, per_vm in constraints:
        room = int((limit - usage) // per_vm)
        notes.append(f"{name} {usage:g}/{limit:g} used: room for {max(room, 0)}")
        vms = room if vms is None else min(vms, room)
    vms = max(1, vms if vms is not None else FALLBACK_MAX_VMS)
    return min(n_tasks, vms * per_node), "; ".join(notes) or f"no quota data: at most {FALLBACK_MAX_VMS} VMs"


def quota_constraints(cfg: dict[str, str], machine: str) -> list[tuple[str, float, float, int]]:
    """The quotas a job of `machine` VMs in cfg's region runs into, with their
    current usage: instances in the region, the machine family's vCPUs in the
    region (older families from the region's quota list, e.g. C2D_CPUS; newer
    ones such as C3D, H3, C4 from the Cloud Quotas API, CPUS_PER_VM_FAMILY,
    with the usage summed over the live VMs), and vCPUs in all regions.
    Read-only gcloud calls; a quota that can't be read is left out."""
    region, project = cfg["GCP_REGION"], cfg["GCP_PROJECT"]
    vcpu = machine_vcpus(machine)
    family = machine.split("-")[0].upper()
    out: list[tuple[str, float, float, int]] = []
    reg = {q["metric"]: q for q in json.loads(_gcloud(
        "compute", "regions", "describe", region, "--project", project, "--format", "json", capture=True)
    ).get("quotas", [])}
    if "INSTANCES" in reg:
        out.append(("instances", reg["INSTANCES"]["limit"], reg["INSTANCES"]["usage"], 1))
    if f"{family}_CPUS" in reg:
        q = reg[f"{family}_CPUS"]
        out.append((f"{family} vCPUs", q["limit"], q["usage"], vcpu))
    else:
        try:
            info = json.loads(_gcloud("beta", "quotas", "info", "describe", "CPUS-PER-VM-FAMILY-per-project-region",
                                      "--service", "compute.googleapis.com", "--project", project,
                                      "--format", "json", capture=True))
        except (subprocess.CalledProcessError, ValueError):
            info = {}
        limit = next((float(d["details"]["value"]) for d in info.get("dimensionsInfos", [])
                      if d.get("dimensions") == {"region": region, "vm_family": family}
                      and "value" in d.get("details", {})), None)
        if limit is not None and limit >= 0:
            vms = json.loads(_gcloud("compute", "instances", "list", "--project", project, "--format",
                                     "json(zone.basename(),machineType.basename(),status)", capture=True))
            used = sum(machine_vcpus(v["machineType"]) for v in vms
                       if v["zone"].startswith(f"{region}-") and v["status"] in _LIVE_STATES
                       and v["machineType"].upper().startswith(f"{family}-"))
            out.append((f"{family} vCPUs", limit, used, vcpu))
    proj = {q["metric"]: q for q in json.loads(_gcloud(
        "compute", "project-info", "describe", "--project", project, "--format", "json", capture=True)
    ).get("quotas", [])}
    if "CPUS_ALL_REGIONS" in proj:
        out.append(("vCPUs, all regions", proj["CPUS_ALL_REGIONS"]["limit"], proj["CPUS_ALL_REGIONS"]["usage"], vcpu))
    return out


def build_job(
    cfg: dict[str, str],
    study_name: str,
    n_tasks: int,
    np_: int,
    machine: str,
    spot: bool,
    max_hours: float,
    parallelism: int | None,
    sets: list[str],
    tag: str | None,
    run_id: str,
) -> dict[str, Any]:
    vcpu = machine_vcpus(machine)
    task_vcpus = max(1, np_) * vcpus_per_rank(machine)
    if task_vcpus > vcpu:
        raise SystemExit(f"np={np_} needs {task_vcpus} vCPUs but {machine} has {vcpu}")
    per_node = max(1, vcpu // task_vcpus)
    mem_mib = int(1024 * {"c3d": 4, "c2d": 4, "c4d": 3.75, "h3": 4, "t2d": 4}.get(machine.split("-")[0], 3.5)
                  * task_vcpus * 0.9)
    shm_gb = max(1, min(64, mem_mib // 1024 // 2))
    study_file = f"{MOUNT}/runs/{study_name}/{run_id}/study.yaml"  # this run's own copy
    cmd = ["iomcfd", "--runs", "/tmp/iomcfd-runs", "run", study_file, "--run-id", run_id,
           "--index", "BATCH_TASK_INDEX", "--jobs", "1", "--np", str(np_), "--export", f"{MOUNT}/runs",
           "--checkpoint", f"{MOUNT}/checkpoints"]
    for s in sets:
        cmd += ["--set", s]
    job = {
        "taskGroups": [
            {
                "taskCount": n_tasks,
                "taskCountPerNode": per_node,
                **({"parallelism": parallelism} if parallelism else {}),
                "taskSpec": {
                    "computeResource": {"cpuMilli": task_vcpus * 1000, "memoryMib": mem_mib},
                    "maxRunDuration": f"{int(max_hours * 3600)}s",
                    "maxRetryCount": 6,
                    # Batch allows a single lifecycle policy. Don't retry: iomcfd's exit
                    # 1 (failed case, error) or 2 (usage), nor 50005 (over maxRunDuration:
                    # a case without checkpoints would start from scratch and hit the
                    # limit again). Everything else, notably 50001 (Spot VM preempted), is
                    # retried up to maxRetryCount; a case with checkpoints resumes from
                    # its last one (checkpoint.py).
                    "lifecyclePolicies": [
                        {"action": "FAIL_TASK", "actionCondition": {"exitCodes": [1, 2, 50005]}},
                    ],
                    "environment": {
                        "variables": {
                            "IOMCFD_GEOMETRY": f"{MOUNT}/geometry",
                            "IOMCFD_SOURCE_RUNS": f"{MOUNT}/runs",  # earlier runs, for start_from
                            "IOMCFD_IMAGE_REF": image_uri(cfg, tag),
                        }
                    },
                    "volumes": [{"gcs": {"remotePath": cfg["GCS_BUCKET"]}, "mountPath": MOUNT}],
                    "runnables": [
                        {
                            "container": {
                                "imageUri": image_uri(cfg, tag),
                                "commands": cmd,
                                "options": f"--shm-size={shm_gb}g",
                            }
                        }
                    ],
                },
            }
        ],
        "allocationPolicy": {
            "location": {"allowedLocations": [f"regions/{cfg['GCP_REGION']}"]},
            "serviceAccount": {"email": cfg["BATCH_SA"]},
            # No external IPs: the IN_USE_ADDRESSES quota (8) would cap the job at
            # 8 VMs. The VMs only talk to Google APIs (Artifact Registry, GCS,
            # Logging, Batch), via Private Google Access on the subnet (setup.sh).
            "network": {
                "networkInterfaces": [
                    {
                        "network": "global/networks/default",
                        "subnetwork": f"regions/{cfg['GCP_REGION']}/subnetworks/default",
                        "noExternalIpAddress": True,
                    }
                ]
            },
            "instances": [
                {
                    "policy": {
                        "machineType": machine,
                        "provisioningModel": "SPOT" if spot else "STANDARD",
                        "bootDisk": {"sizeGb": "50"},
                    }
                }
            ],
        },
        "labels": {"app": "iomcfd", "study": re.sub(r"[^a-z0-9_-]", "-", study_name.lower())[:63], "run": run_id},
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
    }
    return job


def task_hours(project, cases: list, np_: int) -> float:
    """Per-task time limit: one for all tasks of a job, so the longest
    case's (a study can mix mesh levels and sections of very different size)."""
    return max(float(project.resources({**c.params, "np": np_}).get("max_hours", 4)) for c in cases)


def job_name(study_name: str, run_id: str) -> str:
    base = re.sub(r"[^a-z0-9-]", "-", study_name.lower()).strip("-")[:39]
    return f"iomcfd-{base}-{run_id}"  # Batch: at most 63 characters


# ---------------------------------------------------------------------------
# commands


def cmd_submit(args) -> None:
    from ..cli import _load, parse_sets  # noqa: F401  (shared study loading)
    from ..runner import new_run_id, write_run_info

    cfg = load_config()
    study, project, cases = _load(args)
    machine = args.machine or cfg["DEFAULT_MACHINE"]
    np_ = args.np or int(cases[0].params.get("np", 1))
    max_hours = args.max_hours or task_hours(project, cases, np_)
    run_id = new_run_id()
    parallelism = args.parallelism
    if not parallelism:  # fit the job to the quotas' headroom (parallelism_from_quotas)
        per_node = max(1, machine_vcpus(machine) // (max(1, np_) * vcpus_per_rank(machine)))
        try:
            constraints = quota_constraints(cfg, machine)
        except (subprocess.CalledProcessError, ValueError, KeyError, SystemExit) as e:
            print(f"quotas not readable ({e}): at most {FALLBACK_MAX_VMS} VMs", file=sys.stderr)
            constraints = []
        parallelism, why = parallelism_from_quotas(len(cases), per_node, constraints)
        print(f"parallelism {parallelism} ({-(-parallelism // per_node)} VMs at once; --parallelism to set it): {why}")
    job = build_job(cfg, study.name, len(cases), np_, machine, not args.standard, max_hours,
                    parallelism, args.set or [], args.tag, run_id)
    name = job_name(study.name, run_id)
    out = config.home() / "cloud" / "gcp" / "jobs" / name
    out.mkdir(parents=True, exist_ok=True)
    job_file = out / "job.json"
    job_file.write_text(json.dumps(job, indent=2) + "\n")
    run_info = write_run_info(out, study, len(cases), run_id=run_id, backend="gcp", job=name, machine=machine,
                              image=image_uri(cfg, args.tag))
    print(f"run {run_id}: {len(cases)} tasks, {machine} ({'spot' if not args.standard else 'standard'}), "
          f"{job['taskGroups'][0]['taskCountPerNode']} tasks/VM, job spec: {job_file}")

    bucket = f"gs://{cfg['GCS_BUCKET']}"
    dst = f"{bucket}/runs/{study.name}/{run_id}"
    _gcloud("storage", "cp", str(study.path), f"{dst}/study.yaml", dry=args.dry_run)
    _gcloud("storage", "cp", str(run_info), f"{dst}/run.json", dry=args.dry_run)
    _gcloud("storage", "rsync", "-r", str(config.geometry_dir()), f"{bucket}/geometry", dry=args.dry_run)
    _gcloud("batch", "jobs", "submit", name, "--project", cfg["GCP_PROJECT"], "--location", cfg["GCP_REGION"],
            "--config", str(job_file), dry=args.dry_run)
    if not args.dry_run:
        print(f"\nsubmitted {name}\n  iomcfd gcp status {name}\n  iomcfd gcp fetch {args.study} --run-id {run_id}")


def cmd_status(args) -> None:
    cfg = load_config()
    if args.job:
        out = _gcloud("batch", "jobs", "describe", args.job, "--project", cfg["GCP_PROJECT"],
                      "--location", cfg["GCP_REGION"], "--format", "json", capture=True)
        info = json.loads(out)
        st = info.get("status", {})
        print(f"{args.job}: {st.get('state')}  run time {st.get('runDuration', '-')}")
        for grp in (st.get("taskGroups") or {}).values():
            print("  tasks:", ", ".join(f"{k}={v}" for k, v in (grp.get("counts") or {}).items()))
        print(f"\nprogress: iomcfd gcp progress <study> --run-id {info.get('labels', {}).get('run', '<run id>')}")
        print(f"logs: gcloud logging read 'labels.job_uid=\"{info.get('uid')}\"' --project {cfg['GCP_PROJECT']} --limit 50")
    else:
        _gcloud("batch", "jobs", "list", "--project", cfg["GCP_PROJECT"], "--location", cfg["GCP_REGION"],
                "--filter", "labels.app=iomcfd", "--sort-by", "~createTime", "--limit", "20")


def _task_index(task_id: str) -> int:
    try:
        return int(task_id.rsplit("-", 1)[-1])
    except ValueError:
        return -1


def cmd_progress(args) -> None:
    """The newest log lines of each task of a study's job, from Cloud Logging:
    the runner's progress lines (every 10 min: time, %, ETA, deltaT, Courant,
    forces and their drift), divergence stops and results (runner.py,
    monitor.py)."""
    from ..cli import resolve_study_path
    from ..study import Study

    cfg = load_config()
    study = Study.load(resolve_study_path(args.study))
    where = ["--project", cfg["GCP_PROJECT"], "--location", cfg["GCP_REGION"]]
    if args.run_id:
        name = job_name(study.name, args.run_id)
    else:
        label = re.sub(r"[^a-z0-9_-]", "-", study.name.lower())[:63]
        # newest by run id (the name's suffix); gcloud's --limit with a filter dropped jobs
        names = _gcloud("batch", "jobs", "list", *where, "--filter", f"labels.study={label}",
                        "--format", "value(name)", capture=True).split()
        if not names:
            raise SystemExit(f"no Batch jobs of {study.name}")
        name = max(n.rsplit("/", 1)[-1] for n in names)
    info = json.loads(_gcloud("batch", "jobs", "describe", name, *where, "--format", "json", capture=True))
    st = info.get("status", {})
    counts: dict[str, int] = {}
    for grp in (st.get("taskGroups") or {}).values():
        for k, v in (grp.get("counts") or {}).items():
            counts[k] = counts.get(k, 0) + int(v)
    dur = st.get("runDuration", "")
    hours = f"{float(dur[:-1]) / 3600:.1f} h" if dur.endswith("s") and dur[:-1].replace(".", "", 1).isdigit() else "-"
    print(f"{name}: {st.get('state')}, run time {hours}; tasks: "
          + (", ".join(f"{k.lower()} {v}" for k, v in sorted(counts.items())) or "-"))
    flt = f'logName="projects/{cfg["GCP_PROJECT"]}/logs/batch_task_logs" AND labels.job_uid="{info.get("uid")}"'
    out = _gcloud("logging", "read", flt, "--project", cfg["GCP_PROJECT"], "--freshness", "30d",
                  "--limit", "2000", "--format", "json", capture=True)
    lines: dict[str, list[tuple[str, str]]] = {}
    for e in json.loads(out or "[]"):  # newest first
        text = (e.get("textPayload") or "").rstrip()
        if text.strip():
            lines.setdefault(e.get("labels", {}).get("task_id", "?"), []).append((e.get("timestamp", "")[:19], text))
    if not lines:
        print("no task log lines yet")
    for task in sorted(lines, key=_task_index):
        print(f"\ntask {_task_index(task)}")
        for ts, text in reversed(lines[task][: args.lines]):
            print(f"  {ts}Z {text.strip()}")


def cmd_fetch(args) -> None:
    import argparse

    from ..cli import _load_run, _runs, _select, resolve_study_path
    from ..highlights import case_names, plan
    from ..meshplot import has_mesh, mesh_candidates
    from ..results import collect
    from ..runner import is_run_id
    from ..study import Study

    cfg = load_config()
    study = Study.load(resolve_study_path(args.study))
    base = f"gs://{cfg['GCS_BUCKET']}/runs/{study.name}"
    run_id = args.run_id
    if run_id in (None, "latest"):
        try:
            listing = _gcloud("storage", "ls", f"{base}/", capture=True)
        except subprocess.CalledProcessError:  # no such prefix
            listing = ""
        ids = sorted(n for n in (ln.rstrip("/").rsplit("/", 1)[-1] for ln in listing.split()) if is_run_id(n))
        if not ids:
            raise SystemExit(f"no runs of {study.name} in {base}/")
        run_id = ids[-1]
    elif not is_run_id(run_id):
        raise SystemExit(f"--run-id {run_id}: expected YYYYMMDD-HHMMSS")
    dst = _runs(args) / study.name / run_id
    dst.mkdir(parents=True, exist_ok=True)
    src = f"{base}/{run_id}"

    def rsync(keep: str) -> None:
        _gcloud("storage", "rsync", "-r", "--exclude", exclude_pattern(keep), src, str(dst))

    rsync(keep_pattern())  # results of every case
    rows, out = collect(dst)
    run_args = argparse.Namespace(study=args.study, runs=args.runs, run_id=run_id, only=args.only, index=None)
    st, _, cases, _ = _load_run(run_args)
    have = {r["case"] for r in rows}
    full: list[str] = []
    if args.only:
        full = [c.name for c in _select(cases, run_args)]
    elif args.fields:
        planned = plan(st.highlights, cases)
        full = case_names(planned) if planned else [c.name for c in cases]
        print(f"fields of {len(full)} cases" + (f" (highlights from {st.highlights_from})" if planned else
                                               " (all: the study has no highlights)"), file=sys.stderr)
    full = [c for c in full if c in have]
    mesh = [names[0] for names in mesh_candidates(rows) if names and not has_mesh(dst / names[0])]
    logs = [r["case"] for r in rows if r["status"] in ("failed", "not_converged")] if args.logs else []
    if full or mesh or logs:
        rsync(keep_pattern(full, mesh, logs))
    size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    print(f"{out}: {len(rows)} cases (run {run_id}); {len(full)} whole cases, mesh of {', '.join(mesh) or '-'}, "
          f"logs of {len(logs)}; {size / 1e6:.0f} MB on disk")


def add_parser(sub) -> None:
    p = sub.add_parser("gcp", help="run studies on Google Cloud Batch")
    gsub = p.add_subparsers(dest="gcp_cmd", required=True)

    s = gsub.add_parser("submit", help="submit a study as a Batch job (one task per case)")
    s.add_argument("study")
    s.add_argument("--set", action="append", metavar="KEY=VALUE")
    s.add_argument("--machine", help="Compute Engine machine type (default: DEFAULT_MACHINE in config.env)")
    s.add_argument("--np", type=int, help="MPI ranks per case")
    s.add_argument("--standard", action="store_true", help="on-demand VMs instead of Spot")
    s.add_argument("--parallelism", type=int, help="max tasks running at once (default: what the quotas allow now: instances, the machine family vCPUs, all vCPUs)")
    s.add_argument("--max-hours", type=float, help="per-task time limit")
    s.add_argument("--tag", help="image tag (default: IMAGE_TAG in config.env)")
    s.add_argument("--dry-run", action="store_true", help="write the job JSON, don't submit")
    s.set_defaults(func=cmd_submit, only=None, index=None)

    s = gsub.add_parser("status", help="list jobs, or show one")
    s.add_argument("job", nargs="?")
    s.set_defaults(func=cmd_status)

    s = gsub.add_parser("progress", help="newest log lines of each task of a study's job: progress (time, %%, ETA, "
                        "Courant, forces, drift), divergence stops, results")
    s.add_argument("study")
    s.add_argument("--run-id", metavar="ID", help="which run (default: the study's newest job)")
    s.add_argument("--lines", type=int, default=3, help="lines per task (default 3)")
    s.set_defaults(func=cmd_progress)

    s = gsub.add_parser("fetch", help="download a run's results (not meshes, logs, fields) and collect them")
    s.add_argument("study")
    s.add_argument("--run-id", metavar="ID", help="which run (default: the latest in the bucket)")
    s.add_argument("--logs", action="store_true", help="also the solver logs of failed and not-converged cases")
    s.add_argument("--fields", action="store_true", help="also whole cases with field data, for `iomcfd viz`: "
                   "the study's highlights (all cases if it has none)")
    s.add_argument("--only", nargs="+", metavar="CASE", help="also these whole cases (names or indices)")
    s.set_defaults(func=cmd_fetch)
