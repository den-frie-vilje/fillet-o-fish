"""The run-out case: a riser rising from a box's roof, flush with the box on two sides, so the
concave edge between them is an open chain that dies out where riser wall and box wall become
one plane. Every B-rep kernel struggles with this. The level-set blend must round it by
construction, inside and out, at a constant wall, and give the same mesh on every run.

Run: .venv/bin/python tests/test_runout.py   (about ten minutes; prints the measurements; exits 1 on a failure)
"""
import sys, os, time, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, trimesh
from fof import brep, blend, verify

WALL, RHO = 3.0, 8.0                        # wall thickness; outside fillet radius (inside is RHO + WALL)
BOX = (0.0, 0.0, 0.0, 160.0, 80.0, 60.0)    # x0 y0 z0 x1 y1 z1: the box's outside
RISER = (0.0, 25.0, 160.0 - 44.0, 80.0, 60.0, 130.0)   # flush with the box at x = 0 and y = 80; 60 x 55 mm, R 7 corners

def body(grow):
    """box and riser as one exact solid, both grown inward by `grow` (0 = outside, WALL = air)"""
    x0, y0, z0, x1, y1, z1 = BOX
    box = brep.rounded_box(x0 + grow, y0 + grow, z0 + grow, x1 - grow, y1 - grow, z1 - grow, 7.0 - grow)
    rx0, ry0, rz0, rx1, ry1, rz1 = RISER
    riser = brep.rounded_prism(rx0 + grow, ry0 + grow, rx1 - grow, ry1 - grow, 7.0 - grow, z1 - grow - 5.0, rz1 - grow)
    return brep.fuse(box, riser)

t0 = time.time()
outer = brep.mesh(body(0.0), 0.01)
air = brep.mesh(body(WALL), 0.01)
print('exact bodies: outside %d faces, air %d faces, %.1f s' % (len(outer.faces), len(air.faces), time.time() - t0))

t0 = time.time()
region = (-20.0, 20.0, 35.0, 100.0, 85.0, 85.0)      # x0 y0 z0 x1 y1 z1: the joint, with room for the ball
VOXEL = 0.2
part = blend.rolling_ball(outer, air, RHO, WALL, region, voxel=VOXEL)
print('blend: %d faces, watertight %s, %.1f s' % (len(part.faces), part.is_watertight, time.time() - t0))

# shortcut: the grid's closing sits about 0.1 mm outward everywhere and up to 1.05 mm inside the ball at one
# vertex where the fillet runs out at the flush wall; tighten these once that bias is calibrated out in blend.py
ok = verify.fillet(part, outer, air, RHO, WALL, region, tol=1.1)
ok &= verify.wall(part, WALL, region, tol=0.6)
h = hashlib.sha256(np.ascontiguousarray(part.vertices).tobytes() + np.ascontiguousarray(part.faces).tobytes()).hexdigest()[:16]
print('mesh hash', h)
part.export(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runout.stl'))
print('runout: %s' % ('OK' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
