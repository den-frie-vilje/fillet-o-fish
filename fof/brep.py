"""Exact bodies in Open CASCADE (OCP): primitives, sweeps, offsets, Booleans and one tessellation.

Everything here returns OCCT shapes except mesh(), which turns a shape into a closed trimesh.
Booleans run sequentially: parallel Booleans and fillets gave different results run to run.
"""
import numpy as np, trimesh
from OCP.gp import gp_Pnt
from OCP.GC import GC_MakeArcOfCircle
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe, BRepOffsetAPI_MakeOffsetShape
from OCP.BRepOffset import BRepOffset_Mode
from OCP.GeomAbs import GeomAbs_JoinType
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
from OCP.BOPAlgo import BOPAlgo_Options
from OCP.collections import List_TopoDS_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_REVERSED
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Vec
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

BOPAlgo_Options.SetParallelMode_s(False)

def P(p): return gp_Pnt(*map(float, p))

# ---- primitives -------------------------------------------------------------------------
def rrect_face(cx, cy, z, hu, hv, r):
    """a rounded rectangle in the plane z: half sizes hu (x), hv (y), corner radius r"""
    corners = [(cx + hu - r, cy + hv - r, 0), (cx - hu + r, cy + hv - r, 90), (cx - hu + r, cy - hv + r, 180), (cx + hu - r, cy - hv + r, 270)]
    w = BRepBuilderAPI_MakeWire()
    for i, (ox, oy, a0) in enumerate(corners):
        a, b = np.radians(a0), np.radians(a0 + 90); m = (a + b) / 2
        p0, pm, p1 = [(ox + r * np.cos(t), oy + r * np.sin(t), z) for t in (a, m, b)]
        w.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(P(p0), P(pm), P(p1)).Value()).Edge())
        nx, ny, _ = corners[(i + 1) % 4]
        w.Add(BRepBuilderAPI_MakeEdge(P(p1), P((nx + r * np.cos(b), ny + r * np.sin(b), z))).Edge())
    return BRepBuilderAPI_MakeFace(w.Wire()).Face()

def rounded_prism(x0, y0, x1, y1, r, z0, z1):
    """a rounded rectangle x0..x1, y0..y1 (corner radius r) extruded from z0 to z1"""
    f = rrect_face((x0 + x1) / 2, (y0 + y1) / 2, z0, (x1 - x0) / 2, (y1 - y0) / 2, r)
    return BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, z1 - z0)).Shape()

def hull_solid(points):
    """the convex hull of points as a solid with one face per flat side"""
    h = trimesh.convex.convex_hull(np.asarray(points, float))
    sew = BRepBuilderAPI_Sewing(1e-6)
    for tri in h.triangles:
        sew.Add(BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakePolygon(P(tri[0]), P(tri[1]), P(tri[2]), True).Wire()).Face())
    sew.Perform()
    ex = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
    return unify(BRepBuilderAPI_MakeSolid(TopoDS.Shell(ex.Current())).Solid())

def rounded_box(x0, y0, z0, x1, y1, z1, r):
    """a box with every edge and corner rounded by r: the inner box grown by r"""
    pts = [[x, y, z] for x in (x0 + r, x1 - r) for y in (y0 + r, y1 - r) for z in (z0 + r, z1 - r)]
    return grown(hull_solid(pts), r)

def grown(shape, d):
    """shape grown by d with rounded edges and corners: the exact form of shape (+) ball d"""
    mk = BRepOffsetAPI_MakeOffsetShape()
    mk.PerformByJoin(shape, d, 1e-6, BRepOffset_Mode.BRepOffset_Skin, False, False, GeomAbs_JoinType.GeomAbs_Arc)
    return mk.Shape()

def sweep(profile_face, spine_points, bends=()):
    """profile swept along a polyline spine; bends are (index, mid, end) arcs replacing a corner"""
    w = BRepBuilderAPI_MakeWire()
    pts = [P(p) for p in spine_points]
    for i in range(len(pts) - 1):
        w.Add(BRepBuilderAPI_MakeEdge(pts[i], pts[i + 1]).Edge())
    return BRepOffsetAPI_MakePipe(w.Wire(), profile_face).Shape()

