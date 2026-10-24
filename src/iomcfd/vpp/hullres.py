"""Hull resistance, side force and yaw moment: rung 0 of the hull model.

Analytic estimates for the canoe body (no appendages) until the hull
project's CFD tables replace them. Pure functions, SI units, boat frame
(x aft, y port, z up, bow at x = 0, waterline z = 0; docs/geometry.md):

* friction: ITTC-57 line with a form factor (`friction_resistance`);
* waves: Michell's thin-ship integral over the centreplane offsets
  (`michell`), with the offsets from the parametric canoe body
  (`canoe_offsets`) or a closed STL hull (`surface_offsets`);
* side force and yaw moment at leeway: slender-body theory
  (`hull_side_yaw`).

`canoe_resistance` puts friction and waves together for a CanoeSpec.
In docs/nomenclature.md terms R_f is the hull's D_v, R_w the wave part of
D_r, and S, N its shares of S_h and N_h.
"""

from __future__ import annotations

import dataclasses
import functools
import math

import numpy as np
from scipy.integrate import trapezoid  # numpy < 2 in the solver image

from ..geometry import hulls
from ..geometry.stl import Surface
from ..physics import G

# --------------------------------------------------------------------------
# Friction


def ittc57(Re):
    """ITTC-57 model-ship correlation line, C_F = 0.075 / (log10 Re − 2)².
    Re below 1e4 is clipped (the line has a pole at Re = 100)."""
    Re = np.maximum(np.asarray(Re, float), 1e4)
    return (0.075 / (np.log10(Re) - 2.0) ** 2)[()]


def friction_resistance(V, wetted_area: float, length: float, nu: float, rho: float,
                        form_factor: float = 0.0, cf_factor: float = 1.0):
    """Viscous resistance R_f = ½ρV²S (1 + k) · cf_factor · C_F(Re_L) [N],
    with C_F from ITTC-57 at Re_L = V L / ν (V scalar or array).

    ITTC-57 assumes a turbulent boundary layer from the bow. At IOM scale
    (Re_L ≈ 1e6) the hull may stay partly laminar: flat-plate friction with
    natural transition is up to 41 % lower at 1 m/s
    (docs/research/surface-roughness.md). `cf_factor` (e.g. 0.6-1.0)
    brackets that; `form_factor` k adds the pressure part of the viscous
    drag (k ≈ 0.1 for a slender canoe body, an estimate).
    """
    V = np.asarray(V, float)
    return (0.5 * rho * V**2 * wetted_area * (1 + form_factor) * cf_factor * ittc57(V * length / nu))[()]


# --------------------------------------------------------------------------
# Michell's thin-ship wave resistance


