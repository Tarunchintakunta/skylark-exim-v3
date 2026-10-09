"""Skylark asset library: procedural builders shared by every scene (docs/blender/ASSET_LIBRARY.md).

Every scene build script imports this module, so the same object names, materials, sky and people exist in every
.blend (shared boundaries match objects by name). `blender/build_library.py` lays every asset out in
assets-src/blender/asset-library.blend for the review stills.
Units: metres, +Z up, assets face +X, origin at the base centre. No text, logos or numbers on anything.
"""
import math
import os
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

REPO = None  # set by build scripts


# ---------------------------------------------------------------- scene basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.unit_settings.system = 'METRIC'
    return s


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


_ACTIVE = []


def use(c):
    """Set the collection new objects go into."""
    _ACTIVE[:] = [c]
    return c


def _link(o, c=None):
    (c or (_ACTIVE[0] if _ACTIVE else bpy.context.scene.collection)).objects.link(o)
    return o


def empty(name, loc=(0, 0, 0), parent=None, c=None, size=0.3):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = size
    _link(o, c)
    o.parent = parent
    o.location = loc
    return o


def obj(name, me, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), parent=None, c=None):
    if mat is not None and me is not None and len(me.materials) == 0:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    _link(o, c)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.scale = scale
    return o


def inst(name, src, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), parent=None, c=None):
    """Linked duplicate (shares mesh data) of src."""
    o = bpy.data.objects.new(name, src.data)
    _link(o, c)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.scale = scale
    return o


def bm_to_mesh(bm, name, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return me


def _bevel(bm, w, seg=2):
    if w > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=w, segments=seg, profile=0.5, affect='EDGES',
                        clamp_overlap=True)


def box_mesh(name, size, bevel=0.02, seg=2, origin='center'):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    oz = sz / 2 if origin == 'base' else 0
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz + oz))
    _bevel(bm, min(bevel, min(size) * 0.45), seg)
    return bm_to_mesh(bm, name, smooth=bevel > 0 and seg > 1)


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.02, seg=2, rot=(0, 0, 0), parent=None, origin='center', c=None):
    return obj(name, box_mesh(name, size, bevel, seg, origin), mat, loc, rot, parent=parent, c=c)


def cyl_mesh(name, r, h, verts=24, r2=None, axis='Z', bevel=0.0, origin='center', cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=verts, radius1=r, radius2=r if r2 is None else r2,
                          depth=h)
    if origin == 'base':
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    if bevel:
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > 0.6]
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    return bm_to_mesh(bm, name, smooth=True)


def cyl(name, r, h, loc=(0, 0, 0), mat=None, verts=24, r2=None, axis='Z', rot=(0, 0, 0), parent=None, bevel=0.0,
        origin='center', c=None):
    return obj(name, cyl_mesh(name, r, h, verts, r2, axis, bevel, origin), mat, loc, rot, parent=parent, c=c)


def sphere_mesh(name, r, seg=16, rings=10):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    return bm_to_mesh(bm, name, smooth=True)


def sphere(name, r, loc=(0, 0, 0), mat=None, scale=(1, 1, 1), seg=16, rings=10, parent=None, c=None):
    return obj(name, sphere_mesh(name, r, seg, rings), mat, loc, scale=scale, parent=parent, c=c)


def torus_mesh(name, R, r, seg=32, cseg=8):
    bm = bmesh.new()
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(cseg):
            b = 2 * math.pi * j / cseg
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a),
                                      r * math.sin(b))))
        verts.append(ring)
    for i in range(seg):
        for j in range(cseg):
            bm.faces.new((verts[i][j], verts[(i + 1) % seg][j], verts[(i + 1) % seg][(j + 1) % cseg],
                          verts[i][(j + 1) % cseg]))
    return bm_to_mesh(bm, name, smooth=True)


def tube_mesh(name, pts, r, cseg=8, closed=False):
    """Swept circle along a polyline (ropes, pipes, rails)."""
    bm = bmesh.new()
    rings = []
    pts = [Vector(p) for p in pts]
    for i, p in enumerate(pts):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        a = d.cross(up).normalized()
        b = d.cross(a).normalized()
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * j / cseg) * a + math.sin(2 * math.pi * j / cseg) * b))
                      for j in range(cseg)])
    for i in range(len(rings) - 1):
        for j in range(cseg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % cseg], rings[i][(j + 1) % cseg]))
    return bm_to_mesh(bm, name, smooth=True)


def tube(name, pts, r, mat=None, cseg=8, loc=(0, 0, 0), parent=None, c=None):
    return obj(name, tube_mesh(name, pts, r, cseg), mat, loc, parent=parent, c=c)


def join(objs, name):
    """Join objects into one (keeps materials). Returns the joined object."""
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    ctx = {'active_object': objs[0], 'selected_editable_objects': objs, 'object': objs[0]}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def apply_transform(o):
    me = o.data
    me.transform(o.matrix_basis)
    o.matrix_basis = Matrix.Identity(4)


# ---------------------------------------------------------------- materials
def _node(nt, t, loc=(0, 0)):
    n = nt.nodes.new(t)
    n.location = loc
    return n


def _sock(node, name, kind=None, out=False):
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m


