> **How to start:** paste `companion/CLAUDE_REDESIGN_PROMPT.md` first (Claude fixes the code while Blender renders run), then `CLAUDE_BLENDER_PROMPT.md`. Both work in the same repo, on separate issues and branches. Where they differ on scenes or 3D, this pack's `SCENES.md` wins; for engine, design and fonts, the redesign prompt wins.

# skylark-blender-scenes: every Skylark Exim v3 story scene, built in Blender by Claude

**What this is.** A hand-off pack for Claude (Claude Code with the Blender MCP connector on Tarun's Mac, the repo `github.com/Tarunchintakunta/skylark-exim-v3`, and Vercel). Claude builds every story scene end to end in Blender, renders it to scroll-scrubbed video, and rebuilds the Products fish photoreal. It replaces the toy port, the placeholder plant scenes and the cartoon fish Tarun rejected. **No Higgsfield clips are needed any more.**

**Start:** paste `CLAUDE_BLENDER_PROMPT.md` into Claude with this folder attached.

## The scenes (story order)
| # | Clip id | What you'll see | Length |
|---|---|---|---|
| 1 | `o-catch-a` | Net in the sea with floats → winch and boom haul it up dripping → swings over the rail → fish released onto the deck (matches `reference/catch-reference.png`) | 8 s |
| 2 | `o-catch-b` | Crew in oilskins sort the fish into iced crates → crates go into the hold | 8 s |
| 3 | `o-return` | Boat back in a busy Visakhapatnam fishing harbour, crates into a white reefer truck | 12 s |
| 4 | `p-ponds` | Bright morning aerial over the shrimp pond grid, aerators running, one vehicle direction | 8 s |
| 5 | `p-harvest` | Shrimp netted out of the pond into iced crates, onto the reefer truck | 12 s |
| 6 | `truck-reverse` | Truck arrives at the plant, turns, **reverses rear-first** into the bay, cab outside, **driver stands outside**, rear doors open into the plant (both paths meet here) | 12 s |
| 7 | `p-intake` | Masked, gloved, hair-capped workers move iced crates on steel trolleys into the intake hall | 8 s |
| 8 | `p-proc` | Processing hall **already mid-shift**: washing, grading, peeling | 12 s |
| 9 | `p-freeze` | Lab → plate/blast freezer (light frost) → packing → cold store | 12 s |
| 10 | `x-cranes` | Busy real container terminal: gate queue, yard, RTGs, 3 detailed cranes; crane 2 lifts a white reefer from the truck onto the ship | 12 s |
| 11 | `x-ship` | Top-down: ship sails out with wake, tugs peel away, ends on bright blue into the globe | 8 s |
| 12 | Products | Photoreal tuna, swordfish, shrimp on a crushed-ice bed (GLB ≤ 500 KB, or a rendered turntable if that looks better) | – |
Still reused (already made, nothing to do): `opening`, `a1`, `a2`, `b2`. The globe stays code-built.

## Order Claude runs
1. Check the Blender connection and the repo.
2. Site config PR: the new clip ids, the new "Arrival" chapter, all placeholder labels removed.
3. Asset library (people and outfits, crates, ice, trucks, boat, net, fish, containers, cranes, ship, tugs, materials).
4. The catch → the port → the plant chain (truck-reverse, intake, processing, freezer) → return, ponds, harvest → Products fish.
5. For every scene: a small **preview** to you first, then the full render, encoding and checks, one PR each.
6. A final speed and weight check of the whole site.
Details: `3_DAY_SCHEDULE.md`.

## What Tarun does (that's all)
1. **Keep Blender open with the MCP add-on connected** (N panel → BlenderMCP → Connect), and keep the Mac plugged in, especially overnight while it renders.
2. **Approve each preview** in its PR (reply "ok" or say what's wrong). Nothing gets fully rendered until you approve it.
3. **Merge** the PRs in the order Claude lists. Only you merge.

## Files
| File | What |
|---|---|
| `CLAUDE_BLENDER_PROMPT.md` | The master prompt: rules, issues, per-scene loop, order of work, definition of done |
| `SCENES.md` | Every scene: site chapter and clip id, frames, shot list with camera moves, object inventory, animation, lighting, acceptance checklist, commands |
| `ASSET_LIBRARY.md` | Every model to build, budgets, where each is reused, the strict Products standard |
| `RENDER_PIPELINE.md` | Render settings, preview/full commands, encoding, budgets, honest time estimates |
| `3_DAY_SCHEDULE.md` | Day-by-day plan for Claude and Tarun |
| `GIT_WORKFLOW.md` | Branch per issue, micro commits, one PR each, never push or merge to main, only Tarun merges |
| `scripts/` | `scenes.sh` (scene registry), `render-scene.sh`, `frames-to-master.sh`, `boundary-check.sh`, `check-clip.sh`, `path-weight.sh`, `encode-clips.sh`, `make-posters.sh`, `optimize-glb.sh`, `fetch-sources.sh` |
| `blender/` | `render_settings.py` (standard render settings), `boundary_camera.py` (shared frames between scenes) |
| `templates/` | Issue, scene-issue and PR templates |
| `reference/` | `STORY.md`, `CONTENT.md` (the only source of site copy), `BANNED_CLAIMS.md`, `ASSETS_SPEC.md`, `catch-reference.png` (look only; its caption text must never be used), `feedback/` (Tarun's rejected screens) |
| `companion/CLAUDE_REDESIGN_PROMPT.md` | Code-side fixes: stacked headlines, stutter (late clip loading), placeholder tags, dashboard chrome, opening, fonts, caching, real-scroll testing. Scene content comes from this pack; engine, pacing and design come from this prompt. |
| `companion/FIX_LIST.md`, `companion/evidence/` | The full audit of the current site with file:line causes, and screenshot proof. |
