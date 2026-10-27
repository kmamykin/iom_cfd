"""The keel: fin and lead bulb (the shape) and two force models.

* `ParametricKeel`: keel3d's parametric keel (geometry/keel.py), hung from
  the hull at `mount.x` (the fin's root quarter chord): its fin and bulb
  masses and displaced volumes, and its planform for the force models.
* `PolarFit`: keel3d CFD at one speed (and a few heels), read from a VPP
  table (vpp/keel3d.py exports it) and fitted per heel as S_h = S0 + a β_Y
  and D_h = D0 + k S_h² (keel3d `polar_fits`, ORC's D_i = S_h² / (π q
  T_eff²)). keel3d is a double body of canoe body, fin and bulb, so its side
  force and yaw moment include the hull's; the hull's upright drag is left
  to the hull model (friction and waves), and only the drag that grows with
  side force is taken from the hull. Other speeds: friction scales with
  C_F(Re), pressure drag and side force with q, and the induced drag keeps
  T_eff (k ∝ 1/q). The table's geometry must be the shape's.
* `FinAndBulb`: no CFD (rung 0): the fin as a lifting line
  (components/foils.py) and the bulb's friction drag (`Bulb`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import yaml

from ...geometry.keel import keel_geometry
from .. import frames
from .. import keel3d as k3d
from .. import mass as massmod
from .. import tables
from ..hullres import ittc57
from .base import Loads, Perturbation, State, Wind, with_part
from .foils import LiftingLine, lift_slope, section_form_factor  # noqa: F401  (re-exported)


def body_form_factor(d_l: float) -> float:
    """Body-of-revolution drag over its friction (Hoerner): 1 + 1.5 (d/l)^1.5 + 7 (d/l)³."""
    return 1 + 1.5 * d_l**1.5 + 7 * d_l**3


def _interp(xq: float, xs: list[float], ys: list[float]) -> tuple[float, bool]:
    """Linear in x, held (and flagged) outside [xs[0], xs[-1]]."""
    if len(xs) == 1:
        return float(ys[0]), not math.isclose(xq, xs[0], abs_tol=0.5)
    out = xq < xs[0] - 1e-9 or xq > xs[-1] + 1e-9
    return float(np.interp(xq, xs, ys)), out


def bulb_wetted(g: dict) -> float:
    """Wetted area of the bulb: keel3d's derived value when present, else a
    body of revolution's ~0.75 π d L (an estimate)."""
    return float(g.get("bulb_wetted_area_m2") or 0.75 * math.pi * g["bulb_diameter"] * g["bulb_length"])


# ---------------------------------------------------------------------------
# the shape


@dataclass
class ParametricKeel:
    """keel3d's fin and bulb: `p` its keel3d-style parameters
    (projects/keel3d/defaults.yaml), `g` keel_geometry(p) with the fin's root
    on the host's bottom."""

    p: dict
    g: dict
    host: str  # the part it hangs from
    controls: tuple = ()

    @classmethod
    def build(cls, ctx, name: str, mount: dict | None = None, *, fin: dict, bulb: dict | None = None,
              draft: float | None = None, mass: float | None = None) -> "ParametricKeel":
        """fin {section, root_chord, tip_chord, sweep, mass}, bulb {section,
        aspect, top, bottom, cant, x, density}, draft (to the bulb's bottom)
        and mass (fin + bulb); what is left out is keel3d's default."""
        host = ctx.host(mount)
        p = yaml.safe_load(k3d.KEEL3D_DEFAULTS.read_text())
        p.update(getattr(host, "params", dict)())
        root, tip = float(fin["root_chord"]), float(fin["tip_chord"])
        # keel3d's mean chord and taper; rounded so decimal chords give them exactly
        p.update(fin_section=str(fin.get("section", p["fin_section"])), fin_mean_chord=round(0.5 * (root + tip), 12),
                 fin_taper=round(tip / root, 12), fin_x=float(mount["x"]))
        for k, key in (("sweep", "fin_sweep"), ("mass", "fin_mass")):
            if k in fin:
                p[key] = float(fin[k])
        for k, v in (bulb or {}).items():
            p["lead_density" if k == "density" else f"bulb_{k}"] = v if k == "section" else float(v)
        if draft is not None:
            p["draft"] = float(draft)
        if mass is not None:
            p["keel_mass"] = float(mass)
        p["bulb"] = bulb is not False
        z_root = -host.depth_at(float(p["fin_x"]))
        return cls(p, keel_geometry(p, z_root=z_root), mount["host"])

    def params(self) -> dict:
        return {k: self.p[k] for k in k3d.KEEL_KEYS}

    def planform(self) -> dict:
        span, chord = self.g["fin_span"], float(self.p["fin_mean_chord"])
        return {"span": span, "chord": chord, "section": str(self.p["fin_section"]), "x": float(self.p["fin_x"]),
                "z": self.g["fin_z_root"] - 0.5 * span, "area": self.g["fin_area_m2"], "aspect": 2 * span / chord}

    def mass_items(self) -> list[massmod.MassItem]:
        return massmod.keel_items(self.p, z_root=self.g["fin_z_root"])[0]

    def volumes(self) -> list[tuple[float, np.ndarray]]:
        return massmod.keel_items(self.p, z_root=self.g["fin_z_root"])[1]

    def rules(self) -> list[massmod.RuleResult]:
        return massmod.keel_rules(float(self.p["keel_mass"]), float(self.p["draft"]))

    def info(self) -> dict:
        return {"bulb_mass_kg": self.g["bulb_mass_kg"], "bulb_z_cg": round(self.g["bulb_z_cg"], 4),
                "fin_span": round(self.g["fin_span"], 4)}


