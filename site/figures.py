"""Charts, diagrams and generated tables for the website's study pages
(site/fin-selection/index.qmd, site/bulb-design/index.qmd,
site/custom-section/index.qmd, site/steps-and-films/index.qmd), and their
card images on the front page.

`iomcfd site build` calls make_all() before Quarto renders the page. Every
figure is drawn from the committed files in site/data/ and site/assets/ (or from
the project's own code: the mesh, the Wagner function), so the site builds
without runs/.
Output goes to site/_generated/ (not committed): one SVG per figure, and
markdown tables the page includes.

Whole-fin numbers follow projects/foil2d/methodology.md: span 0.36 m below
the hull, lifting-line induced drag with e = 0.9, loads = the side forces
of 0009/80 (steady) at 2, 4 and 6 degrees.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Arc, FancyArrowPatch, Polygon  # noqa: E402

from iomcfd.physics import induced_drag  # noqa: E402

SPAN, SPAN_EFF = 0.36, 0.9
REF = "0009/80"  # its steady forces at 2, 4 and 6 deg are the loads
LOAD_AOA = {"low": 2, "working": 4, "high": 6}  # side-force loads (not wind strengths)
LOAD_NAMES = {"light": "low", "working": "working", "high": "high"}  # findings' names -> this page's
TOP_FOUR = ["0007/100", "0007/90", "0008/100", "0008/90"]
# 2 laps of 90 m windward-leeward legs, about 420 m sailed (42 deg track upwind), 1 m boat:
# 1 % of race time is about 4 boat lengths (docs/research/surface-roughness.md; an estimate)
BOAT_LENGTHS_PER_PCT = 4.2

# Personal palette (site/styles.scss uses the same): ink on warm paper, a
# signal red for the recommended section, greens and earth tones for the rest.
PAPER, INK, MUTED, RULE = "#fbfaf6", "#1d232a", "#6b7480", "#ddd8cc"
ACCENT = "#b5452b"
COLOURS = {
    "0007/100": ACCENT, "0007/90": "#e09a4f", "0008/100": "#2f5d50", "0008/90": "#7fae94",
    "0009/100": "#5c4d7d", "0008/80": "#b3a27f", "0009/80": "#8a8f96",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "axes.titlesize": 10.5, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 9.5, "axes.labelcolor": INK, "axes.edgecolor": MUTED,
    "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": RULE, "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK, "ytick.labelcolor": INK, "text.color": INK, "legend.frameon": False,
    "legend.fontsize": 8.5, "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "lines.linewidth": 1.6, "svg.fonttype": "path",
})


def label(foil: str, chord: float) -> str:
    return f"{foil[-4:]}/{round(chord * 1000)}"


def _save(fig, out: Path, dpi: int = 200) -> Path:
    fig.savefig(out, bbox_inches="tight", pad_inches=0.08, dpi=dpi)
    plt.close(fig)
    return out


def _whole_fin(df: pd.DataFrame) -> pd.DataFrame:
    """Side force and fin drag [N] from section coefficients (methodology.md, step 1)."""
    df = df[df.status != "failed"].copy()
    df["section"] = [label(f, c) for f, c in zip(df.foil, df.chord)]
    q = 0.5 * df.rhoInf * df.speed**2
    df["F"] = df.Cl * q * df.chord * SPAN
    df["D"] = df.Cd * q * df.chord * SPAN + induced_drag(df.F, q, SPAN, e=SPAN_EFF)
    return df


def loads(steady: pd.DataFrame) -> dict[str, float]:
    ref = steady[steady.section == REF].set_index("aoa").F
    return {name: float(ref[a]) for name, a in LOAD_AOA.items()}


def wagner(flow_times):
    """Lift after an impulsive start as a fraction of its final value, R.T.
    Jones's approximation of the Wagner function; s = distance in semi-chords."""
    s = 2 * np.asarray(flow_times, float)
    return 1 - 0.165 * np.exp(-0.0455 * s) - 0.335 * np.exp(-0.3 * s)


# ---------------------------------------------------------------------------
# Diagrams


def course(out: Path) -> Path:
    fig, a = plt.subplots(figsize=(5.4, 4.3))
    a.set_aspect("equal")
    a.axis("off")
    fs = 11

    def bearing(deg, r=1.0):  # degrees clockwise from windward (+y)
        t = np.radians(deg)
        return np.array([np.sin(t), np.cos(t)]) * r

    a.plot([0, 0], [0, 1.08], ls=(0, (4, 3)), color=MUTED, lw=1)
    a.text(0.0, 1.11, "to the windward mark", ha="center", va="bottom", color=MUTED, fontsize=fs)
    a.add_patch(FancyArrowPatch((-0.42, 1.12), (-0.42, 0.82), arrowstyle="-|>", mutation_scale=16, color=INK, lw=1.5))
    a.text(-0.48, 0.97, "true\nwind", ha="right", va="center", fontsize=fs)
    a.plot(*zip((0, 0), bearing(39, 1.05)), color=MUTED, lw=1.2, ls=(0, (6, 2)))
    a.text(*bearing(32, 0.95), "heading 39°", rotation=51, ha="center", va="center", fontsize=fs, color=MUTED)
    a.add_patch(FancyArrowPatch((0, 0), bearing(42, 1.12), arrowstyle="-|>", mutation_scale=16, color=INK, lw=2))
    a.text(*bearing(49, 0.92), "course $\\beta_{TW}$ 42°", rotation=48, ha="center", va="center", fontsize=fs)
    a.add_patch(Arc((0, 0), 0.5, 0.5, theta1=90 - 39, theta2=90, color=MUTED, lw=1))
    a.text(*bearing(19, 0.34), "39°", ha="center", va="center", fontsize=fs, color=MUTED)
    w = np.array([(0, 0), bearing(39, 0.8), bearing(42, 0.8)])
    a.add_patch(Polygon(w, closed=True, color=ACCENT, alpha=0.25, lw=0))
    a.annotate("leeway $\\beta_Y$ 3°", xy=bearing(40.5, 0.72), xytext=(0.62, 0.3), fontsize=fs + 1, color=ACCENT,
               weight="bold", arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.9))
    c, h = bearing(42, 0.55), bearing(39)
    n = np.array([h[1], -h[0]])
    s_ = np.linspace(-1, 1, 30)
    hull = np.r_[[c + 0.11 * t * h + 0.028 * (1 - t**2) * n for t in s_],
                 [c + 0.11 * t * h - 0.028 * (1 - t**2) * n for t in s_[::-1]]]
    a.add_patch(Polygon(hull, closed=True, facecolor=INK, edgecolor=INK, alpha=0.85))
    a.set_xlim(-0.75, 1.0)
    a.set_ylim(-0.08, 1.22)
    fig.tight_layout()
    return _save(fig, out)


def fin_side(out: Path) -> Path:
    """The fin seen from the side (narrow figure: shown at a fixed width on the page)."""
    fig, a = plt.subplots(figsize=(3.6, 4.4))
    a.set_aspect("equal")
    a.axis("off")
    fs = 12
    a.fill_between([-1.0, 1.4], 0.0, 0.14, color="#e4ded0")
    a.plot([-1.0, 1.4], [0, 0], color=INK, lw=1)
    a.text(-0.95, 0.24, "hull", fontsize=fs, va="bottom", color=MUTED)
    a.add_patch(Polygon([(0, 0), (1, 0), (1, -3.6), (0, -3.6)], closed=True, facecolor="#d9d3c4", edgecolor=INK, lw=1))
    t = np.linspace(0, 2 * np.pi, 80)
    a.fill(0.5 + 1.0 * np.cos(t), -3.85 + 0.28 * np.sin(t), color=INK, alpha=0.85)
    a.text(0.5, -4.25, "bulb", fontsize=fs, ha="center", va="top", color=MUTED)
    a.annotate("", xy=(1.3, 0), xytext=(1.3, -3.6), arrowprops=dict(arrowstyle="<->", color=INK, lw=1))
    a.text(1.42, -1.8, "span\n0.36 m", fontsize=fs, va="center")
    a.plot([-0.15, 1.15], [-2.2, -2.2], color=ACCENT, lw=1.6, ls=(0, (4, 2)))
    a.text(-0.2, -2.2, "slice\nsimulated", fontsize=fs, color=ACCENT, ha="right", va="center")
    a.annotate("", xy=(0, -1.0), xytext=(1, -1.0), arrowprops=dict(arrowstyle="<->", color=INK, lw=1))
    a.text(0.5, -0.9, "chord", fontsize=fs, ha="center", va="bottom")
    a.add_patch(FancyArrowPatch((-0.95, -3.2), (-0.25, -3.2), arrowstyle="-|>", mutation_scale=14, color=MUTED, lw=1.3))
    a.text(-0.95, -3.0, "water", fontsize=fs, color=MUTED, va="bottom")
    a.set_xlim(-1.3, 2.4)
    a.set_ylim(-4.6, 0.6)
    fig.tight_layout()
    return _save(fig, out)


def section(out: Path) -> Path:
    """The horizontal slice: NACA 0007, 100 mm chord, at an angle of attack (schematic)."""
    from iomcfd.geometry.foils import naca4

    fig, b = plt.subplots(figsize=(6.6, 3.2))
    b.set_aspect("equal")
    b.axis("off")
    fs = 13.5
    f = naca4("0007")
    al = np.radians(6)

    def rot(px, py):
        return (px - 0.25) * np.cos(al) + py * np.sin(al) + 0.25, -(px - 0.25) * np.sin(al) + py * np.cos(al)

    xr, yr = rot(f.x, f.y)
    b.fill(xr, yr, facecolor="#d9d3c4", edgecolor=INK, lw=1.2)
    le, te = rot(0, 0), rot(1, 0)
    b.plot([le[0], te[0]], [le[1], te[1]], color=MUTED, lw=0.9, ls=(0, (3, 2)))
    b.text(le[0] - 0.03, le[1] + 0.03, "leading\nedge", ha="right", va="bottom", fontsize=fs)
    b.text(te[0] + 0.02, te[1] - 0.03, "trailing\nedge", ha="left", va="top", fontsize=fs)
    b.annotate("", xy=rot(0, -0.12), xytext=rot(1, -0.12), arrowprops=dict(arrowstyle="<->", color=INK, lw=1))
    mx, my = rot(0.5, -0.15)
    b.text(mx, my, "chord 100 mm", ha="center", va="top", fontsize=fs, rotation=-6)
    p0, p1 = rot(0.3, -0.035), rot(0.3, 0.035)
    b.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1.1, shrinkA=0, shrinkB=0))
    b.annotate("max thickness 7 mm\n(7 % of the chord)", xy=p1, xytext=(0.55, 0.27), fontsize=fs, color=ACCENT,
               arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.8))
    for yy in (0.12, -0.02):
        b.add_patch(FancyArrowPatch((-0.62, yy), (-0.24, yy), arrowstyle="-|>", mutation_scale=14, color=MUTED, lw=1.3))
    b.text(-0.62, 0.17, "water", fontsize=fs, color=MUTED)
    b.plot([0.25, 1.18], [0, 0], color=MUTED, lw=0.9)
    b.add_patch(Arc((0.25, 0), 1.6, 1.6, theta1=-6, theta2=0, color=MUTED, lw=1.1))
    b.text(1.07, -0.045, "α", fontsize=fs + 2, color=MUTED, va="center")
    b.add_patch(FancyArrowPatch((0.25, 0), (0.25, 0.42), arrowstyle="-|>", mutation_scale=15, color=ACCENT, lw=2.2))
    b.text(0.21, 0.42, "side force", fontsize=fs, color=ACCENT, va="top", ha="right")
    b.add_patch(FancyArrowPatch((0.25, 0), (0.56, 0), arrowstyle="-|>", mutation_scale=15, color=INK, lw=2.2, zorder=3))
    b.text(0.58, 0.075, "drag", fontsize=fs, ha="left", va="bottom")
    b.set_xlim(-0.7, 1.3)
    b.set_ylim(-0.32, 0.48)
    fig.tight_layout()
    return _save(fig, out)


def bubble_schematic(out: Path) -> Path:
    """Laminar boundary layer, separation, transition in the separated layer, reattachment, turbulent layer."""
    fig, ax = plt.subplots(figsize=(6.8, 3.3))
    ax.axis("off")
    fs = 13
    x = np.linspace(0, 10, 400)
    ax.fill_between(x, -0.5, 0, color="#d9d3c4")
    ax.plot(x, 0 * x, color=INK, lw=1.2)
    S, T, R = 3.0, 5.0, 6.8
    u = np.clip((x - S) / (R - S), 0, 1)
    edge = np.where(x < S, 0.35 * np.sqrt(np.clip(x, 0, None) / S),
                    np.where(x <= R, 0.35 + 0.45 * np.sin(0.5 * np.pi * u), 0.8 + 0.05 * (x - R)))
    ax.plot(x, edge, color=MUTED, lw=1, ls=(0, (4, 2)))
    inner = np.where((x >= S) & (x <= R), 0.32 * np.sin(np.pi * u), np.nan)
    ax.fill_between(x, 0, inner, where=~np.isnan(inner), color="#9cb8e0", alpha=0.9)
    ax.plot(x, inner, color="#2a4f86", lw=1.2)  # the separated shear layer
    for xa in (4.4, 5.8):  # reversed flow near the wall
        ax.add_patch(FancyArrowPatch((xa + 0.45, 0.08), (xa - 0.35, 0.08), arrowstyle="-|>", mutation_scale=10,
                                     color="#1b3f73", lw=1.3))
    for xp, kind in ((1.3, "lam"), (S, "sep"), (8.7, "turb")):
        ys = np.linspace(0, edge[np.searchsorted(x, xp)], 6)[1:]
        for yy in ys:
            frac = yy / ys[-1]
            uu = (0.6 * (1.5 * frac - 0.5 * frac**3) if kind == "lam" else 0.6 * frac**2 if kind == "sep"
                  else 0.6 * frac ** (1 / 7))
            ax.add_patch(FancyArrowPatch((xp, yy), (xp + uu, yy), arrowstyle="-|>", mutation_scale=6, color=INK, lw=0.7))
        ax.plot([xp, xp], [0, ys[-1]], color=INK, lw=0.7)
    for xp in (S, R):
        ax.plot([xp], [0], "o", color=ACCENT, ms=6, zorder=4)
    ax.text(S, -0.1, "S", ha="center", va="top", fontsize=fs + 1, color=ACCENT, weight="bold")
    ax.text(R, -0.1, "R", ha="center", va="top", fontsize=fs + 1, color=ACCENT, weight="bold")
    yT = 0.32 * np.sin(np.pi * (T - S) / (R - S))
    ax.plot([T], [yT], "o", color=ACCENT, ms=6, zorder=4)
    ax.annotate("T", xy=(T, yT), xytext=(T - 0.9, yT + 0.55), fontsize=fs + 1, color=ACCENT, weight="bold",
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.9))
    ax.text(1.6, 0.62, "laminar", ha="center", fontsize=fs, color=INK)
    ax.text(8.8, 1.08, "turbulent", ha="center", fontsize=fs, color=INK)
    ax.text(0.5 * (S + R) + 0.2, 0.17, "reversed", ha="center", fontsize=fs - 1.5, color="#1b3f73")
    ax.add_patch(FancyArrowPatch((0.1, 1.05), (1.1, 1.05), arrowstyle="-|>", mutation_scale=13, color=MUTED, lw=1.2))
    ax.text(0.1, 1.12, "water", fontsize=fs, color=MUTED)
    ax.set_xlim(-0.1, 10.1)
    ax.set_ylim(-0.5, 1.3)
    fig.tight_layout()
    return _save(fig, out)


def mesh(out: Path) -> Path:
    """The medium C-grid of 0007/100 at 1 m/s, from the same generator the runs use."""
    from iomcfd.geometry import cmesh, foils
    from iomcfd.project import load_project

    project = load_project("foil2d")
    p = {**project.defaults, "foil": "naca0007", "chord": 0.1, "speed": 1.0, "mesh": "medium"}
    spec = cmesh.CMeshSpec(**project.derive(p)["mesh_spec"])
    P, _ = cmesh.generate(foils.naca4("0007"), spec)
    P = P / spec.chord
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), gridspec_kw={"width_ratios": [1.1, 1.5, 0.9]})
    views = [("Whole domain, 50 chords", (-55, 55), (-55, 55), 4),
             ("The section", (-0.15, 1.25), (-0.38, 0.38), 1),
             ("Leading edge", (-0.012, 0.05), (-0.03, 0.03), 1)]
    for ax, (title, xl, yl, k) in zip(axes, views):
        for j in range(0, P.shape[1], k):
            ax.plot(P[:, j, 0], P[:, j, 1], color="#3c4a57", lw=0.25)
        for i in range(0, P.shape[0], k):
            ax.plot(P[i, :, 0], P[i, :, 1], color="#3c4a57", lw=0.25)
        ax.plot(P[:, 0, 0], P[:, 0, 1], color=ACCENT, lw=1.2)
        ax.set(xlim=xl, ylim=yl, title=title, xlabel="x / c")
        ax.set_aspect("equal")
        ax.grid(False)
    axes[0].set_ylabel("y / c")
    fig.tight_layout()
    return _save(fig, out, dpi=130)


# ---------------------------------------------------------------------------
# Charts from site/data


def validation(data: Path, ref_csv: Path, out: Path) -> Path:
    v = pd.read_csv(data / "validation-naca0009.csv")
    ref = pd.read_csv(ref_csv, comment="#")
    ref = ref[(ref.Re.round(-4) == 100000) & ref.aoa.between(-0.5, 9)]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3.4))
    a.plot(ref.aoa, ref.Cl, "s", color=INK, ms=4.5, label="Princeton wind tunnel (Selig et al. 1989)")
    b.plot(ref.aoa, ref.Cd, "s", color=INK, ms=4.5)
    for model, colour, name in (("kOmegaSSTLM", ACCENT, "k-ω SST + transition (used)"),
                                ("kOmegaSST", "#2f5d50", "k-ω SST, fully turbulent")):
        m = v[v.turbulence == model].sort_values("aoa")
        a.plot(m.aoa, m.Cl, "-o", color=colour, ms=4, label=name)
        b.plot(m.aoa, m.Cd, "-o", color=colour, ms=4)
        bad = m[m.unsteady.astype(bool) | (m.status != "ok")]
        a.plot(bad.aoa, bad.Cl, "o", ms=8, mfc="none", mec=colour, mew=1)
        b.plot(bad.aoa, bad.Cd, "o", ms=8, mfc="none", mec=colour, mew=1)
    a.set(title="Lift", xlabel="angle of attack [°]", ylabel="C$_l$")
    b.set(title="Drag", xlabel="angle of attack [°]", ylabel="C$_d$")
    a.legend(loc="upper left")
    b.text(0.02, 0.97, "circled: unsteady or not converged\n(steady solver)", transform=b.transAxes, va="top",
           fontsize=8, color=MUTED)
    fig.tight_layout()
    return _save(fig, out)


