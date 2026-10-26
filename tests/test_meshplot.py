import json
import struct

import numpy as np
import pytest

from iomcfd import meshplot, polymesh
from iomcfd.geometry import cmesh, foils

HDR = (
    "FoamFile\n{{\n    version 2.0;\n    format {fmt};\n    arch \"LSB;label=32;scalar=64\";\n"
    "    class {cls};\n    note \"nPoints:8 nCells:1\";\n    object {obj};\n}}\n"
)


def _binary_list(arr: np.ndarray, dtype: str) -> bytes:
    return f"{len(arr)}\n(".encode() + np.asarray(arr, dtype=dtype).tobytes() + b")\n"


def _write_binary_cube(d):
    """One unit hex cell as a binary polyMesh (faceCompactList)."""
    d.mkdir(parents=True)
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [3, 7, 6, 2], [0, 4, 7, 3], [1, 2, 6, 5]]
    offsets = np.concatenate([[0], np.cumsum([len(f) for f in faces])])
    (d / "points").write_bytes(HDR.format(fmt="binary", cls="vectorField", obj="points").encode()
                               + f"{len(pts)}\n(".encode() + pts.tobytes() + b")\n")
    (d / "faces").write_bytes(HDR.format(fmt="binary", cls="faceCompactList", obj="faces").encode()
                              + _binary_list(offsets, "<i4") + _binary_list(np.concatenate(faces), "<i4"))
    (d / "owner").write_bytes(HDR.format(fmt="binary", cls="labelList", obj="owner").encode()
                              + _binary_list(np.zeros(6), "<i4"))
    (d / "boundary").write_text(HDR.format(fmt="ascii", cls="polyBoundaryMesh", obj="boundary")
                                + "1\n(\n    walls\n    {\n        type wall;\n        nFaces 6;\n        startFace 0;\n    }\n)\n")


def test_binary_reader_and_slice(tmp_path):
    _write_binary_cube(tmp_path / "polyMesh")
    m = polymesh.read(tmp_path / "polyMesh")
    assert m.points.shape == (8, 3) and m.n_faces == 6 and m.n_cells == 1
    assert m.patches["walls"] == (0, 6, "wall")
    segs = polymesh.slice_segments(m, (0.5, 0.5, 0.25), (0, 0, 1))
    assert len(segs) == 4  # the four side faces cut by z = 0.25
    assert np.allclose(segs[:, :, 2], 0.25)
    # total cut length = perimeter of the unit square
    assert np.linalg.norm(segs[:, 1] - segs[:, 0], axis=1).sum() == pytest.approx(4.0)


def test_ascii_cmesh_roundtrip_and_slice(tmp_path):
    spec = cmesh.CMeshSpec(chord=1.0, span=0.1, n_surface=40, n_wake=20, n_normal=24, first_cell=1e-3)
    info = cmesh.build(foils.naca4("0012"), spec, tmp_path / "constant" / "polyMesh")
    m = polymesh.read(tmp_path / "constant" / "polyMesh")
    assert m.n_cells == info.n_cells and m.n_faces == info.n_faces
    fb = m.patches["frontAndBack"][1]
    segs = polymesh.slice_segments(m, (0, 0, 0.05), (0, 0, 1))
    assert len(segs) == m.n_faces - fb  # every non-empty face is cut once
    wall = polymesh.slice_segments(m, (0, 0, 0.05), (0, 0, 1), faces=m.patch_faces("foil"))
    assert len(wall) == m.patches["foil"][1]


def test_boat_view_follows_heel():
    v = meshplot.boat_view("t", "side", 0.0, (0, 0), 1.0, heel=30.0, pivot=(0.0, 0.0, -0.04))
    # a point 1 m down the (heeled) fin centreline projects to z_boat = -1.04
    h = np.radians(30.0)
    p = np.array([[0.2, 0.0 - (-1.0) * np.sin(h) * 1.0, -0.04 - 1.0 * np.cos(h)]])
    assert v.project(p)[0] == pytest.approx([0.2, -1.04])
    assert np.dot(v.normal, [0, np.cos(h), np.sin(h)]) == pytest.approx(1.0)


def test_render_foil_mesh_figure(tmp_path):
    from iomcfd.project import load_project

    proj = load_project("foil2d")
    params = {**proj.defaults, "mesh": "xcoarse"}
    derived = proj.derive(params)
    case = tmp_path / "case"
    proj.prepare_case(case, params)
    (case / "result.json").write_text(json.dumps({"metrics": {"yplus_max": 0.8}}))
    spec = proj.mesh_views(case, params, json.loads((case / "params.json").read_text())["derived"])
    out = meshplot.render(case, spec, tmp_path / "mesh.png", "test")
    assert out.is_file() and out.stat().st_size > 20_000
    assert derived["Reynolds"] > 0


def test_section_figures(tmp_path):
    """sections.png for every section, one sheet per stepped section."""
    from iomcfd.sectionplot import describe, study_sections

    files = study_sections(["naca0009", "stair1:naca0009:x=0.35,d=0.3", "stair10:naca0009", "naca0009"], tmp_path,
                           0.08)
    names = sorted(p.name for p in files)
    assert names == ["section_stair10_naca0009.png", "section_stair1_naca0009_x_0.35_d_0.3.png", "sections.png"]
    assert all(p.stat().st_size > 10_000 for p in files)
    from iomcfd.geometry import foils

    assert describe(foils.load("stair10:naca0009"), 0.08).startswith("10 steps per surface of 0.10 mm")
    assert "KFm4" in describe(foils.load("stair1:naca0009"), 0.08)
    assert describe(foils.load("film:naca0009"), 0.1).startswith("a 0.20 mm film round the nose to x/c 0.50")
