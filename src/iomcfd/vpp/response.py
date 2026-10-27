"""Each part's loads around the race's best-VMG states (response.csv): one
input at a time (V_b, heel, leeway, each control) varied, the others held at
the solved state, sinkage and trim re-solved (solver.evaluate). Open loop:
off the state the balance doesn't hold; what a force-model curve is. Values
read outside a part's table carry its `extrapolated` flag."""

from __future__ import annotations

import math

import numpy as np

from .components.base import State, Wind
from .race import RaceRow, WindRange
from .solver import Boat, Point, evaluate

HEELS = np.arange(0.0, 50.01, 5.0)  # deg
LEEWAYS = np.arange(0.0, 6.01, 0.5)  # deg
RUDDER = np.arange(-5.0, 5.01, 1.0)  # deg either side of the solved value


def _with(grid, v0: float) -> list[float]:
    """The grid and the solved value v0 itself (exact), ascending."""
    out = [float(g) for g in grid if not math.isclose(g, v0, rel_tol=1e-9, abs_tol=1e-9)]
    return sorted(out + [float(v0)])


def variables(boat: Boat, p: Point) -> dict[str, list[float]]:
    """What each input is swept over, by name: V, heel, leeway, control keys."""
    out = {"V": _with(p.V * np.linspace(0.5, 1.5, 11), p.V), "heel": _with(HEELS, p.heel),
           "leeway": _with(LEEWAYS, p.leeway)}
    for k in boat.controls():
        v0 = p.controls[k.key]
        if k.role == "optimise" and math.isfinite(k.lo) and math.isfinite(k.hi):
            out[k.key] = _with(np.linspace(k.lo, k.hi, 11), v0)
        elif k.role == "balance":
            out[k.key] = _with(v0 + RUDDER, v0)
        elif k.role == "choice":
            out[k.key] = sorted({float(v) for v, a_min in k.options if p.twa >= a_min - 1e-9} | {float(v0)})
    return out


def response(boat: Boat, p: Point, w: Wind) -> list[dict]:
    """polar.csv rows (Point.row) of every part's loads, with `var` and
    `value`, for each input of `variables` swept around the solved point p."""
    rows = []
    for var, values in variables(boat, p).items():
        for v in values:
            s = State(p.V, p.heel, p.leeway, dict(p.controls))
            if var in ("V", "heel", "leeway"):
                s = s.but(**{var: v})
            else:
                s = s.but(controls={**p.controls, var: v})
            total, parts, att, _ = evaluate(boat, s, w)
            q = Point(p.tws, p.twa, s.V, s.heel, s.leeway, dict(s.controls), att.sink, att.trim, att.rm,
                      extrapolated=total.extrapolated or any(ld.extrapolated for ld in parts.values()), parts=parts)
            r = q.row()
            for k in ("residual", "converged", "flags"):
                r.pop(k, None)
            rows.append({"var": var, "value": v, **r})
    return rows


def responses(boat: Boat, rows: list[RaceRow], wind: WindRange) -> list[dict]:
    """`response` around each wind's converged best-VMG points, up and down."""
    out = []
    for r in rows:
        for leg, p in (("up", r.up), ("down", r.down)):
            if p.converged:
                out += [{"leg": leg, **x} for x in response(boat, p, Wind(p.tws, p.twa, wind.z_ref, wind.alpha))]
    return out
