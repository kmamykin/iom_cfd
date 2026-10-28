"""vpp.hydrostatics: clipped volumes against exact shapes, the wall-sided
GZ curve, and the signs of trim and righting moment."""

import math

import numpy as np
import pytest

from iomcfd.geometry import hulls, stl
from iomcfd.physics import G, fresh_water
from iomcfd.vpp.hydrostatics import Hydrostatics, HydroTable, place, placement, submerged

RHO = fresh_water().rho


def box(length=1.0, beam=0.2, keel=-0.05, deck=0.10, n=6) -> stl.Surface:
    """Closed box, bow at x = 0, bottom at z = keel; each side of the
    section in n pieces so the waterline cuts several triangles."""
    t = np.linspace(0, 1, n, endpoint=False)
    y0, y1 = -beam / 2, beam / 2
    ring = np.vstack([
        np.column_stack([y0 + (y1 - y0) * t, np.full(n, keel)]),  # bottom, starboard -> port
        np.column_stack([np.full(n, y1), keel + (deck - keel) * t]),  # port side, up
        np.column_stack([y1 - (y1 - y0) * t, np.full(n, deck)]),  # deck
        np.column_stack([np.full(n, y0), deck - (deck - keel) * t]),  # starboard side, down
    ])
    return stl.loft([np.column_stack([np.full(len(ring), x), ring]) for x in (0.0, length)], name="box")


def ellipsoid(a, b, c, centre, n_x=161, n_theta=128) -> stl.Surface:
    x = -np.cos(np.linspace(0, math.pi, n_x))
    r = np.sqrt(np.clip(1 - x**2, 0, None))
    return stl.revolve(x, r, n_theta).scaled((a, b, c)).translated(centre)


# --- submerged ------------------------------------------------------------------


def test_wigley_volume_and_waterplane():
    L, B, T = 1.0, 0.18, 0.05
    s = submerged(hulls.wigley(L, B, T))
    assert s.volume == pytest.approx(hulls.wigley_displacement(L, B, T), rel=5e-3)
    assert s.volume == pytest.approx(4 / 9 * L * B * T, rel=5e-3)
    assert s.waterplane_area == pytest.approx(2 / 3 * L * B, rel=5e-3)  # parabolic waterline
    assert s.waterplane_centroid == pytest.approx([L / 2, 0.0], abs=1e-6)
    assert s.centroid[0] == pytest.approx(L / 2, abs=1e-6)
    assert s.lwl == pytest.approx(L, rel=5e-3) and s.bwl == pytest.approx(B, rel=1e-6)


def test_canoe_against_its_exact_shape():
    spec = hulls.CanoeSpec()
    s = submerged(hulls.canoe(spec))
    vol, lcb, area = hulls.canoe_displacement(spec)
    assert s.volume == pytest.approx(vol, rel=5e-3)
    assert s.centroid[0] == pytest.approx(lcb, rel=5e-3)
    # canoe_displacement integrates the section girth along x, which leaves
    # out the slope of the surface along x (the ends narrow and rise), so it
    # is a little low: the facets give 0.65 % more.
    assert s.wetted_area == pytest.approx(area, rel=1e-2)
    assert s.wetted_area > area


def test_box_upright_is_exact():
    s = submerged(box())
    assert s.volume == pytest.approx(1.0 * 0.2 * 0.05, rel=1e-12)
    assert s.centroid == pytest.approx([0.5, 0.0, -0.025], abs=1e-12)
    assert s.wetted_area == pytest.approx(1.0 * 0.2 + 2 * 1.0 * 0.05 + 2 * 0.2 * 0.05, rel=1e-12)
    assert s.waterplane_area == pytest.approx(0.2, rel=1e-12)
    assert s.i_t == pytest.approx(1.0 * 0.2**3 / 12, rel=1e-12)
    assert s.i_l == pytest.approx(0.2 * 1.0**3 / 12, rel=1e-12)


@pytest.mark.parametrize("heel,trim,sink", [(0, 0, 0.0), (30, 4, -0.01), (75, -10, 0.02)])
def test_rotating_the_body_is_rotating_the_plane(heel, trim, sink):
    # An ellipsoid partly under water, placed: its volume below z = 0 is the
    # cap cut off by the plane that z = 0 is in the body's own frame.
    a, b, c, centre = 0.30, 0.08, 0.05, np.array([0.45, 0.01, 0.02])
    body = ellipsoid(a, b, c, centre)
    x_trim = 0.5
    R, t = placement(heel, trim, sink, x_trim)
    n = R[2]  # earth z of a boat-frame point p: n . p + t_z
    m = np.array([a, b, c]) * n  # in the unit sphere, below: u . m <= h |m|
    h = -(n @ centre + t[2]) / np.linalg.norm(m)
    exact = math.pi * (1 + h) ** 2 * (2 - h) / 3 / (4 * math.pi / 3)  # fraction of the volume
    s = submerged(place(body, heel, trim, sink, x_trim))
    assert s.volume / body.volume() == pytest.approx(exact, rel=2e-3)  # facets: 0.03 %


def test_place_matches_placement():
    hull = hulls.wigley()
    R, t = placement(25.0, 3.0, 0.004, 0.5)
    assert place(hull, 25.0, 3.0, 0.004, 0.5).vertices == pytest.approx(hull.vertices @ R.T + t, abs=1e-14)
    # heel: the mast head goes to starboard (−y); trim: the bow goes down
    assert (R @ np.array([0.0, 0.0, 1.0]))[1] < 0
    bow = place(hull, 0.0, 3.0, 0.0, 0.5).vertices[np.argmin(hull.vertices[:, 0])]
    assert bow[2] < hull.vertices[np.argmin(hull.vertices[:, 0]), 2]


