# Nomenclature: forces, moments and angles

The symbols this project uses for sailing forces in docs, findings,
reports and new outputs.

* **The core** comes from Parolini & Quarteroni, "Forces and moments on the
  water plane" ([MOX 10/2007][parolini], Fig. 2 and eq. 2): the course
  frame, the h/a subscripts and the three balance equations.
* **What Parolini doesn't define** comes from the
  [ORC VPP Documentation 2026][orc] (ORC):
  * the heel symbol;
  * the wind abbreviations;
  * resistance and righting-moment components;
  * centre of effort, effective draft and sail trim.

  These are rewritten in Parolini's style: D_i, not ORC's D_induced.
* **Hull form and hydrostatics** use the ITTC symbols (ITTC Symbols and
  Terminology List, ship geometry and hydrostatics).
* **A few symbols neither source defines** are marked *project*.

The geometry frame (x aft, y port, z up, waterline z = 0) and the signs of
heel, leeway and trim are in [geometry.md](geometry.md). Existing parameter
and output names (`leeway`, `drag_N`, `side_N`) stay as they are. The
mapping is at the end.

## Frames

| frame | axes | used for |
|---|---|---|
| boat frame | x aft, y port, z up; origin at the bow on the waterline ([geometry.md](geometry.md)) | geometry, CFD set-up, moments in the output files |
| course frame | x_c along V_b (forward), y_c horizontal and normal to the course, z up | VPP forces: D_h, S_h, T_a, S_a (Parolini's "water plane") |
| apparent-wind frame | along and across the apparent wind | L_a, D_a |

* The course frame is the boat frame turned by the leeway β_Y about z (and
  reversed in x).
* Heel φ rotates the boat about its centreline, not the frames.
* All formulas below are for **port tack** (wind from port, heel to
  starboard, boat sliding to starboard), the repo's convention. Starboard
  tack is the mirror image.

## Symbols

### State and wind

| symbol | meaning | source |
|---|---|---|
| V_b | boat speed through the water | Parolini |
| φ | heel angle; + = to starboard | ORC (Parolini says "heel angle", no symbol) |
| β_Y | **leeway**: angle between the course and the centreline; + = bow to port. Written "leeway β_Y", not Parolini's "yaw angle", because yaw is needed for the moment about z | Parolini symbol, ORC word |
| β_TW, β_AW | true and apparent wind angles, **measured from the course** | Parolini |
| V_TW, V_AW | true and apparent wind speeds | project, to match β_TW and β_AW (ORC writes V_T and V_a) |
| TWS, TWA, AWS, AWA | the same in plots, tables and prose | ORC |
| δ_R | rudder angle; + = trailing edge to port (`rudder_angle`) | project |

### Hydrodynamic (subscript h)

| symbol | meaning | source |
|---|---|---|
| D_h | hydrodynamic drag, along the course | Parolini |
| D_v, D_r, D_i, D_aw | viscous, residuary (wave), induced drag, and added drag in waves: D_h = D_v + D_r + D_i + D_aw | ORC (D_viscous, D_residuary, D_induced, D_raw) |
| S_h | hydrodynamic side force, normal to the course in the water plane; + = to windward | Parolini |
| F_z,h | vertical hydrodynamic force; + = up | project |
| M_h | hydromechanic righting moment about the centreline at the waterline: M_h = RM_φ − RM_V − M_h,dyn | Parolini |
| RM_φ | hydrostatic righting moment at heel φ (weight and buoyancy) | ORC |
| RM_V | loss of righting moment with speed | ORC |
| M_h,dyn | hydrodynamic roll moment of the hull and appendages (heels the boat further). ORC models it as RM4 · FHA ≈ z_CLR · S_h | project, after ORC |
| z_CLR | depth of the centre of lateral resistance below the waterline (ORC's RM4 = 0.43 T_max) | ORC |
| T_eff | effective draft, from D_i = S_h² / (π q T_eff²) with q = ½ρV_b² (ORC eq. 6.37); ORC's maximum effective draft is MHSD | ORC |
| N_h | hydrodynamic yaw moment, about z | project |

### Aerodynamic (subscript a)

| symbol | meaning | source |
|---|---|---|
| T_a | aerodynamic thrust, along the course | Parolini (ORC FRA) |
| S_a | aerodynamic side force, normal to the course in the water plane; + = to leeward | Parolini |
| M_a | aerodynamic heeling moment about the centreline at the waterline | Parolini (ORC HMA) |
| L_a, D_a | aerodynamic lift and drag, normal and parallel to the apparent wind | Parolini |
| C_L, C_D | sail lift and drag coefficients on the sail area | ORC |
| C_R, C_H | thrust and heeling-force coefficients: C_R = C_L sin β_AW − C_D cos β_AW, C_H = C_L cos β_AW + C_D sin β_AW | ORC (eq. 5.49-5.50) |
| Z_CE | height of the centre of effort above the waterline | ORC (ZCE) |
| flat, twist | sail depowering variables (an IOM can't reef; it changes rig, A, B or C) | ORC |
| N_a | aerodynamic yaw moment, about z | project |

ORC's heeling force FHA is normal to the heeled mast plane. S_a is
horizontal. For a force normal to the sail plane, S_a ≈ FHA cos φ.

### Sections and single appendages (foil2d)

Neither source covers 2D sections. These are the usual aerofoil symbols,
marked *project*.

* For one appendage, S_h and D_h mean its share of the hydrodynamic side
  force and drag. Examples are the fin in foil2d's ranking, or one part in
  appendage3d.
* The fin's drag has no residuary or wave-added part in this model, so for
  the fin D_h = D_v + D_i.

| symbol | meaning | source |
|---|---|---|
| α | section angle of attack (`aoa`) | project |
| c, b | chord; span of the fin below the hull | project |
| q | dynamic pressure ½ρV_b² | project |
| Re | chord Reynolds number V_b c / ν | project |
| C_l, C_d, C_m | section lift, drag and pitching-moment coefficients, per unit span on q c (`Cl`, `Cd`, `Cm`) | project |
| D_f, D_p | skin-friction and pressure drag of a section. Together they are its profile drag, D_v = D_f + D_p (`Cd_friction`, `Cd_pressure`) | project |
| e | span efficiency of the lifting-line induced drag (0.9 in foil2d) | project |
| Λ | sweep of a raked board's leading edge from the vertical (the Thistle's rake) | project |
| c_n, V_n, α_n | chord, velocity and section angle square to a swept leading edge: V_n = V_b cos Λ, β_Y = α_n cos Λ (simple sweep theory; foil2d's `chord`, `speed`, `aoa` in the Thistle study) | project |
| b_LE, b_v | span of a swept board along its leading edge, and its depth b_v = b_LE cos Λ | project |

* **α and leeway.** At equal span and side force, the induced part of the
  angle, S_h / (2π e q b²), is the same for every fin. So a difference in α
  is a difference in leeway: Δβ_Y = Δα. On a swept board
  (projects/foil2d/methodology-thistle.md) Δβ_Y = Δα_n cos Λ.

### Hull form and hydrostatics (ITTC)

The VPP's `particulars.csv` and `vpp hydro` (vpp/hydrostatics.py). The
hull's own numbers leave the appendages out; Δ, z_B, GM and MCT count
their volume. x is aft from the bow, z up from the water.

| symbol | meaning | `particulars.csv` |
|---|---|---|
| ∇, Δ | the hull's displaced volume; the boat's displacement (mass), appendages included | `volume`, `displacement` |
| LWL, BWL | waterline length (between its ends) and beam | `lwl` (`x_fwd`, `x_aft`), `bwl` |
| T_c | the hull's draft: its deepest point under water | `draft` |
| LCB, VCB | the hull's centre of buoyancy, x and z | `lcb`, `vcb` |
| LCF | x of the waterplane's centroid (the centre of flotation) | `lcf` |
| S, A_WP | wetted area; waterplane area | `wetted_area`, `waterplane_area` |
| A_X | the largest section under water, at `x_section` | `section_area` |
| C_B, C_P, C_X, C_WP | block ∇ / (LWL BWL T_c), prismatic ∇ / (A_X LWL), section A_X / (BWL T_c), waterplane A_WP / (LWL BWL) | `cb`, `cp`, `cx`, `cwp` |
| BM_T, BM_L | the hull's metacentric radii I_T / ∇, I_L / ∇ (I about the waterplane's centroid) | `bm_t`, `bm_l` |
| z_B, z_G | the boat's centre of buoyancy (appendages included) and centre of gravity, z | `z_b`, `z_g` |
| GM_T, GM_L | the boat's metacentric heights z_B + I / ∇ − z_G, ∇ with the appendages; GZ ≈ GM_T sin φ at small heel | `gm_t`, `gm_l` |
| MCT | moment to trim 1°: ρ g ∇ GM_L π/180 [N m/deg] | `mct` |
| — | immersion: ρ A_WP, mass per mm of sinkage [g/mm] | `immersion` |

## Balance equations

A steady state (Parolini eq. 2, written as magnitudes) is:

    T_a = D_h                  (along the course)
    S_a = S_h                  (across the course)
    M_a + M_h,dyn = RM_φ − RM_V    (roll about the centreline)
    N_a + N_h = 0              (yaw, with δ_R; project addition)

* A VPP finds, for each V_TW and β_TW, the V_b, φ, β_Y, δ_R and sail trim
  that satisfy these and give the greatest V_b.
* ORC solves only the first and third, with the side force implied. It
  states that "the yaw moment balance is ignored".
* An IOM is steered by the rudder alone, so this project keeps the yaw
  balance.

## Mapping to current outputs

Port tack, leeway β = β_Y. These relations were derived for this doc and
not yet tested. Check the signs on first use.

| symbol | project output | relation |
|---|---|---|
| D_h | appendage3d `drag_N`; hull `resistance_N` | equal. Both are already along the course: appendage3d turns the inflow by the leeway, and hull turns the geometry |
| S_h | appendage3d `side_N`; hull `side_force_N` | equal (+ to port, which is windward on port tack) |
| F_z,h | appendage3d `vertical_N`; hull `vertical_force_N` | equal |
| M_h,dyn | appendage3d `roll_moment_Nm` (about x through the bow at the waterline) | equal, + heels to starboard |
| N_h | appendage3d `yaw_moment_Nm` (about z at the bow) | equal |
| T_a | sails `drive_N`, `heel_force_N` (along and across the centreline; sails has no leeway) | T_a = drive_N cos β + heel_force_N sin β |
| S_a | sails | S_a = heel_force_N cos β − drive_N sin β |
| β_AW | sails `awa` (from the bow, so from the centreline) | β_AW = awa + β. Run sails at awa = β_AW − β |
| M_a | sails `heel_moment_Nm` (about x at the waterline) | equal, + heels to starboard |
| Z_CE | sails `z_ce` | equal |
| L_a, D_a | sails `lift_N`, `drag_N` | equal |
| C_D, C_S (hydrodynamic) | appendage3d `Cd`, `Cs` (on the fin's lateral area) | coefficient forms of D_h and S_h for the appendages |
| S_h (fin) | foil2d report `side_force` (`report/selection.csv`, with `report.fin_span`) | S_h = C_l q c b |
| D_v, D_i, D_h (fin) | foil2d report `drag_section`, `drag_induced`, `drag` | D_v = C_d q c b; D_i = S_h² / (2π q e b²) (lifting line, hull as a reflection plane); D_h = D_v + D_i |
| T_eff (fin) | foil2d `report.fin_span` b | the same induced drag in ORC's form: T_eff = b √(2e), about 0.48 m for b = 0.36 m and e = 0.9 |
| V_TW, β_TW | fullboat `tws`, `twa` | equal. fullboat turns the boat by the leeway, not the flow, and sets the wind relative to the flow. So `twa` is measured from the course |
| V_AW, β_AW | fullboat outputs `aws`, `awa_deg` | equal (from the course) |

## Sources

[parolini]: https://www.mate.polimi.it/biblioteca/add/qmox/10-2007.2007.pdf
[orc]: https://orc.org/uploads/files/Rules-Regulations/2026/ORC-VPP-Documentation-2026.pdf

* Parolini, N. & Quarteroni, A., *Mathematical models and numerical
  simulations for the America's Cup*, MOX report 10/2007 ([PDF][parolini]),
  section "Forces and moments on the water plane".
* Offshore Racing Congress, *ORC VPP Documentation 2026* ([PDF][orc]):
  * §3: equilibrium, FRA, FRW, HMA, RM;
  * §4.4: RM4;
  * §5.5: C_R, C_H;
  * §6.5: induced drag and effective draft.
