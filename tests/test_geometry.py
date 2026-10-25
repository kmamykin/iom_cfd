import math

import numpy as np
import pytest

from iomcfd.geometry import appendages as ap
from iomcfd.geometry import cmesh, foils, hulls, sails, stepped, stl
from iomcfd.geometry.distributions import geometric, graded_section, vinokur


# --- foils -------------------------------------------------------------------


@pytest.mark.parametrize("code,t,xt", [("0009", 0.09, 0.30), ("0012", 0.12, 0.30), ("2412", 0.12, 0.30)])
def test_naca4_thickness(code, t, xt):
    f = foils.naca4(code)
    tt, xx = f.thickness()
    assert tt == pytest.approx(t, abs=2e-3)
    assert xx == pytest.approx(xt, abs=0.03)


def test_naca4_closed_te_and_normalised():
    f = foils.naca4("0009")
    assert f.x[0] == pytest.approx(1.0) and f.x[-1] == pytest.approx(1.0)
    assert f.y[0] == pytest.approx(f.y[-1], abs=1e-12)
    le = f.point(f.s_le)
    assert le == pytest.approx([0.0, 0.0], abs=1e-4)


def test_outward_normals():
    f = foils.naca4("0012")
    s_up = 0.5 * f.s_le  # mid upper surface
    s_lo = f.s_le + 0.5 * (f.perimeter - f.s_le)
    assert f.normal(s_up)[1] > 0.9
    assert f.normal(s_lo)[1] < -0.9


def test_dat_roundtrip(tmp_path):
    f = foils.naca4("2412")
    p = tmp_path / "x.dat"
    f.write_dat(p)
    g = foils.from_dat(p)
    assert g.thickness()[0] == pytest.approx(f.thickness()[0], abs=2e-3)
    assert foils.load("x.dat", [tmp_path]).name == g.name


def test_blunt_te_is_closed(tmp_path):
    # NACA 4-digit with the open-TE coefficient, written as a Selig file
    f = foils.naca4("0010", closed_te=False)
    p = tmp_path / "open.dat"
    f.write_dat(p)
    g = foils.from_dat(p)
    assert g.y[0] == pytest.approx(g.y[-1], abs=1e-9)


# --- distributions ---------------------------------------------------------------


def test_geometric_first_cell_and_length():
    x = geometric(50, 1e-4, 2.0)
    assert x[0] == 0 and x[-1] == pytest.approx(2.0)
    assert x[1] - x[0] == pytest.approx(1e-4, rel=1e-6)
    assert np.all(np.diff(x) > 0)


def test_vinokur_end_spacings():
    s = vinokur(100, 1e-3, 5e-3)
    assert s[1] - s[0] == pytest.approx(1e-3, rel=0.05)
    assert s[-1] - s[-2] == pytest.approx(5e-3, rel=0.05)


def test_graded_section_growth():
    n, ratio = graded_section(1.0, 0.005, 0.1)
    assert ratio == pytest.approx(20.0)
    assert (ratio ** (1 / (n - 1))) <= 1.2 + 1e-9


# --- C-mesh -----------------------------------------------------------------------


@pytest.mark.parametrize("code", ["0006", "0009", "4412"])
def test_cmesh_valid_and_orthogonal(code):
    spec = cmesh.CMeshSpec(chord=0.08, span=0.008, n_surface=96, n_wake=40, n_normal=64, first_cell=2e-5)
    P, nw = cmesh.generate(foils.naca4(code), spec)
    assert np.all(cmesh.cell_areas(P) > 0)
    q = cmesh.quality(P)
    assert q["max_nonortho"] < 40.0
    # wake cut points coincide
    NI = P.shape[0]
    assert np.allclose(P[NI - 1 - np.arange(nw + 1), 0], P[np.arange(nw + 1), 0])
    # first cell height on the wall
    assert np.min(np.hypot(*(P[nw:NI - nw, 1] - P[nw:NI - nw, 0]).T)) == pytest.approx(2e-5, rel=0.05)


