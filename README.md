# Fillet-O-Fish

A staged, parametric engine for 3D-printable parts, in Python. It builds parts the way a CAD
timeline does: a profile, an extrusion or sweep, a join, a blend, each step recorded so a viewer
can show it and a reader can comment on it. It exists because the blend between two bodies is
where kernels fail, and it solves that by construction instead of by luck.

## How a part is built

1. **Exact bodies.** Profiles, extrusions, sweeps along bends, shells and Booleans are built as
   exact solids in Open CASCADE (OCP). Fillets that can be drawn in the profile are drawn there,
   before extruding.
2. **Checked kernel fillets.** A 3D fillet on an edge chain is attempted only when the chain
   passes its preconditions: the two faces turn by at least a minimum angle everywhere along it,
   the chain is a closed loop or ends on sharp edges, no end vertex has four or more edges, and
   the radius is under 90 % of the room beside it. The result is validated by the kernel's own
   checker, never by `IsDone()` alone.
3. **Level-set blends.** Where a chain fails its preconditions, the region round the joint goes
   through a signed-distance grid: offset out by the radius, then back in. That is the rolling-ball
   fillet's definition, and on a grid a tangent run-out just stops changing the surface. The
   blended region is re-joined with the exact mesh.
4. **A recorded timeline.** Every step writes its body and a note, so a viewer can step through
   the build.
5. **An independent check.** The finished part is measured against the ideal: fillet surfaces
   against the rolling-ball envelope, walls for thickness, the mesh for closure.

## Status

Started 2026-10-12 from the P2S Mintion exhaust vent, where the junction of a swept duct and a
box chamber failed Open CASCADE's fillet nondeterministically. The research behind the design is
in `docs/research.md`. The first proof is the level-set blend on a small test shape
(`tests/test_runout.py`): a riser flush with a box on two sides, the case every B-rep kernel
struggles with.

## Requirements

Python 3.13 (Blender's `bpy` wheel is pinned to it), `cadquery-ocp`, `trimesh`, `manifold3d`,
`numpy`, `scipy`, `bpy`. See `requirements.txt`.
