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
uv run iomcfd vpp point canoe-placeholder --tws 3 --twa 45   # one equilibrium, each component's forces
uv run iomcfd vpp hydro canoe-placeholder       # mass budget, RM and GZ against heel
uv run iomcfd vpp compare canoe-placeholder --set-b keel.select.bulb_aspect=1.5
uv run iomcfd vpp sweep canoe-placeholder --variant "keel.select.bulb_aspect=1.5;keel.select.bulb_bottom=6.0"
```

* **Boat files.** A boat is `boats/<name>.yaml`, and
  `boats/canoe-placeholder.yaml` documents every key. Private boats, such as
  licensed hull lines, go in `boats/private/`, which git ignores.
* **Overrides.** `--set a.b=v` overrides any entry by its dotted path.
* **CFD runs.** Point the boat file at a keel3d run as `<study>@<run id>`.
  The run is looked up in `$IOMCFD_SOURCE_RUNS`, then in `runs/`. Example:
  `IOMCFD_SOURCE_RUNS=../bulb-design/runs`.

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
  * the hydrostatic table: sinkage, trim, RM_φ, wetted area and waterline
    length against heel and the sails' pitch moment, from the hull STL
    clipped at the heeled waterline (`hydrostatics.py`);
  * the mass budget (`mass.py`);
  * the hull's Michell wave-resistance table over V_b and trim;
  * the components.
* **Solve** (`solver.py`), nested:
  * **inner:** side force, roll and yaw balance give heel, leeway and rudder
    angle at a given V_b;
  * **middle:** the V_b at which drive equals drag;
  * **outer:** the `flat` that gives the greatest V_b, and the faster of the
    two sail sets.

  Tolerances are relative to the boat's force scale. A point is about 0.2 s.
* **Race** (`race.py`): the best VMG upwind and downwind at each wind speed,
  then the leg times plus a fixed time per tack and gybe. The default is
  uniform weights over the wind speeds; `wind.weights: file:<csv>` takes a
  club histogram instead.
* **Exchange rates** (`rates.py`): each perturbation is re-timed at the
  baseline's best-VMG angles and flat. By the envelope theorem that is exact
  to first order; `--check` re-searches instead. The drag step also gives
  the V dR/dV the sails and hull really imply, for comparison with
  `racetime.VDRDV`.

## Components (rung 0)

| part | model | main limits |
|---|---|---|
| hull | ITTC-57 × (1 + k) on the wetted area at the solved attitude, plus Michell thin-ship waves at the upright static sinkage and trim (`hullres.py`; within 0.3 % of the published Wigley Michell curve) | Michell exaggerates humps and hollows near Fn 0.3–0.4 compared with tank tests (about 2× in the wave slope). Heel is ignored in the waves. Fully turbulent friction (`hull.cf_factor` brackets a laminar run) |
| keel (fin + bulb) | keel3d fits: S_h = S0 + a β_Y and D_h = D0 + k S_h² per heel, with the hull's side force and yaw included; friction scales with C_F(Re), the rest with q, and T_eff is kept. Or lifting line (`keel.model: foil`) | keel3d is at 1 m/s and heels 0 and 25° only: points above 25° hold the 25° fit and are flagged `extrapolated` |
| fin section | another section on the keel3d keel (`keel.section`): 2D foil2d polars applied as the change in profile drag and angle at equal fin lift (`section.py`) | polars at their own chord (100 mm in custom-section); linear between computed angles |
| rudder | lifting line (Helmbold slope) in the keel's elliptic downwash | no stall model |
| sails | ORC VPP Documentation 2026 §5: main and jib, flat depowering, effective height, the jib-downwind set standing in for a goose-winged jib (`sails_orc.py`) | full-scale coefficients at Re 10–100× an IOM's. Coefficients are copyright ORC, so **don't publish `vpp/data/orc2026_sails.yaml`** |
| windage | ORC Table 5.12 on the topsides, heeled | |

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
