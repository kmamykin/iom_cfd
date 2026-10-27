"""response.csv: each part's loads swept around a solved point, one input at
a time, on a toy boat."""

import math
from dataclasses import dataclass

import pytest

from iomcfd.vpp.components.base import Control, Loads, State, Wind
from iomcfd.vpp.race import Course, WindRange, race_row
from iomcfd.vpp.response import LEEWAYS, response, responses, variables
from iomcfd.vpp.solver import Boat, Settings, SineRighting, solve_point
from test_vpp_solver import ToyHull, ToyRudder


@dataclass
class FlatSails:
    """Thrust T0 · flat (+10 % on the second set) and side force S0 · flat
    at a CE of height h."""

    T0: float = 2.0
    S0: float = 6.0
    h: float = 0.7
    name: str = "sails"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = (Control("flat", "optimise", 1.0, lo=0.5, hi=1.0),
                       Control("set", "choice", 0.0, options=((0.0, 0.0), (1.0, 60.0))))

    def loads(self, s: State, w: Wind) -> Loads:
        f, k = s.controls["sails.flat"], s.controls["sails.set"]
        p = math.radians(s.heel)
        return Loads.at((0.4, -self.h * math.sin(p), self.h * math.cos(p)), X=self.T0 * f * (1 + 0.1 * k),
                        Y=-self.S0 * f * f)


def boat() -> Boat:
    return Boat([FlatSails(), ToyHull(heel_drag=0.5), ToyRudder()], SineRighting(10.0), Settings(yaw=True))


def test_sweeps_pass_through_the_solved_point():
    b, w = boat(), Wind(3.0, 45.0)
    p = solve_point(b, w)
    assert p.converged
    rows = response(b, p, w)
    for var, values in variables(b, p).items():
        got = [r for r in rows if r["var"] == var]
        assert [r["value"] for r in got] == values
        at = {"V": p.V, "heel": p.heel, "leeway": p.leeway}.get(var, p.controls.get(var))
        r = next(r for r in got if r["value"] == at)
        for name, ld in p.parts.items():  # the solved state, evaluated again: the point's own loads
            assert [r[f"{q}_{name}"] for q in "XYZKMN"] == [getattr(ld, q) for q in "XYZKMN"]
    leeway = [r["value"] for r in rows if r["var"] == "leeway"]
    assert len(leeway) == len(LEEWAYS) + 1 and leeway[0] == 0.0 and leeway[-1] == max(6.0, p.leeway)
    flat = [r["value"] for r in rows if r["var"] == "sails.flat"]
    assert flat[0] == 0.5 and flat[-1] == 1.0
    # only the varied input moves
    for r in rows:
        if r["var"] != "V":
            assert r["V"] == p.V
        if r["var"] != "heel":
            assert r["heel"] == p.heel


def test_choice_sweep_keeps_to_the_allowed_options():
    b = boat()
    up, down = solve_point(b, Wind(3.0, 45.0)), solve_point(b, Wind(3.0, 150.0))
    assert variables(b, up)["sails.set"] == [0.0]
    assert variables(b, down)["sails.set"] == [0.0, 1.0]
    rows = responses(b, [race_row(Course(), 3.0, 1.0, up, down)], WindRange([3.0]))
    assert {r["leg"] for r in rows} == {"up", "down"}
    assert {r["twa"] for r in rows if r["leg"] == "down"} == {150.0}
    assert "converged" not in rows[0] and rows[0]["var"] == "V"
    assert all(r["V"] == pytest.approx(down.V * x) for r, x in
               zip([r for r in rows if r["leg"] == "down" and r["var"] == "V"],
                   [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]))
