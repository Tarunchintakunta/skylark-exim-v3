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
    'plant': ['jacket', 'trousers', 'boots', 'gloves', 'hair', 'haircap', 'mask', 'apron'],   # hairline under the cap
    'plant_coat': ['labcoat', 'trousers', 'boots', 'gloves', 'hair', 'haircap', 'mask'],
    'coldstore': ['parka', 'trousers', 'boots', 'gloves', 'hair', 'haircap', 'mask'],
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


# --- small node helpers (procedural shading on the rest-pose 'rest' attribute: no UVs needed, no swimming)
def _n(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def _in(nt, sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, sock)
    else:
        sock.default_value = v


def _op(nt, op, a, b=0.0, clamp=False):
    n = _n(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    _in(nt, n.inputs[0], a)
    _in(nt, n.inputs[1], b)
    return n.outputs[0]


def _ss(nt, v, lo, hi):
    """smoothstep(lo, hi, v)"""
    n = _n(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    _in(nt, n.inputs['Value'], v)
    n.inputs['From Min'].default_value = lo
    n.inputs['From Max'].default_value = hi
    return n.outputs['Result']


def _rng(nt, v, lo, hi, a, b):
    n = _n(nt, 'ShaderNodeMapRange', clamp=True)
    _in(nt, n.inputs['Value'], v)
    for s, x in zip(('From Min', 'From Max', 'To Min', 'To Max'), (lo, hi, a, b)):
        n.inputs[s].default_value = x
    return n.outputs['Result']


def _col(nt, a, b, fac, blend='MIX'):
    n = _n(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_result=False)
    _in(nt, n.inputs[0], fac)
    _in(nt, n.inputs[6], a if isinstance(a, bpy.types.NodeSocket) else (*a, 1))
    _in(nt, n.inputs[7], b if isinstance(b, bpy.types.NodeSocket) else (*b, 1))
    return n.outputs[2]


def _attr(nt, name):
    return _n(nt, 'ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')


def _noise(nt, vec, scale, detail=2.0, rough=0.5, warp=0.0, sx=(1, 1, 1)):
    if sx != (1, 1, 1):
        mp = _n(nt, 'ShaderNodeVectorMath', operation='MULTIPLY')
        _in(nt, mp.inputs[0], vec)
        mp.inputs[1].default_value = sx
        vec = mp.outputs[0]
    n = _n(nt, 'ShaderNodeTexNoise')
    _in(nt, n.inputs['Vector'], vec)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = warp
    return n.outputs['Fac']


def _vor(nt, vec, scale):
    n = _n(nt, 'ShaderNodeTexVoronoi')
    _in(nt, n.inputs['Vector'], vec)
    n.inputs['Scale'].default_value = scale
    return n


def _bump(nt, h, strength, dist, prev=None):
    b = _n(nt, 'ShaderNodeBump')
    _in(nt, b.inputs['Height'], h)
    _in(nt, b.inputs['Strength'], strength)
    b.inputs['Distance'].default_value = dist
    if prev is not None:
        nt.links.new(prev, b.inputs['Normal'])
    return b.outputs['Normal']


HAIR_RGB = (0.014, 0.011, 0.009)
# South Indian skin, linear base albedo: deep brown .. wheatish; picked per person (Object Info random)
SKIN_TONES = ((0.085, 0.05, 0.032), (0.13, 0.078, 0.048), (0.19, 0.118, 0.074), (0.26, 0.165, 0.105),
              (0.33, 0.215, 0.14))   # dark brown .. medium brown


def _skin_mat():
    """Procedural skin on the rest-pose coordinates ('rest') and the face masks written at build time
    (skm: T-zone, beard, brow, scalp hair; skm2: lips, periorbital, lash line).
    Per person (Object Info random): tone, stubble amount, an occasional short beard, sweat, SSS radius.
    Melanin + redness mottling, sparse dark spots, pores + micro bump at two scales, roughness 0.3-0.6 with an oily
    T-zone coat. Supersedes the ocean lane's _skin_detail (flag set below)."""
    m = bpy.data.materials.get('HUM_Skin')
    if m:
        return m
    m = bpy.data.materials.new('HUM_Skin')
    m.use_nodes = True
    m['ocean_skin'] = 1
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    rest = _attr(nt, 'rest').outputs['Vector']
    s1 = _n(nt, 'ShaderNodeSeparateColor')
    a1 = _attr(nt, 'skm')
    nt.links.new(a1.outputs['Color'], s1.inputs[0])
    tz, beard, brow, scalp = s1.outputs[0], s1.outputs[1], s1.outputs[2], a1.outputs['Alpha']
    s2 = _n(nt, 'ShaderNodeSeparateColor')
    nt.links.new(_attr(nt, 'skm2').outputs['Color'], s2.inputs[0])
    lip, orb, lash = s2.outputs[0], s2.outputs[1], s2.outputs[2]
    r1 = _n(nt, 'ShaderNodeObjectInfo').outputs['Random']
    r2 = _op(nt, 'FRACT', _op(nt, 'MULTIPLY', r1, 7.31))
    r3 = _op(nt, 'FRACT', _op(nt, 'MULTIPLY', r1, 13.7))
    ramp = _n(nt, 'ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].color = (*SKIN_TONES[0], 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (*SKIN_TONES[-1], 1)
    for i, c in enumerate(SKIN_TONES[1:-1], 1):
        cr.elements.new(i / (len(SKIN_TONES) - 1)).color = (*c, 1)
    nt.links.new(r1, ramp.inputs[0])
    c = ramp.outputs[0]
    # mottling: broad melanin patches, mid redness, fine blotch; visible, not a uniform shell
    n_big = _noise(nt, rest, 7.0, 3.0, 0.55)
    n_mid = _noise(nt, rest, 26.0, 5.0, 0.6, warp=0.3)
    n_fine = _noise(nt, rest, 95.0, 4.0, 0.6)
    c = _col(nt, c, (0.62, 0.58, 0.56), _rng(nt, n_big, 0.35, 0.68, 0.0, 1.0), 'MULTIPLY')
    c = _col(nt, c, (1.22, 0.92, 0.82), _rng(nt, n_mid, 0.45, 0.72, 0.0, 0.8), 'MULTIPLY')
    c = _col(nt, c, (0.78, 0.76, 0.74), _rng(nt, n_fine, 0.42, 0.66, 0.0, 0.8), 'MULTIPLY')
    sp = _vor(nt, rest, 70.0)
    sep = _n(nt, 'ShaderNodeSeparateColor')
    nt.links.new(sp.outputs['Color'], sep.inputs[0])
    spot = _op(nt, 'MULTIPLY', _op(nt, 'GREATER_THAN', sep.outputs[0], 0.86),
               _op(nt, 'SUBTRACT', 1.0, _ss(nt, sp.outputs['Distance'], 0.04, 0.12)))
    c = _col(nt, c, (0.62, 0.55, 0.52), _op(nt, 'MULTIPLY', spot, 0.7), 'MULTIPLY')
    c = _col(nt, c, (0.66, 0.60, 0.64), orb, 'MULTIPLY')                  # darker around the eyes
    c = _col(nt, c, (0.78, 0.56, 0.56), _op(nt, 'MULTIPLY', lip, 0.9), 'MULTIPLY')   # darker mauve-brown lips
    # stubble: per-person amount, ~1 in 3 has a short beard
    has_beard = _op(nt, 'GREATER_THAN', r3, 0.66)
    amt = _op(nt, 'MULTIPLY', beard, _op(nt, 'ADD', _op(nt, 'MULTIPLY', r2, 0.55), _op(nt, 'MULTIPLY', has_beard, 0.6)), clamp=True)
    dots = _vor(nt, rest, 1500.0)
    dot = _op(nt, 'SUBTRACT', 1.0, _ss(nt, dots.outputs['Distance'], 0.16, 0.34))
    c = _col(nt, c, (0.50, 0.47, 0.48), amt, 'MULTIPLY')         # shaved shadow
    c = _col(nt, c, HAIR_RGB, _op(nt, 'MULTIPLY', _op(nt, 'MULTIPLY', dot, amt), 0.9))
    bd = _noise(nt, rest, 900.0, 2.0, 0.6, sx=(1, 1, 0.35))                           # short beard hair texture
    c = _col(nt, c, HAIR_RGB, _op(nt, 'MULTIPLY', _op(nt, 'MULTIPLY', has_beard, beard),
                                  _rng(nt, bd, 0.35, 0.6, 0.35, 0.85)))
    # brows: streaks along the brow; lash line; scalp under the hair reads near-black
    st = _noise(nt, rest, 80.0, 2.0, 0.5, sx=(1, 9, 9))
    c = _col(nt, c, HAIR_RGB, _op(nt, 'MULTIPLY', brow, _rng(nt, st, 0.3, 0.62, 0.55, 1.0)))
    c = _col(nt, c, HAIR_RGB, _op(nt, 'MULTIPLY', lash, 0.95))
    hl = _op(nt, 'ADD', scalp, _op(nt, 'MULTIPLY', _op(nt, 'SUBTRACT', _noise(nt, rest, 300.0, 2.0), 0.5), 0.7))
    c = _col(nt, c, (0.02, 0.015, 0.012), _ss(nt, hl, 0.3, 0.75))
    nt.links.new(c, p.inputs['Base Color'])
    # roughness 0.3-0.6, oily T-zone and sweat; lips smoother
    rough = _rng(nt, _noise(nt, rest, 55.0, 3.0), 0.3, 0.7, 0.74, 0.55)
    sweat = _op(nt, 'ADD', 0.12, _op(nt, 'MULTIPLY', r2, 0.18))
    rough = _op(nt, 'SUBTRACT', rough, _op(nt, 'MULTIPLY', tz, _op(nt, 'ADD', sweat, 0.05)))
    rough = _op(nt, 'SUBTRACT', rough, _op(nt, 'MULTIPLY', lip, 0.12))
    nt.links.new(_op(nt, 'MAXIMUM', rough, 0.28), p.inputs['Roughness'])
    nt.links.new(_op(nt, 'MULTIPLY', tz, _op(nt, 'MULTIPLY', sweat, 1.4)), p.inputs['Coat Weight'])
    p.inputs['Coat Roughness'].default_value = 0.32
    p.inputs['Coat IOR'].default_value = 1.38
    p.inputs['Specular IOR Level'].default_value = 0.28
    # SSS: darker skin scatters less and shorter; radius per person
    p.inputs['Subsurface Weight'].default_value = 0.28
    p.inputs['Subsurface Radius'].default_value = (1.0, 0.40, 0.22)
    nt.links.new(_op(nt, 'ADD', 0.0035, _op(nt, 'MULTIPLY', r3, 0.003)), p.inputs['Subsurface Scale'])
    # bump: pores (Voronoi pits ~1 mm), micro grain, fine creases; stubble roughens the jaw
    nolip = _op(nt, 'SUBTRACT', 1.0, lip)
    pores = _vor(nt, rest, 700.0)
    pv = _rng(nt, _noise(nt, rest, 30.0, 2.0), 0.35, 0.65, 0.15, 0.6)
    b = _bump(nt, _ss(nt, pores.outputs['Distance'], 0.0, 0.45), _op(nt, 'MULTIPLY', nolip, pv), 0.0005)
    b = _bump(nt, _noise(nt, rest, 2200.0, 2.0), 0.35, 0.00025, b)
    b = _bump(nt, _noise(nt, rest, 110.0, 5.0, 0.6, sx=(1, 1, 3)), 0.16, 0.0007, b)
    b = _bump(nt, _op(nt, 'MULTIPLY', dot, amt), 0.35, 0.0003, b)
    b = _bump(nt, _op(nt, 'MULTIPLY', lip, _noise(nt, rest, 160.0, 2.0, 0.5, sx=(6, 1, 0.4))), 0.5, 0.0005, b)
    nt.links.new(b, p.inputs['Normal'])
    return m


def _eye_mat():
    """Eye from the rest-space direction to its own centre ('eyec'): warm sclera with redder corners, dark brown iris
    (11.7 mm) with a limbal ring and radial fibres, black pupil, a glossy wet coat for the catchlight."""
    m = bpy.data.materials.get('HUM_Eye')
    if m:
        return m
    m = bpy.data.materials.new('HUM_Eye')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    rest = _attr(nt, 'rest').outputs['Vector']
    d = _n(nt, 'ShaderNodeVectorMath', operation='SUBTRACT')
    nt.links.new(rest, d.inputs[0])
    nt.links.new(_attr(nt, 'eyec').outputs['Vector'], d.inputs[1])
    nd = _n(nt, 'ShaderNodeVectorMath', operation='NORMALIZE')
    nt.links.new(d.outputs[0], nd.inputs[0])
    sx = _n(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(nd.outputs[0], sx.inputs[0])
    fwd = _op(nt, 'ADD', _op(nt, 'MULTIPLY', sx.outputs['Y'], -0.994), _op(nt, 'MULTIPLY', sx.outputs['Z'], 0.11))
    c = _col(nt, (0.36, 0.31, 0.26), (0.40, 0.20, 0.17), _rng(nt, fwd, 0.35, 0.75, 0.5, 0.0))   # sclera, red corners
    c = _col(nt, c, (0.45, 0.42, 0.42), _ss(nt, sx.outputs['Z'], 0.05, 0.4), 'MULTIPLY')        # upper lid shadow
    fib = _noise(nt, nd.outputs[0], 60.0, 3.0, 0.6, sx=(1, 0.2, 1))
    iris = _col(nt, (0.035, 0.018, 0.010), (0.085, 0.045, 0.022), _rng(nt, fib, 0.35, 0.65, 0.0, 1.0))
    c = _col(nt, c, (0.03, 0.022, 0.018), _ss(nt, fwd, 0.815, 0.83))      # limbal ring
    c = _col(nt, c, iris, _ss(nt, fwd, 0.835, 0.85))
    c = _col(nt, c, (0.004, 0.004, 0.004), _ss(nt, fwd, 0.975, 0.98))    # pupil
    nt.links.new(c, p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.12
    p.inputs['Coat Weight'].default_value = 1.0
    p.inputs['Coat Roughness'].default_value = 0.0
    p.inputs['Coat IOR'].default_value = 1.376
    p.inputs['Specular IOR Level'].default_value = 0.6
    p.inputs['Subsurface Weight'].default_value = 0.15
    p.inputs['Subsurface Radius'].default_value = (1.0, 0.5, 0.4)
    p.inputs['Subsurface Scale'].default_value = 0.002
    return m


def _hair_mat():
    """Short black hair cards: per-card tone ('strand'), oiled sheen."""
    m = bpy.data.materials.get('HUM_Hair')
    if m:
        return m
    m = bpy.data.materials.new('HUM_Hair')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    s = _attr(nt, 'strand').outputs['Fac']
    c = _col(nt, (0.006, 0.005, 0.0045), (0.04, 0.03, 0.022), _rng(nt, s, 0.0, 1.0, 0.0, 0.7))
    nt.links.new(c, p.inputs['Base Color'])
    nt.links.new(_rng(nt, s, 0.0, 1.0, 0.58, 0.78), p.inputs['Roughness'])
    p.inputs['Coat Weight'].default_value = 0.0
    p.inputs['Specular IOR Level'].default_value = 0.35
    p.inputs['Specular IOR Level'].default_value = 0.5
    return m


RUBBER = ((0.62, 0.15, 0.02), (0.60, 0.44, 0.03), (0.025, 0.05, 0.14), (0.62, 0.15, 0.02), (0.03, 0.06, 0.16))


def _glove_detail(m, palette=None):
    """Gloves read as rubber/nitrile, not a mannequin hand: knuckle creases (the 'crease' attribute copied from the
    hand), crinkle grain, roughness variation, a wet coat. Works on any glove material (the ocean lane swaps its own)."""
    if m is None or m.get('glove_detail'):
        return m
    m['glove_detail'] = 1
    if palette:                                  # rubber gloves: orange / yellow / dark blue, not a bare dark hand
        _palette(m, palette)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    rest = _attr(nt, 'rest').outputs['Vector']
    cr = _attr(nt, 'crease').outputs['Fac']
    lk = p.inputs['Normal'].links
    prev = lk[0].from_socket if lk else None
    wr = _noise(nt, rest, 420.0, 3.0, 0.6, sx=(1, 1, 4))
    b = _bump(nt, _op(nt, 'MULTIPLY', cr, wr), 1.0, 0.0022, prev)
    b = _bump(nt, _noise(nt, rest, 1800.0, 2.0), 0.25, 0.00025, b)
    nt.links.new(b, p.inputs['Normal'])
    src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else p.inputs['Base Color'].default_value[:3]
    c = _col(nt, src, (0.72, 0.72, 0.72), _op(nt, 'MULTIPLY', cr, _rng(nt, wr, 0.4, 0.7, 0.0, 0.8)), 'MULTIPLY')
    nt.links.new(c, p.inputs['Base Color'])
    nt.links.new(_rng(nt, _noise(nt, rest, 40.0, 3.0), 0.3, 0.7, 0.34, 0.6), p.inputs['Roughness'])
    p.inputs['Coat Weight'].default_value = 0.3
    p.inputs['Coat Roughness'].default_value = 0.18
    p.inputs['Specular IOR Level'].default_value = 0.45
    return m


def _boot_mat():
    """White gumboots as worn rubber: off-white, dark sole band, grime rising from the ground, scuffs, ankle creases."""
    m = bpy.data.materials.get('HUM_WhiteBoot')
    if m:
        return m
    m = bpy.data.materials.new('HUM_WhiteBoot')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    rest = _attr(nt, 'rest').outputs['Vector']
    z = _n(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(rest, z.inputs[0])
    z = z.outputs['Z']
    n1 = _noise(nt, rest, 18.0, 4.0, 0.6)
    c = _col(nt, (0.66, 0.66, 0.61), (0.54, 0.55, 0.52), _rng(nt, n1, 0.35, 0.65, 0.0, 1.0))
    grime = _op(nt, 'MULTIPLY', _op(nt, 'SUBTRACT', 1.0, _ss(nt, z, 0.02, 0.16)), _rng(nt, n1, 0.3, 0.7, 0.55, 1.0))
    c = _col(nt, c, (0.20, 0.17, 0.13), grime)
    scuff = _rng(nt, _noise(nt, rest, 140.0, 3.0, 0.6), 0.6, 0.72, 0.0, 0.5)
    c = _col(nt, c, (0.32, 0.30, 0.27), scuff)
    c = _col(nt, c, (0.035, 0.032, 0.03), _op(nt, 'SUBTRACT', 1.0, _ss(nt, z, 0.022, 0.03)))   # sole
    nt.links.new(c, p.inputs['Base Color'])
    nt.links.new(_rng(nt, n1, 0.3, 0.7, 0.32, 0.6), p.inputs['Roughness'])
    p.inputs['Coat Weight'].default_value = 0.2
    p.inputs['Coat Roughness'].default_value = 0.25
    band = _op(nt, 'MULTIPLY', _op(nt, 'SINE', _op(nt, 'MULTIPLY', z, 260.0)),
               _op(nt, 'MULTIPLY', _ss(nt, z, 0.09, 0.13), _op(nt, 'SUBTRACT', 1.0, _ss(nt, z, 0.2, 0.26))))
    b = _bump(nt, _op(nt, 'MULTIPLY', band, _noise(nt, rest, 9.0)), 0.5, 0.002)
    b = _bump(nt, _noise(nt, rest, 600.0, 2.0), 0.12, 0.0003, b)
    nt.links.new(b, p.inputs['Normal'])
    return m


def _palette(m, colors):
    """Per-person colour from a small palette (Object Info random, constant steps) into Base Color."""
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].color = (*colors[0], 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (*colors[-1], 1)
    for i, c in enumerate(colors[1:-1], 1):
        e = cr.elements.new(i / len(colors))
        e.color = (*c, 1)
    nt.links.new(oi.outputs['Random'], ramp.inputs[0])
    for lk in list(p.inputs['Base Color'].links):
        nt.links.remove(lk)
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    return m


def _hairnet(m):
    """Disposable non-woven bouffant cap: crinkled (noise bump) with soft creases darkening the palette colour.
    (A wave-grid net aliased into contour rings / grey curls at 1080, so no hair shows through.)"""
    nt = m.node_tree
    L = nt.links
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    src = p.inputs['Base Color'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 45.0
    nz.inputs['Detail'].default_value = 10.0
    nz.inputs['Distortion'].default_value = 0.4
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    cm = nt.nodes.new('ShaderNodeMix')
    cm.data_type = 'RGBA'
    cm.blend_type = 'MULTIPLY'
    L.new(nz.outputs['Fac'], cm.inputs[0])
    L.new(src, cm.inputs[6])
    cm.inputs[7].default_value = (0.8, 0.8, 0.82, 1)       # creases
    L.new(cm.outputs[2], p.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.55
    bp.inputs['Distance'].default_value = 0.002
    L.new(nz.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs[0], p.inputs['Normal'])
    return m


def _stache_mat():
    """Moustache cards on about 60 % of the men (Object Info random > 0.4), hidden on the rest."""
    m = bpy.data.materials.get('HUM_Stache')
    if m:
        return m
    m = _mat('HUM_Stache', HAIR_RGB, 0.65, bump=0.25)
    nt = m.node_tree
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.4                      # ~60 % of men
    nt.links.new(oi.outputs['Random'], gt.inputs[0])
    nt.links.new(gt.outputs[0], nt.nodes['Principled BSDF'].inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    return m


def mats():
    fab = CC0 + '/tex/Fabric030/Fabric030_2K-JPG_NormalGL.jpg'
    fab2 = CC0 + '/tex/Fabric061/Fabric061_2K-JPG_NormalGL.jpg'
    return {
        'skin': _skin_mat(),
        'eye': _eye_mat(),
        'white_cotton': _palette(_mat('HUM_WhiteCotton', (0.6, 0.61, 0.6), 0.85, sheen=0.3, bump=0.12, rand=0.04,
                                      wrinkle=0.6, normal_tex=fab, tex_scale=45.0),
                                 ((0.06, 0.09, 0.2), (0.3, 0.05, 0.07), (0.62, 0.63, 0.62), (0.08, 0.2, 0.32),
                                  (0.12, 0.25, 0.16), (0.6, 0.62, 0.63))),   # navy, maroon, white, teal-blue, green: roles by colour
        'white_pvc': _palette(_mat('HUM_WhitePVC', (0.84, 0.86, 0.86), 0.32, coat=0.3, bump=0.02),
                              ((0.80, 0.82, 0.82), (0.30, 0.48, 0.62), (0.34, 0.07, 0.08), (0.80, 0.82, 0.82),
                               (0.16, 0.38, 0.30))),   # aprons: white / blue / maroon / green by person
        'boot': _boot_mat(),
        'nitrile_blue': _mat('HUM_NitrileBlue', (0.10, 0.22, 0.48), 0.38, coat=0.25, rand=0.06),
        'cap_white': _hairnet(_palette(_mat('HUM_CapNonwoven', (0.74, 0.75, 0.77), 0.95, sheen=0.4, bump=0.25),
                                       ((0.74, 0.75, 0.77), (0.42, 0.58, 0.74), (0.74, 0.75, 0.77), (0.36, 0.56, 0.40),
                                        (0.74, 0.75, 0.77), (0.70, 0.45, 0.50)))),   # caps by role: white, blue, green, pink
        'mask_blue': _mat('HUM_MaskBlue', (0.55, 0.70, 0.80), 0.9, sheen=0.3, bump=0.15),
        'parka': _mat('HUM_ParkaNavy', (0.10, 0.14, 0.22), 0.55, coat=0.1, bump=0.12, wrinkle=0.45),
        'shirt_blue': _mat('HUM_ShirtBlue', (0.22, 0.30, 0.42), 0.8, sheen=0.2, bump=0.12, rand=0.15, wrinkle=0.45),
        'trousers_dark': _mat('HUM_TrouserDark', (0.08, 0.08, 0.09), 0.75, bump=0.1, rand=0.2, wrinkle=0.45),
        'shoe': _mat('HUM_Shoe', (0.05, 0.045, 0.04), 0.45, coat=0.2),
        'stache': _stache_mat(),
        'hair': _hair_mat(),
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
    HZ = None
    if piece in ('haircap', 'cap') and 'hairz' in body.data.attributes:
        HZ = [d.value for d in body.data.attributes['hairz'].data]
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
        elif piece in ('haircap', 'cap') and HZ is not None:
            # follows the smooth hairline (no staircase, no ear flap): the bouffant covers the hairline,
            # a cloth cap sits above it so hair shows under the rim
            sel = HZ[v.index] > (-0.012 if piece == 'haircap' else 0.012) and z > 1.45
        elif piece == 'haircap':
            sel = (z > 1.60) or (z > 1.49 and n.y > 0.1 and ax < 0.10) or (z > 1.545 and ax > 0.055 and n.y > -0.3)
            sel = sel and ax < 0.125 and not (1.5 * KH < z < 1.61 * KH and ax > 0.066 * KH)   # ears stay out
        elif piece in ('hair', 'cap'):
            sel = ((z > 1.60) or (z > 1.52 and n.y > 0.3) or (z > 1.56 and ax > 0.06 and n.y > -0.2)) and ax < 0.12
            sel = sel and not (z < 1.605 and ax > 0.07)        # ears stay bare
            if piece == 'cap':
                sel = z > 1.60 and ax < 0.12
        elif piece == 'mask':
            sel = 1.462 < z < 1.552 and ax < 0.078 and n.y < 0.2    # nostril/lip undersides too: no holes
        elif piece == 'stache':
            sel = STACHE[0] < z < STACHE[1] and ax < STACHE[2] and n.y < -0.12
        elif piece == 'vest':
            sel = 0.93 < z < 1.43 and ax < 0.17 and not arm
        out.append(sel)
    return out


STACHE = (1.505, 1.517, 0.030)       # upper lip band (z lo, z hi, half width) on the rest mesh
SLEEVE = {'jacket': 0.545, 'parka': 0.55, 'labcoat': 0.535, 'shirt': 0.17, 'shirt_farm': 0.31}
CUFF = ('shirt_farm', 'trousers_rolled', 'jacket', 'labcoat', 'parka', 'haircap', 'shirt', 'trousers', 'trousers_dark',
        'shorts', 'gloves')
LOOSE = 1.05          # loose cloth stands off the body by THICK * LOOSE (was 1.6: vests and oilskins ballooned)
RELAX_CURL = 0.22     # finger curl baked into the masters: relaxed hands
THICK = {'jacket': 0.028, 'parka': 0.05, 'shirt': 0.03, 'shirt_farm': 0.03, 'labcoat': 0.032, 'trousers': 0.02,
         'trousers_dark': 0.016, 'trousers_rolled': 0.016, 'shorts': 0.018, 'boots': 0.016, 'shoes': 0.008,
         'gloves': 0.0009, 'gloves_rubber': 0.0015, 'haircap': 0.022, 'hair': 0.008, 'cap': 0.02, 'mask': 0.008,
         'vest': 0.024, 'stache': 0.0012}
PMAT = {'jacket': 'white_cotton', 'labcoat': 'white_cotton', 'parka': 'parka', 'shirt': 'shirt_blue',
        'shirt_farm': 'shirt_farm', 'trousers': 'white_cotton', 'trousers_dark': 'trousers_dark',
        'trousers_rolled': 'trousers_dark', 'shorts': 'shorts', 'boots': 'boot', 'shoes': 'shoe',
        'gloves': 'nitrile_blue', 'gloves_rubber': 'rubber_glove', 'haircap': 'cap_white', 'hair': 'hair',
        'cap': 'cap_cloth', 'mask': 'mask_blue', 'vest': 'hivis', 'apron': 'white_pvc', 'stache': 'stache'}


KH = 1.0
# neckline plane per top: (height at the neck centre, front-to-back rise per metre of y)
NECK = {'jacket': (1.452, 0.30), 'parka': (1.462, 0.30), 'shirt': (1.452, 0.30), 'shirt_farm': (1.452, 0.30),
        'labcoat': (1.452, 0.30), 'vest': (1.425, 0.45)}


def _sm1(x, lo, hi):
    t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def _shell(body, piece, mask, M):
    """Copy of the body faces inside mask, pushed out along normals (+ fabric folds), solidified.
    'hair' is no longer a shell (it read as a helmet): an empty piece here, hair cards are grown per outfit."""
    if piece == 'hair':
        o = bpy.data.objects.new('%s_hair' % body.name, bpy.data.meshes.new('%s_hair' % body.name))
        bpy.context.scene.collection.objects.link(o)
        return o
    me = body.data.copy()
    o = bpy.data.objects.new('%s_%s' % (body.name, piece), me)
    bpy.context.scene.collection.objects.link(o)
    for vg in body.vertex_groups:
        o.vertex_groups.new(name=vg.name)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    nk = NECK.get(piece)
    if nk is not None:
        # tops: keep a band above the stepped region cut, then slice one clean neckline plane through it
        # (lower at the front, higher at the back): a smooth collar edge, no stair steps
        band = [nk[0] * KH - 0.06 < v.co.z < nk[0] * KH + 0.06 and abs(v.co.x) < 0.13 * KH for v in bm.verts]
        kill = [f for f in bm.faces if not all(mask[v.index] or band[v.index] for v in f.verts)]
    else:
        kill = [f for f in bm.faces if not all(mask[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    if nk is not None:
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5,
                               plane_co=(0, 0, nk[0] * KH), plane_no=Vector((0, -nk[1], 1)).normalized(),
                               clear_outer=True)
    for _ in range(3):                      # drop one-face slivers and tags hanging off the border
        thin = [f for f in bm.faces if sum(1 for e in f.edges if e.is_boundary) >= 2]
        if not thin:
            break
        bmesh.ops.delete(bm, geom=thin, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    t = THICK[piece]
    loose_cloth = piece in ('jacket', 'parka', 'shirt', 'shirt_farm', 'labcoat', 'trousers', 'trousers_dark',
                            'trousers_rolled', 'shorts', 'vest', 'boots', 'shoes')
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    bnd = [v for v in bm.verts if v.is_boundary]
    for _ in range(30):                     # straighten the hem line (1D smoothing along the border): no ragged cuffs
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
    # relax the first rows inside the hem so the straightened border has even faces behind it
    near = set()
    front_ = set(bnd)
    for _ in range(3):
        front_ = {e.other_vert(v) for v in front_ for e in v.link_edges} - set(bnd) - near
        near |= front_
    if near:
        for _ in range(8):
            bmesh.ops.smooth_vert(bm, verts=list(near), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for v in near:
            hit, _n, _i, _d = bvh.find_nearest(v.co)
            if hit is not None:
                v.co = hit
    # distance to the hem (continuous, so cuff bands are smooth, not stepped by the mesh rings)
    from mathutils.kdtree import KDTree
    rd = {}
    if bnd:
        kd = KDTree(len(bnd))
        for i, v in enumerate(bnd):
            kd.insert(v.co, i)
        kd.balance()
        for v in bm.verts:
            _c, _i, dd = kd.find(v.co)
            if dd < 0.02:
                rd[v] = dd
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
        hem = {'labcoat': 0.018, 'parka': 0.02, 'vest': 0.026}.get(piece, 0.010)   # vest sits over the shirt
        for v in bm.verts:
            v.co += v.normal * (hem if v.is_boundary else t * LOOSE)
        inner = [v for v in bm.verts if not v.is_boundary]
        for it in range(4):
            for _ in range(20):
                bmesh.ops.smooth_vert(bm, verts=inner, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            # smoothing shrinks the shell into the body: re-inflate to keep clearance
            for v in inner:
                hit, nrm, _i, d = bvh.find_nearest(v.co)
                clr = 0.018 if piece in ('boots', 'shoes') else 0.007      # boots: no toes showing through
                if hit is not None and d < clr:
                    v.co = hit + nrm * clr
        if piece in ('boots', 'shoes'):           # boot / shoe toe box: hull of the foot, no toes
            zc = (0.15 if piece == 'boots' else 0.06) * KH
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.z < zc for v in f.verts)], context='FACES')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
            for sx in (-1, 1):
                pts = [v.co.copy() for v in body.data.vertices if v.co.z < zc + 0.02 and v.co.x * sx > 0]
                if len(pts) < 8:
                    continue
                ctr = sum(pts, Vector()) / len(pts)
                new = [bm.verts.new(ctr + (q - ctr) * 1.0 + (q - ctr).normalized() * 0.007) for q in pts]   # hugs the foot
                hull = bmesh.ops.convex_hull(bm, input=new)
                loose = {g for g in hull.get('geom_interior', []) + hull.get('geom_unused', [])
                         if isinstance(g, bmesh.types.BMVert)}
                bmesh.ops.delete(bm, geom=list(loose), context='VERTS')
            inner = [v for v in bm.verts if not v.is_boundary]
        bm.normal_update()
        t = 0.006
    cl = bm.verts.layers.float.get('crease')
    for v in bm.verts:
        z = v.co.z
        extra = 0.0
        if cl is not None and piece in ('gloves', 'gloves_rubber'):
            extra -= 0.0016 * v[cl]                     # glove pinches into the knuckle creases: jointed, not sausages
        if piece in ('labcoat',) and z < 0.95:
            extra = (0.95 - z) * 0.10  # skirt flares a little
        if piece == 'haircap':
            # bouffant: fuller toward the crown and back, gathered pleats
            a = math.atan2(v.co.y, v.co.x)
            extra = 0.010 * max(0.0, (z - 1.52) / 0.2) + 0.006 * max(0.0, v.co.y) / 0.1 \
                + 0.004 * math.sin(a * 26) * max(0.0, (z - 1.56) / 0.12)
        if piece in CUFF and v in rd and piece != 'haircap':
            cuffw = 0.0028 if piece.startswith('gloves') else 0.006
            extra += cuffw * (1 - _sm1(rd[v], 0.004, 0.016))                # turned-back hem / cuff band
        if piece in ('haircap', 'cap') and v in rd:
            extra += 0.005 * (1 - _sm1(rd[v], 0.002, 0.012))                # elastic edge
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
    if piece == 'mask':                     # rebuilt as a smooth pleated panel over the face (no moulded nose/lips)
        bm.clear()
        nx, nz = 26, 14
        x0, x1, z0, z1 = -0.062 * KH, 0.062 * KH, 1.458 * KH, 1.556 * KH
        hits = {}
        for ix in range(nx + 1):
            for iz in range(nz + 1):
                x = x0 + (x1 - x0) * ix / nx
                zb = z0 + 0.03 * KH * (x / x1) ** 2              # lower edge rises along the jaw to the sides
                z = zb + (z1 - zb) * iz / nz
                h = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
                if h[0] is None:
                    h = bvh.find_nearest(Vector((x, -0.06 * KH, z)))
                if h[0] is not None:
                    hits[ix, iz] = h[0].y
        # conforms to the face 5 mm off: depth field blurred so it bridges the nose and lips (no moulded features)
        # but follows cheeks and chin; never closer than 3 mm; three horizontal pleats
        fy = dict(hits)
        for _ in range(6):
            fy = {k: sum(fy.get((k[0] + a, k[1] + b), fy[k]) for a in (-1, 0, 1) for b in (-1, 0, 1)) / 9 for k in fy}
        grid = {}
        for (ix, iz), y0 in hits.items():
            x = x0 + (x1 - x0) * ix / nx
            zb = z0 + 0.03 * KH * (x / x1) ** 2
            z = zb + (z1 - zb) * iz / nz
            pleat = 0.0016 * math.sin((z - z0) / (z1 - z0) * math.pi * 6) * (1 - abs(x) / x1) ** 0.5
            grid[ix, iz] = bm.verts.new((x, min(fy[ix, iz] - 0.009, y0 - 0.007, -0.035 * KH) - pleat, z))   # sides stand off, no flaps
        for ix in range(nx):
            for iz in range(nz):
                q = [grid.get(k) for k in ((ix, iz), (ix + 1, iz), (ix + 1, iz + 1), (ix, iz + 1))]
                if all(q):
                    bm.faces.new(q)
        # thin elastic ear loops: corner -> over the ear root -> behind the ear -> lower corner
        ears = [v.co for v in body.data.vertices if 1.53 * KH < v.co.z < 1.60 * KH and v.co.x > 0 and v.co.y > -0.06]
        ear = max(ears, key=lambda c: c.x) if ears else Vector((0.075 * KH, 0.0, 1.565 * KH))
        for sx, ix in ((-1, 0), (1, nx)):
            a, b = grid.get((ix, nz)), grid.get((ix, 0))
            if a is None or b is None:
                continue
            e = Vector((sx * ear.x, ear.y, ear.z))
            path = [a.co.copy(), Vector((sx * (ear.x - 0.006), ear.y - 0.012, ear.z + 0.022)),
                    Vector((sx * (ear.x - 0.009), ear.y + 0.012, ear.z + 0.026)),
                    Vector((sx * (ear.x - 0.012), ear.y + 0.028, ear.z)),
                    Vector((sx * (ear.x - 0.009), ear.y + 0.014, ear.z - 0.026)), b.co.copy()]
            rows = []
            for i, c in enumerate(path):
                d = (path[min(i + 1, 5)] - path[max(i - 1, 0)]).normalized()
                side = d.cross(Vector((sx, 0, 0))).normalized() * 0.0012
                rows.append((bm.verts.new(c - side), bm.verts.new(c + side)))
            for (p0, p1), (q0, q1) in zip(rows, rows[1:]):
                bm.faces.new((p0, p1, q1, q0))
        bm.normal_update()
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
    sol.thickness = {'gloves': 0.0009, 'gloves_rubber': 0.0011}.get(piece, 0.0065 if piece not in ('mask', 'stache') else 0.0018)
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
            hang = max(0.0, (0.98 * k - z) / (0.46 * k))              # 0 at the waist .. 1 at the hem
            fold = 0.009 * hang * math.sin((x / (w * k)) * math.pi * 2.6 + 0.4) + 0.006 * hang * math.sin(x * 61 / k)
            flare = 0.012 * hang ** 2 * (abs(x) / (w * k))            # hem swings out a little at the sides
            row.append(bm.verts.new((x * (1 + 0.06 * hang), y + 0.02 * (abs(x) / (w * k)) ** 2 - fold - flare, z)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    # neck strap (top corners up round the neck); no loose waist ties (they floated beside the hands)
    for sx in (-1, 1):
        top = grid[-1][0 if sx < 0 else nx].co
        nk = Vector((sx * 0.055 * k, top.y + 0.05 * k, 1.46 * k))
        st = []
        for t in (0.0, 0.5, 1.0):
            c = top.lerp(nk, t)
            st.append((bm.verts.new(c + Vector((-0.006 * k, 0, 0))), bm.verts.new(c + Vector((0.006 * k, 0, 0)))))
        for (a0, a1), (b0, b1) in zip(st, st[1:]):
            bm.faces.new((a0, a1, b1, b0))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
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


def _close_mouth(body):
    """Pull the mouth bag (verts behind the lip line) forward to just behind the lips: closed mouth, no black hole."""
    vs = [v for v in body.data.vertices if abs(v.co.x) < 0.03 * KH and 1.468 * KH < v.co.z < 1.508 * KH]
    if not vs:
        return
    front = min(v.co.y for v in vs)
    lips = [v for v in vs if v.co.y < front + 0.012]
    if not lips:
        return
    lip_y = sum(v.co.y for v in lips) / len(lips)
    for v in vs:
        if v.co.y > lip_y + 0.004 and abs(v.co.x) < 0.024 * KH:
            v.co.y = lip_y + 0.004 + (v.co.y - lip_y) * 0.05


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


def _sm(x, lo, hi):
    import numpy as np
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _landmarks(body, eyes):
    """Eye centre (left side, +x), nose tip, ear (lateral-most point at eye height) on the rest mesh."""
    import numpy as np
    E = [sum((v.co for v in e.data.vertices), Vector()) / len(e.data.vertices) for e in eyes]
    E = max(E, key=lambda c: c.x)
    co = np.array([v.co[:] for v in body.data.vertices])
    face = (co[:, 2] > E.z - 0.06) & (co[:, 2] < E.z + 0.02) & (np.abs(co[:, 0]) < 0.01)
    nose = co[face][np.argmin(co[face][:, 1])]
    band = (co[:, 2] > E.z - 0.04) & (co[:, 2] < E.z + 0.01) & (co[:, 0] > 0) & (co[:, 0] < 0.11)
    ear = co[band][np.argmax(co[band][:, 0])]
    return E, Vector(nose), Vector(ear), co


def _face_maps(body, eyes, gender='male'):
    """Per-vertex masks for the skin shader (rest pose): skm = (T-zone, beard, brow, scalp hair),
    skm2 = (lips, periorbital, lash line, 0); 'rest' = rest position (stable texture space under the rig);
    eyes get 'eyec' (their own centre) for the iris."""
    import numpy as np
    E, nose, ear, co = _landmarks(body, eyes)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    Ex, Ey, Ez = E
    front = 1 - _sm(y, ear.y - 0.02, ear.y + 0.005)
    # T-zone: forehead centre + nose + point of the chin
    fz = (1 - _sm(ax, 0.025, 0.05)) * _sm(z, Ez + 0.012, Ez + 0.025) * (1 - _sm(z, Ez + 0.055, Ez + 0.075))
    nz_ = (1 - _sm(ax, 0.008, 0.02)) * _sm(z, Ez - 0.052, Ez - 0.04) * (1 - _sm(z, Ez, Ez + 0.012)) * (y < Ey - 0.01)
    cz = 0.6 * (1 - _sm(ax, 0.01, 0.025)) * _sm(z, Ez - 0.128, Ez - 0.118) * (1 - _sm(z, Ez - 0.105, Ez - 0.095))
    tz = np.maximum.reduce([fz * front, nz_, cz * (y < Ey)])
    # lips: ellipse round the mouth, only the front-most surface
    zm = nose.z - 0.04
    lipr = (x / 0.024) ** 2 + ((z - zm) / 0.013) ** 2
    lip = (1 - _sm(lipr, 0.6, 1.1)) * (y < nose.y + 0.03)
    # beard: below the line nose wing -> sideburn, above the throat, in front of the ear
    U = np.where(ax < 0.02, nose.z - 0.012, nose.z - 0.012 + (ax - 0.02) * 0.75)
    beard = _sm(U - z, 0.0, 0.006) * _sm(z, Ez - 0.17, Ez - 0.145) * (1 - _sm(y, ear.y - 0.022, ear.y - 0.005))
    beard *= (1 - lip) * (1 - _sm(ax, ear.x - 0.012, ear.x - 0.004))
    # brows
    u = ax - Ex
    zb = Ez + 0.017 + 0.005 * (1 - ((u - 0.003) / 0.026) ** 2)
    th = 0.0048 - 0.0018 * np.clip((u + 0.022) / 0.05, 0, 1)
    brow = (1 - _sm(np.abs(z - zb) / th, 0.55, 1.15)) * _sm(u, -0.025, -0.018) * (1 - _sm(u, 0.022, 0.031))
    brow *= (y < Ey + 0.006)
    # around the eyes
    r = np.sqrt((ax - Ex) ** 2 + ((z - Ez) * 1.25) ** 2)
    orb = _sm(r, 0.011, 0.015) * (1 - _sm(r, 0.021, 0.034)) * np.where(z < Ez, 1.0, 0.55) * (y < Ey + 0.008)
    lash = _sm(r, 0.0108, 0.0122) * (1 - _sm(r, 0.0138, 0.0158)) * (y < Ey - 0.002)
    lash *= np.where(z > Ez - 0.002, 1.0, 0.35)
    # moustache: upper lip between the nose base and the lip line
    stache = (1 - _sm(ax, 0.024, 0.034)) * _sm(z, zm + 0.004, zm + 0.009) * (1 - _sm(z, nose.z - 0.016, nose.z - 0.008))
    stache *= (y < nose.y + 0.035)
    if gender != 'male':
        beard = beard * 0
        stache = stache * 0
    # scalp hair: hairline height by azimuth round the head (front .. nape), ears cut out, sideburns
    sl = (ax < 0.01) & (np.abs(z - Ez - 0.03) < 0.006)
    hcy = (y[sl].min() + y[sl].max()) / 2 if sl.any() else Ey + 0.08
    az = np.abs(np.arctan2(x, -(y - hcy))) / math.pi              # 0 front .. 1 back
    H = np.interp(az, [0.0, 0.12, 0.2, 0.3, 0.36, 0.5, 0.7, 1.0],
                  np.array([0.080, 0.074, 0.058, 0.036, 0.004, 0.012, -0.03, -0.088]) * KH + Ez)
    scalp = _sm(z, H - 0.002, H + 0.008) * (ax < 0.125 * KH)
    earcut = _sm(ax, ear.x - 0.022, ear.x - 0.014) * (np.abs(y - ear.y) < 0.032) * (z > Ez - 0.05) * (z < Ez + 0.03)
    scalp *= 1 - earcut
    me = body.data
    hz = me.attributes.get('hairz') or me.attributes.new('hairz', 'FLOAT', 'POINT')
    hz.data.foreach_set('value', np.where(earcut > 0.3, -1.0, (z - H) / KH).astype(np.float32))   # ears stay out of caps
    for nm, vals in (('skm', np.stack([tz, beard, brow, scalp], 1)),
                     ('skm2', np.stack([lip, orb, lash, stache], 1))):
        a = me.attributes.get(nm) or me.attributes.new(nm, 'FLOAT_COLOR', 'POINT')
        a.data.foreach_set('color', np.clip(vals, 0, 1).astype(np.float32).ravel())
    for o in [body] + list(eyes):
        a = o.data.attributes.get('rest') or o.data.attributes.new('rest', 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set('vector', np.array([v.co[:] for v in o.data.vertices], np.float32).ravel())
    for e in eyes:
        c = sum((v.co for v in e.data.vertices), Vector()) / len(e.data.vertices)
        a = e.data.attributes.new('eyec', 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set('vector', np.tile(np.array(c[:], np.float32), len(e.data.vertices)))
    return E, nose, ear


FACE_BONES = ('face.L', 'face.R', 'nose', 'jaw')


def _face_rig(body, ao, E, nose, ear):
    """Four small face bones under 'head' (cheek/mouth halves, nose, jaw) so each person gets an asymmetric,
    broader-nosed face by bone scale (person()); the eyes stay on 'head'."""
    import numpy as np
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ao.data.edit_bones
    heads = {'face.L': (E.x, E.y + 0.012, E.z - 0.035), 'face.R': (-E.x, E.y + 0.012, E.z - 0.035),
             'nose': (0, nose.y + 0.02, nose.z), 'jaw': (0, E.y + 0.015, E.z - 0.09)}
    for n, h in heads.items():
        if n in eb:
            continue
        b = eb.new(n)
        b.head = Vector(h)
        b.tail = Vector(h) + Vector((0, -0.03, 0))
        b.roll = 0
        b.parent = eb['head']
    bpy.ops.object.mode_set(mode='OBJECT')
    co = np.array([v.co[:] for v in body.data.vertices])
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    F = (1 - _sm(y, ear.y - 0.03, ear.y - 0.005)) * _sm(z, E.z - 0.15, E.z - 0.12) * (1 - _sm(z, E.z + 0.02, E.z + 0.05))
    eye_d = np.sqrt((np.abs(x) - E.x) ** 2 + (y - E.y) ** 2 + (z - E.z) ** 2)
    F *= _sm(eye_d, 0.02, 0.035)
    wn = 0.9 * (1 - _sm(np.linalg.norm(co - np.array(nose[:]), axis=1), 0.01, 0.03)) * (y < nose.y + 0.045)
    wj = 0.55 * F * (1 - _sm(z, nose.z - 0.06, nose.z - 0.035))
    wl = 0.55 * F * _sm(x, 0.004, 0.03) * (1 - wn)
    wr = 0.55 * F * _sm(-x, 0.004, 0.03) * (1 - wn)
    tot = wn + wj + wl + wr
    sc = np.where(tot > 0.95, 0.95 / np.maximum(tot, 1e-6), 1.0)
    W = {'nose': wn * sc, 'jaw': wj * sc, 'face.L': wl * sc, 'face.R': wr * sc}
    hg = body.vertex_groups['head']
    old = {n: body.vertex_groups.get(n) for n in FACE_BONES}
    groups = {n: (old[n] or body.vertex_groups.new(name=n)) for n in FACE_BONES}
    for v in body.data.vertices:
        hw = 0.0
        for g in v.groups:
            if g.group == hg.index or any(og and g.group == og.index for og in old.values()):
                hw += g.weight
        if hw <= 0:
            continue
        i = v.index
        rest = hw
        for n in FACE_BONES:
            w = float(W[n][i]) * hw
            if w > 1e-4:
                groups[n].add([i], w, 'REPLACE')
                rest -= w
            elif old[n]:
                try:
                    groups[n].remove([i])
                except RuntimeError:
                    pass
        hg.add([i], max(0.0, rest), 'REPLACE')


def _hand_crease(body, ao):
    """'crease' = knuckle lines across the fingers (glove wrinkles / skin creases)."""
    import numpy as np
    co = np.array([v.co[:] for v in body.data.vertices])
    out = np.zeros(len(co))
    for side in ('L', 'R'):
        hb = ao.data.bones['hand.' + side]
        h0, d = np.array(hb.head_local[:]), np.array((hb.tail_local - hb.head_local).normalized()[:])
        L = hb.length
        rel = co - h0
        al = rel @ d
        dist = np.linalg.norm(rel - np.outer(al, d), axis=1)
        hand = (al > -0.01) & (al < 1.1 * L) & (dist < 0.08)
        c = np.zeros(len(co))
        for f in (0.57, 0.70, 0.86):
            c = np.maximum(c, np.exp(-((al - f * L) / 0.0045) ** 2))
        c += 0.5 * np.exp(-((al - 0.03) / 0.008) ** 2)        # wrist crease / cuff gather
        out = np.where(hand, np.maximum(out, c), out)
    a = body.data.attributes.get('crease') or body.data.attributes.new('crease', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.clip(out, 0, 1).astype(np.float32))


def _hair_cards(src, cover, gender, M, seed=1, n_scalp=7000):
    """Short black hair as narrow cards: side-parted, matte, slightly wavy, lying in a 2-7 mm layer that follows the
    head; density from the 'skm' scalp mask (thins out at the hairline: no zigzag edge), none where a garment covers
    the scalp (cap, hard hat, mask...), so caps sit on hair and hair shows under the rim. Brows get short cards;
    men get moustache cards (separate object, HUM_Stache shows them on ~60 %); women get a low bun.
    Returns a list of objects rigid on 'head'."""
    import numpy as np
    rng = np.random.default_rng(seed)
    me = src.data
    me.calc_loop_triangles()
    att, att2 = me.attributes.get('skm'), me.attributes.get('skm2')
    if att is None or not len(me.loop_triangles):
        return []
    mk = np.empty(len(me.vertices) * 4, np.float32)
    att.data.foreach_get('color', mk)
    mk2 = np.zeros(len(me.vertices) * 4, np.float32)
    if att2 is not None:
        att2.data.foreach_get('color', mk2)
    mk = np.concatenate([mk.reshape(-1, 4), mk2.reshape(-1, 4)], axis=1)       # 0-3 skm, 4-7 skm2
    co = np.array([v.co[:] for v in me.vertices])
    tris = np.array([t.vertices[:] for t in me.loop_triangles])
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    dg = bpy.context.evaluated_depsgraph_get()
    body_bvh = BVHTree.FromObject(src, dg)
    cv, cp = [], []
    for o in cover:
        if o.type != 'MESH' or not len(o.data.polygons):
            continue
        base = len(cv)
        cv += [o.matrix_world @ v.co for v in o.data.vertices]
        cp += [[base + i for i in p.vertices] for p in o.data.polygons]
    cover_bvh = BVHTree.FromPolygons(cv, cp) if cp else None

    def grow(bm, chan, count, length_fn, dir_fn, lift, width, wave=0.0):
        sl = bm.verts.layers.float.get('strand') or bm.verts.layers.float.new('strand')
        tm = mk[tris, chan].mean(axis=1)
        w = area * np.clip(tm, 0, 1) ** 1.5
        if w.sum() <= 0:
            return 0
        idx = rng.choice(len(tris), count, p=w / w.sum())
        u, v = rng.random(count), rng.random(count)
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        P = a[idx] + (b[idx] - a[idx]) * u[:, None] + (c[idx] - a[idx]) * v[:, None]
        mv = mk[tris[idx], chan]
        mval = mv[:, 0] * (1 - u - v) + mv[:, 1] * u + mv[:, 2] * v
        n = 0
        for k in range(count):
            if rng.random() > mval[k] ** 1.3:           # sparse at the hairline
                continue
            hit, nrm, _i, _d = body_bvh.find_nearest(Vector(P[k]))
            if hit is None:
                continue
            if cover_bvh is not None and cover_bvh.ray_cast(hit + nrm * 0.001, nrm, 0.08)[0] is not None:
                continue
            L = length_fn(hit) * (0.75 + 0.5 * rng.random())
            steps = 6
            pts, nrms = [hit + nrm * 0.0004], [nrm]
            q = hit
            jit = Vector(rng.normal(0, 0.3, 3))
            ph, amp = rng.random() * 6.28, wave * (0.5 + rng.random())
            for st in range(1, steps + 1):
                t = st / steps
                dvec = dir_fn(q) + jit
                tang = (dvec - nrm * dvec.dot(nrm))
                if tang.length < 1e-6:
                    tang = nrm.orthogonal()
                tang.normalize()
                tang = tang + nrm.cross(tang) * amp * math.sin(ph + t * 7.0)          # slight wave
                q2 = q + tang.normalized() * (L / steps)
                h2, n2, _i, _d = body_bvh.find_nearest(q2)
                if h2 is None:
                    break
                q, nrm = h2, n2
                pts.append(q + nrm * (lift[0] + (lift[1] - lift[0]) * t ** 0.7 * (0.6 + 0.8 * rng.random())))
                nrms.append(nrm)
            if len(pts) < 3:
                continue
            tone = rng.random()
            row = []
            for i, (pp, nn) in enumerate(zip(pts, nrms)):
                t = i / (len(pts) - 1)
                fw = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
                sd = nn.cross(fw)
                sd = sd.normalized() if sd.length > 1e-9 else nn.orthogonal().normalized()
                hw = width * (1 - 0.8 * t) * 0.5
                v0, v1 = bm.verts.new(pp - sd * hw), bm.verts.new(pp + sd * hw)
                v0[sl] = v1[sl] = tone
                row.append((v0, v1))
            for (v0, v1), (w0, w1) in zip(row, row[1:]):
                bm.faces.new((v0, v1, w1, w0))
            n += 1
        return n

    part = 0.028 * KH

    def scalp_dir(q):
        if gender != 'male':
            return Vector((0.0, 1.0, -0.45))                       # combed back to the bun
        sx = 1.0 if q.x > part else -1.0
        top = max(0.0, min(1.0, (q.z - 1.60 * KH) / (0.06 * KH)))
        # swept sideways away from the part over the top, down and a little back on the sides and nape
        return Vector((sx * (0.4 + 0.8 * top), 0.25 - 0.2 * top, -0.6 + 0.3 * top))

    def scalp_len(q):
        lo, hi = (0.006, 0.02) if gender == 'male' else (0.03, 0.07)
        t = max(0.0, min(1.0, (q.z - 1.58 * KH) / (0.08 * KH)))
        return lo + (hi - lo) * t * t * (3 - 2 * t)

    bm = bmesh.new()
    ns = grow(bm, 3, n_scalp, scalp_len, scalp_dir, (0.002, 0.007 if gender == 'male' else 0.008), 0.0011, 0.35)
    nb = grow(bm, 2, 900 if gender == 'male' else 600, lambda q: 0.0065,
              lambda q: Vector((0.9 if q.x > 0 else -0.9, 0.0, 0.35)), (0.0003, 0.0012), 0.0004)
    if gender != 'male':
        # low bun at the nape (hidden when a cap covers it)
        sl = bm.verts.layers.float.get('strand') or bm.verts.layers.float.new('strand')
        bk = max((v.co for v in me.vertices if abs(v.co.x) < 0.02 and 1.50 * KH < v.co.z < 1.60 * KH),
                 key=lambda v: v.y, default=None)
        if bk is not None:
            ctr = bk + Vector((0, 0.028 * KH, -0.012 * KH))
            if cover_bvh is None or cover_bvh.find_nearest(ctr, 0.05)[0] is None:
                r = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0,
                                              matrix=Matrix.Translation(ctr) @ Matrix.Diagonal((0.042, 0.032, 0.034, 1)))
                for vv in r['verts']:
                    vv[sl] = rng.random()
                    vv.co += (vv.co - ctr) * 0.08 * math.sin(math.atan2(vv.co.z - ctr.z, vv.co.x - ctr.x) * 9)   # coils
    out = []
    bm2 = bmesh.new()
    nm_ = 0
    if gender == 'male':
        nm_ = grow(bm2, 7, 1400, lambda q: 0.009, lambda q: Vector((0.7 if q.x > 0 else -0.7, -0.25, -1.0)),
                   (0.0005, 0.0022), 0.0006)
    print('hair cards', src.name, ns, 'scalp', nb, 'brow', nm_, 'stache', flush=True)
    for b_, key, nm in ((bm, 'hair', '_haircards'), (bm2, 'stache', '_stachecards')):
        if not b_.faces:
            b_.free()
            continue
        hm = bpy.data.meshes.new(src.name + nm)
        b_.to_mesh(hm)
        b_.free()
        o = bpy.data.objects.new(hm.name, hm)
        bpy.context.scene.collection.objects.link(o)
        o.vertex_groups.new(name='head').add(range(len(hm.vertices)), 1.0, 'REPLACE')
        hm.materials.append(M[key])
        for p in hm.polygons:
            p.use_smooth = True
        out.append(o)
    return out


def build_masters(out_path, level=1, genders=('male', 'female')):
    """Run headless once: writes humans.blend with HUM_Rig_<g> armatures and HUM_<g>_<outfit> meshes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = mats()
    _glove_detail(M.get('nitrile_blue'))
    _glove_detail(M.get('rubber_glove'), RUBBER)
    for gender in genders:
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
        _close_mouth(body)
        E, nose, ear = _face_maps(body, eyes, gender)
        _face_rig(body, ao, E, nose, ear)
        _hand_crease(body, ao)
        for sd in ('L', 'R'):                       # relaxed hands: fingers a little curled, never board-flat
            for i, c in _finger_curl(body.data, ao, sd, RELAX_CURL)[0].items():
                body.data.vertices[i].co = c
        body.data.materials.clear()
        body.data.materials.append(M['skin'])
        for e in eyes:
            e.data.materials.clear()
            e.data.materials.append(M['eye'])
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
            # no moustache piece: it rendered as a black lip-shaped blob (lip skin stays)
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
            cov = [body.data.vertices[i].co.z < 1.44 * KH and   # head skin is never hidden (caps stand off it)
                   any(regions[p][i] for p in plist if p in regions and p not in ('mask', 'hair'))
                   for i in range(len(body.data.vertices))]
            bm = bmesh.new()
            bm.from_mesh(cps[0].data)
            bm.verts.ensure_lookup_table()
            deep = [cov[v.index] and all(cov[e.other_vert(v).index] for e in v.link_edges) for v in bm.verts]
            kill = [f for f in bm.faces if all(deep[v.index] for v in f.verts)]
            bmesh.ops.delete(bm, geom=kill, context='FACES')
            bm.to_mesh(cps[0].data)
            bm.free()
            if 'hair' in plist:
                cover = [c for c, p in zip(cps[1 + len(eyes):], plist) if p not in ('hair', 'stache')]
                cps += _hair_cards(cps[0], cover, gender, M, seed=len(oname) * 31 + len(plist))
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
    # asymmetric faces, broader noses (face bones; masters built before round 8 lack them)
    for n, sc, lo in (('face.L', [r.uniform(0.95, 1.05)] * 3, (r.uniform(-1.5, 1.5), 0, r.uniform(-1.5, 1.5))),
                      ('face.R', [r.uniform(0.95, 1.05)] * 3, (r.uniform(-1.5, 1.5), 0, r.uniform(-1.5, 1.5))),
                      ('nose', (r.uniform(1.06, 1.22), r.uniform(0.98, 1.06), r.uniform(0.96, 1.04)), (0, 0, 0)),
                      ('jaw', (r.uniform(0.97, 1.06), 1.0, r.uniform(0.97, 1.03)), (0, 0, r.uniform(-1, 1)))):
        pb = ao.pose.bones.get(n)
        if pb:
            pb.scale = sc
            pb.location = [c * 0.001 for c in lo]
    set_pose(ao, stand(seed))
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
    for k, v in list(full.items()):
        if k.startswith('upperarm.') and v[1] < ARM_IN:      # rest arm is 23 deg out; past -16 it enters the torso
            full[k] = (v[0], ARM_IN, v[2])
    for pb in ao.pose.bones:
        side = pb.name.split('.')[-1] if '.' in pb.name else ''
        _rot(pb, *full.get(pb.name, (0, 0, 0)), side)
        if frame is not None:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
    if 'root_dz' in P:                                    # crouch / kneel: drop the pelvis (hips bone local Y = up)
        hp = ao.pose.bones['hips']
        hp.location = (0, P['root_dz'], 0)
        if frame is not None:
            hp.keyframe_insert('location', frame=frame)


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


def _finger_curl(me, ao, side, curl, knuckle=0.085):
    """({vertex index: curled position}, knuckle axis) for the fingers of one hand: rotation about the knuckle axis,
    more toward the tips. (The ocean lane's arc wrap flattened gloved fingers into ribbons around handles on these
    meshes, so the pond lane keeps this version; the palm side was checked visually: +1 curls toward the palm.)"""
    import numpy as np
    hb = ao.data.bones['hand.' + side]
    h0, d = hb.head_local, (hb.tail_local - hb.head_local).normalized()
    co = np.array([v.co[:] for v in me.vertices])
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
    axis = d.cross(nrm).normalized()
    piv = h0 + d * knuckle
    out = {}
    for i in np.nonzero(hand & (along > knuckle))[0]:
        ang = curl * min(1.0, (along[i] - knuckle) / 0.07) * math.radians(105)
        out[int(i)] = piv + Matrix.Rotation(ang, 3, axis) @ (Vector(co[i]) - piv)
    return out, axis


def _finger_groups(me, ao, side):
    """Fingers of one hand on the rest mesh (skin and glove vertices alike), thumb first:
    [(vertex indices, along-the-hand values, MCP along)] + hand frame (h0, d, knuckle axis) as numpy arrays.
    Connectivity past the finger roots separates the fingers; pieces at the same lateral spot (glove outer/inner
    shell, skin) are grouped; a merged ring+pinky is split at its largest lateral gap."""
    import numpy as np
    from collections import defaultdict
    hb = ao.data.bones['hand.' + side]
    L = hb.length
    h0 = np.array(hb.head_local[:])
    d = np.array((hb.tail_local - hb.head_local).normalized()[:])
    _pts, axis = _finger_curl(me, ao, side, 0.0)
    ax = np.array(axis[:])
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    rel = co - h0
    al = rel @ d
    dist = np.linalg.norm(rel - np.outer(al, d), axis=1)
    lat = rel @ ax
    hand = (al > -0.01) & (al < 1.2 * L) & (dist < 0.08)
    S = hand & (al > 0.60 * L)
    ed = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get('vertices', ed)
    ed = ed.reshape(-1, 2)
    ed = ed[S[ed[:, 0]] & S[ed[:, 1]]]
    par = {int(i): int(i) for i in np.nonzero(S)[0]}

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for a_, b_ in ed:
        ra, rb = f(int(a_)), f(int(b_))
        if ra != rb:
            par[ra] = rb
    comp = defaultdict(list)
    for i in par:
        comp[f(i)].append(i)
    comps = sorted((np.array(c) for c in comp.values() if len(c) >= 6), key=lambda c: lat[c].mean())
    groups = []
    for c in comps:
        if groups and abs(lat[c].mean() - lat[groups[-1]].mean()) < 0.009:
            groups[-1] = np.concatenate([groups[-1], c])
        else:
            groups.append(c)
    out = []
    for g in groups:
        ls = np.sort(lat[g])
        if ls[-1] - ls[0] > 0.026 and len(ls) > 20:
            gaps = np.diff(ls)
            k = int(np.argmax(gaps[len(ls) // 5: -len(ls) // 5])) + len(ls) // 5
            cut = (ls[k] + ls[k + 1]) / 2
            out += [g[lat[g] < cut], g[lat[g] >= cut]]
        else:
            out.append(g)
    out.sort(key=lambda g: co[g][:, 1].mean())          # thumb: the front-most group
    res = []
    for g in out:
        root = al[g].min()
        mcp = root - 0.012 * L / 0.148
        lo, hi = lat[g].min() - 0.003, lat[g].max() + 0.003
        web = np.nonzero(hand & (al >= mcp) & (al <= root) & (lat >= lo) & (lat <= hi))[0]
        idx = np.unique(np.concatenate([g, web]))
        res.append((idx, al[idx], mcp))
    return res, (h0, d, ax, co, al)


def _grip_axis(ao, side):
    if ('grip_axis_' + side) not in ao.keys():
        hb = ao.data.bones['hand.' + side]
        axis = _finger_curl(ao.children[0].data, ao, side, 0.0)[1]
        ao['grip_axis_' + side] = list(hb.matrix_local.inverted().to_3x3() @ axis)
    return Vector(ao['grip_axis_' + side])


def grip(ao, side, curl=1.0, knuckle=0.085, name=None, target=None, clearance=0.0015):
    """Curl the fingers of one hand: shape key on a single-user copy of this person's mesh.
    target=None: the knuckle curl (curl 1 = closed fist).
    target=object or list: each finger (and the thumb) closes until it touches the target's surface, joint by joint
    (proximal phalanx first, then middle, then tip, as a real grip wraps), never closer than `clearance`; the
    person must already be posed (wrap_hand / ik_hands) with the palm at the object. Report in ao['grip_<side>']:
    joint angles and the closest finger-to-surface distance per finger (negative = clipping)."""
    import numpy as np
    mo = ao.children[0]
    if mo.data.users > 1:
        mo.data = mo.data.copy()
    if not mo.data.shape_keys:
        mo.shape_key_add(name='Basis')
    _grip_axis(ao, side)
    if target is None:
        sk = mo.shape_key_add(name=name or ('grip_' + side))
        pts, axis = _finger_curl(mo.data, ao, side, curl, knuckle)
        for i, c in pts.items():
            sk.data[i].co = c
        sk.value = 1.0
        return sk
    tg = target if isinstance(target, (list, tuple)) else [target]
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    tv = []
    for t in tg:
        te = t.evaluated_get(dg)
        tv.append((BVHTree.FromObject(te, dg), t.matrix_world.inverted()))
    pb = ao.pose.bones['hand.' + side]
    Mh = np.array(ao.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted())
    fingers, (h0, d, ax, co, al) = _finger_groups(mo.data, ao, side)
    axv = Vector(ax)

    def clear(P, prev=None):
        """min signed distance of world points P (n,3) to the target surfaces; with prev (the last accepted
        positions) a vertex whose move crosses a surface counts as clipping (thin walls, rods, net strings)"""
        best = 1.0
        W = P @ Mh[:3, :3].T + Mh[:3, 3]
        W0 = None if prev is None else prev @ Mh[:3, :3].T + Mh[:3, 3]
        for bvh, inv in tv:
            for k, w in enumerate(W):
                q = inv @ Vector(w)
                hit, nrm, _i, dd = bvh.find_nearest(q, 0.05)
                if hit is not None:
                    best = min(best, (q - hit).dot(nrm))
                if W0 is not None:
                    q0 = inv @ Vector(W0[k])
                    mv = q - q0
                    if mv.length > 1e-7 and bvh.ray_cast(q0, mv, mv.length + clearance)[0] is not None:
                        return -1.0
        return best

    def pose(idx, s, piv, A):
        P = co[idx].copy()
        for j in (2, 1, 0):
            w = np.clip((s - piv[j][0] + 0.004) / 0.008, 0.0, 1.0)
            w = w * w * (3 - 2 * w)
            p = piv[j][1]
            for k in np.nonzero(w > 0)[0]:
                R = Matrix.Rotation(A[j] * w[k], 3, axv)
                P[k] = np.array(p) + np.array(R @ Vector(P[k] - p))
        return P

    sk = mo.shape_key_add(name=name or ('grip_' + side))
    rep = {}
    amax = math.radians(95) * curl
    step = math.radians(3)
    for fi, (idx, s, mcp) in enumerate(fingers):
        tip = s.max()
        piv = []
        for frac in (0.0, 0.42, 0.72):
            sj = mcp + (tip - mcp) * frac
            near = idx[np.abs(s - max(sj, s.min() + 0.003)) < 0.005]
            piv.append((sj, co[near].mean(axis=0) if len(near) else co[idx].mean(axis=0)))
        A = [0.0, 0.0, 0.0]
        start = clear(co[idx])                         # a finger already touching may still close, not dig in
        lim = (amax, math.radians(105) * curl, math.radians(75) * curl)
        for stage in (0, 1, 2):
            while True:
                B = list(A)
                if stage == 0:
                    B = [A[0] + step, A[1] + step * 1.1, A[2] + step * 0.75]
                elif stage == 1:
                    B = [A[0], A[1] + step, A[2] + step * 0.7]
                else:
                    B = [A[0], A[1], A[2] + step]
                if any(b > l for b, l in zip(B, lim)):
                    break
                sel = s >= piv[stage][0] - 0.004
                if clear(pose(idx[sel], s[sel], piv, B), pose(idx[sel], s[sel], piv, A)) < min(clearance, start - 0.0005):
                    break
                A = B
        P = pose(idx, s, piv, A)
        for k, i in enumerate(idx):
            sk.data[int(i)].co = Vector(P[k])
        rep['thumb' if fi == 0 else 'f%d' % fi] = ([round(math.degrees(a)) for a in A], round(clear(P) * 1000, 1))
    sk.value = 1.0
    ao['grip_' + side] = str(rep)
    print('GRIP', ao.name, side, rep, flush=True)
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


def auto_poles(objs=None):
    """Every arm IK without a pole gets one (out to the side, behind, at waist height): elbows drop down and back
    instead of winging out to shoulder height. Call once after all people are rigged."""
    n = 0
    for ao in objs or [o for o in bpy.data.objects if o.type == 'ARMATURE' and o.pose]:
        for sd in ('L', 'R'):
            pb = ao.pose.bones.get('forearm.' + sd)
            if pb is None:
                continue
            for c in pb.constraints:
                if c.type == 'IK' and c.pole_target is None:
                    pole = bpy.data.objects.get('%s_Pole%s' % (ao.name, sd))
                    if pole is None:
                        pole = bpy.data.objects.new('%s_Pole%s' % (ao.name, sd), None)
                        for col in ao.users_collection:
                            col.objects.link(pole)
                        pole.parent = ao
                        pole.location = (0.6 if sd == 'L' else -0.6, 0.5, 0.9)
                    c.pole_target = pole
                    c.pole_angle = math.radians(-90)
                    n += 1
    return n


def wrap_hand(ao, side, parent, palm, fing, nrm, inf, C=None):
    """Hand closes around a bar/handle on `parent`: palm centre at `palm` (parent space), fingers along `fing`,
    palm facing `nrm` (toward the object's axis). Wrist IK + hand bone aimed so the curl axis lies along the object.
    inf: [(frame, influence)]. Call grip() first (it stores the knuckle axis). Returns the wrist target."""
    C = C or bpy.context.scene.collection
    fing, nrm = Vector(fing).normalized(), Vector(nrm).normalized()
    along = fing.cross(nrm)
    wrist = Vector(palm) - fing * 0.06
    tg = {}
    for k, v in (('W', wrist), ('F', wrist + fing * 0.4), ('A', wrist + along * 0.4)):
        e = bpy.data.objects.new('%s_Wrap%s%s_%s' % (ao.name, side, k, parent.name), None)
        C.objects.link(e)
        e.parent = parent
        e.location = v
        tg[k] = e
    ax = _grip_axis(ao, side)
    i = 0 if abs(ax.x) > abs(ax.z) else 2
    trk = ('TRACK_' if ax[i] > 0 else 'TRACK_NEGATIVE_') + 'XYZ'[i]
    cs = []
    c = ao.pose.bones['forearm.' + side].constraints.new('IK')
    c.target, c.chain_count, c.use_tail = tg['W'], 2, True
    cs.append(c)
    hb = ao.pose.bones['hand.' + side]
    c = hb.constraints.new('DAMPED_TRACK')
    c.target, c.track_axis = tg['F'], 'TRACK_Y'
    cs.append(c)
    c = hb.constraints.new('LOCKED_TRACK')
    c.target, c.lock_axis, c.track_axis = tg['A'], 'LOCK_Y', trk
    cs.append(c)
    for c in cs:
        for f, v in inf:
            c.influence = v
            c.keyframe_insert('influence', frame=f)
    return tg['W']


def ik_feet(ao, tgt_l, tgt_r):
    for s, t in (('L', tgt_l), ('R', tgt_r)):
        pb = ao.pose.bones['shin.' + s]
        c = pb.constraints.new('IK')
        c.target = t
        c.chain_count = 2


ARM_IN = -16.0     # most-inward upperarm side angle: arm hangs just clear of the hip
def stand(seed=0, amp=1.0):
    """Relaxed stand: weight on one leg (contrapposto: pelvis drops on the free side, shoulders counter-tilt, free knee
    bent and turned out), elbows bent 12-24 deg, wrists soft, head tilted a touch. Mirrored / varied by seed."""
    r = random.Random(seed * 131 + 7)
    j = lambda a=2.0: r.uniform(-a, a) * amp
    w, f = ('R', 'L') if r.random() < 0.5 else ('L', 'R')      # weight leg, free leg
    sg = 1 if w == 'R' else -1                                   # +1: free hip (left) drops
    P = {'hips': (0, 3.5 * sg + j(0.8), 3 * sg + j()), 'spine': (2 + j(1), -3 * sg + j(), -2 * sg),
         'chest': (2 + j(1), -1.5 * sg, -1.5 * sg), 'neck': (-2 + j(), 0, j(3)), 'head': (3 + j(), 3 * sg + j(), j(5)),
         'thigh.' + w: (j(1), -3.5, 0), 'shin.' + w: (-2, 0, 0), 'foot.' + w: (2, 0, 0),
         'thigh.' + f: (7 + j(), 3.5, 9), 'shin.' + f: (-15 + j(3), 0, 0), 'foot.' + f: (8, 0, 0),
         'upperarm.L': (4 + j(3), -15, -6), 'upperarm.R': (2 + j(3), -15, -6),
         'forearm.L': (14 + r.uniform(0, 10), 0, 6), 'forearm.R': (14 + r.uniform(0, 10), 0, 6),
         'hand.L': (6 + j(), 0, 0), 'hand.R': (6 + j(), 0, 0)}
    return P


POSES = {
    'stand': stand(0),          # contrapposto, arms hang with soft elbows: never an A-pose
    'crouch': {'root_dz': -0.40, 'spine': (24, 0, 0), 'chest': (10, 0, 0), 'neck': (-6, 0, 0), 'head': (-14, 0, 0),
               'thigh.L': (100, -3, 4), 'shin.L': (-118, 0, 0), 'foot.L': (24, 0, 0),
               'thigh.R': (82, -4, 4), 'shin.R': (-122, 0, 0), 'foot.R': (36, 0, 0),
               'upperarm': (34, -12, 0), 'forearm': (58, 0, 0), 'hand': (8, 0, 0)},     # knees together, heels up
    'kneel': {'root_dz': -0.44, 'spine': (8, 0, 0), 'chest': (4, 0, 0), 'head': (6, 0, 0),
              'thigh.L': (95, 0, 4), 'shin.L': (-95, 0, 0), 'foot.L': (0, 0, 0),
              'thigh.R': (-6, -2, 0), 'shin.R': (-96, 0, 0), 'foot.R': (-30, 0, 0),
              'upperarm': (24, -12, 0), 'forearm': (40, 0, 0), 'hand': (6, 0, 0)},       # one knee down
    'table': {'spine': (10, 0, 0), 'chest': (8, 0, 0), 'neck': (14, 0, 0), 'head': (12, 0, 0),
              'upperarm': (28, -10, 0), 'forearm': (72, 0, 0), 'hand': (-10, 0, 0)},
    'lift_low': {'spine': (30, 0, 0), 'chest': (12, 0, 0), 'head': (-10, 0, 0),
                 'thigh': (45, -2, 0), 'shin': (-60, 0, 0), 'foot': (15, 0, 0),
                 'upperarm': (50, -8, 0), 'forearm': (20, 0, 0)},
    'carry': {'spine': (-4, 0, 0), 'upperarm': (12, -10, 0), 'forearm': (80, 0, 0)},
    'push': {'spine': (14, 0, 0), 'upperarm': (42, -6, 0), 'forearm': (35, 0, 0)},
    'look': {'upperarm': (6, -16, 0), 'forearm': (16, 0, 0), 'head': (8, 0, 0)},
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
