"""Minimal triangle-surface utilities (no external mesh library needed).

A surface is (vertices[N,3], triangles[M,3]). Read/write STL (ASCII or
binary, as exported by Fusion 360), transform, measure, and combine.

Coordinate convention used across all 3D projects (the "boat frame"):
    x  aft (flow direction for zero leeway; bow is at small x)
    y  to port
    z  up; z = 0 is the design waterline
Fusion 360 exports in mm with whatever axes the design uses; set
`stl_scale: 0.001` and `stl_rotate` in the study to map it into this frame.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Surface:
    vertices: np.ndarray  # (N, 3) float
    triangles: np.ndarray  # (M, 3) int
    name: str = "surface"

    # -- measures -----------------------------------------------------------
    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    def normals(self) -> np.ndarray:
        v = self.vertices[self.triangles]
        n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        return n

    def area(self) -> float:
        return float(0.5 * np.linalg.norm(self.normals(), axis=1).sum())

    def volume(self) -> float:
        """Enclosed volume (positive for a closed, outward-oriented surface)."""
        v = self.vertices[self.triangles]
        return float(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6.0)

    def centroid(self) -> np.ndarray:
        """Centroid of the enclosed volume."""
        v = self.vertices[self.triangles]
        vol = np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])) / 6.0
        c = (v[:, 0] + v[:, 1] + v[:, 2]) / 4.0
        return (vol[:, None] * c).sum(axis=0) / vol.sum()

    def is_closed(self) -> bool:
        edges = np.sort(np.concatenate([self.triangles[:, [0, 1]], self.triangles[:, [1, 2]], self.triangles[:, [2, 0]]]), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        return bool(np.all(counts == 2))

    # -- transforms (return new surfaces) -----------------------------------
    def scaled(self, s: float | tuple[float, float, float]) -> "Surface":
        return Surface(self.vertices * np.asarray(s, float), self.triangles.copy(), self.name)

    def translated(self, d) -> "Surface":
        return Surface(self.vertices + np.asarray(d, float), self.triangles.copy(), self.name)

    def rotated(self, axis: str, deg: float, about=(0.0, 0.0, 0.0)) -> "Surface":
        R = rotation(axis, deg)
        o = np.asarray(about, float)
        return Surface((self.vertices - o) @ R.T + o, self.triangles.copy(), self.name)

    def flipped(self) -> "Surface":
        return Surface(self.vertices.copy(), self.triangles[:, ::-1].copy(), self.name)

    def oriented_outward(self) -> "Surface":
        return self.flipped() if self.volume() < 0 else self

    # -- io -----------------------------------------------------------------
    def write(self, path: str | Path, binary: bool = False) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        v = self.vertices[self.triangles]
        n = self.normals()
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        n = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)
        if binary:
            with open(path, "wb") as f:
                f.write(self.name.encode()[:80].ljust(80, b" "))
                f.write(struct.pack("<I", len(v)))
                rec = np.zeros(len(v), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
                rec["n"], rec["v"] = n, v
                f.write(rec.tobytes())
            return
        with open(path, "w") as f:
            f.write(f"solid {self.name}\n")
            for ni, tri in zip(n, v):
                f.write(f"  facet normal {ni[0]:.6e} {ni[1]:.6e} {ni[2]:.6e}\n    outer loop\n")
                for p in tri:
                    f.write(f"      vertex {p[0]:.9e} {p[1]:.9e} {p[2]:.9e}\n")
                f.write("    endloop\n  endfacet\n")
            f.write(f"endsolid {self.name}\n")


def write_multi(path: str | Path, surfaces: list["Surface"]) -> None:
    """One ASCII STL with a `solid <name>` block per surface. snappyHexMesh
    turns each solid (region) into its own patch, e.g. appendages_fin."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part.stl")
    with open(path, "w") as out:
        for s in surfaces:
            s.write(tmp)
            out.write(tmp.read_text())
    tmp.unlink()


