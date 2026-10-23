"""Checkpoints: resume a case after its machine is lost (iomcfd.checkpoint,
runner.run_case, foil2d's hooks). No OpenFOAM: the solver is a script."""

import json
import os
import re
import stat
import sys
import time
import types

import pytest

from iomcfd.checkpoint import MANIFEST, Checkpoint
from iomcfd.project import load_project
from iomcfd.runner import RunOptions, run_case


def _time_dir(case, t, age=0.0, text="U"):
    d = case / t
    (d / "uniform").mkdir(parents=True, exist_ok=True)
    (d / "U").write_text(f"{text} at {t}\n")
    (d / "uniform" / "time").write_text("deltaT 1e-4;\n")
    if age:
        old = time.time() - age
        for f in d.rglob("*"):
            os.utime(f, (old, old))
    return d


def test_saves_the_newest_complete_time_and_restores_it(tmp_path):
    case = tmp_path / "case"
    _time_dir(case, "0.1", age=300)
    _time_dir(case, "0.2", age=300)
    _time_dir(case, "0.3")  # being written now
    (case / "postProcessing" / "forceCoeffs" / "0").mkdir(parents=True)
    (case / "postProcessing" / "forceCoeffs" / "0" / "coefficient.dat").write_text(
        "# Time Cd Cl\n0.1 0.01 0.4\n0.2 0.011 0.41\n0.3 0.0")  # last line mid-write
    ck = Checkpoint(tmp_path / "bucket" / "case", interval=0, settle=60)
    assert ck.maybe_save(case, "h1") == "0.2"
    assert ck.maybe_save(case, "h1") is None  # nothing newer is complete
    saved = json.loads((tmp_path / "bucket" / "case" / MANIFEST).read_text())
    assert saved["time"] == "0.2" and saved["slot"] == "a"
    dat = tmp_path / "bucket" / "case" / "a" / "postProcessing" / "forceCoeffs" / "0" / "coefficient.dat"
    assert dat.read_text().endswith("0.2 0.011 0.41\n")  # the incomplete line is left out

    new = tmp_path / "new"
    new.mkdir()
    assert Checkpoint(tmp_path / "bucket" / "case").restore(new, "other hash") is None
    assert Checkpoint(tmp_path / "bucket" / "case").restore(new, "h1") == "0.2"
    assert (new / "0.2" / "U").read_text() == "U at 0.2\n"
    assert (new / "0.2" / "uniform" / "time").is_file()
    assert (new / "postProcessing" / "forceCoeffs" / "0" / "coefficient.dat").is_file()


def test_slots_alternate_and_the_interval_is_kept(tmp_path):
    case = tmp_path / "case"
    _time_dir(case, "0.1")
    now = [time.time() + 1]  # a clock we move by hand, after the files' times
    ck = Checkpoint(tmp_path / "ck", interval=600, settle=0, clock=lambda: now[0])
    assert ck.maybe_save(case, "h") == "0.1"
    _time_dir(case, "0.2")
    now[0] += 100
    assert ck.maybe_save(case, "h") is None  # too soon
    now[0] += 600
    assert ck.maybe_save(case, "h") == "0.2"
    m = json.loads((tmp_path / "ck" / MANIFEST).read_text())
    assert m["slot"] == "b" and (tmp_path / "ck" / "a" / "0.1").is_dir()  # the previous one survives a failed copy
    ck.clear()
    assert not (tmp_path / "ck").exists()


# --- foil2d -------------------------------------------------------------------


def _params(project, **kw):
    p = dict(project.defaults)
    p.update(foil="naca0008", chord=0.08, aoa=4, speed=1.0, Tu=0.1, mesh="xcoarse", solver="transient",
             flow_times=20, start_iter=0)
    p.update(kw)
    return p


def _entry(path, key):
    return re.search(rf"^{key}\s+([^;]+);", path.read_text(), re.M).group(1)


