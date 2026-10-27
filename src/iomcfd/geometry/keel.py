"""Keel sizing from the IOM class rules: hull, fin and bulb of a keel3d-style
parameter set (projects/keel3d/defaults.yaml for the keys).

The bulb holds the lead the keel mass limit leaves after the fin, its
lowest point is at the draft, and the fin spans from the hull bottom to the
top of the bulb. Boat frame, upright: x aft, y port, z up, waterline z = 0.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from . import appendages as ap
from . import foils, hulls

# IOM class rule E.4.1: no transverse dimension over 20 mm except in the lowest 60 mm.
MAX_FIN_THICKNESS = 0.020
BULB_ZONE = 0.060


def bulb_spec(p: dict[str, Any], length: float, x_cg: float, z_axis: float) -> ap.FoilBulbSpec:
    return ap.FoilBulbSpec(section=p["bulb_section"], length=length, x_cg=x_cg, z_axis=z_axis,
                           aspect=float(p["bulb_aspect"]), top=float(p["bulb_top"]), bottom=float(p["bulb_bottom"]),
                           cant=float(p["bulb_cant"]))


def keel_geometry(p: dict[str, Any], z_root: float | None = None) -> dict[str, Any]:
    """Sizes of hull, fin and bulb from the study parameters (upright boat).
    `z_root`: the hull's bottom at the fin's root quarter chord [m] (default:
    the canoe body of the hull_* parameters there)."""
    bulb_mass = float(p["keel_mass"]) - float(p["fin_mass"])
    bulb_volume = bulb_mass / float(p["lead_density"])
    _, _, d_over_l = ap.foil_body_coefficients(p["bulb_section"])
    bulb_length = ap.foil_bulb_length(p["bulb_section"], bulb_volume)
    bulb_d = d_over_l * bulb_length  # of the round bulb with the same section areas
    half_w, half_h, _ = (0.5 * bulb_d * v for v in ap.section_shape(
        float(p["bulb_aspect"]), float(p["bulb_top"]), float(p["bulb_bottom"])))

    hull = hull_spec(p)
    if z_root is None:
        z_root = -float(hulls.canoe_depth(hull, float(p["fin_x"])))  # hull bottom at the root quarter chord
    sweep = math.tan(math.radians(float(p["fin_sweep"])))
    # The bulb's lowest point is at the draft (with cant, the tail's), its
    # centre of mass under the fin's quarter chord at the bulb (plus bulb_x).
    # The sweep moves that point with the bulb's height, so iterate once.
    x_cg = float(p["fin_x"]) + sweep * (z_root + float(p["draft"]) - half_h) + float(p["bulb_x"])
    for _ in range(2):
        xt, zt, _, zb = ap.foil_bulb_lines(bulb_spec(p, bulb_length, x_cg, 0.0))
        z_axis = -float(p["draft"]) - float(zb.min())
        x_qc_bulb = float(p["fin_x"]) + sweep * (z_root - z_axis)
        x_cg = x_qc_bulb + float(p["bulb_x"])
    xt, zt, _, _ = ap.foil_bulb_lines(bulb_spec(p, bulb_length, x_cg, z_axis))
    x_unit, r_unit = ap._foil_radius(p["bulb_section"], len(xt))
    z_top = float(zt[np.argmax(r_unit)])  # top of the bulb's widest section: where the fin's span ends
    zoff = ap.foil_bulb_cg_offset(bulb_spec(p, bulb_length, x_cg, z_axis))
    z_cg = z_axis + zoff  # cant turns the bulb about this point
    # Rule E.4.1: no transverse dimension over 20 mm except in the lowest 60 mm.
    # Where each section is 20 mm wide (upper half: 2 b (1 - (z/h)^n)^(1/n)),
    # with cant; sections narrower than that don't count.
    rr = r_unit / r_unit.max()
    wide = half_w * rr > 0.5 * MAX_FIN_THICKNESS
    if wide.any():
        n, b, h = float(p["bulb_top"]), half_w * rr[wide], half_h * rr[wide]
        z20 = h * (1.0 - (0.5 * MAX_FIN_THICKNESS / b) ** n) ** (1.0 / n)  # above the axis
        _, xc, _ = ap.foil_body_coefficients(p["bulb_section"])
        xi = (x_unit[wide] - xc) * bulb_length  # along the axis from the centre of mass
        cant = math.radians(float(p["bulb_cant"]))
        z20 = z_cg - xi * math.sin(cant) + (z20 - zoff) * math.cos(cant)
        if float(z20.max()) > -float(p["draft"]) + BULB_ZONE + 1e-9:
            raise ValueError(f"bulb wider than 20 mm up to {(float(z20.max()) + float(p['draft'])) * 1e3:.1f} mm "
                             f"above the draft, over the {BULB_ZONE * 1e3:.0f} mm zone of rule E.4.1")

    span = z_root - z_top  # exposed: hull bottom to the top of the bulb
    if span <= 0:
        raise ValueError("no room for the fin between the hull and the bulb")
    root, tip = ap.taper_chords(float(p["fin_mean_chord"]), float(p["fin_taper"]))
    foil = foils.load(p["fin_section"])
    tc = foil.thickness()[0]
    if tc * root > MAX_FIN_THICKNESS:
        raise ValueError(f"fin root {tc * root * 1e3:.1f} mm thick, over the 20 mm of rule E.4.1")
    fin_volume = foil.area() * span * (root**2 + root * tip + tip**2) / 3  # exposed part
    hull_volume, hull_lcb, hull_area = hulls.canoe_displacement(hull)
    return {
        "bulb_mass_kg": bulb_mass,
        "bulb_volume_m3": bulb_volume,
        "bulb_length": bulb_length,
        "bulb_diameter": bulb_d,
        "bulb_width": 2 * half_w,
        "bulb_height": 2 * half_h,
        "bulb_z_axis": z_axis,
        "bulb_x_cg": x_cg,
        "bulb_z_cg": z_cg,
        "bulb_cg_above_draft": z_cg + float(p["draft"]),
        # the fin runs on into the bulb, to its axis (which cant tilts nose up)
        "fin_tip_extension": z_top - z_axis + (x_qc_bulb - x_cg) * math.tan(math.radians(float(p["bulb_cant"])))
        if p["bulb"] else 0.0,
        "fin_z_root": z_root,
        "fin_span": span,
        "fin_root_chord": root,
        "fin_tip_chord": tip,
        "fin_area_m2": float(p["fin_mean_chord"]) * span,
        "fin_aspect_ratio": span / float(p["fin_mean_chord"]),
        "fin_root_thickness": tc * root,
        "fin_tip_thickness": tc * tip,
        # second moment of the root section against a constant-chord fin of the
        # same area (solid section, same t/c: I ~ c^4)
        "fin_root_I_rel": (root / float(p["fin_mean_chord"])) ** 4,
        "fin_volume_m3": fin_volume,
        "fin_wetted_area_m2": foil.perimeter * float(p["fin_mean_chord"]) * span,  # exposed, both sides
        "hull_volume_m3": hull_volume,
        "hull_lcb": hull_lcb,
        "hull_wetted_area_m2": hull_area,
    }


def hull_spec(p: dict[str, Any]) -> hulls.CanoeSpec:
    return hulls.CanoeSpec(
        length=float(p["hull_length"]), beam=float(p["hull_beam"]), draft=float(p["hull_draft"]),
        beam_at=float(p["hull_beam_at"]), draft_at=float(p["hull_draft_at"]),
        entry=float(p["hull_entry"]), run=float(p["hull_run"]), section=float(p["hull_section"]),
    )
