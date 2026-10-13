# fin-profile-selection: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results themselves live
in `runs/fin-profile-selection/<run id>/` (not in git), so the numbers that
support a conclusion are copied here. Entries are written by the
`study-findings` skill (`/study-findings foil2d/fin-profile-selection`) or by
hand, and are not rewritten later: a later run that changes a conclusion says
so in its own entry.

## Run 20261013-045759 (2026-10-13, git 19e49d8, GCP, 100 cases)

**Setup.** The four finalists of run 2 at Tu 0.1 %:
* 0008/80 and 0009/80, tied at working load in run 2;
* 0008/90, the best balance over loads;
* 0009/100, best at high load.

Swept at 0.5, 0.75, 1.0, 1.5 and 2.5 m/s × aoa 0-8° (step 2); foil and
chord are zipped. kOmegaSSTLM, steady, medium mesh (90,112 cells), whole fin
as before. Image `iom-cfd:19e49d8` (same solver as run 2, gzipped export),
3 × c3d-standard-16 Spot.

Why: run 1 found the winner can change with Tu, with 3-12 % penalties where
it did, and run 2's tie is smaller than that. 0.25 m/s was dropped (open
laminar separation, unvalidated). The fine-mesh check of the tie ran
alongside as study `mesh-finalists`, run 20261013-045811
([findings/mesh-finalists.md](mesh-finalists.md)).

**Outcome.** 90 ok, 9 not converged, 1 failed. 59 of the 99 finished cases
are flagged unsteady; the same 99 cases at Tu 1 % (run 2) had 23.
* The failure is 0008/90 at 1 m/s and 8°: a floating-point exception at
  iteration 234. It doesn't affect the comparisons at the 2/4/6° forces.
* The not-converged cases are at 4-8°, 7 of 9 at 1.5 m/s or above.

### Conclusions

1. **The medium mesh resolves the 0008/0009 difference** (`mesh-finalists`).
   * At the Cl 0009/80 makes at 4°, 0008/80 has 0.9 % (coarse), 1.6 %
     (medium) and 1.9 % (fine) less drag than 0009/80. The sign is the same
     on all three meshes, and medium to fine moves it by 0.3 points.
   * Cd itself changes by under 0.2 % at 4° and 0.8-1.7 % at 6° from medium
     to fine.

   Confidence: high, for 1 m/s, 80 mm, Tu 1 %.
2. **At Tu 0.1 % the working-load tie breaks toward 0009/80, from 1.5 m/s
   up.**
   * At the 4° force, 0009/80 is within 0-0.2 % of the best finalist at
     0.75-2.5 m/s. 0008/80 is 3.5-13 % worse (+13 % at 2.5 m/s).
   * At Tu 1 % (run 2) the two were within 0-1.6 %.
   * Taking both Tu levels together, 0009/80 is the most robust working-load
     choice: at most 1.6 % above the best finalist at 0.75 m/s and up (mean
     0.4 %). 0008/90 is at most 4.3 % (mean 1.8 %), 0008/80 at most 13 %.

   Confidence: medium. 0008/80's 4° points are unsteady at Tu 0.1 % at
   0.75, 1.5 and 2.5 m/s, and the unsteady Tu 0.1 % points oscillate by up
   to 17 % (conclusion 6).
3. **0008/80 keeps its light-air advantage at Tu 0.1 %.**
   * At the 2° force it is the best finalist at both Tu up to 1 m/s, and at
     most 1.8 % above the best at any speed.
   * 0009/80 is 8-13 % above it at Tu 0.1 % (0.5-1 m/s), 0008/90 about 7 %.
4. **0009/100 is the best finalist at high load (the 6° force) at both Tu
   and all speeds.** 0008/90 comes next: 2-28 % above at Tu 0.1 %, 6-12 % at
   Tu 1 %. 0009/80 is 19-31 % above at Tu 0.1 %. Confidence: medium; most
   Tu 0.1 % points at 6° are unsteady.
5. **A single all-round fin: 0008/90 has the smallest average penalty,
   0009/80 the best working load.** Over all 30 comparisons among the four
   finalists (5 speeds × 3 forces × 2 Tu), the mean drag above the best
   finalist is:
   * 0008/90: 6.0 %;
   * 0009/80: 8.6 %;
   * 0009/100: 8.8 %;
   * 0008/80: 9.4 %.

   The worst cases are all at the 6° force (28-37 %), except 0009/100's
   26 %, which is at the 2° force. Which to choose still depends on how much
   of the sailing is at each load (open question).
   Confidence: low to medium. The averages weight every speed and load
   equally.
6. **Tu 0.1 % gives more drag than Tu 1 % at 4-8°, not less.**
   * Same cases, run 3 against run 2, median ΔCd by angle: −0.5 % at 0°,
     +1.2 % at 2°, +13 % at 4°, +16 % at 6°, +27 % at 8°.
   * Friction drag is 11 % lower and pressure drag 29 % higher (medians).
   * In the highlights at 1 m/s and 4°, the reversed-flow region on the
     suction side grows from x/c 0.25-0.68 to 0.09-0.58 (0008) and from
     0.28-0.68 to 0.16-0.70 (0009). Cf oscillates inside it, and the
     extracted `x_te_sep` (about 0.52-0.54) is an artefact of those
     oscillations.
   * The steady solver struggles more: 59 of 99 cases unsteady against 23,
     and the Cd oscillation of the unsteady cases above 0° is 1.7 % (median)
     and 17 % (90th percentile), against 0.6 % and 4.6 % at Tu 1 %.

   Confidence: medium on the direction, low on the size at 4° and above.
