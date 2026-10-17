"""Scene touch-ups for the composition stills, applied after load and before render or rule check (#255-#260).
- hull draft numerals (SHIP_Draft*) are text, and the stills carry no text: hidden;
- the yard's reefer racks use a generic black material named MAT_PlasticBlack: they are steel frames, so they get a dark steel one."""
import bpy


def apply():
    for o in bpy.data.objects:
        if o.type == 'FONT':
            o.hide_render = o.hide_viewport = True
    steel = bpy.data.materials.get('STILL_DarkSteel')
    if steel is None:
        steel = bpy.data.materials.new('STILL_DarkSteel')
        steel.use_nodes = True
        b = steel.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.05, 0.055, 0.06, 1)
        b.inputs['Metallic'].default_value = 0.9
        b.inputs['Roughness'].default_value = 0.42
    for o in bpy.data.objects:
        if o.type == 'MESH' and 'ReeferRacks' in o.name:
            for sl in o.material_slots:
                if sl.material and 'PlasticBlack' in sl.material.name:
                    sl.material = steel


def crane_paint():
    """#258: quay cranes are painted light-grey steel, not the library's rust-camouflage grime."""
    paint = bpy.data.materials.get('STILL_CranePaint')
    if paint is None:
        paint = bpy.data.materials.new('STILL_CranePaint')
        paint.use_nodes = True
        b = paint.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.62, 0.64, 0.66, 1)
        b.inputs['Metallic'].default_value = 0.15
        b.inputs['Roughness'].default_value = 0.42
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('Crane_'):
            for sl in o.material_slots:
                if sl.material and 'CraneWhite' in sl.material.name:
                    sl.material = paint


def gowns():
    """Plain gowns (#256, #246): the library's white cotton coat and trousers are offset copies of the body, so they carry its
    chest and hips. A smooth over just those faces, with a small push outward so the skin does not show through, turns them
    into straight, loose gowns."""
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith('HUM_') or not o.name.endswith('_mesh') or o.get('gowned'):
            continue
        slots = [i for i, sl in enumerate(o.material_slots) if sl.material and 'WhiteCotton' in sl.material.name]
        if not slots:
            continue
        me = o.data
        vg = o.vertex_groups.get('GOWN') or o.vertex_groups.new(name='GOWN')
        idx = sorted({v for p in me.polygons if p.material_index in slots for v in p.vertices})
        vg.add(idx, 1.0, 'REPLACE')
        sm = o.modifiers.new('gown_smooth', 'SMOOTH')
        sm.factor, sm.iterations, sm.vertex_group = 0.9, 24, 'GOWN'
        d = o.modifiers.new('gown_push', 'DISPLACE')
        d.strength, d.mid_level, d.direction, d.vertex_group = 0.014, 0.0, 'NORMAL', 'GOWN'
        o['gowned'] = True


