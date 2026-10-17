"""Hand-framed cameras for the composition stills (#255, #256, #246): a static camera per still, so the frame is the
composition and not wherever the animated move happens to be. Coordinates are the plant set's (dock wall y = 0, the
truck bay at x = 9.2, the dock floor 1.2 m up, the hall behind the wall at y > 0)."""
import bpy
from mathutils import Vector

# 256: eye level, 1.65 m over the dock floor, square on to the open door, a steel-crate trolley each side
DOLLY_260 = 380.0

# id: (location, look-at target, focal length mm)
CAMS = {
    # truck backed straight into bay 2, rear on the bumpers; seen from the front-right so the driver shows through the
    # windscreen and the right-hand door window (the neighbouring parked trucks are hidden for this still)
    '255': ((9.2, 7.0, 2.35), (9.2, -1.0, 2.0), 30),
    '255b': ((4.5, -18.0, 2.3), (10.2, -6.5, 2.1), 34),      # ~29 deg off the nose: the driver reads through the windscreen
    # 256: eye level (1.65 m over the dock floor), a 3/4 view along the intake line
    '256': ((11.5, 3.8, 2.3), (9.0, 1.0, 2.0), 38),
    # 257: inside the cold store, past the staged pallets, looking down the aisle
    '257': ((8.9, 79.0, 2.5), (8.7, 66.0, 2.3), 28),
    # 258: the whole quay crane, boom and spreader, from the quay a good way back
    '258': ((165.0, -12.0, 8.0), (40.0, -6.0, 17.0), 36),
    # 246: beat 3 from inside the room, looking out through the open dock door at the truck's rear
        '246': ((13.2, 5.0, 2.75), (9.2, 0.4, 2.35), 36),
}
CAMS.update({
    '255a': ((4.2, -14.0, 1.8), (9.2, -4.5, 1.9), 30),
    '255b0': ((6.5, -15.5, 1.6), (9.2, -5.0, 1.9), 28),
    '255d': ((2.0, -12.5, 3.9), (9.2, -4.0, 1.9), 28),
    '255e': ((3.0, -6.0, 4.2), (9.2, -4.2, 1.7), 22),
    '255f': ((1.0, -10.0, 3.0), (9.2, -3.5, 1.8), 24),
    '255g': ((3.0, -12.0, 2.45), (9.0, -5.0, 2.2), 30),
    '255h': ((5.8, -13.5, 2.35), (9.0, -4.5, 2.1), 32),
    '255i': ((4.2, -12.8, 2.4), (9.0, -4.8, 2.2), 30),
    '255j': ((6.0, -18.0, 2.3), (9.0, -4.5, 2.2), 28),
    '255k': ((4.5, -16.5, 2.3), (9.0, -4.5, 2.2), 28),
    '255m': ((-1.0, -5.5, 1.9), (9.2, -4.6, 2.1), 40),
    '255n': ((0.5, -11.0, 1.9), (9.2, -4.2, 2.1), 36),
    '255p': ((-3.0, -15.0, 2.6), (9.2, -4.3, 2.2), 36),
    '255q': ((2.0, -16.0, 3.2), (9.2, -4.0, 2.2), 34),
    '258L': ((48.0, -78.0, 16.0), (-22.0, -6.0, 27.0), 34),
    '258M': ((95.0, -60.0, 22.0), (-25.0, -8.0, 26.0), 34),
    '258N': ((40.0, -230.0, 30.0), (-30.0, -10.0, 30.0), 34),
    '258O': ((120.0, -170.0, 45.0), (-30.0, -10.0, 28.0), 32),
    '255r': ((5.0, -17.5, 2.7), (9.0, -4.2, 2.3), 30),
    '255s': ((3.5, -16.0, 2.4), (9.0, -4.0, 2.2), 32),
    '256d': ((4.2, 0.9, 2.45), (9.3, 1.2, 2.2), 38),
    '256e': ((15.0, 1.0, 2.45), (9.3, 1.2, 2.2), 38),
    '255t': ((6.8, -17.0, 2.6), (9.1, -4.2, 2.4), 30),
    '256f': ((8.0, 4.3, 2.4), (9.2, 0.9, 2.0), 40),
    '256g': ((11.5, 3.8, 2.3), (9.0, 1.0, 2.0), 38),
    '255A': ((3.8, -3.6, 2.0), (9.4, -1.4, 2.1), 36),
    '255B': ((2.4, -7.5, 2.2), (9.4, -2.0, 2.1), 34),
    '257A': ((8.9, 67.8, 2.3), (8.7, 80.0, 2.4), 30),
    '255C': ((7.0, 3.4, 2.5), (9.2, -0.9, 2.0), 42),
    '255D': ((11.5, 3.4, 2.5), (9.2, -0.9, 2.0), 42),
    '257B': ((8.9, 70.0, 2.7), (8.7, 80.0, 2.5), 26),
    '255E': ((9.2, 7.5, 2.3), (9.2, -1.0, 2.0), 30),
    '255F': ((6.0, 6.5, 2.3), (9.2, -1.0, 2.0), 30),
    '258P': ((150.0, -14.0, 12.0), (10.0, -12.0, 16.0), 30),
    '258Q': ((70.0, 120.0, 75.0), (20.0, -12.0, 14.0), 36),
    '258R': ((135.0, 40.0, 30.0), (20.0, -12.0, 14.0), 34),
    '258S': ((135.0, -26.0, 10.0), (30.0, -10.0, 20.0), 30),
    '258T': ((30.0, -75.0, 50.0), (30.0, -12.0, 20.0), 50),
    '258U': ((30.0, -105.0, 60.0), (30.0, -12.0, 22.0), 40),
    '256H': ((9.2, 5.6, 2.4), (9.2, 1.0, 1.9), 42),
    '256I': ((10.6, 5.4, 2.5), (9.0, 1.0, 1.9), 40),
    '257H': ((8.9, 79.0, 2.5), (8.7, 66.0, 2.3), 28),
    '258V': ((112.0, -12.0, 3.5), (40.0, -2.0, 14.0), 48),
    '258W': ((105.0, -20.0, 5.0), (45.0, 0.0, 16.0), 44),
    '258X': ((95.0, 85.0, 7.0), (55.0, 5.0, 24.0), 46),
    'FKS': ((17.0, -13.0, 1.9), (17.0, -7.3, 1.6), 38),
    'FKF': ((12.5, -3.0, 2.6), (16.5, -7.3, 1.6), 34),
    '255c': ((2.0, -12.5, 1.7), (9.2, -4.8, 1.95), 26),
    '256a': ((3.0, 3.4, 2.85), (9.2, 1.4, 2.3), 45),
    '256b': ((5.0, 6.2, 2.85), (9.4, 1.6, 2.3), 40),
    '256c': ((12.6, 5.6, 2.85), (9.0, 1.6, 2.3), 40),
    '246a': ((5.2, 4.2, 2.75), (9.2, 0.4, 2.35), 36),
    '246b': ((13.2, 5.0, 2.75), (9.2, 0.4, 2.35), 36),
})
CAMS['246f'] = CAMS['246']
for _k in 'abc':
    CAMS['258' + _k] = CAMS['258']          # the crane sequence's three stills share the quay camera


