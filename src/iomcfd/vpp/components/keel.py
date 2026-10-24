"""Keel (fin + bulb) and rudder forces.

Two kinds of model:

* `KeelFits`: keel3d CFD at one speed (and a few heels) fitted as
  S_h = S0 + a β_Y and D_h = D0 + k S_h² (keel3d `polar_fits`, ORC's
  D_i = S_h² / (π q T_eff²)). keel3d is a double body of canoe body, fin and
  bulb, so its side force and yaw moment include the hull's; the hull's
  upright drag is left to the hull model (friction and waves), and only the
  drag that grows with side force is taken from the hull. Other speeds:
  friction scales with C_F(Re), pressure drag and side force with q, and the
  induced drag keeps T_eff (k ∝ 1/q).
* `Foil`: a lifting surface from its planform (rung 0, no CFD): lift slope
  from Helmbold's low-aspect-ratio formula on the hull-mirrored aspect ratio,
  lifting-line induced drag (physics.induced_drag, hull as a reflection
  plane), profile drag from ITTC-57 friction and a thickness form factor.
  `Bulb` adds a body's friction drag. Used for the rudder, and for a keel
  without CFD. No stall: points beyond `alpha_max` are flagged.

Heel: a fin's lift is normal to its heeled plane (horizontal part L cos φ,
vertical L sin φ) and it sees the leeway as β_Y cos φ. Rudder angle δ_R (+ =
trailing edge to port) lowers the rudder's angle of attack: α = (β_Y − δ_R)
cos φ − ε, with ε the keel's downwash at the rudder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ... import physics
from ...geometry import foils
from .. import frames
from ..hullres import ittc57
from .base import Loads, State, Wind


def lift_slope(aspect: float) -> float:
    """Helmbold: dC_L/dα per radian of a straight wing of aspect ratio A,
    2π A / (2 + sqrt(A² + 4)); tends to 2π for large A and to πA/2 for small."""
    return 2 * math.pi * aspect / (2 + math.sqrt(aspect**2 + 4))


def section_form_factor(t_c: float) -> float:
    """Profile drag over twice the flat-plate friction (Hoerner): 1 + 2 t/c + 60 (t/c)⁴."""
    return 1 + 2 * t_c + 60 * t_c**4


def body_form_factor(d_l: float) -> float:
    """Body-of-revolution drag over its friction (Hoerner): 1 + 1.5 (d/l)^1.5 + 7 (d/l)³."""
    return 1 + 1.5 * d_l**1.5 + 7 * d_l**3


def _interp(xq: float, xs: list[float], ys: list[float]) -> tuple[float, bool]:
    """Linear in x, held (and flagged) outside [xs[0], xs[-1]]."""
    if len(xs) == 1:
        return float(ys[0]), not math.isclose(xq, xs[0], abs_tol=0.5)
    out = xq < xs[0] - 1e-9 or xq > xs[-1] + 1e-9
    return float(np.interp(xq, xs, ys)), out


@dataclass
class KeelFits:
    heels: list[float]  # φ of the fits [deg], increasing
    D0_friction: list[float]  # N at V_ref: friction part of D_h at S_h = 0 (after any transition factors)
    D0_pressure: list[float]  # N at V_ref: the rest of D0
    k: list[float]  # 1/N at V_ref
    S0: list[float]  # N at V_ref: side force at zero leeway
    a: list[float]  # N/deg at V_ref
    x_clr: list[float]  # m aft of the bow
    z_clr: list[float]  # m (negative: below the waterline)
    fin_share: list[float] = field(default_factory=list)  # the fin's part of S_h (side_fin_N / side_N)
    V_ref: float = 1.0
    length_ref: float = 0.09  # chord for the Reynolds number of the friction scaling [m]
    nu: float = 1.137e-6
    rho: float = 999.1
    leeway_max: float = 4.0  # the fits' range [deg]
    provenance: str = ""
    name: str = "keel"
    kind: str = "hydro"
    attitude: bool = False

    def at_heel(self, heel: float) -> tuple[dict, bool]:
        out = False
        vals = {}
        for f in ("D0_friction", "D0_pressure", "k", "S0", "a", "x_clr", "z_clr"):
            vals[f], o = _interp(abs(heel), self.heels, getattr(self, f))
            out |= o
        return vals, out

    def share_at(self, heel: float) -> tuple[float, bool]:
        return _interp(abs(heel), self.heels, self.fin_share) if self.fin_share else (0.83, True)

    def loads(self, s: State, w: Wind) -> Loads:
        v, out = self.at_heel(s.heel)
        r = (s.V / self.V_ref) ** 2
        cf = ittc57(max(s.V, 1e-3) * self.length_ref / self.nu) / ittc57(self.V_ref * self.length_ref / self.nu)
        D0 = r * (v["D0_friction"] * cf + v["D0_pressure"])
        S = r * (v["S0"] + v["a"] * s.leeway)
        D = D0 + v["k"] / max(r, 1e-12) * S**2
        out |= abs(s.leeway) > self.leeway_max + 1e-9
        pt = (v["x_clr"], 0.0, v["z_clr"])  # keel3d's centre of lateral resistance is already heeled
        ld = Loads.at(pt, X=-D, Y=S, extrapolated=out)
        ld.info.update({"D0": D0, "Di": D - D0, "S": S})
        return ld

    @staticmethod
    def from_results(path: str | Path, select: dict | None = None, max_leeway: float = 4.0,
                     friction_factor: dict | None = None, name: str = "keel") -> "KeelFits":
        """Fits from a keel3d results.csv, for the rows matching `select`
        (design parameters), at each heel. friction_factor {fin: f, bulb: f}
        scales those parts' friction (a transition correction, e.g. the
        bulb-section findings' 0.80 and 0.52)."""
        import pandas as pd

        df = pd.read_csv(path)
        df = df[df["status"].isin(["ok", "not_converged"])]
        for k, val in (select or {}).items():
            col = df[k]
            df = df[np.isclose(col.astype(float), float(val))] if _numeric(val) else df[col.astype(str) == str(val)]
        if df.empty:
            raise ValueError(f"no keel3d rows match {select} in {path}")
        if df["speed"].nunique() > 1:
            raise ValueError("keel3d rows at more than one speed: select one")
        ff = {"fin": 1.0, "bulb": 1.0, **(friction_factor or {})}
        cols = {f: [] for f in ("heels", "D0_friction", "D0_pressure", "k", "S0", "a", "x_clr", "z_clr", "fin_share")}
        for heel, g in df.groupby("heel"):
            g = g[g["leeway"] <= max_leeway + 1e-9].sort_values("leeway")
            up = g[np.isclose(g["leeway"], 0.0)]
            if len(g) < 3 or up.empty:
                continue
            u = up.iloc[0]
            # leeway-dependent drag of the whole double body less the hull's upright drag
            D = g["drag_N"].to_numpy(float) - float(u["drag_hull_N"])
            S = g["side_N"].to_numpy(float)
            b = g["leeway"].to_numpy(float)
            (d0, k), *_ = np.linalg.lstsq(np.column_stack([np.ones_like(S), S**2]), D, rcond=None)
            a, s0 = np.polyfit(b, S, 1)
            fric = ff["fin"] * float(u["drag_fin_friction_N"]) + ff["bulb"] * float(u["drag_bulb_friction_N"])
            fric0 = float(u["drag_fin_friction_N"]) + float(u["drag_bulb_friction_N"])
            lift = g[g["leeway"] > 0]
            cols["heels"].append(float(heel))
            cols["D0_friction"].append(fric)
            cols["D0_pressure"].append(float(d0) - fric0)
            cols["k"].append(float(k))
            cols["S0"].append(float(s0))
            cols["a"].append(float(a))
            cols["x_clr"].append(float(lift["x_clr"].mean()))
            cols["z_clr"].append(float(lift["z_clr"].mean()))
            cols["fin_share"].append(float((lift["side_fin_N"] / lift["side_N"]).mean()) if "side_fin_N" in lift
                                     else 0.83)
        if not cols["heels"]:
            raise ValueError(f"no heel with a leeway sweep (0 deg and two more) in {path}")
        r0 = df.iloc[0]
        return KeelFits(**cols, V_ref=float(r0["speed"]), length_ref=float(r0["fin_mean_chord"]),
                        nu=float(r0["nu"]), rho=float(r0["rhoInf"]), leeway_max=float(max_leeway),
                        provenance=f"{path} {select or {}}", name=name)


