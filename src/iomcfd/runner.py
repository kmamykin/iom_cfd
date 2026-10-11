"""Render and execute cases (inside the OpenFOAM container)."""

from __future__ import annotations

import json
import os
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


@dataclass
class RunOptions:
    jobs: int = 1  # cases in parallel
    np: int | None = None  # MPI ranks per case (None: from params)
    force: bool = False  # re-run cases that already finished
    render_only: bool = False
    export: Path | None = None  # copy finished cases here (e.g. a GCS mount)
    keep_fields: bool = True  # keep the final time directory when exporting
    poll_seconds: float = 15.0  # convergence-monitor interval


def study_dir(study: Study, runs: Path | None = None) -> Path:
    return (runs or config.runs_dir()) / study.name


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


def run_case(project: Project, case: Case, case_dir: Path, opts: RunOptions) -> dict[str, Any]:
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
    if opts.export and result.get("status") != "rendered":
        export_case(case_dir, Path(opts.export) / case_dir.parent.name / case_dir.name, opts.keep_fields)
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


def export_case(src: Path, dst: Path, keep_fields: bool) -> None:
    """Copy a finished case without processor dirs / intermediate times."""
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

    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=ignore, symlinks=True)


def run_study(
    project: Project,
    study: Study,
    cases: list[Case],
    opts: RunOptions,
    runs: Path | None = None,
    log=print,
) -> list[dict[str, Any]]:
    sdir = study_dir(study, runs)
    sdir.mkdir(parents=True, exist_ok=True)
    if study.path:
        shutil.copy2(study.path, sdir / "study.yaml")

    todo = []
    for c in cases:
        cdir = sdir / c.name
        if not opts.force and not opts.render_only and is_done(cdir, c):
            log(f"  skip  {c.name} (done)")
            continue
        todo.append((c, cdir))
    log(f"study {study.name}: {len(cases)} cases, {len(todo)} to run, {opts.jobs} in parallel")

    results = []
    with ThreadPoolExecutor(max_workers=max(1, opts.jobs)) as pool:
        futs = {pool.submit(run_case, project, c, d, opts): c for c, d in todo}
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
