"""Port tractors to Indian right-hand drive (#258): run on port_v3.2.blend, saves port_v3.3.blend.
  Blender -b assets-src/blender/port_v3.2.blend --python blender/port_rhd.py -- assets-src/blender/port_v3.3.blend
Every tractor (<ROOT>_Body + <ROOT>_Driver, +X forward) gets: the driver moved to the right-hand seat (-Y), the cab glass
split into its own see-through object, the cab hollowed with real window openings, and a dash, seats and a steering
wheel on the right, so the driver reads through the glass at the wheel on the right."""
import math
import os
import sys
import bmesh
import bpy
from mathutils import Vector, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skhuman as H     # noqa: E402

SIT = {'thigh.L': (88, -4, 0), 'thigh.R': (88, 4, 0), 'shin.L': (-84, 0, 0), 'shin.R': (-84, 0, 0),
       'foot.L': (6, 0, 0), 'foot.R': (6, 0, 0), 'spine': (-6, 0, 0), 'chest': (4, 0, 0),
       'upperarm.L': (48, -10, 0), 'upperarm.R': (48, -10, 0), 'forearm.L': (40, 0, 0), 'forearm.R': (40, 0, 0)}

CAB = ((3.0, 4.88), (-1.12, 1.12), (1.3, 3.45))       # inner cavity of the tractor cab, body-local (x, y, z ranges)


def glass_mat():
    m = bpy.data.materials.get('MAT_CabGlassClear')
    if m:
        return m
    m = bpy.data.materials.new('MAT_CabGlassClear')
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.1, 0.12, 0.13, 1)
    p.inputs['Roughness'].default_value = 0.05
    p.inputs['Alpha'].default_value = 0.3
    p.inputs['Coat Weight'].default_value = 1.0
    m.surface_render_method = 'BLENDED'
    return m


def dark_mat():
    m = bpy.data.materials.get('MAT_CabInterior')
    if m:
        return m
    m = bpy.data.materials.new('MAT_CabInterior')
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.045, 0.05, 0.055, 1)
    p.inputs['Roughness'].default_value = 0.6
    return m


def box(bm, c, s, rot=None):
    vs = bmesh.ops.create_cube(bm, size=1)['verts']
    for v in vs:
        v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2]))
        if rot:
            v.co = rot.to_matrix() @ v.co
        v.co += Vector(c)


def cyl(bm, a, b, r, seg=10):
    a, b = Vector(a), Vector(b)
    d = b - a
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    q = d.normalized().to_track_quat('Z', 'Y')
    for v in res['verts']:
        v.co = q @ v.co + (a + b) / 2


def mesh_obj(name, bm, mat, parent):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    for c in parent.users_collection:
        c.objects.link(o)
    o.parent = parent
    return o