7. **At 0.5 m/s (Re 35k) and Tu 0.1 %, the laminar separation of the 80 mm
   finalists does not reattach.**
   * 0008/80 and 0009/80 separate at x/c 0.27-0.28 at 4° (0.60-0.67 at 2°),
     with reversed flow to the trailing edge.
   * Cl at 4° is 0.31-0.32, against 0.44 at Tu 1 %.
   * 0008/90 (Re 39.6k) still reattaches: Cl 0.46 at 4°. That cliff between
     Re 35k and 40k is why 0008/90 wins the 0.5 m/s, 4° comparison by
     6-20 %.

   At Tu 1 % the same open separation appeared only at 0.25 m/s (run 2).
   Unvalidated; read as a trend. Confidence: low.

Run 2's conclusions 2-3 (0008/80 and 0009/80 tied at working load; 0008
ahead in light air, 0009 at high load) hold at Tu 1 % only. At Tu 0.1 % the
working-load tie breaks toward 0009/80, while the light- and high-load
statements hold.

### Evidence

Drag at equal side force at Tu 0.1 %, from this run's
`report/selection_compare.md` (forces: what 0009/80 makes at 2/4/6° at
Tu 0.1 %; `*` = interpolated from an unsteady or not-converged point):

| speed [m/s] | aoa ref | side force [N] | lowest drag [N] | 0008/80 | 0008/90 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|---|
| 0.5 | 2° | 0.288 | 0.0675 | **best*** | +7%* | +8%* | +23%* |
| 0.5 | 4° | 1.15 | 0.111 | +6%* | **best*** | +12%* | +11%* |
| 0.5 | 6° | 2.04 | 0.164 | +20%* | +6% | +19% | **best*** |
| 0.75 | 2° | 0.563 | 0.128 | **best*** | +7%* | +11%* | +26%* |
| 0.75 | 4° | 3.78 | 0.252 | +6%* | **best*** | +0%* | +9%* |
| 0.75 | 6° | 4.65 | 0.306 | +26% | +12%* | +21%* | **best*** |
| 1 | 2° | 1.15 | 0.207 | **best*** | +7%* | +13%* | +23%* |
| 1 | 4° | 6.69 | 0.391 | +3% | +1%* | **best*** | +10%* |
| 1 | 6° | 8.33 | 0.488 | +37% | +18%* | +21%* | **best*** |
| 1.5 | 2° | 7.31 | 0.512 | +1%* | +2%* | **best*** | +10%* |
| 1.5 | 4° | 14.9 | 0.752 | +7%* | +4%* | **best*** | +6%* |
| 1.5 | 6° | 16.6 | 0.873 | +14%* | +2%* | +28%* | **best*** |
| 2.5 | 2° | 27.6 | 1.22 | +2%* | +2%* | **best*** | +16%* |
| 2.5 | 4° | 41.8 | 1.8 | +13%* | **best*** | +0%* | +1%* |
| 2.5 | 6° | 52.2 | 2.34 | +37%* | +28%* | +31%* | **best*** |

**Working-load force (4°), % above the best finalist at each Tu, at that
Tu's own forces.** The Tu 1 % rows are run 2 restricted to the four
finalists; interpolation as in the report, recomputed from both runs'
`report/selection.csv`.

| Tu | 0.5 | 0.75 | 1.0 | 1.5 | 2.5 m/s |
|---|---|---|---|---|---|
| 1 %, 0008/80 | 0.0 | 0.0 | 0.0 | 0.5 | 0.3 |
| 1 %, 0009/80 | 2.9 | 1.6 | 1.0 | 0.0 | 0.0 |
| 1 %, 0008/90 | 1.3 | 2.3 | 3.1 | 2.1 | 2.1 |
| 0.1 %, 0008/80 | 6.2 | 5.8 | 3.5 | 7.2 | 13.1 |
| 0.1 %, 0009/80 | 12.4 | 0.2 | 0.0 | 0.0 | 0.1 |
| 0.1 %, 0008/90 | 0.0 | 0.0 | 0.9 | 4.3 | 0.0 |

**Tu sensitivity of the winner** (as in run 1). Each candidate's drag was
compared at the same 15 forces (5 speeds × 3 force levels) under both Tu
values:
* the best finalist is the same at both Tu in 13 of 15 points with the
  forces from Tu 1 %, and 9 of 15 with the forces from Tu 0.1 %;
* where it differs, the Tu 1 % pick has 0.1-6 % more drag at Tu 0.1 %. The
  exception is 17.7 %: 0008/80 against 0008/90 at 0.5 m/s at the 1.57 N
  force (conclusion 7).

**Highlights** (1 m/s, 80 mm, Tu 0.1 %; reversed flow = where Cf < 0 on the
suction side in `surface.csv`, gaps under 0.05 c merged; run 2's Tu 1 %
values in brackets):

| aoa | foil | Cl | Cd | Cd_pressure | Cd_friction | reversed flow (x/c) | unsteady |
|---|---|---|---|---|---|---|---|
| 4 | 0008 | 0.450 (0.443) | 0.0180 (0.0157) | 0.0114 (0.0089) | 0.0066 (0.0068) | 0.09-0.58 (0.25-0.68) | no |
| 4 | 0009 | 0.465 (0.448) | 0.0187 (0.0164) | 0.0122 (0.0093) | 0.0065 (0.0071) | 0.16-0.70 (0.28-0.68) | no |
| 6 | 0008 | 0.572 (0.580) | 0.0307 (0.0270) | 0.0235 (0.0185) | 0.0072 (0.0084) | 0.01-0.20 (0.01-0.14) | no |
| 6 | 0009 | 0.579 (0.588) | 0.0280 (0.0250) | 0.0205 (0.0163) | 0.0075 (0.0087) | 0.01-0.25 (0.02-0.17) | yes |

Figures: `report/highlight_*.png` and `viz/highlights/*.png` of this run;
compare with run 2's.

