"""Hull geometry: the analytic Wigley test hull, plus helpers for CAD hulls.

Wigley hull: y = +-B/2 (1 - (2(x-L/2)/L)^2) (1 - (z/T)^2), the standard
benchmark hull for free-surface CFD. With L=1, B=0.18, T=0.05 it displaces
4/9 L B T = 4.0 litres, i.e. ~4.0 kg in fresh water: an IOM-sized test body.
Above the waterline the sides are extended vertically to `freeboard`, then
closed with a flat deck.
"""

from __future__ import annotations

import math

import numpy as np

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
