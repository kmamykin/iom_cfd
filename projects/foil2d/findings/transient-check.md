# transient-check: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/transient-check/<run id>/` (not in git), so the numbers that support a
conclusion are copied here.

This study checks, with the transient solver (pimpleFoam), the steady points
the fin-profile-selection ranking rests on
([fin-profile-selection.md](fin-profile-selection.md)).

## Run 20261015-161112 (2026-10-15, git 6649979, GCP, 8 cases)

**Setup.** The eight 4° cases of run 20261014-040114, continued from 15 to
30 chord flow-throughs. Settings as before: 1 m/s, Tu 0.1 %, kOmegaSSTLM,
medium mesh, `solver: transient`. Forces are averaged over flow-throughs
24-30.
* Seven cases continue from their final state in run 20261014-040114:
  fields, old-time fields and time step (`start_from`, new in this commit).
* 0009/100, which diverged there, starts from the steady solution of
  fin-profile-selection run 20261013-045759 and runs 30 flow-throughs.
* Image `iom-cfd:6649979`: the same OpenFOAM as `19e49d8`; only the Python
  tooling changed.

Why: after 15 flow-throughs the 4° forces were still drifting (run
20261014-040114, conclusion 3).

**Outcome.** 8 ok.
* One Spot preemption at 00:20 UTC hit the VM running three cases (0008/90,
  0009/100, 0007/100 at max_co 5). They restarted from their sources and
  lost about 8 h each.
* Wall time per case: 6.6-7.4 h for the continued cases at max_co 10, 9.2 h
  at max_co 5, 8.1 h for 0009/100 (30 flow-throughs from steady). That is
  59.5 case-hours, plus about 24 lost to the preemption.

### Conclusions

1. **The 4° forces have settled.**
   * From flow-throughs 24-27 to 27-30, Cl changes by −0.6 to +0.4 % and Cd
     by −1.3 to +0.1 %. At 15 flow-throughs it was +0.3 to +2.0 % and −1.7
     to −4.0 %.
   * Lift still oscillates by 9-11 % (standard deviation / mean): the
     shedding is the flow, not a transient.

   Confidence: high that the run length is no longer the limit.
2. **Two starting points give the same mean flow.**
   * 0009/100, started from the steady solution, reached Cl 0.397-0.401
     within 9 flow-throughs and stayed there.
   * The seven cases started from rest rose to the same level, 0.392-0.399.
   * Either start can be used. Starting from a steady solution settles in
     fewer flow-throughs.
3. **At 4° the time-accurate lift is 4-16 % below the steady value, and
   the drag 5-14 % below.**
   * At 4° every section makes about the same Cl, 0.392-0.399. Steady, they
     spread from 0.408 to 0.465.
   * The thick sections were the most wrong: Cl −14 to −16 % for 0009/80
     and 0009/100, against −4 to −5 % for 0007.
   * That matters for the comparison at equal side force. Every section
     needs more angle (more leeway) for the working-load force:
     3.8-4.8° against 3.4-4.2° steady.
