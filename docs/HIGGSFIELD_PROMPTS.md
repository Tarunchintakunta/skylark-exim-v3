# HIGGSFIELD_PROMPTS.md: the 5 new / regenerated clips (Tarun)

**Higgsfield clips (5):** `o-catch`, `p-ponds`, `p-intake`, `p-proc`, `p-freeze`. The port and ship shots (`x-cranes`, `x-ship`) are **not** Higgsfield any more: Claude builds and renders them in Blender (BLENDER_GLB_SPEC.md §3). Their old prompts are kept in the appendix only for the case where the Blender connector can't be used at all.

**Model and settings (same as the existing chain, from `manifest/chain.json`):** Seedance 2.0 (`seedance_2_0`), 16:9, mode `std`, `generate_audio: false`. Draft at 720p, master at 1080p.
**Credit rates (from chain.json ledger, not estimates):** 720p 8 s = **36** · 1080p 8 s = **72** · 1080p 12 s = **108** · still image (cinematic_studio_2_5) ≈ 2 (ledger: 3 stills = 6). Last recorded balance in chain.json: **160 credits**, so top up before Day 1.
**Anchor files** are in github.com/Tarunchintakunta/skylark → `assets/anchors/` and `assets/stills/`. `scripts/fetch-sources.sh` copies them to `assets-src/anchors/` and also extracts `a3_first_1080.png`.
**Naming:** save each accepted 1080p master as `assets-src/video/<id>.mp4` (ids below). Claude's scripts pick them up by name.

Workflow per clip: 720p draft (36) → check the 5 points in "Accept if" → 1080p master with the same prompt and anchors → if the master has an artefact, re-roll the master only.

Shared style suffix (append to every prompt):
> Anamorphic widescreen, shallow depth of field, 35mm film grain, natural motivated lighting, documentary realism, muted cold grade, no text, no logos.

Shared avoid clause (append to every prompt):
> Avoid: cartoon, CGI plastic look, oversaturated colours, orange-teal grade, lens flare, text, watermark, distorted hands, extra fingers, morphing objects, melting geometry, deformed animals, jitter, sudden cuts.

---

