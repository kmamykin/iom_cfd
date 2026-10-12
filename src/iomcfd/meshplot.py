"""Mesh figures for study reports (matplotlib; no OpenFOAM or ParaView needed).

Each project describes its standard views through `Project.mesh_views()`:
a list of plane cuts (or patch projections) with a zoom window. This module
reads `constant/polyMesh`, cuts it, and draws the cut cells, with wall
patches highlighted and mesh-quality numbers from checkMesh/snappyHexMesh.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from . import polymesh


@dataclass
class MeshView:
    title: str
    origin: tuple[float, float, float]  # a point on the cut plane
    normal: tuple[float, float, float]
    axes: tuple[int, int]  # coordinates shown horizontally / vertically (0=x, 1=y, 2=z)
    center: tuple[float, float]  # window centre in those coordinates
    width: float  # window width (height follows the panel aspect)
    labels: tuple[str, str] = ("x [m]", "y [m]")
    lw: float = 0.25
    # optional in-plane directions for the horizontal/vertical plot axes
    # (e.g. along the mast of a heeled boat); default: the coordinate axes
    basis: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
    basis_origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    basis_offset: tuple[float, float] = (0.0, 0.0)

    def project(self, pts: np.ndarray) -> np.ndarray:
        if self.basis is None:
            return pts[..., list(self.axes)]
        u, v = (np.asarray(b, float) for b in self.basis)
        q = pts - np.asarray(self.basis_origin, float)
        return np.stack([q @ u + self.basis_offset[0], q @ v + self.basis_offset[1]], axis=-1)


def boat_view(title: str, kind: str, level: float, center: tuple[float, float], width: float,
              heel: float = 0.0, pivot=(0.0, 0.0, 0.0), lw: float = 0.25) -> MeshView:
    """A cut in the (upright) boat frame of a heeled boat.

    kind 'side':    plane y_boat = level, plotted as x vs z_boat
    kind 'section': plane z_boat = level, plotted as x vs y_boat
    The boat is heeled by `heel` degrees about the x axis through `pivot`,
    as the projects do it, so cuts follow the mast/fin and axes read in
    boat coordinates.
    """
    import math

    h = math.radians(heel)
    ey = np.array([0.0, math.cos(h), math.sin(h)])  # boat y axis in the world
    ez = np.array([0.0, -math.sin(h), math.cos(h)])  # boat z axis in the world
    piv = np.asarray(pivot, float)
    if kind == "side":
        origin, normal, v, off, axes, labels = piv + level * ey, ey, ez, piv[2], (0, 2), ("x [m]", "z (boat) [m]")
    else:
        origin, normal, v, off, axes, labels = piv + (level - piv[2]) * ez, ez, ey, piv[1], (0, 1), ("x [m]", "y (boat) [m]")
    return MeshView(title, tuple(origin), tuple(normal), axes, center, width, labels, lw,
                    basis=((1.0, 0.0, 0.0), tuple(v)), basis_origin=tuple(piv), basis_offset=(piv[0], off))


@dataclass
class MeshSpec:
    views: list[MeshView]
    walls: str  # regex of wall patch names to draw bold
    notes: list[str] = field(default_factory=list)


def checkmesh_stats(case: Path) -> dict[str, Any]:
    log = case / "log.checkMesh"
    if not log.is_file():
        return {}
    t = log.read_text(errors="replace")
    pick = lambda pat: (re.findall(pat, t) or [None])[-1]
    out = {
        "cells": (re.findall(r"^\s+cells:\s+(\d+)", t, re.M) or [None])[0],
        "max non-orthogonality": pick(r"non-orthogonality Max: ([\d.]+)"),
        "max skewness": pick(r"Max skewness = ([\d.]+)"),
        "max aspect ratio": pick(r"Max aspect ratio = ([\d.]+)"),
        "failed checks": pick(r"Failed (\d+) mesh checks"),
    }
    return {k: v for k, v in out.items() if v is not None}


def layer_stats(case: Path) -> list[str]:
    """Prism-layer coverage table from snappyHexMesh (patch, faces, layers)."""
    log = case / "log.snappyHexMesh"
    if not log.is_file():
        return []
    lines = log.read_text(errors="replace").splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith("patch") and "layers" in ln:
            rows = []
            for row in lines[i + 3 :]:
                if not row.strip():
                    break
                parts = row.split()
                if len(parts) >= 3:
                    rows.append(f"{parts[0]}: {parts[2]} layers on {parts[1]} faces")
            return rows
    return []


def render(case: Path, spec: MeshSpec, out_png: Path, title: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    mesh = polymesh.read(case / "constant" / "polyMesh")
    walls = mesh.patch_faces(spec.walls)
    n = len(spec.views)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    pw, ph = 8.0, 5.0
    fig, axs = plt.subplots(rows, cols, figsize=(pw * cols, ph * rows + 1.6), squeeze=False)
    for ax, v in zip(axs.flat, spec.views):
        segs = polymesh.slice_segments(mesh, v.origin, v.normal)
        hw = 0.5 * v.width
        hh = hw * ph / pw
        x0, x1, y0, y1 = v.center[0] - hw, v.center[0] + hw, v.center[1] - hh, v.center[1] + hh
        if len(segs):
            s2 = v.project(segs)
            keep = ((s2[:, :, 0].max(1) >= x0) & (s2[:, :, 0].min(1) <= x1)
                    & (s2[:, :, 1].max(1) >= y0) & (s2[:, :, 1].min(1) <= y1))
            ax.add_collection(LineCollection(s2[keep], colors="#1f3b73", linewidths=v.lw))
        if len(walls):
            ws = polymesh.slice_segments(mesh, v.origin, v.normal, faces=walls)
            if len(ws):
                ax.add_collection(LineCollection(v.project(ws), colors="#c0392b", linewidths=1.6))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title(v.title, fontsize=10)
        ax.set_xlabel(v.labels[0])
        ax.set_ylabel(v.labels[1])
        ax.tick_params(labelsize=8)
    for ax in list(axs.flat)[n:]:
        ax.axis("off")

    stats = checkmesh_stats(case)
    info = []
    if stats:
        info.append("checkMesh: " + ", ".join(f"{k} {v}" for k, v in stats.items()))
    res = case / "result.json"
    if res.is_file():
        m = json.loads(res.read_text()).get("metrics") or {}
        yp = [f"y+ {k.split('_')[1]} {m[k]:.2f}" for k in ("yplus_max", "yplus_mean") if isinstance(m.get(k), (int, float))]
        if yp:
            info.append(", ".join(yp))
    lay = layer_stats(case)
    if lay:
        info.append("prism layers: " + "; ".join(lay[:6]))
    info += spec.notes
    fig.suptitle(title, fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.005, "\n".join(info) + "\nred: wall patches; blue: cell edges cut by the plane",
             fontsize=8, va="bottom", ha="left", family="monospace")
    fig.tight_layout(rect=(0, 0.02 + 0.018 * len(info), 1, 0.96), h_pad=3.0)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    return out_png


def study_mesh_figures(project, run_dir: Path, df, out_dir: Path, max_figures: int = 4) -> list[Path]:
    """One mesh figure per distinct mesh level in the study (or one in total)."""
    from .project import Project  # noqa: F401  (type only)

    candidates = df.copy()
    if "status" in candidates:
        candidates = candidates.sort_values("status", key=lambda s: s.ne("ok"))
    groups = candidates.groupby("mesh", sort=False) if "mesh" in candidates and candidates["mesh"].nunique() > 1 else [(None, candidates)]
    files = []
    for _, g in groups:
        for case_name in g["case"]:
            case = run_dir / case_name
            if not (case / "constant" / "polyMesh" / "points").exists() and not (case / "constant" / "polyMesh" / "points.gz").exists():
                continue
            pj = json.loads((case / "params.json").read_text())
            spec = project.mesh_views(case, pj["params"], pj["derived"])
            if spec is None:
                break
            title = f"{run_dir.parent.name} / {run_dir.name} / {case_name}: mesh '{pj['params'].get('mesh', '')}'"
            files.append(render(case, spec, out_dir / f"mesh_{case_name}.png", title))
            break
        if len(files) >= max_figures:
            break
    return files
