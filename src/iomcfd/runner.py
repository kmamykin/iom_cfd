"""Render and execute cases (inside the OpenFOAM container).

Every `iomcfd run` writes a new, timestamped run of the study, so a later
run never overwrites an earlier one:

    runs/<study>/<run id>/              run id = UTC start time, YYYYMMDD-HHMMSS
        study.yaml                      the study file as it was run
        run.json                        when, which code (git) and image, overrides
        <case>/                         one OpenFOAM case per parameter set
        results.csv  report/  viz/      post-processing (re-runnable)

`--resume` (or `--run-id ID`) continues an existing run instead: finished
cases are skipped, failed ones run again.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import re
import shutil
import socket
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config
from .foam import tail_log
from .project import Project
from .study import Case, Study

RESULT = "result.json"

# Per-case files that carry a case's results: enough for collect, report
# (except the mesh figure) and the findings. `gcp fetch` downloads only these
# by default, and `iomcfd slim` keeps only these (plus viz/ images).
LIGHT_FILES = ("params.json", RESULT, "surface.csv", "force_history.csv")  # the last: transient cases


@dataclass
class RunOptions:
    jobs: int = 1  # cases in parallel
    np: int | None = None  # MPI ranks per case (None: from params)
    force: bool = False  # re-run cases that already finished
    render_only: bool = False
    export: Path | None = None  # copy finished cases here (e.g. a GCS mount)
    keep_fields: bool = True  # keep the final time directory when exporting
    compress: bool = True  # gzip mesh and logs when exporting
    poll_seconds: float = 15.0  # convergence-monitor interval


RUN_ID_FORMAT = "%Y%m%d-%H%M%S"
_RUN_ID = re.compile(r"\d{8}-\d{6}")


def study_dir(study: Study, runs: Path | None = None) -> Path:
    """All runs of a study: runs/<study>/."""
    return (runs or config.runs_dir()) / study.name


def new_run_id(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now(dt.timezone.utc)).strftime(RUN_ID_FORMAT)


def is_run_id(name: str) -> bool:
    return bool(_RUN_ID.fullmatch(name))


def list_runs(sdir: Path) -> list[str]:
    """Run ids of a study, oldest first."""
    if not Path(sdir).is_dir():
        return []
    return sorted(p.name for p in Path(sdir).iterdir() if p.is_dir() and is_run_id(p.name))


def resolve_run(study: Study, runs: Path | None = None, run_id: str | None = None) -> Path:
    """An existing run of the study: `run_id`, or the latest one (None or 'latest')."""
    sdir = study_dir(study, runs)
    ids = list_runs(sdir)
    if run_id in (None, "latest"):
        if not ids:
            raise SystemExit(f"no runs of {study.name} in {sdir}")
        run_id = ids[-1]
    if run_id not in ids:
        raise SystemExit(f"run {run_id} of {study.name} not found in {sdir} (runs: {', '.join(ids) or 'none'})")
    return sdir / run_id


def write_run_info(rdir: Path, study: Study, n_cases: int, **extra: Any) -> Path:
    """run.json: what was run, when, with which code. Written once per run;
    `extra` adds or overrides fields (backend, job, ...)."""
    f = Path(rdir) / "run.json"
    if not f.is_file():
        info = {
            "run_id": Path(rdir).name,
            "study": study.name,
            "project": study.project,
            "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git": config.git_describe(),
            "image": os.environ.get("IOMCFD_IMAGE_REF", ""),
            "backend": "local",
            "cases": n_cases,
            "overrides": study.overrides,
            **extra,
        }
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(info, indent=2, default=str) + "\n")
    return f


def read_result(case_dir: Path) -> dict[str, Any] | None:
    f = Path(case_dir) / RESULT
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return None


def is_done(case_dir: Path, case: Case) -> bool:
    r = read_result(case_dir)
    return bool(r and r.get("status") in ("ok", "not_converged") and r.get("params_hash") == case.params_hash)


def run_case(project: Project, case: Case, case_dir: Path, opts: RunOptions,
             export_dir: Path | None = None) -> dict[str, Any]:
    """Render (if needed) and run one case. Never raises; returns the result."""
    t0 = time.time()
    result: dict[str, Any] = {
        "case": case.name,
        "index": case.index,
        "params_hash": case.params_hash,
        "host": socket.gethostname(),
        "image": os.environ.get("IOMCFD_IMAGE_REF", ""),
    }
    try:
        if opts.np:
            case.params["np"] = opts.np
        derived = project.prepare_case(case_dir, case.params)
        if opts.render_only:
            return {"case": case.name, "status": "rendered"}
        env = dict(os.environ, NP=str(case.params.get("np", 1)))
        with open(case_dir / "log.Allrun", "w") as log:
            proc = subprocess.Popen(["./Allrun"], cwd=case_dir, stdout=log, stderr=subprocess.STDOUT, env=env)
            stop_requested = False
            while proc.poll() is None:
                time.sleep(opts.poll_seconds)
                if not stop_requested and _safe_converged(project, case_dir, case.params, derived):
                    request_stop(case_dir)
                    stop_requested = True
            result["stopped_on_convergence"] = stop_requested
        result["returncode"] = proc.returncode
        metrics = project.extract(case_dir, case.params, derived)
        result["metrics"] = metrics
        if proc.returncode != 0:
            result["status"] = "failed"
            result["error"] = _last_error(case_dir)
        else:
            result["status"] = metrics.pop("_status", "ok")
    except Exception as exc:  # noqa: BLE001 - one bad case must not stop a sweep
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    result["wall_time_s"] = round(time.time() - t0, 1)
    if case_dir.exists():
        (case_dir / RESULT).write_text(json.dumps(result, indent=2, default=str) + "\n")
    if export_dir and result.get("status") != "rendered":
        export_case(case_dir, Path(export_dir) / case_dir.name, opts.keep_fields, opts.compress)
    return result


def _safe_converged(project: Project, case_dir: Path, params, derived) -> bool:
    try:
        return bool(project.converged(case_dir, params, derived))
    except Exception:  # noqa: BLE001 - files may be mid-write
        return False


def request_stop(case_dir: Path) -> None:
    """Ask a running solver to write and stop (needs runTimeModifiable true)."""
    from .foam import set_entry

    set_entry(case_dir / "system" / "controlDict", "stopAt", "writeNow")


def _last_error(case_dir: Path) -> str:
    logs = sorted(case_dir.glob("log.*"), key=lambda p: p.stat().st_mtime)
    for log in reversed(logs):
        if log.name == "log.Allrun":
            continue
        txt = tail_log(log, 40)
        if "FOAM FATAL" in txt or "error" in txt.lower():
            return f"{log.name}:\n{txt}"
    return tail_log(case_dir / "log.Allrun", 20)


def _gzipped(rel: Path) -> bool:
    """Exported files stored gzipped: the mesh (about 3.5x smaller) and the
    logs (about 10x). OpenFOAM, ParaView and iomcfd read both forms. Binary
    fields gain little (1.2x) and stay as they are."""
    return rel.suffix != ".gz" and (rel.parts[:2] == ("constant", "polyMesh")
                                    or (len(rel.parts) == 1 and rel.name.startswith("log.")))


def export_case(src: Path, dst: Path, keep_fields: bool, compress: bool = True) -> None:
    """Copy a finished case without processor dirs / intermediate times;
    with `compress`, mesh and logs are written gzipped (see _gzipped)."""
    times = []
    for d in src.iterdir():
        try:
            times.append((float(d.name), d.name))
        except ValueError:
            pass
    latest = max(times)[1] if times else None

    def ignore(dirpath: str, names: list[str]) -> set[str]:
        if Path(dirpath) != src:
            return set()
        skip = {n for n in names if n.startswith("processor")}
        for _, name in times:
            if name != "0" and (not keep_fields or name != latest):
                skip.add(name)
        return skip

    def copy(s: str, d: str) -> None:
        if compress and _gzipped(Path(s).relative_to(src)):
            with open(s, "rb") as fi, gzip.open(d + ".gz", "wb", compresslevel=6) as fo:
                shutil.copyfileobj(fi, fo)
        else:
            shutil.copy2(s, d)

    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=ignore, symlinks=True, copy_function=copy)


def slim_run(rdir: Path, keep_mesh: set[str] = frozenset(), dry_run: bool = False) -> tuple[int, int]:
    """Delete a local run's bulk data: in every case all but LIGHT_FILES and
    viz/ (images); the mesh and log.checkMesh of the `keep_mesh` cases stay
    for the report's mesh figure. Run-level files (results.csv, report/, viz/)
    are kept. Returns (files, bytes) deleted, or that would be."""
    n = size = 0
    for case in sorted(p for p in Path(rdir).iterdir() if (p / "params.json").is_file()):
        for f in sorted(case.rglob("*")):
            if not (f.is_file() or f.is_symlink()):
                continue
            rel = f.relative_to(case)
            if rel.parts[0] == "viz" or (len(rel.parts) == 1 and rel.name in LIGHT_FILES):
                continue
            if case.name in keep_mesh and (rel.parts[:2] == ("constant", "polyMesh")
                                           or rel.name in ("log.checkMesh", "log.checkMesh.gz")):
                continue
            n += 1
            size += f.lstat().st_size
            if not dry_run:
                f.unlink()
        if not dry_run:  # empty directories left behind, deepest first
            for d in sorted((d for d in case.rglob("*") if d.is_dir()), key=lambda d: -len(d.parts)):
                if not any(d.iterdir()):
                    d.rmdir()
    return n, size


def run_study(
    project: Project,
    study: Study,
    cases: list[Case],
    opts: RunOptions,
    rdir: Path,
    log=print,
) -> list[dict[str, Any]]:
    """Run `cases` into the run directory `rdir` (runs/<study>/<run id>/).
    Cases already finished there are skipped unless opts.force."""
    rdir = Path(rdir)
    rdir.mkdir(parents=True, exist_ok=True)
    if study.path and not (rdir / "study.yaml").is_file():  # keep the file the run started with
        shutil.copy2(study.path, rdir / "study.yaml")
    write_run_info(rdir, study, len(cases))
    export_dir = Path(opts.export) / study.name / rdir.name if opts.export else None

    todo = []
    for c in cases:
        cdir = rdir / c.name
        if not opts.force and not opts.render_only and is_done(cdir, c):
            log(f"  skip  {c.name} (done)")
            continue
        todo.append((c, cdir))
    log(f"study {study.name}, run {rdir.name}: {len(cases)} cases, {len(todo)} to run, {opts.jobs} in parallel")

    results = []
    with ThreadPoolExecutor(max_workers=max(1, opts.jobs)) as pool:
        futs = {pool.submit(run_case, project, c, d, opts, export_dir): c for c, d in todo}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            m = r.get("metrics") or {}
            summary = " ".join(f"{k}={v:.4g}" for k, v in m.items() if isinstance(v, float) and k in project_summary_keys(project))
            log(f"  {r['status']:<13} {r['case']}  {r.get('wall_time_s', 0):>7}s  {summary}")
            if r["status"] == "failed":
                log("    " + str(r.get("error", "")).replace("\n", "\n    ")[:2000])
    return results


def project_summary_keys(project: Project) -> set[str]:
    return set(getattr(project, "summary_keys", []))
