"""The equilibrium: for a true wind, the fastest boat speed at which the
forces balance (docs/nomenclature.md, balance equations; port tack).

Nested, so that every point is well defined and a failure stays local:

1. inner: for a boat speed V_b and sail trim, solve
   ΣY = 0 (S_a = S_h), ΣK = RM_φ (roll) and ΣN = 0 (yaw) for heel φ,
   leeway β_Y and rudder angle δ_R; sinkage and trim follow from the
   hydrostatics at each evaluation;
2. middle: the V_b where the drive surplus ΣX = T_a − D_h is zero;
3. outer: the trim (`flat`) that gives the greatest V_b.

With `yaw=False` the rudder is held at `rudder` and the yaw balance is
dropped (ORC style: "the yaw moment balance is ignored").
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from scipy.optimize import brentq, minimize_scalar, root

from .components.base import Component, Loads, State, Wind


@dataclass
class Attitude:
    sink: float = 0.0
    trim: float = 0.0
    rm: float = 0.0  # RM_φ [N·m], + restoring
    extrapolated: bool = False
    info: dict = field(default_factory=dict)


class Righting(Protocol):
    """Hydrostatics: sinkage, trim and RM_φ at heel φ under the external
    vertical force Z_ext (+ up) and pitch moment M_ext (+ bow down)."""

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude: ...


@dataclass
class SineRighting:
    """RM_φ = K sin φ with no sinkage or trim (a test stand-in)."""

    K: float

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude:
        return Attitude(rm=self.K * math.sin(math.radians(heel)))


@dataclass
class Settings:
    yaw: bool = True  # solve the yaw balance with the rudder
    rudder: float = 0.0  # δ_R when yaw is False [deg]
    flat_min: float = 0.5  # lowest flat the outer search may use
    optimise_flat: bool = True
    heel_max: float = 70.0  # beyond this the point is flagged
    leeway_max: float = 15.0  # an inner solution beyond this is rejected
    V_min: float = 0.02
    V_max: float = 6.0
    tol: float = 1e-8  # balance residual relative to the boat's force and moment scale
    attitude_passes: int = 2  # fixed-point passes between hull loads and trim
    sailsets: tuple = ((0, 0.0),)  # (sail set, lowest β_TW it may be used at); the faster one is kept


@dataclass
class Boat:
    components: list[Component]
    righting: Righting
    settings: Settings = field(default_factory=Settings)

    def component(self, name: str) -> Component:
        return next(c for c in self.components if c.name == name)


@dataclass
class Point:
    tws: float
    twa: float
    V: float = math.nan
    heel: float = math.nan
    leeway: float = math.nan
    rudder: float = math.nan
    flat: float = math.nan
    twist: float = 0.0
    sailset: int = 0
    sink: float = math.nan
    trim: float = math.nan
    rm: float = math.nan
    residual: float = math.nan
    converged: bool = False
    extrapolated: bool = False
    flags: list[str] = field(default_factory=list)
    parts: dict[str, Loads] = field(default_factory=dict)

    @property
    def vmg(self) -> float:
        return self.V * math.cos(math.radians(self.twa))

    def row(self) -> dict:
        r = {k: getattr(self, k) for k in ("tws", "twa", "V", "heel", "leeway", "rudder", "flat", "twist", "sailset",
                                           "sink", "trim", "rm", "residual", "converged", "extrapolated")}
        r["vmg"] = self.vmg
        r["flags"] = " ".join(self.flags)
        for name, ld in self.parts.items():
            r[f"X_{name}"], r[f"Y_{name}"], r[f"K_{name}"], r[f"N_{name}"] = ld.X, ld.Y, ld.K, ld.N
            for k, v in ld.info.items():
                if isinstance(v, (int, float)):
                    r[f"{name}_{k}"] = v
        return r


# ---------------------------------------------------------------------------
# one state


def _afloat(s: State, att: Attitude) -> State:
    return s.but(sink=att.sink, trim=att.trim, wetted=att.info.get("wetted_area", math.nan),
                 lwl=att.info.get("lwl", math.nan))


def evaluate(boat: Boat, s: State, w: Wind) -> tuple[Loads, dict[str, Loads], Attitude, State]:
    """Loads of every component at state s, with sinkage and trim solved
    from the hydrostatics under the other components' Z and M."""
    parts = {c.name: c.loads(s, w) for c in boat.components if not c.attitude}
    base = sum(parts.values(), Loads())
    dep = [c for c in boat.components if c.attitude]
    hz = hm = 0.0
    att = boat.righting.at(s.heel, M_ext=base.M, Z_ext=base.Z)
    s1 = _afloat(s, att)
    for _ in range(boat.settings.attitude_passes if dep else 0):
        hp = {c.name: c.loads(s1, w) for c in dep}
        new_hz, new_hm = sum(v.Z for v in hp.values()), sum(v.M for v in hp.values())
        if abs(new_hm - hm) < 1e-6 and abs(new_hz - hz) < 1e-6 and hp:
            break
        hz, hm = new_hz, new_hm
        att = boat.righting.at(s.heel, M_ext=base.M + hm, Z_ext=base.Z + hz)
        s1 = _afloat(s, att)
    if dep:
        parts.update({c.name: c.loads(s1, w) for c in dep})
    total = sum(parts.values(), Loads())
    total.extrapolated = total.extrapolated or att.extrapolated
    return total, parts, att, s1


