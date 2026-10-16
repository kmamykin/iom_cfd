# stepped-checks: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/stepped-checks/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. This study checks the numerics of stepped
(Kline-Fogleman) sections before [stepped-vs-naca](../studies/stepped-vs-naca.yaml)
is trusted; the plain-section mesh check is
[mesh-finalists](mesh-finalists.md).

## Run 20261014-043413 (2026-10-14, git 0227c8c, GCP, 2 cases)

**Setup.** Check (b) of run 20261013-190301 again: transient (pimpleFoam)
on the medium mesh, 15 c/U, forces averaged over the last 6. The operating
point is unchanged (1 m/s, 4°, Tu 1 %). Changes since that run:
* Each case starts from 2000 steady iterations (`start_iter`), not from the
  uniform inflow.
* The stair1 step (x/c 0.5, 30 % deep) runs at maxCo 5 instead of 10.
* NACA 0009 stays at maxCo 10, so its change shows the effect of the start
  alone.

Image `iom-cfd:0227c8c`, one c3d-standard-16 Spot VM, 4 ranks per case.

**Outcome.** 2 ok, no preemption. NACA 0009 is flagged unsteady.

### Conclusions

1. **The stair1 flow is steady, and the steady solver's answer is its
   answer.**
   * Transient against steady (medium mesh, run 20261013-190301): Cl
     +0.04 %, Cd −0.04 %.
   * Every flow-through from the first to the fifteenth has the same mean to
     four digits: Cl 0.4346, Cd 0.01856. The ripple is ±0.2 %.
   * Separation ahead of the step (x/c 0.407) and reattachment behind it
     (13.1 step heights) match the steady case.

   Confidence: high, at this operating point.
2. **The steady NACA 0009 solution is unstable in time.**
   * Started from it, an oscillation grows from ±0.6 % in Cl (1-2 c/U) to
     ±6.2 % (14-15 c/U), and the mean drifts down.
   * The last flow-through averages Cl 0.4354 and Cd 0.01591. The reported
     6 c/U window (Cl 0.4436, Cd 0.0162) mixes that growth with the drift,
     so it is not a stationary mean either.

   Confidence: high that the steady solution isn't the time-accurate one.
   Low on where it ends.
3. **The time-averaged NACA 0009 state is bracketed, not known.**
   * Run 20261013-190301 approached it from below (from rest): at 15 c/U, Cl
     0.416 and Cd 0.0167, with Cd still falling.
   * This run approaches it from above (from the steady solution): Cl 0.435,
     Cd 0.0159, both still moving.
   * Against the steady result (Cl 0.4479, Cd 0.01636), the bracket is Cl
     −7 to −3 % and Cd −3 to +2 %.

   This supersedes run 20261013-190301's reading that "the lift gap looks
   real" at −7 %: −7 % is one end of the bracket. Confidence: medium (two
   runs that haven't converged, approaching from opposite sides).
4. **stair1's drag penalty survives the unsteadiness.**
   * Against NACA 0009's bracket, stair1 has 11-17 % more drag. Its lift is
     0 to +4.5 % higher at the same aoa, so the comparison is roughly at
     equal side force.
   * The steady comparison said +13 % Cd and −3 % Cl. So the ranking of
     stair1 below plain 0009 holds; the steady lift deficit was mostly
     NACA 0009's steady over-prediction.

   Confidence: medium (one operating point; the NACA end-state unknown).

### Evidence

Means per flow-through, from `postProcessing/forceCoeffs/0/coefficient.dat`
in the bucket (not fetched; streamed). The other numbers are from
`results.csv` of this run and of run 20261013-190301.

| c/U | NACA 0009 Cl [min, max] | NACA 0009 Cd | stair1 Cl | stair1 Cd |
|---|---|---|---|---|
| 1-2 | 0.4479 [0.4451, 0.4501] | 0.01636 | 0.4345 | 0.01856 |
| 5-6 | 0.4476 [0.4431, 0.4520] | 0.01635 | 0.4346 | 0.01856 |
| 9-10 | 0.4480 [0.4388, 0.4580] | 0.01642 | 0.4346 | 0.01855 |
| 12-13 | 0.4423 [0.4194, 0.4638] | 0.01609 | 0.4346 | 0.01855 |
| 13-14 | 0.4441 [0.4191, 0.4634] | 0.01634 | 0.4346 | 0.01855 |
| 14-15 | 0.4354 [0.4080, 0.4619] | 0.01591 | 0.4346 | 0.01855 |

