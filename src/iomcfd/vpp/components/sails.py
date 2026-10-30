"""The rig (the shape) and its sail forces in the course frame from a
sail-coefficient model (v1: the ORC 2026 coefficients, sails_orc.py;
full-scale, flagged there).

The apparent wind is taken at the rig's area centroid height (the wind
profile's twist over the rig is ignored), turned into the heeled rig's plane
(frames.heeled_wind), and the sails' lift and drag (with mast and rigging
windage) go back to the course frame at the heeled centre of effort.

Controls: `flat` (ORC's depowering, optimised between its bounds) and `set`
(which of the `sets` is up: the jib set, or ORC's "jib downwind" set
standing in for the goose-winged jib, allowed from β_TW 60°; the solver
keeps the faster).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .. import frames, sails_orc
from .base import Control, Loads, State, Wind

SETS = {"upwind": 0.0, "downwind": 60.0}  # ORC set: lowest β_TW (§5.2.2 uses the jib downwind set from 60°)


def rig_centroid(rig: sails_orc.Rig) -> float:
    """Area-weighted height of main and jib above the waterline [m]."""
    return (rig.A_main * rig.z_main + rig.A_jib * rig.z_jib) / (rig.A_main + rig.A_jib)


@dataclass
class Rig:
    """The IOM A rig (geometry/sails.py) as an ORC `Rig`."""

    rig: sails_orc.Rig
    controls: tuple = ()

    @classmethod
    def build(cls, ctx, name: str, mount: dict | None = None, *, rig: str = "iom_a", main_tack: list | None = None,
              jib_tack: list | None = None, sheer: float | None = None) -> "Rig":
        """main_tack [x, y, z]: where the boom meets the mast (default
        geometry/sails.py's, on a flat deck 0.06 m up); jib_tack and sheer
        (the deck at the mast) default from it (sails_orc.iom_a_rig_geometry)."""
        if rig != "iom_a":
            raise NotImplementedError(f"{name}: rig {rig}: only iom_a so far")
        return cls(sails_orc.iom_a_rig_geometry(sails_orc.MAIN_TACK if main_tack is None else main_tack, jib_tack,
                                                None if sheer is None else float(sheer)))


@dataclass
class OrcSails:
    rig: sails_orc.Rig
    z_wind: float = 0.66  # height the apparent wind is evaluated at, upright [m]
    rho: float = 1.225
    level: str = "low"  # ORC coefficient set (§5.1.2: low since 2026)
    sets: tuple = tuple(SETS)  # ORC set names, by the `set` control's value
    name: str = "sails"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()

    @classmethod
    def build(cls, ctx, name: str, shape, *, level: str = "low", sets: dict | None = None) -> "OrcSails":
        """sets {ORC set: lowest β_TW [deg]}, in the order of the `set`
        control's values (default: upwind from 0°, downwind from 60°)."""
        sets = dict(SETS if sets is None else sets)
        options = tuple((float(i), float(a)) for i, a in enumerate(sets.values()))
        controls = (Control("flat", "optimise", 1.0, lo=0.5, hi=1.0), Control("set", "choice", 0.0, options=options))
        return cls(shape.rig, z_wind=rig_centroid(shape.rig), rho=ctx.air.rho, level=str(level), sets=tuple(sets),
                   name=name, controls=controls)

    def loads(self, s: State, w: Wind) -> Loads:
        z = self.z_wind * max(math.cos(math.radians(s.heel)), 0.05)
        aws, awa = w.apparent(s.V, z)
        aws_e, awa_e = frames.heeled_wind(aws, awa, s.leeway, s.heel)
        f = sails_orc.forces(self.rig, aws_e, awa_e, flat=s.controls.get(f"{self.name}.flat", 1.0), rho=self.rho,
                             sails=self.sets[int(s.controls.get(f"{self.name}.set", 0))], level=self.level)
        drive, heel_force = frames.lift_drag_to_centreline(f.L, f.D, awa_e)
        X, Y, Z = frames.rig_to_course(drive, heel_force, s.heel, s.leeway)
        ld = Loads.at(frames.heeled_point(f.x_ce, 0.0, f.z_ce, s.heel), X=X, Y=Y, Z=Z)
        ld.info.update({"aws": aws, "awa": awa, "awa_eff": awa_e, "CL": f.CL, "CD": f.CD, "z_ce": f.z_ce,
                        "x_ce": f.x_ce, "drive": drive, "heel_force": heel_force})
        return ld
