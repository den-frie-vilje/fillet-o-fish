"""The README's example: a riser 0.05 mm in from a box's wall, so the fillet loop closes, rounded
through the fixed kernel, meshed, and checked against the rolling-ball envelope.

Run: .venv/bin/python tests/test_example.py   (a few seconds; exits 1 on a failure)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from fof import brep, verify, kernel

RHO, WALL = 8.0, 3.0
def body(grow):
    box = brep.rounded_box(grow, grow, grow, 160 - grow, 80 - grow, 60 - grow, 7 - grow)
    riser = brep.rounded_prism(0.05 + grow, 25 + grow, 80 - grow, 60 - grow, 7 - grow, 40, 130 - grow)   # starts inside the box, under its rounded top edge
    return brep.unify(brep.fuse(box, riser))

print('fixed kernel:', 'installed' if kernel.available() else 'not installed, using the bindings')
outer_raw = body(0.0)
edges, mids = brep.junction_edges(outer_raw, lambda q: bool(np.all(np.abs(q[:, 2] - 60) < 12)))
outer = brep.fillet_edges(outer_raw, edges, mids, RHO)
air_raw = body(WALL)
edges_in, mids_in = brep.junction_edges(air_raw, lambda q: bool(np.all(np.abs(q[:, 2] - 57) < 12)))
air = brep.fillet_edges(air_raw, edges_in, mids_in, RHO + WALL)
part = brep.mesh(brep.cut(outer, air))
print('part: %d faces, closed %s, volume %.1f cm3, %d outside and %d inside junction edges rounded' % (len(part.faces), part.is_watertight, part.volume / 1000, len(edges), len(edges_in)))
region = (-10, 15, 50, 90, 70, 72)
# over the box's rounded top edge (x < 7) the riser's corners are cylinder meeting cylinder, where the
# kernel's fillet is a planar-section blend, 0.1 (ball 8) and 0.36 mm (ball 11) inside the rolling ball:
# held to smoothness only, within the ball centre's radius (7 + 8) of the corner axes
corners, r_corner = [(7.05, 32), (7.05, 53)], 7 + RHO
raw_outer, raw_air = brep.mesh(outer_raw), brep.mesh(air_raw)
ok = verify.fillet(part, raw_outer, raw_air, RHO, WALL, region, tol=0.05, corners=corners, r_corner=r_corner)   # the fillets' tangent ends run 0.03 inside the ball
ok &= verify.creases(part, region, 4.0)
# the check must be able to fail: the same part shifted by a tenth of a millimetre, either way
for dz in (0.1, -0.1):
    shifted = part.copy(); shifted.apply_translation([0, 0, dz])
    flagged = not verify.fillet(shifted, raw_outer, raw_air, RHO, WALL, region, tol=0.05, corners=corners, r_corner=r_corner)
    print('self-test: a %+.1f mm shift is %s' % (dz, 'flagged' if flagged else 'NOT flagged'))
    ok &= flagged
print('example: %s' % ('OK' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
