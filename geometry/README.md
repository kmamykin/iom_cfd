# geometry/

Your design inputs. Everything here is copied into the solver image and
uploaded to the bucket on `iomcfd gcp submit`, so studies can refer to
files by path relative to this folder.

```
foils/        section coordinates (.dat, Selig or Lednicer), e.g. foil: file:sd8020.dat
hulls/        hull STLs from Fusion 360, e.g. hull: file:hulls/my_hull.stl
appendages/   fin / bulb / rudder STLs
sails/        main, jib (surface bodies) and mast STLs
```

Coordinate frame, units and Fusion 360 export settings:
[docs/geometry.md](../docs/geometry.md).

Section coordinates: the UIUC Airfoil Coordinates Database
(https://m-selig.ae.illinois.edu/ads/coord_database.html) has most published
low-Reynolds-number sections (SD8020, NACA 64A010, HQ, Eppler...). Check the
licence or terms of any file you add if you plan to publish the repository.

Files in `foils/` (2026-10-18, for findings/custom-section.md):
* from the UIUC database, unchanged: `ht13`, `ht14`, `ht34`, `ht35`
  (M. Drela, RC-glider tail sections), `sd8020` (M. Selig), `e168`
  (R. Eppler), `n63010a`, `n64008a`, `naca64a010` (NACA). Redistribution
  terms of the HT and SD files not checked;
* written by `python -m iomcfd.sectiondesign export` (scaled or generated;
  the first line says from what): `ht35-t070`, `ht35-t0725`, `ht14-t070`,
  `sd8020-t070`, `naca64-007`, `naca0007-73`, and the optimiser's
  `cst-opt1`, `cst-opt2` (CST sections, 10 decimals).

Files in `foils/` (2026-10-23, for projects/foil2d/findings/thistle-board.md):
* `naca6-006-r824.csv`: NACA 63-006, 64-006, 65-006 and 66-006 ordinates,
  slopes and nose radii at the 26 stations of NACA Report 824, from the PDAS
  recomputation (https://www.pdas.com/profiles.html);
* `naca63-006`, `naca64-006`, `naca65-006`, `naca66-006` and their `-t0556`
  versions (1 in on an 18 in chord, t/c 5.556 %): CST fits to that table
  with the nose radius held (`tools/naca6_006.py`; within 1e-4 c of every
  station, nose radius within 1 %);
* written by `python -m iomcfd.sectiondesign export` at 1 in on 18 in:
  `naca0006-t0556` (analytic NACA 0006, closed trailing edge),
  `naca0006-45-t0556` (modified 4-digit, the 16-series shape),
  `ht35-t0556`, and the parallel-sided `plank-typical` (an assumed
  home-built wood-lead board: le 0.1, te 0.25, r 0.5, a 0.6) and
  `parallel-l20-t40-r10-a20` (Saporito et al. 2020's best thin family) and
  `parallel-l30-t50-r05-a20` (the XFOIL screen's best of that family),
  `sd8020-t0556` and `naca0006-64-t0556` (thistle-screen candidates);
  the first line of each says from what spec.

