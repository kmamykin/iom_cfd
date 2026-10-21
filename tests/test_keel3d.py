"""keel3d: keel sizing from the IOM rules and the equal-side-force comparison."""

import math

import numpy as np
import pandas as pd
import pytest

from iomcfd.project import load_project


@pytest.fixture(scope="module")
def project():
    return load_project("keel3d")


def test_keel_sized_by_the_rules(project):
    d = project.derive(dict(project.defaults))
    assert d["bulb_mass_kg"] == pytest.approx(2.38)
    assert d["bulb_z_axis"] - d["bulb_diameter"] / 2 == pytest.approx(-0.42)  # bulb bottom at the draft limit
    assert d["fin_z_root"] - d["fin_span"] == pytest.approx(d["bulb_z_axis"] + d["bulb_diameter"] / 2)
    assert d["displacement_kg"] == pytest.approx(4.0, abs=0.05)
    assert d["fin_root_thickness"] <= 0.020


def test_equal_area_across_tapers(project):
    areas = {t: project.derive({**project.defaults, "fin_taper": t})["fin_area_m2"] for t in (1.0, 0.6, 0.4)}
    assert max(areas.values()) == pytest.approx(min(areas.values()))


def test_rule_checks(project):
    with pytest.raises(ValueError, match="E.4.1"):
        project.derive({**project.defaults, "fin_mean_chord": 0.25, "fin_taper": 0.4})  # 25 mm thick root
    with pytest.raises(ValueError, match="E.4.1"):
        project.derive({**project.defaults, "bulb_section": "naca0050"})  # 62 mm bulb


def _sweep(taper, side_slope, k, d0=0.6):
    rows = []
    for b in (0, 2, 4, 6, 8):
        F = side_slope * b
        rows.append({"status": "ok", "fin_taper": taper, "leeway": b, "side_N": F, "drag_N": d0 + k * F**2,
                     "speed": 1.0, "dynamicPressure": 499.6, "draft": 0.42})
    return rows


def test_compare_at_equal_force(project):
    # taper 0.6: same lift slope, less induced drag; taper 0.4: more lift per degree, same drag polar
    df = pd.DataFrame(_sweep(1.0, 1.5, 0.010) + _sweep(0.6, 1.5, 0.009) + _sweep(0.4, 1.6, 0.010))
    t = project.compare_at_equal_force(df, {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4, 6]}})
    w = t[t["load"] == "working"].set_index("fin_taper")
    assert w.loc[1.0, "side_N"] == pytest.approx(6.0)
    assert w.loc[1.0, "leeway"] == pytest.approx(4.0)
    assert w.loc[0.4, "leeway"] == pytest.approx(6.0 / 1.6)
    assert w.loc[0.6, "drag_N"] == pytest.approx(0.6 + 0.009 * 36, rel=1e-3)
    assert w.loc[0.4, "drag_N"] == pytest.approx(0.6 + 0.010 * 36, rel=1e-9)  # between computed points
    # 0.6 has the least drag, 0.4 the least leeway; drag at 0 deg is equal
    drag = 50 * 0.036 / 1.354  # % of race time: half the race upwind
    leeway = 50 * math.tan(math.radians(42)) * math.radians(0.25)
    assert w.loc[0.6, "loss_x1_pct"] == 0.0
    assert w.loc[1.0, "loss_x1_pct"] == pytest.approx(drag, rel=1e-6)
    assert w.loc[0.4, "loss_x1_pct"] == pytest.approx(drag - leeway, rel=1e-6)
    assert w.loc[1.0, "loss_x2_pct"] == pytest.approx(drag / 2, rel=1e-6)
    fits = project.polar_fits(df).set_index("fin_taper")
    assert fits.loc[0.6, "k_per_N"] == pytest.approx(0.009)
    assert fits.loc[1.0, "side_per_deg_N"] == pytest.approx(1.5)