### Decisions

None taken yet. Proposed (**not agreed**):
* Narrow to 0009/80 (working load, most robust over Tu) and 0008/90 (all
  round). Drop 0008/80 unless light air dominates, and 0009/100 unless heavy
  air does.
* Before choosing, settle the sailing-load weighting (open question).
* Check the two in 3D (`appendage3d`): tip, bulb and junction effects could
  be larger than these 1-6 % differences.
* A transient (`solver: transient`) check of 0009/80 and 0008/90 at 1 m/s,
  4° and 6°, Tu 0.1 %: the steady points there oscillate (conclusion 6).
  4 cases, roughly 4-8 case-hours (**not estimated from data**; no transient
  foil2d run so far).

### Assumptions

* As run 2: span, planform, lifting-line induced drag, reference forces,
  speeds (**not verified**, see run 1).
* Tu 0.1 % and 1 % bracket the pond (**not verified**; run 1 thought
  0.1-2 % plausible).
* The mesh check at 1 m/s, 80 mm, Tu 1 % (conclusion 1) stands for the
  other speeds, chords and Tu 0.1 % (**not verified**).
* Below Re ≈ 50,000 (0.5 m/s at every chord here) the transition model is
  **not validated**.

### Compromises

* Steady solver at Tu 0.1 %: 59 of 99 cases unsteady, with drag
  oscillations up to 17 % (90th percentile). Most Tu 0.1 % comparison
  points carry `*`.
* 9 not converged and 1 failed, none re-run.
* Same 2° aoa steps and interpolation as before. At Tu 0.1 % the drag curve
  between 2° and 4° is less linear (Cl at 2° is low: 0.08-0.10 at 1 m/s),
  so 4° force interpolations carry more error (not quantified).

### Learnings

* **Physics:**
  * lowering Tu lengthens the laminar separation bubble and raises pressure
    drag more than it saves in friction, from 4° up;
  * at Re 35k (0.5 m/s, 80 mm) Tu 0.1 % gives open separation where Tu 1 %
    did not.
* **Mesh:** medium and fine agree on bubble positions within 0.02 c
  (coarse within 0.03 c), and medium to fine moves Cd by ≤ 1.7 %
  (mesh-finalists).
* **Determinism:** the 4 medium cases in mesh-finalists repeat run 2's to
  3e-5 in Cd with a newer image.
* **Compute:**
  * 70.7 case-hours in 3.5 h on 3 VMs; the estimate was about 90;
  * Tu 0.1 % cases took 1.32× the Tu 1 % time on the same cases (1.31×
    iterations), not the 2× run 1 measured on the coarse mesh;
  * mesh-finalists: 5.9 case-hours in 1.0 h on 1 VM, with fine cases at 53
    min against 26 for medium;
  * about $2 for both jobs, from the ~$0.18/h Spot list price, not billing;
  * gzipped exports: the 9 highlight cases plus a mesh and 10 logs came to
    164 MB, about 16 MB per case against about 37 MB before.

### Open questions and next steps

* How the sailing divides between light, working and heavy air (side force
  by wind strength). It decides between 0009/80 and 0008/90.
* 3D check of 0009/80 and 0008/90 in `appendage3d`.
* Transient check of the unsteady working-load points at Tu 0.1 %.
* Highlights for a transient check:

  ```yaml
  highlights:
    - name: steady-vs-transient
      why: >
        Run 20261013-045759: at Tu 0.1 % the steady solution at 1 m/s has an oscillating Cf inside a
        long bubble (x/c 0.09-0.70 at 4 deg) and 13-16 % more drag than at Tu 1 %. Does a time-accurate
        run agree with the steady average?
      where: {speed: 1.0, aoa: [4, 6]}
      compare: solver
      views: [separation, transition]
  ```

## Run 20261012-175146 (2026-10-13, git 19a3176, GCP, 450 cases)

**Setup.** NACA 0006 / 0007 / 0008 / 0009 / 0012 × chord 80 / 90 / 100 mm ×
speed 0.25, 0.5, 0.75, 1.0, 1.5, 2.5 m/s × aoa 0-8° (step 2). Tu fixed at
1 %. kOmegaSSTLM, steady (simpleFoam), medium C-grid (90,112 cells). Whole
fin as in run 1: 360 mm span, lifting-line induced drag added (e = 0.9).
Image `iom-cfd:19a3176`, 4 × c3d-standard-16 Spot, 8 cases per VM.
Changes since run 1, as decided there:
* added 0007, 0008 and a 90 mm chord, because run 1 put the thickness
  optimum between 0006 and 0009;
* Tu fixed at 1 % (was 0.1 and 1 %);
* coarse mesh replaced by medium.

**Outcome.** 431 ok, 19 not converged (iteration limit; window average
used), 0 failed. The 19 are all 0006 (14) or 0007 (5), at 4° (5) or 8° (14).
117 of 450 are flagged unsteady, 61 of them at 0°.

### Conclusions

1. **Run 1's rankings hold on the medium mesh.**
   * Among run 1's six candidates, the lowest-drag one at each of the 18
     side forces (6 speeds × 3 forces) is the same in 17. The exception is
     1.5 m/s at the 2° force: 0006/100 and 0009/80 swap, 0.2 % apart.
   * On the 180 cases both runs share (Tu 1 %), medium-mesh Cd is 0.6 %
     below coarse (median); |ΔCd| is at most 2.6 % in 90 % of them, and
     |ΔCl| at most 0.005.
   * The two largest changes, −14 % and −11 %, are 0006/80 at 4° at 0.75 and
     0.5 m/s. Both are not converged and unsteady on the medium mesh.
   * On the 121 cases that are ok and steady in both runs, |ΔCd| ≤ 4.9 %.

   Confidence: high.
