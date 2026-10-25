"""Custom fin sections: shape families, section properties, XFOIL screening
and race-time ranking against a baseline (projects/foil2d/findings/custom-section.md).

The ranking is methodology.md's race time (iomcfd.racetime), evaluated on
XFOIL polars instead of CFD: XFOIL takes under a second per polar, so whole
families of sections can be compared, and the CFD then checks the few that
matter. Use 0.5 deg angle steps or finer: on a 2 deg grid the linear
interpolation between angles reorders candidates (calibration, findings).

    uv run python -m iomcfd.sectiondesign screen naca0007 naca0007-74 file:ht14.dat@0.07 ...
    uv run python -m iomcfd.sectiondesign export naca0007-74 file:ht14.dat@0.07 ...

A section spec is any foils.load spec, optionally '@t' to scale its
thickness to t (fraction of chord), 'cst:a0,a1,...[@t]' (cst_symmetric), or
'parallel:t=..,le=..,te=..,r=..,a=..' (parallel_sided, a dinghy-board plank
section). The Thistle centreboard ranking (drag at equal side force on a
raked board, no race time) is iomcfd.boardrank, built on these tools.
"""

from __future__ import annotations

import argparse
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from iomcfd import config, racetime, xfoil
from iomcfd.geometry import foils
from iomcfd.geometry.foils import Foil
from iomcfd.physics import fresh_water

DESIGN_DIR = Path(__file__).resolve().parents[2] / "projects" / "foil2d" / "design"
ANGLES = np.round(np.arange(0.0, 8.01, 0.5), 2)
DESIGN_ANGLES = np.round(np.arange(0.0, 7.01, 0.5), 2)  # the loads need up to about 6 deg; XFOIL hangs past 7 at Tu 0.1 %


# --------------------------------------------------------------------------
# Shape families


def _symmetric(name: str, x: np.ndarray, y: np.ndarray) -> Foil:
    return foils._from_surfaces(name, x, y, x, -y)


def scaled(foil: Foil, t: float, name: str | None = None) -> Foil:
    """The section with every ordinate scaled so its maximum thickness is t."""
    t0 = foil.thickness()[0]
    return Foil(name or f"{foil.name} t={t:g}", foil.x.copy(), foil.y * (t / t0))


def cst_symmetric(coeffs, t: float | None = None, n: int = 400, name: str | None = None) -> Foil:
    """Symmetric CST section (Kulfan 2008): half-thickness
    sqrt(x) (1-x) sum_i A_i C(N,i) x^i (1-x)^(N-i), N = len(coeffs) - 1.
    A_0 sets the leading-edge radius (r = A_0^2 / 2), A_N the trailing-edge
    wedge angle (tan = A_N). Scaled to thickness t if given."""
    a = np.asarray(coeffs, float)
    N = len(a) - 1
    x = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
    shape = sum(a[i] * math.comb(N, i) * x**i * (1 - x) ** (N - i) for i in range(N + 1))
    y = np.sqrt(x) * (1 - x) * shape
    f = _symmetric(name or "CST " + ",".join(f"{v:.4g}" for v in a), x, y)
    return scaled(f, t, f.name) if t else f


