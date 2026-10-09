"""Build assets-src/blender/port.blend (docs/blender/SCENES.md §10-11, redesign prompt §5.1):
x-cranes (1-288) + x-ship (288-479) on one timeline, shared frame 288.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_port.py

World: quay edge on y = 0 (land y < 0, sea y > 0), quay top z = 3, water z = 0. Cranes along X; crane 2 at x = 0.
Every lifted box is keyed per frame from the evaluated spreader position, so it hangs on the 4 cables from lock to
release with no drift; trucks only drive forward; the ship is static for all of x-cranes.
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
import sklib_port as P  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'port.blend')
D = math.radians
rnd = random.Random(9)
QZ = 3.0

s = L.reset()
s.frame_start, s.frame_end = 1, 479
mats = L.M()
L.hdri('kloofendal_48d_partly_cloudy_puresky_4k', strength=0.7, rot=40.0, sun_strength=3.0)

# ---------------------------------------------------------------- ground, quay, water
asph = mats['asphalt']
conc = mats['concrete']
L.box('QUAY_Yard', (700, 300, 5.0), (0, -190, QZ - 2.5), asph, 0.0)
L.box('QUAY_Apron', (700, 40.2, 5.02), (0, -20, QZ - 2.49), conc, 0.0)
L.box('QUAY_Face', (700, 0.6, 5.5), (0, -0.1, QZ - 3.0), pbr_face := L.pbr('MAT_QuayFace', (0.42, 0.41, 0.38), 0.85,
                                                                              grime=0.5, scale=0.2), 0.0)
sea = L.ocean('Harbour', size=60, repeat=8, res=10, choppy=0.6, wind=5.5, scale=0.35, f0=1, f1=479, foam=0.1,
              mat=mats['water_sea'], loc=(0, 200, 0))
full = L.box('SeaFull', (60000, 60000, 0.1), (0, 0, -0.3), mats['water_sea'], 0.0)
# markings: lane edges, dashed centre lines, crane rails, hatched safety zones (no text, no numbers)
yel = L.pbr('MAT_PaintYellow', (0.85, 0.62, 0.05), 0.6, var=0.2, grime=0.2, scale=0.5)
wht = L.pbr('MAT_PaintLine', (0.85, 0.85, 0.82), 0.6, var=0.2, grime=0.3, scale=0.5)
mb = P.MB()
for y in (-6.0, -30.0, -36.5):
    mb.box((0, y, QZ + 0.01), (700, 0.2, 0.02), yel)
for y in (-12.5 + 3.6, -12.5 - 3.6, -21.0):
    for x in range(-340, 340, 9):
        mb.box((x, y, QZ + 0.01), (4.5, 0.15, 0.02), wht)
for y in (-3.0, -33.0):
    mb.box((0, y, QZ + 0.03), (700, 0.35, 0.06), mats['steel'])
for cx in (-60, 0, 60):
    for y in (-3.0, -33.0):
        for k in range(8):
            mb.box((cx - 12 + k * 1.2, y + (2.0 if y < -10 else -2.0), QZ + 0.01), (0.25, 2.6, 0.02), yel,
                   rot=L.Euler((0, 0, D(35))).to_matrix())
# road from the gate through the yard
for x in (-47.5, -32.5):
    mb.box((x, -70, QZ + 0.01), (0.2, 70, 0.02), wht)
mb.obj('QUAY_Markings')
# bollards, fenders, light masts
bol = P.bollard_mesh()
fend = L.box_mesh('LIB_Fender', (2.2, 0.8, 2.6), 0.2, 2)
fend.materials.append(mats['rubber'])
for x in range(-330, 331, 15):
    L.obj('QUAY_Bollard', bol, None, (x, -0.9, QZ))
    L.obj('QUAY_Fender', fend, None, (x + 7, 0.45, 0.6))
for x in range(-300, 301, 60):
    P.light_mast(f'QUAY_Mast{x}', (x + 30, -38.5, QZ), 34)
    P.light_mast(f'YARD_Mast{x}', (x + 5, -150, QZ), 34)

# ---------------------------------------------------------------- yard: container blocks, reefer racks, RTGs
cmat = P.paint_attr('MAT_ContainerPaint', corrugate=60.0)
blocks = 0
for bx in (-370, -290, -210, -130, 30, 110, 190, 270):
    for by in (-62, -92, -122, -152, -182, -212, -242):
        hts = [[max(1, min(5, int(rnd.gauss(3.8, 1.0)))) for _ in range(7)] for _ in range(6)]
        reef = (0, 1, 2, 3, 4, 5, 6) if (bx == 30 and by in (-122, -152)) else ()
        P.container_block(f'YARD_Block{blocks}', (bx, by, QZ), 6, 7, lambda ix, iy, h=hts: h[ix][iy], cmat, rnd,
                          reefer_rows=reef)
        blocks += 1
for by in (-62, -92, -122, -152, -182):
    hts = [[max(1, min(5, int(rnd.gauss(3.6, 1.0)))) for _ in range(7)] for _ in range(3)]
    P.container_block(f'YARD_Block{blocks}', (-16, by, QZ), 3, 7, lambda ix, iy, h=hts: h[ix][iy], cmat, rnd)
    blocks += 1
# reefer plug racks: steel gantry walkways with cables over the two reefer blocks
rk = P.MB()
for by in (-122, -152):
    for ix in range(7):
        x = 30 - 6.5 + ix * (P.CL + 0.35)
        for iy in (-1.4, 18.0):
            rk.box((x, by + iy, QZ + 6.5), (0.35, 0.35, 13), mats['steel'])
        rk.box((x, by + 8.3, QZ + 12.8), (0.4, 20.0, 0.4), mats['steel'])
    for iy in range(7):
        y = by + iy * (P.CW + 0.35)
        rk.box((30 + 31, y, QZ + 11.2), (76, 0.9, 0.12), mats['steel'])
        for ix in range(6):
            x = 30 + ix * (P.CL + 0.35) - P.CL / 2 + 0.3
            rk.cyl((x, y + 0.6, QZ + 11.1), (x - 0.1, y + 0.6, QZ + 2.0 + (iy % 3) * 2.59), 0.04, mats['plastic_black'], 5)
            rk.sphere((x - 0.12, y + 0.5, QZ + 1.6 + (iy % 3) * 2.59), 0.06, mats['lamp_amber'] if ix % 2 else mats['lamp'], 6)
rk.obj('YARD_ReeferRacks')
rtgs = []
for i, (x, y) in enumerate(((140, -54), (-170, -84), (220, -144))):
    R = P.rtg(f'RTG{i}', (x, y + 8.5, QZ), 23.5, 19.0, D(90), mats=mats)
    rtgs.append(R)
# RTG0 lifts a box while we pass (trolley moves across, head rises)
rtg_box = P.MB()
P.add_container(rtg_box, (0, 0, 0), cmat, (0.06, 0.27, 0.45))
rb = rtg_box.obj('RTG0_Box', rtgs[0]['trolley'])
for f, z in ((1, 2.0), (90, 2.0), (150, 12.0), (240, 12.0), (330, 5.0), (479, 5.0)):
    rb.location = (0, 0, z)
    rb.keyframe_insert('location', frame=f)
for f, y in ((1, -6), (150, -6), (230, 6), (479, 6)):
    rtgs[0]['trolley'].location = (0, y, 0)
    rtgs[0]['trolley'].keyframe_insert('location', frame=f)
# straddle carriers moving +X along the apron lane (same direction as our truck after its turn)
for i, (x0, y) in enumerate(((-120, -24.0), (-200, -21.0))):
    sc = P.straddle(f'STRADDLE{i}', (x0, y, QZ), 0.0, mats=mats, rnd=rnd)
    P.drive(sc, [(x0, y), (x0 + 140, y)], 1, 479, ease=False, keystep=24)
    L.linear_keys(sc)

# ---------------------------------------------------------------- gate + truck queue
gate, barriers = P.gatehouse('GATE', (-40, -78, QZ), lanes=4, lane_w=4.5, mats=mats)
for i, b in enumerate(barriers):
    lane_x = -40 - 9 + i * 4.5 + 2.25
    up = 1 if abs(lane_x - (-42.25)) < 0.5 else 0
    for f, a in ((1, 0), (14, 0), (26, 85 if up else 0), (60, 85 if up else 0), (78, 0)):
        b.rotation_euler = (0, -D(a), 0)
        b.keyframe_insert('rotation_euler', frame=f)


def rig(name, color, with_box, reefer=False, loc=(0, 0, 0), rot_z=0.0, col=None):
    t, w1 = P.tractor(name, loc, rot_z, color=color, mats=mats)
    tr, w2 = P.skeletal_trailer(f'{name}_Trailer', t, mats=mats)
    box_o = None
    if with_box:
        mbx = P.MB()
        P.add_container(mbx, (0, 0, 0), cmat, P.REEFER_WHITE if reefer else (col or rnd.choice(P.CONTAINER_COLS)), reefer)
        box_o = mbx.obj(f'{name}_Box', tr, (-5.9, 0, 1.33))
    return t, w1 + w2, box_o


# the hero: white tractor + skeletal trailer + white reefer (the reefer is its own object, keyed per frame later)
hero, hero_w, _ = rig('HERO', (0.86, 0.86, 0.85), False, loc=(-42.25, -96, QZ), rot_z=D(90))
hero_trailer = bpy.data.objects['HERO_Trailer']
reefer = P.reefer_box('HERO_Reefer', None)
HERO_PATH = [(-42.25, -96), (-42.25, -74), (-42.25, -45), (-41.0, -26), (-34, -15.5), (-22, -12.5), (-8, -12.5), (1.5, -12.5)]
P.drive(hero, HERO_PATH, 1, 166, hero_w, ease=True, keystep=2)
for f in (166, 479):
    hero.keyframe_insert('location', frame=f)
# queue behind, all facing in, creeping forward one direction
for i in range(5):
    lane = -42.25 + (i % 2) * 4.5 - (4.5 if i == 4 else 0)
    y0 = -116 - i * 9
    t, w, _ = rig(f'QUEUE{i}', rnd.choice([(0.6, 0.06, 0.04), (0.06, 0.15, 0.4), (0.85, 0.85, 0.84), (0.1, 0.3, 0.14)]),
                  True, loc=(lane, y0, QZ), rot_z=D(90))
    P.drive(t, [(lane, y0), (lane, y0 + 26 + i * 2)], 1, 479, w, ease=True, keystep=6)
# trucks ahead in the yard and on the apron, same direction as the hero
for i, (path, f0, f1) in enumerate((([(-37.75, -60), (-37.75, -32), (-30, -19), (40, -18.5), (160, -18.5)], 1, 300),
                                    ([(-60, -9), (150, -9)], 1, 479),
                                    ([(-160, -26.5), (40, -26.5)], 1, 479))):
    t, w, _ = rig(f'AHEAD{i}', rnd.choice([(0.62, 0.07, 0.05), (0.85, 0.85, 0.84), (0.75, 0.55, 0.05)]), i != 1, loc=(*path[0], QZ))
    P.drive(t, path, f0, f1, w, ease=(i == 0), keystep=4)
# under cranes 1 and 3: waiting chassis
w1t, _, _ = rig('C1TRUCK', (0.6, 0.06, 0.04), False, loc=(-58.5, -12.5, QZ))
w3t, _, w3box = rig('C3TRUCK', (0.06, 0.15, 0.4), True, loc=(61.5, -20.5, QZ))

# ---------------------------------------------------------------- ship, cranes
SHIP_Y = 21.0
ship = P.container_ship('SHIP', (10.0, SHIP_Y, 0.0), L=230.0, B=32.0, deck=11.0, mats=mats, rnd=rnd, empty_slot=(4, 3),
                        tiers=7, bays=13)
slot_local = ship['slot'] - Vector((10.0, SHIP_Y, 0))  # relative to the ship root
cranes = []
for i, cx in enumerate((-60.0, 0.0, 60.0)):
    C = P.sts_crane(f'Crane_{i + 1}', (cx, -18.0, QZ), mats=mats)
    cranes.append(C)
C2 = cranes[1]
tro, head = C2['trolley'], C2['head']
GZ = C2['gz']


def ly(world_y):
    return world_y + 18.0


def lz_head(world_bottom_of_spreader):
    """head local z (relative to trolley at GZ) so the spreader's twistlocks sit at the given world z."""
    return world_bottom_of_spreader - (QZ + GZ) + 1.35


