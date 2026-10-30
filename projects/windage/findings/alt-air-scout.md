# alt-air-scout: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/alt-air-scout/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study is a set of quick experiments that
settle the parameters of [alt-air](../studies/alt-air.yaml). That study
covers the air part of the alternative hull (`iom-alternative`, private
STL): its topsides at each heel's static attitude in a uniform apparent
wind, for the VPP's windage. The mesh question it left open went to
[alt-air-mesh](alt-air-mesh.md). The water part is in
[keel3d/alt-water-scout](../../keel3d/findings/alt-water-scout.md).
Project: [README](../README.md).

Angles: `awa` is the apparent wind angle from the centreline, from port
(β_AW − β_Y in docs/nomenclature.md). D_a and L_a are along and across
the apparent wind; `cd` and `cl` are on the VPP's projected area normal to
the wind (`A_proj_m2`, `vpp/components/windage.py`). C_X and C_Y below are
the same force in boat axes (+x aft, +y port) on that area:
C_X = cd cos awa + cl sin awa, C_Y = −cd sin awa + cl cos awa. The VPP's
model is drag only, C_D 0.816, so it has C_X = 0.816 cos awa and
C_Y = −0.816 sin awa.

## Run 20261030-023242 (2026-10-30, git 2c93e9e-dirty, GCP, 29 cases)

**Setup.**

* **Hull.** `file:private/iom-alternative.stl` at the static attitude from
  `vpp hydro iom-alternative --zip` (M_ext 0, Z_ext 0):
  * φ 0°: sink −2.15 mm, trim −0.001°;
  * φ 30°: sink −5.40 mm, trim 0.131°.

  The topsides are cut at z = 0 and mirrored below a slip floor
  (`geometry/waterline.split`), so there is no wind gradient and no
  boundary layer on the water.
* **Domain.** 2 L upwind, 4 L downwind, 2 L to the sides and 1.5 L high,
  with a background cell of L/10. Surface cells:
  * coarse 12.5/6.3 mm;
  * medium 6.3/3.1 mm;
  * fine 3.1/1.6 mm.
* **E4, mesh.** φ 0 and 30° × awa 30 and 90° × coarse, medium and fine,
  at 3 m/s.
* **E5, Re.** φ 30° × awa 30, 90 and 150° × V_AW 1.5, 3 and 6 m/s, on the
  medium mesh.
* **E6, angles.** φ 30°, awa 0-180° every 15°, 3 m/s, medium mesh.
* **Solver.** simpleFoam kOmegaSST with Spalding wall functions, fully
  turbulent, Tu 1 %; drift-checked convergence. c2d-standard-16 Spot,
  8 ranks.
* **History.** This is the first run of a new project (`projects/windage`).

**Outcome.** 29 ok, 28 converged.
* φ 30°, awa 120°, medium ran the 3000-iteration limit without settling
  and reports the window mean.
* φ 30°, awa 45°, medium also reached 3000 but passed the drift check.

1.7 case-hours.

### Conclusions

1. **Upwind, the topsides make mostly side force, and their aft force is
   about a tenth of the VPP's drag-only model.**
   * At awa 30°, C_X is 0.06-0.08 at φ 30° and 0.08-0.09 upright (all
     meshes and speeds), against the VPP's 0.71.
   * C_Y is −0.92 to −1.05 at φ 30° and −0.71 to −0.75 upright, against
     the VPP's −0.41.
   * The heeled or upright topsides act like a low plate at an angle: the
     pressure force is nearly normal to the hull's side.
   * Over φ 30°, awa 15-150° (medium, 3 m/s), |C_X| ≤ 0.14, against the
     VPP's 0-0.79.
   * Downwind, the forward push at awa 180° is C_X −0.37 against the
     VPP's −0.82.

   Confidence: medium for the hull alone in a uniform wind; low as a VPP
   input until the sails' effect on the flow over the deck is considered
   (see Compromises).
2. **cd climbs fast from the bow to about 1 by 60°, and cl peaks at
   about −0.87 near 30-45°.**
   * At φ 30°, medium, cd is 0.25 / 0.26 / 0.57 / 0.91 / 1.01 at
     0 / 15 / 30 / 45 / 60°, stays 0.92-0.97 to 120° and falls to 0.46 at
     150° and 0.37 at 180°.
   * cl is 0.06 / −0.43 / −0.87 / −0.86 / −0.57 over 0-60°, then +0.75 at
     135°.
   * The projected area runs 0.015 m² (bow-on) to 0.092 m² (beam-on).

   Confidence: medium (medium mesh; see 3).
