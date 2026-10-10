"""Coldchain beats (#107): the old p-freeze pass split into four one-shot clips, one per caption.
  p-lab   global 766-909  : continues p-proc's camera through the glazed lab door onto the QC bench; the technician
                            lifts a sample tray onto the balance and reads it
  p-iqf   global 910-1053 : own camera low beside the IQF belt: glazed shrimp ride out of the frosted tunnel under
                            the glazing spray; a worker collects at the belt end
  p-pack  global 910-1053 : own camera on the packing table: a packer lowers a vacuum-packed block into a carton
                            (blank label, no text)
  p-store global 900-1043 : own camera low in the cold-store aisle: a worker pulls a pallet truck past wrapped pallets,
                            light frost only
Everything shares the plant set built by plant_chain.build(); this module adds the beat-specific action + cameras."""
import math
import bpy
from mathutils import Vector, Euler
import skhuman as H
import skplant as S
import skinterior as SI
import sktruck as T
from sktruck import Part
import skpbr as P

D = math.radians
DZ = S.DZ
CX = SI.CX
BEATS = {'p-lab': (766, 909), 'p-iqf': (910, 1053), 'p-pack': (910, 1053), 'p-store': (900, 1043)}

# main camera after p-proc's last frame (766 stays exactly where it was): into the lab, onto the QC bench
LAB_KEYS = [
    (800, (8.6, 45.8, 2.75), (10.9, 47.3, 2.1)),
    (840, (9.7, 48.6, DZ + 1.8), (CX + 3.1, 47.0, DZ + 1.05)),
    (880, (10.25, 48.35, DZ + 1.62), (CX + 3.15, 46.98, DZ + 1.1)),
    (909, (10.45, 48.2, DZ + 1.55), (CX + 3.2, 46.97, DZ + 1.12)),
    (930, (10.5, 48.15, DZ + 1.53), (CX + 3.2, 46.97, DZ + 1.12)),
]


def _cam(name, keys, lens=35, fstop=2.8):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = fstop
    tgt = bpy.data.objects.new(name + '_Target', None)
    bpy.context.scene.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cam.data.dof.focus_object = tgt
    for f, loc, t in keys:
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


def _ik(w, side, target, seq):
    c = w.pose.bones['forearm.' + side].constraints.new('IK')
    c.target = target
    c.chain_count = 2
    c.use_tail = True
    for f, v in seq:
        c.influence = v
        c.keyframe_insert('influence', frame=f)
    return c


