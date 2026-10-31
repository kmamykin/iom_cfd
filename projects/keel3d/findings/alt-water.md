# alt-water: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/alt-water/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study is the water part of the alternative
hull (`iom-alternative`, private STL) with its keel. Each heel is cut at its
static waterline and mirrored, which gives the VPP's keel table
(`boats/tables/keel-ht35-alt.csv`) and the hull's form factor
(`boats/tables/hull-k-alt.csv`). Its parameters were settled by
[alt-water-scout](alt-water-scout.md). The same keel on keel3d's canoe body
is [ht35-keel](ht35-keel.md). The air part is
[windage/alt-air](../../windage/findings/alt-air.md). Project:
[README](../README.md).

## Run 20261030-155529 (2026-10-30, git 2c93e9e-dirty, GCP, 284 cases)

**Setup.**

* **Hull.** `file:private/iom-alternative.stl` at each heel's static
  attitude (`vpp hydro iom-alternative --zip`, M_ext 0, Z_ext 0), cut at
  z = 0 and mirrored. It is a double body, with no waves.
  * φ 0, 10, 20, 30, 40, 50, 60°.
  * Sink −2.15 to −14.73 mm, trim −0.001 to 0.225° bow down.
* **Keel.** iom-alternative's keel, as in ht35-keel:
  * fin HT35 at 7.25 %, 100 → 80 mm, fin_x 0.544;
  * round NACA 0011 bulb at 2°.
  The fin root follows the STL's keel line, so the fin span is 322.7 mm
  (328.7 mm on the canoe body).
* **Sweep.**
  * β_Y −2, 0, 1, 2, 3, 4, 6, 8° × V_b 0.5, 0.9, 1.5, 2.4, 3.6 m/s.
  * Keel mesh medium, hull_refine 1 (hull cells 2.8/1.4 mm), as the scout
    settled.
  * Checks:
    * hull_refine 2 at φ 60°;
    * the keel's fine mesh at φ 30°, both at β_Y 0 and 4°, 1.5 m/s.
* **Solver.** kOmegaSST with Spalding wall functions, fully turbulent,
  Tu 0.5 %, drift-checked convergence. c3d-standard-16 Spot, 8 ranks.
* **History.** First run of this study.

**Outcome.** 270 ok, 14 not converged (window means kept), 0 failed.

* The 14 are all stall cases:
  * φ 0°: β_Y 6° at 1.5-3.6 m/s and β_Y 8° at every speed;
  * φ 10° and 30°: β_Y 8° at 1.5-3.6 m/s.
* φ 20° and 40-60° converge at 8°.

### Conclusions

1. **On this hull the fin behaves as on the canoe body up to φ 30°.**
   * Side force: at 1.5 m/s, S_h(4°) is 14.72 / 14.33 / 13.10 N at φ 0 /
     10 / 20°. The canoe body gives 14.65 / 14.25 / 13.14 N (+0.4 / +0.6 /
     −0.3 %).
   * Leeway drag: D_h(4°) − D_h(0°) is 0.373 / 0.369 / 0.337 N, against
     0.381 / 0.352 / 0.336 N.
   * The 1.8 % shorter fin doesn't show in the side force.
   * Confidence: high for side force; medium for drag (the two runs'
     meshes and attitudes differ too).
2. **From φ 40° the hull takes side force away.** The canoe-body table,
   interpolated in heel, overstates this run's S_h:
   * by 5.7 / 9.5 / 16.4 % (median) at φ 40 / 50 / 60°;
   * by up to 31 % at φ 60°.
   It puts the centre of lateral resistance 31 / 51 / 119 mm (median) too
   far forward. At β_Y 0 the heeled hull pushes to leeward: S_h −0.41 N at
   φ 40°, 1.5 m/s.
   The `deck` highlight shows no jump between 40 and 60°: S_h(3°) at
   1.5 m/s falls smoothly, 8.39 / 6.27 / 4.35 / 2.70 N at φ 30 / 40 / 50 /
   60°, and D_h stays within 2.6 %.
   Confidence: medium. Part of the 30-40° change may be the canoe body's
   interpolation between its 35° and 50° heels.
