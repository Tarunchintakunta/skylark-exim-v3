"""People for the Skylark scenes, built on the CC0 Human Base Meshes (Blender Foundation) realistic bodies.

A person = armature + sculpted body (multires level 1, real face) + eyes on the neck bone + short particle hair +
separate garment meshes cut from the body (shirt, T-shirt, trousers, PVC oilskin jacket and bib-pants) that are smoothed
off the anatomy, stand off the skin, carry static folds and deform with the same bone weights. Lungis and aprons are
draped panels on the hips. The body under each garment is masked out, so nothing pokes through.

sklib.person() delegates here when the bundle is on disk; the returned armature works with sklib.pose()/walk().
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import sklib as L

LEVEL = int(os.environ.get('SK_HBM_LEVEL', '1'))   # multires level of the sculpted body (1 = ~42k verts)
_RIG = {}
_GARMENT = {}
_EYES = {}

# ------------------------------------------------------------------------------------------------ materials
SKIN_TONES = [(0.42, 0.25, 0.16), (0.34, 0.2, 0.12), (0.27, 0.15, 0.09), (0.21, 0.12, 0.075), (0.5, 0.32, 0.21),
              (0.3, 0.18, 0.11)]
HAIR_COLS = [(0.012, 0.01, 0.009), (0.02, 0.015, 0.011), (0.035, 0.025, 0.018), (0.25, 0.25, 0.25)]


def skin_mat(i, hair=0):
    name = f'MAT_HSkin{i}_{hair}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    c = SKIN_TONES[i % len(SKIN_TONES)]
    m = L.pbr(name, c, 0.48, var=0.1, bump=0.06, scale=40, sss=0.25, rough_var=0.08)
    p = L.principled(m)
    nt = m.node_tree
    # cropped hair painted on the scalp through the smooth 'hairw' attribute (soft hairline), strand-like noise
    at = L._node(nt, 'ShaderNodeAttribute', (-600, 700))
    at.attribute_name = 'hairw'
    at.attribute_type = 'GEOMETRY'
    tc = L._node(nt, 'ShaderNodeTexCoord', (-900, 900))
    hn = L._node(nt, 'ShaderNodeTexNoise', (-600, 900))
    hn.inputs['Scale'].default_value = 900.0
    hn.inputs['Detail'].default_value = 2
    nt.links.new(L._sock(tc, 'Object', out=True), hn.inputs['Vector'])
    hc = HAIR_COLS[hair % len(HAIR_COLS)]
    hcol = L.mixrgb(nt, L._sock(hn, 'Factor', out=True), hc, tuple(min(1, x * 2.2 + 0.01) for x in hc), loc=(-300, 900))
    base = p.inputs['Base Color'].links[0].from_socket
    nt.links.new(L.mixrgb(nt, L._sock(at, 'Factor', out=True), base, hcol, loc=(0, 700)),
                 p.inputs['Base Color'])
    p.inputs['Subsurface Radius'].default_value = (0.9, 0.35, 0.2)
    p.inputs['Subsurface Scale'].default_value = 0.01
    p.inputs['Specular IOR Level'].default_value = 0.45
    return m


def hair_mat(i):
    name = f'MAT_HHair{i}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    return L.pbr(name, HAIR_COLS[i % len(HAIR_COLS)], 0.42, var=0.25, bump=0.0, scale=60, coat=0.1)


def eye_mat():
    if 'MAT_HEye' in bpy.data.materials:
        return bpy.data.materials['MAT_HEye']
    m = L.new_mat('MAT_HEye')
    nt = m.node_tree
    p = L.principled(m)
    tc = L._node(nt, 'ShaderNodeTexCoord', (-900, 0))
    sep = L._node(nt, 'ShaderNodeSeparateXYZ', (-700, 0))
    nt.links.new(L._sock(tc, 'Normal', out=True), sep.inputs[0])
    # eyes look along +X at rest: iris where the object-space normal points forward
    mr = L._node(nt, 'ShaderNodeMapRange', (-500, 0))
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = 1.0
    nt.links.new(sep.outputs[0], mr.inputs['Value'])
    ramp = L._node(nt, 'ShaderNodeValToRGB', (-300, 0))
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    m['iris_ramp'] = ramp.name
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.75, 0.72, 0.68, 1)
    cr.elements[1].position = 0.86
    cr.elements[1].color = (0.75, 0.72, 0.68, 1)
    e = cr.elements.new(0.88)
    e.color = (0.09, 0.05, 0.025, 1)
    e = cr.elements.new(0.965)
    e.color = (0.005, 0.004, 0.004, 1)
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.05
    p.inputs['Coat Weight'].default_value = 1.0
    p.inputs['Coat Roughness'].default_value = 0.0
    return m


def fabric(name, color, rough=0.85, bump=0.35, coat=0.0, scale=1.0, plaid=None, grime=0.25, sheen=0.3):
    """Woven cloth on the garment's rest-pose UVs (does not swim when the body moves): Fabric030 weave normal,
    optional plaid, dirt; coat > 0 makes wet PVC."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = L.pbr(name, color, rough, var=0.18, bump=0.0, scale=4.0, coat=coat, grime=grime, coords='UV')
    nt = m.node_tree
    l = nt.links
    p = L.principled(m)
    uv = L._node(nt, 'ShaderNodeTexCoord', (-1500, -600))
    if plaid:
        # two crossing stripe sets (u and v) -> classic madras check
        cols = []
        for k, axis in enumerate((0, 1)):
            sep = L._node(nt, 'ShaderNodeSeparateXYZ', (-1300, -500 - 200 * k))
            l.new(L._sock(uv, 'UV', out=True), sep.inputs[0])
            mth = L._node(nt, 'ShaderNodeMath', (-1100, -500 - 200 * k))
            mth.operation = 'MULTIPLY'
            mth.inputs[1].default_value = plaid[2]
            l.new(sep.outputs[axis], mth.inputs[0])
            fr = L._node(nt, 'ShaderNodeMath', (-950, -500 - 200 * k))
            fr.operation = 'FRACT'
            l.new(mth.outputs[0], fr.inputs[0])
            st = L._node(nt, 'ShaderNodeMath', (-800, -500 - 200 * k))
            st.operation = 'LESS_THAN'
            st.inputs[1].default_value = 0.38
            l.new(fr.outputs[0], st.inputs[0])
            cols.append(st.outputs[0])
        both = L._node(nt, 'ShaderNodeMath', (-650, -600))
        both.operation = 'ADD'
        l.new(cols[0], both.inputs[0])
        l.new(cols[1], both.inputs[1])
        h = L._node(nt, 'ShaderNodeMath', (-500, -600))
        h.operation = 'MULTIPLY'
        h.inputs[1].default_value = 0.5
        l.new(both.outputs[0], h.inputs[0])
        base_link = p.inputs['Base Color'].links[0].from_socket
        col = L.mixrgb(nt, h.outputs[0], base_link, plaid[0], loc=(-200, -200))
        col = L.mixrgb(nt, both.outputs[0], col, plaid[1], blend='MULTIPLY', loc=(0, -200)) if plaid[1] else col
        l.new(col, p.inputs['Base Color'])
    # weave normal from the CC0 fabric set when present, else noise
    tex = os.path.join(L.TEXDIR, 'Fabric030')
    nrm = None
    if tex and os.path.isdir(tex):
        f = [x for x in os.listdir(tex) if 'NormalGL' in x]
        if f:
            mp = L._node(nt, 'ShaderNodeMapping', (-1100, -1000))
            mp.inputs['Scale'].default_value = (60 * scale, 60 * scale, 60 * scale)
            l.new(L._sock(uv, 'UV', out=True), mp.inputs['Vector'])
            it = L._node(nt, 'ShaderNodeTexImage', (-900, -1000))
            it.image = bpy.data.images.load(os.path.join(tex, f[0]), check_existing=True)
            it.image.colorspace_settings.name = 'Non-Color'
            l.new(mp.outputs[0], it.inputs['Vector'])
            nm = L._node(nt, 'ShaderNodeNormalMap', (-600, -1000))
            nm.inputs['Strength'].default_value = bump
            l.new(it.outputs['Color'], nm.inputs['Color'])
            nrm = nm.outputs[0]
    if nrm is None:
        n3 = L._node(nt, 'ShaderNodeTexNoise', (-900, -1000))
        n3.inputs['Scale'].default_value = 400 * scale
        l.new(L._sock(uv, 'UV', out=True), n3.inputs['Vector'])
        b = L._node(nt, 'ShaderNodeBump', (-600, -1000))
        b.inputs['Strength'].default_value = bump * 0.5
        b.inputs['Distance'].default_value = 0.002
        l.new(L._sock(n3, 'Factor', out=True), b.inputs['Height'])
        nrm = b.outputs[0]
    l.new(nrm, p.inputs['Normal'])
    if coat:
        p.inputs['Coat Normal'].default_value = (0, 0, 0)
    else:
        p.inputs['Sheen Weight'].default_value = sheen
        p.inputs['Sheen Roughness'].default_value = 0.5
    return m