def _running_mean(t, y, width=1.0, dt=0.01):
    tu = np.arange(t[0], t[-1], dt)
    yu = np.interp(tu, t, y)
    n = int(round(width / dt))
    return tu[n - 1:], np.convolve(yu, np.ones(n) / n, mode="valid")


def force_history(data: Path, out: Path) -> Path:
    h = pd.read_csv(data / "force-history-4deg.csv")
    st = _whole_fin(pd.read_csv(data / "steady-1ms.csv"))
    tr = pd.read_csv(data / "transient-4deg-1ms.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), sharey=True)
    panels = [("chord0.1_foilnaca0007_max_co10", "0007/100: started from rest", True),
              ("chord0.1_foilnaca0009_max_co10", "0009/100: started from the steady solution", False)]
    for ax, (case, title, from_rest) in zip(axes, panels):
        g = h[h.case == case]
        g = g[g.flow_times > 0.05]
        t, cl = g.flow_times.to_numpy(), g.Cl.to_numpy()
        section = title.split(":")[0]
        foil, chord = "naca" + section[:4], int(section[5:]) / 1000
        final = float(tr[(tr.foil == foil) & np.isclose(tr.chord, chord) & (tr.max_co == 10)].Cl.iloc[0])
        steady = float(st[(st.section == section) & (st.aoa == 4)].Cl.iloc[0])
        ax.axvspan(24, 30, color=RULE, alpha=0.6, lw=0)
        ax.text(27, 0.512, "averaged", ha="center", fontsize=8, color=MUTED, va="top")
        ax.plot(t, cl, color=COLOURS[section], lw=0.4, alpha=0.45)
        ax.plot(*_running_mean(t, cl), color=COLOURS[section], lw=2, label="1-flow-through mean")
        ax.axhline(steady, color=INK, ls=(0, (5, 3)), lw=1.1, label=f"steady solver: {steady:.3f}")
        ax.axhline(final, color=COLOURS[section], ls=":", lw=1.2, label=f"time-accurate mean: {final:.3f}")
        if from_rest:
            tt = np.linspace(0.2, 30, 300)
            ax.plot(tt, final * wagner(tt), color=MUTED, lw=1.1, ls="-.", label="Wagner build-up (thin-airfoil)")
            ax.axvline(15, color=MUTED, lw=0.8)
            ax.text(15.3, 0.512, "continued\nfrom here", fontsize=8, color=MUTED, va="top")
        ax.set(title=title, xlabel="chord flow-throughs (c / $V_b$)", xlim=(0, 30), ylim=(0.2, 0.52))
        ax.legend(loc="lower right", fontsize=7.8, ncols=2 if from_rest else 1)
    axes[0].set_ylabel("C$_l$ at 4°")
    fig.tight_layout()
    return _save(fig, out)


def steady_vs_transient(data: Path, out: Path) -> Path:
    st = _whole_fin(pd.read_csv(data / "steady-1ms.csv"))
    tr = pd.read_csv(data / "transient-4deg-1ms.csv")
    tr = tr[tr.max_co == 10].assign(section=lambda d: [label(f, c) for f, c in zip(d.foil, d.chord)])
    m = tr.merge(st[st.aoa == 4][["section", "Cl", "Cd"]], on="section", suffixes=("", "_steady"))
    m = m.sort_values("Cd", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.3), sharey=True)
    y = np.arange(len(m))
    for ax, col, title in ((axes[0], "Cl", "Lift coefficient at 4°"), (axes[1], "Cd", "Drag coefficient at 4°")):
        for yi, (_, r) in zip(y, m.iterrows()):
            ax.plot([r[f"{col}_steady"], r[col]], [yi, yi], color=RULE, lw=3, solid_capstyle="round", zorder=1)
        ax.scatter(m[f"{col}_steady"], y, s=34, facecolor=PAPER, edgecolor=INK, lw=1.1, zorder=2)
        ax.scatter(m[col], y, s=40, color=[COLOURS[s] for s in m.section], zorder=3)
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y, m.section)
    handles = [plt.Line2D([], [], ls="", marker="o", mfc=PAPER, mec=INK, label="steady solver"),
               plt.Line2D([], [], ls="", marker="o", color=INK, label="time-accurate, mean of 24-30")]
    axes[1].legend(handles=handles, loc="lower right")
    axes[1].xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.3f"))
    fig.tight_layout()
    return _save(fig, out)


def time_accurate_1ms(data: Path) -> pd.DataFrame:
    """Time-accurate points at 1 m/s: 4 deg of all seven (transient-check run 2), 2 and 6 deg of the top four
    (run 3)."""
    a = pd.read_csv(data / "transient-4deg-1ms.csv").query("max_co == 10")
    b = pd.read_csv(data / "transient-run3.csv").query("speed == 1.0")
    return _whole_fin(pd.concat([a, b], ignore_index=True))


def equal_force(data: Path, out: Path) -> Path:
    st = _whole_fin(pd.read_csv(data / "steady-1ms.csv"))
    tr = time_accurate_1ms(data)
    L = loads(st)
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for section in TOP_FOUR:
        s = st[st.section == section].sort_values("aoa")
        t = tr[tr.section == section]
        used = pd.concat([s[~s.aoa.isin(t.aoa)], t]).sort_values("aoa")
        c = COLOURS[section]
        a.plot(s.aoa, s.F, color=c, lw=1, alpha=0.4, ls=(0, (3, 2)))
        b.plot(s.F, s.D, color=c, lw=1, alpha=0.4, ls=(0, (3, 2)))
        a.plot(used.aoa, used.F, "-o", color=c, ms=3.5, label=section)
        b.plot(used.F, used.D, "-o", color=c, ms=3.5)
        a.plot(t.aoa, t.F, "D", color=c, ms=7, mec=INK, mew=0.8)
        b.plot(t.F, t.D, "D", color=c, ms=7, mec=INK, mew=0.8)
    for name, F in L.items():
        a.axhline(F, color=MUTED, lw=0.8, ls=":")
        b.axvline(F, color=MUTED, lw=0.8, ls=":")
        a.text(8.3, F + 0.12, f"{name} load {F:.2f} N", fontsize=7.5, color=MUTED, ha="right")
        b.text(F - 0.1, 0.97, f"{name}", fontsize=7.5, color=MUTED, rotation=90, ha="right", va="top",
               transform=b.get_xaxis_transform())
    a.set(title="1. The angle each fin needs", xlabel="angle of attack α [°]", ylabel="side force $S_h$ [N]",
          xlim=(-0.2, 8.4), ylim=(-0.2, 10.5))
    b.set(title="2. Its drag at that side force", xlabel="side force $S_h$ [N]", ylabel="fin drag $D_h$ [N]",
          xlim=(-0.2, 9.2), ylim=(0.15, 0.62))
    a.legend(loc="upper left", title="1 m/s, Tu 0.1 %", title_fontsize=8)
    b.text(0.02, 0.8, "◆ time-accurate points\n- - steady curve they replace", transform=b.transAxes, fontsize=8,
           color=MUTED)
    fig.tight_layout()
    return _save(fig, out)


