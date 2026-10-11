r"""Structured C-grid generator for 2D foils, written directly as an OpenFOAM
polyMesh (one cell thick, `empty` front/back).

Topology (i runs along the C, j runs away from the wall):

            farfield (j = NJ-1)
     .--------------------------------------------.
    /                                              |
   /        upper surface        upper wake        | outlet
  (    LE <-------------- TE --------------------->|  (i = NI-1)
   \        lower surface        lower wake        | outlet
    \                                              |  (i = 0)
     '--------------------------------------------'

The wake line (j = 0 behind the TE) is a cut: lower- and upper-wake points
coincide and are merged, so the cells either side are ordinary neighbours.

Grid lines leave the wall exactly along the surface normal and bend smoothly
(exponential blend) to their far-field point, so near-wall cells are
orthogonal: important for transition (kOmegaSSTLM) and y+ ~ 1 meshes.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .distributions import geometric, vinokur
from .foils import Foil


@dataclass
class CMeshSpec:
    chord: float = 1.0  # m
    span: float = 0.1  # m, thickness of the single cell layer (z)
    n_surface: int = 160  # intervals per side (upper and lower)
    ds_le: float = 1.0e-3  # LE spacing / chord
    ds_te: float = 2.0e-3  # TE spacing / chord
    n_wake: int = 64  # intervals from TE to outlet
    wake_length: float = 30.0  # chords from TE to outlet
    n_normal: int = 128  # intervals wall -> farfield
    first_cell: float = 1.0e-5  # m, wall-adjacent cell height
    farfield: float = 30.0  # chords, radius of the C
    wake_outlet_cell: float = 0.01  # chords, wake-line cell height at the outlet
    normal_extent: float = 0.2  # chords: lines follow the wall normal ~this far
    te_blend: float = 0.1  # chords: normals turn vertical over this distance to the TE
    farfield_spread: float = 0.3  # 0 = far-field points follow the wall clustering, 1 = uniform


@dataclass
class MeshInfo:
    n_points: int
    n_cells: int
    n_faces: int
    n_internal_faces: int
    first_cell: float  # m, smallest wall-adjacent cell height
    spec: dict


# ---------------------------------------------------------------------------
# Grid point generation


def _arc_param(foil: Foil, s_from: float, s_to: float, n_dense: int = 4000):
    """Map true arc-length fraction -> spline parameter between two params."""
    s = np.linspace(s_from, s_to, n_dense)
    p = foil.point(s)
    L = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    return lambda frac: np.interp(frac * L[-1], L, s), L[-1]


def _grid_line(p0, n0, p1, t, extent):
    """Line leaving p0 along unit normal n0, turning smoothly towards p1.

    x(t) = p0 + t*L*[(1-w) n0 + w e], w = 1 - exp(-t*L/extent), e = (p1-p0)/L.
    Orthogonal at the wall, |dx/dt| = L at t=0 (so first cell = L*t[1]), and
    ends at p1 (to within exp(-L/extent)).
    """
    L = float(np.hypot(*(p1 - p0)))
    e = (p1 - p0) / L
    w = (1.0 - np.exp(-t * L / extent))[:, None]
    return p0 + (t * L)[:, None] * ((1.0 - w) * n0 + w * e)


def _smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def generate(foil: Foil, spec: CMeshSpec) -> tuple[np.ndarray, int]:
    """Return grid points P[NI, NJ, 2] (metres) and n_wake."""
    c = spec.chord
    R = spec.farfield * c

    # --- wall distribution: lower TE->LE then upper LE->TE ----------------
    fr = vinokur(spec.n_surface, spec.ds_le / 1.0, spec.ds_te / 1.0)  # LE->TE fractions
    # spacing is relative to each side's arc length (~1 chord); close enough
    up_map, _ = _arc_param(foil, foil.s_le, 0.0)
    lo_map, _ = _arc_param(foil, foil.s_le, foil.perimeter)
    s_up = up_map(fr)  # LE -> TE
    s_lo = lo_map(fr)  # LE -> TE
    s_wall = np.concatenate([s_lo[::-1], s_up[1:]])  # TE(lower) -> LE -> TE(upper)
    wall = foil.point(s_wall) * c
    nrm = foil.normal(s_wall)
    # Sharp TE: turn the normals vertical over the last `te_blend` chords so the
    # foil lines join the (vertical) wake lines without crossing them.
    b = _smoothstep((wall[:, 0] / c - (1.0 - spec.te_blend)) / spec.te_blend)[:, None]
    vert = np.zeros_like(nrm)
    n_lo = spec.n_surface + 1
    vert[:n_lo, 1], vert[n_lo:, 1] = -1.0, 1.0
    vert[n_lo - 1] = (-1.0, 0.0)  # LE (never blended, x/c = 0)
    nrm = (1.0 - b) * nrm + b * vert
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)

    # --- wake line ----------------------------------------------------------
    te = wall[-1]
    ds_te_m = float(np.hypot(*(wall[-1] - wall[-2])))
    xw = geometric(spec.n_wake, ds_te_m, spec.wake_length * c)  # 0..W from TE
    wake_up = np.stack([te[0] + xw, np.full_like(xw, te[1])], axis=1)
    wake_lo = wake_up[::-1]

    n_w = spec.n_wake
    inner = np.vstack([wake_lo[:-1], wall, wake_up[1:]])  # C-line, i = 0..NI-1
    normals = np.vstack(
        [np.tile((0.0, -1.0), (n_w, 1)), nrm, np.tile((0.0, 1.0), (n_w, 1))]
    )
    NI = len(inner)
    i_le = n_w + spec.n_surface

    # --- far-field point for each C-line point -----------------------------
    theta = np.arctan2(normals[:, 1], normals[:, 0]) % (2 * math.pi)
    # switch from circle to straight top/bottom where the normal is vertical
    up_idx = np.arange(i_le, NI - n_w)
    lo_idx = np.arange(i_le, n_w - 1, -1)  # LE -> TE on lower side
    sw_up = up_idx[np.argmax(theta[up_idx] <= math.pi / 2)] if np.any(theta[up_idx] <= math.pi / 2) else up_idx[-1]
    sw_lo = lo_idx[np.argmax(theta[lo_idx] >= 3 * math.pi / 2)] if np.any(theta[lo_idx] >= 3 * math.pi / 2) else lo_idx[-1]
    x_c = 0.5 * (inner[sw_up, 0] + inner[sw_lo, 0])
    x_te = te[0]

    outer = np.zeros_like(inner)

    def straight(i, x_sw, sign):
        x = inner[i, 0]
        xo = x_c + (x - x_sw) / max(x_te - x_sw, 1e-12) * (x_te - x_c) if x <= x_te else x
        outer[i] = (xo, sign * R)

    # upper side: LE -> switch on the circle, switch -> TE straight
    th_run = math.pi
    for i in up_idx:
        if i < sw_up:
            th_run = min(th_run, max(theta[i], math.pi / 2))
            outer[i] = (x_c + R * math.cos(th_run), R * math.sin(th_run))
        else:
            straight(i, inner[sw_up, 0], 1.0)
    th_run = math.pi
    for i in lo_idx:
        if i > sw_lo:
            th = theta[i] if theta[i] >= math.pi / 2 else theta[i] + 2 * math.pi
            th_run = max(th_run, min(th, 1.5 * math.pi))
            outer[i] = (x_c + R * math.cos(th_run), R * math.sin(th_run))
        else:
            straight(i, inner[sw_lo, 0], -1.0)
    outer[i_le] = (x_c - R, 0.0)
    for i in range(n_w):  # lower wake
        straight(i, inner[sw_lo, 0], -1.0)
    for i in range(NI - n_w, NI):  # upper wake
        straight(i, inner[sw_up, 0], 1.0)

    # Spread the far-field points: blend their arc-length position along the
    # outer C with a uniform distribution. Without this the TE/LE clustering
    # reaches the far field as very tall thin cells (bad non-orthogonality).
    x_out = inner[-1, 0]
    seg = np.array([x_out - x_c, math.pi * R, x_out - x_c])  # bottom, arc, top
    S_tot = float(seg.sum())

    def to_S(p):
        x, y = p
        if y <= -R * (1 - 1e-12) and x >= x_c:
            return x_out - x
        if y >= R * (1 - 1e-12) and x >= x_c:
            return seg[0] + seg[1] + (x - x_c)
        phi = math.atan2(y, x - x_c)  # -pi/2 (bottom) .. -pi/pi (front) .. pi/2 (top)
        ang = (-math.pi / 2 - phi) % (2 * math.pi)  # 0 at bottom, pi at top
        return seg[0] + R * ang

    def from_S(S):
        if S <= seg[0]:
            return (x_out - S, -R)
        if S >= seg[0] + seg[1]:
            return (x_c + S - seg[0] - seg[1], R)
        phi = -math.pi / 2 - (S - seg[0]) / R
        return (x_c + R * math.cos(phi), R * math.sin(phi))

    S = np.array([to_S(p) for p in outer])
    S = np.maximum.accumulate(S)
    S = (1.0 - spec.farfield_spread) * S + spec.farfield_spread * np.linspace(0.0, S_tot, NI)
    outer = np.array([from_S(v) for v in S])

    # --- grid lines ---------------------------------------------------------
    NJ = spec.n_normal + 1
    P = np.zeros((NI, NJ, 2))
    for i in range(NI):
        p0, p1 = inner[i], outer[i]
        L = float(np.hypot(*(p1 - p0)))
        t = geometric(spec.n_normal, spec.first_cell / L, 1.0)
        if i < n_w or i >= NI - n_w:
            # Wake: blend towards a coarser wall-normal distribution downstream.
            # Blending point positions (not h0) keeps neighbouring lines'
            # layers aligned, which matters for the tall far-field cells.
            w = abs(p0[0] - x_te) / (spec.wake_length * c)
            t_out = geometric(spec.n_normal, spec.wake_outlet_cell * c / L, 1.0)
            t = (1.0 - w) * t + w * t_out
        P[i] = _grid_line(p0, normals[i], p1, t, spec.normal_extent * c)
    # exact merge of the wake cut (upper-wake j=0 points == lower-wake ones)
    P[NI - 1 - np.arange(n_w + 1), 0] = P[np.arange(n_w + 1), 0]
    return P, n_w


# ---------------------------------------------------------------------------
# polyMesh writer

_HEADER = """/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Generated by iomcfd.geometry.cmesh
    \\\\  /    A nd           |
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    arch        "LSB;label=32;scalar=64";
    class       {cls};
    note        "{note}";
    location    "constant/polyMesh";
    object      {obj};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

