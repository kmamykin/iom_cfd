"""windage views (ParaView, rendered by `iomcfd viz`).

hull_cp_windward / _leeward  Cp on the topsides seen from the side the wind
                             comes from and from the other side
section                      speed/U on a horizontal section at half the
                             topsides' height, with in-plane streamlines: the
                             separation off the deck edge and the wake

The case is in the earth frame (the hull heeled, trimmed and sunk, the
water plane z = 0); cameras look along the wind's normal.
"""

from __future__ import annotations

import math

import numpy as np

DEFAULT_VIEWS = ["hull_cp_windward", "hull_cp_leeward", "section"]
ANIMATE_VIEWS = ["hull_cp_windward", "section"]
ANIMATE_PARAMS = ["awa", "heel", "aws", "mesh"]
TIME_VIEWS: list[str] = []


def _box(ctx):
    d = ctx.d
    lo, hi = np.array(d["topsidesMin"]), np.array(d["topsidesMax"])
    return lo, hi, 0.5 * (lo + hi)


def _title(ctx, what: str):
    p, m = ctx.p, ctx.m
    parts = [f"AWA {p['awa']} deg", f"AWS {p['aws']} m/s", f"heel {p['heel']} deg", f"mesh {p['mesh']}"]
    if "drag_N" in m:
        parts.append(f"drag {m['drag_N']:.4f} N  lift {m['lift_N']:.4f} N  cd {m['cd']:.3f}")
    ctx.title(f"{what}\n" + "   ".join(parts))


def _hull_cp(ctx, side: float, label: str):
    lo, hi, c = _box(ctx)
    a = math.radians(float(ctx.p["awa"]))
    towards_wind = np.array([-math.cos(a), math.sin(a), 0.0])  # where the wind comes from
    ctx.new_view()
    s = ctx.surface(r"patch/hull", arrays=["p"])
    cp = ctx.calc(s, "Cp", f"p/{0.5 * ctx.U ** 2}")
    ctx.color(ctx.show(cp), "Cp", "Cool to Warm", (-1.5, 1.0), "Cp")
    half = 0.55 * max((hi[0] - lo[0]) * 900 / 1600, hi[2] - lo[2])
    ctx.camera(c, side * towards_wind + np.array([0.0, 0.0, 0.35]), np.array([0.0, 0.0, 1.0]), half)
    _title(ctx, f"pressure coefficient on the topsides, seen from {label}")


def hull_cp_windward(ctx):
    _hull_cp(ctx, +1.0, "windward")


def hull_cp_leeward(ctx):
    _hull_cp(ctx, -1.0, "leeward")


def section(ctx):
    lo, hi, c = _box(ctx)
    z = 0.5 * hi[2]
    ctx.new_view()
    sl = ctx.slice((c[0], c[1], z), (0, 0, 1), source=ctx.reader(arrays=["U"]))
    rel = ctx.calc(sl, "Urel", f"mag(U)/{ctx.U}")
    ctx.color(ctx.show(rel), "Urel", "Turbo", (0.0, 1.4), "speed / U")
    L = hi[0] - lo[0]
    ctx.camera_2d(lo[0] - 0.4 * L, hi[0] + 0.6 * L, c[1], normal_axis="z", z=z)
    _title(ctx, f"speed on a horizontal section {z * 1e3:.0f} mm above the water")
