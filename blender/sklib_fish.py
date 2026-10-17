"""Photoreal product fish for the Products section (SCENES.md §12, ASSET_LIBRARY.md 'Products'): yellowfin tuna,
swordfish and raw Vannamei shrimp, plus the crushed-ice tray. High-resolution lofted bodies with real fin shapes
(fin rays), counter-shaded wet skin with scales/iridescence, real eyes and gill covers. Units: metres, head toward +X.
"""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
from sklib import new_mat, principled, _node, _sock, mixrgb, obj, bm_to_mesh, empty, pbr


def _interp(pts, t):
    """piecewise-smooth (cosine) interpolation over [(t, v)] sorted by t."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = (1 - math.cos(u * math.pi)) / 2
            return v0 + (v1 - v0) * u
    return pts[-1][1]


def loft(name, L, height, width, zc=None, n=96, seg=40, expo=None, groove=None, snout=None):
    """Body of revolution-ish: t 0 (tail base, x=0) -> 1 (snout, x=L). height/width: [(t, frac of L)].
    expo: [(t, superellipse exponent)] (2 = ellipse, <2 = boxier). groove: (t, depth) for the gill-cover line."""
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        t = i / n
        t = t ** 0.85  # more rings toward the head
        x = t * L
        h = _interp(height, t) * L
        w = _interp(width, t) * L
        z0 = _interp(zc, t) * L if zc else 0.0
        e = _interp(expo, t) if expo else 2.0
        if groove and abs(t - groove[0]) < 0.006:
            h *= 1 - groove[1]
            w *= 1 - groove[1]
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            ca, sa = math.cos(a), math.sin(a)
            y = w / 2 * math.copysign(abs(ca) ** (2 / e), ca)
            z = h / 2 * math.copysign(abs(sa) ** (2 / e), sa)
            if snout and t > snout[0]:
                # mouth: slight open line on the lower jaw near the snout
                pass
            ring.append(bm.verts.new((x, y, z0 + z)))
        rings.append(ring)
    for i in range(n):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % seg], rings[i][(j + 1) % seg]))
    tip = bm.verts.new((L * 1.003, 0, rings[-1][0].co.z * 0 + (_interp(zc, 1.0) * L if zc else 0.0)))
    for j in range(seg):
        bm.faces.new((rings[-1][j], rings[-1][(j + 1) % seg], tip))
    tail = bm.verts.new((-0.002 * L, 0, _interp(zc, 0.0) * L if zc else 0.0))
    for j in range(seg):
        bm.faces.new((rings[0][(j + 1) % seg], rings[0][j], tail))
    me = bm_to_mesh(bm, name, smooth=True)
    return me


def fin(name, outline, thickness=0.003, rays=True, z_curve=0.0, subdiv=2):
    """Flat fin from an outline [(x, z)] in the XZ plane (y = 0), slightly cambered, thin, subdivided for smoothness.
    Returns mesh. Fin ray bump comes from the fin material (wave along the local fin direction)."""
    bm = bmesh.new()
    vs = [bm.verts.new((p[0], 0.0, p[1])) for p in outline]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    for _ in range(subdiv):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    if z_curve:
        for v in bm.verts:
            v.co.y += z_curve * (v.co.x ** 2 + v.co.z ** 2)
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for g in ext['geom']:
        if isinstance(g, bmesh.types.BMVert):
            g.co.y += thickness
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_to_mesh(bm, name, smooth=True)


def fin_mat(name, color, edge=None, translucency=0.25, rough=0.35):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1000, 0))
    wv = _node(nt, 'ShaderNodeTexWave', (-800, -200))
    wv.wave_type = 'RINGS'
    wv.rings_direction = 'SPHERICAL'
    wv.inputs['Scale'].default_value = 1.0
    wv.inputs['Distortion'].default_value = 0.0
    # rays radiate from the fin base: use the angle around the fin root via a gradient on generated coordinates
    gr = _node(nt, 'ShaderNodeTexGradient', (-800, 100))
    gr.gradient_type = 'RADIAL'
    l.new(_sock(tc, 'Object', out=True), gr.inputs['Vector'])
    mth = _node(nt, 'ShaderNodeMath', (-600, 100))
    mth.operation = 'SINE'
    mm = _node(nt, 'ShaderNodeMath', (-700, 100))
    mm.operation = 'MULTIPLY'
    mm.inputs[1].default_value = 900.0
    l.new(_sock(gr, 'Factor', out=True), mm.inputs[0])
    l.new(mm.outputs[0], mth.inputs[0])
    b = _node(nt, 'ShaderNodeBump', (-300, -200))
    b.inputs['Strength'].default_value = 0.25
    b.inputs['Distance'].default_value = 0.001
    l.new(mth.outputs[0], b.inputs['Height'])
    l.new(b.outputs[0], p.inputs['Normal'])
    col = color
    p.inputs['Base Color'].default_value = (*col, 1)
    if edge:
        # darker toward the fin edge: distance from object origin (fin root) in the fin plane
        sep = _node(nt, 'ShaderNodeVectorMath', (-700, 400))
        sep.operation = 'LENGTH'
        l.new(_sock(tc, 'Object', out=True), sep.inputs[0])
        mr = _node(nt, 'ShaderNodeMapRange', (-500, 400))
        mr.inputs['From Min'].default_value = edge[1] * 0.6
        mr.inputs['From Max'].default_value = edge[1]
        l.new(_sock(sep, 'Value', out=True), mr.inputs['Value'])
        c = mixrgb(nt, mr.outputs[0], color, edge[0], loc=(-200, 300))
        l.new(c, p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = 0.6
    p.inputs['Coat Roughness'].default_value = 0.05
    p.inputs['Subsurface Weight'].default_value = translucency
    p.inputs['Subsurface Radius'].default_value = (0.004, 0.003, 0.002)
    p.inputs['Transmission Weight'].default_value = translucency * 0.5
    return m


def skin_mat(name, L, back, mid, belly, band=None, sheen=None, film=350.0, scales=True, spots=False, metal=0.65):
    """Counter-shaded wet fish skin by object height, iridescent thin film, scale micro-normal, optional faint
    vertical belly bands (tuna) and a yellow lateral sheen."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (-1400, 0))
    l.new(_sock(tc, 'Object', out=True), sep.inputs[0])
    ramp = _node(nt, 'ShaderNodeValToRGB', (-1000, 200))
    mr = _node(nt, 'ShaderNodeMapRange', (-1200, 200))
    mr.inputs['From Min'].default_value = -0.12 * L
    mr.inputs['From Max'].default_value = 0.12 * L
    # wavy counter-shading boundary
    nz = _node(nt, 'ShaderNodeTexNoise', (-1400, 400))
    nz.inputs['Scale'].default_value = 6.0 / L
    nz.inputs['Detail'].default_value = 4
    l.new(_sock(tc, 'Object', out=True), nz.inputs['Vector'])
    ad = _node(nt, 'ShaderNodeMath', (-1300, 300))
    ad.operation = 'MULTIPLY_ADD'
    ad.inputs[1].default_value = 0.02 * L
    l.new(_sock(nz, 'Factor', out=True), ad.inputs[0])
    l.new(sep.outputs[2], ad.inputs[2])
    l.new(ad.outputs[0], mr.inputs['Value'])
    l.new(mr.outputs[0], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*belly, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (*back, 1)
    e = cr.elements.new(0.5)
    e.color = (*mid, 1)
    e2 = cr.elements.new(0.62)
    e2.color = tuple(0.5 * a + 0.5 * b for a, b in zip(mid, back)) + (1,)
    col = _sock(ramp, 'Color', out=True)
    if sheen:
        # lateral band (yellowfin): subtle golden sheen along the mid-flank
        g1 = _node(nt, 'ShaderNodeMapRange', (-1000, -200))
        g1.interpolation_type = 'SMOOTHERSTEP'
        g1.inputs['From Min'].default_value = sheen[0] - sheen[1]
        g1.inputs['From Max'].default_value = sheen[0]
        l.new(sep.outputs[2], g1.inputs['Value'])
        g2 = _node(nt, 'ShaderNodeMapRange', (-1000, -400))
        g2.interpolation_type = 'SMOOTHERSTEP'
        g2.inputs['From Min'].default_value = sheen[0] + sheen[1]
        g2.inputs['From Max'].default_value = sheen[0]
        l.new(sep.outputs[2], g2.inputs['Value'])
        mlt = _node(nt, 'ShaderNodeMath', (-800, -300))
        mlt.operation = 'MULTIPLY'
        l.new(g1.outputs[0], mlt.inputs[0])
        l.new(g2.outputs[0], mlt.inputs[1])
        mlt2 = _node(nt, 'ShaderNodeMath', (-700, -300))
        mlt2.operation = 'MULTIPLY'
        mlt2.inputs[1].default_value = sheen[3]
        l.new(mlt.outputs[0], mlt2.inputs[0])
        col = mixrgb(nt, mlt2.outputs[0], col, sheen[2], loc=(-500, -100))
    if band:
        # faint vertical bands / spot rows on the lower flank
        wv = _node(nt, 'ShaderNodeTexWave', (-1000, -600))
        wv.bands_direction = 'X'
        wv.inputs['Scale'].default_value = band[0] / L
        wv.inputs['Distortion'].default_value = 3.0
        wv.inputs['Detail'].default_value = 2.0
        l.new(_sock(tc, 'Object', out=True), wv.inputs['Vector'])
        bz = _node(nt, 'ShaderNodeMapRange', (-800, -700))
        bz.inputs['From Min'].default_value = 0.02 * L
        bz.inputs['From Max'].default_value = -0.08 * L
        l.new(sep.outputs[2], bz.inputs['Value'])
        bm_ = _node(nt, 'ShaderNodeMath', (-650, -650))
        bm_.operation = 'MULTIPLY'
        l.new(_sock(wv, 'Factor', out=True), bm_.inputs[0])
        l.new(bz.outputs[0], bm_.inputs[1])
        bm2 = _node(nt, 'ShaderNodeMath', (-550, -650))
        bm2.operation = 'MULTIPLY'
        bm2.inputs[1].default_value = band[1]
        l.new(bm_.outputs[0], bm2.inputs[0])
        col = mixrgb(nt, bm2.outputs[0], col, (0.55, 0.6, 0.68), loc=(-350, -300))
    l.new(col, p.inputs['Base Color'])
    # metallic sheen on the silver belly, less on the dark back
    mm = _node(nt, 'ShaderNodeMapRange', (-500, 600))
    mm.inputs['To Min'].default_value = metal
    mm.inputs['To Max'].default_value = metal * 0.55
    l.new(mr.outputs[0], mm.inputs['Value'])
    l.new(mm.outputs[0], p.inputs['Metallic'])
    p.inputs['Roughness'].default_value = 0.22
    p.inputs['Coat Weight'].default_value = 0.8
    p.inputs['Coat Roughness'].default_value = 0.04
    if film:
        p.inputs['Thin Film Thickness'].default_value = film
        p.inputs['Thin Film IOR'].default_value = 1.4
    if scales:
        vor = _node(nt, 'ShaderNodeTexVoronoi', (-700, -1000))
        vor.inputs['Scale'].default_value = 140.0 / L
        vor.feature = 'DISTANCE_TO_EDGE'
        mp = _node(nt, 'ShaderNodeMapping', (-900, -1000))
        mp.inputs['Scale'].default_value = (1.0, 1.6, 1.6)
        l.new(_sock(tc, 'Object', out=True), mp.inputs['Vector'])
        l.new(mp.outputs[0], vor.inputs['Vector'])
        b = _node(nt, 'ShaderNodeBump', (-300, -1000))
        b.inputs['Strength'].default_value = 0.12
        b.inputs['Distance'].default_value = 0.0006 * L
        l.new(_sock(vor, 'Distance', out=True), b.inputs['Height'])
        l.new(b.outputs[0], p.inputs['Normal'])
    else:
        nz2 = _node(nt, 'ShaderNodeTexNoise', (-700, -1000))
        nz2.inputs['Scale'].default_value = 90.0 / L
        nz2.inputs['Detail'].default_value = 10
        l.new(_sock(tc, 'Object', out=True), nz2.inputs['Vector'])
        b = _node(nt, 'ShaderNodeBump', (-300, -1000))
        b.inputs['Strength'].default_value = 0.2
        b.inputs['Distance'].default_value = 0.0008 * L
        l.new(_sock(nz2, 'Factor', out=True), b.inputs['Height'])
        l.new(b.outputs[0], p.inputs['Normal'])
    return m


def eye(name, r, parent, loc, side):
    """Real fish eye: dark glossy pupil, metallic iris ring, clear cornea dome."""
    ir = pbr('MAT_FishIris', (0.55, 0.5, 0.35), 0.25, 0.8, var=0.3, bump=0.2, scale=60)
    pu = pbr('MAT_FishPupil', (0.005, 0.005, 0.006), 0.05, var=0.0, bump=0.0)
    co = new_mat('MAT_FishCornea') if 'MAT_FishCornea' not in bpy.data.materials else bpy.data.materials['MAT_FishCornea']
    p = principled(co)
    p.inputs['Roughness'].default_value = 0.0
    p.inputs['Transmission Weight'].default_value = 1.0
    p.inputs['IOR'].default_value = 1.38
    root = empty(name, loc, parent=parent, size=r)
    root.rotation_euler = (math.radians(90) * side, 0, 0)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    for v in bm.verts:
        v.co.z *= 0.45
    me = bm_to_mesh(bm, f'{name}_iris', smooth=True)
    me.materials.append(ir)
    obj(f'{name}_iris', me, None, parent=root)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=r * 0.5)
    for v in bm.verts:
        v.co.z = v.co.z * 0.3 + r * 0.33
    me = bm_to_mesh(bm, f'{name}_pupil', smooth=True)
    me.materials.append(pu)
    obj(f'{name}_pupil', me, None, parent=root)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r * 1.05)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0], context='VERTS')
    for v in bm.verts:
        v.co.z = v.co.z * 0.55 + r * 0.12
    me = bm_to_mesh(bm, f'{name}_cornea', smooth=True)
    me.materials.append(co)
    obj(f'{name}_cornea', me, None, parent=root)
    return root