# --- floating -------------------------------------------------------------------


def test_box_barge_draft_and_wall_sided_gz():
    L, B, keel = 1.0, 0.2, -0.05
    T = 0.06  # floats 10 mm deeper than its z = 0
    z_g = -0.02
    hs = Hydrostatics(box(L, B, keel), mass=RHO * L * B * T, cg=(L / 2, 0.0, z_g), rho=RHO)
    up = hs.float_at(0.0)
    assert up.converged and up.sink == pytest.approx(T + keel, abs=1e-9)
    assert up.trim == pytest.approx(0.0, abs=1e-9)
    BM, KB, KG = B**2 / (12 * T), T / 2, z_g - keel
    GM = KB + BM - KG
    # wall-sided: valid until the bilge emerges at tan φ = 2T/B (31°) or the deck edge immerses
    for phi in (5, 10, 15, 20, 25, 30):
        f = hs.float_at(phi)
        p = math.radians(phi)
        assert f.converged
        # exact for a box (planar faces, so the clipping is exact too)
        assert f.gz == pytest.approx(math.sin(p) * (GM + 0.5 * BM * math.tan(p) ** 2), rel=1e-6)
        assert f.rm == pytest.approx(f.gz * hs.mass * G)
        # wall-sided: it heels about the middle of its waterline, which is
        # T + keel above the heel axis (the boat's z = 0)
        assert f.sink == pytest.approx((T + keel) * math.cos(p), abs=1e-9)


def test_signs_and_buoyancy():
    spec = hulls.CanoeSpec()
    vol, lcb, _ = hulls.canoe_displacement(spec)
    bulb = (2.1e-4, np.array([0.5, 0.0, -0.40]))
    m = RHO * (vol + bulb[0])
    hs = Hydrostatics(hulls.canoe(spec), appendages=[bulb], mass=m, cg=(0.5, 0.0, -0.25), rho=RHO)
    for heel in (0, 10, 30, 50):
        f = hs.float_at(heel)
        assert f.converged
        assert RHO * G * f.volume == pytest.approx(m * G, rel=1e-8)  # buoyancy = m g
        if heel:
            assert f.rm > 0  # low CG: restoring, towards upright
    up = hs.float_at(0.0)
    assert up.sink == pytest.approx(0.0, abs=2e-4)  # floats at its waterline
    bow_down = hs.float_at(0.0, M_ext=2.0)
    assert bow_down.trim > up.trim + 0.5
    # an upward external force lifts the boat and keeps buoyancy = m g − Z_ext
    lifted = hs.float_at(10.0, Z_ext=5.0)
    assert lifted.sink < hs.float_at(10.0).sink
    assert RHO * G * lifted.volume == pytest.approx(m * G - 5.0, rel=1e-8)
    # a CG above the metacentre capsizes: negative RM
    assert Hydrostatics(hulls.canoe(spec), mass=RHO * vol, cg=(lcb, 0.0, 0.3), rho=RHO).float_at(20.0).rm < 0


def test_table_interpolates_and_flags_extrapolation():
    spec = hulls.CanoeSpec()
    vol, lcb, _ = hulls.canoe_displacement(spec)
    hs = Hydrostatics(hulls.canoe(spec), appendages=[(2.1e-4, np.array([0.5, 0.0, -0.40]))],
                      mass=RHO * (vol + 2.1e-4), cg=(0.5, 0.0, -0.25), rho=RHO)
    tab = hs.table(heels=np.arange(0, 40.1, 5.0), M_ext=np.linspace(-2, 6, 5))
    assert tab.converged.all()
    on = tab.at(20.0, 2.0)
    f = hs.float_at(20.0, M_ext=2.0)
    assert on["rm"] == pytest.approx(f.rm, rel=1e-9) and on["trim"] == pytest.approx(f.trim, rel=1e-9)
    between = tab.at(17.5, 1.0)
    f = hs.float_at(17.5, M_ext=1.0)
    assert not between["extrapolated"]
    assert between["rm"] == pytest.approx(f.rm, rel=1e-2)
    assert between["sink"] == pytest.approx(f.sink, abs=2e-4)
    assert tab.rm(17.5) == pytest.approx(tab.at(17.5, 0.0)["rm"])
    out = tab.at(55.0, 1.0)
    assert out["extrapolated"] and out["rm"] == pytest.approx(tab.at(40.0, 1.0)["rm"])  # clamped
    assert tab.at(20.0, 9.0)["extrapolated"]


def test_table_flags_cells_with_no_equilibrium():
    # trim = M_ext, except a node with no equilibrium (heel 20, M_ext 3) that holds garbage
    heels, M = np.array([0.0, 10.0, 20.0, 30.0]), np.array([0.0, 1.0, 2.0, 3.0])
    trim = np.tile(M, (4, 1)).astype(float)
    conv = np.ones((4, 4), bool)
    trim[2, 3], conv[2, 3] = 55.0, False
    values = {k: (trim if k == "trim" else np.zeros((4, 4))) for k in HydroTable.KEYS}
    tab = HydroTable(heels, M, values, conv)
    assert not tab.at(5.0, 0.5)["extrapolated"] and tab.at(5.0, 0.5)["trim"] == pytest.approx(0.5)
    assert not tab.at(15.0, 1.5)["extrapolated"]
    near = tab.at(25.0, 2.5)  # a corner of its cell found no equilibrium
    assert near["extrapolated"] and near["trim"] == pytest.approx(2.5, abs=1e-6)  # the linear continuation
    assert tab.at(15.0, 2.5)["extrapolated"]
    assert HydroTable.from_rows(tab.rows()).at(25.0, 2.5)["extrapolated"]
