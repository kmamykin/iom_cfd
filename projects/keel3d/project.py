"""keel3d: canoe body + keel fin + lead bulb, steady double-body RANS
(simpleFoam + kOmegaSST).

Built to compare keel planforms (constant chord against tapered) at equal
lateral area. The keel is sized from the IOM class rules: the bulb holds
the lead that the keel mass limit leaves after the fin, its bottom is at
the draft limit, and the fin spans from the hull bottom to the top of the
bulb. The waterline is a symmetry plane, so the hull is in the flow but
makes no waves.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import physics
from iomcfd.foam import find_dat, read_dat
from iomcfd.forces import forces_function, read_forces, settled, window_stats
from iomcfd.geometry import appendages as ap
from iomcfd.geometry import foils, hulls, stl
from iomcfd.geometry.keel import BULB_ZONE, MAX_FIN_THICKNESS, bulb_spec, hull_spec, keel_geometry  # noqa: F401
from iomcfd.project import Project

# Background cell = fin mean chord (100 mm). Refinement level n halves it n
# times: level 6 = 1.6 mm, level 7 = 0.8 mm. fin/bulb/hull: surface levels
# (min, max; max where the surface curves, e.g. the leading edge); feat:
# feature edges (trailing edge, fin-hull and fin-bulb junctions); keel/hullbox/
# wake: refinement boxes; dist: band around fin and bulb. The fin's near-wake
# box (`fin_wake`) is at the fin's minimum surface level. xfine refines the
# fin, bulb, near wake and boxes once more than fine, not the hull.
MESH_LEVELS = {
    "xcoarse": dict(fin=(4, 5), bulb=(4, 5), hull=(3, 4), feat=5, keel=2, hullbox=1, wake=1, dist=4),
    "coarse": dict(fin=(5, 6), bulb=(5, 6), hull=(3, 4), feat=6, keel=3, hullbox=2, wake=2, dist=5),
    "medium": dict(fin=(6, 7), bulb=(5, 6), hull=(4, 5), feat=7, keel=3, hullbox=2, wake=2, dist=6),
    "fine": dict(fin=(7, 8), bulb=(6, 7), hull=(4, 5), feat=8, keel=4, hullbox=3, wake=3, dist=7),
    "xfine": dict(fin=(8, 9), bulb=(7, 8), hull=(4, 5), feat=9, keel=5, hullbox=3, wake=4, dist=8),
}

# Race-time defaults (foil2d/methodology.md): V dR/dV [N] by speed, track angle.
VDRDV = {0.5: 0.40, 0.75: 0.81, 1.0: 1.354, 1.5: 2.71}
TRACK_ANGLE = 42.0
LOAD_NAMES = ("light", "working", "high")

# Bulb shape parameters and their defaults (results of runs made before
# they existed have the defaults).
BULB_SHAPE = {"bulb_section": "naca0007", "bulb_aspect": 1.0, "bulb_top": 2.0, "bulb_bottom": 2.0, "bulb_cant": 0.0}

# Parameters that make a keel design (compared at equal side force) and the
# conditions it is compared under.
DESIGN = ["fin_taper", "fin_sweep", "fin_mean_chord", "fin_section", "fin_x", "bulb", "bulb_section", "bulb_x",
          "bulb_aspect", "bulb_top", "bulb_bottom", "bulb_cant"]
CONDITION = ["speed", "heel", "mesh", "mesh_shift", "fin_wake", "turbulence", "Tu"]


def read_spanload(case_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Force per spanwise strip from the binField function object `spanload`:
    (times (n_t,), forces (n_t, n_bins, 3) N)."""
    files = sorted((Path(case_dir) / "postProcessing" / "spanload").glob("*/*.dat"))
    if not files:
        return None
    rows = [[float(v) for v in ln.replace("(", " ").replace(")", " ").split()]
            for ln in files[-1].read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    if not rows:
        return None
    a = np.array(rows)
    # per bin: total (3), internal (3), patch (3) -> the total
    return a[:, 0], a[:, 1:].reshape(len(a), -1, 9)[:, :, :3]


class Keel3D(Project):
    name = "keel3d"
    summary_keys = ["drag_N", "side_N", "side_drag_ratio", "z_clr"]
    highlight_columns = ["drag_N", "side_N", "drag_hull_N", "drag_fin_N", "drag_bulb_N", "side_fin_N", "z_clr", "eta_cp"]

    def derive(self, p: dict[str, Any]) -> dict[str, Any]:
        fl = physics.fluid(p["fluid"], p["temperature"])
        b = math.radians(float(p["leeway"]))
        drag_dir = [math.cos(b), math.sin(b), 0.0]
        side_dir = [-math.sin(b), math.cos(b), 0.0]
        V = float(p["speed"])
        turb = physics.turbulence_inflow(V, fl.nu, float(p["Tu"]), float(p["viscosity_ratio"]))
        g = keel_geometry(p)
        c = float(p["fin_mean_chord"])
        h = math.radians(float(p["heel"]))
        displaced = g["hull_volume_m3"] + g["fin_volume_m3"] + g["bulb_volume_m3"]
        # Spanwise strips: each a whole number of fin surface cells (background
        # cell / 2^level, rows of faces along z), so every strip holds the same
        # number of face rows; they start at the hull and stop short of the bulb
        # by less than one strip.
        cell = c / 2 ** MESH_LEVELS[p["mesh"]]["fin"][0]
        k = max(1, int(g["fin_span"] / (int(p["span_bins"]) * cell)))
        n_bins = int(g["fin_span"] / (k * cell))
        rot = stl.rotation("x", float(p["heel"]))
        return {
            "rhoInf": fl.rho,
            "nu": fl.nu,
            "magUInf": V,
            "Uinf": [V * d for d in drag_dir],
            "dragDir": drag_dir,
            "sideDir": side_dir,
            "lRef": c,
            "Aref": g["fin_area_m2"],  # fin lateral area (exposed)
            "dynamicPressure": 0.5 * fl.rho * V**2,
            "Re_fin": V * c / fl.nu,
            "Re_root": V * g["fin_root_chord"] / fl.nu,
            "Re_tip": V * g["fin_tip_chord"] / fl.nu,
            "Re_hull": V * float(p["hull_length"]) / fl.nu,
            **g,
            "displacement_kg": displaced * fl.rho,
            # the bulb's centre of mass and pitch axis (boat y), heeled: its pitching moment
            "bulbCofG": [float(v) for v in rot @ np.array([g["bulb_x_cg"], 0.0, g["bulb_z_cg"]])],
            "bulbPitchAxis": [float(v) for v in rot @ np.array([0.0, 1.0, 0.0])],
            # spanwise strips along the (heeled) fin: distance from the waterline
            "spanDir": [0.0, math.sin(h), -math.cos(h)],
            "spanMin": -g["fin_z_root"],
            "spanMax": -g["fin_z_root"] + n_bins * k * cell,
            "spanBins": n_bins,
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
        """Hull, fin and bulb in the world frame (heeled about the x axis at the waterline)."""
        g = keel_geometry(p)
        hull = hulls.canoe(hull_spec(p), "hull")
        root = g["fin_root_chord"]
        fin = ap.fin(ap.FinSpec(
            section=p["fin_section"], root_chord=root, tip_chord=g["fin_tip_chord"], span=g["fin_span"],
            sweep=float(p["fin_sweep"]), x_root_le=float(p["fin_x"]) - 0.25 * root, z_root=g["fin_z_root"],
            root_extension=0.5 * float(p["hull_draft"]), tip_extension=g["fin_tip_extension"], n_span=40,
        ), "fin")
        out = [hull, fin]
        if p["bulb"]:  # else the fin alone, with a flat tip where the bulb's top would be
            out.append(ap.foil_bulb(bulb_spec(p, g["bulb_length"], g["bulb_x_cg"], g["bulb_z_axis"]), "bulb"))
        if float(p["heel"]):
            out = [s.rotated("x", float(p["heel"])) for s in out]
        return out

    def render(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        surfs = self.surfaces(p)
        tri = case_dir / "constant" / "triSurface"
        stl.write_multi(tri / "boat.stl", surfs)  # solids -> patches boat_hull, boat_fin, boat_bulb
        stl.write_multi(tri / "keel.stl", surfs[1:])  # fin + bulb, for the distance refinement only
        self._write_trailing_edge(tri / "trailingEdge.obj", p)

        lo = np.min([s.bounds[0] for s in surfs], axis=0)
        hi = np.max([s.bounds[1] for s in surfs], axis=0)
        klo = np.min([s.bounds[0] for s in surfs[1:]], axis=0)
        khi = np.max([s.bounds[1] for s in surfs[1:]], axis=0)
        L = float(p["hull_length"])
        lv = MESH_LEVELS[p["mesh"]]
        h = float(d["lRef"])  # background cell = fin mean chord
        tb = abs(math.tan(math.radians(float(p["leeway"]))))
        # The domain ends on whole background cells from the origin (bow, centre
        # plane, waterline), so every refined cell sits the same way relative to
        # the boat whatever the leeway or taper. mesh_shift moves that grid in x
        # and y by a fraction of the finest fin cell.
        shift = float(p["mesh_shift"]) * h / 2 ** lv["feat"]
        dom_lo = np.floor(np.array([-1.5 * L, -1.5 * L - 4 * L * tb, klo[2] - 1.2 * L]) / h) * h
        dom_hi = np.ceil(np.array([4.0 * L, 1.5 * L + 4 * L * tb, 0.0]) / h) * h
        n = np.maximum(np.round((dom_hi - dom_lo) / h).astype(int), 1)
        dom_lo[:2] += shift
        dom_hi[:2] += shift
        top = np.array([np.inf, np.inf, h])
        m = 0.4 * h
        wake_x = L + 1.0  # wake box ends 1 m behind the stern
        wake_y = (wake_x - klo[0]) * tb
        boxes = {
            "keelBox": (klo - m, np.minimum(khi + m, top)),
            "hullBox": (np.array([lo[0] - m, lo[1] - m, -float(p["hull_draft"]) - m]), np.array([hi[0] + m, hi[1] + m, h])),
            "wakeBox": (np.array([klo[0] - m, klo[1] - m - wake_y, klo[2] - m]), np.array([wake_x, khi[1] + m + wake_y, h])),
        }
        loc = dom_lo + np.array([0.0371, 0.4123, 0.5137]) * (dom_hi - dom_lo)

        vec = lambda a: [float(x) for x in a]
        d.update({
            "xMin": float(dom_lo[0]), "yMin": float(dom_lo[1]), "zMin": float(dom_lo[2]),
            "xMax": float(dom_hi[0]), "yMax": float(dom_hi[1]), "zMax": float(dom_hi[2]),
            "nx": int(n[0]), "ny": int(n[1]), "nz": int(n[2]),
            "baseCell": h,
            "finLevelMin": lv["fin"][0], "finLevelMax": lv["fin"][1],
            "bulbLevelMin": lv["bulb"][0], "bulbLevelMax": lv["bulb"][1],
            "hullLevelMin": lv["hull"][0], "hullLevelMax": lv["hull"][1],
            "featureLevel": lv["feat"],
            "keelBoxLevel": lv["keel"], "hullBoxLevel": lv["hullbox"], "wakeBoxLevel": lv["wake"],
            "keelDistance": 6 * h / 2 ** lv["dist"], "keelDistanceLevel": lv["dist"],
            "locationInMesh": vec(loc),
            "components": [s.name for s in surfs],
            "bulb_wetted_area_m2": surfs[2].area() if len(surfs) > 2 else 0.0,
            "wetted_area_m2": d["hull_wetted_area_m2"] + d["fin_wetted_area_m2"] + sum(s.area() for s in surfs[2:]),
            "bodyBoxBoat": self._boat_box(p),
        })
        for name, (a, b) in boxes.items():
            d[f"{name}Min"], d[f"{name}Max"] = vec(a), vec(b)
        d.update(self._fin_wake_box(p, d, lv))

        fo = [forces_function(f"forces_{s.name}", [f"boat_{s.name}"]) for s in surfs]
        fo.append(forces_function("forces_keel", [f"boat_{s.name}" for s in surfs[1:]]))
        fo.append(forces_function("forces_total", ["boat"], interval=1))
        inc = case_dir / "system" / "include"
        inc.mkdir(parents=True, exist_ok=True)
        (inc / "forceFunctions").write_text("// generated by iomcfd: one forces function object per component\n\n" + "\n".join(fo))
        self.write_parameters(case_dir, d, inputs=p)

    @staticmethod
    def _fin_wake_box(p: dict[str, Any], d: dict[str, Any], lv: dict[str, Any]) -> dict[str, Any]:
        """Rotated box along the fin's trailing edge: from 0.1 mean chord ahead
        of it to `fin_wake` mean chords behind it, ±0.06 mean chord to each side
        (wider by the leeway drift, on both sides so that an upright mesh stays
        a mirror image), over the exposed span, at the
        fin's minimum surface level. Level 0 (no refinement) if fin_wake is 0."""
        c = float(p["fin_mean_chord"])
        length = float(p["fin_wake"]) * c
        sweep = math.tan(math.radians(float(p["fin_sweep"])))
        z_r, z_t = d["fin_z_root"], d["fin_z_root"] - d["fin_span"]
        te_r = np.array([float(p["fin_x"]) + 0.75 * d["fin_root_chord"], 0.0, z_r])
        te_t = np.array([float(p["fin_x"]) + sweep * d["fin_span"] + 0.75 * d["fin_tip_chord"], 0.0, z_t])
        e3 = (te_r - te_t) / np.linalg.norm(te_r - te_t)  # up the trailing edge
        e1 = np.array([1.0, 0.0, 0.0]) - e3[0] * e3  # downstream, normal to the edge
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(e3, e1)  # = +y upright
        ahead, half, margin = 0.1 * c, 0.06 * c, 0.1 * c
        drift = abs(length * math.tan(math.radians(float(p["leeway"]))))
        lo2, hi2 = -half - drift, half + drift
        corner = te_t - ahead * e1 + lo2 * e2 - margin * e3
        span = [ahead + length, hi2 - lo2, float(np.linalg.norm(te_r - te_t)) + 2 * margin]
        rot = stl.rotation("x", float(p["heel"]))
        vec = lambda a: [float(x) for x in a]
        return {
            "finWakeOrigin": vec(rot @ corner), "finWakeSpan": vec(span),
            "finWakeE1": vec(rot @ e1), "finWakeE3": vec(rot @ e3),
            "finWakeLevel": lv["fin"][0] if length > 0 else 0,
        }

    @staticmethod
    def _write_trailing_edge(path: Path, p: dict[str, Any], eps: float = 1e-6) -> None:
        """The fin's trailing edge as two feature lines 1 um either side of the
        centre plane (OBJ edge mesh for snappyHexMesh `features`).

        The grid is aligned with the boat, so y = 0 is a plane of cell faces
        and the trailing edge lies on it: which cell a point of the edge falls
        in is a tie, and the feature refinement would pick one side in patches
        (about 1 % of the fin faces not mirrored). Refining along both copies
        refines both rows of cells the same."""
        g = keel_geometry(p)
        z_r, span = g["fin_z_root"], g["fin_span"]
        sweep = math.tan(math.radians(float(p["fin_sweep"])))
        # the fin's own extent: into the hull above the root, into the bulb below the tip
        zs = [z_r + 0.5 * float(p["hull_draft"]), z_r, z_r - span]
        if g["fin_tip_extension"] > 0:
            zs.append(z_r - span - g["fin_tip_extension"])

        def x_te(z: float) -> float:
            frac = min(max((z_r - z) / span, 0.0), 1.0)
            chord = g["fin_root_chord"] + (g["fin_tip_chord"] - g["fin_root_chord"]) * frac
            return float(p["fin_x"]) + sweep * (z_r - z) + 0.75 * chord

        rot = stl.rotation("x", float(p["heel"]))
        verts, lines = [], []
        for y in (eps, -eps):
            first = len(verts) + 1  # OBJ numbers from 1
            verts += [rot @ np.array([x_te(z), y, z]) for z in zs]
            lines += [(first + k, first + k + 1) for k in range(len(zs) - 1)]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fin trailing edge, 1 um either side of the centre plane (iomcfd keel3d)\n"
                        + "".join(f"v {x:.9g} {y:.9g} {z:.9g}\n" for x, y, z in verts)
                        + "".join(f"l {a} {b}\n" for a, b in lines))

    def _boat_box(self, p: dict[str, Any]) -> list[float]:
        """Bounding box of the underwater boat, upright: [xmin, ymin, zmin, xmax, ymax, zmax]."""
        up = self.surfaces({**p, "heel": 0.0})
        lo = np.min([s.bounds[0] for s in up], axis=0)
        hi = np.max([s.bounds[1] for s in up], axis=0)
        return [float(v) for v in (*lo, *hi[:2], 0.0)]

    # ------------------------------------------------------------------
    @staticmethod
    def _force_history(case_dir: Path, d: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        """D_h and S_h of the whole boat [N] at every iteration so far
        (forces_total, along and across the course)."""
        ff = find_dat(case_dir, "forces_total", "force.dat")
        if not ff:
            return None
        _, f = read_dat(ff[-1])
        if f.size == 0:
            return None
        return f[:, 1:4] @ np.array(d["dragDir"]), f[:, 1:4] @ np.array(d["sideDir"])

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """Windowed means of D_h and S_h stopped moving."""
        h = self._force_history(case_dir, d)
        if h is None:
            return False
        drag, side = h
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        scale = max(abs(drag[-1]), abs(side[-1]))
        return settled(drag, w, tol, abs(drag[-1])) and settled(side, w, tol, scale)

    def progress(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Latest D_h and S_h of the whole boat [N], and how far their windowed
        means still move (relative, on the scales `converged` uses), against
        conv_tol: the case stops once both changes are below it."""
        h = self._force_history(case_dir, d)
        if h is None:
            return {}
        drag, side = h
        out: dict[str, Any] = {"D_h": float(drag[-1]), "S_h": float(side[-1])}
        w = int(d["convWindow"])
        scales = {"D_h": abs(drag[-1]), "S_h": max(abs(drag[-1]), abs(side[-1]))}
        for key, series in (("D_h", drag), ("S_h", side)):
            st = window_stats(series, w)
            if st is not None and scales[key]:
                out[f"{key}_change"] = st[1] / scales[key]
        out["conv_tol"] = float(p["conv_tol"])
        return out

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
        # centre of lateral resistance, from the moments about the bow at the waterline
        fy = float(tot.total[1])
        out["x_clr"] = float(tot.moment[2] / fy) if abs(fy) > 1e-9 else None
        out["z_clr"] = float(-tot.moment[0] / fy) if abs(fy) > 1e-9 else None
        q, A = d["dynamicPressure"], d["Aref"]
        out["Cd"] = out["drag_N"] / (q * A)
        out["Cs"] = out["side_N"] / (q * A)
        for comp in ("hull", "fin", "bulb", "keel"):
            r = read_forces(case_dir, f"forces_{comp}", win)
            if r is not None:
                out[f"drag_{comp}_N"] = float(r.total @ dd)
                out[f"side_{comp}_N"] = float(r.total @ sd)
                out[f"drag_{comp}_friction_N"] = float(r.viscous @ dd)
                if comp == "bulb":
                    out["drag_bulb_pressure_N"] = float(r.pressure @ dd)
                    out["vertical_bulb_N"] = float(r.total[2])  # + up
                    # about the bulb's centre of mass, + nose up (moments are about the origin)
                    m_cg = r.moment - np.cross(np.array(d["bulbCofG"]), r.total)
                    out["pitch_bulb_Nm"] = float(m_cg @ np.array(d["bulbPitchAxis"]))
        out.update(self._spanload(case_dir, p, d))
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
            for comp in ("hull", "fin", "bulb"):
                vals = [list(map(float, r[2:5])) for r in rows if len(r) >= 5 and r[1] == f"boat_{comp}"]
                if vals:
                    out[f"yplus_{comp}_max"] = max(v[1] for v in vals)
                    out[f"yplus_{comp}_mean"] = float(np.mean([v[2] for v in vals]))
        log = case_dir / "log.checkMesh"
        if log.is_file():
            for ln in log.read_text(errors="ignore").splitlines():
                if ln.strip().startswith("cells:"):
                    out["n_cells"] = int(ln.split()[1])
                    break
        if not out["converged"]:
            rel = tot.std @ np.abs(dd) / max(abs(out["drag_N"]), 1e-9)
            out["_status"] = "ok" if rel < 0.01 else "not_converged"
        return out

    def _spanload(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Write spanload.csv (force per metre of span along the fin, local
        coefficients on the local chord) and return summary values."""
        r = read_spanload(case_dir)
        if r is None or r[1].shape[1] != int(d["spanBins"]):
            return {}
        t, fb = r
        tail = t > t[-1] - int(d["convWindow"])
        f = fb[tail].mean(axis=0)
        n = len(f)
        ds = (d["spanMax"] - d["spanMin"]) / n
        eta = (np.arange(n) + 0.5) * ds / d["fin_span"]  # 0 at the hull, 1 at the top of the bulb
        chord = d["fin_root_chord"] + (d["fin_tip_chord"] - d["fin_root_chord"]) * eta
        q = d["dynamicPressure"]
        sd = np.array(d["sideDir"])
        side = f @ sd / ds
        drag = f @ np.array(d["dragDir"]) / ds
        rows = ["eta,depth_m,chord_m,side_N_per_m,drag_N_per_m,cl,cd"]
        for i in range(n):
            rows.append(f"{eta[i]:.4f},{d['spanMin'] + (i + 0.5) * ds:.5f},{chord[i]:.5f},{side[i]:.6g},{drag[i]:.6g},"
                        f"{side[i] / (q * chord[i]):.6g},{drag[i] / (q * chord[i]):.6g}")
        (Path(case_dir) / "spanload.csv").write_text("\n".join(rows) + "\n")
        total = float(side.sum() * ds)
        if abs(total) < 1e-9:
            return {}
        cl = side / (q * chord)
        out = {"eta_cp": float((eta * side).sum() * ds / total),  # spanwise centre of the strips' side force
               "cl_root": float(cl[0]), "cl_mid": float(cl[n // 2]), "cl_tip": float(cl[-1])}
        # strips / whole fin, at the last iteration both wrote (the strips miss
        # the faces just outside them: at the hull, and up to one strip at the bulb)
        ff = find_dat(case_dir, "forces_fin", "force.dat")
        if ff:
            _, fin = read_dat(ff[-1])
            row = fin[np.isclose(fin[:, 0], t[-1])] if fin.size else fin
            if len(row) and abs(row[0, 1:4] @ sd) > 1e-9:
                out["spanload_coverage"] = float(fb[-1].sum(axis=0) @ sd / (row[0, 1:4] @ sd))
        return out

    # ------------------------------------------------------------------
    def mesh_views(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]):
        from iomcfd.meshplot import MeshSpec, MeshView, boat_view

        bb = d["bodyBoxBoat"]
        h = float(d["baseCell"])
        eps = 0.0137 * h  # keep cut planes off background-mesh planes
        zm = d["fin_z_root"] - 0.5 * d["fin_span"]
        xf = float(p["fin_x"]) + 0.25 * float(p["fin_mean_chord"])
        chord = float(p["fin_mean_chord"])
        # mid-span trailing edge (linear taper: the chord there is the mean chord)
        xte = float(p["fin_x"]) + math.tan(math.radians(float(p["fin_sweep"]))) * 0.5 * d["fin_span"] + 0.75 * chord
        kw = dict(heel=float(p["heel"]))
        return MeshSpec(
            [
                boat_view("side, centre plane: hull, fin, bulb", "side", eps, ((bb[0] + bb[3]) / 2, bb[2] / 2),
                          1.1 * (bb[3] - bb[0]), **kw),
                MeshView("whole domain, plane y = 0", (0.0, eps, 0.0), (0.0, 1.0, 0.0), (0, 2),
                         ((d["xMin"] + d["xMax"]) / 2, (d["zMin"] + d["zMax"]) / 2), 1.02 * (d["xMax"] - d["xMin"]),
                         ("x [m]", "z [m]"), lw=0.15),
                boat_view(f"fin section at mid-span ({abs(zm):.2f} m below the waterline)", "section", zm + eps,
                          (xf, 0.0), 2.2 * chord, **kw),
                boat_view("fin trailing edge: prism layers", "section", zm + eps, (xf + 0.55 * chord, 0.0), 0.35 * chord, **kw),
                boat_view("near wake at mid-span: trailing edge and fin-wake box", "section", zm + eps,
                          (xte + 0.15 * chord, 0.0), 0.7 * chord, **kw),
                boat_view("side, centre plane: trailing edge and near wake along the span", "side", eps,
                          (xte + 0.1 * chord, zm), 1.15 * float(d["fin_span"]) * 8 / 5, **kw),
            ],
            walls="boat(_.*)?",
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        # millions of cells with 5 layers, the near-wake box and the aligned grid
        # (4 deg; coarse measured before those, xfine an estimate)
        cells = {"xcoarse": 0.16, "coarse": 0.5, "medium": 1.07, "fine": 3.3, "xfine": 14}[p.get("mesh", "medium")]
        # time limit: 3000 iterations at a speed not yet measured on GCP, so generous
        return {"cpus": int(p.get("np", 8)), "memory_gb": max(4, int(3 * cells)), "max_hours": 2 + 2.5 * cells}

    # ------------------------------------------------------------------
    @staticmethod
    def compare_at_equal_force(df, options: dict | None = None):
        """Drag and leeway of every keel design at the side forces a reference
        design makes at a few leeway angles, and the race time each loses
        against the best (foil2d/methodology.md, with 3D leeway and drag).

        options: compare_at {<design param>: value, leeway: [..]} (default
        fin_taper 1.0 at 2, 4, 6 deg), vdrdv {speed: V dR/dV [N]},
        track_angle [deg]. Returns a DataFrame, one row per design and load.

        Downwind the boat sails upright, so when the study has an upright
        case at 0 deg of the same design (and speed, mesh, ...), heeled rows
        take their downwind drag from it.
        """
        import pandas as pd
        from scipy.interpolate import PchipInterpolator

        opts = options or {}
        ref = dict(opts.get("compare_at") or {"fin_taper": 1.0, "leeway": [2, 4, 6]})
        ref_leeway = [float(a) for a in ref.pop("leeway", [2, 4, 6])]
        vdrdv = {float(k): float(v) for k, v in (opts.get("vdrdv") or VDRDV).items()}
        tan_t = math.tan(math.radians(float(opts.get("track_angle", TRACK_ANGLE))))
        df = df[df["status"].isin(["ok", "not_converged"])]
        design = [c for c in DESIGN if c in df and df[c].nunique() > 1] or ["fin_taper"]
        cond = [c for c in CONDITION if c in df and df[c].nunique() > 1]
        other = [c for c in cond if c != "heel"]
        upright = {}
        if "heel" in df:
            for _, r in df[(df["heel"] == 0) & (df["leeway"] == 0)].iterrows():
                upright[(tuple(r[c] for c in other), tuple(r[c] for c in design))] = float(r["drag_N"])
        rows = []
        for ckey, cg in (df.groupby(cond) if cond else [((), df)]):
            ckey = ckey if isinstance(ckey, tuple) else (ckey,)
            okey = tuple(dict(zip(cond, ckey))[c] for c in other)
            curves = {}
            for dkey, g in cg.groupby(design):
                g = g.sort_values("leeway")
                b, F, D = g["leeway"].to_numpy(float), g["side_N"].to_numpy(float), g["drag_N"].to_numpy(float)
                keep = np.concatenate([[True], np.diff(F) > 0])  # rising branch only
                keep &= np.cumprod(keep).astype(bool)
                d0 = float(np.interp(0.0, b, D)) if b.min() <= 0 <= b.max() else float("nan")
                d0 = upright.get((okey, dkey if isinstance(dkey, tuple) else (dkey,)), d0)
                if keep.sum() >= 2:  # a sweep, not a single point (e.g. a mesh check)
                    cg_h = float(g["bulb_cg_above_draft"].iloc[0]) if "bulb_cg_above_draft" in g else float("nan")
                    curves[dkey if isinstance(dkey, tuple) else (dkey,)] = (b[keep], F[keep], D[keep], d0, cg_h)
            refkey = [k for k in curves if all(_same(dict(zip(design, k))[n], v) for n, v in ref.items() if n in design)]
            if not refkey:
                continue
            rb, rF, *_ = curves[refkey[0]]
            loads = [float(np.interp(a, rb, rF)) if rb.min() <= a <= rb.max() else float("nan") for a in ref_leeway]
            V = float(dict(zip(cond, ckey)).get("speed", df["speed"].iloc[0]))
            for li, (a, F0) in enumerate(zip(ref_leeway, loads)):
                if np.isnan(F0):
                    continue
                for dkey, (b, F, D, d0, cg_h) in curves.items():
                    ok = len(F) >= 2 and F[0] <= F0 <= F[-1]
                    # drag is close to linear in F^2 (D0 + k F^2), leeway in F
                    f2 = lambda f: f * np.abs(f)
                    interp = (lambda x, y, x0: float(PchipInterpolator(x, y)(x0))) if len(F) >= 3 else \
                        (lambda x, y, x0: float(np.interp(x0, x, y)))
                    beta = interp(F, b, F0) if ok else float("nan")
                    drag = interp(f2(F), D, f2(F0)) if ok else float("nan")
                    rows.append({**dict(zip(cond, ckey)), **dict(zip(design, dkey)),
                                 "load": LOAD_NAMES[li] if li < len(LOAD_NAMES) else f"load{li}",
                                 "ref_leeway": a, "side_N": F0, "leeway": beta, "drag_N": drag, "drag0_N": d0,
                                 "vdrdv": vdrdv.get(V, float("nan")), "bulb_cg_above_draft": cg_h})
        t = pd.DataFrame(rows)
        if t.empty:
            return t
        grp = [*cond, "load"]
        best = t.groupby(grp)[["drag_N", "leeway", "drag0_N"]].transform("min")
        t["d_drag_N"] = t["drag_N"] - best["drag_N"]
        t["d_leeway"] = t["leeway"] - best["leeway"]
        t["d_drag0_N"] = t["drag0_N"] - best["drag0_N"]
        for k in (1, 2):
            loss = 50.0 * ((t["d_drag_N"] + t["d_drag0_N"]) / (k * t["vdrdv"]) + tan_t * np.radians(t["d_leeway"]))
            t[f"loss_x{k}_pct"] = loss - loss.groupby([t[c] for c in grp]).transform("min")
        return t

    @staticmethod
    def polar_fits(df, max_leeway: float | None = None):
        """Per design and condition: D_h at zero S_h and the factor k of
        D_h = D0 + k S_h^2 (least squares); the effective draft
        T_eff = 1 / sqrt(pi q k) (ORC: D_i = S_h^2 / (pi q T_eff^2)) and the
        same as a span efficiency e = 1 / (2 pi q d^2 k) on the draft d (hull
        and keel as a half wing on the waterline mirror); S_h per degree of
        leeway beta_Y (fit up to 4 deg). Fit only the points up to the highest
        attached leeway (`max_leeway` in the study's report options): k also
        holds the growth of viscous drag with S_h, which separation makes
        steep."""
        import pandas as pd

        df = df[df["status"].isin(["ok", "not_converged"])]
        design = [c for c in DESIGN if c in df and df[c].nunique() > 1] or ["fin_taper"]
        cond = [c for c in CONDITION if c in df and df[c].nunique() > 1]
        if max_leeway is not None:
            df = df[df["leeway"] <= float(max_leeway) + 1e-9]
        rows = []
        for key, g in df.groupby([*cond, *design]):
            key = key if isinstance(key, tuple) else (key,)
            F, D, b = g["side_N"].to_numpy(float), g["drag_N"].to_numpy(float), g["leeway"].to_numpy(float)
            if len(g) < 3:
                continue
            A = np.column_stack([np.ones_like(F), F**2])
            (d0, k), *_ = np.linalg.lstsq(A, D, rcond=None)
            q, depth = float(g["dynamicPressure"].iloc[0]), float(g["draft"].iloc[0])
            lin = b <= 4.0 + 1e-9
            slope = float(np.polyfit(b[lin], F[lin], 1)[0]) if lin.sum() >= 2 else float("nan")
            rows.append({**dict(zip([*cond, *design], key)), "D0_N": d0, "k_per_N": k,
                         "e_eff": 1.0 / (2 * math.pi * q * depth**2 * k) if k > 0 else float("nan"),
                         # ORC's form D_i = S_h^2 / (pi q T_eff^2) (VPP documentation eq. 6.37)
                         "T_eff_m": 1.0 / math.sqrt(math.pi * q * k) if k > 0 else float("nan"),
                         "side_per_deg_N": slope, "n_points": len(g)})
        return pd.DataFrame(rows)

    def report(self, df, out_dir: Path, reference=None, options=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = df[df["status"].isin(["ok", "not_converged"])]
        if df.empty:
            return []
        out_dir = Path(out_dir)
        files: list[Path] = []
        design = [c for c in DESIGN if c in df and df[c].nunique() > 1] or ["fin_taper"]
        cond = [c for c in CONDITION if c in df and df[c].nunique() > 1]
        label = lambda k: ", ".join(f"{n} {v}" for n, v in zip([*cond, *design], k if isinstance(k, tuple) else (k,)))

        fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
        for key, g in df.groupby([*cond, *design]):
            g = g.sort_values("leeway")
            axs[0].plot(g["leeway"], g["side_N"], "o-", label=label(key))
            axs[1].plot(g["leeway"], g["drag_N"], "o-", label=label(key))
            axs[2].plot(g["side_N"], g["drag_N"], "o-", label=label(key))
        for ax, (xl, yl) in zip(axs, [("leeway β_Y [deg]", "side force S_h [N]"), ("leeway β_Y [deg]", "drag D_h [N]"),
                                      ("side force S_h [N]", "drag D_h [N]")]):
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.grid(alpha=0.3)
        axs[0].legend(fontsize=7)
        fig.suptitle("hull + fin + bulb (double body)")
        fig.tight_layout()
        files.append(out_dir / "keel_forces.png")
        fig.savefig(files[-1], dpi=130)
        plt.close(fig)

        if df["leeway"].nunique() >= 3:
            fits = self.polar_fits(df, (options or {}).get("max_leeway"))
            if not fits.empty:
                fits.to_csv(out_dir / "polar_fits.csv", index=False)
            t = self.compare_at_equal_force(df, options)
            if not t.empty:
                t.to_csv(out_dir / "planform_compare.csv", index=False)
                files.append(self._compare_md(t, fits, design, cond, out_dir / "planform_compare.md"))

        if "mesh" in df and df["mesh"].nunique() > 1:
            files.append(self._check_md(df, design, "mesh", "medium", "Mesh check", out_dir / "mesh_check.md"))
        if "mesh_shift" in df and df["mesh_shift"].nunique() > 1:
            files.append(self._check_md(df, design, "mesh_shift", 0.0, "Grid-shift check", out_dir / "shift_check.md"))
        files += self._spanload_figure(df, design, cond, out_dir, options)
        files.append(self._planform_figure(df, design, out_dir / "planforms.png"))
        return files

    @staticmethod
    def _planform_figure(df, design, path: Path) -> Path:  # pragma: no cover - plotting
        """Side view of the designs in the run: canoe body, bulb, fin outlines."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6.5))
        first = df.iloc[0]
        hs = hull_spec(first)
        x = np.linspace(0, hs.length, 300)
        ax.fill_between(x, -hulls.canoe_depth(hs, x), 0, color="0.85", label="canoe body (centre line)")
        drawn = set()
        for i, (key, g) in enumerate(df.groupby(design)):
            r = g.iloc[0]
            shape = {k: r.get(k, v) for k, v in BULB_SHAPE.items()}
            if r.get("bulb", True) and tuple(shape.values()) not in drawn:
                drawn.add(tuple(shape.values()))
                xt, zt, xb, zb = ap.foil_bulb_lines(bulb_spec({**r, **shape}, r["bulb_length"], r["bulb_x_cg"],
                                                              r["bulb_z_axis"]), 300)
                h = r.get("bulb_height", r["bulb_diameter"])
                ax.fill(np.r_[xt, xb[::-1]], np.r_[zt, zb[::-1]], color="0.6", alpha=0.5,
                        label=f"bulb {r['bulb_section']}: {r['bulb_length'] * 1e3:.0f} x {r.get('bulb_width', h) * 1e3:.1f}"
                              f" x {h * 1e3:.1f} mm (L x W x H), {r['bulb_mass_kg'] * 1e3:.0f} g"
                              + "".join(f", {k} {shape[k]}" for k in BULB_SHAPE if k != "bulb_section"
                                        and shape[k] != BULB_SHAPE[k]))
            zr, span = r["fin_z_root"], r["fin_span"]
            cr, ct = r["fin_root_chord"], r["fin_tip_chord"]
            xq, xt = float(r["fin_x"]), float(r["fin_x"]) + math.tan(math.radians(float(r["fin_sweep"]))) * span
            ax.plot([xq - 0.25 * cr, xq + 0.75 * cr, xt + 0.75 * ct, xt - 0.25 * ct, xq - 0.25 * cr],
                    [zr, zr, zr - span, zr - span, zr], lw=1.6,
                    label=", ".join(f"{n} {v}" for n, v in zip(design, key if isinstance(key, tuple) else (key,)))
                    + f": {cr * 1e3:.0f} -> {ct * 1e3:.0f} mm")
        ax.axhline(-float(first["draft"]), color="r", lw=0.8, ls=":", label="draft limit")
        ax.set_aspect("equal")
        ax.set_xlim(0.0, hs.length)
        ax.set_xlabel("x from the bow [m]")
        ax.set_ylabel("z [m], waterline 0")
        ax.grid(alpha=0.3)
        ax.set_ylim(-float(first["draft"]) - 0.03, 0.02)
        ax.legend(fontsize=7, loc="center left")
        fig.tight_layout()
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        return path

    @staticmethod
    def _check_md(df, design, col: str, base_value, title: str, path: Path) -> Path:  # pragma: no cover - formatting
        """Forces of the cases run with more than one value of `col` (mesh,
        mesh_shift), everything else equal, as % change from `base_value`."""
        values = list(MESH_LEVELS) if col == "mesh" else sorted(df[col].unique())
        values = [v for v in values if v in set(df[col])]
        cols = [c for c in ("drag_N", "side_N", "drag_fin_N", "drag_bulb_N", "drag_hull_N", "eta_cp", "n_cells") if c in df]
        nuisance = [c for c in ("mesh", "mesh_shift", "fin_wake") if c != col and c in df and df[c].nunique() > 1]
        others = [c for c in [*design, "leeway", "speed", "heel", *nuisance] if c in df]
        L = [f"## {title}", "", f"Cases run with more than one {col} ({', '.join(map(str, values))}), all else equal. "
             f"In brackets: change from {col} {base_value}.", ""]
        L += ["| " + " | ".join([*others, col, *cols]) + " |", "|" + "---|" * (len(others) + 1 + len(cols))]
        for key, g in df.groupby(others):
            if g[col].nunique() < 2:
                continue
            g = g.set_index(col)
            base = g.loc[base_value] if base_value in g.index else None
            for v in values:
                if v not in g.index:
                    continue
                r = g.loc[v]
                cells = []
                for c in cols:
                    x = float(r[c])
                    txt = f"{x:.0f}" if c == "n_cells" else f"{x:.4g}"
                    if base is not None and v != base_value and c != "n_cells" and float(base[c]):
                        txt += f" ({100 * (x / float(base[c]) - 1):+.1f} %)"
                    cells.append(txt)
                L.append("| " + " | ".join([*(str(k) for k in (key if isinstance(key, tuple) else (key,))), str(v), *cells]) + " |")
        path.write_text("\n".join(L) + "\n")
        return path

    @staticmethod
    def _compare_md(t, fits, design, cond, path: Path) -> Path:  # pragma: no cover - formatting
        L = ["## Keel designs at equal side force S_h", "",
             "S_h = what the reference design makes at the given leeway. Leeway β_Y and drag D_h of every design "
             "at that S_h (interpolated along its leeway sweep), and the race time it loses against the best "
             "design (foil2d/methodology.md: half upwind with D_h and β_Y, half downwind with D_h at β_Y = 0; "
             "x1 / x2 = the estimated resistance slope V_b dD_h/dV_b and double it).", ""]
        cg = "bulb_cg_above_draft" in t and t["bulb_cg_above_draft"].nunique() > 1
        if cg:
            L[-1:-1] = ["The bulb's centre of mass is given above the draft (a lower one is more righting moment; "
                        "the race time doesn't count it).", ""]
        head = [*cond, *design, "load", "S_h [N]", "β_Y [deg]", "D_h [N]", "D_h at β_Y = 0 [N]",
                *(["bulb CG above draft [mm]"] if cg else []), "loss x1 / x2 [%]"]
        L += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for _, r in t.iterrows():
            loss = "-" if np.isnan(r["loss_x1_pct"]) else ("best" if r["loss_x1_pct"] < 1e-9 and r["loss_x2_pct"] < 1e-9
                                                           else f"{r['loss_x1_pct']:.2f} / {r['loss_x2_pct']:.2f}")
            L.append("| " + " | ".join([*(str(r[c]) for c in [*cond, *design]), r["load"], f"{r['side_N']:.3f}",
                                        f"{r['leeway']:.2f}", f"{r['drag_N']:.4f}", f"{r['drag0_N']:.4f}",
                                        *([f"{1e3 * r['bulb_cg_above_draft']:.1f}"] if cg else []), loss]) + " |")
        if not fits.empty:
            L += ["", "## Drag polar fits", "", "D_h = D0 + k S_h² over each leeway sweep; effective draft "
                  "T_eff = 1 / √(π q k) (ORC: D_i = S_h² / (π q T_eff²)); e_eff = 1 / (2π q d² k) on the draft d (the "
                  "waterline is a mirror plane). The fit includes the growth of viscous drag with S_h, so T_eff and "
                  "e_eff are lower than their induced-drag values.", ""]
            cols = [c for c in fits.columns if c != "n_points"]
            L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
            for _, r in fits.iterrows():
                L.append("| " + " | ".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
        path.write_text("\n".join(L) + "\n")
        return path

    def _spanload_figure(self, df, design, cond, out_dir: Path, options) -> list[Path]:  # pragma: no cover - plotting
        """Local cl and load along the span, at the leeway nearest the working load."""
        import matplotlib.pyplot as plt
        import pandas as pd

        run_dir = out_dir.parent
        if "mesh" in cond:  # the main mesh only, not the mesh check
            df = df[df["mesh"] == df["mesh"].value_counts().idxmax()]
            cond = [c for c in cond if c != "mesh"]
        target = float(((options or {}).get("compare_at") or {}).get("leeway", [2, 4, 6])[1]) if df["leeway"].nunique() > 1 else None
        groups = list(df.groupby([*cond, *design])) if (cond or design) else [("all", df)]
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
        drawn = 0
        for key, g in groups:
            r = g.iloc[(g["leeway"] - target).abs().argsort().iloc[0]] if target is not None else g.iloc[0]
            f = run_dir / str(r["case"]) / "spanload.csv"
            if not f.is_file():
                continue
            s = pd.read_csv(f)
            lab = f"{', '.join(f'{n} {v}' for n, v in zip([*cond, *design], key if isinstance(key, tuple) else (key,)))}, leeway {r['leeway']}"
            axs[0].plot(s["cl"], -s["eta"], "o-", ms=3, label=lab)
            axs[1].plot(s["side_N_per_m"] / s["side_N_per_m"].mean(), -s["eta"], "o-", ms=3, label=lab)
            drawn += 1
        if not drawn:
            plt.close(fig)
            return []
        eta = np.linspace(0, 1, 101)
        axs[1].plot(4 / math.pi * np.sqrt(1 - eta**2), -eta, "k--", lw=1, label="elliptic (hull as mirror, free tip)")
        axs[0].set_xlabel("local C_l (side force per metre on q × local chord)")
        axs[1].set_xlabel("S_h per metre of span / span mean")
        for ax in axs:
            ax.set_ylabel("span: 0 = hull, -1 = top of the bulb")
            ax.grid(alpha=0.3)
        axs[1].legend(fontsize=7)
        fig.tight_layout()
        path = out_dir / "spanload.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        return [path]


def _same(a, b) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
    except (TypeError, ValueError):
        return str(a) == str(b)
