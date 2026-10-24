"""A boat definition (boats/<name>.yaml) and the solver-ready model built from it.

The YAML names each part's model and its inputs (see boats/canoe-placeholder.yaml).
`--set a.b.c=value` overrides any entry by its dotted path. Building does the
slow work once: the hydrostatic table (sinkage, trim and RM_φ over heel and
pitch moment) and the hull's wave-resistance table.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .. import config, physics
from ..geometry import hulls, stl
from ..geometry.keel import keel_geometry
from . import mass as massmod
from . import sails_orc
from .components.hull import CanoeHull
from .components.keel import Bulb, Foil, KeelFits, lift_slope
from .components.sails import SAILSETS, OrcSails, rig_centroid
from .components.section import SectionChange, deltas
from .components.windage import Windage
from .hydrostatics import Hydrostatics, HydroTable
from .race import Course, WindRange
from .solver import Attitude, Boat, Settings

KEEL3D_DEFAULTS = config.projects_dir() / "keel3d" / "defaults.yaml"


# ---------------------------------------------------------------------------
# spec


def set_path(d: dict, dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


@dataclass
class BoatSpec:
    data: dict
    path: Path | None = None

    @staticmethod
    def load(path: str | Path, overrides: dict[str, Any] | None = None) -> "BoatSpec":
        path = Path(path)
        data = yaml.safe_load(path.read_text()) or {}
        spec = BoatSpec(data, path)
        return spec.with_overrides(overrides or {})

    def with_overrides(self, overrides: dict[str, Any]) -> "BoatSpec":
        d = copy.deepcopy(self.data)
        for k, v in overrides.items():
            set_path(d, k, v)
        return BoatSpec(d, self.path)

    @property
    def name(self) -> str:
        return str(self.data.get("boat", self.path.stem if self.path else "boat"))

    def get(self, dotted: str, default: Any = None) -> Any:
        d: Any = self.data
        for k in dotted.split("."):
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d


# keel3d parameters that make the keel (geometry and mass): with keel.model
# keel3d they are taken from the CFD run, so mass and VCG match the forces.
KEEL_KEYS = ("draft", "keel_mass", "fin_mass", "lead_density", "fin_section", "fin_mean_chord", "fin_taper",
             "fin_sweep", "fin_x", "bulb", "bulb_section", "bulb_x", "bulb_aspect", "bulb_top", "bulb_bottom",
             "bulb_cant")
HULL_KEYS = ("hull_length", "hull_beam", "hull_draft", "hull_beam_at", "hull_draft_at", "hull_entry", "hull_run",
             "hull_section")


def keel_params(spec: BoatSpec, run_row: dict | None = None) -> dict[str, Any]:
    """keel3d-style parameters: keel3d's defaults, the hull's CanoeSpec fields
    as hull_*, keel.params, then the CFD run's keel (run_row)."""
    p = yaml.safe_load(KEEL3D_DEFAULTS.read_text())
    for k, v in (spec.get("hull.params") or {}).items():
        p[f"hull_{k}"] = v
    p.update(spec.get("keel.params") or {})
    if run_row:
        p.update({k: run_row[k] for k in KEEL_KEYS if k in run_row})
    return p


def keel3d_row(path: Path, select: dict | None) -> dict:
    """The parameters of the first keel3d case matching `select`."""
    import pandas as pd

    df = pd.read_csv(path)
    for k, val in (select or {}).items():
        if isinstance(val, (str, bool)):
            df = df[df[k].astype(str) == str(val)]
        else:
            df = df[np.isclose(df[k].astype(float), float(val))]
    if df.empty:
        raise ValueError(f"no keel3d rows match {select} in {path}")
    row = df.iloc[0].to_dict()
    return {k: (bool(v) if k == "bulb" else v) for k, v in row.items()}


def canoe_spec(p: dict[str, Any]) -> hulls.CanoeSpec:
    fields = {f: p[f"hull_{f}"] for f in ("length", "beam", "draft", "beam_at", "draft_at", "entry", "run",
                                          "rise_fwd", "rise_aft", "section", "freeboard") if f"hull_{f}" in p}
    return hulls.CanoeSpec(**fields)