truck_box_top = QZ + 1.33 + 0.52 * 0 + P.CH  # trailer root z offset: chassis top ~1.33 above ground
slot_world = ship['slot']
keys_t = [(1, ly(30.0)), (132, ly(30.0)), (168, ly(-12.5)), (224, ly(-12.5)), (256, ly(slot_world.y)), (300, ly(slot_world.y)),
          (360, ly(-12.5)), (479, ly(-12.5))]
TOP = 36.0
keys_h = [(1, lz_head(TOP)), (132, lz_head(TOP)), (168, lz_head(truck_box_top + 4.0)), (190, lz_head(truck_box_top)),
          (195, lz_head(truck_box_top - 0.02)), (200, lz_head(truck_box_top)), (224, lz_head(TOP)), (256, lz_head(TOP)),
          (280, lz_head(slot_world.z + P.CH)), (284, lz_head(slot_world.z + P.CH)), (288, lz_head(slot_world.z + P.CH + 1.0)),
          (330, lz_head(TOP)), (479, lz_head(TOP))]
for f, y in keys_t:
    tro.location = (0, y, GZ)
    tro.keyframe_insert('location', frame=f)
for f, z in keys_h:
    head.location = (0, 0, z)
    head.keyframe_insert('location', frame=f)
L.smooth_keys(tro)
L.smooth_keys(head)
# sway <= 1 degree while trolleying sea-side
for f, a in ((224, 0), (236, 0.9), (248, -0.7), (256, 0.3), (268, 0)):
    head.rotation_euler = (D(a), 0, 0)
    head.keyframe_insert('rotation_euler', frame=f)
