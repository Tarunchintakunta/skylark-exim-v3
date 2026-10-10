"""Ocean-lane outfits on top of skhuman (the shared real-proportion people). skhuman.py is not edited: this module
registers three outfits and builds its own masters file, humans_ocean.blend, with skhuman's build path.

  fisher         PVC jacket + PVC trousers (orange / yellow / faded by person), white gumboots, rubber gloves, cloth cap
  port_hivis     long-sleeve work shirt, dark trousers, dark safety boots, plain hi-vis vest, hard hat (no marks)
  harbour_lungi  cotton shirt, checked lungi, flat sandals, bare head

New pieces reuse skhuman's clothing shells under another material (ALIAS), or are built here (lungi, hard hat,
sandal soles). Scene use is plain skhuman: load(OUT) then person(name, outfit='fisher', ...), grip(), ik_hands().

Coupling (check here first if a skhuman change breaks this): build() reassigns skhuman.OUTFITS, skhuman.mats,
skhuman._region and skhuman._shell, and relies on build_masters() looking them up as module globals; it also reads
skhuman._palette, _mat, _rot, ARM_IN, KH, set_pose, walk_cycle, person and load.

Build (headless):  Blender -b --factory-startup --python blender/skhuman_ocean.py -- <out.blend> [level] [progress_dir]
"""
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skhuman as sk  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets-src', 'blender', 'humans_ocean.blend')

OCEAN_OUTFITS = {
    'fisher': ['pvc_jacket', 'pvc_trousers', 'boots', 'gloves_rubber', 'hair', 'beanie', 'pvc_trim'],   # hair shows at temples/nape
    'fisher_bare': ['pvc_jacket', 'pvc_trousers', 'boots', 'gloves_rubber', 'hair', 'towel', 'pvc_trim'],   # cotton towel wrap: face reads
    'port_hivis': ['work_shirt', 'trousers_dark', 'boots_dark', 'vest', 'hair', 'hardhat'],
    'harbour_lungi': ['shirt_farm', 'lungi', 'sandals', 'hair'],
}
# new piece -> (skhuman piece whose shell it reuses, material key)
ALIAS = {'pvc_jacket': ('jacket', 'pvc'), 'pvc_trousers': ('trousers', 'pvc'),
         'work_shirt': ('jacket', 'work_shirt'), 'boots_dark': ('boots', 'boot_dark'),
         'towel': ('haircap', 'towel'), 'beanie': ('haircap', 'cap_cloth')}   # knit beanie down to the ears, not a flat cap   # head towel wrapped like the deck crews wear (gathered cap shape)
# oilskins stand off the body (stiff PVC over layers): shell thickness per alias, read by skhuman._shell via THICK
ALIAS_THICK = {'pvc_jacket': 0.026, 'pvc_trousers': 0.02, 'work_shirt': 0.03}   # thicker read as an inflated suit
CUSTOM = ('lungi', 'hardhat', 'sandals', 'pvc_trim')

_progress_dir = None


def _note(msg):
    """Flushed progress line; also a stage file in the job's output folder (the gate's watchdog reads that folder)."""
    print('HUMOCEAN', msg, flush=True)
    d = _progress_dir or os.environ.get('SKY_PROGRESS')      # scene builds pass their gate output folder here
    if d:
        with open(os.path.join(d, 'stage_%03d.txt' % _note.n), 'w') as f:
            f.write(msg + '\n')
        _note.n += 1


_note.n = 0
progress = _note   # scene builds: SO.progress('section') between sections