3. **The medium mesh is within 1 % of fine on cd and 3.5 % on cl in 3 of
   4 places, but not at φ 30°, awa 30°: +9.4 % in cd and −14.3 % in cl.**
   There, coarse is closer to fine (+4.0 % / −1.8 %) than medium.
   alt-air-mesh found two steady states at that point: coarse and fine
   in one, medium and xfine in the other. So this isn't a discretisation
   error that refinement removes. Confidence: high (repeated, see
   alt-air-mesh).
4. **The coefficients change little with wind speed.** On the medium mesh
   from 1.5 to 6 m/s:
   * cd falls 3.8 % at awa 30° and 3.3 % at 90°;
   * at 150° it isn't monotone (0.481 / 0.458 / 0.472);
   * cl is constant at 90° (0.046) and changes by 4.3 % at 30°.

   alt-air-mesh's fine pair (3 → 6 m/s, awa 30°) gives −1.2 % in cd and
   −2.6 % in cl. One V_AW is enough. Confidence: medium (one heel).
5. **The topsides also make an upward force about as large as the drag.**
   At 3 m/s on the fine mesh:
   * upright, F_z is 0.29 N at awa 30° (D_a 0.105 N) and 0.44 N at 90°
     (D_a 0.368 N);
   * at φ 30° it is 0.32 / 0.27 N.

   That is suction over the deck. It is small against the boat's weight,
   and the VPP's windage has no vertical force. Confidence: medium.
6. **At heel, the height of the side force's line of action is well below
   the area's centroid.** z_ce = −K / F_y is 0.011-0.021 m at φ 30°
   (awa 30-150°), against the centroid at 0.046-0.048 m. Upright it is
   0.037-0.041 m against 0.043-0.044 m.

   K includes the vertical force's lateral lever, as z_clr does for the
   keel (ht35-keel), so the heeling moment should be taken from K, not
   from F_y times the centroid's height. Confidence: medium.

### Evidence

* `results.csv` of the run; C_X and C_Y computed from cd, cl and awa as in
  the intro.
* E4, mesh at 3 m/s (coarse / medium / fine):

  | φ, awa | cd | cl | cells [M] |
  |---|---|---|---|
  | 0, 30 | 0.455 / 0.437 / 0.433 | −0.603 / −0.571 / −0.589 | 0.15 / 0.27 / 0.58 |
  | 0, 90 | 0.862 / 0.840 / 0.834 | 0.090 / 0.083 / 0.086 | 0.10 / 0.25 / 0.54 |
  | 30, 30 | 0.543 / 0.571 / 0.522 | −0.776 / −0.871 / −0.762 | 0.15 / 0.26 / 0.54 |
  | 30, 90 | 0.980 / 0.970 / 0.970 | 0.049 / 0.046 / 0.046 | 0.10 / 0.21 / 0.52 |

* E6 at φ 30°, medium, 3 m/s:

  | awa | 0 | 15 | 30 | 45 | 60 | 75 | 90 | 105 | 120 | 135 | 150 | 165 | 180 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | A_proj [m²] | 0.015 | 0.030 | 0.050 | 0.068 | 0.082 | 0.090 | 0.092 | 0.089 | 0.081 | 0.067 | 0.049 | 0.028 | 0.015 |
  | cd | 0.245 | 0.255 | 0.571 | 0.909 | 1.006 | 0.949 | 0.970 | 0.917 | 0.955* | 0.787 | 0.458 | 0.315 | 0.367 |
  | cl | 0.060 | −0.427 | −0.871 | −0.857 | −0.569 | −0.204 | 0.046 | 0.310 | 0.596* | 0.750 | 0.577 | 0.217 | −0.245 |
  | C_X | 0.245 | 0.136 | 0.059 | 0.037 | 0.010 | 0.048 | 0.046 | 0.062 | 0.038* | −0.027 | −0.108 | −0.248 | −0.367 |
  | C_X VPP | 0.816 | 0.788 | 0.707 | 0.577 | 0.408 | 0.211 | 0 | −0.211 | −0.408 | −0.577 | −0.707 | −0.788 | −0.816 |
  | C_Y | 0.060 | −0.478 | −1.040 | −1.249 | −1.156 | −0.969 | −0.970 | −0.966 | −1.125* | −1.087 | −0.728 | −0.291 | 0.245 |
  | C_Y VPP | 0 | −0.211 | −0.408 | −0.577 | −0.707 | −0.788 | −0.816 | −0.788 | −0.707 | −0.577 | −0.408 | −0.211 | 0 |

  \* not converged (3000 iterations, window mean).
