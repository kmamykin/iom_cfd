"""What every part of the boat gives the solver.

A part (hull, keel, rudder, sails, windage) is a shape (geometry, mass,
buoyant volume, where other parts mount) and a force model that maps the
boat's state and the wind to `Loads`: forces in the course frame and moments
about the boat frame origin (bow, waterline, centreline), with the signs of
the balance equations in docs/nomenclature.md (port tack):

    X  along the course, + forward      (T_a = X_aero, D_h = −X_hydro)
    Y  across the course, + to windward (S_h = Y_hydro, S_a = −Y_aero)
    Z  vertical, + up
    K  roll, + heels to starboard        (M_a, M_h,dyn)
    M  pitch, + bow down
    N  yaw, + bow to port (to windward)  (N_a, N_h)

The steady state is ΣX = 0, ΣY = 0, ΣK = RM_φ and ΣN = 0; ΣZ and ΣM set
sinkage and trim through the hydrostatics. Moment arms ignore the small
rotation of the boat by the leeway (cos β_Y ≈ 1).

The solver sees only `Component`: a name, a kind, whether its loads depend
on sinkage and trim, the `Control`s it declares and `loads()`. A control is
a variable of the boat the solver sets: a balance unknown (the rudder angle
closes ΣN = 0), an optimised trim (the sails' flat), a discrete choice (the
sail set) or a held value. Its key is "<part>.<name>"; its value reaches
the force models in `State.controls`.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Protocol

from .. import frames

ROLES = ("balance", "optimise", "choice", "hold")


@dataclass(frozen=True)
class Control:
    name: str  # the part's own name for it: "angle", "flat", "set"
    role: str  # balance (a yaw-balance unknown) | optimise (fastest V_b) | choice (fastest of options) | hold
    default: float = 0.0  # balance: start, and its value when the yaw balance is off; optimise: when not searched
    lo: float = -math.inf  # optimise: search bounds
    hi: float = math.inf
    options: tuple[tuple[float, float], ...] = ()  # choice: (value, lowest β_TW [deg] it may be used at)
    key: str = ""  # "<part>.<name>" (Boat.controls)

    def override(self, spec: Any) -> "Control":
        """A boat file's `controls: {<name>: <role> | {field: value}}` entry."""
        kw = {"role": spec} if isinstance(spec, str) else dict(spec or {})
        if "options" in kw:
            kw["options"] = tuple(tuple(float(v) for v in o) for o in kw["options"])
        c = replace(self, **{k: (v if k in ("role", "options") else float(v)) for k, v in kw.items()})
        if c.role not in ROLES:
            raise ValueError(f"control {self.name}: role {c.role} is not one of {ROLES}")
        return c


@dataclass(frozen=True)
class State:
    V: float  # V_b, boat speed through the water [m/s]
    heel: float = 0.0  # φ [deg], + to starboard
    leeway: float = 0.0  # β_Y [deg], + bow to port
    controls: Mapping[str, float] = field(default_factory=dict)  # by Control.key
    sink: float = 0.0  # sinkage [m], + down
    trim: float = 0.0  # trim [deg], + bow down
    hydro: Mapping[str, float] = field(default_factory=dict)  # the hydrostatics at this attitude (wetted_area, lwl)

    def but(self, **kw) -> "State":
        return replace(self, **kw)


@dataclass(frozen=True)
class Wind:
    tws: float  # V_TW at the reference height [m/s]
    twa: float  # β_TW from the course [deg]
    z_ref: float = 1.0  # height of tws [m]
    alpha: float = 0.0  # power-law profile exponent (0 = uniform)

    def tws_at(self, z: float) -> float:
        return frames.wind_at(self.tws, z, self.z_ref, self.alpha)

    def apparent(self, V: float, z: float | None = None) -> tuple[float, float]:
        """(V_AW, β_AW from the course) at height z (the reference height if None)."""
        return frames.apparent_wind(self.tws if z is None else self.tws_at(z), self.twa, V)


