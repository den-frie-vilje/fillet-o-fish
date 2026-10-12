"""Independent checks of a built part: fillets against the rolling ball, surfaces for creases,
walls for thickness. Nothing here uses the kernel or the grid that built the part.

A rolling-ball fillet of radius r is the boundary of the raw body closed by a ball of r: the
largest ball through a surface point that stays clear of the raw body has radius exactly r. So
for a point F on the fillet, the distance to the raw body, maximised over the closed ball of
radius r about F, equals r: less where the surface comes nearer the raw body than the ball
allows, more where it stands further off (a bigger fillet, or a shift). That is a maximisation
over a ball of a point-to-triangle distance, nothing else: no offset body and no sampling. The
checks fail closed: they count what they inspected and refuse to pass on nothing.
"""
import numpy as np, trimesh

def in_region(P, region):
    x0, y0, z0, x1, y1, z1 = region
    return (P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1) & (P[:, 2] > z0) & (P[:, 2] < z1)

def ball_error(F, N, raw, r, steps=11):
    """for each point F with normal N pointing to the side the ball is on: the signed distance to
    `raw` maximised over the closed ball of radius r about F, minus r. Zero on a rolling-ball surface of radius r (and on the raw
    surface itself, where the ball touches). Gradient ascent from the centre the normal gives,
    projected into the ball; the step halves from r / 4 down to r / 4096 (the maximum sits on a
    crease of the distance field, so the error is linear in the last step)."""
    def dist(C):
        """signed: negative inside raw, by the normal of the nearest face (wrong only within a
        facet of an edge, where the distance is near zero anyway)"""
        out = [trimesh.proximity.closest_point(raw, C[i:i + 4000]) for i in range(0, len(C), 4000)]   # in slices: the query's memory grows with the batch
        near, d, tri = (np.concatenate([o[j] for o in out]) for j in range(3))
        return np.where(np.einsum('ij,ij->i', C - near, raw.face_normals[tri]) < 0, -d, d), near
    C = F + N * r; d, near = dist(C)
    for step in r / 2.0 ** np.arange(2, 2 + steps):
        for _ in range(2):
            g = (C - near) * np.sign(d)[:, None]; g /= np.maximum(np.linalg.norm(g, axis=1), 1e-9)[:, None]
            v = C + g * step - F; n = np.linalg.norm(v, axis=1)
            C2 = F + v * np.minimum(1.0, r / np.maximum(n, 1e-9))[:, None]
            d2, near2 = dist(C2); up = d2 > d; C[up] = C2[up]; d[up] = d2[up]; near[up] = near2[up]
    return d - r

