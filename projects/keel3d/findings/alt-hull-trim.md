# alt-hull-trim: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/alt-hull-trim/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study puts the alternative hull
(`iom-alternative`, private STL), with its keel, at the VPP's downwind
bow-down trims at zero leeway. It tests whether the hull's form factor needs
a trim axis. The static attitudes are in [alt-water](alt-water.md), and the
question comes from [alt-water-scout](alt-water-scout.md) (E3). Project:
[README](../README.md).

## Run 20261030-155550 (2026-10-30, git 2c93e9e-dirty, GCP, 30 cases)

**Setup.**

* **Hull and keel.** As alt-water: the STL cut at the waterline and
  mirrored, hull_refine 1, keel mesh medium, β_Y 0. The keel is HT35 at
  7.25 %, 100 → 80 mm, fin_x 0.544, round NACA 0011 bulb at 2°.
* **Sweep.**
  * φ 0 and 10° at the attitudes of M_ext 3.5 / 5.8 / 8.0 N m bow down
    (`vpp hydro iom-alternative --zip 0,10 --m-ext M`): trim 3.30 / 6.02 /
    9.26° (9.25° at φ 10°), sink −2.0 to −9.4 mm.
  * Each × V_b 0.5, 0.9, 1.5, 2.4, 3.6 m/s.
* **Reference.** alt-water@20261030-155529's static cases at the same heel
  and speed: trim −0.001° (φ 0) and 0.015° (φ 10).
* **Solver.** kOmegaSST with Spalding wall functions, fully turbulent,
  Tu 0.5 %. c2d-standard-16 Spot, 8 ranks, 2 at a time. alt-water ran on
  c3d.
* **History.** First run. Its 12 cases at 1.5 and 2.4 m/s repeat
  alt-water-scout's E3.

**Outcome.** 30 ok, all converged: 464-751 iterations, median 505. None
at the 3,000-iteration limit.

### Conclusions

1. **Bow-down trim raises the hull's form factor by 1.3-3.4 / 3.9-7.6 /
   10.0-13.8 % at 3.3 / 6.0 / 9.3°, over the whole speed range.**
   * The means are 2.6 / 5.6 / 11.8 %, at φ 0 and 10° alike.
   * Against the trimmed hull's own S and LWL: S falls 2.6 / 4.9 / 7.5 %,
     LWL is 0.884 / 0.814 / 0.743 m (0.958 static), and the hull's drag
     still rises 0.3-10.6 %.
   * The rise is about 0.8 %/° up to 6° and 1.9 %/° from 6° to 9.3°.
   * E3's two speeds hold from 0.5 to 3.6 m/s.
   * Confidence: high at 6° and 9.3°. At 3.3° it is medium: the rise is
     the size of the run-to-run scatter (conclusion 5). At φ 0° the 3.3°
     values scatter 1.3-3.4 % with no trend in speed, while φ 10°'s run
     smoothly from 2.3 to 3.0 %.
2. **The VPP misses that rise: its k depends on heel and V_b only.**
   * `IttcMichell` already takes the wetted area and LWL at the solved
     trim. So the error is exactly the (1+k) ratio: hull friction about
     12 % low at 9.3°.
   * The VPP's downwind trims (`vpp point iom-alternative`, β_TW 135-180°):
     * 0.4-1.0° at TWS ≤ 3 m/s;
     * 3.2-4.7° at 5 m/s;
     * 5.5-8.6° at 6.5 m/s;
     * 8.8-12.3° at 8 m/s.
   * Friction R_f is 21-36 % of the hull's resistance downwind at 5-8 m/s.
     So the missing friction is about 0.5 % of the hull's resistance at
     5 m/s (β_TW 180°, 3.2°) and about 3.3 % at 8 m/s (8.8°), which is
     where the winds are rarest.
   * This is an estimate (R_f share × Δ(1+k)); it isn't a VPP run.
   * Confidence: medium.
3. **The hull and keel together change by only −2.4 to +3.7 %, because the
   fin's drag falls as the hull's rises.**
   * The fin's drag falls 2.2-8.2 % with trim at every case.
   * The bulb's drag changes −6.1 to +8.6 %. At 9.25° and φ 10°, the bulb
     (2° nose up on the fin) is about 7° nose down. It pulls down: the
     bulb's vertical force at 3.6 m/s is −1.09 N, against +0.04 N static.
   * The VPP's keel table doesn't carry any of this. Its X is at static
     attitude.
   * Why the fin's drag falls isn't explained. The fin's trailing edge
     rakes aft by the trim angle, but that hasn't been checked.
   * Confidence: high for the numbers; low for the cause.
