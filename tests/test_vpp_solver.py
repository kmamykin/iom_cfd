"""VPP frames, solver and race time on toy boats with closed-form answers."""

import math
from dataclasses import dataclass

import numpy as np
import pytest

from iomcfd import config
from iomcfd.vpp import frames
from iomcfd.vpp.components.base import Control, Loads, Scaled, State, Wind
from iomcfd.vpp.race import Course, WindRange, boat_lengths, race_row, weighted
from iomcfd.vpp.solver import Boat, Point, Settings, SineRighting, best_vmg, evaluate, solve_point


# --- frames ---------------------------------------------------------------


def test_apparent_wind_beam_reach():
    aws, awa = frames.apparent_wind(3.0, 90.0, 4.0)
    assert aws == pytest.approx(5.0)
    assert awa == pytest.approx(math.degrees(math.atan2(3, 4)))


def test_apparent_wind_dead_run():
    aws, awa = frames.apparent_wind(3.0, 180.0, 1.0)
    assert aws == pytest.approx(2.0)
    assert awa == pytest.approx(180.0)


def test_heeled_wind_drops_the_mast_component():
    aws, awa = frames.heeled_wind(2.0, 90.0, 0.0, 60.0)
    assert aws == pytest.approx(1.0)  # cross-wind halved by cos 60
    assert awa == pytest.approx(90.0)
    _, a = frames.heeled_wind(2.0, 40.0, 3.0, 0.0)
    assert a == pytest.approx(37.0)  # from the centreline: β_AW − β_Y


def test_lift_drag_matches_orc_cr_ch():
    L, D, a = 2.0, 0.5, 35.0
    drive, heel = frames.lift_drag_to_centreline(L, D, a)
    r = math.radians(a)
    assert drive == pytest.approx(L * math.sin(r) - D * math.cos(r))
    assert heel == pytest.approx(L * math.cos(r) + D * math.sin(r))


def test_rig_to_course_matches_nomenclature_mapping():
    # docs/nomenclature.md: T_a = drive cos β + heel sin β, S_a = heel cos β − drive sin β (upright)
    drive, heel, b = 2.0, 7.0, 4.0
    X, Y, Z = frames.rig_to_course(drive, heel, 0.0, b)
    rb = math.radians(b)
    assert X == pytest.approx(drive * math.cos(rb) + heel * math.sin(rb))
    assert -Y == pytest.approx(heel * math.cos(rb) - drive * math.sin(rb))
    assert Z == pytest.approx(0.0)
    _, Y30, Z30 = frames.rig_to_course(0.0, heel, 30.0, 0.0)
    assert -Y30 == pytest.approx(heel * math.cos(math.radians(30)))  # S_a ≈ FHA cos φ
    assert Z30 < 0


def test_loads_at_signs():
    # sail heeling force to leeward at the CE heels to starboard: K = FHA · Z_CE
    pt = frames.heeled_point(0.4, 0.0, 0.7, 20.0)
    _, Y, Z = frames.rig_to_course(0.0, 5.0, 20.0, 0.0)
    assert Loads.at(pt, Y=Y, Z=Z).K == pytest.approx(5.0 * 0.7)
    # keel side force to windward below the waterline also heels to starboard
    assert Loads.at((0.5, 0.0, -0.3), Y=6.0).K == pytest.approx(1.8)
    # side force to port aft of the bow turns the bow to starboard
    assert Loads.at((0.9, 0.0, -0.1), Y=1.0).N == pytest.approx(-0.9)
    # thrust high up pushes the bow down
    assert Loads.at((0.4, 0.0, 0.7), X=2.0).M == pytest.approx(1.4)


# --- toy boat -----------------------------------------------------------------


@dataclass
class ConstSails:
    """Constant course-frame forces: thrust T0 and side force S0 (to leeward)
    at a CE of height h, x_ce; or T0 · sin(β_TW) with `vary`."""

    T0: float = 2.0
    S0: float = 6.0
    h: float = 0.7
    x_ce: float = 0.4
    vary: str = ""
    name: str = "sails"
    kind: str = "aero"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        a = math.radians(w.twa)
        T = {"": self.T0, "sin": self.T0 * math.sin(a), "run": self.T0 * (1 - math.cos(a))}[self.vary]
        return Loads.at((self.x_ce, -self.h * math.sin(math.radians(s.heel)), self.h * math.cos(math.radians(s.heel))),
                        X=T, Y=-self.S0)


@dataclass
class ToyHull:
    """D = d V², side force s V² β_Y (per degree) at depth z, x."""

    d: float = 2.0
    s: float = 1.0
    x: float = 0.5
    z: float = -0.3
    heel_drag: float = 0.0  # extra drag factor (1 + heel_drag · φ²)
    name: str = "hull"
    kind: str = "hydro"
    attitude: bool = False

    def loads(self, st: State, w: Wind) -> Loads:
        drag = self.d * st.V**2 * (1 + self.heel_drag * math.radians(st.heel) ** 2)
        side = Loads.at(frames.heeled_point(self.x, 0.0, self.z, st.heel), Y=self.s * st.V**2 * st.leeway)
        return Loads(X=-drag) + side


