"""Project plugins.

Each directory under projects/ is one simulation type:

    projects/<name>/
        README.md        physics, assumptions, how to read results
        defaults.yaml    every parameter with its default (the schema)
        project.py       subclass of `Project` (derive / render / extract / report)
        template/        an OpenFOAM case; files include system/caseParameters
        studies/         *.yaml study definitions

Rendering a case = copy template + write system/caseParameters (+ any
generated geometry/mesh). After that the case is a plain OpenFOAM case that
runs with ./Allrun, with or without Python.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from . import config
from .foam import write_dict


class Project:
    name: str = ""
    def __init__(self, root: Path):
        self.root = Path(root)
        self.template = self.root / "template"
        from .study import coerce_numbers

        self.defaults: dict[str, Any] = coerce_numbers(yaml.safe_load((self.root / "defaults.yaml").read_text()) or {})

    # -- hooks -------------------------------------------------------------
    def derive(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return derived quantities (Reynolds number, inflow vectors, ...)."""
        return {}

    def render(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> None:
        """Populate case_dir (already a copy of the template)."""
        self.write_parameters(case_dir, derived, inputs=params)

    def converged(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> bool:
        """Polled while the solver runs; return True to stop it (writeNow)."""
        return False

    def progress(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
        """Polled while the solver runs: numbers for the progress line in the
        job log (latest forces, how far they still drift). See monitor.py."""
        return {}

    def diverged(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> str | None:
        """Polled while the solver runs: a reason if the solution has blown up
        (the runner then stops the case), else None. The runner also checks
        the time step, Courant number and a stalled solver (monitor.py)."""
        return None

    def checkpoint_setup(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> bool | str:
        """Called on a rendered case when the run keeps checkpoints
        (checkpoint.py). Every case must be resumable after a lost Spot VM:
        * "signal" (the default): the runner makes the solver write its fields
          every checkpoint interval (writeNowSignal) and saves them;
        * True: the project has made the solver write periodically itself;
        * False: this case can't be resumed. Don't: a preempted task then
          starts from scratch.
        The template's Allrun must go straight to the solver when
        IOMCFD_RESUME is set (the mesh and a time directory were restored);
        tests/test_projects.py checks every project."""
        return "signal"

    def checkpoint_restored(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any],
                            time: str) -> None:
        """Called after a checkpoint's time directory was copied into the
        rendered case, before the solver starts from it."""

    def extract(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
        """Parse solver output into a flat dict of metrics."""
        return {}

    def report(self, df, out_dir: Path, reference=None, options=None) -> list[Path]:  # pragma: no cover - host only
        """Make plots from the collected results (pandas DataFrame).

        `reference` is the study's reference-data table (DataFrame) or None;
        `options` the study's `report:` block (dict) or None.
        """
        return []

    # result columns of the highlights table (default: summary_keys)
    highlight_columns: list[str] = []

    def highlight_report(self, run_dir: Path, df, highlights, out_dir: Path) -> list[Path]:  # pragma: no cover - host only
        """Figures and tables for the study's highlights that need no field
        data (`highlights`: [(Highlight, Layout)], see iomcfd.highlights).
        Default: report/highlights.md, one table per highlight. Projects add
        figures (file names starting with 'highlight')."""
        from .highlights import write_table

        cols = self.highlight_columns or list(getattr(self, "summary_keys", []))
        return [write_table(highlights, df, cols, Path(out_dir) / "highlights.md")]

    def load_reference(self, rel: str | None):
        """Read a study's `reference:` CSV (comment lines start with #)."""
        if not rel:
            return None
        import pandas as pd

        return pd.read_csv(self.root / rel, comment="#")

    def mesh_views(self, case_dir: Path, params: dict[str, Any], derived: dict[str, Any]):
        """Views for the report's mesh figure (iomcfd.meshplot.MeshSpec).

        Default: x-y and x-z cuts through the middle of a box domain
        (xMin..zMax in the derived values), or None if there is none.
        """
        from .meshplot import MeshSpec, MeshView

        d = derived
        if not all(k in d for k in ("xMin", "xMax", "yMin", "yMax", "zMin", "zMax")):
            return None
        c = [(d["xMin"] + d["xMax"]) / 2, (d["yMin"] + d["yMax"]) / 2, (d["zMin"] + d["zMax"]) / 2]
        w = 1.05 * (d["xMax"] - d["xMin"])
        return MeshSpec(
            [
                MeshView("plane z = mid-domain", tuple(c), (0, 0, 1), (0, 1), (c[0], c[1]), w),
                MeshView("plane y = mid-domain", tuple(c), (0, 1, 0), (0, 2), (c[0], c[2]), w, ("x [m]", "z [m]")),
            ],
            walls="^$",
        )

    def resources(self, params: dict[str, Any]) -> dict[str, Any]:
        """Hints for cloud scheduling: cpus per case, memory, max runtime."""
        return {"cpus": int(params.get("np", 1)), "memory_gb": 2 * int(params.get("np", 1)), "max_hours": 2}

    # -- helpers -------------------------------------------------------------
    def write_parameters(self, case_dir: Path, values: dict[str, Any], inputs: dict[str, Any] | None = None) -> None:
        """Write system/caseParameters.

        `values` become OpenFOAM entries ($name in the template files); use
        names that cannot clash with OpenFOAM keywords (camelCase derived
        quantities). The study `inputs` are recorded as comments only, because
        names like `geometry` or `mesh` mean something to OpenFOAM utilities.
        """
        entries = {}
        for k, v in values.items():
            if v is None or isinstance(v, dict):
                continue
            if isinstance(v, list) and not all(isinstance(x, (int, float)) for x in v):
                continue
            entries[k] = v
        header = ""
        if inputs:
            header = "// Study inputs (for reference; not read by OpenFOAM):\n" + "".join(
                f"//   {k:<22} {json.dumps(v, default=str)}\n" for k, v in inputs.items()
            ) + "\n"
        write_dict(Path(case_dir) / "system" / "caseParameters", entries, obj="caseParameters", preamble=header)

    def prepare_case(self, case_dir: Path, params: dict[str, Any]) -> dict[str, Any]:
        """Copy the template and render a case. Returns derived values."""
        case_dir = Path(case_dir)
        if case_dir.exists():
            shutil.rmtree(case_dir)
        shutil.copytree(self.template, case_dir, symlinks=True)
        derived = self.derive(params)
        self.render(case_dir, params, derived)
        (case_dir / "params.json").write_text(
            json.dumps({"params": params, "derived": derived}, indent=2, default=str) + "\n"
        )
        return derived


def load_project(name: str) -> Project:
    root = config.projects_dir() / name
    mod_path = root / "project.py"
    if not mod_path.is_file():
        raise FileNotFoundError(f"project '{name}' not found at {root}")
    spec = importlib.util.spec_from_file_location(f"iomcfd_projects.{name}", mod_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    classes = [
        v for v in vars(mod).values() if isinstance(v, type) and issubclass(v, Project) and v is not Project
    ]
    if len(classes) != 1:
        raise RuntimeError(f"{mod_path} must define exactly one Project subclass")
    return classes[0](root)


def list_projects() -> list[str]:
    return sorted(p.name for p in config.projects_dir().iterdir() if (p / "project.py").is_file())
