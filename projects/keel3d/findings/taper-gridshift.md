# taper-gridshift: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/taper-gridshift/<run id>/` (not in git), so the numbers that support
a conclusion are copied here. The study asks why shifting the background
grid by half the finest fin cell moved the constant-chord fin's side force
by 4-7 % in [taper-mesh](taper-mesh.md) (conclusion 6 there), more than the
two fins differ. Symbols: [docs/nomenclature.md](../../../docs/nomenclature.md);
project and mesh: [README](../README.md).

## Run 20261020-183155 (2026-10-20, git 6a01dcb, GCP, 8 cases)

**Setup.**
* NACA 0007, 90 mm mean chord: constant chord (λ 1.0) and 100 → 80 mm
  (λ 0.8), on the canoe body and 2380 g NACA 0007 bulb; 1 m/s, upright.
* `mesh_shift 0.5` moves the background grid by half the finest fin cell:
  0.18 mm on fine (cell 0.35 mm), 0.35 mm on medium; in x and y, or with
  `mesh_shift_only` (new in 6a01dcb) in x or y alone. A shift in x keeps
  the upright mesh a mirror image of itself; any shift in y doesn't.
* Cases, fine unless noted: λ 1.0 at β_Y 0° shifted in x and y (fine and
  medium); λ 1.0 at 4° unshifted, shifted in x and y, in x only, in y
  only; λ 0.8 at 4° unshifted and shifted in x and y.
* simpleFoam, kOmegaSST, wall functions, as taper-mesh; image
  `iom-cfd:6a01dcb` (with the drift-checked convergence test),
  c3d-standard-16 Spot, 8 ranks.

**Outcome.** 8 of 8 ok, all converged (643-717 iterations), 11.3
case-hours.

### Conclusions

1. **A grid shifted across the centre plane gives the fin a false camber.**
   At β_Y = 0 the constant-chord fin makes S_h = +0.23 N on fine and
   +0.39 N on medium, where the aligned mirror-image mesh gives at most
   0.003 N. That is the side force of about 0.15° (fine) and 0.26°
   (medium) of leeway (1.53 and 1.50 N/°, taper-mesh). Confidence high.
2. **It is the shift in y that does it.** At 4° on fine: x only
   +0.5 % S_h, +0.8 % D_h; y only +8.2 %, +3.0 %; both +6.3 %, +2.1 %.
   This confirms taper-mesh's hypothesis: off the y = 0 plane of cell
   faces the snapped trailing edge is no longer symmetric. Confidence high.
3. **The tapered fin hardly feels the shift**: +1.1 % S_h and +0.6 % D_h
   with x and y, against +6.3 % and +2.1 % for the constant-chord fin.
   Likely reason, **not verified**: a tapered fin's trailing edge slants
   across the grid in x, so how it snaps changes along the span and
   averages out; the constant-chord fin's edge sits at one x, so the whole
   edge snaps the same way. Confidence high in the numbers, medium in the
   reason.
4. **The aligned mirror-image mesh is the right reference and treats both
   fins alike.** It has no false camber (S_h ≈ 0 at 0°), and the shift that
   keeps it a mirror image moves the constant-chord fin's S_h by 0.5 %. So
   the 2 % S_h difference between the fins in taper-mesh and taper-compare
   is not a mesh-camber artefact. What remains is an alignment uncertainty
   of about 0.5 % in S_h and 0.8 % in D_h for the constant-chord fin (one
   x shift; the tapered fin's not measured). Confidence medium.
5. **The shift's effect is not a constant offset.** On fine it adds 0.23 N
   at 0° and 0.38 N at 4°. On medium it adds 0.39 N at 0° but took 0.26 N
   away at 4° (taper-mesh run 20261019-213145). A false camber alone would
   add roughly the same at every leeway. Something else changes with the
   shifted grid at leeway on medium. **Not explained.**
6. **Runs repeat to about 0.2 %.** The unshifted 4° cases repeat
   taper-mesh's: S_h 6.130 against 6.119 N (λ 1.0) and 6.225 against
   6.232 N (λ 0.8), D_h within 0.05 %. snappyHexMesh is not bit-identical
   from run to run (cell counts differ by 7-470 between the two runs'
   matching cases). Confidence high.

### Evidence

`report/shift_check.md`, 4°, fine (in brackets: change from the unshifted
case of the same fin):

| λ | shift | cells | D_h [N] | S_h [N] | D fin [N] | eta_cp |
|---|---|---|---|---|---|---|
| 1.0 | none | 3.84 M | 0.8300 | 6.130 | 0.3286 | 0.4553 |
| 1.0 | 0.5 x | 3.86 M | 0.8364 (+0.8 %) | 6.163 (+0.5 %) | 0.3339 | 0.4555 |
| 1.0 | 0.5 y | 3.77 M | 0.8548 (+3.0 %) | 6.634 (+8.2 %) | 0.3435 | 0.4573 |
| 1.0 | 0.5 x and y | 3.71 M | 0.8478 (+2.1 %) | 6.513 (+6.3 %) | 0.3373 | 0.4559 |
| 0.8 | none | 3.84 M | 0.8338 | 6.225 | 0.3317 | 0.4466 |
| 0.8 | 0.5 x and y | 3.76 M | 0.8392 (+0.6 %) | 6.291 (+1.1 %) | 0.3319 | 0.4467 |

At β_Y = 0, λ 1.0, shifted in x and y (`results.csv`; aligned values from
taper-mesh run 20261019-213145):

| mesh | S_h shifted [N] | of which fin / hull / bulb [N] | S_h aligned [N] | D_h shifted / aligned [N] |
|---|---|---|---|---|
| medium | +0.390 | 0.330 / 0.048 / 0.012 | +0.002 | 0.7320 / 0.7218 |
| fine | +0.232 | 0.202 / 0.025 / 0.006 | −0.003 | 0.7029 / 0.7004 |

### Decisions

* keel3d comparisons use the aligned grid (`mesh_shift 0`), which keeps
  upright meshes mirror images. A shifted case is never compared with an
  unshifted one.
* To estimate how sensitive a result is to where the grid lines fall,
  shift in x only (`mesh_shift_only: x`). A shift in y measures the false
  camber, not the alignment.

### Assumptions

* One shift fraction (0.5); the sensitivity may not be largest there.
* Fully turbulent friction, double body, 1 m/s, upright (as taper-mesh).

### Compromises

* The x-only and y-only shifts only for the constant-chord fin at 4°; one
  medium case.

### Learnings

* A thin symmetric foil whose trailing edge lies along a line of cells is
  sensitive to which side of the edge the cells fall: here 8 % of S_h from
  a 0.18 mm shift. A mirror-image mesh removes the false camber.
* Compute: 86-97 min per fine case, 22 min for the medium one; 11.3
  case-hours.

### Open questions and next steps

1. Why does the shifted grid lower S_h at 4° on medium but raise it at 0°
   (conclusion 5)? Low priority while comparisons use the aligned grid.
2. The tapered fin's x-only sensitivity, if a later decision rests on
   differences under 1 %.
3. Heeled cases are not mirror images, so the false camber may come back
   at heel. Run the heeled comparison with a y-shift check.
