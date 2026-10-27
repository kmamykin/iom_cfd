"""The equilibrium: for a true wind, the fastest boat speed at which the
forces balance (docs/nomenclature.md, balance equations; port tack).

Nested, so that every point is well defined and a failure stays local:

1. inner: for a boat speed V_b and the held controls, solve
   ΣY = 0 (S_a = S_h), ΣK = RM_φ (roll) and ΣN = 0 (yaw) for heel φ,
   leeway β_Y and the part's balance control (the rudder angle δ_R);
   sinkage and trim follow from the hydrostatics at each evaluation;
2. middle: the V_b where the drive surplus ΣX = T_a − D_h is zero;
3. outer: the optimised control (the sails' `flat`) that gives the
   greatest V_b, for each allowed option of the choice control (sail set).

The solver knows only the roles of the controls the parts declare
(components/base.py), at most one of each. With `yaw=False`, or no balance
control, the yaw balance is dropped (ORC style: "the yaw moment balance is
ignored") and the balance control is held at its default.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Protocol

import numpy as np
from scipy.optimize import brentq, minimize_scalar, root

from .components.base import Component, Control, Loads, State, Wind


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
    yaw: bool = True  # solve the yaw balance with the balance control
    optimise: bool = True  # search the optimised control (else hold it at its default)
    heel_max: float = 70.0  # beyond this the point is flagged
    leeway_max: float = 15.0  # an inner solution beyond this is rejected
    V_min: float = 0.02
    V_max: float = 6.0
    tol: float = 1e-8  # balance residual relative to the boat's force and moment scale
    attitude_passes: int = 2  # fixed-point passes between hull loads and trim


@dataclass
class Boat:
    components: list[Component]
    righting: Righting
    settings: Settings = field(default_factory=Settings)

    def component(self, name: str) -> Component:
        return next(c for c in self.components if c.name == name)

    def controls(self, role: str | None = None) -> list[Control]:
        """The parts' controls with their keys, in part order."""
        out = [replace(k, key=f"{c.name}.{k.name}") for c in self.components for k in getattr(c, "controls", ())]
        return [k for k in out if role is None or k.role == role]

    def control(self, role: str) -> Control | None:
        """The one control of this role, if any."""
        ks = self.controls(role)
        if len(ks) > 1:
            raise NotImplementedError(f"more than one {role} control: {[k.key for k in ks]}")
        return ks[0] if ks else None


@dataclass
class Point:
    tws: float
    twa: float
    V: float = math.nan
    heel: float = math.nan
    leeway: float = math.nan
    controls: dict[str, float] = field(default_factory=dict)
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
        r = {k: getattr(self, k) for k in ("tws", "twa", "V", "heel", "leeway")}
        r.update(self.controls)
        r.update({k: getattr(self, k) for k in ("sink", "trim", "rm", "residual", "converged", "extrapolated")})
        r["vmg"] = self.vmg
        r["flags"] = " ".join(self.flags)
        for name, ld in self.parts.items():
            for q in "XYZKMN":
                r[f"{q}_{name}"] = getattr(ld, q)
            r[f"{name}_extrapolated"] = ld.extrapolated
            for k, v in ld.info.items():
                if isinstance(v, (int, float)):
                    r[f"{name}_{k}"] = v
        return r


# ---------------------------------------------------------------------------
# one state


def _afloat(s: State, att: Attitude) -> State:
    return s.but(sink=att.sink, trim=att.trim, hydro=att.info)


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


def _yaw(boat: Boat) -> Control | None:
    """The control that closes the yaw balance, if it is solved."""
    return boat.control("balance") if boat.settings.yaw else None


def _state(V: float, x, fixed: dict[str, float], bal: Control | None) -> State:
    """State at V for unknowns x = [heel, leeway(, balance control)]."""
    c = dict(fixed)
    if bal is not None:
        c[bal.key] = float(x[2])
    return State(V, float(x[0]), float(x[1]), c)


def _balance(boat: Boat, w: Wind, V: float, fixed: dict[str, float], bal: Control | None, x) -> np.ndarray:
    total, _, att, _ = evaluate(boat, _state(V, x, fixed, bal), w)
    r = [total.Y, total.K - att.rm]
    if bal is not None:
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


def solve_inner(boat: Boat, w: Wind, V: float, fixed: dict[str, float], x0=None) -> Inner:
    """Heel, leeway (and the balance control) balancing side force, roll
    (and yaw) at V, with the other controls at `fixed`."""
    st = boat.settings
    bal = _yaw(boat)
    n = 3 if bal is not None else 2
    starts = [] if x0 is None else [np.asarray(x0, float)[:n]]
    starts += [np.array([h, b, 0.0][:n]) for h, b in ((10.0, 3.0), (25.0, 4.0), (2.0, 1.0), (40.0, 6.0))]
    _, parts0, att0, _ = evaluate(boat, _state(V, [*starts[0][:2], 0.0], fixed, bal), w)
    tol = st.tol * _scale(parts0, att0)

    def good(x, rnorm):
        return rnorm < tol and abs(x[1]) <= st.leeway_max and -10.0 <= x[0] <= 89.0

    best = None
    for xs in starts:
        try:
            sol = root(lambda x: _balance(boat, w, V, fixed, bal, x), xs, method="hybr")
        except (ValueError, FloatingPointError):
            continue
        x = sol.x
        res = _balance(boat, w, V, fixed, bal, x)
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
    total, parts, att, s1 = evaluate(boat, _state(V, x, fixed, bal), w)
    sc = _scale(parts, att)
    return Inner(x, ok, total.X if ok else math.nan, total, parts, att, s1, rnorm / sc, sc)


