"""Plant interior behind the dock (shared by p-intake, p-proc, p-freeze; deterministic, identical names):
  intake  y 12-21  : boot dip, hand-wash sinks, platform scale, crate stacks, hose reels
  wash    y 21-29  : two stainless wash tanks with spray bars and running water, inclined outfeed conveyor
  grade   y 29-41  : long belt conveyor, roller grading machine with chutes into trays
  process y 41-53  : four long stainless tables (peeling / deveining), one fish table, trays and ice
  lab     y 54-60  : glazed partition + door, QC bench, scale, sample trays, cabinet, fridge
  freeze  y 60-69  : plate freezer cabinet, IQF belt tunnel with glazing spray, trolleys of trays
  pack    y 69-77  : packing tables, export cartons (blank labels), strapping + vacuum machines, carton stacks
  cold    y 77-96  : insulated door + strip curtain, pallet racking both sides, wrapped pallets, light frost
Hall x -6..22.4, floor z = DZ, ceiling z = DZ + 5.2. Centre line CX = 8.2 (behind the truck bay)."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import skpbr as P
import skplant as S
from sktruck import Part

DZ = S.DZ
CX = S.TRUCK_BAY - 1.0
XL, XR = -6.0, 22.4
CEIL = DZ + 5.2
Y_END = 84.0


def mats():
    M = S.MATS()
    M.update({
        'water': P.plain('IN_TankWater', (0.25, 0.32, 0.34), 0.02, transmission=0.85, ior=1.33),
        'belt': P.plain('IN_BeltWhite', (0.78, 0.8, 0.8), 0.35, bump=0.2, bump_scale=60),
        'tray_white': P.plain('IN_TrayWhite', (0.8, 0.81, 0.79), 0.35),
        'tray_blue': P.plain('IN_TrayBlue', (0.12, 0.22, 0.38), 0.4),
        'rubber_mat': P.plain('IN_FootDip', (0.05, 0.06, 0.07), 0.6),
        'frost': P.plain('IN_Frost', (0.86, 0.9, 0.93), 0.6, bump=0.6, bump_scale=80),
        'rack_blue': P.grime_paint('IN_RackBlue', (0.08, 0.2, 0.38), rough=0.4, grime=0.2, streak=0.1, coat=0.2),
        'rack_orange': P.grime_paint('IN_RackOrange', (0.62, 0.3, 0.05), rough=0.4, grime=0.2, streak=0.1, coat=0.2),
        'wrap': P.plain('IN_StretchWrap', (0.85, 0.88, 0.9), 0.12, alpha=0.45, coat=0.8, bump=0.2, bump_scale=6),
        'label': P.plain('IN_LabelBlank', (0.95, 0.95, 0.94), 0.5),
        'label_line': P.plain('IN_LabelLine', (0.45, 0.47, 0.5), 0.5),
        'glass_clear': P.plain('IN_GlassClear', (0.95, 0.97, 0.97), 0.0, transmission=1.0, ior=1.05),   # no milky veil
        'tape': P.plain('IN_Tape', (0.7, 0.6, 0.42), 0.3, coat=0.4),
        'strap': P.plain('IN_Strap', (0.75, 0.75, 0.73), 0.4),
        'vacbag': P.plain('IN_VacBag', (0.66, 0.58, 0.55), 0.22, coat=1.0),      # glazed frozen block in film
        'block': P.plain('IN_FrozenBlock', (0.72, 0.74, 0.74), 0.25, coat=0.5, sss=0.2),
    })
    return M


def _light(name, loc, size=(6, 3), energy=600, C=None, color=(1.0, 0.95, 0.87)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = size
    ld.energy = energy
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    C.objects.link(lo)
    lo.location = loc
    ld.use_shadow = (sum(map(ord, name)) % 2 == 0)     # half the fills cast shadows (shadow pool budget)
    return lo


def shell(C, M):
    p = Part()
    p.box(((XL + XR) / 2, 72.0, DZ / 2), (XR - XL, 24, DZ))
    p.make('IN_FloorSlab2', M['epoxy'], None, coll=C)
    p = Part()
    p.box(((XL + XR) / 2, (12 + Y_END) / 2, CEIL + 0.05), (XR - XL, Y_END - 12, 0.1))
    p.make('IN_Ceiling', M['panel_in'], None, coll=C)
    p = Part()
    for x in (XL, XR):
        p.box((x, (12 + Y_END) / 2, (DZ + CEIL) / 2), (0.16, Y_END - 12, CEIL - DZ))
    p.box(((XL + XR) / 2, Y_END, (DZ + CEIL) / 2), (XR - XL, 0.16, CEIL - DZ))
    p.make('IN_Walls', M['panel_in'], None, coll=C)
    p = Part()
    for x in (XL + 0.1, XR - 0.1):
        p.box((x, (12 + Y_END) / 2, DZ + 0.2), (0.03, Y_END - 12, 0.4))
    p.make('IN_Kick', M['stainless'], None, coll=C)
    # LED panels in rows + area lights
    p = Part()
    for y in [13.5 + i * 3.0 for i in range(24)]:
        for x in (0.0, 5.5, 11.0, 16.5):
            p.box((x, y, CEIL - 0.03), (1.2, 0.3, 0.03))
    p.make('IN_LED', M['led'], None, coll=C)
    for k, y in enumerate(range(15, 84, 6)):
        for j, x in enumerate((2.0, 14.4)):
            _light('IN_Area_%d_%d' % (k, j), (x, y, CEIL - 0.25), (7, 4), 330, C)
    # floor drains along the line + wet sheen patches
    p = Part()
    for x in (2.0, 14.4):
        p.box((x, 48, DZ + 0.004), (0.22, 70, 0.01))
    p.make('IN_Drains', P.tex_mat('PL_Grate', 'metal_plate', scale=4.0, metal=1.0, tint=(0.5, 0.5, 0.5)), None, coll=C)


def _strip_curtain(name, x0, x1, y, z0, z1, C, M, n=None):
    """Individual PVC strips (origin at the top) so they can swing when a trolley passes."""
    n = n or int((x1 - x0) / 0.22)
    strips = []
    me = None
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        if me is None:
            p = Part()
            p.box((0, 0, -(z1 - z0) / 2), (0.3, 0.006, z1 - z0))
            o = p.make('%s_%02d' % (name, i), M['curtain'], None, coll=C)
            me = o.data
        else:
            o = bpy.data.objects.new('%s_%02d' % (name, i), me)
            C.objects.link(o)
        o.location = (x, y + (0.012 if i % 2 else -0.012), z1)
        strips.append(o)
    return strips


def swing_strips(strips, passes):
    """passes: [(frame_in, frame_out, x_centre, half_width, direction)] -> strips in range swing open and settle."""
    for o in strips:
        keyed = False
        for f_in, f_out, xc, hw, dirn in passes:
            if abs(o.location.x - xc) > hw:
                continue
            for f, a in ((f_in - 4, 0.0), (f_in + 4, 1.05), (f_out, 0.95), (f_out + 8, -0.25), (f_out + 16, 0.08),
                         (f_out + 24, 0.0)):
                o.rotation_euler = (a * dirn, 0, 0)
                o.keyframe_insert('rotation_euler', frame=f)
                keyed = True
        if not keyed:
            o.rotation_euler = (0, 0, 0)


def intake(C, M, crate_fn, trolley_fn):
    # boot dip tray + foot-operated sinks + hand dryers + platform scale + hose reels + crate stacks
    p = Part()
    p.box((CX + 5.6, 13.3, DZ + 0.05), (1.6, 1.2, 0.1))
    p.make('IN_BootDip', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    p.box((CX + 5.6, 13.3, DZ + 0.085), (1.4, 1.0, 0.01))
    p.make('IN_BootDipWater', M['water'], None, coll=C)
    p = Part()
    for k in range(4):
        y = 13.5 + k * 1.1
        p.box((XL + 0.45, y, DZ + 0.82), (0.55, 0.8, 0.22))
        p.box((XL + 0.25, y, DZ + 0.4), (0.12, 0.3, 0.8))
        p.box((XL + 0.4, y, DZ + 0.06), (0.25, 0.25, 0.06))
        p.cyl((XL + 0.2, y, DZ + 1.05), (XL + 0.45, y, DZ + 1.15), 0.015, 8)
    p.make('IN_Sinks', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    p.box((16.0, 18.5, DZ + 0.05), (1.2, 1.2, 0.1))
    p.box((16.0, 17.9, DZ + 0.6), (0.1, 0.1, 1.1))
    p.box((16.0, 17.9, DZ + 1.2), (0.4, 0.15, 0.3))
    p.make('IN_PlatformScale', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    for y in (19.0, 30.0, 42.0, 56.0):
        p.cyl((XR - 0.12, y, DZ + 1.6), (XR - 0.3, y, DZ + 1.6), 0.32, 24)
    p.make('IN_HoseReels', M['yellow'], None, coll=C)
    k = 0
    for (x, y) in ((17.5, 13.2), (18.2, 13.2), (17.5, 13.9), (-3.5, 18.5), (-2.8, 18.5)):
        for lv in range(5):
            crate_fn('IN_Stack%02d' % k, ['blue', 'white', 'blue', 'red'][(k + lv) % 4], (x, y, DZ + lv * 0.3), 0.0, None,
                     None, 400 + k)
            k += 1
    trolley_fn('IN_Trolley1', (16.4, 18.0, DZ), math.radians(80), C)
    trolley_fn('IN_Trolley2', (-1.5, 20.0, DZ), math.radians(95), C)


def wash(C, M, rnd, shrimp_fn):
    """Two wash tanks with spray bars, running water and product; inclined outfeed conveyor toward the grader."""
    for t, x in enumerate((CX - 2.6, CX + 2.6)):
        y = 15.6
        p = Part()
        bm = p.bm
        for (cx, cy, sx, sy, sz, cz) in ((0, 0, 3.2, 1.5, 0.06, 0.03), (0, 0.75, 3.2, 0.05, 0.95, 0.475),
                                          (0, -0.75, 3.2, 0.05, 0.95, 0.475), (1.6, 0, 0.05, 1.5, 0.95, 0.475),
                                          (-1.6, 0, 0.05, 1.5, 0.95, 0.475)):
            p.box((x + cx, y + cy, DZ + 0.15 + cz), (sx, sy, sz))
        for sx in (-1.45, 1.45):
            for sy in (-0.6, 0.6):
                p.box((x + sx, y + sy, DZ + 0.075), (0.06, 0.06, 0.15))
        p.box((x, y - 0.78, DZ + 1.12), (3.25, 0.1, 0.04))
        p.make('IN_Tank%d' % t, M['stainless'], None, bevel=0.008, coll=C)
        w = Part()
        w.box((x, y, DZ + 0.92), (3.1, 1.4, 0.02))
        wo = w.make('IN_TankWater%d' % t, M['water'], None, coll=C)
        # spray bar + falling water curtains
        p = Part()
        p.cyl((x - 1.5, y, DZ + 1.75), (x + 1.5, y, DZ + 1.75), 0.03, 10)
        for sy in (-0.7, 0.7):
            p.cyl((x - 1.5, y + sy * 0.0, DZ + 1.75), (x - 1.5, y + sy, DZ + 1.75), 0.02, 8)
        for k in range(9):
            p.cyl((x - 1.4 + k * 0.35, y, DZ + 1.75), (x - 1.4 + k * 0.35, y, DZ + 1.68), 0.012, 6)
        for sx in (-1.6, 1.6):
            p.cyl((x + sx, y + 0.75, DZ + 1.1), (x + sx, y + 0.75, DZ + 1.8), 0.025, 8)
        p.make('IN_SprayBar%d' % t, M['stainless'], None, coll=C)
        st = Part()
        sc = Part()
        for k in (1, 3, 5, 7):                                         # four nozzles run, the rest are off
            xx = x - 1.4 + k * 0.35
            st.cyl((xx, y, DZ + 1.68), (xx, y, DZ + 0.93), 0.022, 14, r2=0.03)
            for j in range(10):                                        # splash crown where the stream hits
                a = j * 0.628
                st.cyl((xx + 0.06 * math.cos(a), y + 0.06 * math.sin(a), DZ + 0.93),
                       (xx + 0.1 * math.cos(a), y + 0.1 * math.sin(a), DZ + 0.99 + 0.02 * (j % 2)), 0.006, 6)
            sc.cyl((xx, y, DZ + 0.931), (xx, y, DZ + 0.934), 0.16, 20)  # foam ring on the surface
        st.make('IN_Stream%d' % t, _stream_mat(), None, smooth=True, coll=C)
        dm = bpy.data.meshes.get('IN_DropMesh')
        if dm is None:                                               # droplets thrown off around each stream
            bmd = bmesh.new()
            bmesh.ops.create_icosphere(bmd, subdivisions=1, radius=0.006)
            dm = bpy.data.meshes.new('IN_DropMesh')
            bmd.to_mesh(dm)
            bmd.free()
            dm.materials.append(_stream_mat())
        for k in (1, 3, 5, 7):
            xx = x - 1.4 + k * 0.35
            for j in range(6):
                d = bpy.data.objects.new('IN_Drop%d_%d_%d' % (t, k, j), dm)
                C.objects.link(d)
                a = rnd.uniform(0, 6.28)
                r0 = rnd.uniform(0.03, 0.05)
                per = rnd.randint(9, 14)
                for f0 in range(1 + j * 2, 1100, per):               # spray out from the stream, fall to the water
                    for df, rr, zz in ((0, r0, rnd.uniform(1.0, 1.5)), (per - 1, r0 + 0.12, 0.93)):
                        d.location = (xx + rr * math.cos(a), y + rr * math.sin(a), DZ + zz)
                        d.keyframe_insert('location', frame=f0 + df)
        sc.make('IN_StreamFoam%d' % t, _foam_ring_mat(), None, coll=C)
        # product in the tank (under/at the surface)
        for k in range(60):
            shrimp_fn('IN_TankShrimp%d_%02d' % (t, k), (x + rnd.uniform(-1.4, 1.4), y + rnd.uniform(-0.6, 0.6),
                                                        DZ + 0.86 + rnd.uniform(-0.06, 0.04)),
                      (rnd.uniform(0, 6.28), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 6.28)))
        # perforated baskets on the tank rim
        p = Part()
        for k in range(2):
            p.box((x - 0.7 + k * 1.4, y - 0.95, DZ + 1.2), (0.55, 0.38, 0.22))
        p.make('IN_Baskets%d' % t, M['tray_blue'], None, bevel=0.01, coll=C)
    # inclined outfeed conveyor from between the tanks up to the grading line
    _conveyor('IN_Outfeed', (CX, 17.2, DZ + 0.6), (CX, 20.5, DZ + 0.95), 0.6, C, M)


_SPRAY = {}


def _brushed():
    return P.plain('IN_BrushedSteel', (0.66, 0.67, 0.68), 0.24, 1.0, bump=0.04, bump_scale=200, aniso=0.7)


def _stream_mat():
    """Clear running water: transmissive, glossy, a little rippled (animated by the spray map clock)."""
    m = bpy.data.materials.get('IN_StreamWater')
    if m:
        return m
    m = P.plain('IN_StreamWater', (0.92, 0.96, 0.98), 0.02, transmission=1.0, ior=1.33, bump=0.3, bump_scale=60)
    return m


def _foam_ring_mat():
    """White aerated water where a stream lands: soft-edged, opaque in the middle."""
    m = bpy.data.materials.get('IN_StreamFoam')
    if m:
        return m
    m = bpy.data.materials.new('IN_StreamFoam')
    m.use_nodes = True
    m.surface_render_method = 'BLENDED'
    nt = m.node_tree
    pb = nt.nodes['Principled BSDF']
    pb.inputs['Base Color'].default_value = (0.9, 0.93, 0.94, 1)
    pb.inputs['Roughness'].default_value = 0.4
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 40.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.4
    mr.inputs['From Max'].default_value = 0.65
    mr.inputs['To Max'].default_value = 0.85
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs[0], pb.inputs['Alpha'])
    return m


def _spray_mat():
    if 'm' in _SPRAY:
        return _SPRAY['m']
    m = bpy.data.materials.new('IN_SprayWater')
    m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.9, 0.95, 0.97, 1)
    p.inputs['Roughness'].default_value = 0.05
    p.inputs['Transmission Weight'].default_value = 0.6
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.name = 'SprayMap'
    mp.inputs['Scale'].default_value = (30, 30, 3)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Detail'].default_value = 4
    L.new(mp.outputs[0], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.5
    mr.inputs['From Max'].default_value = 0.7
    mr.inputs['To Max'].default_value = 0.7
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    L.new(mr.outputs[0], p.inputs['Alpha'])
    _SPRAY['m'] = m
    return m


def animate_spray(f0, f1):
    m = _SPRAY.get('m')
    if not m:
        return
    sock = m.node_tree.nodes['SprayMap'].inputs['Location']
    for f in (f0, f1):
        sock.default_value = (0, 0, (f - f0) / 24 * 4.0)
        sock.keyframe_insert('default_value', frame=f)
    import sktruck
    for fc in sktruck._fcurves(m.node_tree.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def _conveyor(name, a, b, width, C, M, legs=True):
    a, b = Vector(a), Vector(b)
    d = b - a
    Lg = d.length
    ang = math.atan2(d.z, d.y)
    mid = (a + b) / 2
    rot = Euler((ang, 0, 0))
    p = Part()
    for sx in (-1, 1):
        p.box(mid + Vector((sx * (width / 2 + 0.04), 0, 0)), (0.05, Lg, 0.16), rot)
    if legs:
        n = max(2, int(Lg / 2.0) + 1)
        for k in range(n):
            t = k / (n - 1)
            q = a.lerp(b, t)
            for sx in (-1, 1):
                p.box((q.x + sx * (width / 2 + 0.04), q.y, (DZ + q.z) / 2), (0.05, 0.05, q.z - DZ))
    p.make(name + '_Frame', M['stainless'], None, bevel=0.005, coll=C)
    p = Part()
    p.box(mid + Vector((0, 0, 0.06)), (width, Lg, 0.02), rot)
    belt = p.make(name + '_Belt', _mesh_belt() if 'IQF' in name else M['belt'], None, coll=C)
    return belt


def _mesh_belt():
    """IQF belt: dark stainless wire mesh (woven grid, dark gaps, glints on the wires)."""
    m = bpy.data.materials.get('IN_MeshBelt')
    if m:
        return m
    m = bpy.data.materials.new('IN_MeshBelt')
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    pb = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    bk = nt.nodes.new('ShaderNodeTexBrick')
    bk.inputs['Scale'].default_value = 60.0
    bk.inputs['Mortar Size'].default_value = 0.25
    bk.inputs['Color1'].default_value = (0.02, 0.022, 0.025, 1)
    bk.inputs['Color2'].default_value = (0.03, 0.032, 0.035, 1)
    bk.inputs['Mortar'].default_value = (0.42, 0.43, 0.44, 1)
    L.new(tc.outputs['Object'], bk.inputs['Vector'])
    L.new(bk.outputs['Color'], pb.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = 0.0
    mr.inputs['To Max'].default_value = 1.0
    L.new(bk.outputs['Fac'], mr.inputs['Value'])
    L.new(mr.outputs[0], pb.inputs['Metallic'])
    pb.inputs['Roughness'].default_value = 0.3
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.6
    L.new(bk.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs[0], pb.inputs['Normal'])
    return m


def grading(C, M, rnd, shrimp_fn):
    belt = _conveyor('IN_GradeBelt', (CX, 20.5, DZ + 0.95), (CX, 31.5, DZ + 0.95), 0.7, C, M)
    for k in range(360):                                   # product spread along the belt (and the outfeed)
        y = rnd.uniform(17.4, 31.2)
        z = DZ + 1.03 if y > 20.5 else DZ + 0.66 + (y - 17.2) / 3.3 * 0.35 + 0.08
        shrimp_fn('IN_BeltShrimp%03d' % k, (CX + rnd.uniform(-0.27, 0.27), y, z),
                  (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28)))
    # roller grader: hopper, inclined rollers in a frame, four chutes on each side into trays
    p = Part()
    p.box((CX, 26.5, DZ + 1.25), (1.4, 3.2, 0.08), Euler((0.06, 0, 0)))
    for sx in (-1, 1):
        p.box((CX + sx * 0.72, 26.5, DZ + 1.3), (0.05, 3.3, 0.5))
    for k in range(4):
        for sx in (-1, 1):
            p.box((CX + sx * 1.05, 25.4 + k * 0.75, DZ + 0.95), (0.6, 0.45, 0.04), Euler((0, sx * 0.5, 0)))
    for sx in (-0.7, 0.7):
        for sy in (25.0, 28.0):
            p.box((CX + sx, sy, DZ + 0.62), (0.08, 0.08, 1.24))
    p.box((CX, 24.8, DZ + 1.75), (1.2, 0.6, 0.5))
    p.make('IN_Grader', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    for k in range(14):
        p.cyl((CX - 0.68, 25.0 + k * 0.22, DZ + 1.32 + k * 0.012), (CX + 0.68, 25.0 + k * 0.22, DZ + 1.32 + k * 0.012), 0.045, 12)
    rollers = p.make('IN_GraderRollers', M['steel'], None, coll=C)
    p = Part()
    p.box((CX + 0.0, 24.75, DZ + 2.04), (0.6, 0.4, 0.12))
    p.make('IN_GraderMotor', P.plain('IN_MotorGrey', (0.35, 0.38, 0.4), 0.4, 0.4), None, bevel=0.02, coll=C)
    # trays under the chutes with graded product, and stacked trays
    for k in range(4):
        for sx in (-1, 1):
            tr = _tray('IN_GradeTray_%d_%d' % (k, sx > 0), (CX + sx * 1.45, 25.4 + k * 0.75, DZ + 0.7), C, M)
            for m in range(10):
                shrimp_fn('%s_S%02d' % (tr.name, m), (CX + sx * 1.45 + rnd.uniform(-0.18, 0.18),
                                                     25.4 + k * 0.75 + rnd.uniform(-0.12, 0.12), DZ + 0.74),
                          (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28)))
    p = Part()
    for sx in (-1, 1):
        x = CX + sx * 1.45
        p.box((x, 26.5, DZ + 0.66), (0.56, 3.2, 0.03))
        for yy in (25.0, 28.0):
            for dx in (-0.24, 0.24):
                p.box((x + dx, yy, DZ + 0.33), (0.035, 0.035, 0.66))
        p.box((x, 26.5, DZ + 0.15), (0.5, 3.0, 0.02))
    p.make('IN_TrayStands', M['stainless'], None, bevel=0.005, coll=C)
    return belt


def _tray(name, loc, C, M, blue=False):
    key = 'tray_mesh'
    if key not in _SPRAY:
        p = Part()
        bm = p.bm
        p.box((0, 0, 0.0), (0.5, 0.36, 0.012))
        for (cx, cy, sx, sy) in ((0, 0.18, 0.5, 0.012), (0, -0.18, 0.5, 0.012), (0.25, 0, 0.012, 0.36), (-0.25, 0, 0.012, 0.36)):
            p.box((cx, cy, 0.04), (sx, sy, 0.08))
        o = p.make(name, M['tray_white'], None, coll=C)
        _SPRAY[key] = o.data
    else:
        o = bpy.data.objects.new(name, _SPRAY[key])
        C.objects.link(o)
    o.location = loc
    if blue:
        o.material_slots[0].link = 'OBJECT'
        o.material_slots[0].material = M['tray_blue']
    return o


def processing(C, M, rnd, shrimp_fn, fish_fn, ice_mesh):
    """Four long stainless peeling tables (along +Y), one fish table, trays with product on ice."""
    tables = []
    for t, x in enumerate((CX - 6.4, CX - 3.2, CX + 3.2, CX + 6.4)):
        y0, y1 = 32.5, 43.5
        p = Part()
        p.box((x, (y0 + y1) / 2, DZ + 0.9), (1.0, y1 - y0, 0.04))
        for sx in (-0.52, 0.52):
            p.box((x + sx, (y0 + y1) / 2, DZ + 0.95), (0.03, y1 - y0, 0.08))
        for k in range(6):
            yy = y0 + 0.3 + k * (y1 - y0 - 0.6) / 5
            for sx in (-0.42, 0.42):
                p.box((x + sx, yy, DZ + 0.45), (0.04, 0.04, 0.9))
        p.box((x, (y0 + y1) / 2, DZ + 0.18), (0.9, y1 - y0 - 0.4, 0.02))
        p.make('IN_Table%d' % t, M['stainless'], None, bevel=0.006, coll=C)
        # centre gutter of crushed ice with product + work trays along both sides
        ice = bpy.data.objects.new('IN_TableIce%d' % t, ice_mesh)
        C.objects.link(ice)
        ice.location = (x, (y0 + y1) / 2, DZ + 0.92)
        ice.scale = (0.5 / 0.54, (y1 - y0) / 0.34 * 0.9, 1.2)
        for m in range(110):
            shrimp_fn('IN_TabShrimp%d_%03d' % (t, m), (x + rnd.uniform(-0.18, 0.18), rnd.uniform(y0 + 0.4, y1 - 0.4),
                                                       DZ + 0.97 + rnd.uniform(0, 0.03)),
                      (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.28)))
        for k in range(8):
            for sx in (-1, 1):
                tr = _tray('IN_WorkTray_%d_%d_%d' % (t, k, sx > 0), (x + sx * 0.3, y0 + 0.9 + k * 1.2, DZ + 0.92), C, M,
                           blue=(k + t) % 3 == 0)
                tr.scale = (0.7, 0.8, 1)
                for m in range(5):
                    shrimp_fn('%s_S%d' % (tr.name, m), (x + sx * 0.3 + rnd.uniform(-0.1, 0.1),
                                                       y0 + 0.9 + k * 1.2 + rnd.uniform(-0.08, 0.08), DZ + 0.95),
                              (rnd.uniform(-0.3, 0.3), 0, rnd.uniform(0, 6.28)))
        tables.append((x, y0, y1))
    # fish table (cleaning fish) at the right wall
    x = XR - 1.6
    p = Part()
    p.box((x, 38.0, DZ + 0.9), (1.2, 8.0, 0.04))
    for k in range(4):
        for sx in (-0.5, 0.5):
            p.box((x + sx, 34.5 + k * 2.3, DZ + 0.45), (0.04, 0.04, 0.9))
    p.box((x + 0.62, 38.0, DZ + 0.95), (0.03, 8.0, 0.1))
    p.make('IN_FishTable', M['stainless'], None, bevel=0.006, coll=C)
    ice = bpy.data.objects.new('IN_FishIce', ice_mesh)
    C.objects.link(ice)
    ice.location = (x, 38.0, DZ + 0.92)
    ice.scale = (1.9, 21.0, 1.2)
    for m in range(14):
        fish_fn('IN_Fish%02d' % m, rnd.choice(['tuna_s', 'mackerel', 'seer', 'mackerel']),
                (x + rnd.uniform(-0.25, 0.25), 34.7 + m * 0.48, DZ + 0.99),
                (math.radians(90), 0, math.radians(rnd.uniform(-20, 20))))
    # crates of iced product beside the tables, sinks, a scale on a stand
    return tables


def lab(C, M, rnd, shrimp_fn):
    """Glazed lab partition across the hall at y 54 with a door at CX; bench, scale, sample trays, cabinet, fridge."""
    y = 45.0
    p = Part()
    p.box(((XL + CX - 1.0) / 2, y, DZ + 0.5), (CX - 1.0 - XL, 0.12, 1.0))
    p.box(((CX + 1.0 + XR) / 2, y, DZ + 0.5), (XR - CX - 1.0, 0.12, 1.0))
    p.box(((XL + XR) / 2, y, CEIL - 0.6), (XR - XL, 0.12, 1.2))
    for x in [XL + 0.1 + i * 1.8 for i in range(16)]:
        if abs(x - CX) < 1.1:
            continue
        p.box((x, y, (DZ + CEIL) / 2), (0.06, 0.14, CEIL - DZ))
    for sx in (-1, 1):
        p.box((CX + sx * 1.0, y, (DZ + CEIL) / 2), (0.08, 0.16, CEIL - DZ))
    p.make('IN_LabFrame', M['stainless'], None, bevel=0.005, coll=C)
    p = Part()
    p.box(((XL + CX - 1.0) / 2, y, (DZ + 1.0 + CEIL - 1.2) / 2), (CX - 1.0 - XL, 0.02, CEIL - DZ - 2.2))
    p.box(((CX + 1.0 + XR) / 2, y, (DZ + 1.0 + CEIL - 1.2) / 2), (XR - CX - 1.0, 0.02, CEIL - DZ - 2.2))
    p.make('IN_LabGlass', M['glass_clear'], None, coll=C)
    # lab back wall (to the freezing area) with a wide opening at CX
    yb = 51.2
    p = Part()
    p.box(((XL + CX - 1.4) / 2, yb, (DZ + CEIL) / 2), (CX - 1.4 - XL, 0.14, CEIL - DZ))
    p.box(((CX + 1.4 + XR) / 2, yb, (DZ + CEIL) / 2), (XR - CX - 1.4, 0.14, CEIL - DZ))
    p.box((CX, yb, (DZ + 3.0 + CEIL) / 2), (2.8, 0.14, CEIL - DZ - 3.0))
    p.make('IN_LabBackWall', M['panel_in'], None, coll=C)
    # benches along both sides, instruments
    p = Part()
    for x0, x1 in ((XL + 0.4, CX - 2.0), (CX + 2.0, XR - 0.4)):
        p.box(((x0 + x1) / 2, 47.0, DZ + 0.9), (x1 - x0, 0.75, 0.04))
        p.box(((x0 + x1) / 2, 47.0, DZ + 0.45), (x1 - x0, 0.7, 0.85))
        p.box(((x0 + x1) / 2, 50.4, DZ + 0.9), (x1 - x0, 0.75, 0.04))
        p.box(((x0 + x1) / 2, 50.4, DZ + 0.45), (x1 - x0, 0.7, 0.85))
    p.make('IN_LabBenches', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    p.box((CX + 3.2, 47.0, DZ + 0.98), (0.35, 0.3, 0.12))           # balance
    p.box((CX + 3.2, 46.95, DZ + 1.12), (0.25, 0.2, 0.16))
    p.box((XR - 1.5, 50.4, DZ + 1.6), (1.4, 0.7, 1.4))              # fume cabinet (generic)
    p.box((XL + 1.0, 50.5, DZ + 1.0), (0.8, 0.7, 2.0))               # fridge
    p.box((CX - 3.5, 47.0, DZ + 1.05), (0.5, 0.4, 0.3))              # analyser box
    p.make('IN_LabKit', P.plain('IN_LabKitGrey', (0.78, 0.8, 0.82), 0.3, 0.2), None, bevel=0.015, coll=C)
    p = Part()
    p.box((XR - 1.5, 50.05, DZ + 1.6), (1.2, 0.02, 0.9))
    p.make('IN_LabCabGlass', M['glass'], None, coll=C)
    for k in range(5):
        tr = _tray('IN_LabTray%d' % k, (CX + 1.6 + k * 0.6, 46.95, DZ + 0.93), C, M)
        tr.scale = (0.8, 0.8, 1)
        for m in range(12):                                          # a full sample: two rows of six
            shrimp_fn('%s_S%d' % (tr.name, m), (CX + 1.6 + k * 0.6 - 0.13 + (m % 6) * 0.052 + rnd.uniform(-0.01, 0.01),
                                               46.95 + (-0.05 if m < 6 else 0.05) + rnd.uniform(-0.01, 0.01),
                                               DZ + 0.96 + (m % 3) * 0.004), (0, 0, (0 if m < 6 else 3.14) + rnd.uniform(-0.3, 0.3)))
    # QC kit: probe thermometers in the trays, more balances, sample bags, glassware, reagent shelves, microscope, sink
    kit = Part()
    dark = Part()
    for k in (0, 1, 3):                                              # probe thermometers: body + steel probe
        x = CX + 1.6 + k * 0.6 + 0.16
        kit.box((x, 46.8, DZ + 0.99), (0.05, 0.11, 0.025))
        dark.cyl((x, 46.86, DZ + 0.985), (x - 0.06, 46.98, DZ + 0.955), 0.002, 6)
    for x in (CX - 4.4, XR - 3.2):                                   # two more balances with draft shields
        kit.box((x, 47.0, DZ + 0.98), (0.34, 0.3, 0.1))
        kit.box((x, 46.97, DZ + 1.12), (0.22, 0.2, 0.17))
    # microscope
    mx = CX - 5.6
    kit.box((mx, 47.05, DZ + 0.95), (0.22, 0.26, 0.05))
    kit.cyl((mx, 47.15, DZ + 0.95), (mx, 47.15, DZ + 1.3), 0.03, 10)
    kit.cyl((mx, 47.15, DZ + 1.28), (mx, 47.0, DZ + 1.22), 0.025, 10)
    kit.cyl((mx, 47.0, DZ + 1.22), (mx, 46.98, DZ + 1.06), 0.018, 10)
    for k in range(3):                                               # wall shelves over the back bench
        kit.box(((XL + CX - 2.0) / 2, 50.7, DZ + 1.55 + k * 0.38), (CX - 2.0 - XL - 0.6, 0.28, 0.025))
    kit.box((CX + 5.6, 50.4, DZ + 0.92), (0.6, 0.45, 0.04))           # sink rim
    kit.cyl((CX + 5.6, 50.62, DZ + 0.94), (CX + 5.6, 50.62, DZ + 1.25), 0.012, 8)
    kit.make('IN_LabKit2', P.plain('IN_LabKitWhite', (0.7, 0.72, 0.74), 0.3, 0.3), None, bevel=0.006, coll=C)
    dark.box((CX + 5.6, 50.4, DZ + 0.9), (0.52, 0.38, 0.04))
    for k in (0, 1, 3):
        dark.box((CX + 1.6 + k * 0.6 + 0.16, 46.745, DZ + 0.995), (0.03, 0.002, 0.012))
    dark.make('IN_LabSteel', M['steel'], None, coll=C)
    bags = Part()
    for k in range(7):                                               # sealed sample bags in a row
        x = CX + 4.5 + k * 0.16
        bags.box((x, 46.85 + rnd.uniform(-0.04, 0.04), DZ + 0.935), (0.13, 0.19, 0.022))
    bags.make('IN_SampleBags', P.plain('IN_SampleBag', (0.8, 0.78, 0.76), 0.35, coat=0.6), None, bevel=0.01, coll=C)
    lab_ = Part()
    for k in range(7):
        lab_.box((CX + 4.5 + k * 0.16, 46.83, DZ + 0.948), (0.07, 0.05, 0.003))
    lab_.make('IN_SampleBagLabels', M['label'], None, coll=C)
    btl = Part()
    for k in range(3):
        for j in range(14):
            x = XL + 0.8 + j * 0.42 + rnd.uniform(-0.05, 0.05)
            hgt = rnd.choice((0.16, 0.2, 0.24))
            btl.cyl((x, 50.7, DZ + 1.565 + k * 0.38), (x, 50.7, DZ + 1.565 + k * 0.38 + hgt), rnd.choice((0.035, 0.045)), 12)
    btl.make('IN_ReagentBottles', P.plain('IN_BottleAmber', (0.32, 0.15, 0.04), 0.15, coat=0.8), None, coll=C)
    gl = Part()
    for k in range(5):
        gl.cyl((CX - 1.0 - k * 0.14 - 2.2, 47.15, DZ + 0.92), (CX - 1.0 - k * 0.14 - 2.2, 47.15, DZ + 1.05), 0.03, 14,
               cap=False)
    gl.make('IN_Beakers', M['glass_clear'], None, coll=C)
    p = Part()
    p.box((CX - 2.6, 47.0, DZ + 0.93), (0.25, 0.33, 0.012))           # blank clipboard
    p.make('IN_Clipboard', M['label'], None, coll=C)


def _glaze_mat():
    """Frozen, glazed prawn: pale grey-pink flesh under a frosted ice glaze (clear coat, frost speckle, a little SSS)."""
    m = bpy.data.materials.get('IN_GlazedPrawn')
    if m:
        return m
    m = bpy.data.materials.new('IN_GlazedPrawn')
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    pb = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 140.0
    nz.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    seg = nt.nodes.new('ShaderNodeTexWave')                      # shell segments along the body
    seg.inputs['Scale'].default_value = 9.0
    L.new(tc.outputs['Object'], seg.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.74, 0.64, 0.6, 1)
    cr.color_ramp.elements[1].color = (0.9, 0.84, 0.8, 1)
    L.new(seg.outputs['Fac'], cr.inputs[0])
    fr = nt.nodes.new('ShaderNodeMix')
    fr.data_type = 'RGBA'
    fm = nt.nodes.new('ShaderNodeMapRange')
    fm.inputs['From Min'].default_value = 0.55
    fm.inputs['From Max'].default_value = 0.75
    fm.inputs['To Max'].default_value = 0.65
    L.new(nz.outputs['Fac'], fm.inputs['Value'])
    L.new(fm.outputs[0], fr.inputs[0])
    L.new(cr.outputs[0], fr.inputs[6])
    fr.inputs[7].default_value = (0.9, 0.93, 0.95, 1)            # frost
    L.new(fr.outputs[2], pb.inputs['Base Color'])
    L.new(fm.outputs[0], pb.inputs['Roughness'])
    pb.inputs['Coat Weight'].default_value = 1.0                 # the ice glaze
    pb.inputs['Coat Roughness'].default_value = 0.06
    pb.inputs['Subsurface Weight'].default_value = 0.15
    pb.inputs['Transmission Weight'].default_value = 0.25    # translucent ice glaze
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.25
    L.new(nz.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs[0], pb.inputs['Normal'])
    return m


def freezing(C, M, rnd, shrimp_fn):
    """Plate freezer (left), IQF tunnel + glazing spray on a belt (right), trolleys of trays. Frost only on edges."""
    # plate freezer: big stainless cabinet with a stack of plates visible through an open bay, hydraulic rams on top
    x, y = CX - 4.5, 54.6
    p = Part()
    p.box((x, y, DZ + 1.3), (2.6, 2.2, 2.6))
    p.make('IN_PlateFreezer', M['stainless'], None, bevel=0.02, coll=C)
    p = Part()
    for k in range(8):
        p.box((x + 1.32, y, DZ + 0.4 + k * 0.26), (0.02, 1.8, 0.05))
    for sx in (-0.6, 0.6):
        p.cyl((x + sx, y, DZ + 2.6), (x + sx, y, DZ + 3.3), 0.09, 14)
    p.make('IN_Plates', M['steel'], None, coll=C)
    p = Part()                                                         # thin frost on the plate edges only
    for k in range(8):
        p.box((x + 1.335, y, DZ + 0.425 + k * 0.26), (0.006, 1.8, 0.012))
    p.make('IN_PlateFrost', M['frost'], None, coll=C)
    # IQF tunnel: long insulated stainless enclosure the belt runs through (open mouth at each end, strip curtain,
    # frost on the lips, cold vapour rolling out), inspection doors, evaporator housings on top, control cabinet
    tx = CX + 3.6
    y0, y1 = 52.0, 55.6                                                # tunnel body: behind the lab wall (51.2)
    ym = (y0 + y1) / 2
    p = Part()
    p.box((tx, ym, DZ + 2.0), (2.4, y1 - y0, 1.6))                    # roof block over the belt
    for sx in (-1, 1):
        p.box((tx + sx * 0.88, ym, DZ + 0.75), (0.64, y1 - y0, 1.1))  # side walls, belt path open between
    p.make('IN_IQFTunnel', _brushed(), None, bevel=0.03, coll=C)
    p = Part()                                                        # panel seams + door frames + handles
    for k in range(1, 6):
        yy = y0 + k * (y1 - y0) / 6
        for sx in (-1, 1):
            p.box((tx + sx * 1.205, yy, DZ + 1.4), (0.012, 0.03, 2.4))
    for sx in (-1, 1):
        for yy in (y0 + 1.4, y0 + 3.8):
            p.box((tx + sx * 1.21, yy, DZ + 1.35), (0.02, 1.1, 1.6))    # inspection door leaf
            p.box((tx + sx * 1.245, yy + 0.42, DZ + 1.35), (0.05, 0.05, 0.4))   # lever handle
    for yy in (y0 + 1.2, y0 + 2.8, y0 + 4.4):
        p.box((tx, yy, DZ + 3.05), (1.6, 1.1, 0.5))                     # evaporator fan housings
        p.cyl((tx, yy, DZ + 3.3), (tx, yy, DZ + 3.34), 0.4, 20)
    p.make('IN_IQFDetail', M['steel'], None, bevel=0.005, coll=C)
    p = Part()                                                        # insulated refrigerant lines to the roof
    for k, dx in enumerate((-0.5, -0.3)):
        p.cyl((tx + dx, y1 - 0.4, DZ + 3.3), (tx + dx, y1 - 0.4, CEIL - 0.1), 0.06, 12)
    p.make('IN_IQFLines', P.plain('IN_Armaflex', (0.05, 0.05, 0.055), 0.7), None, coll=C)
    p = Part()                                                        # control cabinet + indicator lamps
    p.box((tx + 1.75, y0 + 0.6, DZ + 0.9), (0.5, 0.8, 1.8))
    p.make('IN_IQFPanel', P.grime_paint('IN_PanelGrey', (0.55, 0.58, 0.6), rough=0.4, grime=0.2, streak=0.1), None,
           bevel=0.01, coll=C)
    p = Part()
    for k, col in enumerate(((0.1, 1.0, 0.2), (1.0, 0.6, 0.05), (1.0, 0.1, 0.05))):
        p.cyl((tx + 1.5, y0 + 0.4 + k * 0.12, DZ + 1.5), (tx + 1.49, y0 + 0.4 + k * 0.12, DZ + 1.5), 0.025, 10)
    p.make('IN_IQFLamps', P.plain('IN_LampGreen', (0.1, 0.9, 0.2), 0.2, emission=(0.2, 1.0, 0.3), estr=4.0), None,
           coll=C)
    for yy in (y0 - 0.03, y1 + 0.03):                                 # frost on the mouth lips + strip curtain
        p = Part()
        p.box((tx, yy, DZ + 1.21), (1.2, 0.08, 0.04))
        for sx in (-1, 1):
            p.box((tx + sx * 0.57, yy, DZ + 0.98), (0.04, 0.08, 0.5))
        p.make('IN_IQFMouthFrost%d' % (yy > ym), M['frost'], None, bevel=0.01, coll=C)
        _strip_curtain('IN_IQFStrip%d' % (yy > ym), tx - 0.55, tx + 0.55, yy, DZ + 0.95, DZ + 1.2, C, M, n=8)
    vap = bpy.data.materials.get('IN_ColdVapour')
    if not vap:
        vap = bpy.data.materials.new('IN_ColdVapour')
        vap.use_nodes = True
        vap.surface_render_method = 'BLENDED'         # soft, not dithered grain
        nt = vap.node_tree
        pb = nt.nodes['Principled BSDF']
        pb.inputs['Base Color'].default_value = (0.92, 0.95, 0.97, 1)
        pb.inputs['Roughness'].default_value = 1.0
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 1.6
        nz.inputs['Detail'].default_value = 2
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nt.links.new(tc.outputs['Generated'], nz.inputs['Vector'])
        gr = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Generated'], gr.inputs[0])
        fz = nt.nodes.new('ShaderNodeMapRange')                       # thins out upward
        fz.inputs['To Min'].default_value = 0.35
        fz.inputs['To Max'].default_value = 0.0
        nt.links.new(gr.outputs['Z'], fz.inputs['Value'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.3
        mr.inputs['From Max'].default_value = 0.8
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        nt.links.new(mr.outputs[0], mul.inputs[0])
        nt.links.new(fz.outputs[0], mul.inputs[1])
        nt.links.new(mul.outputs[0], pb.inputs['Alpha'])
    for k, yy in enumerate((y0 - 0.35, y1 + 0.35)):                   # vapour rolling out of each mouth
        for j in range(3):
            p = Part()
            p.box((tx + (j - 1) * 0.25, yy + (j - 1) * 0.12, DZ + 1.02), (1.3, 0.02, 0.45))
            p.make('IN_IQFVapour%d_%d' % (k, j), vap, None, coll=C)
    belt = _conveyor('IN_IQFBelt', (tx, 51.6, DZ + 0.9), (tx, 59.6, DZ + 0.9), 0.9, C, M)
    # glazing hood: brushed stainless box on legs over the belt, seams, bolts, nozzle manifold, drip lips, frost
    hy = 56.6
    p = Part()
    p.box((tx, hy, DZ + 1.62), (1.3, 1.2, 0.56))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((tx + sx * 0.62, hy + sy * 0.55, DZ + 0.68), (0.06, 0.06, 1.36))     # legs
    p.make('IN_GlazeHood', _brushed(), None, bevel=0.012, coll=C)
    p = Part()
    for sy in (-0.3, 0.0, 0.3):
        p.box((tx, hy + sy, DZ + 1.905), (1.31, 0.01, 0.012))                         # roof seams
    for sx in (-1, 1):
        for k in range(6):
            p.cyl((tx + sx * 0.656, hy - 0.5 + k * 0.2, DZ + 1.82), (tx + sx * 0.666, hy - 0.5 + k * 0.2, DZ + 1.82),
                  0.011, 8)                                                            # bolt heads
        p.box((tx + sx * 0.66, hy, DZ + 1.335), (0.04, 1.22, 0.02))                   # drip lips
    p.cyl((tx - 0.6, hy, DZ + 1.3), (tx + 0.6, hy, DZ + 1.3), 0.025, 12)              # nozzle manifold
    for k in range(7):
        p.cyl((tx - 0.48 + k * 0.16, hy, DZ + 1.3), (tx - 0.48 + k * 0.16, hy, DZ + 1.24), 0.01, 6)
    p.cyl((tx + 0.6, hy, DZ + 1.3), (tx + 0.6, hy, DZ + 2.4), 0.025, 12)              # feed line up to the roof
    p.make('IN_GlazeHoodDetail', M['steel'], None, bevel=0.002, coll=C)
    p = Part()
    p.box((tx, hy - 0.605, DZ + 1.66), (0.5, 0.01, 0.22))                             # inspection window
    p.make('IN_GlazeWindow', M['glass_clear'], None, coll=C)
    p = Part()
    for sx in (-1, 1):
        p.box((tx + sx * 0.655, hy, DZ + 1.35), (0.012, 1.22, 0.03))
    p.box((tx, hy - 0.6, DZ + 1.35), (1.3, 0.012, 0.03))
    p.make('IN_GlazeFrost', M['frost'], None, bevel=0.004, coll=C)
    # glazing mist: soft vapour sheets under the nozzles (no thin spray lines)
    vap = bpy.data.materials.get('IN_ColdVapour')
    for k in range(4):
        p = Part()
        p.box((tx + (k - 1.5) * 0.04, hy + (k - 1.5) * 0.09, DZ + 1.1), (1.15, 0.02, 0.36))
        p.make('IN_GlazeMist%d' % k, vap, None, coll=C)
    # glazed, frosted prawns packed on the belt after the hood (IQF: single layer, close together)
    glazed = _glaze_mat()
    k = 0
    for row in range(16):
        yy = hy + 0.7 + row * 0.19
        if yy > 59.5:
            break
        for col in range(8):
            o = shrimp_fn('IN_IQF%03d' % k, (tx - 0.38 + col * 0.108 + rnd.uniform(-0.008, 0.008), yy,
                                           DZ + 0.975), (0, 0, (1.5708 if row % 2 else -1.5708) + rnd.uniform(-0.12, 0.12)))
            for sl in o.material_slots:
                sl.link = 'OBJECT'
                sl.material = glazed
            k += 1
    # trolleys of trays (tray racks)
    for k, (xx, yy) in enumerate(((CX - 1.2, 52.8), (CX - 2.0, 56.8), (XL + 1.3, 55.8))):
        p = Part()
        for sx in (-0.4, 0.4):
            for sy in (-0.3, 0.3):
                p.box((xx + sx, yy + sy, DZ + 0.95), (0.03, 0.03, 1.8))
        for lv in range(9):
            p.box((xx, yy, DZ + 0.25 + lv * 0.18), (0.82, 0.62, 0.012))
        p.make('IN_TrayRack%d' % k, M['stainless'], None, coll=C)
        p = Part()
        for lv in range(9):
            p.box((xx, yy, DZ + 0.27 + lv * 0.18), (0.74, 0.54, 0.04))
        p.make('IN_TrayRackBlocks%d' % k, M['block'], None, bevel=0.005, coll=C)
    # dividing wall to packing at y 69 (opening at CX)
    p = Part()
    p.box(((XL + CX - 1.6) / 2, 59.9, (DZ + CEIL) / 2), (CX - 1.6 - XL, 0.14, CEIL - DZ))
    p.box(((CX + 5.4 + XR) / 2, 59.9, (DZ + CEIL) / 2), (XR - CX - 5.4, 0.14, CEIL - DZ))
    p.box(((CX - 1.6 + CX + 5.4) / 2, 59.9, (DZ + 3.2 + CEIL) / 2), (7.0, 0.14, CEIL - DZ - 3.2))
    p.make('IN_FreezeWall', M['panel_in'], None, coll=C)


def packing(C, M, rnd):
    """Packing tables with cartons (blank labels: lines only), tape, strapping machine, vacuum packer, carton stacks."""
    carton = M['carton']
    for t, x in enumerate((CX - 3.0, CX + 2.4)):
        p = Part()
        p.box((x, 62.3, DZ + 0.88), (1.2, 3.8, 0.04))
        for sx in (-0.55, 0.55):
            for sy in (60.6, 64.0):
                p.box((x + sx, sy, DZ + 0.44), (0.04, 0.04, 0.88))
        p.make('IN_PackTable%d' % t, M['stainless'], None, bevel=0.005, coll=C)
        p = Part()
        q = Part()
        r = Part()
        for k in range(5):
            yy = 60.8 + k * 0.75
            p.box((x, yy, DZ + 1.05), (0.55, 0.38, 0.3))
            q.box((x - 0.276, yy, DZ + 1.08), (0.004, 0.2, 0.12))
            for ln in range(3):
                r.box((x - 0.279, yy, DZ + 1.11 - ln * 0.03), (0.002, 0.16, 0.006))
        p.make('IN_PackCartons%d' % t, carton, None, bevel=0.008, coll=C)
        q.make('IN_PackLabels%d' % t, M['label'], None, coll=C)
        r.make('IN_PackLabelLines%d' % t, M['label_line'], None, coll=C)
    p = Part()
    p.box((CX + 5.5, 62.6, DZ + 0.75), (1.0, 1.4, 1.5))               # strapping machine
    p.box((CX + 5.5, 62.6, DZ + 1.6), (1.1, 0.1, 0.25))
    p.box((CX - 6.0, 61.8, DZ + 0.55), (1.6, 0.9, 1.1))               # vacuum packer
    p.box((CX - 6.0, 61.8, DZ + 1.2), (1.5, 0.85, 0.2))
    p.make('IN_PackMachines', P.plain('IN_MachineGrey', (0.62, 0.65, 0.67), 0.35, 0.3), None, bevel=0.02, coll=C)
    p = Part()
    for k in range(4):
        p.box((CX - 6.4 + k * 0.28, 61.8, DZ + 1.32), (0.24, 0.6, 0.04))
    p.make('IN_VacPacks', M['vacbag'], None, bevel=0.01, coll=C)
    # carton stacks on pallets
    for k, (xx, yy) in enumerate(((XL + 1.4, 61.0), (XL + 1.4, 62.5), (XR - 1.4, 61.0), (XR - 1.4, 62.6))):
        S.pallet('IN_PackPallet%d' % k, (xx, yy, DZ), M, C, 0.0, cartons=4)


def cold_store(C, M, rnd):
    """Insulated door with strip curtain at y 77, racks both sides of the aisle, wrapped pallets, light frost."""
    y0 = 65.0
    p = Part()
    p.box(((XL + CX - 1.8) / 2, y0, (DZ + CEIL) / 2), (CX - 1.8 - XL, 0.3, CEIL - DZ))
    p.box(((CX + 1.8 + XR) / 2, y0, (DZ + CEIL) / 2), (XR - CX - 1.8, 0.3, CEIL - DZ))
    p.box((CX, y0, (DZ + 3.6 + CEIL) / 2), (3.6, 0.3, CEIL - DZ - 3.6))
    p.make('IN_ColdWall', M['panel_in'], None, coll=C)
    p = Part()
    p.box((CX - 3.4, y0 - 0.2, DZ + 1.8), (3.4, 0.12, 3.6))          # sliding insulated door (open, parked left)
    p.make('IN_ColdDoor', M['panel_in'], None, bevel=0.03, coll=C)
    p = Part()
    p.box((CX, y0 - 0.25, DZ + 3.72), (5.8, 0.15, 0.15))
    p.make('IN_ColdDoorRail', M['stainless'], None, coll=C)
    strips = _strip_curtain('IN_ColdStrip', CX - 1.75, CX + 1.75, y0 + 0.18, DZ, DZ + 3.55, C, M)
    # racks: uprights + beams (orange beams, blue uprights), five levels, both sides
    up = Part()
    bm_ = Part()
    fr = Part()
    for side, xr in ((-1, CX - 2.6), (1, CX + 2.6)):
        for k in range(8):
            yy = 66.5 + k * 2.4
            for dx in (0.0, side * 1.2):
                up.box((xr + dx, yy, DZ + 2.5), (0.09, 0.09, 5.0))
        for lv in range(5):
            z = DZ + 0.2 + lv * 0.98
            for dx in (0.0, side * 1.2):
                bm_.box((xr + dx, 66.5 + 8.4, z), (0.06, 16.8, 0.12))
                fr.box((xr + dx, 66.5 + 8.4, z + 0.065), (0.07, 16.8, 0.008))
    up.make('IN_RackUprights', M['rack_blue'], None, coll=C)
    bm_.make('IN_RackBeams', M['rack_orange'], None, coll=C)
    fr.make('IN_RackFrost', M['frost'], None, coll=C)
    # wrapped pallets of cartons on every level
    cart = Part()
    wrap = Part()
    wood = Part()
    for side, xr in ((-1, CX - 2.6), (1, CX + 2.6)):
        for k in range(7):
            yy = 67.7 + k * 2.4
            for lv in range(5):
                if rnd.random() < 0.1:
                    continue
                z = DZ + 0.26 + lv * 0.98
                xc = xr + side * 0.6
                wood.box((xc, yy, z + 0.07), (1.0, 1.2, 0.14))
                h = rnd.choice((0.55, 0.65, 0.7, 0.75))
                cart.box((xc, yy, z + 0.14 + h / 2), (0.98, 1.16, h))
                wrap.box((xc, yy, z + 0.14 + h / 2), (1.0, 1.18, h + 0.02))
    wood.make('IN_ColdPalletWood', M['wood'], None, coll=C)
    cart.make('IN_ColdCartons', P.plain('IN_CartonKraft', (0.5, 0.38, 0.24), 0.7, bump=0.15, bump_scale=20), None,
              bevel=0.01, coll=C)
    wrap.make('IN_ColdWrap', P.plain('IN_StretchWrapCold', (0.82, 0.85, 0.88), 0.15, alpha=0.25, coat=0.8, bump=0.25,
                                      bump_scale=6), None, coll=C)
    lab_ = Part()
    lab2 = Part()
    for side, xr in ((-1, CX - 2.6), (1, CX + 2.6)):                 # coloured product labels on the carton faces
        for k in range(7):
            yy = 67.7 + k * 2.4
            for lv in range(5):
                z = DZ + 0.26 + lv * 0.98
                xf = xr + side * 0.6 - side * 0.5
                (lab_ if (k + lv) % 2 else lab2).box((xf - side * 0.012, yy + rnd.uniform(-0.3, 0.3), z + 0.42),
                                                     (0.004, 0.2, 0.14))
    lab_.make('IN_ColdLabelsBlue', P.plain('IN_LabelBlueBand', (0.08, 0.2, 0.45), 0.5), None, coll=C)
    lab2.make('IN_ColdLabelsOrange', P.plain('IN_LabelOrangeBand', (0.75, 0.35, 0.06), 0.5), None, coll=C)
    st = Part()
    stw = Part()
    for k, (xx, yy) in enumerate(((CX - 0.8, 66.6), (CX + 0.9, 67.4), (CX - 0.7, 69.4))):   # staged in the aisle
        stw.box((xx, yy, DZ + 0.07), (1.0, 1.2, 0.14))
        st.box((xx, yy, DZ + 0.14 + 0.6), (0.98, 1.16, 1.2))
    stw.make('IN_ColdStagedWood', M['wood'], None, coll=C)
    st.make('IN_ColdStaged', bpy.data.materials['IN_CartonKraft'], None, bevel=0.01, coll=C)
    # cold store lights: cooler and a touch dimmer
    for k in range(4):
        _light('IN_ColdArea%d' % k, (CX, 68 + k * 4.2, CEIL - 0.3), (3, 3), 260, C, color=(0.88, 0.94, 1.0))
    p = Part()
    p.box((CX, 74.5, DZ + 0.002), (2.0, 17, 0.003))
    p.make('IN_ColdAisleFrost', P.plain('IN_FloorFrost', (0.8, 0.84, 0.87), 0.5, alpha=0.18), None, coll=C)
    return strips


def _wet_floor():
    """Food-grade epoxy, darker and greener, with wet patches (glossy) and dry scuffed areas (matte)."""
    m = bpy.data.materials.get('PL_Epoxy')
    if m is None or m.get('wet'):
        return
    nt = m.node_tree
    L = nt.links
    pb = nt.nodes['Principled BSDF']
    for l in list(pb.inputs['Base Color'].links) + list(pb.inputs['Roughness'].links):
        nt.links.remove(l)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.18
    nz.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    wet = nt.nodes.new('ShaderNodeMapRange')
    wet.inputs['From Min'].default_value = 0.57
    wet.inputs['From Max'].default_value = 0.63
    L.new(nz.outputs['Fac'], wet.inputs['Value'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value = 0.58   # dry epoxy is satin, not a mirror
    rr.inputs['To Max'].default_value = 0.1
    L.new(wet.outputs[0], rr.inputs['Value'])
    L.new(rr.outputs[0], pb.inputs['Roughness'])
    cm = nt.nodes.new('ShaderNodeMix')
    cm.data_type = 'RGBA'
    cm.inputs[6].default_value = (0.3, 0.35, 0.33, 1)
    cm.inputs[7].default_value = (0.2, 0.24, 0.23, 1)
    L.new(wet.outputs[0], cm.inputs[0])
    L.new(cm.outputs[2], pb.inputs['Base Color'])
    m['wet'] = True


def _services(C, M):
    """Overhead galvanised ducts, coloured service pipes on brackets, cable trays; PVC dado band on the walls."""
    galv = M['galv']
    p = Part()
    for x in (4.0, 12.8):
        p.cyl((x, 13.0, CEIL - 0.7), (x, Y_END - 1.0, CEIL - 0.7), 0.32, 24)       # supply ducts
        for y in range(14, int(Y_END) - 1, 6):
            p.cyl((x, y, CEIL - 0.7), (x, y + 0.08, CEIL - 0.7), 0.335, 24)       # duct joints
            p.box((x, y + 1.0, CEIL - 0.35), (0.04, 0.04, 0.7))                  # hangers
            p.cyl((x, y + 3.0, CEIL - 1.02), (x, y + 3.0, CEIL - 1.1), 0.18, 16)  # diffusers
    for y in range(14, int(Y_END) - 1, 4):
        p.box((XR - 0.5, y, CEIL - 0.9), (0.6, 0.04, 0.04))                     # pipe brackets on the wall
        p.box((XL + 0.5, y, CEIL - 0.9), (0.6, 0.04, 0.04))
    p.make('IN_Ducts', galv, None, coll=C)
    tray = Part()
    for x in (XR - 0.55, XL + 0.55):
        tray.box((x, (13 + Y_END) / 2, CEIL - 0.6), (0.45, Y_END - 14, 0.012))
        for sx in (-1, 1):
            tray.box((x + sx * 0.22, (13 + Y_END) / 2, CEIL - 0.56), (0.012, Y_END - 14, 0.08))
    tray.make('IN_CableTrays', galv, None, coll=C)
    for k, (col, nm) in enumerate((((0.1, 0.35, 0.15), 'Green'), ((0.12, 0.3, 0.6), 'Blue'),
                                   ((0.75, 0.55, 0.08), 'Yellow'))):
        pp = Part()
        for x in (XR - 0.35 - k * 0.14, XL + 0.35 + k * 0.14):
            pp.cyl((x, 13.0, CEIL - 0.95), (x, Y_END - 1.0, CEIL - 0.95), 0.045, 12)
        pp.make('IN_Pipe' + nm, P.grime_paint('IN_PipePaint' + nm, col, rough=0.35, grime=0.25, streak=0.15, coat=0.4),
                None, coll=C)
    d = Part()
    for x in (XL + 0.085, XR - 0.085):
        d.box((x, (12 + Y_END) / 2, DZ + 0.6), (0.01, Y_END - 12, 1.2))
    d.make('IN_Dado', P.plain('IN_PVCDado', (0.36, 0.42, 0.4), 0.35, coat=0.3), None, coll=C)


def _probes(C):
    """Sphere reflection probes down the hall: glass and the wet floor reflect the room, not the sky HDRI."""
    for k, y in enumerate((16, 25, 35, 47, 57, 65, 73, 86)):
        lp = bpy.data.lightprobes.new('IN_Probe%d' % k, 'SPHERE')
        lp.influence_distance = 9.0
        o = bpy.data.objects.new('IN_Probe%d' % k, lp)
        o.location = (CX, y, DZ + 2.4)
        C.objects.link(o)


def build_all(C, crate_fn, trolley_fn, shrimp_fn, fish_fn, ice_mesh, rnd_seed=11):
    M = mats()
    rnd = random.Random(rnd_seed)
    shell(C, M)
    _probes(C)
    _wet_floor()
    _services(C, M)
    pin = bpy.data.materials.get('PL_PanelInside')                 # warm grey panels, not paper white
    if pin and not pin.get('warm'):
        for n in pin.node_tree.nodes:
            if n.type == 'MIX' and n.data_type == 'RGBA' and not n.inputs[6].links:
                c = n.inputs[6].default_value
                if min(c[:3]) > 0.7:                               # the clean panel colour (not the grime tone)
                    n.inputs[6].default_value = (0.44, 0.48, 0.51, 1)   # blue-grey hygienic panel
                    n.inputs[7].default_value = (0.25, 0.27, 0.28, 1)
        pin['warm'] = True
    led = bpy.data.materials.get('PL_LED')
    if led:
        for n in led.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs['Emission Color'].default_value = (1.0, 0.94, 0.84, 1)
    intake(C, M, crate_fn, trolley_fn)
    wash(C, M, rnd, shrimp_fn)
    grading(C, M, rnd, shrimp_fn)
    tables = processing(C, M, rnd, shrimp_fn, fish_fn, ice_mesh)
    lab(C, M, rnd, shrimp_fn)
    freezing(C, M, rnd, shrimp_fn)
    packing(C, M, rnd)
    strips = cold_store(C, M, rnd)
    return tables, strips