4. **With the time-accurate 4° points, NACA 0007 at 100 mm is the best
   section at 1 m/s, and 0008/90 falls to fourth.** Race-time loss, % above
   the best, with the estimated resistance slope / doubled:

   | section | light (2°) | working (4°) | high (6°) | mean |
   |---|---|---|---|---|
   | 0007/100 | 0.81 / 0.36 | best | 0.48 / 0.26 | 0.43 / 0.21 |
   | 0007/90 | best | 0.32 / 0.30 | 2.54 / 1.52 | 0.95 / 0.61 |
   | 0008/100 | 2.18 / 1.12 | 0.87 / 0.43 | best | 1.02 / 0.52 |
   | 0008/90 | 1.37 / 0.79 | 0.92 / 0.60 | 1.77 / 1.13 | 1.35 / 0.84 |
   | 0009/100 | 3.27 / 1.55 | 1.61 / 0.79 | 0.05 / 0.02 | 1.64 / 0.78 |
   | 0008/80 | 0.54 / 0.46 | 2.63 / 1.70 | 4.59 / 2.86 | 2.59 / 1.67 |
   | 0009/80 | 2.26 / 1.47 | 2.75 / 1.76 | 3.27 / 2.19 | 2.76 / 1.81 |

   * With the steady 4° points, 0007/90 was best at working load and
     0007/100 1.44 / 0.63 behind it. The steady 4° point of 0007/100 was
     the least reliable of all: it oscillated 18 % and did not converge.
   * The order holds for every averaging window from 18-21 to 27-30. At
     working load 0007/100 is best in all of them, and its mean is
     0.43-0.49 / 0.20-0.24.

   Confidence: medium.
   * It is one speed, 1 m/s.
   * The 2° points of all sections, and the 6° points except 0009/80 and
     0009/100, are still steady ones.
   * Light air rests on those steady 2° points. At 4° a smooth steady
     solution turned out not to mean steady flow (conclusion 3 of run
     20261014-040114, Learnings).
5. **The time step matters little now.** Halving it (max_co 5) for 0007/100
   changes Cl by +0.9 % and Cd by +1.0 %. If only 0007/100 moved by that
   much, its working-load lead over 0007/90 (0.32 / 0.30) would shrink by
   about 0.1 (**estimate**).

### Evidence

Means over 3-flow-through blocks (`postProcessing/forceCoeffs`; this run
plus run 20261014-040114 for flow-throughs 0-15). Steady values are from
fin-profile-selection runs 20261013-045759 and 20261013-200643.

| case | Cl 12-15 | Cl 24-30 | Cl steady | Cd 12-15 | Cd 24-30 | Cd steady | ΔCl, ΔCd 24-27 → 27-30 | Cl osc | wall [h] |
|---|---|---|---|---|---|---|---|---|---|
| 0007/90 | 0.3837 | 0.3958 | 0.415 | 0.01523 | 0.01488 | 0.01634 | +0.1 %, −0.4 % | 10.0 % | 7.1 |
| 0007/100 | 0.3834 | 0.3929 | 0.408 | 0.01460 | 0.01426 | 0.01666 | +0.4 %, +0.1 % | 9.1 % | 6.6 |
| 0007/100, max_co 5 | 0.3875 | 0.3965 | 0.408 | 0.01486 | 0.01440 | 0.01666 | +0.3 %, −1.0 % | 9.3 % | 9.2 |
| 0008/80 | 0.3857 | 0.3924 | 0.450 | 0.01658 | 0.01613 | 0.01804 | 0.0 %, −0.7 % | 10.6 % | 7.1 |
| 0008/90 | 0.3854 | 0.3949 | 0.443 | 0.01594 | 0.01539 | 0.01669 | +0.1 %, −0.6 % | 9.8 % | 7.4 |
| 0008/100 | 0.3868 | 0.3985 | 0.438 | 0.01514 | 0.01475 | 0.01558 | +0.2 %, −0.5 % | 9.7 % | 7.0 |
| 0009/80 | 0.3906 | 0.3919 | 0.465 | 0.01748 | 0.01684 | 0.01870 | −0.6 %, −1.3 % | 10.9 % | 6.9 |
| 0009/100, from steady | - | 0.3981 | 0.462 | - | 0.01492 | 0.01645 | −0.4 %, −0.1 % | 10.6 % | 8.1 |

0009/100 from steady, block means: 9-12 0.3968 / 0.01476, 15-18 0.4013 /
0.01503, 27-30 0.3973 / 0.01491.

**How the ranking was computed.** This is the race-time metric of
fin-profile-selection analysis 2026-10-13 (2):
* at 1 m/s, the steady 0009/80 forces at 2, 4 and 6°;
* leeway at a 42° track, the estimated resistance slope (V dR/dV =
  1.354 N) or double it;
* equal time downwind at 0°.

