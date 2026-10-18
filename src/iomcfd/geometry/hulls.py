"""Hull geometry: the analytic Wigley test hull, a parametric IOM-like canoe
body, plus helpers for CAD hulls.

Wigley hull: y = +-B/2 (1 - (2(x-L/2)/L)^2) (1 - (z/T)^2), the standard
benchmark hull for free-surface CFD. With L=1, B=0.18, T=0.05 it displaces
4/9 L B T = 4.0 litres, i.e. ~4.0 kg in fresh water: an IOM-sized test body.
Above the waterline the sides are extended vertically to `freeboard`, then
closed with a flat deck.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid  # numpy < 2 in the solver image

from .stl import Surface, loft


def wigley(length: float = 1.0, beam: float = 0.18, draft: float = 0.05, freeboard: float = 0.06,
           n_x: int = 121, n_z: int = 24, n_deck: int = 6) -> Surface:
    eps = 0.002  # tiny flat transoms at the ends keep the triangulation valid
    xs = length * (eps + (1 - 2 * eps) * 0.5 * (1 - np.cos(np.linspace(0, math.pi, n_x))))
    # vertical stations: cosine-clustered below the waterline, uniform above
    zb = -draft * (1 - np.sin(np.linspace(0, math.pi / 2, n_z)))  # -T .. 0
    za = np.linspace(0, freeboard, max(3, n_z // 3))[1:]
    rings = []
    for x in xs:
        half = 0.5 * beam * (1 - (2 * (x - length / 2) / length) ** 2)
        yb = half * (1 - (zb / draft) ** 2)
        y_side = np.concatenate([yb, np.full(len(za), half)])
        z_side = np.concatenate([zb, za])
        stbd = np.column_stack([-y_side, z_side])  # keel -> deck edge
        deck = np.column_stack([np.linspace(-half, half, n_deck + 2)[1:-1], np.full(n_deck, freeboard)])
        port = np.column_stack([y_side[::-1][:-1], z_side[::-1][:-1]])  # deck edge -> just above keel
        ring = np.vstack([stbd, deck, port])
        rings.append(np.column_stack([np.full(len(ring), x), ring]))
    return loft(rings, name="hull")


def wigley_displacement(length: float, beam: float, draft: float) -> float:
    """Displaced volume (m^3) at the design waterline."""
    return 4.0 / 9.0 * length * beam * draft


def wetted_area_below(surface: Surface, z: float = 0.0) -> float:
    """Approximate area of the surface below the plane z (triangle centroids)."""
    v = surface.vertices[surface.triangles]
    a = 0.5 * np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1)
    return float(a[v[:, :, 2].mean(axis=1) < z].sum())


def waterline_length(surface: Surface, z: float = 0.0, tol: float = 2e-3) -> float:
    """Length of the waterline (extent in x of vertices near z)."""
    v = surface.vertices
    m = np.abs(v[:, 2] - z) < tol * max(np.ptp(v[:, 0]), 1e-9)
    if not m.any():
        m = v[:, 2] < z
    return float(np.ptp(v[m, 0])) if m.any() else float(np.ptp(v[:, 0]))


@dataclass
class CanoeSpec:
    """Parametric canoe body (hull without appendages), boat frame, bow at x = 0.

    Waterline half-breadth b(x) and centreline draft t(x) each rise from 0 at
    the ends to their maximum (at `beam_at`, `draft_at`, fractions of the
    length) as 1 - (distance / run)^n, with separate exponents forward and
    aft (2 = parabolic; larger = fuller ends). Sections are superellipses
    |y/b|^n + |z/t|^n = 1 (`section` 2 = elliptic, larger = boxier). Above
    the waterline the sides are vertical up to `freeboard`, then a flat deck
    closes the surface (only the part below the waterline is wetted in a
    double-body model).
    """

    length: float = 0.99
    beam: float = 0.165
    draft: float = 0.053
    beam_at: float = 0.55
    draft_at: float = 0.50
    entry: float = 2.0  # waterline exponent forward of beam_at
    run: float = 2.0  # waterline exponent aft of beam_at
    rise_fwd: float = 2.0  # keel-line exponent forward of draft_at
    rise_aft: float = 2.0  # keel-line exponent aft of draft_at
    section: float = 2.0
    freeboard: float = 0.06
    n_x: int = 141
    n_section: int = 28  # points from the keel to the waterline, per side


def _rise(xi: np.ndarray, at: float, n_fwd: float, n_aft: float) -> np.ndarray:
    xi = np.clip(np.asarray(xi, float), 0.0, 1.0)
    fwd = 1 - (np.clip(at - xi, 0, None) / at) ** n_fwd
    aft = 1 - (np.clip(xi - at, 0, None) / (1 - at)) ** n_aft
    return np.where(xi < at, fwd, aft)


def canoe_half_breadth(spec: CanoeSpec, x) -> np.ndarray:
    """Waterline half-breadth at x (m from the bow)."""
    return 0.5 * spec.beam * _rise(np.asarray(x) / spec.length, spec.beam_at, spec.entry, spec.run)


def canoe_depth(spec: CanoeSpec, x) -> np.ndarray:
    """Canoe-body draft on the centreline at x (positive, m)."""
    return spec.draft * _rise(np.asarray(x) / spec.length, spec.draft_at, spec.rise_fwd, spec.rise_aft)


def _superellipse_area_factor(n: float) -> float:
    """Area of |y/b|^n + |z/t|^n <= 1 is 4 b t times this."""
    return math.gamma(1 + 1 / n) ** 2 / math.gamma(1 + 2 / n)


def canoe_displacement(spec: CanoeSpec) -> tuple[float, float, float]:
    """(underwater volume m^3, centre of buoyancy x m, wetted area m^2), from
    the exact shape (sections integrated along the length)."""
    x = np.linspace(0, spec.length, 4001)
    b, t = canoe_half_breadth(spec, x), canoe_depth(spec, x)
    area = 2 * b * t * _superellipse_area_factor(spec.section)  # half of the full superellipse
    vol = float(trapezoid(area, x))
    # girth of the half superellipse, keel to waterline on both sides
    th = np.linspace(-math.pi / 2, math.pi / 2, 401)
    c, s = np.cos(th), np.sin(th)
    ey = np.abs(c) ** (2 / spec.section)
    ez = -np.abs(s) ** (2 / spec.section)
    girth = np.array([np.sum(np.hypot(np.diff(bi * ey), np.diff(ti * ez))) for bi, ti in zip(b, t)])
    return vol, float(trapezoid(area * x, x)) / vol, float(trapezoid(girth, x))


def canoe(spec: CanoeSpec, name: str = "hull") -> Surface:
    eps = 0.003  # tiny flat ends keep the triangulation valid where b, t -> 0
    xi = eps + (1 - 2 * eps) * 0.5 * (1 - np.cos(np.linspace(0, math.pi, spec.n_x)))
    th = np.linspace(-math.pi / 2, 0, spec.n_section)  # keel -> waterline
    c, s = np.cos(th), np.sin(th)
    ey, ez = c ** (2 / spec.section), -np.abs(s) ** (2 / spec.section)
    za = np.linspace(0, spec.freeboard, 5)[1:]
    n_deck = 8
    rings = []
    for x in xi * spec.length:
        b, t = float(canoe_half_breadth(spec, x)), float(canoe_depth(spec, x))
        ys = np.concatenate([b * ey, np.full(len(za), b)])
        zs = np.concatenate([t * ez, za])
        stbd = np.column_stack([-ys, zs])  # keel -> deck edge
        deck = np.column_stack([np.linspace(-b, b, n_deck + 2)[1:-1], np.full(n_deck, spec.freeboard)])
        port = np.column_stack([ys[::-1][:-1], zs[::-1][:-1]])  # deck edge -> just above the keel
        ring = np.vstack([stbd, deck, port])
        rings.append(np.column_stack([np.full(len(ring), x), ring]))
    return loft(rings, name=name)
