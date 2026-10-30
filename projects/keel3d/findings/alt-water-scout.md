# alt-water-scout: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/alt-water-scout/<run id>/` (not in git), so the numbers that support
a conclusion are copied here. The study is a set of quick experiments that
settle the parameters of [alt-water](../studies/alt-water.yaml) and
[alt-hull-trim](../studies/alt-hull-trim.yaml). Those studies cover the
water part of the alternative hull (`iom-alternative`, private STL) with
its keel, cut at each heel's waterline and mirrored, for the VPP's keel
table and hull form factor. Project: [README](../README.md).
The air part is in [windage/alt-air-scout](../../windage/findings/alt-air-scout.md).

## Run 20261030-021322 (2026-10-30, git 2c93e9e-dirty, GCP, 32 cases)

**Setup.**

* **Hull.** `file:private/iom-alternative.stl` at each heel's static
  attitude: sink and trim from `vpp hydro iom-alternative --zip` at
  M_ext 0, Z_ext 0. For φ 0 / 10 / 30 that is sink −2.15 / −2.53 / −5.40
  mm and trim −0.001 / 0.015 / 0.131°. The hull is cut at z = 0 and
  mirrored (`geometry/waterline.split`): a double body with no waves.
* **Fin root.** The fin's root is at the hull bottom under its quarter
  chord, z_root −59.0 mm. It is extended 29.5 mm into the hull, the most
  the bottom rises under the root section plus a margin (`root_extension`),
  so the trailing-edge corner stays attached despite the rocker.
* **Keel.** iom-alternative's keel, as in [ht35-keel](ht35-keel.md):
  * fin HT35 at 7.25 %, 100 → 80 mm, at fin_x 0.544;
  * round NACA 0011 bulb at 2°;
  * keel mesh medium.
* **New parameter `hull_refine`.** It adds levels on the hull surface and
  the hull box:
  * 0: hull cells 5.6/2.8 mm (keel3d's medium);
  * 1: 2.8/1.4 mm;
  * 2: 1.4/0.7 mm.
* **E1, the hull mesh.** φ 0 and 30° × β_Y 0 and 4° × hull_refine 0, 1
  and 2, at 1.5 m/s.
* **E2, y+ across speed.** φ 30°, β_Y 4°, V_b 0.5 and 3.6 m/s,
  hull_refine 1 and 2.
* **E3, trim.** All at β_Y 0, hull_refine 1:
  * φ 0 and 10° × V_b 1.5 and 2.4 m/s × the attitudes at M_ext 3.5, 5.8
    and 8.0 N m bow down (trim about 3.3, 6.0 and 9.3°, with each heel's
    static case for reference);
  * φ 30° at 2.6 N m (2.47°).
* **Solver.** kOmegaSST with Spalding wall functions, fully turbulent,
  Tu 0.5 %; drift-checked convergence. c3d-standard-16 Spot, 8 ranks.
* **History.** This is the first run. The related run is ht35-keel
  20261027-215521, the same keel on keel3d's canoe body.

**Outcome.** 32 ok, all converged (446-721 iterations, none at the
3000-iteration limit). 14.3 case-hours.

### Conclusions

1. **The side force doesn't depend on the hull's mesh.** At β_Y 4°,
   S_h is 14.70 / 14.67 / 14.69 N upright and 11.17 / 11.14 / 11.12 N at
   φ 30° (hull_refine 0 / 1 / 2): within 0.5 %. Confidence: high.
2. **The leeway drag increment barely depends on the hull's mesh.**
   D_h(4°) − D_h(0°) is:
   * upright: 0.381 / 0.383 / 0.382 N, within 0.6 %;
   * at φ 30°: 0.260 / 0.271 / 0.280 N, up about 4 % per level.

   This increment and S_h are what the keel table carries. Confidence:
   high upright, medium at heel.
3. **The hull's drag doesn't converge with hull refinement, and the
   friction is what keeps rising.**
   * Upright at β_Y 0, the hull's friction is 0.650 / 0.673 / 0.704 N
     (+3.5 %, +4.6 %). Its pressure drag is 0.074 / 0.063 / 0.060 N,
     settling.
   * The hull's mean y+ falls 30 / 19 / 9 through the buffer layer.
   * The CFD friction coefficient is 0.90 / 0.93 / 0.97 × ITTC-57's at all
     4 heel × leeway pairs (0.88-0.98).
   * So the change comes from how the wall functions treat the boundary
     layer, not from resolving the hull's shape, and a finer mesh won't
     close it.

   Confidence: high for the trend; medium for the explanation (no
   resolved-wall, y+ ≈ 1, case to compare).
4. **The hull's form factor on ITTC-57 comes out small, and within the
   uncertainty of the wall treatment: k = 0.00 / 0.02-0.03 / 0.06
   (hull_refine 0 / 1 / 2), against the VPP's 0.10.**
   k = D_hull / (q S C_F,ITTC(Re_LWL)) − 1 at β_Y 0:
   * upright, 1.5 m/s: 0.002 / 0.019 / 0.058;
   * at φ 30°: 0.003 / 0.032 / 0.057;
   * at hull_refine 1: 0.021 at φ 10°; 0.027 upright and 0.018 at φ 10°
     at 2.4 m/s.

   The band from the wall treatment is as large as k itself, so this run
   can't say whether the VPP's 0.10 is too high. Confidence: low for the
   value of k.
5. **At hull_refine 1 the hull stays inside the wall function's range
   across the VPP's speeds.**
   * The hull's mean y+ is 4.8 / 19 / 28 at 0.5 / 1.5 / 3.6 m/s (max
     48 / 134 / 218).
   * The fin's mean y+ is 3.5 / 9.2 / 19.4, as ht35-keel's (3.4-19.2).
   * Against hull_refine 2, D_h is +3.3 % at 0.5 m/s, −1.6 % at 1.5 m/s
     and −1.1 % at 3.6 m/s; S_h is within 0.3 %.

   Confidence: medium (one heel and leeway).
