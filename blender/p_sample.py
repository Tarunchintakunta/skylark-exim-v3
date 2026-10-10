"""p-sample (clip b2, frames 1-192): at the harvest pond, a farm hand kneels on a low sampling landing, dips a sample
bottle with a gloved hand, tests it with a pen pH meter (the LCD reads clearly) and the camera rises away to the exact
opening frame of p-harvest (shared-frame boundary). Built on the p-harvest set: the harvest timeline is shifted to
start at frame 193, so p-sample f192 == p-harvest f1 by construction.
Usage: Blender -b --python blender/p_sample.py -- [out.blend]"""
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skpbr as P            # noqa: E402
import skfarm as F           # noqa: E402
import skhuman as H          # noqa: E402
import sktruck as T          # noqa: E402
from sktruck import Part     # noqa: E402

REPO = os.path.dirname(HERE)
N = 192                      # p-sample length; p-harvest frame 1 lands on N
D = math.radians


def _key(o, f, loc=None, rot=None):
    if loc is not None:
        o.location = loc
        o.keyframe_insert('location', frame=f)
    if rot is not None:
        o.rotation_euler = rot
        o.keyframe_insert('rotation_euler', frame=f)


def _landing(C, x, y0, y1):
    """Low timber sampling landing at the waterline, steps up to the bund."""
    wood = P.grime_paint('SM_Wood', (0.32, 0.24, 0.16), rough=0.8, grime=0.6, streak=0.5, coat=0.0, metal=0.0)
    p = Part()
    z = F.WATER + 0.05                  # floating-deck height: the sample is an arm's length down
    for k in range(9):
        p.box((x, y0 + 0.15 + k * 0.155, z), (1.3, 0.14, 0.04))                  # deck planks
    for sx in (-0.6, 0.6):
        for yy in (y0 + 0.1, y1 - 0.1):
            p.box((x + sx, yy, z - 0.6), (0.08, 0.08, 1.2))                        # posts into the pond
        p.box((x + sx, (y0 + y1) / 2, z - 0.06), (0.06, y1 - y0, 0.08))          # bearers
    for k in range(3):                                                             # steps up the bank
        p.box((x, y0 - 0.25 - k * 0.32, z + 0.12 + k * 0.12), (1.0, 0.3, 0.05))
    p.make('SM_Landing', wood, None, bevel=0.006, coll=C)
    return z


def _bottle(C):
    root = bpy.data.objects.new('SM_Bottle', None)
    C.objects.link(root)
    p = Part()
    p.cyl((0, 0, -0.09), (0, 0, 0.06), 0.032, 24)
    p.cyl((0, 0, 0.06), (0, 0, 0.085), 0.017, 18, r2=0.015)
    p.make('SM_BottleBody', P.plain('SM_PET', (0.85, 0.9, 0.9), 0.05, transmission=0.9, ior=1.45, coat=0.6), root,
           smooth=True, coll=C)
    p = Part()
    p.cyl((0, 0, -0.085), (0, 0, 0.03), 0.03, 24)
    p.make('SM_SampleWater', P.plain('SM_PondWaterIn', (0.32, 0.36, 0.2), 0.05, transmission=0.6, ior=1.33), root,
           smooth=True, coll=C)
    return root


def _meter(C):
    """Pen-type pH tester: grey body, rubber grip, glass bulb probe; LCD with a large clear reading."""
    root = bpy.data.objects.new('SM_Meter', None)
    C.objects.link(root)
    p = Part()
    p.box((0, 0, 0.0), (0.034, 0.02, 0.15))
    p.make('SM_MeterBody', P.plain('SM_MeterGrey', (0.36, 0.38, 0.4), 0.4, coat=0.3), root, bevel=0.008, seg=3,
           coll=C)
    p = Part()
    p.cyl((0, 0, -0.075), (0, 0, -0.13), 0.009, 14)
    p.make('SM_Probe', P.plain('SM_ProbeGlass', (0.8, 0.85, 0.85), 0.05, transmission=0.8, coat=1.0), root,
           smooth=True, coll=C)
    p = Part()
    p.box((0, -0.0105, 0.035), (0.027, 0.002, 0.034))
    p.make('SM_LCD', P.plain('SM_LCDPanel', (0.55, 0.62, 0.5), 0.3, emission=(0.62, 0.7, 0.55), estr=0.35), root,
           coll=C)
    digits = []
    for txt, size, z, x in (('7.8', 0.017, 0.031, -0.0115), ('pH', 0.0065, 0.044, 0.0035)):
        cu = bpy.data.curves.new('SM_Txt_' + txt, 'FONT')
        cu.body = txt
        cu.size = size
        cu.extrude = 0.0002
        t = bpy.data.objects.new('SM_Txt_' + txt, cu)
        C.objects.link(t)
        t.parent = root
        t.location = (x, -0.0118, z - size * 0.35)
        t.rotation_euler = (D(90), 0, 0)
        cu.materials.append(P.plain('SM_LCDDigits', (0.02, 0.025, 0.02), 0.5))
        digits.append(t)
    return root, digits[0]