* E5, φ 30°, medium (V_AW 1.5 / 3 / 6 m/s): cd 0.578 / 0.571 / 0.556
  (awa 30°), 0.977 / 0.970 / 0.945 (90°), 0.481 / 0.458 / 0.472 (150°);
  cl −0.882 / −0.871 / −0.844, 0.046 / 0.046 / 0.046, 0.613 / 0.577 /
  0.622.
* y+ (mean, max): fine 2.9-4.1 (max 30-37) at 3 m/s; medium 3.1-4.0 at
  1.5 m/s and 8.9-12.7 at 6 m/s.
* Compute: median 2.8 min a case, max 8.8; 0.10-0.58 M cells
  (`report/summary.md`).

### Decisions

* **The mesh question went to [alt-air-mesh](alt-air-mesh.md)** (run
  20261030-030100): fine against xfine, a repeat, and fine at 6 m/s.
  * Outcome: alt-air uses the fine mesh.
* **One wind speed, 4 m/s** (conclusion 4).
* **Angles every 10° to 60°, then every 15° to 180°**, where cd and cl
  change fastest (conclusion 2).
* **[alt-air](../studies/alt-air.yaml), run 20261030-155540,** was
  submitted after the user confirmed:
  * content: 7 heels at static attitude (0-60°) × 15 angles at 4 m/s on
    the fine mesh, plus xfine at φ 0 and 60°, awa 30 and 90°;
  * 109 cases on c2d-standard-16, 4 at a time;
  * estimate: about 15 case-hours, about $3.

### Assumptions

* **The STL's z = 0 is the design waterline** (docs/hulls.md). **Not
  verified.**
* **The VPP applies windage at the projected area's centroid with the
  wind gradient** (`vpp/components/windage.py`). That is why the CFD's
  wind is uniform.
* **4 m/s for alt-air** is an estimate of the upwind apparent wind at the
  venue's modal 3 m/s true wind (V_b about 1 m/s, β_TW about 40°). **Not
  verified** against a VPP run; with conclusion 4 it matters little.

### Compromises

* **The hull alone, with no rig or sails.** Upwind, the sails' upwash and
  downwash change the local wind angle over the deck. That can move the
  C_X / C_Y split of conclusion 1, which is the main limit on using it in
  the VPP.
* **Uniform wind over a slip water surface.** There is no gradient and no
  water boundary layer, and no waves on the topsides.
* **Steady RANS, fully turbulent.** At awa 30-45° heeled, the flow has two
  steady states (alt-air-mesh). One case at 120° didn't settle.
* **E5 and E6 are at φ 30° only, on the medium mesh.** The fine-mesh angle
  set is alt-air's.

### Learnings

* **A heeled hull's topsides behave like a low-aspect wing.** Their force
  is mostly normal to the centreline from 30 to 135°. A drag-only C_D on
  the projected area puts the force in the wrong direction upwind.
* **Medium is "closer" to fine than coarse almost everywhere, but not at
  the bistable point.** Check a mesh against two finer levels before
  trusting a single comparison.
* **Compute.** Air cases are cheap: 3-8 min on c2d-standard-16, so the
  whole air table costs less than one water heel.

### Open questions and next steps

* **VPP.** A windage model with lift: export cd, cl, K and N per φ × awa
  from alt-air, or a `table:` for the windage component. Then compare the
  race time against the drag-only C_D 0.816.
* **Sails' influence on the windage.** A combined hull + sails case at one
  upwind point would show how much the sails change conclusion 1.
* **Wind gradient.** A sheared-inflow check at one upwind and one downwind
  angle.
* Highlights in alt-air: upwind (awa 30° across the heels) and deck (awa
  90° at φ 30-60°, where the leeward deck edge goes under between 40 and
  45°).