6. **Bow-down trim raises the hull's form factor by 1.5-3.9 / 5.5-6.7 /
   11-12.5 % at 3.3 / 6.0 / 9.3°, while the hull and keel together change
   by only −2.3 to +3.1 %.**
   * Over φ 0 and 10° × 1.5 and 2.4 m/s, 11 of 12 comparisons exceed the
     plan's 3 % threshold. The one that doesn't is φ 0°, 2.4 m/s, 3.3°:
     +1.5 %.
   * The wetted area falls 2.6 / 4.9 / 7.5 % and the waterline length
     8 / 15 / 22 % (0.958 → 0.743 m).
   * The hull's drag still rises 0.5-9.6 %. The fin and bulb lose much of
     what the hull gains: upright at 1.5 m/s and 9.3°, the hull gains
     0.068 N and the total 0.028 N.
   * At the upwind trim of φ 30°, 2.47°, (1+k) rises only 1.7 %.

   So downwind trims (heel 0-10°) need their own table: alt-hull-trim.
   Confidence: high for the trend.
7. **Trim on a heeled hull turns the fin into a side force at β_Y 0, as
   if leeway were about trim × sin φ.** At φ 10°, S_h is
   −2.0 / −3.5 / −5.3 N at 1.5 m/s and −5.1 / −8.9 / −13.7 N at 2.4 m/s
   for 3.3 / 6.0 / 9.3°. At φ 30° with 2.47° it is −3.5 N. Against
   14.7 N at β_Y 4° upright, 9.25° of trim at φ 10° (1.6° by
   trim × sin φ) gives about 1.4° worth. Confidence: high.
