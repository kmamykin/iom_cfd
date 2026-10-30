"""A lifting surface below the hull: its planform (the shape) and its forces
from lifting-line theory (rung 0, no CFD).

`LiftingLine`: lift slope from Helmbold's low-aspect-ratio formula on the
hull-mirrored aspect ratio, lifting-line induced drag (physics.induced_drag,
hull as a reflection plane), profile drag from ITTC-57 friction and a
thickness form factor. No stall: points beyond `alpha_max` are flagged.

Heel: a fin's lift is normal to its heeled plane (horizontal part L cos φ,
vertical L sin φ) and it sees the leeway as β_Y cos φ. The foil's `angle`
control (the rudder angle δ_R, + = trailing edge to port) lowers its angle
of attack: α = (β_Y − δ_R) cos φ − ε, with ε the keel's downwash at the
rudder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ... import physics
from ...geometry import foils
from .. import frames
from ..hullres import ittc57
from .base import Control, Loads, State, Wind


def lift_slope(aspect: float) -> float:
    """Helmbold: dC_L/dα per radian of a straight wing of aspect ratio A,
    2π A / (2 + sqrt(A² + 4)); tends to 2π for large A and to πA/2 for small."""
    return 2 * math.pi * aspect / (2 + math.sqrt(aspect**2 + 4))


def section_form_factor(t_c: float) -> float:
    """Profile drag over twice the flat-plate friction (Hoerner): 1 + 2 t/c + 60 (t/c)⁴."""
    return 1 + 2 * t_c + 60 * t_c**4


@dataclass
class ParametricFoil:
    """A straight-tapered foil hung from the host's bottom (a rudder):
    `mount: {host: <hull>, x: <root leading edge>}`, swept by `sweep`. Its
    planform acts at the mean chord's quarter point at mid-span; it has an
    `angle` control (held at 0 unless the boat file makes it the yaw-balance
    unknown)."""

    section: str
    root_chord: float
    tip_chord: float
    span: float
    x: float  # quarter chord of the mean chord, m aft of the bow
    z_root: float  # the host's bottom there [m]
    controls: tuple[Control, ...] = (Control("angle", "hold"),)
    sweep_le: float = 0.0  # the leading edge's sweep [deg, + tip aft]

    @classmethod
    def build(cls, ctx, name: str, mount: dict | None = None, *, root_chord: float, tip_chord: float, span: float,
              section: str = "naca0008", sweep: float = 0.0, sweep_at: float = 0.0) -> "ParametricFoil":
        """`sweep` [deg, + tip aft] of the line at `sweep_at` of the chord:
        0 the leading edge (default), 0.25 the quarter chord, 1 the trailing
        edge (`sweep: 0, sweep_at: 1` is a vertical trailing edge)."""
        cr, ct, b = float(root_chord), float(tip_chord), float(span)
        le = b * math.tan(math.radians(float(sweep))) + float(sweep_at) * (cr - ct)  # the tip's leading edge aft of the root's
        chord = 0.5 * (cr + ct)
        x = float(mount["x"]) + 0.5 * le + 0.25 * chord
        return cls(str(section), cr, ct, b, x, -ctx.host(mount).depth_at(x), sweep_le=math.degrees(math.atan2(le, b)))

    @property
    def chord(self) -> float:
        return 0.5 * (self.root_chord + self.tip_chord)

    def planform(self) -> dict:
        return {"span": self.span, "chord": self.chord, "section": self.section, "x": self.x,
                "z": self.z_root - 0.5 * self.span, "area": self.chord * self.span}

    def volumes(self) -> list[tuple[float, np.ndarray]]:
        """The blade's displaced volume: section area ~ c², at its planform centre."""
        v = 0.5 * float(foils.load(self.section).area()) * (self.root_chord**2 + self.tip_chord**2) * self.span
        return [(v, np.array([self.x, 0.0, self.z_root - 0.5 * self.span]))]


@dataclass
class LiftingLine:
    """A fin or rudder below the hull: exposed span b, mean chord c, section,
    quarter-chord point at mid-span (x, z) in the upright boat frame."""

    span: float
    chord: float
    section: str = "naca0008"
    x: float = 0.5
    z: float = -0.2
    e: float = 0.9  # span efficiency of the induced drag
    eps: float = 0.0  # downwash ε per degree of leeway (the keel's, at the rudder)
    alpha_max: float = 12.0  # beyond this the model is flagged (no stall)
    rho: float = 999.1
    nu: float = 1.137e-6
    name: str = "fin"
    kind: str = "hydro"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()
    _tc: float = field(default=math.nan, repr=False)

    def __post_init__(self):
        if math.isnan(self._tc):
            self._tc = float(foils.load(self.section).thickness()[0])

    @classmethod
    def build(cls, ctx, name: str, shape, *, e: float = 0.9, downwash: dict | None = None,
              alpha_max: float = 12.0) -> "LiftingLine":
        """`downwash: {from: <part>, factor: f}`: f times that part's elliptic
        far-field downwash ε = 2 C_Lα / (π A) per unit of leeway."""
        pf = shape.planform()
        eps = float(downwash.get("factor", 1.0)) * ctx.get(downwash["from"]).downwash() if downwash else 0.0
        return cls(pf["span"], pf["chord"], pf["section"], x=pf["x"], z=pf["z"], e=float(e), eps=eps,
                   alpha_max=float(alpha_max), rho=ctx.water.rho, nu=ctx.water.nu, name=name)

    @property
    def area(self) -> float:
        return self.span * self.chord

    @property
    def aspect(self) -> float:
        return 2 * self.span / self.chord  # mirrored in the hull

    def alpha(self, s: State) -> float:
        a = s.leeway - s.controls.get(f"{self.name}.angle", 0.0)
        return a * math.cos(math.radians(s.heel)) - self.eps * s.leeway

    def downwash(self) -> float:
        """This foil's elliptic far-field downwash per unit leeway, 2 C_Lα / (π A)."""
        return 2 * lift_slope(self.aspect) / (math.pi * self.aspect)

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

    def info(self) -> dict:
        return {"downwash_per_leeway": round(self.eps, 4)} if self.eps else {}