@dataclass
class ToyRudder:
    r: float = 0.4
    x: float = 0.9
    z: float = -0.3
    name: str = "rudder"
    kind: str = "hydro"
    attitude: bool = False
    controls: tuple = (Control("angle", "balance"),)

    def loads(self, st: State, w: Wind) -> Loads:
        return Loads.at(frames.heeled_point(self.x, 0.0, self.z, st.heel),
                        Y=self.r * st.V**2 * st.controls["rudder.angle"])


def toy_boat(yaw: bool, **sails) -> Boat:
    return Boat([ConstSails(**sails), ToyHull(), ToyRudder()], SineRighting(10.0),
                Settings(yaw=yaw, optimise=False))


def test_toy_without_yaw_matches_closed_form():
    b = toy_boat(yaw=False)
    p = solve_point(b, Wind(3.0, 45.0))
    V = math.sqrt(2.0 / 2.0)
    assert p.converged
    assert p.V == pytest.approx(V, rel=1e-6)
    # roll: (h − z) S0 cos φ = K sin φ
    assert p.heel == pytest.approx(math.degrees(math.atan((0.7 + 0.3) * 6.0 / 10.0)), abs=1e-5)
    assert p.leeway == pytest.approx(6.0 / (1.0 * V**2), rel=1e-6)


def test_toy_with_yaw_matches_closed_form():
    b = toy_boat(yaw=True)
    p = solve_point(b, Wind(3.0, 45.0))
    assert p.converged
    V = 1.0
    phi = math.atan(0.6)  # same roll balance: both hydro forces at the same depth
    # yaw: N_sails + N_hull + N_rudder = 0 with Y_hull + Y_rudder = S0
    n_sails = 0.4 * 6.0 + 0.7 * math.sin(phi) * 2.0  # −x Y − y X with Y = −S0, y = −h sin φ
    zs = 0.3 * math.sin(phi)  # heeled y of the hydro points (−z sin φ)
    # −x_h Y_h − x_r Y_r = −n_sails (y X terms vanish: hydro side forces have X = 0)
    A = np.array([[1.0, 1.0], [-0.5, -0.9]])
    yh, yr = np.linalg.solve(A, [6.0, -n_sails])
    assert zs > 0
    assert math.radians(p.heel) == pytest.approx(phi, abs=1e-7)
    assert p.leeway == pytest.approx(yh / V**2, rel=1e-6)
    assert p.controls["rudder.angle"] == pytest.approx(yr / (0.4 * V**2), rel=1e-6)


def test_balances_hold_at_the_solution():
    b = toy_boat(yaw=True)
    p = solve_point(b, Wind(3.0, 45.0))
    total, _, att, _ = evaluate(b, State(p.V, p.heel, p.leeway, p.controls), Wind(3.0, 45.0))
    assert abs(total.X) < 1e-6 and abs(total.Y) < 1e-6 and abs(total.N) < 1e-6
    assert total.K == pytest.approx(att.rm, abs=1e-6)


def test_best_vmg_upwind_closed_form():
    # T = T0 sin β_TW, D = d V² -> VMG ∝ sqrt(sin a) cos a, best at tan² a = 1/2
    b = toy_boat(yaw=False, vary="sin")
    p = best_vmg(b, 3.0, "up")
    assert p.twa == pytest.approx(math.degrees(math.atan(math.sqrt(0.5))), abs=0.1)
    assert "vmg-at-bound" not in p.flags


def test_best_vmg_downwind_runs_square():
    b = toy_boat(yaw=False, vary="run")
    p = best_vmg(b, 3.0, "down")
    assert p.twa == pytest.approx(180.0, abs=0.1)
    assert -p.vmg == pytest.approx(math.sqrt(2.0 * 2.0 / 2.0), rel=1e-3)


@dataclass
class FlatSails(ConstSails):
    """Thrust and side force scale with flat; side force with flat² (a
    flatter sail loses heeling force faster than drive)."""

    flat_min: float = 0.5

    @property
    def controls(self) -> tuple:
        return (Control("flat", "optimise", 1.0, lo=self.flat_min, hi=1.0),)

    def loads(self, s: State, w: Wind) -> Loads:
        f = s.controls["sails.flat"]
        T, S = self.T0 * f, self.S0 * f**2
        return Loads.at((self.x_ce, -self.h * math.sin(math.radians(s.heel)), self.h * math.cos(math.radians(s.heel))),
                        X=T, Y=-S)


