"""p-docs (one shot, global 1100-1243 on the plant set): a loaded reefer parked nose-in off bay -4.6, rear doors
shut toward the sunlit yard; a dispatcher holds the export folder (blank sheets, no text) and snaps a plain bolt seal
through the lower lock-rod keeper; the camera opens wide and ends close on the seal, in daylight."""
import math
import bpy
from mathutils import Vector
import skhuman as H
import skplant as S
import sktruck as T
from sktruck import Part
import skpbr as P

D = math.radians
WIN = (1100, 1243)
BX = -4.6                                   # bay
OY = -9.0                                   # truck origin y: nose toward the building, rear to the sunlit yard


def _empty(name, loc, parent, C):
    e = bpy.data.objects.new(name, None)
    C.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def build(C):
    R = T.reefer_truck('TRK_Sealed', coll=C, load=False, seed=7)
    R['root'].location = (BX, OY, 0.0)
    R['root'].rotation_euler = (0, 0, D(90))
    bpy.context.view_layer.update()
    # the right-hand door's inner lock rod, lower keeper: world position of the seal
    dr = R['door_r']
    keeper = dr.matrix_world @ Vector((-0.13, (T.BW / 2 - 0.05) * 0.78, -T.BH / 2 + 0.36))   # through the hasp, proud of the rod
    # bolt seal: steel pin + plain yellow barrel lock (no print)
    pin = Part()
    pin.cyl((0, 0, -0.05), (0, 0, 0.07), 0.005, 10)
    pin.cyl((0, 0, 0.07), (0, 0, 0.082), 0.011, 14)
    po = pin.make('DOC_SealPin', P.plain('DOC_SealSteel', (0.6, 0.62, 0.64), 0.3, 0.9), None, smooth=True, coll=C)
    bar = Part()
    bar.cyl((0, 0, -0.105), (0, 0, -0.05), 0.016, 16)
    bo = bar.make('DOC_SealBarrel', P.plain('DOC_SealYellow', (0.85, 0.62, 0.05), 0.4, coat=0.3), None, smooth=True,
                  coll=C)
    po.location = keeper
    below = keeper + Vector((0.05, -0.3, -0.35))
    for f, loc in ((1, below), (1118, below), (1140, keeper + Vector((0, -0.04, -0.08))), (1156, keeper)):
        bo.location = loc
        bo.keyframe_insert('location', frame=f)
    # dispatcher: right hand brings the barrel up and pushes it home; left hand holds the folder at the hip
    w = H.person('HUM_Dispatch', 'driver', 'male', coll=C, seed=611)
    w.location = (keeper.x - 0.22, keeper.y - 0.55, 0.0)      # yard side of the rear doors, facing +Y
    w.rotation_euler = (0, 0, D(180))
    hr = _empty('HUM_Dispatch_HandR', (0, 0, -0.03), bo, C)
    c = w.pose.bones['forearm.R'].constraints.new('IK')
    c.target = hr
    c.chain_count = 2
    c.use_tail = True
    for f, v in ((1, 1.0), (1162, 1.0), (1172, 0.0)):
        c.influence = v
        c.keyframe_insert('influence', frame=f)
    H.grip(w, 'R', curl=0.8)
    H.grip(w, 'L', curl=0.6)
    H.set_pose(w, {'spine': (6, 0, 0), 'head': (14, 0, 0), 'upperarm.L': (16, -22, 0), 'forearm.L': (70, 0, 0)}, 1)
    H.set_pose(w, {'spine': (6, 0, 0), 'head': (16, 0, 0), 'upperarm.L': (16, -22, 0), 'forearm.L': (70, 0, 0)}, 1156)
    H.set_pose(w, {'spine': (4, 0, 0), 'head': (4, 0, 0), 'upperarm.L': (18, -22, 0), 'forearm.L': (72, 0, 0),
                   'upperarm.R': (6, -24, 0), 'forearm.R': (18, 0, 0)}, 1190)
    # export folder in the left hand: card cover + blank sheets (lines only)
    hand_l = w.pose.bones['hand.L']
    fo = Part()
    fo.box((0, 0, 0), (0.24, 0.016, 0.32))
    folder = fo.make('DOC_Folder', P.plain('DOC_FolderBlue', (0.08, 0.16, 0.32), 0.6), None, bevel=0.003, coll=C)
    sh = Part()
    sh.box((0.004, 0.0, 0.01), (0.22, 0.02, 0.29))
    sheets = sh.make('DOC_Sheets', P.plain('DOC_Paper', (0.88, 0.88, 0.85), 0.7), folder, coll=C)
    folder.parent = w
    folder.parent_type = 'BONE'
    folder.parent_bone = 'hand.L'
    folder.location = (0.0, 0.05, 0.0)
    folder.rotation_euler = (D(90), 0, D(10))
    # camera: close on the seal, easing back to the sealed doors + the folder
    cam = bpy.data.objects.new('CAM_Docs', bpy.data.cameras.new('CAM_Docs'))
    C.objects.link(cam)
    cam.data.lens = 45
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 2.8
    tgt = _empty('CAM_Docs_Target', keeper, None, C)
    tc = cam.constraints.new('TRACK_TO')
    tc.target = tgt
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    cam.data.dof.focus_object = tgt
    for f, loc, t in ((1100, Vector((BX + 2.6, keeper.y - 3.6, 1.9)), Vector((BX, keeper.y, 1.5))),
                      (1150, Vector((BX + 1.7, keeper.y - 2.2, 1.7)), keeper + Vector((-0.2, 0, 0.05))),
                      (1243, keeper + Vector((0.42, -0.62, 0.1)), keeper + Vector((0, 0, -0.03))),
                      (1260, keeper + Vector((0.41, -0.6, 0.1)), keeper + Vector((0, 0, -0.03)))):
        cam.location = loc
        cam.keyframe_insert('location', frame=f)
        tgt.location = t
        tgt.keyframe_insert('location', frame=f)
    for o in (cam, tgt):
        for fc in T._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
            fc.update()
    return cam
