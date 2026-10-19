"""bulb2d: body profiles, the axisymmetric wedge mesh, sizing from the lead mass."""

import math

import numpy as np
import pytest

from iomcfd import config
from iomcfd.geometry import appendages as ap
from iomcfd.geometry import axisym, cmesh
from iomcfd.project import load_project

DRESS = config.geometry_dir() / "bodies" / "dress-laminar-body.csv"


def _spec(L=0.3, **kw):
    return cmesh.CMeshSpec(**{**dict(chord=L, span=0.03, n_surface=64, ds_le=2e-3, ds_te=4e-3, n_wake=24,
                                     wake_length=10.0, n_normal=32, first_cell=2e-5, farfield=10.0), **kw})


def test_profiles_match_the_3d_bulbs():
    # keel3d's NACA bulb: same volume and centre of volume as appendages.foil_body_coefficients
    vol, xc, d = ap.foil_body_coefficients("naca0007")
    prof = axisym.naca_profile(0.07)
    assert prof.volume() == pytest.approx(vol, rel=2e-3)
    assert prof.centroid() == pytest.approx(xc, abs=2e-3)
    assert 2 * prof.max_radius()[0] == pytest.approx(d, rel=2e-3)
    # appendage3d's bulb: the same profile as BulbSpec (L = 1, D = 1 / 8.8)
    b = axisym.bulb_profile(8.8, max_at=0.4, tail_exp=2.0)
    x3, r3 = ap.bulb_profile(ap.BulbSpec(length=1.0, diameter=1 / 8.8, n_axial=2001))
    assert np.interp(x3, b.x, b.r) == pytest.approx(r3, abs=2e-4)
    assert b.max_radius()[1] == pytest.approx(0.4, abs=2e-3)


def test_dress_body():
    prof = axisym.file_profile(DRESS)
    assert prof.x[0] == 0 and prof.x[-1] == 1
    assert 0.5 / prof.max_radius()[0] == pytest.approx(4.5, abs=1e-3)  # 12 in x 2.6666 in
    assert prof.base / prof.max_radius()[0] == pytest.approx(0.3, abs=1e-3)  # Dress's Table I: t = 0.3
    assert prof.volume() * 12**3 == pytest.approx(35.87, rel=2e-3)  # in^3, trapezoid of the table


@pytest.mark.parametrize("prof", [axisym.naca_profile(0.07), axisym.bulb_profile(5.0), axisym.file_profile(DRESS)],
                         ids=["naca", "bulb", "dress"])
def test_wedge_mesh(prof, tmp_path):
    g = axisym.generate(prof, _spec(), n_base=8)
    assert np.all(axisym.cell_areas(g) > 0)
    assert np.all(g.points[:, 1] >= 0)
    info = axisym.write_wedge(g, 5.0, tmp_path / "polyMesh")
    assert info.n_cells == len(g.cells)
    text = (tmp_path / "polyMesh" / "boundary").read_text()
    for name in ("body", "farfield", "outlet", "front", "back"):
        assert f"    {name}\n" in text
    assert ("    base\n" in text) == (prof.base > 0)
    # the body patch: one face per wall interval, its points on the profile
    pts = g.points[[i for e, n in g.boundary.items() if n == "body" for i in e]]
    L = 0.3
    assert pts[:, 1] == pytest.approx(np.interp(pts[:, 0] / L, *prof.dense()) * L, abs=2e-4 * L)
    faces = (tmp_path / "polyMesh" / "faces").read_text()
    assert "3(" in faces  # triangles where a side face meets the axis


def test_sizing_from_the_lead(tmp_path):
    p = load_project("bulb2d")
    d = p.derive({**p.defaults, "fineness": 14.29})
    assert d["lead_kg"] == pytest.approx(2.38)
    assert d["length_m"] == pytest.approx(0.4635, abs=5e-4)  # keel3d's default bulb (NACA 0007)
    d11 = p.derive(dict(p.defaults))
    assert (d11["length_m"], d11["diameter_m"]) == pytest.approx((0.3429, 0.0377), abs=2e-4)  # the bulb studies' NACA 0011
    assert d["Aref"] == pytest.approx(d["wetted_area_m2"] * 5 / 360)
    dr = p.derive({**p.defaults, "body": "file:dress-laminar-body.csv", "mass": 0, "length": 0.3048, "Re": 4.376e5})
    assert dr["Re_L"] == pytest.approx(4.376e5)
    assert dr["base_diameter_m"] == pytest.approx(0.8 * 0.0254, rel=1e-3)
    with pytest.raises(ValueError):
        p.derive({**p.defaults, "body": "sphere"})
    p.prepare_case(tmp_path / "c", {**p.defaults, "mesh": "xcoarse"})
    assert "forces_body" in (tmp_path / "c" / "system" / "include" / "forceFunctions").read_text()
    assert "forces_base" not in (tmp_path / "c" / "system" / "include" / "forceFunctions").read_text()