def test_flat_search_finds_an_interior_optimum():
    # V² = T0 f / (d (1 + 8 φ²)) with tan φ = 9 f² / 4: best near f = 0.28
    hull = ToyHull(s=20.0, heel_drag=8.0)
    b = Boat([FlatSails(S0=9.0, flat_min=0.1), hull, ToyRudder()], SineRighting(4.0), Settings(yaw=False))
    p = solve_point(b, Wind(3.0, 45.0))
    flat = p.controls["sails.flat"]
    assert p.converged and 0.2 < flat < 0.4
    for f in (flat - 0.03, flat + 0.03, 1.0):
        q = solve_point(b, Wind(3.0, 45.0), hold={"sails.flat": min(f, 1.0)})
        assert q.V <= p.V + 1e-6


# --- race time --------------------------------------------------------------


def _pt(tws, twa, V):
    p = Point(tws, twa, V=V, converged=True)
    return p


def test_race_row_and_weighting():
    c = Course(leg=100.0, laps=2, tacks_per_leg=4, gybes_per_leg=2, tack_s=3.0, gybe_s=2.0)
    up = _pt(3.0, 45.0, 1.0 / math.cos(math.radians(45.0)))  # VMG 1 m/s
    down = _pt(3.0, 180.0, 1.25)
    r = race_row(c, 3.0, 1.0, up, down)
    assert r.t_up == pytest.approx(2 * (100.0 + 12.0))
    assert r.t_down == pytest.approx(2 * (80.0 + 4.0))
    r2 = race_row(c, 4.0, 3.0, up, down)
    assert weighted([r, r2]) == pytest.approx(r.t)
    assert boat_lengths(1.0, r.t, c) == pytest.approx(400.0 / r.t)


def test_wind_range_uniform_and_histogram(tmp_path):
    assert WindRange([1.0, 2.0]).weights == [1.0, 1.0]
    f = tmp_path / "club.csv"
    f.write_text("# venue: a club\ntws,weight\n1.5,10\n2.5,30\n")
    w = WindRange.from_histogram(f)
    assert w.tws == [1.5, 2.5] and w.weights == [10.0, 30.0]
    venue = WindRange.from_histogram(config.home() / "boats" / "venue_winds.csv")
    assert venue.tws[0] == 1.5 and sum(venue.weights) == pytest.approx(100.0, abs=0.01)


# --- robustness (found with stand-ins for Python-VPP's YD-41) ----------------


def test_tolerances_scale_with_the_boat():
    # a boat 1000 times as forceful: same speed, still converged
    b = Boat([Scaled(c, 1e3) for c in (ConstSails(), ToyHull(), ToyRudder())], SineRighting(1e4),
             Settings(yaw=True, optimise=False))
    p = solve_point(b, Wind(3.0, 45.0))
    assert p.converged
    assert p.V == pytest.approx(1.0, rel=1e-8)


def test_speed_search_climbs_out_of_an_unbalanced_start():
    # V0 = 0.5 tws = 0.5 m/s needs 24 deg of leeway (> leeway_max): search upward to V = 1
    b = toy_boat(yaw=False)
    p = solve_point(b, Wind(1.0, 45.0))
    assert p.converged and p.V == pytest.approx(1.0, rel=1e-8)


@dataclass
class CappedRighting:
    """RM = K sin φ cos² φ: RM / cos φ (against a heeling arm ∝ cos φ) is at most K/2."""

    K: float

    def at(self, heel, M_ext=0.0, Z_ext=0.0):
        from iomcfd.vpp.solver import Attitude

        p = math.radians(heel)
        return Attitude(rm=self.K * math.sin(p) * math.cos(p) ** 2)


def test_flat_search_when_full_power_cannot_balance():
    # 9 f² cos φ = 10 sin φ cos² φ needs f² <= 5/9: flat 1 has no balance; the fastest
    # (thrust ∝ f, no heel drag) is the stability limit, f = 0.745
    b = Boat([FlatSails(S0=9.0, flat_min=0.3), ToyHull(s=20.0), ToyRudder()], CappedRighting(10.0),
             Settings(yaw=False))
    p = solve_point(b, Wind(3.0, 45.0))
    assert p.converged and 0.70 < p.controls["sails.flat"] < math.sqrt(5 / 9) + 1e-6


# --- controls -----------------------------------------------------------------


def test_controls_are_keyed_by_part_and_held_when_yaw_is_off():
    b = toy_boat(yaw=False)
    assert [(k.key, k.role) for k in b.controls()] == [("rudder.angle", "balance")]
    p = solve_point(b, Wind(3.0, 45.0))
    assert p.controls == {"rudder.angle": 0.0}  # the balance control's default
    assert list(p.row())[:6] == ["tws", "twa", "V", "heel", "leeway", "rudder.angle"]


def test_one_control_per_role():
    b = Boat([FlatSails(), FlatSails(name="jib"), ToyHull()], SineRighting(10.0), Settings(yaw=False))
    with pytest.raises(NotImplementedError):
        solve_point(b, Wind(3.0, 45.0))
