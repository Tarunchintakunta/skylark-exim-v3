"""Build the plant chain scenes (truck-reverse -> p-intake -> p-proc -> p-freeze) from ONE deterministic set and ONE
global timeline, so every shared boundary frame is the same image by construction:
  truck-reverse = global 1..288, p-intake = 288..479, p-proc = 479..766, p-freeze = 766..1053.
Each scene file holds the same set and animation shifted so its own frames run 1..N (scripts/scenes.sh).
Usage: Blender -b --python blender/plant_chain.py -- <scene> [out.blend]
"""
import math
import os
import random
import sys
import bpy
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skpbr as P            # noqa: E402
import sktruck as T          # noqa: E402
import skplant as S          # noqa: E402
import skhuman as H          # noqa: E402
import sklib as L            # noqa: E402
from sktruck import Part     # noqa: E402

REPO = os.path.dirname(HERE)
OFFSETS = {'truck-reverse': (1, 288), 'p-intake': (288, 479), 'p-proc': (479, 766), 'p-freeze': (766, 1053)}
D = math.radians


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ truck path (global frames)
class Path:
    """Arc-length sampled planar path; position + tangent heading by distance."""

    def __init__(self, pts):
        self.p = [Vector(p) for p in pts]
        self.s = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.L = self.s[-1]

    def at(self, d):
        d = max(0.0, min(self.L, d))
        for i in range(len(self.s) - 1):
            if self.s[i + 1] >= d:
                t = (d - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
                pos = self.p[i].lerp(self.p[i + 1], t)
                tg = (self.p[i + 1] - self.p[i]).normalized()
                return pos, tg
        return self.p[-1], (self.p[-1] - self.p[-2]).normalized()


def _forward_pts():
    pts = []
    x0, y0 = 30.5, -10.0
    xa = 11.0                          # arc start
    for i in range(40):
        pts.append((x0 + (xa - x0) * i / 40, y0))
    R = 7.5
    cx, cy = xa, y0 - R
    for i in range(41):
        a = math.radians(90 + 52 * i / 40)
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


def _bezier(p0, p1, p2, p3, n=80):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k] for k in (0, 1)))
    return out


FWD = Path(_forward_pts())
F_STOP, R_START, R_END = 118, 128, 212
TRUCK_END = (S.TRUCK_BAY, -3.08)


def _rev_path():
    p0, tg = FWD.at(FWD.L)
    back = -tg                                    # reversing direction
    p3 = Vector(TRUCK_END)
    return Path(_bezier(tuple(p0), tuple(p0 + back * 4.2), tuple(p3 + Vector((0, -4.6))), tuple(p3)))


REV = _rev_path()


def truck_state(f):
    """(x, y, heading, steer) at global frame f."""
    if f <= F_STOP:
        T1, T2 = 3.0, (F_STOP - 1) / 24
        v0 = FWD.L / (T1 + (T2 - T1) / 2)
        t = (f - 1) / 24
        d = v0 * t if t <= T1 else v0 * T1 + v0 * (t - T1) - v0 * (t - T1) ** 2 / (2 * (T2 - T1))
        pos, tg = FWD.at(d)
        hd = math.atan2(tg.y, tg.x)
        _, tg2 = FWD.at(d + 1.0)
        st = _wrap(math.atan2(tg2.y, tg2.x) - hd) * T.WB / 1.0
        return pos.x, pos.y, hd, max(-0.6, min(0.6, st))
    if f <= R_START:
        x, y, hd, st = truck_state(F_STOP)
        return x, y, hd, st
    u = smooth((f - R_START) / (R_END - R_START))
    pos, tg = REV.at(u * REV.L)
    hd = math.atan2(-tg.y, -tg.x)
    _, tg2 = REV.at(u * REV.L + 1.0)
    st = -_wrap(math.atan2(-tg2.y, -tg2.x) - hd) * T.WB / 1.0
    return pos.x, pos.y, hd, max(-0.6, min(0.6, st))


def _wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


