# taper-mesh: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/taper-mesh/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study picks the mesh level for the keel
planform comparison, on the two fins to compare first: NACA 0007 at a
constant 90 mm chord (λ 1.0, foil2d's 0007/90) and NACA 0007 tapered from
100 mm at the root to 80 mm at the tip (λ 0.8), both 90 mm mean chord, so
the same span and area, on the same canoe body and 2380 g NACA 0007 bulb.
Pass test (study description): the λ 1.0 − 0.8 race-time difference at the
working load moves by < 0.1 % from medium to fine, and their 4° S_h and D_h
differences move by < 1 % from fine to xfine. Symbols:
[docs/nomenclature.md](../../../docs/nomenclature.md). Project and
geometry: [README](../README.md); the first, coarser look at the question:
[taper-selection](taper-selection.md).

## Run 20261019-213145 (2026-10-19, git d8bdfe3, GCP, 16 cases; xfine still running)

**Setup.**
* λ 1.0 (90 → 90 mm) and λ 0.8 (100 → 80 mm), span 334.6 mm; β_Y 0, 2,
  4°; V_b 1 m/s, upright (φ 0); medium and fine; xfine at 4° for both
  fins; λ 1.0 at 4° on medium and fine with the background grid shifted by
  half the finest fin cell in x and y (`mesh_shift 0.5`).
* The mesh since taper-selection: a near-wake box along the trailing edge
  (0.3 mean chords behind it), the grid aligned with the boat, mirror-image
  meshes when upright (`trailingEdge.obj` 1 µm either side of y = 0), layer
  addition limited to 20 medial-axis iterations, and Allrun stops on
  inverted cells after meshing. Medium 1.13-1.21 M cells, fine 3.59-3.84 M.
* simpleFoam, kOmegaSST with wall functions (fully turbulent), Tu 0.5 %,
  5 prism layers. Image `iom-cfd:d8bdfe3`, c3d-standard-16 Spot, 8 ranks.
* Replaces run 20261018-234733 (git 58ba0c7), which lost λ 1.0 on fine at
  0, 2, 4° and on xfine at 4° to inverted cells in the near-wake box above
  the bulb (made by the layer stage; fixed by the medial-axis limit) and was
  cancelled.
* **One case re-run.** λ 0.8, 0°, fine stopped at 402 iterations with D_h
  still climbing (Learnings). It was re-run locally (Docker, local
  `iom-cfd:latest` of 2026-10-11 with the code of 163bed5 mounted, which
  has the drift check) into this run, and its export replaced the cloud
  case in the bucket.

**Outcome.** 14 of 16 ok, all converged: 11 stopped on simpleFoam's
`residualControl`, 2 on the windowed means (λ 1.0, 0° medium at 608
iterations; λ 1.0, 2° fine at 808), and the re-run on `residualControl` at
674. The two xfine cases were at iteration 520 of 3000 after 5.5 h when this
was written; the entry is to be completed when they finish.

### Conclusions

1. **On fine the two fins are a tie: the constant-chord fin loses 0.07 % of
   race time at the working load and 0.01 % at the light load.** At equal
   S_h (6.12 N) the tapered fin sails at 3.93° instead of 4.00° with
   0.0008 N less D_h; its D_h at β_Y = 0 is 0.0005 N higher (0.7009 against
   0.7004 N). Confidence: low until xfine; medium to fine moved the
   difference more than its size (conclusion 2).
2. **The medium mesh can't rank these fins: the first pass test fails.**
   The constant-chord fin's loss at the working load moves from 0.39 % on
   medium to 0.07 % on fine, 0.32 percentage points against the 0.1
   allowed (light load: 0.46 → 0.01 %). Nearly all of it is D_h at
   β_Y = 0, the downwind half: medium gives the tapered fin 0.0060 N less
   (fin 0.0036, hull 0.0024), fine 0.0005 N more. Two fins of the same
   section and area, fully turbulent, should have nearly the same drag at
   zero side force, so fine is the plausible one. Confidence: high that
   medium is not enough; whether fine is enough waits for xfine.
3. **The tapered fin makes 1.8 % more S_h per degree of leeway, on both
   meshes**: 1.531 against 1.504 N/° on medium, 1.558 against 1.530 on fine
   (fit to 4°); +1.8 / +1.9 % at 4°, +2.5 / +1.8 % at 2°. From medium to
   fine, S_h at 4° rose 1.6 % (λ 1.0) and 1.7 % (λ 0.8): the constant-chord
   fin's 8 % jump of taper-selection is gone with the new mesh, and the
   ladder now treats both fins alike (the highlight's question). Confidence
   medium: shifting the grid moves the constant-chord fin's S_h by 4-7 %
   (conclusion 5).
4. **Taper raises the centre of lateral resistance by about 4 mm**:
   z_clr −0.180 against −0.184 m at 2° and 4° on both meshes (4 of 4
   comparisons, 3.7-4.1 mm). The heeling arm M_h,dyn / S_h is 2 % shorter.
   taper-selection found the same direction at 100 mm mean chord.
   Confidence high; the effect is small.
5. **Where the grid lines fall moves the constant-chord fin's side force
   more than the planform does.** Shifting the grid by half the finest fin
   cell in x and y changed S_h at 4° by −4.3 % on medium and +6.5 % on
   fine, and D_h by +2.0 / +2.2 %. The spanwise loading kept its shape (on
   fine the local C_l rose about 6 % at every station), so the fin's whole
   circulation changed, not a local feature. Likely cause, **not verified**:
   the shift takes the trailing edge off the y = 0 plane of cell faces, the
   snapped edge is no longer symmetric and acts as a small camber; the
   aligned mirror-image mesh gives both fins a symmetric edge. A shifted
   case at β_Y = 0 would show it as S_h ≠ 0. Confidence: high in the
   numbers, low in the cause.
6. **Absolute D_h is not mesh-converged**: from medium to fine it fell 5.5 %
   at 4° and 2-3 % at 0°, mostly fin friction (−11 % at 4°; mean fin y+
   5.0 → 3.2, inside the buffer-layer blend of the wall functions) and the
   bulb (−5 to −8 %); the hull moved < 0.6 %. The study uses differences
   between fins at equal S_h, not absolute drag. Confidence high.

### Evidence

From `report/planform_compare.csv` (equal S_h = the constant-chord fin's
at 2° and 4°; race-time loss with V_b dD_h/dV_b ×1 / ×2):

| mesh | λ | load | S_h [N] | β_Y [°] | D_h [N] | D_h at β_Y = 0 [N] | loss ×1 / ×2 [%] |
|---|---|---|---|---|---|---|---|
| medium | 0.8 | light | 3.064 | 1.95 | 0.7517 | 0.7158 | best |
| medium | 1.0 | light | 3.064 | 2.00 | 0.7570 | 0.7218 | 0.46 / 0.25 |
| medium | 0.8 | working | 6.020 | 3.93 | 0.8760 | 0.7158 | best |
| medium | 1.0 | working | 6.020 | 4.00 | 0.8791 | 0.7218 | 0.39 / 0.22 |
| fine | 0.8 | light | 3.073 | 1.96 | 0.7307 | 0.7009 | best |
| fine | 1.0 | light | 3.073 | 2.00 | 0.7308 | 0.7004 | 0.01 / 0.02 |
| fine | 0.8 | working | 6.119 | 3.93 | 0.8288 | 0.7009 | best |
| fine | 1.0 | working | 6.119 | 4.00 | 0.8296 | 0.7004 | 0.07 / 0.06 |

λ 0.8 − λ 1.0 by part (`results.csv`; D in N, S_h in %, z_clr in mm):

| mesh | β_Y | ΔD_h | ΔD fin | ΔD hull | ΔD bulb | ΔS_h | Δz_clr |
|---|---|---|---|---|---|---|---|
| medium | 0° | −0.0060 | −0.0036 | −0.0024 | 0.0000 | | |
| medium | 2° | −0.0033 | −0.0015 | −0.0020 | +0.0002 | +2.5 % | +3.7 |
| medium | 4° | +0.0037 | +0.0047 | 0.0000 | −0.0011 | +1.8 % | +3.9 |
| fine | 0° | +0.0005 | 0.0000 | +0.0005 | 0.0000 | | |
| fine | 2° | +0.0011 | +0.0006 | +0.0010 | −0.0006 | +1.8 % | +4.1 |
| fine | 4° | +0.0045 | +0.0035 | +0.0021 | −0.0011 | +1.9 % | +3.7 |

Mesh ladder and grid shift at 4°, λ 1.0 (`report/mesh_check.md`,
`report/shift_check.md`):

| mesh | mesh_shift | cells | D_h [N] | S_h [N] | D fin [N] | eta_cp |
|---|---|---|---|---|---|---|
| medium | 0 | 1.21 M | 0.8791 | 6.020 | 0.3695 | 0.444 |
| medium | 0.5 | 1.13 M | 0.8963 (+2.0 %) | 5.760 (−4.3 %) | 0.3900 | 0.442 |
| fine | 0 | 3.84 M | 0.8296 | 6.119 | 0.3283 | 0.455 |
| fine | 0.5 | 3.71 M | 0.8479 (+2.2 %) | 6.515 (+6.5 %) | 0.3373 | 0.456 |

λ 0.8 at 4°: medium 0.8827 N / 6.126 N, fine 0.8341 / 6.232 (−5.5 % /
+1.7 %).

The falsely converged case (λ 0.8, 0°, fine), D_h of the whole boat:

| | iterations | D_h [N] | bulb friction [N] |
|---|---|---|---|
| cloud, mean of the last window (what it reported) | 402 | 0.6898 | 0.0709 |
| cloud, last iteration | 402 | 0.6987 | 0.0787 |
| re-run, mean of the last window | 674 | 0.7009 | 0.0805 |
| λ 1.0, 0°, fine, for comparison | 669 | 0.7004 | 0.0803 |

With the reported 0.6898 N the tapered fin looked 0.43-0.44 % faster on fine;
the re-run made it a tie.

### Decisions

* keel3d now stops a case only when D_h and S_h are also flat within the
  last window (`settled(..., drift=True)`, commit 163bed5). Replayed on
  this run's 14 force histories it changes only the false stop.
* The planform comparison runs on fine at least; medium is out. Whether
  fine is enough waits for xfine.
* The aligned mirror-image grid stays the reference; `mesh_shift` results
  are an uncertainty estimate, not an equal alternative (conclusion 5).

### Assumptions

* Race time as in foil2d's methodology: resistance slope V_b dD_h/dV_b =
  1.354 N at 1 m/s (foil2d's estimate, **not verified** in 3D), 42° track,
  half upwind, half downwind with D_h at β_Y = 0.
* Fully turbulent friction; double body (no waves); upright, 1 m/s only.
* Both fins weigh the assumed 120 g (**not verified** for either).
* The local re-run stands in for a cloud case: same OpenFOAM v2512, an
  older image with today's code mounted. Its mesh has 3 596 949 cells; the
  cloud's had 3 597 082 (snappyHexMesh is not bit-identical across
  machines). **Not verified** beyond that.

### Compromises

* xfine only at 4°, the grid shift only for λ 1.0 at 4°: the shift
  sensitivity of the tapered fin is unknown.
* Three leeways: the interpolation to equal S_h runs on three points.
* One of 14 cases came from a local machine.

### Learnings

* **A windowed-mean convergence test can stop a case during its start-up
  climb.** If the earlier window holds the start-up transient, its mean can
  match the next window's by chance while the forces still rise: here D_h
  rose 4 % across the last window and the reported mean was 0.011 N low.
  It sat on the downwind drag, which decided the ranking. The same test
  (without the drift check) is in appendage3d, hull, sails, fullboat,
  bulb2d and steady foil2d. keel3d runs made before 163bed5, including the
  bulb studies, may hold such cases.
* The fine meshes are valid for both fins at 0-4° with the medial-axis
  limit; both xfine meshes passed the mesh check too.
* Compute: medium 16-22 min, fine 83-104 min per case (8 ranks,
  c3d-standard-16 Spot), 12.3 case-hours for 14 cases on GCP; the re-run
  took 1.8 h locally. xfine runs at about 35 s per iteration (fine about
  7 s), so a case needs roughly 8-12 h if it converges in 800-1200
  iterations (**estimate**).

### Open questions and next steps

1. **xfine at 4°** (running): the second pass test, the 4° S_h and D_h
   differences moving by < 1 % from fine to xfine. The xfine cases run
   with the old convergence test, so their force histories need a check
   for a false stop.
2. **Mesh camber check**: λ 1.0 at β_Y = 0 on medium and fine with
   `mesh_shift 0.5`; S_h ≠ 0 would confirm the cause in conclusion 5. A
   shift in x only (keeping the mirror image) would separate the edge's
   position along the chord from its symmetry. That needs a new
   parameter. Cheap: 2-4 cases.
3. If fine passes: the planform comparison on fine, both fins at β_Y 0-6°,
   then 0.75 and 1.5 m/s and heel.
4. Check taper-selection run 20261018-044718 and the bulb studies' keel3d
   runs for false stops (replay their force histories).

Highlights for the next run: the shifted 0° case against the aligned one
(`compare: mesh_shift`, `why`: does the shifted grid give a symmetric fin
side force, i.e. mesh camber?), and λ 1.0 against 0.8 at 4° on xfine
(`compare: fin_taper`, `why`: does the 1.8 % S_h difference survive?).
