"""Contact sheet + rule checklist for the composition stills (#255-#260, #246).
  python3 scripts/stills_sheet.py <stillsdir> <outdir>
Reads <id>.png and <id>.rules.json, writes <outdir>/contact-sheet.jpg, <id>.jpg (3840x2160, q92) and CHECKLIST.md."""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
SHOTS = [('255', '#255 Truck doors open on the dock leveller, outside'), ('255b', '#255 Truck from the front, driver on the right'), ('256', '#256 Intake, steel crates'), ('257', '#257 Cold storage, steel racks'),
         ('258', '#258 Quay crane lifting a container from the ship'), ('258a', '#258 sequence 1: spreader lowers onto the deck'), ('258b', '#258 sequence 2: second crane grips and lifts'), ('258c', '#258 sequence 3: container set down'), ('259', '#259 Ship alone at sea'), ('260', '#260 Dawn hero'), ('246', '#246 Beat 3 unload, truck outside (shrimp)'), ('246f', '#246 Beat 3 unload, truck outside (fish)')]
TW, TH, PAD, HEAD = 1280, 720, 24, 70
COLS = 2
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 30)
small = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
RULES = ['RHD: driver and wheel on the right', 'truck outside the plant', 'steel / iron only (crates, racks, trolleys)', 'no logos or text', 'ship alone in the water']
rows = (len(SHOTS) + COLS - 1) // COLS
CHK = 5 * 30 + 20
W = COLS * (TW + PAD) + PAD
H = rows * (TH + HEAD + CHK + PAD) + PAD
sheet = Image.new('RGB', (W, H), (14, 22, 26))
d = ImageDraw.Draw(sheet)
md = ['# Composition stills, 3840x2160\n', 'Each rule is evaluated by `blender/still_rules.py` on the still\'s own frame. PASS / FAIL / n/a (rule does not apply to that scene).\n',
      '| Still | ' + ' | '.join(RULES) + ' |', '|---|' + '---|' * len(RULES)]
for i, (sid, title) in enumerate(SHOTS):
    im = Image.open(os.path.join(src, sid + '.png')).convert('RGB')
    assert im.size == (3840, 2160), im.size
    im.save(os.path.join(out, sid + '.jpg'), quality=92, optimize=True)
    r = json.load(open(os.path.join(src, sid + '.rules.json')))
    x = PAD + (i % COLS) * (TW + PAD)
    y = PAD + (i // COLS) * (TH + HEAD + CHK + PAD)
    d.text((x, y), title, font=font, fill=(246, 242, 234))
    sheet.paste(im.resize((TW, TH), Image.LANCZOS), (x, y + HEAD - 20))
    cy = y + HEAD - 20 + TH + 10
    for k, name in enumerate(RULES):
        st = r[name]['status']
        col = {'PASS': (110, 200, 130), 'FAIL': (230, 90, 80), 'n/a': (140, 150, 155)}[st]
        d.text((x, cy + k * 30), '%s  %s' % ({'PASS': '[x]', 'FAIL': '[!]', 'n/a': '[-]'}[st], name), font=small, fill=col)
    md.append('| %s | ' % title + ' | '.join('%s: %s' % (r[n]['status'], r[n]['detail']) for n in RULES) + ' |')
sheet.save(os.path.join(out, 'contact-sheet.jpg'), quality=88)
open(os.path.join(out, 'CHECKLIST.md'), 'w').write('\n'.join(md) + '\n')
print('ok', sheet.size)
