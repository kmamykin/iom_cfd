"""Hydrostatics of a heeled, trimmed and sunk boat: displaced volume, centre
of buoyancy, waterplane, and the righting moment RM_φ; the hull's
particulars upright (coefficients, BM, GM, MCT).

Frames (docs/geometry.md): the boat frame is x aft, y port, z up, origin at
the bow on the waterline. The boat is placed in the earth frame by heel φ
(+ to starboard, about the x axis through the waterline), then trim (+ bow
down, about the y axis through (x_trim, 0, 0)), then sinkage (+ down). The
water surface is the earth plane z = 0.

Moments use the signs of `components.base.Loads`, about the (placed) boat
origin: pitch M + bow down, roll K + heels to starboard. RM_φ is −K of
weight and buoyancy, so ΣK_ext = RM_φ at equilibrium and RM_φ > 0 restores
a boat heeled to starboard.
"""

from __future__ import annotations

import dataclasses
import math
import warnings
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import root

from ..geometry import stl
from ..physics import G, fresh_water


@dataclass
class Submerged:
    """The part of a closed body below z = 0 (earth frame)."""

    volume: float  # m^3
    centroid: np.ndarray  # (3,) centre of the displaced volume
    wetted_area: float  # m^2, the body's surface below the plane
    waterplane_area: float  # m^2
    waterplane_centroid: np.ndarray  # (2,) (x, y)
    lwl: float  # waterline length: extent in x of the cut [m]
    bwl: float  # waterline beam: extent in y of the cut [m]
    i_l: float = 0.0  # waterplane second moment about the y axis through its centroid [m^4]
    i_t: float = 0.0  # and about the x axis through its centroid (BM = i_t / volume) [m^4]
    x_fwd: float = 0.0  # the waterline's ends: lwl = x_aft − x_fwd [m]
    x_aft: float = 0.0


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


def _submerged(v: np.ndarray) -> Submerged:
    """`submerged` on triangle corners v (M, 3, 3)."""
    # (sums over the 3 corners are written out: numpy's reductions over a
    # length-3 axis are several times slower)
    T, cut = _clip(v)
    p0, p1, p2 = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(p1 - p0, p2 - p0)  # twice the area vector
    vol6 = p0[:, 0] * n[:, 0] + p0[:, 1] * n[:, 1] + p0[:, 2] * n[:, 2]  # tetrahedra to the origin, on the plane
    volume = float(vol6.sum() / 6.0)
    centroid = vol6 @ (p0 + p1 + p2) / (4.0 * vol6.sum()) if volume > 0 else np.zeros(3)
    # The waterplane closes the clipped surface. Over that closed body
    # ∮ n_z dA = 0 and ∮ f n_z dA = 0 for f = x, y, x², y², xy (no z), so the
    # waterplane's area and moments are minus those of the clipped
    # triangles' z-projections: exact for the polyhedron, and no cut polygon
    # has to be traced (vertices on the plane, several loops: all fine).
    nz = -0.5 * n[:, 2]  # minus the clipped triangles' projected areas
    x0, x1, x2, y0, y1, y2 = p0[:, 0], p1[:, 0], p2[:, 0], p0[:, 1], p1[:, 1], p2[:, 1]
    sx, sy = x0 + x1 + x2, y0 + y1 + y2
    area = float(nz.sum())
    mx, my = nz @ sx / 3.0, nz @ sy / 3.0
    # ∫ x² dA over a triangle = A/6 (Σ x_i² + Σ_{i<j} x_i x_j) = A/12 ((Σ x_i)² + Σ x_i²)
    ixx = nz @ (sx**2 + x0**2 + x1**2 + x2**2) / 12.0
    iyy = nz @ (sy**2 + y0**2 + y1**2 + y2**2) / 12.0
    if area > 1e-12:
        xf, yf = mx / area, my / area
        i_l, i_t = float(ixx - area * xf**2), float(iyy - area * yf**2)
    else:
        xf = yf = i_l = i_t = 0.0
    # The waterline: the points where crossing edges meet the plane.
    x_fwd, x_aft = (float(cut[:, 0].min()), float(cut[:, 0].max())) if len(cut) else (0.0, 0.0)
    bwl = float(np.ptp(cut[:, 1])) if len(cut) else 0.0
    wetted = 0.5 * np.sqrt(n[:, 0] ** 2 + n[:, 1] ** 2 + n[:, 2] ** 2).sum()
    return Submerged(volume, np.asarray(centroid, float), float(wetted), area, np.array([xf, yf]), x_aft - x_fwd,
                     bwl, i_l, i_t, x_fwd, x_aft)


