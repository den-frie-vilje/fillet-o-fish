# How CAD systems handle a fillet that runs out at a tangency

Research of 2026-10-12, by web reading only; no kernel experiments. The case: a rectangular
riser rising from a box's roof, flush with the box on two sides, so the concave edge loop between
riser and roof is open and its two ends die out where riser wall and box wall become one plane.
Sources are linked inline. What could not be reached is listed at the end.

## Why the case is degenerate

A constant-radius rolling-ball blend is the envelope of a ball swept along a spine so that it
always touches both base surfaces; the spine is found by intersecting the surfaces' offsets
(Rossignac and Requicha, https://faculty.cc.gatech.edu/~jarek/papers/Offsets.pdf). Where two faces
become tangent and coplanar, their offsets become tangent too, the intersection stops being a
curve, and the ball's centre has no defined position.

## Terminology by system

| System | Terms for the end of a blend | Source |
|---|---|---|
| Fusion | Rolling Ball vs Setback corners; Tangent Chain; error "This might be occurring at the ends of the selected edges"; "blend to zero" | https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-FILLET-SOLID.htm |
| Inventor | Rolling Ball Where Possible; Roll Along Sharp Edges; Setbacks | https://help.autodesk.com/cloudhelp/2025/ENU/Inventor-Help/files/GUID-590A8760-FFBB-41C8-8169-6B7002207884.htm |
| SolidWorks | Overflow type (Default / Keep edge / Keep surface); Round corners; Setback; face fillet Hold line | https://help.solidworks.com/2022/english/SolidWorks/sldworks/c_example_overflow_type.htm |
| Onshape | Allow edge overflow; Smooth fillet corners; face blend with Tangent / Conic hold lines | https://cad.onshape.com/help/Content/fillet.htm |
| NX, Solid Edge (Parasolid) | Overflow Resolutions; Roll on Edges; cliff-edge blend; Cap Sharp Edges; Force Roll Along At Blend Ends | https://www.soliddna.com/SEHelp/ST5/EN/a_h/feat22d.htm |
| Parasolid | overflow, capping, capping face, apex range | https://blogs.sw.siemens.com/plm-components/parasolid-v32-0-release-highlights/ |
| ACIS (DesignModeler, KeyCreator) | cap the blend; terminate and cap itself; feathered down to a point | https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/wb_dm/dm3DSelectRulesBlends.html |
| Creo | round transitions: Stop Case 1/2/3, Stop at Reference, Patch, Corner Sphere; capped blend ends | https://www.ptc.com/community/proewf/newtools/featureguide/round/to_define_a_round_transition.htm |
| Rhino | FilletEdge rail types; "Failure in building corner"; maximum radius handle | https://docs.mcneel.com/rhino/8/help/en-us/commands/filletedge.htm |
| OCCT | contour of tangent edges, spine, stripe; ChFiDS_State FreeBoundary; FreeCAD: "collapsed end-face" | https://tracker.freecad.org/view.php?id=52 |

## What each system does at a tangent run-out

**Fusion.** The official error: "The fillet/chamfer could not be created at the requested size.
This might be occurring at the ends of the selected edges. Try adjusting the size or using
multiple separate operations." The knowledge base advises not to use a value equal to the
available depth: "use slightly reduced values instead (e.g., 11.999 mm instead of 12 mm)"
(https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Error-The-fillet-chamfer-could-not-be-created-at-the-requested-size.html).
Autodesk staff on the forum: "When the edge for fillet doesn't go all the way around your body
it's failing because Fusion cannot make the correct blend where it starts and stops", and "If you
need the fillet to blend to zero, use a variable radius fillet with 0 as one of the end point
values" (https://forums.autodesk.com/t5/fusion-design-validate-document/fillet-rounded-corners-issue/m-p/5739569).
Sensitivity to exact tangency: "Changing the wall angle from 89,99 deg to 90 deg causes the
fillets to fail" (https://forums.autodesk.com/t5/fusion-design-validate-document/fillet-problem/m-p/5569799).
Constant-radius Fusion fillets do not cap or taper at a tangent run-out; they fail.

**SolidWorks.** Overflow type is documented for closed single edges meeting other edges, not for
run-outs. Face fillet with a Hold line "determines the face fillet shape"
(https://help.solidworks.com/2016/english/SolidWorks/sldworks/r_Face_Fillets.htm); the forum's
usual escape is a hold-line fillet with a split line.

**Onshape.** "Allow edge overflow means the fillet can modify edges on the face created by the
fillet to make a smooth, continuous surface" (https://cad.onshape.com/help/Content/fillet.htm).
Forum: "If the edge goes to zero, a regular rolling ball fillet should work, but if it inverts, it
will fail"; threads end with a manual surface (sweep, loft) because the native fillet could not be
made (https://forum.onshape.com/discussion/22223/fillet-not-calculating,
https://forum.onshape.com/discussion/31755/help-with-fillet).

**Parasolid (NX, Solid Edge).** Solid Edge: "Force Roll Along At Blend Ends - Modify the blend and
force it to cliff"; "Cap Sharp Edges" (https://www.soliddna.com/SEHelp/ST5/EN/i_v/roundingoverflow1a.htm).
NX: "Out-of-the-box, the Edge Blend will automatically produce a so-called 'clift-edge' blend"
(https://eng-tips.com/threads/cliff-edge-blends.332230). Parasolid's vocabulary for this end
condition is a cap (a wall face closing the blend) or a cliff. The kernel's functional
description is not public.

**ACIS.** DesignModeler: "if an edge you select ends where another edge is tangent to it, it can
cause problems if you do not select the tangent edge as well ... the algorithm will sometimes
continue with the blend/chamfer along the unselected edge in an attempt to cap the blend".
KeyCreator: "The blend will terminate and cap itself when it detects that it can no longer roll
smoothly onto a new set of entities" (search snippet, https://kubotek3d.com/help?&id=107699).

**Creo.** Round transitions "Stop Case 1/2/3: Terminate the round using geometry configured by
Pro/ENGINEER" and "Stop at Reference: Terminate round geometry at the datum point or datum plane
that you specify": the most explicit "end the fillet at a plane" primitive among the big systems.

**OCCT.** The chain walker marks a tangent extremity `ChFiDS_FreeBoundary`; there is no capping or
tapering logic in ChFi3d. The constant-radius walk has to find ball positions up to that end and
reports not-done, crashes, or returns a silently invalid solid with `IsDone()` true
(https://github.com/Open-Cascade-SAS/OCCT/issues/1371). FreeCAD's developers: "Ending a fillet on
tangent edge would most likely end in a completely collapsed end-face and highly unstable!"
(https://tracker.freecad.org/view.php?id=52).

## Failure modes and fixes, ranked by how often they are recommended

1. **Change the geometry so the chain does not end on a tangency.** An inset or lip so the loop
   closes, or draft so the angle never reaches 0°. How sharp the cliff is: OCCT fillets a 9.999
   in a 10 box but not 10 (https://github.com/Open-Cascade-SAS/OCCT/issues/1177); a cone at 2.8°
   fillets, 2.9° fails (https://github.com/Open-Cascade-SAS/OCCT/issues/1427); Fusion fails at
   90.00° where 89.99° works.
2. **Reorder features: fillet before the Boolean.** FreeCAD: "Simply apply the fillet on the cube
   before fusing to the sphere" (https://tracker.freecad.org/view.php?id=2715). For a concave edge
   that only exists after a fuse, this means putting the fillet into the profile or into a sweep
   that is fused as a solid.
3. **Variable radius to zero at the run-out end.** Recommended by Fusion and Onshape staff; not
   reliable ("tried variable fillet without success"). In OCCT the radius law "must be always
   positive. The user must check this"
   (https://github.com/Open-Cascade-SAS/OCCT/blob/master/dox/user_guides/modeling_algos/modeling_algos.md).
4. **Face blend with a hold line, or a capped face-face blend.** SolidWorks' own error says "try
   using face fillet". OCCT has no public face-blend or hold-line API.
5. **Build the blend by hand** as a swept 2D fillet section along the edge, capped by the wall
   plane, then fused (`BRepOffsetAPI_MakeEvolved`, `MakePipeShell`).
6. **Select the whole tangent chain in one operation** (ACIS documentation; OCCT extends chains
   itself).
7. **Reduce the radius** so no face is consumed and no opposite edge is met
   (https://github.com/Open-Cascade-SAS/OCCT/issues/172).
8. **Merge coplanar faces first** (`ShapeUpgrade_UnifySameDomain`), so the roof is one face.
9. **Setback vertex blends** are for three or more fillets at a vertex and do not address a
   two-face run-out.

## OCCT specifics

Public API (`BRepFilletAPI_MakeFillet`): `Add(E)`, `Add(Radius, E)`, `Add(R1, R2, E)` (linear
law), `Add(Law_Function, E)`, `Add(Array1<gp_Pnt2d>, E)` (parameter and radius pairs);
`SetContinuity`, `SetParams`; diagnostics `Closed`, `ClosedAndTangent`, `NbFaultyContours`,
`StripeStatus` returning {Ok, Error, WalkingFailure, StartsolFailure, TwistedSurface}
(https://github.com/Open-Cascade-SAS/OCCT/blob/master/src/ModelingAlgorithms/TKFillet/BRepFilletAPI/BRepFilletAPI_MakeFillet.hxx).
Documented unhandled cases: a contour ending at a vertex of four or more edges, and "the
intersection of the fillet with a face which limits the contour is not fully contained in this
face".

What the code does at a tangent extremity (`ChFi3d_Builder_1.cxx`): `TangentExtremity` compares
the two face normals at the end vertex; the end status defaults to `FreeBoundary` unless a
tangent-continuing edge is found (the chain continues) or a sharp neighbour exists
(`BreakPoint`). `PerformFilletOnVertex` returns at once for a one-stripe `FreeBoundary` vertex.

Fallbacks in OCCT: `BRepFilletAPI_MakeFillet2d` on a profile face before extrusion;
`BRepOffsetAPI_MakeFilling` for a cap patch; `BRepOffsetAPI_MakeEvolved` for a swept fillet strip
with a flat end face, the "cap" built by hand.

Versions: OCCT 8.0.1 (2026-07-30) hardened `ChFi3d_Builder::StartSol()` and made fillet
reconstruction thread-safe. The fillet handling pull requests 1293 and 1449 (merged 2026-08-09
into branch IR, milestone 8.1, due 2027-01-15) add `ChFi3d_RemoveConsumedFaces` and accept
tangential fillet contacts (https://github.com/Open-Cascade-SAS/OCCT/pull/1293,
https://github.com/Open-Cascade-SAS/OCCT/pull/1449). fof builds that branch; see `tools/build_occt.sh`.

## What a staged engine does by design

- Prismatic blends go into the profile before extruding.
- For concave edges that only exist after a fuse, decide at definition time whether the loop
  closes. If not: a small step so it does, or a swept and capped strip.
- Run `ShapeUpgrade_UnifySameDomain` after every Boolean.
- Before a 3D fillet, check: the dihedral angle along the whole chain stays above a threshold far
  larger than OCCT's 0.57° (5 to 10°); the chain is closed or ends on sharp edges; no end vertex
  has four or more edges; the radius is under 90 % of the room beside it.
- Validate every result with `BRepCheck_Analyzer`, never `IsDone()` alone.
- Fallback ladder: constant radius on the full chain; the same at 0.9 r; a variable law with a
  small positive end radius; a swept and capped strip; a filling patch; skip and report. Log the
  rung used.

## Not reached

Parasolid's functional description and Spatial's ACIS blending documentation (not public); the
Vida, Martin and Várady survey (1994) and the Várady and Rockwood setback paper (1997) beyond
bibliographic pages; Autodesk's "Fillet Best Practices" blog (403); SolidWorks help on fillets
that end on tangent faces (none found); FreeCAD's wiki and forum (anti-bot blocked);
OCCT's Mantis tracker (no longer resolves).
