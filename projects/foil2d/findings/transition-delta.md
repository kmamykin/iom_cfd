# transition-delta: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/transition-delta/<run id>/` (not in git); the table keel3d uses is
committed as `projects/keel3d/data/naca0007-transition.csv`
(`tools/keel3d_transition_table.py`). The study gives keel3d, which is fully
turbulent, the 2D difference between the transition model and the fully
turbulent model for the fin section, NACA 0007, at the fins' local chords.
Symbols: [docs/nomenclature.md](../../../docs/nomenclature.md).

## Run 20261021-001632 (2026-10-21, git bcd6eec, GCP, 72 cases)

**Setup.**
* NACA 0007 at 80, 90 and 100 mm chord (Re 70k, 79k, 88k at 1 m/s, water
  at 15 °C), 0-7° in 1° steps; medium mesh, steady solver, as
  fin-profile-selection.
* kOmegaSSTLM at Tu 0.1 % and 1 %, kOmegaSST at Tu 0.5 % (keel3d's
  setting).
* Image `iom-cfd:bcd6eec`, c3d-standard-16 Spot, 8 single-rank cases per VM.

**Outcome.** 67 ok, 5 not converged (all at 4°, transition model), 25
unsteady (transition model, mostly 0-1° and 4°). One case diverged on GCP
(80 mm, 4°, Tu 0.1 %). It was re-run locally with lower under-relaxation
(relax_U 0.6, relax_turb and relax_transition 0.5; execution parameters,
same case hash) into this run, and its export replaced the cloud case in the
bucket. It stayed unsteady and hit the 8000-iteration limit: C_l 0.418 ±
0.046, C_d 0.0194 ± 0.0035.

### Conclusions

1. **Laminar flow cuts the section drag at zero lift by 17-23 %**: C_d
   0.0151 / 0.0147 / 0.0144 fully turbulent against 0.0122 / 0.0116 /
   0.0111 at Tu 0.1 % (80 / 90 / 100 mm), and 0.0125 / 0.0118 / 0.0112 at
   Tu 1 %. The longer chord gains a little more. Confidence high (steady
   and steady-converged at 0°, though flagged unsteady by C_l noise of
   ±0.005).
2. **At 1-2° the transition model loses 20-40 % of the lift**: C_l 0.06-0.07
   at 1° against 0.103, 0.12-0.16 at 2° against 0.206. The same section
   then needs about 0.4-0.6° more angle for C_l 0.1-0.2 (the low-Reynolds
   lift loss near zero that foil2d found before). Confidence high.
3. **At 5-7° it has more drag**: at 6°, +20 % at Tu 0.1 % (0.0336 / 0.0323 /
   0.0312 against 0.0280 / 0.0270 / 0.0260), +6-7 % at Tu 1 %. A laminar
   bubble near the nose costs more than the laminar run saves. Confidence
   high at 6-7° (steady and converged), medium at 5°.
4. **At 4° the flow sheds and the steady answer is uncertain**, as
   transient-check found: all 6 transition-model cases at 4° are unsteady
   or not converged, C_d ± 2-18 %. The time-accurate points at 90 and 100 mm
   (transient-check, Tu 0.1 %) have 9-14 % less C_d and 4-5 % less C_l than
   the steady ones. The 80 mm point (steady only) has C_d 0.0194, 16-19 %
   above 90 and 100 mm steady. Whether that is a real low-Re penalty or
   steady noise is **not settled**. Confidence low.
5. **This run reproduces fin-profile-selection's steady points**: at 90 mm,
   Tu 0.1 % C_d 0.01157 at 0° (0.0115668 in run 20261013-200643) and
   0.01634 at 4° (identical). High.

### Evidence

`results.csv`, C_l / C_d (failed and re-run points as described above):

