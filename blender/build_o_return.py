"""Build assets-src/blender/o-return.blend (docs/blender/SCENES.md §3): the boat comes home to a busy fishing harbour,
iced crates go hand to hand onto trolleys and into the white reefer truck, which pulls away forward. Frames 1-288.
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_o_return.py
World: wharf edge on y = 0 (land y < 0, harbour water y > 0), wharf top z = 1.8, water z = 0. No names, no signs.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
import sklib as L  # noqa: E402
import sklib_sea as S  # noqa: E402
import sklib_port as P  # noqa: E402
import sklib_plant as PL  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'o-return.blend')
D = math.radians
rnd = random.Random(21)
WZ = 1.8

s = L.reset()
s.frame_start, s.frame_end = 1, 288
mats = L.M()
L.hdri('qwantani_mid_morning_puresky_4k', strength=0.7, rot=0.0, sun_strength=3.0)

# ---------------------------------------------------------------- water, wharf, breakwater, hills
sea = L.ocean('Harbour', size=60, repeat=6, res=10, choppy=0.5, wind=4.0, scale=0.25, f0=1, f1=288, foam=0.05,
              mat=mats['water_harbour'], loc=(20, 120, 0))
L.box('SeaFull', (20000, 20000, 0.1), (0, 0, -0.3), mats['water_harbour'], 0.0)
L.box('WHARF_Deck', (260, 120, WZ + 2), (0, -60, WZ / 2 - 1), mats['concrete'], 0.0)
L.box('WHARF_Edge', (260, 0.4, 0.3), (0, -0.2, WZ + 0.15), L.pbr('MAT_WharfEdge', (0.5, 0.48, 0.42), 0.8, grime=0.5), 0.02)
bol = P.bollard_mesh()
tyre = L.torus_mesh('WHARF_Tyre', 0.4, 0.15, 20, 8)
tyre.materials.append(mats['rubber'])
for x in range(-120, 121, 8):
    L.obj('WHARF_Bollard', bol, None, (x, -0.6, WZ), scale=(0.7, 0.7, 0.7))
    L.obj('WHARF_Tyre', tyre, None, (x + 4, 0.18, 1.0), (D(90), 0, 0))
# breakwater of boulders
bm = bmesh.new()
for i in range(260):
    t = i / 260
    c = Vector((40 + t * 160, 70 - t * 10, -0.5)) + Vector((rnd.uniform(-3, 3), rnd.uniform(-4, 4), rnd.uniform(0, 2.5)))
    r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(1.2, 2.4))
    for v in r['verts']:
        v.co = Vector((v.co.x * rnd.uniform(0.8, 1.3), v.co.y * rnd.uniform(0.8, 1.3), v.co.z * 0.7)) + c
me = L.bm_to_mesh(bm, 'BREAKWATER')
me.materials.append(L.pbr('MAT_Rock', (0.42, 0.4, 0.37), 0.85, var=0.3, bump=0.6, scale=1.5, grime=0.4))
L.obj('BREAKWATER', me)
L.box('BREAKWATER_Light', (1.2, 1.2, 5.0), (200, 60, 2.5), mats['paint_white'], 0.05)
# distant hills (green, lighter with distance) and a far coast line
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=80, y_segments=20, size=1.0)
for v in bm.verts:
    x, y = v.co.x * 2500, 900 + (v.co.y + 1) * 400
    h = 120 * (0.5 + 0.5 * math.sin(x / 300.0 + 1.3)) * (0.6 + 0.4 * math.sin(x / 97.0)) * max(0.0, (y - 900) / 800) + 10
    v.co = Vector((x, y, h))
me = L.bm_to_mesh(bm, 'HILLS', smooth=True)
me.materials.append(L.pbr('MAT_HillHaze', (0.36, 0.44, 0.42), 0.9, var=0.2, bump=0.0, scale=0.01))
L.obj('HILLS', me)

# ---------------------------------------------------------------- moored boats rafted side by side (no names)
hull_cols = [((0.08, 0.2, 0.5), (0.8, 0.8, 0.78)), ((0.45, 0.08, 0.06), (0.8, 0.8, 0.78)), ((0.1, 0.35, 0.18), (0.8, 0.8, 0.78)),
             ((0.8, 0.8, 0.78), (0.08, 0.2, 0.5)), ((0.06, 0.32, 0.45), (0.85, 0.6, 0.1))]
k = 0
for x0, n_along in ((40, 4), (-92, 3)):
    for a in range(n_along):
        for row in range(2 if x0 > 0 else 3):
            hc = hull_cols[(k * 7) % len(hull_cols)]
            hm = S.hull_material(f'MAT_HullV{k}', white=hc[0], band=hc[1], bottom=(0.3, 0.06, 0.05), band_z=(2.25, 2.5))
            x = x0 + a * 26 + rnd.uniform(-2, 2)
            y = 3.8 + row * 6.9
            R = S.vessel(f'MOORED{k}', (x, y, 0), D(rnd.choice((0, 180)) + rnd.uniform(-2, 2)), mats=mats, hull=hm, detail=False)
            for f in range(1, 289, 24):
                R['root'].rotation_euler.x = D(0.8 * math.sin(f / 19.0 + k))
                R['root'].keyframe_insert('rotation_euler', frame=f)
            k += 1
# mooring lines from the inner row to bollards
for i in range(4):
    x = 40 + i * 26
    L.tube(f'MOOR{i}', [(x - 9, 0.9, 2.6), (x - 10, -0.2, 2.1), (x - 11, -0.6, WZ + 0.6)], 0.035, mats['rope'], 6)

# ---------------------------------------------------------------- our vessel comes home (same library vessel as o-catch)
V = S.vessel('BOAT', (120, 30, 0), D(180), mats=mats)
boat = V['root']
for f, p, rz in ((1, (120, 30, 0), 182), (50, (60, 26, 0), 186), (90, (20, 10, 0), 200), (125, (5, 4.0, 0), 182), (140, (2, 3.7, 0), 180),
                 (288, (2, 3.7, 0), 180)):
    boat.location = p
    boat.rotation_euler = (0, 0, D(rz))
    boat.keyframe_insert('location', frame=f)
    boat.keyframe_insert('rotation_euler', frame=f)
L.smooth_keys(boat)
for f in range(1, 289, 12):
    boat.rotation_euler.x = D(1.0 * math.sin(f / 23.0))
    boat.keyframe_insert('rotation_euler', index=0, frame=f)
# hold full of iced crates (boat local)
hx0, hx1, hy = V['hatch']
hc = (hx0 + hx1) / 2
k = 0
for ix in range(5):
    for iy in range(6):
        L.crate(f'HOLD_Crate{k}', rnd.choice(['blue', 'blue', 'white', 'red']), (hc - 1.6 + ix * 0.68, -1.3 + iy * 0.48,
                                                                                  V['hold_floor'] + 1.2), 0.0,
                fill=rnd.choice(['mixed', 'fish', 'tuna']), parent=boat, mats=mats, seed=k)
        k += 1
# bow wave + wake while under way
foam = L.pbr('MAT_Wake', (0.8, 0.86, 0.9), 0.55, var=0.5, bump=0.6, scale=0.3, alpha=0.5)
wk = P.MB()
for i in range(8):
    wk.box((-12 - i * 4, 0, 0.1), (4.2, 3.0 + i * 0.9, 0.04), foam)
wake = wk.obj('BOAT_Wake', boat)
for f, sc in ((1, 1.0), (100, 0.6), (130, 0.01)):
    wake.scale = (1, sc, 1)
    wake.keyframe_insert('scale', frame=f)

# ---------------------------------------------------------------- crew, hand chain, trolleys, truck
DZ = V['deck_z']
crew = []
for i, (x, y, rz, o) in enumerate(((hc, 1.0, 90, 'fisherman_o'), (hc + 0.8, -1.2, 60, 'fisherman_y'), (-2.0, 1.8, 100, 'fisherman_b'),
                                   (2.5, -2.2, 200, 'fisherman_o'))):
    r = L.person(f'CREW{i}', o, (x, y, DZ), D(rz), seed=i, mats=mats)
    r.parent = boat
    crew.append(r)
L.anim_poses(crew[2], [(1, 'idle'), (110, 'pull'), (125, 'pull2'), (140, 'idle')])
L.anim_poses(crew[3], [(1, 'idle'), (100, 'point'), (130, 'idle')])
# wharf workers
wk_spots = [(4, -1.4, 90, 'farm'), (1.5, -1.6, 70, 'farm2'), (-1.5, -2.0, 30, 'farm3'), (-4.0, -3.5, 120, 'farm'),
            (14, -4, 200, 'farm2'), (22, -9, 250, 'farm3'), (-22, -3, 10, 'farm'), (-30, -7, 300, 'farm2'),
            (30, -2.5, 160, 'farm3'), (9, -12, 90, 'driver'), (-18, -14, 45, 'farm'), (38, -6, 180, 'farm2')]
workers = []
for i, (x, y, rz, o) in enumerate(wk_spots):
    w = L.person(f'WORKER{i}', o, (x, y, WZ), D(rz), seed=40 + i, mats=mats)
    workers.append(w)
    L.anim_poses(w, [(1, 'idle'), (60 + i * 9, 'point' if i % 5 == 0 else 'idle'), (288, 'idle')])
# hand chain 140-200: deck crew -> wharf workers
for r in (crew[0], crew[1]):
    L.anim_poses(r, [(1, 'idle'), (135, 'idle')] + [(f, 'lift' if (f // 8) % 2 == 0 else 'pass') for f in range(140, 210, 8)] + [(220, 'idle')])
for w in workers[:3]:
    L.anim_poses(w, [(1, 'idle'), (138, 'idle')] + [(f, 'reach' if (f // 8) % 2 == 0 else 'carry') for f in range(142, 212, 8)] + [(222, 'idle')])
# trolleys on the wharf, crates stacked on them, pushed to the truck
TRK = Vector((-12.0, -7.0, WZ))
truck = PL.reefer_truck('TRK_RigidReefer', (TRK.x, TRK.y, WZ), D(-90), mats=mats)
troot = truck['root']
for c in truck['cargo']:
    L.key_vis(c, 200)
    for ch in c.children:
        L.key_vis(ch, 200)
for side, sgn in (('l', 1), ('r', -1)):
    h = truck['door_' + side]
    for f, a in ((1, 0), (140, 0), (152, 100), (215, 100), (226, 0)):
        h.rotation_euler = (0, 0, D(-a * sgn))
        h.keyframe_insert('rotation_euler', frame=f)
# cold mist puff when the doors open
mist = L.pbr('MAT_Mist', (0.92, 0.95, 0.97), 0.6, var=0.2, bump=0.0, alpha=0.18)
for i in range(4):
    mo = L.sphere(f'MIST{i}', 0.6, (0, 0, 0), mist, (1.4, 1.0, 0.8), 12, 8, parent=troot)
    for f, p, sc in ((150, (-2.4, 0.3 * i - 0.4, 2.4), 0.3), (165, (-3.2 - i * 0.2, 0.3 * i - 0.4, 2.7), 1.0), (185, (-3.8, 0.3 * i, 3.2), 0.01)):
        mo.location = p
        mo.scale = (sc * 1.4, sc, sc * 0.8)
        mo.keyframe_insert('location', frame=f)
        mo.keyframe_insert('scale', frame=f)
    L.key_vis(mo, 150, 186)
trolleys = []
for i in range(3):
    t = PL.trolley(f'TROLLEY{i}', (2.5 - i * 1.6, -2.4, WZ), D(180), mats)
    for lv in range(3):
        for j in range(2):
            c = L.crate(f'TROLLEY{i}_C{lv}{j}', rnd.choice(['blue', 'white', 'blue']), (0.0, -0.21 + j * 0.42, 0.34 + lv * 0.29), D(90),
                        fill='mixed' if lv == 2 else None, parent=t, mats=mats, seed=100 + i * 10 + lv * 2 + j)
            L.key_vis(c, 150 + i * 8 + lv * 6)
    trolleys.append(t)
    rear = Vector((TRK.x, TRK.y + 2.8, WZ))
    path = [(2.5 - i * 1.6, -2.4), (-3 - i, -3.0 - i * 0.6), (rear.x + 1.2 - i * 0.8, rear.y + 1.4 + i * 1.3)]
    P.drive(t, path, 175 + i * 6, 212 + i * 6, ease=True, keystep=3)
    pusher = L.person(f'PUSHER{i}', 'farm2' if i % 2 else 'farm', (path[0][0] + 1.0, path[0][1], WZ), D(180), seed=70 + i, mats=mats)
    L.walk(pusher, [(path[0][0] + 1.1, path[0][1]), (path[1][0] + 1.1, path[1][1] + 0.3), (path[2][0] + 0.9, path[2][1] + 0.9)],
           175 + i * 6, 212 + i * 6, upper='push')
# truck pulls away forward along the harbour road (facing -Y), one direction
road = [(TRK.x, TRK.y), (TRK.x, TRK.y - 12), (TRK.x - 1.5, TRK.y - 40), (TRK.x - 1.5, TRK.y - 70)]
for f in (1, 230):
    troot.location = (TRK.x, TRK.y, WZ)
    troot.keyframe_insert('location', frame=f)
P.drive(troot, road, 230, 288, truck['wheels'], r=0.5, ease=False, keystep=2)
# accelerate: retime by easing in (re-key with ease-in only)
drv = L.person('DRIVER', 'driver', (0, 0, 0), 0.0, seed=91, mats=mats)
drv.parent = troot
drv.location = (7.0, -0.55, 0.6)
L.pose(drv, 'sit')
# road, harbour buildings, ice shed, palms, parked trucks, crate stacks, lamp posts, gulls
L.box('ROAD', (9, 160, 0.04), (TRK.x - 1.5, -80, WZ + 0.01), mats['asphalt'], 0.0)
blds = P.MB()
for i in range(10):
    for side in (-1, 1):
        x = TRK.x + side * rnd.uniform(14, 22)
        y = -20 - i * 14
        w, d, h = rnd.uniform(8, 12), rnd.uniform(8, 11), rnd.uniform(4, 8)
        col = rnd.choice([(0.82, 0.8, 0.74), (0.75, 0.78, 0.8), (0.85, 0.82, 0.7), (0.7, 0.72, 0.68)])
        blds.box((x, y, WZ + h / 2), (w, d, h), L.pbr('MAT_Building', (0.78, 0.77, 0.72), 0.8, grime=0.5, scale=0.5, attr='col'), col)
        for k2 in range(3):
            blds.box((x - side * w / 2 - side * 0.02, y - d / 3 + k2 * d / 3, WZ + h * 0.55), (0.05, 1.2, 1.1), mats['glass'])
blds.obj('HARBOUR_Buildings')
shed = P.MB()
shed.box((24, -14, WZ + 3.5), (16, 10, 0.3), L.pbr('MAT_ShedRoof', (0.55, 0.57, 0.58), 0.5, 0.6, grime=0.4, scale=0.3))
for x in (17, 31):
    for y in (-18.5, -9.5):
        shed.box((x, y, WZ + 1.75), (0.3, 0.3, 3.5), mats['steel'])
shed.box((24, -18.8, WZ + 1.75), (16, 0.2, 3.5), L.pbr('MAT_ShedWall', (0.8, 0.8, 0.78), 0.6, grime=0.5))
shed.box((20, -15, WZ + 0.9), (3, 2, 1.8), mats['steel'])
shed.obj('ICE_Shed')
for i in range(8):
    PL.tree(f'PALM{i}', (rnd.uniform(-60, 60), rnd.uniform(-40, -25) - (i % 3) * 20, WZ), rnd.uniform(7, 10), mats, seed=i, palm=True)
for i, (x, y, rz) in enumerate(((-26, -8, -90), (-36, -10, -88), (40, -14, 90))):
    PL.reefer_truck(f'PARKED{i}', (x, y, WZ), D(rz), mats=mats, cab_color=rnd.choice([(0.7, 0.1, 0.08), (0.15, 0.25, 0.5), (0.85, 0.85, 0.84)]),
                    load=False)
for i in range(30):
    L.crate(f'STACK{i}', rnd.choice(['blue', 'white', 'red', 'blue']), (8 + (i % 5) * 0.65, -3.2 - (i // 15) * 0.5,
                                                                         WZ + ((i // 5) % 3) * 0.29), 0.0, mats=mats)
for i in range(5):
    PL.trolley(f'SPARE_Trolley{i}', (12 + i * 1.5, -6.5, WZ), D(90 + i * 7), mats)
for x in range(-60, 61, 20):
    lp = P.MB()
    lp.cyl((x, -1.5, WZ), (x, -1.5, WZ + 8), 0.1, mats['steel'], 8)
    lp.box((x, -1.0, WZ + 8), (0.3, 1.0, 0.15), mats['steel'])
    lp.obj(f'LAMP{x}')
for i in range(8):
    g = S.gull(f'GULL{i}', (0, 0, 0))
    cx, cy, cz = rnd.uniform(-10, 30), rnd.uniform(0, 20), rnd.uniform(6, 14)
    rad = rnd.uniform(5, 10)
    ph = rnd.uniform(0, 6.28)
    S.flap(g, 1, 288, period=rnd.randint(9, 13), amp=32,
           path=[(cx + rad * math.cos(ph + j * 0.3), cy + rad * 0.6 * math.sin(ph + j * 0.3), cz) for j in range(20)])

# ---------------------------------------------------------------- camera
cam = L.camera('Camera', 30, (60, -20, 25), (90, 25, 2))
cam.data.dof.aperture_fstop = 5.6
keys = [
    (1, (70.0, -24.0, 26.0), (110.0, 28.0, 2.0), 30),
    (72, (24.0, -20.0, 15.0), (36.0, 18.0, 2.0), 30),
    (130, (7.0, -7.5, WZ + 3.0), (0.0, 3.0, 2.4), 28),
    (175, (1.0, -9.0, WZ + 2.6), (-6.0, -3.0, 1.8), 28),
    (192, (-5.0, -0.5, WZ + 6.0), (TRK.x, TRK.y, WZ + 1.4), 28),
    (210, (-15.0, 3.0, WZ + 3.4), (TRK.x, TRK.y - 1.0, WZ + 1.6), 28),
    (230, (-6.5, 3.2, WZ + 3.0), (TRK.x, TRK.y - 2.0, WZ + 1.4), 30),
]
# follow the truck at a fixed offset, sampled from its evaluated path so the camera never catches up with it
for f in list(range(246, 288, 6)) + [288]:
    s.frame_set(f)
    tp = troot.matrix_world.translation
    keys.append((f, (tp.x + 2.0, tp.y + 9.0, WZ + 3.0), (tp.x - 0.5, tp.y - 4.0, WZ + 1.5), 30))
s.frame_set(1)
L.cam_path(cam, keys, focus=[(1, 50.0), (72, 30.0), (130, 9.0), (175, 8.0), (230, 10.0), (288, 9.0)])
s.camera = cam
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
sys.argv = [sys.argv[0], '--', 'o-return', '1', '288', 'exterior']
exec(compile(open(os.path.join(HERE, 'render_settings.py')).read(), 'render_settings.py', 'exec'))
print('BUILT', OUT, len(bpy.data.objects), 'objects')
