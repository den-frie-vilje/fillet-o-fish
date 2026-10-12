"""Rolling-ball blends on a signed-distance grid, through Blender's geometry nodes (bpy).

A rolling-ball fillet is a morphological closing: offset the solid outward by the radius, then
back inward. On a signed-distance grid that is exact to about one voxel and has no edge chain
to fail, so a fillet that runs out where two faces become coplanar just fades away. The blend is
applied in a box round the joint; outside it the exact tessellation is kept, and the two are
joined by Manifold.

The wall stays constant because the outside and the air are blended with concentric balls:
outside by rho, air by rho + wall. Both grids are built from the same voxel lattice.
"""
import numpy as np, trimesh, bpy

ADAPTIVITY = 0.5

def _bpy_mesh(m, name):
    me = bpy.data.meshes.new(name)
    me.from_pydata(m.vertices.tolist(), [], m.faces.tolist())
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def _to_trimesh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    V = np.array([v.co[:] for v in me.vertices], float)
    F = []
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(1, len(vs) - 1): F.append((vs[0], vs[i], vs[i + 1]))
    ev.to_mesh_clear()
    return trimesh.Trimesh(V, np.array(F), process=True)

def _node_group(voxel, offsets):
    """Mesh -> SDF grid -> offset by each value in turn -> mesh. Offsets alternate +r, -r for a closing."""
    ng = bpy.data.node_groups.new('fof_blend', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nin = ng.nodes.new('NodeGroupInput'); nout = ng.nodes.new('NodeGroupOutput')
    to_sdf = ng.nodes.new('GeometryNodeMeshToSDFGrid')
    to_sdf.inputs['Voxel Size'].default_value = voxel
    to_sdf.inputs['Band Width'].default_value = max(3, int(round(max(abs(o) for o in offsets) / voxel)) + 3)
    ng.links.new(nin.outputs['Geometry'], to_sdf.inputs['Mesh'])
    last = to_sdf.outputs['SDF Grid']
    for d in offsets:
        off = ng.nodes.new('GeometryNodeSDFGridOffset')
        off.inputs['Distance'].default_value = d
        ng.links.new(last, off.inputs['Grid']); last = off.outputs['Grid']
    to_mesh = ng.nodes.new('GeometryNodeGridToMesh')
    to_mesh.inputs['Adaptivity'].default_value = ADAPTIVITY     # 0: a triangle per voxel; towards 1: flat regions merge
    ng.links.new(last, to_mesh.inputs['Grid'])
    ng.links.new(to_mesh.outputs['Mesh'], nout.inputs['Geometry'])
    return ng

def closing(m, rho, voxel):
    """m rounded on its concave edges by a ball of rho: offset out by rho, then in by rho"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob = _bpy_mesh(m, 'fof_in')
    mod = ob.modifiers.new('fof', 'NODES')
    mod.node_group = _node_group(voxel, [rho, -rho])
    out = _to_trimesh(ob)
    assert len(out.faces), 'the grid produced no surface'
    return out

def _clip(m, region):
    x0, y0, z0, x1, y1, z1 = region
    return m.slice_plane(np.array([[x0, 0, 0], [x1, 0, 0], [0, y0, 0], [0, y1, 0], [0, 0, z0], [0, 0, z1]]),
                         np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]), cap=True)

def rolling_ball(outer, air, rho, wall, region, voxel=0.05):
    """the part (outer minus air) with the joint inside `region` rounded: outside by rho, inside
    by rho + wall. Returns a closed trimesh."""
    import manifold3d as mf
    def M(t): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
    def T(man):
        mm = man.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=True)
    x0, y0, z0, x1, y1, z1 = region
    pad = rho + wall + 4 * voxel
    big = (x0 - pad, y0 - pad, z0 - pad, x1 + pad, y1 + pad, z1 + pad)
    # blend each surface on a padded crop, so the grid's band reaches past the region's walls
    outer_b = closing(_clip(outer, big), rho, voxel)
    air_b = closing(_clip(air, big), rho + wall, voxel)
    box = mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
    blended = (M(outer_b) - M(air_b)) ^ box
    exact = (M(outer) - M(air)) - box
    part = exact + blended
    assert part.status() == mf.Error.NoError, 'manifold union failed: %s' % part.status()
    return T(part)
