"""Checkpoints: resume a long case after its machine is lost.

A Spot VM can be preempted at any time, and Cloud Batch then runs the task
again on a new VM, from scratch: a 20 h time-accurate case preempted every
11-24 h never finishes, and transient-check run 20261018-231921 lost two
attempts (about 45 VM-hours) that way. With a checkpoint directory (cloud
jobs: the bucket), the runner copies the newest completely written time
directory of a running case there, with postProcessing/ (the force history)
and, once, the mesh. When the task runs again, run_case renders the case as
usual, restores the checkpoint, sets IOMCFD_RESUME, and the template's
Allrun goes straight to the solver, which continues from latestTime.

Every case is checkpointed (Project.checkpoint_setup):
* "signal" (the default): the runner sends the solver SIGUSR1 every
  `interval`; with `writeNowSignal 10` in system/controlDict (added by
  enable_signal_writes) OpenFOAM writes its fields at the end of that time
  step and carries on. The templates' purgeWrite removes the older writes.
* True: the project makes the solver write periodically itself (foil2d's
  time-accurate cases, every flow-through).

Decomposed cases (np > 1) are saved per processor: processor*/<time> and,
once, processor*/constant/polyMesh. A serial case saves constant/polyMesh.
Saving the mesh lets a resumed 3D case skip snappyHexMesh, whose output
need not match the fields bit for bit if it ran again.

Two slots alternate for the fields and the manifest is written last, so a
preemption during a copy leaves the previous checkpoint usable. A
checkpoint is only restored into a case with the same params_hash and the
same number of processors. It is deleted when its case finishes ok (or not
converged); a failed case keeps it.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

MANIFEST = "checkpoint.json"
MESH = "mesh"
SIGNAL = 10  # SIGUSR1 on Linux (x86-64 and arm64)
SIGNAL_SWITCH = (
    "\nOptimisationSwitches\n{\n"
    f"    writeNowSignal  {SIGNAL};    // SIGUSR1: write now and carry on (iomcfd checkpoints)\n"
    "}\n"
)


def enable_signal_writes(case_dir: Path) -> None:
    """Let the solver write its fields on SIGUSR1 and continue: every
    system/controlDict* (foil2d and bulb2d keep a .steady / .transient one)."""
    for f in sorted((Path(case_dir) / "system").glob("controlDict*")):
        text = f.read_text()
        if "writeNowSignal" not in text:
            f.write_text(text + SIGNAL_SWITCH)


def processor_dirs(case_dir: Path) -> list[Path]:
    """processor0, processor1, ... in order (empty for a serial case)."""
    procs = [p for p in Path(case_dir).glob("processor*") if re.fullmatch(r"processor\d+", p.name) and p.is_dir()]
    return sorted(procs, key=lambda p: int(p.name[9:]))


def _roots(case_dir: Path) -> list[Path]:
    """Where the time directories are: the processor directories of a
    decomposed case, else the case itself."""
    return processor_dirs(case_dir) or [Path(case_dir)]


def time_dirs(case_dir: Path) -> list[tuple[float, str]]:
    """Time directories after 0, sorted by time: (value, name)."""
    out = []
    for d in Path(case_dir).iterdir():
        try:
            v = float(d.name)
        except ValueError:
            continue
        if v > 0 and d.is_dir():
            out.append((v, d.name))
    return sorted(out)


def _newest_mtime(d: Path) -> float:
    return max((p.stat().st_mtime for p in d.rglob("*") if p.is_file()), default=d.stat().st_mtime)


def _copy_whole_lines(src: str, dst: str) -> None:
    """Copy a file that may be mid-append (a solver's postProcessing output):
    text up to its last complete line."""
    data = Path(src).read_bytes()
    cut = data.rfind(b"\n")
    Path(dst).write_bytes(data[: cut + 1] if cut >= 0 else b"")
    shutil.copystat(src, dst)


def _application(case_dir: Path) -> str | None:
    """The solver system/controlDict names."""
    try:
        text = (Path(case_dir) / "system" / "controlDict").read_text(errors="replace")
        return re.search(r"^\s*application\s+(\w+)\s*;", text, re.M).group(1)
    except (OSError, AttributeError):
        return None


def _done_logs(case_dir: Path) -> list[Path]:
    """The logs of the steps before the solver (meshing, checkMesh, a
    steady start): log.* except log.Allrun and the running solver's."""
    skip = {"log.Allrun", f"log.{_application(case_dir)}"}
    return sorted(p for p in Path(case_dir).glob("log.*") if p.is_file() and p.name not in skip)


def _replace_tree(src: Path, dst: Path) -> None:
    shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


class Checkpoint:
    """The checkpoint of one case, in `root` (<checkpoints>/<study>/<run id>/<case>)."""

    def __init__(self, root: Path, interval: float = 900.0, settle: float = 60.0,
                 clock: Callable[[], float] = time.time):
        self.root = Path(root)
        self.interval = interval  # seconds between saves
        self.settle = settle  # a time directory untouched this long is completely written
        self.clock = clock
        self._last_try = -math.inf
        self.saved: str | None = None  # the time saved (or restored) last
        self.saved_app: str | None = None  # and the solver that wrote it

    def manifest(self) -> dict[str, Any] | None:
        try:
            return json.loads((self.root / MANIFEST).read_text())
        except (OSError, ValueError):
            return None

    def restore(self, case_dir: Path, params_hash: str, np: int = 1) -> str | None:
        """Copy the checkpoint into a freshly rendered case: the mesh, the
        time directory (per processor if it was decomposed) and
        postProcessing/. Returns the time restored, or None if there is no
        checkpoint for these parameters and `np` MPI ranks."""
        case_dir = Path(case_dir)
        m = self.manifest()
        if not m or m.get("params_hash") != params_hash:
            return None
        slot, t, roots = self.root / m["slot"], m["time"], m.get("roots") or ["."]
        if roots != (["."] if np <= 1 else [f"processor{i}" for i in range(np)]):
            return None
        if not all((slot / r / t).is_dir() for r in roots):
            return None
        if m.get("mesh"):
            for r in roots:
                src = self.root / MESH / r / "constant" / "polyMesh"
                if src.is_dir():
                    _replace_tree(src, case_dir / r / "constant" / "polyMesh")
            for log in sorted((self.root / MESH / "logs").glob("log.*")):  # meshing logs, read by extract
                if not (case_dir / log.name).exists():
                    shutil.copy2(log, case_dir / log.name)
        for r in roots:
            shutil.copytree(slot / r / t, case_dir / r / t, dirs_exist_ok=True)
        if (slot / "postProcessing").is_dir():
            shutil.copytree(slot / "postProcessing", case_dir / "postProcessing", dirs_exist_ok=True)
        self.saved, self.saved_app = t, m.get("application")
        return t

    def complete_time(self, case_dir: Path) -> str | None:
        """The newest time directory that every root has and nothing has
        written to for `settle` s."""
        now = self.clock()
        roots = _roots(case_dir)
        for _, name in reversed(time_dirs(roots[0])):
            try:
                if all(now - _newest_mtime(r / name) >= self.settle for r in roots):
                    return name
            except (OSError, ValueError):  # purged while we looked, or not on every processor yet
                continue
        return None

    def maybe_save(self, case_dir: Path, params_hash: str, force: bool = False) -> str | None:
        """Save the newest complete time directory if `interval` has passed
        since the last try (or `force`) and it is later than the one saved
        last by the same solver. (An earlier time is fine after a solver
        change: a steady start's last iteration becomes time 0 of the
        time-accurate run. It is not after a restore, whose directory the
        solver's purgeWrite never removes.) The mesh is saved with the first
        one. Returns the time saved, or None."""
        now = self.clock()
        if not force and now - self._last_try < self.interval:
            return None
        self._last_try = now
        case_dir = Path(case_dir)
        t = self.complete_time(case_dir)
        app = _application(case_dir)
        if t is None or (self.saved is not None and app == self.saved_app and float(t) <= float(self.saved)):
            return None
        m = self.manifest()
        roots = [str(r.relative_to(case_dir)) for r in _roots(case_dir)]
        mesh = bool(m and m.get("mesh") and m.get("roots", ["."]) == roots and m.get("params_hash") == params_hash)
        slot = "b" if m and m.get("slot") == "a" else "a"
        dst = self.root / slot
        try:
            if not mesh:  # once: the mesh is final by the time the solver writes
                for r in roots:
                    src = case_dir / r / "constant" / "polyMesh"
                    if src.is_dir():
                        _replace_tree(src, self.root / MESH / r / "constant" / "polyMesh")
                logs = self.root / MESH / "logs"
                shutil.rmtree(logs, ignore_errors=True)
                logs.mkdir(parents=True)
                for log in _done_logs(case_dir):
                    shutil.copy2(log, logs / log.name)
                mesh = True
            shutil.rmtree(dst, ignore_errors=True)
            dst.mkdir(parents=True, exist_ok=True)
            for r in roots:
                shutil.copytree(case_dir / r / t, dst / r / t)
            if (case_dir / "postProcessing").is_dir():
                shutil.copytree(case_dir / "postProcessing", dst / "postProcessing",
                                copy_function=_copy_whole_lines)
            tmp = self.root / (MANIFEST + ".tmp")
            tmp.write_text(json.dumps({"time": t, "slot": slot, "params_hash": params_hash, "roots": roots,
                                       "mesh": mesh, "application": app,
                                       "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                      indent=2) + "\n")
            tmp.replace(self.root / MANIFEST)
        except (OSError, shutil.Error):  # e.g. the solver purged the directory mid-copy: next time
            return None
        self.saved, self.saved_app = t, app
        return t

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
