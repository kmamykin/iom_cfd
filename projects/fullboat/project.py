"""fullboat (EXPERIMENTAL): hull + appendages in water, rig in air (interFoam).

Builds the geometry with the hull and sails projects' generators, places the
whole boat at the requested heel/leeway/trim/sinkage, and reports
hydrodynamic and aerodynamic forces plus the residual (imbalance) force and
moment about the centre of gravity including the weight. A boat sailing in
equilibrium has zero imbalance in surge (x), sway (y), roll and yaw.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import physics
from iomcfd.foam import find_dat, read_dat
from iomcfd.forces import forces_function, read_forces, settled
from iomcfd.geometry import hulls, stl
from iomcfd.geometry.distributions import graded_section
from iomcfd.project import Project, load_project

# base: background cells per hull length; dz: free-surface cell size / L;
# rig: refinement on the sails, rigBox: around them.
MESH_LEVELS = {
    "xcoarse": dict(base=8, dz=1 / 80, near=1, wave=0, surf=(2, 3), feat=3, layers=2, rig=(3, 3), rigbox=1),
    "coarse": dict(base=12, dz=1 / 120, near=2, wave=1, surf=(3, 4), feat=4, layers=3, rig=(4, 4), rigbox=2),
    "medium": dict(base=16, dz=1 / 200, near=2, wave=1, surf=(4, 5), feat=5, layers=3, rig=(4, 5), rigbox=2),
}



class FullBoat(Project):
    name = "fullboat"
    summary_keys = ["net_Fx_N", "net_Fy_N", "net_Mx_Nm", "net_Mz_Nm"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        water = physics.fluid("water", p["temperature"])
        air = physics.air(p["temperature"])
        V, W = float(p["speed"]), float(p["tws"])
        twa = math.radians(float(p["twa"]))
        # course frame (surfaces() turns the boat by the leeway): water flows
        # aft (+x); true wind from port, twa off the course, blows towards
        # +x/-y, and the apparent wind adds the boat's own motion.
        u_air = [W * math.cos(twa) + V, -W * math.sin(twa), 0.0]
        aws = math.hypot(u_air[0], u_air[1])
        tw = physics.turbulence_inflow(V, water.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        ta = physics.turbulence_inflow(aws, air.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        return {
            "rhoWater": water.rho, "nuWater": water.nu, "rhoAir": air.rho, "nuAir": air.nu,
            "boatSpeed": V,
            "Uwater": [V, 0.0, 0.0],
            "Uair": u_air,
            "aws": aws,
            "awa_deg": math.degrees(math.atan2(-u_air[1], u_air[0])),
            "kWater": tw.k, "omegaWater": tw.omega, "kAir": ta.k, "omegaAir": ta.omega,
            "ddtScheme": "localEuler",
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
        }

    def surfaces(self, p: dict[str, Any]) -> list[stl.Surface]:
        hull_p = {**load_project("hull").defaults, **{k: p[k] for k in (
            "hull", "wigley_length", "wigley_beam", "wigley_draft", "freeboard", "stl_scale", "stl_rotate",
            "stl_translate", "appendages", "appendage_params", "extra_stl")}}
        boat = load_project("hull").boat_surfaces({**hull_p, "heel": 0, "trim": 0, "leeway": 0, "sinkage": 0})
        sails_p = {**load_project("sails").defaults, **{k: p[k] for k in (
            "main_sheet", "jib_sheet", "main_twist", "jib_twist", "camber", "deck")},
            "rig": p["rig"], "stl_files": p["rig_stl_files"], "heel": 0}
        rig = load_project("sails").rig_surfaces(sails_p)
        lo, hi = boat[0].bounds
        mid = (0.5 * (lo[0] + hi[0]), 0.0, 0.0)
        out = []
        for s in boat + rig:
            if float(p["heel"]):
                s = s.rotated("x", float(p["heel"]), about=mid)
            if float(p["trim"]):
                s = s.rotated("y", -float(p["trim"]), about=mid)
            if float(p["leeway"]):
                s = s.rotated("z", -float(p["leeway"]), about=mid)
            if float(p["sinkage"]):
                s = s.translated((0, 0, -float(p["sinkage"])))
            out.append(s)
        return out

    def _boat_boxes(self, p: dict[str, Any]) -> dict[str, list[float]]:
        """Upright hull and rig bounding boxes (no heel/trim/leeway/sinkage)."""
        up = self.surfaces({**p, "heel": 0, "trim": 0, "leeway": 0, "sinkage": 0})
        box = lambda ss: [float(v) for v in (*np.min([s.bounds[0] for s in ss], axis=0),
                                              *np.max([s.bounds[1] for s in ss], axis=0))]
        rig = [s for s in up if s.name in ("main", "jib", "mast")]
        return {"hullBoxBoat": box(up[:1]), "rigBoxBoat": box(rig)}

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        surfs = self.surfaces(p)
        boat = [s for s in surfs if s.name not in ("main", "jib", "mast")]
        rig = [s for s in surfs if s.name in ("main", "jib", "mast")]
        tri = case_dir / "constant" / "triSurface"
        stl.write_multi(tri / "boat.stl", boat)
        for s in rig:
            s.write(tri / f"{s.name}.stl")

        hull = boat[0]
        hlo, hi_ = hull.bounds
        L = hulls.waterline_length(hull)
        rlo = np.min([s.bounds[0] for s in rig], axis=0)
        rhi = np.max([s.bounds[1] for s in rig], axis=0)
        H = float(rhi[2])
        lv = MESH_LEVELS[p["mesh"]]
        h = L / lv["base"]
        dzb = L * lv["dz"]
        x0, x1 = hlo[0] - 1.5 * L, hi_[0] + 3.5 * L
        nx = math.ceil((x1 - x0) / h)
        x1 = x0 + nx * h
        y0, y1 = -2.0 * L - 1.5 * H, 2.0 * L
        ny = math.ceil((y1 - y0) / h)
        y0 = y1 - ny * h
        z0, z1 = -1.5 * L, H + 1.0 * H
        band_lo, band_hi = 0.06 * L, 0.05 * L
        nwb = math.ceil(band_lo / dzb)
        nwd, gw = graded_section(-z0 - band_lo, dzb, h)
        nab = math.ceil(band_hi / dzb)
        nah, ga = graded_section(z1 - band_hi, dzb, 2 * h)
        nzw, nza = nwb + nwd, nab + nah
        m = 0.15 * L
        cog = p["cog"] or [0.5 * (hlo[0] + hi_[0]), 0.0, -0.15]
        mr = 0.1 * H
        d.update({
            "Lwl": L, "Fn": physics.froude(d["boatSpeed"], L),
            "xMin": x0, "xMax": x1, "yMin": y0, "yMax": y1, "zMin": z0, "zMax": z1,
            "nx": nx, "ny": ny, "nzWater": nzw, "nzAir": nza,
            "wFracDeep": (-z0 - band_lo) / -z0, "wNFracDeep": nwd / nzw, "wGrade": 1.0 / gw,
            "wFracBand": band_lo / -z0, "wNFracBand": nwb / nzw,
            "aFracBand": band_hi / z1, "aNFracBand": nab / nza,
            "aFracHigh": (z1 - band_hi) / z1, "aNFracHigh": nah / nza, "aGrade": ga,
            "nearBoxMin": [float(hlo[0] - m), float(hlo[1] - m), float(min(hlo[2] - m, -band_lo))],
            "nearBoxMax": [float(hi_[0] + m), float(hi_[1] + m), band_hi + m],
            "nearBoxLevel": lv["near"],
            "waveBoxMin": [float(hlo[0] - 0.3 * L), -1.1 * L, -band_lo],
            "waveBoxMax": [float(hi_[0] + 1.5 * L), 1.1 * L, band_hi],
            "waveBoxLevel": lv["wave"],
            "rigBoxMin": [float(rlo[0] - mr), float(rlo[1] - mr), float(max(rlo[2] - mr, band_hi))],
            "rigBoxMax": [float(rhi[0] + mr), float(rhi[1] + mr), float(rhi[2] + mr)],
            "rigBoxLevel": lv["rigbox"],
            "surfaceLevelMin": lv["surf"][0], "surfaceLevelMax": lv["surf"][1],
            "featureLevel": lv["feat"], "nLayers": lv["layers"],
            "rigLevelMin": lv["rig"][0], "rigLevelMax": lv["rig"][1], "rigFeatureLevel": lv["rig"][1],
            "locationInMesh": [x0 + 0.0371 * (x1 - x0), y0 + 0.6123 * (y1 - y0), z0 + 0.3137 * (-z0)],
            "cog": [float(c) for c in cog],
            "components": [s.name for s in surfs],
            "hullMin": [float(v) for v in hlo], "hullMax": [float(v) for v in hi_],
            "rigMin": [float(v) for v in rlo], "rigMax": [float(v) for v in rhi],
            **self._boat_boxes(p),
        })
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        cofr = "(" + " ".join(f"{c:.6g}" for c in cog) + ")"
        fo = [forces_function(f"forces_{s.name}", [f"boat_{s.name}"], rho_var=None, cofr=cofr) for s in boat]
        fo += [forces_function("forces_main", ['"main.*"'], rho_var=None, cofr=cofr),
               forces_function("forces_jib", ['"jib.*"'], rho_var=None, cofr=cofr),
               forces_function("forces_mast", ["mast"], rho_var=None, cofr=cofr),
               forces_function("forces_hydro", ["boat"], rho_var=None, cofr=cofr),
               forces_function("forces_aero", ["rig"], rho_var=None, cofr=cofr)]
        (inc / "forceFunctions").write_text("// generated by iomcfd\n\n" + "\n".join(fo))
        (inc / "timeControl").write_text(
            "endTime         $maxIter;\ndeltaT          1;\nwriteControl    timeStep;\nwriteInterval   $maxIter;\n")
        (inc / "pimple").write_text(
            "PIMPLE\n{\n    momentumPredictor   no;\n    nOuterCorrectors    1;\n    nCorrectors         2;\n"
            "    nNonOrthogonalCorrectors 0;\n    maxCo               5;\n    maxAlphaCo          2;\n"
            "    rDeltaTSmoothingCoeff 0.05;\n    rDeltaTDampingCoeff 0.5;\n    nAlphaSpreadIter    0;\n"
            "    nAlphaSweepIter     0;\n    maxDeltaT           1;\n}\n")
        from iomcfd.foam import HEADER

        (case_dir / "constant" / "dynamicMeshDict").write_text(
            HEADER.format(cls="dictionary", obj="dynamicMeshDict") + "dynamicFvMesh   staticFvMesh;\n")
        self.write_parameters(case_dir, d, inputs=p)

    # ------------------------------------------------------------------
    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        out = []
        for fo in ("forces_hydro", "forces_aero"):
            ff = find_dat(case_dir, fo, "force.dat")
            if not ff:
                return False
            _, f = read_dat(ff[-1])
            if f.size == 0:
                return False
            fx, fy = f[:, 1], f[:, 2]
            sc = max(abs(fx[-1]), abs(fy[-1]))
            out += [settled(fx, int(d["convWindow"]), float(p["conv_tol"]), sc),
                    settled(fy, int(d["convWindow"]), float(p["conv_tol"]), sc)]
        return all(out)

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        w = int(d["convWindow"])
        hyd = read_forces(case_dir, "forces_hydro", w)
        aer = read_forces(case_dir, "forces_aero", w)
        if hyd is None or aer is None:
            return {"_status": "failed"}
        g = 9.81
        weight = np.array([0.0, 0.0, -float(p["mass"]) * g])
        F = hyd.total + aer.total + weight  # buoyancy is in the hydro pressure force
        M = hyd.moment + aer.moment  # about the CoG, where the weight has no moment
        out: dict[str, Any] = {
            "resistance_N": float(hyd.total[0]),
            "hydro_side_N": float(hyd.total[1]),
            "hydro_vertical_N": float(hyd.total[2]),
            "drive_N": float(-aer.total[0]),
            "heel_force_N": float(-aer.total[1]),
            "aero_heel_moment_Nm": float(aer.moment[0]),
            "hydro_righting_moment_Nm": float(-hyd.moment[0]),
            "net_Fx_N": float(F[0]),
            "net_Fy_N": float(F[1]),
            "net_Fz_N": float(F[2]),
            "net_Mx_Nm": float(M[0]),
            "net_My_Nm": float(M[1]),
            "net_Mz_Nm": float(M[2]),
        }
        for comp in d.get("components", []):
            r = read_forces(case_dir, f"forces_{comp}", w)
            if r is not None:
                out[f"Fx_{comp}_N"] = float(r.total[0])
                out[f"Fy_{comp}_N"] = float(r.total[1])
        ff = find_dat(case_dir, "forces_hydro", "force.dat")
        n_iter = int(read_dat(ff[-1])[1][-1, 0]) if ff else 0
        out["iterations"] = n_iter
        out["converged"] = n_iter < int(d["maxIter"]) or self.converged(case_dir, p, d)
        if not out["converged"]:
            out["_status"] = "not_converged"
        return out

    def mesh_views(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]):
        from iomcfd.meshplot import MeshSpec, MeshView, boat_view

        hb = d.get("hullBoxBoat") or [*(d.get("hullMin") or d["nearBoxMin"]), *(d.get("hullMax") or d["nearBoxMax"])]
        rb = d.get("rigBoxBoat") or [*(d.get("rigMin") or d["rigBoxMin"]), *(d.get("rigMax") or d["rigBoxMax"])]
        L, H = float(d["Lwl"]), float(rb[5])
        eps = 0.00137 * L
        xm = 0.5 * (hb[0] + hb[3])
        zs = 0.45 * H
        kw = dict(heel=float(p["heel"]), pivot=(xm, 0.0, 0.0))
        return MeshSpec(
            [
                boat_view("centre plane: hull, keel and rig", "side", -eps, (xm, 0.5 * (hb[2] - 0.42 + rb[5])),
                          1.15 * max(hb[3] - hb[0], rb[5] - hb[2] + 0.42), **kw),
                boat_view("centre plane: hull and free-surface band", "side", -eps, (xm, 0.0), 1.2 * (hb[3] - hb[0]), **kw),
                boat_view(f"section through the sails ({zs:.2f} m up)", "section", zs + eps,
                          (0.5 * (rb[0] + rb[3]), 0.5 * (rb[1] + rb[4])), 1.3 * (rb[3] - rb[0]), **kw),
                MeshView("whole domain, plane y = 0", (0.0, -eps, 0.0), (0.0, 1.0, 0.0), (0, 2),
                         ((d["xMin"] + d["xMax"]) / 2, (d["zMin"] + d["zMax"]) / 2), 1.02 * (d["xMax"] - d["xMin"]),
                         ("x [m]", "z [m]"), lw=0.15),
            ],
            walls="(boat(_.*)?|main.*|jib.*|mast)",
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        cells = {"xcoarse": 0.5, "coarse": 1.5, "medium": 5}[p.get("mesh", "medium")]
        return {"cpus": int(p.get("np", 16)), "memory_gb": max(8, int(4 * cells)), "max_hours": 2 + 3 * cells}
