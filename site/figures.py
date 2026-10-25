"""Charts, diagrams and generated tables for the website's study pages
(site/fin-selection/index.qmd, site/bulb-design/index.qmd), and their card
images on the front page.

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
# The Thistle centreboard page (site/thistle-board/index.qmd). Data: thistle-*.csv. The board's
# forces and the rankings come from iomcfd.boardrank on those tables, as in
# projects/foil2d/findings/thistle-board.md; the shapes from geometry/foils/. The figures are drawn
# narrow (TH_W inches, panels stacked) with large type, so they stay readable at phone width; the page
# shows them at most about 560 px wide.

TH_BASE = "file:naca0006-t0556.dat"
TH_SECTIONS = {  # spec: (name on the page, colour, marker); the CFD screen's eight, NACA 0006 first
    TH_BASE: ("NACA 0006", ACCENT, "D"),
    "file:naca63-006-t0556.dat": ("NACA 63-006", "#2f5d50", "o"),
    "file:naca64-006-t0556.dat": ("NACA 64-006", "#3f7cac", "s"),
    "file:naca0006-64-t0556.dat": ("NACA 0006-64", "#5c4d7d", "v"),
    "file:ht35-t0556.dat": ("HT35", "#e09a4f", "^"),
    "file:sd8020-t0556.dat": ("SD8020", "#b3a27f", "P"),
    "file:parallel-l30-t50-r05-a20.dat": ("parallel-sided l30-t50", "#8a8f96", "X"),
    "file:plank-typical.dat": ("plank", "#3c4a57", "h"),
}
TH_DASH = {  # line styles, so no two sections in one panel differ by colour alone
    TH_BASE: "-", "file:naca63-006-t0556.dat": (0, (6, 2)), "file:naca64-006-t0556.dat": (0, (1.5, 1.5)),
    "file:naca0006-64-t0556.dat": (0, (6, 2, 1.5, 2)), "file:ht35-t0556.dat": (0, (3, 1.5)),
    "file:sd8020-t0556.dat": (0, (8, 2, 1.5, 2, 1.5, 2)), "file:parallel-l30-t50-r05-a20.dat": (0, (6, 2)),
    "file:plank-typical.dat": (0, (1.5, 1.5)),
}
TH_FINALISTS = [TH_BASE, "file:naca63-006-t0556.dat", "file:naca64-006-t0556.dat"]
TH_TU_DASH = {0.3: "-", 0.6: (0, (5, 2.5))}
TH_LOADS = {"light": "low", "working": "working", "high": "high"}  # boardrank's load keys -> side-force loads
TH_IN = 25.4  # mm per inch
TH_W = 5.4  # figure width [in]
TH_RC = {"font.size": 12, "axes.titlesize": 12, "axes.labelsize": 11.5, "legend.fontsize": 10.5,
         "xtick.labelsize": 10.5, "ytick.labelsize": 10.5}
R824 = Path(__file__).parents[1] / "projects" / "foil2d" / "validation" / "naca6_r824.csv"


def _th_style(fn):
    """The Thistle figures' larger type."""
    import functools

    @functools.wraps(fn)
    def wrapped(*a, **k):
        with plt.rc_context(TH_RC):
            return fn(*a, **k)
    return wrapped


def _th_name(candidate: str) -> str:
    return TH_SECTIONS.get(candidate.rsplit("/", 1)[0], (candidate, None, None))[0]


def _th_colour(candidate: str) -> str:
    return TH_SECTIONS.get(candidate.rsplit("/", 1)[0], (None, "#b3a27f", None))[1]


def _th_marker(candidate: str) -> str:
    return TH_SECTIONS.get(candidate.rsplit("/", 1)[0], (None, None, "o"))[2]


def _th_bottom_legend(fig, ax, ncols=2, y=-0.02, **kw):
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, y), ncols=ncols, frameon=False, **kw)


def thistle_design(**kw):
    """The board (projects/foil2d/design/thistle.yaml), with fields replaced by `kw`."""
    import dataclasses

    from iomcfd import boardrank

    d = boardrank.load_design("thistle")
    return dataclasses.replace(d, **kw) if kw else d


def thistle_rank(data: Path, study: str, tu: float, rake: float | None = None, screen_speeds: bool = False,
                 lds=None) -> dict[str, pd.DataFrame]:
    """boardrank.rank of one study's table at one Tu against NACA 0006 (the findings' ranking).
    screen_speeds: upwind 1, 3, 5 kn and downwind 1, 3, 5, 15 kn, the screen's (`--up-kn 1 3 5
    --down-kn 1 3 5 15`)."""
    from iomcfd import boardrank

    d = thistle_design(up_speeds=[1, 3, 5], down_speeds=[1, 3, 5, 15]) if screen_speeds else thistle_design()
    pol = boardrank.cfd_polars([data / f"thistle-{study}.csv"], tu=tu)
    return boardrank.rank(pol, d, rake, lds=lds, baseline=f"{TH_BASE}/{d.chord * 1000:g}")


def _th_shapes():
    from iomcfd import sectiondesign as sd

    return {k: sd.load(k) for k in TH_SECTIONS}


_TH_FLATS = {"file:parallel-l30-t50-r05-a20.dat": (0.30, 0.50), "file:plank-typical.dat": (0.10, 0.75)}


