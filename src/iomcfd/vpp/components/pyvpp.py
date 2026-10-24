"""Python-VPP's YD-41 as our components, to cross-check the solver against an
independent VPP: https://github.com/marinlauber/Python-VPP (MIT; its authors
benchmarked it against WinVPP), checked at commit 141ea66 (2026-10-20).

Python-VPP is imported from a checkout only when `load` is called, so this
package does not depend on it.

Python-VPP is 3-DOF (V_b, φ, leeway) with two trim variables, flat and RED,
and port tack implied (all its angles ≥ 0):

* V_b along the course; TWA from the course; leeway + = bow to windward,
  which gives a side force to windward (our β_Y on port tack); heel φ to
  leeward (our + to starboard).
* hydro (HydroMod.update): Fxh = D_h (≥ 0, against the course), Fyh =
  K_sf cos φ (horizontal, to windward), Mxh = RmH(φ) + RmC(φ) + RmV(V_b, φ)
  − K_sf · Rm4: hydrostatic, crew and speed-loss righting moments less the
  appendages' heeling moment (K_sf, its side force before the cos φ).
* aero (AeroMod.update): Fxa = T_a, Fya = F_H cos φ (horizontal, to
  leeward), Mxa = F_H · Z_CE (F_H normal to the mast).
* its balance (VPPMod._equilibrium): Fxh = Fxa, Fyh = Fya, Mxh = Mxa.

In our signs (base.py) that is

    hydro  X = −Fxh, Y = +Fyh, K = (RmH + RmC) − Mxh = K_sf Rm4 − RmV
    sails  X = +Fxa, Y = −Fya, K = +Mxa
    righting RM_φ = RmH(φ) + RmC(φ)

so ΣX = Fxa − Fxh, ΣY = Fyh − Fya and ΣK − RM_φ = Mxa − Mxh: the same three
equations. RmV depends on V_b, which `Righting.at` does not see, so it goes
in the hydro K (M_h,dyn + RM_V of docs/nomenclature.md). Python-VPP has no
vertical force, pitch, yaw or rudder: Z = M = N = 0, so run with yaw off.

Wind: Python-VPP builds its own heeled apparent wind (log profile from 10 m,
cross-course component × cos φ, no leeway). `Wind.tws` is passed as its 10 m
TWS in m/s; z_ref and alpha are ignored.

Trim: State.flat is Python-VPP's flat (same ORC meaning; set flat_min to its
FLAT_MIN = 0.53). RED, its second trim variable, is held at `PyVPPSails.red`:
upwind 2 = full sails, 1-2 furls the jib foot, < 1 reefs the main; for a kite
RED ≤ 1 scales the area by RED². Our solver does not search it.
"""

from __future__ import annotations

import importlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ..solver import Attitude, Boat, Settings
from .base import Loads, State, Wind

PHI_MAX = 35.0  # Python-VPP's default heel limit (VPP.set_analysis phi_max) [deg]


