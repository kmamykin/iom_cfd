"""Parametric IOM appendages: keel fin, bulb, rudder -> closed STL surfaces.

All lengths in metres, boat frame (x aft, y port, z up, waterline z=0).
Fins hang down from `z_root` (the canoe-body bottom); they are extended a
little above it so they cut cleanly through the domain top / hull surface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid  # numpy < 2 in the solver image

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
    tip_extension: float = 0.0  # m, extra length below the tip at the tip chord (e.g. into a bulb)
    twist: float = 0.0  # deg, rotation of the tip section (washout) about z
    n_span: int = 24
    n_section: int = 81  # points per surface side


def fin(spec: FinSpec, name: str = "fin") -> Surface:
    f = foils.load(spec.section)
    up = f.surface("upper", spec.n_section)  # LE -> TE
    lo = f.surface("lower", spec.n_section)
    ring2d = np.vstack([up[::-1][:-1], lo[:-1]])  # TE->upper->LE->lower (TE once)
    z_top = spec.z_root + spec.root_extension
    z_tip = spec.z_root - spec.span - spec.tip_extension
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


def taper_chords(mean_chord: float, taper: float) -> tuple[float, float]:
    """(root, tip) chord of a straight-tapered fin with this mean chord and
    taper ratio (tip / root). Equal mean chord and span = equal area."""
    root = 2.0 * mean_chord / (1.0 + taper)
    return root, taper * root


@dataclass
class FoilBulbSpec:
    """Body whose radius follows a symmetric foil's half-thickness (`section`,
    e.g. naca0007: diameter = 7 % of the length, round nose, pointed tail).
    Placed by its centre of volume (= the lead's centre of mass).

    Every cross-section has the same shape: round by default, or a
    superellipse of width / height `aspect` whose upper and lower halves have
    the exponents `top` and `bottom` (|y/b|^n + |z/h|^n = 1; 2 = elliptic,
    larger = flatter with harder shoulders). It has the area of the round
    section, so the volume and the centre of volume along x don't change.
    `cant` turns the body nose up about its centre of volume."""

    section: str = "naca0007"
    length: float = 0.46
    x_cg: float = 0.50  # m, centre of volume
    z_axis: float = -0.40  # m, the axis (where the section is widest) before cant
    aspect: float = 1.0  # width / height of the sections
    top: float = 2.0  # superellipse exponent of the upper half of the sections
    bottom: float = 2.0  # and of the lower half
    cant: float = 0.0  # deg, nose up
    n_axial: int = 100
    n_theta: int = 48

    @property
    def round(self) -> bool:
        return self.aspect == 1.0 and self.top == 2.0 and self.bottom == 2.0


def _half_superellipse(n: float) -> tuple[float, float]:
    """Area and first moment of the half superellipse |y|^n + |z|^n = 1,
    z > 0, with unit half-width and height: (area / 2, moment about z = 0)."""
    area = math.gamma(1 + 1 / n) ** 2 / math.gamma(1 + 2 / n)
    moment = math.gamma(1 + 1 / n) * math.gamma(1 + 2 / n) / math.gamma(1 + 3 / n)
    return area, moment


def section_shape(aspect: float, top: float, bottom: float) -> tuple[float, float, float]:
    """(half-width, half-height, centroid height above the axis) of the
    bulb cross-section with the area of a circle of radius 1."""
    if aspect == 1.0 and top == bottom == 2.0:
        return 1.0, 1.0, 0.0  # exactly, so round bulbs are placed as before
    (a_t, m_t), (a_b, m_b) = _half_superellipse(top), _half_superellipse(bottom)
    h = math.sqrt(math.pi / (2 * aspect * (a_t + a_b)))  # area 2 b h (a_t + a_b) = pi, b = aspect h
    return aspect * h, h, h * (m_t - m_b) / (2 * (a_t + a_b))


def section_ring(aspect: float, top: float, bottom: float, n: int) -> np.ndarray:
    """The cross-section at r = 1 (`section_shape`) as n points (y, z), equal
    arc length apart, from the top through -y, the bottom and +y. n is even
    and the points are exact mirror images in y, so an upright mesh around
    the body can be a mirror image too."""
    if n % 2:
        raise ValueError("n must be even")
    b, h, _ = section_shape(aspect, top, bottom)
    phi = np.linspace(0.5 * math.pi, 1.5 * math.pi, 20001)  # top -> -y -> bottom
    c, s = np.cos(phi), np.sin(phi)
    e = np.where(s >= 0, 2.0 / top, 2.0 / bottom)
    pts = np.column_stack([b * np.sign(c) * np.abs(c) ** e, h * np.sign(s) * np.abs(s) ** e])
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    t = np.linspace(0.0, arc[-1], n // 2 + 1)
    half = np.column_stack([np.interp(t, arc, pts[:, 0]), np.interp(t, arc, pts[:, 1])])
    half[0], half[-1] = (0.0, h), (0.0, -h)
    return np.vstack([half, half[-2:0:-1] * (-1.0, 1.0)])


def foil_bulb_cg_offset(spec: FoilBulbSpec) -> float:
    """Height of the centre of volume above the axis (m, before cant): not 0
    when the top and bottom of the sections differ."""
    if spec.top == spec.bottom:
        return 0.0
    _, _, zc = section_shape(spec.aspect, spec.top, spec.bottom)
    x, r = _foil_radius(spec.section, 4001)
    return zc * spec.length * float(trapezoid(r**3, x) / trapezoid(r**2, x))


def _foil_radius(section: str, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Half-thickness y(x) of a symmetric section, unit chord, x from 0 to 1."""
    f = foils.load(section)
    up, lo = f.surface("upper", n), f.surface("lower", n)
    if np.max(np.abs(up[:, 1] + np.interp(up[:, 0], lo[:, 0], lo[:, 1]))) > 1e-4:
        raise ValueError(f"bulb section {section} is not symmetric")
    x = np.clip(up[:, 0], 0.0, 1.0)
    r = np.clip(up[:, 1], 0.0, None)
    r[0] = r[-1] = 0.0
    return x, r


def foil_body_coefficients(section: str) -> tuple[float, float, float]:
    """(volume / L^3, centre of volume / L, max diameter / L) of the body of
    revolution of `section` (exact shape, not the STL facets)."""
    x, r = _foil_radius(section, 4001)
    a = math.pi * r**2
    vol = float(trapezoid(a, x))
    return vol, float(trapezoid(a * x, x)) / vol, 2.0 * float(r.max())


def foil_bulb_length(section: str, volume: float) -> float:
    """Length of the `section` body of revolution that has this volume."""
    return (volume / foil_body_coefficients(section)[0]) ** (1.0 / 3.0)


def foil_bulb_lines(spec: FoilBulbSpec, n: int = 4001) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Top and bottom lines of the bulb in its centre plane, with cant:
    (x, z of the top line; x, z of the bottom line), m, nose to tail. The
    lowest point of the bulb is on the bottom line."""
    x, r = _foil_radius(spec.section, n)
    _, xc, _ = foil_body_coefficients(spec.section)
    _, h, _ = section_shape(spec.aspect, spec.top, spec.bottom)
    zoff = foil_bulb_cg_offset(spec)
    xi = (x - xc) * spec.length  # along the axis from the centre of volume
    c, s = math.cos(math.radians(spec.cant)), math.sin(math.radians(spec.cant))
    out = []
    for zeta in (h * r * spec.length - zoff, -h * r * spec.length - zoff):  # above the centre of volume
        out += [spec.x_cg + xi * c + zeta * s, spec.z_axis + zoff - xi * s + zeta * c]
    return tuple(out)


def foil_bulb(spec: FoilBulbSpec, name: str = "bulb") -> Surface:
    x, r = _foil_radius(spec.section, spec.n_axial)
    _, xc, _ = foil_body_coefficients(spec.section)
    ring = None if spec.round else section_ring(spec.aspect, spec.top, spec.bottom, spec.n_theta)
    s = revolve(x * spec.length, r * spec.length, spec.n_theta, name, ring)
    s = s.translated((spec.x_cg - xc * spec.length, 0.0, spec.z_axis))
    if spec.cant:
        s = s.rotated("y", spec.cant, about=(spec.x_cg, 0.0, spec.z_axis + foil_bulb_cg_offset(spec)))
    return s
