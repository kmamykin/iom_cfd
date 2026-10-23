"""keel3d views (ParaView, rendered by `iomcfd viz`).

surface_cp_port / _starboard  Cp on hull, fin and bulb seen from each side
                              (at leeway the starboard side is the pressure side)
vortices                      Q-criterion iso-surface: fin-bulb, fin-hull and
                              hull vortices, coloured by speed/U
wake_slice                    streamwise vorticity in a plane behind the keel,
                              looking forward
section                       speed/U on a horizontal section at mid-span of the
                              fin, with in-plane streamlines
tip_cp                        Cp on the lower fin and the bulb, close up from the
                              suction side (port), with isobars: the fin's tip or
                              the fin-bulb junction
tip_vorticity                 streamwise vorticity in a cross-flow plane 0.5 tip
                              chord behind the fin's trailing edge, over the bulb,
                              looking forward: the tip and junction vortices
streamlines                   3D streamlines (tubes, coloured by speed/U) seeded
                              ahead of the fin, ahead of the bulb and through a
                              ball behind the fin's tip, seen from below the
                              waterline; with
                              --options '{"orbit": 240}' also a video of the
                              camera turning once round the keel

Views follow the heel: cameras and cut planes are in the boat frame (the boat
heels about the x axis at the waterline). Options (study `viz: options:` or
--options): q_level (default 2), Q is q_level * (U / mean chord)^2.
"""

from __future__ import annotations

import numpy as np

from iomcfd.viz.geom import box_center, heel_basis, heeled

DEFAULT_VIEWS = ["surface_cp_port", "surface_cp_starboard", "vortices", "wake_slice", "section"]
ANIMATE_VIEWS = ["surface_cp_port", "vortices", "wake_slice"]
ANIMATE_PARAMS = ["leeway", "fin_taper", "speed", "heel", "fin_sweep", "mesh", "bulb_aspect", "bulb_cant"]
TIME_VIEWS: list[str] = []
ORBIT_VIEWS = ["streamlines"]

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


def _title(ctx, what: str, size: int = 20):
    p, m = ctx.p, ctx.m
    parts = [f"taper {p['fin_taper']}", f"speed {p['speed']} m/s", f"leeway {p['leeway']} deg",
             f"heel {p['heel']} deg", f"mesh {p['mesh']}"]
    if not p.get("bulb", True):
        parts.insert(1, "no bulb")
    else:  # bulb shape, where it isn't the round default
        shape = [f"{k[5:]} {p[k]}" for k, v in (("bulb_aspect", 1.0), ("bulb_top", 2.0), ("bulb_bottom", 2.0),
                                                ("bulb_cant", 0.0)) if float(p.get(k, v)) != v]
        if shape:
            parts.insert(1, "bulb " + ", ".join(shape))
    if "drag_N" in m and "side_N" in m:
        parts.append(f"drag {m['drag_N']:.3f} N  side {m['side_N']:.3f} N")
    parts.append(f"{p.get('turbulence', 'kOmegaSST')}, fully turbulent")
    ctx.title(f"{what}\n" + "   ".join(parts), size=size)


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


def _tip(ctx):
    """The fin's tip (boat frame, over the bulb's centre of mass), its tip chord and the x of its
    trailing edge there. Without a bulb the tip is where the bulb's top would be."""
    p, d = ctx.p, ctx.d
    c_tip = float(d["fin_tip_chord"])
    z_top = float(d["fin_z_root"]) - float(d["fin_span"])
    x_te = float(p["fin_x"]) + np.tan(np.radians(float(p["fin_sweep"]))) * float(d["fin_span"]) + 0.75 * c_tip
    return np.array([float(d.get("bulb_x_cg", p["fin_x"])), 0.0, z_top]), c_tip, x_te


