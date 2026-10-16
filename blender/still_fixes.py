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
