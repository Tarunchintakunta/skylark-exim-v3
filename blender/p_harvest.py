"""p-harvest (frames 1-288): workers wade at a pond edge drawing a drag net in; the net bag lifts out of the water
dripping with shrimp; shrimp tipped into crates of crushed ice on the bund, ice scooped over, a blank batch tag
clipped on; crates carried into the white reefer truck on the bund road; the truck drives off (+X) and the camera
ends in road-follow framing (matches truck-reverse frame 1 for the cross-fade).
Usage: Blender -b --python blender/p_harvest.py -- [out.blend]"""
import math
import os
import random
import sys
import bpy
import bmesh
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skpbr as P      # noqa: E402
import skfarm as F     # noqa: E402
import sktruck as T    # noqa: E402
import skhuman as H    # noqa: E402
import sklib as L      # noqa: E402
from sktruck import Part  # noqa: E402

REPO = os.path.dirname(HERE)
F0, F1 = 1, 288
D = math.radians
PI, PJ = 6, 0                         # the pond being harvested (north of the road)


def lin(o):
    for fc in T._fcurves(o.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def smoothk(o):
    for fc in T._fcurves(o.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.update()


def key_hide(o, seq, children=True):
    for f, hidden in seq:
        o.hide_render = hidden
        o.hide_viewport = hidden
        o.keyframe_insert('hide_render', frame=f)
        o.keyframe_insert('hide_viewport', frame=f)
    if children:
        for c in o.children:
            key_hide(c, seq)


def net_mat():
    m = bpy.data.materials.get('FARM_NetMesh')
    if m:
        return m
    m = bpy.data.materials.new('FARM_NetMesh')
    m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    Ln = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.035, 0.07, 0.05, 1)
    p.inputs['Roughness'].default_value = 0.45
    p.inputs['Coat Weight'].default_value = 0.4              # wet twine
    tc = nt.nodes.new('ShaderNodeTexCoord')
    outs = []
    for d in ('X', 'Y'):
        w = nt.nodes.new('ShaderNodeTexWave')
        w.wave_type = 'BANDS'
        w.bands_direction = d
        w.wave_profile = 'SIN'
        w.inputs['Scale'].default_value = 12.6           # period 2pi/(10*scale) = 5 cm mesh (UV in metres)
        w.inputs['Distortion'].default_value = 0.6
        w.inputs['Detail'].default_value = 0.0
        Ln.new(tc.outputs['UV'], w.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.72
        mr.inputs['From Max'].default_value = 0.8
        Ln.new(w.outputs['Fac'], mr.inputs['Value'])
        outs.append(mr.outputs[0])
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    Ln.new(outs[0], mx.inputs[0])
    Ln.new(outs[1], mx.inputs[1])
    Ln.new(mx.outputs[0], p.inputs['Alpha'])
    return m


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    rnd = random.Random(7)
    C = F.coll('SET_Farm')
    F.build_terrain(C, x0=-80, x1=220, y0=-140, y1=160, res=0.6, tex='brown_mud_dry', scale=0.22)
    F.build_water(C)
    F.place_aerators(C, rnd, near=(60, 30, 180))
    F.animate_water(F0 - 24, F1 + 48)
    F.ruts(C)
    xm, ym = F.compound(C, rnd)
    F.poles(C, rnd)
    F.feed_trays(C, rnd)
    F.palms(C, rnd, xm, ym)
    F.groves(C, rnd)
    F.birds(C, rnd, 5, F0, F1 + 24, centre=(60, 60, 18))
    H.load(os.path.join(REPO, 'assets-src/blender/humans.blend'))
    Cp = F.coll('SET_Harvest')

    cx, cy = F.pond_centre(PI, PJ)
    hw, hh = F.pond_size(PI, PJ)
    yb = cy - hh                       # bank line (top of the slope, road side)
    yw = yb + 1.2                      # shoreline (water meets the slope)
    TOP, WATER = F.TOP, F.WATER

    # ---------------- truck parked on the road, rear toward the crates; doors open, loading, then drives +X
    R = T.reefer_truck('TRK_RigidReefer', coll=Cp, load=False)
    tx0 = cx - 1.0
    R['root'].location = (tx0, 1.8, TOP + 0.05)
    for d, sg in ((R['door_l'], -1), (R['door_r'], 1)):
        d.rotation_euler = (0, 0, sg * D(100))
        d.keyframe_insert('rotation_euler', frame=F0)
        d.keyframe_insert('rotation_euler', frame=214)
        d.rotation_euler = (0, 0, 0)
        d.keyframe_insert('rotation_euler', frame=226)
    t_go = 234

    def tpath(f):
        t = max(0.0, (f - t_go) / 24)
        return tx0 + 0.5 * 1.3 * t * t, 1.8, 0.0, 0.0
    T.drive(R, tpath, F0, F1 + 12)
    for fc in T._fcurves(R['root'].animation_data.action):
        if fc.data_path == 'location' and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.co.y = TOP + 0.05
    rear_x = tx0 + T.REAR                # world x of the box rear face
    # crates already loaded (visible through the open doors), more appear as they are carried in
    loaded = []
    k = 0
    for ix in range(4):
        for iy in (-0.66, 0.0, 0.66):
            for lv in range(4):
                c = L.crate('TRK_Load%02d' % k, ['blue', 'white', 'blue', 'red'][k % 4],
                            (T.REAR + 0.3 + (ix + 2) * 0.43, iy, T.BZ + 0.04 + lv * 0.3), math.pi / 2, fill='ice',
                            parent=R['root'], mats=_mats(), seed=k)
                _tint(c)
                k += 1
    for ix, iy, lv in ((1, -0.66, 0), (1, 0.0, 0), (1, 0.66, 0), (1, -0.66, 1)):
        c = L.crate('TRK_New%02d' % len(loaded), 'blue', (T.REAR + 0.3 + ix * 0.43, iy, T.BZ + 0.04 + lv * 0.3), math.pi / 2,
                    fill='ice', parent=R['root'], mats=_mats(), seed=90 + len(loaded))
        _tint(c)
        loaded.append(c)

    # ---------------- crates on the bund: ice-filled, receive shrimp, get ice + a tag
    crates = []
    for n in range(4):
        x = cx - 3.4 + n * 0.68
        y = yb - 1.3 + (n % 2) * 0.05
        c = L.crate('HV_Crate%d' % n, 'blue' if n % 2 else 'white', (x, y, TOP + 0.02), D(rnd.uniform(-4, 4)), fill='ice',
                    parent=None, mats=_mats(), seed=200 + n)
        _tint(c)
        crates.append(c)
        sh = bpy.data.objects.new('HV_Crate%d_Shrimp' % n, None)
        Cp.objects.link(sh)
        sh.parent = c
        for m in range(36):                  # a heap on the ice: some on their backs, most on their sides
            F.shrimp('HV_Crate%d_S%02d' % (n, m), (rnd.uniform(-0.22, 0.22), rnd.uniform(-0.12, 0.12),
                                                     0.265 + (m // 18) * 0.022 + rnd.uniform(0, 0.012)),
                     (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28)), parent=sh, C=Cp,
                     scale=rnd.uniform(0.85, 1.1))
        f_tip = 96 + n * 9
        key_hide(sh, [(F0, True), (f_tip, False)])
        ice2 = bpy.data.objects.new('HV_Crate%d_Ice2' % n, L._CRATE['chunks'])
        Cp.objects.link(ice2)
        ice2.parent = c
        ice2.location = (0, 0, 0.27)
        ice2.data.materials[0] if ice2.data.materials else None
        key_hide(ice2, [(F0, True), (f_tip + 18, False)])
        tag = Part()
        tag.box((0.0, 0, 0), (0.07, 0.004, 0.1))
        tg = tag.make('HV_Crate%d_Tag' % n, P.plain('HV_TagBlank', (0.92, 0.92, 0.9), 0.5), c, coll=Cp)
        tg.location = (0.22, -0.205, 0.26)
        key_hide(tg, [(F0, True), (f_tip + 30, False)])
    # ice box + scoop
    p = Part()
    p.box((cx - 5.4, yb - 1.4, TOP + 0.35), (1.1, 0.7, 0.7))
    p.make('HV_IceBox', P.plain('HV_IceBoxWhite', (0.78, 0.79, 0.77), 0.4), None, bevel=0.03, coll=Cp)
    ib = bpy.data.objects.new('HV_IceBoxIce', L._CRATE['ice'])
    Cp.objects.link(ib)
    ib.location = (cx - 5.4, yb - 1.4, TOP + 0.62)
    ib.scale = (1.8, 1.8, 1.0)
    # scales on a table, buckets, a tarp shade
    p = Part()
    p.box((cx - 7.2, yb - 1.6, TOP + 0.4), (1.2, 0.6, 0.04))
    for sx in (-0.55, 0.55):
        for sy in (-0.25, 0.25):
            p.box((cx - 7.2 + sx, yb - 1.6 + sy, TOP + 0.2), (0.04, 0.04, 0.4))
    p.make('HV_Table', P.plain('HV_TableWood', (0.35, 0.26, 0.17), 0.8, bump=0.3), None, coll=Cp)
    p = Part()
    p.box((cx - 7.2, yb - 1.6, TOP + 0.5), (0.4, 0.4, 0.14))
    p.make('HV_Scale', P.plain('HV_ScaleGrey', (0.55, 0.56, 0.57), 0.3, 0.6), None, bevel=0.01, coll=Cp)
    p = Part()
    for k2, (x, y) in enumerate(((cx - 6.3, yb - 0.8), (cx - 6.0, yb - 0.6), (cx + 0.6, yb - 1.0))):
        p.cyl((x, y, TOP), (x, y, TOP + 0.32), 0.15, 14, r2=0.18)
    p.make('HV_Buckets', P.plain('HV_BucketBlue', (0.08, 0.2, 0.4), 0.45), None, coll=Cp)
    p = Part()
    p.box((cx - 6.5, yb - 1.6, TOP + 2.3), (5, 3.5, 0.04))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl((cx - 6.5 + sx * 2.4, yb - 1.6 + sy * 1.7, TOP), (cx - 6.5 + sx * 2.4, yb - 1.6 + sy * 1.7, TOP + 2.3), 0.04, 6)
    p.make('HV_Shade', P.plain('HV_TarpBlue', (0.1, 0.22, 0.38), 0.6, bump=0.3, bump_scale=2), None, coll=Cp)
    # stacked empty crates on the bund
    for k2 in range(6):
        c = L.crate('HV_Empty%d' % k2, 'blue', (cx + 2.0 + (k2 // 3) * 0.66, yb - 1.4, TOP + 0.02 + (k2 % 3) * 0.3), 0.0,
                    mats=_mats())
        _tint(c)

    # ---------------- drag net: float line + net wall, shrinking arc toward the bank (shape keys)
    net = _net(cx, yw, Cp)
    bag = _bag(cx, yw, Cp, rnd)
    # bag path: under water -> lifted out dripping (55-80) -> carried up the bank to the crates (80-96) -> tipped
    pts = [(F0, (cx - 0.2, yw + 2.4, WATER - 0.12), 0.0), (48, (cx - 0.3, yw + 1.6, WATER - 0.08), 0.0),
           (62, (cx - 0.4, yw + 1.0, WATER + 0.35), 0.0), (78, (cx - 0.6, yw + 0.2, WATER + 1.12), 0.0),
           (92, (cx - 2.4, yb - 0.9, TOP + 1.2), 0.0), (102, (cx - 2.7, yb - 1.25, TOP + 0.8), 1.2),
           (128, (cx - 1.3, yb - 1.25, TOP + 0.8), 1.4), (140, (cx - 0.4, yb - 0.4, TOP + 0.9), 0.0)]
    for f, loc, tip in pts:
        bag.location = loc
        bag.rotation_euler = (tip, 0, 0)
        bag.keyframe_insert('location', frame=f)
        bag.keyframe_insert('rotation_euler', frame=f)
    smoothk(bag)
    key_hide(bag, [(F0, False), (141, True)])
    # shrimp inside the bag disappear as the crates fill
    for n, ch in enumerate([c for c in bag.children if c.name.startswith('HV_BagShrimp')]):
        key_hide(ch, [(F0, False), (100 + (n % 4) * 9, True)])
    # drips under the bag while it is lifted
    for k2 in range(14):
        d = bpy.data.objects.new('HV_Drip%d' % k2, _drip_mesh())
        Cp.objects.link(d)
        ph = rnd.uniform(0, 1)
        for f in range(56, 100, 2):
            t = ((f - 56) / 10.0 + ph) % 1.0
            bl = _bag_at(pts, f)
            d.location = (bl[0] + rnd.uniform(-0.25, 0.25), bl[1] + rnd.uniform(-0.2, 0.2), bl[2] - 0.45 - t * 0.9)
            d.keyframe_insert('location', frame=f)
        key_hide(d, [(F0, True), (58, False), (98, True)])

    # ---------------- workers
    def worker(nm, outfit, g, seed):
        return H.person(nm, outfit, g, coll=Cp, seed=seed)

    def z_at(x, y):
        return F.height(x, y)

    pull = {'spine': (18, 0, 0), 'upperarm': (55, -6, 0), 'forearm': (35, 0, 0), 'thigh': (15, 4, 0), 'shin': (-20, 0, 0)}
    # two waders hold the net ends and walk it in toward the bank
    for k2, (x0, x1) in enumerate(((cx - 4.5, cx - 2.2), (cx + 4.0, cx + 1.4))):
        w = worker('HUM_Wader%d' % k2, 'farm', 'male', 60 + k2)
        y0, y1 = yb + 2.0, yb + 1.35
        H.walk_cycle(w, F0, 60, [(F0, (x0, y0)), (60, (x1, y1))], stride=0.45, base=pull, arms=False, step=2)
        for fc in T._fcurves(w.animation_data.action):
            if fc.data_path == 'location' and fc.array_index == 2:
                for kp in fc.keyframe_points:
                    f = kp.co.x
                    t = max(0.0, min(1.0, (f - F0) / 59))
                    xx, yy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                    kp.co.y += z_at(xx, yy)
                    kp.handle_left.y = kp.handle_right.y = kp.co.y
        w.rotation_euler = (0, 0, D(180 + (25 if k2 else -25)))
        w.keyframe_insert('rotation_euler', frame=62)
        sg = 1 if k2 else -1
        for side, off in (('L', -0.12), ('R', 0.12)):
            e = bpy.data.objects.new('HV_NetEnd%d%s' % (k2, side), None)
            Cp.objects.link(e)
            for f, (ex, ey, ez) in ((F0, (cx - 0.3 + sg * 4.6, yw + 1.0 + off, WATER + 0.36)),
                                    (60, (cx - 0.3 + sg * 1.4, yw + 0.6 + off, WATER + 0.48)),
                                    (80, (cx - 0.3 + sg * 1.2, yw + 0.3 + off, WATER + 0.62))):
                e.location = (ex, ey, ez)
                e.keyframe_insert('location', frame=f)
            c = w.pose.bones['forearm.' + side].constraints.new('IK')
            c.target = e
            c.chain_count = 3
            c.use_tail = True
            for f, v in ((F0, 1.0), (78, 1.0), (86, 0.0)):
                c.influence = v
                c.keyframe_insert('influence', frame=f)
        H.set_pose(w, {'spine': (22, 0, 0), 'upperarm': (50, -8, 0), 'forearm': (55, 0, 0), 'thigh': (12, 4, 0),
                       'shin': (-18, 0, 0)}, 70)
        H.set_pose(w, {'spine': (10, 0, 0), 'upperarm': (30, -12, 0), 'forearm': (60, 0, 0)}, 82)
        rest = {'spine': (4, 0, 0), 'upperarm': (6, -18, 0), 'forearm': (24, 0, 0), 'head': (8, 0, 0)}
        H.jitter(w, rest, 92, 140, every=16, amp=4, seed=k2)
        H.jitter(w, H.POSES['look'], 150, F1 + 10, every=24, amp=5, seed=k2 + 9)
    # two lifters raise the bag, carry it up and tip it into the crates: lifter 0 hauls on the mouth rope with both
    # hands, lifter 1 takes the weight under the belly; both stay at arm's length from the bag along its path
    lifters = []
    grips = (((-0.03, 0.0, MOUTH_HANG + 0.2), (0.02, 0.0, MOUTH_HANG + 0.1)),        # rope, hand over hand
             ((0.27, -0.17, 0.08), (0.17, -0.25, -0.05)))                             # belly / under the bag
    offs = ((-0.40, -0.50), (0.46, -0.42))
    for k2, side in enumerate((-1, 1)):
        w = worker('HUM_Lifter%d' % k2, 'farm_long' if k2 else 'farm', 'male', 70 + k2)
        lifters.append(w)
        for hs, gl in zip(('L', 'R') if k2 == 0 else ('R', 'L'), grips[k2]):
            hand = bpy.data.objects.new('HV_BagHand%d%s' % (k2, hs), None)
            Cp.objects.link(hand)
            hand.parent = bag
            hand.location = gl
            ik = w.pose.bones['forearm.' + hs].constraints.new('IK')
            ik.target = hand
            ik.chain_count = 3
            ik.use_tail = True
            # lifter 1 lets go of the belly as lifter 0 tips the bag by the rope
            for f, v in (((F0, 0.0), (50, 0.0), (56, 1.0), (128, 1.0), (134, 0.0)) if k2 == 0 else
                         ((F0, 0.0), (50, 0.0), (56, 1.0), (92, 1.0), (98, 0.0))):
                ik.influence = v
                ik.keyframe_insert('influence', frame=f)
        ox, oy = offs[k2]
        path = [(f, (loc[0] + ox, loc[1] + oy)) for f, loc, _ in pts if f <= 128]
        path = [(F0, (path[0][1][0], path[0][1][1] - 0.2))] + path[1:]
        path.append((160, (cx + 3.6 + side * 0.8, yb - 1.0)))
        H.walk_cycle(w, F0, 160, path, stride=0.45,
                     base={'spine': (24 if k2 else 12, 0, 0), 'thigh': (14 if k2 else 0, 3, 0),
                           'shin': (-18 if k2 else 0, 0, 0), 'upperarm': (10, -16, 0), 'forearm': (30, 0, 0)},
                     arms=False, step=2)
        for fc in T._fcurves(w.animation_data.action):
            if fc.data_path == 'location' and fc.array_index == 2:
                for kp in fc.keyframe_points:
                    xy = _path_at(path, kp.co.x)
                    kp.co.y += z_at(*xy)
                    kp.handle_left.y = kp.handle_right.y = kp.co.y
        if k2:
            H.set_pose(w, {'spine': (14, 0, 0), 'upperarm': (8, -14, 0), 'forearm': (35, 0, 0), 'head': (12, 0, 0)}, 102)
        H.jitter(w, H.POSES['stand'], 162, F1 + 10, every=24, amp=4, seed=k2 + 30)
    _ripples(Cp, [bpy.data.objects[n] for n in ('HUM_Wader0', 'HUM_Wader1')] + lifters, z_at, WATER)
    # ice scooper at the crates
    w = worker('HUM_Scooper', 'farm_long', 'female', 80)
    w.location = (cx - 2.0, yb - 2.15, TOP)
    w.rotation_euler = (0, 0, D(170))
    scoop_pose = {'spine': (35, 0, 0), 'chest': (10, 0, 0), 'upperarm': (60, -5, 0), 'forearm': (40, 0, 0), 'head': (10, 0, 0)}
    H.jitter(w, H.POSES['look'], F0, 100, every=24, amp=4, seed=5)
    H.jitter(w, scoop_pose, 108, 170, every=8, amp=8, seed=6)
    H.jitter(w, H.POSES['stand'], 176, F1 + 10, every=24, amp=4, seed=7)
    # carriers: crates from the bund into the truck (crate parented to the carrier's hands)
    for k2, (fs, crate_n, slot) in enumerate(((150, 0, 0), (162, 1, 1))):
        w = worker('HUM_Carrier%d' % k2, 'farm_long', 'male', 90 + k2)
        cr = crates[crate_n]
        a = (cr.location.x - 0.5 * (1 if k2 else -1), cr.location.y - 0.6)
        b = (rear_x - 0.9, 1.8 + (0.5 if k2 else -0.5))
        w.location = (a[0], a[1], TOP)
        w.rotation_euler = (0, 0, 0)
        H.jitter(w, H.POSES['look'], F0, fs - 8, every=24, amp=4, seed=k2 + 40)
        H.set_pose(w, H.POSES['lift_low'], fs)
        H.set_pose(w, H.POSES['carry'], fs + 8)
        H.walk_cycle(w, fs + 8, fs + 48, [(fs + 8, a), (fs + 48, b)], stride=0.6, base=H.POSES['carry'], arms=False, step=2)
        H.set_pose(w, {'spine': (10, 0, 0), 'upperarm': (60, -8, 0), 'forearm': (40, 0, 0)}, fs + 56)
        H.set_pose(w, H.POSES['stand'], fs + 66)
        w.keyframe_insert('location', frame=fs + 66)
        w.location = (b[0] + 1.6 + k2 * 0.9, 5.4 + k2 * 0.5, TOP)
        w.keyframe_insert('location', frame=fs + 90)
        H.jitter(w, H.POSES['look'], fs + 92, F1 + 10, every=24, amp=4, seed=k2 + 50)
        for f, dz in ((fs - 6, 0.0), (fs, -0.14), (fs + 8, 0.0)):    # knees bend: hips drop for the pick-up
            bpy.context.scene.frame_set(f)
            w.location.z = TOP + dz
            w.keyframe_insert('location', index=2, frame=f)
        # the crate follows the carrier: hand-height offset in front while walking, then appears in the truck
        cr.parent = None
        cr.keyframe_insert('location', frame=fs)
        cr.keyframe_insert('rotation_euler', frame=fs)
        for f in range(fs + 8, fs + 50, 2):
            p0 = _path_at([(fs + 8, a), (fs + 48, b)], f)
            nxt = _path_at([(fs + 8, a), (fs + 48, b)], f + 2)
            dv = Vector((nxt[0] - p0[0], nxt[1] - p0[1]))
            dv = dv.normalized() if dv.length > 1e-4 else Vector((-1, 0))
            cr.location = (p0[0] + dv.x * 0.42, p0[1] + dv.y * 0.42, TOP + 0.85)
            cr.rotation_euler = (0, 0, math.atan2(dv.y, dv.x) + math.pi / 2)
            cr.keyframe_insert('location', frame=f)
            cr.keyframe_insert('rotation_euler', frame=f)
        for side, hx in (('L', -0.27), ('R', 0.27)):
            e = bpy.data.objects.new('%s_Handle%s' % (cr.name, side), None)
            Cp.objects.link(e)
            e.parent = cr
            e.location = (hx, 0, 0.22)
            c = w.pose.bones['forearm.' + side].constraints.new('IK')
            c.target = e
            c.chain_count = 3
            c.use_tail = True
            for f, v in ((F0, 0.0), (fs - 2, 0.0), (fs + 4, 1.0), (fs + 50, 1.0), (fs + 54, 0.0)):
                c.influence = v
                c.keyframe_insert('influence', frame=f)
        key_hide(cr, [(F0, False), (fs + 52, True)])
        key_hide(loaded[slot], [(F0, True), (fs + 52, False)])
    # every hand on the net rope, the bag or a crate handle: move the bodies until the IK hands land (2 fps check)
    for n_, a_, b_ in (('HUM_Wader0', F0, 90), ('HUM_Wader1', F0, 90), ('HUM_Lifter0', 44, 136), ('HUM_Lifter1', 44, 100),
                       ('HUM_Carrier0', 140, 210), ('HUM_Carrier1', 152, 222)):
        ao = bpy.data.objects[n_]
        H.settle_reach(ao, a_, b_, step=1, iters=10, max_shift=0.5, win=1 if 'Carrier' in n_ else 3,
                       z_fn=z_at if 'Carrier' not in n_ else None)
    # contact grips (library r8): with every body settled, each hand's fingers close on the rope, bag or crate rim
    def _ms(o):
        return [o] if o.type == 'MESH' else [c for c in o.children_recursive if c.type == 'MESH'][:6]
    net_ms = [o for o in (bpy.data.objects.get('HV_Net'), bpy.data.objects.get('HV_NetFloats')) if o]
    holds = [('HUM_Wader0', s_, net_ms, 40) for s_ in 'LR'] + [('HUM_Wader1', s_, net_ms, 40) for s_ in 'LR']
    holds += [('HUM_Lifter0', s_, _ms(bag), 90) for s_ in 'LR'] + [('HUM_Lifter1', s_, _ms(bag), 74) for s_ in 'LR']
    holds += [('HUM_Carrier%d' % k2, s_, _ms(crates[k2]), fs_ + 20) for k2, fs_ in ((0, 150), (1, 162)) for s_ in 'LR']
    for n_, sd_, ms_, f_ in holds:
        bpy.context.scene.frame_set(f_)
        try:
            H.grip(bpy.data.objects[n_], sd_, target=ms_) if ms_ else H.grip(bpy.data.objects[n_], sd_, curl=0.85)
        except Exception as e:
            print('HOLD fallback', n_, sd_, e)
            H.grip(bpy.data.objects[n_], sd_, curl=0.85)
    # driver waiting by the cab, then gets in
    drv = worker('HUM_Driver', 'driver', 'male', 99)
    drv.location = (tx0 + 5.2, -0.4, TOP)
    drv.rotation_euler = (0, 0, D(140))
    H.jitter(drv, H.POSES['look'], F0, 200, every=24, amp=4, seed=99)
    key_hide(drv, [(F0, False), (222, True)])

    # ---------------- camera
    cam = L.camera('Camera', 35, (0, 0, 3))
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 2.8
    tgt = bpy.data.objects.new('CAM_Target', None)
    s.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cam.data.dof.focus_object = tgt

    def follow(f):
        x, y, hd, _ = tpath(f)
        return (x - 9.3, y + 0.25, TOP + 3.1), (x + 5.5, y - 0.4, TOP + 1.7)
    keys = [(F0, (cx + 3.4, yw + 8.5, WATER + 1.5), (cx - 0.4, yw + 0.8, WATER + 0.3)),
            (40, (cx + 3.0, yw + 6.8, WATER + 1.45), (cx - 0.4, yw + 0.9, WATER + 0.4)),
            (58, (cx + 1.7, yw + 2.7, WATER + 0.85), (cx - 0.4, yw + 1.0, WATER + 0.25)),
            (74, (cx + 1.15, yw + 1.85, WATER + 1.05), (cx - 0.55, yw + 0.45, WATER + 0.7)),
            (90, (cx + 2.4, yw + 3.4, WATER + 1.8), (cx - 1.6, yw - 0.9, WATER + 1.0)),
            (118, (cx + 3.2, yb + 3.4, TOP + 1.7), (cx - 2.2, yb - 1.3, TOP + 0.35)),
            (150, (cx + 2.6, yb + 3.0, TOP + 1.8), (cx - 2.0, yb - 1.5, TOP + 0.5)),
            (195, (rear_x + 6.5, yb + 1.6, TOP + 2.5), (rear_x - 0.6, 1.8, TOP + 1.3)),
            (232, (rear_x - 3.2, 6.4, TOP + 2.8), (rear_x + 1.0, 1.8, TOP + 1.6))]
    for f in (256, F1, F1 + 12):
        cl, tl = follow(f)
        keys.append((f, cl, tl))
    for f, loc, t in keys:
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
    smoothk(cam)
    smoothk(tgt)

    wm = bpy.data.materials['FARM_PondWater']            # harvest pond: drained low, turbid olive-brown
    for n in wm.node_tree.nodes:
        if n.type == 'VALTORGB':
            for e, col in zip(n.color_ramp.elements, ((0.05, 0.055, 0.03, 1), (0.07, 0.06, 0.035, 1),
                                                      (0.045, 0.055, 0.035, 1))):
                e.color = col
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs['Roughness'].default_value = 0.12
    for m in list(bpy.data.materials):
        n = m.name
        if n.startswith('HUM_'):
            P.add_dust(m, top=WATER + 0.4, bottom=WATER - 0.05, color=(0.07, 0.06, 0.045), amount=0.6, rough=0.18,
                       scale=1.5, tag='wet')
        elif n.startswith('TRK_') and not any(t in n for t in ('Glass', 'Lamp', 'Refl', 'Interior', 'FloorAlu')):
            P.add_dust(m, top=TOP + 1.4, bottom=TOP + 0.1, color=(0.30, 0.22, 0.14), amount=0.7, rough=0.9, scale=3.0,
                       tag='mud')
        elif n.startswith('CR_'):
            P.add_dust(m, top=1000, color=(0.30, 0.23, 0.15), amount=0.35, rough=0.9, scale=6.0, tag='mud')
    az_h, el_h = P.hdri_sun('qwantani_mid_morning_puresky_4k.hdr')
    sun_az = 130.0
    P.hdri_world('qwantani_mid_morning_puresky_4k.hdr', strength=0.9, rot_deg=sun_az - az_h, sun_elev=el_h, sun_az=sun_az,
                 sun_energy=5.0, sun_color=(1.0, 0.92, 0.8))
    P.sky_haze()                                          # warm dusty haze low in the sky
    P.look_settings('exterior', exposure=0.0, haze=(160.0, 900.0, (0.9, 0.82, 0.7), 0.12))
    s.frame_start, s.frame_end = F0, F1
    s.frame_current = F0
    s.render.filepath = '//../render/p-harvest/'
    if hasattr(H, 'auto_poles'):
        print('POLES', H.auto_poles())          # elbows down and back on every pole-less arm IK
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('OUT built p-harvest', out)


_MM = {}


def _mats():
    if 'm' not in _MM:
        _MM['m'] = L.M()
    return _MM['m']


CRATE_COL = {'blue': (0.05, 0.10, 0.19), 'red': (0.19, 0.065, 0.055), 'white': (0.66, 0.67, 0.65)}


def _tint(c):
    for col, rgb in CRATE_COL.items():
        if c.material_slots[0].material and col in c.material_slots[0].material.name.lower():
            c.material_slots[0].material = P.grime_paint('CR_%s' % col, rgb, rough=0.42, grime=0.35, streak=0.15, coat=0.0,
                                                         metal=0.0)


def _path_at(path, f):
    pts = sorted(path)
    if f <= pts[0][0]:
        return pts[0][1]
    for (fa, a), (fb, b) in zip(pts, pts[1:]):
        if fa <= f <= fb:
            t = (f - fa) / max(1e-6, fb - fa)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return pts[-1][1]


def _bag_at(pts, f):
    for (fa, a, _), (fb, b, _) in zip(pts, pts[1:]):
        if fa <= f <= fb:
            t = (f - fa) / (fb - fa)
            return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
    return pts[-1][1]


_DRIP = {}


def _drip_mesh():
    if 'm' not in _DRIP:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.012)
        for v in bm.verts:
            v.co.z *= 1.4
        me = bpy.data.meshes.new('HV_DripMesh')
        bm.to_mesh(me)
        bm.free()
        me.materials.append(P.plain('HV_Water', (0.8, 0.85, 0.85), 0.02, transmission=0.9, ior=1.33))
        _DRIP['m'] = me
    return _DRIP['m']


def _net(cx, yw, C):
    """Seine net: a ring of floats on the surface and a hanging net wall; shape key 'In' pulls it to the bank."""
    W = F.WATER
    floats = P.plain('HV_FloatFoam', (0.62, 0.30, 0.07), 0.55, coat=0.2)   # small weathered orange foam floats
    p = Part()
    bm = p.bm
    n = 40
    top, bot = [], []
    for i in range(n + 1):
        a = math.pi * i / n
        x = cx - 0.3 - math.cos(a) * 4.6
        y = yw + 1.0 + math.sin(a) * 5.0
        top.append(bm.verts.new((x, y, W + 0.38)))
        bot.append(bm.verts.new((x, y, W - 0.7)))
    for i in range(n):
        bm.faces.new((top[i], top[i + 1], bot[i + 1], bot[i]))
    o = p.make('HV_Net', net_mat(), None, coll=C)
    me = o.data
    uv = me.uv_layers.new(name='UV')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (math.atan2(v.y - yw - 1.0, v.x - cx + 0.3) * 4.8, v.z)
    o.shape_key_add(name='Basis')
    sk = o.shape_key_add(name='In')
    for i, v in enumerate(me.vertices):
        k = i // 2
        a = math.pi * k / n
        x = cx - 0.3 - math.cos(a) * 1.4
        y = yw + 0.6 + math.sin(a) * 1.3
        sk.data[i].co = (x, y, v.co.z + (0.45 if v.co.z < W - 0.3 else 0.12))
    for f, v in ((1, 0.0), (60, 1.0)):
        sk.value = v
        sk.keyframe_insert('value', frame=f)
    key_hide(o, [(1, False), (82, True)], children=False)
    # floats along the head rope follow the same pull (own mesh, same shape-key timing)
    fl = Part()
    owner = []
    centres = []
    for i in range(0, 2 * n + 1):
        a = math.pi * i / (2 * n)
        c0 = Vector((cx - 0.3 - math.cos(a) * 4.6, yw + 1.0 + math.sin(a) * 5.0, W + 0.38))
        c1 = Vector((cx - 0.3 - math.cos(a) * 1.4, yw + 0.6 + math.sin(a) * 1.3, W + 0.5))
        tg = Vector((math.sin(a) * 4.6, math.cos(a) * 5.0, 0)).normalized() * 0.05
        before = len(fl.bm.verts)
        if i % 3 == 0:
            fl.cyl(c0 - tg, c0 + tg, 0.032, 8)             # float threaded on the head rope
        else:
            fl.cyl(c0 - tg * 4, c0 + tg * 4, 0.007, 5)     # head rope segment
        owner += [len(centres)] * (len(fl.bm.verts) - before)
        centres.append(c1 - c0)
    fo = fl.make('HV_NetFloats', floats, None, smooth=True, coll=C)
    fo.shape_key_add(name='Basis')
    sk2 = fo.shape_key_add(name='In')
    for i, v in enumerate(fo.data.vertices):
        sk2.data[i].co = v.co + centres[owner[i]]
    for f, v in ((1, 0.0), (60, 1.0)):
        sk2.value = v
        sk2.keyframe_insert('value', frame=f)
    key_hide(fo, [(1, False), (82, True)], children=False)
    return o


def _bag_mesh_mat():
    """Fine diamond-mesh knotless netting (about 2 cm), wet dark-green twine; alpha + bump from the twine mask."""
    m = bpy.data.materials.get('FARM_BagMesh')
    if m:
        return m
    m = bpy.data.materials.new('FARM_BagMesh')
    m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    Ln = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.03, 0.065, 0.045, 1)
    p.inputs['Roughness'].default_value = 0.35
    p.inputs['Coat Weight'].default_value = 0.5
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(45))     # diamonds, not squares
    Ln.new(tc.outputs['UV'], mp.inputs['Vector'])
    outs = []
    for d in ('X', 'Y'):
        w = nt.nodes.new('ShaderNodeTexWave')
        w.wave_type = 'BANDS'
        w.bands_direction = d
        w.wave_profile = 'SIN'
        w.inputs['Scale'].default_value = 30.0
        w.inputs['Distortion'].default_value = 0.4
        w.inputs['Detail'].default_value = 0.0
        Ln.new(mp.outputs[0], w.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.84
        mr.inputs['From Max'].default_value = 0.93
        Ln.new(w.outputs['Fac'], mr.inputs['Value'])
        outs.append(mr.outputs[0])
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    Ln.new(outs[0], mx.inputs[0])
    Ln.new(outs[1], mx.inputs[1])
    Ln.new(mx.outputs[0], p.inputs['Alpha'])
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = 0.7
    b.inputs['Distance'].default_value = 0.003
    Ln.new(mx.outputs[0], b.inputs['Height'])
    Ln.new(b.outputs[0], p.inputs['Normal'])
    return m


def _mass_mat():
    """Packed live shrimp seen through the mesh: wet translucent grey bodies with pink-brown banding."""
    m = bpy.data.materials.get('HV_ShrimpMass')
    if m:
        return m
    m = bpy.data.materials.new('HV_ShrimpMass')
    m.use_nodes = True
    nt = m.node_tree
    Ln = nt.links
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1.0, 1.0, 2.2)
    Ln.new(tc.outputs['Object'], mp.inputs['Vector'])
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 26.0
    vo.inputs['Randomness'].default_value = 1.0
    Ln.new(mp.outputs[0], vo.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.30, 0.31, 0.29, 1)
    ramp.color_ramp.elements[1].color = (0.46, 0.33, 0.27, 1)
    e = ramp.color_ramp.elements.new(0.55)
    e.color = (0.40, 0.40, 0.37, 1)
    Ln.new(vo.outputs['Color'], ramp.inputs[0])
    band = nt.nodes.new('ShaderNodeTexWave')                   # body segments
    band.inputs['Scale'].default_value = 60.0
    band.inputs['Distortion'].default_value = 3.0
    Ln.new(mp.outputs[0], band.inputs['Vector'])
    bm_ = nt.nodes.new('ShaderNodeMix')
    bm_.data_type = 'RGBA'
    bm_.blend_type = 'MULTIPLY'
    bm_.inputs[0].default_value = 0.35
    Ln.new(ramp.outputs[0], bm_.inputs[6])
    Ln.new(band.outputs['Color'], bm_.inputs[7])
    Ln.new(bm_.outputs[2], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.22
    p.inputs['Coat Weight'].default_value = 0.7
    p.inputs['Subsurface Weight'].default_value = 0.25
    p.inputs['Subsurface Scale'].default_value = 0.01
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.8
    bp.inputs['Distance'].default_value = 0.01
    Ln.new(vo.outputs['Distance'], bp.inputs['Height'])
    Ln.new(bp.outputs[0], p.inputs['Normal'])
    return m


# cod-end shapes (local, origin = bag centre): 'rest' slumped in the water, 'hang' sagging by gravity from the mouth
BAG_SHAPES = {'rest': (0.20, 0.50, 0.42, 0.76), 'hang': (0.42, 0.95, 0.30, 0.72)}   # mouth z, length, belly r, belly u
MOUTH_HANG = 0.42


def _bag_profile(shape, u):
    mz, ln, rb, ub = BAG_SHAPES[shape]
    z = mz - ln * u
    if u <= ub:
        r = 0.05 + (rb - 0.05) * math.sin(0.5 * math.pi * u / ub) ** 0.8
    else:
        q = (u - ub) / (1 - ub)
        r = rb * math.sqrt(max(0.0, 1 - q * q))
    return r, z


def _bag(cx, yw, C, rnd):
    """Net bag (cod end) full of shrimp: soft diamond-mesh sack; slumped in the water, sags from the mouth when
    lifted (55-62), shrimp press through the mesh, rope cinch at the mouth. Lifted out at 55-80."""
    root = bpy.data.objects.new('HV_Bag', None)
    C.objects.link(root)
    root.scale = (0.82, 0.82, 0.82)               # ~80 cm cod end, a two-man lift
    nr, npf = 32, 24
    waves = [(rnd.randint(3, 9), rnd.uniform(4, 16), rnd.uniform(0, 6.3), rnd.uniform(0.015, 0.03)) for _ in range(5)]

    def lump(th, u):                       # shrimp bodies pushing the soft mesh out
        return 1 + sum(a * math.sin(k * th + f * u + ph) for k, f, ph, a in waves) * min(1.0, u * 4)

    def build(name, mat, shrink, cap):
        bm = bmesh.new()
        rings = []
        for j in range(npf):
            u = j / npf
            ring = []
            for i in range(nr):
                th = 2 * math.pi * i / nr
                ring.append(bm.verts.new((0, 0, 0)))
            rings.append(ring)
        tip = bm.verts.new((0, 0, 0))
        for j in range(npf - 1):
            for i in range(nr):
                bm.faces.new((rings[j][i], rings[j][(i + 1) % nr], rings[j + 1][(i + 1) % nr], rings[j + 1][i]))
        for i in range(nr):
            bm.faces.new((rings[-1][i], rings[-1][(i + 1) % nr], tip))
        if cap:
            bm.faces.new(list(reversed(rings[0])))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        C.objects.link(o)
        o.parent = root
        me.materials.append(mat)

        def co(shape):
            out = []
            for j in range(npf):
                u = j / npf
                r, z = _bag_profile(shape, u)
                for i in range(nr):
                    th = 2 * math.pi * i / nr
                    rr = r * lump(th, u) * shrink
                    out.append(Vector((math.cos(th) * rr * 1.06, math.sin(th) * rr, z if shrink == 1 else z - 0.02)))
            out.append(Vector((0, 0, _bag_profile(shape, 1.0)[1] * (1 if shrink == 1 else 0.97))))
            return out
        rest, hang = co('rest'), co('hang')
        for v, c in zip(me.vertices, rest):
            v.co = c
        o.shape_key_add(name='Basis')
        k = o.shape_key_add(name='Hang')
        for i, c in enumerate(hang):
            k.data[i].co = c
        uv = me.uv_layers.new(name='UV')
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                j, i = divmod(vi, nr)
                th = 2 * math.pi * i / nr
                if vi == len(me.vertices) - 1:
                    j, th = npf, 0.0
                # seam: the last column wraps to 2*pi so the diamonds stay continuous
                if poly.vertices[:] and max(me.loops[l2].vertex_index % nr for l2 in poly.loop_indices) == nr - 1 \
                        and min(me.loops[l2].vertex_index % nr for l2 in poly.loop_indices) == 0 and i == 0:
                    th = 2 * math.pi
                uv.data[li].uv = (th * 0.29, j / npf * 1.05)
        for f, v in ((F0, 0.0), (52, 0.0), (62, 1.0)):
            k.value = v
            k.keyframe_insert('value', frame=f)
        for poly in me.polygons:
            poly.use_smooth = True
        return o
    build('HV_BagNet', _bag_mesh_mat(), 1.0, False)
    mass = build('HV_BagMass', _mass_mat(), 0.93, True)
    # bag empties as it is tipped into the crates
    for f, sc in ((F0, 1.0), (100, 1.0), (128, 0.25)):
        mass.scale = (sc, sc, sc)
        mass.keyframe_insert('scale', frame=f)
    key_hide(mass, [(F0, False), (129, True)], children=False)
    # rope: cinch ring round the mouth and a short haul rope up to the hands (moves with the mouth)
    rp = Part()
    for i in range(14):
        a0, a1 = 2 * math.pi * i / 14, 2 * math.pi * (i + 1) / 14
        rp.cyl((math.cos(a0) * 0.055, math.sin(a0) * 0.05, 0.2), (math.cos(a1) * 0.055, math.sin(a1) * 0.05, 0.2), 0.008, 6)
    pts = [(0, 0, 0.2), (0.01, 0.0, 0.3), (-0.005, 0.01, 0.4), (0.0, 0.0, 0.46)]
    for a, b in zip(pts, pts[1:]):
        rp.cyl(a, b, 0.009, 6)
    ro = rp.make('HV_BagRope', P.plain('HV_RopeBlue', (0.08, 0.17, 0.30), 0.7, bump=0.4), root, smooth=True, coll=C)
    ro.shape_key_add(name='Basis')
    kr = ro.shape_key_add(name='Hang')
    for i, v in enumerate(ro.data.vertices):
        kr.data[i].co = v.co + Vector((0, 0, MOUTH_HANG - 0.2))
    for f, v in ((F0, 0.0), (52, 0.0), (62, 1.0)):
        kr.value = v
        kr.keyframe_insert('value', frame=f)
    # shrimp pressed against the mesh (hang shape), shown once the bag hangs
    for m in range(70):
        u = rnd.uniform(0.35, 0.97)
        th = rnd.uniform(0, 2 * math.pi)
        r, z = _bag_profile('hang', u)
        rr = r * lump(th, u) * 0.95
        loc = (math.cos(th) * rr * 1.06, math.sin(th) * rr, z)
        sh = F.shrimp('HV_BagShrimp%02d' % m, loc, (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), th + math.pi / 2 +
                      rnd.uniform(-0.8, 0.8)), parent=root, C=C, scale=rnd.uniform(0.9, 1.15))
        key_hide(sh, [(F0, True), (61, False)], children=False)
    # a few shrimp flick (small rotation jitter)
    for ch in [c for c in root.children if c.name.startswith('HV_BagShrimp')][:12]:
        for f in range(62, 100, 3):
            ch.rotation_euler.x += rnd.uniform(-0.5, 0.5)
            ch.keyframe_insert('rotation_euler', frame=f)
    # water running off the belly while it hangs: droplets falling from the mesh, staggered, accelerating
    dm = _drip_mesh()
    for k in range(9):
        th = rnd.uniform(0, 2 * math.pi)
        u = rnd.uniform(0.82, 0.98)
        r, z = _bag_profile('hang', u)
        x0, y0 = math.cos(th) * r * 0.9, math.sin(th) * r * 0.9
        for j in range(3):
            d = bpy.data.objects.new('HV_BagDrop%d_%d' % (k, j), dm)
            C.objects.link(d)
            d.parent = root
            sc = rnd.uniform(0.35, 0.6)
            d.scale = (sc, sc, sc)
            per = rnd.randint(7, 10)
            ph = (j * per) // 3 + rnd.randint(0, 2)
            for f in range(56 + ph, 100, per):                  # each cycle: hang, fall ~0.6 m, reset
                for df, fall in ((0, 0.0), (1, 0.02), (per - 1, 0.6)):
                    d.location = (x0, y0, z - fall)
                    d.keyframe_insert('location', frame=f + df)
            if d.animation_data:
                for fc in T._fcurves(d.animation_data.action):
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'QUAD'
                        kp.easing = 'EASE_IN'
            key_hide(d, [(F0, True), (58 + ph, False), (100, True)], children=False)
    return root


def _ripples(C, people, z_at, W):
    """Rings spreading on the water round each person standing in it (follow x/y, shown only while wet)."""
    m = bpy.data.materials.get('HV_Ripple')
    if not m:
        m = bpy.data.materials.new('HV_Ripple')
        m.use_nodes = True
        m.surface_render_method = 'DITHERED'
        nt = m.node_tree
        Ln = nt.links
        p = nt.nodes['Principled BSDF']
        p.inputs['Base Color'].default_value = (0.05, 0.055, 0.04, 1)
        p.inputs['Roughness'].default_value = 0.03
        tc = nt.nodes.new('ShaderNodeTexCoord')
        wv = nt.nodes.new('ShaderNodeTexWave')
        wv.name = 'Rings'
        wv.wave_type = 'RINGS'
        wv.inputs['Scale'].default_value = 1.6
        wv.inputs['Distortion'].default_value = 1.2
        wv.inputs['Detail'].default_value = 1.0
        Ln.new(tc.outputs['Object'], wv.inputs['Vector'])
        ln = nt.nodes.new('ShaderNodeVectorMath')
        ln.operation = 'LENGTH'
        Ln.new(tc.outputs['Object'], ln.inputs[0])
        fd = nt.nodes.new('ShaderNodeMapRange')
        fd.inputs['From Min'].default_value = 0.95
        fd.inputs['From Max'].default_value = 0.25
        fd.inputs['To Max'].default_value = 0.7
        Ln.new(ln.outputs['Value'], fd.inputs['Value'])
        Ln.new(fd.outputs[0], p.inputs['Alpha'])
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = 0.5
        b.inputs['Distance'].default_value = 0.01
        Ln.new(wv.outputs['Fac'], b.inputs['Height'])
        Ln.new(b.outputs[0], p.inputs['Normal'])
        sock = wv.inputs['Phase Offset']
        for f, v in ((F0, 0.0), (F1, -90.0)):
            sock.default_value = v
            sock.keyframe_insert('default_value', frame=f)
        for fc in T._fcurves(nt.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.0)
    me = bpy.data.meshes.new('HV_RippleDisc')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    for w in people:
        o = bpy.data.objects.new(w.name + '_Ripple', me)
        C.objects.link(o)
        o.location = (0, 0, W + 0.004)
        c = o.constraints.new('COPY_LOCATION')
        c.target = w
        c.use_z = False
        prev = None
        for f in range(F0, F1 + 1, 4):
            bpy.context.scene.frame_set(f)
            x, y = w.matrix_world.translation.x, w.matrix_world.translation.y
            wet = z_at(x, y) < W - 0.05
            if wet != prev:
                key_hide(o, [(f, not wet)], children=False)
                prev = wet
    bpy.context.scene.frame_set(F0)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build(argv[0] if argv else os.path.join(REPO, 'assets-src/blender/p-harvest.blend'))
