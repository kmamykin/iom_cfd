"""Watch a running solver: progress lines for the job log, and divergence.

`runner.run_case` polls a `Monitor` while ./Allrun runs. The monitor reads
the newest solver log (log.<application>): the time (or iteration), deltaT,
the Courant number and the solver's run time. Every `progress_seconds` it
logs one line; on Cloud Batch these go to Cloud Logging, where
`iomcfd gcp progress` reads them. Projects add their own numbers
(`Project.progress`, e.g. Cl, Cd and their drift) and their own divergence
test (`Project.diverged`, e.g. force coefficients out of range).

Generic divergence tests, each of which must hold for CONFIRM_POLLS polls in
a row:
* the time step collapsed below DT_COLLAPSE of the largest so far;
* the maximum Courant number passed COURANT_LIMIT;
* the solver's time stood still for STALL_SECONDS while its log kept
  growing.

A transient foil2d case that blew up showed all three: deltaT fell from
4e-4 to 1e-23 s, Courant 125,000, and the time stuck at one instant for 25 h
(transient-check run 20261017-193613).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

PROGRESS_SECONDS = 600.0  # a progress line every 10 min (the first after FIRST_PROGRESS)
FIRST_PROGRESS = 120.0
STALL_SECONDS = 1800.0  # solver time unchanged this long, log still growing: stuck
DT_COLLAPSE = 1e-3  # deltaT below this fraction of the largest so far
COURANT_LIMIT = 1000.0
CONFIRM_POLLS = 2
TAIL_BYTES = 256 * 1024

_TIME = re.compile(r"^Time = (\S+)", re.M)
_DT = re.compile(r"^deltaT = (\S+)", re.M)
_CO = re.compile(r"^Courant Number mean: \S+ max: (\S+)", re.M)
_EXEC = re.compile(r"^ExecutionTime = (\S+) s", re.M)
_BOUND = re.compile(r"^bounding (\w+),", re.M)
_ENTRY = r"^\s*{}\s+([^;]+);"


def _num(s: str | None) -> float | None:
    try:
        return float(s) if s is not None else None
    except ValueError:
        return None


def _last(pattern: re.Pattern, text: str) -> str | None:
    found = pattern.findall(text)
    return found[-1] if found else None


def _first(pattern: re.Pattern, text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1) if m else None


def solver_log(case_dir: Path) -> Path | None:
    """The log being written: the newest plain log.* other than log.Allrun."""
    logs = [p for p in Path(case_dir).glob("log.*") if p.name != "log.Allrun" and p.suffix != ".gz" and p.is_file()]
    return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


def _read(path: Path, nbytes: int, tail: bool) -> str:
    with open(path, "rb") as f:
        size = f.seek(0, 2)
        f.seek(max(0, size - nbytes) if tail else 0)
        data = f.read(nbytes)
    text = data.decode(errors="replace")
    if tail and size > nbytes:  # drop the partial first line
        text = text.split("\n", 1)[-1]
    return text


def _entry(text: str, key: str) -> str | None:
    m = re.search(_ENTRY.format(re.escape(key)), text, re.M)
    return m.group(1).strip() if m else None


def end_time(case_dir: Path) -> float | None:
    """controlDict's endTime; `$name` is looked up in system/caseParameters."""
    try:
        value = _entry((Path(case_dir) / "system" / "controlDict").read_text(errors="replace"), "endTime")
        if value and value.startswith("$"):
            value = _entry((Path(case_dir) / "system" / "caseParameters").read_text(errors="replace"), value[1:])
    except OSError:
        return None
    return _num(value)


@dataclass
class SolverState:
    log: str
    time: float | None  # current time, or iteration for steady solvers
    start_time: float | None  # the first time in the log
    end_time: float | None
    delta_t: float | None
    courant_max: float | None
    exec_time: float | None  # solver ExecutionTime [s]
    bounding: dict[str, int] = field(default_factory=dict)  # clipped fields, in the log's tail
    log_mtime: float = 0.0

    @property
    def fraction(self) -> float | None:
        if None in (self.time, self.start_time, self.end_time) or self.end_time <= self.start_time:
            return None
        return min(1.0, max(0.0, (self.time - self.start_time) / (self.end_time - self.start_time)))


def read_state(case_dir: Path) -> SolverState | None:
    log = solver_log(case_dir)
    if log is None:
        return None
    tail = _read(log, TAIL_BYTES, tail=True)
    head = _read(log, 64 * 1024, tail=False)
    bounding: dict[str, int] = {}
    for name in _BOUND.findall(tail):
        bounding[name] = bounding.get(name, 0) + 1
    return SolverState(
        log=log.name,
        time=_num(_last(_TIME, tail)),
        start_time=_num(_first(_TIME, head)),
        end_time=end_time(case_dir),
        delta_t=_num(_last(_DT, tail)),
        courant_max=_num(_last(_CO, tail)),
        exec_time=_num(_last(_EXEC, tail)),
        bounding=bounding,
        log_mtime=log.stat().st_mtime,
    )


