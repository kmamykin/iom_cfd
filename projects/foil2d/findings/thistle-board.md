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

## Where the study stands (updated 2026-10-25, corrected)

**Correction: the 18 in chord was wrong, and the NACA 0006 answer with it.**
The official plans (Thistle book, shown by the user 2026-10-25) give a
tapered board: 15 1/4 in at the break point to about 10 in near the tip,
13 3/16 in at mid-span, 53 in long below the break point, 1 in thick at
most. The study assumed a rectangular 18 in board. NACA 0006 was the 1 in
section on 18 in; it is not the answer for the real board (entry below).

**For the real board: NACA 0007, as the Thistle book suggests.** On the
plans' 13 3/16 in mid-span chord it is the 4-digit section near the class
thickness (0.92 in). A quick XFOIL check on that chord (entry below) finds
the 4-digit sections 0006-0007 within about 1 % of each other upwind and no
section better upwind at low turbulence. XFOIL only: trends, not CFD
numbers. Above about 14.3 in of chord (the top 8 in or so below the break
point) NACA 0007 would exceed 1 in, so the thickness is capped there.

**What still stands from the CFD (at 18 in).** The family trends, expected
to carry over to the real chord but not re-run: the laminar NACA 63-006 and
64-006 lose upwind at the calibrated Tu inputs (9-11 % at Tu 0.3 %, 2-3 % at
0.6 %) and gain 5-8 % downwind; parallel-sided boards lose both ways; the
model and Tu calibration (Report 824) are unaffected. The CFD's absolute
numbers are for a board with about a third more area than the plans' (an
estimate).

**How we got here.**
1. The XFOIL screen.
2. `thistle-mesh`, which picked the fine mesh.
3. `thistle-validation-r824` and `thistle-tu-calibration`: the model
   matches Report 824 at Tu 0.3 % for 0006 and about 0.45 % for 64-006.
4. `thistle-screen`: 8 sections at Tu 0.1 and 1 %. It rejected the two
   parallel-sided boards, and the user dropped HT35, SD8020 and 0006-64.
5. `thistle-extend`: 3 sections, the full grid, Tu 0.3 and 0.6 %.

The Tu literature is in docs/research/turbulence-intensity.md.

**Left open.**
* What a lake's Tu means as a model input. The calibrated 0.3-0.6 % is a
  lower bound, and Tu 1 % is a rough-water bound. This would only matter
  for a board sailed mostly in chop, where the 6-series catch up.
* The optional rough-water check and CST optimisation (thistle-extend
  entry) were not run.
* A shorter, thicker board at 1 in (what-if, entry below): XFOIL says less
  board drag but about 1.5° more leeway for NACA 0009 on 11.11 in; not taken
  to CFD.

## 2026-10-25: the official plans: the 18 in chord was wrong

**What the plans show** (Thistle book, image shared by the user; read from
the drawing, not measured): a tapered board, 16 3/4 in at the top by the
roller, 15 1/4 in at the break point, then 13 7/8, 13 1/4, 12 15/16 and
10 1/16 in at 11 3/4 in spacing, 6 in more to the tip (1 in corner radius
at most); A = 53 in (+1/4, −3/4) from the break point to the tip; the
nominal chord Y = 13 3/16 in (+1/4, −1/2) at A/2; 1 in thick at most. A
hatched section is drawn at mid-span, and the book suggests NACA 0007.

