"""bulb2d: a keel bulb alone, as a body of revolution at zero incidence.

Steady axisymmetric RANS (simpleFoam on a wedge mesh) with Langtry-Menter
transition (kOmegaSSTLM), or fully turbulent kOmegaSST for comparison. Made
for the questions where the fin doesn't matter: how much of the bulb's drag
the boundary layer decides at IOM Reynolds numbers (2-5e5), where laminar
separation sits on the tail, and how fineness, the position of the largest
diameter and the tail shape change that at a fixed lead mass. Validated on
Dress's (1988) laminar body, measured at the same Reynolds numbers.

Pipeline per case:
  derive()  body size (from the lead mass or a length), Re, inflow, mesh sizes
  render()  wedge mesh (geometry/axisym.py) -> constant/polyMesh, caseParameters
  Allrun    checkMesh + simpleFoam (stops on converged Cd)
  extract() drag (friction, pressure, base), C_D on wetted area, volume^(2/3)
            and frontal area, y+, Cp/Cf along the body, separation points
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.foam import find_dat, latest_time, read_dat
from iomcfd.forces import forces_function, read_forces, settled, window_stats
from iomcfd.geometry import axisym, cmesh
from iomcfd.project import Project

# Mesh levels as foil2d: each level doubles the cell count.
MESH_LEVELS = {"xcoarse": 0.5, "coarse": 1 / math.sqrt(2), "medium": 1.0, "fine": math.sqrt(2), "xfine": 2.0}
# 'medium' (factor 1): 256 x 128 cells around the body, about 50k cells.
BASE_MESH = dict(n_surface=256, ds_le=1.0e-3, ds_te=2.0e-3, n_wake=96, n_normal=128, n_base=40)
COEFF_LIMIT = 50.0  # |Cd| past this after the start-up: blown up


def profile(p: dict[str, Any]) -> axisym.Profile:
    body = str(p["body"])
    if body == "naca":
        return axisym.naca_profile(1.0 / float(p["fineness"]))
    if body == "bulb":
        return axisym.bulb_profile(float(p["fineness"]), float(p["max_at"]), float(p["tail_exp"]))
    if body.startswith("file:"):
        return axisym.file_profile(config.geometry_dir() / "bodies" / body[5:])
    raise ValueError(f"body must be naca, bulb or file:<name>, got '{body}'")


def body_size(p: dict[str, Any], prof: axisym.Profile) -> float:
    """Length [m]: from the lead mass if one is given, else `length`."""
    if float(p.get("mass") or 0) > 0:
        return (float(p["mass"]) / float(p["lead_density"]) / prof.volume()) ** (1 / 3)
    return float(p["length"])


class Bulb2D(Project):
    name = "bulb2d"
    summary_keys = ["drag_mN", "Cd_wet", "x_sep", "x_reattach"]
    highlight_columns = ["drag_mN", "Cd_wet", "drag_friction_N", "drag_pressure_N", "x_sep", "x_reattach", "x_cf_min"]

    # ------------------------------------------------------------------
    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        fl = physics.fluid(p["fluid"], p["temperature"])
        prof = profile(p)
        L = body_size(p, prof)
        speed = float(p["Re"]) * fl.nu / L if p.get("Re") else float(p["speed"])
        rmax, xmax = prof.max_radius()
        wet, vol = prof.wetted_area() * L**2, prof.volume() * L**3
        turb = physics.turbulence_inflow(speed, fl.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        level = p["mesh"]
        if level not in MESH_LEVELS:
            raise ValueError(f"mesh must be one of {sorted(MESH_LEVELS)}, got '{level}'")
        f = MESH_LEVELS[level]
        mesh = dict(
            chord=L,
            span=0.1 * L,  # not used by the wedge
            n_surface=int(round(BASE_MESH["n_surface"] * f)),
            ds_le=BASE_MESH["ds_le"] / f,
            ds_te=BASE_MESH["ds_te"] / f,
            n_wake=int(round(BASE_MESH["n_wake"] * f)),
            n_normal=int(round(BASE_MESH["n_normal"] * f)),
            first_cell=physics.first_cell_height(speed, L, fl.nu, float(p["yplus"])) / f,
            farfield=float(p["farfield"]),
            wake_length=float(p["farfield"]),
        )
        share = float(p["wedge"]) / 360.0
        return {
            # body
            "body_name": prof.name,
            "length_m": L,
            "diameter_m": 2 * rmax * L,
            "fineness_actual": 0.5 / rmax,
            "x_max_diameter": xmax,
            "base_diameter_m": 2 * prof.base * L,
            "wetted_area_m2": wet,
            "volume_m3": vol,
            "lead_kg": vol * float(p["lead_density"]),
            "x_centroid": prof.centroid(),
            # physics
            "rhoInf": fl.rho,
            "nu": fl.nu,
            "magUInf": speed,
            "Re_L": speed * L / fl.nu,
            "Re_V": speed * vol ** (1 / 3) / fl.nu,
            "Uinf": [speed, 0.0, 0.0],
            "lRef": L,
            "Aref": wet * share,  # the wedge's share of the wetted area: forceCoeffs' Cd = C_D,wet
            "dynamicPressure": 0.5 * fl.rho * speed**2,
            "wedgeShare": share,
            # turbulence
            "turbModel": p["turbulence"],
            "kInf": turb.k,
            "omegaInf": turb.omega,
            "nutInf": turb.nut,
            "ReThetatInf": turb.ReThetat,
            "decayControl": (p["turbulence"] == "kOmegaSSTLM") if p["decay_control"] == "auto" else bool(p["decay_control"]),
            # solver control
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
            "relaxU": float(p["relax_U"]),
            "relaxTurb": float(p["relax_turb"]),
            "relaxTransition": float(p["relax_transition"]),
            "mesh_spec": mesh,
            "n_base": max(4, int(round(BASE_MESH["n_base"] * f))),
        }

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        prof = profile(p)
        spec = cmesh.CMeshSpec(**d["mesh_spec"])
        info = axisym.build(prof, spec, case_dir / "constant" / "polyMesh", n_base=d["n_base"], wedge=float(p["wedge"]))
        d["n_cells"] = info.n_cells
        d["first_cell"] = info.first_cell
        geo = case_dir / "constant" / "geometry"
        geo.mkdir(parents=True, exist_ok=True)
        x, r = prof.dense(400)
        np.savetxt(geo / "profile.csv", np.column_stack([x * d["length_m"], r * d["length_m"]]), delimiter=",",
                   header="x_m,r_m", comments="")
        fo = [forces_function("forces_body", ["body"])]
        if prof.base > 0:
            fo.append(forces_function("forces_base", ["base"]))
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        (inc / "forceFunctions").write_text("// generated by iomcfd: forces on the wedge's body and base\n\n" + "\n".join(fo))
        self.write_parameters(case_dir, {k: v for k, v in d.items() if k not in ("mesh_spec", "body_name")}, inputs=p)

    # ------------------------------------------------------------------
    def _cd(self, case_dir: Path):
        files = find_dat(case_dir, "forceCoeffs", "coefficient.dat")
        if not files:
            return None
        names, data = read_dat(files[-1])
        if data.size == 0:
            return None
        return data[:, 0], data[:, {n: i for i, n in enumerate(names)}["Cd"]]

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        c = self._cd(case_dir)
        if c is None:
            return False
        _, cd = c
        return settled(cd, int(d["convWindow"]), float(p["conv_tol"]), abs(cd[-1]))

    def progress(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        c = self._cd(case_dir)
        if c is None:
            return {}
        _, cd = c
        out: dict[str, Any] = {"Cd": float(cd[-1])}
        st = window_stats(cd, int(d["convWindow"]))
        if st is not None and cd[-1]:
            out["Cd_change"] = st[1] / abs(cd[-1])
        out["conv_tol"] = float(p["conv_tol"])
        return out

    def diverged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> str | None:
        c = self._cd(case_dir)
        if c is None or len(c[0]) < 100:
            return None
        cd = c[1][-3:]
        if (~np.isfinite(cd) | (np.abs(cd) > COEFF_LIMIT)).all():
            return f"drag coefficient out of range: Cd {cd[-1]:.3g}"
        return None

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        c = self._cd(case_dir)
        if c is None:
            return {"_status": "failed"}
        it, cd = c
        n_iter = int(it[-1])
        win = max(10, min(int(d["convWindow"]), len(it) // 4))
        tail = cd[-win:]
        out: dict[str, Any] = {"Cd_wet": float(tail.mean()), "Cd_std": float(tail.std()), "iterations": n_iter}
        # Steady RANS around a laminar separation bubble can oscillate: the
        # mean still means something, but flag it (a transient run would say).
        out["unsteady"] = out["Cd_std"] > 0.01 * abs(out["Cd_wet"])
        q, scale = d["dynamicPressure"], 1.0 / d["wedgeShare"]
        drag = {"friction": 0.0, "pressure": 0.0, "base": 0.0}
        for part in ("body", "base"):
            fr = read_forces(case_dir, f"forces_{part}", float(d["convWindow"]))
            if fr is None:
                continue
            if part == "body":
                drag["friction"] += scale * float(fr.viscous[0])
                drag["pressure"] += scale * float(fr.pressure[0])
            else:
                drag["base"] = scale * float(fr.total[0])
        total = drag["friction"] + drag["pressure"] + drag["base"]
        out.update({
            "drag_N": total,
            "drag_mN": 1e3 * total,
            "drag_friction_N": drag["friction"],
            "drag_pressure_N": drag["pressure"],  # on the body, without the base
            "drag_base_N": drag["base"],
            "friction_share": drag["friction"] / total if total else float("nan"),
            "Cd_vol": total / (q * d["volume_m3"] ** (2 / 3)),
            "Cd_front": total / (q * math.pi * (0.5 * d["diameter_m"]) ** 2),
        })
        converged = self.converged(case_dir, p, d) or n_iter < int(d["maxIter"])
        out["converged"] = converged
        yp = find_dat(case_dir, "yPlus", "yPlus.dat")
        if yp:
            rows = [ln.split() for ln in yp[-1].read_text().splitlines() if ln and not ln.startswith("#")]
            rows = [r for r in rows if len(r) >= 5 and r[1] == "body"]
            if rows:
                out["yplus_min"], out["yplus_max"], out["yplus_mean"] = map(float, rows[-1][2:5])
        out.update(self._surface(case_dir, p, d))
        if not converged:
            out["_status"] = "not_converged"
        return out

    def _surface(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Cp/Cf along the body -> surface.csv; separation and reattachment x/L."""
        base = case_dir / "postProcessing" / "bodySurface"
        t = latest_time(base) if base.is_dir() else None
        if t is None:
            return {}
        pf, tf = _find_raw(base / t, "p"), _find_raw(base / t, "wallShearStress")
        if pf is None or tf is None:
            return {}
        P = np.loadtxt(pf, comments="#", ndmin=2)
        T = np.loadtxt(tf, comments="#", ndmin=2)
        L, U = d["length_m"], d["magUInf"]
        order = np.argsort(P[:, 0])
        P, T = P[order], T[np.argsort(T[:, 0])]
        x, r = P[:, 0] / L, np.hypot(P[:, 1], P[:, 2]) / L
        cp = P[:, 3] / (0.5 * U**2)
        # skin friction along the surface tangent in the meridian plane; OpenFOAM's
        # wallShearStress points against the near-wall flow, so Cf > 0 = attached
        tx, tr = np.gradient(x), np.gradient(r)
        n = np.hypot(tx, tr)
        cf = -(T[:, 3] * tx + T[:, 4] * tr) / n / (0.5 * U**2)
        with open(case_dir / "surface.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["x_L", "r_L", "Cp", "Cf"])
            w.writerows(zip(*(np.char.mod("%.6g", a) for a in (x, r, cp, cf))))
        sep = _first_crossing(x, cf, falling=True, start=0.02)
        rea = _first_crossing(x, cf, falling=False, start=sep)
        late = _first_crossing(x, cf, falling=True, start=rea) if rea is not None else None
        aft = x > 0.05
        return {
            "x_sep": sep, "x_reattach": rea, "x_te_sep": late,
            # where the laminar skin friction stops falling: transition or separation begins
            "x_cf_min": float(x[aft][np.argmin(cf[aft])]) if aft.any() else None,
            "Cp_min": float(cp.min()), "x_Cp_min": float(x[np.argmin(cp)]),
        }

    # ------------------------------------------------------------------
    def report(self, df, out_dir: Path, reference=None, options=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])]
        if df.empty:
            return []
        out_dir = Path(out_dir)
        files: list[Path] = []
        vary = [c for c in ("body", "fineness", "max_at", "tail_exp", "turbulence", "Tu", "mesh", "speed")
                if c in df and df[c].nunique() > 1 and c != "speed"]
        label = lambda k: ", ".join(f"{n} {v}" for n, v in zip(vary, k if isinstance(k, tuple) else (k,))) or "all"

        # drag coefficient against Reynolds number, with reference data and flat-plate lines
        fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
        groups = list(df.groupby(vary)) if vary else [("all", df)]
        for key, g in groups:
            g = g.sort_values("Re_L")
            axs[0].plot(g["Re_L"], g["Cd_wet"], "o-", label=label(key))
            axs[1].plot(g["Re_L"], g["x_sep"], "o-", label=f"{label(key)}: separation")
            if g["x_reattach"].notna().any():
                axs[1].plot(g["Re_L"], g["x_reattach"], "x--", color=axs[1].lines[-1].get_color(), label="reattachment")
        re = np.geomspace(df["Re_L"].min() / 1.5, df["Re_L"].max() * 1.5, 50)
        axs[0].plot(re, 1.328 / np.sqrt(re), "k:", lw=1, label="laminar flat plate (Blasius)")
        axs[0].plot(re, 0.075 / (np.log10(re) - 2) ** 2, "k--", lw=1, label="turbulent (ITTC-57)")
        if reference is not None and "Cd_wet" in reference:
            axs[0].plot(reference["Re_L"], reference["Cd_wet"], "ks", ms=5, mfc="none", label="measured (reference)")
            axs[1].axhspan(0.50, 0.55, color="0.85", label="Dress: separation line, Re_L < 7e5")
        axs[0].set_xscale("log")
        axs[0].set_xlabel("Re_L")
        axs[0].set_ylabel("C_D on the wetted area")
        axs[1].set_xscale("log")
        axs[1].set_xlabel("Re_L")
        axs[1].set_ylabel("x / L")
        for ax in axs:
            ax.grid(alpha=0.3, which="both")
            ax.legend(fontsize=7)
        fig.tight_layout()
        files.append(out_dir / "drag.png")
        fig.savefig(files[-1], dpi=130)
        plt.close(fig)

        # the bulb at a fixed lead mass: drag against fineness, one line per speed and turbulence setting
        if "fineness" in df and df["fineness"].nunique() > 2 and str(df["body"].iloc[0]) in ("naca", "bulb"):
            fig, ax = plt.subplots(figsize=(7.5, 4.8))
            lines = [c for c in ("speed", "turbulence", "Tu", "body", "max_at", "tail_exp") if c in df and df[c].nunique() > 1]
            for key, g in (df.groupby(lines) if lines else [("all", df)]):
                g = g.sort_values("fineness")
                ax.plot(g["fineness"], g["drag_mN"], "o-",
                        label=", ".join(f"{n} {v}" for n, v in zip(lines, key if isinstance(key, tuple) else (key,))))
            ax.set_xlabel("fineness L / D")
            ax.set_ylabel("drag [mN]")
            ax.set_title(f"bulb alone, {df['lead_kg'].iloc[0]:.2f} kg of lead")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7)
            fig.tight_layout()
            files.append(out_dir / "fineness.png")
            fig.savefig(files[-1], dpi=130)
            plt.close(fig)

        files += self._surface_figure(df, vary, out_dir)
        files.append(self._table(df, vary, out_dir / "drag.md"))
        return files

    @staticmethod
    def _surface_figure(df, vary, out_dir: Path) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib.pyplot as plt
        import pandas as pd

        run_dir = out_dir.parent
        fig, axs = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
        n = 0
        for _, r in df.sort_values([*vary, "Re_L"] if vary else ["Re_L"]).iterrows():
            f = run_dir / str(r["case"]) / "surface.csv"
            if not f.is_file() or n >= 12:
                continue
            s = pd.read_csv(f)
            lab = ", ".join(f"{c} {r[c]}" for c in vary) + f", Re_L {r['Re_L']:.3g}"
            axs[0].plot(s["x_L"], s["Cf"], lw=1, label=lab)
            axs[1].plot(s["x_L"], s["Cp"], lw=1, label=lab)
            n += 1
        if not n:
            plt.close(fig)
            return []
        axs[0].axhline(0, color="k", lw=0.6)
        axs[0].set_ylabel("Cf (< 0: reversed flow)")
        axs[0].set_ylim(-0.005, 0.02)
        axs[1].set_ylabel("Cp")
        axs[1].invert_yaxis()
        axs[1].set_xlabel("x / L")
        for ax in axs:
            ax.grid(alpha=0.3)
        axs[0].legend(fontsize=6, ncol=2)
        fig.tight_layout()
        path = out_dir / "surface.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        return [path]

    @staticmethod
    def _table(df, vary, path: Path) -> Path:  # pragma: no cover - formatting
        cols = [*vary, "magUInf", "Re_L", "length_m", "diameter_m", "drag_mN", "Cd_wet", "friction_share", "drag_base_N",
                "x_sep", "x_reattach", "x_te_sep", "unsteady", "yplus_max"]
        cols = [c for c in dict.fromkeys(cols) if c in df]
        L = ["## Drag of the body alone", "",
             "Speed (magUInf) in m/s; drag in mN for the whole body; C_D on the wetted area (no base); "
             "separation and reattachment as x / L (from the sign of the skin friction).", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.sort_values([*vary, "Re_L"] if vary else ["Re_L"]).iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if isinstance(v, float):
                    v = "-" if math.isnan(v) else (f"{v:.4g}" if c not in ("length_m", "diameter_m") else f"{1e3 * v:.1f} mm")
                cells.append(str(v))
            L.append("| " + " | ".join(cells) + " |")
        path.write_text("\n".join(L) + "\n")
        return path

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        f = MESH_LEVELS.get(p.get("mesh", "medium"), 1.0)
        return {"cpus": int(p.get("np", 1)), "memory_gb": 2, "max_hours": 1 + 2 * f**3}


def _find_raw(d: Path, field: str) -> Path | None:
    for cand in sorted(d.glob(f"*{field}*")):
        if cand.is_file():
            return cand
    return None


def _first_crossing(x, f, falling: bool, start: float | None) -> float | None:
    """First x > start where f changes sign (falling: + to -)."""
    if start is None:
        return None
    for i in range(1, len(x)):
        if x[i] <= start:
            continue
        a, b = f[i - 1], f[i]
        if (falling and a > 0 >= b) or (not falling and a < 0 <= b):
            return float(x[i - 1] + (x[i] - x[i - 1]) * a / (a - b))
    return None
