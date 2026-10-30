"""Windage of the hull above the water (topsides and deck; the mast and
rigging are in the sail model): pure drag along the apparent wind, after ORC
2026 §5.4 (Table 5.12, eq. 5.27-5.30): C_D·A = C_D (A_front |cos β| +
A_side sin β) with C_D 0.816, at 0.66 (freeboard + B sin φ) above the
waterline. ORC's areas: freeboard × beam ahead, heeled freeboard × LOA abeam.

Three force models on the hull's shape (`shape: hull` in the boat file):

* `OrcWindage`: ORC's areas from the shape's dimensions() (beam, length
  and, unless given, freeboard).
* `ProjectedArea`: the area of the hull above the water, projected on the
  plane normal to the apparent wind, times C_D, at that area's centroid,
  with the wind taken at the centroid's height. Tabulated once the
  hydrostatics exist, over heel (each at its static sinkage and trim) and
  the wind's angle to the centreline (cached, vpp/cache.py). Exact for the
  faceted hull's silhouette when every line along the wind crosses the
  topsides at most twice (a cockpit or tumblehome counts hidden faces too).
* `WindageTable`: drag and lift (and the vertical force and the moments)
  from a windage CFD run of this hull (vpp/windage.py export), over heel and
  the wind's angle to the centreline, per unit dynamic pressure at the
  projected area's centroid height. A heeled hull's topsides make mostly a
  side force upwind, little drag (projects/windage/findings/alt-air-scout.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .. import cache, frames, tables
from ..hydrostatics import above_water, placement, projected_area
from .base import Loads, State, Wind


@dataclass
class OrcWindage:
    front_area: float  # m², freeboard × beam
    side_area: float  # m², freeboard × length
    freeboard: float = 0.06  # m, mean
    beam: float = 0.165  # m
    cd: float = 0.816  # ORC Table 5.12
    x: float = 0.5  # m aft of the bow
    rho: float = 1.225
    name: str = "windage"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()

    @classmethod
    def build(cls, ctx, name: str, shape, *, cd: float = 0.816, freeboard: float | None = None,
              x: float = 0.5) -> "OrcWindage":
        d = shape.dimensions()
        fb = float(d["freeboard"] if freeboard is None else freeboard)
        return cls(fb * d["beam"], fb * d["length"], freeboard=fb, beam=d["beam"], cd=float(cd), x=float(x),
                   rho=ctx.air.rho, name=name)

    def loads(self, s: State, w: Wind) -> Loads:
        p = math.radians(s.heel)
        z = 0.66 * (self.freeboard + self.beam * math.sin(abs(p)))
        aws, awa = w.apparent(s.V, z)
        a = math.radians(awa)  # from the course: the force points downwind
        side = self.side_area * (1 + self.beam * math.sin(abs(p)) / max(self.freeboard, 1e-6))  # heeled topsides
        D = 0.5 * self.rho * aws**2 * self.cd * (self.front_area * abs(math.cos(a)) + side * abs(math.sin(a)))
        return Loads.at(frames.heeled_point(self.x, 0.0, z, 0.0), X=-D * math.cos(a), Y=-D * math.sin(a),
                        info={"D": D})


@dataclass
class ProjectedArea:
    shape: object  # the hull's shape: its surface()
    cd: float = 0.816  # ORC Table 5.12
    rho: float = 1.225
    heels: tuple = tuple(np.arange(0.0, 60.1, 2.5))
    angles: tuple = tuple(np.arange(0.0, 180.1, 10.0))  # wind from the bow (0°) to the stern, port side [deg]
    name: str = "windage"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()
    _grid: object = field(default=None, repr=False)

    @classmethod
    def build(cls, ctx, name: str, shape, *, cd: float = 0.816) -> "ProjectedArea":
        if not hasattr(shape, "surface"):
            raise ValueError(f"{name}: the shape has no surface (use shape: hull)")
        return cls(shape, float(cd), ctx.air.rho, name=name)

    def finish(self, ctx) -> None:
        """The table over heel × wind angle at each heel's static attitude."""
        H, A = np.asarray(self.heels, float), np.asarray(self.angles, float)
        att = [ctx.table.at(float(h), 0.0) for h in H]
        x_trim = ctx.hydro.x_trim
        surf = self.shape.surface()
        v, tri = np.asarray(surf.vertices, float), np.asarray(surf.triangles)

        def compute():
            rows = []
            for h, a in zip(H, att):
                R, t = placement(float(h), a["trim"], a["sink"], x_trim)
                T = above_water((v @ R.T + t)[tri])
                Ry = R @ np.linalg.inv(placement(float(h), 0.0, 0.0, x_trim)[0])  # the trim part of R
                for ang in A:
                    r = math.radians(ang)
                    area, c = projected_area(T, (-math.cos(r), math.sin(r), 0.0))  # the side the wind comes from
                    p = Ry.T @ (c - t)  # the centroid in the heeled boat frame
                    rows.append({"heel": float(h), "angle": float(ang), "A": area, "x": float(p[0]),
                                 "y": float(p[1]), "z": float(p[2]), "height": float(c[2])})
            return ({"component": "windage", "dims": ["heel", "angle"], "note": "projected area above the "
                     "water [m²] and its centroid (heeled boat frame; height above the water) at each heel's "
                     "static attitude"}, rows, ["heel", "angle", "A", "x", "y", "z", "height"])

        t = cache.cached("windage", (surf, H, A, [(a["sink"], a["trim"]) for a in att], x_trim), compute)
        idx = {(r["heel"], r["angle"]): r for r in t.rows}
        vals = np.array([[[idx[(float(h), float(a))][k] for k in ("A", "x", "y", "z", "height")] for a in A]
                         for h in H])
        self._grid = tables.Grid([H, A], vals)

    def at(self, heel: float, angle: float) -> tuple[np.ndarray, bool]:
        """(A, x, y, z, height) at heel and wind angle to the centreline."""
        return self._grid(abs(heel), angle)

    def loads(self, s: State, w: Wind) -> Loads:
        h0 = float(self.at(s.heel, 90.0)[0][4])
        aws, awa = w.apparent(s.V, max(h0, 0.01))
        (A, x, y, z, h), out = self.at(s.heel, awa - s.leeway)
        aws, awa = w.apparent(s.V, max(float(h), 0.01))
        D = 0.5 * self.rho * aws**2 * self.cd * float(A)
        a = math.radians(awa)  # from the course: the force points downwind
        return Loads.at((float(x), float(y), float(z)), X=-D * math.cos(a), Y=-D * math.sin(a), extrapolated=out,
                        info={"D": D, "A": float(A)})


