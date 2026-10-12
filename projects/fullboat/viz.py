"""fullboat views (ParaView, rendered by `iomcfd viz`).

overview         free surface (coloured by elevation), hull, appendages and
                 rig together, seen from forward, to port and above
wave_pattern     as in projects/hull
centre_plane     as in projects/hull
sail_cp_leeward  as in projects/sails (apparent wind speed as reference)
"""

from __future__ import annotations

import importlib.util
import sys

import numpy as np

from iomcfd import config
from iomcfd.viz.geom import heel_basis, heeled

DEFAULT_VIEWS = ["overview", "wave_pattern", "centre_plane", "sail_cp_leeward"]
ANIMATE_VIEWS = ["overview", "wave_pattern"]
ANIMATE_PARAMS = ["speed", "heel", "leeway", "twa", "tws", "main_sheet", "mesh"]
TIME_VIEWS: list[str] = []


def _project_views(name: str):
    key = f"iomcfd_viz_shared.{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, config.projects_dir() / name / "viz.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


def overview(ctx):
    hull = _project_views("hull")
    box, pivot, heel, L, V, rho = hull._setup(ctx)
    rig = ctx.d.get("rigBoxBoat") or [0, 0, 0, 1, 0, 1.7]
    ey, ez = heel_basis(heel)
    e = hull._elev_range(ctx, V)
    ctx.new_view()
    ctx.color(ctx.show(hull._free_surface(ctx)), "elevation", "Cool to Warm", (-e, e), "wave elevation [m]")
    s = ctx.surface(r"patch/(boat.*|main.*|jib.*|mast)", arrays=["p"])
    ctx.solid(ctx.show(s), (0.55, 0.55, 0.6))
    c = heeled((0.5 * (box[0] + box[3]), 0.0, 0.35 * rig[5]), heel, pivot)
    ctx.camera(c, np.array([-0.7, 0, 0]) + 0.7 * ey + 0.45 * ez, (0, 0, 1), 0.65 * rig[5], parallel=False)
    p, m = ctx.p, ctx.m
    txt = (f"speed {p['speed']} m/s   TWS {p['tws']} m/s   TWA {p['twa']} deg   AWA {ctx.d.get('awa_deg', 0):.1f} deg"
           f"   heel {p['heel']} deg   leeway {p['leeway']} deg   mesh {p['mesh']}")
    if "net_Fx_N" in m:
        txt += f"\nnet force x {m['net_Fx_N']:.2f} N, y {m['net_Fy_N']:.2f} N; net roll moment {m['net_Mx_Nm']:.2f} N m"
    ctx.title("whole boat: free surface, hull, appendages and rig\n" + txt)


def wave_pattern(ctx):
    _project_views("hull").wave_pattern(ctx)


def centre_plane(ctx):
    _project_views("hull").centre_plane(ctx)


def sail_cp_leeward(ctx):
    _project_views("sails").sail_cp_leeward(ctx)


VIEWS = {
    "overview": overview,
    "wave_pattern": wave_pattern,
    "centre_plane": centre_plane,
    "sail_cp_leeward": sail_cp_leeward,
}