4. **On a heeled hull, trim gives the fin a leeway of 0.90-0.97 × trim ×
   sin φ at β_Y 0, the same at every speed.**
   * At φ 10°, S_h/V_b² is −0.83 to −0.90 / −1.43 to −1.58 / −2.21 to
     −2.41 at 3.3 / 6.0 / 9.25°. The minus sign means to leeward, the side
     the boat heels to.
   * That is −0.55 / −0.95 / −1.47° worth on alt-water's φ 10° lift slope
     over 0-4°. N/S_h ≈ 0.54 m, at the fin.
   * Not in the VPP's keel table, which is at static attitude.
   * The fin's lift for a given side force, and so its induced drag,
     shouldn't change. So the VPP's leeway and rudder angle are off by up
     to about 1° downwind (φ ≤ 10°), but its speed is barely affected.
     That last point is reasoning, not a VPP run.
   * Confidence: high for the force; medium for its effect.
5. **The forces repeat within about 1 % although the meshes don't.**
   * E3's 12 cases, here (c2d) against the scout (c3d):
     * hull drag −1.1 to +0.3 % (10 of 12 within 0.35 %);
     * D_h −0.6 to +0.2 %;
     * S_h within 0.12 N.
     The meshes, though, differ by −6 to +7 % in cells and −24 to +31 % in
     the hull's mean y+.
   * The scout's static cases against alt-water's (both c3d):
     * D_h within 0.8 %;
     * hull drag within 1.5 %;
     * 3 of 9 meshes differ by 5-8 % in cells.
   * The two images differ (`…-202610300212` against `…-202610300300`), so
     machine and image can't be separated.
   * Through y+, the hull's wall-function friction moves by up to 1.5 %
     from one run of a case to the next.
   * Confidence: high, from 21 pairs.

### Evidence

* `report/summary.md`; everything else recomputed from `results.csv`
  against alt-water@20261030-155529's `results.csv` (β_Y 0, medium,
  hull_refine 1). (1+k) uses `vpp/keel3d._form_factor`: ITTC-57 on the cut
  hull's LWL and S, wall functions, no resolved-wall ratio.
* Changes against the static case at the same heel and speed, min to max
  over V_b 0.5-3.6 m/s:

  | φ | trim | S | LWL [m] | hull drag | 1+k | D_h | fin drag | S_h/V_b² |
  |---|---|---|---|---|---|---|---|---|
  | 0 | 3.3 | −2.6 % | 0.884 | +0.3 to +2.6 % | +1.3 to +3.4 % | −2.4 to −0.8 % | −5.9 to −3.6 % | 0.01 |
  | 0 | 6.0 | −4.9 % | 0.814 | +2.3 to +5.6 % | +3.9 to +7.6 % | −1.1 to +0.4 % | −4.5 to −3.8 % | 0.01 |
  | 0 | 9.3 | −7.5 % | 0.743 | +7.4 to +10.3 % | +10.0 to +13.5 % | +0.9 to +2.4 % | −8.2 to −6.7 % | 0.01 |
  | 10 | 3.3 | −2.6 % | 0.887 | +1.6 to +2.0 % | +2.3 to +3.0 % | −0.7 to −0.4 % | −3.0 to −2.2 % | −0.83 to −0.90 |
  | 10 | 6.0 | −4.9 % | 0.816 | +4.0 to +4.4 % | +5.3 to +6.2 % | −0.7 to −0.1 % | −6.2 to −4.6 % | −1.43 to −1.58 |
  | 10 | 9.25 | −7.5 % | 0.745 | +9.1 to +10.6 % | +11.4 to +13.8 % | +3.3 to +3.7 % | −6.3 to −5.5 % | −2.21 to −2.41 |

* (1+k) change by speed, %:

  | φ | trim | 0.5 | 0.9 | 1.5 | 2.4 | 3.6 m/s |
  |---|---|---|---|---|---|---|
  | 0 | 3.3 | 2.2 | 3.4 | 2.4 | 1.3 | 3.0 |
  | 0 | 6.0 | 5.0 | 5.8 | 3.9 | 5.2 | 7.6 |
  | 0 | 9.3 | 10.7 | 10.9 | 10.0 | 10.9 | 13.5 |
  | 10 | 3.3 | 2.3 | 2.6 | 2.9 | 3.0 | 2.8 |
  | 10 | 6.0 | 5.3 | 5.5 | 5.8 | 6.2 | 6.0 |
  | 10 | 9.25 | 11.4 | 11.4 | 12.3 | 12.9 | 13.8 |

  At φ 0°, 2.4 m/s the static case's mean hull y+ is 19.1 and the trimmed
  ones' 25-31. That is the kind of mesh difference conclusion 5 measures.
