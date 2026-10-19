# validation-dress: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/validation-dress/<run id>/` (not in git), so the numbers that support
a conclusion are copied here. The study asks whether bulb2d (axisymmetric
RANS, kOmegaSSTLM) predicts the drag of a body of revolution at IOM
Reynolds numbers, against Dress's (1988) magnetically suspended laminar
body. Project: [README](../README.md); why:
[docs/research/bulb-design.md](../../../docs/research/bulb-design.md), Track B1.

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
