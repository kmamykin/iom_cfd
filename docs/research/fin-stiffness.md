# Why fin stiffness matters on an IOM

Research note, 2026-10-17. It asks why the stiffness of the keel fin
matters, and how much, so that it can be weighed against the small drag
differences between the leading sections (under 1 % of race time;
[findings/fin-profile-selection.md](../../projects/foil2d/findings/fin-profile-selection.md)).

Literature numbers carry their source. Numbers worked out here say how they
were computed and are labelled **estimate**. The class-rule numbers, the
onemetre.net quotes and the SAILSetc product page were read for this note.
Forum posts are opinion and are marked as such. Symbols (heel φ, side force
S_h, righting moment RM_φ) follow [nomenclature.md](../nomenclature.md).

## Short answer

* **At IOM speeds the bulb's weight loads the fin far more than the water
  does.**
  * At a heel φ of 30°, the part of a 2.4 kg bulb's weight acting across
    the fin is about 12 N, at the tip.
  * The fin's own side force S_h is about 6-7 N (this project: 6.7 N at working
    load and 1 m/s).
  * Stiffness is therefore about holding the bulb, not about the water
    bending the fin.
* **Three effects matter.**
  1. **Sag.** At high heel the fin bends to leeward and the bulb swings in,
     which cuts the righting moment.
  2. **Twist.** It happens when the bulb's centre of gravity is ahead of or
     behind the fin's torsion axis.
  3. **Oscillation of fin and bulb in waves.** This is the effect designers
     write about most.
* **Hydroelastic divergence and flutter don't matter at 0.5-2 m/s**
  (**estimate**).
* **No published IOM data links fin stiffness to speed or race time.** The
  evidence is two designers' anecdotes about bulb oscillation, forum
  opinion, and manufacturers' claims without numbers.
* **Designers put thinness ahead of stiffness.** Their advice is to make the
  fin stiff enough by lengthening the chord or by the layup, not by
  thickening it.
* **For this project: stiffness doesn't rule out NACA 0007 at 100 mm**
  (**estimate**).
  * By the c·t³ scaling it is about 50 % stiffer at the root than a 7 %,
    90 mm-chord fin of the same construction, like the one SAILSetc sells.
  * NACA 0008 at 100 mm would be another 30-50 % stiffer still.
  * Whether that extra stiffness is worth anything can't be said from the
    literature. A simple bench test can measure it (last section).

## The loads

The fin carries two loads: the bulb's weight across it when heeled, and the
water's side force on it.

* **The bulb.** It weighs about 2.4 kg (the keel, fin and bulb, must weigh
  2200-2500 g; class rule C.6.4). At heel φ, the component across the fin is
  m g sin φ: about 12 N at 30° and 15 N at 40°. It acts at the tip, about
  0.4 m from the root, so the root bending moment is about 4.7 N·m at 30°
  (**estimate**).
* **The water.** The fin's side force acts to windward and partly cancels
  the sag: about 6.7 N at working load at 1 m/s (this project), centred
  roughly mid-span, so about 1 N·m at the root (**estimate**).
  * Dynamic pressure at 1 m/s is only about 500 Pa.
  * The water's twisting moment on the fin is small next to the bulb's when
    the bulb is offset: about 0.35 N·m for a 30 mm offset against about
    0.1 N·m from the lift (**estimate**).
* **Divergence and flutter.**
  * These are the classic aeroelastic failures (a surface twisting into more
    lift, or a self-excited oscillation; [aeroelasticity][aero]).
  * They need dynamic pressures far above 500 Pa for a fin this stiff.
  * Full-size keel flutter studies are about boats at 20 knots and more
    (e.g. an IMOCA keel study; [HAL record][imoca], abstract only).

  At IOM speeds they don't apply (**estimate**).

## What designers and sailors report

**Bulb oscillation in waves.** This is the strongest qualitative evidence.
* **Lester Gilbert, on a Ten Rater** (a larger radio class, not an IOM),
  [Fin Position][finpos]:
  * the bulb "seemed pretty wobbly on what was an older and less stiff fin";
  * "the boat would slow and spurt unpredictably in waves";
  * "I changed the fin to something much stiffer after a while, and this
    curious behaviour went away";
  * he believes "the bulb's fundamental period of oscillation was excited
    from time to time in waves".

  He recommends "checking that you have enough stiffness to prevent or
  properly damp bulb oscillation when well heeled in waves".