2. **At working load (the 4° force, 0.75 m/s and up), 0008/80 and 0009/80
   are tied.**
   * Over those 4 side forces, 0008/80 is 0-1.4 % above the lowest drag
     (mean 0.6 %) and 0009/80 0-3.0 % (mean 1.0 %). Head to head, 0008/80 is
     −1.5 % to +0.5 % against 0009/80.
   * 0007/90 is lowest at 0.75 m/s (interpolated from an unsteady point) but
     +6 % at 1.5 m/s and +11 % at 2.5 m/s.
   * The 0008/80 and 0009/80 points that set these comparisons are steady
     and converged.

   Confidence: high that the two are within about 3 % of each other; low on
   which is lower. The gap is smaller than the Tu sensitivity measured in
   run 1 (3-12 %) and similar to the coarse-medium change, and medium-to-fine
   is unknown.
3. **Between 0008/80 and 0009/80, the 0008 is ahead at light load and the
   0009 at high load.**
   * 0008/80 has 1-10 % less drag than 0009/80 at the 2° and 4° forces up to
     1 m/s.
   * It has 6-9 % more at the 6° force from 0.5 m/s up.
   * 0008/90 sits between them: 1-5 % less drag than 0009/80 at the 6° force
     (0.25-2.5 m/s), 2-3 % more at the 2° and 4° forces from 1.5 m/s up, and
     −7 % to +3 % everywhere else.

   Which is best overall depends on how the sailing time divides between
   light and heavy air, which is still unknown (run 1, open questions).
   Confidence: medium. Most of these differences are 2-9 %, at the limit of
   what this run resolves.
4. **At high load (the 6° force) the 100 mm chord still wins.**
   * 0009/100 is lowest from 0.75 m/s up, at all 4 speeds.
   * 0008/100 is within 0.2-1.9 % of it, and 0012/100 within 1.6-3.8 %.
   * At 0.5 m/s 0007/100 is lowest (0008/100 +0.4 %); at 0.25 m/s 0006/100
     (all points interpolated from unsteady ones).

   This confirms run 1 conclusion 3. Confidence: medium (steady solver). For the 0009, 90 mm has
   3-8 % more drag than 100 mm at this force from 0.5 m/s up.
5. **At light load (the 2° force) 0006/80 is still lowest up to 1 m/s.**
   0007/80 is within 0-5 % of the lowest at every speed (mean 2.7 %); it is
   the closest all-speed alternative at this load. Confidence: low below
   0.5 m/s (conclusion 7).
6. **Why thin sections lose at working load: the leading-edge bubble, not
   trailing-edge separation.** Highlight `thickness-at-working-load`, 1 m/s,
   80 mm.
   * At 4°, 0008, 0009 and 0012 stay laminar to x/c 0.25-0.28. A long
     mid-chord laminar separation bubble follows, reattaching at about 0.65
     to 0.68.
   * At 4° the 0006 separates at the leading edge (x/c 0.01) and reattaches
     by 0.18. It is then turbulent over the rest of the chord, so its
     friction drag is 31 % above the 0009's (Cd_f 0.00927 vs 0.00710) and its
     pressure drag 10 % above (0.0102 vs 0.0093).
   * 0007 is in between: reversed flow from 0.04 to 0.40, flagged unsteady.
   * At 6° every section but the 0012 has a leading-edge bubble, which ends
     at x/c 0.13-0.17. Friction is similar (Cd_f 0.0070-0.0087), but pressure
     drag rises steadily as the section thins: Cd_p 0.0272 (0006), 0.0221,
     0.0185, 0.0163 (0009), 0.0146 (0012).
   * Downstream of the bubble the thin sections have lower skin friction
     (figure), which suggests a thicker boundary layer.
   * No section separates at the trailing edge on the suction side, except
     the 0012 at 6° at x/c 0.99.

   This answers the highlight's question: the bubble does not grow as the
   section thins. On the 0006 it moves to the leading edge and the flow
   transitions there. Confidence: medium. Steady RANS with the
   transition model; the bubble extents are where Cf < 0 in surface.csv.
7. **At 0.25 m/s (Re 17,600) the laminar separation does not reattach.**
   Highlight `low-speed-bubble`, 4°, 80 mm.
   * Both 0006 and 0009 separate at mid-chord (x/c 0.51 and 0.39) with
     reversed flow to x/c 0.995: no transition, no reattachment.
   * Cl at 4° is 0.285 (0006) and 0.206 (0009), against 0.415 and 0.448 at
     1 m/s. The 0006 separates later, keeps 38 % more lift, and so needs a
     smaller angle for the same force. That is why it wins at light load.
   * At 0.5 m/s the 0009 separates at 0.26 with reversed flow to the
     trailing edge (Cl 0.436). The 0006 separates at the leading edge and
     has several reversed-flow regions up to x/c 0.95 (not converged,
     unsteady).

   So the light-air ranking rests on open laminar separation, a regime this
   method has not been checked in. Confidence: low.
8. **Chord at high load** (highlight `chord-at-high-load`, 0009, 1 m/s, 6°).
   At the same angle, a longer chord shortens the leading-edge bubble
   (reattachment at x/c 0.166, 0.147, 0.133 for 80, 90, 100 mm) and lowers
   Cd by 9 % (0.0250, 0.0238, 0.0228), with Cl within 1 %. At equal side
   force the 100 mm also runs at about 20 % lower Cl (25 % more area), which
   accounts for most of its 6° advantage. Confidence: medium.

**Run 1 conclusion 5 is superseded.** It said 0009/80 is the best single
choice. 0008/80 now matches it at working load, is better in light air and
worse in heavy air. Run 1 conclusions 1-3 stand for the candidates they
named. The study description's expectation that neighbouring candidates
would differ by "a few %, about the coarse-mesh error" holds: 0-3 % at
working load.

