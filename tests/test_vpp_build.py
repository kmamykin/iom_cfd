"""The boat builder's protocol (boat.py BuildContext) and keel3d tables."""

import numpy as np
import pytest

from iomcfd import config, physics
from iomcfd.vpp import keel3d, tables
from iomcfd.vpp.boat import BoatSpec, BuildContext, resolve_class
from iomcfd.vpp.components.keel import PolarFit
from test_vpp_boat import _keel3d_csv

FOIL_BOAT = config.home() / "boats" / "canoe-placeholder-foil.yaml"
BOAT = config.home() / "boats" / "canoe-placeholder.yaml"


def _ctx(path=FOIL_BOAT, **overrides) -> BuildContext:
    spec = BoatSpec.load(path, overrides)
    return BuildContext(spec, physics.fresh_water(15.0), physics.air(15.0))


def test_exported_table_fits_like_the_results(tmp_path):
    csv = _keel3d_csv(tmp_path / "results.csv")
    out = keel3d.export(str(csv), {"bulb_section": "naca0011"}, tmp_path / "keel.csv")
    t = tables.read(out)
    assert t.header["params"]["bulb_section"] == "naca0011" and t.header["model"] == "fit"
    assert t.column("X")[0] < 0  # drag against the inflow
    a, b = PolarFit.from_results(csv, {"bulb_section": "naca0011"}), PolarFit.from_table(t)
    for f in ("heels", "D0_friction", "D0_pressure", "k", "S0", "a", "x_clr", "z_clr", "fin_share", "V_ref",
              "length_ref"):
        assert getattr(a, f) == getattr(b, f), f


def test_table_round_trip_is_exact(tmp_path):
    rows = [{"a": 0.1 + 0.2, "b": "x", "c": float("nan")}, {"a": 1e-300, "b": "y", "c": -0.0}]
    t = tables.read(tables.write(tmp_path / "t.csv", {"component": "test", "grid": np.float64(2.5)}, rows))
    assert t.header == {"vpp-table": 1, "component": "test", "grid": 2.5}
    assert t.rows[0]["a"] == 0.1 + 0.2 and t.rows[1]["a"] == 1e-300 and np.isnan(t.rows[0]["c"])


def test_classes_resolve_relative_and_absolute():
    assert resolve_class(".keel.PolarFit") is PolarFit
    assert resolve_class("iomcfd.vpp.components.keel.PolarFit") is PolarFit
    with pytest.raises(ValueError, match="no class"):
        resolve_class(".keel.Nope")


def test_parts_build_on_request_and_controls_override():
    ctx = _ctx(**{"components.rudder.controls": {"angle": {"role": "hold", "default": 1.5}}})
    rudder = ctx.get("rudder")  # builds the hull and the keel it needs first (host, downwash)
    assert list(ctx.parts) == ["hull", "keel", "rudder"]
    (angle,) = rudder.controls
    assert (angle.role, angle.default) == ("hold", 1.5)
    assert rudder.forces.eps > 0  # the keel's downwash
    with pytest.raises(ValueError, match="no control"):
        _ctx(**{"components.rudder.controls": {"flat": "optimise"}}).get("rudder")


def test_a_cycle_is_an_error():
    with pytest.raises(ValueError, match="cycle"):
        _ctx(**{"components.keel.mount.host": "rudder"}).get("keel")


def test_shape_reuse_counts_mass_once():
    ctx = _ctx()
    w, h = ctx.get("windage"), ctx.get("hull")
    assert w.shape is h.shape and not w.owner and w.mass_items() == [] and w.volumes() == []


def test_set_moves_the_rudder():
    a = _ctx().get("rudder")
    b = _ctx(**{"components.rudder.args.span": 0.21}).get("rudder")
    assert b.forces.z == pytest.approx(a.forces.z - 0.005)  # mid-span 5 mm lower
    assert b.volumes()[0][0] == pytest.approx(a.volumes()[0][0] * 0.21 / 0.20)


def test_keel_geometry_must_match_its_table():
    with pytest.raises(ValueError, match="another keel"):
        _ctx(BOAT, **{"components.keel.args.fin.root_chord": 0.11}).get("keel")


def test_keel_shape_reproduces_keel3d_parameters():
    k = _ctx().get("keel").shape
    p = k.params()
    assert (p["fin_mean_chord"], p["fin_taper"]) == (0.09, 0.8)  # from root 0.100, tip 0.080
    assert k.g["fin_span"] == pytest.approx(0.3293, abs=1e-4)