def principled(m):
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    p = _node(m.node_tree, 'ShaderNodeBsdfPrincipled')
    out = [n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    m.node_tree.links.new(p.outputs[0], out.inputs[0])
    return p


def mixrgb(nt, fac, a, b, blend='MIX', loc=(0, 0)):
    n = _node(nt, 'ShaderNodeMix', loc)
    n.data_type = 'RGBA'
    n.blend_type = blend
    l = nt.links
    if isinstance(fac, (int, float)):
        n.inputs[0].default_value = fac
    else:
        l.new(fac, n.inputs[0])
    for val, sock in ((a, _sock(n, 'A', 'RGBA')), (b, _sock(n, 'B', 'RGBA'))):
        if isinstance(val, tuple):
            sock.default_value = (*val[:3], 1)
        else:
            l.new(val, sock)
    return _sock(n, 'Result', 'RGBA', out=True)


def pbr(name, color, rough=0.5, metal=0.0, var=0.12, bump=0.1, scale=3.0, coat=0.0, grime=0.0, emission=None,
        estrength=0.0, transmission=0.0, alpha=None, attr=None, ior=1.45, sss=0.0, coords='Object', rough_var=0.12):
    """Principled material with procedural colour variation, grime and micro bump (no image textures needed)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    p.location = (400, 0)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    co = _sock(tc, coords, out=True)
    n1 = _node(nt, 'ShaderNodeTexNoise', (-900, 200))
    n1.inputs['Scale'].default_value = scale
    n1.inputs['Detail'].default_value = 6
    l.new(co, n1.inputs['Vector'])
    if attr:
        a = _node(nt, 'ShaderNodeAttribute', (-600, 400))
        a.attribute_name = attr
        a.attribute_type = 'GEOMETRY'
        base = _sock(a, 'Color', out=True)
    else:
        base = tuple(color)
    dark = tuple(c * (1 - var) for c in color) if not attr else (0.5, 0.5, 0.5)
    col = mixrgb(nt, _sock(n1, 'Factor', out=True), base, dark if not attr else base, loc=(-300, 300))
    if attr:
        col = mixrgb(nt, _sock(n1, 'Factor', out=True), col, (1 - var, 1 - var, 1 - var), blend='MULTIPLY', loc=(-200, 300))
    if grime > 0:
        n2 = _node(nt, 'ShaderNodeTexNoise', (-900, -200))
        n2.inputs['Scale'].default_value = scale * 0.35
        n2.inputs['Detail'].default_value = 8
        l.new(co, n2.inputs['Vector'])
        r = _node(nt, 'ShaderNodeMapRange', (-600, -200))
        r.inputs['From Min'].default_value = 0.5
        r.inputs['From Max'].default_value = 0.75
        l.new(_sock(n2, 'Factor', out=True), r.inputs['Value'])
        gm = _node(nt, 'ShaderNodeMath', (-450, -200))
        gm.operation = 'MULTIPLY'
        gm.inputs[1].default_value = grime
        l.new(r.outputs[0], gm.inputs[0])
        col = mixrgb(nt, gm.outputs[0], col, (0.12, 0.09, 0.06), loc=(-100, 200))
    l.new(col, p.inputs['Base Color'])
    rr = _node(nt, 'ShaderNodeMapRange', (-300, 0))
    rr.inputs['To Min'].default_value = max(0.0, rough - rough_var)
    rr.inputs['To Max'].default_value = min(1.0, rough + rough_var)
    l.new(_sock(n1, 'Factor', out=True), rr.inputs['Value'])
    l.new(rr.outputs[0], p.inputs['Roughness'])
    p.inputs['Metallic'].default_value = metal
    p.inputs['IOR'].default_value = ior
    if bump > 0:
        n3 = _node(nt, 'ShaderNodeTexNoise', (-600, -450))
        n3.inputs['Scale'].default_value = scale * 12
        n3.inputs['Detail'].default_value = 4
        l.new(co, n3.inputs['Vector'])
        b = _node(nt, 'ShaderNodeBump', (100, -400))
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = 0.02
        l.new(_sock(n3, 'Factor', out=True), b.inputs['Height'])
        l.new(b.outputs[0], p.inputs['Normal'])
    if coat:
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = 0.08
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = estrength
    if transmission:
        p.inputs['Transmission Weight'].default_value = transmission
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
    if alpha is not None:
        p.inputs['Alpha'].default_value = alpha
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
    return m


TEXDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets-src', 'cc0', 'tex')


def _texfile(tset, *keys):
    d = os.path.join(TEXDIR, tset)
    if not os.path.isdir(d):
        return None
    for k in keys:
        for f in sorted(os.listdir(d)):
            lf = f.lower()
            if k in lf and not lf.endswith('.exr'):
                return os.path.join(d, f)
    return None


def tex_pbr(name, tset, scale=1.0, tint=None, tint_amount=0.75, rough_mul=1.0, rough_add=0.0, metal=None, bump=0.4,
            attr=None, grime=0.0, coat=0.0, dark=1.0, paint_mask=False):
    """PBR material from a CC0 texture set in assets-src/cc0/tex/<tset> (ambientCG or Poly Haven naming), box-projected
    in object space (no UVs needed). tint overlays a colour on the texture's luminance (keeps its wear and grime);
    attr takes the tint per face/instance from a colour attribute. Falls back to pbr() if the set is missing."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    col_f = _texfile(tset, '_color', '_diff')
    if not col_f:
        return pbr(name, tint or (0.5, 0.5, 0.5), 0.5 * rough_mul + rough_add, metal or 0.0, attr=attr, grime=grime)
    rough_f = _texfile(tset, '_roughness', '_rough')
    disp_f = _texfile(tset, '_displacement', '_disp')
    metal_f = _texfile(tset, '_metalness', '_metal_')
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    mp = _node(nt, 'ShaderNodeMapping', (-1200, 0))
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    l.new(_sock(tc, 'Object', out=True), mp.inputs['Vector'])

    def img(path, nonc, y):
        n = _node(nt, 'ShaderNodeTexImage', (-950, y))
        n.image = bpy.data.images.load(path, check_existing=True)
        if nonc:
            n.image.colorspace_settings.name = 'Non-Color'
        n.projection = 'BOX'
        n.projection_blend = 0.25
        l.new(mp.outputs[0], n.inputs['Vector'])
        return n

    ci = img(col_f, False, 300)
    col = ci.outputs['Color']
    if tint is not None or attr:
        import numpy as np
        im = ci.image
        px = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
        im.pixels.foreach_get(px)
        px = px.reshape(-1, 4)[::97, :3]
        mean = float((px * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).sum(axis=1).mean())
        bw = _node(nt, 'ShaderNodeRGBToBW', (-650, 300))
        l.new(col, bw.inputs[0])
        g = _node(nt, 'ShaderNodeMath', (-500, 300))
        g.operation = 'MULTIPLY'
        g.inputs[1].default_value = dark / max(0.005, mean)  # texture luminance normalised to 1 on average
        l.new(bw.outputs[0], g.inputs[0])
        if attr:
            a = _node(nt, 'ShaderNodeAttribute', (-650, 500))
            a.attribute_name = attr
            a.attribute_type = 'GEOMETRY'
            tcol = _sock(a, 'Color', out=True)
        else:
            tcol = tuple(tint)
        mul = _node(nt, 'ShaderNodeMix', (-350, 400))
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        cr = _node(nt, 'ShaderNodeCombineColor', (-500, 450))
        for i in range(3):
            l.new(g.outputs[0], cr.inputs[i])
        l.new(cr.outputs[0], _sock(mul, 'A', 'RGBA'))
        if isinstance(tcol, tuple):
            _sock(mul, 'B', 'RGBA').default_value = (*tcol, 1)
        else:
            l.new(tcol, _sock(mul, 'B', 'RGBA'))
        tinted = _sock(mul, 'Result', 'RGBA', out=True)  # luminance (normalised) * tint, keeps wear and dirt
        if paint_mask:
            # painted metal: paint where the texture's own paint colour is (red channel dominant), bare steel in scratches
            sep = _node(nt, 'ShaderNodeSeparateColor', (-650, 650))
            l.new(ci.outputs['Color'], sep.inputs[0])
            dm = _node(nt, 'ShaderNodeMath', (-500, 650))
            dm.operation = 'SUBTRACT'
            l.new(sep.outputs[0], dm.inputs[0])
            l.new(sep.outputs[1], dm.inputs[1])
            mk = _node(nt, 'ShaderNodeMapRange', (-350, 650))
            mk.inputs['From Min'].default_value = 0.08
            mk.inputs['From Max'].default_value = 0.3
            l.new(dm.outputs[0], mk.inputs['Value'])
            col = mixrgb(nt, mk.outputs[0], (0.5, 0.51, 0.52), tcol if isinstance(tcol, tuple) else (0.5, 0.5, 0.5), loc=(-200, 300))
        else:
            col = mixrgb(nt, tint_amount, col, tinted, loc=(-200, 300))
    if grime > 0:
        n2 = _node(nt, 'ShaderNodeTexNoise', (-650, -150))
        n2.inputs['Scale'].default_value = 0.6
        n2.inputs['Detail'].default_value = 8
        l.new(_sock(tc, 'Object', out=True), n2.inputs['Vector'])
        r = _node(nt, 'ShaderNodeMapRange', (-450, -150))
        r.inputs['From Min'].default_value = 0.52
        r.inputs['From Max'].default_value = 0.75
        r.inputs['To Max'].default_value = grime
        l.new(_sock(n2, 'Factor', out=True), r.inputs['Value'])
        col = mixrgb(nt, r.outputs[0], col, (0.11, 0.08, 0.05), loc=(-100, 200))
    l.new(col, p.inputs['Base Color'])
    if rough_f:
        ri = img(rough_f, True, 0)
        rr = _node(nt, 'ShaderNodeMath', (-600, 0))
        rr.operation = 'MULTIPLY_ADD'
        rr.inputs[1].default_value = rough_mul
        rr.inputs[2].default_value = rough_add
        rr.use_clamp = True
        l.new(ri.outputs['Color'], rr.inputs[0])
        l.new(rr.outputs[0], p.inputs['Roughness'])
    else:
        p.inputs['Roughness'].default_value = 0.5 * rough_mul + rough_add
    if metal is not None:
        p.inputs['Metallic'].default_value = metal
    elif metal_f:
        mi = img(metal_f, True, -300)
        l.new(mi.outputs['Color'], p.inputs['Metallic'])
    if disp_f and bump > 0:
        di = img(disp_f, True, -600)
        b = _node(nt, 'ShaderNodeBump', (-200, -600))
        b.inputs['Strength'].default_value = bump
        b.inputs['Distance'].default_value = 0.02 / max(scale, 0.05)
        l.new(di.outputs['Color'], b.inputs['Height'])
        l.new(b.outputs[0], p.inputs['Normal'])
    if coat:
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = 0.1
    return m


def textured_overrides():
    """Create the CC0-textured versions of the shared materials first, so every later pbr()/M() lookup by the same
    name gets the textured one. No-op for sets that are not on disk."""
    if not os.path.isdir(TEXDIR):
        return
    tex_pbr('MAT_WetDeck', 'rubber_tiles', 1.2, tint=(0.06, 0.07, 0.075), tint_amount=0.8, rough_mul=0.45, coat=0.35, grime=0.3)
    tex_pbr('MAT_Concrete', 'concrete_floor_02', 0.3, tint=(0.46, 0.45, 0.42), tint_amount=0.5, grime=0.3)
    tex_pbr('MAT_Asphalt', 'asphalt_02', 0.25, tint=(0.12, 0.12, 0.125), tint_amount=0.5)
    tex_pbr('MAT_Steel', 'Metal009', 1.0, rough_mul=1.0)
    tex_pbr('MAT_Rust', 'rust_coarse_01', 0.8)
    tex_pbr('MAT_Rubber', 'Rubber004', 2.0, tint=(0.03, 0.03, 0.032), tint_amount=0.8)
    tex_pbr('MAT_PaintWhite', 'PaintedMetal004', 0.6, tint=(0.8, 0.81, 0.79), tint_amount=0.85, metal=0.1, grime=0.35, paint_mask=True)
    tex_pbr('MAT_PaintBlue', 'PaintedMetal004', 0.6, tint=(0.04, 0.12, 0.33), tint_amount=0.85, metal=0.1, grime=0.3, paint_mask=True)
    tex_pbr('MAT_PaintRed', 'PaintedMetal004', 0.6, tint=(0.3, 0.05, 0.04), tint_amount=0.85, metal=0.1, grime=0.3, paint_mask=True)
    tex_pbr('MAT_CraneWhite', 'rusty_metal_02', 0.6, tint=(0.82, 0.83, 0.82), tint_amount=0.7, metal=0.15, grime=0.15)
    tex_pbr('MAT_CraneBlue', 'PaintedMetal004', 0.3, tint=(0.04, 0.17, 0.42), tint_amount=0.85, metal=0.1, grime=0.3, paint_mask=True)
    tex_pbr('MAT_ContainerPaint', 'container_side', 0.33, attr='col', tint_amount=0.88, metal=0.2, grime=0.2)
    tex_pbr('MAT_QuayFace', 'concrete_floor_02', 0.2, tint=(0.4, 0.39, 0.36), tint_amount=0.5, grime=0.5)
    tex_pbr('MAT_InsulPanel', 'corrugated_iron_02', 0.5, tint=(0.88, 0.89, 0.9), tint_amount=0.9, metal=0.05, bump=0.25)
    for nm, c in (('MAT_OilskinOrange', (0.85, 0.32, 0.07)), ('MAT_OilskinYellow', (0.82, 0.6, 0.12)),
                  ('MAT_ClothNavy', (0.05, 0.07, 0.13)), ('MAT_ClothWhite', (0.84, 0.85, 0.86)), ('MAT_ClothKhaki', (0.33, 0.28, 0.19)),
                  ('MAT_ClothGrey', (0.3, 0.31, 0.32)), ('MAT_ClothBlue', (0.13, 0.22, 0.38)), ('MAT_ClothRed', (0.38, 0.09, 0.07)),
                  ('MAT_ClothGreen', (0.15, 0.24, 0.12))):
        tex_pbr(nm, 'Fabric030', 4.0, tint=c, tint_amount=0.95, rough_mul=0.9, metal=0.0, bump=0.35,
                coat=0.25 if 'Oilskin' in nm else 0.0, grime=0.3 if 'Oilskin' in nm else 0.1)
    for nm, c in (('MAT_CrateBlue', (0.2, 0.31, 0.44)), ('MAT_CrateRed', (0.45, 0.16, 0.11)), ('MAT_CrateWhite', (0.72, 0.74, 0.72)),
                  ('MAT_CrateYellow', (0.62, 0.52, 0.25))):
        tex_pbr(nm, 'Plastic006', 3.0, tint=c, tint_amount=0.9, metal=0.0, grime=0.4)


def M():
    """The shared material set (MAT_* in ASSET_LIBRARY.md)."""
    textured_overrides()
    return {
        'paint_white': pbr('MAT_PaintWhite', (0.82, 0.83, 0.81), 0.38, grime=0.35, var=0.08),
        'paint_blue': pbr('MAT_PaintBlue', (0.03, 0.12, 0.38), 0.35, grime=0.25),
        'paint_red': pbr('MAT_PaintRed', (0.32, 0.04, 0.03), 0.5, grime=0.3),
        'steel': pbr('MAT_Steel', (0.55, 0.56, 0.57), 0.35, 0.9, grime=0.25),
        'stainless': pbr('MAT_Stainless', (0.78, 0.79, 0.8), 0.18, 1.0, var=0.05, bump=0.02, rough_var=0.06),
        'rust': pbr('MAT_Rust', (0.28, 0.12, 0.05), 0.8, grime=0.4),
        'rubber': pbr('MAT_Rubber', (0.025, 0.025, 0.027), 0.75, var=0.1),
        'glass': pbr('MAT_Glass', (0.05, 0.08, 0.1), 0.04, 0.0, var=0.0, bump=0.0, coat=0.0),
        'wetdeck': pbr('MAT_WetDeck', (0.05, 0.06, 0.065), 0.2, 0.0, var=0.35, bump=0.35, scale=2.5, grime=0.5, coat=0.35),
        'concrete': pbr('MAT_Concrete', (0.4, 0.395, 0.375), 0.85, var=0.18, bump=0.25, scale=0.8, grime=0.35),
        'asphalt': pbr('MAT_Asphalt', (0.11, 0.11, 0.115), 0.85, var=0.2, bump=0.25, scale=0.6, grime=0.2),
        'rope': pbr('MAT_Rope', (0.32, 0.27, 0.18), 0.9, var=0.25),
        'rope_green': pbr('MAT_RopeGreen', (0.06, 0.2, 0.15), 0.85, var=0.25),
        'net': pbr('MAT_Net', (0.07, 0.11, 0.09), 0.8, var=0.35, bump=0.0, grime=0.3),
        'float_yellow': pbr('MAT_FloatYellow', (0.72, 0.36, 0.1), 0.5, var=0.25, coat=0.2, grime=0.45, scale=6),
        'oilskin_orange': pbr('MAT_OilskinOrange', (0.62, 0.22, 0.07), 0.45, var=0.25, coat=0.25, bump=0.25, scale=9, grime=0.45),
        'oilskin_yellow': pbr('MAT_OilskinYellow', (0.62, 0.45, 0.1), 0.45, var=0.25, coat=0.25, bump=0.25, scale=9, grime=0.45),
        'glove_blue': pbr('MAT_NitrileGlove', (0.08, 0.3, 0.75), 0.35, var=0.05, coat=0.3),
        'glove_teal': pbr('MAT_GloveTeal', (0.08, 0.26, 0.28), 0.45, var=0.15, coat=0.2, grime=0.3),
        'boot_white': pbr('MAT_BootWhite', (0.78, 0.78, 0.75), 0.35, var=0.1, coat=0.3, grime=0.3),
        'boot_yellow': pbr('MAT_BootYellow', (0.6, 0.45, 0.12), 0.4, coat=0.2, grime=0.4),
        'boot_black': pbr('MAT_BootBlack', (0.03, 0.03, 0.03), 0.4, coat=0.3),
        'cloth_white': pbr('MAT_ClothWhite', (0.86, 0.87, 0.88), 0.8, var=0.06, bump=0.05, scale=8),
        'cloth_navy': pbr('MAT_ClothNavy', (0.04, 0.06, 0.13), 0.8, var=0.12, scale=8),
        'cloth_khaki': pbr('MAT_ClothKhaki', (0.35, 0.3, 0.2), 0.85, var=0.12, scale=8),
        'cloth_grey': pbr('MAT_ClothGrey', (0.3, 0.31, 0.32), 0.85, var=0.12, scale=8),
        'cloth_blue': pbr('MAT_ClothBlue', (0.12, 0.22, 0.42), 0.85, var=0.12, scale=8),
        'cloth_check': pbr('MAT_ClothRed', (0.45, 0.08, 0.06), 0.85, var=0.15, scale=8),
        'cloth_green': pbr('MAT_ClothGreen', (0.15, 0.25, 0.12), 0.85, var=0.15, scale=8),
        'cap_grey': pbr('MAT_CapGrey', (0.45, 0.46, 0.47), 0.8, var=0.1, scale=8),
        'apron': pbr('MAT_Apron', (0.9, 0.9, 0.9), 0.35, var=0.04, coat=0.3),
        'apron_blue': pbr('MAT_ApronBlue', (0.2, 0.4, 0.75), 0.35, var=0.04, coat=0.3),
        'haircap': pbr('MAT_HairCap', (0.88, 0.9, 0.93), 0.9, var=0.05, scale=12),
        'mask': pbr('MAT_Mask', (0.55, 0.75, 0.88), 0.9, var=0.04, scale=12),
        'hivis': pbr('MAT_HiVis', (0.75, 0.9, 0.05), 0.6, var=0.05, emission=(0.2, 0.25, 0.0), estrength=0.15),
        'hivis_orange': pbr('MAT_HiVisOrange', (0.95, 0.35, 0.02), 0.6, var=0.05),
        'reflect': pbr('MAT_ReflectStripe', (0.8, 0.8, 0.8), 0.25, 0.8, var=0.0),
        'hardhat': pbr('MAT_HardHat', (0.92, 0.92, 0.9), 0.3, var=0.05, coat=0.5),
        'crate_blue': pbr('MAT_CrateBlue', (0.1, 0.17, 0.27), 0.5, var=0.2, grime=0.45, scale=5),
        'crate_red': pbr('MAT_CrateRed', (0.3, 0.1, 0.08), 0.5, var=0.2, grime=0.45, scale=5),
        'crate_white': pbr('MAT_CrateWhite', (0.62, 0.64, 0.63), 0.5, var=0.15, grime=0.45, scale=5),
        'crate_yellow': pbr('MAT_CrateYellow', (0.5, 0.42, 0.18), 0.5, var=0.2, grime=0.45, scale=5),
        'ice': ice_mat(),
        'water_sea': water_mat('MAT_Water_Sea', (0.004, 0.035, 0.085)),
        'water_harbour': water_mat('MAT_Water_Harbour', (0.01, 0.06, 0.06)),
        'water_clear': pbr('MAT_WaterSheet', (0.8, 0.88, 0.92), 0.15, var=0.1, bump=0.3, ior=1.33, alpha=0.55, coat=0.5),
        'skin': [pbr('MAT_Skin1', (0.36, 0.2, 0.12), 0.5, var=0.08, sss=0.15, scale=10),
                 pbr('MAT_Skin2', (0.26, 0.15, 0.09), 0.5, var=0.08, sss=0.15, scale=10),
                 pbr('MAT_Skin3', (0.45, 0.28, 0.17), 0.5, var=0.08, sss=0.15, scale=10)],
        'hair': pbr('MAT_Hair', (0.02, 0.015, 0.012), 0.6, var=0.1),
        'lamp': pbr('MAT_LampWhite', (1, 1, 1), 0.5, emission=(1.0, 0.98, 0.95), estrength=8.0, var=0.0, bump=0.0),
        'lamp_red': pbr('MAT_LampRed', (1, 0.1, 0.05), 0.5, emission=(1.0, 0.05, 0.02), estrength=20.0, var=0, bump=0),
        'lamp_amber': pbr('MAT_LampAmber', (1, 0.5, 0.05), 0.5, emission=(1.0, 0.45, 0.02), estrength=20.0, var=0, bump=0),
        'panel_white': pbr('MAT_PanelWhite', (0.88, 0.89, 0.9), 0.35, var=0.03, bump=0.02, scale=1.5),
        'epoxy': pbr('MAT_EpoxyFloor', (0.45, 0.55, 0.6), 0.15, var=0.06, bump=0.03, scale=1.0, coat=0.5),
        'plastic_black': pbr('MAT_PlasticBlack', (0.03, 0.03, 0.035), 0.45),
        'wood': pbr('MAT_Wood', (0.35, 0.22, 0.12), 0.7, var=0.25, bump=0.2, scale=6),
        'carton': pbr('MAT_Carton', (0.62, 0.48, 0.32), 0.85, var=0.08, bump=0.05, scale=6),
        'label': pbr('MAT_LabelBlank', (0.95, 0.95, 0.94), 0.6, var=0.0, bump=0.0),
        'foliage': pbr('MAT_Foliage', (0.08, 0.2, 0.05), 0.6, var=0.35, bump=0.3, scale=5, sss=0.1),
        'trunk': pbr('MAT_Trunk', (0.25, 0.2, 0.15), 0.85, var=0.2, bump=0.4, scale=6),
        'earth': pbr('MAT_Earth', (0.36, 0.28, 0.19), 0.9, var=0.25, bump=0.4, scale=0.5, grime=0.3),
        'grass': pbr('MAT_Grass', (0.13, 0.22, 0.06), 0.8, var=0.35, bump=0.3, scale=0.5),
    }


def ice_mat():
    if 'MAT_Ice' in bpy.data.materials:
        return bpy.data.materials['MAT_Ice']
    m = pbr('MAT_Ice', (0.92, 0.96, 1.0), 0.12, var=0.05, bump=0.6, scale=12, sss=0.0, transmission=0.35, ior=1.31)
    return m


def water_mat(name, deep):
    """Sea/harbour water: dark body, low roughness so the sky reflects, white foam from the Ocean modifier's
    foam attribute, fine bump for chop."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    p.inputs['Base Color'].default_value = (*deep, 1)
    p.inputs['Roughness'].default_value = 0.04
    p.inputs['IOR'].default_value = 1.33
    p.inputs['Specular IOR Level'].default_value = 0.5
    a = _node(nt, 'ShaderNodeAttribute', (-800, 200))
    a.attribute_name = 'foam'
    a.attribute_type = 'GEOMETRY'
    n = _node(nt, 'ShaderNodeTexNoise', (-800, -100))
    n.inputs['Scale'].default_value = 3.0
    n.inputs['Detail'].default_value = 8
    mr = _node(nt, 'ShaderNodeMapRange', (-500, 200))
    mr.inputs['From Min'].default_value = 0.25
    mr.inputs['From Max'].default_value = 0.9
    l.new(_sock(a, 'Factor', out=True), mr.inputs['Value'])
    mul = _node(nt, 'ShaderNodeMath', (-300, 200))
    mul.operation = 'MULTIPLY'
    l.new(mr.outputs[0], mul.inputs[0])
    l.new(_sock(n, 'Factor', out=True), mul.inputs[1])
    col = mixrgb(nt, mul.outputs[0], deep, (0.85, 0.9, 0.92), loc=(-100, 300))
    l.new(col, p.inputs['Base Color'])
    rr = _node(nt, 'ShaderNodeMapRange', (-100, 0))
    rr.inputs['To Min'].default_value = 0.03
    rr.inputs['To Max'].default_value = 0.7
    l.new(mul.outputs[0], rr.inputs['Value'])
    l.new(rr.outputs[0], p.inputs['Roughness'])
    n2 = _node(nt, 'ShaderNodeTexNoise', (-500, -300))
    n2.inputs['Scale'].default_value = 40.0
    n2.inputs['Detail'].default_value = 4
    tc = _node(nt, 'ShaderNodeTexCoord', (-1000, -300))
    l.new(_sock(tc, 'Object', out=True), n2.inputs['Vector'])
    b = _node(nt, 'ShaderNodeBump', (100, -300))
    b.inputs['Strength'].default_value = 0.25
    l.new(_sock(n2, 'Factor', out=True), b.inputs['Height'])
    l.new(b.outputs[0], p.inputs['Normal'])
    return m


def mat_color(name, color, rough=0.5, metal=0.0, **kw):
    return pbr(name, color, rough, metal, **kw)


# ---------------------------------------------------------------- world, sun, camera
def sky(sun_elev=48, sun_rot=135, strength=0.2, clouds=0.55, sun_strength=3.5, haze=0.4):
    """Physical sky (multiple scattering) + procedural cumulus layer in the background + a matching sun lamp.
    Returns the sun object (named 'Sun' for boundary_camera.py)."""
    s = bpy.context.scene
    w = bpy.data.worlds.get('WORLD_Day') or bpy.data.worlds.new('WORLD_Day')
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    l = nt.links
    out = _node(nt, 'ShaderNodeOutputWorld', (900, 0))
    bg = _node(nt, 'ShaderNodeBackground', (700, 0))
    bg.inputs['Strength'].default_value = strength
    l.new(bg.outputs[0], out.inputs[0])
    sk = _node(nt, 'ShaderNodeTexSky', (0, 200))
    sk.sky_type = 'MULTIPLE_SCATTERING'
    sk.sun_elevation = math.radians(sun_elev)
    sk.sun_rotation = math.radians(sun_rot)
    for attr, val in (('air_density', 1.0), ('aerosol_density', haze), ('ozone_density', 1.0), ('altitude', 50.0),
                      ('sun_intensity', 0.6), ('sun_disc', True)):
        if hasattr(sk, attr):
            setattr(sk, attr, val)
    col = sk.outputs[0]
    if clouds > 0:
        tc = _node(nt, 'ShaderNodeTexCoord', (-900, -200))
        # direction on the sky dome; squash vertical so clouds read as a layer
        sep = _node(nt, 'ShaderNodeSeparateXYZ', (-700, -200))
        l.new(_sock(tc, 'Generated', out=True), sep.inputs[0])
        div = _node(nt, 'ShaderNodeMath', (-500, -350))
        div.operation = 'DIVIDE'
        mx = _node(nt, 'ShaderNodeMath', (-650, -400))
        mx.operation = 'MAXIMUM'
        mx.inputs[1].default_value = 0.04
        l.new(sep.outputs[2], mx.inputs[0])
        cx = _node(nt, 'ShaderNodeCombineXYZ', (-300, -250))
        dx = _node(nt, 'ShaderNodeMath', (-500, -200))
        dx.operation = 'DIVIDE'
        l.new(sep.outputs[0], dx.inputs[0])
        l.new(mx.outputs[0], dx.inputs[1])
        l.new(sep.outputs[1], div.inputs[0])
        l.new(mx.outputs[0], div.inputs[1])
        l.new(dx.outputs[0], cx.inputs[0])
        l.new(div.outputs[0], cx.inputs[1])
        nz = _node(nt, 'ShaderNodeTexNoise', (-100, -250))
        nz.noise_dimensions = '3D'
        nz.inputs['Scale'].default_value = 0.9
        nz.inputs['Detail'].default_value = 10
        nz.inputs['Roughness'].default_value = 0.62
        l.new(cx.outputs[0], nz.inputs['Vector'])
        ramp = _node(nt, 'ShaderNodeValToRGB', (100, -250))
        ramp.color_ramp.elements[0].position = 1.0 - clouds * 0.85
        ramp.color_ramp.elements[1].position = min(1.0, 1.0 - clouds * 0.85 + 0.2)
        l.new(_sock(nz, 'Factor', out=True), ramp.inputs[0])
        # fade clouds near the horizon and toward the zenith
        hz = _node(nt, 'ShaderNodeMapRange', (100, -450))
        hz.inputs['From Min'].default_value = 0.02
        hz.inputs['From Max'].default_value = 0.15
        l.new(sep.outputs[2], hz.inputs['Value'])
        f = _node(nt, 'ShaderNodeMath', (300, -300))
        f.operation = 'MULTIPLY'
        l.new(ramp.outputs[0], f.inputs[0])
        l.new(hz.outputs[0], f.inputs[1])
        f2 = _node(nt, 'ShaderNodeMath', (400, -300))
        f2.operation = 'MULTIPLY'
        f2.inputs[1].default_value = 0.92
        l.new(f.outputs[0], f2.inputs[0])
        # cloud colour: lit white with a slightly darker underside
        cloudcol = mixrgb(nt, _sock(nz, 'Factor', out=True), (1.6, 1.6, 1.62), (0.95, 0.98, 1.05), loc=(300, -100))
        col = mixrgb(nt, f2.outputs[0], col, cloudcol, loc=(500, 100))
    l.new(col, bg.inputs['Color'])
    sun = bpy.data.objects.get('Sun')
    if sun is None:
        sd = bpy.data.lights.new('Sun', 'SUN')
        sun = bpy.data.objects.new('Sun', sd)
        bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = sun_strength
    sun.data.angle = math.radians(1.2)
    sun.data.color = (1.0, 0.97, 0.92)
    # sky texture: sun_rotation 0 = +X? Blender sky: rotation measured from -Y toward +X; light points opposite
    sun.rotation_euler = Euler((math.radians(90 - sun_elev), 0, math.radians(sun_rot) + math.pi / 2), 'XYZ')
    if hasattr(sun.data, 'use_shadow'):
        sun.data.use_shadow = True
    return sun


CC0 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets-src', 'cc0')


def hdri(name='kloofendal_48d_partly_cloudy_puresky_4k', strength=1.0, rot=0.0, sun_strength=4.0, sun_color=(1.0, 0.96, 0.9)):
    """Poly Haven HDRI (CC0, assets-src/cc0/hdri/) as the world, rotated by rot degrees, plus a sun lamp ('Sun')
    aimed from the HDRI's brightest pixel so shadows match the sky. Falls back to sky() if the file is missing."""
    path = os.path.join(CC0, 'hdri', name + ('' if name.endswith('.hdr') else '.hdr'))
    if not os.path.exists(path):
        return sky()
    import numpy as np
    s = bpy.context.scene
    w = bpy.data.worlds.get('WORLD_Day') or bpy.data.worlds.new('WORLD_Day')
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    l = nt.links
    out = _node(nt, 'ShaderNodeOutputWorld', (600, 0))
    bg = _node(nt, 'ShaderNodeBackground', (400, 0))
    bg.inputs['Strength'].default_value = strength
    env = _node(nt, 'ShaderNodeTexEnvironment', (100, 0))
    img = bpy.data.images.load(path, check_existing=True)
    env.image = img
    mp = _node(nt, 'ShaderNodeMapping', (-150, 0))
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot))
    tc = _node(nt, 'ShaderNodeTexCoord', (-350, 0))
    l.new(_sock(tc, 'Generated', out=True), mp.inputs['Vector'])
    l.new(mp.outputs[0], env.inputs['Vector'])
    l.new(env.outputs['Color'], bg.inputs['Color'])
    l.new(bg.outputs[0], out.inputs[0])
    W, H = img.size
    px = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    lum = px.reshape(H, W, 4)[:, :, :3].sum(axis=2)
    iy, ix = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (ix + 0.5) / W, (iy + 0.5) / H
    phi, th = (u - 0.5) * 2 * math.pi, (v - 0.5) * math.pi
    d = Vector((-math.cos(th) * math.cos(phi), math.cos(th) * math.sin(phi), math.sin(th)))
    d.rotate(Euler((0, 0, math.radians(rot))))
    sun = bpy.data.objects.get('Sun')
    if sun is None:
        sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
        s.collection.objects.link(sun)
    sun.data.energy = sun_strength
    sun.data.angle = math.radians(1.0)
    sun.data.color = sun_color
    sun.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    print('HDRI', name, 'sun elevation %.1f azimuth %.1f' % (math.degrees(th), math.degrees(math.atan2(d.y, d.x))))
    return sun


