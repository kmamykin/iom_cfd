# fineness: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/fineness/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study asks whether, at a fixed lead mass,
a longer and thinner keel bulb still has less drag at IOM speeds, and why
(Track B2 of [docs/research/bulb-design.md](../../../docs/research/bulb-design.md)).
The bulb alone, axisymmetric, zero incidence: [README](../README.md).

## Run 20261019-020546 (2026-10-19, image 0884dd0, GCP, 54 cases)

**Setup.**
* 2380 g of lead (keel3d: 2.5 kg keel − 120 g fin) as NACA 4-digit bodies
  of revolution (largest diameter at 0.3 L) of fineness L/D 5, 5.7, 7.5,
  9.09, 11.5 and 14.29: 230, 251, 302, 343, 401 and 464 mm long, 46.0 to
  32.4 mm in diameter. 9.09 (NACA 0011) is keel3d's bulb-study bulb, 14.29
  (NACA 0007) keel3d's default.
* 0.5, 1.0 and 1.5 m/s (Re_L 1.0e5-6.1e5); kOmegaSSTLM at Tu 0.1 and 0.5 %,
  and fully turbulent kOmegaSST (Tu 0.5 %). Medium mesh, steady.
* Read with [validation-dress](validation-dress.md): the transition model
  gets the trend of a body's drag with Re and is 10-25 % low where the
  laminar layer separates.

**Outcome.** 54 ok, none unsteady. 1,046-1,564 iterations, 16-31 min per
case, 18.7 case-hours.

### Conclusions

1. **With transition, a longer bulb has less drag at fixed lead, with most
   of the gain by L/D 7.5-9.** At 1 m/s, Tu 0.1 %: 51.2, 45.4, 41.0, 40.1,
   39.6, 39.3 mN from L/D 5 to 14.3. From the market-like 9.09 to 14.3 the
   drag falls only 2.0 % at 1 m/s (1.4 % at 0.5, 2.3 % at 1.5 m/s). Tu 0.1
   and 0.5 % differ by at most 4 %.

   Confidence: medium (the transition model's level, validation-dress).
2. **The mechanism: fat bulbs separate on the tail.** The laminar layer
   separates at x/L 0.60-0.65 (L/D 5) and 0.66-0.72 (L/D 5.7), with
   reattachment late (0.86-0.98) or not at all, and pressure drag is 21-37 %
   of the total. From L/D 9.09 up the flow stays attached (at Tu 0.1 %), the
   skin friction keeps falling (laminar) to x/L 0.92-0.95, and pressure drag
   is 4-10 %.

   Confidence: medium. The transition model reattaches too soon (validation-
   dress), so the fat bulbs' penalty is if anything too small.
3. **Fully turbulent RANS ranks the bulbs the other way and doubles the
   slender ones' drag.** At 1 m/s: 69.8 mN (L/D 5) rising to 79.5 mN
   (L/D 14.3), as the friction formulas say. For L/D ≥ 9 it is 1.4-1.6 times
   the transitional drag at 0.5 m/s and 1.8-2.3 times at 1-1.5 m/s. keel3d's bulb drag (fully turbulent) is therefore
   about twice too high, and wrong in its ranking by length.

   Confidence: high (that the two models disagree); medium (which is right:
   validation-dress supports the transition model).
4. **The market-like bulb (343 × 37.7 mm) is nearly laminar:** 14.4, 40.1
   and 73.4 mN at 0.5, 1.0 and 1.5 m/s (Tu 0.1 %), C_D,wet 0.0041, 0.0029,
   0.0023. The research note's attached-laminar estimate for a 330 mm bulb
   was 37 mN at 1 m/s; fully turbulent here is 73 mN.

   Confidence: medium (attached laminar friction is not what Dress's body
   tested).
5. **Against Gilbert's tow test (MY 184): the right direction, too small at
   0.5 m/s** (**estimate**). Converting the drag differences to speed with
   foil2d's resistance slope (V·dR/dV = 0.40 N at 0.5 m/s, 1.354 N at
   1 m/s):
   * 251 → 302 mm: 0.18 % at 0.5 m/s, 0.32 % at 1 m/s. Gilbert measured
     1.4 % at low speed and 0.6 % at high speed for 250 → 300 mm.
   * 251 → 343 mm: 0.23 % at 0.5 m/s against 1.9 % measured (250 → 350 mm,
     low speed).

   At 1 m/s the CFD is about half the measurement; at 0.5 m/s about an
   eighth. Gilbert's bulbs' masses and shapes are unknown (the 250 mm one
   was a 1992 Young body), and the slope is an estimate, so the comparison
   is loose. An under-predicted laminar separation on the fat bulb (B1)
   would explain part of the gap, most at low Re.

   Confidence: low.
