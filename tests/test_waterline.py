"""A hull placed and split at the water plane (geometry/waterline.py), and its
use by keel3d (an STL hull, the fin's root) and windage."""

import math

import numpy as np
import pytest

from iomcfd.geometry import hulls, stl, waterline
from iomcfd.project import load_project
from iomcfd.vpp import hydrostatics


def canoe():
    return hulls.canoe(hulls.CanoeSpec(), "hull")


@pytest.mark.parametrize("heel, trim, sink", [(0.0, 0.0, 0.0), (30.0, 0.5, -0.004), (60.0, 2.0, -0.012)])
def test_split_parts_are_closed_double_bodies(heel, trim, sink):
    hull = canoe()
    water, air = waterline.split(hull, heel, trim, sink)
    for s in (water, air):
        assert s.is_closed() and s.volume() > 0
        assert abs(s.centroid()[2]) < 1e-9  # symmetric about the plane
    placed = hydrostatics.place(hull, heel, trim, sink, waterline.trim_axis(hull))
    sub = hydrostatics.submerged(placed)
    assert water.volume() == pytest.approx(2 * sub.volume, rel=1e-9)
    assert water.area() == pytest.approx(2 * sub.wetted_area, rel=1e-9)
    assert water.area() / 2 + air.area() / 2 == pytest.approx(hull.area(), rel=1e-9)
    assert water.volume() / 2 + air.volume() / 2 == pytest.approx(hull.volume(), rel=1e-9)


def test_faces_in_the_plane_are_dropped():
    # a box whose top face lies in the plane: its double body is the box and its mirror image
    s = stl.loft([np.array([[x, -0.1, -0.05], [x, 0.1, -0.05], [x, 0.1, 0.0], [x, -0.1, 0.0]]) for x in (0.0, 1.0)])
    water, air = waterline.split(s, 0.0)
    assert water.is_closed() and water.volume() == pytest.approx(2 * s.volume())
    assert len(air.triangles) == 0 or air.volume() == pytest.approx(0.0, abs=1e-12)


def test_hydrostatics_uses_the_moved_helpers():
    assert hydrostatics.above_water is waterline.above_water
    assert hydrostatics.placement is waterline.placement


def test_crossings_of_a_vertical_line():
    spec = hulls.CanoeSpec()
    z = waterline.crossings(canoe(), spec.draft_at * spec.length, 0.0)
    assert z[0] == pytest.approx(-spec.draft, rel=1e-3)
    assert z[-1] == pytest.approx(spec.freeboard)
    assert len(waterline.crossings(canoe(), 0.5, 1.0)) == 0  # beside the hull


# --- keel3d with an STL hull ---------------------------------------------------------


@pytest.fixture
def keel3d():
    return load_project("keel3d")


def box_hull(path, rise_to: float, ramp_end: float = 0.6):
    """A box hull 1 m long, 160 mm wide, 60 mm of freeboard, bottom at -60 mm
    up to x = 0.52 m, then rising straight to `rise_to` at `ramp_end` and on
    at that depth: rocker under the fin's root (quarter chord at 0.5 m)."""
    xs = np.unique(np.r_[np.linspace(0.0, 0.5, 11), np.linspace(0.52, ramp_end, 9), np.linspace(0.65, 1.0, 8)])
    zb = np.interp(xs, [0.0, 0.52, ramp_end, 1.0], [-0.06, -0.06, rise_to, rise_to])
    rings = [np.array([[x, -0.08, z], [x, 0.08, z], [x, 0.08, 0.06], [x, -0.08, 0.06]]) for x, z in zip(xs, zb)]
    s = stl.loft(rings, name="hull").scaled(1000.0)  # mm, as the private hulls are
    s.write(path)


