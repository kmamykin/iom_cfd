"""The VPP solver against Python-VPP (iomcfd.vpp.components.pyvpp).

The first test checks the sign mapping on stand-ins that follow Python-VPP's
calling conventions. The others need a Python-VPP checkout,
https://github.com/marinlauber/Python-VPP (checked at 141ea66):

    PYVPP_PATH=/path/to/Python-VPP uv run pytest -m external -s tests/test_vpp_pyvpp.py

They run Python-VPP's own solver (SLSQP over V_b, heel, leeway, flat and
RED) on its YD-41, then ours (yaw off) with its forces, and print the
comparison (-s).
"""

import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from iomcfd.vpp.components import pyvpp
from iomcfd.vpp.components.base import Wind
from iomcfd.vpp.solver import Boat, Point, Settings, solve_point

# --- the mapping on stand-ins ---------------------------------------------------


class FakeYacht:
    """RmH and RmC as Python-VPP's Yacht gives them [N·m]."""

    def _get_RmH(self, phi):
        return 40.0 * math.sin(math.radians(phi))

    def _get_RmC(self, phi):
        return 5.0 * math.sin(math.radians(phi))


class FakeHydro:
    """HydroMod.update's convention: (resistance, side force to windward,
    total righting moment incl. −K_sf·Rm4 and the speed loss RmV < 0)."""

    def __init__(self, yacht):
        self.yacht = yacht

    def update(self, vb, phi, leeway, twa=0.0, tws=None):
        phi = max(0.0, phi)
        self.Ksf = 2.0 * vb**2 * leeway
        Fx = 3.0 * vb**2 * (1 + 0.5 * math.radians(phi) ** 2) + 0.01 * self.Ksf**2 / max(vb**2, 1e-9)
        RmV = -0.05 * vb * phi
        Mx = self.yacht._get_RmH(phi) + self.yacht._get_RmC(phi) + RmV - 0.4 * self.Ksf
        return Fx, self.Ksf * math.cos(math.radians(phi)), Mx


class FakeAero:
    """AeroMod.update's convention: (drive, horizontal heeling force to
    leeward, heeling force × CE height)."""

    aws = awa = 0.0

    def update(self, vb, phi, tws, twa, flat, RED):
        FH = 8.0 * flat**2 * RED / 2
        return 4.0 * flat * RED / 2, FH * math.cos(math.radians(phi)), 1.2 * FH


def test_mapping_solves_pyvpp_equilibrium():
    y = FakeYacht()
    hydro, aero, righting = FakeHydro(y), FakeAero(), pyvpp.PyVPPRighting(y)
    b = Boat([pyvpp.PyVPPHydro(hydro, righting), pyvpp.PyVPPSails(aero, red=2.0)], righting,
             Settings(yaw=False, flat_min=0.53))
    w = Wind(3.0, 45.0)
    p = solve_point(b, w)
    assert p.converged
    # VPPMod._equilibrium: Fxh − Fxa, Fyh − Fya, Mxh − Mxa all vanish at our solution
    Fxh, Fyh, Mxh = hydro.update(p.V, p.heel, p.leeway, w.twa, w.tws)
    Fxa, Fya, Mxa = aero.update(p.V, p.heel, w.tws, w.twa, p.flat, 2.0)
    assert np.allclose([Fxh - Fxa, Fyh - Fya, Mxh - Mxa], 0.0, atol=1e-6)
    # base.py signs: drag aft, keel side force to windward and heeling (K_sf Rm4 − RmV > 0),
    # sail side force to leeward and heeling
    h, s = p.parts["hydro"], p.parts["sails"]
    assert h.X < 0 and h.Y > 0 and h.K == pytest.approx(0.4 * hydro.Ksf + 0.05 * p.V * p.heel)
    assert s.X > 0 and s.Y < 0 and s.K > 0
    assert p.rm == pytest.approx(45.0 * math.sin(math.radians(p.heel)))


# --- against Python-VPP's own solution --------------------------------------------

PYVPP = os.environ.get("PYVPP_PATH", "")
needs_pyvpp = pytest.mark.skipif(not (PYVPP and (Path(PYVPP) / "src" / "python_vpp").is_dir()),
                                 reason="PYVPP_PATH does not point at a Python-VPP checkout")

TWS_KN = (8.0, 16.0)
TWA = (45.0, 90.0, 150.0)
KNOTS = 0.5144  # UtilsMod.KNOTS_TO_MPS [m/s]

# Python-VPP accepts a point when its residuals, scaled by (1e3 N, 1e3 N,
# 1e4 N·m), are within RESID_TOL = 1e-4: 0.1 N of drive or side force and
# 1 N·m of roll. For the YD-41 at these speeds (dD_h/dV_b ≳ 350 N per m/s,
# dRM/dφ ≈ 2500 N·m/°, dS_h/dβ_Y ≳ 600 N/°, estimated from its model) that
# is ≲ 3e-4 m/s (≈ 1e-4 of V_b), ≲ 4e-4° of heel and ≲ 2e-4° of leeway.
# At the same flat and RED the two must agree to that: V_REL and ANGLE leave
# a margin of 5 or more. With flat free both maximise V_b over flat, where
# dV_b/dflat = 0, so V_b still agrees to V_REL. Flat itself (and with it heel
# and leeway) is only printed: V_b(flat) has kinks (fcdmult is a piecewise
# linear table, 1.06 at flat 1, 1.0 at 0.9), so two optimisers can stop at
# flats a little apart with the same V_b.
RESID_TOL = 1e-4  # VPPMod.RESID_TOL, also required of our solution
V_REL = 5e-4
ANGLE = 0.01  # [deg]


