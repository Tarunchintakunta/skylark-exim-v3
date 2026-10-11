"""Build assets-src/blender/o-return.blend (docs/blender/SCENES.md §3): the boat comes home to a busy fishing harbour,
iced crates go hand to hand onto trolleys and into the white reefer truck, which pulls away forward. Frames 1-288.
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_o_return.py
SK_SCENE=o-depart builds o-depart.blend from the same harbour instead (#164): first light, the boat casts off and heads
out past the breakwater head toward the sunrise. Frames 1-240.
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
from mathutils import Vector, Matrix, noise  # noqa: E402
import sklib as L  # noqa: E402
import sklib_sea as S  # noqa: E402
import sklib_port as P  # noqa: E402
import sklib_plant as PL  # noqa: E402

REPO = os.path.dirname(HERE)
DEPART = os.environ.get('SK_SCENE') == 'o-depart'
OUT = os.path.join(REPO, 'assets-src', 'blender', 'o-depart.blend' if DEPART else 'o-return.blend')
F_END = 240 if DEPART else 288
D = math.radians
rnd = random.Random(21)
WZ = 1.8

s = L.reset()
import skhuman_ocean as SO  # noqa: E402
SK = SO.install(L)   # people are skhuman people (real outfits); sklib choreography drives them
s.frame_start, s.frame_end = 1, F_END
mats = L.M()
if DEPART:   # low sun over the sea (+Y = east), warm
    L.hdri('qwantani_morning_puresky_4k', strength=0.45, rot=-64.0, sun_strength=3.4, sun_color=(1.0, 0.72, 0.5))
    _wn = bpy.context.scene.world.node_tree      # dawn: warm the whole sky a little
    _bg = [n for n in _wn.nodes if n.type == 'BACKGROUND'][0]
    _src = _bg.inputs['Color'].links[0].from_socket
    _mx = _wn.nodes.new('ShaderNodeMix')
    _mx.data_type = 'RGBA'
    _mx.blend_type = 'MULTIPLY'
    _mx.inputs['Factor'].default_value = 1.0
    _wn.links.new(_src, _mx.inputs['A'])
    _mx.inputs['B'].default_value = (1.0, 0.82, 0.7, 1)
    _wn.links.new(_mx.outputs['Result'], _bg.inputs['Color'])
else:
    L.hdri('qwantani_mid_morning_puresky_4k', strength=0.7, rot=0.0, sun_strength=3.0)

bpy.context.scene.world.use_sun_shadow = False   # no second shadow from EEVEE's HDRI sun extraction (the Sun lamp keys)
S.haze_world(sat=0.6, amount=0.25)   # humid coastal air, not a postcard sky

SO.progress('section: water, wharf, breakwater, hills')
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
# the wharf slab is not one plain grey: cast panels with joints, patched repairs in other concrete, oil and rust
# stains, puddles, rope coils by the idle bollards, a pallet and drums
wf = P.MB()
wpatch = P.paint_attr('MAT_WharfPatch', 0.9, 0.0, grime=0.7, scale=0.6)
for gx in range(-60, 61, 6):
    wf.box((gx, -15, WZ + 0.002), (0.05, 30, 0.004), mats['rubber'])
for gy in range(-30, 1, 5):
    wf.box((0, gy - 0.5, WZ + 0.002), (120, 0.05, 0.004), mats['rubber'])
for i in range(70):
    pw, pd = rnd.uniform(1.0, 5.5), rnd.uniform(0.8, 4.0)
    tone = rnd.choice([(0.3, 0.29, 0.27), (0.5, 0.49, 0.46), (0.36, 0.33, 0.29), (0.56, 0.55, 0.5), (0.24, 0.2, 0.17)])
    wf.box((rnd.uniform(-60, 60), rnd.uniform(-29, -1.2), WZ + 0.003 + i * 0.00005), (pw, pd, 0.006), wpatch, tone)
puddle = L.pbr('MAT_Puddle', (0.04, 0.045, 0.045), 0.03, var=0.1, bump=0.05, coat=1.0)
for i in range(26):
    c = Vector((rnd.uniform(-50, 50), rnd.uniform(-26, -1.5), WZ + 0.008))
    wf.cyl(c, c + Vector((0, 0, 0.002)), rnd.uniform(0.4, 1.6), puddle if i % 3 else wpatch, 14,
           color=None if i % 3 else (0.12, 0.1, 0.08))       # puddles; every third a dark oil stain
wf.obj('WHARF_Surface')
coil = L.torus_mesh('WHARF_Coil', 0.32, 0.06, 20, 6)
coil.materials.append(mats['rope'])
for x in (-24, -16, 16, 24, 32):
    for j in range(3):
        L.obj('WHARF_Coil', coil, None, (x + 0.9, -1.5, WZ + 0.06 + j * 0.1), (0, 0, D(rnd.uniform(0, 360))),
              scale=(1 - j * 0.15, 1 - j * 0.15, 1))
drum = P.MB()
for i in range(5):
    dx, dy = -31 + (i % 3) * 0.7, -5.5 - (i // 3) * 0.7
    drum.cyl((dx, dy, WZ), (dx, dy, WZ + 0.88), 0.29, L.pbr('MAT_Drum', (0.5, 0.12, 0.06), 0.6, 0.4, grime=0.8, scale=2.0), 14,
             color=None)
drum.box((-28.5, -5.8, WZ + 0.07), (1.2, 1.0, 0.14), L.pbr('MAT_Pallet', (0.36, 0.28, 0.19), 0.85, grime=0.6, scale=2.0))
drum.obj('WHARF_Drums')
# breakwater of boulders
bm = bmesh.new()
for i in range(420):
    t = i / 420
    c = Vector((40 + t * 160, 70 - t * 10, -0.5)) + Vector((rnd.uniform(-3, 3), rnd.uniform(-4, 4), rnd.uniform(0, 2.5)))
    r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(1.2, 2.4))
    for v in r['verts']:
        v.co = Vector((v.co.x * rnd.uniform(0.8, 1.3), v.co.y * rnd.uniform(0.8, 1.3), v.co.z * 0.7)) + c
me = L.bm_to_mesh(bm, 'BREAKWATER')
me.materials.append(L.pbr('MAT_Rock', (0.16, 0.15, 0.14), 0.8, var=0.45, bump=1.0, scale=1.5, grime=0.6))   # dark wet rock
L.obj('BREAKWATER', me)
L.box('BREAKWATER_Light', (1.2, 1.2, 5.0), (200, 60, 2.5), mats['paint_white'], 0.05)
if DEPART:   # beacon on the breakwater head at the harbour mouth the boat passes
    L.cyl('BREAKWATER_Beacon', 0.9, 7.0, (40, 70, 1.5), mats['paint_white'], 16, origin='base')
    L.cyl('BREAKWATER_BeaconBand', 0.95, 1.2, (40, 70, 6.0), mats['paint_red'] if 'paint_red' in mats else mats['lamp_red'], 16,
          origin='base')
# distant hills (green, lighter with distance) and a far coast line
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=80, y_segments=20, size=1.0)
for v in bm.verts:
    x, y = v.co.x * 2500, 900 + (v.co.y + 1) * 400
    h = 120 * (0.5 + 0.5 * math.sin(x / 300.0 + 1.3)) * (0.6 + 0.4 * math.sin(x / 97.0)) * max(0.0, (y - 900) / 800) + 10
    v.co = Vector((x, y, S.hill_height(x, y, h)))
me = L.bm_to_mesh(bm, 'HILLS', smooth=True)
me.materials.append(S.hill_material('MAT_HillHaze', haze=0.15))   # tree cover, scrub, dry grass, bare earth
L.obj('HILLS', me)

SO.progress('section: moored boats rafted side by side (no nam')
# ---------------------------------------------------------------- moored boats rafted side by side (no names)
hull_cols = [((0.08, 0.2, 0.5), (0.8, 0.8, 0.78)), ((0.45, 0.08, 0.06), (0.8, 0.8, 0.78)), ((0.1, 0.35, 0.18), (0.8, 0.8, 0.78)),
             ((0.8, 0.8, 0.78), (0.08, 0.2, 0.5)), ((0.06, 0.32, 0.45), (0.85, 0.6, 0.1))]
ftyre = L.torus_mesh('MOORED_Tyre', 0.32, 0.11, 18, 8)
ftyre.materials.append(mats['rubber'])
k = 0
for x0, n_along in ((40, 4), (-92, 3)):
    for a in range(n_along):
        for row in range(2 if x0 > 0 else 3):
            hc = hull_cols[(k * 7) % len(hull_cols)]
            hm = S.hull_material(f'MAT_HullV{k}', white=hc[0], band=hc[1], bottom=(0.3, 0.06, 0.05), band_z=(2.25, 2.5))
            x = x0 + a * 27.5 + rnd.uniform(-0.8, 0.8)
            y = 3.9 + row * 7.8          # 6.5 m beam + fenders: 1.3 m between rafted hulls (7.3 with 2 deg yaw overlapped at f60)
            R = S.vessel(f'MOORED{k}', (x, y, 0), D(rnd.choice((0, 180)) + rnd.uniform(-0.5, 0.5)), mats=mats, hull=hm, detail=False)
            S.hard_wear(R['hull'].active_material, 1.5, 1.0)     # primer chips, rust runs from the scuppers, salt-dirty water stains
            S.salt_wear(R['hull'].active_material, -0.3, 1.2)
            for sy in (1, -1):                                   # old tyres hung over the side as fenders
                for tx in (-7.0, -2.5, 2.0, 6.5):
                    hb = S.hull_b(tx) * 1.01
                    L.obj(f'MOORED{k}_Fender', ftyre, None, (tx, sy * (hb + 0.12), 1.85 + rnd.uniform(-0.08, 0.08)),
                          (D(90 + rnd.uniform(-6, 6)), 0, 0), parent=R['root'])      # hung just under the rail: reads in the f1-f60 aerials
                    L.tube(f'MOORED{k}_FenderRope', [(tx, sy * (hb + 0.1), 2.26), (tx, sy * (hb + 0.03), 2.52)], 0.012,
                           mats['rope'], 4, parent=R['root'])
            for f in range(1, 289, 24):
                R['root'].rotation_euler.x = D(0.8 * math.sin(f / 19.0 + k))
                R['root'].keyframe_insert('rotation_euler', frame=f)
            k += 1
S.hard_wear(bpy.data.materials['MAT_BoatWhite'], 1.5, 1.2)   # bulwarks and wheelhouses: chips, rust, salt stains
S.salt_wear(bpy.data.materials['MAT_BoatWhite'], 1.4, 2.4)
# mooring lines from the inner row to bollards
for i in range(4):
    x = 40 + i * 26
    L.tube(f'MOOR{i}', [(x - 9, 0.9, 2.6), (x - 10, -0.2, 2.1), (x - 11, -0.6, WZ + 0.6)], 0.035, mats['rope'], 6)

SO.progress('section: our vessel comes home (same library vess')
# ---------------------------------------------------------------- our vessel comes home (same library vessel as o-catch)
V = S.vessel('BOAT', (120, 30, 0), D(180), mats=mats)
boat = V['root']
BOAT_KEYS = ((1, (2, 4.0, 0), 180), (40, (2, 4.0, 0), 180), (80, (-6, 10, 0), 150), (120, (-2, 28, 0), 100),
             (170, (24, 62, 0), 75), (240, (32, 128, 0), 86)) if DEPART else \
    ((1, (120, 34, 0), 180), (50, (68, 34, 0), 182), (90, (26, 29, 0), 196), (120, (8, 12, 0), 200), (140, (2, 4.0, 0), 180),
     (288, (2, 4.0, 0), 180))
for f, p, rz in BOAT_KEYS:
    boat.location = p
    boat.rotation_euler = (0, 0, D(rz))
    boat.keyframe_insert('location', frame=f)
    boat.keyframe_insert('rotation_euler', frame=f)
L.smooth_keys(boat)
for f in range(1, F_END + 1, 12):
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
wake = P.wake('BOAT_Wake', boat, -11.5, length=90.0 if DEPART else 70.0, w0=5.0, w1=22.0, z=0.2, kelvin=DEPART)   # V arms on the way out
for f, sc in (((1, 0.01), (44, 0.01), (90, 0.5), (140, 0.9), (240, 1.0)) if DEPART else
              ((1, 1.0), (100, 0.7), (130, 0.15), (142, 0.01))):
    wake.scale = (sc, 1, 1)
    wake.keyframe_insert('scale', frame=f)

SO.progress('section: crew, hand chain, trolleys, truck')
# ---------------------------------------------------------------- crew, hand chain, trolleys, truck
DZ = V['deck_z']
# the same season of wear as at sea: primer chips, rust from the stanchion feet, dirty runs; foam at the waterline
for _mn, _top in (('MAT_BoatWhite', 1.2), ('MAT_IceBox', 0.9)):
    if _mn in bpy.data.materials:
        S.hard_wear(bpy.data.materials[_mn], DZ, _top)
S.hard_wear(V['hull'].active_material, DZ, 1.0)
S.salt_wear(V['hull'].active_material, -0.3, 1.2)   # rust streaks, chipped paint and salt that read from the far cameras
S.hull_contact('BOAT_WaterFoam', boat, width=0.4)
crew = []
for i, (x, y, rz, o) in enumerate(((hc, 1.0, 90, 'fisherman_o'), (hc + 0.8, -1.2, 60, 'fisherman_y'), (-2.0, 1.8, 100, 'fisherman_b'),
                                   (2.5, -2.2, 200, 'fisherman_o'))):
    r = L.person(f'CREW{i}', o, (x, y, DZ), D(rz), seed=i, mats=mats)
    r.parent = boat
    crew.append(r)
if DEPART:   # bow line comes aboard and is coiled, the skipper's mate points the way out
    L.anim_poses(crew[2], [(1, 'pull'), (14, 'pull2'), (28, 'pull'), (42, 'pull2'), (56, 'idle'), (240, 'idle')])
    L.anim_poses(crew[3], [(1, 'idle'), (70, 'point'), (110, 'idle'), (240, 'idle')])
    L.anim_poses(crew[0], [(1, 'guide'), (60, 'idle'), (240, 'idle')])
    L.anim_poses(crew[1], [(1, 'reach'), (50, 'idle'), (240, 'idle')])
else:
    L.anim_poses(crew[2], [(1, 'idle'), (110, 'pull'), (125, 'pull2'), (140, 'idle')])
    L.anim_poses(crew[3], [(1, 'idle'), (100, 'point'), (130, 'idle')])
# wharf workers
wk_spots = [(4, -1.4, 90, 'dock'), (1.5, -1.6, 70, 'dock2'), (-1.5, -2.0, 30, 'dock'), (-4.0, -3.5, 120, 'dock'),
            (14, -4, 200, 'dock2'), (22, -9, 250, 'dock')]   # fewer, larger, distinct workers (Tarun)
workers = []
for i, (x, y, rz, o) in enumerate(wk_spots):
    w = L.person(f'WORKER{i}', o, (x, y, WZ), D(rz), seed=40 + i, mats=mats)
    workers.append(w)
    L.anim_poses(w, [(1, 'idle'), (60 + i * 9, 'point' if i % 5 == 0 else 'idle'), (288, 'idle')])
# hand chain 140-200: deck crew -> wharf workers
if DEPART:   # a wharf hand slips the bow line off the bollard and throws it aboard
    L.anim_poses(workers[2], [(1, 'pull'), (16, 'pull2'), (30, 'reach'), (44, 'point'), (80, 'idle')])
    mline = L.tube('BOAT_BowLine', [(-8.6, 1.4, 2.5), (-8.3, 0.3, 2.0), (-8.0, -0.6, WZ + 0.55)], 0.03, mats['rope'], 6)
    L.key_vis(mline, 1, 32)
else:
    for r in (crew[0], crew[1]):
        L.anim_poses(r, [(1, 'idle'), (135, 'idle')] + [(f, 'lift' if (f // 8) % 2 == 0 else 'pass') for f in range(140, 210, 8)] + [(220, 'idle')])
    for w in workers[:3]:
        L.anim_poses(w, [(1, 'idle'), (138, 'idle')] + [(f, 'reach' if (f // 8) % 2 == 0 else 'carry') for f in range(142, 212, 8)] + [(222, 'idle')])
    # everyone in the hand chain holds an iced crate against the chest (no empty arms while lifting and passing)
    for i, r in enumerate((crew[0], crew[1]) + tuple(workers[:3])):
        hcr = L.crate(f'CHAIN_Crate{i}', ('blue', 'white', 'blue', 'red', 'blue')[i], (0, 0, 0), 0.0, fill='mixed', mats=mats,
                      seed=500 + i)
        L._bone_attach(hcr, r, 'spine', Matrix.Translation((0.0, -0.34, 0.95)))   # skhuman faces -Y in armature space
        hl, hr = L.empty(f'CHAIN_HandL{i}', (0, 0, 0), size=0.05), L.empty(f'CHAIN_HandR{i}', (0, 0, 0), size=0.05)
        for e, sx in ((hl, 1), (hr, -1)):                  # hands on the crate's end grips
            e.parent = hcr
            e.location = (sx * 0.31, 0.0, 0.12)
        SK.ik_hands(r, hl, hr)
        for sd in 'LR':                                    # hands go to the crate only while it is carried
            c_ = r.pose.bones['forearm.' + sd].constraints['IK']
            for f, v in ((136, 0.0), (141, 1.0), (213, 1.0), (218, 0.0)):
                c_.influence = v
                c_.keyframe_insert('influence', frame=f)
        SO.grip(r, 'L')
        SO.grip(r, 'R')
        for o in [hcr] + list(hcr.children):
            L.key_vis(o, 140, 214)
# trolleys on the wharf, crates stacked on them, pushed to the truck
TRK = Vector((-12.0, -7.0, WZ))
L.weather(PL.panel_mat("MAT_ReeferBox", (0.84, 0.85, 0.84), 0.6, "X"), streak=(0.4, 0.35, 0.27), amount=0.45,
          z0=1.1, z1=2.2, dirt=(0.24, 0.2, 0.15), dirt_amount=0.55)
L.weather(L.pbr('MAT_TruckCab', (0.86, 0.87, 0.86), 0.36, 0.2, grime=0.55, coat=0.4, scale=0.6), amount=0.6, z0=0.3, z1=1.7,
          dirt_amount=0.9)
truck = PL.reefer_truck('TRK_RigidReefer', (TRK.x, TRK.y, WZ), D(-90), mats=mats)
troot = truck['root']
# the box is already two-thirds full of iced crates (front stacks) when the doors open; the rest go in from 200
for i_c, c in enumerate(truck['cargo']):
    f_in = 1 if i_c < len(truck['cargo']) * 2 // 3 else 200
    L.key_vis(c, f_in)
    for ch in c.children:
        L.key_vis(ch, f_in)
# cool interior light so the load reads through the open doors
il = bpy.data.lights.new('TRK_InteriorLight', 'AREA')
il.size = 2.0
il.energy = 45
il.color = (0.85, 0.93, 1.0)
ilo = bpy.data.objects.new('TRK_InteriorLight', il)
s.collection.objects.link(ilo)
ilo.parent = troot
ilo.location = (0.5, 0, 3.4)
for side, sgn in ((() if DEPART else (('l', 1), ('r', -1)))):
    h = truck['door_' + side]
    for f, a in ((1, 0), (140, 0), (152, 100), (215, 100), (226, 0)):
        h.rotation_euler = (0, 0, D(-a * sgn))
        h.keyframe_insert('rotation_euler', frame=f)
# cold mist puff when the doors open
mist = L.pbr('MAT_Mist', (0.92, 0.95, 0.97), 0.6, var=0.2, bump=0.0, alpha=0.18)
for i in range(0 if DEPART else 4):
    mo = L.sphere(f'MIST{i}', 0.6, (0, 0, 0), mist, (1.4, 1.0, 0.8), 12, 8, parent=troot)
    for f, p, sc in ((150, (-2.4, 0.3 * i - 0.4, 2.4), 0.3), (165, (-3.2 - i * 0.2, 0.3 * i - 0.4, 2.7), 1.0), (185, (-3.8, 0.3 * i, 3.2), 0.01)):
        mo.location = p
        mo.scale = (sc * 1.4, sc, sc * 0.8)
        mo.keyframe_insert('location', frame=f)
        mo.keyframe_insert('scale', frame=f)
    L.key_vis(mo, 150, 186)
trolleys = []
for i in range(0 if DEPART else 3):
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
    pusher = L.person(f'PUSHER{i}', 'dock2' if i % 2 else 'dock', (path[0][0] + 1.0, path[0][1], WZ), D(180), seed=70 + i, mats=mats)
    L.walk(pusher, [(path[0][0] + 1.1, path[0][1]), (path[1][0] + 1.1, path[1][1] + 0.3), (path[2][0] + 0.9, path[2][1] + 0.9)],
           175 + i * 6, 212 + i * 6, upper='push')
# truck pulls away forward along the harbour road (facing -Y), one direction
road = [(TRK.x, TRK.y), (TRK.x, TRK.y - 12), (TRK.x - 1.5, TRK.y - 40), (TRK.x - 1.5, TRK.y - 70)]
for f in (1, 230):
    troot.location = (TRK.x, TRK.y, WZ)
    troot.keyframe_insert('location', frame=f)
if not DEPART:
    P.drive(troot, road, 230, 288, truck['wheels'], r=0.5, ease=False, keystep=2)
# accelerate: retime by easing in (re-key with ease-in only)
drv = L.person('DRIVER', 'driver', (0, 0, 0), 0.0, seed=91, mats=mats)
drv.parent = troot
drv.location = (7.0, -0.55, 0.6)
L.pose(drv, 'sit')
# road, harbour buildings, ice shed, palms, parked trucks, crate stacks, lamp posts, gulls
L.box('ROAD', (9, 160, 0.04), (TRK.x - 1.5, -80, WZ + 0.01), mats['asphalt'], 0.0)
blds = P.MB()
bmat = L.weather(L.tex_pbr('MAT_Building', 'painted_plaster_wall', 0.3, attr='col', tint_amount=0.55, grime=0.6, bump=0.6),   # real plaster
                 streak=(0.32, 0.28, 0.22), amount=0.6, z0=WZ, z1=WZ + 2.5, dirt=(0.3, 0.25, 0.18), dirt_amount=0.85, scale=0.8)
shut = L.weather(P.paint_attr('MAT_Shutter', 0.6, 0.3, grime=0.5, corrugate=25.0), amount=0.5, z0=WZ, z1=WZ + 2.0)
awn = L.pbr('MAT_Awning', (0.5, 0.5, 0.5), 0.8, var=0.3, grime=0.5, attr='col')
facades = []
shut_cols = [(0.35, 0.4, 0.42), (0.55, 0.32, 0.18), (0.2, 0.35, 0.45), (0.45, 0.45, 0.4)]
awn_cols = [(0.1, 0.3, 0.55), (0.55, 0.12, 0.08), (0.12, 0.4, 0.2), (0.7, 0.55, 0.15)]
for i in range(10):
    for side in (-1, 1):
        x = TRK.x + side * rnd.uniform(14, 22)
        y = -20 - i * 14
        w, d, h = rnd.uniform(8, 12), rnd.uniform(8, 11), rnd.uniform(4, 8)
        col = rnd.choice([(0.66, 0.62, 0.55), (0.58, 0.62, 0.62), (0.7, 0.64, 0.5), (0.55, 0.56, 0.5), (0.62, 0.5, 0.42)])
        blds.box((x, y, WZ + h / 2), (w, d, h), bmat, col)
        fx = x - side * w / 2 - side * 0.03
        facades.append((side, fx, y, d))
        # upper floors: a row of framed windows per floor (always at least one row), sills, grilles, a rust/dirt run
        # under every sill, the odd AC unit; ground floor: shutter, a small window, a blank colour-block sign board
        rows = [WZ + fl * 3.0 + 0.9 for fl in range(1, 4) if WZ + fl * 3.0 + 1.6 < WZ + h] or [WZ + h * 0.66]
        for zf in rows:
            for k2 in range(4):
                yy = y - d * 0.36 + k2 * d * 0.24 + rnd.uniform(-0.15, 0.15)
                blds.box((fx - side * 0.02, yy, zf), (0.08, 1.3, 1.25), bmat, (0.22, 0.2, 0.18))            # frame
                blds.box((fx - side * 0.05, yy, zf), (0.06, 1.1, 1.05), mats['glass'])
                if rnd.random() < 0.6:
                    blds.box((fx - side * 0.08, yy, zf), (0.04, 1.1, 1.05), shut, rnd.choice(shut_cols))     # half-open shutter
                for g in range(4):                                                                        # window grille bars
                    blds.box((fx - side * 0.1, yy - 0.42 + g * 0.28, zf), (0.03, 0.03, 1.05), mats['steel'])
                blds.box((fx - side * 0.1, yy, zf - 0.66), (0.2, 1.5, 0.08), bmat, col)                      # sill
                blds.box((fx - side * 0.005, yy + rnd.uniform(-0.3, 0.3), zf - 0.66 - 0.7), (0.012, rnd.uniform(0.12, 0.3), 1.3),
                         bmat, (0.2, 0.15, 0.1))                                                          # dirt run below the sill
                if rnd.random() < 0.35:
                    blds.box((fx - side * 0.25, yy + 0.9, zf - 0.3), (0.5, 0.7, 0.45), mats['steel'])
        blds.box((fx - side * 0.02, y - d * 0.33, WZ + 1.6), (0.08, 1.0, 1.0), mats['glass'])               # shop window
        blds.box((fx - side * 0.05, y - d * 0.33, WZ + 1.05), (0.12, 1.2, 0.08), bmat, col)
        sc = rnd.choice([(0.75, 0.6, 0.1), (0.1, 0.3, 0.55), (0.55, 0.1, 0.08), (0.12, 0.42, 0.22), (0.85, 0.82, 0.75)])
        blds.box((fx - side * 0.06, y, WZ + 3.15), (0.08, d * 0.62, 0.75), awn, sc)                         # sign board (no text)
        for b2 in range(rnd.randint(2, 3)):                                                               # abstract colour blocks
            blds.box((fx - side * 0.11, y - d * 0.22 + b2 * d * 0.18, WZ + 3.15 + rnd.uniform(-0.12, 0.12)),
                     (0.02, d * 0.12, 0.28), awn, rnd.choice([(0.92, 0.9, 0.85), (0.08, 0.08, 0.08), (0.8, 0.15, 0.1)]))
        for wz in (WZ + 3.75, WZ + 3.9):                                                                  # cables along the facade
            blds.cyl((fx - side * 0.12, y - d / 2, wz), (fx - side * 0.12, y + d / 2, wz), 0.012, mats['rubber'], 5)
        blds.box((fx - side * 0.1, y + d * 0.38, WZ + 2.0), (0.12, 0.35, 0.5), mats['steel'])               # meter box
        blds.box((x, y, WZ + h + 0.45), (w, d, 0.9), bmat, col)                                 # parapet band
        blds.box((x, y, WZ + h + 0.46), (w - 0.4, d - 0.4, 0.9), bmat, (0.3, 0.29, 0.27))       # roof (darker, stained)
        blds.cyl((fx - side * 0.06, y + d * 0.45, WZ), (fx - side * 0.06, y + d * 0.45, WZ + h), 0.05, mats['steel'], 6)   # drainpipe
        blds.box((fx, y, WZ + 1.15), (0.08, 2.4, 2.3), shut, rnd.choice(shut_cols))       # rolling shutter / door
        ac = rnd.choice(awn_cols)                       # canvas awning: canopy, hanging valance, two poles to the kerb
        blds.box((fx - side * 0.9, y, WZ + 2.6), (1.8, d * 0.9, 0.06), awn, ac)
        blds.box((fx - side * 1.78, y, WZ + 2.42), (0.04, d * 0.9, 0.36), awn, ac)
        for py in (y - d * 0.42, y + d * 0.42):
            blds.cyl((fx - side * 1.75, py, WZ), (fx - side * 1.75, py, WZ + 2.6), 0.035, mats['steel'], 6)
        if h > 5:                                                                               # balcony + railing
            bz = rows[0] - 0.75
            blds.box((fx - side * 0.6, y + d * 0.12, bz), (1.2, d * 0.5, 0.14), bmat, col)
            blds.box((fx - side * 1.17, y + d * 0.12, bz + 0.95), (0.05, d * 0.5, 0.05), mats['steel'])
            for bb in range(int(d * 0.5 / 0.25) + 1):
                yb = y + d * 0.12 - d * 0.25 + bb * 0.25
                blds.box((fx - side * 1.17, yb, bz + 0.5), (0.025, 0.025, 0.9), mats['steel'])
            blds.box((fx - side * 1.0, y + d * 0.12, bz + 1.4), (0.02, d * 0.4, 0.6), awn, rnd.choice(awn_cols))   # washing on a line
        blds.box((x + w * 0.2, y, WZ + h + 1.3), (w * 0.2, d * 0.2, 0.8), mats['steel'])           # water tank on the roof
blds.obj('HARBOUR_Buildings')
wires = P.MB()                    # utility poles along the road, sagging cables between them and over to the facades
POLES = []
for i in range(1 if DEPART else 0, 12):   # o-depart: no pole in front of the rising f40-f80 camera
    for side in (-1, 1):
        px, py = TRK.x - 1.5 + (-7.0 if side < 0 else 3.9), -14 - i * 13
        POLES.append((px, py))
        wires.cyl((px, py, WZ), (px, py, WZ + 7.5), 0.11, mats['concrete'], 8, r2=0.08)
        wires.box((px, py, WZ + 7.2), (1.4, 0.1, 0.1), mats['steel'])
        for o3 in (-0.6, 0.0, 0.6):
            a3, b3 = Vector((px + o3, py, WZ + 7.25)), Vector((px + o3, py - 13, WZ + 7.25))
            mid = (a3 + b3) / 2 - Vector((0, 0, 0.45))
            if i < 11:
                wires.cyl(a3, mid, 0.012, mats['rubber'], 4)
                wires.cyl(mid, b3, 0.012, mats['rubber'], 4)
        sd, fx, fy, fd = min((f for f in facades if f[0] == side), key=lambda f: abs(f[2] - py))
        tgt = Vector((fx - sd * 0.12, max(fy - fd / 2 + 0.3, min(fy + fd / 2 - 0.3, py)), WZ + 3.9))   # ends on the facade cable
        mid = (Vector((px, py, WZ + 7.0)) + tgt) / 2 - Vector((0, 0, 0.3))
        wires.cyl((px, py, WZ + 7.0), mid, 0.01, mats['rubber'], 4)
        wires.cyl(mid, tgt, 0.01, mats['rubber'], 4)
wires.obj('HARBOUR_Wires')
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
    if DEPART and -40 <= x <= 20:   # no lamp post across the foreground of the departure camera
        continue
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

SO.progress('section: busier harbour: pennants, buoys, nets, c')
# ---------------------------------------------------------------- busier harbour: pennants, buoys, nets, crowds, autos, stalls, carts
flag_cols = [(0.75, 0.2, 0.05), (0.1, 0.45, 0.2), (0.8, 0.6, 0.1), (0.6, 0.08, 0.1), (0.15, 0.3, 0.6)]
for o in [o for o in bpy.data.objects if o.name.startswith('MOORED') and o.parent is None]:
    for j in range(2):
        fm = L.pbr(f'MAT_Pennant{j}_{o.name}', flag_cols[(hash(o.name) + j) % len(flag_cols)], 0.8, var=0.2, scale=4)
        fb = bmesh.new()
        a, b2, c2 = fb.verts.new((0, 0, 0)), fb.verts.new((0, 0, -0.5)), fb.verts.new((-0.9, 0, -0.25))
        fb.faces.new((a, b2, c2))
        pm = L.bm_to_mesh(fb, f'PENNANT_{o.name}_{j}')
        pm.materials.append(fm)
        pen = L.obj(f'PENNANT_{o.name}_{j}', pm, None, (-1.5 + j * 4.0, 0, 9.5 - j * 1.6), parent=o)
        for f in range(1, 289, 6):
            pen.rotation_euler = (0, 0, D(10 * math.sin(f / 5.0 + j)))
            pen.keyframe_insert('rotation_euler', frame=f)
    # a heap of green net on the moored deck
    nb = bmesh.new()
    bmesh.ops.create_icosphere(nb, subdivisions=3, radius=1.0)
    for v in nb.verts:
        v.co = Vector((v.co.x * 1.6, v.co.y * 1.1, max(0.0, v.co.z) * 0.55)) * (1 + 0.15 * noise.noise(v.co * 3))
    nm_ = L.bm_to_mesh(nb, f'NETHEAP_{o.name}', smooth=True)
    nm_.materials.append(mats['rope_green'])
    L.obj(f'NETHEAP_{o.name}', nm_, None, (-6.5, 0.5, 1.55), parent=o)
buoy = L.sphere_mesh('BUOY', 0.35, 12, 8)
buoy.materials.append(L.pbr('MAT_Buoy', (0.8, 0.3, 0.05), 0.5, var=0.3, grime=0.4, coat=0.3))
for i in range(22):
    bx, by = rnd.uniform(-80, 140), rnd.uniform(16, 60)
    if abs(bx - 20) < 30 and by < 40:
        continue
    bo_ = L.obj(f'BUOY{i}', buoy, None, (bx, by, 0.05))
    for f in range(1, 289, 16):
        bo_.location.z = 0.05 + 0.08 * math.sin(f / 9.0 + i)
        bo_.keyframe_insert('location', frame=f)
# crowd along the wharf and by the ice shed (clear of the truck road x -17..-7 and the hand chain)
crowd_outfits = ['dock', 'dock2', 'dock', 'farm', 'dock2', 'fisherman_b', 'dock']
placed = 0
tries = 0
while placed < 8 and tries < 400:      # a few distinct people, not a crowd of extras
    tries += 1
    x, y = rnd.uniform(-60, 60), rnd.uniform(-24, -2.5)
    if -19 < x < -5 or (-6 < x < 8 and y > -6) or (16 < x < 32 and -19 < y < -9):
        continue
    if any((x - qx) ** 2 + (y - qy) ** 2 < 1.5 ** 2 for qx, qy in POLES):
        continue
    if -33 < x < -27 and -7.5 < y < -4.5:    # drums and pallet
        continue
    c = L.person(f'CROWD{placed}', rnd.choice(crowd_outfits), (x, y, WZ), D(rnd.uniform(0, 360)), seed=200 + placed, mats=mats)
    if placed % 3 == 0:
        L.walk(c, [(x, y), (x + rnd.uniform(-8, 8), y + rnd.uniform(-3, 3))], rnd.randint(1, 60), rnd.randint(150, 288))
    else:
        L.anim_poses(c, [(1, 'idle'), (rnd.randint(40, 200), 'point' if placed % 4 == 0 else 'idle'), (288, 'idle')])
    placed += 1


for i in range(8):
    side = -1 if i % 2 else 1
    x = (-19.3 + rnd.uniform(0.0, 0.9)) if side < 0 else (-8.5 + rnd.uniform(0.0, 3.8))   # kerbs, clear of the facades
    y = -26 - i * 2.1 + rnd.uniform(-0.8, 0.8)
    c = L.person(f'STREET{i}', rnd.choice(crowd_outfits), (x, y, WZ), D(rnd.uniform(0, 360)), seed=400 + i, mats=mats)
    if i % 3 == 0:
        L.walk(c, [(x, y), (x + rnd.uniform(-0.6, 0.6), y + rnd.choice((-7, 7)))], rnd.randint(200, 240), 288)
    else:
        L.anim_poses(c, [(1, 'idle'), (rnd.randint(200, 260), 'point' if i % 5 == 0 else 'idle'), (288, 'idle')])


def auto_rickshaw(name, loc, rz):
    """Three-wheeler: yellow lower body, black canvas hood, one front wheel, two rear (no markings)."""
    mb = P.MB()
    yel = L.weather(L.pbr('MAT_AutoYellow', (0.75, 0.6, 0.08), 0.35, grime=0.4, coat=0.4), amount=0.3, z0=0.0, z1=0.6)
    grn = L.pbr('MAT_AutoGreen', (0.1, 0.32, 0.15), 0.4, grime=0.4, coat=0.3)
    blk = L.pbr('MAT_AutoHood', (0.03, 0.03, 0.03), 0.8, var=0.2, scale=6)
    mb.box((0, 0, 0.55), (2.3, 1.3, 0.5), grn)
    mb.box((0.95, 0, 0.95), (0.5, 1.2, 0.9), yel)
    mb.box((-0.25, 0, 1.0), (1.4, 1.3, 0.12), yel)
    mb.box((-0.15, 0, 1.75), (2.1, 1.35, 0.1), blk)
    for sy in (-0.64, 0.64):
        mb.box((-0.6, sy, 1.35), (1.0, 0.04, 0.8), blk)
        mb.cyl((0.8, sy, 1.0), (0.8, sy, 1.75), 0.025, mats['steel'], 6)
    mb.box((1.21, 0, 1.4), (0.04, 1.1, 0.55), mats['glass'])
    for p_ in ((1.05, 0, 0.25), (-0.8, 0.6, 0.25), (-0.8, -0.6, 0.25)):
        mb.cyl((p_[0], p_[1] - 0.07, p_[2]), (p_[0], p_[1] + 0.07, p_[2]), 0.25, mats['rubber'], 14)
    o = mb.obj(name, None, loc)
    o.rotation_euler = (0, 0, rz)
    return o


for i, (x, y, rz) in enumerate(((-24, -18, 90), (-30, -21, 80), (6, -20, 180), (34, -6, 20), (-6.5, -44, 95),
                                (-6.0, -58, -85))):
    auto_rickshaw(f'AUTO{i}', (x, y, WZ), D(rz))
# fish-sale stalls under blue tarps by the ice shed, wooden hand carts with baskets
tarp = L.pbr('MAT_Tarp', (0.1, 0.3, 0.6), 0.7, var=0.25, grime=0.4, scale=2)
for i, (x, y) in enumerate(((36, -10), (40, -10), (44, -10), (36, -16))):
    st = P.MB()
    st.box((x, y, WZ + 0.8), (3.0, 1.6, 0.08), mats['wood'])
    for dx in (-1.4, 1.4):
        for dy in (-0.7, 0.7):
            st.box((x + dx, y + dy, WZ + 1.25), (0.06, 0.06, 2.5), mats['wood'])
    tb = bmesh.new()
    st.box((x, y, WZ + 2.55), (3.4, 2.0, 0.04), tarp)
    for k in range(3):
        st.cyl((x - 0.8 + k * 0.8, y, WZ + 0.84), (x - 0.8 + k * 0.8, y, WZ + 1.05), 0.28, mats['rope'], 12, r2=0.33)
    st.obj(f'STALL{i}')
    L.crate(f'STALL{i}_Crate', 'blue', (x + 0.5, y - 1.2, WZ), 0.3, fill='mixed', mats=mats, seed=300 + i)
for i, (x, y, rz) in enumerate(((10, -14, 30), (-36, -4, 100), (48, -20, 200))):
    hc_ = P.MB()
    hc_.box((0, 0, 0.75), (2.0, 1.1, 0.08), mats['wood'])
    for sy in (-0.55, 0.55):
        hc_.box((0, sy, 0.9), (2.0, 0.05, 0.25), mats['wood'])
        hc_.cyl((0.1, sy * 1.15, 0.45), (0.1, sy * 1.25, 0.45), 0.45, mats['wood'], 16)
    hc_.box((1.5, 0.35, 0.8), (1.2, 0.06, 0.06), mats['wood'])
    hc_.box((1.5, -0.35, 0.8), (1.2, 0.06, 0.06), mats['wood'])
    for k in range(2):
        hc_.cyl((-0.4 + k * 0.8, 0, 0.8), (-0.4 + k * 0.8, 0, 1.15), 0.3, mats['rope'], 12, r2=0.36)
    o = hc_.obj(f'CART{i}', None, (x, y, WZ))
    o.rotation_euler = (0, 0, D(rz))

SO.progress('section: camera')
# ---------------------------------------------------------------- camera
cam = L.camera('Camera', 30, (60, -20, 25), (90, 25, 2))
cam.data.dof.aperture_fstop = 11.0   # the near rafted boats stay sharp in the f1-f72 aerial move
keys = [
    (1, (70.0, -24.0, 26.0), (110.0, 28.0, 2.0), 30),
    (72, (24.0, -20.0, 15.0), (36.0, 18.0, 2.0), 30),
    (130, (7.0, -7.5, WZ + 3.0), (0.0, 3.0, 2.4), 28),
    (175, (1.0, -9.0, WZ + 2.6), (-6.0, -3.0, 1.8), 28),
    (192, (-5.0, -0.5, WZ + 6.0), (TRK.x, TRK.y, WZ + 1.4), 28),
    (204, (TRK.x + 0.8, TRK.y + 10.5, WZ + 3.3), (TRK.x, TRK.y + 0.5, WZ + 1.6), 32),
    (216, (TRK.x + 0.3, TRK.y + 9.5, WZ + 3.1), (TRK.x, TRK.y + 0.5, WZ + 1.6), 32),
    (230, (-6.5, 3.2, WZ + 3.0), (TRK.x, TRK.y - 2.0, WZ + 1.4), 30),
]
# follow the truck at a fixed offset, sampled from its evaluated path so the camera never catches up with it
for f in list(range(246, 288, 6)) + [288]:
    s.frame_set(f)
    tp = troot.matrix_world.translation
    keys.append((f, (tp.x + 2.0, tp.y + 9.0, WZ + 3.0), (tp.x - 0.5, tp.y - 4.0, WZ + 1.5), 30))
if DEPART:
    # on the wharf at the bow as the line comes off, then rising behind the boat as it heads for the sunrise
    keys = [(1, (5.0, -10.0, WZ + 3.4), (-7.0, 3.0, 2.2), 30), (36, (6.0, -11.0, WZ + 4.4), (-5.0, 5.5, 2.2), 30)]   # wharf hands mid-distance
    focus = [(1, 15.5), (36, 16.5)]
    for f in list(range(64, F_END, 16)) + [F_END]:
        s.frame_set(f)
        bp = boat.matrix_world.translation
        u = (f - 64) / (F_END - 64)
        keys.append((f, (bp.x - 10.0 + 3 * u, bp.y - 24.0 - 6 * u, 9.0 + 3 * u), (bp.x + 2.0, bp.y + 14.0, 0.0), 30))   # high astern: the V-wake opens below
        focus.append((f, 30.0))
    s.frame_set(1)
    L.cam_path(cam, keys, focus=focus)
else:
    s.frame_set(1)
    L.cam_path(cam, keys, focus=[(1, 50.0), (72, 30.0), (130, 9.0), (175, 8.0), (204, 10.0), (216, 9.0), (230, 10.0), (288, 9.0)])
s.camera = cam
L.decimate_shared()          # repeated scans / palms / crates at 25%: most of the 19 M triangles were repeats
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
sys.argv = [sys.argv[0], '--', 'o-depart' if DEPART else 'o-return', '1', str(F_END), 'exterior']
exec(compile(open(os.path.join(HERE, 'render_settings.py')).read(), 'render_settings.py', 'exec'))
s.render.motion_blur_shutter = 0.1   # the aerial move smeared whole tiles at 0.5 and 0.25 (test render at f60 without blur is sharp)
bpy.ops.wm.save_mainfile()
print('BUILT', OUT, len(bpy.data.objects), 'objects')
