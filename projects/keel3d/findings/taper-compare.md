# taper-compare: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/taper-compare/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study answers the project's first question
on the mesh [taper-mesh](taper-mesh.md) picked: is a constant-chord or a
tapered keel fin better on an IOM? NACA 0007 fins of equal area (90 mm mean
chord): constant chord (λ 1.0) and 100 → 80 mm (λ 0.8), on the canoe body
and 2380 g NACA 0007 bulb, compared at equal side force and ranked by race
time ([foil2d/methodology.md](../../foil2d/methodology.md)). Symbols:
[docs/nomenclature.md](../../../docs/nomenclature.md); project and
geometry: [README](../README.md).

## Run 20261020-183208 (2026-10-20, git 6a01dcb, GCP, 8 cases)

**Setup.**
* λ 1.0 (90 → 90 mm) and λ 0.8 (100 → 80 mm), span 334.6 mm; β_Y 0, 2,
  4, 6°; V_b 1 m/s, upright; fine mesh (3.60-3.99 M cells), aligned
  mirror-image grid.
* Compared at the S_h the constant-chord fin makes at 2, 4 and 6° (light,
  working and high load); race time as foil2d: V_b dD_h/dV_b = 1.354 N,
  42° track, half upwind with D_h and β_Y, half downwind with D_h at
  β_Y = 0.
* simpleFoam, kOmegaSST, wall functions (fully turbulent), Tu 0.5 %;
  image `iom-cfd:6a01dcb` (drift-checked convergence test),
  c3d-standard-16 Spot, 8 ranks.
* The 0, 2, 4° cases repeat taper-mesh run 20261019-213145's fine cases.

**Outcome.** 8 of 8 ok, all converged (684-867 iterations), 13.1
case-hours.

### Conclusions

1. **The tapered fin (100 → 80 mm) is never slower than the constant 90 mm
   chord, and it is faster at high load.** The constant-chord fin loses
   0.02 / 0.07 / 0.70 % of race time at the light / working / high load.
   At the high load (S_h 8.86 N) the tapered fin sails at 5.89° instead of
   6.00° with 0.017 N (1.5 %) less D_h. At the light and working loads the
   difference is far below anything a sailor would notice. Confidence:
   high at the light and working loads (taper-mesh gave 0.01 and 0.07 %;
   from fine to xfine the S_h difference moved 0.34 points, towards the
   tapered fin). Medium at the high load: drag climbs steeply between 4°
   and 6° and the loss there is interpolated. Linear interpolation in S_h
   or S_h² instead of PCHIP gives 0.44 / 0.55 %.
2. **The gain is a little more side force per degree and a little less
   drag due to side force**: 1.557 against 1.535 N/° (+1.4 %), and
   k = 0.00504 against 0.00515 N⁻¹ (−2 %; effective draft T_eff 0.356
   against 0.352 m). The drag at zero side force is the same (D0 0.681
   against 0.680 N; D_h at 0°: 0.7008 against 0.7002 N). A small effect,
   as to be expected from λ 0.8 against 1.0 with a bulb at the tip.
   Confidence high.
3. **The tapered fin's loading is closer to elliptic.** Its local C_l
   varies less along the span: 0.530 → 0.394 from root to tip at 6°,
   against 0.540 → 0.370. Its side force sits nearer the root:
   eta_cp 0.447 against 0.455 at 4°, 0.448 against 0.459 at 6°.
   Confidence high.
4. **Taper raises the centre of lateral resistance by 4 mm**: z_clr
   −0.180 against −0.184 to −0.185 m at 2, 4 and 6° (3.7-4.5 mm), about
   2 % less heeling arm. This is the same in every keel3d run so far.
   Confidence high.
5. **Both fins' drag climbs steeply from 4° to 6°.** Fin drag rises 57 %
   (0.33 → 0.52 N) while S_h² doubles, so viscous drag grows faster than
   induced drag. Flow separation may be starting; **not verified** (no
   flow fields looked at yet).
6. **The results repeat.** The 0, 2, 4° cases match taper-mesh's fine
   cases within 0.1 % in D_h and 0.35 % in S_h.

**So far the answer is the tapered 100 → 80 mm fin.** It is at least as
fast, up to 0.4-0.7 % faster at high load. It is also stiffer at the root
(1.5 times the second moment, README), and its centre of lateral
resistance is 4 mm higher. This holds fully turbulent, at 1 m/s and
upright; see Assumptions.

### Evidence

`report/planform_compare.md` (loss of race time against the best fin,
×1 / ×2 the resistance slope):