# ------------------------------------------------------------------ materials
def _plaid(m, scale=12.0):
    """Woven check for the lungi: bands in X and Z (object space) darken the per-person base colour."""
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    tc = nt.nodes.new('ShaderNodeTexCoord')
    bands = []
    for axis in ('X', 'Z'):
        w = nt.nodes.new('ShaderNodeTexWave')
        w.wave_type = 'BANDS'
        w.bands_direction = axis
        w.inputs['Scale'].default_value = scale
        nt.links.new(tc.outputs['Object'], w.inputs['Vector'])
        bands.append(w)
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(bands[0].outputs['Fac'], mx.inputs[0])
    nt.links.new(bands[1].outputs['Fac'], mx.inputs[1])
    ramp = nt.nodes.new('ShaderNodeValToRGB')       # crisp stripes where either band is high: a woven check
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.5, 0.5, 0.5, 1)
    nt.links.new(mx.outputs[0], ramp.inputs[0])
    mul = nt.nodes.new('ShaderNodeMix')
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    if src is not None:
        nt.links.new(src, mul.inputs['A'])
    else:
        mul.inputs['A'].default_value = p.inputs['Base Color'].default_value
    nt.links.new(ramp.outputs[0], mul.inputs['B'])
    nt.links.new(mul.outputs['Result'], p.inputs['Base Color'])
    return m


_base_mats = sk.mats


def _skin_detail(m):
    """Weathered outdoor skin: roughness varies (oily forehead and nose vs dry cheeks), warm ruddy mottling,
    so it is not a uniform waxy shell."""
    if m.get('ocean_skin'):
        return
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n1 = nt.nodes.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 60.0
    n1.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeMapRange')
    r.inputs['To Min'].default_value = 0.25
    r.inputs['To Max'].default_value = 0.78
    nt.links.new(n1.outputs[0], r.inputs['Value'])
    nt.links.new(r.outputs[0], p.inputs['Roughness'])
    n2 = nt.nodes.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 18.0
    n2.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    f = nt.nodes.new('ShaderNodeMapRange')
    f.inputs['From Min'].default_value = 0.5
    f.inputs['From Max'].default_value = 0.75
    f.inputs['To Max'].default_value = 0.7
    nt.links.new(n2.outputs[0], f.inputs['Value'])
    src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    nt.links.new(f.outputs[0], mx.inputs['Factor'])
    if src is not None:
        nt.links.new(src, mx.inputs['A'])
    else:
        mx.inputs['A'].default_value = p.inputs['Base Color'].default_value
    mx.inputs['B'].default_value = (1.0, 0.5, 0.42, 1)      # sun-reddened patches
    nt.links.new(mx.outputs['Result'], p.inputs['Base Color'])
    m['ocean_skin'] = 1


def mats():
    M = _base_mats()
    _skin_detail(M['skin'])
    M['rubber_glove'] = sk._mat('HUM_RubberGloveWorn', (0.10, 0.085, 0.06), 0.6, coat=0.05, bump=0.08)   # dark worn rubber, not skin-yellow
    M['pvc'] = sk._palette(sk._mat('HUM_PVCOilskin', (0.75, 0.24, 0.04), 0.8, coat=0.0, bump=0.05, wrinkle=0.35, rand=0.12),
                           ((0.74, 0.22, 0.03), (0.78, 0.58, 0.04), (0.26, 0.28, 0.12), (0.58, 0.26, 0.08),
                            (0.22, 0.30, 0.42), (0.70, 0.62, 0.20)))   # orange, yellow, olive, faded orange, faded blue, faded yellow
    M['work_shirt'] = sk._palette(sk._mat('HUM_WorkShirt', (0.2, 0.25, 0.32), 0.85, sheen=0.2, bump=0.12, rand=0.12,
                                          wrinkle=0.5),
                                  ((0.14, 0.18, 0.28), (0.30, 0.30, 0.26), (0.36, 0.34, 0.28), (0.20, 0.26, 0.34)))
    M['boot_dark'] = sk._mat('HUM_BootDark', (0.035, 0.033, 0.03), 0.55, coat=0.1, bump=0.05)
    M['lungi'] = _plaid(sk._palette(sk._mat('HUM_Lungi', (0.2, 0.3, 0.5), 0.9, sheen=0.25, bump=0.1, rand=0.1,
                                            wrinkle=0.5),
                                    ((0.16, 0.24, 0.46), (0.12, 0.30, 0.20), (0.40, 0.10, 0.12), (0.30, 0.30, 0.34),
                                     (0.45, 0.32, 0.12))))   # blue, green, maroon, grey, ochre checks
    M['hardhat'] = sk._palette(sk._mat('HUM_HardHat', (0.85, 0.8, 0.1), 0.38, coat=0.35, bump=0.05, rand=0.05),
                               ((0.80, 0.80, 0.76), (0.82, 0.62, 0.04), (0.80, 0.80, 0.76), (0.78, 0.30, 0.04)))
    M['sandal'] = sk._mat('HUM_Sandal', (0.10, 0.06, 0.035), 0.7, bump=0.1)
    M['towel'] = _plaid(sk._palette(sk._mat('HUM_HeadTowel', (0.6, 0.6, 0.58), 0.95, sheen=0.4, bump=0.3, rand=0.1,
                                            wrinkle=0.6),
                                    ((0.62, 0.6, 0.55), (0.5, 0.14, 0.1), (0.55, 0.55, 0.5), (0.2, 0.3, 0.45))), scale=40.0)
    # deck caps: dark knit / faded cloth (a pale cap from above reads as a bald head)
    M['cap_cloth'] = sk._palette(sk._mat('HUM_CapDeck', (0.1, 0.1, 0.12), 0.9, sheen=0.3, bump=0.2, rand=0.1),
                                 ((0.06, 0.07, 0.09), (0.25, 0.08, 0.06), (0.12, 0.16, 0.22), (0.2, 0.2, 0.18)))
    return M