# cranes 1 and 3 mid-cycle, offset (simple lift/lower loops with their own box)
for C, phase, name in ((cranes[0], 0, 'C1BOX'), (cranes[2], 60, 'C3BOX')):
    t, h = C['trolley'], C['head']
    mbx = P.MB()
    P.add_container(mbx, (0, 0, 0), cmat, rnd.choice(P.CONTAINER_COLS))
    bxo = mbx.obj(name, h, (0, 0, -1.35 - P.CH))
    period = 200
    for k in range(-1, 4):
        f = 1 + k * period + phase
        seq = [(0, ly(-12.5), lz_head(TOP)), (40, ly(-12.5), lz_head(QZ + 1.33 + P.CH)), (60, ly(-12.5), lz_head(QZ + 1.33 + P.CH)),
               (100, ly(-12.5), lz_head(TOP)), (140, ly(24.0), lz_head(TOP)), (175, ly(24.0), lz_head(31.0)),
               (200, ly(-12.5), lz_head(TOP))]
        for df, y, z in seq:
            ff = f + df
            if -40 < ff < 270:
                t.location = (0, y, GZ)
                t.keyframe_insert('location', frame=ff)
                h.location = (0, 0, z)
                h.keyframe_insert('location', frame=ff)
    for ff in (282, 479):
        t.location = (0, ly(-12.5), GZ)
        t.keyframe_insert('location', frame=ff)
        h.location = (0, 0, lz_head(TOP))
        h.keyframe_insert('location', frame=ff)
    L.smooth_keys(t)
    L.smooth_keys(h)
