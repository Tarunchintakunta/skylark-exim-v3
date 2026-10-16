import os
import sys

import bpy
s = bpy.context.scene; r = s.render
r.resolution_x, r.resolution_y, r.resolution_percentage = 3840, 2160, int(os.environ.get('STILL_PCT', 100))
r.use_motion_blur = False      # a composition still: no streaks from the camera move
s.eevee.taa_render_samples = int(os.environ.get('STILL_SAMPLES', 128))
for a, v in (('use_raytracing', True), ('use_shadows', True), ('use_gtao', True)):
    if hasattr(s.eevee, a): setattr(s.eevee, a, v)
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'; r.image_settings.compression = 15
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import still_fixes
still_fixes.apply()
import still_cams
still_cams.apply(os.environ.get('STILL_ID', ''))
still_cams.look(os.environ.get('STILL_ID', ''))