def _balance(boat: Boat, w: Wind, V: float, flat: float, twist: float, sailset: int, x) -> np.ndarray:
    heel, leeway = float(x[0]), float(x[1])
    rudder = float(x[2]) if boat.settings.yaw else boat.settings.rudder
    total, _, att, _ = evaluate(boat, State(V, heel, leeway, rudder, flat, twist, sailset), w)
    r = [total.Y, total.K - att.rm]
    if boat.settings.yaw:
        r.append(total.N)
    return np.asarray(r)


@dataclass
class Inner:
    x: np.ndarray
    ok: bool
    surplus: float  # ΣX = T_a − D_h at the balance [N]
    total: Loads | None = None
    parts: dict | None = None
    att: Attitude | None = None
    state: State | None = None
    residual: float = math.nan  # relative to the force scale
    scale: float = 1.0  # N, N·m (_scale)


def _scale(parts: dict[str, Loads], att: Attitude) -> float:
    """Force and moment scale of the boat [N, N·m] for relative tolerances."""
    return max(1.0, sum(abs(v.Y) for v in parts.values()), sum(abs(v.K) for v in parts.values()), abs(att.rm))


def solve_inner(boat: Boat, w: Wind, V: float, flat: float, twist: float = 0.0, x0=None, sailset: int = 0) -> Inner:
    """Heel, leeway (and rudder) balancing side force, roll (and yaw) at V."""
    st = boat.settings
    n = 3 if st.yaw else 2
    starts = [] if x0 is None else [np.asarray(x0, float)[:n]]
    starts += [np.array([h, b, 0.0][:n]) for h, b in ((10.0, 3.0), (25.0, 4.0), (2.0, 1.0), (40.0, 6.0))]
    _, parts0, att0, _ = evaluate(boat, State(V, *[float(v) for v in starts[0][:2]], 0.0, flat, twist, sailset), w)
    tol = st.tol * _scale(parts0, att0)

    def good(x, rnorm):
        return rnorm < tol and abs(x[1]) <= st.leeway_max and -10.0 <= x[0] <= 89.0

    best = None
    for xs in starts:
        try:
            sol = root(lambda x: _balance(boat, w, V, flat, twist, sailset, x), xs, method="hybr")
        except (ValueError, FloatingPointError):
            continue
        x = sol.x
        res = _balance(boat, w, V, flat, twist, sailset, x)
        rnorm = float(np.max(np.abs(res))) if np.all(np.isfinite(res)) else math.inf
        if good(x, rnorm):
            best = (x, rnorm)
            break
        if best is None or rnorm < best[1]:
            best = (x, rnorm)
    if best is None:
        return Inner(np.full(n, math.nan), False, math.nan)
    x, rnorm = best
    ok = good(x, rnorm)
    rudder = float(x[2]) if st.yaw else st.rudder
    s = State(V, float(x[0]), float(x[1]), rudder, flat, twist, sailset)
    total, parts, att, s1 = evaluate(boat, s, w)
    sc = _scale(parts, att)
    return Inner(x, ok, total.X if ok else math.nan, total, parts, att, s1, rnorm / sc, sc)


