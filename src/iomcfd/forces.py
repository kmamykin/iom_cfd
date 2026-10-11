"""Read `forces` function-object output (force.dat / moment.dat)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .foam import find_dat, read_dat


@dataclass
class ForceResult:
    total: np.ndarray  # (3,) N
    pressure: np.ndarray
    viscous: np.ndarray
    moment: np.ndarray  # (3,) N m about the function object's CofR
    std: np.ndarray  # std of the total force over the window
    n_samples: int


def read_forces(case: Path, fo_name: str, window: float = 50) -> ForceResult | None:
    """Average postProcessing/<fo_name> over the last `window` iterations
    (time units), whatever the write interval of the function object."""
    ff = find_dat(case, fo_name, "force.dat")
    if not ff:
        return None
    _, f = read_dat(ff[-1])
    if f.size == 0 or f.shape[1] < 10:
        return None
    t_end = f[-1, 0]
    tail = f[f[:, 0] > t_end - window]
    if len(tail) == 0:
        tail = f[-1:]
    m = np.zeros(3)
    mf = find_dat(case, fo_name, "moment.dat")
    if mf:
        _, md = read_dat(mf[-1])
        if md.size and md.shape[1] >= 4:
            sel = md[md[:, 0] > t_end - window]
            m = (sel if len(sel) else md[-1:])[:, 1:4].mean(axis=0)
    return ForceResult(
        total=tail[:, 1:4].mean(axis=0),
        pressure=tail[:, 4:7].mean(axis=0),
        viscous=tail[:, 7:10].mean(axis=0),
        moment=m,
        std=tail[:, 1:4].std(axis=0),
        n_samples=len(tail),
    )


def forces_function(name: str, patches: list[str], rho_var: str | None = "$rhoInf", cofr: str = "(0 0 0)", interval: int = 1) -> str:
    """OpenFOAM dictionary text for one `forces` function object.

    rho_var: reference density for incompressible solvers, or None for
    solvers with a density field (interFoam).
    """
    pl = " ".join(patches)
    rho = f"    rho             rhoInf;\n    rhoInf          {rho_var};\n" if rho_var else ""
    return (
        f"{name}\n{{\n"
        f"    type            forces;\n"
        f"    libs            (forces);\n"
        f"    writeControl    timeStep;\n"
        f"    writeInterval   {interval};\n"
        f"    log             false;\n"
        f"    patches         ({pl});\n"
        f"{rho}"
        f"    CofR            {cofr};\n"
        f"}}\n"
    )


def window_stats(series: np.ndarray, window: int) -> tuple[float, float, float] | None:
    """(mean of last window, |mean change vs previous window|, std of last window)."""
    if len(series) < 2 * window:
        return None
    last, prev = series[-window:], series[-2 * window : -window]
    return float(last.mean()), float(abs(last.mean() - prev.mean())), float(last.std())


def settled(series: np.ndarray, window: int, tol: float, scale: float) -> bool:
    """True when the windowed mean has stopped moving: |dmean| < tol*scale."""
    st = window_stats(series, window)
    return bool(st is not None and st[1] < tol * scale)
