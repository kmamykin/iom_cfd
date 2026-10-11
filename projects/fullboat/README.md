# fullboat: the whole boat in water and air (experimental)

One interFoam (VOF) simulation with the hull and appendages in water and the
rig in air: water flows past at boat speed below the waterline, the apparent
wind blows above it (entering through the front and the windward side).

**Status: experimental. Only a pipeline check has been run (xcoarse, 10
iterations); no converged result exists yet.**

## Why and how

A sailing yacht is in steady state when the sails' drive equals the hull
resistance, the keel's side force balances the sails' heeling force, and
the heeling moment equals the righting moment. This project computes all
those forces together at a chosen attitude and reports the imbalance:

* `net_Fx_N`, `net_Fy_N`, `net_Fz_N`: sum of hydrodynamic and aerodynamic
  forces and the weight (`mass`); buoyancy is in the hydrodynamic pressure
  force.
* `net_Mx_Nm`, `net_My_Nm`, `net_Mz_Nm`: moments about the centre of gravity
  (roll, pitch, yaw).
* the pieces: `resistance_N`, `hydro_side_N`, `drive_N`, `heel_force_N`,
  `aero_heel_moment_Nm`, `hydro_righting_moment_Nm`, per-component forces.

Equilibrium (a CFD velocity prediction) means finding `speed`, `heel`,
`leeway` (and `rudder_angle` via `appendage_params`, `sinkage`, `trim`) that
drive the imbalances to zero. Practical route: run small sweeps around a
guess, fit the imbalances linearly in the unknowns, solve, and repeat (a
Newton iteration done with studies). Start from appendage3d, hull and sails
results to make the first guess good.

## Model limits (current)

* Fixed attitude only (no free sinkage/trim in this project yet).
* Uniform apparent wind (no wind gradient or twist), port tack only.
* The free surface leaves the domain through split outlet patches at z = 0;
  large stern waves at the outlet may disturb it.
* The air region is large and mostly coarse: rig refinement is a box around
  the sails.
* The mesh is big: plan on the cloud (`np: 16` or more) at `coarse` and above.

## Studies

`smoke`: Wigley hull, parametric appendages and A rig, 10° heel, 3° leeway,
xcoarse, 10 iterations.
