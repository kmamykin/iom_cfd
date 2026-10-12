"""Render every project's smoke study (pure Python, no OpenFOAM needed) and an
optional end-to-end foil2d run in Docker (pytest -m docker)."""

import json
import re
import shutil
import subprocess

import pytest

from iomcfd import config
from iomcfd.project import list_projects, load_project
from iomcfd.runner import RunOptions, run_study
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
    run_study(project, study, cases[:1], RunOptions(render_only=True), runs=tmp_path, log=lambda *a: None)
    case = tmp_path / study.name / cases[0].name
    assert (case / "Allrun").is_file() and (case / "params.json").is_file()
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
    res = json.loads((config.runs_dir() / "foil2d-smoke" / "aoa4" / "result.json").read_text())
    assert 0.2 < res["metrics"]["Cl"] < 0.6
