# fin-profile-selection: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results themselves live
in `runs/fin-profile-selection/<run id>/` (not in git), so the numbers that
support a conclusion are copied here. Entries are written by the
`study-findings` skill (`/study-findings foil2d/fin-profile-selection`) or by
hand, and are not rewritten later: a later run that changes a conclusion says
so in its own entry.

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
