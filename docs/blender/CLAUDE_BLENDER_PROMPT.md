# CLAUDE_BLENDER_PROMPT.md: paste this whole file into Claude

You are continuing **Skylark Exim v3** (repo `github.com/Tarunchintakunta/skylark-exim-v3`, Vite + React + TS + R3F, GSAP/ScrollTrigger/Lenis, deployed through Vercel). Tarun rejected the current scenes: the port looked like an empty toy, processing was a blurry placeholder, the Products fish look like cartoons. Your job now: **build every story scene end to end in Blender through your Blender MCP connector, render them to scroll-scrubbed video, and rebuild the Products fish photoreal.** You do all of it. Tarun only keeps Blender open with the MCP add-on connected, approves previews, and merges.

Read first, in this order: `README.md`, `SCENES.md` (the spec for every scene), `ASSET_LIBRARY.md`, `RENDER_PIPELINE.md`, `3_DAY_SCHEDULE.md`, `GIT_WORKFLOW.md`, `reference/` (STORY.md, CONTENT.md, BANNED_CLAIMS.md, ASSETS_SPEC.md, `catch-reference.png`, `feedback/*.jpg`). `companion/FIX_LIST.md` (and `CLAUDE_REDESIGN_PROMPT.md`, if Tarun gives it to you too) is the companion brief for smoothness and the redesign; follow both. Split of authority: **what is in each scene** (shots, objects, people, clip ids, frames) = SCENES.md; **engine, pacing, layout and visual design of the site** = FIX_LIST.md / the redesign prompt.

## 0. Hard rules (never break)
1. **Git:** one issue per task → one branch `feat|fix|chore|docs/<issue#>-<slug>` → micro commits (Conventional Commits, each references the issue) → one PR per issue. **Never commit, push, force-push or merge to `main`. Never merge any PR. Only Tarun merges.** Force-push only your own feature branch with `--force-with-lease`. CI (typecheck, build, Playwright smoke + scroll, Lighthouse) green on every PR.
2. **Content:** site copy only from `reference/CONTENT.md` (exact lines in SCENES.md "Copy"). Nothing from `reference/BANNED_CLAIMS.md`. Never name a fishing gear. Never copy text from `catch-reference.png` (it contains a banned term). No new facts, numbers, certifications, places or customers.
3. **No text, logos, brand names, numbers or readable signs inside any render or model.**
4. **Previews before full renders:** every scene goes to Tarun as a 960×540 preview + stills in its PR; full renders only after he says ok in the PR.
5. **Never fake it:** if the MCP connector is down, a render fails, or a scene doesn't meet its acceptance list, say so in the PR and in your report. Don't mark anything done that isn't.
6. **Perf budgets unchanged** (RENDER_PIPELINE.md §4 and ASSETS_SPEC.md): 60 fps desktop, ≥ 50 fps 4× throttled mobile, no long task > 50 ms, Lighthouse mobile ≥ 85, LCP < 2.5 s, CLS < 0.05, full scroll ≤ 25 MB desktop / ≤ 12 MB mobile per path. Only current + next clip loaded.
7. **Secrets:** never commit the Vercel token or any key.

