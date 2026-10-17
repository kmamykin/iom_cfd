# IOM keel fins on the market

Research note, 2026-10-17. It asks what fin sections, chords, thicknesses
and spans IOM fin makers sell, and what the top designs use, to compare
with this project's CFD candidates (NACA 0006-0012 at 80-100 mm constant
chord; [findings/fin-profile-selection.md](../../projects/foil2d/findings/fin-profile-selection.md)).

Product numbers are the makers' claims from their pages (fetched
2026-10-17), not measurements. The SAILSetc, Craig Smith and Rob Nelson
pages, the 2026 class rules and the championship results were read for
this note. Other product pages are as reported by a web survey. Forum posts
are opinion and are marked as such. Numbers worked out here are labelled
**estimate**.

## Short answer

* **Every IOM fin with stated dimensions is tapered.**
  * About 80-100 mm chord where it leaves the hull, down to 63-75 mm at the
    bulb.
  * So the mean chord is about 72-85 mm (**estimate**: the average of root
    and tip).
  * About 350-360 mm below the hull, where stated.
  * Carbon fibre throughout.
* **Thickness is 6-7 % of the chord, 5-6 mm** where stated.
  * SAILSetc 7 %.
  * Craig Smith 6 % (5.2 mm average).
  * An unbranded fin, XF1P, 6 %.
  * MX Components 5-6 mm.
* **No current maker names a NACA section.**
  * Graham Bantock's SAILSetc fins have used custom low-Reynolds-number
    sections by David Hollom since 1992, with unpublished coordinates.
  * Older forum posts mention NACA 0006 and NACA 65-07 fins.
* **The winning designs of recent years publish no fin dimensions.** They
  are VISS, Venti, V12 and K2, with BritPOP in the top 10s. Their fins come
  with the design.
* **Against this project's candidates:**
  * NACA 0007 matches the thickest stated commercial fin.
  * NACA 0006 matches several.
  * NACA 0008 at 100 mm (8 mm thick) is thicker than any stated IOM fin.
  * A constant 100 mm chord gives more area than any listed fin. The 2D
    simulations can't say what the taper does (Implications).

## Fins for sale

