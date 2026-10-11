"""Parametric IOM appendages: keel fin, bulb, rudder -> closed STL surfaces.

All lengths in metres, boat frame (x aft, y port, z up, waterline z=0).
Fins hang down from `z_root` (the canoe-body bottom); they are extended a
little above it so they cut cleanly through the domain top / hull surface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import foils
from .stl import Surface, loft, revolve

LEAD_DENSITY = 11340.0  # kg/m^3


@dataclass
class FinSpec:
    section: str = "naca0008"
    root_chord: float = 0.085
    tip_chord: float = 0.075
    span: float = 0.36  # m, from z_root down to the tip
    sweep: float = 0.0  # deg, quarter-chord sweep (positive = tip aft)
    x_root_le: float = 0.45  # m, root leading edge
    z_root: float = -0.04  # m, canoe-body bottom at the fin
    root_extension: float = 0.02  # m, extra length above z_root
    twist: float = 0.0  # deg, rotation of the tip section (washout) about z
    n_span: int = 24
    n_section: int = 81  # points per surface side


def fin(spec: FinSpec, name: str = "fin") -> Surface:
    f = foils.load(spec.section)
    up = f.surface("upper", spec.n_section)  # LE -> TE
    lo = f.surface("lower", spec.n_section)
    ring2d = np.vstack([up[::-1][:-1], lo[:-1]])  # TE->upper->LE->lower (TE once)
    z_top = spec.z_root + spec.root_extension
    z_tip = spec.z_root - spec.span
    rings = []
    for eta in np.linspace(0, 1, spec.n_span):  # 0 at top
        z = z_top + (z_tip - z_top) * eta
        frac = (spec.z_root - z) / spec.span  # 0 at root, 1 at tip (negative above root)
        frac_c = min(max(frac, 0.0), 1.0)
        c = spec.root_chord + (spec.tip_chord - spec.root_chord) * frac_c
        x_qc = spec.x_root_le + 0.25 * spec.root_chord + math.tan(math.radians(spec.sweep)) * (spec.z_root - z)
        tw = math.radians(spec.twist * frac_c)
        xs = (ring2d[:, 0] - 0.25) * c
        ys = ring2d[:, 1] * c
        xr = xs * math.cos(tw) - ys * math.sin(tw)
        yr = xs * math.sin(tw) + ys * math.cos(tw)
        rings.append(np.column_stack([x_qc + xr, yr, np.full(len(xr), z)]))
    return loft(rings, name=name)


@dataclass
class BulbSpec:
    length: float = 0.33
    diameter: float = 0.0375  # 2.4 kg of lead with the defaults
    max_at: float = 0.4  # fraction of length where the diameter is max
    tail_exp: float = 2.0  # aft profile r ~ 1 - xi^tail_exp (2 = parabolic)
    x_nose: float = 0.30  # m
    z_axis: float = -0.40  # m (IOM max draft is 0.42 m)
    n_axial: int = 80
    n_theta: int = 48


def bulb_profile(spec: BulbSpec) -> tuple[np.ndarray, np.ndarray]:
    xi = 0.5 * (1 - np.cos(np.linspace(0, math.pi, spec.n_axial)))
    m = spec.max_at
    R = spec.diameter / 2
    r = np.where(
        xi < m,
        R * np.sqrt(np.clip(1 - ((m - xi) / m) ** 2, 0, 1)),
        R * np.clip(1 - ((xi - m) / (1 - m)) ** spec.tail_exp, 0, 1),
    )
    r[0] = r[-1] = 0.0
    return xi * spec.length, r


def bulb(spec: BulbSpec, name: str = "bulb") -> Surface:
    x, r = bulb_profile(spec)
    s = revolve(x, r, spec.n_theta, name)
    return s.translated((spec.x_nose, 0.0, spec.z_axis))


def bulb_mass(spec: BulbSpec, density: float = LEAD_DENSITY) -> float:
    return bulb(spec).volume() * density


@dataclass
class RudderSpec(FinSpec):
    section: str = "naca0008"
    root_chord: float = 0.085
    tip_chord: float = 0.06
    span: float = 0.22
    sweep: float = 5.0
    x_root_le: float = 0.86
    z_root: float = -0.02
    angle: float = 0.0  # deg, rudder deflection about the stock (positive = TE to port)
    stock_at: float = 0.25  # stock position as fraction of root chord


def rudder(spec: RudderSpec, name: str = "rudder") -> Surface:
    s = fin(spec, name)
    stock = (spec.x_root_le + spec.stock_at * spec.root_chord, 0.0, 0.0)
    return s.rotated("z", spec.angle, about=stock) if spec.angle else s