| NACA 0009, medium mesh | Cl | Cd | vs steady |
|---|---|---|---|
| steady (run 20261013-190301) | 0.4479 | 0.01636 | |
| transient from rest, 14-15 c/U (run 20261013-190301) | 0.4159 | 0.01672 | Cl −7.1 %, Cd +2.2 % |
| transient from steady, 14-15 c/U (this run) | 0.4354 | 0.01591 | Cl −2.8 %, Cd −2.8 % |
| transient from steady, last-6-c/U window (`results.csv`) | 0.4436 | 0.01621 | Cl −1.0 %, Cd −0.9 % |

At the final time step, the NACA 0009 surface (an instantaneous snapshot)
shows the bubble split. It separates at x/c 0.292 and reattaches at 0.489,
then separates again from 0.528 to the trailing edge. The steady bubble
spans 0.276-0.689.

### Decisions

* For the stair1 candidates, the steady solver is adequate at this point.
* For the plain sections it isn't exact: steady overstates NACA 0009's lift
  by 3-7 % here. That doesn't change stair1 against 0009 (conclusion 4),
  but it does matter wherever plain sections a few percent apart are
  ranked. That is fin-profile-selection's case, which used steady results.
  `main`'s transient-check study looks at this at Tu 0.1 %, starting from
  rest for 15 c/U, which run 20261013-190301 found too short at Tu 1 %.
* Not decided: the scope of stepped-vs-naca. The proposal stands: steady
  for plain and stair1; stair5 and stair10 flagged or left out.

### Assumptions

* That the growing NACA 0009 oscillation is the laminar bubble shedding,
  not a numerical artefact of maxCo 10. Halving the time step wasn't tried
  on NACA 0009. **Not verified.**
* That runs from rest and from steady converge to the same state, between
  their 15 c/U values. **Not verified.**

### Compromises

* 15 c/U wasn't enough for NACA 0009 from either start. No longer run was
  made.
* One operating point (1 m/s, 4°, Tu 1 %).

### Learnings

* **The steady start works.**
  * It cost 3.8 min (NACA 0009) and 5.3 min (stair1) of steady iterations.
  * Both runs continued smoothly from it: the first flow-through has the
    steady means. There is one start-up spike in its first steps, to Cl 0.51
    for NACA 0009 and 0.49 for stair1.
  * The time-step guard didn't trigger.
* **stair1 at maxCo 5** ran 8,974 steps: mean dt 1.34e-4 s, 3.1 s per step,
  7.9 h. That is less than the 9 h estimated.
* **NACA 0009 ran 2,012 steps at 4.2 s per step,** 2.4 h. Run
  20261013-190301 managed 2.5 s per step on the same VM type. The difference
  wasn't investigated.
* 10.3 case-hours in all; the job took 7.9 h.

### Open questions and next steps

* **Where does NACA 0009 settle?** A 40 c/U transient from the steady start
  (about 6.5 h at 4 ranks, estimated from this run) would show whether the
  oscillation saturates and what the mean is. A maxCo 5 repeat would show
  whether the growth depends on the time step.
* **Highlights,** if that run is made: NACA 0009 from rest and from steady
  with the `separation` view. Where does the bubble sit, and does it shed?

## Run 20261013-190301 (2026-10-13, git 6a82393, GCP, 11 cases)

**Setup.** Three sections cut from NACA 0009 at 80 mm chord:
* plain NACA 0009;
* stair1, one step per side at x/c 0.5, 30 % of the local half-thickness
  deep (0.95 mm), `stair1:naca0009:x=0.5,d=0.3`;
* stair10, ten 0.1 mm steps per side from x/c 0.3 to 0.9.

The operating point is stepped-vs-naca's typical upwind point: 1 m/s
(Re 70,400), 4°, Tu 1 %, kOmegaSSTLM. Two checks:
* (a) Mesh convergence: steady solver on the coarse, medium and fine meshes
  (each level 2× the cells; the step refinement scales with the level).