3. **A canoe-body table plus 39 cases of this run predicts the rest within
   1 % in side force at φ ≤ 30°, β_Y ≤ 4°.** This tests option 3 of
   decoupling hull and keel: a full baseline table plus sparse corrections.
   * The sparse set is φ 0 / 20 / 30 / 40 / 60° × β_Y 0 / 2 / 4 / 6° ×
     V_b 0.9 / 2.4 m/s: 39 cases, 14 % of 284.
   * The correction:
     * S_h and N get an offset plus a slope in β_Y; D_h gets offset + c β_Y².
     * They are fitted over β_Y 0-4° at each sparse heel and averaged over
       the two speeds (/V_b²), then made linear in heel.
   * Errors on the 230 held-out cases at φ ≤ 30°, β_Y ≤ 4°:
     * S_h: median ≤ 0.4 %, max 0.9 %;
     * leeway and keel drag: median ≤ 0.8 %, max 2.7 %;
     * centre of lateral resistance: median ≤ 3.6 mm, max 6.7 mm.
   * At φ 40-60° the errors are S_h ≤ 0.7 % (max 2.3 %) and drag ≤ 0.8 %
     (max 2.1 %). The centre of lateral resistance is 3-12 mm off (max
     28 mm).
   * The errors don't grow with speed from 0.5 to 3.6 m/s, although the
     corrections come from 0.9 and 2.4 m/s only.
   * It needs a sparse heel at 30°. Without one, φ 30° gets half of φ 40°'s
     correction: S_h is then off by 3.1 % and the centre of lateral
     resistance by 27 mm, worse than no correction at all.
   * At β_Y 6-8° it fails. Drag is 5-9 % low at φ 10-20° with every
     variant, including fits through 6°.
   * Confidence: high for this hull swap. A keel swap is untested.
4. **The keel table changes the race time by −0.11 %; the CFD form factor
   by −1.32 %.** `vpp compare iom-alternative` with CFD windage:
   * The alt-water keel table in place of the canoe-body one: 438.2 →
     437.7 s weighted. That is −0.2 % in light air and +0.75 % at 8 m/s,
     where the boat heels more.
   * Then the hull's form factor from this run (k −0.12 to −0.01 on
     ITTC-57, against the assumed +0.10): 437.7 → 432.0 s. That is −2.5 %
     at 1.5 m/s TWS and −0.8 to −1.0 % at 3-7.5 m/s.
   * Confidence: medium. The k behind it rests on the resolved-wall ratio
     from four cases, held above 1.5 m/s.
5. **The side force grows 8 % with Re over the speed range.** At φ 30°,
   β_Y 4°, S_h/V_b² is 4.71 / 4.87 / 4.93 / 5.01 / 5.07 at 0.5 / 0.9 /
   1.5 / 2.4 / 3.6 m/s. The fin's mean y+ runs from 3.5 to 19.4 over the
   same range, through the buffer layer, so part of this may be the wall
   treatment (as in ht35-keel). The grid table carries it as run.
   Confidence: medium.
6. **The fin starts to stall between 4° and 6° upright.** At 1.5 m/s, φ 0°,
   S_h is 14.72 / 20.45 / 24.41 N at 4 / 6 / 8°: 3.7 N/° up to 4°, then
   2.9 and 2.0 N/°. At 6° and above the cases don't converge. At φ 30° the
   fin converges to 6° (16.26 N). Confidence: medium, since this is steady
   RANS on unsteady flow.
7. **The meshes are adequate except for the leeway drag increment.**
   * Keel fine against medium at φ 30°, β_Y 4°, 1.5 m/s:
     * S_h −0.7 %;
     * D_h −2.3 %;
     * the fin's drag −6.5 %;
     * D_h(4°) − D_h(0°) 0.263 → 0.224 N (−15 %).
     ht35-keel found the same at φ 35°: D_h −2.3 %, fin −5.8 %.
   * hull_refine 2 against 1 at φ 60°, 1.5 m/s:
     * the hull's drag +1.6 % (β_Y 0°) and +2.7 % (4°), as its y+ falls
       from 15-16 to 9;
     * S_h −1.5 % at 4°.
   * Confidence: high at 1.5 m/s; not checked at other speeds.

### Evidence

* `report/summary.md`, `report/mesh_check.md`, `report/highlights.md`; the
  numbers recomputed from `results.csv` (medium, hull_refine 1 rows).
* Against ht35-keel@20261027-215521 (medium) at 1.5 m/s, β_Y 4°. The canoe
  body's N/S_h is moved to this fin_x (+44 mm), as the VPP moves the table:

  | φ | S_h alt | S_h canoe | ΔD(4°) alt | ΔD(4°) canoe | N/S_h alt, m | N/S_h canoe, m (moved) |
  |---|---|---|---|---|---|---|
  | 0 | 14.72 | 14.65 | 0.373 | 0.381 | 0.524 | 0.527 |
  | 10 | 14.33 | 14.25 | 0.369 | 0.352 | 0.522 | 0.523 |
  | 20 | 13.10 | 13.14 | 0.337 | 0.336 | 0.519 | 0.516 |
  | 30 / 35 | 11.09 | 10.26 | 0.264 | 0.250 | 0.513 | 0.499 |
  | 50 | 5.88 | 6.82 | 0.129 | 0.161 | 0.486 | 0.461 |
  | 60 / 65 | 3.69 | 3.83 | 0.085 | 0.095 | 0.457 | 0.388 |

  Where two heels are given, the first is this run's and the second the
  canoe body's.

