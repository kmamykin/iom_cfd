# sails: main, jib and mast in the apparent wind

Steady RANS of rigid sails above a flat, frictionless water surface: drive
and heeling force (which give the thrust T_a and side force S_a), heeling
moment M_a and centre-of-effort height Z_CE for a sail trim (sheeting,
twist, camber), apparent wind angle and heel φ. Symbols:
[docs/nomenclature.md](../../docs/nomenclature.md).

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

* `drive_N` (forward, −x) and `heel_force_N` (to leeward). sails has no
  leeway, so these are along and across the centreline, not the course.
  With leeway β_Y the thrust is T_a = drive_N cos β_Y + heel_force_N sin β_Y
  and the side force S_a = heel_force_N cos β_Y − drive_N sin β_Y.
* `heel_moment_Nm` (M_a, about the waterline, + heels to starboard).
* `z_ce` (Z_CE, the height of the centre of effort).
* `lift_N` and `drag_N` (L_a, D_a, relative to the apparent wind) with
  `CL`/`CD` (C_L, C_D) on the sail area.
* Per-sail drive and heeling force.

## Studies

`smoke`: xcoarse, 20 iterations. Suggested: sheeting-angle sweep at
`awa` = 25-35°, then an `awa` sweep 20-90° with trims re-optimised. `awa`
is measured from the centreline; the apparent wind angle from the course
is β_AW = `awa` + β_Y.