# all booms go up once the box is set and before the ship moves off the berth: nothing can sweep through the hull
for k, C in enumerate(cranes):
    bh = C['boom']
    for f, a in ((1, 0.0), (292 + k * 4, 0.0), (334 + k * 4, 80.0), (479, 80.0)):
        bh.rotation_euler = (D(a), 0, 0)
        bh.keyframe_insert('rotation_euler', frame=f)
    L.smooth_keys(bh)

# ---------------------------------------------------------------- tugs, distant ships, mooring lines
tugs = []
for i, x in enumerate((-95.0, 112.0)):
    T = P.tug(f'TUG{i}', (x, SHIP_Y + 26, 0), D(90 if i else -90), mats=mats)
    tugs.append(T['root'])
for i, (x, y) in enumerate(((-900, 1600), (700, 2100), (1800, 1400))):
    far = P.MB()
    far.box((0, 0, 4), (180, 28, 14), L.pbr('MAT_FarHull', (0.05, 0.07, 0.1), 0.6))
    for k in range(8):
        far.box((-60 + k * 15, 0, 14), (13, 24, 6 + (k % 3) * 2.6), cmat, rnd.choice(P.CONTAINER_COLS))
    far.box((-80, 0, 20), (12, 20, 18), L.pbr('MAT_ShipWhite', (0.85, 0.86, 0.85), 0.4))
    o = far.obj(f'FARSHIP{i}', None, (x, y, 0))
    o.rotation_euler = (0, 0, rnd.uniform(-0.4, 0.4))