**Consequences.**
* **The study's premise was wrong.** It assumed a rectangular 18 in board
  (user's first description), 1.24 m along the edge. The plans have no
  18 in chord. The exposed area from the break point down is about
  655 in² (0.42 m², trapezoids between the stations, the last 6 in taken
  as about 6 in of mean chord: an estimate), against the 0.57 m² assumed:
  about a quarter less. Where the break point sits relative to the hull was
  not checked.
* **The NACA 0006 recommendation is invalid.** It was the 1 in section on
  18 in (t/c 5.56 %). On the plans' chord the 1 in 4-digit section is
  about 7-7.6 %: NACA 0007 is 0.92 in on 13 3/16 in.
* **Higher working lift** (estimate): for the righting-moment estimate of
  about 440 N at 5 kn the real board works at C_l about 0.3 instead of
  0.24, where Report 824 puts the 6-series further behind the 4-digit
  sections (+14 to +20 % at C_l 0.2-0.3).
* **Taper and the 1 in limit.** NACA 0007 is 1.07 in thick at the 15 1/4 in
  break-point chord, over the limit; it fits below about 14.3 in of chord,
  roughly 8 in below the break point. A builder caps the thickness at 1 in
  above that.

**XFOIL check on the plans' chord.** `python -m iomcfd.boardrank --design
projects/foil2d/design/thistle-plan.yaml screen naca0006 naca0008
naca0007@0.07584 naca0009@0.07584 file:naca63-006.dat@0.07584
file:naca64-006.dat@0.07584 file:ht35.dat@0.07584` (chord 13 3/16 in,
span 53 in read as the exposed span along the edge (A), baseline the
book's NACA 0007, loads its side force at 1/2/4°, rake 10°; 98 s; output in
runs/section-design/thistle-xfoil-plan-chord-20261025). ΔD against NACA
0007 [%] at Tu 0.1 / 0.5 / 1 % and tripped at 5 % chord:

| section on 13 3/16 in | thickness | upwind | downwind, 0° over 1-15 kn |
|---|---|---|---|
| NACA 0007 (the book) | 0.92 in | 0 | 0 |
| NACA 0006 | 0.79 in | +0.8 / 0.0 / −0.7 / −1.0 | −6.7 / −5.7 / −4.2 / −2.3 |
| NACA 0007 scaled to 1 in (7.58 %) | 1.00 in | +1.1 / +0.6 / +0.7 / +0.7 | +4.0 / +3.2 / +2.4 / +1.4 |
| NACA 0008 | 1.06 in (over the limit) | +1.9 / +1.1 / +1.3 / +1.3 | +6.8 / +5.3 / +4.0 / +2.4 |
| NACA 63-006 at 1 in | 1.00 in | +6.5 / +2.4 / +1.1 / −0.1 | +6.2 / −5.8 / −12.2 / −1.0 |
| NACA 64-006 at 1 in | 1.00 in | +8.1 / +3.4 / +1.7 / 0.0 | +5.7 / −7.5 / −14.8 / −1.1 |
| HT35 at 1 in | 1.00 in | +1.1 / +1.3 / +2.0 / +0.2 | +11.0 / +11.4 / +8.9 / +0.9 |

(NACA 0009 scaled to 7.58 % is the same shape as NACA 0007 scaled to it,
and gives the same numbers.)

* **The 4-digit sections 0006-0008 are within about 2 % upwind**, below
  what the CFD could resolve (about 3 %). Thinner gains a little downwind
  in XFOIL. Nothing beats NACA 0007 upwind at low turbulence; the 6-series
  gain downwind only at the higher settings, as at 18 in. Δ leeway within
  ±0.1° except the 6-series at low Tu (+0.2 to +0.4°).
* **Confidence low to medium:** XFOIL under-predicts drag at these Reynolds
  numbers (2-25 % against Report 824) and cannot predict stall for these
  sections; the trend matches the 18 in CFD.

**Decided (user, 2026-10-25).** The 18 in assumption invalidates the NACA
0006 finding; the website page says so in its abstract and stays online,
off the front page. The book's NACA 0007 is the supported section. No CFD
re-run at the plans' chord.

## 2026-10-25: what-if, a shorter chord at 1 in (XFOIL)

**Question (user).** NACA 0009 on a chord shortened to 11.11 in, so it is
still 1 in thick: better than NACA 0006 on 18 in?

**CFD run cancelled.** `thistle-0009-short` (134 cases, the extend settings,
run 20261025-170222 on n2-standard-16) was deleted after about 9 minutes:
10-20 h and $10-20 (estimates) was too much for a first look (user). Its
partial results are not used. The study file stays for later.

**XFOIL instead.** `boardrank screen naca0007 naca0008 naca0009 naca0010
naca0012 --chord SPEC=METRES` (new: a section's own chord, which sets its
Reynolds number and, in `board_forces`, its area; the span stays 1.24 m).
Each section is on the chord that makes it 1 in thick, against NACA 0006 on
18 in. 90 s; output in runs/section-design/thistle-xfoil-short-chord-20261025.

ΔD against NACA 0006 on 18 in [%], rake 10°, at Tu 0.1 / 0.5 / 1 % and
tripped at 5 % chord; Δ leeway in degrees at Tu 0.5 %:

| section, chord | upwind | downwind, 0° over 1-15 kn | Δ leeway |
|---|---|---|---|
| NACA 0007, 14.29 in | −2.5 / −5.6 / −6.4 / −8.4 | −8.8 / −12.9 / −14.7 / −14.0 | +0.63° |
| NACA 0008, 12.5 in | −3.5 / −8.1 / −9.2 / −12.3 | −12.2 / −18.7 / −20.7 / −20.8 | +1.08° |
| NACA 0009, 11.11 in | −4.0 / −9.8 / −11.3 / −15.2 | −14.6 / −22.9 / −26.4 / −26.1 | +1.55° |
| NACA 0010, 10 in | −4.0 / −10.9 / −12.6 / −17.2 | −15.9 / −26.0 / −30.2 / −30.3 | +2.04° |
| NACA 0012, 8.33 in | −2.5 / −11.2 / −13.4 / −18.5 | −17.4 / −30.4 / −35.7 / −36.5 | +3.19° |

* **Less board drag, more leeway.** A shorter board has less area, so less
  friction; for the same side force it works at a higher lift coefficient.
  NACA 0009 on 11.11 in needs α_n about 6.5° at the high load where NACA 0006
  on 18 in needs 4°, and 3.4-3.9° at the working load against 2.2-2.4°.
  Induced drag is the same (same span, same side force).
* **Downwind is a clear gain** in XFOIL: −15 to −26 % for NACA 0009, close to
  its 38 % smaller area.
* **Upwind the leeway probably eats the gain.** There is no Thistle VPP, so
  this is a rough break-even estimate, not a result: close-hauled at about
  45°, 1.5° more leeway costs about tan 45° × 1.5° ≈ 2.6 % of VMG. A 10 %
  cut in board drag is worth about 0.5 × 10 % × (the board's share of upwind
  resistance) in speed: 1.25 % at a 25 % share, 2.5 % at 50 % (shares
  assumed, not known). So upwind it breaks even only if the board makes
  about half the boat's resistance; the hull's own side force at the larger
  leeway is not counted either way.
* **Confidence low.** XFOIL under-predicts drag at these Reynolds numbers
  (2-25 % against Report 824) and its maximum lift is unusable, so its stall
  margins (1-4°) are left out; the 12 % section's margin collapses in every
  variant. The trend (less drag, more leeway) is basic and robust; the sizes
  are not.
* **Class.** A shorter board is probably not class-legal (XII.2).

**Decision.** Not pursued to CFD unless the downwind gain or a leeway cost
model makes it interesting (user's call).
Superseded in part the same day: the plans fix the planform (entry above),
so a shorter board is not an option within the class.

## 2026-10-25: thistle-extend, run 20261024-154540

**Setup.**
* **Sweep.** NACA 0006 (the baseline), 63-006 and 64-006, all at 1 in
  (t/c 5.56 %) on the 0.4572 m normal chord.
  * Tu 0.3 and 0.6 %, the band the calibration found.
  * The full 57-point grid: V_b 1-5 kn at α_n 0-6, 8 and 10°, and 7.5-15
    kn at 0-2°. V_n = V_b cos 10°.
* **Solver.** kOmegaSSTLM, steady, fine mesh, conv_window 1000, max_iter
  12000.
* **Compute.** GCP c3d-standard-16 Spot, image af02c27 (git 8ec1ae1),
  `--max-hours 14`.
  * 19.6 h wall; 1271 case-hours, median 206 min per case.
  * About $29 at docs/cloud-gcp.md's $0.0225 per case-hour (an estimate,
    not billed figures).
* **History.** This is the first run of this study, with no cases shared
  with thistle-screen (Tu 0.1 and 1 % there).
* **Ranking.** `python -m iomcfd.boardrank --design thistle cfd
  results.csv`, output in `runs/thistle-extend/20261024-154540/boardrank/`.
  Board drag D_h = D_v + D_i is compared at equal S_h, with the loads being
  the S_h NACA 0006 makes at α_n 1, 2 and 4° at each speed and Tu.

**Outcome.** All 342 tasks succeeded: 281 ok and 61 not converged.
* **Not converged.** All 60 cases at 8 and 10° (every section, speed and
  Tu), plus NACA 0006 at 1 kn, 3°, Tu 0.3 %. They ran all 12000
  iterations, and the window means are used.
* **Unsteady.** 113 cases. That is 59 of the 60 at 8-10°, and 54 below 8°,
  of which 35 are NACA 0006's (21 at Tu 0.3 %), mostly at 0-3° and 1-3 kn.
  Their C_d std is 2-8 % of C_d, up to 11 % (1 kn, 3°).
* **Time-outs.** None (the screen lost 8 cases to the 8.5 h limit).

### Conclusions

1. **NACA 0006 has the least board drag upwind at both calibrated Tu
   levels.**
   * At Tu 0.3 %, 63-006 is +9.3 % and 64-006 +10.6 % (mean of 15 points).
     NACA 0006 is ahead at 13 and 14 of those 15 points.
   * At Tu 0.6 %, they are +2.4 % and +2.9 %, and NACA 0006 is ahead at 8
     and 9 of 15.
   * Confidence **high** for Tu 0.3 %; **medium** for 0.6 %, where the
     margin is near the mesh uncertainty (about ±3 %).
2. **The 6-series lose at the working and high loads and gain only at the
   light load.**
   * At Tu 0.3 %, the gap is +12 to +16 % at the working and high loads,
     and +3 % at the light load.
   * At Tu 0.6 %, it is +0.4 to +14 % at the working and high loads, and −4
     to −5 % at the light load.
   * By speed, at Tu 0.6 % the 6-series are ahead at 4-5 kn (−1 to −5 %)
     and behind at 1-3 kn (+3 to +10 %).
   * Confidence **medium**: the light-load gaps are smaller than the
     baseline's own oscillation at those points.
3. **Downwind the 6-series have less drag, almost all of it at high speed:
   from 10 kn at Tu 0.3 %, and from 7.5 kn at 0.6 %.**
   * Over 1-15 kn at 0°: 63-006 −4.6 / −6.4 % and 64-006 −5.3 / −7.9 %
     (Tu 0.3 / 0.6 %).
   * At 7.5-15 kn: −10 to −17 %.
   * At 4-5 kn they have *more* drag (+1 to +8 %), and at 1-3 kn 2-4 %
     less.
   * Confidence **medium**: the zero-lift drag depends on where the flow
     turns turbulent, which moves with Tu and speed (Learnings).
4. **By the agreed rule, NACA 0006 wins in 5 of the 6 Tu × rake cases.**
   The upwind gap at rake 5 / 10 / 15° is:
   * Tu 0.3 %: +7.4 / +9.3 / +11.4 % for 63-006 and +8.6 / +10.6 / +12.7 %
     for 64-006.
   * Tu 0.6 %: +0.7 / +2.4 / +4.2 % and +0.8 / +2.9 / +5.2 %.

   Only Tu 0.6 % at 5° rake falls inside the ±1 % window. Downwind then
   decides, for 64-006 (−7.9 %). No veto applies.
5. **The model's bias towards the 6-series does not change the upwind
   answer, and it removes most of their downwind gain.**
   * The calibration matched Report 824 with each section at its own
     input: NACA 0006 at Tu 0.3 % and 64-006 at about 0.45 %.
   * So 64-006 lies between its 0.3 and 0.6 % results, compared with NACA
     0006 at 0.3 %. Upwind that is +10.6 to +11.3 %, and downwind −5.3 to
     +4.8 %, about level.
   * Confidence **medium**: the calibration is at one Re (3e6) and on two
     sections; 63-006 was not calibrated.
6. **Report 824's measurements show the same trade.**
   * At Re 3e6 (true 6 %, quiet tunnel), at equal C_l, 64-006 has −11 %
     drag at C_l 0 and −8 % at 0.1.
   * It has +20 % at 0.2, +14 % at 0.3 and +8 % at 0.4.
   * The Thistle's upwind loads are C_l about 0.1-0.45, and downwind is
     C_l 0.
   * Confidence **high** for the direction, but at one Re only: 3e6 is
     about 13 kn, while upwind is 2.3e5-1.15e6.
7. **Stall margin vetoes none of the three.**
   * Every section, speed and Tu reaches maximum S_h at least 3.85° past
     the high load. NACA 0006 is at 4.0° (censored at 6° in 4 of 5 speeds
     at Tu 0.6 %).
   * Report 824 has C_l,max at about 8° for both sections, about 4° past
     the high load.
   * Confidence **low** for the values, which rest on unsteady,
     unconverged 8-10° points; **high** that no veto applies.
8. **The thistle-screen bounds held.** The upwind gap shrinks steadily
   with Tu: +10 to +12 % at 0.1 %, +9 to +11 % at 0.3 %, +2 to +3 % at
   0.6 %, and −0.2 % at 1 %. The screen's numbers are over 1, 3 and 5 kn
   only.

### Evidence

**Board drag against NACA 0006 [%]**, rake 10°, from
`boardrank/summary-*rake10.csv` and `upwind-*.csv`.
* Upwind: the mean and worst over 1-5 kn and the light, working and high
  loads.
* Downwind: 0° at 1-15 kn, then 7.5-15 kn alone.
* d α_n: the extra section angle at equal S_h.
* Stall margin: the minimum over speeds, in degrees past the high load
  (NACA 0006: 4.0).

| section | Tu | upwind | worst | light / working / high | d α_n [°] | downwind | 7.5-15 kn | stall margin [°] |
|---|---|---|---|---|---|---|---|---|
| 63-006 | 0.3 | +9.3 | +20.9 | +2.8 / +12.1 / +13.0 | +0.11 | −4.6 | −10.0 | 3.9 |
| 64-006 | 0.3 | +10.6 | +21.6 | +2.9 / +12.8 / +16.3 | +0.12 | −5.3 | −12.1 | 3.9 |
| 63-006 | 0.6 | +2.4 | +13.5 | −4.4 / +1.0 / +10.4 | +0.08 | −6.4 | −14.7 | 5.9 (censored) |
| 64-006 | 0.6 | +2.9 | +16.9 | −5.4 / +0.4 / +13.6 | +0.09 | −7.9 | −17.1 | 3.9 |

**Upwind by V_b** [%], mean over the three loads:

| section, Tu | 1 kn | 2 kn | 3 kn | 4 kn | 5 kn |
|---|---|---|---|---|---|
| 63-006, 0.3 | +3.1 | +9.5 | +13.8 | +12.2 | +8.0 |
| 64-006, 0.3 | +4.5 | +11.1 | +15.0 | +13.7 | +8.9 |
| 63-006, 0.6 | +3.3 | +8.9 | +5.1 | −1.2 | −4.4 |
| 64-006, 0.6 | +4.6 | +9.9 | +5.8 | −1.2 | −4.6 |

**Zero-lift drag C_d × 1e4** (results.csv, α_n 0°):

| V_b [kn] | 0006, 0.3 | 63-006, 0.3 | 64-006, 0.3 | 0006, 0.6 | 63-006, 0.6 | 64-006, 0.6 |
|---|---|---|---|---|---|---|
| 1 | 66.4 | 63.6 | 64.2 | 66.7 | 63.8 | 64.3 |
| 3 | 39.0 | 37.9 | 38.4 | 39.2 | 38.3 | 38.6 |
| 5 | 30.4 | 32.8 | 32.4 | 32.7 | 34.9 | 33.8 |
| 7.5 | 30.0 | 31.0 | 30.3 | 43.5 | 38.2 | 37.3 |
| 10 | 36.5 | 31.9 | 31.1 | 49.0 | 41.3 | 40.4 |
| 15 | 45.1 | 37.9 | 37.3 | 54.3 | 46.4 | 44.7 |

**Bias check**, each section against NACA 0006 at Tu 0.3 %, at that run's
loads.
* For the Tu 0.6 % row, the cases were re-ranked with
  `--loads boardrank/loads-CFDkOmegaSSTLMTu0.3rake10.csv`, output in
  `boardrank/tu06-at-tu03-loads/`.
* 64-006's calibrated input (about 0.45 %) lies between the two rows.

| section | upwind, at Tu 0.3 % | upwind, at Tu 0.6 % | downwind 0°, at 0.3 % | downwind 0°, at 0.6 % |
|---|---|---|---|---|
| 63-006 | +9.3 | +10.8 | −4.6 | +6.7 |
| 64-006 | +10.6 | +11.3 | −5.3 | +4.8 |

**Report 824, Re 3e6**, drag at equal C_l, interpolated in
validation/naca6_r824.csv:

| C_l | 0 | 0.1 | 0.2 | 0.3 | 0.4 |
|---|---|---|---|---|---|
| 0006 C_d | 0.00448 | 0.00464 | 0.00502 | 0.00554 | 0.00620 |
| 64-006 C_d | 0.00399 | 0.00426 | 0.00603 | 0.00631 | 0.00669 |
| 64-006 against 0006 | −11 % | −8 % | +20 % | +14 % | +8 % |

**Highlight `laminar-run`** (3 kn, report/highlight_laminar-run.png and
highlights.md). At 2°:

| section | C_l at Tu 0.3 / 0.6 % | C_d at Tu 0.3 / 0.6 % | upper surface turns turbulent near x/c (read from the figure) |
|---|---|---|---|
| NACA 0006 | 0.249 / 0.237 | 0.00406 / 0.00534 | 0.93 / 0.55 |
| 63-006 | 0.221 / 0.216 | 0.00435 / 0.00483 | 0.80 (short bubble from 0.74) / 0.65 |
| 64-006 | 0.221 / 0.216 | 0.00436 / 0.00477 | 0.80 (bubble from 0.74) / 0.65 |

* The 6-series have a sharper suction peak at the nose. Away from 0° they
  turn turbulent earlier than NACA 0006 at Tu 0.3 %.
* At Tu 0.6 % they turn turbulent later, but at equal S_h NACA 0006 is
  still ahead at 3 kn (+4 % for the 6-series), because it makes 10-13 % more
  C_l at 2°.
* At 0°, all three are laminar to about 0.8-0.95 at both Tu.

### Decisions

**Decided (user, 2026-10-25).**
* **NACA 0006 at 1 in is the answer, and the CFD is closed.** The board
  keeps the baseline section.
* The optional checks under Open questions are not run.
* The case for a 6-series board stays on record: rough water (Tu about
  1 %), or a sailor who weights the 7.5-15 kn legs above upwind. Then
  64-006 trades 2-11 % upwind for 10-17 % downwind.

### Assumptions

* **Rake.** 10°, bracketed 5-15° (no published value).
* **Board.** b_LE 1.24 m and e 0.9 (methodology-thistle.md). **Not
  verified.**
* **Loads.** NACA 0006's S_h at α_n 1, 2 and 4°, at each Tu, with equal
  weights over 1-5 kn and the three loads; no wind statistics.
* **Water.** Fresh, 20 °C.
* **Turbulence.** The Tu calibration (Report 824, Re 3e6, 0006 and
  64-006) is taken to hold from 2.3e5 to 3.5e6, and for 63-006. **Not
  verified.**
* **Report 824.** Digitised to about ±2e-4 in C_d; true 6 % sections, not
  5.56 %.
* **Surface.** Smooth boards, sharp trailing edges.

### Compromises

* **Steady RANS of unsteady flow.** NACA 0006's light and working loads
  come mostly from points flagged unsteady (9 of its 15 upwind points per
  Tu).
  * Its C_d oscillates by 2-8 %, so a 3 % gap at the light load is within
    the noise. The 12-16 % gaps at the higher loads are not.
* **Post-stall points.** All 8 and 10° points are not converged, so the
  stall margins are indicative. They only need to clear 2°, and all
  clear 3.85°.
* **Downwind interpolation.** The grid has no point between 5 and 7.5 kn,
  where NACA 0006's zero-lift drag jumps at Tu 0.6 % (32.7 to 43.5e-4).
  Interpolating in log Re smooths that over.
* **No roughness or fully turbulent finalists.** The planned Tu 2 % and
  kOmegaSST finalists (plan stage 6) were not run. The screen's Tu 1 %,
  effectively fully turbulent, stands in for rough water.
* **2D.** There are no tip, root or hull effects beyond the lifting-line
  D_i.

### Learnings

* **Physics.**
  * At 5.6 % thickness, the 6-series' low-drag range is narrow, C_l up to
    about 0.1 (Report 824 and these runs). A Thistle board upwind works at
    C_l 0.1-0.45, outside it.
  * NACA 0006's rounder nose keeps its suction side laminar longer at
    those C_l when the water is quiet.
  * Downwind at C_l 0 the 6-series gain only once NACA 0006's own laminar
    run is lost: from 10 kn at Tu 0.3 %, and from 7.5 kn at 0.6 %.
* **A surprise: the 6-series make less lift at the same α_n in the CFD.**
  At 2°, 3 kn and Tu 0.3 %, C_l is 0.221 against 0.249 (−11 %), so they
  need 0.08-0.14° more section angle. Report 824 doesn't show this: its
  fitted lift slopes over −4 to 4° are 0.104 per degree for 0006 and 0.109
  for 64-006. The CFD's extra leeway for the 6-series is probably a model
  effect, but the equal-C_l drag comparison in Report 824 points the same
  way without it.
* **Workflow.**
  * `--max-hours 14` stopped the time-outs: the longest case took 8.9 h.
  * After this run, the custom-profile merge replaced the steady
    checkpoints (every 1000 iterations) with the runner's signal writes,
    every 15 min. Later submits use those.
  * Runs now live in the main checkout's `runs/`, which this worktree
    links to.

### Open questions and next steps

1. **The user's decision.** Done: NACA 0006 accepted (2026-10-25).
2. **Class legality.** Only needed if a board with a different section is
   ever built; NACA 0006 needs no change.
3. **Optional, rough-water check.** About 114 cases, about $10 (an
   estimate): the three sections at Tu 1.5 % and kOmegaSST at the upwind
   points. Only worth running if the board is often sailed in chop.
4. **Optional, CST optimisation at 1 in** (plan stage 5). The target is
   NACA 0006's upwind with less zero-lift drag. Any gain is likely a few
   %, within the model's ±3-6 %, so it is not recommended.
5. **Highlights for a follow-up run**, if one is made: where NACA 0006
   loses its laminar run at 0°, which drives the downwind result.
   ```yaml
   highlights:
     - name: laminar-loss
       why: >
         NACA 0006's zero-lift drag jumps between 5 and 7.5 kn at Tu 0.6 % (32.7 to 43.5e-4)
         and between 7.5 and 10 kn at 0.3 %: where its laminar run is lost decides the downwind
         ranking (thistle-extend findings 2026-10-25).
       where: {aoa: 0, speed: [2.5331, 3.7997, 5.0663], foil: ["file:naca0006-t0556.dat",
                                                             "file:naca64-006-t0556.dat"]}
       compare: Tu
       views: [transition]
   ```

## 2026-10-24: thistle-screen, run 20261023-125405

**Run.** 8 sections × 20 points × Tu 0.1 and 1 %, fine mesh, image
af02c27, C3D Spot, 18 h.
* 312 of 320 cases have results: 275 ok and 37 not converged. 36 of the
  37 are at 8° and the other is at 6° (all near stall); they ran all
  12000 iterations.
* 8 cases are missing: they were stopped at the 8.5 h limit, all at Tu
  0.1 %. They are near-stall points and plank-board points at 3 kn
  (1-2°).
* Ranked by `boardrank cfd ... --up-kn 1 3 5 --down-kn 1 3 5 15`, output
  in `runs/thistle-screen/20261023-125405/boardrank/`.

Board drag against NACA 0006 [%] (negative = less drag). Upwind is the
mean over 1, 3 and 5 kn and the 1/2/4° loads; downwind is 0° over 1, 3, 5
and 15 kn, and at 15 kn alone. Stall margin is in degrees past the high
load; on a 2° grid it is coarse. Rake 10°, with the 5° and 15° upwind
figures in the last column.

| section | up, Tu 0.1 | up, Tu 1 | down, Tu 0.1 / at 15 kn | down, Tu 1 / at 15 kn | stall margin, Tu 0.1 / 1 | up at rake 5 / 15°, Tu 0.1; Tu 1 |
|---|---|---|---|---|---|---|
| NACA 0006 | 0 | 0 | 0 / 0 | 0 / 0 | 4.0 / 4.0 (censored) | 0 / 0; 0 / 0 |
| HT35 | +1.0 | +1.9 | −0.2 / +11.9 | +2.5 / +0.4 | 2.0 / 4.0 | −0.1 / −2.3; +1.6 / +1.1 |
| SD8020 | +2.2 | +0.8 | +0.7 / +2.9 | 0.0 / −1.8 | 3.9 / 2.0 | +0.5 / +0.4; +0.6 / +1.0 |
| NACA 0006-64 | +5.0 | −0.9 | +4.8 / −2.6 | −4.6 / +2.1 | 4.0 / 1.9 | +4.8 / +1.3; −1.6 / −1.1 |
| NACA 63-006 | +10.4 | −0.2 | −4.3 / −11.9 | −10.2 / −4.4 | 3.8 / 2.1 | +7.9 / +7.5; −1.0 / +0.6 |
| NACA 64-006 | +12.0 | −0.2 | −3.8 / −13.9 | −11.4 / −4.4 | 3.8 / 2.1 | +9.3 / +9.0; −1.2 / +0.8 |
| parallel-l30-t50-r05-a20 | +13.9 | +4.2 | +12.3 / −10.9 | +0.2 / −0.8 | 3.8 / 2.1 | +10.8 / +11.0; +3.6 / +3.5 |
| plank-typical | +63.4 | +35.0 | +75.8 / +122 | +45.2 / +16.1 | 1.2 / 1.7 | +62.5 / +55.6; +34.7 / +32.6 |

* **The two bounds disagree about the 6-series.**
  * At Tu 0.1 % (too laminar) NACA 0006 leads upwind, and 63-006 and
    64-006 are 10-12 % behind (15-17 % at 3-5 kn).
  * At Tu 1 % (effectively fully turbulent) 63-006, 64-006 and 0006-64
    are level or ahead upwind (−0.2 to −0.9 %; −1 to −5 % at 3-5 kn, +4 to
    +9 % at 1 kn). The two 6-series are 10-11 % ahead downwind and 0006-64
    5 %.
  * The calibrated Tu (0.3-0.6 %) lies between, so `thistle-extend`
    decides. Remember the model's 10-20 % bias towards the 6-series at low
    lift (calibration entry).
* **HT35 and SD8020 match NACA 0006** within the mesh uncertainty (about
  ±3 %) at both bounds. They are never ahead by more than that.
* **The two parallel-sided boards lose at both bounds.**
  * The plank board is +35 to +63 % upwind and +45 to +76 % downwind.
  * The best parallel-sided board is +4 to +14 % upwind. It loses 12 %
    downwind at Tu 0.1 % and breaks even at Tu 1 %.
* **Rake 5-15° changes upwind figures by up to 3 %** (HT35 at Tu 0.1 %:
  −0.1 to −2.3 %), but no ordering beyond that.
* **Stall margins.**
  * At Tu 1 % the sharp-nosed sections (6-series, 0006-64, SD8020,
    parallel) reach maximum side force about 2° past the high load (4°).
    NACA 0006 and HT35 are still rising at 8° (censored at 4°).
  * The validation found the model stalls 64-006 early. On this coarse
    2° grid the margins are indicative only; `thistle-extend` has 5, 6, 8
    and 10°.
* **By the agreed rule**, a section is rejected only if it is worse than
  NACA 0006 upwind beyond the mesh uncertainty (about 3 %) at both bounds.
  That rejects **plank-typical** and **parallel-l30-t50-r05-a20**.

**Decided (user, 2026-10-24).**
* `thistle-extend` runs **NACA 0006, 63-006 and 64-006** only. HT35,
  SD8020 and 0006-64 are dropped too: they never led beyond the mesh
  noise, or (0006-64) trade less than the 6-series.
* 342 cases (57 points × Tu 0.3 and 0.6 % × 3 sections), submitted
  2026-10-24: run 20261024-154540, image af02c27, C3D Spot,
  `--max-hours 14`.

## 2026-10-24: thistle-tu-calibration, run 20261023-221604

**Run.** NACA 0006 and 64-006 at their true 6 %, Re 3e6, kOmegaSSTLM,
fine mesh, inlet Tu 0.15, 0.3, 0.6, 1.0 and 1.5 % (decay control holds it
to the foil), 0-4°. Run on n2-standard-16, image af02c27, 3.9 h. All 40
cases succeeded. The Tu 0.05 % points are the validation run's.

**C_d against Report 824 at the computed C_l** [%]:

| Tu | 0006 at 0° | 1° | 2° | 4° | rms | 64-006 at 0° | 1° | 2° | 4° | rms |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 % | −40 | | −23 | −2 | 27 | −32 | | −39 | −1 | 29 |
| 0.15 % | −23 | −18 | −16 | −1 | 17 | −25 | −19 | −30 | +1 | 22 |
| **0.3 %** | **−3** | **0** | **0** | **+6** | **3** | −12 | −10 | −22 | +5 | 14 |
| 0.6 % | +20 | +29 | +27 | +22 | 25 | **+7** | **+19** | **+3** | **+11** | **12** |
| 1.0 % | +60 | +57 | +50 | +34 | 51 | +69 | +60 | +24 | +26 | 49 |
| 1.5 % | +62 | +57 | +49 | +31 | 51 | +79 | +63 | +23 | +23 | 53 |

C_l hardly moves with Tu (2°: 0.205-0.219; Report 824 0.235 for 0006 and
0.204 for 64-006).

* **The effective Tu that reproduces the quiet tunnel** is **0.3 %** for
  NACA 0006, within ±6 % at 0-4°. For 64-006 it lies between 0.3 and
  0.6 %, about 0.45 % (interpolated, not run).
* **Tu 1 % and above is effectively fully turbulent.** C_d at 1.0 and
  1.5 % is the same, close to kOmegaSST's (0006 at 0°: 0.0072-0.0073
  against SST's 0.0077).
* **Both of the screen's levels are off.** Tu 0.1 % is too laminar (about
  −20 to −30 % at low lift) and Tu 1 % too turbulent (+50 to +60 %). The
  calibrated band, 0.3-0.6 %, lies between.
* **The bias depends on the section.** At every Tu, 64-006's drag comes
  out 10-20 % lower relative to its measurement than 0006's does at C_l
  0-0.2 (Tu 0.3 %: −10 to −22 % against 0 to −3 %). So the model favours
  the 6-series at low lift by about that much. A 6-series gain over a
  4-digit section smaller than about 15 % at the working load or downwind
  is within the model's error.
* **Calibration only, not physics.** Report 824's tunnel had a very low
  Tu, about 0.03 %. The 0.3-0.6 % is what *this model* needs to reproduce
  a quiet, smooth test. A lake adds real turbulence on top: about
  0.1-0.3 % at 4-15 kn and more at 1-2 kn (docs/research/turbulence-intensity.md).
  So model inputs of about 0.3-0.6 % are a defensible lower bound for
  Thistle conditions; the screen's Tu 1 % is a rough-water bound.
* **Scope.** One Reynolds number (3e6) and two sections. The board runs
  from 2.3e5 to 3.5e6, and no data were found below 3e6 for these
  sections.

**Decided (user, 2026-10-24).**
* The screen (Tu 0.1 and 1 %) bounds the answer. A section is rejected
  only if it loses at both levels.
* The survivors run the full 57-point grid at the calibrated Tu 0.3 and
  0.6 % (`thistle-extend`, redesigned), and that decides the ranking.
* Near-stall cases need about 9.2 h, so `thistle-extend` is submitted with
  `--max-hours 14`.

## 2026-10-24: thistle-validation-r824, run 20261023-195013

**Run.** NACA 0006 and 64-006 at their true 6 %, Re 3e6, fine mesh, Tu
0.05 %, kOmegaSSTLM and fully turbulent kOmegaSST, 0-12°, on
c2d-standard-16, image af02c27, 3.3 h.
* 25 of 28 cases succeeded.
* The 3 failures are fully turbulent past stall: 0006 at 12°, 64-006 at
  10° and 12°. They diverged (C_l 1e18 to 1e51) and the guard stopped them.
* 10-12° under the transition model and 64-006 at 8° did not converge and
  oscillate.

Against Report 824 (validation/naca6_r824.csv, digitised: C_d ±0.0001,
C_l ±0.01). Drag is compared at the computed C_l, lift at the same angle:

| section, model | 0° C_d | 2° C_d | 4° C_d | 6° C_d | C_l at 2 / 4 / 6 / 8° (Report 824) |
|---|---|---|---|---|---|
| 0006, SSTLM Tu 0.05 % | −40 % | −23 % | −2 % | +1 % | 0.205 / 0.446 / 0.651 / 0.836 (0.235 / 0.446 / 0.646 / 0.828) |
| 0006, SST | +72 % | +55 % | +34 % | +18 % | 0.217 / 0.433 / 0.645 / 0.849; 1.034 at 10° (0.819) |
| 64-006, SSTLM Tu 0.05 % | −32 % | −39 % | −1 % | stalled: C_d 0.035 | 0.215 / 0.431 / 0.584 / 0.639 (0.204 / 0.433 / 0.631 / 0.814) |
| 64-006, SST | +90 % | +28 % | +26 % | | 0.220 / 0.439 / 0.653 / 0.645 (stalled) |

* **Lift is right below stall** for both models and sections: within
  about 0.03 of the measurements up to 6°, and for 0006 under the
  transition model up to 8°.
* **The transition model is too laminar at low lift.** At C_l 0-0.2 its
  drag is 23-40 % low, and it gives 64-006 a laminar bucket at C_l 0.2
  that the data put past the bucket's edge (Report 824: C_d 0.0061 there).
  At C_l 0.45-0.65 it is within 2 %. This is the bias Eça et al. (2022)
  describe at very low Tu (docs/research/turbulence-intensity.md);
  thistle-tu-calibration measures how much Tu removes it.
* **Fully turbulent is too draggy at low lift** (+18 to +90 %). The truth
  lies between the two models, nearer the transition model as C_l grows.
* **64-006 stalls early under the transition model.**
  * The model has C_l falling off past 6°, maximum about 0.64; the
    measurements reach about 0.83 at 8-9°.
  * NACA 0006, with its rounder nose, is right to 8°.
  * The screen's stall margins for the sharp-nosed sections (6-series,
    SD8020) may be pessimistic, so a stall veto on them needs care.
  * Fully turbulent SST misses stall the other way (0006: C_l 1.03 at
    10°). Steady RANS past maximum lift is not to be trusted.

## 2026-10-23: thistle-mesh, run 20261023-052134

**Run.** Image f3cf606 on GCP Spot, 7.4 h wall clock.
* 96 cases: 95 succeeded, 1 failed. The plank board diverged on the coarse
  mesh at 5 kn and 4° within 60 s (C_l 1e34; the divergence guard stopped
  it).
* 6 did not converge, all plank-board cases at 1 and 5 kn and 0-4°. They
  are flagged `unsteady`.
* Report: `runs/thistle-mesh/20261023-052134/report/` (not in git).

**C_d × 10⁴ by mesh level** (steady; Tu 0.1 %, kOmegaSSTLM unless marked):

| section | point | coarse | medium | fine | xfine | fine vs xfine |
|---|---|---|---|---|---|---|
| NACA 0006 | 1 kn, 0° | 66.4 | 66.6 | 66.6 | 66.2 | +0.6 % |
| NACA 0006 | 1 kn, 4° | 136.5 | 138.6 | 146.5 | 143.5 | +2.1 % |
| NACA 0006 | 5 kn, 0° | 32.4 | 31.4 | 31.0 | 30.8 | +0.7 % |
| NACA 0006 | 5 kn, 2° | 41.7 | 39.1 | 37.5 | 35.1 | +6.8 % |
| NACA 0006 | 5 kn, 4° | 87.5 | 83.6 | 85.8 | 96.1 (xfine unsteady) | −10.7 % |
| NACA 0006 | 15 kn, 0° | 36.6 | 34.9 | 33.5 | 26.9 (see below) | +24.5 % |
| NACA 0006 | 15 kn, 2° | 44.0 | 41.6 | 41.1 | 40.6 | +1.3 % |
| NACA 0006 SST | 5 / 15 / 15 kn, 0 / 0 / 2° | 88.6 / 74.3 / 76.7 | 88.5 / 74.2 / 76.3 | 89.0 / 74.6 / 76.7 | 89.5 / 75.1 / 77.2 | −0.6 to −0.7 % |
| NACA 64-006 | the 7 points | | | | | −1.0 to +2.4 % |
| plank-typical | the 7 points | | | | | −3.2 to +1.7 %, but +7.8 % at 1 kn, 4° |

* **Two xfine outliers.** Neither is a mesh effect.
  * 15 kn, 0°: the convergence test stopped the xfine case after 1239
    iterations, against 2286-4932 on the other levels. Its C_l is 0.00075
    on a symmetric section at 0°, and it oscillates (`unsteady`). So it
    stopped while its transition was still moving.
  * 5 kn, 4°: the xfine case settled into a different leading-edge bubble
    (C_dp 0.0049 against 0.0035-0.0039) and oscillates.
* **Transition moves aft with refinement** under the transition model.
  * NACA 0006 at 5 kn and 2°: x/c 0.72, 0.75, 0.78, 0.83 on the upper side,
    estimated from the steepest rise of C_f, and C_d falls with it. This
    point is still 6.8 % from xfine on the fine mesh.
  * At 15 kn and 0° the shift is smaller: 0.68 to 0.73.
  * The fully turbulent C_d is within 1.2 % on every level from medium up:
    the mesh resolves the turbulent boundary layer; it is the transition
    that is mesh-sensitive.
* **Medium is not enough.** It is 4-5 % off fine at the thin sections'
  working-load points (0006 and 64-006 at 5 kn and 2°, 15 kn), and 17-23 %
  off on the plank board at 1 kn and 4° and 5 kn and 0°.
* **Cost** (median and maximum wall time per case, kOmegaSSTLM):

  | mesh | median | maximum |
  |---|---|---|
  | coarse | 0.19 h | 1.0 h |
  | medium | 0.72 h | 2.4 h |
  | fine | 2.1 h | 3.2 h |
  | xfine | 4.0 h | 7.3 h |

  y+ max on fine is 2.0, at the leading-edge suction peak.
* **Concern for the validation.** The transition model at Tu 0.1 % keeps
  NACA 0006 laminar to x/c 0.7 at 15 kn and 0° (Re 3.5e6): C_d 0.0034 on
  the fine mesh. Report 824 measured 0.0045 at Re 3e6 in a quieter tunnel,
  and XFOIL at Ncrit 9 gives 0.0036. Both computations may be too laminar
  at these Reynolds numbers. `thistle-validation-r824` will measure it,
  because it matters for any section whose advantage is a longer laminar
  run (the 6-series).

**Decision.**
* **Mesh.** `mesh: fine` for thistle-screen, thistle-extend and the
  validation. Expect about ±2-3 % mesh uncertainty in drag, up to about 7 %
  where transition sits mid-chord at the working load. So upwind
  differences under about 3 % between sections are not resolved.
* **Convergence window.** `conv_window: 1000` (default 500), so a moving
  transition front doesn't pass the convergence test early. That costs
  about 20 % more iterations.
* **Screen submitted.** thistle-screen, 2026-10-23: run 20261023-125405,
  image af02c27, 320 cases. The user asked for it to go when this run
  finished.

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

**Figure.** `figures/thistle-screen-sections.pdf` shows the eight sections:
true scale, half-thickness against NACA 0006, noses and tails, a properties
table with the XFOIL estimates, and one sheet each. It is drawn by
`uv run python tools/thistle_sections_pdf.py
projects/foil2d/findings/figures/thistle-screen-sections.pdf <work dir>`.

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
