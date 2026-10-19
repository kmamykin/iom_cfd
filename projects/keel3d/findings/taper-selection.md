# taper-selection: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/taper-selection/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study asks whether a constant-chord or a
tapered keel fin is better on an IOM: NACA 0007 fins of equal area (mean
chord 100 mm, the foil2d recommendation, [transient-check](../../foil2d/findings/transient-check.md))
on the same canoe body and 2380 g bulb, compared at equal side force and
ranked by race time ([foil2d/methodology.md](../../foil2d/methodology.md)).
Project and geometry: [README](../README.md).

## Run 20261018-044718 (2026-10-18, git 36630b4, GCP, 24 cases)

**Setup.**
* Taper ratio λ (tip / root chord) 1.0, 0.8, 0.6, 0.4 (root → tip 100 → 100,
  111 → 89, 125 → 75, 143 → 57 mm), quarter-chord line vertical at
  x = 0.50 m; leeway 0, 2, 4, 6, 8°; 1 m/s, upright.
* Hull, bulb, draft and fin area the same for every case (README, Geometry).
* Double body (waterline = symmetry plane), simpleFoam, kOmegaSST with
  wall functions (fully turbulent), Tu 0.5 %, 5 prism layers.
* Medium mesh for the sweep (0.91-1.00 M cells); mesh check at 4° for λ 1.0
  and 0.4 on coarse (0.47-0.50 M) and fine (2.89-2.91 M).
* Image `iom-cfd:36630b4`, c3d-standard-16 Spot, 8 MPI ranks per case.
* First run of the study and of the project.

**Outcome.** 22 ok, 2 not converged: λ 0.8 and 1.0 at 8° reached the 3000
iteration limit (forces averaged over the last 200 iterations). No failures.

### Conclusions

1. **The medium mesh cannot rank the planforms: the differences between
   them are smaller than the change from medium to fine, and the fine mesh
   reverses the medium ranking at 4°.**
   * Medium, at equal side force: λ 0.4 best, then 0.6, 0.8, 1.0, at every
     load and with either reference keel (λ 1.0 or 0.6). λ 1.0 loses 0.78 %
     of race time at the light load and 0.96-1.17 % at the working load (×1
     resistance slope).
   * Medium to fine at 4°: side force +1.2 % for λ 0.4 but +8.1 % for λ 1.0;
     total drag −5.9 % and −4.4 %; fin drag −11.4 % and −10.3 %.
   * Fine, at 4°: λ 1.0 makes 3.7 % more side force than λ 0.4 for 1.6 % more
     drag. Moved to λ 0.4's side force along its own medium-mesh slope, its
     drag is 0.4 % higher to 2.6 % lower than λ 0.4's (depending on the slope
     used) and it needs 0.16° less leeway: 0.0 to 1.0 % of race time
     *better* than λ 0.4 (upwind only; **estimate**).

   Confidence: high that medium cannot rank them; low on any ranking.
2. **The constant-chord fin is the mesh-sensitive one: on medium it makes
   too little side force, most of all at 6°.**
   * λ 1.0 at 4°: 6.79 / 6.55 / 7.08 N on coarse / medium / fine (not
     monotonic). λ 0.4: 6.53 / 6.74 / 6.82 N (monotonic).
   * On medium λ 1.0 already makes 2.8 % less side force than λ 0.4 at 2°.
     At 6° it makes 8.44 N where the three tapered fins make 9.72-9.84 N;
     its local cl is about 11 % below λ 0.8's all along the span. It
     converged steadily (side force 8.43-8.44 N over its last 300
     iterations).
   * The snapped trailing edge of that case is within 0.2 mm of the design
     section at 25, 50 and 75 % span, so it is not a geometry error. Two
     possible causes, **not tested**: the near wake behind the trailing
     edge is coarse (cells grow to the keel-box size, 12.5 mm on medium,
     within about 10 mm of the trailing edge), and the vertical leading and
     trailing edges of the λ 1.0 fin lie at the same place relative to the
     background grid all along the span, so a snapping or wake-resolution
     error does not average out as on a slanted edge.

   Confidence: high that it is a mesh effect; low on the cause.
3. **Taper moves the side force up and inboard, the same on every mesh.**
   * Depth of the centre of lateral resistance at 4°: −0.170 m (λ 0.4),
     −0.175, −0.180, −0.183 m (λ 1.0). λ 0.4 and 1.0 move by ≤ 1 mm between
     coarse, medium and fine.
   * Spanwise centre of the fin's side force (0 = hull, 1 = top of the bulb):
     0.42 (λ 0.4) to 0.45 (λ 1.0), the same on medium and fine to 0.001.
   * The hull carries more of the side force with a tapered fin and the bulb
     less: hull 0.96 N for λ 0.4 against 0.85-0.91 N for λ 1.0, bulb 0.18 N
     against 0.21-0.23 N (4°, all meshes).
   * So a tapered keel's side force acts 13 mm higher: with a sail force
     roughly 0.6 m above the waterline (**estimate**, not computed here) the
     heeling moment at equal side force is about 2 % lower for λ 0.4 than
     for λ 1.0.

   Confidence: high for the load positions (mesh-independent here); medium
   for the heeling-moment estimate.
