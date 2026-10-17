"""Homepage hero (#260): a slow continuous push from the sea toward the coast and the harbour at dawn.
  Blender -b assets-src/blender/port_v3.3.blend --python blender/hero_dawn.py -- assets-src/blender/hero-dawn.blend
The port world (coast, city, breakwaters, harbour with the loaded ship at the quay) under a low dawn sun from the sea
behind the lens. The harbour sits right of centre; the bottom-left third is open water in the shadowed side of the
frame, calm and dark for the headline. No text or logos are added. 6 s at 24 fps, rendered at 2560x1440 or more."""
import math
import sys
import bpy
from mathutils import Vector

FRAMES = 144
CAM = [(1, (-260.0, 2300.0, 120.0), (330.0, 120.0, 30.0)),        # (frame, camera, look-at)
       (FRAMES, (-200.0, 1500.0, 92.0), (220.0, 100.0, 28.0))]
SUN_ELEV, SUN_AZ = math.radians(2.5), math.radians(40.0)          # azimuth from +Y (sea) toward +X (east)

s = bpy.context.scene
for n in ('FARSHIP0', 'FARSHIP2'):           # anchorage ships that would cross the calm left third / leave the frame
    bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)


def hills():
    """Hazy coastal hills behind the city (a generic ridge line, no specific landmark): a displaced grid rising
    from 2.5 km inland to 250-420 m, far enough back to sit in the dawn haze."""
    import bmesh
    from mathutils import noise
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=220, y_segments=60, size=0.5)
    for v in bm.verts:
        x, y = v.co.x * 16000, -2500 - (v.co.y + 0.5) * 4500
        rise = min(1.0, max(0.0, (-y - 2500) / 1600))
        h = 250 + 170 * noise.noise(Vector((x / 2600, y / 2600, 0.3)))
        h += 60 * noise.noise(Vector((x / 700, y / 700, 1.7)))
        v.co = Vector((x, y, max(0.0, h * rise * rise * (3 - 2 * rise))))
    me = bpy.data.meshes.new('HERO_Hills')
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    m = bpy.data.materials.new('HERO_HillScrub')
    m.use_nodes = True
    pb = m.node_tree.nodes['Principled BSDF']
    pb.inputs['Base Color'].default_value = (0.05, 0.07, 0.045, 1)
    pb.inputs['Roughness'].default_value = 0.9
    me.materials.append(m)
    o = bpy.data.objects.new('HERO_Hills', me)
    s.collection.objects.link(o)


hills()
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']:
    bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('HERO_Camera', bpy.data.cameras.new('HERO_Camera'))
s.collection.objects.link(cam)
cam.data.lens = 32
cam.data.clip_end = 20000
tgt = bpy.data.objects.new('HERO_Target', None)
s.collection.objects.link(tgt)
tr = cam.constraints.new('TRACK_TO')
tr.target, tr.track_axis, tr.up_axis = tgt, 'TRACK_NEGATIVE_Z', 'UP_Y'
for f, c, t in CAM:
    cam.location, tgt.location = c, t
    cam.keyframe_insert('location', frame=f)
    tgt.keyframe_insert('location', frame=f)
for o in (cam, tgt):                     # ease in and out: one unbroken, unhurried push
    for fc in getattr(o.animation_data.action, 'fcurves', ()):
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'
            k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
s.camera = cam
s.frame_start, s.frame_end = 1, FRAMES

# dawn: low warm sun from the sea behind the lens, physical sky to match
sun = bpy.data.objects['Sun']
d = Vector((math.sin(SUN_AZ) * math.cos(SUN_ELEV), math.cos(SUN_AZ) * math.cos(SUN_ELEV), math.sin(SUN_ELEV)))
sun.rotation_mode = 'QUATERNION'
sun.rotation_quaternion = (-d).to_track_quat('-Z', 'Y')
sun.data.energy = 2.6
sun.data.color = (1.0, 0.72, 0.5)
sun.data.angle = math.radians(1.2)
w = bpy.data.worlds.new('WORLD_Dawn')
w.use_nodes = True
nt = w.node_tree
sky = nt.nodes.new('ShaderNodeTexSky')
sky.sky_type = 'MULTIPLE_SCATTERING'
sky.sun_elevation = SUN_ELEV
sky.sun_rotation = math.atan2(d.x, d.y)        # matches the lamp; checked against the render
sky.altitude = 50.0
for attr, v in (('air_density', 1.2), ('aerosol_density', 3.0), ('dust_density', 3.0), ('ozone_density', 1.0)):
    if hasattr(sky, attr):
        setattr(sky, attr, v)
bg = nt.nodes['Background']
bg.inputs['Strength'].default_value = 0.28
nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
s.world = w
vs = s.view_settings
vs.view_transform = 'AgX'
vs.exposure = -0.85                       # pre-sunrise: deep water below, light only along the coast and sky
try:
    vs.look = 'AgX - Medium High Contrast'
except TypeError:
    pass
out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if out:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(out))
    print('OUT', out)