def tip_cp(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    tip, c_tip, x_te = _tip(ctx)
    ctx.new_view(1200, 675)
    s = ctx.surface(r"patch/boat_(fin|bulb)", arrays=["p"])
    cp = ctx.calc(s, "Cp", f"p/{0.5 * ctx.U ** 2}")
    ctx.color(ctx.show(cp), "Cp", "Cool to Warm", (-0.6, 0.6), "Cp", label_format="{:.1f}", horizontal=True,
              bar_position=(0.6, 0.04), bar_length=0.36, font_size=18)
    iso = ctx.contour(cp, "Cp", [-0.5, -0.4, -0.3, -0.2, -0.1])
    ctx.solid(ctx.show(iso), (0.1, 0.1, 0.1), line_width=1.5)
    c = heeled(np.array([x_te - 0.1 * c_tip, 0.0, tip[2] + 0.02]), heel, PIVOT)
    ctx.camera(c, ey - 0.3 * ez, ez, 0.105)  # from port, the suction side at + leeway, a little below
    _title(ctx, "pressure coefficient at the fin tip, suction (port) side, bow to the right\n"
                "lines: Cp -0.5 to -0.1 in steps of 0.1", size=18)
    ctx.note("flow right to left", size=18, corner="Lower Left Corner")


def tip_vorticity(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    tip, c_tip, x_te = _tip(ctx)
    x = x_te + 0.5 * c_tip
    ctx.new_view(1200, 675)
    g = ctx.gradient(ctx.reader(arrays=["U"]), q=False)
    sl = ctx.slice((x, 0, 0), (1, 0, 0), source=g)
    w = ctx.calc(sl, "wx", f"Vorticity_X*{chord / ctx.U}")
    ctx.color(ctx.show(w), "wx", "Cool to Warm", (-4.0, 4.0), "streamwise vorticity  w_x c / U", label_format="{:g}",
              font_size=18)
    c = heeled(np.array([x, 0.0, tip[2] - 0.005]), heel, PIVOT)
    ctx.camera(c, (1.0, 0.0, 0.0), ez, 0.06)
    _title(ctx, f"cross-flow plane {1e3 * (x - x_te):.0f} mm behind the fin's trailing edge at its tip, looking forward",
           size=18)
    ctx.note("pressure (starboard) side", size=18, corner="Lower Left Corner")
    ctx.note("suction (port) side", size=18, corner="Lower Right Corner")


def streamlines(ctx):
    heel, box, chord, ey, ez = _setup(ctx)
    p, d = ctx.p, ctx.d
    tip, c_tip, x_te = _tip(ctx)
    z_root, z_top = float(d["fin_z_root"]), tip[2]
    x_le = float(p["fin_x"]) - 0.25 * float(d["fin_root_chord"])
    B = lambda q: heeled(q, heel, PIVOT)  # noqa: E731 - boat frame to world
    src = ctx.reader(arrays=["U"])
    lines = []  # downstream from rakes just ahead of the fin and of the bulb's nose
    rakes = [((x_le - 0.3 * chord, 0.0, z_root - 0.01), (x_le - 0.3 * chord, 0.0, z_top + 0.01), 20)]
    if p.get("bulb", True):
        L, xb, zb = float(d["bulb_length"]), float(d["bulb_x_cg"]), float(d["bulb_z_axis"])
        x0 = xb - 0.5 * L
        rakes += [((x0, -0.04, zb), (x0, 0.04, zb), 14), ((x0, 0.0, zb - 0.035), (x0, 0.0, zb + 0.035), 10)]
    for p1, p2, n in rakes:
        st = ctx.streamlines_line(B(p1), B(p2), n=n, length=1.2, source=src)
        st.IntegrationDirection, st.MaximumSteps = "FORWARD", 10000
        lines.append(st)
    # and both ways through a cloud just behind the fin's tip: the flow that passes the tip or the junction
    cloud = ctx.streamlines_cloud(B((x_te + 0.25 * c_tip, 0.0, z_top - 0.002)), 0.015, n=70, length=1.2, source=src)
    cloud.MaximumSteps = 10000
    lines.append(cloud)
    ctx.new_view(1280, 720)  # small enough for a website video
    for st in lines:  # speed/U: the free stream mid-scale, slower water blue, faster red
        rel = ctx.calc(st, "Urel", f"mag(U)/{ctx.U}")
        ctx.color(ctx.show(ctx.tubes(rel, 0.0008)), "Urel", "Turbo", (0.8, 1.2), "speed / U", label_format="{:.2f}",
                  horizontal=True, bar_position=(0.6, 0.04), bar_length=0.36, font_size=16)
    _bodies(ctx)
    c = B(np.array([0.5 * (x_le + x_te), 0.0, 0.5 * (z_root + z_top)]))
    # from starboard, a little aft and below the waterline; the vertical is the world's (the boat heels)
    ctx.camera(c, (0.35, -1.0, -0.3), (0.0, 0.0, 1.0), 0.3, parallel=False)
    _title(ctx, "streamlines, coloured by speed / U, seen from below the waterline", size=17)
    ctx.note("seeded ahead of the fin and of the bulb,\nand through a ball just behind the fin's tip", size=15,
             corner="Lower Left Corner")


VIEWS = {
    "surface_cp_port": surface_cp_port,
    "surface_cp_starboard": surface_cp_starboard,
    "vortices": vortices,
    "wake_slice": wake_slice,
    "section": section,
    "tip_cp": tip_cp,
    "tip_vorticity": tip_vorticity,
    "streamlines": streamlines,
}