def _empty(name, loc, parent=None, C=None):
    e = bpy.data.objects.new(name, None)
    (C or bpy.context.scene.collection).objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def lab_action(C):
    """QC technician: left hand steadies the bench edge, right hand lifts sample tray 2 onto the balance (820-850);
    two more technicians work further along the bench."""
    import random
    import plant_chain_b as B
    rnd = random.Random(77)
    for k, (x, g) in enumerate(((CX + 5.9, 'female'), (CX + 8.3, 'male'))):     # two more technicians at the bench
        w = H.person('HUM_LabTech%d' % k, 'plant_coat', g, coll=C, seed=560 + k)
        w.location = (x, 47.62, DZ)
        w.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        if B.hands_on_work(w, rnd, reach=0.42, C=C):
            H.jitter(w, {'spine': (14, 0, 0), 'neck': (10, 0, 0), 'head': (16, 0, 0)}, 1, 1100, every=11 + k, amp=4,
                     seed=70 + k, arms=False)
    qc = bpy.data.objects['HUM_QC']
    tray = bpy.data.objects.get('IN_LabTray2')
    kids = [o for o in bpy.data.objects if o.name.startswith('IN_LabTray2_S')]
    for k in kids:                                  # the sample shrimp ride in the tray
        k.parent = tray
        k.matrix_parent_inverse = tray.matrix_world.inverted()
    p0 = tray.location.copy()
    pb_ = Vector((CX + 3.2, 46.97, DZ + 1.2))           # balance pan
    for f, loc in ((1, p0), (818, p0), (834, (p0 + pb_) / 2 + Vector((0, 0.05, 0.12))), (850, pb_), (1100, pb_)):
        tray.location = loc
        tray.keyframe_insert('location', frame=f)
    for c in [c for pb in qc.pose.bones for c in pb.constraints if c.type == 'IK' and c.target and
              '_Work' in c.target.name]:                     # bench work hands hand over to the tray
        for f, v in ((790, 1.0), (802, 0.0)):
            c.influence = v
            c.keyframe_insert('influence', frame=f)
    qc.keyframe_insert('location', frame=772)
    qc.location = (CX + 3.0, 47.44, DZ)                   # a step closer, in front of the balance
    qc.keyframe_insert('location', frame=798)
    hr = _empty('HUM_QC_HandR', (0.0, 0.14, 0.03), tray, C)
    hl = _empty('HUM_QC_HandL', (CX + 2.75, 47.33, DZ + 0.93), None, C)
    _ik(qc, 'R', hr, ((1, 0.0), (804, 0.0), (814, 1.0), (856, 1.0), (866, 0.0)))
    _ik(qc, 'L', hl, ((1, 0.0), (800, 0.0), (812, 1.0), (1100, 1.0)))
    H.set_pose(qc, {'spine': (14, 0, 0), 'neck': (10, 0, 0), 'head': (16, 0, 0), 'upperarm.R': (12, -20, 0),
                    'forearm.R': (30, 0, 0)}, 870)
    H.settle_reach(qc, 800, 909, step=3, iters=3, max_shift=0.25)
    H.set_pose(qc, {'spine': (14, 0, 0), 'neck': (10, 0, 0), 'head': (18, 0, 0), 'upperarm.R': (12, -20, 0),
                    'forearm.R': (30, 0, 0)}, 1100)