def test_new_parameters_out_of_old_hashes(keel3d):
    from iomcfd.study import params_hash

    p = dict(keel3d.defaults)
    old = {k: v for k, v in p.items() if k not in ("hull_stl", "sink", "trim", "hull_refine", "hull_yplus")}
    assert params_hash(p) == params_hash(old) != params_hash({**p, "hull_stl": "file:x.stl"})


def test_hull_yplus_layers(keel3d, tmp_path):
    p = {**keel3d.defaults, "speed": 1.5, "hull_refine": 1}
    plain = keel3d.prepare_case(tmp_path / "plain", p)
    assert "hullLayers" not in plain and not (tmp_path / "plain" / "system" / "include" / "hullLayers").exists()
    d = keel3d.prepare_case(tmp_path / "yplus", {**p, "hull_yplus": 1.0})
    # the first layer: y+ 1 at its centre with ITTC-57's friction at Re on the hull's length
    V, L, nu = 1.5, keel3d.defaults["hull_length"], d["nu"]
    u_tau = V * math.sqrt(0.075 / (math.log10(V * L / nu) - 2) ** 2 / 2)
    assert d["hullFirstLayer"] == pytest.approx(2 * nu / u_tau)
    # 14 layers to 0.3 of the hull's coarser surface cell: the expansion that needs
    final = 0.3 * d["baseCell"] / 2 ** d["hullLevelMin"]
    assert d["hullLayers"] == 14 and d["hullExpansion"] == pytest.approx((final / d["hullFirstLayer"]) ** (1 / 13))
    inc = tmp_path / "yplus" / "system" / "include"
    text = (inc / "hullLayers").read_text()
    assert "boat_hull" in text and "firstAndRelativeFinal" in text and "$hullFirstLayer" in text
    assert "nOuterIter 3;" in (inc / "layerPasses").read_text()
    shm = (tmp_path / "yplus" / "system" / "snappyHexMeshDict").read_text()
    assert '#sinclude "include/hullLayers"' in shm and '#sinclude "include/layerPasses"' in shm
    assert not (tmp_path / "plain" / "system" / "include" / "layerPasses").exists()
    # every other entry as without it
    assert {k: v for k, v in d.items() if k not in ("hullLayers", "hullFirstLayer", "hullExpansion")} == plain
    with pytest.raises(ValueError, match="expansion"):
        keel3d.derive({**p, "hull_yplus": 300.0})


