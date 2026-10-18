# IOM CFD

OpenFOAM simulations for International One Metre (IOM) radio-controlled
yachts: keel and rudder sections, 3D appendages, hull resistance, sails, and
(experimental) the whole boat in water and air.

**Website:** [kmamykin.github.io/iom_cfd](https://kmamykin.github.io/iom_cfd/),
the published studies, each a summary of where it stands (so far: which fin
section, why, and how sure), with flow pictures and videos.

You describe a design study in a small YAML file. The tooling turns each
variation into a complete OpenFOAM case, meshes it, runs it in Docker
(locally or on Google Cloud Batch), stops it when the forces have settled,
and collects the results into one table and a set of plots.

```
study YAML ──> iomcfd run ──> OpenFOAM cases (Docker / Cloud Batch) ──> results.csv, report plots, mesh figures
                                      │  (computed once)
                                      └──> iomcfd viz (ParaView image, re-run any time) ──> images, movies, gallery
```

## Projects

| Project | What it computes | Solver / mesh | Status |
|---|---|---|---|
| [`foil2d`](projects/foil2d) | 2D section polars (Cl, Cd, Cm, Cp, Cf, separation) for fins and rudders | simpleFoam + kOmegaSSTLM transition, generated C-grid | **Working, partly validated** |
| [`appendage3d`](projects/appendage3d) | Fin + bulb + rudder forces and moments (D_h, S_h, M_h,dyn, N_h) at boat speed V_b, leeway β_Y, heel φ, rudder angle δ_R | simpleFoam + kOmegaSST, snappyHexMesh | Runs end to end, not validated |
| [`hull`](projects/hull) | Calm-water resistance D_h, fixed or free sinkage/trim | interFoam (VOF), snappyHexMesh | Fixed attitude runs end to end; free attitude untested |
| [`sails`](projects/sails) | Drive and heeling force (giving T_a, S_a), heeling moment M_a, centre of effort Z_CE of main + jib + mast | simpleFoam + kOmegaSST, sails as baffles | Runs end to end, not validated |
| [`fullboat`](projects/fullboat) | Hull + appendages in water and rig in air together; force/moment balance | interFoam (VOF) | **Experimental**, pipeline check only |

"Runs end to end" means a coarse smoke study meshes, solves and extracts
results; it says nothing about accuracy yet. See each project's README for
physics, parameters, outputs and limitations.

## Quick start

Requirements: Docker, [uv](https://docs.astral.sh/uv/), ~10 GB disk. The
solver image is ESI OpenFOAM v2512 (`opencfd/openfoam-default:2512`, amd64 and
arm64, so it runs natively on Apple Silicon).

```bash
make setup          # Python env for planning, analysis, tests (uv sync)
make image          # build the solver image iom-cfd:latest
make smoke          # 2-case foil2d run end to end (~2 min)

uv run iomcfd projects                                   # list projects and studies
uv run iomcfd plan foil2d/validation-naca0009-re1e5      # what a study expands to
uv run iomcfd run  foil2d/validation-naca0009-re1e5 --set mesh=coarse -j 8
uv run iomcfd report foil2d/validation-naca0009-re1e5    # plots, tables, summary.md in runs/<study>/<run id>/report/
uv run iomcfd runs foil2d/validation-naca0009-re1e5      # every run is kept, newest last

make viz-image                                           # ParaView 6.2 visualisation image (once)
uv run iomcfd viz foil2d/validation-naca0009-re1e5       # flow images, animations, gallery (highlights only, if set)
open runs/validation-naca0009-re1e5/*/viz/index.html
```

`iomcfd run` on the host re-launches itself in the Docker image with the
repository mounted at `/work`, so template and code edits take effect
without rebuilding the image. Each run goes to its own timestamped
directory, `runs/<study>/<YYYYMMDD-HHMMSS>/`, so results are never
overwritten; `--resume` continues the latest run (finished cases are
skipped). What each run showed is logged in
`projects/<project>/findings/<study>.md`. In Claude Code,
`/study-findings <project>/<study>` writes the entry.

To look inside a case with OpenFOAM tools: `uv run iomcfd shell`, then
`cd runs/<study>/<run id>/<case>` (for ParaView, `foamToVTK -latestTime` and open the
`VTK/` folder on the host).

## Directory layout

```
iom_cfd/
├── README.md                 this file
├── Makefile                  setup, image, smoke, test, push
├── pyproject.toml            the iomcfd Python package (uv)
├── docker/                   Dockerfile (solver: OpenFOAM v2512 + Python), Dockerfile.viz (ParaView 6.2)
├── src/iomcfd/               tooling
│   ├── cli.py                iomcfd command (plan/render/run/collect/report/shell/gcp)
│   ├── study.py              study YAML -> cases (sweep, zip, LHS sample, explicit cases)
│   ├── project.py            project plugin base class + loader
│   ├── runner.py             renders and runs cases, convergence monitor, export
│   ├── results.py            results.csv
│   ├── polymesh.py           read OpenFOAM meshes (ASCII/binary) and cut them with planes
│   ├── meshplot.py           mesh figures for reports
│   ├── verification.py       grid convergence (Richardson / GCI)
│   ├── highlights.py         the cases a study names for a close look (report, viz, fetch)
│   ├── viz/                  ParaView visualisation: pvlib (scene helpers), render_case, study (montages, animations, gallery)
│   ├── physics.py            water/air properties, turbulence inflow, y+ sizing
│   ├── forces.py             force/moment output readers
│   ├── geometry/             foils, C-grid mesher, STL tools, fins/bulb/rudder, hulls, sails
│   └── cloud/gcp.py          Google Cloud Batch backend
├── projects/<name>/          one directory per simulation type
│   ├── README.md             physics, parameters, outputs, limitations
│   ├── defaults.yaml         every parameter with its default (the schema)
│   ├── project.py            derive / render / extract / report hooks
│   ├── viz.py                ParaView views of finished cases (iomcfd viz)
│   ├── template/             the OpenFOAM case (reads system/caseParameters)
│   ├── studies/*.yaml        studies (smoke, validation, design sweeps)
│   └── validation/           reference data (foil2d)
├── geometry/                 your CAD exports (Fusion 360 STL) and foil .dat files
├── cloud/gcp/                config.env.example, setup.sh
├── site/                     the website (Quarto, GitHub Pages): page, data, figures
├── docs/                     workflow, OpenFOAM notes, cloud, geometry conventions, nomenclature
│   └── research/             literature notes (e.g. surface-roughness.md, bulb-design.md, vpp.md)
├── tests/                    pytest (pure Python; `-m docker` runs OpenFOAM)
└── runs/                     simulation output (git-ignored)
```

## How experimentation works

1. **Verify** the numerics once per project and flow regime: run the same case
   on `mesh: coarse/medium/fine` and check the change in the quantity you care
   about (Richardson extrapolation / GCI). Keep the domain size and iteration
   budget honest.
2. **Validate** against measurements where they exist
   ([`foil2d/validation`](projects/foil2d/validation)), so you know how far to
   trust absolute numbers versus differences between designs.
3. **Explore** designs with sweeps: change one or two parameters, keep
   everything else fixed, compare. Log what each run showed, and the
   assumptions it rests on, in the study's findings file.
4. **Optimise** with sampled designs (`sample: {method: lhs, ...}`) fitted
   with a surrogate model, or drive studies from your own optimiser.

Details, runs, findings and statistics: [docs/workflow.md](docs/workflow.md).
Visualisation of results (views per project, adding views, animations):
[docs/visualization.md](docs/visualization.md).
The project website, a page per published study built from `site/` and
published on GitHub Pages: [docs/website.md](docs/website.md).

## Running on Google Cloud

One Cloud Batch job per run of a study and one task per case, on Spot VMs, with
results copied to a bucket. One-time setup and commands:
[docs/cloud-gcp.md](docs/cloud-gcp.md).

```bash
cp cloud/gcp/config.env.example cloud/gcp/config.env   # fill in project/bucket
cloud/gcp/setup.sh                                     # APIs, registry, bucket, service account
cloud/gcp/setup-github.sh                              # GitHub Actions pushes the image on every push to main
uv run iomcfd gcp submit foil2d/keel-sections
uv run iomcfd gcp status
uv run iomcfd gcp fetch foil2d/keel-sections           # latest run's results (MBs, not GBs) -> runs/<study>/<run id>/
uv run iomcfd gcp fetch foil2d/keel-sections --fields  # + whole cases of the study's highlights, for viz
```

## Validation so far

NACA 0009 at Re = 1e5 (the IOM fin regime) against Princeton wind-tunnel data
(SoarTech 8, verified against the UIUC archive), coarse mesh, Tu = 0.1 %:

| α | | Cl | Cd |
|---|---|---|---|
| 4° | tunnel (interpolated) | 0.424 | 0.0134 |
| | transition model | 0.425 ± 0.022 (unsteady) | 0.0148 (+10 %) |
| | fully turbulent | 0.404 (−5 %) | 0.0166 (+24 %) |
| 8° | tunnel (interpolated) | 0.713 | 0.0363 |
| | transition model | 0.673 (−6 %) | 0.0454 (+25 %) |
| | fully turbulent | 0.733 (+3 %) | 0.0309 (−15 %) |

The transition model is the right default for IOM fins at small angles;
near stall the two models bracket the measurements. Mesh-refinement,
turbulence-intensity sensitivity, transient runs and the NASA NACA 0012
benchmark are the next validation steps. Discussion:
[projects/foil2d/README.md](projects/foil2d/README.md).

## Conventions

* SI units everywhere; angles in degrees in studies.
* Boat frame for all 3D projects: **x aft** (bow near x = 0, water flows +x),
  **y to port**, **z up**, calm waterline at z = 0. Positive heel φ = mast
  to starboard; positive leeway β_Y = bow to port (port tack upwind).
  See [docs/geometry.md](docs/geometry.md) for Fusion 360 export settings.
* Symbols for forces, moments and angles (D_h, S_h, T_a, S_a, M_a, β_TW,
  β_AW, ...) follow [docs/nomenclature.md](docs/nomenclature.md), after
  Parolini & Quarteroni and the ORC VPP documentation. Parameter and output
  names (`leeway`, `drag_N`, `side_N`) are unchanged; the doc maps them.
* Study parameters are validated against `defaults.yaml`: a typo is an error,
  not a silently ignored setting.
* Generated case files are outputs. Edit the template or the study, not
  `runs/`.

## Licence

* **Code** (Python, OpenFOAM case templates, Docker and workflow files,
  `site/figures.py`): [MIT](LICENSE).
* **Writing, figures and results** (the website in `site/` apart from its
  code, the Markdown in `docs/` and `projects/` such as the findings logs and
  methodology, and the data in `site/data/`):
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit
  "Kliment Mamykin, iom_cfd" with a link to this repository.
* **Not covered:** third-party reference data keeps its own terms.
  * `projects/foil2d/validation/naca0009_re1e5_princeton.csv`: Selig,
    Donovan & Fraser (1989), from the UIUC airfoil data archive.
  * `projects/foil2d/validation/naca0012_re6e6_tmr.csv`: NASA Turbulence
    Modeling Resource.

  Each file's header gives its source.
