"""Build assets-src/blender/asset-library.blend (every library asset laid out) and render the review stills
docs/renders/lib-{people,coldchain,vessel,truck,port}.png.
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_library.py
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import sklib as L  # noqa: E402
import sklib_sea as S  # noqa: E402
import sklib_port as P  # noqa: E402
import sklib_plant as PL  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'asset-library.blend')
REN = os.path.join(REPO, 'docs', 'renders')
D = math.radians
rnd = random.Random(1)

s = L.reset()
mats = L.M()
L.sky(sun_elev=48, sun_rot=-50, strength=0.2, clouds=0.5, sun_strength=3.5, haze=0.15)
L.box('LIB_Ground', (2000, 2000, 0.2), (0, 0, -0.1), mats['concrete'], 0.0)

# people: every outfit in a few poses (x = 0 .. 20)
outfits = ['fisherman_o', 'fisherman_y', 'fisherman_b', 'plant', 'plant_blue', 'qc', 'cold', 'farm', 'farm2', 'farm3',
           'driver', 'port', 'port_o']
poses = ['stand', 'pull', 'guide', 'kneel', 'carry', 'shovel', 'table', 'push', 'idle', 'lift', 'pass', 'point', 'reach']
for i, (o, p) in enumerate(zip(outfits, poses)):
    r = L.person(f'LIB_Person{i}', o, (i * 1.1, 0, 0), D(-90), seed=i, mats=mats)
    L.pose(r, p)
# cold chain props (x = 0..6, y = 6)
fills = [None, 'ice', 'fish', 'tuna', 'mixed', 'shrimp']
for i, f in enumerate(fills):
    L.crate(f'LIB_Crate{i}', ['blue', 'red', 'white', 'blue', 'yellow', 'white'][i], (i * 0.8, 6, 0), 0.0, fill=f, mats=mats, seed=i)
for i, k in enumerate(['tuna', 'mackerel', 'seer', 'ribbon']):
    L.fish(f'LIB_Fish{i}', k, (i * 1.6, 7.6, 0.2), (D(90), 0, 0))
PL.trolley('LIB_Trolley', (6.0, 7.4, 0), 0.0, mats)
PL.pallet('LIB_Pallet', (7.8, 6.2, 0), mats, cartons=3, wrap=True, rnd=rnd)
# vessel (y = 40)
S.vessel('LIB_Boat', (0, 40, 0), 0.0, mats=mats)
# reefer truck (y = 20)
PL.reefer_truck('TRK_RigidReefer', (0, 20, 0), 0.0, mats=mats)
# port kit (x = 100)
P.sts_crane('LIB_Crane', (120, 0, 0), mats=mats)
t, w = P.tractor('LIB_Tractor', (100, -30, 0), 0.0, mats=mats)
P.skeletal_trailer('LIB_Trailer', t, mats=mats)
P.reefer_box('LIB_Reefer', bpy.data.objects['LIB_Trailer'], (-5.9, 0, 1.33))
P.straddle('LIB_Straddle', (80, -60, 0), 0.0, mats=mats, rnd=rnd)
P.rtg('LIB_RTG', (150, -70, 0), mats=mats)

cam = L.camera('Camera', 50, (0, 0, 0), (0, 0, 0))
s.render.resolution_x, s.render.resolution_y = 1600, 900
s.render.engine = 'BLENDER_EEVEE'
s.eevee.taa_render_samples = 32
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=OUT)
shots = {
    'people': ((6.6, -7.5, 2.0), (6.6, 0, 1.0), 40),
    'coldchain': ((3.5, 3.4, 2.4), (3.5, 6.8, 0.2), 35),
    'truck': ((10.0, 12.0, 4.0), (2.0, 20.0, 1.6), 30),
    'vessel': ((24.0, 22.0, 12.0), (0.0, 40.0, 2.5), 30),
    'port': ((60.0, -110.0, 30.0), (120.0, -20.0, 30.0), 24),
}
for k, (loc, tgt, lens) in shots.items():
    L.look(cam, loc, tgt)
    cam.data.lens = lens
    s.render.filepath = os.path.join(REN, f'lib-{k}.png')
    bpy.ops.render.render(write_still=True)
print('BUILT', OUT)
