# alt-air: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/alt-air/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study is the alternative hull's windage for
the VPP: its topsides at each heel's static attitude in a uniform apparent
wind, 0-180° off the bow, exported as `boats/tables/windage-alt.csv` for
iom-alternative (`.windage.WindageTable`). Its parameters were settled by
[alt-air-scout](alt-air-scout.md) and [alt-air-mesh](alt-air-mesh.md).
Symbols and the C_X / C_Y convention are as in alt-air-scout: `awa` is from
the centreline (β_AW − β_Y), and C_X (+ aft) and C_Y (+ to port, windward)
are on the projected area A_proj. The VPP's drag-only C_D 0.816 has
C_X = 0.816 cos awa and C_Y = −0.816 sin awa. Project: [README](../README.md).

## Run 20261030-155540 (2026-10-30, git 2c93e9e-dirty, GCP, 109 cases)

**Setup.**

* **Hull.** `file:private/iom-alternative.stl` at the static attitude of
  φ 0, 10, 20, 30, 40, 50 and 60° (`vpp hydro iom-alternative --zip`,
  M_ext 0, Z_ext 0): sink −2.15 to −14.73 mm, trim −0.001 to 0.225°.
* **Sweep.** × awa 0, 10, 20, 30, 40, 50, 60, 75, 90, 105, 120, 135, 150,
  165 and 180°, at V_AW 4 m/s, on the fine mesh (surface cells 3.1/1.6 mm,
  0.44-0.63 M cells): 105 cases.
* **Checks.** xfine at φ 0 and 60°, awa 30 and 90° (4 cases).
* **Solver.** As the scout: simpleFoam kOmegaSST with Spalding wall
  functions, fully turbulent, Tu 1 %, a slip floor at the water, uniform
  wind. c2d-standard-16 Spot, 8 ranks, 4 at a time.
* **Against the scout:** the fine mesh (not medium), 4 m/s (not 3), every
  heel (not φ 0 and 30° only), and 10° steps to 60°.

**Outcome.**

* 103 ok and 6 not converged (3000 iterations, window mean reported):
  * φ 0° at awa 120, 150, 165 and 180°;
  * φ 50°, awa 50°;
  * the xfine check at φ 60°, awa 30°.
* Three more ran to 3000 iterations but passed the window test: awa 165° at
  φ 10, 20 and 60°.
* 17.4 case-hours; median 7.5 min a case on fine.

### Conclusions

1. **Upwind, the topsides make almost no drag along the boat at any heel:
   C_X is −0.04 to +0.08 at awa 30-60°, against the drag-only model's
   0.41-0.71.**
   * At φ 50-60° it turns slightly forward at awa 50-60° (−0.01 to
     −0.04), so the topsides drive a little there.
   * The side force is larger than the drag-only model's: C_Y is −0.72 to
     −0.93 at awa 30° (VPP −0.41) and −0.92 to −1.29 at 50° (VPP −0.63).
   * This holds across all 7 heels.
   * Confidence: high for the hull alone in a uniform wind; low as the
     whole answer upwind (no sails over the deck, see Compromises).
2. **Heel makes the topsides a stronger wing, up to about 30-40°.**
   * The peak cd is 0.83 / 0.90 / 0.98 / 1.02 / 1.00 / 0.98 / 0.90 at
     φ 0 to 60°. The peak is at awa 90° for φ 0-10° and at 60° from 20° on.
   * The most negative cl is −0.63 at φ 0-10° and −0.79 to −0.86 at
     φ 20-60°, always near awa 30-40°.
   * The projected area beam-on grows from 0.080 to 0.099 m² as the deck
     turns to the wind.

   Confidence: high (smooth across the 7 heels).
3. **Downwind the topsides push forward less than the drag-only model
   says: C_X −0.34 to −0.36 at awa 180°, against −0.82.** At 150° it is
   −0.10 to −0.11 (VPP −0.71). The φ 0° cases at 120-180° are the
   unconverged ones: separated, unsteady flow behind a square-on hull.
   Confidence: medium (4 of the 5 φ 0° points from 120° on haven't
   converged).
4. **The topsides lift: the vertical force is 1.7-2.8 × the drag at awa
   30° and 0.5-1.2 × at 90°.** That is suction over the deck. At 4 m/s it
   is 0.44-0.79 N at those angles, 1-2 % of the boat's weight. Confidence: medium.
