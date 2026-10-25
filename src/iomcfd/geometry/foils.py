"""2D foil section geometry.

A `Foil` is a closed, unit-chord section with the leading edge at (0, 0) and
a sharp trailing edge at (1, 0). It is stored as one smooth parametric curve
running TE -> upper surface -> LE -> lower surface -> TE, so it can be
re-sampled at any point distribution (needed by the mesh generator).
Sections with corners (stepped foils) are stored as several smooth pieces
joined at `breaks`, so a spline never runs across a corner.

Sources:
  naca4("2412")           analytic NACA 4-digit (closed TE variant)
  naca4_modified("0007-74")  analytic NACA modified 4-digit, symmetric (closed TE)
  from_dat(path)          Selig or Lednicer coordinate files (UIUC database,
                          airfoiltools.com, XFoil exports, Fusion 360 sketches
                          exported as points...)
  load("naca0009") / load("file:my_section.dat")  string spec used by studies
  load("stair1:naca0009:d=0.3")  stepped (Kline-Fogleman) section, see stepped.py
  load("film:naca0009:x=0.5,t=0.002")  a film wrapped round the nose, see stepped.py
  load("faired:naca0007:x=0.5,h=0.002")  a stair1 step faired out, see stepped.py
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar


@dataclass
class Foil:
    name: str
    x: np.ndarray  # closed contour TE->upper->LE->lower->TE, unit chord
    y: np.ndarray
    # Indices (into x, y) where the contour has a corner or a curvature jump:
    # each piece between breaks gets its own spline. Empty = one smooth curve.
    breaks: tuple[int, ...] = ()
    # Stepped sections: the smooth section they were cut from, and one
    # StepInfo per step (filled in by stepped.py).
    base: Foil | None = None
    steps: list = field(default_factory=list)

    def __post_init__(self) -> None:
        x, y = np.asarray(self.x, float), np.asarray(self.y, float)
        # Chord-length parametrisation of the closed contour.
        ds = np.hypot(np.diff(x), np.diff(y))
        keep = np.concatenate([[True], ds > 1e-12])
        new_index = np.cumsum(keep) - 1
        x, y = x[keep], y[keep]
        s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
        self.x, self.y = x, y
        self.s_nodes = s  # parameter value of every contour point
        self._s_total = s[-1]
        brk = sorted({int(new_index[b]) for b in self.breaks} - {0, len(s) - 1})
        self.breaks = tuple(brk)
        if brk:
            edges = [0, *brk, len(s) - 1]
            self._seg_s0 = s[edges[:-1]]
            self._segs = [(CubicSpline(s[a : b + 1], x[a : b + 1]), CubicSpline(s[a : b + 1], y[a : b + 1]))
                          for a, b in zip(edges[:-1], edges[1:])]
        else:
            self._sx = CubicSpline(s, x)
            self._sy = CubicSpline(s, y)
        # Leading edge = point of minimum x on the spline.
        i_le = int(np.argmin(x))
        lo, hi = s[max(i_le - 2, 0)], s[min(i_le + 2, len(s) - 1)]
        self.s_le = float(minimize_scalar(lambda t: float(self.point(t)[0]), bounds=(lo, hi), method="bounded").x)

    # -- evaluation --------------------------------------------------------
    @property
    def perimeter(self) -> float:
        return self._s_total

    @property
    def s_breaks(self) -> np.ndarray:
        """Parameter values of the corners (empty for a smooth section)."""
        return self.s_nodes[list(self.breaks)]

    def _eval(self, s: np.ndarray, nu: int = 0) -> tuple[np.ndarray, np.ndarray]:
        if not self.breaks:
            return self._sx(s, nu), self._sy(s, nu)
        s1 = np.atleast_1d(s)
        k = np.clip(np.searchsorted(self._seg_s0, s1, side="right") - 1, 0, len(self._segs) - 1)
        ox, oy = np.empty_like(s1), np.empty_like(s1)
        for i in np.unique(k):
            m = k == i
            ox[m], oy[m] = self._segs[i][0](s1[m], nu), self._segs[i][1](s1[m], nu)
        return ox.reshape(np.shape(s)), oy.reshape(np.shape(s))

    def point(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        return np.stack(self._eval(s), axis=-1)

    def tangent(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        t = np.stack(self._eval(s, 1), axis=-1)
        return t / np.linalg.norm(t, axis=-1, keepdims=True)

    def normal(self, s: np.ndarray) -> np.ndarray:
        """Outward unit normal (contour is counter-clockwise: TE->upper->LE->lower)."""
        t = self.tangent(s)
        return np.stack([t[..., 1], -t[..., 0]], axis=-1)

    def arc_length(self, s0: float, s1: float, n: int = 400) -> float:
        p = self.point(np.linspace(s0, s1, n))
        return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))

    def surface(self, side: str, n: int = 200) -> np.ndarray:
        """Points from LE to TE on 'upper' or 'lower' (cosine spacing).

        On a section with corners every corner is included, with extra points
        on short pieces (a step face, a fillet), so more than n points come
        back."""
        u = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
        if side == "upper":
            s = self.s_le * (1 - u)
        else:
            s = self.s_le + (self._s_total - self.s_le) * u
        if self.breaks:
            lo, hi = sorted((s[0], s[-1]))
            edges = np.concatenate([[0.0], self.s_breaks, [self._s_total]])
            extra = [np.linspace(a, b, 9) for a, b in zip(edges[:-1], edges[1:]) if b - a < 0.05]
            s = np.concatenate([s, self.s_breaks, *extra])
            s = np.unique(s[(s >= lo) & (s <= hi)])
            s = s[::-1] if side == "upper" else s
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

    def write_dat(self, path: Path, n: int = 161, digits: int = 7) -> None:
        """Selig format (TE->upper->LE->lower->TE), e.g. for XFoil or CAD.

        At 7 decimals the points next to the leading edge keep only one or
        two significant digits in x: harmless for the shape (1e-7 c), but
        the nose curvature read back from the file is off by up to 20 %.
        Use more digits where that matters (section design)."""
        up = self.surface("upper", n)[::-1]
        lo = self.surface("lower", n)[1:]
        pts = np.vstack([up, lo])
        lines = [self.name] + [f"{px: .{digits}f} {py: .{digits}f}" for px, py in pts]
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


def modified4_thickness(x: np.ndarray, t: float, m: float = 0.3, rho: float = 1.0, d1: float | None = None,
                        te: float = 0.0) -> np.ndarray:
    """Half-thickness of the NACA modified 4-digit series, continuous parameters.

    t: thickness/chord; m: x/c of maximum thickness; rho: leading-edge radius
    as a multiple of the normal 4-digit one (1.1019 t^2); d1: trailing-edge
    slope in the series' t = 0.2 units (default: NACA's value for m);
    te: trailing-edge half-thickness in the same units (NACA's is 0.002; 0
    closes it). Forward of m a0 sqrt(x) + a1 x + a2 x^2 + a3 x^3, aft of it
    d0 + d1 (1-x) + d2 (1-x)^2 + d3 (1-x)^3, matched at m in value, slope
    and curvature (Abbott & von Doenhoff 1959, sec. 6.4; Ladson & Brooks,
    NASA TM X-3284, 1975)."""
    if d1 is None:
        d1 = (2.24 - 5.42 * m + 12.3 * m**2) / (10 * (1 - 0.878 * m))
    a0 = 0.296904 * math.sqrt(rho)
    L = 1 - m
    d0 = te
    d3 = (2 * d0 + d1 * L - 0.2) / L**3
    d2 = -(d1 + 3 * d3 * L**2) / (2 * L)
    curv = 2 * d2 + 6 * d3 * L  # aft curvature at m, matched by the forward polynomial
    A = np.array([[m, m**2, m**3], [1, 2 * m, 3 * m**2], [0, 2, 6 * m]])
    b = np.array([0.1 - a0 * math.sqrt(m), -a0 / (2 * math.sqrt(m)), curv + a0 / (4 * m**1.5)])
    a1, a2, a3 = np.linalg.solve(A, b)
    x = np.asarray(x, float)
    xf = np.minimum(x, m)
    xa = 1 - np.maximum(x, m)
    fwd = a0 * np.sqrt(xf) + a1 * xf + a2 * xf**2 + a3 * xf**3
    aft = d0 + d1 * xa + d2 * xa**2 + d3 * xa**3
    return t / 0.2 * np.where(x <= m, fwd, aft)


def naca4_modified(code: str, n: int = 400) -> Foil:
    """Symmetric NACA modified 4-digit section '00TT-IM', closed trailing edge.

    I is the leading-edge radius index (6 = the normal 4-digit radius, which
    scales with I^2; 9 = three times normal), M the position of maximum
    thickness in tenths of the chord. NACA 0012-63 is close to, but not the
    same as, NACA 0012."""
    mt = re.fullmatch(r"00(\d{2})-(\d)(\d)", code)
    if not mt:
        raise ValueError(f"modified 4-digit code must be '00TT-IM' (symmetric), got '{code}'")
    t, i_le, m = int(mt.group(1)) / 100, int(mt.group(2)), int(mt.group(3)) / 10
    if not 0.2 <= m <= 0.6 or i_le == 0:
        raise ValueError(f"'{code}': needs a maximum-thickness position 2-6 and a leading-edge index 1-9")
    rho = 3.0 if i_le == 9 else (i_le / 6) ** 2
    x = 0.5 * (1 - np.cos(np.linspace(0, math.pi, n)))
    y = modified4_thickness(x, t, m, rho)
    return _from_surfaces(f"NACA {code}", x, y, x, -y)


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
    if re.match(r"(?i)(?:(?:stair|kfm)\d+|film|faired):", s):  # kfm: renamed, stepped.py explains
        from . import stepped

        return stepped.from_spec(s, search_dirs)
    m = re.fullmatch(r"(?i)naca\s*(\d{4})", s)
    if m:
        return naca4(m.group(1))
    m = re.fullmatch(r"(?i)naca\s*(00\d{2}-\d{2})", s)
    if m:
        return naca4_modified(m.group(1))
    name = s[5:] if s.lower().startswith("file:") else s
    candidates = [Path(name)]
    for d in search_dirs or []:
        candidates += [Path(d) / name, Path(d) / f"{name}.dat"]
    for c in candidates:
        if c.is_file():
            return from_dat(c)
    raise FileNotFoundError(f"foil '{spec}' not found (looked in {[str(c) for c in candidates]})")