def truck_fittings(sid):
    """#255: matt black mirrors, seals and seams (the library's dark grey reads brown under the yard grade), and for the
    side view the two neighbouring parked trucks are hidden."""
    full = sid
    sid = sid.rstrip('abcdeghijklmnopqrstuvwxyz')      # preview variants (255q, 258b) get their base still's fixes; 246f keeps its f
    black = bpy.data.materials.get('STILL_Black')
    if black is None:
        black = bpy.data.materials.new('STILL_Black')
        black.use_nodes = True
        b = black.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.012, 0.012, 0.014, 1)
        b.inputs['Roughness'].default_value = 0.38
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('TRK_RigidReefer') and o.name.endswith(('_Mirrors', '_CabSeals', '_CabSeams', '_Arches', '_Mudguards', '_LampBezels')):
            o.data.materials.clear()
            o.data.materials.append(black)
    def flat(name, color, rough, metal=0.0):
        m = bpy.data.materials.get(name)
        if m is None:
            m = bpy.data.materials.new(name)
            m.use_nodes = True
            b = m.node_tree.nodes['Principled BSDF']
            b.inputs['Base Color'].default_value = (*color, 1)
            b.inputs['Roughness'].default_value = rough
            b.inputs['Metallic'].default_value = metal
        return m
    dash = flat('STILL_CabTrim', (0.045, 0.045, 0.048), 0.6)            # cab interior: dark grey moulded plastic, not black card
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('TRK_RigidReefer') and o.name.endswith(('_CabInterior', '_SteeringWheel')):
            o.data.materials.clear()
            o.data.materials.append(dash)
    tyre = flat('STILL_Tyre', (0.022, 0.022, 0.024), 0.72)               # road tyres: clean black rubber, no mud camouflage
    steel = flat('STILL_ChassisSteel', (0.06, 0.065, 0.07), 0.5, 0.55)    # chassis, flaps and bumper: dark painted steel
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith('TRK_RigidReefer'):
            continue
        tail = o.name[len('TRK_RigidReefer_'):]
        mat = tyre if tail.startswith('Wheel') else steel if tail in ('Chassis', 'Bumper', 'Flaps', 'RearFrame') else None
        if mat is not None:
            o.data.materials.clear()
            o.data.materials.append(mat)
    for o in bpy.data.objects:                        # forklift tyres: black rubber too, not the grimy library rubber
        if o.type == 'MESH' and o.name.startswith('YD_Forklift') and o.name.endswith('_Tyres'):
            o.data.materials.clear()
            o.data.materials.append(tyre)
    glass = bpy.data.materials.get('TRK_Glass')       # clearer glass: the driver reads through the windscreen and the door window
    if glass is not None and glass.node_tree:
        b = glass.node_tree.nodes.get('Principled BSDF')
        if b is not None:
            b.inputs['Alpha'].default_value = 0.16           # still reads as glass: a faint sky reflection
            b.inputs['Coat Weight'].default_value = 0.6
    if sid == '258':                      # the quay shot: the tugs stay out of it
        for o in bpy.data.objects:
            if o.name.startswith('TUG'):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True
    if sid in ('246', '246f') or sid.startswith('256'):   # (and the stiff standing supervisor, HUM_DockW5)     # the waiting trolley worker at the right edge would be cut off by the frame
        for o in bpy.data.objects:
            if o.name.startswith(('HUM_DockW6', 'HUM_DockW5')):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True
    if sid == '255':
        for o in bpy.data.objects:
            if o.name.startswith(('TRK_Parked', 'HUM_YardW', 'HUM_Banksman', 'HUM_JackPusher', 'HUM_GateGuard')):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True
        if full == '255':                    # the rear view: an empty dock, doors up, leveller down, truck outside
            for o in bpy.data.objects:
                if o.name.startswith('HUM_') and o.parent is None and 'Driver' not in o.name:
                    for c in [o] + list(o.children_recursive):
                        c.hide_render = c.hide_viewport = True