lines = []
for x in (-95, -80, 85, 105):
    for z_off in (0, 0.4):
        ln = L.tube(f'MOOR_{x}_{z_off}', [(x + 4, 0, 0), (x + 2, 2.5, -3.5 + z_off), (x, SHIP_Y - 16.5, -6.0)], 0.07,
                    mats['rope'], 6, loc=(0, -0.9, QZ + 7.9 + z_off))
        lines.append(ln)
        L.key_vis(ln, 1, 300)

# ---------------------------------------------------------------- workers (hi-vis, hard hats) on the quay
spots = [(-6, -6.5, 30), (8, -5.5, 200), (-14, -18, 80), (14, -28, 160), (4, -21.5, 250), (-30, -4.5, 10), (30, -5, 180),
         (-52, -7, 60), (52, -7, 220), (70, -28, 100), (-70, -28, 300), (0, -32, 90)]
for i, (x, y, rz) in enumerate(spots):
    w = L.person(f'WORKER{i}', 'port' if i % 3 else 'port_o', (x, y, QZ), D(rz), seed=i, mats=mats)
    if i < 3:
        L.walk(w, [(x, y), (x + 6 * math.cos(D(rz)), y + 6 * math.sin(D(rz)))], 1, 120)
    else:
        L.anim_poses(w, [(1, 'idle'), (100 + i * 7, 'point' if i % 4 == 0 else 'idle'), (200, 'idle')])

# ---------------------------------------------------------------- x-ship: lines off, tugs pull, ship sails out
shp = ship['root']
ship_keys = [(288, (10.0, SHIP_Y, 0), 0.0), (336, (14.0, SHIP_Y + 30, 0), D(4)), (380, (40.0, SHIP_Y + 59, 0), D(30)),
             (430, (95.0, SHIP_Y + 129, 0), D(50)), (479, (150.0, SHIP_Y + 204, 0), D(55))]
for f, p, r in ship_keys:
    shp.location = p
    shp.rotation_euler = (0, 0, r)
    shp.keyframe_insert('location', frame=f)
    shp.keyframe_insert('rotation_euler', frame=f)
shp.location = (10.0, SHIP_Y, 0)
shp.keyframe_insert('location', frame=1)
shp.rotation_euler = (0, 0, 0)
shp.keyframe_insert('rotation_euler', frame=1)
L.smooth_keys(shp)
for i, T in enumerate(tugs):
    x0 = T.location.x
    sgn = -1 if i == 0 else 1
    for f, (dx, dy) in ((1, (0, 0)), (288, (0, 0)), (336, (8 * sgn + 4, 30)), (370, (20 * sgn + 25, 60)),
                        (430, (110 * sgn + 40, 95)), (479, (200 * sgn + 60, 120))):
        T.location = (x0 + dx, SHIP_Y + 26 + dy, 0)
        T.keyframe_insert('location', frame=f)
    L.smooth_keys(T)
