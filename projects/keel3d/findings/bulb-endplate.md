# bulb-endplate: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/bulb-endplate/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study measures what the bulb adds to the
fin as an end plate, and checks keel3d against the one measurement at a
similar Reynolds number: Sfakianaki et al. (2013), a quarter-scale Open 50
keel, +17-24 % side force and +11 % drag from the bulb at the same leeway
(Track A1 of [docs/research/bulb-design.md](../../../docs/research/bulb-design.md)).
Project: [README](../README.md).

## Run 20261019-020506 (2026-10-19, image 0884dd0, GCP, 8 cases)

**Setup.**
* Fin: NACA 0007, 100 → 80 mm (λ 0.8, 90 mm mean chord). Bulb: NACA 0011
  revolved, 2380 g, 343 × 37.7 mm, bottom at the 420 mm draft. Without the
  bulb the same fin ends in a flat tip where the bulb's top would be.
* Canoe body as the README, double body; 1 m/s, upright; leeway 0, 2, 4°.
* kOmegaSST, fully turbulent, wall functions, 5 layers. Medium (0.93-1.16 M
  cells); fine at 4° (2.87 M without the bulb, 3.64 M with it).
* c3d-standard-16 Spot, 8 ranks per case.

**Outcome.** 7 ok, 1 failed: the fine case with the bulb. Its mesh had 12
negative-volume cells and 110 wrongly oriented faces, and simpleFoam
stopped on a floating-point exception in its first iterations (next steps).

### Conclusions

1. **The bulb adds 13-15 % to the keel's side force at the same leeway, a
   little below the Open 50's 17-24 %.**
   * Keel (fin + bulb against the fin alone): 2.729 against 2.377 N at 2°
     (+14.8 %), 5.292 against 4.680 N at 4° (+13.1 %).
   * The fin's own side force rises 10.1 % and 8.4 %; the bulb carries the
     rest (0.11 and 0.22 N).
   * Whole boat, with the hull: +13.2 % and +11.6 %. Side force per degree
     (0-4°): 1.526 against 1.365 N/° (+11.8 %).

   Confidence: medium. Medium mesh: the fin alone moved +1.6 % in side force
   to fine; the bulb case has no fine point. The Open 50 model differs in
   scale, bulb (L/D 4.8, tripped) and keel.
2. **The bulb end-plates the fin: it loads the tip and moves the load down.**
   At 4°: local cl next to the bulb 0.286 against 0.199 without it; the
   spanwise centre of the fin's side force at 0.443 of the span against
   0.426; the centre of lateral resistance 17 mm deeper (z_clr −0.180
   against −0.163 m).

   Confidence: high for the direction (both meshes agree on the fin alone's
   shape), medium for the size.
3. **The induced-drag factor falls 8 % and the effective draft rises 4 %.**
   D = D0 + k S_h² over 0-4°: k 0.004510 against 0.004893 /N; T_eff 0.376
   against 0.361 m. Both include the growth of viscous drag with side
   force, and are fitted to three points.

   Confidence: medium.
4. **At equal side force the bulb saves about 0.27° of leeway, but its own
   drag dominates the drag comparison.** At the light load (3.15 N) the
   fin alone needs 2.27° against 2.00°. At 0° the bulb adds 90.3 mN (keel
   0.364 against 0.276 N; boat 0.708 against 0.617 N, +14.6 %; Open 50:
   +11 %). That drag is fully turbulent; bulb2d's fineness study gives
   40 mN for this bulb alone with transition and 73 mN fully turbulent, so
   keel3d's bulb drag is about twice too high. The race-time table means
   nothing here: the fin alone carries no lead.

   Confidence: high that the turbulent bulb drag is too high; medium on the
   size.
5. **The bulb barely lifts or pitches upright**: vertical force −0.009 to
   −0.086 N and pitching moment −0.002 to +0.004 N·m over 0-4°.

### Evidence

From `results.csv` and `report/planform_compare.md` (polar fits).

| bulb | leeway | mesh | side, boat [N] | side, keel [N] | side, fin [N] | drag, boat [N] | drag, keel [N] | drag, bulb [N] | z_clr [m] |
|---|---|---|---|---|---|---|---|---|---|
| no | 0 | medium | 0.013 | 0.012 | 0.012 | 0.6174 | 0.2756 | - | - |
| no | 2 | medium | 2.779 | 2.377 | 2.377 | 0.6515 | 0.2973 | - | −0.1628 |
| no | 4 | medium | 5.474 | 4.680 | 4.680 | 0.7630 | 0.3753 | - | −0.1633 |
| no | 4 | fine | 5.564 | 4.757 | 4.757 | 0.7252 | 0.3373 | - | −0.1625 |
| yes | 0 | medium | 0.004 | 0.004 | 0.004 | 0.7077 | 0.3637 | 0.0903 | - |
| yes | 2 | medium | 3.147 | 2.729 | 2.617 | 0.7455 | 0.3899 | 0.0974 | −0.1797 |
| yes | 4 | medium | 6.108 | 5.292 | 5.071 | 0.8741 | 0.4850 | 0.1176 | −0.1797 |

The bulb's drag at 0°: friction 78.8 mN, pressure 11.6 mN.

### Decisions

* Take keel3d's end-plate differences between bulbs as usable (the model
  gets the effect, at the low end of the measurement); its bulb drags only
  as relative.
* Fix the fine mesh before relying on any fine bulb case (A2's mesh check).

### Assumptions

* The fin alone's flat tip at the bulb's top stands for "no bulb"; the Open
  50 test removed the bulb from a keel of the same fin.
* Fully turbulent friction on fin and bulb.

### Compromises

* Medium mesh only for the bulb; three leeways.

### Learnings

* Medium cases: 373-594 iterations, 10-20 min on 8 ranks; fine 57 min.

### Open questions and next steps

1. The fine mesh with the bulb: the bad cells sit 15-19 mm behind the fin's
   trailing edge, 11 mm above the bulb, within ±4 mm of the centre plane,
   inside the near-wake box. They appear during layer addition (snapping
   left none), so the layer stage's interior point motion
   (displacementMedialAxis) inverts small cells there. Investigating with
   the layer settings; then rerun this case with A2's mesh check.
   * Done (2026-10-19, local, the same case): unlimited and
     `nMedialAxisIter 40` give the same 12 negative cells; 20 and 10 give
     "Mesh OK" (max skewness 2.2). Layer thickness reached, hull / fin /
     bulb: 89 / 98 / 98 % unlimited, 81 / 96 / 98 % with 20, 73 / 96 / 98 %
     with 10. keel3d now uses 20. A2 (bulb-section) has this case as its
     fine round-bulb point.
