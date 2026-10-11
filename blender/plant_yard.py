"""Yard life for truck-reverse (global frames): gate guard, a working forklift, yard staff and a hand pallet jack,
plus road dust / tyre mud on every truck. Built into the shared plant set by plant_chain.build()."""
import math
import bpy
from mathutils import Vector
import skpbr as P
import skplant as S
import skhuman as H
from sktruck import Part

D = math.radians


def _mover(o, f0, f1, pts, step=2):
    """Key location + heading along polyline pts between f0..f1 (eased start/stop); local +X faces travel."""
    pts = [Vector(p) for p in pts]
    seg = [(b - a).length for a, b in zip(pts, pts[1:])]
    L = sum(seg)

    def pos(d):
        for a, b, l in zip(pts, pts[1:], seg):
            if d <= l:
                return a.lerp(b, d / max(1e-9, l))
            d -= l
        return pts[-1]
    hd = None
    for f in range(f0, f1 + 1, step):
        t = (f - f0) / (f1 - f0)
        d = L * t * t * (3 - 2 * t)
        p, q = pos(d), pos(min(L, d + 0.3))
        o.location.x, o.location.y = p.x, p.y
        o.keyframe_insert('location', frame=f)
        if (q - p).length > 1e-3:
            hd = math.atan2(q.y - p.y, q.x - p.x)
        if hd is not None:
            o.rotation_euler.z = hd
            o.keyframe_insert('rotation_euler', frame=f)


def forklift(name, C, M):
    """Counterbalance forklift, forks toward local +X, origin on the ground at the drive axle."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    body = P.grime_paint('YD_ForkliftPaint', (0.62, 0.40, 0.03), rough=0.38, grime=0.55, streak=0.3, coat=0.3)
    p = Part()
    p.box((-0.55, 0, 0.62), (1.6, 1.05, 0.62))                       # chassis
    p.box((-1.25, 0, 0.95), (0.45, 1.0, 0.75))                       # counterweight
    p.box((0.05, 0, 0.98), (0.35, 0.95, 0.12))                       # dash / cowl
    p.make(name + '_Body', body, root, bevel=0.03, coll=C)
    p = Part()
    for sy in (-0.47, 0.47):                                          # overhead guard posts
        p.cyl((0.1, sy, 0.95), (0.0, sy, 2.15), 0.03, 8)
        p.cyl((-0.95, sy, 1.3), (-0.95, sy, 2.15), 0.03, 8)
    p.box((-0.45, 0, 2.17), (1.15, 1.0, 0.05))
    for k in range(5):
        p.box((-0.9 + k * 0.22, 0, 2.21), (0.04, 0.98, 0.04))
    p.box((-0.55, 0, 0.98), (0.45, 0.5, 0.08))                       # seat base
    p.box((-0.75, 0, 1.25), (0.08, 0.5, 0.45))                       # seat back
    p.cyl((-0.05, 0, 1.05), (-0.25, 0, 1.35), 0.02, 8)               # steering column
    p.make(name + '_Guard', S.MATS()['dark'], root, bevel=0.005, coll=C)
    p = Part()
    for sy in (-0.36, 0.36):                                          # mast
        p.box((0.42, sy, 1.25), (0.09, 0.07, 2.3))
    p.box((0.42, 0, 0.35), (0.09, 0.8, 0.08))
    p.box((0.42, 0, 2.35), (0.09, 0.8, 0.08))
    p.make(name + '_Mast', S.MATS()['steel'], root, bevel=0.008, coll=C)
    car = bpy.data.objects.new(name + '_Carriage', None)
    C.objects.link(car)
    car.parent = root
    car.location = (0.5, 0, 0.12)
    p = Part()
    p.box((0.0, 0, 0.35), (0.06, 0.95, 0.5))
    for sy in (-0.3, 0.3):
        p.box((0.0, sy, 0.3), (0.05, 0.11, 0.6))
        p.box((0.6, sy, 0.0), (1.15, 0.11, 0.045))
    p.make(name + '_Forks', S.MATS()['dark'], car, bevel=0.004, coll=C)
    p = Part()
    for sx, r, w in ((0.15, 0.32, 0.24), (-1.15, 0.27, 0.2)):
        for sy in (-0.48, 0.48):
            p.cyl((sx, sy - w / 2, r), (sx, sy + w / 2, r), r, 18)
    p.make(name + '_Tyres', S.MATS()['rubber'], root, smooth=True, coll=C)
    return root, car


def pallet_jack(name, C, parent):
    """Hand pallet jack in the pusher's local frame (pusher faces -Y): handle near the hands, forks ahead."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    root.parent = parent
    root.location = (0, -0.42, 0)
    red = P.grime_paint('YD_JackRed', (0.42, 0.05, 0.03), rough=0.4, grime=0.5, streak=0.2, coat=0.2)
    p = Part()
    p.cyl((0, 0.02, 1.0), (0, -0.22, 0.25), 0.02, 8)                  # tiller
    p.cyl((-0.13, 0.04, 1.0), (0.13, 0.04, 1.0), 0.018, 8)           # grip
    p.box((0, -0.3, 0.22), (0.4, 0.2, 0.22))                         # pump body
    for sx in (-0.27, 0.27):
        p.box((sx, -0.95, 0.07), (0.16, 1.15, 0.06))                 # forks
    p.make(name + '_Frame', red, root, bevel=0.008, coll=C)
    p = Part()
    for sx in (-0.08, 0.08):
        p.cyl((sx - 0.03, -0.3, 0.09), (sx + 0.03, -0.3, 0.09), 0.09, 14)
    for sx in (-0.27, 0.27):
        p.cyl((sx - 0.05, -1.45, 0.04), (sx + 0.05, -1.45, 0.04), 0.04, 10)
    p.make(name + '_Wheels', S.MATS()['rubber'], root, coll=C)
    return root


