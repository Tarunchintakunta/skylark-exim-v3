"""Hand-framed cameras for the composition stills (#255, #256, #246): a static camera per still, so the frame is the
composition and not wherever the animated move happens to be. Coordinates are the plant set's (dock wall y = 0, the
truck bay at x = 9.2, the dock floor 1.2 m up, the hall behind the wall at y > 0)."""
import bpy
from mathutils import Vector

# 256: eye level, 1.65 m over the dock floor, square on to the open door, a steel-crate trolley each side
# id: (location, look-at target, focal length mm)
CAMS = {
    # truck parked square to bay 2 (facing -Y, rear at the wall), seen from its right-hand side, its driver at the window
    '255': ((2.8, -13.5, 1.9), (8.6, -5.2, 1.75), 28),
    # eye level (1.65 m) inside the hall, looking out along the intake line to the open dock door
    '256': ((9.2, 7.0, 2.85), (9.2, 1.5, 2.35), 40),
}


def apply(sid, env=None):
    if sid not in CAMS:
        return
    loc, tgt, lens = CAMS[sid]
    s = bpy.context.scene
    cam = bpy.data.objects.new('STILL_Camera', bpy.data.cameras.new('STILL_Camera'))
    s.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start, cam.data.clip_end = 0.1, 400
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    s.camera = cam


def look(sid):
    """#260: a soft golden horizon. The sun sits lower and warmer, the haze thickens along the horizon and the exposure
    comes up from the pre-sunrise dark; nothing in the frame changes."""
    if sid != '260':
        return
    import math
    s = bpy.context.scene
    sky = next(n for n in s.world.node_tree.nodes if n.type == 'TEX_SKY')
    elev = math.radians(3.0)
    az = sky.sun_rotation
    sky.sun_elevation = elev
    for attr, v in (('aerosol_density', 6.0), ('dust_density', 5.0), ('air_density', 1.6)):
        if hasattr(sky, attr):
            setattr(sky, attr, v)
    # the physical sky is cool away from the sun: lay a golden band over the horizon, fading up into a pale morning blue
    nt = s.world.node_tree
    bg = nt.nodes['Background']
    bg.inputs['Strength'].default_value = 0.55
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    rng = nt.nodes.new('ShaderNodeMapRange')
    rng.inputs['From Min'].default_value, rng.inputs['From Max'].default_value = 0.0, 0.5   # direction z: horizon to 30 degrees up
    rng.clamp = True
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], rng.inputs['Value'])
    nt.links.new(rng.outputs['Result'], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (1.0, 0.54, 0.16, 1)
    els[1].position, els[1].color = 1.0, (0.60, 0.70, 0.88, 1)
    mid = els.new(0.22)
    mid.color = (1.0, 0.74, 0.40, 1)
    mix.inputs['Factor'].default_value = 0.9
    nt.links.new(sky.outputs['Color'], mix.inputs[6])
    nt.links.new(ramp.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], bg.inputs['Color'])
    sun = bpy.data.objects['Sun']
    d = Vector((math.sin(az) * math.cos(elev), math.cos(az) * math.cos(elev), math.sin(elev)))
    sun.rotation_mode = 'QUATERNION'
    sun.rotation_quaternion = (-d).to_track_quat('-Z', 'Y')
    sun.data.color = (1.0, 0.64, 0.32)
    sun.data.energy = 3.4
    s.view_settings.exposure = -0.3
