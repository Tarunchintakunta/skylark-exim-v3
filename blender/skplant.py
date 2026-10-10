"""The processing plant set shared by truck-reverse, p-intake, p-proc and p-freeze (one deterministic build, identical
object names in every file so boundary frames match). World layout, metres:
  front (dock) wall on y = 0, building interior +Y, yard -Y; dock floor z = 1.2; bays centred on BAYS (x).
  Dock hall y 0..12 -> intake hall (behind bay 2) -> processing hall -> lab / freezing / packing / cold store.
No text, logos or numbers anywhere (painted lines and hazard stripes only)."""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import skpbr as P
from sktruck import Part

DZ = 1.2                                   # dock floor height
BAYS = [-9.2, -4.6, 0.0, 4.6, 9.2, 13.8]  # bay centres (x)
TRUCK_BAY = 9.2                            # our truck ("bay 2", counting from the gate side)
CAM_BAY = 4.6                              # the open neighbouring door the camera passes through ("bay 3")
OPEN = (-9.2, 0.0, 4.6, 9.2)               # doors raised
X0, X1 = -24.0, 22.0                       # dock building extent
HT = 8.6                                   # building height
DOOR_W, DOOR_H = 3.0, 3.3


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def panel_mat(name='PL_Panel', color=(0.80, 0.82, 0.83), seam=1.0, axis='X', grime=0.25):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = P.grime_paint(name, color, rough=0.32, grime=grime, streak=0.18, coat=0.25, metal=0.15)
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = axis
    wv.wave_profile = 'SAW'
    wv.inputs['Scale'].default_value = 1.0 / seam
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.94
    mr.inputs['From Max'].default_value = 1.0
    L.new(wv.outputs['Fac'], mr.inputs['Value'])
    # fine ribs (micro-profiled panel)
    wv2 = nt.nodes.new('ShaderNodeTexWave')
    wv2.wave_type = 'BANDS'
    wv2.bands_direction = axis
    wv2.inputs['Scale'].default_value = 1.0 / seam * 8
    L.new(tc.outputs['Object'], wv2.inputs['Vector'])
    ad = nt.nodes.new('ShaderNodeMath')
    ad.operation = 'MULTIPLY_ADD'
    ad.inputs[1].default_value = 0.08
    L.new(wv2.outputs['Fac'], ad.inputs[0])
    L.new(mr.outputs[0], ad.inputs[2])
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = 0.5
    b.inputs['Distance'].default_value = 0.01
    L.new(ad.outputs[0], b.inputs['Height'])
    L.new(b.outputs[0], p.inputs['Normal'])
    return m