The steady 4° points of all seven sections were replaced by the means over
flow-throughs 24-30. The 6° points of 0009/80 and 0009/100 were replaced by
run 20261014-040114's flow-throughs 12-15 (the flow is steady there). All
other points are steady, from runs 3 and 4.

| window | 0007/100 mean | 0007/90 | 0008/100 | 0008/90 | 0007/90 working | 0008/100 working | 0008/90 working |
|---|---|---|---|---|---|---|---|
| 18-21 | 0.49 / 0.24 | 1.04 / 0.66 | 1.09 / 0.56 | 1.44 / 0.89 | 0.46 / 0.37 | 0.84 / 0.42 | 1.06 / 0.68 |
| 21-24 | 0.45 / 0.22 | 1.01 / 0.64 | 1.05 / 0.54 | 1.39 / 0.86 | 0.44 / 0.37 | 0.90 / 0.44 | 1.01 / 0.65 |
| 24-30 | 0.43 / 0.21 | 0.95 / 0.61 | 1.02 / 0.52 | 1.35 / 0.84 | 0.32 / 0.30 | 0.87 / 0.43 | 0.92 / 0.60 |
| 27-30 | 0.43 / 0.20 | 0.95 / 0.61 | 1.01 / 0.51 | 1.35 / 0.84 | 0.29 / 0.29 | 0.85 / 0.42 | 0.88 / 0.58 |

**Section angle at the working-load force, 1 m/s** [°], steady →
time-accurate:

| 0007/90 | 0007/100 | 0008/100 | 0008/90 | 0008/80 | 0009/80 | 0009/100 |
|---|---|---|---|---|---|---|
| 3.99 → 4.20 | 3.74 → 3.84 | 3.60 → 3.82 | 3.82 → 4.21 | 4.24 → 4.81 | 4.00 → 4.81 | 3.44 → 3.80 |

### Decisions

* Proposed (see fin-profile-selection, "Where the selection stands"):
  recommend NACA 0007 at 100 mm chord, with 0008/100 as the alternative.
* **Fixed after this run: continued cases now write their final fields.**
  OpenFOAM counts adjustable write times from the start time. With
  `writeInterval` equal to the end time, a case restarted at 15
  flow-throughs never reached a write time. The seven continued cases
  therefore have forces but no final fields and no `surface.csv`:
  * no Cp/Cf highlights;
  * no viz;
  * a further continuation would have to start from run 20261014-040114
    again.

  `start_from` now sets `writeInterval` to the remaining time. A local
  check wrote the final fields and `surface.csv`. 0009/100 (started at time
  0) is complete.

### Assumptions

* As run 20261014-040114: 2D URANS represents the shedding (**not
  validated**).
* As fin-profile-selection analysis 2026-10-13 (2): the race-time inputs
  (heading, resistance slope, equal time downwind, the fin carries all the
  side force; **not verified**).
* That steady and time-accurate points can be mixed in one polar for the
  equal-force interpolation (**not verified**).

### Compromises

* 1 m/s only. The other speeds keep their steady 4° points.
* Steady 2° and 6° points for most sections.
* No surface data for the continued cases (Decisions).

### Learnings

* Continuing a transient run works: forces join smoothly at the restart.
  For 0007/90, Cl is 0.4147 at 15.000 flow-throughs and 0.4169 one step
  later, on the same rising slope. The second 15 flow-throughs took about
  7 h, against about 13 h to run 30 from rest again.
* Spot preemption restarts a task from scratch. Tasks of 7+ h on Spot lose
  a lot when it happens: here about 24 case-hours.
* A restart has to make its end time a write time (Decisions).

### Open questions and next steps

* The light-air ranking (steady 2° points) and the 6° points of the
  0007/0008 sections: transient checks at 1 m/s for the top four (0007/100,
  0007/90, 0008/100, 0008/90). That is 8 cases, starting from the steady
  solutions (about 7 h each at 30 flow-throughs; **estimate**).
