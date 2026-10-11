"""Portrait-crop review sheet for the shared human library (skhuman): builds male masters for the outfits it shows,
then renders 960x540 tiles (EEVEE, AgX): four head-and-shoulder crops, gloved grips on a crate handle, a net-bag rim,
a box edge and a thin rod (contact grip), and one mid-distance group (stand / crouch / kneel) as people read in scene.
  Blender -b --factory-startup --python blender/review_humans.py -- <out_dir> [nobuild]
Ocean outfits (fisherman, port hi-vis) come from skhuman_ocean.py when importable (next to this file or SKY_OCEAN_DIR).
Writes stage_NN.txt progress files and tile PNGs to out_dir; blender/review_sheet.py stitches the sheet."""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if os.environ.get('SKY_OCEAN_DIR'):
    sys.path.insert(1, os.environ['SKY_OCEAN_DIR'])
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import skhuman as sk  # noqa: E402
try:
    import skhuman_ocean as SO  # noqa: E402
except ImportError:
    SO = None

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else '/tmp/humans_review')
BUILD = 'nobuild' not in argv
ONLY = [a[5:] for a in argv if a.startswith('only=')]
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
_n = [0]


def stage(msg):
    print('REVIEW', round(time.time() - T0), msg, flush=True)
    with open(os.path.join(OUT, 'stage_%02d.txt' % _n[0]), 'w') as f:
        f.write(msg + '\n')
    _n[0] += 1


BASE = os.path.join(OUT, 'humans_r8.blend')
OCEAN = os.path.join(OUT, 'humans_r8_ocean.blend')
if BUILD:
    keep = sk.OUTFITS
    sk.OUTFITS = {k: keep[k] for k in ('plant', 'driver')}
    stage('build base masters')
    sk.build_masters(BASE, 1, genders=('male', 'female'))
    if SO:
        stage('build ocean masters')
        sk.OUTFITS = {'fisher_nocap': [p for p in SO.OCEAN_OUTFITS['fisher'] if p != 'beanie'],
                      'port_hivis': SO.OCEAN_OUTFITS['port_hivis']}
        sk.mats, sk._region, sk._shell = SO.mats, SO._region, SO._shell
        sk.THICK['gloves_rubber'] = 0.0012
        sk.CUFF = tuple(sk.CUFF) + ('gloves_rubber',)
        sk.build_masters(OCEAN, 1, genders=('male',))
    sk.OUTFITS = keep

stage('scene')
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
C = s.collection
CC0 = sk.CC0


def world(name='kloofendal_48d_partly_cloudy_puresky_4k', strength=0.9, rot=40.0, sun=3.2):
    w = bpy.data.worlds.new('W')
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(os.path.join(CC0, 'hdri', name + '.hdr'), check_existing=True)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot))
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs[0], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs[0])
    ld = bpy.data.lights.new('Sun', 'SUN')
    ld.energy = sun
    ld.angle = math.radians(2.5)
    ld.color = (1.0, 0.95, 0.88)
    so = bpy.data.objects.new('Sun', ld)
    C.objects.link(so)
    so.rotation_euler = (math.radians(52), 0, math.radians(-35))


def mat(name, col, rough=0.6, metal=0.0, noise=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*col, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if noise:
        nt = m.node_tree
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 6
        nz.inputs['Detail'].default_value = 8
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs[0].default_value = noise
        mx.inputs[6].default_value = (*col, 1)
        nt.links.new(nz.outputs['Color'], mx.inputs[7])
        nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    return m


def mesh_obj(name, bm, m, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    C.objects.link(o)
    o.location = loc
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return o


def cyl(name, r, length, axis, loc, m, seg=24):
    bm = bmesh.new()
    rot = {'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X'), 'Z': Matrix()}[axis]
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=length, matrix=rot)
    return mesh_obj(name, bm, m, loc)


def box(name, size, loc, m):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1)))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * 0.15, segments=2, affect='EDGES')
    o = mesh_obj(name, bm, m, loc)
    for p in o.data.polygons:
        p.use_smooth = False
    return o


def torus(name, R, r, loc, m):
    bm = bmesh.new()
    nu, nv = 64, 12
    vs = [[bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
           for b in [2 * math.pi * j / nv for j in range(nv)]] for a in [2 * math.pi * i / nu for i in range(nu)]]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i][j], vs[(i + 1) % nu][j], vs[(i + 1) % nu][(j + 1) % nv], vs[i][(j + 1) % nv]))
    return mesh_obj(name, bm, m, loc)