def test_cmesh_smooth_section_unchanged():
    """Smooth sections are meshed exactly as before stepped sections were
    added (values from the generator at git f2b7bc0): earlier runs stay
    reproducible."""
    spec = cmesh.CMeshSpec(chord=0.08, span=0.008, n_surface=96, n_wake=40, n_normal=64, first_cell=2e-5)
    P, _ = cmesh.generate(foils.naca4("2412"), spec)
    assert P.shape == (273, 65, 2)
    assert float(P.sum()) == pytest.approx(1811.5638625461297, rel=1e-12)
    assert float((P**2).sum()) == pytest.approx(8802.157175833698, rel=1e-12)
    assert P[150, 10] == pytest.approx([0.0008969158266819711, 0.002206040721360161], rel=1e-9)
    assert P[200, 40] == pytest.approx([0.05353692132645316, 0.06157384079078007], rel=1e-9)


# --- stepped (Kline-Fogleman) sections ---------------------------------------------


def _half_thickness(f, x):
    up, lo = f.surface("upper", 2000), f.surface("lower", 2000)
    return 0.5 * (np.interp(x, up[:, 0], up[:, 1]) - np.interp(x, lo[:, 0], lo[:, 1]))


@pytest.mark.parametrize("spec,n", [("stair1:naca0009", 1), ("stair1:naca0009:x=0.35,d=0.5", 1),
                                    ("stair10:naca0009", 10), ("stair5:naca0009", 5)])
def test_stepped_presets(spec, n):
    f = foils.load(spec)
    base = foils.naca4("0009")
    up = sorted((s for s in f.steps if s.side == "upper"), key=lambda s: s.x)
    lo = sorted((s for s in f.steps if s.side == "lower"), key=lambda s: s.x)
    # symmetric: the same steps on both surfaces, and the contour is its own mirror image
    assert len(up) == len(lo) == n and [(s.x, s.height) for s in up] == [(s.x, s.height) for s in lo]
    assert np.allclose(f.x, f.x[::-1], atol=1e-12) and np.allclose(f.y, -f.y[::-1], atol=1e-12)
    for st in up:
        assert 0 < st.height < _half_thickness(base, st.x)
    assert f.thickness()[0] == pytest.approx(0.09, abs=1e-3)  # the steps are behind the maximum thickness


@pytest.mark.parametrize("spec,h,n,left", [("stair10", 0.00125, 10, 0.51), ("stair5", 0.0025, 5, 0.46)])
def test_stairs(spec, h, n, left):
    """stair10 = 10 x 0.1 mm, stair5 = 5 x 0.2 mm on an 80 mm chord: equal steps,
    evenly spaced from x/c 0.3 to 0.9, about half the thickness left near the TE."""
    f = foils.load(f"{spec}:naca0009")
    base = foils.naca4("0009")
    up = sorted((s for s in f.steps if s.side == "upper"), key=lambda s: s.x)
    assert [round(s.x, 6) for s in up] == pytest.approx(np.linspace(0.3, 0.9, n))
    assert all(s.height == pytest.approx(h, rel=1e-9) for s in up)
    assert _half_thickness(f, 0.95) / _half_thickness(base, 0.95) == pytest.approx(left, abs=0.01)
    with pytest.raises(ValueError):  # ten 0.2 mm steps would cut through the section
        foils.load("stair10:naca0009:h=0.0025")


def test_stepped_geometry_one_step():
    f = foils.load("stair1:naca0009:x=0.6,d=0.4")
    base = foils.naca4("0009")
    st = f.steps[0]
    assert st.x == 0.6 and st.depth == 0.4
    assert st.height == pytest.approx(0.4 * _half_thickness(base, 0.6), rel=1e-4)
    # behind the step the section is the base with 60 % of its thickness, sharp TE
    for x in (0.7, 0.85, 0.95):
        assert _half_thickness(f, x) == pytest.approx(0.6 * _half_thickness(base, x), rel=2e-3)
    assert f.point(np.array([0.0, f.perimeter])) == pytest.approx(np.array([[1.0, 0.0], [1.0, 0.0]]), abs=1e-9)
    # vertical face: between the two fillets the contour runs straight down at x = 0.6
    s = np.linspace(st.s_foot[1], st.s_lip[0], 50)
    assert np.allclose(f.point(s)[:, 0], 0.6, atol=1e-9)
    # the same step given by its height instead of its depth
    h = 0.4 * float(stepped._Surfaces(base).half_thickness(0.6))
    g = foils.load(f"stair1:naca0009:x=0.6,h={h!r}")
    assert np.allclose(g.x, f.x, atol=1e-12) and np.allclose(g.y, f.y, atol=1e-12)