# ---- booleans ---------------------------------------------------------------------------
def _lists(a, b):
    la, lb = List_TopoDS_Shape(), List_TopoDS_Shape(); la.Append(a); lb.Append(b); return la, lb

def _boolean(op, a, b, fuzzy):
    la, lb = _lists(a, b)
    op.SetArguments(la); op.SetTools(lb); op.SetFuzzyValue(fuzzy); op.SetRunParallel(False); op.Build()
    assert op.IsDone(), 'boolean failed'
    return unify(op.Shape())

def fuse(a, b, fuzzy=1e-5):
    """a and b joined. The fuzzy value treats faces within it as the same face, which flush walls need."""
    out = _boolean(BRepAlgoAPI_Fuse(), a, b, fuzzy)
    assert volume(out) > max(volume(a), volume(b)) - 1e-6, 'fused body is smaller than its parts'
    return out

def cut(a, b, fuzzy=1e-5): return _boolean(BRepAlgoAPI_Cut(), a, b, fuzzy)
def common(a, b, fuzzy=1e-5): return _boolean(BRepAlgoAPI_Common(), a, b, fuzzy)

def unify(shape):
    u = ShapeUpgrade_UnifySameDomain(shape, True, True, True); u.Build(); return u.Shape()

def volume(shape):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g); return g.Mass()

def valid(shape): return BRepCheck_Analyzer(shape).IsValid()