5. **At heel, the side force's line of action can't be read as a height.**
   z_ce = −K / F_y falls from 0.041 m (φ 0°) to −0.001 m (φ 60°) at awa
   30°, while the area's centroid rises from 0.044 to 0.051 m. K includes
   the vertical force's lateral lever, so the heeling moment must come from
   K itself, which is how the table carries it. Confidence: high.
6. **The fine mesh is good to 3.3 % in cd and 2.8 % in cl where xfine
   checked it** (φ 0 and 60°, awa 30 and 90°; fine was the higher cd in
   all 4). alt-air-mesh's two states at φ 30°, awa 30° are not seen at
   φ 0 or 60°: fine and xfine agree there. At φ 30°, awa 30° this run's
   fine case (cd 0.520, cl −0.758) is in the state the scout's fine cases
   were in (0.522-0.527, −0.762 to −0.778). Confidence: medium (4 checks;
   the bistable point itself isn't re-checked here).
7. **In the VPP, the CFD windage table makes iom-alternative 1.70 %
   faster round the course** (weighted, venue winds; 445.8 → 438.2 s,
   6.8 boat lengths).
   * Upwind VMG rises 2.2-3.7 % at TWS 1.5-5 m/s and 11.6 % at 8 m/s.
   * Downwind VMG falls 0.1-0.2 %.
   * At TWS 3 m/s, β_TW 45°: the windage's drag along the course goes from
     0.189 to 0.014 N, its side force from 0.105 to 0.229 N, and it gains
     0.289 N of lift; V_b +2.0 %, heel 32.2 → 32.8°, leeway 1.64 → 1.70°.
   * Confidence: medium for the direction; low for the size, which rests
     on conclusion 1's caveat.

### Evidence

* `results.csv` of the run; C_X = cd cos awa + cl sin awa,
  C_Y = −cd sin awa + cl cos awa.
* C_X (+ aft) on A_proj, fine, 4 m/s, by φ:

  | awa | VPP | 0° | 10° | 20° | 30° | 40° | 50° | 60° |
  |---|---|---|---|---|---|---|---|---|
  | 0 | 0.816 | 0.232 | 0.219 | 0.223 | 0.223 | 0.222 | 0.220 | 0.221 |
  | 20 | 0.767 | 0.114 | 0.103 | 0.093 | 0.086 | 0.083 | 0.092 | 0.094 |
  | 30 | 0.707 | 0.079 | 0.077 | 0.063 | 0.071 | 0.070 | 0.054 | 0.049 |
  | 40 | 0.625 | 0.067 | 0.073 | 0.058 | 0.047 | 0.035 | 0.015 | 0.010 |
  | 50 | 0.525 | 0.025 | 0.039 | 0.013 | 0.016 | 0.011 | −0.012 | −0.018 |
  | 60 | 0.408 | 0.019 | 0.026 | 0.018 | 0.001 | −0.014 | −0.042 | −0.039 |
  | 90 | 0 | 0.087 | 0.063 | 0.057 | 0.046 | 0.036 | 0.028 | 0.020 |
  | 120 | −0.408 | 0.058* | 0.079 | 0.079 | 0.038 | 0.033 | 0.025 | 0.019 |
  | 150 | −0.707 | −0.103* | −0.103 | −0.108 | −0.105 | −0.106 | −0.108 | −0.111 |
  | 180 | −0.816 | −0.342* | −0.342 | −0.348 | −0.359 | −0.364 | −0.362 | −0.353 |

  \* not converged.
* C_Y (+ to windward) at awa 30 / 50 / 90°: φ 0° −0.720 / −0.961 /
  −0.826; φ 30° −0.917 / −1.290 / −0.963; φ 60° −0.878 / −1.133 / −0.753.
  VPP: −0.408 / −0.625 / −0.816.
* cd and cl (fine, 4 m/s):

  | awa | cd φ 0° | 30° | 60° | cl φ 0° | 30° | 60° |
  |---|---|---|---|---|---|---|
  | 0 | 0.232 | 0.223 | 0.221 | 0.001 | 0.056 | 0.085 |
  | 30 | 0.429 | 0.520 | 0.481 | −0.584 | −0.758 | −0.736 |
  | 40 | 0.614 | 0.756 | 0.682 | −0.628 | −0.827 | −0.797 |
  | 60 | 0.819 | 1.021 | 0.904 | −0.451 | −0.589 | −0.568 |
  | 90 | 0.826 | 0.963 | 0.753 | 0.087 | 0.046 | 0.020 |
  | 135 | 0.624 | 0.708 | 0.639 | 0.594 | 0.661 | 0.574 |
  | 180 | 0.342 | 0.359 | 0.353 | −0.012 | −0.238 | −0.219 |

* xfine against fine: φ 0°, awa 30° cd −2.8 % / cl −1.4 %; φ 60°, 30° −1.7 /
  −1.0 % (xfine not converged); φ 0°, 90° −1.9 / +0.8 %; φ 60°, 90°
  −3.3 / +2.8 %.
* Against the scout at φ 30° (medium, 3 m/s): within 0.2-3.7 % in cd at
  awa 60-180° except 135° (−10.1 %); awa 0° −8.8 %, 30° −8.9 %. Mesh and
  speed both changed; at 30° the medium case was in the other state
  (alt-air-mesh).
* The VPP: `vpp compare iom-alternative --set-b
  'components.windage.forces={class: .windage.WindageTable, args: {table:
  tables/windage-alt.csv}}'` (A: ProjectedArea, C_D 0.816):

  | TWS m/s | VMG up A → B | VMG down A → B | race Δ |
  |---|---|---|---|
  | 1.5 | 0.587 → 0.606 | 0.550 → 0.550 | −1.40 % |
  | 3.0 | 0.895 → 0.915 | 1.068 → 1.068 | −1.06 % |
  | 5.0 | 0.959 → 0.995 | 1.543 → 1.541 | −1.98 % |
  | 8.0 | 0.841 → 0.939 | 2.793 → 2.788 | −7.18 % |
  | weighted | | | **−1.70 %** |

### Decisions

* **The table:** `vpp export-table windage alt-air@20261030-155540
  --select mesh=fine --out boats/tables/windage-alt.csv`, 105 rows (7 heels
  × 15 angles). The 5 not-converged fine cases have `ext` 1, so a VPP point
  nearest them is flagged.
* **iom-alternative's windage** is now `.windage.WindageTable` with that
  table, in place of `ProjectedArea` (C_D 0.816); the boat file's comment
  records the switch and its −1.70 %.

### Assumptions

* **The STL's z = 0 is the design waterline** (docs/hulls.md). **Not
  verified.**
* **Each heel's static attitude** (M_ext 0, Z_ext 0) from the boat file's
  mass budget. The VPP warns if the boat comes to float otherwise.
* **One wind speed, 4 m/s.** The Re effect was 1-4 % (alt-air-scout,
  alt-air-mesh). 4 m/s is about the upwind apparent wind at the venue's
  modal 3 m/s; **not verified** against a VPP run.

### Compromises

* **No rig or sails.** Upwind, the jib and main's upwash and downwash turn
  the local wind over the deck, which moves the C_X / C_Y split of
  conclusion 1. The −1.70 % is the hull's topsides in a free stream.
* **A uniform wind over a slip floor.** The VPP takes q at the projected
  area's centroid height with its own gradient; there is no water boundary
  layer and there are no waves on the topsides.
* **Steady RANS.**
  * φ 0° downwind (120-180°) didn't converge: the hull's wake is unsteady
    there, and the window means are what the table holds.
  * alt-air-mesh's two-state band (about ±4 % in cd, ±7 % in cl at φ 30°,
    awa 30-45°) applies here too.