def apply(sid, env=None):
    if sid == '260':
        # the push-in's last view, same lens and heading, DOLLY m nearer so the ship at its berth reads
        s = bpy.context.scene
        s.frame_set(144)
        bpy.context.view_layer.update()
        src = s.camera
        mw = src.matrix_world.copy()
        cam = bpy.data.objects.new('STILL_Camera', bpy.data.cameras.new('STILL_Camera'))
        s.collection.objects.link(cam)
        cam.data.lens, cam.data.clip_start, cam.data.clip_end = src.data.lens, 0.1, 20000
        cam.data.dof.use_dof = False
        cam.matrix_world = mw
        cam.location = mw.translation + (mw.to_quaternion() @ Vector((0, 0, -1))) * DOLLY_260
        s.camera = cam
        return
    if sid not in CAMS:
        return
    loc, tgt, lens = CAMS[sid]
    s = bpy.context.scene
    cam = bpy.data.objects.new('STILL_Camera', bpy.data.cameras.new('STILL_Camera'))
    s.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.dof.use_dof = False        # a still keeps every worker and crate sharp
    cam.data.clip_start, cam.data.clip_end = 0.1, 400
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    s.camera = cam


def look(sid):
    """#260: one container ship at its berth, nothing else on the water, and a low warm sun glow on a golden horizon."""
    if sid != '260':
        return
    import math
    s = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.name.startswith(('BASIN_Ship', 'FARSHIP', 'TUG')):
            for c in [o] + list(o.children_recursive):
                c.hide_render = c.hide_viewport = True
    bw = bpy.data.objects.get('LAND_Breakwaters')
    if bw is not None:                       # the rock blocks sit into the water: no floating foam line along their base
        bw.location.z -= 0.35
    sf = bpy.data.objects.get('LAND_BreakwaterSurf')
    if sf is not None:
        sf.hide_render = sf.hide_viewport = True
    coast260()
    nt = s.world.node_tree
    sky = next(n for n in nt.nodes if n.type == 'TEX_SKY')
    for attr, v in (('aerosol_density', 6.0), ('dust_density', 5.0), ('air_density', 1.6)):
        if hasattr(sky, attr):
            setattr(sky, attr, v)
    bg = nt.nodes['Background']
    bg.inputs['Strength'].default_value = 0.55
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    rng = nt.nodes.new('ShaderNodeMapRange')
    rng.inputs['From Min'].default_value, rng.inputs['From Max'].default_value = 0.0, 0.5
    rng.clamp = True
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], rng.inputs['Value'])
    nt.links.new(rng.outputs['Result'], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (1.0, 0.54, 0.16, 1)
    els[1].position, els[1].color = 1.0, (0.60, 0.70, 0.88, 1)
    els.new(0.22).color = (1.0, 0.74, 0.40, 1)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['Factor'].default_value = 0.9
    nt.links.new(sky.outputs['Color'], mix.inputs[6])
    nt.links.new(ramp.outputs['Color'], mix.inputs[7])
    # the glow: a soft lobe around a point just above the horizon, 22 degrees left of where the camera looks
    cam = s.camera
    fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    az = math.atan2(fwd.x, fwd.y) - math.radians(22)
    elev = math.radians(2.5)
    sd = Vector((math.sin(az) * math.cos(elev), math.cos(az) * math.cos(elev), math.sin(elev)))
    dot = nt.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = sd
    nt.links.new(tc.outputs['Object'], dot.inputs[0])
    clampn = nt.nodes.new('ShaderNodeMath')
    clampn.operation, clampn.use_clamp = 'MAXIMUM', False
    clampn.inputs[1].default_value = 0.0
    nt.links.new(dot.outputs['Value'], clampn.inputs[0])
    pw = nt.nodes.new('ShaderNodeMath')
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 90.0
    nt.links.new(clampn.outputs[0], pw.inputs[0])
    wide = nt.nodes.new('ShaderNodeMath')              # a wider, fainter halo under the core
    wide.operation = 'POWER'
    wide.inputs[1].default_value = 12.0
    nt.links.new(clampn.outputs[0], wide.inputs[0])
    core = nt.nodes.new('ShaderNodeMath')
    core.operation = 'MULTIPLY'
    core.inputs[1].default_value = 14.0
    nt.links.new(pw.outputs[0], core.inputs[0])
    halo = nt.nodes.new('ShaderNodeMath')
    halo.operation = 'MULTIPLY'
    halo.inputs[1].default_value = 0.9
    nt.links.new(wide.outputs[0], halo.inputs[0])
    tot = nt.nodes.new('ShaderNodeMath')
    tot.operation = 'ADD'
    nt.links.new(core.outputs[0], tot.inputs[0])
    nt.links.new(halo.outputs[0], tot.inputs[1])
    gold = nt.nodes.new('ShaderNodeEmission')
    gold.inputs['Color'].default_value = (1.0, 0.66, 0.32, 1)
    nt.links.new(tot.outputs[0], gold.inputs['Strength'])
    nt.links.new(mix.outputs[2], bg.inputs['Color'])
    add = nt.nodes.new('ShaderNodeAddShader')
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    nt.links.new(bg.outputs['Background'], add.inputs[0])
    nt.links.new(gold.outputs['Emission'], add.inputs[1])
    nt.links.new(add.outputs['Shader'], out.inputs['Surface'])
    sun = bpy.data.objects['Sun']
    sun.data.color = (1.0, 0.64, 0.32)
    sun.data.energy = 3.4
    s.view_settings.exposure = -0.3


def _facade(name, wall):
    """Concrete facade with storeys and window rows by world position (3 m floors, 3.2 m bays from z = 2), glass with
    curtains, a few warm lit windows at dawn, slab lines, sunshade shadows, grime, and a flat grey roof on top faces."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N['Principled BSDF']
    geo = N.new('ShaderNodeNewGeometry')
    sp, sn = N.new('ShaderNodeSeparateXYZ'), N.new('ShaderNodeSeparateXYZ')
    L.new(geo.outputs['Position'], sp.inputs[0])
    L.new(geo.outputs['Normal'], sn.inputs[0])

    def op(o, a, b=None):
        n = N.new('ShaderNodeMath')
        n.operation = o
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                L.new(x, n.inputs[i])
        return n.outputs[0]

    def mix(f, a, b, rgba=True):
        n = N.new('ShaderNodeMix')
        n.data_type = 'RGBA' if rgba else 'FLOAT'
        ins = (n.inputs[6], n.inputs[7]) if rgba else (n.inputs[2], n.inputs[3])
        L.new(f, n.inputs[0]) if not isinstance(f, (int, float)) else None
        for sock, x in zip(ins, (a, b)):
            if isinstance(x, tuple):
                sock.default_value = (*x, 1) if rgba else x
            elif isinstance(x, (int, float)):
                sock.default_value = x
            else:
                L.new(x, sock)
        return n.outputs[2] if rgba else n.outputs[0]

    x, y, z = sp.outputs[0], sp.outputs[1], op('SUBTRACT', sp.outputs[2], 2.0)
    side = op('GREATER_THAN', op('ABSOLUTE', sn.outputs[0]), op('ABSOLUTE', sn.outputs[1]))   # faces +-X: runs along Y
    u = op('ADD', x, op('MULTIPLY', side, op('SUBTRACT', y, x)))
    v = op('ADD', y, op('MULTIPLY', side, op('SUBTRACT', x, y)))
    cu, cz = op('DIVIDE', u, 3.2), op('DIVIDE', z, 3.0)
    fu, fz = op('FRACT', cu), op('FRACT', cz)
    wall_ = op('LESS_THAN', op('ABSOLUTE', sn.outputs[2]), 0.5)
    win = op('MULTIPLY', op('MULTIPLY', op('GREATER_THAN', fu, 0.2), op('LESS_THAN', fu, 0.8)),
             op('MULTIPLY', op('GREATER_THAN', fz, 0.36), op('LESS_THAN', fz, 0.82)))
    win = op('MULTIPLY', win, op('MULTIPLY', wall_, op('GREATER_THAN', z, 3.0)))
    cc = N.new('ShaderNodeCombineXYZ')
    L.new(op('FLOOR', cu), cc.inputs[0])
    L.new(op('FLOOR', cz), cc.inputs[1])
    L.new(op('FLOOR', op('MULTIPLY', v, 0.5)), cc.inputs[2])
    wn = N.new('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    L.new(cc.outputs[0], wn.inputs['Vector'])
    r = wn.outputs['Value']
    lit = op('MULTIPLY', win, op('GREATER_THAN', r, 0.988))
    glass = mix(r, (0.02, 0.025, 0.03), (0.16, 0.14, 0.11))                 # dark glass to drawn curtains
    dn = N.new('ShaderNodeTexNoise')
    dn.inputs['Scale'].default_value = 0.09
    L.new(geo.outputs['Position'], dn.inputs['Vector'])
    grime = op('MULTIPLY', op('SUBTRACT', dn.outputs['Fac'], 0.35), 1.6)
    wallc = mix(grime, wall, (wall[0] * 0.55, wall[1] * 0.5, wall[2] * 0.45))   # monsoon staining
    shade = op('MULTIPLY', op('GREATER_THAN', fz, 0.82), op('LESS_THAN', fz, 0.9))  # sunshade shadow over the windows
    wallc = mix(shade, wallc, (wall[0] * 0.5, wall[1] * 0.5, wall[2] * 0.5))
    slab = op('LESS_THAN', fz, 0.06)
    wallc = mix(slab, wallc, (min(1, wall[0] * 1.15), min(1, wall[1] * 1.15), min(1, wall[2] * 1.15)))
    col = mix(win, wallc, glass)
    col = mix(op('SUBTRACT', 1.0, wall_), col, (0.36, 0.34, 0.31))           # flat concrete roofs
    L.new(col, bsdf.inputs['Base Color'])
    L.new(mix(win, 0.85, 0.12, rgba=False), bsdf.inputs['Roughness'])
    bsdf.inputs['Emission Color'].default_value = (1.0, 0.62, 0.3, 1)
    L.new(op('MULTIPLY', lit, 3.5), bsdf.inputs['Emission Strength'])
    return m


class _Geo:
    def __init__(self):
        self.v, self.f, self.m = [], [], []

    def box(self, x0, x1, y0, y1, z0, z1, mi):
        b = len(self.v)
        self.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append(tuple(b + i for i in f))
            self.m.append(mi)

    def cyl(self, cx, cy, r, z0, z1, mi, n=8):
        import math
        b = len(self.v)
        for k in range(n):
            a = 2 * math.pi * k / n
            self.v += [(cx + r * math.cos(a), cy + r * math.sin(a), z0), (cx + r * math.cos(a), cy + r * math.sin(a), z1)]
        for k in range(n):
            k2 = (k + 1) % n
            self.f.append((b + 2 * k, b + 2 * k2, b + 2 * k2 + 1, b + 2 * k + 1))
            self.m.append(mi)
        self.f.append(tuple(b + 2 * k + 1 for k in range(n)))
        self.m.append(mi)


def _building(g, rnd, x0, x1, y0, y1, zb, floors, mi, near):
    """One Indian RC-frame building: storeys, parapet, stair headroom, black water tanks; sometimes a set-back top
    floor or a lower wing, and sea-facing balconies on the near blocks."""
    TANK = 7
    top = zb + 3.0 * floors
    w, d = x1 - x0, y1 - y0
    k = rnd.random()
    if k < 0.22 and floors >= 3:                                  # lower wing along one side
        if w >= d:
            xs = x0 + w * rnd.uniform(0.45, 0.65)
            lo = max(1, floors - rnd.randint(1, 3))
            g.box(x0, xs, y0, y1, zb, top, mi)
            g.box(xs, x1, y0, y1, zb, zb + 3.0 * lo, mi)
            g.box(xs, x1, y0, y0 + 0.2, zb + 3.0 * lo, zb + 3.0 * lo + 0.95, mi)
            x1 = xs
        else:
            ys = y0 + d * rnd.uniform(0.35, 0.55)
            lo = max(1, floors - rnd.randint(1, 3))
            g.box(x0, x1, y0, ys, zb, zb + 3.0 * lo, mi)
            g.box(x0, x1, y0, y0 + 0.2, zb + 3.0 * lo, zb + 3.0 * lo + 0.95, mi)
            g.box(x0, x1, ys, y1, zb, top, mi)
            y0 = ys
    else:
        g.box(x0, x1, y0, y1, zb, top, mi)
    if near and floors >= 3:                                      # balconies on the sea (+Y) face
        bw = (x1 - x0) * rnd.uniform(0.35, 0.7)
        bx = rnd.uniform(x0, x1 - bw)
        for f in range(1, floors):
            g.box(bx, bx + bw, y1, y1 + 1.3, zb + 3.0 * f - 0.15, zb + 3.0 * f + 1.0, mi)
    if k > 0.78 and floors >= 3 and min(x1 - x0, y1 - y0) > 9:     # set-back top storey
        ix, iy = (x1 - x0) * 0.22, (y1 - y0) * 0.22
        g.box(x0 + ix, x1 - ix, y0 + iy, y1 - iy, top, top + 3.0, mi)
    for (a0, a1, b0, b1) in ((x0, x1, y0, y0 + 0.22), (x0, x1, y1 - 0.22, y1), (x0, x0 + 0.22, y0, y1), (x1 - 0.22, x1, y0, y1)):
        g.box(a0, a1, b0, b1, top, top + 0.95, mi)               # roof parapet
    hx, hy = rnd.uniform(x0 + 1, max(x0 + 1.1, x1 - 4.5)), rnd.uniform(y0 + 1, max(y0 + 1.1, y1 - 4))
    g.box(hx, hx + 3.2, hy, hy + 3.0, top, top + 2.7, mi)        # stair / lift headroom
    g.cyl(hx + 1.6, hy + 1.5, rnd.uniform(0.7, 1.0), top + 2.7, top + 4.2, TANK)   # tank on the headroom
    for _ in range(rnd.randint(0, 2)):
        tx, ty = rnd.uniform(x0 + 1.5, x1 - 1.5), rnd.uniform(y0 + 1.5, y1 - 1.5)
        g.cyl(tx, ty, rnd.uniform(0.6, 0.9), top, top + rnd.uniform(1.3, 1.8), TANK)


def _scrub(name, haze):
    """#260: dry scrub-forest hills (olive / brown-green ground, darker patchy scrub), mixed toward a dawn blue haze by
    `haze` (0 near .. 1 far). No pale grey: that read as snow."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.95
    b.inputs['Specular IOR Level'].default_value = 0.15           # no grazing sheen: that whitened the far ridges
    hz = (0.19, 0.24, 0.31)
    mixc = lambda c: tuple(a * (1 - haze) + h * haze for a, h in zip(c, hz)) + (1,)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ns = nt.nodes.new('ShaderNodeTexNoise')
    ns.inputs['Scale'].default_value = 0.012                      # scrub patches tens of metres across
    ns.inputs['Detail'].default_value = 8.0
    ns.inputs['Roughness'].default_value = 0.65
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.42, mixc((0.055, 0.07, 0.035))   # dark scrub
    cr.elements[1].position, cr.elements[1].color = 0.62, mixc((0.17, 0.15, 0.085))    # dry olive-brown ground
    cr.elements.new(0.52).color = mixc((0.10, 0.11, 0.055))                             # green-brown
    nt.links.new(ns.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


def coast260():
    """#260: a real coastal city seen from the sea at dawn instead of boxes. The port's city blocks are kept only as
    plots: each is split into 1-4 buildings with setbacks, G+1 to G+9 RC-frame blocks (taller along the beach road, a few
    towers), parapets, stair headrooms, black water tanks, balconies, window rows and a few lit windows; houses thin out
    up the lower hill slopes. Plus aerial perspective: bluer, hazier hills."""
    import math
    import random
    import numpy as np
    from bpy_extras.object_utils import world_to_camera_view as w2c
    s = bpy.context.scene
    rnd = random.Random(260)
    city = bpy.data.objects.get('LAND_City')
    tanks = bpy.data.objects.get('LAND_RoofTanks')
    if tanks is not None:                                             # they sat on the old box roofs
        tanks.hide_render = tanks.hide_viewport = True
    hills = bpy.data.objects.get('HERO_Hills')
    walls = [(0.62, 0.60, 0.56), (0.64, 0.56, 0.42), (0.62, 0.46, 0.37), (0.46, 0.52, 0.56), (0.62, 0.56, 0.34),
             (0.40, 0.39, 0.37), (0.48, 0.53, 0.42)]
    mats = [_facade('STILL_Facade%d' % i, c) for i, c in enumerate(walls)]
    tk = bpy.data.materials.new('STILL_WaterTank')
    tk.use_nodes = True
    tk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.03, 0.03, 0.032, 1)
    tk.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5
    WEIGHTS = (5, 3, 2, 2, 1, 3, 1)
    g = _Geo()
    if city is not None:
        me = city.data
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 8, 3)                                     # the city mesh is one 8-vertex box per plot
        assert float(np.max(co.max(1) - co.min(1))) < 300, 'LAND_City is not plot boxes'
        lo, hi = co.min(1), co.max(1)
        tall = (hi[:, 2] - lo[:, 2]) > 1.0
        co[:, :, 2] = float(lo[:, 2].min())                             # old boxes (and stray roof plates) flattened to plots
        me.vertices.foreach_set('co', co.ravel())
        me.update()
        mw = city.matrix_world
        for (x0, y0, z0), (x1, y1, _z1), t in zip(lo.tolist(), hi.tolist(), tall.tolist()):
            if not t or y1 < -2500 or z0 > 4.0:                      # (skip parts stacked on other boxes)
                continue
            p = w2c(s, s.camera, mw @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, z0)))
            if p.z <= 0 or not (-0.05 < p.x < 1.05 and -0.05 < p.y < 1.2):
                continue
            (x0, y0, z0), (x1, y1) = mw @ Vector((x0, y0, z0)), (mw @ Vector((x1, y1, 0)))[:2]
            dist = -(y0 + y1) / 2                                     # inland from the beach road
            zb = 2.0 + 3.0 * round((z0 - 2.0) / 3.0)
            nx = 2 if x1 - x0 > 30 else 1
            ny = 2 if y1 - y0 > 30 else 1
            for i in range(nx):
                for j in range(ny):
                    a0, a1 = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
                    b0, b1 = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
                    sb = rnd.uniform(1.0, 2.6)                        # setbacks from the plot edge
                    a0, a1, b0, b1 = a0 + sb, a1 - rnd.uniform(1.0, 2.6), b0 + rnd.uniform(1.0, 2.6), b1 - sb
                    if a1 - a0 < 6 or b1 - b0 < 6:
                        continue
                    q = rnd.random()
                    if dist < 450:
                        floors = rnd.randint(11, 22) if q < 0.12 else rnd.randint(4, 10)
                    elif dist < 1300:
                        floors = rnd.randint(9, 15) if q < 0.04 else rnd.randint(2, 6)
                    else:
                        floors = rnd.randint(6, 9) if q < 0.01 else rnd.randint(1, 4)
                    if floors >= 11:                                  # slim tower on the plot
                        cx, cy = (a0 + a1) / 2, (b0 + b1) / 2
                        hw, hd = min(11.0, (a1 - a0) / 2), min(11.0, (b1 - b0) / 2)
                        a0, a1, b0, b1 = cx - hw, cx + hw, cy - hd, cy + hd
                    mi = rnd.choices(range(len(walls)), WEIGHTS)[0]
                    _building(g, rnd, a0, a1, b0, b1, zb, floors, mi, dist < 900)
    if hills is not None:                                             # houses thinning out up the hill slopes
        dg = bpy.context.evaluated_depsgraph_get()
        hw_ = hills.matrix_world.inverted()
        for yy in range(-2500, -4400, -13):
            for xx in range(-4000, 6000, 13):
                x, y = xx + rnd.uniform(-4, 4), yy + rnd.uniform(-4, 4)
                o_ = hw_ @ Vector((x, y, 2000.0))
                hit, loc, _n, _i = hills.ray_cast(o_, Vector((0, 0, -1)))
                if not hit:
                    continue
                zh = (hills.matrix_world @ loc).z
                if zh < 3 or zh > 45 or rnd.random() > 0.9 * min(1.0, (45 - zh) / 30) ** 1.5:   # lower slopes only: higher up they read as floating confetti
                    continue
                p = w2c(s, s.camera, Vector((x, y, zh)))
                if p.z <= 0 or not (-0.05 < p.x < 1.05 and -0.05 < p.y < 1.2):
                    continue
                w, d = rnd.uniform(8, 12), rnd.uniform(7, 11)
                zb = 2.0 + 3.0 * math.floor((zh - 3.0) / 3.0)
                _building(g, rnd, x - w / 2, x + w / 2, y - d / 2, y + d / 2, zb, rnd.randint(1, 3),
                          8 + rnd.choices(range(len(walls)), WEIGHTS)[0], False)   # hazed: 3-4 km off
    me = bpy.data.meshes.new('STILL_City')
    me.from_pydata(g.v, [], g.f)
    me.polygons.foreach_set('material_index', g.m)
    haze = [_facade('STILL_FacadeHaze%d' % i, tuple(c_ * 0.45 + h_ * 0.55 for c_, h_ in zip(c, (0.42, 0.46, 0.52))))
            for i, c in enumerate(walls)]
    for m in mats + [tk] + haze:
        me.materials.append(m)
    me.update()
    o = bpy.data.objects.new('STILL_City', me)
    s.collection.objects.link(o)
    print('STILL coast260: %d faces' % len(g.f))
    hills = bpy.data.objects.get('HERO_Hills')
    if hills is not None and hills.data.materials:                     # Eastern Ghats scrub forest, hazed a little
        hills.data.materials[0] = _scrub('STILL_HillsHaze', 0.25)
    if hills is not None:                                               # layered ridges: each further one lighter and bluer
        fwd = s.camera.matrix_world.to_quaternion() @ Vector((0, 0, -1)) if s.camera else Vector((0, 1, 0))
        fwd.z = 0
        fwd.normalize()
        for k, (dist, sz, hz) in enumerate(((500.0, 0.75, 0.45), (1100.0, 1.35, 0.65))):
            h2 = hills.copy()
            h2.data = hills.data.copy()
            s.collection.objects.link(h2)
            h2.location = hills.location + fwd * dist
            h2.scale = (1.0, 1.0, sz)
            h2.data.materials[0] = _scrub('STILL_HillsFar%d' % k, hz)
    w = s.world
    nt = w.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Color'].default_value = (1.0, 0.82, 0.62, 1)
    vs.inputs['Density'].default_value = 0.00004
    vs.inputs['Anisotropy'].default_value = 0.55
    # nt.links.new(vs.outputs['Volume'], out.inputs['Volume'])

