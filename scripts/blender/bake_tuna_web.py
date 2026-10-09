"""Web tuna for the Products stage (public/models/tuna.glb, #141): the yellowfin photogrammetry scan (CC BY 4.0,
ffish.asia / floraZia.com) cleaned of loose crumbs, voxel-remeshed, decimated to ~20k faces, re-unwrapped, and its
unlit scan colour baked into one 1024 texture.
  Blender -b assets-src/blender/fish_scans.blend --python scripts/blender/bake_tuna_web.py -- public/models/tuna.glb 14000 1024
fish_scans.blend (SCAN_Tuna) is built by blender/prep_scans.py on the Blender lane (#100).
"""
import bpy, bmesh, sys, math
a = sys.argv[sys.argv.index('--')+1:]
out, ratio, res = a[0], float(a[1]), int(a[2])
hi = bpy.data.objects['SCAN_Tuna']
for o in list(bpy.data.objects):
    if o is not hi: bpy.data.objects.remove(o)
sc = bpy.context.scene
lo = hi.copy(); lo.data = hi.data.copy(); lo.name = 'Tuna'; sc.collection.objects.link(lo)
bm = bmesh.new(); bm.from_mesh(lo.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
# drop the scan's loose crumbs: keep connected pieces with at least 0.3% of the surface
bm.faces.ensure_lookup_table(); seen = set(); parts = []; total = sum(f.calc_area() for f in bm.faces)
for f0 in bm.faces:
    if f0.index in seen: continue
    stack, part = [f0], []
    seen.add(f0.index)
    while stack:
        f = stack.pop(); part.append(f)
        for e in f.edges:
            for g in e.link_faces:
                if g.index not in seen: seen.add(g.index); stack.append(g)
    parts.append(part)
drop = [f for p in parts if sum(f.calc_area() for f in p) < 0.003 * total for f in p]
print('PARTS', len(parts), 'drop faces', len(drop))
bmesh.ops.delete(bm, geom=drop, context='FACES')
bm.to_mesh(lo.data); bm.free()
r = lo.modifiers.new('R', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.004
with bpy.context.temp_override(active_object=lo, object=lo): bpy.ops.object.modifier_apply(modifier='R')
print('REMESH', len(lo.data.polygons))
d = lo.modifiers.new('D', 'DECIMATE'); d.ratio = ratio / len(lo.data.polygons)
with bpy.context.temp_override(active_object=lo, object=lo): bpy.ops.object.modifier_apply(modifier='D')
print('LOW', len(lo.data.polygons))
lo.data.materials.clear()
while len(lo.data.uv_layers): lo.data.uv_layers.remove(lo.data.uv_layers[0])
lo.data.uv_layers.new(name='UV')
for o in sc.objects: o.select_set(o is lo)
bpy.context.view_layer.objects.active = lo
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
img = bpy.data.images.new('tuna_albedo', res, res)
m = bpy.data.materials.new('tuna'); m.use_nodes = True
nt = m.node_tree; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
bsdf = nt.nodes['Principled BSDF']; nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 0.35
nt.nodes.active = tex
lo.data.materials.append(m)
for p in lo.data.polygons: p.use_smooth = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.device = 'CPU'
hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
b = sc.render.bake; b.use_selected_to_active = True; b.cage_extrusion = 0.012; b.max_ray_distance = 0.03; b.margin = 6
b.use_pass_direct = False; b.use_pass_indirect = False; b.use_pass_color = True
bpy.ops.object.bake(type='EMIT')
bpy.data.objects.remove(hi)
lo.scale = (2.18,)*3
img.file_format = 'JPEG'
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_image_quality=80, export_apply=True, export_animations=False)
