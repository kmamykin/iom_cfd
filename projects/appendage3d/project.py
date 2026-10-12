"""appendage3d: keel fin + bulb + rudder, steady RANS (simpleFoam + kOmegaSST).

The canoe body is replaced by a symmetry plane at z = -hull_depth, so this
measures appendage lift/drag/moments in isolation, at a given speed, leeway,
heel and rudder angle. Use the hull project for hull + appendages together.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.forces import forces_function, read_forces, settled
from iomcfd.foam import find_dat, read_dat
from iomcfd.geometry import appendages as ap
from iomcfd.geometry import stl
from iomcfd.project import Project

# Background cell = 1 mean fin chord (~80 mm). Refinement level n halves it n
# times: level 6 = chord/64 ~ 1.3 mm, enough for a 6-7 % thick fin.
# surf/feat/near/wake/dist: surface, feature-edge, near-box, wake-box and
# distance-band refinement levels.
MESH_LEVELS = {
    "xcoarse": dict(surf=(4, 5), feat=5, near=2, wake=1, dist=4),
    "coarse": dict(surf=(5, 6), feat=6, near=3, wake=2, dist=5),
    "medium": dict(surf=(6, 7), feat=7, near=3, wake=2, dist=6),
    "fine": dict(surf=(7, 8), feat=8, near=4, wake=3, dist=7),
}


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


class Appendage3D(Project):
    name = "appendage3d"
    summary_keys = ["drag_N", "side_N", "side_drag_ratio", "x_clr"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        fl = physics.fluid(p["fluid"], p["temperature"])
        b = math.radians(float(p["leeway"]))
        drag_dir = [math.cos(b), math.sin(b), 0.0]
        side_dir = [-math.sin(b), math.cos(b), 0.0]
        V = float(p["speed"])
        turb = physics.turbulence_inflow(V, fl.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        mean_chord = 0.5 * (float(p["fin_root_chord"]) + float(p["fin_tip_chord"]))
        return {
            "rhoInf": fl.rho,
            "nu": fl.nu,
            "magUInf": V,
            "Uinf": [V * d for d in drag_dir],
            "dragDir": drag_dir,
            "sideDir": side_dir,
            "lRef": mean_chord,
            "Aref": mean_chord * float(p["fin_span"]),  # fin lateral area
            "Re_fin": V * mean_chord / fl.nu,
            "dynamicPressure": 0.5 * fl.rho * V**2,
            "turbModel": p["turbulence"],
            "kInf": turb.k,
            "omegaInf": turb.omega,
            "nutInf": turb.nut,
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
            "nLayers": int(p["n_layers"]),
        }

    # ------------------------------------------------------------------
    def surfaces(self, p: dict[str, Any]) -> list[stl.Surface]:
        zr = -float(p["hull_depth"])
        if p["geometry"] == "parametric":
            out = [
                ap.fin(ap.FinSpec(section=p["fin_section"], root_chord=p["fin_root_chord"], tip_chord=p["fin_tip_chord"],
                                  span=p["fin_span"], sweep=p["fin_sweep"], x_root_le=p["fin_x"], z_root=zr), "fin")
            ]
            if p["bulb"]:
                out.append(ap.bulb(ap.BulbSpec(length=p["bulb_length"], diameter=p["bulb_diameter"],
                                               max_at=p["bulb_max_at"], x_nose=p["bulb_x"],
                                               z_axis=zr - float(p["fin_span"])), "bulb"))
            if p["rudder"]:
                out.append(ap.rudder(ap.RudderSpec(section=p["rudder_section"], root_chord=p["rudder_root_chord"],
                                                   tip_chord=p["rudder_tip_chord"], span=p["rudder_span"],
                                                   sweep=p["rudder_sweep"], x_root_le=p["rudder_x"], z_root=zr,
                                                   angle=p["rudder_angle"]), "rudder"))
        elif p["geometry"] == "stl":
            out = []
            for f in p["stl_files"]:
                s = stl.read(config.geometry_dir() / f, _safe(Path(f).stem))
                s = s.scaled(float(p["stl_scale"]))
                for axis, deg in p["stl_rotate"] or []:
                    s = s.rotated(axis, float(deg))
                out.append(s.translated(p["stl_translate"]))
        else:
            raise ValueError("geometry must be 'parametric' or 'stl'")
        if float(p["heel"]):
            out = [s.rotated("x", float(p["heel"]), about=(0.0, 0.0, zr)) for s in out]
        return out

    def _boat_box(self, p: dict[str, Any]) -> list[float]:
        """Bounding box of the appendages before heel: [xmin, ymin, zmin, xmax, ymax, zmax]."""
        up = self.surfaces({**p, "heel": 0.0})
        lo = np.min([s.bounds[0] for s in up], axis=0)
        hi = np.max([s.bounds[1] for s in up], axis=0)
        return [float(v) for v in (*lo, *hi)]

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        surfs = self.surfaces(p)
        tri = case_dir / "constant" / "triSurface"
        stl.write_multi(tri / "appendages.stl", surfs)

        lo = np.min([s.bounds[0] for s in surfs], axis=0)
        hi = np.max([s.bounds[1] for s in surfs], axis=0)
        z_top = -float(p["hull_depth"])
        L = float(max(hi[0] - lo[0], z_top - lo[2]))
        lv = MESH_LEVELS[p["mesh"]]
        h = float(d["lRef"])  # background cell = mean fin chord
        tb = abs(math.tan(math.radians(float(p["leeway"]))))
        dom_lo = np.array([lo[0] - 2.5 * L, min(lo[1], 0) - 2.5 * L - 4 * L * tb, lo[2] - 2.0 * L])
        dom_hi = np.array([hi[0] + 5.0 * L, max(hi[1], 0) + 2.5 * L + 4 * L * tb, z_top])
        n = np.maximum(np.ceil((dom_hi - dom_lo) / h).astype(int), 1)
        dom_hi = dom_lo + n * h  # exact cell size
        dom_hi[2] = z_top
        dom_lo[2] = z_top - n[2] * h
        m = 0.1 * L
        near_lo, near_hi = lo - m, np.minimum(hi + m, [np.inf, np.inf, z_top + h])
        wake_lo = np.array([lo[0] - m, lo[1] - m - 2 * L * tb, lo[2] - m])
        wake_hi = np.array([hi[0] + 2 * L, hi[1] + m + 2 * L * tb, z_top + h])
        loc = dom_lo + np.array([0.0371, 0.4123, 0.5137]) * (dom_hi - dom_lo)

        vec = lambda a: [float(x) for x in a]
        d.update({
            "xMin": float(dom_lo[0]), "yMin": float(dom_lo[1]), "zMin": float(dom_lo[2]),
            "xMax": float(dom_hi[0]), "yMax": float(dom_hi[1]), "zMax": float(dom_hi[2]),
            "nx": int(n[0]), "ny": int(n[1]), "nz": int(n[2]),
            "baseCell": h,
            "surfaceLevelMin": lv["surf"][0], "surfaceLevelMax": lv["surf"][1],
            "featureLevel": lv["feat"],
            "nearBoxMin": vec(near_lo), "nearBoxMax": vec(near_hi), "nearBoxLevel": lv["near"],
            "wakeBoxMin": vec(wake_lo), "wakeBoxMax": vec(wake_hi), "wakeBoxLevel": lv["wake"],
            "nearDistance": 6 * h / 2 ** lv["dist"], "nearDistanceLevel": lv["dist"],
            "locationInMesh": vec(loc),
            "components": [s.name for s in surfs],
            "wetted_area_m2": float(sum(s.area() for s in surfs)),
            "bodyMin": vec(lo),
            "bodyMax": vec(hi),
            "bodyBoxBoat": self._boat_box(p),
        })
        if p["geometry"] == "parametric" and p["bulb"]:
            b = next(s for s in surfs if s.name == "bulb")
            d["bulb_mass_kg"] = b.volume() * ap.LEAD_DENSITY

        fo = [forces_function(f"forces_{s.name}", [f"appendages_{s.name}"]) for s in surfs]
        fo.append(forces_function("forces_total", ["appendages"], interval=1))
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        (inc / "forceFunctions").write_text("// generated by iomcfd: one forces function object per component\n\n" + "\n".join(fo))
        self.write_parameters(case_dir, d, inputs=p)

    # ------------------------------------------------------------------
    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """Windowed means of total drag and side force stopped moving."""
        ff = find_dat(case_dir, "forces_total", "force.dat")
        if not ff:
            return False
        _, f = read_dat(ff[-1])
        if f.size == 0:
            return False
        drag = f[:, 1:4] @ np.array(d["dragDir"])
        side = f[:, 1:4] @ np.array(d["sideDir"])
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        scale = max(abs(drag[-1]), abs(side[-1]))
        return settled(drag, w, tol, abs(drag[-1])) and settled(side, w, tol, scale)

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        win = int(d["convWindow"])
        dd, sd = np.array(d["dragDir"]), np.array(d["sideDir"])
        tot = read_forces(case_dir, "forces_total", win)
        if tot is None:
            return {"_status": "failed"}
        out["drag_N"] = float(tot.total @ dd)
        out["side_N"] = float(tot.total @ sd)
        out["vertical_N"] = float(tot.total[2])
        out["drag_friction_N"] = float(tot.viscous @ dd)
        out["drag_pressure_N"] = float(tot.pressure @ dd)
        out["side_drag_ratio"] = out["side_N"] / out["drag_N"] if out["drag_N"] else float("nan")
        out["roll_moment_Nm"] = float(tot.moment[0])
        out["yaw_moment_Nm"] = float(tot.moment[2])
        # centre of lateral resistance (x where the side force acts), boat frame
        fy = float(tot.total[1])
        out["x_clr"] = float(tot.moment[2] / fy) if abs(fy) > 1e-9 else None
        q, A = d["dynamicPressure"], d["Aref"]
        out["Cd"] = out["drag_N"] / (q * A)
        out["Cs"] = out["side_N"] / (q * A)
        for comp in d.get("components", []):
            r = read_forces(case_dir, f"forces_{comp}", int(d["convWindow"]))
            if r is not None:
                out[f"drag_{comp}_N"] = float(r.total @ dd)
                out[f"side_{comp}_N"] = float(r.total @ sd)
        files = sorted((case_dir / "postProcessing" / "forceCoeffs").glob("*/coefficient.dat"))
        n_iter = 0
        if files:
            last = [ln for ln in files[-1].read_text().splitlines() if ln and not ln.startswith("#")]
            n_iter = int(float(last[-1].split()[0])) if last else 0
        out["iterations"] = n_iter
        out["converged"] = n_iter < int(d["maxIter"]) or self.converged(case_dir, p, d)
        yp = sorted((case_dir / "postProcessing" / "yPlus").glob("*/yPlus.dat"))
        if yp:
            rows = [ln.split() for ln in yp[-1].read_text().splitlines() if ln and not ln.startswith("#")]
            vals = [list(map(float, r[2:5])) for r in rows if len(r) >= 5 and r[1].startswith("appendages")]
            if vals:
                out["yplus_max"] = max(v[1] for v in vals)
                out["yplus_mean"] = float(np.mean([v[2] for v in vals]))
        if not out["converged"]:
            rel = tot.std @ np.abs(dd) / max(abs(out["drag_N"]), 1e-9)
            out["_status"] = "ok" if rel < 0.01 else "not_converged"
        return out

    def mesh_views(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]):
        from iomcfd.meshplot import MeshSpec, MeshView, boat_view

        bb = d.get("bodyBoxBoat") or [*(d.get("bodyMin") or d["nearBoxMin"]), *(d.get("bodyMax") or d["nearBoxMax"])]
        h = float(d["baseCell"])
        eps = 0.0137 * h  # keep cut planes off background-mesh planes
        zt = -float(p["hull_depth"])
        zm = zt - 0.5 * float(p["fin_span"])
        chord = 0.5 * (float(p["fin_root_chord"]) + float(p["fin_tip_chord"]))
        xf = float(p["fin_x"]) + 0.5 * chord
        kw = dict(heel=float(p["heel"]), pivot=(0.0, 0.0, zt))
        return MeshSpec(
            [
                boat_view("side, fin plane: fin, bulb, rudder", "side", eps, ((bb[0] + bb[3]) / 2, (bb[2] + zt) / 2),
                          1.15 * (bb[3] - bb[0]), **kw),
                MeshView("whole domain, plane y = 0", (0.0, eps, 0.0), (0.0, 1.0, 0.0), (0, 2),
                         ((d["xMin"] + d["xMax"]) / 2, (d["zMin"] + d["zMax"]) / 2), 1.02 * (d["xMax"] - d["xMin"]),
                         ("x [m]", "z [m]"), lw=0.15),
                boat_view(f"fin section at mid-span ({abs(zm - zt):.2f} m below the root)", "section", zm + eps,
                          (xf, 0.0), 2.2 * chord, **kw),
                boat_view("fin trailing edge: prism layers", "section", zm + eps, (xf + 0.45 * chord, 0.0), 0.35 * chord, **kw),
            ],
            walls="appendages(_.*)?",
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        cells = {"xcoarse": 0.3, "coarse": 0.8, "medium": 3, "fine": 12}[p.get("mesh", "medium")]  # millions
        return {"cpus": int(p.get("np", 8)), "memory_gb": max(4, int(3 * cells)), "max_hours": 1 + cells}

    def report(self, df, out_dir: Path, reference=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])]
        if df.empty:
            return []
        x = "leeway" if df["leeway"].nunique() > 1 else ("speed" if df["speed"].nunique() > 1 else "case")
        other = [c for c in ("speed", "heel", "rudder_angle", "fin_section", "mesh") if c != x and c in df and df[c].nunique() > 1]
        fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
        for key, g in (df.groupby(other) if other else [("all", df)]):
            g = g.sort_values(x)
            lab = str(key)
            axs[0].plot(g[x], g["side_N"], "o-", label=lab)
            axs[1].plot(g[x], g["drag_N"], "o-", label=lab)
            axs[2].plot(g["drag_N"], g["side_N"], "o-", label=lab)
        for ax, (xl, yl) in zip(axs, [(x, "side force [N]"), (x, "drag [N]"), ("drag [N]", "side force [N]")]):
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.grid(alpha=0.3)
        axs[0].legend(fontsize=7)
        fig.tight_layout()
        f = out_dir / "appendage_forces.png"
        fig.savefig(f, dpi=130)
        plt.close(fig)
        return [f]
