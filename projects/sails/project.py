"""sails: rigid mainsail + jib + mast in uniform apparent wind (simpleFoam).

Gives driving force, heeling (side) force, heeling moment and centre of
effort for a sail trim (sheet, twist, camber), apparent wind and heel angle.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.foam import find_dat, read_dat
from iomcfd.forces import forces_function, read_forces, settled
from iomcfd.geometry import sails, stl
from iomcfd.project import Project

# Background cell = rig height / 12 (~0.15 m); level 5 on the sails ~ 4.5 mm.
MESH_LEVELS = {
    "xcoarse": dict(surf=(3, 4), feat=4, near=1, wake=1),
    "coarse": dict(surf=(4, 5), feat=5, near=2, wake=1),
    "medium": dict(surf=(5, 6), feat=6, near=3, wake=2),
    "fine": dict(surf=(6, 7), feat=7, near=4, wake=2),
}


class Sails(Project):
    name = "sails"
    summary_keys = ["drive_N", "heel_force_N", "z_ce"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        a = physics.air(p["temperature"])
        awa = math.radians(float(p["awa"]))
        # apparent wind blows towards +x (aft) and -y (to starboard) for wind from port
        drag_dir = [math.cos(awa), -math.sin(awa), 0.0]
        lift_dir = [math.sin(awa), math.cos(awa), 0.0]  # horizontal, towards windward-forward
        V = float(p["aws"])
        turb = physics.turbulence_inflow(V, a.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        return {
            "rhoInf": a.rho,
            "nu": a.nu,
            "magUInf": V,
            "Uinf": [V * c for c in drag_dir],
            "dragDir": drag_dir,
            "liftDir": lift_dir,
            "dynamicPressure": 0.5 * a.rho * V**2,
            "turbModel": p["turbulence"],
            "kInf": turb.k,
            "omegaInf": turb.omega,
            "nutInf": turb.nut,
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
            "nLayers": int(p["n_layers"]),
        }

    def rig_surfaces(self, p: dict[str, Any]) -> list[stl.Surface]:
        if p["rig"] == "iom_a":
            out = sails.iom_a_rig(p["main_sheet"], p["jib_sheet"], p["main_twist"], p["jib_twist"],
                                  p["camber"], p["deck"])
        elif p["rig"] == "stl":
            out = []
            for name, f in (p["stl_files"] or {}).items():
                s = stl.read(config.geometry_dir() / f, name).scaled(float(p["stl_scale"]))
                for axis, deg in p["stl_rotate"] or []:
                    s = s.rotated(axis, float(deg))
                s = s.translated(p["stl_translate"])
                s.name = name
                out.append(s)
            if {s.name for s in out} != {"main", "jib", "mast"}:
                raise ValueError("rig: stl needs stl_files with keys main, jib and mast")
        else:
            raise ValueError("rig must be 'iom_a' or 'stl'")
        if float(p["heel"]):
            out = [s.rotated("x", float(p["heel"])) for s in out]
        return out

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        surfs = self.rig_surfaces(p)
        tri = case_dir / "constant" / "triSurface"
        for s in surfs:
            s.write(tri / f"{s.name}.stl")
        lo = np.min([s.bounds[0] for s in surfs], axis=0)
        hi = np.max([s.bounds[1] for s in surfs], axis=0)
        H = float(hi[2])
        lv = MESH_LEVELS[p["mesh"]]
        h = H / 12
        sa = abs(math.sin(math.radians(float(p["awa"]))))
        x0, x1 = lo[0] - 2.0 * H, hi[0] + 4.0 * H
        y0, y1 = lo[1] - 2.0 * H - 3.0 * H * sa, hi[1] + 2.0 * H
        z0, z1 = 0.0, 2.5 * H
        n = [math.ceil((x1 - x0) / h), math.ceil((y1 - y0) / h), math.ceil((z1 - z0) / h)]
        x1, y1, z1 = x0 + n[0] * h, y0 + n[1] * h, z0 + n[2] * h
        m = 0.08 * H
        loc = [x0 + 0.0371 * (x1 - x0), y0 + 0.8123 * (y1 - y0), z0 + 0.3137 * (z1 - z0)]
        d.update({
            "xMin": x0, "xMax": x1, "yMin": y0, "yMax": y1, "zMin": z0, "zMax": z1,
            "nx": n[0], "ny": n[1], "nz": n[2],
            "surfaceLevelMin": lv["surf"][0], "surfaceLevelMax": lv["surf"][1],
            "featureLevel": lv["feat"],
            "nearBoxMin": [float(lo[0] - m), float(lo[1] - m), 0.0],
            "nearBoxMax": [float(hi[0] + m), float(hi[1] + m), float(hi[2] + m)],
            "nearBoxLevel": lv["near"],
            "wakeBoxMin": [float(lo[0] - m), float(lo[1] - m - 1.5 * H * sa), 0.0],
            "wakeBoxMax": [float(hi[0] + 1.5 * H), float(hi[1] + m), float(hi[2] + 2 * m)],
            "wakeBoxLevel": lv["wake"],
            "locationInMesh": loc,
            "sail_area_m2": float(sum(s.area() for s in surfs if s.name != "mast")),
        })
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        fo = [
            forces_function("forces_main", ['"main.*"']),
            forces_function("forces_jib", ['"jib.*"']),
            forces_function("forces_mast", ["mast"]),
            forces_function("forces_total", ["rig"], interval=1),
        ]
        (inc / "forceFunctions").write_text("// generated by iomcfd\n\n" + "\n".join(fo))
        d["Aref"] = d["sail_area_m2"]
        d["lRef"] = H
        self.write_parameters(case_dir, d, inputs=p)

    # ------------------------------------------------------------------
    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        ff = find_dat(case_dir, "forces_total", "force.dat")
        if not ff:
            return False
        _, f = read_dat(ff[-1])
        if f.size == 0:
            return False
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        fx, fy = f[:, 1], f[:, 2]
        scale = max(abs(fx[-1]), abs(fy[-1]))
        return settled(fx, w, tol, scale) and settled(fy, w, tol, scale)

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        tot = read_forces(case_dir, "forces_total", int(d["convWindow"]))
        if tot is None:
            return {"_status": "failed"}
        F, M = tot.total, tot.moment
        out: dict[str, Any] = {
            "drive_N": float(-F[0]),  # boat moves towards -x
            "heel_force_N": float(-F[1]),  # to starboard (leeward) on port tack
            "vertical_N": float(F[2]),
            "heel_moment_Nm": float(M[0]),  # about x at the waterline; + heels to starboard
            "lift_N": float(F @ np.array(d["liftDir"])),
            "drag_N": float(F @ np.array(d["dragDir"])),
        }
        out["z_ce"] = out["heel_moment_Nm"] / out["heel_force_N"] if abs(out["heel_force_N"]) > 1e-9 else None
        qA = d["dynamicPressure"] * d["Aref"]
        out["CL"] = out["lift_N"] / qA
        out["CD"] = out["drag_N"] / qA
        for comp in ("main", "jib", "mast"):
            r = read_forces(case_dir, f"forces_{comp}", int(d["convWindow"]))
            if r is not None:
                out[f"drive_{comp}_N"] = float(-r.total[0])
                out[f"heel_force_{comp}_N"] = float(-r.total[1])
        ff = find_dat(case_dir, "forces_total", "force.dat")
        n_iter = int(read_dat(ff[-1])[1][-1, 0]) if ff else 0
        out["iterations"] = n_iter
        out["converged"] = n_iter < int(d["maxIter"]) or self.converged(case_dir, p, d)
        if not out["converged"]:
            out["_status"] = "not_converged"
        return out

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        cells = {"xcoarse": 0.3, "coarse": 0.8, "medium": 3, "fine": 12}[p.get("mesh", "medium")]
        return {"cpus": int(p.get("np", 8)), "memory_gb": max(4, int(3 * cells)), "max_hours": 1 + cells}

    def report(self, df, out_dir: Path, reference=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])]
        if df.empty:
            return []
        x = next((c for c in ("awa", "main_sheet", "jib_sheet", "heel", "camber", "aws") if df[c].nunique() > 1), "awa")
        fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
        g = df.sort_values(x)
        axs[0].plot(g[x], g["drive_N"], "o-")
        axs[1].plot(g[x], g["heel_force_N"], "o-")
        axs[2].plot(g[x], g["z_ce"], "o-")
        for ax, yl in zip(axs, ["drive force [N]", "heeling force [N]", "centre of effort height [m]"]):
            ax.set_xlabel(x)
            ax.set_ylabel(yl)
            ax.grid(alpha=0.3)
        fig.tight_layout()
        f = out_dir / "sail_forces.png"
        fig.savefig(f, dpi=130)
        plt.close(fig)
        return [f]
