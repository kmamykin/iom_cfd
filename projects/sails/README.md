# sails: main, jib and mast in the apparent wind

Steady RANS of rigid sails above a flat, frictionless water surface: drive
force, heeling force, heeling moment and centre of effort for a sail trim
(sheeting, twist, camber), apparent wind angle and heel.

**Status: runs end to end on a coarse mesh; not validated.**

## Model

* Sails are zero-thickness surfaces; snappyHexMesh turns them into baffles,
  so each sail has two wall patches (`main`, `main_slave`). The mast is a
  10 mm tube.
* simpleFoam, kOmegaSST, wall functions. Sail Reynolds numbers are low
  (~5e4-2e5), so like the fins the real flow is partly laminar; treat
  absolute forces with care and compare trims relative to each other.
* Rigid sail shapes (no fluid-structure interaction).
* **Uniform apparent wind.** Real apparent wind changes speed and direction
  with height (wind gradient plus boat speed), which is why sails are
  twisted. That needs a height-dependent inflow only on the inflow part of
  the far field and is a planned addition; meanwhile the sail `twist`
  parameter is the main handle.

## Geometry

* `rig: iom_a` (default): IOM A rig from the class-rule dimensions (main
  leech 1615 mm, foot 355 mm, half width 240 mm; jib luff 1325 mm, foot
  380 mm; total ~0.62 m²). Each section is a NACA mean line with `camber` at
  40-45 % chord, set at `main_sheet`/`jib_sheet` at the foot and opening by
  `main_twist`/`jib_twist` towards the head.
* `rig: stl` with `stl_files: {main: sails/main.stl, jib: sails/jib.stl,
  mast: sails/mast.stl}` exported from Fusion 360 (sails as surface bodies).

## Outputs

`drive_N` (forward, −x), `heel_force_N` (to leeward), `heel_moment_Nm`
(about the waterline), `z_ce` (centre of effort height), lift and drag
relative to the apparent wind with `CL`/`CD` on the sail area, and
per-sail drive and heeling force.

## Studies

`smoke`: xcoarse, 20 iterations. Suggested: sheeting-angle sweep at
AWA = 25-35°, then AWA sweep 20-90° with trims re-optimised.
