# Geometry: conventions, parametric generators, Fusion 360 export

## Boat frame (all 3D projects)

| Axis | Direction | Origin |
|---|---|---|
| x | aft; water flows towards +x | bow near x = 0 |
| y | to port | centreline y = 0 |
| z | up | calm waterline z = 0 |

* **Heel φ** + = mast to starboard (port tack upwind), rotation about the x axis
  through midship at the waterline.
* **Leeway β_Y** + = bow to port, i.e. the boat slides to starboard and the keel's
  side force points to port (port tack upwind). appendage3d rotates the inflow;
  hull and fullboat rotate the geometry.
* **Trim** + = bow down; **sinkage** + = down.
* Starboard tack is the mirror image of port tack.
* Force, moment and angle symbols (D_h, S_h, M_h, T_a, leeway β_Y, heel φ)
  and how project outputs map onto them: [nomenclature.md](nomenclature.md).

## Parametric geometry (`src/iomcfd/geometry/`)

| Module | Generates |
|---|---|
| `foils.py` | NACA 4-digit sections (closed TE), Selig/Lednicer `.dat` import, TE closing |
| `cmesh.py` | 2D structured C-grid polyMesh around a foil |
| `appendages.py` | Fin (planform, sweep, twist, section), bulb (body of revolution, ~2.4 kg lead with defaults), rudder (with deflection) |
| `hulls.py` | Wigley test hull (L 1 m, B 0.18 m, T 0.05 m = 4.0 kg displacement) |
| `sails.py` | IOM A-rig main and jib (class-rule girths; camber, draft, sheeting, twist) and mast |
| `stl.py` | STL read/write (ASCII, binary), transforms, volume/area, lofting |

## Foil sections

Put coordinate files in `geometry/foils/` and refer to them as
`foil: file:<name>.dat`. Selig format (one loop TE → upper → LE → lower → TE,
as in the [UIUC database](https://m-selig.ae.illinois.edu/ads/coord_database.html)
or airfoiltools.com) and Lednicer format both work. Sections are normalised to
unit chord, and a blunt trailing edge is closed by linear shearing (the C-grid
needs a sharp TE).

## Exporting from Fusion 360

* **Closed bodies** (hull, fin, bulb, rudder, mast): right-click the body →
  *Save as Mesh* → STL (binary is fine), refinement *High*. Fusion exports in
  the document units (usually mm), so keep `stl_scale: 0.001`.
* **Sails** are surfaces, not bodies: export the surface bodies as STL the same
  way. snappyHexMesh treats them as zero-thickness baffles, so they must not
  be thickened.
* **Axes**: Fusion's default is Y-up. Either set *Preferences → General →
  Default modeling orientation → Z up* before modelling, or map axes in the
  study with `stl_rotate: [[x, 90]]` (a list of `[axis, degrees]`, applied in
  order).
* **Position**: place the bow at x ≈ 0 and the design waterline at z = 0 with
  `stl_translate: [dx, dy, dz]` (metres, after scaling). Or put the file
  itself in the boat frame once with `tools/place_hull.py` (rotations, then a
  translation, in the file's units; it prints the particulars at z = 0). The
  alternative hull ([hulls.md](hulls.md)) was turned 180° about z and moved
  so that x = 0 is the bow of the 1000 mm hull with its bumper. For the hull, the
  waterline must match the displacement you want; check `wetted_area_m2` and
  `Lwl` in `iomcfd plan -v`.
* One file per component gives one patch (and one force breakdown) per
  component. Overlapping bodies (fin into hull, fin into bulb) are fine:
  snappyHexMesh meshes the union and extracts the junction lines as feature
  edges.

Suggested layout:

```
geometry/
├── foils/          *.dat section coordinates
├── hulls/          hull STLs
├── appendages/     fin, bulb, rudder STLs
└── sails/          main, jib (surfaces), mast STLs
```