* Transfer check: errors on the held-out cases, β_Y ≤ 4°, median / max.
  S_h's error is a % of this run's S_h(4°) at the same heel and speed.
  Drag's is a % of this run's D_h − D_h,hull(0°). The centre of lateral
  resistance is (N_pred − N)/S_h. "None" is the canoe-body table as is.

  | φ | S_h, none | S_h, corrected | drag, none | drag, corrected | CLR, none | CLR, corrected |
  |---|---|---|---|---|---|---|
  | 0 | 0.3 / 0.6 % | 0.2 / 0.5 % | 1.7 / 3.2 % | 0.5 / 1.8 % | 0.5 / 4 mm | 1.0 / 5 mm |
  | 10 | 0.6 / 1.0 | 0.4 / 0.9 | 1.2 / 3.1 | 0.6 / 1.7 | 4.4 / 9 | 3.6 / 7 |
  | 20 | 0.3 / 1.1 | 0.1 / 0.5 | 1.9 / 2.7 | 0.4 / 1.3 | 2.3 / 8 | 0.9 / 3 |
  | 30 | 0.4 / 1.1 | 0.2 / 0.5 | 2.5 / 4.3 | 0.8 / 2.7 | 4.2 / 13 | 1.6 / 5 |
  | 40 | 5.7 / 8.2 | 0.3 / 1.3 | 1.4 / 4.1 | 0.8 / 2.1 | 31 / 49 | 3.3 / 16 |
  | 50 | 9.5 / 16 | 0.5 / 2.3 | 2.0 / 4.6 | 0.3 / 1.6 | 51 / 71 | 12 / 28 |
  | 60 | 16 / 31 | 0.7 / 2.3 | 1.9 / 6.1 | 0.6 / 1.5 | 119 / 168 | 11 / 24 |

  * **How the canoe-body table was evaluated.** It is linear in heel
    between its 0 / 10 / 20 / 35 / 50 / 65° rows, and only where both
    neighbouring heels converged. Its 3.7 m/s row stands in for this run's
    3.6 m/s, scaled by V_b².
  * **Variants tried:**
    * sparse heels 0 / 20 / 40 / 60 (31 cases): φ 30° S_h 1.7 / 3.1 %,
      CLR 17 / 27 mm;
    * fits through β_Y 6°: worse at ≤ 4° (S_h up to 1.8 %), with no gain
      at 6-8°;
    * heels 0 / 30 / 50 (23 cases): fine to 30°, but S_h 3.4 % median at
      φ 60°.
  * **The script** is a scratch script of the session, not in the
    repository. The method is as described above.
* Form factor, `boats/tables/hull-k-alt.csv`, built from this run's β_Y 0
  rows and alt-hull-yplus:
  * k on ITTC-57 is −0.124 to −0.013; k_wf, with no wall correction, is
    +0.010 to +0.074;
  * the resolved/wall-function ratio is 0.867 / 0.888 / 0.919 at 0.5 /
    0.9 / 1.5 m/s, held at 0.919 above.
* VPP, `vpp compare boats/iom-alternative.yaml` (windage already
  `WindageTable`):

  | TWS m/s | keel table: race Δ | + form factor: race Δ |
  |---|---|---|
  | 1.5 | −0.21 % | −2.52 % |
  | 3.0 | −0.16 % | −0.87 % |
  | 5.0 | −0.06 % | −0.86 % |
  | 7.0 | +0.11 % | −1.00 % |
  | 8.0 | +0.75 % | +0.17 % |
  | weighted | −0.11 % (438.2 → 437.7 s) | −1.32 % (437.7 → 432.0 s) |

### Decisions

* iom-alternative uses this run's keel table (`tables/keel-ht35-alt.csv`;
  `vpp export-table keel3d alt-water@20261030-155529 --select mesh=medium
  --select hull_refine=1 --model grid --fill`) and the form-factor table
  `tables/hull-k-alt.csv` in place of the assumed 0.10. The 14
  not-converged cases are flagged `ext` in the export.
* The keel export now names an STL hull by its sha256 instead of the canoe
  body's default dimensions, and the VPP checks it. Before this, a table
  of this hull warned that it "was computed on keel3d's canoe body".
