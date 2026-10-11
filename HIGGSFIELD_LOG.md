# HIGGSFIELD_LOG

Media pass per docs/HIGGSFIELD.md + docs/HIGGSFIELD_STORYBOARD.md (issue #175). Masters in `masters/<shot>/` (gitignored, never committed).
Start balance 1910.75 credits (max plan). Credit guard: stop all generation at 1624 credits spent (balance <= 286). Spend is tracked from `balance` calls only.

## 2026-10-10: paused before the first generation
The lead halted the pass on Tarun's order: Higgsfield is paused until the Blender finals are done. No job was submitted. Credits spent: 0. Balance still 1910.75 (max plan). Resume at A2 catch.

## 2026-10-11: resumed (Higgsfield producer)

### Decisions
- **Video model: `minimax_h3` 2K** (10 credits / 5 s). Comparison on HS03 (same start frame, same prompt): minimax_h3 returned 2560x1440 H.264 24 fps, 124 frames, people and rope detail sharp in every sampled frame; `seedance_2_5` 1080p `bitrate_mode: high` (60 credits) returned 1920x1080 HEVC 10-bit 24 fps, 121 frames, but drifted into heavy defocus by 50-100 % and lost face/hand detail. Picked minimax_h3 by contact sheet. Both outputs are 24 fps (no resample needed). minimax output carries an AAC track; it is dropped at encode (`-an`).
- **People start frames: `gpt_image_2_5` quality max, 4k** (15 credits). Comparison on HS03 vs `nano_banana_pro` 4k (4 credits; the job reported model `nano_banana_2`): nano copied the CG poses (lunging figures, hands not on the rope); gpt_image_2_5 gave natural hauling poses with gloved hands on the rope and real faces. Output 3840x2160.
- **Shots without people:** take 1 animated straight from the Blender still (HS01, HS06, HS19, HS20) all read as CG (flat block buildings, toy water/ponds, plastic crane paint). Take 2 for those uses a gpt_image_2_5 realism pass that keeps the Blender composition (the "change the start still" step of HIGGSFIELD.md §3.4).
- **Content rule (coordinator, 2026-10-11):** a closed ring of floats on the sea implies a gear on the never-write list. Sea shots must show the net hauled over the side, a straight float line from the hull or a heaped net; every sea prompt carries "no circular float ring, no encircling net"; no gear is named in prompts. HS03 take 1 PASS revoked for this.
- Reference grading: real photos are viewed in the browser only (nothing downloaded, uploaded or committed). Bing image results for Visakhapatnam crews hauling nets: crews mostly in T-shirts, lungis or shorts, often barefoot, many hands on deck; PVC oilskins mostly appear in non-Indian trawler photos. Our catch frames keep the oilskins from the scene reference; harbour/pond frames use lungis, vests, saris, sandals, which matches the real photos.

### Takes
| Shot | Take | Job id | Credits | Verdict | Notes |
|---|---|---|---|---|---|
| HS03 | img nano | 81513494 | 4 | reject | CG poses copied, hands off the rope |
| HS03 | img gpt | eab48ca9 | 15 | PASS (image) then revoked | real people; closed float ring on the sea (content rule) |
| HS03 | 1 seedance (cmp) | f74114a3 | 60 | FAIL | heavy defocus drift, soft faces/hands |
| HS03 | 1 minimax | 2aebb75e | 10 | FAIL (revoked) | real people, steady; closed float ring |
| HS04 | img gpt | 9df94576 | 15 | PASS (image) | six crew sorting/icing, ice in crates, tuna + mackerel only |
| HS04 | 1 | be52f262 | 10 | FAIL | camera rolls and swings, wake appears and jumps (SSIM f2f min 0.78) |
| HS01 | 1 (Blender still) | ed45a279 | 10 | FAIL | town reads as CG blocks |
| HS06 | 1 (Blender still) | 0103c86c | 10 | FAIL | toy ponds/aerators |
| HS19 | 1 (Blender still) | 0ebd8083 | 10 | FAIL | CG crane/quay; panel with marks at the end |
| HS20 | 1 (Blender still) | 00c684d5 | 10 | FAIL | CG boom and ship |
| HS02 | img gpt | 7929cecc | 15 | PASS (image) | weathered boat, two crew in lungis, mooring buoys only |
| HS05 | img gpt | 4b36f2c3 | 15 | PASS (image) | porters, trolleys, woman in sari; no text |
| HS07 | img gpt | 2375756a | 15 | PASS (image) | drag net at sunrise, plain truck |
| HS08 | img gpt | 844b486b | 15 | PASS (image) | crates of shrimp on ice, nitrile gloves |

### Balance
| When | Balance | Spent |
|---|---|---|
| start | 1910.75 | 0 |
| after HS03 images | 1891.75 | 19 |
| after first 3 batches | 1656.75 | 254 |
| after realism-pass images submitted | 1571.75 | 339 |
