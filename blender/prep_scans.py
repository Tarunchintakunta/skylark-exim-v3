"""Prepare the photogrammetry scans in assets-src/cc0/fish/ (CC BY 4.0, credited in docs/LICENSES.md) for the
scenes and the product turntables.

Each scan: import the GLB, drop the colour-checker cube, join the chunks, orient (length along +X, back up +Z, the
flat side facing Y), centre, scale to 1 m long, give the scanned colour a wet clearcoat, and save as
SCAN_<name> plus a decimated SCAN_<name>_LOD (for instancing dozens in a catch pile or crate) in
assets-src/blender/fish_scans.blend.
  Blender -b --factory-startup --python blender/prep_scans.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, 'assets-src', 'cc0', 'fish')
OUT = os.path.join(REPO, 'assets-src', 'blender', 'fish_scans.blend')
SCANS = {
    # name: (file, flip head to +X, roll so the back is up, LOD ratio)
    'Tuna': ('tuna-yellowfin-ffish.glb', True, -math.pi / 2, 0.02),
    'Prawn': ('shrimp-green-tiger-ffish.glb', True, -math.pi / 2, 0.03),
}


def import_scan(name, fn, flip, roll, lod):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, fn))
    new = [o.name for o in bpy.data.objects if o not in before]
    meshes = []
    for nm in new:
        o = bpy.data.objects[nm]
        if o.type == 'MESH' and (len(o.data.vertices) == 24 or (o.parent and o.parent.name.startswith('Cube'))):
            continue   # the colour-checker cube
        if o.type == 'MESH':
            meshes.append(nm)
    bpy.context.view_layer.update()
    mws = {nm: bpy.data.objects[nm].matrix_world.copy() for nm in meshes}
    for nm in new:
        if nm not in meshes:
            bpy.data.objects.remove(bpy.data.objects[nm])
    meshes = [bpy.data.objects[nm] for nm in meshes]
    for o in meshes:
        o.parent = None
        o.matrix_world = mws[o.name]
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    with bpy.context.temp_override(active_object=meshes[0], object=meshes[0], selected_objects=meshes,
                                   selected_editable_objects=meshes):
        bpy.ops.object.join()
    ob = meshes[0]
    ob.name = f'SCAN_{name}'
    me = ob.data
    # orient by the bounding box: longest -> X, shortest -> Y (flat side), remaining -> Z
    vs = [v.co for v in me.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    dims = hi - lo
    order = sorted(range(3), key=lambda i: -dims[i])   # longest, middle, shortest
    perm = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
    perm[0][order[0]] = 1    # new X = longest
    perm[2][order[1]] = 1    # new Z = middle (fish height)
    perm[1][order[2]] = 1    # new Y = shortest (width)
    if perm.determinant() < 0:
        perm[1] = -perm[1]
    c = (lo + hi) / 2
    T = Matrix.Translation(-c)
    R = perm.to_4x4()
    if flip:
        R = Matrix.Rotation(math.pi, 4, 'Z') @ R
    if roll:
        R = Matrix.Rotation(roll, 4, 'X') @ R
    me.transform(R @ T)
    L = max(v.co.x for v in me.vertices) - min(v.co.x for v in me.vertices)
    me.transform(Matrix.Diagonal((1 / L, 1 / L, 1 / L, 1)))
    for p in me.polygons:
        p.use_smooth = True
    # wet look on the scanned albedo
    for m in me.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value = 0.3
                    if n.inputs['Roughness'].links:
                        m.node_tree.links.remove(n.inputs['Roughness'].links[0])
                    n.inputs['Coat Weight'].default_value = 0.55
                    n.inputs['Coat Roughness'].default_value = 0.04
                    n.inputs['Specular IOR Level'].default_value = 0.6
    # LOD copy for crowds
    lod_o = ob.copy()
    lod_o.data = me.copy()
    lod_o.name = f'SCAN_{name}_LOD'
    bpy.context.scene.collection.objects.link(lod_o)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(lod_o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    bm.to_mesh(lod_o.data)
    bm.free()
    dm = lod_o.modifiers.new('Dec', 'DECIMATE')
    dm.ratio = lod
    with bpy.context.temp_override(active_object=lod_o, object=lod_o):
        bpy.ops.object.modifier_apply(modifier='Dec')
    print('SCAN', name, len(me.vertices), 'verts ->', len(lod_o.data.vertices), 'LOD verts', tuple(round(d, 3) for d in dims))
    return ob, lod_o


bpy.ops.wm.read_factory_settings(use_empty=True)
for nm, (fn, flip, roll, lod) in SCANS.items():
    if os.path.exists(os.path.join(SRC, fn)):
        import_scan(nm, fn, flip, roll, lod)
for im in bpy.data.images:
    im.pack()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('BUILT', OUT)
