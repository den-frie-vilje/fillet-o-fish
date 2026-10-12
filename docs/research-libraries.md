# Foundations for a programmatic parts engine in Python

Survey of 2026-10-12: kernels and libraries usable from Python on macOS (Apple Silicon), headless,
for thin-walled printed parts like a duct: sweeps along bends, constant wall thickness, Boolean
unions, and reliable fillets where a swept duct meets a box. Versions and dates were read on that
day from PyPI, GitHub and the linked pages.

## The finding that decided the design

The failing case (a fillet chain running out at a tangent, a fillet consuming a face) is the
class of defect Open CASCADE fixed in August 2026, and the fix is not in any Python wheel:

- Issue 172 "Fillet can not round a face" (closed 2026-08-09) restates a ten-year-old bug:
  fillets that touch at a tangent point threw "BRep_API: command not done".
  https://github.com/Open-Cascade-SAS/OCCT/issues/172
- Issue 1177 "Fillet/Chamfer cannot meet opposite edges": a 9.999 fillet in a 10 box works, 10
  does not. https://github.com/Open-Cascade-SAS/OCCT/issues/1177
- Pull request 1293 "Enhance fillet and chamfer handling. Part 1" and 1449 "Part 2", merged
  2026-08-09 into branch IR, milestone Release 8.1 (due 2027-01-15): accept tangential contacts,
  reject transversal intersections, exclude fully consumed faces.
  https://github.com/Open-Cascade-SAS/OCCT/pull/1293, https://github.com/Open-Cascade-SAS/OCCT/pull/1449
- Both merges are ahead of tag V8_0_1 (2026-07-30), so cadquery-ocp 8.0.1.1.0 lacks them.
- OCCT 8.0.1's release note on threads: "Independent BRepFilletAPI_MakeFillet operations no
  longer race through TopOpeBRepBuild state and silently produce invalid solids."
  https://github.com/Open-Cascade-SAS/OCCT/releases
- build123d issue 566 "Sketch vertices randomly not filleted": reproduced only on Apple Silicon,
  still present 2025-12-10. https://github.com/gumyr/build123d/issues/566

## B-rep kernels from Python

| Library | Version, date | Licence | Fillet robustness | Notes |
|---|---|---|---|---|
| cadquery-ocp (OCCT bindings) | 8.0.1.1.0, 2026-10-05 | Apache-2.0 (OCCT LGPL 2.1 + exception) | The kernel above | Wheels for macOS arm64, Python 3.11 to 3.14. https://pypi.org/project/cadquery-ocp/ |
| pythonocc-core | 8.0.1.1, 2026-10-05 | LGPL-3.0 | Same kernel | conda only. https://github.com/tpaviot/pythonocc-core/releases |
| CadQuery | 2.8.0, 2026-06-20 | Apache-2.0 | A one-line pass-through to `BRepFilletAPI_MakeFillet`, no `IsDone` check | Adds selectors, not reliability. https://github.com/CadQuery/cadquery/blob/master/cadquery/occ_impl/shapes.py |
| build123d | 0.13.0, 2026-09-21 | Apache-2.0 | Same pass-through; "OpenCascade offers no way to disable" tangent-chain propagation | https://build123d.readthedocs.io/en/latest/operations.html |
| Parasolid, ACIS | no Python bindings | NDA, undisclosed price | | https://www.siemens.com/en-us/products/plm-components/parasolid/ |
| Fusion 360 API | desktop only | subscription | | "The only way to access the API currently is through the full desktop version" (Autodesk, 2023). Cloud Automation API: 3 Flex tokens per processing hour, about $9. https://aps.autodesk.com/blog/design-automation-api-fusion-now-generally-available |
| Onshape FeatureScript `opFillet` | cloud Parasolid | Free: public documents, 2,500 API calls a year; Standard $1,500 a year | `allowEdgeOverflow`, variable, conic, curvature-continuous: the richest fillet API found | https://cad.onshape.com/FsDoc/library.html#opFillet, https://onshape-public.github.io/docs/auth/limits/ |
| Rhino 8 | $995 once, Mac native | | "Both cases are known shortcomings in Rhino's filleting system" (McNeel, 2024) | rhino3dm has no Booleans or fillets; scripting needs the GUI. https://discourse.mcneel.com/t/why-are-fillets-so-bad/184006 |
| Zoo (KittyCAD) | kittycad 1.7.0, 2026-10-06 | MIT SDK, metered API | No robustness evidence found | Young kernel. https://zoo.dev/docs/kcl-std/functions/std-solid-fillet |

SolidWorks and Inventor are Windows only.

## Implicit and mesh-based alternatives

On a redistanced level set, a rolling-ball fillet on a concave edge is a morphological closing
(dilate by r, erode by r), exact to about one voxel. On a closed-form SDF expression, `min` of two
fields is not a true distance inside the union, so libfive and fogleman's sdf give smooth-min
blends rather than constant-radius fillets.