* (b) Steady vs transient: medium mesh, NACA 0009 and stair1 only. The
  transient runs used pimpleFoam at maxCo 10 for 15 c/U, with forces
  averaged over the last 6, started from the uniform inflow.

This is the first run of the study and the first check of the marched step
meshes (`cmesh.py`). Image `iom-cfd:6a82393`, the first one CI built from a
branch. Four c3d-standard-16 Spot VMs, 4 ranks per case, 2 cases per VM.

**Outcome.** 10 ok, 1 failed: the stair1 transient diverged. 4 flagged
unsteady: all three stair10 cases (steady solver), and the NACA 0009
transient, whose forces were still drifting.

### Conclusions

1. **On the medium mesh, plain NACA 0009 is mesh-converged at this point.**
   * Cd: 0.01633 / 0.01636 / 0.01634 (coarse / medium / fine).
   * Cl: falls 0.6 % from coarse to fine.
   * The three cases repeat mesh-finalists run 20261013-045811 to all
     printed digits.

   Confidence: high.
2. **The stair1 step costs drag on every mesh:** Cd +12.8 / +13.4 / +16.2 %
   over NACA 0009, and Cl 3.0-3.8 % lower at equal aoa.
   * Its own mesh dependence is about a sixth of that penalty: from medium
     to fine, Cd +2.3 % and Cl −1.3 %.
   * So the step is worse than plain NACA 0009 on every mesh, but how much
     worse is uncertain by about 3 points.
   * The changes grow with refinement (coarse to medium +0.7 %, medium to
     fine +2.3 %). The meshes are not in the asymptotic range, so no grid
     convergence index can be given.

   Confidence: medium (steady solver only; the transient check failed).
3. **What moves with the stair1 mesh is the laminar separation ahead of the
   step, not the step's own flow.**
   * Upper-surface separation ahead of the step: x/c 0.396 / 0.408 / 0.423.
   * Reattachment behind the step: 13.0 / 13.1 / 13.2 step heights (upper)
     and 14.4 / 13.7 / 13.1 (lower).
   * Friction drag rises 3.3 % from coarse to medium and 6.6 % from medium to
     fine; pressure drag falls 1.1 % and 0.9 %.

   Confidence: medium. This is inferred from surface metrics; no field
   pictures were looked at.
4. **stair10 can't be ranked with the steady solver.**
   * On all three meshes its forces oscillate over the averaging window: Cl
     ±2.5-6.2 %, Cd ±7-16 % (standard deviation).
   * Mean Cd is −3 / 0 / −3 % against NACA 0009 on the same mesh; mean Cl is
     −3 / −4 / −9 %.
   * The fine mesh's 6 % drop in lift is the size of the oscillation, so the
     mesh effect and the unsteadiness can't be told apart.
   * The flow pattern is the same on every mesh. The flow separates at the
     first step (x/c 0.30); on the medium and fine meshes it reattaches at
     0.37. It is separated from x/c 0.50 to the trailing edge on both sides.

   Confidence: high that these numbers can't separate candidates a few
   percent apart. Whether stair10 beats NACA 0009 at equal side force
   remains open.
5. **Steady vs transient is unresolved.**
   * NACA 0009, transient against steady: Cl −7.2 %, Cd +4.3 % (pressure
     drag +6.9 %, friction +0.9 %), with separation at x/c 0.347 instead of
     0.276.
   * But the transient hadn't settled. Over the last 5 c/U its Cd still fell
     from 0.0175 to 0.0167 (1 % per c/U); its Cl stayed within 0.416-0.417
     for the last 3.
   * The stair1 transient diverged after 0.24 c/U (see Learnings).

   Confidence in any steady-transient gap: low. The lift gap looks real;
   the drag gap is overstated by the drift.

### Evidence

From `results.csv` and `report/mesh_convergence.csv`. Separation points are
on the upper surface, from `surface.csv`. sd is the standard deviation over
the averaging window.

