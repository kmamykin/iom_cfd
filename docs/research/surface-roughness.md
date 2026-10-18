# Surface roughness and drag of an IOM fin and hull

Research note, 2026-10-14. It asks three questions:
* How do the simulations treat surface quality?
* What does the literature say about roughness and drag at IOM scale?
* Is the surface finish a better way to cut drag than choosing between
  NACA sections that differ by a few %?

Literature numbers carry their source. Numbers worked out here say how they
were computed and are labelled **estimate**.

## Short answer

* **The simulations model a perfectly smooth fin.** Friction is computed
  exactly for that surface. Whether the boundary layer is laminar or
  turbulent depends only on the turbulence of the incoming water (Tu) and
  the pressure gradient, never on roughness.
* **A finish beyond about 400-600 grit, wet-sanded, doesn't pay.**
  * For a hull with turbulent flow, 80 grit against 600 grit is worth under
    half a boat length per race.
  * That is less than the difference between the leading fin sections
    (about 1 boat length).
* **The gross condition of the boat does pay, and it costs little.** An
  unsanded painted hull, slime, or a gritty surface costs about as much as
  a poor section choice, or more. Keep the hull and fin clean, fair, sanded
  and free of dings: that comes on top of the section choice, not instead
  of it.
* **Two levers may be bigger than either, and both are open questions.**
  * How far the hull's boundary layer stays laminar. That depends mostly on
    the turbulence of the water, which nobody seems to have measured on
    model-yacht ponds.
  * A deliberate trip on the fin, to shrink the laminar separation bubble.
    It would lower drag at working load and raise it downwind.

## How the simulations treat the surface

`foil2d` (all of `fin-profile-selection`, `mesh-finalists` and
`transient-check`):

* **Geometry.** The section is the exact NACA 4-digit shape with a sharp,
  closed trailing edge (`src/iomcfd/geometry/foils.py`, `naca4(...,
  closed_te=True)`).
  * There is no roughness parameter anywhere in the project.
  * Not modelled: waviness, unfairness, dings, paint runs, slime, and the
    finite trailing-edge thickness of a real fin.
* **Friction.** It is computed directly from the shear at the wall, and
  reported as `Cd_friction`, separate from pressure drag. The mesh resolves
  the viscous sublayer: the first cell is sized for y+ of about 0.5
  (`yplus` in `defaults.yaml`). At the wall
  (`projects/foil2d/template/0/`):
  * `k` = 0 (`fixedValue`);
  * `nut` = 0 (`nutLowReWallFunction`);
  * `omega` takes its viscous-sublayer value (`omegaWallFunction`).

  This is a smooth wall. OpenFOAM's rough-wall function
  (`nutkRoughWallFunction`) needs wall-function meshes (y+ above about 30),
  so it can't be used on these meshes with the transition model.
* **Transition.** `kOmegaSSTLM` (Langtry-Menter γ-Reθ) predicts where the
  laminar boundary layer separates, reattaches or turns turbulent.
  * Its inputs are the free-stream turbulence intensity (Tu, 0.1 % or 1 %
    in these studies) and the local pressure gradient.
  * The wall conditions for `gammaInt` and `ReThetat` are `zeroGradient`.
  * There is no roughness term. Tu stands in for disturbances in the water,
    not for the state of the surface.
* **How much of the fin drag is friction.**
  * At 0°: 55-72 % (findings, analysis 2026-10-13).
  * At 1 m/s and Tu 0.1 %, 0007/90: 37 % at 4°, 21 % at 6° (run
    20261013-200643).

  At working load most of the drag is pressure drag from the laminar
  separation bubble.

**Hull, bulb and rudder** appear only in the race-time estimate
(`projects/foil2d/findings/fin-profile-selection.md`, analysis
2026-10-13 (2)):
* hull: ITTC-57 friction × 1.10, on 0.142 m² wetted area, waterline length
  0.99 m;
* bulb: ITTC-57 × 1.2;
* rudder: Cd 0.014.

That is a hull that is hydraulically smooth and turbulent from the bow,
with no roughness allowance and no laminar run.

## Literature

**Model yachts.** K. Klaka (2022), [*The effect of hull surface roughness on
the performance of a model sailing yacht*][klaka]. A practitioner report
(not peer reviewed), read in full. It is the most directly relevant source.

* **Reynolds numbers.** A 1 m model hull runs at 4×10⁵ to 2×10⁶, close to or
  inside the laminar range. Fins and rudders run at 2×10⁴ to 1×10⁵.
