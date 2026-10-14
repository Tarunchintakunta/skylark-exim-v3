"""Export · At sea (#259): the loaded container ship seen straight down on open sea, nothing else in frame.
  Blender -b assets-src/blender/port_v3.3.blend --python blender/sea_topdown.py -- assets-src/blender/x-sea.blend
Keeps only SHIP (hull, stacks, superstructure, bow wave, hull foam, wake), the sea and the sun: every tug, tow line,
other ship, breakwater, quay and the coast are removed. The ship sails far offshore heading up the frame (so the
phone portrait crop holds it too); the camera tracks it from 650 m at a little less than its speed."""
import math
import sys
import bpy

FRAMES = 192                       # 8 s at 24 fps
START = (2400.0, 4200.0)           # far offshore: no land, breakwater or anchorage within kilometres
HEADING = math.radians(84)         # nearly straight up the frame, a slight lean for life
SPEED = 9.0                        # m/s, about 17.5 knots
ALT = 650.0

s = bpy.context.scene
ship = bpy.data.objects['SHIP']
keep = {ship, bpy.data.objects['SeaFull'], bpy.data.objects['Sun']}
keep |= {c for c in ship.children_recursive if not c.name.startswith('TOW_')}
gone = [o for o in bpy.data.objects if o not in keep and o.type not in ('CAMERA',)]
for o in gone:
    bpy.data.objects.remove(o, do_unlink=True)
print('removed', len(gone), 'objects; kept', sorted(o.name for o in keep if o.parent is None))

s.frame_set(479)                                           # the port's last frame: full speed, wake grown out
under_way = {n: (bpy.data.objects[n].location.copy(), bpy.data.objects[n].scale.copy())
             for n in ('SHIP_Wake', 'SHIP_BowWave', 'SHIP_HullFoam')}
for n, (loc, sc) in under_way.items():                    # keyed hidden and small until the departure: under way here
    o = bpy.data.objects[n]
    o.animation_data_clear()
    o.location, o.scale = loc, sc
    o.hide_render = o.hide_viewport = False
ship.animation_data_clear()
d = (math.cos(HEADING), math.sin(HEADING))
for f, t in ((1, 0.0), (FRAMES, (FRAMES - 1) / 24)):
    ship.location = (START[0] + d[0] * SPEED * t, START[1] + d[1] * SPEED * t, 0)
    ship.rotation_euler = (0, 0, HEADING)
    ship.keyframe_insert('location', frame=f)
    ship.keyframe_insert('rotation_euler', frame=f)
for fc in getattr(ship.animation_data.action, 'fcurves', ()):
    for k in fc.keyframe_points:
        k.interpolation = 'LINEAR'

for o in [o for o in bpy.data.objects if o.type == 'CAMERA']:     # the port cameras' actions survive a clear
    bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('SEA_Camera', bpy.data.cameras.new('SEA_Camera'))
s.collection.objects.link(cam)
cam.data.lens = 35
cam.data.clip_end = 5000
for f, t in ((1, 0.0), (FRAMES, (FRAMES - 1) / 24)):
    k = 0.82 * SPEED * t                                      # the ship gains ~14 m on the lens over 8 s
    cam.location = (START[0] + d[0] * (k + 18), START[1] + d[1] * (k + 18), ALT)
    cam.keyframe_insert('location', frame=f)                  # straight down, north up (rotation 0)
for fc in getattr(cam.animation_data.action, 'fcurves', ()):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
s.camera = cam
s.frame_start, s.frame_end = 1, FRAMES
out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if out:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(out))
    print('OUT', out)
