# alt-air-mesh: findings log

Newest run first. One entry per run; results live in
`runs/alt-air-mesh/<run id>/` (not in git), so the numbers are copied here.
The study follows up [alt-air-scout](alt-air-scout.md). There, medium and
fine differed by +9 % in cd and −14 % in cl at φ 30°, 30° off the bow, and
coarse was closer to fine than medium. Symbols and the C_X / C_Y
convention are as in alt-air-scout. Project: [README](../README.md).

## Run 20261030-030100 (2026-10-30, git 2c93e9e-dirty, GCP, 6 cases)

**Setup.**

* **Condition.** The alternative hull at φ 30° static attitude (sink
  −5.40 mm, trim 0.131°), as alt-air-scout.
* **Mesh.** fine (3.1/1.6 mm) and xfine (1.6/0.8 mm), at awa 30 and 45°,
  3 m/s.
* **A repeat.** The fine awa 30° case again, with Tu 1.001 % so that it
  hashes as a new case: the same flow, on another VM.
* **Re.** Fine at 6 m/s, awa 30°.
* **Solver.** c2d-standard-16 Spot, 8 ranks; solver as the scout.

**Outcome.** 6 ok, 5 converged. xfine at awa 45° ran the 3000-iteration
limit with a slow swing. 2.1 case-hours.

### Conclusions

1. **At φ 30°, awa 30°, the steady solution falls into one of two states,
   and the mesh decides which.**
   * Coarse and fine: cd 0.52-0.54, cl −0.76 to −0.78, x_ce 0.331-0.335 m.
   * Medium and xfine: cd 0.56-0.57, cl −0.87 to −0.89, x_ce 0.301-0.306 m.

   The force histories show every mesh passing through the −0.87 state
   near iteration 250; coarse and fine then drift to −0.77 and stay there
   (window std 0.0006). It is likely a separation on the leeward side that
   steady RANS can't settle. That is inferred from the histories; no flow
   fields were looked at. Confidence: high that there are two states;
   low for the cause.
2. **The fine mesh repeats well.** Three runs of the same case on
   different VMs give cd 0.522 / 0.526 / 0.527 and cl −0.762 / −0.775 /
   −0.778: within 0.9 % and 2.0 %. Confidence: high.
3. **At awa 45° the states are closer.** fine gives 0.884 / −0.838 and
   xfine 0.888 / −0.869. xfine swings ±0.02 in cl with a period of about
   800 iterations and didn't settle by 3000. Medium (alt-air-scout) gave
   0.909 / −0.857. Confidence: medium.
4. **The fine mesh's Re effect is small.** From 3 to 6 m/s at awa 30°:
   cd −1.2 % and cl −2.6 % (0.525 → 0.519, −0.771 → −0.752, against the
   mean of the three 3 m/s runs). Confidence: medium.
5. **Either state gives the same upwind picture: C_X 0.04-0.08 against
   the VPP's 0.71.** C_Y is −0.92 to −1.05 (alt-air-scout conclusion 1).
   The two states differ by about ±4 % in cd and ±7 % in cl around their
   mean, which is small against that. Confidence: high.

### Evidence

* `results.csv` of this run and alt-air-scout's, and the
  `postProcessing/forceCoeffs` histories of the five awa 30° cases at
  3 m/s and the two at 45°, downloaded from the bucket.
* φ 30°, awa 30°, 3 m/s:

  | mesh | run | cells [M] | iterations | cd | cl | C_X | C_Y | x_ce [m] | y+ mean |
  |---|---|---|---|---|---|---|---|---|---|
  | coarse | scout | 0.15 | 467 | 0.543 | −0.776 | 0.082 | −0.944 | 0.331 | 12.4 |
  | medium | scout | 0.26 | 1311 | 0.571 | −0.871 | 0.059 | −1.040 | 0.306 | 6.9 |
  | fine | scout | 0.54 | 952 | 0.522 | −0.762 | 0.071 | −0.921 | 0.335 | 4.1 |
  | fine | this | 0.54 | 980 | 0.526 | −0.775 | 0.068 | −0.934 | 0.334 | 4.1 |
  | fine (Tu 1.001) | this | 0.54 | 1015 | 0.527 | −0.778 | 0.067 | −0.937 | 0.335 | 4.1 |
  | xfine | this | 1.63 | 1066 | 0.559 | −0.886 | 0.042 | −1.047 | 0.301 | 2.4 |

* The last 200 iterations' std: fine 0.0003-0.0006 (cd), xfine 0.0006;
  medium 0.0040 (cd) and 0.0059 (cl), a small oscillation.
* awa 45°: fine 0.884 / −0.838 (1242 iterations), xfine 0.888 / −0.869
  (3000, not converged), 0.55 / 1.74 M cells.
* Compute: fine 6.5-8.5 min, xfine 26 min (awa 30°) and 70 min (awa 45°, to
  the limit).

### Decisions

* **alt-air uses the fine mesh.**
  * Why: 0.55 M cells and 7 min a case. xfine costs 4-8 × as much and is
    in the other state, not closer to a converged answer.
  * The band of the two states is recorded in alt-air's description.
* **xfine checks in alt-air at φ 0 and 60°, awa 30 and 90°,** to see
  whether the two states show elsewhere.

### Assumptions

* As alt-air-scout. snappyHexMesh isn't bit-identical across VMs; that is
  the basis of the repeat (conclusion 2). **Not verified** in the logs.

### Compromises

* **Steady RANS.** A transient (URANS or DES) run at awa 30°, φ 30° would
  show whether the two states are one unsteady flow. It wasn't run.
* **No flow fields fetched.** The cause in conclusion 1 is inferred.

### Learnings

* **A mesh study that reverses (coarse closer to fine than medium) points
  to a flow with more than one solution, not to a bad level.** Look at
  the force histories before refining further.
* **Re-running a case with a parameter nudged too small to matter (Tu
  1 → 1.001 %) gets a new hash, and so a cheap repeatability check.**

### Open questions and next steps

* With fields: fetch `--fields` for the fine and xfine awa 30° cases and
  look at the surface pressure on the leeward topsides (windage viz
  `hull_cp_leeward`) to locate the separation.
* A transient run at that point, if the VPP turns out sensitive to the
  upwind side force.