def race_time(data: Path, out: Path) -> Path:
    r = pd.read_csv(data / "race-time-1ms.csv").pivot(index="section", columns="load")
    r = r.sort_values(("loss_x1", "mean"), ascending=False)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(r))
    ax.barh(y, r.loss_x1["mean"], color=[COLOURS[s] for s in r.index], height=0.55, label="mean of the three side-force loads")
    ax.scatter(r.loss_x2["mean"], y, marker="|", s=260, color=INK, lw=2, label="mean, resistance slope doubled", zorder=3)
    for yi, v in zip(y, r.loss_x1["mean"]):
        ax.text(max(v, r.loss_x2["mean"].iloc[yi]) + 0.06, yi, f"{v:.2f}", va="center", fontsize=8.5)
    ax.set_yticks(y, r.index)
    ax.set(xlabel="mean loss against the best fin at each load [% of race time]",
           title="Race-time loss at 1 m/s (time-accurate points)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 3.3)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


def _by_speed(data: Path):
    """Per-speed rows, and the means over the speeds (from the unrounded analysis, as in the findings)."""
    r = pd.read_csv(data / "race-time-by-speed.csv", dtype={"speed": str})
    mean = r[r.speed == "mean"].set_index("section")
    r = r[r.speed != "mean"].assign(speed=lambda d: d.speed.astype(float))
    return r, sorted(r.speed.unique()), mean


def race_time_by_speed(data: Path, out: Path) -> Path:
    r, speeds, _ = _by_speed(data)
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    w = 0.2
    for i, section in enumerate(TOP_FOUR):
        g = r[r.section == section].set_index("speed").loc[speeds]
        x = np.arange(len(speeds)) + (i - 1.5) * w
        ax.bar(x, g.loss_x1, width=w * 0.92, color=COLOURS[section], label=section)
        ax.scatter(x, g.loss_x2, marker="_", s=120, color=INK, lw=2, zorder=3)
    ax.scatter([], [], marker="_", s=120, color=INK, lw=2, label="resistance slope doubled")
    wind = {0.75: "light air", 1.0: "medium", 1.5: "fresh"}
    ax.set_xticks(np.arange(len(speeds)), [f"{v:g} m/s ({wind.get(v, '')})" for v in speeds])
    ax.set(ylabel="mean loss against the best\nfin at each load [% of race time]",
           title="Race-time loss by boat speed (time-accurate 4° points)")
    sec = ax.secondary_yaxis("right", functions=(lambda v: v * BOAT_LENGTHS_PER_PCT, lambda v: v / BOAT_LENGTHS_PER_PCT))
    sec.set_ylabel("boat lengths per race (estimate)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", ncols=5, fontsize=7.8)
    ax.set_ylim(0, 2.1)
    fig.tight_layout()
    return _save(fig, out)


def leading_edge_bubble(data: Path, out: Path) -> Path:
    """The two flows the model finds on 0007/100 at 4 deg and 1.5 m/s: from rest it sheds (one instant),
    from its steady solution it settles into a leading-edge bubble with attached turbulent flow behind."""
    steady_start = pd.read_csv(data / "surface-0007-100-4deg.csv")
    steady_start = steady_start[steady_start.file.str.contains("speed1.5")]
    rest = pd.read_csv(data / "surface-0007-100-4deg-rest.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.4, 3.3))
    for s, colour, label, lw in ((rest, "#2f5d50", "started from rest: sheds (one instant)", 1.1),
                                 (steady_start, ACCENT, "from its steady solution: leading-edge\nbubble, then attached", 1.6)):
        g = s[s.upper.astype(str) == "True"].sort_values("x_c")
        a.plot(g.x_c, -g.Cp, color=colour, label=label, lw=lw)
        b.plot(g.x_c, g.Cf, color=colour, lw=lw)
    b.axhline(0, color=INK, lw=0.8)
    b.text(0.99, -0.0115, "Cf < 0: reversed flow", ha="right", fontsize=8, color=MUTED)
    a.set(title="Suction side: −Cp", xlabel="x / c", ylabel="−C$_p$", xlim=(0, 1))
    b.set(title="Suction side: skin friction", xlabel="x / c", ylabel="C$_f$", xlim=(0, 1), ylim=(-0.014, 0.014))
    a.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


# ---------------------------------------------------------------------------
# Tables (markdown, included by the page)


def race_time_table(data: Path, out: Path) -> Path:
    r = pd.read_csv(data / "race-time-1ms.csv")
    order = r[r.load == "mean"].sort_values("loss_x1").section

    def cell(s, load):
        x = r[(r.section == s) & (r.load == load)].iloc[0]
        return "best" if x.loss_x1 == 0 and x.loss_x2 == 0 else f"{x.loss_x1:.2f} / {x.loss_x2:.2f}"

    rows = ["| section | low load (1.15 N) | working load (6.69 N) | high load (8.33 N) | mean |", "|---|---|---|---|---|"]
    rows += [f"| {s} | " + " | ".join(cell(s, ld) for ld in ("light", "working", "high", "mean")) + " |" for s in order]
    out.write_text("\n".join(rows) + "\n")
    return out


def race_time_by_speed_table(data: Path, out: Path) -> Path:
    r, speeds, mean = _by_speed(data)
    head = "| section | " + " | ".join(f"{v:g} m/s" for v in speeds) + " | mean | worst |"
    rows = [head, "|---" * (len(speeds) + 3) + "|"]
    for section in TOP_FOUR:
        g = r[r.section == section].set_index("speed").loc[speeds]
        cells = [f"{a:.2f} / {b:.2f}" for a, b in zip(g.loss_x1, g.loss_x2)]
        cells += [f"{mean.loss_x1[section]:.2f} / {mean.loss_x2[section]:.2f}",
                  f"{g.loss_x1.max():.2f} / {g.loss_x2.max():.2f}"]
        rows.append(f"| {section} | " + " | ".join(cells) + " |")
    out.write_text("\n".join(rows) + "\n")
    return out


def fin_choice_table(data: Path, out: Path) -> Path:
    """What one fin for every wind costs: each fin's loss at each speed minus the best fin's there (the
    fin you'd fit if you could change keels), in % of race time and boat lengths."""
    r, speeds, _ = _by_speed(data)
    names = {0.75: "light air (0.75 m/s)", 1.0: "medium (1 m/s)", 1.5: "fresh (1.5 m/s)"}
    rows = ["| fin | " + " | ".join(names.get(v, f"{v:g} m/s") for v in speeds) + " | average | average, boat lengths |",
            "|---" * (len(speeds) + 3) + "|"]
    best = {(v, k): r[r.speed == v][k].min() for v in speeds for k in ("loss_x1", "loss_x2")}
    for section in TOP_FOUR:
        g = r[r.section == section].set_index("speed")
        d1 = [g.loss_x1[v] - best[(v, "loss_x1")] for v in speeds]
        d2 = [g.loss_x2[v] - best[(v, "loss_x2")] for v in speeds]
        cells = ["best" if a < 0.005 and b < 0.005 else f"{a:.2f} / {b:.2f}" for a, b in zip(d1, d2)]
        m1, m2 = np.mean(d1), np.mean(d2)
        cells += [f"{m1:.2f} / {m2:.2f}", f"{m1 * BOAT_LENGTHS_PER_PCT:.1f} / {m2 * BOAT_LENGTHS_PER_PCT:.1f}"]
        rows.append(f"| {section} | " + " | ".join(cells) + " |")
    out.write_text("\n".join(rows) + "\n")
    return out


def card_image(render: Path, out: Path) -> Path:
    """The study's card on the front page: the vortex-shedding render (0007/100, 4 deg, 0.75 m/s)
    cropped to the section and its near wake, without the labels and colour bar, at 3:1."""
    from PIL import Image

    Image.open(render).convert("RGB").crop((60, 140, 1500, 620)).resize((1080, 360), Image.LANCZOS).save(
        out, optimize=True)
    return out


def sources_table(data: Path, out: Path, keep=lambda name: True) -> Path:
    src = json.loads((data / "sources.json").read_text())
    rows = ["| file | from | exported |", "|---|---|---|"]
    for name, s in src.items():
        if not keep(name):
            continue
        if s["kind"] == "manual":
            rows.append(f"| `{s['file']}` | {s['source']} | by hand |")
        else:
            what = s["source"] if isinstance(s["source"], str) else ", ".join(s["source"])
            runs = ", ".join(s["runs"])
            rows.append(f"| `{s['file']}` | {s['study']} run {runs}: `{what}` | {s['exported']} |")
    out.write_text("\n".join(rows) + "\n")
    return out


# ---------------------------------------------------------------------------
# The keel bulb page (site/bulb-design/index.qmd). Data: bulb-*.csv. Geometry
# and the equal-side-force race time come from the keel3d project's own code.

BULB_SECTIONS = [  # name, width/height, top and bottom superellipse exponents (keel3d bulb_aspect, bulb_top, bulb_bottom)
    ("round", 1.0, 2.0, 2.0), ("elliptic 1.25", 1.25, 2.0, 2.0), ("elliptic 1.5", 1.5, 2.0, 2.0),
    ("flat bottom 1.5", 1.5, 2.0, 6.0), ("flat top 1.5", 1.5, 6.0, 2.0), ("elliptic 2", 2.0, 2.0, 2.0),
]
BULB_COLOURS = {"round": ACCENT, "elliptic 1.25": "#e09a4f", "elliptic 1.5": "#b3a27f", "flat bottom 1.5": "#2f5d50",
                "flat top 1.5": "#7fae94", "elliptic 2": "#5c4d7d"}
FIN_COLOUR, BULB_GREY = "#c9d6e2", "#9aa3ab"
# Sensitivity scenarios of keel3d findings bulb-section, conclusions 4 and 5 (estimates, not validated corrections)
FIN_FRICTION = 0.80  # fin friction with transition / fully turbulent (foil2d: about 25 % high)
RM_DRAFT_TO_CB = 0.40  # m, draft limit (0.42) to the hull's centre of buoyancy (about 0.02 m down): the bulb's
# righting lever is this less its centre of mass above the draft, about 0.38 m
RM_SPEED = 0.5  # % of upwind speed per 1 % of righting moment: the upper end of the bracket (0 is the lower)
SCENARIOS = [  # key, label, marker
    ("computed", "as computed (fully turbulent)", "o"),
    ("corrected", "friction scaled towards transition (sensitivity)", "s"),
    ("rm", "… plus the upper-end righting-moment credit", "D"),
]


def _keel3d():
    from iomcfd.project import load_project

    k = load_project("keel3d")
    return k, {**k.defaults, "bulb_section": "naca0011", "fin_taper": 0.8, "fin_mean_chord": 0.090}


def _section_name(df: pd.DataFrame) -> pd.Series:
    names = {(a, t, b): n for n, a, t, b in BULB_SECTIONS}
    return pd.Series([names.get((float(a), float(t), float(b))) for a, t, b in
                      zip(df.bulb_aspect, df.bulb_top, df.bulb_bottom)], index=df.index)


def _bulb_outline(k, p, **kw):
    """The bulb's centre-plane outline [mm from its nose, mm above the draft] and the derived sizes."""
    from iomcfd.geometry import appendages as ap

    q = {**p, **kw}
    g = k.derive(q)
    spec = ap.FoilBulbSpec(section=q["bulb_section"], length=g["bulb_length"], x_cg=g["bulb_x_cg"], z_axis=g["bulb_z_axis"],
                           aspect=float(q["bulb_aspect"]), top=float(q["bulb_top"]), bottom=float(q["bulb_bottom"]),
                           cant=float(q["bulb_cant"]))
    xt, zt, xb, zb = ap.foil_bulb_lines(spec, 400)
    x0, draft = float(ap.foil_bulb_lines(ap.FoilBulbSpec(section=q["bulb_section"], length=g["bulb_length"],
                                                         x_cg=g["bulb_x_cg"], z_axis=g["bulb_z_axis"]), 400)[0].min()), float(q["draft"])
    X = (np.r_[xt, xb[::-1]] - x0) * 1e3
    Z = (np.r_[zt, zb[::-1]] + draft) * 1e3
    return X, Z, g, x0


def bulb_side(out: Path) -> Path:
    """The 3D studies' bulb from the side, with the foot of the fin, the draft limit and the 60 mm rule."""
    k, p = _keel3d()
    X, Z, g, x0 = _bulb_outline(k, p)
    mm = 1e3
    fig, a = plt.subplots(figsize=(8.6, 3.4))
    le = (g["bulb_x_cg"] - 0.25 * g["fin_tip_chord"] - x0) * mm
    a.fill([le, le + g["fin_tip_chord"] * mm, le + g["fin_tip_chord"] * mm + 1.5, le - 0.5], [18, 18, 80, 80],
           color=FIN_COLOUR, lw=0)
    a.text(le + 40, 72, "fin", ha="center", va="center", fontsize=9)
    a.fill(X, Z, color=BULB_GREY, ec=INK, lw=1)
    xcg = (g["bulb_x_cg"] - x0) * mm
    a.plot(xcg, g["bulb_cg_above_draft"] * mm, "+", color=INK, ms=11, mew=2)
    a.annotate(f"centre of mass, {g['bulb_cg_above_draft'] * mm:.1f} mm above the draft limit\n"
               f"(about {abs(g['bulb_z_cg']) * mm:.0f} mm below the waterline upright)",
               (xcg, g["bulb_cg_above_draft"] * mm), (xcg + 60, -18), fontsize=8.5, va="center",
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    a.axhline(0, color=ACCENT, lw=1, ls=(0, (3, 2)))
    a.text(0, -1.5, "draft limit: the lowest point, 420 mm down", color=ACCENT, fontsize=8.5, ha="left", va="top")
    a.axhline(60, color=MUTED, lw=0.8, ls=(0, (1, 2)))
    a.text(0, 61.5, "60 mm: above it nothing may be wider than 20 mm (rule E.4.1)", color=MUTED, fontsize=8.5,
           ha="left", va="bottom")
    a.annotate("", (0, -30), (g["bulb_length"] * mm, -30), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
    a.text(g["bulb_length"] * mm / 2, -33, f"length {g['bulb_length'] * mm:.0f} mm, largest diameter "
           f"{g['bulb_diameter'] * mm:.1f} mm at 30 % of the length", ha="center", va="top", fontsize=8.5)
    a.set_aspect("equal")
    a.set(xlim=(-8, g["bulb_length"] * mm + 8), ylim=(-44, 82), xlabel="from the bulb's nose [mm]",
          ylabel="above the draft limit [mm]",
          title=f"The bulb of the 3D studies: {g['bulb_mass_kg'] * 1e3:.0f} g of lead, NACA 0011 thickness turned round its axis")
    a.grid(False)
    return _save(fig, out)


def bulb_sections(out: Path) -> Path:
    """The six cross-sections, three to a row, at the widest point: equal area = equal lead."""
    from iomcfd.geometry import appendages as ap

    k, p = _keel3d()
    fig, axes = plt.subplots(2, 3, figsize=(8.4, 5.0))
    for a, (name, asp, top, bot) in zip(axes.ravel(), BULB_SECTIONS):
        d = k.derive({**p, "bulb_aspect": asp, "bulb_top": top, "bulb_bottom": bot})
        ring = ap.section_ring(asp, top, bot, 240) * 0.5 * d["bulb_diameter"] * 1e3
        zc = (d["bulb_z_axis"] + float(p["draft"])) * 1e3
        a.fill(ring[:, 0], ring[:, 1] + zc, color=BULB_COLOURS[name], lw=0)
        a.plot(0, d["bulb_cg_above_draft"] * 1e3, "+", color=PAPER, ms=10, mew=2)
        a.axhline(0, color=ACCENT, lw=1, ls=(0, (3, 2)))
        a.set_aspect("equal")
        a.set(xlim=(-30, 30), ylim=(-4, 44), xticks=[-20, 0, 20], yticks=[0, 20, 40])
        a.set_title(f"{name}\n{d['bulb_width'] * 1e3:.1f} wide × {d['bulb_height'] * 1e3:.1f} high,"
                    f" CG {d['bulb_cg_above_draft'] * 1e3:.1f}", fontsize=9, loc="center", weight="normal")
        a.grid(False)
    for a in axes[:, 0]:
        a.set_ylabel("above the draft [mm]")
    fig.suptitle("Six cross-sections at the widest point (mm): the same area, so the same lead. "
                 "+ = centre of mass (CG)", fontsize=10, weight="bold", x=0.02, ha="left")
    fig.tight_layout(h_pad=2.2)
    return _save(fig, out)


def bulb_front(out: Path) -> Path:
    """Round and flat-bottom keels seen from astern, with a common fin root and the same 420 mm draft:
    the flatter bulb sits lower and its fin is longer. The waterline-to-bulb distance is broken."""
    from iomcfd.geometry import appendages as ap

    k, p = _keel3d()
    fig, (top, bot) = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [1, 1.5]})
    cases = [("round", 1.0, 2.0, 2.0, -40), ("flat bottom 1.5", 1.5, 2.0, 6.0, 40)]
    for name, asp, tp, bm, xc in cases:
        d = k.derive({**p, "bulb_aspect": asp, "bulb_top": tp, "bulb_bottom": bm})
        zr, span = d["fin_z_root"] * 1e3, d["fin_span"] * 1e3
        zaxis, h = d["bulb_z_axis"] * 1e3, d["bulb_height"] * 1e3
        t = 0.07 * d["fin_tip_chord"] * 1e3  # NACA 0007 at the tip chord, from astern
        ring = ap.section_ring(asp, tp, bm, 240) * 0.5 * d["bulb_diameter"] * 1e3
        for a in (top, bot):
            a.fill([xc - t / 2, xc + t / 2, xc + t / 2, xc - t / 2], [zr, zr, zaxis, zaxis], color=FIN_COLOUR, lw=0)
            a.fill(ring[:, 0] + xc, ring[:, 1] + zaxis, color=BULB_COLOURS[name], lw=0)
        bot.plot(xc, d["bulb_z_cg"] * 1e3, "+", color=PAPER, ms=10, mew=2)
        ztop = zaxis + h / 2
        bot.annotate("", (xc + 27, ztop), (xc + 27, -420), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
        bot.text(xc + 29, (ztop - 420) / 2, f"{h:.1f}", fontsize=8.5, va="center")
        bot.text(xc, -424, f"{name}\nfin span {span:.1f} mm\nCG {d['bulb_cg_above_draft'] * 1e3:.1f} mm above the draft",
                 ha="center", va="top", fontsize=8.5)
        top.text(xc, zr - 6, f"fin {span:.1f} mm long", ha="center", va="top", fontsize=8.5)
    for a in (top, bot):
        a.axhline(-53, color=MUTED, lw=0.8)
        a.grid(False)
    top.axhline(0, color="#5b8bb0", lw=1.2)
    top.text(-95, 2, "waterline", fontsize=8.5, color="#5b8bb0", va="bottom")
    top.text(-95, -51, "hull bottom: the fin root, the same for both", fontsize=8.5, color=MUTED, va="bottom")
    top.set(ylim=(-75, 12), yticks=[0, -53])
    bot.axhline(-420, color=ACCENT, lw=1, ls=(0, (3, 2)))
    bot.text(-95, -419, "draft limit, 420 mm", fontsize=8.5, color=ACCENT, va="bottom")
    bot.set(ylim=(-447, -365), yticks=[-420, -400, -380], xlim=(-100, 100), xticks=[], xlabel="seen from astern (mm)")
    top.spines["bottom"].set_visible(False)
    bot.spines["top"].set_visible(False)
    for a, y in ((top, 0), (bot, 1)):  # break marks
        a.plot([-0.012, 0.012], [y - 0.012, y + 0.012], transform=a.transAxes, color=MUTED, lw=1, clip_on=False)
    fig.text(0.02, 0.985, "Same lead, same length, same draft: the flatter bulb sits lower, so its fin is longer",
             fontsize=10.5, weight="bold", va="top")
    fig.text(0.02, 0.945, "(z in mm from the waterline; the 300 mm between the two panels is cut out)",
             fontsize=8.5, color=MUTED, va="top")
    fig.subplots_adjust(top=0.9, hspace=0.06)
    return _save(fig, out)


def bulb_righting(out: Path) -> Path:
    """Schematic: why the bulb's weight rights the boat only once it heels."""
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.4))
    depth, B = 401.0, np.array([0.0, -18.0])
    for a, phi, label in ((axes[0], 0.0, "upright"), (axes[1], 25.0, "heeled 25°")):
        r = np.radians(phi)
        rot = lambda x, z: (x * np.cos(r) + z * np.sin(r), -x * np.sin(r) + z * np.cos(r))  # heel to starboard (right)
        th = np.linspace(np.pi, 2 * np.pi, 60)
        hx, hz = rot(82 * np.cos(th), 53 * np.sin(th))
        a.fill(np.r_[hx, hx[0]], np.r_[hz, hz[0]], color="#e8e2d4", ec=MUTED, lw=0.8)
        mx, mz = rot(np.array([0.0, 0.0]), np.array([0.0, 230.0]))
        a.plot(mx, mz, color=MUTED, lw=1.2)
        fx, fz = rot(np.array([0.0, 0.0]), np.array([-53.0, -depth]))
        a.plot(fx, fz, color="#8aa6bf", lw=3)
        gx, gz = rot(0.0, -depth)
        a.add_patch(plt.Circle((gx, gz), 19, color=ACCENT, zorder=3))
        bx = B[0] + (14 if phi else 0)  # the centre of buoyancy moves to leeward as the hull heels
        a.plot(bx, B[1], "o", color="#2f5d50", ms=6, zorder=4)
        a.annotate("", (gx, gz - 72), (gx, gz - 22), arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.8))
        a.text(gx - 6, gz - 50, "bulb's\nweight", ha="right", fontsize=8.5, color=ACCENT)
        a.annotate("", (bx, B[1] + 120), (bx, B[1]), arrowprops=dict(arrowstyle="-|>", color="#2f5d50", lw=1.8))
        a.text(bx + 6, B[1] + 70, "buoyancy", fontsize=8.5, color="#2f5d50")
        a.axhline(0, color="#5b8bb0", lw=1)
        if phi:
            a.plot([gx, gx], [gz, B[1]], color=MUTED, lw=0.6, ls=":")
            a.plot([bx, bx], [B[1], -330], color=MUTED, lw=0.6, ls=":")
            a.annotate("", (gx, -300), (bx, -300), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
            a.text(bx + 8, -300, "lever ≈ depth\n× sin φ", va="center", fontsize=8.5)
            a.text(0.5, 0.02, "the weight and the buoyancy are a couple that turns the boat upright",
                   transform=a.transAxes, ha="center", fontsize=8.5, color=INK)
        else:
            a.text(0.5, 0.02, "weight and buoyancy on one vertical line: no moment", transform=a.transAxes,
                   ha="center", fontsize=8.5, color=INK)
        a.set_aspect("equal")
        a.set(xlim=(-260, 260), ylim=(-520, 250), title=f"Seen from astern, {label}")
        a.axis("off")
    fig.text(0.5, -0.02, "Schematic: only the bulb's weight is drawn. The hull's own shape also moves the buoyancy "
             "(form stability); the rig's weight acts the other way.", ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    return _save(fig, out)


def bulb_endplate_schematic(out: Path) -> Path:
    """Schematic: the pressure difference across the fin drives water round a free tip; a bulb blocks part of it."""
    from matplotlib.patches import Ellipse

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.6))
    for a, bulb in zip(axes, (False, True)):
        a.fill([-4, 4, 4, -4], [-10, -10, 100, 100], color=FIN_COLOUR, lw=0)
        a.text(-14, 60, "low\npressure", ha="right", fontsize=8.5, color="#3b6ea5")
        a.text(14, 60, "high\npressure", ha="left", fontsize=8.5, color=ACCENT)
        if bulb:
            a.add_patch(Ellipse((0, -18), 40, 38, color=BULB_GREY))
            a.add_patch(FancyArrowPatch((22, -8), (-22, -8), connectionstyle="arc3,rad=1.25", arrowstyle="-|>",
                                        mutation_scale=12, color=MUTED, lw=1.2))
            a.text(0, -62, "the bulb blocks the leak at the fin's tip:\nthe fin keeps more of its load there",
                   ha="center", va="top", fontsize=8.5)
        else:
            a.add_patch(FancyArrowPatch((10, -2), (-10, -2), connectionstyle="arc3,rad=1.6", arrowstyle="-|>",
                                        mutation_scale=14, color=INK, lw=1.6))
            a.text(0, -62, "water leaks round the free tip:\nthe tip carries little load (a tip vortex)",
                   ha="center", va="top", fontsize=8.5)
        a.set_aspect("equal")
        a.set(xlim=(-70, 70), ylim=(-90, 105), title="fin alone" if not bulb else "fin with a bulb")
        a.axis("off")
    fig.text(0.5, 0.0, "Schematic, seen from astern, the boat making leeway to starboard (right). Not to scale.",
             ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    return _save(fig, out)


def bulb_spanload(data: Path, out: Path) -> Path:
    s = pd.read_csv(data / "bulb-spanload.csv")
    e = pd.read_csv(data / "bulb-endplate.csv")
    e = e[(e["mesh"] == "medium") & (e.leeway == 4)]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.0, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
    for key, name, colour in (("bulbtrue", "fin with the bulb", ACCENT), ("bulbfalse", "the same fin alone", "#2f5d50")):
        m = s[s.file.str.startswith(key)].sort_values("eta")
        a.plot(m.side_N_per_m, m.eta, "-o", ms=3.5, color=colour, label=name)
    a.axhspan(0.8, 1.0, color=RULE, alpha=0.5, lw=0)
    a.text(1, 0.9, "last 20 % of the span:\nthe fin's load holds up\nnext to the bulb", fontsize=8.5, va="center")
    a.invert_yaxis()
    a.set(xlabel="fin side force per metre of span [N/m]", ylabel="along the fin: 0 = hull, 1 = top of the bulb",
          xlim=(0, None), title="Along the fin, 4° leeway, upright, 1 m/s")
    a.legend(loc="upper left")
    w = e[e.bulb.astype(str) == "True"].iloc[0]
    wo = e[e.bulb.astype(str) == "False"].iloc[0]
    b.bar([0], [wo.side_fin_N], color="#2f5d50", width=0.55)
    b.bar([1], [w.side_fin_N], color=ACCENT, width=0.55, label="fin")
    b.bar([1], [w.side_keel_N - w.side_fin_N], bottom=[w.side_fin_N], color=BULB_GREY, width=0.55, label="bulb")
    for x, v in ((0, wo.side_keel_N), (1, w.side_keel_N)):
        b.text(x, v + 0.08, f"{v:.2f} N", ha="center", fontsize=9)
    b.set(xticks=[0, 1], xticklabels=["fin alone", "fin + bulb"], ylabel="keel side force [N]", ylim=(0, 6.2),
          title="The split at 4°")
    from matplotlib.patches import Patch

    b.legend(handles=[Patch(color=ACCENT, label="its fin"), Patch(color=BULB_GREY, label="the bulb")], loc="lower right")
    b.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, out)


def bulb_family(data: Path, out: Path) -> Path:
    """The fineness study's bodies: 2380 g of lead as NACA bodies of six lengths, noses aligned."""
    from iomcfd.geometry import axisym

    f = pd.read_csv(data / "bulb-fineness.csv").groupby("fineness")[["length_m", "diameter_m"]].first()
    fig, a = plt.subplots(figsize=(8.6, 4.2))
    notes = {5.7: "Gilbert's 250 mm bulb", 7.5: "his 300 mm", 9.09: "the 3D studies' bulb; his 350 mm",
             14.29: "the project's first bulb, NACA 0007"}
    for i, (fn, r) in enumerate(f.iterrows()):
        x, rad = axisym.naca_profile(1 / fn).dense(300)
        L = r.length_m * 1e3
        y0 = -i * 52
        colour = ACCENT if abs(fn - 9.09) < 1e-6 else "#8a8f96"
        a.fill(np.r_[x, x[::-1]] * L, np.r_[rad, -rad[::-1]] * L + y0, color=colour, alpha=0.8, lw=0)
        a.text(L + 8, y0, f"{L:.0f} × {r.diameter_m * 1e3:.1f} mm (L/D {fn:g})" + (f" · {notes[fn]}" if fn in notes else ""),
               va="center", fontsize=8.5)
    a.set_aspect("equal")
    a.set(xlim=(-5, 790), xlabel="from the nose [mm]", yticks=[],
          title="The same 2380 g of lead at six lengths (largest diameter at 30 % of the length)")
    a.spines["left"].set_visible(False)
    a.grid(axis="y", visible=False)
    return _save(fig, out)