## 1. `o-catch`: the real catch (NEW, must-have)
- Chain: `a2` → **o-catch** → `a3`
- `start_image`: `assets/anchors/a2_end_1080_v2.png` (open sea behind the stern)
- `end_image`: `a3_first_1080.png` (frame 1 of `assets/video/1080/a3.mp4`; yellowfin in the ice hold). In the cloned skylark repo: `ffmpeg -i assets/video/1080/a3.mp4 -frames:v 1 a3_first_1080.png` (Claude's `scripts/fetch-sources.sh` makes the same file in `assets-src/anchors/`)
- `image_references`: `assets/stills/hero.png` only if the vessel drifts off-model
- Duration 8 s (12 s reads better if credits allow) · 1080p · Camera: swing from the wake forward along the deck to the side rail, then rise and lock overhead on the ice hold
- Cost: draft 36 + master 72 (or 108 for 12 s)

**Prompt**
> Broad daylight on the open sea, deep blue swell under full sun. The net is lifted clear of the sea within the first two seconds. The camera swings from the wake at the stern forward along the wet deck of the steel fishing trawler to the side rail, where Indian fishermen in bright workwear haul a heavy fishing net up out of the water with a winch and rope: the net breaks the surface streaming seawater, bulging with silver fish, swordfish bills and fat yellowfin tuna inside it, spray bursting into sunlit droplets. The crew swing the dripping net inboard over the rail and release it, and the catch pours out onto the deck in a glittering silver rush, fish sliding across the wet steel. The crew move in with gloved hands and lift the fish toward an open ice hold filled with crushed ice. The camera ends locked high above the open ice hold looking down, a whole yellowfin tuna lying on crushed white ice. One continuous camera move, no cuts. Urgent, exhilarating, professional, no gore. + style suffix
> + avoid clause + "fish already lying on deck at the start, net staying underwater, fish merging together."

**Accept if:** net visibly leaves the water · water streams off it · catch lands on deck (not teleported into the hold) · hands have 5 fingers · last frame matches a3 frame 1.
**Re-roll tips:** if the net never surfaces, move "The net is lifted clear of the sea within the first two seconds" to the very start (already there) and drop the end_image for one try, then cross-fade into `a3` over 6 frames in code. If fish morph, remove "swordfish bills" (tuna only).

## 2. `p-ponds`: bright aerial ponds, vehicles one direction (REGEN of `b1`)
- Chain: `opening` → **p-ponds** → (6-frame cross-fade) → `b2`
- `start_image`: `assets/anchors/anchor1_1080.png` (end of `opening`: harbour left, pond bunds right)
- `end_image`: none (b1_end is pre-dawn; forcing it would darken the clip). The 6-frame cross-fade into `b2` is done in code.
- 8 s · 1080p · Camera: turn right toward the pond bunds, rise to a high aerial, glide forward over the grid, slowly descend toward one pond edge
- Cost: 36 + 72

**Prompt**
> The camera turns right away from the harbour toward the coastal aquaculture ponds as dawn breaks into a clear bright morning, then rises into a high aerial glide over a vast ordered grid of rectangular shrimp ponds separated by straight earthen bunds and access roads, turquoise water reflecting a pale blue sky, paddlewheel aerators throwing arcs of white water in every pond, a small farm shed at one corner. Two small pickup trucks and a motorbike drive along the same bund road, all travelling in the same direction, one behind the other, at a steady slow pace, like one harvest pickup route. Green fields and coconut palms at the edge of the farm. The camera glides forward and descends steadily toward the edge of one pond. One continuous move, no cuts. + style suffix
> + avoid clause + "vehicles driving toward each other, vehicles on the water, vehicles reversing, traffic in opposite directions, night, fog, dark pre-dawn sky."

**Accept if:** bright daylight · every vehicle moves the same way for the whole clip · aerators spin · no vehicle crosses water · no cut.
**Re-roll tips:** if vehicles still go opposite ways, reduce to "one pickup truck drives along the bund road" (a single vehicle can't contradict itself).

## 3. `p-intake`: truck backed in, rear doors open into the plant, driver outside (REGEN)
- Chain: `a4` / `b3` (both end on `anchor2`) → **p-intake** → `p-proc`
- `start_image`: `assets/stills/anchor2.png` (truck backed up to the lit bay)
- `end_image`: none (its last frame becomes `p-proc`'s start_image)
- 8 s · 1080p · Camera: slow push from the yard toward the open rear of the truck, then follow a crate through the doorway into the intake hall
- Cost: 36 + 72

**Prompt**
> Early morning at a seafood processing plant loading dock. A white refrigerated truck is already reversed rear-first against the loading bay, its cab and front facing away from the building out into the yard. The truck's rear doors swing open into the brightly lit building. The driver, a man in a reflective vest, steps down from the cab and stands outside beside it in the yard. Inside the dock, workers in white coats, face masks, hair caps and blue gloves unload stacked crates of iced seafood from the back of the truck onto stainless steel trolleys. The camera pushes slowly toward the open rear of the truck and follows one crate on a trolley through the doorway into a clean white intake hall with stainless steel tables and bright cold light. One continuous move, no cuts. + style suffix
> + avoid clause + "truck driving into the building, truck nose-first toward the door, cab inside the building, driver inside the warehouse, workers without masks, bare hands."

**Accept if:** cab never enters the building · rear doors open toward the plant · driver outside · every visible worker masked, capped, gloved · last frame is clean and readable (it is p-proc's start).
**Re-roll tips:** if the truck moves, add "the truck is parked and does not move". If masks are missing, add "every worker's mouth and nose are covered by a white surgical face mask".
**Fallback:** p-intake stays in Higgsfield because of the people. If it still fails after 2 re-rolls, tell Claude "use Blender for intake": Claude renders the truck-backed-to-dock establishing shot itself (rear-first, cab away from the building, rear doors open, no people; BLENDER_GLB_SPEC.md §6), and p-proc is then generated without a start_image.

## 4. `p-proc`: wash, grade, process, already mid-shift, full PPE (REGEN of `t2` / `t2s`)
- Chain: `p-intake` → **p-proc** → `p-freeze`
- `start_image`: last frame of your accepted `p-intake` (`ffmpeg -sseof -0.1 -i assets-src/video/p-intake.mp4 -update 1 -frames:v 1 assets-src/anchors/p-intake_end.png`)
- `end_image`: `assets/anchors/t2_end_1080.png` (white lab bench, microscope, analyser, certificate)
- 12 s · 1080p · Camera: steady dolly forward down the hall, slight left drift, turn through a doorway into the lab
- Cost: 36 (8 s draft) + 108

**Prompt**
> The processing hall is already in full mid-shift from the very first frame: shrimp and fish are already lying on the running conveyors and stainless steel tables, nothing is being newly delivered. The camera dollies steadily forward: clean treated water sprays over shrimp on a stainless washing line and drains away clear; the product moves into parallel grading channels sorted by size; long tables where rows of Indian workers peel and devein shrimp by hand. Every single worker wears a white coat, a white face mask covering mouth and nose, a white hair cap and blue nitrile gloves. Bright clean cold white light, polished steel, wet floor. The camera turns left through a doorway into a quiet clean laboratory and settles on a white lab bench. One continuous move, no cuts. + style suffix
> + avoid clause + "product sliding in from the top of the frame, a new batch arriving, empty conveyors at the start, workers without face masks, bare hands, uncovered hair, red meat, blood."

**Accept if:** product present on frame 1 · zero unmasked faces (scrub frame by frame at 2 fps) · gloves on every hand · ends on the lab bench.
**Re-roll tips:** if masks fail, keep workers at mid distance and add "workers seen from the side and behind"; if product still slides in, add "the conveyor is already full and moves slowly to the right".

## 5. `p-freeze`: lab → clean freezer → packing → cold store (REGEN of `t3`, frost toned down)
- Chain: `p-proc` → **p-freeze** → (cut to documentation interlude)
- `start_image`: `assets/anchors/t2_end_1080.png` (same lab bench p-proc ends on)
- `end_image`: `assets/anchors/t3_end_1080.png` (cold-store aisle, white cartons on blue/orange racking)
- 12 s · 1080p · Camera: slow pull back from the lab bench, through a door into the freezer room, past the packing table, out into the cold-store aisle
- Cost: 36 (8 s draft) + 108. If 12 s feels rushed, split into `p-freeze` (lab → freezer, 8 s) + `p-pack` (packing → cold store, 8 s) = 144 instead of 108.

**Prompt**
> A clean seafood plant. The camera pulls back from a white laboratory bench and moves through a door into a modern, realistic freezer room: stainless steel plate freezers and a spiral IQF freezer with closed doors, only a light frost on the door edges and a little cold mist near the floor, everything else clean, bright and dry. A worker in white coat, face mask, hair cap and blue gloves lifts a tray of individually frozen shrimp with a thin glossy ice glaze. The camera continues to a packing table where gloved workers place frozen product into plain white export cartons and vacuum packs and press a plain white label onto each carton. The camera glides on into a cold-store aisle of white cartons stacked on pallets on blue and orange racking. One continuous move, no cuts. + style suffix
> + avoid clause + "heavy frost, ice crystals growing on walls, frost trees, snow, icicles, blizzard, thick fog, abandoned rooms, readable text on labels, brand names."

**Accept if:** frost is light (doors/edges only) · room looks like a working plant, not an ice cave · masks and gloves · labels are blank or illegible · last frame matches t3_end.

---

## Credit plan (5 clips)
| Clip | Draft 720p | Master 1080p | Total |
|---|---|---|---|
| o-catch | 36 | 72 (108 if 12 s) | 108 (144) |
| p-ponds | 36 | 72 | 108 |
| p-intake | 36 | 72 | 108 |
| p-proc | 36 | 108 (12 s) | 144 |
| p-freeze | 36 | 108 (12 s) | 144 |
| **Total, one take each** | 180 | 432 (468 with 12 s catch) | **612** (648 with 12 s catch) |

Re-roll allowance: one full extra take (draft + master) of the two riskiest clips, o-catch (108–144) and p-proc (144) = up to 288. **Budget about 900–950 credits** (648 + 288 = 936 worst case). With the last ledger balance of 160, top up by about 750–800. Skipping drafts saves 180 but every failed master then costs 72–108. `x-cranes` and `x-ship` cost **0 credits** (Blender renders).

---

## Appendix (only if the Blender connector is unavailable): old Higgsfield prompts for the port and ship
Use these only if Claude reports that Blender can't be used at all and Tarun decides to generate the two shots instead. Extra cost: 108 + 108 = 216 credits (+2 for the optional still).

### A1. `x-cranes`: 2–3 ship-to-shore cranes loading reefer containers (NEW)
- Chain: documentation interlude (cut) → **x-cranes** → `x-ship`
- `start_image`: none (text-to-video; a section cut is intended here). Optional: generate a still first (≈2 credits) with the first sentence of the prompt and use it as start_image for more control.
- `end_image`: none (its last frame becomes `x-ship`'s start_image)
- 8 s · 1080p · Camera: low on the quay, then crane up following one container
- Cost: 36 + 72 (+2 optional still)

**Prompt**
> A busy container port in clear bright morning light. Three tall ship-to-shore gantry cranes stand in a row along the quay working one large container ship that is already stacked with containers. A white refrigerated reefer container, its refrigeration unit on one end, waits on a truck chassis on the quay. The nearest crane's spreader locks onto it and lifts it smoothly into the air; the camera rises with the container as it travels out over the ship and is lowered precisely onto the top of a stack, while the other two cranes lift and lower containers further along the ship. Port workers in hard hats and reflective vests on the quay. The camera keeps rising at the end until it looks down over the whole loaded ship from high above. One continuous move, no cuts. + style suffix
> + avoid clause + "containers floating without cables, cranes bending, ship moving during loading, collisions, dusk, night, text or brand names on containers."

**Accept if:** at least 2 cranes visible working · container hangs from the spreader on cables the whole time · lands on the ship · final frame is a high downward view (feeds x-ship).

### A2. `x-ship`: top-down aerial of the loaded ship on deep blue water (NEW, Mont-Fort style)
- Chain: `x-cranes` → **x-ship** → bright globe (cross-fade in code)
- `start_image`: last frame of your accepted `x-cranes` (`ffmpeg -sseof -0.1 -i assets-src/video/x-cranes.mp4 -update 1 -frames:v 1 assets-src/anchors/x-cranes_end.png`)
- `end_image`: none
- 8 s · 1080p · Camera: straight-down (90°) aerial tracking the ship, then a slow vertical rise
- Cost: 36 + 72

**Prompt**
> A straight-down top-down aerial view, camera pointing directly at the sea. A large container ship fully loaded with colourful stacked containers, including rows of white reefer containers, sails out across calm deep blue open ocean in bright midday sun, a long clean white wake trailing behind it. The camera tracks with the ship, then rises slowly and steadily straight up so the ship becomes smaller in a vast field of deep blue water with gentle sun glints. One continuous move, no cuts. + style suffix (use "clean natural grade" instead of "muted cold grade" here; the hand-off to the bright globe needs true blue)
> + avoid clause + "tilted horizon, land, clouds covering the ship, ship changing shape, containers morphing, multiple ships, dusk."

**Accept if:** truly top-down · water is deep blue (not grey) · final 2 s are nearly uniform blue (clean cross-fade to the globe).
