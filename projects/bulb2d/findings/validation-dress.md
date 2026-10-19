# validation-dress: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/validation-dress/<run id>/` (not in git), so the numbers that support
a conclusion are copied here. The study asks whether bulb2d (axisymmetric
RANS, kOmegaSSTLM) predicts the drag of a body of revolution at IOM
Reynolds numbers, against Dress's (1988) magnetically suspended laminar
body. Project: [README](../README.md); why:
[docs/research/bulb-design.md](../../../docs/research/bulb-design.md), Track B1.

## Where the validation stands (updated 2026-10-19, after run 20261019-020534)

* **kOmegaSSTLM at Tu 0.05-0.1 % follows Dress's drag curve, 10-30 % low.**
  It gets the fall in drag with Reynolds number; fully turbulent RANS
  doesn't (−45 % at low Re, +17 % at 1.34e6).
* **It under-predicts drag where the laminar layer separates**: its bubbles
  reattach within 0.01-0.05 L, where Dress saw separation from 0.50-0.55 L
  with reattachment only near the tail. Read bulb2d drag for a separating
  body as a lower bound, roughly 10-25 % low.
* **Pass criteria of the study:** C_D,wet within 10 % below Re_L 7e5: not
  met (−11 to −17 % at Tu 0.05 %). Separation at 0.50-0.55 at low Re: not
  met (0.63-0.65). The fall in drag above 7e5: met.
* Not yet tested: attached laminar friction on a slender body (Dress's body
  separates at every Re), a transient run, a mesh finer than fine.

## Run 20261019-020534 (2026-10-19, image 0884dd0, GCP, 32 cases)

**Setup.** As run 1, with the corrected body (x = 6.0 in: 1.3234 in) and
the whole study: six Re_L (3.6e5-1.34e6) × kOmegaSSTLM at Tu 0.05, 0.1, 0.2,
0.5 %, plus fully turbulent kOmegaSST, on medium (48,896 cells); mesh check
at 4.376e5, Tu 0.1 % on coarse (24,563) and fine (97,890). c3d-standard-16
Spot, one core per case.

**Outcome.** 32 ok. Two flagged unsteady (C_D swing over 1 % of the mean
in the last window): coarse at 4.376e5 and medium Tu 0.1 % at 1.34e6, both
with a standard deviation of 1-3 % of C_D. 1,019-2,904 iterations, 16-104
min per case (median 35), 21 case-hours in all.

### Conclusions

1. **The transition model reproduces the measured fall of C_D,wet with
   Re_L, at a level 10-23 % low at Tu 0.05 % and lower at higher Tu.**
   From 3.6e5 to 1.34e6 the measured C_D,wet falls by a factor 2.6; the
   model's at Tu 0.05 % by 2.6 too. The error (% of measured):

   | Re_L | measured | LM Tu 0.05 % | Tu 0.1 % | Tu 0.2 % | Tu 0.5 % | fully turbulent |
   |---|---|---|---|---|---|---|
   | 3.645e5 | 0.01179 | −11.1 | −13.6 | −17.5 | −26.9 | −44.6 |
   | 4.376e5 | 0.01201 | −16.8 | −20.1 | −24.3 | −35.8 | −47.5 |
   | 5.608e5 | 0.01121 | −16.6 | −21.5 | −28.0 | −43.0 | −46.1 |
   | 6.894e5 | 0.01050 | −22.6 | −28.0 | −35.0 | −50.6 | −44.4 |
   | 9.406e5 | 0.00786 | −22.6 | −29.7 | −37.0 | −52.0 | −29.2 |
   | 1.3405e6 | 0.00451 | −10.1 | −14.5 | −22.5 | −28.1 | +17.1 |

   Confidence: high for the trend; medium for the level (conclusion 4).
2. **Fully turbulent RANS is no bracket: it is too low at low Re and too
   high at high Re.** C_D,wet 0.0065 → 0.0053, nearly flat, attached to
   x/L 0.75-0.81.

   Confidence: high.