# ------------------------------------------------------------------ pieces
_base_region = sk._region
_base_shell = sk._shell


CLEAN = ('pvc_jacket', 'pvc_trousers', 'work_shirt', 'shirt_farm', 'vest', 'trousers_dark', 'hair')   # hair: no zigzag hairline


def _clean(body, mask, n=2):
    """Morphological close then open on the mesh graph: no torn tags or notches along a garment hem."""
    import numpy as np
    m = np.array(mask, bool)
    e = np.empty(len(body.data.edges) * 2, dtype=np.int64)
    body.data.edges.foreach_get('vertices', e)
    a, b = e[0::2], e[1::2]

    def grow(x):
        y = x.copy()
        y[a[x[b]]] = True
        y[b[x[a]]] = True
        return y
    for op in (grow, ) * n + (lambda x: ~grow(~x), ) * (2 * n) + (grow, ) * n:
        m = op(m)
    return m.tolist()


def _region(body, gender, piece, k):
    if piece in CLEAN:
        return _clean(body, _region_raw(body, gender, piece, k))
    return _region_raw(body, gender, piece, k)


def _region_raw(body, gender, piece, k):
    if piece == 'stache':   # the base moustache renders as a black open-mouth shape: no moustache, lip skin kept
        return [False] * len(body.data.vertices)
    if piece == 'pvc_trousers':   # legs tucked into the gumboot (boot top 0.34): no PVC poking through
        base = _base_region(body, gender, 'trousers', k)
        return [m and v.co.z > 0.30 * k for m, v in zip(base, body.data.vertices)]
    if piece in ALIAS:
        return _base_region(body, gender, ALIAS[piece][0], k)
    if piece == 'lungi':      # skin under the cloth tube is hidden (legs from the waist to the shin)
        return [0.30 * k < v.co.z < 0.98 * k and abs(v.co.x) < 0.19 * k for v in body.data.vertices]
    if piece in ('hardhat', 'sandals', 'pvc_trim'):
        return [False] * len(body.data.vertices)
    return _base_region(body, gender, piece, k)


def _finish(o, body, M, key, soften=()):
    """Weights from the nearest body surface, subdivide + thin solidify, one material."""
    me = o.data
    for vg in body.vertex_groups:
        o.vertex_groups.new(name=vg.name)
    dt = o.modifiers.new('dt', 'DATA_TRANSFER')
    dt.object = body
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    bpy.context.view_layer.objects.active = o
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier=dt.name)
    for vg in o.vertex_groups:
        if vg.name.startswith(soften):
            for v in me.vertices:
                for g in v.groups:
                    if g.group == vg.index:
                        g.weight *= 0.4
    me.materials.clear()
    me.materials.append(M[key])
    for p in me.polygons:
        p.use_smooth = True
    return o


