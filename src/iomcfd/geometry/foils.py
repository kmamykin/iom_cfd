"""2D foil section geometry.

A `Foil` is a closed, unit-chord section with the leading edge at (0, 0) and
a sharp trailing edge at (1, 0). It is stored as one smooth parametric curve
running TE -> upper surface -> LE -> lower surface -> TE, so it can be
re-sampled at any point distribution (needed by the mesh generator).

Sources:
  naca4("2412")           analytic NACA 4-digit (closed TE variant)
  from_dat(path)          Selig or Lednicer coordinate files (UIUC database,
                          airfoiltools.com, XFoil exports, Fusion 360 sketches
                          exported as points...)
  load("naca0009") / load("file:my_section.dat")  string spec used by studies
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar


@dataclass
class Foil:
    name: str
    x: np.ndarray  # closed contour TE->upper->LE->lower->TE, unit chord
    y: np.ndarray

    def __post_init__(self) -> None:
        x, y = np.asarray(self.x, float), np.asarray(self.y, float)
        # Chord-length parametrisation of the closed contour.
        ds = np.hypot(np.diff(x), np.diff(y))
        keep = np.concatenate([[True], ds > 1e-12])
        x, y = x[keep], y[keep]
        s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
        self.x, self.y = x, y
        self._sx = CubicSpline(s, x)
        self._sy = CubicSpline(s, y)
        self._s_total = s[-1]
        # Leading edge = point of minimum x on the spline.
        i_le = int(np.argmin(x))
        lo, hi = s[max(i_le - 2, 0)], s[min(i_le + 2, len(s) - 1)]
        self.s_le = float(minimize_scalar(lambda t: float(self._sx(t)), bounds=(lo, hi), method="bounded").x)

    # -- evaluation --------------------------------------------------------
    @property
    def perimeter(self) -> float:
        return self._s_total

    def point(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        return np.stack([self._sx(s), self._sy(s)], axis=-1)

    def tangent(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        t = np.stack([self._sx(s, 1), self._sy(s, 1)], axis=-1)
        return t / np.linalg.norm(t, axis=-1, keepdims=True)

    def normal(self, s: np.ndarray) -> np.ndarray:
        """Outward unit normal (contour is counter-clockwise: TE->upper->LE->lower)."""
        t = self.tangent(s)
        return np.stack([t[..., 1], -t[..., 0]], axis=-1)

    def arc_length(self, s0: float, s1: float, n: int = 400) -> float:
        p = self.point(np.linspace(s0, s1, n))
        return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))

    def surface(self, side: str, n: int = 200) -> np.ndarray:
        """Points from LE to TE on 'upper' or 'lower' (cosine spacing)."""
        u = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
        if side == "upper":
            s = self.s_le * (1 - u)
        else:
            s = self.s_le + (self._s_total - self.s_le) * u
        return self.point(s)

    # -- properties --------------------------------------------------------
    def thickness(self, n: int = 400) -> tuple[float, float]:
        """(max thickness / chord, x/c of max thickness)."""
        xs = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
        up, lo = self.surface("upper", 600), self.surface("lower", 600)
        yu = np.interp(xs, up[:, 0], up[:, 1])
        yl = np.interp(xs, lo[:, 0], lo[:, 1])
        t = yu - yl
        i = int(np.argmax(t))
        return float(t[i]), float(xs[i])

    def area(self) -> float:
        return float(0.5 * abs(np.dot(self.x, np.roll(self.y, -1)) - np.dot(self.y, np.roll(self.x, -1))))

    def write_dat(self, path: Path, n: int = 161) -> None:
        """Selig format (TE->upper->LE->lower->TE), e.g. for XFoil or CAD."""
        up = self.surface("upper", n)[::-1]
        lo = self.surface("lower", n)[1:]
        pts = np.vstack([up, lo])
        lines = [self.name] + [f"{px: .7f} {py: .7f}" for px, py in pts]
        Path(path).write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# Constructors


def _from_surfaces(name: str, xu, yu, xl, yl) -> Foil:
    """Build from upper/lower surfaces each running LE->TE."""
    x = np.concatenate([xu[::-1], xl[1:]])
    y = np.concatenate([yu[::-1], yl[1:]])
    return Foil(name, x, y)


def naca4(code: str, n: int = 400, closed_te: bool = True) -> Foil:
    """NACA 4-digit section 'MPTT'. closed_te uses the -0.1036 x^4 coefficient."""
    if not re.fullmatch(r"\d{4}", code):
        raise ValueError(f"NACA 4-digit code must be 4 digits, got '{code}'")
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    beta = np.linspace(0, math.pi, n)
    x = 0.5 * (1 - np.cos(beta))
    a4 = -0.1036 if closed_te else -0.1015
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 + a4 * x**4)
    if m == 0 or p == 0:
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    else:
        fwd = x < p
        yc = np.where(fwd, m / p**2 * (2 * p * x - x**2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x**2))
        dyc = np.where(fwd, 2 * m / p**2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    th = np.arctan(dyc)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    foil = _from_surfaces(f"NACA {code}", xu, yu, xl, yl)
    return foil if closed_te else close_trailing_edge(foil)


def _read_dat(path: Path) -> tuple[str, np.ndarray]:
    lines = Path(path).read_text().splitlines()
    name = lines[0].strip() or Path(path).stem
    rows = []
    for line in lines[1:]:
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return name, np.array(rows)


def from_dat(path: str | Path, close_te: bool = True) -> Foil:
    """Read Selig (one loop TE->LE->TE) or Lednicer (two blocks LE->TE) files."""
    name, pts = _read_dat(Path(path))
    if len(pts) < 10:
        raise ValueError(f"{path}: too few coordinate rows")
    # Lednicer: first row holds the point counts (both > 1).
    if pts[0, 0] > 1.5 and pts[0, 1] > 1.5:
        nu, nl = int(pts[0, 0]), int(pts[0, 1])
        up, lo = pts[1 : 1 + nu], pts[1 + nu : 1 + nu + nl]
        x = np.concatenate([up[::-1, 0], lo[1:, 0]])
        y = np.concatenate([up[::-1, 1], lo[1:, 1]])
    else:
        x, y = pts[:, 0], pts[:, 1]
        # Make sure the loop goes TE -> upper -> LE -> lower.
        i_le = int(np.argmin(x))
        if np.mean(y[:i_le]) < np.mean(y[i_le:]):
            x, y = x[::-1], y[::-1]
    foil = normalise(Foil(name, x, y))
    return close_trailing_edge(foil) if close_te else foil


def normalise(foil: Foil) -> Foil:
    """Translate/rotate/scale so LE=(0,0) and the TE midpoint=(1,0)."""
    le = foil.point(foil.s_le)
    te = 0.5 * (np.array([foil.x[0], foil.y[0]]) + np.array([foil.x[-1], foil.y[-1]]))
    d = te - le
    chord = float(np.hypot(*d))
    ang = math.atan2(d[1], d[0])
    c, s = math.cos(-ang), math.sin(-ang)
    px, py = foil.x - le[0], foil.y - le[1]
    x = (c * px - s * py) / chord
    y = (s * px + c * py) / chord
    return Foil(foil.name, x, y)


def close_trailing_edge(foil: Foil) -> Foil:
    """Close a finite-thickness TE by linear shearing (XFoil TGAP style).

    Each surface is shifted by -x * (y_te_surface - y_te_mid), which leaves the
    LE untouched and gives a sharp TE at (1, y_mid). The mesh generator needs a
    sharp TE; for typical model-yacht TE gaps (<0.5 % c) the effect is small.
    """
    x, y = foil.x.copy(), foil.y.copy()
    gap = y[0] - y[-1]
    if abs(gap) < 1e-9 and abs(x[0] - x[-1]) < 1e-9:
        return foil
    i_le = int(np.argmin(x))
    ymid = 0.5 * (y[0] + y[-1])
    xu = np.clip(x[: i_le + 1], 0, 1)
    xl = np.clip(x[i_le:], 0, 1)
    y[: i_le + 1] -= xu * (y[0] - ymid)
    y[i_le:] -= xl * (y[-1] - ymid)
    x[0] = x[-1] = 1.0
    y[0] = y[-1] = ymid
    return Foil(foil.name, x, y)


def load(spec: str, search_dirs: list[Path] | None = None) -> Foil:
    """Resolve a study's `foil:` value.

    'naca0009', 'NACA 2412' -> analytic NACA 4-digit
    'file:sd8020.dat' or 'sd8020.dat' -> coordinate file searched in
    search_dirs (default: geometry/foils of the repository)
    """
    s = spec.strip()
    m = re.fullmatch(r"(?i)naca\s*(\d{4})", s)
    if m:
        return naca4(m.group(1))
    name = s[5:] if s.lower().startswith("file:") else s
    candidates = [Path(name)]
    for d in search_dirs or []:
        candidates += [Path(d) / name, Path(d) / f"{name}.dat"]
    for c in candidates:
        if c.is_file():
            return from_dat(c)
    raise FileNotFoundError(f"foil '{spec}' not found (looked in {[str(c) for c in candidates]})")
