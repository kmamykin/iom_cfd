"""keel3d CFD results as a VPP table (vpp/tables.py), so boat files name a
table instead of a run and a design filter.

`iomcfd vpp export-table keel3d <study>@<run> --select k=v ... --out
boats/tables/<name>.csv` keeps one design's cases (status ok or
not_converged, one speed), maps keel3d's columns to the VPP's frame and
writes them as they are, with the run, the filter and the geometry the
forces belong to in the header. The keel's force model (components/keel.py
PolarFit) fits them when the boat is built.

Columns: X = −drag_N, Y = side_N, Z = vertical_N (the inflow frame: along
and across the inflow, which is the course; Z up), (x, y, z) = keel3d's
centre of lateral resistance (heeled; at zero leeway, where it is undefined,
the mean of the heel's other rows), X_hull = −drag_hull_N, X_friction_fin
and X_friction_bulb (the parts' friction drag), Y_fin = side_fin_N.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np

from .. import config
from . import tables

KEEL3D_DEFAULTS = config.projects_dir() / "keel3d" / "defaults.yaml"

# keel3d parameters that make the keel (geometry and mass), and its hull
KEEL_KEYS = ("draft", "keel_mass", "fin_mass", "lead_density", "fin_section", "fin_mean_chord", "fin_taper",
             "fin_sweep", "fin_x", "bulb", "bulb_section", "bulb_x", "bulb_aspect", "bulb_top", "bulb_bottom",
             "bulb_cant")
HULL_KEYS = ("hull_length", "hull_beam", "hull_draft", "hull_beam_at", "hull_draft_at", "hull_entry", "hull_run",
             "hull_section")
COLUMNS = ["case", "status", "heel", "leeway", "V", "X", "Y", "Z", "x", "y", "z", "X_hull", "X_friction_fin",
           "X_friction_bulb", "Y_fin"]


def resolve_results(ref: str, base: Path | None = None) -> Path:
    """A keel3d run's results.csv from `<study>@<run id>` (looked up in
    config.source_runs_dirs()) or a path (relative to `base`, then the repo
    root)."""
    if "@" in ref and not ref.endswith(".csv"):
        study, run = ref.split("@", 1)
        for d in config.source_runs_dirs():
            p = d / study / run / "results.csv"
            if p.exists():
                return p
        raise FileNotFoundError(f"{ref}: no {study}/{run}/results.csv in {[str(d) for d in config.source_runs_dirs()]}"
                                " (set IOMCFD_SOURCE_RUNS to the runs/ that holds it)")
    for b in ([base] if base else []) + [config.home()]:
        p = (b / ref).resolve()
        if p.exists():
            return p if p.suffix == ".csv" else p / "results.csv"
    raise FileNotFoundError(ref)


def numeric(v: Any) -> bool:
    try:
        float(v)
        return not isinstance(v, bool)
    except (TypeError, ValueError):
        return False


def select_rows(df, select: dict | None):
    """keel3d rows that ran (ok or not_converged) and match `select`."""
    df = df[df["status"].isin(["ok", "not_converged"])]
    for k, val in (select or {}).items():
        col = df[k]
        df = df[np.isclose(col.astype(float), float(val))] if numeric(val) else df[col.astype(str) == str(val)]
    return df


def _param(v: Any) -> Any:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, str) and v in ("True", "False"):
        return v == "True"
    return float(v) if numeric(v) else str(v)


def export(ref: str, select: dict | None, out: str | Path, base: Path | None = None) -> Path:
    """One keel3d design's cases as a VPP table at `out`."""
    import pandas as pd

    path = resolve_results(ref, base)
    df = select_rows(pd.read_csv(path), select)
    if df.empty:
        raise ValueError(f"no keel3d rows match {select} in {path}")
    if df["speed"].nunique() > 1:
        raise ValueError("keel3d rows at more than one speed: select one")
    varies = [k for k in (*KEEL_KEYS, *HULL_KEYS) if k in df and df[k].astype(str).nunique() > 1]
    if varies:
        raise ValueError(f"the selection holds more than one design ({varies} vary): select one")
    rows = []
    for _, r in df.iterrows():
        rows.append({"case": r["case"], "status": r["status"], "heel": float(r["heel"]), "leeway": float(r["leeway"]),
                     "V": float(r["speed"]), "X": -float(r["drag_N"]), "Y": float(r["side_N"]),
                     "Z": float(r["vertical_N"]), "x": float(r["x_clr"]), "y": 0.0, "z": float(r["z_clr"]),
                     "X_hull": -float(r["drag_hull_N"]), "X_friction_fin": -float(r["drag_fin_friction_N"]),
                     "X_friction_bulb": -float(r["drag_bulb_friction_N"]),
                     "Y_fin": float(r["side_fin_N"]) if "side_fin_N" in r else math.nan})
    for heel in {r["heel"] for r in rows}:
        lift = [r for r in rows if r["heel"] == heel and r["leeway"] > 0]
        for r in rows:
            if r["heel"] == heel and r["leeway"] <= 0 and lift:
                r["x"], r["z"] = float(np.nanmean([q["x"] for q in lift])), float(np.nanmean([q["z"] for q in lift]))
    rows.sort(key=lambda r: (r["heel"], r["leeway"]))
    r0 = df.iloc[0]
    header = {
        "component": "keel",
        "model": "fit",
        "dims": ["heel", "leeway", "V"],
        "frame": "inflow",
        "point": "boat",
        "units": {"heel": "deg", "leeway": "deg", "V": "m/s", "X": "N", "Y": "N", "Z": "N", "x": "m"},
        "fluid": {"rho": float(r0["rhoInf"]), "nu": float(r0["nu"])},
        "reference": {"length": float(r0["fin_mean_chord"])},
        "includes": ["host.side_force", "host.yaw_moment"],
        "note": "keel3d double body: canoe body, fin and bulb under a mirror plane at the waterline (no waves); "
                "Z includes the double body's suction",
        "params": {k: _param(r0[k]) for k in (*KEEL_KEYS, *HULL_KEYS) if k in r0},
        "source": {"tool": "keel3d", "run": ref, "file": "/".join(path.parts[-3:]),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "select": dict(select or {})},
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git": config.git_describe(),
    }
    return tables.write(out, header, rows, COLUMNS)
