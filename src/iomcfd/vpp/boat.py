"""A boat definition (boats/<name>.yaml) and the solver-ready model built from it.

The boat file lists its parts under `components:`, each a shape and a force
model named by class (see boats/canoe-placeholder.yaml):

    <part>:
      class: .keel.ParametricKeel     # the shape ("." = iomcfd.vpp.components)
      mount: {host: hull, x: 0.50}    # where it hangs (the shape reads it)
      args: {...}                     # the shape's inputs
      forces: {class: .keel.PolarFit, args: {...}}
      controls: {<name>: <role> | {field: value}}   # override the part's controls
    windage:
      shape: hull                     # another part's shape (its mass counted there)
      forces: {...}

The builder knows no part by name: shapes and force models get a
`BuildContext` to read the environment and the parts they depend on
(`ctx.get`, `ctx.host`), built on first request. Then the hydrostatics of
the one shape with a surface(), the other parts' masses and buoyant
volumes, and each force model's finish(ctx). `--set a.b.c=value` overrides
any entry by its dotted path. Building does the slow work once: the
hydrostatic table (sinkage, trim and RM_φ over heel and pitch moment) and
the hull's wave-resistance table.
"""

from __future__ import annotations

import copy
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .. import config, physics
from . import cache
from . import mass as massmod
from .components.base import Part
from .hydrostatics import Hydrostatics, HydroTable
from .race import Course, WindRange
from .solver import Attitude, Boat, Settings

COMPONENTS = "iomcfd.vpp.components"


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


# ---------------------------------------------------------------------------
# righting from the hydrostatic table


def hydro_table(hydro: Hydrostatics, spec: BoatSpec) -> HydroTable:
    """The hydrostatic table over heel × M_ext × Z_ext (`hydrostatics.Z_ext`:
    the vertical-force layers [N]; one layer at 0 ignores the other parts'
    vertical forces), from the cache when it holds these inputs."""
    hmax, hstep = float(spec.get("hydrostatics.heel_max", 60.0)), float(spec.get("hydrostatics.heel_step", 2.5))
    grid = {"heels": np.arange(0.0, hmax + 1e-9, hstep), "M_ext": np.linspace(-2.0, 6.0, 9),
            "Z_ext": np.atleast_1d(np.asarray(spec.get("hydrostatics.Z_ext", 0.0), float))}

    def compute():
        t = hydro.table(**grid)
        return ({"component": "hydrostatics", "dims": ["heel", "M_ext", "Z_ext"]}, t.rows(),
                ["heel", "M_ext", "Z_ext", *HydroTable.KEYS, "converged"])

    parts = (hydro.hull, [(v, c) for v, c in hydro.appendages], hydro.mass, hydro.cg, hydro.rho, hydro.x_trim,
             grid["heels"], grid["M_ext"], grid["Z_ext"])
    return HydroTable.from_rows(cache.cached("hydro", parts, compute).rows)


@dataclass
class TableRighting:
    table: HydroTable
    solved: bool = True  # False: the attitude at M_ext = 0 and Z_ext = 0 (no trim or sinkage response)

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude:
        d = self.table.at(abs(heel), M_ext if self.solved else 0.0, Z_ext if self.solved else 0.0)
        sign = 1.0 if heel >= 0 else -1.0
        return Attitude(d["sink"], d["trim"], sign * d["rm"], bool(d.get("extrapolated", False)),
                        {"wetted_area": d["wetted_area"], "lwl": d["lwl"]})




# ---------------------------------------------------------------------------
# build


def resolve_class(path: str) -> type:
    """A class by dotted path; a leading "." is relative to iomcfd.vpp.components."""
    full = COMPONENTS + path if path.startswith(".") else path
    module, _, name = full.rpartition(".")
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"no class {path} ({e})") from None