def test_foil2d_writes_every_flow_through_and_resumes(tmp_path):
    project = load_project("foil2d")
    p = _params(project)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    assert project.checkpoint_setup(case, p, d)
    cd = case / "system" / "controlDict"
    assert float(_entry(cd, "writeInterval")) == pytest.approx(d["simEndTime"] / 20)
    assert _entry(cd, "purgeWrite") == "2"
    project.checkpoint_restored(case, p, d, "0.7")  # 8.75 of 20 flow-throughs (t_ref 0.08 s)
    w = float(_entry(cd, "writeInterval"))
    left = d["simEndTime"] - 0.7
    assert left / w == pytest.approx(round(left / w)) and w == pytest.approx(d["flowTime"], rel=0.1)


def test_foil2d_steady_start_switches_on_restore(tmp_path):
    project = load_project("foil2d")
    p = _params(project, start_iter=2000)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    assert project.checkpoint_setup(case, p, d)
    tr = case / "system" / "controlDict.transient"
    assert float(_entry(tr, "writeInterval")) == pytest.approx(d["simEndTime"] / 20)
    project.checkpoint_restored(case, p, d, "0.5")
    assert not tr.exists() and (case / "system" / "controlDict.steady").exists()
    assert _entry(case / "system" / "controlDict", "application") == "pimpleFoam"


@pytest.mark.parametrize("max_iter, every", [(8000, 1000), (12000, 1000), (2500, 625), (300, 300)])
def test_foil2d_steady_writes_on_whole_intervals(tmp_path, max_iter, every):
    """simpleFoam writes only on whole write intervals (not at the end time),
    so the interval divides max_iter; a restored steady case just continues."""
    project = load_project("foil2d")
    p = _params(project, solver="steady", max_iter=max_iter)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    assert project.checkpoint_setup(case, p, d)
    cd = case / "system" / "controlDict"
    assert int(_entry(cd, "writeInterval")) == every and max_iter % every == 0
    assert _entry(cd, "purgeWrite") == "2"
    assert "writeInterval   1;" in cd.read_text()  # the function objects' intervals are left alone
    before = cd.read_text()
    project.checkpoint_restored(case, p, d, str(every))
    assert cd.read_text() == before


HEADER = "# Time    \tCd    \tCd(f)    \tCd(r)    \tCl    \tCl(f)    \tCl(r)    \tCmPitch\n"


def _coeffs(case, start, its, cl):
    path = case / "postProcessing" / "forceCoeffs" / start / "coefficient.dat"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "".join(f"{i}\t0.02\t0\t0\t{cl:g}\t0\t0\t0.01\n" for i in its))


def test_foil2d_steady_history_joins_across_a_resume(tmp_path):
    """Resumed at iteration 2500 (the checkpoint's postProcessing runs on to
    3000): the later start replaces the overlap, and convergence, progress
    and the result see one run of 4200 iterations."""
    project = load_project("foil2d")
    p = _params(project, solver="steady", max_iter=8000)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    _coeffs(case, "0", range(1, 3001), 0.3)
    _coeffs(case, "2500", range(2501, 4201), 0.4)
    it, cl, _, _ = project._coeffs(case, p)
    assert len(it) == 4200 and it[-1] == 4200 and cl[2499] == pytest.approx(0.3) and cl[2500] == pytest.approx(0.4)
    assert project.converged(case, p, d)
    assert project.progress(case, p, d)["Cl"] == pytest.approx(0.4)
    out = project.extract(case, p, d)
    assert out["iterations"] == 4200 and out["converged"] and out["Cl"] == pytest.approx(0.4)


def test_foil2d_steady_convergence_spans_the_restart(tmp_path):
    """300 iterations since the resume are fewer than two windows (2 x 500):
    only the joined history can show the means have settled."""
    project = load_project("foil2d")
    p = _params(project, solver="steady", max_iter=8000)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    _coeffs(case, "0", range(1, 2001), 0.4)
    _coeffs(case, "2000", range(2001, 2301), 0.4)
    assert project.converged(case, p, d)