def cst_fit(x, y, r_le: float, dydx=None, n: int = 12, w_slope: float = 0.05) -> np.ndarray:
    """CST coefficients (cst_symmetric, order n) of a tabulated half-thickness
    y(x) with the leading-edge radius held at r_le (A_0 = sqrt(2 r_le)): least
    squares on the ordinates and, where given (not nan), on the slopes dydx
    weighted by w_slope. For published tables such as NACA Report 824's, whose
    26 stations are too few for a spline to keep the nose radius."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = (x > 0) & (x < 1)
    x, y = x[m], y[m]

    def basis(xx):
        return np.stack([math.comb(n, i) * xx**i * (1 - xx) ** (n - i) * np.sqrt(xx) * (1 - xx) for i in range(n + 1)], 1)

    A, b = basis(x), y
    if dydx is not None:
        d = np.asarray(dydx, float)[m]
        k = ~np.isnan(d)
        h = 1e-7
        A = np.vstack([A, w_slope * (basis(x[k] + h) - basis(x[k] - h)) / (2 * h)])
        b = np.concatenate([b, w_slope * d[k]])
    a0 = math.sqrt(2 * r_le)
    rest = np.linalg.lstsq(A[:, 1:], b - A[:, 0] * a0, rcond=None)[0]
    return np.concatenate([[a0], rest])


def _bezier(p, w, s: np.ndarray) -> np.ndarray:
    """Points of the rational Bézier curve with control points p (k x 2) and
    weights w at the parameters s."""
    n = len(p) - 1
    b = np.stack([w[i] * math.comb(n, i) * s**i * (1 - s) ** (n - i) for i in range(n + 1)], 1)
    return (b @ np.asarray(p, float)) / b.sum(1, keepdims=True)


def parallel_sided(t: float, le: float = 0.2, te: float = 0.4, r: float = 0.1, a: float = 1.0, n: int = 200,
                   name: str | None = None) -> Foil:
    """Parallel-sided section of Saporito, Persson, Larsson & Mancuso (2020,
    J. Mar. Sci. Eng. 8(9) 677, appendix A), the shape of many dinghy boards
    cut from a plank: a nose of length `le` (rational cubic Bézier, leading-edge
    radius r*t), a flat of thickness t, and a tail of length `te` (quartic
    Bézier) to a sharp trailing edge, each joined G2 to the flat. The tail's
    half-angle at the trailing edge is `a` times A_REF = arctan(1.5 t / te),
    the paper's reference (a = 1, 0.8 ... 0.2 are its A1-A5). Lengths are
    fractions of the chord."""
    if not (0 < le and 0 < te and le + te <= 1 and r > 0 and 0 < a <= 1):
        raise ValueError(f"parallel-sided section: needs le, te > 0, le + te <= 1, r > 0, 0 < a <= 1 "
                         f"(got le={le}, te={te}, r={r}, a={a})")
    h = t / 2
    s = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
    x2 = 2 * le / 3
    w1 = math.sqrt(2 * r * t * x2 / (3 * h**2))  # sets the curvature at the leading edge to 1 / (r t)
    nose = _bezier([[0, 0], [0, h], [x2, h], [le, h]], [1, w1, 1, 1], s)
    x7 = 2 * te / 3
    ang = a * math.atan(1.5 * t / te)
    tail = _bezier([[0, h], [te / 5, h], [te / 2.5, h], [x7, (te - x7) * math.tan(ang)], [te, 0]], np.ones(5), s)
    tail[:, 0] += 1 - te
    flat = np.linspace(le, 1 - te, max(3, int(round((1 - te - le) / 0.005)) + 1))[1:-1]
    x = np.concatenate([nose[:, 0], flat, tail[:, 0]])
    y = np.concatenate([nose[:, 1], np.full_like(flat, h), tail[:, 1]])
    return _symmetric(name or f"parallel t={t:g} le={le:g} te={te:g} r={r:g} a={a:g}", x, y)


def load(spec: str) -> Foil:
    """foils.load spec, 'cst:a0,a1,...' or 'parallel:t=..,le=..,te=..,r=..,a=..'
    (parallel_sided), the first two optionally '@t' (scale to t)."""
    base, _, t = spec.partition("@")
    if base.startswith("cst:"):
        f = cst_symmetric([float(v) for v in base[4:].split(",")])
    elif base.startswith("parallel:"):
        kw = {k.strip(): float(v) for k, v in (item.split("=") for item in base[9:].split(","))}
        return parallel_sided(name=spec, **kw)
    else:
        f = foils.load(base, [config.geometry_dir() / "foils"])
    return scaled(f, float(t), spec) if t else f


# --------------------------------------------------------------------------
# Properties


def properties(foil: Foil) -> dict[str, float]:
    """Thickness and position; leading-edge radius, also as a multiple of the
    NACA 4-digit one at the same thickness (1.1019 t^2); trailing-edge
    included angle [deg]; bending second moments per chord^4 about the chord
    line: solid section (2/3) int y^3 dx, and thin skin int y^2 ds (a skin of
    constant thickness over a core)."""
    t, xt = foil.thickness()
    dx, dy = (float(v) for v in foil._eval(np.array(foil.s_le), 1))
    ddx, ddy = (float(v) for v in foil._eval(np.array(foil.s_le), 2))
    r_le = (dx**2 + dy**2) ** 1.5 / abs(dx * ddy - dy * ddx)
    up = foil.surface("upper", 801)
    x, y = up[:, 0], np.maximum(up[:, 1], 0.0)
    te = up[x > 0.995]
    slope = np.polyfit(te[:, 0], te[:, 1], 1)[0]
    ds = np.hypot(np.diff(x), np.diff(y))
    ym = 0.5 * (y[1:] + y[:-1])
    return {"t": t, "x_t": xt, "r_le": r_le, "r_le_rel": r_le / (1.1019 * t**2), "te_angle": float(np.degrees(2 * math.atan(-slope))),
            "i_solid": float(2 / 3 * np.sum(ym**3 * np.abs(np.diff(x)))), "i_skin": float(2 * np.sum(ym**2 * ds))}


# --------------------------------------------------------------------------
# XFOIL polars and ranking


def xfoil_table(sections: dict[str, Foil], chord: float, speeds, tus, angles=ANGLES, nu: float | None = None,
                threads: int = 8, panels: int = 220, xtr: tuple[float, float] | None = None) -> pd.DataFrame:
    """XFOIL polars of every section at every speed and Tu, one row per
    converged angle: candidate, chord, speed, Tu, Re, aoa, Cl, Cd, Cdp,
    xtr_top, xtr_bot. `xtr` forces transition (xfoil.polar)."""
    nu = nu if nu is not None else fresh_water(15.0).nu
    jobs = [(name, f, v, tu) for name, f in sections.items() for v in speeds for tu in tus]

    def run(job):
        name, f, v, tu = job
        re = v * chord / nu
        p = xfoil.polar(f, re, angles, ncrit=xfoil.ncrit_from_tu(tu), panels=panels, xtr=xtr)
        return pd.DataFrame({"candidate": name, "chord": chord, "speed": v, "Tu": tu, "Re": re, "aoa": p.alpha,
                             "Cl": p.cl, "Cd": p.cd, "Cdp": p.cdp, "xtr_top": p.xtr_top, "xtr_bot": p.xtr_bot})

    with ThreadPoolExecutor(threads) as ex:
        parts = list(ex.map(run, jobs))
    return pd.concat(parts, ignore_index=True)


def design_loads() -> pd.DataFrame:
    """The comparison side forces (speed, load, force [N]): what NACA 0009 at
    80 mm makes at 2, 4 and 6 deg in the steady CFD at Tu 0.1 %, as in the
    fin-profile-selection rankings (projects/foil2d/design/loads.csv)."""
    return pd.read_csv(DESIGN_DIR / "loads.csv", comment="#")


def rank(df: pd.DataFrame, baseline: str, loads: pd.DataFrame | None = None, slope_factors=(1.0, 2.0),
         course: racetime.Course | None = None) -> pd.DataFrame:
    """Race-time loss of every candidate against `baseline`, in % of race
    time (negative = faster than the baseline), per Tu, slope factor, speed
    and load. Columns: candidate, Tu, slope, speed, load, aoa, drag_up,
    drag_0, vs_base."""
    loads = loads if loads is not None else design_loads()
    course = course or racetime.Course()
    out = []
    for tu, g in df.groupby("Tu"):
        forces = racetime.fin_forces(g, course)
        for sf in slope_factors:
            c = racetime.Course(course.span, course.e, course.track_deg, course.vdrdv, sf)
            rt = racetime.race_time(forces, loads[loads["speed"].isin(g["speed"].unique())], c)
            base = rt[rt["candidate"] == baseline].set_index(["speed", "load"])["loss_abs"]
            rt["vs_base"] = rt["loss_abs"] - base.reindex(list(zip(rt["speed"], rt["load"]))).to_numpy()
            out.append(rt.assign(Tu=tu, slope=sf))
    return pd.concat(out, ignore_index=True)


def rank_summary(rk: pd.DataFrame) -> pd.DataFrame:
    """Mean race-time gain against the baseline per candidate and variant
    (Tu, slope), the worst variant, and the worst single point."""
    v = rk.pivot_table(index="candidate", columns=["Tu", "slope"], values="vs_base", aggfunc="mean")
    v.columns = [f"Tu{tu:g} x{sf:g}" for tu, sf in v.columns]
    v["worst variant"] = v.max(axis=1)
    v["worst point"] = rk.groupby("candidate")["vs_base"].max()
    v["missing"] = rk.groupby("candidate")["vs_base"].apply(lambda s: int(s.isna().sum()))
    return v.sort_values("worst variant")


def cfd_table(results: list[Path], replace: list[Path] = (), tu: float | None = None, speeds=None,
              turbulence: str | None = None) -> pd.DataFrame:
    """foil2d results.csv files as a polar table (candidate = 'foil/chord mm',
    foil, chord, speed, aoa, Cl, Cd, and where the files have them
    Cd_pressure, Cd_friction and `unsteady`). Rows of the `replace` files
    (e.g. time-accurate points) replace the same candidate, speed and angle,
    or add it if the base runs lack it, in order, so a later file wins;
    duplicates within one file are averaged (unsteady if any is). Failed cases
    are dropped; `tu` and `turbulence` (model) select rows."""

    def read(paths):
        d = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
        d = d[d["status"] != "failed"]
        if tu is not None:
            d = d[np.isclose(d["Tu"], tu)]
        if turbulence is not None:
            d = d[d["turbulence"] == turbulence]
        if speeds is not None:
            d = d[d["speed"].isin(speeds)]
        d["candidate"] = [f"{f}/{c * 1000:g}" for f, c in zip(d["foil"], d["chord"])]
        g = d.groupby(["candidate", "foil", "chord", "speed", "aoa"], as_index=False)
        out = g[[c for c in ("Cl", "Cd", "Cd_pressure", "Cd_friction") if c in d]].mean()
        if "unsteady" in d:
            out["unsteady"] = g["unsteady"].agg(lambda s: bool(s.astype(bool).any()))["unsteady"].to_numpy()
        return out

    key = ["candidate", "speed", "aoa"]
    t = read(results)
    for path in replace:  # a replacement also fills a point the base runs lack (e.g. a failed case)
        t = pd.concat([t, read([path])], ignore_index=True).drop_duplicates(key, keep="last")
    return t.sort_values(key, ignore_index=True)


def calibrate(cfd: pd.DataFrame, tu: float, reference: str | None = None, slope_factors=(1.0, 2.0)) -> pd.DataFrame:
    """Race-time ranking of the CFD candidates by the CFD, by XFOIL on the
    CFD's own angles and by XFOIL on 0.5 deg steps, all at the same loads:
    design_loads(), or the forces of the CFD candidate `reference` at 2, 4
    and 6 deg. One column per source and slope factor (mean loss over speeds
    and loads, % of race time behind the best)."""
    cands = cfd[["candidate", "foil", "chord"]].drop_duplicates()
    speeds = sorted(cfd["speed"].unique())
    loads = racetime.loads_from(racetime.fin_forces(cfd), reference) if reference else design_loads()
    xf = []
    for chord, g in cands.groupby("chord"):
        secs = {r.candidate: load(r.foil) for r in g.itertuples()}
        xf.append(xfoil_table(secs, chord, speeds, [tu]))
    xf = pd.concat(xf, ignore_index=True)
    on_cfd = xf[np.isin(np.round(xf["aoa"], 2), np.round(cfd["aoa"].unique(), 2))]
    cols = {}
    for name, df in (("CFD", cfd), ("XFOIL CFD angles", on_cfd), ("XFOIL 0.5 deg", xf)):
        f = racetime.fin_forces(df)
        for sf in slope_factors:
            rt = racetime.race_time(f, loads, racetime.Course(slope_factor=sf))
            cols[f"{name} x{sf:g}"] = racetime.summary(rt)["mean"]
    return pd.DataFrame(cols).sort_values(f"CFD x{slope_factors[0]:g}")


# --------------------------------------------------------------------------
# Optimisation


def stiffness_matched(foil: Foil, ref: dict[str, float], name: str | None = None) -> Foil:
    """The section scaled (all ordinates) to the smallest thickness at which
    both its bending second moments, solid and skin, are at least the
    reference's (properties())."""
    f = foil
    for _ in range(4):
        p = properties(f)
        k = max((ref["i_solid"] / p["i_solid"]) ** (1 / 3), (ref["i_skin"] / p["i_skin"]) ** 0.5)
        if abs(k - 1) < 1e-4:
            break
        f = scaled(f, p["t"] * k, name or f.name)
    return f


