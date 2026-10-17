"""The project website (site/, GitHub Pages): its data, figures and build.

The page, site/index.qmd, is written by hand. Its charts are drawn by
site/figures.py from small CSV files in site/data/, which are committed, so
the site builds without runs/. site/data.yaml says which run each data file
comes from; `iomcfd site export` copies it out of the local runs (a light
`gcp fetch` is enough for tables) and records the source in
site/data/sources.json. Pictures and videos that can't be rebuilt online
(ParaView renders) are copied the same way into site/assets/.

    iomcfd site export [NAME ...]    refresh data files from runs (data.yaml)
    iomcfd site build [--preview]    draw the figures, then quarto render (or preview)
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from . import config

# Quarto from PyPI when it is not installed (`uvx`); CI installs the same version.
QUARTO_VERSION = "1.10.19"
KINDS = ("table", "force_history", "file", "manual")


def site_dir() -> Path:
    return config.home() / "site"


def manifest(site: Path | None = None) -> dict[str, dict[str, Any]]:
    site = site or site_dir()
    entries = yaml.safe_load((site / "data.yaml").read_text()) or {}
    for name, e in entries.items():
        kind = e.setdefault("kind", "table")
        if kind not in KINDS:
            raise ValueError(f"site/data.yaml {name}: kind must be one of {KINDS}, got '{kind}'")
        if kind == "manual" and not e.get("source"):
            raise ValueError(f"site/data.yaml {name}: a manual entry needs a `source`")
        if kind != "manual" and not (e.get("study") and e.get("runs")):
            raise ValueError(f"site/data.yaml {name}: needs `study` and `runs`")
    return entries


def output_path(site: Path, name: str, entry: dict[str, Any]) -> Path:
    """site/assets/<name><suffix of the source> for files, else site/data/<name>.csv."""
    if entry["kind"] == "file":
        return site / "assets" / (name + Path(entry["file"]).suffix)
    return site / "data" / f"{name}.csv"


def _run_dir(study: str, run: str) -> Path:
    d = config.runs_dir() / study / str(run)
    if not d.is_dir():
        raise FileNotFoundError(f"{d} is not here: `uv run iomcfd gcp fetch <project>/{study} --run-id {run}` "
                                "(results only; add --fields for pictures of highlighted cases)")
    return d


def _table(entry: dict[str, Any]):
    import pandas as pd

    files = entry["file"] if isinstance(entry["file"], list) else [entry["file"]]
    frames = []
    for run in entry["runs"]:
        for name in files:
            df = pd.read_csv(_run_dir(entry["study"], run) / name)
            if len(files) > 1:
                df.insert(0, "file", name)
            df.insert(0, "run", str(run))
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    for col, want in (entry.get("where") or {}).items():
        df = df[df[col].isin(want if isinstance(want, list) else [want])]
    if entry.get("columns"):
        df = df[["run", *entry["columns"]]]
    return df


def _force_history(entry: dict[str, Any]):
    import pandas as pd

    from .project import load_project

    project = load_project(entry.get("project", "foil2d"))
    frames = []
    for run in entry["runs"]:
        rdir = _run_dir(entry["study"], run)
        for case in entry["cases"]:
            cdir = rdir / case
            h = project.force_history(cdir)
            if h is None:
                raise FileNotFoundError(f"{cdir}: no force history (postProcessing/forceCoeffs or force_history.csv)")
            flow_time = json.loads((cdir / "params.json").read_text())["derived"]["flowTime"]
            step = int(entry.get("every", 1))
            frames.append(pd.DataFrame({"run": str(run), "case": case, "flow_times": h[::step, 0] / flow_time,
                                        "Cl": h[::step, 1], "Cd": h[::step, 2]}))
    df = pd.concat(frames, ignore_index=True)
    return df if len(entry["runs"]) > 1 else df.drop(columns="run")


def export(names: list[str] | None = None, site: Path | None = None) -> list[Path]:
    """Refresh the named entries of site/data.yaml (default: all) from the
    local runs and record their sources. Manual entries are only checked."""
    site = site or site_dir()
    entries = manifest(site)
    unknown = set(names or []) - set(entries)
    if unknown:
        raise SystemExit(f"not in site/data.yaml: {', '.join(sorted(unknown))}")
    src_file = site / "data" / "sources.json"
    sources = json.loads(src_file.read_text()) if src_file.is_file() else {}
    sources = {k: v for k, v in sources.items() if k in entries}  # entries removed from data.yaml
    written = []
    for name, e in entries.items():
        if names and name not in names:
            continue
        out = output_path(site, name, e)
        out.parent.mkdir(parents=True, exist_ok=True)
        if e["kind"] == "manual":
            if not out.is_file():
                raise FileNotFoundError(f"{out}: manual data file missing (source: {e['source']})")
            sources[name] = {"kind": "manual", "file": out.relative_to(site).as_posix(), "source": e["source"]}
            continue
        if e["kind"] == "file":
            (run,) = e["runs"]
            shutil.copyfile(_run_dir(e["study"], run) / e["file"], out)
        else:
            df = _table(e) if e["kind"] == "table" else _force_history(e)
            df.to_csv(out, index=False, float_format=f"%.{int(e.get('digits', 6))}g")
        sources[name] = {
            "kind": e["kind"],
            "file": out.relative_to(site).as_posix(),
            "study": e["study"],
            "runs": [str(r) for r in e["runs"]],
            "source": e.get("file") or e.get("cases"),
            "exported": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"),
            "git": config.git_describe(),
        }
        written.append(out)
    src_file.write_text(json.dumps(dict(sorted(sources.items())), indent=2) + "\n")
    return written


def figures(site: Path | None = None) -> list[Path]:
    """Run site/figures.py: every chart from site/data/ into site/_generated/."""
    site = site or site_dir()
    spec = importlib.util.spec_from_file_location("iomcfd_site_figures", site / "figures.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.make_all(site / "data", site / "_generated")


def quarto() -> list[str]:
    exe = shutil.which("quarto")
    return [exe] if exe else ["uvx", "--from", f"quarto-cli=={QUARTO_VERSION}", "quarto"]


def build(preview: bool = False, site: Path | None = None) -> None:
    site = site or site_dir()
    for f in figures(site):
        print(f.relative_to(site))
    subprocess.run([*quarto(), "preview" if preview else "render", str(site)], check=True)
    if not preview:
        print(f"site: {site / '_site' / 'index.html'}")