def _place_fin(name, me, mat, parent, loc, rot=(0, 0, 0), scale=1.0):
    me.materials.append(mat)
    return obj(name, me, None, loc, rot, (scale, scale, scale), parent=parent)


def tuna(name='PROD_Tuna', L=1.1, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Yellowfin tuna, fork length L (tail base at x=0, snout at x=L)."""
    root = empty(name, loc, size=0.2)
    root.rotation_euler = rot
    H = [(0.0, 0.045), (0.06, 0.055), (0.15, 0.1), (0.3, 0.19), (0.48, 0.255), (0.6, 0.265), (0.72, 0.24), (0.82, 0.2),
         (0.9, 0.15), (0.96, 0.085), (1.0, 0.012)]
    Wd = [(0.0, 0.07), (0.06, 0.06), (0.15, 0.075), (0.3, 0.13), (0.48, 0.17), (0.6, 0.175), (0.72, 0.165), (0.82, 0.14),
          (0.9, 0.11), (0.96, 0.065), (1.0, 0.01)]
    Z = [(0.0, 0.0), (0.5, 0.004), (0.85, 0.01), (1.0, 0.012)]
    E = [(0.0, 2.6), (0.4, 2.1), (1.0, 2.0)]
    me = loft(f'{name}_Body', L, H, Wd, Z, n=120, seg=48, expo=E, groove=(0.83, 0.02))
    me.materials.append(skin_mat('MAT_Tuna_Skin', L, back=(0.01, 0.02, 0.055), mid=(0.12, 0.17, 0.26), belly=(0.74, 0.76, 0.78),
                                 band=(26.0, 0.35), sheen=(0.012 * L, 0.012 * L, (0.85, 0.62, 0.1), 0.45), film=380))
    body = obj(f'{name}_Body', me, None, parent=root)
    yel = fin_mat('MAT_Tuna_FinYellow', (0.86, 0.62, 0.06), edge=((0.25, 0.2, 0.08), 0.2 * L), translucency=0.3)
    dark = fin_mat('MAT_Tuna_FinDark', (0.04, 0.05, 0.08), edge=((0.02, 0.02, 0.03), 0.2 * L), translucency=0.15)
    # caudal fin: tall lunate tail
    cf = [(0.0, 0.02), (-0.05, 0.1), (-0.1, 0.17), (-0.16, 0.24), (-0.15, 0.19), (-0.1, 0.1), (-0.07, 0.03), (-0.065, 0.0),
          (-0.07, -0.03), (-0.1, -0.1), (-0.15, -0.19), (-0.16, -0.24), (-0.1, -0.17), (-0.05, -0.1), (0.0, -0.02), (0.02, 0)]
    _place_fin(f'{name}_Caudal', fin(f'{name}_CaudalM', [(x * L, z * L) for x, z in cf], 0.004 * L), dark, root, (0.005 * L, -0.002 * L, 0))
    # first dorsal (dark, foldable) and long sickle second dorsal + anal (yellow)
    d1 = [(0.0, 0.0), (0.03, 0.08), (0.06, 0.09), (0.12, 0.03), (0.16, 0.0)]
    _place_fin(f'{name}_Dorsal1', fin(f'{name}_D1M', [(x * L, z * L) for x, z in d1], 0.003 * L), dark, root,
               (0.55 * L, -0.0015 * L, 0.128 * L), (0, 0, math.pi))
    d2 = [(0.0, 0.0), (0.02, 0.09), (0.0, 0.2), (0.03, 0.12), (0.065, 0.0)]
    _place_fin(f'{name}_Dorsal2', fin(f'{name}_D2M', [(x * L, z * L) for x, z in d2], 0.003 * L), yel, root,
               (0.47 * L, -0.0015 * L, 0.115 * L), (0, 0, math.pi))
    _place_fin(f'{name}_Anal', fin(f'{name}_AnM', [(x * L, -z * L) for x, z in d2], 0.003 * L), yel, root,
               (0.46 * L, -0.0015 * L, -0.115 * L), (0, 0, math.pi))
    # finlets: 8 dorsal, 7 ventral, yellow with dark tips
    fl = [(0.0, 0.0), (0.006, 0.02), (0.02, 0.022), (0.026, 0.0)]
    for k in range(8):
        x = (0.12 + k * 0.034) * L
        hz = _interp(H, x / L) * L / 2
        _place_fin(f'{name}_FinletD{k}', fin(f'{name}_FlD{k}', [(a * L, b * L) for a, b in fl], 0.002 * L, subdiv=1), yel, root,
                   (x, -0.001 * L, hz * 0.97), (0, 0, math.pi))
        if k < 7:
            _place_fin(f'{name}_FinletV{k}', fin(f'{name}_FlV{k}', [(a * L, -b * L) for a, b in fl], 0.002 * L, subdiv=1), yel, root,
                       (x, -0.001 * L, -hz * 0.97), (0, 0, math.pi))
    # long pectoral fins (yellowfin) and small pelvics
    pf = [(0.0, 0.0), (0.0, 0.03), (-0.1, 0.02), (-0.24, -0.02), (-0.12, -0.012), (-0.03, -0.012)]
    for side in (1, -1):
        hy = _interp(Wd, 0.78) * L / 2
        _place_fin(f'{name}_Pectoral{side}', fin(f'{name}_PecM{side}', [(x * L, z * L) for x, z in pf], 0.003 * L, z_curve=side * 0.4),
                   dark, root, (0.78 * L, side * hy * 0.95, -0.01 * L), (math.radians(-side * 70), 0, math.radians(side * 8)))
        _place_fin(f'{name}_Pelvic{side}', fin(f'{name}_PelM{side}', [(x * L * 0.35, z * L * 0.35) for x, z in pf], 0.002 * L),
                   dark, root, (0.74 * L, side * 0.03 * L, -0.11 * L), (math.radians(-side * 30), 0, 0))
        eye(f'{name}_Eye{side}', 0.022 * L, root, (0.925 * L, side * _interp(Wd, 0.925) * L / 2 * 0.92, 0.022 * L), side)
    return root


def swordfish(name='PROD_Swordfish', L=1.6, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Swordfish: body length L from tail base to the eye/jaw, plus a flat bill about a third of the total length."""
    root = empty(name, loc, size=0.2)
    root.rotation_euler = rot
    H = [(0.0, 0.04), (0.08, 0.05), (0.2, 0.09), (0.4, 0.15), (0.6, 0.18), (0.75, 0.175), (0.88, 0.14), (0.95, 0.1), (1.0, 0.05)]
    Wd = [(0.0, 0.08), (0.08, 0.06), (0.2, 0.08), (0.4, 0.13), (0.6, 0.155), (0.75, 0.15), (0.88, 0.12), (0.95, 0.085), (1.0, 0.04)]
    Z = [(0.0, 0.0), (0.7, 0.004), (1.0, 0.01)]
    me = loft(f'{name}_Body', L, H, Wd, Z, n=110, seg=44, expo=[(0.0, 2.2), (1.0, 2.0)], groove=(0.9, 0.02))
    me.materials.append(skin_mat('MAT_Swordfish_Skin', L, back=(0.09, 0.055, 0.03), mid=(0.3, 0.22, 0.15), belly=(0.62, 0.6, 0.56),
                                 film=180, scales=False, metal=0.35))
    obj(f'{name}_Body', me, None, parent=root)
    # bill: flat, sword-like, about a third of total length
    bl = 0.5 * L
    bm = bmesh.new()
    n = 30
    rings = []
    for i in range(n + 1):
        t = i / n
        w = 0.06 * L * (1 - t) ** 0.9 + 0.002 * L
        h = 0.022 * L * (1 - t) ** 1.1 + 0.001 * L
        ring = []
        for j in range(16):
            a = 2 * math.pi * j / 16
            ring.append(bm.verts.new((L * 0.985 + t * bl, w / 2 * math.cos(a), 0.012 * L + h / 2 * math.sin(a) - 0.01 * L * t)))
        rings.append(ring)
    for i in range(n):
        for j in range(16):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % 16], rings[i][(j + 1) % 16]))
    bme = bm_to_mesh(bm, f'{name}_Bill', smooth=True)
    bme.materials.append(pbr('MAT_Swordfish_Bill', (0.12, 0.09, 0.07), 0.3, var=0.2, bump=0.3, scale=40, coat=0.6))
    obj(f'{name}_Bill', bme, None, parent=root)
    dark = fin_mat('MAT_Swordfish_Fin', (0.07, 0.05, 0.04), edge=((0.03, 0.02, 0.02), 0.2 * L), translucency=0.12)
    cf = [(0.0, 0.02), (-0.06, 0.1), (-0.13, 0.2), (-0.17, 0.25), (-0.15, 0.2), (-0.1, 0.09), (-0.07, 0.0), (-0.1, -0.09),
          (-0.15, -0.2), (-0.17, -0.25), (-0.13, -0.2), (-0.06, -0.1), (0.0, -0.02), (0.02, 0)]
    _place_fin(f'{name}_Caudal', fin(f'{name}_CaudalM', [(x * L, z * L) for x, z in cf], 0.004 * L), dark, root, (0.005 * L, -0.002 * L, 0))
    d1 = [(0.0, 0.0), (0.0, 0.08), (0.015, 0.17), (0.05, 0.13), (0.08, 0.05), (0.18, 0.02), (0.2, 0.0)]
    _place_fin(f'{name}_Dorsal1', fin(f'{name}_D1M', [(-x * L, z * L) for x, z in d1], 0.004 * L), dark, root,
               (0.82 * L, -0.002 * L, 0.085 * L))
    small = [(0.0, 0.0), (0.01, 0.04), (0.035, 0.0)]
    _place_fin(f'{name}_Dorsal2', fin(f'{name}_D2M', [(x * L, z * L) for x, z in small], 0.003 * L), dark, root,
               (0.1 * L, -0.0015 * L, 0.045 * L), (0, 0, math.pi))
    for zsg in (-1,):
        _place_fin(f'{name}_Anal1', fin(f'{name}_A1M', [(-x * L * 0.7, -z * L * 0.6) for x, z in d1], 0.003 * L), dark, root,
                   (0.4 * L, -0.0015 * L, -0.085 * L))
    pf = [(0.0, 0.0), (0.0, 0.025), (-0.08, 0.0), (-0.2, -0.05), (-0.1, -0.02), (-0.03, -0.012)]
    for side in (1, -1):
        hy = _interp(Wd, 0.82) * L / 2
        _place_fin(f'{name}_Pectoral{side}', fin(f'{name}_PecM{side}', [(x * L, z * L) for x, z in pf], 0.003 * L, z_curve=side * 0.3),
                   dark, root, (0.82 * L, side * hy * 0.92, -0.04 * L), (math.radians(-side * 75), 0, math.radians(side * 12)))
        eye(f'{name}_Eye{side}', 0.026 * L, root, (0.955 * L, side * _interp(Wd, 0.955) * L / 2 * 0.9, 0.018 * L), side)
    # caudal keel on the peduncle
    bk = bmesh.new()
    bmesh.ops.create_uvsphere(bk, u_segments=16, v_segments=8, radius=1.0)
    for v in bk.verts:
        v.co = Vector((v.co.x * 0.06 * L, v.co.y * 0.05 * L, v.co.z * 0.012 * L))
    km = bm_to_mesh(bk, f'{name}_Keel', smooth=True)
    km.materials.append(bpy.data.materials['MAT_Swordfish_Skin'])
    obj(f'{name}_Keel', km, None, (0.05 * L, 0, 0), parent=root)
    return root


