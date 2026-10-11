# hull: calm-water resistance

Free-surface (VOF) simulation of the hull, optionally with appendages, at a
given speed and attitude. The setup follows the OpenFOAM DTCHull and
DTCHullMoving tutorials, scaled to a 1 m boat.

**Status: fixed attitude runs end to end on a coarse mesh (Wigley hull); not
validated. Free sinkage/trim (`attitude: free`) is set up but untested.**

## Model

* interFoam (two-phase VOF), kOmegaSST with wall functions.
* `attitude: fixed`: local time stepping (pseudo-steady), the attitude is what
  you set (`heel`, `trim`, `sinkage`, `leeway`). Fast; the usual first step.
* `attitude: free`: transient, rigid-body motion in heave and pitch
  (`rigidBodyMotion` with Pz + Ry joints). Needs `mass`, `cog` and `inertia`;
  the hull must be positioned at the waterline that matches its mass. Several
  times more expensive.
* Half domain with a symmetry plane at y = 0 when heel = leeway = 0
  (`half_domain: auto`); forces are doubled in the results.
* Domain: 1.5 L ahead, 3.5 L behind, 2 L to the side, 1.5 L deep. Mesh: z-graded
  background with a fine band at the waterline, refinement boxes around the hull
  and over the Kelvin wave pattern, prism layers on the hull.

## Geometry

* `hull: wigley` (default): the analytic Wigley test hull at L = 1 m,
  B = 0.18 m, T = 0.05 m, which displaces 4.0 kg. It isn't an IOM shape, but it
  is a standard benchmark with published data, useful to check the setup.
* `hull: file:hulls/<name>.stl`: your Fusion 360 hull, mapped into the boat
  frame with `stl_scale`, `stl_rotate`, `stl_translate` (bow at x ≈ 0, design
  waterline at z = 0).
* `appendages: true` adds the appendage3d parametric fin/bulb/rudder
  (`appendage_params` overrides them), or `extra_stl` adds your own STLs.

## Outputs

`resistance_N` (total, friction and pressure parts, per component),
`vertical_force_N`, `side_force_N`, `pitch_moment_Nm` (about the CoG),
`Ct` (on the at-rest wetted area), `Cf_ittc57`, residuary `Cr = Ct − Cf`,
`Fn`, and for free attitude `sinkage_m` and `trim_deg` (from the rigid-body
log; verify the sign convention on your first free run). The free surface
(alpha = 0.5 iso-surface) is written to
`postProcessing/freeSurface/<time>/`.

## Studies

`smoke`: Wigley hull, xcoarse, 20 iterations.

Suggested first real study: speed sweep 0.4-2.0 m/s (Fn 0.13-0.64) on
`coarse`, then `medium`; compare Ct, Cr against published Wigley results
before trusting IOM-hull numbers.
