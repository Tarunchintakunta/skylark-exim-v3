# SCENES.md: every story scene, built end to end in Blender by Claude

Everything here is **rendered video** (EEVEE, 1920×1080, 24 fps), encoded with `scripts/encode-clips.sh` exactly like the old clips, so the site's ScrubVideo, budgets and smoothness rules are unchanged. Frame ranges, render folders and joins live in `scripts/scenes.sh`; this file and that script must always agree.

Ground rules for every scene:
- **No text, logos, brand names, numbers or readable signs anywhere** (boats, hulls, containers, trucks, plates, cartons, labels, walls, crates). Labels and tags are blank.
- **Daylight and bright.** Exteriors: clear morning to midday sun, blue sky with real clouds (HDRI or Sky Texture + cloud cards). Interiors: clean, evenly lit, cool white. Nothing dark, nothing grey and flat, no heavy fog, no orange-teal grade.
- **Busy, not empty.** Each scene has an object inventory ("density list") below. The inventory is a minimum: if a frame still has big empty areas, add more set dressing from the library.
- **People** are mid-distance or in soft focus, natural poses, never a close-up face. Plant staff always wear **face mask, gloves, hair cap**, and apron or white coat, plus boots.
- **One continuous camera per clip. No cuts inside a clip.** Moves are slow and eased (Bezier), motion blur on.
- **Vehicles drive forward in one direction only**, except the deliberate reverse in `truck-reverse`. Wheels rotate from distance travelled (forward, or backward only while reversing).
- Nothing here is site copy. Sizes are modelling guidance only and never appear on the site.

---

## Scene → site map (what replaces what)

