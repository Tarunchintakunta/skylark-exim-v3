"""Real-proportion people for the Skylark scenes, built from Blender's CC0 "Human Base Meshes" bundle (v1.4.1).

build_masters(): appends the realistic male/female base meshes, applies one multires level, rigs them with a simple
22-bone armature (automatic weights), and grows clothing shells from the body surface by region (so clothes deform with
the same weights). One joined mesh per (gender, outfit) is saved to assets-src/blender/humans.blend.
person(): in a scene, makes one armature object + one mesh object that shares the outfit mesh (cheap), with per-object
colour variation. Poses are given as joint angles in degrees; IK targets let hands hold trolley handles, crates, tables.
Character faces -Y in its local space (front), +X is its left. Units metres, feet at z=0.
"""
import math
import os
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree

CC0 = os.environ.get('SKY_CC0', '/Users/tarunchintakunta/Desktop/skylark/skylark-exim-v3/assets-src/cc0')
BUNDLE = CC0 + '/humans/x/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'

# joint guesses for the realistic male (height 1.684), x = |offset from centre|, y filled from the mesh
JOINTS_M = {
    'hips': (0, 0.96), 'spine': (0, 1.10), 'chest': (0, 1.28), 'neck': (0, 1.45), 'head': (0, 1.53), 'head_end': (0, 1.70),
    'shoulder': (0.04, 1.40), 'upperarm': (0.165, 1.385), 'forearm': (0.295, 1.075), 'hand': (0.385, 0.86), 'hand_end': (0.43, 0.72),
    'thigh': (0.095, 0.90), 'shin': (0.135, 0.49), 'foot': (0.172, 0.085), 'toe': (0.18, 0.02),
}

OUTFITS = {
    # name: list of (piece, material key)
    'plant': ['jacket', 'trousers', 'boots', 'gloves', 'haircap', 'mask', 'apron'],
    'plant_coat': ['labcoat', 'trousers', 'boots', 'gloves', 'haircap', 'mask'],
    'coldstore': ['parka', 'trousers', 'boots', 'gloves', 'haircap', 'mask'],
    'driver': ['shirt', 'trousers_dark', 'shoes', 'hair', 'vest'],
    'farm': ['shirt_farm', 'shorts', 'hair', 'cap'],
    'farm_long': ['shirt_farm', 'trousers_rolled', 'hair', 'gloves_rubber'],
    'guard': ['shirt', 'trousers_dark', 'shoes', 'hair', 'cap'],
    'farm_gloves': ['shirt_farm', 'trousers_rolled', 'hair', 'gloves'],
}


