# appendage3d: keel fin, bulb and rudder

Steady 3D RANS of the appendages alone: drag D_h, side force S_h, vertical
force F_z,h and the roll and yaw moments M_h,dyn and N_h, for a given boat
speed V_b, leeway β_Y, heel φ and rudder angle δ_R, with a per-component
breakdown (fin, bulb, rudder). Symbols:
[docs/nomenclature.md](../../docs/nomenclature.md).

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
* Leeway β_Y rotates the inflow, so the forces come out along and across
  the course; heel φ rotates the geometry about the fin root.

## Geometry

* `geometry: parametric` (default): fin (planform, section, sweep), bulb
  (ellipse nose + parabolic tail, `bulb_mass_kg` reported for lead), rudder
  (with deflection). Defaults are a generic modern IOM: 85/75 mm chord fin,
  360 mm span, 330 mm × 37.5 mm bulb (≈ 2.4 kg).
* `geometry: stl` with `stl_files: [appendages/fin.stl, ...]` from Fusion 360
  (see [docs/geometry.md](../../docs/geometry.md)).

## Outputs

* `drag_N` (D_h) and `side_N` (S_h, + to port, which is windward on port
  tack), both along and across the course;
* `vertical_N` (F_z,h);
* `drag_friction_N` and `drag_pressure_N`, the two parts of D_h;
* `side_drag_ratio`;
* `roll_moment_Nm` (M_h,dyn, + heels to starboard) and `yaw_moment_Nm`
  (N_h), about the bow at the waterline;
* `x_clr`, the x position of the centre of lateral resistance (ORC's z_CLR
  is its depth);
* `Cd`/`Cs` (C_D, C_S) on the fin's lateral area;
* per-component `drag_<part>_N` and `side_<part>_N`, and y+.

## Mesh levels

Background cell = mean fin chord. `xcoarse` (~0.25M cells, smoke tests),
`coarse`, `medium` (~3M, the working level), `fine`. Run with `np: 8` or more.

## Research

[bulb-design.md](../../docs/research/bulb-design.md):
keel bulb designs (America's Cup, grand prix, IOM and other model yachts),
what each optimises, low-Reynolds-number body drag, and what that means for
simulating IOM bulbs here.

## Studies

`smoke`: xcoarse, 30 iterations, 3° leeway, 10° heel.

Suggested first real study: leeway sweep 0-6° at 1 m/s, upright and at 15°
heel, on `medium`, then a mesh check at 4° on `coarse/medium/fine`.