* The 4° point at 0.75 and 1.5 m/s for the top four (8 cases), to see
  whether the 1 m/s ranking holds across speeds.

## Run 20261014-040114 (2026-10-14, git c715f67, GCP, 10 cases)

**Setup.**
* Cases (10), all at 1 m/s, Tu 0.1 %, kOmegaSSTLM, medium mesh (90,112
  cells):
  * the seven fin-profile-selection candidates at 4°;
  * 0009/80 and 0009/100 at 6°;
  * 0007/100 at 4° again with half the time step (`max_co` 5 instead of
    10).
* Solver: `solver: transient` (pimpleFoam, backward time scheme, 3 outer
  correctors, adaptive time step), started from a uniform free stream.
  * 15 chord flow-throughs (c/U).
  * Forces averaged over the last 6.
* Image `iom-cfd:19e49d8`, the one fin-profile-selection runs 3 and 4 used.
  c3d-standard-16 Spot, one core per case.

Why: the steady solutions behind the fin-profile-selection ranking oscillate
(at Tu 0.1 %).
* At 4°, Cd oscillates by up to 14-22 % (0007/90, 0007/100, 0008/100), and
  the working-load ranking flips when those points are left out (run
  20261013-200643).
* At 6°, 0009/80 and 0009/100 oscillate by 24-25 %.

This is the first transient foil2d run, so the default run length and time
step were part of what was checked.

**Outcome.** 9 ok, 1 failed. 0009/100 at 4° diverged at 4.7 flow-throughs
after about 7 h: omega grew to about 10⁹⁸, then a floating-point exception
in the turbulence model. All 4° cases are flagged unsteady. Wall time was
4.3-11.7 h per case, 68.5 case-hours in all.

### Conclusions

1. **At 6° the flow is steady, and the steady solver's mean drag is right.**
   * The transient lift oscillates by 0.2 %, against the steady solver's
     24-25 % in Cd.
   * Over flow-throughs 12-15:

     | case | Cd transient | Cd steady | Cl transient | Cl steady |
     |---|---|---|---|---|
     | 0009/80 | 0.02810 | 0.02797 (+0.5 %) | 0.572 | 0.579 |
     | 0009/100 | 0.02575 | 0.02589 (−0.5 %) | 0.577 | 0.520 |

     0009/100's steady Cl was off by 11 %.
   * The split differs even where the totals agree. For 0009/100,
     friction is 0.0077 transient against 0.0055 steady, and pressure drag
     0.0183 against 0.0204.

   The steady oscillation at 6° was the steady solver's, not the flow's.
   The high-load comparisons of fin-profile-selection stand, apart from
   0009/100's lift at 6°.

   Confidence: high for these two cases. The other five sections at 6°
   oscillated by at most 2 % in the steady runs and were not checked.
2. **At 4° every section sheds vortices.**
   * In the final 3 flow-throughs Cl oscillates by 9-11 % (standard
     deviation / mean) for all seven, including the sections that were
     steady in the steady runs.
   * The instantaneous surface plots show the same picture for every
     section:
     * a laminar boundary layer to about 0.3-0.4 c;
     * laminar separation;
     * vortices rolling up and convecting over the rear half (Cf swinging
       ±0.01 from about 0.5 c to the trailing edge).

     These are snapshots; separation points from them are not means.
3. **After 15 flow-throughs the 4° forces are still drifting, so they can't
   rank the sections yet.**
   * From flow-throughs 9-12 to 12-15, Cl rises 0.3-2.0 % and Cd falls
     1.7-4.0 %.
   * At 15 flow-throughs Cl is 0.383-0.391 for all seven, against 0.408-0.465
     steady.
   * The slow rise matches the build-up of circulation after an impulsive
     start. By thin-airfoil theory (Wagner function, R.T. Jones's
     approximation; **estimate**), lift over flow-throughs 12-15 is about
     95 % of its final value, and 30 flow-throughs bring it to about 99 %.
   * So part of the gap to the steady lift is the run length, not the
     physics.
