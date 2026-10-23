# fin-profile-selection: findings log

Newest run first. One entry per run (or per analysis that combines earlier
runs without new cases): conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results themselves live
in `runs/fin-profile-selection/<run id>/` (not in git), so the numbers that
support a conclusion are copied here. Entries are written by the
`study-findings` skill (`/study-findings foil2d/fin-profile-selection`) or by
hand, and are not rewritten later: a later run that changes a conclusion says
so in its own entry. The exception is "Where the selection stands" below: it
is the current summary and is updated in place.

Symbols follow [docs/nomenclature.md](../../../docs/nomenclature.md). On
2026-10-18 the symbols in earlier entries were changed to it: side force S_h
(was F), fin drag D_h = D_v + D_i (was D = D_s + D_i), leeway β_Y (was λ),
the course's true wind angle β_TW (was θ, "track"), boat speed V_b and the
resistance slope dD_h/dV_b (was dR/dV). Only the notation changed. `Cl`,
`Cd` and `aoa` are output and parameter names and stay.

## Where the selection stands (updated 2026-10-17, after transient-check run 20261017-000816)

**Update 2026-10-21: a non-NACA section beats the NACA 0007/100
recommended below** ([custom-section.md](custom-section.md)). M. Drela's
HT35 scaled to 7.25 % at 100 mm, as stiff as 0007/100:
* time-accurate CFD at Tu 0.1 %: 0.66 / 0.38 % of race time ahead, at
  every speed and load (with 0007/100's from-rest point at 1.5 m/s;
  revised 2026-10-23 from 0.82 / 0.44 %);
* Tu 1 %: 0.34 / 0.20 %;
* Tu 2 %: break-even.

Two points there also bear on the NACA ranking below:
* NACA 0007/100's high-drag leading-edge bubble at 1.5 m/s and 4° comes
  only from a start at its steady solution; from rest it sheds
  (transient-check.md);
* the 2° angle grid used here moves candidates by up to 0.5 % of race time.

The rest of this summary is as of 2026-10-17.

**Metric.** The current metric is the race time lost on a windward-leeward
course with equal time upwind and downwind:
* upwind: the fin's drag at equal side force, plus the leeway it needs;
* downwind: the fin's drag at 0°.

It was built up over runs 1-3 and the two analyses of 2026-10-13; the
method is written up in [../methodology.md](../methodology.md). The
drag-only comparison of runs 1-3 favoured 80 mm chords. Counting leeway
moves the balance back toward 90-100 mm, because a longer chord makes the
same side force at a lower angle.

**Settled (high confidence):**
* The medium mesh resolves the differences that matter (`mesh-finalists`).
* NACA 0012 is out. It is never the best at light or working load (at
  least 5 % more drag than the best in run 2), and loses 2.2-5.1 % of race
  time on average at Tu 1 %.
* At 6° and 1 m/s the flow is steady
  ([transient-check.md](transient-check.md)). The steady drag is within
  0.5 % for 0009/80 and 0009/100, but 4-6 % high for 0007/100, 0007/90 and
  0008/100.
* At 4° the sections shed at 0.75, 1 and 1.5 m/s (Cl oscillates about
  10 %). The exception is 0007/100 at 1.5 m/s (below).
* The steady 4° points are 2-16 % off in lift and 5-15 % in drag.

**The choice is now between 0007/100, 0007/90 and 0008/100.** Confidence
that the best fin is one of these: medium. Confidence in the order between
them: low. Not agreed.

**Time-accurate results at three speeds.** Top four, race-time loss, %
behind the best of the four. Mean over the light, working and high loads;
estimated resistance slope / doubled.

| section | 0.75 m/s | 1.0 m/s | 1.5 m/s | mean of the three |
|---|---|---|---|---|
| 0007/100 | 0.27 / 0.12 | 0.39 / 0.19 | 1.58 / 0.68 | 0.75 / 0.33 |
| 0007/90 | 0.82 / 0.53 | 0.84 / 0.55 | 0.83 / 0.50 | 0.83 / 0.53 |
| 0008/100 | 1.05 / 0.56 | 1.09 / 0.55 | 0.58 / 0.14 | 0.91 / 0.41 |
| 0008/90 | 1.19 / 0.75 | 1.71 / 1.07 | 0.70 / 0.39 | 1.20 / 0.74 |

What goes into the table:
* At 1 m/s all three angles are time-accurate, except 0008/90 at 6°.
* At 0.75 and 1.5 m/s only the 4° points are time-accurate.

**0007/100 is first at 0.75 and 1 m/s, by 0.45-0.55 % of race time (0.36-0.41
with the slope doubled).**
* At 1 m/s it is first of all seven. The three outside the top four trail by
  1.8-2.9 %.
* Its weakest loads are mild:
  * light air: 0.8 / 0.4 behind 0007/90;
  * high load: 0.35 / 0.20 behind 0008/100.

**At 1.5 m/s it is last of the four, 1.0 / 0.5 behind 0008/100.**
* In the time-accurate run its 4° flow changed: a leading-edge bubble
  followed by turbulent, attached flow.
* Its drag there is 21-26 % above the other three's.
* This is one case, from a steady start. Confidence: low.
* With steady points at 1.5 m/s it was first.

**Different winds favour different fins** (user, 2026-10-17: state it
plainly, and quantify).
* **Light and medium air (0.75-1 m/s): 0007/100.**
  * It leads 0007/90 by about 0.5 % of race time, about 2 boat lengths.
  * It leads 0008/100 by 0.7-0.8 %, about 3 boat lengths.
* **Fresh air (1.5 m/s): 0008/100.** It leads 0007/100 by about 1 %, about
  4 boat lengths (low confidence; check running).

**What one fin for every wind gives away.** Each fin's loss at each speed,
minus the best fin's there (the fin you'd fit if you could change keels).
% of race time, estimated slope / doubled. Derived from the table above;
4.2 boat lengths per 1 % (**estimate**).

| fin | 0.75 m/s | 1 m/s | 1.5 m/s | average | boat lengths |
|---|---|---|---|---|---|
| 0007/100 | best | best | 1.00 / 0.54 | 0.33 / 0.18 | 1.4 / 0.8 |
| 0007/90 | 0.55 / 0.41 | 0.45 / 0.36 | 0.25 / 0.36 | 0.42 / 0.38 | 1.8 / 1.6 |
| 0008/100 | 0.78 / 0.44 | 0.70 / 0.36 | best | 0.49 / 0.27 | 2.1 / 1.1 |
| 0008/90 | 0.92 / 0.63 | 1.32 / 0.88 | 0.12 / 0.25 | 0.79 / 0.59 | 3.3 / 2.5 |

**Proposed best all-round fin: 0007/100.** Confidence: medium.
* It gives away the least on average: 0.33 / 0.18 %, about 1.4 boat lengths
  per race.
* All of its cost is in fresh air.
* **If the check confirms the leading-edge bubble and finds it already at
  1.25 m/s,** 0008/100 would likely become the better all-round fin
  (**estimate**: with 1.25 m/s like 1.5 m/s and four speeds weighted
  equally, 0.50 against 0.37).
* **0007/90 is the most even** (never more than 0.55 % behind), but it is
  the least stiff of the three.
* **Stiffness doesn't rule out 0007/100**
  ([docs/research/fin-stiffness.md](../../../docs/research/fin-stiffness.md)).
  * At 100 mm it is about 50 % stiffer at the root than a 7 %, 90 mm fin of
    the same construction (**estimate**).
  * No source quantifies what extra stiffness is worth.

**Bending stiffness**, ∝ c t³ for sections of the same shape family and
material, relative to 0008/90 (**estimate**; ignores construction and
taper):

| section | stiffness |
|---|---|
| 0007/100 | 1.02 |
| 0008/100 | 1.52 |
| 0007/90 | 0.67 |

