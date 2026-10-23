"""Smooth NACA 6-series 006 sections for the CFD from their Report 824 tables.

The tables (geometry/foils/naca6-006-r824.csv) give 26 stations, too few for
a spline to keep the nose radius (a spline through them has it 20 % small),
so each section is fitted with a CST curve of order 12 with the tabulated
leading-edge radius held (sectiondesign.cst_fit, ordinates and slopes), and
written at its own 6 % and at 1 in on an 18 in chord (the Thistle board,
findings/thistle-board.md):

    uv run python tools/naca6_006.py
"""

import numpy as np
import pandas as pd

from iomcfd import config, sectiondesign

T_BOARD = 1 / 18  # 1 in on an 18 in chord

foils = config.geometry_dir() / "foils"
tab = pd.read_csv(foils / "naca6-006-r824.csv", comment="#")
for name, g in tab.groupby("section"):
    x, y = g["x_pct"].to_numpy() / 100, g["y_pct"].to_numpy() / 100
    r_le = g["r_le_pct"].iloc[0] / 100
    c = sectiondesign.cst_fit(x, y, r_le, g["dydx"].to_numpy(float), n=12)
    f = sectiondesign.cst_symmetric(c)
    err = np.max(np.abs(np.interp(x, *f.surface("upper", 4000).T) - y))
    p = sectiondesign.properties(f)
    assert err < 1e-4 and abs(p["r_le"] / r_le - 1) < 0.01, (name, err, p["r_le"])
    spec = "cst:" + ",".join(f"{v:.10g}" for v in c)
    stem = "naca" + name
    sectiondesign._main(["export", spec, f"{spec}@{T_BOARD:.10g}", "--names", stem, f"{stem}-t0556"])
    print(f"{name}: fit within {err:.1e} c of the table, r_LE {p['r_le'] * 100:.3f} % (table {r_le * 100:.3f} %)")
