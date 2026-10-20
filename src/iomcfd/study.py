"""Studies: a YAML file that expands into a list of concrete cases.

    study: keel-sections            # name -> runs/<study>/<run id>/
    project: foil2d                 # projects/<project>/
    description: free text
    reference: validation/data.csv  # optional, overlaid by `iomcfd report`
    viz:                            # optional, for `iomcfd viz`
      views: [velocity, separation] # default: the project's DEFAULT_VIEWS
      animate: aoa                  # swept parameter for study animations
      options: {q_level: 3}         # passed to the project's view functions
    report:                         # optional, options for `iomcfd report` (no re-run needed)
      fin_span: 0.36                # e.g. foil2d: whole-fin forces in the selection figure
    highlights:                     # optional: the cases worth a close look (iomcfd.highlights)
      - name: thick-vs-thin
        why: bubble and transition across thickness at working load
        where: {speed: 1.0, aoa: [4, 6]}
        compare: foil
        views: [separation, transition]
    defaults:                       # override the project's defaults.yaml
      speed: 1.0
    sweep:                          # full factorial (cartesian product)
      foil: [naca0008, naca0010]
      aoa: [0, 2, 4, 6]
    zip:                            # varied together, row by row
      speed: [0.5, 1.0, 1.5]
      aoa:   [6, 4, 3]
    sample:                         # random / Latin-hypercube design
      method: lhs                   # lhs | random
      n: 20
      seed: 1
      ranges: {chord: [0.06, 0.09], aoa: [0, 8]}
    cases:                          # explicit one-off cases (not crossed)
      - {foil: naca0012, aoa: 10, mesh: fine}

sweep x zip x sample are crossed with each other; `cases` are appended.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml


@dataclass
class Case:
    name: str
    index: int
    params: dict[str, Any]  # full parameter set (defaults merged), before derive()
    varied: dict[str, Any]  # just the parameters this study varies

    @property
    def params_hash(self) -> str:
        return params_hash(self.params)


# Parameters that change how a case runs or what it writes, but not its
# answer. They are left out of the cache hash, so adding or changing them
# never forces finished cases to re-run (use --force for that).
EXECUTION_KEYS = {"np", "relax_U", "relax_turb", "relax_transition", "snapshot_interval", "start_iter"}

# Parameters added after runs existed, left out of the hash while empty
# (their default), so finished cases of earlier runs keep their hash.
OPTIONAL_KEYS = {"start_from", "mesh_shift_only"}


# Scientific notation PyYAML (YAML 1.1) leaves as a string, e.g. 6.0e6 or 1e5.
_SCI = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)[eE][-+]?\d+$")


def coerce_numbers(v: Any) -> Any:
    """Turn scientific-notation strings (which PyYAML does not parse) into floats."""
    if isinstance(v, str) and _SCI.match(v.strip()):
        return float(v)
    if isinstance(v, list):
        return [coerce_numbers(x) for x in v]
    if isinstance(v, dict):
        return {k: coerce_numbers(x) for k, x in v.items()}
    return v


def params_hash(params: dict) -> str:
    phys = {k: v for k, v in params.items()
            if k not in EXECUTION_KEYS and not (k in OPTIONAL_KEYS and v in (None, "", []))}
    blob = json.dumps(phys, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


@dataclass
class Study:
    name: str
    project: str
    path: Path | None = None
    description: str = ""
    defaults: dict[str, Any] = field(default_factory=dict)
    sweep: dict[str, list] = field(default_factory=dict)
    zip: dict[str, list] = field(default_factory=dict)
    sample: dict[str, Any] = field(default_factory=dict)
    cases: list[dict[str, Any]] = field(default_factory=list)
    reference: str | None = None  # CSV of reference data, relative to the project dir
    report: dict[str, Any] = field(default_factory=dict)  # options for Project.report
    raw: dict[str, Any] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)  # --set on the command line
    highlights: list = field(default_factory=list)  # iomcfd.highlights.Highlight
    highlights_from: str = ""  # the study file they came from

    @classmethod
    def load(cls, path: str | Path, overrides: dict[str, Any] | None = None) -> "Study":
        path = Path(path)
        data = coerce_numbers(yaml.safe_load(path.read_text()) or {})
        unknown = set(data) - {"study", "project", "description", "reference", "defaults", "sweep", "zip", "sample", "cases",
                               "viz", "report", "highlights"}
        if unknown:
            raise ValueError(f"{path}: unknown top-level keys {sorted(unknown)}")
        st = cls(
            name=data.get("study") or path.stem,
            project=data["project"],
            path=path,
            description=data.get("description", ""),
            defaults=dict(data.get("defaults") or {}),
            sweep=dict(data.get("sweep") or {}),
            zip=dict(data.get("zip") or {}),
            sample=dict(data.get("sample") or {}),
            cases=list(data.get("cases") or []),
            reference=data.get("reference"),
            report=dict(data.get("report") or {}),
            raw=data,
        )
        if not re.fullmatch(r"[A-Za-z0-9._-]+", st.name):
            raise ValueError(f"study name '{st.name}' must be [A-Za-z0-9._-]")
        from .highlights import parse

        st.highlights = parse(data.get("highlights"), str(path))  # fails early on a malformed entry
        st.highlights_from = str(path) if st.highlights else ""
        if overrides:
            st.apply_overrides(overrides)
        return st

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        """--set key=value from the CLI: pins a parameter for every case."""
        for k, v in coerce_numbers(overrides).items():
            self.overrides[k] = v
            self.defaults[k] = v
            self.sweep.pop(k, None)
            self.zip.pop(k, None)
            self.sample.get("ranges", {}).pop(k, None)
            for c in self.cases:
                c.pop(k, None)

    # ------------------------------------------------------------------
    def _variations(self) -> list[dict[str, Any]]:
        blocks: list[list[dict]] = []
        if self.sweep:
            keys = list(self.sweep)
            vals = [v if isinstance(v, list) else [v] for v in self.sweep.values()]
            blocks.append([dict(zip(keys, combo)) for combo in itertools.product(*vals)])
        if self.zip:
            lens = {len(v) for v in self.zip.values()}
            if len(lens) != 1:
                raise ValueError(f"zip lists must have equal length, got {lens}")
            n = lens.pop()
            blocks.append([{k: v[i] for k, v in self.zip.items()} for i in range(n)])
        if self.sample:
            blocks.append(self._sample_rows())
        rows = [{}]
        for block in blocks:
            rows = [{**a, **b} for a in rows for b in block]
        if self.cases and not blocks:
            rows = []
        rows += [dict(c) for c in self.cases]
        return rows or [{}]

    def _sample_rows(self) -> list[dict]:
        method = self.sample.get("method", "lhs")
        n = int(self.sample["n"])
        ranges = self.sample["ranges"]
        rng = np.random.default_rng(self.sample.get("seed", 0))
        keys = list(ranges)
        d = len(keys)
        if method == "lhs":
            u = (rng.permuted(np.tile(np.arange(n), (d, 1)), axis=1).T + rng.random((n, d))) / n
        elif method == "random":
            u = rng.random((n, d))
        else:
            raise ValueError(f"unknown sample method '{method}'")
        rows = []
        for r in u:
            row = {}
            for k, ui in zip(keys, r):
                lo, hi = ranges[k]
                val = lo + ui * (hi - lo)
                row[k] = int(round(val)) if isinstance(lo, int) and isinstance(hi, int) else round(float(val), 6)
            rows.append(row)
        return rows

    def expand(self, project_defaults: dict[str, Any]) -> list[Case]:
        base = copy.deepcopy(project_defaults)
        unknown = set(self.defaults) - set(base)
        rows = self._variations()
        for r in rows:
            unknown |= set(r) - set(base)
        if unknown:
            raise ValueError(
                f"study '{self.name}': unknown parameter(s) {sorted(unknown)} for project "
                f"'{self.project}'. Valid: {sorted(base)}"
            )
        base.update(self.defaults)
        varied_keys = sorted({k for r in rows for k in r})
        out: list[Case] = []
        seen: dict[str, int] = {}
        for i, r in enumerate(rows):
            params = {**base, **r}
            varied = {k: params[k] for k in varied_keys}
            name = case_name(varied) if varied else "base"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            out.append(Case(name=name, index=i, params=params, varied=varied))
        return out


def _slug_value(v: Any) -> str:
    if isinstance(v, float):
        v = f"{v:g}"
    if v == "":  # an option left at its default, e.g. keel3d's mesh_shift_only
        return "none"
    s = str(v).strip().lower()
    s = s.replace("file:", "").replace(".dat", "")
    s = re.sub(r"^-", "m", s)
    s = re.sub(r"[^a-z0-9.+]+", "", s.replace("-", "m"))
    return s or "x"


def case_name(varied: dict[str, Any]) -> str:
    name = "_".join(f"{k}{_slug_value(v)}" for k, v in varied.items())
    if len(name) > 80:
        name = "c" + params_hash(varied)[:12]
    return name
