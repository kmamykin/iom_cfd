# Experimentation workflow

## Studies

A study is a YAML file in `projects/<project>/studies/`. It names the project,
overrides some defaults, and says which parameters vary.

```yaml
study: keel-sections            # results go to runs/keel-sections/
project: foil2d
description: Compare candidate fin sections at upwind speed.
reference: validation/some.csv  # optional data overlaid by `iomcfd report`
defaults:                       # override projects/foil2d/defaults.yaml
  chord: 0.085
  speed: 1.0
sweep:                          # full factorial: 3 x 9 = 27 cases
  foil: [naca0007, naca0008, file:sd8020.dat]
  aoa: [0, 1, 2, 3, 4, 5, 6, 7, 8]
# (a real study would use sweep OR zip OR sample; they are shown together here)
zip:                            # varied together, row by row (crossed with sweep)
  speed: [0.5, 1.0, 1.5]
  aoa:   [6, 4, 3]
sample:                         # space-filling design (crossed with sweep/zip)
  method: lhs                   # lhs | random
  n: 30
  seed: 1
  ranges: {chord: [0.065, 0.09], aoa: [0, 8]}
cases:                          # extra one-off cases, appended
  - {foil: naca0012, aoa: 10, mesh: fine}
```

* Every parameter must exist in the project's `defaults.yaml`; unknown names
  are errors.
* `iomcfd plan <study> -v` prints the cases and every derived quantity
  (Reynolds number, inflow vectors, first-cell height...) without running
  anything.
* `--set key=value` on the command line pins a parameter for all cases, e.g.
  `--set mesh=xcoarse --set max_iter=200` for a quick check of a big study.
  Pinned studies hash differently, so they don't overwrite the real results.

## Case names and caching

Case directories are named from the varied parameters
(`aoa4_foilnaca0008`). Each case stores `params.json` and, when finished,
`result.json` with a hash of the physical parameters (`np` excluded). A
re-run skips cases whose result exists with the same hash, so you can:

* add angles or designs to a sweep and only the new cases run,
* interrupt a long study and resume it,
* fetch cloud results into `runs/` and keep extending locally.

`--force` recomputes everything.

## Convergence and statistics

Solvers run until the forces settle, not for a fixed number of iterations.
While a case runs, the runner polls its force history every 15 s. When the
mean over the last `conv_window` iterations differs from the previous
window's mean by less than `conv_tol` (relative), it writes
`stopAt writeNow` into `controlDict` and the solver stops cleanly. If that
never happens within `max_iter`, the case is marked `not_converged`; its
values are still averages over the last window.

Each result reports the mean and standard deviation over the final window.
A large standard deviation (foil2d flags `unsteady`) means the flow itself
is unsteady (laminar separation bubbles shedding vortices, stall). A steady
solver's average over iterations is then only an estimate; use a transient
run for those cases.

## Verification: mesh refinement

Mesh levels are named (`xcoarse`, `coarse`, `medium`, `fine`, `xfine`) and
each step refines consistently (foil2d: √2 per direction, so 2× cells; the
snappyHexMesh projects add one refinement level). For a key result:

```yaml
sweep:
  mesh: [coarse, medium, fine]
```

With three levels at constant ratio r and results f1 (fine), f2, f3:
observed order p = ln((f3 − f2)/(f2 − f1)) / ln r, extrapolated value
f_ext = f1 + (f1 − f2)/(r^p − 1), and the grid convergence index
GCI = 1.25 |f1 − f2| / (f1 (r^p − 1)). Use the coarsest level whose error is
small compared with the design differences you want to resolve.

## Validation

Compare against measurements in the same regime (Re, turbulence level),
interpolating to matching angles. `projects/foil2d/validation/` holds
reference polars with their sources; add new data there and reference it from
a study's `reference:` key.

## Comparing designs

Differences between designs are usually more accurate than absolute values,
because many modelling errors are similar for similar shapes. Good practice:

* change one thing at a time,
* keep mesh level, domain, turbulence settings and convergence criteria
  identical across the designs being compared,
* check a few points on a finer mesh to make sure the ranking doesn't change.

## Optimisation

1. Run a space-filling design (`sample: {method: lhs, n: 20-50}`) over the
   parameters that matter.
2. Fit a surrogate (polynomial response surface or Gaussian process) to
   `results.csv` in a notebook (`uv run python`, pandas and matplotlib are
   installed).
3. Run the surrogate's optimum (and its neighbours) as explicit `cases:`;
   add them to the training set and repeat.

For a closed loop, an optimiser can write a study YAML per generation and
call `iomcfd run` (or `iomcfd gcp submit`), reading `results.csv` back.

## Results

* `runs/<study>/results.csv`: one row per case, all inputs, derived values
  and metrics.
* `runs/<study>/<case>/`: the full OpenFOAM case, logs, `postProcessing/`,
  `result.json`, and for foil2d `surface.csv` (Cp, Cf along the section).
* `iomcfd report <study>`: plots in `runs/<study>/report/`.