| λ | load | S_h [N] | β_Y [°] | D_h [N] | D_h at β_Y = 0 [N] | loss ×1 / ×2 [%] |
|---|---|---|---|---|---|---|
| 0.8 | light | 3.066 | 1.96 | 0.7306 | 0.7008 | best |
| 1.0 | light | 3.066 | 2.00 | 0.7308 | 0.7002 | 0.02 / 0.03 |
| 0.8 | working | 6.140 | 3.94 | 0.8291 | 0.7008 | best |
| 1.0 | working | 6.140 | 4.00 | 0.8304 | 0.7002 | 0.07 / 0.06 |
| 0.8 | high | 8.862 | 5.89 | 1.0875 | 0.7008 | best |
| 1.0 | high | 8.862 | 6.00 | 1.1046 | 0.7002 | 0.70 / 0.39 |

Per case (`results.csv`):

| λ | β_Y | D_h [N] | S_h [N] | D fin [N] | D hull [N] | D bulb [N] | z_clr [m] | eta_cp | C_l root / mid / tip |
|---|---|---|---|---|---|---|---|---|---|
| 1.0 | 0° | 0.7002 | −0.000 | 0.2694 | 0.3446 | 0.0862 | | | |
| 0.8 | 0° | 0.7008 | 0.000 | 0.2695 | 0.3451 | 0.0862 | | | |
| 1.0 | 2° | 0.7308 | 3.066 | 0.2818 | 0.3555 | 0.0935 | −0.1836 | 0.456 | 0.191 / 0.175 / 0.127 |
| 0.8 | 2° | 0.7319 | 3.132 | 0.2824 | 0.3563 | 0.0932 | −0.1797 | 0.447 | 0.186 / 0.177 / 0.137 |
| 1.0 | 4° | 0.8304 | 6.140 | 0.3288 | 0.3869 | 0.1147 | −0.1835 | 0.455 | 0.385 / 0.349 / 0.253 |
| 0.8 | 4° | 0.8340 | 6.229 | 0.3318 | 0.3888 | 0.1135 | −0.1798 | 0.447 | 0.370 / 0.351 / 0.271 |
| 1.0 | 6° | 1.1046 | 8.862 | 0.5173 | 0.4397 | 0.1476 | −0.1853 | 0.459 | 0.540 / 0.503 / 0.370 |
| 0.8 | 6° | 1.1093 | 9.012 | 0.5216 | 0.4426 | 0.1452 | −0.1808 | 0.448 | 0.530 / 0.507 / 0.394 |

Polar fits (`report/polar_fits.csv`, all four leeways): D0 0.6806 /
0.6799 N, k 0.005036 / 0.005146 N⁻¹, T_eff 0.3557 / 0.3519 m, 1.557 /
1.535 N/° (λ 0.8 / 1.0).

### Decisions

* The taper question gets a provisional answer, the tapered 100 → 80 mm
  fin. It is to be confirmed at other speeds, heeled, and with the
  transition correction (next steps); until then it is not the project's
  recommendation.

### Assumptions

* **Fully turbulent friction.** The tapered fin's tip runs at
  Re 70k against 79k for the constant chord (README). foil2d found laminar
  separation at these Reynolds numbers; its penalty would fall more on the
  tapered tip. **Not modelled**, and it could cancel a 0.07 % lead.
* Race-time model: V_b dD_h/dV_b = 1.354 N at 1 m/s (foil2d's estimate,
  **not verified** in 3D), 42° track, half upwind, half downwind.
* 1 m/s and upright only. Upwind the boat heels 10-20°, and heeled meshes
  are not mirror images (taper-gridshift: a false camber may come back).
* Both fins weigh the assumed 120 g (**not verified**).
* Double body: no waves, and no free-surface effect on the fin root.

### Compromises

* Four leeways; the high load sits between the last two, where drag
  climbs steeply (conclusion 1 gives the range).
* No flow fields examined: the 6° highlight (separation?) is open.

### Learnings

* With the mesh issues settled (aligned mirror grid, near-wake box,
  medial-axis limit, drift-checked convergence), keel3d repeats itself to
  0.1-0.35 %. That is well below the 1-2 % differences between these fins.
* Compute: 89-118 min per fine case on 8 ranks, 13.1 case-hours; the 6°
  cases took longest (841-867 iterations).

### Open questions and next steps

1. **Transition correction** (README, Limitations): strip by strip from
   `spanload.csv` with foil2d's kOmegaSSTLM − kOmegaSST drag difference at
   the local chord's Re and C_l. It needs a foil2d run of NACA 0007 at
   80-100 mm chord, with both models.
2. **Other speeds**: 0.75 and 1.5 m/s for both fins (fine, β_Y 0-6°,
   16 cases).
3. **Heel**: both fins at 15-20°, with one y-shifted case to check for the
   false camber.
4. **Flow at 6°**: fetch the fields of the two 6° cases (`gcp fetch
   --fields`) and run `iomcfd viz`: separation at the trailing edge or
   next to the bulb?

Highlights for the next run: the 6° pair again (`compare: fin_taper`,
`why`: separation?), and at 1.5 m/s the working load (`why`: does the
ranking hold at the higher Reynolds number?).