**Superseded.**
* "0008/90 is the safest choice" (2026-10-13, run 20261013-200643). With
  time-accurate points it is fourth at every speed but 1.5 m/s.
* "0007/100 is first or second in every comparison" (2026-10-16). It is
  last of the four at 1.5 m/s with the time-accurate 4° points.
* "At 6° the steady results stand" (2026-10-16). That holds for 0009 only
  (above).

**Why the order is uncertain:**
* **0007/100 at 1.5 m/s rests on one case.** Separation bubbles are the
  transition model's weak spot, and that case was not repeated from another
  start.
* **Some points are still steady:**
  * 2° and 6° at 0.75 and 1.5 m/s;
  * 0008/90 at 6°, 1 m/s;
  * everything at 0.5 m/s.
* **0008 at 2° has not settled** (light air).
* **2D.** Tip, bulb, junction and heel effects are not modelled.
* **Estimated inputs.**
  * The resistance slope and Tu on the water are estimates.
  * The hull and rudder share of side force is left out.
  * Every speed and load is weighted equally. Nobody has said how the
    sailing divides between them.

**How much is at stake.** Averaged over 0.75-1.5 m/s, the top three are
within 0.16 % of race time, and 0008/90 is 0.45 behind the best. Over a
2-lap course of 90 m legs (about 420 m sailed), 1 % of race time is about
4 boat lengths (docs/research/surface-roughness.md; **estimate**).

**What would settle it (proposed, not agreed):**
1. **0007/100 at 1.5 m/s and 4°, started from rest**; then 1.25 m/s if the
   leading-edge bubble returns (2-3 cases, up to 16 h each).
2. **The sailing weighting.** Which wind range matters most (user).
3. **A hull resistance curve:** the `hull` project at 0.5-1.5 m/s (Wigley
   validation first), to replace the resistance estimate.
4. **A 3D check of 0007/100 and 0008/100** (`appendage3d`).
5. **Fin stiffness in practice:** layup, and deflection under the
   working-load side force (6.7 N at 1 m/s and Tu 0.1 %).

**Done since 2026-10-16:**
* time-accurate 2° and 6° at 1 m/s;
* time-accurate 4° at 0.75 and 1.5 m/s (transient-check run 20261017-000816).

**On hold.** A trip-strip study on the fin (forcing transition at a chosen
chord position; [docs/research/surface-roughness.md](../../../docs/research/surface-roughness.md))
waits until a section is recommended (user, 2026-10-15). A trip would also
decide the 1.5 m/s question in practice: it fixes where the boundary layer
turns turbulent.

## Run 20261013-200643 (2026-10-13, git 44a27af, GCP, 75 cases)

**Setup.** 0007/90, 0007/100 and 0008/100 at Tu 0.1 %: the three run-2
candidates that lead under the race-time metric at Tu 1 % (analysis
2026-10-13 (2)). 0.5, 0.75, 1.0, 1.5 and 2.5 m/s × aoa 0-8° (step 2); foil
and chord zipped. kOmegaSSTLM, steady, medium mesh (90,112 cells). Image
`iom-cfd:19e49d8`, the one run 3 used, so all seven candidates have Tu 0.1 %
results from the same solver. c3d-standard-16 Spot.

Why: these three had no Tu 0.1 % results, and most of their Tu 1 % upwind
points were unsteady or not converged.

