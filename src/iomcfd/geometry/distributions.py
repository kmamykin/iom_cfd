"""1D point distributions for structured meshing."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


def geometric(n: int, first: float, length: float = 1.0) -> np.ndarray:
    """n intervals (n+1 points) from 0..length, first interval = `first`.

    Solves for the constant growth ratio r. Works for r < 1 as well.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    h = first / length
    if abs(h * n - 1.0) < 1e-12:
        return np.linspace(0.0, length, n + 1)

    def f(r: float) -> float:
        return h * (r**n - 1.0) / (r - 1.0) - 1.0 if abs(r - 1.0) > 1e-12 else h * n - 1.0

    lo, hi = (1.0 + 1e-12, 4.0) if h * n < 1.0 else (1e-6, 1.0 - 1e-12)
    r = brentq(f, lo, hi, xtol=1e-14)
    k = np.arange(n + 1)
    x = h * (r**k - 1.0) / (r - 1.0)
    x /= x[-1]
    return x * length


def growth_ratio(x: np.ndarray) -> float:
    d = np.diff(x)
    return float(np.max(np.maximum(d[1:] / d[:-1], d[:-1] / d[1:])))


def vinokur(n: int, ds0: float, ds1: float) -> np.ndarray:
    """Two-sided tanh stretching (Vinokur 1983) on [0, 1].

    n intervals, first interval ds0 and last interval ds1 (fractions of the
    total length). Falls back to sine stretching when both ends are coarser
    than uniform.
    """
    a = math.sqrt(ds1 / ds0)
    b = 1.0 / (n * math.sqrt(ds0 * ds1))
    xi = np.linspace(0.0, 1.0, n + 1)
    if abs(b - 1.0) < 1e-6:
        u = xi.copy()
    elif b > 1.0:
        dy = brentq(lambda y: math.sinh(y) / y - b, 1e-8, 50.0)
        u = 0.5 * (1.0 + np.tanh(dy * (xi - 0.5)) / math.tanh(dy / 2.0))
    else:
        dy = brentq(lambda y: math.sin(y) / y - b, 1e-8, math.pi - 1e-8)
        u = 0.5 * (1.0 + np.tan(dy * (xi - 0.5)) / math.tan(dy / 2.0))
    s = u / (a + (1.0 - a) * u)
    s[0], s[-1] = 0.0, 1.0
    return s


def graded_section(length: float, first: float, last: float, max_growth: float = 1.2) -> tuple[int, float]:
    """Cells and blockMesh expansion ratio (last/first) for a section of
    `length` whose cell size grows from `first` to `last` at <= max_growth."""
    if last <= first * 1.05:
        return max(1, round(length / first)), 1.0
    for n in range(1, 400):
        r = (last / first) ** (1.0 / max(n - 1, 1))
        if r > max_growth:
            continue
        if first * (r**n - 1) / (r - 1) >= length:
            return n, last / first
    return 400, last / first