def build(C, crate):
    M = S.MATS()
    # -- gate guard at the raised barrier, waves the truck in
    g = H.person('HUM_GateGuard', 'guard', 'male', coll=C, seed=31)
    g.location = (25.3, -14.4, 0)
    g.rotation_euler = (0, 0, math.atan2(4.0, -4.6))
    H.jitter(g, H.POSES['look'], 1, 6, every=6, amp=2, seed=31)
    wave = {'upperarm.R': (105, -10, 0), 'forearm.R': (35, 0, 0), 'head': (4, 0, 0)}
    for f, pz in ((10, wave), (16, {'upperarm.R': (105, -10, 0), 'forearm.R': (60, 0, 0)}), (22, wave),
                  (28, {'upperarm.R': (105, -10, 0), 'forearm.R': (60, 0, 0)}), (34, wave)):
        H.set_pose(g, pz, f)
    H.jitter(g, H.POSES['look'], 44, 300, every=24, amp=3, seed=32)

    # -- forklift with an operator brings a carton pallet across the west yard toward bay 0
    fl, car = forklift('YD_Forklift', C, M)
    fl.location = (-17.0, -9.0, 0)
    pal = S.pallet('YD_FLPallet', (0.75, 0, 0.05), M, C, 0.0, cartons=3)
    pal.parent = car
    op = H.person('HUM_ForkliftOp', 'driver', 'male', coll=C, seed=33)
    op.parent = fl
    op.location = (-0.55, 0, 0.38)
    op.rotation_euler = (0, 0, D(-90))
    sit = {'thigh': (88, 6, 0), 'shin': (-85, 0, 0), 'spine': (4, 0, 0), 'upperarm': (35, -10, 0),
           'forearm': (55, 0, 0), 'head': (6, 0, 0)}
    H.jitter(op, sit, 1, 300, every=20, amp=3, seed=33)
    _mover(fl, 30, 230, [(-18.0, -10.5), (-9.0, -9.2), (-5.6, -7.6), (-4.6, -5.4), (-4.6, -2.6)])
    car.keyframe_insert('location', frame=190)
    car.location.z = 0.03
    car.keyframe_insert('location', frame=230)

    # -- second forklift on the near apron (in the review frames): brings a pallet of iced crates in behind the truck
    fl2, car2 = forklift('YD_Forklift2', C, M)
    fl2.location = (14.4, -7.3, 0)
    pal2 = S.pallet('YD_FL2Pallet', (0.75, 0, 0.05), M, C, 0.0)
    pal2.parent = car2
    k = 0
    for lv in range(2):
        for ix in (-0.3, 0.3):
            for iy in (-0.21, 0.21):
                crate('YD_FL2Crate%d' % k, ('blue', 'red', 'white')[k % 3], (ix, iy, 0.15 + lv * 0.3), D(90), pal2,
                      'shrimp' if lv else 'ice', 760 + k)
                k += 1
    op2 = H.person('HUM_ForkliftOp2', 'driver', 'female', coll=C, seed=43)
    op2.parent = fl2
    op2.location = (-0.55, 0, 0.38)
    op2.rotation_euler = (0, 0, D(-90))
    H.jitter(op2, sit, 1, 300, every=20, amp=3, seed=43)
    _mover(fl2, 60, 190, [(14.4, -7.3), (13.5, -7.4), (12.6, -7.5)])
    car2.keyframe_insert('location', frame=196)
    car2.location.z = 0.03
    car2.keyframe_insert('location', frame=226)

    # -- two crate carriers walking the apron toward the dock, a crate held in both hands
    for nm, gnd, path, col, sd in (('HUM_Carrier1', 'male', [(20, (15.4, -5.5)), (190, (11.9, -5.7))], 'blue', 44),
                                   ('HUM_Carrier2', 'female', [(50, (16.2, -6.0)), (230, (12.6, -6.1))], 'red', 45)):
        w = H.person(nm, 'plant', gnd, coll=C, seed=sd)
        H.walk_cycle(w, path[0][0], path[1][0], path, stride=0.55, phase=sd * 0.5,
                     base={'upperarm': (38, -10, 0), 'forearm': (55, 0, 0), 'spine': (6, 0, 0)}, arms=False)
        H.jitter(w, {'upperarm': (38, -10, 0), 'forearm': (55, 0, 0), 'spine': (6, 0, 0), 'head': (8, 0, 0)},
                 path[1][0] + 2, 300, every=24, amp=3, seed=sd)
        crate(nm + '_Crate', col, (0, -0.42, 0.86), D(90), w, 'shrimp', 800 + sd)
        for sdd, hx in (('L', 0.29), ('R', -0.29)):
            h = bpy.data.objects.new(nm + '_Hand' + sdd, None)
            C.objects.link(h)
            h.parent = w
            h.location = (hx, -0.42, 1.0)
            c = w.pose.bones['forearm.' + sdd].constraints.new('IK')
            c.target, c.chain_count, c.use_tail = h, 2, True
            import plant_chain_b as B
            B.hold(w, sdd, bpy.data.objects[nm + '_Crate'], path[0][0] + 60, 0.75)

    # -- hand pallet jack: a worker pushes a pallet of iced crates along the apron toward our bay
    pj = H.person('HUM_JackPusher', 'plant', 'male', coll=C, seed=34)
    pj.location = (0, 0, 0)
    jack = pallet_jack('YD_PalletJack', C, pj)
    pal = S.pallet('YD_JackPallet', (0, -0.95, 0.05), M, C, D(90))
    pal.parent = jack
    k = 0
    for lv in range(2):
        for ix in (-0.3, 0.3):
            for iy in (-0.21, 0.21):
                crate('YD_JackCrate%d' % k, 'blue' if k % 3 else 'white', (iy, ix, 0.15 + lv * 0.3), D(0), pal,
                      'ice', 700 + k)
                k += 1
    H.walk_cycle(pj, 120, 300, [(120, (19.5, -1.7)), (300, (14.2, -1.7))], stride=0.55,
                 base=H.POSES['push'], arms=False)

    # -- banksman in hi-vis beside the bay (clear of the truck's path), waving it back, then stepping aside
    sup = H.person('HUM_Banksman', 'driver', 'male', coll=C, seed=35)
    sup.location = (12.7, -4.6, 0)
    sup.rotation_euler = (0, 0, D(-120))                       # faces the reversing truck
    H.jitter(sup, H.POSES['look'], 1, 118, every=24, amp=4, seed=35)
    for k, f in enumerate(range(124, 214, 8)):                 # "keep coming": both forearms beckon in rhythm
        a_ = 95 if k % 2 else 60
        H.set_pose(sup, {'upperarm.L': (70, -22, 0), 'forearm.L': (a_, 0, 0), 'upperarm.R': (70, -22, 0),
                         'forearm.R': (a_, 0, 0), 'spine': (4, 0, 0), 'head': (2, 0, 0),
                         'thigh.L': (8, 4, 0), 'thigh.R': (-4, 4, 0)}, f)
    H.set_pose(sup, {'upperarm.L': (85, -8, 0), 'forearm.L': (10, 0, 0), 'upperarm.R': (6, -20, 0),
                     'forearm.R': (25, 0, 0)}, 218)              # flat palm: stop
    H.jitter(sup, H.POSES['look'], 232, 300, every=24, amp=4, seed=38)
    # -- worker at the dock door, watching the truck in, steps back inside before the doors swing
    dw = H.person('HUM_DockDoor', 'plant', 'female', coll=C, seed=39)
    dw.location = (7.75, 0.45, S.DZ)
    dw.rotation_euler = (0, 0, D(-10))
    H.jitter(dw, {'upperarm.R': (30, -14, 0), 'forearm.R': (95, 0, 0), 'upperarm.L': (6, -18, 0),
                  'forearm.L': (25, 0, 0), 'head': (6, 0, -10)}, 1, 236, every=20, amp=4, seed=39)
    H.walk_cycle(dw, 238, 262, [(238, (7.75, 0.45)), (262, (6.3, 2.7))], stride=0.6)
    H.jitter(dw, H.POSES['stand'], 266, 300, every=24, amp=3, seed=40)
    for nm, out, gnd, path, sd in (('HUM_YardW1', 'guard', 'male', [(40, (-10.5, -4.8)), (288, (3.0, -4.6))], 36),
                                   ('HUM_YardW2', 'farm', 'male', [(40, (-11.4, -5.6)), (288, (2.1, -5.5))], 37)):
        w = H.person(nm, out, gnd, coll=C, seed=sd)
        H.walk_cycle(w, 40, 288, path, stride=0.62, phase=sd * 0.7)

    # -- road dust on the trucks, mud on the tyres
    for m in bpy.data.materials:
        n = m.name
        if not n.startswith('TRK_') or any(t in n for t in ('Glass', 'Lamp', 'Refl', 'Interior', 'FloorAlu', 'Plate')):
            continue
        if 'Tyre' in n:
            P.add_dust(m, top=1.25, color=(0.23, 0.17, 0.11), amount=0.8, rough=0.95, scale=6.0)
        else:
            P.add_dust(m, top=1.9, color=(0.46, 0.38, 0.28), amount=0.7, rough=0.9, scale=2.2)
        if any(t in n for t in ('Chassis', 'DarkGrey', 'Bumper', 'UnitGrey')):
            P.add_dust(m, top=1000, color=(0.20, 0.085, 0.035), amount=0.28, rough=0.8, scale=5.0, zscale=0.12,
                       tag='rusted')
    P.add_dust(bpy.data.materials.get('PL_Rubber'), top=1000, color=(0.32, 0.31, 0.29), amount=0.5, rough=0.9,
               scale=9.0, tag='scuffed')
    _stains(C)


