"""Phase-2 tables: the hydrostatics' vertical-force layers, above-water
areas, heeled offsets, the mesh hull's keel line, grid-table keels, the
keel's vertical force and the cache."""

import math

import numpy as np
import pytest

from iomcfd.geometry import hulls
from iomcfd.physics import G, fresh_water
from iomcfd.vpp import cache, hullres, keel3d, tables
from iomcfd.vpp.components.base import State, Wind
from iomcfd.vpp.components.hull import CanoeHull, MeshHull
from iomcfd.vpp.components.keel import KeelGrid, PolarFit
from iomcfd.vpp.hydrostatics import HydroTable, Hydrostatics, above_water, projected_area
from test_vpp_boat import _keel3d_csv
from test_vpp_hydrostatics import box

RHO = fresh_water().rho


def test_vertical_force_layers_lift_the_box():
    L, B, T = 1.0, 0.2, 0.03
    hs = Hydrostatics(box(L, B, -0.05), mass=RHO * L * B * T, cg=(L / 2, 0.0, -0.01), rho=RHO)
    tab = hs.table(heels=[0.0, 10.0, 20.0, 30.0], M_ext=[-1.0, 0.0, 1.0], Z_ext=[-4.0, 0.0, 4.0])
    # Z_ext acts at the boat origin (the bow) and M_ext carries its moment, as the
    # parts' loads do (M = x Z): a lift of 2 N at mid-length is (Z, M) = (2, L/2·2).
    # A box's waterplane doesn't change with draft: Δsink = −Z / (ρ g A), no trim
    d = tab.at(0.0, 1.0, 2.0)
    assert d["sink"] - tab.at(0.0, 0.0, 0.0)["sink"] == pytest.approx(-2.0 / (RHO * G * L * B), rel=1e-3)
    assert d["trim"] == pytest.approx(0.0, abs=2e-3)
    # exact on the layers; the quadratic through them in between
    assert tab.at(10.0, 0.0, 4.0)["sink"] == pytest.approx(hs.float_at(10.0, 4.0, 0.0).sink, abs=1e-12)
    assert tab.at(10.0, 0.0, 5.0)["extrapolated"] and not tab.at(10.0, 0.0, 3.0)["extrapolated"]
    # one layer: the vertical force is ignored, as before
    one = hs.table(heels=[0.0, 10.0, 20.0, 30.0], M_ext=[-1.0, 0.0, 1.0])
    assert one.at(10.0, 0.5, 3.0) == one.at(10.0, 0.5, 0.0) | {"extrapolated": False}
    # the cache's rows read back as the same table
    back = HydroTable.from_rows(tab.rows())
    assert back.at(12.0, 0.3, -1.5) == tab.at(12.0, 0.3, -1.5)


def test_box_windage_is_its_silhouette():
    L, B, keel, deck = 1.0, 0.2, -0.05, 0.10
    s = box(L, B, keel, deck)
    T = above_water(s.vertices[s.triangles])
    a = math.radians(30.0)
    for d, area in (((0.0, 1.0, 0.0), L * deck), ((-1.0, 0.0, 0.0), B * deck),
                    ((-math.cos(a), math.sin(a), 0.0), L * deck * math.sin(a) + B * deck * math.cos(a))):
        A, c = projected_area(T, d)
        assert A == pytest.approx(area, rel=1e-12)
        assert c[2] == pytest.approx(deck / 2, rel=1e-12)


def test_heeled_offsets_are_half_widths():
    B = 0.2
    s = box(1.0, B, -0.05, 0.10)
    _, _, y = hullres.surface_offsets(s)
    assert y[40, -1] == pytest.approx(B / 2, abs=1e-12)
    # heeled 20°: both sides cross the waterline B / cos φ apart
    _, _, y = hullres.surface_offsets(s, heel=20.0)
    assert y[40, -1] == pytest.approx(B / 2 / math.cos(math.radians(20.0)), rel=1e-9)


def test_canoe_offsets_from_its_mesh():
    spec = hulls.CanoeSpec()
    x, z, y = hullres.surface_offsets(hulls.canoe(spec))
    xc, zc, yc = hullres.canoe_offsets(spec)
    # half-widths of the mesh against the analytic half-breadths at the waterline
    wl = np.interp(xc[10:-10], x, y[:, -1])
    assert np.max(np.abs(wl - yc[10:-10, -1])) < 2e-3


