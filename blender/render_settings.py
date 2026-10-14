"""Apply the standard Skylark render settings to the open .blend (RENDER_PIPELINE.md section 1).
Run through the Blender MCP (paste into execute code) or headless:
  Blender -b assets-src/blender/<name>.blend --python blender/render_settings.py -- <name> <first> <last> [interior|exterior|sea]
Then the script saves the .blend. Frame ranges come from scripts/scenes.sh.
"""
import os
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = argv[0] if argv else os.path.splitext(os.path.basename(bpy.data.filepath))[0]
first = int(argv[1]) if len(argv) > 1 else bpy.context.scene.frame_start
last = int(argv[2]) if len(argv) > 2 else bpy.context.scene.frame_end
kind = argv[3] if len(argv) > 3 else "exterior"

s = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
s.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"

r = s.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
r.fps, r.fps_base = 24, 1.0
s.frame_start, s.frame_end = first, last
r.use_motion_blur = True
if hasattr(r, "motion_blur_shutter"):
    r.motion_blur_shutter = 0.5
r.film_transparent = False
r.use_overwrite = False
r.use_placeholder = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.image_settings.color_depth = "8"
r.image_settings.compression = 15
render_dir = "port" if name == "port" else name
r.filepath = "//../render/%s/" % render_dir

e = s.eevee
e.taa_render_samples = 64
for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_gtao", True),
                  ("use_bloom", False), ("use_volumetric_shadows", False)):
    if hasattr(e, attr):
        setattr(e, attr, val)
rto = getattr(e, "ray_tracing_options", None)
if rto is not None and hasattr(rto, "resolution_scale"):
    rto.resolution_scale = "2"  # half resolution: big speed win, little visible loss after 1280w encode
if hasattr(e, "shadow_ray_count"):
    e.shadow_ray_count = 1
if hasattr(e, "shadow_step_count"):
    e.shadow_step_count = 6

vs = s.view_settings
vs.view_transform = "AgX"
looks = [l.identifier for l in vs.bl_rna.properties["look"].enum_items]
want = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in looks else "None"
vs.look = want if kind != "sea" else "None"
vs.exposure = 0.0
vs.gamma = 1.0
s.display_settings.display_device = "sRGB"

# All external images packed so the headless render finds them (blend files are git-ignored, size is fine)
try:
    bpy.ops.file.pack_all()
except Exception as exc:  # nothing to pack is fine
    print("pack_all:", exc)

bpy.ops.wm.save_mainfile()
print("render settings applied:", name, s.render.engine, first, last, kind, "->", r.filepath)
