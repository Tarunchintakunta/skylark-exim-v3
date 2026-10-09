"""Export the reusable logistics GLBs from port.blend (docs/BLENDER_GLB_SPEC.md §4, §7): truck, reefer, crane, ship.
  /Applications/Blender.app/Contents/MacOS/Blender -b assets-src/blender/port.blend --python scripts/blender/port_export.py
Each model: frame 1 pose, centred on the origin, facing +X, transforms applied, one Principled BSDF whose colour comes
from a per-face colour attribute (material colours baked into it), no animation. crane.glb keeps child nodes
`trolley`, `spreader` and `cables` so code can move them. Not loaded by the default site.
"""
import bpy, math, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODELS = os.path.join(ROOT, 'assets-src', 'models')
RENDERS = os.path.join(ROOT, 'docs', 'renders')
sc = bpy.context.scene
sc.frame_set(1)

def base_color(m):
    if not m or not m.use_nodes: return (0.8, 0.8, 0.8, 1)
    b = m.node_tree.nodes.get('Principled BSDF')
    return tuple(b.inputs['Base Color'].default_value) if b else (0.8, 0.8, 0.8, 1)

def flatten(objs, name):
    """copy objs (world space) into one mesh with a 'Col' colour attribute from their material colours"""
    import bmesh
    bm = bmesh.new()
    lay = bm.loops.layers.color.new('Col')
    for o in objs:
        if o.type != 'MESH': continue
        me = o.data
        src = bmesh.new(); src.from_mesh(me)
        src.transform(o.matrix_world)
        attr = me.color_attributes.get('Col')
        for f in src.faces:
            c = base_color(me.materials[f.material_index] if me.materials else None)
            if attr is not None and me.materials and me.materials[f.material_index].name == 'Containers':
                pass  # handled below from the source attribute
            f.material_index = 0
        tmp = bpy.data.meshes.new('tmp'); src.to_mesh(tmp); src.free()
        # append tmp into bm keeping colours
        off = len(bm.verts)
        vs = [bm.verts.new(v.co) for v in tmp.vertices]
        bm.verts.ensure_lookup_table()
        src_col = tmp.color_attributes.get('Col')
        for p in tmp.polygons:
            try: f = bm.faces.new([vs[i] for i in p.vertices])
            except ValueError: continue
            mat = me.materials[p.material_index] if me.materials else None
            for k, l in enumerate(f.loops):
                if src_col is not None and mat and mat.name == 'Containers':
                    if src_col.domain == 'CORNER': l[lay] = tuple(src_col.data[p.loop_indices[k]].color)
                    else: l[lay] = tuple(src_col.data[p.vertices[k]].color)
                else:
                    l[lay] = base_color(mat)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.color_attributes.active_color_name = 'Col'
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    return o

