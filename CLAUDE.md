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
  every project: `uv run iomcfd run <project>/smoke --force`.
- Templates read `system/caseParameters` via `#include` and `$name`. Only
  derived camelCase names become entries (study inputs are comments) to avoid
  clashing with OpenFOAM keywords; tests/test_projects.py enforces it.
- Boat frame: x aft, y port, z up, waterline z=0; + heel = to starboard,
  + leeway = bow to port (port tack).
- Never edit files under runs/ to fix things; fix the template or project.py.
- Visualisation is a separate, re-runnable layer: `uv run iomcfd viz <study>`
  runs in the `iom-cfd-viz` image (ParaView 6.2, `make viz-image`) and only
  reads finished cases. Views are functions in `projects/<name>/viz.py`
  using `src/iomcfd/viz/pvlib.py`; no `|` in ParaView text.
