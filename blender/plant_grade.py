"""Round-8 plant grade (#163): the halls read pale and clean. This pass adds contrast and working wear across every
plant scene built by plant_chain.build (same names everywhere, so boundary frames stay identical):
  - the sky world fades out as the camera enters the hall (it lit the interior flat), lights shrink to fixture size
    so they pool and fall off
  - darker brushed stainless with water spots, yellowed PVC strips, a blue nonwoven cap (not a white wig)
  - coloured crate stacks, dark control cabinets, hoses on the floor, all placed only where nothing else stands
  - cold store: patchy floor frost, frosted wall base, dented carton corners, plain white pallet labels
apply() runs after the scene action is built, world_fade() after the world is set; both before the global frame shift."""
import random
import bpy
from mathutils import Vector
import skpbr as P
import skinterior as SI
from sktruck import Part

DZ = SI.DZ
CX = SI.CX
XL, XR = SI.XL, SI.XR


def world_fade():
    """World light is unoccluded in EEVEE: inside the hall it flattened everything. Global frames, like the exposure keys."""
    w = bpy.context.scene.world
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            s0 = n.inputs['Strength'].default_value
            for f, k in ((236, 1.0), (264, 0.3)):
                n.inputs['Strength'].default_value = s0 * k
                n.inputs['Strength'].keyframe_insert('default_value', frame=f)


def _lights():
    for o in bpy.data.objects:
        if o.type != 'LIGHT' or o.data.type != 'AREA':
            continue
        if o.name.startswith('IN_Area_'):
            o.data.size, o.data.size_y = 2.4, 1.0      # fixture-sized: pools under each row, falloff between
            o.data.energy = 420
        elif o.name.startswith('IN_ColdArea'):
            o.data.size, o.data.size_y = 1.2, 1.2
            o.data.energy = 230


def _stainless():
    """Darker brushed steel with dried water spots (matte rings) and wet streaks (glossy)."""
    m = bpy.data.materials.get('PL_Stainless')
    if m is None or m.get('r8'):
        return
    nt = m.node_tree
    L = nt.links
    pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = pb.inputs['Base Color']
    if col.links:
        src = col.links[0].from_socket
        mul = nt.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        mul.inputs[7].default_value = (0.8, 0.81, 0.83, 1)
        L.new(src, mul.inputs[6])
        L.new(mul.outputs[2], col)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexVoronoi')
    nz.inputs['Scale'].default_value = 18.0
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    spot = nt.nodes.new('ShaderNodeMapRange')
    spot.inputs['From Min'].default_value = 0.04
    spot.inputs['From Max'].default_value = 0.0
    L.new(nz.outputs['Distance'], spot.inputs['Value'])
    rough = pb.inputs['Roughness']
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'FLOAT'
    L.new(spot.outputs[0], mx.inputs[0])
    if rough.links:
        L.new(rough.links[0].from_socket, mx.inputs[2])
    else:
        mx.inputs[2].default_value = rough.default_value
    mx.inputs[3].default_value = 0.55                       # dried spots: matte
    L.new(mx.outputs[0], rough)
    m['r8'] = True


def _curtains():
    m = bpy.data.materials.get('PL_StripCurtain')
    if m:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Base Color'].default_value = (0.66, 0.57, 0.33, 1)    # aged, yellowed PVC
        pb.inputs['Alpha'].default_value = 0.32


def _cap():
    m = bpy.data.materials.get('HUM_CapNonwoven')
    if m:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        for l in list(pb.inputs['Base Color'].links):
            m.node_tree.links.remove(l)
        pb.inputs['Base Color'].default_value = (0.24, 0.42, 0.66, 1)   # blue nonwoven bouffant cap
        pb.inputs['Roughness'].default_value = 0.85


# ------------------------------------------------------------------ props, placed only on free floor
def _blockers(C):
    out = []
    for o in C.all_objects:
        if o.type != 'MESH' or o.hide_render:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        if (hi - lo).x > 9 or (hi - lo).y > 9 or hi.z < DZ + 0.03:      # walls, floor, decals
            continue
        out.append((lo, hi))
    return out


