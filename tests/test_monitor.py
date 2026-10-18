"""Progress lines and divergence detection while a solver runs (monitor.py,
runner.run_case), without OpenFOAM: the solver is a script writing a log."""

import os
import stat
import sys
import time
import types
from pathlib import Path

import numpy as np

from iomcfd import monitor
from iomcfd.monitor import Monitor, end_time, read_state
from iomcfd.project import load_project
from iomcfd.runner import RunOptions, run_case

CONTROL = "application pimpleFoam;\nstartTime 0;\nstopAt endTime;\nendTime 2.4;\ndeltaT 8e-06;\n"


def _step(t, dt, co, exec_s):
    return (f"Courant Number mean: 0.02 max: {co}\ndeltaT = {dt}\nTime = {t}\n\nPIMPLE: iteration 1\n"
            f"bounding k, min: -1e-07 max: 0.001 average: 2e-06\nExecutionTime = {exec_s} s  ClockTime = {exec_s} s\n\n")


def _case(tmp_path, steps, control=CONTROL):
    (tmp_path / "system").mkdir(exist_ok=True)
    (tmp_path / "system" / "controlDict").write_text(control)
    (tmp_path / "log.pimpleFoam").write_text("".join(_step(*s) for s in steps))
    return tmp_path


class Clock:
    def __init__(self):
        self.now = time.time()

    def __call__(self):
        return self.now


def test_state_and_progress_line(tmp_path):
    case = _case(tmp_path, [(0.0004, 4e-4, 9.9, 10), (1.2, 4.4e-4, 10.0, 3600)])
    st = read_state(case)
    assert (st.log, st.time, st.start_time, st.end_time) == ("log.pimpleFoam", 1.2, 0.0004, 2.4)
    assert (st.delta_t, st.courant_max, st.exec_time, st.bounding) == (4.4e-4, 10.0, 3600, {"k": 2})
    lines = []
    m = Monitor("c1", case, progress=lambda: {"Cl": 0.4}, log=lines.append, progress_seconds=0)
    assert m.poll() is None
    assert "t 1.2/2.4 (50.0 %)" in lines[0] and "ETA 1.0 h" in lines[0] and "Cl 0.4" in lines[0]


def test_end_time_from_case_parameters(tmp_path):
    case = _case(tmp_path, [], control="endTime $maxIter;\n")
    (case / "system" / "caseParameters").write_text("maxIter         8000;\n")
    assert end_time(case) == 8000


def test_time_step_collapse(tmp_path):
    case = _case(tmp_path, [(0.3892, 4.4e-4, 10.0, 7497)])
    m = Monitor("c1", case, log=lambda s: None)
    assert m.poll() is None
    with open(case / "log.pimpleFoam", "a") as f:
        f.write(_step(0.389654, 1.2e-23, 9.97, 98000))
    assert m.poll() is None  # needs CONFIRM_POLLS polls in a row
    assert "time step collapsed" in m.poll()


def test_courant_blow_up(tmp_path):
    case = _case(tmp_path, [(0.3896, 3.5e-8, 125278.2, 7512)])
    m = Monitor("c1", case, log=lambda s: None)
    m.poll()
    assert "Courant number 1.25e+05" in m.poll()


def test_stalled_time(tmp_path):
    case = _case(tmp_path, [(0.389654, 1e-10, 9.9, 7600)])
    clock = Clock()
    m = Monitor("c1", case, log=lambda s: None, clock=clock)
    assert m.poll() is None
    clock.now += monitor.STALL_SECONDS + 60
    os.utime(case / "log.pimpleFoam", (clock.now, clock.now))  # the log still grows
    m.poll()
    assert "stuck at 0.3897" in m.poll()


def test_project_reason(tmp_path):
    case = _case(tmp_path, [(0.1, 4e-4, 9.0, 100)])
    m = Monitor("c1", case, diverged=lambda: "forces out of range", log=lambda s: None)
    m.poll()
    assert m.poll() == "forces out of range"


def _coefficients(case, t, cl, cd):
    d = case / "postProcessing" / "forceCoeffs" / "0"
    d.mkdir(parents=True)
    rows = "\n".join(f"{a:.8g}\t{c:.8g}\t0\t0\t{b:.8g}\t0\t0\t0\t0\t0\t0\t0\t0" for a, b, c in zip(t, cl, cd))
    (d / "coefficient.dat").write_text(
        "# Time Cd Cd(f) Cd(r) Cl Cl(f) Cl(r) CmPitch CmRoll CmYaw Cs Cs(f) Cs(r)\n" + rows + "\n")


def test_foil2d_divergence_and_progress(tmp_path):
    project = load_project("foil2d")
    p = {"solver": "transient", "average_times": 6, "conv_tol": 1e-3}
    d = {"flowTime": 0.08, "convWindow": 500}
    t = np.linspace(1e-5, 0.6, 1200)  # 7.5 flow-throughs: past the 6 of the averaging window
    cl, cd = 0.35 + 0.02 * np.sin(t * 300), np.full_like(t, 0.017)
    cl[:3], cd[:3] = 904, 122  # the impulsive start
    _coefficients(tmp_path, t, cl, cd)
    assert project.diverged(tmp_path, p, d) is None
    prog = project.progress(tmp_path, p, d)
    assert abs(prog["flow_times"] - 7.5) < 1e-6 and "Cl_drift" in prog

    blown = tmp_path / "blown"
    cl[-3:], cd[-3:] = 2.7e4, [1496, np.inf, 2.3e8]
    _coefficients(blown, t, cl, cd)
    assert "out of range" in project.diverged(blown, p, d)


def test_runner_stops_a_diverging_case(tmp_path):
    """The fake solver blows up and ignores the stop request: the runner
    kills it after the grace period and reports the case failed."""
    case_dir = tmp_path / "case"
    script = (
        "#!/usr/bin/env python3\nimport time\n"
        "with open('log.pimpleFoam', 'a') as f:\n"
        "    f.write('Courant Number mean: 0.02 max: 10\\ndeltaT = 0.0004\\nTime = 0.389\\n')\n"
        "    f.flush()\n"
        "    time.sleep(0.3)\n"
        "    while True:\n"
        "        f.write('Courant Number mean: 0.06 max: 125278\\ndeltaT = 1e-23\\nTime = 0.389654\\n')\n"
        "        f.flush()\n"
        "        time.sleep(0.05)\n"
    )

    class Fake:
        name = "fake"

        def prepare_case(self, cdir, params):
            (cdir / "system").mkdir(parents=True)
            (cdir / "system" / "controlDict").write_text(CONTROL)
            (cdir / "Allrun").write_text(script.replace("#!/usr/bin/env python3", f"#!{sys.executable}"))
            (cdir / "Allrun").chmod((cdir / "Allrun").stat().st_mode | stat.S_IXUSR)
            return {}

        def progress(self, *a):
            return {}

        def diverged(self, *a):
            return None

        def converged(self, *a):
            return False

        def extract(self, *a):
            return {}

    case = types.SimpleNamespace(name="case", index=0, params_hash="h", params={"np": 1})
    lines = []
    opts = RunOptions(poll_seconds=0.1, progress_seconds=0.2, stop_grace_seconds=0.5)
    r = run_case(Fake(), case, case_dir, opts, log=lines.append)
    assert r["status"] == "failed" and "time step collapsed" in r["diverged"]
    assert "stopAt noWriteNow;" in (case_dir / "system" / "controlDict").read_text()
    assert any(s.startswith("  DIVERGED  case") for s in lines)
    assert any(s.startswith("  killing   case") for s in lines)
    assert r["wall_time_s"] < 30
