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
