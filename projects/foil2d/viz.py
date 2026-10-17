"""foil2d views (ParaView, rendered by `iomcfd viz`).

Each view is a function(ctx) that builds a scene; the renderer saves it.
All colour ranges are normalised (speed/U, Cp, ...) so cases and frames are
comparable. Add a view: write a function and list it in VIEWS.

velocity        speed/U with streamlines (overall flow, wake, stagnation point)
pressure        pressure coefficient Cp (suction peak, loading)
separation      streamwise velocity close-up of the laminar separation
                bubble (blue = reversed flow), zoomed from the case's
                x_sep/x_reattach, with streamlines through the bubble
transition      intermittency of the transition model (0 laminar, 1 turbulent)
eddy_viscosity  nut/nu, log scale (where the flow is turbulent)
boundary_layer  the whole suction side: streamwise velocity on a light
                background (free stream pale, boundary layer dark, reversed
                flow blue), for reading the flow regime at a glance
vorticity       spanwise vorticity w c/U around the foil and wake: shear
                layers and shed vortices
"""

from __future__ import annotations

import math

import numpy as np

from iomcfd.viz import Skip

DEFAULT_VIEWS = ["velocity", "pressure", "separation", "transition", "eddy_viscosity"]
ANIMATE_VIEWS = ["velocity", "separation", "transition", "boundary_layer", "vorticity"]  # study animations, one frame per case
ANIMATE_PARAMS = ["aoa", "Tu", "speed", "Re", "foil", "chord", "mesh", "turbulence"]
TIME_VIEWS = ["velocity", "separation", "boundary_layer", "vorticity"]  # transient runs with snapshots


def _geom(ctx):
    c = float(ctx.p["chord"])
    span = float(ctx.d["mesh_spec"]["span"])
    a = math.radians(float(ctx.p["aoa"]))
    return c, span, a


def _upper_surface(ctx):
    """Upper surface y(x) in metres from constant/geometry/foil.dat."""
    c = float(ctx.p["chord"])
    f = ctx.dir / "constant" / "geometry" / "foil.dat"
    pts = np.loadtxt(f, skiprows=1)
    i_le = int(np.argmin(pts[:, 0]))
    up = pts[: i_le + 1][::-1]  # LE -> TE
    return lambda x: float(np.interp(x / c, up[:, 0], up[:, 1])) * c


def _base(ctx):
    """Slice near the back plane; streamlines seeded mid-span draw on top of it."""
    _, span, _ = _geom(ctx)
    return ctx.slice((0.0, 0.0, 0.1 * span), (0.0, 0.0, 1.0))


def _outline(ctx):
    foil = ctx.surface(r"patch/foil", arrays=["p"])
    ctx.solid(ctx.show(foil, representation="Wireframe"), (0, 0, 0), line_width=2.0)


def _flat(disp):
    """Exact colour-map colours on a 2D slice (no lighting)."""
    disp.Ambient, disp.Diffuse, disp.Specular = 1.0, 0.0, 0.0
    return disp


def _title(ctx, what: str):
    p, d, m = ctx.p, ctx.d, ctx.m
    parts = [f"{str(p['foil']).upper()}", f"Re {d['Reynolds']:,.0f}", f"aoa {p['aoa']} deg", p["turbulence"],
             f"Tu {p['Tu']}%", f"mesh {p['mesh']}", p.get("solver", "steady")]
    if "Cl" in m and "Cd" in m:
        parts.append(f"Cl {m['Cl']:.3f}  Cd {m['Cd']:.4f}")
    ctx.title(f"{what}\n" + "   ".join(str(x) for x in parts))