def solve_speed(boat: Boat, w: Wind, flat: float, twist: float = 0.0, V0: float | None = None, x0=None,
                sailset: int = 0) -> tuple[float, Inner | None]:
    """The V_b at which the drive surplus vanishes, for fixed trim; nan if
    there is none in [V_min, V_max]. Steps up and down from V0 by 20 % until
    two neighbouring balanced speeds bracket a sign change of the surplus
    (from + to −; the fastest such pair), then refines with Brent."""
    st = boat.settings
    cache: dict[float, Inner] = {}
    guess = [x0]

    def g(V: float) -> float:
        if V not in cache:
            inn = solve_inner(boat, w, V, flat, twist, guess[0], sailset)
            if inn.ok:
                guess[0] = inn.x
            cache[V] = inn
        inn = cache[V]
        return inn.surplus if inn.ok else math.nan

    def bracket():
        pts = sorted((v, g(v)) for v in cache)
        pairs = [(a, b) for (a, ga), (b, gb) in zip(pts, pts[1:])
                 if math.isfinite(ga) and math.isfinite(gb) and ga > 0 >= gb]
        return pairs[-1] if pairs else None

    Vs = min(max(V0 if V0 else 0.5 * w.tws, st.V_min), st.V_max)
    g(Vs)
    V = Vs
    while V < st.V_max and not any(math.isfinite(gv) and gv <= 0 for v, gv in ((u, g(u)) for u in cache) if v >= Vs):
        V = min(V * 1.2, st.V_max)
        g(V)
    V = Vs
    while V > st.V_min and bracket() is None:
        V = max(V / 1.2, st.V_min)
        g(V)
    br = bracket()
    if br is None:
        return math.nan, None
    lo, hi = br

    def gf(v: float) -> float:
        gv = g(v)
        if not math.isfinite(gv):
            raise ValueError("no balance inside the bracket")
        return gv

    try:
        Vr = brentq(gf, lo, hi, xtol=1e-9, rtol=1e-12)
    except ValueError:
        return math.nan, None
    inn = cache.get(Vr) or solve_inner(boat, w, Vr, flat, twist, guess[0], sailset)
    return Vr, inn


def solve_point(boat: Boat, w: Wind, flat: float | None = None, twist: float = 0.0, guess: Point | None = None,
                sailset: int | None = None) -> Point:
    """The fastest balanced state for wind w. flat=None searches flat in
    [flat_min, 1] (when settings.optimise_flat), else holds it. Every sail set
    allowed at this β_TW is tried (or only `sailset`) and the fastest kept."""
    sets = [s for s, a_min in boat.settings.sailsets if w.twa >= a_min - 1e-9] if sailset is None else [sailset]
    best = None
    for k in sets or [0]:
        p = _solve_point_set(boat, w, flat, twist, guess, k)
        if best is None or (p.converged and (not best.converged or p.V > best.V)):
            best = p
    return best