| Order | Site chapter (STORY.md) | Clip id (site expects) | Blend | Frames | Length | Replaces | Join into next |
|---|---|---|---|---|---|---|---|
| Ocean 1 | O1 Setting out | `a1` + `a2` (REUSE, unchanged) | – | – | 16 s | – | cross-fade into `o-catch-a` |
| Ocean 2 | O2 The catch | **`o-catch-a`** | `o-catch.blend` | 1–192 | 8 s | the planned Higgsfield `o-catch` | **shared frame 192** |
| Ocean 3 | O3 On ice | **`o-catch-b`** | `o-catch.blend` | 192–383 | 8 s | `a3` | cross-fade into `o-return` |
| Ocean 4 | O4 Back to Vizag | **`o-return`** | `o-return.blend` | 1–288 | 12 s | first part of `a4` | cross-fade into `truck-reverse` |
| Pond 1 | P1 The ponds | **`p-ponds`** | `p-ponds.blend` | 1–192 | 8 s | the planned Higgsfield `p-ponds` (and `b1`) | cross-fade into `b2` |
| Pond 2 | P2 Traceable | `b2` (REUSE, unchanged) | – | – | 8 s | – | cross-fade into `p-harvest` |
| Pond 3 | P3 Harvest | **`p-harvest`** | `p-harvest.blend` | 1–288 | 12 s | `b3` | cross-fade into `truck-reverse` |
| Shared 4 | **NEW chapter "Arrival"** (both paths converge here) | **`truck-reverse`** | `truck-reverse.blend` | 1–288 | 12 s | the reversing tails of `a4`/`b3` and `anchor2` | **shared frame** |
| Shared 5 | 5 Intake | **`p-intake`** | `p-intake.blend` | 1–192 | 8 s | Higgsfield `p-intake` / `t1` | **shared frame** |
| Shared 6 | 6 Wash · grade · process | **`p-proc`** | `p-proc.blend` | 1–288 | 12 s | Higgsfield `p-proc` / `t2` / `t2s` | **shared frame** |
| Shared 7 | 7 Lab · freeze · pack · cold store | **`p-freeze`** | `p-freeze.blend` | 1–288 | 12 s | Higgsfield `p-freeze` / `t3` | DOM documentation interlude over its last frame |
| Shared 9 | 9 The port | **`x-cranes`** | `port.blend` | 1–288 | 12 s (was 8 s) | the empty toy port render (PR #72) | **shared frame 288** |
| Shared 10 | 10 At sea | **`x-ship`** | `port.blend` | 288–479 | 8 s | – | cross-fade into the code-built globe |
| Products | 12 Products | `tuna.glb` `swordfish.glb` `shrimp.glb` `carton.glb` `ice-tray.glb` (or turntables `prod-tuna` `prod-swordfish` `prod-shrimp`) | `products.blend` / `prod-*.blend` | 1–120 (turntables) | 5 s | the cartoon fish in PRs #73–#75 | – |

Unchanged: loader, start screen (`opening`, REUSE), documentation interlude (DOM), the globe (code-built), all business sections.

**Higgsfield is no longer needed for the story.** The five planned Higgsfield clips (`o-catch`, `p-ponds`, `p-intake`, `p-proc`, `p-freeze`) are all replaced by Blender renders; Tarun does not need to generate or top up anything. Reused clips still in the story: `opening`, `a1`, `a2`, `b2`. Now **optional fallbacks only** (kept in `assets-src/video/`, not on the default chain): `a3`, `a4`, `b3`. Never use the rejected `b1`, `t1`, `t2`, `t2s`, `t3`, `t4`.

### Site config changes this needs (one PR, `chore: chapter config for Blender scenes`, before any scene PR)
1. Ocean: O2 source `o-catch-a` (140 vh, copy enters at 55%), O3 source `o-catch-b` (140 vh), O4 source `o-return` (160 vh).
2. Pond: P1 `p-ponds` (120 vh), P3 `p-harvest` (160 vh).
3. **New shared chapter "Arrival"** between the paths and Intake, source `truck-reverse`, 160 vh. Both paths join here (Ocean after O4, Pond after P3).
4. x-cranes chapter 140 → **180 vh** (clip is now 12 s); x-ship 120 vh.
5. Joins exactly as the table: `joinNext: 'shared'` for o-catch-a→o-catch-b, truck-reverse→p-intake, p-intake→p-proc, p-proc→p-freeze, x-cranes→x-ship; `'crossfade'` for the rest.
6. Scroll lengths above follow STORY.md. If the companion `FIX_LIST.md` pacing rule (scroll ≈ clip length × 25 vh per second) is adopted in the redesign, use that instead; pacing is the redesign's call, the clip content is this file's.
7. Until a scene's final clip is merged, its chapter uses that scene's **encoded 960×540 preview** as a stand-in; before the preview exists, the poster of the nearest existing clip. **No "placeholder" labels or tags are ever rendered on the page** (remove the current "placeholder · awaiting …" overlay everywhere).

### Copy (only CONTENT.md lines; headlines are editorial and claim nothing)
| Chapter | Headline | Body (from CONTENT.md) | HUD |
|---|---|---|---|
| O2 (`o-catch-a`) | Out of the water. | "Initial quality checks (size, freshness, health) are done before acceptance." | `01 PROCUREMENT` · `ON DECK` |
| O3 (`o-catch-b`) | On ice. | "Premium raw fresh, chilled and frozen seafood." + chips: Indian Mackerel · Tuna · Swordfish · Cuttlefish · Squid · Leatherjacket · Ribbon Fish · Seer Fish | `01 PROCUREMENT` · `CHILLED` |
| O4 (`o-return`) | Home under a chilled seal. | "With a fully integrated value chain, we ensure complete control over quality, consistency, and sustainability at every stage, from sourcing to delivery." (About text, dash grammar-cleaned) | `01 PROCUREMENT` · `IN TRANSIT · CHILLED` |
| P1 (`p-ponds`) | Partner farms on the Andhra coast. | unchanged (STORY.md P1) | unchanged |
| P3 (`p-harvest`) | Harvested into ice. | unchanged (STORY.md P3) + shrimp chips | `01 PROCUREMENT` · `IN TRANSIT · CHILLED` |
| Arrival (`truck-reverse`) | Backed to the bay. | "Transported under chilled conditions to the processing plant." | `02 RECEIVING & WASHING` · `ARRIVED · CHILLED` |
| 5, 6, 7, 9, 10 | unchanged (STORY.md) | unchanged | unchanged |

The catch reference image (`reference/catch-reference.png`) has caption text baked in. **Never copy any of its text** (its eyebrow line names a fishing gear, which is a banned claim). Copy never names a fishing gear or method.

---

## Boundaries (how chained clips share a frame)
- **Same .blend, one timeline** (o-catch-a/b, x-cranes/x-ship): rendered once; the boundary PNG is literally the same file, used as the last frame of A and the first of B.
- **Different .blends** (truck-reverse → p-intake → p-proc → p-freeze): all four link the same plant set, people and props from `asset-library.blend` with identical object names. Scene A runs `write_boundary()` from `blender/boundary_camera.py` at its last frame; scene B runs `read_boundary()` at frame 1 (camera, lens, DOF, the hero objects listed per scene). Same world/HDRI, sun and exposure. Then `scripts/boundary-check.sh` must print OK (SSIM ≥ 0.99 on the PNGs). People in the boundary frame hold the same pose for the 6 frames around the cut (pose held, then continue) so tiny timing differences can't show.
- **Cross-fades** (different places or a reused clip on one side): compose the two sides alike (same truck model and colour, similar camera height and direction) so the 6-frame cross-fade reads as continuous.

---

## 1–2. `o-catch-a` + `o-catch-b`: the catch (Tarun's must-have) · `o-catch.blend`, frames 1–383
**Reference: `reference/catch-reference.png`.** Match it: white steel fishing vessel with blue trim, wheelhouse with windows and railings, a hydraulic **boom (derrick)** and **winch drum** with coiled rope, steel rail, wet deck; **6–7 fishermen in orange and yellow oilskins** (bib trousers and jackets), caps, rubber gloves and boots; a **huge dripping net bag full of silver fish with several tuna**, yellow floats along the net, water pouring off; bright daylight on a deep blue sea with whitecaps.
**Purpose:** show the fish coming **out of the water**, not already on deck. Then sorted into iced crates and into the hold.
**Species shown** (real list only): tuna (yellowfin look) and silver schooling fish shaped like Indian mackerel; a few seer fish and ribbon fish in the crates. Nothing else (no species outside CONTENT.md).

### Shot list (24 fps, one continuous camera; boundary at 192)
| Frames | Action | Camera |
|---|---|---|
| 1–40 | **Net in the sea**: a ring of yellow floats on the water beside the hull, the net line running from the boom block down into the water, crew lined up at the rail. Water around the floats boils with fish (splashes, silver flashes just under the surface) | wide 3/4 from the deck's far side, ~5 m high, sea and floats filling the right half; slow push |
| 40–100 | Winch drum turns, rope tightens and drips; the boom takes the weight; the **net bag breaks the surface**, water streaming and pouring off, fish packed inside thrashing, foam and splash particles | camera drifts toward the rail, low angle up at the rising bag (the reference composition) |
| 100–150 | Bag hangs on the boom and **swings in over the rail** (slow pendulum, ≤ 8°), two crew guide it with gloved hands, others step back, water sheets onto the deck | slight lateral track following the swing |
| 150–192 | Bag lowered to the deck, a crewman pulls the release line, **the bottom opens and the fish spill onto the deck** in a silver wave (rigid-body sim, tuna on top). **f192 = boundary**: the pile has landed, crew stepping in | settles at ~2.5 m high, 3/4 on the pile |
| 192–260 | Crew kneel and **sort by hand into plastic crates**: tuna to one row, small silver fish to others; a man shovels flake ice from an ice box over each filled crate | slow arc around the pile, soft DOF (f/4) on the hands, faces never close |
| 260–330 | Filled iced crates are passed hand to hand and **lowered through the open hatch into the hold** (one on a rope hoist) | camera rises and tilts down toward the hatch |
| 330–383 | Overhead into the hold: rows of crates, fish on crushed ice, ice being topped up; last frame is a calm, bright overhead of iced crates (O3 chips sit over it) | top-down, very slow descent |

### Density list (minimum)
Vessel: wheelhouse with windows, mast with lights and antenna, railings, boom with block and hydraulic ram, winch drum with rope coils, net pile and spare floats, life rings (blank), fenders, tyres along the hull, hatch with coaming, ice box, hoses, buckets, baskets, plastic crates (blue/red/white, stacked and loose), shovels, gloves on hooks, water running off the deck through scuppers. Crew: 6–7 (oilskins orange/yellow, caps, gloves, boots), varied builds and poses. Sea: Ocean modifier with whitecaps and foam, splashes and droplets near the net, 1–2 distant fishing boats on the horizon, gulls (4–8, simple flapping cycle). Sky: daylight HDRI with clouds.
### Animation beats
Net + fish: the net bag is a cloth-sim or shape-keyed mesh hung from the boom hook; fish inside are geometry-node instances (mixed silver fish + 4–6 tuna) with jitter; release = rigid-body sim of 150–300 low-poly fish proxies, **baked** before saving. Water off the net: particle drips + a sheet-of-water mesh with transparency. Crew: pose-to-pose actions from the library (pull, guide, kneel-sort, shovel, pass crate).
### Lighting
Sun 40–55° elevation, warm-neutral; sky HDRI; specular glints on wet oilskins, fish and deck; AO; subtle atmospheric perspective on the horizon only.
### Acceptance (tick in the PR)
- [ ] First frames show **the net in the water with floats**; fish come **from the water**. The deck is empty of fish before f150.
- [ ] Net breaks the surface dripping, swings over the rail, is released onto the deck; then sorted into **iced crates** and **into the hold**.
- [ ] Matches the reference: oilskins, caps, gloves, white/blue vessel, boom and winch, bright blue sea.
- [ ] Only species from CONTENT.md; no recognisable gear type named or emphasised; no text from the reference image anywhere.
- [ ] f192 identical in both clips; `boundary-check.sh` OK.
- [ ] Faces never close-up; hands and gloves fine.
- [ ] Brightness passes `check-clip.sh` (floor 85).
### Render + encode
```bash
scripts/render-scene.sh o-catch preview          # -> docs/renders/o-catch-preview.mp4 (approval)
scripts/render-scene.sh o-catch full             # after Tarun approves
scripts/frames-to-master.sh o-catch-a o-catch-b && scripts/boundary-check.sh o-catch-a o-catch-b
scripts/encode-clips.sh o-catch-a o-catch-b && scripts/make-posters.sh o-catch-a o-catch-b && scripts/check-clip.sh o-catch-a o-catch-b
```
Outputs: `public/media/o-catch-a_{1280,720}.mp4`, `o-catch-a_{1280,720}.webp`, `o-catch-a_end_1280.webp` (same for `o-catch-b`), `docs/renders/o-catch-{f040,f120,f175,f240,f360}.png`.

---

## 3. `o-return`: back to Visakhapatnam harbour · `o-return.blend`, frames 1–288
**Purpose:** the boat comes home, iced crates go into a chilled truck. A generic Indian fishing harbour: no landmarks, no names, no signs.
| Frames | Action | Camera |
|---|---|---|
| 1–72 | The same vessel (library) steams in past a breakwater into a busy fishing harbour; moored boats rafted side by side | aerial 3/4, ~25 m, slow descent |
| 72–150 | Vessel comes alongside the wharf; crew throw lines; **iced crates are passed hand to hand** from the hold onto the wharf, onto steel trolleys | camera lands at ~4 m on the wharf |
| 150–230 | Trolleys roll to a **white rigid reefer truck** parked rear to the wharf, doors open; crates stacked inside (cold mist puff when the doors open, light), doors closed and latched | track along the wharf with a trolley |
| 230–288 | Truck pulls away **forward, one direction**, along the harbour road; camera follows behind at 3/4 ("road-follow" framing: truck centred, ~6 m behind, ~3 m high) | follow |
**Density list:** 12–20 moored fishing boats in varied colours (blue, red, green, white; no names), mooring ropes, tyre fenders, wharf with bollards, crates stacked, ice-crushing shed (plain), steel trolleys, baskets, 10–15 workers (work clothes, gloves), 2–3 other trucks parked (not moving), gulls, low harbour buildings, palms and hills far away under haze, calm green-blue harbour water with reflections.
**Acceptance:** busy harbour, no text; crates are iced; the truck is the library `TRK_RigidReefer` (same as p-harvest and truck-reverse); truck moves forward only; end framing matches truck-reverse frame 1 for the cross-fade; floor 85.
**Render:** `scripts/render-scene.sh o-return preview|full` → `frames-to-master.sh o-return` → encode/posters/check as above.

---

## 4. `p-ponds`: the shrimp ponds · `p-ponds.blend`, frames 1–192
| Frames | Action | Camera |
|---|---|---|
| 1–192 | Bright morning aerial over a **grid of rectangular ponds** (16–30), paddlewheel **aerators** spinning and throwing white water, light ripples; the white reefer truck drives along a bund road **in one direction**, a motorbike follows the same way | drone glide at 60–90 m, 20–30° down, slow forward + slight yaw; ends looking along the bund road the truck uses |
**Density list:** ponds with slightly different green-brown water tints, 2–4 aerators per pond (rotating, foam), bund roads (packed earth with tyre ruts), plastic-lined pond edges on some, feeding trays on poles, power poles and cables to aerators, small sheds and a pump house, coconut palms and scrub along the edges, distant fields, 4–8 workers small on the bunds, birds, morning sun with long soft shadows, light haze far away (sky stays blue).
**Acceptance:** bright morning; all vehicles one direction; aerators turning with white water; no text; floor 85.
**Render:** `scripts/render-scene.sh p-ponds preview|full` → `frames-to-master.sh p-ponds` → encode/posters/check.

---

## 5. `p-harvest`: harvest into ice · `p-harvest.blend`, frames 1–288
| Frames | Action | Camera |
|---|---|---|
| 1–80 | Workers wade at a pond edge drawing a drag net in; the net lifts **out of the water** dripping, shrimp flicking inside | low over the water at the pond edge, ~1.5 m |
| 80–150 | Shrimp tipped from the net into crates of crushed ice on the bund; a worker scoops ice over; a blank batch tag is clipped on each crate | push in, soft DOF on the crates |
| 150–230 | Crates carried and stacked into the white reefer truck parked on the bund road | track along with a carrier |
| 230–288 | Truck drives away **forward**, one direction; camera in "road-follow" framing (same as `o-return`'s end) | follow |
**Density list:** drag net, floats, aerators running in the background, 6–10 workers (shirts, shorts or trousers, caps, gloves), stacked crates, ice boxes, buckets, scales on a table, a tarp shade, the reefer truck, the pond grid behind, palms.
**Acceptance:** shrimp come out of the water; crates are iced; truck = `TRK_RigidReefer`; forward only; end framing matches truck-reverse frame 1; floor 85.
**Render:** `scripts/render-scene.sh p-harvest preview|full` → `frames-to-master.sh p-harvest` → encode/posters/check.

---

## 6. `truck-reverse`: arrival and reversing into the bay (Tarun asked for this explicitly) · `truck-reverse.blend`, frames 1–288
**Tarun's corrections, all mandatory:** the truck **reverses rear-first** into the loading bay; the **cab stays outside, facing the yard**; the **driver gets out and stands outside** by the cab; the **rear doors open into the plant**. One continuous shot.
| Frames | Action | Camera |
|---|---|---|
| 1–48 | Road-follow framing behind the white reefer truck as it approaches the plant gate; the plant ahead: white insulated-panel building with a row of loading bays | follow, ~6 m behind, ~3 m high |
| 48–120 | Truck enters the yard, drives past the bays, then **swings out in an arc** so its rear lines up with bay 2; stops | camera stops and pans; ~8 m high, 3/4 view of the bays |
| 120–200 | **Reverses slowly rear-first** into bay 2 (reverse lights on, slight steering correction, wheels turning backward), the dock shelter closes around the rear, stops flush on the dock bumpers. **Cab is outside facing the yard** | slow drift so both the cab and the dock are visible |
| 200–240 | Driver opens the cab door, steps down, **stands outside by the cab** in the yard (hi-vis vest), places a wheel chock | camera moves along the truck's side toward the building, driver mid-distance |
| 240–288 | Camera passes through the open neighbouring dock door (bay 3) into the bright loading dock inside and pans to bay 2: a masked, gloved worker swings the **truck's rear doors open into the plant**, revealing stacked iced crates. **f288 = boundary with p-intake** | ends inside the dock at ~1.7 m, looking into the open truck |
**Density list:** gate with barrier and gatehouse (plain), yard asphalt with painted lines (no text), 4–6 loading bays with dock shelters, levellers and bumpers, two other trucks parked at other bays, pallets and empty crate stacks, a forklift parked, bollards, lamp posts, potted plants or trees along the fence, roof units and pipes on the building, inside the dock: strip curtains, steel trolleys, 2–3 workers in mask/cap/gloves/apron/boots, bright cool light.
**Boundary objects to write:** camera, `TRK_RigidReefer`, `TRK_DoorL`, `TRK_DoorR`, the 2–3 dock workers.
**Acceptance:**
- [ ] Truck reverses **rear-first** into the bay; never drives nose-in.
- [ ] Cab outside facing the yard for the whole reverse; driver **outside** by the cab after he gets out.
- [ ] Rear doors open **into the plant** (seen from inside).
- [ ] One continuous shot, no cuts; `boundary-check.sh truck-reverse p-intake` OK.
- [ ] Busy yard, no text; floor 85.
**Render:** `scripts/render-scene.sh truck-reverse preview|full` → `frames-to-master.sh truck-reverse` → encode/posters/check.

---

## 7. `p-intake`: intake · `p-intake.blend`, frames 1–192 (starts on truck-reverse f288)
| Frames | Action | Camera |
|---|---|---|
| 1–70 | Masked, gloved, hair-capped workers slide iced crates from the truck onto **steel trolleys** | starts on the boundary, slight push |
| 70–150 | A trolley is pushed through the strip curtain into the **white intake hall**; camera follows the crate | follow at hip height |
| 150–192 | Arrives at the washing area: wash tanks with clean running water, crates being emptied in. **f192 = boundary with p-proc** | settles, looking down the hall toward the line |
**Density list:** 4–6 workers, 3–4 trolleys, crate stacks, ice, floor drains and wet floor sheen, stainless walls/panels, hand-wash station, boot dip, foot-operated sinks, overhead LED panels, PVC strip curtains, scales, hoses on reels.
**Acceptance:** every worker in mask, gloves, hair cap, apron/coat, boots; truck rear stays docked; boundaries both ends OK; floor 70.
**Render:** `scripts/render-scene.sh p-intake preview|full` → `frames-to-master.sh p-intake` → encode/posters/check.

---

## 8. `p-proc`: washing · grading · processing · `p-proc.blend`, frames 1–288 (starts on p-intake f192)
**Tarun's correction:** the hall is **already mid-shift on frame 1**: product already on tables and conveyors, everyone already working. **No new batch sliding in from the top**, no empty tables.
| Frames | Caption (STORY.md 6) | Action | Camera |
|---|---|---|---|
| 1–96 | Washed clean. | Shrimp and fish in wash tanks under spray, workers lifting baskets out, water running | slow dolly down the line at ~2 m |
| 96–192 | Graded to one standard. | Conveyor carries product past graders sorting by size into trays; a grading machine (generic, no text) with rollers | lateral track along the conveyor |
| 192–288 | Made to order. | Long stainless tables of workers de-heading, peeling and deveining shrimp by hand; a separate table cleaning fish; trays filling; at the end the camera nears the glass wall of the lab. **f288 = boundary with p-freeze** | dolly continues, ends at the lab door |
**Density list:** 20–30 workers (mask, gloves, hair cap, apron, boots), 6–10 stainless tables, 2 conveyors, wash tanks with spray bars, grading machine, plastic trays and crates full of product, ice everywhere, scales, buckets, hoses, overhead LED panels in rows, wall panels, drains, a supervisor in a white coat walking.
**Acceptance:** mid-shift from f1; PPE on everyone; nothing slides in; no "placeholder" label anywhere on the site; boundaries OK; floor 70.
**Render:** `scripts/render-scene.sh p-proc preview|full` → `frames-to-master.sh p-proc` → encode/posters/check.

---

## 9. `p-freeze`: lab → freezing → packing → cold storage · `p-freeze.blend`, frames 1–288 (starts on p-proc f288)
**Tarun's correction:** realistic and **toned down**: light frost only, soft cool light, no blizzard, no glowing blue.
| Frames | Caption (STORY.md 7) | Action | Camera |
|---|---|---|---|
| 1–58 | Tested before it moves. | Lab bench: a QC technician (white coat, mask, gloves, cap) checks sample trays, weighs on a scale, notes on a blank clipboard | through the lab door, slow push |
| 58–158 | Frozen at its best. | Trays slide into a **plate freezer** / blast freezer cabinet; door closes; a glazing spray over frozen product on a belt; light frost on metal edges only | track to the freezer, slight crane |
| 158–230 | Packed and labelled. | Packing table: blocks into export cartons and vacuum packs; **blank** labels pressed on; cartons taped and strapped | dolly past the packing line |
| 230–288 | Held at −18 °C to −20 °C. | Cold-store aisle: tall pallet racks loaded with cartons; a pallet truck moves along the aisle (one direction) | camera glides down the aisle, slow, stops centred |
**Density list:** lab bench with trays, scales, sample bags, a fume-hood-like cabinet (generic), fridge; plate freezer with hydraulic plates, blast freezer doors, trolleys of trays; glazing belt; packing tables, carton stacks, tape dispensers, strapping machine, vacuum-pack machine; cold store with 4–6 levels of racks, pallets wrapped in film, insulated door with strip curtain, light frost on rack edges, 6–10 workers in PPE (cold store workers in insulated jackets over PPE).
**Acceptance:** frost subtle (no fog, no snow); soft cool light, never dark; no text on cartons/labels; no temperature numbers in the image; floor 70; boundary in OK.
**Render:** `scripts/render-scene.sh p-freeze preview|full` → `frames-to-master.sh p-freeze` → encode/posters/check.

---

## 10–11. `x-cranes` + `x-ship`: the port, end to end · `port.blend`, frames 1–479
**Tarun's rejection (`reference/feedback/rejected-port-empty-toy.jpg`):** bare grey frames for cranes, an empty quay with one tiny truck, flat grey sky, a placeholder tag. The rebuild must read as a **real, busy container terminal**.
### x-cranes, frames 1–288 (12 s)
| Frames | Action | Camera |
|---|---|---|
| 1–72 | **Gate:** a queue of 4–6 trucks with containers at the gatehouse barriers, all facing in; our white reefer truck (tractor + skeletal trailer + white reefer) passes the barrier | ~12 m high over the gate, slow forward |
| 72–132 | **Yard:** truck drives one direction between yard stacks: colourful containers 4–5 high, rows of **white reefers on plug-in racks** with cables, an **RTG** lifting a box, a **straddle carrier** crossing ahead (same direction), other trucks moving the same way | camera tracks alongside and rises to ~20 m |
| 132–168 | Truck reaches the quay and stops under **crane 2**; crane 2's trolley travels land-side over it; cranes 1 and 3 already mid-cycle (each lifting/lowering a container on cables, offset) | camera settles low on the quay (~4 m), 3/4, ship hull and crane legs filling the background |
| 168–190 | Spreader lowers level on **4 cables** onto the reefer | slow tilt up |
| 190–200 | Lock (2 cm dip), pause | – |
| 200–224 | Lift straight up above the ship's stack height | camera rises with the container |
| 224–256 | Trolley travels sea-side along the boom over the ship; sway ≤ 1° | rising, pitch to ~−45° |
| 256–280 | Lowers into the empty top slot of the target bay | high over the quay edge |
| 280–288 | Unlock; spreader rises 1 m. **Ship static for all of x-cranes. f288 = boundary** | ~70–90 m high, pitch ~−60° |
### x-ship, frames 288–479 (8 s)
| Frames | Action | Camera |
|---|---|---|
| 288–336 | Lines released; **2 tugs** push/pull the ship off the berth; cranes keep working behind | rising, pitching to straight down (−90°) by 336 |
| 336–420 | Ship sails out, **white wake and foam**, bow wave; **tugs peel away** to the sides by ~370; quay leaves the frame; water blends from harbour green-blue to **bright deep blue** | top-down tracking (Mont-Fort style), ship crossing diagonally |
| 420–479 | Camera rises straight up ×4 so the ship shrinks to ≤ 3% of frame width; last 24 frames near-uniform bright deep blue with sun glints, matching the globe start colour | rise |
### Density list (minimum)
- **3 detailed STS cranes:** lattice boom and girder (truss members, not boxes), A-frame apex with forestays and backstays, **machinery house**, **operator cabin** under the trolley, **trolley** with rope sheaves, head block and **spreader on 4 wire ropes**, backreach, legs with bogies on rails, stairs and walkways with handrails, **warning lights** (red/amber, small emissive), cable reel/festoon, paint white/light grey with one blue accent, light rust streaks and grime. No lettering.
- **Ship:** large container ship, dark hull with red antifouling below the waterline, white accommodation block and bridge, funnel, **lashing bridges**, hatch covers, **full stacks** in muted colours plus rows of white reefers, one empty slot under crane 2, mooring lines to bollards, pilot ladder. No name or lettering.
- **Yard:** 8–15 container blocks, 4–5 high, colour-varied with per-instance colour; reefer blocks on plug-in racks with cables and walkways; **2–3 RTGs**, **2 straddle carriers**; light masts (tall, with lamp heads); gatehouse with canopy and barriers; 4–6 trucks (some tractor + trailer with containers, some empty chassis) all one direction; terminal tractors; small hi-vis workers (hard hats, vests) at the quay and lashing platforms, 8–15, never close.
- **Quay:** concrete apron with tyre marks, crane rails, **bollards**, rubber fenders, **painted lane markings** (no text), lashing cages, cones, a few pickup service vehicles parked.
- **Water and sky:** harbour water with **real reflections** (roughness ~0.03–0.08, normal waves), **2 tugs**, distant ships at anchor on the horizon (2–3), bright **sky with clouds** (Poly Haven daylight HDRI or Sky Texture + cloud layer). Never flat grey.
### Rig rules (unchanged from the old spec)
Cranes never bend (object transforms only); hierarchy `Crane_N → Trolley → Headblock → 4 cables → Spreader`, cable length driven each frame; containers attach with Child Of keyed on at lock, off at release; truck wheels from distance travelled.
### Acceptance (tick in both PRs)
- [ ] Reads as a **busy real terminal**: gate queue, yard stacks with reefers, RTGs/straddle carriers, 4–6 trucks, 3 detailed cranes, full ship, tugs, workers, lights, markings.
- [ ] Cranes don't bend; every lifted container hangs on 4 cables from lock to release; no intersections.
- [ ] All trucks one direction; ship static in x-cranes.
- [ ] Bright sky with clouds and real water reflections; x-cranes floor 85, x-ship floor 55 (deep blue, never navy-black).
- [ ] f288 identical in both clips; x-ship last frame matches the globe start colour within ~10 per RGB channel (sample the globe chapter at progress 0 with Playwright, centre 20% mean).
- [ ] No text, logos, names or numbers anywhere; no placeholder tag on the site.
### Render + encode
```bash
scripts/render-scene.sh port preview      # docs/renders/port-preview.mp4, all 479 frames at 960x540
scripts/render-scene.sh port full
scripts/frames-to-master.sh x-cranes x-ship && scripts/boundary-check.sh x-cranes x-ship
scripts/encode-clips.sh x-cranes x-ship && scripts/make-posters.sh x-cranes x-ship && scripts/check-clip.sh x-cranes x-ship
```

---

## 12. Products: photoreal fish (strict standard)
**Tarun's verdict on PRs #73–#75: "the worst".** Cartoon look: smooth blobs, a painted stripe, paddle fins, a flat swordfish. Also the species list is **cut off on the right** of the Products section: fix that layout in the same Products PR (list wraps or scrolls inside its column at every width from 360 px to 1920 px; no text clipped; check at 375, 768, 1280 and 1920).
Standard (all mandatory, see ASSET_LIBRARY.md "Products"):
- **Photoreal**: real fin shapes with fin rays, scales and skin detail from normal + roughness maps, species-accurate colour, wet specular, real eyes (glossy, with depth) and gill covers/slits.
  - Yellowfin tuna: torpedo body, dark metallic navy back, silver-white belly, faint vertical belly bands, yellow lateral stripe as a subtle sheen (not a painted stripe), **yellow finlets** top and bottom, long yellow second dorsal and anal fins, crescent tail.
  - Swordfish: **round-bodied, not flat**, long flat **bill** about a third of body length, **bronze-brown back** fading to lighter sides, skin without visible scales, tall rigid first dorsal, crescent tail, large eye.
  - Shrimp (Vannamei, raw): translucent grey-white segmented shell, visible legs and swimmerets, long antennae, tail fan, slight curve.
- **Build method**: first choice Poly Haven / Sketchfab (**CC0 or CC-BY only**, licence logged) or Hyper3D Rodin through the Blender MCP; otherwise sculpt properly (Multires/dyntopo sculpt, then retopo/decimate and bake). **Never ship procedural blobs.**
- **Presentation**: on a **crushed-ice bed** (`ice-tray`) under soft studio lighting (large softbox key, rim light, light background `#eef5f6`).
- **Approval**: 3 stills per fish (side, 3/4, close-up of head/fins) at 1600 px on the ice bed in the PR; nothing goes on the site until Tarun approves.
- **Fallback**: if a fish can't look photoreal within **500 KB** as a GLB, ship a **Blender-rendered turntable** instead (`prod-tuna`, `prod-swordfish`, `prod-shrimp`: 120 frames = one 360° turn on the ice bed, rendered with the standard settings and encoded like every clip, scrubbed by scroll/drag) or high-res stills. **Real looks beat a live 3D viewer.**
**Render (turntable fallback):** `scripts/render-scene.sh prod-tuna preview|full` → `frames-to-master.sh prod-tuna` → `encode-clips.sh prod-tuna && make-posters.sh prod-tuna` (≤ 0.6 MB desktop / 0.3 MB mobile each).
