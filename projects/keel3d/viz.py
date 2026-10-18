"""keel3d views (ParaView, rendered by `iomcfd viz`).

surface_cp_port / _starboard  Cp on hull, fin and bulb seen from each side
                              (at leeway the starboard side is the pressure side)
vortices                      Q-criterion iso-surface: fin-bulb, fin-hull and
                              hull vortices, coloured by speed/U
wake_slice                    streamwise vorticity in a plane behind the keel,
                              looking forward
section                       speed/U on a horizontal section at mid-span of the
                              fin, with in-plane streamlines

Views follow the heel: cameras and cut planes are in the boat frame (the boat
heels about the x axis at the waterline). Options (study `viz: options:` or
--options): q_level (default 2), Q is q_level * (U / mean chord)^2.
"""

from __future__ import annotations

import numpy as np

from iomcfd.viz.geom import box_center, heel_basis, heeled

DEFAULT_VIEWS = ["surface_cp_port", "surface_cp_starboard", "vortices", "wake_slice", "section"]
ANIMATE_VIEWS = ["surface_cp_port", "vortices", "wake_slice"]
ANIMATE_PARAMS = ["leeway", "fin_taper", "speed", "heel", "fin_sweep", "mesh"]
TIME_VIEWS: list[str] = []

PIVOT = (0.0, 0.0, 0.0)


def _setup(ctx):
    p, d = ctx.p, ctx.d
    heel = float(p["heel"])
    box = d["bodyBoxBoat"]
    ey, ez = heel_basis(heel)
    return heel, box, float(p["fin_mean_chord"]), ey, ez


def _bodies(ctx, gray=True):
    s = ctx.surface(r"patch/boat.*", arrays=["p"])
    disp = ctx.show(s)
    if gray:
        ctx.solid(disp, (0.62, 0.62, 0.66))
    return s, disp


def _title(ctx, what: str):
    p, m = ctx.p, ctx.m
    parts = [f"taper {p['fin_taper']}", f"speed {p['speed']} m/s", f"leeway {p['leeway']} deg",
             f"heel {p['heel']} deg", f"mesh {p['mesh']}"]
    if "drag_N" in m and "side_N" in m:
        parts.append(f"drag {m['drag_N']:.3f} N  side {m['side_N']:.3f} N")
    ctx.title(f"{what}\n" + "   ".join(parts))


def _surface_cp(ctx, side: float, label: str):
    heel, box, chord, ey, ez = _setup(ctx)
    ctx.new_view()
    s = ctx.surface(r"patch/boat.*", arrays=["p"])
    cp = ctx.calc(s, "Cp", f"p/{0.5 * ctx.U ** 2}")
    ctx.color(ctx.show(cp), "Cp", "Cool to Warm", (-1.0, 0.6), "Cp")
    c = heeled(box_center(box), heel, PIVOT)
    half = 0.55 * max((box[3] - box[0]) * 900 / 1600, box[5] - box[2])
    ctx.camera(c, side * ey + 0.15 * ez, ez, half)
    _title(ctx, f"pressure coefficient, {label} side")


def surface_cp_port(ctx):
    _surface_cp(ctx, +1.0, "port")


def surface_cp_starboard(ctx):
    _surface_cp(ctx, -1.0, "starboard")


def vortices(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    q_level = float(ctx.options.get("q_level", 2.0)) * (ctx.U / chord) ** 2
    ctx.new_view()
    g = ctx.gradient(ctx.reader(arrays=["U", "p"]))
    iso = ctx.contour(g, "Q Criterion", [q_level])
    rel = ctx.calc(iso, "Urel", f"mag(U)/{ctx.U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.6, 1.2), "speed / U")
    _bodies(ctx)
    c = heeled(box_center(box), heel, PIVOT) + np.array([0.15 * (box[3] - box[0]), 0, 0])
    half = 0.6 * max((box[3] - box[0]) * 1.4 * 900 / 1600, box[5] - box[2])
    ctx.camera(c, np.array([0.75, 0, 0]) + 0.55 * ey - 0.45 * ez, ez, half, parallel=False)
    _title(ctx, f"vortices: Q-criterion = {float(ctx.options.get('q_level', 2.0)):g} (U/c)^2")


def wake_slice(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    p, d = ctx.p, ctx.d
    te = float(p["fin_x"]) + 0.75 * float(d["fin_root_chord"])  # root trailing edge
    x = te + 0.6 * chord
    ctx.new_view()
    g = ctx.gradient(ctx.reader(arrays=["U"]), q=False)
    sl = ctx.slice((x, 0, 0), (1, 0, 0), source=g)
    w = ctx.calc(sl, "wx", f"Vorticity_X*{chord / ctx.U}")
    ctx.color(ctx.show(w), "wx", "Cool to Warm", (-8.0, 8.0), "streamwise vorticity  w_x c / U")
    c = heeled(box_center(box), heel, PIVOT)
    c[0] = x
    half = 0.6 * (box[5] - box[2]) * 1.2
    ctx.camera(c, (1.0, 0.0, 0.0), ez, half)
    _title(ctx, f"wake {x - te:.3f} m behind the fin root trailing edge, looking forward")


def section(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    p, d = ctx.p, ctx.d
    zm = float(d["fin_z_root"]) - 0.5 * float(d["fin_span"])
    xf = float(p["fin_x"]) + 0.25 * chord
    origin = heeled((xf, 0.0, zm), heel, PIVOT)
    ctx.new_view()
    sl = ctx.slice(origin, ez)
    rel = ctx.calc(sl, "Urel", f"mag(U)/{ctx.U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.0, 1.5), "speed / U")
    up = origin - 1.5 * chord * np.array([1, 0, 0])
    st = ctx.streamlines_line(up - 0.8 * chord * ey, up + 0.8 * chord * ey, n=40, length=6 * chord, source=sl, surface=True)
    ctx.solid(ctx.show(st), (0.08, 0.08, 0.08), line_width=1.0)
    ctx.camera(origin + 0.3 * chord * np.array([1, 0, 0]), ez, ey, 1.4 * chord * 900 / 1600 * 1.6)
    _title(ctx, "fin section at mid-span")


VIEWS = {
    "surface_cp_port": surface_cp_port,
    "surface_cp_starboard": surface_cp_starboard,
    "vortices": vortices,
    "wake_slice": wake_slice,
    "section": section,
}
