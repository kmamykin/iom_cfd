"""VPP tables from the hull CFD: windage (vpp/windage.py export, read by
components/windage.py WindageTable: drag and lift in the VPP's frame) and the
hull's form factor (vpp/keel3d.py recipe hull-form-factor, read by
components/hull.py IttcMichell's form_factor_table)."""

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


# --- the hull's form factor from keel3d (vpp/keel3d.py recipe hull-form-factor) --------------------------------


def _ittc(V, L=0.95, nu=1.137e-6):
    return 0.075 / (math.log10(V * L / nu) - 2) ** 2


def _hull_rows(path, rows):
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _k3d(heel, V, D_hull, case, **kw):
    return {"case": case, "status": "ok", "heel": heel, "leeway": 0.0, "speed": V, "trim": 0.1 * heel / 30,
            "hull_stl": "", "hull_refine": 1, "mesh": "medium", "rhoInf": 999.1, "nu": 1.137e-6, "hull_lwl": 0.95,
            "hull_wetted_area_m2": 0.144, "drag_hull_N": D_hull, "yplus_hull_mean": 20.0, **kw}


def _q_s_cf(V):
    return 0.5 * 999.1 * V**2 * 0.144 * _ittc(V)


def test_hull_form_factor_table(tmp_path):
    from iomcfd.vpp import keel3d

    kwf = {(0.0, 0.5): 0.02, (0.0, 1.5): 0.03, (0.0, 3.6): 0.04, (30.0, 0.5): 0.05, (30.0, 1.5): 0.06, (30.0, 3.6): 0.07}
    src = _hull_rows(tmp_path / "src.csv", [_k3d(h, V, (1 + k) * _q_s_cf(V), f"h{h:g}_V{V:g}") for (h, V), k in kwf.items()]
                     + [_k3d(0.0, 1.5, 9.9, "lw4", leeway=4.0)])
    # resolved: 0.90 of the wall functions' drag at 1.5 m/s, 0.98 at 0.5 m/s (heel 30 only there)
    res = _hull_rows(tmp_path / "res.csv", [
        _k3d(0.0, 1.5, 0.90 * (1 + kwf[(0.0, 1.5)]) * _q_s_cf(1.5), "r0", hull_yplus=1.0, yplus_hull_mean=2.4),
        _k3d(30.0, 1.5, 0.90 * (1 + kwf[(30.0, 1.5)]) * _q_s_cf(1.5), "r1", hull_yplus=1.0, yplus_hull_mean=3.9),
        _k3d(30.0, 0.5, 0.98 * (1 + kwf[(30.0, 0.5)]) * _q_s_cf(0.5), "r2", hull_yplus=1.0, yplus_hull_mean=1.6),
        {**_k3d(0.0, 0.5, 1.0, "r3", hull_yplus=1.0), "status": "failed"}])
    recipe = tmp_path / "k.yaml"
    recipe.write_text(f"recipe: hull-form-factor\nsource: {src}\nselect: {{mesh: medium}}\nresolved: [{res}]\nout: k.csv\n")
    t = tables.read(keel3d.build_table(recipe))
    assert t.header["component"] == "hull" and t.header["model"] == "form-factor" and len(t.rows) == 6
    assert t.header["correction"]["V"] == [0.5, 1.5]
    assert t.header["correction"]["ratio"] == pytest.approx([0.98, 0.90])
    for r in t.rows:
        c = {0.5: 0.98, 1.5: 0.90, 3.6: 0.90}[r["V"]]  # held beyond 1.5 m/s
        assert r["k_wf"] == pytest.approx(kwf[(r["heel"], r["V"])], abs=1e-9)
        assert r["k"] == pytest.approx(c * (1 + r["k_wf"]) - 1, abs=1e-9)
        assert r["held"] == float(r["V"] == 3.6)


def test_hull_reads_its_form_factor_table(tmp_path):
    from iomcfd.geometry.hulls import CanoeSpec
    from iomcfd.vpp import hullres
    from iomcfd.vpp.components.hull import CanoeHull, IttcMichell

    rows = [{"heel": h, "V": V, "k": -0.05 + 0.001 * h + 0.01 * V} for h in (0.0, 30.0, 60.0) for V in (0.5, 1.5, 3.6)]
    tables.write(tmp_path / "k.csv", {"component": "hull", "model": "form-factor", "dims": ["heel", "V"],
                                      "params": {"hull_mesh_sha256": "abc"}}, rows)

    class Ctx(_Ctx):
        water = physics.fresh_water(15.0)

    shape = CanoeHull(CanoeSpec())
    hull = IttcMichell.build(Ctx(tmp_path), "hull", shape, form_factor_table="k.csv", waves="none", side_force=False)
    plain = IttcMichell.build(Ctx(tmp_path), "hull", shape, waves="none", side_force=False)
    s = State(1.5, 30.0, 0.0, hydro={"wetted_area": 0.14, "lwl": 0.9})
    k = -0.05 + 0.03 + 0.015
    Rf = hullres.friction_resistance(1.5, 0.14, 0.9, hull.nu, hull.rho, k, 1.0)
    ld = hull.loads(s, Wind(3.0, 45.0))
    assert ld.info["k"] == pytest.approx(k, abs=1e-6) and -ld.X == pytest.approx(Rf, rel=1e-6)
    assert plain.loads(s, Wind(3.0, 45.0)).info["k"] == 0.10  # without the table: form_factor
    assert hull.loads(State(4.0, 30.0, 0.0), Wind(3.0, 45.0)).extrapolated  # beyond the table: held, flagged
    with pytest.raises(ValueError, match="another hull"):
        class Other:
            def params(self):
                return {"hull_mesh_sha256": "def"}

            def displacement(self):
                return shape.displacement()
        IttcMichell.build(Ctx(tmp_path), "hull", Other(), form_factor_table="k.csv")
