"""Mass budget, centre of gravity and the IOM class-rule checks on them.

Positions in the boat frame, upright (x aft, y port, z up, origin at the
bow on the waterline: docs/geometry.md). Masses in kg.

Rules quoted from the IOM Class Rules 2026 (Release 2), as in
docs/research/bulb-design.md and projects/keel3d/README.md:

* C.4.1: draft 370-420 mm, in fresh water;
* C.4.2: the boat at least 4000 g;
* C.6.4: the keel, fin plus bulb (excluding fasteners to the hull),
  2200-2500 g.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ..geometry import foils
from ..geometry.keel import keel_geometry

MIN_MASS = 4.0  # C.4.2 [kg]
DRAFT = (0.370, 0.420)  # C.4.1 [m]
KEEL_MASS = (2.2, 2.5)  # C.6.4 [kg]


@dataclass(frozen=True)
class MassItem:
    name: str
    m: float  # kg
    cg: tuple[float, float, float]  # boat frame [m]
    source: str = ""  # where the number comes from (weighed, estimate, keel_geometry, ...)


@dataclass(frozen=True)
class MassBudget:
    items: list[MassItem]

    @property
    def mass(self) -> float:
        return float(sum(i.m for i in self.items))

    @property
    def cg(self) -> np.ndarray:
        """Centre of gravity of all the items (boat frame)."""
        m = self.mass
        if m <= 0:
            return np.zeros(3)
        return sum(i.m * np.asarray(i.cg, float) for i in self.items) / m

    def item(self, name: str) -> MassItem:
        for i in self.items:
            if i.name == name:
                return i
        raise KeyError(f"no mass item '{name}' (have {[i.name for i in self.items]})")

    def with_item(self, item: MassItem) -> "MassBudget":
        """A new budget with `item` added, or replacing the item of that name."""
        names = [i.name for i in self.items]
        if item.name in names:
            return MassBudget([item if i.name == item.name else i for i in self.items])
        return MassBudget([*self.items, item])

    def without(self, name: str) -> "MassBudget":
        self.item(name)
        return MassBudget([i for i in self.items if i.name != name])

    def moved(self, name: str, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> "MassBudget":
        """A new budget with item `name` moved by (dx, dy, dz) [m]."""
        i = self.item(name)
        x, y, z = i.cg
        return self.with_item(replace(i, cg=(x + dx, y + dy, z + dz)))

    @classmethod
    def from_list(cls, rows: list[dict[str, Any]]) -> "MassBudget":
        """From dicts with `name`, `m` (or `mass`) [kg], `cg` [x, y, z] (or
        `x`, `y`, `z`) [m] and optional `source`, e.g. a study's YAML."""
        items = []
        for r in rows:
            m = r["m"] if "m" in r else r["mass"]
            cg = r["cg"] if "cg" in r else (r["x"], r.get("y", 0.0), r["z"])
            items.append(MassItem(str(r["name"]), float(m), tuple(float(c) for c in cg), str(r.get("source", ""))))
        return cls(items)

    def to_rows(self, total: bool = True) -> list[dict[str, Any]]:
        """One dict per item (name, m, x, y, z, source) and a total row."""
        rows = [{"name": i.name, "m": i.m, "x": i.cg[0], "y": i.cg[1], "z": i.cg[2], "source": i.source}
                for i in self.items]
        if total:
            x, y, z = (float(c) for c in self.cg)
            rows.append({"name": "total", "m": self.mass, "x": x, "y": y, "z": z, "source": ""})
        return rows


def fill_to_minimum(budget: MassBudget, minimum: float = MIN_MASS, at=None, name: str = "corrector") -> MassBudget:
    """Add corrector weight at `at` (boat frame; default the budget's CG, so
    the CG stays put) if the boat is under `minimum` kg (C.4.2: 4000 g)."""
    short = minimum - budget.mass
    if short <= 0:
        return budget
    at = tuple(float(c) for c in (budget.cg if at is None else at))
    return budget.with_item(MassItem(name, short, at, f"fills to the {minimum:g} kg minimum (C.4.2)"))