* **Larry Robinson**, quoted on Gilbert's [foil planforms page][fillets]
  (2005; opinion): if the fin is torsionally soft enough to be twisted by
  the bulb, waves of the right frequency can excite fin and bulb, and "when
  that happens, the boat nearly stops".

**Twist and where the bulb sits** (Gilbert, [Fin Position][finpos]):
* "The 'T' keel gives the least twisting stress to the fin when the boat is
  heeled."
* The "L" layout, with the bulb mostly aft, twists the tip to a higher
  angle (wash-in). The "reverse L" twists it to a lower angle (wash-out).
* "A little fin twist is like the wash-out on an aircraft's wing", which
  can reduce tip-vortex drag.
* "You'll need a particularly stiff fin if you want to go with the 'L'
  configuration."

Hydrofoil research agrees on the direction: twist that lowers the angle
under load reduces loads and delays stall; twist that raises it does the
opposite ([Liao et al. 2019][liao], composite hydrofoils, keels named among
the applications).

**Sag and righting moment.** These come from the IOM class forum, 2004, and
are opinion:
* One sailor measured about 30 mm of tip deflection with the keel held
  horizontal by the root and the 2.4 kg bulb on. Fin dimensions and
  material were not given ([forum][forum2143]).
* Another: sag matters most "when the boat is at near maximum heel", when
  the keel "will not be giving maximum righting moment"; in light air "it
  might even be a bit of an advantage" ([forum][forum2143]).

**Thickness against stiffness.**
* Graham Bantock, as recalled by another poster ([boatdesign.net][bd],
  2018, second-hand):
  * "the thinnest is best-around 6%";
  * if the chord had to be longer "to make the fin strong enough in
    bending, that was ok", because "the gain from a thin fin was huge".
* IOM forum posts from 2004 ([forum][forum1196]):
  * Bantock's fast fin mouldings were 6.5 % thick;
  * another poster: "no problems whatsoever making a 6% fin more than stiff
    enough".
* A 1995 German proposal for a minimum fin thickness was meant to "deny
  carbon fins any advantage from a weight and stiffness aspect" and the low
  drag of thin fins. It was rejected (Bantock, [IOM history part 1][bantock1]).

## The class rules

IOM Class Rules 2026 ([rules][rules]; read for this note):

| rule | what it says |
|---|---|
| C.4.1 | Draft 370-420 mm. |
| C.6.3(a) | "The keel shall not move or rotate relative to the hull, except by flexing." |
| C.6.4 | Keel, excluding fasteners to the hull: 2200-2500 g. |
| E.3.1 | Keel materials: no denser than lead. No other material limit. |
| E.4.1 | Largest transverse dimension, except the lowest 60 mm: at most 20 mm. No minimum thickness. |
| D.2.1(a)(2) | In the **hull**, fibres with a higher modulus than glass are prohibited. |

What that means:
* **A carbon fin is legal.** Fin stiffness is limited by construction and
  weight, not by the rules.
* **Weight is the trade-off.** Every gram of fin comes out of the bulb
  within the 2500 g keel limit.
* **The hull side of the fin box can't be carbon** (D.2.1 and D.2.4). The
  joint's own flexibility adds to the fin's. This is our reading, not an
  official interpretation.

## Numbers for the leading sections

All **estimates**: beam theory, same construction, constant chord.

**Bending stiffness.**
* **Solid or uniformly filled sections:** EI ∝ c t³ = c⁴ (t/c)³.
* **Skin-dominated carbon mouldings** (fixed skin thickness): EI and
  torsional stiffness scale more like c t² instead.

| fin | solid section (c t³) | skin-dominated (c t²) |
|---|---|---|
| 0007/90 (like SAILSetc 370-IOM at the root) | 0.66 | 0.73 |
| 0008/90 | 0.98 | 0.95 |
| **0007/100** | **1.00** | **1.00** |
| **0008/100** | **1.49** | **1.31** |

Stiffness relative to 0007/100. SAILSetc's [370-IOM fin][sailsetc] is 7.0 %
thick, with a 90 mm chord at the hull tapering towards the bulb, carbon over
a core, about 115 g. Its section isn't named.

**Righting moment lost to sag.**
* ΔRM_φ ≈ m g δ_h sin φ cos φ, where δ_h is the tip drop in the horizontal
  bench test.