def solve_speed(boat: Boat, w: Wind, fixed: dict[str, float], V0: float | None = None, x0=None
                ) -> tuple[float, Inner | None]:
    """The V_b at which the drive surplus vanishes, for fixed controls; nan
    if there is none in [V_min, V_max]. Steps up and down from V0 by 20 %
    until two neighbouring balanced speeds bracket a sign change of the
    surplus (from + to −; the fastest such pair), then refines with Brent."""
    st = boat.settings
    cache: dict[float, Inner] = {}
    guess = [x0]

    def g(V: float) -> float:
        if V not in cache:
            inn = solve_inner(boat, w, V, fixed, guess[0])
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
    inn = cache.get(Vr) or solve_inner(boat, w, Vr, fixed, guess[0])
    return Vr, inn


def solve_point(boat: Boat, w: Wind, hold: dict[str, float] | None = None, guess: Point | None = None) -> Point:
    """The fastest balanced state for wind w. The optimised control is
    searched between its bounds (when settings.optimise), and every option
    of the choice control allowed at this β_TW is tried and the fastest
    kept; `hold` {key: value} holds either instead."""
    hold = dict(hold or {})
    ch = boat.control("choice")
    if ch is None:
        return _solve_point_set(boat, w, hold, guess)
    if ch.key in hold:
        sets = [hold[ch.key]]
    else:
        sets = [v for v, a_min in ch.options if w.twa >= a_min - 1e-9]
    best = None
    for k in sets or [ch.default]:
        p = _solve_point_set(boat, w, {**hold, ch.key: float(k)}, guess)
        if best is None or (p.converged and (not best.converged or p.V > best.V)):
            best = p
    return best


def _solve_point_set(boat: Boat, w: Wind, hold: dict[str, float], guess: Point | None) -> Point:
    st = boat.settings
    bal, opt = _yaw(boat), boat.control("optimise")
    fixed = {k.key: k.default for k in boat.controls() if bal is None or k.key != bal.key}
    fixed.update(hold)
    V0 = guess.V if guess and math.isfinite(guess.V) else None
    x0 = None
    if guess and math.isfinite(guess.heel):
        r = guess.controls.get(bal.key, math.nan) if bal is not None else math.nan
        x0 = [guess.heel, guess.leeway, r if math.isfinite(r) else 0.0]
    memo: dict[float, tuple[float, Inner | None]] = {}

    def speed(f: float) -> float:
        f = round(float(f), 6)
        if f not in memo:
            memo[f] = solve_speed(boat, w, fixed if opt is None else {**fixed, opt.key: f}, V0, x0)
        return memo[f][0]

    if opt is None:
        f_best = 0.0
    elif opt.key in hold or not st.optimise:
        f_best = float(fixed[opt.key])
    else:
        v1, v2 = speed(opt.hi), speed(opt.hi - 0.02)
        if not math.isfinite(v1) or (math.isfinite(v2) and v2 > v1):
            # coarse scan (the top of the range may have no balance at all), then refine around the best
            grid = np.linspace(opt.lo, opt.hi, 6)
            vals = [speed(f) for f in grid]
            ok = [i for i, v in enumerate(vals) if math.isfinite(v)]
            if not ok:
                f_best = opt.hi
            else:
                i = max(ok, key=lambda j: vals[j])
                lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
                r = minimize_scalar(lambda f: -speed(f) if math.isfinite(speed(f)) else 0.0,
                                    bounds=(lo, hi), method="bounded", options={"xatol": 1e-3})
                cands = [(speed(f), f) for f in (float(r.x), float(grid[i]), opt.hi) if math.isfinite(speed(f))]
                f_best = max(cands)[1]
        else:
            f_best = opt.hi
    V = speed(f_best)
    p = Point(w.tws, w.twa)
    inn = memo[round(f_best, 6)][1]
    if opt is not None:
        fixed = {**fixed, opt.key: f_best}
    p.controls = {k.key: fixed.get(k.key, math.nan) for k in boat.controls()}
    if not math.isfinite(V) or inn is None or not inn.ok:
        p.flags.append("no-equilibrium")
        return p
    s = inn.state
    p.V, p.heel, p.leeway = V, s.heel, s.leeway
    p.controls = {k.key: s.controls[k.key] for k in boat.controls()}
    p.sink, p.trim, p.rm = s.sink, s.trim, inn.att.rm
    p.residual = max(inn.residual, abs(inn.surplus) / inn.scale)
    p.converged = p.residual < 1e-6
    p.extrapolated = inn.total.extrapolated or any(v.extrapolated for v in inn.parts.values())
    p.parts = inn.parts
    if opt is not None and f_best <= opt.lo + 2e-3:
        p.flags.append(f"{opt.name}-at-min")
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
