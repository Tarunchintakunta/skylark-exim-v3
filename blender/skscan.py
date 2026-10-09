"""Photoreal CC0 scans (assets-src/cc0/fish/) reduced to render-friendly meshes.
build(out): imports the glTF scans, drops the colour-checker cube, joins, decimates, scales to life size, length along +X,
centred on the origin, and saves them as SCAN_* meshes in assets-src/blender/scans.blend.
mesh(name): appends a SCAN_* mesh from scans.blend (None if it is not built).
Usage: Blender -b --python blender/skscan.py"""
import os
import sys
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from skpbr import CC0  # noqa: E402
FISH = os.path.join(CC0, 'fish')
OUT = os.path.join(REPO, 'assets-src', 'blender', 'scans.blend')
# name: (file, life-size length in metres, target faces)
SCANS = {'SCAN_Shrimp': ('shrimp-green-tiger-ffish.glb', 0.13, 60000)}


def _import(file, length, faces):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(FISH, file))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = []
    for o in new:
        if o.type != 'MESH':
            continue
        if len(o.data.polygons) <= 12 and any('Material.001' in m.name for m in o.data.materials if m):
            continue                      # colour-checker cube
        meshes.append(o)
    bpy.context.view_layer.update()
    for o in meshes:                      # bake transforms, unparent
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix()
    names = [x.name for x in new]
    ctx = {'object': meshes[0], 'active_object': meshes[0], 'selected_editable_objects': meshes,
           'selected_objects': meshes}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    o = meshes[0]
    for nm in names:
        x = bpy.data.objects.get(nm)
        if x is not None and x != o:
            bpy.data.objects.remove(x, do_unlink=True)
    n = len(o.data.polygons)
    if n > faces:
        d = o.modifiers.new('dec', 'DECIMATE')
        d.ratio = faces / n
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier='dec')
    me = o.data
    vs = [v.co for v in me.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    size = hi - lo
    axis = max(range(3), key=lambda i: size[i])
    m = Matrix.Translation(-(lo + hi) / 2)
    if axis == 1:
        m = Matrix.Rotation(-1.5708, 4, 'Z') @ m
    elif axis == 2:
        m = Matrix.Rotation(1.5708, 4, 'Y') @ m
    me.transform(Matrix.Scale(length / size[axis], 4) @ m)
    for p in me.polygons:
        p.use_smooth = True
    for m in me.materials:            # glTF 'unlit' scan materials -> lit, wet PBR
        if m and m.use_nodes:
            _relight(m)
    return o


def _relight(m):
    nt = m.node_tree
    tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None)
    for n in [n for n in nt.nodes if tex is None or n.name != tex.name]:
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs['Surface'])
    bs.inputs['Roughness'].default_value = 0.32
    bs.inputs['Coat Weight'].default_value = 0.55       # wet shell
    bs.inputs['Coat Roughness'].default_value = 0.08
    bs.inputs['Subsurface Weight'].default_value = 0.15
    bs.inputs['Subsurface Radius'].default_value = (0.004, 0.002, 0.0015)
    if tex is not None:
        nt.links.new(tex.outputs[0], bs.inputs['Base Color'])
        nt.links.new(tex.outputs[1], bs.inputs['Alpha'])   # the scan is stacked alpha-mapped depth slices
    m.surface_render_method = 'DITHERED'


def build(out=OUT):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, (file, length, faces) in SCANS.items():
        o = _import(file, length, faces)
        o.name = o.data.name = name
        o.data.use_fake_user = True
    for im in bpy.data.images:
        im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('OUT scans', out, {n: len(bpy.data.meshes[n].polygons) for n in SCANS})


# the shared library's prepared scans (feat/100 prep_scans.py): 1 m long, head +X; the prawn comes in back-down
LIB = os.path.join(os.path.dirname(CC0), 'blender', 'fish_scans.blend')
LIB_MAP = {'SCAN_Shrimp': ('SCAN_Prawn_LOD', 0.13, 3.14159265)}   # our name: (library mesh, length m, roll to belly-down)


def mesh(name):
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    if name in LIB_MAP and os.path.exists(LIB):
        src_name, length, roll = LIB_MAP[name]
        with bpy.data.libraries.load(LIB, link=False) as (src, dst):
            dst.meshes = [src_name] if src_name in src.meshes else []
        me = bpy.data.meshes.get(src_name)
        if me is not None:
            me = me.copy()
            me.name = name
            me.transform(Matrix.Rotation(roll, 4, 'X') @ Matrix.Scale(length, 4))
            return me
    if not os.path.exists(OUT):
        return None
    with bpy.data.libraries.load(OUT, link=False) as (src, dst):
        dst.meshes = [name] if name in src.meshes else []
    return bpy.data.meshes.get(name)


if __name__ == '__main__':
    build()
