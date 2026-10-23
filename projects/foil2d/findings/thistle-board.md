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

## Where the study stands (updated 2026-10-23, after the XFOIL screen)

**No CFD answer yet.** XFOIL (2D panel method with e^N transition) says
NACA 0006, the baseline, is already about as good upwind as any section
tried. The trade is upwind against downwind:
* **NACA 6-series.** They lose 3-5 % upwind at Tu 1 % (14-18 % at Tu
  0.1 %), and have 12-20 % less drag at 0° from 7.5 kn.
* **Parallel-sided (plank) boards.** These lose 3-41 % upwind. The less
  flat, the better.

XFOIL under-predicts drag at Re 3e6 by 2-25 % and can't be trusted for
maximum lift, so the CFD decides.

1. `thistle-mesh` (96 cases) **submitted 2026-10-23**: run 20261023-052134,
   image f3cf606.
2. `thistle-validation-r824` is ready. It is submitted after the mesh level
   is chosen.
3. The CFD comes in two stages (split at the user's request, 2026-10-23).
   Both are submitted after the mesh level is set.
   * `thistle-screen`: all 8 sections, the 20 points per section and Tu
     that can reject a section (1, 3, 5 kn at 0, 1, 2, 4, 6, 8°; 15 kn at
     0 and 2°), Tu 0.1 and 1 %: 320 cases.
   * `thistle-extend`: the other 37 points of the full grid, for the
     survivors only. The two runs rank together.
4. In thistle-mesh, the plank board diverged on the coarse mesh at 5 kn and
   4° (C_l 1e34 after 60 s, stopped by the divergence guard). Its finer
   meshes are still running.

## 2026-10-23: XFOIL screen and Report 824 check

**Report 824 against XFOIL, Re 3e6.** These are XFOIL polars of the true
6 % sections against the digitised smooth-model data
(validation/naca6_r824*.csv), with drag compared at the measured C_l,
|C_l| ≤ 0.5.

| section | C_d min, Report 824 | C_d at C_l 0, XFOIL Ncrit 9 | mean C_d error, Ncrit 9 / 11 / 13 |
|---|---|---|---|
| 0006 | 0.0045 | 0.0036 | −11 / −19 / −16 % |
| 63-006 | 0.0041 | 0.0034 | −14 / −19 / −22 % |
| 64-006 | 0.0038 | 0.0033 | −10 / −13 / −25 % |
| 65-006 | 0.0035 (bucket, extra file) | 0.0031 | −2 / −6 / −18 % |
| 66-006 | 0.0031 | 0.0028 | −7 / −20 / −24 % |

* **Drag.** XFOIL under-predicts drag at every Ncrit, least at Ncrit 9. It
  keeps the five sections in Report 824's order of minimum drag, but
  compresses the differences.
* **Maximum lift.** XFOIL's C_l,max for these 6 % sections ranges
  0.26-1.08 depending on Ncrit, against 0.83-0.84 measured: unusable.
* **Decision.** XFOIL rankings don't veto on stall margin
  (`stall_veto=False`); only the CFD does.

**Loads check.** XFOIL's baseline at α_n 1/2/4° and rake 10° gives the
light, working and high loads of `boardrank`:
* **1 kn:** 5 / 20 / 32 N;
* **3 kn:** 110 / 176 / 296 N;
* **5 kn:** 219 / **456** / 835 N.

The 5 kn working load matches the righting-moment estimate (about 440 N,
methodology §3).

**Named sections** (`boardrank screen`, 26 sections at 1 in, V_n grid of
1-15 kn, 0-12° in 0.5° steps; run in
runs/section-design/thistle-xfoil-20261023/named). Upwind mean D_h against
NACA 0006 [%] at rake 10° (negative = less drag), and downwind D_h at 0°
over 1-15 kn [%]:

| section | up Tu 0.1 | up Tu 0.5 | up Tu 1 | up tripped 5 % | down Tu 0.1 | down Tu 1 | down tripped |
|---|---|---|---|---|---|---|---|
| SD8020 | −1.0 | −0.1 | +0.2 | +0.2 | +1.5 | +2.2 | −0.1 |
| cst-opt2 (IOM) | +0.5 | −0.8 | +0.9 | −0.2 | +6.3 | +5.4 | −0.2 |
| HT35 (IOM winner) | +1.0 | −0.1 | +0.9 | −0.6 | +5.7 | +5.7 | −0.4 |
| NACA 0006-64 | +4.8 | +3.9 | +1.7 | +0.8 | +0.3 | −5.0 | +0.4 |
| NACA 63-006 | +11.9 | +4.3 | +2.7 | +0.2 | −1.2 | −12.8 | −1.8 |
| NACA 64-006 | +10.3 | +5.3 | +3.6 | +0.6 | −2.4 | −15.9 | −1.9 |
| NACA 65-006 | +15.3 | +8.5 | +5.3 | +1.9 | −3.1 | −19.4 | −1.8 |
| NACA 66-006 | +20.0 | +11.6 | +7.0 | +3.0 | −0.5 | −20.9 | −1.1 |
| NACA 0006-45 (16-series) | +23.2 | +17.7 | +10.9 | +8.6 | +9.3 | −18.0 | +0.9 |
| NACA 0006 at 7/8 in | +2.8 | +1.1 | −0.1 | −0.2 | −5.0 | −3.0 | −1.6 |
| NACA 0006 at 3/4 in | +10.3 | +4.3 | +1.3 | +0.9 | −10.1 | −6.2 | −3.2 |
| plank-typical (assumed) | +41.0 | +29.6 | +21.5 | +6.8 | +142 | +57.5 | +9.3 |

* **Rake.** It doesn't change the ranking: at Tu 1 %, rake 5° and 15° move
  every section's upwind figure by 0.5 % or less.
* **6-series.** Their loss is at the working and high loads: at Tu 0.1 %,
  64-006 is +14 % at the working load and +19 % at the high load. The
  working load, C_l ≈ 0.2, sits past the edge of their low-drag bucket
  (Report 824: about ±0.15 at Re 3e6). At Tu 1 % the bucket is mostly gone
  on every section, so the penalty drops to 3-5 %.
* **Thinner.** 7/8 in is level upwind at Tu 1 % and 3-5 % better
  downwind; 3/4 in loses upwind at low Tu. The class allows down to
  3/4 in on wood-lead boards; this was not in the agreed scope (at most
  1 in, run at 1 in).

**Parallel-sided family** (Saporito's parametrisation: 144 shapes, nose
length le 0.1-0.3, tail length te 0.2-0.5, nose radius r 0.05-0.5 t, tail
angle a 0.2-1 A_REF; runs/section-design/thistle-xfoil-20261023/parallel).
* **Best shape.** Long tapers and a short flat: le 0.3, te 0.5 (flat 20 %
  of the chord), r 0.05, a 0.2 (`parallel-l30-t50-r05-a20`).
* **Against NACA 0006.** It is +7.0 / +2.7 / +0.4 % upwind and +7.1 /
  +1.1 / +0.5 % downwind (Tu 0.1 % / Tu 1 % / tripped).
* **The trend.** Every step towards a foil (longer tapers, smaller nose,
  finer tail) helps. As Saporito found, a parallel-sided board at best
  matches a NACA section; it doesn't beat it.

**Local CFD check** (thistle-mesh cases 3 and 6 in Docker, coarse mesh,
Tu 0.1 %, NACA 0006 at 2°). Both converged.

| speed | C_l | C_d | iterations | time | y+ max |
|---|---|---|---|---|---|
| 5 kn | 0.246 | 0.00418 | 2142 | 14 min | 2.3 |
| 15 kn | 0.208 | 0.00440 | 2318 | 15 min | 1.9 |

* **C_l at 5 kn.** It is above thin-aerofoil theory (0.22), as XFOIL's is
  (0.264 at Ncrit 9). A long laminar run on the pressure side adds lift.
* **C_d at 15 kn.** It is 13 % under Report 824's 0.0051 at C_l 0.21 and
  Re 3e6. That is the coarse mesh at Tu 0.1 %; thistle-validation-r824
  checks it properly.

**Proposed CFD candidates for thistle-screen** (for the user to decide):

| # | section | why |
|---|---|---|
| 1 | NACA 0006 | baseline |
| 2 | SD8020 | XFOIL's upwind leader at Tu 0.1 %, but its nose is half NACA's: XFOIL's blind spot in the IOM work (leading-edge bubble) |
| 3 | HT35 | the IOM winner, level with the baseline here |
| 4 | NACA 63-006 | the best 6-series compromise: +2.7 % up, −12.8 % down at Tu 1 % |
| 5 | NACA 64-006 | laminar flow; also the validation section |
| 6 | NACA 0006-64 | modified 4-digit with its crest at 40 %: a smaller downwind gain for a smaller upwind loss |
| 7 | parallel-l30-t50-r05-a20 | the best plank-style board |
| 8 | plank-typical | what a simple home-built board might be (assumed shape) |

Options: swap #6 for NACA 0006 at 7/8 in, if a thinner board is in scope.
Each candidate is 57 points × 2 Tu = 114 cases, about $3-6 (estimate).

**Decided (user, 2026-10-23).**
* The CFD is split into a screen of all eight sections at the points that
  can reject one (`thistle-screen`, 320 cases instead of 912), then the
  full grid for the survivors (`thistle-extend`).
* The proposed eight sections go into `thistle-screen`.
* The vetoes and tie-break stay as proposed (methodology §4): a stall
  margin under 2° and more than 1° under NACA 0006's (CFD only), a downwind
  loss larger than the upwind gain; within ±1 % upwind, downwind decides.

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