def cst_coeffs(foil: Foil, n: int = 5) -> np.ndarray:
    """Least-squares CST coefficients (cst_symmetric) of a symmetric section."""
    up = foil.surface("upper", 400)
    x, y = up[:, 0], up[:, 1]
    m = (x > 0.005) & (x < 0.995)
    x, y = x[m], y[m]
    B = np.stack([math.comb(n, i) * x**i * (1 - x) ** (n - i) for i in range(n + 1)], 1) * (np.sqrt(x) * (1 - x))[:, None]
    return np.linalg.lstsq(B, y, rcond=None)[0]


class Objective:
    """Race-time objective of a CST section, for a minimiser.

    The design vector is A_1..A_N / A_0 of cst_symmetric; the section is
    then scaled to the baseline's bending stiffness (stiffness_matched), so
    thickness is not free: a section with its thickness further forward
    needs a little more of it. Value: the race-time loss against the
    baseline (XFOIL both), averaged over speeds and loads, worst of the
    Tu and resistance-slope variants; plus penalties, each a full percent of
    race time or more, for a nose sharper than the baseline's (XFOIL misses
    the leading-edge bubble the CFD finds there), more than one thickness
    maximum, a trailing-edge angle outside `te_min`-`te_max` deg, the maximum thickness
    outside `xt_range`, and side forces XFOIL couldn't reach. Every call is
    logged in `self.log`."""

    def __init__(self, baseline: str = "naca0007", chord: float = 0.10, speeds=(0.75, 1.0, 1.5), tus=(0.1, 1.0),
                 slope_factors=(1.0, 2.0), te_min: float = 4.0, te_max: float = 90.0, xt_range=(0.18, 0.45)):
        self.baseline, self.chord, self.speeds, self.tus = baseline, chord, list(speeds), list(tus)
        self.slope_factors, self.te_min, self.te_max, self.xt_range = slope_factors, te_min, te_max, xt_range
        base = load(baseline)
        self.ref = properties(base)
        self.base_df = xfoil_table({baseline: base}, chord, self.speeds, self.tus, DESIGN_ANGLES)
        self.log: list[dict] = []

    def section(self, z, name: str = "design") -> Foil:
        return stiffness_matched(cst_symmetric([1.0, *z]), self.ref, name)

    def penalties(self, f: Foil, p: dict[str, float]) -> float:
        up = f.surface("upper", 400)
        dy = np.diff(up[:, 1])
        bumps = int(np.sum(np.diff(np.sign(dy[np.abs(dy) > 1e-9])) != 0))  # sign changes of the slope
        pen = 0.0
        pen += 100 * max(0.0, 1 - p["r_le"] / self.ref["r_le"])
        pen += 2.0 * max(0, bumps - 1)
        pen += 0.5 * max(0.0, self.te_min - p["te_angle"], p["te_angle"] - self.te_max)
        pen += 20 * max(0.0, self.xt_range[0] - p["x_t"], p["x_t"] - self.xt_range[1])
        return pen

    def evaluate(self, z) -> dict:
        f = self.section(z)
        p = properties(f)
        rec = {**{f"z{i + 1}": float(v) for i, v in enumerate(z)}, **p, "penalty": self.penalties(f, p)}
        if rec["penalty"] > 1.0:  # far outside: don't spend XFOIL time on it
            rec["value"] = 5.0 + rec["penalty"]
            return rec
        df = pd.concat([self.base_df, xfoil_table({"design": f}, self.chord, self.speeds, self.tus, DESIGN_ANGLES,
                                                  threads=1)])
        rk = rank(df, self.baseline, slope_factors=self.slope_factors)
        d = rk[rk["candidate"] == "design"]
        missing = int(d["vs_base"].isna().sum())
        var = d.groupby(["Tu", "slope"])["vs_base"].mean()
        for (tu, sf), v in var.items():
            rec[f"Tu{tu:g} x{sf:g}"] = float(v)
        rec["missing"] = missing
        rec["value"] = float(var.max()) + rec["penalty"] + 1.0 * missing if len(var) else 5.0 + rec["penalty"]
        return rec

    def __call__(self, z) -> float:
        rec = self.evaluate(np.asarray(z, float))
        self.log.append(rec)
        return rec["value"]