@_th_style
def thistle_board_side(out: Path) -> Path:
    """Side view of the raked board: the water's speed split into its parts square to and along the
    leading edge (simple sweep), the chord square to the edge and along the flow."""
    lam = np.radians(10.0)
    c, b = 18.0, 1.24 / 0.0254  # in
    t_ = np.array([np.sin(lam), -np.cos(lam)])  # along the leading edge, down and aft
    n_ = np.array([np.cos(lam), np.sin(lam)])  # square to it, aft
    fig, a = plt.subplots(figsize=(TH_W, 6.4))
    p0 = np.array([0.0, 0.0])
    a.add_patch(Polygon(np.array([p0, p0 + b * t_, p0 + b * t_ + c * n_, p0 + c * n_]), closed=True, fc="#e8e2d4",
                        ec=INK, lw=1.3))
    a.add_patch(Polygon([[-36, 0], [36, 0], [36, 8], [-36, 8]], closed=True, fc="#d9d3c4", ec="none"))
    a.plot([-36, 36], [0, 0], color=INK, lw=1.5)
    a.text(-35, 4, "hull (bow to the left)", fontsize=10.5, va="center")
    a.plot([0, 0], [0, -17], color=MUTED, lw=0.9, ls=":")
    a.add_patch(Arc((0, 0), 30, 30, theta1=-90, theta2=-80, color=ACCENT, lw=1.4))
    a.text(-1.2, -6.5, "rake Λ = 10°\n(assumed)", color=ACCENT, fontsize=10.5, ha="right", va="top")
    yq = -28.0
    q = np.array([-yq * np.tan(lam), yq])  # on the leading edge
    L = 24.0
    tail = q - np.array([L, 0])
    arrow = dict(arrowstyle="-|>", mutation_scale=14, lw=1.8, shrinkA=0, shrinkB=0)
    a.add_patch(FancyArrowPatch(tail, q, color=INK, **arrow))
    a.text(tail[0], yq - 1.5, "$V_b$: water past the boat", fontsize=10.5, va="top")
    mid = tail + L * np.cos(lam) * n_
    a.add_patch(FancyArrowPatch(tail, mid, color=ACCENT, **arrow))
    a.add_patch(FancyArrowPatch(mid, q, color="#2f5d50", **arrow))
    a.text(tail[0], mid[1] + 1.8, "$V_n = V_b \\cos Λ$: square to the edge", color=ACCENT, fontsize=10.5, va="bottom")
    a.text(q[0] + 1.3, q[1] + 2.2, "$V_b \\sin Λ$:\nalong the edge", color="#2f5d50", fontsize=10, va="center")
    d1 = p0 + 0.86 * b * t_
    a.annotate("", d1 + c * n_, d1, arrowprops=dict(arrowstyle="<->", color=INK, lw=1.0))
    a.text(*(d1 + 0.5 * c * n_ + np.array([0.0, -1.8])), "chord $c_n$ = 18 in,\nsquare to the edge", fontsize=10,
           ha="center", va="top")
    y2 = -38.0
    x_le = -y2 * np.tan(lam)
    a.annotate("", (x_le + c / np.cos(lam), y2), (x_le, y2), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1.0))
    a.text(x_le + c / np.cos(lam) / 2, y2 + 1.0, "18.28 in along the flow", fontsize=10, color=MUTED, ha="center")
    e = p0 + b * t_
    a.text(e[0] - 2, e[1] - 2.5, "$b$ = 1.24 m (49 in) along the edge,\nabout 48 in below the hull (assumed)",
           fontsize=10, va="top")
    a.set_aspect("equal")
    a.set(xlim=(-36, 36), ylim=(-66, 9))
    a.axis("off")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_board_top(out: Path) -> Path:
    """Top view: heading, course and leeway, and the board's side force and drag (schematic, leeway
    exaggerated)."""
    fig, a = plt.subplots(figsize=(TH_W, 5.2))
    s = np.linspace(-1, 1, 200)
    half = 0.36 * np.sqrt(np.clip(1 - s, 0, None)) * np.clip(1 + s, 0, None) ** 0.35  # bow at s = 1
    a.fill(np.r_[half, -half[::-1]], np.r_[s, s[::-1]] * 2.6, color="#e8e2d4", ec=INK, lw=1.2)
    a.plot([0, 0], [-2.9, 3.1], color=MUTED, lw=0.9, ls=":")
    a.text(-0.08, 3.05, "heading\n(centreline)", fontsize=10, color=MUTED, va="bottom", ha="right")
    a.add_patch(Polygon([[-0.03, -0.5], [0.03, -0.5], [0.03, 0.5], [-0.03, 0.5]], closed=True, fc=ACCENT, ec="none"))
    a.text(0.1, 0.45, "board", fontsize=10, color=ACCENT, ha="left", va="center")
    beta = np.radians(9.0)  # exaggerated
    course = np.array([np.sin(beta), np.cos(beta)])  # the path: bow-ish, slipping to leeward (+x)
    a.add_patch(FancyArrowPatch(-2.4 * course, 3.1 * course, arrowstyle="-|>", mutation_scale=14, color=INK, lw=1.4,
                                ls=(0, (6, 3))))
    a.text(*(3.1 * course + np.array([0.12, 0.0])), "course (the boat's path)", fontsize=10, va="bottom")
    a.add_patch(Arc((0, 0), 4.2, 4.2, theta1=90 - np.degrees(beta), theta2=90, color="#2f5d50", lw=1.4))
    a.text(0.42, 1.75, "leeway $β_Y$", color="#2f5d50", fontsize=10.5, va="center")
    flow = -course  # the water passes the board along the course, backwards
    side = np.array([-np.cos(beta), np.sin(beta)])  # square to the flow, to windward (-x)
    a.add_patch(FancyArrowPatch((0, 0), 1.35 * side, arrowstyle="-|>", mutation_scale=16, color=ACCENT, lw=2.2))
    a.text(*(1.35 * side + np.array([-0.02, 0.12])), "side force $S_h$\n(to windward)", color=ACCENT, fontsize=10.5,
           ha="right", va="bottom")
    a.add_patch(FancyArrowPatch((0, 0), 0.7 * flow, arrowstyle="-|>", mutation_scale=14, color=INK, lw=1.8))
    a.text(*(0.7 * flow + np.array([-0.12, -0.05])), "drag $D_h$", fontsize=10.5, va="top", ha="right")
    a.add_patch(FancyArrowPatch((1.35, 1.2), (1.35, -0.1), arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1.2))
    a.text(1.42, 0.55, "water,\nrelative\nto the boat", fontsize=9.5, color=MUTED, va="center")
    a.text(-1.95, -2.75, "Leeway is the sideways angle in this view (here exaggerated).\nRake is the fore-and-aft "
           "tilt in the side view. The section\nsees the leeway square to its raked edge: $α_n = β_Y / \\cos Λ$.",
           fontsize=9.5, color=INK, va="top")
    a.set_aspect("equal")
    a.set(xlim=(-2.0, 2.2), ylim=(-3.9, 3.5))
    a.axis("off")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_shapes(out: Path) -> Path:
    """The eight sections at true scale, 1 in thick on 18 in, one per row: leading edge left, the thickest
    point (or the flat) marked."""
    secs = _th_shapes()
    C = 18.0
    fig, ax = plt.subplots(figsize=(TH_W, 5.6))
    for i, (k, (name, colour, _)) in enumerate(TH_SECTIONS.items()):
        y0 = -i * 2.3
        u = secs[k].surface("upper", 800) * C
        ax.fill(np.r_[u[:, 0], u[::-1, 0]], y0 + np.r_[u[:, 1], -u[::-1, 1]], color=colour, lw=0)
        ax.text(0, y0 + 0.75, name, fontsize=10.5, va="bottom")
        t, xt = secs[k].thickness()
        ticks = [C * f for f in _TH_FLATS[k]] if k in _TH_FLATS else [C * xt]
        for xx in ticks:
            ax.plot([xx, xx], [y0 - 0.85, y0 + 0.85], color=INK, lw=1.0)
    ax.text(-0.2, 0.0, "LE", fontsize=9.5, ha="right", va="center", color=MUTED)
    ax.text(18.2, 0.0, "TE", fontsize=9.5, ha="left", va="center", color=MUTED)
    ax.text(9.0, -17.4, "ticks: thickest point (the flat's ends on the two parallel-sided boards)", fontsize=9.5,
            color=MUTED, ha="center", va="top")
    ax.set_aspect("equal")
    ax.set(xlim=(-1.2, 19.4), ylim=(-18.6, 1.9))
    ax.axis("off")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_profiles(out: Path) -> Path:
    """Half-thickness along the chord, vertical scale exaggerated (the factor is printed on each panel),
    the smooth sections and the parallel-sided ones, and the four that differ most minus NACA 0006."""
    secs = _th_shapes()
    C = 18.0
    x = np.linspace(0, 1, 2001)
    half = {k: np.interp(x, *f.surface("upper", 1600).T) * C for k, f in secs.items()}
    groups = [("Smooth sections", [TH_BASE, "file:naca63-006-t0556.dat", "file:naca64-006-t0556.dat",
                                   "file:naca0006-64-t0556.dat", "file:ht35-t0556.dat", "file:sd8020-t0556.dat"]),
              ("Parallel-sided boards", [TH_BASE, "file:parallel-l30-t50-r05-a20.dat", "file:plank-typical.dat"])]
    fig, axs = plt.subplots(3, 1, figsize=(TH_W, 9.6), gridspec_kw={"height_ratios": [1, 1, 0.9], "hspace": 0.9})
    for ax, (title, keys) in zip(axs[:2], groups):
        for k in keys[::-1]:
            name, colour, _ = TH_SECTIONS[k]
            ax.plot(x * C, half[k], color=colour, ls=TH_DASH[k], lw=2.4 if k == TH_BASE else 1.7, label=name)
        ax.set(xlim=(0, 18), ylim=(0, 0.56), ylabel="half-thickness [in]", title=title)
        h, lab = ax.get_legend_handles_labels()
        ax.legend(h[::-1], lab[::-1], loc="upper center", bbox_to_anchor=(0.5, -0.14), ncols=2, fontsize=9.5)
    d = axs[2]
    for k in ["file:naca63-006-t0556.dat", "file:naca64-006-t0556.dat", "file:parallel-l30-t50-r05-a20.dat",
              "file:plank-typical.dat"]:
        name, colour, _ = TH_SECTIONS[k]
        d.plot(x * C, half[k] - half[TH_BASE], color=colour, ls=TH_DASH[k], lw=1.8, label=name)
    d.axhline(0, color=ACCENT, lw=1.2)
    d.set(xlim=(0, 18), ylim=(-0.09, 0.3), xlabel="from the leading edge [in]", ylabel="[in]",
          title="Half-thickness minus NACA 0006's (above 0: fuller)")
    d.legend(loc="upper left", fontsize=9, ncols=2)
    fig.canvas.draw()
    for ax in axs[:2]:
        bb = ax.get_window_extent()
        k = (18 / bb.width) / (0.56 / bb.height)
        ax.text(0.5, 0.05, f"vertical scale ×{k:.0f}; x: from the leading edge [in]", transform=ax.transAxes,
                ha="center", fontsize=9.5, color=MUTED)
    return _save(fig, out)