def velocity(ctx):
    c, span, _ = _geom(ctx)
    ctx.new_view()
    rel = ctx.calc(_base(ctx), "Urel", f"mag(U)/{ctx.U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.0, 1.6), "speed / U")
    st = ctx.streamlines_line((-0.3 * c, -0.3 * c, 0.5 * span), (-0.3 * c, 0.3 * c, 0.5 * span), n=44, length=3 * c)
    ctx.solid(ctx.show(st), (0.08, 0.08, 0.08), line_width=1.2)
    _outline(ctx)
    ctx.camera_2d(-0.3 * c, 1.5 * c, 0.0)
    _title(ctx, "velocity magnitude and streamlines")


def pressure(ctx):
    c, _, _ = _geom(ctx)
    ctx.new_view()
    cp = ctx.calc(_base(ctx), "Cp", f"p/{0.5 * ctx.U ** 2}")
    ctx.color(ctx.show(cp), "Cp", "Cool to Warm", (-2.5, 1.0), "Cp")
    _outline(ctx)
    ctx.camera_2d(-0.3 * c, 1.5 * c, 0.0)
    _title(ctx, "pressure coefficient")


def _reversed_extent(ctx):
    """(start, end) x/c of reversed wall flow (Cf < 0) on the upper surface,
    ahead of x/c = 0.8, from the case's surface.csv; None if attached."""
    f = ctx.dir / "surface.csv"
    if not f.is_file():
        return None
    rows = np.genfromtxt(f, delimiter=",", names=True, dtype=None, encoding=None)
    up = rows[rows["upper"].astype(str) == "True"]
    sel = (up["x_c"] > 0.005) & (up["x_c"] < 0.8) & (up["Cf"] < 0)
    if not sel.any():
        return None
    return float(up["x_c"][sel].min()), float(up["x_c"][sel].max())


def separation(ctx):
    c, span, a = _geom(ctx)
    ext = _reversed_extent(ctx)
    if ext:
        xs, xr = ext
        x0, x1 = max(-0.02, xs - 0.06), min(1.05, xr + 0.08)
        if x1 - x0 < 0.18:
            x0, x1 = 0.5 * (x0 + x1) - 0.09, 0.5 * (x0 + x1) + 0.09
        xm = xs + 0.4 * (xr - xs)
        note = f"reversed wall flow (Cf < 0) on the upper surface from x/c = {xs:.3f} to {xr:.3f}"
    else:
        x0, x1, xm, note = -0.02, 0.40, 0.15, "upper-surface flow attached (no Cf < 0 ahead of x/c = 0.8)"
    yu = _upper_surface(ctx)
    ctx.new_view(1600, 600)  # wide: the bubble is a thin layer along the surface
    us = ctx.calc(_base(ctx), "Us", f"(U_X*{math.cos(a)} + U_Y*{math.sin(a)})/{ctx.U}")
    lut = ctx.color(_flat(ctx.show(us)), "Us", "Cool to Warm", (-0.3, 1.35), "U_s / U  (blue: reversed)")
    lut.RGBPoints = BL_POINTS
    # streamlines seeded on a short wall-normal line through the bubble
    y0 = yu(xm * c)
    st = ctx.streamlines_line((xm * c, y0 + 1e-4 * c, 0.5 * span), (xm * c, y0 + 0.04 * c, 0.5 * span),
                              n=36, length=2 * c)
    ctx.solid(ctx.show(st), (0.35, 0.35, 0.35), line_width=0.8)
    _outline(ctx)
    half_h = 0.5 * (x1 - x0) * c * 600 / 1600
    ctx.camera_2d(x0 * c, x1 * c, yu(0.5 * (x0 + x1) * c) + 0.45 * half_h)
    _title(ctx, "streamwise velocity near the upper surface")
    ctx.note(note, corner="Lower Right Corner")


def transition(ctx):
    if not ctx.has("gammaInt"):
        raise Skip("no intermittency field (fully turbulent model)")
    c, _, _ = _geom(ctx)
    ctx.new_view()
    ctx.color(ctx.show(_base(ctx)), "gammaInt", "Viridis", (0.0, 1.0), "intermittency")
    _outline(ctx)
    ctx.camera_2d(-0.05 * c, 1.25 * c, 0.03 * c)
    _title(ctx, "intermittency: laminar (0) / turbulent (1) boundary layer")


def eddy_viscosity(ctx):
    if not ctx.has("nut"):
        raise Skip("no nut field")
    c, _, _ = _geom(ctx)
    ctx.new_view()
    r = ctx.calc(_base(ctx), "nutRatio", f"nut/{float(ctx.d['nu'])} + 0.01")
    ctx.color(ctx.show(r), "nutRatio", "Turbo", (0.01, 300.0), "nut / nu", log=True)
    _outline(ctx)
    ctx.camera_2d(-0.2 * c, 2.2 * c, 0.0)
    _title(ctx, "eddy viscosity ratio")


# streamwise velocity Us/U: reversed flow blue, zero dark, free stream pale (page colour), faster than the
# free stream light amber. RGB points: value, r, g, b.
BL_POINTS = [-0.3, 0.10, 0.28, 0.62, -0.03, 0.55, 0.72, 0.92, 0.0, 0.16, 0.19, 0.22,
             0.5, 0.55, 0.58, 0.58, 0.97, 0.985, 0.98, 0.965, 1.35, 0.95, 0.72, 0.42]


def boundary_layer(ctx):
    c, span, a = _geom(ctx)
    ctx.new_view(1800, 520)
    us = ctx.calc(_base(ctx), "Us", f"(U_X*{math.cos(a)} + U_Y*{math.sin(a)})/{ctx.U}")
    lut = ctx.color(_flat(ctx.show(us)), "Us", "Cool to Warm", (-0.3, 1.35), "U_s / U  (blue: reversed)",
                    bar_position=(0.62, 0.05), bar_length=0.3, horizontal=True)
    lut.RGBPoints = BL_POINTS
    rake = ctx.streamlines_line((-0.05 * c, 0.004 * c, 0.5 * span), (-0.05 * c, 0.12 * c, 0.5 * span),
                                n=10, length=3 * c)
    ctx.solid(ctx.show(rake), (0.55, 0.55, 0.55), line_width=0.6)
    _outline(ctx)
    x0, x1 = -0.03, 1.08
    half_h = 0.5 * (x1 - x0) * c * 520 / 1800
    ctx.camera_2d(x0 * c, x1 * c, 0.5 * half_h - 0.01 * c)
    _title(ctx, "streamwise velocity along the suction side")


def vorticity(ctx):
    c, _, _ = _geom(ctx)
    ctx.new_view(1800, 700)
    g = ctx.gradient(_base(ctx), vorticity=True, q=False)
    w = ctx.calc(g, "wz", f"Vorticity_Z*{c}/{ctx.U}")
    ctx.color(_flat(ctx.show(w)), "wz", "Cool to Warm", (-40.0, 40.0), "vorticity  w c / U")
    _outline(ctx)
    ctx.camera_2d(-0.1 * c, 1.8 * c, 0.03 * c)
    _title(ctx, "spanwise vorticity")


VIEWS = {
    "velocity": velocity,
    "pressure": pressure,
    "separation": separation,
    "transition": transition,
    "eddy_viscosity": eddy_viscosity,
    "boundary_layer": boundary_layer,
    "vorticity": vorticity,
}
