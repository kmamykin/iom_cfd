"""Section ranking for a raked centreboard: the Thistle study
(projects/foil2d/methodology-thistle.md, findings/thistle-board.md).

The CFD and XFOIL solve the board's own section in its normal plane: chord c
square to the leading edge, at the normal velocity V_n = V_b cos L, L the
rake (simple sweep theory). The whole board's forces at boat speed V_b then
follow for any rake from the same polars, interpolated in log V_n:

    S_h = Cl q cos^2 L c b                    q = rho V_b^2 / 2, b along the leading edge
    D_v = (Cd_p cos^3 L + Cd_f cos L) q c b   friction also from the spanwise flow
    D_i = S_h^2 / (2 pi q e (b cos L)^2)      hull as a reflection plane
    leeway = alpha_n cos L                    the leeway that sets the section angle alpha_n

Sections are ranked upwind first: the board's drag D_h at the light, working
and high side forces (what the baseline makes at the design's load angles,
alpha_n 1, 2 and 4 deg for the Thistle, at the nominal rake, held in N for
every rake and Tu) over the upwind speeds, with
the stall margin past the high load; downwind, the drag at 0 deg and at the
reach load, as tie-break or veto. There is no Thistle resistance curve, so
drag and leeway are reported apart, not as race time.

    uv run python -m iomcfd.boardrank screen file:naca64-006-t0556.dat ... --out runs/section-design/<name>
    uv run python -m iomcfd.boardrank cfd runs/thistle-screen/<run>/results.csv --up-kn 1 3 5 --down-kn 1 3 5 15
    uv run python -m iomcfd.boardrank cfd runs/thistle-screen/<run>/results.csv runs/thistle-extend/<run>/results.csv
"""

from __future__ import annotations

import argparse
import dataclasses
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from iomcfd import racetime, sectiondesign
from iomcfd.physics import fluid, induced_drag

KN = 0.514444  # m/s per knot
LOAD_NAMES = ("light", "working", "high")


@dataclasses.dataclass
class Design:
    """A board and its sailing (projects/foil2d/design/<name>.yaml)."""

    chord: float  # m, square to the leading edge
    thickness: float  # m
    span: float  # m along the leading edge
    rake: float  # deg
    rake_range: tuple[float, ...]
    e: float
    rho: float
    nu: float
    baseline: str
    up_speeds: list[float]  # kn
    load_aoa: list[float]
    stall_min: float  # deg
    down_speeds: list[float]  # kn
    reach_aoa: float
    cfd_speeds_kn: list[float]
    xfoil_tu: list[float]
    xfoil_xtr: float | None
    xfoil_angles: np.ndarray

    @property
    def t_c(self) -> float:
        return self.thickness / self.chord

    @property
    def cfd_speeds(self) -> list[float]:
        """The foil2d `speed` grid [m/s]: V_n at the nominal rake."""
        return [round(normal_speed(v, self.rake), 4) for v in self.cfd_speeds_kn]


def load_design(name: str = "thistle") -> Design:
    path = Path(name) if name.endswith(".yaml") else sectiondesign.DESIGN_DIR / f"{name}.yaml"
    y = yaml.safe_load(path.read_text())
    b, up, dn, xf = y["board"], y["upwind"], y["downwind"], y["xfoil"]
    w = fluid(y["fluid"]["name"], float(y["fluid"]["temperature"]))
    a0, a1, da = xf["angles"]
    return Design(chord=b["chord"], thickness=b["thickness"], span=b["span"], rake=b["rake"],
                  rake_range=tuple(b["rake_range"]), e=b["e"], rho=w.rho, nu=w.nu, baseline=y["baseline"],
                  up_speeds=list(up["speeds_kn"]), load_aoa=list(up["load_aoa"]), stall_min=up["stall_margin_min"],
                  down_speeds=list(dn["speeds_kn"]), reach_aoa=dn["reach_aoa"], cfd_speeds_kn=list(y["cfd"]["speeds_kn"]),
                  xfoil_tu=list(xf["tu"]), xfoil_xtr=xf.get("xtr"),
                  xfoil_angles=np.round(np.arange(a0, a1 + 1e-9, da), 2))


