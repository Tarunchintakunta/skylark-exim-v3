"""Hard-rule checks on a built scene (#255-#259). Prints one PASS/FAIL line per rule and exits 1 on any FAIL.
  Blender -b <scene>.blend --python blender/rule_check.py -- <truck|intake|cold|port|sea|hero>
Rules: right-hand drive (driver and wheel on the right of every cab, the driver rendered), the plant truck never past
the dock wall, the whole plant truck in frame while it arrives and reverses, steel only for crates/racks/boxes, white
coats on every plant worker, and nothing but the ship and its wake at sea."""
import re
import sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view as w2c

kind = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'truck'
s = bpy.context.scene
fails = []


def check(name, ok, detail=''):
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        fails.append(name)


def shown(o):
    return not o.hide_render and all(not c.hide_render for c in o.users_collection)


def frames(step=4):
    return range(s.frame_start, s.frame_end + 1, step)


def local(o, root):
    return root.matrix_world.inverted() @ o.matrix_world.translation


# -- right-hand drive: every rendered driver sits right of the cab centre line (local -Y, +X forward)
if kind in ('truck', 'intake', 'port'):
    pairs = []
    if kind == 'port':
        for o in bpy.data.objects:
            if o.name.endswith('_DriverRHD'):
                pairs.append((o, o.parent, bpy.data.objects.get(o.name[:-len('_DriverRHD')] + '_CabInterior')))
            if o.name.endswith('_Driver') and o.type == 'ARMATURE':
                check('old LHD driver hidden ' + o.name, not shown(o))
    else:
        d = bpy.data.objects.get('HUM_Driver')
        root = bpy.data.objects.get('TRK_RigidReefer')
        pairs.append((d, root, bpy.data.objects.get('TRK_RigidReefer_SteeringWheel')))
    for drv, root, wheel in pairs:
        y = local(drv, root).y
        check('driver on the right ' + drv.name, y < -0.3 and shown(drv), 'local y %.2f' % y)
        if wheel is not None:
            me = wheel.data
            ys = sorted(v.co.y for v in me.vertices)
            wy = ys[len(ys) // 2]                 # the interior mesh holds both seats: the wheel ring is right of 0
            check('steering wheel on the right ' + wheel.name, wy < 0, 'median y %.2f' % wy)

# -- the plant truck: never past the dock wall (y = 0), whole truck in frame while it arrives and reverses
if kind == 'truck':
    root = bpy.data.objects['TRK_RigidReefer']
    meshes = [o for o in root.children_recursive if o.type == 'MESH' and shown(o)]
    worst_y, worst_m = -9.0, 1.0
    for f in frames(2):
        s.frame_set(f)
        for o in meshes:
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                worst_y = max(worst_y, w.y)
                if f <= 212:
                    v = w2c(s, s.camera, w)
                    worst_m = min(worst_m, v.x, v.y, 1 - v.x, 1 - v.y)
    check('truck stays outside the building (dock wall y=0)', worst_y <= 0.0, 'max y %.2f' % worst_y)
    check('whole truck in frame f1-212', worst_m >= 0.0, 'min margin %.3f' % worst_m)

# -- steel only: no plastic crate, cardboard carton or kraft box rendered in the plant
if kind in ('truck', 'intake', 'cold'):
    bad = set()
    for o in s.objects:
        if o.type != 'MESH' or not shown(o):
            continue
        for sl in o.material_slots:
            m = sl.material
            if m and re.search(r'crate_(blue|red|white|yellow)|Kraft|HDPE|LIB_Crate|Plastic', m.name) and \
                    re.search(r'Crate|Carton|Box|Rack|Pallet', o.name):
                bad.add('%s:%s' % (o.name, m.name))
    check('crates, racks and boxes are steel', not bad, ', '.join(sorted(bad)[:8]))
    racks = [bpy.data.objects.get(n) for n in ('IN_RackUprights', 'IN_RackBeams', 'IN_ColdPalletWood')]
    check('cold-store racks and pallets galvanised', all(r and r.material_slots[0].material.name == 'PL_Galv' for r in racks))
    m = bpy.data.materials.get('HUM_WhiteCotton')
    cols = [e.color for n in m.node_tree.nodes if n.type == 'VALTORGB' for e in n.color_ramp.elements] if m else []
    check('every coat white', bool(cols) and all(min(c[:3]) > 0.6 for c in cols), '%d palette entries' % len(cols))
    outfits = {o.data.name for o in s.objects if o.type == 'MESH' and o.name.startswith('HUM_') and shown(o)}
    wrong = sorted(n for n in outfits if re.search(r'_(plant|coldstore)$', n))
    check('plant workers in white coats with hairnet, mask, blue gloves', not wrong, ', '.join(wrong[:5]))

# -- at sea: the ship and its wake on open sea, nothing else
if kind == 'sea':
    extra = sorted(o.name for o in s.objects if shown(o) and o.type == 'MESH' and o.name != 'SeaFull' and
                   not (o.parent and (o.parent.name == 'SHIP' or o.parent.name.startswith('SHIP'))) and o.name != 'SHIP')
    check('only the ship and its wake at sea', not extra, ', '.join(extra[:8]))
    check('wake rendered', shown(bpy.data.objects['SHIP_Wake']))

print('RULES', kind, 'FAIL' if fails else 'PASS', len(fails))
sys.exit(1 if fails else 0)
