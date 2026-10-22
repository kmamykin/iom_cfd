"""bulb2d views (ParaView, rendered by `iomcfd viz`).

The mesh is a 5 deg wedge of the body of revolution. Every view slices it at
its mid-plane (z = 0), the meridian plane through the axis, and mirrors that
about the axis (y = 0), so it shows a whole longitudinal section through the
bulb. The flow runs from left to right (+x). Colour ranges are fixed and
normalised, so cases compare directly.

tail_flow   signed axial velocity U_x/U over the after-body and the near wake
            (blue: the flow runs backwards, i.e. it has separated)
whole_body  speed/U around the whole body and its wake, with streamlines
"""

from __future__ import annotations

DEFAULT_VIEWS = ["tail_flow", "whole_body"]
ANIMATE_VIEWS = ["tail_flow"]
ANIMATE_PARAMS = ["fineness", "speed", "Tu", "turbulence", "Re", "mesh"]
TIME_VIEWS: list[str] = []

# axial velocity Ux/U: reversed flow blue, zero dark, free stream pale, faster than the free stream amber
# (the same map as foil2d's boundary-layer views). RGB points: value, r, g, b.
BL_POINTS = [-0.3, 0.10, 0.28, 0.62, -0.03, 0.55, 0.72, 0.92, 0.0, 0.16, 0.19, 0.22,
             0.5, 0.55, 0.58, 0.58, 0.97, 0.985, 0.98, 0.965, 1.35, 0.95, 0.72, 0.42]
# speed/U on the same colours: still water dark, free stream pale, faster amber
SPEED_POINTS = [0.0, 0.16, 0.19, 0.22, 0.5, 0.55, 0.58, 0.58, 0.97, 0.985, 0.98, 0.965, 1.15, 0.95, 0.72, 0.42]


def _L(ctx) -> float:
    return float(ctx.d["length_m"])


def _section(ctx, arrays=("U",)):
    return ctx.reflect_y(ctx.slice((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), source=ctx.reader(arrays=list(arrays))))


def _outline(ctx):
    body = ctx.reflect_y(ctx.surface(r"patch/body", arrays=["p"]))
    ctx.solid(ctx.show(body, representation="Wireframe"), (0.05, 0.05, 0.05), line_width=2.0)


def _flat(disp):
    """Exact colour-map colours on a slice (no lighting)."""
    disp.Ambient, disp.Diffuse, disp.Specular = 1.0, 0.0, 0.0
    return disp


def _title(ctx, what: str):
    p, d, m = ctx.p, ctx.d, ctx.m
    body = f"NACA body, L/D {float(p['fineness']):g}" if p["body"] == "naca" else str(p["body"])
    case = [body, f"L {1e3 * _L(ctx):.0f} mm", f"{ctx.U:.2f} m/s", f"Re_L {d['Re_L']:,.0f}"]
    model = [p["turbulence"], f"Tu {p['Tu']}%", f"mesh {p['mesh']}", "steady"]
    if "Cd_wet" in m:
        model.append(f"C_D,wet {m['Cd_wet']:.4f}")
    ctx.title(f"{what}  (flow left to right)\n" + "   ".join(case) + "\n" + "   ".join(str(x) for x in model), size=22)


def tail_flow(ctx):
    L, m = _L(ctx), ctx.m
    ctx.new_view(1200, 470)
    sec = _section(ctx)
    ux = ctx.calc(sec, "Ux", f"U_X/{ctx.U}")
    lut = ctx.color(_flat(ctx.show(ux)), "Ux", "Cool to Warm", (-0.3, 1.35), "U_x / U  (blue: reversed flow)",
                    bar_position=(0.6, 0.06), bar_length=0.32, horizontal=True, label_format="{:.1f}", font_size=18)
    lut.RGBPoints = BL_POINTS
    _outline(ctx)
    ctx.camera_2d(0.55 * L, 1.12 * L, 0.0)
    _title(ctx, "axial velocity over the tail")
    sep = m.get("x_sep")
    if sep is not None:
        rea = m.get("x_reattach")
        ctx.note(f"reversed wall flow (C_f < 0) from x/L = {sep:.2f}" + (f" to {rea:.2f}" if rea else "") +
                 " (surface.csv)", size=18, corner="Lower Left Corner")
    else:
        ctx.note("attached: no reversed wall flow (C_f > 0 everywhere)", size=18, corner="Lower Left Corner")


def whole_body(ctx):
    L = _L(ctx)
    ctx.new_view(1200, 400)
    sec = _section(ctx)
    rel = ctx.calc(sec, "Urel", f"mag(U)/{ctx.U}")
    lut = ctx.color(_flat(ctx.show(rel)), "Urel", "Cool to Warm", (0.0, 1.15), "speed / U",
                    bar_position=(0.6, 0.06), bar_length=0.32, horizontal=True, label_format="{:.1f}", font_size=18)
    lut.RGBPoints = SPEED_POINTS
    st = ctx.streamlines_line((-0.15 * L, 0.004 * L, 0.0), (-0.15 * L, 0.18 * L, 0.0), n=16, length=2.0 * L,
                              source=sec, surface=True)
    ctx.solid(ctx.show(st), (0.3, 0.3, 0.3), line_width=0.8)
    _outline(ctx)
    ctx.camera_2d(-0.12 * L, 1.45 * L, 0.0)
    _title(ctx, "speed around the bulb")


VIEWS = {
    "tail_flow": tail_flow,
    "whole_body": whole_body,
}
