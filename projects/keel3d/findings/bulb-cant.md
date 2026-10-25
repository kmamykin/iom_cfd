# bulb-cant: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/bulb-cant/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study asks how much nose-up cant the keel
bulb should have (Track A3 of
[docs/research/bulb-design.md](../../../docs/research/bulb-design.md)).
IOM practice is 2-3° nose up; Gilbert's rule is leeway × sin(heel) plus the
bow-down trim. Project: [README](../README.md).

## Run 20261020-183634 (2026-10-20, image 594f9e1, GCP, 24 cases)

**Setup.**
* Two bulbs from [bulb-section](bulb-section.md) (run 20261019-203823):
  the round NACA 0011 (343 × 37.7 mm, 2380 g), its best, and the 1.5:1 flat
  bottom, the best flattened one. Fin λ 0.8, 90 mm mean chord, as there.
* Cant 0, 2 and 4° nose up, about the bulb's centre of mass, then moved so
  the lowest point stays at the draft. The centre of mass above the draft:
  18.9 / 18.4 / 19.5 mm (round), 13.6 / 13.4 / 15.4 mm (flat bottom).
* 25° heel at leeway 0, 2, 4°; upright at 0° for the downwind drag. 1 m/s,
  medium mesh, kOmegaSST fully turbulent; no trim (keel3d's model).
* c2d-standard-16 Spot, 6 at a time (the parallelism cap). The first
  submission (job iomcfd-bulb-cant-20261019-231029) failed in every task at
  start-up: an image older than the submit code (Learnings).

**Outcome.** 24 ok, all converged (388-624 iterations).

### Conclusions

1. **For the round bulb, 2° nose up is best at the working load and 0° at
   the light load; 4° is never best.** Race time lost against the best
   (×1 resistance slope, 25° heel upwind, upright downwind):

   | bulb | cant | light load | working load |
   |---|---|---|---|
   | round | 0° | best | 0.07 |
   | round | 2° | 0.06 | best |
   | round | 4° | 0.19 | 0.07 |
   | flat bottom | 0° | 0.82 | 0.79 |
   | flat bottom | 2° | 0.91 | 0.68 |
   | flat bottom | 4° | 1.02 | 0.81 |

   Between 0 and 2° the differences are under 0.1 %: cant hardly matters
   for the round bulb. This agrees with SAILSetc's and Gilbert's 2° "all
   round" and with Gilbert's 1° less in light air.

   Confidence: medium (the differences are small; medium mesh, but A2's
   mesh check moved every bulb section alike).
2. **Upwind, cant adds side force at heel; downwind it costs drag.**
   * At 25° heel and 4° leeway the round bulb's side force grows from 194 to
     226 (2°) and 260 mN (4°), the boat's by 0.5 and 1.2 %. The fin's
     stays put. T_eff (0-4° fit): 0.347, 0.352, 0.354 m (+1.5 %, +2.1 %).
   * Upright at 0° the canted bulb meets the flow at an angle: boat drag
     +1.2 mN at 2°, +4.8 mN at 4° (bulb drag +1.2 and +4.3 mN). As race
     time, 0.09 and 0.35 % of the downwind leg.
   * Gilbert's upright tow test (MY 175, 0.5 m/s) found 2° free and 5°
     1.5 % slower: the same direction.

   Confidence: medium.
3. **The heeled bulb is nearly aligned with the flow without cant here,
   though Gilbert's formula asks for 1.7°.** The bulb's pitching moment
   about its centre of mass (a body of revolution's Munk moment is zero
   with the flow along its axis) at 0° cant: −1.5 (upright, 0°), −2.1 (25°
   heel, 2° leeway), −0.3 mN·m (25°, 4°); with 2° cant +2.8 to +4.6 mN·m.
   So the zero sits at 0.1-0.6° of cant. leeway × sin(heel) gives 0.85° at
   2° leeway and 1.69° at 4°. The fin and hull change the flow at the bulb
   (the bulb sits in the fin's tip flow), which the formula leaves out. The
   bow-down trim that Gilbert adds is not in keel3d.

   Confidence: low (moments of a few mN·m, steady RANS).
4. **Cant doesn't rescue the flat bottom: it stays 0.6-1.0 % behind the
   round bulb at every cant.** Its own best is again 2° at the working load
   and 0° at the light load; its lift at 4° cant upright is twice the round
   bulb's (43 against 20 mN up).
5. **Cant hardly moves the lead.** 2° lowers the round bulb's centre of
   mass 0.5 mm (+0.13 % of its righting moment), 4° raises it 0.6 mm.

### Evidence

From `results.csv` and `report/planform_compare.md`.

Round bulb, forces in mN, pitching moment in mN·m (+ nose up):

| condition | cant | D_h boat | D bulb | S_h boat | S bulb | lift bulb (up) | pitch bulb |
|---|---|---|---|---|---|---|---|
| upright, 0° | 0 | 706.1 | 90.0 | 4 | 0.2 | −9.0 | −1.52 |
| upright, 0° | 2 | 707.4 | 91.2 | −15 | −0.5 | 4.0 | 3.25 |
| upright, 0° | 4 | 710.9 | 94.3 | −1 | −0.4 | 20.5 | 7.74 |
| 25°, 2° | 0 | 740.8 | 95.9 | 2645 | 100.7 | 13.3 | −2.13 |
| 25°, 2° | 2 | 741.2 | 96.6 | 2646 | 116.2 | 34.3 | 2.80 |
| 25°, 2° | 4 | 742.3 | 98.4 | 2674 | 126.2 | 56.6 | 7.29 |
| 25°, 4° | 0 | 850.2 | 113.0 | 5204 | 194.2 | −2.4 | −0.29 |
| 25°, 4° | 2 | 849.1 | 113.2 | 5228 | 225.8 | 26.8 | 4.55 |
| 25°, 4° | 4 | 850.4 | 114.8 | 5265 | 259.5 | 60.7 | 9.04 |

Polar fits at 25° heel (0-4°): T_eff 0.3468 / 0.3519 / 0.3540 m (round,
0 / 2 / 4°), 0.3500 / 0.3572 / 0.3570 m (flat bottom); side force per degree
1.307 / 1.317 / 1.319 and 1.324 / 1.336 / 1.345 N/°.

### Decisions

* **Recommend 2° nose up for the round bulb** (or 0-2°: within 0.1 % of
  race time either way); avoid 4°.
* No more cant runs for now: the differences are below what the fully
  turbulent model can be trusted to rank finely.

### Assumptions

* One heel (25°) for upwind and upright for downwind; the boat's trim is
  not modelled. Gilbert's bow-down trim would add to the cant that lines
  the bulb up.
* Race-time inputs as foil2d's methodology.

### Compromises

* 1 m/s only; medium mesh; fully turbulent (bulb friction about twice the
  transitional value, bulb2d fineness).

### Learnings

* `gcp submit` passes the task options of the local code
  (`--checkpoint`, from main's Spot-preemption checkpoints). Submitting with
  an older image tag made every task fail at its first line
  (`unrecognized arguments: --checkpoint`). Use an image at least as new as
  the code that submits.

### Open questions and next steps

1. Heel 10-15° (lighter air): less pitch at the bulb, so presumably less
   cant.
2. Trim: a bow-down trim of 0.5-1° would move the bulb's best cant up by as
   much (Gilbert); keel3d has no trim parameter yet.