@dataclass
class Case:
    tws_kn: float
    twa: float
    sail: str
    theirs: dict  # V [m/s], heel, leeway, flat, red
    bound: str  # a bound of Python-VPP's that our solver does not have, active at its solution
    fixed: Point  # ours at their flat and RED
    free: Point  # ours, flat searched, RED at theirs
    res_fixed: float  # Python-VPP's scaled residual at our solution
    res_free: float
    t_fixed: float  # [s]
    t_free: float

    def row(self) -> str:
        t, f, x = self.theirs, self.free, self.fixed
        return (f"{self.tws_kn:4.0f} {self.twa:5.0f} {self.sail:3} {t['red']:5.3f} | "
                f"{t['V'] / KNOTS:6.3f} {t['heel']:6.2f} {t['leeway']:5.2f} {t['flat']:5.3f} | "
                f"{x.V / KNOTS:6.3f} {x.heel:6.2f} {x.leeway:5.2f} {self.res_fixed:8.1e} {x.converged!s:5} "
                f"{self.t_fixed:5.1f} | {f.V / KNOTS:6.3f} {f.heel:6.2f} {f.leeway:5.2f} {f.flat:5.3f} "
                f"{self.res_free:8.1e} {f.converged!s:5} {self.t_free:5.1f} | {self.bound} {' '.join(f.flags)}")


HEADER = ("TWS   TWA set  RED  | theirs: V_kn   heel  leew  flat | same trim: V_kn heel leew  resid  conv  t_s"
          " | flat free: V_kn heel leew  flat  resid  conv  t_s | bound flags")


def _table(cases: list[Case]) -> str:
    return "\n".join([HEADER, *(c.row() for c in cases)])


@pytest.fixture(scope="module")
def cases() -> list[Case]:
    pytest.importorskip("matplotlib")  # Python-VPP imports it
    pv = pyvpp.load(PYVPP)
    assert (pv.RESID_TOL, pv.KNOTS) == (RESID_TOL, KNOTS)
    yacht = pyvpp.yd41(pv)
    vpp = pv.VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array(TWS_KN), twa_range=np.array(TWA))
    t0 = time.perf_counter()
    vpp.run()
    t_theirs = time.perf_counter() - t0
    out = []
    for i, tws_kn in enumerate(TWS_KN):
        for j, twa in enumerate(TWA):
            w = Wind(tws_kn * pv.KNOTS, twa, z_ref=10.0)  # Python-VPP's TWS is at 10 m
            for k in range(vpp.Nsails):
                vb_kn, heel, leeway, flat, red = vpp.store[i, j, k]
                if vb_kn <= 0:  # not solved: sail set out of its range, or no equilibrium
                    continue
                sail = yacht.sails[k + 1]
                theirs = dict(V=vb_kn * pv.KNOTS, heel=heel, leeway=leeway, flat=flat, red=red)
                bound = []
                if heel >= pyvpp.heel_limit(sail) - 1e-3:
                    bound.append(f"heel<={pyvpp.heel_limit(sail):g}")
                if leeway >= 6.0 - 1e-3 or leeway <= -2.0 + 1e-3:  # VPPMod._solve_point's bounds
                    bound.append("leeway")
                b = pyvpp.boat(pv, yacht, sail.name, red=red)
                t0 = time.perf_counter()
                fixed = solve_point(b, w, flat=flat)
                t1 = time.perf_counter()
                free = solve_point(b, w)
                t2 = time.perf_counter()
                out.append(Case(tws_kn, twa, sail.name, theirs, " ".join(bound), fixed, free,
                                pyvpp.residual(pv, b, w, fixed.V, fixed.heel, fixed.leeway, fixed.flat),
                                pyvpp.residual(pv, b, w, free.V, free.heel, free.leeway, free.flat),
                                t1 - t0, t2 - t1))
    print(f"\nPython-VPP {t_theirs:.1f} s for {len(TWS_KN) * len(TWA)} points x {vpp.Nsails} sail sets\n"
          + _table(out))
    return out


@needs_pyvpp
@pytest.mark.external
def test_pyvpp_solved_every_point(cases):
    solved = {(c.tws_kn, c.twa) for c in cases}
    assert solved == {(v, a) for v in TWS_KN for a in TWA}, _table(cases)


@needs_pyvpp
@pytest.mark.external
def test_same_trim_matches_pyvpp(cases):
    """Flat and RED at Python-VPP's: the balance alone sets V_b, heel and leeway."""
    bad = [c for c in cases
           if not (c.res_fixed <= RESID_TOL
                   and c.fixed.V == pytest.approx(c.theirs["V"], rel=V_REL)
                   and abs(c.fixed.heel - c.theirs["heel"]) <= ANGLE
                   and abs(c.fixed.leeway - c.theirs["leeway"]) <= ANGLE)]
    assert not bad, "\n" + _table(bad)


@needs_pyvpp
@pytest.mark.external
def test_flat_search_matches_pyvpp(cases):
    """RED at Python-VPP's, flat searched by ours: the same V_b. Where Python-VPP
    sits on a bound ours does not have (its heel limit), ours may only be faster."""
    bad = []
    for c in cases:
        V, theirs = c.free.V, c.theirs["V"]
        ok = V >= theirs * (1 - V_REL) if c.bound else V == pytest.approx(theirs, rel=V_REL)
        if not (ok and c.res_free <= RESID_TOL):
            bad.append(c)
    assert not bad, "\n" + _table(bad)
