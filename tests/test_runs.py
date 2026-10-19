"""Timestamped runs: every `iomcfd run` writes runs/<study>/<run id>/; nothing
is overwritten; --resume and --run-id continue a run (no OpenFOAM)."""

import argparse
import datetime as dt
import json
from pathlib import Path

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
    monkeypatch.setattr(runner, "run_case", lambda p, c, d, o, export_dir=None, log=None, checkpoint_dir=None:
                        seen.append((export_dir, checkpoint_dir)) or {"case": c.name, "status": "ok"})
    rdir = tmp_path / "local" / study.name / "20261012-045433"
    run_study(project, study, cases[:1], RunOptions(export=tmp_path / "bucket", checkpoint=tmp_path / "ck"), rdir,
              log=lambda *a: None)
    assert seen == [(tmp_path / "bucket" / study.name / "20261012-045433",
                     tmp_path / "ck" / study.name / "20261012-045433")]


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
    no_retry = job["taskGroups"][0]["taskSpec"]["lifecyclePolicies"][0]
    assert no_retry["action"] == "FAIL_TASK" and 50005 in no_retry["actionCondition"]["exitCodes"]  # time limit
    nic = job["allocationPolicy"]["network"]["networkInterfaces"][0]
    assert nic["noExternalIpAddress"] and nic["subnetwork"].startswith("regions/us-central1/")  # IP quota is 8
    name =gcp.job_name("a-very-long-study-name-that-goes-on-and-on-and-on", "20261012-045433")
    assert len(name) <= 63 and name.endswith("-20261012-045433")


def test_gcp_task_hours_fit_the_longest_case():
    """stepped-vs-naca starts with plain NACA 0009; its stair10 cases need far
    longer, and every task of a job gets one limit."""
    from iomcfd.cloud import gcp

    project = load_project("foil2d")
    study = Study.load(config.projects_dir() / "foil2d" / "studies" / "stepped-vs-naca.yaml")
    cases = study.expand(project.defaults)
    first = float(project.resources({**cases[0].params, "np": 1})["max_hours"])
    hours = gcp.task_hours(project, cases, 1)
    assert hours == pytest.approx(1 + 2 * 4.0)
    assert hours > 2 * first


def test_transient_hours():
    """A transient case's limit covers its time steps: a stair1 step at maxCo 5
    takes ~5x NACA 0009's steps per c/U, and twice as many at half the Co;
    on one rank ~2.7x longer than on 4."""
    project = load_project("foil2d")
    p = {**project.defaults, "solver": "transient", "mesh": "medium", "np": 4}
    naca = project.resources({**p, "foil": "naca0009"})["max_hours"]
    stair1 = project.resources({**p, "foil": "stair1:naca0009:x=0.5,d=0.3", "max_co": 5})["max_hours"]
    assert naca == pytest.approx(1 + 2 + 2)
    assert stair1 == pytest.approx(1 + 2 * 2.0 + 2 * 5.0 * 2)
    assert project.resources({**p, "foil": "naca0009", "solver": "steady"})["max_hours"] == pytest.approx(3)
    one = project.resources({**p, "foil": "naca0009", "np": 1})["max_hours"]
    assert one == pytest.approx(1 + 2 + 2 * 4**0.72) and one > 3.5 + 2  # transient-check's ~3.5 h estimate