8. **The alternative hull with its keel behaves like the canoe body
   upright, to within 0.4 %.** At hull_refine 0 (the canoe's mesh),
   1.5 m/s, the alternative hull against ht35-keel's medium row:
   * β_Y 0: D_h 1.469 vs 1.465 N;
   * β_Y 4°: D_h 1.849 vs 1.846 N and S_h 14.70 vs 14.65 N.

   The hull carries 14 % of S_h: 2.12 of 14.67 N upright and 1.57 of
   11.14 N at φ 30° (hull_refine 1). Confidence: medium (one speed,
   upright only; φ 30° vs ht35-keel's 35° isn't a like comparison).

### Evidence

* `results.csv` of the run; numbers recomputed with short pandas snippets.
  q = ½ρV_b², C_F,ITTC = 0.075 / (log Re_LWL − 2)², with S and LWL of each
  case's cut hull (`hull_wetted_area_m2`, `hull_lwl`).
* E1, the hull mesh at 1.5 m/s (hull_refine 0 / 1 / 2):

  | φ, β_Y | D_h [N] | hull drag [N] | S_h [N] | hull y+ mean |
  |---|---|---|---|---|
  | 0, 0 | 1.469 / 1.480 / 1.509 | 0.725 / 0.736 / 0.765 | - | 30 / 19 / 9 |
  | 0, 4 | 1.849 / 1.863 / 1.891 | 0.840 / 0.855 / 0.882 | 14.70 / 14.67 / 14.69 | 26 / 20 / 10 |
  | 30, 0 | 1.461 / 1.482 / 1.501 | 0.728 / 0.749 / 0.768 | - | 13 / 17 / 10 |
  | 30, 4 | 1.722 / 1.753 / 1.782 | 0.806 / 0.838 / 0.868 | 11.17 / 11.14 / 11.12 | 30 / 19 / 9 |

  Hull_refine 1 against 2: D_h −1.9, −1.5, −1.3, −1.6 %; hull drag −3.7,
  −3.2, −2.4, −3.5 %. Richardson extrapolation gives no order: the
  differences grow with refinement (upright), or the order is about 0.1-0.2
  (φ 30°).
* E2 at φ 30°, β_Y 4° (hull_refine 1 / 2):

  | V_b | hull y+ mean (max) | fin y+ mean | D_h / V_b² | S_h / V_b² |
  |---|---|---|---|---|
  | 0.5 | 4.8 (48) / 3.4 (27) | 3.5 | 0.968 / 0.937 | 4.697 / 4.702 |
  | 1.5 | 19.4 (134) / 9.3 (68) | 9.2 | 0.779 / 0.792 | 4.949 / 4.941 |
  | 3.6 | 28.0 (218) / 18.8 (130) | 19.4 | 0.665 / 0.672 | 5.063 / 5.058 |

* E3, trim at β_Y 0, hull_refine 1 (changes against each heel and
  speed's static case):

  | φ | V_b | trim | S | LWL [m] | hull drag | 1+k | D_h | S_h [N] |
  |---|---|---|---|---|---|---|---|---|
  | 0 | 1.5 | 3.3 | −2.6 % | 0.884 | +3.0 % | +3.9 % | −0.8 % | 0.02 |
  | 0 | 1.5 | 6.0 | −4.9 % | 0.814 | +5.0 % | +6.7 % | +0.3 % | 0.04 |
  | 0 | 1.5 | 9.3 | −7.5 % | 0.743 | +9.2 % | +11.9 % | +1.9 % | 0.00 |
  | 0 | 2.4 | 3.3 | −2.6 % | 0.884 | +0.5 % | +1.5 % | −2.3 % | 0.05 |
  | 0 | 2.4 | 6.0 | −4.9 % | 0.814 | +3.7 % | +5.5 % | −0.5 % | −0.05 |
  | 0 | 2.4 | 9.3 | −7.5 % | 0.743 | +8.2 % | +11.1 % | +1.2 % | −0.06 |
  | 10 | 1.5 | 3.3 | −2.6 % | 0.887 | +2.3 % | +3.2 % | −0.3 % | −1.99 |
  | 10 | 1.5 | 6.0 | −4.9 % | 0.816 | +4.4 % | +6.1 % | −0.1 % | −3.46 |
  | 10 | 1.5 | 9.3 | −7.5 % | 0.745 | +9.3 % | +12.0 % | +3.1 % | −5.28 |
  | 10 | 2.4 | 3.3 | −2.6 % | 0.887 | +2.5 % | +3.6 % | −0.2 % | −5.11 |
  | 10 | 2.4 | 6.0 | −4.9 % | 0.816 | +4.1 % | +5.9 % | −0.5 % | −8.94 |
  | 10 | 2.4 | 9.3 | −7.5 % | 0.745 | +9.6 % | +12.5 % | +3.1 % | −13.73 |
  | 30 | 1.5 | 2.5 | −1.3 % | 0.927 | +1.2 % | +1.7 % | +1.1 % | −3.51 |

* Compute: case wall time median 24.5 min, mean 26.7, max 46.7. Mean by
  hull_refine 0 / 1 / 2: 20 / 23 / 44 min. 1.0-1.9 M cells
  (`report/summary.md`).

### Decisions

* **[alt-water](../studies/alt-water.yaml) uses hull_refine 1.**
  * Why: side force within 0.5 % of level 2, and drag within 1.1-3.3 %
    across speed, at half level 2's time (23 vs 44 min a case). Level 2
    doesn't converge either (conclusion 3).
  * Checks: hull_refine 2 at φ 60°, β_Y 0 and 4° (φ 0 and 30° are here),
    and the keel's fine mesh at φ 30°, β_Y 0 and 4°, all at 1.5 m/s.
  * Run 20261030-155529 was submitted after the user confirmed: 284 cases,
    7 heels at static attitude × β_Y −2 to 8° × V_b 0.5-3.6 m/s,
    c3d-standard-16, 9 at a time. Estimate: about 185 case-hours, about
    $40 and 21 h. This is scaled from ht35-keel's estimated $30 for 137
    case-hours and this run's times; it isn't from billing.
* **Trim gets its own table: [alt-hull-trim](../studies/alt-hull-trim.yaml)**
  (conclusion 6).
  * Content: β_Y 0, φ 0 and 10°, the M_ext 3.5 / 5.8 / 8.0 attitudes ×
    V_b 0.5-3.6 m/s. 30 cases, about 13 case-hours, about $3.
  * Run 20261030-155550 was submitted on c2d-standard-16, 2 at a time.
  * Upwind trims (≤ 2.75°) are left out: +1.7 % at φ 30°, 2.47°.
* **Static attitude for the main table.** The keel table stays a function
  of heel, leeway and speed, as ht35-keel's.

### Assumptions

* **The STL's z = 0 is the design waterline.** The designer didn't say
  (docs/hulls.md). **Not verified.**
* **Attitudes are from `vpp hydro` (boats/iom-alternative.yaml).** Static
  ones at M_ext 0, Z_ext 0; trimmed ones at M_ext 3.5 / 5.8 / 8.0 /
  2.6 N m.
* **The VPP's trims** (up to 2.75° upwind, up to 9° downwind at φ 0-5°)
  are from earlier VPP runs, quoted in the study's description. They
  weren't recomputed here.
* **ITTC-57 with Re on the cut hull's LWL** is the VPP's friction line
  (`IttcMichell`); k is measured against it.
* **ht35-keel's numbers** are quoted from its findings log (run
  20261027-215521), not re-read from its run.

### Compromises

* **Fully turbulent with wall functions.** The hull's absolute friction
  carries a band of about ±4 % (conclusion 3). The hull's laminar run at
  low V_b, which would lower its friction, isn't modelled.
* **Double body: no waves, no change of wetted area with the wave
  profile.** The VPP adds Michell's wave drag on top. Upright at 2.4 m/s
  (Fn about 0.78) the real flow differs most.
* **E3 is at β_Y 0 only, φ ≤ 10° (plus one φ 30° case), and two speeds.**
  alt-hull-trim covers the speeds but not leeway with trim.
* **One keel mesh (medium) throughout.** ht35-keel found the fine keel mesh
  cuts D_h by 5.0 % at β_Y 4° upright (the fin's own drag −11.9 %).
  That's larger than the hull's mesh effect here. alt-water checks it at
  φ 30° only.

### Learnings

* **Hull refinement with wall functions moves friction, not pressure.**
  Choose the hull's mesh on side force and pressure drag, and treat its
  friction as a band. Refining from y+ 30 to 9 raised the friction 8 %.
* **The root extension works.** The rocker under the root raises the
  bottom 2.03 mm toward the trailing edge, and the computed extension of
  29.5 mm (0.5 × the depth at the root) keeps the junction closed. All 32
  cases meshed and converged.
* **`surfaceFeatureExtract` with `intersectionMethod region` finds no
  junction edges in any keel3d run, including past ones; `self` finds
  about 740.** STL hulls now use `self` (`featureIntersection`); canoe
  cases are unchanged.
* **Compute.** A case at hull_refine 1 is about 1.2-1.3 M cells and 23 min
  on 8 ranks of c3d-standard-16, about 1.3 × ht35-keel's median (17.6 min).

### Open questions and next steps

* **Form factor.** Pin k with a resolved wall (y+ ≈ 1 on the hull) at
  β_Y 0, φ 0 and 30°, 0.5 / 1.5 / 3.6 m/s, or with a CFD flat plate at the
  same wall treatment, before replacing the VPP's 0.10. Resolving the
  wall needs a keel3d option for an absolute first-layer thickness;
  today's layers are relative to the cell.
* **Repeatability.** alt-hull-trim repeats E3's 12 trimmed cases on
  another machine family (c2d against this run's c3d). Compare them for
  the scatter of a water case.
* Highlights in alt-water: upwind (φ 30°, β_Y 3° across V_b), deck (φ 40 /
  50 / 60°, where the leeward deck edge goes under between 40 and 45°)
  and stall (β_Y 4 / 6 / 8° at φ 0 and 30°).
* After alt-water: `vpp export-table --model grid` for iom-alternative's
  keel table. Use (1+k)(φ, V_b) from its β_Y 0 rows and alt-hull-trim for
  trim, once the friction band is settled.