def camera(name='Camera', lens=35, loc=(0, 0, 2), target=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 5000
    c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = loc
    bpy.context.scene.camera = c
    if target is not None:
        look(c, loc, target)
    return c


def look_rot(loc, target, roll=0.0):
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat('-Z', 'Y')
    e = q.to_euler()
    if roll:
        e.rotate_axis('Z', math.radians(roll))
    return e


def look(o, loc, target):
    o.location = loc
    o.rotation_euler = look_rot(loc, target)


def cam_path(cam, keys, focus=None):
    """keys: [(frame, loc, target, lens?)]; keys location/rotation (Bezier, auto-clamped) with Euler unwrapping.
    focus: optional [(frame, distance)] for DOF focus."""
    prev = None
    for k in keys:
        f, loc, tgt = k[0], k[1], k[2]
        e = look_rot(loc, tgt)
        if prev is not None:
            e.make_compatible(prev)
        prev = e
        cam.location = loc
        cam.rotation_euler = e
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        if len(k) > 3 and k[3]:
            cam.data.lens = k[3]
            cam.data.keyframe_insert('lens', frame=f)
    if focus:
        cam.data.dof.use_dof = True
        for f, d in focus:
            cam.data.dof.focus_distance = d
            cam.data.dof.keyframe_insert('focus_distance', frame=f)
    smooth_keys(cam)
    if cam.data.animation_data:
        smooth_keys(cam.data)


def smooth_keys(idb, interp='BEZIER'):
    ad = idb.animation_data
    if not ad or not ad.action:
        return
    for fc in fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.update()


def fcurves(action):
    """Blender 5 layered actions: collect fcurves from every channelbag."""
    out = []
    if hasattr(action, 'fcurves') and len(getattr(action, 'fcurves', [])):
        return list(action.fcurves)
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for cb in getattr(strip, 'channelbags', []):
                out.extend(cb.fcurves)
    return out


def linear_keys(idb):
    ad = idb.animation_data
    if ad and ad.action:
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def key_vis(o, frame_on, frame_off=None):
    """Show an object (render + viewport) from frame_on (until frame_off)."""
    for f, v in ((frame_on - 1, True), (frame_on, False)) + (((frame_off - 1, False), (frame_off, True)) if frame_off else ()):
        o.hide_render = v
        o.hide_viewport = v
        o.keyframe_insert('hide_render', frame=f)
        o.keyframe_insert('hide_viewport', frame=f)
    ad = o.animation_data
    if ad and ad.action:
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'


# ---------------------------------------------------------------- people
OUTFITS = {
    # part -> material key; extras list
    'fisherman_o': dict(top='oilskin_orange', bottom='oilskin_orange', hands='glove_teal', feet='boot_yellow',
                        extras=['cap', 'hood']),
    'fisherman_y': dict(top='oilskin_yellow', bottom='oilskin_yellow', hands='glove_teal', feet='boot_white',
                        extras=['cap']),
    'fisherman_b': dict(top='cloth_grey', bottom='oilskin_yellow', hands='glove_blue', feet='boot_yellow',
                        extras=['cap', 'bib']),
    'plant': dict(top='cloth_white', bottom='cloth_white', hands='glove_blue', feet='boot_white',
                  extras=['haircap', 'mask', 'apron']),
    'plant_blue': dict(top='cloth_white', bottom='cloth_white', hands='glove_blue', feet='boot_white',
                       extras=['haircap', 'mask', 'apron_blue']),
    'qc': dict(top='cloth_white', bottom='cloth_navy', hands='glove_blue', feet='boot_white',
               extras=['haircap', 'mask', 'coat']),
    'cold': dict(top='cloth_navy', bottom='cloth_navy', hands='glove_blue', feet='boot_black',
                 extras=['haircap', 'mask', 'jacket']),
    'farm': dict(top='cloth_check', bottom='cloth_khaki', hands='glove_blue', feet='boot_black', extras=['cap']),
    'farm2': dict(top='cloth_blue', bottom='cloth_navy', hands='glove_blue', feet='boot_black', extras=['cap']),
    'farm3': dict(top='cloth_green', bottom='cloth_khaki', hands='skin', feet='boot_black', extras=[]),
    'driver': dict(top='cloth_blue', bottom='cloth_navy', hands='skin', feet='boot_black', extras=['vest']),
    'port': dict(top='cloth_navy', bottom='cloth_navy', hands='glove_blue', feet='boot_black',
                 extras=['vest', 'hardhat']),
    'port_o': dict(top='hivis_orange', bottom='cloth_navy', hands='glove_blue', feet='boot_black',
                   extras=['vest', 'hardhat']),
}

_PART_MESH = {}


def _part_mesh(key, fn):
    if key not in _PART_MESH:
        _PART_MESH[key] = fn()
    return _PART_MESH[key]


def _limb(name, r1, r2, length):
    """Tapered capsule hanging down from the joint (pivot at top)."""
    bm = bmesh.new()
    rings = 10
    seg = 12
    vs = []
    for i in range(rings + 1):
        t = i / rings
        z = -t * length
        r = r1 + (r2 - r1) * t
        # round the ends
        if i == 0:
            r *= 0.75
        if i == rings:
            r *= 0.75
        vs.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), r * 0.92 * math.sin(2 * math.pi * j / seg), z))
                   for j in range(seg)])
    for i in range(rings):
        for j in range(seg):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % seg], vs[i][(j + 1) % seg]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[-1])
    return bm_to_mesh(bm, name, smooth=True)


