"""Loading beat keyframes L1-L4 (replaces the broken harbour loading clip): the plant dock of truck-reverse.blend at
frame 288, the RHD reefer backed flush to bay 2 (x = 9.2) with its door rolled up, leveller lip on the bed. One locked
camera for all four; only the worker, the jack, the two pallets, the door, the leveller lip and (L4) the truck move.
  STILL_ID=255 LOAD_KEY=L1 STILL_ENGINE=cycles Blender -b truck-reverse.blend --python blender/still_settings.py \
      --python blender/load_beat.py -o <out>/L1- -F PNG -f 288
L1  loader behind a hand pallet jack, a shrink-wrapped pallet of plain white cartons on the forks at the dock edge;
    truck empty; the second wrapped pallet waits on the dock floor
L2  pallet 1 at the front wall of the truck; the loader walks back out pulling the empty jack; pallet 2 still waiting
L3  pallet 2 inside too; door down and latched; leveller lip stowed; loader standing clear, jack parked beside him
L4  as L3, the truck pulled 4 m forward off the dock; the dock seal empty"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skhuman as H
import skpbr as P
import still_fixes
from sktruck import Part, BZ, _fcurves

KEY = os.environ.get('LOAD_KEY', 'L1')
FRAME = 288
DZ = 1.2                      # dock floor
BX = 9.2                      # bay centre line
CAM = ((12.4, 7.6, 2.55), (8.4, -1.6, 1.85), 26)     # inside the plant, right of the bay: opening + open rear + floor
s = bpy.context.scene
C = s.collection
H.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets-src/blender/humans.blend'))
s.frame_set(FRAME)


def mat(name, col, rough, metal=0.0, **kw):
    return bpy.data.materials.get(name) or P.plain(name, col, rough, metal, **kw)


def pallet(name, loc):
    """Wooden export pallet (1.0 m across, 1.2 m long: the jack's forks enter the 1.0 m end) with 3 x 4 x 4 plain white
    cartons, wrapped round the sides in stretch film."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    root.location = loc
    w = Part()
    for x in (-0.45, 0.0, 0.45):
        w.box((x, 0, 0.06), (0.1, 1.2, 0.075))                         # blocks + stringers, along the fork entry
    for y in (-0.55, -0.27, 0.0, 0.27, 0.55):
        w.box((0, y, 0.122), (1.0, 0.1, 0.022))                        # top deck boards
    for x in (-0.45, 0.45):
        w.box((x, 0, 0.011), (0.1, 1.2, 0.022))                        # bottom boards under the outer runners
    w.make(name + '_Wood', mat('LOAD_PalletWood', (0.42, 0.33, 0.22), 0.8), root, bevel=0.004, coll=C)
    c = Part()
    for ix in range(3):
        for iy in range(4):
            for iz in range(4):
                c.box((-0.33 + ix * 0.33, -0.45 + iy * 0.3, 0.27 + iz * 0.26), (0.325, 0.295, 0.255))
    c.make(name + '_Cartons', mat('LOAD_WhiteCarton', (0.86, 0.86, 0.84), 0.62), root, bevel=0.006, coll=C)
    f = Part()
    f.box((0, 0, 0.66), (1.015, 1.215, 1.02))
    fo = f.make(name + '_Film', mat('LOAD_StretchFilm', (0.92, 0.95, 0.97), 0.08, alpha=0.42, coat=1.0), root, coll=C)
    me = fo.data                                                        # sides only: the top stays open
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[fa for fa in bm.faces if abs(fa.normal.z) > 0.9], context='FACES')
    bm.to_mesh(me)
    bm.free()
    return root


