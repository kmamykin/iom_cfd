"""Section (foil profile) figures for study reports: what a study's sections
look like, drawn from the same geometry the mesh is built on (matplotlib;
no OpenFOAM needed).

study_sections() writes, for a list of `foil` specs:
  sections.png             every section at true scale; a stepped one over
                           the smooth section it was cut from, with a
                           close-up of its first step
  section_<spec>.png       one sheet per stepped section: the whole section,
                           a close-up of the first step with its height and
                           fillet radii, both surfaces in mm, a step table

foil2d's report calls it for studies with stepped sections. To check
sections before running anything:

  uv run python -m iomcfd.sectionplot OUT_DIR stair1:naca0009 stair10:naca0009 [--chord 0.08]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

from .geometry import foils
from .geometry.foils import Foil
from .geometry.stepped import is_stepped

C_BASE, C_STEP, C_MARK = "#9aa5b1", "#0b4f9c", "#d1495b"


def _contour(f: Foil, n: int = 30000) -> np.ndarray:
    """Dense contour points, including every stored node (keeps the corners)."""
    s = np.unique(np.concatenate([np.linspace(0.0, f.perimeter, n), f.s_nodes]))
    return f.point(s)


def _half_thickness(f: Foil, x):
    up, lo = f.surface("upper", 3000), f.surface("lower", 3000)
    return 0.5 * (np.interp(x, up[:, 0], up[:, 1]) - np.interp(x, lo[:, 0], lo[:, 1]))


def _upper_steps(f: Foil) -> list:
    return sorted((s for s in f.steps if s.side == "upper"), key=lambda s: s.x)


def describe(f: Foil, chord: float) -> str:
    """One line: what the steps are, in mm at `chord` (m)."""
    if not f.steps:
        return f"{f.name}, no steps"
    mm = 1000.0 * chord
    ups = _upper_steps(f)
    left = _half_thickness(f, 0.95) / _half_thickness(f.base, 0.95)
    if len(ups) == 1:
        st = ups[0]
        what = (f"one step per surface at x/c {st.x:.2f}, {st.height * mm:.2f} mm "
                f"({st.depth:.0%} of the local half-thickness; the hobby KFm4)")
    else:
        hs = [s.height * mm for s in ups]
        size = f"{hs[0]:.2f} mm" if np.ptp(hs) < 1e-9 else f"{min(hs):.2f}-{max(hs):.2f} mm"
        what = f"{len(ups)} steps per surface of {size}, x/c {ups[0].x:.2f} to {ups[-1].x:.2f}"
    return f"{what}; {left:.0%} of the thickness left at x/c 0.95"


def section_sheet(spec: str, f: Foil, path: Path, chord: float) -> Path:  # pragma: no cover - plotting
    """One sheet for a stepped section (see module docstring)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mm = 1000.0 * chord
    b = f.base
    pf, pb = _contour(f), _contour(b)
    fig = plt.figure(figsize=(15, 8.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 3.2], width_ratios=[1.25, 1], hspace=0.28, wspace=0.18)

    ax = fig.add_subplot(gs[0, :])  # whole section, true scale
    ax.fill(pb[:, 0], pb[:, 1], color=C_BASE, alpha=0.25, lw=0, label=f"plain {b.name}")
    ax.plot(pf[:, 0], pf[:, 1], color=C_STEP, lw=1.3, label=spec)
    for st in _upper_steps(f):
        ax.axvline(st.x, color=C_MARK, lw=0.5, alpha=0.5)
    ax.set_aspect("equal")
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.set_title("whole section, true scale (red lines: step positions)", fontsize=10, loc="left")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.grid(alpha=0.25)

    ax = fig.add_subplot(gs[1, 0])  # close-up of the first upper step, true scale
    ups = _upper_steps(f)
    st = ups[0]
    h = st.height
    lip = f.point(np.array(st.s_lip)).mean(axis=0)
    w = 3.2 * h if len(ups) == 1 else 5.0 * h
    ax.fill(pb[:, 0], pb[:, 1], color=C_BASE, alpha=0.25, lw=0)
    ax.plot(pf[:, 0], pf[:, 1], color=C_STEP, lw=1.6)
    near = (np.abs(f.x - st.x) < w) & (np.abs(f.y - lip[1]) < w)
    ax.plot(f.x[near], f.y[near], ".", color=C_STEP, ms=2.5, alpha=0.6)
    xa = st.x - max(0.6 * h, 0.25 * w)
    ax.annotate("", xy=(xa, lip[1] + 0.02 * h), xytext=(xa, lip[1] - h),
                arrowprops=dict(arrowstyle="<->", color=C_MARK, lw=1.2))
    ax.text(xa - 0.08 * h, lip[1] - 0.15 * h,
            f"h = {h * mm:.2f} mm\n({h * 100:.2f} % c,\n{st.depth:.0%} of the local\nhalf-thickness)",
            ha="right", va="top", color=C_MARK, fontsize=9)
    ax.text(st.x + 0.15 * h, lip[1] + 0.35 * h, f"lip fillet r = {st.r_lip * mm * 1000:.0f} um", fontsize=8, color="#333")
    ax.text(st.x + 0.35 * h, lip[1] - 1.25 * h, f"foot fillet r = {st.r_foot * mm * 1000:.0f} um", fontsize=8,
            color="#333", va="top")
    ax.set_xlim(st.x - w, st.x + w)
    ax.set_ylim(lip[1] - 0.75 * w, lip[1] + 0.75 * w)
    ax.set_aspect("equal")
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.grid(alpha=0.25)
    ax.set_title(f"close-up of the {'first ' if len(ups) > 1 else ''}upper-surface step at x/c = {st.x:.2f}, "
                 "true scale (dots: stored contour points)", fontsize=10, loc="left")

    ax = fig.add_subplot(gs[1, 1])  # both surfaces in mm, stretched vertically
    for g, color, lw, label in ((b, C_BASE, 2.0, f"plain {b.name}"), (f, C_STEP, 1.3, spec)):
        for i, side in enumerate(("upper", "lower")):
            pts = g.surface(side, 3000)
            ax.plot(pts[:, 0], pts[:, 1] * mm, color=color, lw=lw, label=label if i == 0 else None)
    ax.axhline(0, color="#888", lw=0.6)
    ax.set_xlabel("x/c")
    ax.set_ylabel(f"y [mm] at {mm:.0f} mm chord")
    ax.set_title("surfaces in mm, stretched vertically", fontsize=10, loc="left")
    ax.legend(fontsize=9, frameon=False, loc="lower left")
    ax.grid(alpha=0.25)

    t, xt = f.thickness()
    rows = [f"x/c {s.x:.3f}   depth {s.depth:.3f}   h = {s.height * 100:.3f} % c = {s.height * mm:.3f} mm" for s in ups]
    shown = rows if len(rows) <= 6 else rows[:3] + [f"... {len(rows) - 6} more ..."] + rows[-3:]
    fig.text(0.01, 0.985, f"{spec}: {describe(f, chord)}", fontsize=12.5, weight="bold", va="top")
    fig.text(0.01, 0.955, f"base {b.name}, chord {mm:.0f} mm, max thickness {t * 100:.2f} % c at x/c {xt:.2f}. "
             f"The same steps on both surfaces ({len(ups)} per surface):", fontsize=9.5, va="top")
    fig.text(0.01, 0.935, "\n".join(shown), fontsize=8.5, va="top", family="monospace")
    fig.subplots_adjust(top=0.84 - 0.017 * len(shown), left=0.05, right=0.98, bottom=0.07)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def sections_overview(sections: list[tuple[str, Foil]], path: Path, chord: float,
                      title: str = "sections") -> Path:  # pragma: no cover - plotting
    """Every section at true scale, one row each; stepped ones over their
    base, with a close-up of the first step."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mm = 1000.0 * chord
    fig, axs = plt.subplots(len(sections), 2, figsize=(15, 2.1 * len(sections) + 0.5), squeeze=False,
                            gridspec_kw=dict(width_ratios=[2.6, 1]))
    for (ax, az), (spec, f) in zip(axs, sections):
        pf = _contour(f)
        if f.base is not None:
            pb = _contour(f.base)
            ax.fill(pb[:, 0], pb[:, 1], color=C_BASE, alpha=0.25, lw=0)
        ax.plot(pf[:, 0], pf[:, 1], color=C_STEP, lw=1.1)
        ax.set_aspect("equal")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.6 * f.thickness()[0] - 0.01, 0.6 * f.thickness()[0] + 0.01)
        ax.set_yticks([])
        ax.set_title(f"{spec}:  {describe(f, chord)}" if f.steps else
                     f"{spec}:  plain, {f.thickness()[0] * 100:.1f} % thick", fontsize=9.5, loc="left")
        if not f.steps:
            az.axis("off")
            continue
        s0 = _upper_steps(f)[0]
        lip = f.point(np.array(s0.s_lip)).mean(axis=0)
        w = 4.0 * s0.height
        az.fill(pb[:, 0], pb[:, 1], color=C_BASE, alpha=0.25, lw=0)
        az.plot(pf[:, 0], pf[:, 1], color=C_STEP, lw=1.3)
        az.set_xlim(s0.x - 0.6 * w, s0.x + 1.4 * w)
        az.set_ylim(lip[1] - 0.55 * w, lip[1] + 0.25 * w)
        az.set_aspect("equal")
        az.set_title(f"first upper step (x/c {s0.x:.2f}), true scale", fontsize=8.5)
        az.tick_params(labelsize=7)
    fig.suptitle(f"{title}: stepped sections (blue) over the section they were cut from (grey), "
                 f"mm at {mm:.0f} mm chord", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.4 / fig.get_figheight()))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def _slug(spec: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", spec).strip("_")


def _natural(spec: str) -> list:
    """Sort key with the numbers as numbers: naca0009 < stair1:..:x=0.35 <
    stair1:..:x=0.5 < stair5 < stair10."""
    parts = re.split(r"(\d+(?:\.\d*)?)", spec.lower())
    return [float(t) if i % 2 else t for i, t in enumerate(parts)]


def study_sections(specs: list[str], out_dir: Path, chord: float, search_dirs: list[Path] | None = None,
                   title: str = "sections") -> list[Path]:  # pragma: no cover - plotting
    """sections.png for all `specs` (plain ones first, then by step count)
    and section_<spec>.png for each stepped one; stale section_*.png in
    out_dir are removed."""
    out_dir = Path(out_dir)
    specs = sorted(dict.fromkeys(str(s) for s in specs), key=lambda s: (is_stepped(s), _natural(s)))
    sections = [(s, foils.load(s, search_dirs)) for s in specs]  # raises before anything is removed
    for old in out_dir.glob("section_*.png"):
        old.unlink()
    files = [sections_overview(sections, out_dir / "sections.png", chord, title)]
    files += [section_sheet(s, f, out_dir / f"section_{_slug(s)}.png", chord) for s, f in sections if f.steps]
    return files


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - CLI
    import argparse

    from . import config

    ap = argparse.ArgumentParser(prog="python -m iomcfd.sectionplot", description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("specs", nargs="+", help="foil specs, e.g. naca0009 stair1:naca0009:x=0.35 stair10:naca0009")
    ap.add_argument("--chord", type=float, default=0.08, help="m, for the mm labels (default 0.08)")
    a = ap.parse_args(argv)
    for p in study_sections(a.specs, a.out_dir, a.chord, [config.geometry_dir() / "foils"]):
        print(p)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