def _torso_mesh(name, w, d, h, waist=0.8):
    """Torso: rounded box tapering to the waist, pivot at the bottom."""
    bm = bmesh.new()
    seg = 16
    rings = 8
    vs = []
    for i in range(rings + 1):
        t = i / rings
        z = t * h
        s = waist + (1 - waist) * math.sin(min(1, t * 1.3) * math.pi / 2)
        if t > 0.85:
            s *= 1 - (t - 0.85) * 1.6
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            cx, cy = math.cos(a), math.sin(a)
            # superellipse for a boxy chest
            e = 0.6
            x = math.copysign(abs(cx) ** e, cx) * d / 2 * s
            y = math.copysign(abs(cy) ** e, cy) * w / 2 * s
            ring.append(bm.verts.new((x, y, z)))
        vs.append(ring)
    for i in range(rings):
        for j in range(seg):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][(j + 1) % seg], vs[i][(j + 1) % seg]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[-1])
    return bm_to_mesh(bm, name, smooth=True)




# ---- skeleton (standing, facing +X, metres, feet on z=0) -> one continuous skin-modifier body, armature, auto weights
SKEL = {
    'pelvis': ((0.0, 0.0, 0.95), (0.15, 0.19)), 'waist': ((0.0, 0.0, 1.12), (0.14, 0.17)),
    'chest': ((0.0, 0.0, 1.32), (0.15, 0.2)), 'neckb': ((0.0, 0.0, 1.49), (0.065, 0.065)),
    'head': ((0.015, 0.0, 1.62), (0.095, 0.085)), 'headt': ((0.0, 0.0, 1.73), (0.06, 0.06)),
    'sh_L': ((0.0, 0.2, 1.43), (0.075, 0.075)), 'el_L': ((-0.02, 0.22, 1.15), (0.056, 0.056)),
    'wr_L': ((0.02, 0.23, 0.9), (0.04, 0.036)), 'ht_L': ((0.04, 0.23, 0.8), (0.036, 0.024)),
    'sh_R': ((0.0, -0.2, 1.43), (0.075, 0.075)), 'el_R': ((-0.02, -0.22, 1.15), (0.056, 0.056)),
    'wr_R': ((0.02, -0.23, 0.9), (0.04, 0.036)), 'ht_R': ((0.04, -0.23, 0.8), (0.036, 0.024)),
    'hp_L': ((0.0, 0.1, 0.9), (0.105, 0.105)), 'kn_L': ((0.025, 0.11, 0.5), (0.07, 0.07)),
    'an_L': ((0.0, 0.11, 0.09), (0.05, 0.05)), 'to_L': ((0.19, 0.11, 0.04), (0.045, 0.055)),
    'hp_R': ((0.0, -0.1, 0.9), (0.105, 0.105)), 'kn_R': ((0.025, -0.11, 0.5), (0.07, 0.07)),
    'an_R': ((0.0, -0.11, 0.09), (0.05, 0.05)), 'to_R': ((0.19, -0.11, 0.04), (0.045, 0.055)),
}
SKEL_EDGES = [('pelvis', 'waist'), ('waist', 'chest'), ('chest', 'neckb'), ('neckb', 'head'), ('head', 'headt')] + \
    [e for s in 'LR' for e in (('chest', f'sh_{s}'), (f'sh_{s}', f'el_{s}'), (f'el_{s}', f'wr_{s}'), (f'wr_{s}', f'ht_{s}'),
                               ('pelvis', f'hp_{s}'), (f'hp_{s}', f'kn_{s}'), (f'kn_{s}', f'an_{s}'), (f'an_{s}', f'to_{s}'))]
# bone name -> (head point, tail point, parent, kind)  kind: down / up / fwd (roll convention used by pose())
BONES = {
    'hips': ('pelvis', 'waist', None, 'up'), 'spine': ('waist', 'neckb', 'hips', 'up'), 'neck': ('neckb', 'headt', 'spine', 'up'),
}
for _s in 'LR':
    BONES.update({f'sh_{_s}': (f'sh_{_s}', f'el_{_s}', 'spine', 'down'), f'el_{_s}': (f'el_{_s}', f'wr_{_s}', f'sh_{_s}', 'down'),
                  f'wr_{_s}': (f'wr_{_s}', f'ht_{_s}', f'el_{_s}', 'down'), f'hp_{_s}': (f'hp_{_s}', f'kn_{_s}', 'hips', 'down'),
                  f'kn_{_s}': (f'kn_{_s}', f'an_{_s}', f'hp_{_s}', 'down'), f'an_{_s}': (f'an_{_s}', f'to_{_s}', f'kn_{_s}', 'fwd')})
JOINTS = list(BONES)
# skeleton point -> clothing zone (0 top, 1 bottom, 2 skin, 3 hands, 4 feet)
ZONE = {'pelvis': 1, 'waist': 0, 'chest': 0, 'neckb': 2, 'head': 2, 'headt': 2}
for _s in 'LR':
    ZONE.update({f'sh_{_s}': 0, f'el_{_s}': 0, f'wr_{_s}': 3, f'ht_{_s}': 3, f'hp_{_s}': 1, f'kn_{_s}': 1, f'an_{_s}': 4,
                 f'to_{_s}': 4})
_BODY = {}


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
    return (a + ab * t - p).length, t


HBM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets-src', 'cc0', 'human-base-meshes',
                   'human-base-meshes-bundle-v1.4.1', 'human_base_meshes_bundle.blend')


