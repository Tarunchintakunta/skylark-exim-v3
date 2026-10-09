"""Build assets-src/blender/port.blend (docs/BLENDER_GLB_SPEC.md §3).

Run headless from the repo root:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/blender/port_build.py
Everything is procedural and every move is baked per frame from the functions in this file, so the reefer is
exactly on its spreader, cables always reach the spreader corners, the truck only moves forward, and the ship is
static for frames 1–192. Units: metres, +Z up. Quay edge on y = 0, sea at y > 0, quay deck at z = 3.
No text, logos or numbers are modelled anywhere.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'assets-src', 'blender', 'port.blend')
random.seed(7)

# ------------------------------------------------------------------ helpers
def clean():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)

def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

def mat(name, rgb, metal=0.0, rough=0.5, attr=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if attr:  # per-face colour from a colour attribute (one material for all containers)
        n = nt.nodes.new('ShaderNodeVertexColor'); n.layer_name = attr
        nt.links.new(n.outputs['Color'], b.inputs['Base Color'])
    return m

def obj(name, me, c, m=None, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    if m and me is not None: me.materials.append(m)
    o.parent = parent
    o.location = loc
    return o

def empty(name, c, parent=None, loc=(0, 0, 0)):
    return obj(name, None, c, parent=parent, loc=loc)

def add_box(bm, center, size, color=None, layer=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    for v in vs:
        v.co = Vector((v.co.x * size[0] + center[0], v.co.y * size[1] + center[1], v.co.z * size[2] + center[2]))
    if color is not None and layer is not None:
        faces = {f for v in vs for f in v.link_faces}
        for f in faces:
            for l in f.loops: l[layer] = (*color, 1)

def add_cyl(bm, a, b, r, segs=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    for v in res['verts']:
        v.co = q @ v.co + (a + b) / 2

def mesh_from(name, build, colored=False):
    bm = bmesh.new()
    layer = bm.loops.layers.color.new('Col') if colored else None
    build(bm, layer)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if colored:
        me.color_attributes.active_color_name = 'Col'
    for p in me.polygons: p.use_smooth = False
    return me

ease = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
lerp = lambda a, b, t: a + (b - a) * t
def seg(f, f0, f1):  # eased 0..1 over [f0, f1]
    return ease((f - f0) / (f1 - f0))

# ------------------------------------------------------------------ dimensions (guidance only, never site copy)
CL, CW, CH = 12.19, 2.44, 2.9          # container
DECK = 3.0                             # quay deck height above water
LANE_Y = -18.0                         # truck lane between crane legs
SEA_LEG_Y, LAND_LEG_Y = -3.0, -33.0    # rail gauge 30 m
BOOM_Z = 50.0
CRANES_X = (-100.0, 0.0, 100.0)
SHIP_Y = 26.0                          # ship centreline
SHIP_L, SHIP_B, SHIP_FB = 270.0, 40.0, 14.0   # length, beam, deck height above water
SHIP_X0 = 30.0
TIERS = 5
STACK_TOP = SHIP_FB + TIERS * CH       # top of on-deck stacks
SLOT = (0.0, SHIP_Y - 2 * CW - 0.4)    # hero slot (x, y) on top of the bay under crane 2

# ------------------------------------------------------------------ materials
M = dict(
    concrete=mat('Concrete', (0.33, 0.33, 0.32), 0, 0.85),
    lane=mat('LanePaint', (0.85, 0.82, 0.7), 0, 0.7),
    crane=mat('CraneWhite', (0.86, 0.88, 0.9), 0.2, 0.45),
    crane_blue=mat('CraneBlue', (0.08, 0.28, 0.55), 0.2, 0.45),
    steel=mat('SteelDark', (0.22, 0.24, 0.26), 0.7, 0.45),
    cable=mat('Cable', (0.08, 0.08, 0.09), 0.8, 0.4),
    reefer=mat('ReeferWhite', (0.93, 0.94, 0.95), 0.15, 0.38),
    unit=mat('ReeferUnit', (0.62, 0.65, 0.68), 0.6, 0.35),
    cab=mat('CabWhite', (0.95, 0.95, 0.95), 0.1, 0.3),
    glass=mat('Glass', (0.12, 0.16, 0.2), 0.2, 0.08),
    tyre=mat('Tyre', (0.03, 0.03, 0.03), 0, 0.8),
    hull=mat('HullDark', (0.07, 0.1, 0.14), 0.2, 0.5),
    antifoul=mat('HullRed', (0.5, 0.1, 0.08), 0.1, 0.55),
    accom=mat('AccomWhite', (0.94, 0.95, 0.95), 0.1, 0.4),
    boxes=mat('Containers', (1, 1, 1), 0.15, 0.55, attr='Col'),
    fender=mat('Fender', (0.04, 0.04, 0.04), 0, 0.9),
)

# ------------------------------------------------------------------ scene
clean()
sc = bpy.context.scene
C_QUAY, C_CR, C_TRUCK, C_REEF, C_SHIP, C_WATER, C_SKY = (coll(n) for n in ('Quay', 'Cranes', 'Truck', 'Reefer', 'Ship', 'Water', 'Sky'))

# quay apron, crane rails, fenders, bollards, lane lines, light masts, yard stacks
def quay(bm, layer):
    add_box(bm, (0, -60, DECK / 2 - 1), (1400, 120, DECK + 2))
me = mesh_from('QuayApron', quay); obj('QuayApron', me, C_QUAY, M['concrete'])
def rails(bm, layer):
    for y in (SEA_LEG_Y, LAND_LEG_Y):
        add_box(bm, (0, y, DECK + 0.08), (1400, 0.25, 0.16))
    for x in range(-690, 700, 18):
        add_box(bm, (x, 0.35, DECK - 1.2), (2.4, 0.7, 1.8))   # fenders
        add_box(bm, (x + 9, -1.2, DECK + 0.4), (0.6, 0.6, 0.8))  # bollards
    for i in range(-80, 80):  # dashed lane edges, no text
        add_box(bm, (i * 9, LANE_Y - 2.2, DECK + 0.01), (4.5, 0.2, 0.02))
        add_box(bm, (i * 9, LANE_Y + 2.2, DECK + 0.01), (4.5, 0.2, 0.02))
me = mesh_from('QuayDetail', rails); obj('QuayDetail', me, C_QUAY, M['steel'])
def masts(bm, layer):
    for x in range(-600, 650, 130):
        add_box(bm, (x + 40, -95, DECK + 15), (0.6, 0.6, 30))
        add_box(bm, (x + 40, -95, DECK + 30.3), (3, 1.2, 0.6))
me = mesh_from('LightMasts', masts); obj('LightMasts', me, C_QUAY, M['steel'])
YARD_COLS = [(0.55, 0.14, 0.11), (0.1, 0.27, 0.48), (0.13, 0.4, 0.3), (0.52, 0.55, 0.57), (0.75, 0.38, 0.12), (0.92, 0.93, 0.94)]
def yard(bm, layer):
    for bx in range(-560, 600, 70):
        for row in range(6):
            for bay in range(4):
                h = random.randint(1, 4)
                for t in range(h):
                    add_box(bm, (bx + bay * (CL + 0.6), -125 - row * (CW + 0.3) * 1.0 - (row // 2) * 6, DECK + CH / 2 + t * CH), (CL, CW, CH), random.choice(YARD_COLS), layer)
me = mesh_from('YardStacks', yard, colored=True); obj('YardStacks', me, C_QUAY, M['boxes'])

# ------------------------------------------------------------------ ship (static mesh, parent empty moves in shot 2)
ship = empty('Ship', C_SHIP, loc=(SHIP_X0, SHIP_Y, 0))
def outline(n=48):
    # deck plan: parallel midbody, faired bow to +X, rounded stern at -X
    h, pts = SHIP_B / 2, []
    for i in range(n + 1):  # starboard side, stern → bow
        u = i / n
        x = -SHIP_L / 2 + u * SHIP_L
        w = h * (1 - max(0.0, (u - 0.8) / 0.2) ** 1.8) if u > 0.8 else h * (0.86 + 0.14 * math.sin(min(1, u / 0.06) * math.pi / 2))
        pts.append((x, -max(w, 0.4)))
    return pts + [(x, -y) for x, y in reversed(pts)]
def hull(bm, layer):
    vs = [bm.verts.new((x, y, -1.0)) for x, y in outline()]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, SHIP_FB + 1.0), verts=top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = mesh_from('Hull', hull); obj('Hull', me, C_SHIP, M['hull'], ship)
def boot(bm, layer):
    vs = [bm.verts.new((x * 1.002, y * 1.004, -0.5)) for x, y in outline()]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, 0, 2.0), verts=[e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = mesh_from('Boottop', boot); obj('Boottop', me, C_SHIP, M['antifoul'], ship)
def accom(bm, layer):
    ax = -SHIP_L / 2 + 30
    add_box(bm, (ax, 0, SHIP_FB + 12), (14, SHIP_B * 0.7, 24))
    add_box(bm, (ax + 1, 0, SHIP_FB + 25), (10, SHIP_B + 4, 2.4))  # bridge wings
    add_box(bm, (ax - 10, 0, SHIP_FB + 8), (5, 4, 16))              # funnel
me = mesh_from('Accommodation', accom); obj('Accommodation', me, C_SHIP, M['accom'], ship)
STACK_COLS = [(0.6, 0.15, 0.12), (0.1, 0.27, 0.5), (0.12, 0.42, 0.31), (0.5, 0.53, 0.55), (0.78, 0.4, 0.12), (0.35, 0.2, 0.3)]
WHITE = (0.93, 0.94, 0.95)
def stacks(bm, layer):
    bays = range(-9, 10)
    rows = range(-7, 8)
    for b in bays:
        bxw = SHIP_X0 + b * (CL + 1.2)  # world x of bay (ship static in shot 1)
        x = b * (CL + 1.2)
        if x < -SHIP_L / 2 + 42 or x > SHIP_L / 2 - 28: continue
        for r in rows:
            y = r * (CW + 0.06)
            reefer_row = r in (-7, -6, 6, 7) or (b % 3 == 0 and r in (-1, 0))
            h = TIERS if abs(b) % 4 else TIERS - 1
            for t in range(h):
                # leave the hero slot (top tier, row nearest the quay, bay under crane 2) empty
                if abs(bxw - SLOT[0]) < 3 and abs((SHIP_Y + y) - SLOT[1]) < 0.5 and t == TIERS - 1: continue
                col = WHITE if reefer_row else random.choice(STACK_COLS)
                add_box(bm, (x, y, SHIP_FB + CH / 2 + t * CH), (CL, CW, CH - 0.02), col, layer)
me = mesh_from('DeckStacks', stacks, colored=True); obj('DeckStacks', me, C_SHIP, M['boxes'], ship)
def lashing(bm, layer):
    for b in range(-9, 10):
        x = b * (CL + 1.2) + CL / 2 + 0.6
        if -SHIP_L / 2 + 42 < x < SHIP_L / 2 - 28:
            add_box(bm, (x, 0, SHIP_FB + 4), (0.4, SHIP_B - 2, 8))
me = mesh_from('LashingBridges', lashing); obj('LashingBridges', me, C_SHIP, M['steel'], ship)

# ------------------------------------------------------------------ container mesh (shared by the hero reefer and crane loads)
def container_mesh(name, reefer):
    def b(bm, layer):
        add_box(bm, (0, 0, 0), (CL, CW, CH))
        for i in range(-24, 25):  # corrugation ribs on the long sides
            for s in (-1, 1):
                add_box(bm, (i * 0.245, s * (CW / 2 + 0.02), 0), (0.1, 0.04, CH - 0.25))
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    add_box(bm, (sx * (CL / 2 - 0.09), sy * (CW / 2 - 0.08), sz * (CH / 2 - 0.06)), (0.2, 0.18, 0.14))
        for k in (-0.5, -0.17, 0.17, 0.5):  # door locking bars on the rear end (-X)
            add_box(bm, (-CL / 2 - 0.04, k * CW * 0.9, 0), (0.06, 0.05, CH - 0.3))
    me = mesh_from(name, b)
    if reefer:  # refrigeration unit flush on the front end (+X): grille + fan housing + blank panel
        def u(bm, layer):
            add_box(bm, (CL / 2 + 0.06, 0, -0.1), (0.14, CW - 0.25, CH - 0.6))
            add_cyl(bm, (CL / 2 + 0.1, 0.45, 0.45), (CL / 2 + 0.2, 0.45, 0.45), 0.42, 16)
            add_box(bm, (CL / 2 + 0.15, -0.6, 0.6), (0.06, 0.5, 0.35))
        return me, mesh_from(name + 'Unit', u)
    return me, None

hero_me, hero_unit = container_mesh('Reefer', True)
reefer = obj('Reefer', hero_me, C_REEF, M['reefer'])
obj('ReeferUnit', hero_unit, C_REEF, M['unit'], reefer)
load_me, _ = container_mesh('CraneLoad', False)

# ------------------------------------------------------------------ truck: tractor + skeletal chassis (moves forward along +X only)
truck = empty('Truck', C_TRUCK)
WHEEL_R = 0.52
def tractor(bm, layer):
    add_box(bm, (5.4, 0, 2.15), (2.2, 2.5, 2.6))   # cab
    add_box(bm, (3.0, 0, 1.15), (6.4, 1.1, 0.35))  # frame
    add_box(bm, (6.65, 0, 1.4), (0.3, 2.4, 1.0))   # bumper/grille block (blank)
    add_box(bm, (6.3, 1.38, 2.6), (0.08, 0.25, 0.5)); add_box(bm, (6.3, -1.38, 2.6), (0.08, 0.25, 0.5))  # mirrors
me = mesh_from('Tractor', tractor); obj('Tractor', me, C_TRUCK, M['cab'], truck)
def windows(bm, layer):
    add_box(bm, (6.51, 0, 2.75), (0.03, 2.2, 0.9))
me = mesh_from('CabGlass', windows); obj('CabGlass', me, C_TRUCK, M['glass'], truck)
def chassis(bm, layer):
    add_box(bm, (-5.6, 0, 1.25), (12.5, 1.0, 0.3))
    add_box(bm, (-5.6, 0.95, 1.25), (12.5, 0.12, 0.25)); add_box(bm, (-5.6, -0.95, 1.25), (12.5, 0.12, 0.25))
    for x in (1.2, -11.6):
        add_box(bm, (x, 0, 1.3), (0.3, 2.3, 0.25))
    add_box(bm, (-2.0, 0.8, 0.6), (0.2, 0.2, 1.0)); add_box(bm, (-2.0, -0.8, 0.6), (0.2, 0.2, 1.0))  # landing legs
me = mesh_from('Chassis', chassis); obj('Chassis', me, C_TRUCK, M['steel'], truck)
wheels = []
for x in (5.4, 2.0, 0.6, -9.0, -10.4, -11.8):
    for s in (-1, 1):
        def w(bm, layer, x=x, s=s):
            add_cyl(bm, (0, -0.3, 0), (0, 0.3, 0), WHEEL_R, 18)
        o = obj(f'Wheel{len(wheels)}', mesh_from('Wheel', w), C_TRUCK, M['tyre'], truck, loc=(x, s * 1.05, WHEEL_R))
        wheels.append(o)
TRUCK_DECK = 1.4  # container bottom above the quay deck

# ------------------------------------------------------------------ cranes
def crane_static(name):
    def b(bm, layer):
        for y in (SEA_LEG_Y, LAND_LEG_Y):
            for x in (-8.5, 8.5):
                add_box(bm, (x, y, DECK + 22), (1.6, 1.6, 44))            # legs
                add_box(bm, (x, y, DECK + 0.8), (3.2, 2.0, 1.6))          # bogie
            add_box(bm, (0, y, DECK + 44), (18.6, 1.8, 2.0))              # portal beams
        for x in (-8.5, 8.5):
            add_box(bm, (x, (SEA_LEG_Y + LAND_LEG_Y) / 2, DECK + 20), (1.2, 30, 1.2))  # sill beams
            add_box(bm, (x, -10, DECK + BOOM_Z - DECK + 0.0), (1.4, 120, 2.4))         # boom/girder (y -70 .. +50)
            add_cyl(bm, (x, (SEA_LEG_Y + LAND_LEG_Y) / 2, BOOM_Z + 1), (x * 0.4, -12, BOOM_Z + 22), 0.6)  # A-frame
            add_cyl(bm, (x * 0.4, -12, BOOM_Z + 22), (x, 40, BOOM_Z + 1), 0.25, 6)     # forestays
            add_cyl(bm, (x * 0.4, -12, BOOM_Z + 22), (x, -62, BOOM_Z + 1), 0.25, 6)    # backstays
        for i in range(-34, 26):  # boom cross members
            add_box(bm, (0, i * 2, BOOM_Z - 1.0), (17, 0.25, 0.25))
        add_box(bm, (0, -58, BOOM_Z + 3), (14, 12, 6))                    # machinery house
    me = mesh_from(name, b)
    return me
crane_me = crane_static('CraneFrame')
def accent(bm, layer):
    for x in (-8.5, 8.5):
        add_box(bm, (x, -10, BOOM_Z + 1.3), (1.42, 120, 0.25))
me_accent = mesh_from('CraneAccent', accent)

TROLLEY_LAND, TROLLEY_LANE, TROLLEY_SHIP = -50.0, LANE_Y, SLOT[1]
HB_UP = BOOM_Z - 6.0  # spreader top when fully raised
cranes = []
for i, cx in enumerate(CRANES_X):
    root = empty(f'Crane_{i + 1}', C_CR, loc=(cx, 0, 0))
    obj(f'Crane_{i + 1}_Frame', crane_me, C_CR, M['crane'], root)
    obj(f'Crane_{i + 1}_Accent', me_accent, C_CR, M['crane_blue'], root)
    def tr(bm, layer):
        add_box(bm, (0, 0, 0), (16, 6, 3))
        add_box(bm, (0, -1, -3.2), (3, 3, 2.6))  # operator cab under the trolley
    trolley = obj(f'Crane_{i + 1}_Trolley', mesh_from('Trolley', tr), C_CR, M['crane_blue'], root, loc=(0, TROLLEY_LAND, BOOM_Z - 1.5))
    def hbm(bm, layer):
        add_box(bm, (0, 0, 0), (4, 2.0, 0.8))
    headblock = obj(f'Crane_{i + 1}_Headblock', mesh_from('Headblock', hbm), C_CR, M['steel'], trolley, loc=(0, 0, -5))
    def spm(bm, layer):
        add_box(bm, (0, 0, 0), (CL, CW, 0.5))
        for sx in (-1, 1):
            for sy in (-1, 1):
                add_box(bm, (sx * (CL / 2 - 0.4), sy * (CW / 2 - 0.3), 0.55), (0.6, 0.5, 0.6))
    spreader = obj(f'Crane_{i + 1}_Spreader', mesh_from('Spreader', spm), C_CR, M['crane_blue'], root)
    cables = []
    for k, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        def cm(bm, layer):
            add_cyl(bm, (0, 0, 0), (0, 0, 1), 0.045, 6)  # unit length along +Z, scaled per frame
        cables.append(obj(f'Crane_{i + 1}_Cable{k}', mesh_from('Cable', cm), C_CR, M['cable'], root))
    load = obj(f'Crane_{i + 1}_Load', load_me, C_CR, M['boxes'], root) if i != 1 else None
    if load:  # coloured load: give it a flat colour via its own material
        load.data = load_me.copy(); load.data.materials.clear(); load.data.materials.append(mat(f'Load{i}', random.choice(STACK_COLS), 0.15, 0.55))
    cranes.append(dict(root=root, trolley=trolley, headblock=headblock, spreader=spreader, cables=cables, load=load, x=cx))

# ------------------------------------------------------------------ water, sky, sun
def water(bm, layer):
    r = bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in r['verts']:
        v.co = Vector((v.co.x * 20000 + 5000, v.co.y * 14000 + 3000, 0))
me = mesh_from('Sea', water)
wm = bpy.data.materials.new('SeaWater'); wm.use_nodes = True
nt = wm.node_tree; bsdf = nt.nodes['Principled BSDF']
bsdf.inputs['Roughness'].default_value = 0.06
tc = nt.nodes.new('ShaderNodeTexCoord')
# harbour green-blue near the quay → bright deep blue open sea (by world Y)
sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 30; mr.inputs['From Max'].default_value = 260
nt.links.new(sep.outputs['Y'], mr.inputs['Value'])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.035, 0.12, 0.13, 1)
ramp.color_ramp.elements[1].color = (0.03, 0.16, 0.44, 1)
nt.links.new(mr.outputs['Result'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'; noise.inputs['Scale'].default_value = 0.08; noise.inputs['Detail'].default_value = 8
nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35
nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
noise.inputs['W'].default_value = 0
noise.inputs['W'].keyframe_insert('default_value', frame=1)
noise.inputs['W'].default_value = 4
noise.inputs['W'].keyframe_insert('default_value', frame=383)
me.materials.append(wm)
sea = obj('Sea', me, C_WATER)

# wake: V-shaped foam plane behind the stern + bow wave, parented to the ship, opacity keyed with speed
foam = bpy.data.materials.new('Foam'); foam.use_nodes = True
fnt = foam.node_tree; fb = fnt.nodes['Principled BSDF']
fb.inputs['Base Color'].default_value = (0.95, 0.97, 0.98, 1); fb.inputs['Roughness'].default_value = 0.6
ftc = fnt.nodes.new('ShaderNodeTexCoord')
fsep = fnt.nodes.new('ShaderNodeSeparateXYZ'); fnt.links.new(ftc.outputs['UV'], fsep.inputs[0])
fnoise = fnt.nodes.new('ShaderNodeTexNoise'); fnoise.inputs['Scale'].default_value = 18; fnoise.inputs['Detail'].default_value = 6
fnt.links.new(ftc.outputs['UV'], fnoise.inputs['Vector'])
# alpha = noise × fade along the wake (u) × narrow band near the centre that widens with distance
fthr = fnt.nodes.new('ShaderNodeMapRange'); fthr.inputs['From Min'].default_value = 0.48; fthr.inputs['From Max'].default_value = 0.62
fnt.links.new(fnoise.outputs['Fac'], fthr.inputs['Value'])
fmath = fnt.nodes.new('ShaderNodeMath'); fmath.operation = 'MULTIPLY'
fnt.links.new(fthr.outputs['Result'], fmath.inputs[0])
fade = fnt.nodes.new('ShaderNodeMath'); fade.operation = 'SUBTRACT'; fade.inputs[0].default_value = 1.0
fnt.links.new(fsep.outputs['X'], fade.inputs[1]); fnt.links.new(fade.outputs[0], fmath.inputs[1])
gain = fnt.nodes.new('ShaderNodeMath'); gain.operation = 'MULTIPLY'; gain.inputs[1].default_value = 0.0
fnt.links.new(fmath.outputs[0], gain.inputs[0]); fnt.links.new(gain.outputs[0], fb.inputs['Alpha'])
for attr in ('surface_render_method',):
    if hasattr(foam, attr): setattr(foam, attr, 'BLENDED')
def wake(bm, layer):
    pass
wake_me = bpy.data.meshes.new('Wake')
L, W0, W1 = 700.0, SHIP_B * 0.6, SHIP_B * 3.5
verts = [(-SHIP_L / 2, -W0 / 2, 0.15), (-SHIP_L / 2, W0 / 2, 0.15), (-SHIP_L / 2 - L, W1 / 2, 0.15), (-SHIP_L / 2 - L, -W1 / 2, 0.15)]
wake_me.from_pydata(verts, [], [(0, 1, 2, 3)])
uv = wake_me.uv_layers.new(); uvs = [(0, 0), (0, 1), (1, 1), (1, 0)]
for li, l in enumerate(wake_me.loops): uv.data[li].uv = uvs[l.vertex_index]
wake_me.materials.append(foam)
obj('Wake', wake_me, C_WATER, parent=ship)

world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World'); sc.world = world
world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes['Background']
sky = wnt.nodes.new('ShaderNodeTexSky')
for k, v in (('sun_elevation', math.radians(42)), ('sun_rotation', math.radians(205)), ('altitude', 50.0)):
    try: setattr(sky, k, v)
    except Exception: pass
wnt.links.new(sky.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.15
sun_data = bpy.data.lights.new('Sun', 'SUN'); sun_data.energy = 3.2; sun_data.angle = math.radians(1.2)
sun = obj('Sun', sun_data, C_SKY); sun.rotation_euler = Euler((math.radians(48), 0, math.radians(205 - 180)))

# ------------------------------------------------------------------ camera
cam_data = bpy.data.cameras.new('Cam'); cam_data.lens = 32; cam_data.clip_end = 20000; cam_data.clip_start = 0.5
cam = obj('Cam', cam_data, C_SKY); sc.camera = cam

# ------------------------------------------------------------------ animation (baked per frame)
F_END = 383
def truck_x(f):          # one direction only (+X), eased to a stop under crane 2 at f60
    return lerp(-150.0, CRANES_X[1], seg(f, 1, 60))
def ship_pos(f):         # static for shot 1; eases off the quay, then sails ahead (+X)
    if f <= 192: return Vector((SHIP_X0, SHIP_Y, 0))
    t = (f - 192)
    off = 320 * ease(min(1, t / 150))                # away from the quay, out to open water
    ahead = 0.12 * t * t / 2 if t < 60 else 0.12 * 60 * 60 / 2 + 7.2 * (t - 60)  # accelerate, then cruise
    return Vector((SHIP_X0 + ahead, SHIP_Y + off, 0))

def hero(f):
    """crane 2: trolley y, spreader bottom z, and where the reefer is."""
    lane_top = DECK + TRUCK_DECK + CH   # container top on the truck
    slot_top = STACK_TOP + CH           # container top once set on the ship stack (tier 5 top)
    high = STACK_TOP + CH + 8
    ty = lerp(TROLLEY_LAND, TROLLEY_LANE, seg(f, 30, 70))
    sz = HB_UP
    if f >= 70: sz = lerp(HB_UP, lane_top + 0.02, seg(f, 70, 96))
    if f >= 96: sz = lane_top - 0.02 * math.sin(min(1, (f - 96) / 10) * math.pi)  # seat (2 cm dip)
    if f >= 106: sz = lerp(lane_top, high, seg(f, 106, 130))
    if f >= 130: ty = lerp(TROLLEY_LANE, TROLLEY_SHIP, seg(f, 130, 162)); sz = high
    if f >= 162: ty = TROLLEY_SHIP; sz = lerp(high, slot_top, seg(f, 162, 184))
    if f >= 186: sz = lerp(slot_top, slot_top + 1.0, seg(f, 186, 192))
    if f > 192: sz = lerp(slot_top + 1.0, HB_UP, seg(f, 192, 240)); ty = lerp(TROLLEY_SHIP, TROLLEY_LAND, seg(f, 210, 280))
    attached = 98 <= f <= 186
    sway = math.radians(0.8) * math.sin((f - 130) / 9) * (1 if 130 <= f <= 170 else 0)
    return ty, sz, attached, sway

def worker(f, phase):
    """cranes 1 and 3: endless lift cycle between the lane and the ship, load always on its 4 cables."""
    T = 150.0
    u = ((f + phase) % T) / T
    lane_top, ship_top = DECK + 1.4 + CH, STACK_TOP + CH + 0.4
    high = STACK_TOP + CH + 8
    if u < 0.2: ty, top = TROLLEY_LANE, lerp(high, lane_top, ease(u / 0.2))
    elif u < 0.35: ty, top = TROLLEY_LANE, lerp(lane_top, high, ease((u - 0.2) / 0.15))
    elif u < 0.55: ty, top = lerp(TROLLEY_LANE, SLOT[1] - CW - 0.4, ease((u - 0.35) / 0.2)), high
    elif u < 0.7: ty, top = SLOT[1] - CW - 0.4, lerp(high, ship_top, ease((u - 0.55) / 0.15))
    elif u < 0.82: ty, top = SLOT[1] - CW - 0.4, lerp(ship_top, high, ease((u - 0.7) / 0.12))
    else: ty, top = lerp(SLOT[1] - CW - 0.4, TROLLEY_LANE, ease((u - 0.82) / 0.18)), high
    return ty, top

def set_crane(c, ty, spreader_bottom, sway=0.0, load=None):
    c['trolley'].location = (0, ty, BOOM_Z - 1.5)
    sp = Vector((0, ty, spreader_bottom))
    c['spreader'].location = sp
    c['spreader'].rotation_euler = (sway, 0, 0)
    hb = Vector((0, ty, BOOM_Z - 1.5 - 5))  # headblock world-ish (crane root space)
    for k, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        top = hb + Vector((sx * 1.6, sy * 0.8, -0.4))
        bot = sp + Vector((sx * (CL / 2 - 0.4), sy * (CW / 2 - 0.3), 0.85))
        d = top - bot
        cab = c['cables'][k]
        cab.location = bot
        cab.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        cab.scale = (1, 1, d.length)
    if load is not None:
        load.location = sp - Vector((0, 0, CH / 2))
        load.rotation_euler = (sway, 0, 0)

def cam_at(f, ship_at):
    """Cam A low on the quay → rises with the container → straight top-down tracking the ship → climbs."""
    tx = truck_x(f)
    if f <= 106:
        pos = Vector((lerp(-38, -16, seg(f, 1, 106)), -37, DECK + 3.6 + 6 * seg(f, 70, 106)))
        ty_, sz_, _, _ = hero(f)
        tgt = Vector((lerp(tx, 0, seg(f, 50, 70)), LANE_Y + 2, lerp(DECK + 3, sz_ - 2, seg(f, 66, 100))))
    elif f <= 192:
        u = seg(f, 106, 192)
        pos = Vector((lerp(-16, -45, u), lerp(-37, -20, u), lerp(DECK + 9.6, 85, u)))
        cont = Vector((0, lerp(LANE_Y, SLOT[1], seg(f, 130, 162)), STACK_TOP + 6))
        tgt = cont.lerp(Vector((10, SLOT[1] + 10, STACK_TOP)), seg(f, 150, 192))
    else:
        u = seg(f, 192, 240)
        s = ship_at
        top_down = Vector((s.x + 10, s.y + 4, lerp(85, 260, u)))
        pos = Vector((-45, -20, 85)).lerp(top_down, u)
        if f > 330:
            pos.z = 260 * (1 + 3 * seg(f, 330, 383))
        tgt = Vector((s.x + 10, s.y + 4.01, 0))
        if u >= 1 or f > 240:
            return Vector((s.x + 10, s.y + 4, pos.z)), None
        return pos, tgt
    return pos, tgt

def key(o, f, loc=True, rot=True, scale=False):
    if loc: o.keyframe_insert('location', frame=f)
    if rot: o.keyframe_insert('rotation_euler', frame=f)
    if scale: o.keyframe_insert('scale', frame=f)

prev_tx = truck_x(1)
for f in range(1, F_END + 1):
    sc.frame_set(f)
    # truck: forward only; wheels roll with distance travelled
    tx = truck_x(f)
    assert tx >= prev_tx - 1e-6, 'truck must never reverse'
    prev_tx = tx
    truck.location = (tx, LANE_Y, DECK); key(truck, f, rot=False)
    for w in wheels:
        w.rotation_euler = (0, (tx - truck_x(1)) / WHEEL_R, 0); key(w, f, loc=False)
    # ship
    sp = ship_pos(f); ship.location = sp; key(ship, f, rot=False)
    speed = (ship_pos(f + 1) - sp).length
    gain.inputs[1].default_value = min(1.0, speed / 6.0) * 0.9
    gain.inputs[1].keyframe_insert('default_value', frame=f)
    # crane 2 + hero reefer
    c2 = cranes[1]
    ty, sz, attached, sway = hero(f)
    set_crane(c2, ty, sz, sway)
    if f < 98:
        reefer.location = (tx, LANE_Y, DECK + TRUCK_DECK + CH / 2); reefer.rotation_euler = (0, 0, 0)
    elif attached:
        reefer.location = (CRANES_X[1], ty, sz - CH / 2); reefer.rotation_euler = (sway, 0, 0)
    else:  # released on the ship: rides with the ship from now on
        reefer.location = sp + Vector((SLOT[0] - SHIP_X0, SLOT[1] - SHIP_Y, STACK_TOP + CH / 2 - CH))
        reefer.location.z = STACK_TOP - CH / 2 + CH
        reefer.rotation_euler = (0, 0, 0)
    key(reefer, f)
    for o in (c2['trolley'], c2['spreader']): key(o, f)
    for cab in c2['cables']: key(cab, f, scale=True)
    # cranes 1 and 3 keep working, phase-offset
    for c, ph in ((cranes[0], 40), (cranes[2], 115)):
        ty, top = worker(f, ph)
        set_crane(c, ty, top, 0.0, c['load'])
        for o in (c['trolley'], c['spreader'], c['load']): key(o, f)
        for cab in c['cables']: key(cab, f, scale=True)
    # camera
    pos, tgt = cam_at(f, sp)
    cam.location = pos
    if tgt is None:
        cam.rotation_euler = (0, 0, math.radians(35))  # straight down (−90° pitch), ship crossing diagonally
    else:
        cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    key(cam, f)

# make every curve smooth-linear between baked keys (they are per-frame anyway)
for a in bpy.data.actions:
    for fc in getattr(a, 'fcurves', []):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

# ------------------------------------------------------------------ render settings (§3.4)
r = sc.render
sc.render.engine = 'BLENDER_EEVEE'
r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
r.fps = 24
sc.frame_start, sc.frame_end = 1, F_END
ee = sc.eevee
for k, v in (('taa_render_samples', 64), ('use_raytracing', True), ('use_bloom', False), ('use_volumetric_shadows', False)):
    try: setattr(ee, k, v)
    except Exception: pass
try: ee.ray_tracing_options.resolution_scale = '2'
except Exception: pass
r.use_motion_blur = True
try: r.motion_blur_shutter = 0.5
except Exception: pass
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.view_settings.exposure = -0.9
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.compression = 15
r.filepath = '//../render/port/'

sc.frame_set(1)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('saved', OUT)