def load(path: str | Path) -> SimpleNamespace:
    """Import Python-VPP from a checkout (its src/ layout) and return the
    parts this adapter and the cross-check use."""
    src = str(Path(path).expanduser().resolve() / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    pkg = importlib.import_module("python_vpp")
    if not Path(pkg.__file__).resolve().is_relative_to(src):
        raise ImportError(f"python_vpp already imported from {pkg.__file__}, not {src}")
    aero, hydro, vpp, yacht, sails, utils = (importlib.import_module(f"python_vpp.{m}") for m in
                                             ("AeroMod", "HydroMod", "VPPMod", "YachtMod", "SailMod", "UtilsMod"))
    return SimpleNamespace(
        VPP=vpp.VPP, AeroMod=aero.AeroMod, HydroMod=hydro.HydroMod,
        Yacht=yacht.Yacht, Keel=yacht.Keel, Rudder=yacht.Rudder, Main=sails.Main, Jib=sails.Jib, Kite=sails.Kite,
        equilibrium=vpp._equilibrium, FLAT_MIN=vpp.FLAT_MIN, RESID_TOL=vpp.RESID_TOL,
        KNOTS=utils.KNOTS_TO_MPS, DATA_DIR=utils.DATA_DIR,
    )


def yd41(pv: SimpleNamespace) -> Any:
    """Python-VPP's YD-41 (its runVPP.py), with the GZ curve read from the
    package data rather than from the working directory."""
    gz = json.loads((pv.DATA_DIR / "righting_moment.json").read_text())
    return pv.Yacht(
        Name="YD41", Lwl=11.90, Vol=6.05, Bwl=3.18, Tc=0.4, WSA=28.20, Tmax=2.30, Amax=1.051, Mass=6500,
        Ff=1.5, Fa=1.5, Boa=4.2, Loa=12.5,
        App=[pv.Keel(Cu=1.00, Cl=0.78, Span=1.90), pv.Rudder(Cu=0.48, Cl=0.22, Span=1.15)],
        Sails=[pv.Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
               pv.Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
               pv.Kite("A2", area=150.0, vce=9.55), pv.Kite("A5", area=110.0, vce=9.0)],
        GZ=gz,
    )


@dataclass
class PyVPPRighting:
    """RM_φ = RmH + RmC: hydrostatic and crew righting moments at heel φ
    (Python-VPP clips φ at 0). No sinkage or trim."""

    yacht: Any

    def rm(self, heel: float) -> float:
        p = max(0.0, heel)
        return float(self.yacht._get_RmH(p)) + float(self.yacht._get_RmC(p))

    def at(self, heel: float, M_ext: float = 0.0, Z_ext: float = 0.0) -> Attitude:
        return Attitude(rm=self.rm(heel))


@dataclass
class PyVPPHydro:
    """Hull, keel and rudder (HydroMod: ORC resistance surfaces, appendage
    friction and lift, induced drag)."""

    hydro: Any  # a python_vpp HydroMod
    righting: PyVPPRighting
    name: str = "hydro"
    kind: str = "hydro"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        Fx, Fy, Mx = self.hydro.update(s.V, s.heel, s.leeway, w.twa, w.tws)
        return Loads(X=-float(Fx), Y=float(Fy), K=self.righting.rm(s.heel) - float(Mx),
                     info={"side_force": float(self.hydro.Ksf)})


@dataclass
class PyVPPSails:
    """Main and one headsail or kite (AeroMod: ORC sail coefficients, hull
    windage), at reef RED = `red`."""

    aero: Any  # a python_vpp AeroMod with its sail set
    red: float
    name: str = "sails"
    kind: str = "aero"
    attitude: bool = False

    def loads(self, s: State, w: Wind) -> Loads:
        Fx, Fy, Mx = self.aero.update(s.V, s.heel, w.tws, w.twa, s.flat, self.red)
        return Loads(X=float(Fx), Y=-float(Fy), K=float(Mx),
                     info={"aws": float(self.aero.aws), "awa": float(self.aero.awa)})


def heel_limit(sail: Any) -> float:
    """Python-VPP's bound on heel for a sail set: PHI_MAX, and a kite's own
    max_heel (21.5° by default)."""
    return min(PHI_MAX, getattr(sail, "max_heel", PHI_MAX))


def boat(pv: SimpleNamespace, yacht: Any, sail: str = "J1", red: float | None = None) -> Boat:
    """Our Boat with Python-VPP's forces: main + `sail`, RED held at `red`
    (default full sail: 2 upwind, 1 for a kite). Yaw off, flat_min =
    Python-VPP's FLAT_MIN, and its heel limit as our heel_max flag. Its heel
    limit is a hard bound in Python-VPP but only a flag here."""
    s = next(x for x in yacht.sails if x.name == sail)
    aero = pv.AeroMod(yacht)
    aero.sails[1], aero.up = s, s.up  # as VPPMod._solve_row
    righting = PyVPPRighting(yacht)
    settings = Settings(yaw=False, flat_min=pv.FLAT_MIN, V_max=10.0, heel_max=heel_limit(s))
    red = (2.0 if s.up else 1.0) if red is None else red
    return Boat([PyVPPHydro(pv.HydroMod(yacht), righting), PyVPPSails(aero, red)], righting, settings)


def residual(pv: SimpleNamespace, b: Boat, w: Wind, V: float, heel: float, leeway: float, flat: float
             ) -> float:
    """Python-VPP's own scaled equilibrium residual (max over Fx, Fy, Mx) at
    a state, for comparison with its RESID_TOL."""
    sails, hydro = b.component("sails"), b.component("hydro")
    r = pv.equilibrium([V, heel, leeway, flat, sails.red], sails.aero, hydro.hydro, w.tws, w.twa)
    return float(max(abs(x) for x in r)) if all(map(math.isfinite, r)) else math.inf