# ------------------------------------------------------------------ props
def trolley(name, loc, rot, C):
    """Stainless crate trolley: deck on four castors, push handle at local -X."""
    M = S.MATS()
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    root.location = loc
    root.rotation_euler = (0, 0, rot)
    p = Part()
    p.box((0, 0, 0.3), (1.1, 0.66, 0.035))
    p.box((0, 0.33, 0.33), (1.1, 0.03, 0.06))
    p.box((0, -0.33, 0.33), (1.1, 0.03, 0.06))
    for sx in (-0.5, 0.5):
        for sy in (-0.28, 0.28):
            p.cyl((sx, sy, 0.28), (sx, sy, 0.14), 0.02, 8)
    for sy in (-0.28, 0.28):
        p.cyl((-0.55, sy, 0.3), (-0.62, sy, 1.0), 0.016, 8)
    p.cyl((-0.62, -0.3, 1.0), (-0.62, 0.3, 1.0), 0.018, 8)
    p.make(name + '_Frame', M['stainless'], root, bevel=0.004, coll=C)
    p = Part()
    for sx in (-0.5, 0.5):
        for sy in (-0.28, 0.28):
            p.cyl((sx, sy - 0.025, 0.065), (sx, sy + 0.025, 0.065), 0.065, 14)
    p.make(name + '_Castors', S.MATS()['rubber'], root, coll=C)
    return root


_LM = {}


def crate(name, color, loc, rot, parent, fill, seed, C=None):
    if 'm' not in _LM:
        _LM['m'] = L.M()
    o = L.crate(name, color, loc, rot, fill=fill, parent=parent, mats=_LM['m'], seed=seed)
    o.material_slots[0].material = crate_mat(color)
    return o


CRATE_COL = {'blue': (0.05, 0.10, 0.19), 'red': (0.19, 0.065, 0.055), 'white': (0.66, 0.67, 0.65),
             'yellow': (0.6, 0.45, 0.08)}


def crate_mat(color):
    """Desaturated, slightly scuffed HDPE crate plastic."""
    return P.grime_paint('CR_%s' % color, CRATE_COL[color], rough=0.42, grime=0.35, streak=0.15, coat=0.0, metal=0.0)


def shrimp_fn(C):
    try:
        import skfarm as F          # detailed raw shrimp (lands with the farm scenes)
    except ImportError:
        def fn(name, loc, rot):
            o = L.shrimp_proxy(name, loc, rot)
            for c in o.users_collection:
                c.objects.unlink(o)
            C.objects.link(o)
            return o
        return fn

    def fn(name, loc, rot):
        return F.shrimp(name, loc, rot, None, C)
    return fn


def fish_fn():
    def fn(name, kind, loc, rot):
        return L.fish(name, kind, loc, rot)
    return fn


def chock(name, C):
    p = Part()
    bm = p.bm
    vs = [bm.verts.new(v) for v in ((0, -0.12, 0), (0.28, -0.12, 0), (0, -0.12, 0.18),
                                    (0, 0.12, 0), (0.28, 0.12, 0), (0, 0.12, 0.18))]
    bm.faces.new((vs[0], vs[1], vs[2]))
    bm.faces.new((vs[3], vs[5], vs[4]))
    bm.faces.new((vs[0], vs[3], vs[4], vs[1]))
    bm.faces.new((vs[1], vs[4], vs[5], vs[2]))
    bm.faces.new((vs[2], vs[5], vs[3], vs[0]))
    return p.make(name, S.MATS()['yellow'], None, bevel=0.01, coll=C)


# ------------------------------------------------------------------ build
def key_hide(o, seq):
    for f, hidden in seq:
        o.hide_render = hidden
        o.hide_viewport = hidden
        o.keyframe_insert('hide_render', frame=f)
        o.keyframe_insert('hide_viewport', frame=f)


