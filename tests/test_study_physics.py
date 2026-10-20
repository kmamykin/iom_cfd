import math

import pytest
import yaml

from iomcfd import physics
from iomcfd.study import Study, case_name, coerce_numbers, params_hash

DEFAULTS = {"foil": "naca0009", "aoa": 0.0, "speed": 1.0, "Re": None, "mesh": "medium", "np": 1}


def _study(tmp_path, body: dict) -> Study:
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump({"study": "t", "project": "foil2d", **body}))
    return Study.load(p)


def test_sweep_is_cartesian(tmp_path):
    st = _study(tmp_path, {"sweep": {"foil": ["naca0008", "naca0010"], "aoa": [0, 2, 4]}})
    cases = st.expand(DEFAULTS)
    assert len(cases) == 6
    assert {c.name for c in cases} == {f"aoa{a}_foilnaca00{t}" for a in (0, 2, 4) for t in ("08", "10")}


def test_zip_and_explicit_cases(tmp_path):
    st = _study(tmp_path, {"zip": {"speed": [0.5, 1.0], "aoa": [6, 4]}, "cases": [{"aoa": 10, "mesh": "fine"}]})
    cases = st.expand(DEFAULTS)
    assert [(c.params["speed"], c.params["aoa"]) for c in cases[:2]] == [(0.5, 6), (1.0, 4)]
    assert cases[2].params["mesh"] == "fine" and cases[2].params["aoa"] == 10


def test_unknown_parameter_rejected(tmp_path):
    st = _study(tmp_path, {"sweep": {"aoa_deg": [1, 2]}})
    with pytest.raises(ValueError, match="unknown parameter"):
        st.expand(DEFAULTS)


def test_overrides_pin_parameters(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump({"study": "t", "project": "foil2d", "sweep": {"aoa": [0, 2], "mesh": ["coarse", "fine"]}}))
    st = Study.load(p, overrides={"mesh": "xcoarse"})
    cases = st.expand(DEFAULTS)
    assert len(cases) == 2 and all(c.params["mesh"] == "xcoarse" for c in cases)


def test_lhs_sample(tmp_path):
    st = _study(tmp_path, {"sample": {"method": "lhs", "n": 8, "seed": 3, "ranges": {"aoa": [0.0, 8.0], "speed": [0.5, 1.5]}}})
    cases = st.expand(DEFAULTS)
    assert len(cases) == 8
    aoas = sorted(c.params["aoa"] for c in cases)
    # one sample per stratum
    assert all(i <= a / 1.0 < i + 1 for i, a in enumerate(aoas))


def test_scientific_notation_from_yaml(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("study: t\nproject: foil2d\ndefaults:\n  Re: 1.0e5\n  foil: '0012'\n")
    st = Study.load(p)
    assert st.defaults["Re"] == 1e5 and st.defaults["foil"] == "0012"
    assert coerce_numbers(["6e6", "abc"]) == [6e6, "abc"]


def test_hash_ignores_np():
    a = {"aoa": 2.0, "np": 1}
    assert params_hash(a) == params_hash({**a, "np": 8})
    assert params_hash(a) != params_hash({**a, "aoa": 3.0})


def test_case_name_is_filesystem_safe():
    assert case_name({"aoa": -2.5, "foil": "file:my-section.dat"}) == "aoam2.5_foilmymsection"
    assert case_name({"mesh_shift_only": ""}) == "mesh_shift_onlynone"
    assert len(case_name({f"k{i}": "x" * 20 for i in range(10)})) <= 80


# --- physics -----------------------------------------------------------------------


def test_water_air_properties():
    w = physics.fresh_water(20.0)
    assert w.rho == pytest.approx(998.2, abs=0.3)
    assert w.nu == pytest.approx(1.004e-6, rel=0.01)
    a = physics.air(20.0)
    assert a.rho == pytest.approx(1.204, abs=0.005)
    assert a.nu == pytest.approx(1.51e-5, rel=0.02)


@pytest.mark.parametrize("tu,expected", [(0.1, 1137), (0.5, 880), (1.0, 584), (3.0, 183)])
def test_langtry_menter_correlation(tu, expected):
    assert physics.retheta_t(tu) == pytest.approx(expected, rel=0.01)


def test_turbulence_inflow_consistency():
    t = physics.turbulence_inflow(1.0, 1e-6, 1.0, 10.0)
    assert t.k == pytest.approx(1.5e-4)
    assert t.k / t.omega == pytest.approx(1e-5)


def test_first_cell_height_scales_with_yplus():
    h1 = physics.first_cell_height(1.0, 0.08, 1.14e-6, 1.0)
    h2 = physics.first_cell_height(1.0, 0.08, 1.14e-6, 0.5)
    assert h1 == pytest.approx(2 * h2)
    assert 1e-5 < h1 < 1e-4


def test_grid_convergence_second_order():
    from iomcfd.verification import grid_convergence

    # f(h) = 1 + h^2 sampled at h = 1, 1/2, 1/4 (ratio 2)
    gc = grid_convergence(1 + 0.25**2, 1 + 0.5**2, 2.0, 2.0)
    assert gc.order == pytest.approx(2.0)
    assert gc.f_extrapolated == pytest.approx(1.0)
    assert gc.monotone and gc.gci_fine > 0
    assert grid_convergence(1.0, 1.1, 1.05, 2.0).order is None  # oscillatory


def test_induced_drag_reflection_plane():
    from iomcfd.physics import induced_drag

    # 3 N side force, 1 m/s in water, 0.36 m fin span, e = 0.9
    q = 0.5 * 999.1 * 1.0**2
    assert induced_drag(3.0, q, 0.36) == pytest.approx(9.0 / (2 * math.pi * q * 0.9 * 0.36**2))
    assert induced_drag(3.0, q, 0.36, reflection_plane=False) == pytest.approx(2 * induced_drag(3.0, q, 0.36))


def test_study_report_block(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("study: t\nproject: foil2d\nreport: {fin_span: 0.36, induced_drag: true}\nsweep: {aoa: [0, 2]}\n")
    st = Study.load(p)
    assert st.report == {"fin_span": 0.36, "induced_drag": True}