def _numeric(v) -> bool:
    try:
        float(v)
        return not isinstance(v, bool)
    except (TypeError, ValueError):
        return False


@dataclass
class Foil:
    """A fin or rudder below the hull: exposed span b, mean chord c, section,
    quarter-chord point at mid-span (x, z) in the upright boat frame."""

    span: float
    chord: float
    section: str = "naca0008"
    x: float = 0.5
    z: float = -0.2
    e: float = 0.9  # span efficiency of the induced drag
    downwash: float = 0.0  # ε per degree of leeway (the keel's, at the rudder)
    rudder: bool = False  # angle of attack includes −δ_R
    alpha_max: float = 12.0  # beyond this the model is flagged (no stall)
    rho: float = 999.1
    nu: float = 1.137e-6
    name: str = "fin"
    kind: str = "hydro"
    attitude: bool = False
    _tc: float = field(default=math.nan, repr=False)

    def __post_init__(self):
        if math.isnan(self._tc):
            self._tc = float(foils.load(self.section).thickness()[0])

    @property
    def area(self) -> float:
        return self.span * self.chord

    @property
    def aspect(self) -> float:
        return 2 * self.span / self.chord  # mirrored in the hull

    def alpha(self, s: State) -> float:
        a = s.leeway - (s.rudder if self.rudder else 0.0)
        return a * math.cos(math.radians(s.heel)) - self.downwash * s.leeway

    def loads(self, s: State, w: Wind) -> Loads:
        q = 0.5 * self.rho * s.V**2
        a = self.alpha(s)
        L = lift_slope(self.aspect) * math.radians(a) * q * self.area
        cf = ittc57(max(s.V, 1e-3) * self.chord / self.nu)
        Dv = 2 * cf * section_form_factor(self._tc) * q * self.area
        Di = physics.induced_drag(L, q, self.span, self.e) if q > 0 else 0.0
        p = math.radians(s.heel)
        pt = frames.heeled_point(self.x, 0.0, self.z, s.heel)
        ld = Loads.at(pt, X=-(Dv + Di), Y=L * math.cos(p), Z=L * math.sin(p), extrapolated=abs(a) > self.alpha_max)
        ld.info.update({"alpha": a, "L": L, "Dv": Dv, "Di": Di})
        return ld


@dataclass
class Bulb:
    """A body's drag only (no lift): ITTC-57 friction on its wetted area times
    Hoerner's body form factor, at its centre (x, z)."""

    length: float
    diameter: float
    wetted_area: float
    x: float = 0.5
    z: float = -0.4
    friction_factor: float = 1.0  # e.g. a laminar-run correction
    rho: float = 999.1
    nu: float = 1.137e-6
    name: str = "bulb"
    kind: str = "hydro"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        q = 0.5 * self.rho * s.V**2
        cf = ittc57(max(s.V, 1e-3) * self.length / self.nu) * self.friction_factor
        D = cf * body_form_factor(self.diameter / self.length) * q * self.wetted_area
        return Loads.at(frames.heeled_point(self.x, 0.0, self.z, s.heel), X=-D, info={"D": D})