How this entry compares runs:
* All seven candidates are ranked together at Tu 0.1 % (runs 3 and 4) and
  at Tu 1 % (run 2), using the same 0009/80 forces at 2, 4 and 6° as before
  (run 3's for Tu 0.1 %).
* The numbers come from `report/selection.csv`, with the race-time metric
  and pre-stall interpolation of analysis 2026-10-13 (2).
* This run's own `selection_compare.md` uses 0007/90's forces, so it can't
  be compared with other runs (Learnings).

**Outcome.** 57 ok, 17 not converged, 1 failed. 43 of the 74 finished cases
are flagged unsteady; the same 75 cases at Tu 1 % (run 2) had 22 unsteady and
4 not converged.
* The failure is 0007/90 at 0.5 m/s and 8°: a floating-point exception at
  iteration 333. It doesn't affect the comparisons at the 2/4/6° forces.
* 11 of the 17 not-converged cases are at 4°: every speed of 0007/100,
  every speed but 0.75 m/s of 0007/90, and 0008/100 at 1.5 and 2.5 m/s.

### Conclusions

1. **At Tu 0.1 %, as at Tu 1 %, the four thinner or longer sections lose
   the least race time: 0008/100, 0007/100, 0007/90 and 0008/90.**
   * Mean loss over 0.5-1.5 m/s and the three loads, with the estimated
     resistance slope / with it doubled (% of race time above the best
     candidate at each point):
     * 0008/100: 1.06 / 0.50;
     * 0007/100: 1.21 / 0.65;
     * 0007/90: 1.25 / 0.77;
     * 0008/90: 1.25 / 0.74.
   * The other three finalists:
     * 0009/100: 2.05 / 0.94;
     * 0008/80: 2.22 / 1.47;
     * 0009/80: 2.66 / 1.71.
   * The four leaders are within 0.19 / 0.27 points of each other. At Tu 1 %
     the same four lead, in the order 0007/100, 0008/100, 0007/90, 0008/90.

   Confidence: low, because the ranking rests on 4° points the steady solver
   can't settle (conclusion 4).
2. **Each load has a different leader, as at Tu 1 %.**
   * **Light load (2° force): 0007/90.** Mean loss 0.00 / 0.04. It is best
     at every speed with the estimated slope (3 of 4 with it doubled), with
     0008/80 next at 0.25 / 0.31.
   * **Working load (4° force): 0007/90.**
     * Mean loss 0.03 / 0.02, never more than 0.13 / 0.06.
     * Next are 0008/90 (0.65 / 0.26) and 0007/100 (0.67 / 0.27).
   * **High load (6° force): 0008/100.**
     * Mean loss 0.16 / 0.11, with 0009/100 next at 0.61 / 0.25.
     * 0007/90 is 3.70 / 2.25 behind; its upwind drag there is 18-30 %
       above the best.
   * **Downwind (0°):** 0008/80 has the least drag, and 0007/90 is within
     0-2.9 % of it. The others are higher:
     * 0007/100: +6-9 %;
     * 0008/90: +6-7 %;
     * 0008/100: +12-14 %;
     * 0009/100: +20-25 %.
3. **Lowering Tu from 1 % to 0.1 % raises drag by about the same amount for
   all seven, so it barely changes the ranking.**
   * The change in Cd (same cases, 0.5-1.5 m/s):
     * at 4°: +8 to +20 % for 0007/90, −1 to +21 % for 0007/100 and +7 to
       +16 % for 0008/100, against +8 to +18 % for the finalists;
     * at 6°: +7 to +22 % for all seven.
   * Lift at 2° falls for all seven: by 8-59 % in 26 of 28 comparisons
     (0008/90 −7.6 % and 0009/100 +2.9 %, at one speed each). This is the
     low-Re lift deficit near 0°.
   * The same four candidates lead at both Tu (conclusion 1).
4. **The steady solver can't settle the 4° points, and the working-load
   ranking rests on them.**
   * **Oscillation of the forces.** At Tu 0.1 % the largest Cd oscillation
     at 4° (standard deviation over the averaging window, as % of Cd,
     0.5-1.5 m/s) is:
     * 14 % for 0007/90;
     * 18 % for 0007/100;
     * 22 % for 0008/100;
     * 3-8 % for the finalists.

     Cl oscillates by up to 10-17 % for the three new candidates.
   * **Highlight `thin-at-working-load` (0007, 1 m/s).**
     * At 4°: laminar separation at 0.03 c on both chords, then Cp and Cf
       oscillate along the whole suction side. The shapes suggest vortices
       shed from the bubble; the flow fields haven't been opened to check.
       Both cases hit the iteration limit.
     * At 6°: a short leading-edge bubble, reattaching at 0.049 c (90 mm)
       and 0.038 c (100 mm), then steady attached flow.
   * **Sensitivity check.** I dropped every candidate's 4° point and
     interpolated linearly between 2° and 6°. This is crude, because it
     overstates the drag in between for every candidate. Even so, it
     reorders the Tu 0.1 % ranking. Mean loss with the estimated slope:
     * 0008/80: 0.66;
     * 0009/80: 0.90;
     * 0008/90: 0.97;
     * 0007/90: 1.20;
     * 0008/100: 1.42;
     * 0007/100: 1.49;
     * 0009/100: 2.04.

   Confidence: high that the 4° points are unreliable; the size of the
   error is unknown.
5. **0008/90 is the safest choice: it stays closest to the best whichever
   way the comparison is done.**
   * I compared the candidates eight ways:
     * Tu 1 % or 0.1 %;
     * the estimated resistance slope or double it;
     * with or without the 4° points.
   * In each, a candidate's regret is its mean race-time loss minus the
     best candidate's. The largest regret over the eight is:
     * 0008/90: 0.47;
     * 0008/100: 0.85;
     * 0007/90: 0.87;
     * 0007/100: 1.08;
     * 0008/80: 1.16;
     * 0009/100: 1.38;
     * 0009/80: 1.59.
   * At working load alone 0008/90's largest regret is 0.62; the next
     smallest is 1.07.
   * Taking the 4° points at face value (the four variants that keep them),
     0007/100 (0.15) and 0008/100 (0.23) lead, ahead of 0008/90 (0.47).

   Confidence:
   * medium that 0008/90 is a safe choice;
   * low on which candidate is best.
6. **0007/100 keeps its light-air advantage over 0008/100 at Tu 0.1 %**
   (highlight `light-air`, 0.5 m/s).
   * It has 5.6 % less drag at the 2° force and 6.5 % less at the 4° force
     (5 % at Tu 1 %).
   * At 4° the two sections behave differently:
     * 0008/100 separates at 0.08 c and reattaches at 0.95 c, a bubble over
       most of the chord; Cl 0.468.
     * 0007/100 separates at 0.30 c and reattaches at 0.86 c; Cl 0.378,
       oscillating and not converged.
7. **At 6° and 1 m/s, 0007/100 has 11 % more drag than 0008/100 at almost
   the same lift** (highlight `thickness-at-100mm`).
   * Cl 0.570 against 0.573; Cd 0.0313 against 0.0281.
   * Friction is lower on 0007 (0.0065 against 0.0070), but pressure drag
     is 18 % higher (0.0247 against 0.0210).
   * Both have a short leading-edge bubble: 0007 from 0.025 to 0.038 c,
     0008 from 0.035 to 0.051 c.
   * The surface plots don't show why the pressure drag is higher.

### Evidence

**Race-time loss at Tu 0.1 %**, % of race time above the best candidate at
each point, with the estimated resistance slope / doubled. Means are over
0.5, 0.75, 1.0 and 1.5 m/s; "worst" is the largest over all 12 points.
Thickness is at the 2D section's maximum.

| candidate | thickness [mm] | all loads | light (2°) | working (4°) | high (6°) | worst |
|---|---|---|---|---|---|---|
| 0008/100 | 8.0 | 1.06 / 0.50 | 1.70 / 0.86 | 1.34 / 0.52 | 0.16 / 0.11 | 2.19 / 1.17 |
| 0007/100 | 7.0 | 1.21 / 0.65 | 0.71 / 0.35 | 0.67 / 0.27 | 2.25 / 1.35 | 3.37 / 2.03 |
| 0007/90 | 6.3 | 1.25 / 0.77 | 0.00 / 0.04 | 0.03 / 0.02 | 3.70 / 2.25 | 4.59 / 2.79 |
| 0008/90 | 7.2 | 1.25 / 0.74 | 1.01 / 0.60 | 0.65 / 0.26 | 2.11 / 1.35 | 3.08 / 1.97 |
| 0009/100 | 9.0 | 2.05 / 0.94 | 3.08 / 1.56 | 2.46 / 1.03 | 0.61 / 0.25 | 3.95 / 2.19 |
| 0008/80 | 6.4 | 2.22 / 1.47 | 0.25 / 0.31 | 1.29 / 0.84 | 5.13 / 3.27 | 6.83 / 4.26 |
| 0009/80 | 7.2 | 2.66 / 1.71 | 1.47 / 1.00 | 1.17 / 0.68 | 5.33 / 3.45 | 6.11 / 3.87 |

**Regret over the eight variants.** Mean race-time loss over all loads,
minus the best candidate's mean. "×1" is the estimated resistance slope,
"×2" double it.

| Tu | 4° points | slope | 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0008/80 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 % | kept | ×1 | 0.18 | 0.14 | **0** | 0.19 | 1.16 | 1.59 | 0.98 |
| 0.1 % | kept | ×2 | 0.27 | 0.15 | **0** | 0.24 | 0.97 | 1.21 | 0.44 |
| 0.1 % | dropped | ×1 | 0.55 | 0.83 | 0.76 | 0.32 | **0** | 0.24 | 1.38 |
| 0.1 % | dropped | ×2 | 0.11 | 0.12 | 0.08 | **0** | 0.01 | 0.19 | 0.41 |
| 1 % | kept | ×1 | 0.39 | **0** | 0.23 | 0.47 | 1.00 | 0.97 | 0.97 |
| 1 % | kept | ×2 | 0.37 | **0** | 0.08 | 0.38 | 0.87 | 0.83 | 0.42 |
| 1 % | dropped | ×1 | 0.87 | 1.08 | 0.85 | 0.47 | 0.42 | **0** | 0.99 |
| 1 % | dropped | ×2 | 0.29 | 0.23 | 0.09 | 0.06 | 0.25 | **0** | 0.11 |
| largest | | | 0.87 | 1.08 | 0.85 | **0.47** | 1.16 | 1.59 | 1.38 |

**Upwind drag at equal side force, Tu 0.1 %** (whole fin; % above the
lowest of the seven; * = interpolated from an unsteady or not-converged
point):

| load | speed [m/s] | 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0008/80 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|---|---|
| 2° | 0.5 | +1.0* | +6.7* | +13.0* | +7.1* | best* | +8.4* | +22.7* |
| 2° | 0.75 | best* | +5.6* | +13.8* | +7.2* | +0.1* | +10.7 | +26.3* |
| 2° | 1.0 | best* | +6.2* | +16.3* | +9.4* | +2.1* | +15.6* | +26.0* |
| 2° | 1.5 | +0.3* | +1.9* | +2.9* | +2.4* | +1.0* | best* | +10.4* |
| 2° | 2.5 | +4.5* | +2.8* | +7.6* | +1.7* | +1.8* | best* | +15.8* |
| 4° | 0.5 | +0.2* | best* | +7.0* | +4.7* | +11.1* | +17.7 | +16.0* |
| 4° | 0.75 | +1.1* | best* | +7.8* | +3.8* | +9.7* | +4.0* | +13.3* |
| 4° | 1.0 | best* | +8.4* | +6.1* | +2.1* | +4.7 | +1.2 | +11.1* |
| 4° | 1.5 | +4.4* | +6.9* | +5.1* | +4.3* | +7.2* | best | +5.9* |
| 4° | 2.5 | +4.8* | +5.0* | +0.8* | best* | +13.1* | +0.1* | +1.4* |
| 6° | 0.5 | +18.2* | +15.3* | best* | +10.9 | +25.7* | +24.8 | +4.9* |
| 6° | 0.75 | +22.3* | +14.2* | best* | +12.5* | +26.5 | +21.5 | +0.2* |
| 6° | 1.0 | +28.3* | +19.6* | +5.3* | +18.1* | +36.8 | +21.3* | best* |
| 6° | 1.5 | +17.8* | +2.7* | best* | +4.7* | +16.7* | +31.1* | +2.1* |
| 6° | 2.5 | +29.5* | +27.5* | +9.6* | +27.7* | +36.6* | +31.2* | best* |

At Tu 0.1 %, 11-12 of the 12 upwind points at 0.5-1.5 m/s are marked * for
every candidate except 0008/80 (9) and 0009/80 (6). At Tu 1 % the counts are
10 (each 0007), 6 (0008/100), 5 (0008/90, 0009/100) and 2 (0008/80,
0009/80).

**Downwind drag at 0°, Tu 0.1 %** (% above 0008/80):

| speed [m/s] | 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|
| 0.5 | +2.9 | +8.5 | +12.4 | +6.3 | +5.5 | +20.1 |
| 0.75 | +1.1 | +6.9 | +14.2 | +7.4 | +6.3 | +20.8 |
| 1.0 | +0.0 | +6.4 | +13.2 | +6.8 | +6.2 | +21.6 |
| 1.5 | +0.1 | +6.1 | +13.7 | +7.2 | +7.2 | +21.1 |
| 2.5 | +1.3 | +6.9 | +13.4 | +6.8 | +9.3 | +25.0 |

At 0° the Cd oscillation is at most 0.7 % at Tu 0.1 %.

**Section angle at the working-load force, Tu 0.1 %** [°]. The differences
are the differences in leeway:

| speed [m/s] | 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0008/80 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|---|
| 0.5 | 3.03 | 3.03 | 2.83 | 3.00 | 4.04 | 4.00 | 2.95 |
| 0.75 | 3.97 | 3.87 | 3.56 | 3.78 | 4.34 | 4.00 | 3.53 |
| 1.0 | 3.99 | 3.74 | 3.60 | 3.82 | 4.24 | 4.00 | 3.44 |
| 1.5 | 3.99 | 3.70 | 3.53 | 3.78 | 4.35 | 4.00 | 2.97 |
| 2.5 | 3.88 | 3.57 | 3.17 | 3.80 | 4.53 | 4.00 | 2.67 |

**Force oscillation** (largest Cd standard deviation over the averaging
window as % of Cd, 0.5-1.5 m/s, from `results.csv` of runs 2-4):

| Tu | aoa | 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0008/80 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|---|---|
| 0.1 % | 2° | 0.5 | 0.5 | 1.7 | 0.7 | 0.8 | 1.2 | 2.0 |
| 0.1 % | 4° | 14.4 | 18.0 | 22.3 | 3.3 | 8.1 | 3.2 | 3.0 |
| 0.1 % | 6° | 0.6 | 1.1 | 0.9 | 1.5 | 2.1 | 25.1 | 24.0 |
| 1 % | 4° | 6.9 | 4.9 | 0.1 | 0.0 | 0.0 | 0.1 | 0.0 |

The finalists' 6° points at Tu 0.1 % oscillate too: 0009/80 and 0009/100
by up to 24-25 %. That makes their high-load numbers just as uncertain.

**Highlights** (Tu 0.1 %; reversed flow = where Cf < 0 on the suction
side, from `report/highlights.md`):

| case | status | Cl | Cd | Cd friction | separation, reattachment (x/c) |
|---|---|---|---|---|---|
| 0007/90, 1 m/s, 4° | not converged, unsteady | 0.415 | 0.0163 | 0.0061 | 0.035, oscillating |
| 0007/100, 1 m/s, 4° | not converged, unsteady | 0.408 | 0.0167 | 0.0042 | 0.032, oscillating |
| 0007/90, 1 m/s, 6° | ok | 0.569 | 0.0324 | 0.0067 | 0.033-0.049 |
| 0007/100, 1 m/s, 6° | ok | 0.570 | 0.0313 | 0.0065 | 0.025-0.038 |
| 0008/100, 1 m/s, 6° | ok | 0.573 | 0.0281 | 0.0070 | 0.035-0.051 |
| 0007/100, 1 m/s, 2° | ok, unsteady | 0.124 | 0.0121 | 0.0077 | 0.66, open to the trailing edge |
| 0008/100, 1 m/s, 2° | ok | 0.105 | 0.0134 | 0.0077 | 0.59, open to the trailing edge |
| 0007/100, 0.5 m/s, 4° | not converged, unsteady | 0.378 | 0.0228 | 0.0078 | 0.30-0.86 |
| 0008/100, 0.5 m/s, 4° | ok, unsteady | 0.468 | 0.0248 | 0.0069 | 0.08-0.95 |

Figures: `report/highlight_*.png` of this run.

### Decisions

Proposed, not agreed:
* Keep 0008/90 as the front-runner, now as the safest choice
  (conclusion 5).
* Drop none of the other six on this run. The 80 mm finalists lose with the
  4° points. Without them, 0008/80 or 0009/80 is first in 3 of the 4
  variants, so they hinge on the same unreliable points as the new three.
* Next, a transient (`solver: transient`) check of the 4° points:
  * all seven candidates at 1 m/s, Tu 0.1 %;
  * 0009/80 and 0009/100 at 6° as well;
  * 9 cases.

  No transient foil2d case has been run, so the cost is unknown. Start with
  one case to measure it.
* Drop "0007/90, 0007/100 and 0008/100 at Tu 0.1 %" from the list of what
  would settle it: done here.

### Assumptions

* As analysis 2026-10-13 (2):
  * a 39° heading and 3° leeway;
  * equal time upwind and downwind, at the same boat speed;
  * the estimated resistance slope, or double it;
  * the fin carries all the side force;
  * the 0009/80 forces stand for light, working and high load.

  These are **not verified**.
* That results from runs 3 and 4 can be combined. Same image, mesh, model
  and settings, so the solver is identical (verified from the two
  `run.json` and `study.yaml` files).
* That the window average of an oscillating steady solution approximates
  the time-averaged flow (**not verified**; conclusion 4).

### Compromises

* **Steady solver for shedding flow at 4°.** At Tu 0.1 % most of the
  working-load comparison rests on it.
* **The regret check** treats the crude no-4° variant as equal to the
  others.
* **2.5 m/s is left out of the race-time metric**, as before (no resistance
  estimate). It is in the upwind and downwind tables.
* **One failed case** (8°, 0.5 m/s), left as it is.

### Learnings

* **Thin sections at Tu 0.1 % shed at 4°.** That is the steady solver's
  limit: 0007 at 4° is unsteady at both Tu, and at Tu 0.1 % 0008/100 joins
  it.
* **Compute.**
  * 63.4 case-hours against the 53 estimated (+20 %): median 35 min per
    case, mean 51, with 17 cases at the 8,000-iteration limit.
  * Wall time was 5¾ h. Spot capacity gave 8, then 16, tasks at once (24
    allowed), after 15-30 minutes in the queue.
* **The report's `compare_at` reference must be one of the run's
  candidates.** The run's `study.yaml` still named 0009/80 (an oversight
  when setting up the run), and the report stopped with an error. The
  report now falls back to the nearest candidate, 0007/90 here, and says
  so in the table. It also lists only the (foil, chord) pairs a run has, so
  a zipped study no longer shows empty columns.