def _stain_mat(name, color, rough, scale, stretch, thr):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale * stretch, scale)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Detail'].default_value = 8
    L.new(mp.outputs[0], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = thr
    mr.inputs['From Max'].default_value = thr + 0.3
    mr.inputs['To Max'].default_value = 0.45
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    L.new(mr.outputs[0], p.inputs['Alpha'])
    return m


def _stains(C):
    """Oil drips where trucks park, tyre marks fanning out of the bays (thin decal slabs on the apron)."""
    oil = _stain_mat('YD_Oil', (0.02, 0.018, 0.016), 0.18, 0.9, 1.0, 0.5)
    tyre = _stain_mat('YD_TyreMark', (0.03, 0.03, 0.03), 0.75, 1.4, 0.08, 0.48)
    for bx in S.BAYS:
        p = Part()
        for dy in (-5.2, -7.6):
            p.box((bx, dy, 0.006), (1.6, 1.8, 0.004))
        o = p.make('YD_Oil_%d' % int(bx * 10), oil, None, coll=C)
        o.rotation_euler.z = 0.0
        q = Part()
        for sy in (-0.92, 0.92):
            q.box((bx + sy, -6.5, 0.005), (0.55, 9.0, 0.004))
        q.make('YD_TyreMarks_%d' % int(bx * 10), tyre, None, coll=C)
