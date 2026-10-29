"""The ORC sail force model for a main and jib (ORC VPP Documentation 2026,
§5; tables in boats/private/orc/orc2026_sails.yaml, kept out of git:
copyright ORC).

**Full-scale coefficients.** The ORC fitted the sail coefficients, the
depowering law and the effective-height constants to full-size yachts, at
Reynolds numbers 10-100 times an IOM's (~1e5). They are used here unchanged,
as a reference to compare with the sails CFD, not as a calibrated IOM model.

One call is one apparent wind: the heeled, mast-normal wind of
`frames.heeled_wind` (ORC eq. 7.2-7.3; heel enters the sail model only
through that wind, since the PHI_UP correction was dropped in 2023, §5.5).

1. Each sail's maximum lift CL_i and parasitic drag CD0_i at β (§5.2 tables),
   its blanketing bk_i (§5.6) and its area A_i.
2. The sail set: CLmax and CD0max (eq. 5.36-5.37), KPP (5.41), the effective
   height heff (5.42-5.45) and CE = KPP + A_ref/(π heff²) (5.46).
3. Depowering by `flat` (5.47-5.48, with fcdmult). The centre of effort
   height (5.39) is lowered by the twist function (5.40). ORC 2026 has no
   separate twist variable, and an IOM changes rig instead of reefing, so
   reef = 1.
4. Windage of the mast and rigging (§5.3, Table 5.12, eq. 5.27): drag along
   the apparent wind. Hull windage is a separate component.

Sail sets (`sails=`):

* "upwind": main and jib (Tables 5.2 and 5.5). ORC runs it at every true
  wind angle (§7.2).
* "downwind": main and the jib goose-winged. This is ORC's "jib downwind" in
  the No Spinnaker configuration (§5.2.2, p. 47): area 1.064 A_jib with the
  asymmetric-spinnaker coefficients, on a pole (Table 5.10) if
  `Rig.jib_pole`, else on the centreline (5.9). ORC uses it from TWA 60° to
  180° and keeps the faster polar. The IOM jib boom is taken as the pole.

Project choices where ORC is silent (all flagged in the docstrings):
PCHIP interpolation in β; tables held at their end values outside their
range; A_fore = I·J/2; for the downwind set, ORC's spinnaker effective
height (5.44) with b_max = b + HBI, fcdj = 0, no twist lowering, and the
jib's own centroid as its centre of effort; x_ce (ORC has no yaw balance);
one wind for all parts (ORC gives each windage element the wind at its own
height).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cache, lru_cache

import numpy as np
import yaml
from scipy.interpolate import PchipInterpolator

from .. import config
from ..geometry.sails import SailSpec, _chord
from . import frames

DATA = config.home() / "boats" / "private" / "orc" / "orc2026_sails.yaml"

RHO_AIR = 1.225  # kg/m³, ISA sea level (ORC gives no value)
FLAT_MIN = 0.53  # §5.1.3 p. 40: FlatMIN = 0.53 · Flat8 (Flat8 = flat at TWS 8 kt, TWA 52°)
CEH_MAIN_ADD = 0.024  # eq. 5.7: main CEH = area centroid above the boom + 0.024 P
# Eq. 5.40 as printed divides (overlap − 0.9) by 0.6. Fig. 5.14 (p. 56) is
# reproduced by 1.8 instead; see twist_factor.
TWIST_OVERLAP_SCALE = 0.6


# --- tables -------------------------------------------------------------------


@dataclass
class Table:
    """One sail's 2-D coefficients against β [deg] (a §5.2 table), PCHIP in β
    (ORC doesn't state its interpolation; PCHIP is C¹, passes through the
    tabulated values and doesn't overshoot them). Held at the end values
    outside the table."""

    kp: float  # quadratic viscous drag coefficient (eq. 5.41)
    beta: np.ndarray
    cl: np.ndarray
    cd: np.ndarray
    _cl: PchipInterpolator = field(init=False, repr=False)
    _cd: PchipInterpolator = field(init=False, repr=False)

    def __post_init__(self):
        self._cl = PchipInterpolator(self.beta, self.cl)
        self._cd = PchipInterpolator(self.beta, self.cd)

    def __call__(self, beta: float) -> tuple[float, float]:
        b = min(max(beta, self.beta[0]), self.beta[-1])
        return float(self._cl(b)), float(self._cd(b))


@lru_cache(maxsize=1)
def tables() -> dict:
    """The transcribed ORC tables (`DATA`)."""
    if not DATA.is_file():
        raise FileNotFoundError(f"no ORC 2026 sail tables at {DATA}: they are copyright ORC, so they live in "
                                "boats/private/orc/ (git-ignored), not in the repo")
    return yaml.safe_load(DATA.read_text())


@cache
def table(name: str, level: str = "") -> Table:
    """`name` main | jib (with `level` low | high) | asym_pole | asym_cl."""
    t = tables()[name]
    c = t[level] if level else t
    return Table(t["kp"], np.array(t["beta"], float), np.array(c["cl"], float), np.array(c["cd"], float))


@cache
def _curve(name: str, x: str) -> PchipInterpolator:
    t = tables()[name]
    return PchipInterpolator(np.array(t[x], float), np.array(t["value"], float))


def fcdmult(flat: float) -> float:
    """Drag multiplier along the depowering curve (table under Fig. 5.16,
    p. 58; PCHIP, held below flat 0.1)."""
    return float(_curve("fcdmult", "flat")(min(max(flat, 0.1), 1.0)))


def kheff(awa: float) -> float:
    """Effective span factor against AWA (Fig. 5.15, p. 57, digitised; 1.45 at
    20° and 0.80 from 80°, as the text says). Held at 0.80 beyond 90°."""
    return float(_curve("kheff", "awa")(min(max(awa, 0.0), 90.0)))


def fcoef(frac: float) -> float:
    """Fractionality coefficient for a backstay without runners (eq. 5.5)."""
    return math.sqrt(math.sin(math.pi / 0.6 * min(0.3, max(0.0, 1.0 / frac - 1.0))))


def coefficients(sail: str, level: str, beta: float, frac: float = 1.0) -> tuple[float, float, float]:
    """(CL, CD0, kp) of the main or jib with the `level` low | high | medium
    set (Tables 5.2-5.6). ORC 2026 solves the VPP with the low set and adds
    the rig's adjustability afterwards as a speed credit (§5.1.2, p. 39); an
    IOM (backstay, forestay fixed while racing) is L in Tables 5.3 and 5.6
    anyway. Medium blends low and high by fcoef (eq. 5.6 main, 5.9 jib)."""
    if level != "medium":
        t = table(sail, level)
        return *t(beta), t.kp
    lo, hi, f = table(sail, "low")(beta), table(sail, "high")(beta), fcoef(frac)
    w = f / 2 if sail == "main" else 1.0 - f  # weight of the high set
    return (1 - w) * lo[0] + w * hi[0], (1 - w) * lo[1] + w * hi[1], table(sail, "low").kp


# --- the rig --------------------------------------------------------------------


@dataclass(frozen=True)
class Rig:
    """The sail plan the ORC model needs (ORC symbols, Fig. 5.1). Heights in m
    above the waterline, x in m aft of the bow (boat frame), upright."""

    A_main: float  # main area (planform integral)
    z_main: float  # main area centroid
    x_main: float
    A_jib: float
    z_jib: float
    x_jib: float
    P: float  # main hoist (luff height)
    E: float  # main foot
    BAS: float  # boom above the sheer at the mast
    HBI: float  # sheer (base of I) above the waterline
    I: float  # jib head (hounds) above the sheer; ORC's IG is the same here
    J: float  # forestay at the sheer to the front of the mast
    LPG: float  # jib luff perpendicular (clew to luff)
    roach: float  # main ROACH parameter (eq. 5.3)
    main_shadow: float  # m², main area in the mast's shadow above the hounds (§5.2.1, p. 44)
    mast_x: float
    mast_d: float  # m, round section: MDL = MDT
    rigging_d: float  # m, summed diameter of the stays (ORC: four stays, eq. 5.32)
    spreaders: bool = False  # rigging drag × 1.2 (eq. 5.34)
    jib_pole: bool = True  # the jib boom holds the clew out goose-winged (ORC: SPL > 0 or WPL > 0.9 J)

    @property
    def frac(self) -> float:
        """Fractionality I / (P + BAS) (§5.4.3)."""
        return self.I / (self.P + self.BAS)

    @property
    def overlap(self) -> float:
        """LPG / J (§5.4.3)."""
        return self.LPG / self.J

    @property
    def A_fore(self) -> float:
        """Foretriangle area I·J/2 (ORC uses A_fore in §5.6.2 without defining
        it; the usual definition, an assumption)."""
        return 0.5 * self.I * self.J

    @property
    def A_main_rated(self) -> float:
        """Main area less the mast shadow above the hounds (§5.2.1)."""
        return self.A_main - self.main_shadow

    @property
    def z_ceh_main(self) -> float:
        """ORC main centre of effort: the area centroid + 0.024 P (eq. 5.7)."""
        return self.z_main + CEH_MAIN_ADD * self.P

    @property
    def tf(self) -> float:
        """0.16 Zm/P + 0.94, Zm the main centroid above the boom (§5.3 p. 53;
        eq. 5.44 writes it with CEH_main − 0.024 P)."""
        return 0.16 * (self.z_main - self.HBI - self.BAS) / self.P + 0.94

    @property
    def EHM(self) -> float:
        """Static effective height max(P·tf + BAS, I, ISP) (§5.3, p. 53; ISP = 0)."""
        return max(self.P * self.tf + self.BAS, self.I)

    @property
    def b(self) -> float:
        """Highest point of the sail plan above the sheer: the main head, or the
        mean of both heads if the jib's is higher (§5.4.3, p. 57)."""
        return self.P + self.BAS if self.I <= self.P + self.BAS else 0.5 * (self.P + self.BAS + self.I)


def orc_roach(P: float, MQW: float, MHW: float, MTW: float, MUW: float, MHB: float) -> float:
    """ORC main roach from the girths at 1/4, 1/2, 3/4 and 7/8 height and the
    head (eq. 5.3-5.4); 0 for a triangle, negative values count as 0."""
    upper = P / 8 * (MQW + 2 * MHW + 1.5 * MTW + MUW + 0.5 * MHB)
    return max(0.0, (upper / (0.375 * P * MQW) - 1.0) / 0.844)


def planform(spec: SailSpec) -> tuple[float, float, float]:
    """(area, z, x) of a sail's flat planform: horizontal chords by the law of
    geometry/sails.py from a (raked) luff, integrated over the height."""
    t, w = np.polynomial.legendre.leggauss(8)  # exact for the quartic integrands
    eta, w = 0.5 * (t + 1.0), 0.5 * w
    c = _chord(spec, eta)
    x_luff = spec.tack[0] + eta * spec.luff * math.tan(math.radians(spec.rake))
    m = float(w @ c)
    return spec.luff * m, spec.tack[2] + spec.luff * float(w @ (eta * c)) / m, float(w @ ((x_luff + 0.5 * c) * c)) / m


MAIN_TACK = (0.406, 0.0, 0.14)  # geometry.sails.iom_a_rig's: the mast at 0.40 m on a deck 0.06 m up


def iom_a_specs(main_tack=MAIN_TACK, jib_tack=None) -> tuple[SailSpec, SailSpec]:
    """Main and jib planforms of `geometry.sails.iom_a_rig` (the same numbers,
    which that function keeps inline; boats/private/orc/test_vpp_sails_orc.py
    checks they agree). `main_tack`: where the boom meets the mast (the
    mast's centre 6 mm ahead); `jib_tack` default 0.08 m from the bow,
    0.04 m below the main's tack, as on geometry/sails.py's flat deck."""
    mx, _, mz = (float(v) for v in main_tack)
    jt = (0.08, 0.0, round(mz - 0.04, 12)) if jib_tack is None else tuple(float(v) for v in jib_tack)
    mast_x = round(mx - 0.006, 12)  # rounded so decimal tacks give geometry.sails' numbers exactly
    main = SailSpec(luff=1.60, foot=0.355, half=0.240, head=0.03, tack=(mx, 0.0, mz))
    jib = SailSpec(luff=1.25, foot=0.380, half=0.200, head=0.02, tack=jt,
                   rake=math.degrees(math.atan2(mast_x - jt[0] - 0.03, 1.25)))
    return main, jib


def iom_a_rig_geometry(main_tack=MAIN_TACK, jib_tack=None, sheer: float | None = None, mast_d: float = 0.010,
                       rigging_d: float = 4 * 0.0006, spreaders: bool = False, jib_pole: bool = True) -> Rig:
    """The IOM A rig of geometry/sails.py as an ORC `Rig`, placed by the
    main's tack (boom and mast, boat frame [m]) and the jib's (`iom_a_specs`).
    `sheer`: the deck at the mast, ORC's base of I and BAS (HBI); default
    0.08 m below the main's tack, the boom height of geometry/sails.py.

    Girths are the horizontal chords at 1/4, 1/2, 3/4 and 7/8 of the main's
    height (ORC measures them from leech points to the luff; the same for a
    vertical luff). `rigging_d` is an estimate: four stays of 0.6 mm."""
    main, jib = iom_a_specs(main_tack, jib_tack)
    mast_x = round(main.tack[0] - 0.006, 12)
    deck = round(main.tack[2] - 0.08, 12) if sheer is None else float(sheer)
    A_m, z_m, x_m = planform(main)
    A_j, z_j, x_j = planform(jib)
    rake = math.radians(jib.rake)
    I = jib.tack[2] + jib.luff - deck
    forestay_x = jib.tack[0] - (jib.tack[2] - deck) * math.tan(rake)  # the jib luff at the sheer
    girths = _chord(main, np.array([0.25, 0.5, 0.75, 0.875, 1.0]))
    # main area within 1.5 mast diameters of the luff, above the hounds (§5.2.1 "mast shadow")
    eta = np.linspace(min(1.0, (deck + I - main.tack[2]) / main.luff), 1.0, 401)
    shadow = main.luff * float(np.trapezoid(np.minimum(_chord(main, eta), 1.5 * mast_d), eta))
    return Rig(A_main=A_m, z_main=z_m, x_main=x_m, A_jib=A_j, z_jib=z_j, x_jib=x_j,
               P=main.luff, E=main.foot, BAS=main.tack[2] - deck, HBI=deck, I=I,
               J=mast_x - 0.5 * mast_d - forestay_x, LPG=jib.foot * math.cos(rake),
               roach=orc_roach(main.luff, *map(float, girths)), main_shadow=shadow,
               mast_x=mast_x, mast_d=mast_d, rigging_d=rigging_d, spreaders=spreaders, jib_pole=jib_pole)


# --- the sail-set model ---------------------------------------------------------------


def blanket_jib(rig: Rig, beta: float) -> float:
    """Jib blanketing bk(β) (§5.6.2): the part of the jib outside the
    foretriangle loses its force from β 135° to 180°."""
    if beta <= 135.0:
        return 1.0
    f_j = (rig.A_jib - min(rig.A_jib, rig.A_fore)) / rig.A_jib
    return 1.0 - f_j * (beta - 135.0) / 45.0


def eff_span_corr(roach: float, frac: float, overlap: float) -> float:
    """Effective span coefficient from the sail plan (eq. 5.42)."""
    return 1.1 + 0.08 * (roach - 0.2) + 0.5 * (0.68 + 0.31 * frac + 0.075 * overlap - 1.1)


def heff_upwind(rig: Rig, beta: float) -> float:
    """Effective rig height with the jib: eff_span_corr · kheff(β) · (b + HBI)
    (eq. 5.43, 5.45)."""
    return eff_span_corr(rig.roach, rig.frac, rig.overlap) * kheff(beta) * (rig.b + rig.HBI)


def heff_downwind(rig: Rig) -> float:
    """Effective rig height of a spinnaker set, (P·tf + BAS + HBI) · reef
    (eq. 5.44-5.45, reef = 1). ORC leaves b_max undefined; b_max = b + HBI
    is assumed, which makes heff the main head height scaled by tf. Used for
    the goose-winged jib, which ORC models as a spinnaker-type sail
    (assumption: ORC doesn't say which heff the jib downwind uses)."""
    return rig.P * rig.tf + rig.BAS + rig.HBI


def twist_factor(rig: Rig, flat: float, overlap_scale: float = TWIST_OVERLAP_SCALE) -> float:
    """The twist function (eq. 5.40): ZCE above the sheer is multiplied by
    1 − [0.5(1 − flat) + 0.902(1 − flat)(1 − frac)] · [1 − (overlap − 0.9)/s].

    s = 0.6 as printed. FLAG: Fig. 5.14 (p. 56) is reproduced with s = 1.8,
    not 0.6 (with 0.6 a 150 % genoa would not lower its ZCE at all, but the
    figure shows it does). For the IOM's overlap of ~1.14 the overlap term is
    0.60 with 0.6 and 0.87 with 1.8."""
    f = 1.0 - flat
    return 1.0 - (0.5 * f + 0.902 * f * (1.0 - rig.frac)) * (1.0 - (rig.overlap - 0.9) / overlap_scale)


@dataclass(frozen=True)
class Part:
    """One part's force: lift L normal to and drag D along the apparent wind
    [N], acting at height z above the waterline and x aft of the bow."""

    L: float
    D: float
    z: float
    x: float


@dataclass
class SailForces:
    """Total lift L and drag D [N] (sails, mast and rigging windage); z_ce,
    x_ce [m] the centre of the total force, its parts weighted by force
    magnitude (eq. 5.39 extended to the windage parts; the heeling moment
    from z_ce is then exact to ~0.2 %; `info["M_heel"]` and `parts` are
    exact). CL, CD are the sail set's alone (eq. 5.47-5.48, on A_ref)."""

    L: float
    D: float
    z_ce: float
    x_ce: float
    CL: float
    CD: float
    parts: dict[str, Part]
    info: dict


def forces(rig: Rig, aws: float, awa: float, flat: float = 1.0, rho: float = RHO_AIR, sails: str = "upwind",
           level: str = "low") -> SailForces:
    """ORC sail, mast and rigging forces for the apparent wind `aws` [m/s] at
    `awa` [deg from the centreline] in the heeled mast-normal plane
    (`frames.heeled_wind`). L is normal to the wind and D along it; convert
    with `frames.lift_drag_to_centreline` and `frames.rig_to_course`.

    `flat` in (0, 1]: CL = flat · CLmax (eq. 5.48); ORC's lower limit is
    FLAT_MIN · Flat8, left to the solver. `sails` "upwind" | "downwind"
    (module docstring); `level` the main and jib coefficient set
    (`coefficients`). Port tack; the mirror image for starboard (|awa|).

    The centre of effort is eq. 5.39 as printed: its denominator is
    |Σ (CL_i, CD0_i) bk_i A_i|, not Σ |(CL_i, CD0_i)| bk_i A_i, so it is not
    a convex mean. Where the main and jib forces point different ways it
    lies above the weighted mean: for the A rig's upwind set by 0 % at β
    15-40° but 2-4 % at β 80-120° and at 7° (heights above the sheer)."""
    if not 0.0 < flat <= 1.0:
        raise ValueError(f"flat must be in (0, 1], got {flat}")
    if sails not in ("upwind", "downwind"):
        raise ValueError(f"sails must be 'upwind' or 'downwind', got {sails!r}")
    beta = min(abs(awa), 180.0)
    q = 0.5 * rho * aws**2

    cl_m, cd_m, kp_m = coefficients("main", level, beta, rig.frac)
    A_m, bk_m = rig.A_main_rated, 1.0  # §5.6.1: bk = 1 without a mizzen staysail
    if sails == "upwind":
        cl_j, cd_j, kp_j = coefficients("jib", level, beta, rig.frac)
        A_j, bk_j, heff = rig.A_jib, blanket_jib(rig, beta), heff_upwind(rig, beta)
    else:
        t = table("asym_pole" if rig.jib_pole else "asym_cl")
        (cl_j, cd_j), kp_j = t(beta), t.kp
        A_j, bk_j, heff = tables()["jib_downwind_area_factor"] * rig.A_jib, 1.0, heff_downwind(rig)
    A_ref = A_m + A_j
    w_m, w_j = bk_m * A_m / A_ref, bk_j * A_j / A_ref

    CLmax = cl_m * w_m + cl_j * w_j  # eq. 5.36
    CD0max = cd_m * w_m + cd_j * w_j  # eq. 5.37
    kpp_cl2 = kp_m * cl_m**2 * w_m + kp_j * cl_j**2 * w_j  # KPP · CLmax² (eq. 5.41)
    k_ind = A_ref / (math.pi * heff**2)  # eq. 5.35
    # jib share of the parasitic drag; 0 for the jib downwind, a spinnaker-type sail (assumption)
    fcdj = cd_j * w_j / CD0max if sails == "upwind" else 0.0
    fm = fcdmult(flat)
    CL = flat * CLmax  # eq. 5.48
    CD = CD0max * (flat * fm * fcdj + 1.0 - fcdj) + (kpp_cl2 + k_ind * CLmax**2) * flat**2 * fm  # eq. 5.47

    # centre of effort: eq. 5.39 on heights above the sheer (ORC's datum, eq. 5.56), then eq. 5.40
    g_m, g_j = math.hypot(cl_m, cd_m) * w_m, math.hypot(cl_j, cd_j) * w_j
    zs = ((rig.z_ceh_main - rig.HBI) * g_m + (rig.z_jib - rig.HBI) * g_j) / math.hypot(CLmax, CD0max)
    tw = twist_factor(rig, flat) if sails == "upwind" else 1.0  # no twist lowering downwind (assumption)
    z_s = rig.HBI + zs * tw
    x_s = (rig.x_main * g_m + rig.x_jib * g_j) / (g_m + g_j)  # project: ORC has no x_ce

    # windage, Table 5.12 and eq. 5.27 (|cos β| = cos β · sgn(90 − β)); round mast: front = side area
    c, s = abs(math.cos(math.radians(beta))), math.sin(math.radians(beta))
    wd = tables()["windage"]
    cd_mast = wd["mast_sail"]["cd_front"] * c + wd["mast_sail"]["cd_side"] * s
    cd_rig = wd["rigging"]["cd"] * (1.0 + (wd["rigging"]["spreader_factor"] if rig.spreaders else 0.0)) * (c + s)
    parts = {
        "sails": Part(q * A_ref * CL, q * A_ref * CD, z_s, x_s),
        "mast": Part(0.0, q * cd_mast * rig.mast_d * rig.EHM, rig.HBI + 0.5 * rig.EHM, rig.mast_x),
        "rigging": Part(0.0, q * cd_rig * rig.I * rig.rigging_d, rig.HBI + 0.5 * rig.I, rig.mast_x),
    }

    L = sum(p.L for p in parts.values())
    D = sum(p.D for p in parts.values())
    F = {k: math.hypot(p.L, p.D) for k, p in parts.items()}
    Ft = sum(F.values())
    z_ce = sum(p.z * F[k] for k, p in parts.items()) / Ft if Ft > 0 else z_s
    x_ce = sum(p.x * F[k] for k, p in parts.items()) / Ft if Ft > 0 else x_s
    drive, heel_force = frames.lift_drag_to_centreline(L, D, beta)
    CR, CH = frames.lift_drag_to_centreline(CL, CD, beta)  # eq. 5.49-5.50
    M_heel = sum(frames.lift_drag_to_centreline(p.L, p.D, beta)[1] * p.z for p in parts.values())
    info = {
        "sails": sails, "beta": beta, "q": q, "A_ref": A_ref, "flat": flat,
        "CL_main": cl_m, "CD0_main": cd_m, "CL_jib": cl_j, "CD0_jib": cd_j, "bk_jib": bk_j,
        "CLmax": CLmax, "CD0max": CD0max, "KPP": kpp_cl2 / CLmax**2 if CLmax**2 > 1e-12 else float("nan"),
        "heff": heff, "kheff": kheff(beta) if sails == "upwind" else float("nan"),
        "CDi": k_ind * CL**2 * fm, "CE": (kpp_cl2 / CLmax**2 if CLmax**2 > 1e-12 else 0.0) + k_ind,
        "fcdj": fcdj, "fcdmult": fm, "z_ce_flat1": rig.HBI + zs, "twist": tw,
        "CR": CR, "CH": CH, "drive": drive, "heel_force": heel_force, "M_heel": M_heel,
    }
    return SailForces(L, D, z_ce, x_ce, CL, CD, parts, info)
