"""Procedural raw Vannamei shrimp for Products (docs/BLENDER_GLB_SPEC.md §2.2: translucent grey-white segmented body,
long antennae, tail fan, slight curve). One mesh, one Principled BSDF driven by a colour attribute (no texture).
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/blender/shrimp_build.py
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'assets-src', 'models', 'shrimp.glb')
RENDERS = os.path.join(ROOT, 'docs', 'renders')
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)

BODY = (0.80, 0.82, 0.80)      # translucent grey-white flesh seen through the shell
GROOVE = (0.52, 0.56, 0.57)    # segment joints
DORSAL = (0.6, 0.63, 0.64)
TAILTIP = (0.32, 0.42, 0.5)    # bluish uropod edges (raw Vannamei)
EYE = (0.03, 0.03, 0.03)
LEG = (0.72, 0.68, 0.62)

bm = bmesh.new()
col = bm.loops.layers.color.new('Col')

def paint(faces, rgb):
    for f in faces:
        for l in f.loops: l[col] = (*rgb, 1)

def spine(s):
    """head (+X) → tail; the abdomen curls down and back."""
    L = 1.0
    th = 0.0 if s < 0.35 else (math.pi * 0.62) * ((s - 0.35) / 0.65) ** 1.6
    # integrate the curve numerically
    n = max(1, int(s * 200)); x = z = 0.0; ds = s / n if n else 0
    for i in range(n):
        si = (i + 0.5) * ds
        t = 0.0 if si < 0.35 else (math.pi * 0.62) * ((si - 0.35) / 0.65) ** 1.6
        x -= math.cos(t) * ds * L; z -= math.sin(t) * ds * L
    return Vector((0.45 + x, 0, z)), th

def radius(s):
    if s < 0.1: return 0.006 + 0.05 * (s / 0.1) ** 1.5                # rostrum
    if s < 0.36: return 0.056 + 0.034 * math.sin((s - 0.1) / 0.26 * math.pi / 2)  # carapace
    if s < 0.92:
        r = 0.09 - 0.055 * ((s - 0.36) / 0.56)
        k = ((s - 0.36) / 0.56) * 6                                      # 6 abdominal segments
        return r * (0.93 + 0.07 * min(1, abs(math.sin(k * math.pi)) * 3))
    return 0.035 - 0.02 * (s - 0.92) / 0.08

N, SEG = 140, 18
rings = []
for i in range(N + 1):
    s = i / N
    c, th = spine(s)
    r = radius(s)
    tang = Vector((-math.cos(th), 0, -math.sin(th)))
    up = Vector((-math.sin(th), 0, math.cos(th)))
    side = Vector((0, 1, 0))
    ring = []
    for j in range(SEG):
        a = 2 * math.pi * j / SEG
        ry = r * (0.82 if s > 0.36 else 0.95)        # laterally compressed abdomen
        rz = r * (1.0 + 0.12 * max(0, math.sin(a)))  # fuller back
        ring.append(bm.verts.new(c + side * (ry * math.cos(a)) + up * (rz * math.sin(a))))
    rings.append(ring)
for i in range(N):
    s = (i + 0.5) / N
    k = ((s - 0.36) / 0.56) * 6
    groove = 0.36 < s < 0.92 and (k % 1) < 0.07
    for j in range(SEG):
        f = bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[i + 1][(j + 1) % SEG], rings[i + 1][j]))
        a = 2 * math.pi * (j + 0.5) / SEG
        paint([f], GROOVE if groove else DORSAL if math.sin(a) > 0.93 else BODY)
paint([bm.faces.new(rings[0])], BODY)

def tube(a, b, r0, r1, rgb, segs=6):
    a, b = Vector(a), Vector(b); d = b - a
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r0, radius2=r1, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    for v in res['verts']: v.co = q @ v.co + (a + b) / 2
    paint({f for v in res['verts'] for f in v.link_faces}, rgb)

def curve_tube(pts, r0, r1, rgb):
    for i in range(len(pts) - 1):
        u = i / (len(pts) - 1)
        tube(pts[i], pts[i + 1], r0 + (r1 - r0) * u, r0 + (r1 - r0) * (u + 1 / (len(pts) - 1)), rgb)

head, _ = spine(0.12)
# antennae: two long whips sweeping back over the body
for sgn in (-1, 1):
    pts = []
    for i in range(24):
        u = i / 23
        pts.append(head + Vector((0.05 - 2.1 * u ** 1.1, sgn * (0.04 + 0.35 * math.sin(u * math.pi * 0.7)), 0.03 + 0.25 * math.sin(u * math.pi))))
    curve_tube(pts, 0.009, 0.004, LEG)
    # short antennules
    curve_tube([head + Vector((0.02, sgn * 0.02, 0.01)), head + Vector((0.12, sgn * 0.05, 0.03)), head + Vector((0.2, sgn * 0.04, 0.0))], 0.004, 0.002, LEG)
    # eyes on short stalks
    e = head + Vector((-0.03, sgn * 0.055, 0.03))
    res = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.022)
    for v in res['verts']: v.co += e
    paint({f for v in res['verts'] for f in v.link_faces}, EYE)
# walking legs under the carapace and swimmerets under the abdomen
for k in range(5):
    c, th = spine(0.2 + k * 0.035)
    for sgn in (-1, 1):
        curve_tube([c + Vector((0, sgn * 0.04, -0.05)), c + Vector((0.02, sgn * 0.09, -0.13)), c + Vector((0.06, sgn * 0.1, -0.2))], 0.006, 0.003, LEG)
for k in range(5):
    s = 0.42 + k * 0.1
    c, th = spine(s)
    dn = Vector((-math.sin(th), 0, math.cos(th))) * -1
    for sgn in (-1, 1):
        tube(c + dn * radius(s) * 0.8 + Vector((0, sgn * 0.03, 0)), c + dn * (radius(s) + 0.06) + Vector((0.02, sgn * 0.05, 0)), 0.008, 0.003, LEG)
# tail fan: telson + 4 uropods as thin flattened blades at the end of the curl
tail, th = spine(1.0)
tang = Vector((-math.cos(th), 0, -math.sin(th)))
for ang, length, sgn in ((0, 0.16, 0), (0.35, 0.15, 1), (0.35, 0.15, -1), (0.7, 0.13, 1), (0.7, 0.13, -1)):
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res['verts']:
        v.co = Vector((v.co.x * length, v.co.y * 0.06, v.co.z * 0.008))
    rot = tang.to_track_quat('X', 'Z')
    for v in res['verts']:
        p = v.co.copy(); p.x += length / 2
        p.rotate(__import__('mathutils').Euler((0, 0, sgn * ang)))
        v.co = tail + (rot @ p)
    faces = {f for v in res['verts'] for f in v.link_faces}
    paint(faces, TAILTIP if ang else BODY)

me = bpy.data.meshes.new('shrimp'); bm.to_mesh(me); bm.free()
me.color_attributes.active_color_name = 'Col'
shrimp = bpy.data.objects.new('shrimp', me); bpy.context.scene.collection.objects.link(shrimp)
bpy.context.view_layer.objects.active = shrimp; shrimp.select_set(True)
m = shrimp.modifiers.new('Subd', 'SUBSURF'); m.levels = m.render_levels = 1
bpy.ops.object.modifier_apply(modifier='Subd')
bpy.ops.object.shade_smooth()
# centre
bb = [Vector(c) for c in shrimp.bound_box]
shrimp.location = -(sum(bb, Vector()) / 8); bpy.ops.object.transform_apply(location=True)
size = Vector((max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)))

mat = bpy.data.materials.new('shrimp'); mat.use_nodes = True
b = mat.node_tree.nodes['Principled BSDF']
vc = mat.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
mat.node_tree.links.new(vc.outputs['Color'], b.inputs['Base Color'])
b.inputs['Metallic'].default_value = 0.0; b.inputs['Roughness'].default_value = 0.3
me.materials.append(mat)
tris = sum(len(p.vertices) - 2 for p in me.polygons)

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 32
sc.render.resolution_x, sc.render.resolution_y = 1200, 750
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.855, 0.913, 0.922, 1)
sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 2.6; sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(30))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(size) * 1.1
os.makedirs(RENDERS, exist_ok=True)
for view, d in (('side', (0, -1, 0.0)), ('34', (0.7, -0.8, 0.45)), ('top', (0.0001, 0, 1))):
    v = Vector(d).normalized() * max(size) * 3
    cam.location = v; cam.rotation_euler = (-v).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(RENDERS, f'shrimp-{view}.png'); bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(cam, do_unlink=True); bpy.data.objects.remove(sun, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT'); shrimp.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_cameras=False, export_lights=False,
                          export_yup=True, export_apply=True, export_animations=False, export_draco_mesh_compression_enable=False)
print('EXPORTED', OUT, 'tris', tris, 'size', [round(x, 2) for x in size])
