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
uv run iomcfd vpp point canoe-placeholder --tws 3 --twa 45   # one equilibrium, each part's forces
uv run iomcfd vpp point canoe-placeholder --tws 3 --twa 45 --hold sails.flat=0.8
uv run iomcfd vpp hydro canoe-placeholder       # mass budget, RM and GZ against heel
uv run iomcfd vpp compare canoe-placeholder canoe-placeholder-foil      # two boats
uv run iomcfd vpp compare canoe-placeholder --set-b components.hull.forces.args.cf_factor=0.8
uv run iomcfd vpp sweep canoe-placeholder --vary components.keel.forces.args.table=tables/a.csv,tables/b.csv
uv run iomcfd vpp export-table keel3d bulb-section@20261019-203823 --select bulb_aspect=1.0 ... \
    --out boats/tables/keel-round-bulb.csv      # one keel3d design as a table for a boat file
```

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
| `race.csv` | best VMG angle, speed, heel, leeway and flat, plus race time, per wind speed |
| `rates.csv` | the change in race time per perturbation and wind |
| `polar.csv`, `polar.png` | the polar |
| `vmg.csv` | the best-VMG points with every component's forces |
| `mass.csv` | the mass budget |
| `summary.md` | a summary of the run |
| `boat.yaml`, `run.json` | the boat as run, and the run's metadata |

## How it works

* **Build** (`boat.py`, about 5 s):
  * the parts (shapes and force models);
  * the mass budget (`mass.py`): the shapes' items, then `mass.items`;
  * the hydrostatic table: sinkage, trim, RM_φ, wetted area and waterline
    length against heel and the sails' pitch moment, from the hull's surface
    clipped at the heeled waterline, plus the appendages' volumes
    (`hydrostatics.py`);
  * each force model's finish: the hull's Michell wave-resistance table over
    V_b and trim at the static sinkage.
* **Solve** (`solver.py`), nested:
  * **inner:** side force, roll and yaw balance give heel, leeway and the
    balance control (rudder angle) at a given V_b;
  * **middle:** the V_b at which drive equals drag;
  * **outer:** the optimised control (`sails.flat`) that gives the greatest
    V_b, for each allowed option of the choice control (`sails.set`).

  Tolerances are relative to the boat's force scale. A point is about 0.2 s.
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

## Components (rung 0)

| part | shape · force model | model | main limits |
|---|---|---|---|
| hull | `.hull.CanoeHull` · `.hull.IttcMichell` | ITTC-57 × (1 + k) on the wetted area at the solved attitude, plus Michell thin-ship waves at the upright static sinkage and trim (`hullres.py`; within 0.3 % of the published Wigley Michell curve) | Michell exaggerates humps and hollows near Fn 0.3–0.4 compared with tank tests (about 2× in the wave slope). Heel is ignored in the waves. Fully turbulent friction (`cf_factor` brackets a laminar run) |
| keel (fin + bulb) | `.keel.ParametricKeel` · `.keel.PolarFit` | keel3d fits from a table: S_h = S0 + a β_Y and D_h = D0 + k S_h² per heel, with the hull's side force and yaw included; friction scales with C_F(Re), the rest with q, and T_eff is kept. Or `.keel.FinAndBulb`: lifting line on the fin and the bulb's friction (`boats/canoe-placeholder-foil.yaml`) | keel3d is at 1 m/s and heels 0 and 25° only: points above 25° hold the 25° fit and are flagged `extrapolated` |
| rudder | `.foils.ParametricFoil` · `.foils.LiftingLine` | lifting line (Helmbold slope) in the keel's elliptic downwash | no stall model |
| sails | `.sails.Rig` · `.sails.OrcSails` | ORC VPP Documentation 2026 §5: main and jib, flat depowering, effective height, the jib-downwind set standing in for a goose-winged jib (`sails_orc.py`) | full-scale coefficients at Re 10–100× an IOM's. Coefficients are copyright ORC, so **don't publish `vpp/data/orc2026_sails.yaml`** |
| windage | `shape: hull` · `.windage.OrcWindage` | ORC Table 5.12 on the topsides, heeled | |

Another fin section on the keel3d keel (2D foil2d polars applied as the
change in profile drag and angle at equal fin lift, `components/section.py`)
is no longer a boat-file switch: it is to become a table of its own, built
from the keel3d table and the polars, so that a section comparison is two
boats. Until then it is only available in code.

## Inputs to replace

* **Component masses and CGs.** Only the bulb and fin come from the CFD
  designs.
* **Wind and race settings:** the A-rig wind range, the height wind is
  measured at, the profile exponent, leg length, and tacks and gybes with
  their time cost.
* **The hull.** The canoe body is keel3d's, until the Alioth lines arrive.

## Verification

* **Unit tests:** `tests/test_vpp_*.py` cover frames and signs, toy boats
  with closed-form equilibria and rates, hydrostatics against Wigley, canoe
  and box-barge results, Michell against Wigley, the ORC tables, the keel
  fits and an end-to-end build.
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
