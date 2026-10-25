"""The eight thistle-screen sections in one PDF (findings/thistle-board.md):
every section at true scale on the 18 in chord, the half-thickness against
NACA 0006, noses and tails, a table with the XFOIL estimates, and one
sectiondesign.section_figure sheet each. Needs pdfunite (poppler).

    uv run python tools/thistle_sections_pdf.py \
        projects/foil2d/findings/figures/thistle-screen-sections.pdf <work dir>

The XFOIL columns come from runs/section-design/thistle-xfoil-20261023
(boardrank screen); without those files they are left blank.
"""
import subprocess, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from iomcfd import sectiondesign as sd

OUT = Path(sys.argv[1])
WORK = Path(sys.argv[2])
C = 457.2  # mm
SECS = [  # spec, label, note
    ("file:naca0006-t0556.dat", "NACA 0006", "baseline (user)"),
    ("file:sd8020-t0556.dat", "SD8020", "XFOIL's upwind leader at Tu 0.1 %; sharp nose"),
    ("file:ht35-t0556.dat", "HT35", "the IOM winner"),
    ("file:naca63-006-t0556.dat", "NACA 63-006", "laminar 6-series, best compromise in XFOIL"),
    ("file:naca64-006-t0556.dat", "NACA 64-006", "laminar 6-series; validation section"),
    ("file:naca0006-64-t0556.dat", "NACA 0006-64", "modified 4-digit, crest at 40 %"),
    ("file:parallel-l30-t50-r05-a20.dat", "Parallel l30-t50", "best parallel-sided board (XFOIL)"),
    ("file:plank-typical.dat", "Plank (typical)", "assumed home-built wood-lead board"),
]
COL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a65", "#d9d8d2"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titlecolor": INK})

foils = {s: sd.load(s) for s, _, _ in SECS}
props = {s: sd.properties(f) for s, f in foils.items()}

# XFOIL estimates (runs/section-design/thistle-xfoil-20261023), rake 10 deg
xf = {}
for sub in ("named", "parallel"):
    for v in ("Tu0.1", "Tu1"):
        p = Path(f"runs/section-design/thistle-xfoil-20261023/{sub}/summary-{v}rake10.csv")
        if p.exists():
            t = pd.read_csv(p, index_col=0)
            for idx, r in t.iterrows():
                key = {"parallel:t=0.05555555556,le=0.3,te=0.5,r=0.05,a=0.2": "file:parallel-l30-t50-r05-a20.dat",
                       "file:sd8020.dat@0.05555555556": "file:sd8020-t0556.dat",
                       "naca0006-64@0.05555555556": "file:naca0006-64-t0556.dat"}.get(idx, idx)
                xf.setdefault(key, {})[v] = (r["upwind %"], r["downwind %"])


def upper(f, n=1500):
    u = f.surface("upper", n)
    return u[:, 0] * C, u[:, 1] * C