def shrimp_mat():
    if 'MAT_Vannamei' in bpy.data.materials:
        return bpy.data.materials['MAT_Vannamei']
    m = new_mat('MAT_Vannamei')
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    p.inputs['Base Color'].default_value = (0.62, 0.64, 0.64, 1)
    p.inputs['Roughness'].default_value = 0.18
    p.inputs['Subsurface Weight'].default_value = 0.7
    p.inputs['Subsurface Radius'].default_value = (0.004, 0.0035, 0.003)
    p.inputs['Subsurface Scale'].default_value = 0.6
    p.inputs['Transmission Weight'].default_value = 0.25
    p.inputs['Coat Weight'].default_value = 0.9
    p.inputs['Coat Roughness'].default_value = 0.03
    tc = _node(nt, 'ShaderNodeTexCoord', (-1000, 0))
    nz = _node(nt, 'ShaderNodeTexNoise', (-800, 200))
    nz.inputs['Scale'].default_value = 120.0
    nz.inputs['Detail'].default_value = 6
    l.new(_sock(tc, 'Object', out=True), nz.inputs['Vector'])
    col = mixrgb(nt, _sock(nz, 'Factor', out=True), (0.7, 0.72, 0.72), (0.42, 0.45, 0.5), loc=(-400, 200))
    l.new(col, p.inputs['Base Color'])
    b = _node(nt, 'ShaderNodeBump', (-300, -200))
    b.inputs['Strength'].default_value = 0.1
    b.inputs['Distance'].default_value = 0.0003
    l.new(_sock(nz, 'Factor', out=True), b.inputs['Height'])
    l.new(b.outputs[0], p.inputs['Normal'])
    return m


