"""report.html: a run folder's CSVs, run.json and boat.yaml embedded in one
page as written (vpp/report.py), and what `vpp run` records for it."""

import argparse
import csv
import io
import json
import re
from types import SimpleNamespace

import yaml

from iomcfd.vpp import cli, report
from iomcfd.vpp.boat import BoatSpec
from iomcfd.vpp.race import Course, WindRange
from test_vpp_solver import toy_boat

BLOCK = re.compile(r'<script type="([^"]+)" data-file="([^"]+)">(.*?)</script>', re.S)


def _text(path):
    with open(path, newline="") as f:
        return f.read()


def _blocks(html: str) -> dict:
    """{file: (type, text)} of the page's data blocks, unescaped as the page does."""
    return {m[2]: (m[1], m[3].replace("<\\/", "</")) for m in BLOCK.finditer(html)}


def _run(d, polar=True, rates=True):
    pts = [{"tws": 3.0, "twa": a, "V": 1.0, "heel": 20.0, "converged": True, "X_sails": 1.5, "sails_CL": 1.1,
            "sails_CD": 0.1, "sails_aws": 3.2, "X_hull": -1.5, "flags": ""} for a in (45.0, 90.0)]
    if polar:
        report.write_csv(d / "polar.csv", pts)
    report.write_csv(d / "vmg.csv", [pts[0] | {"leg": "up"}])
    report.write_csv(d / "race.csv", [{"tws": 3.0, "weight": 1.0, "t_s": 450.0, "flags_up": "extrapolated"}])
    report.write_csv(d / "mass.csv", [{"name": "rig A: mast, booms", "m": 0.22, "x": 0.4, "y": 0.0, "z": 0.5}])
    report.write_csv(d / "particulars.csv", [{"condition": "floating", "sink": -0.002, "trim": 0.4, "cb": 0.42,
                                               "gm_t": 0.21, "converged": 1.0}])
    if rates:
        report.write_csv(d / "rates.csv", [{"name": "fixed drag +0.01 N", "tws": 3.0, "dt": 1.2, "dt_pct": 0.27}])
        report.write_csv(d / "rates_summary.csv", [{"name": "fixed drag +0.01 N", "dt_pct": 0.27, "boat_lengths": 1.1}])
    (d / "run.json").write_text(json.dumps({"boat": "toy", "info": {}, "course": {"leg": 100.0, "laps": 2}}))
    (d / "boat.yaml").write_text("boat: toy\ndescription: a </script> in the text\ncomponents: {}\n")
    return d


def test_report_embeds_the_files_as_written(tmp_path):
    d = _run(tmp_path)
    html = _text(report.html_report(d))
    assert "__DATA__" not in html and "__TITLE__" not in html and "<title>toy · VPP run" in html
    b = _blocks(html)
    assert set(b) == {"polar.csv", "vmg.csv", "race.csv", "rates.csv", "rates_summary.csv", "mass.csv",
                      "particulars.csv", "run.json", "boat.json", "boat.yaml"}
    for f in ("race.csv", "mass.csv", "particulars.csv", "rates.csv", "rates_summary.csv"):
        assert b[f] == ("text/csv", _text(d / f))
    # the ORC coefficients are dropped, every other cell kept as written
    for f in ("polar.csv", "vmg.csv"):
        got = list(csv.DictReader(io.StringIO(b[f][1])))
        want = [{k: v for k, v in r.items() if k not in ("sails_CL", "sails_CD")} for r in csv.DictReader(io.StringIO(_text(d / f)))]
        assert got == want and "sails_aws" in got[0]
    assert not any("_CL" in t or "_CD" in t for _, t in b.values())
    assert json.loads(b["run.json"][1]) == json.loads((d / "run.json").read_text())
    assert json.loads(b["boat.json"][1]) == yaml.safe_load((d / "boat.yaml").read_text())
    assert b["boat.yaml"][1] == _text(d / "boat.yaml")  # "</script>" in it survives the escaping
    # regenerating gives the same page
    assert _text(report.html_report(d)) == html


def test_report_without_polar_or_rates(tmp_path):
    b = _blocks(_text(report.html_report(_run(tmp_path, polar=False, rates=False))))
    assert "polar.csv" not in b and "rates.csv" not in b and "vmg.csv" in b


def test_vpp_report_reads_the_latest_run(tmp_path):
    runs = tmp_path / "runs"
    for rid in ("20261027-120000", "20261027-130000"):
        (runs / "vpp" / "toy" / rid).mkdir(parents=True)
        _run(runs / "vpp" / "toy" / rid)
    cli.cmd_report(argparse.Namespace(run="toy", run_id=None, runs=str(runs)))
    assert (runs / "vpp" / "toy" / "20261027-130000" / "report.html").is_file()
    assert not (runs / "vpp" / "toy" / "20261027-120000" / "report.html").exists()
    cli.cmd_report(argparse.Namespace(run="toy", run_id="20261027-120000", runs=str(runs)))
    assert (runs / "vpp" / "toy" / "20261027-120000" / "report.html").is_file()
    cli.cmd_report(argparse.Namespace(run=str(runs / "vpp" / "toy" / "20261027-120000"), run_id=None, runs=None))


def test_run_info_records_what_the_build_resolved(tmp_path):
    f = tmp_path / "toy.yaml"
    f.write_text("boat: toy\nmass: {extra: 0.0}\n")
    spec = BoatSpec.load(f, {"mass.extra": 0.01, "course.leg": 80.0})
    b = SimpleNamespace(spec=spec, boat=toy_boat(yaw=True), wind=WindRange([2.0, 3.0]), course=Course(leg=80.0),
                        info={"mass_kg": 4.0}, warnings=[])
    info = cli._run_info(argparse.Namespace(set=["mass.extra=0.01", "course.leg=80.0"]), b, {"build_s": 1.0})
    json.dumps(info, allow_nan=False)  # infinite control bounds are written as null
    assert info["file_values"] == {"mass.extra": 0.0, "course.leg": None}
    assert info["course"]["leg"] == 80.0 and info["course"]["tacks_per_leg"] == 4.0
    assert info["wind"]["weights"] == [1.0, 1.0]
    rudder = next(p for p in info["parts"] if p["name"] == "rudder")
    assert rudder["controls"] == [{"name": "angle", "role": "balance", "default": 0.0, "lo": None, "hi": None,
                                   "options": [], "key": "rudder.angle"}]
    assert rudder["shape"] is None and rudder["forces"].endswith("ToyRudder")
