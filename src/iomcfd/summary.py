"""report/summary.md: the facts of one run, for people and for the findings
agent (.claude/skills/study-findings): what was run, what finished, what
failed and why, where the solver struggled, compute used, and the report
files to read. Facts only; interpretation goes in the findings log
(projects/<project>/findings/<study>.md)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import RESULT

_REASONS = ("FOAM FATAL", "Floating point exception", "Segmentation fault", "Killed", "Error", "error")


def failure_reason(case_dir: Path) -> str:
    """One line: why a case failed (from result.json)."""
    try:
        err = str(json.loads((Path(case_dir) / RESULT).read_text()).get("error", ""))
    except (OSError, json.JSONDecodeError):
        return "no result.json"
    lines = [ln.strip() for ln in err.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    for key in _REASONS:
        for i, ln in enumerate(lines):
            if key in ln:
                if key == "FOAM FATAL":  # the message is on the following lines
                    return " ".join(lines[i : i + 3])[:200]
                return ln[:200]
    return (lines[-1] if lines else "unknown")[:200]


def _flag(df, col: str):
    import pandas as pd

    return df[col].astype(str) == "True" if col in df else pd.Series(False, index=df.index)


def _by_param(df, mask, varied: list[str]) -> list[str]:
    """'aoa: 4 (22), 6 (14)' per varied parameter, for the rows in mask."""
    out = []
    for k in varied:
        if k not in df:
            continue
        counts = df[mask][k].value_counts().sort_index()
        if counts.empty:
            continue
        total = df[k].value_counts()
        out.append(f"{k}: " + ", ".join(f"{v} ({n}/{total.get(v, n)})" for v, n in counts.items()))
    return out


def write_summary(rdir: Path, study, cases, df, report_files: list[Path]) -> Path:
    rdir = Path(rdir)
    info: dict[str, Any] = {}
    if (rdir / "run.json").is_file():
        info = json.loads((rdir / "run.json").read_text())
    varied = list(cases[0].varied) if cases else []
    L = [f"# {study.name}, run {rdir.name}", ""]
    L += [f"* project: {study.project}; study file: {rdir / 'study.yaml'} (as run)"]
    for k in ("created", "git", "image", "backend", "job", "machine"):
        if info.get(k):
            L.append(f"* {k}: {info[k]}")
    if info.get("overrides"):
        L.append(f"* overrides (--set): {info['overrides']}")
    L.append(f"* cases: {len(df)} of {len(cases)} in the study")
    if varied:
        L += ["", "## Swept parameters", ""]
        for k in varied:
            vals = sorted({c.varied[k] for c in cases}, key=lambda v: (isinstance(v, str), v))
            L.append(f"* {k}: {', '.join(str(v) for v in vals)}")
    fixed = {k: v for k, v in (study.defaults or {}).items() if k not in varied}
    if fixed:
        L += ["", "Study defaults (fixed for every case): " + ", ".join(f"{k} = {v}" for k, v in fixed.items())]

    L += ["", "## Status", ""]
    counts = df["status"].value_counts()
    L += [f"* {s}: {n}" for s, n in counts.items()]
    failed = df[df["status"] == "failed"]
    if not failed.empty:
        L += ["", "Failed cases:", ""]
        L += [f"* {c}: {failure_reason(rdir / c)}" for c in failed["case"]]
        L += [f"  * by {x}" for x in _by_param(df, df["status"] == "failed", varied)]
    nc = df["status"] == "not_converged"
    if nc.any():
        L += ["", f"Not converged ({int(nc.sum())}: hit the iteration limit; the window average is still reported), "
              "count (of all cases with that value):", ""]
        L += [f"* {x}" for x in _by_param(df, nc, varied)]
    uns = _flag(df, "unsteady") & df["status"].isin(["ok", "not_converged"])
    if uns.any():
        L += ["", f"Unsteady ({int(uns.sum())}: force coefficients still oscillate over the averaging window; "
              "steady answers of unsteady flow are less certain):", ""]
        L += [f"* {x}" for x in _by_param(df, uns, varied)]

    drift = _flag(df, "drifting") & df["status"].isin(["ok", "not_converged"])
    if drift.any():
        L += ["", f"Drifting ({int(drift.sum())}: transient cases whose Cl or Cd mean still changes across the "
              "averaging window; run them longer, see report/transient.md):", ""]
        L += [f"* {x}" for x in _by_param(df, drift, varied)]

    if "wall_time_s" in df and df["wall_time_s"].notna().any():
        w = df["wall_time_s"].dropna() / 60
        L += ["", "## Compute", "",
              f"* case wall time [min]: median {w.median():.1f}, mean {w.mean():.1f}, max {w.max():.1f}; "
              f"total {w.sum() / 60:.1f} case-hours"]
        if "iterations" in df and df["iterations"].notna().any():
            it = df["iterations"].dropna()
            L.append(f"* iterations: median {it.median():.0f}, max {it.max():.0f}")
        if "n_cells" in df and df["n_cells"].notna().any():
            L.append(f"* cells: {df['n_cells'].min():.0f} to {df['n_cells'].max():.0f}")

    others = [f for f in report_files if Path(f).name != "summary.md"]
    if others:
        L += ["", "## Report files", ""]
        L += [f"* {Path(f).relative_to(rdir) if Path(f).is_relative_to(rdir) else f}" for f in others]
    tables = [Path(f) for f in others if Path(f).suffix == ".md"]
    for t in tables:  # project comparison tables, inline so one file has the numbers
        L += ["", t.read_text().strip()]
    out = rdir / "report" / "summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    return out
