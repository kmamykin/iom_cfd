"""Keel fits from keel3d results (straight and through an exported table), a
whole boat built from a boat file, and the builder's protocol."""

import math

import pandas as pd
import pytest

from iomcfd import config
from iomcfd.vpp import sails_orc
from iomcfd.vpp.components.base import State, Wind
from iomcfd.vpp.components.foils import LiftingLine, lift_slope
from iomcfd.vpp.components.keel import PolarFit

needs_orc = pytest.mark.skipif(not sails_orc.DATA.exists(), reason="the ORC 2026 sail tables are not in boats/private/orc")

D_HULL, D0, K, A, S0 = 0.40, 0.30, 0.004, 1.3, 0.05


def _keel3d_csv(path):
    rows = []
    for heel, a in ((0, A), (25, 0.9 * A)):
        for b in (0, 2, 4):
            S = S0 + a * b
            rows.append({"case": f"heel{heel}_leeway{b}", "status": "ok", "heel": heel, "leeway": b, "speed": 1.0,
                         "fin_mean_chord": 0.09, "nu": 1.137e-6, "rhoInf": 999.1, "bulb_section": "naca0011",
                         "bulb_aspect": 1.0, "side_N": S, "drag_N": D_HULL + D0 + K * S**2, "drag_hull_N": D_HULL,
                         "vertical_N": -2.7 + 0.1 * b, "drag_fin_friction_N": 0.15, "drag_bulb_friction_N": 0.08,
                         "x_clr": 0.47, "z_clr": -0.25})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_keel_fits_recover_the_polar(tmp_path):
    f = PolarFit.from_results(_keel3d_csv(tmp_path / "results.csv"), {"bulb_section": "naca0011"})
    assert f.heels == [0.0, 25.0]
    assert f.a[0] == pytest.approx(A) and f.a[1] == pytest.approx(0.9 * A)
    assert f.k[0] == pytest.approx(K, rel=1e-6)
    assert f.D0_friction[0] + f.D0_pressure[0] == pytest.approx(D0, rel=1e-6)
    ld = f.loads(State(1.0, 0.0, 2.0), Wind(3.0, 45.0))
    assert ld.Y == pytest.approx(S0 + 2 * A)
    assert -ld.X == pytest.approx(D0 + K * (S0 + 2 * A) ** 2)
    assert ld.K == pytest.approx(0.25 * ld.Y)  # side force to windward 0.25 m down heels to starboard
    # twice the speed: side force x4, induced drag x4 (T_eff kept), friction with C_F(Re)
    l2 = f.loads(State(2.0, 0.0, 2.0), Wind(3.0, 45.0))
    assert l2.Y == pytest.approx(4 * ld.Y)
    assert l2.info["Di"] == pytest.approx(4 * ld.info["Di"])
    assert 3.0 * D0 < l2.info["D0"] < 4.0 * D0
    # beyond the fits' heel or leeway: held and flagged
    assert f.loads(State(1.0, 30.0, 2.0), Wind(3.0, 45.0)).extrapolated
    assert f.loads(State(1.0, 10.0, 5.0), Wind(3.0, 45.0)).extrapolated
    assert not f.loads(State(1.0, 10.0, 3.0), Wind(3.0, 45.0)).extrapolated


def test_foil_lift_and_rudder_sign():
    assert lift_slope(1e6) == pytest.approx(2 * math.pi, rel=1e-5)
    assert lift_slope(1e-3) == pytest.approx(math.pi * 1e-3 / 2, rel=1e-3)
    r = LiftingLine(0.2, 0.07, "naca0008", x=0.87, z=-0.12, name="rudder")
    w = Wind(3.0, 45.0)
    # trailing edge to starboard (δ < 0, weather helm) adds windward lift aft: bow to starboard
    ld = r.loads(State(1.0, 0.0, 2.0, {"rudder.angle": -3.0}), w)
    assert ld.Y > 0 and ld.N < 0
    assert r.loads(State(1.0, 0.0, 2.0, {"rudder.angle": 2.0}), w).Y == pytest.approx(0.0, abs=1e-12)


