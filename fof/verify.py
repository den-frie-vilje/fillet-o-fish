"""Independent checks of a built part: fillets against the rolling-ball envelope, walls for
thickness, meshes for closure. Nothing here uses the kernel or the grid that built the part.

The envelope of a rolling-ball fillet is the unblended solid grown by the ball's radius: every
point of the filleted surface lies exactly that radius inside the envelope's boundary. So the
check is a distance query, and it fails closed: it counts what it inspected and refuses to pass
on nothing.
"""
import numpy as np, trimesh

def _in_region(P, region):
    x0, y0, z0, x1, y1, z1 = region
    return (P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1) & (P[:, 2] > z0) & (P[:, 2] < z1)

def _side(outer, P, N):
    """is each sampled point on the air surface? Air-surface points lie inside the unblended
    outer body (the cavity is within its volume); outside-surface points, nudged along their
    normal, lie outside it"""
    return outer.contains(P + N * 0.05)

def fillet(part, outer, air, rho, wall, region, tol=0.05, min_points=200):
    """every vertex of `part` inside `region` sits rho (outside) or rho + wall (air) inside the
    boundary of the unblended solid grown by that radius"""
    import manifold3d as mf
    V, N = part.vertices, part.vertex_normals
    k = _in_region(V, region); P, Nn = V[k], N[k]
    assert len(P) >= min_points, 'fillet check read only %d points' % len(P)
    env_out = _grown(outer, rho)
    env_air = _grown(air, rho + wall)
    inner = _side(outer, P, Nn)
    ok = True
    for name, env, r, sel in (('outside', env_out, rho, ~inner), ('inside', env_air, rho + wall, inner)):
        if sel.sum() < min_points // 4:
            print('  fillet %-7s: only %d points, not checked' % (name, sel.sum())); ok = False; continue
        d = _dist(env, P[sel])
        err = d - r
        bad = np.abs(err) > tol
        print('  fillet %-7s: %6d points, off its ball by %+.3f..%+.3f mm, %d beyond %.2f' % (name, sel.sum(), err.min(), err.max(), bad.sum(), tol))
        ok &= not bad.any()
    return ok

def _grown(m, r, h=None):
    """the boundary of m (+) ball r, sampled: points at distance exactly r from m, on the outside.
    Grid points of spacing h (default r / 8) over m's bounds padded by r get their distance to a
    dense sampling of m's surface from a KD-tree; the outside is the grid's connected region from
    its corner that never touches m (the cavity is sealed off by the wall); points of the outside
    within a cell of r are snapped onto the exact distance-r surface."""
    from scipy.spatial import cKDTree
    from scipy import ndimage
    h = h or r / 8.0
    S = trimesh.sample.sample_surface_even(m, int(m.area / (0.25 * h * h)) + 1000)[0]
    S = np.vstack([S, m.vertices])
    tree = cKDTree(S)
    lo, hi = m.bounds[0] - r - 2 * h, m.bounds[1] + r + 2 * h
    ax = [np.arange(lo[i], hi[i], h) for i in range(3)]
    shape = tuple(len(a) for a in ax)
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    d, idx = tree.query(G)
    free = (d > 0.5 * h).reshape(shape)
    lab, _ = ndimage.label(free)
    outside = (lab == lab[0, 0, 0]).reshape(-1)
    assert outside.sum() > 0.1 * len(G), 'the envelope grid found no outside'
    k = outside & (np.abs(d - r) < 0.6 * h)
    P, Sn, dk = G[k], S[idx[k]], d[k]
    on = Sn + (P - Sn) * (r / dk)[:, None]                      # snapped to exactly r from the surface sample
    class Env:
        def __init__(self, P): self.tree = cKDTree(P)
    return Env(on)

def _dist(env, P):
    return env.tree.query(P)[0]

def wall(part, wall, region, tol=0.05, samples=4000, seed=0):
    """the wall is `wall` thick everywhere inside `region`: from points on the outside surface,
    the nearest point on the air surface is `wall` away"""
    rng = np.random.default_rng(seed)
    V, N = part.vertices, part.vertex_normals
    k = _in_region(V, region)
    idx = np.where(k)[0]; idx = rng.choice(idx, min(samples, len(idx)), replace=False)
    P, Nn = V[idx], N[idx]
    # shoot inward along the normal: the first hit is the opposite face of the wall
    hits, ray_idx = part.ray.intersects_location(P - Nn * 1e-3, -Nn)[:2]
    if not len(hits): print('  wall: no rays hit'); return False
    d = np.linalg.norm(hits - P[ray_idx], axis=1)
    # keep the nearest hit per ray
    first = {}
    for h, i in zip(d, ray_idx):
        if i not in first or h < first[i]: first[i] = h
    t = np.array(list(first.values()))
    # across a plain wall the ray meets the far side at exactly wall; through a fillet it is
    # longer only where the surfaces are not parallel, so a lower bound is what matters
    thin = t < wall - tol
    print('  wall: %d rays, thinnest %.3f mm, %d thinner than %.2f' % (len(t), t.min(), thin.sum(), wall - tol))
    return not thin.any()