@pytest.mark.parametrize("path, kept", [
    ("study.yaml", True), ("run.json", True), ("report/summary.md", True), ("viz/index.html", True),
    ("aoa4/result.json", True), ("aoa4/params.json", True), ("aoa4/surface.csv", True), ("aoa4/viz/velocity.png", True),
    ("aoa4/1500/U", False), ("aoa4/constant/polyMesh/points.gz", False), ("aoa4/log.simpleFoam.gz", False),
    ("aoa4/postProcessing/forceCoeffs/0/coefficient.dat", False), ("aoa4/system/controlDict", False),
    ("aoa0/constant/polyMesh/faces.gz", True), ("aoa0/log.checkMesh.gz", True), ("aoa0/log.simpleFoam", False),
    ("aoa8/log.simpleFoam.gz", True), ("aoa8/1500/U", False), ("aoa2/1500/U", True), ("aoa2/system/controlDict", True),
    ("aoa2x/1500/U", False),
])
def test_fetch_downloads_results_and_only_the_extras_asked_for(path, kept):
    import re

    from iomcfd.cloud import gcp

    pat = gcp.exclude_pattern(gcp.keep_pattern(full=["aoa2"], mesh=["aoa0"], logs=["aoa8"]))
    assert not pat.startswith("^") and "," not in pat  # gcloud list-flag escapes
    assert (re.match(pat, path) is None) is kept  # gcloud: re.match on the source-relative path


def _fake_bucket(tmp_path, rid="20261012-045433"):
    """A finished foil2d smoke run as `gcp submit` + the tasks leave it in the bucket."""
    from iomcfd.runner import export_case

    project, study, cases = _smoke()
    work = tmp_path / "work" / study.name / rid
    run_study(project, study, cases, RunOptions(render_only=True), work, log=lambda *a: None)
    bucket = tmp_path / "bucket" / "runs" / study.name / rid
    for i, c in enumerate(cases):
        d = work / c.name
        (d / "log.simpleFoam").write_text("Time = 1\n" * 1000)
        (d / "log.checkMesh").write_text("    cells:            22528\nMesh OK.\n")
        (d / "300").mkdir()
        (d / "300" / "U").write_text("field")
        (d / "surface.csv").write_text("upper,x_c,y_c,Cp,Cf\n")
        (d / "result.json").write_text(json.dumps({"status": "ok" if i == 0 else "not_converged", "metrics": {}}))
        export_case(d, bucket / c.name, keep_fields=True)
    for f in ("study.yaml", "run.json"):
        (bucket / f).write_bytes((work / f).read_bytes())
    return study, cases, tmp_path / "bucket"


def test_fetch_light_then_fields(tmp_path, monkeypatch):
    import re
    import shutil

    from iomcfd.cloud import gcp

    study, cases, bucket = _fake_bucket(tmp_path)
    calls = []

    def fake_gcloud(*args, capture=False, dry=False):
        calls.append(args)
        if args[:2] == ("storage", "ls"):
            return "\n".join(f"gs://b/runs/{study.name}/{d.name}/" for d in (bucket / "runs" / study.name).iterdir())
        assert args[:3] == ("storage", "rsync", "-r") and args[3] == "--exclude"
        src = bucket / args[5].removeprefix("gs://b/")
        for f in src.rglob("*"):
            rel = f.relative_to(src).as_posix()
            if f.is_file() and not re.match(args[4], rel):
                (Path(args[6]) / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, Path(args[6]) / rel)
        return ""

    monkeypatch.setattr(gcp, "_gcloud", fake_gcloud)
    monkeypatch.setattr(gcp, "load_config", lambda: {"GCS_BUCKET": "b"})
    runs = tmp_path / "local"
    ns = lambda **kw: argparse.Namespace(**{"study": "foil2d/smoke", "runs": str(runs), "run_id": None,  # noqa: E731
                                            "logs": False, "fields": False, "only": None, **kw})
    gcp.cmd_fetch(ns())
    rdir = runs / study.name / "20261012-045433"
    first, second = cases[0].name, cases[1].name
    assert (rdir / "results.csv").is_file() and (rdir / second / "result.json").is_file()
    assert (rdir / first / "constant" / "polyMesh" / "points.gz").is_file()  # mesh figure (the ok case)
    assert (rdir / first / "log.checkMesh.gz").is_file()
    assert not (rdir / second / "constant").exists() and not list(rdir.glob("*/log.simpleFoam*"))
    assert not list(rdir.glob("*/300"))
    gcp.cmd_fetch(ns(logs=True))
    assert (rdir / second / "log.simpleFoam.gz").is_file() and not (rdir / first / "log.simpleFoam.gz").exists()
    gcp.cmd_fetch(ns(only=[second]))
    assert (rdir / second / "300" / "U").is_file() and not (rdir / first / "300").exists()
    gcp.cmd_fetch(ns(fields=True))  # no highlights in the smoke study: every case
    assert (rdir / first / "300" / "U").is_file()


