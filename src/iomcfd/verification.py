"""Grid-convergence (Richardson extrapolation / GCI, Roache; Celik et al. 2008)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class GridConvergence:
    f_fine: float
    f_medium: float
    f_coarse: float
    ratio: float  # grid refinement ratio per direction (coarse/medium = medium/fine)
    order: float | None  # observed order of accuracy (None if not monotone)
    f_extrapolated: float | None
    gci_fine: float | None  # relative uncertainty of the fine-grid value
    monotone: bool


def grid_convergence(f_fine: float, f_medium: float, f_coarse: float, ratio: float, safety: float = 1.25) -> GridConvergence:
    e21 = f_medium - f_fine
    e32 = f_coarse - f_medium
    if e21 == 0 or e32 == 0 or (e21 > 0) != (e32 > 0):
        # oscillatory or exactly converged: no meaningful order
        return GridConvergence(f_fine, f_medium, f_coarse, ratio, None, None, None, False)
    p = math.log(abs(e32 / e21)) / math.log(ratio)
    f_ext = f_fine + (f_fine - f_medium) / (ratio**p - 1)
    gci = safety * abs(e21 / f_fine) / (ratio**p - 1) if f_fine else None
    return GridConvergence(f_fine, f_medium, f_coarse, ratio, p, f_ext, gci, True)