def fabrics():
    """The garment palette (desaturated, real working clothes)."""
    F = {
        'pvc_orange': fabric('MAT_PVCOrange', (0.62, 0.22, 0.05), 0.3, bump=0.15, coat=0.6, grime=0.35),
        'pvc_yellow': fabric('MAT_PVCYellow', (0.64, 0.48, 0.07), 0.3, bump=0.15, coat=0.6, grime=0.35),
        'pvc_green': fabric('MAT_PVCGreen', (0.07, 0.2, 0.1), 0.32, bump=0.15, coat=0.55, grime=0.3),
        'shirt_check_red': fabric('MAT_ShirtCheckRed', (0.42, 0.1, 0.07), plaid=((0.12, 0.12, 0.2), (0.7, 0.7, 0.7), 9.0)),
        'shirt_check_blue': fabric('MAT_ShirtCheckBlue', (0.12, 0.2, 0.38), plaid=((0.55, 0.55, 0.5), (0.8, 0.8, 0.85), 8.0)),
        'shirt_check_green': fabric('MAT_ShirtCheckGreen', (0.15, 0.25, 0.15), plaid=((0.5, 0.45, 0.3), (0.75, 0.75, 0.7), 10.0)),
        'shirt_white': fabric('MAT_ShirtWhite', (0.72, 0.72, 0.7), grime=0.35),
        'shirt_sky': fabric('MAT_ShirtSky', (0.35, 0.45, 0.55)),
        'shirt_maroon': fabric('MAT_ShirtMaroon', (0.28, 0.06, 0.06)),
        'tee_grey': fabric('MAT_TeeGrey', (0.3, 0.3, 0.3), grime=0.3),
        'tee_navy': fabric('MAT_TeeNavy', (0.05, 0.07, 0.13)),
        'tee_olive': fabric('MAT_TeeOlive', (0.22, 0.22, 0.12)),
        'banian': fabric('MAT_Banian', (0.66, 0.65, 0.6), grime=0.45),
        'trouser_navy': fabric('MAT_TrouserNavy', (0.04, 0.05, 0.08)),
        'trouser_khaki': fabric('MAT_TrouserKhaki', (0.3, 0.26, 0.18)),
        'trouser_grey': fabric('MAT_TrouserGrey', (0.18, 0.18, 0.19)),
        'lungi_blue': fabric('MAT_LungiBlue', (0.1, 0.18, 0.4), plaid=((0.55, 0.5, 0.4), None, 6.0)),
        'lungi_green': fabric('MAT_LungiGreen', (0.08, 0.25, 0.2), plaid=((0.6, 0.55, 0.45), None, 5.0)),
        'lungi_check': fabric('MAT_LungiCheck', (0.35, 0.08, 0.1), plaid=((0.08, 0.1, 0.25), (0.75, 0.7, 0.7), 7.0)),
        'lungi_white': fabric('MAT_LungiWhite', (0.7, 0.69, 0.64), grime=0.4),
        'coat_white': fabric('MAT_CoatWhite', (0.82, 0.83, 0.84), grime=0.1),
        'scrub_white': fabric('MAT_ScrubWhite', (0.8, 0.81, 0.82), grime=0.12),
        'jacket_navy': fabric('MAT_JacketNavy', (0.04, 0.06, 0.12), 0.7, coat=0.1),
        'hivis': fabric('MAT_HiVisVest', (0.7, 0.85, 0.05), 0.7, grime=0.3),
        'hivis_orange': fabric('MAT_HiVisVestOrange', (0.85, 0.3, 0.03), 0.7, grime=0.3),
        'apron_white': fabric('MAT_ApronPVCWhite', (0.85, 0.86, 0.86), 0.25, bump=0.05, coat=0.5, grime=0.15),
        'apron_blue': fabric('MAT_ApronPVCBlue', (0.18, 0.36, 0.62), 0.25, bump=0.05, coat=0.5, grime=0.15),
    }
    return F


