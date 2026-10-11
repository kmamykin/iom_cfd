"""Parametric IOM rig: mainsail, jib (zero-thickness surfaces) and mast.

Sail shape per horizontal section: a NACA 4-digit mean line with camber
`camber` (fraction of chord) at `draft` (fraction of chord aft of the luff),
set at an angle to the centreline that varies linearly from `sheet` at the
foot to `sheet + twist` at the head. Chord varies quadratically through the
foot, half-height and head widths (the IOM class-rule girth measurements).

Default dimensions follow the IOM A rig (class rules 2026): main leech
1615 mm, foot 355 mm, half width 240 mm; jib luff 1325 mm, foot 380 mm.
Boat frame: x aft, y port, z up. Sails are set to starboard for port tack
(wind from port) when `sheet` > 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .stl import Surface, revolve


@dataclass
class SailSpec:
    luff: float  # m, height of the sail (vertical extent along the luff line)
    foot: float  # m, chord at the foot
    half: float  # m, chord at half height
    head: float  # m, chord at the head
    tack: tuple[float, float, float]  # m, (x, y, z) of the luff bottom
    rake: float = 0.0  # deg, luff inclination aft from vertical
    camber: float = 0.08
    draft: float = 0.45
    sheet: float = 10.0  # deg, chord angle to the centreline at the foot (+ = boom to starboard)
    twist: float = 10.0  # deg, extra opening at the head
    n_chord: int = 30
    n_span: int = 40


def _chord(spec: SailSpec, eta: np.ndarray) -> np.ndarray:
    # quadratic through (0, foot), (0.5, half), (1, head)
    a, b, c = spec.foot, spec.half, spec.head
    return a * (1 - eta) * (1 - 2 * eta) + 4 * b * eta * (1 - eta) + c * eta * (2 * eta - 1)


def _camber_line(xi: np.ndarray, m: float, p: float) -> np.ndarray:
    return np.where(xi < p, m / p**2 * (2 * p * xi - xi**2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xi - xi**2))


def sail(spec: SailSpec, name: str) -> Surface:
    eta = np.linspace(0, 1, spec.n_span)
    xi = 0.5 * (1 - np.cos(np.linspace(0, math.pi, spec.n_chord)))
    chords = np.maximum(_chord(spec, eta), 0.01)
    rake = math.radians(spec.rake)
    pts = np.zeros((spec.n_span, spec.n_chord, 3))
    for i, (e, c) in enumerate(zip(eta, chords)):
        z = spec.tack[2] + e * spec.luff
        x_luff = spec.tack[0] + e * spec.luff * math.tan(rake)
        ang = math.radians(spec.sheet + e * spec.twist)
        # local section in (along-chord, camber) coordinates; camber bulges
        # to leeward (towards -y when sheeted to starboard, i.e. sheet > 0)
        sx = xi * c
        sy = -_camber_line(xi, spec.camber, spec.draft) * c * np.sign(spec.sheet or 1.0)
        # rotate the section by the sheeting angle (boom to starboard = -y)
        x = x_luff + sx * math.cos(ang) + sy * math.sin(ang)
        y = spec.tack[1] - sx * math.sin(ang) + sy * math.cos(ang)
        pts[i] = np.column_stack([x, y, np.full_like(x, z)])
    V = pts.reshape(-1, 3)
    tris = []
    nc = spec.n_chord
    for i in range(spec.n_span - 1):
        for j in range(nc - 1):
            a, b, c, d = i * nc + j, i * nc + j + 1, (i + 1) * nc + j + 1, (i + 1) * nc + j
            tris += [(a, b, c), (a, c, d)]
    return Surface(V, np.array(tris, dtype=np.int64), name)


def mast(x: float, z0: float, z1: float, diameter: float = 0.010, rake: float = 0.0, n_theta: int = 16) -> Surface:
    """Closed cylinder (round ends) along z, optionally raked aft."""
    L, R = z1 - z0, 0.5 * diameter
    a = np.linspace(0, math.pi / 2, 6)
    t = np.concatenate([R * (1 - np.cos(a)), np.linspace(R, L - R, 30)[1:-1], L - R * (1 - np.cos(a))[::-1]])
    r = np.concatenate([R * np.sin(a), np.full(28, R), R * np.sin(a)[::-1]])
    r[0] = r[-1] = 0.0
    body = revolve(t, r, n_theta, "mast")  # along +x
    body = body.rotated("y", -90.0)  # x -> z
    body = body.translated((x, 0.0, z0))
    if rake:
        body = body.rotated("y", rake, about=(x, 0.0, z0))
    return body


def iom_a_rig(sheet_main: float = 8.0, sheet_jib: float = 12.0, twist_main: float = 10.0,
              twist_jib: float = 10.0, camber: float = 0.08, deck: float = 0.06,
              mast_x: float = 0.40, jib_tack_x: float = 0.08) -> list[Surface]:
    boom = deck + 0.08
    main = SailSpec(luff=1.60, foot=0.355, half=0.240, head=0.03, tack=(mast_x + 0.006, 0.0, boom),
                    camber=camber, draft=0.45, sheet=sheet_main, twist=twist_main)
    jib = SailSpec(luff=1.25, foot=0.380, half=0.200, head=0.02, tack=(jib_tack_x, 0.0, deck + 0.04),
                   rake=math.degrees(math.atan2(mast_x - jib_tack_x - 0.03, 1.25)),
                   camber=camber, draft=0.40, sheet=sheet_jib, twist=twist_jib)
    return [sail(main, "main"), sail(jib, "jib"), mast(mast_x, deck, boom + 1.62)]
