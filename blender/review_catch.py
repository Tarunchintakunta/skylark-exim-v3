"""Catch review stills: iced crates with fish, fish lying on a wet deck, close-up of one fish.
  Blender -b --factory-startup --python blender/review_catch.py -- <out_prefix>
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import sklib as L  # noqa: E402

out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/catch'
s = L.reset()
mats = L.M()
L.hdri('kloofendal_48d_partly_cloudy_puresky_4k', strength=0.8, rot=0.0, sun_strength=3.0)
L.box('DECK', (20, 20, 0.2), (0, 0, -0.1), mats['wetdeck'], 0.0)
rnd = random.Random(3)
for i, (fill, col) in enumerate((('fish', 'blue'), ('ice', 'red'), ('tuna', 'white'), ('fish', 'red'))):
    L.crate(f'C{i}', col, (-0.2 + (i % 2) * 0.66, -0.5 + (i // 2) * 0.46, 0), 0.0, fill=fill, mats=mats, seed=i)
for k in range(40):
    kind = 'mackerel' if k % 5 else 'seer'
    L.fish(f'F{k}', kind, (1.1 + rnd.uniform(-0.45, 0.45), rnd.uniform(-0.6, 0.6), 0.02 + rnd.uniform(0, 0.03)),
           (math.radians(90 * rnd.choice((1, -1)) + rnd.uniform(-12, 12)), rnd.uniform(-0.15, 0.15), rnd.uniform(0, 6.28)))
s.render.engine = 'BLENDER_EEVEE'
s.eevee.taa_render_samples = 48
s.eevee.use_raytracing = True
s.render.resolution_x, s.render.resolution_y = 1600, 900
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
cam = L.camera('Camera', 35, (0, -2, 1.5), (0.3, 0, 0.1))
s.camera = cam
for nm, loc, tgt, lens in (('wide', (-0.6, -2.2, 1.7), (0.5, -0.1, 0.1), 32), ('crates', (0.1, -1.0, 1.1), (0.15, -0.3, 0.15), 40),
                           ('fish', (1.1, -0.8, 0.6), (1.1, 0.0, 0.05), 55)):
    L.look(cam, loc, tgt)
    cam.data.lens = lens
    s.render.filepath = f'{out}-{nm}.png'
    bpy.ops.render.render(write_still=True)
    print('STILL', nm)