* **Fully turbulent.** The topsides of an IOM at 4 m/s (Re_L about 2.7e5)
  would have laminar regions.

### Learnings

* **The drag-only windage model is the wrong shape, not just the wrong
  size.** It puts the force along the wind, where the CFD puts it across
  the hull. The race-time effect is largest in strong wind, where heel and
  apparent wind are highest.
* **The heeling moment needs K from the CFD.** A centre-of-effort height
  goes below the water at 60° of heel because of the vertical force's
  lever.
* **Compute.** 17.4 case-hours on c2d-standard-16; the 105 fine cases took
  a median of 7.5 min. The whole table costs about as much as one water
  heel.

### Open questions and next steps

* **A hull + sails case at one upwind point** (β_AW about 30°, φ 30°): how
  much do the sails change the topsides' C_X and C_Y, and so the −1.70 %?
* **A wind gradient:** a sheared inflow at awa 30 and 150°.
* **The downwind φ 0° cases:** a transient run at awa 165-180° for the
  mean force, if the downwind race time turns out sensitive to it (it
  moved 0.1-0.2 % here).
* Highlights to look at with fields (`gcp fetch --fields`, `iomcfd viz`):
  * the deck at φ 50-60°, awa 50-60°, where C_X turns forward;
  * φ 0°, awa 180°, unsteady.