def bulb_length_mechanism(data: Path, out: Path) -> Path:
    """251 vs 343 mm at 1 m/s (transition, Tu 0.1 %): the bodies at the same scale, Cp and signed Cf along x/L."""
    from iomcfd.geometry import axisym

    s = pd.read_csv(data / "bulb-surface.csv")
    f = pd.read_csv(data / "bulb-fineness.csv")
    f = f[(f.speed == 1.0) & (f.turbulence == "kOmegaSSTLM") & (f.Tu == 0.1)].set_index("fineness")
    fig = plt.figure(figsize=(8.4, 7.4))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.8, 1, 1.2], hspace=0.45)
    a0 = fig.add_subplot(gs[0])
    cases = [(5.7, "fineness5.7_", "251 mm (L/D 5.7)", "#5c4d7d", 26), (9.09, "fineness9.09_", "343 mm (L/D 9.1)", ACCENT, -26)]
    for fn, key, name, colour, y0 in cases:
        L = f.loc[fn].length_m * 1e3
        x, r = axisym.naca_profile(1 / fn).dense(300)
        a0.fill(np.r_[x, x[::-1]] * L, np.r_[r, -r[::-1]] * L + y0, color=colour, alpha=0.85, lw=0)
        sep = f.loc[fn].x_sep
        if pd.notna(sep):
            a0.plot(sep * L, y0 + np.interp(sep, x, r) * L, "v", color=INK, ms=7)
            a0.text(sep * L + 4, y0 + np.interp(sep, x, r) * L + 3, f"separates at {sep:.2f} L = {sep * L:.0f} mm",
                    fontsize=8.5)
        else:
            a0.text(L + 6, y0, "stays attached", fontsize=8.5, va="center")
        a0.text(-6, y0, name, ha="right", va="center", fontsize=8.5)
    a0.set_aspect("equal")
    a0.set(xlim=(-110, 400), yticks=[], xlabel="from the nose [mm] (same physical scale; flow left to right)",
           title="The same 2380 g of lead: short and fat against the 3D studies' bulb")
    a0.spines["left"].set_visible(False)
    a0.grid(False)
    a1 = fig.add_subplot(gs[1])
    a2 = fig.add_subplot(gs[2], sharex=a1)
    for fn, key, name, colour, _ in cases:
        m = s[s.file.str.contains(key)].sort_values("x_L")
        a1.plot(m.x_L, m.Cp, color=colour, label=name)
        a2.plot(m.x_L, m.Cf, color=colour, label=name)
        sep, rea = f.loc[fn].x_sep, f.loc[fn].x_reattach
        if pd.notna(sep):
            a2.axvline(sep, color=colour, lw=0.8, ls=":")
    a1.invert_yaxis()
    a1.set(ylabel="pressure coefficient C$_p$", ylim=(0.25, -0.25),
           title="Pressure along the bulb: it rises again over the tail (adverse gradient)")
    a1.legend(loc="lower right")
    a2.axhline(0, color=INK, lw=0.8)
    a2.fill_between([0, 1], -0.004, 0, color="#d9e4f0", lw=0, zorder=0)
    a2.text(0.02, -0.0025, "C$_f$ < 0: the flow at the wall runs backwards (separated)", fontsize=8.5, color="#3b6ea5")
    a2.set(xlim=(0, 1), ylim=(-0.004, 0.012), xlabel="along the bulb, x / L (each bulb's own length)",
           ylabel="skin friction C$_f$ (signed)", title="Skin friction: the fat bulb's laminar layer separates on its tail")
    return _save(fig, out)


def bulb_drag_parts(data: Path, out: Path) -> Path:
    f = pd.read_csv(data / "bulb-fineness.csv")
    lm = f[(f.speed == 1.0) & (f.turbulence == "kOmegaSSTLM") & (f.Tu == 0.1)].sort_values("length_m")
    tb = f[(f.speed == 1.0) & (f.turbulence == "kOmegaSST")].sort_values("length_m")
    L = lm.length_m * 1e3
    fig, a = plt.subplots(figsize=(7.6, 3.8))
    x = np.arange(len(L))
    a.bar(x, lm.drag_friction_N * 1e3, color="#8aa6bf", width=0.6, label="skin friction")
    a.bar(x, lm.drag_pressure_N * 1e3, bottom=lm.drag_friction_N * 1e3, color=ACCENT, width=0.6,
          label="pressure (grows when the flow separates)")
    a.plot(x, tb.drag_N * 1e3, "o", mfc="none", mec="#2f5d50", mew=1.5, label="fully turbulent total, for comparison")
    a.set(xticks=x, xticklabels=[f"{v:.0f} mm" for v in L], ylim=(0, 118), ylabel="drag of the bulb alone [mN]",
          title="Bulb drag at 1 m/s split in two (transition model, Tu 0.1 %)")
    a.legend(loc="upper left", fontsize=8)
    a.grid(axis="x", visible=False)
    return _save(fig, out)


def bulb_fineness(data: Path, out: Path) -> Path:
    f = pd.read_csv(data / "bulb-fineness.csv")
    f["L"] = f.length_m * 1e3
    fig, a = plt.subplots(figsize=(7.2, 3.9))
    for speed, colour in ((0.5, "#7fae94"), (1.0, ACCENT), (1.5, "#5c4d7d")):
        m = f[(f.speed == speed) & (f.turbulence == "kOmegaSSTLM") & (f.Tu == 0.1)].sort_values("L")
        ref = float(m[np.isclose(m.fineness, 9.09)].drag_N.iloc[0])
        a.plot(m.L, 100 * (m.drag_N / ref - 1), "-o", ms=4, color=colour, label=f"{speed:g} m/s")
    a.axhline(0, color=MUTED, lw=0.8)
    a.axvspan(345, 365, color=RULE, alpha=0.6, lw=0)
    a.text(355, 22, "bulbs\nsold", ha="center", fontsize=8, color=MUTED)
    a.set(xlabel="bulb length [mm], 2380 g of lead", ylabel="bulb drag against the 343 mm bulb [%]",
          title="Bulb drag by length (bulb alone, transition model, Tu 0.1 %)")
    a.legend(title="boat speed")
    return _save(fig, out)


def bulb_dress(data: Path, ref_csv: Path, out: Path) -> Path:
    v = pd.read_csv(data / "bulb-dress.csv")
    v = v[v["mesh"] == "medium"]
    ref = pd.read_csv(ref_csv, comment="#")
    fig, a = plt.subplots(figsize=(7.4, 4.2))
    a.plot(ref.Re_L, ref.Cd_wet, "s", color=INK, ms=5, label="measured, free transition (Dress 1988)")
    for tu, colour in ((0.05, ACCENT), (0.1, "#e09a4f"), (0.2, "#b3a27f"), (0.5, "#8a8f96")):
        m = v[(v.turbulence == "kOmegaSSTLM") & (v.Tu == tu)].sort_values("Re_L")
        a.plot(m.Re_L, m.Cd_wet, "-o", color=colour, ms=3.5, label=f"transition model, Tu {tu:g} %")
    m = v[v.turbulence == "kOmegaSST"].sort_values("Re_L")
    a.plot(m.Re_L, m.Cd_wet, "--o", color="#2f5d50", ms=3.5, label="fully turbulent")
    fin = pd.read_csv(data / "bulb-fineness.csv")  # the bulbs of this page: 230-464 mm at 0.5-1.5 m/s
    a.axvspan(fin.Re_L.min(), fin.Re_L.max(), color=RULE, alpha=0.5, lw=0)
    a.text(np.sqrt(fin.Re_L.min() * fin.Re_L.max()), 0.0127, "the bulbs of this page, 0.5–1.5 m/s", ha="center",
           va="top", fontsize=8.5, color=MUTED)
    a.set_xscale("log")
    a.set(xlabel="length Reynolds number Re$_L$", ylabel="C$_D$ on the wetted area", ylim=(0.0020, 0.0130),
          xlim=(0.85e5, 1.6e6), title="Drag of Dress's laminar body: measured and computed")
    a.legend(loc="lower left", fontsize=8)
    return _save(fig, out)


def bulb_endplate(data: Path, out: Path) -> Path:
    e = pd.read_csv(data / "bulb-endplate.csv")
    e = e[e["mesh"] == "medium"].sort_values("leeway")
    fig, a = plt.subplots(figsize=(6.4, 3.8))
    w, wo = e[e.bulb.astype(str) == "True"], e[e.bulb.astype(str) == "False"]
    a.plot(w.leeway, w.side_keel_N, "-o", color=ACCENT, label="fin + bulb")
    a.plot(w.leeway, w.side_fin_N, ":o", color=ACCENT, ms=3.5, label="… of which the fin")
    a.plot(wo.leeway, wo.side_keel_N, "-o", color="#2f5d50", label="the same fin alone")
    for lw in (2, 4):
        s1, s0 = float(w[w.leeway == lw].side_keel_N.iloc[0]), float(wo[wo.leeway == lw].side_keel_N.iloc[0])
        a.annotate("", (lw, s1), (lw, s0), arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=0.8))
        right = lw == 4  # at 2 deg the lines run through the right-hand side: label above them, on the left
        a.text(lw + 0.08 if right else lw - 0.08, (s1 + s0) / 2 if right else s1 + 0.2, f"+{100 * (s1 / s0 - 1):.0f} %",
               va="center", ha="left" if right else "right", fontsize=9, color=ACCENT)
    a.set(xlabel="leeway β$_Y$ [°]", ylabel="keel side force S$_h$ [N]", xlim=(-0.15, 4.6),
          title="Side force at the same leeway, with and without the bulb")
    a.legend(loc="upper left")
    return _save(fig, out)


def bulb_race(data: Path) -> pd.DataFrame:
    """Race time lost against the best bulb section (keel3d's compare_at_equal_force), in three scenarios:
    as computed; with the friction scaled towards transition; and with the upper-end righting-moment credit
    too. Sensitivity scenarios (estimates), not validated corrections."""
    k, _ = _keel3d()
    df = pd.read_csv(data / "bulb-section.csv")
    df = df[df["mesh"] == "medium"]
    fn = pd.read_csv(data / "bulb-fineness.csv")
    fr = fn[np.isclose(fn.fineness, 9.09) & (fn.speed == 1.0)]
    r_b = float(fr[(fr.turbulence == "kOmegaSSTLM") & (fr.Tu == 0.1)].drag_friction_N.iloc[0]) / \
        float(fr[fr.turbulence == "kOmegaSST"].drag_friction_N.iloc[0])
    opts = {"compare_at": {"bulb_aspect": 1.0, "bulb_top": 2.0, "bulb_bottom": 2.0, "leeway": [2, 4]}}
    frames = []
    for variant, rb, rf in (("computed", 1.0, 1.0), ("corrected", r_b, FIN_FRICTION)):
        d = df.copy()
        d["drag_N"] = d.drag_N - (1 - rb) * d.drag_bulb_friction_N - (1 - rf) * d.drag_fin_friction_N
        t = k.compare_at_equal_force(d, opts)
        t["variant"] = variant
        frames.append(t)
    t = pd.concat(frames, ignore_index=True)
    t["section"] = _section_name(t)
    cg0 = float(t[t.section == "round"].bulb_cg_above_draft.iloc[0])
    t["rm_pct"] = 100 * (cg0 - t.bulb_cg_above_draft) / (RM_DRAFT_TO_CB - t.bulb_cg_above_draft)
    rm = t[t.variant == "corrected"].copy()
    for c in ("loss_x1_pct", "loss_x2_pct"):
        rm[c] = rm[c] - 0.5 * RM_SPEED * rm.rm_pct  # upwind is half the race
    rm["variant"] = "rm"
    t = pd.concat([t, rm], ignore_index=True)
    t.attrs["r_b"] = r_b
    return t


def bulb_section_race(data: Path, out: Path) -> Path:
    t = bulb_race(data)
    names = [n for n, *_ in BULB_SECTIONS]
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 6.8), sharex=True)
    for a, heel in zip(axes, (0, 25)):
        s = t[(t.heel == heel) & (t.load == "working")]
        y = np.arange(len(names))
        for j, (key, label_, marker) in enumerate(SCENARIOS):
            v = s[s.variant == key].set_index("section").reindex(names)
            yy = y + (j - 1) * 0.22
            a.hlines(yy, v.loss_x2_pct, v.loss_x1_pct, color=MUTED, lw=1)  # x2 to x1 resistance slope
            a.scatter(v.loss_x1_pct, yy, marker=marker, s=34, c=[BULB_COLOURS[n] for n in names],
                      edgecolors=INK if marker != "o" else "none", linewidths=0.6, zorder=3)
        a.axvline(0, color=INK, lw=0.8)
        a.set_yticks(y, names)
        a.invert_yaxis()
        f0 = s[(s.section == "round") & (s.variant == "computed")].side_N.iloc[0]
        a.set_title(f"{'Upright' if heel == 0 else f'Heel {heel}°'}, working load (S$_h$ = {f0:.2f} N)",
                    fontsize=10)
        a.grid(axis="y", visible=False)
    axes[1].set_xlabel("race time lost against the round bulb [%] (positive: slower; negative: a modelled gain)")
    from matplotlib.lines import Line2D

    axes[1].legend(handles=[Line2D([], [], ls="", marker=m, color=MUTED, mec=INK if m != "o" else MUTED, label=lb)
                            for _, lb, m in SCENARIOS] + [Line2D([], [], color=MUTED, lw=1, label="to the same with the "
                                                                 "resistance slope doubled")],
                   loc="upper right", fontsize=7.5)
    fig.tight_layout()
    return _save(fig, out)


def bulb_race_table(data: Path, out: Path) -> Path:
    t = bulb_race(data)
    cols = [(0, "light"), (0, "working"), (25, "light"), (25, "working")]
    rows = ["| section | scenario | upright, light | upright, working | 25°, light | 25°, working |",
            "|:--|:--|--:|--:|--:|--:|"]
    lab = {"computed": "as computed", "corrected": "friction scaled", "rm": "+ RM credit (upper)"}
    for n, *_ in BULB_SECTIONS[1:]:
        for key in ("computed", "corrected", "rm"):
            vals = []
            for heel, load in cols:
                r = t[(t.section == n) & (t.variant == key) & (t.heel == heel) & (t.load == load)]
                vals.append(f"{r.loss_x1_pct.iloc[0]:.2f}" if len(r) else "–")
            rows.append(f"| {n if key == 'computed' else ''} | {lab[key]} | " + " | ".join(vals) + " |")
    out.write_text("\n".join(rows) + "\n")
    return out


def bulb_loads_table(data: Path, out: Path) -> Path:
    t = bulb_race(data)
    s = t[(t.section == "round") & (t.variant == "computed")]
    rows = ["| | light load | working load |", "|:--|--:|--:|"]
    for heel in (0, 25):
        r = s[s.heel == heel].set_index("load").side_N
        rows.append(f"| {'upright' if heel == 0 else f'heel {heel}°'} | {r['light']:.2f} N | {r['working']:.2f} N |")
    out.write_text("\n".join(rows) + "\n")
    return out


def bulb_drag_split(data: Path, out: Path) -> Path:
    df = pd.read_csv(data / "bulb-section.csv")
    df = df[(df["mesh"] == "medium") & (df.heel == 0) & (df.leeway == 0)].copy()
    df["section"] = _section_name(df)
    df = df.set_index("section")
    base = df.loc["round"]
    names = [n for n, *_ in BULB_SECTIONS][1:]
    fin = [(df.loc[n].drag_fin_N - base.drag_fin_N) * 1e3 for n in names]
    bulb = [(df.loc[n].drag_bulb_N - base.drag_bulb_N) * 1e3 for n in names]
    fig, a = plt.subplots(figsize=(7.2, 3.4))
    y = np.arange(len(names))
    a.barh(y, fin, color="#8aa6bf")
    a.barh(y, bulb, left=fin, color=[BULB_COLOURS[n] for n in names])
    for i, n in enumerate(names):
        a.text(fin[i] + bulb[i] + 0.3, i, f"fin {1e3 * (df.loc[n].fin_span - base.fin_span):+.0f} mm longer", va="center",
               fontsize=8, color=MUTED)
    a.set_yticks(y, names)
    a.invert_yaxis()
    a.set(xlim=(0, 24), xlabel=f"extra drag of the modelled hull + fin + bulb against the round bulb's "
                                f"({base.drag_N * 1e3:.0f} mN), upright, 0° [mN]",
          title="Where a flatter bulb's extra drag comes from (fully turbulent)")
    from matplotlib.patches import Patch

    a.legend(handles=[Patch(color="#8aa6bf", label="its longer fin"), Patch(color=MUTED, label="the bulb itself")],
             loc="upper right")
    a.grid(axis="y", visible=False)
    return _save(fig, out)


def bulb_cant_schematic(out: Path) -> Path:
    """Cant on the real bulb (0 and 4 deg nose up, about the centre of mass, then moved to the draft), and how
    heel turns part of the sideways flow into flow along the fin at the bulb (schematic)."""
    k, p = _keel3d()
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1.6, 1]})
    for cant, colour in ((0, BULB_GREY), (4, ACCENT)):
        X, Z, g, x0 = _bulb_outline(k, p, bulb_cant=cant)
        if cant == 0:
            a.fill(X, Z, color=colour, lw=0, alpha=0.7, label="0°")
        else:
            a.plot(np.r_[X, X[:1]], np.r_[Z, Z[:1]], "--", color=colour, lw=1.4, label=f"{cant}° nose up")
        a.plot((g["bulb_x_cg"] - x0) * 1e3, g["bulb_cg_above_draft"] * 1e3, "+", color=INK if cant == 0 else ACCENT,
               ms=10, mew=1.8)
    a.axhline(0, color=ACCENT, lw=1, ls=(0, (3, 2)))
    a.text(2, -2, "draft limit: the lowest point stays here", color=ACCENT, fontsize=8.5, va="top")
    a.annotate("nose up", (6, 30), (30, 54), fontsize=8.5, arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=0.9))
    a.set_aspect("equal")
    a.set(xlim=(-8, 352), ylim=(-16, 64), xlabel="from the nose [mm] (flow left to right)", ylabel="mm",
          title="Cant, seen from the side (+ = centre of mass)")
    a.legend(loc="upper right")
    a.grid(False)
    phi = np.radians(25)
    ux, uz = -np.sin(phi), -np.cos(phi)  # down the fin: heeled to starboard, the keel swings to port (left)
    b.plot([0, 300 * ux], [0, 300 * uz], color="#8aa6bf", lw=4)
    b.add_patch(plt.Circle((330 * ux, 330 * uz), 22, color=BULB_GREY))
    b.plot([0, 220 * np.sin(phi)], [0, 220 * np.cos(phi)], color=MUTED, lw=1.2)  # the mast, in line with the fin
    b.axhline(0, color="#5b8bb0", lw=1)
    o = np.array([300 * ux + 300, 300 * uz + 110])
    flow = np.array([-150.0, 0.0])  # the boat slides to starboard (right): the water moves to port (left)
    b.annotate("", o + flow, o, arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6))
    b.text(o[0] - 75, o[1] + 10, "sideways flow (leeway)", ha="center", fontsize=8.2)
    d = np.array([ux, uz])
    along = (flow @ d) * d
    b.annotate("", o + along, o, arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.4))
    b.text(o[0] + along[0] + 6, o[1] + along[1] - 4, "its part along the fin,\nabout β$_Y$ sin φ of the flow:\n"
           "it meets the bulb at\nan angle (from above)", fontsize=8, color=ACCENT, va="top")
    b.set_aspect("equal")
    b.set(xlim=(-190, 330), ylim=(-400, 230), title="Heeled 25°, seen from astern")
    b.axis("off")
    fig.tight_layout()
    return _save(fig, out)