3. **The model's laminar separation sits at x/L 0.63-0.67 at every Re and
   reattaches within 0.01-0.05 L.** It moves aft with Re by about 0.03 (Tu
   0.05 %: 0.631 at 3.6e5, 0.664 at 1.34e6), as Dress saw. At 1.34e6 the
   bubble, 0.664-0.671 (Tu 0.05 %) to 0.685-0.733 (Tu 0.5 %), matches the
   oil flow at 1.2e6 (0.67 to 0.73) and the liquid crystals (0.63). At low
   Re Dress's separation was 0.50-0.55 with reattachment near the tail: the
   model is 0.1 L too far aft and reattaches far too soon. After
   reattachment the turbulent layer separates again at 0.65-0.71.

   Confidence: medium.
4. **The medium mesh is within 5 % of fine.** At 4.376e5, Tu 0.1 %: C_D,wet
   0.00959 / 0.00959 / 0.00913 on coarse / medium / fine (fine −4.8 %);
   separation 0.641 / 0.640 / 0.642, reattachment 0.672 / 0.665 / 0.664. The
   change is a quarter of the gap to the measurement, but not converged.

   Confidence: medium (one point).
5. **The typo fix changes nothing that matters**: 0.009592 against 0.009566
   in run 1 (Tu 0.1 %, 4.376e5, +0.3 %).
6. **The base pushes at low Re again** (−17 to −36 mN up to 5.6e5) and
   drags at 1.34e6 (+0.12 to +0.28 N): positive base pressure at low Re, as
   Dress measured.

   Confidence: low.

### Evidence

From `report/drag.md`; Cf and Cp in `report/surface.png`; the comparison
with validation/dress1988.csv recomputed from `results.csv`.

C_D,wet (medium):

| Re_L | LM Tu 0.05 % | Tu 0.1 % | Tu 0.2 % | Tu 0.5 % | fully turbulent |
|---|---|---|---|---|---|
| 3.645e5 | 0.01048 | 0.01018 | 0.00972 | 0.00861 | 0.00653 |
| 4.376e5 | 0.01000 | 0.00959 | 0.00909 | 0.00772 | 0.00631 |
| 5.608e5 | 0.00935 | 0.00880 | 0.00807 | 0.00639 | 0.00604 |
| 6.894e5 | 0.00813 | 0.00756 | 0.00683 | 0.00518 | 0.00584 |
| 9.406e5 | 0.00609 | 0.00553 | 0.00495 | 0.00377 | 0.00556 |
| 1.3405e6 | 0.00406 | 0.00386 | 0.00349 | 0.00324 | 0.00528 |

The friction share is 19-26 % (LM, Tu 0.05 %) below 7e5 and 36 % at 1.34e6;
fully turbulent 74-76 %.

### Decisions

* bulb2d's working setting: kOmegaSSTLM at Tu 0.05-0.1 % for the lower end
  of the drag and 0.5 % as the pond's upper end (unknown); not fully
  turbulent.
* A body whose laminar layer separates gets 10-25 % too little drag. Read
  B2's fat bulbs that way.
* Not pursued now: a transient check, Tu below 0.05 %, xfine.

### Assumptions