"""


def _write_list(path: Path, cls: str, obj: str, note: str, rows: list[str]) -> None:
    with open(path, "w") as f:
        f.write(_HEADER.format(cls=cls, obj=obj, note=note))
        f.write(f"{len(rows)}\n(\n")
        f.write("\n".join(rows))
        f.write("\n)\n")


def write_polymesh(P: np.ndarray, n_w: int, span: float, mesh_dir: Path) -> MeshInfo:
    NI, NJ, _ = P.shape
    i_te_up = NI - 1 - n_w

    # unique 2D point ids (upper-wake j=0 points merge onto lower-wake ones)
    pid = -np.ones((NI, NJ), dtype=np.int64)
    pts = []
    for i in range(NI):
        for j in range(NJ):
            if j == 0 and i >= i_te_up:
                continue
            pid[i, j] = len(pts)
            pts.append(P[i, j])
    for i in range(i_te_up, NI):
        pid[i, 0] = pid[NI - 1 - i, 0]
    pts = np.asarray(pts)
    np2 = len(pts)

    nci, ncj = NI - 1, NJ - 1

    def cid(ci, cj):
        return ci * ncj + cj

    def a(ci, cj):  # 4 corners of a cell, back plane
        return pid[ci, cj], pid[ci + 1, cj], pid[ci + 1, cj + 1], pid[ci, cj + 1]

    internal = []  # (owner, neighbour, face points)
    for ci in range(nci):
        for cj in range(ncj):
            p_a, p_b, p_c, p_d = a(ci, cj)
            own = cid(ci, cj)
            if ci + 1 < nci:  # east face, normal +i
                internal.append((own, cid(ci + 1, cj), (p_b, p_c, p_c + np2, p_b + np2)))
            if cj + 1 < ncj:  # north face, normal +j
                internal.append((own, cid(ci, cj + 1), (p_d, p_d + np2, p_c + np2, p_c)))
    for ci in range(n_w):  # wake cut: lower-wake cell owns the face
        p_a, p_b, _, _ = a(ci, 0)
        internal.append((cid(ci, 0), cid(NI - 2 - ci, 0), (p_a, p_b, p_b + np2, p_a + np2)))
    internal.sort(key=lambda f: (f[0], f[1]))

    patches: dict[str, tuple[str, list]] = {
        "foil": ("wall", []),
        "farfield": ("patch", []),
        "outlet": ("patch", []),
        "frontAndBack": ("empty", []),
    }
    for ci in range(n_w, nci - n_w):
        p_a, p_b, _, _ = a(ci, 0)
        patches["foil"][1].append((cid(ci, 0), (p_a, p_b, p_b + np2, p_a + np2)))
    for ci in range(nci):
        _, _, p_c, p_d = a(ci, ncj - 1)
        patches["farfield"][1].append((cid(ci, ncj - 1), (p_d, p_d + np2, p_c + np2, p_c)))
    for cj in range(ncj):
        p_a, _, _, p_d = a(0, cj)
        patches["outlet"][1].append((cid(0, cj), (p_a, p_a + np2, p_d + np2, p_d)))
    for cj in range(ncj):
        _, p_b, p_c, _ = a(nci - 1, cj)
        patches["outlet"][1].append((cid(nci - 1, cj), (p_b, p_c, p_c + np2, p_b + np2)))
    for ci in range(nci):
        for cj in range(ncj):
            p_a, p_b, p_c, p_d = a(ci, cj)
            patches["frontAndBack"][1].append((cid(ci, cj), (p_a, p_d, p_c, p_b)))
            patches["frontAndBack"][1].append((cid(ci, cj), (p_a + np2, p_b + np2, p_c + np2, p_d + np2)))

    faces = [f[2] for f in internal]
    owner = [f[0] for f in internal]
    neigh = [f[1] for f in internal]
    bnd = []
    start = len(faces)
    for name, (ptype, flist) in patches.items():
        bnd.append((name, ptype, len(flist), start))
        start += len(flist)
        faces += [f[1] for f in flist]
        owner += [f[0] for f in flist]

    n_cells = nci * ncj
    n_faces = len(faces)
    note = f"nPoints:{2 * np2}  nCells:{n_cells}  nFaces:{n_faces}  nInternalFaces:{len(internal)}"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    xyz = np.vstack([np.column_stack([pts, np.zeros(np2)]), np.column_stack([pts, np.full(np2, span)])])
    _write_list(mesh_dir / "points", "vectorField", "points", "", [f"({x:.10g} {y:.10g} {z:.10g})" for x, y, z in xyz])
    _write_list(mesh_dir / "faces", "faceList", "faces", "", [f"4({f[0]} {f[1]} {f[2]} {f[3]})" for f in faces])
    _write_list(mesh_dir / "owner", "labelList", "owner", note, [str(o) for o in owner])
    _write_list(mesh_dir / "neighbour", "labelList", "neighbour", note, [str(n) for n in neigh])

    groups = {"wall": "wall", "empty": "empty"}
    with open(mesh_dir / "boundary", "w") as f:
        f.write(_HEADER.format(cls="polyBoundaryMesh", obj="boundary", note=""))
        f.write(f"{len(bnd)}\n(\n")
        for name, ptype, nf, sf in bnd:
            grp = groups.get(ptype, "freestream")
            f.write(f"    {name}\n    {{\n        type            {ptype};\n")
            f.write(f"        inGroups        1({grp});\n")
            f.write(f"        nFaces          {nf};\n        startFace       {sf};\n    }}\n")
        f.write(")\n")

    return MeshInfo(
        n_points=2 * np2,
        n_cells=n_cells,
        n_faces=n_faces,
        n_internal_faces=len(internal),
        first_cell=float(np.min(np.hypot(*(P[n_w:NI - n_w, 1] - P[n_w:NI - n_w, 0]).T))),
        spec={},
    )


def quality(P: np.ndarray) -> dict:
    """2D non-orthogonality (deg) and aspect ratio, as checkMesh measures them."""
    C = 0.25 * (P[:-1, :-1] + P[1:, :-1] + P[1:, 1:] + P[:-1, 1:])

    def ang(fa, fb, c0, c1):
        t = fb - fa
        n = np.stack([t[..., 1], -t[..., 0]], -1)
        d = c1 - c0
        cosv = np.abs(np.sum(n * d, -1)) / (np.linalg.norm(n, axis=-1) * np.linalg.norm(d, axis=-1))
        return np.degrees(np.arccos(np.clip(cosv, 0, 1)))

    ai = ang(P[1:-1, :-1], P[1:-1, 1:], C[:-1], C[1:])
    aj = ang(P[:-1, 1:-1], P[1:, 1:-1], C[:, :-1], C[:, 1:])
    di = np.linalg.norm(P[1:, :-1] - P[:-1, :-1], axis=-1)
    dj = np.linalg.norm(P[:-1, 1:] - P[:-1, :-1], axis=-1)
    ar = np.maximum(di / dj, dj / di)
    allang = np.concatenate([ai.ravel(), aj.ravel()])
    return {
        "max_nonortho": float(allang.max()),
        "mean_nonortho": float(allang.mean()),
        "n_nonortho_gt70": int((allang > 70).sum()),
        "max_aspect": float(ar.max()),
    }


def cell_areas(P: np.ndarray) -> np.ndarray:
    """Signed area of every 2D cell (all must be > 0 for a valid mesh)."""
    a, b = P[:-1, :-1], P[1:, :-1]
    c, d = P[1:, 1:], P[:-1, 1:]
    cross = lambda u, v: u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]
    return 0.5 * (cross(c - a, d - b))


def build(foil: Foil, spec: CMeshSpec, mesh_dir: Path) -> MeshInfo:
    P, n_w = generate(foil, spec)
    areas = cell_areas(P)
    if np.any(areas <= 0):
        bad = np.argwhere(areas <= 0)
        raise RuntimeError(
            f"C-mesh has {len(bad)} inverted cells (first at i,j={tuple(bad[0])}); "
            "try a larger normal_extent/te_blend or check the foil geometry"
        )
    info = write_polymesh(P, n_w, spec.span, Path(mesh_dir))
    info.spec = asdict(spec)
    return info
