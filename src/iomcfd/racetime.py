"""Race-time ranking of fin sections (projects/foil2d/methodology.md, steps 1-7).

Each candidate fin (section and chord) is turned into the percentage of race
time it loses against the best candidate, on a windward-leeward course with
equal time upwind and downwind:

* upwind, at each load (a side force the sails demand): the fin's drag at
  that force, and the leeway (section angle) it needs to make it;
* downwind: the fin's drag at 0 deg.

Drag costs time through the slope of the boat's resistance with speed,
ΔD / (V dR/dV); leeway through the longer track, tan(track) Δα. The input is
a table of whole-fin forces per candidate, speed and angle (`fin_forces`
makes one from 2D Cl and Cd, e.g. XFOIL polars; foil2d's
report/selection.csv already is one).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from iomcfd.physics import fresh_water, induced_drag

# V dR/dV [N] at each boat speed [m/s]: hull, fin, bulb and rudder friction,
# no wave drag (methodology.md section 3 and 8; an estimate).
VDRDV = {0.5: 0.40, 0.75: 0.81, 1.0: 1.354, 1.5: 2.71}


@dataclass
class Course:
    span: float = 0.36  # m of fin below the hull
    e: float = 0.9  # span efficiency (hull as a reflection plane)
    track_deg: float = 42.0  # heading 39 deg + 3 deg leeway off the true wind
    vdrdv: dict[float, float] = field(default_factory=lambda: dict(VDRDV))
    slope_factor: float = 1.0  # x1 = the estimate above; x2 doubles it

    def vdrdv_at(self, speed: float) -> float:
        for v, s in self.vdrdv.items():
            if math.isclose(v, speed):
                return s * self.slope_factor
        raise KeyError(f"no resistance slope for {speed} m/s (have {sorted(self.vdrdv)})")


def fin_forces(df: pd.DataFrame, course: Course | None = None, rho: float | None = None) -> pd.DataFrame:
    """Whole-fin side force and drag (section + induced) [N] from 2D Cl, Cd.

    df needs candidate, chord [m], speed [m/s], aoa, Cl, Cd."""
    course = course or Course()
    rho = rho if rho is not None else fresh_water(15.0).rho
    t = df.copy()
    q = 0.5 * rho * t["speed"] ** 2
    t["side_force"] = t["Cl"] * q * t["chord"] * course.span
    t["drag"] = t["Cd"] * q * t["chord"] * course.span + induced_drag(t["side_force"], q, course.span, course.e)
    return t


def prestall_branch(aoa, force) -> np.ndarray:
    """Indices (increasing aoa) of the rising branch up to maximum side force,
    walked down from the maximum: a dip near 0 deg (the low-Reynolds lift
    reversal) is skipped, as in foil2d's selection_compare."""
    order = np.argsort(aoa)
    f = np.asarray(force, float)[order]
    keep, low = [], np.inf
    for k in range(int(np.argmax(f)), -1, -1):
        if f[k] < low:
            keep.append(k)
            low = f[k]
    return order[keep[::-1]]


def at_force(g: pd.DataFrame, force: float) -> tuple[float, float]:
    """(aoa, drag) of one candidate's polar at a side force, linear along the
    pre-stall branch; (nan, nan) outside it."""
    g = g[g["aoa"] >= 0]
    if g.empty:
        return math.nan, math.nan
    idx = prestall_branch(g["aoa"].to_numpy(), g["side_force"].to_numpy())
    sf = g["side_force"].to_numpy()[idx]
    if force < sf[0] - 1e-12 or force > sf[-1] + 1e-12:
        return math.nan, math.nan
    return (float(np.interp(force, sf, g["aoa"].to_numpy()[idx])),
            float(np.interp(force, sf, g["drag"].to_numpy()[idx])))


def loads_from(df: pd.DataFrame, reference: str, aoas=(2, 4, 6), names=("light", "working", "high")) -> pd.DataFrame:
    """The side forces the reference candidate makes at `aoas`, per speed."""
    r = df[df["candidate"] == reference]
    rows = []
    for speed, g in r.groupby("speed"):
        g = g.set_index("aoa")
        for name, a in zip(names, aoas):
            if a in g.index:
                rows.append({"speed": speed, "load": name, "force": float(g.loc[a, "side_force"])})
    return pd.DataFrame(rows)


def race_time(df: pd.DataFrame, loads: pd.DataFrame, course: Course | None = None) -> pd.DataFrame:
    """Race-time loss per candidate, speed and load.

    df: candidate, speed, aoa, side_force, drag (whole fin, N), with a 0 deg
    point per candidate and speed for the downwind leg. loads: speed, load,
    force. Returns one row per candidate, speed and load: aoa and drag at the
    load, drag at 0 deg, the upwind and downwind losses in % of each leg,
    `loss_abs` (% of race time, half upwind, half downwind) and `loss` (the
    same minus the best candidate's at that speed and load). Candidates
    that can't make the force get nan."""
    course = course or Course()
    tan_t = math.tan(math.radians(course.track_deg))
    rows = []
    for (cand, speed), g in df.groupby(["candidate", "speed"]):
        sel = loads[np.isclose(loads["speed"], speed)]
        if sel.empty:
            continue
        zero = g[np.isclose(g["aoa"], 0.0)]
        d0 = float(zero["drag"].iloc[0]) if not zero.empty else math.nan
        slope = course.vdrdv_at(speed)
        for _, ld in sel.iterrows():
            a, d = at_force(g, ld["force"])
            up = 100 * (d / slope + tan_t * math.radians(a))
            down = 100 * d0 / slope
            rows.append({"candidate": cand, "speed": speed, "load": ld["load"], "force": ld["force"], "aoa": a,
                         "drag_up": d, "drag_0": d0, "loss_up": up, "loss_down": down, "loss_abs": 0.5 * (up + down)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["loss"] = out["loss_abs"] - out.groupby(["speed", "load"])["loss_abs"].transform("min")
    return out


def summary(rt: pd.DataFrame, by: str = "candidate") -> pd.DataFrame:
    """Mean loss over loads and speeds per candidate, plus the worst point and
    the per-load means; sorted best first."""
    piv = rt.pivot_table(index=by, columns="load", values="loss", aggfunc="mean")
    s = pd.DataFrame({"mean": rt.groupby(by)["loss"].mean(), "worst": rt.groupby(by)["loss"].max()})
    return s.join(piv).sort_values("mean")
