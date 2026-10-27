import math

import numpy as np
import pytest
from scipy.integrate import trapezoid

from iomcfd.geometry import hulls
from iomcfd.physics import G, fresh_water
from iomcfd.vpp import hullres as hr

# Wigley hull of the 1979 Workshop on Ship Wave-Resistance Computations:
# L/B = 10, L/T = 16, C_W = R_w / (½ρV²S) with S = 0.1487 L² (Lazauskas 2009,
# "Resistance, wave-making and wave-decay of thin ships", PhD thesis,
# Univ. Adelaide, Table 7.1 and §7.4.1).
WIGLEY_B, WIGLEY_T, WIGLEY_S = 0.1, 0.0625, 0.1487


def wigley_offsets(length=1.0, beam=WIGLEY_B, draft=WIGLEY_T, nx=81, nz=21):
    x = np.linspace(0.0, length, nx)
    z = np.linspace(-draft, 0.0, nz)
    xi = x / length - 0.5
    return x, z, 0.5 * beam * (1 - (2 * xi[:, None]) ** 2) * (1 - (z[None, :] / draft) ** 2)


def wigley_cw(fn, nx=81, nz=21, n_lambda=None):
    V = fn * math.sqrt(G)
    return hr.michell(*wigley_offsets(nx=nx, nz=nz), V, n_lambda=n_lambda) / (0.5 * 1000.0 * V**2 * WIGLEY_S)


def test_ittc57():
    assert hr.ittc57(1e6) == pytest.approx(0.0046875, rel=1e-12)
    np.testing.assert_allclose(hr.ittc57([1e6, 1e7]), [0.0046875, 0.075 / 25])


def test_friction_resistance():
    # Re = 1e6: 0.5 * 1000 * 1 * 0.1 * 1.1 * 0.8 * 0.0046875
    R = hr.friction_resistance(1.0, 0.1, 1.0, 1e-6, 1000.0, form_factor=0.1, cf_factor=0.8)
    assert R == pytest.approx(0.20625, rel=1e-12)
    R = hr.friction_resistance(np.array([0.0, 0.5, 1.0]), 0.1, 1.0, 1e-6, 1000.0)
    assert R[0] == 0.0 and np.all(np.diff(R) > 0)


# Published Michell values for that Wigley hull, 1000 C_W:
# * Fn 0.2: "the true wave resistance coefficient is 0.89 (to 2 decimal
#   places)" (Landweber, discussion at the 1979 workshop, quoted in
#   Lazauskas 2009 §6.5);
# * the humps, hollow and peak: Lazauskas 2009 Fig. 7.6 (Fn < 0.41) and
#   Fig. 7.1 (Fn up to 1), digitised from the thesis PDF at 600 dpi on the
#   figures' gridlines (residual < 0.5 px). The curve's line is ±0.004-0.007
#   wide in 1000 C_W at the smooth points, so the readings are good to
#   about 0.3 %. Each extremum is the max or min over its Fn window.
WIGLEY_POINTS = [
    # (Fn window, max/min/at, 1000 C_W published)
    ((0.200, 0.200), "at", 0.89),
    ((0.230, 0.245), "max", 1.397),
    ((0.290, 0.310), "max", 2.143),
    ((0.335, 0.360), "min", 1.236),
    ((0.450, 0.550), "max", 4.517),
    ((0.600, 0.600), "at", 3.918),
    ((0.800, 0.800), "at", 2.594),
]


@pytest.mark.parametrize("window,kind,published", WIGLEY_POINTS)
def test_michell_wigley_published(window, kind, published):
    fns = np.arange(window[0], window[1] + 1e-9, 0.001)
    cw = np.array([1000 * wigley_cw(fn) for fn in fns])
    got = {"at": cw[0], "max": cw.max(), "min": cw.min()}[kind]
    # 1 %: the reading (0.3 %, Landweber's 2 decimals 0.6 %) plus the
    # 81 × 21 grid, which is 0.1 % low (test_michell_converges).
    assert got == pytest.approx(published, rel=0.01)