def submerged(surface: stl.Surface) -> Submerged:
    """The part of a closed, outward-oriented surface (already placed in the
    earth frame) below the water plane z = 0.

    Each triangle is clipped at z = 0 (the ones that cross are split, the
    part below kept), so the result is exact for the faceted body. Volume
    and centroid come from the divergence theorem, as tetrahedra from the
    origin to the clipped triangles: the origin is on the plane, so the
    waterplane cap that closes the body adds nothing. Wetted area is the
    area of the clipped triangles. The waterplane area, centroid and second
    moments follow from the clipped triangles too (see `_submerged`);
    lwl and bwl are the x and y extents of the cut.
    """
    return _submerged(surface.vertices[surface.triangles])


def above_water(v: np.ndarray) -> np.ndarray:
    """The triangles of corners v (M, 3, 3, earth frame, outward) clipped to
    z ≥ 0, still outward."""
    f = v * np.array([1.0, 1.0, -1.0])
    T, _ = _clip(f[:, ::-1])  # mirrored in the plane, corners reversed to stay outward
    return (T * np.array([1.0, 1.0, -1.0]))[:, ::-1]


def projected_area(T: np.ndarray, d) -> tuple[float, np.ndarray]:
    """The area of the triangles T (K, 3, 3) facing the direction d (unit)
    projected on the plane normal to it, and the centroid of that area. The
    silhouette of a closed body seen from d, exactly when every line along d
    crosses the body at most twice (more crossings, e.g. a cockpit, count
    the hidden faces too)."""
    n = 0.5 * np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    w = np.maximum(n @ np.asarray(d, float), 0.0)
    A = float(w.sum())
    return A, (w @ T.mean(axis=1) / A if A > 0 else np.zeros(3))


def placement(heel: float, trim: float, sink: float, x_trim: float) -> tuple[np.ndarray, np.ndarray]:
    """(R, t) with p_earth = R p_boat + t, for `place`."""
    Rx, Ry = stl.rotation("x", heel), stl.rotation("y", -trim)  # bow down = −y rotation for x aft
    a = np.array([x_trim, 0.0, 0.0])
    return Ry @ Rx, a - Ry @ a - np.array([0.0, 0.0, sink])


def place(surface: stl.Surface, heel: float, trim: float, sink: float, x_trim: float) -> stl.Surface:
    """The boat-frame `surface` in the earth frame: heeled by φ = `heel` [deg]
    about the x axis through the waterline origin (mast head to −y), then
    trimmed by `trim` [deg, + bow down] about the y axis through
    (x_trim, 0, 0), then sunk by `sink` [m, + down]."""
    return (surface.rotated("x", heel).rotated("y", -trim, about=(x_trim, 0.0, 0.0))
            .translated((0.0, 0.0, -sink)))


@dataclass
class Particulars:
    """The form of a hull at an attitude (`particulars`), in ITTC's symbols
    (docs/nomenclature.md). Earth frame: x as placed (from the bow when
    there is no trim), z from the water."""

    volume: float  # ∇ [m^3]
    lwl: float  # [m]
    x_fwd: float  # the waterline's ends [m]
    x_aft: float
    bwl: float  # [m]
    draft: float  # T_c: the deepest point under water [m]
    lcb: float  # x of the centre of buoyancy [m]
    vcb: float  # z of the centre of buoyancy (< 0) [m]
    lcf: float  # x of the waterplane's centroid [m]
    waterplane_area: float  # A_WP [m^2]
    wetted_area: float  # S [m^2]
    section_area: float  # A_X: the largest section under water [m^2]
    x_section: float  # where it is [m]
    cb: float  # C_B = ∇ / (LWL BWL T_c)
    cp: float  # C_P = ∇ / (A_X LWL)
    cx: float  # C_X = A_X / (BWL T_c)
    cwp: float  # C_WP = A_WP / (LWL BWL)
    bm_t: float  # I_T / ∇ [m]
    bm_l: float  # I_L / ∇ [m]
    immersion: float  # ρ A_WP: mass per unit sinkage [kg/m, = g/mm]