@dataclass
class Loads:
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0
    K: float = 0.0
    M: float = 0.0
    N: float = 0.0
    extrapolated: bool = False  # a table was read outside its range
    info: dict = field(default_factory=dict)  # model-specific outputs (z_ce, aws, ...)

    @staticmethod
    def at(point: tuple[float, float, float], X: float = 0.0, Y: float = 0.0, Z: float = 0.0, **kw) -> "Loads":
        """A force (course frame) acting at `point` (boat frame, already heeled)."""
        x, y, z = point
        return Loads(X, Y, Z, K=y * Z - z * Y, M=z * X + x * Z, N=-x * Y - y * X, **kw)

    def __add__(self, o: "Loads") -> "Loads":
        return Loads(self.X + o.X, self.Y + o.Y, self.Z + o.Z, self.K + o.K, self.M + o.M, self.N + o.N,
                     self.extrapolated or o.extrapolated, {**self.info, **o.info})

    def scaled(self, f: float) -> "Loads":
        return Loads(f * self.X, f * self.Y, f * self.Z, f * self.K, f * self.M, f * self.N, self.extrapolated,
                     dict(self.info))

    def finite(self) -> bool:
        return all(math.isfinite(v) for v in (self.X, self.Y, self.Z, self.K, self.M, self.N))


class Component(Protocol):
    name: str
    kind: str  # "hydro" or "aero"
    attitude: bool  # its loads depend on sinkage and trim (the hull)
    controls: tuple[Control, ...]

    def loads(self, s: State, w: Wind) -> Loads: ...


class Shape(Protocol):
    """Geometry: `build(ctx, name, mount=None, **args)`; optional hooks
    mass_items(), volumes() (buoyant (volume, centroid), upright boat frame),
    params(), info(), and what other parts query: a hull's surface() and
    depth_at(x), an appendage's planform()."""

    controls: tuple[Control, ...]


class ForceModel(Protocol):
    """Loads: `build(ctx, name, shape, **args)`; optional hooks finish(ctx)
    (once the hydrostatics exist), perturbations() (its exchange rates) and
    info(). `covers`: other parts' physics already in these loads, e.g.
    "hull.side_force"."""

    name: str
    kind: str
    attitude: bool
    controls: tuple[Control, ...]
    covers: frozenset[str]

    def loads(self, s: State, w: Wind) -> Loads: ...


@dataclass
class Part:
    """A part as the solver sees it: a shape and its force model. `owner`
    False: the shape is another part's (windage on the hull's topsides), so
    its mass and volume are counted there."""

    name: str
    shape: Any
    forces: Any
    controls: tuple[Control, ...] = ()
    owner: bool = True

    @property
    def kind(self) -> str:
        return self.forces.kind

    @property
    def attitude(self) -> bool:
        return self.forces.attitude

    @property
    def covers(self) -> frozenset[str]:
        return getattr(self.forces, "covers", frozenset())

    def loads(self, s: State, w: Wind) -> Loads:
        return self.forces.loads(s, w)

    def mass_items(self) -> list:
        return getattr(self.shape, "mass_items", list)() if self.owner else []

    def volumes(self) -> list:
        return getattr(self.shape, "volumes", list)() if self.owner else []

    def downwash(self) -> float:
        return self.forces.downwash()

    def perturbations(self) -> list["Perturbation"]:
        return getattr(self.forces, "perturbations", list)()

    def info(self) -> dict:
        out = dict(getattr(self.shape, "info", dict)()) if self.owner else {}
        return out | getattr(self.forces, "info", dict)()

    def with_forces(self, forces: Any) -> "Part":
        return replace(self, forces=forces)


class Wrapper:
    """Another component with some of its behaviour changed: every attribute
    the wrapper doesn't set is the base's (name, controls, hooks)."""

    def __init__(self, base: Any):
        self.base = base

    def __getattr__(self, k: str) -> Any:
        if k == "base":
            raise AttributeError(k)
        return getattr(self.base, k)


class Scaled(Wrapper):
    """A component whose loads are multiplied by `factor`."""

    def __init__(self, base: Any, factor: float):
        super().__init__(base)
        self.factor = factor

    def loads(self, s: State, w: Wind) -> Loads:
        return self.base.loads(s, w).scaled(self.factor)


@dataclass
class Perturbation:
    name: str  # what changes, e.g. "fixed drag +0.01 N"
    apply: Callable  # Boat -> Boat
    note: str = ""
    dD: float | None = None  # a constant drag step [N]: the rates report the V dR/dV it implies


def with_part(boat: Any, name: str, fn: Callable) -> Any:
    """A copy of the boat with part `name` replaced by fn(part)."""
    b = copy.copy(boat)
    b.components = [fn(c) if c.name == name else c for c in boat.components]
    return b


def scale_component(name: str, f: float) -> Callable:
    return lambda b: with_part(b, name, lambda c: Scaled(c, f))
