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
    '255b': ((2.2, -17.5, 2.3), (9.3, -6.5, 2.1), 34),
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


def _tint(mat, col, name):
    m = mat.copy()
    m.name = name
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bc = b.inputs['Base Color']
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type, mx.blend_type = 'RGBA', 'MULTIPLY'
    mx.inputs['Factor'].default_value = 1.0
    mx.inputs[7].default_value = (*col, 1)
    if bc.links:
        nt.links.new(bc.links[0].from_socket, mx.inputs[6])
    else:
        mx.inputs[6].default_value = bc.default_value
    nt.links.new(mx.outputs[2], bc)
    return m


def coast260():
    """#260: varied coastal buildings (heights, gable and flat roofs, white / sand / terracotta / pale blue washes) instead of
    one block city, and aerial perspective: bluer, hazier hills under a thin warm haze volume."""
    import bmesh
    import random
    s = bpy.context.scene
    rnd = random.Random(11)
    city = bpy.data.objects.get('LAND_City')
    if city is not None and city.data.materials:
        base = city.data.materials[0]
        tints = [(1.0, 1.0, 1.0), (1.0, 0.86, 0.68), (0.95, 0.62, 0.48), (0.78, 0.88, 0.95), (0.96, 0.93, 0.82)]
        mats = [_tint(base, c, 'STILL_Bld%d' % i) for i, c in enumerate(tints)]
        me = city.data
        me.materials.clear()
        for m in mats:
            me.materials.append(m)
        bm = bmesh.new()
        bm.from_mesh(me)
        seen = set()
        extra = []
        for v0 in list(bm.verts):                                  # snapshot: new roof verts are not new islands
            if v0 in seen:
                continue
            stack, isl = [v0], []
            seen.add(v0)
            while stack:
                v = stack.pop()
                isl.append(v)
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            zs = [v.co.z for v in isl]
            z0, top = min(zs), max(zs)
            fcs = {f for v in isl for f in v.link_faces}
            mi = rnd.randrange(len(mats))
            for f in fcs:
                f.material_index = mi
            k = rnd.choice((0.5, 0.65, 0.8, 1.0, 1.0, 1.25, 1.6))             # heights differ block to block
            for v in isl:
                v.co.z = z0 + (v.co.z - z0) * k
            xs = [v.co.x for v in isl]
            ys = [v.co.y for v in isl]
            zt = max(v.co.z for v in isl)
            w_, d_ = max(xs) - min(xs), max(ys) - min(ys)
            if min(w_, d_) < 3.0 or w_ > 60 or d_ > 60 or z0 > 2.0 or zt - z0 < 5.0:     # real buildings only: nothing perched on roofs
                continue
            extra.append((rnd.random(), min(xs), max(xs), min(ys), max(ys), zt, mi))
        bm.to_mesh(me)
        bm.free()
        # roofs and upper storeys as separate small meshes on top of the blocks (no edits to the big city mesh)
        eb = bmesh.new()
        for kind, x0, x1, y0, y1, zt, mi in extra:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w_, d_ = x1 - x0, y1 - y0

            def quad(a, b, c, d):
                eb.faces.new([eb.verts.new(p_) for p_ in (a, b, c, d)]).material_index = mi + 5
            if kind < 0.40:                                            # gable roof, ridge along the long side
                h = min(w_, d_) * (0.28 + 0.3 * rnd.random())
                if w_ >= d_:
                    r0, r1 = (x0, cy, zt + h), (x1, cy, zt + h)
                    quad((x0, y0, zt), (x1, y0, zt), r1, r0)
                    quad((x1, y1, zt), (x0, y1, zt), r0, r1)
                    for xx in (x0, x1):
                        eb.faces.new([eb.verts.new(p_) for p_ in ((xx, y0, zt), (xx, y1, zt), (xx, cy, zt + h))]).material_index = mi + 5
                else:
                    r0, r1 = (cx, y0, zt + h), (cx, y1, zt + h)
                    quad((x0, y0, zt), (x0, y1, zt), r1, r0)
                    quad((x1, y1, zt), (x1, y0, zt), r0, r1)
                    for yy in (y0, y1):
                        eb.faces.new([eb.verts.new(p_) for p_ in ((x0, yy, zt), (x1, yy, zt), (cx, yy, zt + h))]).material_index = mi + 5
            elif kind < 0.65:                                          # set-back upper storey
                ix, iy = w_ * 0.26, d_ * 0.26
                hh = 3.2 + 6.0 * rnd.random()
                bx0, bx1, by0, by1 = x0 + ix, x1 - ix, y0 + iy, y1 - iy
                p8 = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
                for k in range(4):
                    a_, b_ = p8[k], p8[(k + 1) % 4]
                    quad((a_[0], a_[1], zt), (b_[0], b_[1], zt), (b_[0], b_[1], zt + hh), (a_[0], a_[1], zt + hh))
                quad((bx0, by0, zt + hh), (bx1, by0, zt + hh), (bx1, by1, zt + hh), (bx0, by1, zt + hh))
            elif kind < 0.80:                                          # slim lift tower
                tw = min(w_, d_) * 0.22
                hh = 5 + 9 * rnd.random()
                tx0, tx1, ty0, ty1 = cx - tw, cx + tw, cy - tw, cy + tw
                for a_, b_ in (((tx0, ty0), (tx1, ty0)), ((tx1, ty0), (tx1, ty1)), ((tx1, ty1), (tx0, ty1)), ((tx0, ty1), (tx0, ty0))):
                    quad((a_[0], a_[1], zt), (b_[0], b_[1], zt), (b_[0], b_[1], zt + hh), (a_[0], a_[1], zt + hh))
                quad((tx0, ty0, zt + hh), (tx1, ty0, zt + hh), (tx1, ty1, zt + hh), (tx0, ty1, zt + hh))
        for f in eb.faces:
            f.normal_update()
        em = bpy.data.meshes.new('STILL_BldExtra')
        eb.to_mesh(em)
        eb.free()
        roof_cols = [(0.60, 0.26, 0.17), (0.72, 0.70, 0.66), (0.52, 0.30, 0.22), (0.40, 0.44, 0.48), (0.66, 0.52, 0.34)]
        for i_, col in enumerate(tints):
            mat = bpy.data.materials.new('STILL_Roof%d' % i_)
            mat.use_nodes = True
            mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*roof_cols[i_ % len(roof_cols)], 1)
            mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.75
            em.materials.clear() if i_ == 0 else None
        em.materials.clear()
        for m in mats:
            em.materials.append(m)
        for i_ in range(len(tints)):
            mat = bpy.data.materials.new('STILL_RoofM%d' % i_)
            mat.use_nodes = True
            mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*roof_cols[i_], 1)
            mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.75
            em.materials.append(mat)
        eo = bpy.data.objects.new('STILL_BldExtra', em)
        s.collection.objects.link(eo)
    hills = bpy.data.objects.get('HERO_Hills')
    if hills is not None and hills.data.materials:
        hm = hills.data.materials[0].copy()
        hm.name = 'STILL_HillsHaze'
        nt = hm.node_tree
        b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (0.33, 0.37, 0.40, 1)        # far hills read blue-grey
        b.inputs['Roughness'].default_value = 0.95
        hills.data.materials[0] = hm
    if hills is not None:                                               # layered ridges: each further one lighter and bluer
        fwd = s.camera.matrix_world.to_quaternion() @ Vector((0, 0, -1)) if s.camera else Vector((0, 1, 0))
        fwd.z = 0
        fwd.normalize()
        for k, (dist, sz, col) in enumerate(((500.0, 0.75, (0.43, 0.49, 0.55)), (1100.0, 1.35, (0.56, 0.62, 0.70)))):
            h2 = hills.copy()
            h2.data = hills.data.copy()
            s.collection.objects.link(h2)
            h2.location = hills.location + fwd * dist
            h2.scale = (1.0, 1.0, sz)
            m2 = hills.data.materials[0].copy()
            m2.name = 'STILL_HillsFar%d' % k
            b2 = next(n for n in m2.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            b2.inputs['Base Color'].default_value = (*col, 1)
            h2.data.materials[0] = m2
    w = s.world
    nt = w.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Color'].default_value = (1.0, 0.82, 0.62, 1)
    vs.inputs['Density'].default_value = 0.00004
    vs.inputs['Anisotropy'].default_value = 0.55
    # nt.links.new(vs.outputs['Volume'], out.inputs['Volume'])

