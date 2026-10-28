# ht35-keel: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/ht35-keel/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study is not a selection: it simulates the
chosen keel (HT35 at 7.25 %, 100 -> 80 mm, round NACA 0011 bulb at 2° nose
up) over the heels, leeways and boat speeds the VPP sails, and exports the
result as the VPP's keel table (`boats/tables/keel-ht35-3d.csv`, a grid
table read by `KeelGrid`). Project: [README](../README.md).

## Run 20261027-215521 (2026-10-28, git 1663664, GCP, 276 cases)

**Setup.**
* The keel: fin `file:ht35-t0725.dat` (custom-section's recommendation),
  100 -> 80 mm (λ 0.8, 90 mm mean chord), round NACA 0011 bulb (2380 g,
  343 × 37.7 mm) at 2° nose up ([bulb-section](bulb-section.md),
  [bulb-cant](bulb-cant.md)); keel3d's canoe body, 420 mm draft.
* Sweep: heel φ 0, 10, 20, 35, 50, 65° × leeway β_Y −2, 0, 1, 2, 3, 4, 6,
  8, 10° × V_b 0.5, 0.9, 1.5, 2.4, 3.7 m/s on the medium mesh (270 cases),
  plus 6 fine cases (φ 0 / 35 / 65 × β_Y 0 / 4°, 1.5 m/s).
* The range comes from a baseline VPP run of canoe-placeholder with the old
  keel table (runs/vpp/canoe-placeholder/20261027-213633, NACA 0007, cant 0,
  TWS 1.5-8 m/s, leeway limit 10°): its polar solved V_b 0.55-3.63 m/s,
  heel 0.2-63° and leeway −0.6 to 5.2°; its best-VMG points V_b 0.55-3.10,
  heel 0.3-62.5°, leeway −0.1 to 2.8°.
* kOmegaSST with Spalding wall functions, fully turbulent, Tu 0.5 % at every
  speed (with wall functions the inflow Tu only sets the freestream k and ω).
  Double body (mirror plane at the waterline), no trim or sinkage.
* c3d-standard-16 Spot, 8 ranks per case, 9 at a time; 16.7 h of job time,
  no preemptions.

**Outcome.** 248 ok, 28 not converged (all at β_Y 8 and 10°, φ 0-35°: they
ran the 3000-iteration limit and report the window mean), 0 failed.

### Conclusions

1. **The forces are clean and symmetric where the boat sails (β_Y ≤ 6°).**
   Upright, S_h(−2°) = −0.996 to −0.999 × S_h(+2°) at all five speeds, and
   D_h(−2°) equals D_h(+2°) to 3 digits. S_h rises monotonically with
   leeway up to 6° at all 30 heel × speed combinations, and D_h rises with
   |β_Y| at all of them. At 0° leeway S_h is under 0.1 N at φ ≤ 50° (1.5 m/s;
   0.29 N at 65°, where the heeled hull is asymmetric). Confidence: high.
2. **The fin starts to stall between 6 and 8° upright, later as the boat
   heels.** At 1.5 m/s, the side-force slope dS_h/dβ_Y and the drag:

   | φ | 0-4° | 4-6° | 6-8° | 8-10° | D_h 6° → 8° | L/D 6° | L/D 8° |
   |---|---|---|---|---|---|---|---|
   | 0 | 3.66 | 3.13 | 2.65 | 1.40 N/° | 2.62 → 4.65 N | 8.0 | 5.6 |
   | 10 | 3.58 | 3.11 | 1.44 | 1.55 | 2.50 → 4.25 | 8.2 | 5.5 |
   | 20 | 3.29 | 2.92 | 1.58 | 1.17 | 2.38 → 3.97 | 8.0 | 5.6 |
   | 35 | 2.59 | 2.38 | 1.98 | 0.88 | 2.16 → 3.09 | 7.0 | 6.1 |
   | 50 | 1.70 | 1.66 | 1.54 | 1.29 | 2.00 → 2.38 | 5.1 | 5.6 |
   | 65 | 0.88 | 0.91 | 0.91 | 1.02 | 1.99 → 2.22 | 2.8 | 3.4 |

   Upright the drag rises 77 % from 6 to 8° while the side force rises
   25 %; S_h/D_h peaks near 6°. At 50-65° the fin is unloaded by the heel
   (and the hull carries more of the side force), so nothing stalls by 10°.
   Every non-converged case is in the stalled corner (β_Y 8-10°,
   φ 0-35°): the separated flow is unsteady and steady RANS doesn't settle.
   Confidence: medium for where it starts (steady RANS, fully turbulent,
   medium mesh; the fine checks stop at 4°); low for the 8-10° numbers.
3. **The VPP never needs the stalled corner.** The baseline VPP's points
   reach 5.2° of leeway (polar) and 2.8° (best VMG); the 8° limit
   (`solver.leeway_max`, set after this run) keeps solutions out of it.
   (The VPP result with this table is below.)
4. **The keel's coefficients depend on the speed, as Re: the side force
   rises 9 % and the 0° drag falls 36 % per V_b² from 0.5 to 3.7 m/s.**
   Upright, S_h(3°)/V_b² is 4.67, 4.81, 4.94, 5.02 and 5.08 N s²/m² at
   0.5, 0.9, 1.5, 2.4 and 3.7 m/s (+9 %); at 35° heel +9 % too. D_h(0°)/V_b²
   falls 0.831 → 0.533 (−36 %), as skin friction does: a flat plate's
   C_F ∝ Re^−0.2 gives −33 %. The old table had one speed (1 m/s) and
   scaled to others by C_F(Re) on the friction only; the grid table now
   carries the CFD's own Re dependence, lift included. Confidence: medium
   (the fin's y+ grows with speed; see Compromises).
5. **Heel takes the side force off the fin in steps that don't depend on the
   speed.** dS_h/dβ_Y (0-4° fit) at 1.5 m/s: 3.69, 3.59, 3.30, 2.59, 1.69
   and 0.89 N/° at 0, 10, 20, 35, 50 and 65°; at 0.9 m/s the same ratios
   to upright (1, 0.98, 0.90, 0.70, 0.46, 0.24). The effective draft T_eff
   falls from 0.40 to 0.21 m. The roll lever z_clr = −K/S_h (moments about
   the bow at the waterline) grows from 0.181 to 0.354 m (3°, 1.5 m/s, φ 0
   to 65): it is a lever, not a point on the keel, since the heeled fin's
   lift has a vertical part acting off the centreline. The spanwise centre
   of pressure stays at 0.44 of the span at every speed (upwind highlight,
   35° / 3°: 0.441-0.442). Confidence: high (all speeds agree).
6. **Against the old table (NACA 0007, cant 0, bulb-section@20261019-203823)
   the new keel makes 3-4 % more side force for about 1 % more drag at
   1 m/s.** Upright, interpolated to 1 m/s in log V: S_h(2°) 3.24 vs 3.13 N
   (+3.4 %), S_h(4°) 6.39 vs 6.12 N (+4.4 %); D_h(0°) 0.715 vs 0.707 N
   (+1.0 %), D_h(4°) 0.882 vs 0.875 N (+0.8 %). Two changes at once (HT35
   for NACA 0007, 2° cant) and an interpolation, so medium confidence.
7. **The medium mesh is good to 0.6 % in side force and 5 % in drag.** Fine
   against medium at 1.5 m/s: S_h within 0.6 % at 4° (3 heels); D_h −0.4
   to +0.1 % at 0°, −0.6, −2.3 and −5.0 % at 4° (φ 65, 35, 0); the fin's
   own drag at 4° upright −11.9 %. So the medium mesh overstates the
   induced/pressure part of the fin's drag at leeway, most upright.
   Confidence: high at 1.5 m/s; unchecked at other speeds.

### Evidence

* `report/summary.md`, `report/mesh_check.md`, `report/highlights.md`,
  `report/polar_fits.csv`; the numbers above recomputed from
  `results.csv` (medium rows).
* Mesh check (1.5 m/s, change fine vs medium):

  | φ | β_Y | D_h medium | D_h fine | S_h medium | S_h fine | fin drag |
  |---|---|---|---|---|---|---|
  | 0 | 0 | 1.465 | 1.459 (−0.4 %) | 0.024 | −0.001 | −1.7 % |
  | 35 | 0 | 1.509 | 1.510 (+0.1 %) | −0.084 | −0.021 | +0.6 % |
  | 65 | 0 | 1.735 | 1.733 (−0.1 %) | 0.294 | 0.293 | +0.4 % |
  | 0 | 4 | 1.846 | 1.753 (−5.0 %) | 14.65 | 14.73 (+0.6 %) | −11.9 % |
  | 35 | 4 | 1.759 | 1.718 (−2.3 %) | 10.26 | 10.24 (−0.2 %) | −5.8 % |
  | 65 | 4 | 1.830 | 1.819 (−0.6 %) | 3.833 | 3.810 (−0.6 %) | −1.2 % |

* Upwind highlight (φ 35°, β_Y 3°, medium): D_h 0.232, 0.659, 1.641,
  3.816, 8.358 N and S_h 0.813, 2.701, 7.744, 20.12, 48.36 N at 0.5, 0.9,
  1.5, 2.4, 3.7 m/s; z_clr −0.234 to −0.233 m; eta_cp 0.441-0.442.
* Not converged (heel: speeds): β_Y 8°: φ 0 (0.5, 0.9, 1.5, 3.7), φ 10
  (1.5, 2.4, 3.7), φ 20 (0.9, 1.5, 2.4, 3.7); β_Y 10°: φ 0 and 10 (all
  five), φ 20 (0.9-3.7), φ 35 (0.9, 1.5, 2.4).
* The hull's drag at 0° leeway, 1.5 m/s: 0.708, 0.706, 0.712, 0.765, 0.859,
  0.982 N at φ 0-65°: it rises once the deck edge nears the mirror plane.
* y+ (median over cases): fin mean 3.4, 5.7, 8.9, 13.3, 19.2 at 0.5-3.7
  m/s (max 31-176); bulb mean 4.3-26; hull mean 12-69.

### The VPP keel table

`uv run iomcfd vpp export-table keel3d ht35-keel@20261027-215521
--select mesh=medium --model grid --out boats/tables/keel-ht35-3d.csv`:
270 rows (6 heels × 9 leeways × 5 speeds), X less the hull's 0° drag, K/M/N
at each case's centre of lateral resistance, Zv/Mv the vertical force less
its 0° value; `ext` = 1 on the 28 non-converged rows, which `KeelGrid` flags
by nearest node (so a VPP point within about 1° of 8° at φ ≤ 20° is flagged
extrapolated). Header `fit.a` (dS_h/dβ_Y per heel at V_ref 0.9 m/s, for the
rudder's downwash): 1.29, 1.26, 1.17, 0.90, 0.60, 0.32 N/°.
`boats/canoe-placeholder.yaml` now uses it (fin `file:ht35-t0725.dat`, bulb
cant 2°, `vertical: delta`, `solver.leeway_max: 8`).

### The VPP with this keel

`uv run iomcfd vpp run canoe-placeholder` (run
runs/vpp/canoe-placeholder/20261028-144458, report.html there): TWS 1.5-8
m/s, leeway limit 8°. `vpp compare` against the old keel (fin naca0007,
cant 0, `tables/keel-round-bulb.csv`, PolarFit), both at the 8° limit:

| TWS m/s | 1.5 | 2 | 3 | 4 | 4.5 | 5 | 5.5 | 6 | 6.5 | 7 | 7.5 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| race time, new vs old | +0.23 | +0.33 | +0.25 | +0.32 | +0.37 | +0.50 | +0.80 | +1.21 | +1.78 | +2.80 | +4.08 | +2.98 % |

Weighted (uniform over 14 winds): 434.8 s against 430.4 s, **+1.0 %
(4 boat lengths)**.

8. **The new table removes the keel's extrapolation, and that, not the
   keel, is most of the +1.0 %.** The old table (1 m/s, heels 0 and 25°)
   held its 25° fit above 25° and was flagged `keel_extrapolated` at every
   upwind VMG point from 2.5 m/s and at 101 of 196 polar points; the new
   one at none. At TWS 7, β_TW 36° the old keel gives S_h 3.32 N at 2.3° of
   leeway and 56° of heel; the grid gives 2.61 N at 4.3°: the heeled keel
   makes less side force than the 25° fit, so the boat makes more leeway
   (VMG up to 4.2° against 2.8°) and points lower. The upwind loss grows
   with the heel: +0.2 to +0.5 % at TWS ≤ 4.5 (φ ≤ 36°), +1.6 to +5.2 % at
   6-8 m/s (φ 48-61°). Confidence: medium (the 50-65° CFD is itself rough, double
   body with the deck under the mirror plane).
9. **Below 25° of heel, where both tables are CFD, the new keel is 0.2-0.4 %
   slower, from its drag at low speed.** At TWS 1.5 m/s upwind (V_b 0.78,
   φ 12°) both make 1.91 N of side force, the new keel at 2.06° (old 2.18°)
   for 0.267 N of drag against 0.262 N (+1.8 %, at a slightly lower V_b).
   The grid carries the CFD's own rise in drag coefficient at low Re
   (the double body's D_h(0°)/V_b² +14 % from 0.9 to 0.5 m/s); the old fit scaled its 1 m/s
   friction by ITTC-57. Downwind (upright, 0°) +0.0 to +0.5 %: the 2° cant's
   upright drag (bulb-cant: +1.2 mN at 1 m/s) and the thicker section.
   Confidence: medium (it is the difference of two models, not of two keels
   in one model).
10. **The HT35 section's advantage is not in this table.** custom-section
    recommended HT35 at 7.25 % for its laminar flow: 0.66 / 0.38 % of race
    time at Tu 0.1 %, 0.34 / 0.20 % at Tu 1 %, break-even at 2 % (foil2d,
    transitional). This run is fully turbulent, as the old table is, so
    neither VPP time includes it; the race-time difference above is no
    verdict on the section.
**Update, same day: trim tables extended** (VPP run 20261028-175817;
[docs/vpp.md](../../../docs/vpp.md#the-3d-keel-table-2026-10-28)). The
hydrostatics stopped at 8.2° of trim and the waves at 4° and 3 m/s, so
downwind from 5 m/s the VPP held them. Extended, the weighted race time is
439.0 s (434.8 s): downwind +0.9 % at 5 m/s to +13.8 % at 8 m/s, upwind
unchanged to 7 m/s. Dead-downwind trim: 0.7° bow down at 1.5 m/s, 2.8° at
4, 4.5° at 5, 6.6° at 6, 7.4-8.0° at 6.5-7.5, 17° at 8 (bow buried). The
keel comparison in the table above predates it.

12. **2° of bulb cant stays about right once the trim is counted, on these
    inputs.** With Gilbert's rule (zero bulb incidence at cant = trim +
    β_Y sin φ) and the run's VMG points, the ideal cant rises with the wind
    on both legs: upwind 1.5° (1.5 m/s) to 3.7° (4) to 7.2° (7), downwind
    0.7° to 2.8° to 7.4°. Pricing the misalignment with bulb-cant's
    upright drag curve (0.30 mN per deg² at 1 m/s, × V_b²) and this run's
    drag exchange rates per wind and leg, the race-time cost over TWS
    1.5-7 m/s is 0.101, 0.065, 0.042, 0.032, 0.036 and 0.052 % at 0-5° of
    cant (best 3°); over 1.5-5 m/s it is best at 2° (0.009 %, 3°: 0.014 %).
    The optimum moves by about 1° with the wind range and is worth about
    0.01 % of race time. Confidence: low. The trims are the placeholder
    hull's and masses'; the drag curve is measured only to 4° and at 1 m/s
    with no leeway; the bulb's side force at heel (bulb-cant: +0.5 % at 2°,
    +1.2 % at 4°, which favours more cant upwind) is left out; and the VPP's
    keel table has no trim, so the VPP itself can't price cant.

13. **The top of the wind range is past the A rig.** At TWS 7.5-8 the polar
    has no equilibrium at β_TW 30-40° (5 points; the old keel solved
    them), and the upwind VMG points sail at 56-61° of heel with the
    rudder at −15 to −26° (old −12 to −26°). The rudder has no stall model,
    so those points are optimistic for both keels.

### Decisions

* The boat file's keel is this table; the old ones (`keel-round-bulb.csv`,
  `keel-ht35.*`) stay for the docs, the tests and `vpp compare`.
* `solver.leeway_max` 10 → 8° (user, after seeing the stall cost): the
  table's 8-10° nodes are kept, flagged, as the spline's support above 6°.
* The 10° column cost about a fifth of the compute (it is 17 of the 28
  non-converged cases, 1.6-1.9 h each against a median of 17.6 min). A
  rerun or a sister keel should stop at 8°.
* The race time moves +1.0 % with this table (conclusions 8-9). It replaces
  a table that was extrapolated over half the polar, so the new number is
  the one to compare designs against; the old one was optimistic in wind.

### Assumptions

* Fully turbulent at Tu 0.5 % at every speed. A real fin at Re 4·10⁴ to
  3·10⁵ (chord 90 mm) may have laminar runs and laminar separation, which
  would cut the friction and could start the stall earlier. **Not
  verified** here; bulb-section's transition correction (fin 0.80, bulb
  0.52 of the friction, NACA 0007) is not applied.
* Double body: no waves, no free surface at the hull. Above about 36° of
  heel the canoe body's deck edge is under the mirror plane, so the 50 and
  65° cases model a hull that is not there; at V_b above about 1.5 m/s the
  real hull makes waves the mirror plane can't. The VPP adds the hull's own
  wave resistance (Michell) and takes the hull's 0° drag out of the keel
  table, but the hull's influence on the fin at speed is the double body's.
* No trim, no sinkage: the keel is at the design waterline at every speed.
* The keel geometry as built by keel3d (fin at x = 0.50 m, 420 mm draft,
  bulb centre of mass under the quarter chord); not measured on a boat.

### Compromises

* Medium mesh everywhere, fine only at 1.5 m/s and β_Y 0 / 4°: the 5 % drag
  error at 4° upright (12 % of the fin's own drag) goes into the table as
  is, and the mesh error at other speeds is not known.
* One near-wall spacing for a 7× range of speed: the fin's mean y+ runs
  from 3.4 to 19, through the buffer layer, where Spalding's wall function
  is least accurate. Part of conclusion 4's Re trend could be y+.
* 28 non-converged cases are window means of unsteady flow; their spread
  wasn't recorded in the table.
* Steady RANS for the stall; no time-accurate check.

### Learnings

* **Physics.** The canted, round bulb on a tapered fin carries the spanwise
  loading close to elliptic (eta_cp 0.44) at every speed and heel; the
  bulb end-plates the fin, so the tip vortex forms at the junction (the
  35° / 4° / 2.4 m/s streamlines, viz/streamlines.png of that case).
* **Solver.** Steady cases converge in a median of 472 iterations; the
  stalled ones never do (3000). The `bounding k` warnings (up to 288 per
  check) flag them early: a run could stop a stalled case sooner and keep
  its window mean.
* **Workflow.** `vpp export-table --model grid` needs one row per node,
  hence `--select mesh=medium`; the fine cases are for the mesh check only.
* **Compute and cost.** 137.4 case-hours (median 17.6 min, mean 29.9, max
  113.7 min per case), 16.7 h of wall time at 9 parallel, 0 preemptions;
  roughly $30 of Spot time (an estimate from the hours, not from billing).

### Open questions and next steps

* Do the stall and the friction change with a transition model (foil2d's
  γ-Re_θ on HT35 7.25 %, or a laminar-run correction like bulb-section's)?
  Without it the VPP can't show the section's gain (conclusion 10).
* The top winds: a B rig, or a rudder stall model, before trusting
  TWS 7-8 m/s upwind (conclusion 13).
* Bulb cant against trim (conclusion 12): with the real hull lines and
  masses, re-run the estimate; if the trims stay large, a keel3d sweep of
  bulb incidence (bulb_cant −6 to +4°, upright, at the downwind speeds
  1.2-2.4 m/s) would replace the extrapolated drag curve.
* A time-accurate check of one stalled case (φ 0, β_Y 8°, 1.5 m/s): the
  steady window mean against a pimpleFoam average.
* Fine mesh at 0.5 and 3.7 m/s (β_Y 4°, φ 0 and 35) to bound the y+ effect
  on the Re trend.
* Highlights for a next run: `stall` as now (it shows where separation
  starts); add `re` = φ 0, β_Y 4°, compare speed, views
  surface_cp_starboard and wake_slice, to look at the Re effect.
