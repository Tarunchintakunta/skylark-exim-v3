"""p-ponds (frames 1-192): bright golden-morning drone glide over the shrimp pond grid. Aerators churning, the white
reefer truck and a motorbike drive the bund road in one direction (+X), workers on the bunds, egrets.
Ends looking along the bund road the truck uses.
Usage: Blender -b --python blender/p_ponds.py -- [out.blend]"""
import math
import os
import random
import sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skpbr as P      # noqa: E402
import skfarm as F     # noqa: E402
import sktruck as T    # noqa: E402
import skhuman as H    # noqa: E402
import sklib as L      # noqa: E402

REPO = os.path.dirname(HERE)
F0, F1 = 1, 192
D = math.radians


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    rnd = random.Random(42)
    C = F.coll('SET_Farm')
    F.build_terrain(C)
    F.build_water(C)
    F.place_aerators(C, rnd)
    F.animate_water(F0 - 24, F1 + 48)
    F.ruts(C)
    xm, ym = F.compound(C, rnd)
    F.poles(C, rnd)
    F.feed_trays(C, rnd)
    F.palms(C, rnd, xm, ym)
    F.birds(C, rnd, 8, F0, F1 + 24, centre=(-90, 10, 28))

    # truck + motorbike on the bund road, +X, left lane (y +1.8); 8 m/s
    Cv = F.coll('SET_Vehicles')
    R = T.reefer_truck('TRK_RigidReefer', coll=Cv, load=False)
    R['root'].location.z = F.TOP + 0.05

    def tpath(f):
        return -150 + (f - F0) / 24 * 8.0, 1.8, 0.0, 0.0
    T.drive(R, tpath, F0 - 6, F1 + 6, step=1)
    for fc in T._fcurves(R['root'].animation_data.action):
        if fc.data_path == 'location' and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.co.y = F.TOP + 0.05
    mb = F.motorbike('MB_Bike', Cv)
    H.load(os.path.join(REPO, 'assets-src/blender/humans.blend'))
    rider = H.person('HUM_Rider', 'farm', 'male', coll=Cv, seed=3)
    rider.parent = mb
    rider.location = (-0.1, 0, 0.35)
    rider.rotation_euler = (0, 0, D(90))
    H.set_pose(rider, {'thigh': (80, 10, 0), 'shin': (-85, 0, 0), 'upperarm': (55, -5, 0), 'forearm': (30, 0, 0),
                       'spine': (12, 0, 0)})
    for f in (F0 - 6, F1 + 6):
        mb.location = (-150 - 16 + (f - F0) / 24 * 8.0, 1.6, F.TOP + 0.05)
        mb.keyframe_insert('location', frame=f)
    for fc in T._fcurves(mb.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

    # workers on the bunds (small): two walking with buckets, others standing at ponds / casting feed
    Cp = F.coll('SET_People')
    spots = [(-95, 33.6, 'walk', (1, 0)), (-40, -30.6, 'stand', None), (10, 33.6, 'walk', (-1, 0)),
             (-150, 86, 'stand', None), (60, -56.5, 'walk', (0, -1)), (-20, 70, 'stand', None)]
    for k, (x, y, kind, d) in enumerate(spots):
        i, j, cx, cy = F.cell_of(x, y)
        w = H.person('HUM_Farm%d' % k, 'farm_long' if k % 2 else 'farm', 'male' if k % 3 else 'female', coll=Cp, seed=50 + k)
        z = F.height(x, y)
        w.location = (x, y, z)
        if kind == 'walk':
            path = [(F0 - 6, (x, y)), (F1 + 6, (x + d[0] * 1.2 * (F1 - F0 + 12) / 24, y + d[1] * 1.2 * (F1 - F0 + 12) / 24))]
            H.walk_cycle(w, F0 - 6, F1 + 6, path, stride=0.7,
                         base={'upperarm.R': (5, -8, 0), 'forearm.R': (10, 0, 0)}, step=2)
            for fc in T._fcurves(w.animation_data.action):
                if fc.data_path == 'location' and fc.array_index == 2:
                    for kp in fc.keyframe_points:
                        kp.co.y += z
                        kp.handle_left.y += z
                        kp.handle_right.y += z
        else:
            w.rotation_euler = (0, 0, rnd.uniform(0, 6.28))
            H.jitter(w, H.POSES['look'], F0 - 6, F1 + 6, every=20, amp=6, seed=k)

    # drone camera: glide forward + slight yaw, ending along the road the truck uses
    cam = L.camera('Camera', 30, (0, 0, 80))
    cam.data.dof.use_dof = False
    tgt = bpy.data.objects.new('CAM_Target', None)
    s.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    keys = [(F0, (-262, -150, 86), (-95, 30, 0)),
            (96, (-238, -100, 76), (-40, 18, 0)),
            (F1, (-215, -46, 66), (40, 2, 0))]
    for f, loc, t in keys:
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
    for o in (cam, tgt):
        for fc in T._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
            fc.update()

    # golden morning: HDRI sun at elev ~20, lamp aimed to match
    az_h, el_h = P.hdri_sun('qwantani_mid_morning_puresky_4k.hdr')
    sun_az = 120.0                      # light from the east-south-east: long shadows across the bunds
    P.hdri_world('qwantani_mid_morning_puresky_4k.hdr', strength=0.9, rot_deg=sun_az - az_h, sun_elev=el_h, sun_az=sun_az,
                 sun_energy=5.0, sun_color=(1.0, 0.88, 0.72))
    P.look_settings('exterior', exposure=0.0, haze=(260.0, 1200.0, (0.62, 0.74, 0.9), 0.22))
    s.frame_start, s.frame_end = F0, F1
    s.frame_current = F0
    s.render.filepath = '//../render/p-ponds/'
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('OUT built p-ponds', out)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build(argv[0] if argv else os.path.join(REPO, 'assets-src/blender/p-ponds.blend'))
