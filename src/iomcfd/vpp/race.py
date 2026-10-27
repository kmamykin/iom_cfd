"""Windward-leeward race time from the best VMG upwind and downwind.

Each lap is one beat and one run of `leg` metres measured along the wind,
plus a fixed time per tack and per gybe. The race time per true wind speed is
kept, so a different wind weighting (a club histogram) needs no new solve.
Downwind numbers are flagged lower confidence: the sails there are
separated and goose-winged, where the sail model is weakest.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

from .solver import Boat, Point, best_vmg


@dataclass
class Course:
    leg: float = 100.0  # m along the wind, windward mark to leeward mark
    laps: int = 2
    tacks_per_leg: float = 4.0
    gybes_per_leg: float = 2.0
    tack_s: float = 3.0  # time lost per tack [s]
    gybe_s: float = 2.0
    boat_length: float = 1.0  # m, to express time as boat lengths

    def leg_times(self, vmg_up: float, vmg_down: float) -> tuple[float, float]:
        up = self.leg / vmg_up + self.tacks_per_leg * self.tack_s if vmg_up > 0 else math.inf
        down = self.leg / vmg_down + self.gybes_per_leg * self.gybe_s if vmg_down > 0 else math.inf
        return up, down


@dataclass
class WindRange:
    tws: list[float]
    weights: list[float] = field(default_factory=list)  # empty = uniform
    z_ref: float = 1.0  # height the tws is given at [m]
    alpha: float = 0.0  # power-law profile exponent

    def __post_init__(self):
        if not self.weights:
            self.weights = [1.0] * len(self.tws)
        if len(self.weights) != len(self.tws):
            raise ValueError("wind weights and tws differ in length")

    @staticmethod
    def from_histogram(path: str | Path, z_ref: float = 1.0, alpha: float = 0.0) -> "WindRange":
        """A CSV with columns tws (m/s) and weight (e.g. hours or race count)."""
        with open(path) as f:
            rows = list(csv.DictReader(f))
        return WindRange([float(r["tws"]) for r in rows], [float(r["weight"]) for r in rows], z_ref, alpha)


@dataclass
class RaceRow:
    tws: float
    weight: float
    up: Point
    down: Point
    t_up: float  # s, all upwind legs
    t_down: float
    t: float

    def row(self) -> dict:
        return {"tws": self.tws, "weight": self.weight,
                "twa_up": self.up.twa, "V_up": self.up.V, "vmg_up": self.up.vmg, "heel_up": self.up.heel,
                "leeway_up": self.up.leeway, **{f"{k}_up": v for k, v in self.up.controls.items()},
                "twa_down": self.down.twa, "V_down": self.down.V, "vmg_down": -self.down.vmg,
                **{f"{k}_down": v for k, v in self.down.controls.items()},
                "t_up_s": self.t_up, "t_down_s": self.t_down, "t_s": self.t,
                "flags_up": " ".join(self.up.flags), "flags_down": " ".join(self.down.flags)}


def race_row(course: Course, tws: float, weight: float, up: Point, down: Point) -> RaceRow:
    tu, td = course.leg_times(up.vmg if up.converged else 0.0, -down.vmg if down.converged else 0.0)
    return RaceRow(tws, weight, up, down, course.laps * tu, course.laps * td, course.laps * (tu + td))


def race(boat: Boat, wind: WindRange, course: Course) -> list[RaceRow]:
    rows, up, down = [], None, None
    for v, wt in zip(wind.tws, wind.weights):
        up = best_vmg(boat, v, "up", wind.z_ref, wind.alpha, guess=up if up and up.converged else None)
        down = best_vmg(boat, v, "down", wind.z_ref, wind.alpha, guess=down if down and down.converged else None)
        rows.append(race_row(course, v, wt, up, down))
    return rows


def weighted(rows: list[RaceRow], attr: str = "t") -> float:
    w = sum(r.weight for r in rows)
    return sum(r.weight * getattr(r, attr) for r in rows) / w


def distance(course: Course) -> float:
    """Metres sailed along the wind in a race."""
    return 2 * course.laps * course.leg


def boat_lengths(dt: float, t: float, course: Course) -> float:
    """A time difference as boat lengths at the race's mean speed along the wind."""
    return dt * distance(course) / t / course.boat_length