def add(ctx):
    """ctx: names from p_harvest.build (cx, yb, yw, Cp, cam, tgt)."""
    import plant_chain
    plant_chain.shift_all(N - 1)                     # harvest frame 1 -> N
    s = bpy.context.scene
    cx, yb, yw, Cp, cam, tgt = (ctx[k] for k in ('cx', 'yb', 'yw', 'Cp', 'cam', 'tgt'))
    W = F.WATER
    x = cx + 8.5
    zd = _landing(Cp, x, yw - 0.2, yw + 1.3)
    S = Vector((x, yw + 1.12, zd + 0.02))            # where the sampler kneels, at the landing's front edge

    w = H.person('HUM_Sampler', 'farm_gloves', 'male', coll=Cp, seed=101)
    w.location = S
    w.rotation_euler = (0, 0, D(180))                # faces +Y, over the water
    kneel = {'thigh.L': (95, 6, 0), 'shin.L': (-95, 0, 0), 'foot.L': (10, 0, 0),
             'thigh.R': (-5, 4, 0), 'shin.R': (-120, 0, 0), 'foot.R': (40, 0, 0),
             'spine': (28, 0, 0), 'chest': (12, 0, 0), 'neck': (10, 0, 0), 'head': (14, 0, 0)}
    w.location.z = S.z - 0.42                        # kneeling height
    H.set_pose(w, kneel, 1)
    H.set_pose(w, dict(kneel, spine=(60, 0, 0), chest=(25, 0, 0), neck=(-10, 0, 0)), 30)
    H.set_pose(w, dict(kneel, spine=(60, 0, 0), chest=(25, 0, 0), neck=(-10, 0, 0)), 50)
    H.set_pose(w, dict(kneel, spine=(20, 0, 0), head=(18, 0, 0)), 76)
    H.set_pose(w, dict(kneel, spine=(16, 0, 0), head=(22, 0, 0)), N)
    skr = H.grip(w, 'R')
    for f, v in ((1, 1.0), (57, 1.0), (61, 0.55), (192, 0.55)):     # tight fist on the pole, open round the bottle
        skr.value = v
        skr.keyframe_insert('value', frame=f)
    skl = H.grip(w, 'L', curl=0.85)
    skl.value = 1.0

    # the bottle and the meter move freely; each hand's IK target rides on the object it grips
    bottle = _bottle(Cp)
    meter, reading = _meter(Cp)
    # a 1 m sampling pole with a bottle clamp: the far end dips under the surface; then the bottle comes off into the hand
    pole = bpy.data.objects.new('SM_Pole', None)
    Cp.objects.link(pole)
    pp = Part()
    pp.cyl((0, -0.06, 0), (0, 1.0, 0), 0.012, 12)
    pp.cyl((0, 0.98, -0.03), (0, 0.98, 0.04), 0.036, 18, cap=False)
    pp.make('SM_PoleBody', P.plain('SM_PoleAlu', (0.7, 0.71, 0.72), 0.3, 1.0), pole, smooth=True, coll=Cp)
    pb_ = bpy.data.objects.new('SM_PoleBottle', None)
    Cp.objects.link(pb_)
    pb_.parent = pole
    pb_.location = (0, 0.98, 0.0)
    for ch in bottle.children:
        cc = bpy.data.objects.new(ch.name + '_Pole', ch.data)
        Cp.objects.link(cc)
        cc.parent = pb_
    reach = S + Vector((0.28, 1.15, W - S.z - 0.04))                   # under the surface, a metre out
    for f, loc, pitch in ((1, S + Vector((0.26, 0.2, 0.42)), 18), (20, S + Vector((0.24, 0.24, 0.36)), -4),
                          (32, S + Vector((0.24, 0.26, 0.24)), -21), (46, S + Vector((0.24, 0.26, 0.24)), -21),
                          (54, S + Vector((0.24, 0.2, 0.34)), 6), (60, S + Vector((0.2, -0.25, 0.42)), 38)):
        _key(pole, f, tuple(loc), (D(pitch), 0, 0))
    for f in (63, N):                                    # laid down on the deck once the bottle is off
        _key(pole, f, tuple(S + Vector((0.55, -0.45, -0.005))), (0, 0, D(-12)))
    B62 = S + Vector((0.12, 0.45, 0.6))
    _key(bottle, 1, tuple(B62), (0, 0, 0))
    _key(bottle, N, tuple(B62 + Vector((0, 0, 0.01))), (0, 0, 0))
    import p_harvest as PH0
    for ob, seq in ((bottle, [(1, True), (61, False)]), (pb_, [(1, False), (61, True)])):
        PH0.key_hide(ob, seq)
    lcd_dir = Vector((0.35, 0.22, 0.0)).normalized()                 # toward the close-up camera
    yaw = math.atan2(lcd_dir.x, -lcd_dir.y)
    M122 = S + Vector((-0.05, 0.5, 0.9))
    for f, loc, rot in ((1, S + Vector((-0.24, 0.3, 0.42)), (0, 0, D(170))),
                        (64, S + Vector((-0.22, 0.3, 0.46)), (0, 0, D(170))),
                        (82, B62 + Vector((0, 0, 0.16)), (0, 0, D(170))),
                        (104, B62 + Vector((0, 0, 0.16)), (0, 0, D(170))),
                        (122, M122, (D(-8), 0, yaw)), (N, M122 + Vector((0, 0, 0.005)), (D(-8), 0, yaw))):
        _key(meter, f, tuple(loc), rot)
    # fist round the pole near its end; palm round the bottle's side; meter held from behind (the LCD stays clear)
    for side, ob, palm, fing, nrm, inf in (
            ('R', pole, (-0.02, 0.05, 0.0), (0, 0, -1), (1, 0, 0), ((1, 1.0), (57, 1.0), (61, 0.0))),
            ('R', bottle, (0.0, -0.048, -0.03), (1, 0, 0), (0, 1, 0), ((1, 0.0), (57, 0.0), (61, 1.0))),
            ('L', meter, (0.0, 0.024, -0.045), (1, 0, 0), (0, -1, 0), ((1, 1.0),))):
        H.wrap_hand(w, side, ob, palm, fing, nrm, inf, Cp)
    reading.data.body = '7.8'
    # small drips off the bottle as it leaves the water
    import p_harvest as PH
    drip = PH._drip_mesh()
    for k in range(8):
        d = bpy.data.objects.new('SM_Drip%d' % k, drip)
        Cp.objects.link(d)
        d.scale = (0.45, 0.45, 0.45)
        ph = (k * 0.37) % 1.0
        for f in range(46, 72, 2):
            t = ((f - 46) / 7.0 + ph) % 1.0
            u = min(1.0, max(0.0, (f - 46) / 16.0))
            base = reach.lerp(S + Vector((0.2, 0.6, 0.5)), u)
            d.location = base + Vector(((k % 3 - 1) * 0.01, (k % 2) * 0.008, -0.1 - t * (0.1 + (B62.z - W) * u)))
            d.keyframe_insert('location', frame=f)
        PH.key_hide(d, [(1, True), (48, False), (72, True)])

    # camera: kneeling close-up -> hands -> the LCD -> rises and swings to p-harvest's opening frame
    h1 = [(fc.array_index, fc.evaluate(N)) for fc in T._fcurves(cam.animation_data.action) if fc.data_path == 'location']
    t1 = [(fc.array_index, fc.evaluate(N)) for fc in T._fcurves(tgt.animation_data.action) if fc.data_path == 'location']
    end_cam = Vector([v for _, v in sorted(h1)])
    end_tgt = Vector([v for _, v in sorted(t1)])
    for fc in T._fcurves(cam.animation_data.action) + T._fcurves(tgt.animation_data.action):
        for kp in list(fc.keyframe_points):
            if kp.co.x < N:
                fc.keyframe_points.remove(kp)
    keys = [(1, S + Vector((1.5, 1.9, 0.75)), S + Vector((0.1, 0.6, 0.2))),
            (40, S + Vector((1.45, 1.55, 0.85)), S + Vector((0.2, 0.75, 0.05))),
            (70, S + Vector((0.75, 1.0, 0.75)), S + Vector((0.1, 0.45, 0.55))),
            (100, S + Vector((0.45, 0.85, 0.85)), B62 + Vector((0, 0, 0.12))),
            (124, M122 + lcd_dir * 0.34 + Vector((0, 0, 0.03)), M122 + Vector((0, 0, 0.03))),
            (150, M122 + lcd_dir * 0.31 + Vector((0, 0, 0.035)), M122 + Vector((0, 0, 0.035))),
            (N, end_cam, end_tgt)]
    for f, c, t in keys:
        _key(cam, f, tuple(c))
        _key(tgt, f, tuple(t))
    for o in (cam, tgt):
        for fc in T._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
            fc.update()
    cam.data.dof.aperture_fstop = 2.0
    s.frame_start, s.frame_end = 1, N
    s.render.filepath = '//../render/p-sample/'


if __name__ == '__main__':
    import p_harvest
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p_harvest.build(argv[0] if argv else os.path.join(REPO, 'assets-src/blender/p-sample.blend'), scene='p-sample')