def _hbm_mesh(gender='male'):
    """Blender Foundation 'Human Base Meshes' (CC0) realistic body, base level, turned to face +X, feet on z=0,
    scaled to 1.72 m; eyes joined. Returns (mesh, skeleton points) or None if the bundle is not on disk."""
    if not os.path.exists(HBM):
        return None
    name = f'GEO-body_{gender}_realistic'
    with bpy.data.libraries.load(HBM, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == name]
    objs = [o for o in dst.objects if o is not None]
    body = [o for o in objs if o.name.startswith(name) and '.eye' not in o.name][0]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    for m in list(body.modifiers):
        body.modifiers.remove(m)
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for o in objs:
        bpy.data.objects.remove(o)
    xs = [v.co.x for v in bm.verts]
    zmin = min(v.co.z for v in bm.verts)
    H = max(v.co.z for v in bm.verts) - zmin
    cx = (min(xs) + max(xs)) / 2
    s = 1.72 / H
    T = Matrix.Diagonal((s, s, s, 1)) @ Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Translation((-cx, 0, -zmin))
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    me = bpy.data.meshes.new(f'BODY_hbm_{gender}')
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    vs = [v.co for v in me.vertices]
    Hn = 1.72

    def centroid(sel):
        pts = [v for v in vs if sel(v)]
        return sum(pts, Vector()) / max(1, len(pts))

    skel = {}
    for side, sg in (('L', 1), ('R', -1)):
        leg = lambda v, z0, z1: z0 * Hn < v.z < z1 * Hn and sg * v.y > 0.01
        skel[f'hp_{side}'] = centroid(lambda v: leg(v, 0.46, 0.48)) * 1.0
        skel[f'hp_{side}'].x = 0.0
        skel[f'kn_{side}'] = centroid(lambda v: leg(v, 0.27, 0.29))
        skel[f'an_{side}'] = centroid(lambda v: leg(v, 0.045, 0.06))
        foot = [v for v in vs if v.z < 0.05 * Hn and sg * v.y > 0.01]
        skel[f'to_{side}'] = max(foot, key=lambda v: v.x).copy()
        skel[f'to_{side}'].z = 0.04
        tip = max((v for v in vs if v.z > 0.35 * Hn), key=lambda v: sg * v.y).copy()
        sh = Vector((-0.01, sg * 0.105 * Hn, 0.815 * Hn))
        skel[f'sh_{side}'] = sh
        skel[f'el_{side}'] = sh + (tip - sh) * 0.46
        skel[f'wr_{side}'] = sh + (tip - sh) * 0.84
        skel[f'ht_{side}'] = tip
    skel.update({'pelvis': Vector((0, 0, 0.53 * Hn)), 'waist': Vector((0, 0, 0.62 * Hn)), 'chest': Vector((0, 0, 0.73 * Hn)),
                 'neckb': Vector((-0.01, 0, 0.845 * Hn)), 'head': Vector((0.01, 0, 0.935 * Hn)), 'headt': Vector((0, 0, 1.0 * Hn))})
    return me, skel


def _skin_mesh(bulk, build):
    names = list(SKEL)
    bm = bmesh.new()
    vs = {}
    for n in names:
        p, r = SKEL[n]
        vs[n] = bm.verts.new((p[0], p[1] * (build if n[:2] in ('sh', 'el', 'wr', 'ht') else 1.0), p[2]))
    for a, b in SKEL_EDGES:
        bm.edges.new((vs[a], vs[b]))
    me = bpy.data.meshes.new('BODY_skel')
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new('BODY_tmp', me)
    bpy.context.scene.collection.objects.link(o)
    sk = o.modifiers.new('Skin', 'SKIN')
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.6
    for i, n in enumerate(names):
        r = SKEL[n][1]
        limb = n[:2] in ('sh', 'el', 'wr', 'hp', 'kn')
        k = bulk if (limb or n in ('waist', 'chest', 'pelvis')) else 1.0
        rv = me.skin_vertices[0].data[i]
        rv.radius = (r[0] * k * (build if n in ('chest', 'waist', 'pelvis') else 1.0), r[1] * k * build)
        rv.use_root = (n == 'pelvis')
    ss = o.modifiers.new('Sub', 'SUBSURF')
    ss.levels = 2
    dg = bpy.context.evaluated_depsgraph_get()
    body = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o)
    bpy.data.meshes.remove(me)
    return body, {n: Vector(SKEL[n][0]) for n in names}


def _body(bulk=1.0, build=1.0, gender='male'):
    """Rigged base body for one (bulk, build, gender) variant: returns (mesh, armature data, skeleton points).
    Uses the CC0 Human Base Meshes body when the bundle is on disk, else a skin-modifier body. Built once, shared."""
    key = (round(bulk, 2), round(build, 2), gender)
    if key in _BODY:
        return _BODY[key]
    got = _hbm_mesh(gender)
    if got:
        body, skel = got
        if build != 1.0:
            body.transform(Matrix.Diagonal((build, build, 1.0, 1.0)))
            skel = {n: Vector((p.x * build, p.y * build, p.z)) for n, p in skel.items()}
    else:
        body, skel = _skin_mesh(bulk, build)
    body.name = f'BODY_{key[0]}_{key[1]}_{gender}'
    ad = bpy.data.armatures.new(f'RIG_{key[0]}_{key[1]}_{gender}')
    ao = bpy.data.objects.new('RIG_tmp', ad)
    bpy.context.scene.collection.objects.link(ao)
    bo = bpy.data.objects.new('BODY_tmp2', body)
    bpy.context.scene.collection.objects.link(bo)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    ao.select_set(True)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, (h, t, par, kind) in BONES.items():
        eb = ad.edit_bones.new(bn)
        eb.head = skel[h]
        eb.tail = skel[t]
        if par:
            eb.parent = ad.edit_bones[par]
        eb.align_roll({'down': (0, 1, 0), 'up': (0, -1, 0), 'fwd': (0, 0, 1)}[kind])
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    bo.select_set(True)
    ao.select_set(True)
    bpy.context.view_layer.objects.active = ao
    with bpy.context.temp_override(active_object=ao, object=ao, selected_objects=[bo, ao], selected_editable_objects=[bo, ao]):
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    bo.select_set(False)
    ao.select_set(False)
    # hands are rigid on the wrist bone (auto weights smear fingers onto the hips); feet rigid on the ankle bone
    for sd in 'LR':
        sh, tip = skel[f'sh_{sd}'], skel[f'ht_{sd}']
        d = tip - sh
        wg = bo.vertex_groups[f'wr_{sd}']
        ag = bo.vertex_groups[f'an_{sd}']
        for v in body.vertices:
            t = (v.co - sh).dot(d) / d.length_squared
            near_arm = (sh + d * max(0, min(1, t)) - v.co).length < 0.09
            foot = v.co.z < skel[f'an_{sd}'].z - 0.01 and (1 if sd == 'L' else -1) * v.co.y > 0
            if (t > 0.86 and near_arm) or foot:
                for g in bo.vertex_groups:
                    g.remove([v.index])
                (wg if not foot else ag).add([v.index], 1.0, 'REPLACE')
    for sd, sg in (('L', 1), ('R', -1)):
        a = skel[f'el_{sd}'] - skel[f'sh_{sd}']
        ad[f'arm_{sd}'] = math.atan2(sg * a.y, -a.z)
    # clothing zones from the strongest bone weight per face: 0 torso, 1 legs, 2 skin, 3 hands, 4 boots, 5 sleeves
    zb = {'hips': 1, 'spine': 0, 'neck': 2}
    for sd in 'LR':
        zb.update({f'sh_{sd}': 5, f'el_{sd}': 5, f'wr_{sd}': 3, f'hp_{sd}': 1, f'kn_{sd}': 1, f'an_{sd}': 4})
    gname = {g.index: g.name for g in bo.vertex_groups}
    vbest = []
    for v in body.vertices:
        best, bw = 'spine', -1.0
        for g in v.groups:
            if g.weight > bw:
                best, bw = gname[g.group], g.weight
        vbest.append(best)
    neck_z = skel['neckb'].z - 0.03
    vz = [0] * len(body.vertices)
    for f in body.polygons:
        cnt = {}
        for vi in f.vertices:
            cnt[vbest[vi]] = cnt.get(vbest[vi], 0) + 1
        bn = max(cnt, key=cnt.get)
        z = zb.get(bn, 0)
        c = f.center
        if bn.startswith('kn') and c.z < 0.36:
            z = 4
        if bn == 'spine' and c.z > neck_z:
            z = 2
        if bn == 'hips' and c.z > skel['waist'].z - 0.06:
            z = 0
        if bn.startswith('el') and (c - skel['wr_L' if c.y > 0 else 'wr_R']).length < 0.035:
            z = 3
        f.material_index = z
        f.use_smooth = True
        for vi in f.vertices:
            vz[vi] = max(vz[vi], 1 if z in (0, 1, 5) else (2 if z == 4 else 0))
    # clothes stand off the skin: inflate clothed zones along the normals (oilskins more than shirts)
    if got:
        off = {1: 0.012 + 0.12 * (bulk - 1.0), 2: 0.016}
        for v in body.vertices:
            if vz[v.index]:
                v.co += v.normal * off[vz[v.index]]
    bpy.data.objects.remove(bo)
    bpy.data.objects.remove(ao)
    _BODY[key] = (body, ad, skel)
    return _BODY[key]


def _bone_attach(o, arm, bone, world):
    """Parent o to a bone keeping the given rest-pose world matrix (arm at the origin, rest pose)."""
    o.parent = arm
    o.parent_type = 'BONE'
    o.parent_bone = bone
    pb = arm.data.bones[bone]
    o.matrix_parent_inverse = (pb.matrix_local @ Matrix.Translation((0, pb.length, 0))).inverted()
    o.matrix_basis = world


