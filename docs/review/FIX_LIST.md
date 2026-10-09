# Skylark Exim v3: full audit and fix list

**Branch:** `perf/34-lazy-product-stage` @ `f555d2d` (github.com/Tarunchintakunta/skylark-exim-v3)
**Date:** Fri 9 Oct 2026

**How it was tested:**
- Local `vite build` + `vite preview` on :4174, with headless Playwright Chromium at 1440×900. Requests were recorded over CDP and frames/long tasks with PerformanceObserver.
- Ocean and Pond were both scrolled end to end with real wheel input (60 px every 16 ms).
- ffprobe ran on every clip.
- Screenshots were taken per chapter on a fresh page each time.

**Evidence:**
- Screenshots: `review/v3b/{ocean,pond}-NN-<chapter>-<pct>.png`
- Raw network/perf data: `review/v3b/{ocean,pond}-network.json`
- Bug proofs: `review/v3b/bug-evidence/`
- Tarun's chore/80 screenshots: `review/*.png`

> **Measurement caveat:** the box has no GPU, so its fps is not what a laptop sees. The long tasks, bytes, request timing, seek latency and code paths below are real.

**Severity:** 🔴 = Tarun sees it on every visit · 🟠 = clearly visible / costs smoothness · 🟡 = polish

---

## Key numbers (cold, local, 1440×900)

| | Ocean | Pond |
|---|---|---|
| Before first scroll | **1.98 MB** / 30 requests | **1.24 MB** / 26 requests |
| One full scroll | **11.0 MB** | **6.0 MB** |
| Down + back up (Ocean re-downloads every clip) | 19.8 MB | 6.0 MB |