## 1. Before anything
1. **Verify the Blender connection:** call the MCP scene-info tool (e.g. `get_scene_info`). Report the Blender version and the engine id. If it fails, tell Tarun exactly: "Open Blender → press N in the 3D viewport → BlenderMCP tab → Connect", and meanwhile do the repo-only work (§3 issue 1).
2. Check which MCP extras exist (Poly Haven, Sketchfab, Hyper3D status tools). Note them in the first PR.
3. Find the Blender binary for headless renders: `/Applications/Blender.app/Contents/MacOS/Blender --version` (else `export BLENDER=…`). Render 1 test frame headless to prove it works on this Mac.
4. Repo state: `git fetch`, list open PRs and their bases. The old stack (#39–#80) is unmerged. **Base new branches on `main` if Tarun has merged the stack; otherwise on the top branch of the current stack (the last one in PR #39's merge order), and state the base in each PR.** Don't close old PRs; list the ones this work supersedes (#72 port preview, #73–#75 fish, #76–#79 logistics GLBs) in your report and let Tarun close them.
5. Copy this pack into the repo on the docs branch of issue 1: `docs/blender/` (README, SCENES, ASSET_LIBRARY, RENDER_PIPELINE, 3_DAY_SCHEDULE, this prompt, reference/), and `scripts/*.sh` + `blender/*.py` into the repo's `scripts/` and `blender/` (replace the old encode/poster/glb scripts with these versions). `chmod +x scripts/*.sh`. Make sure `assets-src/` stays in `.gitignore`.

## 2. How you work in Blender
- **Small steps through the MCP:** one object or one animation block per call, a viewport screenshot after each important step, and **save after every step** (`bpy.ops.wm.save_as_mainfile(filepath=<abs path in assets-src/blender/>)`). Blender and the repo are on the same Mac, so paths are shared.
- **Library first:** build `assets-src/blender/asset-library.blend` (ASSET_LIBRARY.md), then each scene `.blend` **links** from it (relative paths), with library overrides for anything animated. Same object names in every scene (boundaries depend on it).
- **External assets** only through the MCP's own Poly Haven / Sketchfab (CC0 or CC-BY only) / Hyper3D tools, and only when it offers them. Log every one in `docs/LICENSES.md` (name, URL, author, licence, scene). CC-BY credit goes in the footer.
- **Realism standard:** PBR materials, bevels on every hard edge, wear/rust/grime/wet decals (never letters or logos), HDRI daylight + one sun, AO, real shadows, depth of field, atmospheric perspective for distance (never fog or grey), motion blur, AgX. Fill every frame with the scene's density list; a frame with big empty areas is not done.
- **People:** mid-distance or soft focus, natural varied poses, never a close-up face. Plant staff always in **mask, gloves, hair cap, apron/coat, boots**. Fishermen in **orange/yellow oilskins, caps, gloves** (match `catch-reference.png`).
- **Rigs:** cranes never bend (object transforms only); containers hang on 4 cables from lock to release; vehicles forward only, one direction (except the deliberate reverse in `truck-reverse`); wheels rotate from distance travelled.
- **Simulations** (net cloth, fish rigid bodies, splashes) are **baked** and saved before any headless render.
- **Render settings:** run `blender/render_settings.py` on each scene (EEVEE, 1920×1080, 24 fps, 64 samples, motion blur, AgX, PNG to `assets-src/render/<dir>/`, frame range from `scripts/scenes.sh`).
- **Renders never run inside an MCP call.** Use the terminal: `scripts/render-scene.sh <blend> preview|full` (wraps `Blender -b file.blend -a` in `caffeinate -i`). Benchmark 10 frames first and put s/frame + projected hours in the PR.
- **Boundaries:** for different-.blend joins use `blender/boundary_camera.py` (write in A at its last frame, read in B at frame 1), then `scripts/boundary-check.sh` must print OK.

## 3. Issues (create all first, labels `3d`, `video`, `scene`, `content`, `perf`; milestones Day1–Day3 per 3_DAY_SCHEDULE.md)
| # | Issue title | Branch slug | What's in the PR |
|---|---|---|---|
| 1 | `chore: chapter config for Blender scenes` | `chore/<n>-blender-chapters` | pack docs + scripts into the repo; chapters per SCENES.md "Site config changes" (o-catch-a/b, o-return, p-harvest, new **Arrival** chapter with `truck-reverse`, x-cranes 180 vh, join types); copy per SCENES.md "Copy"; **remove every "placeholder" label/overlay from the site**; stand-in logic (preview clip → poster); media cache fix (hashed names or no `immutable` on `/media`, RENDER_PIPELINE.md §5) |
| 2 | `3d: asset library` | `feat/<n>-asset-library` | stills of every library asset group (`docs/renders/lib-*.png`), `docs/LICENSES.md` |
| 3 | `scene: o-catch (o-catch-a + o-catch-b)` | `feat/<n>-scene-o-catch` | preview → (ok) → final clips + posters + stills + checks |
| 4 | `scene: x-cranes (port.blend build)` | `feat/<n>-scene-x-cranes` | preview of all 479 frames → (ok) → x-cranes media |
| 5 | `scene: x-ship` | `feat/<n>-scene-x-ship` | x-ship media (same full render as #4) + globe colour match |
| 6 | `scene: truck-reverse` | `feat/<n>-scene-truck-reverse` | same pattern |
| 7 | `scene: p-intake` | `feat/<n>-scene-p-intake` | same pattern |
| 8 | `scene: p-proc` | `feat/<n>-scene-p-proc` | same pattern |
| 9 | `scene: p-freeze` | `feat/<n>-scene-p-freeze` | same pattern |
| 10 | `scene: o-return` | `feat/<n>-scene-o-return` | same pattern |
| 11 | `scene: p-ponds` | `feat/<n>-scene-p-ponds` | same pattern |
| 12 | `scene: p-harvest` | `feat/<n>-scene-p-harvest` | same pattern |
| 13 | `3d: tuna (photoreal)` | `feat/<n>-tuna` | 3 stills on the ice bed → (ok) → GLB or turntable |
| 14 | `3d: swordfish (photoreal)` | `feat/<n>-swordfish` | same |
| 15 | `3d: shrimp (photoreal)` | `feat/<n>-shrimp` | same |
| 16 | `feat: products stage (ice bed, carton, studio light) + species list layout` | `feat/<n>-products-stage` | `ice-tray.glb`, `carton.glb`, R3F studio lighting, **fix the species list that's cut off on the right** (wraps/scrolls in its column 360–1920 px, checked at 375/768/1280/1920) |
| 17 | `perf: full-scroll audit with Blender clips` | `perf/<n>-blender-audit` | `scripts/path-weight.sh`, Playwright scroll fps/long tasks both paths, Lighthouse mobile; fixes if anything is over |
Scene PRs (3–12) touch only `public/media/<their ids>*`, `docs/renders/<blend>-*` and (if needed) that chapter's entry, so they don't conflict; base them on issue 1's branch until Tarun merges it, and say so. If the redesign prompt also has open issues, keep their branches separate.

## 4. Per-scene loop (do this for each of issues 3–12)
1. Build the `.blend` from library links to SCENES.md: shot list by frame, density list, animation beats, lighting. Viewport screenshots as you go. Save often.
2. Bake sims. `blender/render_settings.py`. Benchmark 10 frames.
3. `scripts/render-scene.sh <blend> preview` → open the PR as **draft** with: `docs/renders/<blend>-preview.mp4`, 3–5 stills at key frames (`<blend>-fNNN.png`), the acceptance list from SCENES.md ticked honestly, the benchmark, and an encoded stand-in clip so the site shows the preview on the Vercel preview URL.
4. **Message Tarun (in your chat report): "Preview ready: <scene> – PR #n – reply ok or notes."** Wait. Apply notes → new preview.
5. After ok: `scripts/render-scene.sh <blend> full` (terminal, overnight if long) → `frames-to-master.sh` → `boundary-check.sh` → `encode-clips.sh` → `make-posters.sh` → `check-clip.sh` (no `!!`; fix any `!`) → commit the `public/media` files → update the PR (numbers, final stills, preview URL), mark ready for review.
6. Playwright: scroll through that chapter on the Vercel preview, both directions, confirm no stutter at the joins and no visible pop at shared frames; put fps/long-task numbers in the PR.

## 5. Order of work
Day 1: connection + repo checks → issue 1 (config, no placeholders) → issue 2 (library: people/outfits, crates/ice, reefer truck, fishing vessel + net + fish proxies, then containers/cranes/ship/tug) → **o-catch** preview (Tarun's must-have) → **port** preview. Night: full renders of whatever Tarun approved.
Day 2: plant chain **truck-reverse → p-intake → p-proc → p-freeze** (shared plant set; boundaries) previews → finals of approved scenes; Products fish look-dev starts. Night: plant full renders.
Day 3: **o-return, p-ponds, p-harvest** (reuse vessel, truck, pond grid) → Products fish + stage + list fix → all finals encoded → issue 17 audit → report.
If time runs short, ship in this priority: o-catch, x-cranes/x-ship, truck-reverse, p-proc, p-intake, p-freeze, Products, p-harvest, o-return, p-ponds. Unfinished scenes keep their approved preview as a stand-in (never a labelled placeholder) and are listed in the report.

## 6. Done = all of this
- [ ] 11 story clips final and encoded: o-catch-a, o-catch-b, o-return, p-ponds, p-harvest, truck-reverse, p-intake, p-proc, p-freeze, x-cranes, x-ship; each PR approved by Tarun.
- [ ] Every shared join passes `boundary-check.sh`; cross-fades look continuous.
- [ ] `check-clip.sh` passes for every clip (brightness, GOP 6/no B-frames, size).
- [ ] `path-weight.sh`: Ocean and Pond ≤ 25 MB desktop, ≤ 12 MB mobile.
- [ ] Products: photoreal tuna, swordfish, shrimp on the ice bed (GLB ≤ 500 KB each, or turntables/stills), approved; species list not cut off.
- [ ] No placeholder labels anywhere; no text/logos in any render; copy only from CONTENT.md; no banned claims (`grep -riE` the BANNED_CLAIMS terms over `src/` returns nothing).
- [ ] Perf numbers (desktop + 4× throttle, both paths) and Lighthouse mobile in issue 17's PR.
- [ ] Nothing pushed to or merged into `main` by you.

## 7. Report to Tarun (end of each day and at the end)
Plain list: PRs opened (with links) and their state; previews waiting for his ok; scenes final vs stand-in; per-scene s/frame and total render hours; clip sizes; path weights; perf numbers; licences used; anything you couldn't do and why; which old PRs are superseded (for him to close).