def bulb_cant(data: Path, out: Path) -> Path:
    k, _ = _keel3d()
    df = pd.read_csv(data / "bulb-cant.csv")
    t = k.compare_at_equal_force(df, {"compare_at": {"bulb_aspect": 1.0, "bulb_bottom": 2.0, "bulb_cant": 0.0,
                                                      "leeway": [2, 4]}})
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6), sharey=True)
    for a, load in zip(axes, ("light", "working")):
        s = t[t.load == load]
        for asp, name, colour in ((1.0, "round", ACCENT), (1.5, "flat bottom 1.5", "#2f5d50")):
            m = s[s.bulb_aspect == asp].sort_values("bulb_cant")
            a.plot(m.bulb_cant, m.loss_x1_pct, "-o", color=colour, label=name)
            for x, v in zip(m.bulb_cant, m.loss_x1_pct):
                a.text(x, v + 0.035, f"{v:.2f}", ha="center", fontsize=8, color=colour)
        f0 = s.side_N.iloc[0]
        a.set(xticks=[0, 2, 4], xlabel="cant, nose up [°]", ylim=(-0.08, 1.15),
              title=f"25° heel, {load} load (S$_h$ = {f0:.2f} N)")
    axes[0].set_ylabel("race time lost against the best [%]")
    axes[1].legend(loc="center right")
    fig.tight_layout()
    return _save(fig, out)


def bulb_sections_table(data: Path, out: Path) -> Path:
    df = pd.read_csv(data / "bulb-section.csv")
    df = df[(df["mesh"] == "medium") & (df.heel == 0) & (df.leeway == 0)].copy()
    df["section"] = _section_name(df)
    df = df.set_index("section").reindex([n for n, *_ in BULB_SECTIONS])
    rows = ["| section | W × H | CG | area | fin |", "|:--|--:|--:|--:|--:|"]
    for n, r in df.iterrows():
        rows.append(f"| {n} | {1e3 * r.bulb_width:.1f}&nbsp;×&nbsp;{1e3 * r.bulb_height:.1f} | "
                    f"{1e3 * r.bulb_cg_above_draft:.1f} | {1e4 * r.bulb_wetted_area_m2:.0f} | {1e3 * r.fin_span:.1f} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def bulb_card(data: Path, out: Path) -> Path:
    """The bulb page's card at 3:1: the bulb and the foot of the fin from the side, with two of the
    cross-sections (round and flat bottom) beside it."""
    from iomcfd.geometry import appendages as ap

    k, p = _keel3d()
    X, Z, g, x0 = _bulb_outline(k, p)
    fig = plt.figure(figsize=(9, 3))
    a = fig.add_axes([0, 0, 1, 1])
    le = (g["bulb_x_cg"] - 0.25 * g["fin_tip_chord"] - x0) * 1e3
    a.fill([le, le + g["fin_tip_chord"] * 1e3, le + g["fin_tip_chord"] * 1e3 + 4, le - 2], [20, 20, 140, 140],
           color=FIN_COLOUR, lw=0)
    a.fill(X, Z, color="#5d6670", lw=0)
    for i, (name, asp, top, bot) in enumerate([BULB_SECTIONS[0], BULB_SECTIONS[3]]):
        d = k.derive({**p, "bulb_aspect": asp, "bulb_top": top, "bulb_bottom": bot})
        ring = ap.section_ring(asp, top, bot, 240) * 0.5 * d["bulb_diameter"] * 1e3
        a.fill(ring[:, 0] + 395 + i * 58, ring[:, 1] + (d["bulb_z_axis"] + float(p["draft"])) * 1e3,
               color=BULB_COLOURS[name], lw=0)
    a.axhline(0, color=ACCENT, lw=1.4, ls=(0, (4, 3)))
    a.set_aspect("equal")
    a.set(xlim=(-16, 494), ylim=(-36, 134))  # 510 x 170: 3:1
    a.axis("off")
    fig.savefig(out, dpi=120, facecolor=PAPER)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# The fin section page (site/custom-section/index.qmd). Data: custom-*.csv. The ranking is
# `python -m iomcfd.sectiondesign cfd`'s (projects/foil2d/findings/custom-section.md), and the shapes
# come from the section coordinates in geometry/foils/.

BASE, HT35, OPT2 = "naca0007/100", "file:ht35-t0725.dat/100", "file:cst-opt2.dat/100"
CUSTOM_NAMES = {
    BASE: "NACA 0007", HT35: "HT35 at 7.25 %", OPT2: "cst-opt2", "file:ht35-t070.dat/100": "HT35 at 7 %",
    "file:sd8020-t070.dat/100": "SD8020 at 7 %", "file:cst-opt1.dat/100": "cst-opt1",
    "file:ht14-t070.dat/100": "HT14 at 7 %", "file:naca0007-73.dat/100": "NACA 0007-73",
    "file:naca64-007.dat/100": "NACA 64-007",
}
CUSTOM_COLOURS = {BASE: "#3c4a57", HT35: ACCENT, OPT2: "#2f5d50"}
# the shapes: HT35 from the UIUC coordinates scaled to 7.25 % (ht35-t0725.dat, which the CFD meshed, has
# the same shape to 1e-7 c, but its 7 decimals spoil a nose radius read back from it)
CUSTOM_SPECS = {BASE: "naca0007", HT35: "file:ht35.dat@0.0725", OPT2: "file:cst-opt2.dat"}
CUSTOM_SPEEDS = (0.75, 1.0, 1.5)
WIND = {0.75: "light air", 1.0: "medium", 1.5: "fresh"}


def custom_polars(data: Path, tu: float = 0.1) -> pd.DataFrame:
    """The section polars behind the ranking (candidate, foil, chord, speed, aoa, Cl, Cd, Tu). Tu 0.1 %: the
    steady screen and optima runs, with the time-accurate points replacing theirs, later files winning
    (NACA 0007 at 4 deg and 1.5 m/s: started from rest); `steady_only` leaves them out. Tu 1 and 2 %:
    the steady runs (the flow is steady there)."""
    from iomcfd import sectiondesign as sd

    if tu == 0.1:
        base = [data / "custom-steady.csv", data / "custom-optima.csv"]
        replace = [data / f"custom-{n}.csv" for n in
                   ("transient", "transient-opt2", "transient-15", "transient-rerun", "0007-rest")]
    else:
        base, replace = [data / "custom-tu.csv", data / "custom-tu-opt2.csv"], []
    return sd.cfd_table(base, replace, tu=tu, speeds=list(CUSTOM_SPEEDS)).assign(Tu=tu)


def custom_rank(data: Path, tu: float = 0.1, candidates=(BASE, HT35, OPT2), steady_only: bool = False) -> pd.DataFrame:
    """sectiondesign.rank against NACA 0007/100: `vs_base` per candidate, slope (x1, x2), speed and load,
    % of race time (negative = faster)."""
    from iomcfd import sectiondesign as sd

    if steady_only:
        t = sd.cfd_table([data / "custom-steady.csv", data / "custom-optima.csv"], tu=0.1,
                         speeds=list(CUSTOM_SPEEDS)).assign(Tu=0.1)
    else:
        t = custom_polars(data, tu)
    return sd.rank(t[t.candidate.isin(candidates)] if candidates else t, BASE)


def custom_parts(data: Path) -> pd.DataFrame:
    """The race-time gain of HT35 and cst-opt2 over NACA 0007 (Tu 0.1 %, slope x1) per speed and load, split
    as methodology.md adds it up (half the race upwind, half downwind): extra drag upwind, extra leeway,
    extra drag downwind at 0 deg. Positive = a gain."""
    from iomcfd import racetime

    c = racetime.Course()
    rk = custom_rank(data)
    rk = rk[rk.slope == 1.0].set_index(["speed", "load"])
    base = rk[rk.candidate == BASE]
    rows = []
    for cand in (HT35, OPT2):
        r = rk[rk.candidate == cand]
        slope = np.array([c.vdrdv_at(v) for v, _ in r.index])
        rows.append(pd.DataFrame({
            "candidate": cand,
            "upwind drag": -50 * (r.drag_up - base.drag_up).to_numpy() / slope,
            "leeway": -50 * np.tan(np.radians(c.track_deg)) * np.radians(r.aoa - base.aoa).to_numpy(),
            "downwind drag": -50 * (r.drag_0 - base.drag_0).to_numpy() / slope,
            "total": -r.vs_base.to_numpy(),
        }, index=r.index))
    return pd.concat(rows).reset_index()


def custom_shapes(out: Path) -> Path:
    """NACA 0007, HT35 at 7.25 % and cst-opt2 at 100 mm: at true scale, the half-thickness stretched,
    HT35 and cst-opt2 minus NACA 0007, and the nose and tail at true scale."""
    from iomcfd import sectiondesign as sd

    C = 100.0
    secs = {k: sd.load(s) for k, s in CUSTOM_SPECS.items()}
    props = {k: sd.properties(f) for k, f in secs.items()}
    x = np.linspace(0, 1, 4001)
    half = {k: np.interp(x, *f.surface("upper", 1600).T) * C for k, f in secs.items()}
    order = (BASE, OPT2, HT35)  # HT35 drawn last, on top
    lw = {BASE: 1.6, OPT2: 1.1, HT35: 2.0}
    ls = {BASE: "-", OPT2: (0, (4, 2)), HT35: "-"}
    fig = plt.figure(figsize=(9.6, 7.4))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.55, 1.15, 1.25], width_ratios=[1.75, 1], hspace=0.6, wspace=0.22)
    a = fig.add_subplot(gs[0, :])
    up = secs[BASE].surface("upper", 800) * C
    a.fill(np.r_[up[:, 0], up[::-1, 0]], np.r_[up[:, 1], -up[::-1, 1]], color="#d9d3c4", lw=0)
    for k in (BASE, HT35):
        u = secs[k].surface("upper", 800) * C
        a.plot(np.r_[u[:, 0], u[::-1, 0]], np.r_[u[:, 1], -u[::-1, 1]], color=CUSTOM_COLOURS[k], lw=lw[k] * 0.7)
    a.set_aspect("equal")
    a.set(xlim=(-1, 101), ylim=(-4.5, 4.5), yticks=[], title="At true scale: 100 mm chord, about 7 mm thick")
    a.grid(False)
    a.spines["left"].set_visible(False)
    b = fig.add_subplot(gs[1, :])
    for k in order:
        b.plot(x * C, half[k], color=CUSTOM_COLOURS[k], lw=lw[k], ls=ls[k], label=CUSTOM_NAMES[k])
        p = props[k]
        b.plot(p["x_t"] * C, p["t"] * C / 2, "o", color=CUSTOM_COLOURS[k], ms=5)
    p0, p1 = props[BASE], props[HT35]
    b.annotate(f"thickest {p1['t'] * C:.2f} mm\nat {p1['x_t'] * C:.0f} mm", (p1["x_t"] * C, p1["t"] * C / 2),
               (14, 1.2), color=ACCENT, fontsize=8.5, arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.8))
    b.annotate(f"thickest {p0['t'] * C:.2f} mm\nat {p0['x_t'] * C:.0f} mm", (p0["x_t"] * C, p0["t"] * C / 2),
               (42, 3.9), color=CUSTOM_COLOURS[BASE], fontsize=8.5,
               arrowprops=dict(arrowstyle="-", color=CUSTOM_COLOURS[BASE], lw=0.8))
    b.set(xlim=(0, 100), ylim=(0, 4.6), xlabel="from the leading edge [mm]", ylabel="half-thickness [mm]",
          title="Half the section, vertical scale stretched about 7 times")
    b.legend(loc="upper right")
    d = fig.add_subplot(gs[2, 0])
    for k in (OPT2, HT35):
        d.plot(x * C, half[k] - half[BASE], color=CUSTOM_COLOURS[k], lw=lw[k], ls=ls[k])
    d.axhline(0, color=CUSTOM_COLOURS[BASE], lw=1)
    d.text(21, 0.31, "fuller than NACA 0007", color=MUTED, fontsize=8.5)
    d.text(48, -0.31, "thinner", color=MUTED, fontsize=8.5, va="top")
    d.set(xlim=(0, 100), ylim=(-0.4, 0.4), xlabel="from the leading edge [mm]", ylabel="mm",
          title="Half-thickness minus NACA 0007's")
    n = fig.add_subplot(gs[2, 1])
    for k in order:
        u = secs[k].surface("upper", 4000) * C
        for sgn in (1, -1):
            n.plot(u[:, 0], sgn * u[:, 1], color=CUSTOM_COLOURS[k], lw=lw[k], ls=ls[k])
    n.set_aspect("equal")
    n.set(xlim=(-0.3, 3.2), ylim=(-1.75, 1.75), xlabel="mm",
          title=f"Nose at true scale: radius\n{p1['r_le'] * C:.2f} mm (HT35), {p0['r_le'] * C:.2f} mm (NACA)")
    return _save(fig, out)


def custom_screen(data: Path, out: Path) -> Path:
    """The steady CFD screen: nine sections at 100 mm against NACA 0007, mean race-time gain over the three
    speeds and three loads, Tu 0.1 %."""
    rk = custom_rank(data, candidates=None, steady_only=True)
    m = rk.pivot_table(index="candidate", columns="slope", values="vs_base", aggfunc="mean")
    m = -m.sort_values(1.0, ascending=False)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    y = np.arange(len(m))
    colours = [CUSTOM_COLOURS.get(c, "#b3a27f") for c in m.index]
    ax.barh(y, m[1.0], color=colours, height=0.6)
    ax.scatter(m[2.0], y, marker="|", s=200, color=INK, lw=2, zorder=3, label="resistance slope doubled")
    for yi, (c, v1, v2) in enumerate(zip(m.index, m[1.0], m[2.0])):
        text = "reference" if c == BASE else f"{v1:+.2f}"
        ax.text(max(v1, v2, 0) + 0.04 if v1 >= 0 else min(v1, v2) - 0.04, yi, text, va="center",
                ha="left" if v1 >= 0 else "right", fontsize=8.5)
    ax.axvline(0, color=INK, lw=0.9)
    names = {**CUSTOM_NAMES, "file:ht35-t070.dat/100": "HT35 at 7 % (less stiff)"}
    ax.set_yticks(y, [names.get(c, c) for c in m.index])
    ax.set(xlim=(-1.9, 1.25), xlabel="race time gained against NACA 0007 [%]   (← slower · faster →)",
           title="Steady screen at Tu 0.1 %: mean of three speeds and three loads")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


def custom_gain(data: Path, out: Path) -> Path:
    """HT35 and cst-opt2 against NACA 0007: race time gained by boat speed (Tu 0.1 %, time-accurate where
    the flow sheds) and by the water's turbulence (Tu 1 and 2 %: steady)."""
    rk = {tu: custom_rank(data, tu) for tu in (0.1, 1.0, 2.0)}
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.7), sharey=True, gridspec_kw={"width_ratios": [1.35, 1]})
    w = 0.34
    for i, cand in enumerate((HT35, OPT2)):
        r = rk[0.1][rk[0.1].candidate == cand]
        by = -r.pivot_table(index="speed", columns="slope", values="vs_base", aggfunc="mean")
        vals = [by.loc[v] for v in CUSTOM_SPEEDS] + [by.mean()]
        xs = np.arange(4) + (i - 0.5) * w
        a.bar(xs, [v[1.0] for v in vals], width=w * 0.9, color=CUSTOM_COLOURS[cand], label=CUSTOM_NAMES[cand])
        a.scatter(xs, [v[2.0] for v in vals], marker="_", s=110, color=INK, lw=2, zorder=3)
        tus = []
        for tu in (0.1, 1.0, 2.0):
            g = rk[tu][rk[tu].candidate == cand]
            tus.append(-g.groupby("slope").vs_base.mean())
        xs = np.arange(3) + (i - 0.5) * w
        b.bar(xs, [t[1.0] for t in tus], width=w * 0.9, color=CUSTOM_COLOURS[cand])
        b.scatter(xs, [t[2.0] for t in tus], marker="_", s=110, color=INK, lw=2, zorder=3)
        for xi, t in zip(xs, tus):
            b.text(xi, max(t[1.0], 0) + 0.03, f"{t[1.0]:.2f}", ha="center", fontsize=7.8)
    a.scatter([], [], marker="_", s=110, color=INK, lw=2, label="resistance slope doubled")
    a.set_xticks(range(4), [f"{v:g} m/s\n({WIND[v]})" for v in CUSTOM_SPEEDS] + ["mean"])
    a.set(ylabel="race time gained against\nNACA 0007 [%]", title="By boat speed (calm water, Tu 0.1 %)")
    b.set_xticks(range(3), ["Tu 0.1 %\n(calm)", "Tu 1 %", "Tu 2 %\n(rough)"])
    b.set(title="By the water's turbulence (mean)")
    sec = b.secondary_yaxis("right", functions=(lambda v: v * BOAT_LENGTHS_PER_PCT, lambda v: v / BOAT_LENGTHS_PER_PCT))
    sec.set_ylabel("boat lengths per race (estimate)")
    for ax in (a, b):
        ax.axhline(0, color=INK, lw=0.9)
        ax.grid(axis="x", visible=False)
    a.set_ylim(-0.1, 1.0)
    a.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