def resolve_results(ref: str, base: Path | None) -> Path:
    """A keel3d run's results.csv from `<study>@<run id>` (looked up in
    config.source_runs_dirs()) or a path (relative to the boat file, then the
    repo root)."""
    if "@" in ref and not ref.endswith(".csv"):
        study, run = ref.split("@", 1)
        for d in config.source_runs_dirs():
            p = d / study / run / "results.csv"
            if p.exists():
                return p
        raise FileNotFoundError(f"{ref}: no {study}/{run}/results.csv in {[str(d) for d in config.source_runs_dirs()]}"
                                " (set IOMCFD_SOURCE_RUNS to the runs/ that holds it)")
    for b in ([base] if base else []) + [config.home()]:
        p = (b / ref).resolve()
        if p.exists():
            return p if p.suffix == ".csv" else p / "results.csv"
    raise FileNotFoundError(ref)


# ---------------------------------------------------------------------------
# righting from the hydrostatic table


@dataclass
class TableRighting:
    table: HydroTable
    solved: bool = True  # False: the attitude at M_ext = 0 (no trim response)

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude:
        d = self.table.at(abs(heel), M_ext if self.solved else 0.0)
        sign = 1.0 if heel >= 0 else -1.0
        return Attitude(d["sink"], d["trim"], sign * d["rm"], bool(d.get("extrapolated", False)),
                        {"wetted_area": d["wetted_area"], "lwl": d["lwl"]})


