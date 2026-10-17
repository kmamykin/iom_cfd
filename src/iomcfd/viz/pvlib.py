"""ParaView building blocks for case visualisations (runs inside the viz image).

Project view functions (projects/<name>/viz.py) get a `Ctx` for one case and
use its helpers to build a scene:

    def velocity(ctx):
        sl = ctx.slice(normal=(0, 0, 1), origin=(0, 0, ctx.zmid))
        rel = ctx.calc(sl, "Urel", f"mag(U)/{ctx.U}")
        ctx.color(ctx.show(rel), "Urel", "Turbo", (0, 1.6), "|U| / U")
        ctx.camera_2d(-0.3 * c, 1.5 * c, 0.0)
        ctx.title("velocity")

The renderer saves the image (and, for time series, one frame per time).
Every proxy created through the helpers is deleted after the view, while
the (expensive) readers are kept for the next view of the same case.

Colour ranges are fixed and use normalised quantities (|U|/U, Cp, ...) so
images and animations are comparable across cases.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from paraview import simple as pv

WIDTH, HEIGHT = 1600, 900


class Ctx:
    def __init__(self, case_dir: Path, out_dir: Path, options: dict[str, Any] | None = None):
        self.dir = Path(case_dir)
        self.out = Path(out_dir)
        self.options = options or {}
        info = json.loads((self.dir / "params.json").read_text())
        self.p: dict[str, Any] = info["params"]
        self.d: dict[str, Any] = info["derived"]
        res = self.dir / "result.json"
        self.m: dict[str, Any] = (json.loads(res.read_text()).get("metrics") or {}) if res.is_file() else {}
        self.foam = self.dir / "case.foam"
        self.foam.touch(exist_ok=True)
        self._readers: dict[tuple, Any] = {}
        self._tracked: list[Any] = []
        self.view = None
        self._title = None
        self._probe = pv.OpenFOAMReader(registrationName="probe", FileName=str(self.foam))
        self._probe.UpdatePipelineInformation()
        self.regions_available = list(self._probe.GetProperty("MeshRegions").Available)
        self.arrays_available = list(self._probe.GetProperty("CellArrays").Available)
        tv = self._probe.TimestepValues  # a VectorProperty, a scalar, or None
        try:
            self.times: list[float] = [float(t) for t in tv]
        except TypeError:
            self.times = [float(tv)] if tv is not None else []
        self.times = self.times or [0.0]
        self.time = self.times[-1] if self.times else 0.0
        pv.Delete(self._probe)

    # -- data -------------------------------------------------------------
    def has(self, array: str) -> bool:
        return array in self.arrays_available

    def regions(self, pattern: str) -> list[str]:
        import re

        return [r for r in self.regions_available if re.fullmatch(pattern, r)]

    def reader(self, regions: Iterable[str] = ("internalMesh",), arrays: Iterable[str] | None = None):
        """OpenFOAM reader with cell-to-point data, merged into one dataset."""
        regions = tuple(regions)
        arrays = tuple(a for a in (arrays or self.arrays_available) if a in self.arrays_available)
        key = (regions, arrays)
        if key not in self._readers:
            r = pv.OpenFOAMReader(registrationName=f"r{len(self._readers)}", FileName=str(self.foam))
            r.MeshRegions = list(regions)
            r.CellArrays = list(arrays)
            r.Createcelltopointfiltereddata = 1
            r.UpdatePipelineInformation()
            merged = pv.MergeBlocks(Input=r)
            # keep coincident points separate: the two sides of a baffle (sails)
            # share coordinates but carry different pressures
            if "MergePoints" in merged.ListProperties():
                merged.MergePoints = 0
            merged.UpdatePipeline(self.time)
            self._readers[key] = merged
        return self._readers[key]

    def surface(self, pattern: str, arrays: Iterable[str] | None = None):
        """Merged patches whose region name ('patch/<name>') matches the regex."""
        regs = self.regions(pattern)
        if not regs:
            raise RuntimeError(f"no mesh region matches {pattern!r}; available: {self.regions_available}")
        return self.reader(regs, arrays)

    @property
    def U(self) -> float:
        return float(self.d.get("magUInf") or self.d.get("boatSpeed") or 1.0)

    # -- filters (tracked, deleted after the view) ---------------------------
    def track(self, proxy):
        self._tracked.append(proxy)
        return proxy

    def slice(self, origin, normal, source=None):
        s = self.track(pv.Slice(Input=source or self.reader()))
        s.SliceType = "Plane"
        s.SliceType.Origin = [float(v) for v in origin]
        s.SliceType.Normal = [float(v) for v in normal]
        return s

    def calc(self, source, name: str, expr: str):
        c = self.track(pv.Calculator(Input=source))
        c.ResultArrayName = name
        c.Function = expr
        return c

    def contour(self, source, array: str, values):
        c = self.track(pv.Contour(Input=source))
        c.ContourBy = ["POINTS", array]
        c.Isosurfaces = [float(v) for v in values]
        return c

    def gradient(self, source=None, vorticity=True, q=True):
        g = self.track(pv.Gradient(Input=source or self.reader()))
        g.ScalarArray = ["POINTS", "U"]
        g.ComputeVorticity = int(vorticity)
        g.ComputeQCriterion = int(q)
        return g

    def streamlines_line(self, p1, p2, n: int = 40, length: float = 1.0, source=None, surface: bool = False):
        st = self.track(pv.StreamTracer(Input=source or self.reader(), SeedType="Line"))
        st.Vectors = ["POINTS", "U"]
        st.SeedType.Point1 = [float(v) for v in p1]
        st.SeedType.Point2 = [float(v) for v in p2]
        st.SeedType.Resolution = int(n)
        st.MaximumStreamlineLength = float(length)
        if surface:
            st.SurfaceStreamlines = 1
        return st

    def reflect_y(self, source):
        """Mirror about y = 0 (half-domain runs), keeping the original."""
        r = self.track(pv.AxisAlignedReflect(Input=source))  # ParaView >= 6 name of 'Reflect'
        r.PlaneMode = "Interactive"
        r.ReflectionPlane.Origin = [0.0, 0.0, 0.0]
        r.ReflectionPlane.Normal = [0.0, 1.0, 0.0]
        r.CopyInput = 1
        return r

    # -- display -------------------------------------------------------------
    def new_view(self, width: int = WIDTH, height: int = HEIGHT):
        pv.LoadPalette("WhiteBackground")
        v = self.track(pv.CreateView("RenderView"))
        v.ViewSize = [width, height]
        v.ViewTime = self.time
        v.OrientationAxesVisibility = 0
        v.CameraParallelProjection = 1
        self.view = v
        return v

    def show(self, source, opacity: float = 1.0, representation: str = "Surface"):
        disp = pv.Show(source, self.view)
        disp.Representation = representation
        disp.Opacity = opacity
        return disp

    def solid(self, disp, rgb=(0.25, 0.25, 0.28), line_width: float | None = None):
        disp.ColorArrayName = ["POINTS", ""]
        disp.AmbientColor = disp.DiffuseColor = list(rgb)
        if line_width:
            disp.LineWidth = line_width
        return disp

    def color(self, disp, array: str, preset: str, rng: tuple[float, float], title: str,
              component: str | None = None, bar: bool = True, log: bool = False, assoc: str = "POINTS",
              bar_position: tuple[float, float] = (0.92, 0.12), bar_length: float = 0.72,
              horizontal: bool = False):
        pv.ColorBy(disp, (assoc, array) if component is None else (assoc, array, component))
        lut = pv.GetColorTransferFunction(array)
        if not lut.ApplyPreset(preset, True):
            lut.ApplyPreset("Cool to Warm", True)
        lut.AutomaticRescaleRangeMode = "Never"
        if log:
            lut.UseLogScale = 1
        lut.RescaleTransferFunction(float(rng[0]), float(rng[1]))
        disp.SetScalarBarVisibility(self.view, bar)
        if bar:
            sb = pv.GetScalarBar(lut, self.view)
            sb.Title, sb.ComponentTitle = title, ""
            sb.WindowLocation = "Any Location"
            sb.Orientation = "Horizontal" if horizontal else "Vertical"
            sb.Position = [float(v) for v in bar_position]
            sb.ScalarBarLength = bar_length
            sb.TitleFontSize = sb.LabelFontSize = 16
        return lut

    def camera_2d(self, x0: float, x1: float, yc: float, normal_axis: str = "z", z: float = 0.0):
        """Frame x0..x1 horizontally on an axis-aligned plane, looking along -normal."""
        v = self.view
        cx = 0.5 * (x0 + x1)
        half_h = 0.5 * (x1 - x0) * v.ViewSize[1] / v.ViewSize[0]
        if normal_axis == "z":
            v.CameraFocalPoint, v.CameraPosition, v.CameraViewUp = [cx, yc, z], [cx, yc, z + 10.0], [0, 1, 0]
        elif normal_axis == "y":  # x horizontal, z up, looking from -y (port side seen from starboard: use +y)
            v.CameraFocalPoint, v.CameraPosition, v.CameraViewUp = [cx, z, yc], [cx, z - 10.0, yc], [0, 0, 1]
        v.CameraParallelScale = half_h

    def camera(self, focal, direction, up, half_height: float, parallel: bool = True):
        """Look at `focal` from `direction` (unit vector pointing from focal to the camera)."""
        v = self.view
        d = np.asarray(direction, float)
        d /= np.linalg.norm(d)
        dist = 20.0 * half_height
        v.CameraFocalPoint = [float(x) for x in focal]
        v.CameraPosition = [float(x) for x in np.asarray(focal, float) + dist * d]
        v.CameraViewUp = [float(x) for x in up]
        v.CameraParallelProjection = int(parallel)
        v.CameraParallelScale = float(half_height)
        if not parallel:
            v.CameraViewAngle = 2 * math.degrees(math.atan(half_height / dist))

    def title(self, text: str, size: int = 20):
        t = self.track(pv.Text(Text=text))
        d = pv.Show(t, self.view)
        d.WindowLocation = "Upper Left Corner"
        d.Justification = "Left"
        d.FontSize = size
        d.Color = [0, 0, 0]
        self._title = t
        return t

    def note(self, text: str, size: int = 15, corner: str = "Lower Left Corner"):
        t = self.track(pv.Text(Text=text))
        d = pv.Show(t, self.view)
        d.WindowLocation = corner
        d.Justification = "Left"
        d.FontSize = size
        d.Color = [0.2, 0.2, 0.2]
        return t

    # -- output ----------------------------------------------------------------
    def save(self, path: Path, time: float | None = None):
        if time is not None:
            self.view.ViewTime = time
        path.parent.mkdir(parents=True, exist_ok=True)
        pv.SaveScreenshot(str(path), self.view, ImageResolution=list(self.view.ViewSize), TransparentBackground=0)
        return path

    def end_view(self):
        for p in reversed(self._tracked):
            try:
                pv.Delete(p)
            except Exception:  # noqa: BLE001 - already gone with its consumer
                pass
        self._tracked = []
        self.view = None
