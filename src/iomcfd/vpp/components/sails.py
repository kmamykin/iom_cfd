"""Sail forces in the course frame from a sail-coefficient model (v1: the ORC
2026 coefficients, sails_orc.py; full-scale, flagged there).

The apparent wind is taken at the rig's area centroid height (the wind
profile's twist over the rig is ignored), turned into the heeled rig's plane
(frames.heeled_wind), and the sails' lift and drag (with mast and rigging
windage) go back to the course frame at the heeled centre of effort.
State.sailset 0 is the jib set, 1 ORC's "jib downwind" set standing in for
the goose-winged jib (sails_orc: allowed from β_TW 60°; the solver keeps the
faster).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .. import frames, sails_orc
from .base import Loads, State, Wind

SAILSETS = ((0, 0.0), (1, 60.0))  # (set, lowest β_TW): ORC §5.2.2 uses the jib downwind set from 60°
SET_NAMES = {0: "upwind", 1: "downwind"}


@dataclass
class OrcSails:
    rig: sails_orc.Rig
    z_wind: float = 0.66  # height the apparent wind is evaluated at, upright [m]
    rho: float = 1.225
    level: str = "low"  # ORC coefficient set (§5.1.2: low since 2026)
    name: str = "sails"
    kind: str = "aero"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        z = self.z_wind * max(math.cos(math.radians(s.heel)), 0.05)
        aws, awa = w.apparent(s.V, z)
        aws_e, awa_e = frames.heeled_wind(aws, awa, s.leeway, s.heel)
        f = sails_orc.forces(self.rig, aws_e, awa_e, flat=s.flat, rho=self.rho, sails=SET_NAMES[s.sailset],
                             level=self.level)
        drive, heel_force = frames.lift_drag_to_centreline(f.L, f.D, awa_e)
        X, Y, Z = frames.rig_to_course(drive, heel_force, s.heel, s.leeway)
        ld = Loads.at(frames.heeled_point(f.x_ce, 0.0, f.z_ce, s.heel), X=X, Y=Y, Z=Z)
        ld.info.update({"aws": aws, "awa": awa, "awa_eff": awa_e, "CL": f.CL, "CD": f.CD, "z_ce": f.z_ce,
                        "x_ce": f.x_ce, "drive": drive, "heel_force": heel_force})
        return ld


def rig_centroid(rig: sails_orc.Rig) -> float:
    """Area-weighted height of main and jib above the waterline [m]."""
    return (rig.A_main * rig.z_main + rig.A_jib * rig.z_jib) / (rig.A_main + rig.A_jib)