def net_bag(name, R, depth, loc, m):
    """Knotted net hanging from a ring: a diamond grid on a bag surface, made into strings by a wireframe."""
    bm = bmesh.new()
    nu, nv = 40, 12
    rows = []
    for j in range(nv + 1):
        t = j / nv
        rr = R * (1 - 0.55 * t ** 1.5)
        z = -depth * t
        rows.append([bm.verts.new((rr * math.cos(2 * math.pi * (i + 0.5 * (j % 2)) / nu),
                                   rr * math.sin(2 * math.pi * (i + 0.5 * (j % 2)) / nu), z)) for i in range(nu)])
    for j in range(nv):
        for i in range(nu):
            a, b = rows[j][i], rows[j][(i + 1) % nu]
            c = rows[j + 1][i if j % 2 == 0 else (i + 1) % nu]
            bm.edges.new((a, c)) if not bm.edges.get((a, c)) else None
            d = rows[j + 1][(i - 1) % nu if j % 2 == 0 else i]
            bm.edges.new((a, d)) if not bm.edges.get((a, d)) else None
    for j in range(nv):
        for i in range(nu):
            q = (rows[j][i], rows[j + 1][i if j % 2 == 0 else (i + 1) % nu], rows[j][(i + 1) % nu])
            try:
                bm.faces.new(q)
            except ValueError:
                pass
    o = mesh_obj(name, bm, m, loc)
    wf = o.modifiers.new('wf', 'WIREFRAME')
    wf.thickness = 0.0025
    wf.use_replace = True
    return o


world()
plastic_b = mat('M_CrateGrey', (0.22, 0.26, 0.22), 0.5)
plastic_w = mat('M_BoxWhite', (0.62, 0.63, 0.6), 0.4)
rope = mat('M_Rope', (0.32, 0.22, 0.08), 0.8)
netm = mat('M_Net', (0.1, 0.32, 0.18), 0.7)
steel = mat('M_Steel', (0.55, 0.55, 0.56), 0.3, metal=1.0)
ground = mat('M_Ground', (0.32, 0.31, 0.29), 0.85, noise=0.5)
bm_ = bmesh.new()
bmesh.ops.create_grid(bm_, x_segments=1, y_segments=1, size=60)
mesh_obj('Ground', bm_, ground)

sk.load(BASE)
if SO and os.path.exists(OCEAN):
    sk.load(OCEAN, tag='oc')
FISH = ('fisher_nocap', 'oc') if SO else ('plant', '')
PORT = ('port_hivis', 'oc') if SO else ('driver', '')


def human(name, outfit, lod='', loc=(0, 0, 0), rot=0.0, seed=0, pose=None, gender='male'):
    ao = sk.person(name, outfit, gender, loc, math.radians(rot), seed=seed, lod=lod)
    if pose:
        sk.set_pose(ao, pose)
    return ao


# ---------------------------------------------------------------- portraits (x 0..9)
heads = []
for i, (nm, (of, lod), seed, g) in enumerate((('plant', ('plant', ''), 3, 'male'), ('fisher', FISH, 5, 'male'),
                                               ('port', PORT, 8, 'male'), ('driver', ('driver', ''), 11, 'male'),
                                               ('fplant', ('plant', ''), 12, 'female'),
                                               ('fbun', ('driver', ''), 14, 'female'))):
    ao = human('Por_' + nm, of, lod, (i * 2.5, 0, 0), 0, seed, gender=g)
    heads.append((nm, ao))

# ---------------------------------------------------------------- mid-distance group (y = 12)
grp = [('plant', '', (-1.6, 12.2, 0), -10, 21, None), ('driver', '', (-0.5, 12.6, 0), 15, 22, None),
       (FISH[0], FISH[1], (0.6, 11.8, 0), 25, 23, sk.POSES['crouch']), (PORT[0], PORT[1], (1.7, 12.3, 0), -20, 24,
                                                                        sk.POSES['kneel']),
       (PORT[0], PORT[1], (2.8, 12.7, 0), 5, 25, None), (FISH[0], FISH[1], (3.9, 12.1, 0), -25, 26, None),
       ('plant', '', (-2.6, 12.5, 0), 20, 27, None)]
for i, (of, lod, loc, rot, seed, pz) in enumerate(grp):
    human('Grp%d' % i, of, lod, loc, rot, seed, pz, gender='female' if i == 6 else 'male')
box('GrpTub', (0.6, 0.4, 0.3), (0.45, 10.95, 0.15), plastic_b)

# ---------------------------------------------------------------- grips (x = 20..)
grips = []


def setup_grip(key, outfit, lod, ox, targets, hands, seed):
    ao = human('G_' + key, outfit, lod, (ox, 0, 0), 0, seed)
    for side, parent, palm, fing, nrm in hands:
        sk.wrap_hand(ao, side, parent, palm, fing, nrm, [(1, 1.0)], C)
    sk.auto_poles([ao])
    bpy.context.view_layer.update()
    sk.settle_reach(ao, 1, 1, step=1, iters=4)
    s.frame_set(1)
    bpy.context.view_layer.update()
    for side, *_ in hands:
        sk.grip(ao, side, target=targets)
    grips.append((key, ao, targets))
    return ao


# crate carried by its side handles (cylinder bars along Y)
ox = 20.0
box('Crate', (0.56, 0.36, 0.26), (ox, -0.40, 0.86), plastic_b)
hr = cyl('CrateBarR', 0.013, 0.13, 'Y', (ox - 0.325, -0.40, 0.95), plastic_b)
hl = cyl('CrateBarL', 0.013, 0.13, 'Y', (ox + 0.325, -0.40, 0.95), plastic_b)
for sx in (-1, 1):
    for sy in (-1, 1):
        box('CrateLug', (0.05, 0.02, 0.05), (ox + sx * 0.30, -0.40 + sy * 0.065, 0.94), plastic_b)