def _slab(body, k, z, half_x):
    """Body cross-section extents (x0, x1, y0, y1) of the legs/hips at height z."""
    pts = [v.co for v in body.data.vertices if abs(v.co.z - z) < 0.025 * k and abs(v.co.x) < half_x]
    if not pts:
        return -0.15 * k, 0.15 * k, -0.1 * k, 0.1 * k
    return min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts)


def _lungi(body, k, M):
    """Wrap-around cloth tube from the waist (rolled band) to just above the ankle, loose between the legs."""
    bm = bmesh.new()
    na, nz = 48, 22
    z_top, z_hem = 1.0 * k, 0.16 * k
    rings = []
    for j in range(nz + 1):
        u = j / nz                                   # 0 waist .. 1 hem
        z = z_top + (z_hem - z_top) * u
        x0, x1, y0, y1 = _slab(body, k, max(z, 0.62 * k), 0.2 * k)   # below the knee keep the knee-width tube
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # hugs the waist under the shirt hem (shirt hem sits 12 mm off the body), hangs free below it
        clr = 0.006 * k if z > 0.78 * k else 0.012 * k + 0.025 * k * min(1.0, (0.78 * k - z) / (0.3 * k))
        rx, ry = (x1 - x0) / 2 + clr, (y1 - y0) / 2 + clr
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            c, s = math.cos(a), math.sin(a)
            # superellipse (fuller at the sides), drape folds deepening toward the hem, a front overlap fold
            e = 0.9
            px = rx * math.copysign(abs(c) ** e, c)
            py = ry * math.copysign(abs(s) ** e, s)
            fold = (0.004 + 0.012 * u * u) * k * math.sin(a * 11 + math.sin(z * 9) * 1.2)
            front = 0.006 * k * max(0.0, -s) * math.exp(-((a - 1.5 * math.pi - 0.35) ** 2) / 0.02)
            n = Vector((c, s, 0))
            row.append(bm.verts.new((cx + px + n.x * (fold + front), cy + py + n.y * (fold + front), z)))
        rings.append(row)
    for j in range(nz):
        for i in range(na):
            i2 = (i + 1) % na
            bm.faces.new((rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]))
    # (no rolled waistband ring: the shirt hangs over the waist and the ring poked through it)
    me = bpy.data.meshes.new(body.name + '_lungi')
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(body.name + '_lungi', me)
    bpy.context.scene.collection.objects.link(o)
    sm = o.modifiers.new('sub', 'SUBSURF')
    sm.levels = 1
    sol = o.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.003
    sol.offset = 1
    for m in list(o.modifiers):
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)
    _finish(o, body, M, 'lungi', soften=('thigh', 'shin'))
    hips = o.vertex_groups.get('hips')
    if hips:
        for v in me.vertices:
            hips.add([v.index], 0.6, 'ADD')     # the tube follows the pelvis; legs only pull it a little
    return o