def _forward_volume(T: np.ndarray, xs: float) -> float:
    """The volume of the clipped body T (K, 3, 3: the part below z = 0)
    forward of the plane x = xs."""
    # x becomes the third coordinate (a cyclic swap, so the orientation is
    # kept) and _clip cuts it at xs. The origin (xs, 0, 0) is on both cut
    # planes, so neither cap adds to the tetrahedra.
    C, _ = _clip((T - np.array([xs, 0.0, 0.0]))[:, :, [1, 2, 0]])
    n = np.cross(C[:, 1] - C[:, 0], C[:, 2] - C[:, 0])
    return float(np.einsum("ij,ij->", C[:, 0], n) / 6.0)


def _largest_section(T: np.ndarray, x0: float, x1: float, n: int = 100) -> tuple[float, float]:
    """(A_X, x) of the clipped body T between x0 and x1: the section area
    dV/dx from the volume forward of n + 1 stations, then of 20 more around
    the largest (exact for the facets but for the difference over a step)."""
    x = np.linspace(x0, x1, n + 1)
    V = np.array([_forward_volume(T, xs) for xs in x])
    i = int(np.argmax(np.diff(V)))
    x = np.linspace(x[max(i - 1, 0)], x[min(i + 2, n)], 21)
    V = np.array([_forward_volume(T, xs) for xs in x])
    j = int(np.argmax(np.diff(V)))
    return float((V[j + 1] - V[j]) / (x[j + 1] - x[j])), float(0.5 * (x[j] + x[j + 1]))


def _particulars(v: np.ndarray, rho: float) -> Particulars:
    """`particulars` on placed triangle corners v (M, 3, 3)."""
    sub = _submerged(v)
    T, _ = _clip(v)
    vol, L, B = sub.volume, sub.lwl, sub.bwl
    Tc = -float(T[:, :, 2].min())
    ax, xx = _largest_section(T, sub.x_fwd, sub.x_aft)
    return Particulars(vol, L, sub.x_fwd, sub.x_aft, B, Tc, float(sub.centroid[0]), float(sub.centroid[2]),
                       float(sub.waterplane_centroid[0]), sub.waterplane_area, sub.wetted_area, ax, xx,
                       vol / (L * B * Tc), vol / (ax * L), ax / (B * Tc), sub.waterplane_area / (L * B),
                       sub.i_t / vol, sub.i_l / vol, rho * sub.waterplane_area)


def particulars(surface: stl.Surface, sink: float = 0.0, trim: float = 0.0, x_trim: float | None = None,
                rho: float | None = None) -> Particulars:
    """The form of a closed hull in the boat frame floating upright, sunk by
    `sink` [m, + down] and trimmed by `trim` [deg, + bow down] about
    (x_trim, 0, 0) (default the middle of its length), as `place` does:
    ∇, LCB, LCF, the coefficients, BM and the immersion. ρ default fresh
    water at 15 °C. The appendages are not in it (see
    `Hydrostatics.particulars_rows`)."""
    lo, hi = surface.bounds
    x_trim = 0.5 * float(lo[0] + hi[0]) if x_trim is None else float(x_trim)
    R, t = placement(0.0, trim, sink, x_trim)
    v = (np.asarray(surface.vertices, float) @ R.T + t)[np.asarray(surface.triangles)]
    return _particulars(v, fresh_water().rho if rho is None else float(rho))