4. **The time-accurate means have more friction and less pressure drag than
   the steady ones at 4°.**
   * Friction: +14-17 % (+61 % for 0007/100).
   * Pressure drag: −11 to −35 %.
   * Total Cd is 3-12 % below steady over flow-throughs 12-15, and still
     falling.

   The steady solutions held more reversed flow on the suction side.
5. **The default time step (max_co 10) is adequate but not negligible.**
   Halving it for 0007/100 at 4° changes Cl by +1.3 % and Cd by +1.8 %
   (flow-throughs 12-15). That is the size of the drift (conclusion 3) and
   of some differences between sections. The lift oscillation is 9.2 % in
   both.

   Confidence: medium. It is one case, the effect is probably the same
   for all sections, and that is not verified.

### Evidence

Means over 3-flow-through blocks, from `postProcessing/forceCoeffs`. Steady
values are from fin-profile-selection runs 20261013-045759 and
20261013-200643 (same mesh, model, Tu and image). Cl osc is the standard
deviation of Cl over flow-throughs 12-15, as % of its mean.

| case | Cl 6-9 | Cl 9-12 | Cl 12-15 | Cl steady | Cd 6-9 | Cd 9-12 | Cd 12-15 | Cd steady | Cl osc | wall [h] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0007/90, 4° | 0.360 | 0.378 | 0.384 | 0.415 | 0.01636 | 0.01558 | 0.01523 | 0.01634 | 9.7 % | 5.8 |
| 0007/100, 4° | 0.362 | 0.379 | 0.383 | 0.408 | 0.01562 | 0.01501 | 0.01460 | 0.01666 | 9.2 % | 6.4 |
| 0007/100, 4°, max_co 5 | 0.363 | 0.380 | 0.388 | 0.408 | 0.01569 | 0.01512 | 0.01486 | 0.01666 | 9.2 % | 11.7 |
| 0008/80, 4° | 0.355 | 0.385 | 0.386 | 0.450 | 0.01794 | 0.01726 | 0.01658 | 0.01804 | 10.4 % | 4.3 |
| 0008/90, 4° | 0.350 | 0.378 | 0.385 | 0.443 | 0.01728 | 0.01629 | 0.01594 | 0.01669 | 10.0 % | 9.1 |
| 0008/100, 4° | 0.363 | 0.382 | 0.387 | 0.438 | 0.01608 | 0.01557 | 0.01514 | 0.01558 | 10.1 % | 5.4 |
| 0009/80, 4° | 0.354 | 0.385 | 0.391 | 0.465 | 0.01928 | 0.01810 | 0.01748 | 0.01870 | 10.7 % | 5.8 |
| 0009/100, 4° | failed at 4.7 flow-throughs | | | 0.462 | | | | 0.01645 | | about 7 |
| 0009/80, 6° | 0.542 | 0.565 | 0.572 | 0.579 | 0.02911 | 0.02862 | 0.02810 | 0.02797 | 0.2 % | 7.2 |
| 0009/100, 6° | 0.544 | 0.570 | 0.577 | 0.520 | 0.02673 | 0.02628 | 0.02575 | 0.02589 | 0.2 % | 5.5 |

**Friction and pressure drag** (`results.csv`, transient window 9-15
against the steady window):

| case | Cd friction, transient / steady | Cd pressure, transient / steady |
|---|---|---|
| 0007/90, 4° | 0.00699 / 0.00612 | 0.00841 / 0.01022 |
| 0007/100, 4° | 0.00676 / 0.00419 | 0.00805 / 0.01247 |
| 0008/80, 4° | 0.00754 / 0.00660 | 0.00938 / 0.01144 |
| 0008/90, 4° | 0.00718 / 0.00630 | 0.00893 / 0.01038 |
| 0008/100, 4° | 0.00684 / 0.00601 | 0.00852 / 0.00957 |
| 0009/80, 4° | 0.00763 / 0.00653 | 0.01016 / 0.01217 |
| 0009/80, 6° | 0.00784 / 0.00746 | 0.02052 / 0.02052 |
| 0009/100, 6° | 0.00769 / 0.00549 | 0.01832 / 0.02039 |

