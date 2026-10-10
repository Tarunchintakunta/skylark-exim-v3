"""Plant + cold-chain assets for the Skylark library (ASSET_LIBRARY.md 'Vehicles' + 'Sets'): the white rigid reefer
truck (TRK_RigidReefer), the plant exterior with loading bays, the plant interior (dock, intake, wash, processing,
lab, freezers, packing, cold store), steel trolleys, pallets, forklift, trees. Deterministic (seeded) so every scene
that builds the set gets identical objects with identical names (shared boundary frames)."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
from sklib import (M, pbr, weather, empty, obj, box, cyl, cyl_mesh, sphere, sphere_mesh, box_mesh, tube, bm_to_mesh, crate, D,
                   person, ice_mesh, _node, _sock, principled)
from sklib_port import MB


def panel_mat(name='MAT_InsulPanel', color=(0.88, 0.89, 0.9), seam=1.15, axis='X'):
    """Insulated sandwich panel: white with vertical seams every ~1.15 m (bump from a wave texture)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = pbr(name, color, 0.4, 0.05, var=0.04, bump=0.0, grime=0.15, scale=0.5)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1200, -800))
    wv = _node(nt, 'ShaderNodeTexWave', (-900, -800))
    wv.wave_type = 'BANDS'
    wv.bands_direction = axis
    wv.wave_profile = 'SAW'
    wv.inputs['Scale'].default_value = 1.0 / seam
    l.new(_sock(tc, 'Object', out=True), wv.inputs['Vector'])
    mr = _node(nt, 'ShaderNodeMapRange', (-700, -800))
    mr.inputs['From Min'].default_value = 0.93
    mr.inputs['From Max'].default_value = 1.0
    l.new(_sock(wv, 'Factor', out=True), mr.inputs['Value'])
    b = _node(nt, 'ShaderNodeBump', (-300, -800))
    b.inputs['Strength'].default_value = 0.6
    b.inputs['Distance'].default_value = 0.01
    l.new(mr.outputs[0], b.inputs['Height'])
    l.new(b.outputs[0], p.inputs['Normal'])
    return m