def _linear_exp_weights(s: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weights (w_a, w_b), shape (len(c), len(s) − 1), with
    ∫ f e^{c s} ds over [s_j, s_j+1] = w_a f(s_j) + w_b f(s_j+1) exactly for
    f linear there (a Filon-type rule: no limit on |c Δs|). c real or complex."""
    h = np.diff(s)[None, :]
    t = c[:, None] * h
    E = np.exp(c[:, None] * s[None, :])
    Ea, Eb = E[:, :-1], E[:, 1:]
    small = np.abs(t) < 1e-2  # the closed form cancels there; use its series
    ts = np.where(small, 1.0, t)
    q = h / ts**2
    wa, wb = q * (Eb - Ea - ts * Ea), q * (ts * Eb - Eb + Ea)
    if small.any():
        t, e, h = t[small], Ea[small], np.broadcast_to(h, small.shape)[small]
        wa[small] = e * h * (1 / 2 + t / 6 + t**2 / 24 + t**3 / 120)
        wb[small] = e * h * (1 / 2 + t / 3 + t**2 / 8 + t**3 / 30)
    return wa, wb


def michell(x, z, y, V: float, g: float = G, rho: float = 1000.0, n_lambda: int | None = None) -> float:
    """Wave resistance R_w [N] of a thin ship from Michell's integral
    (Michell 1898; in this form Dambrine, Pierre & Rousseaux, arXiv:1410.2800,
    eq. 2.1-2.3; an equivalent form in Lazauskas 2009, PhD thesis, Univ.
    Adelaide, §5.1):

        R_w = 4ρg² / (πV²) ∫₁^∞ |P + iQ|² λ² / √(λ² − 1) dλ
        P + iQ = ∫∫ ∂y/∂x · exp(k₀λ²z) · exp(ik₀λx) dx dz,  k₀ = g / V²

    x (nx,) stations and z (nz,) waterlines, ascending, with z from the
    keel to the waterline (z ≤ 0); y (nx, nz) the half-breadth on that
    grid (0 outside the hull). λ = sec θ, θ the direction of the waves.

    Thin-ship theory: linearised inviscid flow, a fixed hull (sinkage and
    trim enter only through the offsets), deep water, no transom flow.
    Michell over-predicts the humps and hollows at Fn < 0.4 compared with
    tank tests (Lazauskas 2009, Fig. 7.6).

    Quadrature: ∂y/∂x by second-order differences, taken piecewise linear
    in x (exact for the Wigley hull) and the x integral done exactly for
    that; the result piecewise linear in z with the e^{k₀λ²z} weight done
    exactly; λ = 1 + s² removes the 1/√(λ² − 1) singularity and the
    trapezoidal rule in s (the integrand is even in s) does the rest.
    n_lambda (default: adaptive) resolves the bow-stern interference
    period, which shrinks as 1/(k₀L).
    """
    x, z, y = np.asarray(x, float), np.asarray(z, float), np.asarray(y, float)
    if V <= 0:
        return 0.0
    k0 = g / V**2
    length, depth = x[-1] - x[0], max(-z[0], 1e-9)
    # The integrand falls off as λ^-5 beyond max(1, 1/√(k0 T)), where the
    # z factor starts to decay: integrate to 20 times that (tail < 1e-5)
    # and resolve the oscillation, phase k0 λ L, to 8 times that.
    knee = max(1.0, 1.0 / math.sqrt(k0 * depth))
    s_max = math.sqrt(20 * knee - 1)
    if n_lambda is None:
        ds = (2 * math.pi / 8) / (2 * k0 * length * math.sqrt(8 * knee - 1))  # 8 points per period
        n_lambda = int(np.clip(math.ceil(s_max / ds), 200, 40000))
    s = np.linspace(0.0, s_max, n_lambda)
    lam = 1 + s**2
    yx = np.gradient(y, x, axis=0, edge_order=2)
    wa, wb = _linear_exp_weights(x, 1j * k0 * lam)
    f = wa @ yx[:-1] + wb @ yx[1:]  # (n_lambda, nz): the x integral on each waterline
    za, zb = _linear_exp_weights(z, k0 * lam**2)
    pq = (za * f[:, :-1] + zb * f[:, 1:]).sum(axis=1)
    integrand = np.abs(pq) ** 2 * lam**2 * 2 / np.sqrt(lam + 1)  # dλ/√(λ²−1) = 2 ds/√(λ+1)
    return float(4 * rho * g**2 / (math.pi * V**2) * trapezoid(integrand, s))


# --------------------------------------------------------------------------
# Offsets


def _stations(x0: float, x1: float, n: int) -> np.ndarray:
    """n stations from x0 to x1, cosine-clustered at both ends. The thin bow
    and stern sections make most of the short waves: on 81 × 21 the canoe's
    R_w at 0.5 m/s (Fn 0.16) is 12 % off with uniform stations, and within
    3 % at 0.5-2 m/s with these."""
    return x0 + (x1 - x0) * 0.5 * (1 - np.cos(np.linspace(0.0, math.pi, n)))


def _canoe_section(spec: hulls.CanoeSpec, x, zb) -> np.ndarray:
    """Half-breadth of the canoe body at station x and height zb above its
    design waterline: the superellipse below it, vertical sides above it up
    to the freeboard, 0 below the keel and above the deck."""
    b, t = hulls.canoe_half_breadth(spec, x), hulls.canoe_depth(spec, x)
    r = np.clip(-zb / np.maximum(t, 1e-12), 0.0, 1.0)
    y = np.where(zb <= 0, b * (1 - r**spec.section) ** (1 / spec.section), b)
    return np.where((zb >= -t) & (zb <= spec.freeboard), y, 0.0)


def canoe_offsets(spec: hulls.CanoeSpec, sink: float = 0.0, trim: float = 0.0, x_trim: float | None = None,
                  nx: int = 81, nz: int = 21) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x, z, y): half-breadths y (nx, nz) of the canoe body after sinkage
    `sink` [m, + down] and trim `trim` [deg, + bow down] about (x_trim, 0, 0)
    (default mid-length), on nx stations over the wetted length
    (cosine-clustered at its ends) and nz uniform waterlines from the
    deepest keel point to the new waterline.

    Small-angle trim: each station is lowered by sink − (x − x_trim) tan(trim)
    and stays vertical (the x shift of order z·trim is ignored).
    """
    x_trim = 0.5 * spec.length if x_trim is None else x_trim
    slope = math.tan(math.radians(trim))

    def rise(x):  # height of the new waterline on the body at station x
        return sink - (x - x_trim) * slope

    # The wetted length: where the keel is below the new waterline (to L/4000).
    xf = np.linspace(0.0, spec.length, 4001)
    wet = np.flatnonzero(hulls.canoe_depth(spec, xf) + rise(xf) > 0)
    if wet.size == 0:
        raise ValueError(f"the canoe body is out of the water at sink {sink} m, trim {trim} deg")
    x = _stations(xf[max(wet[0] - 1, 0)], xf[min(wet[-1] + 1, len(xf) - 1)], nx)
    r = rise(x)
    z = np.linspace(float(np.min(-hulls.canoe_depth(spec, x) - r)), 0.0, nz)
    return x, z, _canoe_section(spec, x[:, None], z[None, :] + r[:, None])


def surface_offsets(surface: Surface, sink: float = 0.0, trim: float = 0.0, x_trim: float | None = None,
                    nx: int = 81, nz: int = 21) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x, z, y) as canoe_offsets, from a closed STL hull in the boat frame.

    The surface is trimmed (rotated about the y axis through (x_trim, 0, 0),
    default mid-length of its bounding box; exact, not small-angle) and then
    sunk. Each station plane cuts the triangles into segments of the
    section; y is the largest |y| where they cross each waterline. Stations
    span the wetted length (the vertices below the waterline and the edges'
    crossings of it), waterlines the lowest vertex to z = 0. A symmetric
    hull is assumed (port and starboard are not told apart).
    """
    lo, hi = surface.bounds
    x_trim = 0.5 * (lo[0] + hi[0]) if x_trim is None else x_trim
    placed = surface.rotated("y", -trim, about=(x_trim, 0.0, 0.0)).translated((0.0, 0.0, -sink))
    tri = placed.vertices[placed.triangles]  # (M, 3 corners, xyz)
    tri = tri[tri[:, :, 2].min(axis=1) < 0]
    if len(tri) == 0:
        raise ValueError(f"the surface is out of the water at sink {sink} m, trim {trim} deg")
    a, b = tri, tri[:, [1, 2, 0]]  # the edges of each triangle
    za, zb = a[:, :, 2], b[:, :, 2]
    crosses = (za < 0) != (zb < 0)
    x_wl = (a[:, :, 0] + za / np.where(crosses, za - zb, 1.0) * (b[:, :, 0] - a[:, :, 0]))[crosses]
    x_wet = np.concatenate([a[:, :, 0][za < 0], x_wl])
    x = _stations(x_wet.min(), x_wet.max(), nx)
    z = np.linspace(za.min(), 0.0, nz)
    y = np.zeros((nx, nz))
    for i, xs in enumerate(x):
        # Half-open sides (x >= xs) make every cut triangle cross exactly two edges.
        sa, sb = a[:, :, 0] >= xs, b[:, :, 0] >= xs
        cross = sa != sb
        cut = cross.any(axis=1)
        if not cut.any():
            continue
        ea, eb, c = a[cut], b[cut], cross[cut]
        dx = np.where(c, eb[:, :, 0] - ea[:, :, 0], 1.0)
        p = ea + ((xs - ea[:, :, 0]) / dx)[:, :, None] * (eb - ea)  # (K, 3, xyz)
        two = np.argsort(~c, axis=1, kind="stable")[:, :2]
        seg = np.take_along_axis(p, two[:, :, None], axis=1)  # (K, 2 ends, xyz)
        y0, z0, y1, z1 = seg[:, 0, 1:2], seg[:, 0, 2:3], seg[:, 1, 1:2], seg[:, 1, 2:3]
        hit = (z0 >= z) != (z1 >= z)  # (K, nz)
        u = (z - z0) / np.where(z1 != z0, z1 - z0, 1.0)
        y[i] = np.where(hit, np.abs(y0 + u * (y1 - y0)), 0.0).max(axis=0)
    return x, z, y


def offsets_wetted_area(x, z, y) -> float:
    """Wetted area [m²] from offsets: twice the girth of each section
    (polyline through the wet points, from the keel to the waterline),
    integrated along x. Ignores the longitudinal slope of the surface (as
    hulls.canoe_displacement does) and puts the keel at the last dry
    waterline (an overestimate of up to one waterline spacing per section)."""
    x, z, y = np.asarray(x, float), np.asarray(z, float), np.asarray(y, float)
    seg = np.hypot(np.diff(y, axis=1), np.diff(z)[None, :])
    girth = np.where(y[:, 1:] > 0, seg, 0.0).sum(axis=1)
    return float(trapezoid(2 * girth, x))


def offsets_waterline_length(x, z, y) -> float:
    """Length of the waterline [m]: from the last dry station before the
    wetted waterline to the first dry one after it (to within one station;
    canoe_offsets puts the end stations within L/4000 of the wetted ends)."""
    wet = np.flatnonzero(np.asarray(y)[:, -1] > 0)
    if wet.size == 0:
        return 0.0
    return float(x[min(wet[-1] + 1, len(x) - 1)] - x[max(wet[0] - 1, 0)])


# --------------------------------------------------------------------------
# Side force and yaw moment at leeway


def hull_side_yaw(V, leeway_deg, draft: float, length: float, volume: float, rho: float,
                  draft_at: float = 0.5, rise: float = 2.0, k21: float = 1.0):
    """Rough rung-0 (S, x_cp, N_munk) of the canoe body at leeway β_Y, from
    slender-body theory. Heel, the free-surface waves, the beam and the
    appendages (the fin's carry-over onto the hull) are all ignored.

    * Side force S [N], + to port (windward) for β > 0. At low Froude number
      the free surface acts as a reflection plane, so the hull of draft T
      is half of a slender wing of span b = 2T. Jones (1946, NACA TR 835)
      gives that wing L = (π/4)ρV²b²α, with the vortex sheet shed from the
      deepest station aft. For the half body:
          S = (π/2) ρ V² T² sin β cos β = π q T² β (small β).
      It is the leading term, π (T/L)², of the ship-manoeuvring derivative
      Y'_v in Clarke, Gedling & Hine (1983) (from memory, not re-checked).
    * x_cp [m from the bow]: where S acts. The local force is ∝ d(T(x)²)/dx
      from the bow to the deepest station and zero aft of it. For a keel
      line T(x) = T (1 − (1 − ξ/a)^n) forward of ξ = a (CanoeSpec's
      draft_at and rise_fwd), x_cp = a L (2/(n+1) − 1/(2n+1)), i.e. 0.233 L
      for the defaults (a = 0.5, n = 2).
    * N_munk [N m], + = bow to port: Munk's (1924, NACA TR 184) moment on a
      body that sheds no vorticity, N = (k₂ − k₁) ρ ∇ V² sin β cos β. It is
      destabilising: it turns the bow further to port at β > 0. For a
      slender body k₂ − k₁ → 1 (`k21`). Strip theory with the hull's
      half-elliptic sections gives k21 ≈ T/b (the sway added mass ρπT²/2
      against the area πbT/2), about 0.64 for the default canoe.

    The two are alternative idealisations of the same flow, not terms to
    add: with vortex shedding (Jones) the hull carries S at x_cp and no
    other couple; without it (Munk) there is no net force, only N_munk.
    A real hull lies between them. A leeway sweep of the hull CFD should
    replace both. Background: Newman (1977), Marine Hydrodynamics, ch. 5
    (low-aspect-ratio lifting surfaces) and ch. 7 (slender bodies).
    """
    beta = np.radians(np.asarray(leeway_deg, float))
    sc = np.sin(beta) * np.cos(beta)
    V2 = np.asarray(V, float) ** 2
    S = 0.5 * math.pi * rho * V2 * draft**2 * sc
    x_cp = draft_at * length * (2 / (rise + 1) - 1 / (2 * rise + 1))
    N = k21 * rho * volume * V2 * sc
    return S[()], x_cp, N[()]


# --------------------------------------------------------------------------
# The canoe body


@functools.lru_cache(maxsize=32)
def _design_areas(spec_fields: tuple) -> tuple[float, float]:
    """(exact wetted area, the 201 × 201 offsets' area) at the design attitude.
    Cached: canoe_displacement takes ~25 ms."""
    spec = hulls.CanoeSpec(*spec_fields)
    return hulls.canoe_displacement(spec)[2], offsets_wetted_area(*canoe_offsets(spec, nx=201, nz=201))


def canoe_resistance(spec: hulls.CanoeSpec, V, rho: float, nu: float, sink: float = 0.0, trim: float = 0.0,
                     form_factor: float = 0.1, cf_factor: float = 1.0, nx: int = 81, nz: int = 21) -> dict:
    """Resistance of the canoe body at speed V (scalar or array) and attitude
    (sink m, + down; trim deg, + bow down): R_f (friction_resistance), R_w
    (michell on canoe_offsets, nx × nz), R_total = R_f + R_w [N], and the
    wetted area, L_wl and Fn used.

    Upright, at the design attitude the wetted area is exact
    (hulls.canoe_displacement) and L_wl = spec.length. At another attitude
    both come from fine offsets (201 × 201): the area by girth integration
    (offsets_wetted_area), scaled by the exact/offsets ratio at the design
    attitude to remove the grid bias.

    form_factor 0.1 is ITTC-57 × 1.10, the hull estimate of
    projects/foil2d/methodology.md (section 8); an estimate, not measured.

    Grid: on 81 × 21, R_w is within 3 % of a converged grid upright at
    0.5-2 m/s. Trimmed, the waterline ends bluntly where the keel leaves the
    water, and R_w converges only to first order: up to 8 % low at
    0.5 m/s (where R_w is ~5 % of R_total), 1 % from 1 m/s.
    """
    area, area_offsets = _design_areas(dataclasses.astuple(spec))
    L_wl = spec.length
    if sink or trim:
        fine = canoe_offsets(spec, sink, trim, nx=201, nz=201)
        area *= offsets_wetted_area(*fine) / area_offsets
        L_wl = offsets_waterline_length(*fine)
    x, z, y = canoe_offsets(spec, sink, trim, nx=nx, nz=nz)
    Vs = np.asarray(V, float)
    R_w = np.array([michell(x, z, y, v, rho=rho) for v in Vs.ravel()]).reshape(Vs.shape)
    R_f = np.asarray(friction_resistance(Vs, area, L_wl, nu, rho, form_factor, cf_factor))
    return {
        "R_f": R_f[()],
        "R_w": R_w[()],
        "R_total": (R_f + R_w)[()],
        "wetted_area": area,
        "L_wl": L_wl,
        "Fn": (Vs / math.sqrt(G * L_wl))[()],
    }