def custom_breakdown(data: Path, out: Path) -> Path:
    """Where HT35's gain comes from, per boat speed: less drag upwind, less leeway, less drag downwind."""
    p = custom_parts(data)
    p = p[p.candidate == HT35]
    parts = [("upwind drag", ACCENT, "less drag upwind, at the same side force"),
             ("leeway", "#e09a4f", "less leeway (angle) for that side force"),
             ("downwind drag", "#2f5d50", "less drag downwind, at 0°")]
    by = p.groupby("speed")[[k for k, *_ in parts]].mean()
    by.loc["all"] = p[[k for k, *_ in parts]].mean()
    fig, ax = plt.subplots(figsize=(8.6, 3.3))
    y = np.arange(len(by))[::-1]
    left = np.zeros(len(by))
    for key, colour, text in parts:
        ax.barh(y, by[key], left=left, color=colour, height=0.58, label=text)
        for yi, l0, v in zip(y, left, by[key]):
            if v > 0.07:
                ax.text(l0 + v / 2, yi, f"{v:.2f}", ha="center", va="center", fontsize=8, color=PAPER)
        left += by[key].to_numpy()
    for yi, v in zip(y, left):
        ax.text(v + 0.02, yi, f"{v:.2f} %", va="center", fontsize=8.5, weight="bold")
    ax.set_yticks(y, [f"{v:g} m/s ({WIND[v]})" if v != "all" else "all three" for v in by.index])
    ax.set(xlim=(0, 1.05), xlabel="race time gained against NACA 0007 [%] (estimated resistance slope)",
           title="HT35 at 7.25 %: where the gain comes from (mean of three loads, Tu 0.1 %)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), ncols=3, fontsize=7.8)
    fig.tight_layout()
    return _save(fig, out)


def custom_upwind(data: Path, out: Path) -> Path:
    """Upwind, at equal side force: each section's drag and angle against NACA 0007's, per boat speed,
    linear between the computed angles along the pre-stall branch (as the ranking interpolates)."""
    from iomcfd import racetime, sectiondesign as sd

    f = racetime.fin_forces(custom_polars(data))
    loads = sd.design_loads()
    fig, axs = plt.subplots(2, 3, figsize=(10, 5.4), sharey="row")

    def branch(cand, v):
        g = f[(f.candidate == cand) & np.isclose(f.speed, v) & (f.aoa >= 0)]
        i = racetime.prestall_branch(g.aoa.to_numpy(), g.side_force.to_numpy())
        return g.side_force.to_numpy()[i], g.drag.to_numpy()[i], g.aoa.to_numpy()[i]

    for j, v in enumerate(CUSTOM_SPEEDS):
        s0, d0, a0 = branch(BASE, v)
        for cand in (OPT2, HT35):
            s, d, al = branch(cand, v)
            grid = np.linspace(max(s0[0], s[0]), min(s0[-1], s[-1]), 400)
            st = dict(color=CUSTOM_COLOURS[cand], lw=1.9 if cand == HT35 else 1.2,
                      ls="-" if cand == HT35 else (0, (4, 2)), label=CUSTOM_NAMES[cand])
            axs[0, j].plot(grid, 100 * (np.interp(grid, s, d) / np.interp(grid, s0, d0) - 1), **st)
            axs[1, j].plot(grid, np.interp(grid, s, al) - np.interp(grid, s0, a0), **st)
        for ax in axs[:, j]:
            ax.axhline(0, color=CUSTOM_COLOURS[BASE], lw=1)
            for _, ld in loads[np.isclose(loads.speed, v)].iterrows():
                ax.axvline(ld.force, color=MUTED, lw=0.8, ls=":")
        for _, ld in loads[np.isclose(loads.speed, v)].iterrows():
            axs[0, j].text(ld.force, 1.0, {"light": "low", "working": "working", "high": "high"}[ld.load],
                           transform=axs[0, j].get_xaxis_transform(), rotation=90, ha="right", va="top",
                           fontsize=7.5, color=MUTED)
        axs[0, j].set_title(f"{v:g} m/s ({WIND[v]})")
        axs[1, j].set_xlabel("side force $S_h$ [N]")
    axs[0, 0].set(ylabel="drag $D_h$ against\nNACA 0007's [%]", ylim=(-13, 8))
    axs[1, 0].set(ylabel="angle α against\nNACA 0007's [°]", ylim=(-0.9, 0.4))
    axs[1, 0].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


def _surface_forces():
    """foil2d's surface_forces (projects/foil2d/project.py): each surface point's share of Cd and Cl."""
    from iomcfd.project import load_project

    return type(load_project("foil2d")).extract.__globals__["surface_forces"]


def custom_friction(data: Path, out: Path) -> Path:
    """Downwind (0 deg, 1 m/s, Tu 0.1 %, steady): pressure and skin friction along the surface, and the
    friction drag gathered from the leading edge, NACA 0007 against HT35 at 7.25 %."""
    s = pd.read_csv(data / "custom-surface-0deg.csv")
    forces = _surface_forces()
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.3))
    for key, tag in ((BASE, "naca0007"), (HT35, "ht35")):
        g = s[s.file.str.contains(tag)]
        up = g[(g.upper.astype(str) == "True") & (g.x_c < 0.995)].sort_values("x_c")  # without the TE corner
        st = dict(color=CUSTOM_COLOURS[key], lw=1.6, label=CUSTOM_NAMES[key])
        axs[0].plot(up.x_c, -up.Cp, **st)
        axs[1].plot(up.x_c, up.Cf, **st)
        sf = forces(g, 0.0).sort_values("x_c", kind="stable")
        cum = sf.d_friction.cumsum().to_numpy()
        axs[2].plot(sf.x_c, cum, **st)
        axs[2].text(1.01, cum[-1], f"{cum[-1]:.4f}", color=CUSTOM_COLOURS[key], fontsize=8, va="center")
    axs[1].axhline(0, color=INK, lw=0.8)
    axs[0].set(title="Pressure: −C$_p$", xlabel="x / c", ylabel="−C$_p$", xlim=(0, 1), ylim=(-0.15, 0.3))
    axs[1].set(title="Skin friction C$_f$", xlabel="x / c", xlim=(0, 1), ylim=(-0.002, 0.012))
    axs[2].set(title="Friction drag from the nose to x/c", xlabel="x / c", ylabel="C$_d$ (both sides)",
               xlim=(0, 1.0))
    axs[1].text(0.97, -0.0016, "C$_f$ < 0: reversed flow", ha="right", fontsize=7.5, color=MUTED)
    axs[0].legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return _save(fig, out)


def custom_gain_table(data: Path, out: Path) -> Path:
    """Race time gained against NACA 0007 (positive = faster), x1 / x2, by speed (Tu 0.1 %), the least
    favourable of the nine speed-load points, and at Tu 1 and 2 %."""
    rk = {tu: custom_rank(data, tu) for tu in (0.1, 1.0, 2.0)}

    def cell(s):
        return f"{-s[1.0]:.2f} / {-s[2.0]:.2f}"

    rows = ["| section | 0.75 m/s | 1 m/s | 1.5 m/s | mean | least favourable point | Tu 1 % | Tu 2 % |",
            "|---|---|---|---|---|---|---|---|"]
    for cand in (HT35, OPT2):
        r = rk[0.1][rk[0.1].candidate == cand]
        by = r.pivot_table(index="speed", columns="slope", values="vs_base", aggfunc="mean")
        worst = r[r.slope == 1.0].vs_base.max()
        cells = [cell(by.loc[v]) for v in CUSTOM_SPEEDS] + [f"**{cell(by.mean())}**", f"{-worst:.2f}"]
        cells += [cell(rk[tu][rk[tu].candidate == cand].groupby("slope").vs_base.mean()) for tu in (1.0, 2.0)]
        rows.append(f"| {CUSTOM_NAMES[cand]} | " + " | ".join(cells) + " |")
    out.write_text("\n".join(rows) + "\n")
    return out


def custom_properties_table(out: Path) -> Path:
    """Thickness, crest, nose radius, trailing-edge angle and bending stiffness at 100 mm."""
    from iomcfd import sectiondesign as sd

    p = {k: sd.properties(sd.load(s)) for k, s in CUSTOM_SPECS.items()}
    rows = ["| section | thickness | thickest at | nose radius | trailing-edge angle | bending stiffness |",
            "|---|--:|--:|--:|--:|--:|"]
    for k in (BASE, HT35, OPT2):
        q = p[k]
        stiff = "reference" if k == BASE else \
            f"{q['i_solid'] / p[BASE]['i_solid']:.2f} solid, {q['i_skin'] / p[BASE]['i_skin']:.2f} skin"
        rows.append(f"| {CUSTOM_NAMES[k]} | {100 * q['t']:.2f} mm | {100 * q['x_t']:.0f} mm | "
                    f"{100 * q['r_le']:.2f} mm | {q['te_angle']:.1f}° | {stiff} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def custom_card(out: Path) -> Path:
    """The page's card at 3:1: HT35 at 7.25 % over NACA 0007, the thickness stretched three times."""
    from iomcfd import sectiondesign as sd

    fig = plt.figure(figsize=(9, 3))
    a = fig.add_axes([0, 0, 1, 1])
    for k, fill in ((HT35, True), (BASE, False)):
        u = sd.load(CUSTOM_SPECS[k]).surface("upper", 800)
        xs, ys = np.r_[u[:, 0], u[::-1, 0]], 3 * np.r_[u[:, 1], -u[::-1, 1]]
        if fill:
            a.fill(xs, ys, color=ACCENT, alpha=0.85, lw=0)
        else:
            a.plot(xs, ys, color=INK, lw=1.6, ls=(0, (5, 3)))
    a.set_aspect("equal")
    a.set(xlim=(-0.08, 1.08), ylim=(-0.193, 0.193))  # 1.16 x 0.387: 3:1
    a.axis("off")
    fig.savefig(out, dpi=120, facecolor=PAPER)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# The steps and films page (site/steps-and-films/index.qmd). Data: steps-*.csv. The race time is the fin
# section page's (sectiondesign.cfd_table and rank), against plain NACA 0007/100 of the same run, or against
# a modification's own plain section; the shapes come from the project's geometry code (geometry/stepped.py),
# as the CFD meshed them. Its charts are narrow (STEPS_W) with large type, panels stacked rather than side by
# side, so they stay legible on a phone; the page shows them at most 560 px wide (styles.scss .steps-fig).

S_BASE, S_FILM = "naca0007/100", "film:naca0007:x=0.5,t=0.002/100"
S_TRIP, S_FAIR = "stair1:naca0007:x=0.5,h=0.002/100", "faired:naca0007:x=0.5,h=0.002,l=0.1/100"
S_HT, S_HTFILM = "file:ht35-t070.dat/100", "film:file:ht35-t070.dat:x=0.5,t=0.002/100"
STEPS_NAMES = {S_BASE: "NACA 0007", S_FILM: "NACA 0007 + film", S_TRIP: "NACA 0007, trip step",
               S_FAIR: "NACA 0007, sanded step", S_HT: "HT35 at 7 %", S_HTFILM: "HT35 at 7 % + film"}
STEPS_COLOURS = {S_BASE: "#3c4a57", S_FILM: "#e09a4f", S_TRIP: "#2f5d50", S_FAIR: "#7fae94", S_HT: ACCENT,
                 S_HTFILM: "#5c4d7d"}
STEPS_STYLES = {S_BASE: "-", S_FILM: "-", S_TRIP: "-", S_FAIR: (0, (5, 2)), S_HT: "-", S_HTFILM: (0, (5, 2))}
STEPS_MARKERS = {S_HT: "o", S_TRIP: "^", S_HTFILM: "D", S_FAIR: "s", S_FILM: "v"}
STEPS_ORDER = (S_HT, S_TRIP, S_HTFILM, S_FAIR, S_FILM)  # by the gain at Tu 1 %
OWN_BASE = {S_HTFILM: S_HT, S_FILM: S_BASE, S_TRIP: S_BASE, S_FAIR: S_BASE}
MOD_NAMES = {S_HTFILM: "film on HT35 at 7 %", S_FILM: "film on NACA 0007", S_TRIP: "trip step",
             S_FAIR: "sanded step"}
KFM4, TRIP_SPEC = "stair1:naca0007:d=0.5", "stair1:naca0007:x=0.5,h=0.002"
STAIRS = {KFM4: "KFm4: one 1.54 mm step", "stair5:naca0007:h=0.002": "five 0.2 mm steps",
          "stair10:naca0007:h=0.001": "ten 0.1 mm steps"}
STAIR_COLOURS = {"naca0007": "#3c4a57", KFM4: ACCENT, "stair5:naca0007:h=0.002": "#e09a4f",
                 "stair10:naca0007:h=0.001": "#5c4d7d", TRIP_SPEC: "#2f5d50"}
STEPS_FILES = ("steps-naca-film", "steps-naca-trip", "steps-naca-faired", "steps-ht35-film")
STEPS_TUS = (0.1, 1.0, 2.0)
STEPS_W = 5.6  # inches wide
STEPS_RC = {"font.size": 11, "axes.titlesize": 11.5, "axes.labelsize": 11, "xtick.labelsize": 10.5,
            "ytick.labelsize": 10.5, "legend.fontsize": 10}


def _steps_foil(spec: str):
    """A section as the CFD meshed it ('naca0007', 'film:...', 'stair1:...', 'file:...'; no '/100')."""
    from iomcfd import config
    from iomcfd.geometry import foils

    return foils.load(spec.removesuffix("/100"), [config.geometry_dir() / "foils"])


def _steps_cfd(data: Path) -> pd.DataFrame:
    """The steady polars of the six sections at Tu 0.1, 1 and 2 % (sectiondesign.cfd_table, one Tu at a time:
    without `tu` it averages over Tu)."""
    from iomcfd import sectiondesign as sd

    files = [data / f"{n}.csv" for n in STEPS_FILES]
    return pd.concat([sd.cfd_table(files, tu=tu, speeds=list(CUSTOM_SPEEDS)).assign(Tu=tu) for tu in STEPS_TUS],
                     ignore_index=True)


def steps_rank(data: Path, time_accurate_4deg: bool = False, base: str = S_BASE) -> pd.DataFrame:
    """sectiondesign.rank of the six sections against `base` at Tu 0.1, 1 and 2 %, steady. With
    `time_accurate_4deg`, NACA 0007's and the trip's 4 deg points at 1 m/s and Tu 1 % are the time-accurate
    ones of stepped-vs-baseline (the steady solver is up to 2.6 % off there); every other point stays steady."""
    from iomcfd import sectiondesign as sd

    t = _steps_cfd(data)
    if time_accurate_4deg:
        s = pd.read_csv(data / "steps-stepped.csv")
        s = s[(s.solver == "transient") & (s.aoa == 4)].set_index("foil")
        for cand in (S_BASE, S_TRIP):
            m = (t.candidate == cand) & (t.Tu == 1.0) & (t.speed == 1.0) & (t.aoa == 4)
            t.loc[m, ["Cl", "Cd"]] = s.loc[cand.removesuffix("/100"), ["Cl", "Cd"]].to_numpy(float)
    return sd.rank(t, base)


def _pair(g: pd.Series) -> str:
    """'x1 / x2' race-time gain (positive = faster) from the mean vs_base per slope factor."""
    return f"{-g[1.0]:+.2f} / {-g[2.0]:+.2f}"


@plt.rc_context(STEPS_RC)
def steps_sections(out: Path) -> Path:
    """The two plain sections at true scale, and every 0.2 mm modification as its upper surface minus its own
    plain section's, along the chord."""
    C = 100.0
    f = {k: _steps_foil(k) for k in STEPS_NAMES}
    fig, (a, b) = plt.subplots(2, 1, figsize=(STEPS_W, 5.4), height_ratios=[0.8, 2.4], gridspec_kw={"hspace": 0.55})
    up = f[S_BASE].surface("upper", 800) * C
    a.fill(np.r_[up[:, 0], up[::-1, 0]], np.r_[up[:, 1], -up[::-1, 1]], color="#d9d3c4", lw=0)
    u = f[S_HT].surface("upper", 800) * C
    a.plot(np.r_[u[:, 0], u[::-1, 0]], np.r_[u[:, 1], -u[::-1, 1]], color=ACCENT, lw=1.2, ls=(0, (4, 2)))
    a.axvline(50, color=INK, lw=0.9, ls=":")
    a.set_aspect("equal")
    a.set(xlim=(-1, 101), ylim=(-4.5, 4.5), yticks=[], xticks=[0, 25, 50, 75, 100])
    a.set_title("True scale: plain NACA 0007 (filled) and plain\nHT35 at 7 % (dashed); 50 mm dotted")
    a.grid(False)
    a.spines["left"].set_visible(False)

    def minus(k, ref):
        p, r = f[k].surface("upper", 6000) * C, f[ref].surface("upper", 6000) * C
        p = p[p[:, 0] >= 2.5]
        return p[:, 0], p[:, 1] - np.interp(p[:, 0], r[:, 0], r[:, 1])

    for k in (S_FILM, S_HTFILM, S_TRIP, S_FAIR):
        b.plot(*minus(k, OWN_BASE[k]), color=STEPS_COLOURS[k], lw=2.4 if k == S_FAIR else 2.0, ls=STEPS_STYLES[k],
               zorder=4 if k == S_FAIR else 3)
    b.axhline(0, color=STEPS_COLOURS[S_BASE], lw=1)
    b.text(99, 0.02, "plain section", ha="right", va="bottom", fontsize=10, color=STEPS_COLOURS[S_BASE])
    b.text(2, 0.23, "film: +0.2 mm from the nose\nto 50 mm (NACA 0007 solid,\nHT35 dashed)", va="bottom",
           fontsize=10, color=STEPS_COLOURS[S_FILM])
    b.text(52, -0.24, "trip step: 0.2 mm cut at 50 mm; behind it\nthe section is 6.5 % thinner, so the\n"
           "difference tapers to the tail", va="top", fontsize=10, color=STEPS_COLOURS[S_TRIP])
    b.text(52, 0.2, "sanded step (dashed): the same\nthinner rear, ramped in over 50-60 mm", va="bottom",
           fontsize=10, color="#4f8a6c")
    b.set(xlim=(0, 100), ylim=(-0.55, 0.55), xlabel="distance from the leading edge [mm]", ylabel="[mm]",
          title="Upper surface minus its plain section's\n(the lower surface is the same)")
    return _save(fig, out)


@plt.rc_context(STEPS_RC)
def steps_section_details(out: Path) -> Path:
    """Close-ups of the 0.2 mm modifications at half chord (vertical scale x5) over the plain outline, with a
    0.2 mm dimension, and the filmed noses at true scale."""
    C = 100.0
    f = {k: _steps_foil(k) for k in STEPS_NAMES}
    fig = plt.figure(figsize=(STEPS_W, 8.6))
    gs = fig.add_gridspec(4, 2, height_ratios=[1, 1, 1, 1.5], hspace=0.95, wspace=0.3)

    def upper(k, x0=40.0, x1=70.0):
        p = f[k].surface("upper", 12000) * C
        return p[(p[:, 0] > x0) & (p[:, 0] < x1)]

    details = [(S_FILM, "Film: 0.2 mm on top, ending in a square edge\nat 50 mm", 46.0),
               (S_TRIP, "Trip step: cut 0.2 mm deep at 50 mm", 51.0),
               (S_FAIR, "Sanded step: the same thinner rear, ramped\nin over 50-60 mm, no step", 60.5)]
    for i, (k, title, xa) in enumerate(details):
        ax = fig.add_subplot(gs[i, :])
        p0, p = upper(S_BASE), upper(k)
        ax.plot(p0[:, 0], p0[:, 1], color=MUTED, lw=1.4, ls=(0, (4, 2)))
        ax.plot(p[:, 0], p[:, 1], color=STEPS_COLOURS[k], lw=2.4)
        y0, y1 = np.interp(xa, p0[:, 0], p0[:, 1]), np.interp(xa, p[:, 0], p[:, 1])
        ax.annotate("", xy=(xa, y1), xytext=(xa, y0), arrowprops=dict(arrowstyle="<->", color=INK, lw=1.2,
                                                                         shrinkA=0, shrinkB=0))
        _note(ax, f"{abs(y1 - y0):.2f} mm", (xa, 0.5 * (y0 + y1)), (xa + 2.5, max(y0, y1) + 0.55))
        ax.text(40.5, 2.0, "dashed: plain", fontsize=10, color=MUTED)
        ax.set_aspect(4)
        ax.set(xlim=(40, 70), ylim=(1.9, 4.1), yticks=[2, 3, 4],
               xlabel="from the leading edge [mm]" if i == 2 else None, ylabel="[mm]")
        ax.set_title(title + (" (vertical scale ×4)" if i == 0 else ""))
    for j, (base, film, name) in enumerate(((S_BASE, S_FILM, "NACA 0007"), (S_HT, S_HTFILM, "HT35 at 7 %"))):
        n = fig.add_subplot(gs[3, j])
        for k, colour, ls, lw in ((base, MUTED, (0, (4, 2)), 1.4), (film, STEPS_COLOURS[film], "-", 2.0)):
            p = f[k].surface("upper", 6000) * C
            for sgn in (1, -1):
                n.plot(p[:, 0], sgn * p[:, 1], color=colour, lw=lw, ls=ls)
        n.annotate("", xy=(-0.2, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="<->", color=INK, lw=1.0,
                                                                      shrinkA=0, shrinkB=0))
        n.text(0.15, 0.12, "0.2 mm", fontsize=9.5)
        n.set_aspect("equal")
        n.set(xlim=(-0.5, 3.0), ylim=(-1.75, 1.75), xlabel="[mm]", xticks=[0, 1, 2, 3])
        n.set_title(f"{name} nose,\ntrue scale", fontsize=10.5)
    return _save(fig, out)


@plt.rc_context(STEPS_RC)
def steps_stairs(out: Path) -> Path:
    """NACA 0007 and the three Kline-Fogleman stairs cut from it: at true scale, and the half-thickness
    stretched."""
    C = 100.0
    specs = ["naca0007", *STAIRS]
    names = {"naca0007": "NACA 0007 (plain)", **STAIRS}
    fig = plt.figure(figsize=(STEPS_W, 7.6))
    gs = fig.add_gridspec(6, 1, height_ratios=[0.5, 0.5, 0.5, 0.5, 0.35, 2.6], hspace=0.75)
    for i, spec in enumerate(specs):
        a = fig.add_subplot(gs[i])
        g = _steps_foil(spec)
        u, lo = g.surface("upper", 1500) * C, g.surface("lower", 1500) * C
        a.fill(np.r_[u[:, 0], lo[::-1, 0]], np.r_[u[:, 1], lo[::-1, 1]], color=STAIR_COLOURS[spec], lw=0, alpha=0.9)
        a.set_aspect("equal")
        a.set(xlim=(-1, 101), ylim=(-4.2, 4.2), yticks=[], xticks=[])
        a.set_title(names[spec] + (": true scale, 100 mm chord" if i == 0 else ""), fontsize=10.5)
        a.grid(False)
        for sp in a.spines.values():
            sp.set_visible(False)
    b = fig.add_subplot(gs[5])  # gs[4]: room for its title
    for spec in specs:
        u = _steps_foil(spec).surface("upper", 3000) * C
        b.plot(u[:, 0], u[:, 1], color=STAIR_COLOURS[spec], lw=1.6 if spec != "naca0007" else 2.4,
               label=names[spec], zorder=3 if spec != "naca0007" else 2)
    b.set(xlim=(0, 100), ylim=(0, 3.9), xlabel="from the leading edge [mm]", ylabel="half-thickness [mm]",
          title="Half the section, thickness stretched ×7: each\nstair takes away about half the thickness near\n"
                "the tail, in one step or in many")
    b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncols=2)
    return _save(fig, out)