@pytest.mark.parametrize("taper,leeway,heel", [(1.0, 0, 0), (0.4, 4, 0), (0.4, 4, 15)])
def test_fin_wake_box_holds_the_trailing_edge(project, taper, leeway, heel):
    import numpy as np

    from iomcfd.geometry import stl

    p = {**project.defaults, "fin_taper": taper, "leeway": leeway, "heel": heel}
    d = project.derive(p)
    levels = project.render.__globals__["MESH_LEVELS"]
    b = project._fin_wake_box(p, d, levels[p["mesh"]])
    o, span, e1, e3 = (np.array(b[k]) for k in ("finWakeOrigin", "finWakeSpan", "finWakeE1", "finWakeE3"))
    e2 = np.cross(e3, e1)
    rot = stl.rotation("x", heel)
    for chord, z in ((d["fin_root_chord"], d["fin_z_root"]), (d["fin_tip_chord"], d["fin_z_root"] - d["fin_span"])):
        q = rot @ np.array([float(p["fin_x"]) + 0.75 * chord, 0.0, z]) - o
        local = np.array([q @ e1, q @ e2, q @ e3]) / span
        assert np.all(local > 0) and np.all(local < 1)
        assert local[0] == pytest.approx(0.25)  # 0.1 chord ahead, 0.3 behind
        assert local[1] == pytest.approx(0.5)  # symmetric about the centre plane
    assert b["finWakeLevel"] == levels[p["mesh"]]["fin"][0]
    assert project._fin_wake_box({**p, "fin_wake": 0}, d, levels[p["mesh"]])["finWakeLevel"] == 0


def test_mesh_shift_moves_the_background_grid(project, tmp_path):
    base = project.prepare_case(tmp_path / "a", {**project.defaults, "mesh": "medium"})
    moved = project.prepare_case(tmp_path / "b", {**project.defaults, "mesh": "medium", "mesh_shift": 0.5})
    cell = 0.1 / 2**7  # finest fin cell on medium (feature level 7)
    assert moved["xMin"] - base["xMin"] == pytest.approx(0.5 * cell)
    assert moved["yMin"] - base["yMin"] == pytest.approx(0.5 * cell)
    assert moved["zMax"] == base["zMax"] == 0.0  # the waterline stays the top
    for axis, (dx, dy) in (("x", (0.5, 0.0)), ("y", (0.0, 0.5))):
        one = project.prepare_case(tmp_path / axis, {**project.defaults, "mesh": "medium", "mesh_shift": 0.5,
                                                     "mesh_shift_only": axis})
        assert one["xMin"] - base["xMin"] == pytest.approx(dx * cell, abs=1e-12)
        assert one["yMin"] - base["yMin"] == pytest.approx(dy * cell, abs=1e-12)
    with pytest.raises(ValueError, match="mesh_shift_only"):
        project.prepare_case(tmp_path / "z", {**project.defaults, "mesh_shift_only": "z"})


def test_shift_axes_kept_apart_and_out_of_old_hashes(project):
    from iomcfd.study import params_hash

    grid_shift = type(project).report.__globals__["_grid_shift"]  # project modules load outside sys.modules
    p = dict(project.defaults)
    old = {k: v for k, v in p.items() if k != "mesh_shift_only"}  # a case from before the parameter
    assert params_hash(p) == params_hash(old) != params_hash({**p, "mesh_shift_only": "x"})
    df = pd.DataFrame({"mesh_shift": [0.0, 0.5, 0.5, 0.5], "mesh_shift_only": [np.nan, np.nan, "x", "y"]})
    assert grid_shift(df) == ["0", "0.5 xy", "0.5 x", "0.5 y"]
    assert grid_shift(df.drop(columns="mesh_shift_only")) == ["0", "0.5 xy", "0.5 xy", "0.5 xy"]


