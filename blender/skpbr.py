"""Photographic materials and lighting for the plant / pond scenes: CC0 image-texture PBR (Poly Haven, ambientCG) in
assets-src/cc0/tex, Poly Haven HDRI worlds with a matched sun, and the shared EEVEE look (AgX MHC, AO, raytraced
reflections, motion blur 0.5). Textures are box-projected in object space so no UVs are needed."""
import math
import os
import glob
import bpy
from mathutils import Euler

CC0 = os.environ.get('SKY_CC0', '/Users/tarunchintakunta/Desktop/skylark/skylark-exim-v3/assets-src/cc0')


def _find(folder, *keys):
    for k in keys:
        hits = sorted(glob.glob(os.path.join(CC0, 'tex', folder, '*%s*' % k)))
        hits = [h for h in hits if h.lower().endswith(('.jpg', '.png'))]
        if hits:
            return hits[0]
    return None


def _img(path, data=False):
    im = bpy.data.images.load(path, check_existing=True)
    if data:
        im.colorspace_settings.name = 'Non-Color'
    return im


def tex_mat(name, folder, scale=1.0, tint=None, rough=None, rough_mul=1.0, metal=None, normal=1.0, coat=0.0,
            dirt=0.0, dirt_scale=0.15, coords='Object', sat=1.0, bright=1.0, aniso=0.0, macro=0.12):
    """PBR material from a CC0 texture set. scale = tiles per metre. tint multiplies the albedo (desaturate with
    sat<1), dirt adds large-scale grime, macro breaks tiling with a low-frequency brightness variation."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    L.new(tc.outputs[coords], mp.inputs['Vector'])

    def image(path, data):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = _img(path, data)
        n.projection = 'BOX'
        n.projection_blend = 0.25
        L.new(mp.outputs[0], n.inputs['Vector'])
        return n

    col = _find(folder, 'diff', 'Color', 'diffuse')
    nor = _find(folder, 'nor_gl', 'NormalGL')
    rgh = _find(folder, 'rough', 'Roughness')
    met = _find(folder, 'Metalness')
    c = image(col, False).outputs['Color'] if col else None
    if c is not None:
        hs = nt.nodes.new('ShaderNodeHueSaturation')
        hs.inputs['Saturation'].default_value = sat
        hs.inputs['Value'].default_value = bright
        L.new(c, hs.inputs['Color'])
        c = hs.outputs[0]
        if tint:
            mx = nt.nodes.new('ShaderNodeMix')
            mx.data_type = 'RGBA'
            mx.blend_type = 'MULTIPLY'
            mx.inputs[0].default_value = 1.0
            L.new(c, mx.inputs[6])
            mx.inputs[7].default_value = (*tint, 1)
            c = mx.outputs[2]
        if macro or dirt:
            nz = nt.nodes.new('ShaderNodeTexNoise')
            nz.inputs['Scale'].default_value = dirt_scale
            nz.inputs['Detail'].default_value = 6
            L.new(tc.outputs['Object'], nz.inputs['Vector'])
            mr = nt.nodes.new('ShaderNodeMapRange')
            mr.inputs['From Min'].default_value = 0.35
            mr.inputs['From Max'].default_value = 0.7
            L.new(nz.outputs['Fac'], mr.inputs['Value'])
            fac = nt.nodes.new('ShaderNodeMath')
            fac.operation = 'MULTIPLY'
            fac.inputs[1].default_value = max(macro, dirt)
            L.new(mr.outputs[0], fac.inputs[0])
            mx2 = nt.nodes.new('ShaderNodeMix')
            mx2.data_type = 'RGBA'
            mx2.blend_type = 'MULTIPLY'
            L.new(fac.outputs[0], mx2.inputs[0])
            L.new(c, mx2.inputs[6])
            mx2.inputs[7].default_value = (0.55, 0.5, 0.44, 1) if dirt else (0.8, 0.8, 0.8, 1)
            c = mx2.outputs[2]
        L.new(c, p.inputs['Base Color'])
    elif tint:
        p.inputs['Base Color'].default_value = (*tint, 1)
    if rough is not None:
        p.inputs['Roughness'].default_value = rough
    elif rgh:
        r = image(rgh, True)
        mt = nt.nodes.new('ShaderNodeMath')
        mt.operation = 'MULTIPLY'
        mt.use_clamp = True
        mt.inputs[1].default_value = rough_mul
        L.new(r.outputs['Color'], mt.inputs[0])
        L.new(mt.outputs[0], p.inputs['Roughness'])
    if metal is not None:
        p.inputs['Metallic'].default_value = metal
    elif met:
        L.new(image(met, True).outputs['Color'], p.inputs['Metallic'])
    if nor and normal > 0:
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal
        L.new(image(nor, True).outputs['Color'], nm.inputs['Color'])
        L.new(nm.outputs[0], p.inputs['Normal'])
    if coat:
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = 0.05
    if aniso:
        p.inputs['Anisotropic'].default_value = aniso
    return m


def plain(name, color, rough=0.5, metal=0.0, coat=0.0, emission=None, estr=0.0, alpha=None, transmission=0.0,
          ior=1.45, bump=0.0, bump_scale=40.0, rand=0.0, aniso=0.0, sss=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    if rand:
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        hsv = nt.nodes.new('ShaderNodeHueSaturation')
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = 1 - rand
        mr.inputs['To Max'].default_value = 1 + rand
        L.new(oi.outputs['Random'], mr.inputs['Value'])
        L.new(mr.outputs[0], hsv.inputs['Value'])
        hsv.inputs['Color'].default_value = (*color, 1)
        L.new(hsv.outputs[0], p.inputs['Base Color'])
    else:
        p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['IOR'].default_value = ior
    if coat:
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = 0.05
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = estr
    if transmission:
        p.inputs['Transmission Weight'].default_value = transmission
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
    if aniso:
        p.inputs['Anisotropic'].default_value = aniso
    if alpha is not None:
        p.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'BLENDED'
    if bump:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = bump_scale
        nz.inputs['Detail'].default_value = 8
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = 0.01
        L.new(nz.outputs['Fac'], b.inputs['Height'])
        L.new(b.outputs[0], p.inputs['Normal'])
    return m


def grime_paint(name, color, rough=0.35, grime=0.35, streak=0.4, coat=0.5, metal=0.1):
    """Painted metal with edge-darkening grime (pointiness is Cycles-only, so: AO node + vertical streaks)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.35
    ao.samples = 8
    # vertical streaks: noise stretched along z
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (6.0, 6.0, 0.35)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 8
    L.new(mp.outputs[0], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.5
    mr.inputs['From Max'].default_value = 0.8
    mr.inputs['To Max'].default_value = streak
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(ao.outputs['AO'], inv.inputs[1])
    g = nt.nodes.new('ShaderNodeMath')
    g.operation = 'MULTIPLY'
    g.inputs[1].default_value = grime
    L.new(inv.outputs[0], g.inputs[0])
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.use_clamp = True
    L.new(g.outputs[0], add.inputs[0])
    L.new(mr.outputs[0], add.inputs[1])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    L.new(add.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (*color, 1)
    mx.inputs[7].default_value = (color[0] * 0.55, color[1] * 0.52, color[2] * 0.48, 1)
    L.new(mx.outputs[2], p.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value = rough
    rr.inputs['To Max'].default_value = min(1, rough + 0.35)
    L.new(add.outputs[0], rr.inputs['Value'])
    L.new(rr.outputs[0], p.inputs['Roughness'])
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = 0.08
    return m


def hdri_world(name, strength=1.0, rot_deg=0.0, sun_elev=45.0, sun_az=0.0, sun_energy=4.0, sun_color=(1.0, 0.96, 0.9),
               bg_strength=None):
    """Poly Haven HDRI as world + a sun lamp aimed to match it. sun_az: compass direction the light COMES FROM,
    degrees, 0 = +Y, 90 = +X. Returns the sun ('Sun', for boundary_camera.py)."""
    s = bpy.context.scene
    w = bpy.data.worlds.get('WORLD_HDRI') or bpy.data.worlds.new('WORLD_HDRI')
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    L = nt.links
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot_deg))
    L.new(tc.outputs['Generated'], mp.inputs['Vector'])
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(os.path.join(CC0, 'hdri', name), check_existing=True)
    L.new(mp.outputs[0], env.inputs['Vector'])
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    L.new(env.outputs[0], bg.inputs['Color'])
    if bg_strength is not None:
        # camera rays see a different strength than lighting (keeps the sky bright without over-lighting)
        lp = nt.nodes.new('ShaderNodeLightPath')
        bg2 = nt.nodes.new('ShaderNodeBackground')
        bg2.inputs['Strength'].default_value = bg_strength
        L.new(env.outputs[0], bg2.inputs['Color'])
        mix = nt.nodes.new('ShaderNodeMixShader')
        L.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
        L.new(bg.outputs[0], mix.inputs[1])
        L.new(bg2.outputs[0], mix.inputs[2])
        L.new(mix.outputs[0], out.inputs[0])
    else:
        L.new(bg.outputs[0], out.inputs[0])
    sun = bpy.data.objects.get('Sun')
    if sun is None:
        sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
        s.collection.objects.link(sun)
    sun.data.energy = sun_energy
    sun.data.color = sun_color
    sun.data.angle = math.radians(1.5)
    az = math.radians(sun_az)
    # light travels opposite to where it comes from; sun lamp points along its local -Z
    sun.rotation_euler = Euler((math.radians(90 - sun_elev), 0, math.pi - az), 'XYZ')
    sun.rotation_euler = Euler((math.radians(90 - sun_elev), 0, -az + math.pi), 'XYZ')
    return sun


def look_settings(kind='exterior', exposure=0.0, samples=32, haze=None):
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    e = s.eevee
    e.taa_render_samples = samples
    for a, v in (('use_raytracing', True), ('use_shadows', True), ('use_gtao', True), ('use_volumetric_shadows', False),
                 ('use_fast_gi', True)):
        if hasattr(e, a):
            setattr(e, a, v)
    if hasattr(e, 'gtao_distance'):
        e.gtao_distance = 1.2
    rto = getattr(e, 'ray_tracing_options', None)
    if rto is not None:
        if hasattr(rto, 'resolution_scale'):
            rto.resolution_scale = '2'
        if hasattr(rto, 'use_denoise'):
            rto.use_denoise = True
    if hasattr(e, 'ray_tracing_method'):
        e.ray_tracing_method = 'SCREEN'
    if hasattr(e, 'shadow_pool_size'):
        e.shadow_pool_size = '1024'
    if hasattr(e, 'shadow_ray_count'):
        e.shadow_ray_count = 1
    if hasattr(e, 'shadow_step_count'):
        e.shadow_step_count = 6
    s.render.use_motion_blur = True
    s.render.motion_blur_shutter = 0.5
    vs = s.view_settings
    vs.view_transform = 'AgX'
    vs.look = 'AgX - Medium High Contrast'
    vs.exposure = exposure
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, 100
    s.render.fps = 24
    s.render.film_transparent = False
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.image_settings.compression = 15
    s.render.use_overwrite = False
    # glare (subtle bloom) through the compositor
    try:
        _bloom(s, haze)
    except Exception as ex:
        print('bloom skipped', ex)


def hdri_sun(name):
    """(compass azimuth deg, elevation deg) of the brightest pixel of a Poly Haven equirect HDRI (Blender mapping)."""
    import numpy as np
    im = bpy.data.images.load(os.path.join(CC0, 'hdri', name), check_existing=True)
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    lum = px.reshape(h, w, 4)[:, :, :3].sum(axis=2)
    j, i = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (i + 0.5) / w, (j + 0.5) / h
    phi = (u - 0.5) * 2 * math.pi
    th = (v - 0.5) * math.pi
    x, y = -math.cos(phi) * math.cos(th), math.sin(phi) * math.cos(th)
    return math.degrees(math.atan2(x, y)), math.degrees(th)


def _bloom(s, haze=None):
    """Compositor: optional aerial haze from the mist pass (haze = (start, depth, color, amount)), then subtle bloom."""
    tree = None
    if hasattr(s, 'compositing_node_group'):
        tree = bpy.data.node_groups.new('COMP_Look', 'CompositorNodeTree')
        s.compositing_node_group = tree
        gi = tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        rl = tree.nodes.new('CompositorNodeRLayers')
        gl = tree.nodes.new('CompositorNodeGlare')
        out = tree.nodes.new('NodeGroupOutput')
        _glare_cfg(gl)
        img = rl.outputs['Image']
        if haze:
            start, depth, color, amount = haze
            bpy.context.view_layer.use_pass_mist = True
            w = s.world
            w.mist_settings.start = start
            w.mist_settings.depth = depth
            w.mist_settings.falloff = 'QUADRATIC'
            mul = tree.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            mul.inputs[1].default_value = amount
            tree.links.new(rl.outputs['Mist'], mul.inputs[0])
            mx = tree.nodes.new('ShaderNodeMix')
            mx.data_type = 'RGBA'
            tree.links.new(mul.outputs[0], mx.inputs[0])
            tree.links.new(img, mx.inputs[6])
            mx.inputs[7].default_value = (*color, 1)
            img = mx.outputs[2]
        tree.links.new(img, gl.inputs['Image'])
        tree.links.new(gl.outputs['Image'], out.inputs[0])
    else:
        s.use_nodes = True
        tree = s.node_tree
        rl = tree.nodes.get('Render Layers') or tree.nodes.new('CompositorNodeRLayers')
        comp = tree.nodes.get('Composite') or tree.nodes.new('CompositorNodeComposite')
        gl = tree.nodes.new('CompositorNodeGlare')
        _glare_cfg(gl)
        tree.links.new(rl.outputs['Image'], gl.inputs['Image'])
        tree.links.new(gl.outputs['Image'], comp.inputs['Image'])


def _glare_cfg(gl):
    for k, v in (('glare_type', 'BLOOM'), ('quality', 'MEDIUM')):
        try:
            setattr(gl, k, v)
        except Exception:
            pass
    # Blender 5.x: the glare type is a menu input (default Streaks, which drew star crosses on sun glints)
    for nm, v in (('Type', 'Bloom'), ('Quality', 'Medium'), ('Clamp', True), ('Maximum', 4.0),
                  ('Threshold', 1.2), ('Strength', 0.12), ('Size', 0.5), ('Mix', -0.85)):
        if nm in gl.inputs:
            try:
                gl.inputs[nm].default_value = v
            except Exception:
                pass
    for k, v in (('threshold', 1.2), ('mix', -0.85), ('size', 7)):
        if hasattr(gl, k):
            try:
                setattr(gl, k, v)
            except Exception:
                pass


def haze(strength=0.0015, color=(0.75, 0.82, 0.92)):
    """Very light world volume for aerial perspective (outdoors only)."""
    w = bpy.context.scene.world
    nt = w.node_tree
    out = [n for n in nt.nodes if n.type == 'OUTPUT_WORLD'][0]
    v = nt.nodes.new('ShaderNodeVolumePrincipled')
    v.inputs['Density'].default_value = strength
    v.inputs['Color'].default_value = (*color, 1)
    v.inputs['Anisotropy'].default_value = 0.3
    nt.links.new(v.outputs[0], out.inputs['Volume'])
    e = bpy.context.scene.eevee
    if hasattr(e, 'volumetric_end'):
        e.volumetric_end = 600
        e.volumetric_tile_size = '16'
        e.volumetric_samples = 32


def add_dust(m, top=1.1, color=(0.44, 0.37, 0.27), amount=0.7, rough=0.92, scale=2.5, zscale=1.0, tag='dusted', bottom=0.0):
    """Overlay road dust / mud on an existing material: strongest at the ground, fading out by world height `top`,
    broken up by noise. Rewires Base Color and Roughness through a mix (idempotent per material and tag).
    zscale < 1 stretches the noise vertically (rust / grime run-off streaks); top=1000 disables the height fade."""
    if m is None or not m.use_nodes or m.get(tag):
        return
    nt = m.node_tree
    p = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if p is None:
        return
    L = nt.links
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L.new(geo.outputs['Position'], sep.inputs[0])
    h = nt.nodes.new('ShaderNodeMapRange')          # 1 at the ground .. 0 at `top`
    h.inputs['From Min'].default_value = top
    h.inputs['From Max'].default_value = bottom
    L.new(sep.outputs[2], h.inputs['Value'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 10
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'MULTIPLY'
    vm.inputs[1].default_value = (1.0, 1.0, zscale)
    L.new(geo.outputs['Position'], vm.inputs[0])
    L.new(vm.outputs[0], nz.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeMapRange')
    nm.inputs['From Min'].default_value = 0.35
    nm.inputs['From Max'].default_value = 0.65
    L.new(nz.outputs['Fac'], nm.inputs['Value'])
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    L.new(h.outputs[0], mul.inputs[0])
    L.new(nm.outputs[0], mul.inputs[1])
    fac = nt.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.use_clamp = True
    fac.inputs[1].default_value = amount * 1.6
    L.new(mul.outputs[0], fac.inputs[0])
    for sock, val in (('Base Color', (*color, 1)), ('Roughness', rough)):
        inp = p.inputs[sock]
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA' if sock == 'Base Color' else 'FLOAT'
        a, b, out = (6, 7, 2) if sock == 'Base Color' else (2, 3, 0)
        if inp.links:
            L.new(inp.links[0].from_socket, mx.inputs[a])
        else:
            mx.inputs[a].default_value = inp.default_value
        mx.inputs[b].default_value = val
        L.new(fac.outputs[0], mx.inputs[0])
        L.new(mx.outputs[out], inp)
    m[tag] = True


def sky_haze(color=(1.0, 0.86, 0.68), amount=0.45, height=0.32):
    """Blend the world HDRI toward a warm haze near the horizon (call after hdri_world): dusty tropical air.
    amount at the horizon, fading out by `height` (direction z)."""
    w = bpy.context.scene.world
    nt = w.node_tree
    L = nt.links
    env = next(n for n in nt.nodes if n.type == 'TEX_ENVIRONMENT')
    tc = next(n for n in nt.nodes if n.type == 'TEX_COORD')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nrm = nt.nodes.new('ShaderNodeVectorMath')
    nrm.operation = 'NORMALIZE'
    L.new(tc.outputs['Generated'], nrm.inputs[0])
    L.new(nrm.outputs[0], sep.inputs[0])
    fac = nt.nodes.new('ShaderNodeMapRange')
    fac.interpolation_type = 'SMOOTHSTEP'
    fac.inputs['From Min'].default_value = -0.02
    fac.inputs['From Max'].default_value = height
    fac.inputs['To Min'].default_value = amount
    fac.inputs['To Max'].default_value = 0.0
    L.new(sep.outputs['Z'], fac.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MIX'
    L.new(fac.outputs[0], mx.inputs[0])
    L.new(env.outputs['Color'], mx.inputs[6])
    mx.inputs[7].default_value = (*color, 1.0)
    for lk in [lk for lk in nt.links if lk.from_node == env and lk.to_node.type == 'BACKGROUND']:
        to = lk.to_socket
        nt.links.remove(lk)
        L.new(mx.outputs[2], to)
    return mx