| section | mesh | solver | cells | Cl (sd %) | Cd (sd %) | Cd pressure | Cd friction | upper sep. / reatt. (x/c) | iter. | wall [min] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0009 | coarse | steady | 45,318 | 0.4485 | 0.01633 | 0.00927 | 0.00706 | 0.269 / 0.674 | 1713 | 2 |
| 0009 | medium | steady | 90,112 | 0.4479 | 0.01636 | 0.00926 | 0.00710 | 0.276 / 0.689 | 2052 | 4 |
| 0009 | fine | steady | 180,276 | 0.4461 | 0.01634 | 0.00916 | 0.00718 | 0.285 / 0.690 | 2756 | 14 |
| 0009 | medium | transient | 90,112 | 0.4154 (0.3) | 0.01706 (1.6) | 0.00990 | 0.00716 | 0.347 / 0.695, TE 0.998 | 1872 steps | 79 |
| stair1 | coarse | steady | 61,516 | 0.4344 | 0.01842 | 0.01073 | 0.00769 | 0.396 / 0.655 | 1395 | 2 |
| stair1 | medium | steady | 120,832 | 0.4344 | 0.01856 | 0.01061 | 0.00795 | 0.408 / 0.656 | 2005 | 8 |
| stair1 | fine | steady | 240,006 | 0.4289 | 0.01898 | 0.01051 | 0.00847 | 0.422 / 0.657 | 3617 | 36 |
| stair1 | medium | transient | 120,832 | failed | | | | | | 255 |
| stair10 | coarse | steady | 255,164 | 0.4340 (5.5) | 0.01585 (16.3) | 0.00885 | 0.00705 | 0.300, TE 0.517 | 7851 | 63 |
| stair10 | medium | steady | 494,848 | 0.4315 (2.5) | 0.01635 (7.3) | 0.00924 | 0.00712 | 0.300 / 0.367, TE 0.501 | 4280 | 113 |
| stair10 | fine | steady | 971,608 | 0.4056 (6.2) | 0.01593 (11.7) | 0.00913 | 0.00678 | 0.300 / 0.367, TE 0.503 | 3567 | 226 |

The steady NACA 0009 and stair1 cases have sd ≤ 0.06 %. "TE" is where the
trailing-edge separation starts.

`mesh_convergence.csv` gives negative apparent orders for every quantity
(changes that grow, or oscillate, with refinement). Its GCI values are
therefore not meaningful, NACA 0009 included, whose changes are tiny.

Step resolution comes from `cmesh` with this study's parameters (cells
across the step height 2 h behind the face / cells on the face / cells
along the 8 h behind it):

| level | stair1 (0.95 mm) | stair10 (0.1 mm) and stair5 (0.2 mm) |
|---|---|---|
| coarse | 15 / 11 / 61 | 9 / 6 / 61 |
| medium | 21 / 15 / 84 | 12-13 / 9 / 84 |
| fine | 29 / 21 / 116 | 17-18 / 13 / 116 |

In wall units, a 0.1 mm step is 0.9-3.0 tall and a 0.2 mm step 1.7-6.0.
This uses the plain NACA 0009 medium case's upper-surface Cf at x/c 0.3-0.9
(`surface.csv`, ν = 1.137e-6 m²/s).

### Decisions

* **Start transient runs from 2000 steady iterations** (`start_iter`, the
  new default). Allrun restarts the steady solution as time 0 of the
  pimpleFoam run.
  * Cost: about 4-8 min per medium case.
  * `start_iter` is left out of the case hash, like the relaxation factors,
    so finished runs resume as before.
* **Guard against a collapsing time step.** Transient cases stop with an
  error when the time step falls below 1e-6 c/U (`runTimeControl`,
  `minTimeStep`).
* **Size the time limit for transient cases.** `resources()` now counts
  time steps: 15 c/U at maxCo 10 on the medium mesh measured 1.3 h for NACA
  0009, and is taken as about 5× that for stair1.
  * Before, a transient case got the steady limit, 5 h for stair1.
* **Run 2 repeats check (b) only.**
  * NACA 0009 stays at maxCo 10, as in this run, so its change shows the
    effect of the steady start alone.
  * stair1 runs at maxCo 5.
  * Estimated about 1.5 h and 9 h of compute. The task limit is 25 h,
    from stair1.