# ---- edges and fillets --------------------------------------------------------------------
def unique_edges(shape):
    out = []; ex = TopExp_Explorer(shape, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge(ex.Current()); ex.Next()
        if not any(e.IsSame(q) for q in out): out.append(e)
    return out

def edge_faces(e, faces):
    """the faces an edge belongs to (normally two)"""
    out = []
    for f in faces:
        ex = TopExp_Explorer(f, TopAbs_EDGE)
        while ex.More():
            if ex.Current().IsSame(e): out.append(f); break
            ex.Next()
    return out

def edge_turn(faces, p):
    """the angle (degrees) between the normals of the faces that meet at point p; pass the edge's
    own faces (edge_faces), or a face that merely passes close by can be paired instead"""
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    ns = []
    for f in faces:
        pr = GeomAPI_ProjectPointOnSurf(p, BRep_Tool.Surface_s(f))
        if pr.NbPoints() and pr.LowerDistance() < 1e-4:
            u, v = pr.LowerDistanceParameters()
            sp = BRepLProp_SLProps(BRepAdaptor_Surface(f), u, v, 1, 1e-6)
            if sp.IsNormalDefined():
                n = sp.Normal(); ns.append(np.array([n.X(), n.Y(), n.Z()]) * (-1 if f.Orientation() == TopAbs_REVERSED else 1))
    if len(ns) < 2: return 0.0
    return float(np.degrees(np.arccos(np.clip(ns[0] @ ns[1], -1, 1))))

def edges_where(s, keep, faces=None):
    """the edges of s that keep(points along it) accepts, with a midpoint of each; with faces,
    only edges whose two faces actually turn (a seam between flush faces has nothing to round)"""
    edges, mids = [], []
    for e in unique_edges(s):
        c = BRepAdaptor_Curve(e)
        ts = np.linspace(c.FirstParameter(), c.LastParameter(), 5)
        pts = np.array([[c.Value(t).X(), c.Value(t).Y(), c.Value(t).Z()] for t in ts])
        if keep(pts) and (faces is None or edge_turn(edge_faces(e, faces), c.Value(ts[2])) > 1.0):
            edges.append(e); mids.append(pts[2])
    assert edges, 'no edges found to fillet'
    return edges, mids

def junction_edges(s, keep):
    """the edges of s that keep() accepts and that actually turn, with a midpoint of each"""
    faces = []
    ex = TopExp_Explorer(s, TopAbs_FACE)
    while ex.More(): faces.append(TopoDS.Face(ex.Current())); ex.Next()
    return edges_where(s, keep, faces)

from fof import kernel as fof_kernel          # the fixed kernel (OCCT's IR branch) through its DRAW harness

def fillet_edges(s, edges, mids, rho):
    """s with the given edges rounded by a ball of rho: through the fixed kernel when it is installed"""
    if fof_kernel is not None and fof_kernel.available():
        return fof_kernel.fillet(s, mids, rho)
    fl = BRepFilletAPI_MakeFillet(s)
    for e in edges: fl.Add(rho, e)
    fl.Build(); assert fl.IsDone(), 'fillet failed'
    out = fl.Shape()
    assert BRepCheck_Analyzer(out).IsValid(), 'filleted body is not a valid solid'
    return out

def fused_and_filleted(make_a, make_b, rho, keep):
    """make_a() and make_b() fused, with every edge that keep(points along it) accepts rounded by a
    ball of rho. Returns the result, the number of edges, and the fused body before the fillet."""
    if fof_kernel is not None and fof_kernel.available():
        a, b = make_a(), make_b()
        s = unify(fuse(a, b))
        assert volume(s) > max(volume(a), volume(b)), 'fused body is smaller than its parts'
        edges, mids = junction_edges(s, keep)
        return fof_kernel.fillet(s, mids, rho), len(edges), s
    # shortcut: the bindings' own kernel (8.0.1) fails this fillet on some runs (its internal order
    # follows memory addresses); a fresh attempt from new solids nearly always succeeds and every
    # success gives the same solid. Upgrade: install the fixed kernel (fof: tools/build_occt.sh).
    for attempt in range(8):
        a, b = make_a(), make_b()
        s = unify(fuse(a, b))
        assert volume(s) > max(volume(a), volume(b)), 'fused body is smaller than its parts'
        edges, _ = junction_edges(s, keep)
        fl = BRepFilletAPI_MakeFillet(s)
        for e in edges: fl.Add(rho, e)
        fl.Build()
        if fl.IsDone(): break
    assert fl.IsDone(), 'fillet failed %d times' % (attempt + 1)
    if attempt: print('fillet %.0f mm: done on attempt %d' % (rho, attempt + 1))
    out = fl.Shape()
    assert BRepCheck_Analyzer(out).IsValid(), 'filleted body is not a valid solid'
    return out, len(edges), s


# ---- tessellation -----------------------------------------------------------------------
def mesh(shape, deflection=0.01, angle=0.05):
    """triangulate a solid: deflection (mm) and angle (rad) bound the facets' distance and turn"""
    BRepMesh_IncrementalMesh(shape, deflection, False, angle, True)
    V, F, off = [], [], 0
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current()); ex.Next(); loc = TopLoc_Location()
        t = BRep_Tool.Triangulation_s(f, loc)
        if t is None: continue
        T = loc.Transformation()
        V += [(lambda p: (p.X(), p.Y(), p.Z()))(t.Node(i).Transformed(T)) for i in range(1, t.NbNodes() + 1)]
        rev = f.Orientation() == TopAbs_REVERSED
        for i in range(1, t.NbTriangles() + 1):
            a, b, c = t.Triangle(i).Get()
            F.append((off + a - 1, off + c - 1, off + b - 1) if rev else (off + a - 1, off + b - 1, off + c - 1))
        off += t.NbNodes()
    m = merge_close(trimesh.Trimesh(np.array(V), np.array(F), process=True))
    assert m.is_watertight, 'meshed body is not closed'
    if m.volume < 0: m.invert()
    return m

def merge_close(m, tol=1e-4):
    """merge vertices closer than tol and drop the triangles that collapse: a fuzzy fuse leaves the
    two sides of a few edges up to its fuzzy value apart"""
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import coo_matrix
    from scipy.spatial import cKDTree
    pairs = cKDTree(m.vertices).query_pairs(tol, output_type='ndarray')
    n = len(m.vertices)
    _, lab = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)), directed=False)
    F = lab[m.faces]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    V = np.zeros((lab.max() + 1, 3)); V[lab] = m.vertices
    return trimesh.Trimesh(V, F, process=True)
