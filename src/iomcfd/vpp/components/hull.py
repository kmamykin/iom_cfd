"""The hull: the canoe body (the shape) and its resistance, side force and
yaw moment (rung 0, `IttcMichell`).

Friction: ITTC-57 × (1 + k) on the wetted area at the solved attitude (heel,
sinkage, trim; from the hydrostatics). Waves: Michell's thin-ship integral
on the upright hull at its static sinkage (`sink0`, so the boat's mass
counts) and its trim, tabulated over V_b and trim once the hydrostatics
exist (heel's effect on the waves is ignored). Side force and Munk moment:
slender-body estimates, off when another part's loads already hold the
hull's share (keel3d is a double body of hull, fin and bulb).
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import RectBivariateSpline

from ...geometry import hulls
from ...geometry.hulls import CanoeSpec, canoe_depth, canoe_displacement
from .. import frames, hullres
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


@dataclass
class IttcMichell:
    spec: CanoeSpec
    rho: float = 999.1
    nu: float = 1.137e-6
    form_factor: float = 0.10
    cf_factor: float = 1.0
    waves: bool = True
    side_force: bool | str = True  # "auto": off when another part covers <name>.side_force
    sink0: float = 0.0  # upright static sinkage at the boat's mass [m], + down
    V_grid: tuple = tuple(np.round(np.arange(0.1, 3.01, 0.1), 3))
    trim_grid: tuple = (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
    name: str = "hull"
    kind: str = "hydro"
    attitude: bool = True
    controls: tuple = ()
    covers: frozenset = frozenset()
    _rw: RectBivariateSpline | None = field(default=None, repr=False)

    @classmethod
    def build(cls, ctx, name: str, shape, *, form_factor: float = 0.10, cf_factor: float = 1.0,
              waves: str = "michell", side_force: bool | str = "auto") -> "IttcMichell":
        """waves: michell | none. form_factor (1 + k) − 1; cf_factor < 1
        brackets a laminar run."""
        if waves not in ("michell", "none"):
            raise ValueError(f"{name}: waves {waves}: michell or none")
        return cls(shape.spec, ctx.water.rho, ctx.water.nu, float(form_factor), float(cf_factor), waves == "michell",
                   side_force, name=name)

    def finish(self, ctx) -> None:
        """Once the hydrostatics exist: the static sinkage for the waves, and
        whether the side force is someone else's."""
        if self.side_force == "auto":
            self.side_force = not ctx.covered(f"{self.name}.side_force")
        self.sink0 = float(ctx.table.at(0.0, 0.0)["sink"])
        self._rw = None
        self.wave_table()

    def __post_init__(self):
        vol, self._lcb, self._wetted = canoe_displacement(self.spec)
        self._volume = vol

    def wave_table(self) -> RectBivariateSpline:
        """Michell's R_w over V_grid × trim_grid at sink0 (built once)."""
        if self._rw is None:
            V, T = np.asarray(self.V_grid, float), np.asarray(self.trim_grid, float)
            R = np.empty((len(V), len(T)))
            for j, t in enumerate(T):
                x, z, y = hullres.canoe_offsets(self.spec, sink=self.sink0, trim=t)
                for i, v in enumerate(V):
                    R[i, j] = hullres.michell(x, z, y, v, rho=self.rho)
            self._rw = RectBivariateSpline(V, T, R, kx=3, ky=min(3, len(T) - 1))
        return self._rw

    def wave_resistance(self, V: float, trim: float) -> tuple[float, bool]:
        if not self.waves:
            return 0.0, False
        V_lo, V_hi, t_lo, t_hi = self.V_grid[0], self.V_grid[-1], self.trim_grid[0], self.trim_grid[-1]
        out = not (V_lo <= V <= V_hi and t_lo <= trim <= t_hi)
        Vc, tc = min(max(V, V_lo), V_hi), min(max(trim, t_lo), t_hi)
        R = max(float(self.wave_table()(Vc, tc)[0, 0]), 0.0)
        if V < V_lo:  # waves vanish as V -> 0
            R *= (V / V_lo) ** 6
            out = False
        return R, out

    def loads(self, s: State, w: Wind) -> Loads:
        S = s.hydro.get("wetted_area", math.nan)
        L = s.hydro.get("lwl", math.nan)
        S = S if math.isfinite(S) else self._wetted
        L = L if math.isfinite(L) else self.spec.length
        Rf = hullres.friction_resistance(s.V, S, L, self.nu, self.rho, self.form_factor, self.cf_factor)
        Rw, out = self.wave_resistance(s.V, s.trim)
        z_d = -0.4 * self.spec.draft  # drag centre: about the wetted area's centroid depth
        ld = Loads.at(frames.heeled_point(self._lcb, 0.0, z_d, s.heel), X=-(Rf + Rw), extrapolated=out)
        if self.side_force is True and s.V > 0:
            # Jones' side force at its centre of pressure; the Munk moment is the
            # other idealisation of the same flow, so it is not added (hullres)
            Sh, x_cp, _ = hullres.hull_side_yaw(s.V, s.leeway, self.spec.draft, self.spec.length, self._volume,
                                                self.rho)
            ld = ld + Loads.at(frames.heeled_point(x_cp, 0.0, z_d, s.heel), Y=Sh)
        ld.info.update({"Rf": Rf, "Rw": Rw, "wetted": S})
        return ld

    def info(self) -> dict:
        return {"side_force": self.side_force is True}
