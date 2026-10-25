"""Highlights: the cases a study names for a close look (report figures,
viz montages, fields fetched only for these). No OpenFOAM or ParaView."""

import json

import pytest

from iomcfd import config, highlights as hl
from iomcfd.project import load_project
from iomcfd.study import Case, Study


def _cases(rows):
    return [Case(name="_".join(f"{k}{v}" for k, v in r.items()), index=i, params=dict(r, Tu=1.0), varied=dict(r))
            for i, r in enumerate(rows)]


CASES = _cases([{"aoa": a, "chord": c, "foil": f, "speed": s}
                for f in ("naca0009", "naca0006", "naca0012") for c in (0.08, 0.1) for s in (0.5, 1.0) for a in (4, 6)])


def test_parse_validates():
    h = hl.parse([{"name": "a-1", "where": {"aoa": 4}, "views": "velocity"}])[0]
    assert h.views == ["velocity"] and h.compare is None
    for bad in ([{"where": {}}], [{"name": "a b"}], [{"name": "a"}, {"name": "a"}], [{"name": "a", "wehre": {}}]):
        with pytest.raises(ValueError):
            hl.parse(bad)


def test_select_matches_values_lists_and_fixed_parameters():
    h = hl.Highlight("x", where={"speed": 1, "chord": 0.080, "aoa": [4, 6], "Tu": 1})
    sel = hl.select(h, CASES)
    assert len(sel) == 6 and all(c.params["speed"] == 1.0 and c.params["chord"] == 0.08 for c in sel)
    assert hl.select(hl.Highlight("y", where={"foil": "naca0010"}), CASES) == []
    with pytest.raises(ValueError):
        hl.select(hl.Highlight("z", where={"speeed": 1}), CASES)


def test_layout_columns_follow_compare_rows_the_rest():
    h = hl.Highlight("x", where={"speed": 1.0, "chord": 0.08}, compare="foil")
    lay = hl.layout(h, hl.select(h, CASES))
    assert lay.columns == ["naca0009", "naca0006", "naca0012"]  # words: study order
    assert [label for label, _ in lay.rows] == ["aoa 4", "aoa 6"] and lay.row_keys == ["aoa"]
    assert lay.rows[1][1]["naca0006"].params["aoa"] == 6 and len(lay.cases) == 6
    auto = hl.layout(hl.Highlight("y", where={"foil": "naca0009", "aoa": 6}), hl.select(
        hl.Highlight("y", where={"foil": "naca0009", "aoa": 6}), CASES))
    assert auto.compare == "chord" and auto.columns == [0.08, 0.1] and auto.row_keys == ["speed"]  # tie: first
    one = hl.layout(hl.Highlight("z"), CASES[:1])
    assert one.compare is None and len(one.cases) == 1
    # a list-valued parameter that differs between cases (start_from) still makes rows
    mixed = _cases([{"foil": f, "start_from": s} for f, s in (("a", ["run/1"]), ("b", ["run/1"]), ("b", ["x"]))])
    lay = hl.layout(hl.Highlight("w", compare="foil"), mixed)
    assert [label for label, _ in lay.rows] == ["start_from run/1", "start_from x"]


def test_plan_skips_what_does_not_fit_this_run():
    msgs = []
    planned = hl.plan([hl.Highlight("ok", where={"aoa": 4}), hl.Highlight("typo", where={"aoaa": 4}),
                       hl.Highlight("none", where={"foil": "naca0010"})], CASES, msgs.append)
    assert [h.name for h, _ in planned] == ["ok"] and len(msgs) == 2
    assert len(hl.case_names(planned * 2)) == 12  # each case once


@pytest.mark.parametrize("name, sizes, unique", [
    ("fin-profile-selection", {"thin-at-working-load": (4, "chord", 2), "thickness-at-100mm": (4, "foil", 2),
                               "light-air": (4, "foil", 2)}, 11),  # 0007/100, 1 m/s, 6 deg twice
    ("mesh-finalists", {"bubble-by-mesh": (12, "mesh", 4)}, 12),
])
def test_study_highlights_select_the_intended_cases(name, sizes, unique):
    project = load_project("foil2d")
    study = Study.load(config.projects_dir() / "foil2d" / "studies" / f"{name}.yaml")
    planned = hl.plan(study.highlights, study.expand(project.defaults), lambda m: pytest.fail(m))
    assert {h.name: (len(lay.cases), lay.compare, len(lay.rows)) for h, lay in planned} == sizes
    assert len(hl.case_names(planned)) == unique


