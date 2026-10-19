r"""Axisymmetric (wedge) meshes around a body of revolution: a keel bulb alone.

The meridian plane (x along the axis, r up) is meshed with the C-grid of
cmesh, which is made for 2D sections: the body's profile r(x) is the upper
half of a symmetric "section", and only the upper half of the C is kept.

            farfield
         .-----------------------------------.
        /                                    |
       /  i = 0 (axis)   body                | outlet
      (---------- nose ======== tail --------|
                          base | block B     |
                     axis ---------------------

* Ahead of the nose the C's centre line lies on the axis.
* A pointed tail's wake line lies on the axis too.
* A blunt base (Dress's laminar body) sheds its wake line from the base's
  edge. A second block, B, fills the space between that line and the axis.
  Its upstream face is the base.

The 2D quad mesh becomes an OpenFOAM `wedge` mesh: every point is turned by
+-wedge/2 about the x axis. Points on the axis stay one point, so faces on
the axis vanish and the cells next to it become prisms. Forces on the body
are the wedge's share of the whole body's: 360 / wedge of them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from . import cmesh
from .distributions import geometric
from .foils import Foil


@dataclass
class Profile:
    """Body of revolution of unit length: radius r(x), nose at x = 0
    (r = 0), tail at x = 1 (r = 0, or the radius of a blunt base)."""

    name: str
    x: np.ndarray
    r: np.ndarray

    @property
    def base(self) -> float:
        return float(self.r[-1])

    def foil(self) -> Foil:
        """The profile as a symmetric 'section' (TE -> upper -> LE -> lower),
        open at a blunt base."""
        x = np.concatenate([self.x[::-1], self.x[1:]])
        y = np.concatenate([self.r[::-1], -self.r[1:]])
        return Foil(self.name, x, y)

    def dense(self, n: int = 4001) -> tuple[np.ndarray, np.ndarray]:
        """The profile on a fine cosine grid, interpolated along the spline
        of `foil` (smooth through tabulated points)."""
        up = self.foil().surface("upper", n)
        return up[:, 0], np.clip(up[:, 1], 0.0, None)

    def volume(self) -> float:
        x, r = self.dense()
        return float(math.pi * trapezoid(r**2, x))

    def wetted_area(self) -> float:
        """Side surface, without a blunt base."""
        x, r = self.dense()
        return float(2 * math.pi * np.sum(0.5 * (r[1:] + r[:-1]) * np.hypot(np.diff(x), np.diff(r))))

    def centroid(self) -> float:
        x, r = self.dense()
        return float(trapezoid(r**2 * x, x) / trapezoid(r**2, x))

    def max_radius(self) -> tuple[float, float]:
        """(largest radius, its x)."""
        x, r = self.dense()
        i = int(np.argmax(r))
        return float(r[i]), float(x[i])


def naca_profile(thickness: float, n: int = 401) -> Profile:
    """NACA 4-digit thickness distribution (closed tail) as the radius:
    diameter = `thickness` x length, largest at 30 %, round nose."""
    x = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
    r = 5 * thickness * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
    r[0] = r[-1] = 0.0
    return Profile(f"naca thickness, L/D {1 / thickness:.4g}", x, np.clip(r, 0.0, None))


def bulb_profile(fineness: float, max_at: float = 0.4, tail_exp: float = 2.0, n: int = 401) -> Profile:
    """appendage3d's bulb (geometry.appendages.bulb_profile): an elliptic
    nose to the largest diameter at `max_at`, then r ~ 1 - u^tail_exp to a
    pointed tail. Diameter = length / fineness."""
    m, R = max_at, 0.5 / fineness
    xi = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
    # cluster points at the round nose: a cosine grid on the nose ellipse
    nose = m * (1 - np.cos(np.linspace(0, 0.5 * math.pi, n // 2)))
    xi = np.unique(np.concatenate([nose, xi[xi > m]]))
    r = np.where(xi < m, R * np.sqrt(np.clip(1 - ((m - xi) / m) ** 2, 0, 1)),
                 R * np.clip(1 - ((xi - m) / (1 - m)) ** tail_exp, 0, 1))
    r[0] = r[-1] = 0.0
    return Profile(f"bulb L/D {fineness:g}, max at {max_at:g}, tail {tail_exp:g}", xi, r)


def file_profile(path: str | Path) -> Profile:
    """Two columns x, r (any length unit, '#' comments, a header line),
    nose first. Scaled to unit length."""
    path = Path(path)
    rows = []
    for ln in path.read_text().splitlines():
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        try:
            rows.append([float(v) for v in ln.replace(",", " ").split()[:2]])
        except ValueError:
            continue  # header
    a = np.array(rows)
    x, r = a[:, 0] - a[0, 0], a[:, 1]
    L = x[-1]
    return Profile(path.stem, x / L, r / L)


# ---------------------------------------------------------------------------
# Grid


@dataclass
class Grid2D:
    """Quad mesh of the meridian plane: points (x, r) [m], cells as 4 point
    indices counter-clockwise, and the patch of every boundary edge (edges
    with both points on the axis need none)."""

    points: np.ndarray
    cells: np.ndarray
    boundary: dict[tuple[int, int], str]
    first_cell: float


def generate(profile: Profile, spec: cmesh.CMeshSpec, n_base: int = 40) -> Grid2D:
    """Upper half of cmesh's C-grid around the profile, plus block B behind
    a blunt base (n_base cells from the axis to the base's edge)."""
    L = spec.chord
    P, n_w = cmesh.generate(profile.foil(), spec)
    i_le = n_w + spec.n_surface  # the C-line point at the nose
    H = P[i_le:].copy()
    NI, NJ = H.shape[:2]
    i_te = spec.n_surface  # the tail, or the base's edge
    rb = profile.base * L
    H[0, :, 1] = 0.0  # the C's centre line ahead of the nose: the axis
    H[0, 0] = (0.0, 0.0)
    H[i_te:, 0, 1] = rb  # wake line, from the tail or the base's edge
    H[i_te, 0, 0] = L

    pid = np.arange(NI * NJ).reshape(NI, NJ)
    pts = [H.reshape(-1, 2)]
    cells = [np.stack([pid[:-1, :-1], pid[1:, :-1], pid[1:, 1:], pid[:-1, 1:]], axis=-1).reshape(-1, 4)]
    bnd: dict[tuple[int, int], str] = {}

    def edge(a, b, name):
        bnd[(min(a, b), max(a, b))] = name

    for i in range(i_te):
        edge(pid[i, 0], pid[i + 1, 0], "body")
    for i in range(NI - 1):
        edge(pid[i, NJ - 1], pid[i + 1, NJ - 1], "farfield")
    for j in range(NJ - 1):
        edge(pid[NI - 1, j], pid[NI - 1, j + 1], "outlet")

    if rb > 0:
        # block B: columns i_te .. NI-1 of the wake line, k = 0 (axis) .. n_base
        # (the wake line itself). Next to the wake line its cells are as high
        # as the C-grid's first cells there; they grow towards the axis.
        cols = np.arange(i_te, NI)
        Q = np.zeros((len(cols), n_base + 1), dtype=np.int64)
        new = []
        for c, i in enumerate(cols):
            dr = min(H[i, 1, 1] - H[i, 0, 1], rb / n_base)  # uniform where the C-grid's cells are coarser
            g = geometric(n_base, dr, rb)  # from the wake line down
            rk = rb - g[::-1]
            Q[c, n_base] = pid[i, 0]
            for k in range(n_base):
                Q[c, k] = NI * NJ + len(new)
                new.append((H[i, 0, 0], max(rk[k], 0.0)))
        pts.append(np.array(new))
        cells.append(np.stack([Q[:-1, :-1], Q[1:, :-1], Q[1:, 1:], Q[:-1, 1:]], axis=-1).reshape(-1, 4))
        for k in range(n_base):
            edge(Q[0, k], Q[0, k + 1], "base")
            edge(Q[-1, k], Q[-1, k + 1], "outlet")

    points = np.vstack(pts)
    points[:, 1] = np.where(points[:, 1] < 1e-12 * L, 0.0, points[:, 1])
    cells = np.vstack(cells)
    first = float(np.min(np.hypot(*(H[1:i_te, 1] - H[1:i_te, 0]).T)))
    return Grid2D(points, cells, bnd, first)


def cell_areas(g: Grid2D) -> np.ndarray:
    p = g.points[g.cells]  # (M, 4, 2)
    a, b, c, d = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    cross = lambda u, v: u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    return 0.5 * cross(c - a, d - b)


# ---------------------------------------------------------------------------
# polyMesh

PATCH_TYPES = {"body": "wall", "base": "wall", "farfield": "patch", "outlet": "patch"}


def write_wedge(g: Grid2D, wedge: float, mesh_dir: Path) -> cmesh.MeshInfo:
    """Write the grid as an OpenFOAM wedge mesh (symmetric about z = 0)."""
    on_axis = g.points[:, 1] == 0.0
    N = len(g.points)
    a = math.radians(0.5 * wedge)
    back = np.arange(N)
    front = np.where(on_axis, back, N + np.cumsum(~on_axis) - 1)
    n_pts = N + int((~on_axis).sum())
    xyz = np.zeros((n_pts, 3))
    x, r = g.points[:, 0], g.points[:, 1]
    xyz[:N] = np.column_stack([x, r * math.cos(a), -r * math.sin(a)])
    xyz[front[~on_axis]] = np.column_stack([x, r * math.cos(a), r * math.sin(a)])[~on_axis]

    def face(pts):
        out = []
        for p in pts:  # drop repeated points (a side face with one end on the axis: a triangle)
            if p not in out:
                out.append(int(p))
        return out if len(out) >= 3 else None

    edges: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for ci, c in enumerate(g.cells):
        for k in range(4):
            p, q = int(c[k]), int(c[(k + 1) % 4])
            edges.setdefault((min(p, q), max(p, q)), []).append((ci, p, q))
    internal, patches = [], {name: [] for name in ("body", "base", "farfield", "outlet")}
    for key, uses in edges.items():
        if on_axis[key[0]] and on_axis[key[1]]:
            continue  # on the axis: no face
        (own, p, q) = min(uses)
        f = face((back[p], back[q], front[q], front[p]))  # outward from the owner (p -> q counter-clockwise)
        if f is None:
            continue
        if len(uses) == 2:
            internal.append((own, max(u[0] for u in uses), f))
        elif len(uses) == 1:
            if key not in g.boundary:
                raise RuntimeError(f"boundary edge {key} at {g.points[list(key)]} has no patch")
            patches[g.boundary[key]].append((own, f))
        else:
            raise RuntimeError(f"edge {key} shared by {len(uses)} cells")
    internal.sort(key=lambda t: (t[0], t[1]))
    wedges = {"front": [], "back": []}
    for ci, c in enumerate(g.cells):
        wedges["front"].append((ci, face([front[i] for i in c])))
        wedges["back"].append((ci, face([back[i] for i in c[::-1]])))

    faces = [f for _, _, f in internal]
    owner = [o for o, _, _ in internal]
    neigh = [n for _, n, _ in internal]
    bnd = []
    groups = [(n, PATCH_TYPES[n], v) for n, v in patches.items() if v or n != "base"]
    groups += [(n, "wedge", v) for n, v in wedges.items()]
    for name, ptype, flist in groups:
        bnd.append((name, ptype, len(flist), len(faces)))
        faces += [f for _, f in flist]
        owner += [o for o, _ in flist]

    mesh_dir = Path(mesh_dir)
    mesh_dir.mkdir(parents=True, exist_ok=True)
    note = f"nPoints:{n_pts}  nCells:{len(g.cells)}  nFaces:{len(faces)}  nInternalFaces:{len(internal)}"
    w = cmesh._write_list
    w(mesh_dir / "points", "vectorField", "points", "", [f"({px:.10g} {py:.10g} {pz:.10g})" for px, py, pz in xyz])
    w(mesh_dir / "faces", "faceList", "faces", "", [f"{len(f)}({' '.join(map(str, f))})" for f in faces])
    w(mesh_dir / "owner", "labelList", "owner", note, [str(o) for o in owner])
    w(mesh_dir / "neighbour", "labelList", "neighbour", note, [str(n) for n in neigh])
    grp = {"wall": "wall", "wedge": "wedge"}
    with open(mesh_dir / "boundary", "w") as f:
        f.write(cmesh._HEADER.format(cls="polyBoundaryMesh", obj="boundary", note=""))
        f.write(f"{len(bnd)}\n(\n")
        for name, ptype, nf, sf in bnd:
            f.write(f"    {name}\n    {{\n        type            {ptype};\n")
            f.write(f"        inGroups        1({grp.get(ptype, 'freestream')});\n")
            f.write(f"        nFaces          {nf};\n        startFace       {sf};\n    }}\n")
        f.write(")\n")
    return cmesh.MeshInfo(n_points=n_pts, n_cells=len(g.cells), n_faces=len(faces),
                          n_internal_faces=len(internal), first_cell=g.first_cell, spec={})


def build(profile: Profile, spec: cmesh.CMeshSpec, mesh_dir: Path, n_base: int = 40, wedge: float = 5.0) -> cmesh.MeshInfo:
    g = generate(profile, spec, n_base)
    areas = cell_areas(g)
    if np.any(areas <= 0):
        bad = int(np.argmax(areas <= 0))
        raise RuntimeError(f"axisymmetric mesh has {int((areas <= 0).sum())} inverted cells "
                           f"(first near {g.points[g.cells[bad]].mean(axis=0)})")
    info = write_wedge(g, wedge, mesh_dir)
    info.spec = {"n_base": n_base, "wedge": wedge}
    return info
