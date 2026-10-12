"""Timestamped runs: every `iomcfd run` writes runs/<study>/<run id>/; nothing
is overwritten; --resume and --run-id continue a run (no OpenFOAM)."""

import argparse
import datetime as dt
import json

import pytest

from iomcfd import cli, config
from iomcfd.project import load_project
from iomcfd.runner import RunOptions, is_run_id, list_runs, new_run_id, resolve_run, run_study
from iomcfd.study import Study


def _smoke():
    project = load_project("foil2d")
    study = Study.load(config.projects_dir() / "foil2d" / "studies" / "smoke.yaml", {"mesh": "xcoarse"})
    return project, study, study.expand(project.defaults)


def _args(tmp_path, **kw):
    return argparse.Namespace(**{"study": "foil2d/smoke", "runs": str(tmp_path), "run_id": None, "resume": False, **kw})


def test_run_id_format():
    rid = new_run_id(dt.datetime(2026, 10, 12, 4, 54, 33, tzinfo=dt.timezone.utc))
    assert rid == "20261012-045433" and is_run_id(rid)
    assert not is_run_id("latest") and not is_run_id("../x") and not is_run_id("20261012")


def test_each_run_gets_its_own_directory(tmp_path):
    project, study, cases = _smoke()
    for rid in ("20261012-045433", "20261013-090000"):
        run_study(project, study, cases[:1], RunOptions(render_only=True), tmp_path / study.name / rid,
                  log=lambda *a: None)
    sdir = tmp_path / study.name
    assert list_runs(sdir) == ["20261012-045433", "20261013-090000"]
    (sdir / "notes").mkdir()  # not a run id: ignored
    assert resolve_run(study, tmp_path) == sdir / "20261013-090000"
    assert resolve_run(study, tmp_path, "latest") == sdir / "20261013-090000"
    assert resolve_run(study, tmp_path, "20261012-045433") == sdir / "20261012-045433"
    with pytest.raises(SystemExit):
        resolve_run(study, tmp_path, "20200101-000000")
    old = sdir / "20261012-045433"
    assert (old / cases[0].name / "params.json").is_file() and (old / "study.yaml").is_file()
    info = json.loads((old / "run.json").read_text())
    assert info["run_id"] == "20261012-045433" and info["study"] == "foil2d-smoke"
    assert info["overrides"] == {"mesh": "xcoarse"}


def test_resume_keeps_the_original_study_file(tmp_path):
    project, study, cases = _smoke()
    rdir = tmp_path / study.name / "20261012-045433"
    run_study(project, study, cases[:1], RunOptions(render_only=True), rdir, log=lambda *a: None)
    (rdir / "study.yaml").write_text("# as first run\n" + (rdir / "study.yaml").read_text())
    run_study(project, study, cases[:1], RunOptions(render_only=True), rdir, log=lambda *a: None)
    assert (rdir / "study.yaml").read_text().startswith("# as first run")


def test_target_run(tmp_path):
    project, study, cases = _smoke()
    with pytest.raises(SystemExit):  # nothing to resume yet
        cli._target_run(_args(tmp_path, resume=True), study)
    new = cli._target_run(_args(tmp_path), study)
    assert new.parent == tmp_path / study.name and is_run_id(new.name)
    new.mkdir(parents=True)
    assert cli._target_run(_args(tmp_path, resume=True), study) == new
    a = _args(tmp_path)
    a.run_id = "20261012-045433"
    assert cli._target_run(a, study).name == "20261012-045433"  # created later if missing (cloud tasks)
    a.run_id = "my-run"
    with pytest.raises(SystemExit):
        cli._target_run(a, study)


def test_post_processing_uses_the_runs_own_study_file(tmp_path):
    project, study, cases = _smoke()
    rdir = tmp_path / study.name / "20261012-045433"
    run_study(project, study, cases, RunOptions(render_only=True), rdir, log=lambda *a: None)
    snap = rdir / "study.yaml"
    snap.write_text(snap.read_text().replace("description:", "report: {fin_span: 0.3}\ndescription:", 1))
    st, _, run_cases, got = cli._load_run(_args(tmp_path))
    assert got == rdir and st.report == {"fin_span": 0.3}
    assert [c.name for c in run_cases] == [c.name for c in cases]


def test_export_goes_to_study_and_run(tmp_path, monkeypatch):
    from iomcfd import runner

    project, study, cases = _smoke()
    seen = []
    monkeypatch.setattr(runner, "run_case", lambda p, c, d, o, export_dir=None: seen.append(export_dir) or
                        {"case": c.name, "status": "ok"})
    rdir = tmp_path / "local" / study.name / "20261012-045433"
    run_study(project, study, cases[:1], RunOptions(export=tmp_path / "bucket"), rdir, log=lambda *a: None)
    assert seen == [tmp_path / "bucket" / study.name / "20261012-045433"]


def test_gcp_job_writes_into_its_run():
    from iomcfd.cloud import gcp

    cfg = {"GCP_PROJECT": "p", "GCP_REGION": "us-central1", "GCS_BUCKET": "b", "AR_REPO": "r", "BATCH_SA": "sa@x",
           "IMAGE_NAME": "iom-cfd", "IMAGE_TAG": "latest"}
    job = gcp.build_job(cfg, "fin-profile-selection", 450, 1, "c3d-standard-16", True, 4, 32, [], None,
                        "20261012-045433")
    cmd = job["taskGroups"][0]["taskSpec"]["runnables"][0]["container"]["commands"]
    assert cmd[cmd.index("--run-id") + 1] == "20261012-045433"
    assert cmd[cmd.index("run") + 1] == f"{gcp.MOUNT}/runs/fin-profile-selection/20261012-045433/study.yaml"
    assert job["labels"]["run"] == "20261012-045433"
    assert "--no-fields" not in cmd  # final fields go to the bucket: `gcp fetch --fields` + `iomcfd viz` need them
    name = gcp.job_name("a-very-long-study-name-that-goes-on-and-on-and-on", "20261012-045433")
    assert len(name) <= 63 and name.endswith("-20261012-045433")


@pytest.mark.parametrize("path, field", [
    ("aoa4/1500/U", True), ("aoa4/0/U", True), ("aoa4/0.05/U", True), ("aoa4/1e-05/p", True),
    ("aoa4/postProcessing/forces/0/force.dat", False), ("aoa4/constant/polyMesh/points", False),
    ("aoa4/result.json", False), ("study.yaml", False), ("aoa4_chord0.08_foilnaca0007_speed1/log.simpleFoam", False),
])
def test_fetch_skips_only_field_directories(path, field):
    import re

    from iomcfd.cloud import gcp

    assert bool(re.fullmatch(gcp.FIELD_DIRS, path)) is field  # gcloud matches the whole relative path