def test_mesh_hull_keel_line_and_side_force():
    spec = hulls.CanoeSpec()
    c, m = CanoeHull(spec), MeshHull(hulls.canoe(spec), {"canoe": {}})
    for x in (0.2, 0.5, 0.86):
        assert m.depth_at(x) == pytest.approx(c.depth_at(x), abs=3e-4)
    assert m.draft == pytest.approx(spec.draft, rel=1e-9)
    (S0, x0), (S1, x1) = c.jones(1.0, 2.0, RHO, 0.004), m.jones(1.0, 2.0, RHO, 0.004)
    assert S1 == pytest.approx(S0, rel=1e-9) and x1 == pytest.approx(x0, abs=1e-3)
    assert m.params() == c.params()


class _Fin:
    host = "hull"

    def planform(self):
        return {"area": 0.03, "aspect": 7.3}


def test_grid_keel_reproduces_its_table(tmp_path):
    rows = []
    for h in (0.0, 10.0, 20.0, 30.0):
        for b in (-1.0, 0.0, 1.0, 2.0, 3.0):
            for V in (0.5, 1.0, 1.5, 2.0):
                Y = 1.3 * b * V**2 * (1 - h / 100)
                rows.append({"heel": h, "leeway": b, "V": V, "X": -(0.3 + 0.01 * b**2) * V**2, "Y": Y, "Z": 0.0,
                             "K": 0.2 * Y, "M": 0.0, "N": -0.47 * Y, "Zv": 0.1 * b * V**2, "Mv": 0.047 * b * V**2,
                             "ext": float(b > 2.5)})
    t = tables.read(tables.write(tmp_path / "g.csv", {"component": "keel", "model": "grid",
                                                       "dims": ["heel", "leeway", "V"], "fit": {"a": [1.3]}}, rows))
    g = KeelGrid.from_table(t, "keel", RHO, _Fin())
    for r in rows[::7]:
        ld = g.loads(State(r["V"], r["heel"], r["leeway"]), Wind(3.0, 45.0))
        assert (ld.X, ld.Y, ld.N) == pytest.approx((r["X"], r["Y"], r["N"]), abs=1e-12) and ld.Z == 0.0
    # between the nodes: cubic in leeway and heel, loads / V² in V: exact for these
    ld = g.loads(State(1.2, 15.0, 1.5), Wind(3.0, 45.0))
    assert ld.Y == pytest.approx(1.3 * 1.5 * 1.44 * 0.85, rel=1e-9)
    assert ld.X == pytest.approx(-(0.3 + 0.01 * 2.25) * 1.44, rel=1e-9) and not ld.extrapolated
    assert g.loads(State(2.5, 15.0, 1.5), Wind(3.0, 45.0)).extrapolated  # beyond V: held and flagged
    assert g.loads(State(1.0, 15.0, 3.0), Wind(3.0, 45.0)).extrapolated  # flagged where the table is
    v = KeelGrid.from_table(t, "keel", RHO, _Fin(), vertical=True)
    assert v.loads(State(1.0, 10.0, 2.0), Wind(3.0, 45.0)).Z == pytest.approx(0.2, abs=1e-12)


