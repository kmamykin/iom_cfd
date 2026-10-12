"""foil2d: steady 2D section polars for keel fins, rudders (and sail sections).

Pipeline per case:
  derive()  fluid properties, Re, inflow vector, turbulence inflow, mesh sizes
  render()  structured C-grid -> constant/polyMesh, system/caseParameters
  Allrun    checkMesh + simpleFoam (stops on converged Cl/Cd averages)
  extract() Cl, Cd (pressure/friction split), Cm, y+, Cp/Cf, separation points
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.foam import find_dat, latest_time, read_dat, set_entry
from iomcfd.forces import read_forces, settled
from iomcfd.geometry import cmesh, foils
from iomcfd.project import Project

# Mesh levels: each level doubles the cell count (factor sqrt(2) per direction),
# which is the refinement ratio used for grid-convergence (GCI) studies.
MESH_LEVELS = {"xcoarse": 0.5, "coarse": 1 / math.sqrt(2), "medium": 1.0, "fine": math.sqrt(2), "xfine": 2.0}

# 'medium' (factor 1) resolution. ~90k cells.
BASE_MESH = dict(n_surface=256, ds_le=1.0e-3, ds_te=2.0e-3, n_wake=96, n_normal=128)


class Foil2D(Project):
    name = "foil2d"
    summary_keys = ["Cl", "Cd", "L_D", "yplus_max"]

    # ------------------------------------------------------------------
    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        fl = physics.fluid(p["fluid"], p["temperature"])
        c = float(p["chord"])
        if p.get("Re"):
            speed = float(p["Re"]) * fl.nu / c
        else:
            speed = float(p["speed"])
        re = speed * c / fl.nu
        a = math.radians(float(p["aoa"]))
        drag_dir = [math.cos(a), math.sin(a), 0.0]
        lift_dir = [-math.sin(a), math.cos(a), 0.0]
        turb = physics.turbulence_inflow(speed, fl.nu, float(p["Tu"]), float(p["viscosity_ratio"]))

        level = p["mesh"]
        if level not in MESH_LEVELS:
            raise ValueError(f"mesh must be one of {sorted(MESH_LEVELS)}, got '{level}'")
        f = MESH_LEVELS[level]
        h0 = physics.first_cell_height(speed, c, fl.nu, float(p["yplus"])) / f
        span = 0.1 * c
        mesh = dict(
            chord=c,
            span=span,
            n_surface=int(round(BASE_MESH["n_surface"] * f)),
            ds_le=BASE_MESH["ds_le"] / f,
            ds_te=BASE_MESH["ds_te"] / f,
            n_wake=int(round(BASE_MESH["n_wake"] * f)),
            n_normal=int(round(BASE_MESH["n_normal"] * f)),
            first_cell=h0,
            farfield=float(p["farfield"]),
            wake_length=float(p["farfield"]),
        )
        return {
            # physics
            "rhoInf": fl.rho,
            "nu": fl.nu,
            "magUInf": speed,
            "Reynolds": re,
            "Uinf": [speed * drag_dir[0], speed * drag_dir[1], 0.0],
            "dragDir": drag_dir,
            "liftDir": lift_dir,
            "CofR": [0.25 * c, 0.0, 0.5 * span],
            "lRef": c,
            "Aref": c * span,
            "dynamicPressure": 0.5 * fl.rho * speed**2,
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
            # mesh (not used by OpenFOAM, recorded for reference)
            "mesh_spec": mesh,
        }

    # ------------------------------------------------------------------
    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        foil = foils.load(str(p["foil"]), [config.geometry_dir() / "foils"])
        spec = cmesh.CMeshSpec(**d["mesh_spec"])
        info = cmesh.build(foil, spec, case_dir / "constant" / "polyMesh")
        geo = case_dir / "constant" / "geometry"
        geo.mkdir(parents=True, exist_ok=True)
        foil.write_dat(geo / "foil.dat")
        t, xt = foil.thickness()
        d["thickness"] = round(t, 5)
        d["x_max_thickness"] = round(xt, 4)
        d["n_cells"] = info.n_cells
        d["first_cell"] = info.first_cell
        if p["solver"] == "transient":
            self._make_transient(case_dir, p, d)
        elif p["solver"] != "steady":
            raise ValueError("solver must be 'steady' or 'transient'")
        self.write_parameters(case_dir, {k: v for k, v in d.items() if k != "mesh_spec"}, inputs=p)

    def _make_transient(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        """Switch the copied (steady) case to pimpleFoam with an adaptive time
        step. The template itself stays steady."""
        t_ref = float(p["chord"]) / d["magUInf"]  # one chord flow-through
        end = float(p["flow_times"]) * t_ref
        d["flowTime"] = t_ref
        d["simEndTime"] = end
        cd = case_dir / "system" / "controlDict"
        set_entry(cd, "application", "pimpleFoam")
        set_entry(cd, "endTime", end)
        set_entry(cd, "deltaT", 1e-4 * t_ref)
        set_entry(cd, "writeControl", "adjustable")
        set_entry(cd, "writeInterval", end)
        text = cd.read_text().replace(
            "writeControl    adjustable;",
            f"adjustTimeStep  yes;\nmaxCo           {float(p['max_co'])};\nmaxDeltaT       {0.05 * t_ref:.6g};\n"
            "writeControl    adjustable;",
            1,
        )
        cd.write_text(text)
        set_entry(case_dir / "system" / "fvSchemes", "default", "backward")  # first 'default' = ddtSchemes
        fs = case_dir / "system" / "fvSolution"
        text = fs.read_text()
        # looser linear-solver tolerances: each time step is converged by the
        # PIMPLE outer loop, not by driving every solve to 1e-10
        text = text.replace("        tolerance       1e-8;\n        relTol          0.05;",
                            "        tolerance       1e-6;\n        relTol          0.05;")
        text = text.replace("        tolerance       1e-10;\n        relTol          0.1;",
                            "        tolerance       1e-8;\n        relTol          0.1;")
        i = text.index("SIMPLE\n{")
        text = text[:i] + (
            "PIMPLE\n{\n"
            "    nOuterCorrectors    3;\n"
            "    nCorrectors         2;\n"
            "    nNonOrthogonalCorrectors 0;\n"
            "    consistent          yes;\n"
            "    momentumPredictor   yes;\n"
            "}\n\n"
            "relaxationFactors\n{\n    equations\n    {\n        \".*\"          0.9;\n        \".*Final\"     1;\n    }\n}\n"
        )
        fs.write_text(text)

    # ------------------------------------------------------------------
    def _coeffs(self, case_dir: Path):
        files = find_dat(case_dir, "forceCoeffs", "coefficient.dat")
        if not files:
            return None
        names, data = read_dat(files[-1])
        if data.size == 0:
            return None
        col = {n: i for i, n in enumerate(names)}
        return data[:, 0], data[:, col["Cl"]], data[:, col["Cd"]], data[:, col["CmPitch"]]

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """Windowed means of Cl and Cd stopped moving (relative conv_tol).
        Transient runs always run for flow_times."""
        if p["solver"] == "transient":
            return False
        c = self._coeffs(case_dir)
        if c is None:
            return False
        _, cl, cd, _ = c
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        return settled(cl, w, tol, max(abs(cl[-1]), 0.1)) and settled(cd, w, tol, abs(cd[-1]))

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        c = self._coeffs(case_dir)
        if c is None:
            return {"_status": "failed"}
        it, cl, cd, cm = c
        transient = p["solver"] == "transient"
        if transient:
            # time-average over the last average_times flow-throughs
            t_avg = float(p["average_times"]) * d["flowTime"]
            sel = it > it[-1] - t_avg
            n_iter = len(it)
            out["time_s"] = float(it[-1])
            out["flow_times_done"] = float(it[-1] / d["flowTime"])
        else:
            n_iter = int(it[-1])
            win = max(10, min(int(d["convWindow"]), len(it) // 4))
            sel = np.arange(len(it)) >= len(it) - win
        for key, series in (("Cl", cl), ("Cd", cd), ("Cm", cm)):
            tail = series[sel]
            out[key] = float(tail.mean())
            out[f"{key}_std"] = float(tail.std())
        out["L_D"] = out["Cl"] / out["Cd"] if out["Cd"] else float("nan")
        q, c = d["dynamicPressure"], float(p["chord"])
        out["lift_N_per_m"] = out["Cl"] * q * c
        out["drag_N_per_m"] = out["Cd"] * q * c
        out["iterations"] = n_iter
        if transient:
            converged = out["flow_times_done"] >= 0.99 * float(p["flow_times"])
        else:
            converged = self.converged(case_dir, p, d) or n_iter < int(d["maxIter"])
        out["converged"] = converged
        # Steady RANS around a laminar separation bubble can oscillate; the
        # mean is still meaningful but flag it (consider a transient run).
        out["unsteady"] = out["Cl_std"] > 0.01 * max(abs(out["Cl"]), 0.1) or out["Cd_std"] > 0.01 * out["Cd"]

        # pressure / viscous drag split over the same averaging window
        window = float(p["average_times"]) * d["flowTime"] if transient else float(d["convWindow"])
        fr = read_forces(case_dir, "forces", window)
        if fr is not None:
            dd = np.array(d["dragDir"])
            denom = q * d["Aref"]
            out["Cd_pressure"] = float(fr.pressure @ dd / denom)
            out["Cd_friction"] = float(fr.viscous @ dd / denom)

        # y+ on the foil at the final time
        yp = find_dat(case_dir, "yPlus", "yPlus.dat")
        if yp:
            text = yp[-1].read_text().splitlines()
            rows = [ln.split() for ln in text if ln and not ln.startswith("#")]
            rows = [r for r in rows if len(r) >= 5 and r[1] == "foil"]
            if rows:
                out["yplus_min"], out["yplus_max"], out["yplus_mean"] = map(float, rows[-1][2:5])

        out.update(self._surface(case_dir, p, d))
        if not converged:
            out["_status"] = "not_converged"
        return out

    def _surface(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Cp/Cf along the foil -> surface.csv + separation/reattachment x/c."""
        base = case_dir / "postProcessing" / "foilSurface"
        if not base.is_dir():
            return {}
        t = latest_time(base)
        if t is None:
            return {}
        pf = _find_raw(base / t, "p")
        tf = _find_raw(base / t, "wallShearStress")
        if pf is None or tf is None:
            return {}
        P = np.loadtxt(pf, comments="#", ndmin=2)
        T = np.loadtxt(tf, comments="#", ndmin=2)
        c = float(p["chord"])
        U = d["magUInf"]
        x, y = P[:, 0] / c, P[:, 1] / c
        cp = P[:, 3] / (0.5 * U**2)
        # Skin friction along the local surface tangent (LE -> TE on each side).
        # OpenFOAM's wallShearStress points opposite to the near-wall flow, so
        # Cf = -tau.t/q is > 0 where the flow is attached and < 0 where reversed.
        upper = _upper_mask(x, y)
        q = 0.5 * U**2
        cf = np.zeros_like(x)
        for m in (upper, ~upper):
            idx = np.where(m)[0][np.argsort(x[m])]
            pts = P[idx, :2]
            t = np.gradient(pts, axis=0)
            t /= np.linalg.norm(t, axis=1, keepdims=True)
            cf[idx] = -(T[idx, 3] * t[:, 0] + T[idx, 4] * t[:, 1]) / q
        order = np.lexsort((x, ~upper))
        rows = [(bool(upper[i]), x[i], y[i], cp[i], cf[i]) for i in order]
        with open(case_dir / "surface.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["upper", "x_c", "y_c", "Cp", "Cf"])
            w.writerows(rows)
        res: dict[str, Any] = {}
        for side, m in (("upper", upper), ("lower", ~upper)):
            k = np.argsort(x[m])
            xs, cfs = x[m][k], cf[m][k]
            # laminar separation, reattachment, and a later (trailing-edge) separation
            sep = _first_crossing(xs, cfs, falling=True, start=0.01)
            rea = _first_crossing(xs, cfs, falling=False, start=sep) if sep is not None else None
            res[f"x_sep_{side}"] = sep
            res[f"x_reattach_{side}"] = rea
            res[f"x_te_sep_{side}"] = _first_crossing(xs, cfs, falling=True, start=max(rea or 0.0, 0.5))
        return res

    # ------------------------------------------------------------------
    def report(self, df, out_dir: Path, reference=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])].copy()
        if df.empty:
            return []
        group_cols = [c for c in ("foil", "chord", "speed", "Re", "Tu", "turbulence", "mesh", "temperature", "fluid")
                      if c in df and df[c].nunique(dropna=False) > 1]
        groups = df.groupby(group_cols) if group_cols else [("all", df)]
        fig, axs = plt.subplots(2, 2, figsize=(12, 9))
        for key, g in groups:
            g = g.sort_values("aoa")
            label = key if isinstance(key, str) else ", ".join(f"{c}={v}" for c, v in zip(group_cols, np.atleast_1d(key)))
            style = dict(marker="o", ms=3, label=label)
            axs[0, 0].plot(g["aoa"], g["Cl"], **style)
            axs[0, 1].plot(g["Cd"], g["Cl"], **style)
            axs[1, 0].plot(g["aoa"], g["Cd"], **style)
            axs[1, 1].plot(g["aoa"], g["L_D"], **style)
        if reference is not None:
            for src, r in reference.groupby("source"):
                for key, rr in (r.groupby("Re") if "Re" in r else [(None, r)]):
                    lab = f"{src} Re={int(key):,}" if key else str(src)
                    st = dict(ls="none", marker="s", mfc="none", ms=6, label=f"ref: {lab}")
                    axs[0, 0].plot(rr["aoa"], rr["Cl"], **st)
                    axs[0, 1].plot(rr["Cd"], rr["Cl"], **st)
                    axs[1, 0].plot(rr["aoa"], rr["Cd"], **st)
                    axs[1, 1].plot(rr["aoa"], rr["Cl"] / rr["Cd"], **st)
        for ax, (xl, yl) in zip(axs.flat, [("aoa [deg]", "Cl"), ("Cd", "Cl"), ("aoa [deg]", "Cd"), ("aoa [deg]", "L/D")]):
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.grid(alpha=0.3)
        axs[0, 0].legend(fontsize=7)
        fig.tight_layout()
        polar = out_dir / "polar.png"
        fig.savefig(polar, dpi=130)
        plt.close(fig)
        files = [polar]
        gci = self._mesh_convergence(df, out_dir)
        if gci:
            files.append(gci)
        return files

    def _mesh_convergence(self, df, out_dir: Path):  # pragma: no cover - host only
        """GCI table when a study runs the same case on three consecutive mesh levels."""
        from iomcfd.verification import grid_convergence

        if "mesh" not in df or df["mesh"].nunique() < 3:
            return None
        order = list(MESH_LEVELS)
        others = [c for c in ("foil", "aoa", "Re", "speed", "Tu", "turbulence", "solver") if c in df and df[c].nunique() > 1]
        rows = []
        for key, g in (df.groupby(others) if others else [("all", df)]):
            g = g.set_index("mesh")
            levels = [m for m in order if m in g.index]
            for i in range(len(levels) - 2):
                c3, c2, c1 = levels[i : i + 3]  # coarse, medium, fine
                ratio = MESH_LEVELS[c1] / MESH_LEVELS[c2]
                for q in ("Cl", "Cd"):
                    gc = grid_convergence(g.loc[c1, q], g.loc[c2, q], g.loc[c3, q], ratio)
                    rows.append({**dict(zip(others, np.atleast_1d(key))), "levels": f"{c3}/{c2}/{c1}", "quantity": q,
                                 "coarse": gc.f_coarse, "medium": gc.f_medium, "fine": gc.f_fine,
                                 "order": gc.order, "extrapolated": gc.f_extrapolated, "gci_fine": gc.gci_fine})
        import pandas as pd

        path = out_dir / "mesh_convergence.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return path

    def mesh_views(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]):
        from iomcfd.meshplot import MeshSpec, MeshView

        c = float(p["chord"])
        m = d["mesh_spec"]
        zm = 0.5 * float(m["span"])
        R = float(m["farfield"]) * c
        cut = dict(origin=(0.0, 0.0, zm), normal=(0.0, 0.0, 1.0), axes=(0, 1))
        return MeshSpec(
            [
                MeshView("whole domain: C-grid, wake cut to the outlet", center=(0.0, 0.0), width=3.4 * R, lw=0.15, **cut),
                MeshView("foil", center=(0.55 * c, 0.0), width=1.45 * c, **cut),
                MeshView("leading edge", center=(0.03 * c, 0.0), width=0.12 * c, **cut),
                MeshView("trailing edge and start of the wake cut", center=(c, 0.0), width=0.12 * c, **cut),
            ],
            walls="foil",
            notes=[f"structured C-grid: {m['n_surface'] + 1} points per surface, {m['n_normal']} wall-normal cells, "
                   f"{m['n_wake']} wake cells, first cell {m['first_cell'] / c:.1e} c, far field {m['farfield']:.0f} c"],
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        f = MESH_LEVELS.get(p.get("mesh", "medium"), 1.0)
        return {"cpus": int(p.get("np", 1)), "memory_gb": 2, "max_hours": 1 + 2 * f * f}


def _find_raw(d: Path, field: str) -> Path | None:
    for cand in sorted(d.glob(f"*{field}*")):
        if cand.is_file():
            return cand
    return None


def _upper_mask(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Split a foil's faces into upper/lower about its camber line estimate."""
    xs = np.linspace(0, 1, 101)
    mids = []
    for xi in xs:
        near = np.abs(x - xi) < 0.02
        mids.append(0.5 * (y[near].max() + y[near].min()) if near.any() else 0.0)
    return y >= np.interp(x, xs, mids)


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
