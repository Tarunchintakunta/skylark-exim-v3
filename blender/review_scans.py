"""Look-dev stills of the prepared scans (fish_scans.blend): each scan at real size on crushed ice, studio light.
  Blender -b --factory-startup --python blender/review_scans.py -- <out_prefix> [Tuna|Prawn ...]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import sklib as L  # noqa: E402

REPO = os.path.dirname(HERE)
SC = os.path.join(REPO, 'assets-src', 'blender', 'fish_scans.blend')
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['/tmp/scan']
out = args[0]
want = args[1:] or ['Tuna', 'Prawn']
SIZE = {'Tuna': 1.2, 'Prawn': 0.2}
s = L.reset()
mats = L.M()
w = bpy.data.worlds.new('W')
s.world = w
bg = [n for n in w.node_tree.nodes if n.type == 'BACKGROUND'][0]
bg.inputs['Color'].default_value = (0.86, 0.91, 0.92, 1)
bg.inputs['Strength'].default_value = 0.5


def area(name, loc, size, energy):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.size = size
    ld.energy = energy
    o = bpy.data.objects.new(name, ld)
    s.collection.objects.link(o)
    L.look(o, loc, (0, 0, 0))


L.box('SWEEP', (20, 20, 0.02), (0, 0, -0.01), L.pbr('MAT_Sweep', (0.86, 0.91, 0.92), 0.6, var=0.02, bump=0.0), 0.0)
with bpy.data.libraries.load(SC, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.replace('SCAN_', '').replace('_LOD', '') in want]
s.render.engine = 'BLENDER_EEVEE'
s.eevee.taa_render_samples = 64
s.eevee.use_raytracing = True
s.render.resolution_x, s.render.resolution_y = 1600, 900
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
cam = L.camera('Camera', 50, (0, -2, 1), (0, 0, 0))
s.camera = cam
for o in dst.objects:
    if o is None:
        continue
    s.collection.objects.link(o)
    o.hide_render = True
for o in [o for o in dst.objects if o is not None]:
    nm = o.name.replace('SCAN_', '')
    base = nm.replace('_LOD', '')
    sz = SIZE[base]
    for x in bpy.data.objects:
        if x.name.startswith('SCAN_'):
            x.hide_render = x is not o
    o.scale = (sz, sz, sz)
    o.location = (0, 0, 0)
    bpy.context.view_layer.update()
    zmin = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    o.location.z = -zmin
    for l in [x for x in bpy.data.objects if x.type == 'LIGHT']:
        bpy.data.objects.remove(l)
    area('KEY', (sz * 0.5, -sz * 1.2, sz * 2.2), sz * 2.0, 120 * sz * sz * 4)
    area('RIM', (-sz * 1.6, sz * 1.3, sz * 1.1), sz * 1.2, 90 * sz * sz * 4)
    for v, loc, lens in (('side', (0, -sz * 2.6, sz * 0.35), 50), ('34', (sz * 1.3, -sz * 1.6, sz * 0.9), 50),
                         ('top', (0.0, -sz * 0.2, sz * 2.6), 50), ('head', (sz * 0.75, -sz * 0.55, sz * 0.3), 70)):
        tgt = (sz * 0.25 if v == 'head' else 0, 0, sz * 0.05)
        L.look(cam, loc, tgt)
        cam.data.lens = lens
        s.render.filepath = f'{out}-{nm}-{v}.png'
        bpy.ops.render.render(write_still=True)
        print('STILL', nm, v)