@_th_style
def thistle_noses(out: Path) -> Path:
    """The noses at true scale, the first 1.2 in of the chord."""
    secs = _th_shapes()
    C = 18.0
    groups = [("Smooth sections", [TH_BASE, "file:naca63-006-t0556.dat", "file:naca64-006-t0556.dat",
                                   "file:naca0006-64-t0556.dat", "file:ht35-t0556.dat", "file:sd8020-t0556.dat"]),
              ("Parallel-sided boards", [TH_BASE, "file:parallel-l30-t50-r05-a20.dat", "file:plank-typical.dat"])]
    fig, axs = plt.subplots(1, 2, figsize=(TH_W, 3.3), sharey=True)
    for ax, (title, keys) in zip(axs, groups):
        for k in keys[::-1]:
            name, colour, _ = TH_SECTIONS[k]
            u = secs[k].surface("upper", 4000) * C
            for sgn in (1, -1):
                ax.plot(u[:, 0], sgn * u[:, 1], color=colour, ls=TH_DASH[k], lw=2.2 if k == TH_BASE else 1.4)
        ax.set_aspect("equal")
        ax.set(xlim=(-0.05, 1.2), ylim=(-0.55, 0.55), title=title, xlabel="[in]")
    axs[0].set_ylabel("[in]")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_properties_table(out: Path) -> Path:
    """Where each section is thickest, and its nose radius and trailing-edge angle estimated from the
    coordinates, at 1 in on 18 in."""
    from iomcfd import sectiondesign as sd

    notes = {
        TH_BASE: "the reference: the 4-digit section scaled to 1 in",
        "file:naca63-006-t0556.dat": "laminar-flow section (Report 824 table), scaled from 6 to 5.56 %",
        "file:naca64-006-t0556.dat": "the same family, crest further aft",
        "file:naca0006-64-t0556.dat": "NACA 0006 with its crest moved to 40 %",
        "file:ht35-t0556.dat": "Drela's glider tail section, the IOM study's winner",
        "file:sd8020-t0556.dat": "Selig-Donovan low-speed section, sharp nose",
        "file:parallel-l30-t50-r05-a20.dat": "best of 144 parallel-sided shapes in XFOIL",
        "file:plank-typical.dat": "half-round nose, straight taper (an assumed home-built board)",
    }
    rows = ["| section | thickest at | nose radius (est.) | trailing-edge angle (est.) | what it is |",
            "|---|--:|--:|--:|---|"]
    for k, (name, _, _) in TH_SECTIONS.items():
        p = sd.properties(sd.load(k))
        flat = {"file:parallel-l30-t50-r05-a20.dat": "flat 30–50 %", "file:plank-typical.dat": "flat 10–75 %"}
        where = flat.get(k, f"{100 * p['x_t']:.0f} %&nbsp;({18 * p['x_t']:.1f}&nbsp;in)")
        rows.append(f"| {name} | {where} | {18 * TH_IN * p['r_le']:.1f}&nbsp;mm | {p['te_angle']:.1f}° | {notes[k]} |")
    out.write_text("\n".join(rows) + "\n")
    return out


@_th_style
def thistle_grid(data: Path, out: Path) -> Path:
    """The computed points: boat speed against the section's angle, the screen's and the finalists', with
    the Reynolds number on top and the three upwind side-force loads."""
    from iomcfd import boardrank

    d = thistle_design()
    sc = pd.read_csv(data / "thistle-screen.csv")
    ex = pd.read_csv(data / "thistle-extend.csv")
    kn = {round(boardrank.normal_speed(v, d.rake), 4): v for v in d.cfd_speeds_kn}
    xs = {v: i for i, v in enumerate(d.cfd_speeds_kn)}
    fig, ax = plt.subplots(figsize=(TH_W, 4.6))
    ax.axvspan(-0.5, 4.5, color="#e8e2d4", alpha=0.6, lw=0)
    for df, st in ((ex, dict(s=48, facecolors="none", edgecolors="#2f5d50", lw=1.2, label="finalists: 3 sections")),
                   (sc, dict(s=18, color=ACCENT, marker="D", label="screen: 8 sections"))):
        pts = df[["speed", "aoa"]].drop_duplicates()
        ax.scatter([xs[kn[round(v, 4)]] for v in pts.speed], pts.aoa, zorder=3, **st)
    ax.text(2, 11.2, "upwind", ha="center", fontsize=11)
    ax.text(6.5, 11.2, "downwind", ha="center", fontsize=11)
    for a_, name in zip(d.load_aoa, ("low", "working", "high")):
        ax.axhline(a_, xmax=5 / 9, color=MUTED, lw=0.9, ls=":")
        ax.text(4.6, a_ + 0.12, name, fontsize=9.5, color=MUTED, va="bottom")
    ax.set_xticks(range(9), [f"{v:g}" for v in d.cfd_speeds_kn])
    ax.set(xlim=(-0.5, 8.5), ylim=(-0.6, 12.2), xlabel="boat speed $V_b$ [kn]", ylabel="section angle $α_n$ [°]",
           yticks=[0, 1, 2, 3, 4, 5, 6, 8, 10])
    top = ax.secondary_xaxis("top")
    top.set_xticks(range(9), [f"{boardrank.normal_speed(v, d.rake) * d.chord / d.nu / 1e6:.1f}" for v in d.cfd_speeds_kn])
    top.set_xlabel("Reynolds number [millions]", fontsize=10.5)
    ax.grid(axis="x", visible=False)
    _th_bottom_legend(fig, ax, ncols=2, y=0.02)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_pipeline(out: Path) -> Path:
    """The steps of the study, top to bottom."""
    from matplotlib.patches import FancyBboxPatch

    steps = [
        ("XFOIL screen", "26 sections + 144 parallel-sided shapes, seconds each", "#e8e2d4"),
        ("Mesh study", "3 sections × 4 meshes: 96 CFD cases → the fine mesh", "#e8e2d4"),
        ("Validation", "NACA 0006 and 64-006 against NACA Report 824: 28 cases", "#e8e2d4"),
        ("Tu calibration", "the model input that matches the tunnel: 40 cases", "#e8e2d4"),
        ("CFD screen", "8 sections at Tu 0.1 and 1 %: 320 cases", "#d4dfd9"),
        ("Finalists", "3 sections at Tu 0.3 and 0.6 %: 342 cases", "#d4dfd9"),
        ("Answer", "NACA 0006 at 1 in, the reference section", "#f0d6cc"),
    ]
    fig, ax = plt.subplots(figsize=(TH_W, 6.3))
    h, gap = 0.62, 0.3
    for i, (head, body, fc) in enumerate(steps):
        y = -i * (h + gap)
        ax.add_patch(FancyBboxPatch((0.6, y - h), 4.6, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc,
                                    ec=ACCENT if head == "Answer" else MUTED, lw=1.0))
        ax.text(0.75, y - 0.2, head, fontsize=11.5, weight="bold", va="center")
        ax.text(0.75, y - 0.46, body, fontsize=9.8, va="center")
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((2.9, y - h - 0.02), (2.9, y - h - gap + 0.02), arrowstyle="-|>",
                                         mutation_scale=11, color=MUTED, lw=1))
    for (i0, i1, label, colour) in ((0, 3, "method\nchecks", MUTED), (4, 5, "ranking", "#2f5d50")):
        y0, y1 = -i0 * (h + gap), -i1 * (h + gap) - h
        ax.plot([0.4, 0.4], [y0, y1], color=colour, lw=1.2)
        ax.text(0.33, (y0 + y1) / 2, label, rotation=90, ha="right", va="center", fontsize=10, color=colour)
    ax.set(xlim=(-0.05, 5.3), ylim=(-6 * (h + gap) - h - 0.05, 0.05))
    ax.axis("off")
    return _save(fig, out)


@_th_style
def thistle_mesh(out: Path) -> Path:
    """The fine C-grid of NACA 0006 at 457 mm and 3 kn, from the same generator the runs use."""
    from iomcfd import config
    from iomcfd.geometry import cmesh, foils
    from iomcfd.project import load_project

    project = load_project("foil2d")
    p = {**project.defaults, "foil": TH_BASE, "chord": 0.4572, "speed": 1.5199, "mesh": "fine", "temperature": 20}
    spec = cmesh.CMeshSpec(**project.derive(p)["mesh_spec"])
    P, _ = cmesh.generate(foils.load(TH_BASE, [config.geometry_dir() / "foils"]), spec)
    P = P / spec.chord
    fig = plt.figure(figsize=(TH_W, 5.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15])
    axes = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    views = [("The section", (-0.15, 1.25), (-0.3, 0.3), 2),
             ("Whole domain, 50 chords", (-55, 55), (-55, 55), 6),
             ("Leading edge", (-0.006, 0.03), (-0.018, 0.018), 1)]
    for ax, (title, xl, yl, k) in zip(axes, views):
        for j in range(0, P.shape[1], k):
            ax.plot(P[:, j, 0], P[:, j, 1], color="#3c4a57", lw=0.2)
        for i in range(0, P.shape[0], k):
            ax.plot(P[i, :, 0], P[i, :, 1], color="#3c4a57", lw=0.2)
        ax.plot(P[:, 0, 0], P[:, 0, 1], color=ACCENT, lw=1.3)
        ax.set(xlim=xl, ylim=yl, title=title, xlabel="x / c")
        ax.set_aspect("equal")
        ax.grid(False)
    axes[0].set_ylabel("y / c")
    fig.tight_layout()
    return _save(fig, out, dpi=150)


