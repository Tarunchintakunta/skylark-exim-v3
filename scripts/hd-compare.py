"""Before/after frames for the HD re-encode (#hd2): one frame per clip at 100 %, the shipped file before against the new one.

  python3 scripts/hd-compare.py <before dir> <after dir> <out dir> <crop dir> id...

For each id: the middle frame of <id>_2560.av1.mp4 (else _1920, the old top where 2560 was not served) from both
dirs. Writes <out>/<id>.jpg (before | after, full frames, q 92) and <crop>/<id>.jpg (the 640×400 region with the most
detail, before | after, at 100 %), and prints luma sharpness (mean |Laplacian|) and 8×8 block-edge ratio for both.
"""
import subprocess
import sys

import numpy as np
from PIL import Image

before, after, out, crops = sys.argv[1:5]


def frame(path):
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', path],
                           capture_output=True, text=True, check=True).stdout)
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{n // 2})', '-frames:v', '1', '-pix_fmt', 'rgb24',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path],
                                   capture_output=True, text=True, check=True).stdout.strip().split(','))
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def pick(id, d):
    import os
    for t in (2560, 1920):
        f = f'{d}/{id}_{t}.av1.mp4'
        if os.path.exists(f):
            return f, t
    raise FileNotFoundError(id)


def luma(a):
    return a.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)


def sharp(y):
    return float(np.abs(4 * y[1:-1, 1:-1] - y[:-2, 1:-1] - y[2:, 1:-1] - y[1:-1, :-2] - y[1:-1, 2:]).mean())


def blocky(y):
    # mean column step on 8-px block boundaries against the mean step elsewhere (1.0: no block edges)
    d = np.abs(np.diff(y, axis=1))
    on = d[:, 7::8].mean()
    return float(on / d.mean())


for id in sys.argv[5:]:
    (fb, tb), (fa, ta) = pick(id, before), pick(id, after)
    b, a = frame(fb), frame(fa)
    if b.shape != a.shape:  # the old top was 1920: compare at the new size, the old frame scaled as a browser would
        b = np.asarray(Image.fromarray(b).resize((a.shape[1], a.shape[0]), Image.LANCZOS))
    yb, ya = luma(b), luma(a)
    # the most detailed 640×400 region of the new frame, on a 64-px grid
    g = np.abs(np.diff(ya, axis=1))[:-1, :] + np.abs(np.diff(ya, axis=0))[:, :-1]
    best, at = -1, (0, 0)
    for y in range(0, ya.shape[0] - 400, 64):
        for x in range(0, ya.shape[1] - 640, 64):
            e = g[y:y + 400, x:x + 640].mean()
            if e > best:
                best, at = e, (y, x)
    y, x = at
    Image.fromarray(np.hstack([b, a])).save(f'{out}/{id}.jpg', quality=92)
    Image.fromarray(np.hstack([b[y:y + 400, x:x + 640], np.full((400, 8, 3), 255, np.uint8), a[y:y + 400, x:x + 640]])).save(f'{crops}/{id}.jpg', quality=90)
    print(f'{id:18s} before {tb} sharp {sharp(yb):5.2f} block {blocky(yb):4.2f} | after {ta} sharp {sharp(ya):5.2f} block {blocky(ya):4.2f} | crop x{x} y{y}')
