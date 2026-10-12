# The modules

| Module | What it holds |
|---|---|
| `brep.py` | Exact bodies in Open CASCADE through OCP: rounded boxes and prisms, hull solids, offsets (`grown`), sweeps along a spine, sequential Booleans with a fuzzy tolerance, `unify`, edge selection (`edges_where`, `junction_edges`), `fillet_edges`, and `mesh`, the one tessellation. |
| `kernel.py` | The fixed Open CASCADE kernel (branch IR, the fillet fixes of 2026-08-09) driven through its DRAW harness: the body goes out as BREP, the fillet runs there, the result comes back validated. `FOF_OCCT` names the install prefix. |
| `blend.py` | Rolling-ball blends on a signed-distance grid through Blender's geometry nodes (`bpy`, loaded on first use): a closing of the outside by the radius and of the air by radius plus wall, cropped to a region and re-joined by Manifold. |
| `verify.py` | The independent checks: the ball test (the signed distance to the raw mesh maximised over the ball about each point), the fillet check with its corner zones, the crease check, the wall check. |
| `steps.py` | Records each construction step as a mesh and a note for a viewer's timeline. |

## Conventions

- **Booleans run sequential** and with a fuzzy value of 1e-5 mm, so faces that are flush within
  it merge. Parallel runs gave different results from one run to the next.
- **A fillet is never trusted on `IsDone()`**: the result goes through `BRepCheck_Analyzer`, and
  the kernel path reads the DRAW log for its own checker's verdict.
- **The envelope check fails closed.** It asserts how many points it inspected, refuses to run
  on fewer than it needs, and each test shifts a good part by 0.1 mm to see it fail.
- **No ray casting against big meshes.** Which side of a surface a point lies on comes from
  whether a step along its normal moves it towards or away from the envelope; containment
  queries on a 100,000-face mesh allocate gigabytes.
- **Heavy runs go through `tools/capped.sh`**, which kills a process and its children when their
  memory passes a cap.
- **Tolerances are stated with their reason**: 0.1 mm along a fillet's straight runs (a quarter
  of a printed layer, and the reach of the kernel's vertex blends), one facet of the tightest
  curve plus 2° for a crease.

## Where the engine came from

The first user is the P2S Mintion exhaust vent, a private project whose build scripts keep their
own copy of the edge selection (`occ_body.py`) from before it was ported here. New projects use
`fof.brep` directly.
