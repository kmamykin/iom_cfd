"""sails views (ParaView, rendered by `iomcfd viz`).

sail_cp_leeward / _windward  Cp on the sails seen from each side. A sail
                             is a baffle: two coincident wall patches (main,
                             main_slave), one per side; only the face looking
                             at the camera is drawn, so each side shows the
                             pressure of the air on that side.
streamlines                  3D streamlines through the rig, speed/U
section_mid / section_upper  speed/U on horizontal sections at 45 % and 75 % of
                             the rig height, with in-plane streamlines: the
                             jib-main slot and the twist of the flow
"""

from __future__ import annotations

import numpy as np

from iomcfd.viz.geom import box_center, heel_basis, heeled

DEFAULT_VIEWS = ["sail_cp_leeward", "sail_cp_windward", "streamlines", "section_mid", "section_upper"]
ANIMATE_VIEWS = ["sail_cp_leeward", "section_mid"]
ANIMATE_PARAMS = ["awa", "main_sheet", "jib_sheet", "main_twist", "jib_twist", "camber", "heel", "aws", "mesh"]
TIME_VIEWS: list[str] = []


def _setup(ctx):
    d = ctx.d
    box = d.get("rigBoxBoat") or [*(d.get("rigMin") or d["nearBoxMin"]), *(d.get("rigMax") or d["nearBoxMax"])]
    heel = float(ctx.p.get("heel", 0.0))
    if "hullBoxBoat" in d:  # fullboat heels about midship
        pivot = (0.5 * (d["hullBoxBoat"][0] + d["hullBoxBoat"][3]), 0.0, 0.0)
    else:
        pivot = (0.0, 0.0, 0.0)
    U = float(d.get("aws") or ctx.U)
    return box, heel, pivot, U


def _rig(ctx, rgb=(0.6, 0.6, 0.64)):
    s = ctx.surface(r"patch/(main|jib|mast).*", arrays=["p"])
    ctx.solid(ctx.show(s), rgb)
    return s


def _title(ctx, what: str):
    p, m = ctx.p, ctx.m
    if "awa" in p:
        parts = [f"AWA {p['awa']} deg", f"AWS {p['aws']} m/s"]
    else:
        parts = [f"TWA {p['twa']} deg", f"TWS {p['tws']} m/s", f"AWA {ctx.d.get('awa_deg', 0):.1f} deg"]
    parts += [f"heel {p.get('heel', 0)} deg", f"sheet {p.get('main_sheet')}/{p.get('jib_sheet')} deg", f"mesh {p['mesh']}"]
    if "drive_N" in m:
        parts.append(f"drive {m['drive_N']:.3f} N  heel force {m['heel_force_N']:.3f} N")
    ctx.title(f"{what}\n" + "   ".join(parts))


def _sail_cp(ctx, side: float, label: str):
    box, heel, pivot, U = _setup(ctx)
    ey, ez = heel_basis(heel)
    ctx.new_view()
    s = ctx.surface(r"patch/(main|jib).*", arrays=["p"])
    cp = ctx.calc(s, "Cp", f"p/{0.5 * U * U}")
    disp = ctx.show(cp)
    disp.BackfaceRepresentation = "Cull Frontface"  # patch normals point into the sail
    ctx.color(disp, "Cp", "Cool to Warm", (-2.5, 1.0), "Cp")
    mast = ctx.surface(r"patch/mast", arrays=["p"])
    ctx.solid(ctx.show(mast), (0.2, 0.2, 0.2))
    c = heeled(box_center(box), heel, pivot)
    half = 0.55 * max((box[3] - box[0]) * 900 / 1600, box[5] - box[2])
    ctx.camera(c, side * ey + 0.1 * np.array([1, 0, 0]), ez, half)
    _title(ctx, f"pressure on the sails, {label} side")


def sail_cp_leeward(ctx):
    _sail_cp(ctx, -1.0, "leeward (starboard)")


def sail_cp_windward(ctx):
    _sail_cp(ctx, +1.0, "windward (port)")


def streamlines(ctx):
    box, heel, pivot, U = _setup(ctx)
    ey, ez = heel_basis(heel)
    H = box[5]
    flow = np.asarray(ctx.d.get("dragDir") or [1, 0, 0], float)
    if "Uair" in ctx.d:
        flow = np.asarray(ctx.d["Uair"], float) / np.linalg.norm(ctx.d["Uair"])
    c = heeled(box_center(box), heel, pivot)
    seed = c - 0.5 * H * flow
    ctx.new_view()
    st = ctx.streamlines_line((seed[0], seed[1], 0.08 * H), (seed[0], seed[1], 1.05 * H), n=50, length=4 * H)
    rel = ctx.calc(st, "Urel", f"mag(U)/{U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.5, 1.5), "speed / U")
    _rig(ctx)
    ctx.camera(c + np.array([0.3 * H, 0, 0]), np.array([-0.4, 0, 0]) - 0.8 * ey + 0.35 * ez, ez,
               0.6 * H, parallel=False)
    _title(ctx, "streamlines through the rig")


def _section(ctx, frac: float):
    box, heel, pivot, U = _setup(ctx)
    ey, ez = heel_basis(heel)
    H = box[5]
    xm, ym = 0.5 * (box[0] + box[3]), 0.5 * (box[1] + box[4])
    origin = heeled((xm, ym, frac * H), heel, pivot)
    ctx.new_view()
    sl = ctx.slice(origin, ez)
    rel = ctx.calc(sl, "Urel", f"mag(U)/{U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.0, 1.8), "speed / U")
    w = box[3] - box[0]
    flow = np.asarray(ctx.d.get("dragDir") or [1, 0, 0], float)
    if "Uair" in ctx.d:
        flow = np.asarray(ctx.d["Uair"], float) / np.linalg.norm(ctx.d["Uair"])
    across = np.cross(ez, flow)
    up = origin - 0.9 * w * flow
    st = ctx.streamlines_line(up - 0.6 * w * across, up + 0.6 * w * across, n=50, length=4 * w, source=sl, surface=True)
    ctx.solid(ctx.show(st), (0.08, 0.08, 0.08), line_width=1.0)
    ctx.camera(origin, ez, ey, 0.5 * 1.5 * w * 900 / 1600)
    _title(ctx, f"section at {frac * 100:.0f} % of the rig height")


def section_mid(ctx):
    _section(ctx, 0.45)


def section_upper(ctx):
    _section(ctx, 0.75)


VIEWS = {
    "sail_cp_leeward": sail_cp_leeward,
    "sail_cp_windward": sail_cp_windward,
    "streamlines": streamlines,
    "section_mid": section_mid,
    "section_upper": section_upper,
}