# wake: churned foam behind the stern widening into streaks + Kelvin arms; bow wave; tugs throw their own wash
wk = P.wake('SHIP_Wake', shp, -112.0, length=420.0, w0=20.0, w1=90.0, kelvin=False)
bw = P.wake('SHIP_BowWave', shp, 118.0, length=150.0, w0=6.0, w1=46.0, z=0.18, kelvin=False)
bw.scale = (0.6, 1, 1)
for f, sc in ((296, 0.02), (330, 0.35), (380, 0.85), (430, 1.0)):
    wk.scale = (sc, min(1.0, 0.4 + sc), 1)
    wk.keyframe_insert('scale', frame=f)
L.key_vis(wk, 296)
L.key_vis(bw, 320)
for i, T in enumerate(tugs):
    tw = P.wake(f'TUG{i}_Wake', T, -14.0, length=90.0, w0=4.0, w1=16.0, kelvin=False)
    for f, sc in ((290, 0.05), (320, 0.8), (479, 1.0)):
        tw.scale = (sc, 1, 1)
        tw.keyframe_insert('scale', frame=f)
    L.key_vis(tw, 290)

# ---------------------------------------------------------------- hero reefer: keyed per frame (trailer -> spreader -> ship)
LOCK, RELEASE = 195, 284
dg = bpy.context.evaluated_depsgraph_get()
for f in range(1, 480):
    s.frame_set(f)
    if f < LOCK:
        m = hero_trailer.matrix_world
        p = m @ Vector((-5.9, 0, 1.33))
        rz = hero.matrix_world.to_euler().z
    elif f < RELEASE:
        m = C2['spreader'].matrix_world
        p = m @ Vector((0, 0, -1.35 - P.CH))
        rz = m.to_euler().z
    else:
        m = shp.matrix_world
        p = m @ slot_local
        rz = m.to_euler().z
    reefer.location = p
    reefer.rotation_euler = (0, 0, rz)
    reefer.keyframe_insert('location', frame=f)
    reefer.keyframe_insert('rotation_euler', frame=f)
L.linear_keys(reefer)

# ---------------------------------------------------------------- coastline, breakwaters, city (seen from the top-down end)
def coast_y(x):
    """Shoreline (y of the waterline) east and west of the 700 m container quay: bays, a headland, beaches."""
    if abs(x) <= 360:
        return 0.0
    d = abs(x) - 360
    return -40 - 0.08 * d + 140 * math.sin(d / 900.0) * (1 if x > 0 else -0.6) - 60 * math.sin(d / 260.0)


land_tex = L.tex_pbr('MAT_LandScrub', 'aerial_grass_rock', 0.004, tint=(0.2, 0.24, 0.15), tint_amount=0.75, grime=0.3) \
    if os.path.isdir(os.path.join(L.TEXDIR, 'aerial_grass_rock')) else L.pbr('MAT_LandScrub', (0.3, 0.29, 0.2), 0.9, var=0.4,
                                                                               scale=0.003)
sand = L.pbr('MAT_Sand', (0.62, 0.55, 0.42), 0.9, var=0.2, scale=0.02)
roadm = L.pbr('MAT_RoadFar', (0.16, 0.16, 0.17), 0.9, var=0.15, scale=0.02)
lm = P.MB()
X0, X1, Y0 = -7000.0, 7000.0, -6000.0
xs = [X0 + i * 100.0 for i in range(141)]
for i in range(len(xs) - 1):
    xa, xb = xs[i], xs[i + 1]
    ya, yb = coast_y(xa), coast_y(xb)
    if abs(xa) < 350 and abs(xb) < 350:
        ya = yb = -310.0          # behind the container yard (land tucks under the yard box)
    v = [lm.bm.verts.new((xa, Y0, QZ - 0.6)), lm.bm.verts.new((xb, Y0, QZ - 0.6)), lm.bm.verts.new((xb, yb - 25, QZ - 0.6)),
         lm.bm.verts.new((xa, ya - 25, QZ - 0.6))]
    f = lm.bm.faces.new(v)
    f.material_index = lm.mi(land_tex)
    if not (abs(xa) < 350 and abs(xb) < 350):
        w = [lm.bm.verts.new((xa, ya - 25, QZ - 0.6)), lm.bm.verts.new((xb, yb - 25, QZ - 0.6)), lm.bm.verts.new((xb, yb, 0.4)),
             lm.bm.verts.new((xa, ya, 0.4))]
        f = lm.bm.faces.new(w)
        f.material_index = lm.mi(sand)
