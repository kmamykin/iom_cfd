# Ranking fin sections by race time

How `fin-profile-selection` ranks fin sections. The ranking turns each fin's
lift and drag into one number: the percentage of race time it loses against
the best fin, at a given speed and load. The results and the decisions taken
with them are in [findings/fin-profile-selection.md](findings/fin-profile-selection.md)
(analyses of 2026-10-13) and [findings/transient-check.md](findings/transient-check.md).
Symbols follow [docs/nomenclature.md](../../docs/nomenclature.md). S_h and D_h
here are the fin's share of the boat's hydrodynamic side force and drag.

**What is automated.**
* `iomcfd report` does steps 1 and 2: `report/selection.csv` and
  `report/selection_compare.md`, the drag at equal side force.
* Steps 3-7 were run as analysis scripts, not yet in the repository. Adding
  leeway and race time to the report is a proposed next step.

## 1. From the CFD to whole-fin forces

Each case gives the section's lift and drag coefficients, C_l and C_d
(`Cl`, `Cd`), at one angle α and boat speed V_b. They are scaled to the
whole fin (span b = 0.36 m below the hull, chord c, dynamic pressure
q = ½ρV_b²):

```
side force            S_h = C_l · q · c · b
viscous (profile) drag D_v = C_d · q · c · b
induced drag          D_i = S_h² / (2π · q · e · b²)   lifting line, hull as a reflection plane, e = 0.9
fin drag              D_h = D_v + D_i
```

In ORC's form, D_i = S_h² / (π q T_eff²), this is an effective draft
T_eff = b √(2e) ≈ 0.48 m (derived here, not used in the ranking).

These are the `side_force`, `drag_section`, `drag_induced` and `drag` columns
of `report/selection.csv` (`report.fin_span`, `report.induced_drag` in the
study).

## 2. Compare at equal side force

This is where lift enters the ranking.

The sails decide how much side force the fin must supply, not the fin. So
every fin is compared at the same three forces. These "loads" are what one
reference section, 0009/80, makes at 2°, 4° and 6° at each speed
(`report.compare_at`). At 1 m/s and Tu 0.1 %:

| load | side force |
|---|---|
| light | 1.15 N |
| working | 6.69 N |
| high | 8.33 N |

For each fin, the force is interpolated along its lift curve, linearly
between the computed angles. That gives two numbers:
* **the angle α it needs** to make that force. A longer chord, or a section
  with more lift per degree, needs less angle;
* **its drag D_h at that force.**

Only the pre-stall branch is used. A dip in lift near 0° (the low-Reynolds-
number lift reversal of thicker sections) is skipped, and forces outside a
fin's range are left blank.

Two simplifications make this a fair comparison:
* **Induced drag cancels out.** All fins have the same span and carry the
  same force, so their induced drag D_i is identical. It is part of D_h but
  drops out of the differences.
* **Leeway difference = section-angle difference.** The 3D part of the
  angle, S_h / (2π e q b²), doesn't depend on chord. So the difference in
  leeway between two fins is just the difference in their 2D section
  angle: Δβ_Y = Δα.

## 3. Upwind: extra drag plus extra leeway

Two costs, each measured against the best fin at that point.

**Drag slows the boat.** Extra drag ΔD_h reduces the boat speed by
ΔD_h ÷ dD_h/dV_b, where dD_h/dV_b is the slope of the boat's total
hydrodynamic drag (its resistance) with speed. As a fraction of the leg's
time:

```
drag loss = ΔD_h / (V_b · dD_h/dV_b)
```

* V_b · dD_h/dV_b is about 1.354 N at 1 m/s (0.40 N at 0.5 m/s, 0.81 N at 0.75 m/s,
  2.71 N at 1.5 m/s). It is estimated from hull, fin, bulb and rudder
  friction, without wave drag (section 8).
* Because it is only an estimate, everything is computed twice: with this
  slope ("×1") and with it doubled ("×2").
* At ×1, 0.01 N of extra drag costs 0.74 % of the leg's time at 1 m/s.

**Leeway lengthens the path.** The boat heads 39° off the true wind and
slides another 3° sideways (leeway β_Y), so its course is at β_TW = 42° to
the true wind. Making a distance d to windward takes d / cos β_TW of
sailing. One extra degree of leeway adds:

```
leeway loss = tan β_TW · Δβ_Y (in radians) = tan 42° × π/180 ≈ 1.57 % per degree
```

So 1° of leeway is worth about 0.021 N of drag at ×1 and 1 m/s.

## 4. Downwind