def normal_speed(vb_kn: float, rake: float) -> float:
    """V_n [m/s] square to the leading edge at boat speed vb_kn [kn]."""
    return vb_kn * KN * math.cos(math.radians(rake))


# --------------------------------------------------------------------------
# Polars -> whole board


def at_speed(polars: pd.DataFrame, v: float, max_extrap: float = 0.03) -> pd.DataFrame:
    """The polars (candidate, speed = V_n [m/s], aoa, Cl, Cd, Cdp, Cdf and
    optionally unsteady) at V_n = v: per candidate and angle, Cl linear and
    the drags log-log in V_n between the two nearest speeds that have that
    angle. Beyond the speeds by more than max_extrap of v the point is left
    out."""
    rows = []
    for (cand, a), g in polars.groupby(["candidate", "aoa"]):
        g = g.sort_values("speed")
        sp = g["speed"].to_numpy(float)
        if v < sp[0] * (1 - max_extrap) or v > sp[-1] * (1 + max_extrap):
            continue
        if len(sp) == 1:
            if not math.isclose(v, sp[0], rel_tol=1e-6):
                continue
            k0 = k1 = 0
            w = 0.0
        else:
            k1 = int(np.clip(np.searchsorted(sp, v), 1, len(sp) - 1))
            k0 = k1 - 1
            w = math.log(v / sp[k0]) / math.log(sp[k1] / sp[k0])
        r0, r1 = g.iloc[k0], g.iloc[k1]
        row = {"candidate": cand, "aoa": a, "v_n": v, "Cl": r0["Cl"] + w * (r1["Cl"] - r0["Cl"])}
        for c in ("Cd", "Cdp", "Cdf"):
            lo, hi = float(r0[c]), float(r1[c])
            row[c] = math.exp(math.log(lo) + w * math.log(hi / lo)) if lo > 0 and hi > 0 else lo + w * (hi - lo)
        if "unsteady" in g:
            row["unsteady"] = bool(r0["unsteady"]) or (w != 0.0 and bool(r1["unsteady"]))
        rows.append(row)
    return pd.DataFrame(rows)


def board_forces(polars: pd.DataFrame, d: Design, speeds_kn, rake: float | None = None) -> pd.DataFrame:
    """Whole-board side force, drag (viscous, induced, total) [N] and leeway
    [deg] per candidate, boat speed (`speed`, kn) and section angle, at
    `rake` (default the nominal one)."""
    rake = d.rake if rake is None else rake
    c = math.cos(math.radians(rake))
    out = []
    for vb in speeds_kn:
        p = at_speed(polars, normal_speed(vb, rake))
        if p.empty:
            continue
        q = 0.5 * d.rho * (vb * KN) ** 2
        p["speed"], p["rake"] = vb, rake
        p["side_force"] = p["Cl"] * q * c**2 * d.chord * d.span
        p["drag_v"] = (p["Cdp"] * c**3 + p["Cdf"] * c) * q * d.chord * d.span
        p["drag_i"] = induced_drag(p["side_force"], q, d.span * c, d.e)
        p["drag"] = p["drag_v"] + p["drag_i"]
        p["leeway"] = p["aoa"] * c
        out.append(p)
    return pd.concat(out, ignore_index=True)


def loads(forces: pd.DataFrame, baseline: str, aoas, names=LOAD_NAMES) -> pd.DataFrame:
    """The side forces [N] the baseline makes at `aoas`, per boat speed."""
    return racetime.loads_from(forces, baseline, aoas, names)


# --------------------------------------------------------------------------
# Ranking


def _unsteady_near(g: pd.DataFrame, a: float) -> bool:
    if "unsteady" not in g or math.isnan(a):
        return False
    lo, hi = g.loc[g["aoa"] <= a + 1e-9, "aoa"].max(), g.loc[g["aoa"] >= a - 1e-9, "aoa"].min()
    return bool(g.loc[(g["aoa"] >= lo) & (g["aoa"] <= hi), "unsteady"].astype(bool).any())


