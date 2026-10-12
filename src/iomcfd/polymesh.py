"""Read an OpenFOAM polyMesh (ASCII or binary, optionally gzipped) without
OpenFOAM, and cut it with planes for plotting.

Only what visualisation needs: points, faces, the patch table, and
`slice_segments`, which intersects every face with a plane. The resulting
segments are exactly the edges of the cut cells, so they draw the mesh on
that plane for any cell shape (hex C-grids, snappyHexMesh polyhedra).
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class PolyMesh:
    points: np.ndarray  # (nPoints, 3)
    face_offsets: np.ndarray  # (nFaces + 1,) start of each face in face_points
    face_points: np.ndarray  # flat point labels
    patches: dict[str, tuple[int, int, str]]  # name -> (startFace, nFaces, type)
    n_cells: int | None = None

    @property
    def n_faces(self) -> int:
        return len(self.face_offsets) - 1

    def patch_faces(self, pattern: str) -> np.ndarray:
        """Face indices of all patches whose name matches the regex."""
        idx = [np.arange(s, s + n) for name, (s, n, _) in self.patches.items() if re.fullmatch(pattern, name)]
        return np.concatenate(idx) if idx else np.array([], dtype=np.int64)

    def face_polygons(self, faces: np.ndarray) -> list[np.ndarray]:
        o, fp = self.face_offsets, self.face_points
        return [self.points[fp[o[f] : o[f + 1]]] for f in faces]


# ---------------------------------------------------------------------------
# File reading


def _open(path: Path) -> bytes:
    if path.is_file():
        return path.read_bytes()
    gz = path.with_name(path.name + ".gz")
    if gz.is_file():
        return gzip.decompress(gz.read_bytes())
    raise FileNotFoundError(path)


def _header(data: bytes) -> tuple[dict[str, str], int]:
    """Parse the FoamFile header; return (entries, offset after it)."""
    m = re.search(rb"FoamFile\s*\{(.*?)\}", data, re.S)
    if not m:
        return {}, 0
    entries = dict(re.findall(r"(\w+)\s+\"?([^;\"]*)\"?\s*;", m.group(1).decode("latin-1")))
    return entries, m.end()


def _next_list(data: bytes, pos: int, binary: bool, dtype, width: int):
    """Read 'N (' + payload + ')' starting at pos. Returns (array, new_pos)."""
    m = re.compile(rb"\s*(\d+)\s*\(").match(data, pos) or re.compile(rb"(?:.|\n)*?(\d+)\s*\(").match(data, pos)
    n = int(m.group(1))
    start = m.end()
    if binary:
        nbytes = n * width * np.dtype(dtype).itemsize
        arr = np.frombuffer(data, dtype=dtype, count=n * width, offset=start)
        end = start + nbytes
        end = data.index(b")", end) + 1
    else:
        end = start
        depth = 1
        while depth:  # find the matching ')'
            c = data[end : end + 1]
            depth += c == b"(" or 0
            depth -= c == b")" or 0
            end += 1
        body = data[start : end - 1].decode("latin-1").replace("(", " ").replace(")", " ")
        arr = np.array(body.split(), dtype=dtype)
    return (arr.reshape(n, width) if width > 1 else arr), end


def _read_field(path: Path, dtype_label, dtype_scalar, width_scalar: int = 1, scalar: bool = False):
    data = _open(path)
    hdr, pos = _header(data)
    binary = hdr.get("format", "ascii") == "binary"
    dtype = dtype_scalar if scalar else dtype_label
    arr, _ = _next_list(data, pos, binary, dtype, width_scalar if scalar else 1)
    return arr, hdr


def _dtypes(hdr: dict[str, str]):
    arch = hdr.get("arch", "label=32;scalar=64")
    label = np.int64 if "label=64" in arch else np.int32
    scalar = np.float32 if "scalar=32" in arch else np.float64
    return label, scalar


def _read_faces(path: Path, label_dtype):
    data = _open(path)
    hdr, pos = _header(data)
    binary = hdr.get("format", "ascii") == "binary"
    if hdr.get("class", "") == "faceCompactList":
        offsets, pos = _next_list(data, pos, binary, label_dtype, 1)
        flat, _ = _next_list(data, pos, binary, label_dtype, 1)
        return offsets.astype(np.int64), flat.astype(np.int64)
    # faceList: "N ( 4(a b c d) 3(a b c) ... )" (ASCII)
    m = re.compile(rb"\s*(\d+)\s*\(").search(data, pos)
    text = data[m.end() :].decode("latin-1")
    faces = re.findall(r"(\d+)\(([^)]*)\)", text)
    sizes = np.array([int(n) for n, _ in faces], dtype=np.int64)
    flat = np.array(" ".join(body for _, body in faces).split(), dtype=np.int64)
    offsets = np.concatenate([[0], np.cumsum(sizes)])
    return offsets, flat


def _read_boundary(path: Path) -> dict[str, tuple[int, int, str]]:
    text = _open(path).decode("latin-1")
    text = re.sub(r"FoamFile\s*\{.*?\}", "", text, flags=re.S)
    out = {}
    for name, body in re.findall(r"(\w+)\s*\{([^}]*)\}", text):
        get = lambda k: re.search(rf"{k}\s+([^;]+);", body)
        if get("nFaces") and get("startFace"):
            out[name] = (int(get("startFace").group(1)), int(get("nFaces").group(1)), get("type").group(1).strip())
    return out


def read(mesh_dir: str | Path) -> PolyMesh:
    d = Path(mesh_dir)
    raw = _open(d / "points")
    hdr, _ = _header(raw)
    label, scalar = _dtypes(hdr)
    points, _ = _read_field(d / "points", label, scalar, 3, scalar=True)
    offsets, flat = _read_faces(d / "faces", label)
    n_cells = None
    try:
        own_hdr, _ = _header(_open(d / "owner"))
        m = re.search(r"nCells:\s*(\d+)", own_hdr.get("note", ""))
        n_cells = int(m.group(1)) if m else None
    except FileNotFoundError:
        pass
    return PolyMesh(np.asarray(points, float), offsets, flat, _read_boundary(d / "boundary"), n_cells)


# ---------------------------------------------------------------------------
# Plane cuts


def slice_segments(mesh: PolyMesh, origin, normal, faces: np.ndarray | None = None) -> np.ndarray:
    """Intersect faces with the plane (origin, normal) -> segments (M, 2, 3)."""
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    dist = (mesh.points - np.asarray(origin, float)) @ n
    o, fp = mesh.face_offsets, mesh.face_points
    df = dist[fp]
    lo = np.minimum.reduceat(df, o[:-1])
    hi = np.maximum.reduceat(df, o[:-1])
    crossing = np.where((lo < 0) & (hi > 0))[0]
    if faces is not None:
        crossing = np.intersect1d(crossing, faces)
    if len(crossing) == 0:
        return np.empty((0, 2, 3))
    sizes = o[crossing + 1] - o[crossing]
    out = []
    for k in np.unique(sizes):  # vectorise over faces with the same vertex count
        fk = crossing[sizes == k]
        idx = fp[o[fk][:, None] + np.arange(k)]  # (m, k)
        dv = dist[idx]
        pv = mesh.points[idx]  # (m, k, 3)
        dn = np.roll(dv, -1, axis=1)
        pn = np.roll(pv, -1, axis=1)
        cross = (dv < 0) != (dn < 0)  # edge k -> k+1 crosses the plane
        t = np.where(cross, dv / np.where(cross, dv - dn, 1.0), 0.0)
        pts = pv + t[..., None] * (pn - pv)
        order = np.argsort(~cross, axis=1, kind="stable")[:, :2]  # first two crossing edges
        rows = np.arange(len(fk))[:, None]
        ok = cross[rows, order].all(axis=1)
        out.append(pts[rows, order][ok])
    return np.concatenate(out) if out else np.empty((0, 2, 3))


def patch_edges(mesh: PolyMesh, faces: np.ndarray) -> np.ndarray:
    """All edges of the given faces as segments (M, 2, 3) (shared edges once)."""
    o, fp = mesh.face_offsets, mesh.face_points
    starts = np.concatenate([fp[o[f] : o[f + 1]] for f in faces]) if len(faces) else np.array([], dtype=np.int64)
    ends = np.concatenate([np.roll(fp[o[f] : o[f + 1]], -1) for f in faces]) if len(faces) else starts
    e = np.unique(np.sort(np.stack([starts, ends], axis=1), axis=1), axis=0)
    return mesh.points[e]