def _hardhat(body, k, M):
    """Shell dome with a centre ridge and a short peak, standing ~2 cm off the head; rigid on the head bone."""
    hv = [v.co for v in body.data.vertices if v.co.z > 1.58 * k and abs(v.co.x) < 0.11 * k]
    zt = max(p.z for p in hv)
    xs, ys = [p.x for p in hv], [p.y for p in hv]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    rx, ry = (max(xs) - min(xs)) / 2 + 0.022 * k, (max(ys) - min(ys)) / 2 + 0.026 * k
    zb = 1.605 * k
    rz = zt - zb + 0.024 * k
    bm = bmesh.new()
    na, nr = 40, 10
    rings = []
    for j in range(nr + 1):
        t = (j / nr) * math.pi / 2                    # 0 rim .. pi/2 crown
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            ridge = 0.006 * k * math.exp(-(math.cos(a) / 0.10) ** 2) * math.sin(t)   # fore-aft crown ridge
            row.append(bm.verts.new((cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a),
                                     zb + rz * math.sin(t) + ridge)))
        rings.append(row)
    for j in range(nr):
        for i in range(na):
            i2 = (i + 1) % na
            bm.faces.new((rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]))
    # brim: narrow all round, a peak at the front (face is -Y)
    brim = []
    for i in range(na):
        a = 2 * math.pi * i / na
        w = 0.012 * k + 0.035 * k * max(0.0, -math.sin(a)) ** 3
        brim.append(bm.verts.new((cx + (rx + w) * math.cos(a), cy + (ry + w) * math.sin(a), zb - 0.006 * k)))
    for i in range(na):
        i2 = (i + 1) % na
        bm.faces.new((rings[0][i], brim[i], brim[i2], rings[0][i2]))
    me = bpy.data.meshes.new(body.name + '_hardhat')
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(body.name + '_hardhat', me)
    bpy.context.scene.collection.objects.link(o)
    sol = o.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.004 * k
    sol.offset = -1
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier=sol.name)
    for vg in body.vertex_groups:
        o.vertex_groups.new(name=vg.name)
    o.vertex_groups['head'].add([v.index for v in me.vertices], 1.0, 'REPLACE')
    me.materials.append(M['hardhat'])
    for p in me.polygons:
        p.use_smooth = True
    return o


