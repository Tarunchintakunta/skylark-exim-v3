"""Detailed white rigid reefer truck (cab-over, 2 axles, insulated box, nose-mounted refrigeration unit, twin rear
doors with lock rods). Replaces the boxy library truck for the plant/pond scenes; keeps its interface and names:
root `TRK_RigidReefer` (or `name`), rear-door hinges `TRK_DoorL` / `TRK_DoorR`. Facing +X, origin on the ground under
the rear axle. All part meshes are built in truck coordinates (objects sit at the root origin), so Object texture
coordinates = truck coordinates (dirt gradients by height work). No text, logos or numbers anywhere."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import skpbr as P

BL, BW, BH, BZ = 7.0, 2.5, 2.55, 1.28      # box length, width, height, floor height (dock ~1.2-1.3)
REAR = -2.75                              # rear face x
WB = 4.7                                  # wheelbase (front axle x)
TR = 0.52                                 # tyre radius


def _mats():
    return {
        'white': P.grime_paint('TRK_PaintWhite', (0.80, 0.81, 0.80), rough=0.28, grime=0.55, streak=0.25, coat=0.6),
        'box': P.grime_paint('TRK_BoxGRP', (0.8, 0.79, 0.74), rough=0.36, grime=0.6, streak=0.5, coat=0.3, metal=0.0),
        'alu': P.tex_mat('TRK_Alu', 'Metal009', scale=1.5, tint=(0.85, 0.86, 0.88), rough_mul=0.9, metal=1.0, aniso=0.4),
        'dark': P.plain('TRK_DarkGrey', (0.035, 0.037, 0.04), 0.5, 0.2, bump=0.05),
        'chassis': P.grime_paint('TRK_Chassis', (0.03, 0.03, 0.032), rough=0.45, grime=0.3, streak=0.2, coat=0.0, metal=0.3),
        'rubber': P.tex_mat('TRK_Tyre', 'Rubber004', scale=4.0, tint=(0.35, 0.35, 0.36), rough_mul=1.0, metal=0.0, normal=0.8),
        'rim': P.plain('TRK_Rim', (0.55, 0.56, 0.57), 0.3, 1.0),
        'glass': P.plain('TRK_Glass', (0.10, 0.12, 0.13), 0.04, 0.0, coat=1.0, alpha=0.32),   # see-through: the driver reads
        'chrome': P.plain('TRK_Chrome', (0.9, 0.9, 0.92), 0.08, 1.0),
        'lamp_clear': P.plain('TRK_LampClear', (0.85, 0.85, 0.85), 0.05, 0.0, transmission=0.6, coat=1.0),
        'lamp_red': P.plain('TRK_LampRed', (0.55, 0.02, 0.01), 0.1, 0.0, coat=1.0, emission=(1, 0.03, 0.01), estr=0.6),
        'lamp_amber': P.plain('TRK_LampAmber', (0.8, 0.35, 0.02), 0.1, 0.0, coat=1.0, emission=(1, 0.4, 0.02), estr=0.3),
        'reflect_red': P.plain('TRK_ReflRed', (0.5, 0.02, 0.02), 0.25, 0.3),
        'reflect_white': P.plain('TRK_ReflWhite', (0.8, 0.8, 0.8), 0.25, 0.4),
        'seal': P.plain('TRK_Seal', (0.02, 0.02, 0.022), 0.6, 0.0),
        'grille': P.plain('TRK_Grille', (0.06, 0.065, 0.07), 0.45, 0.6),
        'unit': P.grime_paint('TRK_UnitGrey', (0.62, 0.64, 0.66), rough=0.4, grime=0.5, streak=0.3, coat=0.2),
        'plate': P.plain('TRK_PlateBlank', (0.85, 0.82, 0.55), 0.35, 0.1),
        'interior': P.plain('TRK_BoxInterior', (0.42, 0.43, 0.43), 0.4, 0.3, bump=0.08),   # used aluminium liner, not paper white
        'floor': P.tex_mat('TRK_FloorAlu', 'metal_plate', scale=1.0, tint=(0.8, 0.8, 0.82), metal=1.0, rough_mul=0.8),
    }


class Part:
    """Accumulates geometry for one object, then makes it with optional bevel modifier."""

    def __init__(self):
        self.bm = bmesh.new()

    def box(self, c, s, rot=None):
        r = bmesh.ops.create_cube(self.bm, size=1)['verts']
        m = Matrix.Translation(c) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*s, 1))
        bmesh.ops.transform(self.bm, matrix=m, verts=r)
        return r

    def cyl(self, a, b, r, seg=16, r2=None, cap=True):
        a, b = Vector(a), Vector(b)
        d = b - a
        res = bmesh.ops.create_cone(self.bm, cap_ends=cap, segments=seg, radius1=r, radius2=r if r2 is None else r2,
                                    depth=d.length)
        q = d.normalized().to_track_quat('Z', 'Y')
        m = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        bmesh.ops.transform(self.bm, matrix=m, verts=res['verts'])
        return res['verts']

    def hull(self, pts):
        vs = [self.bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(self.bm, input=vs)
        kill = [g for g in res.get('geom_interior', []) if isinstance(g, bmesh.types.BMVert)]
        if kill:
            bmesh.ops.delete(self.bm, geom=kill, context='VERTS')

    def make(self, name, mat, parent, bevel=0.0, seg=2, smooth=False, coll=None):
        me = bpy.data.meshes.new(name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        self.bm.to_mesh(me)
        self.bm.free()
        me.materials.append(mat)
        o = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(o)
        o.parent = parent
        if bevel:
            b = o.modifiers.new('bevel', 'BEVEL')
            b.width = bevel
            b.segments = seg
            b.limit_method = 'ANGLE'
            b.harden_normals = False
            for p in me.polygons:
                p.use_smooth = True
            wn = o.modifiers.new('wn', 'WEIGHTED_NORMAL')
            wn.keep_sharp = True
        elif smooth:
            for p in me.polygons:
                p.use_smooth = True
        return o


def _empty(name, loc, parent, coll):
    e = bpy.data.objects.new(name, None)
    (coll or bpy.context.scene.collection).objects.link(e)
    e.parent = parent
    e.location = loc
    e.empty_display_size = 0.3
    return e


_SHARED = {}


def _wheel_meshes(M):
    if 'tyre' in _SHARED:
        return _SHARED['tyre'], _SHARED['rim']
    # tyre: lathe of a rounded profile around Y
    bm = bmesh.new()
    prof = []
    w = 0.30
    GROOVES = (-0.085, -0.03, 0.03, 0.085)             # a road tyre (#255): ribbed tread with circumferential grooves, no lugs
    for i in range(25):
        a = math.pi * i / 24
        y = -w / 2 + w * (1 - math.cos(a)) / 2
        crown = TR - 0.06 + 0.06 * math.sin(a)
        groove = sum(0.012 * max(0.0, 1 - abs(y - g) / 0.011) for g in GROOVES) if 0.1 < a < math.pi - 0.1 else 0.0
        prof.append((crown - groove, y))
    prof = [(0.33, -w / 2 + 0.02)] + prof + [(0.33, w / 2 - 0.02)]
    seg = 64
    rings = []
    for k in range(seg):
        t = 2 * math.pi * k / seg
        rings.append([bm.verts.new((r * math.cos(t), y, r * math.sin(t))) for r, y in prof])
    for k in range(seg):
        a, b = rings[k], rings[(k + 1) % seg]
        for i in range(len(prof) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    me = bpy.data.meshes.new('TRK_TyreMesh')
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(M['rubber'])
    # rim: dish + hub + nuts
    p = Part()
    p.cyl((0, -0.13, 0), (0, 0.13, 0), 0.335, 32)
    p.cyl((0, 0.13, 0), (0, 0.16, 0), 0.17, 24, r2=0.12)
    for k in range(8):
        t = 2 * math.pi * k / 8
        p.cyl((0.13 * math.cos(t), 0.15, 0.13 * math.sin(t)), (0.13 * math.cos(t), 0.18, 0.13 * math.sin(t)), 0.017, 6)
    for k in range(6):
        t = 2 * math.pi * (k + 0.5) / 6
        p.cyl((0.24 * math.cos(t), 0.12, 0.24 * math.sin(t)), (0.24 * math.cos(t), 0.14, 0.24 * math.sin(t)), 0.045, 10)
    rbm = p.bm
    rme = bpy.data.meshes.new('TRK_RimMesh')
    rbm.to_mesh(rme)
    rbm.free()
    rme.materials.append(M['rim'])
    for poly in rme.polygons:
        poly.use_smooth = True
    _SHARED['tyre'], _SHARED['rim'] = me, rme
    return me, rme


def _cut_windows(cab, name, root, coll, cx1, W2):
    """Shell the convex cab hull (4 cm walls) and cut the windscreen and side-window openings through it, so the
    interior and the driver read through the glass panes, which overlap the openings by 3 cm all round."""
    sol = cab.modifiers.new('shell', 'SOLIDIFY')
    sol.thickness, sol.offset, sol.use_even_offset = 0.04, -1.0, True
    p = Part()
    a, b = Vector((cx1 + 0.02, 0, 1.80)), Vector((cx1 - 0.025, 0, 2.76))
    ang = math.atan2(b.x - a.x, b.z - a.z)
    for sy in (-1, 1):
        p.box((a + b) / 2 + Vector((0, sy * 0.52, 0)), (0.4, 0.9, (b - a).length - 0.06), Euler((0, ang, 0)))
        p.box((cx1 - 0.55, sy * W2, 2.33), (0.69, 0.4, 0.56))
        p.box((cx1 - 1.3, sy * W2, 2.45), (0.29, 0.4, 0.29))
    cut = p.make(name + '_WindowCut', None, root, coll=coll)
    cut.hide_render = True
    cut.display_type = 'WIRE'
    bo = cab.modifiers.new('windows', 'BOOLEAN')
    bo.operation, bo.solver, bo.object = 'DIFFERENCE', 'EXACT', cut


def reefer_truck(name='TRK_RigidReefer', loc=(0, 0, 0), rot_z=0.0, coll=None, load=True, seed=1,
                 cab_color=None, crate_fn=None):
    """Returns dict: root, wheels (list of (obj, is_front)), steer (front steer empties), door_l, door_r, cab_door,
    reverse_mat, rear_x, cargo."""
    M = _mats()
    if cab_color:
        M['white'] = P.grime_paint('TRK_Paint_%s' % name, cab_color, rough=0.3, grime=0.55, streak=0.25, coat=0.6)
    import sklib
    M['door'] = M['box'].copy()
    M['door'].name = 'TRK_BoxGRP_Door'
    sklib.weather(M['door'], streak=(0.33, 0.26, 0.17), amount=0.6, z0=-BH / 2 + 0.11, z1=-BH / 2 + 0.95,
                  dirt=(0.2, 0.15, 0.1), dirt_amount=0.75, scale=0.8)   # doors live in hinge space (z centred on 0)
    sklib.weather(M['interior'], streak=(0.36, 0.33, 0.28), amount=0.35, z0=BZ, z1=BZ + 0.7, dirt=(0.24, 0.21, 0.17),
                  dirt_amount=0.7, scale=1.2)                      # scuffed, stained liner near the floor
    sklib.weather(M['box'], streak=(0.33, 0.26, 0.17), amount=0.75, z0=BZ, z1=BZ + 0.9, dirt=(0.2, 0.15, 0.1),
                  dirt_amount=0.9, scale=0.8)                      # heavy road grime on the lower third + streaks
    M['rust'] = sklib.weather(P.grime_paint('TRK_RearSteel', (0.32, 0.32, 0.33), rough=0.5, grime=0.7, streak=0.6,
                                             coat=0.1, metal=0.4),
                              streak=(0.36, 0.15, 0.05), amount=0.85, z0=0.0, z1=4.5, dirt=(0.3, 0.13, 0.05),
                              dirt_amount=0.5, scale=1.6)          # rust bleeding from hinges and the rear frame
    sklib.weather(M['white'], streak=(0.3, 0.24, 0.16), amount=0.35, z0=0.35, z1=1.45, dirt=(0.22, 0.17, 0.11),
                  dirt_amount=0.65, scale=0.8)                     # mud on the cab's lower panels and steps
    root = _empty(name, loc, None, coll)
    root.rotation_euler = (0, 0, rot_z)
    root.empty_display_size = 1.5
    R = {'root': root, 'rear_x': REAR}
    cx0, cx1 = REAR + BL + 0.12, REAR + BL + 2.05      # cab back / front
    # ---------------- chassis
    p = Part()
    for sy in (-0.43, 0.43):
        p.box((0.9, sy, 0.92), (8.0, 0.08, 0.26))
    for x in (-2.4, -1.2, 0.0, 1.4, 2.8, 4.0):
        p.box((x, 0, 0.92), (0.1, 0.86, 0.2))
    p.box((0.0, 0, TR), (0.18, 1.7, 0.16))           # rear axle
    p.cyl((0.0, -0.18, TR), (0.0, 0.18, TR), 0.2, 16)  # diff
    p.box((WB, 0, TR + 0.05), (0.14, 1.75, 0.12))     # front axle
    p.box((REAR + 0.15, 0, 0.62), (0.12, 2.3, 0.14))  # under-run bar
    for sy in (-0.9, 0.9):
        p.box((REAR + 0.15, sy, 0.8), (0.08, 0.08, 0.35))
    # side guards between axles
    for sy in (-1.12, 1.12):
        for z in (0.68, 0.9):
            p.box((2.35, sy, z), (3.2, 0.03, 0.1))
        for x in (1.0, 2.35, 3.7):
            p.box((x, sy * 0.96, 0.85), (0.05, 0.3, 0.35))
    # fuel tank (+Y side), battery box, air tanks (-Y side)
    p.cyl((1.0, 0.95, 0.78), (2.2, 0.95, 0.78), 0.26, 20)
    p.box((3.3, -0.88, 0.8), (0.6, 0.35, 0.4))
    p.cyl((0.9, -0.82, 0.86), (1.9, -0.82, 0.86), 0.12, 12)
    p.make(name + '_Chassis', M['chassis'], root, bevel=0.012, coll=coll)
    # fuel tank sheen part
    p = Part()
    p.cyl((1.0, 0.95, 0.78), (2.2, 0.95, 0.78), 0.265, 24)
    p.make(name + '_Tank', M['alu'], root, smooth=True, coll=coll)
    # mudguards (rear) as half-cylinder shells
    p = Part()
    for sy in (-0.92, 0.92):
        bm = p.bm
        seg = 12
        prev = None
        for k in range(seg + 1):
            t = math.pi * k / seg
            x = -math.cos(t) * (TR + 0.12)
            z = TR + math.sin(t) * (TR + 0.12)
            vs = [bm.verts.new((x, sy - 0.33, z)), bm.verts.new((x, sy + 0.33, z))]
            if prev:
                bm.faces.new((prev[0], prev[1], vs[1], vs[0]))
            prev = vs
    p.make(name + '_Mudguards', M['dark'], root, smooth=True, coll=coll).modifiers.new('sol', 'SOLIDIFY').thickness = 0.02
    # mud flaps
    p = Part()
    for sy in (-0.92, 0.92):
        p.box((-0.75, sy, 0.45), (0.01, 0.6, 0.55))
        p.box((WB - 0.75, sy * 1.0, 0.5), (0.01, 0.45, 0.45))
    p.make(name + '_Flaps', M['seal'], root, coll=coll)

    # ---------------- insulated box
    bx = REAR + BL / 2
    p = Part()
    p.box((bx, 0, BZ + BH / 2), (BL, BW, BH))
    p.bm.normal_update()
    bmesh.ops.delete(p.bm, geom=[f for f in p.bm.faces if f.normal.x < -0.9], context='FACES')   # open rear
    o = p.make(name + '_Box', M['box'], root, bevel=0.06, seg=4, coll=coll)
    o.modifiers.new('sol', 'SOLIDIFY').thickness = 0.08
    p = Part()
    for sy in (-1, 1):
        p.box((bx, sy * (BW / 2 + 0.012), BZ + 0.07), (BL - 0.02, 0.03, 0.14))       # bottom rub rail
        p.box((bx, sy * (BW / 2 + 0.006), BZ + BH - 0.05), (BL - 0.1, 0.02, 0.07))   # top rail
        for x in (REAR + 1.75, REAR + 3.5, REAR + 5.25):
            p.box((x, sy * (BW / 2 + 0.004), BZ + 0.05), (0.08, 0.02, 0.06))
    # body floor sill / cross members under the box
    for x in [REAR + 0.3 + i * 0.6 for i in range(12)]:
        p.box((x, 0, BZ - 0.06), (0.06, BW - 0.1, 0.1))
    p.box((bx, 0, BZ - 0.12), (BL, 0.9, 0.04))
    p.make(name + '_BoxTrim', M['alu'], root, bevel=0.006, coll=coll)
    p = Part()                                                    # bonded panel seams on the box sides and roof
    for sy in (-1, 1):
        for k in range(1, 6):
            p.box((REAR + k * BL / 6, sy * (BW / 2 + 0.003), BZ + BH / 2), (0.012, 0.004, BH - 0.2))
    for k in range(1, 6):
        p.box((REAR + k * BL / 6, 0, BZ + BH + 0.003), (0.012, BW - 0.2, 0.004))
    p.make(name + '_BoxSeams', M['dark'], root, coll=coll)
    # rear frame (portal) around the doors
    p = Part()
    p.box((REAR - 0.02, BW / 2 - 0.05, BZ + BH / 2), (0.1, 0.12, BH + 0.02))
    p.box((REAR - 0.02, -BW / 2 + 0.05, BZ + BH / 2), (0.1, 0.12, BH + 0.02))
    p.box((REAR - 0.02, 0, BZ + BH - 0.06), (0.1, BW, 0.14))
    p.box((REAR - 0.04, 0, BZ - 0.02), (0.14, BW, 0.16))
    p.make(name + '_RearFrame', M['rust'], root, bevel=0.01, coll=coll)
    # rear lights, reflectors, blank plate, bumper lamps
    p = Part()
    for sy in (-1, 1):
        p.box((REAR + 0.12, sy * 0.95, 0.66), (0.05, 0.36, 0.14))
    p.box((REAR + 0.12, 0, 0.84), (0.03, 0.5, 0.13))
    p.make(name + '_LightBar', M['dark'], root, coll=coll)
    p = Part()
    for sy in (-1, 1):
        p.box((REAR + 0.09, sy * 1.05, 0.66), (0.03, 0.12, 0.1))
    p.make(name + '_TailLamps', M['lamp_red'], root, bevel=0.01, coll=coll)
    p = Part()
    for sy in (-1, 1):
        p.box((REAR + 0.09, sy * 0.88, 0.66), (0.03, 0.08, 0.1))
    p.make(name + '_Indicators', M['lamp_amber'], root, bevel=0.01, coll=coll)
    p = Part()
    p.box((REAR + 0.1, 0, 0.84), (0.02, 0.46, 0.11))
    p.make(name + '_Plate', M['plate'], root, bevel=0.005, coll=coll)
    rm = bpy.data.materials.new('TRK_Reverse_' + name)
    rm.use_nodes = True
    pr = rm.node_tree.nodes['Principled BSDF']
    pr.inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1)
    pr.inputs['Roughness'].default_value = 0.1
    pr.inputs['Emission Color'].default_value = (1, 0.97, 0.9, 1)
    pr.inputs['Emission Strength'].default_value = 0.0
    p = Part()
    for sy in (-1, 1):
        p.box((REAR + 0.09, sy * 0.74, 0.66), (0.03, 0.1, 0.1))
    p.make(name + '_ReverseLamps', rm, root, bevel=0.01, coll=coll)
    R['reverse_mat'] = rm
    # reflective tape blocks along the box sides and rear (alternating red / white, decals only)
    for mk, col in (('reflect_red', 0), ('reflect_white', 1)):
        p = Part()
        for i in range(22):
            if i % 2 != col:
                continue
            x = REAR + 0.3 + i * 0.3
            for sy in (-1, 1):
                p.box((x, sy * (BW / 2 + 0.03), BZ + 0.07), (0.28, 0.005, 0.05))
        for i in range(8):
            if i % 2 != col:
                continue
            p.box((REAR + 0.21, -0.98 + i * 0.28, 0.62), (0.005, 0.26, 0.05))
        p.make(name + '_Tape_' + mk, M[mk], root, coll=coll)

    # ---------------- rear doors (hinged on the outer edges) with lock rods, hinges, handles, seals
    dw = BW / 2 - 0.05
    for side, sy in (('L', 1), ('R', -1)):
        hn = ('TRK_Door' + side) if name == 'TRK_RigidReefer' else '%s_Door%s' % (name, side)
        h = _empty(hn, (REAR - 0.08, sy * (BW / 2 - 0.1), BZ + BH / 2), root, coll)
        p = Part()
        p.box((0, -sy * dw / 2, 0), (0.07, dw, BH - 0.22))
        d = p.make(hn + '_Panel', M['door'], h, bevel=0.015, coll=coll)
        p = Part()
        for k in (0.22, 0.78):                                    # lock rods
            yy = -sy * dw * k
            p.cyl((-0.06, yy, -BH / 2 + 0.12), (-0.06, yy, BH / 2 - 0.12), 0.018, 10)
            for zz in (-BH / 2 + 0.15, BH / 2 - 0.15):              # keepers
                p.box((-0.05, yy, zz), (0.05, 0.07, 0.1))
            for zz in (-0.25, 0.35):                               # guides
                p.box((-0.05, yy, zz), (0.04, 0.06, 0.05))
            p.box((-0.1, yy - sy * 0.06, -0.05), (0.03, 0.14, 0.04))  # handle
        for zz in (-0.95, -0.3, 0.35, 0.95):                       # hinges
            p.box((-0.05, 0.0, zz), (0.05, 0.16, 0.08))
        p.make(hn + '_Hardware', M['rust'], h, bevel=0.005, coll=coll)
        p = Part()
        p.box((0.03, -sy * dw / 2, BH / 2 - 0.1), (0.04, dw, 0.03))
        p.box((0.03, -sy * dw / 2, -BH / 2 + 0.1), (0.04, dw, 0.03))
        p.box((0.03, -sy * (dw - 0.02), 0), (0.04, 0.03, BH - 0.2))
        p.make(hn + '_Seal', M['seal'], h, coll=coll)
        R['door_' + side.lower()] = h
    # box interior (visible when open): walls + aluminium floor
    p = Part()
    p.box((bx, 0, BZ + 0.02), (BL - 0.2, BW - 0.16, 0.02))
    p.make(name + '_InFloor', M['floor'], root, coll=coll)
    p = Part()
    p.box((bx, BW / 2 - 0.09, BZ + BH / 2), (BL - 0.2, 0.02, BH - 0.2))
    p.box((bx, -BW / 2 + 0.09, BZ + BH / 2), (BL - 0.2, 0.02, BH - 0.2))
    p.box((bx, 0, BZ + BH - 0.1), (BL - 0.2, BW - 0.16, 0.02))
    p.box((REAR + BL - 0.12, 0, BZ + BH / 2), (0.02, BW - 0.16, BH - 0.2))
    p.make(name + '_InWalls', M['interior'], root, coll=coll)

    # ---------------- refrigeration unit (nose mount, above the cab)
    ux = REAR + BL + 0.26
    p = Part()
    p.box((ux, 0, BZ + BH - 0.62), (0.5, 1.95, 1.1))
    p.make(name + '_Unit', M['unit'], root, bevel=0.06, seg=3, coll=coll)
    # condenser face (r8): recessed dark coil panel behind a full set of angled louvre slats, the two fan guards
    # just visible through the gaps; no badges
    p = Part()
    p.box((ux + 0.24, 0, BZ + BH - 0.62), (0.03, 1.84, 0.98))
    p.make(name + '_UnitGrille', M['grille'], root, coll=coll)
    p = Part()
    for k in range(17):
        p.box((ux + 0.285, 0, BZ + BH - 1.08 + 0.06 + k * 0.054), (0.07, 1.8, 0.012), Euler((0, -0.55, 0)))
    for sy in (-0.93, 0.0, 0.93):
        p.box((ux + 0.29, sy, BZ + BH - 0.62), (0.08, 0.04, 1.0))       # slat carriers
    p.box((ux + 0.29, 0, BZ + BH - 0.1), (0.08, 1.9, 0.05))             # frame top / bottom
    p.box((ux + 0.29, 0, BZ + BH - 1.14), (0.08, 1.9, 0.05))
    p.make(name + '_UnitLouvres', M['unit'], root, bevel=0.003, coll=coll)
    p = Part()
    for sy in (-0.45, 0.45):
        for rr in (0.1, 0.18, 0.26):
            res = bmesh.ops.create_circle(p.bm, cap_ends=False, segments=28, radius=rr)
            bmesh.ops.transform(p.bm, matrix=Matrix.Translation((ux + 0.26, sy, BZ + BH - 0.55)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'),
                                verts=res['verts'])
    o = p.make(name + '_UnitRings', M['alu'], root, coll=coll)
    sk = o.modifiers.new('skin', 'WIREFRAME')
    sk.thickness = 0.012

    # ---------------- cab (cab-over), built from a convex hull, then bevelled
    W2 = 1.18
    NB = 0.36                                   # short bonnet nose ahead of the windscreen
    pts = []
    for sy in (-1, 1):
        pts += [(cx0, sy * W2, 1.05), (cx0, sy * W2, 3.0), (cx1 - 0.14, sy * (W2 - 0.04), 3.0),
                (cx1 - 0.03, sy * (W2 - 0.02), 2.86), (cx1 + 0.02, sy * W2, 1.72), (cx1 + 0.02, sy * W2, 1.05)]
    p = Part()
    p.hull(pts)
    cab = p.make(name + '_Cab', M['white'], root, bevel=0.07, seg=4, coll=coll)
    _cut_windows(cab, name, root, coll, cx1, W2)     # hollow cab with real window openings: the driver shows (#255)
    pts = []                                    # bonnet nose: its own hull so the screen corner stays concave
    for sy in (-1, 1):
        pts += [(cx1 - 0.1, sy * (W2 - 0.02), 1.62), (cx1 - 0.1, sy * (W2 - 0.02), 1.0),
                (cx1 + NB - 0.08, sy * (W2 - 0.1), 1.56), (cx1 + NB - 0.02, sy * 0.72, 1.585),
                (cx1 + NB - 0.08, sy * (W2 - 0.1), 1.0), (cx1 + NB - 0.02, sy * 0.72, 1.0)]
    pts += [(cx1 + NB, 0, 1.59), (cx1 + NB, 0, 1.0)]
    p = Part()
    p.hull(pts)
    p.make(name + '_Bonnet', M['white'], root, bevel=0.06, seg=4, coll=coll)
    # windscreen (raked), side windows, door seams, grille, headlamps, bumper, steps, visor, mirrors, wipers
    p = Part()
    a = Vector((cx1 + 0.02, 0, 1.80))
    b = Vector((cx1 - 0.025, 0, 2.76))
    mid = (a + b) / 2
    ang = math.atan2(b.x - a.x, b.z - a.z)
    for sy in (-1, 1):                          # tall upright two-piece screen
        p.box(mid + Vector((0.014, sy * 0.52, 0)), (0.02, 0.96, (b - a).length), Euler((0, ang, 0)))
    for sy in (-1, 1):
        p.box((cx1 - 0.55, sy * (W2 + 0.006), 2.33), (0.75, 0.02, 0.62))
        p.box((cx1 - 1.3, sy * (W2 + 0.006), 2.45), (0.35, 0.02, 0.35))
    p.make(name + '_CabGlass', M['glass'], root, bevel=0.01, coll=coll)
    p = Part()                                  # black rubber seals round the screen and side glass (r8)
    for sy in (-1, 1):
        for z, l in ((1.80, 0.98), (2.76, 0.98)):
            zz = a.z + (b.z - a.z) * (z - a.z) / (b.z - a.z)
            xx = a.x + (b.x - a.x) * (z - a.z) / (b.z - a.z)
            p.box((xx + 0.02, sy * 0.52, zz), (0.03, l, 0.035), Euler((0, ang, 0)))
        p.box(mid + Vector((0.022, sy * 1.0, 0)), (0.03, 0.035, (b - a).length), Euler((0, ang, 0)))
        p.box((cx1 - 0.55, sy * (W2 + 0.01), 2.65), (0.79, 0.02, 0.03))
        p.box((cx1 - 0.55, sy * (W2 + 0.01), 2.01), (0.79, 0.02, 0.03))
        p.box((cx1 - 0.94, sy * (W2 + 0.01), 2.33), (0.03, 0.02, 0.66))
    p.make(name + '_CabSeals', M['dark'], root, bevel=0.005, coll=coll)
    p = Part()
    for sy in (-1, 1):
        p.box((cx1 - 0.08, sy * (W2 + 0.004), 1.85), (0.012, 0.012, 1.55))   # front door seam
        p.box((cx0 + 0.35, sy * (W2 + 0.004), 1.85), (0.012, 0.012, 1.55))   # rear door seam
        p.box((cx1 - 0.5, sy * (W2 + 0.012), 1.75), (0.18, 0.02, 0.04))      # door handle
        p.box((cx1 + 0.04, sy * (W2 + 0.03), 1.55), (0.025, 0.025, 0.55))    # grab handle by the door
    p.make(name + '_CabSeams', M['dark'], root, coll=coll)
    # Indian rigid-truck front (Tata LPT / Ashok Leyland style, no badges): black slatted grille panel in a bright
    # frame, twin round headlamps in square bezels, a deep painted steel bumper with fog lamps and a blank yellow
    # commercial plate, accent stripe under the split windscreen, roof marker lamps, big mirrors on tube arms.
    fx = cx1 + NB                               # nose front (centre)
    p = Part()
    p.box((fx - 0.005, 0, 1.30), (0.03, 1.36, 0.42))                        # wide grille panel across the nose
    p.box((cx1 + 0.02, 0, 2.28), (0.03, 0.07, 1.0), Euler((0, -0.04, 0)))    # windscreen centre pillar
    p.make(name + '_Grille', M['grille'], root, bevel=0.005, coll=coll)
    p = Part()
    for k in range(6):
        p.box((fx + 0.018, 0, 1.135 + k * 0.066), (0.022, 1.3, 0.03))         # horizontal slats
    for z in (1.085, 1.515):
        p.box((fx + 0.012, 0, z), (0.035, 1.42, 0.03))                         # frame top / bottom
    for sy in (-1, 1):
        p.box((fx + 0.005, sy * 0.70, 1.30), (0.035, 0.03, 0.46))              # frame sides
    p.make(name + '_GrilleFrame', M['chrome'], root, bevel=0.004, coll=coll)
    p = Part()
    for sy in (-1, 1):
        for yc in (0.84, 1.0):
            p.box((fx - 0.05, sy * yc, 1.36), (0.05, 0.16, 0.16))              # square bezels at the nose corners
    p.make(name + '_LampBezels', M['dark'], root, bevel=0.015, coll=coll)
    p = Part()
    for sy in (-1, 1):
        for yc in (0.84, 1.0):
            p.cyl((fx - 0.03, sy * yc, 1.36), (fx - 0.005, sy * yc, 1.36), 0.06, 20)
        p.cyl((fx + 0.17, sy * 0.86, 0.86), (fx + 0.2, sy * 0.86, 0.86), 0.055, 16)   # fog lamps in the bumper
    p.make(name + '_Headlamps', M['lamp_clear'], root, smooth=True, coll=coll)
    p = Part()
    for sy in (-1, 1):
        p.box((fx - 0.06, sy * 0.93, 1.19), (0.04, 0.26, 0.07))                # indicators under the lamps
        p.box((cx1 - 0.25, sy * 1.12, 3.06), (0.08, 0.1, 0.06))                # roof corner markers
    p.box((cx1 - 0.25, 0, 3.06), (0.08, 0.14, 0.06))
    p.make(name + '_FrontInd', M['lamp_amber'], root, bevel=0.01, coll=coll)
    p = Part()
    p.box((fx - 0.01, 0, 1.555), (0.012, 1.7, 0.035))                         # accent stripe along the nose top
    for sy in (-1, 1):
        p.box((cx1 - 0.6, sy * (W2 + 0.008), 1.79), (1.2, 0.01, 0.06))
    p.make(name + '_Stripe', P.plain('TRK_StripeBlue', (0.03, 0.08, 0.22), 0.35, coat=0.5), root, coll=coll)
    p = Part()
    p.box((fx + 0.1, 0, 0.88), (0.24, 2.1, 0.34))                            # deep steel bumper
    for sy in (-1, 1):
        p.box((fx - 0.07, sy * 1.12, 0.88), (0.36, 0.1, 0.34), Euler((0, 0, sy * 0.5)))   # wrap-round corner guards
        p.box((cx1 - 0.55, sy * 1.08, 0.72), (0.5, 0.26, 0.04))             # step 1
        p.box((cx1 - 0.55, sy * 1.12, 0.95), (0.5, 0.2, 0.04))
    p.make(name + '_Bumper', P.grime_paint('TRK_BumperPaint', (0.16, 0.17, 0.18), rough=0.45, grime=0.6, streak=0.3,
                                           coat=0.2, metal=0.4), root, bevel=0.03, coll=coll)
    p = Part()
    for sy in (-1, 1):                                                       # corner guard bars up the nose
        p.cyl((fx + 0.17, sy * 1.0, 1.05), (fx + 0.05, sy * 1.02, 1.5), 0.022, 10)
        p.cyl((fx + 0.05, sy * 1.02, 1.5), (fx - 0.12, sy * 1.06, 1.56), 0.022, 10)
    p.make(name + '_GuardBars', M['chrome'], root, smooth=True, coll=coll)
    p = Part()
    p.box((cx1 - 0.05, 0, 2.97), (0.34, 2.24, 0.05), Euler((0, -0.28, 0)))   # sun visor
    p.make(name + '_Visor', M['white'], root, bevel=0.02, coll=coll)
    p = Part()
    p.box((fx + 0.225, 0, 0.9), (0.012, 0.5, 0.12))
    p.make(name + '_FrontPlate', P.plain('TRK_PlateYellow', (0.75, 0.58, 0.06), 0.4, coat=0.3), root, bevel=0.006,
           coll=coll)
    p = Part()
    for sy in (-1, 1):
        for zb in (2.62, 2.0):                                                   # two tube arms, each bolted to the cab by a plate
            p.box((cx1 - 0.02, sy * (W2 + 0.012), zb), (0.1, 0.03, 0.12))
            p.cyl((cx1 - 0.02, sy * (W2 + 0.02), zb), (cx1 + 0.1, sy * (W2 + 0.36), zb), 0.018, 8)
        p.box((cx1 + 0.1, sy * (W2 + 0.37), 2.31), (0.07, 0.2, 0.7), Euler((0, 0, sy * 0.1)))   # mirror head: tall and slim
        p.box((cx1 + 0.04, sy * (W2 + 0.22), 2.88), (0.07, 0.15, 0.14))        # kerb mirror
        p.box((cx1 + 0.02, sy * 0.35, 1.84), (0.02, 0.6, 0.02), Euler((0.3 * sy, 0, 0)))  # wiper
    p.make(name + '_Mirrors', M['dark'], root, bevel=0.01, coll=coll)
    p = Part()
    for sy in (-1, 1):
        p.box((cx1 + 0.14, sy * (W2 + 0.37), 2.31), (0.02, 0.17, 0.62), Euler((0, 0, sy * 0.1)))
        p.box((cx1 + 0.085, sy * (W2 + 0.22), 2.88), (0.02, 0.12, 0.11))
    p.make(name + '_MirrorGlass', M['glass'], root, coll=coll)
    # driver door (right-hand drive -> the -Y side when facing +X)
    hn = name + '_CabDoorHinge'
    cdh = _empty(hn, (cx1 - 0.08, -W2 - 0.01, 1.85), root, coll)
    p = Part()
    p.box((-0.35, -0.012, -0.32), (0.72, 0.02, 0.86))                      # lower door skin
    p.box((-0.35, -0.012, 0.73), (0.72, 0.02, 0.05))                       # window frame: top, sides
    for dx in (-0.69, -0.02):
        p.box((dx, -0.012, 0.43), (0.05, 0.02, 0.62))
    p.make(name + '_CabDoorSkin', M['white'], cdh, bevel=0.01, coll=coll)
    p = Part()
    p.box((-0.355, -0.008, 0.43), (0.64, 0.012, 0.6))
    p.make(name + '_CabDoorGlass', M['glass'], cdh, coll=coll)
    R['cab_door'] = cdh
    # cab interior, right-hand drive (Indian): the wheel, column and driver's seat on the right (-Y); dash, binnacle,
    # gear lever in the middle, passenger seat on the left, a floor so the footwell reads through the glass
    p = Part()
    p.box((cx1 - 0.3, 0, 1.94), (0.48, 2.2, 0.28))                          # dashboard
    p.box((cx1 - 0.52, -0.55, 2.13), (0.14, 0.5, 0.12), Euler((0, 0.5, 0)))  # instrument binnacle, driver's side
    p.box((cx1 - 0.7, 0.0, 1.62), (0.5, 0.36, 0.3))                         # centre console
    p.cyl((cx1 - 0.75, 0.0, 1.77), (cx1 - 0.8, 0.0, 2.05), 0.014, 8)        # gear lever
    p.box(((cx0 + cx1) / 2, 0, 1.38), (cx1 - cx0, 2.2, 0.04))               # cab floor
    for sy in (-0.55, 0.55):
        p.box((cx0 + 0.55, sy, 1.75), (0.5, 0.52, 0.15))                    # seat cushion
        p.box((cx0 + 0.3, sy, 2.2), (0.12, 0.5, 0.75), Euler((0, -0.12, 0)))   # backrest, slightly raked
        p.box((cx0 + 0.24, sy, 2.68), (0.1, 0.28, 0.2))                     # headrest
        p.box((cx0 + 0.55, sy, 1.55), (0.36, 0.36, 0.26))                   # seat base
    p.make(name + '_CabInterior', M['dark'], root, coll=coll)
    # steering wheel on the right: rim ring, three spokes, hub, column into the dash; raked like a cab-over wheel
    wc = Vector((cx0 + 1.02, -0.55, 2.2))
    tilt = Euler((0, math.radians(-52), 0))            # wheel plane leans back toward the driver
    u, v = tilt.to_matrix() @ Vector((0, 1, 0)), tilt.to_matrix() @ Vector((0, 0, 1))
    p = Part()
    n, rr = 28, 0.235
    ring = [wc + u * (rr * math.cos(2 * math.pi * k / n)) + v * (rr * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for k in range(n):
        p.cyl(ring[k], ring[(k + 1) % n], 0.018, 8)
    for ang in (math.pi / 2 + 0.0, math.pi * 7 / 6, math.pi * 11 / 6):
        p.cyl(wc, wc + u * (rr * math.cos(ang)) + v * (rr * math.sin(ang)), 0.012, 6)
    nrm = tilt.to_matrix() @ Vector((1, 0, 0))
    p.cyl(wc - nrm * 0.02, wc + nrm * 0.05, 0.05, 16)                     # hub
    p.cyl(wc + nrm * 0.05, Vector((cx1 - 0.5, -0.55, 1.98)), 0.035, 10)    # column
    p.make(name + '_SteeringWheel', M['dark'], root, smooth=True, coll=coll)
    R['wheel_grips'] = []
    for side, ang in (('L', math.radians(20)), ('R', math.radians(160))):   # ten-to-two; +Y is the driver's left
        g = _empty('%s_Grip%s' % (name, side), wc + u * (rr * math.cos(ang)) + v * (rr * math.sin(ang)), root, coll)
        R['wheel_grips'].append(g)
    R['seat_driver'] = Vector((cx0 + 0.52, -0.55, 1.9))                    # driver's hip point, truck-local

    # ---------------- wheels
    tyre, rim = _wheel_meshes(M)
    wheels = []
    steer = []
    for x, front in ((0.0, False), (WB, True)):
        for sy in (-1, 1):
            if front:
                st = _empty('%s_Steer%s' % (name, 'L' if sy > 0 else 'R'), (x, sy * 0.98, TR), root, coll)
                steer.append(st)
                offs = [(0.0, st)]
            else:
                offs = [(sy * 0.98, root), (sy * 0.66, root)]
            for yo, par in offs:
                w = bpy.data.objects.new('%s_Wheel' % name, tyre)
                (coll or bpy.context.scene.collection).objects.link(w)
                w.parent = par
                w.location = (0, yo, 0) if front else (x, yo, TR)
                if sy < 0:
                    w.scale = (1, -1, 1)
                rr = bpy.data.objects.new('%s_Rim' % name, rim)
                (coll or bpy.context.scene.collection).objects.link(rr)
                rr.parent = w
                if (not front) and abs(yo) < 0.8:
                    rr.scale = (1, -1, 1)
                wheels.append((w, front))
    R['wheels'] = wheels
    R['steer'] = steer

    # wheel arches (#255): a painted half-shell over each front tyre and one over each rear twin, so the tyres sit in the body
    p = Part()
    for x, y0, wd in ((WB, 0.98, 0.34), (0.0, 0.82, 0.74)):
        for sy in (-1, 1):
            for k in range(11):
                th = math.radians(14 + k * 15.2)
                rr_ = TR + 0.09
                p.box((x + rr_ * math.cos(th), sy * y0, TR + rr_ * math.sin(th)), (0.15, wd, 0.035),
                      Euler((0, math.atan2(-math.cos(th), -math.sin(th)), 0)))
    p.make(name + '_Arches', M['dark'], root, bevel=0.008, coll=coll)
    p = Part()                                                               # bumper detail: bolt heads, slots, tow eyes
    for k in range(-4, 5):
        p.cyl((fx + 0.225, k * 0.23, 0.99), (fx + 0.245, k * 0.23, 0.99), 0.02, 10)
    for sy in (-1, 1):
        p.box((fx + 0.23, sy * 0.45, 0.8), (0.02, 0.38, 0.06))
        p.cyl((fx + 0.12, sy * 0.35, 0.7), (fx + 0.34, sy * 0.35, 0.7), 0.03, 10)
    p.make(name + '_BumperDetail', M['chrome'], root, smooth=True, coll=coll)

    # ---------------- cargo: iced crates stacked inside (seen when the doors open)
    R['cargo'] = []
    if load and crate_fn:
        rnd = random.Random(seed)
        k = 0
        for ix in range(5):
            for iy in (-0.66, 0.0, 0.66):
                top = 3 if ix == 0 else rnd.choice((2, 3, 3))       # uneven stacks; the front row is unloaded
                for lv in range(top):                                # three high at most: the top layer is seen into
                    c = crate_fn('%s_Cargo%02d' % (name, k), rnd.choice(['blue', 'blue', 'white', 'red']),
                                 (REAR + 0.3 + ix * 0.43, iy, BZ + 0.04 + lv * 0.3), math.pi / 2, root,
                                 'shrimp' if lv == top - 1 else ('ice' if ix == 0 else None), k)   # iced catch on top
                    R['cargo'].append(c)
                    k += 1
    return R


def set_reverse(R, seq):
    """seq: [(frame, on)] keyed constant."""
    s = R['reverse_mat'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for f, on in seq:
        s.default_value = 8.0 if on else 0.0
        s.keyframe_insert('default_value', frame=f)
    fc = R['reverse_mat'].node_tree.animation_data.action
    for c in _fcurves(fc):
        for kp in c.keyframe_points:
            kp.interpolation = 'CONSTANT'


def _fcurves(action):
    if action is None:
        return []
    if hasattr(action, 'fcurves') and action.fcurves is not None:
        try:
            return list(action.fcurves)
        except Exception:
            pass
    out = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def drive(R, path, f0, f1, reverse_frames=(), step=1):
    """Key the truck root along path(f) -> (x, y, heading) for f in [f0, f1]; wheels spin from distance travelled
    (sign from the direction of motion relative to heading), front wheels steer from the heading rate."""
    root = R['root']
    prev = None
    spin = 0.0
    for f in range(f0, f1 + 1, step):
        x, y, hd, st = path(f)
        root.location = (x, y, root.location.z)
        root.rotation_euler = (0, 0, hd)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        if prev is not None:
            d = Vector((x - prev[0], y - prev[1]))
            fwd = Vector((math.cos(hd), math.sin(hd)))
            spin += d.dot(fwd) / TR
        for w, front in R['wheels']:
            w.rotation_euler = (0, spin, 0)
            w.keyframe_insert('rotation_euler', frame=f)
        for s in R['steer']:
            s.rotation_euler = (0, 0, st)
            s.keyframe_insert('rotation_euler', frame=f)
        prev = (x, y)
