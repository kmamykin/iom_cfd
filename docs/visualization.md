# Visualisation (ParaView)

Computing a case is expensive; looking at it should be cheap and
repeatable. So visualisation is a separate layer that only reads finished
cases:

```
iomcfd run   (solver image, once)  ->  runs/<study>/<case>/  (fields, results)
iomcfd viz   (viz image, any time) ->  runs/<study>/<case>/viz/*.png, *.mp4
                                       runs/<study>/viz/*_by_<param>.mp4, index.html
```

Re-render as often as you like: with new views, other colour ranges,
another animation parameter. Nothing in the case is modified, and nothing is
re-solved.

## Quick start

```bash
make viz-image                                     # ParaView 6.2 image (~4.8 GB, once)
uv run iomcfd viz foil2d/validation-naca0009-re1e5 # all cases, default views
open runs/validation-naca0009-re1e5/viz/index.html # gallery: report, animations, every view

uv run iomcfd viz foil2d/fin-profile-selection --views separation --animate speed
uv run iomcfd viz appendage3d/leeway --options '{"q_level": 5}' --only leeway4
uv run iomcfd shell --viz                          # pvpython/pvbatch in the viz image
```

`--only` and `--views` re-render just those; study animations and the
gallery are rebuilt from everything already rendered, so partial updates
stay consistent.

## The image

`docker/Dockerfile.viz`: Ubuntu 24.04, ParaView 6.2.0 from conda-forge
(`linux-64` and `linux-aarch64`, so native on Apple Silicon and on x86 cloud
VMs), software rendering with OSMesa (`libosmesa6`,
`VTK_DEFAULT_OPENGL_WINDOW=vtkOSOpenGLRenderWindow`; no GPU or X server),
ffmpeg for movies, and the iomcfd package. It has no OpenFOAM: ParaView's
OpenFOAM reader reads the case files directly (a `case.foam` marker file is
created in each case).

## What gets rendered

Per case, `runs/<study>/<case>/viz/<view>.png` (1600x900 unless a view needs
another shape) and a manifest `viz.json` (status per view, timings, errors).
Per study, `runs/<study>/viz/`:

* **study animations** `<view>_by_<param>[_<group>].mp4/.gif`: one frame per
  case along the swept parameter (angle of attack, speed, leeway, Tu...),
  one movie per combination of the other swept parameters;
* **time animations** `<case>/viz/<view>_time.mp4` for transient runs with
  field snapshots (`snapshot_interval` in foil2d);
* **index.html**: the report plots, all animations and every view of every
  case with its key results.

Colour ranges are fixed and use normalised quantities (speed / U, Cp,
vorticity x chord / U), so frames and cases are directly comparable.

## Views per project

| Project | Views (default order) | Study animation axis (first that varies) |
|---|---|---|
| foil2d | `velocity` (speed + streamlines), `pressure` (Cp), `separation` (streamwise velocity close-up of the laminar bubble, framed from the case's Cf < 0 region, streamlines through it), `transition` (intermittency, transition model only), `eddy_viscosity` (nut/nu, log) | aoa, Tu, speed, Re, foil, chord, mesh |
| appendage3d | `surface_cp_port`, `surface_cp_starboard`, `vortices` (Q-criterion iso-surface; option `q_level`), `wake_slice` (streamwise vorticity between keel and rudder), `section` (mid-span section, speed + in-plane streamlines) | leeway, speed, heel, rudder_angle, fin_section |
| hull | `wave_pattern` (free surface from above, coloured by elevation; mirrored for half-domain runs), `wave_profile` (low side view; option `exaggerate`), `hull_pressure`, `centre_plane` (speed + free-surface line) | speed, heel, leeway, trim |
| sails | `sail_cp_leeward`, `sail_cp_windward` (each side of the baffle sails), `streamlines` (3D through the rig), `section_mid`, `section_upper` (jib-main slot) | awa, main_sheet, jib_sheet, twist, camber, heel |
| fullboat | `overview` (free surface + hull + appendages + rig), `wave_pattern`, `centre_plane`, `sail_cp_leeward` | speed, heel, leeway, twa |

Views of heeled boats are built in the boat frame: cut planes and cameras
rotate with the heel. Views that need data a case does not have (e.g.
intermittency for a fully turbulent run) are skipped, not failed.

## Choosing views in a study

```yaml
viz:
  views: [velocity, separation]   # default: the project's DEFAULT_VIEWS
  animate: Tu                     # default: the first varied parameter in ANIMATE_PARAMS
  options: {q_level: 5}           # passed to the view functions
```

Command-line `--views`, `--animate`, `--options` override the study.

## Adding a view

Views live next to the project in `projects/<name>/viz.py`. A view is a
function that builds a scene from a `Ctx` (see `src/iomcfd/viz/pvlib.py`);
the renderer saves it, makes time animations, and cleans up:

```python
def tip_vortex_closeup(ctx):
    ctx.new_view()
    g = ctx.gradient(ctx.reader(arrays=["U"]))
    iso = ctx.contour(g, "Q Criterion", [5 * (ctx.U / 0.08) ** 2])
    ctx.color(ctx.show(iso), "U", "Turbo", (0.5, 1.2), "speed", component="Magnitude")
    ctx.camera(focal=(0.5, 0.0, -0.4), direction=(1, 0.5, -0.3), up=(0, 0, 1), half_height=0.1)
    ctx.title("tip vortex close-up")

VIEWS["tip_vortex_closeup"] = tip_vortex_closeup
```

`Ctx` gives the case (`ctx.p` parameters, `ctx.d` derived values, `ctx.m`
results), readers (`ctx.reader`, `ctx.surface("patch/fin")`), filters
(`slice`, `calc`, `contour`, `gradient`, `streamlines_line`, `reflect_y`) and
display helpers (`color`, `solid`, `camera`, `camera_2d`, `title`, `note`).
Anything else from `paraview.simple` works too; wrap new proxies in
`ctx.track(...)` so they are deleted after the view. Raise
`iomcfd.viz.Skip("reason")` when a case lacks the data. Text must not contain
`|` (ParaView draws it as a table separator).

To iterate on one view: `uv run iomcfd viz <study> --only <case> --views <view>`.

## Time animations of transient runs

foil2d with `solver: transient` writes only the final fields by default.
Set `snapshot_interval: 0.05` (in chord flow-throughs) to keep ~20 fields
per flow-through; `iomcfd viz` then renders `velocity_time.mp4` and
`separation_time.mp4` for those cases. Each snapshot costs disk (about 10 MB
for the coarse 2D mesh). `snapshot_interval` does not change the cached
result of a case, so it can be added to existing studies.

## Interactive ParaView

Install ParaView 6.2 on the Mac (paraview.org, macOS arm64 build) and open
`runs/<study>/<case>/case.foam`. To turn something you built in the GUI into
a batch view, use *Tools > Start Trace*, reproduce it, and paste the traced
Python into a view function.

## Cloud results

Rendering needs the final field directory of each case. `iomcfd gcp fetch`
skips fields by default; use `iomcfd gcp fetch <study> --fields` before
`iomcfd viz`. (Rendering inside the cloud task, so that only images come
back, is a possible next step: `make push-viz` already publishes the image.)

## Performance

Rendering is CPU-only (Mesa llvmpipe). A 2D foil case renders its five views
in about 5 s; a ~250k-cell 3D case in ~20-40 s. Cases are rendered in
parallel (`-j`, default half the cores). For multi-million-cell meshes, views
read only the arrays they need and draw slices and surfaces, not volumes.