with PdfPages(WORK / "overview.pdf") as pdf:
    # page 1: every section at true scale
    fig, axs = plt.subplots(len(SECS), 1, figsize=(11.69, 8.27))
    fig.subplots_adjust(left=0.24, right=0.97, top=0.88, bottom=0.07, hspace=0.55)
    fig.text(0.03, 0.95, "Thistle centreboard: the eight sections in thistle-screen", fontsize=15, weight="bold", color=INK)
    fig.text(0.03, 0.915, "True scale. Chord 18 in (457.2 mm) square to the leading edge, 1 in (25.4 mm) thick: "
             "t/c 5.56 %. Section as cut square to the leading edge.", fontsize=9.5, color=MUTED)
    for ax, (s, lab, note), col in zip(axs, SECS, COL):
        f = foils[s]
        x, y = upper(f)
        ax.fill(np.r_[x, x[::-1]], np.r_[y, -y[::-1]], color=col, lw=0)
        ax.set_aspect("equal")
        ax.set_xlim(-3, C + 3)
        ax.set_ylim(-14, 14)
        ax.axis("off")
        p = props[s]
        fig.text(0.03, ax.get_position().y0 + ax.get_position().height / 2 + 0.008, lab, fontsize=10.5, weight="bold",
                 color=INK, va="center")
        fig.text(0.03, ax.get_position().y0 + ax.get_position().height / 2 - 0.016,
                 f"max at {p['x_t'] * 100:.0f} %, nose r {p['r_le'] * C:.1f} mm, TE {p['te_angle']:.1f}°",
                 fontsize=8, color=MUTED, va="center")
    axs[-1].axis("on")
    for sp in ("top", "right", "left"):
        axs[-1].spines[sp].set_visible(False)
    axs[-1].set_yticks([])
    axs[-1].set_xticks(np.arange(0, 460, 50))
    axs[-1].set_xlabel("mm from the leading edge")
    pdf.savefig(fig)
    plt.close(fig)

    # page 2: half-thickness against NACA 0006, stretched, small multiples
    fig, axs = plt.subplots(4, 2, figsize=(11.69, 8.27), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.08, hspace=0.45, wspace=0.08)
    fig.text(0.03, 0.95, "Half-thickness along the chord, against the baseline", fontsize=15, weight="bold", color=INK)
    fig.text(0.03, 0.915, "Vertical scale stretched about 7x. Grey: NACA 0006 at 1 in. All sections reach 12.7 mm "
             "(half of 1 in); where they reach it, and how they get there, differs.", fontsize=9.5, color=MUTED)
    xb, yb = upper(foils[SECS[0][0]])
    for ax, (s, lab, _), col in zip(axs.flat, SECS, COL):
        ax.plot(xb, yb, color="#9aa5b1", lw=1.6, label="NACA 0006")
        x, y = upper(foils[s])
        if s != SECS[0][0]:
            ax.plot(x, y, color=col, lw=2.0, label=lab)
        ax.set_title(lab, loc="left", fontsize=10.5, weight="bold")
        ax.grid(color=GRID, lw=0.6)
        ax.set_xlim(0, C)
        ax.set_ylim(0, 14)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    for ax in axs[-1]:
        ax.set_xlabel("mm from the leading edge")
    for ax in axs[:, 0]:
        ax.set_ylabel("half-thickness [mm]")
    pdf.savefig(fig)
    plt.close(fig)

    # page 3: noses and tails close up (true scale)
    fig, axs = plt.subplots(2, 1, figsize=(11.69, 8.27))
    fig.subplots_adjust(left=0.07, right=0.8, top=0.86, bottom=0.08, hspace=0.35)
    fig.text(0.03, 0.95, "Noses and tails, true scale", fontsize=15, weight="bold", color=INK)
    fig.text(0.03, 0.915, "Upper surface only (the sections are symmetric). Nose: first 40 mm at true scale. "
             "Tail: last 150 mm, vertical scale stretched 4x.",
             fontsize=9.5, color=MUTED)
    for ax, (x0, x1, y1, ttl, asp) in zip(axs, ((0, 40, 13.5, "nose", 1.0), (C - 150, C, 13.5, "tail (4x vertical)", 4.0))):
        for (s, lab, _), col in zip(SECS, COL):
            x, y = upper(foils[s])
            m = (x >= x0 - 1) & (x <= x1 + 1)
            ax.plot(x[m], y[m], color=col, lw=1.8, label=lab)
        ax.set_aspect(asp)
        ax.set_xlim(x0, x1)
        ax.set_ylim(0, y1)
        ax.grid(color=GRID, lw=0.6)
        ax.set_title(ttl, loc="left", fontsize=11, weight="bold")
        ax.set_xlabel("mm from the leading edge")
        ax.set_ylabel("mm")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axs[0].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=9.5)
    pdf.savefig(fig)
    plt.close(fig)

    # page 4: table
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.03, 0.95, "Section properties and the XFOIL estimates", fontsize=15, weight="bold", color=INK)
    fig.text(0.03, 0.885, "Thickness in mm at stations along the 457 mm chord.\n"
             "XFOIL estimate of the board's drag against NACA 0006 (negative = less drag), rake 10°: upwind = mean over "
             "1-5 kn at the 1/2/4° loads; downwind = 0° over 1-15 kn.\n"
             "XFOIL under-predicts drag at Re 3e6 by 2-25 % and misses the CFD's leading-edge bubbles; the CFD decides.",
             fontsize=9, color=MUTED, linespacing=1.5)
    xs = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90])
    head = ["section", "max at", "nose r", "TE", *[f"t@{x * 100:.0f}%" for x in xs], "up Tu0.1", "up Tu1", "dn Tu0.1", "dn Tu1"]
    rows = []
    for s, lab, _ in SECS:
        f, p = foils[s], props[s]
        t = np.interp(xs, *f.surface("upper", 1500).T) * 2 * C
        e = xf.get(s, {})
        fmt = lambda v: "" if v is None or pd.isna(v) else f"{v:+.1f} %"
        rows.append([lab, f"{p['x_t'] * C:.0f} mm", f"{p['r_le'] * C:.1f} mm", f"{p['te_angle']:.1f}°",
                     *[f"{v:.1f}" for v in t],
                     fmt(e.get("Tu0.1", (None, None))[0]), fmt(e.get("Tu1", (None, None))[0]),
                     fmt(e.get("Tu0.1", (None, None))[1]), fmt(e.get("Tu1", (None, None))[1])])
    ax = fig.add_axes([0.03, 0.3, 0.94, 0.52])
    ax.axis("off")
    tab = ax.table(cellText=rows, colLabels=head, loc="upper left", cellLoc="right", colLoc="right")
    tab.auto_set_font_size(False)
    tab.set_fontsize(9)
    tab.scale(1, 1.7)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_text_props(weight="bold", color=INK)
        cell.set_width(0.155 if c == 0 else 0.0603)
        if c == 0:
            cell.set_text_props(ha="left", weight="bold")
            cell._loc = "left"
            if r:
                cell.get_text().set_color(COL[r - 1])
    notes = "\n".join(f"{lab}: {note}" for _, lab, note in SECS)
    fig.text(0.03, 0.08, notes, fontsize=8.5, color=MUTED, va="bottom", linespacing=1.5)
    pdf.savefig(fig)
    plt.close(fig)

# one sheet per section against the baseline (sectiondesign.section_figure)
pages = [WORK / "overview.pdf"]
for i, (s, lab, note) in enumerate(SECS):
    out = WORK / f"sheet{i}.pdf"
    comp = [] if i == 0 else [SECS[0][0]]
    sd.section_figure(s, comp, out, chord=C / 1000, title=f"{lab}: {note}")
    pages.append(out)
subprocess.run(["pdfunite", *map(str, pages), str(OUT)], check=True)
print(OUT)