def _mat(name, col, rough, metal=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Metallic'].default_value = metal
        b.inputs['Roughness'].default_value = rough
    return m


def _box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.data.materials.append(mat)
    return o


def leveler(sid):
    """#255: the dock leveller engaged, its lip lying on the truck bed across the gap between the dock floor and the box."""
    if sid != '255':
        return
    st = _mat('STILL_Leveller', (0.42, 0.44, 0.46), 0.45, 1.0)
    _box('STILL_LevellerPlate', (9.2, -0.14, 1.265), (2.3, 0.78, 0.045), st, rot=(0.0, 0.0, 0.0))
    _box('STILL_LevellerHinge', (9.2, 0.27, 1.215), (2.3, 0.1, 0.05), st)
    for sx in (-1.1, 1.1):
        _box('STILL_LevellerGuard', (9.2 + sx, -0.14, 1.3), (0.04, 0.78, 0.1), st)


def props256(sid):
    """#256: a fuller bay: more stainless crates with crushed ice stacked by the dock wall, a pile of crushed ice on the mat
    and a wash-down hose coiled across the floor. Copies of the plant's own crates, so they match."""
    if not sid.startswith('256'):
        return
    import math
    import random
    from mathutils import Vector
    src = bpy.data.objects.get('PL_PushCrate0')
    if src is None:
        return
    s = bpy.context.scene
    s.frame_set(100)
    bpy.context.view_layer.update()

    def clone(o, mw, par=None):
        c = o.copy()
        c.data = o.data
        s.collection.objects.link(c)
        c.parent = par
        c.matrix_world = mw
        return c
    from mathutils import Matrix
    for k, (x, y, z, rz) in enumerate(((7.0, 0.9, 1.2, 0.2), (7.0, 0.9, 1.5, 0.15), (7.1, 1.7, 1.2, 0.1), (11.4, 0.9, 1.2, -0.1),
                                        (11.4, 0.9, 1.5, 0.1), (11.5, 1.7, 1.2, -0.2))):
        mw = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz + math.pi / 2, 4, 'Z')
        root = clone(src, mw)
        root.name = 'STILL_Crate%d' % k
        for ch in src.children_recursive:
            rel = src.matrix_world.inverted() @ ch.matrix_world
            clone(ch, mw @ rel, None).name = 'STILL_Crate%d_%s' % (k, ch.name[-6:])
    ice = _mat('STILL_Ice', (0.88, 0.94, 1.0), 0.25)
    random.seed(4)
    for i in range(70):
        a, r = random.uniform(0, 6.28), random.uniform(0, 0.55)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.025, 0.06),
                                              location=(10.6 + math.cos(a) * r, 3.0 + math.sin(a) * r * 0.7, 1.22 + random.uniform(0, 0.06)))
        o = bpy.context.active_object
        o.scale = (1, random.uniform(0.7, 1.2), random.uniform(0.6, 1.0))
        o.data.materials.append(ice)
        o.name = 'STILL_Ice%d' % i
    hose = bpy.data.curves.new('STILL_HoseCurve', 'CURVE')
    hose.dimensions = '3D'
    hose.bevel_depth, hose.bevel_resolution = 0.028, 4
    sp = hose.splines.new('POLY')
    pts = [(12.4, 0.2, 1.5), (12.2, 0.5, 1.23), (11.8, 1.6, 1.23), (11.9, 2.6, 1.23), (11.4, 3.5, 1.23), (10.4, 3.9, 1.23),
           (9.6, 3.5, 1.23), (9.9, 2.9, 1.23), (10.8, 2.5, 1.23)]
    sp.points.add(len(pts) - 1)
    for p_, v in zip(sp.points, pts):
        p_.co = (*v, 1)
    ho = bpy.data.objects.new('STILL_Hose', hose)
    s.collection.objects.link(ho)
    ho.data.materials.append(_mat('STILL_HoseRubber', (0.03, 0.12, 0.28), 0.5))