def test_fin_root_runs_up_into_a_rockered_hull(keel3d, tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_GEOMETRY", str(tmp_path))
    box_hull(tmp_path / "rocker.stl", -0.02)
    geometry = type(keel3d).surfaces.__globals__["geometry"]
    p = {**keel3d.defaults, "hull_stl": "file:rocker.stl", "fin_x": 0.5}
    g = geometry(p)
    assert g["fin_z_root"] == pytest.approx(-0.06)
    # the bottom under the root's trailing edge (x 0.575) is 37.5 mm higher than at the quarter chord: more than
    # half the depth, so the extension is that rise plus the margin
    rise = 0.04 * (0.575 - 0.52) / 0.08
    assert g["fin_root_extension"] == pytest.approx(rise + 0.25 * 0.06, abs=2e-4)
    # every point of the fin's top section is inside the hull
    fin = next(s for s in keel3d.surfaces(p) if s.name == "fin")
    hull = type(keel3d).surfaces.__globals__["hull_surface"](p)
    top = fin.vertices[np.isclose(fin.vertices[:, 2], fin.vertices[:, 2].max())]
    assert len(top) > 20
    for x, y, z in top:
        assert int(np.sum(waterline.crossings(hull, x, y) < z)) % 2 == 1


def test_fin_root_that_would_leave_the_hull_raises(keel3d, tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_GEOMETRY", str(tmp_path))
    box_hull(tmp_path / "steep.stl", -0.005, ramp_end=0.56)  # 5 mm deep under the root's trailing edge
    geometry = type(keel3d).surfaces.__globals__["geometry"]
    with pytest.raises(ValueError, match="waterline|not inside|outside"):
        geometry({**keel3d.defaults, "hull_stl": "file:steep.stl", "fin_x": 0.5})


def test_stl_hull_case(keel3d, tmp_path, monkeypatch):
    monkeypatch.setenv("IOMCFD_GEOMETRY", str(tmp_path))
    box_hull(tmp_path / "rocker.stl", -0.03)
    p = {**keel3d.defaults, "hull_stl": "file:rocker.stl", "fin_x": 0.5, "heel": 30.0, "sink": -0.005, "trim": 0.5,
         "leeway": 4.0, "hull_refine": 1}
    d = keel3d.prepare_case(tmp_path / "case", p)
    R, t = waterline.placement(30.0, 0.5, -0.005, 0.5)
    assert d["cofR"] == pytest.approx(list(t))
    assert d["spanDir"] == pytest.approx(list(R @ np.array([0.0, 0.0, -1.0])))
    assert d["featureIntersection"] == "self" and d["zMax"] == 0.0
    base = load_project("keel3d").prepare_case(tmp_path / "base", {**p, "hull_refine": None})
    assert (d["hullLevelMin"], d["hullLevelMax"], d["hullBoxLevel"]) == (
        base["hullLevelMin"] + 1, base["hullLevelMax"] + 1, base["hullBoxLevel"] + 1)
    text = (tmp_path / "case" / "constant" / "triSurface" / "boat.stl").read_text()
    assert [ln.split()[1] for ln in text.splitlines() if ln.startswith("solid")] == ["hull", "fin", "bulb"]
    hull = stl.read(tmp_path / "case" / "constant" / "triSurface" / "boat.stl")  # all solids merged
    assert hull.bounds[0][2] < -0.3  # the bulb
    # the hull solid alone: closed, mirrored about the plane
    surfs = keel3d.surfaces(p)
    assert surfs[0].is_closed() and abs(surfs[0].centroid()[2]) < 1e-9
    assert f"CofR            ({t[0]:.9g} {t[1]:.9g} {t[2]:.9g});" in (
        tmp_path / "case" / "system" / "include" / "forceFunctions").read_text()


# --- windage -------------------------------------------------------------------------


def test_windage_area_is_the_vpp_projected_area():
    pr = load_project("windage")
    p = {**pr.defaults, "heel": 30.0, "sink": -0.005, "trim": 0.3, "awa": 40.0}
    d = pr.derive(p)
    hull = canoe()
    placed = hydrostatics.place(hull, 30.0, 0.3, -0.005, waterline.trim_axis(hull))
    T = hydrostatics.above_water(placed.vertices[placed.triangles])
    r = math.radians(40.0)
    A, c = hydrostatics.projected_area(T, (-math.cos(r), math.sin(r), 0.0))  # as vpp ProjectedArea
    assert d["Aref"] == pytest.approx(A, rel=1e-12)
    assert d["centroid"] == pytest.approx(list(c))


def test_windage_case_floor_and_domain(tmp_path):
    pr = load_project("windage")
    for awa in (0.0, 90.0, 150.0):
        p = {**pr.defaults, "heel": 20.0, "awa": awa}
        d = pr.prepare_case(tmp_path / f"a{awa:g}", p)
        s = stl.read(tmp_path / f"a{awa:g}" / "constant" / "triSurface" / "hull.stl")
        assert s.is_closed() and d["zMin"] == 0.0
        lo, hi = np.array(d["topsidesMin"]), np.array(d["topsidesMax"])
        L = d["lRef"]
        w = np.array(d["dragDir"])
        # at least 1.9 L upwind and 3.9 L downwind of the topsides' middle, inside the domain
        mid = 0.5 * (lo + hi)
        for k in (-1.9, 3.9):
            q = mid + k * L * w
            assert d["xMin"] <= q[0] <= d["xMax"] and d["yMin"] <= q[1] <= d["yMax"]
