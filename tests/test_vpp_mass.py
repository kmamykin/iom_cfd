"""vpp.mass: budget totals and CG, the IOM rule checks, and the keel items."""

import numpy as np
import pytest

from iomcfd.geometry.keel import keel_geometry
from iomcfd.project import load_project
from iomcfd.vpp.mass import MassBudget, MassItem, check_rules, fill_to_minimum, keel_items


@pytest.fixture(scope="module")
def keel3d():
    return dict(load_project("keel3d").defaults)


def budget():
    return MassBudget.from_list([
        {"name": "hull", "m": 1.0, "cg": [0.5, 0.0, 0.02]},
        {"name": "rig", "mass": 0.3, "x": 0.4, "z": 0.6, "source": "estimate"},
        {"name": "keel", "m": 2.5, "cg": [0.5, 0.0, -0.38]},
    ])


def test_totals_and_cg():
    b = budget()
    assert b.mass == pytest.approx(3.8)
    assert b.cg == pytest.approx([(0.5 + 0.12 + 1.25) / 3.8, 0.0, (0.02 + 0.18 - 0.95) / 3.8])
    assert b.item("rig").source == "estimate"
    rows = b.to_rows()
    assert [r["name"] for r in rows] == ["hull", "rig", "keel", "total"]
    assert rows[-1]["m"] == pytest.approx(3.8) and rows[-1]["z"] == pytest.approx(b.cg[2])


def test_budgets_are_new_copies():
    b = budget()
    lower = b.moved("keel", dz=-0.02)
    assert lower.cg[2] == pytest.approx(b.cg[2] - 0.02 * 2.5 / 3.8)
    assert b.item("keel").cg == (0.5, 0.0, -0.38)  # unchanged
    more = b.with_item(MassItem("radio", 0.1, (0.6, 0.0, 0.03)))
    assert more.mass == pytest.approx(3.9) and b.mass == pytest.approx(3.8)
    assert more.with_item(MassItem("radio", 0.2, (0.6, 0.0, 0.03))).mass == pytest.approx(4.0)  # replaced
    assert more.without("radio").mass == pytest.approx(3.8)
    with pytest.raises(KeyError):
        b.moved("ballast", dz=0.1)


def test_fill_to_minimum():
    b = budget()
    full = fill_to_minimum(b, at=(0.5, 0.0, -0.05))
    assert full.mass == pytest.approx(4.0)
    assert full.item("corrector").m == pytest.approx(0.2)
    assert full.item("corrector").cg == (0.5, 0.0, -0.05)
    assert fill_to_minimum(b).cg == pytest.approx(b.cg)  # default: at the CG
    assert fill_to_minimum(full) is full  # nothing to add


def test_rules_pass_and_fail_at_both_ends():
    def ok(**kw):
        a = {"total_mass": 4.0, "keel_mass": 2.4, "draft": 0.40, **kw}
        return {r.clause: r.ok for r in check_rules(**a)}

    assert ok() == {"C.4.1": True, "C.4.2": True, "C.6.4": True}
    assert ok(draft=0.370)["C.4.1"] and ok(draft=0.420)["C.4.1"]
    assert not ok(draft=0.369)["C.4.1"] and not ok(draft=0.421)["C.4.1"]
    assert ok(total_mass=4.0)["C.4.2"] and ok(total_mass=5.5)["C.4.2"] and not ok(total_mass=3.99)["C.4.2"]
    assert ok(keel_mass=2.2)["C.6.4"] and ok(keel_mass=0.12 + 2.38)["C.6.4"]  # a sum on the limit passes
    assert not ok(keel_mass=2.19)["C.6.4"] and not ok(keel_mass=2.51)["C.6.4"]
    r = {r.clause: r for r in check_rules(4.2, 2.45, 0.38)}
    assert r["C.4.1"].margin == pytest.approx(0.010) and r["C.6.4"].margin == pytest.approx(0.05)
    assert r["C.4.2"].hi is None and r["C.4.2"].margin == pytest.approx(0.2)
    assert check_rules(3.9, 2.4, 0.4)[1].margin == pytest.approx(-0.1)


def test_keel_items_match_keel_geometry(keel3d):
    g = keel_geometry(keel3d)
    items, volumes = keel_items(keel3d)
    fin, bulb = items
    assert bulb.m == pytest.approx(2.38)
    assert bulb.cg == pytest.approx((g["bulb_x_cg"], 0.0, g["bulb_z_cg"]))
    assert fin.m == pytest.approx(0.12)
    assert fin.m + bulb.m == pytest.approx(keel3d["keel_mass"])
    # constant chord: mid exposed span, on the section's centroid (0.42 c for NACA 0007)
    assert fin.cg[2] == pytest.approx(g["fin_z_root"] - g["fin_span"] / 2)
    assert fin.cg[0] == pytest.approx(keel3d["fin_x"] + 0.168 * keel3d["fin_mean_chord"], abs=1e-3)
    assert [v for v, _ in volumes] == pytest.approx([g["fin_volume_m3"], g["bulb_volume_m3"]])
    assert volumes[1][1] == pytest.approx(np.array(bulb.cg))
    rules = {r.clause: r.ok for r in check_rules(4.0, MassBudget(items).mass, keel3d["draft"])}
    assert all(rules.values())
    # a tapered fin carries its weight nearer the root
    tapered = keel_items({**keel3d, "fin_taper": 0.4})[0][0]
    assert tapered.cg[2] > fin.cg[2]
    assert len(keel_items({**keel3d, "bulb": False})[0]) == 1