def _pvc_trim(body, k, M):
    """Oilskin details that make the jacket read as PVC gear, not a sweater: a low collar band at the neck base
    with a storm flap down the front, and seam welts over the shoulders. Weights from the nearest body surface."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    off = (ALIAS_THICK['pvc_jacket'] * 1.6 + 0.008) * k          # sits just outside the jacket shell
    bm = bmesh.new()

    def strip(path, half_w, lift=0.0):
        """Ribbon of quads along body-surface points, pushed out by off."""
        rows = []
        for p in path:
            hit, nrm, _i, _d = bvh.ray_cast(Vector((p[0], -1.0, p[1])), Vector((0, 1, 0))) if len(p) == 2 else (None,) * 4
            if hit is None:
                hit, nrm, _i, _d = bvh.find_nearest(Vector(p if len(p) == 3 else (p[0], 0, p[1])))
            base = hit + nrm * (off + lift)
            side = nrm.cross(Vector((0, 0, 1))).normalized() if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
            rows.append((bm.verts.new(base - side * half_w), bm.verts.new(base + side * half_w)))
        for (a0, a1), (b0, b1) in zip(rows, rows[1:]):
            bm.faces.new((a0, a1, b1, b0))
    # collar band: a low ring around the neck base, below the jaw
    ring = []
    for i in range(24):
        a = 2 * math.pi * i / 24
        p = Vector((0.075 * k * math.cos(a), 0.01 * k + 0.07 * k * math.sin(a), 1.40 * k))
        hit, nrm, _i, _d = bvh.find_nearest(p)
        d = Vector((p.x, p.y - 0.01 * k, 0)).normalized()
        c = hit + d * (off + 0.004 * k)
        ring.append((bm.verts.new(c), bm.verts.new(c + Vector((0, 0, 0.025 * k)) + d * 0.003 * k)))
    for i in range(24):
        a0, a1 = ring[i]
        b0, b1 = ring[(i + 1) % 24]
        bm.faces.new((a0, b0, b1, a1))
    # shoulder seam welts (neck to shoulder point, both sides)
    for sx in (-1, 1):
        strip([(sx * (0.07 + 0.11 * t) * k, 0.0, (1.44 - 0.03 * t) * k) for t in [i / 8 for i in range(9)]], 0.006 * k, 0.003 * k)
    me = bpy.data.meshes.new(body.name + '_pvc_trim')
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(body.name + '_pvc_trim', me)
    bpy.context.scene.collection.objects.link(o)
    sol = o.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.004 * k
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier=sol.name)
    _finish(o, body, M, 'pvc')
    return o


def _sandals(body, k, M):
    """Flat dark soles under each foot (ponytail: no strap; add a thong strap if close-ups need it)."""
    bm = bmesh.new()
    for sx in (-1, 1):
        foot = [v.co for v in body.data.vertices if v.co.z < 0.03 * k and v.co.x * sx > 0]
        if len(foot) < 8:
            continue
        ctr = sum(foot, Vector()) / len(foot)
        pts = []
        for q in foot:
            d = Vector((q.x - ctr.x, q.y - ctr.y, 0))
            p = Vector((ctr.x, ctr.y, 0)) + d * 1.06 + (d.normalized() * 0.004 * k if d.length > 1e-6 else d)
            pts.append(bm.verts.new((p.x, p.y, -0.002 * k)))
            pts.append(bm.verts.new((p.x, p.y, 0.012 * k)))
        hull = bmesh.ops.convex_hull(bm, input=pts)
        drop = {g for g in hull.get('geom_interior', []) + hull.get('geom_unused', []) if isinstance(g, bmesh.types.BMVert)}
        bmesh.ops.delete(bm, geom=list(drop), context='VERTS')
    me = bpy.data.meshes.new(body.name + '_sandals')
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(body.name + '_sandals', me)
    bpy.context.scene.collection.objects.link(o)
    _finish(o, body, M, 'sandal')
    return o


def _shell(body, piece, mask, M):
    _note('piece %s %s' % (body.name, piece))
    if piece == 'stache':
        o = bpy.data.objects.new('%s_stache' % body.name, bpy.data.meshes.new('%s_stache' % body.name))
        bpy.context.scene.collection.objects.link(o)
        return o
    if piece == 'lungi':
        return _lungi(body, sk.KH, M)
    if piece == 'hardhat':
        return _hardhat(body, sk.KH, M)
    if piece == 'pvc_trim':
        return _pvc_trim(body, sk.KH, M)
    if piece == 'sandals':
        return _sandals(body, sk.KH, M)
    if piece in ALIAS:
        base, key = ALIAS[piece]
        t0 = sk.THICK[base]
        sk.THICK[base] = ALIAS_THICK.get(piece, t0)
        try:
            o = _base_shell(body, base, mask, M)
        finally:
            sk.THICK[base] = t0
        o.data.materials[0] = M[key]
        o.name = '%s_%s' % (body.name, piece)
        return o
    o = _base_shell(body, piece, mask, M)
    if piece == 'vest':
        _inflate(o, body, 0.02)    # clear of the work shirt's folds: no shirt poking through the vest hem
    return o


def _inflate(o, body, d):
    """Move a finished shell away from the body surface (nearest-point direction), keeping its thickness."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    for v in o.data.vertices:
        hit, _n, _i, _d = bvh.find_nearest(v.co)
        if hit is not None and (v.co - hit).length > 1e-6:
            v.co += (v.co - hit).normalized() * d


def build(out_path=OUT, level=1, progress_dir=None):
    """Patch skhuman for the ocean outfits only, then run its own build_masters."""
    global _progress_dir
    _progress_dir = progress_dir
    if progress_dir:
        os.makedirs(progress_dir, exist_ok=True)
    sk.OUTFITS = dict(OCEAN_OUTFITS)
    sk.mats = mats
    sk._region = _region
    sk._shell = _shell
    sk.THICK['gloves_rubber'] = 0.0012          # thin enough that the fingers stay separate (thicker fused into mitts)
    sk.CUFF = tuple(sk.CUFF) + ('gloves_rubber',)   # turned glove cuff band at the wrist
    _note('build start -> %s' % out_path)
    sk.build_masters(os.path.abspath(out_path), level)
    _note('BUILT %s' % out_path)


# ------------------------------------------------------------------ scene use: drop-in for sklib's person / pose / walk
# The ocean scenes were choreographed with sklib's people: joints sh/el/hp/kn/an, character facing +X, POSES in
# sklib.POSES. install(L) swaps those three functions so the same choreography drives skhuman people.
OLD_OUTFIT = {'port': 'port_hivis', 'port_o': 'port_hivis'}
FACE = math.pi / 2          # skhuman faces -Y; sklib's choreography faces +X
_L = None


