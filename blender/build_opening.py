"""Build assets-src/blender/opening.blend (#165): the film opens under the sea, rises through blue-green water past
a school of mackerel and a tuna, breaks the surface and settles on the Vizag horizon at dawn (headland with a
lighthouse, the town along the foot of the hills, boats out on the water). Frames 1-192.
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_opening.py
World: sea surface z = 0, coast toward +Y (west, ~2.5 km), low sun behind the camera's left (east). No names, no signs.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, noise  # noqa: E402
import sklib as L  # noqa: E402
import sklib_sea as S  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets-src', 'blender', 'opening.blend')
D = math.radians
rnd = random.Random(7)
F_END = 192
BREAK = 112          # frame the camera crosses the surface

s = L.reset()
s.frame_start, s.frame_end = 1, F_END
mats = L.M()
L.hdri('qwantani_morning_puresky_4k', strength=0.5, rot=96.0, sun_strength=3.0, sun_color=(1.0, 0.74, 0.52))
s.world.use_sun_shadow = False   # no second shadow from EEVEE's HDRI sun extraction (the Sun lamp keys)
_wn = s.world.node_tree      # warm coastal haze over the whole sky
_bg = [n for n in _wn.nodes if n.type == 'BACKGROUND'][0]
_src = _bg.inputs['Color'].links[0].from_socket
_mx = _wn.nodes.new('ShaderNodeMix')
_mx.data_type = 'RGBA'
_mx.inputs['Factor'].default_value = 0.25
_wn.links.new(_src, _mx.inputs['A'])
_mx.inputs['B'].default_value = (0.9, 0.78, 0.62, 1)
_wn.links.new(_mx.outputs['Result'], _bg.inputs['Color'])

# ---------------------------------------------------------------- sea surface: water from above, a bright window from below
wmat = L.water_mat('MAT_Water_Open', (0.004, 0.04, 0.06))
nt = wmat.node_tree
out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
pr = L.principled(wmat)
geo = nt.nodes.new('ShaderNodeNewGeometry')
glass = nt.nodes.new('ShaderNodeBsdfGlass')
glass.inputs['IOR'].default_value = 1.0 / 1.33          # seen from inside the water
glass.inputs['Roughness'].default_value = 0.04
glass.inputs['Color'].default_value = (0.75, 0.95, 0.95, 1)
mix = nt.nodes.new('ShaderNodeMixShader')
nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
nt.links.new(pr.outputs[0], mix.inputs[1])
nt.links.new(glass.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs['Surface'])
if hasattr(wmat, 'use_raytrace_refraction'):
    wmat.use_raytrace_refraction = True
wmat.use_backface_culling = False
sea = L.ocean('Surface', size=40, repeat=6, res=10, choppy=0.9, wind=6.0, scale=0.45, f0=1, f1=F_END, foam=0.12,
              mat=wmat, loc=(0, 0, 0))
L.far_water('SeaFar', 9000, -0.05, mat=wmat, hole=235.0)

# ---------------------------------------------------------------- the water column: scattering volume, shafts, motes
vm = bpy.data.materials.new('MAT_Underwater')
vm.use_nodes = True
vn = vm.node_tree
vn.nodes.clear()
vo = vn.nodes.new('ShaderNodeOutputMaterial')
pv = vn.nodes.new('ShaderNodeVolumePrincipled')
pv.inputs['Anisotropy'].default_value = 0.65
pv.inputs['Absorption Color'].default_value = (0.02, 0.25, 0.3, 1)
vn.links.new(pv.outputs[0], vo.inputs['Volume'])
# depth gradient: bright teal under the surface, dark blue-black 30-40 m down (object z +20 = surface, -20 = 40 m)
vtc = vn.nodes.new('ShaderNodeTexCoord')
vsx = vn.nodes.new('ShaderNodeSeparateXYZ')
vn.links.new(vtc.outputs['Object'], vsx.inputs[0])
vdp = vn.nodes.new('ShaderNodeMapRange')
vdp.inputs['From Min'].default_value = 20.0
vdp.inputs['From Max'].default_value = -12.0
vn.links.new(vsx.outputs[2], vdp.inputs['Value'])
vpw = vn.nodes.new('ShaderNodeMath')
vpw.operation = 'POWER'
vpw.inputs[1].default_value = 0.7
vn.links.new(vdp.outputs[0], vpw.inputs[0])
vcol = L.mixrgb(vn, vpw.outputs[0], (0.11, 0.46, 0.48), (0.004, 0.03, 0.05))
vn.links.new(vcol, pv.inputs['Color'])
vden = vn.nodes.new('ShaderNodeMapRange')
vden.inputs['To Min'].default_value = 0.05
vden.inputs['To Max'].default_value = 0.13
vn.links.new(vpw.outputs[0], vden.inputs['Value'])
vn.links.new(vden.outputs[0], pv.inputs['Density'])
L.box('WaterColumn', (6000, 6000, 40), (0, 40, -20.12), vm, 0.0)   # edge far past the horizon: its side face showed as a cyan band
# seen from above, the volume shows through the far water as a cyan band under the coast (debug render at f150 with
# the column hidden: band gone), so the column only renders while the camera is under the surface
L.key_vis(bpy.data.objects['WaterColumn'], 1, BREAK + 1)
# seabed 16 m down: rippled sand and rocks, lost in the dark murk (falloff below, not an empty void)
sb = bmesh.new()
bmesh.ops.create_grid(sb, x_segments=80, y_segments=80, size=1.0)
for v in sb.verts:
    x, y = v.co.x * 160, v.co.y * 160 + 60
    v.co = Vector((x, y, -16.0 + 0.25 * math.sin(x * 0.9 + y * 0.3) + 1.6 * noise.noise(Vector((x / 25, y / 25, 0.3)))))
sme = L.bm_to_mesh(sb, 'SEABED', smooth=True)
sme.materials.append(L.pbr('MAT_Seabed', (0.3, 0.29, 0.22), 0.9, var=0.35, bump=0.8, scale=0.4, grime=0.6))
L.obj('SEABED', sme)
rk = bmesh.new()
for i in range(90):
    c = Vector((rnd.uniform(-50, 50), rnd.uniform(5, 90), -16.0))
    r = bmesh.ops.create_icosphere(rk, subdivisions=2, radius=rnd.uniform(0.4, 2.2))
    for v in r['verts']:
        v.co = Vector((v.co.x * rnd.uniform(0.8, 1.4), v.co.y * rnd.uniform(0.8, 1.4), v.co.z * 0.6)) * \
            (1 + 0.2 * noise.noise(v.co * 2.0)) + c
rme = L.bm_to_mesh(rk, 'SEABED_Rocks', smooth=True)
rme.materials.append(L.pbr('MAT_ReefRock', (0.12, 0.13, 0.11), 0.85, var=0.4, bump=1.0, scale=1.2, grime=0.7))
L.obj('SEABED_Rocks', rme)
for _o in ('SEABED', 'SEABED_Rocks'):
    L.key_vis(bpy.data.objects[_o], 1, BREAK + 1)
# light shafts slanting down from the surface along the sun (soft, additive, fading with depth)
# soft god rays: emission + transparency, fading to nothing at the shaft's edges (facing) and along its length
shaft = bpy.data.materials.new('MAT_Shaft')
shaft.use_nodes = True
if hasattr(shaft, 'surface_render_method'):
    shaft.surface_render_method = 'BLENDED'
sn = shaft.node_tree
sn.nodes.clear()
so = sn.nodes.new('ShaderNodeOutputMaterial')
em = sn.nodes.new('ShaderNodeEmission')
em.inputs['Color'].default_value = (0.6, 0.9, 0.88, 1)
em.inputs['Strength'].default_value = 1.0
tr = sn.nodes.new('ShaderNodeBsdfTransparent')
mx = sn.nodes.new('ShaderNodeMixShader')
lw = sn.nodes.new('ShaderNodeLayerWeight')
lw.inputs['Blend'].default_value = 0.5
inv = sn.nodes.new('ShaderNodeMath')
inv.operation = 'SUBTRACT'
inv.inputs[0].default_value = 1.0
sn.links.new(lw.outputs['Facing'], inv.inputs[1])
pw = sn.nodes.new('ShaderNodeMath')
pw.operation = 'POWER'
pw.inputs[1].default_value = 6.0
sn.links.new(inv.outputs[0], pw.inputs[0])
tc = sn.nodes.new('ShaderNodeTexCoord')
sx = sn.nodes.new('ShaderNodeSeparateXYZ')
sn.links.new(tc.outputs['Generated'], sx.inputs[0])
sine = sn.nodes.new('ShaderNodeMath')          # brightest just under the surface, fading to nothing with depth
sine.operation = 'POWER'
sine.inputs[1].default_value = 2.2
sn.links.new(sx.outputs[2], sine.inputs[0])
m1 = sn.nodes.new('ShaderNodeMath')
m1.operation = 'MULTIPLY'
sn.links.new(pw.outputs[0], m1.inputs[0])
sn.links.new(sine.outputs[0], m1.inputs[1])
m2 = sn.nodes.new('ShaderNodeMath')
m2.operation = 'MULTIPLY'
m2.inputs[1].default_value = 0.2                       # overall strength of the rays
sn.links.new(m1.outputs[0], m2.inputs[0])
sn.links.new(m2.outputs[0], mx.inputs['Fac'])
sn.links.new(tr.outputs[0], mx.inputs[1])
sn.links.new(em.outputs[0], mx.inputs[2])
sn.links.new(mx.outputs[0], so.inputs['Surface'])
sun = bpy.data.objects['Sun']
sd = sun.rotation_euler.to_matrix() @ Vector((0, 0, 1))          # toward the sun
refr = Vector((sd.x * 0.75, sd.y * 0.75, sd.z)).normalized()     # bent steeper on entering the water
for i in range(26):
    top = Vector((rnd.choice((-1, 1)) * rnd.uniform(2, 14), rnd.uniform(6, 40), -1.3))   # under the wave troughs, clear of the lens
    bot = top - refr * rnd.uniform(14, 24)
    o = L.cyl(f'SHAFT_{i}', rnd.uniform(0.12, 0.35), (top - bot).length, tuple((top + bot) / 2), shaft, 10,
              r2=None)
    o.rotation_euler = (top - bot).to_track_quat('Z', 'Y').to_euler()
    o.visible_shadow = False
    L.key_vis(o, 1, BREAK - 2)
    for f in range(1, F_END + 1, 24):
        o.scale = (1 + 0.3 * math.sin(f / 13 + i), 1 + 0.3 * math.sin(f / 13 + i), 1)
        o.keyframe_insert('scale', frame=f)
mote = L.pbr('MAT_Mote', (0.8, 0.9, 0.85), 0.6, var=0.0, bump=0.0)
mm = L.sphere_mesh('MOTE_m', 1.0, 6, 4)
mm.materials.append(mote)
for i in range(1400):              # suspended matter near and far, from just under the surface to 14 m down
    yy = rnd.uniform(0.3, 30) ** 1.0
    p = (rnd.uniform(-1, 1) * (0.8 + 0.7 * yy), yy, rnd.uniform(-14, -0.4))
    r = rnd.uniform(0.003, 0.012) * (1.6 if yy < 3 else 1.0)
    o = L.obj(f'MOTE_{i}', mm, None, p, scale=(r, r, r))
    o.visible_shadow = False
    o.keyframe_insert('location', frame=1)
    o.location = (p[0] + rnd.uniform(-0.3, 0.3), p[1] + rnd.uniform(-0.3, 0.3), p[2] + rnd.uniform(0.1, 0.4))
    o.keyframe_insert('location', frame=F_END)
    L.linear_keys(o)

# ---------------------------------------------------------------- a school of mackerel streams across, a tuna passes close
# one tight school (a ball of ~260 fish moving together) crosses 5-6 m in front of the lens, frames 6-150
def school_c(f):
    u = (f - 6) / 144.0
    return Vector((-13 + 26 * u, 5.6 + 0.6 * math.sin(u * 3), -4.4 + 1.2 * u))
for i in range(260):
    off = Vector((rnd.gauss(0, 1.3), rnd.gauss(0, 0.6), rnd.gauss(0, 0.5)))
    fo = L.fish(f'SCHOOL_{i}', 'mackerel', (0, 0, 0), (0, 0, 0), rnd.uniform(1.25, 1.55))
    ph = rnd.uniform(0, 6.28)
    lag = off.x * 0.6
    for f in range(0, 160, 6):
        c = school_c(f - lag)
        fo.location = c + off + Vector((0, 0.15 * math.sin(f / 8 + ph), 0.1 * math.sin(f / 6 + ph)))
        fo.rotation_euler = (0, 0.05 * math.sin(f / 7 + ph), 0.1 * math.cos(f / 8 + ph) + 0.05 * off.y)
        fo.keyframe_insert('location', frame=f)
        fo.keyframe_insert('rotation_euler', frame=f)
    L.key_vis(fo, 1, BREAK - 2)
# a tuna close to the lens (~3 m), rising with the camera, and a second one farther back
for i, (y0, y1, z0, z1, f0, sc) in enumerate(((3.0, 3.4, -6.0, -3.4, 28, 1.0), (9.0, 9.5, -5.2, -4.4, 52, 0.9))):
    t = L.fish(f'TUNA_{i}', 'tuna', (0, 0, 0), (0, 0, D(180)), sc)
    for k in range(0, 78, 6):
        u = k / 72
        t.location = (7 - u * 14, y0 + (y1 - y0) * u, z0 + (z1 - z0) * u + 0.15 * math.sin(k / 9))
        t.rotation_euler = (0, 0, D(180) + 0.08 * math.sin(k / 6))
        t.keyframe_insert('location', frame=f0 + k)
        t.keyframe_insert('rotation_euler', frame=f0 + k)
    L.key_vis(t, f0, f0 + 78)

# ---------------------------------------------------------------- the Vizag horizon: headland, hills, town, boats, gulls
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=120, y_segments=24, size=1.0)
for v in bm.verts:
    x = v.co.x * 4200
    yy = (v.co.y + 1) / 2                    # 0 shore .. 1 inland
    y = 1250 + yy * 700        # coast pulled in from 2.6 km: it fills the top of the frame after the break
    head = 1.0 + 1.6 * math.exp(-((x + 900) / 380) ** 2)          # the headland to the left
    ridge = 170 * (0.55 + 0.45 * math.sin(x / 520 + 0.7)) * (0.7 + 0.3 * noise.noise(Vector((x / 300, yy * 3, 0.5))))
    h = max(0.0, ridge * head * min(1.0, yy * 3.2) - 6)
    v.co = Vector((x, y - (head - 1) * 160 * (1 - yy), S.hill_height(x, y, h)))
me = L.bm_to_mesh(bm, 'COAST_Hills', smooth=True)
me.materials.append(S.hill_material('MAT_CoastHills', haze=0.25))   # tree cover, scrub, dry grass, bare earth
L.obj('COAST_Hills', me)
town = L.tex_pbr('MAT_Town', 'painted_concrete', 0.05, tint=(0.3, 0.27, 0.23), tint_amount=0.55, grime=0.7)   # stained concrete and plaster
win = L.pbr('MAT_TownLights', (1.0, 0.75, 0.45), 0.5, estrength=4.0)
tb = bmesh.new()
for i in range(420):
    x = rnd.uniform(-650, 2600)
    y = 1260 + rnd.uniform(0, 90)
    w, d, h = rnd.uniform(8, 22), rnd.uniform(8, 18), rnd.uniform(6, 34)
    r = bmesh.ops.create_cube(tb, size=1.0)
    for v in r['verts']:
        v.co = Vector((x + v.co.x * w, y + v.co.y * d, h / 2 + v.co.z * h))
tme = L.bm_to_mesh(tb, 'COAST_Town')
tme.materials.append(town)
L.obj('COAST_Town', tme)
lb = bmesh.new()
for i in range(160):
    x = rnd.uniform(-650, 2600)
    r = bmesh.ops.create_cube(lb, size=1.0)
    for v in r['verts']:
        v.co = Vector((x + v.co.x * 1.6, 1252 + v.co.y * 0.4, rnd.uniform(3, 18) + v.co.z * 1.2))
lme = L.bm_to_mesh(lb, 'COAST_Lights')
lme.materials.append(win)
L.obj('COAST_Lights', lme)
# lighthouse on the headland
hx, hy = -900, 1120
_hz = max((v.co.z for v in bpy.data.objects['COAST_Hills'].data.vertices
           if abs(v.co.x - hx) < 60 and abs(v.co.y - hy) < 60), default=150.0) - 3.0   # stand on the (noisy) headland
L.cyl('LIGHTHOUSE', 4.0, 34.0, (hx, hy, _hz), mats['paint_white'], 16, r2=3.0, origin='base')
L.cyl('LIGHTHOUSE_Lamp', 3.2, 4.0, (hx, hy, _hz + 34), L.pbr('MAT_Beacon', (1.0, 0.85, 0.6), 0.3, estrength=8.0), 16, origin='base')
# boats out on the water (silhouettes against the shore), gulls
for i, (x, y, rz) in enumerate(((-70, 240, 0.3), (60, 380, 2.4), (150, 520, 1.2), (-160, 600, 0.9), (30, 760, 2.9), (260, 840, 1.9),
                                 (-280, 900, 0.5), (120, 1000, 2.2), (-30, 1100, 1.4))):
    S.vessel(f'FARBOAT{i}', loc=(x, y, 0), rot_z=rz, mats=mats, detail=False)
for i in range(7):      # 3 near (12-25 m, wings and black tips read), 4 farther over the boats
    g = S.gull(f'GULL{i}', (0, 0, 0))
    near = i < 3
    cx, cy, cz = rnd.uniform(-8, 8) if near else rnd.uniform(-40, 40), rnd.uniform(14, 26) if near else rnd.uniform(60, 140), \
        rnd.uniform(4, 8) if near else rnd.uniform(10, 25)
    rad = 5 if near else 12
    path = [(cx + rad * math.cos(k * 0.08 + i * 1.7), cy + rad * 0.5 * math.sin(k * 0.08 + i * 1.7), cz + 0.4 * math.sin(k * 0.4))
            for k in range(24)]
    S.flap(g, 1, F_END, period=rnd.randint(16, 22), amp=24, path=path)   # slow strokes, glide speed: no blur streaks
    L.key_vis(g, BREAK - 6)

# ---------------------------------------------------------------- surface break: a splash crown and droplets round the lens
spl = L.pbr('MAT_Splash', (0.85, 0.93, 0.95), 0.05, transmission=0.9, ior=1.33, coat=0.6)
dm = L.sphere_mesh('SPLASH_m', 1.0, 8, 6)
dm.materials.append(spl)
for i in range(40):
    a = rnd.uniform(0, 2 * math.pi)
    r0 = rnd.uniform(0.2, 0.9)
    o = L.obj(f'SPLASH_{i}', dm, None, (0, 0, 0))
    rr = rnd.uniform(0.008, 0.03)
    o.scale = (rr, rr, rr * rnd.uniform(1.2, 2.5))
    v = Vector((math.cos(a) * rnd.uniform(0.6, 1.6), math.sin(a) * rnd.uniform(0.6, 1.6) + 0.4, rnd.uniform(1.8, 3.4)))
    f0 = BREAK - 2 + rnd.randint(0, 4)
    for k in range(0, 22, 2):
        t = k / 24
        p = Vector((math.cos(a) * r0 * 2, 4.5 + math.sin(a) * r0, 0.05)) + v * t + Vector((0, 0, -4.9 * t * t))
        o.location = p
        o.keyframe_insert('location', frame=f0 + k)
    L.key_vis(o, f0, f0 + 22)

# ---------------------------------------------------------------- camera: rises through the water, breaks the surface, settles on the coast
cam = L.camera('Camera', 24, (0, -2, -6), (0, 20, -2))
cam.data.dof.aperture_fstop = 8.0
keys = [
    (1, (0.0, -1.0, -7.5), (0.0, 18.0, -2.5), 22),
    (50, (0.2, 0.0, -5.0), (0.0, 18.0, -1.0), 22),
    (96, (0.1, 1.0, -1.6), (0.0, 30.0, 1.5), 24),
    (BREAK, (0.0, 1.4, 0.05), (0.0, 400.0, 6.0), 26),
    (132, (0.0, 1.8, 1.3), (0.0, 1200.0, 30.0), 30),
    (F_END, (0.0, 2.4, 1.9), (40.0, 1250.0, 45.0), 38),
]
L.cam_path(cam, keys, focus=[(1, 8.0), (60, 9.0), (100, 6.0), (BREAK, 30.0), (140, 600.0), (F_END, 1250.0)])
for f, cs in ((1, 0.05), (BREAK, 0.05), (BREAK + 12, 0.3)):
    cam.data.clip_start = cs
    cam.data.keyframe_insert('clip_start', frame=f)
s.camera = cam

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
sys.argv = [sys.argv[0], '--', 'opening', '1', str(F_END), 'sea']
exec(compile(open(os.path.join(HERE, 'render_settings.py')).read(), 'render_settings.py', 'exec'))
e = s.eevee
for attr, val in (('use_volumetric_shadows', True), ('volumetric_end', 120.0), ('volumetric_tile_size', '8')):
    if hasattr(e, attr):
        setattr(e, attr, val)
s.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_mainfile()
print('BUILT', OUT, len(bpy.data.objects), 'objects')
