# Experimentation workflow

## Studies

A study is a YAML file in `projects/<project>/studies/`. It names the project,
overrides some defaults, and says which parameters vary.

```yaml
study: keel-sections            # results go to runs/keel-sections/<run id>/
project: foil2d
description: Compare candidate fin sections at upwind speed.
reference: validation/some.csv  # optional data overlaid by `iomcfd report`
report:                         # optional post-processing options for `iomcfd report`
  fin_span: 0.36                # foil2d: whole-fin forces in selection.png
  compare_at: {foil: naca0008, chord: 0.085, aoa: [2, 4, 6]}  # foil2d: forces of the comparison table
viz: {views: [velocity]}        # optional, for `iomcfd viz` (docs/visualization.md)
highlights:                     # optional: the few cases worth a close look (see Highlights)
  - name: thickness-at-working-load
    why: Does the laminar bubble grow as the section thins?
    where: {speed: 1.0, aoa: [4, 6]}
    compare: foil
    views: [separation, transition]
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
* `report:`, `viz:` and `highlights:` only change how finished results are
  presented. They are not case parameters, so editing them never re-runs a
  case: change them and re-run `iomcfd report` / `iomcfd viz`. `report:` and
  `viz:` are read from the study file stored with the run; `highlights:`
  from the current study file (see Highlights).
* `iomcfd plan <study> -v` prints the cases and every derived quantity
  (Reynolds number, inflow vectors, first-cell height...) without running
  anything.
* `--set key=value` on the command line pins a parameter for all cases, e.g.
  `--set mesh=xcoarse --set max_iter=200` for a quick check of a big study.
  The overrides are recorded in the run's `run.json`.

## Runs

Every `iomcfd run` (and every `iomcfd gcp submit`) starts a new run of the
study in its own directory, named after its UTC start time, so a later run
never overwrites an earlier one:

```
runs/<study>/<YYYYMMDD-HHMMSS>/
    study.yaml          the study file as it was when the run started
    run.json            created, git version (`git describe --dirty`), image, overrides, backend, job
    <case>/             one OpenFOAM case per parameter set
    results.csv         collected results
    report/             iomcfd report (plots, tables, summary.md)
    viz/                iomcfd viz (montages, animations, gallery)
```

* `iomcfd runs <study>` lists the runs and their size on disk.
* `collect`, `report` and `viz` work on the latest run, or `--run-id ID`.
  They use the run's own `study.yaml`, so editing the study afterwards (for
  the next run) does not change what an old run means.
* `iomcfd run <study> --resume` continues the latest run instead of starting
  a new one: finished cases are skipped, failed and missing ones run. Use
  it after an interruption, to retry failed cases (e.g. with
  `--set relax_U=0.6`), or to add points to the same run. `--run-id ID`
  continues a particular run.
* Within a run, a case counts as finished when its `result.json` has the
  same hash of the physical parameters (`np` and relaxation factors are
  excluded). `--force` with `--resume` re-runs finished cases too.
* A new run computes every case again, so each run reflects the code at
  its git version. Old runs are not reused; delete the ones you no longer
  need.
* `iomcfd slim <study> [--run-id ID]` frees disk: it deletes each case's
  mesh, logs, fields and the rest of the OpenFOAM case, and keeps its
  results (`params.json`, `result.json`, `surface.csv`), its `viz/` images,
  `results.csv`, `report/` and the mesh of one case per mesh level (for the
  report's mesh figure). It shows what it would delete; `--yes` deletes.
  What is not also in the bucket is gone for good.

Case directories are named from the varied parameters (`aoa4_foilnaca0008`).
Each case stores `params.json` and, when finished, `result.json`.

## Highlights

A run of a few hundred cases is too many to inspect, or download, case by
case. A study's `highlights:` name the few cases worth a close look, chosen
from earlier findings, and say why:

```yaml
highlights:
  - name: chord-at-high-load                 # [A-Za-z0-9_-], used in file names
    why: At the 6 deg force a 100 mm chord wins. How do the bubble and transition move with chord?
    where: {foil: naca0009, speed: 1.0, aoa: 6}   # parameter: value or list (swept or fixed)
    compare: chord                           # side by side (default: the parameter with most values)
    views: [velocity, separation]            # ParaView views (default: the study's / project's)
```

The selected cases form a grid: one column per value of `compare`, one row
per combination of the other parameters that still vary. They drive:

* `iomcfd report`: `report/highlights.md` (a table per highlight: the
  cases' key results, for foil2d including the separation and reattachment
  points) and project figures that need no field data; foil2d draws
  `report/highlight_<name>.png`, Cp and Cf along the chord from each case's
  `surface.csv`, one line per compared value.
* `iomcfd viz`: renders only these cases, each with its highlights' views,
  and one montage per highlight and view (`viz/highlights/`).
* `iomcfd gcp fetch --fields`: downloads field data only for these cases.

Highlights come from the current study file (falling back to the run's own
copy), because what to look at usually follows from a run's results: add
them after a run and re-run `report`/`viz` on it. A highlight that selects
nothing in a run (e.g. a parameter the run did not have) is skipped with a
message. The `study-findings` skill proposes highlights for the next run.

## Findings

Each study keeps a log of what its runs showed in
`projects/<project>/findings/<study>.md`. It is committed; `runs/` is not.
One entry per run, newest first, with conclusions, the evidence tables they
rest on, assumptions, compromises, decisions for the next run, learnings
and next steps.

`iomcfd report` writes `report/summary.md`: the facts of the run (setup,
status, failures and their reasons, convergence and unsteadiness by
parameter, compute used) plus the project's comparison tables and the
highlights tables. None of it needs meshes, logs or fields, so it works on a
run fetched with the default (light) `iomcfd gcp fetch`. The
`study-findings` skill builds on it. In Claude Code, run
`/study-findings <project>/<study> [run id]`, or headless
`claude -p "/study-findings <project>/<study>"`. It reads the summary, the
figures, the run's study file and the earlier findings for this and related
studies, checks the conclusions against the numbers, and adds the entry.

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

All paths below are in one run, `runs/<study>/<run id>/` (`<run>`).

* `<run>/results.csv`: one row per case, all inputs, derived values and
  metrics.
* `<run>/<case>/`: the full OpenFOAM case, logs, `postProcessing/`,
  `result.json`, and for foil2d `surface.csv` (Cp, Cf along the section).
  Cases run on GCP have their mesh and logs gzipped (`points.gz`,
  `log.simpleFoam.gz`; read with `zless`), and locally hold only what was
  fetched (see docs/cloud-gcp.md).
* `iomcfd report <study>`: in `<run>/report/`:
  * `summary.md`: setup, status, failures, convergence, compute, tables
    (see Findings);
  * the project's result plots (foil2d: polar with reference data, and a
    grid-convergence table `mesh_convergence.csv` when the study varies `mesh`);
  * `highlights.md` and the project's highlight figures (see Highlights);
  * **a mesh figure for every study**, `mesh_<case>.png` (one per mesh level
    when `mesh` varies): plane cuts through the actual `constant/polyMesh`
    the solver used, with wall patches in red, zoomed on the regions that
    matter (foil leading/trailing edge, fin section and prism layers, hull
    profile and free-surface band, sail sections), plus checkMesh quality,
    y+ and prism-layer coverage. Cuts follow the boat's heel. Each project
    defines its views in `Project.mesh_views()`; drawing is pure Python
    (`iomcfd.polymesh`, `iomcfd.meshplot`), no OpenFOAM or ParaView needed.