# ------------------------------------------------------------------------------------------------ rig + body
def _load_hbm(gender):
    """Sculpted body at LEVEL + its two eyes, turned to face +X, feet on z=0, 1.72 m. -> (body me, eyes me, skel)"""
    name = f'GEO-body_{gender}_realistic'
    with bpy.data.libraries.load(L.HBM, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == name or n.startswith(name + '.eye')]
    objs = [o for o in dst.objects if o is not None]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    body = [o for o in objs if o.name == name or (o.name.startswith(name) and '.eye' not in o.name)][0]
    for m in body.modifiers:
        if m.type == 'MULTIRES':
            m.levels = min(LEVEL, m.total_levels)
            m.render_levels = m.levels
            m.sculpt_levels = m.levels
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bmb, bme = bmesh.new(), bmesh.new()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        (bme if '.eye' in o.name else bmb).from_mesh(me)
        bpy.data.meshes.remove(me)
    for o in objs:
        bpy.data.objects.remove(o)
    zmin = min(v.co.z for v in bmb.verts)
    H = max(v.co.z for v in bmb.verts) - zmin
    xs = [v.co.x for v in bmb.verts]
    cx = (min(xs) + max(xs)) / 2
    s = 1.72 / H
    T = Matrix.Diagonal((s, s, s, 1)) @ Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Translation((-cx, 0, -zmin))
    for bm in (bmb, bme):
        bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    body_me = L.bm_to_mesh(bmb, f'HBODY_{gender}', smooth=True)
    eyes_me = L.bm_to_mesh(bme, f'HEYES_{gender}', smooth=True)
    return body_me, eyes_me


def _skel_from(me):
    """Joint points from the base-mesh proportions (same rules as sklib._hbm_mesh)."""
    vs = [v.co for v in me.vertices]
    Hn = 1.72

    def centroid(sel):
        pts = [v for v in vs if sel(v)]
        return sum(pts, Vector()) / max(1, len(pts))

    skel = {}
    for side, sg in (('L', 1), ('R', -1)):
        leg = lambda v, z0, z1: z0 * Hn < v.z < z1 * Hn and sg * v.y > 0.01
        skel[f'hp_{side}'] = centroid(lambda v: leg(v, 0.46, 0.48))
        skel[f'hp_{side}'].x = 0.0
        skel[f'kn_{side}'] = centroid(lambda v: leg(v, 0.27, 0.29))
        skel[f'an_{side}'] = centroid(lambda v: leg(v, 0.045, 0.06))
        foot = [v for v in vs if v.z < 0.05 * Hn and sg * v.y > 0.01]
        skel[f'to_{side}'] = max(foot, key=lambda v: v.x).copy()
        skel[f'to_{side}'].z = 0.04
        tip = max((v for v in vs if v.z > 0.35 * Hn), key=lambda v: sg * v.y).copy()
        sh = Vector((-0.01, sg * 0.105 * Hn, 0.815 * Hn))
        skel[f'sh_{side}'] = sh
        skel[f'el_{side}'] = sh + (tip - sh) * 0.46
        skel[f'wr_{side}'] = sh + (tip - sh) * 0.84
        skel[f'ht_{side}'] = tip
    skel.update({'pelvis': Vector((0, 0, 0.53 * Hn)), 'waist': Vector((0, 0, 0.62 * Hn)), 'chest': Vector((0, 0, 0.73 * Hn)),
                 'neckb': Vector((-0.01, 0, 0.845 * Hn)), 'head': Vector((0.01, 0, 0.935 * Hn)), 'headt': Vector((0, 0, 1.0 * Hn))})
    return skel


def _seg_t(p, a, b):
    ab = b - a
    t = (p - a).dot(ab) / max(1e-9, ab.length_squared)
    return t, (a + ab * max(0.0, min(1.0, t)) - p).length


def rig(gender='male', build=1.0):
    """Rigged, zoned body for one variant (cached): (body mesh, armature data, skel, eyes mesh, zones per vertex)."""
    key = (gender, round(build, 2))
    if key in _RIG:
        return _RIG[key]
    body, eyes = _load_hbm(gender)
    skel = _skel_from(body)
    if build != 1.0:
        S = Matrix.Diagonal((build, build, 1.0, 1.0))
        body.transform(S)
        eyes.transform(S)
        skel = {n: Vector((p.x * build, p.y * build, p.z)) for n, p in skel.items()}
    ad = bpy.data.armatures.new(f'HRIG_{gender}_{key[1]}')
    ao = bpy.data.objects.new('HRIG_tmp', ad)
    bpy.context.scene.collection.objects.link(ao)
    bo = bpy.data.objects.new('HBODY_tmp', body)
    bpy.context.scene.collection.objects.link(bo)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    ao.select_set(True)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, (h, t, par, kind) in L.BONES.items():
        eb = ad.edit_bones.new(bn)
        eb.head = skel[h]
        eb.tail = skel[t]
        if par:
            eb.parent = ad.edit_bones[par]
        eb.align_roll({'down': (0, 1, 0), 'up': (0, -1, 0), 'fwd': (0, 0, 1)}[kind])
    bpy.ops.object.mode_set(mode='OBJECT')
    bo.select_set(True)
    ao.select_set(True)
    bpy.context.view_layer.objects.active = ao
    with bpy.context.temp_override(active_object=ao, object=ao, selected_objects=[bo, ao], selected_editable_objects=[bo, ao]):
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    bo.select_set(False)
    ao.select_set(False)
    # rigid hands on the wrist bone, feet on the ankle bone (auto weights smear fingers)
    for sd in 'LR':
        sh, tip = skel[f'sh_{sd}'], skel[f'ht_{sd}']
        wg = bo.vertex_groups[f'wr_{sd}']
        ag = bo.vertex_groups[f'an_{sd}']
        sg = 1 if sd == 'L' else -1
        for v in body.vertices:
            t, d = _seg_t(v.co, sh, tip)
            foot = v.co.z < skel[f'an_{sd}'].z - 0.01 and sg * v.co.y > 0
            if (t > 0.86 and d < 0.09) or foot:
                for g in bo.vertex_groups:
                    g.remove([v.index])
                (wg if not foot else ag).add([v.index], 1.0, 'REPLACE')
    for sd, sg in (('L', 1), ('R', -1)):
        a = skel[f'el_{sd}'] - skel[f'sh_{sd}']
        ad[f'arm_{sd}'] = math.atan2(sg * a.y, -a.z)
    top = [v.co for v in body.vertices if v.co.z > 1.62]
    xs = [c.x for c in top]
    skel['headc'] = Vector(((min(xs) + max(xs)) / 2, 0.0, max(c.z for c in top) - 0.06))
    # geometric zones per vertex: torso, upper arm, forearm, hip/pelvis, thigh, shin, foot, hand, neck/head, scalp
    hc = skel['head']
    zones = []
    for v in body.vertices:
        p = v.co
        sgn = 'L' if p.y > 0 else 'R'
        ta, da = _seg_t(p, skel[f'sh_{sgn}'], skel[f'ht_{sgn}'])
        on_arm = da < 0.075 and ta > 0.02 and abs(p.y) > 0.16
        rel = p - hc
        if p.z > skel['neckb'].z - 0.035 and not on_arm:
            scalp = (rel.z > 0.072) or (rel.z > 0.02 and rel.x < 0.02) or (rel.z > -0.075 and rel.x < -0.035)
            ear = abs(rel.y) > 0.07 and -0.05 < rel.z < 0.035 and -0.03 < rel.x < 0.03
            zones.append('scalp' if scalp and not ear and p.z > skel['neckb'].z + 0.02 else 'head')
        elif on_arm:
            zones.append('hand' if ta > 0.82 else ('forearm' if ta > 0.44 else 'upperarm'))
        elif p.z < skel[f'an_{sgn}'].z + 0.03:
            zones.append('foot')
        elif p.z < skel[f'kn_{sgn}'].z:
            zones.append('shin')
        elif p.z < skel['pelvis'].z - 0.04:
            zones.append('thigh')
        elif p.z < skel['waist'].z - 0.02:
            zones.append('pelvis')
        else:
            zones.append('torso')
    sg = bo.vertex_groups.new(name='scalp')
    hw = body.attributes.new('hairw', 'FLOAT', 'POINT')
    for v in body.vertices:
        rel = v.co - hc
        f = max(rel.z - 0.072, min(rel.z - 0.02, 0.02 - rel.x), min(rel.z + 0.075, -0.035 - rel.x))
        w = max(0.0, min(1.0, (f + 0.008) / 0.016)) if v.co.z > skel['neckb'].z + 0.02 else 0.0
        hw.data[v.index].value = w
        if w > 0.05:
            sg.add([v.index], w, 'REPLACE')
    bpy.data.objects.remove(bo)
    bpy.data.objects.remove(ao)
    _RIG[key] = (body, ad, skel, eyes, zones)
    return _RIG[key]


