# keel3d: keel planform on a canoe body

Steady 3D RANS of the underwater boat (canoe body, keel fin and lead bulb):
drag D_h, side force S_h, vertical force F_z,h, the roll and yaw moments
M_h,dyn and N_h, the centre of lateral resistance and the fin's spanwise
loading, for a given boat speed V_b, leeway β_Y and heel φ. Symbols:
[docs/nomenclature.md](../../docs/nomenclature.md). Built to answer one
question first: **is a constant-chord or a tapered keel fin better on an
IOM?**

**Status: runs end to end on GCP; not validated.** taper-selection run
20261018-044718 (24 cases) showed that the medium mesh could not rank the
planforms ([findings](findings/taper-selection.md)). The mesh has changed
since (Mesh levels), and taper-mesh, a mesh ladder for the first two fins
to compare, is the next run.

## The question and how it is answered

foil2d picked the section: NACA 0007, at 90-100 mm chord
([findings](../foil2d/findings/transient-check.md)). A 2D section can't say
what the planform does: taper moves side force towards the root, changes
the induced drag, lowers the Reynolds number at the tip and changes the
fin-bulb junction. So this project builds the whole underwater boat in 3D
and changes only the fin planform.

* **Equal lateral area.** The fins of a study have the same mean chord
  (`fin_mean_chord`) and the same span, so the same area. Only the taper
  ratio λ = tip chord / root chord changes. The quarter-chord line stays
  vertical at the same x, so the fin's centre of lateral resistance and the
  bulb stay put.
* **Same hull, same bulb, same draft** for every fin (sizes below).
* **Compared at equal S_h, ranked by race time.** The sails set the side
  force (S_h = S_a), not the keel. Each planform is run over a leeway sweep
  and interpolated to the S_h the reference keel (constant chord) makes at a
  few leeways (2, 4, 6°: light, working, high load). At each load it has a
  drag D_h and a leeway β_Y. D_h, β_Y and the drag at β_Y = 0 (downwind)
  are turned into % of race time lost against the best planform, as in
  [foil2d/methodology.md](../foil2d/methodology.md), steps 3-5. In 3D β_Y
  is the boat's own leeway, so no 2D-to-3D angle conversion is needed, and
  the hull's side force and the hull-keel interaction are included.
* **Why it could go either way.** For a wing with a mirror plane at the root
  (here the hull and waterline) and a free tip, the lowest induced drag
  D_i comes with near-elliptic loading, which a taper of about 0.4
  approaches. The bulb at the tip acts partly as an end plate and keeps load
  out at the tip, which can move the optimum towards constant chord. And a
  short tip chord runs at a low Reynolds number, where foil2d found laminar
  separation and shedding.

**The fins.** Every commercial IOM fin with stated dimensions is tapered,
λ about 0.7-0.83 (one older Bantock fin about 0.6), with roots of at most
about 100 mm ([docs/research/iom-fins-on-the-market.md](../../docs/research/iom-fins-on-the-market.md)).

