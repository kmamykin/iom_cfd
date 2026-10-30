"""Windage CFD tables (vpp/windage.py) and the windage force model that reads
them (components/windage.py WindageTable): drag and lift in the VPP's frame."""

import math

import numpy as np
import pytest

from iomcfd import physics
from iomcfd.vpp import tables, windage
from iomcfd.vpp.components.base import State, Wind
from iomcfd.vpp.components.windage import WindageTable
from test_vpp_boat import needs_orc

HEELS, ANGLES = (0.0, 30.0), (0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0)
AWS = 4.0


def _coeffs(h, a):
    """A made-up hull: area, cd, cl (< 0 ahead of the beam), cz, centre."""
    r = math.radians(a)
    A = 0.015 + 0.075 * math.sin(r) + 0.001 * h / 30
    return A, 0.3 + 0.7 * math.sin(r) ** 2, -0.9 * math.sin(2 * r) * (1 + h / 60), 0.5 * math.sin(r), (0.45, 0.04)


def _windage_csv(path, drop=(), extra=()):
    """windage results as the project writes them (forces in its frame: x aft, y port, z up)."""
    import pandas as pd

    rho = physics.air(15.0).rho
    q = 0.5 * rho * AWS**2
    rows = []
    for h in HEELS:
        for a in ANGLES:
            if (h, a) in drop:
                continue
            A, cd, cl, cz, (x, z) = _coeffs(h, a)
            r = math.radians(a)
            D, L, Fz = q * A * cd, q * A * cl, q * A * cz
            dd, ld = np.array([math.cos(r), -math.sin(r), 0.0]), np.array([math.sin(r), math.cos(r), 0.0])
            F = D * dd + L * ld + np.array([0.0, 0.0, Fz])
            M = np.cross([x, -0.01 * h / 30, z], F)  # about the bow on the waterline
            rows.append({"case": f"awa{a:g}_heel{h:g}", "status": "not_converged" if (h, a) == (30.0, 120.0) else "ok",
                         "hull_stl": "", "heel": h, "awa": a, "aws": AWS, "temperature": 15.0, "mesh": "fine",
                         "rhoInf": rho, "nu": 1.5e-5, "dynamicPressure": q, "A_proj_m2": A, "z_centroid_m": z + 0.01,
                         "sink": -0.002 - 0.0001 * h, "trim": 0.004 * h, "cd": cd, "cl": cl,
                         "drag_N": D, "lift_N": L, "vertical_N": Fz, "Fx_N": F[0], "Fy_N": F[1],
                         "roll_moment_Nm": M[0], "pitch_moment_Nm": M[1], "yaw_moment_Nm": M[2]})
    rows += [dict(rows[0], **e) for e in extra]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


class _Ctx:
    def __init__(self, tmp_path):
        self.base, self.air, self.warnings = tmp_path, physics.air(15.0), []

    def resolve(self, ref):
        return self.base / ref

    def warn(self, msg):
        self.warnings.append(msg)


class _Hull:
    def __init__(self, sha="abc"):
        self.sha = sha

    def params(self):
        return {"hull_mesh_sha256": self.sha}


def test_windage_export_per_unit_q(tmp_path):
    t = tables.read(windage.export(str(_windage_csv(tmp_path / "results.csv")), None, tmp_path / "w.csv"))
    assert t.header["component"] == "windage" and t.header["dims"] == ["heel", "angle"] and len(t.rows) == 14
    assert t.header["attitude"]["30"] == pytest.approx({"sink": -0.005, "trim": 0.12})
    for r in t.rows:
        A, cd, cl, cz, (x, z) = _coeffs(r["heel"], r["angle"])
        assert (r["D"], r["L"], r["Z"]) == pytest.approx((A * cd, A * cl, A * cz))
        assert r["ext"] == float((r["heel"], r["angle"]) == (30.0, 120.0))


def test_windage_export_needs_one_full_grid(tmp_path):
    with pytest.raises(ValueError, match="full grid"):
        windage.export(str(_windage_csv(tmp_path / "a.csv", drop={(30.0, 60.0)})), None, tmp_path / "w.csv")
    two = _windage_csv(tmp_path / "b.csv", extra=[{"case": "x", "mesh": "xfine"}])
    with pytest.raises(ValueError, match="more than one case"):
        windage.export(str(two), None, tmp_path / "w.csv")
    assert len(tables.read(windage.export(str(two), {"mesh": "fine"}, tmp_path / "w.csv")).rows) == 14


