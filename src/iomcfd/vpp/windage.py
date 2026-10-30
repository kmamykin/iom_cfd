"""windage CFD results (projects/windage) as a VPP table, read by
components/windage.py WindageTable.

`iomcfd vpp export-table windage <study>@<run> --select mesh=fine --out
boats/tables/<name>.csv` keeps one hull's cases (status ok or
not_converged) at one wind speed over heel × the wind's angle to the
centreline (a full grid, one case per node) and writes, per case, the
topsides' loads per unit dynamic pressure q = ½ρV_AW² (m², m³):

* D along the apparent wind and L across it, horizontal: windage's liftDir,
  the wind's direction turned 90° anticlockwise seen from above (to port for
  wind from the bow), so L < 0 ahead of the beam pulls forward and to
  leeward;
* Z, the vertical force (+ up);
* K, M, N about the bow on the waterline (the placed boat origin), with the
  VPP's signs (components/base.py): K = the CFD's roll moment, M and N its
  pitch and yaw moments negated (x aft, y port, z up in the CFD).

With them: A, the projected area normal to the wind (the coefficients' area,
as ProjectedArea's), `height`, its centroid's height above the water (where
the VPP takes the wind), cd and cl, and ext 1 for a not_converged case. The
header has each heel's attitude (sink, trim) and the hull (an STL's sha256,
as MeshHull.params()).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .. import config
from . import keel3d, tables

COLUMNS = ["heel", "angle", "A", "height", "cd", "cl", "D", "L", "Z", "K", "M", "N", "ext", "case"]


def export(ref: str, select: dict | None, out: str | Path, base: Path | None = None) -> Path:
    """One hull's windage cases at one wind speed as a VPP table at `out`."""
    import pandas as pd

    path = keel3d.resolve_results(ref, base)
    df = keel3d.select_rows(pd.read_csv(path), select)
    if df.empty:
        raise ValueError(f"no windage rows match {select} in {path}")
    for k in ("hull_stl", "aws", "temperature"):
        if k in df and df[k].astype(str).nunique() > 1:
            raise ValueError(f"the selection holds more than one {k} ({sorted(df[k].astype(str).unique())}): "
                             "select one")
    n = df.groupby(["heel", "awa"]).size()
    if (n > 1).any():
        raise ValueError(f"more than one case at (heel, awa) {list(n[n > 1].index)}: select one "
                         "(e.g. --select mesh=fine)")
    heels, angles = (sorted(df[d].astype(float).unique()) for d in ("heel", "awa"))
    by = {(float(r["heel"]), float(r["awa"])): r for _, r in df.iterrows()}
    missing = [(h, a) for h in heels for a in angles if (h, a) not in by]
    if missing:
        raise ValueError(f"no case at (heel, awa) {missing}: the table is a full grid")
    rows, attitude = [], {}
    for h in heels:
        for a in angles:
            r = by[(h, a)]
            q = float(r["dynamicPressure"])
            rows.append({"heel": h, "angle": a, "A": float(r["A_proj_m2"]), "height": float(r["z_centroid_m"]),
                         "cd": float(r["cd"]), "cl": float(r["cl"]),
                         "D": float(r["drag_N"]) / q, "L": float(r["lift_N"]) / q, "Z": float(r["vertical_N"]) / q,
                         "K": float(r["roll_moment_Nm"]) / q, "M": -float(r["pitch_moment_Nm"]) / q,
                         "N": -float(r["yaw_moment_Nm"]) / q, "ext": float(r["status"] != "ok"), "case": r["case"]})
        r = by[(h, angles[0])]
        attitude[f"{h:g}"] = {"sink": float(r.get("sink") or 0.0), "trim": float(r.get("trim") or 0.0)}
    r0 = df.iloc[0]
    header = {
        "component": "windage",
        "model": "grid",
        "dims": ["heel", "angle"],
        "frame": "wind",
        "normalise": "q",
        "moments": "bow",
        "units": {"heel": "deg", "angle": "deg", "A": "m2", "height": "m", "D": "m2", "K": "m3"},
        "fluid": {"rho": float(r0["rhoInf"]), "nu": float(r0["nu"])},
        "aws": float(r0["aws"]),
        "attitude": attitude,
        "note": "windage CFD: the topsides at each heel's attitude in a uniform apparent wind over a slip water "
                "surface (no gradient, no rig); D, L, Z, K, M, N per unit ½ρV_AW², D along and L across the "
                "wind (L < 0 ahead of the beam: forward and to leeward), moments about the bow on the waterline; "
                "angle from the centreline; ext: not converged",
        "params": {"hull_stl": str(r0.get("hull_stl") or ""), **keel3d.hull_params(r0)},
        "source": {"tool": "windage", "run": ref, "file": "/".join(path.parts[-3:]),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "select": dict(select or {})},
        "git": config.git_describe(),
    }
    out_path = tables.write(out, header, rows, COLUMNS)
    if not np.isfinite([r[k] for r in rows for k in ("D", "L", "Z", "K", "M", "N")]).all():
        raise ValueError(f"{out_path}: non-finite loads")
    return out_path
