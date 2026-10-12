"""Fluid properties and turbulence inflow conditions.

All SI units. Temperatures in degrees Celsius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

G = 9.80665  # m/s^2


@dataclass(frozen=True)
class Fluid:
    name: str
    rho: float  # kg/m^3
    nu: float  # m^2/s (kinematic viscosity)

    @property
    def mu(self) -> float:
        return self.rho * self.nu


def fresh_water(temp_c: float = 15.0) -> Fluid:
    """Pure water at 1 atm.

    Density from the Tanaka et al. (2001) style fit, viscosity from the
    Vogel equation. Within ~0.1 % of tabulated values over 0-40 C.
    """
    t = temp_c
    rho = 1000.0 * (1.0 - (t + 288.9414) / (508929.2 * (t + 68.12963)) * (t - 3.9863) ** 2)
    mu = 2.414e-5 * 10.0 ** (247.8 / (t + 273.15 - 140.0))
    return Fluid("water", rho, mu / rho)


def sea_water(temp_c: float = 15.0, salinity: float = 35.0) -> Fluid:
    """Approximate sea water (ITTC 7.5-02-01-03 trend, salinity in g/kg).

    Scales the fresh-water values; good to ~0.5 % for 5-30 C, S=30-38.
    For high-accuracy work use the ITTC tables directly.
    """
    fw = fresh_water(temp_c)
    rho = fw.rho + 0.77 * salinity
    nu = fw.nu * (1.0 + 0.00127 * salinity)
    return Fluid("seawater", rho, nu)


def air(temp_c: float = 15.0, pressure: float = 101325.0) -> Fluid:
    """Dry air: ideal gas density, Sutherland viscosity."""
    t = temp_c + 273.15
    rho = pressure / (287.05 * t)
    mu = 1.716e-5 * (t / 273.15) ** 1.5 * (273.15 + 110.4) / (t + 110.4)
    return Fluid("air", rho, mu / rho)


def fluid(name: str, temp_c: float = 15.0) -> Fluid:
    name = name.lower()
    if name in ("water", "freshwater", "fresh_water"):
        return fresh_water(temp_c)
    if name in ("seawater", "sea_water", "sea"):
        return sea_water(temp_c)
    if name == "air":
        return air(temp_c)
    raise ValueError(f"unknown fluid '{name}' (use water, seawater or air)")


# --------------------------------------------------------------------------
# Turbulence inflow


@dataclass(frozen=True)
class TurbulenceInflow:
    k: float  # m^2/s^2
    omega: float  # 1/s
    nut: float  # m^2/s
    ReThetat: float  # transition onset momentum-thickness Reynolds number
    gammaInt: float = 1.0  # intermittency in the freestream


def retheta_t(tu_percent: float) -> float:
    """Langtry-Menter (2009) correlation for zero pressure gradient.

    Tu in percent. Clipped at Tu >= 0.027 % as recommended by Langtry-Menter,
    and ReThetat >= 20.
    """
    tu = max(tu_percent, 0.027)
    if tu <= 1.3:
        val = 1173.51 - 589.428 * tu + 0.2196 / tu**2
    else:
        val = 331.50 * (tu - 0.5658) ** -0.671
    return max(val, 20.0)


def turbulence_inflow(speed: float, nu: float, tu_percent: float, viscosity_ratio: float) -> TurbulenceInflow:
    """Freestream k, omega, nut, ReThetat from intensity and nut/nu ratio."""
    k = 1.5 * (speed * tu_percent / 100.0) ** 2
    nut = nu * viscosity_ratio
    omega = k / nut
    return TurbulenceInflow(k=k, omega=omega, nut=nut, ReThetat=retheta_t(tu_percent))


# --------------------------------------------------------------------------
# Near-wall mesh sizing


def skin_friction(re_x: float) -> float:
    """Schlichting turbulent flat-plate local skin friction (upper estimate)."""
    return (2.0 * math.log10(re_x) - 0.65) ** -2.3


def first_cell_height(speed: float, length: float, nu: float, yplus: float) -> float:
    """Wall-adjacent cell height giving `yplus` at the cell centre.

    Uses the turbulent flat-plate skin friction at Re based on `length`, which
    over-predicts u_tau for laminar/transitional regions (so is conservative).
    OpenFOAM reports y+ at the cell centre, which sits at half the cell height.
    """
    re = max(speed * length / nu, 1e3)
    u_tau = speed * math.sqrt(skin_friction(re) / 2.0)
    return 2.0 * yplus * nu / u_tau


def froude(speed: float, length: float) -> float:
    return speed / math.sqrt(G * length)


def induced_drag(lift, q, span: float, e: float = 0.9, reflection_plane: bool = True):
    """Lifting-line induced drag [N] of a fin of `span` [m] carrying `lift` [N]
    at dynamic pressure `q` [Pa] (scalars or numpy arrays).

    D_i = L^2 / (pi q e b^2) for a free wing. A fin under a hull sees the hull
    as a reflection plane: it behaves as half of a wing of span 2b carrying
    2L, so D_i = L^2 / (2 pi q e b^2). e is the span efficiency (1 for an
    elliptic load; ~0.85-0.95 for a tapered fin). An estimate: heel, the gap
    to the hull and the bulb change the effective span.
    """
    factor = 2.0 if reflection_plane else 1.0
    return lift**2 / (factor * math.pi * q * e * span**2)
