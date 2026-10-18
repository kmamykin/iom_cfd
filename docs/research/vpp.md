# Velocity prediction programs (VPPs) for an IOM

Research note, 2026-10-18. It asks:
* What VPP force models and programs exist, open source or not?
* Which suit a 1 m radio yacht?
* How would a VPP sit on top of this project's CFD (hull, appendage3d,
  sails)?

The aim is to turn force differences from the simulations (for example a
bulb's drag against its righting moment,
[bulb-design.md](bulb-design.md)) into boat speed and
race time.

How much was read:
* Read for this note: the Python-VPP README, the gvpp project page, the
  SA-VPP forum post, Gilbert's *Simple VPP* page, the USMMA slides and
  Parolini & Quarteroni.
* Known only from search summaries or abstracts, and marked as such: the
  ORC documentation's contents, the Day 2017 paper and the commercial
  tools.

## Nomenclature

From Parolini & Quarteroni, "Forces and moments on the water plane"
([MOX 10/2007][parolini], Fig. 2 and eq. 2). On the water plane, x points
along the boat velocity (the course) and y is normal to it.

| symbol | meaning |
|---|---|
| V_b | boat velocity |
| β_Y | yaw angle, between the course and the boat centreline (this repo's `leeway`) |
| β_TW, β_AW | true and apparent wind angles |
| D_h | hydrodynamic drag, along the course |
| S_h | hydrodynamic side force, normal to the course |
| M_h | hydromechanic righting moment, about the boat centreline |
| T_a | aerodynamic thrust, along the course |
| S_a | aerodynamic side force, normal to the course |
| M_a | aerodynamic heeling moment |
| L_a, D_a | aerodynamic lift and drag, in the apparent-wind frame |

A steady sailing state satisfies

    D_h + T_a = 0,   S_h + S_a = 0,   M_h + M_a = 0

Each term is a function of V_b, heel and β_Y. A VPP finds, for each true
wind speed and β_TW, the V_b, heel, β_Y and sail trim that satisfy these
and give the most speed. Adding a yaw-moment balance brings in the rudder
angle.

Clashes with this repo's names:
* The repo says leeway for β_Y.
* appendage3d's `yaw_moment_Nm` is a moment about z, so "yaw" now means two
  things.
* The repo frame has x aft (flow towards +x), while the paper's x points
  along V_b.

## Short answer

* **The physics is public. Good open code is scarce.**
  * The ORC publishes its full VPP formulation every year, free.
  * The Delft series (DSYHS) regressions are published.
  * Open-source programs are few, small, or built for other kinds of boat.
    One presentation sums it up: "Few open-source VPP's exist. Lack of
    documentation. Companies guard their intellectual property"
    ([USMMA][usmma]).
* **The best open code to start from is [Python-VPP][pyvpp]** (MIT
  licence).
  * It solves the equilibrium with SciPy's SLSQP.
  * Its force models are the ORC's, and its default boat is the YD-41.
* **The only IOM VPP is Lester Gilbert's Excel *Simple VPP*.** Its forces
  are "arbitrarily scaled" and it is not calibrated ([onemetre.net][poorvpp]).
* **Don't use the empirical hull models (ORC, DSYHS) for an IOM.** They were
  fitted to full-size hulls at Reynolds numbers 10-100 times higher. At IOM
  scale the laminar or turbulent state of the boundary layer dominates the
  drag ([bulb-design.md](bulb-design.md),
  [surface-roughness.md](surface-roughness.md)).
* **For this project: use the CFD results as the boat model and a small
  solver on top.**
  * Tabulate D_h, S_h, M_h, T_a, S_a and M_a from the hull, appendage3d and
    sails projects.
  * Interpolate the tables, and solve eq. 2 plus a yaw balance.
  * Either fork Python-VPP, replacing its force functions, or write about
    200 lines in `iomcfd` (**estimate**).
  * The missing piece is the hydrostatic righting moment at heel (below).

## Force models (the boat model)

| model | covers | for an IOM |
|---|---|---|
| [ORC VPP Documentation][orcdoc] (yearly, free; [2023 edition][orc2023]) | hull resistance (upright and heeled), appendages, sail forces with depowering (flatten, reef), the solution method | A good template for the structure and the depowering logic. Its hull model is full scale: since 2013 the residuary resistance is fitted to a 43-hull RANS series, and friction uses the Hughes line instead of ITTC-57 ([ORC column][orc2012], **search summary**). |
| Delft Systematic Yacht Hull Series (DSYHS), e.g. [Keuning & Sonnenberg 1998][keuning] | regressions for upright and heeled residuary resistance, side force and induced drag of the hull and keel | full-size hulls of the 1970s-2000s; well outside an IOM's Reynolds number and hull shapes |
| Day 2017, [Performance prediction for sailing dinghies][day] | a dinghy VPP for a rig that can't reef: depowering, heel decoupled from the heeling moment, crew position, yaw-moment balance; validated upwind against measurements | the closest in kind to an IOM: small, light, can't reef (**abstract only**) |
| Hazen (1980) sail model, Kerwin's MIT VPP (1978) | the original sail coefficients and VPP structure behind IMS and ORC ([history][wiki]; names and dates from background knowledge, not re-checked) | historical; the ORC documentation supersedes them |
| Parolini & Quarteroni ([MOX 10/2007][parolini]) | the equilibrium (eq. 2) and the CFD that feeds a VPP: transition, junctions, winglets, free surface | the nomenclature and method this project follows |

## Open-source programs

| program | language, licence | force models | what it solves | status and limits |
|---|---|---|---|---|
| [Python-VPP][pyvpp] (Lauber, Villani, Dickson) | Python, MIT | ORC aero and hydro | maximises V_b over speed, heel, leeway, sail flattening and reefing, at each true wind speed and angle (SLSQP); "3-DOF" | default boat YD-41, benchmarked against WinVPP output; kite model "very rough"; 143 commits, about 60 stars; [web demo][pyvpp-app], [docs][pyvpp-docs] |
| [gvpp][gvpp] | MATLAB, GPLv2 | DSYHS or the user's own data | equilibrium VPP | beta, last updated 2020-12-21; Python version "available upon request" |
| [SA-VPP Sailboat][savpp] | LibreOffice spreadsheet, "free and open source" (no licence named) | Delft series and derived formulas | speed and heel | only three headings (upwind, 90°, 135°), 4-20 kn; meant "for design purpose more than for rating" |
| [Simple VPP][poorvpp] (Lester Gilbert; macros updated by David Kender, 2020) | Excel (.xls, .xlsm) | sail lift and drag coefficients; hull drag scaled to an IOM hull speed of 1.23 m/s | polars, VMG, time to reach top speed | **the only IOM VPP**; forces "arbitrarily scaled", "we don't have a calibrated spreadsheet"; no spinnaker; fragile macros |
| [USMMA dynamic VPP][usmma] (Perez, 2022) | Python | towing-tank lift and drag of a hull with a bar keel; sail coefficients | marches in time until the forces balance | for merchant sailing ships; slides only, no code location found |

## Commercial and research tools

Names and claims here come from search summaries. None was evaluated.

* **[ORC Designer's suite][orcvpp]:** the software the rating offices use
  (DXT/OFF hull input), about €400 a year.
* **WinDesign** (Wolfson Unit): steady-state only, per a
  [Chalmers thesis][chalmers-wd]. The same thesis names SailSim as a
  time-domain alternative.
* **FS-Equilibrium** (now DNV): a modular "workbench" of force modules,
  used for a hydrofoil lake racer ([TUHH][tuhh]).
* **Maxsurf VPP** (Bentley), **PCSail** and **WinVPP**: known by name only.
* **Research:** CFD coupled to rigid-body motion in 6 degrees of freedom
  ([Chalmers, dinghy][chalmers-6dof]); CFD-based dynamic VPPs
  ([LHEEA][lheea]).

## How a VPP would sit on this project

Each term in eq. 2 maps to a project output. These are the outputs as the
project READMEs describe them.

| term | source | output | gap |
|---|---|---|---|
| D_h | `hull` (VOF; `appendages: true` adds the keel and rudder) or `hull` + `appendage3d` | `resistance_N`; `drag_N` | the two projects use different turbulence and transition setups |
| S_h | `appendage3d` (+ `hull`) | `side_N`; `side_force_N` | in the boat frame; rotate by β_Y into the course frame |
| M_h | hydrostatics: weight and buoyancy at heel, plus the hydrodynamic roll moment (`roll_moment_Nm`) | not computed today | needs a heeled-hydrostatics routine (STL volume and centroid below a heeled waterline; `src/iomcfd/geometry/stl.py` already computes volumes) and the boat's mass properties: bulb, fin, hull, rig |
| T_a, S_a, M_a | `sails` | `drive_N`, `heel_force_N`, `heel_moment_Nm`, `z_ce`, lift and drag relative to the apparent wind | same frame rotation; depowering (sheeting, twist, camber) becomes a VPP variable |
| yaw balance | `appendage3d` (`rudder_angle`, `yaw_moment_Nm`), sails' centre of effort | partly | needs the sails' centre of effort in x |
| all at once | `fullboat` | - | experimental; no converged run yet |

Notes:
* **Tables, not formulas.** Run the hull, appendage3d and sails sweeps over
  V_b, heel and β_Y (and AWA and trim for the sails), store the results,
  and fit smooth response surfaces. Polynomials in β_Y and heel per speed
  are a common choice (**assumption**).
  * The VPP only interpolates. It never extrapolates outside the swept
    range.
* **The solver** (**estimate** of the work):
  * For each TWS and β_TW, maximise V_b over heel, β_Y and the sail trim
    variables, subject to eq. 2 and the yaw balance.
  * Use `scipy.optimize` (SLSQP), as Python-VPP does.
  * An IOM can't reef but changes rig (A, B, C); treat each rig as its own
    set of sail tables.
* **Validation.** Gilbert's polar and timing measurements, GPS logs of real
  IOMs, or the tow-test speeds in bulb-design.md could anchor it.
  None was checked for this note.
* **Race time.** A VPP turns a drag or righting-moment difference into
  seconds per leg. That is what the bulb trade-offs need (drag against a
  lower VCG), as do the fin results in
  [fin-stiffness.md](fin-stiffness.md).

## Gaps

* No VPP calibrated for an IOM exists that I could find.
* Python-VPP was judged from its README. Whether its ORC force functions
  can be swapped out cleanly is unchecked.
* The ORC documentation, Day 2017 and the commercial tools were not read.
  Their descriptions above come from summaries.
* Hydrostatic righting moment at heel and the boat's mass properties
  (VCG, inertia) are not yet in the project.

## Sources

Most useful: [Parolini & Quarteroni][parolini] (nomenclature, equilibrium),
[ORC VPP Documentation][orcdoc] (a complete public formulation),
[Python-VPP][pyvpp] (code to start from), [Day 2017][day] (small boats
that can't reef), [Simple VPP][poorvpp] (the one IOM VPP).

[parolini]: https://www.mate.polimi.it/biblioteca/add/qmox/10-2007.2007.pdf
[pyvpp]: https://github.com/marinlauber/Python-VPP
[pyvpp-app]: https://yacht-vpp.streamlit.app
[pyvpp-docs]: https://app.readthedocs.org/projects/python-vpp/
[gvpp]: https://sourceforge.net/projects/gvpp/
[savpp]: https://www.boatdesign.net/goto/post?id=889612
[poorvpp]: https://onemetre.net/Design/VPP/PoorVPP.htm
[usmma]: https://www.webb.edu/wp-content/uploads/2023/02/WI-SISD22-10-Perez-VPP-Dynamic-Open-Source-Velocity-Prediction-Program-VPP-25-Oct-2022.pdf
[orcdoc]: https://orc.org/organization/rules-regulations
[orc2023]: https://orc.org/uploads/files/ORC-VPP-Documentation-2023.pdf
[orcvpp]: https://orc.org/for-designers/orc-vpp
[orc2012]: https://orc2.orc.org/SH%20Columns/SH%20ORC%202012%20Dec.pdf
[keuning]: https://research.tudelft.nl/en/publications/approximation-of-the-hydrodynamic-forces-on-a-sailing-yacht-based/
[day]: https://strathprints.strath.ac.uk/59980/1/Day_OE_2017_Performance_prediction_for_sailing_dinghies.pdf
[wiki]: https://en.wikipedia.org/wiki/Velocity_prediction_program
[chalmers-wd]: https://odr.chalmers.se/server/api/core/bitstreams/0d90b808-fe89-4260-9de5-e1ba30c3899c/content
[tuhh]: https://tore.tuhh.de/entities/publication/f0fb35bd-6973-40d4-b2fb-c727a39aab85
[chalmers-6dof]: https://research.chalmers.se/en/publication/252516
[lheea]: https://hal-cnrs.archives-ouvertes.fr/LHEEA/hal-04375824v1
