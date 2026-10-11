"""Stitch the review_humans.py tiles into one labelled sheet (2 columns of 960x540 tiles), JPEG.
  python3 blender/review_sheet.py <tile_dir> <out.jpg>"""
import os
import sys
from PIL import Image, ImageDraw

TILES = [('t1_plant', 'Plant worker: cap + mask'), ('t2_fisher', 'Fisherman: oilskin, no cap'),
         ('t3_port', 'Port: hi-vis + hard hat'), ('t4_driver', 'Driver'),
         ('t5_crate', 'Nitrile glove: crate handles (contact grip)'), ('t6_net', 'Rubber glove: net-bag rim'),
         ('t8', 'Box edge | thin rod'), ('t7_mid', 'Mid distance: stand / crouch / kneel'),
         ('t9_fplant', 'Plant worker (woman): cap + mask'), ('t10_fbun', 'Woman, no cap: low bun')]
src, out = sys.argv[1], sys.argv[2]
W, H = 960, 540
sheet = Image.new('RGB', (W * 2, H * ((len(TILES) + 1) // 2)), (20, 20, 20))
for i, (name, label) in enumerate(TILES):
    if name == 't8':
        im = Image.new('RGB', (W, H))
        for j, n in enumerate(('t8a_box', 't8b_rod')):
            p = os.path.join(src, n + '.png')
            if os.path.exists(p):
                im.paste(Image.open(p).convert('RGB').resize((W // 2, H)), (j * W // 2, 0))
    else:
        p = os.path.join(src, name + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB').resize((W, H))
    d = ImageDraw.Draw(im)
    d.rectangle((0, H - 30, W, H), fill=(0, 0, 0))
    d.text((10, H - 22), label, fill=(235, 235, 235))
    sheet.paste(im, ((i % 2) * W, (i // 2) * H))
sheet.save(out, quality=88)
print('sheet', out)
