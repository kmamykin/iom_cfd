# Hulls the VPP floats

The hulls in the boat files, where their lines come from, how they are
placed in the boat frame ([geometry.md](geometry.md): x aft from the bow,
z up from the design waterline) and their particulars
([nomenclature.md](nomenclature.md#hull-form-and-hydrostatics-ittc)).
`uv run iomcfd vpp hydro <boat>` prints these numbers, and every `vpp run`
writes them to `particulars.csv` and its report.

## The hulls

| boat file | hull | lines |
|---|---|---|
| `canoe-placeholder` | keel3d's parametric canoe body (`CanoeSpec` defaults, geometry/hulls.py) as a mesh | analytic, in the repo |
| `iom-alternative` | the alternative hull | private STL, `boats/private/hulls/iom-alternative.stl` (git-ignored) |

### The alternative hull

* **Source.** `IOM_Alternative_Hull.stl`, a Fusion binary STL in mm, 25 730
  triangles, closed, symmetric about y = 0. sha256 3900e02b…b49a040; the
  placed file is 02f6fb7f…1749985.
* **Source frame.** x forward from a flat transom, z up, origin where the
  transom meets the waterline. The transom's bottom edge lies on z = 0.
* **Placement.** `tools/place_hull.py --rotate z 180 --translate 1000 0 0`,
  so x' = 1000 mm − x and y' = −y. The transom/waterline point is at
  x = 1000 mm. The stem tip is at x = 2.25 mm: the STL's bow bumper is a few
  mm short, so x = 0 is the bow of the full 1000 mm hull. The design
  waterline meets the stem at x = 23.75 mm.
* **Shape.** The deck is raised forward: about 85 mm at the sheer and
  114 mm at the stem, against 51–59 mm aft. The windage model sees that deck.
* **Assumed, not stated by the designer:** the source's z = 0 is the
  design waterline. With canoe-placeholder's fin, bulb and rudder, the boat
  displaces 4.25 kg there. At the class minimum of 4.0 kg it floats about
  2 mm higher.

## Particulars

### At the design waterline, even keel (hull alone; Δ with the appendages)

| | canoe body | alternative |
|---|---|---|
| ∇ (hull) | 3.619 L | 3.864 L |
| Δ, with canoe-placeholder's fin, bulb and rudder | 4.010 kg | 4.253 kg |
| LWL (waterline x) | 984.1 mm (3–987) | 976.2 mm (24–1000) |
| BWL, T_c | 165.0, 53.0 mm | 157.7, 59.1 mm |
| LCB, LCF | 504.3, 507.4 mm | 528.3, 537.3 mm |
| S, A_WP | 0.1431, 0.1089 m² | 0.1495, 0.1149 m² |
| A_X (at x) | 68.3 cm² (517 mm) | 70.2 cm² (530 mm) |
| C_B, C_P, C_X, C_WP | 0.421, 0.538, 0.781, 0.671 | 0.425, 0.564, 0.753, 0.746 |
| BM_T, BM_L | 46.8, 1477 mm | 44.9, 1653 mm |
| immersion | 108.8 g/mm | 114.8 g/mm |

### Floating at canoe-placeholder's mass budget

The mass budget is 4.000 kg with its CG at x = 498 mm, z = −219 mm. Both
hulls carry the same items here (measured from each hull's bow), so this
compares the hulls. `iom-alternative.yaml` now has its own rudder and mass
items (below).

| | canoe body | alternative | alternative, CG moved to x = 531 mm |
|---|---|---|---|
| sinkage, trim | 0.00 mm, 0.46° bow down | −1.79 mm, 1.16° bow down | −2.23 mm, 0.00° |
| LWL (waterline x) | 969.0 mm (3–972) | 945.6 mm (6–952) | 957.1 mm (33–990) |
| S | 0.1430 m² | 0.1430 m² | 0.1440 m² |
| C_P, C_WP | 0.547, 0.679 | 0.571, 0.744 | 0.566, 0.751 |
| GM_T, GM_L | 214.7, 1489 mm | 210.9, 1586 mm | 211.4, 1683 mm |
| MCT | 1.020 N·m/deg | 1.086 N·m/deg | 1.152 N·m/deg |

* **The alternative's LCB is 24 mm aft of the canoe's.** With the canoe's
  mass positions it trims 1.16° bow down, and the transom lifts clear: the
  waterline ends 48 mm forward of it.
* **Moving the CG 33 mm aft** (to x = 531 mm) floats it level, 2.2 mm above
  the DWL. That is the total CB with the appendages: the hull's own LCB is
  528 mm, and the rudder's volume pulls the total aft.
* **What sets the trim is the fin, mast and equipment positions,** not
  the hull.
* **With `iom-alternative.yaml`'s own layout** (2026-10-29, after the
  designer's plan below):
  * the HT35 100 → 80 mm fin (the keel3d study's; the table moves with it)
    with its quarter chord at x = 0.544 m, the plan's fin's centre of force
    (below), so its root leading edge at 0.519 m;
  * the rig weighed at 100 g; the mast's centre at x = 0.506 m and the main's
    tack (boom at the mast) at (0.512, 0, 0.120) m, the mast stepped in a
    well behind the crowned foredeck (the sheer 0.061 m there); the jib's tack
    at (0.111, 0, 0.117) m (below);
  * the user's rudder, 75 → 60 mm over 200 mm, its trailing edge vertical
    at x = 0.995 m and its leading edge swept 4.3° from 0.92 m at the root
    (its mean quarter chord at 0.944 m); servo and winch further aft;
  * the 574 g corrector at x = 0.509 m, placed so it floats level.

  The CG is at x = 535 mm, z = −237 mm. It floats level, 2.2 mm above the
  DWL, the waterline from 33 to 991 mm (LWL 958 mm); GM_T 230 mm, MCT
  1.167 N·m/deg. RM_φ is 1.565, 3.086, 4.514 and 6.410 N·m at 10, 20, 30
  and 45°. At V_TW 3 m/s and β_TW 45° the rig's centre of effort is at
  x = 0.523 m, 21 mm ahead of the fin's quarter chord, and the rudder holds
  3.6° of weather helm (V_b 1.169 m/s, 32.2° of heel).

### Against the designer's plan

The designer's profile plan (2026-10-29; not in the repo) measures from a
datum at the transom on the waterline, forward: boat x = 1 m − plan x.
Read from a scan at 2.70 px/mm (station lines 100 mm apart, ±2 px):

* **Keel line.** The plan's and the STL's agree within ±2 mm at 22 stations
  from 25 to 960 mm (the largest, 2.2 mm, at 800 mm).
* **Check line.** "To underside of hull at stem 644 mm" runs from the stem at
  the waterline (plan x 986 mm) at 37.1° to (x 0.527, z −0.388) m: the fin's
  leading edge at the bulb. The model's is at (0.527, −0.382), 640 mm from
  the same point; its bulb is 6 mm deeper at the top.
* **Mast.** The mast's centre at 494 mm is the boat file's 0.506 m.
* **Deck.** The STL's crowned foredeck ends at x = 0.507–0.510 m; the plan's
  bulkhead, where it ends, is at 514 mm (x = 0.486 m). The plan's mast well
  (its floor 30 mm below the sheer, about 30 mm above the waterline, from
  about x = 0.486 to 0.59 m) isn't in the STL. The sheer at the mast is
  61 mm on both.
* **Fin.** The plan's fin: leading edge at 478 mm at the root and 474 mm at
  the tip; trailing edge at 391 mm at the root, raked forward to 402 mm.
  Its chord is 86 mm at the root and 72 mm at the tip, 79 mm mean, and its
  mean aerodynamic chord (79.5 mm, 48.5 % down the span) has its quarter
  point at plan 456 mm, x = 0.544 m. An untapered 80 mm fin on the same
  leading edge has its centre at the same place. The boat file keeps the
  HT35 100 → 80 mm fin (the keel3d table) and puts its quarter-chord line,
  vertical, there.
* **Rudder.** The plan's rudder: post at 60 mm (x = 0.940 m); leading edge at
  the root at 83 mm (x = 0.917 m), raked aft; trailing edge vertical at
  10 mm (x = 0.990 m); chord about 73 mm at the root and 45 mm near the tip,
  which is rounded, at 192 mm below the waterline (a span of about 180 mm).
  The boat file has the user's own rudder instead, 75 → 60 mm over 200 mm,
  on the same post (its root quarter chord at 0.939 m).
* **Jib tack.** The BritPOP jib boom layout (Brad Gibson, 2012) puts the A
  jib's luff wire 388 mm and the pivot 310 mm from the boom's aft end (B 351
  and 279, C 304 and 249): the tack 78 mm ahead of the pivot. Taking the
  plan's deck marks at 811, 782 and 752 mm as the A, B and C pivots
  (assumed: the larger jib furthest forward), the A pivot is at x = 0.189 m
  and the tack at 0.111 m, about 15 mm above the foredeck (101.6 mm there;
  the user's estimate): z = 0.117 m.
* **Not in the model.** The jib sheet eyes at 627 mm, the deck marks at 551
  and 573 mm, the post at 283 mm.

### Righting moment at the mass budget (M_ext = 0, Z_ext = 0)

| φ | canoe RM_φ, GZ | alternative RM_φ, GZ |
|---|---|---|
| 10° | 1.461 N·m, 37.3 mm | 1.438 N·m, 36.7 mm |
| 20° | 2.874 N·m, 73.3 mm | 2.836 N·m, 72.3 mm |
| 30° | 4.196 N·m, 107.0 mm | 4.152 N·m, 105.9 mm |
| 45° | 5.935 N·m, 151.3 mm | 5.907 N·m, 150.6 mm |

The bulb dominates: GM_T is about 211 mm of which BM_T is 45 mm. The
alternative's narrower waterline (157.7 against 165.0 mm) costs 1.6 % of
RM_φ at 10° and 0.5 % at 45°.

## Next

* The designer's fin, mast, rudder and equipment positions for
  `iom-alternative`, in place of canoe-placeholder's.
* A keel table on this hull: the keel3d table's double body is the canoe
  body's (a build warning says so), so its side force and yaw include that
  hull.
* `vpp compare canoe-placeholder iom-alternative` for race time, once the
  positions are in.
