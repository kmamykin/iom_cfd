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