# ------------------------------------------------------------------------------------------------ garments
GARMENTS = {
    # zones covered, stand-off from the skin (m), fold amplitude, smoothing passes, sleeve/hem extras
    'shirt': dict(zones={'torso', 'upperarm', 'forearm', 'pelvis'}, off=0.012, fold=0.006, smooth=16, cuff_t=0.72),
    'shirt_rolled': dict(zones={'torso', 'upperarm', 'forearm', 'pelvis'}, off=0.012, fold=0.007, smooth=16, cuff_t=0.52),
    'tee': dict(zones={'torso', 'upperarm', 'pelvis'}, off=0.008, fold=0.004, smooth=8, cuff_t=0.3),
    'banian': dict(zones={'torso', 'pelvis'}, off=0.004, fold=0.003, smooth=6, cuff_t=0.0),
    'trousers': dict(zones={'pelvis', 'thigh', 'shin'}, off=0.011, fold=0.006, smooth=10),
    'shorts': dict(zones={'pelvis', 'thigh'}, off=0.012, fold=0.005, smooth=8),
    'pvc_jacket': dict(zones={'torso', 'upperarm', 'forearm', 'pelvis'}, off=0.03, fold=0.016, smooth=24, cuff_t=0.8),
    'pvc_bib': dict(zones={'torso', 'pelvis', 'thigh', 'shin'}, off=0.03, fold=0.016, smooth=24, bib=True),
    'coat': dict(zones={'torso', 'upperarm', 'forearm', 'pelvis', 'thigh'}, off=0.026, fold=0.008, smooth=26, cuff_t=0.8),
}


def _garment(key, kind):
    """Garment mesh cut from the rigged body (keeps its bone weights): smoothed, offset, folded, UV'd at rest."""
    gk = (key, kind)
    if gk in _GARMENT:
        return _GARMENT[gk]
    body, ad, skel, eyes, zones = _RIG[key]
    g = GARMENTS[kind]
    bm = bmesh.new()
    bm.from_mesh(body)
    bm.verts.ensure_lookup_table()
    keep = set()
    for v in bm.verts:
        z = zones[v.index]
        if z not in g['zones']:
            continue
        p = v.co
        sgn = 'L' if p.y > 0 else 'R'
        if z in ('upperarm', 'forearm'):
            t, _ = _seg_t(p, skel[f'sh_{sgn}'], skel[f'ht_{sgn}'])
            if t > g.get('cuff_t', 1.0):
                continue
        if g.get('bib') and z == 'torso':
            # bib front + back panels up to mid chest, braces over the shoulders
            if p.z > skel['chest'].z + 0.02:
                continue
        keep.add(v.index)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(v.index in keep for v in f.verts)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True, smooth=0.0)
    bm.verts.ensure_lookup_table()
    # hems: smooth each open edge loop along itself so cuffs, collars and hems are clean curves, not stair steps
    bnd = [v for v in bm.verts if v.is_boundary]
    nb = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bnd}
    for _ in range(14):
        new = {v: (v.co + sum((u.co for u in nb[v]), Vector())) / (1 + len(nb[v])) for v in bnd if len(nb[v]) == 2}
        for v, c in new.items():
            v.co = c
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(g['smooth']):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # cloth spans the hollows: every horizontal slice of the torso/legs is pushed out to its convex hull
    _hull_slices(bm, skel, _arm_groups(body))
    # drape: cloth falls from the most forward/backward point of the chest instead of following the anatomy under it
    bm.normal_update()
    _drape(bm, skel, front=True)
    _drape(bm, skel, front=False)
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    rnd = random.Random(hash(kind) & 0xffff)
    seed = Vector((rnd.random() * 50, rnd.random() * 50, rnd.random() * 50))
    joints = [skel[n] for n in ('el_L', 'el_R', 'kn_L', 'kn_R', 'waist', 'sh_L', 'sh_R')]
    for v in bm.verts:
        p = v.co.copy()
        n = v.normal.copy()
        # loose cloth: low-frequency bagginess + folds that run around the limbs (squashed noise along z)
        bag = noise.noise(Vector((p.x * 3, p.y * 3, p.z * 1.5)) + seed) * 0.5 + 0.5
        # soft drape folds: mostly vertical/diagonal, a few ridged creases (1 - |noise|), stronger lower down
        drape = noise.noise(Vector((p.x * 7, p.y * 7, (p.z + 0.4 * p.y) * 4)) + seed)
        crease = 1.0 - abs(noise.noise(Vector((p.x * 5, p.y * 5, p.z * 9)) + seed * 1.7))
        bunch = 0.0
        for j in joints:
            dj = (p - j).length
            if dj < 0.09:
                bunch += (1 - dj / 0.09) * (1.0 - abs(noise.noise(Vector((p.x * 14, p.y * 14, p.z * 30)) + seed)))
        d = g['off'] * (0.7 + 0.6 * bag) + g['fold'] * (1.8 * drape + 2.0 * (crease - 0.5) + 1.4 * bunch)
        if v.is_boundary:
            d = g['off'] + 0.006
        v.co = p + n * d
    # rest-pose UVs (u around, v up) so the weave and plaid stay on the cloth when it moves
    uvl = bm.loops.layers.uv.new('rest')
    for f in bm.faces:
        for lp in f.loops:
            p = lp.vert.co
            lp[uvl].uv = (p.y * 1.0 + p.x * 0.6, p.z)
    me = L.bm_to_mesh(bm, f'HG_{kind}_{key[0]}_{key[1]}', smooth=True)
    _copy_group_names(body, me)
    _GARMENT[gk] = me
    return me


