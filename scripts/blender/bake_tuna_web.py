"""Web tuna for the Products stage (public/models/tuna.glb, #141): the yellowfin photogrammetry scan (CC BY 4.0,
ffish.asia / floraZia.com) as a clean, light model.

The scan's fins are ragged and stringy, so the body is voxel-remeshed coarse enough to drop them (and the loose specks),
its scanned colour is baked into one texture, and clean solid fins are modelled back on: lunate tail, long sickle
pectorals, first and second dorsal, anal fin and the yellow finlets. Then compress with scripts/optimize-glb.sh.
  Blender -b assets-src/blender/fish_scans.blend --python scripts/blender/bake_tuna_web.py -- out.glb 6000 1024
fish_scans.blend (SCAN_Tuna: 1 m long, head +X, back +Z) is built by blender/prep_scans.py on the Blender lane (#100).
"""
import bpy, bmesh, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index('--') + 1:]
out, faces, res = a[0], int(a[1]), int(a[2])
hi = bpy.data.objects['SCAN_Tuna']
for o in list(bpy.data.objects):
    if o is not hi:
        bpy.data.objects.remove(o)
sc = bpy.context.scene


def apply(o, mod):
    with bpy.context.temp_override(active_object=o, object=o):
        bpy.ops.object.modifier_apply(modifier=mod.name)


