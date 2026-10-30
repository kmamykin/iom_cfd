# windage: the hull above the water in the apparent wind

Steady RANS of the topsides (and deck) in a uniform apparent wind, for the
VPP's windage: drag along the wind, lift across it, where they act. The
water side of the same split is keel3d with an STL hull (`hull_stl`).

**Status: new (2026-10-29); the alt-air-scout study settles mesh, Re
dependence and wind angles.**

## Model

* simpleFoam with kOmegaSST, wall functions (`nutUSpaldingWallFunction`),
  fully turbulent; the inflow Tu sets the freestream k and omega (held, as
  in keel3d).
* **Geometry.** The hull (an STL in the boat frame, `hull_stl`, or keel3d's
  canoe body) is placed at the heel's attitude: heel φ about the x axis at
  the waterline, then `trim` about the middle of its length, then `sink`,
  as the VPP floats it (`vpp hydro --zip` prints a heel's static attitude).
  It is cut at the water plane and closed by its mirror image below it
  (`iomcfd.geometry.waterline.split`). The floor z = 0 cuts the mirror image
  off again; mirroring lets the topsides cross it at their own angle, so
  snappyHexMesh snaps the cells there onto the hull (a flat cap on the plane
  coincides with the boundary; a cap above it put a sharp edge next to the
  plane, and at 60° of heel gave 33 highly skewed faces against the
  mirror's 7, and prism layers over 61 % of the hull's target thickness
  against 80 %: keel3d's water side, xcoarse, 2026-10-29).
* **Wind.** The apparent wind, uniform with height, from `awa` off the
  centreline (0 = from the bow), from port; the boat heels to starboard, away
  from it. The hull only feels the air's velocity relative to it, so the
  apparent wind is what to sweep: the true wind enters through the VPP's
  wind triangle and its height profile. AWS matters only through Re.
* **Water surface.** A slip floor: no boundary layer on the water and no
  wind gradient. The VPP takes the apparent wind at the height of the
  projected area's centroid (`z_centroid_m`), as it does for its own
  windage model.
* **Domain.** 2 L upwind of the topsides, 4 L downwind, 2 L to each side,
  1.5 L high, as a box aligned with the boat; all sides but the floor are the
  `freestream` group, so every `awa` uses the same layout. Background cell
  L/10; a box round the topsides and a box downwind of them, along the wind.

## Outputs

`drag_N` (along the apparent wind), `lift_N` (across it, horizontal: + is
the wind's direction turned 90° anticlockwise seen from above, to port for
wind from the bow and aft for any wind from port, so the topsides' lift
ahead of the beam is negative, forward and to leeward), `vertical_N`,
`Fx_N`, `Fy_N`; `roll_moment_Nm`,
`pitch_moment_Nm`, `yaw_moment_Nm` about the bow on the waterline (the placed
boat origin), right-handed about x aft, y port, z up; `x_ce`, `z_ce` where
the side force acts; `cd`, `cl` on `A_proj_m2`, the topsides' area projected
normal to the wind (the area the VPP's `ProjectedArea` model multiplies by
its C_D 0.816); `cx`, `cy` on the beam-on area.

## Studies

* `smoke`: canoe body, heel 20°, xcoarse, 20 iterations.
* `alt-air-scout`: the alternative hull: mesh, Re and wind-angle checks.
* `alt-air-mesh`: fine against xfine at heel 30°, 30 and 45° off the bow,
  a repeat, and fine at 6 m/s (findings/alt-air-mesh.md).
* `alt-air`: the alternative hull for the VPP: 7 heels × 15 angles at 4 m/s,
  fine.

## In the VPP

`iomcfd vpp export-table windage alt-air@<run id> --select mesh=fine --out
boats/tables/<name>.csv` writes a run as a windage table (vpp/windage.py):
D, L, the vertical force and the moments per unit dynamic pressure over heel
× `awa`. A boat file reads it with `windage: forces: {class:
.windage.WindageTable, args: {table: tables/<name>.csv}}` in place of the
drag-only `ProjectedArea` (docs/vpp.md).
