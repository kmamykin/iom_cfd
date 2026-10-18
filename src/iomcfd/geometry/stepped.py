"""Stepped (Kline-Fogleman) sections cut from a smooth base section.

A backward-facing step drops the surface towards the camber line. Behind a
step the surface is the base section with its thickness scaled down, so the
part behind the step keeps the base shape and the trailing edge stays sharp:

    y(x) = camber(x) +/- half_thickness(x) * F(x)
    F(x) = 1 - (sum of the depths of the steps ahead of x)

Every step is cut into both surfaces at the same x/c: a fin works on both
tacks, so the sections are symmetric (the one-sided hobby KFm1/KFm2 were
dropped).

Spec strings (a study's `foil:` value); the number is the steps per surface:

    stair1:naca0009:x=0.5,d=0.3  one step on each surface (the hobby KFm4)
    stair5:naca0009              5 steps of 0.2 mm on each surface
    stair10:naca0009             10 steps of 0.1 mm on each surface

The hobby KFm numbers are a catalogue (KFm4 = variant 4, one step on top and
one below), not step counts, hence this project's own names. stair5 and
stair10 are equal steps, evenly spaced from x to x_end; their heights are
fractions of the chord, the mm above are for the 80 mm fin chord.

Options (default):
  x       stair1: step position x/c (0.5); stair5/10: first step (0.3)
  d       stair1: depth, the fraction of the local half-thickness removed (0.3)
  h       height of every step as a fraction of the chord (stair5 0.0025,
          stair10 0.00125); for stair1 instead of d
  x_end   stair5/10: last step x/c (0.9)
  angle   step face to the chord line, deg (90 = vertical face)
  r_lip   fillet radius at the top of the face, fraction of the step height (0.05)
  r_foot  fillet radius at the foot of the face, fraction of the step height (0.25)

On an 80 mm NACA 0009, stair10 (10 x 0.1 mm) and stair5 (5 x 0.2 mm) each
leave about half the thickness near the trailing edge, like one 1.6 mm
stair1 step at x/c 0.5 with d=0.5. Higher steps than the section can take
(over 90 % of the thickness) are refused.

The radii keep the contour smooth enough for a body-fitted mesh; a 5 %
lip radius on a 1 mm step is 0.05 mm, sharp at model scale. The base can be
any section `foils.load` accepts whose surfaces run monotonically in x from
the LE (symmetric NACA sections, most .dat files).
"""

from __future__ import annotations

import dataclasses
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from .foils import Foil

# steps per surface and default options
STAIRS = {"stair1": (1, {"x": 0.5, "d": 0.3}),
          "stair5": (5, {"x": 0.3, "x_end": 0.9, "h": 0.0025}),
          "stair10": (10, {"x": 0.3, "x_end": 0.9, "h": 0.00125})}
PRESETS = tuple(STAIRS)
OPTIONS = {k: (*(("x", "d", "h") if n == 1 else ("x", "x_end", "h")), "angle", "r_lip", "r_foot")
           for k, (n, _) in STAIRS.items()}
SPEC_RE = re.compile(r"(?i)((?:stair|kfm)\d+):(.+)")  # kfm only to explain the rename


@dataclass
class StepInfo:
    side: str  # 'upper' | 'lower'
    x: float  # x/c of the lip (top of the face)
    depth: float  # fraction of the local half-thickness removed
    height: float  # step height / chord (vertical drop at x)
    r_lip: float = 0.0  # fillet radii / chord at the top and the foot of the face
    r_foot: float = 0.0
    s_lip: tuple[float, float] = (0.0, 0.0)  # Foil parameter range of the lip fillet
    s_foot: tuple[float, float] = (0.0, 0.0)  # ... and of the foot fillet


def is_stepped(spec: str) -> bool:
    return bool(SPEC_RE.fullmatch(str(spec).strip()))


