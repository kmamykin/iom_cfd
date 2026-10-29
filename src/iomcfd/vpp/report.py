"""Files a VPP run writes: polar.csv, vmg.csv / race.csv, rates.csv, a polar
plot, summary.md and report.html (the run's CSVs embedded in one page,
report_template.html)."""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

import yaml

from .race import Course, RaceRow, boat_lengths, distance, weighted
from .rates import Rate
from .solver import Point


def write_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def polar_figure(points: list[Point], race_rows: list[RaceRow] | None, path: Path,
                 title: str = "") -> Path:  # pragma: no cover - plotting
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(6.5, 7))
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    for tws in sorted({p.tws for p in points}):
        ps = sorted((p for p in points if p.tws == tws and p.converged), key=lambda p: p.twa)
        if ps:
            ax.plot([math.radians(p.twa) for p in ps], [p.V for p in ps], label=f"{tws:g} m/s")
    for r in race_rows or []:
        for p in (r.up, r.down):
            if p.converged:
                ax.plot(math.radians(p.twa), p.V, "k.", ms=5)
    ax.set_xlabel("V_b [m/s] against β_TW (from the course)")
    ax.legend(title="V_TW", loc="lower left", bbox_to_anchor=(0.0, -0.1), fontsize=8)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def summary_md(path: Path, boat: str, info: dict, rows: list[RaceRow], course: Course,
               rates_rows: list[Rate] | None = None, rate_summary: dict | None = None,
               warnings: list[str] | None = None) -> Path:
    t = weighted(rows)
    L = [f"# VPP: {boat}", ""]
    for k, v in info.items():
        L.append(f"* {k}: {v}")
    L += ["", "Results are relative to the model (no real-world calibration). Downwind is lower confidence.", ""]
    keys = list(rows[0].up.controls) if rows else []
    L += ["## Race", "",
          f"W/L course: {course.laps} laps of {course.leg:g} m, {course.tacks_per_leg:g} tacks "
          f"({course.tack_s:g} s) and {course.gybes_per_leg:g} gybes ({course.gybe_s:g} s) per leg; "
          f"{distance(course):g} m along the wind.", "",
          "| TWS m/s | weight | β_TW up | V_b up | VMG up | heel up | leeway up | "
          + "".join(f"{k} up | " for k in keys) + "β_TW down | VMG down | race s |",
          "|" + "---|" * (10 + len(keys))]
    for r in rows:
        L.append(f"| {r.tws:g} | {r.weight:g} | {r.up.twa:.1f} | {r.up.V:.3f} | {r.up.vmg:.3f} | {r.up.heel:.1f} | "
                 f"{r.up.leeway:.2f} | " + "".join(f"{r.up.controls.get(k, math.nan):.2f} | " for k in keys)
                 + f"{r.down.twa:.1f} | {-r.down.vmg:.3f} | {r.t:.1f} |")
    L += ["", f"Weighted race time: {t:.1f} s.", ""]
    if rate_summary:
        L += ["## Exchange rates", "",
              "Change in weighted race time (and boat lengths over the race) per perturbation, re-timed at the "
              "baseline's best-VMG angles and optimised controls (envelope theorem).", "",
              "| perturbation | race time % | boat lengths |", "|---|---|---|"]
        for name, pct in rate_summary.items():
            L.append(f"| {name} | {pct:+.3f} | {boat_lengths(pct / 100 * t, t, course):+.2f} |")
        vd = [r for r in rates_rows or [] if math.isfinite(r.vdrdv_up)]
        if vd:
            L += ["", "V dR/dV implied by the drag step (compare racetime.VDRDV, 1.354 N at 1 m/s):", "",
                  "| TWS m/s | V_b up | V dR/dV up N | V_b down | V dR/dV down N |", "|---|---|---|---|---|"]
            byt = {r.tws: r for r in rows}
            for r in vd:
                L.append(f"| {r.tws:g} | {byt[r.tws].up.V:.3f} | {r.vdrdv_up:.3f} | {byt[r.tws].down.V:.3f} | "
                         f"{r.vdrdv_down:.3f} |")
    if warnings:
        L += ["", "## Warnings", ""] + [f"* {w}" for w in warnings]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n")
    return path


TEMPLATE = Path(__file__).parent / "report_template.html"
CSVS = ("polar", "vmg", "race", "rates", "rates_summary", "mass", "hydro", "particulars", "response")
ORC = ("_CL", "_CD")  # the ORC 2026 sail coefficients: copyright ORC, kept off the page


def _without_orc(text: str) -> str:
    """The CSV without its ORC coefficient columns (cells unchanged)."""
    rows = list(csv.reader(io.StringIO(text)))
    keep = [i for i, k in enumerate(rows[0] if rows else []) if not k.endswith(ORC)]
    if not rows or len(keep) == len(rows[0]):
        return text
    buf = io.StringIO()
    csv.writer(buf).writerows([[r[i] for i in keep] for r in rows])
    return buf.getvalue()


def _text(path: Path) -> str:
    with open(path, newline="") as f:  # as written: csv's \r\n line ends kept
        return f.read()


def _block(kind: str, name: str, text: str) -> str:
    """A <script> data block; "</" escaped (the page undoes it)."""
    esc = text.replace("</", "<\\/")
    return f'<script type="{kind}" data-file="{name}">{esc}</script>'


def html_report(run_dir: str | Path) -> Path:
    """report.html in a run folder: its CSVs, run.json and boat.yaml
    embedded as they are (the ORC columns dropped), drawn by the template."""
    run_dir = Path(run_dir)
    blocks = [_block("text/csv", f"{n}.csv", _without_orc(_text(run_dir / f"{n}.csv")))
              for n in CSVS if (run_dir / f"{n}.csv").is_file()]
    run = json.loads((run_dir / "run.json").read_text())
    boat = _text(run_dir / "boat.yaml")
    blocks += [_block("application/json", "run.json", json.dumps(run)),
               _block("application/json", "boat.json", json.dumps(yaml.safe_load(boat), default=str)),
               _block("text/plain", "boat.yaml", boat)]
    title = f"{run.get('boat', 'boat')} · VPP run {run_dir.name}".replace("&", "&amp;").replace("<", "&lt;")
    html = TEMPLATE.read_text().replace("__TITLE__", title).replace("__DATA__", "\n".join(blocks))
    out = run_dir / "report.html"
    out.write_text(html)
    return out