@dataclass(frozen=True)
class RuleResult:
    clause: str
    quantity: str
    value: float
    lo: float | None  # None: no lower limit
    hi: float | None  # None: no upper limit
    ok: bool
    margin: float  # to the nearer limit; + inside, − outside (same units as value)


def _rule(clause: str, quantity: str, value: float, lo: float | None, hi: float | None,
          tol: float = 1e-9) -> RuleResult:
    gaps = []
    if lo is not None:
        gaps.append(value - lo)
    if hi is not None:
        gaps.append(hi - value)
    margin = min(gaps) if gaps else math.inf
    return RuleResult(clause, quantity, float(value), lo, hi, margin >= -tol, float(margin))


def check_rules(total_mass: float, keel_mass: float, draft: float) -> list[RuleResult]:
    """C.4.1 draft [m], C.4.2 total mass [kg] and C.6.4 keel mass [kg]. A
    value on a limit passes (to 1e-9, so a sum of parts at 2.5 kg does)."""
    k = keel_rules(keel_mass, draft)
    return [k[0], mass_rule(total_mass), k[1]]


def mass_rule(total_mass: float) -> RuleResult:
    """C.4.2: the boat's total mass [kg]."""
    return _rule("C.4.2", "total mass", total_mass, MIN_MASS, None)


def keel_rules(keel_mass: float, draft: float) -> list[RuleResult]:
    """C.4.1 draft [m] and C.6.4 keel mass [kg]."""
    return [_rule("C.4.1", "draft", draft, *DRAFT), _rule("C.6.4", "keel mass (fin + bulb)", keel_mass, *KEEL_MASS)]


def _section_centroid(section: str) -> float:
    """x/c of the area centroid of a foil section (polygon centroid)."""
    f = foils.load(section)
    x, y = f.x, f.y
    cross = x * np.roll(y, -1) - np.roll(x, -1) * y
    return float(((x + np.roll(x, -1)) * cross).sum() / (3.0 * cross.sum()))


def keel_items(p: dict[str, Any], n: int = 201, z_root: float | None = None
               ) -> tuple[list[MassItem], list[tuple[float, np.ndarray]]]:
    """Mass items and displaced volumes of the keel from a keel3d-style
    parameter dict (projects/keel3d/defaults.yaml), via `keel_geometry`.

    Returns ([fin, bulb] MassItems, [(volume m³, centroid)] for
    `Hydrostatics(appendages=...)`). The bulb's centre of mass is that of
    its lead (uniform: also the centre of its volume).

    The fin is taken as a solid, uniform section along its exposed span
    (hull bottom to the top of the bulb), so its mass and volume share a
    centroid: section area ~ c², at the section's area centroid (about
    0.42 c from the leading edge for NACA 00xx, 0.17 c aft of the quarter
    chord), on the swept quarter-chord line. For a constant chord that is
    mid-span. Approximations: a real fin is a laminate shell (its mass
    nearer half chord), and the fin's 120 g also covers the parts inside
    the hull and the bulb, which are ignored here.
    """
    g = keel_geometry(p, z_root=z_root)
    span, root, tip = g["fin_span"], g["fin_root_chord"], g["fin_tip_chord"]
    eta = np.linspace(0.0, 1.0, n)  # 0 at the root, 1 at the tip
    c = root + (tip - root) * eta
    z = g["fin_z_root"] - span * eta
    x = float(p["fin_x"]) + math.tan(math.radians(float(p["fin_sweep"]))) * span * eta \
        + (_section_centroid(p["fin_section"]) - 0.25) * c
    w = c**2 * np.r_[0.5, np.ones(n - 2), 0.5]  # trapezoidal rule
    w /= w.sum()
    fin_cg = (float(w @ x), 0.0, float(w @ z))
    items = [MassItem("fin", float(p["fin_mass"]), fin_cg, "keel3d fin_mass, solid-section centroid")]
    volumes = [(g["fin_volume_m3"], np.array(fin_cg))]
    if p.get("bulb", True):
        bulb_cg = (g["bulb_x_cg"], 0.0, g["bulb_z_cg"])
        items.append(MassItem("bulb", g["bulb_mass_kg"], bulb_cg, "keel_geometry: keel_mass - fin_mass, lead"))
        volumes.append((g["bulb_volume_m3"], np.array(bulb_cg)))
    return items, volumes
