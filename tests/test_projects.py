"""Render every project's smoke study (pure Python, no OpenFOAM needed) and an
optional end-to-end foil2d run in Docker (pytest -m docker)."""

import json
import re
import shutil
import subprocess

import pytest

from iomcfd import config
from iomcfd.project import list_projects, load_project
from iomcfd.runner import RunOptions, list_runs, run_study
from iomcfd.study import Study

# OpenFOAM keywords that must never appear as caseParameters entries (they
# would shadow or break sub-dictionaries in the dicts that #include it).
RESERVED = {"geometry", "mesh", "type", "value", "dimensions", "internalField", "boundaryField", "application",
            "turbulence", "patches", "solvers", "castellatedMesh", "endTime", "deltaT", "startTime", "writeInterval"}


def test_all_projects_listed():
    assert {"foil2d", "appendage3d", "hull", "sails", "fullboat"} <= set(list_projects())


@pytest.mark.parametrize("name", ["foil2d", "appendage3d", "hull", "sails", "fullboat"])
def test_render_smoke_study(tmp_path, name):
    project = load_project(name)
    study = Study.load(config.projects_dir() / name / "studies" / "smoke.yaml")
    cases = study.expand(project.defaults)
    run_study(project, study, cases[:1], RunOptions(render_only=True), tmp_path / "run", log=lambda *a: None)
    case = tmp_path / "run" / cases[0].name
    assert (case / "Allrun").is_file() and (case / "params.json").is_file()
    # initial conditions come from the template's 0/ (must be tracked in git: CI builds from a clean checkout)
    assert (case / "0" / "U").is_file() and any((case / "0" / f).is_file() for f in ("p", "p_rgh"))
    params = (case / "system" / "caseParameters").read_text()
    keys = {m.group(1) for m in re.finditer(r"^(\w+)\s", params, re.M)}
    assert not keys & RESERVED, keys & RESERVED
    # every $variable used by the template is defined in caseParameters
    used = set()
    for f in case.rglob("*"):
        if f.is_file() and f.parent.name in ("0", "system", "constant") and f.suffix not in (".stl", ".dat"):
            text = re.sub(r"//[^\n]*", "", f.read_text(errors="ignore"))  # drop comments
            if '#include "$FOAM_CASE/system/caseParameters"' in text:
                used |= set(re.findall(r"\$(\w+)", text))
    used -= {"FOAM_CASE", "internalField", "turbulence", "p", "p_rgh", "U", "kOmegaSSTCoeffs"}  # dict-local refs
    assert used <= keys, sorted(used - keys)
    json.loads((case / "params.json").read_text())


def test_template_files_parse_as_text():
    for p in config.projects_dir().glob("*/template/**/*"):
        if p.is_file() and p.suffix not in (".stl",):
            p.read_text()


@pytest.mark.docker
def test_foil2d_smoke_in_docker():
    if not shutil.which("docker"):
        pytest.skip("docker not installed")
    r = subprocess.run(["uv", "run", "iomcfd", "run", "foil2d/smoke", "--force"], cwd=config.home(),
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    sdir = config.runs_dir() / "foil2d-smoke"
    res = json.loads((sdir / list_runs(sdir)[-1] / "aoa4" / "result.json").read_text())
    assert 0.2 < res["metrics"]["Cl"] < 0.6


def test_render_stepped_smoke(tmp_path):
    """Stepped sections: marched mesh, first cell below the step, one
    non-orthogonal corrector, step height recorded."""
    project = load_project("foil2d")
    study = Study.load(config.projects_dir() / "foil2d" / "studies" / "stepped-smoke.yaml")
    cases = study.expand(project.defaults)
    run_study(project, study, cases, RunOptions(render_only=True), tmp_path / "run", log=lambda *a: None)
    for c in cases:
        case = tmp_path / "run" / c.name
        assert (case / "constant" / "polyMesh" / "owner").is_file()
        assert re.search(r"^stepHeight\s", (case / "system" / "caseParameters").read_text(), re.M)
        assert "nNonOrthogonalCorrectors 1;" in (case / "system" / "fvSolution").read_text()
        d = json.loads((case / "params.json").read_text())["derived"]
        assert d["mesh_spec"]["first_cell"] <= 0.1 * d["stepHeight"]  # 5 % of h at 'medium', xcoarse is 2x


def test_stepped_surface_order():
    """Surface samples of a stepped section sort LE -> TE along the contour,
    including the face, where x does not change."""
    import numpy as np

    from iomcfd.geometry import foils

    contour_param = type(load_project("foil2d")).extract.__globals__["_contour_param"]
    f = foils.load("stair1:naca0009")
    s_true = np.random.default_rng(1).permutation(np.linspace(0.001, f.perimeter - 0.001, 3000))
    pts = f.point(s_true)
    s = contour_param(f, pts[:, 0], pts[:, 1])
    assert np.allclose(s, s_true, atol=2e-4)
    up = s < f.s_le
    order = np.argsort(-s[up])  # upper surface LE -> TE
    x = pts[up][order, 0]
    assert x[0] < 0.01 and x[-1] > 0.99 and np.all(np.diff(x) > -1e-9)