def _lungi_mesh(skel, tucked):
    """Wrap-around lungi: a draped tube from the waist to the ankle (or folded up to the knee), with vertical folds,
    weighted to the hips and thighs."""
    bm = bmesh.new()
    seg, rings = 48, 22
    z0 = skel['waist'].z - 0.03
    z1 = (skel['kn_L'].z - 0.02) if tucked else 0.16
    rows = []
    for i in range(rings + 1):
        t = i / rings
        z = z0 + (z1 - z0) * t
        r = 0.165 + 0.035 * math.sin(min(1.0, t * 2.2) * math.pi / 2) + (0.01 * t if not tucked else 0)
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            fold = 0.008 * math.sin(a * 11 + t * 2) * t + 0.006 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, z * 4)))
            rr = r + fold
            row.append(bm.verts.new((rr * math.cos(a) * 0.92 + 0.01, rr * math.sin(a), z)))
        rows.append(row)
    for i in range(rings):
        for j in range(seg):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % seg], rows[i + 1][(j + 1) % seg], rows[i + 1][j]))
    uvl = bm.loops.layers.uv.new('rest')
    for f in bm.faces:
        for lp in f.loops:
            p = lp.vert.co
            lp[uvl].uv = (math.atan2(p.y, p.x) * 0.2, p.z)
    me = L.bm_to_mesh(bm, 'HG_lungi_tucked' if tucked else 'HG_lungi', smooth=True)
    return me


def _lungi_weights(o, skel):
    gh = o.vertex_groups.new(name='hips')
    gl = o.vertex_groups.new(name='hp_L')
    gr = o.vertex_groups.new(name='hp_R')
    z0 = skel['waist'].z
    for v in o.data.vertices:
        t = max(0.0, min(1.0, (z0 - v.co.z) / 0.55))
        side = max(0.0, min(1.0, 0.5 + v.co.y / 0.2))
        gh.add([v.index], 1.0 - 0.6 * t, 'REPLACE')
        gl.add([v.index], 0.6 * t * side, 'REPLACE')
        gr.add([v.index], 0.6 * t * (1 - side), 'REPLACE')


def _apron_mesh(skel, length=0.95):
    """Front PVC apron: curved panel from mid-chest to below the knee, soft vertical folds, rigid on the hips."""
    bm = bmesh.new()
    cols, rows = 16, 26
    top = skel['chest'].z + 0.06
    vs = []
    for i in range(rows + 1):
        t = i / rows
        z = top - length * t
        w = 0.16 + 0.07 * min(1.0, t * 2.5)
        row = []
        for j in range(cols + 1):
            u = j / cols * 2 - 1
            y = u * w
            x = 0.155 - 0.07 * u * u + 0.004 * math.sin(u * 9 + t * 3) * t + (0.02 * t if t > 0.45 else 0)
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for i in range(rows):
        for j in range(cols):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    uvl = bm.loops.layers.uv.new('rest')
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.y, lp.vert.co.z)
    return L.bm_to_mesh(bm, 'HG_apron', smooth=True)


# ------------------------------------------------------------------------------------------------ outfits
OUTFITS = {
    # garments [(kind, fabric key | list to pick from)], headwear, hands, feet
    'fisherman_o': dict(g=[('shirt_rolled', ['shirt_check_red', 'shirt_check_blue', 'tee_grey']), ('pvc_bib', 'pvc_orange')],
                        head='cap', hands='glove_teal', feet='boot_yellow'),
    'fisherman_y': dict(g=[('pvc_jacket', 'pvc_yellow'), ('pvc_bib', 'pvc_yellow')], head='cap', hands='glove_teal',
                        feet='boot_white'),
    'fisherman_b': dict(g=[('tee', ['tee_navy', 'tee_olive', 'tee_grey']), ('pvc_bib', ['pvc_orange', 'pvc_yellow'])],
                        head='cap', hands='skin', feet='boot_yellow'),
    'dock': dict(g=[('shirt_rolled', ['shirt_check_red', 'shirt_check_blue', 'shirt_check_green', 'shirt_sky', 'shirt_white']),
                    ('lungi_tucked', ['lungi_blue', 'lungi_check', 'lungi_green', 'lungi_white'])],
                 head=['none', 'towel', 'cap'], hands='skin', feet='sandal'),
    'dock2': dict(g=[('banian', 'banian'), ('lungi', ['lungi_blue', 'lungi_check', 'lungi_white'])], head=['none', 'towel'],
                  hands='skin', feet='sandal'),
    'plant': dict(g=[('coat', 'scrub_white'), ('trousers', 'scrub_white'), ('apron', 'apron_white')], head='haircap', mask=True,
                  hands='glove_blue', feet='boot_white'),
    'plant_blue': dict(g=[('coat', 'scrub_white'), ('trousers', 'scrub_white'), ('apron', 'apron_blue')], head='haircap', mask=True,
                       hands='glove_blue', feet='boot_white'),
    'qc': dict(g=[('coat', 'coat_white'), ('trousers', 'trouser_navy')], head='haircap', mask=True, hands='glove_blue',
               feet='boot_white'),
    'cold': dict(g=[('pvc_jacket', 'jacket_navy'), ('trousers', 'trouser_navy')], head='haircap', mask=True, hands='glove_blue',
                 feet='boot_black'),
    'farm': dict(g=[('shirt_rolled', ['shirt_check_red', 'shirt_check_green']), ('trousers', 'trouser_khaki')], head='cap',
                 hands='skin', feet='boot_black'),
    'farm2': dict(g=[('shirt', ['shirt_sky', 'shirt_maroon']), ('trousers', 'trouser_navy')], head='none', hands='glove_blue',
                  feet='boot_black'),
    'farm3': dict(g=[('banian', 'banian'), ('lungi_tucked', ['lungi_blue', 'lungi_check'])], head=['towel', 'none'], hands='skin',
                  feet='boot_black'),
    'driver': dict(g=[('shirt', ['shirt_sky', 'shirt_white']), ('trousers', 'trouser_khaki'), ('vest', 'hivis')], head='none',
                   hands='skin', feet='boot_black'),
    'port': dict(g=[('shirt', 'jacket_navy'), ('trousers', 'trouser_navy'), ('vest', ['hivis', 'hivis_orange'])], head='hardhat',
                 hands='glove_blue', feet='boot_black'),
    'port_o': dict(g=[('shirt', 'hivis_orange'), ('trousers', 'trouser_navy'), ('vest', 'hivis')], head='hardhat',
                   hands='glove_blue', feet='boot_black'),
}