def outfit_for(old):
    if old.startswith('fisher'):
        return 'fisher_bare' if old.endswith('_b') else 'fisher'
    return OLD_OUTFIT.get(old, 'harbour_lungi')


def translate(spec):
    """sklib pose dict (degrees; limbs: Y- = swing forward, X = out to the side; spine Y+ = lean forward)
    -> skhuman set_pose dict (flex forward +, side out +, knee bend negative)."""
    P = {}
    for s in ('L', 'R'):
        sg = 1 if s == 'L' else -1
        x, y, z = spec.get('sh_' + s, (6 * sg, 0, 0))
        # a raised arm keeps the rest pose's 23 deg splay; swing it back in about the vertical (measured: at flex
        # 90 the hand is 26 deg out, a -0.3 * flex twist brings it straight ahead)
        P['upperarm.' + s] = (-y, -20 + x * sg, z * sg - 0.3 * max(0.0, -y))
        fl = P['upperarm.' + s][0]
        x, y, z = spec.get('el_' + s, (0, -8, 0))
        P['forearm.' + s] = (max(4.0, -y, 28.0 if fl > 50 else 0.0), 0, 0)   # raised arms keep soft elbows, never locked straight
        x, y, z = spec.get('hp_' + s, (0, 0, 0))
        P['thigh.' + s] = (-y, 2 + x * sg, z * sg)
        x, y, z = spec.get('kn_' + s, (0, 0, 0))
        P['shin.' + s] = (-abs(y), 0, 0)
        x, y, z = spec.get('an_' + s, (0, 0, 0))
        P['foot.' + s] = (-y, 0, 0)
    x, y, z = spec.get('spine', (0, 0, 0))
    P['spine'] = (y * 0.55, x * 0.5, z * 0.5)
    P['chest'] = (y * 0.45, x * 0.5, z * 0.5)
    x, y, z = spec.get('neck', (0, 0, 0))
    P['neck'] = (y * 0.6, 0, 0)
    P['head'] = (y * 0.4, 0, 0)
    return P


def pose(root, p, frame=None, upper_only=False, overrides=None):
    spec = dict(_L.POSES[p]) if isinstance(p, str) else dict(p)
    if overrides:
        spec.update(overrides)
    P = translate(spec)
    for pb in root.pose.bones:
        if upper_only and (pb.name.startswith(('thigh', 'shin', 'foot')) or pb.name == 'hips'):
            continue                       # legs keep their walk / stance keys
        v = P.get(pb.name, (0, 0, 0))
        lim = sk.ARM_IN   # skhuman.set_pose clamp: the arm never enters the torso
        if pb.name.startswith('upperarm.') and v[1] < lim:
            v = (v[0], lim, v[2])
        sk._rot(pb, *v, pb.name.split('.')[-1] if '.' in pb.name else '')
        if frame is not None:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
    if not upper_only:
        h = root.pose.bones['hips']
        h.location = (0, spec.get('hips_z', 0.94) - 0.94, 0)
        if frame is not None:
            h.keyframe_insert('location', frame=frame)


def person(name, outfit='plant', loc=(0, 0, 0), rot_z=0.0, height=1.72, skin=None, build=1.0, seed=None, mats=None):
    """sklib.person signature. Returns the armature; root rotation is offset so +X stays 'forward' for callers."""
    seed = seed if seed is not None else (hash(name) & 0xffff)
    ao = sk.person(name, outfit_for(outfit), 'male', loc, rot_z + FACE, height / 1.72, seed=seed)
    pose(ao, 'stand')
    return ao