@dataclass
class Built:
    """A built boat and what it was built from."""

    spec: BoatSpec
    boat: Boat
    wind: WindRange
    course: Course
    mass: massmod.MassBudget
    keel: dict
    hydro: Hydrostatics
    info: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def build(spec: BoatSpec, table: HydroTable | None = None) -> Built:
    water = physics.fresh_water(float(spec.get("water.temperature", 15.0)))
    air = physics.air(float(spec.get("air.temperature", 15.0)))
    warnings: list[str] = []

    # --- geometry: hull and keel -------------------------------------------
    kmodel = spec.get("keel.model", "keel3d")
    run_row, results = None, None
    if kmodel == "keel3d":
        results = resolve_results(str(spec.get("keel.results")), spec.path.parent if spec.path else None)
        run_row = keel3d_row(results, spec.get("keel.select"))
    p = keel_params(spec, run_row)
    if run_row:
        diff = [k for k in HULL_KEYS if k in run_row and not np.isclose(float(run_row[k]), float(p[k]))]
        if diff:
            warnings.append(f"the keel3d run's hull differs from this boat's in {diff}: its side force and yaw "
                            "moment include that hull")
    kg = keel_geometry(p)
    geom = spec.get("hull.geometry", "canoe")
    if geom != "canoe":
        raise NotImplementedError(f"hull.geometry {geom}: only the parametric canoe body so far")
    cs = canoe_spec(p)
    hull_surface = hulls.canoe(cs)

    # --- rudder -----------------------------------------------------------------
    r = spec.get("rudder") or {}
    r_root, r_tip, r_span = float(r.get("root_chord", 0.085)), float(r.get("tip_chord", 0.060)), float(r.get("span", 0.20))
    r_chord = 0.5 * (r_root + r_tip)
    r_x = float(r.get("x", 0.86)) + 0.25 * r_chord
    r_z = -float(hulls.canoe_depth(cs, min(r_x, cs.length))) - 0.5 * r_span

    # --- mass and hydrostatics -----------------------------------------------
    items = massmod.MassBudget.from_list(spec.get("mass.items") or [])
    keel_items, app_volumes = massmod.keel_items(p)
    budget = massmod.MassBudget([*keel_items, *items.items])
    if spec.get("mass.extra"):
        budget = budget.with_item(massmod.MassItem("extra (rates)", float(spec.get("mass.extra")),
                                                   tuple(budget.cg)))
    fill = spec.get("mass.fill_to")
    if fill:
        budget = massmod.fill_to_minimum(budget, float(fill), at=tuple(spec.get("mass.corrector_at", (0.5, 0, 0))))
    if spec.get("mass.vcg_shift"):
        dz = float(spec.get("mass.vcg_shift"))
        budget = massmod.MassBudget([massmod.MassItem(i.name, i.m, (i.cg[0], i.cg[1], i.cg[2] + dz), i.source)
                                     for i in budget.items])
    rudder_vol = 0.5 * float(foils_area(r.get("section", "naca0008"))) * (r_root**2 + r_tip**2) * r_span
    app_volumes = [*app_volumes, (rudder_vol, np.array([r_x, 0.0, r_z]))]
    hydro = Hydrostatics(hull_surface, app_volumes, mass=budget.mass, cg=budget.cg, rho=water.rho)
    if table is None:
        hmax, hstep = float(spec.get("hydrostatics.heel_max", 60.0)), float(spec.get("hydrostatics.heel_step", 2.5))
        table = hydro.table(heels=np.arange(0.0, hmax + 1e-9, hstep))
    righting = TableRighting(table, spec.get("hydrostatics.attitude", "solved") == "solved")
    for rr in massmod.check_rules(budget.mass, float(p["keel_mass"]), float(p["draft"])):
        if not rr.ok:
            warnings.append(f"class rule {rr.clause} ({rr.quantity}) fails: {rr.value:.4g} not in "
                            f"[{rr.lo}, {rr.hi}]")

    # --- components ------------------------------------------------------------
    comps = []
    if kmodel == "keel3d":
        keel = KeelFits.from_results(results, spec.get("keel.select"), float(spec.get("keel.max_leeway", 4.0)),
                                     spec.get("keel.friction_factor"))
        keel.nu, keel.rho = water.nu, water.rho
        q_ref = 0.5 * keel.rho * keel.V_ref**2
        cla = float(np.mean(keel.a)) * 180 / math.pi / (q_ref * kg["fin_area_m2"])  # per rad, on the fin area
        hull_side = False
        sec = spec.get("keel.section") or {}
        ref = str(sec.get("reference", p["fin_section"]))
        if sec.get("foil") and str(sec["foil"]) != ref:
            if ref != str(p["fin_section"]):
                warnings.append(f"keel.section.reference {ref} is not the keel3d fin's section {p['fin_section']}")
            keel = SectionChange(keel, deltas(section_polars(spec, float(sec.get("tu", 0.1))), str(sec["foil"]), ref),
                                 chord=float(p["fin_mean_chord"]), span=kg["fin_span"],
                                 x=float(p["fin_x"]), z=kg["fin_z_root"] - 0.5 * kg["fin_span"], rho=water.rho,
                                 label=f"{sec['foil']} for {ref}, Tu {float(sec.get('tu', 0.1)):g} %")
    elif kmodel == "foil":
        fin = Foil(kg["fin_span"], float(p["fin_mean_chord"]), str(p["fin_section"]),
                   x=float(p["fin_x"]), z=kg["fin_z_root"] - 0.5 * kg["fin_span"], e=float(spec.get("keel.e", 0.9)),
                   rho=water.rho, nu=water.nu, name="keel")
        bulb = Bulb(kg["bulb_length"], kg["bulb_diameter"], bulb_wetted(kg), x=kg["bulb_x_cg"], z=kg["bulb_z_cg"],
                    rho=water.rho, nu=water.nu)
        comps.append(bulb)
        keel = fin
        cla = lift_slope(fin.aspect)
        hull_side = True
    else:
        raise ValueError(f"keel.model {kmodel}: keel3d or foil")
    side = spec.get("hull.side_force", "auto")
    hull = CanoeHull(cs, water.rho, water.nu, float(spec.get("hull.form_factor", 0.10)),
                     float(spec.get("hull.cf_factor", 1.0)), spec.get("hull.waves", "michell") == "michell",
                     hull_side if side == "auto" else bool(side), sink0=float(table.at(0.0, 0.0)["sink"]))
    aspect = 2 * kg["fin_span"] / float(p["fin_mean_chord"])
    eps = float(r.get("downwash", 1.0)) * 2 * cla / (math.pi * aspect)  # ε per unit leeway
    rudder = Foil(r_span, r_chord, str(r.get("section", "naca0008")), x=r_x, z=r_z, e=float(r.get("e", 0.9)),
                  downwash=eps, rudder=True, rho=water.rho, nu=water.nu, name="rudder")
    rig_spec = spec.get("rig") or {}
    if rig_spec.get("sails", "orc2026") != "orc2026":
        raise NotImplementedError(f"rig.sails {rig_spec.get('sails')}: only orc2026 so far")
    rig = sails_orc.iom_a_rig_geometry(mast_x=float(rig_spec.get("mast_x", 0.40)),
                                       deck=float(rig_spec.get("deck", 0.06)))
    sails = OrcSails(rig, z_wind=rig_centroid(rig), rho=air.rho, level=str(rig_spec.get("level", "low")))
    wd = spec.get("windage") or {}
    fb = float(wd.get("freeboard", cs.freeboard))
    windage = Windage(fb * cs.beam, fb * cs.length, freeboard=fb, beam=cs.beam, x=float(wd.get("x", 0.5)),
                      rho=air.rho)
    comps = [hull, keel, *comps, rudder, sails, windage]

    sv = spec.get("solver") or {}
    settings = Settings(yaw=bool(sv.get("yaw", True)), flat_min=float(sv.get("flat_min", 0.5)),
                        heel_max=float(sv.get("heel_max", 70.0)),
                        sailsets=SAILSETS if sv.get("jib_downwind", True) else ((0, 0.0),))
    boat = Boat(comps, righting, settings)

    w = spec.get("wind") or {}
    wts = w.get("weights", "uniform")
    if isinstance(wts, str) and wts.startswith("file:"):
        wind = WindRange.from_histogram(resolve_file(wts[5:], spec), float(w.get("z_ref", 1.0)),
                                        float(w.get("alpha", 0.0)))
    else:
        tws = [float(v) for v in w.get("tws", [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])]
        wind = WindRange(tws, [] if wts == "uniform" else [float(x) for x in wts], float(w.get("z_ref", 1.0)),
                         float(w.get("alpha", 0.0)))
    course = Course(**{k: float(v) if k != "laps" else int(v) for k, v in (spec.get("course") or {}).items()})

    info = {"mass_kg": round(budget.mass, 4), "cg": [round(float(c), 4) for c in budget.cg],
            "bulb_mass_kg": kg["bulb_mass_kg"], "bulb_z_cg": round(kg["bulb_z_cg"], 4),
            "fin_span": round(kg["fin_span"], 4), "keel": getattr(keel, "provenance", kmodel),
            "rudder_downwash_per_leeway": round(eps, 4), "rm_30deg_Nm": round(table.rm(30.0), 4)}
    return Built(spec, boat, wind, course, budget, kg, hydro, info, warnings)


