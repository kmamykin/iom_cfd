# Notes for Claude sessions in this repo

- Personal project: OpenFOAM (ESI v2512) CFD for IOM RC yachts. GCP is the
  approved cloud for it.
- Python tooling in `src/iomcfd` (uv). Each simulation type is a plugin in
  `projects/<name>/` (defaults.yaml = parameter schema, project.py hooks,
  template/ OpenFOAM case, studies/).
- Tests: `uv run pytest -m "not docker"` (fast, no OpenFOAM);
  `uv run pytest -m docker` runs a real foil2d case in the image.
- OpenFOAM runs in Docker: `uv run iomcfd run <study>` re-execs in the
  `iom-cfd:latest` image (`make image` to build). Smoke studies exist for
  every project: `uv run iomcfd run <project>/smoke`.
- Runs are timestamped: `runs/<study>/<YYYYMMDD-HHMMSS>/` (UTC; study.yaml
  and run.json inside). Each `run`/`gcp submit` is a new run; `--resume`
  continues the latest. collect/report/viz take `--run-id` (default latest)
  and use the run's own study.yaml.
- Highlights (`highlights:` in a study; iomcfd/highlights.py) name the few
  cases worth a close look. They come from the current study file (else the
  run's copy) and drive the report's highlight tables/figures, which cases
  `viz` renders (plus montages), and `gcp fetch --fields`.
- `gcp fetch` downloads only results (params/result.json, surface.csv,
  force_history.csv, start_from.json) plus one mesh per mesh level; `--logs`, `--fields`,
  `--only` add more. Exported cases have gzipped mesh and logs. `iomcfd slim` frees a local run (dry run
  unless `--yes`). Don't fetch whole runs: the laptop's disk is limited.
- Website: `site/` (Quarto, GitHub Pages on push to main; see
  docs/website.md). The front page (`site/index.qmd`) is a card per
  published study; each study is a page, `site/<study>/index.qmd` (now only
  `fin-selection`). The charts come from committed CSVs in `site/data/`
  (`iomcfd site export`, sources in `site/data.yaml`), not from runs/.
  After findings change, the `site-update` skill updates it. Pushing to
  main publishes it, so commit and push only when asked.
- Findings: `projects/<project>/findings/<study>.md` (committed) logs
  conclusions, evidence tables, assumptions, compromises and decisions per
  run. `iomcfd report` writes report/summary.md; the `study-findings` skill
  turns it into a log entry.
- Templates read `system/caseParameters` via `#include` and `$name`. Only
  derived camelCase names become entries (study inputs are comments) to avoid
  clashing with OpenFOAM keywords; tests/test_projects.py enforces it.
- Boat frame: x aft, y port, z up, waterline z=0; + heel φ = to starboard,
  + leeway β_Y = bow to port (port tack).
- Symbols for forces, moments and angles in docs, findings and the site:
  docs/nomenclature.md (after Parolini & Quarteroni and the ORC VPP): D_h,
  S_h, T_a, S_a, M_a, D_h = D_v + D_i for a fin, β_TW/β_AW from the course,
  V_b. Parameter and output names (`leeway`, `drag_N`, `awa`) stay as they
  are; sails `awa` is from the centreline, fullboat `twa` from the course.
- Never edit files under runs/ to fix things; fix the template or project.py.
- foil2d stepped (Kline-Fogleman) sections: `foil: stair1:naca0009:x=0.5,d=0.3`
  (the number is steps per side: stair1 = the hobby KFm4; stair5/stair10 are
  5 x 0.2 / 10 x 0.1 mm at 80 mm chord; symmetric only; geometry/stepped.py). Their meshes are marched near the steps
  (cmesh.py); smooth sections must stay bit-identical to the old generator.
- Visualisation is a separate, re-runnable layer: `uv run iomcfd viz <study>`
  runs in the `iom-cfd-viz` image (ParaView 6.2, `make viz-image`) and only
  reads finished cases. Views are functions in `projects/<name>/viz.py`
  using `src/iomcfd/viz/pvlib.py`; no `|` in ParaView text.
