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
}


# ------------------------------------------------------------------ materials
def _mat(name, color, rough=0.6, sss=0.0, coat=0.0, bump=0.0, sheen=0.0, normal_tex=None, tex_scale=30.0, metal=0.0,
         emission=None, estr=0.0, rand=0.0):
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
    if nrm_in:
        L.new(nrm_in, p.inputs['Normal'])
    return m


def mats():
    fab = CC0 + '/tex/Fabric030/Fabric030_2K-JPG_NormalGL.jpg'
    fab2 = CC0 + '/tex/Fabric061/Fabric061_2K-JPG_NormalGL.jpg'
    return {
        'skin': _mat('HUM_Skin', (0.42, 0.25, 0.17), 0.45, sss=0.15, bump=0.05, rand=0.25),
        'eye': _mat('HUM_Eye', (0.05, 0.035, 0.03), 0.08, coat=1.0),
        'white_cotton': _mat('HUM_WhiteCotton', (0.80, 0.81, 0.80), 0.85, sheen=0.3, bump=0.12, rand=0.04),
        'white_pvc': _mat('HUM_WhitePVC', (0.84, 0.86, 0.86), 0.32, coat=0.3, bump=0.02),
        'boot': _mat('HUM_WhiteBoot', (0.80, 0.81, 0.79), 0.35, coat=0.2, bump=0.02),
        'nitrile_blue': _mat('HUM_NitrileBlue', (0.16, 0.33, 0.62), 0.38, coat=0.25, rand=0.06),
        'cap_white': _mat('HUM_CapNonwoven', (0.84, 0.85, 0.86), 0.95, sheen=0.4, bump=0.25),
        'mask_blue': _mat('HUM_MaskBlue', (0.55, 0.70, 0.80), 0.9, sheen=0.3, bump=0.15),
        'parka': _mat('HUM_ParkaNavy', (0.10, 0.14, 0.22), 0.55, coat=0.1, bump=0.12),
        'shirt_blue': _mat('HUM_ShirtBlue', (0.22, 0.30, 0.42), 0.8, sheen=0.2, bump=0.12, rand=0.15),
        'trousers_dark': _mat('HUM_TrouserDark', (0.08, 0.08, 0.09), 0.75, bump=0.1, rand=0.2),
        'shoe': _mat('HUM_Shoe', (0.05, 0.045, 0.04), 0.45, coat=0.2),
        'hair': _mat('HUM_Hair', (0.025, 0.02, 0.018), 0.5, bump=0.4, rand=0.2),
        'hivis': _mat('HUM_HiVis', (0.75, 0.85, 0.08), 0.6, emission=(0.6, 0.7, 0.05), estr=0.15, bump=0.12),
        'shirt_farm': _mat('HUM_ShirtFarm', (0.62, 0.55, 0.42), 0.85, sheen=0.2, bump=0.12, rand=0.3),
        'shorts': _mat('HUM_Shorts', (0.20, 0.22, 0.25), 0.85, bump=0.1, rand=0.3),
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
        hand = z < 0.895 and ax > 0.30
        forearm = ax > 0.25 and z < 1.08
        arm = ax > 0.19 and z < 1.40 and not (z < 1.0 and ax < 0.24)
        sel = False
        if piece in ('jacket', 'parka', 'shirt', 'shirt_farm'):
            top = 1.455
            sel = 0.80 < z < top and not hand
            if piece == 'shirt' and forearm:
                sel = False
            if piece == 'shirt_farm' and ax > 0.33:
                sel = False
            if piece == 'parka':
                sel = 0.74 < z < 1.47 and not hand
        elif piece == 'labcoat':
            sel = 0.50 < z < 1.455 and not hand
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
            sel = (z < 0.97 and ax > 0.285) if piece == 'gloves' else (z < 0.93 and ax > 0.30)
        elif piece == 'haircap':
            sel = (z > 1.583) or (z > 1.49 and n.y > 0.1 and ax < 0.10) or (z > 1.535 and ax > 0.05 and n.y > -0.45)
            sel = sel and ax < 0.125
        elif piece in ('hair', 'cap'):
            sel = ((z > 1.60) or (z > 1.52 and n.y > 0.3) or (z > 1.56 and ax > 0.06 and n.y > -0.2)) and ax < 0.12
            if piece == 'cap':
                sel = z > 1.60 and ax < 0.12
        elif piece == 'mask':
            sel = 1.462 < z < 1.552 and ax < 0.078 and n.y < -0.25
        elif piece == 'vest':
            sel = 0.93 < z < 1.43 and ax < 0.17 and not arm
        out.append(sel)
    return out


THICK = {'jacket': 0.028, 'parka': 0.05, 'shirt': 0.03, 'shirt_farm': 0.03, 'labcoat': 0.032, 'trousers': 0.02,
         'trousers_dark': 0.016, 'trousers_rolled': 0.016, 'shorts': 0.018, 'boots': 0.018, 'shoes': 0.008,
         'gloves': 0.0035, 'gloves_rubber': 0.005, 'haircap': 0.028, 'hair': 0.008, 'cap': 0.014, 'mask': 0.008,
         'vest': 0.04}
PMAT = {'jacket': 'white_cotton', 'labcoat': 'white_cotton', 'parka': 'parka', 'shirt': 'shirt_blue',
        'shirt_farm': 'shirt_farm', 'trousers': 'white_cotton', 'trousers_dark': 'trousers_dark',
        'trousers_rolled': 'trousers_dark', 'shorts': 'shorts', 'boots': 'boot', 'shoes': 'shoe',
        'gloves': 'nitrile_blue', 'gloves_rubber': 'rubber_glove', 'haircap': 'cap_white', 'hair': 'hair',
        'cap': 'cap_cloth', 'mask': 'mask_blue', 'vest': 'hivis', 'apron': 'white_pvc'}


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
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    t = THICK[piece]
    loose_cloth = piece in ('jacket', 'parka', 'shirt', 'shirt_farm', 'labcoat', 'trousers', 'trousers_dark',
                            'trousers_rolled', 'shorts', 'vest', 'boots')
    if loose_cloth:
        # cloth drapes over the anatomy: push out, then relax (removes muscle detail), keep borders
        for v in bm.verts:
            v.co += v.normal * t
        inner = [v for v in bm.verts if not v.is_boundary]
        for _ in range(25):
            bmesh.ops.smooth_vert(bm, verts=inner, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
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
            extra = 0.022 * max(0.0, (z - 1.50) / 0.2) + 0.012 * max(0.0, v.co.y) / 0.1 \
                + 0.007 * math.sin(a * 22) * max(0.0, (z - 1.55) / 0.15)
        if piece in ('jacket', 'parka', 'shirt', 'shirt_farm', 'labcoat', 'trousers', 'trousers_dark', 'shorts'):
            extra += 0.0015 * math.sin(z * 55 + v.co.x * 20) * math.sin(v.co.x * 40 + v.co.y * 30)  # folds
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
    sol.thickness = 0.004 if piece not in ('gloves', 'mask') else 0.0015
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
            y = (min(ys) if ys else -0.12) - 0.025
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


def build_masters(out_path):
    """Run headless once: writes humans.blend with HUM_Rig_<g> armatures and HUM_<g>_<outfit> meshes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = mats()
    for gender in ('male', 'female'):
        body, eyes = _append_body(gender)
        _apply_multires(body, 1)
        h = _normalize(body, eyes)
        k = h / 1.684
        body.name = 'HUMB_' + gender
        ao = _build_armature(body, h, 'HUM_Rig_' + gender)
        _skin(body, eyes, ao, bpy.data.objects.get('HUMB_male') if gender == 'female' else None)
        body.data.materials.clear()
        body.data.materials.append(M['skin'])
        for e in eyes:
            e.data.materials.clear()
            e.data.materials.append(M['eye'])
        pieces = {}
        regions = {}
        need = sorted({p for ps in OUTFITS.values() for p in ps})
        for p in need:
            if p == 'apron':
                pieces[p] = _apron(body, k, M)
            else:
                regions[p] = _region(body, gender, p, k)
                pieces[p] = _shell(body, p, regions[p], M)
        for oname, plist in OUTFITS.items():
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


def load(path):
    if _LOADED.get('path') == path:
        return
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('HUM_')]
    for o in dst.objects:
        if o.type == 'MESH':
            _LOADED[o.name] = o.data
        else:
            _LOADED[o.name] = o.data
    _LOADED['path'] = path


def person(name, outfit='plant', gender='male', loc=(0, 0, 0), rot_z=0.0, scale=1.0, coll=None, seed=0):
    """Armature object `name` (root) + mesh child `name_mesh` sharing the outfit mesh. Returns the armature."""
    arm = _LOADED['HUM_Rig_' + gender]
    me = _LOADED['HUM_%s_%s' % (gender, outfit)]
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
    'look': {'upperarm': (4, -13, 0), 'forearm': (40, 0, 0), 'head': (8, 0, 0)},
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
    build_masters(argv[0] if argv else '/tmp/humans.blend')