def shrimp(name='PROD_Shrimp', L=0.16, loc=(0, 0, 0), rot=(0, 0, 0), seed=1):
    """Raw Vannamei shrimp, body length L (rostrum to telson), slight curve: carapace with rostrum, 6 abdominal
    segments with overlapping plates and side pleura, tail fan (telson + uropods), walking legs, swimmerets,
    long antennae, stalked eyes."""
    rnd = random.Random(seed)
    root = empty(name, loc, size=0.03)
    root.rotation_euler = rot
    sm = shrimp_mat()
    edge = pbr('MAT_VannameiEdge', (0.25, 0.3, 0.42), 0.2, var=0.2, bump=0.1, scale=200, coat=0.8, sss=0.3)
    # spine curve: carapace front at +X, abdomen curls down/back toward -X
    def spine(t):  # t 0 head .. 1 tail
        a = math.radians(10 + 75 * t ** 1.4)
        R = L * 0.75
        return Vector((-R * math.sin(a) + R * math.sin(math.radians(10)), 0, -R * (1 - math.cos(a)) + R * (1 - math.cos(math.radians(10)))))
    def radius(t):
        return L * (0.085 if t < 0.38 else 0.085 * (1 - (t - 0.38) * 0.9))
    # carapace (t 0..0.38) + 6 segments, each its own shell ring overlapping the next
    pieces = [(0.0, 0.38)] + [(0.36 + k * 0.095, 0.36 + k * 0.095 + 0.11) for k in range(6)]
    for k, (t0, t1) in enumerate(pieces):
        bm = bmesh.new()
        n, seg = 10, 20
        rings = []
        for i in range(n + 1):
            t = t0 + (t1 - t0) * i / n
            c = spine(t)
            d = (spine(min(1, t + 0.01)) - spine(max(0, t - 0.01))).normalized()
            side = Vector((0, 1, 0))
            up = d.cross(side).normalized()
            r = radius(t) * (1.06 if i == n else 1.0) * (0.92 + 0.08 * math.sin(math.pi * i / n))
            ring = []
            for j in range(seg):
                a = 2 * math.pi * j / seg
                s, cz = math.sin(a), math.cos(a)
                # flatten the underside and drop side plates (pleura) down
                zz = cz * (1.0 if cz > 0 else 0.55)
                yy = s * (1.08 if cz < 0.2 else 1.0)
                ring.append(bm.verts.new(c + up * (r * zz) + side * (r * 0.82 * yy)))
            rings.append(ring)
        for i in range(n):
            for j in range(seg):
                bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % seg], rings[i][(j + 1) % seg]))
        if k == 0:
            tip = bm.verts.new(spine(0) + Vector((0.005 * L, 0, 0)))
            for j in range(seg):
                bm.faces.new((rings[0][(j + 1) % seg], rings[0][j], tip))
        me = bm_to_mesh(bm, f'{name}_Shell{k}', smooth=True)
        me.materials.append(sm)
        obj(f'{name}_Shell{k}', me, None, parent=root)
    # rostrum (toothed spike) over the head
    c0 = spine(0.02)
    bm = bmesh.new()
    for i in range(7):
        x = c0.x + i * 0.012 * L
        z = c0.z + radius(0) * 0.85 + (0.006 * L if i % 2 else 0) - i * 0.002 * L
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.006 * L * (1 - i / 8), radius2=0.004 * L * (1 - i / 8),
                                  depth=0.014 * L)
        bmesh.ops.rotate(bm, verts=r['verts'], cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
        bmesh.ops.translate(bm, verts=r['verts'], vec=(x + 0.07 * L, 0, z))
    me = bm_to_mesh(bm, f'{name}_Rostrum', smooth=True)
    me.materials.append(sm)
    obj(f'{name}_Rostrum', me, None, parent=root)
    # tail fan: telson + two pairs of uropods
    ct = spine(1.0)
    dt = (spine(1.0) - spine(0.97)).normalized()
    ang = math.atan2(dt.z, dt.x)
    for k, (dy, ln, wd) in enumerate(((0.0, 0.2, 0.035), (0.045, 0.22, 0.05), (-0.045, 0.22, 0.05), (0.08, 0.19, 0.045), (-0.08, 0.19, 0.045))):
        outline = [(0, -wd * 0.3), (ln * 0.4, -wd * 0.5), (ln, -wd * 0.25), (ln * 1.02, 0), (ln, wd * 0.25), (ln * 0.4, wd * 0.5), (0, wd * 0.3)]
        bmu = bmesh.new()
        vs = [bmu.verts.new((p[0] * L, p[1] * L, 0)) for p in outline]
        bmu.faces.new(vs)
        bmesh.ops.triangulate(bmu, faces=bmu.faces[:])
        bmesh.ops.subdivide_edges(bmu, edges=bmu.edges[:], cuts=2, use_grid_fill=True)
        ex = bmesh.ops.extrude_face_region(bmu, geom=bmu.faces[:])
        for g in ex['geom']:
            if isinstance(g, bmesh.types.BMVert):
                g.co.z += 0.002 * L
        me = bm_to_mesh(bmu, f'{name}_Uropod{k}', smooth=True)
        me.materials.append(edge if k else sm)
        o = obj(f'{name}_Uropod{k}', me, None, tuple(ct), parent=root)
        o.rotation_euler = (0, -ang, math.atan2(dy, 0.2) * 1.8)
    # legs (5 pairs of thin walking legs under the carapace) and swimmerets under the abdomen
    lm = bpy.data.materials['MAT_Vannamei']
    for k in range(5):
        t = 0.08 + k * 0.06
        c = spine(t)
        for side in (1, -1):
            pts = [c + Vector((0, side * 0.03 * L, -0.05 * L)), c + Vector((0.02 * L, side * 0.07 * L, -0.12 * L)),
                   c + Vector((0.05 * L, side * 0.09 * L, -0.2 * L))]
            from sklib import tube_mesh
            me = tube_mesh(f'{name}_Leg{k}{side}', pts, 0.004 * L, 6)
            me.materials.append(lm)
            obj(f'{name}_Leg{k}{side}', me, None, parent=root)
    for k in range(5):
        t = 0.45 + k * 0.095
        c = spine(t)
        for side in (1, -1):
            pts = [c + Vector((0, side * 0.035 * L, -0.06 * L)), c + Vector((-0.02 * L, side * 0.05 * L, -0.11 * L))]
            from sklib import tube_mesh
            me = tube_mesh(f'{name}_Swim{k}{side}', pts, 0.006 * L, 6)
            me.materials.append(edge)
            obj(f'{name}_Swim{k}{side}', me, None, parent=root)
    # antennae (long, curving back) and antennules; stalked eyes
    from sklib import tube_mesh
    for side in (1, -1):
        base = spine(0.0) + Vector((0.02 * L, side * 0.03 * L, 0.02 * L))
        pts = [base + Vector((0.12 * L * i / 10 + 0.1 * L * math.sin(i / 3.0) * 0.2, side * 0.05 * L * i / 10, 0.02 * L * i / 10))
               for i in range(4)]
        pts += [pts[-1] + Vector((-0.15 * L * i, side * (0.06 + 0.04 * i) * L, -0.02 * L * i * i)) for i in range(1, 12)]
        me = tube_mesh(f'{name}_Antenna{side}', pts, 0.0025 * L, 5)
        me.materials.append(edge)
        obj(f'{name}_Antenna{side}', me, None, parent=root)
        pts2 = [base, base + Vector((0.08 * L, side * 0.02 * L, 0.01 * L)), base + Vector((0.14 * L, side * 0.03 * L, 0.0))]
        me = tube_mesh(f'{name}_Antennule{side}', pts2, 0.003 * L, 5)
        me.materials.append(sm)
        obj(f'{name}_Antennule{side}', me, None, parent=root)
        ep = spine(0.0) + Vector((0.0, side * 0.045 * L, 0.035 * L))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.012 * L)
        me = bm_to_mesh(bm, f'{name}_Eye{side}', smooth=True)
        me.materials.append(pbr('MAT_ShrimpEye', (0.01, 0.01, 0.012), 0.08, var=0.0, bump=0.0, coat=1.0))
        obj(f'{name}_Eye{side}', me, None, tuple(ep), parent=root)
    return root


