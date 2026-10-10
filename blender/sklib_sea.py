"""Sea assets for the Skylark library: fishing vessel, net bag, gulls (ASSET_LIBRARY.md 'Fishing')."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, noise
from sklib import (M, pbr, weather, new_mat, principled, _node, _sock, mixrgb, empty, obj, box, cyl, cyl_mesh, sphere, torus_mesh,
                   tube, bm_to_mesh, crate, ice_mesh, fish, D)


def hull_material(name='MAT_HullWhiteBlue', white=(0.82, 0.83, 0.8), band=(0.03, 0.12, 0.4), bottom=(0.33, 0.05, 0.04),
                  band_z=(2.25, 2.5), boot=0.15):
    """Hull paint by height (object Z): red antifouling, black boot-top, white topsides, blue trim at the rail,
    with rust/grime streaks running down."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (-1200, 0))
    l.new(_sock(tc, 'Object', out=True), sep.inputs[0])
    mr = _node(nt, 'ShaderNodeMapRange', (-1050, 0))
    mr.inputs['From Min'].default_value = -3.0
    mr.inputs['From Max'].default_value = 4.0
    l.new(sep.outputs[2], mr.inputs['Value'])
    ramp = _node(nt, 'ShaderNodeValToRGB', (-900, 0))
    ramp.color_ramp.interpolation = 'CONSTANT'
    l.new(mr.outputs[0], ramp.inputs[0])
    cr = ramp.color_ramp
    z2t = lambda z: (z + 3.0) / 7.0
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*bottom, 1)
    cr.elements[1].position = z2t(-0.12)
    cr.elements[1].color = (0.02, 0.02, 0.02, 1)
    for z, c in ((boot, white), (band_z[0], band), (band_z[1], white)):
        e = cr.elements.new(z2t(z))
        e.color = (*c, 1)
    mp = _node(nt, 'ShaderNodeMapping', (-1100, -400))
    mp.inputs['Scale'].default_value = (3.0, 3.0, 0.25)
    l.new(_sock(tc, 'Object', out=True), mp.inputs['Vector'])
    nz = _node(nt, 'ShaderNodeTexNoise', (-900, -400))
    nz.inputs['Scale'].default_value = 2.0
    nz.inputs['Detail'].default_value = 8
    l.new(mp.outputs[0], nz.inputs['Vector'])
    st = _node(nt, 'ShaderNodeMapRange', (-700, -400))
    st.inputs['From Min'].default_value = 0.55
    st.inputs['From Max'].default_value = 0.8
    st.inputs['To Max'].default_value = 0.6
    l.new(_sock(nz, 'Factor', out=True), st.inputs['Value'])
    col = mixrgb(nt, st.outputs[0], _sock(ramp, 'Color', out=True), (0.3, 0.18, 0.1), loc=(-400, -100))
    l.new(col, p.inputs['Base Color'])
    rr = _node(nt, 'ShaderNodeMapRange', (-400, -400))
    rr.inputs['To Min'].default_value = 0.5
    rr.inputs['To Max'].default_value = 0.82      # matte, sun-worn paint
    l.new(_sock(nz, 'Factor', out=True), rr.inputs['Value'])
    l.new(rr.outputs[0], p.inputs['Roughness'])
    p.inputs['Coat Weight'].default_value = 0.04
    # waterline scum and grime low on the topsides, salt-dulled above
    return weather(m, streak=(0.28, 0.16, 0.08), amount=0.55, z0=-0.2, z1=1.4, dirt=(0.16, 0.17, 0.11),
                   dirt_amount=0.7, scale=1.2)


def hull_b(x, L=24.0, B=3.2):
    """Half beam at x (stern -L/2 .. bow +L/2)."""
    xb = L / 2 - 8.0
    if x <= xb:
        return B * (0.9 + 0.1 * min(1.0, (x + L / 2) / 5.0))
    t = (x - xb) / 8.0
    return max(0.04, B * math.sqrt(max(0.0, 1 - t * t)))


def hull_top(x, L=24.0, top=2.5):
    xb = L / 2 - 8.0
    return top + (0.9 * ((x - xb) / 8.0) ** 2 if x > xb else 0.0)


def hull_keel(x, L=24.0):
    if x > L / 2 - 5:
        t = (x - (L / 2 - 5)) / 5.0
        return -1.8 + 1.6 * t ** 1.6
    if x < -L / 2 + 3:
        return -1.8 + 0.7 * (1 - (x + L / 2) / 3.0)
    return -1.8


