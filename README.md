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
box chamber failed Open CASCADE's fillet on some runs. The research behind the design is in
`docs/`. The vent's Part A now builds through `fof.kernel`: Open CASCADE's fixed branch, driven
through its DRAW harness, gives ten identical builds out of ten, with the fillet within 0.08 mm of
the rolling ball along its straight runs and the corners smooth. The level-set blend (`fof.blend`)
is proven on the flush-riser test shape (`tests/test_runout.py`): right by construction, with an
outward bias of about three quarters of a voxel (0.15 mm at 0.2 mm) and minutes per joint, so it
is the fallback.

## Requirements

Python 3.13 (Blender's `bpy` wheel is pinned to it), `cadquery-ocp`, `trimesh`, `manifold3d`,
`numpy`, `scipy`, `bpy`. See `requirements.txt`. Another project's Python 3.11 venv can use the
exact bodies, the kernel and the checks without Blender: `pip install -e <this repo> --no-deps`.

## Tools

- `tools/build_occt.sh` builds Open CASCADE's fixed branch with its DRAW harness into
  `~/.local/opt/occt-ir` (or `$FOF_OCCT`), about 30 minutes.
- `tools/capped.sh CAP_GB cmd...` runs a command and kills it, with everything it started, if
  their memory together passes the cap. Every heavy run goes through it.
