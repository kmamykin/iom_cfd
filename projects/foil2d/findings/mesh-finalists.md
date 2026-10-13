# mesh-finalists: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/mesh-finalists/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. This study checks the mesh for the
fin-profile-selection finalists ([fin-profile-selection.md](fin-profile-selection.md)).

## Run 20261013-045811 (2026-10-13, git 19e49d8, GCP, 12 cases)

**Setup.** NACA 0008 and 0009 at 80 mm chord, 1 m/s (Re 70,400), Tu 1 %,
aoa 4 and 6°, kOmegaSSTLM, steady. Three meshes: coarse (45,318 cells),
medium (90,112) and fine (180,276). Image `iom-cfd:19e49d8`, 1 ×
c3d-standard-16 Spot.
Why: fin-profile-selection run 20261012-175146 found the two within 0-3 %
at the working-load side force, about the coarse-medium change; medium-fine
was unknown.

**Outcome.** 12 ok, none unsteady.

### Conclusions

1. **The medium mesh resolves the 0008/0009 difference.**
   * At the Cl 0009 makes at 4°, 0008 has 0.9 % (coarse), 1.6 % (medium)
     and 1.9 % (fine) less drag than 0009.
   * At equal aoa the difference is −4.0 / −4.2 / −4.1 % at 4° and
     +8.8 / +7.8 / +6.7 % at 6° (coarse / medium / fine).

   Confidence: high, for this speed, chord and Tu.
2. **Medium is close to mesh-independent for forces and bubble position.**
   * Medium to fine: Cd −0.1 % (0008) and −0.2 % (0009) at 4°, −1.7 % and
     −0.8 % at 6°; Cl within 0.4 %.
   * Bubble ends move by ≤ 0.016 c from medium to fine, and by ≤ 0.03 c from
     coarse to medium.
   * At 6° Cd converges monotonically but slowly, so the GCI extrapolation
     is not meaningful there (apparent order 0.15-0.27).

### Evidence

From `results.csv` and `report/mesh_convergence.csv`; reversed flow is where
Cf < 0 on the suction side in `surface.csv`.

| foil | aoa | mesh | Cl | Cd | reversed flow (x/c) | iterations | wall [min] |
|---|---|---|---|---|---|---|---|
| 0008 | 4 | coarse | 0.4427 | 0.01568 | 0.216-0.658 | 1597 | 8.3 |
| 0008 | 4 | medium | 0.4427 | 0.01568 | 0.245-0.684 | 2000 | 28.3 |
| 0008 | 4 | fine | 0.4415 | 0.01567 | 0.261-0.693 | 2798 | 59.8 |
| 0008 | 6 | coarse | 0.5790 | 0.02745 | 0.010-0.138 | 1709 | 7.3 |
| 0008 | 6 | medium | 0.5804 | 0.02695 | 0.010-0.138 | 1805 | 24.3 |
| 0008 | 6 | fine | 0.5815 | 0.02648 | 0.010-0.132 | 2336 | 52.3 |
| 0009 | 4 | coarse | 0.4485 | 0.01633 | 0.275-0.674 | 1654 | 8.3 |
| 0009 | 4 | medium | 0.4479 | 0.01636 | 0.278-0.684 | 2016 | 27.5 |
| 0009 | 4 | fine | 0.4461 | 0.01634 | 0.288-0.688 | 2775 | 53.3 |
| 0009 | 6 | coarse | 0.5869 | 0.02523 | 0.016-0.157 | 1266 | 6.3 |
| 0009 | 6 | medium | 0.5879 | 0.02501 | 0.016-0.166 | 1978 | 24.5 |
| 0009 | 6 | fine | 0.5883 | 0.02481 | 0.017-0.166 | 2812 | 50.8 |

The medium cases repeat fin-profile-selection run 20261012-175146 (image
19a3176) to 3e-5 in Cd and 3e-6 in Cl.

### Decisions

* Keep the medium mesh for foil2d selection studies at Re ≈ 70k.

### Assumptions

* That the mesh behaves the same at other speeds and chords, and at
  Tu 0.1 % (**not verified**).

### Compromises

* One speed, two angles, Tu 1 % only; Tu 0.1 % has longer, oscillating
  bubbles (fin-profile-selection run 20261013-045759) and may be more
  mesh-sensitive.

### Learnings

* Fine cases take about 2× the medium wall time (1.4× iterations); 5.9
  case-hours for the 12 cases.
* The solver is deterministic across image rebuilds that don't change it.

### Open questions and next steps

* A Tu 0.1 % mesh check at the same points, if a decision ends up resting on
  Tu 0.1 % differences of a few %.