# ---------------------------------------------------------------- the white rigid reefer truck
def reefer_truck(name='TRK_RigidReefer', loc=(0, 0, 0), rot_z=0.0, mats=None, cab_color=(0.86, 0.87, 0.86),
                 load=True, seed=1):
    """Rigid reefer truck facing +X. Origin on the ground under the rear axle. Box 7.2 m, rear doors at the -X end.
    Returns dict: root, wheels, door_l, door_r (hinges at the rear corners), cab_door, reverse (light objects),
    rear_x (local x of the rear face), cargo (crates inside)."""
    mats = mats or M()
    root = empty(name, loc, size=1.5)
    root.rotation_euler = (0, 0, rot_z)
    # working truck, not showroom: panel seams, grime streaks from the roof rail, road dirt up the lower sides
    paint = weather(pbr('MAT_TruckCab', cab_color, 0.32, 0.2, grime=0.3, coat=0.5, scale=0.6), amount=0.35,
                    z0=0.3, z1=1.5, dirt_amount=0.75)
    boxw = weather(panel_mat("MAT_ReeferBox", (0.86, 0.87, 0.86), 0.6, "X"), streak=(0.42, 0.38, 0.3), amount=0.32,
                   z0=1.1, z1=2.0, dirt_amount=0.45)
    dark = pbr('MAT_TruckDark', (0.06, 0.065, 0.07), 0.6, 0.3, grime=0.5)
    mb = MB()
    BL, BW, BH, BZ = 7.2, 2.5, 2.6, 1.15     # box length/width/height, floor height
    rear = -2.2
    R = {'root': root, 'rear_x': rear}
    # chassis
    for sy in (-0.45, 0.45):
        mb.box((1.6, sy, 0.85), (8.4, 0.22, 0.3), dark)
    # insulated box with rounded-ish edges (corner caps) and a bottom rail
    bx = rear + BL / 2
    # hollow (floor, roof, sides, front wall): the load shows through the open rear doors
    mb.box((bx, 0, BZ + 0.04), (BL, BW, 0.08), boxw)
    # roof: grey with soot, pooled-water stains and seams (seen from above it was a bare white slab)
    roofm = weather(pbr('MAT_ReeferRoof', (0.55, 0.56, 0.54), 0.55, 0.2, grime=1.0, scale=0.35), streak=(0.25, 0.23, 0.2),
                    amount=0.9, z0=BZ + BH - 0.2, z1=BZ + BH + 0.1, dirt=(0.16, 0.15, 0.13), dirt_amount=0.9, scale=0.6)
    mb.box((bx, 0, BZ + BH - 0.04), (BL, BW, 0.08), roofm)
    for k in range(1, 6):
        mb.box((rear + BL * k / 6, 0, BZ + BH + 0.005), (0.05, BW - 0.06, 0.02), mats['steel'])   # roof bows / seams
    for sy in (-1, 1):
        mb.box((bx, sy * (BW / 2 - 0.04), BZ + BH / 2), (BL, 0.08, BH), boxw)
    mb.box((rear + BL - 0.04, 0, BZ + BH / 2), (0.08, BW, BH), boxw)
    # inside: scuffed grey liner and a dark aluminium floor, not bare white (seen through the open doors)
    liner = weather(pbr('MAT_ReeferLiner', (0.3, 0.31, 0.31), 0.7, 0.0, grime=0.9, scale=0.4), streak=(0.3, 0.28, 0.24),
                    amount=0.7, z0=BZ, z1=BZ + 1.4, dirt=(0.18, 0.16, 0.13), dirt_amount=0.8)
    mb.box((bx, 0, BZ + 0.085), (BL - 0.2, BW - 0.2, 0.01), pbr('MAT_ReeferFloor', (0.16, 0.17, 0.17), 0.5, 0.7, grime=0.9))
    for sy in (-1, 1):
        mb.box((bx, sy * (BW / 2 - 0.085), BZ + BH / 2), (BL - 0.2, 0.01, BH - 0.2), liner)
    mb.box((rear + BL - 0.085, 0, BZ + BH / 2), (0.01, BW - 0.2, BH - 0.2), liner)
    mb.box((bx, 0, BZ + BH - 0.085), (BL - 0.2, BW - 0.2, 0.01), liner)
    for sy in (-1, 1):
        mb.box((bx, sy * (BW / 2 + 0.01), BZ + 0.08), (BL, 0.04, 0.16), mats['steel'])
        mb.box((bx, sy * (BW / 2 + 0.01), BZ + BH - 0.06), (BL, 0.04, 0.12), mats['steel'])
        for x in (rear + 0.04, rear + BL - 0.04):
            mb.box((x, sy * (BW / 2 - 0.02), BZ + BH / 2), (0.1, 0.1, BH), mats['steel'])
    mb.box((rear - 0.02, 0, BZ + BH - 0.06), (0.1, BW, 0.12), mats['steel'])
    mb.box((rear - 0.02, 0, BZ + 0.05), (0.12, BW, 0.1), mats['steel'])
    # under-run bar + rear lights
    mb.box((rear + 0.1, 0, 0.55), (0.12, 2.2, 0.15), dark)
    for sy in (-1.0, 1.0):
        mb.box((rear - 0.03, sy, 0.75), (0.05, 0.3, 0.14), mats['lamp_red'])
    # refrigeration unit on the front wall, top
    mb.box((rear + BL + 0.25, 0, BZ + BH - 0.55), (0.5, 2.1, 0.9), pbr('MAT_FridgeUnit', (0.75, 0.76, 0.77), 0.4, 0.2))
    for k in range(5):
        mb.box((rear + BL + 0.51, -0.8 + k * 0.4, BZ + BH - 0.55), (0.03, 0.3, 0.7), dark)
    # side skirts + tanks
    for sy in (-1, 1):
        mb.box((1.0, sy * 1.0, 0.75), (1.2, 0.4, 0.5), mats['steel'])
    # cab
    cx = rear + BL + 1.35
    mb.box((cx, 0, 1.9), (2.0, 2.4, 2.1), paint)
    mb.box((cx + 0.2, 0, 1.0), (2.2, 2.42, 0.6), paint)
    mb.box((cx + 1.02, 0, 2.3), (0.06, 2.1, 0.95), mats['glass'])
    for sy in (-1.21, 1.21):
        mb.box((cx + 0.2, sy, 2.35), (1.1, 0.04, 0.75), mats['glass'])
        mb.box((cx + 1.15, sy * 1.15, 2.35), (0.08, 0.06, 0.45), mats['plastic_black'])
    mb.box((cx + 1.31, 0, 1.15), (0.06, 2.3, 0.5), dark)                 # bumper
    mb.box((cx + 1.27, 0, 1.5), (0.06, 1.6, 0.35), mats['steel'])        # grille
    for sy in (-0.85, 0.85):
        mb.box((cx + 1.33, sy, 1.42), (0.04, 0.35, 0.16), mats['lamp'])
    mb.box((cx - 0.2, 0, 3.05), (1.4, 2.2, 0.25), paint)                 # roof deflector base
    mb.obj(f'{name}_Body', root)
    # wheels (front axle under the cab, rear axle at origin)
    wm = bpy.data.meshes.get('LIB_TruckWheel') or cyl_mesh('LIB_TruckWheel', 0.5, 0.32, 22, axis='Y', bevel=0.04)
    if not wm.materials:
        wm.materials.append(mats['rubber'])
    hub = bpy.data.meshes.get('LIB_TruckHub') or cyl_mesh('LIB_TruckHub', 0.26, 0.34, 16, axis='Y')
    if not hub.materials:
        hub.materials.append(mats['steel'])
    wheels = []
    for x, dual in ((0.0, True), (cx + 0.1, False)):
        for sy in (-1, 1):
            for off in ((0.98, 0.66) if dual else (1.0,)):
                w = obj(f'{name}_Wheel', wm, None, (x, sy * off, 0.5), parent=root)
                obj(f'{name}_Hub', hub, None, (0, 0, 0), parent=w)
                wheels.append(w)
    R['wheels'] = wheels
    # rear doors, hinged at the rear corners (open by rotating the hinge about Z)
    dm = box_mesh(f'{name}_DoorM', (0.06, BW / 2 - 0.02, BH - 0.1), 0.01, 2)
    dm.materials.append(boxw)
    bar = cyl_mesh(f'{name}_DoorBar', 0.025, BH - 0.2, 8)
    bar.materials.append(mats['steel'])
    for side, sy in (('L', 1), ('R', -1)):
        hinge = empty(f'TRK_Door{side}' if name == 'TRK_RigidReefer' else f'{name}_Door{side}', (rear - 0.03, sy * BW / 2, BZ + BH / 2),
                      root, size=0.3)
        obj(f'{name}_DoorPanel{side}', dm, None, (0, -sy * (BW / 4), 0), parent=hinge)
        for k in (0.25, 0.75):
            obj(f'{name}_DoorBar{side}', bar, None, (-0.05, -sy * BW / 2 * k, 0), parent=hinge)
        R['door_' + side.lower()] = hinge
    # cab door (driver side = +Y in right-hand-drive India -> driver on the right: -Y when facing +X)
    cdh = empty(f'{name}_CabDoorHinge', (cx + 0.8, -1.21, 1.85), root, size=0.3)
    box(f'{name}_CabDoor', (1.1, 0.06, 1.7), (-0.55, -0.02, 0), paint, 0.02, parent=cdh)
    box(f'{name}_CabDoorWin', (0.8, 0.07, 0.6), (-0.5, -0.03, 0.45), mats['glass'], 0.01, parent=cdh)
    R['cab_door'] = cdh
    # reverse lights (emission keyed by the scene)
    rl = []
    for sy in (-0.7, 0.7):
        lm = pbr(f'MAT_ReverseLight_{name}', (1, 1, 1), 0.3, emission=(1, 0.97, 0.9), estrength=0.0, var=0, bump=0)
        rl.append(box(f'{name}_Reverse', (0.05, 0.18, 0.12), (rear - 0.03, sy, 0.75), lm, 0.01, parent=root))
    R['reverse_mat'] = bpy.data.materials[f'MAT_ReverseLight_{name}']
    # cargo: stacked iced crates inside the box (visible when the doors open)
    if load:
        rnd = random.Random(seed)
        cargo = []
        k = 0
        for ix in range(5):
            for iy in (-0.62, 0.0, 0.62):
                for lv in range(4):
                    c = crate(f'{name}_Cargo{k}', rnd.choice(['blue', 'blue', 'white', 'red']),
                              (rear + 0.55 + ix * 0.48 * 1.0, iy, BZ + 0.09 + lv * 0.29), D(90), parent=root, mats=mats,
                              fill=('ice' if lv == 3 else None), seed=k)
                    cargo.append(c)
                    k += 1
        R['cargo'] = cargo
    return R