class BuildContext:
    """What a part's shape and force model may ask for while the boat is built."""

    def __init__(self, spec: "BoatSpec", water: physics.Fluid, air: physics.Fluid):
        self.spec, self.water, self.air = spec, water, air
        self.warnings: list[str] = []
        self.parts: dict[str, Part] = {}
        self._stack: list[str] = []
        self.table: HydroTable | None = None  # set once the hydrostatics exist (finish)
        self.righting: Any = None
        self.budget: massmod.MassBudget | None = None
        self.hydro: Hydrostatics | None = None

    def get(self, name: str) -> Part:
        """Part `name`, built on first request."""
        if name in self.parts:
            return self.parts[name]
        if name in self._stack:
            raise ValueError(f"components: {' -> '.join([*self._stack, name])} is a cycle")
        e = self.spec.get(f"components.{name}")
        if not isinstance(e, dict):
            raise ValueError(f"components: no part {name}")
        self._stack.append(name)
        try:
            owner = "shape" not in e
            if owner:
                shape = resolve_class(str(e["class"])).build(self, name, mount=e.get("mount"), **(e.get("args") or {}))
            else:
                shape = self.get(str(e["shape"])).shape
            f = e.get("forces") or {}
            if "class" not in f:
                raise ValueError(f"components.{name}: no forces.class")
            forces = resolve_class(str(f["class"])).build(self, name, shape, **(f.get("args") or {}))
            ctl = {c.name: c for c in (*(getattr(shape, "controls", ()) if owner else ()),
                                       *getattr(forces, "controls", ()))}
            for k, v in (e.get("controls") or {}).items():
                if k not in ctl:
                    raise ValueError(f"components.{name}: no control {k} (it has {list(ctl) or 'none'})")
                ctl[k] = ctl[k].override(v)
            part = Part(name, shape, forces, tuple(ctl.values()), owner)
        finally:
            self._stack.pop()
        self.parts[name] = part
        return part

    def host(self, mount: dict | None) -> Any:
        """The shape a part hangs from: `mount: {host: <part>, ...}`."""
        if not mount or "host" not in mount:
            raise ValueError(f"{self._stack[-1]}: needs mount: {{host: <part>, x: ...}}")
        return self.get(str(mount["host"])).shape

    def covered(self, what: str) -> bool:
        """Whether some part's loads already hold `what` (e.g. "hull.side_force")."""
        return any(what in p.covers for p in self.parts.values())

    def resolve(self, ref: str) -> Path:
        """A file named in the boat file: relative to it, then to the repo root."""
        for b in ([self.spec.path.parent] if self.spec.path else []) + [config.home()]:
            p = (b / ref).resolve()
            if p.exists():
                return p
        raise FileNotFoundError(ref)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


@dataclass
class Built:
    """A built boat and what it was built from."""

    spec: BoatSpec
    boat: Boat
    wind: WindRange
    course: Course
    mass: massmod.MassBudget
    table: HydroTable
    hydro: Hydrostatics
    info: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def build(spec: BoatSpec, table: HydroTable | None = None) -> Built:
    water = physics.fresh_water(float(spec.get("water.temperature", 15.0)))
    air = physics.air(float(spec.get("air.temperature", 15.0)))
    ctx = BuildContext(spec, water, air)
    names = list(spec.get("components") or {})
    if not names:
        raise ValueError(f"{spec.path}: no components")
    parts = [ctx.get(n) for n in names]

    # --- mass and hydrostatics -----------------------------------------------
    items = massmod.MassBudget.from_list(spec.get("mass.items") or [])
    budget = massmod.MassBudget([*(i for p in parts for i in p.mass_items()), *items.items])
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
    floating = [p for p in parts if p.owner and hasattr(p.shape, "surface")]
    if len(floating) != 1:
        raise ValueError(f"components: {len(floating)} parts with a floating surface ({[p.name for p in floating]}); "
                         "one hull")
    hydro = Hydrostatics(floating[0].shape.surface(), [v for p in parts for v in p.volumes()], mass=budget.mass,
                         cg=budget.cg, rho=water.rho)
    if table is None:
        table = hydro_table(hydro, spec)
    righting = TableRighting(table, spec.get("hydrostatics.attitude", "solved") == "solved")
    ctx.table, ctx.righting, ctx.budget, ctx.hydro = table, righting, budget, hydro
    rules = [massmod.mass_rule(budget.mass)]
    for p in parts:
        if p.owner and hasattr(p.shape, "rules"):
            rules += p.shape.rules()
    for rr in rules:
        if not rr.ok:
            ctx.warn(f"class rule {rr.clause} ({rr.quantity}) fails: {rr.value:.4g} not in [{rr.lo}, {rr.hi}]")
    for p in parts:
        if hasattr(p.forces, "finish"):
            p.forces.finish(ctx)

    sv = spec.get("solver") or {}
    settings = Settings(yaw=bool(sv.get("yaw", True)), optimise=bool(sv.get("optimise", True)),
                        heel_max=float(sv.get("heel_max", 70.0)), leeway_max=float(sv.get("leeway_max", 15.0)))
    boat = Boat(parts, righting, settings)

    w = spec.get("wind") or {}
    wts = w.get("weights", "uniform")
    if isinstance(wts, str) and wts.startswith("file:"):
        wind = WindRange.from_histogram(ctx.resolve(wts[5:]), float(w.get("z_ref", 1.0)), float(w.get("alpha", 0.0)))
    else:
        tws = [float(v) for v in w.get("tws", [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])]
        wind = WindRange(tws, [] if wts == "uniform" else [float(x) for x in wts], float(w.get("z_ref", 1.0)),
                         float(w.get("alpha", 0.0)))
    course = Course(**{k: float(v) if k != "laps" else int(v) for k, v in (spec.get("course") or {}).items()})

    info = {"mass_kg": round(budget.mass, 4), "cg": [round(float(c), 4) for c in budget.cg]}
    info |= {f"{p.name}.{k}": v for p in parts for k, v in p.info().items()}
    info["rm_30deg_Nm"] = round(table.rm(30.0), 4)
    return Built(spec, boat, wind, course, budget, table, hydro, info, ctx.warnings)
