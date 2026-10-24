"""What every force model gives the solver.

A component (hull, keel, rudder, sails, windage) maps the boat's state and
the wind to `Loads`: forces in the course frame and moments about the boat
frame origin (bow, waterline, centreline), with the signs of the balance
equations in docs/nomenclature.md (port tack):

    X  along the course, + forward      (T_a = X_aero, D_h = −X_hydro)
    Y  across the course, + to windward (S_h = Y_hydro, S_a = −Y_aero)
    Z  vertical, + up
    K  roll, + heels to starboard        (M_a, M_h,dyn)
    M  pitch, + bow down
    N  yaw, + bow to port (to windward)  (N_a, N_h)

The steady state is ΣX = 0, ΣY = 0, ΣK = RM_φ and ΣN = 0; ΣZ and ΣM set
sinkage and trim through the hydrostatics. Moment arms ignore the small
rotation of the boat by the leeway (cos β_Y ≈ 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Protocol

from .. import frames


@dataclass(frozen=True)
class State:
    V: float  # V_b, boat speed through the water [m/s]
    heel: float = 0.0  # φ [deg], + to starboard
    leeway: float = 0.0  # β_Y [deg], + bow to port
    rudder: float = 0.0  # δ_R [deg], + trailing edge to port
    flat: float = 1.0  # sail flattening, 1 = full power (ORC)
    twist: float = 0.0  # sail twist variable (meaning set by the sail model)
    sailset: int = 0  # which sail set is up (the sail model names them; ORC: 0 jib, 1 jib downwind)
    sink: float = 0.0  # sinkage [m], + down
    trim: float = 0.0  # trim [deg], + bow down
    wetted: float = math.nan  # hull wetted area at this attitude [m²] (from the hydrostatics)
    lwl: float = math.nan  # waterline length at this attitude [m]

    def but(self, **kw) -> "State":
        return replace(self, **kw)


@dataclass(frozen=True)
class Wind:
    tws: float  # V_TW at the reference height [m/s]
    twa: float  # β_TW from the course [deg]
    z_ref: float = 1.0  # height of tws [m]
    alpha: float = 0.0  # power-law profile exponent (0 = uniform)

    def tws_at(self, z: float) -> float:
        return frames.wind_at(self.tws, z, self.z_ref, self.alpha)

    def apparent(self, V: float, z: float | None = None) -> tuple[float, float]:
        """(V_AW, β_AW from the course) at height z (the reference height if None)."""
        return frames.apparent_wind(self.tws if z is None else self.tws_at(z), self.twa, V)


@dataclass
class Loads:
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    K: float = 0.0
    M: float = 0.0
    N: float = 0.0
    extrapolated: bool = False  # a table was read outside its range
    info: dict = field(default_factory=dict)  # model-specific outputs (z_ce, aws, ...)

    @staticmethod
    def at(point: tuple[float, float, float], X: float = 0.0, Y: float = 0.0, Z: float = 0.0, **kw) -> "Loads":
        """A force (course frame) acting at `point` (boat frame, already heeled)."""
        x, y, z = point
        return Loads(X, Y, Z, K=y * Z - z * Y, M=z * X + x * Z, N=-x * Y - y * X, **kw)

    def __add__(self, o: "Loads") -> "Loads":
        return Loads(self.X + o.X, self.Y + o.Y, self.Z + o.Z, self.K + o.K, self.M + o.M, self.N + o.N,
                     self.extrapolated or o.extrapolated, {**self.info, **o.info})

    def scaled(self, f: float) -> "Loads":
        return Loads(f * self.X, f * self.Y, f * self.Z, f * self.K, f * self.M, f * self.N, self.extrapolated,
                     dict(self.info))

    def finite(self) -> bool:
        return all(math.isfinite(v) for v in (self.X, self.Y, self.Z, self.K, self.M, self.N))


class Component(Protocol):
    name: str
    kind: str  # "hydro" or "aero"
    attitude: bool  # its loads depend on sinkage and trim (the hull)

    def loads(self, s: State, w: Wind) -> Loads: ...