def set_reverse_lights(R, seq):
    """seq: [(frame, on_bool)]"""
    m = R['reverse_mat']
    p = principled(m)
    s = p.inputs['Emission Strength']
    for f, on in seq:
        s.default_value = 6.0 if on else 0.0
        s.keyframe_insert('default_value', frame=f)


# ---------------------------------------------------------------- props
def trolley(name, loc=(0, 0, 0), rot_z=0.0, mats=None, parent=None):
    """Stainless crate trolley (flat deck on castors with a push handle at -X)."""
    mats = mats or M()
    root = empty(name, loc, parent=parent, size=0.5)
    root.rotation_euler = (0, 0, rot_z)
    mb = MB()
    st = mats['stainless']
    mb.box((0, 0, 0.32), (1.2, 0.7, 0.04), st)
    for sx in (-0.55, 0.55):
        for sy in (-0.3, 0.3):
            mb.cyl((sx, sy, 0.3), (sx, sy, 0.12), 0.02, st, 6)
            mb.cyl((sx, sy - 0.03, 0.07), (sx, sy + 0.03, 0.07), 0.065, mats['rubber'], 10)
    for sy in (-0.3, 0.3):
        mb.cyl((-0.6, sy, 0.32), (-0.68, sy, 1.0), 0.018, st, 6)
    mb.cyl((-0.68, -0.32, 1.0), (-0.68, 0.32, 1.0), 0.02, st, 6)
    mb.obj(f'{name}_Body', root)
    return root


def pallet(name, loc, mats=None, rot_z=0.0, cartons=0, wrap=False, rnd=None):
    mats = mats or M()
    root = empty(name, loc, size=0.5)
    root.rotation_euler = (0, 0, rot_z)
    mb = MB()
    for y in (-0.5, 0, 0.5):
        mb.box((0, y, 0.07), (1.2, 0.1, 0.1), mats['wood'])
    for x in range(7):
        mb.box((-0.54 + x * 0.18, 0, 0.135), (0.12, 1.0, 0.025), mats['wood'])
    if cartons:
        rnd = rnd or random
        for lv in range(cartons):
            for ix in range(3):
                for iy in range(2):
                    mb.box((-0.4 + ix * 0.4, -0.25 + iy * 0.5, 0.15 + 0.15 + lv * 0.3), (0.39, 0.49, 0.29), mats['carton'])
        if wrap:
            mb.box((0, 0, 0.15 + cartons * 0.15), (1.22, 1.02, cartons * 0.3 + 0.02),
                   pbr('MAT_StretchWrap', (0.85, 0.88, 0.9), 0.15, var=0.1, bump=0.4, scale=8, alpha=0.35))
    mb.obj(f'{name}_Body', root)
    return root


