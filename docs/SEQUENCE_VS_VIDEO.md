# Image sequence or video, per chapter (#264 step 3)

Terminal Industries draws its whole scroll on one `<canvas>`: 410 WebP frames of about 59 KB, loaded out of order so a
coarse version plays early. The brief asked for the same treatment on `/story`, keeping video "only where a benchmark
shows it is smoother or much lighter, decided per chapter by measurement". This is that measurement.

## How it was measured

`scripts/seq-bench.sh` extracts frames from each clip's own master (`masters/<id>/master.mp4`, 2560×1440, 24 fps, ~3 s),
encodes every frame as AVIF (SVT-AV1 `-crf 25`, which lands near libavif q 60) and as WebP `q 78`, and prints the
sequence's total bytes beside the clip's own AV1 file at the same tier. The clips are the ones the budget solver already
caps (`scripts/clip-manifest.ts`), so this compares what a visitor actually downloads either way.

```
scripts/seq-bench.sh seq-1920-12.tsv 12 1920          # every master, 12 fps, the 1920 tier
IDS="hf-catch hf-store hf-sail" scripts/seq-bench.sh matrix.tsv 24 810 1920 2560
```

## What it costs: one clip, three tiers, two frame rates

AVIF `crf 25` ≈ q 60, WebP q 78. `crf 33` is included to show what dropping below the brief's quality floor buys.
A busy shot (`hf-catch`: net, spray, fish), a calm interior (`hf-store`), and a smooth aerial (`hf-sail`).

| Clip | Tier | AVIF q60 24 fps | AVIF q60 12 fps | AVIF crf33 12 fps | WebP q78 24 fps | The clip as AV1 video |
| --- | --- | --- | --- | --- | --- | --- |
| hf-catch | 810×1440 phone | 11.51 MB | 5.76 MB | 3.91 MB | 10.84 MB | **0.46 MB** |
| hf-catch | 1920 | 23.74 MB | 11.87 MB | 8.37 MB | 19.74 MB | **0.98 MB** |
| hf-catch | 2560 | 33.45 MB | 16.72 MB | 11.82 MB | 28.84 MB | **1.90 MB** |
| hf-store | 810×1440 phone | 4.51 MB | 2.26 MB | 1.41 MB | 4.46 MB | **0.38 MB** |
| hf-store | 1920 | 11.71 MB | 5.85 MB | 3.79 MB | 9.46 MB | **0.81 MB** |
| hf-store | 2560 | 16.34 MB | 8.17 MB | 5.28 MB | 13.61 MB | **1.60 MB** |
| hf-sail | 810×1440 phone | 4.40 MB | 2.20 MB | 1.46 MB | 3.86 MB | **0.44 MB** |
| hf-sail | 1920 | 4.81 MB | 2.41 MB | 1.53 MB | 3.82 MB | **0.90 MB** |
| hf-sail | 2560 | 7.29 MB | 3.65 MB | 2.38 MB | 6.07 MB | **1.75 MB** |

An image sequence carries no motion compensation: every frame is a fresh still. Against AV1 with a 6-frame GOP that is
5× the bytes on the kindest shot in the film and 24× on the busiest, and the brief's own quality floor (AVIF q ≥ 60 /
WebP q ≥ 70) is what makes it so.

## Per clip, at the most favourable honest setting

12 fps at the 1920 tier, AVIF q 60 — half the master's frame rate, the tier most desktops are served.

<!-- seq-bench:1920:12 -->

## The decision

- **`/story` chapters stay video.** The active path is 17 clips (wild catch) or 19 (farmed shrimp). At 12 fps and 1920
  the sequences come to SEQ_OCEAN and SEQ_POND against 15.45 MB and 14.96 MB as AV1. The desktop budget for a whole
  path is 25 MB at 1920 and 40 MB at 2560: no frame rate inside the quality floor fits, and thinning the density far
  enough to fit (about 3 fps) would be visibly worse than the video it replaced, not better.
- **The homepage hero is a canvas sequence** (#249, kept and rebuilt on this engine). It is one 6-second shot scrubbed
  over 300 vh, where a `<video>` has to seek on every frame; the sequence draws a decoded bitmap instead, and at 60
  frames it fits the homepage's 8 MB budget. This is the one place where the sequence is both affordable and smoother.
- **The engine is still the right thing to own.** `src/film/sequence.ts` is what makes the hero smooth and what any
  future shot-as-sequence would use: a worker that fetches each frame once and decodes on demand, a capped bitmap LRU,
  coarse-first loading, and drawing on the page's single rAF.
- **What Terminal's loading pattern gives `/story` instead** is in the rest of this issue: no blocking loader, the whole
  active path fetched coarse-first in the background after the first screen, and a scroll that touches the network not
  at all (`tests/terminal-mode.spec.ts`).

Terminal can afford 410 frames because its scroll is one continuous camera move at 59 KB a frame. This film is twenty
separate photoreal shots; the same technique on it costs an order of magnitude more bytes for a worse picture.