lm.obj('LAND_Coast')
# city: blocks of low-rise buildings between a road grid, denser near the harbour, a few taller ones; parks left open
cm = P.MB()
roof_cols = [(0.72, 0.7, 0.66), (0.55, 0.53, 0.5), (0.8, 0.78, 0.74), (0.5, 0.36, 0.3), (0.34, 0.37, 0.4), (0.62, 0.45, 0.36), (0.25, 0.33, 0.42)]
bmat = L.pbr('MAT_CityRoofs', (0.6, 0.58, 0.55), 0.85, var=0.3, scale=0.05, attr=None)
cityp = P.paint_attr('MAT_CityPaint', 0.85, grime=0.4, scale=0.05)
crnd = random.Random(21)
blk = 120.0
for bx in range(-55, 56):
    for by in range(1, 46):
        x = bx * blk
        y = -340 - by * blk if abs(x) < 420 else coast_y(x) - 60 - by * blk
        if y < Y0 + 200 or crnd.random() < 0.08:
            continue
        # main roads every 6 blocks: leave a wider gap
        for k in range(crnd.randint(3, 9)):
            w = crnd.uniform(18, 48)
            d = crnd.uniform(18, 48)
            px = x + crnd.uniform(-blk / 2 + w / 2 + 8, blk / 2 - w / 2 - 8)
            py = y + crnd.uniform(-blk / 2 + d / 2 + 8, blk / 2 - d / 2 - 8)
            near = max(0.0, 1.0 - abs(by) / 18.0)
            h = crnd.choice((6, 9, 12, 15, 18)) + (crnd.random() < 0.05) * crnd.uniform(25, 60) * (0.5 + near)
            cm.box((px, py, QZ + h / 2 - 0.5), (w, d, h), cityp, crnd.choice(roof_cols))
cm.obj('LAND_City')
rd = P.MB()
for bx in range(-55, 56, 3):
    rd.box((bx * blk + blk / 2, (Y0 - 340) / 2, QZ - 0.45), (10, abs(Y0) - 340, 0.2), roadm)
for by in range(1, 46, 3):
    rd.box((0, -340 - by * blk - blk / 2, QZ - 0.45), (14000, 12, 0.2), roadm)
rd.obj('LAND_Roads')
# rubble-mound breakwaters closing the basin; the harbour mouth opens to the north-east, on the ship's heading
rock = L.tex_pbr('MAT_Breakwater', 'rust_coarse_01', 0.02, tint=(0.42, 0.41, 0.39), tint_amount=0.9, grime=0.3) \
    if False else L.pbr('MAT_Breakwater', (0.42, 0.41, 0.39), 0.9, var=0.45, bump=0.8, scale=0.4, grime=0.4)
bwm = P.MB()
for pts in (((-450, 0), (-450, 640), (240, 780)), ((720, -20), (720, 340), (580, 440))):
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        a, b = Vector((xa, ya, 0)), Vector((xb, yb, 0))
        n = int((b - a).length / 6)
        for k in range(n):
            c = a + (b - a) * (k / n)
            for j in range(3):
                off = Vector((crnd.uniform(-9, 9), crnd.uniform(-9, 9), 0))
                bwm.box(c + off + Vector((0, 0, crnd.uniform(0.5, 3.5))), (crnd.uniform(4, 9), crnd.uniform(4, 9), crnd.uniform(3, 6)),
                        rock, rot=L.Euler((crnd.random(), crnd.random(), crnd.random())).to_matrix())
        bwm.box((a + b) / 2 + Vector((0, 0, 4.2)), ((b - a).length + 6, 7, 1.2), conc,
                rot=L.Euler((0, 0, math.atan2(b.y - a.y, b.x - a.x))).to_matrix())
