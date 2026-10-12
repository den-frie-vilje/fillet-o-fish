"""Record the steps a part is built in, for the viewer's timeline.

A build calls step(part, name, body, note) after each construction step. The body is a manifold
(the part so far) or a trimesh. Each step is written to out/steps/<part>/<nn> <name>.stl and
listed in out/steps/<part>.json; scene.py puts them in the viewer scene. Steps go through the
same decimation as the parts, so the scene stays small.
"""
import os, json, numpy as np, trimesh

_STEPS = {}

def step(part, name, body, note='', kind='solid'):
    """kind: 'solid' (the part so far), 'tool' (a body that is about to be added or cut), 'cut'"""
    m = body if isinstance(body, trimesh.Trimesh) else _tm(body)
    os.makedirs(f'out/steps/{part}', exist_ok=True)
    k = len(_STEPS.setdefault(part, []))
    fn = f'out/steps/{part}/{k:02d} {name}.stl'
    m.export(fn)
    _STEPS[part].append(dict(index=k, name=name, note=note, kind=kind, file=fn, faces=len(m.faces),
                             volume_cm3=round(float(abs(m.volume)) / 1000, 2)))
    json.dump(_STEPS[part], open(f'out/steps/{part}.json', 'w'), indent=1)

def _tm(man):
    mm = man.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=False)
