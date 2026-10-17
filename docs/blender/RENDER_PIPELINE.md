# RENDER_PIPELINE.md: render, encode, budgets

## 1. Render settings (saved in every scene .blend)
Apply with `blender/render_settings.py` (via the MCP, or `Blender -b <file> --python blender/render_settings.py -- <name> <first> <last> [interior|exterior|sea]`). It sets:
- Engine **EEVEE** (`BLENDER_EEVEE_NEXT` on 4.2–4.5, `BLENDER_EEVEE` on 5.x; the script picks whichever exists).
- **1920×1080**, 100%, **24 fps**, frame range from `scripts/scenes.sh`.
- Samples **64**; ray tracing on at half resolution; shadows on; AO on; **no bloom/glare**.
- **Motion blur on**, shutter 0.5.
- Colour management **AgX** (Look Medium High Contrast for exteriors/interiors, None for the open sea), exposure tuned per scene so skies, water and walls stay bright.
- Output PNG RGB 8-bit, compression 15, `//../render/<dir>/####.png` (= `assets-src/render/<dir>/`), overwrite off (so a stopped render resumes).
- Packs all external images into the .blend so headless renders find every texture.
Per scene, set by hand: depth of field (camera, f/2.8–8, focus on the action; off for top-down sea), sun + HDRI rotation, subtle atmospheric perspective for distance (light world volume or a depth-based mix; never fog, never grey).

**Bake before saving:** every simulation (rigid-body fish, cloth net, particles, dynamic paint) must be baked and its cache saved next to the .blend (`bpy.ops.ptcache.bake_all(bake=True)`), or the headless render will re-simulate or skip it.

## 2. Preview → approval → full render (per scene)
```bash
scripts/render-scene.sh <blend> preview      # 960x540, 16 samples, no motion blur -> docs/renders/<blend>-preview.mp4 (<= 4 MB)
# post in the scene PR: the preview mp4 + 3-5 stills (docs/renders/<blend>-fNNN.png) + the ticked acceptance list
# WAIT for Tarun's ok in the PR. Fix notes -> re-run preview.
scripts/render-scene.sh <blend> full         # saved settings, 1920x1080 -> assets-src/render/<dir>/
FORCE=1 scripts/render-scene.sh <blend> full # after a change, re-render every frame
scripts/render-scene.sh <blend> full 1 96    # a chunk (resume/overnight splitting)
```
`<blend>` is one of: `o-catch` `o-return` `p-ponds` `p-harvest` `truck-reverse` `p-intake` `p-proc` `p-freeze` `port` (and `prod-tuna` `prod-swordfish` `prod-shrimp` only for the Products fallback). Renders always run in Claude Code's **terminal**, never inside one MCP call (MCP calls time out). `render-scene.sh` wraps Blender in `caffeinate -i` so the Mac doesn't sleep. If headless EEVEE fails on this Mac, render from the open Blender via MCP in chunks of ≤ 24 frames per call.

Stand-in rule: once a preview exists, encode it (`ffmpeg … docs/renders/<blend>-preview.mp4` → split per clip with the `scenes.sh` frame ranges, `-start_number` and `-frames:v`) as the chapter's temporary clip, so the site never shows an empty scene. No "placeholder" text on the page, ever.

## 3. Frames → masters → site media
```bash
scripts/frames-to-master.sh <id> [id ...]    # PNGs -> assets-src/video/<id>.mp4 (crf 14, 1080p), refuses if frames are missing
scripts/boundary-check.sh                    # every shared join: last frame of A == first frame of B (SSIM >= 0.99)
scripts/encode-clips.sh <id> ...             # -> public/media/<id>_1280.mp4 + _720.mp4 (GOP 6, no B-frames, faststart)
scripts/make-posters.sh <id> ...             # -> <id>_1280.webp, <id>_720.webp, <id>_end_1280.webp
scripts/check-clip.sh <id> ...               # length, GOP, brightness floor, size target/cap
scripts/path-weight.sh                       # full-scroll MB per path, desktop + mobile
```
Two-clip blends: `o-catch` → `o-catch-a` (1–192) + `o-catch-b` (192–383); `port` → `x-cranes` (1–288) + `x-ship` (288–479). Every other blend = one clip.

