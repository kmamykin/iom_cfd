"""Windage of the hull above the water (topsides and deck; the mast and
rigging are in the sail model): pure drag along the apparent wind, after ORC
2026 §5.4 (Table 5.12, eq. 5.27-5.30): C_D·A = C_D (A_front |cos β| +
A_side sin β) with C_D 0.816, at 0.66 (freeboard + B sin φ) above the
waterline. ORC's areas: freeboard × beam ahead, heeled freeboard × LOA abeam.

A force model on the hull's shape (`shape: hull` in the boat file): beam,
length and, unless given, freeboard come from its dimensions().
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .. import frames
from .base import Loads, State, Wind


@dataclass
class OrcWindage:
    front_area: float  # m², freeboard × beam
    side_area: float  # m², freeboard × length
    freeboard: float = 0.06  # m, mean
    beam: float = 0.165  # m
    cd: float = 0.816  # ORC Table 5.12
    x: float = 0.5  # m aft of the bow
    rho: float = 1.225
    name: str = "windage"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()

    @classmethod
    def build(cls, ctx, name: str, shape, *, cd: float = 0.816, freeboard: float | None = None,
              x: float = 0.5) -> "OrcWindage":
        d = shape.dimensions()
        fb = float(d["freeboard"] if freeboard is None else freeboard)
        return cls(fb * d["beam"], fb * d["length"], freeboard=fb, beam=d["beam"], cd=float(cd), x=float(x),
                   rho=ctx.air.rho, name=name)

    def loads(self, s: State, w: Wind) -> Loads:
        p = math.radians(s.heel)
        z = 0.66 * (self.freeboard + self.beam * math.sin(abs(p)))
        aws, awa = w.apparent(s.V, z)
        a = math.radians(awa)  # from the course: the force points downwind
        side = self.side_area * (1 + self.beam * math.sin(abs(p)) / max(self.freeboard, 1e-6))  # heeled topsides
        D = 0.5 * self.rho * aws**2 * self.cd * (self.front_area * abs(math.cos(a)) + side * abs(math.sin(a)))
        return Loads.at(frames.heeled_point(self.x, 0.0, z, 0.0), X=-D * math.cos(a), Y=-D * math.sin(a),
                        info={"D": D})
