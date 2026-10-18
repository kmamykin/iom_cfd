# foil2d: 2D keel and rudder sections

Steady 2D RANS polars for fin and rudder sections at IOM Reynolds numbers,
with laminar-turbulent transition.

**Status: working, partly validated** (NACA 0009 at Re 1e5 below; mesh
refinement, turbulence-intensity sensitivity and the NASA NACA 0012
benchmark are next).

How fin sections are ranked by race time (equal side force, leeway, upwind
and downwind legs): [methodology.md](methodology.md). Results and decisions:
[findings/](findings/).

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
(`naca0008`, `naca0007-74` (modified 4-digit), `file:<name>.dat` or a stepped section such as `stair1:naca0009`), `chord`, `aoa`, `speed` or `Re`,
`turbulence`, `Tu`, `mesh`.

The modified 4-digit `naca00TT-IM` separates what the plain 4-digit ties to
thickness: I is the nose-radius index (6 = the plain section's radius,
1.1019 t², which scales with I²; 9 = three times it) and M the position of
maximum thickness in tenths (`naca0007-45` is the 16-series shape).
Symmetric only.

## Section design (XFOIL)

`python -m iomcfd.sectiondesign` screens and optimises sections with XFOIL
before they get CFD time: `screen` ranks sections by race time against a
baseline (methodology.md, `iomcfd.racetime`), `calibrate` checks XFOIL's
ranking against finished CFD runs, `optimise` evolves a CST section at the
baseline's bending stiffness, `export` writes sections to
`geometry/foils/` for a study (`file:<name>.dat`), and `figure` draws a
section against others (true scale, nose and tail close-ups, thickness and
stiffness), e.g. for `findings/figures/`. XFOIL is not part of the
image: build it with `tools/build-xfoil.sh`. Use 0.5° angle steps; how far
XFOIL can be trusted, and what it misses (the leading-edge bubble on sharp
noses), is in [findings/custom-section.md](findings/custom-section.md).

## Outputs (per case, in results.csv)

`Cl`, `Cd`, `Cm` (quarter chord, nose-up +) with `_std` over the final
window; `L_D`; `Cd_pressure` and `Cd_friction`; lift and drag per metre of
span; `x_sep_*`, `x_reattach_*`, `x_te_sep_*` (laminar separation,
reattachment and trailing-edge separation, x/c, per side); `yplus_max`;
`converged`, `unsteady`. Each case also has `surface.csv` (Cp and Cf along
both surfaces). `iomcfd report` draws polars with any reference data.

Transient cases (`solver: transient`) add:
* `flow_times_done`;
* the drift check, `Cl_drift`, `Cd_drift` and `drifting` (docs/workflow.md,
  "Convergence and statistics");
* `force_history.csv`: t, flow-throughs, Cl, Cd, Cm, joined with the case
  it continued, if any (`start_from`).

The report adds `report/transient.md` and `report/force_history.png`.
`surface.csv` of a transient case is the final instant, not a time average.

Studies that vary the section or chord also get `report/selection.png`
(and the numbers in `selection.csv`): drag against side force, one panel per
speed and turbulence setting. Sections and chords are compared at equal side
force, not equal Cl. `selection_compare.md` / `.csv` tabulate every
candidate's drag, as % above the best, at the side forces a reference
candidate makes at a few angles (interpolated along each candidate's
pre-stall branch). The table is also included in `summary.md`. Options in
the study's `report:` block (no re-run):

```yaml
report:
  fin_span: 0.36        # m: whole-fin forces [N] instead of per metre of span
  induced_drag: true    # add L^2 / (2 pi q e b^2): lifting line, hull as reflection plane
  span_efficiency: 0.9  # e
  compare_at: {foil: naca0009, chord: 0.08, aoa: [2, 4, 6]}  # default: middle section, shortest chord
```

Studies with `highlights:` (docs/workflow.md) also get
`report/highlights.md` (Cl, Cd, friction drag and the separation and
reattachment points of each highlighted case) and
`report/highlight_<name>.png`: Cp and Cf along the chord from `surface.csv`,
one line per compared value (e.g. per section), with Cf on the upper
(suction) and lower surface in separate panels. Cf < 0 marks reversed flow:
a laminar separation bubble where it is short and followed by reattachment,
trailing-edge separation where it runs to the trailing edge. No field data
is needed, so it works on a default (light) `gcp fetch`.

Induced drag depends on side force and span, not on chord or section, so at
equal side force it is the same for every candidate: it shows how much the
section differences matter in the total, it does not reorder them. Questions
where the span changes (equal-area fins, aspect ratio, tip and bulb effects)
need the 3D `appendage3d` project.

## Stepped sections (Kline-Fogleman)

`foil: stair1:naca0009:x=0.5,d=0.3` cuts backward-facing steps into a smooth
symmetric base section (`naca0009`, `file:<name>.dat`). Every step is cut
into both surfaces at the same x/c: a fin works on both tacks, so the
sections stay symmetric (the one-sided hobby KFm1/KFm2 are not offered). Behind a step
the surface is the base with its thickness scaled down, so the shape is kept
and the trailing edge stays sharp
([src/iomcfd/geometry/stepped.py](../../src/iomcfd/geometry/stepped.py)).

The number in the name is the steps per surface:

| spec | steps |
|---|---|
| `stair1:<base>` | one on each surface at the same x/c (the layout the hobby calls KFm4) |
| `stair5:<base>` | 5 steps of 0.2 mm on each surface, evenly spaced from x/c 0.3 to 0.9 |
| `stair10:<base>` | 10 steps of 0.1 mm on each surface, evenly spaced from x/c 0.3 to 0.9 |

The hobby KFm numbers are a catalogue (KFm1 a step below, KFm2 one on top,
KFm3 two on top, KFm4 one on top and one below, ...), not step counts, so
this project uses its own names. The mm are for an 80 mm chord.

Options after a third `:`, comma separated. stair1: `x` (step x/c, 0.5), `d`
(depth as a fraction of the local half-thickness, 0.3) or instead `h`.
stair5/stair10: `h` (every step's height as a fraction of the chord: 0.0025
and 0.00125), `x` and `x_end` (first and last step, 0.3 and 0.9).
All: `angle` (face to chord line, 90 = vertical), `r_lip`, `r_foot` (fillet
radii at the top and foot of the face, fractions of the step height: 0.05,
0.25). On an 80 mm NACA 0009: `stair1` d=0.3 at x/c 0.5 is a 0.95 mm step,
d=0.5 a 1.6 mm one; `stair10:naca0009` and `stair5:naca0009` each leave
about half the thickness near the trailing edge, like the 1.6 mm step.
Steps that would remove more than 90 % of the thickness are refused.

Mesh: the same C-grid, with two changes for stepped sections only (smooth
sections are meshed bit-for-bit as before). Wall points are refined to a
fraction of the step height at the lip (2 %), at the foot (10 %) and over
8 step heights behind it (10 %), and the first cell is kept below 5 % of
the smallest step height (a 0.1 mm step would otherwise sit inside it at
low speed). Near the steps the grid lines are marched outward layer
by layer, hyperbolic-grid style, so they fan round the lip and spread out
of the concave foot instead of crossing, and the points clustered at each
step spread out with wall distance. Quality on the medium level (centroid
non-orthogonality, as checkMesh): no inverted cells; stairs up to ~55 deg;
stair1 60-79 deg in up to a few hundred faces, the most for the deepest step
at x/c 0.35 at low speed (smooth sections ~20 deg), so stepped cases run one
non-orthogonal corrector. Cells: stair1 ~1.3x the smooth section, stair5
3x, stair10 5.5x. Extra mesh figures zoom on the first upper step; `iomcfd viz` has a
`step` view (streamwise velocity, reversed flow in blue). Extra outputs:
`step_reattach_upper/lower`, where the flow reattaches behind the most
forward step on each side, in step heights (0: no reversed flow behind it).

Section figures: `iomcfd report` on a study with stepped sections writes
`report/sections.png` (every section of the study at true scale, stepped
ones over the section they were cut from, with a close-up of the first
step) and `report/section_<spec>.png` per stepped section (whole section,
step close-up with height and fillet radii, both surfaces in mm, step
table; [src/iomcfd/sectionplot.py](../../src/iomcfd/sectionplot.py)). To
look at sections before running a study:

```sh
uv run python -m iomcfd.sectionplot /tmp/sections naca0009 stair1:naca0009:x=0.35 stair10:naca0009 stair5:naca0009
```

Status: the step flow is unvalidated (no open measurements of a symmetric
stepped section at these Reynolds numbers were found; the studies that
exist are mostly abstracts or closed access). Numerics checks:
`stepped-checks`. Comparison with NACA sections: `stepped-vs-naca`.

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
`fin-profile-selection` (now the four finalists 0008/80, 0009/80, 0008/90,
0009/100 at 0.5-2.5 m/s, Tu 0.1 %, medium mesh: 100 cases; run
20261012-175146 had NACA 0006-0012 × 80/90/100 mm at Tu 1 %, 450 cases; run
20261012-045433 0006/0009/0012 × 80/100 mm at Tu 0.1 and 1 %, coarse mesh),
`mesh-finalists` (0008/80 and 0009/80 at 1 m/s, 4 and 6°, coarse / medium /
fine: is the medium mesh enough to separate them?), `stepped-smoke`
(pipeline check for stair1, stair5 and stair10), `stepped-checks` (mesh
convergence and steady vs transient for stepped sections; run 20261013-190301:
11 cases, run 2: the two transient cases again, from a steady start),
`stepped-vs-naca` (stair1 steps at x/c 0.35 and 0.5, 15/30/50 % deep, and
stair5 and stair10, cut from NACA 0009, against plain 0009 and 0007;
0.5-1.5 m/s: 150 cases), `custom-section-screen` (published low-Reynolds
sections scaled to 7 %, a modified 4-digit and a 6-series section against
NACA 0007 at 100 mm, 0-6° with 3° and 5°: the CFD screen of
[findings/custom-section.md](findings/custom-section.md)),
`custom-section-optima` (the two XFOIL-optimised CST sections, same
settings), `custom-section-transient` (HT35 at 7.25 % and NACA 0007,
time-accurate at 2-5°), `custom-section-tu` (the same two, steady, at Tu 1
and 2 %), `custom-section-transient-opt2` and `custom-section-tu-opt2`
(both again for cst-opt2), `custom-section-transient-rerun` (failed
time-accurate cases again, at max_co 5).

What the runs showed, and the assumptions behind them, is logged per study
in [findings/](findings/), e.g.
[findings/fin-profile-selection.md](findings/fin-profile-selection.md).