def walk(root, path, f0, f1, stride=0.75, upper=None):
    """sklib.walk signature on skhuman's distance-locked walk cycle (feet don't skate)."""
    pts = [Vector(p[:2]) for p in path]
    seg = [(b - a).length for a, b in zip(pts, pts[1:])]
    tot = sum(seg) or 1.0
    keyed, acc = [(f0, tuple(pts[0]))], 0.0
    for p, d in zip(pts[1:], seg):
        acc += d
        keyed.append((f0 + (f1 - f0) * acc / tot, tuple(p)))
    base = {}
    if upper:
        up = {k: v for k, v in _L.POSES[upper].items() if not k.startswith(('hp', 'kn', 'an')) and k != 'hips_z'}
        base = {k: v for k, v in translate(up).items() if not k.startswith(('thigh', 'shin', 'foot'))}
    sk.walk_cycle(root, int(f0), int(f1), keyed, stride=stride, base=base, arms=not upper)


def grip(ao, side, curl=1.0, knuckle=0.085):
    """Fist around a handle. skhuman.grip takes the palm normal from the spread finger vertices (which picks the
    wrong axis on these meshes: fingers loop sideways into long hooks) and bends them rigidly at the knuckle. Here the
    normal comes from the flat back-of-hand plate and each finger wraps on an arc."""
    import numpy as np
    mo = ao.children[0]
    if mo.data.users > 1:
        mo.data = mo.data.copy()
    hb = ao.data.bones['hand.' + side]
    h0, d = hb.head_local, (hb.tail_local - hb.head_local).normalized()
    co = np.array([v.co[:] for v in mo.data.vertices])
    rel = co - np.array(h0[:])
    along = rel @ np.array(d[:])
    perp = rel - np.outer(along, np.array(d[:]))
    dist = np.linalg.norm(perp, axis=1)
    # palm normal from the back-of-hand plate (flat, unlike the spread fingers); the palm side is where the
    # relaxed fingertips already lean
    plate = perp[(along > 0.01) & (along < 0.075) & (dist < 0.06)]
    plate = plate - plate.mean(axis=0)
    _w, ev = np.linalg.eigh(plate.T @ plate)
    nrm = Vector(ev[:, 0])
    nrm = (nrm - d * nrm.dot(d)).normalized()
    tips = perp[(along > 0.15) & (along < 0.24) & (dist < 0.075)]
    if len(tips) and float(tips.mean(axis=0) @ np.array(nrm[:])) - float(perp[(along > 0.01) & (along < 0.075) & (dist < 0.06)].mean(axis=0) @ np.array(nrm[:])) < 0:
        nrm = -nrm
    axis = d.cross(nrm).normalized()
    piv = h0 + d * knuckle
    fing = (along > knuckle) & (along < 0.24) & (dist < 0.075)
    if not mo.data.shape_keys:
        mo.shape_key_add(name='Basis')
    sk_ = mo.shape_key_add(name='grip_' + side)
    # fingers bend continuously (all three joints), not as a rigid hook at the knuckle: a straight finger of length
    # Lf wraps onto an arc of total angle curl * 250 deg toward the palm; a vertex's offset from the finger's
    # centre plane (its thickness) stays radial, so the finger keeps its width.
    lf = max(0.06, float(along[fing].max() - knuckle)) if fing.any() else 0.09
    theta = curl * math.radians(250)
    if abs(theta) < 1e-3:
        return sk_
    R = lf / abs(theta)
    pal = nrm * math.copysign(1.0, theta)
    for i in np.nonzero(fing)[0]:
        q = Vector(co[i]) - piv
        a_, n_, w_ = q.dot(d), q.dot(pal), q.dot(axis)
        ph = a_ / R
        sk_.data[i].co = piv + axis * w_ + pal * R + (R - n_) * (d * math.sin(ph) - pal * math.cos(ph))
    sk_.value = 1.0
    return sk_


def install(L, blend=OUT):
    """Load the ocean masters and route sklib's person / pose / walk to skhuman people."""
    global _L
    _L = L
    sk.load(os.path.abspath(blend))
    L.person, L.pose, L.walk = person, pose, walk
    return sk


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build(argv[0] if argv else OUT, int(argv[1]) if len(argv) > 1 else 1, argv[2] if len(argv) > 2 else None)