@dataclass
class WindageTable:
    """The topsides' loads from a windage CFD table (vpp/windage.py): D along
    and L across the apparent wind, the vertical force Z and the moments K, M,
    N about the bow, per unit q = ½ρV_AW², over |φ| × the wind's angle to the
    centreline (β_AW − β_Y), interpolated by cubic splines. The wind is taken
    at the projected area's centroid height, as ProjectedArea does; outside
    the table the inputs are held at its edge and the point is flagged, as are
    the table's not-converged nodes (nearest)."""

    coeffs: object  # tables.Grid: (|φ|, angle) -> (D, L, Z, K, M, N, height, A)
    flags: object  # nearest-node lookup of the table's ext column
    rho: float = 1.225
    provenance: str = ""
    name: str = "windage"
    kind: str = "aero"
    attitude: bool = False
    controls: tuple = ()
    covers: frozenset = frozenset()
    attitudes: dict = field(default_factory=dict)  # the table's {heel: {sink, trim}}

    COLS = ("D", "L", "Z", "K", "M", "N", "height", "A")

    @classmethod
    def build(cls, ctx, name: str, shape, *, table: str) -> "WindageTable":
        from scipy.interpolate import RegularGridInterpolator

        t = tables.read(ctx.resolve(table))
        if t.header.get("component") != "windage":
            raise ValueError(f"{name}: {table} is a {t.header.get('component')} table, not windage")
        tp, hp = t.header.get("params") or {}, getattr(shape, "params", dict)()
        diff = [k for k in tp if k in hp and tp[k] != hp[k]]
        if diff:
            raise ValueError(f"{name}: {table} was computed for another hull ({', '.join(diff)} differ)")
        if not any(k in hp for k in tp):
            ctx.warn(f"{name}: {table} names no hull this boat's can be checked against")
        dims = t.header["dims"]
        axes = [np.array(sorted({r[d] for r in t.rows})) for d in dims]
        shape_ = tuple(len(a) for a in axes)
        rows = sorted(t.rows, key=lambda r: tuple(r[d] for d in dims))
        vals = np.stack([np.array([r[q] for r in rows]).reshape(shape_) for q in cls.COLS], axis=-1)
        ext = np.array([r.get("ext", 0.0) for r in rows]).reshape(shape_)
        src = t.header.get("source") or {}
        return cls(tables.Grid(axes, vals), RegularGridInterpolator(axes, ext, method="nearest"), ctx.air.rho,
                   f"{table} ({src.get('run', '')} {src.get('select', '')})", name,
                   attitudes=t.header.get("attitude") or {})

    def finish(self, ctx) -> None:
        """Warn if this boat floats differently from the attitudes the table was run at."""
        moved = []
        for h, a in self.attitudes.items():
            now = ctx.table.at(float(h), 0.0)
            if abs(now["sink"] - a["sink"]) > 1e-3 or abs(now["trim"] - a["trim"]) > 0.1:
                moved.append(f"{h}° ({a['sink'] * 1e3:.1f} -> {now['sink'] * 1e3:.1f} mm, "
                             f"{a['trim']:.2f} -> {now['trim']:.2f}°)")
        if moved:
            ctx.warn(f"{self.name}: the boat floats differently from the windage table's attitudes at {', '.join(moved)}")

    def loads(self, s: State, w: Wind) -> Loads:
        h0 = float(self.coeffs(abs(s.heel), 90.0)[0][6])
        _, awa = w.apparent(s.V, max(h0, 0.01))
        c, out = self.coeffs(abs(s.heel), awa - s.leeway)
        aws, awa = w.apparent(s.V, max(float(c[6]), 0.01))
        c, out = self.coeffs(abs(s.heel), awa - s.leeway)
        q = 0.5 * self.rho * aws**2
        D, L = q * float(c[0]), q * float(c[1])
        a = math.radians(awa)  # from the course: D points downwind, L < 0 forward and to leeward (ahead of the beam)
        flag = bool(self.flags(np.clip([abs(s.heel), awa - s.leeway], self.coeffs.lo, self.coeffs.hi))[0])
        return Loads(-D * math.cos(a) - L * math.sin(a), -D * math.sin(a) + L * math.cos(a), q * float(c[2]),
                     q * float(c[3]), q * float(c[4]), q * float(c[5]), extrapolated=out or flag,
                     info={"D": D, "L": L, "A": float(c[7])})