### Evidence

Drag at equal side force, from `report/selection_compare.md`, trimmed to 9
of the 15 candidates. Percentages are above the lowest drag at that force,
over all 15; the **lowest** column names the winner. Side forces are what
0009/80 makes at the reference angle. `*` = interpolated from an unsteady or
not-converged point; `-` = beyond that candidate's maximum side force. Not
shown: 0006/90-100, 0007/100, 0009/90, 0012/80-90.

| speed [m/s] | aoa ref | side force [N] | lowest drag [N] | lowest | 0006/80 | 0007/80 | 0007/90 | 0008/80 | 0008/90 | 0008/100 | 0009/80 | 0009/100 | 0012/100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.25 | 2° | 0.0898 | 0.0224 | 0006/80 | **best** | +2% | +9% | +6% | +12% | +18% | +10% | +25%* | +68% |
| 0.25 | 4° | 0.185 | 0.0246 | 0006/80 | **best** | +6%* | +10%* | +16%* | +20%* | +24%* | +29%* | +37%* | +76% |
| 0.25 | 6° | 0.5 | 0.0555 | 0006/100* | +6% | +4%* | +2%* | +5%* | +3%* | +2%* | +8%* | +5%* | +20% |
| 0.5 | 2° | 0.331 | 0.0639 | 0006/80 | **best** | +3%* | +10%* | +9%* | +16%* | +22%* | +17%* | +32%* | +61%* |
| 0.5 | 4° | 1.57 | 0.111 | 0006/90* | +8%* | +1%* | +3%* | +6% | +8%* | +11%* | +9% | +16% | +26%* |
| 0.5 | 6° | 2.07 | 0.148 | 0007/100 | +46% | +33% | +15% | +22% | +11% | +0% | +15% | +2% | +8% |
| 0.75 | 2° | 0.977 | 0.122 | 0006/80* | **best*** | +5%* | +11%* | +12% | +19%* | +26%* | +22%* | +33%* | +65%* |
| 0.75 | 4° | 3.63 | 0.217 | 0007/90* | +24%* | +2% | **best*** | +1% | +4% | +8%* | +3%* | +11%* | +17% |
| 0.75 | 6° | 4.71 | 0.292 | 0009/100 | +62% | +40% | +18% | +25% | +11% | +0% | +15% | **best** | +4% |
| 1 | 2° | 2.8 | 0.221 | 0006/80* | **best*** | +3%* | +7%* | +8%* | +10%* | +16%* | +10%* | +22%* | +47%* |
| 1 | 4° | 6.44 | 0.345 | 0008/80 | +28% | +6%* | +0%* | **best** | +3% | +7% | +1%* | +9% | +16% |
| 1 | 6° | 8.46 | 0.48 | 0009/100 | +76%* | +46% | +21%* | +26% | +12% | +1% | +16% | **best** | +2% |
| 1.5 | 2° | 8.53 | 0.471 | 0006/100 | +12%* | +3%* | +0%* | +0% | +2%* | +9%* | +0%* | +15%* | +28% |
| 1.5 | 4° | 14.6 | 0.694 | 0009/80 | +33% | +10%* | +6%* | +1% | +2% | +5% | **best** | +6% | +18% |
| 1.5 | 6° | 19.4 | 1.01 | 0009/100 | +91%* | +48% | +21%* | +23% | +11% | +2% | +14% | **best** | +2% |
| 2.5 | 2° | 23.7 | 1.03 | 0006/90* | +2% | +0% | +4% | +2% | +9% | +18% | +6% | +21% | +30% |
| 2.5 | 4° | 41.2 | 1.77 | 0009/80 | +30% | +16% | +11% | +0% | +2% | +7% | **best** | +9% | +14% |
| 2.5 | 6° | 55.3 | 2.71 | 0009/100 | +158%* | +42%* | +16% | +14% | +6% | +1% | +7% | **best** | +3% |

**Finalists head to head**, % drag against 0009/80 at the same side force
(from `report/selection_compare.csv`):

| speed [m/s] | 0008/80 at 2° / 4° / 6° force | 0008/90 at 2° / 4° / 6° force |
|---|---|---|
| 0.25 | −4.1 / −10.0 / −2.8 | +1.8 / −6.6 / −4.6 |
| 0.5 | −6.8 / −2.9 / +6.3 | −0.7 / −1.6 / −3.5 |
| 0.75 | −7.9 / −1.5 / +8.7 | −1.9 / +0.7 / −3.1 |
| 1.0 | −1.6 / −1.0 / +8.7 | −0.1 / +2.1 / −3.1 |
| 1.5 | +0.1 / +0.5 / +8.2 | +2.2 / +2.1 / −2.3 |
| 2.5 | −4.2 / +0.3 / +6.5 | +3.2 / +2.1 / −1.1 |

Worst case over the 12 rows from 0.75 m/s up, % above the lowest:
* 0007/100: 18 %;
* 0008/90: 19 %;
* 0007/90: 21 %;
* 0009/80: 22 %;
* 0008/80: 26 %.

The 2° rows, where 0006 wins, set all of these.

**Highlight `thickness-at-working-load`** (1 m/s, 80 mm; `report/highlights.md`
and `results.csv`; reversed-flow extents are where Cf < 0 on the suction side
in `surface.csv`):