* For the forum's 30 mm, at 40° heel: about 0.35 N·m. That is roughly 6-7 %
  of the boat's righting moment, using Gilbert's 117-158 mm righting arm at
  40° ([Stiffness][gilbertstiff]).
* A fin 1.3-1.5 times stiffer cuts that by 23-33 %.

**Natural frequency of fin and bulb.**
* f ≈ 0.48 / √δ_h, with δ_h in metres, the hull held fixed and about
  0.2 kg added mass.
* That gives about 2.7 Hz for 30 mm of sag and 4.8 Hz for 10 mm.
* Short pond chop met at 1 m/s arrives at a few Hz, so resonance is
  plausible, as the anecdotes suggest.
* The water's damping is large, which argues against strong resonance. Not
  verified.

**Fin weight.**
* At the same construction, a 0008 fin weighs about 14 % more than a 0007
  of the same chord: roughly 15-20 g.
* That comes out of the bulb.

## What this means for the choice

* **Stiffness separates 0007/100 from 0008/100 only if it matters on the
  water.** The literature can't say. The leading designer's view is that
  thin wins and stiffness comes from chord and layup.
* **0007/100 should be stiffer than a typical commercial 7 % fin**, because
  of its longer chord (**estimate**). Stiffness is therefore not a reason to
  rule it out.
* **If the boat sails a lot in waves at high heel**, or the bulb sits well
  aft of the fin ("L" layout), the extra stiffness of 0008/100 is the safer
  side. Its drag cost is 0.7-0.8 % of race time in light and medium air
  (findings).

**A bench test would settle it for a real fin.**
1. Hold the keel horizontal by the root, with the bulb on, and measure the
   tip drop δ_h.
2. With a known torque on the bulb, measure the twist.
3. Put δ_h into the formulas above for the righting-moment loss and the
   natural frequency.

## Caveats

* **Every number in "Numbers for the leading sections" is an estimate**
  from beam theory and the forum's single deflection figure. The real
  layups, core and taper are unknown.
* **The anecdotes are not IOM data.** The best one is about a Ten Rater.
* **No source quantifies the effect of fin flex on IOM speed, pointing or
  race time.**
* **The fin's span is set by the draft rule.** The exposed span is the
  draft (at most 420 mm) minus the hull depth at the fin and the bulb's
  depth. The project's 0.36 m is consistent with that, not measured.

## Sources

* IOM Class Rules 2026: [rules][rules]
* L. Gilbert: [Fin Position][finpos], [foil planforms and fillets][fillets],
  [Stiffness (AMYA MY 173)][gilbertstiff],
  [Foil sections and forces][finforce]
* G. Bantock, [Development of the IOM class, part 1][bantock1] (MYA, 2025)
* SAILSetc: [370-IOM fin][sailsetc]
* IOM class forum, 2004: [fin thickness][forum1196], [swept-back fin][forum2143]
* [boatdesign.net thread][bd] (2018)
* Liao, Garg, Martins and Young (2019), [composite hydrofoils][liao],
  Composite Structures 212
* Aeroelasticity overview: [Wikipedia][aero]; IMOCA keel flutter:
  [HAL record][imoca] (abstract only)

[rules]: https://iomclass.org/wp-content/uploads/2026/04/IOM-Class-Rules-2026-Release-2.pdf
[finpos]: https://onemetre.net/Design/FinPosition/FinPosn.htm
[fillets]: https://www.onemetre.net/Design/Fillets/Fillets.htm
[gilbertstiff]: https://onemetre.net/Design/Stiffness%20(AMYA%20MY%20173)/Stiffness.htm
[finforce]: https://www.onemetre.net/Design/FinForce/FinForce.htm
[bantock1]: https://www.mya-uk.org.uk/wp-content/uploads/2025/11/Graham-Bantock-Development-of-the-IOM-class-updated-2025-Part-1.pdf
[sailsetc]: https://www.sailsetc2.com/index.php/fin-92.html
[forum1196]: https://iomclass.org/phpBB3/viewtopic.php?p=1196
[forum2143]: https://iomclass.org/phpBB3/viewtopic.php?p=2143
[bd]: https://www.boatdesign.net/threads/keel-fin-design-foil-shape-and-surface-area-for-a-given-amount-of-sail-area.60461/
[liao]: https://public.websites.umich.edu/~mdolaboratory/pdf/Liao2019a.pdf
[aero]: https://en.wikipedia.org/wiki/Aeroelasticity
[imoca]: https://hal.archives-ouvertes.fr/hal-02394876