def steps_sections_table(out: Path) -> Path:
    """The sections at 100 mm: what was changed, thickness, nose radius and the thickness near the tail."""
    from iomcfd import sectiondesign as sd

    r_naca = sd.properties(sd.load("naca0007"))["r_le"]
    r_ht = sd.properties(sd.load("file:ht35.dat@0.07"))["r_le"]  # the UIUC coordinates: an exact nose radius
    rows = [("NACA 0007", "naca0007", "-", r_naca),
            ("NACA 0007 + film", S_FILM, "0.2 mm film per side, from 50 mm on one side round the nose to 50 mm "
             "on the other", r_naca + 0.002),
            ("NACA 0007, trip step", S_TRIP, "a 0.2 mm step cut at 50 mm; behind it 6.5 % thinner", r_naca),
            ("NACA 0007, sanded step", S_FAIR, "the trip's thinner rear, ramped in over 50-60 mm: no step", r_naca),
            ("HT35 at 7 %", S_HT, "-", r_ht),
            ("HT35 at 7 % + film", S_HTFILM, "0.2 mm film as on NACA 0007", r_ht + 0.002),
            ("KFm4 stair", KFM4, "one 1.54 mm step at 50 mm: half the local thickness", r_naca),
            ("five steps", "stair5:naca0007:h=0.002", "0.2 mm steps at 30, 45, 60, 75 and 90 mm", r_naca),
            ("ten steps", "stair10:naca0007:h=0.001", "0.1 mm steps every 6.7 mm from 30 to 90 mm", r_naca)]
    lines = ["| section | what was changed | thickest | at 80 mm | nose radius |", "|---|---|--:|--:|--:|"]
    for name, spec, what, r in rows:
        g = _steps_foil(spec)
        up, lo = (q[q[:, 0] > 0.77] for q in (g.surface("upper", 4000), g.surface("lower", 4000)))  # past every step
        at80 = 100 * (np.interp(0.8, up[:, 0], up[:, 1]) - np.interp(0.8, lo[:, 0], lo[:, 1]))
        lines.append(f"| {name} | {what} | {100 * g.thickness()[0]:.2f} mm | {at80:.2f} mm | {100 * r:.2f} mm |")
    out.write_text("\n".join(lines) + "\n")
    return out


@plt.rc_context(STEPS_RC)
def steps_gain(data: Path, out: Path) -> Path:
    """Race time gained against plain NACA 0007/100, steady, one panel per Tu: a filled marker per section with
    the estimated resistance slope, a hollow diamond with it doubled; the trip step with its and NACA 0007's
    4 deg, 1 m/s points time-accurate at Tu 1 %."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    m = -steps_rank(data).pivot_table(index="candidate", columns=["Tu", "slope"], values="vs_base", aggfunc="mean")
    rt = steps_rank(data, time_accurate_4deg=True)
    ta = -rt[(rt.candidate == S_TRIP) & (rt.Tu == 1.0) & (rt.slope == 1.0)].vs_base.mean()
    fig, axs = plt.subplots(3, 1, figsize=(STEPS_W - 1.4, 7.8), sharex=True)  # the names take the rest
    y = np.arange(len(STEPS_ORDER))[::-1]
    titles = {0.1: "Tu 0.1 %: steady answers too noisy to rank", 1.0: "Tu 1 %", 2.0: "Tu 2 %"}
    for ax, tu in zip(axs, STEPS_TUS):
        noisy = tu == 0.1
        ax.axvspan(-0.1, 0.1, color=RULE, alpha=0.7, lw=0)
        if noisy:
            ax.axvspan(-0.9, 0.85, facecolor="none", edgecolor=RULE, hatch="///", lw=0)
        ax.axvline(0, color=INK, lw=1.0)
        for yi, cand in zip(y, STEPS_ORDER):
            v1, v2 = m.loc[cand, (tu, 1.0)], m.loc[cand, (tu, 2.0)]
            c = STEPS_COLOURS[cand]
            ax.plot([v1, v2], [yi, yi], color=c, lw=1.2, alpha=0.6)
            ax.scatter([v2], [yi], s=46, marker="D", facecolor=PAPER, edgecolor=c, lw=1.4, zorder=3)
            ax.scatter([v1], [yi], s=70, marker=STEPS_MARKERS[cand], color=c, alpha=0.55 if noisy else 1, zorder=4)
            right = max(v1, v2) > 0
            ax.text(max(v1, v2) + 0.05 if right else min(v1, v2) - 0.05, yi, f"{v1:+.2f}".replace("-", "−"),
                    va="center", ha="left" if right else "right", fontsize=10, color=MUTED if noisy else INK)
        if tu == 1.0:
            ax.scatter([ta], [y[STEPS_ORDER.index(S_TRIP)]], s=150, marker="o", facecolor="none", edgecolor=INK,
                       lw=1.3, zorder=5)
        ax.set_yticks(y, [STEPS_NAMES[c] for c in STEPS_ORDER])
        ax.set(xlim=(-0.9, 0.85), ylim=(-0.7, len(STEPS_ORDER) - 0.3), xticks=[-0.5, -0.25, 0, 0.25, 0.5, 0.75])
        ax.set_xticklabels(["−0.5", "", "0", "", "0.5", ""])
        ax.set_title(titles[tu])
        ax.grid(axis="y", visible=False)
    axs[-1].set_xlabel("race-time gain against plain NACA 0007 [%]\n(+ = faster, mean of 3 speeds x 3 loads)")
    handles = [Line2D([], [], marker="o", ls="", color=INK, label="estimated resistance slope"),
               Line2D([], [], marker="D", ls="", markerfacecolor=PAPER, markeredgecolor=INK,
                      label="slope doubled (a sensitivity,\nnot a confidence range)"),
               Patch(color=RULE, label="within 0.1 % of plain\nNACA 0007: not resolved"),
               Line2D([], [], marker="o", ls="", markersize=11, markerfacecolor="none", markeredgecolor=INK,
                      label=f"Tu 1 %: the trip step ({ta:+.2f}) with its and NACA\n0007's 4°, 1 m/s points "
                            "time-accurate")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.0), fontsize=9.5)
    fig.tight_layout()
    return _save(fig, out)


def steps_gain_table(data: Path, out: Path) -> Path:
    """Race time gained against NACA 0007/100 (positive = faster), x1 / x2 per Tu, how many of the nine
    speed-load points are faster at Tu 1 and 2 %, and the trip step with its time-accurate 4 deg points."""
    rk = steps_rank(data)
    rows = ["| section | Tu 0.1 % | Tu 1 % | Tu 2 % | faster at, Tu 1 % | faster at, Tu 2 % |",
            "|---|---|---|---|---|---|"]

    def faster(r, tu):
        g = r[(r.Tu == tu) & (r.slope == 1.0)]
        return f"{int((g.vs_base < 0).sum())} of {len(g)}"

    for cand in STEPS_ORDER:
        r = rk[rk.candidate == cand]
        cells = [_pair(r[r.Tu == tu].groupby("slope").vs_base.mean()) for tu in STEPS_TUS]
        rows.append(f"| {STEPS_NAMES[cand]} | " + " | ".join(cells + [faster(r, 1.0), faster(r, 2.0)]) + " |")
    rt = steps_rank(data, time_accurate_4deg=True)
    r = rt[rt.candidate == S_TRIP]
    rows.append(f"| {STEPS_NAMES[S_TRIP]}, 4° at 1 m/s time-accurate (and NACA 0007's) | - | "
                f"{_pair(r[r.Tu == 1.0].groupby('slope').vs_base.mean())} | - | {faster(r, 1.0)} | - |")
    out.write_text("\n".join(rows) + "\n")
    return out


def steps_own_base_table(data: Path, out: Path) -> Path:
    """Race time each 0.2 mm modification gains against its own plain section (positive = faster), x1 / x2
    per Tu, and at Tu 1 % the part from the upwind leg and from the downwind leg (x1)."""
    from iomcfd import sectiondesign as sd

    t = _steps_cfd(data)
    rows = ["| modification | against | Tu 0.1 % | Tu 1 % | Tu 2 % | Tu 1 %, upwind | Tu 1 %, downwind |",
            "|---|---|---|---|---|---|---|"]
    for cand, base in OWN_BASE.items():
        rk = sd.rank(t, base)
        r = rk[rk.candidate == cand]
        cells = [_pair(r[r.Tu == tu].groupby("slope").vs_base.mean()) for tu in STEPS_TUS]
        key = ["speed", "load"]
        r1 = r[(r.Tu == 1.0) & (r.slope == 1.0)].set_index(key)
        b1 = rk[(rk.candidate == base) & (rk.Tu == 1.0) & (rk.slope == 1.0)].set_index(key).loc[r1.index]
        up, down = (-0.5 * (r1[c] - b1[c]).mean() for c in ("loss_up", "loss_down"))
        cells += [f"{up:+.2f}", f"{down:+.2f}"]
        rows.append(f"| {MOD_NAMES[cand]} | plain {STEPS_NAMES[base]} | " + " | ".join(cells) + " |")
    out.write_text("\n".join(rows) + "\n")
    return out


@plt.rc_context(STEPS_RC)
def steps_4deg(data: Path, out: Path) -> Path:
    """Section drag at 4 deg, 1 m/s, Tu 1 % against plain NACA 0007 from the same solver (steady against
    steady, time-accurate against time-accurate), and plain NACA 0007's own steady-against-time-accurate
    difference: how far the solvers alone move the answer."""
    s = pd.read_csv(data / "steps-stepped.csv")
    s = s[s.aoa == 4]
    cd = {(f, sv): float(g.Cd.iloc[0]) for (f, sv), g in s.groupby(["foil", "solver"])}
    order = [KFM4, "stair5:naca0007:h=0.002", "stair10:naca0007:h=0.001", TRIP_SPEC]
    names = {**STAIRS, TRIP_SPEC: "trip step\n(0.2 mm)", KFM4: "KFm4: one\n1.54 mm step",
             "stair5:naca0007:h=0.002": "five 0.2 mm\nsteps", "stair10:naca0007:h=0.001": "ten 0.1 mm\nsteps"}
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(STEPS_W - 0.8, 5.6), height_ratios=[4, 1.1], sharex=True)
    y = np.arange(len(order))[::-1]
    for yi, foil in zip(y, order):
        for solver, dy, alpha in (("steady", 0.2, 0.45), ("transient", -0.2, 1.0)):
            if (foil, solver) not in cd:
                ax.text(0.8, yi + dy, "time-accurate: did not finish", va="center", fontsize=9.5, color=MUTED)
                continue
            v = 100 * (cd[(foil, solver)] / cd[("naca0007", solver)] - 1)
            ax.barh(yi + dy, v, height=0.36, color=STAIR_COLOURS[foil], alpha=alpha)
            note = " (6 flow-throughs)" if foil.startswith("stair5") and solver == "transient" else ""
            ax.text(max(v, 0) + 0.8, yi + dy, f"{v:+.1f} %{note}".replace("-", "−"), va="center", fontsize=10)
    ax.axvline(0, color=INK, lw=0.9)
    ax.set_yticks(y, [names[f] for f in order])
    ax.set_title("Against plain NACA 0007 from the same solver:\nsteady (pale) and time-accurate (dark)")
    ax.grid(axis="y", visible=False)
    v = 100 * (cd[("naca0007", "steady")] / cd[("naca0007", "transient")] - 1)
    bx.barh(0, v, height=0.5, color=STAIR_COLOURS["naca0007"], alpha=0.6)
    bx.text(v + 0.8, 0, f"{v:+.1f} %", va="center", fontsize=10)
    bx.axvline(0, color=INK, lw=0.9)
    bx.set_yticks([0], ["plain NACA 0007"])
    bx.set(xlim=(-9, 52), ylim=(-0.6, 0.6), xlabel="section drag difference [%]")
    bx.set_title("Steady against time-accurate, same section")
    bx.grid(axis="y", visible=False)
    fig.tight_layout()
    return _save(fig, out)


def steps_4deg_table(data: Path, out: Path) -> Path:
    """Lift and drag at 4 deg, 1 m/s, Tu 1 %, steady / time-accurate; drag against plain NACA 0007 from the
    same solver; the time-accurate lift's standard deviation over the averaging window."""
    s = pd.read_csv(data / "steps-stepped.csv")
    s = s[s.aoa == 4]
    names = {"naca0007": "NACA 0007", **STAIRS, TRIP_SPEC: "trip step (0.2 mm)"}
    ref = {sv: float(s[(s.foil == "naca0007") & (s.solver == sv)].Cd.iloc[0]) for sv in ("steady", "transient")}
    rows = ["| section | C~l~ steady / time-acc. | C~d~ steady / time-acc. | C~d~ against plain, same solver "
            "| C~l~ std, time-acc. | flow in time |", "|---|---|---|---|---|---|"]
    for foil, name in names.items():
        st = s[(s.foil == foil) & (s.solver == "steady")].iloc[0]
        tr = s[(s.foil == foil) & (s.solver == "transient")]
        tr = tr.iloc[0] if not tr.empty else None
        if foil == "naca0007":
            against = "reference"
        else:
            d = [f"{100 * (r.Cd / ref[sv] - 1):+.1f}" if r is not None else "-"
                 for r, sv in ((st, "steady"), (tr, "transient"))]
            against = f"{d[0]} / {d[1]} %"
        if tr is None:
            rows.append(f"| {name} | {st.Cl:.3f} / - | {st.Cd:.5f} / - | {against} | - | not run to the end |")
            continue
        flow = "unsteady" if str(tr.unsteady) == "True" else "steady"
        if tr.flow_times < 20:
            flow += f" ({tr.flow_times:g} flow-throughs)"
        rows.append(f"| {name} | {st.Cl:.3f} / {tr.Cl:.3f} | {st.Cd:.5f} / {tr.Cd:.5f} | {against} | "
                    f"{tr.Cl_std:.4f} | {flow} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def _steps_surface(data: Path, names: list[str]) -> pd.DataFrame:
    return pd.concat([pd.read_csv(data / f"{n}.csv") for n in names], ignore_index=True)


def _note(ax, text, xy, xytext, **kw):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=9.5, color=INK, va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8, shrinkA=2, shrinkB=1), **kw)