| aoa | foil | Cl | Cd | Cd_pressure | Cd_friction | reversed flow, suction side (x/c) | unsteady |
|---|---|---|---|---|---|---|---|
| 4 | 0006 | 0.415 | 0.0195 | 0.0102 | 0.0093 | 0.01-0.18 | no |
| 4 | 0007 | 0.430 | 0.0156 | 0.0085 | 0.0071 | 0.04-0.40 | yes |
| 4 | 0008 | 0.443 | 0.0157 | 0.0089 | 0.0068 | 0.25-0.68 | no |
| 4 | 0009 | 0.448 | 0.0164 | 0.0093 | 0.0071 | 0.28-0.68 | no |
| 4 | 0012 | 0.474 | 0.0186 | 0.0110 | 0.0076 | 0.28-0.65 | no |
| 6 | 0006 | 0.566 | 0.0343 | 0.0272 | 0.0070 | 0.00-0.14 | no |
| 6 | 0007 | 0.573 | 0.0299 | 0.0221 | 0.0078 | 0.01-0.13 | no |
| 6 | 0008 | 0.580 | 0.0270 | 0.0185 | 0.0084 | 0.01-0.14 | no |
| 6 | 0009 | 0.588 | 0.0250 | 0.0163 | 0.0087 | 0.02-0.17 | no |
| 6 | 0012 | 0.610 | 0.0227 | 0.0146 | 0.0081 | 0.08-0.35 | no |

Figures: `report/highlight_*.png` (Cp, Cf) and `viz/highlights/*.png`
(ParaView montages).

**Mesh effect** (run 1 coarse vs this run's medium, the 180 shared Tu 1 %
cases): median ΔCd −0.6 %. 90th percentile of |ΔCd|: 1.2 % at 0°, 0.8 % at
2°, 2.4 % at 4°, 3.6 % at 6°, 2.9 % at 8°; 3.7 % for the 0006, 2.0 % for the
0009, 0.9 % for the 0012.

### Decisions

None taken yet. Proposed for the next run (**not agreed**):
* **Finalists:** 0008/80 and 0009/80 (tied at working load), 0008/90 (best
  balance over loads) and 0009/100 (heavy air). Drop 0006 and 0012, and
  0007 except as a light-air reference.
* **Tu 0.1 % check of the finalists**, as run 1 decided. 4 candidates ×
  5 speeds (0.5-2.5 m/s) × 5 angles = 100 cases. Estimated about 2× the
  Tu 1 % case time (run 1, coarse), so roughly 90 case-hours or about $2,
  from the Spot price in docs/cloud-gcp.md. The cost buys an answer to
  whether the 0-3 % tie survives a different Tu.
* **Fine-mesh check** of 0008/80 and 0009/80 at 1 m/s, 4° and 6° (4 cases),
  to see whether a 0-3 % gap can be resolved at all.

### Assumptions

* As run 1: 360 mm span, rectangular planform, lifting-line induced drag,
  no tip, bulb or junction effects; side forces of the 2/4/6° reference
  angles stand in for light, working and high load; the speeds and their
  meaning (**not verified**, see run 1).
* Tu = 1 % (run 1 decision; it matched the NACA 0009 tunnel drag at Re 1e5
  within 2-4 %, coarse mesh). The pond's real Tu is unknown.
* The medium mesh is close enough to mesh-independent. Coarse to medium
  moves Cd by under 3 % in 90 % of cases (this run). Medium to fine at these
  Re's is **not verified**.
* Transition model results below Re ≈ 50,000 (0.25 and 0.5 m/s) are taken
  at face value although **not validated**.

### Compromises

* Steady solver for unsteady flow. 117 of 450 cases flagged unsteady. At 0°
  (61 cases) the Cd oscillation is 0.06 % of Cd (median std/mean). For the
  56 unsteady cases above 0° it is 0.6 % (median) and 4.6 % (90th
  percentile). The finalists' points from 0.75 m/s up at 4-6° are all
  steady; at the 2° force several are unsteady (`*` in the table).
* 19 not converged, all 0006 or 0007 at 4° or 8°; window averages used. Two
  of them (0006/80 at 4°, 0.5 and 0.75 m/s) set 0006/80's 4° points.
* aoa in 2° steps with linear interpolation of drag against side force; the
  0-3 % differences in conclusion 2 are about the size of that
  interpolation error (not quantified).
* Tu fixed at 1 % (run 1 measured 3-12 % penalties where Tu swaps the
  winner).

### Learnings

* **Physics:**
  * at Re 70k and 4° the thin 0006 transitions at the leading edge and pays
    in friction;
  * at 6° thinner sections pay in pressure drag after the leading-edge
    bubble;
  * at Re 17.6k the model predicts open laminar separation from mid-chord
    and a large lift loss (Cl 0.2-0.3 at 4°).
* **Solver:** thin sections (0006, 0007) at 8° and at the edge of their
  bubble regime (4°) are where the steady solver doesn't converge.
* **Workflow:**
  * the default `gcp fetch` brought all 450 results down in 26 s;
  * the highlight fields (16 whole cases) plus 19 logs took 844 MB on disk,
    because this run predates the gzipped export (about 37 MB per case);
  * highlights chosen from run 1 answered their questions without opening
    any other case.
* **Compute:**
  * 235.8 case-hours (median 27.4 min per case, max 111); the job took 8.0 h
    on 4 VMs (32 cases in parallel);
  * cost about $5-6, from the ~$0.18/h Spot list price in
    docs/cloud-gcp.md, not from billing;
  * against run 1's coarse mesh on the same cases: 3.55× wall time =
    1.25× iterations × 2.83× time per iteration, for 1.99× the cells;
  * the pre-run estimate assumed 1.8× the coarse case time and was about
    2× low;
  * memory-bandwidth contention between the 8 cases on a VM is a possible
    cause, **not verified**.

### Open questions and next steps

* What side force the boat needs, by wind strength (open since run 1). It
  decides between 0008/80 (light to working) and 0009/80 or 0008/90 (working
  to heavy).