bwm.obj('LAND_Breakwaters')
# other berths in the basin: a bulk ship and two small coasters along the west breakwater's inner side
for i, (x, y, r, Ls) in enumerate(((-400, 300, D(90), 190), (-380, 520, D(88), 90), (-200, 690, D(12), 110))):
    far = P.MB()
    far.box((0, 0, 4), (Ls, Ls * 0.15, 12), L.pbr('MAT_BulkHull', (0.32, 0.08, 0.06), 0.7, grime=0.5))
    far.box((0, 0, 10.3), (Ls * 0.92, Ls * 0.12, 0.6), L.pbr('MAT_BulkDeck', (0.3, 0.31, 0.3), 0.8, grime=0.6))
    for k in range(int(Ls / 25)):
        far.box((-Ls * 0.38 + k * 25, 0, 11.5), (16, Ls * 0.1, 1.8), L.pbr('MAT_Hatch', (0.18, 0.25, 0.3), 0.6, grime=0.5))
    far.box((-Ls * 0.42, 0, 18), (10, Ls * 0.12, 16), L.pbr('MAT_ShipWhite', (0.85, 0.86, 0.85), 0.4))
    o = far.obj(f'BASIN_Ship{i}', None, (x, y, 0))
    o.rotation_euler = (0, 0, r)

# ---------------------------------------------------------------- camera
cam = L.camera('Camera', 30, (-40, -92, 12), (-40, -55, 2))
cam.data.clip_end = 30000
# keep depth precision when the camera climbs to the top-down end (land vs sea planes would z-fight otherwise)
for f, cs in ((1, 0.1), (288, 0.1), (336, 20.0), (420, 60.0), (479, 200.0)):
    cam.data.clip_start = cs
    cam.data.keyframe_insert('clip_start', frame=f)
cam.data.dof.aperture_fstop = 8.0
keys = [
    (1, (-40.0, -128.0, 15.0), (-42.0, -86.0, 3.0), 28),
    (40, (-29.0, -100.0, 13.0), (-42.0, -68.0, 3.0), 28),
    (72, (-48.0, -74.0, 18.5), (-41.0, -46.0, 3.0), 28),
    (132, (-50.0, -42.0, 21.0), (-12.0, -14.0, 6.0), 26),
    (168, (-14.0, -27.0, 5.0), (1.5, -12.5, 6.5), 30),
    (196, (-12.0, -28.0, 8.0), (1.5, -12.5, 6.2), 30),
    (224, (-14.0, -30.0, 18.0), (2.0, -4.0, 30.0), 28),
    (256, (-45.0, -80.0, 70.0), (2.0, 12.0, 22.0), 26),
    (288, (-50.0, -115.0, 230.0), (5.0, 18.0, 10.0), 30),
    (336, (14.0, SHIP_Y + 28.0, 330.0), (14.0, SHIP_Y + 30.0, 0.0), 28),
    (380, (45.0, SHIP_Y + 110.0, 400.0), (45.0, SHIP_Y + 112.0, 0.0), 28),
    (420, (95.0, SHIP_Y + 200.0, 720.0), (95.0, SHIP_Y + 202.0, 0.0), 28),
    (479, (150.0, SHIP_Y + 120.0, 2600.0), (150.0, SHIP_Y + 122.0, 0.0), 28),
]
L.cam_path(cam, keys, focus=[(1, 40.0), (168, 21.0), (196, 15.5), (224, 40.0), (288, 95.0), (336, 330.0), (479, 2600.0)])
cam.data.dof.use_dof = True
# the top-down part: hide the harbour detail patch once the camera is high (far plane = same deep blue everywhere)
L.key_vis(sea, 1, 340)
s.camera = cam

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
sys.argv = [sys.argv[0], '--', 'port', '1', '479', 'exterior']
exec(compile(open(os.path.join(HERE, 'render_settings.py')).read(), 'render_settings.py', 'exec'))
print('BUILT', OUT, len(bpy.data.objects), 'objects')
