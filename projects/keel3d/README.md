# keel3d: keel planform on a canoe body

Steady 3D RANS of the underwater boat (canoe body, keel fin and lead bulb)
at a given speed, leeway and heel. Built to answer one question first:
**is a constant-chord or a tapered keel fin better on an IOM?**

**Status: runs end to end on the xcoarse mesh (smoke, and a 10-case
leeway sweep to check the report); coarse, medium and fine meshed but not
solved. Not validated; taper-selection not run yet.**

## The question and how it is answered

foil2d picked the section: NACA 0007 at 100 mm chord
([findings](../foil2d/findings/transient-check.md)). A 2D section can't
say what the planform does: taper moves side force towards the root,
changes the induced drag, lowers the Reynolds number at the tip and changes
the fin-bulb junction. So this project builds the whole underwater boat in
3D and changes only the fin planform.

* **Equal lateral area.** Every fin has the same mean chord (100 mm) and the
  same span, so the same area. Only the taper ratio λ = tip chord / root
  chord changes. The quarter-chord line stays vertical at the same x, so
  the fin's centre of lateral resistance and the bulb stay put.
* **Same hull, same bulb, same draft** for every fin (sizes below).
* **Compared at equal side force, ranked by race time.** The sails set the
  side force, not the keel. Each planform is run over a leeway sweep (0-8°)
  and interpolated to the side forces the constant-chord keel makes at 2, 4
  and 6° (light, working, high load). At each load it has a drag and a
  leeway angle. Drag, leeway and the drag at 0° (downwind) are turned into
  % of race time lost against the best planform, as in
  [foil2d/methodology.md](../foil2d/methodology.md), steps 3-5. In 3D the
  leeway is the boat's own, so no 2D-to-3D angle conversion is needed, and
  hull side force and hull-keel interaction are included.
* **Why it could go either way.** For a wing with a mirror plane at the root
  (here the hull and waterline) and a free tip, the lowest induced drag
  comes with near-elliptic loading, which a taper of about 0.4 approaches.
  The bulb at the tip acts partly as an end plate and keeps load out at the
  tip, which can move the optimum towards constant chord. And a 57 mm tip
  (λ 0.4) runs at Re 50,000, where foil2d found laminar separation and
  shedding.

Taper ratios studied: 1.0, 0.8, 0.6, 0.4. Every commercial IOM fin with
stated dimensions is tapered, about 0.7-0.83, one older Bantock fin about
0.6 ([docs/research/iom-fins-on-the-market.md](../../docs/research/iom-fins-on-the-market.md)),
so 0.6-0.8 brackets the market and 0.4 and 1.0 are the ends.

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
| fin | NACA 0007, quarter chord vertical at x = 0.50 m, from the hull bottom to the top of the bulb; carried on into the hull and into the bulb so the junctions are real intersections | span 334.6 mm, area 0.0335 m² |
| displacement | hull + exposed fin + bulb | 3.99 kg (rule minimum 4.0 kg) |

| taper λ | root → tip chord [mm] | root / tip thickness [mm] | Re root / tip at 1 m/s | root I vs constant chord |
|---|---|---|---|---|
| 1.0 | 100 → 100 | 7.0 / 7.0 | 88k / 88k | 1.0 |
| 0.8 | 111 → 89 | 7.8 / 6.2 | 98k / 78k | 1.5 |
| 0.6 | 125 → 75 | 8.8 / 5.3 | 110k / 66k | 2.4 |
| 0.4 | 143 → 57 | 10.0 / 4.0 | 126k / 50k | 4.2 |

Root I: second moment of the root section (c·t³, solid section, same t/c),
a rough measure of how much stiffer the fin is where the bulb's moment is
largest ([docs/research/fin-stiffness.md](../../docs/research/fin-stiffness.md)).
The CFD does not use it. All four fins weigh the assumed 120 g.

Code: `geometry.hulls.CanoeSpec` / `canoe`, `geometry.appendages.FoilBulbSpec`
/ `foil_bulb` / `foil_bulb_length`, `taper_chords`, and `FinSpec` (with
`tip_extension` into the bulb). `keel_geometry()` in project.py does the
sizing and refuses a fin or bulb that breaks rule E.4.1.

## Model

* **Double body.** The waterline z = 0 is a symmetry plane that cuts the
  hull. No waves: at 1 m/s (Fn 0.32) the hull makes waves, but they hardly
  differ between keels; the fin root is 53 mm down. Use `hull` with
  `appendages` for wave drag.
* simpleFoam, kOmegaSST, Spalding wall functions, prism layers from
  snappyHexMesh, as appendage3d. **Fully turbulent.** foil2d showed that at
  these Reynolds numbers much of the fin is laminar, so friction is
  overestimated (about +25 % in 2D at small angles) and laminar separation
  is missed. Friction at equal area is nearly the same for every planform,
  so the comparison rests on the 3D effects (induced drag, tip and junction
  flows), which RANS does capture. The Reynolds-number effect of a small tip
  chord is not captured (see Next steps).
* Leeway rotates the inflow; heel rotates the boat about the x axis at the
  waterline (no re-trim, no sinkage).
* Domain: 1.5 L ahead, 3 L behind the stern, 1.5 L to each side, 1.2 L below
  the bulb (L = hull length); far boundaries freestream.

## Mesh levels