def deck_wear(m):
    """Working deck: wet patches (lower roughness), stretched scuffs worn through to rusty steel. Once per material."""
    if m.get('worn'):
        return m
    m['worn'] = True
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wet = nt.nodes.new('ShaderNodeTexNoise')
    wet.inputs['Scale'].default_value = 0.35
    wet.inputs['Detail'].default_value = 6
    l.new(tc.outputs['Object'], wet.inputs['Vector'])
    wr = nt.nodes.new('ShaderNodeMapRange')
    wr.inputs['From Min'].default_value = 0.5
    wr.inputs['From Max'].default_value = 0.56
    wr.inputs['To Min'].default_value = 0.55
    wr.inputs['To Max'].default_value = 0.18            # wet patches: lower roughness, still matte-ish
    l.new(wet.outputs['Fac'] if 'Fac' in wet.outputs else wet.outputs[0], wr.inputs['Value'])
    l.new(wr.outputs[0], p.inputs['Roughness'])
    sc = nt.nodes.new('ShaderNodeTexNoise')            # scuffs: stretched streaks of worn paint
    sc.inputs['Scale'].default_value = 3.0
    sc.inputs['Detail'].default_value = 10
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.25, 3.0, 1.0)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])
    l.new(mp.outputs[0], sc.inputs['Vector'])
    sr = nt.nodes.new('ShaderNodeMapRange')
    sr.inputs['From Min'].default_value = 0.66
    sr.inputs['From Max'].default_value = 0.74
    l.new(sc.outputs[0], sr.inputs['Value'])
    src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    l.new(sr.outputs[0], mx.inputs['Factor'])
    if src is not None:
        l.new(src, mx.inputs['A'])
    else:
        mx.inputs['A'].default_value = p.inputs['Base Color'].default_value
    mx.inputs['B'].default_value = (0.11, 0.075, 0.05, 1)      # worn through to rusty steel
    l.new(mx.outputs['Result'], p.inputs['Base Color'])

    return m


