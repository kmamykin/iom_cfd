"""Exchange rates on a toy boat with a closed-form answer."""

import math

import pytest

from iomcfd.vpp.race import Course, WindRange, race
from iomcfd.vpp.rates import Perturbation, add_drag, rates, scale_component, scale_righting
from iomcfd.vpp.solver import Boat, Settings, SineRighting
from test_vpp_solver import ConstSails, ToyHull, ToyRudder


def _boat():
    # thrust T0 sin β_TW upwind, T0 (1 − cos β_TW) downwind; D = d V²
    return Boat([ConstSails(vary="sin"), ToyHull(), ToyRudder()], SineRighting(10.0),
                Settings(yaw=False, optimise=False))


def test_drag_rate_matches_closed_form_and_the_full_search():
    b = _boat()
    course, wind = Course(tacks_per_leg=0, gybes_per_leg=0), WindRange([3.0])
    base = race(b, wind, course)
    dD = 0.01
    rs, summary = rates(b, course, wind, base, [Perturbation("drag +0.01 N", add_drag(dD), dD=dD)])
    # upwind at the best angle a*: V² = (T0 sin a* − ΔD) / d, so dV/V = −ΔD / (2 T0 sin a*)
    a = math.atan(math.sqrt(0.5))
    T = 2.0 * math.sin(a)
    t_up = base[0].t_up
    assert rs[0].dt_up == pytest.approx(t_up * (math.sqrt(T / (T - dD)) - 1), rel=2e-3)
    # the implied V dR/dV is 2 D = 2 T at the balance (D = d V²)
    assert rs[0].vdrdv_up == pytest.approx(2 * T, rel=2e-2)
    # the envelope shortcut agrees with a full re-search of angle and trim
    full, _ = rates(b, course, wind, base, [Perturbation("drag +0.01 N", add_drag(dD), dD=dD)], check=True)
    assert full[0].dt == pytest.approx(rs[0].dt, rel=2e-2)
    assert summary["drag +0.01 N"] > 0


def test_rm_and_scaling_rates_have_the_right_sign():
    b = _boat()
    course, wind = Course(), WindRange([3.0])
    base = race(b, wind, course)
    rs, summary = rates(b, course, wind, base, [Perturbation("RM +1 %", scale_righting(1.01)),
                                                 Perturbation("hull +1 %", scale_component("hull", 1.01))])
    assert summary["hull +1 %"] > 0  # more drag: slower
    assert summary["RM +1 %"] == pytest.approx(0.0, abs=1e-9)  # the toy's heel costs nothing
