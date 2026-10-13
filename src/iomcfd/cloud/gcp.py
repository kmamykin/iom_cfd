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
           "--index", "BATCH_TASK_INDEX", "--jobs", "1", "--np", str(np_), "--export", f"{MOUNT}/runs"]
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
                    "maxRetryCount": 3,
                    # Batch allows a single lifecycle policy. iomcfd exits 1 (failed case,
                    # error) or 2 (usage): don't retry those. Everything else, notably
                    # 50001 (Spot VM preempted), is retried up to maxRetryCount.
                    "lifecyclePolicies": [
                        {"action": "FAIL_TASK", "actionCondition": {"exitCodes": [1, 2]}},
                    ],
                    "environment": {
                        "variables": {
                            "IOMCFD_GEOMETRY": f"{MOUNT}/geometry",
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
    job = build_job(cfg, study.name, len(cases), np_, machine, not args.standard, max_hours,
                    args.parallelism, args.set or [], args.tag, run_id)
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
        print(f"\nlogs: gcloud logging read 'labels.job_uid=\"{info.get('uid')}\"' --project {cfg['GCP_PROJECT']} --limit 50")
    else:
        _gcloud("batch", "jobs", "list", "--project", cfg["GCP_PROJECT"], "--location", cfg["GCP_REGION"],
                "--filter", "labels.app=iomcfd", "--sort-by", "~createTime", "--limit", "20")


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
    s.add_argument("--parallelism", type=int, help="max tasks running at once")
    s.add_argument("--max-hours", type=float, help="per-task time limit")
    s.add_argument("--tag", help="image tag (default: IMAGE_TAG in config.env)")
    s.add_argument("--dry-run", action="store_true", help="write the job JSON, don't submit")
    s.set_defaults(func=cmd_submit, only=None, index=None)

    s = gsub.add_parser("status", help="list jobs, or show one")
    s.add_argument("job", nargs="?")
    s.set_defaults(func=cmd_status)

    s = gsub.add_parser("fetch", help="download a run's results (not meshes, logs, fields) and collect them")
    s.add_argument("study")
    s.add_argument("--run-id", metavar="ID", help="which run (default: the latest in the bucket)")
    s.add_argument("--logs", action="store_true", help="also the solver logs of failed and not-converged cases")
    s.add_argument("--fields", action="store_true", help="also whole cases with field data, for `iomcfd viz`: "
                   "the study's highlights (all cases if it has none)")
    s.add_argument("--only", nargs="+", metavar="CASE", help="also these whole cases (names or indices)")
    s.set_defaults(func=cmd_fetch)