def ice_bed(name='PROD_IceTray', w=1.8, d=0.9, n=4500, seed=4):
    """Stainless tray filled with crushed ice: thousands of irregular chunks (one mesh) on a mounded ice base."""
    rnd = random.Random(seed)
    root = empty(name, (0, 0, 0), size=0.3)
    st = pbr('MAT_TrayStainless', (0.8, 0.81, 0.82), 0.18, 1.0, var=0.05, bump=0.02, scale=3)
    bm = bmesh.new()
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = Vector((v.co.x * w, v.co.y * d, v.co.z * 0.08 + 0.04))
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context='FACES_ONLY')
    tm = bm_to_mesh(bm, f'{name}_Tray')
    tm.materials.append(st)
    tray = obj(f'{name}_Tray', tm, None, parent=root)
    sol = tray.modifiers.new('S', 'SOLIDIFY')
    sol.thickness = 0.008
    bv = tray.modifiers.new('B', 'BEVEL')
    bv.width = 0.006
    bv.segments = 3
    ice = new_mat('MAT_CrushedIce') if 'MAT_CrushedIce' not in bpy.data.materials else bpy.data.materials['MAT_CrushedIce']
    p = principled(ice)
    p.inputs['Base Color'].default_value = (0.9, 0.95, 1.0, 1)
    p.inputs['Roughness'].default_value = 0.12
    p.inputs['Transmission Weight'].default_value = 0.85
    p.inputs['IOR'].default_value = 1.31
    p.inputs['Subsurface Weight'].default_value = 0.15
    p.inputs['Coat Weight'].default_value = 0.4
    nt = ice.node_tree
    tc = _node(nt, 'ShaderNodeTexCoord', (-800, -300))
    nz = _node(nt, 'ShaderNodeTexNoise', (-600, -300))
    nz.inputs['Scale'].default_value = 60.0
    nz.inputs['Detail'].default_value = 8
    nt.links.new(_sock(tc, 'Object', out=True), nz.inputs['Vector'])
    rr = _node(nt, 'ShaderNodeMapRange', (-400, -100))
    rr.inputs['To Min'].default_value = 0.03
    rr.inputs['To Max'].default_value = 0.35
    nt.links.new(_sock(nz, 'Factor', out=True), rr.inputs['Value'])
    nt.links.new(rr.outputs[0], p.inputs['Roughness'])
    b = _node(nt, 'ShaderNodeBump', (-300, -400))
    b.inputs['Strength'].default_value = 0.3
    nt.links.new(_sock(nz, 'Factor', out=True), b.inputs['Height'])
    nt.links.new(b.outputs[0], p.inputs['Normal'])
    # base mound
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=60, y_segments=30, size=0.5)
    for v in bm.verts:
        x, y = v.co.x * (w - 0.04), v.co.y * (d - 0.04)
        v.co = Vector((x, y, 0.06 + 0.03 * (1 - (2 * abs(v.co.y)) ** 3) + rnd.uniform(0, 0.012)))
    bm_ = bm_to_mesh(bm, f'{name}_IceBase', smooth=True)
    bm_.materials.append(ice)
    obj(f'{name}_IceBase', bm_, None, parent=root)
    bm = bmesh.new()
    for i in range(n):
        x = rnd.uniform(-w / 2 + 0.03, w / 2 - 0.03)
        y = rnd.uniform(-d / 2 + 0.03, d / 2 - 0.03)
        r_ = rnd.uniform(0.006, 0.02)
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r_)
        sc = Vector((rnd.uniform(0.6, 1.4), rnd.uniform(0.6, 1.4), rnd.uniform(0.5, 1.1)))
        M = Matrix.Translation((x, y, 0.07 + 0.03 * (1 - (2 * abs(y / d)) ** 3) + rnd.uniform(0, 0.025))) @ \
            Euler((rnd.random() * 6, rnd.random() * 6, rnd.random() * 6)).to_matrix().to_4x4() @ Matrix.Diagonal((*sc, 1))
        bmesh.ops.transform(bm, matrix=M, verts=res['verts'])
    cm = bm_to_mesh(bm, f'{name}_IceChunks')
    cm.materials.append(ice)
    obj(f'{name}_IceChunks', cm, None, parent=root)
    return root