* **Roughness of sanded paint.** From Schultz (2002), peak roughness heights
  (k_max) and rms values are:

  | finish | k_max [µm] | k_rms [µm] |
  |---|---|---|
  | P600 | 8-9 | 0.67-0.73 |
  | P400 | 8-9 | 0.70-0.77 |
  | P60 | 12-13 | 1.43-1.63 |
  | painted, unsanded | 39-50 | 3.4-5.0 |

  Schultz (2002) found friction falls with finer sanding down to 400 grit
  and no further. The sanding roughness is an order of magnitude smaller
  than the grit size.
* **When roughness stops mattering.** The "critical" (sublayer) roughness
  for a hull with turbulent flow, by formula:

  | speed | Larsson et al. | Schlichting | Hoerner |
  |---|---|---|---|
  | 0.5 m/s | 200 µm | 238 µm | 735 µm |
  | 1.0 m/s | 100 µm | 119 µm | 389 µm |
  | 2.0 m/s | 50 µm | 60 µm | 206 µm |

  Klaka prefers White's (2006) formula for model yachts. It has no critical
  height. The friction increase at Re ≈ 10⁶ is:

  | roughness | friction increase |
  |---|---|
  | 2 µm | 0.5 % |
  | 10 µm | 2 % |
  | 50 µm | 9 % |
  | 100 µm | 16 % |
  | 200 µm | 27 % |

  The ITTC-1978 ship allowance gives 15-120 % over the same range, a large
  overestimate at this Reynolds number.
* **Speed and race distance.**
  * A velocity prediction program (Bantock, WinDesign, DF95, 50 % upwind)
    gives a speed loss of 0.10-0.15 × the % friction increase.
  * Over 2 laps of a 90 m windward-leeward course, a hull with turbulent
    flow sanded with 600 grit instead of 80 gains "less than half a boat
    length" (text).
  * Read from his Figure 5, it is about 0.2 boat lengths: 0.72 lost at 80
    grit and 0.52 at 600, against a perfectly smooth hull.
* **Sailing trial.** A DF95 raced with gritty varnish (about 235 µm) lost
  about 5 % of boat speed; the program predicted 4 %. This is one
  qualitative trial in light wind.
* **Laminar flow on the hull.** In still water a smooth 1 m hull could be
  laminar over most of its length. Even a rough one could keep 20-80 % in
  his estimates.
  * Upper-ocean turbulence is Tu 0.1-1.2 % (Vijgen et al. 1992). Klaka
    argues a model yacht sees up to ten times that, because Tu is relative
    to the boat speed.
  * Laminar flow needs Tu below about 0.6 % (White 1974: Tu 0.6 % gives a
    transition Reynolds number of 10⁶).
  * His conclusion: in open water the flow is probably mostly turbulent;
    small ponds may be calmer.
  * There are no turbulence measurements for model-yacht ponds.
* **Foils (his Appendix B).** Upwind lift coefficients are 0.2-0.4. The fin
  is probably laminar unless the leading edge or the water trips it, with a
  laminar separation bubble upwind. "It may be worth trying to artificially
  turbulate the flow over the foils."

**When roughness trips laminar flow:**
* Turbulent spots appear behind roughness once its Reynolds number (local
  velocity at the roughness top × height / ν) exceeds about 600
  ([NACA TN 3858][tn3858]).
* Braslow and Knox give a method to predict that critical height
  ([Dommett][dommett]).
* Hoerner (quoted by Klaka): 10⁴ k_crit / x_tr ≈ 2.5 (2-4).

**Admissible roughness, turbulent flow:**
* Schlichting: about 100 ν/U ([cited in this DTIC report][dtic]).
* [Newer measurements][arxiv] put the bound about three times tighter.

**Ships:**
* The ITTC-1978 roughness allowance is ΔCF = [105 (k/L)^⅓ − 0.64]×10⁻³.
  Townsin's later work refined it ([TRID record][townsin]).
* Schultz (2007), [*Effects of coating roughness and biofouling on ship
  resistance and powering*][schultz2007]: slime films add noticeably to
  resistance; heavy calcareous fouling adds up to 86 % to the power at
  cruising speed (abstract only).

**Towing tanks.** Ship models of IOM size are tripped deliberately at the
bow (trip wire, studs, sand strips), because at Re ≈ 10⁶ they would otherwise
be partly laminar ([ITTC 7.5-01-01-01][ittc], [NTNU study][ntnu]; ITTC
dimensions not checked).

**Keels.**
* Obara and van Dam (1989), [*Keel design for low viscous drag*][obara]:
  roughness, waviness and free-stream turbulence limit laminar flow on
  keels, and the paper gives limits (not read).