def hazard_mat(name='PL_Hazard', a=(0.72, 0.52, 0.04), b=(0.02, 0.02, 0.02), scale=4.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'DIAGONAL'
    wv.wave_profile = 'SAW'
    wv.inputs['Scale'].default_value = scale
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.5
    L.new(wv.outputs['Fac'], gt.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    L.new(gt.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (*a, 1)
    mx.inputs[7].default_value = (*b, 1)
    L.new(mx.outputs[2], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.5
    return m


def line_mat(name, color, alpha=0.9):
    """Worn road paint: noise eats into the paint."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = 0.6
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 6
    nz.inputs['Detail'].default_value = 10
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.3
    mr.inputs['From Max'].default_value = 0.42
    mr.inputs['To Max'].default_value = alpha
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    L.new(mr.outputs[0], p.inputs['Alpha'])
    m.surface_render_method = 'DITHERED'
    return m


def MATS():
    return {
        'panel': panel_mat(),
        'panel_grey': panel_mat('PL_PanelGrey', (0.42, 0.45, 0.48), axis='X'),
        'panel_in': panel_mat('PL_PanelInside', (0.86, 0.88, 0.89), axis='X', grime=0.08),
        'plinth': P.tex_mat('PL_DockFace', 'painted_concrete', scale=0.25, sat=0.0, tint=(0.62, 0.63, 0.63), rough=0.7, normal=0.4, dirt=0.25),
        'apron': P.tex_mat('PL_Apron', 'concrete_floor_02', scale=0.22, sat=0.5, tint=(0.95, 0.94, 0.92), dirt=0.2,
                           dirt_scale=0.04),
        'asphalt': P.tex_mat('PL_Asphalt', 'asphalt_02', scale=0.18, sat=0.4, tint=(0.8, 0.8, 0.82), macro=0.2, dirt_scale=0.03),
        'rubber': P.tex_mat('PL_Rubber', 'Rubber004', scale=2.0, tint=(0.22, 0.22, 0.23), metal=0.0),
        'shelter': P.tex_mat('PL_ShelterPVC', 'Rubber004', scale=1.0, tint=(0.12, 0.125, 0.13), metal=0.0, rough_mul=0.8),
        'yellow': P.grime_paint('PL_Yellow', (0.75, 0.52, 0.04), rough=0.4, grime=0.5, streak=0.3, coat=0.2),
        'hazard': hazard_mat(),
        'steel': P.tex_mat('PL_Steel', 'Metal012', scale=1.0, metal=1.0, rough_mul=1.0),
        'stainless': P.tex_mat('PL_Stainless', 'Metal009', scale=1.2, tint=(0.95, 0.96, 0.97), metal=1.0, rough_mul=0.6,
                               aniso=0.6),
        'galv': P.plain('PL_Galv', (0.55, 0.57, 0.58), 0.4, 1.0, bump=0.1),
        'dark': P.plain('PL_DarkGrey', (0.05, 0.055, 0.06), 0.5, 0.2),
        'door': panel_mat('PL_SectionalDoor', (0.78, 0.8, 0.82), seam=0.55, axis='Z', grime=0.2),
        'glass': P.plain('PL_Glass', (0.03, 0.045, 0.055), 0.03, 0.0, coat=1.0),
        'line_white': line_mat('PL_LineWhite', (0.85, 0.85, 0.82)),
        'line_yellow': line_mat('PL_LineYellow', (0.8, 0.58, 0.05)),
        'epoxy': P.plain('PL_Epoxy', (0.50, 0.55, 0.58), 0.16, coat=0.7, bump=0.03, bump_scale=3),
        'curtain': P.plain('PL_StripCurtain', (0.45, 0.6, 0.64), 0.05, 0.0, alpha=0.12, coat=0.35),   # clear PVC, no milky haze
        'led': P.plain('PL_LED', (1, 1, 1), 0.3, emission=(0.94, 0.97, 1.0), estr=18.0),
        'lamp_ext': P.plain('PL_WallLamp', (1, 1, 1), 0.3, emission=(1.0, 0.97, 0.92), estr=6.0),
        'lamp_red': P.plain('PL_SigRed', (0.3, 0.02, 0.02), 0.2, emission=(1, 0.05, 0.02), estr=3.0),
        'lamp_green': P.plain('PL_SigGreen', (0.02, 0.3, 0.05), 0.2, emission=(0.05, 1, 0.2), estr=4.0),
        'grass': P.tex_mat('PL_Grass', 'sparse_grass', scale=0.4, sat=0.8),
        'roof': P.tex_mat('PL_Roof', 'box_profile_metal_sheet', scale=0.4, sat=0.0, tint=(0.8, 0.82, 0.84), metal=0.6),
        'fence': P.plain('PL_FenceGreen', (0.08, 0.16, 0.12), 0.5, 0.4),
        'wood': P.plain('PL_PalletWood', (0.42, 0.32, 0.2), 0.8, bump=0.4, bump_scale=12),
        'carton': P.plain('PL_Carton', (0.62, 0.5, 0.35), 0.85, bump=0.15, bump_scale=30),
        'blue_plastic': P.plain('PL_BluePlastic', (0.05, 0.16, 0.42), 0.45),
        'unit': P.grime_paint('PL_RoofUnit', (0.62, 0.64, 0.65), rough=0.4, grime=0.4, streak=0.3, coat=0.1),
        'pipe': P.plain('PL_PipeInsul', (0.75, 0.76, 0.76), 0.35, 0.6),
    }


def _ground(M, C):
    p = Part()
    p.box((-1.0, -9.6, -0.05), (46, 19.2, 0.1))
    p.make('PL_ApronSlab', M['apron'], None, coll=C)
    p = Part()
    p.box((-8.25, -25.25, -0.055), (63.5, 12.5, 0.1))      # yard asphalt in front of the apron
    p.box((-32.0, -9.6, -0.055), (16, 19.2, 0.1))          # beside the office
    p.box((75.0, -10.0, -0.055), (103, 8.5, 0.1))          # road out of the gate
    p.box((60.0, -60.0, -0.055), (8.5, 92, 0.1))           # cross road
    p.make('PL_Asphalt', M['asphalt'], None, coll=C)
    p = Part()
    p.box((0, 0, -0.08), (700, 700, 0.1))
    p.make('PL_Land', P.tex_mat('PL_LandDirtGrass', 'aerial_grass_rock', scale=0.08, sat=0.75, tint=(0.95, 0.92, 0.85),
                                macro=0.25, dirt_scale=0.01), None, coll=C)
    # painted lines: bay guides, apron edge, walkway hatch
    p = Part()
    for b in BAYS:
        for sx in (-1, 1):
            p.box((b + sx * 2.3, -7.0, 0.006), (0.12, 13.6, 0.01))
    p.box((0, -18.6, 0.006), (60, 0.15, 0.01))
    for i in range(10):
        p.box((-17.0, -1.0 - i * 0.6, 0.006), (3.0, 0.3, 0.01))
    p.make('PL_LinesWhite', M['line_white'], None, coll=C)
    p = Part()
    p.box((0, -19.0, 0.006), (60, 0.15, 0.01))
    for b in BAYS:
        p.box((b, -0.9, 0.006), (2.6, 0.12, 0.01))
    p.make('PL_LinesYellow', M['line_yellow'], None, coll=C)
    # verges with grass along the fence lines
    p = Part()
    p.box((-10, -33.5, 0.02), (64, 3.0, 0.06))
    p.box((25.5, -24.0, 0.02), (3.0, 16, 0.06))
    p.box((25.5, -2.6, 0.02), (3.0, 5.2, 0.06))
    p.make('PL_Verge', M['grass'], None, coll=C)
    p = Part()
    p.box((-10, -32.0, 0.06), (64, 0.18, 0.14))
    p.make('PL_Kerb', M['plinth'], None, bevel=0.02, coll=C)


def _building(M, C):
    # front wall pieces around the door openings
    p = Part()
    xs = [X0] + sum([[b - DOOR_W / 2, b + DOOR_W / 2] for b in BAYS], []) + [X1]
    for a, b in zip(xs[0::2], xs[1::2]):
        if b - a > 0.01:
            p.box(((a + b) / 2, 0.08, DZ + DOOR_H / 2), (b - a, 0.16, DOOR_H))
    p.box(((X0 + X1) / 2, 0.08, (DZ + DOOR_H + HT) / 2), (X1 - X0, 0.16, HT - DZ - DOOR_H))
    p.make('PL_FrontWall', M['panel'], None, coll=C)
    p = Part()
    p.box(((X0 + X1) / 2, 0.1, DZ / 2), (X1 - X0, 0.2, DZ))
    p.make('PL_DockPlinth', M['plinth'], None, bevel=0.02, coll=C)
    # grey band at the top + parapet cap
    p = Part()
    p.box(((X0 + X1) / 2, -0.01, HT - 0.6), (X1 - X0 + 0.02, 0.06, 1.2))
    p.make('PL_TopBand', M['panel_grey'], None, coll=C)
    p = Part()
    p.box(((X0 + X1) / 2, -0.04, HT + 0.03), (X1 - X0 + 0.1, 0.12, 0.08))
    for x in (X0, X1):
        p.box((x, 0.0, HT / 2), (0.14, 0.14, HT))
    p.make('PL_Flashing', M['galv'], None, bevel=0.01, coll=C)
    # side walls + roof (big boxes; only their outsides are ever seen)
    p = Part()
    p.box((X0 - 0.08, 35, HT / 2), (0.16, 70, HT))
    p.box((X1 + 0.08, 35, HT / 2), (0.16, 70, HT))
    p.make('PL_SideWalls', panel_mat('PL_PanelSide', (0.80, 0.82, 0.83), axis='Y'), None, coll=C)
    p = Part()
    p.box(((X0 + X1) / 2, 35, HT + 0.05), (X1 - X0, 70, 0.1))
    p.make('PL_Roof', M['roof'], None, coll=C)
    # office block (left end), two floors of strip windows
    p = Part()
    p.box((-29.5, 8, 3.6), (11, 16, 7.2))
    p.make('PL_Office', panel_mat('PL_OfficePanel', (0.84, 0.85, 0.85), seam=1.5), None, coll=C)
    p = Part()
    for z in (1.6, 5.0):
        p.box((-29.5, -0.02, z), (9.6, 0.06, 1.3))
    p.box((X0 - 0.2, -0.02, 2.6), (0.06, 0.06, 0.06))
    p.make('PL_OfficeGlass', M['glass'], None, coll=C)
    p = Part()
    for z in (1.6, 5.0):
        for i in range(9):
            p.box((-34.2 + i * 1.2, -0.06, z), (0.05, 0.05, 1.32))
        p.box((-29.5, -0.06, z - 0.66), (9.7, 0.08, 0.05))
        p.box((-29.5, -0.06, z + 0.66), (9.7, 0.08, 0.05))
    p.make('PL_OfficeMullions', M['galv'], None, coll=C)
    # personnel door + landing + steps at x -17
    p = Part()
    p.box((-17.0, -1.0, DZ / 2), (2.4, 2.0, DZ))
    for i in range(6):
        p.box((-15.3 + 0.0, -1.0 - 0.0, 0.1 + i * 0.2), (0.3 + 0.0, 1.4, 0.2))
    p.make('PL_Landing', M['plinth'], None, bevel=0.01, coll=C)
    p = Part()
    p.box((-17.0, -0.02, DZ + 1.05), (1.0, 0.08, 2.1))
    p.make('PL_PersonnelDoor', M['panel_grey'], None, bevel=0.01, coll=C)
    p = Part()
    p.cyl((-18.2, -2.0, DZ), (-18.2, -2.0, DZ + 1.0), 0.025)
    p.cyl((-15.8, -2.0, DZ), (-15.8, -2.0, DZ + 1.0), 0.025)
    p.cyl((-18.2, -2.0, DZ + 1.0), (-15.8, -2.0, DZ + 1.0), 0.025)
    p.make('PL_Rail', M['yellow'], None, coll=C)
    # canopy over the docks
    p = Part()
    p.box((2.3, -1.6, 5.45), (24.6, 3.2, 0.12))
    p.make('PL_Canopy', M['roof'], None, coll=C)
    p = Part()
    p.box((2.3, -3.18, 5.4), (24.7, 0.08, 0.3))
    for x in [-9.9 + i * 4.1 for i in range(7)]:
        p.cyl((x, -3.1, 5.45), (x, 0.0, 7.4), 0.02, 6)
    p.make('PL_CanopyEdge', M['galv'], None, coll=C)
    # refrigerant pipes along the facade + down pipes
    p = Part()
    for z in (6.75, 7.05):
        p.cyl((X0 + 1, -0.25, z), (X1 - 0.5, -0.25, z), 0.09, 12)
    p.cyl((X1 - 0.5, -0.25, 6.75), (X1 - 0.5, -0.25, HT + 0.6), 0.09, 12)
    p.cyl((X1 - 0.5, -0.25, 7.05), (X1 - 0.8, -0.25, HT + 0.6), 0.09, 12)
    p.make('PL_Pipes', M['pipe'], None, smooth=True, coll=C)
    p = Part()
    for x in [X0 + 1 + i * 3.0 for i in range(15)]:
        p.box((x, -0.15, 6.9), (0.05, 0.3, 0.6))
    for x in (-13.8, -2.3, 11.5, 20.0):
        p.cyl((x, -0.12, 0.05), (x, -0.12, HT), 0.06, 10)
    p.make('PL_Brackets', M['galv'], None, coll=C)
    # roof plant (condensers) peeking over the parapet
    p = Part()
    for x in (-14, -6, 6, 14):
        p.box((x, 4.0, HT + 0.9), (3.2, 1.6, 1.6))
    p.make('PL_RoofUnits', M['unit'], None, bevel=0.03, coll=C)
    p = Part()
    for x in (-14, -6, 6, 14):
        for dx in (-0.8, 0.8):
            p.cyl((x + dx, 4.0, HT + 1.71), (x + dx, 4.0, HT + 1.74), 0.6, 24)
    p.make('PL_RoofFans', M['dark'], None, coll=C)


def _bays(M, C):
    for i, b in enumerate(BAYS):
        tag = 'PL_Bay%d' % i
        # shelter: side pads + header, black PVC, two yellow guide stripes on the side pads
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * 1.68, -0.32, DZ + 1.55), (0.42, 0.62, 3.6))
        p.box((b, -0.32, DZ + 3.55), (3.8, 0.62, 0.55))
        p.make(tag + '_Shelter', M['shelter'], None, bevel=0.04, coll=C)
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * 1.46, -0.64, DZ + 1.6), (0.05, 0.02, 3.0))
            p.box((b + sx * 1.62, -0.64, DZ + 1.6), (0.05, 0.02, 3.0))
        p.make(tag + '_ShelterStripes', M['yellow'], None, coll=C)
        p = Part()       # flexible curtains hanging into the opening
        for sx in (-1, 1):
            p.box((b + sx * 1.32, -0.62, DZ + 1.55), (0.36, 0.02, 3.4))
        p.box((b, -0.62, DZ + 3.18), (2.4, 0.02, 0.5))
        p.make(tag + '_Curtains', M['shelter'], None, coll=C)
        # bumpers, wheel guides, leveller lip
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * 0.95, -0.1, DZ - 0.32), (0.26, 0.2, 0.5))
        p.make(tag + '_Bumpers', M['rubber'], None, bevel=0.02, coll=C)
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * 1.42, -2.2, 0.12), (0.14, 3.6, 0.24))
        p.make(tag + '_Guides', M['hazard'], None, bevel=0.01, coll=C)
        p = Part()
        p.box((b, -0.03, DZ - 0.02), (2.0, 0.08, 0.04))
        p.make(tag + '_Lip', M['steel'], None, bevel=0.005, coll=C)
        # wall lamp + signal light
        p = Part()
        p.box((b, -0.35, DZ + 4.35), (0.5, 0.25, 0.14))
        p.make(tag + '_Lamp', M['dark'], None, bevel=0.01, coll=C)
        p = Part()
        p.box((b, -0.36, DZ + 4.27), (0.4, 0.2, 0.01))
        p.make(tag + '_LampLens', M['lamp_ext'], None, coll=C)
        p = Part()
        p.box((b - 2.05, -0.14, DZ + 1.6), (0.18, 0.12, 0.42))
        p.make(tag + '_Signal', M['dark'], None, bevel=0.01, coll=C)
        p = Part()
        p.cyl((b - 2.05, -0.21, DZ + 1.7), (b - 2.05, -0.22, DZ + 1.7), 0.06, 12)
        p.make(tag + '_SignalLamp', M['lamp_green'] if b in OPEN else M['lamp_red'], None, coll=C)
        # sectional door: closed in the opening, or raised under the ceiling inside
        p = Part()
        if b in OPEN:
            p.box((b, 0.6, DZ + DOOR_H + 0.15), (DOOR_W + 0.1, 1.2, 0.06))
        else:
            p.box((b, 0.1, DZ + DOOR_H / 2), (DOOR_W, 0.06, DOOR_H))
        p.make(tag + '_Door', M['door'], None, bevel=0.01, coll=C)
        if b not in OPEN:
            p = Part()
            p.box((b, 0.06, DZ + 2.2), (2.4, 0.02, 0.32))
            p.make(tag + '_DoorWindows', M['glass'], None, coll=C)
        # bollards by the piers
        p = Part()
        for sx in (-1, 1):
            p.cyl((b + sx * 2.3, -0.6, 0.0), (b + sx * 2.3, -0.6, 1.1), 0.08, 14)
        p.make(tag + '_Bollards', M['yellow'], None, bevel=0.01, coll=C)


def _yard(M, C, rnd, veg):
    # fence (palisade) along the front of the yard and the gate side, gate gap y -15..-5 at x 23
    p = Part()
    for x in [-40 + i * 0.25 for i in range(int(62 / 0.25))]:
        p.box((x, -31.5, 1.1), (0.06, 0.03, 2.2))
    for z in (0.4, 1.8):
        p.box((-9, -31.5, z), (62, 0.05, 0.08))
    for y in [-31.5 + i * 0.25 for i in range(int(31.5 / 0.25))]:
        if -15.5 < y < -4.5:
            continue
        p.box((23.5, y, 1.1), (0.03, 0.06, 2.2))
    for z in (0.4, 1.8):
        p.box((23.5, -23.5, z), (0.05, 16, 0.08))
        p.box((23.5, -2.2, z), (0.05, 4.4, 0.08))
    p.make('PL_Fence', M['fence'], None, coll=C)
    # gatehouse + barrier (raised)
    p = Part()
    p.box((26.8, -18.0, 1.4), (3.0, 2.6, 2.8))
    p.make('PL_Gatehouse', panel_mat('PL_GatePanel', (0.82, 0.83, 0.83), seam=1.2), None, bevel=0.03, coll=C)
    p = Part()
    p.box((26.8, -16.68, 1.6), (2.2, 0.04, 1.0))
    p.box((25.28, -18.0, 1.6), (0.04, 1.8, 1.0))
    p.make('PL_GatehouseGlass', M['glass'], None, coll=C)
    p = Part()
    p.box((26.8, -18.0, 2.9), (3.6, 3.2, 0.16))
    p.make('PL_GatehouseRoof', M['galv'], None, bevel=0.02, coll=C)
    p = Part()
    p.box((24.6, -15.8, 0.55), (0.35, 0.35, 1.1))
    p.make('PL_BarrierPost', M['yellow'], None, bevel=0.02, coll=C)
    arm = Part()
    arm.box((0, 0, 0), (0.08, 0.08, 8.0))
    a = arm.make('PL_BarrierArm', hazard_mat('PL_BarrierStripe', (0.85, 0.85, 0.85), (0.55, 0.03, 0.02), 2.5), None, coll=C)
    a.location = (24.6, -15.8, 1.0)
    a.rotation_euler = (math.radians(-8), 0, 0)
    for o in (a,):
        o.data.transform(Matrix.Translation((0, 0, 4.0)))
    # road outside the gate
    p = Part()
    p.box((60, -10, 0.004), (72, 0.14, 0.01))
    p.make('PL_RoadLine', M['line_white'], None, coll=C)
    # lamp posts
    p = Part()
    q = Part()
    for x, y in ((-30, -29), (-15, -29), (0, -29), (15, -29), (21.5, -26), (21.5, -2)):
        p.cyl((x, y, 0), (x, y, 8.5), 0.09, 10, r2=0.06)
        p.cyl((x, y, 8.4), (x, y + 1.0, 8.5), 0.04, 6)
        p.box((x, y + 1.2, 8.45), (0.3, 0.6, 0.12))
        q.box((x, y + 1.2, 8.38), (0.24, 0.5, 0.01))
    p.make('PL_LampPosts', M['galv'], None, coll=C)
    q.make('PL_LampHeads', M['lamp_ext'], None, coll=C)
    # vegetation: trees + palms behind the fence, shrubs on the verges
    T = veg
    tm = T.tree_mesh()
    pm = T.palm_mesh()
    sm = T.shrub_mesh()
    for i in range(16):
        x = -38 + i * 4.2 + rnd.uniform(-1, 1)
        if rnd.random() < 0.45:
            T.place(pm, 'VEG_Palm', (x, -35.5 + rnd.uniform(-1.5, 1.5), 0), rnd.uniform(0.8, 1.15), coll=C, rnd=rnd)
        else:
            T.place(tm, 'VEG_Tree', (x, -36 + rnd.uniform(-1.5, 2), 0), rnd.uniform(0.85, 1.25), coll=C, rnd=rnd)
    for i in range(7):
        y = -30 + i * 4.5 + rnd.uniform(-1, 1)
        if abs(y + 10) < 6.5:
            continue
        T.place(pm, 'VEG_Palm', (27 + rnd.uniform(0, 3), y, 0), rnd.uniform(0.85, 1.2), coll=C, rnd=rnd)
    for i in range(20):
        T.place(sm, 'VEG_Shrub', (-38 + i * 3.2 + rnd.uniform(-0.8, 0.8), -33.4, 0), rnd.uniform(0.6, 1.1), coll=C, rnd=rnd)
    # neighbouring low industrial buildings far behind the trees
    p = Part()
    for x, w, h in ((-60, 30, 9), (-20, 26, 7), (15, 30, 10), (55, 22, 8)):
        p.box((x, -62, h / 2), (w, 14, h))
    p.make('PL_Neighbours', panel_mat('PL_NeighbourPanel', (0.70, 0.72, 0.72), seam=1.4), None, coll=C)
    for i in range(14):
        T.place(tm, 'VEG_TreeFar', (-70 + i * 11 + rnd.uniform(-3, 3), -50 + rnd.uniform(-4, 4), 0), rnd.uniform(1.1, 1.6),
                coll=C, rnd=rnd)
        T.place(pm, 'VEG_PalmFar', (-66 + i * 11 + rnd.uniform(-3, 3), -46 + rnd.uniform(-4, 4), 0), rnd.uniform(0.9, 1.3),
                coll=C, rnd=rnd)
    # west horizon: warehouses, a water tank, tree belts, power line along the road
    p = Part()
    for x, y, w, d, h in ((-75, -25, 34, 22, 10), (-78, 15, 30, 26, 12), (-120, -5, 40, 30, 9), (-60, 45, 26, 20, 8),
                          (95, 25, 36, 24, 11), (110, -40, 30, 20, 9)):
        p.box((x, y, h / 2), (w, d, h))
    p.make('PL_FarSheds', panel_mat('PL_FarPanel', (0.74, 0.76, 0.77), seam=1.6, axis='Y'), None, coll=C)
    p = Part()
    p.cyl((-95, 30, 0), (-95, 30, 14), 0.4, 8)
    p.cyl((-95, 30, 14), (-95, 30, 19), 3.0, 24)
    p.make('PL_WaterTank', panel_mat('PL_TankPanel', (0.7, 0.72, 0.72), seam=0.8), None, coll=C)
    for i in range(18):
        T.place(tm, 'VEG_TreeW', (-48 - rnd.uniform(0, 14), -45 + i * 5.5 + rnd.uniform(-2, 2), 0), rnd.uniform(1.1, 1.6),
                coll=C, rnd=rnd)
        if i % 2:
            T.place(pm, 'VEG_PalmW', (-52 - rnd.uniform(0, 12), -44 + i * 5.5, 0), rnd.uniform(0.9, 1.3), coll=C, rnd=rnd)
    p = Part()
    for x in range(30, 150, 30):
        p.cyl((x, -15.5, 0), (x, -15.5, 9.5), 0.14, 8, r2=0.1)
        p.box((x, -15.5, 9.2), (0.12, 1.8, 0.12))
    p.make('PL_PowerPoles', P.plain('PL_ConcretePole', (0.55, 0.54, 0.52), 0.8, bump=0.3), None, coll=C)
    p = Part()
    for yy in (-16.3, -14.7):
        for x0 in range(30, 120, 30):
            for k in range(12):
                t0, t1 = k / 12, (k + 1) / 12
                z0 = 9.25 - 0.6 * math.sin(math.pi * t0)
                z1 = 9.25 - 0.6 * math.sin(math.pi * t1)
                p.cyl((x0 + 30 * t0, yy, z0), (x0 + 30 * t1, yy, z1), 0.012, 4)
    p.make('PL_Wires', M['dark'], None, coll=C)
    for i in range(8):
        T.place(tm, 'VEG_TreeSide', (34 + rnd.uniform(0, 8), (-50 + i * 6 if i < 5 else 6 + i * 5) + rnd.uniform(-2, 2), 0), rnd.uniform(1.0, 1.4),
                coll=C, rnd=rnd)


def pallet(name, loc, M, C, rot=0.0, cartons=0, crates=None, rnd=None):
    root = bpy.data.objects.new(name, None)
    C.objects.link(root)
    root.location = loc
    root.rotation_euler = (0, 0, rot)
    p = Part()
    for y in (-0.5, 0, 0.5):
        p.box((0, y, 0.06), (1.2, 0.1, 0.1))
    for x in range(7):
        p.box((-0.54 + x * 0.18, 0, 0.125), (0.12, 1.0, 0.022))
    p.make(name + '_Wood', M['wood'], root, coll=C)
    if cartons:
        p = Part()
        for lv in range(cartons):
            for ix in range(3):
                for iy in range(2):
                    p.box((-0.4 + ix * 0.4, -0.25 + iy * 0.5, 0.29 + lv * 0.3), (0.39, 0.49, 0.29))
        p.make(name + '_Cartons', M['carton'], root, bevel=0.01, coll=C)
    return root


def exterior(rnd_seed=7):
    """Yard, building facade, bays, fence, gate, vegetation. Returns the collection."""
    import skveg
    M = MATS()
    C = coll('SET_PlantExterior')
    rnd = random.Random(rnd_seed)
    _ground(M, C)
    _building(M, C)
    _bays(M, C)
    _yard(M, C, rnd, skveg)
    pallet('PL_PalletA', (-20.0, -2.0, 0), M, C, 0.1, cartons=4)
    pallet('PL_PalletB', (-20.2, -3.4, 0), M, C, -0.05)
    pallet('PL_PalletC', (-21.6, -2.4, 0), M, C, 0.05)
    return C


def dock(crate_fn, trolley_fn):
    """Dock hall behind the front wall (y 0..12): epoxy floor, levellers, raised door sections and tracks, LED panels,
    strip curtain to the intake hall (behind the truck bay), trolleys and crate stacks."""
    M = MATS()
    C = coll('SET_Dock')
    p = Part()
    p.box(((X0 + X1) / 2, 30, DZ / 2), (X1 - X0, 60, DZ))
    p.make('PL_FloorSlab', M['epoxy'], None, coll=C)
    p = Part()
    p.box(((X0 + X1) / 2, 12.08, (DZ + HT) / 2), (X1 - X0, 0.16, HT - DZ))
    o = p.make('PL_DockBackWall', M['panel_in'], None, coll=C)
    # opening in the back wall for the intake (behind the truck bay): cut by a boolean
    cut = Part()
    cut.box((TRUCK_BAY - 1.0, 12.08, DZ + 1.6), (3.2, 0.6, 3.2))
    cobj = cut.make('PL_IntakeCut', M['dark'], None, coll=C)
    cobj.hide_render = True
    cobj.hide_viewport = True
    bo = o.modifiers.new('cut', 'BOOLEAN')
    bo.object = cobj
    bo.solver = 'EXACT'
    p = Part()
    p.box(((X0 + X1) / 2, 6, HT - 0.05), (X1 - X0, 12.2, 0.1))
    p.make('PL_DockCeiling', M['panel_in'], None, coll=C)
    p = Part()
    p.box((X0 + 0.1, 6, (DZ + HT) / 2), (0.16, 12.2, HT - DZ))
    p.box((X1 - 0.1, 6, (DZ + HT) / 2), (0.16, 12.2, HT - DZ))
    p.make('PL_DockEndWalls', M['panel_in'], None, coll=C)
    # strip curtain across the intake opening: individual swinging strips, built by the scene (skinterior)
    p = Part()
    p.box((TRUCK_BAY - 1.0, 11.95, DZ + 3.26), (3.4, 0.12, 0.12))
    for sx in (-1, 1):
        p.box((TRUCK_BAY - 1.0 + sx * 1.62, 11.95, DZ + 1.6), (0.08, 0.14, 3.2))
    p.make('PL_IntakeFrame', M['stainless'], None, bevel=0.005, coll=C)
    # levellers (diamond plate) with yellow/black edges, door tracks, raised door undersides
    for i, b in enumerate(BAYS):
        p = Part()
        p.box((b, 1.25, DZ + 0.005), (2.1, 2.5, 0.02))
        p.make('PL_Leveller%d' % i, P.tex_mat('PL_Diamond', 'metal_plate', scale=1.2, metal=1.0, rough_mul=0.9), None, coll=C)
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * 1.1, 1.25, DZ + 0.012), (0.1, 2.5, 0.01))
        p.make('PL_LevEdge%d' % i, M['hazard'], None, coll=C)
        p = Part()
        for sx in (-1, 1):
            p.box((b + sx * (DOOR_W / 2 + 0.08), 0.25, DZ + DOOR_H / 2 + 0.3), (0.06, 0.12, DOOR_H + 0.6))
            p.box((b + sx * (DOOR_W / 2 + 0.08), 0.9, DZ + DOOR_H + 0.25), (0.06, 1.4, 0.06))
        p.make('PL_Tracks%d' % i, M['galv'], None, coll=C)
        p = Part()
        p.box((b - 2.15, 0.25, DZ + 1.3), (0.22, 0.12, 0.3))
        p.make('PL_DoorCtrl%d' % i, P.plain('PL_CtrlBox', (0.62, 0.64, 0.66), 0.4, 0.2), None, bevel=0.01, coll=C)
    # LED panel rows + real area lights
    p = Part()
    for x in [X0 + 2 + i * 3.0 for i in range(15)]:
        for y in (2.5, 6.0, 9.5):
            p.box((x, y, HT - 0.12), (1.2, 0.3, 0.03))
    p.make('PL_DockLED', M['led'], None, coll=C)
    for k, (x, y) in enumerate([(x, y) for x in (-14, -6, 2, 10, 18) for y in (3.5, 8.5)]):
        ld = bpy.data.lights.new('PL_DockArea%d' % k, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = 5.0, 3.0
        ld.energy = 520
        ld.color = (0.93, 0.97, 1.0)
        lo = bpy.data.objects.new('PL_DockArea%d' % k, ld)
        C.objects.link(lo)
        lo.location = (x, y, HT - 0.3)
    # trolleys + crate stacks + hand-wash station + hose reel
    trolley_fn('PL_DockTrolley1', (TRUCK_BAY - 2.6, 3.2, DZ), math.radians(90), C)
    trolley_fn('PL_DockTrolley2', (CAM_BAY - 0.8, 6.8, DZ), math.radians(10), C)
    trolley_fn('PL_DockTrolley3', (TRUCK_BAY + 3.0, 7.5, DZ), math.radians(-80), C)
    k = 0
    for (x, y) in ((14.6, 10.8), (15.4, 10.8), (16.2, 10.8), (-1.0, 10.9), (-1.8, 10.9)):
        for lv in range(5):
            crate_fn('PL_StackCrate%02d' % k, ['blue', 'white', 'blue', 'red', 'blue'][(k + lv) % 5], (x, y, DZ + lv * 0.3), 0.0,
                     None, None, k)
            k += 1
    p = Part()
    p.box((-4.0, 11.6, DZ + 0.45), (1.6, 0.6, 0.9))
    p.box((-4.0, 11.85, DZ + 1.3), (1.6, 0.1, 0.8))
    p.make('PL_HandWash', M['stainless'], None, bevel=0.01, coll=C)
    p = Part()
    p.cyl((19.0, 11.9, DZ + 1.5), (19.0, 11.75, DZ + 1.5), 0.3, 24)
    p.make('PL_HoseReel', M['yellow'], None, coll=C)
    # stainless kick plates along the walls, floor drains, yellow walkway lines, extinguisher, aprons on hooks
    p = Part()
    p.box(((X0 + X1) / 2, 11.98, DZ + 0.2), (X1 - X0 - 0.4, 0.03, 0.4))
    for x in (X0 + 0.2, X1 - 0.2):
        p.box((x, 6, DZ + 0.2), (0.03, 11.8, 0.4))
    p.make('PL_KickPlates', M['stainless'], None, coll=C)
    p = Part()
    for x in (X0 + 3, X1 - 3):
        p.box((x, 6.0, DZ + 0.004), (0.25, 10.5, 0.01))
    p.box(((X0 + X1) / 2, 4.6, DZ + 0.004), (X1 - X0 - 6, 0.25, 0.01))
    p.make('PL_FloorDrains', P.tex_mat('PL_Grate', 'metal_plate', scale=4.0, metal=1.0, tint=(0.5, 0.5, 0.5)), None, coll=C)
    p = Part()
    for y in (5.6, 8.8):
        p.box(((X0 + X1) / 2, y, DZ + 0.003), (X1 - X0 - 2, 0.1, 0.006))
    p.make('PL_WalkLines', M['line_yellow'], None, coll=C)
    p = Part()
    p.cyl((-2.3, 11.85, DZ + 0.8), (-2.3, 11.85, DZ + 1.35), 0.09, 16)
    p.make('PL_Extinguisher', P.plain('PL_ExtRed', (0.45, 0.02, 0.02), 0.3, coat=0.6), None, bevel=0.01, coll=C)
    p = Part()
    for i in range(6):
        x = -6.2 + i * 0.32
        p.box((x, 11.9, DZ + 1.25), (0.28, 0.02, 0.85))
    p.make('PL_HangingAprons', P.plain('PL_ApronPVC', (0.82, 0.84, 0.85), 0.3, coat=0.3), None, bevel=0.01, coll=C)
    # pallets of empty crates and a hand pallet truck on the left of the camera bay
    k = 0
    for (x, y) in ((1.4, 7.6), (2.7, 7.6), (1.4, 9.0)):
        pallet('PL_DockPallet%d' % k, (x, y, DZ), M, C, 0.0)
        for lv in range(6):
            for ix in (-0.3, 0.3):
                crate_fn('PL_PalCrate%02d_%d' % (k, lv * 2 + (ix > 0)), ['blue', 'blue', 'white', 'red'][(k + lv) % 4],
                         (x + ix, y, DZ + 0.15 + lv * 0.3), math.pi / 2, None, None, k * 20 + lv)
        k += 1
    p = Part()
    p.box((0.2, 5.6, DZ + 0.09), (1.15, 0.16, 0.06))
    p.box((0.2, 6.2, DZ + 0.09), (1.15, 0.16, 0.06))
    p.box((-0.55, 5.9, DZ + 0.25), (0.3, 0.7, 0.4))
    p.cyl((-0.75, 5.9, DZ + 0.4), (-1.3, 5.9, DZ + 1.25), 0.02, 8)
    p.make('PL_PalletTruck', P.plain('PL_PTRed', (0.5, 0.06, 0.03), 0.4, 0.2), None, bevel=0.01, coll=C)
    return C


def intake_shell():
    """Enough of the intake hall behind the strip curtain to read as a bright white room through the strips."""
    M = MATS()
    C = coll('SET_IntakeShell')
    p = Part()
    p.box((TRUCK_BAY - 1.0, 18, HT - 0.05), (16, 12, 0.1))
    p.box((TRUCK_BAY - 9.0, 18, (DZ + HT) / 2), (0.16, 12, HT - DZ))
    p.box((TRUCK_BAY + 7.0, 18, (DZ + HT) / 2), (0.16, 12, HT - DZ))
    p.box((TRUCK_BAY - 1.0, 24.0, (DZ + HT) / 2), (16, 0.16, HT - DZ))
    p.make('PL_IntakeShell', M['panel_in'], None, coll=C)
    ld = bpy.data.lights.new('PL_IntakeArea', 'AREA')
    ld.size, ld.size_y = 8, 8
    ld.shape = 'RECTANGLE'
    ld.energy = 1500
    ld.color = (0.93, 0.97, 1.0)
    lo = bpy.data.objects.new('PL_IntakeArea', ld)
    C.objects.link(lo)
    lo.location = (TRUCK_BAY - 1.0, 18, HT - 0.4)
    return C
