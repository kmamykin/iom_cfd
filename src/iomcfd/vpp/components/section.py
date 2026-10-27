"""A different fin section on a keel3d keel, from 2D polars (foil2d).

keel3d gives the whole keel (hull, fin and bulb) with its own section (the
`reference`, NACA 0007 in the runs so far). Another section changes only the
fin's 2D behaviour, so it is applied as a difference at equal fin lift:

* the fin's lift L_fin = share · S_h / cos φ (its share of keel3d's side
  force, `PolarFit.fin_share`; the fin's lift is normal to its heeled plane)
  gives the section lift coefficient C_l = L_fin / (q c b) on the fin's mean
  chord c and exposed span b;
* drag: + (C_d,new − C_d,ref)(C_l) · q c b, profile drag at equal C_l (the
  induced drag is the planform's, unchanged);
* leeway: the new section needs Δα = α_new − α_ref (C_l) more angle for the
  same lift, so the keel behaves as the reference keel at β_Y − Δα / cos φ.

Both differences come from the polars' rising (pre-stall) branch, linear in
C_l between the computed angles, at the polar speeds (linear in V between
them). Outside the common C_l range or the speeds they are held and the
point flagged. The polars are at their own chord (100 mm in custom-section),
not the fin's: a Reynolds-number mismatch the docstring of the boat file
should state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ...racetime import prestall_branch
from .. import frames
from .base import Loads, State, Wind


@dataclass
class Branch:
    """C_l -> (α, C_d) along one polar's rising branch (α ≥ 0)."""

    cl: np.ndarray
    alpha: np.ndarray
    cd: np.ndarray

    @staticmethod
    def of(aoa, cl, cd) -> "Branch":
        aoa, cl, cd = (np.asarray(v, float) for v in (aoa, cl, cd))
        keep = aoa >= 0
        aoa, cl, cd = aoa[keep], cl[keep], cd[keep]
        idx = prestall_branch(aoa, cl)
        return Branch(cl[idx], aoa[idx], cd[idx])

    def at(self, c: float) -> tuple[float, float, bool]:
        # below the first angle's C_l (≈ 0 at 0°) is not out of range
        out = c < self.cl[0] - 0.02 or c > self.cl[-1] + 1e-12
        c = min(max(c, self.cl[0]), self.cl[-1])
        return float(np.interp(c, self.cl, self.alpha)), float(np.interp(c, self.cl, self.cd)), out


def section_polars(polars: dict, tu: float, resolve):
    """The fin-section polar table at turbulence intensity `tu` [%] from
    {<tu>: {base: [csv], replace: [csv]}} (foil2d results.csv or their
    site/data copies, found by `resolve`; later files replace earlier points
    of the same section, speed and angle, as sectiondesign.cfd_table)."""
    from ...sectiondesign import cfd_table

    entry = next((v for k, v in (polars or {}).items() if math.isclose(float(k), tu)), None)
    if entry is None:
        raise ValueError(f"no section polars for Tu {tu:g} %")
    return cfd_table([resolve(str(f)) for f in entry.get("base") or []],
                     [resolve(str(f)) for f in entry.get("replace") or []], tu=tu)


def deltas(polars, foil: str, reference: str) -> dict[float, tuple[Branch, Branch]]:
    """{speed: (new, reference)} from a polar table (foil, speed, aoa, Cl, Cd)."""
    out = {}
    for v, g in polars.groupby("speed"):
        a, b = g[g["foil"] == foil], g[g["foil"] == reference]
        if a.empty or b.empty:
            continue
        out[float(v)] = (Branch.of(a["aoa"], a["Cl"], a["Cd"]), Branch.of(b["aoa"], b["Cl"], b["Cd"]))
    if not out:
        raise ValueError(f"no speed with polars of both {foil} and {reference}")
    return out


@dataclass
class SectionChange:
    base: object  # a PolarFit (components/keel.py)
    branches: dict[float, tuple[Branch, Branch]]
    chord: float  # the fin's mean chord [m]
    span: float  # the fin's exposed span [m]
    x: float = 0.5  # where the extra drag acts (the fin's quarter chord at mid-span)
    z: float = -0.2
    rho: float = 999.1
    label: str = ""
    _speeds: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        self.name, self.kind, self.attitude = self.base.name, self.base.kind, self.base.attitude
        self.controls, self.covers = getattr(self.base, "controls", ()), getattr(self.base, "covers", frozenset())
        self._speeds = sorted(self.branches)
        self.provenance = f"{getattr(self.base, 'provenance', '')} + section {self.label}"

    def delta(self, cl: float, V: float) -> tuple[float, float, bool]:
        """(Δα [deg], ΔC_d) at |C_l| and V; linear in V, held outside."""
        sp = self._speeds
        out = V < sp[0] - 1e-9 or V > sp[-1] + 1e-9
        Vc = min(max(V, sp[0]), sp[-1])
        vals, out_c = [], False
        for v in sp:
            new, ref = self.branches[v]
            an, dn, o1 = new.at(cl)
            ar, dr, o2 = ref.at(cl)
            vals.append((an - ar, dn - dr))
            out_c |= o1 or o2
        da = float(np.interp(Vc, sp, [v[0] for v in vals]))
        dd = float(np.interp(Vc, sp, [v[1] for v in vals]))
        return da, dd, out or out_c

    def _cl(self, S: float, s: State) -> float:
        share, _ = self.base.share_at(s.heel)
        q = 0.5 * self.rho * max(s.V, 1e-6) ** 2
        return abs(share * S / max(math.cos(math.radians(s.heel)), 0.05)) / (q * self.chord * self.span)

    def loads(self, s: State, w: Wind) -> Loads:
        cosp = max(math.cos(math.radians(s.heel)), 0.05)
        ld = self.base.loads(s, w)
        for _ in range(2):  # Δα depends on the lift it is found at
            da, dd, out = self.delta(self._cl(ld.Y, s), s.V)
            ld = self.base.loads(s.but(leeway=s.leeway - da * math.copysign(1.0, ld.Y or 1.0) / cosp), w)
        cl = self._cl(ld.Y, s)
        da, dd, out = self.delta(cl, s.V)
        q = 0.5 * self.rho * s.V**2
        extra = Loads.at(frames.heeled_point(self.x, 0.0, self.z, s.heel), X=-dd * q * self.chord * self.span)
        total = ld + extra
        total.extrapolated = ld.extrapolated or out
        total.info.update({"fin_cl": cl, "section_dalpha": da, "section_dD": dd * q * self.chord * self.span})
        return total
