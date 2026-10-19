"""Checkpoints: resume a long case after its machine is lost.

A Spot VM can be preempted at any time, and Cloud Batch then runs the task
again on a new VM, from scratch: a 20 h time-accurate case preempted every
11-14 h never finishes. With a checkpoint directory (cloud jobs: the
bucket), the runner copies the newest completely written time directory of
a running case there, with postProcessing/ (the force history), at most
every `interval` seconds. When the task runs again, run_case renders the
case as usual, restores the checkpoint, and the solver continues from it
(the templates start from latestTime).

Projects opt in per case (Project.checkpoint_setup): a case only has
something to save if it writes its fields during the run, which foil2d's
time-accurate cases then do every flow-through. Decomposed (np > 1) cases
are not checkpointed: their time directories live in processor*/.

Two slots alternate and the manifest is written last, so a preemption
during a copy leaves the previous checkpoint usable. A checkpoint is only
restored into a case with the same params_hash. It is deleted when its
case finishes ok (or not converged); a failed case keeps it.
"""

from __future__ import annotations

import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

MANIFEST = "checkpoint.json"


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

    def manifest(self) -> dict[str, Any] | None:
        try:
            return json.loads((self.root / MANIFEST).read_text())
        except (OSError, ValueError):
            return None

    def restore(self, case_dir: Path, params_hash: str) -> str | None:
        """Copy the checkpoint into a freshly rendered case. Returns the time
        restored, or None if there is no checkpoint for these parameters."""
        m = self.manifest()
        if not m or m.get("params_hash") != params_hash:
            return None
        slot, t = self.root / m["slot"], m["time"]
        if not (slot / t).is_dir():
            return None
        shutil.copytree(slot / t, Path(case_dir) / t, dirs_exist_ok=True)
        if (slot / "postProcessing").is_dir():
            shutil.copytree(slot / "postProcessing", Path(case_dir) / "postProcessing", dirs_exist_ok=True)
        self.saved = t
        return t

    def complete_time(self, case_dir: Path) -> str | None:
        """The newest time directory nothing has written to for `settle` s."""
        now = self.clock()
        for _, name in reversed(time_dirs(case_dir)):
            try:
                if now - _newest_mtime(Path(case_dir) / name) >= self.settle:
                    return name
            except OSError:  # purged while we looked
                continue
        return None

    def maybe_save(self, case_dir: Path, params_hash: str) -> str | None:
        """Save the newest complete time directory if `interval` has passed
        since the last try and it is newer than the last one saved. Returns
        the time saved, or None."""
        now = self.clock()
        if now - self._last_try < self.interval:
            return None
        self._last_try = now
        t = self.complete_time(case_dir)
        if t is None or (self.saved is not None and float(t) <= float(self.saved)):
            return None
        m = self.manifest()
        slot = "b" if m and m.get("slot") == "a" else "a"
        dst = self.root / slot
        try:
            shutil.rmtree(dst, ignore_errors=True)
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(Path(case_dir) / t, dst / t)
            if (Path(case_dir) / "postProcessing").is_dir():
                shutil.copytree(Path(case_dir) / "postProcessing", dst / "postProcessing",
                                copy_function=_copy_whole_lines)
            tmp = self.root / (MANIFEST + ".tmp")
            tmp.write_text(json.dumps({"time": t, "slot": slot, "params_hash": params_hash,
                                       "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                      indent=2) + "\n")
            tmp.replace(self.root / MANIFEST)
        except (OSError, shutil.Error):  # e.g. the solver purged the directory mid-copy: next time
            return None
        self.saved = t
        return t

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