def parse_spec(spec: str) -> tuple[str, str, dict[str, float]]:
    """'stair1:naca0009:x=0.6,d=0.5' -> ('stair1', 'naca0009', {'x': 0.6, 'd': 0.5})."""
    m = SPEC_RE.fullmatch(spec.strip())
    if not m:
        raise ValueError(f"not a stepped section spec: '{spec}'")
    preset, rest = m.group(1).lower(), m.group(2)
    if preset.startswith("kfm"):
        raise ValueError(f"'{spec}': the kfm names are gone: kfm4 is now stair1, kfm5/kfm10 are stair5/stair10")
    if preset not in PRESETS:
        raise ValueError(f"unknown stepped section '{preset}', expected one of {PRESETS}")
    parts = rest.split(":")
    opts: dict[str, float] = {}
    if len(parts) > 1 and "=" in parts[-1]:
        for item in parts.pop().split(","):
            k, _, v = item.partition("=")
            k = k.strip()
            if k not in OPTIONS[preset]:
                raise ValueError(f"'{spec}': unknown option '{k}' for {preset} (options: {', '.join(OPTIONS[preset])})")
            opts[k] = float(v)
    if "d" in opts and "h" in opts:
        raise ValueError(f"'{spec}': give the step's depth d or its height h, not both")
    return preset, ":".join(parts), opts


def from_spec(spec: str, search_dirs: list[Path] | None = None) -> Foil:
    from .foils import load

    preset, base_spec, o = parse_spec(spec)
    base = load(base_spec, search_dirs)
    n, dflt = STAIRS[preset]
    o = {**dflt, **o}
    xs = np.linspace(o["x"], o.get("x_end", o["x"]), n)
    if "d" in o and "h" not in o:
        steps = [(float(xs[0]), o["d"])]
    else:
        S = _Surfaces(base)
        steps = [(float(x), o["h"] / float(S.half_thickness(x))) for x in xs]  # depth that gives height h
    return stepped(base, steps, angle=o.get("angle", 90.0), r_lip=o.get("r_lip", 0.05),
                   r_foot=o.get("r_foot", 0.25), name=f"{preset} {base.name} ({spec})")


# ---------------------------------------------------------------------------


class _Surfaces:
    """Camber line and half-thickness of a smooth base section (dense tables)."""

    def __init__(self, base: Foil, n: int = 8000):
        u = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
        self.base = base
        self.up = base.point(base.s_le * (1 - u))  # LE -> TE
        self.lo = base.point(base.s_le + (base.perimeter - base.s_le) * u)
        if np.any(np.diff(self.up[:, 0]) < 0) or np.any(np.diff(self.lo[:, 0]) < 0):
            raise ValueError(f"{base.name}: x is not monotonic along a surface; cannot step it")
        self.symmetric = bool(np.allclose(self.up[:, 0], self.lo[:, 0], rtol=0, atol=1e-12)
                              and np.allclose(self.up[:, 1], -self.lo[:, 1], rtol=0, atol=1e-12))

    def y(self, x, sign: int, F: float):
        yu = np.interp(x, self.up[:, 0], self.up[:, 1])
        yl = np.interp(x, self.lo[:, 0], self.lo[:, 1])
        return 0.5 * (yu + yl) + sign * 0.5 * (yu - yl) * F

    def half_thickness(self, x):
        return 0.5 * (np.interp(x, self.up[:, 0], self.up[:, 1]) - np.interp(x, self.lo[:, 0], self.lo[:, 1]))

    def tangent(self, x: float, sign: int, F: float) -> np.ndarray:
        dx = 1e-5
        t = np.array([2 * dx, self.y(x + dx, sign, F) - self.y(x - dx, sign, F)])
        return t / np.linalg.norm(t)

    def curve(self, x0: float, x1: float, sign: int, F: float, ds: float = 1e-3) -> np.ndarray:
        n = max(8, int(math.ceil((x1 - x0) / ds)) + 1)
        x = np.linspace(x0, x1, n)
        return np.column_stack([x, self.y(x, sign, F)])

    def s_at(self, x: float, side: str) -> float:
        """Base-foil parameter where `side` passes through x."""
        b = self.base
        lo, hi = (0.0, b.s_le) if side == "upper" else (b.s_le, b.perimeter)
        return brentq(lambda s: float(b.point(s)[0]) - x, lo, hi, xtol=1e-14)