## 4. Budgets (ASSETS_SPEC.md, plus stricter targets for Blender clips)
| Asset | Desktop (1280) | Mobile (720) |
|---|---|---|
| Hard cap per 8 s clip (12 s = ×1.5) | 1.5 MB | 0.8 MB |
| **Target per 8 s Blender clip** (12 s = ×1.5) | **1.2 MB** | **0.6 MB** |
| Poster | ≤ 80 KB | ≤ 40 KB |
| Product GLB | ≤ 500 KB each (carton ≤ 150 KB, ice tray ≤ 300 KB) | same |
| Turntable fallback `prod-*` (5 s) | ≤ 0.6 MB | ≤ 0.3 MB |
| Initial load | 1.5 MB target, 3 MB cap | 0.8 MB target, 1.5 MB cap |
| Full scroll, one path | **≤ 25 MB** | **≤ 12 MB** |

Why the stricter target: the Ocean path now has 9 Blender clips (4 × 8 s + 5 × 12 s). At the hard caps it would be ~24 MB desktop (just inside) but ~14 MB mobile (over). At the targets it is about **21 MB desktop / 11.5 MB mobile**. So the mobile target is effectively mandatory: if a 720 file is over target, `FORCE=1 MCRF=2 scripts/encode-clips.sh <id>` (mobile crf +2), then reduce fine noise in the render (water micro-detail, foliage, film grain off). Never `TRIM` a Blender clip (its length is fixed in `scenes.sh`). Clean CG usually compresses better than AI footage, so expect most clips under target.

## 5. Time estimates (honest ranges, not measurements)
These depend heavily on the Mac (M1 vs M3 Max), scene density and ray tracing. **Benchmark first:** render 10 frames of each scene at full settings, time them, and put the per-frame time and the projected total in the PR.
| Step | Rough range on Apple-silicon EEVEE |
|---|---|
| Preview frame (960×540, 16 samples, no motion blur) | ~1–6 s |
| Full frame (1080p, 64 samples, ray tracing, motion blur), dense scene | ~5–30 s |
| All previews (≈2,700 frames: 2,686 story + 360 turntable only if needed) | ~1–5 h |
| All full renders (≈2,700 frames) | ~4–22 h, so run them overnight and in parallel with other work |
| Simulation bakes (net, fish, splashes) | minutes to ~1 h per scene |
| Encode + posters + checks, all clips | ~10–20 min |
| Building the library and 9 scene files through the MCP | the real bottleneck: most of 2–3 days |
If a scene runs over ~20 s per frame, in this order: ray tracing resolution 1/4 (distant scenes), samples 48, simpler distant instances, then render at **1600×900 or 1280×720** (the site ships at most 1280 wide, so the visible loss is minimal; say so in the PR).

**Caching:** `vercel.json` serves `/media/*` as `immutable`, and re-rendered clips keep the same names, so browsers would keep the old toy renders. Either content-hash the media names through a manifest (preferred, see FIX_LIST.md) or drop `immutable` for `/media` (`max-age=3600, must-revalidate`) in issue 1, before any final clip lands.

## 6. File names
| What | Where | Committed? |
|---|---|---|
| Scene sources | `assets-src/blender/<blend>.blend`, `asset-library.blend`, `boundaries/*.json`, sim caches | no (git-ignored) |
| Frames | `assets-src/render/<dir>/####.png`, `assets-src/render/preview/<blend>/` | no |
| Masters | `assets-src/video/<id>.mp4` | no |
| Site media | `public/media/<id>_1280.mp4`, `<id>_720.mp4`, `<id>_1280.webp`, `<id>_720.webp`, `<id>_end_1280.webp` | yes |
| Product models | `public/models/{tuna,swordfish,shrimp,carton,ice-tray}.glb` | yes |
| Review | `docs/renders/<blend>-preview.mp4` (≤ 4 MB), `docs/renders/<blend>-fNNN.png`, `docs/renders/<model>-{side,34,head}.png` | yes, on the PR's branch |
| Licences | `docs/LICENSES.md` | yes |