def test_current_study_file_wins(tmp_path):
    def study(name, extra):
        f = tmp_path / name
        f.write_text("study: s\nproject: foil2d\nsweep: {aoa: [0, 4]}\n" + extra)
        return Study.load(f)

    snap = study("snap.yaml", "highlights: [{name: old, where: {aoa: 0}}]\n")
    cur = study("cur.yaml", "highlights: [{name: new, where: {aoa: 4}}]\n")
    assert [h.name for h in hl.resolve(cur, snap)[0]] == ["new"]
    assert [h.name for h in hl.resolve(study("bare.yaml", ""), snap)[0]] == ["old"]
    with pytest.raises(ValueError):
        study("bad.yaml", "highlights: [{name: 'a b'}]\n")


def test_views_per_case():
    from iomcfd.viz.study import views_per_case

    planned = hl.plan([hl.Highlight("a", where={"aoa": 4}, views=["separation"]),
                       hl.Highlight("b", where={"aoa": 4, "speed": 1.0}, views=["velocity", "separation"])], CASES)
    v = views_per_case(CASES, planned, ["pressure"], None)
    c4_slow = next(c for c in CASES if c.params["aoa"] == 4 and c.params["speed"] == 0.5)
    c4_fast = next(c for c in CASES if c.params["aoa"] == 4 and c.params["speed"] == 1.0)
    c6 = next(c for c in CASES if c.params["aoa"] == 6)
    assert v[c4_slow.name] == ["separation"] and v[c4_fast.name] == ["separation", "velocity"]
    assert v[c6.name] == ["pressure"]  # not highlighted (e.g. --only): defaults
    assert views_per_case(CASES, planned, ["pressure"], ["eddy_viscosity"])[c4_fast.name] == ["eddy_viscosity"]


def _png(path, w=80, h=40, value=0.5):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(path, np.full((h, w, 3), value))


def test_montages_and_gallery(tmp_path):
    from iomcfd.viz import study as vstudy

    class S:
        name, description = "demo", "a study"

    h = hl.Highlight("thick", why="does the bubble grow?", where={"speed": 1.0, "chord": 0.08}, compare="foil",
                     views=["separation"])
    planned = hl.plan([h], CASES)
    for c in planned[0][1].cases[:-1]:  # one case not rendered: an empty panel
        _png(tmp_path / c.name / "viz" / "separation.png")
    made = vstudy.highlight_montages(S, tmp_path, planned, ["velocity", "separation"], log=lambda *a: None)
    assert made[0]["files"] == ["thick_separation.png"]
    assert (tmp_path / "viz" / "highlights" / "thick_separation.png").stat().st_size > 1000
    md = (tmp_path / "viz" / "highlights.md").read_text()
    assert "does the bubble grow?" in md and "viz/highlights/thick_separation.png" in md
    index = vstudy.write_gallery(S, tmp_path, [], ["separation"], [], made)
    assert "highlights/thick_separation.png" in index.read_text()


def test_highlight_table_and_surface_figure(tmp_path):
    import pandas as pd

    project = load_project("foil2d")
    h = hl.Highlight("thick", why="why", where={"speed": 1.0, "chord": 0.08}, compare="foil")
    planned = hl.plan([h], CASES)
    rows = []
    for c in planned[0][1].cases:
        (tmp_path / c.name).mkdir()
        (tmp_path / c.name / "surface.csv").write_text(
            "upper,x_c,y_c,Cp,Cf\n" + "".join(f"{u},{x},0,{-1 + x},{0.01 - 0.02 * (0.2 < x < 0.4)}\n"
                                               for u in ("True", "False") for x in (0.0, 0.1, 0.3, 0.5, 1.0)))
        rows.append({"case": c.name, "status": "ok", "Cl": 0.5, "Cd": 0.02, "x_sep_upper": 0.2, "unsteady": False})
    files = project.highlight_report(tmp_path, pd.DataFrame(rows), planned, tmp_path)
    assert [f.name for f in files] == ["highlights.md", "highlight_thick.png"]
    md = files[0].read_text()
    assert "### thick" in md and "| aoa | foil | status | Cl | Cd |" in md and "| 4 | naca0009 | ok | 0.5 | 0.02 |" in md
    assert files[1].stat().st_size > 10_000
