"""hull views (ParaView, rendered by `iomcfd viz`).

wave_pattern   free surface (alpha = 0.5) seen from above, coloured by
               elevation: the Kelvin wave system (mirrored for half-domain runs)
wave_profile   free surface and hull seen low from the side: bow and stern
               waves (option `exaggerate` scales heights, default 1)
hull_pressure  p_rgh / (0.5 rho V^2) on the hull, seen from below and to port
centre_plane   water/air on the boat's centre plane, with the free-surface
               line and speed/V

Options: exaggerate (wave_profile vertical scale), elevation (colour range
in metres; default from V^2/2g).
"""

from __future__ import annotations

import numpy as np

from iomcfd.viz.geom import heel_basis, heeled

DEFAULT_VIEWS = ["wave_pattern", "wave_profile", "hull_pressure", "centre_plane"]
ANIMATE_VIEWS = ["wave_pattern", "wave_profile", "centre_plane"]
ANIMATE_PARAMS = ["speed", "heel", "leeway", "trim", "sinkage", "hull", "mesh"]
TIME_VIEWS = ["wave_pattern", "centre_plane"]


def _setup(ctx):
    d = ctx.d
    box = d.get("hullBoxBoat") or [*(d.get("hullMin") or d["nearBoxMin"]), *(d.get("hullMax") or d["nearBoxMax"])]
    xm = 0.5 * (box[0] + box[3])
    heel = float(ctx.p.get("heel", 0.0))
    L = float(d["Lwl"])
    V = ctx.U
    rho = float(d.get("rhoWater", 998.0))
    return box, (xm, 0.0, 0.0), heel, L, V, rho


def _elev_range(ctx, V):
    e = ctx.options.get("elevation")
    return float(e) if e else max(0.004, 0.4 * V * V / (2 * 9.81))


def _hull(ctx, gray=(0.25, 0.25, 0.28)):
    s = ctx.surface(r"patch/boat.*", arrays=["p_rgh"])
    if ctx.d.get("halfDomain"):
        s = ctx.reflect_y(s)
    ctx.solid(ctx.show(s), gray)
    return s


def _free_surface(ctx):
    fs = ctx.contour(ctx.reader(arrays=["alpha.water", "U"]), "alpha.water", [0.5])
    if ctx.d.get("halfDomain"):
        fs = ctx.reflect_y(fs)
    return ctx.calc(fs, "elevation", "coordsZ")


def _title(ctx, what: str):
    p, d, m = ctx.p, ctx.d, ctx.m
    parts = [f"speed {p['speed']} m/s (Fn {d.get('Fn', 0):.2f})", f"heel {p.get('heel', 0)} deg",
             f"leeway {p.get('leeway', 0)} deg", f"mesh {p['mesh']}"]
    if "resistance_N" in m:
        parts.append(f"resistance {m['resistance_N']:.3f} N")
    ctx.title(f"{what}\n" + "   ".join(parts))


def wave_pattern(ctx):
    box, pivot, heel, L, V, rho = _setup(ctx)
    e = _elev_range(ctx, V)
    ctx.new_view()
    ctx.color(ctx.show(_free_surface(ctx)), "elevation", "Cool to Warm", (-e, e), "wave elevation [m]")
    _hull(ctx)
    c = (box[0] + 1.0 * L, 0.0, 0.0)
    ctx.camera(c, (0, 0, 1), (0, 1, 0), 0.5 * 3.4 * L * 900 / 1600)
    _title(ctx, "wave pattern (free surface seen from above)")


def wave_profile(ctx):
    box, pivot, heel, L, V, rho = _setup(ctx)
    from paraview import simple as pv

    k = float(ctx.options.get("exaggerate", 1.0))
    e = _elev_range(ctx, V)
    ctx.new_view()
    fs = ctx.track(pv.Transform(Input=_free_surface(ctx)))
    fs.Transform.Scale = [1.0, 1.0, k]
    ctx.color(ctx.show(fs), "elevation", "Cool to Warm", (-e, e), "wave elevation [m]")
    hull = ctx.surface(r"patch/boat.*", arrays=["p_rgh"])
    hs = ctx.track(pv.Transform(Input=hull))
    hs.Transform.Scale = [1.0, 1.0, k]
    ctx.solid(ctx.show(hs), (0.25, 0.25, 0.28))
    c = (0.5 * (box[0] + box[3]) + 0.3 * L, 0.0, 0.0)
    ctx.camera(c, (0.0, 1.0, 0.22), (0, 0, 1), 0.5 * 2.2 * L * 900 / 1600, parallel=False)
    _title(ctx, "bow and stern waves" + (f" (vertical scale x{k:g})" if k != 1 else ""))


def hull_pressure(ctx):
    box, pivot, heel, L, V, rho = _setup(ctx)
    ctx.new_view()
    s = ctx.surface(r"patch/boat.*", arrays=["p_rgh"])
    if ctx.d.get("halfDomain"):
        s = ctx.reflect_y(s)
    cp = ctx.calc(s, "Cp", f"p_rgh/{0.5 * rho * V * V}")
    ctx.color(ctx.show(cp), "Cp", "Cool to Warm", (-0.6, 0.6), "p_rgh / (0.5 rho V^2)")
    ey, ez = heel_basis(heel)
    c = heeled((0.5 * (box[0] + box[3]), 0.0, 0.5 * box[2]), heel, pivot)
    ctx.camera(c, 0.8 * ey - 0.6 * ez + np.array([-0.15, 0, 0]), ez, 0.5 * 1.45 * L * 900 / 1600)
    _title(ctx, "hull pressure (dynamic and wave), seen from below to port")


def centre_plane(ctx):
    box, pivot, heel, L, V, rho = _setup(ctx)
    ey, ez = heel_basis(heel)
    eps = 0.003 * L
    origin = heeled((0.5 * (box[0] + box[3]), -eps, 0.0), heel, pivot)
    ctx.new_view()
    sl = ctx.slice(origin, ey, source=ctx.reader(arrays=["alpha.water", "U"]))
    rel = ctx.calc(sl, "Urel", f"mag(U)/{V}")
    top = 1.4 if "aws" not in ctx.d else 1.2 * float(ctx.d["aws"]) / V  # fullboat: air is faster
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.0, top), "speed / V (boat speed)")
    line = ctx.contour(sl, "alpha.water", [0.5])
    ctx.solid(ctx.show(line), (1, 1, 1), line_width=2.5)
    _hull(ctx)
    c = heeled((0.5 * (box[0] + box[3]) + 0.25 * L, 0.0, 0.0), heel, pivot)
    ctx.camera(c, -ey, ez, 0.5 * 1.8 * L * 900 / 1600)
    _title(ctx, "centre plane: flow speed and the free surface (white)")


VIEWS = {
    "wave_pattern": wave_pattern,
    "wave_profile": wave_profile,
    "hull_pressure": hull_pressure,
    "centre_plane": centre_plane,
}
