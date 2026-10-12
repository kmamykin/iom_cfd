"""Highlights: the few cases of a run worth a close look, named in the study
file and chosen from earlier findings, so a 450-case run is not inspected
(or downloaded) case by case.

    highlights:
      - name: thickness-at-working-load          # [A-Za-z0-9_-], used in file names
        why: why thin sections lose at working load (bubble, transition)
        where: {speed: 1.0, chord: 0.08, aoa: [4, 6]}   # parameter: value or list
        compare: foil                  # side by side (default: the parameter with most values)
        views: [separation, transition]  # ParaView views (default: the study's / project's)

`where` matches the cases' full parameters (swept or fixed). Within one
highlight, the cases are laid out as a grid: one column per value of
`compare`, one row per combination of the other parameters that still vary.

Used by `iomcfd report` (project figures and tables that need no field data,
report/highlights.md), `iomcfd viz` (renders only these cases, plus one
montage per highlight and view) and `iomcfd gcp fetch --fields` (downloads
field data only for these cases).

Highlights are post-processing: what to look at often follows from a run's
results. So they come from the current study file, falling back to the run's
own copy if the current file has none (see `resolve`).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Highlight:
    name: str
    why: str = ""
    where: dict[str, Any] = field(default_factory=dict)
    compare: str | None = None
    views: list[str] | None = None


@dataclass
class Layout:
    """A highlight's cases as a grid: columns = values of `compare`, rows =
    combinations of the other parameters that vary within the selection."""

    compare: str | None
    columns: list[Any]
    row_keys: list[str]
    rows: list[tuple[str, dict[Any, Any]]]  # (row label, {column value: case})

    @property
    def cases(self) -> list:
        return [c for _, cells in self.rows for c in cells.values()]


def parse(raw: list | None, source: str = "study") -> list[Highlight]:
    out, seen = [], set()
    for i, h in enumerate(raw or []):
        if not isinstance(h, dict) or not h.get("name"):
            raise ValueError(f"{source}: highlights[{i}] needs a name")
        unknown = set(h) - {"name", "why", "where", "compare", "views"}
        if unknown:
            raise ValueError(f"{source}: highlight '{h['name']}': unknown keys {sorted(unknown)}")
        name = str(h["name"])
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name in seen:
            raise ValueError(f"{source}: highlight name '{name}' must be unique and [A-Za-z0-9_-]")
        seen.add(name)
        views = h.get("views")
        out.append(Highlight(name, str(h.get("why") or "").strip(), dict(h.get("where") or {}),
                             h.get("compare"), [views] if isinstance(views, str) else views))
    return out


def resolve(current, snapshot) -> tuple[list[Highlight], str]:
    """Highlights for post-processing a run: the current study file's, else
    the run's copy. Returns (highlights, the file they came from)."""
    for st in (current, snapshot):
        if st is not None and st.highlights:
            return st.highlights, st.highlights_from
    return [], ""


def _same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
    except (TypeError, ValueError):
        return str(a) == str(b)


def matches(case, where: dict[str, Any]) -> bool:
    for k, want in where.items():
        if k not in case.params:
            return False
        wanted = want if isinstance(want, list) else [want]
        if not any(_same(case.params[k], w) for w in wanted):
            return False
    return True


def select(h: Highlight, cases: list) -> list:
    """The cases of `h`, in study order. Raises ValueError for a parameter the
    cases don't have (typo, or a highlight written for another run)."""
    if cases:
        unknown = set(h.where) - set(cases[0].params)
        if unknown:
            raise ValueError(f"highlight '{h.name}': unknown parameter(s) {sorted(unknown)}")
    return [c for c in cases if matches(c, h.where)]


def _order(values: list, cases: list, key: str) -> list:
    """Numbers ascending; words (foil names, mesh levels) in study order."""
    nums = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)
    if nums:
        return sorted(values)
    first = {}
    for c in cases:
        first.setdefault(str(c.params[key]), c.index)
    return sorted(values, key=lambda v: first.get(str(v), 0))