@pytest.mark.parametrize("fn,tol", [(0.04, 0.004), (0.05, 0.007)])
def test_michell_low_froude_limit(fn, tol):
    """Michell's integral tends to its low-Fn expansion (Wehausen 1973, Adv.
    Appl. Mech. 13; in Lazauskas 2009 eq. 7.8) as Fn → 0. For the Wigley
    hull the bow and stern half-angles are 2B/L, and the end-point
    asymptotics of the λ integral give
    R_w = 16 ρ g L B² Fn⁶ (4/(3π) + √(2/π) Fn cos(Fn⁻² + π/4)) + O(Fn⁸).
    This checks the constant 4ρg²/(πV²) independently of the curves."""
    V = fn * math.sqrt(G)
    R = hr.michell(*wigley_offsets(), V)
    bracket = 4 / (3 * math.pi) + math.sqrt(2 / math.pi) * fn * math.cos(fn**-2 + math.pi / 4)
    expansion = 16 * 1000 * G * WIGLEY_B**2 * fn**6 * bracket
    assert R == pytest.approx(expansion, rel=tol)


@pytest.mark.parametrize("fn", [0.16, 0.3, 0.5, 1.0])
def test_michell_converges(fn):
    coarse, fine = wigley_cw(fn), wigley_cw(fn, nx=161, nz=81)
    assert coarse == pytest.approx(fine, rel=2e-3)
    assert wigley_cw(fn, n_lambda=4000) == pytest.approx(coarse, rel=1e-4)


def test_michell_froude_scaling_and_sign():
    """R_w / (ρ g ∇) depends only on Fn and the shape."""
    fn = 0.35
    small = hr.michell(*wigley_offsets(1.0, 0.1, 0.0625), fn * math.sqrt(G))
    big = hr.michell(*wigley_offsets(3.0, 0.3, 0.1875), fn * math.sqrt(3 * G))
    vol = hulls.wigley_displacement
    assert small / vol(1.0, 0.1, 0.0625) == pytest.approx(big / vol(3.0, 0.3, 0.1875), rel=1e-9)
    assert all(hr.michell(*wigley_offsets(), v) >= 0 for v in (0.2, 0.5, 1.0, 3.0))
    assert hr.michell(*wigley_offsets(), 0.0) == 0.0


def test_canoe_offsets():
    spec = hulls.CanoeSpec()
    x, z, y = hr.canoe_offsets(spec)
    assert x[0] == 0 and x[-1] == pytest.approx(spec.length) and z[-1] == 0
    assert z[0] == pytest.approx(-spec.draft)
    assert y.max() == pytest.approx(spec.beam / 2, rel=1e-3)
    assert np.all(y[[0, -1]] == 0)
    # sinkage lowers every station; the vertical sides keep the waterline beam
    xs, zs, ys = hr.canoe_offsets(spec, sink=0.01)
    assert zs[0] == pytest.approx(-spec.draft - 0.01)
    assert ys[:, -1] == pytest.approx(y[:, -1])
    # bow down: the keel is deeper forward, and the stern lifts out
    xt, zt, yt = hr.canoe_offsets(spec, trim=2.0)
    keel = zt[np.argmax(yt > 0, axis=1)]
    L = spec.length
    assert np.interp(0.25 * L, xt, keel) < np.interp(0.75 * L, xt, keel) - 0.01
    assert xt[0] == 0 and xt[-1] < 0.95 * L and yt[-1].max() == 0


def test_offsets_wetted_area_and_length():
    spec = hulls.CanoeSpec()
    _, _, exact = hulls.canoe_displacement(spec)
    fine = hr.canoe_offsets(spec, nx=201, nz=201)
    assert hr.offsets_wetted_area(*fine) == pytest.approx(exact, rel=2e-3)
    assert hr.offsets_waterline_length(*fine) == pytest.approx(spec.length)
    # the stern lifts out when the bow goes down
    assert hr.offsets_waterline_length(*hr.canoe_offsets(spec, trim=3.0, nx=201, nz=201)) < spec.length


