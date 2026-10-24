"""Frames, wind triangle and the heeled apparent wind.

Port tack throughout (docs/nomenclature.md; starboard is the mirror image):

* boat frame: x aft, y port, z up, origin at the bow on the waterline
  (docs/geometry.md);
* course frame: x_c forward along the course, y_c horizontal and to windward
  (port), z up;
* heel φ + = to starboard; leeway β_Y + = bow to port of the course;
  β_TW and β_AW are measured from the course, `awa` from the centreline.

Angles in degrees at the interfaces, radians inside.
"""

from __future__ import annotations

import math


def wind_at(tws_ref: float, z: float, z_ref: float, alpha: float) -> float:
    """True wind speed at height z [m] from a power-law profile
    V(z) = V_ref (z / z_ref)^alpha (alpha 0 = uniform wind)."""
    return tws_ref * (max(z, 1e-3) / z_ref) ** alpha


def apparent_wind(tws: float, twa: float, V: float) -> tuple[float, float]:
    """(V_AW, β_AW) from V_TW = tws at β_TW = twa (from the course) and the
    boat speed V_b. Both angles are where the wind comes from."""
    a = math.radians(twa)
    wx = tws * math.cos(a) + V  # component from ahead
    wy = tws * math.sin(a)  # component from windward (port)
    return math.hypot(wx, wy), math.degrees(math.atan2(wy, wx))


def heeled_wind(aws: float, awa_course: float, leeway: float, heel: float) -> tuple[float, float]:
    """The apparent wind a heeled rig sees: the component along the mast is
    dropped (ORC's effective angle, tan β_eff = tan β cos φ). Returns
    (speed, angle from the centreline) in the plane normal to the mast."""
    a = math.radians(awa_course - leeway)
    wx, wy = aws * math.cos(a), aws * math.sin(a) * math.cos(math.radians(heel))
    return math.hypot(wx, wy), math.degrees(math.atan2(wy, wx))


def lift_drag_to_centreline(L: float, D: float, awa: float) -> tuple[float, float]:
    """Lift L (normal to the wind) and drag D (along it) of a sail seeing the
    wind from `awa` (from the centreline, port side) as (forward, to leeward)
    forces in the rig plane: drive L sin β − D cos β, heeling force
    L cos β + D sin β (ORC C_R and C_H, eq. 5.49-5.50)."""
    a = math.radians(awa)
    return L * math.sin(a) - D * math.cos(a), L * math.cos(a) + D * math.sin(a)


def rig_to_course(drive: float, heel_force: float, heel: float, leeway: float) -> tuple[float, float, float]:
    """(X, Y, Z) in the course frame of a force with `drive` forward along the
    centreline and `heel_force` to leeward normal to the heeled mast."""
    p, b = math.radians(heel), math.radians(leeway)
    side = -heel_force * math.cos(p)  # horizontal, + to port
    Z = -heel_force * math.sin(p)
    return drive * math.cos(b) - side * math.sin(b), drive * math.sin(b) + side * math.cos(b), Z


def heeled_point(x: float, y: float, z: float, heel: float) -> tuple[float, float, float]:
    """A point of the upright boat (boat frame) after heeling by φ about the
    x axis at the waterline: the mast head moves to starboard (−y)."""
    p = math.radians(heel)
    return x, y * math.cos(p) - z * math.sin(p), y * math.sin(p) + z * math.cos(p)
