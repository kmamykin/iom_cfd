"""A hull placed at an attitude and split at the water plane z = 0.

Placement (docs/geometry.md, as vpp/hydrostatics.py floats a boat): the
boat-frame surface (x aft, y port, z up, origin at the bow on the waterline)
is heeled by φ (+ to starboard) about the x axis through the origin, then
trimmed (+ bow down) about the y axis through (x_trim, 0, 0), then sunk
(+ down). The earth plane z = 0 is the water surface.

`split` cuts the placed hull at z = 0 and closes each part with its mirror
image in the plane: the underwater part as a double body for a water domain
whose top is a mirror plane (keel3d), the topsides for an air domain whose
floor is a slip wall (windage). The domain boundary is the flat lid; the
mirror lets the body cross it at the angle it arrives at, so snappyHexMesh
snaps the cells next to the plane onto the hull's own continuation (not
onto a deck edge or a cap just beyond it).
"""

from __future__ import annotations

import numpy as np

from . import stl


def placement(heel: float, trim: float, sink: float, x_trim: float) -> tuple[np.ndarray, np.ndarray]:
    """(R, t) with p_earth = R p_boat + t."""
    Rx, Ry = stl.rotation("x", heel), stl.rotation("y", -trim)  # bow down = −y rotation for x aft
    a = np.array([x_trim, 0.0, 0.0])
    return Ry @ Rx, a - Ry @ a - np.array([0.0, 0.0, sink])


def trim_axis(surface: stl.Surface) -> float:
    """The trim axis vpp/hydrostatics.py uses: the middle of the hull's length."""
    lo, hi = surface.bounds
    return 0.5 * float(lo[0] + hi[0])


def _cut(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Where the edges p -> q (p at or below z = 0, q above) meet the plane."""
    t = p[:, 2] / (p[:, 2] - q[:, 2])
    return p + t[:, None] * (q - p)


def _clip(v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The triangles of corners v (M, 3, 3) clipped to z ≤ 0 (K, 3, 3), and
    the points where crossing edges meet the plane."""
    below = v[:, :, 2] <= 0.0
    nb = below[:, 0].astype(np.int8) + below[:, 1] + below[:, 2]
    k3 = np.arange(3)
    # One corner below: keep the triangle (a, p_ab, p_ac), a the corner below.
    v1, b1 = v[nb == 1], below[nb == 1]
    r1 = np.take_along_axis(v1, ((np.argmax(b1, axis=1)[:, None] + k3) % 3)[:, :, None], axis=1)
    a, b, c = r1[:, 0], r1[:, 1], r1[:, 2]
    pab, pac = _cut(a, b), _cut(a, c)
    # Two corners below: the quad (a, b, p_bc, p_ca), c the corner above.
    # Rolling the corners keeps their cyclic order, so the orientation too.
    v2, b2 = v[nb == 2], below[nb == 2]
    r2 = np.take_along_axis(v2, ((np.argmin(b2, axis=1)[:, None] + 1 + k3) % 3)[:, :, None], axis=1)
    a2, b2_, c2 = r2[:, 0], r2[:, 1], r2[:, 2]
    pbc, pca = _cut(b2_, c2), _cut(a2, c2)
    T = np.concatenate([v[nb == 3], np.stack([a, pab, pac], axis=1),
                        np.stack([a2, b2_, pbc], axis=1), np.stack([a2, pbc, pca], axis=1)])
    return T, np.concatenate([pab, pac, pbc, pca])


def mirrored(T: np.ndarray) -> np.ndarray:
    """Triangles T (K, 3, 3) reflected in the plane z = 0, corners reversed
    so that outward stays outward."""
    return (T * np.array([1.0, 1.0, -1.0]))[:, ::-1]


def below_water(v: np.ndarray) -> np.ndarray:
    """The triangles of corners v (M, 3, 3, earth frame, outward) clipped to
    z ≤ 0, still outward."""
    return _clip(v)[0]


def above_water(v: np.ndarray) -> np.ndarray:
    """The triangles of corners v (M, 3, 3, earth frame, outward) clipped to
    z ≥ 0, still outward."""
    return mirrored(_clip(mirrored(v))[0])


def weld(T: np.ndarray, name: str = "surface", tol: float = 1e-9) -> stl.Surface:
    """A surface from a triangle soup (K, 3, 3): corners within `tol` of the
    extent merged, corners within it of z = 0 put on the plane, triangles
    that lie in the plane or collapse to an edge dropped."""
    flat = T.reshape(-1, 3).copy()
    scale = float(np.ptp(flat, axis=0).max()) * tol + 1e-30
    flat[np.abs(flat[:, 2]) < scale, 2] = 0.0
    key = np.round(flat / scale).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    tri = inv.reshape(-1, 3)
    v = flat[idx]
    keep = (tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 2] != tri[:, 0])
    keep &= ~np.all(v[tri][:, :, 2] == 0.0, axis=1)
    tri = tri[keep]
    used = np.unique(tri)
    remap = np.full(len(v), -1, np.int64)
    remap[used] = np.arange(len(used))
    return stl.Surface(v[used], remap[tri], name)


def double_body(T: np.ndarray, name: str) -> stl.Surface:
    """The triangles T (one side of z = 0, outward) and their mirror image as
    one closed surface."""
    s = weld(np.concatenate([T, mirrored(T)]), name)
    if not s.is_closed():
        raise ValueError(f"{name}: the double body is not closed (is the hull surface closed?)")
    return s


def split(surface: stl.Surface, heel: float, trim: float = 0.0, sink: float = 0.0,
          x_trim: float | None = None, names: tuple[str, str] = ("hull", "hull")) -> tuple[stl.Surface, stl.Surface]:
    """The boat-frame `surface` (closed, outward) placed at (heel, trim,
    sink) and cut at z = 0: (underwater double body, topsides double body),
    each closed by its mirror image in the plane."""
    R, t = placement(heel, trim, sink, trim_axis(surface) if x_trim is None else float(x_trim))
    v = (surface.vertices @ R.T + t)[surface.triangles]
    return double_body(below_water(v), names[0]), double_body(above_water(v), names[1])


def crossings(surface: stl.Surface, x: float, y: float) -> np.ndarray:
    """Every z where the vertical line through (x, y) crosses the surface,
    sorted."""
    v = surface.vertices[surface.triangles]
    a, b, c = v[:, 0], v[:, 1], v[:, 2]
    det = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    ok = np.abs(det) > 1e-18  # triangles seen edge-on from above have no crossing
    a, b, c, det = a[ok], b[ok], c[ok], det[ok]
    # barycentric coordinates of (x, y) in each triangle's plan view
    u = ((x - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (y - a[:, 1])) / det
    w = ((b[:, 0] - a[:, 0]) * (y - a[:, 1]) - (x - a[:, 0]) * (b[:, 1] - a[:, 1])) / det
    hit = (u >= 0) & (w >= 0) & (u + w <= 1)
    return np.sort(a[hit, 2] + u[hit] * (b[hit, 2] - a[hit, 2]) + w[hit] * (c[hit, 2] - a[hit, 2]))
