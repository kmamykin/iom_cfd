# Freestream turbulence intensity (Tu) for sailing appendages

What inlet Tu should foil2d's transition model (kOmegaSSTLM, Langtry-Menter
γ-Re_θ) get for a dinghy centreboard in a lake, a keel at sea, or an RC
yacht's fin on a pond?

The answer moves the results a lot. The model's transition onset
correlation (Langtry-Menter 2009, zero pressure gradient,
`iomcfd.physics.retheta_t`) gives an onset momentum-thickness Reynolds
number Re_θt of 584 at Tu 1 %, 880 at 0.5 %, 1030 at 0.25 %, 1137 at
0.1 %, 1232 at 0.05 % and 1459 at the floor of 0.027 %. Pressure gradient
changes these values; the trend with Tu stays the same.

Literature search of 2026-10-23, for the Thistle study
([findings/thistle-board.md](../../projects/foil2d/findings/thistle-board.md)).
Quotes are as gathered by the search. Saporito et al. was checked against
the paper; the others were not re-read. Anything marked *inference* is
ours, not a source's.

## Sailing-appendage CFD

**Saporito, Persson, Larsson & Mancuso (2020).** "A New Systematic Series
of Foil Sections with Parallel Sides", J. Mar. Sci. Eng. 8(9) 677,
doi:10.3390/jmse8090677. STAR-CCM+, k-ω SST with the one-equation γ
model (not γ-Re_θ), 2D, Re 3e5-1.5e6.
* §2.2: "For the NACA 64-006 section, the ambient turbulence intensity …
  is 0.006, taken from the wind tunnel specification in [16]. For the
  systematic investigation, an estimation of the turbulence level in the
  sea, presented in [17], is adopted. This value is 0.0025."
* They used source terms to hold Tu; without them "the turbulence [died]
  out rapidly behind the inlet".
* §4: "the transition model is not accurate enough to predict the width of
  the drag bucket".
* *Inference:* 0.6 % is far above the Langley low-turbulence tunnel's own
  level (Remmlinger quotes 0.03 %). It reads like a value tuned to match
  the data, as our thistle-tu-calibration does.

**Remmlinger, U. (2013, corrected 2014).** "The Factors that Trigger the
Transition to Turbulent Flow on the Keel of a Sailing Yacht",
self-published, not peer reviewed:
http://www.remmlinger.com/Turblence%20level.pdf. This is Saporito's source
[17].
* **Definition.** Tu counts only the eddies in the Tollmien-Schlichting
  frequency band. Kramer towed a body at 1 m depth in the sea and found "an
  average fluctuating velocity of 0.01 m/s", so Tu "varies … only with 1/U,
  i.e. fast ships 'see' a lower turbulence level than slow ships".
* **Dissipation rates ε at 1 m depth.** Inland lake, 10 kn wind:
  6.8e-7 W/kg. Inshore, 14 kn: 2.3e-6 W/kg. Open sea in a wave trough
  (24 kn, 0.6 m depth): 1e-4 W/kg. Breaking crest: 5e-3 W/kg.
* **His Tu for those rates**, recomputed from his equations 7-10; they
  match his Fig. 1:

  | water | 1 kn | 2 kn | 4 kn | 6 kn | 10 kn | 15 kn |
  |---|---|---|---|---|---|---|
  | lake | 0.74 % | 0.29 % | 0.12 % | 0.068 % | 0.034 % | 0.020 % |
  | inshore | 1.1 % | 0.44 % | 0.18 % | 0.10 % | 0.052 % | 0.030 % |
  | open sea | 3.9 % | 1.6 % | 0.62 % | 0.36 % | 0.18 % | 0.11 % |
  | breaking crest | 14 % | 5.7 % | 2.3 % | 1.3 % | 0.67 % | 0.39 % |

* **Threshold:** "up to 0.1% will not affect the transition point, but
  above this level, the transition point will move forward on the foil and
  the laminar bucket will disappear".
* **Bow wave.** Its 10 % turbulence stays at the wave's toe, so it doesn't
  reach the keel.
* **Alinghi at sea**, via Tanguay et al. 2007, second-hand: the
  low-frequency turbulence at full size didn't affect the laminar flow,
  where the wind tunnel's high-frequency turbulence caused early
  transition.

**Knudsen, Marimon Giovannetti, Legarth & Walther (2024).** "Dynamic Fluid
Structure Interaction of NACRA 17 Foil", JMSE 12 237,
doi:10.3390/jmse12020237. With γ-Re_θ: "the turbulence intensity in the
cavitation tunnel is unknown". No value.

**dos Santos (2018).** MSc thesis on a windsurf fin, IST Lisbon. 0.1 % at
the inlet, "as good practice demands". A weak source.

**Sfakianaki et al. (2013).** J. Maritime Research X(1) 51-58, a yacht
keel in a towing tank. The keel "features a relatively large laminar
region"; trip wires "are unreliable … where lifting surfaces exist". No Tu.

## Marine transition CFD: choosing and holding Tu

