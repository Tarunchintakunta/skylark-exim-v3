"""Build assets-src/blender/o-catch.blend (docs/blender/SCENES.md §1-2): o-catch-a (1-192) + o-catch-b (192-383).

Run from the repo root:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_o_catch.py
Everything is procedural and keyed (no simulation caches): the fish spill is computed ballistically, so headless
renders need no bake. World axes: vessel bow +X, starboard (boom side, sea with the net) +Y, deck at z = 1.5.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import sklib as L  # noqa: E402
import sklib_sea as S  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'o-catch.blend')
D = math.radians
rnd = random.Random(42)

s = L.reset()
s.frame_start, s.frame_end = 1, 383
s.render.fps = 24
mats = L.M()
sun = L.hdri('kloofendal_48d_partly_cloudy_puresky_4k', strength=0.7, rot=0.0, sun_strength=3.0)

# ---------------------------------------------------------------- vessel
V = S.vessel('BOAT', mats=mats)
boat = V['root']
DZ = V['deck_z']
# gentle roll and pitch (the sea moves the boat; crew and props are children so they move with it)
for f in range(1, 384, 12):
    boat.rotation_euler = (D(1.3 * math.sin(f / 26.0)), D(0.6 * math.sin(f / 37.0 + 1)), 0)
    boat.location = (0, 0, 0.08 * math.sin(f / 21.0))
    boat.keyframe_insert('rotation_euler', frame=f)
    boat.keyframe_insert('location', frame=f)

# ---------------------------------------------------------------- sea
sea = L.ocean('Ocean', size=60, repeat=6, res=11, choppy=1.0, wind=9.0, scale=0.7, f0=1, f1=383, foam=0.3)
cut = L.box('OceanCut', (24.5, 6.6, 6.0), (0, 0, 0), mats['steel'], 0.0)
cut.display_type = 'WIRE'
cut.hide_render = True
cut.parent = boat
bm = sea.modifiers.new('HullCut', 'BOOLEAN')
bm.operation = 'DIFFERENCE'
bm.object = cut
bm.solver = 'FLOAT' if 'FLOAT' in [e.identifier for e in bm.bl_rna.properties['solver'].enum_items] else 'FAST'
far = L.far_water('SeaFar', 8000, -0.3, hole=330.0)

# ---------------------------------------------------------------- distant boats + gulls
for i, (x, y, rz) in enumerate(((-260, 420, 0.4), (180, 520, 2.6))):
    b = S.vessel(f'FARBOAT{i}', loc=(x, y, 0), rot_z=rz, mats=mats, detail=False)
for i in range(7):
    g = S.gull(f'GULL{i}', (0, 0, 0))
    cx, cy, cz = rnd.uniform(-6, 10), rnd.uniform(6, 14), rnd.uniform(7, 13)
    rad = rnd.uniform(4, 8)
    ph = rnd.uniform(0, 6.28)
    path = [(cx + rad * math.cos(ph + k * 0.35), cy + rad * 0.6 * math.sin(ph + k * 0.35), cz + 0.6 * math.sin(k * 0.5))
            for k in range(24)]
    S.flap(g, 1, 383, period=rnd.randint(9, 13), amp=32, path=path)

# ---------------------------------------------------------------- net, ropes, floats
NETX = 1.6
bag_parent = L.empty('NET_Swing', (0, 0, 0), size=0.6)
cl = bag_parent.constraints.new('COPY_LOCATION')
cl.target = V['boom_tip']
bag_root, net, core, bag_fish, bag_floats = S.net_bag('NET', R=1.45, depth=2.5, mats=mats, n_fish=170, n_tuna=6)
bag_root.parent = bag_parent
aim = L.empty('BOOM_Aim', (1.0, 7.0, 9.4), size=0.5)
dt = V['boom_pivot'].constraints.new('DAMPED_TRACK')
dt.target = aim
dt.track_axis = 'TRACK_Z'


def key_aim(f, p):
    aim.location = p
    aim.keyframe_insert('location', frame=f)


def key_rope(f, length, swing=0.0):
    bag_root.location = (0, 0, -length)
    bag_root.keyframe_insert('location', frame=f)
    bag_parent.rotation_euler = (D(swing), 0, 0)
    bag_parent.keyframe_insert('rotation_euler', frame=f)


PILE = Vector((NETX + 0.8, 0.0, DZ))
# boom out over the sea, net in the water
key_aim(1, (NETX, 8.0, 9.6))
key_aim(100, (NETX, 8.0, 9.6))
# boom luffs in over the deck (100-150); tip above the pile
key_aim(150, (PILE.x, PILE.y, 12.0))
key_aim(230, (PILE.x, PILE.y, 12.0))
key_aim(300, (NETX, 5.0, 10.5))
key_rope(1, 10.4)
key_rope(40, 10.2, 1.0)
key_rope(100, 2.4, -2.0)
key_rope(118, 2.4, 8.0)   # pendulum while the boom swings in (<= 8 degrees)
key_rope(134, 2.4, -5.0)
key_rope(150, 2.4, 2.0)
key_rope(160, 4.2, -1.0)
key_rope(174, 6.75, 0.0)
key_rope(178, 6.75, 0.0)
key_rope(200, 6.0, 0.0)
key_rope(240, 3.0, 0.0)
L.smooth_keys(aim)
L.smooth_keys(bag_root)
L.smooth_keys(bag_parent)
# whip rope boom tip -> hook (stretch)
rope = L.cyl('NET_Whip', 0.018, 1.0, (0, 0, 0), mats['rope'], 8, origin='base')
rope.parent = bag_root
st = rope.constraints.new('STRETCH_TO')
st.target = V['boom_tip']
st.volume = 'NO_VOLUME'
# drum -> post top rope
dw = V['drum_world']
L.tube('BOOM_DrumRope', [(dw[0] + 0.3, dw[1], dw[2] + 0.3), (V['post_top'][0], V['post_top'][1] - 0.2, 5.0),
                        (V['post_top'][0], V['post_top'][1], V['post_top'][2] - 0.1)], 0.02, mats['rope'], 8).parent = boat
# drum turns while hauling (40-100) and paying out (150-178)
drum = V['drum']
drum.rotation_mode = 'XYZ'
for f, a in ((1, 0), (40, 0), (100, -10.5), (150, -10.5), (178, -6.0), (240, -12)):
    drum.rotation_euler = (0, a, 0)
    drum.keyframe_insert('rotation_euler', frame=f)

# float ring on the water at the start, beside the hull (hidden once the bag is up)
fl = bpy.data.meshes['NET_FloatM']
ring = L.empty('FLOATRING', (NETX, 9.6, 0), size=1)
fbig = L.sphere_mesh('FLOATRING_float', 0.2, 12, 8)
fbig.materials.append(mats['float_yellow'])
for i in range(30):
    a = 2 * math.pi * i / 30
    o = L.obj(f'FLOATRING_f{i}', fbig, None, (3.4 * math.cos(a), 2.6 * math.sin(a), 0.3), (0, 0, a), (1.4, 1, 0.8), parent=ring)
    for f in range(1, 80, 8):
        o.location.z = 0.32 + 0.22 * math.sin(f / 9.0 + i * 0.7)
        o.keyframe_insert('location', frame=f)
ringline = L.tube('FLOATRING_Line', [(NETX + 3.4 * math.cos(2 * math.pi * k / 40), 9.6 + 2.6 * math.sin(2 * math.pi * k / 40), 0.3)
                                    for k in range(41)], 0.015, mats['rope'], 6)
for o in [ring, ringline]:
    L.key_vis(o, 1, 70)
    for c in o.children:
        L.key_vis(c, 1, 70)
# boil: foam discs and leaping fish around the bag mouth (1-60)
foam_mat = L.pbr('MAT_Foam', (0.9, 0.93, 0.95), 0.6, var=0.3, bump=0.5, scale=8, alpha=0.6)
disc = L.cyl_mesh('BOIL_disc', 1.0, 0.02, 24)
disc.materials.append(foam_mat)
for i in range(9):
    p = (NETX + rnd.uniform(-2.6, 2.6), 9.6 + rnd.uniform(-1.8, 1.8), 0.05)
    d = L.obj(f'BOIL_{i}', disc, None, p)
    for f, sc in ((1, rnd.uniform(0.2, 0.5)), (20 + i * 3, rnd.uniform(0.7, 1.1)), (60, 0.3), (75, 0.01)):
        d.scale = (sc, sc, 1)
        d.keyframe_insert('scale', frame=f)
for i in range(12):
    f0 = rnd.randint(2, 60)
    p0 = Vector((NETX + rnd.uniform(-2.5, 2.5), 9.6 + rnd.uniform(-1.6, 1.6), -0.1))
    v = Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(2.2, 3.2)))
    fo = L.fish(f'LEAP_{i}', 'mackerel', tuple(p0), (0, 0, rnd.uniform(0, 6.28)), 1.0)
    for k in range(0, 18, 2):
        t = k / 24
        pos = p0 + v * t + Vector((0, 0, -4.9 * t * t))
        fo.location = pos
        fo.rotation_euler = (rnd.uniform(-0.3, 0.3), -math.atan2(v.z - 9.8 * t, 1.5), fo.rotation_euler.z)
        fo.keyframe_insert('location', frame=f0 + k)
        fo.keyframe_insert('rotation_euler', frame=f0 + k)
    L.key_vis(fo, f0, f0 + 18)

# water streaming off the bag (60-170)
streams = []
for i in range(0):  # replaced by the drip field below (solid stream rods read as white sticks)
    a = rnd.uniform(0, 2 * math.pi)
    r = rnd.uniform(0.2, 0.9)
    sth = L.cyl(f'NET_Stream{i}', rnd.uniform(0.012, 0.03), 1.0, (r * math.cos(a), r * math.sin(a), -2.35),
                mats['water_clear'], 8, origin='base', rot=(D(180), 0, 0), parent=bag_root)
    for f, sz in ((58, 0.01), (66, rnd.uniform(1.5, 3.0)), (110, rnd.uniform(1.0, 2.0)), (150, rnd.uniform(0.6, 1.2)),
                  (170, 0.3), (176, 0.01)):
        sth.scale = (1, 1, sz)
        sth.keyframe_insert('scale', frame=f)
    streams.append(sth)
# splash at break-out
spl = L.cyl('SPLASH_Ring', 1.0, 0.25, (NETX, 8.0, 0.0), foam_mat, 32, r2=1.3)
for f, sc in ((55, 0.3), (62, 1.5), (80, 2.8), (95, 0.01)):
    spl.scale = (sc, sc, max(0.01, 1.4 - f / 80))
    spl.keyframe_insert('scale', frame=f)
drops = []
drip = L.pbr('MAT_Drip', (0.85, 0.92, 0.96), 0.03, var=0.0, bump=0.0, transmission=0.95, ior=1.33, coat=0.8)
dmesh = L.sphere_mesh('DROP_mesh', 1.0, 8, 6)
for i in range(260):
    dpo = L.obj(f'DROP_{i}', dmesh, drip, (0, 0, 0))
    r = rnd.uniform(0.006, 0.02)
    dpo.scale = (r, r, r * rnd.uniform(2.0, 4.5))
    # dense dripping while the bag is out of the water, thinning out as it drains
    f0 = int(56 + (rnd.random() ** 1.6) * 118)
    a = rnd.uniform(0, 6.28)
    drops.append((dpo, f0, a))

# ---------------------------------------------------------------- release + fish spill onto the deck (176-192)
REL = 176
for o in [core] + bag_fish:
    L.key_vis(o, 1, REL + 1)
net.scale = (1, 1, 1)
net.keyframe_insert('scale', frame=REL)
net.scale = (0.75, 0.75, 0.55)
net.keyframe_insert('scale', frame=REL + 8)
# the pile: a low mound of fish mass + fish lying on it (children of the boat)
pm = L.sphere_mesh('PILE_Mound', 1.0, 32, 16)
pm.materials.append(bpy.data.materials['MAT_FishMass'])
pm.materials.clear()
pm.materials.append(L.pbr('MAT_PileMass', (0.38, 0.42, 0.46), 0.3, 0.5, var=0.7, bump=1.0, scale=22, coat=0.3))
mound = L.obj('PILE_Mound', pm, None, tuple(PILE), scale=(1.5, 1.25, 0.32), parent=boat)
for f, sc in ((REL + 2, 0.05), (REL + 10, 0.85), (192, 1.0), (330, 0.8)):
    mound.scale = (1.5 * max(sc, 0.3), 1.25 * max(sc, 0.3), 0.32 * sc)
    mound.keyframe_insert('scale', frame=f)
L.key_vis(mound, REL + 2)


def mound_z(x, y):
    dx, dy = (x - PILE.x) / 1.5, (y - PILE.y) / 1.25
    r2 = dx * dx + dy * dy
    return DZ + (0.32 * math.sqrt(max(0.0, 1 - r2)) if r2 < 1 else 0.0)


spill = []
for i in range(320):
    kind = 'tuna' if i < 6 else ('tuna_s' if i < 46 else ('seer' if i < 52 else 'mackerel'))
    sc = rnd.uniform(0.7, 0.85) if kind == 'tuna' else rnd.uniform(0.85, 1.15)
    a = rnd.uniform(0, 2 * math.pi)
    rr = math.sqrt(rnd.random()) * (0.9 if kind == 'tuna' else 1.25)
    land = Vector((PILE.x + rr * math.cos(a) * 1.15, PILE.y + rr * math.sin(a), 0))
    land.z = mound_z(land.x, land.y) + (0.05 if kind != 'tuna' else 0.12)
    start = Vector((PILE.x + rnd.uniform(-0.5, 0.5), PILE.y + rnd.uniform(-0.5, 0.5), DZ + rnd.uniform(0.7, 1.6)))
    fo = L.fish(f'SPILL_{i}', kind, tuple(start), (0, 0, 0), sc, parent=boat)
    f0 = REL + rnd.randint(0, 4)
    fall = math.sqrt(2 * max(0.05, start.z - land.z) / 9.8) * 24
    f1 = f0 + max(4, int(fall))
    rz = rnd.uniform(0, 6.28)
    fo.rotation_euler = (rnd.uniform(-1, 1), rnd.uniform(-0.8, 0.8), rz)
    fo.keyframe_insert('location', frame=f0)
    fo.keyframe_insert('rotation_euler', frame=f0)
    fo.location = land + Vector((0, 0, 0.0))
    fo.rotation_euler = (D(90) * (1 if rnd.random() < 0.5 else -1) + rnd.uniform(-0.25, 0.25), rnd.uniform(-0.1, 0.1), rz + rnd.uniform(-0.5, 0.5))
    fo.keyframe_insert('location', frame=f1)
    fo.keyframe_insert('rotation_euler', frame=f1)
    fo.location.z = land.z + 0.04
    fo.keyframe_insert('location', frame=f1 + 2)
    fo.location.z = land.z
    fo.keyframe_insert('location', frame=f1 + 4)
    L.key_vis(fo, f0)
    spill.append((fo, kind))
for o, _ in spill:
    L.linear_keys(o) if False else None

# ---------------------------------------------------------------- crates: sorting row, hand chain, hold
row = []
for i in range(6):
    c = L.crate(f'SORT_Crate{i}', ['blue', 'red', 'blue', 'white', 'blue', 'red'][i], (PILE.x - 1.4 + i * 0.62, -1.75, DZ),
                0.0, fill=('tuna' if i in (1, 4) else 'mixed'), parent=boat, mats=mats, seed=i)
    row.append(c)
    t_fill = 200 + i * 10
    for ch in c.children:
        L.key_vis(ch, t_fill)
# crates passed to the hatch and lowered into the hold (one chain of three)
hold_floor = V['hold_floor']
hx0, hx1, hy = V['hatch']
HC = Vector(((hx0 + hx1) / 2, 0.0, DZ))
for k, c in enumerate(row[3:]):
    f0 = 262 + k * 18
    p0 = c.location.copy()
    path = [(f0, p0), (f0 + 6, p0 + Vector((0, 0, 0.8))), (f0 + 14, Vector((hx0 - 0.1, -0.6, DZ + 1.0))),
            (f0 + 22, Vector((HC.x - 0.4 + k * 0.4, -0.3, DZ + 0.3))),
            (f0 + 34, Vector((HC.x - 0.6 + k * 0.6, -0.4 + 0.3 * k, hold_floor + 0.3)))]
    for f, p in path:
        c.location = p
        c.keyframe_insert('location', frame=f)
    L.smooth_keys(c)
# the hold: rows of iced crates, some two high
k = 0
for ix in range(6):
    for iy in range(7):
        x = HC.x - 1.9 + ix * 0.68
        y = -1.45 + iy * 0.45
        if abs(x - HC.x) < 0.8 and -0.6 < y < 0.4:
            continue  # space where the chain lands its crates
        lv = 2 if (ix + iy) % 3 == 0 else 1
        for z in range(lv):
            L.crate(f'HOLD_Crate{k}', rnd.choice(['blue', 'blue', 'white', 'red']), (x, y, hold_floor + z * 0.29),
                    rnd.uniform(-0.04, 0.04), fill=rnd.choice(['mixed', 'fish', 'tuna', 'ice']) if z == lv - 1 else None,
                    parent=boat, mats=mats, seed=k)
            k += 1

# ---------------------------------------------------------------- crew (orange / yellow oilskins, caps, gloves)
P = L.person
crew = {}


def crew_member(nm, outfit, loc, rot, h=1.72, b=1.0):
    r = P(nm, outfit, (loc[0], loc[1], DZ), D(rot), h, build=b, seed=hash(nm) & 255, mats=mats)
    r.parent = boat
    crew[nm] = r
    return r


w = crew_member('CREW_Winch', 'fisherman_b', (-2.6, -0.9), 90, 1.68)
L.anim_poses(w, [(1, 'idle'), (36, 'pull'), (60, 'pull2'), (84, 'pull'), (100, 'pull2'), (150, 'idle'), (160, 'pull'),
                 (180, 'idle'), (383, 'idle')])
r1 = crew_member('CREW_Rail1', 'fisherman_o', (0.2, 2.25), 90, 1.75, 1.05)
L.anim_poses(r1, [(1, 'idle'), (40, 'reach'), (95, 'reach'), (110, 'guide'), (150, 'guide'), (170, 'reach'), (186, 'idle')])
r2 = crew_member('CREW_Rail2', 'fisherman_y', (2.9, 2.2), 100, 1.7)
L.anim_poses(r2, [(1, 'idle'), (42, 'point'), (90, 'idle'), (112, 'guide'), (155, 'guide'), (175, 'pull'), (186, 'idle')])
c3 = crew_member('CREW_Mid', 'fisherman_o', (0.9, -0.3), 60, 1.74)
L.anim_poses(c3, [(1, 'idle'), (60, 'idle'), (100, 'stand'), (150, 'idle')])
c4 = crew_member('CREW_Hatch', 'fisherman_y', (5.95, 0.3), 180, 1.7)
L.anim_poses(c4, [(1, 'idle'), (383, 'idle')])
c5 = crew_member('CREW_Ice', 'fisherman_b', (5.3, -1.75), 180, 1.69)
c6 = crew_member('CREW_Stern', 'fisherman_o', (-1.2, 1.6), 30, 1.71)
L.anim_poses(c6, [(1, 'idle'), (100, 'stand'), (176, 'pull'), (186, 'idle')])
# the guiding crew step back as the bag comes inboard, then step in to sort (walk keys after 186)
L.walk(r1, [(0.2, 2.25), (0.6, 1.7), (1.3, 1.25)], 150, 176)
L.walk(r2, [(2.9, 2.2), (3.4, 1.6), (3.8, 1.0)], 155, 182)
L.walk(c3, [(0.9, -0.3), (1.2, -0.9), (1.7, -1.1)], 176, 196)
L.walk(c6, [(-1.2, 1.6), (-0.5, 1.2), (0.6, 0.5)], 186, 210)
# 192-330: sorting by hand around the pile (kneel cycle), shovelling ice over the crates, passing crates
for nm, (x, y, rot) in {'CREW_Rail1': (1.3, 1.25, -90), 'CREW_Rail2': (3.9, 0.9, -150), 'CREW_Mid': (1.8, -1.05, 80),
                        'CREW_Stern': (0.6, 0.45, -20)}.items():
    r = crew[nm]
    for f in (200, 383):
        r.location = (x, y, DZ)
        r.rotation_euler = (0, 0, D(rot))
        r.keyframe_insert('location', frame=f)
        r.keyframe_insert('rotation_euler', frame=f)
    seq = []
    ph = rnd.randint(0, 6)
    for f in range(200 + ph, 383, 14):
        seq.append((f, 'kneel' if (f // 14) % 2 == 0 else 'kneel2'))
    L.anim_poses(r, seq)
L.anim_poses(c5, [(1, 'idle'), (190, 'idle')] + [(f, 'shovel' if (f // 16) % 2 == 0 else 'shovel2') for f in range(200, 383, 16)])
shovel = bpy.data.objects['BOAT_Shovel0']
cs = shovel.constraints.new('CHILD_OF')
cs.target = bpy.data.objects['CREW_Ice']
cs.subtarget = 'wr_R'
cs.inverse_matrix.identity()
cs.influence = 0.0
cs.keyframe_insert('influence', frame=196)
cs.influence = 1.0
cs.keyframe_insert('influence', frame=197)
shovel.location = (0.0, 0.0, -0.1)
shovel.rotation_euler = (0, D(-90), 0)
shovel.keyframe_insert('location', frame=197)
shovel.keyframe_insert('rotation_euler', frame=197)
# hand chain to the hatch: CREW_Hatch + one crewman in the hold
L.anim_poses(c4, [(240, 'idle')] + [(f, 'pass' if (f // 9) % 2 == 0 else 'lift') for f in range(258, 340, 9)] + [(350, 'idle')])

# ---------------------------------------------------------------- camera (one continuous shot)
cam = L.camera('Camera', 30, (-6, -6, 6.5), (2, 8, 0))
cam.data.dof.aperture_fstop = 5.6
keys = [
    (1, (-3.6, -4.6, 6.2), (3.0, 8.8, 0.4), 26),
    (40, (-2.4, -3.9, 5.6), (2.6, 8.2, 1.2), 26),
    (100, (3.6, -1.4, 2.5), (1.8, 7.0, 5.4), 22),
    (130, (4.2, -3.1, 3.0), (2.2, 3.6, 6.2), 22),
    (150, (5.4, -5.0, 3.0), (2.4, 0.6, 7.2), 24),
    (170, (3.0, -4.4, 3.2), (2.4, 0.2, 3.2), 26),
    (192, (-1.3, -3.4, 3.4), (PILE.x, PILE.y, DZ + 0.3), 30),
    (260, (4.8, -3.6, 3.0), (2.6, 0.0, DZ + 0.2), 32),
    (330, (5.2, -2.4, 6.4), (HC.x, 0.0, hold_floor + 0.6), 30),
    (383, (HC.x + 0.05, -0.02, 4.9), (HC.x, 0.0, hold_floor), 32),
]
L.cam_path(cam, keys, focus=[(1, 14.0), (40, 12.5), (100, 8.0), (130, 6.5), (150, 5.5), (192, 4.2), (260, 3.4), (330, 6.0), (383, 6.0)])
s.camera = cam

# ---------------------------------------------------------------- water drops falling off the bag (world space)
for dpo, f0, a in drops:
    con = dpo.constraints.new('COPY_LOCATION')
    con.target = bag_root
    con.use_offset = True
    rr = 0.95 * math.sqrt(rnd.random())
    x, y = rr * math.cos(a), rr * math.sin(a)
    z0 = -2.25 - 0.25 * (1 - (rr / 0.95) ** 2)
    for k, dz in ((0, 0.0), (3, -0.11), (6, -0.44), (9, -0.99), (12, -1.76)):   # free fall at 24 fps
        dpo.location = (x, y, z0 + dz)
        dpo.keyframe_insert('location', frame=f0 + k)
    L.key_vis(dpo, f0, f0 + 12)

# ---------------------------------------------------------------- render settings + save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
sys.argv = [sys.argv[0], '--', 'o-catch', '1', '383', 'sea']
exec(compile(open(os.path.join(HERE, 'render_settings.py')).read(), 'render_settings.py', 'exec'))
s.view_settings.look = 'AgX - Medium High Contrast'
s.render.filepath = '//../render/o-catch/'
bpy.ops.wm.save_mainfile()
print('BUILT', OUT, len(bpy.data.objects), 'objects')