4. **λ 0.4 loads its sections evenly; the constant-chord fin loads its root.**
   * Local cl at 4° (medium): λ 0.4 0.31-0.34 along the whole span; λ 1.0
     0.38 at the root falling to 0.24 next to the bulb.
   * No fin unloads at the bulb the way a free tip would: next to the bulb
     the load per metre is 0.6-0.7 of the span mean (elliptic: 0). The bulb
     works as a partial end plate.

   Confidence: high for the shapes; the levels carry the medium-mesh error
   of conclusion 2.
5. **From 4° to 6° the drag grows mostly as pressure drag, with the suction
   side close to trailing-edge separation; the high-load comparison is
   unreliable.**
   * λ 0.6: pressure drag 0.12 / 0.17 / 0.34 / 0.79 / 1.72 N at 0 / 2 / 4 /
     6 / 8°, while friction drag falls from 0.63 to 0.51 N.
   * At 6° the wall y+ on the suction side over the aft 30 % of the chord is
     1.3-2 against 4.5-5 on the pressure side (λ 1.0 and 0.8, mid-span): low
     wall shear ahead of the trailing edge.
   * Over 0-4° every planform has the same drag growth: D = D0 + k F² with
     k 0.0039-0.0040 /N (±1.2 %), 2.2 times the ideal induced drag of a 0.42 m
     half-span (effective span efficiency 0.45-0.46). The 0-8° fits in the
     report (e 0.18) are dominated by the separating 6-8° points.
   * The high-load rows of the comparison (λ 1.0 losing 4-11 %) rest on λ 1.0's
     6° outlier and its unconverged 8° point.

   Confidence: medium. Fully turbulent RANS with wall functions; the real
   fin is partly laminar at Re 50,000-126,000 (foil2d).
6. **At 0° (downwind) the tapered fins have slightly less drag on medium.**
   * Total 0.7528 N (λ 0.4), 0.7582, 0.7621, 0.7630 N (λ 1.0): −1.3 % for
     λ 0.4, all of it on the fin (0.302 against 0.313 N; friction 0.226
     against 0.232 N).
   * Not checked on another mesh, and smaller than the 10-11 % medium-to-fine
     change of fin drag at 4°.

   Confidence: low.

### Evidence

From `results.csv` and `report/planform_compare.md`, `report/mesh_check.md`;
the extra comparisons recomputed with `Keel3D.compare_at_equal_force`.

Medium mesh, total side force and drag [N] (hull + fin + bulb):

| λ | 0° | 2° | 4° | 6° | 8° |
|---|---|---|---|---|---|
| 0.4 | 0.02 / 0.7528 | 3.427 / 0.7937 | 6.743 / 0.9337 | 9.836 / 1.3337 | 11.72 / 2.233 |
| 0.6 | 0.01 / 0.7582 | 3.407 / 0.7950 | 6.727 / 0.9356 | 9.744 / 1.3344 | 12.15 / 2.237 |
| 0.8 | 0.00 / 0.7621 | 3.367 / 0.7976 | 6.671 / 0.9347 | 9.724 / 1.3506 | 12.20 / 2.222 (nc) |
| 1.0 | 0.06 / 0.7630 | 3.330 / 0.8009 | 6.547 / 0.9333 | 8.441 / 1.2792 | 12.22 / 2.255 (nc) |

nc: not converged (3000 iterations).

Race time lost against the best, medium, % (×1 / ×2 resistance slope);
leeway [°] and drag [N] at the load's side force:

