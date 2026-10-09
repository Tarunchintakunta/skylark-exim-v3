"""Shared boundary frames between two different .blend files (SCENES.md 'Boundaries').
Scene A (e.g. truck-reverse) writes its camera + named hero objects at its LAST frame; scene B (p-intake) reads
them at its FIRST frame and keys them, so both renders produce the same image. Then run scripts/boundary-check.sh.

Usage inside Blender (MCP execute code), with the repo root as REPO:
  exec(open(REPO + '/blender/boundary_camera.py').read())
  write_boundary('truck-reverse', 'p-intake', frame=288, objects=['TRK_Reefer', 'TRK_DoorL', 'TRK_DoorR'])   # in A
  read_boundary('truck-reverse', 'p-intake', frame=1)                                                       # in B
Objects must have the same names in both files (they come from the linked asset library, see ASSET_LIBRARY.md).
Lighting, world and set collections must be the same linked collections in both files.
"""
import json
import os
import bpy

def _path(a, b):
    root = bpy.path.abspath("//")
    d = os.path.join(root, "boundaries")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s__%s.json" % (a, b))

def _state(ob):
    return {"matrix_world": [list(r) for r in ob.matrix_world]}

def write_boundary(a, b, frame, objects=()):
    s = bpy.context.scene
    s.frame_set(frame)
    cam = s.camera
    data = {"frame": frame, "camera": _state(cam),
            "lens": cam.data.lens, "sensor_width": cam.data.sensor_width,
            "dof": [cam.data.dof.use_dof, cam.data.dof.focus_distance, cam.data.dof.aperture_fstop],
            "objects": {n: _state(bpy.data.objects[n]) for n in objects},
            "sun": [list(r) for r in bpy.data.objects["Sun"].matrix_world] if "Sun" in bpy.data.objects else None}
    with open(_path(a, b), "w") as f:
        json.dump(data, f, indent=1)
    print("boundary written", _path(a, b))

def _apply(ob, st, frame):
    from mathutils import Matrix
    ob.matrix_world = Matrix(st["matrix_world"])
    ob.keyframe_insert("location", frame=frame)
    rot = "rotation_quaternion" if ob.rotation_mode == "QUATERNION" else "rotation_euler"
    ob.keyframe_insert(rot, frame=frame)
    ob.keyframe_insert("scale", frame=frame)

def read_boundary(a, b, frame=1):
    with open(_path(a, b)) as f:
        data = json.load(f)
    s = bpy.context.scene
    cam = s.camera
    _apply(cam, data["camera"], frame)
    cam.data.lens = data["lens"]
    cam.data.sensor_width = data["sensor_width"]
    cam.data.dof.use_dof, cam.data.dof.focus_distance, cam.data.dof.aperture_fstop = data["dof"]
    for n, st in data["objects"].items():
        if n in bpy.data.objects:
            _apply(bpy.data.objects[n], st, frame)
        else:
            print("WARNING missing object for boundary:", n)
    print("boundary applied at frame", frame, "from", _path(a, b))
