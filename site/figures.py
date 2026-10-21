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
    s = pd.read_csv(data / "surface-0007-100-4deg.csv")
    s = s[s.upper.astype(str) == "True"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.4, 3.3))
    for name, colour, label in (("speed0.75", "#2f5d50", "0.75 m/s: sheds from mid-chord"),
                                ("speed1.5", ACCENT, "1.5 m/s: leading-edge bubble, then attached")):
        g = s[s.file.str.contains(name)].sort_values("x_c")
        a.plot(g.x_c, -g.Cp, color=colour, label=label)
        b.plot(g.x_c, g.Cf, color=colour)
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
        sources_table(data, out / "sources.md", keep=lambda n: not n.startswith("bulb-")),
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
    ]
