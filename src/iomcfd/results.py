"""Collect per-case results into one table (runs/<study>/<run id>/results.csv)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .runner import RESULT


def _flat(prefix: str, d: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            continue
        if isinstance(v, list):
            v = " ".join(str(x) for x in v)
        out[f"{prefix}{k}"] = v
    return out


def collect(run_dir: Path) -> tuple[list[dict[str, Any]], Path]:
    rows = []
    for case_dir in sorted(p for p in Path(run_dir).iterdir() if p.is_dir()):
        pj = case_dir / "params.json"
        if not pj.is_file():
            continue
        pdata = json.loads(pj.read_text())
        res = {}
        if (case_dir / RESULT).is_file():
            res = json.loads((case_dir / RESULT).read_text())
        row = {"case": case_dir.name, "status": res.get("status", "pending")}
        row.update(_flat("", pdata.get("params", {})))
        row.update(_flat("", pdata.get("derived", {})))
        row.update(_flat("", res.get("metrics") or {}))
        row["wall_time_s"] = res.get("wall_time_s")
        rows.append(row)
    out = Path(run_dir) / "results.csv"
    if rows:
        cols: list[str] = []
        for r in rows:
            cols += [k for k in r if k not in cols]
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    return rows, out