def person(name, outfit='plant', loc=(0, 0, 0), rot_z=0.0, height=1.72, skin=None, build=1.0, seed=None, mats=None):
    """A person: one continuous subdivided skin body deformed by an armature (bones named like JOINTS), clothing
    zones as material slots, rigid accessories (caps, masks, aprons, vests, hard hats) on bones.
    Returns the armature object (the root you place and key)."""
    mats = mats or M()
    rnd = random.Random(seed if seed is not None else hash(name) & 0xffff)
    o = OUTFITS[outfit]
    sk = skin or mats['skin'][rnd.randrange(3)]
    k = 1.22 if outfit.startswith('fisher') else (1.12 if outfit in ('plant', 'plant_blue', 'qc', 'cold', 'port', 'port_o') else 1.0)
    gender = 'female' if (outfit in ('plant', 'plant_blue', 'qc', 'farm2') and rnd.random() < 0.4) else 'male'
    body, ad, skel = _body(k, round(build, 2), gender)
    arm = bpy.data.objects.new(name, ad)
    _link(arm)
    bo = bpy.data.objects.new(f'{name}_body', body)
    _link(bo)
    bo.parent = arm
    mod = bo.modifiers.new('Rig', 'ARMATURE')
    mod.object = arm
    ex0 = o['extras']
    torso = mats[o['bottom']] if 'bib' in ex0 else mats[o['top']]
    sleeves = mats[o['top']]
    legs = mats[o['bottom']]
    if 'coat' in ex0:
        torso = sleeves = mats['cloth_white']
    if 'jacket' in ex0:
        torso = sleeves = mats['cloth_navy']
    if 'vest' in ex0:
        torso = mats['hivis'] if rnd.random() < 0.6 else mats['hivis_orange']
    zm = [torso, legs, sk, sk if o['hands'] == 'skin' else mats[o['hands']], mats[o['feet']], sleeves]
    while len(body.materials) < len(zm):
        body.materials.append(zm[len(body.materials)])
    for i, m in enumerate(zm):
        bo.material_slots[i].link = 'OBJECT'
        bo.material_slots[i].material = m
    ex = o['extras']
    H = lambda n: skel[n].copy()

    def acc(nm, me, mat, bone, pos, scale=(1, 1, 1), rot=(0, 0, 0)):
        a = bpy.data.objects.new(f'{name}_{nm}', me)
        _link(a)
        if a.data and len(a.material_slots) == 0 and len(me.materials) == 0:
            me.materials.append(mat)
        if len(a.material_slots):
            a.material_slots[0].link = 'OBJECT'
            a.material_slots[0].material = mat
        _bone_attach(a, arm, bone, Matrix.Translation(pos) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1)))
        return a

    hp = H('head')
    if not os.path.exists(HBM):
        acc('face', _part_mesh('face', _face_mesh), sk, 'neck', hp + Vector((0.0, 0, 0)))
    if os.path.exists(HBM):
        bt = _part_mesh('boot', lambda: box_mesh('BODY_bootfoot', (0.29, 0.125, 0.11), 0.05, 3))
        sh_m = _part_mesh('bootshaft', lambda: cyl_mesh('BODY_bootshaft', 0.07, 0.3, 16, r2=0.065))
        for sd in 'LR':
            an, to = skel[f'an_{sd}'], skel[f'to_{sd}']
            acc(f'bootfoot_{sd}', bt, mats[o['feet']], f'an_{sd}', Vector(((an.x + to.x) / 2 - 0.005, an.y, 0.055)))
            acc(f'bootshaft_{sd}', sh_m, mats[o['feet']], f'kn_{sd}', Vector((an.x, an.y, 0.24)))
    if 'cap' in ex:
        acc('cap', _part_mesh('cap', _cap_mesh), mats['cap_grey'] if rnd.random() < 0.6 else mats['cloth_navy'], 'neck',
            hp + Vector((0.02, 0, 0.05)), (0.97, 0.97, 0.95))
    elif 'haircap' in ex:
        acc('haircap', _part_mesh('haircap', lambda: sphere_mesh('BODY_haircap', 0.105, 16, 10)), mats['haircap'], 'neck',
            hp + Vector((0.012, 0, 0.03)), (1.05, 1.0, 0.85))
    elif 'hardhat' in ex:
        acc('hardhat', _part_mesh('hardhat', _hardhat_mesh), mats['hardhat'] if rnd.random() < 0.5 else mats['float_yellow'],
            'neck', hp + Vector((0.02, 0, 0.055)))
    else:
        acc('hair', _part_mesh('hair', lambda: sphere_mesh('BODY_hair', 0.098, 16, 10)), mats['hair'], 'neck',
            hp + Vector((0.008, 0, 0.025)), (1.05, 1.0, 0.8))
    if 'mask' in ex:
        acc('mask', _part_mesh('mask', lambda: box_mesh('BODY_mask', (0.05, 0.15, 0.085), 0.024, 3)), mats['mask'], 'neck',
            hp + Vector((0.075, 0, -0.035)))
    if 'apron' in ex or 'apron_blue' in ex:
        acc('apron', _part_mesh(('apron', k), lambda: box_mesh('BODY_apron', (0.025, 0.36, 0.95), 0.012, 2)),
            mats['apron_blue' if 'apron_blue' in ex else 'apron'], 'hips', Vector((0.15 * k, 0, 0.82)))
    if 'coat' in ex or 'jacket' in ex:
        acc('coat', _part_mesh(('skirt', k), lambda: cyl_mesh('BODY_skirt', 0.2 * k, 0.5 if 'coat' in ex else 0.22, 20,
                                                              r2=0.17 * k, origin='center')),
            mats['cloth_white'] if 'coat' in ex else mats['cloth_navy'], 'hips', Vector((0, 0, 0.72 if 'coat' in ex else 0.95)))
    if 'hood' in ex:
        acc('hood', _part_mesh('hood', lambda: sphere_mesh('BODY_hood', 0.1, 12, 8)), mats[o['top']], 'spine',
            Vector((-0.1, 0, 1.47)), (0.8, 1.6, 0.8))
    s = height / 1.72
    arm.location = loc
    arm.rotation_euler = (0, 0, rot_z)
    arm.scale = (s, s, s)
    arm['joints'] = JOINTS
    if arm.pose is None or len(arm.pose.bones) == 0:
        bpy.context.view_layer.update()
    pose(arm, 'stand')
    return arm


def bone_target(root, j):
    """(object, subtarget) for constraints that follow a joint (e.g. a tool in the hand)."""
    return root, j


def _set_mat(oname, m):
    o = bpy.data.objects[oname]
    if len(o.material_slots) == 0:
        o.data.materials.append(m)
    o.material_slots[0].link = 'OBJECT'
    o.material_slots[0].material = m


def _face_mesh():
    """Nose, brow and ears so heads read as heads at mid distance."""
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.018, radius2=0.004, depth=0.035)
    bmesh.ops.rotate(bm, verts=r['verts'], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(80), 3, 'Y'))
    bmesh.ops.translate(bm, verts=r['verts'], vec=(0.11, 0, 0.0))
    r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.03)
    bmesh.ops.scale(bm, verts=r['verts'], vec=(0.6, 2.4, 0.5))
    bmesh.ops.translate(bm, verts=r['verts'], vec=(0.085, 0, 0.045))
    for sy in (1, -1):
        r = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.022)
        bmesh.ops.scale(bm, verts=r['verts'], vec=(0.6, 0.4, 1.2))
        bmesh.ops.translate(bm, verts=r['verts'], vec=(-0.005, sy * 0.09, 0.0))
    r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.05)
    bmesh.ops.scale(bm, verts=r['verts'], vec=(1.0, 1.2, 0.7))
    bmesh.ops.translate(bm, verts=r['verts'], vec=(0.05, 0, -0.075))
    return bm_to_mesh(bm, 'BODY_face', smooth=True)


def _cap_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.112)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context='VERTS')
    for v in bm.verts:
        v.co.z *= 0.75
    me = bm_to_mesh(bm, 'BODY_cap', smooth=True)
    b2 = bmesh.new()
    b2.from_mesh(me)
    # brim
    r = bmesh.ops.create_circle(b2, cap_ends=True, segments=16, radius=0.08)
    for v in r['verts']:
        v.co = Vector((v.co.x * 1.1 + 0.11, v.co.y * 1.05, -0.005))
    b2.to_mesh(me)
    b2.free()
    return me


def _hardhat_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.125)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context='VERTS')
    for v in bm.verts:
        v.co.z *= 0.85
        v.co.x *= 1.1
    r = bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=0.15)
    for v in r['verts']:
        v.co = Vector((v.co.x * 1.1 + 0.01, v.co.y, -0.005))
    return bm_to_mesh(bm, 'BODY_hardhat', smooth=True)


D = math.radians
POSES = {
    # joint: (x, y, z) degrees. Y+ on a leg/arm swings it backward, Y- forward. spine Y+ = lean forward.
    'stand': {'sh_L': (6, 0, 0), 'sh_R': (-6, 0, 0), 'el_L': (0, -8, 0), 'el_R': (0, -8, 0)},
    'idle': {'sh_L': (5, 4, 0), 'sh_R': (-5, -6, 0), 'el_L': (0, -20, 0), 'el_R': (0, -15, 0), 'hp_L': (0, -4, 0),
             'kn_L': (0, 6, 0), 'spine': (0, 2, 3)},
    'pull': {'spine': (0, -12, 0), 'sh_L': (5, -75, 0), 'sh_R': (-5, -65, 0), 'el_L': (0, -25, 0),
             'el_R': (0, -30, 0), 'hp_L': (0, -25, 0), 'kn_L': (0, 20, 0), 'hp_R': (0, 12, 0), 'kn_R': (0, 10, 0),
             'an_L': (0, 5, 0)},
    'pull2': {'spine': (0, -18, 0), 'sh_L': (5, -55, 0), 'sh_R': (-5, -50, 0), 'el_L': (0, -45, 0),
              'el_R': (0, -50, 0), 'hp_L': (0, -28, 0), 'kn_L': (0, 22, 0), 'hp_R': (0, 15, 0), 'kn_R': (0, 12, 0)},
    'guide': {'spine': (0, 8, 0), 'sh_L': (10, -120, 0), 'sh_R': (-10, -110, 0), 'el_L': (0, -20, 0),
              'el_R': (0, -25, 0), 'hp_L': (0, -15, 0), 'kn_L': (0, 15, 0), 'hp_R': (0, 10, 0)},
    'reach': {'spine': (0, 15, 0), 'sh_L': (5, -95, 0), 'sh_R': (-5, -90, 0), 'el_L': (0, -10, 0), 'el_R': (0, -12, 0),
              'hp_L': (0, -10, 0), 'kn_L': (0, 10, 0)},
    'kneel': {'hips_z': 0.52, 'spine': (0, 30, 0), 'hp_L': (0, -95, 0), 'kn_L': (0, 95, 0), 'an_L': (0, 0, 0),
              'hp_R': (0, -5, 0), 'kn_R': (0, 92, 0), 'an_R': (0, -40, 0), 'sh_L': (5, -45, 0), 'sh_R': (-5, -55, 0),
              'el_L': (0, -35, 0), 'el_R': (0, -30, 0), 'neck': (0, 15, 0)},
    'kneel2': {'hips_z': 0.52, 'spine': (0, 38, 0), 'hp_L': (0, -95, 0), 'kn_L': (0, 95, 0), 'hp_R': (0, -5, 0),
               'kn_R': (0, 92, 0), 'an_R': (0, -40, 0), 'sh_L': (10, -70, 0), 'sh_R': (-5, -30, 0),
               'el_L': (0, -10, 0), 'el_R': (0, -50, 0), 'neck': (0, 20, 0)},
    'crouch': {'hips_z': 0.6, 'spine': (0, 35, 0), 'hp_L': (0, -80, 0), 'kn_L': (0, 120, 0), 'an_L': (0, -35, 0),
               'hp_R': (0, -70, 0), 'kn_R': (0, 115, 0), 'an_R': (0, -40, 0), 'sh_L': (5, -50, 0),
               'sh_R': (-5, -40, 0), 'el_L': (0, -30, 0), 'el_R': (0, -35, 0)},
    'shovel': {'spine': (0, 28, -10), 'sh_L': (15, -55, 0), 'sh_R': (-5, -30, 0), 'el_L': (0, -30, 0),
               'el_R': (0, -55, 0), 'hp_L': (0, -25, 0), 'kn_L': (0, 30, 0), 'hp_R': (0, 10, 0), 'kn_R': (0, 15, 0)},
    'shovel2': {'spine': (0, 10, 10), 'sh_L': (15, -85, 0), 'sh_R': (-5, -60, 0), 'el_L': (0, -20, 0),
                'el_R': (0, -45, 0), 'hp_L': (0, -15, 0), 'kn_L': (0, 15, 0)},
    'carry': {'spine': (0, -4, 0), 'sh_L': (8, -40, 0), 'sh_R': (-8, -40, 0), 'el_L': (0, -60, 0),
              'el_R': (0, -60, 0)},
    'lift': {'spine': (0, 35, 0), 'sh_L': (12, -60, 0), 'sh_R': (-12, -60, 0), 'el_L': (0, -10, 0),
             'el_R': (0, -10, 0), 'hp_L': (0, -35, 0), 'kn_L': (0, 45, 0), 'hp_R': (0, -35, 0), 'kn_R': (0, 45, 0),
             'hips_z': 0.86},
    'pass': {'spine': (0, 10, 0), 'sh_L': (12, -85, 0), 'sh_R': (-12, -85, 0), 'el_L': (0, -25, 0),
             'el_R': (0, -25, 0), 'hp_L': (0, -15, 0), 'kn_L': (0, 10, 0)},
    'push': {'spine': (0, 18, 0), 'sh_L': (8, -70, 0), 'sh_R': (-8, -70, 0), 'el_L': (0, -30, 0), 'el_R': (0, -30, 0)},
    'table': {'spine': (0, 22, 0), 'neck': (0, 15, 0), 'sh_L': (12, -40, 0), 'sh_R': (-12, -40, 0),
              'el_L': (0, -60, 0), 'el_R': (0, -55, 0)},
    'table2': {'spine': (0, 20, 5), 'neck': (0, 20, 0), 'sh_L': (12, -35, 10), 'sh_R': (-12, -45, -10),
               'el_L': (0, -70, 0), 'el_R': (0, -50, 0)},
    'point': {'sh_R': (-10, -85, -20), 'el_R': (0, -5, 0), 'sh_L': (6, 0, 0)},
    'sit': {'hips_z': 0.55, 'hp_L': (0, -90, 0), 'kn_L': (0, 90, 0), 'hp_R': (0, -90, 0), 'kn_R': (0, 90, 0),
            'sh_L': (5, -45, 0), 'sh_R': (-5, -45, 0), 'el_L': (0, -30, 0), 'el_R': (0, -30, 0)},
}
WALK = [
    {'hp_L': (0, -24, 0), 'kn_L': (0, 8, 0), 'an_L': (0, 6, 0), 'hp_R': (0, 18, 0), 'kn_R': (0, 30, 0), 'an_R': (0, -8, 0),
     'sh_L': (6, 18, 0), 'sh_R': (-6, -18, 0), 'el_L': (0, -15, 0), 'el_R': (0, -25, 0), 'hips_z': 0.93},
    {'hp_L': (0, -5, 0), 'kn_L': (0, 10, 0), 'hp_R': (0, 5, 0), 'kn_R': (0, 55, 0), 'an_R': (0, -10, 0),
     'sh_L': (6, 2, 0), 'sh_R': (-6, -2, 0), 'el_L': (0, -15, 0), 'el_R': (0, -15, 0), 'hips_z': 0.95},
    {'hp_R': (0, -24, 0), 'kn_R': (0, 8, 0), 'an_R': (0, 6, 0), 'hp_L': (0, 18, 0), 'kn_L': (0, 30, 0), 'an_L': (0, -8, 0),
     'sh_R': (-6, 18, 0), 'sh_L': (6, -18, 0), 'el_R': (0, -15, 0), 'el_L': (0, -25, 0), 'hips_z': 0.93},
    {'hp_R': (0, -5, 0), 'kn_R': (0, 10, 0), 'hp_L': (0, 5, 0), 'kn_L': (0, 55, 0), 'an_L': (0, -10, 0),
     'sh_R': (-6, 2, 0), 'sh_L': (6, -2, 0), 'el_R': (0, -15, 0), 'el_L': (0, -15, 0), 'hips_z': 0.95},
]


