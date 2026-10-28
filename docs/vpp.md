# VPP: boat speed, race time and exchange rates

`src/iomcfd/vpp/` turns forces into boat speed. For each true wind speed and
angle it finds the fastest steady state in which the forces balance, then
times a windward-leeward race. Background and choices:
[research/vpp.md](research/vpp.md). Symbols and signs:
[nomenclature.md](nomenclature.md).

**Results are relative to the model.** No real-world speed has calibrated
it. Several inputs are placeholders (see [Inputs to replace](#inputs-to-replace)).

## Use

```
uv run iomcfd vpp run canoe-placeholder         # race time, exchange rates, polar -> runs/vpp/<boat>/<UTC time>/
uv run iomcfd vpp report canoe-placeholder      # write the latest run's report.html again (--run-id, or a run dir)
uv run iomcfd vpp point canoe-placeholder --tws 3 --twa 45   # one equilibrium, each part's forces
uv run iomcfd vpp point canoe-placeholder --tws 3 --twa 45 --hold sails.flat=0.8
uv run iomcfd vpp hydro canoe-placeholder       # mass budget, RM and GZ against heel
uv run iomcfd vpp compare canoe-placeholder canoe-placeholder-foil      # two boats
uv run iomcfd vpp compare canoe-placeholder --set-b components.hull.forces.args.cf_factor=0.8
uv run iomcfd vpp sweep canoe-placeholder --vary components.keel.forces.args.table=tables/a.csv,tables/b.csv
uv run iomcfd vpp export-table keel3d bulb-section@20261019-203823 --select bulb_aspect=1.0 ... \
    --out boats/tables/keel-round-bulb.csv      # one keel3d design as a table for a boat file
uv run iomcfd vpp export-table keel3d ht35-keel@<run id> --select mesh=medium --model grid \
    --out boats/tables/keel-ht35-3d.csv         # a heel x leeway x speed keel3d run as a grid table
uv run iomcfd vpp table build boats/tables/keel-ht35.yaml   # a table built by a model from a recipe
uv run iomcfd vpp compare canoe-placeholder --set-b components.keel.forces.args.table=tables/keel-ht35.csv
```

Every command takes `--no-cache` to compute the boat's tables afresh.

* **Boat files.** A boat is `boats/<name>.yaml`; `boats/canoe-placeholder.yaml`
  documents every key. Private boats, such as licensed hull lines, go in
  `boats/private/`, which git ignores. A boat's parts are listed under
  `components:` (see [Boat files](#boat-files)).
* **Overrides.** `--set a.b=v` overrides any entry by its dotted path, e.g.
  `--set components.rudder.args.span=0.21`.
* **Designs.** A part describes one design. To compare designs, build two
  boats: two files, `compare --set-b`, or `sweep --vary`.
* **CFD results** reach a boat file as a table (`boats/tables/*.csv`),
  exported from a run with `vpp export-table`. The run is given as
  `<study>@<run id>` and looked up in `$IOMCFD_SOURCE_RUNS`, then in
  `runs/` (e.g. `IOMCFD_SOURCE_RUNS=../bulb-design/runs`); `--select` picks
  the design's cases. The table holds the raw points and, in its header, the
  run, the filter and the geometry the forces belong to.
* **Grid exports.** A keel3d run over heel × leeway × speed (every
  combination, one design) exports with `--model grid` as a `model: grid`
  table: per case X less the hull's 0° drag (the hull model has it), Y, and
  K, M, N at the case's centre of lateral resistance; the vertical force
  less its 0° value as `Zv`, `Mv`. `KeelGrid` reads it as it is, so the
  speed dependence is the CFD's, not the C_F(Re) scaling of a fit. A missing
  case is an error; `--fill` fills it along the leeway and flags it, as a
  `not_converged` case is.
* **Built tables.** `vpp table build <recipe>.yaml` evaluates a model on a
  grid and writes its table (`model: grid`). The one recipe so far,
  `keel-section`, puts another fin section on a keel3d table's keel from 2D
  foil2d polars (`boats/tables/keel-ht35.yaml`: the HT35 fin). Speed is one
  of its dimensions, because the 2D differences depend on Re.
* **The cache.** The tables a build computes (hydrostatics, a mesh hull's
  waves, its windage) are kept in `.cache/iomcfd/vpp/` (`$IOMCFD_CACHE`),
  keyed by a hash of their inputs and of the code that computes them. A
  cached table reads back bit for bit, so it never changes a result; delete
  the directory at will.

## Boat files

```yaml
components:                       # in output order; "." = iomcfd.vpp.components
  keel:
    class: .keel.ParametricKeel   # the shape: geometry, mass, buoyancy
    mount: {host: hull, x: 0.50}  # hangs from the hull's bottom at x (fin root quarter chord)
    args: {draft: 0.42, mass: 2.5, fin: {section: naca0007, root_chord: 0.100, tip_chord: 0.080}, ...}
    forces:                       # the force model
      class: .keel.PolarFit
      args: {table: tables/keel-round-bulb.csv, max_leeway: 4.0}
  rudder:
    ...
    controls: {angle: balance}    # override a control: a role, or {role, default, lo, hi, options}
  windage:
    shape: hull                   # another part's shape (its mass and volume count once, there)
    forces: {class: .windage.OrcWindage, args: {...}}
```

* **Shape** (`class` + `args`, or `shape: <part>`): what the part is. It
  gives the mass items and buoyant volumes, and what other parts ask of it:
  a hull's floating `surface()` and `depth_at(x)`, an appendage's
  `planform()`. Exactly one shape has a surface.
* **Force model** (`forces`): its loads in the course frame
  (`components/base.py`), built with the shape. `covers` names other parts'
  physics its loads already hold (keel3d's double body: `hull.side_force`).
  `finish()` runs once the hydrostatics exist (the hull's static sinkage for
  the waves).
* **Controls** are what the solver sets, by role: `balance` (an unknown of
  the yaw balance: the rudder angle), `optimise` (searched for the greatest
  V_b: the sails' flat), `choice` (the fastest allowed option: the sail set)
  or `hold`. Keys are `<part>.<name>` (`rudder.angle`, `sails.flat`,
  `sails.set`); they are the polar's and race's columns and `point --hold`'s
  names. The solver knows only the roles, at most one of each.
* **Build** (`boat.py` BuildContext): parts are built on first request
  (`ctx.get`, `ctx.host`), so a part may use the ones it depends on (the
  rudder hangs from the hull and takes the keel's downwash). A geometry that
  differs from the table's is an error.

Each run writes these files:

| file | contents |
|---|---|
| `report.html` | one page that draws the files below; open it from the folder (it needs no server) |
| `race.csv` | best VMG angle, speed, heel, leeway and the controls, plus race time, per wind speed |
| `vmg.csv` | the best-VMG points in full, polar.csv's columns plus `leg` |
| `polar.csv`, `polar.png` | the polar: per point the state, the controls, each part's X, Y, Z, K, M, N, its `<part>_extrapolated` flag and its info (`hull_Rf`, `sails_aws`, …) |
| `response.csv` | each part's loads around every best-VMG state, one input varied at a time (below) |
| `hydro.csv` | the hydrostatic table as built: heel × M_ext × Z_ext → sink, trim, rm, wetted_area, lwl, bwl |
| `rates.csv`, `rates_summary.csv` | the change in race time per perturbation and wind; and weighted, in % and boat lengths |
| `mass.csv` | the mass budget |
| `summary.md` | a summary of the run |
| `boat.yaml`, `run.json` | the boat as run; the run's metadata |

* **run.json** holds what the build resolved: `course`, `wind`, the solver
  `settings` (defaults included), each part's shape and force-model classes
  and its controls after the boat file's overrides (`parts`), the `--set`
  overrides with the boat file's own values (`file_values`), and the time
  each stage took (`timings`).
* **response.csv** starts from each converged best-VMG point (vmg.csv) and
  varies one input with the others held: V_b (0.5–1.5 ×), heel (0–50°),
  leeway (0–6°), the optimised control over its bounds, the balance control
  ± 5° and each allowed option of the choice control, always including the
  solved value. `solver.evaluate` re-solves sinkage and trim at each sample.
  Off the solved state the boat is not in balance: these are the force
  models' own responses (`var` and `value` say what was varied).
* **report.html** embeds the run's files as written, so the page and its
  numbers can't drift apart. It leaves out the ORC sail-coefficient columns
  (`sails_CL`, `sails_CD`: copyright ORC); the CSVs keep them. Its sections:
  summary and polar, the boat file as run, the balance at one point, the
  force models, hydrostatics and the mass budget, the race with a race-time
  calculator, exchange rates, and the frames and symbols.
  `vpp report <boat | run dir>` writes it again, e.g. after a change to
  `vpp/report_template.html`; nothing is solved.

## How it works

* **Build** (`boat.py`; about 30 s the first time, 1–2 s from the cache):
  * the parts (shapes and force models);
  * the mass budget (`mass.py`): the shapes' items, then `mass.items`;
  * the hydrostatic table: sinkage, trim, RM_φ, wetted area and waterline
    length against heel, the other parts' pitch moment and their vertical
    force (`hydrostatics.Z_ext`: three layers, read back by a quadratic;
    one layer ignores the vertical forces), from the hull's surface clipped
    at the heeled waterline, plus the appendages' volumes
    (`hydrostatics.py`);
  * each force model's finish: the hull's Michell wave-resistance table
    (over V_b and trim at the static sinkage; with `michell-heeled` also
    over heel, each at its own static sinkage) and the windage's
    projected-area table (over heel and the wind's angle to the
    centreline).
* **Solve** (`solver.py`), nested:
  * **inner:** side force, roll and yaw balance give heel, leeway and the
    balance control (rudder angle) at a given V_b;
  * **middle:** the V_b at which drive equals drag;
  * **outer:** the optimised control (`sails.flat`) that gives the greatest
    V_b, for each allowed option of the choice control (`sails.set`).

  Tolerances are relative to the boat's force scale. A point is about
  0.25 s on the rung-0 boat and 0.5 s with the phase-2 tables.
* **Race** (`race.py`): the best VMG upwind and downwind at each wind speed,
  then the leg times plus a fixed time per tack and gybe. The default is
  uniform weights over the wind speeds; `wind.weights: file:<csv>` takes a
  club histogram instead.
* **Exchange rates** (`rates.py`): a drag step, RM_φ, each part's own rates
  (the keel fits' D0, k, slope and leeway) or else its loads +1 %, and the
  mass and its height. Each is re-timed at the baseline's best-VMG angles
  and flat. By the envelope theorem that is exact
  to first order; `--check` re-searches instead. The drag step also gives
  the V dR/dV the sails and hull really imply, for comparison with
  `racetime.VDRDV`.

## Components

`boats/canoe-placeholder.yaml` uses the models below; `canoe-placeholder-foil.yaml`
is the rung-0 boat (no CFD, no tables to compute: lifting-line keel,
`CanoeHull` with upright waves, `OrcWindage`, no vertical forces), which the
tests build.

| part | shape · force model | model | main limits |
|---|---|---|---|
| hull | `.hull.MeshHull` (an STL, or `canoe:` the canoe body as a mesh; `.hull.CanoeHull` = analytic) · `.hull.IttcMichell` | ITTC-57 × (1 + k) on the wetted area at the solved attitude, plus Michell thin-ship waves (`hullres.py`; within 0.3 % of the published Wigley Michell curve). `waves: michell-heeled`: the heeled sections' half-widths as the centreplane offsets, each heel at its static sinkage. Jones' side force at the keel line's centre of pressure | Michell exaggerates humps and hollows near Fn 0.3–0.4 compared with tank tests (about 2× in the wave slope). Thin-ship theory has no heel, so the heeled waves are an estimate; above 45° they are held and flagged. Fully turbulent friction (`cf_factor` brackets a laminar run) |
| keel (fin + bulb) | `.keel.ParametricKeel` · `.keel.PolarFit` | A grid table (`model: grid`) is read by `KeelGrid`: X, Y, Z, K, M, N over heel × leeway × V_b, interpolated as loads / V_b² by cubic splines, so the speed dependence is the CFD's. The boat's is `tables/keel-ht35-3d.csv` (keel3d ht35-keel@20261027-215521: HT35 7.25 %, 2° cant; φ 0–65°, β_Y −2 to 10°, V_b 0.5–3.7 m/s). A one-speed table (`tables/keel-round-bulb.csv`, the NACA 0007 fin) gives fits instead: S_h = S0 + a β_Y and D_h = D0 + k S_h² per heel, with the hull's side force and yaw included; friction scales with C_F(Re), the rest with q, and T_eff is kept. `vertical: delta`: keel3d's vertical force less its zero-leeway value. Or `.keel.FinAndBulb`: lifting line on the fin and the bulb's friction | keel3d is fully turbulent (Tu 0.5 %), so a section's laminar-flow gain (HT35's, custom-section) is not in it, and a double body (no waves; above about 36° of heel the deck edge is under the mirror plane). Outside a grid the loads are held at its edge and flagged `extrapolated`, as are points nearest a not-converged node (ht35-keel: 8–10° at φ ≤ 35°, stalled). A one-speed fit table holds its 25° fit above 25° (flagged). The zero-leeway vertical force is the double body's suction under its mirror plane, so it is dropped (an assumption: the hull's real squat is not modelled) |
| rudder | `.foils.ParametricFoil` · `.foils.LiftingLine` | lifting line (Helmbold slope) in the keel's elliptic downwash | no stall model |
| sails | `.sails.Rig` · `.sails.OrcSails` | ORC VPP Documentation 2026 §5: main and jib, flat depowering, effective height, the jib-downwind set standing in for a goose-winged jib (`sails_orc.py`) | full-scale coefficients at Re 10–100× an IOM's. Coefficients are copyright ORC, so **don't publish `vpp/data/orc2026_sails.yaml`** |
| windage | `shape: hull` · `.windage.ProjectedArea` (`.windage.OrcWindage` = ORC's areas) | C_D 0.816 (ORC Table 5.12) on the hull's area above the water projected normal to the apparent wind, at its centroid, the wind read at the centroid's height; tabulated over heel at each heel's static attitude | exact for the faceted hull's silhouette when every line along the wind crosses it at most twice (a cockpit or tumblehome counts hidden faces); the mesh must be the hull alone, since the rig's windage is in the sail model |

The hull's projected area at 30° heel with the wind 30° off the bow is
0.040 m², against ORC's formula's 0.079 m², with its centroid 0.041 m above
the water against ORC's 0.094 m. The canoe body's ends are narrow and its
topsides vertical, so its heeled windward side is lower than ORC's
full-beam estimate assumes. Real lines will differ.

## What phase 2 changed (2026-10-26)

Each change switched on with the ones above it already on (`vpp compare`,
weighted race time, uniform wind weights):

| change | boat-file switch | race time |
|---|---|---|
| the canoe body as a mesh (offsets from the mesh, upright waves) | `components.hull.class: .hull.MeshHull`, `args: {canoe: {}}` | −0.06 % |
| the heeled hull's waves | `components.hull.forces.args.waves: michell-heeled` | 0.00 % (−0.14 % at 2 m/s, +0.15 % at 5 m/s) |
| windage from the hull's projected area | `components.windage.forces.class: .windage.ProjectedArea` | −2.14 % (−1.1 % at 1.5 m/s to −4.2 % at 5 m/s) |
| the other parts' vertical force in the hydrostatics | `hydrostatics.Z_ext: [-4.0, 0.0, 4.0]` | +0.32 % |
| the keel's vertical force | `components.keel.forces.args.vertical: delta` | −0.05 % |
| all together | | −1.93 % (492.2 → 482.7 s) |

The HT35 fin (`tables/keel-ht35.csv`) is −0.045 % with the rung-0 hull and
windage (it reproduces the earlier section change to 1e-5) and −0.057 % with
all of the above.

## The 3D keel table (2026-10-28)

`boats/canoe-placeholder.yaml` now sails TWS 1.5–8 m/s (14 winds, to the A
rig's top wind of about 15 kn) with `solver.leeway_max: 8` (the fin starts to
stall at 6–8° upright), and its keel is the chosen one as a keel3d grid:
HT35 at 7.25 %, 100 → 80 mm, the round NACA 0011 bulb at 2° nose up
(`tables/keel-ht35-3d.csv`; [keel3d ht35-keel findings](../projects/keel3d/findings/ht35-keel.md)).

Against the old keel (NACA 0007, cant 0, `keel-round-bulb.csv`), both at the
8° limit, the weighted race time is 434.8 s against 430.4 s: **+1.0 %**
(+0.2 to +0.5 % per wind up to 5 m/s, +0.8 % at 5.5, +1.2 to +4.1 % at
6–8 m/s). It is
mostly the old table's extrapolation going away, not the keel: the old table
held its 25° heel fit at every heel above 25°, which overstated the heeled
keel's side force (at TWS 7 m/s, 56° of heel, 3.32 N at 2.3° of leeway
against the grid's 2.61 N at 4.3°). It was flagged `keel_extrapolated` at
every upwind VMG point from 2.5 m/s; the grid at none. Below 25° of heel the
grid's drag at low speed (the CFD's own Re dependence against ITTC-57
scaling of a 1 m/s fit) and the cant's upright drag cost 0.2–0.4 %. Both
tables are fully turbulent, so the HT35 section's laminar gain is in
neither. At 7.5–8 m/s the polar has no equilibrium at β_TW 30–40°, and
upwind the boat sails at 56–61° of heel with 15–26° of rudder (no rudder
stall model): the A rig is past its range there.

## Inputs to replace

* **Component masses and CGs.** Only the bulb and fin come from the CFD
  designs.
* **Wind and race settings:** the A-rig wind range, the height wind is
  measured at, the profile exponent, leg length, and tacks and gybes with
  their time cost.
* **The hull.** The canoe body is keel3d's, until the Alioth lines arrive
  (`components.hull.args: {stl: hulls/<name>.stl, scale: 0.001, ...}`). Its
  topsides (vertical to a flat deck) set the windage.

## Verification

* **Unit tests:** `tests/test_vpp_*.py` cover frames and signs, toy boats
  with closed-form equilibria and rates, hydrostatics against Wigley, canoe
  and box-barge results, Michell against Wigley, the ORC tables, the keel
  fits and an end-to-end build (race time pinned on the rung-0 boat);
  `test_vpp_build.py` the builder; `test_vpp_tables.py` the phase-2 tables:
  a box's sinkage under a vertical force (Z/(ρgA)) and its projected areas,
  heeled offsets (B / (2 cos φ) for a box), the mesh hull's keel line against
  the analytic canoe, a grid keel against its table, the keel's vertical
  force and the cache. Upright, the mesh's half-widths differ from the old
  max |y| by up to 5 µm, because the canoe mesh's triangulation isn't
  exactly symmetric.
* **Python-VPP cross-check:** `PYVPP_PATH=<checkout> uv run pytest -m external -s
  tests/test_vpp_pyvpp.py` runs Python-VPP's YD-41 forces (commit 141ea66) in
  this solver with the yaw balance off.
  * **Run 2026-10-24:** 12 points at TWS 8 and 16 kn, TWA 45/90/150°, sail
    sets J1, A2 and A5.
  * **Same trim (their flat and reef):** V_b matches to the printed 0.001 kn,
    heel and leeway to 0.01°.
  * **Flat free:** the same, except at two points where Python-VPP's hard heel
    bound is active (21.5° with a kite, TWS 16 kn at 90°). There this solver,
    which only flags heel, is 0.2 kn faster at 30° of heel.