def forklift(name, loc, rot_z=0.0, mats=None):
    mats = mats or M()
    root = empty(name, loc, size=1)
    root.rotation_euler = (0, 0, rot_z)
    y = pbr('MAT_ForkliftYellow', (0.85, 0.55, 0.03), 0.4, 0.1, grime=0.3, coat=0.4)
    mb = MB()
    mb.box((0, 0, 0.6), (2.2, 1.1, 0.8), y)
    mb.box((-0.8, 0, 0.9), (0.6, 1.1, 0.9), mats['plastic_black'])
    for sx in (-0.6, 0.7):
        for sy in (-0.5, 0.5):
            mb.cyl((sx, sy - 0.12, 0.3), (sx, sy + 0.12, 0.3), 0.3, mats['rubber'], 14)
    for sy in (-0.45, 0.45):
        mb.box((0.0 + 0.1, sy, 1.6), (0.06, 0.06, 1.3), mats['steel'])
        mb.box((-0.6, sy, 1.6), (0.06, 0.06, 1.3), mats['steel'])
    mb.box((-0.25, 0, 2.25), (0.9, 1.0, 0.06), mats['steel'])
    for sy in (-0.3, 0.3):
        mb.box((1.25, sy, 1.3), (0.1, 0.12, 2.4), mats['steel'])
        mb.box((1.75, sy, 0.08), (1.1, 0.12, 0.05), mats['steel'])
    mb.obj(f'{name}_Body', root)
    return root


def tree(name, loc, h=7.0, mats=None, seed=0, palm=False):
    mats = mats or M()
    rnd = random.Random(seed)
    mb = MB()
    if palm:
        # coconut palm: leaning, slightly curved ringed trunk; 14 arching pinnate fronds of leaflets; nut cluster
        lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * h * rnd.uniform(0.05, 0.14)
        base = Vector(loc)
        pts = [base + lean * (t * t) + Vector((0, 0, h * t)) for t in [i / 8 for i in range(9)]]
        for i in range(8):
            mb.cyl(pts[i], pts[i + 1], 0.2 - 0.06 * i / 8, mats['trunk'], 10, r2=0.2 - 0.06 * (i + 1) / 8)
            mb.cyl(pts[i] + (pts[i + 1] - pts[i]) * 0.5, pts[i] + (pts[i + 1] - pts[i]) * 0.56, 0.205 - 0.06 * i / 8, mats['trunk'], 10)
        top = pts[-1]
        frond = mats.get('palm_frond') or pbr('MAT_PalmFrond', (0.14, 0.24, 0.07), 0.55, var=0.35, bump=0.2, scale=4, grime=0.2)
        for k in range(14):
            a = k * 2 * math.pi / 14 + rnd.uniform(-0.15, 0.15)
            d = Vector((math.cos(a), math.sin(a), 0))
            side = Vector((-d.y, d.x, 0))
            Lf = rnd.uniform(3.2, 4.4)
            up = rnd.uniform(0.3, 0.9)
            prev = None
            for j in range(19):
                t = j / 18
                c = top + d * (Lf * t) + Vector((0, 0, up * 1.6 * t - (1.4 + up) * t * t))
                if prev is not None:
                    mb.beam(prev, c, 0.05, frond)
                    if 2 <= j <= 17:
                        ll = 0.75 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.1
                        for sg in (1, -1):
                            tipp = c + side * (sg * ll) + Vector((0, 0, -0.35 * ll)) + d * 0.12
                            v0 = mb.bm.verts.new(prev)
                            v1 = mb.bm.verts.new(c)
                            v2 = mb.bm.verts.new(tipp)
                            f = mb.bm.faces.new((v0, v1, v2))
                            f.material_index = mb.mi(frond)
                prev = c
        for k in range(5):
            mb.sphere(top + Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), -0.35 - rnd.uniform(0, 0.2))), 0.12,
                      mats['trunk'], 8)
    else:
        mb.cyl(loc, (loc[0], loc[1], loc[2] + h * 0.5), 0.18, mats['trunk'], 8, r2=0.12)
        for k in range(7):
            c = Vector((loc[0] + rnd.uniform(-1.2, 1.2), loc[1] + rnd.uniform(-1.2, 1.2), loc[2] + h * rnd.uniform(0.55, 0.85)))
            res = bmesh.ops.create_icosphere(mb.bm, subdivisions=2, radius=rnd.uniform(1.0, 1.7))
            for v in res['verts']:
                v.co = v.co * Vector((1, 1, 0.8)) + c + Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15)))
            mb._finish(res['verts'], mats['foliage'], None)
    return mb.obj(name)


# ---------------------------------------------------------------- the plant: exterior + interior (one deterministic set)
PLANT = dict(front_y=0.0, dock_z=1.2, bays=6, bay_w=4.6, bay_x0=-11.5, width=64.0, depth=70.0, height=9.0)


def bay_x(i):
    return PLANT['bay_x0'] + i * PLANT['bay_w']