* The VPP's downwind points: `vpp point boats/iom-alternative.yaml --tws T
  --twa A` at d3e130d, with the CFD keel, form-factor and windage tables:

  | TWS m/s | β_TW | V_b | φ | trim | R_f [N] | R_w [N] |
  |---|---|---|---|---|---|---|
  | 3 | 180 | 1.08 | 0.7 | 0.95 | 0.369 | 0.440 |
  | 5 | 180 | 1.56 | 2.1 | 3.23 | 0.728 | 2.674 |
  | 5 | 135 | 1.95 | 10.1 | 4.66 | 1.065 | 3.349 |
  | 6.5 | 180 | 2.20 | 3.2 | 5.48 | 1.328 | 3.671 |
  | 6.5 | 135 | 2.71 | 15.7 | 8.61 | 1.880 | 4.686 |
  | 8 | 180 | 2.86 | 4.3 | 8.76 | 2.076 | 4.663 |
  | 8 | 135 | 3.54 | 21.2 | 12.26 | 3.009 | 5.393 |

### Decisions

* **The VPP keeps a static k for now.** iom-alternative's form factor
  stays `tables/hull-k-alt.csv`, over heel × V_b at static attitude.
* **Proposed, waiting for the user:** a trim factor on the form factor,
  (1+k)(φ, V_b) × f(trim).
  * f comes from this run: linear in trim through 0 / 3.3 / 6.0 / 9.3°,
    averaged over φ 0 and 10° and over speed, held and flagged beyond
    9.3°.
  * `IttcMichell` would apply it at the solved trim.
  * Cost: a `trim:` source in the hull-form-factor recipe, a third axis in
    the hull's table, and tests. No new CFD.
  * Expected effect: small in the weighted race time, concentrated
    downwind at 6.5-8 m/s TWS (conclusion 2). This is an estimate, not
    computed.

### Assumptions

* The attitudes are `vpp hydro`'s for iom-alternative (2c93e9e-dirty) at
  M_ext 3.5 / 5.8 / 8.0 N m, Z_ext 0.
* The hull form factor's resolved/wall-function ratio (alt-hull-yplus) is
  taken to be the same at these trims. **Not verified.** It was measured at
  static attitude, φ 0 and 30°.
* The STL's z = 0 is the design waterline (docs/hulls.md). **Not
  verified.**
* The VPP's downwind trims and R_f shares come from seven `vpp point`
  solutions, not from a polar run.

### Compromises

* **β_Y 0 only.** The VPP's downwind leeway is near 0 (0.02° at 5 m/s,
  180°), so this matters little downwind.
* **Heel 0 and 10° only, and trim up to 9.3°.** The VPP reaches φ 21° and
  12.3° of trim at 8 m/s, β_TW 135°. Both are outside this run.
* **Double body.** With no free surface, at 9° of trim the real bow buries
  and the waves dominate: R_w is 1.8-3.7 × R_f at 5-8 m/s downwind. The
  double body's vertical force changes with trim (−11.3 N at 9.3°, φ 0°,
  3.6 m/s), but that is mirror-plane suction and the VPP doesn't use it.
* **Wall functions.** The hull's friction moves by up to 1.5 % from run to
  run (conclusion 5). That blurs the 3.3° result.

### Learnings

* **Physics.**
  * Bow-down trim raises the hull's viscous drag more than its smaller
    wetted area lowers it: +10 % at 9° (the hull's drag, against S −7.5 %).
  * On a heeled hull, trim turns into an equivalent leeway of about
    0.93 × trim × sin φ.
* **Solver.** At β_Y 0 the cases converge quickly: 505 iterations median,
  11.4 min.
* **Workflow.** snappyHexMesh doesn't give the same mesh from one run of a
  case to the next (5-8 % in cells for 3 of 9 static pairs, and most
  trimmed pairs). So a small effect needs its reference from the same run
  and image, and ideally a repeat to measure the scatter.
* **Compute and cost.**
  * 5.8 case-hours (median 11.4 min, max 15.8 min); 3.1 h of wall time at
    2 parallel.
  * About $1.3 at ht35-keel's estimated rate per case-hour. This is an
    estimate, not from billing. The scout had expected about 13
    case-hours.

### Open questions and next steps

* **The trim factor in the VPP** (Decisions), if the user wants it.
* **Trim beyond 9.3° and at φ 15-20°**, which the VPP reaches at 6.5-8 m/s.
  Six cases (φ 0 / 15 × 12° × 3 speeds) would cover the factor's held
  range, if it goes in.
* **Mesh repeatability.** Run the same case twice on the same machine and
  image, to separate snappy's own scatter from the image change.
* **Why the fin's drag falls with trim.** Look at the fin's surface Cp and
  Cf at φ 0°, 2.4 m/s, 0 against 9.3° of trim.
* Suggested highlights, if the study runs again:

  ```yaml
  highlights:
    - name: trim-friction
      why: The hull's (1+k) rises 11 % at 9.3 deg of trim while S falls 7.5 % - where on the hull, and why the fin's drag falls.
      where: {heel: 0, speed: 2.4}
      compare: trim
      views: [surface_cp_starboard, wake_slice]
    - name: trim-yaw
      why: At heel 10, trim acts as 0.93 x trim x sin(heel) of leeway on the fin.
      where: {heel: 10, speed: 1.5}
      compare: trim
      views: [surface_cp_starboard, vortices]
  ```
