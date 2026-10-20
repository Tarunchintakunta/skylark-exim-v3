"""Grade the boxes on the racks of Blender still #257 (cold store) from white to brushed, galvanised steel: cool grey,
streaked along the box faces, a soft sheen per shelf, darker edges. Workers, the floor, lights and the wall are left as
they are; framing is untouched. Regions are hand-placed for #257 (1280x720 coordinates, scaled to the still).
  python3 scripts/steel-grade.py <257.jpg> <out.jpg>
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
src, out = sys.argv[1], sys.argv[2]
img = Image.open(src).convert('RGB'); W, H = img.size
a = np.asarray(img).astype(np.float32)
L = a.mean(2); sat = a.max(2) - a.min(2)
# regions in 1280x720 coordinates, scaled up: the two racks and the stack on the pallet jack
sx = W / 1280
def poly(pts): 
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(x * sx, y * sx) for x, y in pts], fill=255); return np.asarray(m) > 0
racks = poly([(0, 0), (470, 0), (470, 470), (175, 600), (0, 640)]) | poly([(890, 0), (1280, 0), (1280, 560), (890, 440)]) | poly([(552, 372), (648, 372), (648, 505), (552, 505)]) | poly([(360, 360), (436, 360), (436, 470), (360, 470)])
people = poly([(5, 100), (150, 100), (165, 200), (152, 240), (200, 400), (235, 550), (290, 545), (290, 720), (0, 720), (0, 270)]) | poly([(0, 0), (1280, 0), (1280, 12), (0, 12)]) | poly([(436, 255), (562, 255), (562, 650), (436, 650)]) | poly([(645, 280), (720, 280), (720, 560), (645, 560)]) | poly([(596, 382), (646, 382), (646, 410), (596, 410)]) | poly([(812, 290), (900, 290), (900, 510), (812, 510)])
box = racks & ~people & (L > 130) & (sat < 30)
# drop specks: keep areas that survive an open, then feather
m = Image.fromarray((box * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5 * sx))
m = np.asarray(m).astype(np.float32)[..., None] / 255
# steel: cool grey, brushed (streaks along the box face), sheen, darker edges
rng = np.random.default_rng(7)
n = rng.normal(0, 1, (H, W)).astype(np.float32)
brush = np.asarray(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)).resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BICUBIC)).astype(np.float32) - 128
grey = 0.62 * L + 8 + brush * 0.45
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
sheen = 22 * np.exp(-((yy * 6) % 1 - 0.35) ** 2 / 0.02)  # a soft highlight band per shelf
grey = grey + sheen
edges = np.asarray(Image.fromarray(L.clip(0, 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
grey = grey - edges * 2.2
steel = np.stack([grey - 5, grey + 1, grey + 9], 2)
res = a * (1 - m) + steel * m
Image.fromarray(res.clip(0, 255).astype(np.uint8)).save(out, quality=95)
