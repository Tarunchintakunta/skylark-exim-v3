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


def veg():
    """Shared vegetation pool: palms of different height / frond count, broadleaf trees, shrubs."""
    if 'palms' not in _VEG:
        _VEG['palms'] = [V.palm_mesh(), V.palm_mesh('VEG_PalmMesh2', h=13.5, seed=8, fronds=20),
                         V.palm_mesh('VEG_PalmTall', h=16.0, seed=21, fronds=26),
                         V.palm_mesh('VEG_PalmYoung', h=6.5, seed=23, fronds=14)]
        _VEG['trees'] = [V.tree_mesh(), V.tree_mesh('VEG_TreeWide', h=10.0, crown=4.6, seed=4),
                         V.tree_mesh('VEG_TreeSmall', h=5.5, crown=2.2, seed=6, leaves=1400)]
        _VEG['shrubs'] = [V.shrub_mesh(), V.shrub_mesh('VEG_ShrubLow', r=1.3, seed=9, leaves=900)]
    return _VEG


_VEG = {}


def place(mesh, name, loc, scale, C, rnd, lean=0.09):
    o = V.place(mesh, name, loc, scale, coll=C, rnd=rnd)
    o.rotation_euler.x = rnd.uniform(-lean, lean)
    o.rotation_euler.y = rnd.uniform(-lean, lean)
    return o


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
    mx.inputs[7].default_value = (0.19, 0.155, 0.12, 1)
    wet.inputs['From Min'].default_value = WATER + 0.75
    gn = nt.nodes.new('ShaderNodeTexNoise')
    gn.inputs['Scale'].default_value = 0.22
    gn.inputs['Detail'].default_value = 10
    L.new(geo.outputs['Position'], gn.inputs['Vector'])
    gt = nt.nodes.new('ShaderNodeMapRange')
    gt.inputs['From Min'].default_value = 0.44
    gt.inputs['From Max'].default_value = 0.52
    L.new(gn.outputs['Fac'], gt.inputs['Value'])
    gh = nt.nodes.new('ShaderNodeMapRange')
    gh.inputs['From Min'].default_value = WATER + 0.25
    gh.inputs['From Max'].default_value = TOP - 0.1
    L.new(sep.outputs[2], gh.inputs['Value'])
    ay = nt.nodes.new('ShaderNodeMath')
    ay.operation = 'ABSOLUTE'
    L.new(sep.outputs[1], ay.inputs[0])
    gr = nt.nodes.new('ShaderNodeMapRange')
    gr.inputs['From Min'].default_value = ROAD + 0.3
    gr.inputs['From Max'].default_value = ROAD + 1.5
    L.new(ay.outputs[0], gr.inputs['Value'])
    g1 = nt.nodes.new('ShaderNodeMath')
    g1.operation = 'MULTIPLY'
    L.new(gt.outputs[0], g1.inputs[0])
    L.new(gh.outputs[0], g1.inputs[1])
    g2 = nt.nodes.new('ShaderNodeMath')
    g2.operation = 'MULTIPLY'
    L.new(g1.outputs[0], g2.inputs[0])
    L.new(gr.outputs[0], g2.inputs[1])
    g3 = nt.nodes.new('ShaderNodeMath')
    g3.operation = 'MULTIPLY'
    g3.inputs[1].default_value = 0.95
    L.new(g2.outputs[0], g3.inputs[0])
    gmx = nt.nodes.new('ShaderNodeMix')
    gmx.data_type = 'RGBA'
    L.new(g3.outputs[0], gmx.inputs[0])
    L.new(mx.outputs[2], gmx.inputs[6])
    gc = nt.nodes.new('ShaderNodeTexNoise')               # grass colour: green to sun-dried straw
    gc.inputs['Scale'].default_value = 0.6
    L.new(geo.outputs['Position'], gc.inputs['Vector'])
    gcr = nt.nodes.new('ShaderNodeValToRGB')
    gcr.color_ramp.elements[0].color = (0.06, 0.13, 0.025, 1)
    gcr.color_ramp.elements[1].color = (0.20, 0.19, 0.07, 1)
    gcr.color_ramp.elements[0].position = 0.35
    gcr.color_ramp.elements[1].position = 0.7
    e = gcr.color_ramp.elements.new(0.52)
    e.color = (0.11, 0.17, 0.035, 1)
    L.new(gc.outputs['Fac'], gcr.inputs[0])
    gtx = nt.nodes.new('ShaderNodeMix')                   # blades: fine dark/light speckle inside the patches
    gtx.data_type = 'RGBA'
    gtx.blend_type = 'MULTIPLY'
    gtn = nt.nodes.new('ShaderNodeTexNoise')
    gtn.inputs['Scale'].default_value = 9.0
    gtn.inputs['Detail'].default_value = 6
    L.new(geo.outputs['Position'], gtn.inputs['Vector'])
    gtm = nt.nodes.new('ShaderNodeMapRange')
    gtm.inputs['To Min'].default_value = 0.6
    gtm.inputs['To Max'].default_value = 1.3
    L.new(gtn.outputs['Fac'], gtm.inputs['Value'])
    gtx.inputs[0].default_value = 1.0
    L.new(gcr.outputs[0], gtx.inputs[6])
    gcomb = nt.nodes.new('ShaderNodeCombineXYZ')
    for k in range(3):
        L.new(gtm.outputs[0], gcomb.inputs[k])
    L.new(gcomb.outputs[0], gtx.inputs[7])
    L.new(gtx.outputs[2], gmx.inputs[7])
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
    L.new(gmx.outputs[2], mx2.inputs[6])
    mx2.inputs[7].default_value = (0.018, 0.019, 0.021, 1)
    L.new(mx2.outputs[2], p.inputs['Base Color'])
    # puddles on the flat road and bund tops after the last rain: dark, glossy, sky reflections
    pz = nt.nodes.new('ShaderNodeTexNoise')
    pz.inputs['Scale'].default_value = 0.11
    pz.inputs['Detail'].default_value = 4
    L.new(geo.outputs['Position'], pz.inputs['Vector'])
    pt = nt.nodes.new('ShaderNodeMapRange')
    pt.inputs['From Min'].default_value = 0.705
    pt.inputs['From Max'].default_value = 0.715
    L.new(pz.outputs['Fac'], pt.inputs['Value'])
    pf = nt.nodes.new('ShaderNodeMapRange')               # only where the ground is flat and high
    pf.inputs['From Min'].default_value = TOP - 0.05
    pf.inputs['From Max'].default_value = TOP - 0.01
    L.new(sep.outputs[2], pf.inputs['Value'])
    pu = nt.nodes.new('ShaderNodeMath')
    pu.operation = 'MULTIPLY'
    L.new(pt.outputs[0], pu.inputs[0])
    L.new(pf.outputs[0], pu.inputs[1])
    pmx = nt.nodes.new('ShaderNodeMix')
    pmx.data_type = 'RGBA'
    L.new(pu.outputs[0], pmx.inputs[0])
    L.new(mx2.outputs[2], pmx.inputs[6])
    pmx.inputs[7].default_value = (0.05, 0.045, 0.04, 1)
    L.new(pmx.outputs[2], p.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMix')
    rr.data_type = 'FLOAT'
    L.new(lf.outputs[0], rr.inputs[0])
    rr.inputs[2].default_value = 0.85
    rr.inputs[3].default_value = 0.32
    rw = nt.nodes.new('ShaderNodeMix')                    # wet mud near the waterline is glossy
    rw.data_type = 'FLOAT'
    L.new(wet.outputs[0], rw.inputs[0])
    L.new(rr.outputs[0], rw.inputs[2])
    rw.inputs[3].default_value = 0.38
    rpd = nt.nodes.new('ShaderNodeMix')
    rpd.data_type = 'FLOAT'
    L.new(pu.outputs[0], rpd.inputs[0])
    L.new(rw.outputs[0], rpd.inputs[2])
    rpd.inputs[3].default_value = 0.03
    L.new(rpd.outputs[0], p.inputs['Roughness'])
    if p.inputs['Normal'].links:                          # puddles are flat: no ground bump through them
        nb = p.inputs['Normal'].links[0].from_socket
        geo2 = nt.nodes.new('ShaderNodeNewGeometry')
        nmx = nt.nodes.new('ShaderNodeMix')
        nmx.data_type = 'VECTOR'
        L.new(pu.outputs[0], nmx.inputs[0])
        L.new(nb, nmx.inputs[4])
        L.new(geo2.outputs['Normal'], nmx.inputs[5])
        L.new(nmx.outputs[1], p.inputs['Normal'])
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
    p.make('FARM_Fields', paddy_mat(), None, coll=C)
    return o


def paddy_mat():
    """Coastal Andhra paddy: plots of young / ripening rice and a few freshly flooded plots, thin earth bunds."""
    m = bpy.data.materials.get('FARM_Paddy')
    if m:
        return m
    m = bpy.data.materials.new('FARM_Paddy')
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 42.0, 1 / 26.0, 1.0)
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(7))
    L.new(geo.outputs['Position'], mp.inputs['Vector'])
    fl = nt.nodes.new('ShaderNodeVectorMath')
    fl.operation = 'FLOOR'
    L.new(mp.outputs[0], fl.inputs[0])
    wn = nt.nodes.new('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    L.new(fl.outputs[0], wn.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.045, 0.13, 0.025, 1)
    cr.elements[1].position, cr.elements[1].color = 0.88, (0.17, 0.27, 0.05, 1)
    for pos, col in ((0.35, (0.10, 0.25, 0.035, 1)), (0.6, (0.07, 0.19, 0.03, 1)), (0.8, (0.15, 0.30, 0.045, 1)),
                     (0.885, (0.035, 0.055, 0.05, 1)), (1.0, (0.04, 0.06, 0.055, 1))):
        e = cr.elements.new(pos)
        e.color = col
    L.new(wn.outputs['Value'], ramp.inputs[0])
    flood = nt.nodes.new('ShaderNodeMapRange')       # flooded plots: water with sky reflections
    flood.inputs['From Min'].default_value = 0.88
    flood.inputs['From Max'].default_value = 0.885
    L.new(wn.outputs['Value'], flood.inputs['Value'])
    fine = nt.nodes.new('ShaderNodeTexNoise')        # crop texture
    fine.inputs['Scale'].default_value = 0.9
    fine.inputs['Detail'].default_value = 8
    L.new(geo.outputs['Position'], fine.inputs['Vector'])
    big = nt.nodes.new('ShaderNodeTexNoise')         # large-scale variation
    big.inputs['Scale'].default_value = 0.004
    L.new(geo.outputs['Position'], big.inputs['Vector'])
    vr = nt.nodes.new('ShaderNodeMapRange')
    vr.inputs['To Min'].default_value = 0.75
    vr.inputs['To Max'].default_value = 1.2
    L.new(fine.outputs['Fac'], vr.inputs['Value'])
    vb = nt.nodes.new('ShaderNodeMapRange')
    vb.inputs['To Min'].default_value = 0.8
    vb.inputs['To Max'].default_value = 1.15
    L.new(big.outputs['Fac'], vb.inputs['Value'])
    m1 = nt.nodes.new('ShaderNodeVectorMath')
    m1.operation = 'MULTIPLY'
    L.new(ramp.outputs[0], m1.inputs[0])
    L.new(vr.outputs[0], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeVectorMath')
    m2.operation = 'MULTIPLY'
    L.new(m1.outputs[0], m2.inputs[0])
    L.new(vb.outputs[0], m2.inputs[1])
    fr = nt.nodes.new('ShaderNodeVectorMath')        # earth bunds between plots
    fr.operation = 'FRACTION'
    L.new(mp.outputs[0], fr.inputs[0])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L.new(fr.outputs[0], sep.inputs[0])
    edge = None
    for comp in ('X', 'Y'):
        inv = nt.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        L.new(sep.outputs[comp], inv.inputs[1])
        mn = nt.nodes.new('ShaderNodeMath')
        mn.operation = 'MINIMUM'
        L.new(sep.outputs[comp], mn.inputs[0])
        L.new(inv.outputs[0], mn.inputs[1])
        if edge is None:
            edge = mn
        else:
            e2 = nt.nodes.new('ShaderNodeMath')
            e2.operation = 'MINIMUM'
            L.new(edge.outputs[0], e2.inputs[0])
            L.new(mn.outputs[0], e2.inputs[1])
            edge = e2
    bund = nt.nodes.new('ShaderNodeMapRange')
    bund.inputs['From Min'].default_value = 0.03
    bund.inputs['From Max'].default_value = 0.018
    L.new(edge.outputs[0], bund.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    L.new(bund.outputs[0], mx.inputs[0])
    L.new(m2.outputs[0], mx.inputs[6])
    mx.inputs[7].default_value = (0.20, 0.17, 0.11, 1)
    L.new(mx.outputs[2], p.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value = 0.78
    rr.inputs['To Max'].default_value = 0.04
    L.new(flood.outputs[0], rr.inputs['Value'])
    rb = nt.nodes.new('ShaderNodeMath')
    rb.operation = 'MAXIMUM'
    L.new(rr.outputs[0], rb.inputs[0])
    L.new(bund.outputs[0], rb.inputs[1])
    L.new(rb.outputs[0], p.inputs['Roughness'])
    p.inputs['Specular IOR Level'].default_value = 0.4
    rows = nt.nodes.new('ShaderNodeTexWave')                 # transplanted rows along each plot
    rows.wave_type = 'BANDS'
    rows.bands_direction = 'X'
    rows.inputs['Scale'].default_value = 0.9
    rows.inputs['Distortion'].default_value = 1.5
    rows.inputs['Detail Scale'].default_value = 0.4
    rr2 = nt.nodes.new('ShaderNodeMapping')
    rr2.inputs['Rotation'].default_value = (0, 0, math.radians(7))
    rr2.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    L.new(geo.outputs['Position'], rr2.inputs['Vector'])
    L.new(rr2.outputs[0], rows.inputs['Vector'])
    rm = nt.nodes.new('ShaderNodeMapRange')
    rm.inputs['To Min'].default_value = 0.72
    rm.inputs['To Max'].default_value = 1.12
    L.new(rows.outputs['Fac'], rm.inputs['Value'])
    rmx = nt.nodes.new('ShaderNodeMix')
    rmx.data_type = 'RGBA'
    rmx.blend_type = 'MULTIPLY'
    rmx.inputs[0].default_value = 1.0
    L.new(mx.outputs[2], rmx.inputs[6])
    rc = nt.nodes.new('ShaderNodeCombineXYZ')
    for k in range(3):
        L.new(rm.outputs[0], rc.inputs[k])
    L.new(rc.outputs[0], rmx.inputs[7])
    L.new(rmx.outputs[2], p.inputs['Base Color'])
    vb.inputs['To Min'].default_value = 0.62
    vb.inputs['To Max'].default_value = 1.3
    big.inputs['Scale'].default_value = 0.012
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.35
    L.new(fine.outputs['Fac'], bp.inputs['Height'])
    bp2 = nt.nodes.new('ShaderNodeBump')
    bp2.inputs['Strength'].default_value = 0.3
    L.new(rows.outputs['Fac'], bp2.inputs['Height'])
    L.new(bp.outputs[0], bp2.inputs['Normal'])
    L.new(bp2.outputs[0], p.inputs['Normal'])
    return m


def groves(C, rnd, n_clusters=70):
    """Coconut groves in the paddy, canals with a mangrove edge north and west of the farm."""
    VG = veg()
    xa, xb = X0 - PX / 2, X0 + (NCOL - 0.5) * PX
    yb = ROAD + NROW * PY
    g = TOP - 0.3
    for k in range(n_clusters):
        side = k % 3
        if side == 0:
            cx, cy = rnd.uniform(xa - 300, xb + 300), rnd.uniform(yb + 110, yb + 600)
        elif side == 1:
            cx, cy = rnd.uniform(xa - 600, xa - 90), rnd.uniform(-500, yb + 500)
        else:
            cx, cy = rnd.uniform(xa - 300, xb + 300), -rnd.uniform(yb + 70, yb + 500)
        r = rnd.uniform(18, 40)
        for _ in range(int(r * 0.8)):
            a, d = rnd.uniform(0, 6.28), r * math.sqrt(rnd.random())
            mesh = rnd.choice(VG['palms']) if rnd.random() < 0.75 else rnd.choice(VG['trees'] + VG['shrubs'])
            place(mesh, 'VEG_Grove', (cx + math.cos(a) * d, cy + math.sin(a) * d, g), rnd.uniform(0.8, 1.35), C, rnd)
    wm = water_mat()
    mang = V.shrub_mesh().copy()
    mang.name = 'VEG_MangroveMesh'
    mang.materials[0] = V._leaf_mat('VEG_Mangrove', (0.03, 0.075, 0.028), trans=0.2)
    p = Part()
    yc, xc = yb + 72, xa - 58
    p.box(((xa + xb) / 2, yc, g + 0.02), (3000, 16, 0.02))
    p.box((xc, 0, g + 0.02), (14, 3000, 0.02))
    p.make('FARM_Canal', wm, None, coll=C)
    for x in range(-1400, 1400, 4):
        for row in range(2):
            V.place(mang, 'VEG_Mangrove', (x + rnd.uniform(-2, 2), yc + 9.5 + row * 3.5 + rnd.uniform(-1, 1), g),
                    rnd.uniform(2.6, 4.2), coll=C, rnd=rnd)
    for y in range(-1400, 1400, 4):
        for row in range(2):
            V.place(mang, 'VEG_Mangrove', (xc - 8.5 - row * 3.5 + rnd.uniform(-1, 1), y + rnd.uniform(-2, 2), g),
                    rnd.uniform(2.6, 4.2), coll=C, rnd=rnd)


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
    cr.elements[0].color = (0.02, 0.06, 0.032, 1)        # algae green
    cr.elements[1].color = (0.05, 0.055, 0.03, 1)        # olive / tea
    for pos, col in ((0.2, (0.035, 0.095, 0.06)), (0.4, (0.025, 0.065, 0.055)), (0.6, (0.06, 0.065, 0.04)),
                     (0.8, (0.03, 0.05, 0.05))):          # bloom green, blue-green, khaki, deep teal
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    L.new(at.outputs['Fac'], ramp.inputs[0])
    # shallows: the water over the slope near the shore is muddy and lighter (distance to the quad edge, metres)
    al = nt.nodes.new('ShaderNodeAttribute')
    al.attribute_name = 'loc'
    al.attribute_type = 'GEOMETRY'
    ah = nt.nodes.new('ShaderNodeAttribute')
    ah.attribute_name = 'half'
    ah.attribute_type = 'GEOMETRY'
    ab = nt.nodes.new('ShaderNodeVectorMath')
    ab.operation = 'ABSOLUTE'
    L.new(al.outputs['Vector'], ab.inputs[0])
    sb = nt.nodes.new('ShaderNodeVectorMath')
    sb.operation = 'SUBTRACT'
    L.new(ah.outputs['Vector'], sb.inputs[0])
    L.new(ab.outputs[0], sb.inputs[1])
    sp = nt.nodes.new('ShaderNodeSeparateXYZ')
    L.new(sb.outputs[0], sp.inputs[0])
    dmin = nt.nodes.new('ShaderNodeMath')
    dmin.operation = 'MINIMUM'
    L.new(sp.outputs[0], dmin.inputs[0])
    L.new(sp.outputs[1], dmin.inputs[1])
    sh = nt.nodes.new('ShaderNodeMapRange')
    sh.name = 'Shallow'
    sh.inputs['From Min'].default_value = 2.9          # shoreline sits ~2.9 m inside the quad edge
    sh.inputs['From Max'].default_value = 6.0
    sh.inputs['To Min'].default_value = 0.6
    sh.inputs['To Max'].default_value = 0.0
    L.new(dmin.outputs[0], sh.inputs['Value'])
    smx = nt.nodes.new('ShaderNodeMix')
    smx.data_type = 'RGBA'
    smx.name = 'ShallowMix'
    L.new(sh.outputs[0], smx.inputs[0])
    L.new(ramp.outputs[0], smx.inputs[6])
    smx.inputs[7].default_value = (0.14, 0.115, 0.075, 1)
    L.new(smx.outputs[2], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.075
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
    b.inputs['Strength'].default_value = 0.03
    b.inputs['Distance'].default_value = 0.05
    L.new(nz.outputs['Fac'], b.inputs['Height'])
    # wind ripples: fine wavelets stretched across the wind, in patches (cat's paws)
    mp2 = nt.nodes.new('ShaderNodeMapping')
    mp2.inputs['Scale'].default_value = (1.0, 3.2, 1.0)
    L.new(mp.outputs[0], mp2.inputs['Vector'])
    fn = nt.nodes.new('ShaderNodeTexNoise')
    fn.inputs['Scale'].default_value = 7.0
    fn.inputs['Detail'].default_value = 4
    fn.inputs['Roughness'].default_value = 0.55
    L.new(mp2.outputs[0], fn.inputs['Vector'])
    pw = nt.nodes.new('ShaderNodeTexNoise')
    pw.inputs['Scale'].default_value = 0.05
    L.new(mp.outputs[0], pw.inputs['Vector'])
    pm = nt.nodes.new('ShaderNodeMapRange')
    pm.inputs['From Min'].default_value = 0.42
    pm.inputs['From Max'].default_value = 0.62
    pm.inputs['To Min'].default_value = 0.25
    pm.inputs['To Max'].default_value = 1.0
    L.new(pw.outputs['Fac'], pm.inputs['Value'])
    b2 = nt.nodes.new('ShaderNodeBump')
    b2.inputs['Distance'].default_value = 0.012
    L.new(pm.outputs[0], b2.inputs['Strength'])
    L.new(fn.outputs['Fac'], b2.inputs['Height'])
    L.new(b.outputs[0], b2.inputs['Normal'])
    rmul = nt.nodes.new('ShaderNodeMath')
    rmul.operation = 'MULTIPLY'
    rmul.inputs[1].default_value = 0.09
    L.new(pm.outputs[0], rmul.inputs[0])
    radd = nt.nodes.new('ShaderNodeMath')
    radd.operation = 'ADD'
    radd.name = 'RoughAdd'
    radd.inputs[1].default_value = 0.035
    L.new(rmul.outputs[0], radd.inputs[0])
    L.new(radd.outputs[0], p.inputs['Roughness'])
    sb2 = nt.nodes.new('ShaderNodeMath')               # shallows a little less glossy
    sb2.operation = 'MULTIPLY'
    sb2.inputs[1].default_value = 0.12
    L.new(sh.outputs[0], sb2.inputs[0])
    L.new(sb2.outputs[0], radd.inputs[1])
    L.new(b2.outputs[0], p.inputs['Normal'])
    return m


def build_water(C):
    verts, faces, tints, locs, halves = [], [], [], [], []
    for i in range(NCOL):
        for j in range(-NROW, NROW):
            if not in_farm(i, j):
                continue
            _, _, cx, cy = cell_of(X0 + i * PX, (ROAD + (j + 0.5) * PY) if j >= 0 else -(ROAD + (-1 - j + 0.5) * PY))
            hw, hh = pond_size(i, j)
            k = len(verts)
            ex, ey = hw + SLOPE * 0.6, hh + SLOPE * 0.6
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append((cx + sx * ex, cy + sy * ey, WATER))
                locs.append((sx * ex, sy * ey, 0.0))
                halves.append((ex, ey, 0.0))
            faces.append((k, k + 1, k + 2, k + 3))
            tints.append(pond_rand(i, j, 4))
    me = bpy.data.meshes.new('FARM_WaterMesh')
    me.from_pydata(verts, [], faces)
    at = me.attributes.new('tint', 'FLOAT', 'FACE')
    at.data.foreach_set('value', tints)
    for nm, vals in (('loc', locs), ('half', halves)):
        a2 = me.attributes.new(nm, 'FLOAT_VECTOR', 'CORNER')
        for li, lp in enumerate(me.loops):
            a2.data[li].vector = vals[lp.vertex_index]
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
    mp.inputs['Scale'].default_value = (1.0, 0.3, 1.0)          # streaks along the trail
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    om = nt.nodes.new('ShaderNodeVectorMath')
    om.operation = 'SCALE'
    om.inputs['Scale'].default_value = 37.0
    L.new(oi.outputs['Random'], om.inputs[0])
    ad = nt.nodes.new('ShaderNodeVectorMath')
    L.new(tc.outputs['UV'], ad.inputs[0])
    L.new(om.outputs[0], ad.inputs[1])
    L.new(ad.outputs[0], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.6
    nz.inputs['Detail'].default_value = 12
    nz.inputs['Roughness'].default_value = 0.7
    L.new(mp.outputs[0], nz.inputs['Vector'])
    # trail falloff: dense at the wheels (tn 0), thinning and breaking up downstream, soft at the sides
    atn = nt.nodes.new('ShaderNodeAttribute')
    atn.attribute_name = 'tn'
    atn.attribute_type = 'GEOMETRY'
    avn = nt.nodes.new('ShaderNodeAttribute')
    avn.attribute_name = 'vn'
    avn.attribute_type = 'GEOMETRY'
    vv = nt.nodes.new('ShaderNodeMath')
    vv.operation = 'POWER'
    vv.inputs[1].default_value = 2.0
    av = nt.nodes.new('ShaderNodeMath')
    av.operation = 'ABSOLUTE'
    L.new(avn.outputs['Fac'], av.inputs[0])
    L.new(av.outputs[0], vv.inputs[0])
    cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    L.new(vv.outputs[0], cmb.inputs[0])
    L.new(atn.outputs['Fac'], cmb.inputs[1])
    ln = nt.nodes.new('ShaderNodeVectorMath')
    ln.operation = 'LENGTH'
    L.new(cmb.outputs[0], ln.inputs[0])
    fall = nt.nodes.new('ShaderNodeMapRange')
    fall.inputs['From Min'].default_value = 1.05
    fall.inputs['From Max'].default_value = 0.0
    L.new(ln.outputs['Value'], fall.inputs['Value'])
    thr = nt.nodes.new('ShaderNodeMapRange')
    thr.inputs['From Min'].default_value = 0.34
    thr.inputs['From Max'].default_value = 0.5
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
    core.inputs['From Min'].default_value = 0.16
    core.inputs['From Max'].default_value = 0.04
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
    return C


def foam_trail(name, C, rnd, length, bend, spread):
    """Churned white water at the wheels decaying into a curved trail (aerator space: wheels on X, flow +Y).
    UV = metres (x across, y along) for the drifting noise; attribute 'tn' = 0..1 along, 'vn' = -1..1 across."""
    nu, nv = 6, 28
    bm = bmesh.new()
    R = length / max(1e-3, abs(bend)) if bend else None
    grid = []
    for j in range(nv + 1):
        t = j / nv
        sl = length * (t ** 1.3)
        if R:
            a = sl / R
            cx_, cy_ = (R * (1 - math.cos(a))) * (1 if bend > 0 else -1), R * math.sin(a)
            tx, ty = math.sin(a) * (1 if bend > 0 else -1), math.cos(a)
        else:
            cx_, cy_, tx, ty = 0.0, sl, 0.0, 1.0
        hw = 1.35 + spread * t ** 0.8
        row = []
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            row.append(bm.verts.new((cx_ + ty * u * hw, -0.9 + cy_ - tx * u * hw, 0.03)))
        grid.append((row, t, sl))
    faces = []
    for j in range(nv):
        for i in range(nu):
            faces.append(bm.faces.new((grid[j][0][i], grid[j][0][i + 1], grid[j + 1][0][i + 1], grid[j + 1][0][i])))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    uv = me.uv_layers.new(name='UV')
    tn = me.attributes.new('tn', 'FLOAT', 'POINT')
    vn = me.attributes.new('vn', 'FLOAT', 'POINT')
    for j, (row, t, sl) in enumerate(grid):
        for i in range(nu + 1):
            k = j * (nu + 1) + i
            tn.data[k].value = t
            vn.data[k].value = -1 + 2 * i / nu
    for poly in me.polygons:
        for li in poly.loop_indices:
            k = me.loops[li].vertex_index
            j, i = divmod(k, nu + 1)
            row, t, sl = grid[j]
            uv.data[li].uv = ((-1 + 2 * i / nu) * (1.35 + spread * t ** 0.8), sl)
    me.materials.append(foam_mat())
    o = bpy.data.objects.new(name, me)
    C.objects.link(o)
    return o


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
                # its own churn trail: length fits the pond, curving with the pond's circulation
                room = (2 * hh - 9) if k < 2 else (2 * hw - 14)
                fo = foam_trail('AER_Foam_%d_%d_%d' % (i, j, k), C, rnd, min(room, rnd.uniform(7.5, 13.0)) / 1.3,
                                rnd.choice((-1, 1)) * rnd.uniform(0.25, 0.75), rnd.uniform(1.0, 2.6))
                fo.location = (x, y, WATER - 0.02)
                fo.rotation_euler = o.rotation_euler
                fo.scale = o.scale
    return out


def animate_water(f0, f1):
    """Drift the ripple and foam noise so the water and the churn move."""
    for mn, node, vel in (('FARM_PondWater', 'RippleMap', (0.35, 0.12, 0.0)), ('FARM_Foam', 'FoamMap', (0.0, 2.6, 0.6))):
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
def grass_tufts(C, rnd, x0, x1, y0, y1, step=1.1, p=0.4):
    """Clumps of blade cards on the bund tops and outer slopes (one joined mesh)."""
    bm = bmesh.new()
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            xx, yy = x + rnd.uniform(-0.5, 0.5), y + rnd.uniform(-0.5, 0.5)
            z = height(xx, yy)
            if z > WATER + 0.3 and abs(yy) > ROAD + 0.6 and rnd.random() < p:
                for _ in range(rnd.randint(5, 9)):
                    a = rnd.uniform(0, 6.28)
                    h = rnd.uniform(0.18, 0.42)
                    w = 0.025
                    d = Vector((math.cos(a), math.sin(a), 0))
                    side = Vector((-d.y, d.x, 0)) * w
                    base = Vector((xx + rnd.uniform(-0.12, 0.12), yy + rnd.uniform(-0.12, 0.12), z - 0.02))
                    tip = base + d * h * rnd.uniform(0.2, 0.5) + Vector((0, 0, h))
                    bm.faces.new([bm.verts.new(v) for v in (base - side, base + side, tip)])
            y += step
        x += step
    me = bpy.data.meshes.new('FARM_TuftMesh')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(V._leaf_mat('FARM_Grass', (0.11, 0.2, 0.045), trans=0.3))
    a = me.attributes.new('vcol', 'FLOAT_COLOR', 'POINT')
    for i in range(len(a.data)):
        k = rnd.uniform(0.7, 1.3)
        a.data[i].color = (k, k * rnd.uniform(0.9, 1.1), k * 0.8, 1)
    o = bpy.data.objects.new('FARM_Tufts', me)
    C.objects.link(o)
    return o


def footpaths(C, rnd, x0, x1):
    """Worn, compacted strips along the centre of the bunds between ponds."""
    import skplant
    p = Part()
    for i in range(NCOL + 1):
        x = X0 + (i - 0.5) * PX
        if x0 <= x <= x1:
            for j in range(-NROW, NROW):
                yc = (ROAD + (j + 0.5) * PY) if j >= 0 else -(ROAD + (-1 - j + 0.5) * PY)
                p.box((x + rnd.uniform(-0.3, 0.3), yc, TOP + 0.012), (0.7, PY * 0.9, 0.004))
    for j in range(1, NROW):
        for sg in (-1, 1):
            p.box(((x0 + x1) / 2, sg * (ROAD + j * PY), TOP + 0.012), (x1 - x0, 0.7, 0.004))
    p.make('FARM_Paths', skplant.line_mat('FARM_PathMat', (0.30, 0.25, 0.18), alpha=0.55), None, coll=C)


def feed_cart(name, C):
    """Two-wheel push cart with feed sacks; handle toward local +Y (the pusher), cart ahead along -Y."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    steel = P.grime_paint('FARM_CartSteel', (0.18, 0.2, 0.2), rough=0.5, grime=0.6, streak=0.4, coat=0.0, metal=0.5)
    p = Part()
    p.box((0, -1.1, 0.5), (0.8, 1.1, 0.04))
    for sx in (-0.4, 0.4):
        p.cyl((sx, -0.55, 0.5), (sx, 0.05, 0.95), 0.02, 8)
        p.box((sx, -1.1, 0.62), (0.03, 1.1, 0.25))
    p.cyl((-0.4, 0.05, 0.95), (0.4, 0.05, 0.95), 0.022, 8)
    p.cyl((-0.48, -1.2, 0.28), (0.48, -1.2, 0.28), 0.02, 8)
    p.make(name + '_Frame', steel, root, bevel=0.005, coll=C)
    p = Part()
    for sx in (-0.48, 0.48):
        p.cyl((sx - 0.04, -1.2, 0.28), (sx + 0.04, -1.2, 0.28), 0.28, 18)
    p.make(name + '_Wheels', P.plain('FARM_CartTyre', (0.03, 0.03, 0.03), 0.8), root, smooth=True, coll=C)
    p = Part()
    for k, (x, y, z) in enumerate(((-0.2, -0.85, 0.66), (0.2, -0.85, 0.66), (-0.2, -1.35, 0.66), (0.2, -1.35, 0.66),
                                   (0.0, -1.1, 0.88))):
        p.box((x, y, z), (0.38, 0.5, 0.22))
    p.make(name + '_Sacks', P.plain('FARM_Sack', (0.55, 0.47, 0.33), 0.9, bump=0.6, bump_scale=60), root, bevel=0.06,
           seg=3, coll=C)
    return root


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
    VG = veg()
    pm, pm2 = VG['palms'][0], VG['palms'][1]
    tm = VG['trees'][0]
    sm = VG['shrubs'][0]
    for x in range(-340, 460, 11):
        for side in (7.6, -7.6):
            if rnd.random() < 0.55:
                place(rnd.choice(VG['palms']), 'VEG_RoadPalm', (x + rnd.uniform(-3, 3), side + rnd.uniform(-1, 1), TOP),
                      rnd.uniform(0.75, 1.25), C, rnd, lean=0.14)
            elif rnd.random() < 0.18 and not (20 < x < 100):
                place(rnd.choice(VG['trees']), 'VEG_RoadTree', (x + rnd.uniform(-3, 3), side * 1.15, TOP),
                      rnd.uniform(0.8, 1.2), C, rnd)
            elif rnd.random() < 0.4 and not (20 < x < 100):
                place(rnd.choice(VG['shrubs']), 'VEG_RoadShrub', (x + rnd.uniform(-3, 3), side * 1.05, TOP),
                      rnd.uniform(0.6, 1.3), C, rnd)
    for k in range(26):
        place(rnd.choice(VG['palms'] + VG['trees'][:1]), 'VEG_YardPalm',
              (xm + rnd.uniform(-34, 34), ym + rnd.uniform(-20, 20), TOP), rnd.uniform(0.85, 1.25), C, rnd, lean=0.12)
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
        mesh = rnd.choice(VG['palms'] + VG['palms'] + VG['trees'] + VG['shrubs'])
        place(mesh, 'VEG_Belt', (x, y, TOP - 0.3), rnd.uniform(0.85, 1.4), C, rnd, lean=0.12)
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