@dataclass
class Floating:
    """A floating position (earth frame, see the module docstring)."""

    heel: float  # φ [deg]
    sink: float  # [m], + down
    trim: float  # [deg], + bow down
    rm: float  # RM_φ [N m]: −(roll moment of weight and buoyancy); + restores φ > 0
    gz: float  # rm / (m g) [m]
    wetted_area: float  # hull only [m^2]
    lwl: float  # [m]
    bwl: float  # [m]
    volume: float  # displaced, hull + appendages [m^3]
    cb: np.ndarray  # centre of buoyancy, earth frame (hull + appendages)
    converged: bool


class Hydrostatics:
    """Free floating position and righting moment of a hull with appendages.

    `hull`: closed surface in the boat frame, waterline z = 0 upright.
    `appendages`: (volume, centroid) in the boat frame of fully submerged
    bodies (fin, bulb, rudder). Their buoyancy is constant and moves with
    the boat; they are assumed to stay under water at every heel.
    `mass` [kg] at `cg` (boat frame). `rho` default: fresh water at 15 °C
    (C.4.1 measures in fresh water). `x_trim`: the trim axis (default the
    middle of the hull's length).
    """

    def __init__(self, hull: stl.Surface, appendages: list[tuple[float, np.ndarray]] | None = None, *,
                 mass: float, cg, rho: float | None = None, x_trim: float | None = None):
        self.hull = hull
        self._v, self._tri = np.asarray(hull.vertices, float), np.asarray(hull.triangles)
        self.appendages = [(float(v), np.asarray(c, float)) for v, c in (appendages or [])]
        self.mass = float(mass)
        self.cg = np.asarray(cg, float)
        self.rho = fresh_water().rho if rho is None else float(rho)
        lo, hi = hull.bounds
        self.x_trim = 0.5 * float(lo[0] + hi[0]) if x_trim is None else float(x_trim)
        self.length = float(hi[0] - lo[0])
        self.depth = float(hi[2] - lo[2])

    def _at(self, heel: float, trim: float, sink: float) -> tuple[Submerged, dict]:
        """Hull clipped and the placed points (degrees, m)."""
        R, t = placement(heel, trim, sink, self.x_trim)
        sub = _submerged((self._v @ R.T + t)[self._tri])
        pts = {"cg": R @ self.cg + t, "origin": t, "app": [R @ c + t for _, c in self.appendages]}
        return sub, pts

    def _balance(self, sub: Submerged, pts: dict, Z_ext: float, M_ext: float) -> tuple[np.ndarray, float, np.ndarray]:
        """Residuals (vertical force, pitch moment), total volume and CB."""
        vols = [sub.volume] + [v for v, _ in self.appendages]
        cens = [sub.centroid] + pts["app"]
        V = float(sum(vols))
        cb = sum(v * c for v, c in zip(vols, cens)) / V if V > 0 else np.zeros(3)
        W, B = self.mass * G, self.rho * G * V
        xo = pts["origin"][0]
        M = (pts["cg"][0] - xo) * (-W) + (cb[0] - xo) * B + M_ext  # M = x Z for vertical forces
        return np.array([B - (W - Z_ext), M]), V, cb

    def float_at(self, heel: float, Z_ext: float = 0.0, M_ext: float = 0.0,
                 start: tuple[float, float] = (0.0, 0.0), tol: float = 1e-9) -> Floating:
        """Sinkage and trim at heel φ [deg] where buoyancy = m g − Z_ext
        (Z_ext + up, e.g. the sails' and appendages' vertical forces) and the
        pitch moment of weight, buoyancy and M_ext (+ bow down, about the
        boat origin, e.g. the sail drive at the CE height) is zero. Z_ext
        acts at the boat origin: M_ext holds the moment of where it acts
        (x Z, as the parts' loads do).

        Newton's method on (sink, trim) from `start` = (sink m, trim deg),
        with the hydrostatic Jacobian from the waterplane (area, centroid,
        second moment) and the heights of G, B and the appendages; scipy's
        `root` (hybr) if that fails. Residuals are relative to m g and
        m g L; `tol` is their bound.
        """
        W, L = self.mass * G, self.length
        scale = np.array([W, W * L])
        rg = self.rho * G
        x = np.array([start[0], math.radians(start[1])])
        ok = False
        for _ in range(40):
            sub, pts = self._at(heel, math.degrees(x[1]), x[0])
            r, V, cb = self._balance(sub, pts, Z_ext, M_ext)
            if np.all(np.abs(r) < tol * scale):
                ok = True
                break
            A, xf = sub.waterplane_area, sub.waterplane_centroid[0]
            if A <= 0:
                break
            # A small sink ds and trim dθ (bow down) lower the body at x by
            # ds − dθ (x − x_trim) and move points along x by −dθ (z − z_axis)
            # (aft below the trim axis). The trim axis' own drift is left out.
            za = -x[0]
            ixx0 = sub.i_l + A * xf**2  # ∫ x² dA
            app_z = sum(v * (p[2] - za) for (v, _), p in zip(self.appendages, pts["app"]))
            J = np.array([
                [rg * A, -rg * A * (xf - self.x_trim)],
                [rg * A * xf, rg * (-sub.volume * (sub.centroid[2] - za) - (ixx0 - self.x_trim * A * xf) - app_z)
                 + W * (pts["cg"][2] - za)],
            ])
            try:
                dx = np.linalg.solve(J, -r)
            except np.linalg.LinAlgError:
                break
            dx[0] = np.clip(dx[0], -0.25 * self.depth, 0.25 * self.depth)
            dx[1] = np.clip(dx[1], -math.radians(5.0), math.radians(5.0))
            x = x + dx
        if not ok:
            def f(y):
                s, p = self._at(heel, math.degrees(y[1]), y[0])
                return self._balance(s, p, Z_ext, M_ext)[0] / scale

            sol = root(f, np.array([start[0], math.radians(start[1])]), method="hybr", options={"xtol": 1e-12})
            x = sol.x
            sub, pts = self._at(heel, math.degrees(x[1]), x[0])
            r, V, cb = self._balance(sub, pts, Z_ext, M_ext)
            ok = bool(np.all(np.abs(r) < 1e3 * tol * scale))
        # roll moment K = y Z of weight (−W at G) and buoyancy (+B at CB)
        K = pts["cg"][1] * (-W) + cb[1] * self.rho * G * V
        return Floating(heel=float(heel), sink=float(x[0]), trim=math.degrees(x[1]), rm=float(-K), gz=float(-K / W),
                        wetted_area=sub.wetted_area, lwl=sub.lwl, bwl=sub.bwl, volume=V, cb=cb, converged=ok)

    def particulars_rows(self, sinks=None) -> list[dict]:
        """The hull's `particulars` with the boat's displacement and
        metacentric heights, as table rows: floating upright (`float_at(0)`,
        condition "floating"), then on an even keel at each sinkage `sinks`
        [m, + down; default −10 to +10 mm every 2.5 mm] from the waterline
        z = 0 ("even keel"). The boat's columns count the appendages' volume
        ∇ (displacement ρ∇, z_b): GM_T = z_b + I_T / ∇ − z_g, GM_L likewise,
        and the moment to trim one degree MCT = ρ g ∇ GM_L π/180 [N m/deg]."""
        sinks = np.arange(-0.010, 0.010 + 1e-9, 0.0025) if sinks is None else np.asarray(sinks, float)
        f = self.float_at(0.0)
        rows = []
        for cond, sink, trim, ok in [("floating", f.sink, f.trim, f.converged),
                                     *(("even keel", float(s), 0.0, True) for s in sinks)]:
            R, t = placement(0.0, trim, sink, self.x_trim)
            p = _particulars((self._v @ R.T + t)[self._tri], self.rho)
            app = [(v, R @ c + t) for v, c in self.appendages]
            V = p.volume + sum(v for v, _ in app)
            z_b = (p.volume * p.vcb + sum(v * c[2] for v, c in app)) / V
            z_g = float((R @ self.cg + t)[2])
            gm_t, gm_l = z_b + p.bm_t * p.volume / V - z_g, z_b + p.bm_l * p.volume / V - z_g
            rows.append({"condition": cond, "sink": sink, "trim": trim, **dataclasses.asdict(p),
                         "displacement": self.rho * V, "z_b": z_b, "z_g": z_g, "gm_t": gm_t, "gm_l": gm_l,
                         "mct": self.rho * G * V * gm_l * math.pi / 180, "converged": float(ok)})
        return rows

    def table(self, heels=None, M_ext=None, Z_ext=0.0) -> "HydroTable":
        """`float_at` on the grid heels × M_ext × Z_ext (defaults: φ 0-60°
        every 2.5°; M_ext −2 to +6 N m every 1 N m, bow-down sail moments of
        an IOM upwind and downwind; Z_ext one layer at 0, a value or a list
        of layers [N, + up])."""
        heels = np.arange(0.0, 60.0 + 1e-9, 2.5) if heels is None else np.asarray(heels, float)
        M_ext = np.linspace(-2.0, 6.0, 9) if M_ext is None else np.asarray(M_ext, float)
        Z = np.atleast_1d(np.asarray(Z_ext, float))
        out = {k: np.zeros((len(heels), len(M_ext), len(Z))) for k in HydroTable.KEYS}
        conv = np.zeros((len(heels), len(M_ext), len(Z)), bool)
        j0 = int(np.argmin(np.abs(M_ext)))
        for m, z in enumerate(Z):
            prev = (0.0, 0.0)
            for i, h in enumerate(heels):
                # start each heel from the last one at M_ext ≈ 0, then walk out from there
                for js in (range(j0, len(M_ext)), range(j0 - 1, -1, -1)):
                    start = prev
                    for j in js:
                        f = self.float_at(float(h), float(z), float(M_ext[j]), start=start)
                        for k in HydroTable.KEYS:
                            out[k][i, j, m] = getattr(f, k)
                        conv[i, j, m] = f.converged
                        start = (f.sink, f.trim)
                        if j == j0:
                            prev = start
        if not conv.all():
            bad = [(float(heels[i]), float(M_ext[j]), float(Z[m])) for i, j, m in zip(*np.nonzero(~conv))]
            warnings.warn(f"hydrostatics did not converge at (heel, M_ext, Z_ext) = {bad}", stacklevel=2)
        return HydroTable(heels, M_ext, out, conv, Z)


