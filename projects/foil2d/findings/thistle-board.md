# thistle-board: findings log

What is the best section for a Thistle's centreboard? The Thistle is a 17 ft
one-design dinghy. This is the IOM fin-section work
([custom-section.md](custom-section.md)) applied to a full-size dinghy, a
3-30 times higher Reynolds number. The method is in
[methodology-thistle.md](../methodology-thistle.md); the inputs are in
[design/thistle.yaml](../design/thistle.yaml).

Newest entry first; entries are not rewritten later, except "Where the study
stands", which is updated in place. Results live in `runs/` (not in git), so
the numbers that support a conclusion are copied here. Symbols follow
[docs/nomenclature.md](../../../docs/nomenclature.md) (S_h, D_h = D_v + D_i,
leeway β_Y, section angle α_n, rake Λ).

## Where the study stands (updated 2026-10-23, set-up)

No CFD has run yet. The tools, sections and the first study are ready:

1. `thistle-mesh` picks the mesh level at Re up to 3.5e6. Not submitted.
2. `thistle-validation-r824` checks the transition model against NACA
   Report 824 at Re 3e6. Waiting for the digitised data.
3. XFOIL screen of about 30 sections and a parallel-sided family. Local; then
   the **user picks the CFD candidates and agrees the vetoes**.
4. `thistle-screen` (CFD, 8 sections × 57 points × Tu 0.1/1 %), then the
   optional optimisation and the finalist checks (methodology §4).

## 2026-10-23: study set-up

**Question and scope (user).** The best section for the Thistle
centreboard, at 0-5 kn upwind and 0-15 kn downwind. The rake needed
verifying, and so did the chord the water actually flows along.

**What the class rules say** (TCA Green Book, effective 2026-02-28, Art. XII;
https://thistleclass.com/official-rules-of-the-tca/):
* **Thickness.** A wood-lead board is at least 3/4 in thick, and covered to
  at most 1 in overall (XII.5). Fibreglass boards come from approved
  builders (XII.4).
* **Shape.** Every board "must meet the dimensions and shape as shown on the
  Official Plans" (XII.2). The plans are not online, so whether they fix the
  section is not known. **Check with a class measurer before building a
  board.**
* **Rake.** The board hangs from rollers on top of the trunk (no pivot pin;
  Good Old Boat, "Turning a derelict Thistle into a ThistleCruiser"). It may
  be pulled down and held back by a line, but nothing may make it hang more
  vertically than it naturally does (XII.9), and no cocking device is
  allowed (XII.10).
* **No published angle.** No source gives the rake. The user's 5-15° is
  kept as the bracket.
* **Rudder.** At most 7/8 in thick below the break-point line (2025
  Nationals measurement form).
* **Prior work.** No published Thistle board section was found. Saporito et
  al. (2020, JMSE 8(9) 677) studied parallel-sided boards (470, 420,
  Optimist) with k-ω SST + γ transition: the best thin parallel-sided
  sections were about level with NACA 4-digit sections at Re 9e5-1.5e6 and
  C_L 0.4, and 13 % worse at 0°.

**User decisions (2026-10-22/23).**

| question | answer |
|---|---|
| section freedom | free shape, at most 1 in thick |
| 18 in chord | measured square to the leading edge; rake unknown: assume 10°, check 5° and 15° |
| downwind | board fully lowered, same rake as upwind (first answer: half raised below 10 kn; then "disregard the half raised fin downwind") |
| ranking | upwind first: drag at equal side force plus stall margin; downwind as tie-break or veto |
| baseline | NACA 0006 at 1 in (today's section unknown) |
| water | fresh, 20 °C |

**Chord the water flows along.** c_n / cos Λ = 18.07, 18.28 and 18.63 in
at 5, 10 and 15°, through a section 5.53, 5.47 and 5.37 % thick. The study
instead runs the board's own section (18 in, 5.556 %) at V_n = V_b cos Λ
(simple sweep, methodology §2). At these angles both views rank sections
alike, and this one reuses every CFD point for any rake.

**Method decisions** (methodology-thistle.md):
* **Speed grid.** V_n for V_b = 1-5, 7.5, 10, 12.5 and 15 kn: Re 2.3e5 to
  3.5e6.
* **Angles.** α_n 0-6, 8 and 10° upwind, 0-2° from 7.5 kn.
* **Loads.** α_n 1, 2 and 4° of the baseline (A). A righting-moment
  estimate puts the upwind working load at C_l ≈ 0.2-0.25, about 2°, at
  every speed. The IOM's working load was 4°.
* **Transition.** kOmegaSSTLM at Tu 0.1 and 1 %. Finalists also run at
  Tu 2 % and fully turbulent.
* **No race time.** There is no Thistle resistance curve, so drag and
  leeway are reported apart.

**Assumptions** (A in the files):
* rake 10° (bracketed 5-15°);
* exposed span 1.24 m along the leading edge;
* span efficiency e = 0.9 with the hull as a reflection plane;
* the loads (above);
* equal weight for every speed;
* the plank-board shape (`plank-typical`: le 0.1, te 0.25, nose radius
  0.5 t, tail angle 0.6 A_REF);
* the vetoes (stall margin under 2° and 1° under the baseline's; a downwind
  loss larger than the upwind gain);
* 2D sections stand for a board whose planform and tip are ignored.

**Sections prepared** (all 1 in on 18 in; geometry/README.md):
* NACA 0006 (the baseline).
* NACA 63-, 64-, 65- and 66-006. They are fitted to their Report 824
  tables with the nose radius held, because a spline through the 26
  stations makes it 20 % small.
* NACA 0006-45 (the 16-series shape) and HT35.
* `plank-typical`.
* Saporito's best thin family, `parallel-l20-t40-r10-a20`.

**Tools.** `iomcfd.boardrank`: the sweep mapping, the ranking, the XFOIL
screen, the calibration and the optimiser. `sectiondesign.parallel_sided`,
the parallel-sided family. `tools/naca6_006.py`. foil2d steady cases now
checkpoint on GCP Spot VMs, because high-Re cases run for hours.

**Cost estimate** (not measured; c3d-16 Spot ≈ $0.02 per case-hour):

| stage | cost |
|---|---|
| mesh | ≈ $5 |
| validation | $1-3 |
| CFD screen | $25-50 |
| optimisation | $9-17 |
| finalists | $8-19 |
