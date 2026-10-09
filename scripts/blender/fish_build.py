"""Build a Products model GLB from the kohl-draft base (docs/BLENDER_GLB_SPEC.md §2, §4, §5, §7).

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/blender/fish_build.py -- tuna
Import base → join → smooth (subdivision) → species colour fixes → Smart UV → Cycles bake of the base colour into
one 2048 albedo → one Principled BSDF → 3 review renders on #eef5f6 → assets-src/models/<name>.glb (compression off;
scripts/optimize-glb.sh adds meshopt + WebP).
"""
import bpy, math, os, sys
from mathutils import Vector

NAME = sys.argv[sys.argv.index('--') + 1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE = {
    'tuna': '../kohl/public/assets/models/products/tuna_hero.glb',
    'swordfish': '../kohl/public/assets/models/products/swordfish_hero.glb',
    'shrimp': '../kohl/public/assets/models/products/shrimp_product_forms.glb',
}[NAME]
SPEC = {  # metallic, roughness, max tris (§4)
    'tuna': (0.4, 0.35, 30000),
    'swordfish': (0.3, 0.38, 30000),
    'shrimp': (0.0, 0.3, 30000),
}[NAME]
OUT = os.path.join(ROOT, 'assets-src', 'models', f'{NAME}.glb')
RENDERS = os.path.join(ROOT, 'docs', 'renders')

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, BASE))
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if NAME == 'shrimp':
    # the kohl file is a tray of product forms; keep only the first whole (head-on) shrimp
    keep = [o for o in meshes if o.name.split('_')[0] in ('HOSO',) and '_0_' in o.name] or meshes
    for o in meshes:
        if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
    meshes = keep
for o in bpy.data.objects:
    if o.type != 'MESH':
        for c in o.children: c.parent = None
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw; o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
fish = bpy.context.active_object
fish.name = fish.data.name = NAME
for o in list(bpy.data.objects):
    if o is not fish: bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# orient: longest axis on X, head toward +X (the kohl models already face +X), centre on the origin
bb = [fish.matrix_world @ Vector(c) for c in fish.bound_box]
size = Vector((max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)))
center = sum(bb, Vector()) / 8
fish.location -= center
bpy.ops.object.transform_apply(location=True)

# smooth the faceted low-poly base, staying inside the triangle budget
tris = sum(len(p.vertices) - 2 for p in fish.data.polygons)
lvl = 2 if tris * 16 <= SPEC[2] else 1 if tris * 4 <= SPEC[2] else 0
if lvl:
    m = fish.modifiers.new('Subd', 'SUBSURF'); m.levels = m.render_levels = lvl
    bpy.ops.object.modifier_apply(modifier='Subd')
bpy.ops.object.shade_smooth()
tris = sum(len(p.vertices) - 2 for p in fish.data.polygons)

# species colour fixes on the kohl palette (§2.2)
def tint(mat_name, rgb):
    m = bpy.data.materials.get(mat_name)
    if m and m.use_nodes:
        b = m.node_tree.nodes.get('Principled BSDF')
        if b and not b.inputs['Base Color'].is_linked: b.inputs['Base Color'].default_value = (*rgb, 1)
if NAME == 'tuna': tint('TunaYellow', (0.95, 0.76, 0.12)); tint('TunaFin', (0.05, 0.09, 0.16))
if NAME == 'swordfish': tint('SwordFin', (0.16, 0.14, 0.12))
if NAME == 'shrimp':
    tint('ShrimpShell', (0.78, 0.76, 0.72)); tint('ShrimpTail', (0.62, 0.6, 0.58))  # raw Vannamei: translucent grey-white

# body colour as a procedural back→flank→belly gradient (by height), replacing the kohl vertex-colour body
BODY = {
    'tuna': ['TunaBody'], 'swordfish': ['SwordBody'], 'shrimp': [],
}[NAME]
RAMP = {
    'tuna': [(0.0, (0.86, 0.89, 0.9)), (0.44, (0.62, 0.68, 0.72)), (0.56, (0.2, 0.28, 0.38)), (0.6, (0.82, 0.66, 0.16)), (0.63, (0.1, 0.17, 0.3)), (1.0, (0.025, 0.05, 0.12))],
    'swordfish': [(0.0, (0.78, 0.79, 0.79)), (0.42, (0.5, 0.49, 0.47)), (0.6, (0.24, 0.21, 0.19)), (1.0, (0.12, 0.1, 0.09))],
}.get(NAME)
zmin = min((fish.matrix_world @ v.co).z for v in fish.data.vertices); zmax = max((fish.matrix_world @ v.co).z for v in fish.data.vertices)
for mn in BODY:
    m = bpy.data.materials.get(mn)
    if not m: continue
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    for l in list(b.inputs['Base Color'].links): nt.links.remove(l)
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = zmin; mr.inputs['From Max'].default_value = zmax
    ramp = nt.nodes.new('ShaderNodeValToRGB'); els = ramp.color_ramp.elements
    for i, (pos, rgb) in enumerate(RAMP):
        e = els[i] if i < 2 else els.new(pos)
        e.position = pos; e.color = (*rgb, 1)
    nt.links.new(tc.outputs['Object'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])

# bake the base colour into one 2048 albedo
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
img = bpy.data.images.new(f'{NAME}_albedo', 2048, 2048)
for m in fish.data.materials:
    if not m or not m.use_nodes: continue
    n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
    m.node_tree.nodes.active = n
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.cycles.device = 'GPU'
sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.margin = 8
fish.select_set(True); bpy.context.view_layer.objects.active = fish
bpy.ops.object.bake(type='DIFFUSE')
tex_path = os.path.join(ROOT, 'assets-src', 'models', f'{NAME}_albedo.png')
img.filepath_raw = tex_path; img.file_format = 'PNG'; img.save()

final = bpy.data.materials.new(NAME); final.use_nodes = True
b = final.node_tree.nodes['Principled BSDF']
t = final.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
final.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
b.inputs['Metallic'].default_value, b.inputs['Roughness'].default_value = SPEC[0], SPEC[1]
fish.data.materials.clear(); fish.data.materials.append(final)
for a in list(fish.data.color_attributes): fish.data.color_attributes.remove(a)

# review renders: side, 3/4, top on the light Products background
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 32
sc.render.resolution_x, sc.render.resolution_y = 1200, 750
sc.view_settings.view_transform = 'Standard'  # so the background is exactly #eef5f6
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.855, 0.913, 0.922, 1)  # #eef5f6 (linear)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(30))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(size) * 1.15
os.makedirs(RENDERS, exist_ok=True)
for view, d in (('side', (0, -1, 0.0)), ('34', (0.7, -0.8, 0.45)), ('top', (0.0001, 0, 1))):
    v = Vector(d).normalized() * max(size) * 3
    cam.location = v
    cam.rotation_euler = (-v).to_track_quat('-Z', 'Y').to_euler()
    sc.render.film_transparent = False
    sc.render.filepath = os.path.join(RENDERS, f'{NAME}-{view}.png')
    bpy.ops.render.render(write_still=True)

bpy.data.objects.remove(cam, do_unlink=True); bpy.data.objects.remove(sun, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT'); fish.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_cameras=False, export_lights=False,
                          export_yup=True, export_apply=True, export_animations=False, export_draco_mesh_compression_enable=False)
print('EXPORTED', OUT, 'tris', tris, 'size', [round(x, 2) for x in size])
