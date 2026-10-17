"""foil2d transient force histories: joined across continuations, drift check
and the report's transient table (pure Python, no OpenFOAM)."""

import json

import numpy as np
import pytest

from iomcfd.project import load_project

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

FLOW_TIME = 0.1  # s, chord 0.1 m at 1 m/s
HEADER = "# Time    \tCd    \tCd(f)    \tCd(r)    \tCl    \tCl(f)    \tCl(r)    \tCmPitch\n"


def _coeffs(path, t, cl, cd):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(f"{a:.6g}\t{c:.6g}\t0\t0\t{b:.6g}\t0\t0\t0.01\n" for a, b, c in zip(t, cl, cd))
    path.write_text("# Force coefficients\n" + HEADER + rows)


def _case(root, rel, t, cl, cd, start="0", **params):
    case = root / rel
    _coeffs(case / "postProcessing" / "forceCoeffs" / start / "coefficient.dat", t, cl, cd)
    p = {"solver": "transient", "average_times": 6, "chord": 0.1, **params}
    (case / "params.json").write_text(json.dumps({"params": p, "derived": {"flowTime": FLOW_TIME}}))
    return case


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_SOURCE_RUNS", str(tmp_path / "bucket"))
    return load_project("foil2d")


def test_a_continued_case_is_joined_to_its_source(tmp_path, project):
    t1, t2 = np.arange(1, 151) * 0.01, np.arange(151, 301) * 0.01  # 0-15 and 15-30 flow-throughs
    _case(tmp_path / "bucket", "tc/r1/src", t1, 0.3 + 0 * t1, 0.015 + 0 * t1)
    new = _case(tmp_path / "local", "tc/r2/new", t2, 0.4 + 0 * t2, 0.014 + 0 * t2, start="1.5")
    # recorded on GCP: an absolute path under the bucket mount, found here by its last three parts
    (new / "start_from.json").write_text(json.dumps(
        {"case": "/mnt/disks/data/runs/tc/r1/src", "time": "1.5", "solver": "transient", "continued": True}))
    h = project.force_history(new)
    assert len(h) == 300 and np.all(np.diff(h[:, 0]) > 0)
    assert h[0, 1] == pytest.approx(0.3) and h[-1, 1] == pytest.approx(0.4)
    assert project.source_case(new) == tmp_path / "bucket" / "tc/r1/src"


def test_a_later_restart_replaces_what_it_overlaps(tmp_path, project):
    case = _case(tmp_path, "r/c", np.arange(1, 101) * 0.01, np.full(100, 0.3), np.full(100, 0.02))
    _coeffs(case / "postProcessing" / "forceCoeffs" / "0.8" / "coefficient.dat",
            np.arange(81, 121) * 0.01, np.full(40, 0.5), np.full(40, 0.03))
    h = project.force_history(case)
    assert len(h) == 120 and h[79, 1] == pytest.approx(0.3) and h[80, 1] == pytest.approx(0.5)


def test_force_history_csv_when_there_is_no_postprocessing(tmp_path, project):
    case = tmp_path / "light"
    case.mkdir()
    (case / "force_history.csv").write_text("t,flow_times,Cl,Cd,Cm\n0.1,1,0.39,0.015,0.01\n0.2,2,0.40,0.014,0.01\n")
    h = project.force_history(case)
    assert h.shape == (2, 4) and h[1, 1] == pytest.approx(0.40)


def test_drift_is_the_change_between_the_halves_of_the_window(project):
    t = np.linspace(0, 30, 3001)
    shedding = 0.04 * np.sin(2 * np.pi * t / 0.3)  # 10 % oscillation, many periods per half window
    steady = project.window_stats(t, 0.4 + shedding, 0.015 + 0 * t, 6.0)
    assert abs(steady["Cl_drift"]) < 0.002 and not steady["drifting"]
    rising = project.window_stats(t, 0.4 * (1 + 0.004 * (t - 24)) + shedding, 0.015 + 0 * t, 6.0)
    assert rising["Cl_drift"] == pytest.approx(0.012, rel=0.1) and rising["drifting"]  # +0.4 % per flow-through


def test_report_table_and_figure(tmp_path, project):
    run = tmp_path / "run"
    t = np.arange(1, 3001) * 0.001  # 30 flow-throughs
    _case(run.parent, "run/a", t, 0.4 + 0.04 * np.sin(2 * np.pi * t / 0.03), 0.015 + 0 * t)  # settled, shedding
    _case(run.parent, "run/b", t, 0.3 + 0.1 * t, 0.015 + 0 * t)  # still rising
    (run / "report").mkdir()
    df = pd.DataFrame({"case": ["a", "b", "c"], "solver": "transient", "status": "ok"})
    files = project._transient_report(run, df, run / "report")
    assert {f.name for f in files} == {"transient.md", "force_history.png"}
    md = (run / "report" / "transient.md").read_text()
    rows = {line.split(" | ")[0].lstrip("| "): line for line in md.splitlines() if line.startswith("| a") or
            line.startswith("| b")}
    assert "**" not in rows["a"].split(" | ")[7] and "**+" in rows["b"].split(" | ")[7]  # Cl drift column
    assert "| 30.0 | 24-30 |" in rows["a"]
