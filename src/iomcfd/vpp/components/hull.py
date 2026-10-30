"""The hull: its shape (the parametric canoe body, or any closed mesh) and
its resistance, side force and yaw moment (rung 0, `IttcMichell`).

Friction: ITTC-57 × (1 + k) on the wetted area at the solved attitude (heel,
sinkage, trim; from the hydrostatics). Waves: Michell's thin-ship integral
on the hull's offsets, tabulated once the hydrostatics exist (cached, see
vpp/cache.py): `michell` on the upright hull at its static sinkage
(`sink0`, so the boat's mass counts) over V_b and trim; `michell-heeled`
also over heel, each heel at its own static sinkage, with the heeled
sections' half-widths as the centreplane offsets (hullres.surface_offsets;
thin-ship theory has no heel, so this is an estimate, and above 45° it is
held and flagged). Side force: Jones' slender-body estimate at the keel
line's centre of pressure, off when another part's loads already hold the
hull's share (keel3d is a double body of hull, fin and bulb).
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import RectBivariateSpline

from ... import config
from ...geometry import hulls, stl
from ...geometry.hulls import CanoeSpec, canoe_depth, canoe_displacement
from .. import cache, frames, hullres, tables
from ..hydrostatics import submerged
from .base import Loads, State, Wind


@dataclass
class CanoeHull:
    """The parametric canoe body (geometry/hulls.py CanoeSpec): the floating
    surface, the bottom other parts hang from and the topsides."""

    spec: CanoeSpec
    controls: tuple = ()
    _surface: object = field(default=None, repr=False)

    @classmethod
    def build(cls, ctx, name: str, mount: dict | None = None, *, params: dict | None = None) -> "CanoeHull":
        return cls(CanoeSpec(**(params or {})))

    def surface(self):
        if self._surface is None:
            self._surface = hulls.canoe(self.spec)
        return self._surface

    def depth_at(self, x: float) -> float:
        """The bottom below the waterline at x (clamped to the hull) [m]."""
        return float(canoe_depth(self.spec, min(max(x, 0.0), self.spec.length)))

    def params(self) -> dict:
        """keel3d's names for the canoe body (hull_*)."""
        return {f"hull_{k}": v for k, v in dataclasses.asdict(self.spec).items()}

    def dimensions(self) -> dict:
        return {"length": self.spec.length, "beam": self.spec.beam, "freeboard": self.spec.freeboard}

    # what the force model asks
    @property
    def draft(self) -> float:
        return self.spec.draft

    @property
    def length(self) -> float:
        return self.spec.length

    def displacement(self) -> tuple[float, float, float]:
        """(volume, LCB, wetted area) upright at the design waterline."""
        return canoe_displacement(self.spec)

    def offsets(self, sink: float, trim: float, heel: float = 0.0):
        if heel:
            return hullres.surface_offsets(self.surface(), sink, trim, heel=heel)
        return hullres.canoe_offsets(self.spec, sink=sink, trim=trim)

    def jones(self, V: float, leeway: float, rho: float, volume: float) -> tuple[float, float]:
        S, x_cp, _ = hullres.hull_side_yaw(V, leeway, self.spec.draft, self.spec.length, volume, rho)
        return S, x_cp

    def key(self) -> dict:
        return {"canoe": dataclasses.asdict(self.spec)}


