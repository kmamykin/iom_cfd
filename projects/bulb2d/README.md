# bulb2d: the keel bulb alone, axisymmetric

Steady RANS of a body of revolution at zero incidence, on an axisymmetric
(wedge) mesh, with Langtry-Menter transition. It answers the bulb questions
where the fin doesn't matter:
* how much of the bulb's drag the boundary layer decides at IOM Reynolds
  numbers;
* where laminar separation sits on the tail;
* how fineness, the position of the largest diameter and the tail shape
  change that, at a fixed lead mass.

Why it exists: [docs/research/bulb-design.md](../../docs/research/bulb-design.md)
(Track B). A bulb's length Reynolds number at 0.5-1.5 m/s is 1.4-6 × 10⁵.
There the bulb's drag depends mostly on what its boundary layer does: by
the usual correlations anywhere from about 37 to over 160 mN at 1 m/s for
the same bulb (**estimate**, in the research note). keel3d is fully
turbulent, so it can't rank bulb shapes by drag. This project can, once it
is validated. A 2D case is cheap enough for Tu sweeps and mesh studies.

**Status: runs end to end; validation against Dress (1988) under way
([validation-dress](studies/validation-dress.yaml)).**

## Model

* **Axisymmetric.** The meridian plane (x along the axis, r up) is meshed
  and turned into a 5° wedge (`wedge`). Forces from OpenFOAM are the
  wedge's share. The project scales them to the whole body.
* **Mesh.** foil2d's structured C-grid generator (`geometry/cmesh.py`)
  with the profile r(x) as the upper half of a symmetric section. Only the
  upper half of the C is kept: ahead of the nose and behind a pointed tail
  its centre line is the axis. A blunt base (Dress's body) gets a second
  block between the axis and the wake line from the base's edge. Grid lines
  leave the wall along the normal; the first cell is set for y+ ≈ 0.5
  (`yplus`). Code: `geometry/axisym.py`.
* **Turbulence.** kOmegaSSTLM with decay control (freestream k and ω held,
  so Tu at the body is the Tu set), as foil2d. `turbulence: kOmegaSST` is
  the fully turbulent bracket.
* **No incidence, no fin, no free surface.** The bulb is about 10 diameters
  deep, so waves don't matter (research note, physics point 8). Incidence,
  the fin junction and the end-plate effect are keel3d's (Track A).
* **Steady only.** A case whose drag still swings by more than 1 % over the
  last averaging window is flagged `unsteady`; a transient solver is not
  wired in yet (foil2d has one).

## Bodies

`body`:
* `naca`: a NACA 4-digit thickness distribution revolved: diameter =
  length / `fineness`, largest at 0.3 L, round nose, pointed tail. keel3d's
  bulbs are this family: NACA 0011 = fineness 9.09 (the bulb studies, the
  default here), NACA 0007 = 14.3 (keel3d's default).
* `bulb`: appendage3d's family: elliptic nose to the largest diameter at
  `max_at`, then r ∝ 1 − u^`tail_exp` to a pointed tail.
* `file:<name>.csv`: x, r columns in `geometry/bodies/`, any unit, nose
  first. `dress-laminar-body.csv` is Dress's validation body (12 in, L/D
  4.5, largest diameter at 0.56 L, blunt base 0.3 of it).

Size: `mass` of lead (kg, at `lead_density`) sets the length for the shape;
with `mass: 0`, `length` does. Speed: `speed`, or `Re` (length Reynolds
number), which sets the speed.

## Outputs

* `drag_N` / `drag_mN`, the whole body. Parts: `drag_friction_N`,
  `drag_pressure_N` (on the body, without a base), `drag_base_N`.
  `friction_share` is the friction part of the total.
* `Cd_wet` on the wetted area (no base: Dress's C_D,wet), `Cd_vol` on
  volume^(2/3), `Cd_front` on the frontal area.
* Along the body (`surface.csv`: x/L, r/L, Cp, Cf):
  * `x_sep`: the first separation, where Cf turns negative;
  * `x_reattach`: where it turns positive again;
  * `x_te_sep`: a later, turbulent separation;
  * `x_cf_min`: where the laminar skin friction stops falling (transition
    or separation begins);
  * `Cp_min` and its position `x_Cp_min`.
* `yplus_min/max/mean` on the body, `unsteady`.
* Derived: `length_m`, `diameter_m`, `fineness_actual`, `x_max_diameter`,
  `wetted_area_m2`, `volume_m3`, `lead_kg`, `x_centroid`, `Re_L`, `Re_V`.

`iomcfd report`:
* `drag.png`: C_D,wet against Re_L, with the study's reference data and the
  laminar and turbulent flat-plate lines, and separation and reattachment
  against Re_L;
* `fineness.png`: drag against fineness at fixed lead (when swept);
* `surface.png`: Cf and Cp along the body;
* `drag.md`: the table.

## Mesh levels

Each level doubles the cell count (as foil2d). medium: 256 intervals along
the body, 128 normal to it, 96 along the wake, 40 across a base: about
45-50k cells. On one core a medium case takes about … (to be measured).

## Studies

* `smoke`: Dress's body and keel3d's bulb on xcoarse, 300 iterations.
* `validation-dress` (Track B1): Dress's body at six of his Reynolds
  numbers, Tu 0.1, 0.2 and 0.5 %, and fully turbulent; mesh check. The
  reference is `validation/dress1988.csv` (his Table III).
* `fineness` (Track B2): keel3d's 2380 g of lead as NACA bodies of fineness
  5-14.3 (230-463 mm long, including keel3d's NACA 0011 and 0007 bulbs) at
  0.5, 1.0 and 1.5 m/s, Tu 0.1 and 0.5 %, and
  fully turbulent.

## Limitations

* The transition model has not been validated on bodies of revolution at
  these Reynolds numbers (that is what validation-dress is for). Pond
  turbulence is unknown, so every result is a range over Tu.
* Langtry-Menter cannot predict crossflow transition, which a body at
  incidence has: keep incidence in keel3d.
* Dress's model had a blunt base and a magnetic core; his drag includes the
  base drag (corrected for blockage), and his base-pressure data are
  uncertain (his words).