def _joint(root, j):
    return root.pose.bones.get(j) if root.pose else None


def _bone_euler(j, r):
    """POSES are written as rotations about the body's axes (X forward, Y left, Z up) of a limb hanging down;
    convert to the bone's local euler for the roll convention set in _body()."""
    rx, ry, rz = D(r[0]), D(r[1]), D(r[2])
    kind = BONES[j][3]
    if kind == 'down':
        return (rx, -rz, ry)
    if kind == 'up':
        return (rx, rz, -ry)
    return (-ry, rx, rz)


def pose(root, p, frame=None, upper_only=False, overrides=None):
    """Apply a named pose (or a dict) to a person; key it when frame is given."""
    spec = dict(POSES[p]) if isinstance(p, str) else dict(p)
    if overrides:
        spec.update(overrides)
    for j in JOINTS:
        if upper_only and j in ('hips', 'hp_L', 'kn_L', 'an_L', 'hp_R', 'kn_R', 'an_R'):
            continue
        pb = _joint(root, j)
        if pb is None:
            continue
        pb.rotation_mode = 'XYZ'
        e = list(_bone_euler(j, spec.get(j, (0, 0, 0))))
        if j in ('sh_L', 'sh_R'):  # rest pose has the arms out (A-pose): bring them down first
            a = root.data.get('arm_' + j[-1], 0.0)
            e[0] += -a if j == 'sh_L' else a
        pb.rotation_euler = e
        if frame is not None:
            pb.keyframe_insert('rotation_euler', frame=frame)
    if not upper_only:
        h = _joint(root, 'hips')
        h.location = (0, spec.get('hips_z', 0.94) - 0.94, 0)
        if frame is not None:
            h.keyframe_insert('location', frame=frame)


def mix_pose(a, b, t):
    pa = POSES[a] if isinstance(a, str) else a
    pb = POSES[b] if isinstance(b, str) else b
    out = {}
    for k in set(pa) | set(pb):
        if k == 'hips_z':
            out[k] = pa.get(k, 0.94) * (1 - t) + pb.get(k, 0.94) * t
        else:
            va, vb = pa.get(k, (0, 0, 0)), pb.get(k, (0, 0, 0))
            out[k] = tuple(va[i] * (1 - t) + vb[i] * t for i in range(3))
    return out


def anim_poses(root, seq, upper_only=False):
    """seq: [(frame, pose_name_or_dict)] keyed with Bezier easing."""
    for f, p in seq:
        pose(root, p, f, upper_only=upper_only)


def walk(root, path, f0, f1, stride=0.75, upper=None):
    """Walk the person along a polyline path [(x, y)] between frames f0..f1 (forward only).
    Root location/rotation are keyed per step; legs cycle with the distance."""
    pts = [Vector((p[0], p[1], root.location.z)) for p in path]
    segs = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(segs)
    n = max(2, int((f1 - f0) / 3))
    prev_rot = None
    for i in range(n + 1):
        t = i / n
        f = f0 + (f1 - f0) * t
        d = total * t
        k = 0
        while k < len(segs) - 1 and d > segs[k]:
            d -= segs[k]
            k += 1
        a = pts[k] + (pts[k + 1] - pts[k]) * (d / segs[k] if segs[k] else 0)
        dirv = (pts[k + 1] - pts[k]).normalized()
        rz = math.atan2(dirv.y, dirv.x)
        if prev_rot is not None:
            while rz - prev_rot > math.pi:
                rz -= 2 * math.pi
            while rz - prev_rot < -math.pi:
                rz += 2 * math.pi
        prev_rot = rz
        root.location = a
        root.rotation_euler = (0, 0, rz)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        phase = (total * t) / stride
        idx = int(phase * 2) % 4
        frac = phase * 2 - int(phase * 2)
        pz = mix_pose(WALK[idx], WALK[(idx + 1) % 4], frac)
        if upper:
            pz.update({k: v for k, v in POSES[upper].items() if k not in ('hips_z',) and not k.startswith(('hp', 'kn', 'an'))})
        pose(root, pz, f)


