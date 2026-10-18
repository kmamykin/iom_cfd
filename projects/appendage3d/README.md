# appendage3d: keel fin, bulb and rudder

Steady 3D RANS of the appendages alone: drag, side force, heave force and
moments for a given boat speed, leeway, heel and rudder angle, with a
per-component breakdown (fin, bulb, rudder).

**Status: runs end to end on a coarse mesh; not validated.**

## Model

* The canoe body is replaced by a symmetry plane at `z = -hull_depth`
  (mirror image of the appendages; no hull boundary layer, no free surface).
  Use `hull` with `appendages: true` to include hull interaction and waves.
* simpleFoam with kOmegaSST and Spalding wall functions (y+ from ~1 to ~300
  is acceptable), prism layers from snappyHexMesh. Fully turbulent, so friction
  drag is overestimated at fin Reynolds numbers (~1e5); see the foil2d
  validation (about +25 % at small angles). Use foil2d for section choice,
  and this project for 3D effects (tip vortex, induced drag, fin-bulb
  junction, rudder in the keel's downwash).
* Leeway rotates the inflow; heel rotates the geometry about the fin root.

## Geometry

* `geometry: parametric` (default): fin (planform, section, sweep), bulb
  (ellipse nose + parabolic tail, `bulb_mass_kg` reported for lead), rudder
  (with deflection). Defaults are a generic modern IOM: 85/75 mm chord fin,
  360 mm span, 330 mm × 37.5 mm bulb (≈ 2.4 kg).
* `geometry: stl` with `stl_files: [appendages/fin.stl, ...]` from Fusion 360
  (see [docs/geometry.md](../../docs/geometry.md)).

## Outputs

`drag_N`, `side_N` (+ to port), `vertical_N`, `drag_friction_N`,
`drag_pressure_N`, `side_drag_ratio`, `roll_moment_Nm`, `yaw_moment_Nm`
(about the bow at the waterline), `x_clr` (centre of lateral resistance, x),
`Cd`/`Cs` on the fin's lateral area, per-component `drag_<part>_N` and
`side_<part>_N`, y+.

## Mesh levels

Background cell = mean fin chord. `xcoarse` (~0.25M cells, smoke tests),
`coarse`, `medium` (~3M, the working level), `fine`. Run with `np: 8` or more.

## Research

[research.md](research.md): keel bulb designs (America's Cup, grand prix,
IOM and other model yachts), what each optimises, low-Reynolds-number
body drag, and what that means for simulating IOM bulbs here.

## Studies

`smoke`: xcoarse, 30 iterations, 3° leeway, 10° heel.

Suggested first real study: leeway sweep 0-6° at 1 m/s, upright and at 15°
heel, on `medium`, then a mesh check at 4° on `coarse/medium/fine`.