def optimise(obj: Objective, x0: list[np.ndarray], bounds, popsize: int = 12, maxiter: int = 40, seed: int = 1,
             threads: int = 8):
    """Differential evolution over the CST shape ratios, starting from a
    population that includes the given sections' fits (x0)."""
    from scipy.optimize import differential_evolution

    rng = np.random.default_rng(seed)
    lo, hi = np.array(bounds).T
    n = popsize * len(bounds)
    init = rng.uniform(lo, hi, size=(n, len(bounds)))
    init[: len(x0)] = np.clip(np.array(x0), lo, hi)
    with ThreadPoolExecutor(threads) as ex:
        res = differential_evolution(obj, bounds, init=init, maxiter=maxiter, seed=seed, polish=False,
                                     updating="deferred", workers=ex.map, tol=1e-4)
    return res


# --------------------------------------------------------------------------
# Figure


def polar_figure(df: pd.DataFrame, path: Path, loads: pd.DataFrame | None = None, title: str | None = None,
                 course: racetime.Course | None = None) -> Path:  # pragma: no cover - plotting
    """Whole-fin drag D_h (section + induced) against side force S_h, one
    panel per speed, one line per candidate (cfd_table rows, Cl and Cd), with
    the comparison loads as vertical lines; below, each candidate's D_h as %
    above or below the first candidate's at the same S_h (linear along each
    pre-stall branch). Lower is better."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    loads = loads if loads is not None else design_loads()
    f = racetime.fin_forces(df, course)
    speeds = sorted(f["speed"].unique())
    cands = list(dict.fromkeys(f["candidate"]))
    colors = ["#9aa5b1", "#d1495b", "#0b4f9c", "#3c9d5d", "#e0a030"]
    fig, axs = plt.subplots(2, len(speeds), figsize=(4.6 * len(speeds), 7.6), squeeze=False,
                            gridspec_kw={"height_ratios": [1.3, 1]})

    def branch(g):
        idx = racetime.prestall_branch(g["aoa"].to_numpy(), g["side_force"].to_numpy())
        return g["side_force"].to_numpy()[idx], g["drag"].to_numpy()[idx]

    for j, v in enumerate(speeds):
        ax, ax2 = axs[0, j], axs[1, j]
        sel = {c: f[(f["candidate"] == c) & np.isclose(f["speed"], v)].sort_values("aoa") for c in cands}
        sf0, d0 = branch(sel[cands[0]])
        for k, c in enumerate(cands):
            g = sel[c]
            lab = c.removeprefix("file:").replace(".dat", "")
            ax.plot(g["side_force"], g["drag"], "o-", ms=3.5, color=colors[k % len(colors)], label=lab)
            sf, d = branch(g)
            grid = np.linspace(max(sf0[0], sf[0]), min(sf0[-1], sf[-1]), 200)
            ax2.plot(grid, 100 * (np.interp(grid, sf, d) / np.interp(grid, sf0, d0) - 1), color=colors[k % len(colors)])
        for a in (ax, ax2):
            for _, ld in loads[np.isclose(loads["speed"], v)].iterrows():
                a.axvline(ld["force"], color="0.6", lw=0.8, ls=":")
            a.grid(alpha=0.3)
        for _, ld in loads[np.isclose(loads["speed"], v)].iterrows():
            ax.text(ld["force"], ax.get_ylim()[1], f"{ld['load']} ", rotation=90, va="top", ha="right", fontsize=7,
                    color="0.4")
        ax.set_title(f"V_b = {v:g} m/s", fontsize=10)
        ax.set_ylabel("drag D_h [N]")
        ax2.set_xlabel("side force S_h [N]")
        ax2.set_ylabel(f"D_h vs {cands[0].removeprefix('file:').replace('.dat', '')} [%]")
    axs[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle(title or "Whole fin, drag against side force (lower is better)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def section_figure(spec: str, compare: list[str], path: Path, chord: float = 0.10,
                   title: str | None = None) -> Path:  # pragma: no cover - plotting
    """One sheet for a section: at true scale, its upper surface against the
    `compare` sections (vertical scale stretched), close-ups of the nose and
    the tail, and a thickness table against the first of `compare`, whose
    bending stiffness it is also compared with. Lengths in mm at `chord`."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    C = chord * 1000
    names = [spec, *compare]
    secs = {sp: load(sp) for sp in names}
    def nice(sp: str) -> str:  # 'file:ht35.dat@0.0725' -> 'ht35 @ 7.25 %'
        base, _, t = sp.removeprefix("file:").partition("@")
        base = base.removesuffix(".dat")
        return f"{base} @ {float(t) * 100:g} %" if t else base

    label = {sp: nice(sp) for sp in names}
    colors = dict(zip(names, ["#0b4f9c", "#9aa5b1", "#d1495b", "#3c9d5d", "#e0a030"]))
    width = {sp: 2.2 if sp == spec else 1.4 for sp in names}
    p = properties(secs[spec])
    ref_name = compare[0] if compare else spec
    ref = properties(secs[ref_name])

    def sides(f):
        return f.surface("upper", 800) * C, f.surface("lower", 800) * C

    fig = plt.figure(figsize=(13, 9.5))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.25, 1.25], hspace=0.5, wspace=0.18)
    ax = fig.add_subplot(gs[0, :])
    up, lo = sides(secs[spec])
    xy = np.vstack([up[::-1], lo[1:]])
    ax.fill(xy[:, 0], xy[:, 1], color=colors[spec], alpha=0.85)
    ax.set_aspect("equal")
    ax.set_xlim(-0.02 * C, 1.02 * C)
    ax.set_ylim(-0.06 * C, 0.06 * C)
    ax.set_title(f"{label[spec]} at true scale, {C:g} mm chord", loc="left", fontsize=12)
    ax.set_xlabel("mm")
    ax.grid(alpha=0.25)
    ax.annotate(f"max {p['t'] * C:.2f} mm at {p['x_t'] * C:.0f} mm", xy=(p["x_t"] * C, p["t"] * C / 2),
                xytext=(0.4 * C, 0.05 * C), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=9)
    ax2 = fig.add_subplot(gs[1, :])
    for sp, f in secs.items():
        up, _ = sides(f)
        ax2.plot(up[:, 0], up[:, 1], color=colors[sp], lw=width[sp], label=label[sp])
    ax2.set_title("upper surface (half-thickness), vertical scale stretched", loc="left", fontsize=11)
    ax2.set_xlabel("x [mm]")
    ax2.set_ylabel("y [mm]")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=9, loc="upper right")
    vs = f" ({label[ref_name]} " if compare else " ("
    windows = [(-0.003 * C, 0.06 * C, f"nose: r = {p['r_le'] * C:.2f} mm{vs}{ref['r_le'] * C:.2f} mm)"),
               (0.8 * C, 1.005 * C, f"tail: trailing-edge angle {p['te_angle']:.1f}°{vs}{ref['te_angle']:.1f}°)")]
    for k, (x0, x1, ttl) in enumerate(windows):
        a = fig.add_subplot(gs[2, k])
        for sp, f in secs.items():
            for s in sides(f):
                m = (s[:, 0] >= x0 - 0.01 * C) & (s[:, 0] <= x1 + 0.01 * C)
                a.plot(s[m, 0], s[m, 1], color=colors[sp], lw=width[sp])
        a.set_aspect("equal")
        a.set_xlim(x0, x1)
        a.set_ylim(-0.022 * C, 0.022 * C)
        a.grid(alpha=0.3)
        a.set_title(ttl, loc="left", fontsize=10)
        a.set_xlabel("x [mm]")
    xs = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90])
    lines = ["thickness [mm] at x =  " + "  ".join(f"{x * C:4.0f}" for x in xs)]
    for sp in dict.fromkeys([spec, ref_name]):
        t = np.interp(xs, *secs[sp].surface("upper", 800).T) * 2 * C
        lines.append(f"  {label[sp]:<20s}" + "  ".join(f"{v:4.2f}" for v in t))
    if compare:
        lines.append(f"bending stiffness against {label[ref_name]}: solid {p['i_solid'] / ref['i_solid']:.3f}, "
                     f"skin {p['i_skin'] / ref['i_skin']:.3f}")
    fig.text(0.07, 0.0, "\n".join(lines), family="monospace", fontsize=8.5)
    fig.suptitle(title or f"{label[spec]}, {p['t'] * 100:.2f} % thick", fontsize=13, x=0.07, ha="left")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Command line


