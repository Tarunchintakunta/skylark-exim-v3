# 3_DAY_SCHEDULE.md: Blender scenes

Approvals gate the full renders, so Tarun checks previews **at least morning, afternoon and evening** each day. Full renders run in the evening/overnight with the Mac plugged in and awake (`caffeinate` is built into `render-scene.sh`). Times are estimates; the honest risk is in RENDER_PIPELINE.md §5.

## Day 1: foundations, the catch, the port
| Block | Claude | Tarun |
|---|---|---|
| Morning | Blender connection check, headless test frame, MCP extras check, repo state; **issue 1** `chore: chapter config for Blender scenes` (pack into repo, new chapters/ids, Arrival chapter, remove placeholder labels, stand-in logic); create issues 2–17 | Open Blender with the MCP add-on connected; keep it open all three days |
| Midday | **Issue 2** asset library: people + outfits + poses, crates/ice/trolleys, reefer truck, fishing vessel + net bag + fish proxies, materials, HDRIs | – |
| Afternoon | **o-catch** (`o-catch-a` + `o-catch-b`) build + sims + preview → draft PR | Approve or send notes on the o-catch preview |
| Evening | Library: containers, STS cranes, RTG, straddle carrier, ship, tug, quay kit → **port** (`x-cranes` + `x-ship`) build + preview → draft PRs | Approve or send notes on the port preview |
| Night | Full renders of approved o-catch and/or port | Leave the Mac plugged in |

## Day 2: the plant chain
| Block | Claude | Tarun |
|---|---|---|
| Morning | Encode + PR o-catch / port finals (if rendered); plant sets in the library | Review final o-catch / port PRs |
| Midday | **truck-reverse** build + preview (reverse rear-first, cab outside, driver outside, doors into the plant) | Approve truck-reverse |
| Afternoon | **p-intake** + **p-proc** (mid-shift from frame 1) builds, boundaries, previews | Approve both |
| Evening | **p-freeze** build + preview; Products fish look-dev starts (sources, sculpt/scan, ice bed) | Approve p-freeze |
| Night | Full renders of the approved plant chain | Mac plugged in |

## Day 3: return, ponds, harvest, Products, audit
| Block | Claude | Tarun |
|---|---|---|
| Morning | Encode + PR plant finals, boundary checks; **o-return** build + preview | Review plant PRs; approve o-return |
| Midday | **p-ponds** + **p-harvest** builds + previews | Approve both |
| Afternoon | **tuna, swordfish, shrimp** photoreal stills on the ice bed → GLB (≤ 500 KB) or turntable fallback; **products stage** + species list fix; full renders of o-return/p-ponds/p-harvest | Approve the fish renders |
| Evening | Encode remaining finals; **issue 17** perf audit (path weights, fps, long tasks, Lighthouse); report | Review and merge in the order Claude lists |
If the day runs out, the priority list in CLAUDE_BLENDER_PROMPT.md §5 decides what ships; unfinished scenes keep their approved preview as a stand-in and roll to Day 4.
