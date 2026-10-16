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
    sid = sid.rstrip('abcdeghijklmnopqrstuvwxyz')      # preview variants (255q, 258b) get their base still's fixes; 246f keeps its f
    black = bpy.data.materials.get('STILL_Black')
    if black is None:
        black = bpy.data.materials.new('STILL_Black')
        black.use_nodes = True
        b = black.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.012, 0.012, 0.014, 1)
        b.inputs['Roughness'].default_value = 0.38
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('TRK_RigidReefer') and o.name.endswith(('_Mirrors', '_CabSeals', '_CabSeams', '_CabInterior')):
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
    glass = bpy.data.materials.get('TRK_Glass')       # clearer glass: the driver reads through the windscreen and the door window
    if glass is not None and glass.node_tree:
        b = glass.node_tree.nodes.get('Principled BSDF')
        if b is not None:
            b.inputs['Alpha'].default_value = 0.1
            b.inputs['Coat Weight'].default_value = 0.35
    if sid == '258':                      # the quay shot: the tugs stay out of it
        for o in bpy.data.objects:
            if o.name.startswith('TUG'):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True
    if sid in ('246', '246f', '256'):     # the waiting trolley worker at the right edge would be cut off by the frame
        for o in bpy.data.objects:
            if o.name.startswith('HUM_DockW6') or (sid == '256' and o.name.startswith('HUM_DockW5')):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True
    if sid == '255':
        for o in bpy.data.objects:
            if o.name.startswith(('TRK_Parked', 'YD_Forklift', 'HUM_YardW', 'HUM_Banksman', 'HUM_Carrier', 'HUM_JackPusher', 'HUM_GateGuard')):
                for c in [o] + list(o.children_recursive):
                    c.hide_render = c.hide_viewport = True


def apply_all(sid=''):
    apply()
    gowns()
    truck_fittings(sid)