| chord | model | 0° | 2° | 4° | 6° |
|---|---|---|---|---|---|
| 80 mm | kOmegaSST, Tu 0.5 % | 0.000 / 0.0151 | 0.206 / 0.0156 | 0.406 / 0.0178 | 0.575 / 0.0280 |
| 80 mm | SSTLM, Tu 0.1 % | 0.001 / 0.0122 | 0.126 / 0.0132 | 0.418 / 0.0194 (re-run, unsteady) | 0.566 / 0.0336 |
| 80 mm | SSTLM, Tu 1 % | 0.000 / 0.0125 | 0.144 / 0.0135 | 0.431 / 0.0155 (unsteady) | 0.573 / 0.0299 |
| 90 mm | kOmegaSST, Tu 0.5 % | 0.000 / 0.0147 | 0.206 / 0.0153 | 0.407 / 0.0173 | 0.578 / 0.0270 |
| 90 mm | SSTLM, Tu 0.1 % | 0.001 / 0.0116 | 0.124 / 0.0125 | 0.415 / 0.0163 (n.c.) | 0.568 / 0.0323 |
| 90 mm | SSTLM, Tu 1 % | 0.000 / 0.0118 | 0.150 / 0.0128 | 0.429 / 0.0142 (n.c.) | 0.575 / 0.0286 |
| 100 mm | kOmegaSST, Tu 0.5 % | 0.000 / 0.0144 | 0.207 / 0.0149 | 0.408 / 0.0169 | 0.580 / 0.0260 |
| 100 mm | SSTLM, Tu 0.1 % | 0.001 / 0.0111 | 0.124 / 0.0120 | 0.408 / 0.0167 (n.c.) | 0.570 / 0.0312 |
| 100 mm | SSTLM, Tu 1 % | 0.000 / 0.0112 | 0.163 / 0.0123 | 0.435 / 0.0137 (n.c.) | 0.577 / 0.0276 |

Time-accurate at Tu 0.1 %, 1 m/s (transient-check runs 20261015-161112 and
20261017-000816; they replace the steady points in keel3d's table):
90 mm 0.131 / 0.0127 (2°), 0.396 / 0.0149 (4°), 0.572 / 0.0309 (6°);
100 mm 0.127 / 0.0122, 0.393 / 0.0143, 0.576 / 0.0295.

The difference keel3d applies, transition minus fully turbulent at equal
C_l (dC_d in 1e-4, dα in degrees, from the committed table):

| Tu | chord | dC_d at C_l 0 / 0.2 / 0.3 / 0.4 / 0.55 | dα at C_l 0.1 / 0.2 / 0.3 / 0.4 |
|---|---|---|---|
| 0.1 % | 80 mm | −29 / −5 / +8 / +14 / +61 | +0.61 / +0.81 / +0.46 / −0.03 |
| 0.1 % | 90 mm | −32 / −12 / −9 / −19 / +45 | +0.59 / +0.59 / +0.36 / +0.11 |
| 0.1 % | 100 mm | −33 / −18 / −12 / −19 / +39 | +0.63 / +0.49 / +0.10 / +0.15 |
| 1 % | 80 mm | −26 / −17 / −17 / −23 / +22 | +0.45 / +0.41 / +0.05 / −0.18 |
| 1 % | 90 mm | −29 / −22 / −24 / −32 / +20 | +0.43 / +0.35 / −0.04 / −0.19 |
| 1 % | 100 mm | −32 / −26 / −30 / −34 / +19 | +0.37 / +0.28 / −0.11 / −0.26 |

### Decisions

* keel3d's transition correction uses this table, with the time-accurate
  points where they exist (foil2d/methodology.md's rule).

### Assumptions

* The medium mesh and the steady solver, as fin-profile-selection; steady
  answers where the flow sheds (4°) are uncertain (conclusion 4).
* 1 m/s only: the keel3d correction is for 1 m/s.
* Tu 0.1 % and 1 % bracket the pond (unknown, as before).

### Compromises

* No time-accurate point at 80 mm, and none at Tu 1 %.

### Learnings

* Compute: median 23 min per case, 28.3 case-hours, about 1 h wall on 8
  VMs; the local re-run took 50 min.

### Open questions and next steps

1. A time-accurate 80 mm, 4°, Tu 0.1 % case: it decides the sign of the
   working-load comparison in keel3d taper-compare (findings there).
   foil2d transient cases took 4-16 h.
