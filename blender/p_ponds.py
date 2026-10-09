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
    F.groves(C, rnd)
    F.grass_tufts(C, random.Random(5), -330, -20, -150, 150)
    F.footpaths(C, random.Random(6), -360, 0)
    F.birds(C, rnd, 9, F0, F1 + 24, centre=(-90, 10, 28))
    F.birds(C, random.Random(7), 7, F0, F1 + 24, centre=(-200, -40, 14))

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
             (-150, 86, 'stand', None), (60, -56.5, 'walk', (0, -1)), (-20, 70, 'stand', None),
             (-225.5, 24, 'walk', (0, 1)), (-162.5, -22, 'stand', None), (-190, -6.6, 'walk', (1, 0)),
             (-162.5, 31, 'stand', None), (-130, 56, 'walk', (-1, 0)), (-225.5, -40, 'stand', None)]
    for k, (x, y, kind, d) in enumerate(spots):
        i, j, cx, cy = F.cell_of(x, y)
        w = H.person('HUM_Farm%d' % k, 'farm_long' if k % 2 else 'farm', 'male' if k % 3 else 'female', coll=Cp, seed=50 + k)
        z = F.height(x, y)
        w.location = (x, y, z)
        if kind == 'walk':
            w.location.z = 0.0              # walk_cycle keys z from the rest height; the bund height is added below
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

    # a feed-sack cart pushed along the road edge, a worker casting feed from the bund, one carrying a bucket
    cart_man = H.person('HUM_CartPusher', 'farm', 'male', coll=Cp, seed=70)
    cart = F.feed_cart('FARM_FeedCart', Cp)
    cart.parent = cart_man
    cart.location = (0, -0.35, 0)
    cart_man.location = (-152.0, -6.4, F.TOP)
    H.walk_cycle(cart_man, F0 - 6, F1 + 6, [(F0 - 6, (-152.0, -6.4)), (F1 + 6, (-139.0, -6.4))], stride=0.55,
                 base=H.POSES['push'], arms=False, step=2)
    caster = H.person('HUM_FeedCaster', 'farm_long', 'male', coll=Cp, seed=71)
    caster.location = (-162.5, -17.0, F.height(-162.5, -17.0))
    caster.rotation_euler = (0, 0, D(-90))                  # faces the pond to the east
    for k, f in enumerate(range(F0 - 6, F1 + 8, 10)):       # scoop from the bucket, swing out, release
        if k % 2:
            H.set_pose(caster, {'spine': (14, 0, -8), 'upperarm.R': (95, -18, 0), 'forearm.R': (10, 0, 0),
                                'upperarm.L': (25, -15, 0), 'forearm.L': (70, 0, 0), 'thigh.L': (12, 3, 0)}, f)
        else:
            H.set_pose(caster, {'spine': (24, 0, 10), 'upperarm.R': (20, -10, 0), 'forearm.R': (40, 0, 0),
                                'upperarm.L': (25, -15, 0), 'forearm.L': (70, 0, 0)}, f)
    bucket = F.Part()
    bucket.cyl((0, 0, 0), (0, 0, 0.3), 0.14, 14, r2=0.17)
    bk = bucket.make('FARM_CasterBucket', P.plain('FARM_BucketBlue', (0.06, 0.16, 0.34), 0.45), None, coll=Cp)
    bk.location = (-162.2, -17.45, F.height(-162.2, -17.45))
    walker = H.person('HUM_BucketCarrier', 'farm', 'female', coll=Cp, seed=72)
    walker.location = (0, 0, F.TOP)
    H.walk_cycle(walker, F0 - 6, F1 + 6, [(F0 - 6, (-162.5, -46.0)), (F1 + 6, (-162.5, -30.0))], stride=0.6,
                 base={'upperarm.R': (5, -8, 0), 'forearm.R': (10, 0, 0)}, step=2)

    # drone camera: glide forward + slight yaw, ending along the road the truck uses
    cam = L.camera('Camera', 28, (0, 0, 80))
    cam.data.dof.use_dof = False
    tgt = bpy.data.objects.new('CAM_Target', None)
    s.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    # lower, faster drone pass (~18 m/s), looking toward the morning sun for glints on the ponds
    keys = [(F0, (-305, -122, 34), (-150, 34, 0)),
            (96, (-238, -72, 26), (-90, 20, 0)),
            (F1, (-170, -22, 19), (-30, 5, 0))]
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
    hdr = 'kloofendal_48d_partly_cloudy_puresky_4k.hdr'   # bright day, soft cumulus
    az_h, el_h = P.hdri_sun(hdr)
    sun_az = 112.0                      # warm late-morning sun from the east-south-east, raking across the bunds
    P.hdri_world(hdr, strength=1.0, rot_deg=sun_az - az_h, sun_elev=el_h, sun_az=sun_az,
                 sun_energy=5.2, sun_color=(1.0, 0.88, 0.72), bg_strength=1.2)
    P.look_settings('exterior', exposure=0.15, haze=(420.0, 1800.0, (0.62, 0.76, 0.96), 0.07))
    s.frame_start, s.frame_end = F0, F1
    s.frame_current = F0
    s.render.filepath = '//../render/p-ponds/'
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('OUT built p-ponds', out)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build(argv[0] if argv else os.path.join(REPO, 'assets-src/blender/p-ponds.blend'))