# ---------------------------------------------------------------- cold-chain props
def crate_mesh(name='LIB_Crate', w=0.6, d=0.4, h=0.3):
    """Stackable plastic fish crate: open top, thick rim, hand holes as recesses, ribbed sides."""
    bm = bmesh.new()
    t = 0.025
    outer = bmesh.ops.create_cube(bm, size=1)['verts']
    for v in outer:
        v.co = Vector((v.co.x * w, v.co.y * d, v.co.z * h + h / 2))
    # open top: delete top face, inset walls via solidify-like inner box
    top = [f for f in bm.faces if f.normal.z > 0.9][0]
    bmesh.ops.delete(bm, geom=[top], context='FACES_ONLY')
    edges = [e for e in bm.edges if e.is_boundary]
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    nv = [g for g in ext['geom'] if isinstance(g, bmesh.types.BMVert)]
    for v in nv:
        v.co.x -= math.copysign(t, v.co.x)
        v.co.y -= math.copysign(t, v.co.y)
    ext2 = bmesh.ops.extrude_edge_only(bm, edges=[g for g in ext['geom'] if isinstance(g, bmesh.types.BMEdge)])
    nv2 = [g for g in ext2['geom'] if isinstance(g, bmesh.types.BMVert)]
    for v in nv2:
        v.co.z = 0.03
    bmesh.ops.contextual_create(bm, geom=[g for g in ext2['geom'] if isinstance(g, bmesh.types.BMEdge)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # rim lip
    for (cx, cy, sx, sy) in ((0, d / 2, w + 0.02, 0.035), (0, -d / 2, w + 0.02, 0.035), (w / 2, 0, 0.035, d),
                             (-w / 2, 0, 0.035, d)):
        rim = bmesh.ops.create_cube(bm, size=1)['verts']
        for v in rim:
            v.co = Vector((v.co.x * sx + cx, v.co.y * sy + cy, v.co.z * 0.03 + h - 0.015))
    # ribs on the long sides
    for i in range(5):
        x = -w / 2 + w * (i + 0.5) / 5
        for sy in (-1, 1):
            rb = bmesh.ops.create_cube(bm, size=1)['verts']
            for v in rb:
                v.co = Vector((v.co.x * 0.02 + x, v.co.y * 0.012 + sy * (d / 2 + 0.006), v.co.z * (h * 0.7) + h * 0.42))
    return bm_to_mesh(bm, name)


def ice_mesh(name, w, d, mound=0.06, res=14, seed=1):
    """Crushed-ice layer: displaced grid with chunky noise, slightly mounded."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=max(2, int(res * d / w)), size=0.5)
    for v in bm.verts:
        x, y = v.co.x * w, v.co.y * d
        r = 1 - (abs(v.co.x) * 2) ** 2 * 0.6 - (abs(v.co.y) * 2) ** 2 * 0.6
        v.co = Vector((x, y, mound * max(0.0, r) + rnd.uniform(0, mound * 0.45)))
    return bm_to_mesh(bm, name, smooth=False)


def ice_chunks(name, w, d, n=60, seed=2, z=0.0, size=0.025):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for _ in range(n):
        r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(size * 0.5, size))
        m = Matrix.Translation((rnd.uniform(-w / 2, w / 2), rnd.uniform(-d / 2, d / 2), z + rnd.uniform(0, size))) @ \
            Euler((rnd.random() * 3, rnd.random() * 3, rnd.random() * 3)).to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=m, verts=r['verts'])
    return bm_to_mesh(bm, name)


_CRATE = {}


def crate(name, color='blue', loc=(0, 0, 0), rot_z=0.0, fill=None, parent=None, mats=None, seed=0):
    """A plastic crate (LIB_Crate_Plastic); fill = None | 'ice' | 'fish' | 'tuna' | 'shrimp' (+ crushed ice on top).
    Returns the crate object; contents are children."""
    mats = mats or M()
    if 'mesh' not in _CRATE:
        _CRATE['mesh'] = crate_mesh()
        _CRATE['ice'] = ice_mesh('LIB_CrateIce', 0.54, 0.34, 0.05, 12, 3)
        _CRATE['chunks'] = ice_chunks('LIB_CrateIceChunks', 0.5, 0.3, 50, 4, 0.0, 0.02)
    c = obj(name, _CRATE['mesh'], None, loc, (0, 0, rot_z), parent=parent)
    if len(c.material_slots) == 0:
        c.data.materials.append(mats['crate_' + color])
    c.material_slots[0].link = 'OBJECT'
    c.material_slots[0].material = mats['crate_' + color]
    if fill:
        rnd = random.Random(seed)
        level = 0.2
        if fill in ('fish', 'tuna', 'mixed'):
            kinds = {'fish': ['mackerel'], 'tuna': ['tuna_s'], 'mixed': ['mackerel', 'seer', 'ribbon']}[fill]
            cnt = 3 if fill == 'tuna' else 14
            for i in range(cnt):
                k = rnd.choice(kinds)
                fo = fish(f'{name}_f{i}', k, parent=c, loc=(rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.1),
                                                          level - 0.02 + rnd.uniform(0, 0.06)),
                          rot=(D(90 + rnd.uniform(-20, 20)), 0, D(rnd.uniform(-25, 25) + (90 if fill == 'tuna' and False else 0))),
                          scale=(0.95 if fill == 'tuna' else 1.0))
        elif fill == 'shrimp':
            for i in range(40):
                shrimp_proxy(f'{name}_s{i}', parent=c, loc=(rnd.uniform(-0.22, 0.22), rnd.uniform(-0.13, 0.13),
                                                            level + rnd.uniform(0, 0.04)),
                             rot=(rnd.uniform(0, 6.28), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.28)))
        ice = obj(f'{name}_ice', _CRATE['ice'], mats['ice'], (0, 0, level + (0.05 if fill != 'ice' else 0.02)), parent=c)
        if fill != 'ice':
            ice.scale = (1, 1, 0.6)
            ice.location.z = level + 0.03
        obj(f'{name}_icech', _CRATE['chunks'], mats['ice'], (0, 0, level + 0.07), parent=c)
    return c


# ---------------------------------------------------------------- fish
FISH_SPECS = {
    # length (m), height ratio, width ratio, back colour, belly colour, fin colour, kind
    'tuna': dict(L=1.4, h=0.27, w=0.2, back=(0.012, 0.025, 0.07), belly=(0.72, 0.74, 0.76), fin=(0.85, 0.62, 0.04),
                 finlets=True, tail=0.42),
    'tuna_s': dict(L=0.55, h=0.27, w=0.2, back=(0.012, 0.025, 0.07), belly=(0.72, 0.74, 0.76), fin=(0.85, 0.62, 0.04),
                   finlets=True, tail=0.42),
    'mackerel': dict(L=0.24, h=0.2, w=0.13, back=(0.03, 0.12, 0.13), belly=(0.78, 0.76, 0.66), fin=(0.6, 0.55, 0.35),
                     finlets=False, tail=0.3, stripes=True),
    'seer': dict(L=0.7, h=0.17, w=0.09, back=(0.09, 0.14, 0.24), belly=(0.82, 0.83, 0.84), fin=(0.25, 0.28, 0.33),
                 finlets=True, tail=0.3),
    'ribbon': dict(L=0.8, h=0.07, w=0.025, back=(0.75, 0.78, 0.8), belly=(0.85, 0.86, 0.87), fin=(0.7, 0.72, 0.75),
                   finlets=False, tail=0.05),
}
_FISH = {}


def fish_material(kind):
    sp = FISH_SPECS[kind]
    name = f'MAT_FishSkin_{kind}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    tc = _node(nt, 'ShaderNodeTexCoord', (-1200, 0))
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (-1000, 0))
    l.new(_sock(tc, 'Object', out=True), sep.inputs[0])
    mr = _node(nt, 'ShaderNodeMapRange', (-800, 0))
    mr.inputs['From Min'].default_value = -0.02
    mr.inputs['From Max'].default_value = 0.06
    l.new(sep.outputs[2], mr.inputs['Value'])
    col = mixrgb(nt, mr.outputs[0], sp['belly'], sp['back'], loc=(-500, 100))
    if sp.get('stripes'):
        wv = _node(nt, 'ShaderNodeTexWave', (-800, 300))
        wv.inputs['Scale'].default_value = 9.0
        wv.inputs['Distortion'].default_value = 6.0
        l.new(_sock(tc, 'Object', out=True), wv.inputs['Vector'])
        sm = _node(nt, 'ShaderNodeMath', (-600, 300))
        sm.operation = 'MULTIPLY'
        l.new(_sock(wv, 'Factor', out=True), sm.inputs[0])
        l.new(mr.outputs[0], sm.inputs[1])
        col = mixrgb(nt, sm.outputs[0], col, (0.01, 0.03, 0.03), loc=(-300, 200))
    if kind.startswith('tuna'):
        # faint yellow lateral sheen
        mr2 = _node(nt, 'ShaderNodeMapRange', (-800, -250))
        mr2.inputs['From Min'].default_value = 0.0
        mr2.inputs['From Max'].default_value = 0.015
        mr2.interpolation_type = 'SMOOTHERSTEP'
        l.new(sep.outputs[2], mr2.inputs['Value'])
        mr3 = _node(nt, 'ShaderNodeMapRange', (-800, -450))
        mr3.inputs['From Min'].default_value = 0.035
        mr3.inputs['From Max'].default_value = 0.015
        l.new(sep.outputs[2], mr3.inputs['Value'])
        band = _node(nt, 'ShaderNodeMath', (-600, -300))
        band.operation = 'MULTIPLY'
        l.new(mr2.outputs[0], band.inputs[0])
        l.new(mr3.outputs[0], band.inputs[1])
        bs = _node(nt, 'ShaderNodeMath', (-450, -300))
        bs.operation = 'MULTIPLY'
        bs.inputs[1].default_value = 0.45
        l.new(band.outputs[0], bs.inputs[0])
        col = mixrgb(nt, bs.outputs[0], col, (0.7, 0.5, 0.05), loc=(-250, -100))
    l.new(col, p.inputs['Base Color'])
    p.inputs['Metallic'].default_value = 0.55
    p.inputs['Roughness'].default_value = 0.22
    p.inputs['Coat Weight'].default_value = 0.6
    p.inputs['Coat Roughness'].default_value = 0.05
    # scale micro-normal
    vor = _node(nt, 'ShaderNodeTexVoronoi', (-600, -650))
    vor.inputs['Scale'].default_value = 180.0
    l.new(_sock(tc, 'Object', out=True), vor.inputs['Vector'])
    b = _node(nt, 'ShaderNodeBump', (0, -600))
    b.inputs['Strength'].default_value = 0.15
    b.inputs['Distance'].default_value = 0.002
    l.new(_sock(vor, 'Distance', out=True), b.inputs['Height'])
    l.new(b.outputs[0], p.inputs['Normal'])
    return m


def fish_mesh(kind):
    """Lofted fish body (unit length along +X, head at +X), crescent tail, dorsal/anal/pectoral fins, finlets, eye."""
    if kind in _FISH:
        return _FISH[kind]
    sp = FISH_SPECS[kind]
    bm = bmesh.new()
    n = 28
    seg = 14
    H, W = sp['h'], sp['w']
    rings = []
    for i in range(n + 1):
        t = i / n  # 0 tail -> 1 snout
        x = 0.08 + t * 0.92
        if kind == 'ribbon':
            prof = math.sin(math.pi * min(1, t ** 0.35)) ** 0.4
        else:
            prof = math.sin(math.pi * (t ** 0.72)) ** 0.85
        prof = max(prof, 0.06 if t < 0.15 else 0.02)
        h = H * prof
        w = W * prof * (0.75 + 0.25 * t)
        zc = 0.004 * math.sin(math.pi * t)
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            ring.append(bm.verts.new((x - 0.5, w / 2 * math.cos(a), zc + h / 2 * math.sin(a) * (1.0 if math.sin(a) > 0 else 0.92))))
        rings.append(ring)
    for i in range(n):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % seg], rings[i][(j + 1) % seg]))
    tipv = bm.verts.new((0.5 + 0.01, 0, 0.002))
    for j in range(seg):
        bm.faces.new((rings[-1][j], rings[-1][(j + 1) % seg], tipv))
    tailv = bm.verts.new((0.08 - 0.5 - 0.005, 0, 0))
    for j in range(seg):
        bm.faces.new((rings[0][(j + 1) % seg], rings[0][j], tailv))
    me_body = bm_to_mesh(bm, f'LIB_Fish_{kind}_body', smooth=True)

    fins = bmesh.new()

    def fin(pts, thick=0.003):
        vs = [fins.verts.new((p[0] - 0.5, p[1], p[2])) for p in pts]
        f = fins.faces.new(vs)
        return f

    ts = sp['tail']
    # crescent tail fin (two lobes)
    fin([(0.09, 0, 0.01), (0.04, 0, ts * 0.45), (-0.02, 0, ts * 0.55), (0.03, 0, ts * 0.2), (0.0, 0, 0.0),
         (0.03, 0, -ts * 0.2), (-0.02, 0, -ts * 0.55), (0.04, 0, -ts * 0.45), (0.09, 0, -0.01)])
    if kind != 'ribbon':
        # first dorsal
        fin([(0.6, 0, H * 0.42), (0.66, 0, H * 0.42 + H * 0.35), (0.72, 0, H * 0.45 + H * 0.12), (0.76, 0, H * 0.45)])
        # second dorsal + anal (long sickle on tuna)
        sickle = 0.45 if kind.startswith('tuna') else 0.18
        fin([(0.4, 0, H * 0.43), (0.47, 0, H * 0.4 + H * sickle * 1.6), (0.5, 0, H * 0.43)])
        fin([(0.4, 0, -H * 0.4), (0.47, 0, -H * 0.4 - H * sickle * 1.6), (0.5, 0, -H * 0.4)])
        # pectoral fins (both sides)
        pl = 0.32 if kind.startswith('tuna') else 0.12
        for sy in (1, -1):
            fin([(0.78, sy * W * 0.45, -0.005), (0.78 - pl, sy * W * 0.85, -H * 0.12), (0.74, sy * W * 0.45, -0.02)])
        if sp['finlets']:
            for k in range(7):
                x = 0.13 + k * 0.035
                hh = H * (0.12 + 0.03 * k) * 0.5
                fin([(x, 0, hh), (x - 0.02, 0, hh + 0.025), (x + 0.012, 0, hh)])
                fin([(x, 0, -hh), (x - 0.02, 0, -hh - 0.025), (x + 0.012, 0, -hh)])
    else:
        fin([(0.15, 0, H * 0.45), (0.9, 0, H * 0.45), (0.9, 0, H * 0.75), (0.15, 0, H * 0.55)])
    me_fins = bm_to_mesh(fins, f'LIB_Fish_{kind}_fins')
    eye = bmesh.new()
    for sy in (1, -1):
        r = bmesh.ops.create_uvsphere(eye, u_segments=10, v_segments=6, radius=H * 0.08)
        bmesh.ops.translate(eye, verts=r['verts'], vec=(0.9 - 0.5, sy * W * 0.36, H * 0.12))
    me_eye = bm_to_mesh(eye, f'LIB_Fish_{kind}_eye', smooth=True)
    mats = M()
    me_body.materials.append(fish_material(kind))
    me_fins.materials.append(pbr(f'MAT_FishFin_{kind}', sp['fin'], 0.35, var=0.15, transmission=0.0, coat=0.3))
    me_eye.materials.append(pbr('MAT_FishEye', (0.01, 0.01, 0.01), 0.02, coat=1.0, var=0.0, bump=0.0))
    # join into one mesh
    tmp = []
    for me in (me_body, me_fins, me_eye):
        o = bpy.data.objects.new('tmp_' + me.name, me)
        bpy.context.scene.collection.objects.link(o)
        tmp.append(o)
    j = join(tmp, f'LIB_Fish_{kind}')
    me = j.data
    bpy.data.objects.remove(j)
    me.name = f'LIB_Fish_{kind}'
    _FISH[kind] = me
    return me


def fish(name, kind='mackerel', loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, parent=None):
    me = fish_mesh(kind)
    L = FISH_SPECS[kind]['L'] * scale
    return obj(name, me, None, loc, rot, (L, L, L), parent=parent)


_SHRIMP = {}


def shrimp_mesh():
    if 'm' in _SHRIMP:
        return _SHRIMP['m']
    bm = bmesh.new()
    seg = 10
    n = 14
    rings = []
    for i in range(n + 1):
        t = i / n
        a = math.pi * 0.75 * t
        R = 0.05
        cx, cz = R * math.sin(a), R * (1 - math.cos(a))
        r = 0.012 * (0.35 + 0.65 * math.sin(math.pi * min(1, t * 1.1 + 0.05)))
        nrm = Vector((math.cos(a), 0, math.sin(a)))
        side = Vector((0, 1, 0))
        ring = []
        for j in range(seg):
            b = 2 * math.pi * j / seg
            p = Vector((cx, 0, cz)) + r * (math.cos(b) * side + math.sin(b) * Vector((-nrm.z, 0, nrm.x)) * 1.0)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for i in range(n):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % seg], rings[i][(j + 1) % seg]))
    me = bm_to_mesh(bm, 'LIB_Shrimp_proxy', smooth=True)
    me.materials.append(pbr('MAT_ShrimpRaw', (0.62, 0.6, 0.55), 0.25, var=0.15, sss=0.4, coat=0.6, transmission=0.15))
    _SHRIMP['m'] = me
    return me


def shrimp_proxy(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, scale=1.0):
    return obj(name, shrimp_mesh(), None, loc, rot, (scale, scale, scale), parent=parent)


# ---------------------------------------------------------------- ocean
def ocean(name='Ocean', size=60.0, repeat=4, res=12, choppy=1.1, wind=11.0, scale=1.0, mat=None, f0=1, f1=480,
          foam=0.35, loc=(0, 0, 0), depth=200.0):
    me = bpy.data.meshes.new(name)
    o = bpy.data.objects.new(name, me)
    _link(o)
    # the modifier builds its grid from the origin toward +X/+Y: centre it on loc
    o.location = (loc[0] - size * repeat / 2, loc[1] - size * repeat / 2, loc[2])
    m = o.modifiers.new('Ocean', 'OCEAN')
    m.geometry_mode = 'GENERATE'
    m.resolution = res
    m.spatial_size = int(size)
    m.repeat_x = repeat
    m.repeat_y = repeat
    m.choppiness = choppy
    m.wave_scale = scale
    m.wind_velocity = wind
    m.wave_alignment = 0.4
    m.depth = depth
    m.use_foam = True
    m.foam_coverage = foam
    m.foam_layer_name = 'foam'
    m.use_normals = True
    m.time = f0 / 24.0
    m.keyframe_insert('time', frame=f0)
    m.time = f1 / 24.0
    m.keyframe_insert('time', frame=f1)
    linear_keys(o)
    me.materials.append(mat or M()['water_sea'])
    for p in me.polygons:
        p.use_smooth = True
    o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
    return o


def far_water(name='SeaFar', size=8000, z=-0.05, mat=None, hole=190.0):
    """Flat water to the horizon with a square hole where the Ocean modifier surface sits."""
    bm = bmesh.new()
    o, h = size / 2, hole / 2
    outer = [bm.verts.new(p) for p in ((-o, -o, 0), (o, -o, 0), (o, o, 0), (-o, o, 0))]
    inner = [bm.verts.new(p) for p in ((-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0))]
    for i in range(4):
        bm.faces.new((outer[i], outer[(i + 1) % 4], inner[(i + 1) % 4], inner[i]))
    me = bm_to_mesh(bm, name)
    me.materials.append(mat or M()['water_sea'])
    return obj(name, me, None, (0, 0, z))
