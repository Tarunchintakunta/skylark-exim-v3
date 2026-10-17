"""Render review stills of the open .blend at the given frames.
  Blender -b <file.blend> --python blender/stills.py -- <out_prefix> <pct> <samples> <frame> [frame ...]
writes <out_prefix>-fNNN.png (e.g. docs/renders/o-catch-f040.png) and prints seconds per frame."""
import sys
import time
import bpy

a = sys.argv[sys.argv.index('--') + 1:]
prefix, pct, samples, frames = a[0], int(a[1]), int(a[2]), [int(x) for x in a[3:]]
s = bpy.context.scene
s.render.resolution_percentage = pct
s.eevee.taa_render_samples = samples
for f in frames:
    s.frame_set(f)
    s.render.filepath = '%s-f%03d.png' % (prefix, f)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print('STILL f%03d %.1fs' % (f, time.time() - t))
