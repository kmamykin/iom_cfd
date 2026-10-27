"""Tables the VPP reads forces from: a CSV whose header is YAML in `# `
lines, then one row per point. The same format holds exported CFD results
(vpp/keel3d.py), tables built by evaluating a model on a grid, and the
VPP's own caches.

Header keys (the ones a reader relies on):

    vpp-table: 1
    component: keel                 # what the table describes
    model: fit                      # fit: raw points, fitted at load; grid: interpolate as is
    dims: [heel, leeway, V]         # condition columns
    frame: inflow                   # X against the inflow, Y to its port, Z up [N]
    point: boat                     # x, y, z where X, Y, Z act: boat frame, heeled [m]
    params: {...}                   # the geometry the forces belong to
    source: {...}                   # where the numbers came from

Floats are written with repr, so a table read back is bit-identical to the
numbers written.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

VERSION = 1


@dataclass
class Table:
    header: dict
    columns: list[str]
    rows: list[dict[str, Any]] = field(default_factory=list)
    path: Path | None = None

    def column(self, name: str) -> np.ndarray:
        return np.array([r[name] for r in self.rows], dtype=float)


def _value(s: str) -> Any:
    try:
        return float(s)
    except ValueError:
        return s


def read(path: str | Path) -> Table:
    path = Path(path)
    head, body = [], []
    for line in path.read_text().splitlines():
        (head if line.startswith("#") else body).append(line)
    header = yaml.safe_load("\n".join(h[2:] if h.startswith("# ") else h[1:] for h in head)) or {}
    if int(header.get("vpp-table", 0)) != VERSION:
        raise ValueError(f"{path}: not a vpp-table {VERSION} file")
    rd = csv.DictReader(io.StringIO("\n".join(body)))
    rows = [{k: _value(v) for k, v in r.items()} for r in rd]
    return Table(header, list(rd.fieldnames or []), rows, path)


def _cell(v: Any) -> Any:
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v)).lower()
    if isinstance(v, (float, np.floating)):
        return repr(float(v))
    return v


def _plain(v: Any) -> Any:
    """Header values as plain YAML (no numpy types)."""
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v) if math.isfinite(v) else None
    return v


def write(path: str | Path, header: dict, rows: list[dict[str, Any]], columns: list[str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(rows[0])
    head = yaml.safe_dump({"vpp-table": VERSION, **_plain(header)}, sort_keys=False, allow_unicode=True, width=1000)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: _cell(r.get(k, "")) for k in columns})
    path.write_text("".join(f"# {line}\n" for line in head.splitlines()) + buf.getvalue())
    return path