@plt.rc_context(STEPS_RC)
def steps_flow(data: Path, out: Path) -> Path:
    """The suction side of NACA 0007 at 1 m/s, Tu 1 %, steady: skin friction at 0 deg, pressure and skin
    friction at 2 deg; plain, with the film, the trip step and the sanded step."""
    s = _steps_surface(data, ["steps-surface-1ms", "steps-surface-1ms-trip", "steps-surface-1ms-faired"])
    tags = {S_BASE: "foilnaca0007_", S_FILM: "foilfilmnaca0007", S_TRIP: "foilstair1naca0007", S_FAIR: "foilfaired"}
    fig, axs = plt.subplots(3, 1, figsize=(STEPS_W, 9.4), sharex=True)
    panels = [(0, "Cf", "0° (the downwind leg): skin friction"), (2, "Cp", "2°: suction (−C$_p$)"),
              (2, "Cf", "2°: skin friction")]
    for ax, (aoa, var, title) in zip(axs, panels):
        for k, tag in tags.items():
            g = s[s.file.str.contains(tag) & s.file.str.contains(f"aoa{aoa}_")]
            g = g[(g.upper.astype(str) == "True") & (g.x_c < 0.995)]
            ax.plot(g.x_c, -g.Cp if var == "Cp" else g.Cf, color=STEPS_COLOURS[k], ls=STEPS_STYLES[k],
                    lw=2.8 if k == S_BASE else (2.2 if k == S_FAIR else 1.6), label=STEPS_NAMES[k],
                    zorder=2 if k == S_BASE else 3)
        if var == "Cf":
            ax.axhspan(-0.0016, 0, color=RULE, alpha=0.45, lw=0)
            ax.axhline(0, color=INK, lw=0.8)
            ax.text(0.305, -0.0013, "C$_f$ < 0: reversed flow", fontsize=9.5, color=MUTED)
            ax.set(ylim=(-0.0016, 0.0045), ylabel="C$_f$")
        else:
            ax.set(ylim=(0.0, 0.55), ylabel="−C$_p$")
        ax.set_title(title)
    _note(axs[0], "film, trip step: a short bubble\nat 50 % (50-53 %)", (0.505, -0.0004), (0.56, 0.0033))
    _note(axs[0], "sanded step: slows the flow,\nno reversal", (0.585, 0.0006), (0.66, 0.0021))
    _note(axs[1], "film, trip and sanded step: more suction\nalong the chord, so more lift at this angle\n"
          "(C$_l$ 0.19-0.21, plain 0.16)", (0.42, 0.235), (0.47, 0.43))
    _note(axs[2], "film, trip step: bubble 50-57 %", (0.53, -0.0005), (0.31, 0.0041))
    _note(axs[2], "sanded step: its own\nbubble, 57-63 %", (0.6, -0.0003), (0.6, 0.0031))
    _note(axs[2], "plain: separates at 72 %,\ndoes not reattach", (0.723, 0.0), (0.76, 0.0021))
    _note(axs[2], "all four: reversed\nflow at the tail", (0.96, -0.0009), (0.83, 0.0009))
    axs[2].set_xlabel("x / c: distance from the leading edge / chord")
    axs[2].set_xlim(0.3, 1.0)
    axs[2].legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncols=2)
    fig.tight_layout()
    return _save(fig, out)


@plt.rc_context(STEPS_RC)
def steps_flow_4deg(data: Path, out: Path) -> Path:
    """Skin friction on both surfaces at 4 deg, 1 m/s, Tu 1 %, time-accurate, the final instant: NACA 0007
    and the sections cut from it (the five 0.2 mm steps on the lower surface only)."""
    s = _steps_surface(data, ["steps-surface-4deg"])
    tags = {"naca0007": "foilnaca0007_", KFM4: "foilstair1naca0007d0.5", "stair5:naca0007:h=0.002": "foilstair5",
            TRIP_SPEC: "foilstair1naca0007x0.5"}
    names = {"naca0007": "NACA 0007 (plain)", **STAIRS, TRIP_SPEC: "trip step (0.2 mm)"}
    fig, axs = plt.subplots(2, 1, figsize=(STEPS_W, 6.9), sharex=True)
    for ax, side in zip(axs, ("upper", "lower")):
        for k, tag in tags.items():
            if side == "upper" and k == "stair5:naca0007:h=0.002":
                continue  # it sheds at every step: one instant of it hides the rest
            g = s[s.file.str.contains(tag)]
            g = g[(g.upper.astype(str) == ("True" if side == "upper" else "False")) & (g.x_c < 0.995)]
            ax.plot(g.x_c, g.Cf, color=STAIR_COLOURS[k], lw=2.8 if k == "naca0007" else 1.5, label=names[k],
                    zorder=2 if k == "naca0007" else 3)
        ax.axhspan(-0.006, 0, color=RULE, alpha=0.45, lw=0)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set(xlim=(0, 1.0), ylim=(-0.006, 0.012), ylabel="C$_f$")
        ax.set_title("Upper (suction) surface" if side == "upper" else "Lower (pressure) surface")
    axs[0].text(0.01, -0.0055, "C$_f$ < 0: reversed flow", fontsize=9.5, color=MUTED)
    _note(axs[0], "leading-edge bubble\n(every section)", (0.1, -0.0008), (0.2, 0.0085))
    _note(axs[0], "plain: the wiggles are its shedding\nvortices at this one instant", (0.66, 0.0045), (0.56, 0.0098))
    _note(axs[1], "KFm4: separates at the step,\nreattaches at 60 %", (0.55, -0.0015), (0.13, -0.0038))
    _note(axs[1], "behind it, 2.3 times the\nplain section's friction", (0.78, 0.0064), (0.66, 0.0098))
    _note(axs[1], "five steps: a small\nbubble behind each", (0.755, -0.0008), (0.62, -0.0042))
    axs[1].set_xlabel("x / c")
    axs[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncols=2)
    fig.tight_layout()
    return _save(fig, out)


@plt.rc_context(STEPS_RC)
def steps_drag_split(data: Path, out: Path) -> Path:
    """Section drag of each 0.2 mm modification against its own plain section at the same angle (1 m/s,
    Tu 1 %), split into friction and pressure drag, in % of the plain section's drag: steady at 0 and 2 deg,
    and the trip step at 4 deg time-accurate (stepped-vs-baseline)."""
    t = pd.concat([pd.read_csv(data / f"{n}.csv") for n in STEPS_FILES], ignore_index=True)
    t = t[(t.speed == 1.0) & (t.Tu == 1.0) & (t.status != "failed")]
    t = t.assign(cand=t.foil + "/100").drop_duplicates(["cand", "aoa"]).set_index(["cand", "aoa"])
    rows = []
    for aoa in (0, 2):
        for cand in (S_HTFILM, S_FILM, S_TRIP, S_FAIR):
            m, b = t.loc[(cand, aoa)], t.loc[(OWN_BASE[cand], aoa)]
            rows.append((f"{MOD_NAMES[cand]}, {aoa}°", m, b))
    st = pd.read_csv(data / "steps-stepped.csv")
    st = st[(st.aoa == 4) & (st.solver == "transient")].set_index("foil")
    rows.append(("trip step, 4°, time-accurate", st.loc[TRIP_SPEC], st.loc["naca0007"]))
    fig, ax = plt.subplots(figsize=(STEPS_W - 1.9, 6.4))  # the names take the rest
    y = np.arange(len(rows))[::-1].astype(float)
    y[:4] += 1.0  # gaps between the angles
    y[-1] -= 1.0
    for yi, (name, m, b) in zip(y, rows):
        df, dp = (100 * (m[c] - b[c]) / b.Cd for c in ("Cd_friction", "Cd_pressure"))
        ax.barh(yi + 0.18, df, height=0.34, color="#3e7cb1")
        ax.barh(yi - 0.18, dp, height=0.34, color="#e09a4f")
        ax.scatter([df + dp], [yi], marker="|", s=260, color=INK, lw=2.2, zorder=3)
        ax.text(5.2, yi, f"{df + dp:+.1f} %".replace("-", "−"), va="center", fontsize=10)
    ax.axvline(0, color=INK, lw=0.9)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set(xlim=(-5, 6.6), xlabel="change in section drag, % of the plain section's drag")
    ax.set_title("Same angle, 1 m/s, Tu 1 %: friction (blue),\npressure drag (orange) and total (black)")
    ax.grid(axis="y", visible=False)
    return _save(fig, out)


def _render(path: Path, box: tuple[int, int, int, int]) -> np.ndarray:
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGB").crop(box))


REAR = (690, 230, 1800, 520)  # the boundary_layer view (1800 x 520): x/c 0.4 to the wake, and the colour bar


@plt.rc_context(STEPS_RC)
def _render_stack(panels: list[tuple[np.ndarray, str]], out: Path, arrows: int) -> Path:
    """Renders one under another, each with a title; a flow arrow on the first `arrows`."""
    hs = [p.shape[0] / p.shape[1] for p, _ in panels]
    fig, axs = plt.subplots(len(panels), 1, figsize=(STEPS_W, STEPS_W * sum(hs) + 0.55 * len(panels)),
                            height_ratios=hs)
    for i, (ax, (img, title)) in enumerate(zip(np.atleast_1d(axs), panels)):
        ax.imshow(img, interpolation="lanczos")
        ax.set_title(title, fontsize=10.5)
        ax.axis("off")
        if i < arrows:
            ax.annotate("flow", xy=(250, 30), xytext=(40, 30), fontsize=10.5, va="center",
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6))
    fig.tight_layout(h_pad=0.6)
    return _save(fig, out)


def steps_film_flow(data: Path, out: Path) -> Path:
    """HT35 at 7 % bare and filmed at 2 deg, 1 m/s, Tu 1 % (steady, the last iteration): the rear of the same
    ParaView view with its colour bar, and the film's edge close up (its own colour scale)."""
    assets = data.parent / "assets"
    t = pd.read_csv(data / "steps-ht35-film.csv")
    t = t[(t.speed == 1.0) & (t.Tu == 1.0) & (t.aoa == 2)].set_index("foil")

    def forces(foil):
        return f"C$_l$ {t.loc[foil].Cl:.3f}, C$_d$ {t.loc[foil].Cd:.4f}"

    return _render_stack([
        (_render(assets / "steps-flow-2deg-ht35.png", REAR), f"HT35 at 7 %, bare: {forces('file:ht35-t070.dat')}"),
        (_render(assets / "steps-flow-2deg-ht35-film.png", REAR),
         f"HT35 at 7 % with the film: {forces('film:file:ht35-t070.dat:x=0.5,t=0.002')}"),
        (_render(assets / "steps-flow-2deg-ht35-film-edge.png", (0, 50, 1600, 600)),
         "The film's edge at 50 mm, close up (its own colour scale)")], out, arrows=2)


def steps_flow_pictures(data: Path, out: Path) -> Path:
    """Plain NACA 0007, the trip step and the KFm4 step at 4 deg, 1 m/s, Tu 1 %, time-accurate, the final
    instant: the rear of the same ParaView view, with its colour bar; forces are time averages."""
    assets = data.parent / "assets"
    s = pd.read_csv(data / "steps-stepped.csv")
    s = s[(s.aoa == 4) & (s.solver == "transient")].set_index("foil")
    panels = []
    for asset, foil, name in (("naca0007", "naca0007", "Plain NACA 0007"), ("trip", TRIP_SPEC, "Trip step"),
                              ("kfm4", KFM4, "KFm4 step")):
        r = s.loc[foil]
        panels.append((_render(assets / f"steps-flow-4deg-{asset}.png", REAR),
                       f"{name}: C$_l$ {r.Cl:.3f}, C$_d$ {r.Cd:.4f} (time averages)"))
    return _render_stack(panels, out, arrows=3)


def steps_card(out: Path) -> Path:
    """The page's card at 3:1: the KFm4 stair over NACA 0007, the thickness stretched three times."""
    fig = plt.figure(figsize=(9, 3))
    a = fig.add_axes([0, 0, 1, 1])
    for spec, fill in ((KFM4, True), ("naca0007", False)):
        g = _steps_foil(spec)
        u, lo = g.surface("upper", 1500), g.surface("lower", 1500)
        xs, ys = np.r_[u[:, 0], lo[::-1, 0]], 3 * np.r_[u[:, 1], lo[::-1, 1]]
        if fill:
            a.fill(xs, ys, color=ACCENT, alpha=0.85, lw=0)
        else:
            a.plot(xs, ys, color=INK, lw=1.6, ls=(0, (5, 3)))
    a.set_aspect("equal")
    a.set(xlim=(-0.08, 1.08), ylim=(-0.193, 0.193))  # 1.16 x 0.387: 3:1
    a.axis("off")
    fig.savefig(out, dpi=120, facecolor=PAPER)
    plt.close(fig)
    return out


def make_all(data: Path, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    ref = data.parents[1] / "projects" / "foil2d" / "validation" / "naca0009_re1e5_princeton.csv"
    return [
        course(out / "course.svg"),
        fin_side(out / "fin-side.svg"),
        section(out / "section.svg"),
        bubble_schematic(out / "bubble-schematic.svg"),
        mesh(out / "mesh.png"),
        validation(data, ref, out / "validation.svg"),
        equal_force(data, out / "equal-force.svg"),
        force_history(data, out / "force-history.svg"),
        steady_vs_transient(data, out / "steady-vs-transient.svg"),
        race_time(data, out / "race-time.svg"),
        race_time_by_speed(data, out / "race-time-by-speed.svg"),
        leading_edge_bubble(data, out / "leading-edge-bubble.svg"),
        race_time_table(data, out / "race-time.md"),
        race_time_by_speed_table(data, out / "race-time-by-speed.md"),
        fin_choice_table(data, out / "fin-choice.md"),
        sources_table(data, out / "sources.md", keep=lambda n: not n.startswith(("bulb-", "custom-", "steps-"))),
        card_image(data.parent / "assets" / "flow-shedding-vorticity.png", out / "fin-selection-card.png"),
        # the keel bulb page
        bulb_side(out / "bulb-side.svg"),
        bulb_sections(out / "bulb-sections.svg"),
        bulb_front(out / "bulb-front.svg"),
        bulb_righting(out / "bulb-righting.svg"),
        bulb_endplate_schematic(out / "bulb-endplate-schematic.svg"),
        bulb_family(data, out / "bulb-family.svg"),
        bulb_dress(data, data.parents[1] / "projects" / "bulb2d" / "validation" / "dress1988.csv", out / "bulb-dress.svg"),
        bulb_fineness(data, out / "bulb-fineness.svg"),
        bulb_length_mechanism(data, out / "bulb-length-mechanism.svg"),
        bulb_drag_parts(data, out / "bulb-drag-parts.svg"),
        bulb_endplate(data, out / "bulb-endplate.svg"),
        bulb_spanload(data, out / "bulb-spanload.svg"),
        bulb_section_race(data, out / "bulb-section-race.svg"),
        bulb_race_table(data, out / "bulb-race.md"),
        bulb_loads_table(data, out / "bulb-loads.md"),
        bulb_drag_split(data, out / "bulb-drag-split.svg"),
        bulb_cant_schematic(out / "bulb-cant-schematic.svg"),
        bulb_cant(data, out / "bulb-cant.svg"),
        bulb_sections_table(data, out / "bulb-sections.md"),
        sources_table(data, out / "sources-bulb.md", keep=lambda n: n.startswith("bulb-")),
        bulb_card(data, out / "bulb-design-card.png"),
        # the fin section page
        custom_shapes(out / "custom-shapes.svg"),
        custom_screen(data, out / "custom-screen.svg"),
        custom_gain(data, out / "custom-gain.svg"),
        custom_breakdown(data, out / "custom-breakdown.svg"),
        custom_upwind(data, out / "custom-upwind.svg"),
        custom_friction(data, out / "custom-friction.svg"),
        custom_gain_table(data, out / "custom-gain.md"),
        custom_properties_table(out / "custom-properties.md"),
        sources_table(data, out / "sources-custom.md", keep=lambda n: n.startswith("custom-")),
        custom_card(out / "custom-section-card.png"),
        # the steps and films page
        steps_sections(out / "steps-sections.svg"),
        steps_section_details(out / "steps-section-details.svg"),
        steps_stairs(out / "steps-stairs.svg"),
        steps_sections_table(out / "steps-sections.md"),
        steps_gain(data, out / "steps-gain.svg"),
        steps_gain_table(data, out / "steps-gain.md"),
        steps_own_base_table(data, out / "steps-own-base.md"),
        steps_4deg(data, out / "steps-4deg.svg"),
        steps_4deg_table(data, out / "steps-4deg.md"),
        steps_flow(data, out / "steps-flow.svg"),
        steps_flow_4deg(data, out / "steps-flow-4deg.svg"),
        steps_drag_split(data, out / "steps-drag-split.svg"),
        steps_film_flow(data, out / "steps-film-flow.png"),
        steps_flow_pictures(data, out / "steps-flow-pictures.png"),
        sources_table(data, out / "sources-steps.md", keep=lambda n: n.startswith("steps-")),
        steps_card(out / "steps-and-films-card.png"),
    ]
