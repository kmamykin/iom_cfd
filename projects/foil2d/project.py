"""foil2d: steady 2D section polars for keel fins, rudders (and sail sections).

Pipeline per case:
  derive()  fluid properties, Re, inflow vector, turbulence inflow, mesh sizes
  render()  structured C-grid -> constant/polyMesh, system/caseParameters
  Allrun    checkMesh + simpleFoam (stops on converged Cl/Cd averages);
            solver: transient restarts its steady start with pimpleFoam
  extract() Cl, Cd (pressure/friction split), Cm, y+, Cp/Cf, separation points
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from iomcfd import config, physics
from iomcfd.foam import find_dat, latest_time, read_dat, set_entry
from iomcfd.forces import read_forces, settled, window_stats
from iomcfd.geometry import cmesh, foils, stepped
from iomcfd.project import Project

# Mesh levels: each level doubles the cell count (factor sqrt(2) per direction),
# which is the refinement ratio used for grid-convergence (GCI) studies.
MESH_LEVELS = {"xcoarse": 0.5, "coarse": 1 / math.sqrt(2), "medium": 1.0, "fine": math.sqrt(2), "xfine": 2.0}

# Inputs that must match for a case to start from another case's fields
# (start_from): the same flow and the same mesh.
START_MATCH = ("foil", "chord", "aoa", "speed", "Re", "fluid", "temperature", "turbulence", "Tu",
               "viscosity_ratio", "decay_control", "mesh", "yplus", "farfield")
START_FIELDS = ("U", "p", "k", "omega", "nut", "gammaInt", "ReThetat")

# Transient runs: the Cl and Cd means of the two halves of the averaging
# window may differ by at most this fraction of the window mean; above it the
# case is flagged `drifting` (its time average has not settled: run longer).
DRIFT_TOL = 0.01
COEFF_LIMIT = 50.0  # |Cl| or |Cd| past this after the start-up: blown up (Project.diverged)
BLOCK_FLOW_TIMES = 3  # block length for the block means in report/transient.md

# 'medium' (factor 1) resolution. ~90k cells.
BASE_MESH = dict(n_surface=256, ds_le=1.0e-3, ds_te=2.0e-3, n_wake=96, n_normal=128)
# stepped sections, 'medium': wall spacing around each step as fractions of
# its height (cmesh.CMeshSpec.step_*); a stair1 step adds ~120 points per side
STEP_MESH = dict(step_corner=0.02, step_foot=0.1, step_recirc=0.1, step_growth=0.1)
STEP_FIRST_CELL = 0.05  # first cell at most this fraction of the smallest step height ('medium')

# solver: transient
TRANSIENT_FILES = ("controlDict", "fvSchemes", "fvSolution")  # system/ files that differ from steady
MIN_DT_FLOW_TIMES = 1e-6  # abort below this time step, in c/U (at Co 10: stair1 2e-3, NACA 0009 8e-3)
CHECKPOINT_FLOW_TIMES = 1.0  # with checkpoints, a time-accurate case writes its fields this often (c/U)
CHECKPOINT_ITERATIONS = 1000  # with checkpoints, a steady case writes its fields at most this many iterations apart


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
        extra = {}
        if stepped.is_stepped(p["foil"]):
            # wall spacings around the steps refine with the level too, and the
            # first cell stays well below the smallest step (else the step
            # sits inside the first cell at low speed: stair10's are 0.1 mm)
            mesh.update({k: v / f for k, v in STEP_MESH.items()})
            h_step = min(s.height for s in foils.load(str(p["foil"]), [config.geometry_dir() / "foils"]).steps) * c
            mesh["first_cell"] = min(h0, STEP_FIRST_CELL * h_step / f)
            extra["stepHeight"] = h_step
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
            "relaxU": float(p["relax_U"]),
            "relaxTurb": float(p["relax_turb"]),
            "relaxTransition": float(p["relax_transition"]),
            # mesh (not used by OpenFOAM, recorded for reference)
            "mesh_spec": mesh,
            **extra,
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
        if p.get("start_from"):
            self._start_from(case_dir, p, d)
        if foil.steps:
            # the cells fanning round a step reach 60-78 deg non-orthogonality
            # (smooth sections ~20 deg): one corrector per pressure solve
            # (also in a transient case's fvSolution.transient)
            for fs in sorted((case_dir / "system").glob("fvSolution*")):
                set_entry(fs, "nNonOrthogonalCorrectors", 1)
        self.write_parameters(case_dir, {k: v for k, v in d.items() if k != "mesh_spec"}, inputs=p)

    def _make_transient(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        """Switch the copied (steady) case to pimpleFoam with an adaptive time
        step. The template itself stays steady.

        With start_iter > 0 the steady setup stays in place for that many
        SIMPLE iterations and the time-accurate one goes to system/*.transient;
        Allrun then restarts the steady solution as time 0 of the transient
        run (unless start_from gives the initial fields). Started from the
        uniform inflow instead, NACA 0009 drifted for more than 15 c/U and a
        stair1 step diverged (stepped-checks run 1).
        """
        t_ref = float(p["chord"]) / d["magUInf"]  # one chord flow-through
        end = float(p["flow_times"]) * t_ref
        d["flowTime"] = t_ref
        d["simEndTime"] = end
        sysd = case_dir / "system"
        n_start = int(p.get("start_iter") or 0)
        if n_start > 0:  # keep the steady setup for the start
            for name in TRANSIENT_FILES:
                shutil.copy(sysd / name, sysd / f"{name}.steady")
        cd = sysd / "controlDict"
        set_entry(cd, "application", "pimpleFoam")
        set_entry(cd, "endTime", end)
        set_entry(cd, "deltaT", 1e-4 * t_ref)
        set_entry(cd, "writeControl", "adjustable")
        snap = float(p.get("snapshot_interval") or 0.0)
        if snap > 0:  # field snapshots for time animations
            set_entry(cd, "writeInterval", snap * t_ref)
            set_entry(cd, "purgeWrite", 0)
        else:
            set_entry(cd, "writeInterval", end)
        text = cd.read_text().replace(
            "writeControl    adjustable;",
            f"adjustTimeStep  yes;\nmaxCo           {float(p['max_co'])};\nmaxDeltaT       {0.05 * t_ref:.6g};\n"
            "writeControl    adjustable;",
            1,
        )
        # a diverged run's time step collapses towards 0 (stair1 crawled for
        # 4 h at dt ~1e-67 s): stop it with an error instead
        text = text.replace("functions\n{\n", (
            "functions\n{\n"
            "    timeStepGuard\n    {\n"
            "        type            runTimeControl;\n"
            "        libs            (utilityFunctionObjects);\n"
            "        satisfiedAction abort;\n"
            "        conditions\n        {\n"
            f"            minTimeStep {{ type minTimeStep; minValue {MIN_DT_FLOW_TIMES * t_ref:.6g}; }}\n"
            "        }\n    }\n\n"), 1)
        cd.write_text(text)
        set_entry(sysd / "fvSchemes", "default", "backward")  # first 'default' = ddtSchemes
        fs = sysd / "fvSolution"
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
        if n_start > 0:
            for name in TRANSIENT_FILES:
                (sysd / name).rename(sysd / f"{name}.transient")
                (sysd / f"{name}.steady").rename(sysd / name)
            set_entry(sysd / "controlDict", "endTime", n_start)
            set_entry(sysd / "controlDict", "writeInterval", n_start)

    @staticmethod
    def find_start_case(runs: list[str] | str, p: dict[str, Any]) -> tuple[Path, str, dict[str, Any]] | None:
        """The first finished case in `runs` ('<study>/<run id>', looked up in
        config.source_runs_dirs()) with the same flow and mesh as `p`, and
        the same max_co if both are transient, that has final fields.
        Returns (case dir, final time directory name, its params)."""
        def same(a, b) -> bool:
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
                return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
            return a == b

        for run in [runs] if isinstance(runs, str) else runs:
            for root in config.source_runs_dirs():
                rdir = Path(root) / run
                if not rdir.is_dir():
                    continue
                for cdir in sorted(rdir.iterdir()):
                    try:
                        sp = json.loads((cdir / "params.json").read_text())["params"]
                        status = json.loads((cdir / "result.json").read_text()).get("status")
                    except (OSError, ValueError, KeyError):
                        continue
                    if status not in ("ok", "not_converged") or not all(same(sp.get(k), p.get(k)) for k in START_MATCH):
                        continue
                    if sp.get("solver") == p["solver"] == "transient" and not same(sp.get("max_co"), p.get("max_co")):
                        continue
                    times = []
                    for t in cdir.iterdir():
                        try:
                            if float(t.name) > 0 and t.is_dir():
                                times.append((float(t.name), t.name))
                        except ValueError:
                            pass
                    if times:
                        return cdir, max(times)[1], sp
        return None

    # ------------------------------------------------------------------
    # checkpoints (iomcfd.checkpoint): resume a case on a new VM
    def checkpoint_setup(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """A time-accurate case on one rank writes its fields every
        CHECKPOINT_FLOW_TIMES flow-throughs and keeps the last two (purgeWrite
        2: the older is complete while the newer is written). A snapshot run
        already writes every snapshot_interval and keeps them all. Adjustable
        writes count from the start time, so the interval divides the time
        left exactly and the last write is at the end time. A steady case
        writes every CHECKPOINT_ITERATIONS iterations or less, an interval
        that divides max_iter: simpleFoam writes only on whole intervals, not
        at the end time otherwise (if max_iter has no divisor near it, the case
        runs without checkpoints). Decomposed ones (np > 1) are not supported:
        False."""
        if int(p.get("np") or 1) > 1:
            return False
        if p["solver"] != "transient":
            n = int(d["maxIter"])
            every = max(k for k in range(1, min(CHECKPOINT_ITERATIONS, n) + 1) if n % k == 0)
            if every < min(CHECKPOINT_ITERATIONS, n) / 4:
                return False
            set_entry(Path(case_dir) / "system" / "controlDict", "writeInterval", every)
            set_entry(Path(case_dir) / "system" / "controlDict", "purgeWrite", 2)
            return True
        if not float(p.get("snapshot_interval") or 0.0) > 0:
            sysd = Path(case_dir) / "system"
            cd = sysd / "controlDict.transient" if (sysd / "controlDict.transient").exists() else sysd / "controlDict"
            set_entry(cd, "writeInterval", self._checkpoint_interval(float(d.get("restartTime", 0.0)), d))
            set_entry(cd, "purgeWrite", 2)
        return True

    @staticmethod
    def _checkpoint_interval(start: float, d: dict[str, Any]) -> float:
        span = float(d["simEndTime"]) - start
        n = max(1, round(span / (CHECKPOINT_FLOW_TIMES * float(d["flowTime"]))))
        return span / n

    def checkpoint_restored(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any], time: str) -> None:
        """Continue from the restored time: past a steady start (start_iter)
        switch to the time-accurate setup now, as Allrun would after it, and
        divide the time left into whole write intervals again. A steady case
        just continues (its write interval divides max_iter already)."""
        if p["solver"] != "transient":
            return
        sysd = Path(case_dir) / "system"
        if (sysd / "controlDict.transient").exists():
            for name in TRANSIENT_FILES:
                (sysd / name).replace(sysd / f"{name}.steady")
                (sysd / f"{name}.transient").replace(sysd / name)
        if not float(p.get("snapshot_interval") or 0.0) > 0:
            set_entry(sysd / "controlDict", "writeInterval", self._checkpoint_interval(float(time), d))

    def _start_from(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> None:
        """Initial fields from an earlier case's final time (see start_from in
        defaults.yaml). The mesh is rebuilt from the same inputs, so the fields
        fit it. A transient source is continued: its final time directory
        (fields, old-time fields, time step) is copied and the solver starts
        there (startFrom latestTime) and runs to flow_times. Otherwise the
        source's fields replace those in 0/. The source is recorded in
        start_from.json."""
        found = self.find_start_case(p["start_from"], p)
        if found is None:
            raise ValueError(f"start_from {p['start_from']}: no finished case with the same flow and mesh and final "
                             "fields in " + ", ".join(str(r) for r in config.source_runs_dirs())
                             + " (fetch its fields: gcp fetch --only CASE)")
        src, t, sp = found
        n_src = json.loads((src / "params.json").read_text()).get("derived", {}).get("n_cells")
        if n_src is not None and n_src != d["n_cells"]:
            raise ValueError(f"start_from {src}: its mesh has {n_src} cells, this case's {d['n_cells']}")
        # the source replaces a transient case's steady start (start_iter): a
        # transient source is continued, a steady one already is a steady solution
        sysd = case_dir / "system"
        for name in TRANSIENT_FILES:
            if (sysd / f"{name}.transient").is_file():
                (sysd / f"{name}.transient").replace(sysd / name)
        continued = sp.get("solver") == p["solver"] == "transient"
        if continued:
            if float(t) >= d["simEndTime"] * (1 - 1e-9):
                raise ValueError(f"start_from {src}: it already ran to t = {t} s; flow_times "
                                 f"{p['flow_times']} ends at {d['simEndTime']:.6g} s")
            shutil.copytree(src / t, case_dir / t, symlinks=True)
            d["restartTime"] = float(t)
            if not float(p.get("snapshot_interval") or 0.0) > 0:
                # adjustable write times count from the start time: make the end one
                set_entry(case_dir / "system" / "controlDict", "writeInterval", d["simEndTime"] - float(t))
        else:
            for name in START_FIELDS:
                for f in (src / t / name, src / t / f"{name}.gz"):
                    if f.is_file():
                        for old in (case_dir / "0" / name, case_dir / "0" / f"{name}.gz"):
                            old.unlink(missing_ok=True)
                        if f.suffix == ".gz":
                            with gzip.open(f, "rb") as fi, open(case_dir / "0" / name, "wb") as fo:
                                shutil.copyfileobj(fi, fo)
                        else:
                            shutil.copy2(f, case_dir / "0" / name)
                        break
                else:
                    raise ValueError(f"start_from {src}: no field '{name}' in {t}/")
        rel = next((src.relative_to(r).as_posix() for r in map(Path, config.source_runs_dirs())
                    if src.is_relative_to(r)), None)  # <study>/<run id>/<case>, wherever the runs live
        (case_dir / "start_from.json").write_text(json.dumps(
            {"case": str(src), "source": rel, "time": t, "solver": sp.get("solver"), "continued": continued},
            indent=2) + "\n")

    # ------------------------------------------------------------------
    # transient force histories: joined across continuations, drift check
    @staticmethod
    def source_case(case_dir: Path) -> Path | None:
        """The case a continued transient case started from (its
        start_from.json), looked up in config.source_runs_dirs(); None if the
        case was not continued or its source is not here."""
        f = Path(case_dir) / "start_from.json"
        if not f.is_file():
            return None
        info = json.loads(f.read_text())
        if not info.get("continued"):
            return None
        rel = info.get("source") or "/".join(Path(info["case"]).parts[-3:])  # <study>/<run id>/<case>
        for root in config.source_runs_dirs():
            if (Path(root) / rel / "params.json").is_file():
                return Path(root) / rel
        return None

    def force_history(self, case_dir: Path) -> np.ndarray | None:
        """Force coefficients against time, shape (n, 4): t [s], Cl, Cd, Cm.

        A transient case continued from another (start_from) is joined to the
        history of the case it continued, recursively, so the two read as one
        run. Read from postProcessing/forceCoeffs (every restart; a later start
        replaces what it overlaps), else from force_history.csv (written by
        extract, already joined, and downloaded by a light fetch)."""
        case_dir = Path(case_dir)
        h = self._join(find_dat(case_dir, "forceCoeffs", "coefficient.dat"))
        if h is None:
            saved = case_dir / "force_history.csv"
            if saved.is_file():
                return np.loadtxt(saved, delimiter=",", skiprows=1, usecols=(0, 2, 3, 4), ndmin=2)
            return None
        src = self.source_case(case_dir)
        if src is not None:
            earlier = self.force_history(src)
            if earlier is not None:
                h = np.vstack([earlier[earlier[:, 0] < h[0, 0]], h])
        return h

    @staticmethod
    def window_stats(t, cl, cd, window: float) -> dict[str, Any]:
        """Drift over the averaging window (the last `window`, in t's units):
        the change of the Cl and Cd means from its first to its second half,
        relative to the window mean (Cl relative to at least 0.1, as for
        `unsteady`). `drifting` if either exceeds DRIFT_TOL."""
        t, cl, cd = map(np.asarray, (t, cl, cd))
        sel = t > t[-1] - window
        late = t > t[-1] - window / 2
        out: dict[str, Any] = {}
        for key, s, floor in (("Cl", cl, 0.1), ("Cd", cd, 0.0)):
            a, b = s[sel & ~late], s[sel & late]
            ref = max(abs(float(s[sel].mean())), floor)
            out[f"{key}_drift"] = float((b.mean() - a.mean()) / ref) if a.size and b.size and ref else float("nan")
        out["drifting"] = bool(max(abs(out["Cl_drift"]), abs(out["Cd_drift"])) > DRIFT_TOL)
        return out

    @staticmethod
    def _join(files: list[Path]) -> np.ndarray | None:
        """forceCoeffs files of successive starts (postProcessing/forceCoeffs/
        <start>/coefficient.dat, in start order) as one history, shape (n, 4):
        t, Cl, Cd, Cm. A later start replaces what it overlaps."""
        h = None
        for f in files:
            names, data = read_dat(f)
            if data.size == 0:
                continue
            col = {n: i for i, n in enumerate(names)}
            part = np.c_[data[:, 0], data[:, col["Cl"]], data[:, col["Cd"]], data[:, col["CmPitch"]]]
            h = part if h is None else np.vstack([h[h[:, 0] < part[0, 0]], part])
        return h

    # ------------------------------------------------------------------
    def _coeffs(self, case_dir: Path, p: dict[str, Any]):
        """Time (iteration), Cl, Cd, Cm of the running solver. Steady: every
        start joined, so a case resumed from a checkpoint reads as one run.
        Time-accurate: the latest start only."""
        files = find_dat(case_dir, "forceCoeffs", "coefficient.dat")
        h = self._join(files[-1:] if self._time_accurate_now(case_dir, p) else files)
        return None if h is None else tuple(h.T)

    def converged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> bool:
        """Windowed means of Cl and Cd stopped moving (relative conv_tol).
        Transient runs always run for flow_times."""
        if p["solver"] == "transient":
            return False
        c = self._coeffs(case_dir, p)
        if c is None:
            return False
        _, cl, cd, _ = c
        w, tol = int(d["convWindow"]), float(p["conv_tol"])
        return settled(cl, w, tol, max(abs(cl[-1]), 0.1)) and settled(cd, w, tol, abs(cd[-1]))

    @staticmethod
    def _time_accurate_now(case_dir: Path, p: dict[str, Any]) -> bool:
        """pimpleFoam is running (not the steady start of a transient case,
        during which Allrun keeps the transient setup in *.transient)."""
        return p["solver"] == "transient" and not (Path(case_dir) / "system" / "controlDict.transient").exists()

    def progress(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        """Latest Cl and Cd. Transient: flow-throughs, the lift oscillation over
        the last flow-through and the drift of the means over the averaging
        window (as `extract`). Steady: how far the windowed means still move,
        relative, against conv_tol (as `converged`)."""
        c = self._coeffs(case_dir, p)
        if c is None:
            return {}
        t, cl, cd, _ = c
        out: dict[str, Any] = {"Cl": float(cl[-1]), "Cd": float(cd[-1])}
        if self._time_accurate_now(case_dir, p):
            ft = float(d["flowTime"])
            out["flow_times"] = float(t[-1] / ft)
            last = t > t[-1] - ft
            mean = float(cl[last].mean())
            out["Cl_osc"] = float(cl[last].std() / max(abs(mean), 0.1))
            win = float(p["average_times"]) * ft
            if t[-1] - t[0] >= win:
                s = self.window_stats(t, cl, cd, win)
                out["Cl_drift"], out["Cd_drift"] = s["Cl_drift"], s["Cd_drift"]
        else:
            w = int(d["convWindow"])
            for key, series, scale in (("Cl", cl, max(abs(cl[-1]), 0.1)), ("Cd", cd, abs(cd[-1]))):
                st = window_stats(series, w)
                if st is not None and scale:
                    out[f"{key}_change"] = st[1] / scale
            out["conv_tol"] = float(p["conv_tol"])
        return out

    def diverged(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> str | None:
        """Force coefficients non-finite or past COEFF_LIMIT in the last three
        samples, once past the start-up (100 samples and, for a transient
        start from rest, half a flow-through: the impulsive start gives Cl in
        the hundreds for a few steps)."""
        c = self._coeffs(case_dir, p)
        if c is None or len(c[0]) < 100:
            return None
        t, cl, cd, _ = c
        if self._time_accurate_now(case_dir, p) and t[-1] - t[0] < 0.5 * float(d["flowTime"]):
            return None
        rows = np.c_[cl[-3:], cd[-3:]]
        bad = ~np.isfinite(rows) | (np.abs(rows) > COEFF_LIMIT)
        if bad.any(axis=1).all():
            return f"force coefficients out of range: Cl {cl[-1]:.3g}, Cd {cd[-1]:.3g} (t {t[-1]:.6g})"
        return None

    def extract(self, case_dir: Path, p: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        c = self._coeffs(case_dir, p)
        if c is None:
            return {"_status": "failed"}
        it, cl, cd, cm = c
        transient = p["solver"] == "transient"
        if transient:
            n_iter = len(it)  # this run's time steps
            # the whole history, joined with the case this one continued
            h = self.force_history(case_dir)
            it, cl, cd, cm = h.T
            ft = it / d["flowTime"]
            with open(case_dir / "force_history.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t", "flow_times", "Cl", "Cd", "Cm"])
                w.writerows(zip(*(np.char.mod("%.8g", a) for a in (it, ft, cl, cd, cm))))
            # time-average over the last average_times flow-throughs
            t_avg = float(p["average_times"]) * d["flowTime"]
            sel = it > it[-1] - t_avg
            out["time_s"] = float(it[-1])
            out["flow_times_done"] = float(it[-1] / d["flowTime"])
            out.update(self.window_stats(it, cl, cd, t_avg))
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
        # Each side's faces in order LE -> TE: by x on a smooth section; on a
        # stepped one by position along the contour (a step face has one x).
        foil = foils.load(str(p["foil"]), [config.geometry_dir() / "foils"]) if stepped.is_stepped(p["foil"]) else None
        if foil is None:
            upper = _upper_mask(x, y)
            sides = {"upper": np.where(upper)[0][np.argsort(x[upper])], "lower": np.where(~upper)[0][np.argsort(x[~upper])]}
        else:
            s = _contour_param(foil, x, y)
            upper = s < foil.s_le
            sides = {"upper": np.where(upper)[0][np.argsort(-s[upper])], "lower": np.where(~upper)[0][np.argsort(s[~upper])]}
        # Skin friction along the local surface tangent (LE -> TE on each side).
        # OpenFOAM's wallShearStress points opposite to the near-wall flow, so
        # Cf = -tau.t/q is > 0 where the flow is attached and < 0 where reversed.
        q = 0.5 * U**2
        cf = np.zeros_like(x)
        tx = np.ones_like(x)
        for idx in sides.values():
            pts = P[idx, :2]
            t = np.gradient(pts, axis=0)
            t /= np.linalg.norm(t, axis=1, keepdims=True)
            cf[idx] = -(T[idx, 3] * t[:, 0] + T[idx, 4] * t[:, 1]) / q
            tx[idx] = t[:, 0]
        order = np.lexsort((x, ~upper)) if foil is None else np.concatenate([sides["upper"], sides["lower"]])
        rows = [(bool(upper[i]), x[i], y[i], cp[i], cf[i]) for i in order]
        with open(case_dir / "surface.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["upper", "x_c", "y_c", "Cp", "Cf"])
            w.writerows(rows)
        res: dict[str, Any] = {}
        for side, idx in sides.items():
            if foil is not None:
                idx = idx[tx[idx] > 0.5]  # leave out step faces (x is not monotonic there)
            xs, cfs = x[idx], cf[idx]
            # laminar separation, reattachment, and a later (trailing-edge) separation
            sep = _first_crossing(xs, cfs, falling=True, start=0.01)
            rea = _first_crossing(xs, cfs, falling=False, start=sep) if sep is not None else None
            res[f"x_sep_{side}"] = sep
            res[f"x_reattach_{side}"] = rea
            res[f"x_te_sep_{side}"] = _first_crossing(xs, cfs, falling=True, start=max(rea or 0.0, 0.5))
            if foil is not None:
                # behind the most forward step on this side: where the flow
                # reattaches, in step heights from the step (0: no reversed
                # flow within 3 heights behind it; None: never reattaches)
                st = min((st for st in foil.steps if st.side == side), key=lambda st: st.x, default=None)
                if st is not None:
                    # first reversed flow on the surface behind the face (past a
                    # small corner eddy at the foot), then where it turns forward
                    rev = np.where((xs > st.x) & (xs < st.x + 3 * st.height) & (cfs < 0))[0]
                    rs = _first_crossing(xs, cfs, falling=False, start=xs[rev[0]]) if len(rev) else None
                    res[f"step_reattach_{side}"] = (0.0 if not len(rev) else
                                                    None if rs is None else (rs - st.x) / st.height)
        return res

    # ------------------------------------------------------------------
    def report(self, df, out_dir: Path, reference=None, options=None) -> list[Path]:  # pragma: no cover - plotting
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        files = self._sections(df, out_dir)
        df = df[df["status"].isin(["ok", "not_converged"])].copy()
        if df.empty:
            return files
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
        n_groups = len(groups) if group_cols else 1
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
        if n_groups <= 16:
            axs[0, 0].legend(fontsize=7)
        else:  # too many lines to label; selection.png separates them
            axs[0, 0].set_title(f"{n_groups} combinations of {', '.join(group_cols)}", fontsize=9)
        fig.tight_layout()
        polar = out_dir / "polar.png"
        fig.savefig(polar, dpi=130)
        plt.close(fig)
        files.append(polar)
        files += self._selection(df, out_dir, options)
        gci = self._mesh_convergence(df, out_dir)
        if gci:
            files.append(gci)
        files += self._transient_report(Path(out_dir).parent, df, out_dir)
        return files

    def _transient_report(self, run_dir: Path, df, out_dir: Path) -> list[Path]:
        """report/transient.md and force_history.png for the transient cases:
        time averages over the averaging window, the oscillation and drift in
        it, and 3-flow-through block means, from each case's joined force
        history (postProcessing, else force_history.csv). Cases whose history
        is not here are listed as such (fetch them with --only)."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if "solver" not in df or not (df["solver"] == "transient").any():
            return []
        tr = df[df["solver"] == "transient"].sort_values("case")
        md = ["## Transient statistics", "",
              f"Over each case's averaging window (the last `average_times` flow-throughs, c/U). Osc: standard "
              f"deviation of Cl / mean. Drift: change of the mean from the first to the second half of the window, "
              f"relative to the window mean; **drifting** above {DRIFT_TOL:.0%} (run longer). Blocks: means over "
              f"successive {BLOCK_FLOW_TIMES} flow-throughs, the last four. Continued cases are joined to the case "
              f"they continued (start_from).", "",
              "| case | start | flow-throughs | window | Cl | Cl osc | Cd | Cl drift | Cd drift | Cl blocks | Cd blocks |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        hists = []
        for _, r in tr.iterrows():
            cdir = Path(run_dir) / r["case"]
            try:
                pdict = json.loads((cdir / "params.json").read_text())
            except OSError:
                continue
            p, d = pdict["params"], pdict["derived"]
            start = "rest"
            sf = cdir / "start_from.json"
            if sf.is_file():
                info = json.loads(sf.read_text())
                src = info.get("source") or "/".join(Path(info["case"]).parts[-3:])
                start = (f"continued: {src} at {info['time']} s" if info.get("continued")
                         else f"{info.get('solver', '')} {src}")
            h = self.force_history(cdir)
            if h is None:
                md.append(f"| {r['case']} | {start} | no force history here (gcp fetch --only) | | | | | | | | |")
                continue
            ft = h[:, 0] / d["flowTime"]
            win = float(p["average_times"])
            sel = ft > ft[-1] - win
            st = self.window_stats(ft, h[:, 1], h[:, 2], win)
            cl, cdm = h[sel, 1].mean(), h[sel, 2].mean()
            edges = np.arange(ft[-1], 0, -BLOCK_FLOW_TIMES)[:5][::-1]
            blocks = [(h[(ft > a) & (ft <= b), 1].mean(), h[(ft > a) & (ft <= b), 2].mean())
                      for a, b in zip(edges[:-1], edges[1:])]
            drift = lambda v: f"**{v:+.1%}**" if abs(v) > DRIFT_TOL else f"{v:+.1%}"  # noqa: E731
            md.append(f"| {r['case']} | {start} | {ft[-1]:.1f} | {ft[-1] - win:.0f}-{ft[-1]:.0f} | {cl:.4f} | "
                      f"{h[sel, 1].std() / max(abs(cl), 0.1):.1%} | {cdm:.5f} | {drift(st['Cl_drift'])} | "
                      f"{drift(st['Cd_drift'])} | {', '.join(f'{b[0]:.4f}' for b in blocks)} | "
                      f"{', '.join(f'{b[1]:.5f}' for b in blocks)} |")
            restart = None
            if sf.is_file() and json.loads(sf.read_text()).get("continued"):
                restart = float(json.loads(sf.read_text())["time"]) / d["flowTime"]
            hists.append((r["case"], ft, h, win, restart))
        md_path = Path(out_dir) / "transient.md"
        md_path.write_text("\n".join(md) + "\n")
        files = [md_path]
        if hists:
            fig, axs = plt.subplots(len(hists), 2, figsize=(14, 2.2 * len(hists) + 0.6), squeeze=False)
            for (name, ft, h, win, restart), row in zip(hists, axs):
                for ax, k, lab in ((row[0], 1, "Cl"), (row[1], 2, "Cd")):
                    ax.plot(ft, h[:, k], lw=0.4, color="0.6")
                    edges = np.arange(ft[-1], 0, -BLOCK_FLOW_TIMES)[::-1]
                    for a, b in zip(edges[:-1], edges[1:]):
                        m = (ft > a) & (ft <= b)
                        if m.any():
                            ax.hlines(h[m, k].mean(), a, b, color="C0", lw=1.5)
                    ax.axvspan(ft[-1] - win, ft[-1], color="C1", alpha=0.12)
                    if restart:
                        ax.axvline(restart, color="C3", lw=0.8, ls="--")
                    tail = h[ft > ft[-1] - 2 * win, k]
                    pad = 0.6 * (tail.max() - tail.min()) + 1e-9
                    ax.set_ylim(tail.min() - pad, tail.max() + pad)
                    ax.set_ylabel(lab)
                    ax.set_title(f"{name}: {lab}", fontsize=8)
                    ax.grid(alpha=0.3)
            for ax in axs[-1]:
                ax.set_xlabel("flow-throughs (c/U)")
            fig.suptitle(f"Force histories (grey), {BLOCK_FLOW_TIMES}-flow-through block means (blue), averaging "
                         "window (orange), restart of a continued case (red)", fontsize=10)
            fig.tight_layout(rect=(0, 0, 1, 1 - 0.45 / fig.get_figheight()))
            png = Path(out_dir) / "force_history.png"
            fig.savefig(png, dpi=100)
            plt.close(fig)
            files.append(png)
        return files

    @staticmethod
    def _sections(df, out_dir: Path) -> list[Path]:  # pragma: no cover - plotting
        """Studies with stepped sections: sections.png (every section of the
        study at true scale) and a section_<spec>.png sheet per stepped one
        (iomcfd.sectionplot). Geometry only, so drawn even if cases failed."""
        if "foil" not in df or not any(stepped.is_stepped(s) for s in df["foil"].astype(str)):
            return []
        from iomcfd.sectionplot import study_sections

        chord = float(df["chord"].min()) if "chord" in df else 0.08
        try:
            return study_sections(list(df["foil"].astype(str)), out_dir, chord, [config.geometry_dir() / "foils"],
                                  title=Path(out_dir).parent.parent.name)
        except (ValueError, FileNotFoundError) as e:  # e.g. a run made with a spec that no longer exists
            print(f"sections figure skipped: {e}")
            return []

    def _selection(self, df, out_dir: Path, options=None):
        """Section/chord selection: drag against side force.

        At a fixed fin span (the class draught limit) the fin must produce a
        given side force; a longer chord does that at a lower Cl, so sections
        and chords are compared at equal lift force, not equal Cl. One panel
        per speed (columns) and per turbulence model / Tu (rows, whichever the
        study varies); colour = section, line style = chord. Only for studies
        that vary the section or chord (not the mesh).

        Study `report:` options: `fin_span` [m] turns the per-metre 2D forces
        into whole-fin forces [N]; `induced_drag: true` adds the lifting-line
        induced drag of that span (hull as a reflection plane; it is the same
        for every candidate at equal side force, so it shows the size of the
        differences, not a different ranking); `span_efficiency` (default 0.9);
        `compare_at: {foil, chord, aoa}` sets the side forces of the comparison
        table (see _compare_at_equal_force).
        Writes selection.png, the plotted numbers (selection.csv) and the
        comparison table (selection_compare.csv / .md). Returns the files.
        """
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from iomcfd.physics import induced_drag

        need = {"foil", "chord", "aoa", "lift_N_per_m", "drag_N_per_m"}
        if not need <= set(df) or (df["foil"].nunique() < 2 and df["chord"].nunique() < 2):
            return []
        if "mesh" in df and df["mesh"].nunique() > 1:  # a mesh study: the GCI table, not a selection
            return []
        opts = dict(options or {})
        span = float(opts["fin_span"]) if opts.get("fin_span") else None
        with_induced = bool(opts.get("induced_drag"))
        e = float(opts.get("span_efficiency", 0.9))
        if with_induced and span is None:
            raise ValueError("report: induced_drag needs fin_span")

        t = df.copy()
        if span is None:
            t["side_force"], t["drag_section"] = t["lift_N_per_m"], t["drag_N_per_m"]
            unit, what = "N/m", "per metre of span (2D)"
        else:
            t["side_force"], t["drag_section"] = t["lift_N_per_m"] * span, t["drag_N_per_m"] * span
            unit, what = "N", f"whole fin, span {span * 1000:g} mm"
        t["drag_induced"] = 0.0
        if with_induced:
            q = 0.5 * t["rhoInf"] * t["magUInf"] ** 2
            t["drag_induced"] = induced_drag(t["side_force"], q, span, e)
            what += f", section + induced drag (lifting line, e = {e:g})"
        t["drag"] = t["drag_section"] + t["drag_induced"]
        keep = [c for c in ("foil", "chord", "speed", "Re", "turbulence", "Tu", "aoa", "side_force", "drag_section",
                            "drag_induced", "drag", "unsteady", "status") if c in t]
        t[keep].sort_values([c for c in ("foil", "chord", "speed", "turbulence", "Tu", "aoa") if c in t]) \
            .to_csv(out_dir / "selection.csv", index=False)

        speeds = sorted(t["speed"].unique()) if "speed" in t else [None]
        row_cols = [c for c in ("turbulence", "Tu") if c in t and t[c].nunique() > 1]
        rows = (sorted(t[row_cols].drop_duplicates().itertuples(index=False, name=None),
                       key=lambda r: tuple((v != "kOmegaSSTLM", v) if isinstance(v, str) else (False, v) for v in r))
                if row_cols else [()])  # transition model first, then increasing Tu
        foils = sorted(t["foil"].unique())
        chords = sorted(t["chord"].unique())
        colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        styles = ["-", "--", ":", "-."]
        width = max(4.2 * len(speeds), 10.0)  # wide enough for the title and legend
        fig, axs = plt.subplots(len(rows), len(speeds), figsize=(width, 3.8 * len(rows) + 0.6), squeeze=False)
        for i, row in enumerate(rows):
            for j, speed in enumerate(speeds):
                ax = axs[i, j]
                sub = t
                if speed is not None:
                    sub = sub[sub["speed"] == speed]
                for c, v in zip(row_cols, row):
                    sub = sub[sub[c] == v]
                for k, foil in enumerate(foils):
                    for m, chord in enumerate(chords):
                        g = sub[(sub["foil"] == foil) & (sub["chord"] == chord)].sort_values("aoa")
                        if g.empty:
                            continue
                        ax.plot(g["side_force"], g["drag"], styles[m % len(styles)], marker="o", ms=3,
                                color=colors[k % len(colors)], label=f"{foil}, c = {chord * 1000:g} mm")
                        unsteady = g[g["unsteady"].astype(str) == "True"] if "unsteady" in g else g.iloc[0:0]
                        if not unsteady.empty:  # steady answer of an unsteady flow: less certain
                            ax.plot(unsteady["side_force"], unsteady["drag"], "x", ms=7, color=colors[k % len(colors)])
                title = []
                if speed is not None:
                    title.append(f"{speed:g} m/s")
                title += [f"Tu {v:g} %" if c == "Tu" else str(v) for c, v in zip(row_cols, row)]
                ax.set_title(", ".join(title), fontsize=10)
                ax.set_xlabel(f"side force (lift) [{unit}]")
                ax.set_ylabel(f"drag [{unit}]")
                ax.grid(alpha=0.3)
        h, lab = axs[0, 0].get_legend_handles_labels()
        ncol = min(len(lab), 6, max(1, int(width // 2.4)))
        legend_rows = -(-len(lab) // ncol)
        H = fig.get_figheight()
        fig.tight_layout()  # panels first, then make room at the top for the title and the legend
        fig.subplots_adjust(top=1 - (0.95 + 0.2 * legend_rows) / H)
        fig.suptitle(f"Section and chord selection, {what}\nlower curve = less drag for the same side force "
                     "(points: aoa 0, 2, 4...; x: unsteady)", y=1 - 0.05 / H, va="top", fontsize=11)
        fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 1 - 0.55 / H), ncol=ncol, fontsize=8,
                   frameon=False)
        path = out_dir / "selection.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        files = [path, out_dir / "selection.csv"]
        files += self._compare_at_equal_force(t, row_cols, rows, speeds, opts, unit, what, out_dir)
        return files

    @staticmethod
    def _compare_at_equal_force(t, row_cols, rows, speeds, opts, unit, what, out_dir: Path) -> list[Path]:
        """Every candidate's drag at the same side forces, as % above the best.

        The side forces are those the reference candidate makes at the
        reference angles (`compare_at: {foil, chord, aoa}`; default: the
        middle section, the shortest chord, aoa 2/4/6), i.e. roughly light,
        typical and high upwind leeway. Other candidates are interpolated
        linearly along their pre-stall branch: the points up to the maximum
        side force where it rises with aoa (a dip near 0°, the low-Re lift
        reversal of thick sections, is skipped); '-' = that force is outside
        it. '*' = interpolated from an unsteady or not-converged point.
        Only the (foil, chord) pairs the run has are candidates (a study may
        zip them). If the reference is not one of them (a study's later run
        that drops it), the nearest candidate is used instead: the same foil
        if there is one, then the closest chord; the table says so.
        """
        import pandas as pd

        foils, chords = sorted(t["foil"].unique()), sorted(t["chord"].unique())
        cands = sorted({(f, float(c)) for f, c in zip(t["foil"], t["chord"])})
        ref = dict(opts.get("compare_at") or {})
        ref_foil = ref.get("foil", foils[len(foils) // 2])
        ref_chord = float(ref.get("chord", chords[0]))
        angles = ref.get("aoa", [2, 4, 6])

        def label(foil, chord):
            return f"{str(foil).removeprefix('naca')}/{chord * 1000:g}"

        note = ""
        if not any(f == ref_foil and np.isclose(c, ref_chord) for f, c in cands):
            asked = label(ref_foil, ref_chord)
            ref_foil, ref_chord = min(cands, key=lambda fc: (fc[0] != ref_foil, abs(fc[1] - ref_chord), fc[0]))
            note = (f" The reference {asked} (report.compare_at) is not in this run; {label(ref_foil, ref_chord)} "
                    "is used instead, so the forces differ from runs that had it.")
            print(f"report: compare_at {asked} is not in this run; using {label(ref_foil, ref_chord)}")

        def drag_at(g, force):
            g = g.sort_values("aoa")
            sf, dr = g["side_force"].to_numpy(), g["drag"].to_numpy()
            shaky = ((g["status"] != "ok") | (g["unsteady"].astype(str) == "True")).to_numpy() if "unsteady" in g \
                else (g["status"] != "ok").to_numpy()
            if not len(sf):
                return None, False
            keep, low = [], np.inf  # walk down from the maximum, keep a strictly rising branch
            for k in range(int(np.argmax(sf)), -1, -1):
                if sf[k] < low:
                    keep.append(k)
                    low = sf[k]
            keep = keep[::-1]
            sf, dr, shaky = sf[keep], dr[keep], shaky[keep]
            if not len(sf) or force < sf[0] - 1e-12 or force > sf[-1] + 1e-12:
                return None, False
            i = int(np.clip(np.searchsorted(sf, force), 1, max(1, len(sf) - 1)))
            if len(sf) == 1:
                return float(dr[0]), bool(shaky[0])
            return float(np.interp(force, sf, dr)), bool(shaky[i - 1] or shaky[i])

        records = []
        for row in rows:
            for speed in speeds:
                sub = t if speed is None else t[t["speed"] == speed]
                for c, v in zip(row_cols, row):
                    sub = sub[sub[c] == v]
                r = sub[(sub["foil"] == ref_foil) & np.isclose(sub["chord"], ref_chord)].set_index("aoa")
                for a in angles:
                    if a not in r.index:
                        continue
                    force = float(r.loc[a, "side_force"])
                    got = {}
                    for foil, chord in cands:
                        g = sub[(sub["foil"] == foil) & np.isclose(sub["chord"], chord)]
                        got[(foil, chord)] = drag_at(g, force) if not g.empty else (None, False)
                    valid = [d for d, _ in got.values() if d is not None]
                    best = min(valid) if valid else None
                    for (foil, chord), (d, shaky) in got.items():
                        records.append({**dict(zip(row_cols, row)), "speed": speed, "ref_aoa": a,
                                        "side_force": force, "foil": foil, "chord": chord, "drag": d,
                                        "above_best_pct": 100 * (d / best - 1) if d is not None and best else None,
                                        "uncertain": shaky})
        if not records:
            return []
        cmp = pd.DataFrame(records)
        cmp["rank"] = cmp.groupby([*row_cols, "speed", "ref_aoa"])["drag"].rank(method="min")
        csv_path = out_dir / "selection_compare.csv"
        cmp.to_csv(csv_path, index=False)

        md = [f"## Drag at equal side force ({what})", "",
              f"Side forces: what {label(ref_foil, ref_chord)} makes at aoa {', '.join(f'{a:g}' for a in angles)}°."
              f"{note} Cells: % drag above the lowest at that force; **best** = lowest; '-' = force outside that "
              "candidate's pre-stall range; '*' = interpolated from an unsteady or not-converged point.", ""]
        for row in rows:
            if row_cols:
                md += [f"### {', '.join(f'Tu {v:g} %' if c == 'Tu' else str(v) for c, v in zip(row_cols, row))}", ""]
            md.append(f"| speed [m/s] | aoa ref | side force [{unit}] | lowest drag [{unit}] | "
                      + " | ".join(label(f, c) for f, c in cands) + " |")
            md.append("|---|---|---|---|" + "---|" * len(cands))
            sel = cmp
            for c, v in zip(row_cols, row):
                sel = sel[sel[c] == v]
            for (speed, a), g in sel.groupby(["speed", "ref_aoa"], sort=True, dropna=False):
                g = g.set_index(["foil", "chord"])
                lowest = g["drag"].min()
                cells = []
                for f, c in cands:
                    d, pct, shaky = g.loc[(f, c), "drag"], g.loc[(f, c), "above_best_pct"], g.loc[(f, c), "uncertain"]
                    if pd.isna(d):
                        cells.append("-")
                        continue
                    cell = "**best**" if pct < 0.05 else f"+{pct:.0f}%"
                    cells.append(cell + ("*" if shaky else ""))
                sp = "-" if pd.isna(speed) else f"{speed:g}"
                md.append(f"| {sp} | {a:g}° | {g['side_force'].iloc[0]:.3g} | {lowest:.3g} | " + " | ".join(cells) + " |")
            md.append("")
        md_path = out_dir / "selection_compare.md"
        md_path.write_text("\n".join(md))
        return [csv_path, md_path]

    highlight_columns = ["Cl", "Cd", "Cd_friction", "x_sep_upper", "x_reattach_upper", "x_te_sep_upper",
                         "x_sep_lower", "x_reattach_lower", "unsteady"]

    def highlight_report(self, run_dir: Path, df, highlights, out_dir: Path) -> list[Path]:
        """report/highlights.md plus, per highlight, highlight_<name>.png:
        pressure and skin friction along the chord from each case's
        surface.csv (no field data needed), one line per compared value."""
        files = super().highlight_report(run_dir, df, highlights, out_dir)
        for h, lay in highlights:
            f = self._surface_figure(Path(run_dir), df, h, lay, Path(out_dir) / f"highlight_{h.name}.png")
            if f:
                files.append(f)
        return files

    @staticmethod
    def _surface_figure(run_dir: Path, df, h, lay, out: Path) -> Path | None:
        """Rows: the highlight's rows. Columns: Cp (solid upper, dashed lower
        surface), Cf on the upper and on the lower surface; Cf < 0 is reversed
        flow (laminar separation bubble, trailing-edge separation). The upper
        surface is the suction side at positive aoa."""
        import textwrap

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd

        unsteady = set(df.loc[df["unsteady"].astype(str) == "True", "case"]) if "unsteady" in df else set()
        colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        nr = len(lay.rows)
        head = [f"{h.name}: pressure and skin friction along the chord (Cf < 0: reversed flow)",
                *textwrap.wrap(h.why, 170)]
        fig, axs = plt.subplots(nr, 3, figsize=(17, 3.7 * nr + 0.3 + 0.2 * len(head)), squeeze=False)
        cf_in = [[[], []] for _ in range(nr)]  # Cf away from the edges, for the axis limits
        drew = False
        for i, (label, cells) in enumerate(lay.rows):
            for j, col in enumerate(lay.columns):
                c = cells.get(col)
                f = run_dir / c.name / "surface.csv" if c is not None else None
                if f is None or not f.is_file():
                    continue
                s = pd.read_csv(f)
                up = s[s["upper"].astype(str) == "True"].sort_values("x_c")
                lo = s[s["upper"].astype(str) != "True"].sort_values("x_c")
                name = (f"{lay.compare} {col:g}" if isinstance(col, float) else f"{lay.compare} {col}") \
                    if lay.compare else c.name
                name += " (unsteady)" if c.name in unsteady else ""
                st = dict(color=colors[j % len(colors)], lw=1.3)
                axs[i, 0].plot(up["x_c"], up["Cp"], "-", label=name, **st)
                axs[i, 0].plot(lo["x_c"], lo["Cp"], "--", **{**st, "lw": 0.9})
                axs[i, 1].plot(up["x_c"], up["Cf"], "-", label=name, **st)
                axs[i, 2].plot(lo["x_c"], lo["Cf"], "-", label=name, **st)
                for k, side in ((0, up), (1, lo)):
                    cf_in[i][k] += list(side.loc[(side["x_c"] > 0.03) & (side["x_c"] < 0.97), "Cf"])
                drew = True
        if not drew:
            plt.close(fig)
            return None
        for i, (label, _) in enumerate(lay.rows):
            pre = f"{label}: " if label else ""
            axs[i, 0].set_title(pre + "Cp (solid: upper, dashed: lower surface)", fontsize=10)
            axs[i, 0].invert_yaxis()
            axs[i, 0].set_ylabel("Cp")
            if axs[i, 0].get_legend_handles_labels()[0]:  # a row can be empty while a run is unfinished
                axs[i, 0].legend(fontsize=8)
            for k, ax in ((0, axs[i, 1]), (1, axs[i, 2])):
                ax.set_title(pre + f"Cf, {'upper (suction)' if k == 0 else 'lower'} surface", fontsize=10)
                ax.axhline(0.0, color="k", lw=0.6)
                vals = np.array(cf_in[i][k])
                if len(vals):
                    lo_, hi_ = np.percentile(vals, [1, 99])
                    pad = 0.15 * (hi_ - min(lo_, 0.0))
                    ax.set_ylim(min(lo_, 0.0) - pad, hi_ + pad)
                ax.set_ylabel("Cf")
            for ax in axs[i]:
                ax.set_xlim(0.0, 1.0)
                ax.set_xlabel("x/c")
                ax.grid(alpha=0.3)
        H = fig.get_figheight()
        fig.suptitle("\n".join(head), x=0.01, y=1 - 0.08 / H, ha="left", va="top", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 1 - (0.15 + 0.2 * len(head)) / H))
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=110)
        plt.close(fig)
        return out

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
        views = [
            MeshView("whole domain: C-grid, wake cut to the outlet", center=(0.0, 0.0), width=3.4 * R, lw=0.15, **cut),
            MeshView("foil", center=(0.55 * c, 0.0), width=1.45 * c, **cut),
            MeshView("leading edge", center=(0.03 * c, 0.0), width=0.12 * c, **cut),
            MeshView("trailing edge and start of the wake cut", center=(c, 0.0), width=0.12 * c, **cut),
        ]
        surface = f"{m['n_surface'] + 1} points per surface"
        try:  # a run made with a spec that no longer exists keeps the standard views
            foil = foils.load(str(p["foil"]), [config.geometry_dir() / "foils"]) if stepped.is_stepped(p["foil"]) else None
        except ValueError:
            foil = None
        if foil is not None:
            st = min((s for s in foil.steps if s.side == "upper"), key=lambda s: s.x)  # most forward upper step
            h = st.height * c
            y_lip = float(foil.point(np.array([st.s_lip[0]]))[0, 1]) * c
            views += [
                MeshView(f"upper step at x/c = {st.x:.2f}: lip, face and recirculation zone",
                         center=(st.x * c + 3 * h, y_lip), width=10 * h, **cut),
                MeshView("step: lip and foot corners", center=(st.x * c + 0.3 * h, y_lip - 0.5 * h), width=2 * h, lw=0.4, **cut),
            ]
            surface = f"surface points refined around {len(foil.steps) // 2} step(s) per side (height {h * 1000:.3f} mm)"
        return MeshSpec(
            views,
            walls="foil",
            notes=[f"structured C-grid: {surface}, {m['n_normal']} wall-normal cells, "
                   f"{m['n_wake']} wake cells, first cell {m['first_cell'] / c:.1e} c, far field {m['farfield']:.0f} c"],
        )

    def resources(self, p: dict[str, Any]) -> dict[str, Any]:
        f = MESH_LEVELS.get(p.get("mesh", "medium"), 1.0)
        # stepped sections have more cells: stair1 ~1.3x, stair5 3x, stair10 5.5x
        k = 1.0
        preset = stepped.parse_spec(str(p["foil"]))[0] if stepped.is_stepped(p.get("foil", "")) else None
        if preset:
            k = {"stair5": 3.0, "stair10": 4.0}.get(preset, 2.0)
        # steady: up to ~1.05 s an iteration on the medium mesh (fin-profile-selection's
        # 8000-iteration cases took up to 7330 s), so 2.5 h per 8000 iterations
        hours = 2.5 * f * f * k * int(p.get("max_iter") or 8000) / 8000
        if p.get("solver") == "transient":
            hours = 2 * f * f * k  # mesh and the steady start (start_iter)
            # 15 c/U at Co 10 on the medium mesh took 1.3 h for NACA 0009 (4
            # ranks); a stair1 step's cells cut the time step 3.6x and add
            # cells (~5x). stair5/stair10 are guesses from their smallest cells.
            # One rank is ~2.7x slower than 4 (transient-check's local probe).
            kt = {"stair5": 20.0, "stair10": 60.0}.get(preset, 5.0) if preset else 1.0
            ranks = max(1.0, 4 / max(int(p.get("np", 1)), 1)) ** 0.72
            hours += 2 * f**3 * kt * float(p.get("flow_times", 15)) / 15 * 10 / float(p.get("max_co", 10)) * ranks
        return {"cpus": int(p.get("np", 1)), "memory_gb": 2, "max_hours": 1 + hours}


def _find_raw(d: Path, field: str) -> Path | None:
    for cand in sorted(d.glob(f"*{field}*")):
        if cand.is_file():
            return cand
    return None


def _contour_param(foil, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Foil parameter (TE upper -> LE -> TE lower) of the contour point nearest
    to each (x, y) (unit chord)."""
    from scipy.spatial import cKDTree

    s = np.unique(np.concatenate([np.linspace(0.0, foil.perimeter, 40001), foil.s_nodes]))
    _, k = cKDTree(foil.point(s)).query(np.column_stack([x, y]))
    return s[k]


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
