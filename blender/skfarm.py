"""Shrimp pond farm set for p-ponds and p-harvest: a heightfield of rectangular ponds with rounded bunds (some ponds
HDPE-lined), per-pond water tints, paddle-wheel aerators with churned foam, a farm compound (shed, pump house,
store), power poles and wires, feeding trays, coconut palms, fields and tree belts. Main bund road along y = 0.
Deterministic (seeded); no text, logos or numbers anywhere."""
import math
import random
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
import skpbr as P
import skveg as V
from sktruck import Part

HW, HH = 26.0, 20.0          # pond water half sizes (at the toe)
SLOPE = 3.0                  # bund slope width
BUND = 2.5                   # half bund-top width
PX, PY = 2 * (HW + SLOPE + BUND), 2 * (HH + SLOPE + BUND)
ROAD = 5.0                   # road half width (|y| < ROAD)
X0 = -320.0                  # first column centre
NCOL, NROW = 12, 5           # columns, rows each side of the road
TOP, BOTTOM, WATER = 1.5, -0.3, 0.95
COMPOUND = {(4, -1), (5, -1)}  # cells that are the farm yard (flat), south of the road


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def cell_of(x, y):
    """(i, j, cx, cy) of the pond cell containing (x, y); j >= 0 north of the road, j < 0 south."""
    i = int(math.floor((x - X0) / PX + 0.5))
    if y >= 0:
        j = int(math.floor((y - ROAD) / PY))
        cy = ROAD + (j + 0.5) * PY
    else:
        jj = int(math.floor((-y - ROAD) / PY))
        j = -1 - jj
        cy = -(ROAD + (jj + 0.5) * PY)
    return i, j, X0 + i * PX, cy


def pond_rand(i, j, k=0):
    return random.Random(i * 7919 + j * 104729 + k * 31).random()


def pond_size(i, j):
    return HW + (pond_rand(i, j, 1) - 0.5) * 5, HH + (pond_rand(i, j, 2) - 0.5) * 4


def in_farm(i, j):
    return 0 <= i < NCOL and -NROW <= j < NROW and (i, j) not in COMPOUND


def height(x, y):
    if abs(y) < ROAD:
        return TOP + 0.05
    i, j, cx, cy = cell_of(x, y)
    if not in_farm(i, j):
        return TOP if (i, j) in COMPOUND else TOP - 0.3
    hw, hh = pond_size(i, j)
    r = 5.0
    qx, qy = abs(x - cx) - (hw - r), abs(y - cy) - (hh - r)
    d = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r     # rounded-box SDF (negative inside)
    if d >= 0:
        return TOP
    if d > -SLOPE:
        t = -d / SLOPE
        return TOP + (BOTTOM - TOP) * (t * t * (3 - 2 * t))
    return BOTTOM