def build_truck_reverse(C_people):
    """Truck arrival + reverse + driver + dock workers + doors (global frames 1..~300)."""
    R = T.reefer_truck('TRK_RigidReefer', crate_fn=lambda n, c, l, r, par, fill, s: crate(n, c, l, r, par, fill, s))
    T.drive(R, truck_state, 1, 300)
    T.set_reverse(R, [(1, False), (R_START - 4, True), (R_END + 6, False)])
    # rear doors: closed until 262, swing into the plant 262..282 (R +, L -), held after
    for door, sgn, f0 in ((R['door_r'], 1, 262), (R['door_l'], -1, 266)):
        door.rotation_euler = (0, 0, 0)
        door.keyframe_insert('rotation_euler', frame=f0)
        door.rotation_euler = (0, 0, sgn * D(96))
        door.keyframe_insert('rotation_euler', frame=f0 + 18)
    # cab door opens 198..208, stays open
    cd = R['cab_door']
    cd.rotation_euler = (0, 0, 0)
    cd.keyframe_insert('rotation_euler', frame=198)
    cd.rotation_euler = (0, 0, D(-62))
    cd.keyframe_insert('rotation_euler', frame=208)
    # parked trucks at two other bays (doors closed, no cargo, static)
    for nm, bx, col in (('TRK_Parked1', 0.0, (0.80, 0.81, 0.80)), ('TRK_Parked2', -9.2, (0.56, 0.62, 0.68))):
        T.reefer_truck(nm, loc=(bx, -3.08, 0), rot_z=D(-90), load=False, cab_color=col)

    # driver (hi-vis), steps down, places a chock at the front wheel, stands by the cab
    drv = H.person('HUM_Driver', 'driver', 'male', coll=C_people, seed=11)
    drv.location = (7.85, -8.85, 0.92)
    drv.rotation_euler = (0, 0, D(-90))
    for f in (1, 202):
        drv.keyframe_insert('location', frame=f)
        drv.keyframe_insert('rotation_euler', frame=f)
    key_hide(drv, [(1, True), (203, False)])
    for c in drv.children:
        key_hide(c, [(1, True), (203, False)])
    H.set_pose(drv, {'thigh.L': (30, 4, 0), 'shin.L': (-40, 0, 0), 'upperarm.R': (60, -10, 0), 'forearm.R': (40, 0, 0),
                     'upperarm.L': (20, -15, 0), 'forearm.L': (30, 0, 0), 'spine': (8, 0, 0)}, 203)
    drv.location = (7.3, -8.9, 0.45)
    drv.keyframe_insert('location', frame=209)
    H.set_pose(drv, {'thigh.R': (30, 4, 0), 'shin.R': (-40, 0, 0), 'upperarm.R': (50, -10, 0), 'forearm.R': (40, 0, 0),
                     'spine': (6, 0, 0)}, 209)
    drv.location = (7.05, -8.95, 0.0)
    drv.keyframe_insert('location', frame=215)
    H.set_pose(drv, H.POSES['stand'], 215)
    # turn toward the wheel, crouch, place the chock, stand up and stay by the cab
    drv.rotation_euler = (0, 0, D(-90))
    drv.keyframe_insert('rotation_euler', frame=215)
    drv.rotation_euler = (0, 0, D(-242))
    drv.keyframe_insert('rotation_euler', frame=222)
    drv.location = (7.45, -9.05, 0.0)
    drv.keyframe_insert('location', frame=222)
    crouch = {'spine': (32, 0, 0), 'chest': (10, 0, 0), 'head': (-12, 0, 0), 'thigh': (75, 8, 0), 'shin': (-110, 0, 0),
              'foot': (25, 0, 0), 'upperarm': (45, -6, 0), 'forearm': (30, 0, 0)}
    H.set_pose(drv, H.POSES['stand'], 222)
    drv.location = (7.5, -9.0, -0.38)
    drv.keyframe_insert('location', frame=232)
    H.set_pose(drv, crouch, 232)
    H.set_pose(drv, crouch, 240)
    drv.keyframe_insert('location', frame=240)
    drv.location = (7.45, -9.05, 0.0)
    drv.keyframe_insert('location', frame=250)
    H.set_pose(drv, H.POSES['stand'], 250)
    drv.rotation_euler = (0, 0, D(-120))
    drv.keyframe_insert('rotation_euler', frame=262)
    H.set_pose(drv, {'upperarm': (6, -22, 0), 'forearm': (20, 0, 0), 'head': (4, 0, 8)}, 300)
    ch = chock('TRK_Chock', C_people)
    ch.rotation_euler = (0, 0, D(-90))
    for f, loc in ((222, (7.78, -8.88, 0.85)), (228, (7.95, -8.7, 0.45)), (234, (8.12, -8.47, 0.03)),
                   (236, (8.15, -8.42, 0.0))):
        ch.location = loc
        ch.keyframe_insert('location', frame=f)
    key_hide(ch, [(1, True), (222, False)])

    # dock workers: two open the rear doors from inside (hands on the door handles via IK), one pushes a trolley
    # across, two wait with empty trolleys, one at the strip curtain
    def opener(nm, gender, door, side, sy, p0, p1, r0, r1, f0, f1, seed):
        w = H.person(nm, 'plant', gender, coll=C_people, seed=seed)
        h = bpy.data.objects.new(nm + '_Handle', None)
        C_people.objects.link(h)
        h.parent = door
        h.location = (-0.16, -sy * 0.95, -0.05)
        pole = bpy.data.objects.new(nm + '_Pole', None)
        C_people.objects.link(pole)
        pole.parent = w
        pole.location = (0.6 if side == 'L' else -0.6, 0.5, 0.9)
        pb = w.pose.bones['forearm.' + side]
        ik = pb.constraints.new('IK')
        ik.target = h
        ik.pole_target = pole
        ik.pole_angle = D(-90)
        ik.chain_count = 2
        ik.use_tail = True
        for f, v in ((1, 0.0), (f0 - 10, 0.0), (f0 - 2, 1.0), (f1 - 2, 1.0), (f1 + 4, 0.0)):
            ik.influence = v
            ik.keyframe_insert('influence', frame=f)
        w.location = (*p0, S.DZ)
        w.rotation_euler = (0, 0, D(r0))
        for f in (1, f0):
            w.keyframe_insert('location', frame=f)
            w.keyframe_insert('rotation_euler', frame=f)
        w.location = (*p1, S.DZ)
        w.rotation_euler = (0, 0, D(r1))
        for f in (f1, 310):
            w.keyframe_insert('location', frame=f)
            w.keyframe_insert('rotation_euler', frame=f)
        H.jitter(w, H.POSES['stand'], 1, f0 - 12, every=24, amp=3, seed=seed)
        H.set_pose(w, {'spine': (8, 0, 0), 'upperarm': (6, -18, 0), 'forearm': (15, 0, 0)}, f0 - 6)
        H.set_pose(w, {'spine': (4, 0, 0), 'upperarm': (6, -18, 0), 'forearm': (15, 0, 0),
                       'thigh.L': (10, 3, 0), 'thigh.R': (-8, 3, 0)}, (f0 + f1) // 2)
        rest = {'upperarm': (6, -20, 0), 'forearm': (22, 0, 0), 'head': (6, 0, 0)}
        H.set_pose(w, rest, f1 + 4)
        H.set_pose(w, rest, 310)
        return w

    opener('HUM_DockW1', 'male', R['door_r'], 'R', -1, (8.85, 0.85), (7.35, 1.6), 8, 40, 262, 280, 21)
    opener('HUM_DockW2', 'female', R['door_l'], 'L', 1, (9.6, 0.85), (11.05, 1.6), -8, -40, 266, 284, 22)
    for nm, g, xy, rz, sd in (('HUM_DockW5', 'male', (7.0, 3.2), 200, 25), ('HUM_DockW6', 'female', (11.6, 3.3), 150, 26)):
        w = H.person(nm, 'plant', g, coll=C_people, seed=sd)
        w.location = (*xy, S.DZ)
        w.rotation_euler = (0, 0, D(rz))
        H.jitter(w, {'upperarm.L': (8, -26, 0), 'forearm.L': (14, 0, 0), 'upperarm.R': (10, -24, 0),
                     'forearm.R': (24, 0, 0), 'spine': (4, 0, 0), 'head': (8, 0, 0)}, 1, 310, every=20, amp=3, seed=sd)
    trolley('PL_WaitTrolley1', (7.55, 2.35, S.DZ), D(90), C_people)
    trolley('PL_WaitTrolley2', (10.9, 2.45, S.DZ), D(95), C_people)
    w3 = H.person('HUM_DockW3', 'plant', 'male', coll=C_people, seed=23)
    tr = trolley('PL_PushTrolley', (0, 0, S.DZ), 0.0, C_people)
    tr.parent = w3
    tr.location = (0, -1.0, 0)
    tr.rotation_euler = (0, 0, D(-90))             # handle end toward W3
    for k, (ly, lz) in enumerate(((-0.24, 0), (0.24, 0), (-0.24, 1), (0.24, 1))):
        c = crate('PL_PushCrate%d' % k, ['blue', 'white', 'blue', 'blue'][k], (ly, 0, 0.325 + lz * 0.3), D(90), tr,
                  'ice', 600 + k)
    w3_path = [(180, (-6.0, 7.2)), (300, (3.5, 6.6)), (330, (4.6, 7.0)), (400, (7.6, 10.6)), (430, (8.2, 12.3)),
               (466, (8.2, 13.55))]
    H.walk_cycle(w3, 180, 466, w3_path, stride=0.68,
                 base={'upperarm': (40, -8, 0), 'forearm': (40, 0, 0), 'spine': (10, 0, 0)}, arms=False)
    H.set_pose(w3, {'upperarm': (40, -8, 0), 'forearm': (40, 0, 0), 'spine': (10, 0, 0)}, 470)
    H.jitter(w3, {'upperarm': (30, -10, 0), 'forearm': (35, 0, 0), 'spine': (6, 0, 0)}, 476, 1060, every=24, amp=4,
             seed=23)
    _lift(w3, S.DZ)
    for sd, hy in (('L', 0.22), ('R', -0.22)):         # both hands on the push bar the whole way
        h = bpy.data.objects.new('HUM_DockW3_Push' + sd, None)
        C_people.objects.link(h)
        h.parent = tr
        h.location = (-0.62, hy, 1.0)
        c = w3.pose.bones['forearm.' + sd].constraints.new('IK')
        c.target = h
        c.chain_count = 2
        c.use_tail = True
        H.grip(w3, sd, curl=0.8)
    w4 = H.person('HUM_DockW4', 'plant_coat', 'female', coll=C_people, seed=24)
    w4.location = (11.6, 10.2, S.DZ)
    w4.rotation_euler = (0, 0, D(200))
    H.jitter(w4, H.POSES['look'], 1, 300, every=24, amp=4, seed=4)
    return R


def _lift(arm_obj, z):
    """walk_cycle keys z from the rest location; add the dock height to every z key."""
    ad = arm_obj.animation_data
    if not ad or not ad.action:
        return
    for fc in T._fcurves(ad.action):
        if fc.data_path == 'location' and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.co.y += z
                kp.handle_left.y += z
                kp.handle_right.y += z


def camera_truck_reverse():
    cam = L.camera('Camera', 35, (0, 0, 2))
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 5.6
    tgt = bpy.data.objects.new('CAM_Target', None)
    bpy.context.scene.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.up_axis = 'UP_Y'
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    cam.data.dof.focus_object = tgt

    def tx(f):
        x, y, hd, _ = truck_state(f)
        return Vector((x, y, 0))

    keys = []
    for f in (1, 16, 32, 48):
        t = tx(f)
        keys.append((f, (t.x + 9.3, -10.25, 3.1 + 0.4 * (f - 1) / 47), (t.x - 5.5, -9.6, 1.7)))
    t80 = tx(80)
    keys += [
        (80, (23.5, -16.5, 6.0), (t80.x - 1.0, t80.y, 1.6)),
        (120, (19.0, -21.5, 7.8), (8.0, -9.5, 1.6)),
        (165, (12.5, -20.0, 5.6), (9.0, -6.0, 1.8)),
        (200, (3.4, -13.4, 2.3), (7.5, -8.7, 1.2)),       # driver steps down from the cab
        (222, (4.4, -12.6, 1.85), (7.9, -8.7, 0.75)),     # ... walks to the front wheel
        (240, (4.0, -11.3, 1.6), (7.7, -8.9, 0.5)),      # chock goes under the tyre, held in frame
        (256, (4.0, -5.0, 2.4), (6.2, 1.0, 2.3)),
        (272, (5.9, 1.9, 2.85), (8.8, 1.0, 2.45)),
        (288, (8.95, 4.35, 2.85), (S.TRUCK_BAY, -1.4, 2.15)),
    ]
    for f, loc, t in keys:
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
    import plant_chain_b as B
    for f, loc, t in B.CAM_KEYS:
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
    for o in (cam, tgt):
        for fc in T._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
            fc.update()
    return cam


def shift_all(delta):
    """Shift every keyframe of every action by delta frames (scene frame = global frame + delta)."""
    acts = set()
    for idb in list(bpy.data.objects) + list(bpy.data.materials) + list(bpy.data.lights) + list(bpy.data.cameras) + \
            list(bpy.data.scenes) + list(bpy.data.shape_keys):
        ad = getattr(idb, 'animation_data', None)
        if ad and ad.action:
            acts.add(ad.action)
        nt = getattr(idb, 'node_tree', None)
        if nt is not None and nt.animation_data and nt.animation_data.action:
            acts.add(nt.animation_data.action)
    for a in acts:
        for fc in T._fcurves(a):
            for kp in fc.keyframe_points:
                kp.co.x += delta
                kp.handle_left.x += delta
                kp.handle_right.x += delta


def build(scene, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    H.load(os.path.join(REPO, 'assets-src/blender/humans.blend'))
    C_people = S.coll('SET_People')
    S.exterior()
    S.dock(lambda n, c, l, r, par, fill, sd: crate(n, c, l, r, par, fill, sd),
           lambda n, l, r, C: trolley(n, l, r, C))
    import skinterior as SI
    C_in = S.coll('SET_Interior')
    ice_m = L.ice_mesh('IN_IceBed', 0.54, 0.34, 0.05, 40, 9)
    SI.build_all(C_in, lambda n, c, l, r, par, fill, sd: crate(n, c, l, r, par, fill, sd),
                 lambda n, l, r, C: trolley(n, l, r, C), shrimp_fn(C_in), fish_fn(), ice_m)
    strips = SI._strip_curtain('PL_IntakeStrip', SI.CX - 1.55, SI.CX + 1.55, 12.0, S.DZ, S.DZ + 3.18, C_in, SI.mats())
    SI.swing_strips(strips, [(424, 440, 8.2, 0.85, -1), (462, 478, 7.5, 0.8, -1)])
    SI.animate_spray(1, 1100)
    R = build_truck_reverse(C_people)
    import plant_yard
    plant_yard.build(C_people, lambda n, c, l, r, par, fill, sd: crate(n, c, l, r, par, fill, sd))
    import plant_chain_b as B
    B.build_interior_people(C_people, R)
    cam = camera_truck_reverse()
    B.extend_camera(cam)
    B.shadow_policy()
    P.hdri_world('kloofendal_48d_partly_cloudy_puresky_4k.hdr', strength=0.9, rot_deg=201, sun_elev=46, sun_az=145,
                 sun_energy=4.2, sun_color=(1.0, 0.95, 0.88))
    # P.haze(): EEVEE world volume dims the sun; aerial perspective comes from the HDRI horizon instead
    P.sky_haze()                                          # warm dusty haze low in the sky
    P.look_settings('exterior', exposure=0.0)
    vs = s.view_settings          # step down the exposure as the camera goes from daylight into the lit hall
    for f, ev in ((236, 0.0), (264, -0.3), (330, -0.3), (420, -0.5)):   # white hall: hold highlights
        vs.exposure = ev
        vs.keyframe_insert('exposure', frame=f)
    f0, f1 = OFFSETS[scene]
    if scene in ('p-proc', 'p-freeze'):
        for cn in ('SET_PlantExterior',):
            bpy.data.collections[cn].hide_render = True
    shift_all(1 - f0)
    s.frame_start, s.frame_end = 1, f1 - f0 + 1
    s.frame_current = 1
    s.render.filepath = '//../render/%s/' % scene
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('OUT built', scene, out)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['truck-reverse']
    sc = argv[0]
    out = argv[1] if len(argv) > 1 else os.path.join(REPO, 'assets-src/blender/%s.blend' % sc)
    build(sc, out)
