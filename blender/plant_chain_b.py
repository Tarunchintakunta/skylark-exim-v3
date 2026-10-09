"""Plant chain, part B: everything after truck-reverse on the same global timeline (p-intake 288-479,
p-proc 479-766, p-freeze 766-1053): unloading crates onto trolleys, tank tipping, the processing-hall crew
mid-shift, lab / freezing / packing / cold-store crews, and the camera keys that continue the truck-reverse move."""
import math
import os
import random
import bpy
from mathutils import Vector, Euler
import skhuman as H
import skplant as S
import skinterior as SI
import sktruck as T

D = math.radians
DZ = S.DZ
CX = SI.CX
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# camera continues from truck-reverse f288 = (8.95, 4.35, 2.85) looking into the truck
CAM_KEYS = [
    # p-intake: slight push on the unloading, then turn and follow W3's loaded trolley through the curtain
    (318, (8.9, 4.5, 3.25), (9.15, -1.2, 1.95)),     # over the shoulders onto the unloading
    (346, (7.9, 5.2, 3.15), (6.0, 6.2, 1.6)),
    (372, (6.1, 5.9, 3.05), (7.6, 9.6, 1.7)),
    (400, (6.3, 8.0, 3.1), (8.3, 12.6, 1.8)),
    (430, (7.0, 9.8, 3.3), (8.2, 14.8, 1.9)),        # W3 pushes through the strips ahead of the lens
    (456, (7.3, 11.3, 3.5), (8.4, 17.5, 1.9)),
    (479, (7.6, 12.6, 3.6), (8.6, 22.0, 2.0)),        # through the swinging strips, over the wash line
    # p-proc: wash (dolly down the line) -> grading (lateral track) -> peeling tables -> lab door
    (520, (7.6, 14.0, 2.75), (9.4, 18.5, 1.95)),
    (575, (6.0, 17.6, 2.6), (8.4, 22.5, 1.9)),
    (624, (4.1, 22.6, 2.5), (8.2, 25.8, 1.85)),
    (671, (4.3, 28.6, 2.55), (8.2, 31.8, 1.85)),
    (720, (8.2, 34.0, 2.6), (8.2, 41.0, 2.0)),
    (766, (8.2, 42.6, 2.7), (8.3, 49.0, 2.15)),
    # p-freeze: lab -> plate freezer / glazing -> packing -> cold store aisle
    (800, (8.3, 45.6, 2.65), (10.6, 47.4, 2.05)),
    (824, (8.6, 47.6, 2.6), (11.0, 47.2, 2.0)),
    (862, (8.4, 50.4, 2.8), (5.0, 54.4, 2.25)),
    (900, (9.4, 53.6, 2.9), (11.0, 56.8, 2.15)),
    (924, (9.0, 56.8, 2.8), (8.0, 62.0, 2.1)),
    (962, (8.4, 59.8, 2.65), (6.0, 62.2, 1.75)),
    (996, (8.2, 62.6, 2.55), (8.2, 70.0, 1.9)),
    (1030, (8.2, 66.6, 2.45), (8.2, 78.0, 1.95)),
    (1053, (8.2, 68.4, 2.4), (8.2, 80.5, 1.95)),
    (1070, (8.2, 68.6, 2.4), (8.2, 80.7, 1.95)),
]


def _key_world_to_truck(R, wx, wy, wz):
    """World point -> local coordinates of the docked truck root (origin (9.2, -3.08), heading -90 deg)."""
    ox, oy = S.TRUCK_BAY, -3.08
    return (oy - wy, wx - ox, wz)


def _ik(w, side, target, seq, pole=None):
    pb = w.pose.bones['forearm.' + side]
    c = pb.constraints.new('IK')
    c.target = target
    c.chain_count = 2
    c.use_tail = True
    if pole is not None:
        c.pole_target = pole
        c.pole_angle = D(-90)
    for f, v in seq:
        c.influence = v
        c.keyframe_insert('influence', frame=f)
    return c