def vessel(name='BOAT', loc=(0, 0, 0), rot_z=0.0, mats=None, hull=None, detail=True, L=24.0, deck_z=1.5):
    """White steel fishing vessel with blue trim (catch-reference.png). Returns a dict of key objects/values.
    Names: <name>_Hull, <name>_Deck, <name>_BoomPivot, <name>_BoomTip, <name>_Drum, <name>_HatchCentre."""
    mats = mats or M()
    deck_wear(mats['wetdeck'])
    # salt-worn white for bulwarks, rails, stanchions and house: dull, rust runs from fittings, grime low down
    ww = bpy.data.materials.get('MAT_BoatWhite') or weather(
        pbr('MAT_BoatWhite', (0.74, 0.74, 0.7), 0.62, var=0.25, bump=0.3, grime=0.6, scale=1.5),
        streak=(0.32, 0.17, 0.08), amount=0.7, z0=deck_z - 0.2, z1=deck_z + 2.6, dirt=(0.2, 0.18, 0.13),
        dirt_amount=0.6, scale=1.2)
    hm = weather(hull or hull_material(), streak=(0.3, 0.15, 0.06), amount=0.65, z0=-0.2, z1=0.9,
                 dirt=(0.12, 0.14, 0.08), dirt_amount=0.55, scale=0.8)
    root = empty(name, loc, size=2.0)
    root.rotation_euler = (0, 0, rot_z)
    R = {'root': root, 'deck_z': deck_z}
    bm = bmesh.new()
    xs = [-L / 2 + L * i / 40 for i in range(41)]
    secs = []
    for x in xs:
        b = hull_b(x, L)
        zk = hull_keel(x, L)
        zt = hull_top(x, L)
        prof = [(0.0, zk), (0.45 * b, zk + 0.12), (0.8 * b, zk * 0.55), (0.97 * b, zk * 0.2), (b, 0.0),
                (b * 1.01, deck_z), (b * 1.015, zt)]
        pts = [(-y, z) for (y, z) in reversed(prof[1:])] + prof
        secs.append([bm.verts.new((x, y, z)) for (y, z) in pts])
    for i in range(len(secs) - 1):
        for j in range(len(secs[i]) - 1):
            bm.faces.new((secs[i][j], secs[i + 1][j], secs[i + 1][j + 1], secs[i][j + 1]))
    bm.faces.new(secs[0][::-1])
    me = bm_to_mesh(bm, f'{name}_Hull', smooth=True)
    me.materials.append(hm)
    h = obj(f'{name}_Hull', me, None, parent=root)
    sm = h.modifiers.new('Solid', 'SOLIDIFY')
    sm.thickness = 0.12
    sm.offset = -1
    R['hull'] = h
    hx0, hx1, hy = 3.2, 5.6, 1.1
    R['hatch'] = (hx0, hx1, hy)

    def deck_poly(x0, x1, nm):
        b2 = bmesh.new()
        xs2 = [x0 + (x1 - x0) * i / 16 for i in range(17)]
        right = [b2.verts.new((x, hull_b(x, L) - 0.1, deck_z)) for x in xs2]
        left = [b2.verts.new((x, -hull_b(x, L) + 0.1, deck_z)) for x in reversed(xs2)]
        b2.faces.new(right + left)
        bmesh.ops.triangulate(b2, faces=b2.faces)
        mm = bm_to_mesh(b2, nm)
        mm.materials.append(mats['wetdeck'])
        return obj(nm, mm, None, parent=root)

    deck_poly(-L / 2 + 0.15, hx0, f'{name}_Deck')
    deck_poly(hx1, L / 2 - 0.3, f'{name}_DeckFore')
    for sy in (1, -1):
        bw = hull_b(hx1, L) - 0.1 - hy
        box(f'{name}_DeckSide', (hx1 - hx0, bw, 0.05), ((hx0 + hx1) / 2, sy * (hy + bw / 2), deck_z - 0.025),
            mats['wetdeck'], 0.0, parent=root)
    for (cx, cy, sx, sy2) in (((hx0 + hx1) / 2, hy, hx1 - hx0 + 0.16, 0.08), ((hx0 + hx1) / 2, -hy, hx1 - hx0 + 0.16, 0.08),
                              (hx0, 0, 0.08, 2 * hy), (hx1, 0, 0.08, 2 * hy)):
        box(f'{name}_Coaming', (sx, sy2, 0.45), (cx, cy, deck_z + 0.225), ww, 0.02, parent=root)
    hold_floor = deck_z - 2.6
    ins = pbr('MAT_HoldInsulation', (0.42, 0.44, 0.43), 0.55, var=0.15, grime=0.6, scale=2)   # worn, wet, not a white void
    hc = (hx0 + hx1) / 2
    box(f'{name}_HoldFloor', (4.6, 3.6, 0.1), (hc, 0, hold_floor - 0.05), ins, 0.0, parent=root)
    for (cx, cy, sx, sy2) in ((hc, 1.8, 4.6, 0.1), (hc, -1.8, 4.6, 0.1), (hc - 2.3, 0, 0.1, 3.6), (hc + 2.3, 0, 0.1, 3.6)):
        box(f'{name}_HoldWall', (sx, sy2, 2.6), (cx, cy, hold_floor + 1.3), ins, 0.0, parent=root)
    ld = bpy.data.lights.new(f'{name}_HoldLight', 'AREA')
    ld.energy = 400
    ld.size = 3.0
    ld.color = (0.92, 0.96, 1.0)
    lo = bpy.data.objects.new(f'{name}_HoldLight', ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = root
    lo.location = (hc, 0, deck_z - 0.25)
    R['hold_floor'] = hold_floor
    R['hatch_c'] = empty(f'{name}_HatchCentre', (hc, 0, deck_z), root)
    for sy in (1, -1):
        pts = [(x, sy * hull_b(x, L) * 1.015, hull_top(x, L) + 0.03) for x in xs[1:-1]]
        tube(f'{name}_RailCap', pts, 0.05, ww, 8, parent=root)
        if detail:
            for x in xs[2:-3:2]:
                b = hull_b(x, L)
                box(f'{name}_Stanchion', (0.06, 0.25, hull_top(x, L) - deck_z), (x, sy * (b - 0.12), (deck_z + hull_top(x, L)) / 2),
                    ww, 0.01, parent=root)
            tyre = bpy.data.meshes.get(f'{name}_Tyre') or torus_mesh(f'{name}_Tyre', 0.35, 0.13, 20, 8)
            if not tyre.materials:
                tyre.materials.append(mats['rubber'])
            for x in (-8, -4, 0, 4):
                obj(f'{name}_Tyre', tyre, None, (x, sy * (hull_b(x, L) + 0.15), 1.1), (D(90), 0, 0), parent=root)
    # wheelhouse (aft)
    wx0, wx1, hw = -10.4, -4.6, 2.5
    pw = ww
    box(f'{name}_House', (wx1 - wx0, 2 * hw, 2.4), ((wx0 + wx1) / 2, 0, deck_z), pw, 0.06, origin='base', parent=root)
    box(f'{name}_HouseBand', (wx1 - wx0 + 0.04, 2 * hw + 0.04, 0.16), ((wx0 + wx1) / 2, 0, deck_z + 2.32), mats['paint_blue'],
        0.02, parent=root)
    box(f'{name}_Bridge', (4.4, 4.4, 2.0), (-7.8, 0, deck_z + 2.4), pw, 0.06, origin='base', parent=root)
    box(f'{name}_BridgeRoof', (4.8, 4.8, 0.12), (-7.8, 0, deck_z + 4.46), pw, 0.03, parent=root)
    box(f'{name}_BridgeBand', (4.44, 4.44, 0.14), (-7.8, 0, deck_z + 2.47), mats['paint_blue'], 0.02, parent=root)
    glass = mats['glass']
    for i in range(4):
        box(f'{name}_Win', (0.06, 0.9, 0.8), (-5.58, -1.5 + i, deck_z + 3.5), glass, 0.02, parent=root)
        box(f'{name}_WinFrame', (0.05, 0.98, 0.88), (-5.6, -1.5 + i, deck_z + 3.5), pw, 0.01, parent=root)
    for sy in (1, -1):
        for i in range(3):
            box(f'{name}_Win', (0.8, 0.06, 0.75), (-9.3 + i * 1.1, sy * 2.22, deck_z + 3.5), glass, 0.02, parent=root)
            cyl(f'{name}_Port', 0.2, 0.06, (wx0 + 1.2 + i * 1.6, sy * (hw + 0.02), deck_z + 1.5), glass, 16, axis='Y',
                parent=root)
        box(f'{name}_Door', (0.8, 0.05, 1.9), (wx1 - 0.7, sy * (hw + 0.02), deck_z + 0.98), pw, 0.02, parent=root)
    for i in range(3):
        box(f'{name}_WinLow', (0.06, 0.9, 0.7), (wx1 + 0.02, -1.4 + i * 1.4, deck_z + 1.55), glass, 0.02, parent=root)
    rl = [[(wx1 - 0.1, sy * (hw - 0.1)), (wx0 + 0.3, sy * (hw - 0.1))] for sy in (1, -1)]
    rl.append([(wx1 - 0.1, -hw + 0.1), (wx1 - 0.1, hw - 0.1)])
    for seg in rl:
        for zz in (3.4, 2.95):
            tube(f'{name}_Rail', [(p[0], p[1], deck_z + zz) for p in seg], 0.025, pw, 6, parent=root)
        a, b2 = Vector((*seg[0], 0)), Vector((*seg[1], 0))
        n = int((a - b2).length / 0.9)
        for i in range(n + 1):
            p = a + (b2 - a) * (i / max(1, n))
            cyl(f'{name}_RailPost', 0.022, 1.0, (p.x, p.y, deck_z + 2.9), pw, 6, parent=root)
    lr = torus_mesh(f'{name}_LifeRing', 0.3, 0.07, 24, 8)
    lr.materials.append(pbr('MAT_LifeRing', (0.9, 0.25, 0.04), 0.5, var=0.1))
    for sy in (1, -1):
        obj(f'{name}_LifeRing', lr, None, (wx0 + 2.6, sy * (hw + 0.08), deck_z + 1.4), (D(90), 0, 0), parent=root)
    cyl(f'{name}_Mast', 0.1, 5.0, (-7.8, 0, deck_z + 4.5), pw, 12, origin='base', parent=root)
    box(f'{name}_MastBar', (0.12, 2.4, 0.12), (-7.8, 0, deck_z + 7.8), pw, 0.02, parent=root)
    for sy in (-1.1, 1.1):
        sphere(f'{name}_MastLight', 0.08, (-7.8, sy, deck_z + 7.95), mats['lamp'], parent=root)
    sphere(f'{name}_MastTop', 0.09, (-7.8, 0, deck_z + 9.55), mats['lamp_red'], parent=root)
    for dx in (-0.4, 0.3):
        cyl(f'{name}_Antenna', 0.015, 2.2, (-7.8 + dx, 0.6, deck_z + 4.6), mats['steel'], 6, origin='base', parent=root)
    box(f'{name}_Radar', (0.3, 1.6, 0.12), (-7.8, 0, deck_z + 6.6), pw, 0.03, parent=root)
    # king post + boom over the starboard rail (+Y), block and hydraulic ram
    kp = Vector((1.0, 1.3, deck_z))
    cyl(f'{name}_KingPost', 0.22, 8.0, tuple(kp), pw, 16, origin='base', parent=root)
    box(f'{name}_KingPostBand', (0.5, 0.5, 0.3), (kp.x, kp.y, deck_z + 7.0), mats['paint_blue'], 0.04, parent=root)
    R['post_top'] = (kp.x, kp.y, deck_z + 8.0)
    pivot = empty(f'{name}_BoomPivot', (kp.x, kp.y, deck_z + 1.6), root, size=0.5)
    pivot.rotation_euler = (D(-42), 0, 0)
    R['boom_pivot'] = pivot
    blen = 8.2
    R['boom_len'] = blen
    cyl(f'{name}_Boom', 0.17, blen, (0, 0, 0), pw, 14, r2=0.12, origin='base', parent=pivot)
    R['boom_tip'] = empty(f'{name}_BoomTip', (0, 0, blen + 0.05), pivot, size=0.4)
    cyl(f'{name}_Block', 0.28, 0.14, (0, 0, blen + 0.05), mats['steel'], 20, axis='X', parent=pivot)
    for dx in (0.1, -0.1):
        box(f'{name}_BlockCheek', (0.06, 0.65, 0.65), (dx, 0, blen + 0.05), mats['paint_blue'], 0.02, parent=pivot)
    ram = cyl(f'{name}_Ram', 0.08, 2.6, (0, -0.35, 0.9), mats['steel'], 10, origin='base', parent=pivot)
    ram.rotation_euler = (D(14), 0, 0)
    # winch drum with rope coils
    drum_root = empty(f'{name}_DrumFrame', (-3.4, 0.2, deck_z), root)
    for sy in (-0.95, 0.95):
        box(f'{name}_WinchCheek', (0.9, 0.12, 1.2), (0, sy, 0.6), mats['paint_blue'], 0.03, parent=drum_root)
    box(f'{name}_WinchBase', (1.1, 2.1, 0.15), (0, 0, 0.075), mats['paint_blue'], 0.02, parent=drum_root)
    box(f'{name}_WinchMotor', (0.5, 0.5, 0.5), (0, 1.3, 0.55), mats['paint_blue'], 0.04, parent=drum_root)
    drum = cyl(f'{name}_Drum', 0.32, 1.8, (0, 0, 0.75), mats['steel'], 24, axis='Y', parent=drum_root)
    coil = torus_mesh(f'{name}_Coil', 0.4, 0.045, 24, 6)
    coil.materials.append(mats['rope'])
    for i in range(14):
        obj(f'{name}_Coil', coil, None, (0, -0.8 + i * 0.122, 0), (D(90), 0, 0), parent=drum)
    R['drum'] = drum
    R['drum_world'] = (-3.4, 0.2, deck_z + 0.75)
    reel = cyl(f'{name}_Reel', 0.45, 0.9, (-1.6, -2.1, deck_z + 0.6), mats['steel'], 24, axis='Y', parent=root)
    coil2 = torus_mesh(f'{name}_Coil2', 0.5, 0.05, 24, 6)
    coil2.materials.append(mats['rope_green'])
    for i in range(7):
        obj(f'{name}_Coil2', coil2, None, (0, -0.38 + i * 0.12, 0), (D(90), 0, 0), parent=reel)
    if detail:
        _dress(name, root, mats, deck_z, L, R, wx1)
    return R


def _dress(name, root, mats, deck_z, L, R, wx1):
    icebox = box(f'{name}_IceBox', (1.6, 1.1, 0.9), (6.6, -1.8, deck_z), pbr('MAT_IceBox', (0.85, 0.87, 0.86), 0.45, grime=0.3),
                 0.05, origin='base', parent=root)
    R['icebox'] = icebox
    obj(f'{name}_IceBoxIce', ice_mesh(f'{name}_IceBoxIce', 1.4, 0.9, 0.12, 16, 9), mats['ice'], (6.6, -1.8, deck_z + 0.82),
        parent=root)
    rnd = random.Random(5)
    k = 0
    for (cx, cy, n) in ((-4.0, -2.2, 4), (-4.4, 2.1, 3), (7.6, 1.9, 4), (-2.4, -2.5, 2)):
        for lvl in range(n):
            crate(f'{name}_Stack{k}', rnd.choice(['blue', 'blue', 'red', 'white']),
                  (cx + rnd.uniform(-0.03, 0.03), cy, deck_z + lvl * 0.29), rnd.uniform(-0.06, 0.06), parent=root, mats=mats)
            k += 1
    bucket = cyl_mesh(f'{name}_Bucket', 0.16, 0.32, 16, r2=0.19, origin='base')
    bucket.materials.append(pbr('MAT_BucketBlue', (0.12, 0.2, 0.3), 0.5, grime=0.4))
    for (bx, by) in ((-2.0, -1.4), (6.0, 0.4), (-4.6, 0.9)):
        obj(f'{name}_Bucket', bucket, None, (bx, by, deck_z), parent=root)
    basket = cyl_mesh(f'{name}_Basket', 0.28, 0.3, 18, r2=0.32, origin='base')
    basket.materials.append(pbr('MAT_Basket', (0.6, 0.45, 0.2), 0.8, var=0.3, bump=0.4, scale=20))
    for (bx, by) in ((7.6, -0.4), (8.2, 0.2), (-3.0, 2.6)):
        obj(f'{name}_Basket', basket, None, (bx, by, deck_z), parent=root)
    tube(f'{name}_Hose', [(-4.6, -0.5, deck_z + 0.03), (-3.0, -1.2, deck_z + 0.03), (-1.0, -1.0, deck_z + 0.03),
                          (0.5, -1.6, deck_z + 0.03), (2.0, -2.5, deck_z + 0.03)], 0.03,
         pbr('MAT_HoseYellow', (0.8, 0.6, 0.05), 0.45), 8, parent=root)
    for i in range(2):
        sh = empty(f'{name}_Shovel{i}', (5.7 + i * 0.25, -2.45, deck_z), root)
        sh.rotation_euler = (D(-12), D(-10), 0)
        cyl(f'{name}_ShovelShaft', 0.018, 1.2, (0, 0, 0.32), mats['wood'], 8, origin='base', parent=sh)
        box(f'{name}_ShovelBlade', (0.02, 0.26, 0.34), (0, 0, 0.17), mats['steel'], 0.01, parent=sh)
    rnd2 = random.Random(11)
    bmn = bmesh.new()
    bmesh.ops.create_icosphere(bmn, subdivisions=3, radius=1.0)
    for v in bmn.verts:
        v.co = Vector((v.co.x * 1.6, v.co.y * 1.3, max(0.0, v.co.z) * 0.55 + rnd2.uniform(0, 0.08)))
    nm = bm_to_mesh(bmn, f'{name}_NetPile', smooth=True)
    nm.materials.append(pbr('MAT_NetPile', (0.2, 0.18, 0.12), 0.85, var=0.35, bump=0.8, scale=25))
    obj(f'{name}_NetPile', nm, None, (-L / 2 + 1.9, 0.4, deck_z), parent=root)
    fl = cyl_mesh(f'{name}_Float', 0.09, 0.2, 12, axis='X')
    fl.materials.append(mats['float_yellow'])
    for i in range(18):
        obj(f'{name}_SpareFloat', fl, None, (-L / 2 + 1.9 + rnd2.uniform(-1.4, 1.4), 0.4 + rnd2.uniform(-1.1, 1.1),
                                            deck_z + 0.35 + rnd2.uniform(0, 0.35)), (0, 0, rnd2.uniform(0, 3)), parent=root)
    for i in range(3):
        box(f'{name}_GloveHung', (0.03, 0.1, 0.2), (wx1 + 0.04, 1.6 + i * 0.15, deck_z + 1.4), mats['glove_teal'], 0.02,
            parent=root)


def gull(name, loc=(0, 0, 0)):
    """Simple gull: body + two wings on hinges (flap by rotating <name>_wL / <name>_wR)."""
    w = pbr('MAT_Gull', (0.92, 0.92, 0.9), 0.6, var=0.05)
    g = pbr('MAT_GullGrey', (0.55, 0.57, 0.6), 0.6, var=0.05)
    root = empty(name, loc, size=0.3)
    sphere(f'{name}_body', 0.12, (0, 0, 0), w, scale=(2.2, 0.8, 0.8), parent=root)
    for side, sy in (('L', 1), ('R', -1)):
        hinge = empty(f'{name}_w{side}', (0, sy * 0.06, 0.03), root, size=0.1)
        bmw = bmesh.new()
        vs = [bmw.verts.new(p) for p in ((0.1, 0, 0), (0.08, sy * 0.45, 0.02), (-0.05, sy * 0.75, 0.0),
                                          (-0.12, sy * 0.4, 0), (-0.1, 0, 0))]
        bmw.faces.new(vs if sy > 0 else vs[::-1])
        me = bm_to_mesh(bmw, f'{name}_wing{side}')
        me.materials.append(g)
        obj(f'{name}_wing{side}', me, None, (0, 0, 0), parent=hinge)
    return root


def flap(g, f0, f1, period=10, amp=35, path=None):
    for f in range(f0, f1 + 1, max(1, period // 4)):
        a = math.sin(2 * math.pi * (f - f0) / period) * D(amp)
        for side, sgn in (('L', 1), ('R', -1)):
            hw = bpy.data.objects[f'{g.name}_w{side}']
            hw.rotation_euler = (sgn * a, 0, 0)
            hw.keyframe_insert('rotation_euler', frame=f)
    if path:
        n = len(path) - 1
        prev = None
        for i, p in enumerate(path):
            f = f0 + (f1 - f0) * i / n
            g.location = p
            j = min(i, n - 1)
            d = Vector(path[j + 1]) - Vector(path[j])
            rz = math.atan2(d.y, d.x)
            if prev is not None:
                while rz - prev > math.pi:
                    rz -= 2 * math.pi
                while rz - prev < -math.pi:
                    rz += 2 * math.pi
            prev = rz
            g.rotation_euler = (0, 0, rz)
            g.keyframe_insert('location', frame=f)
            g.keyframe_insert('rotation_euler', frame=f)


def bag_radius(t, R):
    # loaded sack: gathered neck under the ring, sides swelling slowly (weight drags the load down), widest low
    # (t ~ 0.66), then a round sagging bottom
    g = min(1.0, t / 0.78)
    g = g * g * (3 - 2 * g)
    r = R * (0.08 + 0.92 * g ** 1.7)          # long tapering upper half: the weight is all at the bottom
    if t > 0.8:
        r *= max(0.04, math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2)))
    return r


def net_sack_mat(name='MAT_NetSack', mesh=0.075, twine=0.16):
    """Knotted diamond netting as a texture on a continuous sack surface: cylindrical coordinates (angle x radius,
    height) from object space, two diagonal triangle waves -> twine mask -> alpha. Reads as fine mesh stretched over
    the load instead of a wire cage."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'DITHERED'
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    p.inputs['Base Color'].default_value = (0.03, 0.075, 0.045, 1)     # dark green nylon twine
    p.inputs['Roughness'].default_value = 0.6
    p.inputs['Metallic'].default_value = 0.0
    if 'Coat Weight' in p.inputs:
        p.inputs['Coat Weight'].default_value = 0.12          # only a slight wet sheen
        p.inputs['Coat Roughness'].default_value = 0.3
    tc = _node(nt, 'ShaderNodeTexCoord', (-1600, 0))
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (-1400, 0))
    l.new(_sock(tc, 'Object', out=True), sep.inputs[0])

    def math_(op, a, b=None, loc=(0, 0)):
        n = _node(nt, 'ShaderNodeMath', loc)
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                l.new(v, n.inputs[i])
        return n.outputs[0]
    ang = math_('ARCTAN2', sep.outputs[1], sep.outputs[0], (-1200, 100))
    u = math_('MULTIPLY', ang, 1.3, (-1000, 100))               # ~ arc length at the sack's mean radius
    v = sep.outputs[2]
    masks = []
    for k, (a, b) in enumerate(((u, v), (u, v))):
        d = math_('ADD' if k == 0 else 'SUBTRACT', a, b, (-800, 200 - k * 200))
        q = math_('DIVIDE', d, mesh, (-650, 200 - k * 200))
        f = math_('FRACT', q, None, (-500, 200 - k * 200))
        c = math_('SUBTRACT', f, 0.5, (-350, 200 - k * 200))
        t = math_('ABSOLUTE', c, None, (-200, 200 - k * 200))
        masks.append(t)
    mx = math_('MAXIMUM', masks[0], masks[1], (-50, 100))
    tw = math_('GREATER_THAN', mx, 0.5 - twine / 2, (100, 100))
    l.new(tw, p.inputs['Alpha'])
    return m


def net_bag(name='NET', R=1.5, depth=2.6, mats=None, n_fish=160, n_tuna=5, seed=3):
    """Hanging net bag full of fish. Root empty = hook (top), bag hangs down -Z.
    Returns (root, net, core, fishes, floats)."""
    mats = mats or M()
    rnd = random.Random(seed)
    root = empty(name, (0, 0, 0), size=0.5)
    bm = bmesh.new()
    seg, rings = 96, 56
    vs = []
    for i in range(rings + 1):
        t = i / rings
        z = -depth * t
        r = bag_radius(t, R)
        sway = 0.12 * t * t           # the load hangs a little off the hook line
        ring = []
        for j in range(seg):
            # odd rings shifted half a mesh: the wireframe reads as diamond netting, not a square grid
            a = 2 * math.pi * (j + 0.5 * (i % 2)) / seg
            p = Vector((math.cos(a), math.sin(a), z / depth))
            # fish pressing through the mesh: lumpy, more so in the loaded lower half
            lump = 1 + (0.05 + 0.1 * t) * noise.noise(p * 2.4 + Vector((seed, 0, 0))) \
                + 0.05 * t * noise.noise(p * 8.0 + Vector((0, seed, 0)))
            # gathered folds near the neck, fading out as the sack fills
            lump += 0.32 * max(0.0, 0.5 - t) * math.sin(10 * a + 3 * noise.noise(p * 2.0))   # slack folds at the ring
            # slack netting bellies out between the load points low down
            zz = z + 0.06 * t * noise.noise(p * 5.0 + Vector((seed, seed, 0)))
            ring.append(bm.verts.new((r * lump * math.cos(a) + sway, r * lump * math.sin(a), zz)))
        vs.append(ring)
    for i in range(rings):
        for j in range(seg):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % seg], vs[i][(j + 1) % seg]))
    me = bm_to_mesh(bm, f'{name}_Mesh', smooth=True)
    me.materials.append(net_sack_mat())
    net = obj(f'{name}_Mesh', me, None, parent=root)   # textured diamond mesh stretched over the load (no wire cage)
    bmc = bmesh.new()
    bmesh.ops.create_icosphere(bmc, subdivisions=4, radius=1.0)
    for v in bmc.verts:
        zz = (v.co.z + 1) / 2  # 0 bottom .. 1 top
        t = 0.95 - zz * 0.62
        rr = bag_radius(t, R) * 0.9
        a = math.atan2(v.co.y, v.co.x)
        rad = math.hypot(v.co.x, v.co.y)
        v.co = Vector((rr * rad * math.cos(a) + 0.12 * t * t, rr * rad * math.sin(a), -depth * t))
    cm = bm_to_mesh(bmc, f'{name}_Core', smooth=True)
    cm.materials.append(pbr('MAT_FishMass', (0.32, 0.36, 0.4), 0.45, 0.15, var=0.7, bump=0.9, scale=9, coat=0.2))   # matte wet bodies
    core = obj(f'{name}_Core', cm, None, parent=root)
    fishes = []
    for i in range(n_fish):
        a = rnd.uniform(0, 2 * math.pi)
        t = rnd.uniform(0.33, 0.93)
        r = bag_radius(t, R) * rnd.uniform(0.93, 1.0)       # bodies pressing out through the meshes
        # lying along the sack wall (flank out), big enough to read as fish at preview size
        f = fish(f'{name}_fish{i}', 'mackerel', (r * math.cos(a) + 0.12 * t * t, r * math.sin(a), -depth * t),
                 (math.pi / 2 + rnd.uniform(-0.3, 0.3), rnd.uniform(-0.4, 0.4), a + math.pi / 2 + rnd.uniform(-0.5, 0.5)),
                 rnd.uniform(1.3, 1.6), parent=root)
        fishes.append(f)
    for i in range(n_tuna):
        a = rnd.uniform(0, 2 * math.pi)
        t = rnd.uniform(0.5, 0.92)
        r = bag_radius(t, R) * 0.9
        f = fish(f'{name}_tuna{i}', 'tuna_s', (r * math.cos(a) + 0.12 * t * t, r * math.sin(a), -depth * t),
                 (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.3, 0.3), a + math.pi / 2), rnd.uniform(0.75, 0.95), parent=root)
        fishes.append(f)
    obj(f'{name}_Ring', torus_mesh(f'{name}_Ring', 0.3, 0.04, 24, 8), mats['steel'], (0, 0, -0.12), parent=root)
    fl = cyl_mesh(f'{name}_FloatM', 0.08, 0.2, 12, axis='X')
    fl.materials.append(mats['float_yellow'])
    floats = []
    for i in range(12):
        t = 0.08 + i * 0.07
        r = bag_radius(t, R) + 0.06
        a = 0.4 + 0.1 * i
        floats.append(obj(f'{name}_Float{i}', fl, None, (r * math.cos(a) + 0.12 * t * t, r * math.sin(a), -depth * t), (0, D(60), a),
                          parent=root))
    return root, net, core, fishes, floats
