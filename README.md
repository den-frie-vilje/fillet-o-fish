# Fillet-O-Fish

A staged, parametric engine for 3D-printable parts, in Python. It builds a part the way a CAD
timeline does, from profile to finished body, and records every step so a viewer can show them.
It rounds the joints between bodies in a way that does not fail: through a fixed Open CASCADE
kernel where the geometry allows it, and on a distance grid where it does not. Every part is
measured against an independent ideal before it is called done.

## Install

```
git clone https://github.com/den-frie-vilje/fillet-o-fish.git
cd fillet-o-fish
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
tools/build_occt.sh
```

The last line builds the fixed Open CASCADE kernel into `~/.local/opt/occt-ir`; it takes about
30 minutes and needs `cmake`, `make` and `clang`. Without it, fillets fall back to the kernel in
the Python bindings, which fails some of them on some runs.

A project on Python 3.11 can use the exact bodies, the kernel and the checks without Blender:
`pip install -e <this repo> --no-deps`.

## Run

```
.venv/bin/python tests/test_example.py     # the example below, a few seconds
.venv/bin/python tests/test_runout.py      # the grid blend on the hard case, about ten minutes
```

In a build script:

```python
import numpy as np
from fof import brep, verify

box = brep.rounded_box(0, 0, 0, 160, 80, 60, 7)              # x0 y0 z0 x1 y1 z1, edge radius
riser = brep.rounded_prism(0.05, 25, 80, 60, 7, 55, 130)      # 0.05 mm in from the box's wall, so the loop closes
body = brep.unify(brep.fuse(box, riser))
edges, mids = brep.junction_edges(body, lambda q: bool(np.all(np.abs(q[:, 2] - 60) < 12)))
body = brep.fillet_edges(body, edges, mids, 8.0)              # the fixed kernel, when it is installed
part = brep.mesh(body)                                        # a closed trimesh, tessellated at 0.01 mm
```

## Requirements

macOS on Apple Silicon is where it is built and tested. Python 3.13, because Blender's `bpy`
wheel is pinned to it. The kernel build needs Xcode's command line tools and `cmake`.

## Inputs and output

Dimensions live in the build script, in millimetres, in the part's own frame. Between steps the
engine hands back Open CASCADE shapes; at the end it returns a closed, manifold `trimesh` mesh
with positive volume, tessellated at 0.01 mm, plus one mesh and a note per recorded step for a
viewer. Writing STL or 3MF, slicing and printing are the project's business.

## The stages

1. **Exact bodies** (`fof.brep`): profiles, extrusions, sweeps along bends, offsets for walls,
   sequential Booleans, one tessellation at the end. Fillets that can be drawn in a profile are
   drawn there, before extruding.
2. **Checked kernel fillets** (`fof.brep.fillet_edges`, `fof.kernel`): a 3D fillet runs only
   where its preconditions hold: the edge chain is a closed loop or ends on sharp edges, the
   radius fits beside the neighbouring faces, no end vertex has four or more edges. It runs
   through the fixed kernel, by BREP files and Open CASCADE's DRAW harness, and the result is
   validated by the kernel's own checker, never by `IsDone()` alone.
3. **Grid blends** (`fof.blend`): for a joint that fails its preconditions, the region round it
   goes through a signed-distance grid in Blender: offset out by the radius, then back in. That
   is the rolling-ball fillet's definition, and it cannot fail. The blended region is re-joined
   with the exact mesh by Manifold.
4. **A recorded timeline** (`fof.steps`): every step writes its body and a note.
5. **An independent check** (`fof.verify`): every surface point must carry the rolling ball.
   The largest ball through a point of a rolling-ball fillet that stays clear of the raw body
   has exactly the fillet's radius, so the check maximises the signed distance to the raw mesh
   over the ball of that radius about each point and holds the result to the radius: less
   where the surface comes nearer the raw body than the ball allows, more where it stands
   further off. It needs only the raw bodies as meshes: no offset body (Open CASCADE's offset
   fails on some bodies) and no sampling. Creases are held to a facet of the tightest curve,
   walls to their thickness. The checks count what they inspected, refuse to pass on nothing,
   and every test shifts a good part by 0.1 mm each way to see the check fail.

## What the joints taught

- A fillet whose edge chain runs out on a flush wall fails even in the fixed kernel: 3 builds in
  10 on a duct's junction. A 0.05 mm step on that wall closes the loop, and never prints.
- A ball touching a roof under a bend of inside radius R that starts h above the roof is at most
  (R + h) / 2. The old flares were twice that, which is why they met the bend at a crease. Stay
  under 90 % of it: at 98 % the fillet still met the bend at a crease on some builds and ran up to
  2 mm off the ball at the corners; at 84 % it sits on the ball to 0.01 mm and the corners are
  within 1 mm.
- The kernel's constant-radius fillet is a rolling ball only where the two faces' normals lie
  in the plane normal to the edge: plane on plane, and a cylinder on a plane normal to its axis
  (`BlendFunc_ConstRad` sweeps a circle in that plane). There it is exact to 0.001 mm. Where a
  cylinder meets a cylinder, as a riser's rounded corner over a box's rounded top edge, the
  circle's centre leaves the ball's path and the surface sits up to 0.36 mm inside the ball
  (ball 11), smooth and without a crease; where two fillets meet, the vertex blend is its own
  surface, up to 1 mm off. Hold those zones to smoothness and the rest to the ball.
- A sampled envelope is no reference: the crease where the ball's centre runs falls between the
  samples, and every reading comes out 0 to 0.2 mm high, differently on each run. The exact
  offset body is no reference either: Open CASCADE's offset returned nothing for a riser flush
  with a box's wall and for the vent's chamber. The ball test above needs neither.
- The kernel in the Python bindings (OCP 8.0.1) fails this fillet about one run in ten; its
  internal order follows memory addresses. Open CASCADE merged the fix on 2026-08-09 for release
  8.1, due 2027-01-15. Until a wheel ships, the fix runs through DRAW.
- The grid blend sits about three quarters of a voxel outward (0.15 mm at 0.2 mm) and takes
  minutes per joint, so it is the fallback, applied to a box round the joint.
- Parallel Booleans gave different results from one run to the next. Everything runs sequential.

The research behind these is in `docs/`. How the modules are built and the conventions they
follow are in `fof/README.md`; the tools in `tools/README.md`.

## Status

Started 2026-10-12 from the P2S Mintion exhaust vent, whose Part A now builds through this
engine: ten builds out of ten give the same solid, the fillets on the rolling ball to 0.01 mm
along their straight runs, and `tests/test_example.py` holds its own to 0.05 mm, with the fillets' tangent ends 0.03 mm inside the ball.

## Licence

MIT. Ole Kristensen, Den Frie Vilje ApS.
