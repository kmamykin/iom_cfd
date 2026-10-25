import math

import numpy as np
import pandas as pd
import pytest

from iomcfd import boardrank, racetime
from iomcfd.physics import induced_drag


def _design(**kw):
    d = boardrank.load_design("thistle")
    return boardrank.dataclasses.replace(d, **kw)


def _polars(cands=("base", "x"), speeds=(0.5, 1.0, 2.0, 4.0), cd0=0.006, k=1.0):
    """Synthetic polars: Cl = 0.1 aoa (pre-stall to 8 deg, then falls), Cd
    split half and half, Cd ~ Re^-0.2; candidate 'x' has k times the drag."""
    rows = []
    for c in cands:
        for v in speeds:
            for a in range(0, 11):
                cl = 0.1 * a if a <= 8 else 0.8 - 0.1 * (a - 8)
                cd = (cd0 + 0.002 * (0.1 * a) ** 2) * (v / 1.0) ** -0.2 * (k if c == "x" else 1.0)
                rows.append({"candidate": c, "speed": v, "aoa": float(a), "Cl": cl, "Cd": cd, "Cdp": cd / 2,
                             "Cdf": cd / 2, "unsteady": False})
    return pd.DataFrame(rows)


def test_design_and_normal_speed():
    d = boardrank.load_design("thistle")
    assert d.t_c == pytest.approx(1 / 18)
    assert d.cfd_speeds[4] == pytest.approx(5 * 0.514444 * math.cos(math.radians(10)), abs=1e-4)
    assert d.nu == pytest.approx(1.0035e-6, rel=1e-3)


def test_at_speed_loglog_exact_and_extrapolation_limit():
    p = _polars(cands=("base",))
    r = boardrank.at_speed(p, 1.5).set_index("aoa")
    assert r.loc[0.0, "Cd"] == pytest.approx(0.006 * 1.5**-0.2, rel=1e-9)  # exact for Cd ~ V^-0.2
    assert len(boardrank.at_speed(p, 4.0 * 1.02)) == 11  # 2 % past the last speed: extrapolated
    assert boardrank.at_speed(p, 4.0 * 1.05).empty  # 5 %: left out


def test_board_forces_reduce_to_fin_forces_without_rake():
    d = _design(rake=0.0)
    p = _polars(cands=("base",))
    f = boardrank.board_forces(p, d, [1.0 / boardrank.KN]).set_index("aoa")  # V_b = 1 m/s
    q = 0.5 * d.rho
    assert f.loc[4.0, "side_force"] == pytest.approx(0.4 * q * d.chord * d.span)
    cd = p[(p["speed"] == 1.0) & (p["aoa"] == 4.0)]["Cd"].iloc[0]
    course = racetime.Course(span=d.span, e=d.e)
    ref = racetime.fin_forces(pd.DataFrame({"candidate": ["b"], "chord": [d.chord], "speed": [1.0], "aoa": [4.0],
                                            "Cl": [0.4], "Cd": [cd]}), course, rho=d.rho)
    assert f.loc[4.0, "drag"] == pytest.approx(ref["drag"].iloc[0], rel=1e-9)


def test_board_forces_use_each_candidates_chord():
    """A candidate with a shorter chord gets a proportionally smaller area:
    the same Cl makes less side force and the same Cd less viscous drag."""
    d = _design()
    p = _polars()
    p["chord"] = np.where(p["candidate"] == "x", 0.6 * d.chord, d.chord)
    f = boardrank.board_forces(p, d, [3.0]).set_index(["candidate", "aoa"])
    assert f.loc[("x", 4.0), "side_force"] == pytest.approx(0.6 * f.loc[("base", 4.0), "side_force"])
    assert f.loc[("x", 4.0), "drag_v"] == pytest.approx(0.6 * f.loc[("base", 4.0), "drag_v"])
    no_chord = boardrank.board_forces(p.drop(columns="chord"), d, [3.0]).set_index(["candidate", "aoa"])
    assert no_chord.loc[("x", 4.0), "side_force"] == pytest.approx(f.loc[("base", 4.0), "side_force"])


def test_sweep_projections_and_induced_drag_identity():
    lam = 60.0
    d = _design(rake=lam)
    c = math.cos(math.radians(lam))
    vb = 2.0 / c / boardrank.KN  # V_n = 2 m/s exactly
    p = _polars(cands=("base",))
    f = boardrank.board_forces(p, d, [vb]).set_index("aoa")
    q = 0.5 * d.rho * (vb * boardrank.KN) ** 2
    row = p[(p["speed"] == 2.0) & (p["aoa"] == 4.0)].iloc[0]
    assert f.loc[4.0, "side_force"] == pytest.approx(0.4 * q * c**2 * d.chord * d.span)
    assert f.loc[4.0, "drag_v"] == pytest.approx((row["Cdp"] * c**3 + row["Cdf"] * c) * q * d.chord * d.span)
    # the induced drag at the boat's q on the vertical depth = foil2d's at q_n on the length along the edge
    qn = 0.5 * d.rho * 2.0**2
    assert f.loc[4.0, "drag_i"] == pytest.approx(induced_drag(f.loc[4.0, "side_force"], qn, d.span, d.e))
    assert f.loc[4.0, "leeway"] == pytest.approx(4.0 * c)


def test_ranking_at_equal_force():
    d = _design(rake=10.0, up_speeds=[2.0, 4.0], down_speeds=[2.0, 4.0], load_aoa=[1, 2, 4])
    p = _polars(k=1.1, speeds=(0.9, 1.0, 1.9, 2.0, 2.1))
    r = boardrank.rank(p, d, baseline="base")
    s = r["summary"]
    assert s.loc["base", "upwind %"] == pytest.approx(0.0)
    # same lift curve, 10 % more section drag: less than 10 % more board drag (the induced part is equal)
    assert 0 < s.loc["x", "upwind %"] < 10
    assert s.loc["x", "downwind %"] == pytest.approx(10.0, rel=1e-6)  # no lift, no induced drag
    assert s.loc["x", "d leeway deg"] == pytest.approx(0.0, abs=1e-9)
    assert s.loc["x", "veto"] == "downwind"  # loses more downwind than it gains upwind (it gains nothing)


def test_stall_margin_and_censoring():
    p = _polars(cands=("base",), speeds=(1.0,))
    d = _design(rake=0.0)
    f = boardrank.board_forces(p, d, [1.0 / boardrank.KN])
    lds = boardrank.loads(f, "base", [1, 2, 4])
    m = boardrank.stall_margin(f, lds).iloc[0]
    assert m["aoa_max"] == 8 and m["margin"] == pytest.approx(4.0) and not m["censored"]
    m = boardrank.stall_margin(f[f["aoa"] <= 6], lds).iloc[0]
    assert m["censored"]