def _handles(name, crate, C):
    hs = []
    for s in (-1, 1):
        h = bpy.data.objects.new('%s_H%d' % (name, s > 0), None)
        C.objects.link(h)
        h.parent = crate
        h.location = (0, s * 0.22, 0.24)
        hs.append(h)
    return hs


def unload(C, R):
    """W1 (trolley A) and W2 (trolley B) lift the top crates out of the truck onto trolleys W5/W6 bring up."""
    tA, tB = bpy.data.objects['PL_WaitTrolley1'], bpy.data.objects['PL_WaitTrolley2']
    for t, dest, f0, f1 in ((tA, (8.72, 1.35), 292, 306), (tB, (9.68, 1.4), 294, 308)):
        t.keyframe_insert('location', frame=f0)
        t.keyframe_insert('rotation_euler', frame=f0)
        t.location = (dest[0], dest[1], DZ)
        t.rotation_euler = (0, 0, D(90))
        t.keyframe_insert('location', frame=f1)
        t.keyframe_insert('rotation_euler', frame=f1)
    for nm, t, f0, f1 in (('HUM_DockW5', tA, 288, 308), ('HUM_DockW6', tB, 290, 310)):
        w = bpy.data.objects[nm]
        a = (w.location.x, w.location.y)
        b = (t.location.x - 0.0, 2.75)
        w.animation_data_clear()
        relax = {'upperarm.L': (8, -26, 0), 'forearm.L': (14, 0, 0), 'upperarm.R': (10, -24, 0),
                 'forearm.R': (24, 0, 0), 'spine': (4, 0, 0), 'head': (8, 0, 0)}
        for f in (1, f0 - 4):                       # hold relaxed until the walk, not eased into the push pose
            H.set_pose(w, relax, f)
        w.location.z = 0.0
        H.walk_cycle(w, f0, f1, [(f0, a), (f1, b)], stride=0.55, base=H.POSES['push'], arms=False)
        _lift(w)
        w.rotation_euler = (0, 0, 0)
        w.keyframe_insert('rotation_euler', frame=f1 + 2)
        H.jitter(w, H.POSES['look'], f1 + 4, 1060, every=24, amp=4, seed=sum(map(ord, nm)) % 97)
    # crates: top of the first rows (k index in the truck cargo)
    moves = [(3, tA, (0, -0.24, 0)), (12, tB, (0, -0.24, 0)), (8, tA, (0, 0.24, 0)), (2, tB, (0, 0.24, 0)),
             (11, tA, (0, -0.24, 1)), (7, tB, (0, -0.24, 1))]
    workers = {id(tA): bpy.data.objects['HUM_DockW1'], id(tB): bpy.data.objects['HUM_DockW2']}
    for i, (k, t, (dx, dy, lv)) in enumerate(moves):
        c = bpy.data.objects['TRK_RigidReefer_Cargo%02d' % k]
        t0 = 312 + i * 6
        p0 = c.location.copy()
        rz0 = c.rotation_euler.z
        c.keyframe_insert('location', frame=t0)
        c.keyframe_insert('rotation_euler', frame=t0)
        c.location = p0 + Vector((0, 0, 0.06))
        c.keyframe_insert('location', frame=t0 + 2)
        wx, wy = t.location.x + dx, t.location.y + dy
        wz = DZ + 0.33 + lv * 0.3
        mid = _key_world_to_truck(R, (wx + (S.TRUCK_BAY + c.location.y)) / 2, 0.3, max(wz, p0.z) + 0.1)
        c.location = mid
        c.keyframe_insert('location', frame=t0 + 6)
        c.location = _key_world_to_truck(R, wx, wy, wz)
        c.rotation_euler = (0, 0, rz0)
        c.keyframe_insert('location', frame=t0 + 10)
        c.keyframe_insert('rotation_euler', frame=t0 + 10)
        w = workers[id(t)]
        hs = _handles(c.name, c, C)
        _ik(w, 'L', hs[0], [(t0 - 8, 0.0), (t0 - 2, 1.0), (t0 + 10, 1.0), (t0 + 14, 0.0)])
        _ik(w, 'R', hs[1], [(t0 - 8, 0.0), (t0 - 2, 1.0), (t0 + 10, 1.0), (t0 + 14, 0.0)])
    # W1/W2 step up to the truck before lifting
    for nm, pos, rz in (('HUM_DockW1', (8.55, 0.75), 0), ('HUM_DockW2', (9.85, 0.75), 0)):
        w = bpy.data.objects[nm]
        w.location = (pos[0], pos[1], DZ)
        w.rotation_euler = (0, 0, D(rz))
        w.keyframe_insert('location', frame=304)
        w.keyframe_insert('rotation_euler', frame=304)
        H.set_pose(w, {'spine': (20, 0, 0), 'thigh': (15, 4, 0), 'shin': (-20, 0, 0)}, 306)
        H.set_pose(w, {'spine': (10, 0, 0)}, 352)
        H.jitter(w, H.POSES['look'], 360, 1060, every=24, amp=4, seed=len(nm))


