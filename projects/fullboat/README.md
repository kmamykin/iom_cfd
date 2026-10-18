# fullboat: the whole boat in water and air (experimental)

One interFoam (VOF) simulation with the hull and appendages in water and the
rig in air: water flows past at boat speed below the waterline, the apparent
wind blows above it (entering through the front and the windward side).

**Status: experimental. Only a pipeline check has been run (xcoarse, 10
iterations); no converged result exists yet.**

## Why and how

A sailing yacht is in steady state when the forces and moments balance
(the balance equations in [docs/nomenclature.md](../../docs/nomenclature.md)):
* the sails' thrust equals the hydrodynamic drag, T_a = D_h;
* the hydrodynamic side force balances the sails' side force, S_h = S_a;
* the heeling moment is balanced by the righting moment,
  M_a + M_h,dyn = RM_φ − RM_V;
* the yaw moments cancel, N_a + N_h = 0.

This project computes all those forces together at a chosen attitude and
reports the imbalance:

* `net_Fx_N`, `net_Fy_N`, `net_Fz_N`: sum of hydrodynamic and aerodynamic
  forces and the weight (`mass`); buoyancy is in the hydrodynamic pressure
  force.
* `net_Mx_Nm`, `net_My_Nm`, `net_Mz_Nm`: moments about the centre of gravity
  (roll, pitch, yaw).
* the pieces:
  * `resistance_N` (D_h), `hydro_side_N` (S_h), `drive_N` (T_a) and
    `heel_force_N` (S_a). All are along or across the course, because the
    boat, not the flow, is turned by the leeway.
  * `aero_heel_moment_Nm` (M_a).
  * `hydro_righting_moment_Nm`: the water's roll moment, buoyancy included.
    The weight's moment is in the net moments.
  * per-component forces.

The wind is set by `tws` and `twa` (V_TW, β_TW). `twa` is measured from the
course, since the flow, not the boat, defines x. The apparent wind follows
as `aws` and `awa_deg` (V_AW, β_AW).

Equilibrium (a CFD velocity prediction) means finding `speed` (V_b), `heel`
(φ), `leeway` (β_Y) (and `rudder_angle` δ_R via `appendage_params`,
`sinkage`, `trim`) that
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