def _keel3d_grid_csv(path, drop=()):
    """keel3d results over heel × leeway × speed: loads ∝ V², the hull's drag
    D_HULL V² and a −2.7 V² N suction; x_clr meaningless at 0°, as in keel3d."""
    import pandas as pd

    rows = []
    for heel in (0.0, 20.0):
        a = 1.3 * (1 - heel / 100)
        for b in (-2.0, 0.0, 2.0, 4.0):
            for V in (0.5, 1.0, 1.5):
                if (heel, b, V) in drop:
                    continue
                q, S = V**2, (0.05 + a * b) * V**2
                rows.append({"case": f"heel{heel:g}_leeway{b:g}_speed{V:g}", "status": "ok", "heel": heel,
                             "leeway": b, "speed": V, "fin_mean_chord": 0.09, "nu": 1.137e-6, "rhoInf": 999.1,
                             "bulb_section": "naca0011", "side_N": S, "drag_N": (0.4 + 0.3) * q + 0.004 * S**2 / q,
                             "drag_hull_N": 0.4 * q, "vertical_N": (-2.7 + 0.1 * b) * q,
                             "x_clr": 0.47 if b else 0.9, "z_clr": -0.25 if b else 3.0,
                             "roll_moment_Nm": 0.25 * S, "yaw_moment_Nm": 0.47 * S})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_keel3d_grid_export(tmp_path):
    csv = _keel3d_grid_csv(tmp_path / "results.csv")
    t = tables.read(keel3d.export(str(csv), {"bulb_section": "naca0011"}, tmp_path / "keel.csv", model="grid"))
    assert t.header["model"] == "grid" and t.header["moments"] == "bow" and len(t.rows) == 24
    assert t.header["fit"]["V_ref"] == 1.0 and t.header["fit"]["a"] == pytest.approx([1.3, 1.3 * 0.8])
    g = KeelGrid.from_table(t, "keel", RHO, _Fin(), vertical=True)
    for r in t.rows:
        q, S = r["V"] ** 2, (0.05 + 1.3 * (1 - r["heel"] / 100) * r["leeway"]) * r["V"] ** 2
        assert r["X"] == pytest.approx(-(0.3 * q + 0.004 * S**2 / q))  # the hull's 0° drag left to the hull
        assert r["Y"] == pytest.approx(S) and r["Z"] == 0.0
        assert r["K"] == pytest.approx(0.25 * S) and r["N"] == pytest.approx(-0.47 * S)  # keel3d's moments, VPP signs
        assert r["Zv"] == pytest.approx(0.1 * r["leeway"] * q)  # the suction is gone
        assert r["Mv"] == pytest.approx(0.47 * r["Zv"])  # at the lifting cases' x_clr at 0° too
        ld = g.loads(State(r["V"], r["heel"], r["leeway"]), Wind(3.0, 45.0))
        assert (ld.X, ld.Y, ld.Z, ld.N) == pytest.approx((r["X"], r["Y"], r["Zv"], r["N"]), abs=1e-12)
        assert not ld.extrapolated


def test_keel3d_grid_export_needs_every_case(tmp_path):
    csv = _keel3d_grid_csv(tmp_path / "results.csv", drop={(20.0, 4.0, 1.0)})
    with pytest.raises(ValueError, match="no case at"):
        keel3d.export(str(csv), None, tmp_path / "k.csv", model="grid")
    t = tables.read(keel3d.export(str(csv), None, tmp_path / "k.csv", model="grid", fill=True))
    r = next(r for r in t.rows if (r["heel"], r["leeway"], r["V"]) == (20.0, 4.0, 1.0))
    assert r["ext"] == 1.0 and r["Y"] == pytest.approx(0.05 + 1.04 * 4)  # linear along the leeway: exact here



def test_keel3d_grid_export_one_case_per_node(tmp_path):
    import pandas as pd

    df = pd.read_csv(_keel3d_grid_csv(tmp_path / "results.csv"))
    pd.concat([df, df.assign(case=df["case"] + "_fine")]).to_csv(tmp_path / "two.csv", index=False)
    with pytest.raises(ValueError, match="more than one case"):  # e.g. a mesh check: --select mesh=medium
        keel3d.export(str(tmp_path / "two.csv"), None, tmp_path / "k.csv", model="grid")


def test_keel_vertical_force_less_the_suction(tmp_path):
    csv = _keel3d_csv(tmp_path / "results.csv")  # vertical_N = −2.7 + 0.1 β
    t = tables.read(keel3d.export(str(csv), {"bulb_section": "naca0011"}, tmp_path / "keel.csv"))
    f = PolarFit.from_table(t)
    for b in (2.0, 4.0):  # exact on the CFD points at V_ref; the −2.7 N is gone
        assert f.loads(State(1.0, 0.0, b), Wind(3.0, 45.0)).Z == pytest.approx(0.1 * b, abs=1e-9)


def test_cache_reads_back_what_it_computed(tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_CACHE", str(tmp_path))
    calls = []

    def compute():
        calls.append(1)
        return {"component": "test"}, [{"a": 0.1 + 0.2, "b": 1e-300}], ["a", "b"]

    a = cache.cached("test", (1, np.arange(3)), compute)
    b = cache.cached("test", (1, np.arange(3)), compute)
    assert len(calls) == 1 and a.rows == b.rows and b.rows[0]["a"] == 0.1 + 0.2
    cache.cached("test", (2, np.arange(3)), compute)
    assert len(calls) == 2
    cache.ENABLED[0] = False
    try:
        cache.cached("test", (1, np.arange(3)), compute)
        assert len(calls) == 3
    finally:
        cache.ENABLED[0] = True