| maker | product | thickness | chord, hull → bulb | below hull / overall | material, weight, price | source |
|---|---|---|---|---|---|---|
| SAILSetc (G. Bantock, UK) | Fin 7.0 % t/c, IOM (370-IOM) | 7.0 % | 90 mm at the hull → 75 mm (section not named) | not stated / 450 mm | carbon over a core, about 115 g before trimming, £165 | [page][sailsetc] |
| Craig Smith (AU), via RadioSailingShop | CF1 keel fin | 6 %, 5.2 mm average | 90 → 75 mm | 350 / 450 mm | ultra-high-modulus carbon; page gives both 88 g and 108 g; A$295, sold out | [page][cs] |
| RadioSailingShop (maker not stated) | XF1P IOM fin | 6 % | 80 → 65 mm | not stated / 480 mm | UHM carbon, 80 g, sold out | [page][xf1p] |
| Rob Nelson Boats (NZ) | GP IOM fin | not stated | 100 → 70 mm | 360 / 450 mm | carbon, about 70 g (62 g fitted to a Venti), NZ$875 | [page][rn] |
| RCSails | IOM carbon keel 1 | not stated | 90 to 65 mm | not stated / 430 mm | about 120 g | [page][rcsails] |
| MX Components (IT) | Deriva Classe IOM | 5 mm max | "95x70x470" (probably 95 → 70 mm, 470 mm long; not labelled) | not stated | carbon, autoclave, €190 | [page][mx] |
| MX Components | MX EVO 3 and variants (IOM) | 5-6 mm, tapered | not stated | not stated | carbon and foam core, 115 g, €125-170 | [page][mxevo] |
| Sailboat RC (HR) | fins for VISS and K2 (the K2's "signed by Craig Smith") | not stated | not stated | not stated | UHM carbon | [VISS][sbviss], [K2][sbk2] |
| RC Sailing Lab (ES) | Alioth carbon fin | "CFD optimized"; not stated | not stated | not stated | carbon, €185 | [page][alioth] |
| Vickers RC Sailing (NZ) | V12 foils (only with the hull) | not stated | not stated | not stated | carbon | [site][vickers] |

**Historic fins.** IOM class forum posts:
* 2004: a NACA 65-07 fin, 7 % thick at the top, 6 % in the middle, 5 % at
  the bottom, 147 g, "deflection 19 m/m" with no load given ([forum][f272]).
* 2008: a NACA 0006 fin ([forum][f7244]).
* 2004 (Anders Wallin):
  * "small" parallel fins were about 85 mm chord;
  * a Bantock Italiko fin was about 135 mm at the root, tapering to about
    80 mm;
  * "modern fins are around 6-7% thick" ([forum][f2220]).

## What wins

IOM World Championships ([IOMICA Hall of Fame][hof]):

| event | 1st | 2nd | 3rd |
|---|---|---|---|
| 2026, Datchet, UK | Alexis Carré (V12) | Zvonko Jelačić (VISS) | Rob Walsh (Venti) |
| 2024, Gladstone, AUS | Zvonko Jelačić (VISS) | Ian Vickers (V12) | Alexis Carré (V12) |
| 2022 | Olivier Cohen (Venti) | Alexis Carré (V11) | Zvonko Jelačić (K2) |
| 2019 | Zvonko Jelačić (K2) | Ante Kovačević (K2) | Ian Vickers (V11) |

* None of these designs publishes its fin's section or dimensions.
* The VISS and K2 fins come from Sailboat RC; the K2's is by Craig Smith.
  The V12 is sold with its own carbon foils.
* Rob Nelson quotes a Venti-fitted weight for his GP fin (100 → 70 mm), so
  at least some Venti sailors use it (**estimate**).
* Brad Gibson used the same fins across his Glam Rock, SKA and BritPOP
  designs to isolate hull changes ([2013 interview][gibson]). Dimensions
  were not given.

## Designers' guidance

* **Lester Gilbert** ([Foil sections and forces][finforce]):
  * "Our fin probably has an average chord of 80 mm", giving Re about 88,000
    at 1.1 m/s.
  * Typical leeway is about 3° in No. 1 rig.
  * Thinner sections stall at a lower angle, roughly at an angle of attack
    similar to their thickness in %.
* **Graham Bantock**, in comments on the same page: cutting the chord lowers
  the Reynolds number and raises the drag coefficient.
* **Thickness is the most debated choice.**
  * Bantock, second-hand: "the thinnest is best-around 6%"; lengthen the
    chord if the fin needs strength ([boatdesign.net][bd], 2018).
  * Gilbert: "a competitive IOM must have a thin fin which inevitably means
    a fin made of carbon fibre" ([IOM history][history]).
  * Proposals for a minimum thickness ("10 mm or 10% of chord", and a
    German proposal in 1995) were defeated.
* **Hollom:** "since 1992 Graham has exclusively used four of our sections,
  designed specifically for Re numbers typical of model yachts"
  (sidebar in D. Davis, "Instructive", [Seahorse][seahorse], 2008).

## The class rules

IOM Class Rules 2026 ([rules][rules]):
* draft 370-420 mm (C.4.1);
* keel 2200-2500 g (C.6.4);
* the fin no thicker than 20 mm except in the lowest 60 mm (E.4.1);
* keel materials no denser than lead (E.3.1).

Chord, planform, section and minimum thickness are free. Carbon is banned
in the hull (D.2.1) but not in the fin. More detail:
[fin-stiffness.md](fin-stiffness.md).

## Implications for this project

* **Thickness: the CFD agrees with the market.** The best sections in the
  simulations are 7 % thick (NACA 0007 at 90 and 100 mm). That is the
  thickness the market sells, and the leading designer's 6-7 %.
  * The 6 % section lost at working load in the simulations: its laminar
    boundary layer separates at the leading edge (selection run 2).
    Commercial 6 % fins are not NACA 0006, so this doesn't transfer
    directly.
  * NACA 0008 at 100 mm is thicker than anything sold.
* **Chord: the CFD favours more chord than the market sells.**
  * The simulations favour 90-100 mm, because a longer chord needs less
    leeway for the same side force.
  * Commercial fins taper from 80-100 mm at the hull to 63-75 mm at the
    bulb: a mean chord of about 72-85 mm.
* **The 2D model can't weigh taper.** Taper moves the lift towards the
  root, cuts the bending moment and weight at the tip, and changes the
  induced drag. Those are 3D effects.
* **Two checks would close the gap:**
  * a 3D check (`appendage3d`) of a tapered 7 % fin, for example 100 → 70
    mm, against a constant 100 mm chord;
  * a 2D run at the market's mean chord, about 80 mm at 6-7 %. Selection
    runs 1-2 had 80 mm, so it is partly covered: 0007/80 and 0006/80 were
    in run 2 at Tu 1 %.

## Caveats

* Product numbers are makers' claims.
  * Which end of the RCSails range is the root, and what MX's "95x70x470"
    means, are not stated.
  * Craig Smith's page gives two weights.
* Several maker sites render little text to a fetcher, so some details may
  be missing.
* Forum figures are mostly from 2004-2008, before the current generation of
  designs.
* Whether tapered fins keep the same thickness ratio along the span is not
  stated anywhere.

## Sources

* Makers:
  * SAILSetc: [370-IOM fin][sailsetc]
  * RadioSailingShop: [CF1][cs], [XF1P][xf1p]
  * [Rob Nelson Boats][rn]
  * [RCSails][rcsails]
  * MX Components: [IOM][mx], [EVO 3][mxevo]
  * Sailboat RC: [VISS fin][sbviss], [K2 fin][sbk2]
  * [RC Sailing Lab][alioth]
  * [Vickers RC Sailing][vickers]
* Results: [IOMICA Hall of Fame][hof]
* Designers:
  * L. Gilbert: [Foil sections and forces][finforce],
    [IOM history (AMYA MY 177)][history]
  * [Seahorse article (2008)][seahorse]
  * [Brad Gibson interview (2013)][gibson]
* Forums: IOMICA forum [t=272][f272], [p=7244][f7244], [p=2220][f2220];
  [boatdesign.net][bd]
* Rules: [IOM Class Rules 2026][rules]

[sailsetc]: https://www.sailsetc2.com/index.php/fin-92.html
[cs]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&products_id=191
[xf1p]: https://www.radiosailingshop.com.au/index.php?main_page=product_info&products_id=954
[rn]: https://www.robnelsonboats.nz/shop/product/916185/gp-iom-fin/
[rcsails]: https://rcsails.com/iomappend.html
[mx]: https://www.mxcomponents.com/it/26-deriva-classe-iom.html
[mxevo]: https://www.mxcomponents.com/it/259-deriva-mx-evo-3.html
[sbviss]: https://www.sailboatrc.com/product/sailboat-rc-fin-keel-iom-yacht/
[sbk2]: https://www.sailboatrc.com/product/fin-keel-kantun-2/
[alioth]: https://rcsailinglab.com/product/alioth-carbon-fin/
[vickers]: https://www.vickersrcsailing.com/
[hof]: https://iomclass.org/?p=20767
[gibson]: http://modelyacht.blogspot.com/2013/03/iom-in-review-britpop.html
[finforce]: https://www.onemetre.net/Design/FinForce/FinForce.htm
[history]: https://www.onemetre.net/OtherTopics/IOM%20history%20(AMYA%20MY%20177)/IOM%20History%20AMYA%20MY%20177.htm
[seahorse]: https://onemetre.net/OtherTopics/IOMcomparisons/SeahorseArticle.pdf
[bd]: https://www.boatdesign.net/threads/keel-fin-design-foil-shape-and-surface-area-for-a-given-amount-of-sail-area.60461/
[f272]: https://www.iomclass.org/phpBB3/viewtopic.php?t=272
[f7244]: https://www.iomclass.org/phpBB3/viewtopic.php?p=7244
[f2220]: https://iomclass.org/phpBB3/viewtopic.php?p=2220
[rules]: https://iomclass.org/wp-content/uploads/2026/04/IOM-Class-Rules-2026-Release-2.pdf