**Baltazar, Rijpkema & Falcão de Campos (2021).** JMSE 9 1115,
doi:10.3390/jmse9101115, propellers.
* γ-Re_θt with "Tu = 2.5% and µt/µ = 500 … the best qualitative agreement
  … [with] paint-tests". These values are tuned to model-scale paint
  tests, not measured.
* No iterative convergence at Re 1e6 with Tu 1 % and µt/µ 1.

**Kim, Kim, Li, Wilson, Martin & Carrica (2019).** "Boundary Layer
Transition Models for Naval Applications", J. Ship Research 63(4) 294-307.
* Towed hull: "Low FSTI (0.9%), consistent with tow tank".
* Cavitation tunnel: an estimated 4.2 %.
* Ncrit 3 "corresponds to FSTI ~ 0.8%".

**Eça, Lopes, Toxopeus et al. (2022).** 34th Symposium on Naval
Hydrodynamics (NATO AVT-313):
https://ntrs.nasa.gov/api/citations/20220002151/downloads/SNH_34_Eca_etal_Transition_2D_Flows_revised_v2.pdf
* Ship CFD normally forces transition "close to the stagnation region to
  mimic full-scale conditions".
* With very low Tu at the leading edge, "the RANS solutions exhibit a
  [laminar separation] bubble at the midchord location" that the
  experiments and LES don't show.
* **This is the clearest statement that γ-Re_θ is too laminar at low Tu.**

**Lopes (2021).** PhD thesis, IST Lisbon, §6.3.3. Two-equation models
over-predict the decay of freestream turbulence. Transition models "appear
to be more sensitive to the inlet eddy-viscosity rather than to the inlet
turbulence intensity".

**For foil2d.** `decay_control` (on for kOmegaSSTLM) holds Tu at the foil
at its inlet value, so its `Tu` is the leading-edge value these papers ask
for. Report it as such.

## Natural waters and facilities

* **Gemmrich & Farmer (2004).** J. Phys. Oceanogr. 34(5). Under breaking
  waves near-surface dissipation is "more than four orders larger than the
  background", which is the basis of Remmlinger's sea values.
* **Lake surface layer** (*inference*). Law-of-the-wall scaling, ε =
  u*³/(κz), with a 10 kn wind gives ε ≈ 6.7e-7 W/kg at 1 m, as Remmlinger's
  table does. If u' ≈ u*w ≈ 5-14 mm/s (Kramer's 10 mm/s), then Tu = u'/V
  is about 1 % at 2 kn, 0.3 % at 6 kn and 0.13 % at 15 kn. That is total
  energy, which is what γ-Re_θ reads, not Remmlinger's band-limited share.
* **Towing tanks.** ITTC 7.5-01-01-01 (2017) asks for turbulence
  stimulation on appendages "when laminar flow over the appendage is
  likely", using studs 1.6-3.2 mm in diameter. It gives no tank Tu, and no
  measured towing-tank Tu was found.
* **Cavitation tunnel.** The Delft multiphase flow tunnel measured 0.5-0.6 %
  (Nikolaidou et al. 2026, arXiv 2604.14003).
* **XFOIL.** Mack's correlation, Ncrit = −8.43 − 2.4 ln(Tu), gives Ncrit 9
  ≈ 0.07 %, 5.9 ≈ 0.25 % and 3 ≈ 0.8 %.

## What this means for the studies (*inference*)

* **Thistle centreboard on a lake.** About 0.1-0.3 % at the leading edge
  for 4-15 kn, and 0.3-1 % drifting at 1-2 kn. Tu falls with boat speed,
  roughly as 1/V. Saporito's 0.25 % for the sea is in this range.
* **Open sea.** About 0.2-0.5 % at 4-10 kn in a moderate sea; over 1 %
  under breaking waves and at low speed.
* **RC yacht on a pond.** No source found. Scaling the lake values to 1-3
  kn and a shallow fin gives about 0.3-1 %, possibly 2 %. At Re ≈ 1e5 the
  flow is dominated by bubbles, where Eça et al. found γ-Re_θ least
  reliable.
* **The model.** The physical Tu and the model's input are not the same
  thing. γ-Re_θ at low Tu predicts too much laminar flow. foil2d's own
  check agrees: at Tu 0.05 %, Re 3e6 and C_l 0-0.2, its drag is 23-40 %
  under NACA Report 824 (thistle-validation-r824).
  `thistle-tu-calibration` finds the input that reproduces the
  measurements. A real lake adds turbulence on top of that quiet-tunnel
  calibration, so the calibrated value is a lower bound and Tu 1 % a rough
  upper one.

## Not found

* Tanguay et al. 2007 (Alinghi) and Kramer's original papers; both are
  known only through Remmlinger.
* The Tu values in Liebrand et al. 2019 (MARINE) and Gaggero 2018/2020.
* Any measured towing-tank Tu.
* Tu from yacht-appendage RANS beyond Saporito: Viola, Day, Ferrari,
  Brizzolara, Lombardi, Moth, AC75 or IMOCA foils.
* Any Thistle- or model-yacht-specific source.
