"""Visualisation orchestration (no ParaView needed) and an optional render
in the viz image (pytest -m docker)."""

import json
import shutil
import subprocess

import pytest

from iomcfd import config
from iomcfd.study import Case
from iomcfd.viz import study as vstudy


@pytest.mark.parametrize("project", ["foil2d", "appendage3d", "hull", "sails", "fullboat"])
def test_view_metadata_loads_without_paraview(project):
    meta = vstudy.load_viz_meta(project)
    assert meta.DEFAULT_VIEWS and set(meta.DEFAULT_VIEWS) <= set(meta.VIEWS)
    assert set(meta.ANIMATE_VIEWS) <= set(meta.VIEWS)
    assert set(meta.TIME_VIEWS) <= set(meta.VIEWS)
    assert all(callable(f) for f in meta.VIEWS.values())


def _cases(rows):
    return [Case(name=f"c{i}", index=i, params=r, varied=r) for i, r in enumerate(rows)]


def test_animation_axis_prefers_project_order():
    cases = _cases([{"aoa": a, "turbulence": t} for t in ("A", "B") for a in (4, 0, 8)])
    axis, others = vstudy.animation_axis(cases, ["aoa", "Tu"], None)
    assert axis == "aoa" and others == ["turbulence"]
    groups = vstudy.animation_groups(cases, axis, others)
    assert set(groups) == {"turbulenceA", "turbulenceB"}
    assert [c.varied["aoa"] for c in groups["turbulenceA"]] == [0, 4, 8]  # sorted along the axis
    axis, _ = vstudy.animation_axis(cases, ["aoa"], "turbulence")
    assert axis == "turbulence"
    with pytest.raises(SystemExit):
        vstudy.animation_axis(cases, ["aoa"], "speed")


def test_axis_with_most_values_and_study_order_for_words():
    rows = [{"aoa": a, "mesh": m} for a in (2, 8) for m in ("coarse", "medium", "fine")]
    cases = _cases(rows)
    axis, others = vstudy.animation_axis(cases, ["aoa", "mesh"], None)
    assert axis == "mesh" and others == ["aoa"]
    g = vstudy.animation_groups(cases, axis, others)["aoa2"]
    assert [c.varied["mesh"] for c in g] == ["coarse", "medium", "fine"]


def test_single_case_has_no_animation_groups():
    cases = _cases([{"aoa": 4}])
    axis, others = vstudy.animation_axis(cases, ["aoa"], None)
    assert vstudy.animation_groups(cases, axis, others) == {}


def test_gallery_lists_views_and_animations(tmp_path):
    class S:
        name, description = "demo", "a study"

    case = tmp_path / "c0"
    (case / "viz").mkdir(parents=True)
    (case / "viz" / "velocity.png").write_bytes(b"png")
    (case / "result.json").write_text(json.dumps({"status": "ok", "metrics": {"Cl": 0.4}}))
    (tmp_path / "viz").mkdir()
    anim = [{"view": "velocity", "axis": "aoa", "group": "", "values": [0, 4], "files": ["velocity_by_aoa.mp4"]}]
    index = vstudy.write_gallery(S, tmp_path, _cases([{"aoa": 0}]), ["velocity", "pressure"], anim)
    html = index.read_text()
    assert "../c0/viz/velocity.png" in html and "velocity_by_aoa.mp4" in html and "pressure.png" not in html


def test_has_fields(tmp_path):
    (tmp_path / "0").mkdir()
    (tmp_path / "0" / "U").write_text("x")
    assert not vstudy.has_fields(tmp_path)  # initial conditions only
    (tmp_path / "1500").mkdir()
    (tmp_path / "1500" / "U").write_text("x")
    assert vstudy.has_fields(tmp_path)


@pytest.mark.docker
def test_foil2d_render_in_viz_image():
    if not shutil.which("docker"):
        pytest.skip("docker not installed")
    from iomcfd.runner import list_runs

    sdir = config.runs_dir() / "foil2d-smoke"
    runs = list_runs(sdir)
    if not runs:
        pytest.skip("run `make smoke` first")
    case = sdir / runs[-1] / "aoa4"
    if not vstudy.has_fields(case):
        pytest.skip("run `make smoke` first")
    r = subprocess.run(["uv", "run", "iomcfd", "viz", "foil2d/smoke", "--views", "velocity,pressure"],
                       cwd=config.home(), capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    manifest = json.loads((case / "viz" / "viz.json").read_text())
    assert manifest["views"]["velocity"]["status"] == "ok"
    assert (case / "viz" / "velocity.png").stat().st_size > 50_000
    assert (sdir / runs[-1] / "viz" / "index.html").is_file()
