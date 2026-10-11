"""hull: calm-water resistance (interFoam VOF), fixed or free sinkage/trim.

Fixed attitude uses local time stepping (pseudo-steady, like the DTCHull
tutorial) and converges in a few thousand iterations. Free attitude solves
the transient rigid-body motion in heave and pitch (like DTCHullMoving) and
is several times more expensive.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.foam import HEADER, find_dat, read_dat
from iomcfd.forces import forces_function, read_forces, settled
from iomcfd.geometry import hulls, stl
from iomcfd.geometry.distributions import graded_section
from iomcfd.project import Project, load_project

# base: background cells per waterline length; dzBand: free-surface cell
# height as a fraction of L; the rest are snappyHexMesh refinement levels.
MESH_LEVELS = {
    "xcoarse": dict(base=8, dz=1 / 80, near=1, wave=0, surf=(2, 3), feat=3, layers=2),
    "coarse": dict(base=12, dz=1 / 120, near=2, wave=1, surf=(3, 4), feat=4, layers=3),
    "medium": dict(base=16, dz=1 / 200, near=2, wave=1, surf=(4, 5), feat=5, layers=3),
    "fine": dict(base=24, dz=1 / 300, near=3, wave=2, surf=(4, 5), feat=5, layers=4),
}



class Hull(Project):
    name = "hull"
    summary_keys = ["resistance_N", "Ct", "Fn"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        water = physics.fluid(p["fluid"], p["temperature"])
        air = physics.air(p["temperature"])
        V = float(p["speed"])
        turb = physics.turbulence_inflow(V, water.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        return {
            "rhoWater": water.rho,
            "nuWater": water.nu,
            "rhoAir": air.rho,
            "nuAir": air.nu,
            "magUInf": V,
            "Uinf": [V, 0.0, 0.0],
            "kInf": turb.k,
            "omegaInf": turb.omega,
            "nutInf": turb.nut,
            "ddtScheme": "localEuler" if p["attitude"] == "fixed" else "Euler",
        }

    # ------------------------------------------------------------------
    def boat_surfaces(self, p: dict[str, Any]) -> list[stl.Surface]:
        spec = str(p["hull"])
        if spec == "wigley":
            hull = hulls.wigley(p["wigley_length"], p["wigley_beam"], p["wigley_draft"], p["freeboard"])
        else:
            hull = stl.read(config.geometry_dir() / spec.removeprefix("file:"), "hull")
            hull = hull.scaled(float(p["stl_scale"]))
            for axis, deg in p["stl_rotate"] or []:
                hull = hull.rotated(axis, float(deg))
            hull = hull.translated(p["stl_translate"])
            hull.name = "hull"
        out = [hull]
        if p["appendages"]:
            app = load_project("appendage3d")
            ap = {**app.defaults, **(p["appendage_params"] or {})}
            out += app.surfaces({**ap, "heel": 0.0})
        for f in p["extra_stl"] or []:
            s = stl.read(config.geometry_dir() / f).scaled(float(p["stl_scale"]))
            for axis, deg in p["stl_rotate"] or []:
                s = s.rotated(axis, float(deg))
            out.append(s.translated(p["stl_translate"]))
        # attitude: sinkage/trim/heel/yaw about midship on the waterline
        lo, hi = hull.bounds
        mid = (0.5 * (lo[0] + hi[0]), 0.0, 0.0)
        tf = []
        for s in out:
            if float(p["heel"]):
                s = s.rotated("x", float(p["heel"]), about=mid)
            if float(p["trim"]):
                s = s.rotated("y", -float(p["trim"]), about=mid)
            if float(p["leeway"]):
                s = s.rotated("z", -float(p["leeway"]), about=mid)
            if float(p["sinkage"]):
                s = s.translated((0, 0, -float(p["sinkage"])))
            tf.append(s)
        return tf

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        surfs = self.boat_surfaces(p)
        stl.write_multi(case_dir / "constant" / "triSurface" / "boat.stl", surfs)
        hull = surfs[0]
        lo, hi = hull.bounds
        L = hulls.waterline_length(hull)
        half = p["half_domain"] == "auto" and not float(p["heel"]) and not float(p["leeway"]) and not p["extra_stl"]
        half = half or p["half_domain"] is True
        lv = MESH_LEVELS[p["mesh"]]
        h = L / lv["base"]
        dzb = L * lv["dz"]

        # domain: 1.5 L ahead, 3.5 L behind, 2 L to the sides, 1.5 L deep
        x0, x1 = lo[0] - 1.5 * L, hi[0] + 3.5 * L
        nx = math.ceil((x1 - x0) / h)
        x1 = x0 + nx * h
        y0, y1 = -2.0 * L, (0.0 if half else 2.0 * L)
        ny = math.ceil((y1 - y0) / h)
        y0 = y1 - ny * h
        z0, z1 = -1.5 * L, max(0.6 * L, hi[2] + 0.3 * L)
        zb0, zb1 = -0.06 * L, 0.05 * L  # free-surface band
        nb = math.ceil((zb1 - zb0) / dzb)
        nbelow, gbelow = graded_section(zb0 - z0, dzb, h)
        nabove, gabove = graded_section(z1 - zb1, dzb, h)
        nz = nb + nbelow + nabove
        H = z1 - z0

        V = d["magUInf"]
        m = 0.15 * L
        near_lo = [lo[0] - m, lo[1] - m, min(lo[2] - m, zb0)]
        near_hi = [hi[0] + m, hi[1] + m, zb1 + m]
        # Kelvin wedge half-angle 19.5 deg: |y| < 0.35 (x - x_bow) covers it
        wave_lo = [lo[0] - 0.3 * L, -(0.35 * 2.5 * L + 0.2 * L), zb0]
        wave_hi = [hi[0] + 1.5 * L, (0.0 if half else 0.35 * 2.5 * L + 0.2 * L) + h, zb1]
        loc = [x0 + 0.0371 * (x1 - x0), y0 + 0.2123 * (y1 - y0), z0 + 0.3137 * H]

        cog = p["cog"] or [0.5 * (lo[0] + hi[0]), 0.0, 0.0]
        d.update({
            "Lwl": L,
            "Fn": physics.froude(V, L),
            "Re_L": V * L / d["nuWater"],
            "halfDomain": half,
            "xMin": x0, "xMax": x1, "yMin": y0, "yMax": y1, "zMin": z0, "zMax": z1,
            "nx": nx, "ny": ny, "nz": nz,
            "zFracBelow": (zb0 - z0) / H, "zFracBand": (zb1 - zb0) / H, "zFracAbove": (z1 - zb1) / H,
            "nzFracBelow": nbelow / nz, "nzFracBand": nb / nz, "nzFracAbove": nabove / nz,
            "zGradeBelow": 1.0 / gbelow, "zGradeAbove": gabove,
            "nearBoxMin": near_lo, "nearBoxMax": near_hi, "nearBoxLevel": lv["near"],
            "waveBoxMin": wave_lo, "waveBoxMax": wave_hi, "waveBoxLevel": lv["wave"],
            "surfaceLevelMin": lv["surf"][0], "surfaceLevelMax": lv["surf"][1],
            "featureLevel": lv["feat"], "nLayers": lv["layers"],
            "locationInMesh": loc,
            "cog": [float(c) for c in cog],
            "wetted_area_m2": hulls.wetted_area_below(hull),  # whole hull at rest
            "components": [s.name for s in surfs],
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
        })
        if p["hull"] == "wigley":
            d["displacement_kg"] = hulls.wigley_displacement(p["wigley_length"], p["wigley_beam"], p["wigley_draft"]) * d["rhoWater"]

        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        cofr = "(" + " ".join(f"{c:.6g}" for c in cog) + ")"
        # interFoam: forces use the rho field (rho_var=None)
        fo = [forces_function(f"forces_{s.name}", [f"boat_{s.name}"], rho_var=None, cofr=cofr) for s in surfs]
        fo.append(forces_function("forces_total", ["boat"], rho_var=None, cofr=cofr, interval=1))
        (inc / "forceFunctions").write_text("// generated by iomcfd\n\n" + "\n".join(fo))

        if p["attitude"] == "fixed":
            (inc / "timeControl").write_text(
                "endTime         $maxIter;\ndeltaT          1;\nwriteControl    timeStep;\n"
                "writeInterval   $maxIter;\n"
            )
            (inc / "pimple").write_text(
                "PIMPLE\n{\n    momentumPredictor   no;\n    nOuterCorrectors    1;\n    nCorrectors         2;\n"
                "    nNonOrthogonalCorrectors 0;\n    maxCo               10;\n    maxAlphaCo          5;\n"
                "    rDeltaTSmoothingCoeff 0.05;\n    rDeltaTDampingCoeff 0.5;\n    nAlphaSpreadIter    0;\n"
                "    nAlphaSweepIter     0;\n    maxDeltaT           1;\n}\n"
            )
            dyn = "dynamicFvMesh   staticFvMesh;\n"
        else:
            (inc / "timeControl").write_text(
                f"endTime         {float(p['sim_time'])};\ndeltaT          1e-4;\nwriteControl    adjustable;\n"
                "writeInterval   1;\nadjustTimeStep  yes;\nmaxCo           10;\nmaxAlphaCo      5;\nmaxDeltaT       0.01;\n"
            )
            (inc / "pimple").write_text(
                "PIMPLE\n{\n    momentumPredictor   no;\n    nOuterCorrectors    2;\n    nCorrectors         2;\n"
                "    nNonOrthogonalCorrectors 0;\n    correctPhi          yes;\n    moveMeshOuterCorrectors no;\n"
                "    turbOnFinalIterOnly yes;\n}\n"
            )
            I = p["inertia"]
            mass = float(p["mass"])
            dyn = (
                "dynamicFvMesh   dynamicMotionSolverFvMesh;\nmotionSolverLibs (rigidBodyMeshMotion);\n"
                "motionSolver    rigidBodyMotion;\nreport          on;\nsolver { type Newmark; }\n"
                "accelerationRelaxation 0.4;\n\nbodies\n{\n    hull\n    {\n        type            rigidBody;\n"
                "        parent          root;\n        centreOfMass    (0 0 0);\n"
                f"        mass            {mass};\n"
                f"        inertia         ({' '.join(str(float(x)) for x in I)});\n"
                f"        transform       (1 0 0 0 1 0 0 0 1) {cofr};\n"
                "        joint\n        {\n            type    composite;\n"
                "            joints ( { type Pz; } { type Ry; } );   // sinkage and trim\n        }\n"
                "        patches         (boat);\n"
                f"        innerDistance   {0.05 * L:.4g};\n        outerDistance   {0.3 * L:.4g};\n    }}\n}}\n\n"
                "restraints\n{\n"
                f"    translationDamper {{ type linearDamper; body hull; coeff {20 * mass:.4g}; }}\n"
                f"    rotationDamper    {{ type sphericalAngularDamper; body hull; coeff {12 * float(I[3]):.4g}; }}\n}}\n"
            )
        (case_dir / "constant" / "dynamicMeshDict").write_text(HEADER.format(cls="dictionary", obj="dynamicMeshDict") + dyn)
        self.write_parameters(case_dir, d, inputs=p)

    # ------------------------------------------------------------------
    def _resistance_series(self, case_dir: Path):
        ff = find_dat(case_dir, "forces_total", "force.dat")
        if not ff:
            return None
        _, f = read_dat(ff[-1])
        return f if f.size else None

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        if p["attitude"] != "fixed":
            return False
        f = self._resistance_series(case_dir)
        if f is None:
            return False
        rx = f[:, 1]
        return settled(rx, int(d["convWindow"]), float(p["conv_tol"]), abs(rx[-1]))

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        tot = read_forces(case_dir, "forces_total", int(d["convWindow"]))
        if tot is None:
            return {"_status": "failed"}
        k = 2.0 if d["halfDomain"] else 1.0
        V, rho = d["magUInf"], d["rhoWater"]
        S = d["wetted_area_m2"]
        out: dict[str, Any] = {
            "resistance_N": k * float(tot.total[0]),
            "resistance_friction_N": k * float(tot.viscous[0]),
            "resistance_pressure_N": k * float(tot.pressure[0]),
            "vertical_force_N": k * float(tot.total[2]),
            "side_force_N": 0.0 if d["halfDomain"] else float(tot.total[1]),
            "pitch_moment_Nm": k * float(tot.moment[1]),
            "resistance_std_N": k * float(tot.std[0]),
        }
        q = 0.5 * rho * V**2 * S
        out["Ct"] = out["resistance_N"] / q
        re = d["Re_L"]
        out["Cf_ittc57"] = 0.075 / (math.log10(re) - 2) ** 2
        out["Cr"] = out["Ct"] - out["Cf_ittc57"]
        for comp in d.get("components", []):
            r = read_forces(case_dir, f"forces_{comp}", int(d["convWindow"]))
            if r is not None:
                out[f"resistance_{comp}_N"] = k * float(r.total[0])
        f = self._resistance_series(case_dir)
        out["iterations"] = int(f[-1, 0]) if p["attitude"] == "fixed" and f is not None else None
        if p["attitude"] == "fixed":
            out["converged"] = self.converged(case_dir, p, d) or (out["iterations"] or 0) < int(d["maxIter"])
            if not out["converged"]:
                out["_status"] = "not_converged"
        else:
            out.update(self._motion(case_dir, d))
        return out

    def _motion(self, case_dir: Path, d: dict[str, Any]) -> dict[str, Any]:
        """Final sinkage/trim from the rigid-body status lines in the solver log:
        'Centre of rotation: (x y z)' and 'Orientation: (9 components)'."""
        log = case_dir / "log.interFoam"
        if not log.is_file():
            return {}
        cor = ori = None
        for line in log.read_text(errors="replace").splitlines():
            if "Centre of rotation:" in line:
                cor = line
            elif "Orientation:" in line:
                ori = line
        out: dict[str, Any] = {}
        if cor:
            v = [float(x) for x in cor.split(":", 1)[1].strip(" ()").split()]
            out["sinkage_m"] = float(d["cog"][2]) - v[2]  # + = down
        if ori:
            E = [float(x) for x in ori.split(":", 1)[1].strip(" ()").split()]
            # rotation about +y; bow is at small x, so bow-down trim = -pitch
            out["trim_deg"] = -math.degrees(math.atan2(-E[6], E[0]))
        return out

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        cells = {"xcoarse": 0.15, "coarse": 0.4, "medium": 1.2, "fine": 4}[p.get("mesh", "medium")]
        hours = (1 + 3 * cells) * (6 if p.get("attitude") == "free" else 1)
        return {"cpus": int(p.get("np", 8)), "memory_gb": max(4, int(4 * cells)), "max_hours": hours}

    def report(self, df, out_dir: Path, reference=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])].sort_values("speed")
        if df.empty:
            return []
        other = [c for c in ("hull", "heel", "leeway", "trim", "sinkage", "mesh", "attitude") if c in df and df[c].nunique() > 1]
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
        for key, g in (df.groupby(other) if other else [("", df)]):
            lab = str(key) if other else "CFD"
            axs[0].plot(g["speed"], g["resistance_N"], "o-", label=lab)
            axs[1].plot(g["Fn"], g["Ct"] * 1e3, "o-", label=f"Ct {lab}")
            axs[1].plot(g["Fn"], g["Cr"] * 1e3, "s--", label=f"Cr {lab}")
        axs[0].set_xlabel("speed [m/s]"); axs[0].set_ylabel("resistance [N]")
        axs[1].set_xlabel("Froude number"); axs[1].set_ylabel("coefficient x 1000")
        for ax in axs:
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7)
        fig.tight_layout()
        f = out_dir / "resistance.png"
        fig.savefig(f, dpi=130)
        plt.close(fig)
        return [f]


def _isnum(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