| study | mean chord | λ: root → tip chord |
|---|---|---|
| taper-selection run 1 | 100 mm | 1.0: 100 → 100; 0.8: 111 → 89; 0.6: 125 → 75; 0.4: 143 → 57 |
| taper-mesh (next) | 90 mm | 1.0: 90 → 90 (foil2d's 0007/90); 0.8: 100 → 80 |

## Geometry (defaults)

Sized from the [IOM class rules 2026](https://iomclass.org/iom-class-rules/)
(Release 2): draft 370-420 mm (C.4.1), keel 2200-2500 g excluding fasteners
(C.6.4), no keel material denser than lead, 11340 kg/m³ (E.3.1), no
transverse dimension over 20 mm except the lowest 60 mm (E.4.1), boat at
least 4000 g (C.4.2).

| part | how it is sized | result |
|---|---|---|
| bulb | lead = keel limit 2500 g − carbon fin 120 g = 2380 g, 209.9 cm³; NACA 0007 thickness revolved about the axis (diameter 7 % of the length) | 463.4 mm long, 32.4 mm diameter |
| bulb position | bottom at the 420 mm draft limit; centre of mass (38.3 % of the length from the nose) under the fin's quarter chord | axis at z = −403.8 mm, centre of mass at x = 0.50 m |
| canoe body | elliptic sections, parabolic waterline and keel line; L 0.99 m, B 0.165 m, T 0.053 m | 3.62 L, centre of buoyancy x = 0.504 m, wetted area 0.142 m² |
| fin | NACA 0007, quarter chord vertical at x = 0.50 m, from the hull bottom to the top of the bulb; carried on into the hull and into the bulb so the junctions are real intersections | span b = 334.6 mm; area 0.0335 m² (100 mm mean chord), 0.0301 m² (90 mm) |
| displacement | hull + exposed fin + bulb | 3.99 kg (100 mm mean chord), 3.96 kg (90 mm); rule minimum 4.0 kg |

| mean chord | λ | root → tip chord [mm] | root / tip thickness [mm] | Re root / tip at V_b = 1 m/s | root I vs constant chord |
|---|---|---|---|---|---|
| 100 mm | 1.0 | 100 → 100 | 7.0 / 7.0 | 88k / 88k | 1.0 |
| 100 mm | 0.8 | 111 → 89 | 7.8 / 6.2 | 98k / 78k | 1.5 |
| 100 mm | 0.6 | 125 → 75 | 8.8 / 5.3 | 110k / 66k | 2.4 |
| 100 mm | 0.4 | 143 → 57 | 10.0 / 4.0 | 126k / 50k | 4.2 |
| 90 mm | 1.0 | 90 → 90 | 6.3 / 6.3 | 79k / 79k | 1.0 |
| 90 mm | 0.8 | 100 → 80 | 7.0 / 5.6 | 88k / 70k | 1.5 |

Root I: second moment of the root section (c·t³, solid section, same t/c),
against the constant-chord fin of the same mean chord: a rough measure of
how much stiffer the fin is where the bulb's moment is largest
([docs/research/fin-stiffness.md](../../docs/research/fin-stiffness.md)).
The CFD does not use it. Every fin weighs the assumed 120 g.

Code: `geometry.hulls.CanoeSpec` / `canoe`, `geometry.appendages.FoilBulbSpec`
/ `foil_bulb` / `foil_bulb_length`, `taper_chords`, and `FinSpec` (with
`tip_extension` into the bulb). `keel_geometry()` in project.py does the
sizing and refuses a fin or bulb that breaks rule E.4.1.

## Model

* **Double body.** The waterline z = 0 is a symmetry plane that cuts the
  hull. No waves (D_r = 0): at V_b = 1 m/s (Fn 0.32) the hull makes waves,
  but they hardly differ between keels; the fin root is 53 mm down. Use
  `hull` with `appendages` for wave drag.
* simpleFoam, kOmegaSST, Spalding wall functions, prism layers from
  snappyHexMesh, as appendage3d. **Fully turbulent.** foil2d showed that at
  these Reynolds numbers much of the fin is laminar, so friction is
  overestimated (about +25 % in 2D at small angles) and laminar separation
  is missed. Friction at equal area is nearly the same for every planform,
  so the comparison rests on the 3D effects (D_i, tip and junction flows),
  which RANS does capture. The Reynolds-number effect of a short tip chord
  is not captured (see Next steps).
* Leeway β_Y turns the inflow, so forces come out along and across the
  course; heel φ turns the boat about the x axis at the waterline (no
  re-trim, no sinkage).
* Domain: 1.5 L ahead, 3 L behind the stern, 1.5 L to each side, 1.2 L below
  the bulb (L = hull length); far boundaries freestream.

## Mesh levels

Background cell = fin mean chord. Fin surface at level 6-7 on `medium`
(1.6-0.8 mm at 100 mm mean chord), bulb 5-6, hull 4-5, with boxes around
the keel, the hull and the wake (to 1 m behind the stern). `xfine` refines
the fin, bulb, near wake and boxes once more than `fine`, not the hull.

* **Near wake** (`fin_wake`, default 0.3): a box along the fin's trailing
  edge (it follows the slant of a tapered fin), from 0.1 mean chord ahead of
  the edge to `fin_wake` mean chords behind it, ±6 mm to the sides (plus the
  leeway drift over its length), at the fin's minimum surface level.
  Without it the cells behind the trailing edge grew to 6-12 mm within 5 mm
  of the edge, even on fine (taper-selection run 20261018-044718).
* **Grid aligned with the boat**: the domain ends on whole background cells
  from the bow, centre plane and waterline, so every refined cell sits the
  same way relative to the boat for any leeway or taper. Before, the domain
  width (which grows with leeway) also moved the grid sideways relative to
  the fin.
* **Mirror-image mesh when upright**: the centre plane y = 0 is then a
  plane of cell faces with the trailing edge on it, so which side the
  edge's feature refinement lands on is a tie, decided one way or the other
  in patches (99.1 % of the castellated fin faces mirrored on λ 0.4,
  medium; the same in serial and parallel). `trailingEdge.obj` adds the
  edge 1 µm either side of y = 0, so both rows are refined (100 %, +0.3 %
  cells), and the near-wake box widens for leeway on both sides. Any S_h at
  β_Y = 0 is then the solver's, not the mesh's.
* **`mesh_shift`** moves that grid in x and y by a fraction of the finest
  fin cell, to test how sensitive the forces are to where the grid lines
  fall. On medium, a shift of 0.5 broke the mirror image (by design) and
  gave the constant-chord fin 10 % fewer faces (58k against 65k).

With the wake box and the aligned grid, measured at β_Y = 4° with 100 mm
mean chord (a 90 mm fin has cells 10 % smaller, so roughly 10-15 % more
of them; **estimate**):

| `mesh` | cells λ 1.0 / 0.4 | fin faces λ 1.0 / 0.4 | layer coverage on the fin | use |
|---|---|---|---|---|
| xcoarse | 0.16 M (2 layers, before the changes) | 6.9k | 2 of 2 | smoke |
| coarse | not measured (0.47 M before) | | | |
| medium | 1.07 / 1.08 M | 65k / 67k | 96.8 / 95.5 % | |
| fine | 3.3 / 3.4 M | 172k / 175k | 97.8 / 97.5 % | |
| xfine | about 14 M (**estimate**; too big for 11.7 GB of local Docker memory) | | | |

Meshing takes about 3-4 minutes (medium) and 8 minutes (fine) on 8 cores.
Every level has 3 faces over the skewness limit (5.3) on the waterline
plane at the stern tip, where the hull's pointed end meets the waterline;
they are far from the keel.

## Outputs

Per case (`results.csv`):
* `drag_N` (D_h) and `side_N` (S_h, + to port, which is windward on port
  tack), along and across the course;
* `vertical_N` (F_z,h); `drag_friction_N` and `drag_pressure_N`, the two
  parts of D_h; `side_drag_ratio`;
* `roll_moment_Nm` (M_h,dyn, + heels to starboard) and `yaw_moment_Nm`
  (N_h), about the bow at the waterline;
* `x_clr`, the x position of the centre of lateral resistance, and `z_clr`
  its height (z_CLR, ORC's depth below the waterline, is −`z_clr`;
  M_h,dyn ≈ z_CLR · S_h, so a deeper z_CLR heels the boat more);
* `Cd`/`Cs` (C_D, C_S) on the fin's lateral area;
* per part: `drag_<part>_N`, `side_<part>_N`, `drag_<part>_friction_N` for
  `hull`, `fin`, `bulb` and `keel` (fin + bulb);
* spanwise loading: `spanload.csv` (side and drag force per metre of span
  and the local C_l, C_d on the local chord; OpenFOAM `binField` on the
  fin's face forces), and `eta_cp` (spanwise centre of the strips' side
  force, 0 at the hull, 1 at the top of the bulb), `cl_root`, `cl_mid`,
  `cl_tip`, `spanload_coverage` (strips / whole-fin side force). About
  `span_bins` strips from the hull down; each is a whole number of fin
  surface cells wide, so every strip holds the same number of face rows
  (otherwise the load jumps by ±15 % from strip to strip on xcoarse). They
  stop short of the bulb by less than one strip (10 mm on medium);
* y+ per part, `n_cells`, and the derived sizes (`fin_root_chord`,
  `bulb_length`, `displacement_kg`, ...).

While a case runs, its progress line ([docs/workflow.md](../../docs/workflow.md),
"Progress and divergence"; `iomcfd gcp progress <study>` on GCP) adds the boat's latest
`D_h` and `S_h` [N] and `D_h_change`, `S_h_change`: how far their means
over the last `conv_window` iterations moved from the window before,
relative to D_h and to max(D_h, S_h). The case stops when both are below
`conv_tol`.

`iomcfd report`:
* `keel_forces.png`: S_h and D_h against β_Y, and D_h against S_h;
* `planform_compare.md` / `.csv`: every planform at the reference's S_h
  (β_Y, D_h, D_h at β_Y = 0, race-time loss ×1 / ×2 resistance slope);
  `polar_fits.csv`: D_h = D0 + k S_h² per planform, the effective draft
  T_eff = 1 / √(π q k) (ORC's form of D_i = S_h² / (π q T_eff²)), the same
  as a span efficiency e = 1 / (2π q d² k) on the draft d, and S_h per
  degree of β_Y. The fit includes the growth of viscous drag with S_h, so
  T_eff is shorter than the induced-drag value;
* `spanload.png`: local C_l and normalised load along the span near the
  working load, against elliptic;
* `mesh_check.md` when a study runs cases on more than one mesh, and
  `shift_check.md` when it runs cases with more than one `mesh_shift`.

Study `report:` options: `compare_at` (reference design and leeway angles,
default `{fin_taper: 1.0, leeway: [2, 4, 6]}`), `vdrdv` (the resistance
slope V_b dD_h/dV_b by speed, default the foil2d estimates 0.40 / 0.81 /
1.354 / 2.71 N at 0.5 / 0.75 / 1 / 1.5 m/s), `track_angle` (42°).

## Studies

* `smoke`: λ 0.6, xcoarse, 30 iterations, β_Y 3°, φ 10° (about 30 s on
  4 cores).
* `taper-selection`: λ 1.0, 0.8, 0.6, 0.4 at 100 mm mean chord, β_Y 0, 2,
  4, 6, 8° at 1 m/s, upright, medium; mesh check on coarse and fine at 4°.
  Run 20261018-044718 (on the old mesh): no ranking, the medium mesh could
  not resolve the planform differences; taper raises the centre of lateral
  resistance on every mesh ([findings](findings/taper-selection.md)).
* `taper-mesh`: 0007/90 constant chord against 100 → 80 mm, β_Y 0, 2, 4° on
  medium and fine, 4° on xfine, and the constant-chord fin at 4° with the
  grid shifted. Picks the mesh level for the planform comparison.

## Limitations and next steps

* **Transition.** Correct the fully turbulent 3D section drag strip by
  strip with foil2d: for each strip in `spanload.csv`, the 2D drag difference
  between kOmegaSSTLM and kOmegaSST at the local chord's Reynolds number and
  the local C_l. Needs a foil2d run of NACA 0007 over the fins' chord range
  (80-100 mm for taper-mesh's fins) with both turbulence models. Without it
  the tapered tips get no penalty for low-Re laminar separation.
* **Heel φ** (upwind 10-20°) and **other speeds** (V_b 0.75, 1.5 m/s) for
  the best two planforms.
* **Market-like fins**: 100 → 70 mm (λ 0.7, mean 85 mm, less area) is a
  second question (area and planform together).
* **Free surface**: one check of the best two with `hull` (VOF).
* No rudder: it sits in the keel's downwash and would shift the comparison
  slightly.
* Not validated against measurements.
