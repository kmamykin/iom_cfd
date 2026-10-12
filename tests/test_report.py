"""foil2d report figures from a synthetic results table (no OpenFOAM)."""

import itertools

import pytest

from iomcfd.project import load_project

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")


def _results(foils, chords, speeds, models, tus=(0.1,)):
    rows = []
    for foil, chord, speed, model, tu, aoa in itertools.product(foils, chords, speeds, models, tus, [0, 2, 4, 6, 8]):
        t = int(foil[-2:]) / 100
        cl = 0.1 * aoa * (1 - t)
        cd = 0.008 + 0.05 * t + 0.0005 * aoa**2 + (0.002 if model == "kOmegaSST" else 0.0)
        q = 0.5 * 998.0 * speed**2
        rows.append({"status": "ok", "foil": foil, "chord": chord, "speed": speed, "Re": speed * chord / 1.14e-6,
                     "Tu": tu, "turbulence": model, "rhoInf": 998.0, "magUInf": speed, "mesh": "coarse", "aoa": aoa, "Cl": cl, "Cd": cd,
                     "L_D": cl / cd, "lift_N_per_m": q * chord * cl, "drag_N_per_m": q * chord * cd,
                     "unsteady": aoa == 4})
    return pd.DataFrame(rows)


def test_selection_figure_for_section_and_chord_sweep(tmp_path):
    df = _results(["naca0006", "naca0009", "naca0012"], [0.08, 0.10], [0.5, 1.0, 1.5, 2.5],
                  ["kOmegaSSTLM", "kOmegaSST"])
    files = load_project("foil2d").report(df, tmp_path)
    names = {f.name for f in files}
    assert {"polar.png", "selection.png"} <= names
    assert (tmp_path / "selection.png").stat().st_size > 50_000


def test_no_selection_figure_for_a_single_section(tmp_path):
    df = _results(["naca0009"], [0.08], [1.0], ["kOmegaSSTLM", "kOmegaSST"])
    names = {f.name for f in load_project("foil2d").report(df, tmp_path)}
    assert names == {"polar.png"}


def test_selection_rows_follow_tu_sweep(tmp_path):
    df = _results(["naca0006", "naca0012"], [0.08], [0.5, 1.0], ["kOmegaSSTLM"], tus=(0.1, 1.0))
    names = {f.name for f in load_project("foil2d").report(df, tmp_path)}
    assert "selection.png" in names


def test_selection_whole_fin_with_induced_drag(tmp_path):
    from iomcfd.physics import induced_drag

    df = _results(["naca0006", "naca0009"], [0.08, 0.10], [1.0], ["kOmegaSSTLM"])
    opts = {"fin_span": 0.36, "induced_drag": True}
    names = {f.name for f in load_project("foil2d").report(df, tmp_path, options=opts)}
    assert {"selection.png", "selection.csv"} <= names
    sel = pd.read_csv(tmp_path / "selection.csv")
    row = sel[(sel.foil == "naca0009") & (sel.chord == 0.08) & (sel.aoa == 4)].iloc[0]
    src = df[(df.foil == "naca0009") & (df.chord == 0.08) & (df.aoa == 4)].iloc[0]
    assert row.side_force == pytest.approx(src.lift_N_per_m * 0.36)
    di = induced_drag(row.side_force, 0.5 * 998.0 * 1.0**2, 0.36, 0.9)
    assert row.drag_induced == pytest.approx(di)
    assert row.drag == pytest.approx(src.drag_N_per_m * 0.36 + di)


def test_induced_drag_needs_span(tmp_path):
    df = _results(["naca0006", "naca0009"], [0.08], [1.0], ["kOmegaSSTLM"])
    with pytest.raises(ValueError, match="fin_span"):
        load_project("foil2d").report(df, tmp_path, options={"induced_drag": True})


def test_compare_at_equal_side_force(tmp_path):
    df = _results(["naca0006", "naca0009", "naca0012"], [0.08, 0.10], [1.0], ["kOmegaSSTLM"])
    # low-Re lift reversal of the thick section near 0 deg: must not hide the rest of its polar
    rev = (df.foil == "naca0012") & (df.chord == 0.08) & (df.aoa == 2)
    df.loc[rev, "lift_N_per_m"] = -0.05
    opts = {"fin_span": 0.36, "compare_at": {"foil": "naca0009", "chord": 0.08, "aoa": [2, 4, 6]}}
    names = {f.name for f in load_project("foil2d").report(df, tmp_path, options=opts)}
    assert {"selection_compare.csv", "selection_compare.md"} <= names
    cmp = pd.read_csv(tmp_path / "selection_compare.csv")
    assert set(cmp.ref_aoa) == {2, 4, 6} and len(cmp) == 3 * 6
    ref = cmp[(cmp.foil == "naca0009") & (cmp.chord == 0.08) & (cmp.ref_aoa == 4)].iloc[0]
    src = df[(df.foil == "naca0009") & (df.chord == 0.08) & (df.aoa == 4)].iloc[0]
    assert ref.drag == pytest.approx(src.drag_N_per_m * 0.36)  # the reference sits on its own point
    assert (cmp.groupby("ref_aoa")["above_best_pct"].min().abs() < 1e-9).all()  # one best per force
    thick = cmp[(cmp.foil == "naca0012") & (cmp.chord == 0.08) & (cmp.ref_aoa == 4)].iloc[0]
    assert pd.notna(thick.drag)
    md = (tmp_path / "selection_compare.md").read_text()
    assert "**best**" in md and "| 0009/80 |" in md