def _fillet(c: np.ndarray, a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """Circular arc of radius r replacing the corner at c, where the contour
    turns from direction a to direction b (unit vectors). Returns the arc
    points from the tangent point on the incoming line to the one on the
    outgoing line."""
    theta = math.acos(float(np.clip(a @ b, -1.0, 1.0)))
    if r <= 0 or theta < 1e-9:
        return c[None, :].copy()
    T = r * math.tan(theta / 2)
    p1 = c - a * T
    turn = math.copysign(1.0, a[0] * b[1] - a[1] * b[0])  # +1 = left (CCW)
    centre = p1 + r * turn * np.array([-a[1], a[0]])
    a1 = math.atan2(*(p1 - centre)[::-1])
    n = max(5, int(math.ceil(theta / (math.pi / 2) * 16)) + 1)
    ang = a1 + turn * theta * np.linspace(0, 1, n)
    return centre + r * np.column_stack([np.cos(ang), np.sin(ang)])


def _side_pieces(S: _Surfaces, side: str, steps: list[tuple[float, float]], angle: float,
                 r_lip: float, r_foot: float) -> tuple[list[np.ndarray], list[StepInfo]]:
    """Contour pieces LE->TE of one stepped surface. The list starts with the
    point where the smooth forward piece ends (the first lip fillet's start);
    consecutive pieces share their end point exactly."""
    sign = 1 if side == "upper" else -1
    pieces: list = [None]
    infos = []
    F = 1.0
    phi = math.radians(angle)
    if not 30.0 <= angle <= 90.0:
        raise ValueError(f"step face angle must be 30-90 deg, got {angle}")
    x_prev = None
    for xk, dk in steps:
        if not 0.05 <= xk <= 0.95 or dk <= 0:
            raise ValueError(f"step at x/c={xk} with depth {dk}: need 0.05 <= x <= 0.95 and depth > 0")
        F1 = F - dk
        if F1 < 0.1:
            raise ValueError(f"steps on the {side} surface remove {1 - F1:.2f} of the thickness (max 0.9)")
        h = float(S.half_thickness(xk)) * dk
        lip = np.array([xk, float(S.y(xk, sign, F))])
        a = S.tangent(xk, sign, F)
        if angle == 90.0:
            xf = xk
        else:
            g = lambda x: sign * (float(S.y(x, sign, F1)) - lip[1]) + (x - xk) * math.tan(phi)  # noqa: E731
            xf = brentq(g, xk, xk + 10 * h / math.tan(phi) + 1e-6, xtol=1e-14)
        foot = np.array([xf, float(S.y(xf, sign, F1))])
        face = foot - lip
        L = float(np.hypot(*face))
        b = face / L
        c = S.tangent(xf, sign, F1)
        arc_lip = _fillet(lip, a, b, r_lip * h)
        arc_foot = _fillet(foot, b, c, r_foot * h)
        if np.hypot(*(arc_lip[-1] - lip)) + np.hypot(*(arc_foot[0] - foot)) >= 0.95 * L:
            raise ValueError(f"step at x/c={xk}: fillet radii too large for a {h:.2e} c step")
        # snap the arc ends onto the neighbouring curves (differences ~1e-8 c)
        arc_lip[0] = (arc_lip[0][0], float(S.y(arc_lip[0][0], sign, F)))
        arc_foot[-1] = (arc_foot[-1][0], float(S.y(arc_foot[-1][0], sign, F1)))
        if x_prev is not None:
            if arc_lip[0][0] <= x_prev + 2 * h:
                raise ValueError(f"steps on the {side} surface are too close together at x/c={xk}")
            pieces.append(S.curve(x_prev, arc_lip[0][0], sign, F))
        else:
            pieces[0] = arc_lip[0]  # where the smooth forward piece ends
        n_face = max(8, int(math.ceil(L / max(h / 40, 1e-5))) + 1)
        face_pts = arc_lip[-1] + np.linspace(0, 1, n_face)[:, None] * (arc_foot[0] - arc_lip[-1])
        pieces += [arc_lip, face_pts, arc_foot]
        infos.append(StepInfo(side=side, x=xk, depth=dk, height=h, r_lip=r_lip * h, r_foot=r_foot * h))
        F, x_prev = F1, float(arc_foot[-1][0])
    if x_prev is not None:
        pieces.append(S.curve(x_prev, 1.0, sign, F))
    # make consecutive pieces share their end points exactly
    for i in range(2, len(pieces)):
        pieces[i][0] = pieces[i - 1][-1]
    return pieces, infos


def stepped(base: Foil, steps: list[tuple[float, float]], angle: float = 90.0,
            r_lip: float = 0.05, r_foot: float = 0.25, name: str | None = None) -> Foil:
    """Cut the same steps, [(x/c, depth), ...], into both surfaces of `base`."""
    if not steps:
        raise ValueError("no steps")
    S = _Surfaces(base)
    up, up_info = _side_pieces(S, "upper", sorted(steps), angle, r_lip, r_foot)
    if S.symmetric:  # mirror the upper surface: exactly symmetric, point for point
        lo = [q * np.array([1.0, -1.0]) for q in up]
        lo_info = [dataclasses.replace(i, side="lower") for i in up_info]
    else:
        lo, lo_info = _side_pieces(S, "lower", sorted(steps), angle, r_lip, r_foot)

    # Smooth forward piece: the base spline from the first upper corner round
    # the LE to the first lower corner.
    s_u, s_l = S.s_at(float(up[0][0]), "upper"), S.s_at(float(lo[0][0]), "lower")
    tau = np.linspace(0, 1, 801)[1:]  # clustered at the LE
    s_fwd = np.concatenate([base.s_le - (base.s_le - s_u) * (1 - np.cos(0.5 * math.pi * tau[::-1])),
                            [base.s_le],
                            base.s_le + (s_l - base.s_le) * (1 - np.cos(0.5 * math.pi * tau))])
    fwd = base.point(s_fwd)
    fwd[0], fwd[-1] = up[0], lo[0]
    te = 0.5 * (base.point(0.0) + base.point(base.perimeter))
    for p, end in ((up, fwd[0]), (lo, fwd[-1])):
        p[1][0] = end
        p[-1][-1] = te

    contour = [q[::-1] for q in reversed(up[1:])] + [fwd] + lo[1:]
    pts = [contour[0]]
    breaks = []
    n = len(contour[0])
    for q in contour[1:]:
        breaks.append(n - 1)
        pts.append(q[1:])
        n += len(q) - 1
    xy = np.vstack(pts)
    foil = Foil(name or f"stepped {base.name}", xy[:, 0], xy[:, 1], breaks=tuple(breaks), base=base)

    # Parameter ranges of each step's fillets, for the mesh generator.
    def s_of(p):
        return float(foil.s_nodes[int(np.argmin(np.hypot(foil.x - p[0], foil.y - p[1])))])

    for pieces, infos in ((up, up_info), (lo, lo_info)):
        for k, info in enumerate(infos):
            # pieces after the forward one: [lip arc, face, foot arc, curve] per step
            arc_lip, arc_foot = pieces[1 + 4 * k], pieces[3 + 4 * k]
            info.s_lip = tuple(sorted((s_of(arc_lip[0]), s_of(arc_lip[-1]))))
            info.s_foot = tuple(sorted((s_of(arc_foot[0]), s_of(arc_foot[-1]))))
    foil.steps = sorted(up_info + lo_info, key=lambda i: i.s_lip[0])
    return foil
