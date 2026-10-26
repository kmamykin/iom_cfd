# stepped-vs-baseline: findings log

Why don't stepped (Kline-Fogleman) sections, or a trip step, help an IOM
fin? Every stepped section is cut from NACA 0007 at 100 mm, so the steps are
the only difference, at one operating point (1 m/s, Tu 1 %). The numerics of
stepped sections were checked in [stepped-checks](stepped-checks.md); the
trip over the full speed and Tu sweep, with the film and the faired step, is
in [naca0007-film](naca0007-film.md).

Newest entry first. Results live in `runs/stepped-vs-baseline/<run id>/`
(not in git), so the numbers that support a conclusion are copied here.
Symbols follow [docs/nomenclature.md](../../../docs/nomenclature.md).

## Run 20261023-201101 (2026-10-23 to 2026-10-26, git ffb4c90, GCP, 16 cases, 15 finished)

**Setup.**
* NACA 0007 at 100 mm, 1 m/s (Re 88,000), Tu 1 %, kOmegaSSTLM, medium mesh;
  the steps' meshes refined to a fraction of the step height (cmesh.py).
* Sections, all cut from NACA 0007:
  * `stair1:naca0007:d=0.5`: one 1.54 mm step per side at x/c 0.5, half
    the local half-thickness (the hobby KFm4 layout);
  * `stair5:naca0007:h=0.002`: five 0.2 mm steps per side, x/c 0.3-0.9;
  * `stair10:naca0007:h=0.001`: ten 0.1 mm steps per side;
  * the trip, `stair1:naca0007:x=0.5,h=0.002`: one 0.2 mm step per side at
    x/c 0.5 (6.5 % thinner behind it).
  * The three stairs each remove about half the thickness near the TE.
* Steady at 4° for all; the trip and plain also at 0 and 2°.
* Time-accurate (pimpleFoam, max_co 5, from 2000 steady iterations): 20
  flow-throughs averaged over 12-20 for plain, stair1 and the trip at 4°,
  and plain and the trip at 2°; stair5 and stair10 6 flow-throughs averaged
  over 3-6 (their small steps need time steps near 4.5e-5 s).
* Image `iom-cfd:094ffb4`, c2d-standard-16 Spot VMs, 4 ranks per case,
  48 h per task.

**Outcome.** 13 ok, 2 not converged, 1 failed.
* Not converged: steady plain and steady stair1 at 4°.
* Failed: stair10 time-accurate. It wrote its 1-flow-through checkpoint
  (0.1 s) on 2026-10-24 at 23:30 and then ran into the 48 h task limit; no
  averaged forces. Batch marked the job FAILED for it.