def test_stepped_splines_do_not_overshoot():
    """One spline per smooth piece: no ringing at the corners (a single spline
    through a step overshoots by about the step height). From ahead of the
    lip to behind the foot the upper surface only ever goes down."""
    f = foils.load("stair1:naca0009")
    st = [s for s in f.steps if s.side == "upper"][0]
    s = np.linspace(st.s_foot[0] - 0.02, st.s_lip[1] + 0.02, 20000)  # parameter runs TE -> LE on the upper side
    assert np.all(np.diff(f.point(s)[:, 1]) >= -1e-12)


def test_stepped_spec_options():
    assert stepped.parse_spec("stair5:naca0009:x=0.4,x_end=0.6,h=0.002") == (
        "stair5", "naca0009", {"x": 0.4, "x_end": 0.6, "h": 0.002})
    assert stepped.parse_spec("stair1:file:sd8020.dat")[1] == "file:sd8020.dat"
    with pytest.raises(ValueError):
        stepped.parse_spec("stair1:naca0009:depth=0.3")
    with pytest.raises(ValueError):  # options belong to one preset: a stair has a height, not a depth
        stepped.parse_spec("stair10:naca0009:d=0.3")
    with pytest.raises(ValueError):  # one step has no x_end
        stepped.parse_spec("stair1:naca0009:x_end=0.8")
    with pytest.raises(ValueError):  # depth or height, not both
        stepped.parse_spec("stair1:naca0009:d=0.3,h=0.01")
    with pytest.raises(ValueError):  # the name fixes the number of steps
        stepped.parse_spec("stair10:naca0009:n=12")
    with pytest.raises(ValueError):
        foils.load("stair3:naca0009")
    for gone in ("kfm1", "kfm2", "kfm4", "kfm5", "kfm10", "kfm15"):  # renamed stair1/5/10; one-sided ones dropped
        with pytest.raises(ValueError, match="stair1"):
            foils.load(f"{gone}:naca0009")
    with pytest.raises(ValueError):
        foils.load("stair1:naca0009:d=0.95")  # nothing left behind the step


def test_film_geometry():
    """A film round the nose: the base offset by t ahead of its edge, the bare
    base behind it, and a step of height t at the edge (stepped.film)."""
    f = foils.load("film:naca0009:x=0.5,t=0.002")
    base = foils.naca4("0009")
    assert len(f.steps) == 2 and all(s.kind == "film" and s.height == 0.002 for s in f.steps)
    assert all(s.x == pytest.approx(0.5, abs=2e-4) for s in f.steps)
    assert np.allclose(f.x, f.x[::-1], atol=1e-12) and np.allclose(f.y, -f.y[::-1], atol=1e-12)
    for x in (0.55, 0.8, 0.95):
        assert _half_thickness(f, x) == pytest.approx(_half_thickness(base, x), abs=1e-7)
    # at the maximum thickness the surface is flat: offset along the normal = offset in y
    assert _half_thickness(f, 0.3) == pytest.approx(_half_thickness(base, 0.3) + 0.002, abs=1e-6)
    assert f.x.min() == pytest.approx(-0.002, abs=1e-7)  # the LE moves forward by t
    assert f.point(np.array([0.0, f.perimeter])) == pytest.approx(np.array([[1.0, 0.0], [1.0, 0.0]]), abs=1e-9)
    assert stepped.parse_spec("film:file:ht35-t070.dat:x=0.4,t=0.001") == (
        "film", "file:ht35-t070.dat", {"x": 0.4, "t": 0.001})
    with pytest.raises(ValueError):  # a film has a thickness, not a step depth
        stepped.parse_spec("film:naca0009:d=0.3")
    with pytest.raises(ValueError):
        foils.load("film:naca0009:x=0.98")  # the edge must leave room for the fillets