def rotation(axis: str, deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return {
        "x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
        "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
        "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]),
    }[axis]


def merge(surfaces: list[Surface], name: str = "merged") -> Surface:
    verts, tris, off = [], [], 0
    for s in surfaces:
        verts.append(s.vertices)
        tris.append(s.triangles + off)
        off += len(s.vertices)
    return Surface(np.vstack(verts), np.vstack(tris), name)


def read(path: str | Path, name: str | None = None) -> Surface:
    """Read ASCII or binary STL; merges duplicate vertices."""
    path = Path(path)
    data = path.read_bytes()
    tri_pts: np.ndarray
    is_ascii = data[:5].lower() == b"solid" and b"facet" in data[:1024]
    if not is_ascii and len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + 50 * n != len(data):
            is_ascii = True
    if is_ascii:
        pts = [list(map(float, line.split()[1:4])) for line in data.decode(errors="replace").splitlines()
               if line.strip().startswith("vertex")]
        tri_pts = np.array(pts, float).reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", data[80:84])[0]
        rec = np.frombuffer(data, dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n, offset=84)
        tri_pts = rec["v"].astype(float)
    flat = tri_pts.reshape(-1, 3)
    key = np.round(flat / (np.ptp(flat, axis=0).max() * 1e-9 + 1e-30)).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return Surface(flat[idx], inv.reshape(-1, 3), name or path.stem)


# ---------------------------------------------------------------------------
# Construction helpers


def loft(rings: list[np.ndarray], cap_start: bool = True, cap_end: bool = True, name: str = "loft") -> Surface:
    """Surface through a list of closed rings (each (K,3), same K, same order).

    Caps are fans from the ring centroid (fine for star-shaped sections such
    as foils and circles).
    """
    K = len(rings[0])
    verts = np.vstack(rings)
    tris = []
    for r in range(len(rings) - 1):
        a0, b0 = r * K, (r + 1) * K
        for k in range(K):
            k1 = (k + 1) % K
            tris.append((a0 + k, a0 + k1, b0 + k1))
            tris.append((a0 + k, b0 + k1, b0 + k))
    extra = []
    # Side triangles walk ring edge k -> k+1 on the first ring and k+1 -> k on
    # the last; each cap must walk the same edges the other way round.
    for flag, r, start in ((cap_start, 0, True), (cap_end, len(rings) - 1, False)):
        if not flag:
            continue
        c = len(verts) + len(extra)
        extra.append(rings[r].mean(axis=0))
        base = r * K
        for k in range(K):
            a, b = base + k, base + (k + 1) % K
            tris.append((c, b, a) if start else (c, a, b))
    if extra:
        verts = np.vstack([verts, np.array(extra)])
    return Surface(verts, np.array(tris, dtype=np.int64), name).oriented_outward()


def revolve(x: np.ndarray, r: np.ndarray, n_theta: int = 48, name: str = "body",
            section: np.ndarray | None = None) -> Surface:
    """Body of revolution about the x axis from a profile r(x).

    r must be 0 at both ends (pointed or rounded tips). `section`: the cross
    section at r = 1 as a closed ring of (y, z) points (n_theta of them), for
    a body whose sections are all the same non-circular shape scaled by r;
    default a circle.
    """
    if section is None:
        th = np.linspace(0, 2 * math.pi, n_theta, endpoint=False)
        section = np.column_stack([np.cos(th), np.sin(th)])
    n_theta = len(section)
    inner = [np.column_stack([np.full(n_theta, xi), ri * section[:, 0], ri * section[:, 1]])
             for xi, ri in zip(x[1:-1], r[1:-1])]
    verts = [np.array([[x[0], 0.0, 0.0]])] + inner + [np.array([[x[-1], 0.0, 0.0]])]
    V = np.vstack(verts)
    tris = []
    nose, tail = 0, len(V) - 1
    for k in range(n_theta):
        tris.append((nose, 1 + (k + 1) % n_theta, 1 + k))
    for ring in range(len(inner) - 1):
        a0, b0 = 1 + ring * n_theta, 1 + (ring + 1) * n_theta
        for k in range(n_theta):
            k1 = (k + 1) % n_theta
            tris.append((a0 + k, a0 + k1, b0 + k1))
            tris.append((a0 + k, b0 + k1, b0 + k))
    last = 1 + (len(inner) - 1) * n_theta
    for k in range(n_theta):
        tris.append((tail, last + k, last + (k + 1) % n_theta))
    return Surface(V, np.array(tris, dtype=np.int64), name).oriented_outward()
