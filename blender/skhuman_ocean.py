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
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skhuman as sk  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets-src', 'blender', 'humans_ocean.blend')

OCEAN_OUTFITS = {
    'fisher': ['pvc_jacket', 'pvc_trousers', 'boots', 'gloves_rubber', 'cap'],
    'port_hivis': ['work_shirt', 'trousers_dark', 'boots_dark', 'vest', 'hair', 'hardhat'],
    'harbour_lungi': ['shirt_farm', 'lungi', 'sandals', 'hair'],
}
# new piece -> (skhuman piece whose shell it reuses, material key)
ALIAS = {'pvc_jacket': ('jacket', 'pvc'), 'pvc_trousers': ('trousers', 'pvc'),
         'work_shirt': ('jacket', 'work_shirt'), 'boots_dark': ('boots', 'boot_dark')}
CUSTOM = ('lungi', 'hardhat', 'sandals')

_progress_dir = None


def _note(msg):
    """Flushed progress line; also a stage file in the job's output folder (the gate's watchdog reads that folder)."""
    print('HUMOCEAN', msg, flush=True)
    if _progress_dir:
        with open(os.path.join(_progress_dir, 'stage_%03d.txt' % _note.n), 'w') as f:
            f.write(msg + '\n')
        _note.n += 1


_note.n = 0


# ------------------------------------------------------------------ materials
def _plaid(m, scale=26.0):
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


def mats():
    M = _base_mats()
    M['pvc'] = sk._palette(sk._mat('HUM_PVCOilskin', (0.75, 0.24, 0.04), 0.42, coat=0.3, bump=0.04, wrinkle=0.6, rand=0.08),
                           ((0.74, 0.22, 0.03), (0.78, 0.58, 0.04), (0.58, 0.26, 0.08), (0.80, 0.30, 0.04),
                            (0.70, 0.62, 0.20)))   # orange, yellow, sun-faded orange, bright orange, faded yellow
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
    return M


# ------------------------------------------------------------------ pieces
_base_region = sk._region
_base_shell = sk._shell


def _region(body, gender, piece, k):
    if piece in ALIAS:
        return _base_region(body, gender, ALIAS[piece][0], k)
    if piece == 'lungi':      # skin under the cloth tube is hidden (legs from the waist to the shin)
        return [0.30 * k < v.co.z < 0.98 * k and abs(v.co.x) < 0.19 * k for v in body.data.vertices]
    if piece in ('hardhat', 'sandals'):
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
        clr = 0.012 * k if u < 0.06 else 0.03 * k + 0.035 * k * u      # hugs the waist, hangs free lower down
        rx, ry = (x1 - x0) / 2 + clr, (y1 - y0) / 2 + clr
        row = []
        for i in range(na):
            a = 2 * math.pi * i / na
            c, s = math.cos(a), math.sin(a)
            # superellipse (fuller at the sides), drape folds deepening toward the hem, a front overlap fold
            e = 0.7
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
    # rolled waistband: a fat ring tucked at the front
    top = rings[0]
    ctr = sum((v.co for v in top), Vector()) / na
    band = []
    for zz, out in ((1.0 * k, 0.0), (1.012 * k, 0.010 * k), (1.024 * k, 0.0)):
        band.append([bm.verts.new(Vector((ctr.x, ctr.y, 0)) + (Vector((v.co.x, v.co.y, 0)) - Vector((ctr.x, ctr.y, 0)))
                                  * 1.0 + (Vector((v.co.x - ctr.x, v.co.y - ctr.y, 0)).normalized() * out)
                                  + Vector((0, 0, zz))) for v in top])
    for b0, b1 in zip(band, band[1:]):
        for i in range(na):
            i2 = (i + 1) % na
            bm.faces.new((b0[i], b0[i2], b1[i2], b1[i]))
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
    if piece == 'lungi':
        return _lungi(body, sk.KH, M)
    if piece == 'hardhat':
        return _hardhat(body, sk.KH, M)
    if piece == 'sandals':
        return _sandals(body, sk.KH, M)
    if piece in ALIAS:
        base, key = ALIAS[piece]
        o = _base_shell(body, base, mask, M)
        o.data.materials[0] = M[key]
        o.name = '%s_%s' % (body.name, piece)
        return o
    return _base_shell(body, piece, mask, M)


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
        return 'fisher'
    return OLD_OUTFIT.get(old, 'harbour_lungi')


def translate(spec):
    """sklib pose dict (degrees; limbs: Y- = swing forward, X = out to the side; spine Y+ = lean forward)
    -> skhuman set_pose dict (flex forward +, side out +, knee bend negative)."""
    P = {}
    for s in ('L', 'R'):
        sg = 1 if s == 'L' else -1
        x, y, z = spec.get('sh_' + s, (6 * sg, 0, 0))
        P['upperarm.' + s] = (-y, -20 + x * sg, z * sg)
        x, y, z = spec.get('el_' + s, (0, -8, 0))
        P['forearm.' + s] = (max(4.0, -y), 0, 0)
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
        if pb.name.startswith('upperarm.') and v[1] < sk.ARM_IN:
            v = (v[0], sk.ARM_IN, v[2])    # same clamp as skhuman.set_pose: arm never enters the torso
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