# The weighted race time at 07ad64b (before the components refactor), which
# the refactor reproduced bit for bit; a change here is a change of the model.
# 507.52813971251095 until the trim tables were extended (pitch moment to
# 10 N m, waves to 15° and 4 m/s): the new nodes move the splines, −2.7e-6.
PINNED_RACE_S = 507.5267728187576


@pytest.fixture(scope="module")
def built():
    from iomcfd.vpp.boat import BoatSpec, build

    spec = BoatSpec.load(config.home() / "boats" / "canoe-placeholder-foil.yaml", {"wind.tws": [2.0, 4.0]})
    return build(spec)


@needs_orc
def test_build_placeholder_boat(built):
    assert built.mass.mass == pytest.approx(4.0)
    assert not built.warnings
    # GZ at 40 deg against Gilbert's 117-158 mm for real IOMs (fin-stiffness.md; unverified anchor)
    gz40 = built.table.rm(40.0) / (built.mass.mass * 9.80665)
    assert 0.10 < gz40 < 0.17


@needs_orc
def test_solver_settings_from_the_boat_file(built):
    from iomcfd.vpp.boat import BoatSpec, build

    assert built.boat.settings.leeway_max == 15.0
    spec = BoatSpec.load(config.home() / "boats" / "canoe-placeholder-foil.yaml",
                         {"wind.tws": [2.0], "solver.leeway_max": 10.0})
    assert build(spec).boat.settings.leeway_max == 10.0


@needs_orc
def test_race_and_rates_on_the_built_boat(built):
    from iomcfd.vpp.race import race, weighted
    from iomcfd.vpp.rates import rates, standard

    rows = race(built.boat, built.wind, built.course)
    for r in rows:
        assert r.up.converged and r.down.converged
        assert 0.3 < r.up.V < 2.0 and 25 < r.up.twa < 60 and r.down.twa > 140
        assert 0 <= r.up.heel < 60
    assert weighted(rows) == pytest.approx(PINNED_RACE_S, rel=1e-9)
    rs, summary = rates(built.boat, built.course, built.wind, rows, standard(built.boat))
    assert summary["drag +0.01 N"] > 0
    assert summary["RM_φ +1 %"] < 0


def test_section_change_at_equal_lift(tmp_path):
    from iomcfd.vpp.components.section import SectionChange, deltas

    # new section: 10 % more lift per degree and 0.001 less C_d at equal C_l, both speeds
    rows = []
    for v in (0.75, 1.5):
        for a in (0, 2, 4, 6):
            cl = 0.1 * a
            rows += [{"foil": "ref", "speed": v, "aoa": a, "Cl": cl, "Cd": 0.010 + 0.05 * cl**2},
                     {"foil": "new", "speed": v, "aoa": a, "Cl": 1.1 * cl, "Cd": 0.009 + 0.05 * (1.1 * cl) ** 2}]
    br = deltas(pd.DataFrame(rows), "new", "ref")
    f = PolarFit.from_results(_keel3d_csv(tmp_path / "results.csv"), {"bulb_section": "naca0011"})
    sc = SectionChange(f, br, chord=0.09, span=0.33)
    da, dd, out = sc.delta(0.3, 1.0)
    # −0.001 plus the linear interpolation of the quadratic term between the computed angles:
    # ref 0.015 at C_l 0.3 (between 0.2 and 0.4), new 0.01406 (between 0.22 and 0.44)
    assert dd == pytest.approx(-0.00094, abs=1e-9)
    assert da == pytest.approx(0.3 / 0.11 - 3.0, abs=1e-9)  # the new section needs less angle
    assert not out and sc.delta(0.3, 2.0)[2]  # beyond the polar speeds: flagged
    s = State(1.0, 0.0, 2.0)
    base, new = f.loads(s, Wind(3.0, 45.0)), sc.loads(s, Wind(3.0, 45.0))
    assert new.Y > base.Y  # less angle needed: more side force at the same leeway
    q = 0.5 * 999.1
    cl = 0.83 * new.Y / (q * 0.09 * 0.33)
    assert -new.X == pytest.approx(f.loads(s.but(leeway=2.0 - sc.delta(cl, 1.0)[0]), Wind(3.0, 45.0)).X * -1
                                   + sc.delta(cl, 1.0)[1] * q * 0.09 * 0.33, rel=1e-3)  # 2-pass fixed point
