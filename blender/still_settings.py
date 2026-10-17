import os
import sys

import bpy
s = bpy.context.scene; r = s.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 3840, 2160, int(os.environ.get('STILL_PCT', 100))
r.use_motion_blur = False      # a composition still: no streaks from the camera move
s.eevee.taa_render_samples = int(os.environ.get('STILL_SAMPLES', 128))
for a, v in (('use_raytracing', True), ('use_shadows', True), ('use_gtao', True)):
    if hasattr(s.eevee, a): setattr(s.eevee, a, v)
if os.environ.get('STILL_ENGINE', '').lower() == 'cycles':     # release stills: Cycles on the Metal GPU, OIDN, filmic
    r.engine = 'CYCLES'
    s.cycles.device = 'GPU'
    pr = bpy.context.preferences.addons['cycles'].preferences
    pr.compute_device_type = 'METAL'
    pr.get_devices()
    for d in pr.devices:
        d.use = True
    s.cycles.samples = int(os.environ.get('STILL_SAMPLES', 64))
    s.cycles.use_denoising, s.cycles.denoiser = True, 'OPENIMAGEDENOISE'
    s.cycles.use_adaptive_sampling = True
    vs = s.view_settings
    try:
        vs.view_transform = 'Filmic'
        vs.look = 'Filmic - Medium High Contrast'
    except TypeError:
        vs.view_transform = 'AgX'
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'; r.image_settings.compression = 15
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import still_fixes
still_fixes.apply_all(os.environ.get('STILL_ID', ''))
import still_cams
still_cams.apply(os.environ.get('STILL_ID', ''))
still_cams.look(os.environ.get('STILL_ID', ''))
