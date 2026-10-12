# foil2d: 2D keel and rudder sections

Steady 2D RANS polars for fin and rudder sections at IOM Reynolds numbers,
with laminar-turbulent transition.

**Status: working, partly validated** (NACA 0009 at Re 1e5 below; mesh
refinement, turbulence-intensity sensitivity and the NASA NACA 0012
benchmark are next).

## Physics

* IOM fins: chord 65-90 mm, 6-8 % thick, boat speed 0.5-2 m/s, so
  Re ≈ 3e4-2e5. At these Reynolds numbers much of the section is laminar and
  laminar separation bubbles set the drag, so the default turbulence model is
  **kOmegaSSTLM** (Langtry-Menter transition). `turbulence: kOmegaSST` gives
  the fully turbulent answer for comparison.
* Freestream turbulence intensity `Tu` drives transition. The pond value is
  unknown (a towing tank is < 0.1 %, open water with waves probably 0.5-2 %),
  so treat it as a parameter to sweep, not a constant. Decay control keeps
  Tu at the foil equal to the inlet value regardless of domain size.
* Angle of attack is set by rotating the freestream, so one mesh serves a
  whole polar.

## Mesh

Structured C-grid written directly as an OpenFOAM `polyMesh` by
`iomcfd.geometry.cmesh` (no blockMesh): hexahedra only, wall-normal grid
lines, first cell sized for y+ ≈ `yplus` from a flat-plate estimate, 50-chord
far field, wake cut behind a sharp trailing edge.

| `mesh` | cells | surface points per side | wall-normal cells |
|---|---|---|---|
| xcoarse | ~22k | 128 | 64 |
| coarse | ~45k | 181 | 91 |
| medium | ~90k | 256 | 128 |
| fine | ~180k | 362 | 181 |
| xfine | ~360k | 512 | 256 |

## Parameters

See [defaults.yaml](defaults.yaml); the main ones are `foil`
(`naca0008` or `file:<name>.dat`), `chord`, `aoa`, `speed` or `Re`,
`turbulence`, `Tu`, `mesh`.

## Outputs (per case, in results.csv)

`Cl`, `Cd`, `Cm` (quarter chord, nose-up +) with `_std` over the final
window; `L_D`; `Cd_pressure` and `Cd_friction`; lift and drag per metre of
span; `x_sep_*`, `x_reattach_*`, `x_te_sep_*` (laminar separation,
reattachment and trailing-edge separation, x/c, per side); `yplus_max`;
`converged`, `unsteady`. Each case also has `surface.csv` (Cp and Cf along
both surfaces). `iomcfd report` draws polars with any reference data.

## Validation: NACA 0009, Re = 1e5

Study `validation-naca0009-re1e5`, coarse mesh, Tu = 0.1 %, compared with
Princeton wind-tunnel data (Selig, Donovan & Fraser 1989), interpolated to
the same angles:

| α | | Cl | Cd |
|---|---|---|---|
| 4° | tunnel | 0.424 | 0.0134 |
| | kOmegaSSTLM | 0.425 ± 0.022 | 0.0148 (+10 %) |
| | kOmegaSST | 0.404 (−5 %) | 0.0166 (+24 %) |
| 8° | tunnel | 0.713 | 0.0363 |
| | kOmegaSSTLM | 0.673 (−6 %) | 0.0454 (+25 %) |
| | kOmegaSST | 0.733 (+3 %) | 0.0309 (−15 %) |

What the solutions show:

* **4°**: laminar flow on the whole lower surface and the front of the upper
  surface. Laminar friction is half the turbulent value, which is why the
  fully turbulent model overpredicts drag. Around x/c ≈ 0.2 the upper-surface
  layer separates and sheds vortices instead of forming a steady bubble, so
  the steady solver never settles (Cl ± 5 %, flagged `unsteady`). The
  4° numbers are averages over iterations, not over physical time.
* **8°**: the transition model predicts a laminar bubble from about 0.04c to
  0.23c that flattens the suction peak (−6 % lift) and dominates the drag
  (+25 %). The fully turbulent model has no bubble and too little drag. The
  measured drag rises steeply here (7.2° → 8.2°: +49 %), so this point is
  very sensitive to where the separated shear layer becomes turbulent.

Likely causes of the differences, roughly in order: the transition model's
treatment of separation bubbles (its known weak spot); uncertain effective
tunnel turbulence (0.36 % unfiltered, 0.01-0.06 % above 1 Hz); steady
solutions of unsteady flow at 4°; mesh resolution (coarse level, y+ up to
3 at the suction peak); and the experiment's own scatter (a separate lift
run in the same archive reads 0.01-0.02 lower Cl).

Practical reading: at upwind leeway angles (2-5°) the transition model is
good enough to rank sections, with absolute drag uncertain by roughly
10-25 %. Above ~6° use both models as bounds.

Studies: `smoke` (pipeline check), `validation-naca0009-re1e5`,
`validation-naca0012-tmr` (NASA Turbulence Modeling Resource case, Re 6e6,
fully turbulent: a solver check independent of transition modelling),
`thickness-re1e5` (NACA 0006 against NACA 0009, Re 1e5; no reference data
for the 0006).