@dataclass
class MeshHull:
    """A hull from its surface: an STL file (`stl`, found next to the boat
    file, in the repo or in config.geometry_dir(); `scale`, `rotate` [[axis,
    deg], ...] and `translate` [m] map it to the boat frame: bow at x = 0,
    design waterline z = 0) or the canoe body as a mesh (`canoe: {CanoeSpec
    fields}`). It must be the hull alone, closed and outward: the rig's
    windage is the sail model's."""

    mesh: stl.Surface
    source: dict
    controls: tuple = ()
    _x: np.ndarray = field(default=None, repr=False)  # stations of the keel line
    _T: np.ndarray = field(default=None, repr=False)

    @classmethod
    def build(cls, ctx, name: str, mount: dict | None = None, *, stl: str | None = None, scale: float = 1.0,
              rotate: list | None = None, translate: list | None = None, canoe: dict | None = None) -> "MeshHull":
        ref = stl
        if (ref is None) == (canoe is None):
            raise ValueError(f"{name}: give stl or canoe")
        if canoe is not None:
            return cls(hulls.canoe(CanoeSpec(**canoe)), {"canoe": dict(canoe)})
        from ...geometry import stl as stlmod

        try:
            path = ctx.resolve(ref)
        except FileNotFoundError:
            path = config.geometry_dir() / ref
            if not path.is_file():
                where = [str(ctx.spec.path.parent)] if ctx.spec.path else []
                raise FileNotFoundError(f"{name}: no {ref} next to the boat file, in the repo or in the geometry "
                                        f"directory ({', '.join([*where, str(config.home()), str(config.geometry_dir())])}); "
                                        "private hull lines go in boats/private/, which git ignores") from None
        s = stlmod.read(path).scaled(float(scale))
        for axis, deg in rotate or []:
            s = s.rotated(str(axis), float(deg))
        if translate:
            s = s.translated(tuple(float(v) for v in translate))
        if not s.is_closed():
            raise ValueError(f"{name}: {ref} is not a closed surface")
        return cls(s.oriented_outward(), {"stl": str(ref), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                          "scale": scale, "rotate": rotate, "translate": translate})

    def __post_init__(self):
        lo, hi = self.mesh.bounds
        self._x = np.linspace(float(lo[0]), float(hi[0]), 401)
        self._T = hullres.keel_line(self.mesh, self._x)

    def surface(self):
        return self.mesh

    def depth_at(self, x: float) -> float:
        """The bottom below the waterline at x, from the keel line on 401
        stations (clamped to the hull) [m]."""
        return float(np.interp(x, self._x, self._T))

    def params(self) -> dict:
        if "canoe" in self.source:
            return {f"hull_{k}": v for k, v in dataclasses.asdict(CanoeSpec(**self.source["canoe"])).items()}
        return {"hull_mesh_sha256": self.source["sha256"]}

    def dimensions(self) -> dict:
        lo, hi = self.mesh.bounds
        return {"length": float(hi[0] - lo[0]), "beam": float(hi[1] - lo[1]), "freeboard": float(hi[2])}

    @property
    def draft(self) -> float:
        return float(self._T.max())

    @property
    def length(self) -> float:
        return submerged(self.mesh).lwl

    def displacement(self) -> tuple[float, float, float]:
        sub = submerged(self.mesh)
        return sub.volume, float(sub.centroid[0]), sub.wetted_area

    def offsets(self, sink: float, trim: float, heel: float = 0.0):
        return hullres.surface_offsets(self.mesh, sink, trim, heel=heel)

    def jones(self, V: float, leeway: float, rho: float, volume: float) -> tuple[float, float]:
        return hullres.jones_keel_line(V, leeway, self._x, self._T, rho)

    def key(self):
        return self.mesh


