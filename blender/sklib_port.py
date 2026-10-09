"""Port assets for the Skylark library (ASSET_LIBRARY.md 'Port' + 'Vehicles'): containers, STS cranes, RTG, straddle
carrier, container ship, tug, quay kit, tractor + skeletal trailer, driving helpers. No lettering anywhere."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
from sklib import (M, pbr, weather, new_mat, principled, _node, _sock, mixrgb, empty, obj, box, cyl, cyl_mesh, sphere, tube,
                   bm_to_mesh, D, _link)


# ---------------------------------------------------------------- mesh builder (many parts -> one mesh)
class MB:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('col')
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _finish(self, verts, m, color):
        faces = {f for v in verts for f in v.link_faces}
        idx = self.mi(m)
        for f in faces:
            f.material_index = idx
            if color is not None:
                for lp in f.loops:
                    lp[self.col] = (*color, 1.0)
        return faces

    def box(self, c, s, m, color=None, rot=None, bevel=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = r['verts']
        mat = Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        if rot is not None:
            mat = rot.to_4x4() @ mat
        mat = Matrix.Translation(c) @ mat
        bmesh.ops.transform(self.bm, matrix=mat, verts=vs)
        self._finish(vs, m, color)
        return vs

    def beam(self, a, b, w, m, h=None, color=None):
        """Square/rect member from a to b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return
        q = d.to_track_quat('Z', 'Y')
        self.box((a + b) / 2, (w, h or w, L), m, color, rot=q.to_matrix())

    def cyl(self, a, b, r, m, seg=8, color=None, r2=None):
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                    radius2=r if r2 is None else r2, depth=L)
        q = d.to_track_quat('Z', 'Y')
        mat = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        bmesh.ops.transform(self.bm, matrix=mat, verts=res['verts'])
        fs = self._finish(res['verts'], m, color)
        for f in fs:
            f.smooth = True

    def sphere(self, c, r, m, seg=10, color=None):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r)
        bmesh.ops.translate(self.bm, verts=res['verts'], vec=c)
        self._finish(res['verts'], m, color)

    def truss(self, p0, p1, up, w, m, n, chord=0.6, web=0.3, depth=None):
        """Planar truss between two bottom-chord points p0->p1, height vector up, n panels, Warren + verticals."""
        p0, p1, up = Vector(p0), Vector(p1), Vector(up)
        self.beam(p0, p1, chord, m)
        self.beam(p0 + up, p1 + up, chord, m)
        for i in range(n + 1):
            a = p0 + (p1 - p0) * (i / n)
            self.beam(a, a + up, web, m)
            if i < n:
                b = p0 + (p1 - p0) * ((i + 1) / n)
                if i % 2 == 0:
                    self.beam(a, b + up, web, m)
                else:
                    self.beam(a + up, b, web, m)

    def obj(self, name, parent=None, loc=(0, 0, 0), smooth=False):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        _link(o)
        o.parent = parent
        o.location = loc
        return o