* The finalist check above: Tu 0.1 % and a fine-mesh pair.
* Light-air results (≤ 0.5 m/s) need validation data at Re 20-50k, or
  should be read as trends only.
* 3D check of the chosen fin in `appendage3d`.
* Highlights for the next run (if it sweeps Tu over the finalists):

  ```yaml
  highlights:
    - name: tie-at-working-load
      why: >
        Run 20261012-175146: 0008/80 and 0009/80 within 0-3 % at the 4 deg force from 0.75 m/s.
        Does Tu 0.1 % move transition differently on the two and break the tie?
      where: {foil: [naca0008, naca0009], chord: 0.08, speed: 1.0, aoa: 4}
      compare: Tu
      views: [separation, transition]
    - name: high-load-chord
      why: >
        Run 20261012-175146: 0008/80 has 6-9 % more drag than 0009/80 at the 6 deg force; 0008/90 is
        1-5 % below 0009/80. Is it the leading-edge bubble, and does it hold at Tu 0.1 %?
      where: {speed: 1.0, aoa: 6, Tu: 0.1}
      compare: foil
      views: [separation]
  ```

## Run 20261012-045433 (2026-10-12, git 360a33b, GCP, 360 cases)

**Setup.** NACA 0006 / 0009 / 0012 × chord 80 / 100 mm × speed 0.25, 0.5,
0.75, 1.0, 1.5, 2.5 m/s × Tu 0.1 / 1 % × aoa 0-8° (step 2). kOmegaSSTLM,
steady (simpleFoam), coarse C-grid (45,318 cells). Forces are for the whole
fin: 360 mm span, lifting-line induced drag added (hull as reflection plane,
e = 0.9). Image `iom-cfd:360a33b`, 2 × c3d-standard-16 Spot.

**Outcome.** 305 ok, 51 not converged (iteration limit; window average
used), 4 failed. 174 of the 356 finished cases are flagged unsteady.

### Conclusions

1. **At the side force a fin needs upwind, NACA 0009 at 80 mm has the
   lowest drag from 0.75 m/s up.** Compared at the force 0009/80 makes at 4°,
   at both Tu levels: 0009/100 is +2-10 %, 0012/80 +5-15 %, 0012/100 +14-22 %,
   0006/100 +6-23 % and 0006/80 +22-36 %, the 0006 because it is near its
   bubble/stall limit.
   Confidence: medium (coarse mesh; most of these points are unsteady).
2. **At low side force a thin, short fin wins.** At the 2° force, 0006/80
   has the lowest drag at speeds up to 1 m/s, 9-30 % below 0009/80. The
   absolute drag there is small (0.02-0.2 N). Confidence: medium; below
   0.5 m/s (Re < 45k) the method is unvalidated.
3. **At high side force a longer chord wins.** At the 6° force the best is
   0009/100 from 0.75 m/s up (0012/100 within 2-6 % at 1.5-2.5 m/s) and
   0006/100 below that. 0006/80 is +50-142 % from 0.75 m/s up because it is
   at or past stall.
4. **The thickness optimum for working loads lies between 0006 and 0009,
   and is untested.** 0006 wins light, 0009 wins working load; 0007 and 0008
   were not in this run, which is why run 2 adds them and a 90 mm chord.
5. **0009/80 is the best single choice of the candidates tested** if
   upwind working load matters most: lowest there from 0.75 m/s up. It gives
   up 9-30 % at light load (≤ 1 m/s, where drag is small) and 1-34 % at
   high load, where a 100 mm chord wins.

### Evidence