* **Not decided: the scope of stepped-vs-naca.** Proposed:
  * run the plain and stair1 candidates on the medium mesh with the steady
    solver (conclusions 2 and 3);
  * flag the stair5 and stair10 points, or leave them out (120 cases
    instead of 150), until a transient answer for them exists
    (conclusion 4).

### Assumptions

* A 0.1-0.2 mm step's height in wall units is taken from the plain
  section's skin friction. The steps change Cf locally, and from x/c 0.3 to
  0.6 the plain section has a laminar bubble with Cf ≈ 0. **Not verified.**
* The failed checkMesh "small determinant" check is an artefact of
  one-cell-thick 2D meshes with thin wall cells, not a defect. Every mesh
  fails it, the plain ones included: 1,774-4,966 cells on the plain meshes,
  201,534 on stair10 medium. **Not verified.**
* stair10's transient time step is near 5e-5 s, per the study description,
  so a transient stair10 case would take days. **Not verified.**
* The transient cost estimates come from this run's logs:
  * NACA 0009: 2.5 s per step, dt 6.2e-4 s at Co 10;
  * stair1: 2.2 s per step, dt 1.7e-4 s at Co 10 before it diverged.

  The stair1 and stair5/stair10 factors in `resources()` are estimates.

### Compromises

* One operating point (1 m/s, 4°). Lower speeds have longer laminar
  bubbles and may be more mesh-sensitive.
* stair5 was not checked. It has the same number of cells per step height
  as stair10, so it is assumed to behave like stair10. **Not verified.**
* stair10 was run only with the steady solver, so its averaged numbers are
  estimates.
* No field pictures (`iomcfd viz`). The flow descriptions rest on surface
  metrics.
* The failed stair1 transient was not re-run in this run.

### Learnings

* **A stair1 transient started from the uniform inflow at maxCo 10
  diverged.**
  * omega went strongly negative near the step (bounded at −2.6e7 a step
    before), and the run blew up at t = 0.019 s (0.24 c/U, step 128).
  * The adaptive time step then collapsed to 1e-67 s, and the case crawled
    for 4 h until a floating-point exception.
  * A Spot preemption had already cost 1.5 h, after which Batch restarted
    the task from scratch. In all, about 5.75 VM-hours were lost.
* **NACA 0009 started from rest needs more than 15 c/U** before its
  averaged drag settles. Lift levelled after about 12 c/U.
* **The steady solver's flags work as intended:** NACA 0009 and stair1 have
  sd ≤ 0.06 %, while stair10 is flagged unsteady on every mesh.
* **The CI image from a branch matches the local image.** It reproduces the
  local image to about 1e-12 (stepped-smoke run 20261013-185800 on GCP
  against local run 20261013-151959).
* **The steps sit inside the viscous sublayer** (0.9-6 wall units). So the
  flow at each step is a viscous corner eddy; there are no turbulent eddies
  there for a finer mesh to resolve. What the mesh has to get right is the
  separation and transition on the scale of the chord (conclusions 3 and
  4).
* **Compute.**
  * 13.4 case-hours. The job took 7.3 h, held up by the stair1 transient;
    stair10 fine took 3.8 h.
  * Four c3d-standard-16 VMs use the whole C3D quota of 64 vCPUs, so the
    stepped-smoke job waited about an hour in the queue.
* **Report.**
  * `iomcfd report` crashed on this study (the selection plot can't handle
    several meshes). The fix was ported from `main`.
  * `polar.png` joins the steady and transient points of a section into one
    line.

### Open questions and next steps

* **Run 2** (set up): the transient check from a steady start. If the
  steady and transient results differ by more than the differences between
  candidates in stepped-vs-naca (for stair1 against NACA 0009: Cd +13 %, Cl
  −3 %), its working-load points need transient runs.
* **Is stair10's oscillation physical shedding or numerical?** The stepped
  meshes reach 53-59° non-orthogonality, against 22-25° on the plain ones.
  The fields of stair10 medium (`gcp fetch --fields`, then `iomcfd viz`)
  would show where it oscillates; that is cheaper than a transient run.
* **stair5 mesh check,** if stair5 stays a candidate.
* **Highlights for run 2:** each transient case against its steady
  counterpart from this run, with the `separation` and `step` views. Look
  at where the stair1 bubble ahead of the step sits, and how long the step's
  recirculation is.