def terrain_mat(tex='dry_mud_field_001', scale=0.09):
    m = bpy.data.materials.get('FARM_Terrain')
    if m:
        return m
    dry = P.tex_mat('FARM_DryEarth', tex, scale=scale, sat=0.6, tint=(0.95, 0.86, 0.74), macro=0.35,
                    dirt_scale=0.012, normal=0.8)
    m = dry.copy()
    m.name = 'FARM_Terrain'
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    base = p.inputs['Base Color'].links[0].from_socket
    rough = p.inputs['Roughness'].links[0].from_socket if p.inputs['Roughness'].links else None
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L.new(geo.outputs['Position'], sep.inputs[0])
    # wet band near the waterline: darker, glossier
    wet = nt.nodes.new('ShaderNodeMapRange')
    wet.inputs['From Min'].default_value = WATER + 0.35
    wet.inputs['From Max'].default_value = WATER - 0.05
    L.new(sep.outputs[2], wet.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    L.new(wet.outputs[0], mx.inputs[0])
    L.new(base, mx.inputs[6])
    mx.inputs[7].default_value = (0.42, 0.36, 0.3, 1)
    # HDPE liner on the slopes of lined ponds (attribute 'liner' 0/1)
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'liner'
    at.attribute_type = 'GEOMETRY'
    band = nt.nodes.new('ShaderNodeMapRange')
    band.inputs['From Min'].default_value = TOP - 0.02
    band.inputs['From Max'].default_value = TOP - 0.12
    L.new(sep.outputs[2], band.inputs['Value'])
    lf = nt.nodes.new('ShaderNodeMath')
    lf.operation = 'MULTIPLY'
    L.new(at.outputs['Fac'], lf.inputs[0])
    L.new(band.outputs[0], lf.inputs[1])
    mx2 = nt.nodes.new('ShaderNodeMix')
    mx2.data_type = 'RGBA'
    L.new(lf.outputs[0], mx2.inputs[0])
    L.new(mx.outputs[2], mx2.inputs[6])
    mx2.inputs[7].default_value = (0.018, 0.019, 0.021, 1)
    L.new(mx2.outputs[2], p.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMix')
    rr.data_type = 'FLOAT'
    L.new(lf.outputs[0], rr.inputs[0])
    rr.inputs[2].default_value = 0.85
    rr.inputs[3].default_value = 0.32
    L.new(rr.outputs[0], p.inputs['Roughness'])
    return m


def build_terrain(C, x0=-360, x1=470, y0=-300, y1=300, res=1.5, tex='dry_mud_field_001', scale=0.09):
    nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    verts = []
    liner = []
    for y in ys:
        for x in xs:
            z = height(x, y)
            verts.append((x, y, z))
            i, j, _, _ = cell_of(x, y)
            liner.append(1.0 if in_farm(i, j) and pond_rand(i, j, 3) > 0.62 else 0.0)
    faces = []
    for r in range(ny - 1):
        for c in range(nx - 1):
            a = r * nx + c
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('FARM_TerrainMesh')
    me.from_pydata(verts, [], faces)
    at = me.attributes.new('liner', 'FLOAT', 'POINT')
    at.data.foreach_set('value', liner)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(terrain_mat(tex, scale))
    o = bpy.data.objects.new('FARM_Terrain', me)
    C.objects.link(o)
    # ground beyond the farm: fields (four slabs around the heightfield, never over the ponds)
    p = Part()
    big = 3000
    for cx, cy, sx, sy in (((x0 + x1) / 2, y1 + big / 2, big * 2, big), ((x0 + x1) / 2, y0 - big / 2, big * 2, big),
                           (x0 - big / 2, (y0 + y1) / 2, big, y1 - y0), (x1 + big / 2, (y0 + y1) / 2, big, y1 - y0)):
        p.box((cx, cy, TOP - 0.35), (sx, sy, 0.1))
    p.make('FARM_Fields', P.tex_mat('FARM_FieldTex', 'aerial_grass_rock', scale=0.02, sat=0.85, tint=(0.9, 0.95, 0.75),
                                    macro=0.35, dirt_scale=0.004), None, coll=C)
    return o


def water_mat():
    m = bpy.data.materials.get('FARM_PondWater')
    if m:
        return m
    m = bpy.data.materials.new('FARM_PondWater')
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'tint'
    at.attribute_type = 'GEOMETRY'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].color = (0.035, 0.085, 0.045, 1)      # algae green
    cr.elements[1].color = (0.085, 0.085, 0.045, 1)      # olive / tea
    e = cr.elements.new(0.5)
    e.color = (0.05, 0.10, 0.075, 1)                     # blue-green
    L.new(at.outputs['Fac'], ramp.inputs[0])
    L.new(ramp.outputs[0], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.05
    p.inputs['IOR'].default_value = 1.33
    p.inputs['Specular IOR Level'].default_value = 0.5
    # wind ripples (animated by the mapping location, keyed by the scene)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.name = 'RippleMap'
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.6
    nz.inputs['Detail'].default_value = 6
    nz.inputs['Roughness'].default_value = 0.6
    L.new(mp.outputs[0], nz.inputs['Vector'])
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = 0.08
    b.inputs['Distance'].default_value = 0.05
    L.new(nz.outputs['Fac'], b.inputs['Height'])
    L.new(b.outputs[0], p.inputs['Normal'])
    return m


def build_water(C):
    verts, faces, tints = [], [], []
    for i in range(NCOL):
        for j in range(-NROW, NROW):
            if not in_farm(i, j):
                continue
            _, _, cx, cy = cell_of(X0 + i * PX, (ROAD + (j + 0.5) * PY) if j >= 0 else -(ROAD + (-1 - j + 0.5) * PY))
            hw, hh = pond_size(i, j)
            k = len(verts)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append((cx + sx * (hw + SLOPE * 0.6), cy + sy * (hh + SLOPE * 0.6), WATER))
            faces.append((k, k + 1, k + 2, k + 3))
            tints.append(pond_rand(i, j, 4))
    me = bpy.data.meshes.new('FARM_WaterMesh')
    me.from_pydata(verts, [], faces)
    at = me.attributes.new('tint', 'FLOAT', 'FACE')
    at.data.foreach_set('value', tints)
    me.materials.append(water_mat())
    o = bpy.data.objects.new('FARM_Water', me)
    C.objects.link(o)
    return o


def pond_centre(i, j):
    cy = (ROAD + (j + 0.5) * PY) if j >= 0 else -(ROAD + (-1 - j + 0.5) * PY)
    return X0 + i * PX, cy


# ------------------------------------------------------------------ aerators
def foam_mat():
    m = bpy.data.materials.get('FARM_Foam')
    if m:
        return m
    m = bpy.data.materials.new('FARM_Foam')
    m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.92, 0.94, 0.92, 1)
    p.inputs['Roughness'].default_value = 0.6
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.name = 'FoamMap'
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.6
    nz.inputs['Detail'].default_value = 12
    nz.inputs['Roughness'].default_value = 0.7
    L.new(mp.outputs[0], nz.inputs['Vector'])
    # radial falloff from the object origin (foam densest at the wheel, streaking downstream along +X)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs['Object'], sep.inputs[0])
    sx = nt.nodes.new('ShaderNodeMath')
    sx.operation = 'MULTIPLY'
    sx.inputs[1].default_value = 0.32
    L.new(sep.outputs[0], sx.inputs[0])
    sy = nt.nodes.new('ShaderNodeMath')
    sy.operation = 'MULTIPLY'
    sy.inputs[1].default_value = 0.13
    L.new(sep.outputs[1], sy.inputs[0])
    cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    L.new(sx.outputs[0], cmb.inputs[0])
    L.new(sy.outputs[0], cmb.inputs[1])
    ln = nt.nodes.new('ShaderNodeVectorMath')
    ln.operation = 'LENGTH'
    L.new(cmb.outputs[0], ln.inputs[0])
    fall = nt.nodes.new('ShaderNodeMapRange')
    fall.inputs['From Min'].default_value = 1.0
    fall.inputs['From Max'].default_value = 0.1
    L.new(ln.outputs['Value'], fall.inputs['Value'])
    thr = nt.nodes.new('ShaderNodeMapRange')
    thr.inputs['From Min'].default_value = 0.42
    thr.inputs['From Max'].default_value = 0.62
    L.new(nz.outputs['Fac'], thr.inputs['Value'])
    a = nt.nodes.new('ShaderNodeMath')
    a.operation = 'MULTIPLY'
    L.new(thr.outputs[0], a.inputs[0])
    L.new(fall.outputs[0], a.inputs[1])
    a2 = nt.nodes.new('ShaderNodeMath')
    a2.operation = 'ADD'
    a2.use_clamp = True
    L.new(a.outputs[0], a2.inputs[0])
    core = nt.nodes.new('ShaderNodeMapRange')
    core.inputs['From Min'].default_value = 0.45
    core.inputs['From Max'].default_value = 0.15
    L.new(ln.outputs['Value'], core.inputs['Value'])
    L.new(core.outputs[0], a2.inputs[1])
    L.new(a2.outputs[0], p.inputs['Alpha'])
    return m


def aerator_collection(phase=0.0, name='AER_0', f0=1, f1=600):
    """Paddle-wheel aerator: two floats, frame, motor + gearbox, shaft with 2 paddle wheels, churn foam."""
    C = bpy.data.collections.get(name)
    if C:
        return C
    C = bpy.data.collections.new(name)
    blue = P.plain('FARM_FloatBlue', (0.06, 0.16, 0.32), 0.45, coat=0.3)
    white = P.plain('FARM_FloatWhite', (0.75, 0.76, 0.74), 0.4, coat=0.2)
    steel = P.grime_paint('FARM_AerSteel', (0.42, 0.44, 0.45), rough=0.4, grime=0.6, streak=0.4, coat=0.0, metal=0.6)
    motor = P.plain('FARM_Motor', (0.12, 0.22, 0.35), 0.35, 0.3, coat=0.4)
    paddle = P.plain('FARM_Paddle', (0.6, 0.62, 0.6), 0.5)
    root = bpy.data.objects.new(name + '_Root', None)
    C.objects.link(root)
    p = Part()
    for x in (-1.6, 1.6):
        p.cyl((x, -0.35, 0.05), (x, 0.55, 0.05), 0.22, 16)
    p.make(name + '_Floats', blue, root, smooth=True, coll=C)
    p = Part()
    p.box((0, 0, 0.32), (3.4, 0.08, 0.08))
    for x in (-1.6, 0, 1.6):
        p.box((x, 0.1, 0.2), (0.06, 0.5, 0.25))
    p.make(name + '_Frame', steel, root, coll=C)
    p = Part()
    p.box((-2.1, 0.0, 0.42), (0.6, 0.38, 0.38))
    p.cyl((-2.4, 0, 0.42), (-2.75, 0, 0.42), 0.17, 16)
    p.make(name + '_Motor', motor, root, bevel=0.02, coll=C)
    for k, x in enumerate((-0.8, 0.8)):
        w = Part()
        w.cyl((-0.35, 0, 0), (0.35, 0, 0), 0.06, 10)
        for n in range(8):
            a = 2 * math.pi * n / 8
            q = Euler((a, 0, 0)).to_matrix()
            for s in (-0.25, 0.25):
                c = q @ Vector((s, 0, 0.42))
            w.box(tuple(q @ Vector((0, 0, 0.42))), (0.62, 0.03, 0.34), Euler((a, 0, 0)))
        wo = w.make(name + '_Wheel%d' % k, paddle, root, coll=C)
        wo.location = (x, 0.0, 0.32)
        for f, ang in ((f0, phase), (f1, phase + (f1 - f0) / 24 * 2 * math.pi * 1.1)):
            wo.rotation_euler = (ang, 0, 0)
            wo.keyframe_insert('rotation_euler', frame=f)
        for fc in _fc(wo):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    # churn foam on the water around the wheels, streaking downstream (+Y in aerator space)
    p = Part()
    bm = p.bm
    res = bmesh.ops.create_grid(bm, x_segments=4, y_segments=8, size=1.0)
    for v in res['verts']:
        v.co = Vector((v.co.x * 4.2, (v.co.y + 0.7) * 11.0, -0.25))
    fo = p.make(name + '_Foam', foam_mat(), root, coll=C)
    fo.location = (0, 0, 0)
    return C


def _fc(o):
    import sktruck
    return sktruck._fcurves(o.animation_data.action) if o.animation_data and o.animation_data.action else []


def place_aerators(C, rnd, near=None):
    """2-4 aerators per pond near the long edges; returns the instance objects."""
    cols = [aerator_collection(0.0, 'AER_0'), aerator_collection(1.3, 'AER_1'), aerator_collection(2.4, 'AER_2')]
    out = []
    for i in range(NCOL):
        for j in range(-NROW, NROW):
            if not in_farm(i, j):
                continue
            cx, cy = pond_centre(i, j)
            if near and math.hypot(cx - near[0], cy - near[1]) > near[2]:
                continue
            hw, hh = pond_size(i, j)
            n = 2 + int(pond_rand(i, j, 5) * 2.99)
            spots = [(cx - hw * 0.45, cy - hh + 5, 0), (cx + hw * 0.45, cy + hh - 5, math.pi),
                     (cx - hw + 6, cy + hh * 0.35, -math.pi / 2), (cx + hw - 6, cy - hh * 0.35, math.pi / 2)][:n]
            for k, (x, y, r) in enumerate(spots):
                o = bpy.data.objects.new('AER_%d_%d_%d' % (i, j, k), None)
                o.instance_type = 'COLLECTION'
                o.instance_collection = cols[(i + j + k) % 3]
                o.location = (x, y, WATER - 0.02)
                o.scale = (1.3, 1.3, 1.3)
                o.rotation_euler = (0, 0, r + rnd.uniform(-0.12, 0.12))
                C.objects.link(o)
                out.append(o)
    return out


def animate_water(f0, f1):
    """Drift the ripple and foam noise so the water and the churn move."""
    for mn, node, vel in (('FARM_PondWater', 'RippleMap', (0.35, 0.12, 0.0)), ('FARM_Foam', 'FoamMap', (0.0, 1.6, 0.6))):
        m = bpy.data.materials.get(mn)
        if not m:
            continue
        mp = m.node_tree.nodes[node]
        sock = mp.inputs['Location']
        for f in (f0, f1):
            t = (f - f0) / 24
            sock.default_value = (vel[0] * t, vel[1] * t, vel[2] * t)
            sock.keyframe_insert('default_value', frame=f)
        import sktruck
        for fc in sktruck._fcurves(m.node_tree.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


# ------------------------------------------------------------------ farm compound, poles, trays, palms
def ruts(C):
    import skplant
    p = Part()
    for y in (-2.9, -0.8, 0.8, 2.9):
        p.box((55, y, TOP + 0.07), (830, 0.45, 0.01))
    p.make('FARM_Ruts', skplant.line_mat('FARM_RutMat', (0.13, 0.09, 0.06), alpha=0.75), None, coll=C)


def compound(C, rnd):
    brick = P.tex_mat('FARM_PlasterWall', 'painted_plaster_wall', scale=0.5, sat=0.5, tint=(0.95, 0.92, 0.85), dirt=0.3)
    roof = P.tex_mat('FARM_TinRoof', 'corrugated_iron_02', scale=0.5, sat=0.4, tint=(0.85, 0.85, 0.85), metal=0.7)
    tarp = P.plain('FARM_Tarp', (0.12, 0.25, 0.42), 0.6, bump=0.4, bump_scale=3)
    cx, cy = pond_centre(4, -1)
    cx2, _ = pond_centre(5, -1)
    xm = (cx + cx2) / 2
    p = Part()
    p.box((xm - 20, cy + 6, TOP + 1.8), (18, 9, 3.6))           # farm shed (feed store)
    p.box((xm + 6, cy + 10, TOP + 1.4), (6, 5, 2.8))             # pump house
    p.box((xm + 22, cy - 2, TOP + 1.6), (10, 7, 3.2))            # store / office
    p.make('FARM_Buildings', brick, None, bevel=0.03, coll=C)
    p = Part()
    p.box((xm - 20, cy + 6, TOP + 3.8), (19.5, 10.5, 0.12), Euler((0.08, 0, 0)))
    p.box((xm + 6, cy + 10, TOP + 3.0), (6.8, 5.8, 0.1), Euler((0.1, 0, 0)))
    p.box((xm + 22, cy - 2, TOP + 3.4), (11, 8, 0.1), Euler((-0.07, 0, 0)))
    p.make('FARM_Roofs', roof, None, coll=C)
    p = Part()
    p.box((xm - 2, cy - 8, TOP + 2.2), (8, 6, 0.05))               # tarp shade
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl((xm - 2 + sx * 3.9, cy - 8 + sy * 2.9, TOP), (xm - 2 + sx * 3.9, cy - 8 + sy * 2.9, TOP + 2.2), 0.05, 6)
    p.make('FARM_TarpShade', tarp, None, coll=C)
    # feed bags, drums, a parked pickup-sized block, a small generator
    p = Part()
    for k in range(14):
        p.box((xm - 6 + (k % 7) * 0.7, cy - 9 + (k // 7) * 0.5, TOP + 0.15), (0.6, 0.42, 0.28))
    p.make('FARM_FeedBags', P.plain('FARM_Sack', (0.75, 0.72, 0.62), 0.9, bump=0.3), None, bevel=0.05, coll=C)
    p = Part()
    for k in range(6):
        p.cyl((xm + 12 + k * 0.7, cy + 3, TOP), (xm + 12 + k * 0.7, cy + 3, TOP + 0.9), 0.29, 16)
    p.make('FARM_Drums', P.plain('FARM_DrumBlue', (0.08, 0.18, 0.35), 0.4, coat=0.2), None, coll=C)
    return xm, cy


def poles(C, rnd):
    conc = P.plain('FARM_PoleConcrete', (0.58, 0.57, 0.54), 0.8, bump=0.3)
    wire = P.plain('FARM_Wire', (0.03, 0.03, 0.03), 0.5)
    p = Part()
    q = Part()
    xs = list(range(-340, 460, 38))
    for side in (6.2, -6.2):
        pts = []
        for x in xs:
            top = (x, side, TOP + 8.0)
            p.cyl((x, side, TOP - 0.5), top, 0.12, 6, r2=0.08)
            p.box((x, side, TOP + 7.7), (0.1, 1.2, 0.1))
            pts.append(top)
        for a, b in zip(pts, pts[1:]):
            for dy in (-0.5, 0.5):
                for k in range(8):
                    t0, t1 = k / 8, (k + 1) / 8
                    z0 = a[2] - 0.2 - 0.7 * math.sin(math.pi * t0)
                    z1 = a[2] - 0.2 - 0.7 * math.sin(math.pi * t1)
                    q.cyl((a[0] + (b[0] - a[0]) * t0, side + dy, z0), (a[0] + (b[0] - a[0]) * t1, side + dy, z1), 0.015, 3)
    # feeder lines up the cross bunds to the aerators (low poles)
    for i in range(NCOL + 1):
        x = X0 + (i - 0.5) * PX
        for sgn in (1, -1):
            prev = None
            for k in range(NROW * 2 + 1):
                y = sgn * (ROAD + k * PY / 2)
                if abs(y) > ROAD + NROW * PY:
                    break
                top = (x, y, TOP + 4.0)
                p.cyl((x, y, TOP - 0.3), top, 0.07, 5)
                if prev:
                    q.cyl(prev, top, 0.01, 3)
                prev = top
    p.make('FARM_Poles', conc, None, coll=C)
    q.make('FARM_Wires', wire, None, coll=C)


def feed_trays(C, rnd):
    tray = P.plain('FARM_Tray', (0.1, 0.1, 0.11), 0.5)
    pole = P.plain('FARM_TrayPole', (0.45, 0.36, 0.25), 0.8)
    p = Part()
    q = Part()
    for i in range(NCOL):
        for j in range(-NROW, NROW):
            if not in_farm(i, j):
                continue
            cx, cy = pond_centre(i, j)
            hw, hh = pond_size(i, j)
            for k in range(2):
                x = cx + (rnd.uniform(-0.6, 0.6)) * hw
                y = cy + (hh + 0.8) * (1 if k else -1)
                q.cyl((x, y, WATER - 0.5), (x, y, WATER + 1.4), 0.03, 4)
                p.cyl((x, y - 0.7 * (1 if k else -1), WATER + 0.02), (x, y - 0.7 * (1 if k else -1), WATER + 0.08), 0.4, 12)
    p.make('FARM_Trays', tray, None, coll=C)
    q.make('FARM_TrayPoles', pole, None, coll=C)


def palms(C, rnd, xm, ym):
    pm = V.palm_mesh()
    pm2 = V.palm_mesh('VEG_PalmMesh2', h=13.5, seed=8, fronds=20)
    tm = V.tree_mesh()
    sm = V.shrub_mesh()
    for x in range(-340, 460, 11):
        for side in (7.6, -7.6):
            if rnd.random() < 0.55:
                V.place(rnd.choice([pm, pm2]), 'VEG_RoadPalm', (x + rnd.uniform(-3, 3), side + rnd.uniform(-1, 1), TOP),
                        rnd.uniform(0.8, 1.2), coll=C, rnd=rnd)
            elif rnd.random() < 0.4 and not (20 < x < 100):
                V.place(sm, 'VEG_RoadShrub', (x + rnd.uniform(-3, 3), side * 1.05, TOP), rnd.uniform(0.6, 1.2), coll=C, rnd=rnd)
    for k in range(26):
        V.place(rnd.choice([pm, pm2]), 'VEG_YardPalm', (xm + rnd.uniform(-34, 34), ym + rnd.uniform(-20, 20), TOP),
                rnd.uniform(0.85, 1.25), coll=C, rnd=rnd)
    # outer belts of palms and trees around the farm
    xa, xb = X0 - PX / 2, X0 + (NCOL - 0.5) * PX
    yb = ROAD + NROW * PY
    for k in range(160):
        side = k % 4
        if side == 0:
            x, y = rnd.uniform(xa - 60, xb + 60), yb + rnd.uniform(6, 40)
        elif side == 1:
            x, y = rnd.uniform(xa - 60, xb + 60), -yb - rnd.uniform(6, 40)
        elif side == 2:
            x, y = xa - rnd.uniform(6, 50), rnd.uniform(-yb, yb)
        else:
            x, y = xb + rnd.uniform(6, 50), rnd.uniform(-yb, yb)
        mesh = rnd.choice([pm, pm2, pm, tm])
        V.place(mesh, 'VEG_Belt', (x, y, TOP - 0.3), rnd.uniform(0.9, 1.4), coll=C, rnd=rnd)
    # far horizon tree belt (large scale, cheap)
    for k in range(220):
        a = 2 * math.pi * k / 220
        r = rnd.uniform(650, 900)
        V.place(rnd.choice([tm, pm2]), 'VEG_Far', (60 + math.cos(a) * r, math.sin(a) * r * 0.8, TOP - 0.4),
                rnd.uniform(2.0, 3.2), coll=C, rnd=rnd)


def birds(C, rnd, n=7, f0=1, f1=300, centre=(0, 0, 25)):
    white = P.plain('FARM_Egret', (0.85, 0.86, 0.84), 0.6)
    out = []
    for k in range(n):
        root = bpy.data.objects.new('BIRD_%d' % k, None)
        C.objects.link(root)
        body = Part()
        body.cyl((-0.25, 0, 0), (0.3, 0, 0), 0.07, 6, r2=0.03)
        body.make('BIRD_%d_Body' % k, white, root, coll=C)
        for s in (-1, 1):
            wg = Part()
            bm = wg.bm
            vs = [bm.verts.new(v) for v in ((-0.12, 0, 0), (0.12, 0, 0), (0.05, s * 0.75, 0), (-0.15, s * 0.7, 0))]
            bm.faces.new(vs)
            wo = wg.make('BIRD_%d_Wing%d' % (k, s), white, root, coll=C)
            ph = rnd.uniform(0, 6.28)
            for f in range(f0, f1 + 1, 3):
                wo.rotation_euler = (s * 0.6 * math.sin(ph + f * 0.55), 0, 0)
                wo.keyframe_insert('rotation_euler', frame=f)
        a = rnd.uniform(0, 6.28)
        p0 = Vector(centre) + Vector((rnd.uniform(-60, 60), rnd.uniform(-60, 60), rnd.uniform(-8, 8)))
        d = Vector((math.cos(a), math.sin(a), 0))
        for f in (f0, f1):
            root.location = p0 + d * (f - f0) / 24 * 7.0
            root.rotation_euler = (0, 0, a)
            root.keyframe_insert('location', frame=f)
            root.keyframe_insert('rotation_euler', frame=f)
        for fc in _fc(root):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
        root.scale = (1.4, 1.4, 1.4)
        out.append(root)
    return out


_SH = {}


def shrimp_mesh():
    """Raw whiteleg shrimp (~12 cm): curved segmented abdomen with ridges, carapace + rostrum, tail fan,
    walking legs, swimmerets and long antennae. Translucent grey shell with darker tail-fan edges."""
    if 'm' in _SH:
        return _SH['m']
    bm = bmesh.new()
    seg = 12
    n = 26
    rings = []
    L = 0.12
    for i in range(n + 1):
        t = i / n
        a = math.pi * 0.62 * t                     # curl
        R = L / (math.pi * 0.62)
        c = Vector((R * math.sin(a), 0, R * (1 - math.cos(a))))
        tan = Vector((math.cos(a), 0, math.sin(a)))
        up = Vector((-math.sin(a), 0, math.cos(a)))
        prof = 0.011 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.15 + t * 0.95)))
        if t < 0.38:
            prof *= 1.08                            # carapace
        ridge = 1.0 + 0.06 * max(0.0, math.cos(t * n * math.pi)) if t > 0.38 else 1.0
        ring = []
        for j in range(seg):
            b = 2 * math.pi * j / seg
            off = Vector((0, math.cos(b) * prof * 0.85 * ridge, 0)) + up * (math.sin(b) * prof * ridge * 1.1)
            ring.append(bm.verts.new(c + off))
        rings.append((ring, c, tan, up))
    for i in range(n):
        a, b = rings[i][0], rings[i + 1][0]
        for j in range(seg):
            bm.faces.new((a[j], b[j], b[(j + 1) % seg], a[(j + 1) % seg]))
    bm.faces.new(list(reversed(rings[0][0])))
    nb = len(bm.faces)
    # tail fan at the end of the abdomen
    _, c, tan, up = rings[-1]
    for k in range(5):
        ang = (k - 2) * 0.32
        d = (tan * math.cos(ang) + Vector((0, math.sin(ang), 0))).normalized()
        w = Vector((0, 1, 0)).cross(d).normalized() if abs(ang) > 0.01 else up
        side = d.cross(up).normalized()
        p0 = c
        p1 = c + d * 0.028 + side * 0.006
        p2 = c + d * 0.03 - side * 0.006
        bm.faces.new([bm.verts.new(v) for v in (p0 + side * 0.002, p1, p2, p0 - side * 0.002)])
    nf = len(bm.faces)
    # rostrum, antennae, legs, swimmerets (thin strips)
    head, ht, hu = rings[0][1], rings[0][2], rings[0][3]

    def strip(a, b, w=0.0012):
        s = Vector((0, w, 0))
        bm.faces.new([bm.verts.new(v) for v in (a - s, b - s, b + s, a + s)])
    strip(head, head - ht * 0.03 + hu * 0.006, 0.002)
    for sy in (-1, 1):
        a0 = head + Vector((0, sy * 0.004, 0.002))
        prev = a0
        for k in range(6):
            nxt = a0 + Vector((-0.05 * (k + 1), sy * 0.012 * (k + 1), 0.01 * math.sin(k * 0.7) + 0.004 * (k + 1)))
            strip(prev, nxt, 0.0006)
            prev = nxt
        for k in range(5):
            r = rings[2 + k * 2]
            base = r[1] - r[3] * 0.009 + Vector((0, sy * 0.006, 0))
            strip(base, base - r[3] * 0.02 + Vector((0, sy * 0.006, 0)) - r[2] * 0.004, 0.0008)
        for k in range(5):
            r = rings[12 + k * 2]
            base = r[1] - r[3] * 0.008 + Vector((0, sy * 0.004, 0))
            strip(base, base - r[3] * 0.012 - r[2] * 0.005, 0.0015)
    me = bpy.data.meshes.new('FARM_ShrimpMesh')
    bm.to_mesh(me)
    bm.free()
    shell = bpy.data.materials.get('FARM_ShrimpShell') or P.plain('FARM_ShrimpShell', (0.62, 0.64, 0.62), 0.22, coat=0.8,
                                                                   sss=0.3, transmission=0.2)
    fan = P.plain('FARM_ShrimpFan', (0.32, 0.30, 0.34), 0.25, coat=0.6, sss=0.2)
    me.materials.append(shell)
    me.materials.append(fan)
    for i, poly in enumerate(me.polygons):
        poly.use_smooth = i < nb
        poly.material_index = 1 if nb <= i < nf else 0
    _SH['m'] = me
    return me


def shrimp(name, loc, rot, parent=None, C=None, scale=1.0):
    o = bpy.data.objects.new(name, shrimp_mesh())
    (C or bpy.context.scene.collection).objects.link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.scale = (scale, scale, scale)
    return o


def motorbike(name, C):
    """Small motorbike with a rider block (seen from far above only)."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    p = Part()
    p.box((0, 0, 0.55), (1.3, 0.25, 0.35))
    p.box((-0.1, 0, 0.82), (0.7, 0.3, 0.12))
    p.make(name + '_Body', P.plain('MB_Red', (0.3, 0.05, 0.04), 0.35, 0.3, coat=0.5), root, bevel=0.03, coll=C)
    p = Part()
    for x in (-0.6, 0.62):
        p.cyl((x, -0.06, 0.3), (x, 0.06, 0.3), 0.3, 16)
    p.make(name + '_Wheels', P.plain('MB_Tyre', (0.03, 0.03, 0.03), 0.7), root, coll=C)
    return root