* As run 1 (Dress's C_D,wet without the base; water at the same Re_L).
* Dress's tunnel turbulence is unknown; the Tu sweep brackets it.

### Learnings

* On Spot c3d cores a medium case takes 16-104 min (median 35): the low-Tu
  cases converge slowest.

## Run 20261019-002930 (2026-10-19, git 58ba0c7-dirty, local Docker, 5 cases)

**Setup.**
* Dress's body (12 in, L/D 4.5, blunt base) from his Table II **as
  printed**, with the digit swap at x = 6.0 in (1.3243 for 1.3234) not yet
  corrected: a 0.0009 in kink at x/L 0.5.
* Re_L 4.376e5 and 9.406e5; kOmegaSSTLM at Tu 0.1 and 0.5 %; kOmegaSST
  (fully turbulent) at 4.376e5. Medium mesh (about 49k cells, y+ < 1),
  steady.
* First run of the project. Run alongside keel3d bulb-endplate (8 MPI
  ranks) on the same 8 cores.

**Outcome.** 5 ok, none flagged unsteady.

### Conclusions

1. **The transition model under-predicts the drag: by 20 % at Re_L 4.4e5
   and 31 % at 9.4e5 at Tu 0.1 %, and by more at Tu 0.5 %.** Lower Tu gives
   more drag, so a lower Tu (0.05 %) may come closer.

   | Re_L | measured C_D,wet | LM Tu 0.1 % | LM Tu 0.5 % | fully turbulent |
   |---|---|---|---|---|
   | 4.376e5 | 0.01201 | 0.00957 (−20 %) | 0.00771 (−36 %) | 0.00631 (−47 %) |
   | 9.406e5 | 0.00786 | 0.00546 (−31 %) | 0.00387 (−51 %) | - |

   Confidence: medium (one mesh; geometry kink; see run 2).
2. **Fully turbulent RANS is no upper bound here: it gives half the
   measured drag at 4.4e5.** It stays attached to x/L 0.75 and separates
   only on the steep afterbody. The measured drag comes from a laminar
   separation that the turbulent model can't have.

   Confidence: high.
3. **The model separates later and reattaches sooner than Dress saw at low
   Re.** LM at 4.4e5: laminar separation at x/L 0.64-0.65, reattachment
   0.66-0.67, then turbulent separation from 0.68-0.69 on the afterbody.
   Dress at low Re: separation from 0.50-0.55, reattachment only near the
   tail. At 9.4e5 LM's bubble (0.66-0.68 to 0.66-0.70) is close to Dress's
   oil flow at 1.2e6 (0.67 to 0.73). Langtry-Menter's separation-induced
   transition is built to reattach laminar bubbles quickly; a separation
   that doesn't reattach is what it misses.

   Confidence: medium.
4. **The base pushes the body forward at low Re (positive base pressure),
   as Dress measured.** Base drag −23 mN (Tu 0.1 %) and −7 mN (Tu 0.5 %) at
   4.4e5, +19 to +81 mN at 9.4e5. Dress found positive base pressure
   coefficients and doubted them.

   Confidence: low (base region on one mesh).

### Evidence

From `report/drag.md`; Cf and Cp in `report/surface.png`.

| turbulence | Tu % | Re_L | drag [mN] | C_D,wet | friction share | base drag [N] | x_sep | x_reattach | later separation |
|---|---|---|---|---|---|---|---|---|---|
| kOmegaSST | 0.2 | 4.376e5 | 377.3 | 0.006309 | 0.75 | 0.0016 | 0.754 | 0.866 | - |
| kOmegaSSTLM | 0.1 | 4.376e5 | 571.7 | 0.009566 | 0.21 | −0.0234 | 0.642 | 0.668 | 0.690 |
| kOmegaSSTLM | 0.5 | 4.376e5 | 460.5 | 0.007709 | 0.29 | −0.0071 | 0.652 | 0.663 | 0.676 |
| kOmegaSSTLM | 0.1 | 9.406e5 | 1507 | 0.005459 | 0.30 | 0.0193 | 0.658 | 0.660 | 0.673 |
| kOmegaSSTLM | 0.5 | 9.406e5 | 1070 | 0.003874 | 0.48 | 0.0812 | 0.679 | 0.702 | 0.714 |

(Drag in water at Dress's Re_L: 1.63 and 3.51 m/s on a 0.3048 m body.)

### Decisions

* Correct the digit swap (x = 6.0 in: 1.3234) and rerun. The kink shows as
  a Cp and Cf wiggle at x/L 0.5 in every case, right where Dress saw
  separation at low Re.
* Add Tu 0.05 %.
* Run the mesh check (coarse, fine) before reading more into conclusion 3.

### Assumptions

* Dress's C_D,wet is on the side surface without the base, as here (his
  text says wetted area; the base is not mentioned).
* Water at the same Re_L stands for his air flow (incompressible: Mach
  about 0.1 in his tunnel).

### Compromises

* Steady solver; the bubble region's Cf is wavy (0.65-0.75), which a
  transient run might settle.
* Two Reynolds numbers only; six are in the study.

### Learnings

* A medium case takes 13-44 min on one core while 8 MPI ranks of a keel3d
  case share the machine.

### Open questions and next steps

1. Run 2: the corrected body at Tu 0.05-0.2 %, the mesh check, and the
   turbulent bracket; then the other four Reynolds numbers.
2. If LM still reattaches too soon at low Re, bulb2d's drag for a bulb with
   tail separation is a lower bound, and B2 has to be read that way.