def _fmt(v: Any) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    return f"{v:.4g}"


def _hours(s: float) -> str:
    return f"{s / 3600:.1f} h"


class Monitor:
    """Polled by the runner; `poll()` returns a divergence reason, or None."""

    def __init__(self, name: str, case_dir: Path,
                 progress: Callable[[], dict[str, Any]] | None = None,
                 diverged: Callable[[], str | None] | None = None,
                 log: Callable[[str], Any] = print,
                 progress_seconds: float = PROGRESS_SECONDS,
                 clock: Callable[[], float] = time.time):
        self.name, self.case_dir = name, Path(case_dir)
        self.project_progress, self.project_diverged = progress, diverged
        self.log, self.progress_seconds, self.clock = log, progress_seconds, clock
        self.t0 = clock()
        self.next_progress = self.t0 + min(FIRST_PROGRESS, progress_seconds)
        self._reset(None)

    def _reset(self, log_name: str | None) -> None:
        self.log_name = log_name
        self.max_dt = 0.0
        self.last_time: float | None = None
        self.last_advance = self.clock()
        self.strikes: dict[str, int] = {}

    def _extras(self) -> dict[str, Any]:
        if not self.project_progress:
            return {}
        try:
            return dict(self.project_progress() or {})
        except Exception:  # noqa: BLE001 - files may be mid-write
            return {}

    def line(self, st: SolverState | None) -> str:
        parts = [f"  progress  {self.name}  wall {_hours(self.clock() - self.t0)}"]
        if st is not None:
            parts.append(st.log)
            f = st.fraction
            if st.time is not None:
                parts.append(f"t {_fmt(st.time)}" + (f"/{_fmt(st.end_time)}" if st.end_time is not None else "")
                             + (f" ({100 * f:.1f} %)" if f is not None else ""))
            if st.delta_t is not None:
                parts.append(f"deltaT {st.delta_t:.3g}")
            if st.courant_max is not None:
                parts.append(f"Co max {st.courant_max:.3g}")
            if st.exec_time is not None:
                eta = f", ETA {_hours(st.exec_time * (1 - f) / f)}" if f and f > 1e-3 else ""
                parts.append(f"solver {_hours(st.exec_time)}{eta}")
            if st.bounding:
                parts.append("bounding " + ",".join(f"{k}:{n}" for k, n in sorted(st.bounding.items())))
        parts += [f"{k} {_fmt(v)}" for k, v in self._extras().items()]
        return "  ".join(parts)

    def _check(self, st: SolverState, now: float) -> dict[str, str]:
        found: dict[str, str] = {}
        if st.delta_t is not None and st.delta_t > 0:
            if self.max_dt and st.delta_t < DT_COLLAPSE * self.max_dt:
                found["dt"] = (f"time step collapsed: deltaT {st.delta_t:.3g} s against {self.max_dt:.3g} s "
                               f"earlier (t {_fmt(st.time)})")
            self.max_dt = max(self.max_dt, st.delta_t)
        if st.courant_max is not None and (not math.isfinite(st.courant_max) or st.courant_max > COURANT_LIMIT):
            found["courant"] = f"Courant number {st.courant_max:.3g} (t {_fmt(st.time)})"
        if st.time is not None:
            if self.last_time is None or abs(st.time - self.last_time) > 1e-9 * max(abs(st.time), 1e-30):
                self.last_time, self.last_advance = st.time, now
            elif now - self.last_advance > STALL_SECONDS and now - st.log_mtime < 300:
                found["stall"] = f"solver time stuck at {_fmt(st.time)} for {_hours(now - self.last_advance)}"
        if self.project_diverged:
            try:
                reason = self.project_diverged()
            except Exception:  # noqa: BLE001
                reason = None
            if reason:
                found["project"] = reason
        return found

    def poll(self) -> str | None:
        now = self.clock()
        st = read_state(self.case_dir)
        if st is not None and st.log != self.log_name:  # a new application started
            self._reset(st.log)
        if now >= self.next_progress:
            self.log(self.line(st))
            self.next_progress = now + self.progress_seconds
        if st is None:
            return None
        found = self._check(st, now)
        self.strikes = {k: self.strikes.get(k, 0) + 1 for k in found}
        hits = [found[k] for k in found if self.strikes[k] >= CONFIRM_POLLS]
        if hits:
            self.log(self.line(st))
            return "; ".join(hits)
        return None
