"""Exchange rates: race time per small change of one force, moment or mass.

Each perturbation modifies a built boat (or its spec) and the race is
re-timed at the baseline's best-VMG points. At those points the true wind
angle and `flat` are optimal, so to first order (the envelope theorem) only
the boat speed has to be re-solved, at the same angle and flat; that keeps a
rates run to a few solves per wind speed instead of a full VMG search.
`check=True` re-optimises angle and flat as well, to test that shortcut.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, replace
from typing import Callable

from .components.base import Loads, State, Wind
from .race import Course, RaceRow, WindRange, boat_lengths, race, race_row, weighted
from .solver import Attitude, Boat, best_vmg, solve_point


@dataclass
class Scaled:
    """A component whose loads are multiplied by `factor`."""

    base: object
    factor: float

    def __post_init__(self):
        self.name, self.kind, self.attitude = self.base.name, self.base.kind, self.base.attitude

    def loads(self, s: State, w: Wind) -> Loads:
        return self.base.loads(s, w).scaled(self.factor)


@dataclass
class ExtraDrag:
    """A constant drag force [N] at (x, z): a stand-in for any part's drag."""

    D: float
    x: float = 0.5
    z: float = -0.02
    name: str = "extra-drag"
    kind: str = "hydro"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        return Loads.at((self.x, 0.0, self.z), X=-self.D)


@dataclass
class RightingChange:
    base: object
    factor: float = 1.0

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude:
        a = self.base.at(heel, M_ext, Z_ext)
        return replace(a, rm=a.rm * self.factor)


@dataclass
class Perturbation:
    name: str  # what changes, e.g. "drag +0.01 N"
    apply: Callable[[Boat], Boat]
    note: str = ""


def _with(boat: Boat, name: str, fn) -> Boat:
    b = copy.copy(boat)
    b.components = [fn(c) if c.name == name else c for c in boat.components]
    return b


def scale_component(name: str, f: float) -> Callable[[Boat], Boat]:
    return lambda b: _with(b, name, lambda c: Scaled(c, f))


def scale_fields(name: str, f: float, *fields: str) -> Callable[[Boat], Boat]:
    """Multiply list or scalar fields of a dataclass component (e.g. KeelFits k)."""

    def fn(c):
        kw = {}
        for k in fields:
            v = getattr(c, k)
            kw[k] = [f * x for x in v] if isinstance(v, list) else f * v
        return replace(c, **kw)

    return lambda b: _with(b, name, fn)


def keel_leeway(name: str, deg: float) -> Callable[[Boat], Boat]:
    """The keel needs `deg` more leeway for the same side force (its lift
    curve moved by −deg); for a Foil, its zero-lift angle."""

    def fn(c):
        if hasattr(c, "S0") and hasattr(c, "a"):
            return replace(c, S0=[s0 - a * deg for s0, a in zip(c.S0, c.a)])
        raise TypeError(f"{name}: no lift-curve offset for {type(c).__name__}")

    return lambda b: _with(b, name, fn)


def add_drag(D: float) -> Callable[[Boat], Boat]:
    def fn(b: Boat) -> Boat:
        b = copy.copy(b)
        b.components = [*b.components, ExtraDrag(D)]
        return b

    return fn


def scale_righting(f: float) -> Callable[[Boat], Boat]:
    def fn(b: Boat) -> Boat:
        b = copy.copy(b)
        b.righting = RightingChange(b.righting, f)
        return b

    return fn


def standard(boat: Boat, rebuild: Callable[[dict], Boat] | None = None) -> list[Perturbation]:
    """The rates the plan asks for, as far as the boat's components allow.
    `rebuild(overrides)` builds the boat from its spec with dotted-path
    overrides, for changes of mass and its position."""
    names = {c.name: c for c in boat.components}
    out = [Perturbation("drag +0.01 N", add_drag(0.01), "constant drag at the hull"),
           Perturbation("RM_φ +1 %", scale_righting(1.01))]
    for n in ("hull", "sails", "rudder", "windage"):
        if n in names:
            out.append(Perturbation(f"{n} loads +1 %", scale_component(n, 1.01)))
    k = names.get("keel")
    if k is not None and hasattr(k, "k"):
        out += [Perturbation("keel D0 +1 %", scale_fields("keel", 1.01, "D0_friction", "D0_pressure")),
                Perturbation("keel k +1 % (T_eff −0.5 %)", scale_fields("keel", 1.01, "k")),
                Perturbation("keel side slope +1 %", scale_fields("keel", 1.01, "a")),
                Perturbation("keel leeway +1°", keel_leeway("keel", 1.0))]
    elif k is not None:
        out.append(Perturbation("keel loads +1 %", scale_component("keel", 1.01)))
    if rebuild is not None:
        out += [Perturbation("VCG −1 mm", lambda b: rebuild({"mass.vcg_shift": -0.001})),
                Perturbation("mass +10 g at the CG", lambda b: rebuild({"mass.extra": 0.010}))]
    return out


@dataclass
class Rate:
    name: str
    tws: float
    dt_up: float  # s over the race
    dt_down: float
    dt: float
    dt_pct: float  # % of that wind's race time
    vdrdv_up: float = math.nan  # for a drag perturbation: the V dR/dV it implies [N]
    vdrdv_down: float = math.nan

    def row(self) -> dict:
        return dict(self.__dict__)


def _retime(boat: Boat, course: Course, wind: WindRange, base: list[RaceRow], check: bool) -> list[RaceRow]:
    if check:
        return race(boat, WindRange(wind.tws, wind.weights, wind.z_ref, wind.alpha), course)
    out = []
    for r in base:
        pts = []
        for p in (r.up, r.down):
            pts.append(solve_point(boat, Wind(r.tws, p.twa, wind.z_ref, wind.alpha), flat=p.flat, guess=p)
                       if p.converged else p)
        out.append(race_row(course, r.tws, r.weight, *pts))
    return out


def rates(boat: Boat, course: Course, wind: WindRange, base: list[RaceRow], perts: list[Perturbation],
          check: bool = False) -> tuple[list[Rate], dict[str, float]]:
    """Per perturbation and wind: the change in race time; and the weighted
    change in % of the weighted race time."""
    t0 = weighted(base)
    out, summary = [], {}
    for pt in perts:
        rows = _retime(pt.apply(boat), course, wind, base, check)
        for r0, r1 in zip(base, rows):
            rate = Rate(pt.name, r0.tws, r1.t_up - r0.t_up, r1.t_down - r0.t_down, r1.t - r0.t,
                        100 * (r1.t - r0.t) / r0.t)
            if pt.name.startswith("drag +"):
                dD = float(pt.name.split("+")[1].split()[0])
                rate.vdrdv_up = _vdrdv(dD, r0.up, r1.up)
                rate.vdrdv_down = _vdrdv(dD, r0.down, r1.down)
            out.append(rate)
        summary[pt.name] = 100 * (weighted(rows) - t0) / t0
    return out, summary


def _vdrdv(dD: float, p0, p1) -> float:
    """V dR/dV implied by a drag step: ΔV/V = −ΔD / (V dR/dV), the slope the
    hand estimate (racetime.VDRDV) assumes, now with the sails' response."""
    dV = p1.V - p0.V
    return -dD * p0.V / dV if dV else math.inf


def lengths(rate_pct: float, rows: list[RaceRow], course: Course) -> float:
    """A weighted % of race time as boat lengths over the race."""
    t = weighted(rows)
    return boat_lengths(rate_pct / 100 * t, t, course)
