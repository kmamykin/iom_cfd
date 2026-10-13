# fin-profile-selection: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results themselves live
in `runs/fin-profile-selection/<run id>/` (not in git), so the numbers that
support a conclusion are copied here. Entries are written by the
`study-findings` skill (`/study-findings foil2d/fin-profile-selection`) or by
hand, and are not rewritten later: a later run that changes a conclusion says
so in its own entry.

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
