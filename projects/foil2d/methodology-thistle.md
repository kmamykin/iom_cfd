# Ranking centreboard sections for a Thistle

How the Thistle study ranks sections for the dinghy's centreboard. The IOM
ranking ([methodology.md](methodology.md)) turns drag into race time; for
the Thistle there is no resistance curve, so this one stops at the board's
drag and leeway. Results and decisions:
[findings/thistle-board.md](findings/thistle-board.md). Inputs:
[design/thistle.yaml](design/thistle.yaml). Code: `iomcfd.boardrank`.
Symbols follow [docs/nomenclature.md](../../docs/nomenclature.md); (A)
marks an assumption.

## 1. The board

| input | value | source |
|---|---|---|
| thickness | 1 in maximum overall, so t/c = 5.556 % on an 18 in chord | TCA Green Book (2026-02-28), Art. XII.5. Wood-lead boards are 3/4-1 in; every board must also match "the dimensions and shape" of the Official Plans, not found online |
| chord c_n | 18 in = 0.4572 m, square to the leading edge (like the class's dimension Y) | user |
| rake Λ | 10° aft of vertical, fully down (A); bracket 5-15° | The board hangs on rollers (no pivot pin) at its natural angle, which may not be made more vertical (XII.9). No published value |
| span b_LE | 1.24 m along the leading edge (A) | Draft 4'6" with the board down, 6" up, so 48 in below the hull, at 10° |
| water | fresh, 20 °C: ν = 1.0035e-6 m²/s, ρ = 998.2 kg/m³ | user (summer lake sailing) |
| speeds | upwind 1-5 kn; downwind 1-15 kn; board fully down on every leg | user |
| baseline | NACA 0006 scaled to 1 in | user (the section on today's boards is unknown) |

## 2. From the raked board to a 2D section

The flow meets a raked board at the sweep angle Λ. Simple sweep theory
(independence principle) splits it into the component square to the leading
edge, V_n = V_b cos Λ, which the section sees, and a component along the
edge, which changes nothing but the friction. So foil2d and XFOIL solve
**the board's own section in its normal plane**: chord c_n, thickness 1 in,
at V_n. The whole board then follows, with q = ½ρV_b²:

```
side force       S_h = C_l · q cos²Λ · c_n · b_LE
viscous drag     D_v = (C_dp cos³Λ + C_df cos Λ) · q · c_n · b_LE
induced drag     D_i = S_h² / (2π · q · e · b_v²),   b_v = b_LE cos Λ (depth), e = 0.9 (A)
board drag       D_h = D_v + D_i
leeway           β_Y = α_n cos Λ
```

* **Friction.** The friction term counts the spanwise flow too: with the
  laminar independence principle the wall shear along the edge is the
  chordwise shear times tan Λ. Taking friction on the whole velocity
  instead differs by 1.5 % at 10°.
* **Induced drag.** This D_i equals foil2d's own, `induced_drag(S_h, q_n,
  b_LE, e)`, so a study's `report.fin_span: 1.24` gives the board's S_h and
  D_h at each CFD `speed` = V_n directly.
* **Streamwise view.** The water flows along a chord of c_n / cos Λ: 18.07,
  18.28 and 18.63 in at 5, 10 and 15°, through a section 5.53, 5.47 and
  5.37 % thick. At these angles both views give the same ranking (Re within
  3.5 %). The normal-plane one keeps the real section and lets every rake
  reuse the same CFD.
* **Rake.** Changing the rake only moves V_n by a few per cent, so
  `boardrank` interpolates the polars in log V_n (C_l linear, drags
  log-log). It extrapolates at most 3 %; past that a point is left out.

The CFD speed grid is V_n for V_b = 1, 2, 3, 4, 5, 7.5, 10, 12.5 and 15 kn
at 10°:

| V_b [kn] | 1 | 2 | 3 | 4 | 5 | 7.5 | 10 | 12.5 | 15 |
|---|---|---|---|---|---|---|---|---|---|
| V_n [m/s] | 0.5066 | 1.0133 | 1.5199 | 2.0265 | 2.5331 | 3.7997 | 5.0663 | 6.3329 | 7.5994 |
| Re | 2.3e5 | 4.6e5 | 6.9e5 | 9.2e5 | 1.15e6 | 1.73e6 | 2.31e6 | 2.89e6 | 3.46e6 |

* Upwind speeds (1-5 kn) run at α_n = 0, 1, 2, 3, 4, 5, 6, 8 and 10°.
* Downwind speeds (7.5 kn up) run at 0, 1 and 2°; downwind below 7.5 kn
  uses the upwind speeds' points.

## 3. Loads

As for the IOM, sections are compared at equal side force, not equal C_l.
The light, working and high loads are the S_h [N] the baseline makes at
α_n = 1, 2 and 4° at each upwind speed, at the nominal rake. They are held
in newtons for every rake and Tu.

Why 1, 2 and 4° (A): an estimate, to be refined.

* **Righting moment.** A crew of three, about 227 kg (500 lb), hikes from
  the rail with their centre of gravity about 0.65 m to windward. With
  about 300 N·m of form stability that is about 1750 N·m.
* **Side force.** Over a heeling arm of about 3.0 m (sail centre of effort
  about 2.4 m above the water, centre of lateral resistance about 0.6 m
  below), the sails' side force is about 580 N.
* **Board's share.** The board takes about 75 % of it (the hull and rudder
  the rest), so about 440 N at about 5 kn, fully powered.
* **Lift coefficient.** That is C_l ≈ 0.24 on the board (q cos²Λ c_n b_LE
  = 3300 × 0.97 × 0.567 m²). In lighter air the sail force estimate gives
  C_l ≈ 0.19-0.25 at 1-3 kn: α_n ≈ 2° at every speed.
* **Choice of loads.** Working is 2°, light 1°, and high 4° for gusts and
  acceleration out of tacks. The IOM's working load was 4°.

## 4. Ranking (upwind first, the user's choice)

1. **Upwind.** The board's D_h at each load, linear along the pre-stall
   branch (`racetime.at_force`), against the baseline's at the same load:
   **mean % over 5 speeds × 3 loads**, equal weights (A: no wind
   statistics). The table also shows the worst point and the mean leeway
   difference Δβ_Y.
2. **Stall margin.** The section angle at maximum S_h less the angle at
   the high load, the smallest over the speeds. A section whose margin is
   both under 2° and more than 1° under the baseline's is vetoed (A). A
   margin at the last computed angle is censored: it is at least that.
3. **Downwind (tie-break or veto).** The board's drag at 0° and at the
   reach load (the baseline's S_h at 2°), against the baseline's. The table
   shows the mean over 1-15 kn and over 7.5-15 kn. A section that loses
   more downwind than it gains upwind is vetoed (A). Within ±1 % upwind,
   downwind decides (A).
4. **Variants.**
   * **CFD.** Steady kOmegaSSTLM at Tu 0.1 and 1 %. The finalists also run
     at Tu 2 % and fully turbulent kOmegaSST, which stands in for a rough
     or painted board.
   * **XFOIL.** Ncrit 8.15, 4.0 and 2.6 (Tu 0.1, 0.5 and 1 %, Mack), plus a
     variant tripped at x/c 0.05.
   * **Rake.** Every variant is ranked at rake 10, 5 and 15°.

Drag and leeway are not combined into one number: that needs the hull's
resistance slope, which a Thistle VPP would give (docs/research/vpp.md).

## 5. What is automated

* `python -m iomcfd.boardrank screen <specs> --out DIR` ranks sections with
  XFOIL on the CFD's V_n grid (0.5° steps, every variant and rake).
  `--write-loads` stores the loads in `design/thistle-loads.csv`.
* `python -m iomcfd.boardrank cfd <results.csv>...` ranks finished foil2d
  runs. Each Tu and model is ranked separately; `--replace` takes
  time-accurate points; `--loads` holds the forces fixed.
* `python -m iomcfd.boardrank calibrate <results.csv> --tu 1`: XFOIL's
  ranking against the CFD's (Spearman).
* `python -m iomcfd.boardrank optimise --out DIR`: a CST section at exactly
  1 in, by differential evolution on the XFOIL ranking.
* Sections:
  * the parallel-sided family of Saporito et al. (2020) is
    `sectiondesign.parallel_sided`, spec `parallel:t=..,le=..,te=..,r=..,a=..`;
  * the NACA 6-series 006 sections are fitted to their Report 824 tables by
    `tools/naca6_006.py`;
  * `sectiondesign export` writes either to `geometry/foils/`.
