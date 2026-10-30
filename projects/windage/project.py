"""windage: the hull above the water in a uniform apparent wind (simpleFoam
+ kOmegaSST).

The topsides at a heel's attitude (sink, trim: the VPP's static attitude,
`vpp hydro --zip`) are cut at the water plane and closed by their mirror
image below it (iomcfd.geometry.waterline.split); the floor z = 0 is a slip
wall, so the flow is that round the topsides and their reflection. The
apparent wind comes from `awa` off the centreline (wind from port, the boat
heeled to starboard) at `aws`, the same at every height. Gives drag along
the wind and lift across it, their coefficients on the topsides' area
projected normal to the wind (the area the VPP's windage model uses, so cd
compares with its C_D 0.816), moments and the centre of effort.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import physics
from iomcfd.foam import find_dat, read_dat
from iomcfd.forces import forces_function, read_forces, settled, window_drift, window_stats
from iomcfd.geometry import hulls, stl, waterline
from iomcfd.project import Project
from iomcfd.vpp.hydrostatics import projected_area

# Background cell = hull length / 10 (~0.1 m). Surface levels (min, max; max
# where the surface curves): level 4 = 6.3 mm, 5 = 3.1 mm on a 1 m hull.
# near: a box round the topsides; wake: a box downwind of them.
MESH_LEVELS = {
    "xcoarse": dict(surf=(2, 3), feat=3, near=1, wake=1),
    "coarse": dict(surf=(3, 4), feat=4, near=2, wake=1),
    "medium": dict(surf=(4, 5), feat=5, near=2, wake=2),
    "fine": dict(surf=(5, 6), feat=6, near=3, wake=2),
    "xfine": dict(surf=(6, 7), feat=7, near=4, wake=3),
}


def hull_surface(p: dict[str, Any]) -> stl.Surface:
    """The hull in the boat frame, upright: the STL or keel3d's canoe body."""
    return hulls.stl_hull(p["hull_stl"]) if p.get("hull_stl") else hulls.canoe(hulls.CanoeSpec(), "hull")