### Open questions and next steps

* The transient check of the 4° points (Decisions).
* A hull resistance curve, to replace the estimated slope.
* How the sailing divides between light, working and high load. With
  0007/90 best at light and working load and 0008/100 best at high load,
  the load mix decides between them if the 4° points hold up.
* Fin stiffness: 0007/90 is the thinnest at 6.3 mm.
* Highlights for the transient run: each candidate's 4° case at 1 m/s,
  steady against transient.

## Analysis 2026-10-13 (2): leeway and race time (runs 20261012-175146 and 20261013-045759, no new cases)

**Setup.** No new cases. This puts numbers on a 100 m windward-leeward
course: what a degree of leeway, a newton of side force and a newton of fin
drag are worth. It uses published IOM figures (Inputs) and an estimate of
the boat's resistance. It then adds each candidate's leeway to the race-time
comparison of the previous analysis, which counted drag only.
* The four finalists at Tu 1 % (run 2) and Tu 0.1 % (run 3).
* All 15 run-2 candidates at Tu 1 %.
* 0.5-1.5 m/s. 2.5 m/s is left out: there is no resistance estimate there
  (Fn 0.80, far past hull speed).

Why: the user's question, 2026-10-13. Equal-side-force comparisons hide that
a longer chord makes the same force at a lower angle, i.e. with less leeway.