def _free(blk, x0, x1, y0, y1, z1=None):
    for lo, hi in blk:
        if hi.x > x0 and lo.x < x1 and hi.y > y0 and lo.y < y1 and lo.z < (z1 or DZ + 2.0) and hi.z > DZ + 0.02:
            return False
    return True


def _props(C, crate_fn, blk):
    rnd = random.Random(808)
    cols = ['blue', 'blue', 'red', 'yellow', 'white', 'red', 'blue']
    n = 0
    for y in (16.5, 19.0, 24.5, 31.5, 34.5, 39.0, 43.5, 47.0, 50.5):
        for x in (XL + 0.75, XR - 0.75, CX - 4.6, CX + 4.6):
            if not _free(blk, x - 0.4, x + 0.4, y - 0.4, y + 0.4):
                continue
            h = rnd.choice((2, 3, 4, 5))
            c = rnd.choice(cols)
            for lv in range(h):
                o = crate_fn('IN_R8Crate%03d' % n, c, (x + rnd.uniform(-0.02, 0.02), y, DZ + lv * 0.3),
                             1.5708 + rnd.uniform(-0.05, 0.05), None, None, n)
                for cc in list(o.users_collection):
                    cc.objects.unlink(o)
                C.objects.link(o)
                n += 1
            blk.append((Vector((x - 0.4, y - 0.4, DZ)), Vector((x + 0.4, y + 0.4, DZ + h * 0.3))))
    # dark control cabinets / junction boxes on the side walls
    cab = Part()
    door = Part()
    for y in (18.0, 27.0, 36.5, 45.0, 52.0, 62.5):
        for x, sx in ((XL + 0.25, 1), (XR - 0.25, -1)):
            if not _free(blk, x - 0.2, x + 0.2, y - 0.45, y + 0.45, DZ + 2.2):
                continue
            cab.box((x, y, DZ + 1.35), (0.3, 0.8, 1.3))
            door.box((x + sx * 0.152, y, DZ + 1.62), (0.006, 0.22, 0.14))        # blank white panel plate
            blk.append((Vector((x - 0.2, y - 0.45, DZ)), Vector((x + 0.2, y + 0.45, DZ + 2.0))))
    cab.make('IN_R8Cabinets', P.grime_paint('IN_CabinetGrey', (0.11, 0.12, 0.13), rough=0.4, grime=0.5, streak=0.3,
                                             coat=0.3), None, bevel=0.01, coll=C)
    door.make('IN_R8CabinetPlates', bpy.data.materials.get('IN_LabelBlank'), None, coll=C)
    # yellow walkway lines continue down the cold-store aisle
    p = Part()
    for x in (CX - 1.45, CX + 1.45):
        p.box((x, 74.5, DZ + 0.003), (0.08, 18.5, 0.003))
    p.make('IN_R8ColdLines', bpy.data.materials['IN_SafetyYellow'], None, coll=C)
    # wash-down hoses lying on the floor, snaking from the wall hooks
    hose_m = bpy.data.materials.get('IN_Hose') or P.plain('IN_Hose', (0.08, 0.32, 0.12), 0.5)
    yel = P.plain('IN_HoseYellow', (0.7, 0.5, 0.05), 0.45)
    for k, (y, sx) in enumerate(((15.5, 1), (26.0, -1), (37.0, 1), (48.5, -1))):
        x0 = XL + 0.15 if sx > 0 else XR - 0.15
        pts = [(x0, y, DZ + 0.9), (x0 + sx * 0.08, y + 0.1, DZ + 0.03)]
        x, yy = x0 + sx * 0.4, y + 0.3
        for j in range(5):
            x += sx * rnd.uniform(0.35, 0.6)
            yy += rnd.uniform(-0.5, 0.5)
            pts.append((x, yy, DZ + 0.022))
        if not _free(blk, min(p[0] for p in pts[1:]), max(p[0] for p in pts[1:]),
                     min(p[1] for p in pts[1:]) - 0.05, max(p[1] for p in pts[1:]) + 0.05, DZ + 0.3):
            pts = pts[:4]
        cu = bpy.data.curves.new('IN_R8Hose%d' % k, 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 0.019
        cu.bevel_resolution = 3
        sp = cu.splines.new('NURBS')
        sp.points.add(len(pts) - 1)
        for p, v in zip(sp.points, pts):
            p.co = (v[0], v[1], v[2], 1)
        sp.use_endpoint_u = True
        sp.order_u = 3
        o = bpy.data.objects.new('IN_R8Hose%d' % k, cu)
        o.data.materials.append(hose_m if k % 2 else yel)
        C.objects.link(o)


def _cold():
    """Cold store: patchy frost on the aisle floor and the wall base, dented carton corners, white pallet labels."""
    fm = bpy.data.materials.get('IN_FloorFrost')
    if fm and not fm.get('r8'):
        nt = fm.node_tree
        pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 3.5
        nz.inputs['Detail'].default_value = 12
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.5
        mr.inputs['From Max'].default_value = 0.75
        mr.inputs['To Max'].default_value = 0.4    # thin rime in the trafficked aisle, not snow
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        for l in list(pb.inputs['Alpha'].links):
            nt.links.remove(l)
        nt.links.new(mr.outputs[0], pb.inputs['Alpha'])
        pb.inputs['Base Color'].default_value = (0.78, 0.83, 0.87, 1)
        fm['r8'] = True
    for n in ('IN_ColdCartons', 'IN_ColdStaged', 'IN_ColdWrap'):          # wrap dents with its cartons
        o = bpy.data.objects.get(n)
        if o is None or o.modifiers.get('dent'):
            continue
        tx = bpy.data.textures.get('IN_R8Dent') or bpy.data.textures.new('IN_R8Dent', 'CLOUDS')
        tx.noise_scale = 0.35
        d = o.modifiers.new('dent', 'DISPLACE')
        d.texture = tx
        d.texture_coords = 'GLOBAL'
        d.strength = 0.05
        d.mid_level = 0.6                                   # mostly inward: crushed corners, bowed faces
    o = bpy.data.objects.get('IN_ColdWall')
    C = o.users_collection[0] if o else None
    if C:
        p = Part()
        p.box(((XL + CX - 1.8) / 2, 65.17, DZ + 0.22), (CX - 1.8 - XL, 0.02, 0.44))
        p.box(((CX + 1.8 + XR) / 2, 65.17, DZ + 0.22), (XR - CX - 1.8, 0.02, 0.44))
        p.make('IN_R8WallFrost', bpy.data.materials['IN_Frost'], None, bevel=0.005, coll=C)
        lab = Part()
        ln = Part()
        rnd = random.Random(5)
        for side, xr in ((-1, CX - 2.6), (1, CX + 2.6)):
            for k in range(7):
                yy = 67.7 + k * 2.4
                for lv in range(5):
                    z = DZ + 0.26 + lv * 0.98
                    xf = xr + side * 0.1 - side * 0.016
                    yl = yy + rnd.uniform(-0.35, -0.1)
                    lab.box((xf, yl, z + 0.3), (0.004, 0.16, 0.11))
                    ln.box((xf - side * 0.003, yl, z + 0.32), (0.002, 0.12, 0.012))
                    ln.box((xf - side * 0.003, yl - 0.02, z + 0.29), (0.002, 0.08, 0.01))
        lab.make('IN_R8PalletLabels', bpy.data.materials['IN_LabelBlank'], None, coll=C)
        ln.make('IN_R8PalletLabelPrint', bpy.data.materials['IN_LabelLine'], None, coll=C)


def _puddles():
    """Standing water reads as water (thin, reflective, tinted by the floor) rather than black holes."""
    m = bpy.data.materials.get('IN_Puddle')
    if m:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Base Color'].default_value = (0.16, 0.19, 0.18, 1)
        pb.inputs['Roughness'].default_value = 0.02


def apply(scene, crate_fn):
    C = bpy.data.collections['SET_Interior']
    _lights()
    _stainless()
    _curtains()
    _cap()
    _puddles()
    blk = _blockers(C)
    if 'SET_People' in bpy.data.collections:
        blk += _blockers(bpy.data.collections['SET_People'])
    _props(C, crate_fn, blk)
    _cold()