- **Heaviest files:** a4_1280.mp4 2.0 MB · a3 1.49 MB · a2 1.45 MB · x-cranes 1.16 MB · a1 1.03 MB · x-ship 0.93 MB · company-profile.pdf 2.97 MB (on demand) · three.js chunk 234 KB gz · main JS 167 KB gz.
- **Wasted:** opening clip downloaded twice at boot (561 KB × 2); 16 posters + end-posters (~600 KB) fetched right after the loader; fonts requested twice.
- **Long tasks:** Ocean 5 (52/70/76/108/**475 ms**), Pond 3 (62/92/218 ms), all when Products' GLBs + three init. None during the film.
- **Video:** 1280×720 (desktop) / 720×406 (mobile), H.264 High 24 fps, GOP 6 (0.25 s), no B-frames, faststart ✔, 0.57–1.5 Mbps. Seek latency on the box: median 13 ms, p90 21 ms.

## Verdict in one paragraph
The engineering base is decent:
- One ticker, Lenis wired correctly, no per-frame React state.
- GOP-6 / no-B-frame / faststart encodes.
- Lazy three.js and a small initial load.

The **site Tarun sees** is a different story:
- 6 of the 14 story chapters are frozen still photos or toy renders, and 3 of them show a `PLACEHOLDER · AWAITING …` tag.
- The headlines stack on top of each other at chapter changes.
- A dashboard HUD box, chapter rail and boxed buttons sit on every frame.
- The videos are 1280×720, upscaled to full screen (soft), and only start downloading when their chapter begins, so on a real network the picture freezes and then jumps.
- The business half is a plain white template.

It reads as the kohl draft rebuilt with a control panel on top, not a new cinematic site. The fix is not a perf tweak. It's (a) real moving footage or Blender renders in every chapter, (b) removing the chrome, (c) a new opening, a new type system and a new design language, and (d) fixing the 6 engine bugs below.

---

## 1. Smoothness / network (why it stutters for Tarun but "passes" Claude's tests)

### 🔴 S1. Clips start downloading only when their chapter begins, so the frame freezes and then jumps on a real network
- **Cause:** `src/film/scrub.ts:148-156`.
  - The current clip's `src` is set the moment the segment becomes active (`slotFor(want)` → `load()` at `:79-90`).
  - The *next* clip is only requested once the current one is past **50%** (`const next = p > 0.5 ? …`).
  - Each clip is a single `bytes=0-` request: a1 1.0 MB, a2 1.45 MB, a3 1.49 MB, a4 **2.0 MB**, x-cranes 1.16 MB, x-ship 0.93 MB.
- **Measured locally:** every clip's request starts exactly at chapter entry (see `ocean-network.json`: a1 at `start`→`o1` boundary, a4 on entering `o3`, etc.).
- **What happens on a real network:**
  - On Vercel over normal Wi-Fi or 4G, a 1.5–2 MB clip takes 0.5–3 s.
  - While it buffers, `seek()` (`:184-193`) returns early (`readyState < 1`), or seeks into ranges that aren't buffered and stall.
  - The poster stays up and the picture is frozen while the page and captions keep moving. That's the "not smooth af".
  - Inside `o1`, a2 is requested at 50% of a1, which is only ~100 vh (≈0.5–1 s of normal scrolling) ahead.
- **Fix:**
  - Prefetch the next clip as soon as the current one has `canplaythrough` (not at 50%).
  - Keep a 3-slot decoder pool: prev, current, next.
  - Never seek a slot whose `buffered` range doesn't cover the target; hold the last good frame instead.
  - Make clips smaller (see S3) so they buffer in < 1 s on 4G.

### 🔴 S2. "60 fps, 0 long tasks, Lighthouse 0.97" (PR #82) measures the wrong thing
The gap between the tests and Tarun's experience has these causes:
1. **Localhost, not the deployed preview:**
   - `tests/helpers.ts` opens `/` on `vite preview`.
   - Media arrives instantly (my log shows every MP4 finishing within 10–20 ms of starting), so S1 never shows up.
   - Tarun is on the Vercel preview, which also injects the **Vercel toolbar/auth** (`jwe`, `validate?hostname=…`, feedback script).
2. **rAF cadence ≠ video smoothness:**
   - `tests/scroll-perf.spec.ts:21-27` counts `requestAnimationFrame` intervals.
   - Video seeks are decoded asynchronously, so rAF stays at 60 while the `<video>` shows the *same* frame or the poster.
   - Nothing measures **presented video frames** (`requestVideoFrameCallback`), **seek latency** or **time spent on a stale frame or poster**.
   - On the box, seeks measured **median 13 ms, p90 21 ms, max 33 ms locally (289 seeks over a 6,000 px wheel scroll). So decoding is fine; the stutter users feel is buffering/network (S1) and the frozen still chapters (S9), which the test never sees**.
3. **Mobile "4x throttled" uses `window.scrollBy`** in a rAF loop (`tests/helpers.ts:26-38`), not touch. That's a perfect programmatic scroll with no inertia.
4. **Warm cache / no cold load:**
   - The 0.9 MB "initial" excludes the loader's 600 KB range fetch plus the duplicate full re-download of `opening` (S5), and the 16 posters fetched right after.
   - My cold run: **1.98 MB before first scroll (Ocean), 1.24 MB (Pond)**.
5. **Static stills score perfect:**
   - A 200 vh chapter showing one JPEG-like still has 0 work to do, so the fps test loves it.
   - To a human it reads as "stuck": the page moves but the picture doesn't.
6. **Lighthouse measures load only**, never scroll.
7. **Why Tarun's DevTools showed only 217 kB / 9 of 45 requests on Process:** that chapter has *no video at all*, just a cached 17 KB still. Nothing was loading, and nothing was moving. The other requests were the Vercel toolbar/auth (`jwe`, `validate?hostname=`), which doesn't exist in the tests.

**Fix (acceptance):**
- Measure on the **deployed preview with protection off, cold cache, real wheel/trackpad input (and a real phone touch-scroll)**.
- Record **presented-frames/s via rVFC, seek p50/p95, % of scroll time showing a stale frame**, plus a screen recording. Details are in the prompt.

### 🟠 S3. Video resolution and bitrate are wrong for full-bleed at 1440 px and up
- **The clips (ffprobe):**
  - Every desktop clip is **1280×720** H.264 High, 24 fps, GOP 6 (0.25 s), `has_b_frames=0`, faststart OK, 0.57–1.5 Mbps, 8 s (a4 12 s).
  - Mobile: **720×406**.
- **Effect:**
  - At 1440×900 with `object-fit: cover`, 720 p is upscaled ×1.27 (×2.5 on Retina), so it looks soft.
  - Tarun's DevTools-narrowed window got the **720×406** files (`segments.ts:27`, `max-width: 819px`), which look blurry.
- **Fix:**
  - Encode a **1920-wide** desktop tier: `-crf 22 -g 8 -bf 0 -preset slow`, roughly 1.5–2.5 MB per 8 s.
  - Keep 1280 for ≤ 1280 viewports, and 960×540 for mobile (not 720×406).
  - Pick the tier by `innerWidth * min(dpr, 1.5)` at load.
  - Re-render Blender clips at 1920×1080 (they are currently 960×540 previews upscaled to 1280).

### 🟠 S4. Bug: the global `.stage__light` (globe) layer stays at opacity 1 after you visit the business sections, so every still chapter turns into a blank light-grey screen
- **Cause:**
  - `scrub.ts:128-136`: when `frame.past` becomes true it releases decoders and sets `cur = -1`, but leaves the poster layers' opacity as is. The globe layer stays at 1.
  - Coming back (nav "Story", the rail, or scrolling up from Products), `enter(i, prev=-1)` (`:195-202`) can't clean up the previous layer, because it only clears `posters[prev]` when `prev >= 0`.
  - The globe layer is later in the DOM than the still `<img>` layers, so it covers every still chapter (videos are `z-index: 1` and still show).
- **Proof:** `review/v3b/bug-evidence/process-after-returning-from-globe.png` and `o2-after-returning-from-globe.png`.
- **Fix:**
  - When hiding, reset *all* poster/layer opacities to 0 and clear `over`.
  - In `enter()`, when `prev < 0`, zero every layer except `i`.
  - Add a Playwright test: scroll to `#quote` → click nav "Story" → assert only one stage layer has opacity > 0.

### 🟠 S5. The opening clip downloads twice during the loader, and fonts are fetched twice
- **Cause:**
  - `engine/preload.ts:14,24` fetches `opening_1280.mp4` with `Range: bytes=0-614399` through `fetch()`.
  - Then the `<video>` element requests `bytes=0-` again. The fetch cache isn't shared with the media element's range requests: 561 KB + 561 KB.
  - The 4 fonts are also `fetch()`ed while already `<link rel=preload>`ed, which doesn't match the preload (no `crossorigin`/mode), so you get double requests.
- **Fix:**
  - Drive loader progress from the *video element itself*: set `src` early with `preload=auto` and read `buffered`/`progress` events.
  - Fonts: use `document.fonts.load()` only.

### 🟠 S6. All 16 posters + end-posters (~600 KB) load right after the loader, even for the last chapters
- **Cause:** `ScrubStage.tsx:37` (`src={ready || i === 0 ? …}`) plus `scrub.ts:220-225` `preloadPosters()` fetch every `_end_1280.webp` at once.
- **Fix:** load posters for the current, next and next+1 chapters only. Load end-posters only for the chapter you are in, for back-scrolling.

### 🟠 S7. Backdrop-filter blur on boxes floating over moving video
- **Cause:** `ui/hud.css:10` (`backdrop-filter: blur(10px)` on the HUD panel, on screen in every chapter), `ui/start.css:13` (path buttons), `ui/start.css:40` (path pill, on screen all the time) and `film/stage.css:15` (`filter: blur(14px)` on a full-screen layer in Docs).
- **Effect:** a backdrop blur over a `<video>` that changes every frame forces a GPU re-blur of that region every frame. It's cheap on an M-series Mac, but it's a known jank source on integrated GPUs and phones.
- **Fix:**
  - Delete the HUD and boxed buttons (see U1/U2), so nothing uses backdrop-filter over video.
  - For Docs, use a **pre-blurred WebP** instead of a live `filter: blur`.

### 🟠 S8. Long tasks when Products mounts (GLB parse + texture upload + shader compile)
- **Measured (box CPU):**
  - Ocean: 52, 76, 108, 70 and **475 ms** at the Products section, from `constants-*.js` (three) `Gv`/`da` and `index-*.js D`.
  - Pond: 62, 92, 218 ms.
- **Cause:**
  - `three/ProductStage.tsx` mounts the GLBs (tuna 193 KB, swordfish 151 KB with 1024 textures) when Products is near.
  - The meshopt decode, texture upload and program compile all land in the same frames.
  - The globe canvas also stays mounted after `world`, because `GlobeLayer.tsx:11` keeps `near` true while the store chapter is `world`. That means 2 WebGL contexts are alive.
- **Fix:**
  - Preload and `gl.compileAsync` + `initTexture` for product models in idle slices one section earlier (as `Globe.tsx:46-53` already does).
  - Unmount the globe canvas when `frame.past`.
  - Use KTX2/ETC1S or flat colours instead of 1024 WebP textures.
  - Better still, **use one shared R3F canvas** for the globe and products (see the reference recipe).

### 🟡 S9. 200–240 vh chapters with nothing moving
- `process` (200 vh) and `coldchain` (240 vh) are a single still with a 1.04 scale (`scrub.ts:161`), and `o2` (140 vh) reuses **the same a3 tuna frame** that `o3` then plays.
- That's 6+ screens of scrolling where only text changes, which reads as lag.
- **Fix:** every chapter must show real motion (video or Blender render), with scroll length ≈ clip length × 25 vh/s.

### 🟡 S10. Cache headers make clip replacements invisible to returning visitors
- **Cause:** `vercel.json` sets `Cache-Control: public, max-age=31536000, immutable` on `/media/*` and `/models/*`, but the file names are **not hashed** (`x-cranes_1280.mp4`).
- **Effect:** when Claude replaces the 960×540 preview with the final render under the same name, Tarun's browser (and every CDN edge) keeps the old one for a year.
- **Fix:** content-hash the media file names (e.g. `x-cranes.3f9a2c_1920.mp4` via a manifest), or drop `immutable` and use `max-age=3600, must-revalidate` for `/media`.

### 🟡 S11. Other engine notes
- **Decoders released, then re-downloaded on the way back:**
  - Scrolling from `quote` back up re-requests every clip (Ocean full log: **19.8 MB transferred**, because each clip came down twice; a single pass is about 11 MB).
  - Fix: keep `src` on the two nearest slots; don't release everything on `frame.past`.
- **Lenis settings:** `lerp: 0.1` (`engine/ticker.ts:21`) is fine. Add `wheelMultiplier: 0.9`, and make sure the scrub target is the *Lenis* value (it is). No change needed besides S1.
- **Bundle:** `index-*.js` is 524 KB (173 KB gz), with zod + react-hook-form in the critical bundle. Lazy-load the quote form chunk.

---

## 2. Opening (Tarun: "this opening is not needed")
**🔴 O1. The start screen reads like a dashboard.**
- **What's on it:**
  - A dark, mostly empty underwater frame.
  - Two outlined boxes, THE OCEAN / THE POND (`ui/StartScreen.tsx:73-93`, `ui/start.css:7-21`).
  - A floating `COLD CHAIN · STEP 01/09` HUD box mid-right.
  - A mono eyebrow and a "Skip the story → Products" link at the top.
  - The headline only appears after 55% of the chapter (`StartScreen.tsx:41`).
  - A tiny "Scroll" cue.
  - The sticky quote button already showing.
- **The core problem:** the user is forced to make a *choice* before seeing anything beautiful.
- **Fix:**
  - Loader → logo reveal → a full-bleed **moving** shot (the `opening` clip playing or scrubbed at 1920) with one large editorial headline in the first frame.
  - The scroll begins **Ocean by default**.
  - Ocean/Pond becomes a small, elegant text toggle in the header (or a single line "Wild catch / Farmed shrimp" under the headline). No boxes, no HUD, no skip link, no quote button until after the first chapter.

---

## 3. Scene by scene

| # | Chapter | What Tarun sees | Problem | Fix |
|---|---|---|---|---|
| 🔴 | **Process** (200 vh) | One blurry still of a **lab bench + microscope** (17 KB WebP at 1280), the dashed `PLACEHOLDER · AWAITING P-PROC` tag top-right, and the HUD box overlapping the monitor. "Washed clean" sits over a lab bench, which is the wrong scene for washing. | Placeholder, wrong subject, no motion, label shown (`ScrubStage.tsx:46-53` renders the tag whenever `__PREVIEW__`, i.e. on *every* Vercel preview). | Blender processing-line render (workers in masks/gloves/hair caps, washing tank → grading table → peeling line), 3 beats in one continuous camera move. Never render placeholder tags. |
| 🔴 | **Lab · freeze · pack · cold store** (240 vh) | One still of a racked freezer aisle for 4 captions (lab, freezing, packing, cold storage); a placeholder tag. | Same frame for 4 different steps. | Blender: QC lab table → IQF tunnel/plate freezer with glaze → carton packing + label → cold store (realistic, lightly frosted, not over-frosted). |
| 🔴 | **Intake** | Still of a reefer box at a dock door at night; placeholder tag. | Static, dark, and the truck isn't clearly backed rear-first with the driver outside. | Blender: truck reverses rear-first to the lit dock door, driver standing outside by the cab, crates moving in. |
| 🔴 | **Port** (x-cranes) | A 960×540 preview: plain grey toy cranes, one teal box, an empty flat quay, a tiny truck far off, hazy grey sky; placeholder tag + HUD box. Tarun: "looks empty empty". | Low-poly, unlit, no port life. | Full real-port brief in §6 (3D/Blender, B1). |
| 🟠 | **At sea** (x-ship) | Top-down ship on a flat, uniform blue plane, no wake/waves, blocky containers; placeholder tag. | Toy-like water; the hard colour block also fights the globe hand-off. | Ocean shader/displacement with wake, foam and specular sun glint, a detailed hull and lashing bridges, slight camera drift; end frame graded to match the globe's sky blue. |
| 🟠 | **O2 "Out of the water"** | The *same* tuna-on-ice frame as O3, frozen for 140 vh. | Duplicate visual, no catch moment. | Real catch footage (Higgsfield `o-catch`) or cut the chapter. |
| 🟠 | **P1 "The ponds"** | b2 first-frame still (dark aerial ponds), placeholder `p-ponds`. | Static, dark. | Real pond clip (golden-hour aerial, aerators running), or a Blender aerial of pond grids with water shader. |
| 🟠 | **Docs** | Blurred, darkened freezer still with 3 white "paper" cards; in chore/80, "Paperwork, done properly" stacked over "Held at −18 °C to −20 °C". | Live blur, dashboard-like cards, overlap. | One clean editorial composition: big headline + 3 lines of text over a real, slow shot (e.g. a document folder + stamped carton label in Blender). No cards. |
| 🟡 | **World/globe** | Bright globe ✔, but the HUD box sits *on* the globe; 16 market chips look like tag pills; the start of the chapter has no caption. | Chrome over the hero. | Remove the HUD; market names as a typographic list (2 columns, serif), route labels on the globe only. |
| 🟡 | **O1, O3, O4, P2, P3** | Real footage, OK. | Soft at 1280; dark bottom-left scrim on every frame (`stage.css:17-21`) flattens it all into a navy wash. | 1920 tier; per-chapter grading; a lighter, shorter scrim only behind the text block. |

---

## 4. UI chrome (the "dashboard" look)
- 🔴 **U1. Cold-chain HUD box on every frame:**
  - `ui/Hud.tsx` + `ui/hud.css`: a glass panel right-centre with "COLD CHAIN · STEP 02 / 09 · WASHING".
  - It overlaps the picture in every chapter, and the numbering is **inconsistent**:
    - Process shows 02 → **04** → **03**, because `config/chapters.ts:115-117` orders Washing 02, Grading 04, Processing 03, while the website's workflow is 3 = Processing, 4 = Grading.
    - Docs, Port, At sea and World are all "09/09".
    - Start is "01" before anything happens.
  - **Fix:** remove it. If a step indicator is kept at all, use one hairline progress line + a small serif chapter number in the corner, Mont-Fort style.
- 🟠 **U2. Chapter rail** (`ui/Rail.tsx`, `chrome.css:41-56`): 14 grey ticks on the left edge, with hover labels in mono pills. **Fix:** remove, or replace with a minimal chapter title in the header on chapter change.
- 🔴 **U3. Placeholder tags on previews** (`ScrubStage.tsx:46-53`, `stage.css:22`, `vite.config.ts:7` `__PREVIEW__ = VERCEL_ENV !== 'production'`): every preview Tarun opens shows dashed `PLACEHOLDER · AWAITING …` banners (6+ scenes). **Fix:** delete the feature; track placeholders in the PR body instead.
- 🟠 **U4. Pills and boxes everywhere:** `OCEAN ⇄ POND` pill centred in the top bar (`chrome.css:22`), species chips (`film.css:21-22`), market chips, doc cards, the label card, boxed product/state chips in the form. **Fix:** text-only toggles and typographic lists.
- 🟠 **U5. Sticky "REQUEST EXPORT QUOTE" button bottom-right on every frame**, including the cinematic opening. **Fix:** show it only from Products onward, or as a quiet text link in the header.
- 🟡 **U6. Top bar cut off / crowded:** the eyebrow and skip link sit under the header on the start screen. **Fix:** a single clean header (logo left, 4 links right, toggle).

## 5. Typography and design
- 🔴 **T1. Fonts** (Tarun dislikes them): Sora 600 headlines + Inter body + **JetBrains Mono** in all-caps for every eyebrow, label, nav item, chip and button (`styles/tokens.css:2-5,31-33`). Mono all-caps everywhere is the core of the "dashboard" feel.
  - **Fix:** a new type system (pairing options, scale and rules in the prompt):
    - Editorial serif/display headlines.
    - A clean body face.
    - Mono removed or limited to one tiny use.
    - Self-hosted, subset, free licence (Google Fonts / Fontshare).
    - 2–3 pairing options shown on a preview page for Tarun to choose from.
- 🔴 **T2. Stacked headlines at chapter changes** (Tarun's chore/80 screenshots `08-ocean-ch05-intake.png`, `11-ocean-ch08-documentation.png`):
  - "Both origins arrive at one door." is drawn over "Home under a chilled seal.", and "Paperwork, done properly." over "Held at −18 °C…".
  - **Cause:**
    - `film/captions.ts:37-44`: on a caption change, `hide(old)` and `show(new)` start **in the same frame**.
    - `hide()` (`:59-61`) fades the old one out over **0.45 s with `power2.in`**, so it is still ~80% opaque after 0.2 s. Meanwhile `show()` (`:46-57`) instantly sets the new caption `autoAlpha: 1` and slides its lines up.
    - Both are `position: fixed` at the **same** bottom-left spot (`film/film.css:6-15`), so they overlap.
    - The gap between captions (e.g. o4 ends at local 0.9, intake starts at 0.1) is only ~100–200 px of scroll, i.e. one wheel notch.
    - There's a second path: `show()` calls `gsap.killTweensOf(el)` only on the *incoming* element, so fast back-and-forth leaves several half-faded captions.
  - **Fix:**
    - Sequence it: hide the old caption over 0.25 s with `power2.out`, and start the new one only after the old one has finished (or after 0.2 s).
    - Clip each caption's lines with masks so the outgoing one moves *up and out* and the incoming one comes *up and in* in the same mask.
    - Never show 2 captions: keep one shared caption container and swap its content.
    - Add a test that asserts ≤ 1 visible `.caption` at 0/250/500 ms after crossing every boundary (my probe results: `review/v3b/bug-evidence/caption-overlap-*.png`, reproduced at 3 of 3 boundaries tested (o3→o4, o4→intake, coldchain→docs) with a 3-notch wheel flick. The old headline was still at 79–99 % opacity when the new one was already at 100 %).
- 🟠 **T3. Hierarchy:** every chapter uses the same layout: bottom-left headline, 1 grey sentence, a mono eyebrow, over a navy scrim. No scale changes, no full-width moments, no numbers/quotes as graphic elements. **Fix:** a varied editorial layout per chapter (see the prompt's design section).
- 🟠 **T4. Dark/low-contrast scenes:** the opening, intake, docs, the ponds and the port are all deep navy/grey; the left+bottom scrim (`stage.css:20`) darkens even bright plant frames. **Fix:** grade the footage brighter (morning/day), use a smaller scrim, and use light chapters (plant interiors on white) for rhythm.
- 🔴 **T5. Hard seam from the dark story into the white business sections**: the globe ends, then a flat `#eef5f6` page with a template grid ("Our Products", "Why choose us" tiles, form) starts. **Fix:** a designed transition (globe zooms to a white paper texture / a sliding panel with a ScrollTrigger mask), and business sections in the same editorial language (large serif, full-bleed product imagery, 2-column text).
- 🟠 **T6. Business sections look like a generic template:** small toy fish on an empty white stage, a plain list of species, 6 bordered tiles, a standard form grid with chips. **Fix:** products as large studio renders (Blender, Zoi-style), species as an editorial index, "Why choose us" as 3 large statements with real photos/renders, and a quote form that's two columns, generous and serif-led.
- 🟡 **T7. It's still the kohl draft in a new repo:** same reused clips (opening/a1–a4/b2/b3), same navy+brass palette, same bottom-left caption + scrim pattern, and the same "dashboard" idea. **Fix:** new palette (ivory/sand + deep sea + one accent), new type, new layouts, new Blender scenes.

## 6. 3D / Blender
- 🔴 **B1. Port scene (x-cranes) looks empty and toy-like** (Tarun: "the place looks empty empty, I need multiple things, check how real ports look end to end"). The current render has:
  - 3 plain grey boxes-on-legs cranes with no lattice, machinery house, cabin or trolley detail.
  - One teal box hanging.
  - An empty flat grey quay with no markings.
  - A tiny truck far off and a few distant containers.
  - A hazy grey sky, flat lighting, no shadows/AO and no people.
  - **Fix:** the full real-port brief in the prompt (gate + truck queue, container yard with colour + reefer stacks and reefer racks, RTGs/straddle carriers, 3 detailed STS cranes, berthed ship with lashing bridges, tugs, light poles, markings, bollards, workers in hi-vis, water reflections, a bright sky with clouds + HDRI, PBR/wear, DOF, atmospheric perspective, a low-angle moving camera, EEVEE shadows + AO, 1920×1080).
- 🟠 **B2. x-ship:** blocky hull, flat blue plane, no wake. (Fix in §3.)
- 🟠 **B3. Product fish are toy-like** (`public/models/tuna.glb`, `swordfish.glb`, `shrimp.glb`; renders in `docs/renders/*-34.png`):
  - Smooth plastic shading, cartoon proportions, no scale/fin detail, small on an empty stage.
  - **Fix:**
    - Rebuild with proper anatomy references: yellowfin tuna, swordfish and Vannamei shrimp.
    - Bake real colour/normal/roughness (scales, iridescence, wet sheen) at 1024–2048 → KTX2.
    - Present them larger: one hero per screen with a slow turntable and studio lighting, or pre-rendered turntable video if real-time can't look real.
- 🟠 **B4. Missing scenes that block the story** (intake, processing, freezer/pack, ponds, catch): Tarun authorised Claude to build any of these in Blender rather than wait for Higgsfield (brief in the prompt).
- 🟡 **B5. The Blender renders are 960×540** and named `_1280` after upscaling. Render at 1920×1080, 24 fps, EEVEE, then encode tiers.

## 7. Copy (vs CONTENT.md; only real facts)
Copy is mostly clean: all body lines trace to CONTENT.md, and no banned claims were found. Fix these:
- 🟠 **C1.** HUD step order 02 → **04 → 03** in Process (`config/chapters.ts:115-117`) contradicts the website workflow (3 Processing, 4 Grading). It also shows 09/09 on four chapters. (This goes away with the HUD.)
- 🟡 **C2.** `o2` caption "Initial quality checks (size, freshness, health) are done before acceptance" sits on a boat/catch scene, but on the real site that's an acceptance step at the plant. Move it to Intake.
- 🟡 **C3.** Alt/sr-only text says "**yellowfin** tuna" (`config/chapters.ts:64,70`). The site only says "Tuna", so drop "yellowfin".
- 🟡 **C4.** Code comments still say "Bay of Bengal" (`stage.css:9`, `Globe.tsx:31,77,86`). It isn't visible, but keep it out of any visible copy.
- 🟡 **C5.** Headline style: "Home under a chilled seal.", "Made to order." and "Out of the water." are editorial and allowed, but weak. Have Tarun approve the headline set in one PR (list in the prompt).

## 8. Repo / CI
- 🟠 **R1.** Perf tests don't measure what users feel (see S2). Add the `video-smoothness` test + preview-URL runs.
- 🟠 **R2.** Placeholder machinery (`__PREVIEW__`, `awaiting` fields, `stage__ph`) must be deleted, not just hidden.
- 🟡 **R3.** The 20+ PRs are stacked; the merge order lives in PR #39. Keep that up to date and squash-merge in order (Tarun merges).
- 🟡 **R4.** The Vercel preview is behind Vercel Authentication, so Tarun and reviewers can't open it on a phone without logging in. Turn Deployment Protection off for previews or create a share link.
- 🟡 **R5.** `vercel.json` immutable caching on un-hashed media (S10).