# ---------------------------------------------------------------------------
# keel3d CFD


@dataclass
class PolarFit:
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
    controls: tuple = ()
    covers: frozenset = frozenset()
    fin_area: float = math.nan  # for the lift slope (downwash at the rudder) [m²]
    fin_aspect: float = math.nan  # 2 b / c

    @classmethod
    def build(cls, ctx, name: str, shape, *, table: str, max_leeway: float = 4.0,
              friction_factor: dict | None = None) -> "PolarFit":
        """`table`: a keel3d export (vpp/keel3d.py) of this shape's keel.
        friction_factor {fin: f, bulb: f} scales those parts' friction (a
        transition correction, e.g. the bulb-section findings' 0.80 and
        0.52)."""
        t = tables.read(ctx.resolve(table))
        tp = t.header.get("params") or {}
        diff = [k for k, v in shape.params().items() if k in tp and not _same(v, tp[k])]
        if diff:
            raise ValueError(f"{name}: {table} was computed for another keel: {', '.join(f'{k} {tp[k]} (boat file '
                             f'{shape.params()[k]})' for k in diff)}")
        hp = getattr(ctx.get(shape.host).shape, "params", dict)()
        hdiff = [k for k in k3d.HULL_KEYS if k in tp and k in hp and not _same(hp[k], tp[k])]
        if hdiff:
            ctx.warn(f"{name}: {table}'s hull differs from this boat's in {hdiff}: its side force and yaw moment "
                     "include that hull")
        f = cls.from_table(t, max_leeway, friction_factor, name)
        pf = shape.planform()
        src = t.header.get("source") or {}
        return replace(f, nu=ctx.water.nu, rho=ctx.water.rho, fin_area=pf["area"], fin_aspect=pf["aspect"],
                       covers=frozenset(c.replace("host", shape.host, 1) for c in t.header.get("includes") or []),
                       provenance=f"{table} ({src.get('run', '')} {src.get('select', '')})")

    @staticmethod
    def from_table(t: tables.Table, max_leeway: float = 4.0, friction_factor: dict | None = None,
                   name: str = "keel") -> "PolarFit":
        """The fits from a keel3d export's raw points (dims heel, leeway, V)."""
        if len({r["V"] for r in t.rows}) > 1:
            raise ValueError(f"{t.path}: points at more than one speed")
        ff = {"fin": 1.0, "bulb": 1.0, **(friction_factor or {})}
        cols = {f: [] for f in ("heels", "D0_friction", "D0_pressure", "k", "S0", "a", "x_clr", "z_clr", "fin_share")}
        for heel in sorted({r["heel"] for r in t.rows}):
            g = sorted((r for r in t.rows if r["heel"] == heel and r["leeway"] <= max_leeway + 1e-9),
                       key=lambda r: r["leeway"])
            up = [r for r in g if math.isclose(r["leeway"], 0.0, abs_tol=1e-8)]
            if len(g) < 3 or not up:
                continue
            u = up[0]
            # leeway-dependent drag of the whole double body less the hull's upright drag
            D = np.array([-r["X"] for r in g]) - (-u["X_hull"])
            S = np.array([r["Y"] for r in g])
            b = np.array([r["leeway"] for r in g])
            (d0, k), *_ = np.linalg.lstsq(np.column_stack([np.ones_like(S), S**2]), D, rcond=None)
            a, s0 = np.polyfit(b, S, 1)
            fric = ff["fin"] * -u["X_friction_fin"] + ff["bulb"] * -u["X_friction_bulb"]
            fric0 = -u["X_friction_fin"] + -u["X_friction_bulb"]
            lift = [r for r in g if r["leeway"] > 0]
            cols["heels"].append(float(heel))
            cols["D0_friction"].append(fric)
            cols["D0_pressure"].append(float(d0) - fric0)
            cols["k"].append(float(k))
            cols["S0"].append(float(s0))
            cols["a"].append(float(a))
            cols["x_clr"].append(float(np.nanmean([r["x"] for r in lift])))
            cols["z_clr"].append(float(np.nanmean([r["z"] for r in lift])))
            share = [r["Y_fin"] / r["Y"] for r in lift if isinstance(r.get("Y_fin"), float)]
            cols["fin_share"].append(float(np.nanmean(share)) if share and not np.isnan(share).all() else 0.83)
        if not cols["heels"]:
            raise ValueError(f"no heel with a leeway sweep (0 deg and two more) in {t.path}")
        fl, ref = t.header.get("fluid") or {}, t.header.get("reference") or {}
        return PolarFit(**cols, V_ref=float(t.rows[0]["V"]), length_ref=float(ref.get("length", 0.09)),
                        nu=float(fl.get("nu", 1.137e-6)), rho=float(fl.get("rho", 999.1)),
                        leeway_max=float(max_leeway), provenance=str(t.path), name=name)

    @staticmethod
    def from_results(path: str | Path, select: dict | None = None, max_leeway: float = 4.0,
                     friction_factor: dict | None = None, name: str = "keel") -> "PolarFit":
        """The fits straight from a keel3d results.csv, for the rows matching
        `select` (design parameters), at each heel."""
        import pandas as pd

        df = k3d.select_rows(pd.read_csv(path), select)
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
        return PolarFit(**cols, V_ref=float(r0["speed"]), length_ref=float(r0["fin_mean_chord"]),
                        nu=float(r0["nu"]), rho=float(r0["rhoInf"]), leeway_max=float(max_leeway),
                        provenance=f"{path} {select or {}}", name=name)

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

    def downwash(self) -> float:
        """The fin's elliptic far-field downwash per unit leeway, 2 C_Lα / (π A),
        with C_Lα the fits' mean side-force slope on the fin's area."""
        q_ref = 0.5 * self.rho * self.V_ref**2
        cla = float(np.mean(self.a)) * 180 / math.pi / (q_ref * self.fin_area)  # per rad, on the fin area
        return 2 * cla / (math.pi * self.fin_aspect)

    def perturbations(self) -> list[Perturbation]:
        n = self.name
        return [Perturbation(f"{n} D0 +1 %", _fields(n, 1.01, "D0_friction", "D0_pressure")),
                Perturbation(f"{n} k +1 % (T_eff −0.5 %)", _fields(n, 1.01, "k")),
                Perturbation(f"{n} side slope +1 %", _fields(n, 1.01, "a")),
                Perturbation(f"{n} leeway +1°", _leeway(n, 1.0))]

    def info(self) -> dict:
        return {"source": self.provenance}