@dataclass
class HydroTable:
    """`Hydrostatics.float_at` on a grid of heel φ [deg], external pitch
    moment M_ext [N m] and external vertical force Z_ext [N] (one or more
    layers), read back by bicubic splines in φ and M_ext (C¹ and smooth) and
    a polynomial through the Z_ext layers (quadratic for three). Outside
    the grid the inputs are clamped to it and `extrapolated` is set. A node
    with no equilibrium (the bow buried by a large bow-down moment) is
    continued linearly along M_ext from its converged neighbours for the
    splines, and a point in a cell that touches one is `extrapolated`."""

    heels: np.ndarray
    M_ext: np.ndarray
    values: dict  # key -> (n_heel, n_M, n_Z) array (or (n_heel, n_M): one layer)
    converged: np.ndarray
    Z_ext: np.ndarray = field(default_factory=lambda: np.zeros(1))
    _splines: dict = field(default_factory=dict, repr=False)

    KEYS = ("sink", "trim", "rm", "wetted_area", "lwl", "bwl")

    def __post_init__(self):
        self.Z_ext = np.atleast_1d(np.asarray(self.Z_ext, float))
        self.values = {k: (v[:, :, None] if np.ndim(v) == 2 else np.asarray(v)) for k, v in self.values.items()}
        conv = np.asarray(self.converged, bool)
        self.converged = conv[:, :, None] if conv.ndim == 2 else conv
        # a cell (heel, M_ext) is good when its four corners converged in every layer
        good = self.converged.all(axis=2)
        self._cell_ok = good[:-1, :-1] & good[1:, :-1] & good[:-1, 1:] & good[1:, 1:]
        kx, ky = min(3, len(self.heels) - 1), min(3, len(self.M_ext) - 1)
        self._splines = {k: [RectBivariateSpline(self.heels, self.M_ext, self._filled(self.values[k][:, :, m], m),
                                                 kx=kx, ky=ky)
                             for m in range(len(self.Z_ext))] for k in self.KEYS}

    def _filled(self, v: np.ndarray, m: int) -> np.ndarray:
        """Layer m of a value with its non-converged nodes continued linearly
        along M_ext from the nearest two converged ones (held when only one)."""
        v, M = v.copy(), self.M_ext
        for i in range(len(self.heels)):
            ok = self.converged[i, :, m]
            if ok.all() or not ok.any():
                continue
            j_ok = np.nonzero(ok)[0]
            for j in np.nonzero(~ok)[0]:
                lo, hi = j_ok[j_ok < j], j_ok[j_ok > j]
                if len(lo) and len(hi):
                    a, b = lo[-1], hi[0]
                elif len(j_ok) >= 2:
                    a, b = (lo[-2], lo[-1]) if len(lo) else (hi[0], hi[1])
                else:
                    v[i, j] = v[i, j_ok[0]]
                    continue
                v[i, j] = v[i, a] + (v[i, b] - v[i, a]) * (M[j] - M[a]) / (M[b] - M[a])
        return v

    def _weights(self, z: float) -> np.ndarray:
        """Lagrange weights of the Z_ext layers at z."""
        Z = self.Z_ext
        w = np.ones(len(Z))
        for i in range(len(Z)):
            for j in range(len(Z)):
                if i != j:
                    w[i] *= (z - Z[j]) / (Z[i] - Z[j])
        return w

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> dict:
        h = float(np.clip(heel, self.heels[0], self.heels[-1]))
        m = float(np.clip(M_ext, self.M_ext[0], self.M_ext[-1]))
        if len(self.Z_ext) == 1:
            out = {k: float(s[0](h, m)[0, 0]) for k, s in self._splines.items()}
            z = Z_ext
        else:
            z = float(np.clip(Z_ext, self.Z_ext[0], self.Z_ext[-1]))
            w = self._weights(z)
            out = {k: float(sum(wi * si(h, m)[0, 0] for wi, si in zip(w, s))) for k, s in self._splines.items()}
        i = min(max(int(np.searchsorted(self.heels, h, side="right")) - 1, 0), len(self.heels) - 2)
        j = min(max(int(np.searchsorted(self.M_ext, m, side="right")) - 1, 0), len(self.M_ext) - 2)
        no_eq = len(self.heels) > 1 and len(self.M_ext) > 1 and not self._cell_ok[i, j]
        out["extrapolated"] = h != heel or m != M_ext or z != Z_ext or bool(no_eq)
        return out

    def rm(self, heel: float) -> float:
        """RM_φ [N m] at M_ext = 0 and Z_ext = 0 (clamped to the grid)."""
        return self.at(heel, 0.0, 0.0)["rm"]

    def rows(self) -> list[dict]:
        """The grid as table rows (vpp/tables.py), for the cache."""
        out = []
        for i, h in enumerate(self.heels):
            for j, m in enumerate(self.M_ext):
                for n, z in enumerate(self.Z_ext):
                    out.append({"heel": float(h), "M_ext": float(m), "Z_ext": float(z),
                                **{k: float(self.values[k][i, j, n]) for k in self.KEYS},
                                "converged": float(self.converged[i, j, n])})
        return out

    @staticmethod
    def from_rows(rows: list[dict]) -> "HydroTable":
        axes = [np.array(sorted({r[k] for r in rows})) for k in ("heel", "M_ext", "Z_ext")]
        shape = tuple(len(a) for a in axes)
        idx = {(r["heel"], r["M_ext"], r["Z_ext"]): r for r in rows}
        grid = [[[idx[(h, m, z)] for z in axes[2]] for m in axes[1]] for h in axes[0]]
        values = {k: np.array([[[c[k] for c in b] for b in a] for a in grid]).reshape(shape) for k in HydroTable.KEYS}
        conv = np.array([[[bool(c["converged"]) for c in b] for b in a] for a in grid]).reshape(shape)
        return HydroTable(axes[0], axes[1], values, conv, axes[2])