setup_grip('crate', 'plant', '', ox, [hr, hl], [('R', hr, (-0.012, 0, 0.032), (1, 0, 0), (0, 0, -1)),
                                                ('L', hl, (0.012, 0, 0.032), (-1, 0, 0), (0, 0, -1))], 31)
# net bag rim (rope ring + net)
ox = 23.0
rim = torus('NetRim', 0.22, 0.009, (ox - 0.05, -0.60, 0.98), rope)
net = net_bag('NetBag', 0.22, 0.35, (ox - 0.05, -0.60, 0.98), netm)
setup_grip('net', FISH[0], FISH[1], ox, [rim, net], [('R', rim, (-0.03, 0.214, 0.055), (0, -1, 0), (0, 0, -1))], 32)
# fish box edge (thin walls)
ox = 26.0
for nm_, sz, lo in (('BoxN', (0.6, 0.012, 0.25), (0, -0.20, 0)), ('BoxF', (0.6, 0.012, 0.25), (0, -0.60, 0)),
                    ('BoxE', (0.012, 0.4, 0.25), (0.3, -0.40, 0)), ('BoxW', (0.012, 0.4, 0.25), (-0.3, -0.40, 0)),
                    ('BoxB', (0.6, 0.4, 0.012), (0, -0.40, -0.125))):
    box(nm_, sz, (ox - 0.22 + lo[0], lo[1], 0.82 + lo[2]), plastic_w)        # clear of the free hand
edge = bpy.data.objects['BoxN']
setup_grip('box', FISH[0], FISH[1], ox, [edge], [('R', edge, (0.12, 0.035, 0.15), (0, -1, 0), (0, 0, -1))], 33)
# thin rod (rail)
ox = 29.0
rod = cyl('Rod', 0.005, 0.9, 'X', (ox, -0.40, 1.02), steel)
setup_grip('rod', 'plant', '', ox, [rod], [('R', rod, (-0.10, 0.0, 0.024), (0, -1, 0), (0, 0, -1)),
                                           ('L', rod, (0.12, 0.0, 0.024), (0, -1, 0), (0, 0, -1))], 34)

# ---------------------------------------------------------------- render
s.render.engine = 'BLENDER_EEVEE'
e = s.eevee
e.taa_render_samples = 96
for k, v in (('use_raytracing', True), ('use_shadows', True), ('ray_tracing_method', 'SCREEN'),
             ('use_fast_gi', True), ('shadow_ray_count', 2), ('shadow_step_count', 8)):
    try:
        setattr(e, k, v)
    except (AttributeError, TypeError):
        pass
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
s.view_settings.exposure = 0.0
s.render.resolution_percentage = 100
s.render.image_settings.file_format = 'PNG'
cd = bpy.data.cameras.new('Cam')
cam = bpy.data.objects.new('Cam', cd)
C.objects.link(cam)
s.camera = cam
s.frame_set(1)


def shot(name, loc, tgt, lens, w=960, h=540, fstop=None, focus=None):
    if ONLY and not any(name.startswith(o) for o in ONLY):
        return
    cam.location = loc
    d = Vector(tgt) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    cd.dof.use_dof = fstop is not None
    if fstop:
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(focus or tgt) - Vector(loc)).length
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'review.blend'), copy=True)
    bpy.ops.render.render(write_still=True)
    stage('rendered ' + name)


def eye(ao):
    s.frame_set(1)
    bpy.context.view_layer.update()
    hb = ao.pose.bones['head']
    return ao.matrix_world @ (hb.head + (hb.tail - hb.head) * 0.32 + Vector((0, -0.05, 0)))


for i, (nm, ao) in enumerate(heads):
    t = eye(ao)
    az = math.radians((-28, 24, -18, 32, -22, 125)[i])     # fbun: from behind-side to show the bun
    loc = t + Vector((math.sin(az) * 1.15, -math.cos(az) * 1.15, 0.04))
    shot(('t%d_%s' % (i + 1, nm)) if i < 4 else ('t9_' + nm if nm == 'fplant' else 't10_' + nm), loc,
         t + Vector((0, 0, -0.07)), 75, fstop=2.8, focus=t)
for key, ao, tg in grips:
    c = tg[0].matrix_world.translation
    off = {'crate': Vector((-0.42, -0.5, 0.22)), 'net': Vector((-0.45, -0.35, 0.3)),
           'box': Vector((-0.4, -0.35, 0.25)), 'rod': Vector((-0.38, -0.42, 0.2))}[key]
    size = (960, 540) if key in ('crate', 'net') else (480, 540)
    shot({'crate': 't5_crate', 'net': 't6_net', 'box': 't8a_box', 'rod': 't8b_rod'}[key], c + off, c, 55,
         *size, fstop=4.0)
shot('t7_mid', (0.7, 5.0, 1.45), (0.7, 12.2, 0.85), 35)
stage('DONE')
