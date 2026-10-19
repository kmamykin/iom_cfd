# Keel bulb designs: what exists, what each is for, what to simulate

Research note, 2026-10-18. It asks:
* What keel bulb designs exist, on America's Cup and other full-size
  yachts and on radio-controlled models, and how they group.
* What each design optimises for: drag, righting moment, side force, and
  side effects such as pitch, weed and strength.
* What results and assumptions can set the parameters of IOM bulb
  simulations in this project (keel3d and bulb2d; first written for
  appendage3d), and what can check them.

Four web surveys gathered the material (America's Cup and grand prix,
academic hydrodynamics, model yachts, low-Reynolds-number bodies). Key
quotes and numbers were re-checked against the source text:
* the IOM rules (2026);
* SAILSetc TI23;
* Gilbert's *Bulb cant* page;
* the Open 50 bulb tank tables;
* Dress's drag table (1988);
* the Australia II paper (2024).

Labels used below:
* **measured**: tank, tunnel or tow test.
* **CFD**: a computed result.
* **designer** / **maker**: a claim without published data.
* **forum**: opinion.
* **estimate**: worked out here, with the inputs given. The scripts used
  ν = 1.138e-6 m²/s and ρ = 999 kg/m³ (fresh water at 15 °C, as in
  `defaults.yaml`).

Force and moment symbols (D_h, S_h, D_i, T_eff, leeway β_Y, heel φ) follow
[nomenclature.md](../nomenclature.md).

## Short answer

* **The IOM bulb works in a regime full-size data barely covers.**
  * Its length Reynolds number is about 2-5 × 10⁵, against about 10⁷ for an
    America's Cup bulb.
  * An IACC bulb is only 7-15 % laminar ([Parolini & Quarteroni][parolini]).
    An IOM bulb is probably laminar for most of its length (**estimate**,
    below).
  * So full-size lessons about shape carry over only in part. At IOM scale
    the boundary layer decides the drag.
* **Bulb designs fall into seven families.** Each one trades drag against a
  lower centre of gravity (VCG):
  1. short torpedo;
  2. long slender torpedo;
  3. flattened, elliptic, flat-bottomed or chined;
  4. beaver tail;
  5. winglets;
  6. keel layout (T, L, integrated, tandem);
  7. laminar-flow bodies.

  The table in "Design families" says what each optimises and what it
  costs.
* **IOM practice has converged.**
  * Round section, length/diameter (L/D) about 9-10, length 345-365 mm,
    about 2.4 kg (**maker**).
  * Set 2-3° nose up to the hull ([SAILSetc][ti23], [Gilbert][bulbcant]).
  * The fin slot sits near the bulb's centre of gravity.
  * The move from L/D 5 to 10 happened in 1998 ([Bantock][bantock2]).
  * Flat-bottomed IOM bulbs are new (2021 on) and have maker claims only.
  * Winglets are probably not allowed (class commentary, not rule text).
* **Length barely changes drag at a fixed lead mass, by the formulas.**
  * Friction plus Hoerner's form factor gives a flat optimum: within 1 %
    from L/D 6 to 10 in turbulent flow (**estimate**).
  * The only IOM tow test found the longer bulbs faster: 350 mm against
    250 mm was +1.9 % speed at 0.5 m/s ([Gilbert, MY 184][my184],
    **measured**).
  * That is roughly 6-20 times the gap the attached-flow formulas predict
    (**estimate**). The likely cause is laminar separation on the fat bulb's
    tail. The CFD must be able to capture it.
* **The bulb end-plates the fin.**
  * Quarter-scale Open 50 tank test: adding the bulb raised drag 11 % and
    side force 17-24 % at the same leeway ([Sfakianaki et al.][sfak],
    **measured**).
  * A round bulb moves the tip vortex up. A flat bottom with sharp edges
    keeps it low.
  * The ORC rating VPP builds this in: a round or elliptic bulb reduces the
    keel's effective draft T_eff, a flat-topped bulb or winglets raise it
    ([ORC 2026][orc] §4.2.7).
* **For the simulations:**
  * keel3d's (and appendage3d's) fully turbulent kOmegaSST with wall
    functions is the wrong tool for bulb shape. Depending on what the
    boundary layer does, the baseline bulb's drag at 1 m/s ranges from
    about 37 to over 160 mN (**estimate**).
  * Fully turbulent is not even a safe upper bound: laminar separation can
    cost more ([Dress][dress], [Mishra et al.][mishra]).
  * Use kOmegaSSTLM at y+ ≈ 1 with a Tu sweep, as foil2d does. Bracket it
    with fully turbulent runs.
  * Compare bulbs at equal lead mass.
  * Add cant, section aspect and tail shape as parameters.
  * Validate against Dress's laminar body, whose Reynolds number overlaps
    the IOM range.

## The baseline bulb in numbers

`BulbSpec` defaults (`src/iomcfd/geometry/appendages.py`):
* elliptic nose, parabolic tail;
* maximum diameter at 0.40 L;
* axis at z = -0.40 m.

All values below are **estimates** from integrating that profile.