Background cell = fin mean chord (100 mm). Fin surface at level 6-7 on
`medium` (1.6-0.8 mm), bulb 5-6, hull 4-5, with boxes around the keel, the
hull and the wake (to 1 m behind the stern). `xfine` refines the fin, bulb,
near wake and boxes once more than `fine`, not the hull.

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
  cells), and the near-wake box widens for leeway on both sides. Any side
  force at 0° leeway is then the solver's, not the mesh's.
* **`mesh_shift`** moves that grid in x and y by a fraction of the finest
  fin cell, to test how sensitive the forces are to where the grid lines
  fall. On medium, a shift of 0.5 puts 4 faces over the skewness limit
  (up to 9.6) on the constant-chord fin's straight trailing edge, and the
  fin gets 10 % fewer faces (58k against 65k).

With the wake box and the aligned grid, measured at 4° leeway:

| `mesh` | cells λ 1.0 / 0.4 | fin faces λ 1.0 / 0.4 | layer coverage on the fin | use |
|---|---|---|---|---|
| xcoarse | 0.16 M (2 layers, before the changes) | 6.9k | 2 of 2 | smoke |
| coarse | not measured (0.47 M before) | | | |
| medium | 1.06 / 1.07 M | 65k / 67k | 96.8 / 95.5 % | |
| fine | 3.28 / 3.32 M | 172k / 174k | 97.8 / 97.4 % | |
| xfine | about 14 M (**estimate**; too big for 11.7 GB of local Docker memory) | | | |

Meshing takes about 3-4 minutes (medium) and 8 minutes (fine) on 8 cores.
Every level now has 3 faces over the skewness limit (5.3) on the waterline
plane at the stern tip, where the hull's pointed end meets the waterline;
they are far from the keel. Before these changes, medium had none and fine
30.

At 0° the side force should be zero: medium (before the changes) gave
0.004-0.06 N, xcoarse −0.15 to −0.2 N.

## Outputs

Per case (`results.csv`):
* `drag_N`, `side_N` (+ to port), `vertical_N`, friction and pressure drag,
  `side_drag_ratio`, `Cd`/`Cs` on the fin area;
* per part: `drag_<part>_N`, `side_<part>_N`, `drag_<part>_friction_N` for
  `hull`, `fin`, `bulb` and `keel` (fin + bulb);
* centre of lateral resistance `x_clr` and depth `z_clr` (from the moments
  about the bow at the waterline; a deeper z_clr is a longer heeling arm);
* spanwise loading: `spanload.csv` (side and drag force per metre and local
  cl, cd on the local chord; OpenFOAM `binField` on the fin's face forces),
  and `eta_cp` (spanwise centre of the strips' side force, 0 at the hull,
  1 at the top of the bulb), `cl_root`, `cl_mid`, `cl_tip`,
  `spanload_coverage` (strips / whole fin side force). About `span_bins`
  strips from the hull down; each is a whole number of fin surface cells
  wide, so every strip holds the same number of face rows (otherwise the
  load jumps by ±15 % from strip to strip on xcoarse). They stop short of
  the bulb by less than one strip (10 mm on medium);
* y+ per part, `n_cells`, and the derived sizes (`fin_root_chord`,
  `bulb_length`, `displacement_kg`, ...).

`iomcfd report`:
* `keel_forces.png`: side force and drag against leeway, drag polar;
* `planform_compare.md` / `.csv`: every planform at the reference's side
  forces (leeway, drag, drag at 0°, race-time loss ×1 / ×2 resistance slope),
  plus `polar_fits.csv`: D = D0 + k F² per planform, effective span
  efficiency e = 1 / (2π q d² k) with d the draft, side force per degree;
* `spanload.png`: local cl and normalised load along the span near the
  working load, against elliptic;
* `mesh_check.md` when a study runs cases on more than one mesh.

Study `report:` options: `compare_at` (reference design and leeway angles,
default `{fin_taper: 1.0, leeway: [2, 4, 6]}`), `vdrdv` (V·dR/dV by speed,
default the foil2d estimates 0.40 / 0.81 / 1.354 / 2.71 N at 0.5 / 0.75 / 1 /
1.5 m/s), `track_angle` (42°).

## Studies

* `smoke`: λ 0.6, xcoarse, 30 iterations, 3° leeway, 10° heel (about 30 s
  on 4 cores).
* `taper-selection`: λ 1.0, 0.8, 0.6, 0.4 × leeway 0, 2, 4, 6, 8° at
  1 m/s, upright, medium; mesh check on coarse and fine at 4° for λ 1.0 and
  0.4. 24 cases, meant for GCP.

## Limitations and next steps

* **Transition.** Correct the fully turbulent 3D section drag strip by
  strip with foil2d: for each strip in `spanload.csv`, the 2D drag difference
  between kOmegaSSTLM and kOmegaSST at the local chord's Reynolds number and
  the local cl. Needs a foil2d run of NACA 0007 at 57-143 mm chord with both
  turbulence models. Without it the tapered tips get no penalty for low-Re
  laminar separation.
* **Heel** (upwind 10-20°) and **other speeds** (0.75, 1.5 m/s) for the best
  two planforms.
* **Market-like fins**: 100 → 70 mm (λ 0.7, mean 85 mm, less area) is a
  second question (area and planform together).
* **Free surface**: one check of the best two with `hull` (VOF).
* No rudder: it sits in the keel's downwash and would shift the comparison
  slightly.
* Not validated against measurements.
