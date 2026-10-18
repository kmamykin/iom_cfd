"""foil2d start_from: initial fields from an earlier case (pure Python, no OpenFOAM)."""

import json
import re

import pytest

from iomcfd.project import load_project
from iomcfd.study import params_hash


def _params(project, **kw):
    p = dict(project.defaults)
    p.update(foil="naca0008", chord=0.08, aoa=4, speed=1.0, Tu=0.1, mesh="xcoarse", solver="transient")
    p.update(kw)
    return p


def _source(project, root, run, name, status="ok", time="1.2", **kw):
    """A finished case in root/run/name, with a fake final time directory."""
    case = root / run / name
    project.prepare_case(case, _params(project, **kw))
    (case / "result.json").write_text(json.dumps({"status": status}))
    (case / time / "uniform").mkdir(parents=True)
    for f in ("U", "p", "k", "omega", "nut", "gammaInt", "ReThetat", "U_0"):
        (case / time / f).write_text(f"{f} from {name}\n")
    (case / time / "uniform" / "time").write_text("deltaT 1e-4;\n")
    return case


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_SOURCE_RUNS", str(tmp_path / "bucket"))
    return load_project("foil2d")


def test_empty_start_from_keeps_the_hash():
    p = {"foil": "naca0008", "aoa": 4, "Re": None}
    assert params_hash(p) == params_hash({**p, "start_from": []})
    assert params_hash(p) != params_hash({**p, "start_from": ["a/20260101-000000"]})


def test_transient_case_continues_from_the_final_time(tmp_path, project):
    root = tmp_path / "bucket"
    _source(project, root, "tc/r1", "other", max_co=5)  # different time step: not this one
    _source(project, root, "tc/r1", "failed", status="failed")
    src = _source(project, root, "tc/r1", "same")
    case = tmp_path / "new"
    project.prepare_case(case, _params(project, flow_times=30, start_from=["tc/r1"]))
    assert (case / "1.2" / "U_0").read_text() == "U_0 from same\n"  # old-time fields come along
    assert (case / "1.2" / "uniform" / "time").is_file()  # and the time step
    info = json.loads((case / "start_from.json").read_text())
    assert info["case"] == str(src) and info["continued"] and info["time"] == "1.2"
    assert "restartTime" in (case / "system" / "caseParameters").read_text()
    # write times count from the start time (1.2 s): the end, 2.4 s, must be one, or no final fields
    m = re.search(r"^writeInterval\s+([0-9.eE+-]+);", (case / "system" / "controlDict").read_text(), re.M)
    assert float(m.group(1)) == pytest.approx(1.2)


def test_falls_back_to_a_steady_run(tmp_path, project):
    root = tmp_path / "bucket"
    _source(project, root, "tc/r1", "same", status="failed")  # e.g. diverged
    _source(project, root, "sel/r3", "steady", time="2016", solver="steady")
    case = tmp_path / "new"
    project.prepare_case(case, _params(project, flow_times=30, start_from=["tc/r1", "sel/r3"]))
    assert (case / "0" / "U").read_text() == "U from steady\n"  # steady fields become the initial ones
    assert not (case / "2016").exists()
    assert json.loads((case / "start_from.json").read_text())["continued"] is False


@pytest.mark.parametrize("solver, time", [("transient", "1.2"), ("steady", "2016")])
def test_start_from_replaces_the_steady_start(tmp_path, project, solver, time):
    """A transient case's steady start (start_iter) is dropped when start_from
    gives the initial fields: the time-accurate setup is the active one."""
    _source(project, tmp_path / "bucket", "tc/r1", "src", time=time, solver=solver)
    case = tmp_path / "new"
    project.prepare_case(case, _params(project, flow_times=30, start_iter=2000, start_from=["tc/r1"]))
    assert not list((case / "system").glob("*.transient"))
    cd = (case / "system" / "controlDict").read_text()
    assert re.search(r"^application\s+pimpleFoam;", cd, re.M) and "timeStepGuard" in cd
    assert "PIMPLE" in (case / "system" / "fvSolution").read_text()
    if solver == "transient":  # writeInterval set on the transient controlDict, not a steady one
        m = re.search(r"^writeInterval\s+([0-9.eE+-]+);", cd, re.M)
        assert float(m.group(1)) == pytest.approx(1.2)


def test_no_matching_case_is_an_error(tmp_path, project):
    _source(project, tmp_path / "bucket", "tc/r1", "same", chord=0.09)
    with pytest.raises(ValueError, match="no finished case"):
        project.prepare_case(tmp_path / "new", _params(project, flow_times=30, start_from=["tc/r1"]))


def test_nothing_left_to_run_is_an_error(tmp_path, project):
    _source(project, tmp_path / "bucket", "tc/r1", "same")
    with pytest.raises(ValueError, match="already ran"):  # flow_times 15 at 1 m/s, 80 mm: ends at 1.2 s
        project.prepare_case(tmp_path / "new", _params(project, flow_times=15, start_from=["tc/r1"]))