def frost257(sid):
    """#257: plain white export cartons under a thin, even frost (no grey speckle), the floor frost decal removed, steel racks
    kept, and two more workers in the aisle (copies of the cold-store checker, offset, so the motion is the plant's own)."""
    if not sid.startswith('257'):
        return
    for oname in ('IN_ColdStaged', 'IN_ColdStagedWood', 'IN_ColdAisleFrost'):
        o = bpy.data.objects.get(oname)
        if o is not None:
            o.hide_render = o.hide_viewport = True
    for oname, col, rough in (('IN_ColdCartons', (0.88, 0.88, 0.86), 0.62),):     # white, not beige (#257)
        o = bpy.data.objects.get(oname)
        if o is None:
            continue
        m = bpy.data.materials.new('STILL_FrostCarton')
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Roughness'].default_value = rough
        b.inputs['Metallic'].default_value = 0.0
        noi = nt.nodes.new('ShaderNodeTexNoise')               # fine, even frost: small scale, low contrast
        noi.inputs['Scale'].default_value = 260.0
        noi.inputs['Detail'].default_value = 3.0
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nt.links.new(tc.outputs['Object'], noi.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.inputs[6].default_value = (*col, 1)
        mx.inputs[7].default_value = (0.93, 0.96, 1.0, 1)
        mx.inputs['Factor'].default_value = 0.32
        nt.links.new(noi.outputs['Fac'], mx.inputs['Factor'])
        nt.links.new(mx.outputs[2], b.inputs['Base Color'])
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.12
        nt.links.new(noi.outputs['Fac'], bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
        o.data.materials.clear()
        o.data.materials.append(m)


def crew257(sid):
    """#257: different faces and white cartons. The four cold-store workers in frame each get their own skin (fixed tone
    from dark to medium-light brown, beard or clean-shaven, one older man with greying stubble and brows) and a broader or
    narrower head / jaw / nose, so they read as four different Visakhapatnam workers; every carton in frame is white."""
    if not sid.startswith('257'):
        return
    # name: (tone 0 dark .. 1 medium brown, older, head xyz, jaw, nose); tone value also picks stubble / beard in the shader
    crew = {'HUM_ColdW3': (0.78, False, (1.04, 1.0, 0.97), 1.06, 1.16),      # medium brown, short beard, broad jaw
            'HUM_ColdW2': (0.93, False, (0.95, 0.98, 1.03), 0.95, 1.02),     # lighter brown woman, narrow face
            'HUM_Cold': (0.12, True, (1.02, 1.03, 1.0), 1.0, 1.20),          # dark, older: greying stubble and brows
            'HUM_ColdCheck': (0.45, False, (0.97, 1.02, 1.05), 1.03, 1.08)}  # mid brown, long face
    for nm, (tone, old, hs, jaw, nose) in crew.items():
        w = bpy.data.objects.get(nm)
        if w is None:
            continue
        for mo in [c for c in w.children if c.type == 'MESH']:
            for sl in mo.material_slots:
                if not (sl.material and sl.material.name.startswith('HUM_Skin')):
                    continue
                m = sl.material.copy()
                m.name = 'STILL_Skin_' + nm
                nt = m.node_tree
                v = nt.nodes.new('ShaderNodeValue')
                v.outputs[0].default_value = tone
                for oi in [n for n in nt.nodes if n.type == 'OBJECT_INFO']:
                    for lk in list(oi.outputs['Random'].links):
                        nt.links.new(v.outputs[0], lk.to_socket)
                if old:
                    for n in nt.nodes:
                        if n.type == 'MIX' and n.data_type == 'RGBA' and not n.inputs[7].is_linked and \
                                max(n.inputs[7].default_value[:3]) < 0.02:
                            n.inputs[7].default_value = (0.30, 0.29, 0.28, 1)
                sl.link = 'OBJECT'
                sl.material = m
        pb = w.pose.bones
        if 'head' in pb:
            pb['head'].scale = hs
        if 'jaw' in pb:
            pb['jaw'].scale = (jaw, 1.0, pb['jaw'].scale[2])
        if 'nose' in pb:
            pb['nose'].scale = (nose, pb['nose'].scale[1], pb['nose'].scale[2])
    white = _mat('STILL_WhiteCarton', (0.88, 0.88, 0.86), 0.6)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('IN_Cold') and 'Carton' in o.name and o.name != 'IN_ColdCartons':
            for sl in o.material_slots:
                sl.link = 'OBJECT'
                sl.material = white
    seams = bpy.data.objects.get('IN_ColdBoxSeams')      # its seam / underside slabs read as dark boxes on the shelves
    if seams is not None:
        seams.hide_render = seams.hide_viewport = True


def _fcurves(act):
    if act is None:
        return []
    if getattr(act, 'fcurves', None) is not None:
        return list(act.fcurves)
    return [fc for ly in act.layers for st in ly.strips for cb in st.channelbags for fc in cb.fcurves]


def carry246(sid, frame=62):
    """#246 beat 3: both unloaders hold the one crate between them, one at each grab bar, gloves wrapped over the bar,
    feet planted (no walk-cycle kick). Staged at the still frame only: the film's own carry is unchanged."""
    if sid not in ('246', '246f'):
        return
    import math
    from mathutils import Matrix, Vector
    import skhuman as H
    s = bpy.context.scene
    s.frame_set(frame)
    DZ = 1.2
    crate = bpy.data.objects['TRK_RigidReefer_Cargo08']
    ctr = Vector((9.2, 0.42))                        # W1 clear of the crate on trolley A (Cargo02)
    u = Vector((1.0, 0.0))                           # crate's bar axis, W1 -> W2
    crate.animation_data_clear()
    crate.matrix_world = Matrix.Translation((ctr.x, ctr.y, DZ + 0.70)) @ Matrix.Rotation(math.atan2(-u.x, u.y), 4, 'Z')
    legs = {'hips': (0, 0, 0), 'spine': (12, 0, 0), 'thigh.L': (12, 3, 0), 'shin.L': (-14, 0, 0), 'foot.L': (3, 0, 0),
            'thigh.R': (2, 3, 0), 'shin.R': (-6, 0, 0), 'foot.R': (2, 0, 0)}
    for nm, sg in (('HUM_DockW1', -1), ('HUM_DockW2', 1)):
        w = bpy.data.objects[nm]
        mo = w.children[0]
        for fc in _fcurves(w.animation_data.action if w.animation_data else None):
            if fc.data_path in ('location', 'rotation_euler') or any('"%s"' % b in fc.data_path for b in legs) or \
                    '.constraints[' in fc.data_path:      # the film's IK influence keys would drive the new same-named IK
                fc.mute = True
        p = ctr + u * sg * 0.66
        face = -u * sg
        w.location = (p.x, p.y, DZ - 0.01)
        w.rotation_euler = (0, 0, math.atan2(face.x, -face.y))
        for b, v in legs.items():
            H._rot(w.pose.bones[b], *v, b.split('.')[-1] if '.' in b else '')
        for sd in 'LR':                              # the film's carry / door IK and hand tracks off (removed: the legacy IK
            for b in ('forearm.', 'hand.'):          # solver still blends a muted IK into the chain)
                cs = w.pose.bones[b + sd].constraints
                for c in list(cs):
                    cs.remove(c)
        if mo.data.shape_keys:                       # the film's finger grips off: new ones close on this bar
            for kb in mo.data.shape_keys.key_blocks:
                if kb.name.startswith('grip'):
                    kb.value = 0.0
            ad = mo.data.shape_keys.animation_data
            for fc in _fcurves(ad.action if ad else None):
                fc.mute = True
        by = sg * 0.258                              # this worker's bar, crate local y; fingers point in over it
        for sd, bx in (('L', 0.06 * sg), ('R', -0.06 * sg)):
            H.wrap_hand(w, sd, crate, (bx, by + sg * 0.02, 0.275), (0, -sg * 0.8, 0.6), (0, -sg * 0.6, -0.8), [(1, 1.0)],
                        s.collection)                # palm on the bar's outer top, fingers over it and down behind
            ik = [c for c in w.pose.bones['forearm.' + sd].constraints if c.type == 'IK' and not c.mute][-1]
            pole = bpy.data.objects.get('%s_CarryPole%s' % (nm, sd))
            if pole is not None:
                ik.pole_target, ik.pole_angle = pole, math.radians(-90)
    s.frame_set(frame)
    bpy.context.view_layer.update()
    for nm in ('HUM_DockW1', 'HUM_DockW2'):
        for sd in 'LR':
            H.grip(bpy.data.objects[nm], sd, target=[crate], curl=1.0)


def apply_all(sid=''):
    apply()
    crane_paint()
    gowns()
    truck_fittings(sid)
    leveler(sid)
    props256(sid)
    frost257(sid)
    crew257(sid)
    carry246(sid)
