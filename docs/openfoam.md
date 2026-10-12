# OpenFOAM notes for this repository

ESI OpenFOAM v2512 (openfoam.com), from the official
`opencfd/openfoam-default:2512` image. The tutorials and full sources are in
the image under `/usr/lib/openfoam/openfoam2512/` (`$FOAM_TUTORIALS`,
`$WM_PROJECT_DIR/src`), which is the best reference for exact keywords.

## Anatomy of a case

```
case/
├── 0/                      initial and boundary conditions per field (U, p, k, omega, ...)
├── constant/
│   ├── polyMesh/           the mesh (written by blockMesh, snappyHexMesh or iomcfd)
│   ├── triSurface/         STL geometry for snappyHexMesh
│   ├── transportProperties fluid viscosity (and density, phases for interFoam)
│   ├── turbulenceProperties RAS model and coefficients
│   └── g, hRef, dynamicMeshDict   gravity, reference level, mesh motion (interFoam)
├── system/
│   ├── caseParameters      written by iomcfd: every number that varies between cases
│   ├── controlDict         solver, end time, write controls, function objects (forces...)
│   ├── fvSchemes           discretisation schemes
│   ├── fvSolution          linear solvers, SIMPLE/PIMPLE settings, relaxation
│   ├── blockMeshDict       background mesh
│   ├── snappyHexMeshDict   body-fitted mesh around STL surfaces
│   ├── decomposeParDict    domain decomposition for MPI runs
│   └── include/            generated fragments (force function objects, time control)
├── Allrun                  meshing + solving sequence (NP=8 ./Allrun for 8 ranks)
├── params.json             iomcfd: study inputs and derived values
└── result.json             iomcfd: extracted metrics and status
```

Templates are valid OpenFOAM cases apart from `caseParameters`. Every file
that needs a varying value does `#include "$FOAM_CASE/system/caseParameters"`
and uses `$name`. Only derived, camelCase names (`$Uinf`, `$kInf`, `$xMin`)
are written as entries; the raw study inputs appear as comments. Names like
`geometry` or `mesh` would collide with OpenFOAM keywords.

## Meshing strategies

| Project | Mesher | Notes |
|---|---|---|
| foil2d | `iomcfd.geometry.cmesh` writes `polyMesh` directly | Structured C-grid, hexahedra only, one cell thick. Lines leave the wall exactly normal to it (y+ < 1 with growth ≤ 1.1 near the wall), sharp trailing edge, 50-chord far field. |
| appendage3d, sails | blockMesh box + snappyHexMesh | Background cell = fin chord (or rig height/12); surface, feature-edge, near-body and wake refinement boxes; prism layers. Sails are zero-thickness surfaces turned into baffles (`faceType baffle`), so each sail has two wall patches, `main` and `main_slave`. |
| hull, fullboat | blockMesh with z-grading + snappyHexMesh | Fine, flat cells in a band around the calm waterline (free surface), refinement boxes around the hull and the Kelvin wave pattern, as in the DTCHull tutorial. |

Checks: `checkMesh` runs in every Allrun; read `log.checkMesh` (max
non-orthogonality, skewness, negative volumes) and
`log.snappyHexMesh` (layer coverage per patch) when a case misbehaves.

## Turbulence and transition

* **kOmegaSSTLM** (Langtry-Menter γ-Reθ transition) for foil2d: needed at IOM
  Reynolds numbers (fins ~1e5, sails ~5e4-2e5), where long laminar runs and
  laminar separation bubbles control drag. Needs y+ ≈ 1 or below, no wall
  functions, and the extra fields `ReThetat` and `gammaInt`. The freestream
  `ReThetat` comes from the turbulence intensity via the Langtry-Menter
  correlation (`iomcfd.physics.retheta_t`).
* **Decay control** (`decayControl`, `kInf`, `omegaInf`): without it k decays
  between the far field and the body, so the intensity that drives
  transition would depend on the domain size. On by default with
  kOmegaSSTLM; off for fully turbulent runs (with a very low viscosity ratio
  at high Re it destabilises the solution).
* **kOmegaSST** with wall functions (`nutUSpaldingWallFunction`, valid from
  y+ ~1 to ~300) for the snappyHexMesh projects, where y+ < 1 layers are hard
  to guarantee. This assumes turbulent flow everywhere, which overpredicts
  friction drag at these Reynolds numbers (foil2d validation: about +25 % at
  small angles).

## Numerics that mattered

* Limited gradients for k and ω transport (`linearUpwind limitedGrad`): with
  unlimited gradients ω went negative and diverged on the stretched C-grid.
* SIMPLEC (`consistent yes`) for 2D sections; SIMPLEC plus pressure
  relaxation 0.5 on snappyHexMesh meshes.
* interFoam pseudo-steady runs use local time stepping (`localEuler`) as in
  DTCHull; free sinkage/trim needs true transient runs (`attitude: free`).
* `runTimeControl` `average` conditions stop a run on the first condition
  that passes, even while the forces still oscillate, so stopping is done by
  the iomcfd convergence monitor instead (see workflow.md).

## Function objects used

`forceCoeffs` (Cl, Cd, Cm; e1 = drag, e3 = lift direction), `forces`
(pressure/viscous split, moments), `yPlus`, `wallShearStress`, `surfaces`
(Cp/Cf along the foil; free-surface iso-surface), `solverInfo` (residuals).
Output goes to `postProcessing/<name>/<startTime>/`.

## Debugging a case

```bash
uv run iomcfd shell                     # OpenFOAM environment, repo at /work
cd runs/<study>/<run id>/<case>
tail -50 log.simpleFoam                 # or log.interFoam, log.snappyHexMesh
foamDictionary system/caseParameters    # resolved values
./Allclean && NP=4 ./Allrun             # re-run by hand
foamToVTK -latestTime                   # then open VTK/ in ParaView on the host
```