* Unsteady: 7. Steady plain and trip at 0°; the trip time-accurate at 2°
  (Cl oscillates 2.6 %, the mean doesn't move); steady plain and stair10 at
  4°; plain and stair5 time-accurate at 4°.
* The trip's time-accurate 4° case took 47.8 h (27,856 time steps), just
  inside the limit. 123.8 case-hours in all; the job ran 66.9 h.

### Conclusions

1. **A Kline-Fogleman step costs a lot of drag: the KFm4-like stair1 has 41 %
   more than plain NACA 0007 at 4° (time-accurate), though it is half as
   thick behind the step.**
   * Cd 0.01948 against 0.01382, at Cl 0.4300 against 0.4336. Pressure drag
     +44 %, friction +36 %.
   * Both surfaces separate at the step. On the lower one the flow
     reattaches at x/c 0.60 and is turbulent from there (Cf about 0.006
     against plain's 0.001-0.003; figure).
   * Steady gives the same within 1 % (Cd 0.01930), and the flow is steady
     in time.
   * Confidence: high. Both solvers agree, and stepped-checks found a 30 %
     step on NACA 0009 cost 13 %.
2. **Finer stairs cost less, but none gains.**
   * stair5, time-accurate (6 flow-throughs): Cd +2.3 % (Cl +0.1 %). It
     sheds a row of vortices along the upper surface (vorticity figure).
     Steady: +3.2 % against plain's time-accurate value.
   * stair10, steady only: +0.9 % (Cl −0.8 %) against plain's
     time-accurate value, −1.7 % against plain's steady one. The case is
     unsteady.
   * Confidence: low for the ranking of stair5 and stair10 against plain:
     the differences are within the steady/time-accurate spread at 4°
     (conclusion 4), and stair5's average covers 3 flow-throughs.
     stepped-checks said the same of stair10 (its conclusion 4).
3. **The 0.2 mm trip gains at 2°, not at 4°. Its 4° gain in the steady runs
   was the steady solver's.**
   * 0°, steady: Cd −0.9 % (0.01114 against 0.01124; both unsteady). The
     faired step of naca0007-faired gives −1.3 %, so this is the thinner
     rear, not the step.
   * 2°: Cd −2.9 % (0.01188 against 0.01224) and Cl +0.030 (0.193 against
     0.163). Steady and time-accurate agree to 0.0004 in Cl and exactly in
     Cd. The step makes a bubble from x/c 0.50 to 0.57. Behind it the flow
     separates again at x/c 0.72, as plain's does, so the trip doesn't close
     plain's separation (the study asked whether it would shorten it).
   * 4°, time-accurate: Cd −1.0 % (0.01368 against 0.01382) at 1.2 % less
     lift (Cl 0.4285 against 0.4336). Pressure drag −6.2 %, friction
     +5.8 %. The trip's flow is steady in time; plain's leading-edge bubble
     sheds.
   * At equal lift the 4° comparison depends on the slope of the drag
     curve, and 4° sits at its knee:
     * from plain's 3-4° slope (dCd/dCl 0.015, naca0007-film run
       20261025-161234), the trip has 0.4 % less drag;
     * from the 4-5° slope (0.10), it has 2.7 % more.
     * So: no measurable gain at 4°.
   * Steady at 4° said −4.2 % at 0.9 % more lift (0.01358 against 0.01418).
     That came from plain's steady Cd being 2.6 % high and the trip's steady
     Cl being 1.9 % high.
   * Confidence: medium. One speed and Tu, and the equal-lift bracket is
     wide.
4. **Where the flow is steady, the steady solver repeats time-accurate; at
   4°, where plain's leading-edge bubble sheds, it is off by up to 2.6 % in
   Cd and 1.9 % in Cl, in both directions.**

   | section, 4° | steady Cl | time-acc. Cl | steady Cd | time-acc. Cd | Cd, steady / time-acc. |
   |---|---|---|---|---|---|
   | plain | 0.4328 | 0.4336 | 0.01418 | 0.01382 | +2.6 % |
   | stair1 | 0.4335 | 0.4300 | 0.01930 | 0.01948 | −0.9 % |
   | trip | 0.4366 | 0.4285 | 0.01358 | 0.01368 | −0.7 % |
   | stair5 (6 flow-throughs) | 0.4307 | 0.4339 | 0.01426 | 0.01414 | +0.8 % |

   * At 2°: plain 0.1633 / 0.1629 and 0.01224 / 0.01224; trip 0.1930 /
     0.1932 and 0.01188 / 0.01188.
   * Confidence: high (that the spread is this size, at this point).
5. **What this does to the trip's race-time gain (naca0007-film entry):**
   * With the time-accurate 1 m/s, 4° cases of plain and the trip in place
     of the steady ones, its Tu 1 % gain over plain NACA 0007 drops from
     +0.40 % to +0.32 % of race time (slope ×1; ×2: +0.22 to +0.18 %). It is
     still faster at 9 of 9 load points.
   * At 1 m/s its high-load gain goes from +0.61 % to +0.03 %, and its
     working-load gain from +0.43 % to +0.29 %.
   * Its lead over the faired step (the same section without the step)
     drops from +0.23 % to +0.17 %. That lead comes from 0.75 and 1.5 m/s,
     where there are no time-accurate cases.
   * Recomputed with `iomcfd.racetime` on the three naca0007 runs and this
     run's results.csv.
6. **The answer to the study's question:** at the working load (4°) plain
   NACA 0007's upper flow reattaches behind its leading-edge bubble by x/c
   0.24, and the lower surface is attached (its Cf falls smoothly, as a
   laminar layer's does). There is no
   separation for a step to hold.
   * A deep step adds a separation of its own on both surfaces and turns
     the lower boundary layer turbulent: +41 %.
   * Shallow steps add little drag but don't gain either.
   * The 0.2 mm trip helps only at 2°, where plain stays laminar up to its
     separation at x/c 0.72, and in kOmegaSSTLM a 10 mm fairing does the
     same there (naca0007-faired).

### Evidence

All cases (results.csv; 1 m/s, Tu 1 %):

| α | section | solver | status | Cl | Cd | Cd pressure | Cd friction | unsteady |
|---|---|---|---|---|---|---|---|---|
| 0° | plain | steady | ok | 0.0000 | 0.01124 | 0.00304 | 0.00821 | yes |
| 0° | trip | steady | ok | 0.0003 | 0.01114 | 0.00306 | 0.00809 | yes |
| 2° | plain | steady | ok | 0.1633 | 0.01224 | 0.00451 | 0.00774 | no |
| 2° | plain | time-acc. | ok | 0.1629 | 0.01224 | 0.00451 | 0.00774 | no |
| 2° | trip | steady | ok | 0.1930 | 0.01188 | 0.00444 | 0.00744 | no |
| 2° | trip | time-acc. | ok | 0.1932 | 0.01188 | 0.00444 | 0.00744 | yes |
| 4° | plain | steady | not conv. | 0.4328 | 0.01418 | 0.00790 | 0.00629 | yes |
| 4° | plain | time-acc. | ok | 0.4336 | 0.01382 | 0.00785 | 0.00597 | yes |
| 4° | stair1 | steady | not conv. | 0.4335 | 0.01930 | 0.01135 | 0.00796 | no |
| 4° | stair1 | time-acc. | ok | 0.4300 | 0.01948 | 0.01134 | 0.00813 | no |
| 4° | stair5 | steady | ok | 0.4307 | 0.01426 | 0.00785 | 0.00641 | no |
| 4° | stair5 | time-acc. (6) | ok | 0.4339 | 0.01414 | 0.00794 | 0.00620 | yes |
| 4° | stair10 | steady | ok | 0.4302 | 0.01394 | 0.00806 | 0.00588 | yes |
| 4° | stair10 | time-acc. (6) | failed | - | - | - | - | - |
| 4° | trip | steady | ok | 0.4366 | 0.01358 | 0.00780 | 0.00578 | no |
| 4° | trip | time-acc. | ok | 0.4285 | 0.01368 | 0.00737 | 0.00631 | no |

Time-accurate statistics (report/transient.md): every 20-flow-through case
drifts 0.3 % or less over its window. The trip at 4°: Cd over successive
3-flow-through blocks 0.01359, 0.01366, 0.01369, 0.01370; plain 0.01380,
0.01381, 0.01381, 0.01382.

Upper-surface separation and reattachment (report/highlights.md; time-accurate
cases are their final instant): at 4° the leading-edge bubble runs from x/c
0.028-0.040 to 0.24 (plain), 0.28 (stair1) and 0.39 (trip).

Figures:
* [figures/stepped-vs-baseline-4deg-time.png](figures/stepped-vs-baseline-4deg-time.png):
  Cp and Cf at 4°, time-accurate, final instant.
* [figures/stepped-vs-baseline-vorticity.png](figures/stepped-vs-baseline-vorticity.png):
  vorticity at 4°, time-accurate, final instant (`iomcfd viz`).

### Decisions

* No stepped section for the fin; a KFm4-like step costs 41 % at the
  working load.
* Where a comparison at 4° and 1 m/s hinges on less than about 3 % drag,
  run it time-accurately: the steady solver is off by that much there.

### Assumptions

* Re 88,000 at 1 m/s from the case's ν (1.137e-6 m²/s) and the 100 mm chord.
* The drag slopes used for equal lift at 4° come from naca0007-film's
  steady plain cases at 3, 4 and 5° (1 m/s, Tu 1 %).

### Compromises

* One operating point (1 m/s, Tu 1 %); the race-time recomputation swaps
  one speed's 4° cases only.
* stair5's time-accurate average covers 3 flow-throughs; stair10 has none.

### Learnings

* A 0.1 mm step costs more than 48 h for 6 flow-throughs on 4 ranks: stair10
  wrote its 1-flow-through checkpoint and no later one. Its time step is set by cells a few microns high.
* The trip's 4° case needed 47.8 h for 20 flow-throughs, against 8.7 h for
  plain: the step's small cells again.
* Steady results at 4° were enough to mislead the naca0007-trip ranking at
  high load (conclusion 5).

### Open questions and next steps

* A time-accurate faired step at 4°, 1 m/s, Tu 1 % (about 9 h, plain's
  cost; it has no step) would show whether the faired section also loses
  its steady 4° numbers.
* Time-accurate plain and trip at 4° and 0.75 or 1.5 m/s would show whether
  the trip's remaining lead over the faired step holds there. About 9 h and
  48 h each; the trip would need a longer task limit (`--max-hours`).
