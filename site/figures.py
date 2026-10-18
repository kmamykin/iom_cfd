"""Charts, diagrams and generated tables for the website's fin-selection study
(site/fin-selection/index.qmd), and its card image on the front page.

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


def sources_table(data: Path, out: Path) -> Path:
    src = json.loads((data / "sources.json").read_text())
    rows = ["| file | from | exported |", "|---|---|---|"]
    for name, s in src.items():
        if s["kind"] == "manual":
            rows.append(f"| `{s['file']}` | {s['source']} | by hand |")
        else:
            what = s["source"] if isinstance(s["source"], str) else ", ".join(s["source"])
            runs = ", ".join(s["runs"])
            rows.append(f"| `{s['file']}` | {s['study']} run {runs}: `{what}` | {s['exported']} |")
    out.write_text("\n".join(rows) + "\n")
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
        sources_table(data, out / "sources.md"),
        card_image(data.parent / "assets" / "flow-shedding-vorticity.png", out / "fin-selection-card.png"),
    ]
