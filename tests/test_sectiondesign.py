import math

import numpy as np
import pandas as pd
import pytest

from iomcfd import racetime, sectiondesign, xfoil
from iomcfd.geometry import foils


# --- modified NACA 4-digit ------------------------------------------------------


@pytest.mark.parametrize("code,t,xt", [("0007-74", 0.07, 0.40), ("0008-34", 0.08, 0.40), ("0006-45", 0.06, 0.50),
                                       ("0012-63", 0.12, 0.30), ("0007-92", 0.07, 0.20)])
def test_modified4_thickness_and_position(code, t, xt):
    tt, xx = foils.naca4_modified(code).thickness()
    assert tt == pytest.approx(t, abs=2e-4)
    assert xx == pytest.approx(xt, abs=0.01)


@pytest.mark.parametrize("i_le,factor", [(6, 1.0), (3, 0.25), (9, 3.0)])
def test_modified4_leading_edge_radius(i_le, factor):
    p = sectiondesign.properties(foils.load(f"naca0010-{i_le}4"))
    assert p["r_le"] == pytest.approx(1.1019 * 0.10**2 * factor, rel=0.03)


def test_modified4_close_to_standard_4digit():
    # NACA: 0012-63 is approximately the standard 0012
    up = foils.load("naca0012-63").surface("upper", 400)
    ref = foils.load("naca0012").surface("upper", 400)
    xs = np.linspace(0.01, 0.99, 50)
    assert np.max(np.abs(np.interp(xs, *up.T) - np.interp(xs, *ref.T))) < 0.0015


def test_modified4_rejects_camber():
    with pytest.raises(ValueError):
        foils.naca4_modified("2412-63")


# --- CST, properties, stiffness ------------------------------------------------------


def test_cst_nose_and_trailing_edge():
    f = sectiondesign.cst_symmetric([0.12, 0.1, 0.1, 0.1, 0.1, 0.06])
    p = sectiondesign.properties(f)
    assert p["r_le"] == pytest.approx(0.12**2 / 2, rel=0.03)
    assert p["te_angle"] == pytest.approx(2 * math.degrees(math.atan(0.06)), abs=0.3)


def test_cst_fit_roundtrip():
    f = foils.load("naca0009")
    g = sectiondesign.cst_symmetric(sectiondesign.cst_coeffs(f, 7))
    assert g.thickness()[0] == pytest.approx(0.09, abs=3e-4)


def test_scaled_and_stiffness_matched():
    ref = sectiondesign.properties(foils.load("naca0007"))
    thin = sectiondesign.scaled(foils.load("naca0007"), 0.06)
    assert sectiondesign.properties(thin)["i_solid"] == pytest.approx(ref["i_solid"] * (6 / 7) ** 3, rel=1e-3)
    m = sectiondesign.properties(sectiondesign.stiffness_matched(thin, ref))
    assert m["t"] == pytest.approx(0.07, abs=2e-4)
    assert min(m["i_solid"] / ref["i_solid"], m["i_skin"] / ref["i_skin"]) == pytest.approx(1.0, abs=2e-3)


def test_spec_with_thickness():
    assert sectiondesign.load("naca0009@0.07").thickness()[0] == pytest.approx(0.07, abs=2e-4)


# --- race time --------------------------------------------------------------------------


def _polar(cand, d0, a_load, d_load, force=6.69):
    # three points: 0 deg, exactly the load, beyond it
    return pd.DataFrame({"candidate": cand, "speed": 1.0, "aoa": [0.0, a_load, 6.0],
                         "side_force": [0.0, force, 10.0], "drag": [d0, d_load, 0.6]})


def test_race_time_worked_example():
    # methodology.md section 6: 0008/90 is 0.92 % of race time behind 0007/100 at 1 m/s, working load
    df = pd.concat([_polar("0007/100", 0.1990, 3.84, 0.3800), _polar("0008/90", 0.1999, 4.21, 0.3963)])
    loads = pd.DataFrame({"speed": [1.0], "load": ["working"], "force": [6.69]})
    rt = racetime.race_time(df, loads).set_index("candidate")
    assert rt.loc["0007/100", "loss"] == 0
    assert rt.loc["0008/90", "loss"] == pytest.approx(0.926, abs=0.005)
    rt2 = racetime.race_time(df, loads, racetime.Course(slope_factor=2)).set_index("candidate")
    assert rt2.loc["0008/90", "loss"] < rt.loc["0008/90", "loss"]


def test_prestall_branch_skips_dip_and_stall():
    aoa = np.array([0, 1, 2, 3, 4, 5])
    force = np.array([0.0, 0.3, 0.2, 1.0, 1.2, 1.1])  # lift reversal at 1-2 deg, stall after 4
    assert list(racetime.prestall_branch(aoa, force)) == [0, 2, 3, 4]


def test_race_time_force_out_of_range_is_nan():
    df = _polar("a", 0.2, 3.0, 0.3)
    loads = pd.DataFrame({"speed": [1.0], "load": ["high"], "force": [20.0]})
    assert racetime.race_time(df, loads)["aoa"].isna().all()


def test_fin_forces():
    df = pd.DataFrame({"candidate": ["x"], "chord": [0.1], "speed": [1.0], "aoa": [4.0], "Cl": [0.4], "Cd": [0.015]})
    t = racetime.fin_forces(df, rho=1000.0)
    assert t["side_force"].iloc[0] == pytest.approx(0.4 * 500 * 0.1 * 0.36)
    assert t["drag"].iloc[0] > 0.015 * 500 * 0.1 * 0.36  # plus induced drag


# --- XFOIL -----------------------------------------------------------------------------


def test_ncrit_from_tu():
    assert xfoil.ncrit_from_tu(0.1) == pytest.approx(8.15, abs=0.01)
    assert xfoil.ncrit_from_tu(1.0) == pytest.approx(2.62, abs=0.01)


def test_parse_polar():
    text = """
   alpha    CL        CD       CDp       CM     Top_Xtr  Bot_Xtr  Top_Itr  Bot_Itr
  ------ -------- --------- --------- -------- -------- -------- -------- --------
   0.000   0.0000   0.01207   0.00334  -0.0000   1.0000   1.0000   1.0000 200.0000
   2.000   0.2708   0.01300   0.00448  -0.0154   0.9342   1.0000   7.5719 200.0000
"""
    d = xfoil._parse_polar(text)
    assert d.shape == (2, 7) and d[1, 1] == pytest.approx(0.2708)


def _have_xfoil():
    try:
        xfoil.find_xfoil()
        return True
    except FileNotFoundError:
        return False


@pytest.mark.skipif(not _have_xfoil(), reason="xfoil not built (tools/build-xfoil.sh)")
def test_xfoil_polar_naca0009():
    p = xfoil.polar(foils.load("naca0009"), 1e5, [0, 2, 4], ncrit=9)
    assert list(p.alpha) == [0, 2, 4]
    assert p.cl[0] == pytest.approx(0, abs=1e-3) and 0.3 < p.cl[2] < 0.6
    assert 0.008 < p.cd[0] < 0.02
