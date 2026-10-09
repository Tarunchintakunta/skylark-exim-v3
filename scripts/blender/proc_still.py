"""Processing-hall stand-in still (#141): p-proc mid-shift, a steel tray of whole prawns and two tuna on crushed ice in
the foreground, the masked, gloved line behind it out of focus. Stand-in for the process chapter until p-proc is rendered.
  Blender -b assets-src/blender/p-proc.blend --python scripts/blender/proc_still.py -- out.png 101 <fish_scans.blend> <blender lib dir> [percent]
"""
import bpy, sys, math, random, os
from mathutils import Vector, Euler
a = sys.argv[sys.argv.index('--') + 1:]
OUT, FRAME, SCANS, LIB = a[0], int(a[1]), a[2], a[3]
sys.path.insert(0, LIB)
import sklib as L
s = bpy.context.scene
s.frame_set(FRAME)
cam = s.camera
mw = cam.matrix_world.copy()
fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
right = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
# drop the camera to just above table height and look slightly down onto the tray
base = mw.translation.copy()
flat = Vector((fwd.x, fwd.y, 0)).normalized()
cam.animation_data_clear()
for c in list(cam.constraints): cam.constraints.remove(c)
cam.parent = None
tray_c = base + flat * 1.6
dg = bpy.context.evaluated_depsgraph_get()
hit, hp, *_ = s.ray_cast(dg, Vector((tray_c.x, tray_c.y, base.z)), Vector((0, 0, -1)))
tray_c.z = (hp.z if hit else 0.0) + 0.92
cam.location = tray_c - flat * 1.05 + Vector((0, 0, 0.42))
look = tray_c + flat * 0.55 + Vector((0, 0, 0.12))
cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
yaw = math.atan2(flat.y, flat.x)
mats = L.M()
steel = L.pbr('MAT_TrayStill', (0.62, 0.64, 0.66), 0.28, var=0.04, bump=0.1)
L.principled(steel).inputs['Metallic'].default_value = 1.0
root = L.empty('STILL_Tray', tuple(tray_c))
root.rotation_euler = (0, 0, yaw - math.pi / 2)
W, D = 1.1, 0.6
L.box('STILL_TrayBase', (W, D, 0.02), (0, 0, -0.01), steel, 0.0, parent=root) if 'parent' in L.box.__code__.co_varnames else None
tb = bpy.data.objects.get('STILL_TrayBase')
if tb and tb.parent is None:
    tb.parent = root; tb.location = (0, 0, -0.01)
for sx, sy, w, d in ((0, D / 2, W, 0.01), (0, -D / 2, W, 0.01), (W / 2, 0, 0.01, D), (-W / 2, 0, 0.01, D)):
    L.box('STILL_TrayRim', (w, d, 0.05), (0, 0, 0), steel, 0.0)
    r = bpy.context.scene.objects[-1] if False else [o for o in bpy.data.objects if o.name.startswith('STILL_TrayRim') and o.parent is None][-1]
    r.parent = root; r.location = (sx, sy, 0.02)
bed = L.ice_chunks('STILL_IceBed', W * 0.97, D * 0.95, 3200, 11, 0.0, 0.018)
L.obj('STILL_Ice', bed, mats['ice'], (0, 0, 0.0), parent=root)
with bpy.data.libraries.load(SCANS, link=False) as (src, dst):
    dst.objects = ['SCAN_Prawn', 'SCAN_Tuna']
prawn, tuna = dst.objects
rnd = random.Random(4)
def place(src, loc, rz, sc, belly_down):
    o = src.copy(); s.collection.objects.link(o); o.parent = root
    o.rotation_mode = 'XYZ'
    o.rotation_euler = ((math.pi if belly_down else 0) + rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.1), rz)
    o.scale = (sc,) * 3
    o.location = loc
    return o
# two whole tuna along the back of the tray, prawns heaped in front
place(tuna, (0.12, 0.17, 0.075), math.radians(4), 0.55, False)
for i in range(60):
    x = rnd.uniform(-W * 0.44, W * 0.44); y = rnd.uniform(-D * 0.44, -D * 0.02)
    z = 0.05 + 0.03 * max(0.0, 1 - abs(x) / (W * 0.5)) + rnd.uniform(0, 0.03)
    place(prawn, (x, y, z), rnd.uniform(-math.pi, math.pi), rnd.uniform(0.14, 0.16), False)
cam.data.lens = 45
cam.data.dof.use_dof = True
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = (tray_c - flat * 0.12 - cam.location).length
cam.data.dof.aperture_fstop = 2.8
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, int(a[4]) if len(a) > 4 else 100
s.eevee.taa_render_samples = 64
s.render.image_settings.file_format = 'PNG'
s.render.filepath = OUT
bpy.ops.render.render(write_still=True)