def test_grid_aligned_with_the_boat_at_any_leeway(project, tmp_path):
    for i, (leeway, taper) in enumerate(((0, 1.0), (4, 1.0), (6, 0.4))):
        d = project.prepare_case(tmp_path / str(i), {**project.defaults, "leeway": leeway, "fin_taper": taper})
        for k in ("xMin", "yMin", "zMin", "xMax", "yMax"):
            assert d[k] / d["baseCell"] == pytest.approx(round(d[k] / d["baseCell"]), abs=1e-9), k
        assert d["zMax"] == 0.0


def test_trailing_edge_feature_lines(project, tmp_path):
    project.prepare_case(tmp_path / "c", {**project.defaults, "fin_taper": 0.4})
    lines = (tmp_path / "c" / "constant" / "triSurface" / "trailingEdge.obj").read_text().splitlines()
    v = [list(map(float, ln.split()[1:])) for ln in lines if ln.startswith("v ")]
    assert len(v) == 8 and sum(ln.startswith("l ") for ln in lines) == 6
    assert {round(p[1] * 1e6) for p in v} == {1, -1}  # 1 um either side of the centre plane
    assert "trailingEdge.obj" in (tmp_path / "c" / "system" / "snappyHexMeshDict").read_text()


def test_grid_shift_cases_kept_apart(project):
    # a shifted-grid point at 4 deg must not join the unshifted leeway curve
    rows = _sweep(1.0, 1.5, 0.010) + _sweep(0.4, 1.5, 0.009)
    for r in rows:
        r["mesh_shift"] = 0.0
    rows.append({**_sweep(1.0, 1.5, 0.010)[2], "mesh_shift": 0.5, "side_N": 5.0, "drag_N": 2.0})
    t = project.compare_at_equal_force(pd.DataFrame(rows), {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4, 6]}})
    w = t[(t["load"] == "working") & (t["mesh_shift"] == 0.0)].set_index("fin_taper")
    assert w.loc[1.0, "side_N"] == pytest.approx(6.0) and w.loc[1.0, "drag_N"] == pytest.approx(0.96)
    assert t[t["mesh_shift"] == 0.5].empty  # a single point is not a sweep


def _total_forces(case, drag, side):
    d = case / "postProcessing" / "forces_total" / "0"
    d.mkdir(parents=True)
    rows = "\n".join(f"{i + 1}\t{dr:.8g}\t{si:.8g}\t0\t0\t0\t0\t0\t0\t0" for i, (dr, si) in enumerate(zip(drag, side)))
    (d / "force.dat").write_text("# Time total_x total_y total_z pressure_x pressure_y pressure_z "
                                 "viscous_x viscous_y viscous_z\n" + rows + "\n")


def test_progress_reports_forces_and_their_drift(project, tmp_path):
    import numpy as np

    p = {**project.defaults}
    d = {"dragDir": [1.0, 0.0, 0.0], "sideDir": [0.0, 1.0, 0.0], "convWindow": 100}
    n = np.arange(400)
    drag, side = 0.93 + 0.1 * np.exp(-n / 60), 6.7 - 0.5 * np.exp(-n / 60)
    _total_forces(tmp_path, drag, side)
    prog = project.progress(tmp_path, p, d)
    assert prog["D_h"] == pytest.approx(drag[-1]) and prog["S_h"] == pytest.approx(side[-1])
    w = slice(-100, None), slice(-200, -100)
    assert prog["D_h_change"] == pytest.approx(abs(drag[w[0]].mean() - drag[w[1]].mean()) / drag[-1])
    assert prog["S_h_change"] == pytest.approx(abs(side[w[0]].mean() - side[w[1]].mean()) / side[-1])
    last = drag[-100:]
    assert prog["D_h_drift"] == pytest.approx(abs(last[50:].mean() - last[:50].mean()) / drag[-1])
    assert prog["conv_tol"] == p["conv_tol"]
    worst = max(prog[f"{k}_{m}"] for k in ("D_h", "S_h") for m in ("change", "drift"))
    assert project.converged(tmp_path, p, d) == (worst < p["conv_tol"])
    assert project.progress(tmp_path / "none", p, d) == {}


