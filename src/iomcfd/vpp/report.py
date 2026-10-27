"""Files a VPP run writes: polar.csv, vmg.csv / race.csv, rates.csv, a polar
plot and summary.md."""

from __future__ import annotations

import csv
import math
from pathlib import Path

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