def _pick(rnd, v):
    return rnd.choice(v) if isinstance(v, list) else v


def _hair(bo, mat, rnd, length):
    """Short particle hair on the scalp vertex group (follows the armature-deformed body)."""
    ps_mod = bo.modifiers.new('Hair', 'PARTICLE_SYSTEM')
    ps = ps_mod.particle_system.settings
    ps.type = 'HAIR'
    ps.count = 2500
    ps.hair_length = length
    ps.emit_from = 'FACE'
    ps.use_advanced_hair = False
    ps.normal_factor = 0.0
    ps.child_type = 'INTERPOLATED'
    ps.child_percent = 3
    ps.rendered_child_count = 6
    ps.child_length = 1.0
    ps.roughness_1 = 0.004
    ps.roughness_endpoint = 0.003
    ps.clump_factor = 0.15
    ps.root_radius = 0.6
    ps.tip_radius = 0.2
    ps.radius_scale = 0.0012
    ps.display_step = 2
    ps.render_step = 3
    ps.material_slot = mat.name
    bo.particle_systems[0].vertex_group_density = 'scalp'
    ps.use_hair_bspline = True
    return ps


def _towel_mesh():
    """Head towel wrapped as a low turban."""
    bm = bmesh.new()
    seg, ring = 28, 10
    rows = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(ring):
            b = 2 * math.pi * j / ring
            R = 0.095 + 0.004 * math.sin(a * 5)
            r = 0.028 + 0.004 * math.sin(a * 3 + 1)
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b) + 0.015 * math.cos(a)
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for i in range(seg):
        for j in range(ring):
            bm.faces.new((rows[i][j], rows[(i + 1) % seg][j], rows[(i + 1) % seg][(j + 1) % ring], rows[i][(j + 1) % ring]))
    return L.bm_to_mesh(bm, 'HG_towel', smooth=True)


def _sandal_mesh():
    return L.box_mesh('HG_sandal', (0.27, 0.105, 0.015), 0.006, 2)


