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
        for m in range(26):
            F.shrimp('HV_Crate%d_S%02d' % (n, m), (rnd.uniform(-0.23, 0.23), rnd.uniform(-0.13, 0.13), 0.24 + rnd.uniform(0, 0.03)),
                     (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.28)), parent=sh, C=Cp,
                     scale=rnd.uniform(0.9, 1.15))
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
    pts = [(F0, (cx - 0.2, yw + 2.4, WATER - 0.35), 0.0), (48, (cx - 0.3, yw + 1.6, WATER - 0.25), 0.0),
           (62, (cx - 0.4, yw + 1.0, WATER + 0.25), 0.0), (78, (cx - 0.6, yw + 0.2, WATER + 0.85), 0.0),
           (92, (cx - 2.4, yb - 0.9, TOP + 0.95), 0.0), (102, (cx - 2.7, yb - 1.25, TOP + 0.8), 1.2),
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
            d.location = (bl[0] + rnd.uniform(-0.25, 0.25), bl[1] + rnd.uniform(-0.2, 0.2), bl[2] - 0.35 - t * 0.9)
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
        H.set_pose(w, {'spine': (22, 0, 0), 'upperarm': (50, -8, 0), 'forearm': (55, 0, 0), 'thigh': (12, 4, 0),
                       'shin': (-18, 0, 0)}, 70)
        H.set_pose(w, {'spine': (10, 0, 0), 'upperarm': (30, -12, 0), 'forearm': (60, 0, 0)}, 82)
        rest = {'spine': (4, 0, 0), 'upperarm': (6, -18, 0), 'forearm': (24, 0, 0), 'head': (8, 0, 0)}
        H.jitter(w, rest, 92, 140, every=16, amp=4, seed=k2)
        H.jitter(w, H.POSES['look'], 150, F1 + 10, every=24, amp=5, seed=k2 + 9)
    # two lifters raise the bag, carry it up and tip it into the crates
    for k2, side in enumerate((-1, 1)):
        w = worker('HUM_Lifter%d' % k2, 'farm_long' if k2 else 'farm', 'male', 70 + k2)
        hand = bpy.data.objects.new('HV_BagHand%d' % k2, None)
        Cp.objects.link(hand)
        hand.parent = bag
        hand.location = (side * 0.32, 0, 0.32)
        ik = w.pose.bones['forearm.R' if side > 0 else 'forearm.L'].constraints.new('IK')
        ik.target = hand
        ik.chain_count = 2
        ik.use_tail = True
        ik2 = w.pose.bones['forearm.L' if side > 0 else 'forearm.R'].constraints.new('IK')
        ik2.target = hand
        ik2.chain_count = 2
        ik2.use_tail = True
        for c in (ik, ik2):
            for f, v in ((F0, 0.0), (52, 0.0), (58, 1.0), (128, 1.0), (134, 0.0)):
                c.influence = v
                c.keyframe_insert('influence', frame=f)
        path = [(F0, (cx - 0.3 + side * 0.9, yb + 2.1)), (50, (cx - 0.3 + side * 0.85, yb + 1.8)),
                (80, (cx - 0.6 + side * 0.8, yb + 0.9)), (96, (cx - 2.6 + side * 0.75, yb - 0.4)),
                (128, (cx - 1.3 + side * 0.75, yb - 0.45)), (160, (cx + 3.6 + side * 0.8, yb - 1.0))]
        H.walk_cycle(w, F0, 160, path, stride=0.45,
                     base={'spine': (12, 0, 0), 'upperarm': (10, -16, 0), 'forearm': (30, 0, 0)}, arms=False, step=2)
        for fc in T._fcurves(w.animation_data.action):
            if fc.data_path == 'location' and fc.array_index == 2:
                for kp in fc.keyframe_points:
                    xy = _path_at(path, kp.co.x)
                    kp.co.y += z_at(*xy)
                    kp.handle_left.y = kp.handle_right.y = kp.co.y
        H.jitter(w, H.POSES['stand'], 162, F1 + 10, every=24, amp=4, seed=k2 + 30)
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
        key_hide(cr, [(F0, False), (fs + 52, True)])
        key_hide(loaded[slot], [(F0, True), (fs + 52, False)])
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
            (80, (cx + 2.6, yw + 4.6, WATER + 1.7), (cx - 1.0, yw - 0.6, WATER + 0.9)),
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

    az_h, el_h = P.hdri_sun('qwantani_mid_morning_puresky_4k.hdr')
    sun_az = 130.0
    P.hdri_world('qwantani_mid_morning_puresky_4k.hdr', strength=0.9, rot_deg=sun_az - az_h, sun_elev=el_h, sun_az=sun_az,
                 sun_energy=5.0, sun_color=(1.0, 0.92, 0.8))
    P.look_settings('exterior', exposure=0.0, haze=(160.0, 900.0, (0.64, 0.76, 0.94), 0.1))
    s.frame_start, s.frame_end = F0, F1
    s.frame_current = F0
    s.render.filepath = '//../render/p-harvest/'
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
            v.co.z *= 2.5
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


def _bag(cx, yw, C, rnd):
    """Net bag (cod end) full of shrimp; lifted out at 55-80."""
    root = bpy.data.objects.new('HV_Bag', None)
    C.objects.link(root)
    p = Part()
    bm = p.bm
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.45)
    for v in bm.verts:
        v.co.z = v.co.z * 0.75 if v.co.z < 0 else v.co.z * 0.35
        v.co.x *= 1.1
    o = p.make('HV_BagNet', net_mat(), root, smooth=True, coll=C)
    me = o.data
    uv = me.uv_layers.new(name='UV')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (math.atan2(v.y, v.x) * 0.6, v.z * 1.4)
    for m in range(70):
        while True:
            q = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 0.2)))
            if q.length < 1:
                break
        F.shrimp('HV_BagShrimp%02d' % m, (q.x * 0.36, q.y * 0.3, q.z * 0.28), (rnd.uniform(0, 6.3), rnd.uniform(0, 6.3),
                 rnd.uniform(0, 6.3)), parent=root, C=C, scale=rnd.uniform(0.95, 1.2))
    # a few shrimp flick (small rotation jitter)
    for ch in list(root.children)[1:12]:
        for f in range(50, 100, 3):
            ch.rotation_euler.x += rnd.uniform(-0.5, 0.5)
            ch.keyframe_insert('rotation_euler', frame=f)
    return root


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build(argv[0] if argv else os.path.join(REPO, 'assets-src/blender/p-harvest.blend'))