# ------------------------------------------------------------------ materials
def _mat(name, color, rough=0.6, sss=0.0, coat=0.0, bump=0.0, sheen=0.0, normal_tex=None, tex_scale=30.0, metal=0.0,
         emission=None, estr=0.0, rand=0.0, hue_rand=0.0, wrinkle=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    L = nt.links
    col = p.inputs['Base Color']
    if rand > 0:  # per-object variation (Object Info random)
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        hsv = nt.nodes.new('ShaderNodeHueSaturation')
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = 1 - rand
        mr.inputs['To Max'].default_value = 1 + rand
        L.new(oi.outputs['Random'], mr.inputs['Value'])
        L.new(mr.outputs[0], hsv.inputs['Value'])
        hsv.inputs['Color'].default_value = (*color, 1)
        if hue_rand:
            hr = nt.nodes.new('ShaderNodeMapRange')
            hr.inputs['To Min'].default_value = 0.5 - hue_rand
            hr.inputs['To Max'].default_value = 0.5 + hue_rand
            L.new(oi.outputs['Random'], hr.inputs['Value'])
            L.new(hr.outputs[0], hsv.inputs['Hue'])
        L.new(hsv.outputs[0], col)
    else:
        col.default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
        p.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.2)
        p.inputs['Subsurface Scale'].default_value = 0.01
    if coat:
        p.inputs['Coat Weight'].default_value = coat
    if sheen:
        p.inputs['Sheen Weight'].default_value = sheen
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = estr
    nrm_in = None
    if normal_tex and os.path.exists(normal_tex):
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (tex_scale, tex_scale, tex_scale)
        L.new(tc.outputs['UV'], mp.inputs['Vector'])
        im = nt.nodes.new('ShaderNodeTexImage')
        im.image = bpy.data.images.load(normal_tex, check_existing=True)
        im.image.colorspace_settings.name = 'Non-Color'
        L.new(mp.outputs[0], im.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = 0.6
        L.new(im.outputs['Color'], nm.inputs['Color'])
        nrm_in = nm.outputs[0]
    if bump:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 60
        nz.inputs['Detail'].default_value = 8
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = 0.004
        L.new(nz.outputs['Fac'], b.inputs['Height'])
        if nrm_in:
            L.new(nrm_in, b.inputs['Normal'])
        nrm_in = b.outputs[0]
    if wrinkle:
        # cloth creases: noise stretched along the limbs (object Z) + a little warp
        tc2 = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (14.0, 14.0, 3.5)
        L.new(tc2.outputs['Object'], mp.inputs['Vector'])
        nz2 = nt.nodes.new('ShaderNodeTexNoise')
        nz2.inputs['Scale'].default_value = 1.6
        nz2.inputs['Detail'].default_value = 3
        nz2.inputs['Distortion'].default_value = 0.6
        L.new(mp.outputs[0], nz2.inputs['Vector'])
        b2 = nt.nodes.new('ShaderNodeBump')
        b2.inputs['Strength'].default_value = wrinkle
        b2.inputs['Distance'].default_value = 0.012
        L.new(nz2.outputs['Fac'], b2.inputs['Height'])
        if nrm_in:
            L.new(nrm_in, b2.inputs['Normal'])
        nrm_in = b2.outputs[0]
        ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
        ao.inputs['Distance'].default_value = 0.06
        cm = nt.nodes.new('ShaderNodeMix')
        cm.data_type = 'RGBA'
        cm.blend_type = 'MULTIPLY'
        inv = nt.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        L.new(ao.outputs['AO'], inv.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = 0.6
        L.new(inv.outputs[0], mul.inputs[0])
        L.new(mul.outputs[0], cm.inputs[0])
        src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
        if src is not None:
            L.new(src, cm.inputs[6])
        else:
            cm.inputs[6].default_value = p.inputs['Base Color'].default_value
        cm.inputs[7].default_value = (0.55, 0.55, 0.55, 1)
        L.new(cm.outputs[2], p.inputs['Base Color'])
    if nrm_in:
        L.new(nrm_in, p.inputs['Normal'])
    return m


def _eye_mat():
    m = bpy.data.materials.get('HUM_Eye')
    if m:
        return m
    m = _mat('HUM_Eye', (0.7, 0.68, 0.64), 0.06, coat=1.0)
    nt = m.node_tree
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'iris'
    at.attribute_type = 'GEOMETRY'
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    nt.links.new(at.outputs['Fac'], mx.inputs[0])
    mx.inputs[6].default_value = (0.70, 0.67, 0.62, 1)
    mx.inputs[7].default_value = (0.025, 0.016, 0.012, 1)
    nt.links.new(mx.outputs[2], nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


def _stache_mat():
    """Moustache on about half the men (Object Info random > 0.45), hidden on the rest."""
    m = bpy.data.materials.get('HUM_Stache')
    if m:
        return m
    m = _mat('HUM_Stache', (0.02, 0.016, 0.014), 0.6, bump=0.25)
    nt = m.node_tree
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.45
    nt.links.new(oi.outputs['Random'], gt.inputs[0])
    nt.links.new(gt.outputs[0], nt.nodes['Principled BSDF'].inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    return m


def mats():
    fab = CC0 + '/tex/Fabric030/Fabric030_2K-JPG_NormalGL.jpg'
    fab2 = CC0 + '/tex/Fabric061/Fabric061_2K-JPG_NormalGL.jpg'
    return {
        'skin': _mat('HUM_Skin', (0.42, 0.25, 0.17), 0.45, sss=0.15, bump=0.05, rand=0.25),
        'eye': _eye_mat(),
        'white_cotton': _mat('HUM_WhiteCotton', (0.80, 0.81, 0.80), 0.85, sheen=0.3, bump=0.12, rand=0.04, wrinkle=0.45),
        'white_pvc': _mat('HUM_WhitePVC', (0.84, 0.86, 0.86), 0.32, coat=0.3, bump=0.02),
        'boot': _mat('HUM_WhiteBoot', (0.80, 0.81, 0.79), 0.35, coat=0.2, bump=0.02),
        'nitrile_blue': _mat('HUM_NitrileBlue', (0.16, 0.33, 0.62), 0.38, coat=0.25, rand=0.06),
        'cap_white': _mat('HUM_CapNonwoven', (0.84, 0.85, 0.86), 0.95, sheen=0.4, bump=0.25),
        'mask_blue': _mat('HUM_MaskBlue', (0.55, 0.70, 0.80), 0.9, sheen=0.3, bump=0.15),
        'parka': _mat('HUM_ParkaNavy', (0.10, 0.14, 0.22), 0.55, coat=0.1, bump=0.12, wrinkle=0.45),
        'shirt_blue': _mat('HUM_ShirtBlue', (0.22, 0.30, 0.42), 0.8, sheen=0.2, bump=0.12, rand=0.15, wrinkle=0.45),
        'trousers_dark': _mat('HUM_TrouserDark', (0.08, 0.08, 0.09), 0.75, bump=0.1, rand=0.2, wrinkle=0.45),
        'shoe': _mat('HUM_Shoe', (0.05, 0.045, 0.04), 0.45, coat=0.2),
        'stache': _stache_mat(),
        'hair': _mat('HUM_Hair', (0.025, 0.02, 0.018), 0.5, bump=0.4, rand=0.2),
        'hivis': _mat('HUM_HiVis', (0.75, 0.85, 0.08), 0.6, emission=(0.6, 0.7, 0.05), estr=0.15, bump=0.12, wrinkle=0.45),
        'shirt_farm': _mat('HUM_ShirtFarm', (0.34, 0.27, 0.22), 0.85, sheen=0.2, bump=0.12, rand=0.35, hue_rand=0.5, wrinkle=0.45),
        'shorts': _mat('HUM_Shorts', (0.20, 0.22, 0.25), 0.85, bump=0.1, rand=0.3, wrinkle=0.45),
        'cap_cloth': _mat('HUM_CapCloth', (0.55, 0.52, 0.45), 0.85, rand=0.3),
        'rubber_glove': _mat('HUM_RubberGlove', (0.55, 0.42, 0.12), 0.35, coat=0.3),
    }


# ------------------------------------------------------------------ master build
def _append_body(gender):
    nm = 'GEO-body_%s_realistic' % gender
    with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(nm)]
    objs = [o for o in dst.objects if o]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    body = [o for o in objs if o.name.startswith(nm) and 'eye' not in o.name][0]
    eyes = [o for o in objs if 'eye' in o.name]
    return body, eyes


def _apply_multires(o, level=1):
    for m in o.modifiers:
        if m.type == 'MULTIRES':
            m.levels = level
            m.render_levels = level
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)


def _normalize(body, eyes):
    """Feet at z=0, centred on x/y; eyes unparented and baked into world space."""
    for e in eyes:
        mw = e.matrix_world.copy()
        e.parent = None
        e.matrix_world = mw
    vs = [body.matrix_world @ v.co for v in body.data.vertices]
    cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
    cy = sum(v.y for v in vs if v.z > 1.0) / max(1, len([v for v in vs if v.z > 1.0]))
    z0 = min(v.z for v in vs)
    off = Vector((-cx, -cy, -z0))
    for o in [body] + eyes:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(Matrix.Translation(off))
    return max(v.z for v in vs) - z0


def _joint_y(body, x, z, r=0.05):
    pts = [v.co for v in body.data.vertices if (v.co.x - x) ** 2 + (v.co.z - z) ** 2 < r * r]
    if not pts:
        return 0.0
    return (min(p.y for p in pts) + max(p.y for p in pts)) / 2


def _build_armature(body, height, name):
    k = height / 1.684
    J = {n: (x * k, z * k) for n, (x, z) in JOINTS_M.items()}
    arm = bpy.data.armatures.new(name)
    ao = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones

    def P(j, side=0):
        x, z = J[j]
        x *= side if side else 0
        return Vector((x, _joint_y(body, x, z), z))

    def bone(n, h, t, parent=None, connect=False):
        b = eb.new(n)
        b.head, b.tail = h, t
        b.roll = 0
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    bone('hips', P('hips') + Vector((0, 0, -0.06)), P('spine'))
    bone('spine', P('spine'), P('chest'), 'hips', True)
    bone('chest', P('chest'), P('neck'), 'spine', True)
    bone('neck', P('neck'), P('head'), 'chest', True)
    bone('head', P('head'), P('head_end'), 'neck', True)
    for s, sx in (('L', 1), ('R', -1)):
        bone('shoulder.' + s, P('shoulder', sx) + Vector((0, 0, 0.0)), P('upperarm', sx), 'chest')
        bone('upperarm.' + s, P('upperarm', sx), P('forearm', sx), 'shoulder.' + s, True)
        bone('forearm.' + s, P('forearm', sx), P('hand', sx), 'upperarm.' + s, True)
        bone('hand.' + s, P('hand', sx), P('hand_end', sx), 'forearm.' + s, True)
        bone('thigh.' + s, P('thigh', sx), P('shin', sx), 'hips')
        bone('shin.' + s, P('shin', sx), P('foot', sx), 'thigh.' + s, True)
        f = P('foot', sx)
        bone('foot.' + s, f, Vector((f.x, f.y - 0.13 * k, 0.02)), 'shin.' + s, True)
    # roll so every bone's local X matches armature X (lateral) -> joint angles are intuitive
    for b in eb:
        b.align_roll(Vector((0, 0, 1)) if abs((b.tail - b.head).normalized().z) < 0.7 else Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    return ao


def _skin(body, eyes, ao, weights_from=None):
    """Bone-heat weights; the female base mesh shares the male topology, so it reuses the male weights by index
    (bone heat fails on it)."""
    if weights_from is None:
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        ao.select_set(True)
        bpy.context.view_layer.objects.active = ao
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    else:
        src = weights_from
        assert len(src.data.vertices) == len(body.data.vertices)
        for vg in src.vertex_groups:
            body.vertex_groups.new(name=vg.name)
        for v in src.data.vertices:
            for g in v.groups:
                body.vertex_groups[src.vertex_groups[g.group].name].add([v.index], g.weight, 'REPLACE')
        body.parent = ao
        md = body.modifiers.new('Armature', 'ARMATURE')
        md.object = ao
    for e in eyes:
        vg = e.vertex_groups.new(name='head')
        vg.add(range(len(e.data.vertices)), 1.0, 'REPLACE')


def _region(body, gender, piece, k):
    """Vertex mask for a clothing piece, from the rest (A-pose) surface. k = height scale."""
    out = []
    for v in body.data.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z / k
        ax = abs(x) / k
        n = v.normal
        arm = ax > 0.19 and z < 1.40 and not (z < 1.0 and ax < 0.24)
        # distance along the arm from the shoulder joint (elbow ~0.34, wrist ~0.57): cuts square to the limb
        sa = ((ax - 0.165) * 0.387 + (z - 1.385) * -0.922) if arm or ax > 0.25 else -1.0
        hand = sa > 0.555
        sel = False
        if piece in ('jacket', 'parka', 'shirt', 'shirt_farm'):
            top = 1.455
            sel = 0.80 < z < top and sa < SLEEVE[piece]
            if piece == 'parka':
                sel = 0.74 < z < 1.47 and sa < SLEEVE[piece]
        elif piece == 'labcoat':
            sel = 0.50 < z < 1.455 and sa < SLEEVE[piece]
        elif piece in ('trousers', 'trousers_dark'):
            sel = 0.08 < z < 1.02 and not arm and not hand
        elif piece == 'trousers_rolled':
            sel = 0.32 < z < 1.02 and not arm and not hand
        elif piece == 'shorts':
            sel = 0.50 < z < 1.02 and not arm and not hand
        elif piece == 'boots':
            sel = z < 0.34
        elif piece == 'shoes':
            sel = z < 0.105
        elif piece in ('gloves', 'gloves_rubber'):
            sel = sa > (0.50 if piece == 'gloves' else 0.44)
        elif piece == 'haircap':
            sel = (z > 1.60) or (z > 1.49 and n.y > 0.1 and ax < 0.10) or (z > 1.545 and ax > 0.055 and n.y > -0.3)
            sel = sel and ax < 0.125
        elif piece in ('hair', 'cap'):
            sel = ((z > 1.60) or (z > 1.52 and n.y > 0.3) or (z > 1.56 and ax > 0.06 and n.y > -0.2)) and ax < 0.12
            sel = sel and not (z < 1.605 and ax > 0.07)        # ears stay bare
            if piece == 'cap':
                sel = z > 1.60 and ax < 0.12
        elif piece == 'mask':
            sel = 1.462 < z < 1.552 and ax < 0.078 and n.y < -0.25
        elif piece == 'stache':
            sel = STACHE[0] < z < STACHE[1] and ax < STACHE[2] and n.y < -0.12
        elif piece == 'vest':
            sel = 0.93 < z < 1.43 and ax < 0.17 and not arm
        out.append(sel)
    return out


STACHE = (1.505, 1.517, 0.030)       # upper lip band (z lo, z hi, half width) on the rest mesh
SLEEVE = {'jacket': 0.545, 'parka': 0.55, 'labcoat': 0.535, 'shirt': 0.17, 'shirt_farm': 0.31}
CUFF = ('shirt_farm', 'trousers_rolled', 'jacket', 'labcoat', 'parka', 'haircap', 'shirt', 'trousers', 'trousers_dark',
        'shorts')
THICK = {'jacket': 0.028, 'parka': 0.05, 'shirt': 0.03, 'shirt_farm': 0.03, 'labcoat': 0.032, 'trousers': 0.02,
         'trousers_dark': 0.016, 'trousers_rolled': 0.016, 'shorts': 0.018, 'boots': 0.018, 'shoes': 0.008,
         'gloves': 0.0016, 'gloves_rubber': 0.003, 'haircap': 0.018, 'hair': 0.008, 'cap': 0.014, 'mask': 0.008,
         'vest': 0.04, 'stache': 0.0012}
PMAT = {'jacket': 'white_cotton', 'labcoat': 'white_cotton', 'parka': 'parka', 'shirt': 'shirt_blue',
        'shirt_farm': 'shirt_farm', 'trousers': 'white_cotton', 'trousers_dark': 'trousers_dark',
        'trousers_rolled': 'trousers_dark', 'shorts': 'shorts', 'boots': 'boot', 'shoes': 'shoe',
        'gloves': 'nitrile_blue', 'gloves_rubber': 'rubber_glove', 'haircap': 'cap_white', 'hair': 'hair',
        'cap': 'cap_cloth', 'mask': 'mask_blue', 'vest': 'hivis', 'apron': 'white_pvc', 'stache': 'stache'}


KH = 1.0


def _shell(body, piece, mask, M):
    """Copy of the body faces inside mask, pushed out along normals (+ fabric folds), solidified."""
    me = body.data.copy()
    o = bpy.data.objects.new('%s_%s' % (body.name, piece), me)
    bpy.context.scene.collection.objects.link(o)
    for vg in body.vertex_groups:
        o.vertex_groups.new(name=vg.name)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if not all(mask[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    for _ in range(3):                      # drop one-face slivers and tags hanging off the border
        thin = [f for f in bm.faces if sum(1 for e in f.edges if e.is_boundary) >= 2]
        if not thin:
            break
        bmesh.ops.delete(bm, geom=thin, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    t = THICK[piece]
    loose_cloth = piece in ('jacket', 'parka', 'shirt', 'shirt_farm', 'labcoat', 'trousers', 'trousers_dark',
                            'trousers_rolled', 'shorts', 'vest', 'boots')
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    bnd = [v for v in bm.verts if v.is_boundary]
    for _ in range(8):                      # straighten the hem line (1D smoothing along the border)
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items():
            v.co = c
    for v in bnd:
        hit, nrm, _i, _d = bvh.find_nearest(v.co)
        if hit is not None:
            v.co = hit
    # rings from the border: 0 at the hem
    ring = {v: 0 for v in bnd}
    front = list(bnd)
    for r in range(1, 5):
        nxt = []
        for v in front:
            for e in v.link_edges:
                w = e.other_vert(v)
                if w not in ring:
                    ring[w] = r
                    nxt.append(w)
        front = nxt
    if loose_cloth:
        # cloth drapes over the anatomy: push out, then relax (removes muscle detail); hems hug the body
        hem = {'labcoat': 0.022, 'parka': 0.022, 'vest': 0.06}.get(piece, 0.012)   # vest sits over the shirt
        for v in bm.verts:
            v.co += v.normal * (hem if v.is_boundary else t * 1.6)
        inner = [v for v in bm.verts if not v.is_boundary]
        for it in range(4):
            for _ in range(20):
                bmesh.ops.smooth_vert(bm, verts=inner, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            # smoothing shrinks the shell into the body: re-inflate to keep clearance
            for v in inner:
                hit, nrm, _i, d = bvh.find_nearest(v.co)
                clr = 0.018 if piece == 'boots' else 0.007      # boots: no toes showing through
                if hit is not None and d < clr:
                    v.co = hit + nrm * clr
        if piece == 'boots':                      # rubber boot toe box: hull of the foot, no toes
            zc = 0.15 * KH
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.z < zc for v in f.verts)], context='FACES')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
            for sx in (-1, 1):
                pts = [v.co.copy() for v in body.data.vertices if v.co.z < zc + 0.02 and v.co.x * sx > 0]
                if len(pts) < 8:
                    continue
                ctr = sum(pts, Vector()) / len(pts)
                new = [bm.verts.new(ctr + (q - ctr) * 1.0 + (q - ctr).normalized() * 0.014) for q in pts]
                hull = bmesh.ops.convex_hull(bm, input=new)
                loose = {g for g in hull.get('geom_interior', []) + hull.get('geom_unused', [])
                         if isinstance(g, bmesh.types.BMVert)}
                bmesh.ops.delete(bm, geom=list(loose), context='VERTS')
            inner = [v for v in bm.verts if not v.is_boundary]
        bm.normal_update()
        t = 0.006
    for v in bm.verts:
        z = v.co.z
        extra = 0.0
        if piece in ('labcoat',) and z < 0.95:
            extra = (0.95 - z) * 0.10  # skirt flares a little
        if piece == 'haircap':
            # bouffant: fuller toward the crown and back, gathered pleats
            a = math.atan2(v.co.y, v.co.x)
            extra = 0.010 * max(0.0, (z - 1.52) / 0.2) + 0.006 * max(0.0, v.co.y) / 0.1 \
                + 0.004 * math.sin(a * 26) * max(0.0, (z - 1.56) / 0.12)
        if piece in CUFF and v in ring and piece != 'haircap':
            extra += (0.006, 0.0065, 0.005, 0.002, 0.0)[ring[v]]          # turned-back hem / cuff band
        if piece in ('haircap', 'cap') and v in ring:
            extra += (0.004, 0.005, 0.003, 0.0, 0.0)[ring[v]]             # elastic edge
        if piece == 'mask':
            extra += 0.004 + (0.002 if v in ring and ring[v] < 2 else 0.0)  # stands off the face; bound edge
            zz = (z - 1.462 * KH) / (0.09 * KH)                                # 0 chin .. 1 nose bridge
            ctr = max(0.0, 1 - abs(v.co.x) / (0.07 * KH))
            extra += 0.006 * ctr * max(0.0, math.sin(zz * math.pi)) * (1 - zz)   # tented over lips and chin
            if v not in ring or ring[v] > 1:
                extra += 0.0022 * max(0.0, math.sin(zz * math.pi * 6)) * (0.4 + 0.6 * ctr)   # three pleats
        if piece in ('jacket', 'parka', 'shirt', 'shirt_farm', 'labcoat', 'trousers', 'trousers_dark', 'shorts',
                     'trousers_rolled'):
            extra += 0.002 * math.sin(z * 38 + v.co.x * 14) * math.sin(v.co.x * 31 + v.co.y * 23)  # soft folds
            ax_ = abs(v.co.x)
            # compression rings at the elbow and the back of the knee, drag folds from the armpit
            sa = (ax_ - 0.165 * KH) * 0.387 + (z - 1.385 * KH) * -0.922
            if ax_ > 0.19 * KH and z < 1.40 * KH and 0.25 * KH < sa < 0.42 * KH:
                extra += 0.006 * max(0.0, math.sin(sa * 120)) * (1 - abs(sa - 0.335 * KH) / (0.085 * KH))
            if piece.startswith('trousers') and 0.40 * KH < z < 0.60 * KH:
                extra += 0.005 * max(0.0, math.sin(z * 110)) * (1 - abs(z - 0.5 * KH) / (0.1 * KH))
            if piece in ('jacket', 'shirt', 'shirt_farm', 'parka') and 1.05 * KH < z < 1.36 * KH and ax_ > 0.08 * KH:
                extra += 0.004 * max(0.0, math.sin((z * 0.8 + ax_ * 1.2) * 70)) * min(1.0, (ax_ - 0.08 * KH) / 0.06)
            if piece in ('jacket', 'shirt', 'shirt_farm', 'parka') and 0.88 * KH < z < 1.02 * KH:
                a = math.atan2(v.co.y, v.co.x)                          # gathered at the waist / apron tie
                extra += 0.004 * max(0.0, math.sin(a * 14 + z * 9))
            if piece in ('labcoat', 'jacket', 'parka') and z < 1.25:
                # vertical drape folds hanging from the chest, deeper toward the hem
                a = math.atan2(v.co.y, v.co.x)
                u = min(1.0, (1.25 * KH - z) / 0.5)
                extra += 0.007 * u * u * (3 - 2 * u) * (0.5 + 0.5 * math.sin(a * 9 + math.sin(z * 7) * 0.8))
        v.co += v.normal * (t + extra)
    bm.to_mesh(me)
    bm.free()
    # copy weights from body (same vertex order before delete is lost, so transfer by nearest)
    dt = o.modifiers.new('dt', 'DATA_TRANSFER')
    dt.object = body
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    sol = o.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.0065 if piece not in ('gloves', 'mask', 'gloves_rubber', 'stache') else 0.0018
    sol.offset = -1
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)
    me.materials.clear()
    me.materials.append(M[PMAT[piece]])
    for p in me.polygons:
        p.material_index = 0
        p.use_smooth = True
    return o


def _apron(body, k, M):
    """PVC apron: a gently curved sheet chest->knee in front of the body, weights from the nearest body surface."""
    bm = bmesh.new()
    nx, nz = 9, 16
    grid = []
    for j in range(nz + 1):
        z = (0.52 + (1.34 - 0.52) * j / nz) * k
        row = []
        w = 0.17 if z / k > 1.05 else 0.22
        for i in range(nx + 1):
            x = (-1 + 2 * i / nx) * w * k
            # front surface of the body at this height (min y of verts in a slab) minus clearance
            ys = [v.co.y for v in body.data.vertices if abs(v.co.z - z) < 0.03 and abs(v.co.x - x) < 0.05]
            y = (min(ys) if ys else -0.12) - 0.042           # clear of the jacket folds
            y = min(y, -0.10 * k) if z / k < 0.85 else y
            row.append(bm.verts.new((x, y + 0.02 * (abs(x) / (w * k)) ** 2, z)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new(body.name + '_apron')
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(body.name + '_apron', me)
    bpy.context.scene.collection.objects.link(o)
    for vg in body.vertex_groups:
        o.vertex_groups.new(name=vg.name)
    dt = o.modifiers.new('dt', 'DATA_TRANSFER')
    dt.object = body
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    sm = o.modifiers.new('sub', 'SUBSURF')
    sm.levels = 1
    sol = o.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.003
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)
    # smooth the weights so the apron hangs between the legs instead of splitting
    for vg in o.vertex_groups:
        if vg.name.startswith(('thigh', 'shin')):
            for v in me.vertices:
                for g in v.groups:
                    if g.group == vg.index:
                        g.weight *= 0.5
    hips = o.vertex_groups.get('hips')
    for v in me.vertices:
        hips.add([v.index], 0.35, 'ADD')
    me.materials.append(M['white_pvc'])
    for p in me.polygons:
        p.use_smooth = True
    return o


def _slim_hands(body, ao):
    """Base-mesh hands read puffy under gloves: flatten each hand (palm-to-back) by 22 % about its mid plane and
    pull the fingers 10 % toward the hand axis, fading in from the wrist."""
    import numpy as np
    co = np.array([v.co[:] for v in body.data.vertices])
    for side in ('L', 'R'):
        hb = ao.data.bones['hand.' + side]
        h0, d = np.array(hb.head_local[:]), np.array((hb.tail_local - hb.head_local).normalized()[:])
        rel = co - h0
        along = rel @ d
        perp = rel - np.outer(along, d)
        dist = np.linalg.norm(perp, axis=1)
        hand = (along > -0.005) & (along < 0.25) & (dist < 0.08)
        pts = perp[hand & (along > 0.03)]
        _w, ev = np.linalg.eigh(pts.T @ pts)
        nrm = ev[:, 0]                                    # palm normal: least spread across the hand
        mid = (perp[hand] @ nrm).mean()
        fade = np.clip(along / 0.04, 0.0, 1.0)
        for i in np.nonzero(hand)[0]:
            off = perp[i] @ nrm - mid
            side_v = perp[i] - nrm * (perp[i] @ nrm)
            k = fade[i]
            co[i] = co[i] - nrm * off * 0.22 * k - side_v * 0.10 * k * (along[i] > 0.085)
    for v, c in zip(body.data.vertices, co):
        v.co = c


def build_masters(out_path, level=1):
    """Run headless once: writes humans.blend with HUM_Rig_<g> armatures and HUM_<g>_<outfit> meshes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = mats()
    for gender in ('male', 'female'):
        body, eyes = _append_body(gender)
        _apply_multires(body, level)
        h = _normalize(body, eyes)
        k = h / 1.684
        global KH
        KH = k
        body.name = 'HUMB_' + gender
        ao = _build_armature(body, h, 'HUM_Rig_' + gender)
        _skin(body, eyes, ao, bpy.data.objects.get('HUMB_male') if gender == 'female' else None)
        _slim_hands(body, ao)
        body.data.materials.clear()
        body.data.materials.append(M['skin'])
        for e in eyes:
            e.data.materials.clear()
            e.data.materials.append(M['eye'])
            ctr = sum((v.co for v in e.data.vertices), Vector()) / len(e.data.vertices)
            at = e.data.attributes.new('iris', 'FLOAT', 'POINT')
            vals = []
            for v in e.data.vertices:
                d = (v.co - ctr).normalized()
                vals.append(max(0.0, min(1.0, (-d.y - 0.80) / 0.08)))
            at.data.foreach_set('value', vals)
        pieces = {}
        regions = {}
        need = sorted({p for ps in OUTFITS.values() for p in ps} | {'stache'})
        for p in need:
            if p == 'apron':
                pieces[p] = _apron(body, k, M)
            else:
                regions[p] = _region(body, gender, p, k)
                pieces[p] = _shell(body, p, regions[p], M)
        for oname, plist in OUTFITS.items():
            if gender == 'male' and 'mask' not in plist:
                plist = plist + ['stache']
            parts = [body] + eyes + [pieces[p] for p in plist]
            cps = []
            for src in parts:
                c = src.copy()
                c.data = src.data.copy()
                for m in list(c.modifiers):
                    c.modifiers.remove(m)
                c.parent = None
                bpy.context.scene.collection.objects.link(c)
                cps.append(c)
            # hide the skin under opaque clothes (no poke-through when posed); the border ring stays
            cov = [any(regions[p][i] for p in plist if p in regions and p != 'mask') for i in range(len(body.data.vertices))]
            bm = bmesh.new()
            bm.from_mesh(cps[0].data)
            bm.verts.ensure_lookup_table()
            deep = [cov[v.index] and all(cov[e.other_vert(v).index] for e in v.link_edges) for v in bm.verts]
            kill = [f for f in bm.faces if all(deep[v.index] for v in f.verts)]
            bmesh.ops.delete(bm, geom=kill, context='FACES')
            bm.to_mesh(cps[0].data)
            bm.free()
            bpy.ops.object.select_all(action='DESELECT')
            for c in cps:
                c.select_set(True)
            bpy.context.view_layer.objects.active = cps[0]
            bpy.ops.object.join()
            j = bpy.context.view_layer.objects.active
            j.name = 'HUM_%s_%s' % (gender, oname)
            j.data.name = j.name
            j.use_fake_user = True
            j.data.use_fake_user = True
        for p in pieces.values():
            bpy.data.objects.remove(p)
        ao.data.use_fake_user = True
    # drop the raw body objects, keep meshes on fake users
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and not o.name.startswith('HUM_'):
            bpy.data.objects.remove(o)
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    print('humans written', out_path)


# ------------------------------------------------------------------ scene use
_LOADED = {}


def load(path, tag=''):
    """Append the masters from humans.blend; tag='lo' for the low-res set (humans_lo.blend)."""
    if _LOADED.get('path' + tag) == path:
        return
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        names = [n for n in src.objects if n.startswith('HUM_')]
        dst.objects = list(names)
    for n, o in zip(names, dst.objects):
        _LOADED[tag + n] = o.data
    _LOADED['path' + tag] = path


def person(name, outfit='plant', gender='male', loc=(0, 0, 0), rot_z=0.0, scale=1.0, coll=None, seed=0, lod=''):
    """Armature object `name` (root) + mesh child `name_mesh` sharing the outfit mesh. Returns the armature."""
    arm = _LOADED[lod + 'HUM_Rig_' + gender]
    me = _LOADED[lod + 'HUM_%s_%s' % (gender, outfit)]
    c = coll or bpy.context.scene.collection
    ao = bpy.data.objects.new(name, arm)
    c.objects.link(ao)
    ao.location = loc
    ao.rotation_euler = (0, 0, rot_z)
    ao.scale = (scale, scale, scale)
    mo = bpy.data.objects.new(name + '_mesh', me)
    c.objects.link(mo)
    mo.parent = ao
    md = mo.modifiers.new('arm', 'ARMATURE')
    md.object = ao
    bpy.context.view_layer.update()  # creates ao.pose
    for pb in ao.pose.bones:
        pb.rotation_mode = 'XYZ'
    ao['seed'] = seed
    # build and proportions vary per person (callers may still override scale)
    r = random.Random(seed * 7919 + len(name))
    wx, hz = r.uniform(0.94, 1.08), r.uniform(0.96, 1.04)
    ao.scale = (scale * wx, scale * wx, scale * hz)
    hb = ao.pose.bones.get('head')
    if hb:
        hb.scale = (r.uniform(0.95, 1.05), r.uniform(0.96, 1.04), r.uniform(0.96, 1.05))
    set_pose(ao, {'upperarm': (4, -24, 0), 'forearm': (14, 0, 0), 'hand': (0, 0, 0)})
    return ao


# joint angles (degrees) as (flex, side, twist): flex = forward(+) for every bone (knee: negative = bend back),
# side = outward(+) for limbs / lean to the character's left for the spine chain, twist mirrored per side.
def _rot(pb, flex, side_a, twist, side):
    rest = pb.bone.matrix_local.to_quaternion()
    d = (pb.bone.tail_local - pb.bone.head_local).normalized()
    up = d.z > 0.5
    s = 1 if side != 'R' else -1
    rx = flex if up else -flex
    ry = side_a if side == '' else -side_a * s
    rz = twist * s
    q = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_quaternion()
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = rest.inverted() @ q @ rest


def set_pose(ao, P, frame=None):
    """P: dict joint -> (x, y, z) degrees; 'upperarm' applies to both sides unless 'upperarm.L' given."""
    full = {}
    for k, v in P.items():
        if k in ('root_z', 'root_dz'):
            continue
        if '.' in k or k in ('hips', 'spine', 'chest', 'neck', 'head'):
            full[k] = v
        else:
            full.setdefault(k + '.L', v)
            full.setdefault(k + '.R', v)
    for pb in ao.pose.bones:
        side = pb.name.split('.')[-1] if '.' in pb.name else ''
        _rot(pb, *full.get(pb.name, (0, 0, 0)), side)
        if frame is not None:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
    if 'root_dz' in P and frame is not None:
        pass


def walk_cycle(ao, f0, f1, path, stride=0.72, base=None, arms=True, bob=0.025, phase=0.0, step=2):
    """Walk along path [(frame, (x,y)) ...] keyed linearly; legs cycle with distance so feet don't skate."""
    base = base or {}
    pts = sorted(path)
    def pos(f):
        for (fa, pa), (fb, pb_) in zip(pts, pts[1:]):
            if fa <= f <= fb:
                t = (f - fa) / max(1e-6, fb - fa)
                return Vector(pa).lerp(Vector(pb_), t)
        return Vector(pts[0][1] if f < pts[0][0] else pts[-1][1])
    dist = 0.0
    prev = pos(f0)
    z0 = ao.location.z
    for f in range(f0, f1 + 1, step):
        p = pos(f)
        d = (p - prev)
        dist += d.length
        if d.length > 1e-4:
            ao.rotation_euler.z = math.atan2(d.x, -d.y)  # face -Y local -> direction of travel
            ao.keyframe_insert('rotation_euler', frame=f)
        prev = p
        ph = 2 * math.pi * dist / (2 * stride) + phase
        s = math.sin(ph)
        c = math.cos(ph)
        P = dict(base)
        P['thigh.L'] = (24 * s, 2, 0)
        P['thigh.R'] = (-24 * s, 2, 0)
        P['shin.L'] = (-max(0, 40 * -c) - 4, 0, 0)
        P['shin.R'] = (-max(0, 40 * c) - 4, 0, 0)
        P['foot.L'] = (max(0, 10 * -s), 0, 0)
        P['foot.R'] = (max(0, 10 * s), 0, 0)
        if arms and 'upperarm' not in base:
            P['upperarm.L'] = (-16 * s, -13, 0)
            P['upperarm.R'] = (16 * s, -13, 0)
            P['forearm'] = (18, 0, 0)
        P.setdefault('spine', (4, 0, 0))
        P['hips'] = (0, 0, 4 * s)
        set_pose(ao, P, f)
        ao.location = (p.x, p.y, z0 + bob * abs(math.cos(ph)) - bob)
        ao.keyframe_insert('location', frame=f)


def grip(ao, side, curl=1.0, knuckle=0.085, name=None):
    """Curl the fingers of one hand around a handle: shape key on a single-user copy of this person's mesh.
    Fingers (everything past the knuckle line) rotate about the knuckle axis, more toward the tips.
    The rest-pose palm faces the thigh; the curl direction was checked visually (+1 = toward the palm)."""
    import numpy as np
    mo = ao.children[0]
    if mo.data.users > 1:
        mo.data = mo.data.copy()
    hb = ao.data.bones['hand.' + side]
    h0, d = hb.head_local, (hb.tail_local - hb.head_local).normalized()
    co = np.array([v.co[:] for v in mo.data.vertices])
    rel = co - np.array(h0[:])
    along = rel @ np.array(d[:])
    dist = np.linalg.norm(rel - np.outer(along, np.array(d[:])), axis=1)
    hand = (along > -0.01) & (along < 0.25) & (dist < 0.08)
    fin = hand & (along > 0.09)
    pts = co[fin] - co[fin].mean(axis=0)
    _w, ev = np.linalg.eigh(pts.T @ pts)
    nrm = Vector(ev[:, 0])
    if nrm.x * h0.x > 0:              # palm normal points toward the body's midline (the rest palm faces the thigh)
        nrm = -nrm
    axis = d.cross(nrm).normalized()  # (a cross product of mirrored vectors is the mirrored rotation axis)
    piv = h0 + d * knuckle
    if not mo.data.shape_keys:
        mo.shape_key_add(name='Basis')
    sk = mo.shape_key_add(name=name or ('grip_' + side))
    for i in np.nonzero(hand & (along > knuckle))[0]:
        ang = curl * min(1.0, (along[i] - knuckle) / 0.07) * math.radians(105)
        sk.data[i].co = piv + Matrix.Rotation(ang, 3, axis) @ (Vector(co[i]) - piv)
    sk.value = 1.0
    return sk


def ik_hands(ao, tgt_l, tgt_r, pole_l=None, pole_r=None):
    """Hands reach the given objects (IK on the forearm, 2-bone chain)."""
    for s, t, pole in (('L', tgt_l, pole_l), ('R', tgt_r, pole_r)):
        if t is None:
            continue
        pb = ao.pose.bones['forearm.' + s]
        c = pb.constraints.new('IK')
        c.target = t
        c.chain_count = 2
        c.use_tail = True
        if pole is not None:
            c.pole_target = pole
            c.pole_angle = math.radians(-90)
        hb = ao.pose.bones['hand.' + s]
        cr = hb.constraints.new('COPY_ROTATION')
        cr.target = t
        cr.influence = 0.0


def ik_feet(ao, tgt_l, tgt_r):
    for s, t in (('L', tgt_l), ('R', tgt_r)):
        pb = ao.pose.bones['shin.' + s]
        c = pb.constraints.new('IK')
        c.target = t
        c.chain_count = 2


POSES = {
    'stand': {'upperarm': (4, -25, 0), 'forearm': (12, 0, 0)},
    'table': {'spine': (10, 0, 0), 'chest': (8, 0, 0), 'neck': (14, 0, 0), 'head': (12, 0, 0),
              'upperarm': (28, -10, 0), 'forearm': (72, 0, 0), 'hand': (-10, 0, 0)},
    'lift_low': {'spine': (30, 0, 0), 'chest': (12, 0, 0), 'head': (-10, 0, 0),
                 'thigh': (45, 4, 0), 'shin': (-60, 0, 0), 'foot': (15, 0, 0),
                 'upperarm': (50, -8, 0), 'forearm': (20, 0, 0)},
    'carry': {'spine': (-4, 0, 0), 'upperarm': (12, -10, 0), 'forearm': (80, 0, 0)},
    'push': {'spine': (14, 0, 0), 'upperarm': (42, -6, 0), 'forearm': (35, 0, 0)},
    'look': {'upperarm': (6, -24, 0), 'forearm': (16, 0, 0), 'head': (8, 0, 0)},
}


def jitter(ao, base, f0, f1, every=12, amp=6, seed=0, arms=True):
    """Small working motion around a base pose (hands busy at a table etc.)."""
    r = random.Random(seed)
    for f in range(f0, f1 + 1, every):
        P = {k: tuple(v) for k, v in base.items()}
        def add(k, a):
            x, y, z = P.get(k, (0, 0, 0))
            P[k] = (x + r.uniform(-a, a), y + r.uniform(-a * 0.5, a * 0.5), z + r.uniform(-a * 0.4, a * 0.4))
        if arms:
            for k in ('upperarm.L', 'upperarm.R', 'forearm.L', 'forearm.R', 'hand.L', 'hand.R'):
                b = k.split('.')[0]
                if k not in P and b in P:
                    P[k] = P[b]
                add(k, amp)
        add('head', amp * 0.5)
        add('spine', amp * 0.25)
        set_pose(ao, P, f)


if __name__ == '__main__':
    import sys
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build_masters(argv[0] if argv else '/tmp/humans.blend', int(argv[1]) if len(argv) > 1 else 1)


def settle_reach(ao, f0, f1, step=2, iters=3, max_shift=0.7, z_fn=None, win=5):
    """Move the person (root x/y) so every active IK hand actually lands on its target: no hands grasping air.
    The per-frame correction is smoothed over time (no sliding jumps) and keyed on the root location.
    z_fn(x, y) re-grounds the feet after the move."""
    s = bpy.context.scene
    iks = [(pb, c) for pb in ao.pose.bones for c in pb.constraints if c.type == 'IK' and c.target]
    if not iks:
        return
    frames = list(range(f0, f1 + 1, step))
    base = {}
    for f in frames:
        s.frame_set(f)
        base[f] = ao.location.copy()
    shift = {f: Vector((0.0, 0.0)) for f in frames}
    for _ in range(iters):
        raw = {}
        for f in frames:
            s.frame_set(f)
            miss = [(c.target.matrix_world.translation - (ao.matrix_world @ pb.tail)) * c.influence
                    for pb, c in iks if c.influence > 0.05]
            m = (sum(miss, Vector()) / len(miss)).xy if miss else Vector((0.0, 0.0))
            raw[f] = shift[f] + m
        for k, f in enumerate(frames):                      # moving average over neighbouring samples
            nb = [raw[frames[j]] for j in range(max(0, k - win), min(len(frames), k + win + 1))]
            v = sum(nb, Vector((0.0, 0.0))) / len(nb)
            shift[f] = v if v.length <= max_shift else v.normalized() * max_shift
        for f in frames:
            b = base[f]
            loc = Vector((b.x + shift[f].x, b.y + shift[f].y, b.z))
            if z_fn:
                loc.z = b.z + z_fn(loc.x, loc.y) - z_fn(b.x, b.y)
            ao.location = loc
            ao.keyframe_insert('location', frame=f)
    s.frame_set(f0)
