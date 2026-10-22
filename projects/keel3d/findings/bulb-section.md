# bulb-section: findings log

Newest run first. One entry per run: conclusions, the evidence for them,
assumptions, compromises, learnings and next steps. Results live in
`runs/bulb-section/<run id>/` (not in git), so the numbers that support a
conclusion are copied here. The study asks whether a flattened keel bulb is
better than a round one (Track A2 of
[docs/research/bulb-design.md](../../../docs/research/bulb-design.md)):
six cross-sections of the same 2380 g NACA 0011 bulb at the 420 mm draft,
ranked by race time at equal side force. Project: [README](../README.md).

## Run 20261019-203823 (2026-10-19, image 13eac93, GCP, 39 cases)

**Setup.**
* Bulb: NACA 0011 revolved, 343 mm long, 2380 g, bottom at the draft. Six
  sections of equal area: round; elliptic 1.25, 1.5 and 2.0 (width /
  height); 1.5 with a flat bottom (lower half a superellipse of exponent 6);
  1.5 with a flat top (upper half exponent 6).
* Fin: NACA 0007, 100 → 80 mm (λ 0.8, 90 mm mean chord), down to the
  bulb's top. A flatter bulb sits lower at the same draft, so its fin is
  longer: 329.3 mm (round), 333.3, 336.2, 340.3 (2.0), 337.8 (flat bottom
  and flat top).
* 1 m/s; heel 0 and 25°; leeway 0, 2, 4°; medium mesh (1.01-1.23 M cells).
  Fine at 4° upright for round, 1.5 and flat bottom (mesh check).
* kOmegaSST, fully turbulent, wall functions, 5 layers;
  `nMedialAxisIter 20` (the fine-mesh fix from bulb-endplate).
* c2d-standard-16 Spot, 8 ranks per case, 6 at a time (the C3D quota was
  full). The first two submissions never started (quota; see Learnings).

**Outcome.** 39 ok, all converged.

### Conclusions

1. **The round bulb has the least race-time loss of the six, upright and at
   25° heel, at the light and the working load.** Loss against round (×1
   resistance slope), fully turbulent as computed:

   | section | heel 0, light | heel 0, working | heel 25, light | heel 25, working |
   |---|---|---|---|---|
   | round | best | best | best | best |
   | elliptic 1.25 | 0.35 | 0.27 | 0.42 | 0.38 |
   | elliptic 1.5 | 0.58 | 0.42 | 0.68 | 0.60 |
   | flat bottom 1.5 | 0.74 | 0.50 | 0.80 | 0.69 |
   | flat top 1.5 | 0.74 | 0.60 | 0.81 | 0.76 |
   | elliptic 2.0 | 1.16 | 0.93 | 1.19 | 1.17 |

   The race time doesn't count the lower centre of mass (conclusion 5).

   Confidence: medium (fully turbulent, conclusion 4; the medium mesh ranks
   the sections, conclusion 6).
2. **What a flattened bulb costs is mostly its longer fin, not the bulb.**
   At 0° (upright) the drag rises 5.3 (1.25) to 16.7 mN (2.0) over the
   round bulb's 707 mN. Of that, the fin 3.7-8.9 mN (its span grows 1.2-3.3 %),
   the bulb 1.3-8.1 mN (wetted area +1 to +9 %), the hull nothing. At 4°
   the bulb's own drag even falls for 1.25, 1.5 and the flat top (less
   pressure drag), and the fin carries the whole difference.

   Confidence: high for the split (the same on every heel and leeway).