def test_not_converged_while_climbing_after_the_transient(project, tmp_path):
    # taper-mesh run 20261019-213145, 0.8 at 0 deg on fine: the start-up
    # transient's window had the same mean as the next, still-climbing window
    p = {**project.defaults}
    d = {"dragDir": [1.0, 0.0, 0.0], "sideDir": [0.0, 1.0, 0.0], "convWindow": 200}
    n = np.arange(200)
    drag = np.concatenate([0.68 + 0.2 * np.sin(2 * np.pi * n / 50), 0.66 + 0.04 * n / 199])
    _total_forces(tmp_path, drag, 0 * drag)
    prog = project.progress(tmp_path, p, d)
    assert prog["D_h_change"] < p["conv_tol"] < prog["D_h_drift"]
    assert not project.converged(tmp_path, p, d)


def test_flatter_bulb_same_lead_lower_and_longer_fin(project):
    base = project.derive(dict(project.defaults))
    for kw in ({"bulb_aspect": 1.5}, {"bulb_aspect": 1.5, "bulb_bottom": 6.0}, {"bulb_aspect": 2.0, "bulb_top": 6.0}):
        d = project.derive({**project.defaults, **kw})
        assert d["bulb_volume_m3"] == base["bulb_volume_m3"] and d["bulb_length"] == base["bulb_length"]
        assert d["bulb_z_axis"] - d["bulb_height"] / 2 == pytest.approx(-0.42)  # bottom at the draft
        assert d["bulb_cg_above_draft"] < base["bulb_cg_above_draft"]
        # the fin reaches down to the lower top of the bulb, and on to its axis
        assert d["fin_span"] - base["fin_span"] == pytest.approx(base["bulb_height"] - d["bulb_height"], abs=1e-9)
        assert d["fin_tip_extension"] == pytest.approx(d["bulb_height"] / 2)
    # E.4.1 limits the width above the lowest 60 mm, not the height
    tall = {**project.defaults, "bulb_section": "naca0015", "bulb_aspect": 0.4}
    assert project.derive(tall)["bulb_height"] > 0.060  # 66 mm tall, but under 20 mm wide above 60 mm
    with pytest.raises(ValueError, match="E.4.1"):
        project.derive({**project.defaults, "bulb_section": "naca0040", "bulb_aspect": 0.7})


def test_canted_bulb_stays_at_the_draft(project):
    p = {**project.defaults, "bulb_cant": 3.0}
    d = project.derive(p)
    bulb = project.surfaces(p)[2]
    assert bulb.vertices[:, 2].min() == pytest.approx(-0.42, abs=2e-4)  # the tail, now the lowest point
    assert bulb.centroid()[0] == pytest.approx(d["bulb_x_cg"], abs=1e-4)
    assert d["bulb_cg_above_draft"] > project.derive(dict(project.defaults))["bulb_cg_above_draft"]


def test_fin_alone(project, tmp_path):
    p = {**project.defaults, "bulb": False}
    assert [s.name for s in project.surfaces(p)] == ["hull", "fin"]
    assert project.derive(p)["fin_span"] == project.derive(dict(project.defaults))["fin_span"]
    d = project.prepare_case(tmp_path / "f", p)
    assert d["bulb_wetted_area_m2"] == 0.0
    assert "boat_bulb" not in (tmp_path / "f" / "system" / "include" / "forceFunctions").read_text()


def test_downwind_drag_from_the_upright_case(project):
    rows = []
    for heel, extra in ((0, 0.0), (25, 0.05)):
        for r in _sweep(1.0, 1.5, 0.010) + _sweep(0.6, 1.5, 0.009, d0=0.62):
            rows.append({**r, "heel": heel, "drag_N": r["drag_N"] + extra})
    t = project.compare_at_equal_force(pd.DataFrame(rows), {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4]}})
    heeled = t[t["heel"] == 25].set_index(["fin_taper", "load"])
    assert heeled.loc[(1.0, "working"), "drag0_N"] == pytest.approx(0.6)  # upright, not 0.65
    assert heeled.loc[(0.6, "working"), "drag0_N"] == pytest.approx(0.62)


