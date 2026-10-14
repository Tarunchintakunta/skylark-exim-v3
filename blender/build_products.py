"""Products look-dev: photoreal tuna, swordfish and Vannamei shrimp on a crushed-ice bed under soft studio light
(SCENES.md §12). Builds assets-src/blender/products.blend and renders the approval stills
docs/renders/{tuna,swordfish,shrimp}-{side,34,head}.png at 1600 px.
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_products.py [-- fish ...]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import sklib as L  # noqa: E402
import sklib_fish as F  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'products.blend')
REN = os.path.join(REPO, 'docs', 'renders')
D = math.radians
want = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['tuna', 'swordfish', 'shrimp']

s = L.reset()
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
s.render.engine = 'CYCLES' if 'CYCLES' in engines else 'BLENDER_EEVEE'
if s.render.engine == 'CYCLES':
    s.cycles.samples = 160
    s.cycles.use_denoising = True
    try:
        s.cycles.device = 'GPU'
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception as exc:
        print('cycles device', exc)
else:
    s.eevee.taa_render_samples = 64
    s.eevee.use_raytracing = True
s.render.resolution_x, s.render.resolution_y = 1600, 900
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Medium High Contrast'
# studio: light #eef5f6 background, large softbox key, rim, fill
w = bpy.data.worlds.new('WORLD_Studio')
s.world = w
bg = [n for n in w.node_tree.nodes if n.type == 'BACKGROUND'][0]
bg.inputs['Color'].default_value = (0.855, 0.913, 0.921, 1)
bg.inputs['Strength'].default_value = 0.6


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.size = size
    ld.energy = energy
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    s.collection.objects.link(o)
    L.look(o, loc, target)
    return o


area('KEY_Softbox', (0.6, -1.6, 2.4), (0, 0, 0.1), 2.2, 900)
area('RIM', (-1.8, 1.4, 1.2), (0, 0, 0.15), 1.2, 600, (0.95, 0.98, 1.0))
area('FILL', (1.8, -0.4, 0.6), (0, 0, 0.1), 1.5, 150)
L.box('SWEEP', (12, 12, 0.02), (0, 0, -0.01), L.pbr('MAT_Sweep', (0.855, 0.913, 0.921), 0.6, var=0.02, bump=0.0), 0.0)
F.ice_bed('PROD_IceTray', 1.9, 0.95)
fish = {}
if 'tuna' in want:
    fish['tuna'] = F.tuna('PROD_Tuna', 1.25, (-0.62, -0.02, 0.2), (D(-82), 0, D(-3)))
if 'swordfish' in want:
    fish['swordfish'] = F.swordfish('PROD_Swordfish', 1.15, (-0.7, 0.0, 0.2), (D(-80), 0, D(2)))
if 'shrimp' in want:
    for i in range(7):
        fish[f'shrimp{i}'] = F.shrimp(f'PROD_Shrimp{i}', 0.17, (-0.45 + (i % 4) * 0.28, -0.18 + (i // 4) * 0.3, 0.12),
                                      (D(-80 + i * 4), D(5 * (i % 3)), D(-20 + i * 25)), seed=i)
cam = L.camera('Camera', 85, (0, -3, 1.2), (0, 0, 0.2))
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 5.6
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
shots = {
    'tuna': {'side': ((0.0, -3.4, 0.55), (0.0, 0.0, 0.2), 70), '34': ((1.9, -2.3, 1.3), (0.05, 0.0, 0.18), 70),
             'head': ((1.05, -0.95, 0.45), (0.45, 0.0, 0.2), 85)},
    'swordfish': {'side': ((0.2, -3.6, 0.6), (0.2, 0.0, 0.2), 65), '34': ((2.2, -2.3, 1.3), (0.3, 0.0, 0.18), 65),
                  'head': ((1.15, -0.95, 0.42), (0.55, 0.0, 0.22), 85)},
    'shrimp': {'side': ((0.0, -1.6, 0.35), (0.0, 0.0, 0.14), 85), '34': ((0.9, -1.0, 0.75), (0.0, 0.0, 0.12), 85),
               'head': ((0.25, -0.42, 0.28), (0.05, -0.15, 0.14), 100)},
}
for f, views in shots.items():
    if f not in want:
        continue
    # show only this species on the tray
    for o in bpy.data.objects:
        if o.name.startswith('PROD_') and not o.name.startswith('PROD_IceTray'):
            top = o
            while top.parent:
                top = top.parent
            o.hide_render = not top.name.lower().startswith('prod_' + f[:5])
    for v, (loc, tgt, lens) in views.items():
        L.look(cam, loc, tgt)
        cam.data.lens = lens
        cam.data.dof.focus_distance = (Vector(loc) - Vector(tgt)).length
        s.render.filepath = os.path.join(REN, f'{f}-{v}.png')
        bpy.ops.render.render(write_still=True)
        print('STILL', f, v)
print('BUILT', OUT, s.render.engine)