def fillet(part, outer, air, rho, wall, region, tol=0.05, corners=(), r_corner=0.0, min_points=200):
    """every vertex of `part` inside `region` lies on a rolling ball of rho about the raw outer body
    (outside surface) or of rho + wall about the raw air body (inside surface), by `ball_error`;
    `outer` and `air` are the unblended bodies as meshes. Points within r_corner (in x, y) of a
    corner centre are where the kernel's fillet is not a rolling ball (two fillets meeting in a
    vertex blend, or an edge between two curved faces, where the kernel sweeps planar circles
    instead): they are reported, not held to the ball."""
    V, N = part.vertices, part.vertex_normals
    k = in_region(V, region); P, Nn = V[k], N[k]
    assert len(P) >= min_points, 'fillet check read only %d points' % len(P)
    # an inside-surface point's normal points into the cavity, against the raw air body's outward
    # normal where it is nearest; an outside point's normal runs with it. Distances cannot tell
    # them apart (an inside fillet near its ends runs closer to the raw outer roof than to the raw
    # air ceiling), and nor can the direction to the nearest air point, which is nothing where the
    # inside surface and the raw air body coincide
    air_side = np.einsum('ij,ij->i', Nn, air.face_normals[trimesh.proximity.closest_point(air, P)[2]]) < 0
    corners = np.asarray(corners, float).reshape(-1, 2)
    in_corner = (np.min(np.linalg.norm(P[:, None, :2] - corners[None], axis=2), axis=1) < r_corner) if len(corners) else np.zeros(len(P), bool)
    ok = True
    # the ball sits outside the body whose edge it rounds: beyond the outside surface, and on the material side of the air surface
    for name, raw, r, side, sel in (('outside', outer, rho, 1.0, ~air_side), ('inside', air, rho + wall, -1.0, air_side)):
        if sel.sum() < min_points // 4:
            print('  fillet %-7s: only %d points, not checked' % (name, sel.sum())); ok = False; continue
        err = ball_error(P[sel], Nn[sel] * side, raw, r); inc = in_corner[sel]; st = ~inc
        if not st.any():
            print('  %-7s stripes: no points outside the corners, not checked' % name); ok = False; continue
        bad = np.abs(err[st]) > tol
        print('  %-7s stripes: %6d points, off the ball by %+.3f..%+.3f mm, %d beyond %.2f' % (name, st.sum(), err[st].min(), err[st].max(), bad.sum(), tol))
        if bad.any():
            q = P[sel][st][bad]; print('    at x %.0f..%.0f, y %.0f..%.0f, z %.1f..%.1f' % (q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max(), q[:, 2].min(), q[:, 2].max()))
        ok &= not bad.any()
        if inc.any(): print('  %-7s corners: %6d points, off the ball by %+.2f..%+.2f mm (the kernel\'s own blends, smoothness only)' % (name, inc.sum(), err[inc].min(), err[inc].max()))
    return ok

def creases(part, region, r_smallest, deflection=0.01, margin=2.0, min_area=0.05):
    """no edge between neighbouring faces in `region` turns more than one facet on the tightest
    curve there does, plus a margin: a tessellation at `deflection` of a radius r turns
    2 acos(1 - deflection / r) per facet"""
    facet = np.degrees(2 * np.arccos(1 - deflection / r_smallest))
    c = part.triangles_center
    sub = part.submesh([np.where(in_region(c, region))[0]], append=True)
    fa = sub.face_adjacency; big = (sub.area_faces[fa] > min_area).all(1)
    ang = np.degrees(sub.face_adjacency_angles)[big]; mid = sub.vertices[sub.face_adjacency_edges[big]].mean(1)
    assert len(ang) > 100, 'crease check read only %d edges' % len(ang)
    bad = ang > facet + margin
    print('  creases: worst turn between neighbours %.1f deg; one facet on the tightest curve (R %.0f) turns %.1f' % (ang.max(), r_smallest, facet))
    if bad.any():
        q = mid[bad]; print('    %d edges above %.1f deg, at x %.0f..%.0f, y %.0f..%.0f, z %.1f..%.1f' % (bad.sum(), facet + margin, q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max(), q[:, 2].min(), q[:, 2].max()))
    return not bad.any()

def wall(part, wall, region, tol=0.05, samples=4000, seed=0):
    """the wall is `wall` thick everywhere inside `region`: from points on either surface, a ray
    straight into the material meets the other surface no sooner than `wall` - tol"""
    rng = np.random.default_rng(seed)
    V, N = part.vertices, part.vertex_normals
    idx = np.where(in_region(V, region))[0]; idx = rng.choice(idx, min(samples, len(idx)), replace=False)
    P, Nn = V[idx], N[idx]
    hits, ray_idx = part.ray.intersects_location(P - Nn * 1e-3, -Nn)[:2]
    if not len(hits): print('  wall: no rays hit'); return False
    d = np.linalg.norm(hits - P[ray_idx], axis=1)
    first = {}
    for h, i in zip(d, ray_idx):
        if i not in first or h < first[i]: first[i] = h
    t = np.array(list(first.values()))
    thin = t < wall - tol
    print('  wall: %d rays, thinnest %.3f mm, %d thinner than %.2f' % (len(t), t.min(), thin.sum(), wall - tol))
    return not thin.any()