def person(name, outfit='plant', loc=(0, 0, 0), rot_z=0.0, height=1.72, skin=None, build=1.0, seed=None, mats=None):
    mats = mats or L.M()
    F = fabrics()
    rnd = random.Random(seed if seed is not None else hash(name) & 0xffff)
    o = OUTFITS.get(outfit) or OUTFITS['farm']
    female = outfit in ('plant', 'plant_blue', 'qc', 'farm2') and rnd.random() < 0.4
    gender = 'female' if female else 'male'
    build = round(build * rnd.choice((0.94, 1.0, 1.0, 1.06, 1.12)), 2)
    key = (gender, round(build, 2))
    body, ad, skel, eyes, zones = rig(gender, build)
    arm = bpy.data.objects.new(name, ad)
    L._link(arm)
    sk = skin if isinstance(skin, bpy.types.Material) else skin_mat(skin if isinstance(skin, int) else rnd.randrange(6))
    garments = []
    covered = set()
    lower_kind = None
    for kind, fk in o['g']:
        fk = _pick(rnd, fk)
        mat = F.get(fk) or mats.get(fk)
        if kind in GARMENTS:
            me = _garment(key, kind)
            g = bpy.data.objects.new(f'{name}_{kind}', me)
            L._link(g)
            g.parent = arm
            md = g.modifiers.new('Rig', 'ARMATURE')
            md.object = arm
            sol = g.modifiers.new('Thick', 'SOLIDIFY')
            sol.thickness = 0.004 if not kind.startswith('pvc') else 0.006
            sol.offset = -1.0
            if not len(me.materials):
                me.materials.append(mat)
            g.material_slots[0].link = 'OBJECT'
            g.material_slots[0].material = mat
            garments.append(g)
            cut = GARMENTS[kind]
            for vi, z in enumerate(zones):
                if z in cut['zones']:
                    covered.add((vi, kind))
            if kind in ('trousers', 'pvc_bib', 'shorts'):
                lower_kind = kind
            if kind == 'pvc_bib':
                st = _acc(name, 'straps', _part(('straps', key), lambda: _straps_mesh(skel)), mat)
                st.modifiers.new('Thick', 'SOLIDIFY').thickness = 0.004
                L._bone_attach(st, arm, 'spine', Matrix.Identity(4))
        elif kind in ('lungi', 'lungi_tucked'):
            me = _part(('lungi', kind), lambda: _lungi_mesh(skel, kind == 'lungi_tucked'))
            g = bpy.data.objects.new(f'{name}_lungi', me)
            L._link(g)
            g.parent = arm
            _lungi_weights(g, skel)
            md = g.modifiers.new('Rig', 'ARMATURE')
            md.object = arm
            sol = g.modifiers.new('Thick', 'SOLIDIFY')
            sol.thickness = 0.004
            if not len(me.materials):
                me.materials.append(mat)
            g.material_slots[0].link = 'OBJECT'
            g.material_slots[0].material = mat
            garments.append(g)
            lower_kind = 'lungi'
        elif kind == 'apron':
            me = _part(('apron', key), lambda: _apron_mesh(skel))
            a = bpy.data.objects.new(f'{name}_apron', me)
            L._link(a)
            if not len(me.materials):
                me.materials.append(mat)
            a.material_slots[0].link = 'OBJECT'
            a.material_slots[0].material = mat
            sol = a.modifiers.new('Thick', 'SOLIDIFY')
            sol.thickness = 0.003
            L._bone_attach(a, arm, 'hips', Matrix.Identity(4))
        elif kind == 'vest':
            me = _garment(key, 'banian')
            v = bpy.data.objects.new(f'{name}_vest', me)
            L._link(v)
            v.parent = arm
            md = v.modifiers.new('Rig', 'ARMATURE')
            md.object = arm
            dsp = v.modifiers.new('Over', 'DISPLACE')
            dsp.strength = 0.014
            dsp.mid_level = 0.0
            if not len(me.materials):
                me.materials.append(mat)
            v.material_slots[0].link = 'OBJECT'
            v.material_slots[0].material = mat
    # body: skin everywhere, hands/feet zones get gloves/boots colours; hide skin under the garments
    bo = bpy.data.objects.new(f'{name}_body', body)
    L._link(bo)
    bo.parent = arm
    md = bo.modifiers.new('Rig', 'ARMATURE')
    md.object = arm
    _body_slots(body, zones)
    hands = sk if o['hands'] == 'skin' else mats[o['hands']]
    feet = sk if o['feet'] == 'sandal' else mats[o['feet']]
    hj = rnd.randrange(3) if rnd.random() > 0.12 else 3
    hmat = hair_mat(hj)
    if not isinstance(skin, bpy.types.Material):
        sk = skin_mat(skin if isinstance(skin, int) else rnd.randrange(6), hj)
        hands = sk if o['hands'] == 'skin' else hands
        feet = sk if o['feet'] == 'sandal' else feet
    for i, m in enumerate([sk, hands, feet, hmat]):
        bo.material_slots[i].link = 'OBJECT'
        bo.material_slots[i].material = m
    kinds = {k for _, k in covered}
    gname = 'cov_' + '_'.join(sorted(kinds)) if kinds else None
    if gname:
        _cover_group(body, zones, kinds, skel, gname)
        mk = bo.modifiers.new('Under', 'MASK')
        mk.vertex_group = gname
        mk.invert_vertex_group = True
    head = _pick(rnd, o.get('head', 'none'))
    if head in ('none', 'towel', 'cap'):
        _hair(bo, hmat, rnd, rnd.choice((0.012, 0.018, 0.026)))
    # eyes on the neck bone
    e = bpy.data.objects.new(f'{name}_eyes', eyes)
    L._link(e)
    if not len(eyes.materials):
        eyes.materials.append(eye_mat())
    L._bone_attach(e, arm, 'neck', Matrix.Identity(4))
    hp = skel['headc'] + Vector((0, 0, -0.04))
    hm = skel['head']
    if gender == 'male' and rnd.random() < 0.6 and not o.get('mask'):
        L._bone_attach(_acc(name, 'moustache', _part('moustache', _moustache_mesh), hmat), arm, 'neck',
                       Matrix.Translation(hm + Vector((0.093, 0, -0.047))) @ Matrix.Diagonal((1, rnd.uniform(0.85, 1.15),
                                                                                              rnd.uniform(0.8, 1.3), 1)))
    if head == 'cap':
        L._bone_attach(_acc(name, 'cap', L._part_mesh('cap', L._cap_mesh), mats['cap_grey'] if rnd.random() < 0.5 else F['tee_navy']),
                       arm, 'neck', Matrix.Translation(hp + Vector((-0.01, 0, 0.045))) @ Matrix.Rotation(-0.2, 4, 'Y') @ Matrix.Diagonal((1.0, 0.86, 0.95, 1)))
    elif head == 'towel':
        L._bone_attach(_acc(name, 'towel', _part('towel', _towel_mesh), rnd.choice((F['lungi_white'], F['shirt_check_red'], F['banian']))),
                       arm, 'neck', Matrix.Translation(hp + Vector((0.005, 0, 0.06))))
    elif head == 'haircap':
        L._bone_attach(_acc(name, 'haircap', L._part_mesh('haircap', lambda: L.sphere_mesh('BODY_haircap', 0.105, 20, 12)),
                            mats['haircap']), arm, 'neck',
                       Matrix.Translation(hp + Vector((0.0, 0, 0.035))) @ Matrix.Diagonal((1.08, 1.02, 0.86, 1)))
    elif head == 'hardhat':
        L._bone_attach(_acc(name, 'hardhat', L._part_mesh('hardhat', L._hardhat_mesh),
                            mats['hardhat'] if rnd.random() < 0.5 else mats['float_yellow']),
                       arm, 'neck', Matrix.Translation(hp + Vector((0.02, 0, 0.06))))
    if o.get('mask'):
        L._bone_attach(_acc(name, 'mask', L._part_mesh('mask', lambda: L.box_mesh('BODY_mask', (0.05, 0.15, 0.085), 0.024, 3)),
                            mats['mask']), arm, 'neck', Matrix.Translation(hm + Vector((0.085, 0, -0.035))))
    if o['feet'] == 'sandal':
        for sd in 'LR':
            an, to = skel[f'an_{sd}'], skel[f'to_{sd}']
            L._bone_attach(_acc(name, f'sandal_{sd}', _part('sandal', _sandal_mesh), mats['rubber']), arm, f'an_{sd}',
                           Matrix.Translation(Vector(((an.x + to.x) / 2 - 0.01, an.y, 0.006))))
    elif o['feet'].startswith('boot'):
        bt = L._part_mesh('hboot', lambda: L.box_mesh('HBODY_bootfoot', (0.29, 0.12, 0.1), 0.045, 3))
        shm = L._part_mesh('hbootshaft', lambda: L.cyl_mesh('HBODY_bootshaft', 0.066, 0.3, 20, r2=0.06))
        bmat = mats[o['feet']]
        for sd in 'LR':
            an, to = skel[f'an_{sd}'], skel[f'to_{sd}']
            L._bone_attach(_acc(name, f'boot_{sd}', bt, bmat), arm, f'an_{sd}',
                           Matrix.Translation(Vector(((an.x + to.x) / 2 - 0.005, an.y, 0.05))))
            if lower_kind != 'pvc_bib':
                L._bone_attach(_acc(name, f'bootshaft_{sd}', shm, bmat), arm, f'kn_{sd}', Matrix.Translation(Vector((an.x, an.y, 0.24))))
    s = height / 1.72
    arm.location = loc
    arm.rotation_euler = (0, 0, rot_z)
    arm.scale = (s, s, s)
    arm['joints'] = L.JOINTS
    if arm.pose is None or len(arm.pose.bones) == 0:
        bpy.context.view_layer.update()
    L.pose(arm, 'stand')
    nb = arm.pose.bones.get('neck')
    if nb is not None:   # no two heads alike: small differences in head width, depth and length
        nb.scale = (rnd.uniform(0.95, 1.06), rnd.uniform(0.93, 1.07), rnd.uniform(0.95, 1.06))
    return arm


def _moustache_mesh():
    """Thick moustache over the upper lip: a tapered, drooping roll across the face (local Y), front at +X."""
    bm = bmesh.new()
    n, seg = 12, 8
    rings = []
    for i in range(n + 1):
        u = i / n * 2 - 1                         # -1 .. 1 across the lip
        y = u * 0.03
        x = -0.012 * u * u                        # follows the face round
        z = -0.007 * u * u * u * u - 0.003 * abs(u)   # ends droop
        r = 0.0055 * (1 - 0.65 * u * u) + 0.0012
        ring = [bm.verts.new((x + r * 0.7 * math.cos(2 * math.pi * k / seg), y, z + r * math.sin(2 * math.pi * k / seg)))
                for k in range(seg)]
        rings.append(ring)
    for i in range(n):
        for k in range(seg):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    return L.bm_to_mesh(bm, 'HBODY_moustache', smooth=True)


_PARTS = {}