def section_polars(spec: BoatSpec, tu: float):
    """The fin-section polar table at turbulence intensity `tu` [%] from
    keel.section.polars: {<tu>: {base: [csv], replace: [csv]}} (foil2d
    results.csv or their site/data copies; later files replace earlier
    points of the same section, speed and angle, as sectiondesign.cfd_table)."""
    from ..sectiondesign import cfd_table

    table = spec.get("keel.section.polars") or {}
    entry = next((v for k, v in table.items() if math.isclose(float(k), tu)), None)
    if entry is None:
        raise ValueError(f"keel.section.polars has no entry for Tu {tu:g} %")
    paths = lambda key: [resolve_file(str(f), spec) for f in entry.get(key) or []]  # noqa: E731
    return cfd_table(paths("base"), paths("replace"), tu=tu)


def foils_area(section: str) -> float:
    from ..geometry import foils

    return foils.load(section).area()


def bulb_wetted(kg: dict) -> float:
    """Wetted area of the bulb: keel3d's derived value when present, else a
    body of revolution's ~0.75 π d L (an estimate)."""
    return float(kg.get("bulb_wetted_area_m2") or 0.75 * math.pi * kg["bulb_diameter"] * kg["bulb_length"])


def resolve_file(ref: str, spec: BoatSpec) -> Path:
    for b in ([spec.path.parent] if spec.path else []) + [config.home()]:
        p = (b / ref).resolve()
        if p.exists():
            return p
    raise FileNotFoundError(ref)


def read_stl(ref: str) -> stl.Surface:  # pragma: no cover - for real hulls later
    return stl.read(config.geometry_dir() / ref)
