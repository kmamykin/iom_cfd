"""Reversed flow on a keel3d fin: where the streamwise velocity is below -1 %
of U, per 10 % band of the span, on the suction (port, y > 0) side.

Run on a case with fields (`iomcfd gcp fetch ... --fields`), in the viz image:

    docker run --rm -v "$PWD":/work -w /work --entrypoint pvpython iom-cfd-viz:latest \\
        tools/keel3d_separation.py runs/<study>/<run id>/<case> ...

Prints, per band, the chordwise extent (x/c, 2nd to 98th percentile of the
reversed cells' centres; x/c > 0.02 leaves out the flow running forward round
the nose from the stagnation point) and the number of cells.
"""
import json
import sys
from pathlib import Path

import numpy as np
import paraview.simple as pv
from paraview import servermanager as sm
from vtk.util.numpy_support import vtk_to_numpy

for case in map(Path, sys.argv[1:]):
    pj = json.loads((case / "params.json").read_text())
    p, d = pj["params"], pj["derived"]
    foam = case / "case.foam"
    foam.touch()
    times = sorted(float(t.name) for t in case.iterdir() if t.name.replace(".", "").isdigit() and float(t.name) > 0)
    r = pv.OpenFOAMReader(FileName=str(foam))
    r.MeshRegions = ["internalMesh"]
    r.CellArrays = ["U"]
    r.UpdatePipeline(times[-1])
    u = np.asarray(d["dragDir"], float)
    calc = pv.Calculator(Input=r, AttributeType="Cell Data", ResultArrayName="ux",
                         Function=f"(U_X*{u[0]} + U_Y*{u[1]} + U_Z*{u[2]})/{float(p['speed'])}")
    th = pv.Threshold(Input=calc, Scalars=["CELLS", "ux"], LowerThreshold=-1e9, UpperThreshold=-0.01)
    cen = pv.CellCenters(Input=th)
    cen.UpdatePipeline(times[-1])
    data = sm.Fetch(pv.MergeBlocks(Input=cen))
    xyz = vtk_to_numpy(data.GetPoints().GetData()) if data.GetNumberOfPoints() else np.zeros((0, 3))
    zr, span, cr, ct = d["fin_z_root"], d["fin_span"], d["fin_root_chord"], d["fin_tip_chord"]
    eta = (zr - xyz[:, 2]) / span
    chord = cr + (ct - cr) * np.clip(eta, 0, 1)
    xq = float(p["fin_x"]) + np.tan(np.radians(float(p["fin_sweep"]))) * np.clip(eta, 0, 1) * span
    xc = (xyz[:, 0] - (xq - 0.25 * chord)) / chord
    suction = (xyz[:, 1] > 0) & (xc > 0.02) & (xc < 1.0) & (np.abs(xyz[:, 1]) < 0.5 * chord)
    print(f"== {case.name} (leeway {p['leeway']} deg): reversed flow on the suction side, x/c per span band")
    for lo in np.arange(0.0, 1.0, 0.1):
        m = suction & (eta >= lo) & (eta < lo + 0.1)
        ext = f"x/c {np.percentile(xc[m], 2):.3f} to {np.percentile(xc[m], 98):.3f}" if m.sum() else "none"
        print(f"  eta {lo:.1f}-{lo + 0.1:.1f}: {ext}, {m.sum()} cells")
    pv.Delete(r)