def jack(name):
    """Hand pallet jack, own frame: tiller grip at y = +0.04, forks ahead toward -Y (as plant_yard.pallet_jack),
    painted yellow; the root sits on the floor under the pump."""
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    yel = mat('LOAD_JackYellow', (0.75, 0.52, 0.03), 0.42, coat=0.2)
    p = Part()
    p.cyl((0, 0.02, 1.0), (0, -0.22, 0.25), 0.02, 8)                      # tiller
    p.cyl((-0.13, 0.04, 1.0), (0.13, 0.04, 1.0), 0.018, 8)               # grip
    p.box((0, -0.3, 0.2), (0.36, 0.2, 0.2))                              # pump body
    for sx in (-0.27, 0.27):
        p.box((sx, -0.95, 0.065), (0.16, 1.15, 0.055))                   # forks
    p.make(name + '_Frame', yel, root, bevel=0.008, coll=C)
    p = Part()
    for sx in (-0.08, 0.08):
        p.cyl((sx - 0.03, -0.3, 0.09), (sx + 0.03, -0.3, 0.09), 0.09, 14)
    for sx in (-0.27, 0.27):
        p.cyl((sx - 0.05, -1.45, 0.035), (sx + 0.05, -1.45, 0.035), 0.035, 10)
    p.make(name + '_Wheels', mat('LOAD_Rubber', (0.03, 0.03, 0.03), 0.7), root, coll=C)
    return root


def white_gear(w):
    """Plain white hygiene gear on the loader (the 'plant' outfit's coat / apron palettes go white; gloves stay blue,
    boots white), on copies of his materials only."""
    mo = next(c for c in w.children if c.type == 'MESH')
    for sl in mo.material_slots:
        m = sl.material
        if m is None or not m.name.startswith(('HUM_WhiteCotton', 'HUM_WhitePVC', 'HUM_WhiteBoot')):
            continue
        m = m.copy()
        for n in m.node_tree.nodes:
            if n.type == 'VALTORGB':
                for e in n.color_ramp.elements:
                    e.color = (0.80, 0.82, 0.82, 1) if 'PVC' in m.name else (0.62, 0.63, 0.62, 1)
        if 'Boot' in m.name:
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            for lk in list(pb.inputs['Base Color'].links):
                m.node_tree.links.remove(lk)
            pb.inputs['Base Color'].default_value = (0.78, 0.79, 0.78, 1)
        sl.link = 'OBJECT'
        sl.material = m


def place(o, x, y, z, rz=0.0):
    o.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, 'Z')


def ground(w):
    """Lowest sole vertex onto the dock floor."""
    bpy.context.view_layer.update()
    mo = next(c for c in w.children if c.type == 'MESH')
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mo.evaluated_get(dg)
    me = ev.to_mesh()
    zmin = min((mo.matrix_world @ v.co).z for v in me.vertices)
    ev.to_mesh_clear()
    w.location.z += DZ - zmin


def hand_on(w, side, jk, inf=1.0):
    """Glove round the tiller grip, fingers over the top and down the far side."""
    sx = -0.09 if side == 'R' else 0.09
    if w.rotation_euler.z > 1.0:                     # walking away from the jack: the near end of the grip
        sx = -sx
    H.grip(w, side, curl=0.9)
    H.wrap_hand(w, side, jk, (sx, 0.04, 1.02), (0, -0.7, -0.7) if w.rotation_euler.z < 1.0 else (0, 0.7, -0.7),
                (0, 0, -1), [(1, inf)], C)


# --- the empty truck: cargo out, the rest of the dock as in the #255 still ----------------------------------------
truck = bpy.data.objects['TRK_RigidReefer']
for o in truck.children_recursive:
    if 'Cargo' in o.name:
        o.hide_render = o.hide_viewport = True
for n in ('PL_WaitTrolley1', 'PL_WaitTrolley2'):                     # the empty carts would sit in the jack's path
    o = bpy.data.objects.get(n)
    if o is not None:
        for c in [o] + list(o.children_recursive):
            c.hide_render = c.hide_viewport = True

floor_in = 1.312                                                       # top of the truck's aluminium floor
p1 = pallet('LOAD_Pallet1', (0, 0, 0))
p2 = pallet('LOAD_Pallet2', (0, 0, 0))
jk = jack('LOAD_Jack')
w = H.person('HUM_Loader', 'plant_coat', 'male', coll=C, seed=733)
white_gear(w)
FRONT, PX = -6.62, 8.62                                                # pallet 1 at the box front wall, on the far (left) side
WAIT = (8.15, 4.7)                                                     # pallet 2 on the dock floor, left of the bay