def test_faired_geometry():
    """A stair1 step faired out (stepped.faired): the base ahead of x, the
    step's thinner rear behind x + l, a smooth surface in between, and no
    steps, so it is meshed and run as a smooth section."""
    f = foils.load("faired:naca0007:x=0.5,h=0.002,l=0.1")
    trip, base = foils.load("stair1:naca0007:x=0.5,h=0.002"), foils.naca4("0007")
    assert not f.steps and not f.breaks and f.base is not None
    assert not stepped.is_stepped("faired:naca0007") and stepped.is_stepped("stair1:naca0007")
    assert np.allclose(f.x, f.x[::-1], atol=1e-12) and np.allclose(f.y, -f.y[::-1], atol=1e-12)
    for x in (0.1, 0.3, 0.49):
        assert _half_thickness(f, x) == pytest.approx(_half_thickness(base, x), abs=1e-7)
    for x in (0.61, 0.8, 0.95):
        assert _half_thickness(f, x) == pytest.approx(_half_thickness(trip, x), abs=1e-7)
    # through the fairing the surface only ever goes down: no step, no ripple
    up = f.surface("upper", 4000)
    assert np.all(np.diff(up[(up[:, 0] > 0.45) & (up[:, 0] < 0.65), 1]) <= 0)
    assert f.point(np.array([0.0, f.perimeter])) == pytest.approx(np.array([[1.0, 0.0], [1.0, 0.0]]), abs=1e-9)
    assert stepped.parse_spec("faired:naca0009:x=0.4,d=0.2,l=0.2") == ("faired", "naca0009",
                                                                       {"x": 0.4, "d": 0.2, "l": 0.2})
    with pytest.raises(ValueError):  # a fairing has a depth or a height, not a thickness
        stepped.parse_spec("faired:naca0009:t=0.002")
    with pytest.raises(ValueError):
        foils.load("faired:naca0009:x=0.9,l=0.2")  # the fairing must end by the TE
    spec = cmesh.CMeshSpec(chord=0.1, span=0.01, n_surface=96, n_wake=40, n_normal=64, first_cell=2e-5)
    P, _ = cmesh.generate(f, spec)
    assert np.all(cmesh.cell_areas(P) > 0) and cmesh.quality(P)["max_nonortho"] < 40.0


def test_stepped_dat_base():
    """A .dat base, whose LE is found numerically (x dips by ~1e-14 next to
    it), can be stepped and wrapped: HT35 at 7 %."""
    from iomcfd import config

    G = [config.geometry_dir() / "foils"]
    assert len(foils.load("stair1:file:ht35-t070.dat:x=0.5,h=0.002", G).steps) == 2
    f = foils.load("film:file:ht35-t070.dat", G)
    assert f.thickness()[0] == pytest.approx(0.074, abs=1e-5) and f.base.thickness()[0] == pytest.approx(0.07, abs=1e-5)


@pytest.mark.parametrize("spec", ["stair1:naca0009", "stair1:naca0009:x=0.35,d=0.5", "stair10:naca0009",
                                  "stair5:naca0009", "film:naca0009"])
def test_cmesh_stepped_valid(spec):
    f = foils.load(spec)
    h_min = min(s.height for s in f.steps) * 0.08
    mesh = cmesh.CMeshSpec(chord=0.08, span=0.008, n_surface=128, n_wake=48, n_normal=64,
                           first_cell=min(2e-5, h_min / 20), farfield=50, wake_length=50)
    P, nw = cmesh.generate(f, mesh)
    assert np.all(cmesh.cell_areas(P) > 0)
    assert cmesh.quality(P)["max_nonortho"] < 80.0
    # wall points cluster at each lip: spacing there ~ step_corner * h
    NI = P.shape[0]
    wall = P[nw:NI - nw, 0] / 0.08
    ds = np.hypot(*np.diff(wall, axis=0).T)
    for st in f.steps:
        lip = f.point(np.array(st.s_lip)).mean(axis=0)
        near = np.hypot(*(0.5 * (wall[1:] + wall[:-1]) - lip).T) < 0.2 * st.height
        assert near.any() and ds[near].min() <= max(3 * mesh.step_corner * st.height, 2.5e-4)
    # first wall cell still sized for y+ (the marched lines leave the wall normally)
    assert np.min(np.hypot(*(P[nw:NI - nw, 1] - P[nw:NI - nw, 0]).T)) == pytest.approx(mesh.first_cell, rel=0.05)


