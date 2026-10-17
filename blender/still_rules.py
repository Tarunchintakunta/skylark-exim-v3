"""Rule checklist for one composition still (#255-#260, #246).
  Blender -b <scene>.blend --python blender/still_rules.py -- <id> <frame> <out.json>
Each rule is PASS, FAIL or n/a (the rule does not apply to that scene), evaluated at the still's own frame."""
import json
import re
import sys
import bpy
import os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import still_fixes
still_fixes.apply_all()

sid, frame, out = sys.argv[sys.argv.index('--') + 1:][:3]
s = bpy.context.scene
s.frame_set(int(frame))
res = {}


def shown(o):
    return not o.hide_render and all(not c.hide_render for c in o.users_collection)


def put(rule, ok, detail=''):
    res[rule] = {'status': 'n/a' if ok is None else ('PASS' if ok else 'FAIL'), 'detail': detail}


# RHD: every rendered driver right of its cab's centre line, steering wheel too
drivers = []
for o in bpy.data.objects:
    if o.name.endswith('_DriverRHD') and shown(o):
        drivers.append((o, o.parent))
    elif o.name == 'HUM_Driver' and shown(o):
        drivers.append((o, bpy.data.objects['TRK_RigidReefer']))
ys = [(root.matrix_world.inverted() @ d.matrix_world.translation).y for d, root in drivers]
put('RHD: driver and wheel on the right', (all(y < -0.3 for y in ys) if ys else None), '%d driver(s), local y %s' % (len(ys), ', '.join('%.2f' % y for y in ys[:4])) if ys else 'no truck cab in this scene')

# truck outside the plant: no vertex of the plant truck past the dock wall (y = 0)
root = bpy.data.objects.get('TRK_RigidReefer')
if root is not None:
    top = max((o.matrix_world @ Vector(c)).y for o in root.children_recursive if o.type == 'MESH' and shown(o) and 'Cargo' not in o.name and not re.search(r'Crate|Carton', o.name) for c in o.bound_box)
    put('truck outside the plant', top <= 0.0, 'truck body rearmost y %.2f m (dock wall y = 0); cargo crates being unloaded are not the truck' % top)
else:
    put('truck outside the plant', None, 'no plant truck in this scene')

# steel only
bad = set()
n_steel = 0
for o in s.objects:
    if o.type != 'MESH' or not shown(o) or not re.search(r'Crate|Carton|Box|Rack|Pallet|Trolley', o.name):
        continue
    n_steel += 1
    for sl in o.material_slots:
        m = sl.material
        if m and re.search(r'crate_(blue|red|white|yellow)|Kraft|HDPE|LIB_Crate|Plastic', m.name):
            bad.add('%s:%s' % (o.name, m.name))
put('steel / iron only (crates, racks, trolleys)', (not bad) if n_steel else None, ', '.join(sorted(bad)[:4]) or ('%d objects checked' % n_steel))

# no logos or text: no text objects, no image named like a logo, no brand strings in material names
txt = [o.name for o in s.objects if o.type == 'FONT' and shown(o)]
imgs = [i.name for i in bpy.data.images if re.search(r'logo|brand|label|decal|sticker|text', i.name, re.I)]
mats = [m.name for m in bpy.data.materials if re.search(r'logo|brand|decal|sticker', m.name, re.I) and m.users]
put('no logos or text', not (txt or imgs or mats), ', '.join((txt + imgs + mats)[:5]) or 'no text objects, logo images or logo materials')

# ship alone (open-sea shots only)
if sid == '259':
    extra = sorted(o.name for o in s.objects if shown(o) and o.type == 'MESH' and o.name not in ('SeaFull', 'SHIP') and
                   not (o.parent and o.parent.name.startswith('SHIP')))
    boats = [o.name for o in s.objects if shown(o) and re.search(r'tug|boat|buoy|Tug|Boat|Buoy', o.name)]
    put('ship alone in the water', not extra and not boats, ', '.join((extra + boats)[:6]) or 'only the ship and its wake')
else:
    put('ship alone in the water', None, 'not an open-sea shot')

json.dump(res, open(out, 'w'), indent=1)
print('STILL', sid, 'FAIL' if any(v['status'] == 'FAIL' for v in res.values()) else 'PASS')