def material(name, metal=0.15, rough=0.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    v = m.node_tree.nodes.new('ShaderNodeVertexColor'); v.layer_name = 'Col'
    m.node_tree.links.new(v.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    return m

def tree(root):
    out = [root]
    for c in root.children: out += tree(c)
    return out

def recenter(objs, pivot):
    for o in objs:
        if o.parent is None or o.parent not in objs: o.location -= pivot

def export(name, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(MODELS, f'{name}.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_cameras=False, export_lights=False,
                              export_yup=True, export_apply=True, export_animations=False, export_draco_mesh_compression_enable=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')
    print('EXPORTED', name, 'tris', tris)

def renders(name, objs):
    hide = [o for o in sc.objects if o not in objs and o.type in ('MESH',)]
    for o in hide: o.hide_render = True
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c, size = (lo + hi) / 2, max(hi - lo)
    cam = bpy.data.objects.new('RCam', bpy.data.cameras.new('RCam')); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = size * 1.1; cam.data.clip_end = size * 20
    old_cam, old_world = sc.camera, sc.world
    sc.camera = cam
    # slate background: these models are mostly white, so the light Products background would hide them
    w = bpy.data.worlds.new('RW'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.06, 0.1, 0.13, 1)
    sc.world = w
    vt = sc.view_settings.view_transform; ex = sc.view_settings.exposure
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.6
    r = sc.render; rx, ry, rp, fp, mb = r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.use_motion_blur
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.use_motion_blur = 1200, 750, 100, False
    sc.eevee.taa_render_samples = 32
    for view, d in (('side', (0, -1, 0.05)), ('34', (0.7, -0.8, 0.5)), ('top', (0.0001, 0, 1))):
        v = Vector(d).normalized() * size * 4
        cam.location = c + v; cam.rotation_euler = (-v).to_track_quat('-Z', 'Y').to_euler()
        r.filepath = os.path.join(RENDERS, f'{name}-{view}.png'); bpy.ops.render.render(write_still=True)
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.use_motion_blur = rx, ry, rp, fp, mb
    sc.view_settings.view_transform = vt; sc.view_settings.exposure = ex
    sc.camera, sc.world = old_cam, old_world
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in hide: o.hide_render = False

# strip animation so exports and renders use the frame-1 pose as static geometry
for o in sc.objects: o.animation_data_clear()
sea = bpy.data.objects.get('Sea'); wake = bpy.data.objects.get('Wake')
for o in (sea, wake):
    if o: o.hide_render = True

D = bpy.data.objects
# truck: tractor + chassis + wheels + glass (the reefer is its own model)
truck_parts = [o for o in tree(D['Truck']) if o.type == 'MESH']
t = flatten(truck_parts, 'truck'); t.data.materials.append(material('truck', 0.1, 0.4))
t.location -= Vector((D['Truck'].location.x, D['Truck'].location.y, D['Truck'].location.z)); bpy.ops.object.select_all(action='DESELECT')
t.select_set(True); bpy.context.view_layer.objects.active = t; bpy.ops.object.transform_apply(location=True)
# reefer
rf = flatten([D['Reefer'], D['ReeferUnit']], 'reefer'); rf.data.materials.append(material('reefer', 0.15, 0.38))
bpy.context.view_layer.objects.active = rf
rf.location = (0, 0, 0)
# ship: hull, boot-top, accommodation, stacks, lashing
ship_parts = [o for o in tree(D['Ship']) if o.type == 'MESH' and o.name != 'Wake']
sh = flatten(ship_parts, 'ship'); sh.data.materials.append(material('ship', 0.15, 0.5))
# crane 2 at frame 1: frame + accent → `crane`; trolley/headblock, spreader, cables keep their own nodes
c2 = D['Crane_2']
frame = flatten([D['Crane_2_Frame'], D['Crane_2_Accent']], 'crane'); cm = material('crane', 0.2, 0.45); frame.data.materials.append(cm)
trolley = flatten([D['Crane_2_Trolley'], D['Crane_2_Headblock']], 'trolley'); trolley.data.materials.append(cm)
spreader = flatten([D['Crane_2_Spreader']], 'spreader'); spreader.data.materials.append(cm)
cables = flatten([D[f'Crane_2_Cable{k}'] for k in range(4)], 'cables'); cables.data.materials.append(cm)
for o in (trolley, spreader, cables): o.parent = frame

def center_xy(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    cx = (min(p.x for p in bb) + max(p.x for p in bb)) / 2; cy = (min(p.y for p in bb) + max(p.y for p in bb)) / 2
    return Vector((cx, cy, min(p.z for p in bb)))
for o in (t, rf, sh, frame):
    p = center_xy(o)
    for ch in [o] + list(o.children):
        if ch.data:
            ch.data.transform(__import__('mathutils').Matrix.Translation(-(p if ch is o else p)))
    o.location = (0, 0, 0)
# the crane's long axis is its boom (Y in the scene): turn it so the boom points +X like the other models
import mathutils
for o in [frame] + list(frame.children):
    o.data.transform(mathutils.Matrix.Rotation(-math.pi / 2, 4, 'Z'))

for name, objs in (('truck', [t]), ('reefer', [rf]), ('ship', [sh]), ('crane', [frame, trolley, spreader, cables])):
    # hide the original scene meshes while rendering this model
    export(name, objs)
    renders(name, objs)