@_th_style
def thistle_mesh_study(data: Path, out: Path) -> Path:
    """Drag on each mesh against the fine mesh's, per test point, for the three sections of the mesh
    study (transition model, Tu 0.1 %)."""
    from iomcfd import boardrank

    d = thistle_design()
    m = pd.read_csv(data / "thistle-mesh.csv")
    m = m[(m.status != "failed") & (m.turbulence == "kOmegaSSTLM")]
    levels = ["coarse", "medium", "fine", "xfine"]
    kn = {round(boardrank.normal_speed(v, d.rake), 4): v for v in d.cfd_speeds_kn}
    fig, axs = plt.subplots(3, 1, figsize=(TH_W, 8.2), sharex=True)
    pal = ["#2f5d50", "#3f7cac", "#e09a4f", ACCENT, "#5c4d7d", "#3c4a57", "#b3a27f"]
    marks = ["o", "s", "D", "^", "v", "P", "X"]
    for ax, f in zip(axs, ["file:naca0006-t0556.dat", "file:naca64-006-t0556.dat", "file:plank-typical.dat"]):
        g = m[m.foil == f]
        for i, ((v, a_), h) in enumerate(g.groupby(["speed", "aoa"])):
            h = h.set_index("mesh").reindex(levels)
            ax.plot(range(4), 100 * (h.Cd / h.loc["fine", "Cd"] - 1), marker=marks[i % 7], ms=4.5, lw=1.3,
                    color=pal[i % 7], label=f"{kn[round(v, 4)]:g} kn, {a_:g}°")
        ax.axhline(0, color=INK, lw=0.8)
        ax.axhspan(-3, 3, color="#e8e2d4", alpha=0.7, lw=0)
        ax.set(title=TH_SECTIONS[f][0], ylim=(-25, 25), ylabel="drag vs fine [%]")
        ax.grid(axis="x", visible=False)
    axs[-1].set_xticks(range(4), levels)
    _th_bottom_legend(fig, axs[0], ncols=3, y=0.04, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    return _save(fig, out)


def _r824():
    v = pd.read_csv(R824, comment="#")
    return {"naca0006": v[v.source == "R824 NACA 0006"], "file:naca64-006.dat": v[v.source == "R824 NACA 64-006"]}


def _r824_cd(ref: pd.DataFrame, cl):
    g = ref.dropna(subset=["Cd"]).sort_values("Cl")
    return np.interp(cl, g.Cl, g.Cd)


def _validation_runs(data: Path, f: str):
    v = pd.read_csv(data / "thistle-validation.csv")
    v = v[v.status != "failed"]
    c = pd.read_csv(data / "thistle-tu-calibration.csv")
    return [(v[(v.foil == f) & (v.turbulence == "kOmegaSSTLM")], dict(color="#7fae94", ls="-", marker="s", ms=4),
             "transition model, Tu 0.05 % (the tunnel's)"),
            (c[(c.foil == f) & np.isclose(c.Tu, 0.3)], dict(color=ACCENT, ls="-", marker="^", ms=5),
             "transition model, Tu 0.3 %"),
            (c[(c.foil == f) & np.isclose(c.Tu, 0.6)], dict(color="#e09a4f", ls=(0, (5, 2)), marker="v", ms=5),
             "transition model, Tu 0.6 %"),
            (v[(v.foil == f) & (v.turbulence == "kOmegaSST")], dict(color="#5c4d7d", ls=(0, (2, 2)), marker="o", ms=4),
             "fully turbulent (SST)")]


@_th_style
def thistle_validation_drag(data: Path, out: Path) -> Path:
    """Drag against lift from the CFD and from Report 824 (true 6 % sections, Re 3e6)."""
    ref = _r824()
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 7.6), sharex=True)
    for ax, (f, title) in zip(axs, (("naca0006", "NACA 0006"), ("file:naca64-006.dat", "NACA 64-006"))):
        rd = ref[f].dropna(subset=["Cd"])
        ax.plot(rd.Cl, rd.Cd * 1e4, "o", color=INK, ms=5.5, label="Report 824, measured", zorder=5)
        for g, st, lab in _validation_runs(data, f):
            lo = g[g.aoa <= 6].sort_values("aoa")
            ax.plot(lo.Cl, lo.Cd * 1e4, lw=1.5, label=lab, **st)
        ax.set(xlim=(-0.05, 0.72), ylim=(20, 130), ylabel="$C_d$ × 10⁴", title=f"{title}, Re 3 million")
    axs[1].set_xlabel("lift coefficient $C_l$")
    _th_bottom_legend(fig, axs[0], ncols=1, y=0.02, fontsize=10)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_validation_lift(data: Path, out: Path) -> Path:
    """Lift against angle from the CFD and from Report 824; hollow points did not converge."""
    ref = _r824()
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 7.0), sharex=True)
    for ax, (f, title) in zip(axs, (("naca0006", "NACA 0006"), ("file:naca64-006.dat", "NACA 64-006"))):
        ra = ref[f].dropna(subset=["aoa"])
        ax.plot(ra.aoa, ra.Cl, "o", color=INK, ms=5.5, label="Report 824, measured", zorder=5)
        for g, st, lab in _validation_runs(data, f):
            if "0.3" in lab or "0.6" in lab:
                continue
            g = g.sort_values("aoa")
            ok = g[g.status == "ok"]
            ax.plot(ok.aoa, ok.Cl, lw=1.5, label=lab, **st)
            nc = g[g.status != "ok"]
            ax.plot(nc.aoa, nc.Cl, ls="none", marker=st["marker"], ms=st["ms"] + 2, mfc="none", mec=st["color"])
        ax.set(xlim=(-0.5, 12.5), ylim=(-0.05, 1.1), ylabel="$C_l$", title=title)
    axs[1].set_xlabel("angle of attack [°]")
    axs[0].plot([], [], ls="none", marker="o", mfc="none", mec=MUTED, ms=6, label="hollow: did not converge")
    _th_bottom_legend(fig, axs[0], ncols=1, y=0.02, fontsize=10)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_calibration(data: Path, out: Path) -> Path:
    """Drag error against Report 824 at the computed lift, per angle, against the inlet Tu."""
    ref = _r824()
    v = pd.read_csv(data / "thistle-validation.csv")
    v = v[(v.status != "failed") & (v.turbulence == "kOmegaSSTLM") & v.aoa.isin([0, 2, 4])]
    c = pd.concat([pd.read_csv(data / "thistle-tu-calibration.csv"), v], ignore_index=True)
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 7.0), sharex=True)
    pal = {0: ("#3c4a57", "o", "-"), 1: ("#3f7cac", "s", (0, (5, 2))), 2: (ACCENT, "D", "-"), 4: ("#e09a4f", "^", (0, (2, 2)))}
    for ax, (f, title, tu_eff) in zip(axs, (("naca0006", "NACA 0006", 0.3), ("file:naca64-006.dat", "NACA 64-006", 0.45))):
        g = c[c.foil == f].copy()
        g["err"] = 100 * (g.Cd / _r824_cd(ref[f], g.Cl.abs()) - 1)
        for a_, h in g.groupby("aoa"):
            colour, mk, ls = pal[int(a_)]
            h = h.sort_values("Tu")
            ax.plot(h.Tu, h.err, marker=mk, ls=ls, ms=5, lw=1.5, color=colour, label=f"{a_:g}°")
        ax.axhline(0, color=INK, lw=0.9)
        ax.axhspan(-6, 6, color="#e8e2d4", alpha=0.7, lw=0)
        ax.axvline(tu_eff, color=ACCENT, lw=1.1, ls=":")
        ax.text(tu_eff * 0.94, 75, f"matches\nat about\n{tu_eff:g} %", color=ACCENT, fontsize=10, va="top", ha="right")
        ax.set_xscale("log")
        ax.set(title=title, ylim=(-50, 90), ylabel="drag vs Report 824\nat the same $C_l$ [%]")
    axs[1].set_xticks([0.05, 0.1, 0.3, 0.6, 1, 1.5], ["0.05", "0.1", "0.3", "0.6", "1", "1.5"])
    axs[1].set_xlabel("inlet turbulence intensity Tu, the model input [%]")
    _th_bottom_legend(fig, axs[0], ncols=4, y=0.03, title="section angle", title_fontsize=10)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_r824(out: Path) -> Path:
    """Report 824's measured drag of NACA 0006 and 64-006 against lift at Re 3e6, with the lift the
    Thistle board needs downwind and upwind."""
    ref = _r824()
    fig, ax = plt.subplots(figsize=(TH_W, 4.6))
    ax.axvspan(-0.03, 0.03, color="#d4dfd9", lw=0)
    ax.axvspan(0.1, 0.45, color="#f0d6cc", alpha=0.7, lw=0)
    ax.text(0.0, 99, "down-\nwind", ha="center", va="top", fontsize=10, color="#2f5d50")
    ax.text(0.275, 99, "upwind side-force loads", ha="center", va="top", fontsize=10, color=ACCENT)
    for f, name, colour, mk, ls in (("naca0006", "NACA 0006", ACCENT, "D", "-"),
                                    ("file:naca64-006.dat", "NACA 64-006", "#3f7cac", "s", (0, (5, 2)))):
        g = ref[f].dropna(subset=["Cd"]).sort_values("Cl")
        g = g[g.Cl > -0.2]
        ax.plot(g.Cl, g.Cd * 1e4, marker=mk, ls=ls, color=colour, ms=5, lw=1.7, label=name)
    for cl, (xt, yt) in ((0.0, (0.035, 36)), (0.2, (0.21, 66)), (0.4, (0.46, 63))):
        a0, a6 = _r824_cd(ref["naca0006"], cl), _r824_cd(ref["file:naca64-006.dat"], cl)
        ax.text(xt, yt, f"$C_l$ {cl:g}: {100 * (a6 / a0 - 1):+.0f} %", fontsize=10, color=INK)
    ax.set(xlim=(-0.2, 0.8), ylim=(30, 100), xlabel="lift coefficient $C_l$", ylabel="$C_d$ × 10⁴")
    ax.legend(loc="lower right", fontsize=10)
    ax.text(0.79, 31.5, "64-006 against 0006 at equal $C_l$", fontsize=9, color=MUTED, ha="right", va="bottom",
            transform=ax.transData, alpha=0)
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_screen(data: Path, out: Path) -> Path:
    """The CFD screen: board drag against NACA 0006, upwind (1, 3, 5 kn, three loads) and downwind (0 deg at
    1, 3, 5 and 15 kn), at the two screen levels of the model's turbulence input."""
    s = {tu: thistle_rank(data, "screen", tu, screen_speeds=True)["summary"] for tu in (0.1, 1.0)}
    order = (s[0.1]["upwind %"] + s[1.0]["upwind %"]).sort_values().index
    order = [c for c in order if not c.startswith(TH_BASE)]
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 8.4), sharex=True)
    y = np.arange(len(order))[::-1]
    clip = 22
    from matplotlib.patches import Patch

    for ax, col, title in ((axs[0], "upwind %", "Upwind: drag at equal side force"),
                           (axs[1], "downwind %", "Downwind: drag at 0°")):
        for tu, alpha, off, hatch in ((0.1, 0.45, 0.2, "///"), (1.0, 1.0, -0.2, None)):
            vals = s[tu].reindex(order)[col]
            ax.barh(y + off, np.clip(vals, -clip, clip), height=0.38, color=[_th_colour(c) for c in order],
                    alpha=alpha, hatch=hatch, edgecolor=PAPER, lw=0)
            for yi, v in zip(y + off, vals):
                if v > clip:
                    ax.text(clip - 0.5, yi, f"{v:+.0f} % →", ha="right", va="center", fontsize=9.5, color=PAPER,
                            weight="bold")
                else:
                    ax.text(v + (0.5 if v >= 0 else -0.5), yi, f"{v:+.1f}", ha="left" if v >= 0 else "right",
                            va="center", fontsize=9)
        ax.axvline(0, color=ACCENT, lw=1.3)
        ax.set(xlim=(-16, clip), title=title)
        ax.set_yticks(y, [_th_name(c) for c in order])
        ax.grid(axis="y", visible=False)
    axs[1].set_xlabel("ΔD against NACA 0006 [%]  (← less drag · more →)")
    fig.legend(handles=[Patch(facecolor=MUTED, alpha=0.45, hatch="///", edgecolor=PAPER, label="Tu 0.1 % (pale, hatched)"),
                        Patch(color=MUTED, label="Tu 1 % (solid)")], loc="upper center", bbox_to_anchor=(0.5, 0.025),
               ncols=2, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, out)