Drag at equal side force, Tu 1 %, from `report/selection_compare.md` (% above
the lowest drag at that force; side forces are what 0009/80 makes at the
reference angle; `*` = interpolated from an unsteady or not-converged
point; `-` = beyond that candidate's maximum side force). The Tu 0.1 % table
is in the run's report and gives the same winners in the working-load (4°)
rows from 0.75 m/s up.

| speed [m/s] | aoa ref | side force [N] | lowest drag [N] | 0006/80 | 0006/100 | 0009/80 | 0009/100 | 0012/80 | 0012/100 |
|---|---|---|---|---|---|---|---|---|---|
| 0.25 | 2° | 0.0882 | 0.0225 | **best** | +12% | +10%* | +24%* | +54%* | +68% |
| 0.25 | 4° | 0.186 | 0.0248 | **best** | +6%* | +29%* | +37%* | +73%* | +76% |
| 0.25 | 6° | 0.497 | 0.0564 | +7% | **best*** | +6%* | +4%* | - | +17% |
| 0.5 | 2° | 0.327 | 0.0642 | **best** | +12%* | +17%* | +32%* | +47%* | +61%* |
| 0.5 | 4° | 1.58 | 0.118 | +6% | **best*** | +3%* | +9%* | +14%* | +19%* |
| 0.5 | 6° | 2.06 | 0.149 | +46% | +18%* | +15% | **best** | +14% | +7%* |
| 0.75 | 2° | 0.97 | 0.122 | **best*** | +13%* | +22%* | +33%* | +45%* | +66% |
| 0.75 | 4° | 3.64 | 0.224 | +22% | +16%* | **best*** | +8%* | +9% | +14% |
| 0.75 | 6° | 4.69 | 0.29 | +66% | +26% | +17% | **best** | +10% | +4% |
| 1 | 2° | 2.8 | 0.221 | **best*** | +4%* | +10%* | +22%* | +32% | +48%* |
| 1 | 4° | 6.45 | 0.349 | +30% | +23%* | **best*** | +8% | +9% | +15% |
| 1 | 6° | 8.44 | 0.478 | +81% | +31% | +17% | **best** | +7% | +3% |
| 1.5 | 2° | 8.58 | 0.473 | +12%* | +0%* | **best*** | +15%* | +17% | +28% |
| 1.5 | 4° | 14.7 | 0.697 | +36% | +22% | **best** | +6% | +8% | +18% |
| 1.5 | 6° | 19.4 | 1 | +105%* | +33% | +15% | **best** | +4% | +2% |
| 2.5 | 2° | 24 | 1.07 | **best** | +6%* | +3% | +17% | +19% | +27% |
| 2.5 | 4° | 41.4 | 1.78 | +31% | +16%* | **best** | +9% | +5% | +14% |
| 2.5 | 6° | 55.3 | 2.71 | +142%* | +25%* | +8% | **best** | +0% | +3% |

At 1 m/s and the 4° force (6.45 N) the induced drag is about 0.11 N of
the 0.35 N total, the same for every candidate.

**Sensitivity to turbulence intensity (Tu 0.1 % vs 1 %), at a common side
force.** Each candidate's drag was compared at the same force under both Tu
values (17-18 comparison points: 6 speeds × 3 force levels):

* lowest-drag candidate the same: 10 of 17 points (forces taken from Tu 1 %)
  or 15 of 18 (forces from Tu 0.1 %);
* Spearman rank correlation of the six candidates: median 0.77-0.94, worst
  0.10-0.31;
* where the winner differs, the Tu 1 % winner has 3-12 % more drag than the
  Tu 0.1 % winner when the water is really Tu 0.1 %. The swaps are always
  between neighbouring candidates: chord (80 vs 100 mm) at 0.5 and
  1.5-2.5 m/s, 0006 vs 0009 at light load, and 0009 vs 0012 at high load;
* absolute drag differs by 8-12 % on average between the two Tu values;
* Tu 0.1 % converges much worse: 46 of 180 not converged and 4 failed,
  against 5 of 180 not converged at Tu 1 %. The Tu 0.1 % mean case time is
  18.6 min against 9.2.

### Decisions

* **Run 2 fixes Tu = 1 %** (half the compute). Basis: the working-load
  winner (4° force, 0.75 m/s and up) is 0009/80 at both levels when each
  level uses its own 4° force; at exactly the same force, Tu 0.1 % prefers
  0009/100 at 1.5 and 2.5 m/s, by 9 and 3 %. Tu 1 % matched the NACA 0009 wind-tunnel
  drag at Re 1e5 within 2-4 % at 4° and 8° (`validation-naca0009-re1e5`,
  coarse mesh, possibly compensating errors); far better convergence. Cost
  of the assumption: candidates within ~10 % of each other can swap at
  another Tu, so finalists get a Tu 0.1 % check.
* **Run 2 uses the medium mesh** and adds NACA 0007 and 0008 and a 90 mm
  chord (conclusion 4): 450 cases.

### Assumptions

* Fin span 360 mm (appendage3d default, set by the class draught limit);
  rectangular planform; 2D section forces × span plus lifting-line induced
  drag. No tip, bulb or fin-hull junction effects. Same span for every chord.
* Upwind side force for an IOM in a moderate breeze about 5-8 N, which makes
  the 1 m/s, 4° row "typical upwind". **Not verified**: a back-of-envelope
  estimate (about 2.5 kg of bulb at about 0.42 m, about 20° heel, about a
  0.5 m heeling arm).
* Speeds: hull speed about 1.25 m/s (Fn 0.4, 1 m waterline); 2.5 m/s downwind
  from a reported championship average of about 5 kn (search summary, **not
  verified**).
* Pond turbulence intensity unknown; 0.1-2 % thought plausible.
* Steady RANS averages stand in for unsteady flow (shedding laminar bubbles).

### Compromises

* Coarse mesh (45k cells). In `mesh-naca0009-re1e5` (Tu 0.1 %, Re 1e5)
  coarse vs medium: Cd within 0.2 % at 2° and 4.3 % at 8°, Cl within 4.4 %.
  Small next to most differences above, but similar to the 0009/80 vs
  0009/100 margins (2-10 %).
* Steady solver for unsteady flow. 174 of 356 finished cases are flagged
  unsteady, 54 of them at 0°. There the flag is set by Cl oscillating around
  zero; the drag oscillates by only 0.2 % (median), so 0° drag is usable.
* The 4 failed cases (floating-point exceptions, all Tu 0.1 %, ≤ 0.5 m/s,
  6-8°) were not re-run with lower relaxation. They don't affect the
  working-load comparison.
* The comparison uses 2° steps in aoa and linear interpolation of drag
  against side force.

### Learnings

* **Thick sections show low-Re lift reversal.** 0012/80 at 0.5 m/s, Tu 0.1 %
  makes -0.03 N at 2°, less than at 0°. This is consistent with the lift
  reversal reported for thick sections at low Re (not checked against
  measurements here). The comparison now skips such a dip instead of
  ending the curve there.
* Tu 1 % halves the wall time and nearly removes the convergence problems.
  Tu 0.1 % at 4-8° is where the steady solver struggles.
* Thin sections lose most at high load: 0006/80 at the 6° force is
  +50-142 % from 0.75 m/s up.
* Compute: 83.2 case-hours; the job took 5.7 h on 2 VMs because it was
  submitted with `--parallelism 16` (the quota was 24 vCPUs at the time; it
  is now 64, enough for 4 VMs). Cost was about $1.7, estimated from a
  third-party Spot price rather than billing.

### Open questions and next steps

* Run 2: NACA 0006/0007/0008/0009/0012 × 80/90/100 mm, Tu 1 %, medium mesh.
* Check the 2-3 finalists at Tu 0.1 % (and with `solver: transient` where
  they are unsteady) before choosing.
* What side force does the boat actually need, by wind strength? A
  measurement or VPP estimate would replace the 2/4/6° reference forces.
* 3D check of the chosen fin in `appendage3d` (tip, bulb, junction).
