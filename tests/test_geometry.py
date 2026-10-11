import math

import numpy as np
import pytest

from iomcfd.geometry import appendages as ap
from iomcfd.geometry import cmesh, foils, hulls, sails, stl
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


@pytest.mark.parametrize("code", ["0009", "4412"])
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
