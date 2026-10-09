"""People review stills: every outfit in a row (full body) and two head-and-shoulders close-ups.
  Blender -b --factory-startup --python blender/review_people.py -- <out_prefix>
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import sklib as L  # noqa: E402

out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/people'
s = L.reset()
mats = L.M()
L.hdri('kloofendal_48d_partly_cloudy_puresky_4k', strength=0.8, rot=0.0, sun_strength=3.0)
L.box('GROUND', (60, 60, 0.2), (0, 0, -0.1), mats['concrete'], 0.0)
outs = ['fisherman_o', 'fisherman_y', 'fisherman_b', 'dock', 'dock2', 'plant', 'qc', 'port', 'driver', 'farm3']
poses = ['stand', 'stand', 'stand', 'stand', 'stand', 'stand', 'stand', 'stand', 'stand', 'stand']
t0 = time.time()
for i, o in enumerate(outs):
    a = L.person(f'P{i}', o, (0, -4.5 + i * 1.0, 0), rot_z=math.radians(-90 + (i % 3 - 1) * 15), seed=i * 7 + 3)
    L.pose(a, poses[i])
print('PEOPLE', round(time.time() - t0, 1), 's')
s.render.engine = 'BLENDER_EEVEE'
s.eevee.taa_render_samples = 32
s.render.resolution_x, s.render.resolution_y = 1920, 1080
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
cam = L.camera('Camera', 35, (-7.5, 0, 1.3), (0, 0, 1.0))
s.camera = cam
for nm, loc, tgt, lens in (('row', (-8.5, 0, 1.25), (0, 0, 0.95), 32),
                           ('close1', (-1.25, -4.45, 1.62), (0, -4.5, 1.55), 50),
                           ('close2', (-1.25, -1.5, 1.62), (0, -1.5, 1.55), 50),
                           ('mid', (-3.0, 1.0, 1.4), (0, 1.0, 1.0), 40)):
    L.look(cam, loc, tgt)
    cam.data.lens = lens
    s.render.filepath = f'{out}-{nm}.png'
    bpy.ops.render.render(write_still=True)
    print('STILL', nm)