def convert(root):
    body = bpy.data.objects[root + '_Body']
    drv = bpy.data.objects[root + '_Driver']
    me = body.data
    paint = next(sl.material for sl in body.material_slots if sl.material and sl.material.name.startswith('MAT_Tractor'))
    drop = {i for i, sl in enumerate(body.material_slots)
            if sl.material and sl.material.name.startswith(('MAT_Tractor', 'MAT_CabGlass'))}
    # 1. the solid cab shell (paint + glass faces) goes; a panelled cab with real window openings replaces it
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in drop], context='FACES')
    bm.to_mesh(me)
    bm.free()
    x0, x1, yw, z0, zw0, zw1, z1 = 2.85, 5.0, 1.24, 0.85, 2.08, 3.02, 3.6
    t = 0.06
    sh = bmesh.new()
    box(sh, (x0 + t / 2, 0, (z0 + z1) / 2), (t, 2 * yw, z1 - z0))                       # back wall
    box(sh, ((x0 + x1) / 2, 0, z1 - t / 2), (x1 - x0, 2 * yw, t))                       # roof
    box(sh, (x1 - t / 2, 0, (z0 + zw0) / 2), (t, 2 * yw, zw0 - z0))                     # front below the screen
    box(sh, (x1 - t / 2, 0, (zw1 + z1) / 2), (t, 2 * yw, z1 - zw1))                     # header over the screen
    box(sh, (x1 - t / 2, 0, (zw0 + zw1) / 2), (t, 0.08, zw1 - zw0))                     # centre pillar
    for sy in (-1, 1):
        box(sh, (x1 - t / 2, sy * (yw - 0.07), (zw0 + zw1) / 2), (t, 0.14, zw1 - zw0))  # A pillars
        box(sh, ((x0 + x1) / 2, sy * (yw - t / 2), (z0 + zw0) / 2), (x1 - x0, t, zw0 - z0))   # lower side / door
        box(sh, ((x0 + x1) / 2, sy * (yw - t / 2), (zw1 + z1) / 2), (x1 - x0, t, z1 - zw1))   # over the side window
        box(sh, ((x0 + 3.65) / 2, sy * (yw - t / 2), (zw0 + zw1) / 2), (3.65 - x0, t, zw1 - zw0))   # behind it
        box(sh, (3.62, sy * (yw + 0.005), 1.47), (0.012, 0.012, 1.2))                   # door seam
    box(sh, ((x0 + x1) / 2, 0, 1.31), (x1 - x0, 2 * yw, 0.04))                          # cab floor
    mesh_obj(root + '_CabShell', sh, paint, body)
    gl = bmesh.new()
    for sy in (-1, 1):
        box(gl, (x1 - t / 2, sy * 0.58, (zw0 + zw1) / 2), (0.012, 1.0, zw1 - zw0 + 0.04))   # windscreen halves
        box(gl, ((3.65 + x1 - t) / 2, sy * (yw - t / 2), (zw0 + zw1) / 2), (x1 - t - 3.65 + 0.04, 0.012, zw1 - zw0 + 0.04))
    mesh_obj(root + '_CabGlass', gl, glass_mat(), body)
    # 2. right-hand-drive interior: dash, binnacle, seats, steering wheel and column on the right (-Y)
    ib = bmesh.new()
    box(ib, (4.78, 0, 1.95), (0.32, 2.3, 0.26))
    box(ib, (4.6, -0.55, 2.14), (0.12, 0.46, 0.1), Euler((0, 0.5, 0)))
    for sy in (-0.55, 0.55):
        box(ib, (3.74, sy, 1.62), (0.5, 0.52, 0.14))
        box(ib, (3.44, sy, 2.1), (0.12, 0.5, 0.8), Euler((0, -0.12, 0)))
        box(ib, (3.38, sy, 2.6), (0.1, 0.28, 0.2))
        box(ib, (3.74, sy, 1.45), (0.34, 0.34, 0.24))
    wc = Vector((4.3, -0.55, 2.16))
    tilt = Euler((0, math.radians(-50), 0)).to_matrix()
    u, v, nrm = tilt @ Vector((0, 1, 0)), tilt @ Vector((0, 0, 1)), tilt @ Vector((1, 0, 0))
    ring = [wc + u * (0.22 * math.cos(2 * math.pi * k / 24)) + v * (0.22 * math.sin(2 * math.pi * k / 24))
            for k in range(24)]
    for k in range(24):
        cyl(ib, ring[k], ring[(k + 1) % 24], 0.017, 6)
    for a in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6):
        cyl(ib, wc, wc + u * (0.22 * math.cos(a)) + v * (0.22 * math.sin(a)), 0.011, 6)
    cyl(ib, wc - nrm * 0.02, wc + nrm * 0.05, 0.045, 14)
    cyl(ib, wc + nrm * 0.05, (4.65, -0.55, 1.95), 0.032, 8)
    mesh_obj(root + '_CabInterior', ib, dark_mat(), body)
    # 3. a fresh library driver (the inherited one never deformed: a rest-pose figure through the floor) sits on the
    # right-hand seat, hips 0.903 m over the rig origin, hands on the wheel at ten-to-two
    for o in [drv] + list(drv.children_recursive):
        o.hide_render = o.hide_viewport = True
    nd = H.person(root + '_DriverRHD', 'driver', 'male', coll=body.users_collection[0], seed=hash(root) % 97)
    nd.parent = body
    nd.location = (3.8, -0.55, 1.72 - 0.903)
    nd.rotation_euler = (0, 0, math.radians(90))
    H.set_pose(nd, SIT, 1)
    for sd, a in (('L', math.radians(20)), ('R', math.radians(160))):     # +Y is the driver's left
        e = bpy.data.objects.new('%s_Grip%s' % (root, sd), None)
        body.users_collection[0].objects.link(e)
        e.parent = body
        e.location = wc + u * (0.22 * math.cos(a)) + v * (0.22 * math.sin(a))
        c = nd.pose.bones['forearm.' + sd].constraints.new('IK')
        c.target, c.chain_count, c.use_tail = e, 2, True
        H.grip(nd, sd, curl=0.85)
    return root


H.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets-src/blender/humans.blend'))
roots = sorted(o.name[:-len('_Driver')] for o in bpy.data.objects
               if o.name.endswith('_Driver') and bpy.data.objects.get(o.name[:-len('_Driver')] + '_Body'))
print('RHD', [convert(r) for r in roots])
# the camera skimmed 2-5 m over the gate canopy (f40-58) and the blue roof filled the frame: lift it 9 m there
cam = bpy.data.objects['Camera']
for f, dz in ((26, 0.0), (42, 9.0), (58, 9.0), (76, 0.0)):
    cam.delta_location = (0, 0, dz)
    cam.keyframe_insert('delta_location', index=2, frame=f)
out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if out:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(out))
    print('OUT', out)