def plant_exterior(mats=None, open_bays=(1, 2), seed=3):
    """Plant facade on y=0 facing -Y (yard at y<0); dock floor inside at z=dock_z. Bays i=0..5 at x=bay_x(i)
    (bay 2 in SCENES.md = index 1, bay 3 = index 2). Returns dict with bay door objects and useful points."""
    mats = mats or M()
    rnd = random.Random(seed)
    P = PLANT
    W, Dp, H, dz = P['width'], P['depth'], P['height'], P['dock_z']
    wall = panel_mat()
    trim = pbr('MAT_PlantTrim', (0.1, 0.32, 0.55), 0.4, grime=0.2)
    mb = MB()
    # facade with bay openings (3.2 wide x 3.3 high above the dock floor)
    ow, oh = 3.2, 3.3
    xs = sorted([bay_x(i) for i in range(P['bays'])])
    edges = [-W / 2] + [v for x in xs for v in (x - ow / 2, x + ow / 2)] + [W / 2]
    for k in range(0, len(edges), 2):
        a, b = edges[k], edges[k + 1]
        if b - a > 0.01:
            mb.box(((a + b) / 2, 0.15, H / 2), (b - a, 0.3, H), wall)
    for x in xs:
        mb.box((x, 0.15, (dz + oh + H) / 2), (ow, 0.3, H - dz - oh), wall)
        mb.box((x, 0.15, dz / 2), (ow, 0.3, dz), mats['concrete'])
    # side and back walls, roof with parapet + blue band
    mb.box((-W / 2, Dp / 2, H / 2), (0.3, Dp, H), wall)
    mb.box((W / 2, Dp / 2, H / 2), (0.3, Dp, H), wall)
    mb.box((0, Dp, H / 2), (W, 0.3, H), wall)
    mb.box((0, Dp / 2, H + 0.1), (W, Dp, 0.2), pbr('MAT_Roof', (0.7, 0.71, 0.72), 0.6, 0.3, grime=0.3, scale=0.2))
    mb.box((0, -0.05, H - 0.4), (W + 0.2, 0.2, 0.5), trim)
    mb.box((0, -0.05, dz + oh + 0.55), (W + 0.2, 0.18, 0.2), trim)
    # dock apron (concrete) and bay furniture
    mb.box((0, -1.6, 0.05), (W, 3.2, 0.1), mats['concrete'])
    sh = pbr('MAT_DockShelter', (0.05, 0.05, 0.055), 0.8, var=0.1, bump=0.3, scale=6)
    yel = pbr('MAT_PaintYellow', (0.85, 0.62, 0.05), 0.6, var=0.2, grime=0.2, scale=0.5)
    for x in xs:
        # dock shelter: padded frame around the opening
        mb.box((x - ow / 2 - 0.25, -0.35, dz + oh / 2 + 0.2), (0.5, 0.7, oh + 0.8), sh)
        mb.box((x + ow / 2 + 0.25, -0.35, dz + oh / 2 + 0.2), (0.5, 0.7, oh + 0.8), sh)
        mb.box((x, -0.35, dz + oh + 0.45), (ow + 1.0, 0.7, 0.5), sh)
        for sx in (-1.1, 1.1):
            mb.box((x + sx, -0.12, dz - 0.3), (0.3, 0.24, 0.45), mats['rubber'])   # bumpers
        mb.box((x, 0.6, dz - 0.02), (2.0, 1.2, 0.05), mats['steel'])                 # leveller
        mb.box((x + 2.05, -0.02, 2.8), (0.25, 0.04, 0.25), yel)                      # blank signal box
        mb.sphere((x + 2.05, -0.06, 2.85), 0.06, mats['lamp_amber'], 8)
        mb.box((x, -0.3, dz + oh + 1.0), (0.6, 0.6, 0.15), mats['lamp'])             # bay light
        # yard bay lines (no text)
        for sx in (-ow / 2 - 0.4, ow / 2 + 0.4):
            mb.box((x + sx, -9.0, 0.012), (0.15, 15.0, 0.02), pbr('MAT_PaintLine', (0.85, 0.85, 0.82), 0.6, var=0.2))
    # roof units and pipes
    for i in range(6):
        mb.box((-20 + i * 8, 12 + (i % 2) * 14, H + 1.0), (3.0, 2.2, 1.6), pbr('MAT_RoofUnit', (0.78, 0.79, 0.8), 0.45, 0.4,
                                                                                  grime=0.3))
        mb.cyl((-20 + i * 8, 12 + (i % 2) * 14, H + 1.8), (-20 + i * 8, 12 + (i % 2) * 14, H + 2.4), 0.6, mats['steel'], 14)
    for k in range(3):
        mb.cyl((-W / 2 + 2, 6 + k * 0.6, H + 0.6), (W / 2 - 2, 6 + k * 0.6, H + 0.6), 0.15, mats['steel'], 8)
    ext = mb.obj('SET_PlantExterior')
    # bay doors (roller doors): closed ones are full panels; open ones rolled up into a drum above the opening
    door_m = panel_mat('MAT_RollerDoor', (0.8, 0.82, 0.84), 0.12, axis='Z')
    doors = {}
    for i in range(P['bays']):
        x = bay_x(i)
        d = box(f'SET_BayDoor{i}', (ow, 0.08, oh), (x, 0.05, dz + oh / 2), door_m, 0.0)
        doors[i] = d
        if i in open_bays:
            d.scale = (1, 1, 0.06)
            d.location.z = dz + oh - 0.1
        cyl(f'SET_BayDrum{i}', 0.22, ow, (x, 0.05, dz + oh + 0.25), mats['steel'], 14, axis='X')
    # yard: asphalt, fence, gate with barrier and gatehouse, lamp posts, trees, potted plants, bollards, parked kit
    box('SET_Yard', (160, 90, 0.2), (0, -45, -0.1), mats['asphalt'], 0.0)
    box('SET_Verge', (400, 300, 0.2), (0, 40, -0.15), mats['grass'], 0.0)
    fm = MB()
    for x in range(-70, 71, 3):
        fm.cyl((x, -70, 0), (x, -70, 2.2), 0.04, mats['steel'], 6)
    for z in (0.3, 1.2, 2.1):
        fm.cyl((-70, -70, z), (-12, -70, z), 0.025, mats['steel'], 5)
        fm.cyl((12, -70, z), (70, -70, z), 0.025, mats['steel'], 5)
    for y in range(-70, 0, 3):
        for x in (-70, 70):
            fm.cyl((x, y, 0), (x, y, 2.2), 0.04, mats['steel'], 6)
    fm.obj('SET_Fence')
    box('SET_Gatehouse', (3.0, 3.0, 2.8), (-15, -72, 0), mats['paint_white'], 0.05, origin='base')
    box('SET_GatehouseRoof', (3.8, 3.8, 0.2), (-15, -72, 2.9), pbr('MAT_PlantTrim', (0.1, 0.32, 0.55), 0.4), 0.03)
    box('SET_GatehouseWin', (3.02, 2.0, 1.0), (-15, -72, 1.6), mats['glass'], 0.01)
    bar_piv = empty('SET_GateBarrier', (-12.5, -70.5, 1.0), size=0.4)
    box('SET_GateBarrierArm', (9.0, 0.1, 0.1), (4.5, 0, 0), pbr('MAT_BarrierStripe', (0.85, 0.1, 0.06), 0.5), 0.01,
        parent=bar_piv)
    for x in range(-60, 61, 20):
        lp = MB()
        lp.cyl((x, -60, 0), (x, -60, 9), 0.12, mats['steel'], 8)
        lp.box((x, -59.4, 9), (0.4, 1.2, 0.2), mats['steel'])
        lp.box((x, -59.0, 8.88), (0.3, 0.5, 0.05), mats['lamp'])
        lp.obj(f'SET_LampPost{x}')
    for i, x in enumerate(range(-66, 67, 8)):
        if abs(x) > 12:
            tree(f'SET_Tree{i}', (x, -67, 0), rnd.uniform(5.5, 8), mats, seed=i, palm=(i % 3 == 0))
    for i in range(6):
        tree(f'SET_SideTree{i}', (-38 - (i % 2) * 4, -10 - i * 8, 0), rnd.uniform(6, 9), mats, seed=40 + i, palm=True)
    pot = cyl_mesh('SET_PotM', 0.35, 0.6, 16, r2=0.28, origin='base')
    pot.materials.append(mats['concrete'])
    for i, x in enumerate((-30, -26, 22, 26)):
        obj(f'SET_Pot{i}', pot, None, (x, -1.5, 0))
        tree(f'SET_PotPlant{i}', (x, -1.5, 0.5), 1.3, mats, seed=80 + i)
    bol = cyl_mesh('SET_BollardM', 0.12, 1.0, 12, origin='base')
    bol.materials.append(yel)
    for i, x in enumerate(range(-24, 25, 4)):
        if all(abs(x - bx) > 2.2 for bx in xs):
            obj(f'SET_Bollard{i}', bol, None, (x, -0.9, 0))
    forklift('SET_Forklift', (24, -6, 0), D(-100), mats)
    for i in range(4):
        pallet(f'SET_YardPallet{i}', (19 + (i % 2) * 1.4, -3 - (i // 2) * 1.3, 0), mats, D(5 * i), cartons=0)
    for i in range(10):
        crate(f'SET_YardCrate{i}', rnd.choice(['blue', 'red', 'white']), (-22 + (i % 3) * 0.65, -2.5 - (i // 6) * 0.5,
                                                                            (i // 3 % 2) * 0.29), 0.0, mats=mats)
    return {'exterior': ext, 'doors': doors}


def plant_interior(mats=None, seed=5):
    """Interior behind the facade, along +Y: dock (0-10), intake hall (10-24), wash (24-32), processing (32-52),
    lab (52-58, glass wall at y=52), freezing + packing (58-66), cold store (66-70+ annex). Floors at dock_z."""
    mats = mats or M()
    rnd = random.Random(seed)
    P = PLANT
    W, Dp, H, dz = P['width'], P['depth'], P['height'], P['dock_z']
    st = mats['stainless']
    wall = panel_mat('MAT_InteriorPanel', (0.9, 0.91, 0.92), 1.2)
    floor = mats['epoxy']
    mb = MB()
    mb.box((0, Dp / 2, dz / 2), (W - 0.4, Dp - 0.4, dz), floor)
    mb.box((0, Dp / 2, H - 0.6), (W - 0.4, Dp - 0.4, 0.2), wall)                 # ceiling
    # interior partitions: dock | intake (strip curtain at y=10), wash/processing open, lab glass at y=52
    for (a, b) in ((-W / 2, -2.0), (2.0, W / 2)):
        mb.box(((a + b) / 2, 10.0, (dz + H) / 2), (b - a, 0.15, H - dz), wall)
    mb.box((0, 10.0, dz + 3.3 + (H - dz - 3.3) / 2), (4.0, 0.15, H - dz - 3.3), wall)
    # LED panels in rows
    led = mats['lamp']
    for y in range(3, int(Dp) - 2, 4):
        for x in range(-24, 25, 6):
            mb.box((x, y, H - 0.72), (1.2, 0.6, 0.04), led)
    # floor drains (dark strips) and wet sheen handled by the epoxy coat
    for y in (14, 22, 30, 40, 48):
        mb.box((0, y, dz + 0.005), (W - 6, 0.15, 0.01), mats['steel'])
    # wash station, boot dip, hose reels on the intake walls
    for x in (-10, -6):
        mb.box((x, 10.6, dz + 0.9), (1.2, 0.6, 0.9), st)
        mb.cyl((x, 10.4, dz + 1.4), (x, 10.4, dz + 1.7), 0.02, st, 6)
    mb.box((0, 11.5, dz + 0.05), (3.2, 1.2, 0.1), pbr('MAT_BootDip', (0.25, 0.45, 0.55), 0.05, coat=1.0))
    for y in (13, 20):
        mb.cyl((-W / 2 + 0.6, y, dz + 1.5), (-W / 2 + 0.9, y, dz + 1.5), 0.35, mats['crate_yellow'], 16)
    # wash tanks (y 24-31) with spray bars
    for k, x in enumerate((-8, -2, 4)):
        mb.box((x, 27.0, dz + 0.55), (4.5, 2.2, 1.1), st)
        mb.box((x, 27.0, dz + 1.06), (4.3, 2.0, 0.04), mats['water_clear'])
        mb.cyl((x - 2, 27.0, dz + 2.2), (x + 2, 27.0, dz + 2.2), 0.04, st, 8)
        for sx in (-1.2, 1.2):
            mb.cyl((x + sx, 26.0, dz + 1.1), (x + sx, 26.0, dz + 2.2), 0.03, st, 6)
    # conveyors (y 32-52) with rollers + grading machine
    for x in (-12, 8):
        mb.box((x, 42, dz + 0.85), (0.9, 20, 0.12), pbr('MAT_ConveyorBelt', (0.85, 0.87, 0.88), 0.4, var=0.05))
        for y in range(32, 53, 2):
            for sx in (-0.4, 0.4):
                mb.box((x + sx, y, dz + 0.4), (0.05, 0.05, 0.8), st)
        mb.box((x - 0.5, 42, dz + 0.95), (0.05, 20, 0.15), st)
        mb.box((x + 0.5, 42, dz + 0.95), (0.05, 20, 0.15), st)
    gm = (8, 35)
    mb.box((gm[0], gm[1], dz + 1.2), (2.4, 3.0, 1.3), st)
    for k in range(6):
        mb.cyl((gm[0] - 1.1, gm[1] - 1.2 + k * 0.48, dz + 1.9), (gm[0] + 1.1, gm[1] - 1.2 + k * 0.48, dz + 1.9), 0.09, st, 12)
    mb.box((gm[0] + 1.6, gm[1], dz + 0.5), (0.8, 2.6, 0.8), st)
    # stainless tables (processing), legs
    tables = []
    for x in (-20, -15, -5, 0, 15, 20):
        for y in (36, 44):
            mb.box((x, y, dz + 0.9), (1.2, 6.0, 0.05), st)
            mb.box((x, y, dz + 0.55), (1.0, 5.8, 0.03), st)
            for sx in (-0.5, 0.5):
                for sy in (-2.8, 2.8):
                    mb.box((x + sx, y + sy, dz + 0.45), (0.05, 0.05, 0.9), st)
            tables.append((x, y))
    # lab glass wall at y=52, lab benches beyond, fridge, cabinet
    glass = pbr('MAT_LabGlass', (0.85, 0.92, 0.95), 0.03, var=0.0, bump=0.0, alpha=0.18)
    for (a, b) in ((-W / 2, -1.2), (1.2, W / 2)):
        mb.box(((a + b) / 2, 52.0, dz + 1.5), (b - a, 0.06, 3.0), glass)
        mb.box(((a + b) / 2, 52.0, dz + 0.05), (b - a, 0.12, 0.1), st)
    mb.box((0, 52.0, dz + 3.2), (W - 0.4, 0.15, 0.4), wall)
    for x in (-6, -2, 2, 6):
        mb.box((x, 55, dz + 0.9), (3.2, 0.9, 0.06), pbr('MAT_LabTop', (0.92, 0.93, 0.94), 0.3))
        mb.box((x, 55, dz + 0.45), (3.1, 0.8, 0.88), wall)
    mb.box((-10, 57.2, dz + 1.0), (1.4, 0.8, 2.0), st)                            # fridge
    mb.box((10, 57.0, dz + 1.3), (1.8, 1.0, 2.6), wall)                             # fume cabinet
    mb.box((10, 56.48, dz + 1.6), (1.6, 0.05, 1.0), glass)
    # plate freezer + freezer doors + glazing belt (58-64)
    pf = (-14, 61)
    mb.box((pf[0], pf[1], dz + 1.2), (3.0, 2.2, 2.4), st)
    for k in range(8):
        mb.box((pf[0], pf[1] - 1.12, dz + 0.3 + k * 0.27), (2.8, 0.04, 0.08), pbr('MAT_Frost', (0.9, 0.94, 0.97), 0.5, var=0.1,
                                                                                  bump=0.5, scale=20))
    mb.box((-8, 64.9, dz + 1.5), (4.0, 0.2, 3.0), panel_mat('MAT_FreezerDoor', (0.92, 0.93, 0.95), 0.4, 'X'))
    mb.box((0, 61, dz + 0.85), (8.0, 0.8, 0.1), pbr('MAT_ConveyorBelt', (0.85, 0.87, 0.88), 0.4, var=0.05))
    mb.box((0, 61, dz + 1.9), (1.0, 1.0, 0.8), st)                                 # glazing spray hood
    # packing tables + carton stacks + strapping machine (58-66, right side)
    for x in (8, 14, 20):
        mb.box((x, 62, dz + 0.85), (3.0, 1.2, 0.06), st)
        for sx in (-1.4, 1.4):
            mb.box((x + sx, 62, dz + 0.42), (0.05, 1.1, 0.85), st)
    mb.box((24, 64, dz + 0.6), (1.4, 1.0, 1.2), pbr('MAT_StrapMachine', (0.2, 0.4, 0.7), 0.4))
    # cold store annex beyond y=Dp: racks 5 levels (cold store visible through a door)
    cs = MB()
    cs.box((0, Dp + 15, dz / 2), (30, 30, dz), floor)
    cs.box((0, Dp + 15, H + 1), (30, 30, 0.2), wall)
    for sx in (-15, 15):
        cs.box((sx, Dp + 15, (dz + H + 1) / 2), (0.2, 30, H + 1 - dz), wall)
    cs.box((0, Dp + 30, (dz + H + 1) / 2), (30, 0.2, H + 1 - dz), wall)
    rack_b = pbr('MAT_RackBlue', (0.05, 0.25, 0.6), 0.4, 0.2, grime=0.1)
    rack_o = pbr('MAT_RackOrange', (0.9, 0.4, 0.05), 0.4, 0.2, grime=0.1)
    frost = pbr('MAT_Frost', (0.9, 0.94, 0.97), 0.5, var=0.1, bump=0.5, scale=20)
    for rx in (-10.5, -4.5, 4.5, 10.5):
        for ry in range(int(Dp) + 2, int(Dp) + 29, 3):
            cs.box((rx - 1.4, ry, (dz + 8.5) / 2), (0.12, 0.12, 8.5 - dz), rack_b)
            cs.box((rx + 1.4, ry, (dz + 8.5) / 2), (0.12, 0.12, 8.5 - dz), rack_b)
        for lv in range(5):
            z = dz + 0.1 + lv * 1.5
            for sx in (-1.4, 1.4):
                cs.box((rx + sx, Dp + 15.5, z), (0.1, 27, 0.14), rack_o)
                cs.box((rx + sx, Dp + 15.5, z + 0.08), (0.1, 27, 0.02), frost)
            for ry in range(int(Dp) + 3, int(Dp) + 28, 2):
                if rnd.random() < 0.88:
                    cs.box((rx, ry + 0.5, z + 0.1 + 0.65), (2.4, 1.2, 1.2), mats['carton'])
                    cs.box((rx, ry + 0.5, z + 0.1 + 0.65), (2.42, 1.22, 1.22),
                           pbr('MAT_StretchWrap', (0.85, 0.88, 0.9), 0.15, var=0.1, bump=0.4, scale=8, alpha=0.35))
    for y in range(int(Dp) + 3, int(Dp) + 29, 4):
        for x in (-7.5, 0, 7.5):
            cs.box((x, y, H + 0.85), (1.0, 0.5, 0.05), led)
    cs.obj('SET_ColdStore')
    # door from the packing area into the cold store with strip curtain
    for k in range(10):
        mb.box((-2.25 + k * 0.5, Dp - 0.2, dz + 1.6), (0.45, 0.02, 3.2), pbr('MAT_StripCurtain', (0.75, 0.82, 0.85), 0.1,
                                                                            alpha=0.4, var=0.0, bump=0.0))
    # intake strip curtain at y=10 (the trolleys push through it)
    curt = []
    for k in range(8):
        c = box(f'SET_Curtain{k}', (0.48, 0.02, 3.2), (-1.75 + k * 0.5, 10.0, dz + 1.6),
                pbr('MAT_StripCurtain', (0.75, 0.82, 0.85), 0.1, alpha=0.4, var=0.0, bump=0.0), 0.0)
        curt.append(c)
    inside = mb.obj('SET_PlantInterior')
    # hall lights (area lights, cool white, even)
    lights = []
    for i, y in enumerate((5, 17, 28, 40, 48, 56, 63, Dp + 8, Dp + 20)):
        ld = bpy.data.lights.new(f'SET_HallLight{i}', 'AREA')
        ld.energy = 9000 if y < Dp else 6000
        ld.shape = 'RECTANGLE'
        ld.size = 40 if y < Dp else 24
        ld.size_y = 9
        ld.color = (0.95, 0.97, 1.0)
        lo = bpy.data.objects.new(f'SET_HallLight{i}', ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = (0, y, H - 0.9 if y < Dp else H + 0.7)
        lights.append(lo)
    return {'interior': inside, 'tables': tables, 'curtains': curt, 'grader': gm, 'plate_freezer': pf}