6. **Length also lowers the centre of mass** (keel3d, same lead, bottom at
   the draft): 18.9 mm above the draft for L/D 9.09, 16.2 mm for 14.3. So
   within this family the long bulb wins on drag and righting moment; what
   stops IOM bulbs at 345-365 mm is outside this model (bending strength,
   yaw and pitch inertia, turning).

### Evidence

From `results.csv` (`report/drag.md`, `report/fineness.png`).

Drag [mN]:

| speed | model | 5 (230 mm) | 5.7 (251) | 7.5 (302) | 9.09 (343) | 11.5 (401) | 14.29 (464) |
|---|---|---|---|---|---|---|---|
| 0.5 m/s | LM Tu 0.1 % | 16.5 | 15.3 | 14.6 | 14.4 | 14.2 | 14.2 |
| 0.5 m/s | LM Tu 0.5 % | 17.0 | 15.6 | 14.7 | 14.5 | 14.3 | 14.2 |
| 0.5 m/s | turbulent | 19.9 | 19.9 | 20.2 | 20.6 | 21.4 | 22.4 |
| 1.0 m/s | LM Tu 0.1 % | 51.2 | 45.4 | 41.0 | 40.1 | 39.6 | 39.3 |
| 1.0 m/s | LM Tu 0.5 % | 50.0 | 46.3 | 41.8 | 40.6 | 40.0 | 39.7 |
| 1.0 m/s | turbulent | 69.8 | 70.0 | 71.5 | 73.3 | 76.2 | 79.5 |
| 1.5 m/s | LM Tu 0.1 % | 94.7 | 86.3 | 75.5 | 73.4 | 72.3 | 71.7 |
| 1.5 m/s | LM Tu 0.5 % | 91.0 | 85.6 | 77.9 | 75.1 | 73.4 | 72.7 |
| 1.5 m/s | turbulent | 146.6 | 147.1 | 150.3 | 154.0 | 160.0 | 166.8 |

Laminar separation x/L (none: attached):

| speed | model | 5 | 5.7 | 7.5 | 9.09 |
|---|---|---|---|---|---|
| 0.5 m/s | LM Tu 0.1 / 0.5 % | 0.61 / 0.64 | 0.71 / 0.72 | none | none |
| 1.0 m/s | LM Tu 0.1 / 0.5 % | 0.60 / 0.63 | 0.67 / 0.70 | 0.85 / none | none |
| 1.5 m/s | LM Tu 0.1 / 0.5 % | 0.60 / 0.65 | 0.66 / 0.71 | 0.82 / 0.93 | none / 0.99 |

Friction share of the drag (LM Tu 0.1 %): 0.63-0.71 (L/D 5), 0.71-0.79
(5.7), 0.86-0.87 (7.5), 0.90-0.91 (9.09), 0.93-0.94 (11.5), 0.95-0.96 (14.29).

### Decisions

* **Drop B3** (tail shape and trip) for the bulb studies' bulb: it stays
  attached at L/D 9.09, so there is no tail separation to fix. B3 would
  matter only for bulbs shorter than about 300 mm.
* keel3d's bulb drags (fully turbulent) are read as relative only, and the
  bulb's friction is about twice too high in A2; keep that in mind where
  wetted area decides a ranking.

### Assumptions

* The bulb alone, at zero incidence: no fin junction, no end-plate effect,
  no pitch from heel and leeway (keel3d's).
* Race-time slopes as foil2d's methodology (estimates).

### Compromises

* One family (NACA, largest diameter at 0.3 L); medium mesh only (B1's mesh
  check: −4.8 % from medium to fine on Dress's body).

### Open questions and next steps

1. A transient run of the fat bulbs (L/D 5-5.7), where the separation sits.
2. A Tu below 0.1 % for the slender bulbs: does the laminar run reach the
   tail?