if KEY == 'L1':
    place(jk, BX, 2.25, DZ)
    place(p1, BX, 2.25 - 0.95, DZ + 0.03)                              # forks raised: pallet 3 cm off the floor
    place(p2, *WAIT, DZ)
    w.location, w.rotation_euler = (BX, 2.25 + 0.62, DZ), (0, 0, 0)    # behind the tiller, facing the truck
    H.set_pose(w, {'spine': (14, 0, 0), 'chest': (4, 0, 0), 'head': (-6, 0, 0),
                   'thigh.L': (8, -3, 0), 'shin.L': (-4, 0, 0), 'foot.L': (-4, 0, 0),
                   'thigh.R': (-6, -3, 0), 'shin.R': (-2, 0, 0), 'foot.R': (8, 0, 0)})     # push stance, both soles flat
    hand_on(w, 'L', jk)
    hand_on(w, 'R', jk)
elif KEY == 'L2':
    place(jk, 9.0, 2.45, DZ)
    place(p1, PX, FRONT, floor_in)
    place(p2, *WAIT, DZ)
    w.location, w.rotation_euler = (9.08, 2.45 + 0.52, DZ), (0, 0, math.pi)   # walking out, toward the hall
    H.set_pose(w, {'spine': (4, 0, 0), 'head': (4, 0, 0),
                   'thigh.L': (9, -3, 0), 'shin.L': (-4, 0, 0), 'foot.L': (-5, 0, 0),
                   'thigh.R': (-7, -3, 0), 'shin.R': (-3, 0, 0), 'foot.R': (10, 0, 0),
                   'upperarm.L': (-10, -18, 0), 'forearm.L': (14, 0, 0)})     # mid-stride, both soles on the floor
    hand_on(w, 'R', jk)                                                # right hand trails behind on the grip
else:                                                                  # L3 / L4
    place(jk, 12.2, 1.0, DZ, math.pi)                                 # parked by the wall, forks toward the hall
    place(p1, PX, FRONT, floor_in)
    place(p2, PX + 1.12, FRONT, floor_in)                              # beside it, two across
    w.location, w.rotation_euler = (11.1, 2.5, DZ), (0, 0, math.radians(-150))     # clear of the bay, watching
    st = H.stand(seed=5)                                               # relaxed arms; both soles flat on the floor
    st.update({'hips': (0, 0, 0), 'thigh.L': (2, -4, 0), 'shin.L': (-3, 0, 0), 'foot.L': (1, 0, 0),
               'thigh.R': (3, -4, 3), 'shin.R': (-4, 0, 0), 'foot.R': (1, 0, 0)})
    H.set_pose(w, st)
    for d in ('TRK_DoorL', 'TRK_DoorR'):                               # door down and latched
        o = bpy.data.objects[d]
        for fc in _fcurves(o.animation_data.action):
            fc.mute = True
        o.scale = (1, 1, 1)
        o.location.z = BZ + 2.55 / 2
    for n in ('STILL_LevellerPlate', 'STILL_LevellerGuard', 'STILL_LevellerGuard.001'):   # leveller stowed: lip off
        o = bpy.data.objects.get(n)                                    # the bed, deck flush with the dock floor
        if o is not None:
            o.hide_render = o.hide_viewport = True
    if KEY == 'L4':
        for fc in _fcurves(truck.animation_data.action):
            if fc.data_path == 'location':
                fc.mute = True
        truck.location.y -= 4.0                                       # pulled forward (cab toward -Y) off the dock
s.frame_set(FRAME)
ground(w)
s.frame_set(FRAME)

# the locked camera, shared by all four keyframes
loc, tgt, lens = CAM
cam = bpy.data.objects.new('LOAD_Camera', bpy.data.cameras.new('LOAD_Camera'))
C.objects.link(cam)
cam.data.lens, cam.data.clip_start, cam.data.clip_end = lens, 0.1, 400
cam.data.dof.use_dof = False
cam.location = Vector(loc)
cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
s.camera = cam
print('LOAD', KEY, 'loader at', tuple(round(v, 2) for v in w.location))
