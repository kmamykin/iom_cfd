# naca0007-film: findings log

Does a self-adhesive film wrapped round the nose of an existing NACA 0007
fin pay? And how does it compare with the cut trip of stepped-vs-baseline?
Both have the same 0.2 mm edge at x/c 0.5. The film adds material ahead of
the edge; the trip removes it behind the edge. This is the
[ht35-film](ht35-film.md) study on NACA 0007 at 100 mm, the all-round
recommendation of [fin-profile-selection.md](fin-profile-selection.md).
The trip runs in its own study, `naca0007-trip`, and is analysed here.

Newest entry first. Results live in `runs/naca0007-film/<run id>/` and
`runs/naca0007-trip/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. Symbols follow
[docs/nomenclature.md](../../../docs/nomenclature.md): S_h, D_h = D_v + D_i,
section angle α.

## Runs 20261025-161234 (film) and 20261025-173646 (trip) (2026-10-25, git a5641dc, GCP, 108 + 54 cases)

**Setup.**
* Three sections at 100 mm chord:
  * plain NACA 0007 (`naca0007`);
  * the film (`film:naca0007:x=0.5,t=0.002`):
    * 0.2 mm, an exact offset of the section from x/c 0.5 on one surface
      round the nose to x/c 0.5 on the other;
    * nose radius 0.54 → 0.74 mm, 7.40 mm thick;
  * the cut trip (`stair1:naca0007:x=0.5,h=0.002`):
    * one 0.2 mm backward-facing step per side at x/c 0.5;
    * plain ahead of the step, scaled to 93.5 % thickness behind it.
  * Both edges are square, with a 10 µm lip fillet and a 50 µm foot
    fillet.
* Swept as ht35-film: Tu 0.1, 1 and 2 %; 0.75, 1.0 and 1.5 m/s; α 0, 2, 3, 4,
  5 and 6°.
* Fixed: kOmegaSSTLM, steady (simpleFoam), medium mesh, with the step's mesh
  refined to a fraction of its height (cmesh.py).
* Compute: image `iom-cfd:a5641dc`, c3d-standard-16 Spot VMs, 4 ranks per
  case.
* Plain and film ran in naca0007-film. The trip ran in naca0007-trip
  straight after, on the same image and settings.

**Outcome.**
* **naca0007-film:** 96 ok, 12 not converged, 0 failed (after one rerun).
  * The 12 not converged: 10 at Tu 0.1 %, 2 at Tu 1 %; 8 of them at 4°.
  * 36 unsteady: 23 of 36 at Tu 0.1 %, 13 of 36 at Tu 1 %, none at Tu 2 %.
  * Plain NACA 0007 at Tu 0.1 %, 1 m/s, 5° failed on GCP:
    * a floating-point exception in the turbulence model at iteration 141;
    * the same case converged in custom-section-screen.
  * It was rerun locally into the same run (`iomcfd run --run-id
    20261025-161234 --only ... --force`):
    * image `iom-cfd:latest`, git 799ac33, with the same `src/`, foil2d
      project and geometry as a5641dc;
    * it reached the iteration limit unconverged at Cl 0.4985, Cd 0.02304;
    * custom-section-screen had Cl 0.4994, Cd 0.02289.
  * 17.8 case-hours.
* **naca0007-trip:** 49 ok, 5 not converged (4 at Tu 0.1 %, 1 at Tu 1 %; 4 of
  the 5 at 4°).
  * 17 unsteady: 11 of 18 at Tu 0.1 %, 6 of 18 at Tu 1 %, none at Tu 2 %.
  * 12.1 case-hours, median 10.6 min per case. The job took 59 min of wall
    time, against an estimate of 30-40 min (Learnings).

### Conclusions

1. **Wrapping NACA 0007 in the film doesn't pay. At Tu 1 % it breaks even
   (+0.05 % of race time, slope ×1; +0.06 % with ×2), and at Tu 2 % it
   costs 0.37 % (0.18 %).**
   * At Tu 1 % the film is faster at 5 of 9 load points (−0.22 to +0.43 %).
   * At Tu 2 % it is faster at 2 of 9 (−1.03 to +0.13 %).
   * At Tu 0.1 % the result is −0.29 % (×1), faster at 4 of 9, and runs from
     −1.55 to +0.89 %. This is noise-limited (conclusion 6).
   * Same verdict as on HT35, where the film cost 0.16 % at Tu 1 % and 0.46 %
     at Tu 2 %.
   * NACA 0007 does a little better at Tu 1 % than HT35 did, because its
     upwind is better with the film (next conclusion).
   * Confidence: medium.
     * Tu 2 % is steady flow throughout.
     * At Tu 1 % the 2° and 4° comparison points rest on unsteady cases
       (13 of 36).
2. **The cut trip is the only variant that pays at Tu 1 %: +0.40 % of race
   time (slope ×1; +0.22 % with ×2), faster at 9 of 9 load points (+0.12 to
   +0.73 %).**
   * Per load: light +0.23, working +0.32, high +0.64 %.
   * At equal side force S_h its fin drag D_h is 0.1-4.7 % lower in 9 of 9
     comparisons.
   * At Tu 2 % it loses 0.15 % (×1), faster at 4 of 9.
   * At Tu 0.1 % it gains +0.24 %, faster at 5 of 9, with a range of −0.86
     to +2.34 %. This is noise-limited.
   * Confidence: medium at Tu 1 %. Steady flow in 12 of 18 trip cases; at 2°
     steady repeats time-accurate (Learnings).
3. **The film and the trip do the same thing to the boundary layer. The
   difference between them is where the material is.**
   * At 1 m/s, Tu 1 %, the upper surface's skin friction behind the edge is
     the same for both at 0° and 2° (figure).
   * Both separate at the edge (x/c 0.50). At 2° plain NACA 0007 separates
     laminar at x/c 0.72 and doesn't reattach.
   * Upwind at Tu 1 % both gain: film +0.19 %, trip +0.31 % of race time.
     The step they share helps NACA 0007 upwind at this Tu. On HT35 the
     film's upwind was −0.07 %.
   * Downwind (0°) they part:
     * The film costs 1.0-2.8 % section drag at Tu 1 %. Its pressure drag is
       +0.00040 to +0.00052, with friction −0.00021 to −0.00028.
     * The trip saves 0.7-2.0 %. Its pressure drag is −0.00006 to
       +0.00003, with friction −0.00012 to −0.00016.
     * The film's thicker front costs pressure drag. The trip's thinner rear
       offsets the bubble behind its step.
   * Confidence: medium. This is inferred from force splits and Cf curves at
     one speed, plus 0° at all speeds.
4. **Most or all of the trip's 0° gain is plausibly its thinner rear, not
   the step.**
   * NACA 0006 against 0007 at 100 mm, 0°, Tu 1 % (fin-profile-selection
     run 20261012-175146): 1 % c less thickness is 3.5-4.2 % less drag at
     0.75-1.5 m/s.
   * The trip's rear is 6.5 % thinner (relative). NACA 0006 is 14 % thinner
     everywhere. That puts the thinner rear at about 0.8-1.6 % less drag:
     half to all of the full-section effect, scaled by 6.5/14.
   * The trip's measured 0° gain is 0.7-2.0 %.
   * This is an **estimate** (linear scaling), **not verified**. A faired
     section with the trip's thickness and no step would settle it.
   * It confirms the doubt raised about stepped-vs-baseline's 0° result in
     ht35-film.md (conclusion 4 there).
   * Confidence: low.
5. **Plain HT35 at 7.0 % is still the best of the five sections. The trip
   brings NACA 0007 close to it at Tu 1 % only.**
   * Race-time gain over plain NACA 0007 (slope ×1), all five on the same
     image:
     * HT35 7.0 %: +0.59 / +0.45 / +0.10 % at Tu 0.1 / 1 / 2 %.
     * NACA 0007 trip: +0.24 / +0.40 / −0.15 %.
     * HT35 7.0 % + film: +0.46 / +0.30 / −0.37 %.
     * NACA 0007 + film: −0.29 / +0.05 / −0.37 %.
   * Against this run's plain NACA 0007, HT35's gain at Tu 1 % is +0.45 %.
     Against custom-section-tu's it is +0.36 % (ht35-film.md). The
     difference is NACA 0007's repeat noise (conclusion 6), about 0.1 % of
     race time.
   * A trip on HT35 is not run.
   * Confidence: medium at Tu 1-2 %; low at Tu 0.1 %.
6. **At Tu 0.1 % no steady answer here is reliable.**
   * Plain NACA 0007 repeats custom-section-screen (run 20261018-043724) to
     within 0.25 % in Cd at only 9 of 17 points.
   * The worst is 11.4 %, at 1 m/s 4°, not converged in both runs.
   * At Tu 1 %, 14 of 18 points repeat custom-section-tu (run
     20261018-104350) to within 0.25 %. The worst is 3.2 % (1 m/s 4°, not
     converged), and 1.5 % at 0.75 m/s 4° with both runs converged and
     steady.
   * At Tu 2 %, 18 of 18 repeat to 0.01 %.
   * Confidence: high (that the noise is this size).

### Evidence

**Race-time gain over plain NACA 0007**, % of race time (+ = faster):
* Mean of 9 points: 3 speeds × 3 loads of `design/loads.csv`.
* Up and down are each leg's share, slope ×1.
* Computed with `iomcfd.racetime` from the runs' results.csv
  (`fin_forces`, `race_time`).

| Tu | section | slope ×1 | slope ×2 | up | down | faster at | range | light / working / high |
|---|---|---|---|---|---|---|---|---|
| 0.1 % | film | −0.29 | −0.09 | −0.13 | −0.16 | 4/9 | −1.55..+0.89 | −0.15 / −0.31 / −0.42 |
| 0.1 % | trip | +0.24 | +0.17 | +0.21 | +0.03 | 5/9 | −0.86..+2.34 | +0.30 / −0.13 / +0.54 |
| 1 % | film | +0.05 | +0.06 | +0.19 | −0.14 | 5/9 | −0.22..+0.43 | −0.20 / −0.01 / +0.36 |
| 1 % | trip | +0.40 | +0.22 | +0.31 | +0.09 | 9/9 | +0.12..+0.73 | +0.23 / +0.32 / +0.64 |
| 2 % | film | −0.37 | −0.18 | −0.12 | −0.25 | 2/9 | −1.03..+0.13 | −0.47 / −0.46 / −0.18 |
| 2 % | trip | −0.15 | −0.07 | −0.04 | −0.11 | 4/9 | −0.75..+0.21 | −0.19 / −0.21 / −0.04 |

**All five sections, race-time gain over plain NACA 0007**, % (slope ×1 /
×2):
* All on image a5641dc: this run, naca0007-trip, and ht35-film run
  20261025-145441.

| section | Tu 0.1 % | Tu 1 % | Tu 2 % |
|---|---|---|---|
| HT35 7.0 % | +0.59 / +0.36 | +0.45 / +0.25 | +0.10 / +0.04 |
| HT35 7.0 % + film | +0.46 / +0.37 | +0.30 / +0.19 | −0.37 / −0.18 |
| NACA 0007 trip | +0.24 / +0.17 | +0.40 / +0.22 | −0.15 / −0.07 |
| NACA 0007 + film | −0.29 / −0.09 | +0.05 / +0.06 | −0.37 / −0.18 |

**Fin drag D_h at equal side force S_h, relative to plain NACA 0007**:
* The forces are what plain NACA 0007 makes at the reference α.
* Whole fin, 360 mm span, section + induced drag.
* Film: report/selection_compare.csv of naca0007-film; '*' = an unsteady or
  not-converged point.
* Trip: the same interpolation (`iomcfd.racetime.at_force`) across the two
  runs; no flags computed.

| speed [m/s] | ref α | film, Tu 0.1 % | film, Tu 1 % | film, Tu 2 % | trip, Tu 0.1 % | trip, Tu 1 % | trip, Tu 2 % |
|---|---|---|---|---|---|---|---|
| 0.75 | 2° | +6.3 %* | +2.5 %* | +1.6 % | −0.5 % | −0.7 % | −0.3 % |
| 0.75 | 4° | +7.4 %* | +0.4 % | +1.1 % | +6.9 % | −0.1 % | +0.3 % |
| 0.75 | 6° | −5.7 % | −4.7 % | −3.3 % | −4.2 % | −2.8 % | −1.5 % |
| 1.0 | 2° | +7.6 %* | +0.6 %* | +2.5 % | +1.2 % | −1.8 % | +1.2 % |
| 1.0 | 4° | +7.5 %* | −1.1 %* | +1.1 % | +12.2 % | −2.6 % | +0.2 % |
| 1.0 | 6° | −7.2 %* | −5.0 % | −3.0 % | −5.2 % | −1.5 % | −1.0 % |
| 1.5 | 2° | −0.0 %* | +0.8 %* | +4.6 % | −0.8 % | −1.3 % | +2.9 % |
| 1.5 | 4° | +8.3 %* | −3.5 %* | +0.7 % | +1.2 % | −4.7 % | −0.1 % |
| 1.5 | 6° | −0.7 %* | −3.5 % | −2.4 % | +1.1 % | −0.3 % | −0.0 % |

**Section drag at 0°**, Cd (change against plain), results.csv:

| Tu | speed [m/s] | plain | film | trip |
|---|---|---|---|---|
| 0.1 % | 0.75 | 0.01258 | 0.01309 (+4.0 %) | 0.01281 (+1.8 %) |
| 0.1 % | 1.0 | 0.01115 | 0.01143 (+2.5 %) | 0.01101 (−1.3 %) |
| 0.1 % | 1.5 | 0.00932 | 0.00931 (−0.1 %) | 0.00913 (−2.1 %) |
| 1 % | 0.75 | 0.01288 | 0.01301 (+1.0 %) | 0.01279 (−0.7 %) |
| 1 % | 1.0 | 0.01124 | 0.01156 (+2.8 %) | 0.01114 (−0.8 %) |
| 1 % | 1.5 | 0.00937 | 0.00955 (+1.9 %) | 0.00918 (−2.0 %) |
| 2 % | 0.75 | 0.01340 | 0.01351 (+0.8 %) | 0.01327 (−1.0 %) |
| 2 % | 1.0 | 0.01173 | 0.01188 (+1.3 %) | 0.01169 (−0.4 %) |
| 2 % | 1.5 | 0.00988 | 0.01067 (+8.0 %) | 0.01047 (+6.0 %) |

At Tu 2 % and 1.5 m/s both edges bring transition forward. Friction drag is
+0.00064 for both, the largest cost in the table, as on HT35 (+7.7 %).

![Cp and Cf, plain NACA 0007, the film and the trip, 1 m/s, Tu 1 %, 0, 2 and 4°](figures/naca0007-film-trip.png)

Drawn from the three runs' `surface.csv` by a one-off matplotlib script
(not in the repository). The report can't overlay cases from two runs.
* **0° and 2°:** the film's and the trip's Cf curves behind the edge lie on
  top of each other.
* **4°:**
  * Both edges lengthen the leading-edge bubble, from x/c 0.22 to about
    0.31.
  * Both lower the turbulent friction behind it, the trip's most.
  * Plain NACA 0007 at 4° is not converged and is unsteady.

### Decisions

* **Don't wrap the fin, on NACA 0007 or on HT35.** The film is break-even at
  best (Tu 1 %) and costs 0.37 % of race time at Tu 2 %.
* The cut trip is not recommended yet:
  * Its gain is at Tu 1 % only (+0.40 %), and it loses at Tu 2 % (−0.15 %).
  * Part of that gain may be its thinner rear (conclusion 4).
  * Plain HT35 at 7 % is as good or better at every Tu.
* No time-accurate runs. At Tu 1 % and 2° steady already repeats
  time-accurate (Learnings). At Tu 0.1 % time-accurate runs would cost
  about 48 h per stepped case.

### Assumptions

* **Film and trip shape:**
  * a square edge with fillets;
  * smooth surfaces, no roughness;
  * the edge straight along the span.
  * A real tape edge, or a sanded step, is not that clean. **Not verified**.
* **kOmegaSSTLM:** a step acts on transition only through the separation it
  causes; there is no roughness-induced transition. **Not verified** for a
  0.2 mm step (ht35-film.md, Assumptions).
* **Race-time inputs as custom-section.md:**
  * the loads of `design/loads.csv`;
  * the resistance slope VDRDV, an estimate run at ×1 and ×2 (**not
    verified**);
  * track 42°, span 360 mm, e = 0.9;
  * equal time upwind and downwind.
* The Tu values stand for calm, moderate and rough water. The pond's
  turbulence has not been measured.
* **The thickness sensitivity in conclusion 4:**
  * from NACA 0006 against 0007 (fin-profile-selection run 20261012-175146,
    medium mesh, an older image);
  * scaled linearly to a rear-only thinning. **Estimate**.

### Compromises

* **Steady solver.** At Tu 0.1 % the steady answers are noise-limited, so
  conclusions there are low confidence. At Tu 1 % the film's comparison
  points rest on unsteady cases.
* **Medium mesh, and the edge not mesh-checked.** For a much larger step
  (0.95 mm, stepped-checks), the medium-to-fine change was +2.3 % in Cd.
  That is as large as most differences here.
* **One failed case rerun locally** (same code, different image build and
  hardware). Its value enters the Tu 0.1 % high load at 1 m/s.
* **The trip's flags are not in the equal-force table.** The report can't
  compare across runs.
* **One film and one trip:** 0.2 mm at x/c 0.5. No other heights or
  positions were run.

### Learnings

* **Steady at 2°, Tu 1 %, 1 m/s repeats the time-accurate results of
  stepped-vs-baseline (run 20261023-201101, read from the bucket):**

  | case | steady here | time-accurate (stepped-vs-baseline) |
  |---|---|---|
  | plain | Cl 0.163, Cd 0.01225 | Cl 0.1629, Cd 0.01224 |
  | trip | Cl 0.193, Cd 0.01188 | Cl 0.1932, Cd 0.01188 |

  So at Tu 1 % and this angle the steady solver is enough.
* **The same step behaves the same whether material is added ahead of it or
  removed behind it.** What decides the result is the thickness
  distribution it comes with.
* **Batch marks a whole job FAILED if one task fails.**
  * The chained submit script waited for SUCCEEDED, so it didn't submit the
    trip, and the trip was submitted by hand about 1 min later.
  * A future chain should look at task counts, not the job state.
* **Compute:**
  * Stepped cases (film or trip, 129,536 cells) take a median of about
    11 min: film 10.9, trip 10.6.
  * Plain cases (90,112 cells) take 3.8 min.
  * The trip job's estimate used the median of a mixed run (7-8 min), which
    is why 30-40 min became 59.
  * Estimate stepped-only jobs at about 11 min a case.

### Open questions and next steps

* **Separate the trip's step from its thinner rear:** a faired section with
  the trip's thickness distribution and no step.
  * It needs a new geometry option (stepped.py), e.g. `stair1:...:faired`.
  * Steady over this sweep: 54 cases, about 10 case-hours.
* **A trip cut into HT35** (`stair1:file:ht35-t070.dat:x=0.5,h=0.002`), if a
  trip is still of interest. HT35 separates laminar at 2° too (x/c 0.68,
  ht35-film.md).
* **Highlights for a next run:**
  * `faired-vs-trip`: 1 m/s, Tu 1 %, 0° and 2°, compare along foil. Is the
    0° gain the step or the rear?
  * `trip-tu2`: 1.5 m/s, Tu 2 %, 0°. Both edges move transition forward
    there, and that is the largest cost.
