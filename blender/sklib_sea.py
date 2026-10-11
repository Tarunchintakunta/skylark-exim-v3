"""Sea assets for the Skylark library: fishing vessel, net bag, gulls (ASSET_LIBRARY.md 'Fishing')."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, noise
from sklib import (M, pbr, weather, new_mat, principled, _node, _sock, mixrgb, empty, obj, box, cyl, cyl_mesh, sphere, torus_mesh,
                   tube, bm_to_mesh, crate, ice_mesh, fish, D, tex_pbr)


def hull_material(name='MAT_HullWhiteBlue', white=(0.72, 0.72, 0.68), band=(0.03, 0.12, 0.4), bottom=(0.33, 0.05, 0.04),
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
    # rust runs and salt streaks all the way up the topsides and the inside of the bulwarks, grime at the waterline
    return weather(m, streak=(0.34, 0.17, 0.07), amount=0.95, z0=-0.2, z1=2.8, dirt=(0.18, 0.17, 0.12),
                   dirt_amount=0.6, scale=1.8)


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
    wr.inputs['To Max'].default_value = 0.38            # wet patches: a little lower roughness, still matte
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
        tex_pbr('MAT_BoatWhite', 'PaintedMetal004', 0.5, tint=(0.74, 0.74, 0.69), tint_amount=0.8, metal=0.1, grime=0.7,
                bump=0.3, paint_mask=True),   # chipped paint to rusty steel
        streak=(0.38, 0.17, 0.06), amount=0.95, z0=deck_z - 0.2, z1=deck_z + 2.6, dirt=(0.2, 0.18, 0.13),
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
    ins = pbr('MAT_HoldInsulation', (0.26, 0.27, 0.26), 0.55, var=0.15, grime=0.7, scale=2)   # worn, wet, not a white void
    hc = (hx0 + hx1) / 2
    if not detail:   # moored boats: hold closed under a weathered tarpaulin (open holds read as white boxes in the sun)
        tarp = pbr('MAT_HoldTarp', (0.07, 0.15, 0.2), 0.8, var=0.45, grime=0.8, scale=1.5)
        box(f'{name}_HatchTarp', (hx1 - hx0 + 0.3, 2 * hy + 0.3, 0.08), (hc, 0, deck_z + 0.47), tarp, 0.04, parent=root)
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
    ibm = weather(pbr('MAT_IceBox', (0.8, 0.82, 0.8), 0.55, grime=0.5, scale=4.0), streak=(0.3, 0.2, 0.1), amount=0.6,
                  z0=deck_z, z1=deck_z + 0.9, dirt_amount=0.5)
    icebox = box(f'{name}_IceBox', (1.6, 1.1, 0.9), (6.6, -1.8, deck_z), ibm, 0.05, origin='base', parent=root)
    R['icebox'] = icebox
    # flake ice: fine, matte-white granules (not the clear crate-ice glass, which read as grey blotches from above)
    flake = pbr('MAT_FlakeIce', (0.84, 0.89, 0.92), 0.4, var=0.25, bump=1.0, scale=70, sss=0.2)
    obj(f'{name}_IceBoxIce', ice_mesh(f'{name}_IceBoxIce', 1.4, 0.9, 0.12, 40, 26), flake, (6.6, -1.8, deck_z + 0.82),
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
    for (bx, by) in ((-2.0, -1.4), (7.0, 0.95), (-4.6, 0.9)):   # clear of the hatch hand at (5.95, 0.3)
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
    # heavy load: narrow neck under the ring, widest low down (t ~ 0.72), rounded sagging bottom
    r = R * (math.sin(math.pi * min(1.0, 0.04 + t * 0.9)) ** 0.55) * (0.1 + 0.9 * min(1, t * 1.5) ** 1.4)
    if t > 0.86:
        r *= max(0.04, math.sqrt(max(0.0, 1 - ((t - 0.86) / 0.14) ** 2)))
    return r


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
        z = -depth * (t ** 0.85)
        r = bag_radius(t, R)
        ring = []
        for j in range(seg):
            # odd rings shifted half a mesh: the wireframe reads as diamond netting, not a square grid
            a = 2 * math.pi * (j + 0.5 * (i % 2)) / seg
            p = Vector((math.cos(a), math.sin(a), z / depth))
            # fish pressing through the mesh: lumpy, more so in the loaded lower half
            lump = 1 + (0.03 + 0.06 * t) * noise.noise(p * 3.2 + Vector((seed, 0, 0))) \
                + 0.025 * t * noise.noise(p * 9.0 + Vector((0, seed, 0)))
            ring.append(bm.verts.new((r * lump * math.cos(a), r * lump * math.sin(a), z)))
        vs.append(ring)
    for i in range(rings):
        for j in range(seg):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % seg], vs[i][(j + 1) % seg]))
    me = bm_to_mesh(bm, f'{name}_Mesh', smooth=True)
    me.materials.append(mats['net'])
    net = obj(f'{name}_Mesh', me, None, parent=root)
    wm = net.modifiers.new('Wire', 'WIREFRAME')
    wm.thickness = 0.009
    wm.use_even_offset = True
    bmc = bmesh.new()
    bmesh.ops.create_icosphere(bmc, subdivisions=4, radius=1.0)
    for v in bmc.verts:
        zz = (v.co.z + 1) / 2  # 0 bottom .. 1 top
        t = 0.95 - zz * 0.62
        rr = bag_radius(t, R) * 0.9
        a = math.atan2(v.co.y, v.co.x)
        rad = math.hypot(v.co.x, v.co.y)
        v.co = Vector((rr * rad * math.cos(a), rr * rad * math.sin(a), -depth * (t ** 0.85)))
    cm = bm_to_mesh(bmc, f'{name}_Core', smooth=True)
    cm.materials.append(pbr('MAT_FishMass', (0.55, 0.58, 0.62), 0.2, 0.6, var=0.6, bump=0.9, scale=14, coat=0.6))
    core = obj(f'{name}_Core', cm, None, parent=root)
    fishes = []
    for i in range(n_fish):
        a = rnd.uniform(0, 2 * math.pi)
        t = rnd.uniform(0.33, 0.93)
        r = bag_radius(t, R) * rnd.uniform(0.84, 0.95)
        f = fish(f'{name}_fish{i}', 'mackerel', (r * math.cos(a), r * math.sin(a), -depth * (t ** 0.85)),
                 (rnd.uniform(0, 6.28), rnd.uniform(-0.5, 0.5), a + math.pi / 2 + rnd.uniform(-0.6, 0.6)),
                 rnd.uniform(0.9, 1.15), parent=root)
        fishes.append(f)
    for i in range(n_tuna):
        a = rnd.uniform(0, 2 * math.pi)
        t = rnd.uniform(0.45, 0.75)
        r = bag_radius(t, R) * 0.8
        f = fish(f'{name}_tuna{i}', 'tuna', (r * math.cos(a), r * math.sin(a), -depth * (t ** 0.85)),
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
        floats.append(obj(f'{name}_Float{i}', fl, None, (r * math.cos(a), r * math.sin(a), -depth * (t ** 0.85)), (0, D(60), a),
                          parent=root))
    return root, net, core, fishes, floats


def hill_material(name='MAT_HillTerrain', haze=0.0):
    """Distant coastal hills: patches of dark tree cover, dry scrub and bare red earth at two scales (object space),
    with a little bump so ridges catch the light. haze lifts the colours toward the sky for far ranges."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Roughness'].default_value = 0.92
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n1 = nt.nodes.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 0.006
    n1.inputs['Detail'].default_value = 8.0
    n2 = nt.nodes.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 0.05
    n2.inputs['Detail'].default_value = 6.0
    for n in (n1, n2):
        nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MULTIPLY_ADD'
    nt.links.new(n2.outputs['Fac'], mx.inputs[0])
    mx.inputs[1].default_value = 0.35
    nt.links.new(n1.outputs['Fac'], mx.inputs[2])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    h = lambda c: tuple(c[i] * (1 - haze) + (0.42, 0.45, 0.48)[i] * haze for i in range(3)) + (1.0,)
    cr.elements[0].position, cr.elements[0].color = 0.45, h((0.03, 0.05, 0.025))     # tree cover
    cr.elements[1].position, cr.elements[1].color = 0.95, h((0.22, 0.13, 0.07))      # bare laterite
    e = cr.elements.new(0.62)
    e.color = h((0.07, 0.09, 0.04))                                                   # scrub
    e = cr.elements.new(0.78)
    e.color = h((0.15, 0.14, 0.08))                                                   # dry grass
    nt.links.new(mx.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.4
    nt.links.new(n2.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


def hill_height(x, y, h):
    """Add ridges and gullies to a smooth hill profile (metres)."""
    return h + 0.18 * h * noise.fractal(Vector((x / 180.0, y / 180.0, 0.0)), 0.6, 2.0, 5)


# ---------------------------------------------------------------- working-boat wear, humid sky, hull/sea contact
def _over(m, fac_socket, color):
    """Mix `color` over the material's current Base Color by fac."""
    nt = m.node_tree
    p = principled(m)
    src = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else tuple(p.inputs['Base Color'].default_value)[:3]
    col = mixrgb(nt, fac_socket, src, color, loc=(-500, -2600))
    nt.links.new(col, p.inputs['Base Color'])


def _noise_band(m, scale, lo, hi, amount, stretch=(1.0, 1.0, 1.0), z0=None, z1=None, loc=(-1600, -2600)):
    """Thresholded object-space noise (optionally stretched) as a 0..amount factor, faded out between z0 and z1."""
    nt = m.node_tree
    l = nt.links
    tc = _node(nt, 'ShaderNodeTexCoord', loc)
    mp = _node(nt, 'ShaderNodeMapping', (loc[0] + 200, loc[1]))
    mp.inputs['Scale'].default_value = stretch
    l.new(_sock(tc, 'Object', out=True), mp.inputs['Vector'])
    n = _node(nt, 'ShaderNodeTexNoise', (loc[0] + 400, loc[1]))
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = 8
    l.new(mp.outputs[0], n.inputs['Vector'])
    r = _node(nt, 'ShaderNodeMapRange', (loc[0] + 600, loc[1]))
    r.inputs['From Min'].default_value = lo
    r.inputs['From Max'].default_value = hi
    r.inputs['To Max'].default_value = amount
    l.new(_sock(n, 'Factor', out=True), r.inputs['Value'])
    if z0 is None:
        return r.outputs[0]
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (loc[0] + 400, loc[1] - 250))
    l.new(_sock(tc, 'Object', out=True), sep.inputs[0])
    zr = _node(nt, 'ShaderNodeMapRange', (loc[0] + 600, loc[1] - 250))
    zr.inputs['From Min'].default_value = z0
    zr.inputs['From Max'].default_value = z1
    zr.inputs['To Min'].default_value = 1.0
    zr.inputs['To Max'].default_value = 0.0
    l.new(sep.outputs[2], zr.inputs['Value'])
    mul = _node(nt, 'ShaderNodeMath', (loc[0] + 800, loc[1]))
    mul.operation = 'MULTIPLY'
    l.new(r.outputs[0], mul.inputs[0])
    l.new(zr.outputs[0], mul.inputs[1])
    return mul.outputs[0]


def hard_wear(m, deck_z=1.5, top=1.2):
    """Paint on a working boat after a season: grey primer where the white is chipped, rust bleeding from the
    stanchion feet and scuppers (strong at deck level, thin runs above), dirty water stains down the inner faces."""
    if m.get('hard_worn'):
        return m
    _over(m, _noise_band(m, 14.0, 0.62, 0.7, 0.9, loc=(-2600, -2600)), (0.36, 0.37, 0.36))                    # primer chips
    _over(m, _noise_band(m, 3.0, 0.5, 0.7, 0.85, stretch=(28.0, 28.0, 0.5), z0=deck_z, z1=deck_z + 0.6,
                         loc=(-2600, -3000)), (0.26, 0.1, 0.035))                                             # rust at the feet
    _over(m, _noise_band(m, 3.0, 0.6, 0.75, 0.75, stretch=(40.0, 40.0, 0.3), loc=(-2600, -3400)), (0.3, 0.13, 0.05))   # rust runs
    _over(m, _noise_band(m, 2.0, 0.45, 0.8, 0.55, stretch=(6.0, 6.0, 0.4), z0=deck_z + 0.1, z1=deck_z + top,
                         loc=(-2600, -3800)), (0.24, 0.23, 0.19))                                             # dirty-water stains
    m['hard_worn'] = 1
    return m


def salt_wear(m, z0=0.0, z1=4.0):
    """Wear that still reads from 20-40 m away (hard_wear's chips vanish at that distance; detail-8 noise sits near 0.5,
    so thresholds stay close to it): long rust streaks from
    fittings, big chipped-paint patches down to dark primer, whitish salt crust in bands, dirt low down."""
    if m.get('salt_worn'):
        return m
    _over(m, _noise_band(m, 1.6, 0.53, 0.6, 0.55, stretch=(9.0, 9.0, 0.35), loc=(-3400, -2600)), (0.28, 0.12, 0.045))   # rust streaks
    _over(m, _noise_band(m, 2.4, 0.56, 0.62, 0.8, loc=(-3400, -3000)), (0.2, 0.2, 0.19))                                  # chipped to primer
    _over(m, _noise_band(m, 0.9, 0.5, 0.64, 0.25, stretch=(1.0, 1.0, 3.0), loc=(-3400, -3400)), (0.82, 0.8, 0.74))       # salt crust
    _over(m, _noise_band(m, 1.2, 0.4, 0.7, 0.7, z0=z0, z1=z1, loc=(-3400, -3800)), (0.16, 0.14, 0.1))                     # dirt low down
    m['salt_worn'] = 1
    return m


def gut_stains(m):
    """Deck after a haul: diluted blood smears and stuck fish scales that glint."""
    if m.get('gutted'):
        return m
    nt = m.node_tree
    _over(m, _noise_band(m, 1.4, 0.6, 0.75, 0.7, stretch=(1.0, 3.0, 1.0), loc=(-2600, -4300)), (0.12, 0.015, 0.012))
    sc = _noise_band(m, 90.0, 0.74, 0.76, 1.0, loc=(-2600, -4700))
    _over(m, sc, (0.7, 0.72, 0.74))
    p = principled(m)
    rough_src = p.inputs['Roughness'].links[0].from_socket if p.inputs['Roughness'].links else None
    inv = _node(nt, 'ShaderNodeMapRange', (-300, -4700))
    inv.inputs['To Min'].default_value = 0.0
    inv.inputs['To Max'].default_value = 1.0
    nt.links.new(sc, inv.inputs['Value'])
    mx = _node(nt, 'ShaderNodeMix', (-100, -4700))
    mx.data_type = 'FLOAT'
    nt.links.new(inv.outputs[0], mx.inputs['Factor'])
    if rough_src is not None:
        nt.links.new(rough_src, mx.inputs['A'])
    else:
        mx.inputs['A'].default_value = p.inputs['Roughness'].default_value
    mx.inputs['B'].default_value = 0.12                       # scales are shiny
    nt.links.new(mx.outputs['Result'], p.inputs['Roughness'])
    m['gutted'] = 1
    return m


def haze_world(sat=0.5, haze=(0.66, 0.69, 0.68), amount=0.35, contrast=-0.15):
    """Humid coastal sky from a clear HDRI: lower saturation and contrast, lifted toward a grey-green haze."""
    w = bpy.context.scene.world
    nt = w.node_tree
    env = next(n for n in nt.nodes if n.type == 'TEX_ENVIRONMENT')
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = sat
    bc = nt.nodes.new('ShaderNodeBrightContrast')
    bc.inputs['Contrast'].default_value = contrast
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.inputs['Factor'].default_value = amount
    mx.inputs['B'].default_value = (*haze, 1)
    nt.links.new(env.outputs['Color'], hs.inputs['Color'])
    nt.links.new(hs.outputs['Color'], bc.inputs['Color'])
    nt.links.new(bc.outputs['Color'], mx.inputs['A'])
    nt.links.new(mx.outputs['Result'], bg.inputs['Color'])


def sea_tone(m, deep=(0.012, 0.032, 0.03), foam_from=0.12):
    """Green-grey coastal water instead of cobalt; more whitecaps from the ocean foam attribute."""
    p = principled(m)
    for n in m.node_tree.nodes:
        if n.type == 'MIX' and n.data_type == 'RGBA' and not n.inputs['A'].links:
            n.inputs['A'].default_value = (*deep, 1)
        if n.type == 'MAP_RANGE' and abs(n.inputs['From Min'].default_value - 0.25) < 1e-6:
            n.inputs['From Min'].default_value = foam_from
    if not p.inputs['Base Color'].links:
        p.inputs['Base Color'].default_value = (*deep, 1)


def hull_contact(name, root, L=24.0, z=0.03, width=0.7, mats=None):
    """Foam where the hull cuts the water: a broken ring hugging the waterline (hull_b), parented to the boat,
    plus a bow cushion. Alpha from noise so it reads as churned water, not a white rim."""
    m = bpy.data.materials.get('MAT_HullFoam')
    if m is None:
        m = pbr('MAT_HullFoam', (0.86, 0.9, 0.9), 0.5, var=0.2, bump=0.4, scale=6, alpha=0.75)
        nt = m.node_tree
        p = principled(m)
        f = _noise_band(m, 4.0, 0.42, 0.62, 1.0, stretch=(1.0, 1.0, 1.0), loc=(-1600, 600))
        nt.links.new(f, p.inputs['Alpha'])
    bm = bmesh.new()
    n = 80
    inner, outer = [], []
    xs = [(-L / 2 + 0.2) + (L - 0.6) * k / (n // 2) for k in range(n // 2 + 1)]
    loop = [(x, 0.92 * hull_b(x, L)) for x in xs] + [(x, -0.92 * hull_b(x, L)) for x in reversed(xs)]   # waterline beam
    for (x, y) in loop:
        d = Vector((0, 1 if y >= 0 else -1, 0))
        bow = max(0.0, (x - (L / 2 - 4.0)) / 4.0)              # wider cushion at the bow
        w = width * (1.0 + 1.5 * bow)
        inner.append(bm.verts.new((x, y - d.y * 0.05, z)))
        outer.append(bm.verts.new((x + 0.4 * bow, y + d.y * w, z)))
    for i in range(len(loop) - 1):
        bm.faces.new((inner[i], inner[i + 1], outer[i + 1], outer[i]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = obj(name, me, None)
    o.parent = root
    return o