* Vijgen, van Dam and Obara (1992), *Turbulence effects on the design and
  performance of low-drag keels*, J. Ship Research 36(3), via Klaka.

**Low-Reynolds-number foils and trips:**
* Lyon, Selig and Broeren (1997), [*Boundary layer trips on airfoils at low
  Reynolds numbers*][lyon], Re 100-300k (abstract):
  * thin trips gave large drag reductions on sections with bubbles;
  * the trip location mattered little if it was ahead of laminar
    separation;
  * a tripped section with a large bubble could not beat an untripped one
    with a small bubble.
* Selig et al. (1996) ([PDF][selig96]): zig-zag trips shrank the bubbles at
  Re 40-100k.
* Gopalarathnam et al. (2003) ([PDF][gopal]): a trip that helps at one angle
  and Reynolds number can hurt at another.
* Other studies disagree on whether tripping helps or hurts above Re about
  10⁵ (secondary summaries only, not checked).

## Numbers for an IOM

All worked out here; **estimates**.

**Resistance split at 1 m/s** (viscous only, upright, no wave drag; method
as in the race-time analysis):

| part | drag [N] | share |
|---|---|---|
| hull | 0.377 | 50 % |
| fin | 0.200 | 27 % |
| bulb | 0.105 | 14 % |
| rudder | 0.070 | 9 % |
| total | 0.752 | |

At 0.5 and 1.5 m/s the hull's share is 49 % and 51 %.

**Hull laminar run.** Flat-plate friction with natural transition at Re_x =
5×10⁵ (Prandtl-Schlichting, A = 1700), against turbulent from the bow
(0.074 Re^-0.2):

| speed | Re_L | friction with a laminar run / turbulent from the bow |
|---|---|---|
| 0.5 m/s | 4.4×10⁵ | 0.37 (all laminar) |
| 1.0 m/s | 8.7×10⁵ | 0.59 |
| 1.5 m/s | 1.3×10⁶ | 0.71 |

At 1 m/s that is a 41 % cut in hull friction, about 20 % of the boat's
viscous resistance. It holds only if the water and the bow let the flow
stay laminar.

**Unsanded paint against 600 grit (hull, turbulent flow).**
* Using White's figures at 10 and 50 µm, hull friction is about 7 % higher.
* Speed loss:
  * 0.7-1.0 % with Klaka's program factor (0.10-0.15);
  * 1.0-2.0 % with this project's resistance slope (doubled / as
    estimated; analysis 2026-10-13 (2)).

The two methods agree within that range.

**Roughness that could trip the fin.** Roughness Reynolds number 600, with
the near-wall Blasius profile u = 0.332 U (k/x) √Re_x:

| speed | at 5-50 mm from the leading edge | 100 ν/U |
|---|---|---|
| 0.5 m/s | 0.7-1.2 mm | 227 µm |
| 1.0 m/s | 0.4-0.7 mm | 114 µm |
| 2.5 m/s | 0.2-0.35 mm | 45 µm |

These heights are about the boundary-layer thickness, where the linear
profile no longer holds, so they are an order of magnitude only.
* Sanding roughness (about 10 µm) is far below them.
* A ding, paint run or tape edge of a few tenths of a millimetre near the
  leading edge is not.

**Comparison per race.** Using Klaka's course of 2 laps of 90 m legs,
about 420 m sailed with the course at β_TW = 42° upwind: 1 % of race time ≈ 4 m ≈ 4 boat
lengths. This is a rough conversion.

