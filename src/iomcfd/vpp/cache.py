"""Tables the VPP computes while it builds a boat (the hydrostatic table, a
hull's wave and windage tables), kept on disk in the table format
(vpp/tables.py) under config.cache_dir()/vpp, keyed by a hash of everything
they depend on: their inputs and the source of the modules that compute
them. A cached table reads back bit-identical to a computed one (floats are
written with repr), so caching never changes a result. Delete the directory
at will; `vpp ... --no-cache` skips it.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .. import config
from . import tables

ENABLED = [True]  # the CLI's --no-cache clears it

# their code is part of every key: a change to it recomputes
SOURCES = ("hydrostatics.py", "hullres.py", "tables.py", "cache.py", "components/hull.py", "components/windage.py")


def _update(h, x: Any) -> None:
    if hasattr(x, "vertices") and hasattr(x, "triangles"):  # an stl.Surface
        _update(h, np.asarray(x.vertices, float))
        _update(h, np.asarray(x.triangles))
    elif isinstance(x, np.ndarray):
        h.update(f"{x.dtype}{x.shape}".encode())
        h.update(np.ascontiguousarray(x).tobytes())
    elif isinstance(x, (list, tuple)):
        h.update(b"[")
        for v in x:
            _update(h, v)
        h.update(b"]")
    else:
        h.update(json.dumps(x, sort_keys=True, default=repr).encode())


def key(kind: str, *parts: Any) -> str:
    h = hashlib.sha256(kind.encode())
    here = Path(__file__).parent
    for f in SOURCES:
        h.update((here / f).read_bytes())
    for p in parts:
        _update(h, p)
    return h.hexdigest()[:16]


def path(kind: str, k: str) -> Path:
    return config.cache_dir() / "vpp" / f"{kind}-{k}.csv"


def cached(kind: str, parts: tuple, compute: Callable[[], tuple[dict, list[dict], list[str]]]) -> tables.Table:
    """The table `kind` for these inputs: from the cache, else computed by
    compute() -> (header, rows, columns) and stored."""
    p = path(kind, key(kind, *parts))
    if ENABLED[0] and p.exists():
        return tables.read(p)
    header, rows, columns = compute()
    if ENABLED[0]:
        try:
            tmp = p.with_name(f"{p.stem}.{os.getpid()}.tmp")
            tables.write(tmp, {"cache": kind, **header}, rows, columns)
            os.replace(tmp, p)
            return tables.read(p)
        except OSError:
            pass
    return tables.Table({"cache": kind, **header}, columns, rows)