On a dead run the fin needs no side force, so it sits at 0°. Its cost is
extra drag only, ΔD_h,0 / (V_b · dD_h/dV_b), at the same boat speed as upwind.

## 5. Combine into race time

With equal time upwind and downwind:

```
loss = ½ · ( drag loss + leeway loss   [upwind]
           + drag loss at 0°           [downwind] )
```

The result is then shifted so the best fin at that speed and load scores 0.
Every other score reads as "% of race time behind the best".

## 6. Worked example

Working load (6.69 N), 1 m/s, Tu 0.1 %, time-accurate 4° points
(transient-check run 20261015-161112). 0007/100 against 0008/90:

| | 0007/100 | 0008/90 | best of the seven |
|---|---|---|---|
| upwind drag at 6.69 N | 0.3800 N | 0.3963 N | 0.3800 N (0007/100) |
| angle needed | 3.84° | 4.21° | 3.80° (0009/100) |
| drag at 0° | 0.1990 N | 0.1999 N | 0.1872 N (0007/90, 0008/80) |

At ×1, 0008/90 is 0.92 % behind 0007/100. Where the gap comes from:

| part | calculation | share of race time |
|---|---|---|
| upwind drag | 0.0163 N ÷ 1.354 N = 1.20 % of the leg | 0.60 % |
| leeway | 0.36° × 1.57 % = 0.57 % of the leg | 0.29 % |
| downwind drag | 0.0009 N ÷ 1.354 N = 0.07 % of the leg | 0.03 % |
| **total** | | **0.92 %** |

Each leg's loss is halved because the race is half upwind, half downwind.
Here upwind drag and leeway decide the comparison and downwind barely
matters. Against 0007/90 it is the downwind leg where 0007/100 loses: 0.4 %
of race time from its higher drag at 0°.

## 7. Aggregating and checking robustness

* **Per load, then averaged.** Scores are computed for light, working and
  high load at each speed. The mean weights every load and speed equally:
  0.5-1.5 m/s for steady results, 1 m/s for the time-accurate ones. 2.5 m/s
  is left out because there is no resistance estimate there.
* **Several variants.** The same calculation is repeated for:
  * both water-turbulence levels, Tu 1 % and 0.1 %;
  * both resistance slopes, ×1 and ×2;
  * steady or time-accurate 4° points.
* **Regret.** For each fin and variant, regret is its mean minus the best
  fin's mean. The largest regret across the variants says how badly a
  choice could turn out.

## 8. Inputs and assumptions

| input or assumption | value | source | status |
|---|---|---|---|
| heading | 39° to the true wind (β_TW − β_Y), at V_b = 1.13 m/s | L. Gilbert, [VMG (AMYA MY 180)](https://www.onemetre.net/Design/VMG%20(AMYA%20MY%20180)/VMG%20(AMYA%20MY%20180).htm) | not verified for this boat |
| leeway β_Y | about 3° | L. Gilbert, [Foil sections and forces](https://onemetre.net/Design/FinForce/FinForce.htm) | typical value, not measured |
| hull for the resistance estimate | wetted area 0.142 m², waterline 0.99 m; ITTC-57 × 1.10 | G. Bantock, [The ISAF One Metre Class, Part 3](https://www.mya-uk.org.uk/wp-content/uploads/2025/11/Graham-Bantock-Development-of-the-IOM-class-updated-2025-Part-3.pdf) | estimate; viscous only, no wave drag |
| bulb, rudder | bulb 0.0274 m², ITTC-57 × 1.2; rudder 0.010 m², Cd 0.014 | estimates | not verified |
| fin at 0° | from the CFD | this project | as computed |
| course | equal time upwind and downwind, same boat speed; reaches ignored | user, 2026-10-13 | assumption |
| side force S_h | the fin carries all of it; hull and rudder ignored | - | not verified |
| loads | the forces of 0009/80 at 2, 4 and 6°, so they shift with Tu. At Tu 0.1 % the light load is only 1.15 N, because of the lift loss near 0° at low Reynolds number. | method choice | - |
| weighting | equal weight for every load and speed | - | how the sailing divides between loads is unknown |
| flow model | 2D sections plus lifting-line induced drag; no tip, bulb or heel effects | - | not checked in 3D |

**Steady and time-accurate points.** At Tu 0.1 % the steady solver's 4°
points are 4-16 % off in lift and 5-14 % in drag (transient-check). Where
time-accurate points exist, they replace the steady ones in the
interpolation. A fin's lift curve can then mix the two solvers, for example
steady at 2° and 6°, time-accurate at 4°.