* **Decoupling (option 3) is viable for a new hull, but not built.**
  * The recipe for a new hull: a full baseline table plus about 40 cases at
    φ 0 / 20 / 30 / 40 / 60° × β_Y 0-6° × two speeds.
  * Cost: about 14 % of a full grid, roughly 20 case-hours against 154.
  * It waits for the user's go-ahead and a keel-swap test.

### Assumptions

* Each heel's static attitude comes from the VPP's hydrostatics
  (2c93e9e-dirty). The VPP solves the attitude, and trim at β_Y 0 is
  alt-hull-trim's.
* The STL's z = 0 is the design waterline (docs/hulls.md). **Not verified**
  with the designer.
* Fully turbulent flow and wall functions. The hull's wall correction comes
  from four resolved cases (alt-hull-yplus, φ 0 / 30°, 0.5 / 1.5 m/s). It
  is held above 1.5 m/s: **not verified** at 2.4 / 3.6 m/s, where y+ ≈ 1
  doesn't mesh.
* Double body: no waves and no wave-changed wetted area. The VPP adds
  Michell's waves.
* The canoe-body comparison uses ht35-keel@20261027-215521. It differs from
  this run in more than the hull, and the transfer check's corrections
  absorb all of it:
  * hull mesh (hull_refine 0 there);
  * attitude;
  * fin span;
  * top speed (3.7 m/s).

### Compromises

* **Keel mesh medium.** The leeway drag increment at φ 30°, β_Y 4° is 15 %
  above the fine mesh's (D_h +2.3 %). It goes into the table as is, as in
  ht35-keel, so the two tables compare like for like.
* **hull_refine 1.** The hull's drag is 1.6-2.7 % below hull_refine 2's at
  φ 60°. The VPP doesn't use the table's hull drag: the hull model has it,
  with the CFD k, wall-corrected.
* **The 14 not-converged stall cases** are window means of unsteady flow,
  flagged `ext`.
* **Heels every 10°.** The hull's effect switches on between 30° and 40°
  and isn't resolved finer.

### Learnings

* **Physics.**
  * The hull-keel interaction in side force is about 1 % (max 1.1 %) up to
    φ 30°, and 6-31 % from 40°.
  * The heeled hull's asymmetry gives a leeward force at β_Y 0 (−0.41 N
    at φ 40°, 1.5 m/s), which the grid table carries.
* **Solver.** Converged cases take 468-3,000 iterations, median 581, and
  three quarters finish under 660. The β_Y 8° cases that do converge take
  1,900-3,000 iterations: two (φ 20°, 2.4 m/s and φ 30°, 0.9 m/s) settled
  only at the limit. Convergence at β_Y 8° doesn't follow heel: φ 20° and
  40-60° converge, while φ 10° and 30° don't above 0.9 m/s.
* **Workflow.**
  * `--select hull_refine=1` drops the hull-mesh checks, as `mesh=medium`
    drops the keel's.
  * The transfer check is a cheap way to test a table method before
    building it.
* **Compute and cost.**
  * 154.3 case-hours: median 25.2 min, max 133 min per case.
  * 17.8 h of wall time at 9 parallel.
  * Medium cells: 1.07-1.40 M. The plan had assumed 2 M and 35 min.
  * About $34 of Spot time. This is scaled from ht35-keel's estimate per
    case-hour, not from billing.

### Open questions and next steps

* **A keel-swap transfer test** before building option 3. Two canoe-body
  keel tables of different fins or bulbs would test whether the offset and
  slope absorb a change in lift slope.
* **The 8 m/s upwind slowdown.** Upwind VMG drops 1.2 % with the keel table
  and another 0.9 % with the form factor. That is the A rig's top wind,
  near the 8° leeway limit. Not investigated.
* **Where between 30° and 40° the hull starts to take side force**, and
  why. A φ 35° row (40 cases) would settle the table there.
* **alt-hull-trim's findings** are still to write.
* Suggested highlights for a next run:

  ```yaml
  highlights:
    - name: hull-onset
      why: The hull takes side force from 40 deg (canoe-body table 6-16 % high) - where it starts and how.
      where: {heel: [30, 40, 50], leeway: 4, speed: 1.5, mesh: medium, hull_refine: 1}
      compare: heel
      views: [surface_cp_starboard, wake_slice]
    - name: stall-heel
      why: At 8 deg heels 20 and 40-60 converge, while 10 and 30 don't - a physical difference or a solver one?
      where: {heel: [10, 20, 30], leeway: 8, speed: 1.5, mesh: medium, hull_refine: 1}
      compare: heel
      views: [surface_cp_starboard, vortices]
  ```