# body: a 1 cm voxel remesh closes the shells and drops the thin fins; keep only the largest piece (no specks)
body = hi.copy(); body.data = hi.data.copy(); body.name = 'Tuna'; sc.collection.objects.link(body)
r = body.modifiers.new('R', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.01
apply(body, r)
bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table()
seen, parts = set(), []
for f0 in bm.faces:
    if f0.index in seen:
        continue
    stack, part = [f0], []
    seen.add(f0.index)
    while stack:
        f = stack.pop(); part.append(f)
        for e in f.edges:
            for g in e.link_faces:
                if g.index not in seen:
                    seen.add(g.index); stack.append(g)
    parts.append(part)
parts.sort(key=len)
bmesh.ops.delete(bm, geom=[f for p in parts[:-1] for f in p], context='FACES')
bm.to_mesh(body.data); bm.free()
sm = body.modifiers.new('S', 'SMOOTH'); sm.factor = 0.5; sm.iterations = 4
apply(body, sm)
d = body.modifiers.new('D', 'DECIMATE'); d.ratio = min(1.0, faces / len(body.data.polygons))
apply(body, d)
print('BODY', len(body.data.polygons))

# bake the scan colour onto the body
body.data.materials.clear()
while len(body.data.uv_layers):
    body.data.uv_layers.remove(body.data.uv_layers[0])
body.data.uv_layers.new(name='UV')
for o in sc.objects:
    o.select_set(o is body)
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
img = bpy.data.images.new('tuna_albedo', res, res)
m = bpy.data.materials.new('tuna'); m.use_nodes = True
nt = m.node_tree; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
bsdf = nt.nodes['Principled BSDF']; nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 0.35
nt.nodes.active = tex
body.data.materials.append(m)
for p in body.data.polygons:
    p.use_smooth = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.device = 'CPU'
hi.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
b = sc.render.bake; b.use_selected_to_active = True; b.cage_extrusion = 0.02; b.max_ray_distance = 0.04; b.margin = 8
b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True
bpy.ops.object.bake(type='EMIT')
bpy.data.objects.remove(hi)

# fins, rooted on the body surface found by ray casts
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def surf(x, z_dir, y=0.0):
    """z of the body surface above (z_dir=1) or below (-1) the axis at x."""
    hit = bvh.ray_cast(Vector((x, y, z_dir * 0.5)), Vector((0, 0, -z_dir)))
    return hit[0].z if hit[0] else 0.0


def side(x, z, s):
    hit = bvh.ray_cast(Vector((x, s * 0.5, z)), Vector((0, -s, 0)))
    return hit[0].y if hit[0] else s * 0.05


def mat(name, color, rough=0.45):
    mm = bpy.data.materials.new(name); mm.use_nodes = True
    p = mm.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    return mm


DARK = mat('fin_dark', (0.07, 0.08, 0.10), 0.4)
YELLOW = mat('fin_yellow', (0.78, 0.56, 0.06), 0.45)
fins = []


def fin(name, pts, material, thick=0.0035):
    """pts: 3D outline (root edge first); filled, given thickness, smooth-shaded."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(material)
    so = o.modifiers.new('T', 'SOLIDIFY'); so.thickness = thick; so.offset = 0
    apply(o, so)
    for p in me.polygons:
        p.use_smooth = True
    fins.append(o)


def arc(p0, p1, bulge, n=6):
    """points from p0 to p1 bowed by `bulge` (in the fin plane, perpendicular to the chord)."""
    p0, p1 = Vector(p0), Vector(p1)
    ch = p1 - p0
    nrm = Vector((-ch.z, 0, ch.x)).normalized() if abs(ch.y) < 1e-6 else Vector((-ch.y, ch.x, 0)).normalized()
    return [p0.lerp(p1, t) + nrm * bulge * math.sin(math.pi * t) for t in (i / n for i in range(1, n))]


yc = 0.012   # the scan's midline drifts slightly to +Y toward the tail
# lunate tail: two swept lobes from the peduncle
xt = -0.36
zt = (surf(xt, 1, yc) + surf(xt, -1, yc)) / 2
top = Vector((-0.505, yc, zt + 0.15)); bot = Vector((-0.505, yc, zt - 0.15))
root_t = Vector((xt, yc, zt + 0.016)); root_b = Vector((xt, yc, zt - 0.016))
notch = Vector((-0.445, yc, zt))
tail = [root_b, root_t] + arc(root_t, top, -0.025) + [top] + arc(top, notch, 0.012, 4) + [notch] \
    + arc(notch, bot, 0.012, 4) + [bot] + arc(bot, root_b, -0.025)
fin('Fin_Tail', tail, DARK, 0.004)

# pectorals: long sickles lying back along each flank, a little off the body
for s in (-1, 1):
    x0, z0 = 0.2, -0.005
    y0 = side(x0, z0, s) + s * 0.004
    tip = Vector((-0.03, y0 + s * 0.035, z0 - 0.03))
    up = Vector((x0, y0, z0 + 0.018)); lo_ = Vector((x0 - 0.035, y0, z0 - 0.012))
    fin(f'Fin_Pec_{s}', [lo_, up] + arc(up, tip, 0.012) + [tip] + arc(tip, lo_, -0.01), DARK, 0.003)

# first dorsal (low, dark) and the tall yellow second dorsal and anal fins
def dorsal(name, xa, xb, h, sweep, sgn, material):
    za, zb = surf(xa, sgn, yc) - sgn * 0.006, surf(xb, sgn, yc) - sgn * 0.006
    a_, b_ = Vector((xa, yc, za)), Vector((xb, yc, zb))
    tip = Vector((xb - sweep, yc, zb + sgn * h))
    fin(name, [b_, a_] + arc(a_, tip, sgn * 0.01) + [tip] + arc(tip, b_, -sgn * 0.006, 4), material)


dorsal('Fin_Dorsal1', 0.2, 0.1, 0.035, 0.03, 1, DARK)
dorsal('Fin_Dorsal2', -0.06, -0.12, 0.075, 0.05, 1, YELLOW)
dorsal('Fin_Anal', -0.07, -0.13, 0.07, 0.05, -1, YELLOW)

# finlets: small yellow flags along the back and belly to the peduncle
for sgn in (1, -1):
    for i in range(8):
        x = -0.15 - i * 0.026
        z = surf(x, sgn, yc) - sgn * 0.003
        fin(f'Finlet_{sgn}_{i}', [Vector((x + 0.012, yc, z)), Vector((x - 0.006, yc, z)),
                                    Vector((x - 0.016, yc, z + sgn * 0.016))], YELLOW, 0.002)

# one mesh, ready for scripts/optimize-glb.sh
for o in sc.objects:
    o.select_set(o in fins or o is body)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.scale = (2.18,) * 3
print('FACES', len(body.data.polygons))
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_image_quality=80,
                          export_apply=True, export_animations=False)