def _base(t: pd.DataFrame, baseline: str, key, col: str) -> np.ndarray:
    """The baseline's `col` on every row of t (matched on `key`)."""
    base = t[t["candidate"] == baseline].set_index(key)[col]
    idx = pd.MultiIndex.from_frame(t[key]) if len(key) > 1 else pd.Index(t[key[0]])
    return base.reindex(idx).to_numpy()


def upwind(forces: pd.DataFrame, lds: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Per candidate, boat speed and load: section angle, leeway and drag at
    the load; `vs_base` = drag against the baseline's [%], `d_leeway` [deg];
    nan where the candidate can't make the force."""
    rows = []
    for (cand, vb), g in forces.groupby(["candidate", "speed"]):
        c = math.cos(math.radians(g["rake"].iloc[0]))
        for _, ld in lds[np.isclose(lds["speed"], vb)].iterrows():
            a, dr = racetime.at_force(g, ld["force"])
            rows.append({"candidate": cand, "speed": vb, "load": ld["load"], "force": ld["force"], "aoa": a,
                         "leeway": a * c, "drag": dr, "unsteady": _unsteady_near(g, a)})
    up = pd.DataFrame(rows)
    key = ["speed", "load"]
    up["vs_base"] = 100 * (up["drag"] / _base(up, baseline, key, "drag") - 1)
    up["d_leeway"] = up["leeway"] - _base(up, baseline, key, "leeway")
    return up


def stall_margin(forces: pd.DataFrame, lds: pd.DataFrame, high: str = LOAD_NAMES[-1]) -> pd.DataFrame:
    """Per candidate and boat speed: the section angle at maximum side force
    (end of the pre-stall branch) less the angle at the high load [deg].
    `censored`: the maximum is the polar's last angle, so the margin is at
    least this."""
    rows = []
    for (cand, vb), g in forces.groupby(["candidate", "speed"]):
        g = g[g["aoa"] >= 0]
        if g.empty:
            continue
        idx = racetime.prestall_branch(g["aoa"].to_numpy(), g["side_force"].to_numpy())
        a_max = float(g["aoa"].to_numpy()[idx[-1]])
        ld = lds[np.isclose(lds["speed"], vb) & (lds["load"] == high)]
        a_high = racetime.at_force(g, float(ld["force"].iloc[0]))[0] if len(ld) else math.nan
        rows.append({"candidate": cand, "speed": vb, "aoa_max": a_max, "margin": a_max - a_high,
                     "censored": a_max >= g["aoa"].max() - 1e-9})
    return pd.DataFrame(rows)


def downwind(forces: pd.DataFrame, baseline: str, reach_aoa: float) -> pd.DataFrame:
    """Per candidate and boat speed: drag at 0 deg and at the reach load (the
    baseline's side force at reach_aoa), each also against the baseline's [%]."""
    ref = forces[(forces["candidate"] == baseline) & np.isclose(forces["aoa"], reach_aoa)].set_index("speed")
    rows = []
    for (cand, vb), g in forces.groupby(["candidate", "speed"]):
        zero = g[np.isclose(g["aoa"], 0.0)]
        d0 = float(zero["drag"].iloc[0]) if len(zero) else math.nan
        f = float(ref.loc[vb, "side_force"]) if vb in ref.index else math.nan
        dr = racetime.at_force(g, f)[1] if not math.isnan(f) else math.nan
        rows.append({"candidate": cand, "speed": vb, "drag_0": d0, "reach_force": f, "drag_reach": dr})
    dn = pd.DataFrame(rows)
    for col in ("drag_0", "drag_reach"):
        dn[f"{col}_vs_base"] = 100 * (dn[col] / _base(dn, baseline, ["speed"], col) - 1)
    return dn


def summary(up: pd.DataFrame, margin: pd.DataFrame, dn: pd.DataFrame, d: Design, baseline: str,
            stall_veto: bool = True) -> pd.DataFrame:
    """One row per candidate, best upwind first: mean and worst drag against
    the baseline upwind [%], mean leeway difference [deg], the smallest stall
    margin [deg] (and whether it is censored), downwind drag at 0 deg (all
    speeds and from 7.5 kn) and at the reach load [%], points missing or
    unsteady upwind, and the vetoes: a stall margin both under d.stall_min
    and more than 1 deg under the baseline's (a thin section's margin is
    small whatever its shape), a downwind
    loss larger than the upwind gain. XFOIL's maximum lift of a thin section
    is not to be trusted (findings, Report 824 check), so its rankings pass
    stall_veto=False and show the margin for information only."""
    by = up.groupby("candidate")
    mg = margin.dropna(subset=["margin"])
    m = mg.loc[mg.groupby("candidate")["margin"].idxmin()].set_index("candidate")
    s = pd.DataFrame({"upwind %": by["vs_base"].mean(), "upwind worst %": by["vs_base"].max(),
                      "d leeway deg": by["d_leeway"].mean(), "stall margin deg": m["margin"],
                      "margin censored": m["censored"],
                      "downwind %": dn.groupby("candidate")["drag_0_vs_base"].mean(),
                      "downwind 7.5+ kn %": dn[dn["speed"] >= 7.5].groupby("candidate")["drag_0_vs_base"].mean(),
                      "reach %": dn.groupby("candidate")["drag_reach_vs_base"].mean(),
                      "missing": by["drag"].apply(lambda v: int(v.isna().sum())),
                      "unsteady": by["unsteady"].sum().astype(int)})
    base_margin = s.loc[baseline, "stall margin deg"] if baseline in s.index else math.nan

    def veto(r):
        why = []
        if stall_veto and not r["margin censored"] and r["stall margin deg"] < min(d.stall_min, base_margin - 1):
            why.append("stall")
        if r["downwind %"] > max(0.0, -r["upwind %"]):
            why.append("downwind")
        return ",".join(why)

    s["veto"] = s.apply(veto, axis=1)
    return s.sort_values("upwind %")


def rank(polars: pd.DataFrame, d: Design, rake: float | None = None, lds: pd.DataFrame | None = None,
         baseline: str | None = None, stall_veto: bool = True) -> dict[str, pd.DataFrame]:
    """The whole ranking of one set of polars (one Tu or model) at `rake`;
    the loads come from the baseline at the nominal rake unless given."""
    baseline = baseline or d.baseline
    if lds is None:
        lds = loads(board_forces(polars, d, d.up_speeds), baseline, d.load_aoa)
    f_up = board_forces(polars, d, d.up_speeds, rake)
    f_dn = board_forces(polars, d, d.down_speeds, rake)
    up, mg, dn = upwind(f_up, lds, baseline), stall_margin(f_up, lds), downwind(f_dn, baseline, d.reach_aoa)
    return {"loads": lds, "upwind": up, "margin": mg, "downwind": dn,
            "summary": summary(up, mg, dn, d, baseline, stall_veto)}


# --------------------------------------------------------------------------
# Sources of polars


def xfoil_polars(d: Design, specs, threads: int = 8, variants: list[str] | None = None) -> pd.DataFrame:
    """XFOIL polars of the baseline and `specs` on the CFD's V_n grid, one
    `variant` per Tu of the design (Ncrit from Tu) plus the tripped one."""
    sections = {sp: sectiondesign.load(sp) for sp in dict.fromkeys([d.baseline, *specs])}
    runs = [(f"Tu {tu:g}", tu, None) for tu in d.xfoil_tu]
    if d.xfoil_xtr:
        runs.append((f"XTR {d.xfoil_xtr:g}", d.xfoil_tu[-1], (d.xfoil_xtr, d.xfoil_xtr)))
    parts = []
    for name, tu, xtr in runs:
        if variants and name not in variants:
            continue
        t = sectiondesign.xfoil_table(sections, d.chord, d.cfd_speeds, [tu], d.xfoil_angles, nu=d.nu,
                                      threads=threads, xtr=xtr)
        parts.append(t.assign(variant=name))
    df = pd.concat(parts, ignore_index=True)
    df["Cdf"] = df["Cd"] - df["Cdp"]
    return df


def cfd_polars(results, replace=(), tu: float | None = None, turbulence: str | None = None) -> pd.DataFrame:
    """foil2d results.csv files (sectiondesign.cfd_table), with the drag split
    named as XFOIL's: Cdp, Cdf."""
    t = sectiondesign.cfd_table(results, replace, tu, turbulence=turbulence)
    return t.rename(columns={"Cd_pressure": "Cdp", "Cd_friction": "Cdf"})


# --------------------------------------------------------------------------
# Optimisation


class BoardObjective(sectiondesign.Objective):
    """sectiondesign.Objective for the board: a CST section at the class
    thickness (not stiffness-matched), valued by its mean upwind drag against
    the baseline (XFOIL both), worst of the Tu variants, plus the parent's
    shape penalties (nose radius under r_le_rel_min x the baseline's, more
    than one thickness maximum, trailing-edge angle, maximum-thickness
    position) and one percent per stall or downwind veto."""

    def __init__(self, d: Design, tus=(0.1, 1.0), r_le_rel_min: float = 0.6, te_min: float = 4.0,
                 te_max: float = 90.0, xt_range=(0.18, 0.5)):
        self.d, self.baseline, self.chord, self.tus = d, d.baseline, d.chord, list(tus)
        self.te_min, self.te_max, self.xt_range = te_min, te_max, xt_range
        base = sectiondesign.load(d.baseline)
        self.ref = {**sectiondesign.properties(base)}
        self.ref["r_le"] *= r_le_rel_min
        self.base_df = self._polars({d.baseline: base}, threads=8)
        first = self.base_df[np.isclose(self.base_df["Tu"], self.tus[0])]
        self.loads = loads(board_forces(first, d, d.up_speeds), d.baseline, d.load_aoa)
        self.log: list[dict] = []

    def _polars(self, sections, threads: int = 1) -> pd.DataFrame:
        t = sectiondesign.xfoil_table(sections, self.d.chord, self.d.cfd_speeds, self.tus, self.d.xfoil_angles,
                                      nu=self.d.nu, threads=threads)
        return t.assign(Cdf=t["Cd"] - t["Cdp"])

    def section(self, z, name: str = "design"):
        return sectiondesign.cst_symmetric([1.0, *z], t=self.d.t_c, name=name)

    def evaluate(self, z) -> dict:
        f = self.section(z)
        p = sectiondesign.properties(f)
        rec = {**{f"z{i + 1}": float(v) for i, v in enumerate(z)}, **p, "penalty": self.penalties(f, p)}
        if rec["penalty"] > 1.0:  # far outside: don't spend XFOIL time on it
            rec["value"] = 5.0 + rec["penalty"]
            return rec
        df = pd.concat([self.base_df, self._polars({"design": f})], ignore_index=True)
        worst = -math.inf
        for tu, g in df.groupby("Tu"):
            s = rank(g, self.d, lds=self.loads, stall_veto=False)["summary"]
            if "design" not in s.index or math.isnan(s.loc["design", "upwind %"]):
                rec["value"] = 5.0 + rec["penalty"]
                return rec
            r = s.loc["design"]
            rec[f"Tu{tu:g} upwind %"], rec[f"Tu{tu:g} downwind %"] = float(r["upwind %"]), float(r["downwind %"])
            worst = max(worst, float(r["upwind %"]) + r["missing"] + 1.0 * len([v for v in r["veto"].split(",") if v]))
        rec["value"] = worst + rec["penalty"]
        return rec


# --------------------------------------------------------------------------
# Command line


def _print_rankings(polars: pd.DataFrame, d: Design, out: Path | None, label: str, by: str | None,
                    lds: pd.DataFrame | None, baseline: str | None = None,
                    stall_veto: bool = True) -> None:  # pragma: no cover - thin CLI
    pd.set_option("display.width", 220)
    groups = polars.groupby(by) if by else [(label, polars)]
    for name, g in groups:
        for rake in dict.fromkeys([d.rake, *d.rake_range]):
            r = rank(g, d, rake, lds, baseline, stall_veto)
            lds = r["loads"] if lds is None else lds
            tag = f"{name} rake {rake:g}"
            print(f"\n== {tag} (against {baseline or d.baseline}; % of the board's drag, lower is better)")
            print(r["summary"].round(2).to_string())
            if rake == d.rake:
                per = r["upwind"].pivot_table(index="candidate", columns="speed", values="vs_base", aggfunc="mean")
                print("upwind by speed [kn], mean over loads:")
                print(per.reindex(r["summary"].index).round(2).to_string())
            if out:
                stem = tag.replace(" ", "")
                for k, t in r.items():
                    t.to_csv(out / f"{k}-{stem}.csv", index=k == "summary")


def _main(argv=None) -> None:  # pragma: no cover - thin CLI
    ap = argparse.ArgumentParser(prog="python -m iomcfd.boardrank", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", default="thistle", help="projects/foil2d/design/<name>.yaml or a path")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="XFOIL ranking of sections against the design's baseline")
    s.add_argument("specs", nargs="+")
    s.add_argument("--variants", nargs="*", help="only these XFOIL variants, e.g. 'Tu 1' 'XTR 0.05'")
    s.add_argument("--out", type=Path, help="directory for polars.csv and the ranking tables")
    s.add_argument("--write-loads", action="store_true", help="also write design/<name>-loads.csv")
    c = sub.add_parser("cfd", help="ranking of finished foil2d runs (results.csv)")
    c.add_argument("results", nargs="+", type=Path)
    c.add_argument("--replace", nargs="*", type=Path, default=[], help="results.csv whose points replace (transient)")
    c.add_argument("--tu", type=float, help="only this Tu (default: rank each Tu)")
    c.add_argument("--turbulence", help="only this model, e.g. kOmegaSST")
    c.add_argument("--loads", type=Path, help="loads CSV (speed [kn], load, force [N]); default: the baseline's")
    c.add_argument("--up-kn", type=float, nargs="+", help="upwind boat speeds [kn] (default: the design's); "
                   "only those the runs have, e.g. thistle-screen's 1 3 5")
    c.add_argument("--down-kn", type=float, nargs="+", help="downwind boat speeds [kn] (default: the design's)")
    c.add_argument("--out", type=Path)
    k = sub.add_parser("calibrate", help="does XFOIL rank the CFD candidates as the CFD does?")
    k.add_argument("results", nargs="+", type=Path)
    k.add_argument("--tu", type=float, required=True)
    o = sub.add_parser("optimise", help="differential evolution of a CST section at the class thickness (XFOIL)")
    o.add_argument("--start", nargs="+", default=["naca0006", "file:naca64-006.dat", "file:naca65-006.dat"])
    o.add_argument("--tu", type=float, nargs="+", default=[0.1, 1.0])
    o.add_argument("--order", type=int, default=6)
    o.add_argument("--bounds", type=float, nargs=2, default=[0.2, 2.0])
    o.add_argument("--popsize", type=int, default=12)
    o.add_argument("--maxiter", type=int, default=40)
    o.add_argument("--seed", type=int, default=1)
    o.add_argument("--r-le-min", type=float, default=0.6, help="smallest nose radius, x the baseline's")
    o.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    d = load_design(a.design)
    if getattr(a, "up_kn", None):
        d = dataclasses.replace(d, up_speeds=a.up_kn)
    if getattr(a, "down_kn", None):
        d = dataclasses.replace(d, down_speeds=a.down_kn)

    if a.cmd == "screen":
        df = xfoil_polars(d, a.specs, variants=a.variants)
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            df.to_csv(a.out / "polars.csv", index=False)
        props = pd.DataFrame({sp: sectiondesign.properties(sectiondesign.load(sp)) for sp in df["candidate"].unique()}).T
        print(props[["t", "x_t", "r_le_rel", "te_angle"]].round(4).to_string())
        first = df[df["variant"] == df["variant"].iloc[0]]
        lds = loads(board_forces(first, d, d.up_speeds), d.baseline, d.load_aoa)
        if a.write_loads:
            path = sectiondesign.DESIGN_DIR / f"{Path(a.design).stem}-loads.csv"
            path.write_text(f"# side forces [N] of {d.baseline} at section angles {d.load_aoa} deg, rake {d.rake:g} deg,"
                            f" XFOIL {df['variant'].iloc[0]} (boardrank screen)\n" + lds.to_csv(index=False))
        _print_rankings(df, d, a.out, "XFOIL", "variant", lds, stall_veto=False)
    elif a.cmd == "cfd":
        raw = pd.concat([pd.read_csv(p) for p in a.results], ignore_index=True)
        combos = raw[["Tu", "turbulence"]].drop_duplicates().sort_values(["turbulence", "Tu"])
        if a.tu is not None:
            combos = combos[np.isclose(combos["Tu"], a.tu)]
        if a.turbulence:
            combos = combos[combos["turbulence"] == a.turbulence]
        base = f"{d.baseline}/{d.chord * 1000:g}"
        lds = pd.read_csv(a.loads, comment="#") if a.loads else None
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
        for tu, model in combos.itertuples(index=False):
            df = cfd_polars(a.results, a.replace, tu, model)
            _print_rankings(df, d, a.out, f"CFD {model} Tu {tu:g}", None, lds, base)
    elif a.cmd == "calibrate":
        cfd = cfd_polars(a.results, tu=a.tu)
        specs = list(cfd["foil"].unique())
        xf = xfoil_polars(dataclasses.replace(d, xfoil_tu=[a.tu], xfoil_xtr=None), specs)
        on_cfd = xf[np.isin(np.round(xf["aoa"], 2), np.round(cfd["aoa"].unique(), 2))]
        cfd = cfd.assign(candidate=cfd["foil"])  # XFOIL's labels: the foil spec
        cols = {}
        for name, df in (("CFD", cfd), ("XFOIL CFD angles", on_cfd), ("XFOIL 0.5 deg", xf)):
            cols[name] = rank(df, d, stall_veto=name == "CFD")["summary"]["upwind %"]
        cal = pd.DataFrame(cols).sort_values("CFD")
        print(cal.round(2).to_string())
        print("\nSpearman rank correlation with the CFD:")
        print(cal.corr(method="spearman").iloc[0].round(2).to_string())
    elif a.cmd == "optimise":
        import json

        a.out.mkdir(parents=True, exist_ok=True)
        obj = BoardObjective(d, a.tu, a.r_le_min)
        x0 = []
        for sp in a.start:
            cc = sectiondesign.cst_coeffs(sectiondesign.load(sp), a.order)
            x0.append(cc[1:] / cc[0])
        res = sectiondesign.optimise(obj, x0, [tuple(a.bounds)] * a.order, a.popsize, a.maxiter, a.seed)
        pd.DataFrame(obj.log).to_csv(a.out / "evaluations.csv", index=False)
        best = obj.evaluate(res.x)
        spec = "cst:" + ",".join(f"{v:.10g}" for v in [1.0, *res.x]) + f"@{d.t_c:.10g}"
        (a.out / "result.json").write_text(json.dumps({"args": {k: str(v) for k, v in vars(a).items()},
                                                       "x": list(map(float, res.x)), "spec": spec, "best": best,
                                                       "nfev": int(res.nfev), "message": str(res.message)}, indent=2))
        print(json.dumps(best, indent=2))
        print(f"wrote {a.out}")


if __name__ == "__main__":  # pragma: no cover
    _main()