**Provisional effect on the ranking.** Not a result: the 4° forces are
still drifting.
* Method: at 1 m/s and Tu 0.1 %, the steady 4° points (and the 0009 6°
  points) of fin-profile-selection runs 3 and 4 were replaced by these
  flow-throughs 12-15 means. 0009/100 keeps its steady 4° point. The
  race-time metric was then recomputed, at the steady 0009/80 forces.
* Working-load race-time loss (estimated resistance slope / doubled):

  | section | loss |
  |---|---|
  | 0007/100 | best |
  | 0008/100 | 0.87 / 0.43 |
  | 0007/90 | 1.02 / 0.67 |
  | 0008/90 | 1.45 / 0.88 |
  | 0009/100 (steady 4° point) | 2.33 / 0.98 |
  | 0008/80 | 2.74 / 1.74 |
  | 0009/80 | 2.75 / 1.73 |

  With the steady points, 0007/90 was best and 0008/90 0.64 / 0.26
  behind.
* The time-accurate lift at 4° is lower, so every section needs more angle
  for the reference force: 3.9-4.9° against 3.4-4.2° steady.

The report's `selection_compare.md` for this run is not meaningful: most
candidates have a single angle.

### Decisions

* **Continue the eight 4° cases to 30 flow-throughs**, from the final time
  step of this run (user, 2026-10-15). That is run 20261015-161112, image
  `iom-cfd:6649979`, which adds `start_from`:
  * a continued case copies its source's final fields, old-time fields and
    time step, and runs on to `flow_times`, now the total (30);
  * 0009/100, which diverged here, starts from the steady solution of
    fin-profile-selection run 20261013-045759.
* **The 6° points need no transient check** beyond these two. The other
  sections' 6° points oscillated by at most 2 % steady.

### Assumptions

* That the time average over the last flow-throughs, once the drift has
  stopped, is the fin's mean force (**not yet shown**: drift remains).
* That 2D URANS with the transition model represents the shedding over the
  rear half. Its frequency and amplitude are **not validated**: there are
  no measurements at Re 80-90k for these sections.
* Wagner-function estimate of the lift build-up (thin-airfoil theory;
  **estimate**).

### Compromises

* 15 flow-throughs was too short. The defaults (`flow_times` 15,
  `average_times` 6) were not checked before the run.
* One speed (1 m/s) and the 4° and 6° points only. The equal-force
  comparison still uses steady 2° and 6° points for most sections.
* One time-step check, on one case.

### Learnings

* **Cost and time.**
  * About 150 time steps per flow-through, 7.6-15.6 s per step on one GCP
    core: 4.3-9.1 h per case at max_co 10 (11.7 h at max_co 5). That is
    1.2-2.6× the 3.5 h I estimated from a local probe of 0.5
    flow-throughs, which measured only the start-up steps, on a faster
    core.
  * Four MPI ranks were slower locally (10.4 s against 7.0 s per step),
    but that test ran alongside other containers.
* **An impulsive start leaves a slow lift transient.** Starting from a
  converged steady solution, or continuing a run, avoids most of it. That
  is what `start_from` is for.
* **A steady solver can oscillate where the real flow is steady (here at
  6°).** It can also be smooth where the flow sheds. At 1 m/s and 4°, the
  steady Cd of 0008/80, 0008/90, 0008/100 and 0009/80 varied by only
  0.7-1.6 %, yet the transient flow sheds on all of them.

### Open questions and next steps

* Run 20261015-161112: do the 4° means settle between flow-throughs 15 and
  30, and does the section ranking hold?
* The equal-force comparison needs transient points at 2° and 6° for the
  sections that shed, if the 4° results move the ranking.
* Validation of the shedding (frequency, amplitude) against low-Re
  measurements.