3. **The end-plate gain from flattening is small, and most of it is the
   longer fin too.** At 4° upright the boat's side force rises 0.2 % (1.25)
   to 1.8 % (flat bottom, 2.0); the fin's +0.8 to +3.4 %, the bulb's own
   side force falls (−15 to −35 %). Effective draft T_eff (0-4°): round
   0.375 m, 1.25 0.378, 1.5 0.379, flat top 0.380, 2.0 0.382, flat bottom
   0.382 (+1.9 %). At 25° heel they shrink to −0.1 to +1.2 % in T_eff. At
   the working load's side force the flat bottom and 2:1 need 0.07° less
   leeway; the rest 0.01-0.03°.
   * Same aspect, the flat bottom beats the elliptic 1.5 on every count
     but drag: more side force (+1.8 against +0.8 % at 4°), T_eff 0.382
     against 0.379 m, 1.8 mm lower centre of mass. ORC's credit for a
     flat-topped bulb doesn't show: the flat top is the weakest 1.5 here.

   Confidence: medium. The differences are 1-2 %, but they survive the fine
   mesh (conclusion 6).
4. **Corrected for transition, the round bulb still wins, by less.**
   keel3d's friction is fully turbulent. bulb2d (fineness, run
   20261019-020546) gives this bulb alone at 1 m/s 0.52 times the turbulent
   friction (Tu 0.1 %); foil2d puts fin friction about 25 % high. Scaling
   each case's bulb friction by 0.52, and its fin friction by 0.80, cuts the
   losses by about a third: elliptic 1.5 0.29 % and flat bottom 0.30 % at
   the upright working load (from 0.42 and 0.50), 2:1 0.59 %.
   (**estimate**: the ratio is the round bulb's; a flattened bulb's laminar
   extent isn't known.)
5. **The lower centre of mass could pay for the flat bottom in a breeze,
   nowhere else** (**estimate**). The bulb's centre of mass above the draft:
   round 18.9 mm, 1.25 16.9, 1.5 15.4, flat top 15.6, flat bottom 13.6,
   2.0 13.3. On a lever of about 0.38 m (hull centre of buoyancy 20 mm
   down, an estimate) that is +0.5 % (1.25) to +1.4 % (flat bottom, 2.0) of
   the bulb's righting moment. With 0.5 % of upwind speed per 1 % of
   righting moment (the upper end of the research note's bracket, for an
   overpowered boat; 0 in light air) and the corrected drag of conclusion 4:

   | section | heel 0, light | heel 0, working | heel 25, light | heel 25, working |
   |---|---|---|---|---|
   | elliptic 1.25 | 0.14 | 0.07 | 0.22 | 0.19 |
   | elliptic 1.5 | 0.21 | 0.06 | 0.30 | 0.24 |
   | flat bottom 1.5 | 0.20 | −0.04 | 0.26 | 0.15 |
   | flat top 1.5 | 0.36 | 0.23 | 0.41 | 0.37 |
   | elliptic 2.0 | 0.46 | 0.23 | 0.50 | 0.48 |

   Only the flat bottom at the upright working load comes out level with
   the round bulb. A VPP is needed to say what the righting moment is worth.
6. **The medium mesh ranks the sections: medium to fine moves every
   section the same way, and the differences between them stay.** At 4°
   upright, medium → fine: side force +1.49 / +1.44 / +1.34 % (round /
   elliptic 1.5 / flat bottom), drag −5.53 / −5.48 / −5.46 % (fin −11.4 to
   −11.7 %, bulb −4.0 to −4.3 %, hull −0.1 %), as in the taper studies.
   Against the round bulb:

   | section | Δ side force, medium / fine | Δ drag, medium / fine |
   |---|---|---|
   | elliptic 1.5 | +51.0 / +48.6 mN (+0.83 / +0.78 %) | +7.4 / +7.4 mN (+0.84 / +0.89 %) |
   | flat bottom 1.5 | +109.2 / +101.3 mN (+1.78 / +1.63 %) | +10.7 / +10.8 mN (+1.23 / +1.30 %) |

   The fin's and the bulb's shares of those differences move by at most
   8 mN. Fine meshes: 3.62 M (round), 3.71 M, 3.84 M cells, all clean
   (`nMedialAxisIter 20`).

   Confidence: high for these two sections at 4°.
7. **The bulb's lift and pitch are negligible at these angles.** At 25° heel
   and 4° leeway the flattened bulbs push down by up to 0.048 N (2:1;
   round 0.002 N) and nose down by up to 5 mN·m; upright at 4°, −0.07 to
   −0.09 N for all. Against a 4 kg boat (39 N) that is 0.1 %: no
   nose-diving from bulb lift at these leeways.

   Confidence: medium (steady, medium mesh).

### Evidence

From `results.csv` and `report/planform_compare.md` (polar fits on 0-4°,
`max_leeway: 4`). The corrected rankings recomputed with
`Keel3D.compare_at_equal_force` on drags with the friction scaled.

Drag at 0° (upright) and side force at 4° (upright), differences from the
round bulb in mN (round absolute):

| section | fin span [mm] | ΔD total | ΔD fin | ΔD bulb | ΔD hull | ΔS at 4° | ΔS fin | ΔS bulb |
|---|---|---|---|---|---|---|---|---|
| round | 329.3 | (707.3) | (273.1) | (90.4) | (343.9) | (6124) | (5086) | (222) |
| elliptic 1.25 | 333.3 | +5.3 | +3.7 | +1.3 | +0.3 | +12 | +42 | −32 |
| elliptic 1.5 | 336.2 | +8.1 | +5.7 | +2.7 | −0.2 | +51 | +98 | −53 |
| elliptic 2.0 | 340.3 | +16.7 | +8.9 | +8.1 | −0.2 | +104 | +175 | −78 |
| flat bottom 1.5 | 337.8 | +11.2 | +7.2 | +3.8 | +0.3 | +109 | +142 | −40 |
| flat top 1.5 | 337.8 | +10.8 | +7.0 | +3.6 | +0.2 | +39 | +100 | −65 |

Polar fits (0-4°):

| section | T_eff, heel 0 [m] | side per deg, heel 0 [N/°] | T_eff, heel 25 [m] | side per deg, heel 25 [N/°] |
|---|---|---|---|---|
| round | 0.3749 | 1.529 | 0.3471 | 1.310 |
| elliptic 1.25 | 0.3781 | 1.534 | 0.3469 | 1.312 |
| elliptic 1.5 | 0.3792 | 1.544 | 0.3484 | 1.313 |
| flat bottom 1.5 | 0.3821 | 1.559 | 0.3513 | 1.323 |
| flat top 1.5 | 0.3796 | 1.538 | 0.3494 | 1.313 |
| elliptic 2.0 | 0.3815 | 1.556 | 0.3490 | 1.318 |

### Decisions

* For A3 (cant), keep the round bulb; add the flat bottom as the one
  flattened candidate worth a second look.
* Report flattening as "a longer fin plus a lower bulb", not as a bulb
  shape alone: at a fixed draft the two can't be separated.

### Assumptions

* keel3d's fully turbulent friction, corrected only as in conclusion 4.
* The righting-moment lever (0.38 m) and the bracket for its value are
  estimates; the bulb's share stands for the boat's.
* Race-time inputs as foil2d's methodology (estimated resistance slope, 42°
  track, half the race upwind); downwind drag from the upright 0° case.

### Compromises

* One speed (1 m/s); medium mesh for the ranking; 3 fine points.
* c2d-standard-16 instead of keel3d's usual c3d-standard-16 (8 physical
  cores both; all 39 cases on the same machine type).

### Learnings

* Batch asks for every task's VM at once. 39 one-VM tasks were over the
  region's 24 instances, and 12 c3d-16 VMs over the 150-vCPU C3D quota with
  other jobs holding 116: both jobs sat in QUEUED for good. `gcp submit`
  now caps the parallelism to the quotas' headroom (commit ce41395).
* Medium cases: 385-627 iterations, 7-13 min each on c2d-standard-16; all
  converged.

### Open questions and next steps

1. A3: cant on the round bulb (and the flat bottom).
2. A fixed-span comparison would separate the bulb's own end-plate effect
   from the longer fin (the fin's root moved up into the hull).