| what changes | effect | boat lengths per race |
|---|---|---|
| hull, 600 grit → perfectly smooth (turbulent flow) | Klaka Fig. 5 | about 0.5 |
| hull, 80 → 600 grit (turbulent flow) | Klaka Fig. 5 | about 0.2 |
| fin section, among the four leaders | 0.2-0.3 % race time (findings, run 20261013-200643) | about 1 |
| fin section, best against worst of the seven candidates | up to 1.6 % | about 6 |
| fin section, NACA 0012 against the leaders | 2.2-5.1 % (Tu 1 %) | 9-20 |
| hull, unsanded paint (40-50 µm) → 600 grit | 0.7-2 % speed | 3-8 |
| hull, very rough (about 235 µm) | about 5 % speed (Klaka's trial) | about 20 |
| hull, laminar to mid-length against tripped at the bow | −41 % hull friction at 1 m/s | possibly the largest; set by the water's turbulence |

## Conclusions

1. **Within the normal range of finishes (400-1200 grit, polished), the
   finish is worth less than the choice between the leading sections.**
   Sanding below 400 grit buys nothing measurable for turbulent flow
   (Schultz 2002), and roughness has little effect on laminar friction.
2. **A poor surface costs as much as a poor section choice, or more.**
   Unsanded paint, slime, weed, grit, dings and unfair areas fall in this
   class. Fix these first: they are cheap, and they come on top of the
   section choice.
3. **On the fin, micro-roughness doesn't matter, but defects near the
   leading edge might.** A finish of 400 grit or finer is far below the
   heights that trip transition, so the smooth-wall CFD is a fair model of
   a well-finished fin. Defects of a few tenths of a millimetre near the
   leading edge can trip it. That could raise drag (more turbulent
   friction) or lower it (a smaller bubble).
4. **A deliberate trip on the fin is a lever of the same order as the
   section choice, or larger.**
   * The laminar bubble causes most of the fin's drag at 4-6°.
   * The literature shows large drag reductions from trips at Re 100-300k,
     but off-design penalties.
   * Downwind at 0°, a trip adds turbulent friction.
   * Only the race-time balance can say whether it pays.
5. **The hull's laminar run is the largest unknown.**
   * It depends mostly on the turbulence of the water, which hasn't been
     measured.
   * A smooth, fair, undamaged bow keeps the chance of laminar flow open.
   * If the hull is partly laminar, its resistance slope is lower than the
     turbulent estimate used in the race-time analysis. The fin's drag then
     matters relatively more.

## Implications for this project

* **The fin-section comparison stands** for well-finished fins. It does not
  cover fins with leading-edge damage or a blunt trailing edge.
* **A trip study in `foil2d`**, on hold until a section is recommended
  (user, 2026-10-15). The transient check decides whether it can use the
  steady solver.
  * Force transition at a chosen chord position on the suction side, both
    sides, or neither.
  * Run the leading sections at 0-6° and 0.5-1.5 m/s, and compare by race
    time.
* **The race-time analysis assumes a turbulent, smooth hull.** A `hull`
  CFD run with the transition model, or a turbulence measurement on a
  sailing pond, would bound the laminar-run question.
* **Fin-making spec suggested by this note:**
  * wet-sand to 400-600 grit;
  * keep the leading edge free of dings and the profile fair;
  * keep the trailing edge as thin as stiffness allows;
  * keep the fin and hull clean.

  Polishing further is not supported by the evidence found here.

## Caveats

* Klaka's report is not peer reviewed. Its speed factors come from one
  program and one boat (DF95), and its trial is one regatta.
* Several sources were seen only as abstracts or secondary summaries (marked
  above), and the stated ranges come from those.
* Every estimate here uses flat-plate relations with no pressure gradient.
  The fin's real transition is set mainly by its pressure gradient and the
  laminar bubble, which the CFD resolves and these formulas do not.
* The conversion to boat lengths assumes the same boat speed and Klaka's
  course.

[klaka]: https://www.onemetre.net/Race/Surface%20finish/Klaka%20roughness%20for%20modelyachts-v8-full%20version.pdf
[tn3858]: https://ntrs.nasa.gov/api/citations/19930084653/downloads/19930084653.pdf
[dommett]: https://resolve.cambridge.org/core/journals/aeronautical-journal/article/abs/critical-height-of-distributed-roughness-to-cause-boundary-layer-transition/ECC939658FCDFFE9F45D7FA5998EBA22
[dtic]: https://apps.dtic.mil/sti/pdfs/AD0730427.pdf
[arxiv]: https://arxiv.org/pdf/1810.05743v2
[townsin]: https://trid.trb.org/View/402727
[schultz2007]: https://pubmed.ncbi.nlm.nih.gov/17852068/
[ittc]: https://home.hvl.no/ansatte/gste/ftp/MarinLab_files/Litteratur/ITTC/ITTC-75-01-01-01_Model_manufacture.pdf
[ntnu]: https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2566250
[obara]: https://trid.trb.org/View/401850
[lyon]: https://m-selig.web.engr.illinois.edu/pubs/LyonSeligBroeren-1997-AIAA-1997-0511-BLTrips.pdf
[selig96]: https://m-selig.web.engr.illinois.edu/pubs/SeligGuglielmoBroerenGiguere-1996-AIAA-1996-0062.pdf
[gopal]: https://m-selig.web.engr.illinois.edu/pubs/GopalarathnamEtal-2003-JofAC-LRNAirfoiLDesignWithTrips.pdf