def _same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or not (k3d.numeric(a) and k3d.numeric(b)):
        return str(a).lower() == str(b).lower()
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)


def _forces(name: str, fn):
    """A perturbation that replaces part `name`'s force model by fn(forces)."""
    return lambda b: with_part(b, name, lambda c: c.with_forces(fn(c.forces)))


def _fields(name: str, f: float, *fields: str):
    """Multiply list or scalar fields of the force model (e.g. PolarFit k)."""

    def fn(m):
        kw = {}
        for k in fields:
            v = getattr(m, k)
            kw[k] = [f * x for x in v] if isinstance(v, list) else f * v
        return replace(m, **kw)

    return _forces(name, fn)


def _leeway(name: str, deg: float):
    """The keel needs `deg` more leeway for the same side force (its lift
    curve moved by −deg)."""
    return _forces(name, lambda m: replace(m, S0=[s0 - a * deg for s0, a in zip(m.S0, m.a)]))


# ---------------------------------------------------------------------------
# no CFD


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


@dataclass
class FinAndBulb:
    """The keel without CFD: the fin as a lifting line on the shape's
    planform plus the bulb's friction drag."""

    fin: LiftingLine
    bulb: Bulb
    name: str = "keel"
    kind: str = "hydro"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()

    @classmethod
    def build(cls, ctx, name: str, shape, *, e: float = 0.9) -> "FinAndBulb":
        pf, g = shape.planform(), shape.g
        fin = LiftingLine(pf["span"], pf["chord"], pf["section"], x=pf["x"], z=pf["z"], e=float(e),
                          rho=ctx.water.rho, nu=ctx.water.nu, name=name)
        bulb = Bulb(g["bulb_length"], g["bulb_diameter"], bulb_wetted(g), x=g["bulb_x_cg"], z=g["bulb_z_cg"],
                    rho=ctx.water.rho, nu=ctx.water.nu, name=name)
        return cls(fin, bulb, name)

    def loads(self, s: State, w: Wind) -> Loads:
        fin, bulb = self.fin.loads(s, w), self.bulb.loads(s, w)
        ld = fin + bulb
        ld.info = {**fin.info, "D_bulb": bulb.info["D"]}
        return ld

    def downwash(self) -> float:
        return self.fin.downwash()

    def info(self) -> dict:
        return {"source": "lifting line + bulb friction"}