| quantity | value |
|---|---|
| length × diameter, L/D | 330 × 37.5 mm, 8.8 |
| volume, mass in lead | 213.8 cm³, 2.425 kg |
| wetted area | 279 cm² |
| frontal area | 11.0 cm² |
| V^(2/3) | 35.8 cm² |
| prismatic coefficient | 0.587 |
| centroid | 0.434 L from the nose (x = 0.443 m with the defaults, 26 mm ahead of the fin tip's quarter chord) |
| bottom (draft) | 418.75 mm below the waterline (rule maximum 420 mm) |

| speed | Re_L | Re_V = U V^(1/3) / ν | laminar Cf (Blasius) | turbulent Cf (ITTC-57) |
|---|---|---|---|---|
| 0.6 m/s | 1.7 × 10⁵ | 3.2 × 10⁴ | 0.0032 | 0.0071 |
| 1.0 m/s | 2.9 × 10⁵ | 5.3 × 10⁴ | 0.0025 | 0.0063 |
| 1.6 m/s | 4.6 × 10⁵ | 8.4 × 10⁴ | 0.0019 | 0.0056 |

Mass check:
* A real fin weighs 70-130 g.
* A 2.425 kg bulb plus a 100 g fin is 2.525 kg, over the 2500 g keel limit
  ([rules][iomrules] C.6.4).
* Real IOM bulbs are about 2.4 kg. At L/D 8.8 that is 329 × 37.4 mm
  (**estimate**). The difference doesn't matter for drag, but bulb
  comparisons should hold mass fixed.

## Design families and what each optimises

| family | examples | optimises for | costs and side effects |
|---|---|---|---|
| **Short torpedo**, L/D 4-6, round | IOM before 1998 (L/D about 5; [Bantock][bantock2]); Oracle USA-76, 2003 ("short and squat… to keep the wetted surface area down", [Sheahan][sheahan], **press**); NZL 32, 1995: 4.55 m × 1.2 m wide × 0.8 m high, 20 t ([Te Papa][tepapa]) | least wetted area per volume; light-air and downwind drag; manoeuvring (low yaw inertia) | higher VCG; more pressure drag. At low Re: laminar separation on the steeper tail ([Dress][dress], [Han & Patel][hanpatel]) |
| **Long slender torpedo**, L/D 8-12, round | every current IOM bulb; NZL 82 (2003, about 7 m against about 5 m typical, **press**); Marblehead and 10R | lower VCG at the draft limit; lower pressure drag; at model scale, lower Cf from the longer run | more wetted area; bending strength (Bantock calls this the limit); yaw and pitch inertia; harder pre-starts ([Ruiz de Elvira][alinghi03], **designer**) |
| **Flattened**: elliptic, flat-bottomed or chined | VO65 ("generous amount of 'squish'", [Farr][vo65]); IMOCA (flat bottom, [BoatNews][imoca-bulb]); Farr TP52 (chined, [Farr 533][farr533]); SAILSetc pattern 1.2:1 ([pattern][pattern]); MC-1 "flat bulb" and the Sailboat RC 2021 bulb (IOM) | lower VCG for the same volume; end-plating; flat bottom and sharp edges keep the tip vortex low ([Ljungqvist][ljungqvist], **CFD**); side force at heel | more wetted area (+3 % at 1.5:1, +9 % at 2:1 at equal section area, **estimate**); lift at incidence, so pitch and heave forces. Model results are mixed: Bantock's oval IOM bulb was "about as good… on the beat, but not quite as good on the run" ([oval bulb][ovalbulb]); an elliptic 36R bulb was blamed for nose-diving ([MI 50][mi50]) |
| **Beaver tail** (flat, wide tail) | VO65, IMOCA, Britannia II's AC75 foil body ([Slooff][slooff]); the Valenza Marblehead ("thin beaver tail", [Valenza][valenza]); the Chalmers T-bulb ([Axfors][axfors]) | effective span (pushes the tip flow down); avoids the axial vortex a steep, pointed tail sheds ([Holroyd][holroyd], **designer**) | wetted area; lift at incidence. Slooff thinks it is "probably better than a bulb with a pointed rear end" (**opinion**) |
| **Winglets** | Australia II (1983); the IACC norm (aft, mid-bulb, or just aft of the fin); ITA 86 (angled down) | induced drag and effective span: NLR computed "as much as 35 %" less induced drag for Australia II ([van Oossanen & Peterson][vo-pet]); 12 Metre wind tunnel: about 9 % of upwind drag ([Howlett][howlett], **measured**) | friction drag; a separation bubble at the winglet-bulb junction ([Parolini][parolini]); downwind penalty; weed (Young America swept them for kelp, [MIT][mit95]); pitching moment. They pay only at high keel loading ([Orych et al.][orych]). Chalmers IACC model at 4° leeway: no L/D gain (**measured**, [Mylonas][mylonas]). IOM: probably illegal (see "Model yachts") |
| **Keel layout**: T, L, integrated, tandem | Chalmers YD-40 study ([Axfors & Tunander][axfors]); FAST 2000 tandem ([van Oossanen][fast2000]); IOM "reverse L" with a forward bulb ([Gilbert][fillets]) | the T-bulb lets the fin sit for helm balance and the bulb for trim; tandem splits lead and side force | a T-keel's fin and bulb pressure minima at the same x gave "massive separation" (**CFD**, [Axfors][axfors]); a bulb well forward of the fin twists it ([Gilbert][fillets], [fin-stiffness.md](fin-stiffness.md)) |
| **Laminar-flow bodies** | Young's bodies (SAILSetc 1990-98, [TI23][ti23]); Myring profiles; Parsons-Goodson and Carmichael laminar bodies ([Parsons & Goodson][pg]) | a long laminar run: maximum thickness aft, pressure falling over the forebody | at Re_L below about 7 × 10⁵, laminar separation on the tail with little reattachment. Measured drag can exceed fully turbulent drag ([Dress][dress]) |

## America's Cup and other full-size yachts

**12 Metre era.**
* Australia II (1983) had no separate bulb. The lead was in an
  inverted-taper keel and its winglets. The winglets were made thicker "to
  fit more lead ballast" ([van Oossanen & Peterson 2024][vo-pet]).
* One-third-scale tank predictions of speed made good to windward
  (**measured**, from the same paper):

  | true wind | base boat | + inverted keel and winglets | final boat |
  |---|---|---|---|
  | 8 kn | 4.90 kn | 4.97 kn | 5.04 kn |
  | 16 kn | 6.80 kn | 6.89 kn | 6.91 kn |

* Howlett reports a 12 Metre keel that looked worse in a 1:10 tank than
  conventional keels. He blames scale effects ([Howlett][howlett]). Model
  scale can reverse full-scale rankings.

**IACC era, 1992-2007.**
* The rule ([v5.0][acc5]) set draft at 4.1 m and ballast density at
  9,000-11,300 kg/m³. Appendages could be no wider than the hull above
  them. Ballast-carrying appendages could not rotate.
* Bulbs were about 19-21 t, roughly 75-85 % of the boat's weight
  ([Pedrick][pedrick], [Practical Sailor][practical]). Shapes ranged:
  * short and fat (USA-76, USA 87, Luna Rossa 2000, with its maximum
    thickness just aft of the fin);
  * long and slender (NZL 82, NZL 84, Alinghi);
  * nearly square undersides on some 2007 boats ([Yachting World][yw07],
    **press**).
* NZL 32 (1995) is the one with published dimensions: 4.55 m long,
  1.2 m wide, 0.8 m high, about 20 t ([Te Papa][tepapa]). That is
  width/height 1.5 and length/height 5.7 (**estimate**).
* Team New Zealand, 2003 ([Holroyd][holroyd], **designer**):
  * They tested six bulbs in a wind tunnel, then ran CFX with k-ω.
  * Too steep a tail sheds "an axial vortex".
  * Squashing the bulb against the depth limit "tends to increase its
    surface area".
  * The gain was "about a percent" of drag.
* Mike Drummond on NZL 82's long bulb (**designer**): "more stability…
  extra wetted surface area… an extra drag item in light airs"
  ([sailing.org][drummond]).
* Where to put winglets was never settled. CFD could not decide, and crews
  preferred mid-bulb over aft ([Davidson][davidson], **designer**).
* Alinghi with EPFL ([Parolini & Quarteroni][parolini], **CFD**):
  * A slender bulb against a short one of equal volume trades pressure drag
    against friction, so the transition location decides it. They used
    SST with Langtry-Menter transition.
  * They found a horseshoe vortex at the fin-bulb junction and reshaped the
    bulb locally (fillets) to weaken it.
  * Winglets cut wake vorticity, more so in yaw.
* Two-boat teams ran a short, round bulb with a light round hull against a
  long bulb with a narrow hull ([Cupinfo][cupinfo], **press**).
* Contento et al. tank-tested three bulb lengths for heave and pitch in
  waves ([abstract][contento]).
* Geremia et al. optimised an IACC bulb for drag against VCG at fixed
  volume (17 variables, CFX, 480 designs). They published no drag numbers
  ([GECCO 2007][geremia]).

**AC75 (2021 on).**
* The ballast is in the canting foil arms. A foil wing assembly weighs
  550-580 kg, and material in new wings may not exceed 9,000 kg/m³
  ([AC75 rule v3.01][ac75]).
* Slooff on the shapes: Britannia I had a substantial bulb. Britannia II had
  a short body with a small beaver tail ([Scuttlebutt][slooff], **opinion**).

**Other classes.**
* **VO65** ([Farr in Seahorse][vo65], **designer**):
  * The bulb is long, with "squish" for a lower VCG at the cost of wetted
    area.
  * The flat tail adds effective span.
  * The keel pin is inclined 5°, which gives "a large vertical lift force".
* **IMOCA 60:** the bulb weighs 2.2-2.85 t. The rule puts the bulb's centre
  of gravity ahead of the fin's torsional axis
  ([IMOCA rule 2019][imoca]). The bulb is flat on the bottom for the lowest
  weight ([BoatNews][imoca-bulb]).
* **TP52:** the bulb is limited to 3.8 t, and a VCG limit drove the designs
  for a time. Farr's 2003 boat used a "chined bulb shape to improve the
  upwind performance and achieve the deepest center of gravity"
  ([Farr 533][farr533]).
* **Open 50, quarter-scale tank test** ([Sfakianaki et al. 2013][sfak],
  **measured**). This is the nearest measured bulb at Reynolds numbers
  close to the IOM's.
  * The model bulb was about 0.6 × 0.125 m (L/D 4.8), so Re_L ≈ 6 × 10⁵ at
    1 m/s. The fin was NACA 64A015. There was a 0.5 mm trip wire on the
    bulb.

  | speed | drag increase from adding the bulb, leeway 0-7° | side-force increase at the same leeway |
  |---|---|---|
  | 0.5 m/s | 5.1-12.6 % | 24 % |
  | 1 m/s | 10.9-11.2 % | 17 % |
  | 2 m/s | 11.8-14.8 % | 19 % |

  * The authors put the side-force gain down to the bulb suppressing the
    fin's tip vortex.
  * At 1 m/s and 0° the bulb adds 0.064 kp (0.63 N). On a wetted area of
    about 0.18 m², that is C_D,wet ≈ 0.007, including the junction and the
    trip (**estimate**).
  * Removing the keel's turbulence stimulators changed the side force
    noticeably. Laminar flow matters at this scale.

## Model yachts

### IOM bulbs on the market

| bulb | length × diameter | L/D | mass | notes | fin slot | source |
|---|---|---|---|---|---|---|
| SAILSetc IOM ballast (IKON onward) | 350 mm, diameter not stated | about 10 | 2.4 kg finished | round; lead-antimony; brass rod on the axis; tail cast thick, then faired "to a fine ended conical shape" | 8 × 14 × 97 mm, 105-202 mm from the nose, "45 mm forward to 52 mm aft of lcg" | [maker][ti23], [maker][sailsetc-ballast] |
| RadioSailingShop HC1 ("Bantock/Pikanto/Fraktal style") | 345 × 37 mm | 9.3 | about 2.4 kg | "latest round section" | 60 × 7 mm, front 112 mm from the nose | [maker][hc1] |
| Craig Smith CK1 | 365 × 35 mm | 10.4 | about 2.4 kg | "latest generation" | 80 × 5 mm, front 120 mm from the nose | [maker][ck1] |
| MC-1 "Next Generation IOM Flat Bulb" | 350 mm, diameter not stated | - | not stated | "maximum weight lower down sections with lightly flattened tail sections" | 72 mm, from 150 mm back | [maker][mc1] |
| Sailboat RC (VISS, K2), 2021 | not stated | - | not stated | carbon or glass coated, steel end plates, "improved weight distribution"; newer fins have a "flat bulb connection shape" | fits Craig Smith fins | [maker][sbrc], [fin][sbrc-fin] |
| MX Components | not stated | - | "circa 2380 g" | glass coated | - | [maker][mx] |
| Anders Wallin, home cast (2003) | 355 × 38 mm | 9.3 | 2.4 kg target | round, "NACA 0010-34 profile" | - | [builder][wallin] |
| Gary Cameron, TS2 proposal | 360 × 36.4 mm | 9.9 | - | "the best trade off", from XFOIL and UIUC data (not measured) | - | [designer][bulbsize] |

The winning V12, VISS and Venti designs publish no bulb dimensions, nor do
Vickers and Rob Nelson. The slot fronts above sit at 30-43 % of the bulb's
length from the nose, so the slot centres are at about 41-53 %
(**estimate**). SAILSetc puts the slot "approximately at the longitudinal
centre of gravity of the ballast" to "minimise fin twist and deflection"
([TI23][ti23]).

### Trends and designer guidance

* **Longer and thinner since 1998** (**designer**). "Until early 1998 most
  ballasts in the UK had a L/D ratio of around 5. TS2 uses one with L/D
  around 7 and IKON uses an L/D ratio around 10" ([Bantock][bantock2]).
  * Bantock's fits to Hoerner's data "showed a steadily decreasing drag for
    ballast bulbs as the length:diameter ratio increased"
    ([Seahorse][seahorse]).
  * He names the limits as "long, thin ballast strength and the increased
    moment of inertia in yaw and pitch". He judges the pitch inertia minor,
    because IOMs "already have incredibly high inertia in pitch due to the
    deep draught and tall rig".
  * Howlett gives model-yacht (Marblehead) bulbs as "Young's Laminar
    bodies" at d/l ≈ 1:6, and says "finer forms with ratios as extreme as
    1:10 may have a performance advantage" ([Howlett][howlett]).
* **Nose-up cant of 2-3°.**
  * SAILSetc: "drop the aft end of the ballast by a few mm… aligned with the
    water flow when the hull trims down by the bow… 2 to 3 degrees of 'nose
    up' is best for all round performance" ([TI23][ti23], **maker**).
  * Gilbert works the cant out as leeway × sin(heel), plus the bow-down
    trim. 4° leeway at 30° heel gives 2° ([Bulb cant][bulbcant],
    **designer**, a calculation with no test). His guidance:
    * 2° all round;
    * 3° for wide-transom hulls or top-of-suit wind;
    * about 1° less if the wind rarely exceeds 6 kn.
  * Forum posts give "1 to 3 degrees", and "Pointing down is a no-no"
    (**forum**).
  * Toe (yaw of the bulb) is not discussed anywhere. Makers only stress
    lining up the fin and bulb axes with a jig.
* **Fillets.** SAILSetc tried a prototype bulb "with fin fillets" at the
  2001 Worlds ([report][worlds01], **designer**). No data was found.
* **Fin over the bulb.**
  * Gilbert puts the bulb's centre of gravity under the hull's centre of
    buoyancy ([fin position][finposn]).
  * The Corbie 5 manual puts the bulb's balance point 10 mm aft of the fin's
    leading edge at its base ([builder][corbie]).
  * No source states a "quarter chord over the CG" rule.
* **Manoeuvring.** "Some skippers are moving away from long leads" for
  faster turning ([forum, 2004][iomica-long]).
* **Other classes** (**maker**):
  * Marblehead bulbs are 3.2-3.6 kg, for example 355 × 44 mm at 3.4 kg.
  * 10R: 412 × 45 mm at 3.8 kg.
  * RG65: 255 × 25 mm at 0.7 kg ([RadioSailingShop][mhb]).
  * SAILSetc uses flattened, winged bulbs on its 6 Metre and A Class models
    ([TI23][ti23]).

### IOM rules that bound the bulb

From [IOM Class Rules 2026][iomrules]:
* **C.4.1:** draft 370-420 mm, in fresh water.
* **C.6.4:** keel, fin plus bulb, 2200-2500 g.
* **C.6.3:** the keel may not move or rotate relative to the hull except by
  flexing. So cant is fixed for an event.
* **E.1.1(a):** the keel "may comprise a fin and a bulb".
* **E.3.1:** no material denser than lead (11,340 kg/m³).
* **E.3.2(b):** no articulation and no openings water can flow through.
* **E.4.1:** "The largest transverse dimension except for the lowest 60 mm
  … 20 mm".

Two readings:
* **Winglets.** The class's rules-history commentary says defining the keel
  as fin plus bulb "implies that the 'bulb' cannot be a 'bulb with
  winglets'" ([history][iomhist]). That is commentary, not rule text.
* **Fillets** (my reading of E.4.1). Width over 20 mm is allowed only in the
  lowest 60 mm. A 37.5 mm bulb sitting at the draft leaves about 22 mm of
  fin above the bulb where a fillet may be wider than 20 mm.

## Measurements at or near IOM scale

| test | what | result | use |
|---|---|---|---|
| Gilbert, MY 184 ([page][my184], **measured**) | Fraktal hull towed by a falling weight at about 0.5 and 1.0 m/s; bulbs about 250 mm ("fat", a 1992 Young body), 300 mm (1998), 350 mm (2015); standard error about 0.15 % | 300 vs 250 mm: +0.6 % speed at high speed, +1.4 % at low. 350 vs 250 mm: about +1.9 % at low speed. No masses or diameters given | the only IOM bulb-shape comparison. +1.9 % speed is about 3.5-4 % less resistance. If the tow pull is about 20 gf at 0.5 m/s ([MY 174][my174]), that is about 7 mN (**estimate**) |
| Gilbert, MY 175 ([page][my175], **measured**) | upright hull, about 0.5 m/s, bulb cant 0, 2, 5° | 0.480, 0.480, 0.473 m/s | 2° costs nothing upright; 5° costs about 1.5 % |
| Sfakianaki et al. ([JMR][sfak], **measured**) | Open 50 quarter-scale, keel with and without bulb, 0.5-2 m/s, leeway 0-7° | drag +11 %, side force +17-24 % (table above) | the end-plate effect; Re_L about 6 × 10⁵ |
| Dress 1988 ([NASA][dress], **measured**) | laminar-flow body of revolution, 12 in × 2.68 in (L/D 4.5), magnetically suspended (no support interference), coordinates tabulated | C_D,wet: 0.0118 at R_L 3.6 × 10⁵; 0.0120 at 4.4 × 10⁵; 0.0105 at 6.9 × 10⁵; 0.0079 at 9.4 × 10⁵; 0.0045 at 1.34 × 10⁶. Below R_L ≈ 7 × 10⁵, laminar separation from x/L ≈ 0.50-0.55 "with either no reattachment or reattachment close to the tail" | **the best validation case for the transition model**: same Re, public geometry. At IOM Re its drag is about twice turbulent friction |
| Han & Patel 1977 ([IIHR][hanpatel], **measured**) | low-drag body (maximum radius at 0.44 L) in a water flume and a wind tunnel | at Re_L ≈ 8 × 10⁴: laminar separation at x/L ≈ 0.56, turbulent reattachment near 0.60 (a toroidal bubble) | where the bubble sits |
| Axfors & Tunander ([Chalmers][axfors], **measured**) | four keels (fin, L, integrated L, T-bulb) of equal righting moment, wind tunnel, Re ≈ 1.4 × 10⁶, tripped | C_D at 0°: fin 0.0108, T-bulb 0.0121, L-bulbs 0.0129-0.0130 (on K1's lateral area). RANS over-predicted C_L by 7-13 % and C_D by 3-7 % | the T-bulb lesson: separate the fin's and the bulb's pressure minima |

**The tow test against the formulas** (**estimate**):
* Hold the mass fixed (213.8 cm³) and use the same nose and tail family.
  The formulas then give these drags at 0.5 m/s:

  | bulb | length × diameter | fully turbulent | laminar |
  |---|---|---|---|
  | fat | 250 × 43.1 mm | 28.4 mN | 14.0 mN |
  | standard | 350 × 36.4 mm | 28.0 mN | 12.9 mN |

* That is a 0.3-1.1 mN gap. The tow test measured something like 7 mN,
  with unknown bulb masses and shapes.
* The gap suggests the fat bulb paid for something the attached-flow
  formulas leave out. Laminar separation on its tail is the likely
  candidate (inference).

## Physics that matters at IOM scale

1. **Friction is most of the drag. The boundary layer state sets it.**
   * Hoerner's form factor is 1 + 1.5(d/l)^1.5 + 7(d/l)³ ([Hoerner][hoerner],
     ch. VI). It gives 1.07 for the baseline. Other aircraft correlations
     give 1.09-1.11 ([OpenVSP][openvsp], [Götten][gotten]).
   * Pressure drag is therefore only about 6-10 % of the total if the flow
     stays attached.
   * Baseline drag at 1 m/s (**estimate**, from 279 cm² wetted area):

   | boundary layer | C_D,wet | drag at 0.6 / 1.0 / 1.6 m/s |
   |---|---|---|
   | laminar, attached (Blasius × form factor) | 0.0027 | 17 / 37 / 74 mN |
   | Hoerner's laminar-body fit (his eq. 24) | 0.004 | 24 / 56 / 123 mN |
   | fully turbulent (ITTC-57 × form factor) | 0.0067 | 38 / 93 / 213 mN |
   | Open 50 model bulb, tripped (above) | 0.007 | 35 / 98 / 250 mN |
   | laminar separation, Dress-like | 0.012 | 60 / 167 / 429 mN |

   A fat laminar body at R_L 4 × 10⁵ measured about 0.012 ([Dress][dress]).
   The slender baseline, with its gentler tail, should sit lower, but nobody
   has measured it. Hoerner: between R_l 10⁵ and 10⁶ measured body drag
   runs "parallel to the laminar skin-friction" line. He found "not a
   single source" below R_l = 10⁵.

2. **Where transition happens on the baseline** (**estimate**, by the
   low-Reynolds-number survey: an axisymmetric panel method, Thwaites's
   laminar boundary layer and Michel's transition criterion):
   * Peak velocity is u/U = 1.034 (Cp_min = -0.07) at x/L = 0.33.
   * Laminar separation is at x/L ≈ 0.74.
   * Michel transition is at x/L ≈ 0.72, 0.69 and 0.67 at 0.6, 1.0 and
     1.6 m/s.

   So the boundary layer is laminar for about two-thirds of the length,
   then transitions through a separation bubble on the tail. Moving the
   maximum diameter to 0.45-0.50 L moves separation only to about 0.75: the
   tail recovery controls it, not the nose. This ignores viscous-inviscid
   interaction, and Michel is a 2D correlation.

3. **Fineness at fixed mass is a flat optimum.** It is decided by
   separation, VCG and strength, not by friction (**estimate**, same nose
   and tail family, 213.8 cm³, bottom held at the draft):

   | L/D | L × D (mm) | drag at 1 m/s, turbulent / laminar | bulb CG above its bottom | bulb's righting moment |
   |---|---|---|---|---|
   | 5 | 226 × 45.3 | 95.9 / 41.4 mN | 22.6 mm | -1.0 % |
   | 6 | 256 × 42.6 | 93.6 / 39.3 mN | 21.3 mm | -0.7 % |
   | 7 | 283 × 40.5 | 92.9 / 38.0 mN | 20.2 mm | -0.4 % |
   | 8.8 | 330 × 37.5 | 93.2 / 36.7 mN | 18.8 mm | 0 |
   | 10 | 359 × 35.9 | 93.9 / 36.2 mN | 18.0 mm | +0.2 % |
   | 12 | 406 × 33.8 | 95.4 / 35.7 mN | 16.9 mm | +0.5 % |

   * Righting moment here means the bulb's weight times its depth below an
     assumed hull centre of buoyancy at z = -0.02 m (a lever of about
     380 mm). The whole boat's righting moment changes by a smaller
     fraction.
   * Literature optima at fixed volume:
     * Hoerner: l/d 4 for a fixed friction coefficient ("rather flat").
     * Young: about 5 ([Young][young]).
     * Myring: 5.5 ([Myring][myring]).
     * Walker et al.: about 6.2 in the transitional regime, and no optimum
       when fully laminar ([Walker][walker]).
     * Parsons-Goodson laminar optima: L/D 8.5 at the lowest Re_V they
       studied, 5 × 10⁶ ([P & G][pg]).
   * With Cf taken at each body's own Re_L, the turbulent optimum moves to
     about 7.5, within 1 % from 6 to 10.

4. **Flattening buys VCG at a small wetted-area cost** (**estimate**,
   elliptic section of equal area, bottom held at the draft):

   | width/height | width × height (mm) | perimeter | CG lower by | bulb's righting moment |
   |---|---|---|---|---|
   | 1.25 | 41.9 × 33.5 | +0.9 % | 2.0 mm | +0.5 % |
   | 1.5 | 45.9 × 30.6 | +3.1 % | 3.4 mm | +0.9 % |
   | 2.0 | 53.0 × 26.5 | +9.0 % | 5.5 mm | +1.5 % |

   * Friction drag rises roughly with the perimeter.
   * An elliptic body also lifts at incidence. Round bodies have "little
     lift". At width/height 1-1.5, lift slope is about 0.005-0.008 per
     degree on width², rising to 0.024 at 3:1 ([Hoerner, Lift][hoerner-lift]).
     That is the source of the pitch and nose-diving side effects.
   * No equal-volume measurement of round against elliptic bodies was found.

5. **Incidence: the bulb sees pitch whenever the boat heels with leeway.**
   * The pitch angle is about leeway × sin(heel), minus the bow-down trim.
   * A closed body in potential flow has zero lift and a Munk moment. At
     1 m/s that moment is 7, 14 and 21 mN·m at 2, 4 and 6°
     ([Allen & Perkins][allen]; **estimate** using a prolate spheroid of
     L/D 8.8).
   * Viscous crossflow adds a normal force of about 5, 18 and 40 mN
     (**estimate**: crossflow drag coefficient 1.2, factor 0.7).
   * At 4° this is 0.2-0.5 times the bulb's drag.
   * Langtry-Menter cannot predict crossflow transition, which a body at
     incidence has ([Xu et al.][xu]).

6. **The fin-bulb junction.**
   * Hoerner's wing-wall formula, ΔD = q c² (0.8 (t/c)³ - 0.0003), gives
     0.35 mN for an 8 % fin at 80 mm chord and 1 m/s, and about zero at 7 %
     (**estimate**). That is small, but it comes from turbulent data.
   * A laminar junction sheds horseshoe vortices periodically. Swept
     leading-edge fillets remove the separation ahead of the fin, and an
     optimum fillet size exists ([Harvey et al.][harvey],
     [Kubendran & Harvey][kubendran]).
   * Hoerner puts the optimum fillet radius at 4-8 % of chord: about 3-6 mm
     here. Interference is small with the wing near the body's nose and
     largest "somewhat aft of the maximum thickness"
     ([Hoerner][hoerner], ch. VIII).
   * RANS over-predicts junction corner separation, even with QCR
     ([NASA juncture flow][juncture]).
   * Keep the fin's and the bulb's pressure minima apart ([Axfors][axfors]).
     In the defaults the bulb's minimum is at x ≈ 0.409 m. The fin's maximum
     thickness at its tip is at x ≈ 0.473 m, about 64 mm aft.

7. **End-plate effect.**
   * The bulb adds 17-24 % side force on the Open 50 model ([Sfakianaki][sfak]).
   * A round bulb "moves the trailing vortex further up". The best tip is
     square and sharp-edged ([Ljungqvist][ljungqvist], citing Larsson &
     Eliasson).
   * De Saix measured the fin's share of side force on a 5.5 Metre falling
     from 80 % upright to 62 % at 30° heel ([Howlett][howlett]).
   * **The ORC VPP corrects effective draft for bulbs and winglets**
     ([ORC 2026][orc] §4.2.7, read for this note).
     * Its rule: "A ballast bulb with circular (or elliptical) cross
       section reduces the effect[ive] span of the keel fin. A well
       designed wing keel extends the effective span."
     * The shape of the bulb's top matters, through an upper-bulb shape
       factor (UPBULBF). "A straight shape (e.g. a Scheel Keel) has a
       positive effect, although a round shape has negative effect on
       effective draft."
     * The correction ΔD/MHSD is a function of:
       * the bulb's and winglets' added widths, WBULB and WWING;
       * the keel's draft DHK0, maximum width MAXW, and the draft TMAXW at
         that width.

       Its constants are "based on CFD calculations for eight bulb or
       winglet configurations", and "the multiplier of 0.5… is an arbitrary
       reduction of the bulb credit".
     * ORC uses T_eff in D_i = S_h² / (π q T_eff²) (§6.5, eq. 6.37).
     * The correction is fitted to full-size keels. At IOM scale it is a
       hypothesis to test, not a number to use.

8. **The free surface doesn't matter for the bulb.**
   * The bulb is about 10 diameters deep. The submerged-body wave factor
     exp(-2gh/U²) is 4 × 10⁻⁴ at 1 m/s and 0.05 at 1.6 m/s (**estimate**).
   * keel3d's double body and appendage3d's symmetry plane are fine for
     the bulb. At the top speed and heel, one check against `hull` with
     appendages would confirm it.

## What this means for the simulations

The bulb work runs in two projects (added 2026-10-19):
* **keel3d** (Track A): the whole underwater boat, canoe body, fin and bulb
  sized by the IOM rules. Steady kOmegaSST, fully turbulent, with wall
  functions and 5 prism layers; double body. Its bulb holds 2380 g of
  lead (2.5 kg keel − 120 g fin) with its bottom at the 420 mm draft. The
  default is NACA 0007 revolved, 463 × 32.4 mm (L/D 14.3), longer than any
  IOM bulb on the market; the bulb studies use NACA 0011, 343 × 37.7 mm
  (L/D 9.1), like the HC1 (345 × 37 mm). Heel turns the boat, so the heeled bulb sees
  leeway × sin(heel) of pitch. Good for side force, the end-plate effect and
  induced drag; not for ranking bulbs by drag.
* **bulb2d** (Track B): the bulb alone as a body of revolution at zero
  incidence, on an axisymmetric wedge mesh with kOmegaSSTLM: the
  boundary-layer questions.

appendage3d (fin, bulb and rudder under a flat plate) has the same
turbulence model as keel3d and is not used for bulbs.

**Recommendations**, in order:

1. **Model transition on the bulb.** *Done in bulb2d; keel3d stays fully
   turbulent.*
   * Use kOmegaSSTLM as foil2d does: decay control, Tu swept over 0.1, 0.5
     and 1 %.
   * In Alinghi's appendage CFD (a downwind case), raising the inlet Tu
     from 0.1 % to 0.5 % cut the total drag error from 16 % to 1 %. The bulb's
     laminar extent fell from 18-26 % to 2-2.5 %, against 2 % measured
     ([Parolini][parolini], Table 2). The Tu that matched the measured
     transition line also matched the force, so they calibrated Tu on one
     measured transition location. Pond turbulence is unknown
     ([surface-roughness.md](surface-roughness.md)), so
     a visualised transition line on a real bulb would be worth having.
   * Keep fully turbulent SST as a bracket, but not as an upper bound.
   * The mesh needs y+ ≈ 1 with 20-30 prism layers at a growth of 1.1-1.2
     ([Riedeberger & Rist][riedeberger]). For the bulb that means a first
     cell of about 0.02 mm. The boundary layer at the tail is about 3 mm
     thick if laminar and about 10 mm if turbulent (**estimate**).
   * snappyHexMesh struggles with that many layers. Budget for it.
2. **Run the isolated, upright, zero-incidence bulb as a 2D axisymmetric
   case first.** *Done: bulb2d, a wedge cut from foil2d's C-grid.*
   * It is cheap enough for the transition model, Tu sweeps and mesh
     studies.
   * It covers the questions where the fin doesn't matter: fineness at
     fixed mass, maximum-thickness position, nose and tail shape.
   * Use 3D keel3d for the junction, incidence, heel and flattened
     sections.
3. **Compare at equal mass.** *Done: keel3d sizes the bulb from the lead the
   keel limit leaves (2380 g); bulb2d takes `mass`.*
   * Add a `bulb_mass` input that solves for the diameter (or the scale)
     given length, shape and section aspect. Set it to about 2.40 kg (a
     legal keel with a 100 g fin).
   * Report the bulb's CG height and its righting-moment lever with the
     drag. A shape gains on one and loses on the other, and the study should
     show both.
4. **Expose the design parameters the literature says matter.** *Done in
   keel3d: `bulb_cant`, `bulb_aspect`, `bulb_top`/`bulb_bottom` (flat top or
   bottom), and `bulb_x` (slot position). In bulb2d: fineness, `max_at`,
   `tail_exp`. Not done: a nose exponent, a beaver tail, fillets.*
   * `bulb_cant`: nose-up degrees, 0-4°. Rotate about the bulb centroid,
     or the fin tip.
   * `bulb_aspect`: width/height at equal section area, 1-2. Optionally a
     flat-bottom variant.
   * `bulb_tail_exp`: already in `BulbSpec`; it sets the tail closure
     angle. Also a beaver-tail option.
   * a nose exponent, like Myring's n.
   * the fin slot position along the bulb. Today it follows from `fin_x`
     and `bulb_x`; better to express it as a fraction of bulb length.
   * a fillet radius of 0-8 mm at the fin-bulb junction (legal; see
     "IOM rules").
5. **Add outputs.** *Done in keel3d: `drag_bulb_friction_N`,
   `drag_bulb_pressure_N`, `vertical_bulb_N`, `pitch_bulb_Nm`, `bulb_z_cg`,
   `bulb: false` for the fin alone, and `T_eff_m` in `polar_fits.csv`.*
   * Bulb friction and pressure drag separately.
   * Bulb vertical force and pitching moment (about the bulb centroid).
   * Bulb CG z.
   * Fin side force with and without the bulb (the end-plate gain).
   * Effective draft T_eff from a leeway sweep. Fit D_h = D_0 + S_h² / (π q
     T_eff²), the ORC induced-drag form, so the slope of D_h against S_h²
     gives T_eff. That makes the end-plate effect of each bulb one number,
     comparable with ORC's bulb and winglet correction. This is a method
     suggestion; it assumes the profile drag D_0 doesn't change much over
     the sweep.
6. **Validate step by step.** *Dress: bulb2d `validation-dress`.*
   1. Dress's laminar body: coordinates in his Table II, C_D,wet at
      R_L 3.6 × 10⁵ to 1.34 × 10⁶, and the separation line. It tests the
      transition model at IOM Re.
   2. Han & Patel's bubble location.
   3. SUBOFF AFF-1 (L/D 8.6), a turbulent check of the bulb mesh at high Re
      ([data][suboff]).
   4. The Open 50 bulb increments as a sanity check (geometry incomplete).
   5. Gilbert's tow test as a ranking check (250 < 300 < 350 mm), with
      guessed geometry.
7. **Resolve millinewtons.**
   * Bulb candidates differ by a few mN at 0.5-1 m/s: about 7 mN in the
     tow test, about 1-3 mN in the formulas.
   * The convergence tolerance (`conv_tol`, 0.2 % of drag) and the
     discretisation error must both sit below that. Check with a mesh
     study on the bulb drag alone.

**The plan** (2026-10-19).

The design direction to explore is the **flattened bulb that works as an
end plate** (elliptic, flat-bottomed or flat-topped sections at equal lead
mass). In parallel, build the boundary-layer model that bulb drag needs.

* **Upwind, the bulb matters more as an end plate than as a drag body**
  (**estimate**). At the fin study's working load (S_h 6.44 N at 1 m/s,
  T_eff 0.48 m) the keel's induced drag is about 115 mN, more than the
  bulb's own drag if its flow stays attached (37-93 mN).
  * A 5 % gain in T_eff cuts that by about 11 mN: about 0.8 % of the upwind
    leg, by foil2d's conversion (10 mN = 0.74 % at 1 m/s).
  * By the formulas, bulb lengths differ by only 1-3 mN.
* **Flattening helps on every upwind count:** a lower centre of mass (+0.9 %
  of the bulb's righting moment at 1.5:1), a lower tip vortex with a flat
  bottom and sharp edges (Ljungqvist), and ORC's credit for a flat-topped
  bulb.
* **Its costs fall mostly downwind:** about 3 % more wetted area, and lift
  at incidence (pitch). That fits Bantock's oval bulb: "as good… on the
  beat, but not quite as good on the run". The IOM market is moving this
  way (MC-1, Sailboat RC) with no published data.
* **Not worth runs now:**
  * longer bulbs: a flat optimum from L/D 6 to 10, and IOMs are at 9-10
    (B2 checks the model against the tow test instead);
  * winglets: probably not legal;
  * T, L or tandem layouts: the rules allow a fin and a bulb;
  * fillets: about 0.35 mN by Hoerner, and RANS is unreliable at junction
    corners.

| track | study | what | why |
|---|---|---|---|
| A1 | keel3d `bulb-endplate` | λ 0.8 fin with and without the NACA 0011 bulb, leeway 0-4°, upright, medium; fine at 4° | calibration: the Open 50 tank test measured +17-24 % side force from the bulb |
| A2 | keel3d `bulb-section` | six sections of the NACA 0011 bulb (round; 1.25, 1.5, 2:1; flat bottom 1.5; flat top 1.5) × heel 0 and 25° × leeway 0-4°; fine at 4° | the main question, scored by race time on both legs, with the bulb's centre of mass beside it |
| A3 | keel3d `bulb-cant` | round bulb at 0, 2 and 4° nose up, 25° heel; then the A2 winner | Gilbert's 2-3° rule is a calculation for round bulbs; a flattened bulb lifts at incidence |
| B1 | bulb2d `validation-dress` | Dress's body at six of his Re_L, Tu 0.1-0.5 % and fully turbulent; mesh check | without it no drag ranking of bulbs means anything |
| B2 | bulb2d `fineness` | 2380 g NACA bodies of L/D 5-14.3 (230-463 mm, including A's NACA 0011) at 0.5, 1.0 and 1.5 m/s | reproduce Gilbert's tow ranking; does today's bulb separate on its tail? |
| B3 | bulb2d (not written) | largest diameter at 0.35-0.55 L, tail exponent 1.5-3, a trip step at 0.55-0.7 L; best worst case over Tu | only if B2 finds tail separation |

Then rerun the A2 winner's friction drag with the transition model.

**Results so far** (2026-10-19; details in the findings logs):
* **B1** ([validation-dress](../../projects/bulb2d/findings/validation-dress.md)):
  the transition model at Tu 0.05-0.1 % follows Dress's fall of drag with
  Re_L, 10-30 % low. Its laminar bubbles reattach too soon, so a separating
  body's drag reads low. Fully turbulent RANS is no bracket (−45 % at low
  Re, +17 % at 1.34e6).
* **B2** ([fineness](../../projects/bulb2d/findings/fineness.md)): with
  transition, longer is better at fixed lead, but from L/D 9.1 (343 mm) to
  14.3 only 2 %. Fat bulbs (L/D 5-5.7) separate on the tail; from 9.1 the
  flow stays attached and laminar to about 0.93 L. Fully turbulent ranks
  them the other way and doubles the slender bulbs' drag. The direction
  matches Gilbert's tow test; the size is about half at 1 m/s and an eighth
  at 0.5 m/s. **B3 is dropped**: the market-like bulb doesn't separate.
* **A1** ([bulb-endplate](../../projects/keel3d/findings/bulb-endplate.md)):
  the bulb adds 13-15 % keel side force at the same leeway (Open 50:
  17-24 %), T_eff +4 %, the fin's tip load +44 %. keel3d's bulb drag is
  about twice the transitional value.
* **A2** ([bulb-section](../../projects/keel3d/findings/bulb-section.md)):
  the round bulb has the least race-time loss of six sections, upright and
  at 25° heel; 1.25:1 loses 0.2-0.4 %, 2:1 about 1 %. A flatter bulb at the
  same draft brings a longer fin, which is most of its extra drag and most
  of its extra side force (effective draft +1-2 %). With friction corrected
  for transition and the upper righting-moment credit, only the flat bottom
  comes level with round, and only at the upright working load. Bulb lift
  and pitch are negligible. The differences survive the fine mesh.

**Assumptions in the plan:**
* **Righting moment has no conversion to race time yet.** Bracket it from
  0 (light air) to about 0.5 % of speed per 1 % of righting moment
  (overpowered). The upper figure assumes drive ∝ righting moment and
  resistance ∝ V². It is a back-of-envelope figure, not from a source. A VPP
  would replace it ([vpp.md](vpp.md)).
* **The fin is held fixed** (λ 0.8, 90 mm mean chord, NACA 0007: taper-mesh's
  market-like fin). This assumes the bulb ranking doesn't flip with the fin.
* **keel3d's flatter bulbs come with a longer fin** (the draft is fixed), so
  A2 compares designs at the draft limit, not bulbs alone.

## Assumptions, gaps and caveats

* **No published keel-bulb measurement at IOM Reynolds numbers comes with
  complete geometry.** The nearest are Dress's isolated body (no fin), the
  Open 50 model (twice the Re, partial geometry) and Gilbert's tow tests
  (relative speeds only).
* **The top IOM designs publish no bulb data** (V12, VISS, Venti). The
  flat-bottomed IOM bulbs (MC-1, Sailboat RC) are maker claims.
* **No equal-volume comparison of round and elliptic bodies** was found, and
  no quantified effect of fillets on drag in a laminar junction.
* **The drag spread** (37 to over 160 mN at 1 m/s) rests on correlations
  from other bodies. Only CFD validated against Dress-type data can narrow
  it.
* **The transition estimate** (laminar to about 0.7 L, separation about
  0.74 L) is a 2D-correlation screening calculation. Langtry-Menter is
  also unvalidated on bodies of revolution at this Re. No published error
  statistics were found.
* **The righting-moment percentages are the bulb's own contribution.** They
  assume the hull's centre of buoyancy at z = -0.02 m. What 1 % of righting
  moment is worth in race time needs a VPP.
* **Winglets.** Their legality rests on class commentary, not rule text.
  The full-size evidence is mixed at low keel loading.
* **Paywalled, read only as abstracts:** van Oossanen & Joubert 1986 (JFM),
  Werner 2007, Coiro 2005, Orych 2008, Contento 2006, Nicolopoulos 2009,
  Götten 2021, Hess 1976. Larsson & Eliasson's *Principles of Yacht
  Design* and the Delft keel series (Keuning) could not be reached. The
  ORC's bulb and winglet correction to effective draft (§4.2.7, above) is
  the only effective-span formula with a bulb term found.

## Sources

Most useful first: [Howlett][howlett] (appendage design, model-yacht bulbs),
[Hoerner][hoerner] (body drag, junctions), [Dress][dress] (laminar body at
IOM Re), [Parolini & Quarteroni][parolini] (transition on an AC bulb),
[Sfakianaki et al.][sfak] (bulb at model scale), [Axfors & Tunander][axfors]
(T/L bulbs, wind tunnel table), [Gilbert MY 184][my184] (IOM tow test),
[SAILSetc TI23][ti23] (IOM bulb practice), [Myring][myring] and
[Parsons & Goodson][pg] (optimal bodies), [ORC VPP Documentation 2026][orc]
(effective draft with bulbs and winglets).

[orc]: https://orc.org/uploads/files/Rules-Regulations/2026/ORC-VPP-Documentation-2026.pdf
[howlett]: https://6metrearchive.org/wp-content/uploads/2021/02/INHW.7.1.pdf
[hoerner]: https://archive.org/details/FluidDynamicDragHoerner1965
[hoerner-lift]: https://archive.org/details/FluidDynamicLiftHoerner1985
[young]: https://reports.aerade.cranfield.ac.uk/handle/1826.2/1433
[myring]: https://archive.org/details/DTIC_ADA107999
[walker]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3799785/
[pg]: https://archive.org/details/DTIC_AD0744314
[dress]: https://ntrs.nasa.gov/api/citations/19880016048/downloads/19880016048.pdf
[hanpatel]: https://archive.org/details/DTIC_ADA045245
[allen]: https://www.pdas.com/refs/rep1048.pdf
[openvsp]: https://github.com/OpenVSP/OpenVSP/blob/main/src/geom_core/ParasiteDragMgr.cpp
[gotten]: https://arc.aiaa.org/doi/10.2514/1.C036032
[riedeberger]: https://www.iag.uni-stuttgart.de/dateien/pdf/rist_papers/HLRS_report_dolphin_20110421.pdf
[mishra]: https://arxiv.org/abs/2102.13277
[xu]: https://jafmonline.net/article_1812.html
[juncture]: https://ntrs.nasa.gov/api/citations/20180006307/downloads/20180006307.pdf
[harvey]: https://repository.exst.jaxa.jp/dspace/handle/a-is/372993
[kubendran]: https://ntrs.nasa.gov/citations/19860029716
[suboff]: https://apps.dtic.mil/sti/pdfs/ADA359226.pdf
[parolini]: https://www.mate.polimi.it/biblioteca/add/qmox/10-2007.2007.pdf
[sfak]: https://www.jmr.unican.es/jmr/article/view/216
[axfors]: https://publications.lib.chalmers.se/records/fulltext/148387.pdf
[ljungqvist]: https://publications.lib.chalmers.se/records/fulltext/148485.pdf
[mylonas]: https://stax.strath.ac.uk/downloads/37720c97z
[orych]: https://research.chalmers.se/en/publication/131987
[geremia]: https://gpbib.cs.ucl.ac.uk/gecco2007/docs/p2007.pdf
[contento]: https://arts.units.it/handle/11368/2299661
[vo-pet]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11078783/
[acc5]: https://baronerosso.it/forum/attachments/navimodellismo-vela/184641d1298710539-quale-scala-riprodurre-una-acc5-ac_class_rule_version_5.doc.pdf
[tepapa]: https://collections.tepapa.govt.nz/object/715300
[mit95]: https://news.mit.edu/1995/americas-cup-0426
[pedrick]: https://www.sailingworld.com/?p=69363
[practical]: https://www.practical-sailor.com/safety-seamanship/offshore-log-americas-cup-triumphs-and-failures/
[davidson]: https://www.sailingscuttlebutt.com/newsletter-archive/archived_Detailb992.html?key=1576
[drummond]: https://www.sailing.org/2003/01/08/unveiling-day-focus-on-team-new-zealand
[alinghi03]: https://scoop.co.nz/stories/CU0302/S00044/unveiling-day-at-team-alinghi.htm
[sheahan]: https://www.sailingscuttlebutt.com/newsletter-archive/archived_Detail6e1b-2.html?key=2452
[holroyd]: https://www.digitalengineering247.com/article/using-cfd-to-take-back-the-cup
[yw07]: https://www.yachtingworld.com/?p=29424
[cupinfo]: https://cupinfo.com/en/unveiling_designers1.php
[ac75]: https://www.cuplegend.com/wp-content/uploads/2025/09/m26296_2025-09-09-AC75-Class-Rule-V301.pdf
[slooff]: https://www.sailingscuttlebutt.com/?p=101357
[vo65]: https://www.seahorsemagazine.com/article/august-2013/leading-edge
[imoca]: https://www.sailing.org/tools/documents/IMOCACLASSRULE2019V.1.1-%5B24852%5D.pdf
[imoca-bulb]: https://www.boatnews.com/story/35523/the-keel-bulb-on-an-imoca-description-of-this-important-counterweight
[farr533]: https://www.farrdesign.com/yacht/533
[fast2000]: https://oossanen.nl/project/fast-2000/
[iomrules]: https://iomclass.org/wp-content/uploads/2026/04/IOM-Class-Rules-2026-Release-2.pdf
[iomhist]: https://iomclass.org/wp-content/uploads/2026/04/IOM-Class-Rules-History-2026-Revision.pdf
[my184]: https://www.onemetre.net/design/IOM%20bulb%20drag%20(AMYA%20MY%20184)/IOM%20bulb%20drag%20(AMYA%20MY%20184).htm
[my175]: https://www.onemetre.net/Build/Bulb%20cant%20AMYA%20MY%20175/Bulb%20cant%20AMYA%20MY%20175.htm
[my174]: https://onemetre.net/Build/Trim%20Drag%20AMYA%20MY%20174/Trim%20and%20drag%20AMYA%20MY%20174.htm
[bulbcant]: https://onemetre.net/Design/Bulbcant/BulbCant.htm
[bulbsize]: https://www.onemetre.net/Design/Bulbsize/BulbSize.htm
[ovalbulb]: https://www.onemetre.net/Design/OvalBulb/OvalBulb.htm
[fillets]: https://www.onemetre.net/Design/Fillets/Fillets.htm
[finposn]: https://www.onemetre.net/Design/FinPosition/FinPosn.htm
[worlds01]: https://www.onemetre.net/Reports/Wor2001/Omisalj.HTM
[ti23]: https://www.sailsetc2.com/downloads/TI%2023%20ballast%20castings%20%20cf%20coated.pdf
[mi50]: https://www.sailsetc2.com/downloads/MI%2050%20Yacht%20Design%20Notes.pdf
[pattern]: https://www.sailsetc2.com/index.php/ballast-pattern-bulb.html
[sailsetc-ballast]: https://www.sailsetc2.com/index.php/ballast-iom.html
[bantock2]: https://www.mya-uk.org.uk/wp-content/uploads/2025/11/Graham-Bantock-Development-of-the-IOM-class-updated-2025-Part-2.pdf
[seahorse]: https://onemetre.net/OtherTopics/IOMcomparisons/SeahorseArticle.pdf
[hc1]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&cPath=14&products_id=571
[ck1]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&cPath=14&products_id=890
[mc1]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&cPath=14&products_id=909
[mhb]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&cPath=14&products_id=391
[sbrc]: https://www.sailboatrc.com/product/sailboat-rc-bulb-iom-ballast/
[sbrc-fin]: https://www.sailboatrc.com/product/sailboat-rc-fin-keel-iom-yacht/
[mx]: https://www.mxcomponents.com/it/248-bulbo-rivestito-classe-iom.html
[wallin]: http://www.anderswallin.net/2003/05/making-a-bulb/
[corbie]: https://www.rcmodelyachts.com/2019/02/corbie-5-iom-fin-and-bulb-alignment.html
[iomica-long]: https://iomclass.org/phpBB3/viewtopic.php?p=2066
[valenza]: https://dariovalenza.com/project/marblehead-rc-yachts/