def test_polymesh_files(tmp_path):
    spec = cmesh.CMeshSpec(chord=1.0, span=0.1, n_surface=40, n_wake=20, n_normal=24, first_cell=1e-3)
    info = cmesh.build(foils.naca4("0012"), spec, tmp_path / "polyMesh")
    nci, ncj = 2 * 20 + 2 * 40, 24
    assert info.n_cells == nci * ncj
    owner = (tmp_path / "polyMesh" / "owner").read_text()
    neigh = (tmp_path / "polyMesh" / "neighbour").read_text()
    n_owner = int(owner.split("// * *")[-1].split("\n(")[0].strip().splitlines()[-1])
    assert n_owner == info.n_faces
    # upper-triangular ordering of internal faces: owner sorted, neighbour > owner
    own = [int(v) for v in owner.split("(\n")[1].split("\n)")[0].split()][: info.n_internal_faces]
    nei = [int(v) for v in neigh.split("(\n")[1].split("\n)")[0].split()]
    assert all(a < b for a, b in zip(own, nei))
    assert own == sorted(own)
    assert "frontAndBack" in (tmp_path / "polyMesh" / "boundary").read_text()


# --- 3D surfaces --------------------------------------------------------------------


def test_appendages_closed_and_bulb_mass():
    for s in (ap.fin(ap.FinSpec()), ap.bulb(ap.BulbSpec()), ap.rudder(ap.RudderSpec(angle=5))):
        assert s.is_closed()
        assert s.volume() > 0
    assert ap.bulb_mass(ap.BulbSpec()) == pytest.approx(2.4, abs=0.05)


def test_wigley_displacement():
    h = hulls.wigley(1.0, 0.18, 0.05, 0.06)
    assert h.is_closed()
    assert hulls.wigley_displacement(1.0, 0.18, 0.05) == pytest.approx(0.004)
    assert hulls.waterline_length(h) == pytest.approx(1.0, abs=0.01)


def test_iom_rig_areas():
    main, jib, mast = sails.iom_a_rig()
    assert main.area() == pytest.approx(0.36, abs=0.03)
    assert jib.area() == pytest.approx(0.25, abs=0.03)
    assert mast.is_closed()


@pytest.mark.parametrize("binary", [False, True])
def test_stl_roundtrip(tmp_path, binary):
    s = ap.bulb(ap.BulbSpec())
    p = tmp_path / "b.stl"
    s.write(p, binary=binary)
    r = stl.read(p)
    assert r.is_closed()
    assert r.volume() == pytest.approx(s.volume(), rel=1e-4)


def test_rotation_keeps_volume():
    s = ap.fin(ap.FinSpec())
    r = s.rotated("x", 20.0, about=(0, 0, -0.04)).rotated("z", -3.0)
    assert r.volume() == pytest.approx(s.volume(), rel=1e-9)
    assert stl.rotation("z", 90) @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-12)
    assert math.isclose(np.linalg.det(stl.rotation("y", 33)), 1.0)


def test_foil_bulb_volume_and_centre():
    vol = (2.5 - 0.12) / ap.LEAD_DENSITY  # IOM keel limit minus a 120 g fin, in lead
    length = ap.foil_bulb_length("naca0007", vol)
    assert length == pytest.approx(0.4634, abs=5e-4)
    k, xc, d = ap.foil_body_coefficients("naca0007")
    assert d == pytest.approx(0.07, abs=1e-4)  # diameter = section thickness
    b = ap.foil_bulb(ap.FoilBulbSpec(section="naca0007", length=length, x_cg=0.5, z_axis=-0.4))
    assert b.is_closed()
    assert b.volume() == pytest.approx(vol, rel=0.005)  # facets lose a little
    assert b.centroid() == pytest.approx([0.5, 0.0, -0.4], abs=1e-4)
    with pytest.raises(ValueError):
        ap.foil_bulb_length("naca2412", vol)