@pytest.mark.parametrize("kw", [{"np": 2}, {"solver": "steady", "max_iter": 7919}])
def test_foil2d_no_checkpoints(tmp_path, kw):
    project = load_project("foil2d")
    p = _params(project, **kw)
    case = tmp_path / "case"
    d = project.prepare_case(case, p)
    before = (case / "system" / "controlDict").read_text()
    assert not project.checkpoint_setup(case, p, d)
    assert (case / "system" / "controlDict").read_text() == before


# --- runner -------------------------------------------------------------------

SOLVER = """#!PYTHON
# A fake solver: continues from the latest time directory (like startFrom
# latestTime), writes one every 0.1 s of simulated time, and loses its
# machine at t = 0.3 on the first attempt.
import os, sys, time
from pathlib import Path
times = [float(d.name) for d in Path('.').iterdir() if d.is_dir() and d.name.replace('.', '').isdigit()]
start = max(times, default=0.0)
pp = Path('postProcessing/forceCoeffs') / f'{start:g}'
pp.mkdir(parents=True, exist_ok=True)
Path('started_at').write_text(f'{start:g}')
t = start
while t < 0.5 - 1e-9:
    t = round(t + 0.1, 6)
    (Path(f'{t:g}') / 'uniform').mkdir(parents=True, exist_ok=True)
    (Path(f'{t:g}') / 'U').write_text(f'U at {t:g}\\n')
    with open(pp / 'coefficient.dat', 'a') as f:
        f.write(f'{t:g} 0.01 0.4\\n')
    time.sleep(0.4)
    lost = Path(os.environ.get('LOSE_MACHINE', '/nonexistent'))
    if t >= 0.3 and lost.parent.is_dir() and not lost.exists():
        lost.write_text('')
        sys.exit(137)
"""


class _Fake:
    name = "fake"

    def prepare_case(self, cdir, params):
        if cdir.exists():
            import shutil

            shutil.rmtree(cdir)
        (cdir / "system").mkdir(parents=True)
        (cdir / "system" / "controlDict").write_text("application pimpleFoam;\nendTime 0.5;\n")
        (cdir / "Allrun").write_text(SOLVER.replace("PYTHON", sys.executable))
        (cdir / "Allrun").chmod((cdir / "Allrun").stat().st_mode | stat.S_IXUSR)
        return {}

    def checkpoint_setup(self, *a):
        return True

    def checkpoint_restored(self, cdir, p, d, t):
        (cdir / "restored").write_text(t)

    def progress(self, *a):
        return {}

    def diverged(self, *a):
        return None

    def converged(self, *a):
        return False

    def extract(self, *a):
        return {}


def test_runner_resumes_a_case_after_losing_its_machine(tmp_path, monkeypatch):
    monkeypatch.setenv("LOSE_MACHINE", str(tmp_path / "lost-once"))
    monkeypatch.setattr("iomcfd.checkpoint.Checkpoint.__init__.__defaults__", (0.0, 0.1, time.time))
    case = types.SimpleNamespace(name="c", index=0, params_hash="h", params={"np": 1})
    opts = RunOptions(poll_seconds=0.05, progress_seconds=60, checkpoint_seconds=0.0)
    ck_dir = tmp_path / "bucket"
    lines = []
    first = run_case(_Fake(), case, tmp_path / "vm1" / "c", opts, log=lines.append, checkpoint_dir=ck_dir)
    assert first["status"] == "failed"
    saved = json.loads((ck_dir / "c" / MANIFEST).read_text())["time"]
    assert float(saved) >= 0.1 and any(s.startswith("  checkpoint c: t =") for s in lines)

    second = run_case(_Fake(), case, tmp_path / "vm2" / "c", opts, log=lines.append, checkpoint_dir=ck_dir)
    assert second["status"] == "ok" and second["resumed_from"] == saved
    assert (tmp_path / "vm2" / "c" / "started_at").read_text() == saved  # it continued, not restarted
    assert (tmp_path / "vm2" / "c" / "restored").read_text() == saved
    assert (tmp_path / "vm2" / "c" / "0.5" / "U").is_file()
    assert not (ck_dir / "c").exists()  # finished: the checkpoint is gone
