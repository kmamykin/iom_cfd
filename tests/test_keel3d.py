"""keel3d: keel sizing from the IOM rules and the equal-side-force comparison."""

import math

import pandas as pd
import pytest

from iomcfd.project import load_project


@pytest.fixture(scope="module")
def project():
    return load_project("keel3d")


def test_keel_sized_by_the_rules(project):
    d = project.derive(dict(project.defaults))
    assert d["bulb_mass_kg"] == pytest.approx(2.38)
    assert d["bulb_z_axis"] - d["bulb_diameter"] / 2 == pytest.approx(-0.42)  # bulb bottom at the draft limit
    assert d["fin_z_root"] - d["fin_span"] == pytest.approx(d["bulb_z_axis"] + d["bulb_diameter"] / 2)
    assert d["displacement_kg"] == pytest.approx(4.0, abs=0.05)
    assert d["fin_root_thickness"] <= 0.020


def test_equal_area_across_tapers(project):
    areas = {t: project.derive({**project.defaults, "fin_taper": t})["fin_area_m2"] for t in (1.0, 0.6, 0.4)}
    assert max(areas.values()) == pytest.approx(min(areas.values()))


def test_rule_checks(project):
    with pytest.raises(ValueError, match="E.4.1"):
        project.derive({**project.defaults, "fin_mean_chord": 0.25, "fin_taper": 0.4})  # 25 mm thick root
    with pytest.raises(ValueError, match="E.4.1"):
        project.derive({**project.defaults, "bulb_section": "naca0050"})  # 62 mm bulb


def _sweep(taper, side_slope, k, d0=0.6):
    rows = []
    for b in (0, 2, 4, 6, 8):
        F = side_slope * b
        rows.append({"status": "ok", "fin_taper": taper, "leeway": b, "side_N": F, "drag_N": d0 + k * F**2,
                     "speed": 1.0, "dynamicPressure": 499.6, "draft": 0.42})
    return rows


def test_compare_at_equal_force(project):
    # taper 0.6: same lift slope, less induced drag; taper 0.4: more lift per degree, same drag polar
    df = pd.DataFrame(_sweep(1.0, 1.5, 0.010) + _sweep(0.6, 1.5, 0.009) + _sweep(0.4, 1.6, 0.010))
    t = project.compare_at_equal_force(df, {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4, 6]}})
    w = t[t["load"] == "working"].set_index("fin_taper")
    assert w.loc[1.0, "side_N"] == pytest.approx(6.0)
    assert w.loc[1.0, "leeway"] == pytest.approx(4.0)
    assert w.loc[0.4, "leeway"] == pytest.approx(6.0 / 1.6)
    assert w.loc[0.6, "drag_N"] == pytest.approx(0.6 + 0.009 * 36, rel=1e-3)
    assert w.loc[0.4, "drag_N"] == pytest.approx(0.6 + 0.010 * 36, rel=1e-9)  # between computed points
    # 0.6 has the least drag, 0.4 the least leeway; drag at 0 deg is equal
    drag = 50 * 0.036 / 1.354  # % of race time: half the race upwind
    leeway = 50 * math.tan(math.radians(42)) * math.radians(0.25)
    assert w.loc[0.6, "loss_x1_pct"] == 0.0
    assert w.loc[1.0, "loss_x1_pct"] == pytest.approx(drag, rel=1e-6)
    assert w.loc[0.4, "loss_x1_pct"] == pytest.approx(drag - leeway, rel=1e-6)
    assert w.loc[1.0, "loss_x2_pct"] == pytest.approx(drag / 2, rel=1e-6)
    fits = project.polar_fits(df).set_index("fin_taper")
    assert fits.loc[0.6, "k_per_N"] == pytest.approx(0.009)
    assert fits.loc[1.0, "side_per_deg_N"] == pytest.approx(1.5)