| reference keel | load (side force) | λ 0.4 | λ 0.6 | λ 0.8 | λ 1.0 |
|---|---|---|---|---|---|
| λ 1.0 | light (3.33 N) | best | 0.28 / 0.14 | 0.57 / 0.30 | 0.78 / 0.41 |
| λ 1.0 | working (6.55 N) | best (3.88°, 0.9202 N) | 0.31 / 0.16 | 0.59 / 0.31 | 0.96 / 0.53 (4.00°, 0.9333 N) |
| λ 0.6 | light (3.41 N) | best | 0.27 / 0.14 | 0.57 / 0.30 | 0.78 / 0.41 |
| λ 0.6 | working (6.73 N) | best (3.99°, 0.9326 N) | 0.32 / 0.16 | 0.61 / 0.32 | 1.17 / 0.65 (4.16°, 0.9505 N) |
| λ 1.0 | high (8.44 N) | best | 0.87 / 0.47 | 1.51 / 0.80 | 8.01 / 4.39 (λ 1.0's 6° outlier) |

Mesh check at 4°:

| λ | mesh | cells | side [N] | drag [N] | fin drag [N] | z_clr [m] | spanwise centre |
|---|---|---|---|---|---|---|---|
| 0.4 | coarse | 470k | 6.535 | 0.9908 | 0.4882 | −0.1691 | 0.416 |
| 0.4 | medium | 937k | 6.743 | 0.9337 | 0.4219 | −0.1701 | 0.4225 |
| 0.4 | fine | 2.91 M | 6.822 | 0.8782 | 0.3739 | −0.1701 | 0.4225 |
| 1.0 | coarse | 498k | 6.789 | 1.0038 | 0.4903 | −0.1840 | 0.448 |
| 1.0 | medium | 930k | 6.547 | 0.9333 | 0.4222 | −0.1832 | 0.4524 |
| 1.0 | fine | 2.89 M | 7.076 | 0.8923 | 0.3786 | −0.1830 | 0.4519 |

Fine-mesh estimate at equal side force (conclusion 1): λ 1.0's fine point
moved by −0.254 N of side force along slope dD/dF = 0.041 N/N (its medium
2-4° secant) or 0.144 N/N (2kF of the 0-8° polar fit), and dF/dβ = 1.61 N/°
(medium, 2-4°).

### Decisions

* **No planform ranking from this run.** The medium-mesh ranking (λ 0.4
  best by about 1 % at the working load) is not reported as a result.
* **Before another sweep, fix the mesh.** Add refinement in the fin's near
  wake and find the mesh level where the λ 1.0 − λ 0.4 difference stops
  moving (next steps). A sweep on fine alone would cost about 18 case-hours
  with no evidence that fine is converged either.
* **Drop 8° leeway.** It is past the working range (12 N, twice the working
  load), separated and does not converge in 3000 iterations. Fit drag polars
  over 0-4° (or up to the highest attached point), not 0-8°.
* Keep the working-load comparison as the main one; treat the high load as
  unreliable until the 6° flow is resolved.

### Assumptions

* Hull: the generic canoe body of the README (not a measured IOM hull);
  bulb 2380 g (keel limit 2500 g minus a 120 g fin, user's figure), fin
  quarter chord and bulb centre of mass at x = 0.50 m.
* Race-time inputs as foil2d: V·dR/dV = 1.354 N at 1 m/s, track 42° to the
  wind, equal time upwind and downwind (methodology.md; **not verified**).
* Sail force height for the heeling-moment estimate: about 0.6 m above the
  waterline (**estimate**, **not verified**).
* Double body, no waves; upright; fully turbulent (README, Model).

### Compromises

* One speed (1 m/s), upright, Tu 0.5 %.
* Mesh check at one leeway (4°) and two tapers only, so the fine-mesh
  comparison at equal side force uses medium-mesh slopes.
* Steady RANS through 6-8°, where the suction side approaches separation.
* No flow pictures: the fields of λ 1.0 and 0.8 at 6° were fetched, but the
  local Docker daemon stopped responding, so `iomcfd viz` was not run.

### Learnings

* The pipeline works on GCP: 24 of 24 cases. Medium cases at 0-6° converge
  in 434-696 iterations (median 14.9 min on 8 ranks); at 8°, 1064 and 1925
  iterations, or not within 3000. Fine: 637-691 iterations, 63-69 min;
  coarse 7 min. 10.6 case-hours in all.
* The job took 10.7 h of wall time because two other jobs held 36 of the
  project's 64 vCPUs (global quota), so it ran one VM at a time.
* Spanwise strips one whole fin cell wide give smooth loading; at 2-8° they
  cover 96.7-98.5 % of the fin's side force (the last 10 mm at the bulb is
  outside them; at 0° the ratio of two near-zero forces means nothing).
* Load positions (z_clr, spanwise centre) converge on coarse already;
  forces don't. A quantity that converges early is not evidence that the
  forces have.
* At 0° the medium mesh is symmetric to 0.06 N of side force (xcoarse:
  −0.2 N).

### Open questions and next steps

1. **Run 2 (proposed): a mesh ladder with near-wake refinement.**
   * Code: a refinement box behind the fin's trailing edge (about half a
     chord long, over the span, at the fin's surface level), an `xfine`
     level (fin surface 8-9) and a background-grid shift parameter to test
     the alignment idea of conclusion 2.
   * Cases: λ 1.0 and 0.4 at 2° and 4° on medium, fine and xfine with the
     wake box (12), plus λ 1.0 at 4° on medium and fine with the grid
     shifted by half a fin cell (2). About 25 case-hours, most of it xfine
     (**estimate**: 8-10 M cells, 4-5 h per case on 8 ranks).
   * Pass criterion: the λ 1.0 − λ 0.4 difference in race time at the
     working load changes by less than 0.3 % between the last two levels.
2. **Run 3**: the four tapers at 0, 2, 3, 4, 5, 6° on the level run 2 picks.
3. Then, as in the README: heel 15° for the best two, 0.75 and 1.5 m/s,
   and the laminar (foil2d) correction of the section drag strip by strip,
   which would penalise the 57 mm tip of λ 0.4.
4. Highlights for run 2: λ 1.0 against 0.4 at 4° on each mesh (why does
   λ 1.0's side force jump by 8 % from medium to fine?), with the pressure
   on the fin and the near wake at mid-span.