def iqf_action(C):
    """Glazed shrimp ride the IQF belt out of the tunnel (+Y) and under the glazing spray."""
    flow = _empty('IN_IQFFlow', (0, 0, 0), None, C)
    for o in [o for o in bpy.data.objects if o.name.startswith('IN_IQF') and o.type == 'MESH' and
              o.name[6:8].isdigit()]:
        o.parent = flow
    for f, y in ((900, -1.6), (1060, 0.0)):
        flow.location = (0, y, 0)
        flow.keyframe_insert('location', frame=f)
    for fc in T._fcurves(flow.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    tx = CX + 3.6                                     # (tunnel mouth frost + vapour are built with the tunnel)
    return _cam('CAM_IQF', [(910, (CX + 2.15, 59.3, DZ + 1.5), (tx, 55.7, DZ + 0.95)),
                            (1053, (CX + 2.35, 57.9, DZ + 1.38), (tx, 56.6, DZ + 1.0)),
                            (1070, (CX + 2.36, 57.85, DZ + 1.38), (tx, 56.6, DZ + 1.0))], lens=40, fstop=3.2)


def pack_action(C):
    """A packer at table 1 lowers a vacuum-packed block into a carton; both hands stay on the block."""
    x = CX + 2.4
    w = H.person('HUM_Packer', 'plant', 'female', coll=C, seed=541)
    w.location = (x - 0.62, 61.55, DZ)
    w.rotation_euler = (0, 0, D(-90))
    blk = Part()
    blk.box((0, 0, 0), (0.24, 0.17, 0.05))
    b = blk.make('IN_PackBlock', bpy.data.materials.get('IN_VacBag') or P.plain('IN_VacBag', (0.66, 0.58, 0.55), 0.22,
                 coat=1.0), None, bevel=0.012, coll=C)
    a0 = Vector((x - 0.2, 61.25, DZ + 0.93))             # on the table beside the carton
    a1 = Vector((x, 61.55, DZ + 1.32))                   # lifted over the open carton
    a2 = Vector((x, 61.55, DZ + 1.17))                   # lowered to the rim
    a3 = Vector((x, 61.55, DZ + 1.04))                   # let go: settles on the two blocks already packed
    for k in range(2):
        pk = Part()
        pk.box((x + (k - 0.5) * 0.02, 61.55, DZ + 0.938 + k * 0.051), (0.24, 0.17, 0.05))
        pk.make('IN_PackedBlock%d' % k, b.data.materials[0], None, bevel=0.012, coll=C)
    for f, loc in ((1, a0), (930, a0), (962, a1), (992, a1), (1018, a2), (1030, a2), (1036, a3), (1100, a3)):
        b.location = loc
        b.keyframe_insert('location', frame=f)
    for sd, dx in (('L', -0.1), ('R', 0.1)):
        e = _empty('HUM_Packer_Hand' + sd, (dx, 0.0, 0.035), b, C)
        _ik(w, sd, e, ((1, 1.0), (1020, 1.0), (1028, 0.0)))
        H.grip(w, sd, curl=0.55)
    base = {'spine': (18, 0, 0), 'chest': (6, 0, 0), 'neck': (10, 0, 0), 'head': (18, 0, 0)}
    H.jitter(w, base, 1, 1100, every=16, amp=3, seed=41, arms=False)
    H.set_pose(w, {'upperarm': (10, -22, 0), 'forearm': (40, 0, 0)}, 1040)
    # table 1's cartons: rebuilt so the middle one is open (walls + floor, flaps folded out) to receive the block
    for n in ('IN_PackCartons1', 'IN_PackLabels1', 'IN_PackLabelLines1'):
        o = bpy.data.objects.get(n)
        if o:
            o.hide_render = o.hide_viewport = True
    cm = bpy.data.materials.get('PL_Carton')
    p = Part()
    q = Part()
    for k in range(5):
        yy = 60.8 + k * 0.75
        if k != 1:
            p.box((x, yy, DZ + 1.05), (0.55, 0.38, 0.3))
            q.box((x - 0.276, yy, DZ + 1.08), (0.004, 0.2, 0.12))
            continue
        p.box((x, yy, DZ + 0.905), (0.55, 0.38, 0.01))                 # floor
        for sx in (-1, 1):
            p.box((x + sx * 0.27, yy, DZ + 1.05), (0.01, 0.38, 0.3))     # end walls
            p.box((x, yy + sx * 0.185, DZ + 1.05), (0.55, 0.01, 0.3))    # side walls
            p.box((x + sx * 0.34, yy, DZ + 1.25), (0.01, 0.38, 0.16), Euler((0, sx * 0.55, 0)))   # flaps out
    p.make('IN_PackCartonsOpen', cm, None, bevel=0.003, coll=C)
    q.make('IN_PackLabelsOpen', bpy.data.materials.get('IN_LabelBlank'), None, coll=C)
    return _cam('CAM_Pack', [(910, (x + 1.25, 60.55, DZ + 1.75), (x - 0.05, 61.5, DZ + 1.05)),
                             (1053, (x + 1.05, 60.85, DZ + 1.6), (x - 0.05, 61.5, DZ + 1.02)),
                             (1070, (x + 1.04, 60.86, DZ + 1.6), (x - 0.05, 61.5, DZ + 1.02))], lens=40, fstop=3.2)


def store_action(C):
    """Low camera in the cold-store aisle, the pallet-truck worker comes toward and past it."""
    return _cam('CAM_Store', [(900, (CX - 0.9, 75.5, DZ + 1.05), (CX + 0.3, 67.5, DZ + 1.25)),
                              (1043, (CX - 0.95, 77.2, DZ + 1.15), (CX + 0.4, 74.0, DZ + 1.15)),
                              (1060, (CX - 0.95, 77.3, DZ + 1.15), (CX + 0.4, 74.3, DZ + 1.15))], lens=32, fstop=4.0)


def build(scene, C, cam_main):
    """Called by plant_chain.build before the global shift; returns the camera for the clip."""
    if scene == 'p-lab':
        lab_action(C)
        return cam_main
    if scene == 'p-iqf':
        return iqf_action(C)
    if scene == 'p-pack':
        return pack_action(C)
    if scene == 'p-store':
        return store_action(C)
    return cam_main
