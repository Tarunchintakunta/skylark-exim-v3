"""Per-frame clearance check for o-catch: the net sack (evaluated mesh) against the king post, the boom and the mast.
  Blender -b assets-src/blender/o-catch.blend --python blender/check_o_catch_net.py
Prints the frames where any sack vertex comes inside a pole (radius + 2 cm) and fails if there are any."""
import bpy
from mathutils import Vector
from mathutils.geometry import intersect_point_line

s = bpy.context.scene
net = bpy.data.objects['NET_Mesh']
post = bpy.data.objects['BOAT_KingPost']
boom = bpy.data.objects['BOAT_Boom']
mast = bpy.data.objects['BOAT_Mast']


def axis(o, length):
    a = o.matrix_world @ Vector((0, 0, 0))
    b = o.matrix_world @ Vector((0, 0, length))
    return a, b


def seg_dist(p, a, b):
    q, t = intersect_point_line(p, a, b)
    t = max(0.0, min(1.0, t))
    return (p - (a + (b - a) * t)).length


bad = []
dg = bpy.context.evaluated_depsgraph_get()
for f in range(1, s.frame_end + 1):
    s.frame_set(f)
    if net.hide_render:
        continue
    ev = net.evaluated_get(dg)
    me = ev.to_mesh()
    mw = net.matrix_world
    pts = [mw @ me.vertices[i].co for i in range(0, len(me.vertices), 7)]
    ev.to_mesh_clear()
    worst = []
    for nm, o, ln, r in (('kingpost', post, 8.0, 0.22), ('boom', boom, boom.data.dimensions.z if hasattr(boom.data, 'dimensions') else 0, 0.17),
                         ('mast', mast, 5.0, 0.1)):
        if nm == 'boom':
            ln = max(v.co.z for v in boom.data.vertices)
        a, b = axis(o, ln)
        d = min(seg_dist(p, a, b) for p in pts)
        if d < r + 0.02:
            worst.append((nm, round(d - r, 3)))
    if worst:
        bad.append((f, worst))
print('NETCHECK clipping frames:', len(bad), bad[:30])
assert not bad, 'net sack clips a pole'