@dataclass
class IttcMichell:
    hull: object  # the shape: CanoeHull or MeshHull
    rho: float = 999.1
    nu: float = 1.137e-6
    form_factor: float = 0.10
    cf_factor: float = 1.0
    waves: str = "michell"  # michell | michell-heeled | none
    side_force: bool | str = True  # "auto": off when another part covers <name>.side_force
    sink0: float = 0.0  # upright static sinkage at the boat's mass [m], + down
    V_grid: tuple = tuple(np.round(np.arange(0.1, 4.01, 0.1), 3))
    trim_grid: tuple = (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0)
    heel_grid: tuple = tuple(np.arange(0.0, 45.1, 5.0))  # michell-heeled
    name: str = "hull"
    kind: str = "hydro"
    attitude: bool = True
    controls: tuple = ()
    covers: frozenset = frozenset()
    sinks: tuple = ()  # michell-heeled: the static sinkage at each heel [m]
    _rw: object = field(default=None, repr=False)

    @classmethod
    def build(cls, ctx, name: str, shape, *, form_factor: float = 0.10, cf_factor: float = 1.0,
              waves: str = "michell", side_force: bool | str = "auto") -> "IttcMichell":
        """waves: michell | michell-heeled | none. form_factor (1 + k) − 1;
        cf_factor < 1 brackets a laminar run."""
        if waves not in ("michell", "michell-heeled", "none"):
            raise ValueError(f"{name}: waves {waves}: michell, michell-heeled or none")
        return cls(shape, ctx.water.rho, ctx.water.nu, float(form_factor), float(cf_factor), waves, side_force,
                   name=name)

    def finish(self, ctx) -> None:
        """Once the hydrostatics exist: the static sinkage for the waves, and
        whether the side force is someone else's."""
        if self.side_force == "auto":
            self.side_force = not ctx.covered(f"{self.name}.side_force")
        self.sink0 = float(ctx.table.at(0.0, 0.0)["sink"])
        if self.waves == "michell-heeled":
            self.sinks = tuple(float(ctx.table.at(float(h), 0.0)["sink"]) for h in self.heel_grid)
        self._rw = None
        self.wave_table()

    def __post_init__(self):
        vol, self._lcb, self._wetted = self.hull.displacement()
        self._volume = vol

    def wave_table(self):
        """Michell's R_w on the grid (built once, cached)."""
        if self._rw is None and self.waves != "none":
            V, T = np.asarray(self.V_grid, float), np.asarray(self.trim_grid, float)
            if self.waves == "michell":
                def compute():
                    rows = []
                    for t in T:
                        x, z, y = self.hull.offsets(self.sink0, float(t))
                        rows += [{"V": float(v), "trim": float(t), "Rw": hullres.michell(x, z, y, v, rho=self.rho)}
                                 for v in V]
                    return {"component": "hull waves", "dims": ["V", "trim"]}, rows, ["V", "trim", "Rw"]

                t = cache.cached("waves", (self.hull.key(), self.rho, V, T, self.sink0), compute)
                R = {(r["V"], r["trim"]): r["Rw"] for r in t.rows}
                grid = np.array([[R[(float(v), float(tt))] for tt in T] for v in V])
                self._rw = RectBivariateSpline(V, T, grid, kx=3, ky=min(3, len(T) - 1))
            else:
                H = np.asarray(self.heel_grid, float)

                def compute():
                    rows = []
                    for h, sk in zip(H, self.sinks):
                        for t in T:
                            x, z, y = self.hull.offsets(sk, float(t), heel=float(h))
                            rows += [{"heel": float(h), "V": float(v), "trim": float(t),
                                      "Rw": hullres.michell(x, z, y, v, rho=self.rho)} for v in V]
                    return ({"component": "hull waves", "dims": ["heel", "V", "trim"]}, rows,
                            ["heel", "V", "trim", "Rw"])

                t = cache.cached("waves", (self.hull.key(), self.rho, H, V, T, list(self.sinks)), compute)
                R = {(r["heel"], r["V"], r["trim"]): r["Rw"] for r in t.rows}
                grid = np.array([[[R[(float(h), float(v), float(tt))] for tt in T] for v in V] for h in H])
                self._rw = tables.Grid([H, V, T], grid)
        return self._rw

    def wave_resistance(self, V: float, trim: float, heel: float = 0.0) -> tuple[float, bool]:
        if self.waves == "none":
            return 0.0, False
        V_lo, V_hi, t_lo, t_hi = self.V_grid[0], self.V_grid[-1], self.trim_grid[0], self.trim_grid[-1]
        out = not (V_lo <= V <= V_hi and t_lo <= trim <= t_hi)
        Vc, tc = min(max(V, V_lo), V_hi), min(max(trim, t_lo), t_hi)
        if self.waves == "michell":
            R = max(float(self.wave_table()(Vc, tc)[0, 0]), 0.0)
        else:
            r, o = self.wave_table()(abs(heel), Vc, tc)
            R, out = max(float(r), 0.0), out or o
        if V < V_lo:  # waves vanish as V -> 0
            R *= (V / V_lo) ** 6
            out = False
        return R, out

    def loads(self, s: State, w: Wind) -> Loads:
        S = s.hydro.get("wetted_area", math.nan)
        L = s.hydro.get("lwl", math.nan)
        S = S if math.isfinite(S) else self._wetted
        L = L if math.isfinite(L) else self.hull.length
        Rf = hullres.friction_resistance(s.V, S, L, self.nu, self.rho, self.form_factor, self.cf_factor)
        Rw, out = self.wave_resistance(s.V, s.trim, s.heel)
        z_d = -0.4 * self.hull.draft  # drag centre: about the wetted area's centroid depth
        ld = Loads.at(frames.heeled_point(self._lcb, 0.0, z_d, s.heel), X=-(Rf + Rw), extrapolated=out)
        if self.side_force is True and s.V > 0:
            # Jones' side force at its centre of pressure; the Munk moment is the
            # other idealisation of the same flow, so it is not added (hullres)
            Sh, x_cp = self.hull.jones(s.V, s.leeway, self.rho, self._volume)
            ld = ld + Loads.at(frames.heeled_point(x_cp, 0.0, z_d, s.heel), Y=Sh)
        ld.info.update({"Rf": Rf, "Rw": Rw, "wetted": S})
        return ld

    def info(self) -> dict:
        return {"side_force": self.side_force is True}