def test_export_gzips_mesh_and_logs(tmp_path):
    import gzip

    from iomcfd.foam import read_text, tail_log
    from iomcfd.meshplot import checkmesh_stats, has_mesh
    from iomcfd.polymesh import read as read_mesh

    _, cases, bucket = _fake_bucket(tmp_path)
    case = next(bucket.glob("runs/*/*")) / cases[0].name
    assert has_mesh(case) and not (case / "constant" / "polyMesh" / "points").exists()
    assert (case / "log.simpleFoam.gz").is_file() and not (case / "log.simpleFoam").exists()
    assert (case / "300" / "U").read_text() == "field" and (case / "params.json").is_file()  # fields as they are
    assert gzip.decompress((case / "log.checkMesh.gz").read_bytes()).startswith(b"    cells:")
    assert "Mesh OK." in read_text(case / "log.checkMesh") and tail_log(case / "log.simpleFoam", 1) == "Time = 1"
    assert checkmesh_stats(case)["cells"] == "22528"
    assert read_mesh(case / "constant" / "polyMesh").n_faces > 0


def test_slim_keeps_results_images_and_one_mesh(tmp_path):
    from iomcfd.runner import slim_run

    _, cases, bucket = _fake_bucket(tmp_path)
    rdir = next(bucket.glob("runs/*/*"))
    (rdir / cases[1].name / "viz").mkdir()
    (rdir / cases[1].name / "viz" / "velocity.png").write_bytes(b"png")
    before = sorted(p for p in rdir.rglob("*") if p.is_file())
    n, size = slim_run(rdir, {cases[0].name}, dry_run=True)
    assert n > 0 and size > 0 and sorted(p for p in rdir.rglob("*") if p.is_file()) == before
    assert slim_run(rdir, {cases[0].name}) == (n, size)
    left = sorted(p.relative_to(rdir).as_posix() for p in rdir.rglob("*") if p.is_file())
    a, b = cases[0].name, cases[1].name
    assert f"{b}/viz/velocity.png" in left and f"{b}/result.json" in left and "study.yaml" in left
    assert f"{a}/constant/polyMesh/points.gz" in left and f"{a}/log.checkMesh.gz" in left
    assert not any(x.startswith(f"{b}/constant") or "/300/" in x or "log.simpleFoam" in x for x in left)
    assert not (rdir / b / "system").exists()  # empty directories go too
    assert slim_run(rdir, {a}) == (0, 0)


def test_mesh_candidates_one_per_level_finished_first():
    from iomcfd.meshplot import mesh_candidates

    rows = [{"case": "a", "status": "failed", "mesh": "coarse"}, {"case": "b", "status": "ok", "mesh": "coarse"},
            {"case": "c", "status": "ok", "mesh": "medium"}]
    assert mesh_candidates(rows) == [["b", "a"], ["c"]]
    assert mesh_candidates([{"case": "x", "status": "ok"}]) == [["x"]]


def test_cli_parser_builds_with_every_help_string():
    # argparse (Python >= 3.14) checks help strings when a parser is added:
    # a bare % breaks every command, not just its own.
    parser = cli.build_parser()
    for args in (["gcp", "-h"], ["gcp", "progress", "-h"], ["run", "-h"]):
        with pytest.raises(SystemExit) as e:
            parser.parse_args(args)
        assert e.value.code == 0