def _main(argv=None) -> None:  # pragma: no cover - thin CLI
    ap = argparse.ArgumentParser(prog="python -m iomcfd.sectiondesign", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="XFOIL race-time ranking of sections against a baseline")
    s.add_argument("specs", nargs="+")
    s.add_argument("--baseline", default="naca0007")
    s.add_argument("--chord", type=float, default=0.10)
    s.add_argument("--speeds", type=float, nargs="+", default=[0.75, 1.0, 1.5])
    s.add_argument("--tu", type=float, nargs="+", default=[0.1, 1.0])
    s.add_argument("--out", type=Path, default=None, help="directory for polars.csv, rank.csv, summary.csv")
    c = sub.add_parser("calibrate", help="does XFOIL rank CFD candidates as the CFD does? (race time)")
    c.add_argument("results", nargs="+", type=Path, help="foil2d results.csv files")
    c.add_argument("--replace", nargs="*", type=Path, default=[], help="results.csv whose points replace (transient)")
    c.add_argument("--tu", type=float, required=True)
    c.add_argument("--speeds", type=float, nargs="+", default=[0.75, 1.0, 1.5])
    c.add_argument("--reference", help="CFD candidate whose 2/4/6 deg forces are the loads (default: design loads)")
    r = sub.add_parser("cfd", help="race-time ranking of a finished foil2d run against a baseline candidate")
    r.add_argument("results", nargs="+", type=Path, help="foil2d results.csv files")
    r.add_argument("--replace", nargs="*", type=Path, default=[], help="results.csv whose points replace (transient)")
    r.add_argument("--baseline", default="naca0007/100", help="candidate label 'foil/chord mm'")
    r.add_argument("--tu", type=float, default=0.1)
    r.add_argument("--speeds", type=float, nargs="+", default=[0.75, 1.0, 1.5])
    r.add_argument("--angles", type=float, nargs="*", help="use only these angles (e.g. 0 2 4 6: the coarse grid)")
    r.add_argument("--only", nargs="*", help="rank only these candidates ('foil/chord mm'; the baseline is added)")
    r.add_argument("--figure", type=Path, help="also draw drag against side force per speed (PNG)")
    r.add_argument("--title", help="the figure's title")
    o = sub.add_parser("optimise", help="differential evolution of a CST section against the baseline (XFOIL)")
    o.add_argument("--start", nargs="+", default=["naca0007", "file:ht35.dat@0.07", "file:ht34.dat@0.07"],
                   help="sections whose CST fits seed the population")
    o.add_argument("--baseline", default="naca0007")
    o.add_argument("--chord", type=float, default=0.10)
    o.add_argument("--order", type=int, default=5, help="CST order N (N free shape ratios)")
    o.add_argument("--bounds", type=float, nargs=2, default=[0.3, 1.6], help="range of every ratio A_i / A_0")
    o.add_argument("--popsize", type=int, default=12)
    o.add_argument("--maxiter", type=int, default=40)
    o.add_argument("--seed", type=int, default=1)
    o.add_argument("--te-min", type=float, default=4.0, help="smallest trailing-edge angle [deg]")
    o.add_argument("--te-max", type=float, default=90.0, help="largest trailing-edge angle [deg]")
    o.add_argument("--out", type=Path, default=None, help="default: runs/section-design/<UTC time>/")
    e = sub.add_parser("export", help="write sections as Selig .dat files (default geometry/foils/)")
    e.add_argument("specs", nargs="+")
    e.add_argument("--names", nargs="+", help="file names (default: derived from the spec)")
    e.add_argument("--dir", type=Path, default=None)
    g = sub.add_parser("figure", help="one sheet for a section, against others (PNG)")
    g.add_argument("spec")
    g.add_argument("--compare", nargs="*", default=["naca0007"], help="sections to draw with it; the first is "
                   "the reference for the thickness table and stiffness")
    g.add_argument("--chord", type=float, default=0.10)
    g.add_argument("--title")
    g.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    if a.cmd == "screen":
        specs = list(dict.fromkeys([a.baseline, *a.specs]))
        sections = {sp: load(sp) for sp in specs}
        props = pd.DataFrame({sp: properties(f) for sp, f in sections.items()}).T
        ref = props.loc[a.baseline]
        props["i_solid_rel"], props["i_skin_rel"] = props["i_solid"] / ref["i_solid"], props["i_skin"] / ref["i_skin"]
        df = xfoil_table(sections, a.chord, a.speeds, a.tu)
        rk = rank(df, a.baseline)
        summ = rank_summary(rk).join(props[["t", "x_t", "r_le_rel", "te_angle", "i_solid_rel", "i_skin_rel"]])
        pd.set_option("display.width", 200)
        print(summ.round(3).to_string())
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            df.to_csv(a.out / "polars.csv", index=False)
            rk.to_csv(a.out / "rank.csv", index=False)
            summ.to_csv(a.out / "summary.csv")
    elif a.cmd == "calibrate":
        cfd = cfd_table(a.results, a.replace, a.tu, a.speeds)
        cal = calibrate(cfd, a.tu, a.reference)
        pd.set_option("display.width", 200)
        print(cal.round(2).to_string())
        print("\nSpearman rank correlation with the CFD (first column):")
        print(cal.corr(method="spearman").iloc[0].round(2).to_string())
    elif a.cmd == "cfd":
        df = cfd_table(a.results, a.replace, a.tu, a.speeds).assign(Tu=a.tu)
        if a.angles:
            df = df[np.isin(np.round(df["aoa"], 2), np.round(a.angles, 2))]
        if a.only:
            df = df[df["candidate"].isin([a.baseline, *a.only])]
        rk = rank(df, a.baseline)
        if a.figure:
            order = [a.baseline, *(a.only or [c for c in df["candidate"].unique() if c != a.baseline])]
            df["_o"] = df["candidate"].map({c: i for i, c in enumerate(order)})
            print(polar_figure(df.sort_values(["_o", "speed", "aoa"]).drop(columns="_o"), a.figure, title=a.title))
        pd.set_option("display.width", 200)
        print(rank_summary(rk).round(2).to_string())
        per = rk[rk["slope"] == 1.0].pivot_table(index="candidate", columns="speed", values="vs_base", aggfunc="mean")
        print("\nby speed (slope x1, mean over loads):")
        print(per.round(2).to_string())
    elif a.cmd == "optimise":
        import json
        from datetime import datetime, timezone

        out = a.out or config.runs_dir() / "section-design" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out.mkdir(parents=True, exist_ok=True)
        obj = Objective(a.baseline, a.chord, te_min=a.te_min, te_max=a.te_max)
        x0 = []
        for sp in a.start:
            c = cst_coeffs(load(sp), a.order)
            x0.append(c[1:] / c[0])
        bounds = [tuple(a.bounds)] * a.order
        res = optimise(obj, x0, bounds, a.popsize, a.maxiter, a.seed)
        log = pd.DataFrame(obj.log)
        log.to_csv(out / "evaluations.csv", index=False)
        best = obj.evaluate(res.x)
        (out / "result.json").write_text(json.dumps({"args": {k: str(v) for k, v in vars(a).items()},
                                                     "x": list(map(float, res.x)), "best": best,
                                                     "nfev": int(res.nfev), "message": str(res.message)}, indent=2))
        print(json.dumps(best, indent=2))
        print(f"wrote {out}")
    elif a.cmd == "export":
        d = a.dir or config.geometry_dir() / "foils"
        d.mkdir(parents=True, exist_ok=True)
        names = a.names or [sp.replace("file:", "").replace(".dat", "").replace("@", "-t") for sp in a.specs]
        for sp, nm in zip(a.specs, names):
            f = load(sp)
            p = properties(f)
            path = d / f"{nm}.dat"
            f.name = f"{nm} (from '{sp}': t {p['t'] * 100:.2f} % at x/c {p['x_t']:.2f}, r_LE {p['r_le_rel']:.2f} x NACA)"
            f.write_dat(path, n=201, digits=10)
            print(f"wrote {path}: {p['t'] * 100:.2f} % thick")
    elif a.cmd == "figure":
        print(section_figure(a.spec, a.compare, a.out, a.chord, a.title))


if __name__ == "__main__":  # pragma: no cover
    _main()