@pytest.mark.parametrize("sink,trim", [(0.0, 0.0), (0.005, 0.0), (0.0, 1.0), (0.004, -1.5)])
def test_surface_offsets_match_canoe(sink, trim):
    spec = hulls.CanoeSpec()
    xs, zs, ys = hr.surface_offsets(hulls.canoe(spec), sink, trim)
    xc, zc, yc = hr.canoe_offsets(spec, sink, trim)
    assert zs[0] == pytest.approx(zc[0], abs=5e-4)
    # sectional areas along the same stations (the STL's ends are cut at
    # 0.3 % of L, so compare at the STL's stations)
    rise = sink - (xs - 0.5 * spec.length) * math.tan(math.radians(trim))
    y_exact = hr._canoe_section(spec, xs[:, None], zs[None, :] + rise[:, None])
    area_s, area_c = trapezoid(ys, zs, axis=1), trapezoid(y_exact, zs, axis=1)
    assert np.abs(area_s - area_c).max() < 0.02 * area_c.max()
    if sink == trim == 0:
        assert np.abs(ys - y_exact).max() < 0.02 * spec.beam / 2
    # R_w: within 2 % from 0.75 m/s (Fn 0.24). Below that R_w is a few %
    # of R_f and grid-sensitive: at 0.5 m/s both are within 3 % of a fine
    # grid upright but up to 8 % off when trimmed.
    speeds = [(0.75, 0.02), (1.0, 0.02), (1.5, 0.02)] + ([(0.5, 0.03)] if sink == trim == 0 else [])
    for V, tol in speeds:
        assert hr.michell(xs, zs, ys, V) == pytest.approx(hr.michell(xc, zc, yc, V), rel=tol)


def test_canoe_resistance():
    spec = hulls.CanoeSpec()
    w = fresh_water(15.0)
    V = np.array([0.5, 1.0, 1.5])
    r = hr.canoe_resistance(spec, V, w.rho, w.nu)
    _, _, area = hulls.canoe_displacement(spec)
    assert r["wetted_area"] == area and r["L_wl"] == spec.length
    np.testing.assert_allclose(r["R_f"], hr.friction_resistance(V, area, spec.length, w.nu, w.rho, 0.1))
    np.testing.assert_allclose(r["R_total"], r["R_f"] + r["R_w"])
    np.testing.assert_allclose(r["Fn"], V / math.sqrt(G * spec.length))
    assert np.all(np.diff(r["R_w"]) > 0) and r["R_w"][0] < 0.05 * r["R_f"][0]
    one = hr.canoe_resistance(spec, 1.0, w.rho, w.nu)
    assert one["R_total"] == pytest.approx(r["R_total"][1])
    # sinkage wets more of the vertical sides
    sunk = hr.canoe_resistance(spec, 1.0, w.rho, w.nu, sink=0.005)
    assert sunk["wetted_area"] > area and sunk["L_wl"] == pytest.approx(spec.length)
    assert sunk["R_w"] > one["R_w"]
    # laminar bracket: cf_factor scales friction only
    lam = hr.canoe_resistance(spec, 1.0, w.rho, w.nu, cf_factor=0.6)
    assert lam["R_f"] == pytest.approx(0.6 * one["R_f"]) and lam["R_w"] == one["R_w"]


def test_hull_side_yaw():
    rho, V, T, L, vol = 1000.0, 1.0, 0.053, 0.99, 0.0036
    S, x_cp, N = hr.hull_side_yaw(V, 3.0, T, L, vol, rho)
    beta = math.radians(3.0)
    assert S == pytest.approx(math.pi * 0.5 * rho * V**2 * T**2 * beta, rel=2e-3)  # π q T² β
    assert S > 0 and N > 0  # to port and bow to port (destabilising) for β > 0
    assert N == pytest.approx(rho * vol * V**2 * math.sin(beta) * math.cos(beta))
    Sm, _, Nm = hr.hull_side_yaw(V, -3.0, T, L, vol, rho)
    assert Sm == pytest.approx(-S) and Nm == pytest.approx(-N)
    assert x_cp == pytest.approx(0.7 / 3 * L)
    # x_cp is the centre of d(T(x)²)/dx over the canoe's keel line forward of its deepest point
    spec = hulls.CanoeSpec(draft_at=0.45, rise_fwd=2.5)
    x = np.linspace(0, spec.draft_at * spec.length, 20001)
    t2 = hulls.canoe_depth(spec, x) ** 2
    centre = float(np.sum(0.5 * (x[1:] + x[:-1]) * np.diff(t2)) / t2[-1])
    _, x_cp, _ = hr.hull_side_yaw(V, 3.0, spec.draft, spec.length, vol, rho, spec.draft_at, spec.rise_fwd)
    assert x_cp == pytest.approx(centre, rel=1e-4)
    S2, _, N2 = hr.hull_side_yaw(np.array([1.0, 2.0]), 3.0, T, L, vol, rho)
    np.testing.assert_allclose(S2, [S, 4 * S])