| Tool | Version, date | Licence | Fillet | Fit |
|---|---|---|---|---|
| libfive | last commit 2025-11-12, no releases | MPL-2.0 | smooth-min blends only | Source build on Apple Silicon. https://github.com/libfive/libfive |
| fogleman/sdf, sdfcad | 2024 | MIT | k-blends, not constant radius | Marching cubes; not watertight by construction. https://github.com/fogleman/sdf |
| OpenVDB | 13.1.0, 2026-09-16 | Apache-2.0 | closing on a level set | The Python module exposes "almost none of the many tools"; `vdb_tool` CLI has dilate, erode, Booleans, ls2mesh. conda-forge builds for osx-arm64. https://www.openvdb.org/documentation/doxygen/python.html |
| Manifold (manifold3d) | 3.5.4, 2026-09-25 | Apache-2.0 | none (PR 1229 closed unmerged) | Guaranteed manifold Booleans; Blender 4.5's Boolean solver. `level_set` from Python is serial. https://github.com/elalish/manifold |
| OpenSCAD, PythonSCAD, SolidPython2 | 2026 nightlies; 1.1.2 | GPL-2 with exception | minkowski rounds convex edges only; PythonSCAD claims `fillet()` with no reference found | https://pythonscad.org/ |
| ImplicitCAD | 0.4.1.0, 2023 | AGPL-3.0 | rounded unions | Haskell, no Python. |
| Blender as a module (bpy) | 5.2.2, 2026-09-15, Python 3.13 only, 245 MB wheel | GPL-3.0 | Blender 5.0 geometry nodes: Mesh to SDF Grid, SDF Grid Offset, "SDF Grid Fillet: Rounds off concave internal corners", SDF Grid Boolean, Grid to Mesh | The one pip-installable, Apple-Silicon package that does mesh-to-SDF, closing, offset, Boolean and meshing in one dependency, headless. https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/ |
| nTopology, Rhino.Compute | Windows or server | undisclosed; $0.10 per core-hour | | Out for a Mac. |

Production use: PrusaSlicer's and Bambu Studio's SLA hollowing is OpenVDB level-set offsetting
(`src/libslic3r/OpenVDBUtils.cpp` in both), shipped to millions of users; Blender 4.5 LTS ships
Manifold; KiCad's 3D package generator is CadQuery scripts.

## The hybrid, and its arithmetic

No single maintained Python library does "B-rep in, narrow-band closing, dual contouring out" at
sub-0.1 mm on 250 mm parts. The pieces exist: OCP for sweeps, shells and Booleans; Blender's grids
(or OpenVDB through `vdb_tool`) for the closing; Manifold to re-join the blended region with the
exact tessellation.

A narrow band stores about surface area / h² × band width. A 250 mm duct-on-box with 1e5 mm² of
surface at h = 0.01 mm is about 6e9 active voxels (24 GB): infeasible. At 0.05 mm about 2.4e8
(1 GB, tens of seconds); at 0.1 mm about 6e7 (seconds). Cropping to a box round the junction at
0.05 mm gives about 5e7 voxels. Measured in fof on 2026-10-12 with Blender's nodes on a 60 × 55 mm
riser-on-box junction: 0.5 mm voxels 12 s, 0.2 mm voxels 349 s, and Grid to Mesh emits a triangle
per voxel unless its Adaptivity is raised (1.9 million faces at 0.2 mm, 36 thousand with
adaptivity 0.5). So the level-set blend is a fallback, applied to a tight region, not the default.

## Recommendation

| Stack | Fillet at a run-out | Watertight | Headless on Apple Silicon | Licence | Verdict |
|---|---|---|---|---|---|
| OCP B-rep + OCCT's IR branch for fillets (fof builds it; `fof/kernel.py` drives it through DRAW) + Manifold | The 2026 fixes, verified on the vent's junction: 10 of 10 builds, identical solids | Yes, with `BRepCheck_Analyzer` | Yes | LGPL + exception | Default |
| OCP B-rep + Blender bpy SDF grids + Manifold | By construction | Yes | Yes, Python 3.13 | Apache + GPL | Fallback for chains that fail their preconditions |
| Onshape REST + FeatureScript | Strong API | STL export | Cloud | $1,500 a year | Only if both above fail |
| libfive, sdf, PythonSCAD, ImplicitCAD | smooth-min, not constant radius | varies | | | Not for this requirement |

## Not reached

Parasolid and nTop pricing; Zoo's pricing page (JavaScript only); the Blender manual page for SDF
Grid Fillet (the release notes are quoted instead); any primary source on run-to-run
nondeterminism of OCCT fillets in a single thread; OCCT's reference manual page for
`BRepFilletAPI_MakeFillet` (404; the header was used).