def layout(h: Highlight, cases: list) -> Layout:
    """Grid of the selected `cases` (see Layout)."""
    if not cases:
        return Layout(h.compare, [], [], [])
    varied = [k for k in cases[0].varied if len({str(c.params[k]) for c in cases}) > 1]
    cmp = h.compare
    if cmp is not None and cmp not in cases[0].params:
        raise ValueError(f"highlight '{h.name}': compare '{cmp}' is not a parameter")
    if cmp is None and varied:
        cmp = max(varied, key=lambda k: (len({str(c.params[k]) for c in cases}), -varied.index(k)))
    others = [k for k in varied if k != cmp]
    columns = _order(list({str(c.params[cmp]): c.params[cmp] for c in cases}.values()), cases, cmp) if cmp else [None]
    groups: dict[tuple, dict] = {}
    for c in cases:
        key = tuple(c.params[k] for k in others)
        groups.setdefault(key, {})[c.params[cmp] if cmp else None] = c
    keys = list(groups)
    for i in reversed(range(len(others))):  # sort rows by each parameter, numbers ascending
        vals = _order(list({str(k[i]): k[i] for k in keys}.values()), cases, others[i])
        pos = {str(v): j for j, v in enumerate(vals)}
        keys.sort(key=lambda k: pos[str(k[i])])
    rows = [(", ".join(f"{k} {_fmt(v)}" for k, v in zip(others, key)), groups[key]) for key in keys]
    return Layout(cmp, columns, others, rows)


def _fmt(v) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def plan(highlights: list[Highlight], cases: list, log=print) -> list[tuple[Highlight, Layout]]:
    """Select and lay out every highlight; skip (with a message) those that
    select nothing or don't fit this run's parameters."""
    out = []
    for h in highlights:
        try:
            sel = select(h, cases)
            lay = layout(h, sel)
        except ValueError as exc:
            log(f"  highlight skipped: {exc}")
            continue
        if not sel:
            log(f"  highlight '{h.name}' selects no case of this run: {h.where}")
            continue
        out.append((h, lay))
    return out


def case_names(planned: list[tuple[Highlight, Layout]]) -> list[str]:
    seen: dict[str, None] = {}
    for _, lay in planned:
        for c in lay.cases:
            seen.setdefault(c.name)
    return list(seen)


def write_table(planned, df, columns: list[str], out_path) -> Any:
    """report/highlights.md: per highlight, why, and one row per case with
    the given result columns."""
    import pandas as pd

    by_case = df.set_index("case") if "case" in df else pd.DataFrame()
    L = ["## Highlights", "",
         "Cases named in the study's `highlights:`, chosen from earlier findings. Figures: "
         "report/highlight_<name>.png; ParaView montages (after `iomcfd viz`): viz/highlights/.", ""]
    for h, lay in planned:
        L += [f"### {h.name}", ""]
        if h.why:
            L += [h.why, ""]
        L += [f"Selection: {', '.join(f'{k} = {v}' for k, v in h.where.items()) or 'all cases'}; "
              f"compared along {lay.compare or '-'}.", ""]
        params = lay.row_keys + ([lay.compare] if lay.compare else [])
        cols = [c for c in ["status", *columns] if c in by_case.columns]
        L.append("| " + " | ".join([*params, *cols]) + " |")
        L.append("|" + "---|" * (len(params) + len(cols)))
        for _, cells in lay.rows:
            for col in lay.columns:
                c = cells.get(col)
                if c is None:
                    continue
                vals = [_fmt(c.params[k]) for k in params]
                row = by_case.loc[c.name] if c.name in by_case.index else None
                for k in cols:
                    v = None if row is None else row.get(k)
                    vals.append("-" if v is None or (isinstance(v, float) and math.isnan(v))
                                else (f"{v:.4g}" if isinstance(v, float) else str(v)))
                L.append("| " + " | ".join(vals) + " |")
        L.append("")
    out_path.write_text("\n".join(L))
    return out_path