def _lift(w):
    ad = w.animation_data
    if not ad or not ad.action:
        return
    for fc in T._fcurves(ad.action):
        if fc.data_path == 'location' and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.co.y += DZ
                kp.handle_left.y += DZ
                kp.handle_right.y += DZ


def tank_crew(C, rnd, crate_fn):
    """Two workers at the wash tanks tipping crates in; two more lifting baskets."""
    out = []
    for k, (x, y, rz) in enumerate(((CX - 1.6, 14.4, 160), (CX + 1.7, 14.4, 200))):
        w = H.person('HUM_Tank%d' % k, 'plant', 'female' if k else 'male', coll=C, seed=300 + k)
        w.location = (x, y, DZ)
        w.rotation_euler = (0, 0, D(rz))
        c = crate_fn('IN_TipCrate%d' % k, 'blue', (x + (0.9 if k else -0.9) * 0.0, y + 0.75, DZ + 1.15), 0.0, None, 'ice',
                     700 + k)
        c.rotation_euler = (0, D(-25 if k else 25), 0)
        for f0 in (300, 380, 460, 540, 620, 700):
            for f, ang in ((f0, 15), (f0 + 20, 75), (f0 + 40, 15)):
                c.rotation_euler = (0, D(-ang if k else ang), 0)
                c.keyframe_insert('rotation_euler', frame=f)
        hs = _handles(c.name, c, C)
        _ik(w, 'L', hs[0], [(1, 1.0)])
        _ik(w, 'R', hs[1], [(1, 1.0)])
        H.jitter(w, {'spine': (14, 0, 0), 'upperarm': (55, -8, 0)}, 1, 1060, every=20, amp=4, seed=k)
        out.append(w)
    for k, (x, y, rz) in enumerate(((CX - 4.4, 14.6, 180), (CX + 4.5, 16.6, 0), (CX - 2.4, 16.7, 0), (CX + 2.8, 14.5, 180))):
        w = H.person('HUM_Wash%d' % k, 'plant', 'male' if k % 2 else 'female', coll=C, seed=310 + k, lod='lo')
        w.location = (x, y, DZ)
        w.rotation_euler = (0, 0, D(rz))
        H.jitter(w, {'spine': (28, 0, 0), 'chest': (8, 0, 0), 'upperarm': (55, -8, 0), 'forearm': (45, 0, 0),
                     'head': (10, 0, 0)}, 1, 1060, every=10, amp=7, seed=20 + k)
        out.append(w)
    return out