def test_effective_draft(project):
    df = pd.DataFrame(_sweep(1.0, 1.5, 0.010))
    fits = project.polar_fits(df).set_index("fin_taper")
    assert fits.loc[1.0, "T_eff_m"] == pytest.approx(1 / math.sqrt(math.pi * 499.6 * 0.010))
    df.loc[df["leeway"] == 8, "drag_N"] += 1.0  # a separated point
    assert project.polar_fits(df, max_leeway=6).loc[0, "k_per_N"] == pytest.approx(0.010)


def _polars(chords=(0.08, 0.10)):
    rows = []
    for c in chords:
        for a in range(0, 8):
            cl = 0.1 * a
            rows.append({"chord": c, "aoa": a, "Cl": cl, "Cd": 0.02 + 0.05 * cl, "turbulence": "kOmegaSST", "Tu": 0.5})
            # transition model: 10 % more angle for the same lift, less drag at zero lift, more so on the longer
            # chord (linear in C_l, so that interpolation is exact)
            rows.append({"chord": c, "aoa": a, "Cl": cl / 1.1, "Cd": 0.012 - 0.02 * (c - 0.08) + 0.08 * (cl / 1.1),
                         "turbulence": "kOmegaSSTLM", "Tu": 0.1})
    return pd.DataFrame(rows)


def test_transition_delta_at_equal_section_lift(project):
    g = type(project).report.__globals__
    delta = g["transition_delta"](_polars(), 0.1)
    dcd, da = delta([0.08, 0.10, 0.09], [0.3, 0.3, -0.3])
    assert dcd[0] == pytest.approx((0.012 + 0.08 * 0.3) - (0.02 + 0.05 * 0.3))
    assert dcd[1] == pytest.approx(dcd[0] - 0.02 * 0.02)
    assert dcd[2] == pytest.approx(0.5 * (dcd[0] + dcd[1]))  # linear in chord; |C_l|
    assert np.allclose(da, 0.3 * 10 * (1.1 - 1.0))  # 3.3 deg against 3.0 deg
    assert np.isnan(delta(0.09, 0.69)[0])  # beyond the transition polar's highest C_l (0.636)


def test_transition_correction_strip_by_strip(project):
    g = type(project).report.__globals__
    delta = g["transition_delta"](_polars(), 0.1)
    span = pd.DataFrame({"eta": [0.25, 0.75], "chord_m": [0.10, 0.08], "side_N_per_m": [20.0, 10.0], "cl": [0.3, 0.3]})
    d = {"fin_span": 0.3, "dynamicPressure": 500.0}
    c = g["transition_correction"](span, d, delta)
    dcd, da = delta(span["chord_m"], span["cl"])
    assert c["dD_N"] == pytest.approx(float(np.sum(dcd * 500.0 * span["chord_m"] * 0.15)))
    assert c["dbeta_deg"] == pytest.approx(0.3) and c["strips_out"] == 0
    zero = g["transition_correction"](span.assign(side_N_per_m=[1e-4, -1e-4], cl=[0.0, 0.0]), d, delta)
    assert zero["dbeta_deg"] == 0.0 and zero["dD_N"] < 0  # downwind: laminar friction only


def test_compare_at_given_loads(project):
    df = pd.DataFrame(_sweep(1.0, 1.5, 0.010) + _sweep(0.6, 1.5, 0.009, d0=0.62))
    t0 = project.compare_at_equal_force(df, {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4]}})
    later = df.assign(leeway=df["leeway"] + 0.5)  # e.g. a leeway correction
    t = project.compare_at_equal_force(later, {"compare_at": {"fin_taper": 1.0, "leeway": [2, 4]}}, loads=t0)
    assert np.allclose(t["side_N"], t0["side_N"])
    assert np.allclose(t["leeway"], t0["leeway"] + 0.5)
