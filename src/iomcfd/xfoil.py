"""XFOIL polars: a fast, low-fidelity companion to the foil2d CFD.

XFOIL (Drela 1989) couples a panel method to an integral boundary layer
with e^n transition, which is what it was built for: laminar separation
bubbles at chord Reynolds numbers of 5e4-5e5. A polar takes well under a
second, against 1-16 h for a time-accurate CFD point, so it can screen
sections and drive an optimiser; the CFD then checks the few that matter.

The binary is not part of the project: build it with tools/build-xfoil.sh.
It is found through $IOMCFD_XFOIL, then PATH, then ~/.local/bin/xfoil.

Freestream turbulence enters through the critical amplification ratio,
Ncrit (Mack's correlation, `ncrit_from_tu`): Tu 0.1 % gives about 8.2,
Tu 1 % about 2.6.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from iomcfd.geometry.foils import Foil


def find_xfoil() -> str:
    for c in (os.environ.get("IOMCFD_XFOIL"), shutil.which("xfoil"), str(Path.home() / ".local/bin/xfoil")):
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError("xfoil not found: build it with tools/build-xfoil.sh or set IOMCFD_XFOIL")


def ncrit_from_tu(tu_percent: float) -> float:
    """Mack (1977): Ncrit = -8.43 - 2.4 ln(Tu), Tu as a fraction."""
    return -8.43 - 2.4 * math.log(tu_percent / 100)


@dataclass
class Polar:
    """One XFOIL polar. Arrays over the converged angles only, increasing."""

    re: float
    ncrit: float
    alpha: np.ndarray  # deg
    cl: np.ndarray
    cd: np.ndarray
    cdp: np.ndarray  # pressure drag (Cd - Cdp is friction)
    cm: np.ndarray
    xtr_top: np.ndarray  # transition x/c, upper (suction side at alpha > 0)
    xtr_bot: np.ndarray

    def at(self, alpha: float, field: str = "cd") -> float:
        """Linear interpolation in alpha; nan outside the converged range."""
        a, v = self.alpha, getattr(self, field)
        if not len(a) or alpha < a[0] - 1e-9 or alpha > a[-1] + 1e-9:
            return math.nan
        return float(np.interp(alpha, a, v))


def _parse_polar(text: str) -> np.ndarray:
    rows, started = [], False
    for line in text.splitlines():
        if line.strip().startswith("------"):
            started = True
            continue
        if started and line.strip():
            try:
                rows.append([float(v) for v in line.split()[:7]])
            except ValueError:
                pass
    return np.array(rows).reshape(-1, 7)


def polar(foil: Foil, re: float, alphas, ncrit: float = 9.0, panels: int = 220, iters: int = 300,
          timeout: float = 10.0, xtr: tuple[float, float] | None = None) -> Polar:
    """Viscous polar of `foil` at Reynolds number `re` over the angles `alphas`.

    The angles are run in increasing order, each from the previous solution
    (boundary layer kept between points), from the angle nearest 0 outward on
    each side so the first point starts from an easy flow. Angles that don't
    converge are left out of the result. `xtr` = (top, bottom) forces
    transition at those x/c at the latest (XFOIL's XTR; a trip, roughness)."""
    xfoil = find_xfoil()
    alphas = sorted({round(float(a), 4) for a in alphas})
    pos = [a for a in alphas if a >= 0]
    neg = [a for a in alphas if a < 0][::-1]
    with tempfile.TemporaryDirectory(prefix="xfoil-") as tmp:
        tmpd = Path(tmp)
        foil.write_dat(tmpd / "foil.dat", n=121, digits=10)  # XFOIL holds at most 365 points; it re-panels anyway
        vpar = [f"N {ncrit:.4g}"] + ([f"XTR {xtr[0]:.4g} {xtr[1]:.4g}"] if xtr else [])
        cmds = ["PLOP", "G F", "", "LOAD foil.dat", "PPAR", f"N {panels}", "", "", "OPER", f"ITER {iters}",
                f"VISC {re:.6g}", "VPAR", *vpar, "", "PACC", "polar.txt", ""]
        for k, branch in enumerate(b for b in (pos, neg) if b):
            if k:
                cmds.append("INIT")  # toggles: before the first solution it would corrupt the boundary layer
            cmds += [f"ALFA {a:g}" for a in branch]
        cmds += ["PACC", "", "QUIT"]
        try:
            subprocess.run([xfoil], input="\n".join(cmds) + "\n", cwd=tmpd, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass  # XFOIL can hang past stall; the points saved before that are kept
        pol = tmpd / "polar.txt"
        data = _parse_polar(pol.read_text()) if pol.is_file() else np.zeros((0, 7))
    if len(data):
        data = data[np.argsort(data[:, 0])]
        _, first = np.unique(np.round(data[:, 0], 4), return_index=True)
        data = data[first]
    a, cl, cd, cdp, cm, xt, xb = (data[:, k] for k in range(7))
    return Polar(re, ncrit, a, cl, cd, cdp, cm, xt, xb)