def attitude(p: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """(R, t): boat frame to earth frame, p_earth = R p_boat + t."""
    return waterline.placement(float(p["heel"]), float(p.get("trim") or 0.0), float(p.get("sink") or 0.0),
                               waterline.trim_axis(hull_surface(p)))


def topsides(p: dict[str, Any]) -> np.ndarray:
    """The hull's triangles above the water at the case's attitude (K, 3, 3)."""
    hull = hull_surface(p)
    R, t = attitude(p)
    return waterline.above_water((hull.vertices @ R.T + t)[hull.triangles])


class Windage(Project):
    name = "windage"
    summary_keys = ["drag_N", "lift_N", "cd", "cl"]
    highlight_columns = ["drag_N", "lift_N", "cd", "cl", "x_ce", "z_ce"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        a = physics.air(p["temperature"])
        awa = math.radians(float(p["awa"]))
        # the apparent wind blows towards +x (aft) and -y (to starboard) for wind from port
        drag_dir = [math.cos(awa), -math.sin(awa), 0.0]
        # horizontal, normal to the wind: its direction turned 90° anticlockwise seen from above (to port for wind
        # from the bow, aft for any wind from port), so lift ahead of the beam is negative: forward and to leeward
        lift_dir = [math.sin(awa), math.cos(awa), 0.0]
        V = float(p["aws"])
        turb = physics.turbulence_inflow(V, a.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        T = topsides(p)
        # the area the wind sees (normal to it, facing where it comes from), as vpp ProjectedArea
        A, c = projected_area(T, (-drag_dir[0], -drag_dir[1], 0.0))
        A90, _ = projected_area(T, (0.0, 1.0, 0.0))  # beam on, from port
        hull = hull_surface(p)
        _, t = attitude(p)
        return {
            "rhoInf": a.rho,
            "nu": a.nu,
            "magUInf": V,
            "Uinf": [V * d for d in drag_dir],
            "dragDir": drag_dir,
            "liftDir": lift_dir,
            "dynamicPressure": 0.5 * a.rho * V**2,
            "Aref": A,  # projected normal to the wind
            "A_beam_m2": A90,
            "centroid": [float(v) for v in c],  # of the projected area (earth frame); z: its height
            "lRef": float(np.ptp(hull.vertices[:, 0])),
            "Re_L": V * float(np.ptp(hull.vertices[:, 0])) / a.nu,
            "cofR": [float(v) for v in t],  # moments about the bow on the waterline (the placed boat origin)
            "turbModel": p["turbulence"],
            "kInf": turb.k,
            "omegaInf": turb.omega,
            "nutInf": turb.nut,
            "maxIter": int(p["max_iter"]),
            "convWindow": int(p["conv_window"]),
            "nLayers": int(p["n_layers"]),
        }

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        hull = hull_surface(p)
        _, air = waterline.split(hull, float(p["heel"]), float(p.get("trim") or 0.0), float(p.get("sink") or 0.0))
        tri = case_dir / "constant" / "triSurface"
        air.write(tri / "hull.stl")
        T = topsides(p)
        pts = T.reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)  # the topsides, above the water
        L = float(d["lRef"])
        lv = MESH_LEVELS[p["mesh"]]
        h = L / 10
        w = np.array(d["dragDir"])
        n = np.array([-w[1], w[0], 0.0])  # e2 = e3 x e1: across the wind
        # the domain: 2 L upwind of the topsides, 4 L downwind, 2 L to each side,
        # 1.5 L high; the box round that, on whole background cells from the origin
        along, across = pts @ w, pts @ n
        a0, a1 = along.min() - 2 * L, along.max() + 4 * L
        b0, b1 = across.min() - 2 * L, across.max() + 2 * L
        corners = np.array([a * w + b * n for a in (a0, a1) for b in (b0, b1)])
        dom_lo = np.floor(np.r_[corners[:, :2].min(axis=0), 0.0] / h) * h
        dom_hi = np.ceil(np.r_[corners[:, :2].max(axis=0), 1.5 * L] / h) * h
        cells = np.maximum(np.round((dom_hi - dom_lo) / h).astype(int), 1)
        m = 0.08 * L
        top = float(hi[2])
        wake = 1.5 * L
        origin = (along.min() - m) * w + (across.min() - m) * n + np.array([0.0, 0.0, -m])
        loc = dom_lo + np.array([0.0371, 0.0412, 0.6137]) * (dom_hi - dom_lo)  # a corner, well above the hull
        vec = lambda a: [float(x) for x in a]
        d.update({
            "xMin": float(dom_lo[0]), "yMin": float(dom_lo[1]), "zMin": 0.0,
            "xMax": float(dom_hi[0]), "yMax": float(dom_hi[1]), "zMax": float(dom_hi[2]),
            "nx": int(cells[0]), "ny": int(cells[1]), "nz": int(cells[2]),
            "baseCell": h,
            "surfaceLevelMin": lv["surf"][0], "surfaceLevelMax": lv["surf"][1],
            "featureLevel": lv["feat"],
            "nearBoxMin": vec([lo[0] - m, lo[1] - m, -m]), "nearBoxMax": vec([hi[0] + m, hi[1] + m, top + m]),
            "nearBoxLevel": lv["near"],
            "wakeOrigin": vec(origin), "wakeE1": vec(w),
            "wakeSpan": vec([float(np.ptp(along)) + m + wake, float(np.ptp(across)) + 2 * m, 2 * top + m]),
            "wakeBoxLevel": lv["wake"],
            "locationInMesh": vec(loc),
            "topsidesMin": vec(lo), "topsidesMax": vec(hi),
            "topsides_area_m2": float(0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum()),
        })
        cofr = "({:.9g} {:.9g} {:.9g})".format(*d["cofR"])
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        (inc / "forceFunctions").write_text("// generated by iomcfd\n\n"
                                            + forces_function("forces_total", ["hull"], cofr=cofr, interval=1))
        self.write_parameters(case_dir, d, inputs=p)

    # ------------------------------------------------------------------
    @staticmethod
    def _force_history(case_dir: Path, d: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        """Drag and lift [N] at every iteration so far."""
        ff = find_dat(case_dir, "forces_total", "force.dat")
        if not ff:
            return None
        _, f = read_dat(ff[-1])
        if f.size == 0:
            return None
        return f[:, 1:4] @ np.array(d["dragDir"]), f[:, 1:4] @ np.array(d["liftDir"])

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """Windowed means of drag and lift stopped moving, and neither drifts
        within the last window (on the scale of the larger of the two)."""
        h = self._force_history(case_dir, d)
        if h is None:
            return False
        drag, lift = h
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        scale = max(abs(drag[-1]), abs(lift[-1]))
        return settled(drag, w, tol, scale, drift=True) and settled(lift, w, tol, scale, drift=True)

    def progress(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Latest drag and lift [N], how far their windowed means still move and
        how much they drift within the last window (relative to the larger),
        against conv_tol."""
        h = self._force_history(case_dir, d)
        if h is None:
            return {}
        drag, lift = h
        out: dict[str, Any] = {"D": float(drag[-1]), "L": float(lift[-1])}
        w = int(d["convWindow"])
        scale = max(abs(drag[-1]), abs(lift[-1]))
        for key, series in (("D", drag), ("L", lift)):
            st = window_stats(series, w)
            if st is not None and scale:
                out[f"{key}_change"] = st[1] / scale
                out[f"{key}_drift"] = window_drift(series, w) / scale
        out["conv_tol"] = float(p["conv_tol"])
        return out

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        tot = read_forces(case_dir, "forces_total", int(d["convWindow"]))
        if tot is None:
            return {"_status": "failed"}
        F, M = tot.total, tot.moment
        dd, ld = np.array(d["dragDir"]), np.array(d["liftDir"])
        out: dict[str, Any] = {
            "drag_N": float(F @ dd),  # along the apparent wind
            "lift_N": float(F @ ld),  # across it, horizontal, along liftDir (+ aft)
            "vertical_N": float(F[2]),
            "Fx_N": float(F[0]), "Fy_N": float(F[1]),
            "drag_friction_N": float(tot.viscous @ dd),
            "drag_pressure_N": float(tot.pressure @ dd),
            # about the bow on the waterline, right-handed about x aft, y port, z up
            "roll_moment_Nm": float(M[0]), "pitch_moment_Nm": float(M[1]), "yaw_moment_Nm": float(M[2]),
        }
        fy = float(F[1])
        out["x_ce"] = float(M[2] / fy) if abs(fy) > 1e-9 else None  # where the side force acts, from the bow
        out["z_ce"] = float(-M[0] / fy) if abs(fy) > 1e-9 else None  # and its height
        out["A_proj_m2"] = float(d["Aref"])  # normal to the wind
        out["z_centroid_m"] = float(d["centroid"][2])  # its centroid's height: where the VPP takes the wind
        qA = d["dynamicPressure"] * d["Aref"]
        out["cd"] = out["drag_N"] / qA if qA > 0 else None
        out["cl"] = out["lift_N"] / qA if qA > 0 else None
        qB = d["dynamicPressure"] * d["A_beam_m2"]
        out["cx"], out["cy"] = out["Fx_N"] / qB, out["Fy_N"] / qB  # on the beam-on area, boat axes
        ff = find_dat(case_dir, "forces_total", "force.dat")
        n_iter = int(read_dat(ff[-1])[1][-1, 0]) if ff else 0
        out["iterations"] = n_iter
        out["converged"] = n_iter < int(d["maxIter"]) or self.converged(case_dir, p, d)
        yp = sorted((case_dir / "postProcessing" / "yPlus").glob("*/yPlus.dat"))
        if yp:
            rows = [ln.split() for ln in yp[-1].read_text().splitlines() if ln and not ln.startswith("#")]
            vals = [list(map(float, r[2:5])) for r in rows if len(r) >= 5 and r[1] == "hull"]
            if vals:
                out["yplus_max"] = max(v[1] for v in vals)
                out["yplus_mean"] = float(np.mean([v[2] for v in vals]))
        log = case_dir / "log.checkMesh"
        if log.is_file():
            for ln in log.read_text(errors="ignore").splitlines():
                if ln.strip().startswith("cells:"):
                    out["n_cells"] = int(ln.split()[1])
                    break
        if not out["converged"]:
            rel = float(tot.std @ np.abs(dd)) / max(abs(out["drag_N"]), 1e-12)
            out["_status"] = "ok" if rel < 0.01 else "not_converged"
        return out

    def mesh_views(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]):
        from iomcfd.meshplot import MeshSpec, MeshView

        lo, hi = np.array(d["topsidesMin"]), np.array(d["topsidesMax"])
        xm, ym = 0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1])
        zs = 0.5 * hi[2] + 0.00137
        L = float(d["lRef"])
        return MeshSpec(
            [
                MeshView(f"horizontal section {zs * 1e3:.0f} mm above the water", (0.0, 0.0, zs), (0, 0, 1), (0, 1),
                         (xm, ym), 1.4 * L),
                MeshView("section at mid-length: the topsides, prism layers", (xm + 0.00137, 0.0, 0.0), (1, 0, 0), (1, 2),
                         (ym, 0.6 * hi[2]), 3.0 * float(np.ptp([lo[1], hi[1]])), ("y [m]", "z [m]")),
                MeshView("whole domain, plane z = 0.5 x the topsides' height", (0.0, 0.0, zs), (0, 0, 1), (0, 1),
                         ((d["xMin"] + d["xMax"]) / 2, (d["yMin"] + d["yMax"]) / 2), 1.02 * (d["xMax"] - d["xMin"]),
                         lw=0.15),
            ],
            walls="hull",
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        # millions of cells: measured at 3 m/s (alt-air-scout), xfine an estimate
        cells = {"xcoarse": 0.05, "coarse": 0.15, "medium": 0.3, "fine": 0.6, "xfine": 2.5}[p.get("mesh", "medium")]
        return {"cpus": int(p.get("np", 8)), "memory_gb": max(4, int(3 * cells)), "max_hours": 1 + 2 * cells}

    def report(self, df, out_dir: Path, reference=None, options=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])]
        if df.empty or "awa" not in df:
            return []
        fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
        for (heel, mesh, aws), g in df.groupby(["heel", "mesh", "aws"]):
            g = g.sort_values("awa")
            lab = f"heel {heel:g}, {mesh}, {aws:g} m/s"
            axs[0].plot(g["awa"], g["cd"], "o-", label=lab)
            axs[1].plot(g["awa"], g["cl"], "o-", label=lab)
            axs[2].plot(g["awa"], g["A_proj_m2"], "o-", label=lab)
        axs[0].axhline(0.816, color="0.5", ls="--", lw=1, label="ORC C_D 0.816")
        for ax, yl in zip(axs, ["cd (on the projected area)", "cl (on the projected area)", "projected area [m²]"]):
            ax.set_xlabel("apparent wind angle from the centreline [deg]")
            ax.set_ylabel(yl)
            ax.grid(alpha=0.3)
        axs[0].legend(fontsize=7)
        fig.tight_layout()
        f = out_dir / "windage_coefficients.png"
        fig.savefig(f, dpi=130)
        plt.close(fig)
        return [f]