def _solve_point_set(boat: Boat, w: Wind, flat: float | None, twist: float, guess: Point | None, sailset: int
                     ) -> Point:
    st = boat.settings
    V0 = guess.V if guess and math.isfinite(guess.V) else None
    x0 = None
    if guess and math.isfinite(guess.heel):
        x0 = [guess.heel, guess.leeway, guess.rudder if math.isfinite(guess.rudder) else 0.0]
    memo: dict[float, tuple[float, Inner | None]] = {}

    def speed(f: float) -> float:
        f = round(float(f), 6)
        if f not in memo:
            memo[f] = solve_speed(boat, w, f, twist, V0, x0, sailset)
        return memo[f][0]

    if flat is not None or not st.optimise_flat:
        f_best = 1.0 if flat is None else float(flat)
    else:
        v1, v2 = speed(1.0), speed(0.98)
        if not math.isfinite(v1) or (math.isfinite(v2) and v2 > v1):
            # coarse scan (flat 1 may have no balance at all), then refine around the best
            grid = np.linspace(st.flat_min, 1.0, 6)
            vals = [speed(f) for f in grid]
            ok = [i for i, v in enumerate(vals) if math.isfinite(v)]
            if not ok:
                f_best = 1.0
            else:
                i = max(ok, key=lambda j: vals[j])
                lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
                r = minimize_scalar(lambda f: -speed(f) if math.isfinite(speed(f)) else 0.0,
                                    bounds=(lo, hi), method="bounded", options={"xatol": 1e-3})
                cands = [(speed(f), f) for f in (float(r.x), float(grid[i]), 1.0) if math.isfinite(speed(f))]
                f_best = max(cands)[1]
        else:
            f_best = 1.0
    V = speed(f_best)
    p = Point(w.tws, w.twa, flat=f_best, twist=twist, sailset=sailset)
    inn = memo[round(f_best, 6)][1]
    if not math.isfinite(V) or inn is None or not inn.ok:
        p.flags.append("no-equilibrium")
        return p
    s = inn.state
    p.V, p.heel, p.leeway, p.rudder = V, s.heel, s.leeway, s.rudder
    p.sink, p.trim, p.rm = s.sink, s.trim, inn.att.rm
    p.residual = max(inn.residual, abs(inn.surplus) / inn.scale)
    p.converged = p.residual < 1e-6
    p.extrapolated = inn.total.extrapolated or any(v.extrapolated for v in inn.parts.values())
    p.parts = inn.parts
    if f_best <= st.flat_min + 2e-3:
        p.flags.append("flat-at-min")
    if s.heel > st.heel_max:
        p.flags.append("heel-over-max")
    if p.extrapolated:
        p.flags.append("extrapolated")
    return p


# ---------------------------------------------------------------------------
# polars and VMG


def polar(boat: Boat, tws: list[float], twa: list[float], z_ref: float = 1.0, alpha: float = 0.0) -> list[Point]:
    """Points on a grid, continued along TWA within each TWS."""
    out = []
    for v in tws:
        prev = None
        for a in twa:
            p = solve_point(boat, Wind(v, a, z_ref, alpha), guess=prev)
            out.append(p)
            if p.converged:
                prev = p
    return out


def best_vmg(boat: Boat, tws: float, leg: str, z_ref: float = 1.0, alpha: float = 0.0,
             bounds: tuple[float, float] | None = None, guess: Point | None = None) -> Point:
    """The TWA (from the course) that gives the best VMG upwind or downwind.
    Downwind VMG is V_b cos(180° − β_TW)."""
    lo, hi = bounds or ((25.0, 75.0) if leg == "up" else (110.0, 180.0))
    sign = 1.0 if leg == "up" else -1.0
    seen: dict[float, Point] = {}
    last = [guess]

    def neg_vmg(a: float) -> float:
        a = round(float(a), 4)
        if a not in seen:
            p = solve_point(boat, Wind(tws, a, z_ref, alpha), guess=last[0])
            seen[a] = p
            if p.converged:
                last[0] = p
        p = seen[a]
        return -sign * p.vmg if p.converged else 0.0

    # coarse scan, then a bounded search around the best
    grid = np.linspace(lo, hi, 7)
    vals = [neg_vmg(a) for a in grid]
    i = int(np.argmin(vals))
    a_lo, a_hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    r = minimize_scalar(neg_vmg, bounds=(a_lo, a_hi), method="bounded", options={"xatol": 0.05})
    best = min(seen.values(), key=lambda p: -sign * p.vmg if p.converged else math.inf)
    if r.success and round(float(r.x), 4) in seen and seen[round(float(r.x), 4)].converged:
        cand = seen[round(float(r.x), 4)]
        if -sign * cand.vmg <= -sign * best.vmg:
            best = cand
    if abs(best.twa - lo) < 0.1 or abs(best.twa - hi) < 0.1:
        if not (leg == "down" and abs(best.twa - 180.0) < 0.1):
            best.flags.append("vmg-at-bound")
    return best