def paint_attr(name, rough=0.45, metal=0.0, grime=0.3, corrugate=0.0, scale=1.0):
    """Paint whose colour comes from the 'col' colour attribute (per container), with grime and optional corrugation
    bump along X (container side panels)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = pbr(name, (0.5, 0.5, 0.5), rough, metal, var=0.18, bump=0.08, scale=scale, grime=grime, attr='col')
    if corrugate:
        nt = m.node_tree
        l = nt.links
        p = principled(m)
        tc = _node(nt, 'ShaderNodeTexCoord', (-1200, -800))
        wv = _node(nt, 'ShaderNodeTexWave', (-900, -800))
        wv.wave_type = 'BANDS'
        wv.bands_direction = 'X'
        wv.wave_profile = 'TRI'
        wv.inputs['Scale'].default_value = corrugate
        l.new(_sock(tc, 'Object', out=True), wv.inputs['Vector'])
        wv2 = _node(nt, 'ShaderNodeTexWave', (-900, -1000))
        wv2.wave_type = 'BANDS'
        wv2.bands_direction = 'Y'
        wv2.wave_profile = 'TRI'
        wv2.inputs['Scale'].default_value = corrugate
        l.new(_sock(tc, 'Object', out=True), wv2.inputs['Vector'])
        add = _node(nt, 'ShaderNodeMath', (-700, -900))
        add.operation = 'MAXIMUM'
        l.new(_sock(wv, 'Factor', out=True), add.inputs[0])
        l.new(_sock(wv2, 'Factor', out=True), add.inputs[1])
        b = _node(nt, 'ShaderNodeBump', (-300, -900))
        b.inputs['Strength'].default_value = 0.35
        b.inputs['Distance'].default_value = 0.03
        l.new(add.outputs[0], b.inputs['Height'])
        l.new(b.outputs[0], p.inputs['Normal'])
    return m


CONTAINER_COLS = [(0.42, 0.08, 0.05), (0.5, 0.12, 0.06), (0.06, 0.17, 0.38), (0.05, 0.27, 0.45), (0.1, 0.3, 0.14),
                  (0.45, 0.45, 0.43), (0.62, 0.3, 0.05), (0.7, 0.55, 0.12), (0.25, 0.27, 0.3), (0.55, 0.18, 0.1),
                  (0.12, 0.35, 0.4), (0.78, 0.78, 0.76)]
REEFER_WHITE = (0.84, 0.85, 0.84)
CL, CW, CH = 12.19, 2.44, 2.59


def add_container(mb, c, m, color, reefer=False, rot_z=0.0, long=True):
    """One 40 ft box (or 20 ft if not long) centred at c (bottom at c.z), with corner posts, door end and, for reefers,
    the machinery front."""
    L = CL if long else 6.06
    R = Matrix.Rotation(rot_z, 3, 'Z')
    cx = Vector(c) + Vector((0, 0, CH / 2))
    mb.box(cx, (L - 0.04, CW - 0.04, CH - 0.04), m, color, rot=R)
    dark = tuple(v * 0.6 for v in color)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box(cx + R @ Vector((sx * (L / 2 - 0.08), sy * (CW / 2 - 0.08), 0)), (0.17, 0.17, CH), m, dark, rot=R)
    for sz in (-1, 1):
        for sy in (-1, 1):
            mb.box(cx + R @ Vector((0, sy * (CW / 2 - 0.05), sz * (CH / 2 - 0.08))), (L - 0.3, 0.1, 0.16), m, dark, rot=R)
    # corner castings (the twistlock / stacking points), a touch proud of the frame
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                mb.box(cx + R @ Vector((sx * (L / 2 - 0.09), sy * (CW / 2 - 0.09), sz * (CH / 2 - 0.06))), (0.19, 0.2, 0.13), m,
                       tuple(v * 0.45 for v in color), rot=R)
    # door bars on the -X end; a reefer's refrigeration unit sits on the +X (front) wall
    for k in (-0.75, -0.3, 0.3, 0.75):
        mb.box(cx + R @ Vector((-L / 2 - 0.03, k, 0)), (0.06, 0.06, CH - 0.35), m, (0.35, 0.36, 0.36), rot=R)   # locking rods
        mb.box(cx + R @ Vector((-L / 2 - 0.06, k + 0.08, -0.2)), (0.05, 0.2, 0.05), m, (0.3, 0.3, 0.3), rot=R)  # handle
    mb.box(cx + R @ Vector((-L / 2 - 0.015, 0, 0)), (0.02, 0.04, CH - 0.2), m, dark, rot=R)                     # door seam
    if reefer:
        mb.box(cx + R @ Vector((L / 2 + 0.02, 0, 0)), (0.06, CW - 0.4, CH - 0.5), m, (0.22, 0.24, 0.26), rot=R)
        for k in range(9):   # condenser grille slats
            mb.box(cx + R @ Vector((L / 2 + 0.06, -0.35, -0.75 + k * 0.12)), (0.02, 1.0, 0.04), m, (0.12, 0.13, 0.14), rot=R)
        mb.box(cx + R @ Vector((L / 2 + 0.04, 0.5, 0.4)), (0.05, 0.8, 0.8), m, (0.1, 0.1, 0.11), rot=R)
        for k in range(4):
            mb.box(cx + R @ Vector((L / 2 + 0.05, -0.6, -0.6 + k * 0.25)), (0.03, 0.7, 0.05), m, (0.4, 0.42, 0.44), rot=R)


def container_block(name, origin, nx, ny, heights, mat, rnd, reefer_rows=(), axis_x=True, gap=(0.35, 0.35), skip=None,
                    colors=None, parent=None):
    """A yard/ship block: nx along X (40 ft bays) x ny across (rows), heights[ix][iy] tiers. One mesh, per-box colour."""
    mb = MB()
    ox, oy, oz = origin
    for ix in range(nx):
        for iy in range(ny):
            h = heights(ix, iy) if callable(heights) else heights
            for t in range(h):
                if skip and skip(ix, iy, t):
                    continue
                ref = iy in reefer_rows
                col = REEFER_WHITE if ref else rnd.choice(colors or CONTAINER_COLS)
                col = tuple(min(1, c * rnd.uniform(0.85, 1.12)) for c in col)
                add_container(mb, (ox + ix * (CL + gap[0]), oy + iy * (CW + gap[1]), oz + t * CH), mat, col, ref)
    return mb.obj(name, parent)


# ---------------------------------------------------------------- STS crane
def sts_crane(name, loc=(0, 0, 0), mats=None, gauge=30.0, legx=9.0, girder_z=48.0, out=52.0, back=18.0, accent=None):
    """Ship-to-shore crane. Local axes: X along the quay, +Y toward the sea, z up. Origin = midway between the legs on
    the ground. Sea-side legs at y=+gauge/2. Returns dict: root, trolley (empty, moves along Y), headblock (empty,
    child of trolley, moves along Z), spreader (object), cables, y range of the trolley."""
    mats = mats or M()
    white = pbr('MAT_CraneWhite', (0.8, 0.81, 0.8), 0.45, 0.1, grime=0.4, var=0.08, scale=0.15)
    blue = accent or pbr('MAT_CraneBlue', (0.04, 0.18, 0.45), 0.45, grime=0.3, scale=0.15)
    steel = mats['steel']
    dark = pbr('MAT_CraneDark', (0.08, 0.09, 0.1), 0.5, 0.3, grime=0.2)
    root = empty(name, loc, size=5)
    mb = MB()
    ys, yl = gauge / 2, -gauge / 2
    gz = girder_z
    # legs (box columns) with bogies
    for sx in (-legx, legx):
        for y in (ys, yl):
            mb.box((sx, y, (gz - 1.0) / 2 + 1.2), (1.8, 1.8, gz - 1.0), white)
            for dx in (-2.5, 2.5):
                mb.box((sx + dx, y, 0.7), (4.2, 1.6, 1.2), blue)
                for wx in (-1.4, -0.45, 0.45, 1.4):
                    mb.cyl((sx + dx + wx, y - 0.9, 0.45), (sx + dx + wx, y + 0.9, 0.45), 0.42, dark, 12)
            mb.box((sx, y, 1.5), (7.0, 2.0, 0.8), blue)
        # portal beam + sill + diagonal bracing across (Y) at each side
        mb.box((sx, 0, 20.0), (1.6, gauge, 2.2), white)
        mb.beam((sx, ys, 21.5), (sx, yl, gz - 2), 0.8, white)
        mb.beam((sx, yl, 21.5), (sx, ys, gz - 2), 0.8, white)
    # cross beams along X at portal and top
    for y in (ys, yl):
        mb.box((0, y, 20.0), (2 * legx + 1.8, 1.6, 2.0), white)
        mb.box((0, y, gz - 1.0), (2 * legx + 1.8, 1.8, 2.0), white)
        mb.beam((-legx, y, 21), (legx, y, gz - 2.2), 0.6, white)
        mb.beam((legx, y, 21), (-legx, y, gz - 2.2), 0.6, white)
    # girder (land) on the frame; the boom (sea side) is its own object on a hinge at y1 so it can be raised
    gx = 3.6
    th = 3.6
    y0, y1 = yl - back, ys + 2
    yb = ys + out
    H = Vector((0, y1, gz))
    bmb = MB()
    sh = lambda p: Vector(p) - H
    for sx in (-gx, gx):
        mb.truss((sx, y0, gz), (sx, y1, gz), (0, 0, th), 0.9, white, int((y1 - y0) / 4.5), 0.9, 0.35)
        bmb.truss(sh((sx, y1, gz)), sh((sx, yb, gz + 0.5)), (0, 0, th - 0.6), 0.9, white, int((yb - y1) / 4.5), 0.85, 0.3)
        mb.box((sx, (y0 + y1) / 2, gz + 0.2), (0.3, y1 - y0, 0.3), steel)  # trolley rail
        bmb.box(sh((sx, (y1 + yb) / 2, gz + 0.2)), (0.3, yb - y1, 0.3), steel)
    # cross ties between the two trusses (top)
    for y in range(int(y0), int(yb), 6):
        if y < y1:
            mb.beam((-gx, y, gz + th), (gx, y, gz + th), 0.35, white)
            mb.beam((-gx, y, gz + th), (gx, y + 6, gz + th), 0.25, white)
        else:
            bmb.beam(sh((-gx, y, gz + th - 0.1)), sh((gx, y, gz + th - 0.1)), 0.35, white)
            bmb.beam(sh((-gx, y, gz + th - 0.1)), sh((gx, min(yb, y + 6), gz + th - 0.1)), 0.25, white)
    # A-frame / apex with forestays and backstays
    apex = Vector((0, ys - 4, gz + 28))
    for sx in (-legx, legx):
        mb.beam((sx, ys, gz), apex + Vector((sx * 0.25, 0, 0)), 1.4, white)
        mb.beam((sx, yl + 6, gz), apex + Vector((sx * 0.25, -1, 0)), 1.1, white)
    mb.box(apex + Vector((0, -0.5, 0)), (2 * legx * 0.25 + 2, 3, 2), white)
    for sx in (-gx, gx):
        # forestays ride with the boom (they swing up with it); backstays stay on the frame
        for yy in (ys + out * 0.5, ys + out * 0.92):
            bmb.cyl(sh(apex + Vector((sx * 0.4, 0.8, 0.3))), sh((sx, yy, gz + th - 0.6)), 0.16, steel, 8)
        mb.cyl(apex + Vector((sx * 0.4, -1.5, 0.3)), (sx, y0 + 2, gz + th), 0.18, steel, 8)
    # machinery house on the girder (backreach side)
    mh_y = yl - back / 2 + 1
    mb.box((0, mh_y, gz + th + 3.2), (10.5, 13.0, 6.0), white)
    mb.box((0, mh_y, gz + th + 0.6), (10.6, 13.1, 0.6), blue)
    for k in range(5):
        mb.box((5.27, mh_y - 5 + k * 2.5, gz + th + 3.8), (0.05, 1.2, 1.4), mats['glass'])
    # stairs zig-zag on one land leg + walkways with handrails along the girder
    for i in range(10):
        z = 3 + i * 4.4
        sy = 1 if i % 2 == 0 else -1
        mb.beam((legx + 1.6, yl - 2.2 * sy, z), (legx + 1.6, yl + 2.2 * sy, z + 4.4), 0.9, steel, h=0.12)
        mb.box((legx + 1.6, yl + 2.6 * sy, z + 4.4), (1.2, 1.2, 0.1), steel)
        mb.cyl((legx + 2.15, yl - 2.2 * sy, z + 1.0), (legx + 2.15, yl + 2.2 * sy, z + 5.4), 0.035, mats['paint_blue'], 6)
    for sx in (-gx - 1.3, gx + 1.3):
        rx = sx + math.copysign(0.45, sx)
        mb.box((sx, (y0 + y1) / 2, gz - 0.1), (1.0, y1 - y0, 0.08), steel)
        bmb.box(sh((sx, (y1 + yb) / 2, gz - 0.1)), (1.0, yb - y1, 0.08), steel)
        mb.cyl((rx, y0, gz + 1.0), (rx, y1, gz + 1.0), 0.03, blue, 6)
        bmb.cyl(sh((rx, y1, gz + 1.0)), sh((rx, yb, gz + 1.0)), 0.03, blue, 6)
        for y in range(int(y0), int(yb), 3):
            (mb if y < y1 else bmb).cyl(Vector((rx, y, gz - 0.1)) - (H if y >= y1 else Vector()),
                                        Vector((rx, y, gz + 1.0)) - (H if y >= y1 else Vector()), 0.025, blue, 5)
    # festoon cable loops under the girder
    for k in range(6):
        y = y0 + 4 + k * 2.2
        mb.cyl((gx - 1, y, gz - 0.2), (gx - 1, y, gz - 2.5 - (k % 2) * 0.6), 0.12, dark, 8)
    # warning lights
    lights = [apex + Vector((0, 0, 1.3)), Vector((0, yb, gz + th)), Vector((gx, y0, gz + th + 0.5)),
              Vector((-gx, y0, gz + th + 0.5))]
    for p in lights:
        if p.y >= y1:
            bmb.sphere(p - H, 0.35, mats['lamp_red'], 8)
        else:
            mb.sphere(p, 0.35, mats['lamp_red'], 8)
    for sx in (-legx, legx):
        mb.sphere((sx, ys, gz + 0.8), 0.3, mats['lamp_amber'], 8)
    frame = mb.obj(f'{name}_Frame', root)
    boom = empty(f'{name}_BoomHinge', tuple(H), root, size=2)
    bmb.obj(f'{name}_Boom', boom)
    # trolley + operator cabin
    trolley = empty(f'{name}_Trolley', (0, ys + 10, gz), root, size=2)
    tb = MB()
    tb.box((0, 0, 0.6), (2 * gx - 0.4, 7.0, 1.8), blue)
    for sx in (-gx + 0.6, gx - 0.6):
        for sy in (-2.5, 2.5):
            tb.cyl((sx - 0.3, sy, 0.0), (sx + 0.3, sy, 0.0), 0.45, dark, 12)
    for sy in (-2.6, 2.6):
        for sx in (-1.2, 1.2):
            tb.cyl((sx - 0.35, sy, -0.5), (sx + 0.35, sy, -0.5), 0.45, steel, 12)
    tb.box((2.2, 0, -2.4), (2.6, 3.0, 2.8), white)
    tb.box((2.2, 1.52, -2.4), (2.4, 0.05, 2.0), mats['glass'])
    tb.box((3.52, 0, -2.4), (0.05, 2.6, 2.2), mats['glass'])
    tb.box((2.2, 0, -3.8), (2.4, 2.8, 0.05), mats['glass'])
    tb.sphere((0, 3.4, 1.6), 0.3, mats['lamp_amber'], 8)
    tb.obj(f'{name}_TrolleyBody', trolley)
    # headblock + spreader (child of trolley; hangs on 4 cables)
    head = empty(f'{name}_Headblock', (0, 0, -20), trolley, size=1.5)
    hb = MB()
    hb.box((0, 0, 0.5), (3.0, 2.2, 1.0), blue)
    for sx in (-1.0, 1.0):
        for sy in (-0.6, 0.6):
            hb.cyl((sx - 0.15, sy, 0.9), (sx + 0.15, sy, 0.9), 0.35, steel, 10)
    hb.obj(f'{name}_HeadblockBody', head)
    # telescopic spreader at 40 ft: central chassis, two telescopic main beams the full box length, end beams with
    # a twistlock cone at each corner casting (bottom of the twistlocks = z -1.35 below the headblock)
    sp = MB()
    yel = weather(pbr('MAT_SpreaderYellow', (0.78, 0.55, 0.06), 0.45, 0.1, grime=0.45, scale=0.4), amount=0.4, z0=-1.4,
                  z1=-0.4, dirt_amount=0.3)
    sp.box((0, 0, -0.45), (3.6, 2.3, 0.75), yel)
    for sy in (-0.42, 0.42):
        sp.box((0, sy, -0.75), (12.1, 0.42, 0.42), yel)          # outer telescopic beams
        sp.box((0, sy, -0.75), (12.18, 0.3, 0.3), yel)
    for sx in (-6.0, 6.0):
        sp.box((sx, 0, -0.82), (0.55, 2.44, 0.55), yel)          # end beams
        for sy in (-1.08, 1.08):
            sp.box((sx, sy, -1.12), (0.3, 0.3, 0.1), steel)      # twistlock head on the casting
            sp.cyl((sx, sy, -1.17), (sx, sy, -1.35), 0.06, steel, 8, r2=0.03)
            sp.box((sx + math.copysign(0.25, sx), sy, -0.9), (0.08, 0.5, 0.45), yel)   # guide flipper
    for sx in (-1.4, 1.4):
        for sy in (-0.9, 0.9):
            sp.cyl((sx, sy, -0.05), (sx, sy, 0.25), 0.2, steel, 10)  # rope sheaves on the chassis
    spreader = sp.obj(f'{name}_Spreader', head)
    # 4 wire ropes trolley sheaves -> headblock sheaves (stretch constraints)
    cables = []
    for i, (sx, sy) in enumerate(((-1.0, -0.6), (1.0, -0.6), (-1.0, 0.6), (1.0, 0.6))):
        anchor_t = empty(f'{name}_CabT{i}', (sx * 1.2, sy * 2.6, -0.2), trolley, size=0.2)
        anchor_h = empty(f'{name}_CabH{i}', (sx, sy, 1.0), head, size=0.2)
        c = cyl(f'{name}_Cable_{i + 1}', 0.06, 1.0, (0, 0, 0), steel, 8, origin='base')
        cc = c.constraints.new('COPY_LOCATION')
        cc.target = anchor_h
        st = c.constraints.new('STRETCH_TO')
        st.target = anchor_t
        st.volume = 'NO_VOLUME'
        cables.append(c)
    return {'root': root, 'trolley': trolley, 'head': head, 'spreader': spreader, 'gz': gz, 'ys': ys, 'yl': yl,
            'yb': yb, 'y0': y0, 'y1': y1, 'frame': frame, 'boom': boom}


# ---------------------------------------------------------------- RTG, straddle carrier, light mast, gate
def rtg(name, loc=(0, 0, 0), span=23.5, h=19.0, rot_z=0.0, mats=None):
    mats = mats or M()
    white = pbr('MAT_CraneWhite', (0.8, 0.81, 0.8), 0.45, 0.1, grime=0.4, var=0.08, scale=0.15)
    blue = pbr('MAT_CraneBlue', (0.04, 0.18, 0.45), 0.45, grime=0.3, scale=0.15)
    root = empty(name, loc, size=3)
    root.rotation_euler = (0, 0, rot_z)
    mb = MB()
    for sy in (-span / 2, span / 2):
        for sx in (-3.2, 3.2):
            mb.box((sx, sy, h / 2), (1.2, 1.2, h), white)
            for wx in (-0.9, 0.9):
                mb.cyl((sx + wx, sy - 0.5, 0.75), (sx + wx, sy + 0.5, 0.75), 0.75, mats['rubber'], 14)
        mb.box((0, sy, 1.6), (8.0, 1.4, 1.2), white)
        mb.beam((-3.2, sy, 2.5), (3.2, sy, h - 1.5), 0.5, white)
    for sx in (-3.2, 3.2):
        mb.box((sx, 0, h), (1.4, span + 1.4, 1.8), white)
    mb.box((0, span / 2 - 2, h + 1.7), (6.5, 3.5, 2.4), blue)
    tb = MB()
    tb.box((0, 0, h + 1.2), (6.0, 4.0, 1.2), blue)
    tb.box((2.4, 0, h - 1.2), (1.8, 2.0, 2.2), white)
    tb.box((3.3, 0, h - 1.2), (0.05, 1.8, 1.6), mats['glass'])
    mb.obj(f'{name}_Frame', root)
    trolley = empty(f'{name}_Trolley', (0, -4, 0), root)
    tb.obj(f'{name}_TrolleyBody', trolley)
    return {'root': root, 'trolley': trolley, 'h': h}


def straddle(name, loc=(0, 0, 0), rot_z=0.0, mats=None, with_box=True, rnd=None):
    mats = mats or M()
    red = pbr('MAT_StraddleRed', (0.55, 0.08, 0.05), 0.45, grime=0.3, scale=0.3)
    root = empty(name, loc, size=2)
    root.rotation_euler = (0, 0, rot_z)
    mb = MB()
    for sy in (-2.0, 2.0):
        mb.box((0, sy, 0.8), (12.5, 0.8, 0.9), red)
        for sx in (-5.5, -1.8, 1.8, 5.5):
            mb.box((sx, sy, 6.5), (0.7, 0.7, 11.5), red)
            mb.cyl((sx, sy - 0.4, 0.75), (sx, sy + 0.4, 0.75), 0.75, mats['rubber'], 14)
        mb.box((0, sy, 12.2), (12.5, 0.9, 1.0), red)
    mb.box((0, 0, 12.9), (5.0, 4.8, 0.6), red)
    mb.box((5.5, 2.6, 11.0), (1.6, 1.6, 2.2), mats['paint_white'])
    mb.box((6.32, 2.6, 11.0), (0.05, 1.4, 1.6), mats['glass'])
    if with_box:
        add_container(mb, (0, 0, 2.2), paint_attr('MAT_ContainerPaint', corrugate=60.0),
                      (rnd or random).choice(CONTAINER_COLS))
    mb.obj(f'{name}_Body', root)
    return root


def light_mast(name, loc, h=35.0, mats=None):
    mats = mats or M()
    mb = MB()
    mb.cyl(loc, (loc[0], loc[1], loc[2] + h), 0.45, mats['steel'], 10, r2=0.25)
    mb.box((loc[0], loc[1], loc[2] + h + 0.3), (3.4, 3.4, 0.4), mats['steel'])
    for sx in (-1.2, 0, 1.2):
        for sy in (-1.2, 1.2):
            mb.box((loc[0] + sx, loc[1] + sy, loc[2] + h + 0.8), (0.9, 0.3, 0.7), mats['plastic_black'])
    return mb.obj(name)


def gatehouse(name, loc, lanes=6, lane_w=4.5, mats=None):
    """Terminal gate: canopy over the lanes, booths on islands, barrier arms (children named <name>_Barrier<i>)."""
    mats = mats or M()
    root = empty(name, loc, size=3)
    w = lanes * lane_w
    mb = MB()
    canopy = pbr('MAT_Canopy', (0.85, 0.86, 0.87), 0.4, 0.2, grime=0.2, scale=0.3)
    mb.box((0, 0, 7.0), (w + 3, 14.0, 1.0), canopy)
    mb.box((0, 0, 7.6), (w + 3.2, 14.2, 0.3), mats['paint_blue'])
    for i in range(lanes + 1):
        x = -w / 2 + i * lane_w
        mb.box((x, 0, 0.15), (1.2, 12.0, 0.3), mats['concrete'])
        for sy in (-5.5, 5.5):
            mb.box((x, sy, 3.6), (0.5, 0.5, 6.8), mats['steel'])
        if i < lanes + 1:
            mb.box((x, 1.0, 1.4), (1.0, 2.0, 2.5), mats['paint_white'])
            mb.box((x + 0.52, 1.0, 1.7), (0.05, 1.6, 1.0), mats['glass'])
            mb.box((x - 0.52, 1.0, 1.7), (0.05, 1.6, 1.0), mats['glass'])
    for i in range(lanes * 3):
        mb.box((-w / 2 + (i + 0.5) * (w / (lanes * 3)), 0, 6.45), (0.9, 12.0, 0.08), mats['lamp'])
    mb.obj(f'{name}_Canopy', root)
    barriers = []
    stripe = pbr('MAT_BarrierStripe', (0.85, 0.1, 0.06), 0.5, var=0.05)
    for i in range(lanes):
        x = -w / 2 + i * lane_w + 0.6
        piv = empty(f'{name}_Barrier{i}', (x, -2.0, 1.0), root, size=0.5)
        box(f'{name}_BarrierArm{i}', (lane_w - 1.2, 0.1, 0.1), ((lane_w - 1.2) / 2, 0, 0), stripe, 0.01, parent=piv)
        barriers.append(piv)
    return root, barriers


# ---------------------------------------------------------------- container ship
def ship_hull_mat():
    if 'MAT_ShipHull' in bpy.data.materials:
        return bpy.data.materials['MAT_ShipHull']
    from sklib_sea import hull_material
    return hull_material('MAT_ShipHull', white=(0.04, 0.06, 0.1), band=(0.04, 0.06, 0.1), bottom=(0.35, 0.06, 0.04),
                         band_z=(30, 31), boot=0.6)


def container_ship(name, loc=(0, 0, 0), L=230.0, B=32.0, deck=11.0, mats=None, rnd=None, empty_slot=None, tiers=7,
                   bays=13, detail=True):
    """Large container ship along +X (bow +X). Water line at z=0 (hull material uses object z, so keep root z=0).
    Deck stacks, lashing bridges between bays, hatch covers, aft accommodation with bridge wings, funnel.
    empty_slot=(bay, row) leaves the top slot free (crane 2's target). Returns dict: root, slot world pos."""
    mats = mats or M()
    rnd = rnd or random.Random(4)
    root = empty(name, loc, size=8)
    hm = ship_hull_mat()
    bm = bmesh.new()
    n = 48
    secs = []
    for i in range(n + 1):
        x = -L / 2 + L * i / n
        t = (x + L / 2) / L
        if t > 0.8:
            b = B / 2 * math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 1.6))
        elif t < 0.08:
            b = B / 2 * (0.82 + 0.18 * t / 0.08)
        else:
            b = B / 2
        b = max(b, 0.25)
        zk = -11.0 if t > 0.04 else -11.0 + (0.04 - t) * 120
        zt = deck + (2.5 * ((t - 0.85) / 0.15) ** 2 if t > 0.85 else 0)
        flare = 1.0 + (0.08 if t > 0.8 else 0)
        prof = [(0.0, zk), (b * 0.85, zk), (b, zk + 2.0), (b, 0.0), (b * flare, zt)]
        pts = [(-y, z) for (y, z) in reversed(prof[1:])] + prof
        secs.append([bm.verts.new((x, y, z)) for (y, z) in pts])
    for i in range(n):
        for j in range(len(secs[i]) - 1):
            bm.faces.new((secs[i][j], secs[i + 1][j], secs[i + 1][j + 1], secs[i][j + 1]))
    bm.faces.new(secs[0][::-1])
    top = [s[len(s) // 2:] for s in secs]
    me = bm_to_mesh(bm, f'{name}_Hull', smooth=True)
    me.materials.append(hm)
    h = obj(f'{name}_Hull', me, None, parent=root)
    for p in me.polygons:
        p.use_smooth = False
    # main deck plate
    box(f'{name}_DeckPlate', (L * 0.9, B - 1.0, 0.4), (-L * 0.02, 0, deck - 0.2), pbr('MAT_ShipDeck', (0.3, 0.12, 0.08), 0.6,
                                                                                    grime=0.4), 0.0, parent=root)
    cmat = paint_attr('MAT_ContainerPaint', corrugate=60.0)
    grey = pbr('MAT_ShipGrey', (0.5, 0.52, 0.52), 0.5, 0.2, grime=0.35, scale=0.2)
    mb = MB()
    rows = int(B // (CW + 0.06))
    x0 = -L / 2 + 50
    pitch = CL + 2.0
    slot = None
    for bi in range(bays):
        bx = x0 + bi * pitch
        mb.box((bx, 0, deck + 0.4), (CL + 0.4, B - 2, 0.8), grey)  # hatch cover
        if bi > 0:
            lb = bx - pitch / 2
            for lv in (1, 2):
                mb.box((lb, 0, deck + 0.8 + lv * CH - CH / 2), (0.15, B - 2, 0.15), grey)
            for r in range(rows + 1):
                y = -B / 2 + 1 + r * (B - 2) / rows
                mb.box((lb, y, deck + 0.8 + CH), (0.8, 0.15, 2 * CH), grey)
        base_t = tiers - (2 if bi in (0, bays - 1) else 0)
        for r in range(rows):
            y = -B / 2 + 1 + (r + 0.5) * (B - 2) / rows
            t_here = max(2, base_t - (1 if r in (0, rows - 1) else 0) - (rnd.random() < 0.15))
            for t in range(t_here):
                if empty_slot and bi == empty_slot[0] and r == empty_slot[1] and t == t_here - 1:
                    slot = Vector((bx, y, deck + 0.8 + t * CH))
                    continue
                reef = (bi in (bays - 3, bays - 2) and r < rows // 2) or (bi == 2 and t >= t_here - 2)
                col = REEFER_WHITE if reef else rnd.choice(CONTAINER_COLS)
                col = tuple(min(1, c * rnd.uniform(0.82, 1.1)) for c in col)
                add_container(mb, (bx, y, deck + 0.8 + t * CH), cmat, col, reef, rot_z=math.pi / 2 if False else 0.0)
    stacks = mb.obj(f'{name}_Stacks', root)
    # stacks run along X (40 ft along the ship)
    # accommodation block + bridge wings + funnel (aft)
    ax = -L / 2 + 22
    white = pbr('MAT_ShipWhite', (0.85, 0.86, 0.85), 0.4, grime=0.3, scale=0.2)
    acc = MB()
    acc.box((ax, 0, deck + 13), (16, 24, 26), white)
    for lvl in range(7):
        z = deck + 3 + lvl * 3.3
        acc.box((ax + 8.02, 0, z), (0.05, 20, 1.1), mats['glass'])
        for sy in (-12.02, 12.02):
            acc.box((ax, sy, z), (12, 0.05, 1.1), mats['glass'])
    acc.box((ax + 2, 0, deck + 27), (12, B + 4, 2.5), white)  # bridge with wings
    acc.box((ax + 8.1, 0, deck + 27.2), (0.05, B + 2, 1.3), mats['glass'])
    acc.box((ax - 2, 0, deck + 30), (6, 8, 4), white)
    acc.cyl((ax - 2, 0, deck + 32), (ax - 2, 0, deck + 38), 0.25, mats['steel'], 8)
    acc.sphere((ax - 2, 0, deck + 38.3), 0.35, mats['lamp_red'], 8)
    acc.box((ax - 12, 0, deck + 9), (8, 10, 18), pbr('MAT_Funnel', (0.12, 0.13, 0.15), 0.5, grime=0.3))
    acc.box((ax - 12, 0, deck + 18.2), (8.2, 10.2, 0.5), white)
    acc.box((L / 2 - 14, 0, deck + 3.5), (6, B - 8, 3.5), white)  # forecastle break
    acc.obj(f'{name}_Superstructure', root)
    return {'root': root, 'slot': slot, 'deck': deck, 'L': L, 'B': B}


def tug(name, loc=(0, 0, 0), rot_z=0.0, mats=None):
    mats = mats or M()
    from sklib_sea import vessel, hull_material
    hm = hull_material('MAT_TugHull', white=(0.55, 0.06, 0.04), band=(0.05, 0.05, 0.06), bottom=(0.06, 0.06, 0.07),
                       band_z=(2.0, 2.6), boot=0.25)
    R = vessel(name, loc, rot_z, mats=mats, hull=hm, detail=False, L=24.0)
    # tug: drop the fishing gear look by adding a big fender bow and a tall wheelhouse
    root = R['root']
    box(f'{name}_Fender', (1.6, 6.2, 1.2), (11.2, 0, 1.6), mats['rubber'], 0.4, parent=root)
    box(f'{name}_Wheel2', (3.5, 4.2, 2.4), (-6.5, 0, 7.0), mats['paint_white'], 0.08, parent=root)
    return R


def bollard_mesh():
    if 'LIB_Bollard' in bpy.data.meshes:
        return bpy.data.meshes['LIB_Bollard']
    mb = MB()
    m = pbr('MAT_BollardBlack', (0.05, 0.05, 0.05), 0.5, 0.4, grime=0.3)
    mb.cyl((0, 0, 0), (0, 0, 0.75), 0.3, m, 14)
    mb.cyl((0, 0, 0.75), (0, 0, 0.9), 0.42, m, 14)
    o = mb.obj('LIB_Bollard')
    me = o.data
    bpy.data.objects.remove(o)
    return me


# ---------------------------------------------------------------- tractor + skeletal trailer
def tractor(name, loc=(0, 0, 0), rot_z=0.0, color=(0.85, 0.85, 0.84), mats=None, driver=True):
    """Day-cab tractor unit, facing +X, origin under the rear axle at ground. Returns (root, wheels)."""
    mats = mats or M()
    paint = pbr(f'MAT_Tractor_{name}', color, 0.3, 0.2, grime=0.25, coat=0.6, scale=0.5)
    root = empty(name, loc, size=1.5)
    root.rotation_euler = (0, 0, rot_z)
    mb = MB()
    mb.box((1.6, 0, 1.05), (6.2, 0.9, 0.3), mats['steel'])
    mb.box((3.9, 0, 2.05), (2.0, 2.45, 2.3), paint)  # cab
    mb.box((3.95, 0, 1.15), (2.1, 2.48, 0.6), paint)
    mb.box((4.92, 0, 2.5), (0.06, 2.1, 0.9), mats['glass'])  # windscreen
    for sy in (-1.23, 1.23):
        mb.box((4.1, sy, 2.4), (1.1, 0.04, 0.7), mats['glass'])
        mb.box((5.0, sy * 1.18, 2.6), (0.08, 0.06, 0.45), mats['plastic_black'])  # mirrors
    mb.box((4.97, 0, 1.3), (0.06, 2.2, 0.55), mats['steel'])  # grille
    for sy in (-0.9, 0.9):
        mb.box((4.98, sy, 1.05), (0.04, 0.35, 0.18), mats['lamp'])
    mb.box((2.6, 0, 3.0), (0.3, 1.0, 0.8), mats['steel'])  # exhaust/air deflector stub
    mb.cyl((2.75, 1.0, 1.4), (2.75, 1.0, 3.6), 0.1, mats['steel'], 8)
    mb.box((0.0, 0, 1.25), (1.6, 1.8, 0.12), mats['plastic_black'])  # fifth wheel
    for sy in (-1.05, 1.05):
        mb.box((2.3, sy * 1.12, 1.1), (1.4, 0.25, 0.55), mats['steel'])  # tanks
    body = mb.obj(f'{name}_Body', root)
    wheels = []
    wm = cyl_mesh(f'{name}_WheelM', 0.52, 0.32, 20, axis='Y', bevel=0.04)
    wm.materials.append(mats['rubber'])
    for x in (0.0, 4.0):
        for sy in (-1.0, 1.0):
            wheels.append(obj(f'{name}_Wheel', wm, None, (x, sy, 0.52), parent=root))
            if x == 0.0:
                wheels.append(obj(f'{name}_Wheel', wm, None, (x, sy * 0.66, 0.52), parent=root))
    if driver:
        from sklib import person, pose
        d = person(f'{name}_Driver', 'driver', (4.0, 0.55, 0.6), 0.0, mats=mats)
        d.parent = root
        pose(d, 'sit')
    return root, wheels


def skeletal_trailer(name, parent, mats=None, length=12.5):
    """3-axle skeletal chassis behind a tractor (fifth wheel at the tractor's origin). Returns (trailer root, wheels)."""
    mats = mats or M()
    root = empty(f'{name}', (0.4, 0, 0), parent, size=1)
    mb = MB()
    for sy in (-0.5, 0.5):
        mb.box((-length / 2 + 0.6, sy, 1.15), (length, 0.25, 0.35), mats['steel'])
    for x in (-length + 0.8, -length / 2, 0.4):
        mb.box((x, 0, 1.25), (0.25, 2.4, 0.2), mats['steel'])
    mb.box((-2.2, 0.9, 0.7), (0.15, 0.15, 0.9), mats['steel'])
    mb.box((-2.2, -0.9, 0.7), (0.15, 0.15, 0.9), mats['steel'])
    mb.box((-length + 0.5, 0, 0.85), (0.15, 2.4, 0.3), mats['lamp_red'])
    mb.obj(f'{name}_Chassis', root)
    wheels = []
    wm = bpy.data.meshes.get('LIB_TrailerWheel') or cyl_mesh('LIB_TrailerWheel', 0.52, 0.3, 20, axis='Y', bevel=0.04)
    if not wm.materials:
        wm.materials.append(mats['rubber'])
    for x in (-length + 1.6, -length + 2.9, -length + 4.2):
        for sy in (-1.0, -0.66, 0.66, 1.0):
            wheels.append(obj(f'{name}_Wheel', wm, None, (x, sy, 0.52), parent=root))
    return root, wheels


def reefer_box(name, parent, loc=(0, 0, 0), mats=None):
    """The hero white 40 ft reefer as its own object (so the crane can carry it). Origin at the bottom centre."""
    mb = MB()
    m = paint_attr('MAT_ContainerPaint', corrugate=60.0)
    add_container(mb, (0, 0, 0), m, REEFER_WHITE, True)
    o = mb.obj(name, parent, loc)
    return o


def drive(root, path, f0, f1, wheels=(), r=0.52, ease=True, keystep=2, stop_hold=0, reverse=False):
    """Move a vehicle along a polyline (forward only unless reverse) between frames f0..f1, heading follows the path,
    wheels rotate from the distance travelled. ease=True: smooth start and stop."""
    pts = [Vector((p[0], p[1], p[2] if len(p) > 2 else root.location.z)) for p in path]
    # densify with a simple Catmull-Rom so turns are smooth
    dense = []
    for i in range(len(pts) - 1):
        p0, p1 = pts[max(0, i - 1)], pts[i]
        p2, p3 = pts[i + 1], pts[min(len(pts) - 1, i + 2)]
        for k in range(12):
            t = k / 12
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense.append(pts[-1])
    cum = [0.0]
    for i in range(1, len(dense)):
        cum.append(cum[-1] + (dense[i] - dense[i - 1]).length)
    total = cum[-1]
    prev = None
    for f in list(range(f0, f1, keystep)) + [f1]:
        u = (f - f0) / max(1, (f1 - f0))
        if ease:
            u = u * u * (3 - 2 * u)
        d = total * u
        k = 0
        while k < len(cum) - 2 and cum[k + 1] < d:
            k += 1
        seg = cum[k + 1] - cum[k]
        a = dense[k] + (dense[k + 1] - dense[k]) * ((d - cum[k]) / seg if seg else 0)
        dv = dense[k + 1] - dense[k]
        if reverse:
            dv = -dv
        rz = math.atan2(dv.y, dv.x)
        if prev is not None:
            while rz - prev > math.pi:
                rz -= 2 * math.pi
            while rz - prev < -math.pi:
                rz += 2 * math.pi
        prev = rz
        root.location = a
        root.rotation_euler = (0, 0, rz)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        for w in wheels:
            w.rotation_euler = (0, (-1 if reverse else 1) * d / r, 0)
            w.keyframe_insert('rotation_euler', frame=f)
    return total


# ---------------------------------------------------------------- wake
def wake_mat(name='MAT_WakeFoam'):
    """White water: churned foam in the propeller wash, broken streaks further back, fading to nothing (alpha)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = new_mat(name)
    nt = m.node_tree
    l = nt.links
    p = principled(m)
    p.inputs['Base Color'].default_value = (0.86, 0.9, 0.92, 1)
    p.inputs['Roughness'].default_value = 0.55
    uv = _node(nt, 'ShaderNodeTexCoord', (-1400, 0))
    sep = _node(nt, 'ShaderNodeSeparateXYZ', (-1200, -300))
    l.new(_sock(uv, 'UV', out=True), sep.inputs[0])
    # streaky foam: noise stretched along the wake (u = along, v = across)
    mp = _node(nt, 'ShaderNodeMapping', (-1200, 200))
    mp.inputs['Scale'].default_value = (3.0, 28.0, 1.0)
    l.new(_sock(uv, 'UV', out=True), mp.inputs['Vector'])
    nz = _node(nt, 'ShaderNodeTexNoise', (-1000, 200))
    nz.inputs['Scale'].default_value = 6.0
    nz.inputs['Detail'].default_value = 12
    nz.inputs['Roughness'].default_value = 0.7
    l.new(mp.outputs[0], nz.inputs['Vector'])
    vr = _node(nt, 'ShaderNodeTexVoronoi', (-1000, 500))
    vr.inputs['Scale'].default_value = 60.0
    vr.feature = 'F1'
    l.new(mp.outputs[0], vr.inputs['Vector'])
    fm = _node(nt, 'ShaderNodeMath', (-800, 300))
    fm.operation = 'MULTIPLY'
    l.new(_sock(nz, 'Factor', out=True), fm.inputs[0])
    l.new(_sock(vr, 'Distance', out=True), fm.inputs[1])
    th = _node(nt, 'ShaderNodeMapRange', (-600, 300))
    th.inputs['From Min'].default_value = 0.12
    th.inputs['From Max'].default_value = 0.5
    l.new(fm.outputs[0], th.inputs['Value'])
    # fade: strong at the stern (u = 0), gone by u = 1; edges soft across (v 0..1, centre 0.5)
    fu = _node(nt, 'ShaderNodeMapRange', (-900, -300))
    fu.inputs['From Min'].default_value = 0.0
    fu.inputs['From Max'].default_value = 1.0
    fu.inputs['To Min'].default_value = 1.0
    fu.inputs['To Max'].default_value = 0.0
    fu.interpolation_type = 'SMOOTHSTEP'
    l.new(sep.outputs[0], fu.inputs['Value'])
    cv = _node(nt, 'ShaderNodeMath', (-900, -500))
    cv.operation = 'PINGPONG'
    cv.inputs[1].default_value = 0.5
    l.new(sep.outputs[1], cv.inputs[0])
    ce = _node(nt, 'ShaderNodeMapRange', (-700, -500))
    ce.inputs['From Min'].default_value = 0.0
    ce.inputs['From Max'].default_value = 0.35
    ce.interpolation_type = 'SMOOTHSTEP'
    l.new(cv.outputs[0], ce.inputs['Value'])
    a1 = _node(nt, 'ShaderNodeMath', (-500, -300))
    a1.operation = 'MULTIPLY'
    l.new(fu.outputs[0], a1.inputs[0])
    l.new(ce.outputs[0], a1.inputs[1])
    a2 = _node(nt, 'ShaderNodeMath', (-300, 0))
    a2.operation = 'MULTIPLY'
    l.new(a1.outputs[0], a2.inputs[0])
    l.new(th.outputs[0], a2.inputs[1])
    # churned zone right behind the stern is nearly solid white
    ch = _node(nt, 'ShaderNodeMapRange', (-700, -800))
    ch.inputs['From Min'].default_value = 0.0
    ch.inputs['From Max'].default_value = 0.12
    ch.inputs['To Min'].default_value = 0.75
    ch.inputs['To Max'].default_value = 0.0
    l.new(sep.outputs[0], ch.inputs['Value'])
    a3 = _node(nt, 'ShaderNodeMath', (-150, -200))
    a3.operation = 'MAXIMUM'
    l.new(a2.outputs[0], a3.inputs[0])
    l.new(ch.outputs[0], a3.inputs[1])
    a4 = _node(nt, 'ShaderNodeMath', (0, -200))
    a4.operation = 'MULTIPLY'
    l.new(a3.outputs[0], a4.inputs[0])
    l.new(ce.outputs[0], a4.inputs[1])
    a5 = _node(nt, 'ShaderNodeMath', (100, -200))
    a5.operation = 'MULTIPLY'
    a5.inputs[1].default_value = 0.85
    l.new(a4.outputs[0], a5.inputs[0])
    l.new(a5.outputs[0], p.inputs['Alpha'])
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'BLENDED'
    return m


def wake(name, parent, stern_x, length=320.0, w0=14.0, w1=70.0, z=0.15, kelvin=True):
    """Turbulent wake trailing behind -X of the parent from stern_x, widening w0 -> w1, plus two Kelvin arms
    (19.5 degrees). UV u runs along the wake. Returns the object (origin at the stern; scale X to grow it)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    nu, nv = 60, 8

    def strip(length, wa, wb, ang=0.0, off=0.0):
        rows = []
        for i in range(nu + 1):
            u = i / nu
            x = -u * length
            w = wa + (wb - wa) * u
            row = []
            for j in range(nv + 1):
                v = j / nv
                y = (v - 0.5) * w
                c, s_ = math.cos(ang), math.sin(ang)
                row.append((bm.verts.new((x * c - y * s_, x * s_ + y * c + off, z)), u, v))
            rows.append(row)
        for i in range(nu):
            for j in range(nv):
                f = bm.faces.new((rows[i][j][0], rows[i + 1][j][0], rows[i + 1][j + 1][0], rows[i][j + 1][0]))
                for lp, (uu, vv) in zip(f.loops, ((rows[i][j][1], rows[i][j][2]), (rows[i + 1][j][1], rows[i + 1][j][2]),
                                                  (rows[i + 1][j + 1][1], rows[i + 1][j + 1][2]),
                                                  (rows[i][j + 1][1], rows[i][j + 1][2]))):
                    lp[uvl].uv = (uu, vv)
    strip(length, w0, w1)
    if kelvin:
        for sg in (1, -1):
            strip(length * 0.6, w0 * 0.6, w0 * 2.4, ang=sg * math.radians(19.5), off=0.0)
    me = bm_to_mesh(bm, name)
    me.materials.append(wake_mat())
    o = obj(name, me, None, (stern_x, 0, 0), parent=parent)
    return o
