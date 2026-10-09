"""Vegetation for the plant yard and the ponds: broadleaf trees (branching trunk + leaf cards), coconut palms (curved
ringed trunk + pinnate fronds), shrubs. Each species is built once as a mesh and placed as linked duplicates with
random rotation/scale (cheap). Leaves carry a per-face colour attribute for variation."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, Quaternion
import skpbr as P

_M = {}


def _leaf_mat(name, base, rnd=0.25, trans=0.3):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    a = nt.nodes.new('ShaderNodeAttribute')
    a.attribute_name = 'vcol'
    a.attribute_type = 'GEOMETRY'
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    mx.inputs[6].default_value = (*base, 1)
    L.new(a.outputs['Color'], mx.inputs[7])
    L.new(mx.outputs[2], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.55
    p.inputs['Subsurface Weight'].default_value = 0.0
    p.inputs['Transmission Weight'].default_value = 0.0
    p.inputs['Specular IOR Level'].default_value = 0.35
    # translucency via a mix with a translucent BSDF
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    L.new(mx.outputs[2], tr.inputs['Color'])
    ms = nt.nodes.new('ShaderNodeMixShader')
    ms.inputs[0].default_value = trans
    out = nt.nodes['Material Output']
    L.new(p.outputs[0], ms.inputs[1])
    L.new(tr.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs['Surface'])
    return m


def mats():
    if _M:
        return _M
    _M['leaf'] = _leaf_mat('VEG_Leaf', (0.09, 0.16, 0.045))
    _M['palm'] = _leaf_mat('VEG_PalmFrond', (0.16, 0.22, 0.06), trans=0.35)
    _M['bark'] = P.plain('VEG_Bark', (0.16, 0.13, 0.1), 0.85, bump=0.6, bump_scale=18)
    _M['palm_trunk'] = P.plain('VEG_PalmTrunk', (0.28, 0.24, 0.19), 0.85, bump=0.8, bump_scale=10)
    _M['shrub'] = _leaf_mat('VEG_Shrub', (0.07, 0.14, 0.04))
    return _M


def _vcol(me, rnd, lo=0.7, hi=1.25, yellow=0.15):
    attr = me.color_attributes.new('vcol', 'FLOAT_COLOR', 'CORNER')
    for poly in me.polygons:
        v = rnd.uniform(lo, hi)
        y = rnd.uniform(0, yellow)
        c = (v * (1 + y), v * (1 + y * 0.6), v * (1 - y), 1)
        for li in poly.loop_indices:
            attr.data[li].color = c


def _tube(bm, pts, r0, r1, seg=8):
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        q = d.to_track_quat('Z', 'Y')
        r = r0 + (r1 - r0) * i / max(1, n - 1)
        ring = [bm.verts.new(p + q @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), 0)))
                for k in range(seg)]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))


def tree_mesh(name='VEG_TreeMesh', h=8.0, crown=3.2, seed=1, leaves=2600):
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    M = mats()
    rnd = random.Random(seed)
    bm = bmesh.new()
    trunk = [Vector((0.15 * math.sin(i * 0.7), 0.1 * math.cos(i * 0.5), h * 0.45 * i / 6)) for i in range(7)]
    _tube(bm, trunk, 0.22, 0.12)
    tips = []
    top = trunk[-1]
    for b in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        el = rnd.uniform(0.35, 0.9)
        L = rnd.uniform(1.6, 2.8)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        start = top - Vector((0, 0, rnd.uniform(0, 1.2)))
        pts = [start + d * L * t + Vector((0, 0, 0.3 * math.sin(t * 3))) for t in (0, 0.33, 0.66, 1.0)]
        _tube(bm, pts, 0.09, 0.03, 6)
        tips.append(pts[-1])
    nb = len(bm.faces)
    me = bpy.data.meshes.new(name)
    # leaf cards scattered in ellipsoid clusters around the branch tips
    cz = h * 0.68
    for i in range(leaves):
        c = rnd.choice(tips) if rnd.random() < 0.6 else Vector((0, 0, cz))
        rad = crown * (0.45 if c.z != cz else 1.0)
        while True:
            v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
            if v.length < 1:
                break
        v = v.normalized() * (v.length ** 0.35)  # bias toward the surface
        p = c + Vector((v.x * rad, v.y * rad, v.z * rad * 0.7))
        s = rnd.uniform(0.18, 0.3)
        q = Euler((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 6.3))).to_quaternion()
        quad = [p + q @ Vector(o) for o in ((-s, 0, 0), (0, -s * 0.45, 0.02), (s, 0, 0), (0, s * 0.45, 0.02))]
        bm.faces.new([bm.verts.new(x) for x in quad])
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['bark'])
    me.materials.append(M['leaf'])
    for i, poly in enumerate(me.polygons):
        poly.material_index = 0 if i < nb else 1
        poly.use_smooth = i < nb
    _vcol(me, rnd)
    return me


def _frond(bm, base, direction, length, droop, rnd, leaflets=26):
    """Pinnate frond: arched rachis with leaflet strips on both sides."""
    d = direction.normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    pts = []
    for i in range(9):
        t = i / 8
        pts.append(base + d * length * t + Vector((0, 0, length * (0.35 * t - droop * t * t))))
    _tube(bm, pts, 0.03, 0.01, 4)
    for j in range(leaflets):
        t = 0.12 + 0.86 * j / leaflets
        i = min(7, int(t * 8))
        f = t * 8 - i
        p = pts[i].lerp(pts[i + 1], f)
        tang = (pts[i + 1] - pts[i]).normalized()
        ll = 0.7 * math.sin(math.pi * min(1, t * 1.1)) + 0.15
        for s in (-1, 1):
            out = (side * s * 0.85 + tang * 0.45 - Vector((0, 0, 0.35 + rnd.uniform(0, 0.3)))).normalized()
            w = 0.045
            a = p
            b = p + out * ll
            n = tang * w
            bm.faces.new([bm.verts.new(x) for x in (a - n, a + n, b + n * 0.2, b - n * 0.2)])


def palm_mesh(name='VEG_PalmMesh', h=11.0, seed=3, fronds=18):
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    M = mats()
    rnd = random.Random(seed)
    bm = bmesh.new()
    lean = Vector((rnd.uniform(0.6, 1.4), rnd.uniform(-0.4, 0.4), 0))
    pts = [Vector((0, 0, 0)) + lean * (t * t) + Vector((0, 0, h * t)) for t in [i / 14 for i in range(15)]]
    rings = []
    seg = 10
    for i, p in enumerate(pts):
        r = 0.2 - 0.06 * i / 14 + (0.012 if i % 2 else 0)
        rings.append([bm.verts.new(p + Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), 0)))
                      for k in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    nb = len(bm.faces)
    top = pts[-1]
    # crown shaft + coconuts
    for k in range(6):
        a = 2 * math.pi * k / 6
        c = top + Vector((0.22 * math.cos(a), 0.22 * math.sin(a), -0.35))
        r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.11)
        bmesh.ops.translate(bm, vec=c, verts=r['verts'])
    nc = len(bm.faces)
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + rnd.uniform(-0.15, 0.15)
        up = rnd.uniform(-0.2, 0.7)
        d = Vector((math.cos(a), math.sin(a), up))
        _frond(bm, top, d, rnd.uniform(3.2, 4.2), rnd.uniform(0.7, 1.1), rnd)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['palm_trunk'])
    me.materials.append(M['palm'])
    for i, poly in enumerate(me.polygons):
        poly.material_index = 0 if i < nc else 1
        poly.use_smooth = i < nb
    _vcol(me, rnd, 0.75, 1.2, 0.35)
    return me


def shrub_mesh(name='VEG_ShrubMesh', r=0.9, seed=5, leaves=700):
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    M = mats()
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(leaves):
        while True:
            v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 1)))
            if v.length < 1:
                break
        p = Vector((v.x * r, v.y * r, v.z * r * 0.8))
        s = rnd.uniform(0.08, 0.14)
        q = Euler((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 6.3))).to_quaternion()
        bm.faces.new([bm.verts.new(p + q @ Vector(o)) for o in ((-s, 0, 0), (0, -s * 0.5, 0), (s, 0, 0), (0, s * 0.5, 0))])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['shrub'])
    _vcol(me, rnd)
    return me


def place(mesh, name, loc, scale=1.0, rot=None, coll=None, rnd=None):
    rnd = rnd or random
    o = bpy.data.objects.new(name, mesh)
    (coll or bpy.context.scene.collection).objects.link(o)
    o.location = loc
    o.rotation_euler = (0, 0, rnd.uniform(0, 6.28) if rot is None else rot)
    o.scale = (scale, scale, scale * rnd.uniform(0.9, 1.1))
    return o