def thistle_screen_table(data: Path, out: Path) -> Path:
    s = {tu: thistle_rank(data, "screen", tu, screen_speeds=True)["summary"] for tu in (0.1, 1.0)}
    order = (s[0.1]["upwind %"] + s[1.0]["upwind %"]).sort_values().index
    rows = ["| section | up, Tu 0.1 % | up, Tu 1 % | down, Tu 0.1 % | down, Tu 1 % | stall margin (indicative) | outcome |",
            "|---|--:|--:|--:|--:|--:|---|"]
    out_of = {"file:plank-typical.dat", "file:parallel-l30-t50-r05-a20.dat"}
    for c in order:
        a, b = s[0.1].loc[c], s[1.0].loc[c]
        base = c.rsplit("/", 1)[0]
        verdict = ("reference" if base == TH_BASE else "rejected: loses at both levels" if base in out_of
                   else "finalist" if base in TH_FINALISTS
                   else "dropped: trades less than the 6-series" if base == "file:naca0006-64-t0556.dat"
                   else "dropped: never ahead beyond the mesh resolution")
        cells = ["0"] * 4 if base == TH_BASE else \
            [f"{v:+.1f}" for v in (a["upwind %"], b["upwind %"], a["downwind %"], b["downwind %"])]
        rows.append(f"| {_th_name(c)} | " + " | ".join(cells) +
                    f" | {a['stall margin deg']:.1f}°&nbsp;/&nbsp;{b['stall margin deg']:.1f}° | {verdict} |")
    out.write_text("\n".join(rows) + "\n")
    return out


TH_LABEL_OFFSETS = {  # (Tu, section): label offset in points, where the defaults collide
    (0.1, TH_BASE): (-7, 8), (0.1, "file:ht35-t0556.dat"): (7, -8), (0.1, "file:sd8020-t0556.dat"): (7, 8),
    (0.1, "file:naca63-006-t0556.dat"): (-7, -7), (0.1, "file:naca64-006-t0556.dat"): (7, 7),
    (1.0, TH_BASE): (-7, 8), (1.0, "file:sd8020-t0556.dat"): (4, -10), (1.0, "file:parallel-l30-t50-r05-a20.dat"): (7, 8),
    (1.0, "file:ht35-t0556.dat"): (7, 6), (1.0, "file:naca63-006-t0556.dat"): (7, 6), (1.0, "file:naca64-006-t0556.dat"): (7, -6),
    (1.0, "file:naca0006-64-t0556.dat"): (7, 0),
}