@pytest.mark.parametrize("taper", [1.0, 0.8, 0.6, 0.4])
def test_taper_keeps_mean_chord(taper):
    root, tip = ap.taper_chords(0.1, taper)
    assert 0.5 * (root + tip) == pytest.approx(0.1)
    assert tip / root == pytest.approx(taper)
    spec = ap.FinSpec(section="naca0007", root_chord=root, tip_chord=tip, span=0.33, z_root=-0.05,
                      tip_extension=0.016, n_span=40)
    s = ap.fin(spec)
    assert s.is_closed()
    assert s.bounds[0][2] == pytest.approx(-0.05 - 0.33 - 0.016)


def test_canoe_body():
    spec = hulls.CanoeSpec()
    h = hulls.canoe(spec)
    assert h.is_closed()
    vol, lcb, area = hulls.canoe_displacement(spec)
    assert vol == pytest.approx(3.62e-3, rel=0.01)
    assert lcb == pytest.approx(0.504, abs=0.005)
    assert area == pytest.approx(hulls.wetted_area_below(h), rel=0.02)
    assert float(hulls.canoe_depth(spec, spec.draft_at * spec.length)) == pytest.approx(spec.draft)
    assert float(hulls.canoe_half_breadth(spec, 0.0)) == 0.0
    lo, hi = h.bounds
    assert lo[2] == pytest.approx(-spec.draft, abs=1e-4) and hi[1] == pytest.approx(spec.beam / 2, abs=1e-4)


@pytest.mark.parametrize("aspect,top,bottom", [(1.0, 2.0, 2.0), (1.5, 2.0, 2.0), (2.0, 6.0, 2.0), (1.5, 2.0, 6.0)])
def test_bulb_sections_keep_the_lead(aspect, top, bottom):
    ring = ap.section_ring(aspect, top, bottom, 48)
    y, z = ring[:, 0], ring[:, 1]
    assert 0.5 * abs(y @ np.roll(z, -1) - z @ np.roll(y, -1)) == pytest.approx(math.pi, rel=0.005)  # circle's area
    assert ring[1:24][::-1] * (-1, 1) == pytest.approx(ring[25:], abs=0)  # exact mirror images in y
    b, h, zc = ap.section_shape(aspect, top, bottom)
    assert (y.max() - y.min(), z.max() - z.min()) == pytest.approx((2 * b, 2 * h), rel=1e-3)
    assert b / h == pytest.approx(aspect)
    vol = (2.5 - 0.12) / ap.LEAD_DENSITY
    spec = ap.FoilBulbSpec(section="naca0007", length=ap.foil_bulb_length("naca0007", vol), x_cg=0.5, z_axis=-0.4,
                           aspect=aspect, top=top, bottom=bottom)
    s = ap.foil_bulb(spec)
    assert s.is_closed()
    assert s.volume() == pytest.approx(vol, rel=0.006)
    zoff = ap.foil_bulb_cg_offset(spec)
    assert (zoff > 0) == (top > bottom) and (zoff < 0) == (top < bottom)  # a flat bottom puts the lead lower
    assert s.centroid() == pytest.approx([0.5, 0.0, -0.4 + zoff], abs=2e-4)


def test_bulb_cant_is_nose_up_about_the_centre_of_mass():
    spec = ap.FoilBulbSpec(section="naca0007", length=0.46, x_cg=0.5, z_axis=-0.4, aspect=1.5, bottom=6.0)
    up, canted = ap.foil_bulb(spec), ap.foil_bulb(ap.FoilBulbSpec(**{**spec.__dict__, "cant": 3.0}))
    assert canted.centroid() == pytest.approx(up.centroid(), abs=1e-5)  # about the exact one, not the facets
    nose = lambda s: s.vertices[np.argmin(s.vertices[:, 0])]
    tail = lambda s: s.vertices[np.argmax(s.vertices[:, 0])]
    assert nose(canted)[2] > nose(up)[2] and tail(canted)[2] < tail(up)[2]
    xt, zt, xb, zb = ap.foil_bulb_lines(ap.FoilBulbSpec(**{**spec.__dict__, "cant": 3.0}))
    assert zb.min() == pytest.approx(canted.vertices[:, 2].min(), abs=2e-4)  # the lowest point is on the bottom line
    assert zt.max() == pytest.approx(canted.vertices[:, 2].max(), abs=2e-4)