def proc_crew(C, rnd):
    """Mid-shift from the first frame: graders at the belt/grader, peelers at all four tables, fish cleaners,
    a supervisor in a white coat walking the aisle."""
    work = {'spine': (16, 0, 0), 'chest': (10, 0, 0), 'neck': (12, 0, 0), 'head': (14, 0, 0),
            'upperarm': (30, -12, 0), 'forearm': (78, 0, 0), 'hand': (-10, 0, 0)}
    n = 0
    spots = []
    for k in range(4):                                         # belt sorters
        spots.append((CX + (1.0 if k % 2 else -1.0), 21.5 + (k // 2) * 2.4, 90 if k % 2 else -90, 'lo'))
    for k in range(4):                                         # graders beside the chutes
        spots.append((CX + (2.1 if k % 2 else -2.1), 25.6 + (k // 2) * 1.5, 90 if k % 2 else -90, 'lo'))
    for t, x in enumerate((CX - 6.4, CX - 3.2, CX + 3.2, CX + 6.4)):
        near = t in (1, 2)
        for sx in (-1, 1):
            cnt = 4 if near else 3
            for j in range(cnt):
                y = 33.6 + j * (9.0 / (cnt - 1)) + rnd.uniform(-0.3, 0.3)
                spots.append((x + sx * 0.78, y, -90 if sx < 0 else 90, 'lo'))
    for j in range(2):                                         # fish table
        spots.append((SI.XR - 2.4, 35.5 + j * 4.0, -90, 'lo'))
    for x, y, rz, lod in spots:
        g = 'female' if rnd.random() < 0.45 else 'male'
        w = H.person('HUM_Proc%02d' % n, 'plant', g, coll=C, seed=400 + n, lod=lod)
        h = rnd.uniform(0.93, 1.06) * (0.95 if g == 'female' else 1.0)    # varied height and build
        w.scale = (h * rnd.uniform(0.94, 1.1), h * rnd.uniform(0.95, 1.08), h)
        H.grip(w, 'L', curl=rnd.uniform(0.35, 0.7))                         # working hands, not splayed
        H.grip(w, 'R', curl=rnd.uniform(0.35, 0.7))
        w.location = (x, y, DZ)
        w.rotation_euler = (0, 0, D(rz + rnd.uniform(-8, 8)))
        H.jitter(w, work, 1, 1060, every=8 + n % 5, amp=7, seed=n)
        n += 1
    sup = H.person('HUM_Supervisor', 'plant_coat', 'male', coll=C, seed=499, lod='lo')
    H.set_pose(sup, H.POSES['stand'], 1)
    H.walk_cycle(sup, 470, 780, [(470, (CX + 0.8, 44.0)), (780, (CX + 0.9, 31.0))], stride=0.6, step=2)
    _lift(sup)
    return n + 1


def freeze_crew(C, rnd, crate_fn):
    out = []
    qc = H.person('HUM_QC', 'plant_coat', 'female', coll=C, seed=500)
    qc.location = (CX + 3.2, 47.75, DZ)
    qc.rotation_euler = (0, 0, D(-5))
    H.jitter(qc, {'spine': (14, 0, 0), 'neck': (10, 0, 0), 'head': (12, 0, 0), 'upperarm': (30, -10, 0),
                  'forearm': (75, 0, 0)}, 1, 1060, every=12, amp=6, seed=1)
    qc2 = H.person('HUM_QC2', 'plant_coat', 'male', coll=C, seed=501, lod='lo')
    qc2.location = (CX - 3.5, 47.7, DZ)
    qc2.rotation_euler = (0, 0, D(10))
    H.jitter(qc2, {'spine': (12, 0, 0), 'upperarm': (25, -12, 0), 'forearm': (70, 0, 0), 'head': (16, 0, 0)}, 1, 1060,
             every=14, amp=6, seed=2)
    for k, (x, y, rz) in enumerate(((CX - 2.8, 54.0, 90), (CX - 2.2, 55.6, 120), (CX + 2.4, 57.2, -90))):
        w = H.person('HUM_Freeze%d' % k, 'plant', 'male' if k != 1 else 'female', coll=C, seed=510 + k, lod='lo')
        w.location = (x, y, DZ)
        w.rotation_euler = (0, 0, D(rz))
        H.jitter(w, {'spine': (12, 0, 0), 'upperarm': (45, -8, 0), 'forearm': (55, 0, 0)}, 1, 1060, every=10, amp=8,
                 seed=10 + k)
    for k, (x, y, rz) in enumerate(((CX - 3.8, 61.6, -90), (CX - 3.8, 63.0, -90), (CX + 1.6, 61.4, -90),
                                    (CX + 3.2, 62.6, 90))):
        w = H.person('HUM_Pack%d' % k, 'plant', 'female' if k % 2 else 'male', coll=C, seed=520 + k, lod='lo')
        w.location = (x, y, DZ)
        w.rotation_euler = (0, 0, D(rz))
        H.jitter(w, {'spine': (14, 0, 0), 'neck': (8, 0, 0), 'upperarm': (35, -10, 0), 'forearm': (70, 0, 0)}, 1, 1060,
                 every=9, amp=8, seed=20 + k)
    # cold-store worker pulling a pallet truck along the aisle (+Y, one direction)
    cs = H.person('HUM_Cold', 'coldstore', 'male', coll=C, seed=530)
    pt = bpy.data.objects.new('IN_ColdPalletJack', None)
    C.objects.link(pt)
    pt.parent = cs
    pt.location = (0, 1.1, 0)
    from sktruck import Part
    M = S.MATS()
    p = Part()
    for sx in (-0.28, 0.28):
        p.box((sx, 0.6, 0.06), (0.16, 1.15, 0.06))
    p.box((0, -0.05, 0.25), (0.6, 0.3, 0.4))
    p.cyl((0, -0.1, 0.4), (0, 0.15, 1.15), 0.02, 8)
    p.make('IN_ColdJackBody', S.MATS()['yellow'], pt, bevel=0.01, coll=C)
    S.pallet('IN_ColdJackPallet', (0, 0.62, 0.08), M, C, 0.0, cartons=3).parent = pt
    H.walk_cycle(cs, 880, 1070, [(880, (CX + 0.4, 66.0)), (1070, (CX + 0.4, 77.5))], stride=0.55,
                 base={'upperarm.R': (40, -5, 0), 'forearm.R': (20, 0, 0)}, step=2)
    _lift(cs)
    cs.rotation_euler = (0, 0, D(180))
    return out


def build_interior_people(C, R):
    rnd = random.Random(99)
    H.load(os.path.join(REPO, 'assets-src/blender/humans_lo.blend'), tag='lo')
    import plant_chain as PC
    crate_fn = lambda n, c, l, r, par, fill, sd: PC.crate(n, c, l, r, par, fill, sd)
    unload(C, R)
    cold = [o for o in bpy.data.objects if o.name.startswith('IN_ColdStrip_')]
    SI.swing_strips(cold, [(1006, 1022, CX, 0.9, 1)])
    tank_crew(C, rnd, crate_fn)
    proc_crew(C, rnd)
    freeze_crew(C, rnd, crate_fn)
    join_static_shrimp()


def join_static_shrimp():
    """Merge the hundreds of static shrimp instances into one mesh per zone (far cheaper to sync/render)."""
    groups = {}
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.data.name.startswith('FARM_ShrimpMesh') and o.parent is None and not o.animation_data:
            if not o.name.startswith('IN_'):
                continue
            key = int(o.location.y // 6)
            groups.setdefault(key, []).append(o)
    for key, objs in groups.items():
        if len(objs) < 2:
            continue
        act = objs[0]
        act.data = act.data.copy()
        with bpy.context.temp_override(active_object=act, object=act, selected_objects=objs,
                                       selected_editable_objects=objs):
            bpy.ops.object.join()
        act.name = 'IN_ShrimpZone%02d' % key


def extend_camera(cam):
    cam.data.dof.aperture_fstop = 4.0


SHADOW_LIGHTS = {'PL_DockArea4', 'PL_DockArea6', 'PL_DockArea7', 'IN_Area_0_0', 'IN_Area_2_1', 'IN_Area_4_0',
                 'IN_Area_6_1', 'IN_Area_8_0', 'IN_ColdArea1'}


def shadow_policy():
    """Area-light shadow maps dominate EEVEE render time (24 shadowed lights ~ 4x slower). The same fixed subset
    casts shadows in every plant scene (identical boundary frames); AO + ray-traced GI carry the rest."""
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.data.type == 'AREA':
            o.data.use_shadow = o.name in SHADOW_LIGHTS