@_th_style
def thistle_tradeoff(data: Path, out: Path) -> Path:
    """Upwind against downwind for the eight sections at both screen levels of the turbulence input."""
    s = {tu: thistle_rank(data, "screen", tu, screen_speeds=True)["summary"] for tu in (0.1, 1.0)}
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 9.4), sharex=True)
    lim = (-15, 17)
    for ax, tu in zip(axs, (0.1, 1.0)):
        ax.axhspan(lim[0], 0, xmin=0, xmax=(0 - lim[0]) / (lim[1] - lim[0]), color="#d4dfd9", alpha=0.6, lw=0)
        ax.text(-14.4, -14.3, "better both ways", fontsize=9.5, color="#2f5d50")
        for c, r in s[tu].iterrows():
            x, y = r["upwind %"], r["downwind %"]
            off = x > lim[1] or y > lim[1]
            xp, yp = min(x, lim[1] - 0.7), min(y, lim[1] - 0.7)
            ax.scatter(xp, yp, s=70, color=_th_colour(c), zorder=3, marker=">" if off else _th_marker(c),
                       edgecolors=PAPER, lw=0.6)
            lab = _th_name(c) + (f" ({x:+.0f} %, {y:+.0f} %)" if off else "")
            base = c.rsplit("/", 1)[0]
            dx, dy = TH_LABEL_OFFSETS.get((tu, base), (7, 5)) if not off else (-7, -11)
            ax.annotate(lab, (xp, yp), (dx, dy), textcoords="offset points", fontsize=9.5,
                        ha="left" if dx >= 0 else "right", va="center")
        ax.axhline(0, color=INK, lw=0.8)
        ax.axvline(0, color=INK, lw=0.8)
        ax.set(xlim=lim, ylim=lim, title=f"Tu {tu:g} %" + (" (too laminar)" if tu == 0.1 else " (higher input)"),
               ylabel="downwind ΔD [%]")
    axs[1].set_xlabel("upwind ΔD against NACA 0006 [%]")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_bounds(data: Path, out: Path) -> Path:
    """The 6-series' upwind and downwind drag against NACA 0006 at the four turbulence inputs run (1, 3 and
    5 kn upwind; 1, 3, 5 and 15 kn downwind, as in the screen)."""
    rows = []
    for study, tus in (("screen", (0.1, 1.0)), ("extend", (0.3, 0.6))):
        for tu in tus:
            sm = thistle_rank(data, study, tu, screen_speeds=True)["summary"]
            for c, r in sm.iterrows():
                rows.append({"candidate": c, "Tu": tu, "up": r["upwind %"], "down": r["downwind %"]})
    df = pd.DataFrame(rows)
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 7.2), sharex=True)
    for ax, col, title in ((axs[0], "up", "Upwind (1, 3 and 5 kn)"), (axs[1], "down", "Downwind (0° at 1, 3, 5, 15 kn)")):
        ax.axvspan(0.3, 0.6, color="#f0d6cc", alpha=0.6, lw=0)
        ax.axhspan(-3, 3, color="#e8e2d4", alpha=0.6, lw=0)
        for c in ("file:naca63-006-t0556.dat/457.2", "file:naca64-006-t0556.dat/457.2"):
            g = df[df.candidate == c].sort_values("Tu")
            ax.plot(g.Tu, g[col], marker=_th_marker(c), ls=TH_DASH[c.rsplit("/", 1)[0]], color=_th_colour(c), lw=2,
                    ms=6, label=_th_name(c))
        ax.axhline(0, color=ACCENT, lw=1.3)
        ax.set_xscale("log")
        ax.set(title=title, ylabel="ΔD vs NACA 0006 [%]")
    axs[0].text(0.425, 11.5, "calibrated\ninput band", ha="center", va="top", fontsize=9.5, color=ACCENT)
    axs[1].set_xticks([0.1, 0.3, 0.6, 1.0], ["0.1", "0.3", "0.6", "1"])
    axs[1].set_xlabel("inlet turbulence intensity Tu, the model input [%]")
    _th_bottom_legend(fig, axs[0], ncols=2, y=0.03)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_finalists(data: Path, out: Path) -> Path:
    """The finalists against NACA 0006 by boat speed at the calibrated Tu: upwind (mean of the three
    loads) and downwind (0 deg)."""
    r = {tu: thistle_rank(data, "extend", tu) for tu in (0.3, 0.6)}
    fig, axs = plt.subplots(2, 1, figsize=(TH_W, 8.0))
    for tu in (0.3, 0.6):
        up = r[tu]["upwind"].pivot_table(index="speed", columns="candidate", values="vs_base", aggfunc="mean")
        dn = r[tu]["downwind"].pivot_table(index="speed", columns="candidate", values="drag_0_vs_base")
        for c in TH_FINALISTS[1:]:
            k = f"{c}/457.2"
            name, colour, mk = TH_SECTIONS[c]
            st = dict(color=colour, ls=TH_TU_DASH[tu], lw=1.9, marker=mk, ms=5.5,
                      mfc=colour if tu == 0.3 else PAPER)
            axs[0].plot(up.index, up[k], label=f"{name}, Tu {tu:g} %", **st)
            axs[1].plot(dn.index, dn[k], **st)
    for ax in axs:
        ax.axhline(0, color=ACCENT, lw=1.3)
        ax.axhspan(-3, 3, color="#e8e2d4", alpha=0.6, lw=0)
        ax.set_ylabel("ΔD vs NACA 0006 [%]")
    axs[0].set(title="Upwind, mean of the three side-force loads", xticks=[1, 2, 3, 4, 5], xlabel="boat speed $V_b$ [kn]")
    axs[1].set(title="Downwind, at 0°", xlabel="boat speed $V_b$ [kn]")
    axs[1].set_xticks([1, 3, 5, 7.5, 10, 12.5, 15], ["1", "3", "5", "7.5", "10", "12.5", "15"])
    axs[1].axvspan(5.15, 7.35, color="#e8e2d4", alpha=0.9, lw=0)
    axs[1].text(6.25, -17.5, "not\ncomputed", ha="center", fontsize=9, color=MUTED)
    _th_bottom_legend(fig, axs[0], ncols=2, y=0.03, fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return _save(fig, out)


@_th_style
def thistle_equal_force(data: Path, out: Path) -> Path:
    """Upwind at equal side force: each finalist's board drag against NACA 0006's, over the side-force
    range at 1, 3 and 5 kn, at the calibrated Tu (linear between the computed angles, as the ranking)."""
    from iomcfd import boardrank, racetime

    d = thistle_design()
    fig, axs = plt.subplots(3, 1, figsize=(TH_W, 10.0))
    for tu in (0.3, 0.6):
        pol = boardrank.cfd_polars([data / "thistle-extend.csv"], tu=tu)
        f = boardrank.board_forces(pol, d, d.up_speeds)
        lds = boardrank.loads(f, f"{TH_BASE}/457.2", d.load_aoa)
        for ax, v in zip(axs, (1, 3, 5)):
            def branch(c):
                g = f[(f.candidate == f"{c}/457.2") & np.isclose(f.speed, v) & (f.aoa >= 0)].sort_values("aoa")
                k = racetime.prestall_branch(g.aoa.to_numpy(), g.side_force.to_numpy())
                return g.side_force.to_numpy()[k], g.drag.to_numpy()[k]

            s0, d0 = branch(TH_BASE)
            for c in TH_FINALISTS[1:]:
                s1, d1 = branch(c)
                grid = np.linspace(max(s0[0], s1[0]), min(s0[-1], s1[-1]), 400)
                name, colour, mk = TH_SECTIONS[c]
                ax.plot(grid, 100 * (np.interp(grid, s1, d1) / np.interp(grid, s0, d0) - 1), color=colour,
                        ls=TH_TU_DASH[tu], lw=1.9, label=f"{name}, Tu {tu:g} %")
            if tu == 0.3:
                for _, ld in lds[np.isclose(lds.speed, v)].iterrows():
                    ax.axvline(ld.force, color=MUTED, lw=0.9, ls=":")
                    ax.text(ld.force, 0.97, TH_LOADS[ld.load], transform=ax.get_xaxis_transform(), rotation=90,
                            ha="right", va="top", fontsize=9, color=MUTED)
                ax.set_xlim(0, 1.12 * lds[np.isclose(lds.speed, v)].force.max())
            ax.axhline(0, color=ACCENT, lw=1.2)
            ax.set(title=f"{v} kn", ylabel="ΔD vs NACA 0006 [%]", ylim=(-17, 32))
    axs[-1].set_xlabel("side force $S_h$ [N]")
    _th_bottom_legend(fig, axs[0], ncols=2, y=0.03, fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return _save(fig, out)


def _th_results(data: Path):
    return {tu: thistle_rank(data, "extend", tu) for tu in (0.3, 0.6)}


def thistle_results_table(data: Path, out: Path) -> Path:
    """The main answer: the finalists against NACA 0006 at the calibrated Tu, rake 10 deg."""
    rows = ["| section | Tu | ΔD upwind | Δ leeway | ΔD downwind 1–15 kn | ΔD downwind 7.5–15 kn |",
            "|---|--:|--:|--:|--:|--:|"]
    for tu, r in _th_results(data).items():
        sm = r["summary"]
        for c in TH_FINALISTS[1:]:
            q = sm.loc[f"{c}/457.2"]
            rows.append(f"| {TH_SECTIONS[c][0]} | {tu:g}&nbsp;% | **{q['upwind %']:+.1f}&nbsp;%** | "
                        f"{q['d leeway deg']:+.2f}° | {q['downwind %']:+.1f}&nbsp;% | {q['downwind 7.5+ kn %']:+.1f}&nbsp;% |")
    out.write_text("\n".join(rows) + "\n")
    return out


def thistle_results_detail_table(data: Path, out: Path) -> Path:
    """The upwind gap per side-force load, the least favourable point and the indicative stall margins."""
    rows = ["| section | Tu | low load | working load | high load | worst point | stall margin (indicative) |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for tu, r in _th_results(data).items():
        sm, up = r["summary"], r["upwind"]
        per = up.groupby(["candidate", "load"]).vs_base.mean().unstack()
        for c in TH_FINALISTS:
            k = f"{c}/457.2"
            q = sm.loc[k]
            margin = f"{q['stall margin deg']:.1f}°" + ("&nbsp;(≥)" if q["margin censored"] else "")
            if c == TH_BASE:
                rows.append(f"| {TH_SECTIONS[c][0]} | {tu:g}&nbsp;% | 0 | 0 | 0 | 0 | {margin} |")
                continue
            rows.append(f"| {TH_SECTIONS[c][0]} | {tu:g}&nbsp;% | {per.loc[k, 'light']:+.1f}&nbsp;% | "
                        f"{per.loc[k, 'working']:+.1f}&nbsp;% | {per.loc[k, 'high']:+.1f}&nbsp;% | "
                        f"{q['upwind worst %']:+.1f}&nbsp;% | {margin} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def thistle_rake_table(data: Path, out: Path) -> Path:
    """Upwind and downwind drag against NACA 0006 at rake 5, 10 and 15 deg (loads fixed at 10 deg)."""
    rows = ["| section | Tu | up, 5° | up, 10° | up, 15° | down, 5° | down, 10° | down, 15° | rule outcome |",
            "|---|--:|--:|--:|--:|--:|--:|--:|---|"]
    for tu in (0.3, 0.6):
        lds = thistle_rank(data, "extend", tu)["loads"]
        sm = {rk: thistle_rank(data, "extend", tu, rake=rk, lds=lds)["summary"] for rk in (5.0, 10.0, 15.0)}
        for c in TH_FINALISTS[1:]:
            k = f"{c}/457.2"
            up = [sm[rk].loc[k, "upwind %"] for rk in (5.0, 10.0, 15.0)]
            dn = [sm[rk].loc[k, "downwind %"] for rk in (5.0, 10.0, 15.0)]
            verdict = "NACA 0006 at every rake" if all(u > 1 for u in up) else "tie at 5°: downwind decides"
            rows.append(f"| {TH_SECTIONS[c][0]} | {tu:g}&nbsp;% | " + " | ".join(f"{u:+.1f}" for u in up) + " | "
                        + " | ".join(f"{x:+.1f}" for x in dn) + f" | {verdict} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def _th_transition(x: np.ndarray, cf: np.ndarray) -> float:
    """An estimate of where the boundary layer turns turbulent: the steepest rise of C_f past 5 % of the
    chord (the curve smoothed a little first)."""
    k = (x > 0.05) & (x < 0.985)
    xs, cs = x[k], np.convolve(cf[k], np.ones(9) / 9, mode="same")
    slope = np.gradient(cs, xs)
    return float(xs[np.argmax(slope[5:-5]) + 5])


@_th_style
def thistle_surface(data: Path, out: Path, tu: float) -> Path:
    """At 3 kn and 2 deg, the same angle for all three finalists (so different lift, not equal side force):
    their shapes, the pressure on the suction side and the skin friction, with the estimated transition
    (steepest friction rise) and the computed bubble (reversed wall friction) marked."""
    s = pd.read_csv(data / "thistle-surface-3kn.csv")
    ex = pd.read_csv(data / "thistle-extend.csv")
    tags = {TH_BASE: "naca0006mt0556", "file:naca63-006-t0556.dat": "naca63m006", "file:naca64-006-t0556.dat": "naca64m006"}
    secs = _th_shapes()
    fig, axs = plt.subplots(3, 1, figsize=(TH_W, 9.0), sharex=True, gridspec_kw={"height_ratios": [0.55, 1, 1.25]})
    x = np.linspace(0, 1, 801)
    for c in TH_FINALISTS[::-1]:
        name, colour, mk = TH_SECTIONS[c]
        st = dict(color=colour, ls=TH_DASH[c], lw=2.2 if c == TH_BASE else 1.6)
        axs[0].plot(x, np.interp(x, *secs[c].surface("upper", 1600).T), **st)
        g = s[s.file.str.contains(f"Tu{tu:g}_") & s.file.str.contains(tags[c])]
        up = g[(g.upper.astype(str) == "True") & (g.x_c < 0.997)].sort_values("x_c")
        row = ex[(ex.foil == c) & np.isclose(ex.Tu, tu) & np.isclose(ex.speed, 1.5199) & (ex.aoa == 2)].iloc[0]
        axs[1].plot(up.x_c, -up.Cp, label=f"{name} ($C_l$ {row.Cl:.3f}, $C_d$ {row.Cd:.4f})", **st)
        axs[2].plot(up.x_c, up.Cf * 1e3, **st)
        xc, cf = up.x_c.to_numpy(), up.Cf.to_numpy()
        xt = _th_transition(xc, cf)
        axs[2].plot([xt], [np.interp(xt, xc, cf) * 1e3], marker=mk, color=colour, ms=8, mec=PAPER, zorder=5)
        neg = (cf < 0) & (xc > 0.05) & (xc < 0.97)
        if neg.any():
            axs[2].axvspan(xc[neg].min(), xc[neg].max(), color=colour, alpha=0.18, lw=0)
    axs[0].set(ylim=(0, 0.035), ylabel="y / c")
    axs[0].set_title("Shapes (upper half, vertical scale stretched)", fontsize=11)
    axs[0].set_yticks([0, 0.02])
    axs[1].set(ylabel="−$C_p$", ylim=(-0.1, 1.3))
    axs[1].set_title("Pressure on the suction side: a falling curve slows the flow", fontsize=11)
    axs[1].legend(loc="upper right", fontsize=9.5)
    axs[2].axhline(0, color=INK, lw=0.8)
    axs[2].set(ylabel="$C_f$ × 10³", ylim=(-0.4, 4.6), xlabel="x / c", xlim=(0, 1))
    axs[2].set_title("Skin friction: marker = estimated transition; shading = reversed flow", fontsize=11)
    axs[2].text(0.1, 4.25, "laminar: low friction", fontsize=9.5, color=MUTED)
    axs[2].text(0.98, 4.25, "turbulent: high friction", fontsize=9.5, color=MUTED, ha="right")
    fig.suptitle(f"3 kn, 2° (same angle, so different lift), Tu {tu:g} %", x=0.02, ha="left", fontsize=12,
                 weight="bold")
    fig.tight_layout()
    return _save(fig, out)


@_th_style
def thistle_bl_schematic(out: Path) -> Path:
    """Schematic (not computed): three ways the flow can run along the suction side, and the sign of the
    skin friction each gives."""
    fig, axs = plt.subplots(6, 1, figsize=(TH_W, 9.6), gridspec_kw={"height_ratios": [1, 0.55, 1, 0.55, 1, 0.55],
                                                                   "hspace": 0.45})
    x = np.linspace(0, 10, 500)
    cases = [
        ("1. Attached: laminar, then turbulent", 6.5, None, None, False),
        ("2. Short laminar bubble that reattaches", 5.5, (4.4, 6.0), None, False),
        ("3. Long open separation (near stall)", None, (0.6, 10.0), None, True),
    ]
    for i, (title, xt, bubble, _, open_sep) in enumerate(cases):
        a, b = axs[2 * i], axs[2 * i + 1]
        a.fill_between(x, -0.3, 0, color="#d9d3c4")
        a.plot(x, 0 * x, color=INK, lw=1.2)
        if open_sep:
            edge = 0.2 + 0.08 * x
            rev = np.clip(0.08 * (x - 0.6), 0, None)
            a.fill_between(x, 0, np.where(x > 0.6, rev, np.nan), color="#9cb8e0", alpha=0.9)
            for xa in (3.5, 6.5, 9.0):
                a.add_patch(FancyArrowPatch((xa + 0.5, 0.1), (xa - 0.4, 0.1), arrowstyle="-|>", mutation_scale=9,
                                            color="#1b3f73", lw=1.2))
            a.text(5.0, 1.15, "reversed flow to the trailing edge: no reattachment", fontsize=9.5, color="#1b3f73",
                   ha="center")
            cf = np.where(x < 0.6, 2.5 - 2.5 * x / 0.6, -0.6 + 0.0 * x)
        else:
            lam = 0.35 * np.sqrt(x / 10 + 1e-6) * 2
            if bubble:
                S, R = bubble
                u = np.clip((x - S) / (R - S), 0, 1)
                inner = np.where((x >= S) & (x <= R), 0.22 * np.sin(np.pi * u), np.nan)
                a.fill_between(x, 0, inner, where=~np.isnan(inner), color="#9cb8e0", alpha=0.9)
                a.add_patch(FancyArrowPatch((S + 1.0, 0.07), (S + 0.3, 0.07), arrowstyle="-|>", mutation_scale=8,
                                            color="#1b3f73", lw=1.1))
                edge_r = 0.35 * np.sqrt(R / 10) * 2 + 0.25
                edge = np.where(x < R, lam + 0.25 * u, edge_r + 0.06 * (x - R))
                a.text((S + R) / 2, 0.75, "bubble", fontsize=9.5, color="#1b3f73", ha="center")
                cf = np.where(x < S, 2.4 * np.exp(-x / 2.5) + 0.2, np.where(x < R, -0.35 * np.sin(np.pi * u), 3.2))
                cf = np.where((x >= R) & (x < R + 0.6), 3.2 * (x - R) / 0.6, cf)
            else:
                edge = np.where(x < xt, lam, lam + 0.09 * (x - xt))
                cf = np.where(x < xt, 2.4 * np.exp(-x / 2.5) + 0.2, 3.4 - 0.05 * (x - xt))
                cf = np.where((x >= xt) & (x < xt + 0.8), 0.2 + 2.4 * np.exp(-xt / 2.5) + 3.0 * (x - xt) / 0.8, cf)
                a.text(xt, 1.05, "transition", fontsize=9.5, color=ACCENT, ha="center")
                a.plot([xt], [0], "o", color=ACCENT, ms=6)
            a.text(1.5, 0.95, "laminar", fontsize=9.5, ha="center")
            a.text(8.8, 0.95, "turbulent", fontsize=9.5, ha="center")
        a.plot(x, edge, color=MUTED, lw=1, ls=(0, (4, 2)))
        a.set(xlim=(0, 10), ylim=(-0.3, 1.3))
        a.set_title(title, fontsize=11, loc="left")
        a.axis("off")
        b.plot(x, cf, color=INK, lw=1.5)
        b.axhline(0, color=MUTED, lw=0.8)
        b.fill_between(x, cf, 0, where=cf < 0, color="#9cb8e0", alpha=0.9)
        b.set(xlim=(0, 10), ylim=(-1, 4), yticks=[0], yticklabels=["$C_f$ = 0"], xticks=[])
        b.grid(False)
        b.spines["bottom"].set_visible(False)
    axs[-1].set_xlabel("along the suction side →  (schematic, not computed)")
    return _save(fig, out)


def thistle_xfoil_table(data: Path, out: Path) -> Path:
    x = pd.read_csv(data / "thistle-xfoil.csv")

    def f(v):
        return "" if pd.isna(v) else f"{v:+.1f}"

    rows = ["| section | up, Tu 0.1 % | up, 0.5 % | up, 1 % | up, tripped | down, Tu 0.1 % | down, 1 % | down, tripped | CFD |",
            "|---|--:|--:|--:|--:|--:|--:|--:|:-:|"]
    for _, r in x.iterrows():
        rows.append(f"| {r.section} | {f(r['up_tu0.1'])} | {f(r['up_tu0.5'])} | {f(r['up_tu1'])} | {f(r.up_tripped)} | "
                    f"{f(r['down_tu0.1'])} | {f(r.down_tu1)} | {f(r.down_tripped)} | {'yes' if r.group == 'cfd' else ''} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def thistle_short_chord_table(data: Path, out: Path) -> Path:
    """The side note: NACA 00xx on the chord that makes it 1 in thick, against NACA 0006 on 18 in (XFOIL):
    board drag upwind and downwind over XFOIL's four turbulence settings, and the extra leeway at Tu 0.5 %."""
    x = pd.read_csv(data / "thistle-short-chord.csv")
    x = x[x.candidate.str.match(r"naca00\d\d$")]
    rows = ["| section | chord | upwind ΔD | downwind ΔD | extra leeway |", "|---|--:|--:|--:|--:|"]
    for cand, g in sorted(x.groupby("candidate"), key=lambda kv: kv[0]):
        t = int(cand[-2:]) / 100
        up, dn = g["upwind %"], g["downwind %"]
        lee = g.loc[g.file.str.contains("Tu0.5"), "d leeway deg"].iloc[0]
        rows.append(f"| NACA&nbsp;{cand[-4:]} | {1 / t:.1f}&nbsp;in | {up.max():+.0f}&nbsp;to&nbsp;{up.min():+.0f}&nbsp;% | "
                    f"{dn.max():+.0f}&nbsp;to&nbsp;{dn.min():+.0f}&nbsp;% | +{lee:.1f}° |")
    out.write_text("\n".join(rows) + "\n")
    return out


TH_PLAN = {  # the plans-chord check: spec -> (name, thickness on 13 3/16 in)
    "naca0007": ("NACA 0007 (the book)", "0.92&nbsp;in"),
    "naca0006": ("NACA 0006", "0.79&nbsp;in"),
    "naca0007@0.07584": ("NACA 0007 scaled to 1&nbsp;in", "1.00&nbsp;in"),
    "naca0008": ("NACA 0008", "1.06&nbsp;in (over the limit)"),
    "file:naca63-006.dat@0.07584": ("NACA 63-006 at 1&nbsp;in", "1.00&nbsp;in"),
    "file:naca64-006.dat@0.07584": ("NACA 64-006 at 1&nbsp;in", "1.00&nbsp;in"),
    "file:ht35.dat@0.07584": ("HT35 at 1&nbsp;in", "1.00&nbsp;in"),
}


def thistle_plan_chord_table(data: Path, out: Path) -> Path:
    """The correction: sections on the official plans' 13 3/16 in mid-span chord against the book's NACA 0007
    (XFOIL): board drag upwind and downwind over XFOIL's four turbulence settings."""
    x = pd.read_csv(data / "thistle-plan-chord.csv")
    rows = ["| section on 13 3/16 in | thickness | upwind ΔD | downwind ΔD |", "|---|--:|--:|--:|"]
    for spec, (name, thick) in TH_PLAN.items():
        g = x[x.candidate == spec]
        if spec == "naca0007":
            rows.append(f"| **{name}** | {thick} | reference | reference |")
            continue
        def rng(v):
            lo, hi = (int(round(float(z))) for z in (v.min(), v.max()))
            f = (lambda n: f"{n:+d}" if n else "0")
            return (f"{f(lo)}&nbsp;%" if lo == hi else f"{f(lo)}&nbsp;to&nbsp;{f(hi)}&nbsp;%").replace("-", "−")

        rows.append(f"| {name} | {thick} | {rng(g['upwind %'])} | {rng(g['downwind %'])} |")
    out.write_text("\n".join(rows) + "\n")
    return out


def thistle_card(out: Path) -> Path:
    """The page's card at 3:1: NACA 0006 over the plank board, the thickness stretched three times."""
    from iomcfd import sectiondesign as sd

    fig = plt.figure(figsize=(9, 3))
    a = fig.add_axes([0, 0, 1, 1])
    for k, fill in ((TH_BASE, True), ("file:plank-typical.dat", False)):
        u = sd.load(k).surface("upper", 800)
        xs, ys = np.r_[u[:, 0], u[::-1, 0]], 3 * np.r_[u[:, 1], -u[::-1, 1]]
        if fill:
            a.fill(xs, ys, color=ACCENT, alpha=0.85, lw=0)
        else:
            a.plot(xs, ys, color=INK, lw=1.6, ls=(0, (5, 3)))
    a.set_aspect("equal")
    a.set(xlim=(-0.08, 1.08), ylim=(-0.193, 0.193))
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
        sources_table(data, out / "sources.md", keep=lambda n: not n.startswith(("bulb-", "custom-", "thistle-"))),
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
        # the Thistle centreboard page
        thistle_board_side(out / "thistle-board-side.svg"),
        thistle_board_top(out / "thistle-board-top.svg"),
        thistle_grid(data, out / "thistle-grid.svg"),
        thistle_pipeline(out / "thistle-pipeline.svg"),
        thistle_shapes(out / "thistle-shapes.svg"),
        thistle_profiles(out / "thistle-profiles.svg"),
        thistle_noses(out / "thistle-noses.svg"),
        thistle_properties_table(out / "thistle-properties.md"),
        thistle_mesh(out / "thistle-mesh.png"),
        thistle_mesh_study(data, out / "thistle-mesh-study.svg"),
        thistle_validation_drag(data, out / "thistle-validation-drag.svg"),
        thistle_validation_lift(data, out / "thistle-validation-lift.svg"),
        thistle_calibration(data, out / "thistle-calibration.svg"),
        thistle_r824(out / "thistle-r824.svg"),
        thistle_screen(data, out / "thistle-screen.svg"),
        thistle_screen_table(data, out / "thistle-screen.md"),
        thistle_tradeoff(data, out / "thistle-tradeoff.svg"),
        thistle_bounds(data, out / "thistle-bounds.svg"),
        thistle_finalists(data, out / "thistle-finalists.svg"),
        thistle_equal_force(data, out / "thistle-equal-force.svg"),
        thistle_results_table(data, out / "thistle-results.md"),
        thistle_results_detail_table(data, out / "thistle-results-detail.md"),
        thistle_rake_table(data, out / "thistle-rake.md"),
        thistle_bl_schematic(out / "thistle-bl-schematic.svg"),
        thistle_surface(data, out / "thistle-surface-tu03.svg", 0.3),
        thistle_surface(data, out / "thistle-surface-tu06.svg", 0.6),
        thistle_xfoil_table(data, out / "thistle-xfoil.md"),
        thistle_short_chord_table(data, out / "thistle-short-chord.md"),
        thistle_plan_chord_table(data, out / "thistle-plan-chord.md"),
        sources_table(data, out / "sources-thistle.md", keep=lambda n: n.startswith("thistle-")),
        thistle_card(out / "thistle-board-card.png"),
    ]