### Inputs

| quantity | value | source | status |
|---|---|---|---|
| best-VMG heading | 39° to the true wind, boat speed 1.13 m/s, VMG 0.88 m/s; pinching to 30° or footing to 50° drops VMG to 0.82 m/s | L. Gilbert, [VMG (AMYA MY 180)](https://www.onemetre.net/Design/VMG%20(AMYA%20MY%20180)/VMG%20(AMYA%20MY%20180).htm) | the polar is "our boat"; the page doesn't say it is measured IOM data (**not verified**) |
| close-hauled angles | true wind about 45° off, apparent about 30°, at mid No.1 rig speed | L. Gilbert, [Apparent wind](https://onemetre.net/Design/AppWind/appwind.htm) | read from a graph |
| leeway | about 3° in No.1 rig over much of the wind range | L. Gilbert, [Foil sections and forces](https://onemetre.net/Design/FinForce/FinForce.htm) | typical value, not measured |
| sail force | about 6 N at 4 m/s wind and 1.1 m/s boat speed (0.6 m² No.1 rig, CL about 1.0) | same page | worked estimate |
| side-force share | fin about 90 %, hull 10 % | L. Gilbert, [Fin area](https://onemetre.net/Design/FinArea/FinArea.htm) | an eyeball estimate for the Marblehead quoted there; not used in the numbers |
| hull | wetted area 0.142 m² (practical minimum, 160 mm waterline beam), waterline length 990 mm; canoe body 3.62 kg, total 4.01 kg | G. Bantock, [The ISAF One Metre Class, Part 3](https://www.mya-uk.org.uk/wp-content/uploads/2025/11/Graham-Bantock-Development-of-the-IOM-class-updated-2025-Part-3.pdf) (MYA, 2006) | design data; a minimum, real hulls are larger |
| bulb | 250-350 mm long (300 mm used); 2.4 kg lead | L. Gilbert, [IOM bulb drag (AMYA MY 184)](https://onemetre.net/Design/IOM%20bulb%20drag%20(AMYA%20MY%20184)/IOM%20bulb%20drag%20(AMYA%20MY%20184).htm); `docs/geometry.md` defaults | length chosen, not measured |
| fin | span 360 mm, hull as a reflection plane, e = 0.9 | as runs 2 and 3 | as there |
| course | 100 m windward-leeward; equal time upwind and downwind; same boat speed on both legs; downwind a dead run | user, 2026-10-13; previous analysis | assumptions |

The user's 35° heading is closer to the apparent wind angle in these
sources; 39° (plus 3° leeway) is used, with 35° and 45° as bounds.

### Method

* **Value of leeway.** The course through the water is heading + leeway
  β_Y off the true wind, at the true wind angle β_TW. The distance sailed
  for d to windward is d / cos β_TW, so dt / t = tan β_TW · Δβ_Y.
* **Leeway of each candidate.** At equal side force and span, the
  lifting-line induced angle, S_h / (2π e q b²), doesn't depend on chord. So
  the difference in leeway between candidates is the difference in 2D
  section angle at that force. It is interpolated along the pre-stall branch
  like the drag (`selection_compare.csv`). This assumes the fin carries all
  the side force.
* **Side-force slope.** a = a0 / (1 + a0 / (π e AR)) with AR = 2b / c = 9,
  from the Cl of 0009/80 (`results.csv`).
* **Drag to time.** δV_b = ΔD_h / (dD_h/dV_b), so the fraction of a leg's
  time lost is ΔD_h / (V_b · dD_h/dV_b). The boat's resistance D_h(V_b) is
  estimated, upright and in calm
  water:
  * hull: ITTC-57 friction × (1 + k), with 1 + k = 1.10 (assumed), on
    0.142 m² and L = 0.99 m;
  * fin at 0°: CFD (run 2, 0009/80);
  * bulb: ITTC-57 × 1.2 on 0.0274 m² (2.4 kg lead, 300 mm long, prismatic
    0.6 assumed);
  * rudder: 0.010 m² planform, Cd 0.014 (assumed, like the fin at 0°).

  Wave, heel, leeway and induced drag are left out, so this slope ("×1") is
  a lower bound and the drag costs it gives are upper bounds. "×2" doubles
  the slope, a stand-in for the missing parts (not computed).
* **Race time.** The average of the upwind and downwind losses (equal time),
  each in % of its leg's time:
  * upwind = drag + leeway;
  * downwind = drag at 0°.

### Conclusions

1. **1° of leeway costs 1.4-1.9 % of the beat.**
   * Heading 39° + 3° leeway = a course at β_TW = 42°: 134.6 m sailed per
     100 m to windward. 1° more leeway adds 2.1 m, 1.6 % and 1.9 s at
     1.13 m/s.
   * At a 35° heading it adds 1.7 m (1.4 %); at 45°, 2.9 m (1.9 %).

   Confidence: high for the geometry, given the heading.
2. **1 N of side force is worth about 0.8° of leeway at 1 m/s**: 1.2 % of
   the beat, 1.7 m per 100 m.
   * Secant: 6.44 N at a 4° section angle plus 1.0° induced, i.e. 5.0°, so
     1.29 N/°.
   * The local slope is 0.7-1.9 N/° between 2 and 6° (both Tu) because of
     the laminar bubble.
   * It scales with 1/V²: about 0.35° at 1.5 m/s and 3° at 0.5 m/s.
   * Carrying 1 N more also costs about 0.03 N of fin drag (0009/80, Tu 1 %,
     1 m/s, between the 2° and 4° forces).

   Confidence: medium. Fin only; the hull and rudder share is left out.
3. **0.01 N of fin drag costs at most 0.74 % of speed at 1 m/s**, and 0.37 %
   at 1.5 m/s.
   * On a 100 m run: 0.74 s at 1 m/s, 0.25 s at 1.5 m/s. On the 100 m beat:
     0.99 s at 1 m/s, 0.72 s at 1.13 m/s.
   * 1 N is more than the boat's whole estimated resistance at 1 m/s
     (0.75 N), so per-newton figures don't apply.
   * So 1° of leeway is worth about 0.021 N of fin drag at 1 m/s, or
     0.043 N with the slope doubled. The finalists' drag differences are
     0.003-0.04 N.

   Confidence: low. The resistance estimate is not verified.
4. **At working load the finalists' leeway differs by up to 1.4°
   (0.5-1.5 m/s; 1.9° at 2.5 m/s), as much as their drag differences are
   worth.** Against 0009/80 (4.0°), over 5 speeds × 2 Tu: 0008/80 needs
   +0.02 to +0.53°, 0008/90 −0.18 to −1.00°, and 0009/100 −0.47 to
   −1.33°. The drag-only
   comparisons of runs 1-3 and the previous analysis left this out.
   Confidence: medium. Fin only; 3D effects unchecked.
5. **Among the finalists, 0008/90 is the best all-round fin once leeway
   counts.** Equal time, 0.5-1.5 m/s, both Tu; race time lost above the best
   finalist, with the ×1 / ×2 resistance slope:
   * working load: worst case 0008/90 0.54 / 0.13 %, 0008/80 1.18 / 1.00 %,
     0009/80 2.44 / 1.61 %, 0009/100 2.54 / 1.25 %.
     * The 80 mm worst cases are at 0.5 m/s, Tu 0.1 %, where their bubble
       doesn't reattach (run 3, conclusion 7).
     * From 0.75 m/s up: 0008/90 0.54 / 0.13 %, 0009/80 0.53 / 0.24 %,
       0008/80 0.80 / 0.62 %, 0009/100 2.22 / 1.01 %.
   * light load (2° force): 0008/80 is best in 7 of 8 (×1) / 6 of 8 (×2);
     0008/90 is within 0.99 / 0.44 %.
   * high load (6° force): 0009/100 is best in all 8. 0008/90 is second in
     all 8, 0.1-3.1 % (×1) / 0.4-2.0 % (×2) behind; the 80 mm sections are
     2.2-6.8 % / 1.7-4.3 % behind.
   * all three loads weighted equally, mean: 0008/90 0.85 / 0.49 %, 0009/100
     1.50 / 0.61 %, 0008/80 1.60 / 1.10 %, 0009/80 1.80 / 1.20 %.

   0.5 % of race time is about 0.6 s per 100 m beat. Confidence: low to
   medium. It rests on the resistance estimate, the fin-only side force and
   the course assumptions, and the differences among 0008/80, 0009/80 and
   0008/90 are within those uncertainties.
6. **Over all 15 run-2 candidates (Tu 1 %), thinner sections on longer
   chords lead.**
   * Mean over the three loads (×1 / ×2): 0007/100 1.11 / 0.49 %, 0008/100
     1.34 / 0.57 %, 0007/90 1.50 / 0.85 %, 0008/90 1.58 / 0.87 %.
   * At working load 0007/90 is best: mean 0.21 / 0.07 %, worst
     0.43 / 0.18 %.
   * Run 2 dropped all three on drag alone.
   * Their evidence is weaker. 10 of the 12 upwind comparison points of
     0007/90 and 0007/100 are interpolated from unsteady or not-converged
     cases (0008/100: 6, 0008/90: 5, 0008/80 and 0009/80: 2). None has been
     run at Tu 0.1 %, where thin 80 mm sections lost ground (run 3).

   Confidence: low.
7. **This supersedes the previous analysis's proposals** to narrow to
   0008/80 and 0009/80, and to try a 70 mm chord. A shorter chord needs more
   leeway: 0008/80 already needs 0.35-1.04° more than 0008/90. It agrees
   with run 3's proposal of 0008/90 as the all-round fin, for a different
   reason.

### Evidence

Values on a 100 m leg (conclusions 1-3):

| item | value |
|---|---|
| 1° leeway, β_TW 38 / 42 / 48° (heading 35 / 39 / 45° + 3°) | +1.73 / +2.11 / +2.90 m; +1.36 / +1.57 / +1.94 % of the beat; +1.53 / +1.87 / +2.56 s at 1.13 m/s |
| fin side-force slope, 0009/80, 1 m/s | 1.29 N/° (secant to 4°, with 1.01° induced); 0.73-1.93 N/° local, 2-6° |
| 1 N of side force, 1 m/s | 0.78° of leeway; 1.2 % of the beat; 1.65 m |
| 0.01 N of drag, ×1 slope | upwind: 0.74 % speed, 0.99 s at 1.0 m/s; 0.61 %, 0.72 s at 1.13 m/s. Downwind: 0.74 %, 0.74 s at 1.0 m/s; 0.37 %, 0.25 s at 1.5 m/s |
| 1° of leeway as fin drag, 1 m/s | 0.021 N (×1), 0.043 N (×2) |

Resistance estimate (method), N:

| V_b [m/s] | hull | fin (0°) | bulb | rudder | total | V_b · dD_h/dV_b |
|---|---|---|---|---|---|---|
| 0.5 | 0.110 | 0.068 | 0.032 | 0.017 | 0.227 | 0.40 |
| 0.75 | 0.226 | 0.126 | 0.064 | 0.039 | 0.456 | 0.81 |
| 1.0 | 0.377 | 0.200 | 0.105 | 0.070 | 0.752 | 1.35 |
| 1.13 | 0.469 | 0.247 | 0.130 | 0.089 | 0.935 | 1.65 |
| 1.5 | 0.777 | 0.380 | 0.214 | 0.157 | 1.529 | 2.71 |

Section angle at the working-load force (0009/80's 4° force), degrees:

| Tu | speed [m/s] | 0008/80 | 0009/80 | 0008/90 | 0009/100 |
|---|---|---|---|---|---|
| 1 % | 0.5 | 4.02 | 4.0 | 3.64 | 3.43 |
| 1 % | 0.75 | 4.07 | 4.0 | 3.72 | 3.34 |
| 1 % | 1.0 | 4.07 | 4.0 | 3.67 | 3.15 |
| 1 % | 1.5 | 4.10 | 4.0 | 3.54 | 2.97 |
| 1 % | 2.5 | 4.11 | 4.0 | 3.55 | 3.19 |
| 0.1 % | 0.5 | 4.04 | 4.0 | 3.00 | 2.95 |
| 0.1 % | 0.75 | 4.34 | 4.0 | 3.78 | 3.53 |
| 0.1 % | 1.0 | 4.24 | 4.0 | 3.82 | 3.44 |
| 0.1 % | 1.5 | 4.35 | 4.0 | 3.78 | 2.97 |
| 0.1 % | 2.5 | 4.53 | 4.0 | 3.80 | 2.67 |

Race time lost at working load, finalists, % above the best finalist (×1 /
×2 slope):

| Tu | speed [m/s] | 0008/80 | 0009/80 | 0008/90 | 0009/100 |
|---|---|---|---|---|---|
| 1 % | 0.5 | best / best | 0.76 / 0.37 | 0.41 / 0.06 | 2.22 / 0.88 |
| 1 % | 0.75 | best / best | 0.53 / 0.24 | 0.51 / 0.12 | 2.17 / 0.80 |
| 1 % | 1.0 | best / best | 0.53 / 0.23 | 0.54 / 0.11 | 1.90 / 0.58 |
| 1 % | 1.5 | best / 0.11 | 0.30 / 0.22 | 0.22 / best | 1.23 / 0.28 |
| 0.1 % | 0.5 | 1.18 / 1.00 | 2.44 / 1.61 | best / best | 2.54 / 1.25 |
| 0.1 % | 0.75 | 0.79 / 0.62 | 0.12 / 0.15 | best / best | 2.22 / 1.01 |
| 0.1 % | 1.0 | 0.27 / 0.28 | best / 0.05 | 0.04 / best | 2.05 / 0.85 |
| 0.1 % | 1.5 | 0.80 / 0.54 | best / best | 0.43 / 0.13 | 0.92 / 0.06 |

All 15 run-2 candidates, Tu 1 %, 0.5-1.5 m/s, race time lost above the best
of the 15, % (×1 / ×2 slope). Sorted by the ×2 mean over all loads.

| candidate | mean, all loads | worst, all loads | mean, working load | worst, working load |
|---|---|---|---|---|
| 0007/100 | 1.11 / 0.49 | 2.42 / 1.18 | 0.91 / 0.29 | 1.01 / 0.30 |
| 0008/100 | 1.34 / 0.57 | 3.42 / 1.76 | 1.41 / 0.51 | 2.19 / 0.89 |
| 0007/90 | 1.50 / 0.85 | 3.49 / 2.10 | 0.21 / 0.07 | 0.43 / 0.18 |
| 0008/90 | 1.58 / 0.87 | 2.62 / 1.52 | 0.78 / 0.32 | 1.49 / 0.63 |
| 0009/100 | 2.08 / 0.90 | 4.76 / 2.53 | 2.23 / 0.88 | 3.30 / 1.45 |
| 0009/90 | 2.08 / 1.08 | 3.84 / 2.15 | 1.58 / 0.70 | 2.47 / 1.13 |
| 0006/100 | 2.40 / 1.18 | 5.05 / 2.67 | 2.08 / 0.93 | 2.79 / 1.30 |
| 0009/80 | 2.08 / 1.31 | 3.78 / 2.56 | 0.88 / 0.51 | 1.84 / 0.95 |
| 0008/80 | 2.10 / 1.36 | 4.95 / 3.18 | 0.35 / 0.28 | 1.08 / 0.58 |
| 0006/90 | 2.82 / 1.55 | 7.10 / 3.96 | 1.62 / 0.84 | 2.39 / 1.23 |
| 0007/80 | 2.94 / 1.81 | 9.00 / 5.28 | 0.47 / 0.38 | 1.05 / 0.75 |
| 0012/100 | 5.06 / 2.24 | 8.92 / 4.28 | 5.04 / 2.11 | 6.98 / 3.16 |
| 0012/90 | 4.70 / 2.24 | 7.79 / 3.82 | 4.51 / 2.02 | 6.27 / 2.98 |
| 0012/80 | 4.35 / 2.30 | 6.91 / 3.65 | 3.85 / 1.91 | 5.27 / 2.65 |
| 0006/80 | 5.25 / 3.02 | 17.00 / 9.40 | 2.87 / 1.70 | 3.83 / 2.19 |

### Decisions

Proposed, not agreed (see "Where the selection stands"):
* Treat 0008/90 as the front-runner, with 0008/80 and 0009/80 as close
  alternatives. Keep 0009/100 only for heavy air.
* Run 0007/90, 0007/100 and 0008/100 at Tu 0.1 %: 3 candidates × 5 speeds
  × 5 angles = 75 cases. That is about 53 case-hours, scaled from run 3's
  70.7 case-hours for 100 cases (**estimate**).
* Drop the 70 mm chord run.
* Add leeway to the report's selection comparison: a heading angle and
  resistance slope as `report:` options, ranking by race time.

### Assumptions

1. Heading 39° to the true wind and 3° leeway (Gilbert; **not verified**
   for this boat).
2. Equal time upwind and downwind (the user, 2026-10-13). On a 100 m course
   at the same speed the beat takes 35 % longer than a dead run. If the beat
   takes more of the race, upwind weighs more, and leeway with it.
3. The same boat speed on both legs.
4. The resistance slope: the viscous estimate in Method (**not
   verified**), or double it.
5. The fin carries all the side force, and leeway differences equal section
   angle differences (**not verified**). If the hull and rudder carry
   20-30 %, the leeway differences shrink roughly in proportion (not
   computed).
6. Sails trimmed to the same apparent wind, so less leeway means a course
   closer to the wind (smaller β_TW) at the same heading and speed.
7. Downwind the fin is at 0° (as the previous analysis).

### Compromises

* 2.5 m/s is left out: no resistance estimate there.
* Heel, hull upwash on the fin and the bulb's side force are ignored.
* The race-time differences among the leaders (≤ about 1 %) are smaller than
  the combined uncertainty of the inputs.

### Learnings

* Leeway is worth as much as fin drag. A longer chord buys leeway: 10 mm
  more chord saves 0.2-0.6° at working load (up to 1.0° at 0.5 m/s and
  Tu 0.1 %), worth 0.3-0.9 % of the beat.
* 1 N of side force is about 15 % of the working-load force at 1 m/s, and
  worth about 0.8° of leeway.
* 0008/90 and 0009/80 are the same thickness in millimetres (7.2 mm). 0008/90
  trades a thinner section for a longer chord at no loss of thickness.

### Open questions and next steps

* Hull resistance at 0.5-1.5 m/s (`hull` project) to replace the estimate.
* The real split of race time between upwind, reach and downwind, and the
  boat speed on each. GPS tracks of IOM races would settle assumptions 1-3.
* The hull and rudder share of side force (`appendage3d` or `fullboat`).
* The Tu 0.1 % check of 0007/90, 0007/100 and 0008/100 (Decisions).

## Analysis 2026-10-13: upwind and downwind legs (runs 20261012-175146 and 20261013-045759, no new cases)

**Setup.** No new cases. Runs 2 and 3 compared the finalists upwind only:
drag at equal side force. A race also has downwind legs (and reaches). This
analysis adds a downwind leg, sailed for the same time as upwind. It uses
the four finalists' cases at Tu 1 % (run 20261012-175146) and Tu 0.1 % (run
20261013-045759), 0.5-2.5 m/s.
* Upwind: whole-fin drag (section + induced) at the side force 0009/80
  makes at 2, 4 and 6° (light, working and high load), as in
  `selection_compare.csv`.
* Downwind: whole-fin drag at aoa 0, with no side force.
* Combined: upwind + downwind drag at the same speed. This treats a newton
  of fin drag as costing the same time on either leg (assumption 2).

Why: run 3 left the choice depending on how much of the sailing is at each
load. The equal upwind/downwind time is the user's input.

### Conclusions

1. **Downwind, 0008/80 has the least drag of the finalists at every speed
   and both Tu.**
   * Above 0008/80: 0009/80 +3.3-9.3 %, 0008/90 +4.7-7.4 %, 0009/100
     +14.5-25.0 % (10 speed × Tu points each).
   * At 0° the drag is 55-72 % friction, so it follows chord and thickness.
     0008/90 is 6.7-6.8 % above 0008/80 at 1 m/s, close to the 6 % laminar
     friction (∝ √chord) gives for 90 against 80 mm.

   Confidence: high on the ranking. 37 of the 40 0° points are flagged
   unsteady, but their Cd oscillates by at most 0.5 %.
2. **With equal time upwind and downwind, 0009/100 drops out and the choice
   is between the 80 mm chords.** Mean drag above the best finalist,
   upwind only → upwind + downwind:
   * working load (4° force), 0.75-2.5 m/s, both Tu (8 comparisons):
     0009/80 0.4 → 1.2 % (max 3.0), 0008/80 3.8 → 1.4 % (max 6.9), 0008/90
     1.8 → 2.3 % (max 4.4), 0009/100 7.5 → 10.6 % (max 13.3);
   * light load (2° force): 0008/80 is best in all 10 comparisons; the others
     are 2.3 % or more above it;
   * high load (6° force): 0009/100 is still best in 9 of 10. The exception
     is Tu 0.1 %, 1.5 m/s, where 0008/90 is best and 0009/100 2.2 % above;
   * all 30 comparisons: 0008/90 6.0 → 4.1 %, 0008/80 9.4 → 4.3 %, 0009/80
     8.6 → 5.5 %, 0009/100 8.8 → 10.0 %. 0008/80 is best in 15 of 30.

   Confidence: medium. It rests on assumptions 1-3.
3. **This supersedes the reading of run 3 conclusion 5, that 0008/90 is the
   all-round choice.**
   * Downwind, 0008/90 and 0009/80 differ by 2.3 % or less, so the downwind
     leg doesn't separate them.
   * At working load 0008/90 is now behind both 80 mm sections. Its
     all-30 mean (4.1 %) ties 0008/80's (4.3 %) only through the high-load
     points.
4. **Between 0008/80 and 0009/80, Tu decides, as it did upwind.**
   * Tu 1 %: 0008/80 is best at light and working load at every speed (10 of
     10). At working load 0009/80 is 0.8-3.4 % above it.
   * Tu 0.1 %, working load:
     * 0.75-1.5 m/s: 0009/80 is best, with 0008/80 0.4-2.5 % above;
     * 2.5 m/s: 0008/90 is best, with 0009/80 +0.8 % and 0008/80 +6.9 %;
     * 0.5 m/s: 0008/90 is best, with 0008/80 +1.6 % and 0009/80 +7.4 %.

   Confidence: low to medium. Most Tu 0.1 % upwind points at 4° are unsteady
   (run 3, conclusion 2).
5. **At Tu 0.1 % the answer is sensitive to the weighting.** Weight the
   downwind drag by w against the upwind drag; this analysis is w = 1.
   * Tu 1 %, working load: 0008/80 wins at every w up to 1 m/s, and for
     w ≥ 0.15 (1.5 m/s) or w ≥ 0.25 (2.5 m/s).
   * Tu 0.1 %, working load: 0008/80 becomes best at w = 1.2 (1 m/s), 1.75
     (0.5 m/s), 1.9 (0.75 m/s), 2.15 (1.5 m/s) and 4.5 (2.5 m/s, over
     0008/90). At 1 m/s a downwind newton only has to count 20 % more than
     an upwind one.

   Break-even found on a 0.05 grid of w.

### Evidence

Computed from `report/selection.csv` of both runs: whole fin, 360 mm span,
section drag + lifting-line induced drag (e = 0.9). Upwind drag is
interpolated linearly along each candidate's pre-stall branch at the side
force 0009/80 makes at that Tu, as `selection_compare.csv` does. Downwind
drag is the aoa 0 case. Percentages are above the best of the four
finalists; at Tu 1 % only the four finalists of run 2's 15 candidates are
compared. Cd_std and Cd_friction come from `results.csv`.

Downwind (aoa 0), % above 0008/80:

| Tu | speed [m/s] | 0008/80 drag [N] | 0009/80 | 0008/90 | 0009/100 |
|---|---|---|---|---|---|
| 1 % | 0.5 | 0.0649 | +4.2 | +6.5 | +17.3 |
| 1 % | 0.75 | 0.1205 | +5.0 | +6.4 | +19.6 |
| 1 % | 1.0 | 0.1875 | +6.7 | +6.7 | +22.0 |
| 1 % | 1.5 | 0.3560 | +6.8 | +7.0 | +20.6 |
| 1 % | 2.5 | 0.7715 | +3.3 | +4.7 | +14.5 |
| 0.1 % | 0.5 | 0.0632 | +5.5 | +6.3 | +20.1 |
| 0.1 % | 0.75 | 0.1186 | +6.3 | +7.4 | +20.8 |
| 0.1 % | 1.0 | 0.1872 | +6.2 | +6.8 | +21.6 |
| 0.1 % | 1.5 | 0.3529 | +7.2 | +7.2 | +21.1 |
| 0.1 % | 2.5 | 0.7746 | +9.3 | +6.8 | +25.0 |

Working load (4° force). Cells: % above the best finalist, upwind only →
upwind + downwind. The drag columns are 0009/80's on each leg.

| Tu | speed [m/s] | up [N] | down [N] | 0008/80 | 0009/80 | 0008/90 | 0009/100 |
|---|---|---|---|---|---|---|---|
| 1 % | 0.5 | 0.122 | 0.068 | best → best | +2.9 → +3.4 | +1.3 → +3.1 | +8.7 → +11.8 |
| 1 % | 0.75 | 0.224 | 0.126 | best → best | +1.6 → +2.8 | +2.3 → +3.7 | +9.4 → +13.0 |
| 1 % | 1.0 | 0.349 | 0.200 | best → best | +1.0 → +3.0 | +3.1 → +4.4 | +8.7 → +13.3 |
| 1 % | 1.5 | 0.694 | 0.380 | +0.5 → best | best → +2.0 | +2.1 → +3.4 | +6.4 → +10.9 |
| 1 % | 2.5 | 1.773 | 0.797 | +0.3 → best | best → +0.8 | +2.1 → +2.6 | +9.2 → +10.5 |
| 0.1 % | 0.5 | 0.124 | 0.067 | +6.2 → +1.6 | +12.4 → +7.4 | best → best | +10.8 → +11.6 |
| 0.1 % | 0.75 | 0.252 | 0.126 | +5.8 → +1.7 | +0.2 → best | best → +0.2 | +9.2 → +10.6 |
| 0.1 % | 1.0 | 0.391 | 0.199 | +3.5 → +0.4 | best → best | +0.9 → +0.8 | +9.8 → +11.4 |
| 0.1 % | 1.5 | 0.752 | 0.378 | +7.2 → +2.5 | best → best | +4.3 → +2.9 | +5.9 → +8.3 |
| 0.1 % | 2.5 | 1.799 | 0.847 | +13.1 → +6.9 | +0.1 → +0.8 | best → best | +1.4 → +6.4 |

Upwind + downwind at the other loads, range over the 5 speeds (% above the
best finalist):

| load | Tu | 0008/80 | 0009/80 | 0008/90 | 0009/100 |
|---|---|---|---|---|---|
| light (2°) | 1 % | best | 2.8-6.9 | 3.8-6.5 | 16.6-19.4 |
| light (2°) | 0.1 % | best | 2.3-9.9 | 2.5-7.2 | 14.1-23.6 |
| high (6°) | 1 % | 7.6-11.6 | 3.1-6.6 | 2.5-4.3 | best |
| high (6°) | 0.1 % | 6.1-20.0 | 9.2-18.4 | 0-15.4 | 0-2.2 |

### Decisions

Proposed, not agreed:
* If the equal-time weighting is accepted, narrow the finalists to 0008/80
  and 0009/80. 0009/100 then needs heavy-air upwind to dominate the race;
  0008/90 has no load where it is clearly best.
* Test a shorter chord. Downwind favours the shortest chord, and 80 mm is the
  shortest tested (README: IOM fins are 65-90 mm). Candidate run: 0008 and
  0009 at 70 mm, Tu 0.1 and 1 %, 0.5-2.5 m/s, aoa 0-8°. That is 100 cases,
  about run 3's size.

### Assumptions

1. Equal time upwind and downwind (the user's input, 2026-10-13). Reaches are
   left out.
2. The same boat speed on both legs, and the same speed loss per newton of
   fin drag, so the two legs' drag adds (**not verified**: there is no hull
   resistance data yet, only a hull smoke run). Faster downwind sailing gives
   more newtons of 0° drag (about U²). But each newton costs less speed where
   the hull's resistance rises steeply. Which effect wins is unknown;
   conclusion 5 shows how far the weighting can move before the answer
   changes.
3. Downwind the fin carries no side force (aoa 0) (**not verified**:
   steering, running by the lee and sail asymmetry put small angles on it).
4. Upwind loads are the 0009/80 forces at 2, 4 and 6°, as in runs 2 and 3.
5. Only the fin differs. Hull, rudder and bulb are the same for every
   candidate.

### Compromises

* The percentages are of fin drag, not of race time. Converting them needs
  the fin's share of total boat resistance on each leg (assumption 2).
* 2D sections + lifting line, steady solver, as in runs 2 and 3.

### Learnings

* At zero lift the section drag is 55-72 % friction (Cd_friction / Cd) and
  oscillates by at most 0.5 % even where flagged unsteady, so the 0° ranking
  is firmer than the upwind one.
* For 0009/80, downwind drag is 45-57 % of the working-load upwind drag at
  the same speed. So a 6 % downwind penalty weighs about as much as a 3 %
  upwind one.
* 0009/80 and 0008/90 have about the same 0° drag: one extra point of
  thickness costs about as much as 10 mm of chord.

### Open questions and next steps

* Hull resistance at 0.5-2.5 m/s (`hull` project), to turn fin drag into
  time per leg and to check assumption 2.
* The real split of race time between upwind, reach and downwind, and the
  boat speed on each.
* Reaches, where the fin makes a moderate side force at higher speed. If a
  reach is like the 2° force at 1.5-2.5 m/s (**not verified**), upwind-only
  figures put 0008/80 within 1.8 % and 0009/80 within 4.3 % of the best
  finalist there, which doesn't separate them.
* 70 mm chords (Decisions). Highlights for that run: compare chord at aoa 0
  and 1 m/s (downwind: friction against chord), and at the 4° force at
  1 m/s and Tu 0.1 % (does the bubble grow on the shorter chord?).
* The 3D and time-accurate checks from run 3, now for 0008/80 and 0009/80.
* Fin stiffness under the bulb load, which CFD doesn't cover. 0008 at
  80 mm has about 70 % of 0009's bending stiffness (estimate from thickness
  cubed, **not verified**).

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