def _table(tmp_path, sha="abc"):
    out = windage.export(str(_windage_csv(tmp_path / "results.csv")), None, tmp_path / "w.csv")
    t = tables.read(out)
    t.header["params"]["hull_mesh_sha256"] = sha
    return tables.write(out, t.header, t.rows, t.columns).name


def test_windage_table_loads_in_the_vpp_frame(tmp_path):
    ctx = _Ctx(tmp_path)
    w = WindageTable.build(ctx, "windage", _Hull(), table=_table(tmp_path))
    rho = physics.air(15.0).rho
    for h, a in ((0.0, 30.0), (30.0, 30.0), (30.0, 90.0), (30.0, 150.0)):
        # a stopped boat in a uniform wind: the apparent wind is the true wind, from port at a to the course
        ld = w.loads(State(0.0, h, 0.0), Wind(AWS, a))
        A, cd, cl, cz, (x, z) = _coeffs(h, a)
        r, q = math.radians(a), 0.5 * rho * AWS**2
        Fx, Fy = q * A * (cd * math.cos(r) + cl * math.sin(r)), q * A * (-cd * math.sin(r) + cl * math.cos(r))
        # X forward = −(the CFD's aft force), Y to windward = its force to port; K, M, N in the VPP's signs
        # (tables.Grid's spline is exact at its nodes to its iterative solver's tolerance, about 1e-6)
        assert (ld.X, ld.Y, ld.Z) == pytest.approx((-Fx, Fy, q * A * cz), rel=1e-5, abs=1e-9)
        M = np.cross([x, -0.01 * h / 30, z], [Fx, Fy, q * A * cz])
        assert (ld.K, ld.M, ld.N) == pytest.approx((M[0], -M[1], -M[2]), rel=1e-5, abs=1e-9)
        assert ld.extrapolated is False
    # upwind the made-up lift pulls forward: more than the drag's aft part
    assert w.loads(State(0.0, 30.0, 0.0), Wind(AWS, 30.0)).X > 0
    # leeway turns the wind relative to the hull, not the force's direction
    ld = w.loads(State(0.0, 30.0, 5.0), Wind(AWS, 95.0))
    A, cd, cl, _, _ = _coeffs(30.0, 90.0)
    q, r = 0.5 * rho * AWS**2, math.radians(95.0)
    assert ld.X == pytest.approx(-q * A * (cd * math.cos(r) + cl * math.sin(r)), rel=1e-5)
    # the not-converged node and beyond the table are flagged
    assert w.loads(State(0.0, 30.0, 0.0), Wind(AWS, 120.0)).extrapolated
    assert w.loads(State(0.0, 40.0, 0.0), Wind(AWS, 90.0)).extrapolated


def test_windage_table_checks_the_hull(tmp_path):
    with pytest.raises(ValueError, match="another hull"):
        WindageTable.build(_Ctx(tmp_path), "windage", _Hull("def"), table=_table(tmp_path, "abc"))
    ctx = _Ctx(tmp_path)
    WindageTable.build(ctx, "windage", object(), table=_table(tmp_path))  # a shape without params: a warning
    assert ctx.warnings and "no hull" in ctx.warnings[0]


@needs_orc
def test_a_boat_with_a_windage_table(tmp_path):
    from iomcfd import config
    from iomcfd.vpp.boat import BoatSpec, build

    table = tmp_path / _table(tmp_path)
    spec = BoatSpec.load(config.home() / "boats" / "canoe-placeholder.yaml",
                         {"wind.tws": [2.0], "components.windage.forces": {"class": ".windage.WindageTable",
                                                                           "args": {"table": str(table)}}})
    b = build(spec)
    w = b.boat.component("windage")
    assert isinstance(w.forces, WindageTable) and w.loads(State(1.0, 20.0, 2.0), Wind(3.0, 40.0)).finite()
    # the made-up table names no hull of this boat's and floats it differently
    assert any("no hull" in m for m in b.warnings) and any("floats differently" in m for m in b.warnings)