def _part(k, fn):
    if k not in _PARTS:
        _PARTS[k] = fn()
    return _PARTS[k]


def _acc(name, nm, me, mat):
    a = bpy.data.objects.new(f'{name}_{nm}', me)
    L._link(a)
    if not len(me.materials):
        me.materials.append(mat)
    a.material_slots[0].link = 'OBJECT'
    a.material_slots[0].material = mat
    return a


def _body_slots(body, zones):
    """Material slots on the shared body mesh: 0 skin, 1 hands, 2 feet, 3 scalp (hair colour)."""
    if len(body.materials) >= 4:
        return
    while len(body.materials) < 4:
        body.materials.append(None)
    idx = {'hand': 1, 'foot': 2}
    for f in body.polygons:
        cnt = {}
        for vi in f.vertices:
            k = idx.get(zones[vi], 0)
            cnt[k] = cnt.get(k, 0) + 1
        f.material_index = max(cnt, key=cnt.get)


def _cover_group(body, zones, kinds, skel, gname):
    """Vertex group of the skin hidden under the given garment kinds (one ring short of each garment edge)."""
    tmp = bpy.data.objects.new('HCOV_tmp', body)
    bpy.context.scene.collection.objects.link(tmp)
    if gname not in tmp.vertex_groups:
        grp = tmp.vertex_groups.new(name=gname)
        cov = set()
        for kind in kinds:
            cz = GARMENTS[kind]['zones']
            for vi, z in enumerate(zones):
                if z in cz:
                    p = body.vertices[vi].co
                    if z in ('upperarm', 'forearm'):
                        sgn = 'L' if p.y > 0 else 'R'
                        t, _ = _seg_t(p, skel[f'sh_{sgn}'], skel[f'ht_{sgn}'])
                        if t > GARMENTS[kind].get('cuff_t', 1.0) - 0.06:
                            continue
                    if GARMENTS[kind].get('bib') and z == 'torso':
                        continue
                    cov.add(vi)
        # shrink by one edge ring so the garment edge overlaps visible skin
        edge = set()
        for e in body.edges:
            a, b = e.vertices
            if (a in cov) != (b in cov):
                edge.add(a if a in cov else b)
        grp.add(list(cov - edge), 1.0, 'REPLACE')
    bpy.data.objects.remove(tmp)


def _copy_group_names(src_me, dst_me):
    """bmesh keeps the deform weights by group index; give the new mesh the same group names in the same order."""
    a = bpy.data.objects.new('HGRP_a', src_me)
    b = bpy.data.objects.new('HGRP_b', dst_me)
    for g in a.vertex_groups:
        b.vertex_groups.new(name=g.name)
    bpy.data.objects.remove(a)
    bpy.data.objects.remove(b)


def _straps_mesh(skel):
    """Bib-pant braces: two 4 cm bands from the bib top at the front, over the shoulders, down the back."""
    bm = bmesh.new()
    cz = skel['chest'].z + 0.02
    sz = skel['sh_L'].z + 0.045
    for sg in (1, -1):
        path = [(0.135, 0.075, cz), (0.12, 0.085, cz + 0.08), (0.075, 0.095, sz - 0.01), (0.0, 0.1, sz + 0.012),
                (-0.075, 0.095, sz - 0.01), (-0.12, 0.08, cz + 0.06), (-0.125, 0.065, cz - 0.02)]
        rows = []
        for i, (x, y, z) in enumerate(path):
            rows.append([bm.verts.new((x, sg * (y + dy), z)) for dy in (-0.02, 0.02)])
        for i in range(len(rows) - 1):
            bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    uvl = bm.loops.layers.uv.new('rest')
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.x, lp.vert.co.z)
    return L.bm_to_mesh(bm, 'HG_straps', smooth=True)


def _drape(bm, skel, front=True):
    """Within 2 cm columns (by y), torso cloth hangs from the highest protrusion: x never falls back by more than a
    gentle slope below it (removes chest/belly anatomy, keeps the silhouette)."""
    zt, zb = skel['neckb'].z - 0.06, skel['pelvis'].z - 0.05
    sg = 1 if front else -1
    cols = {}
    for v in bm.verts:
        p = v.co
        if zb < p.z < zt and sg * p.x > 0.0 and abs(p.y) < 0.13 and sg * v.normal.x > 0.55:
            cols.setdefault(round(p.y / 0.02), []).append(v)
    for vs in cols.values():
        vs.sort(key=lambda v: -v.co.z)
        best, bz = None, None
        for v in vs:
            x = sg * v.co.x
            if best is not None:
                lim = best - 0.35 * (bz - v.co.z)
                if x < lim:
                    v.co.x = sg * lim
                    x = lim
            if best is None or x > best - 0.35 * (bz - v.co.z):
                best, bz = x, v.co.z


def _hull2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _ray_hull(c, d, hull):
    """Distance along unit 2D direction d from c to the hull boundary."""
    best = None
    n = len(hull)
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        ax, ay = a[0] - c[0], a[1] - c[1]
        t = (ax * ey - ay * ex) / den
        u = (ax * d[1] - ay * d[0]) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6:
            best = t if best is None else max(best, t)
    return best


def _arm_groups(me):
    o = bpy.data.objects.new('HGRP_c', me)
    ids = {g.index for g in o.vertex_groups if g.name[:3] in ('sh_', 'el_', 'wr_')}
    bpy.data.objects.remove(o)
    return ids


def _hull_slices(bm, skel, arm_ids):
    """Torso slices (between hips and armpits, arms excluded) and each leg's slices -> convex hull, verts pushed out."""
    arm_z = skel['sh_L'].z - 0.07
    crotch = skel['pelvis'].z - 0.06
    groups = {}
    dl = bm.verts.layers.deform.active
    for v in bm.verts:
        p = v.co
        if dl is not None:
            dv = v[dl]
            if sum(w for gi, w in dv.items() if gi in arm_ids) > 0.3:
                continue
        if p.z > arm_z or p.z < skel['an_L'].z + 0.05:
            continue
        if p.z > crotch:
            if abs(p.y) > 0.2:
                continue
            k = ('t', round(p.z / 0.015))
        else:
            k = ('L' if p.y > 0 else 'R', round(p.z / 0.015))
        groups.setdefault(k, []).append(v)
    for vs in groups.values():
        if len(vs) < 6:
            continue
        pts = [(v.co.x, v.co.y) for v in vs]
        hull = _hull2d(pts)
        if len(hull) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        for v in vs:
            dx, dy = v.co.x - cx, v.co.y - cy
            r = math.hypot(dx, dy)
            if r < 1e-6:
                continue
            t = _ray_hull((cx, cy), (dx / r, dy / r), hull)
            if t and t > r:
                v.co.x = cx + dx / r * t
                v.co.y = cy + dy / r * t
