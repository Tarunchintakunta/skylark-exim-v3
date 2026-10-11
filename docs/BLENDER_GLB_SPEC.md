# BLENDER_GLB_SPEC.md: everything 3D (Claude builds it all in Blender)

**Claude builds every 3D asset itself through its Blender connector (Blender MCP).** Tarun does not model, animate or render anything. His only 3D jobs: keep Blender open on his Mac with the MCP add-on connected while Claude works, keep the Mac awake and plugged in during renders, and approve the renders/PRs.

This zip contains no .glb, .blend or video files. Claude creates them, keeps sources in git-ignored `assets-src/`, and commits only optimised outputs in `public/`.

## What Claude builds (all of it)
| # | Deliverable | Source file Claude makes | Output used by the site | Issue / PR |
|---|---|---|---|---|
| 1 | Fish + shrimp models | `assets-src/models/{tuna,swordfish,shrimp}.glb` | `public/models/{tuna,swordfish,shrimp}.glb` (Products) | one per model: `3d: tuna`, `3d: swordfish`, `3d: shrimp` |
| 2 | **Port & ship scene**: quay, 3 STS gantry cranes, refrigerated truck, reefer container, loaded container ship, water, sky, keyframed crane lift and ship sail-out | `assets-src/blender/port.blend` | rendered to the two scroll clips **`x-cranes`** (scene 9) and **`x-ship`** (scene 10) through the normal video pipeline | `3d: port scene build`, `3d: port animation + preview`, then one per shot: `render: x-cranes`, `render: x-ship` |
| 3 | Logistics models exported from port.blend | `assets-src/models/{truck,reefer,crane,ship}.glb` | `public/models/{truck,reefer,crane,ship}.glb` (reuse: p-intake fallback, OG image, realtime fallback, future pages; **not loaded by the default site**) | one per model: `3d: truck`, `3d: reefer`, `3d: crane`, `3d: ship` |
| 4 | Only if needed: p-intake fallback shot (truck backed to the dock, no people) | `assets-src/blender/intake.blend` | an 8 s render encoded as the `p-intake` clip | `render: p-intake fallback` (only opened if the fallback is triggered, see §6) |
| – | Globe | none: **built in code** (last section) | R3F | `feat: bright globe + routes` |

Every Blender PR carries: 3 still renders (PNG, 1200 px wide, in `docs/renders/`), the numbers (tris, texture sizes, bytes from `gltf-transform inspect`; or clip KB from `encode-clips.sh`), and for animation PRs a preview MP4 link. Tarun approves the look in the PR; only Tarun merges.

## 1. Working with the Blender connector (rules)
1. **Check the connection first:** ask Blender for the scene info. If the connector isn't reachable, stop and tell Tarun: "Open Blender, press N in the 3D viewport → BlenderMCP tab → Connect". Never fake a model or a render; keep the placeholders (CLAUDE_PROMPT §6) and carry on with other issues.
2. **Small steps:** send Python in small chunks (one object or one animation block per call), check with a viewport screenshot after each important step, and **save the .blend after every step** (`bpy.ops.wm.save_as_mainfile(filepath=...)`, absolute path inside the repo's `assets-src/`). Blender and Claude Code run on the same Mac, so the repo path is the same for both.
3. **Long renders never run inside an MCP call** (it times out). Run them headless from Claude Code's terminal: `/Applications/Blender.app/Contents/MacOS/Blender -b assets-src/blender/port.blend -a` (settings are saved in the .blend). If background EEVEE fails on this Mac, render from the open Blender via MCP in chunks of ≤ 24 frames per call (`scene.frame_start/end` per chunk).
4. **Starting points** (in this order): (a) Tarun's own kohl-draft sources in github.com/Tarunchintakunta/skylark-exim-cinematic: `blender/scripts/_lib.py` (helpers), `a02_container_vessel.py` (`build_container`, container ship), `a03_reefer_and_transfer.py` (reefer with doors; its crane is only two legs and a beam, so rebuild it), `a04_products.py` (fish), and `blender/blends/*.blend`, `public/assets/models/**.glb`. Reuse code, then improve to this spec. (b) If the connector offers Poly Haven: CC0 HDRIs and textures (concrete, painted metal, water). (c) If it offers Sketchfab: downloadable **CC0 or CC-BY** models only, logged in `assets-src/models/LICENSES.md` (name, URL, author, licence; CC-BY credit in the footer); never NC/ND/Editorial. (d) If it offers AI 3D generation (e.g. Hyper3D Rodin): fine for organic shapes (fish, shrimp), then clean up. (e) Otherwise model procedurally with Blender Python (bmesh, curves, modifiers).
5. Units metres, +Z up inside Blender (the glTF exporter converts to +Y up). Version: whatever Blender is installed (4.2+ or 5.x); use the engine id Blender reports (`BLENDER_EEVEE_NEXT` in 4.2–4.5, `BLENDER_EEVEE` in 5.x).

## 2. Fish and shrimp (Products)
1. Base: kohl `tuna_hero.glb`, `swordfish_hero.glb`, `shrimp_product_forms.glb` (or `a04_products.py`), imported and improved; else options 1.4 (b)–(e).
2. **Species-accurate look (fix proportions first):** yellowfin tuna = torpedo body, dark navy-blue back, silver belly, yellow finlets, long yellow second dorsal and anal fins. Swordfish = long flat sword bill (about a third of body length), smooth skin with no scale look, dark bronze-grey back, tall rigid first dorsal, crescent tail. Shrimp (Vannamei, raw) = translucent grey-white segmented body, long antennae, tail fan, slight curve. Compare with reference photos the connector can fetch or describe.
3. Clean and bake to the table in §4: apply transforms, join to one mesh, decimate to the budget, Smart UV Project, bake Base Color (+ Normal from the high-poly) to one texture in Cycles, one Principled BSDF.
4. Render check: 3 PNGs per model (side, 3/4, top) on the light Products background `#eef5f6`, 1200 px wide → `docs/renders/<name>-{side,34,top}.png`.
5. Export (§7) → `scripts/optimize-glb.sh <name>` → ≤ 500 KB.
6. Until a model is approved, Products uses the kohl GLBs as placeholders.

## 3. Port & ship scene (`assets-src/blender/port.blend`) → clips `x-cranes` + `x-ship`
**Default delivery = rendered video**, not realtime 3D: Claude renders the two shots from Blender (EEVEE, photoreal daylight), encodes them with `scripts/encode-clips.sh` like every other clip, so scroll smoothness, budgets and the photoreal look of the AI clips stay the same. Nothing in this scene appears as text on the site; the sizes below are **modelling guidance only and must never be used in site copy**.

### 3.1 Objects (one collection each)
| Collection | What to build | Modelling guidance (approximate, generic, not any real port) |
|---|---|---|
| `Quay` | Concrete quay apron along the water, two crane rails, rubber fenders and bollards on the edge, painted lane lines (no text), light masts, a few background yard stacks (simple boxes, same container materials), distant terminal edge | apron 60–80 m deep, quay length ≥ 400 m so the camera never sees its end |
| `Crane_1`, `Crane_2`, `Crane_3` | **Ship-to-shore gantry crane**: 4 legs on rail bogies, portal beams, sill beam, boom (sea side) + girder (land side) horizontal in working position, A-frame apex with forestays, machinery house, operator cab under the trolley, **trolley** that runs along boom/girder, **head block + spreader** hanging on **4 wire ropes** (thin cylinders, one per corner) | rail gauge ~30 m; lift height under spreader ~40–45 m above quay; outreach ~55–65 m beyond the sea-side legs; back-reach ~15–20 m; spreader footprint = container footprint. Paint: white/light grey with one accent colour (blue), no lettering. Cranes ~100 m apart along the quay |
| `Truck` | **White refrigerated truck**: tractor unit (cab, 3 axles, mirrors, blank number plates) + skeletal trailer chassis (3 axles, landing legs) carrying the **reefer container** | tractor ~6.5 m; chassis ~12.5 m |
| `Reefer` | **White reefer container**: corrugated side panels (normal/bump), corner castings, twin rear doors with locking bars, **refrigeration unit flush on the front end** (grille, fan housing, blank display panel). No text, logos or numbers | box ~12.2 × 2.44 × 2.9 m (standard high-cube size) |
| `Ship` | **Large container ship** moored alongside: dark hull with red below the waterline, white accommodation block and bridge near the stern, hatch covers, lashing bridges, bays of stacked containers 4–6 high on deck in muted colours (red, blue, green, grey, orange) **plus rows of white reefers**; one empty slot on top of the target bay under crane 2 for the hero reefer. No name, no lettering, no logos anywhere | ~250–300 m long, ~40 m beam |
| `Water` | Harbour water (calmer, slightly darker green-blue) by the quay; open sea (deep blue, Ocean modifier with gentle swell, small sun glints) beyond; a **wake** (V-shaped foam plane + noise texture parented to the stern, scaled with ship speed) and a bow wave for shot 2 | ocean plane ≥ 4 km so the top-down rise never shows an edge |
| `Sky` | World: Sky Texture (Nishita in 4.x / default sky model in 5.x) with sun elevation 35–50°, or a CC0 Poly Haven daylight HDRI; one Sun lamp aligned with it | clear bright morning–midday |
| `Extras` (optional) | 1–2 terminal tractors in the yard, each moving one direction only. No people needed (if any, tiny figures in hard hats and hi-vis, never close-up) | – |

Materials: Principled BSDF, painted metal (roughness 0.4–0.55), slight edge wear and grime via procedural noise, concrete with tyre marks, rubber fenders, glass on cab/bridge. Containers share one material with a colour attribute (per-instance colour) so the ship stacks stay light; use instancing (collection instances / geometry nodes) for repeated containers, crane parts and bollards.

### 3.2 Rig (rigid parts only: **cranes never bend**)
- Cranes, ship and truck are moved only by **object transforms** (no armature deformation, no shape keys, no soft-body on them).
- Hierarchy per crane: `Crane_N` → `Crane_N_Trolley` (moves along local boom axis) → `Crane_N_Headblock` → 4 cables → `Crane_N_Spreader`. Cable length is driven (driver or `Stretch To` constraint) from head block to the spreader's corner each frame, so the spreader always hangs on 4 cables.
- Containers attach with a **Child Of** constraint keyed on at the lock frame and off at the release frame (the container then stays exactly where it was set down).
- Truck wheels: rotation driven by distance travelled (`distance / wheel_radius`), forward only.

### 3.3 Animation timeline (24 fps; frames 1–383 rendered once, split into two 8 s clips sharing frame 192)
**Shot 1 = `x-cranes`, frames 1–192**
| Frames | Action | Camera |
|---|---|---|
| 1–60 | Truck enters from frame left, drives **one direction only** along the quay lane under the cranes, eases to a stop with the reefer centred under crane 2 at f60. Crane 1 and crane 3 are already mid-cycle (each lifting/lowering a container on cables, phase-offset so something always moves) | **Cam A** low on the quay (~4 m high), 3/4 view, slow lateral track with the truck; crane 2 legs and the ship hull fill the background |
| 30–70 | Crane 2 trolley travels land-side to above the truck lane (starts before the truck stops so it reads as coordinated) | Cam A settles, slight push-in |
| 70–96 | Spreader lowers level on its 4 cables onto the container top | slow tilt up begins |
| 96–106 | Lock: spreader seats (2 cm dip), pause | – |
| 106–130 | Lift straight up to above the ship's stack height | **Cam rises with the container** (crane-up move), keeping it in the upper third |
| 130–162 | Trolley travels sea-side along the boom out over the ship; container sway ≤ 1°; never detaches | camera keeps rising and drifts sea-side, pitch going from ~+10° to ~−45° |
| 162–184 | Lowers onto the empty top slot of the target bay; lands aligned at f184 | camera high above the quay/ship edge |
| 184–192 | Unlock, spreader rises 1 m. **Ship has not moved at all during shot 1** | f192: high view (~70–90 m), pitch ~−60°, looking down on the loaded deck |

**Shot 2 = `x-ship`, frames 192–383 (frame 192 is shared, so the hand-off is invisible)**
| Frames | Action | Camera |
|---|---|---|
| 192–240 | Ship eases away from the quay and starts moving ahead (cranes keep working in the background, other ships none) | camera continues rising and pitches to **straight down (−90°)** by f240 |
| 240–330 | Ship sails out across open water, white wake trailing, bow wave; quay leaves the frame; water blends from harbour to **deep blue open sea** | **top-down tracking** the ship (Mont-Fort style), ship crossing the frame diagonally, steady |
| 330–383 | Ship keeps going | camera rises straight up (altitude ×4) so the ship shrinks to ≤ 3% of frame width; the last 24 frames are an almost uniform field of deep blue with gentle sun glints |

All F-curves Bezier with eased starts/stops, no jumps, no cuts. Motion blur on, so every move stays slow enough to read as continuous.

**Hand-off colour (film → globe):** the site cross-fades the last 15% of scene 10 into the bright globe, whose camera starts close over the sea off Visakhapatnam. Claude samples the globe's first frame (Playwright screenshot of the globe chapter at progress 0, mean of the centre 20% box) and tunes the open-sea colour/exposure so x-ship's last frame centre mean is within ~10 per RGB channel of it. Until the globe exists, use the mean of the Blue Marble texture around 15°N 88°E. If that colour would make the film look navy-black, brighten the globe (exposure/atmosphere) instead: the hand-off must read as **bright deep blue, never dark**.

### 3.4 Render settings (saved in port.blend)
- Engine EEVEE (Next), 1920×1080, 100%, 24 fps, frames 1–383.
- Samples: render **64**; ray tracing on (resolution 1/2); shadows on; volumetrics off (no fog); **no bloom/glare**; motion blur **on** (shutter 0.5); depth of field off for shot 2, subtle for shot 1 (f-stop 8+).
- Colour management: View **AgX** (Look None or Medium High Contrast), exposure tuned so sky and water stay bright; no orange-teal grade.
- Output: PNG, RGB 8-bit, compression 15, output path `//../render/port/` (= `assets-src/render/port/####.png`).
- Expect roughly 0.5–2 h for 383 frames on an Apple-silicon Mac (EEVEE). Schedule it on **Day 2** and do other issues while it renders.

### 3.5 Preview first (Tarun approves before the full render)
```bash
B=/Applications/Blender.app/Contents/MacOS/Blender
mkdir -p assets-src/render/preview docs/renders
$B -b assets-src/blender/port.blend --python-expr "import bpy; s=bpy.context.scene; s.render.resolution_percentage=50; s.eevee.taa_render_samples=16; s.render.use_motion_blur=False; s.render.filepath='//../render/preview/'" -a
ffmpeg -v error -y -framerate 24 -i assets-src/render/preview/%04d.png -c:v libx264 -crf 26 -pix_fmt yuv420p docs/renders/port-preview.mp4
```
960×540, all 383 frames, ≤ 4 MB. Post it in the `3d: port animation + preview` PR with 3 stills (f60 truck parked, f150 container over the ship, f300 top-down ship) and wait for Tarun's ok or notes. Until the final clips exist, the encoded preview can stand in as the scene 9–10 placeholder.

### 3.6 Full render → clips
```bash
$B -b assets-src/blender/port.blend -a                      # 1920x1080, frames 1-383 -> assets-src/render/port/
ffmpeg -v error -y -framerate 24 -start_number 1   -i assets-src/render/port/%04d.png -frames:v 192 -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p assets-src/video/x-cranes.mp4
ffmpeg -v error -y -framerate 24 -start_number 192 -i assets-src/render/port/%04d.png -frames:v 192 -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p assets-src/video/x-ship.mp4
scripts/encode-clips.sh x-cranes x-ship && scripts/make-posters.sh x-cranes x-ship
```
The masters in `assets-src/video/` are 1080p like the Higgsfield masters, so the rest of the pipeline is identical (`<id>_1280.mp4`, `<id>_720.mp4`, posters, budgets ≤ 1.5 MB / 0.8 MB per 8 s). One PR per shot (`render: x-cranes`, `render: x-ship`) with 3 stills each, the KB numbers and the preview link.

### 3.7 Acceptance checks (put this list, ticked, in each render PR)
- [ ] **Cranes don't bend**: crane objects have no armature/shape-key/deform modifiers; only object transforms are animated.
- [ ] **Container on cables the whole time**: every lifted container (all 3 cranes) is attached to a spreader on 4 visible cables from lock to release; no container moves on its own; no intersections with boom, stacks or truck.
- [ ] **Truck moves one direction only**: its X location never decreases over frames 1–60, then stays parked; wheels roll forward only.
- [ ] **Ship static during loading** (frames 1–192), moves only in shot 2.
- [ ] **No text, logos, brand names or numbers** anywhere (containers, hull, truck, plates, crane).
- [ ] **Daylight, not dark**: blue sky, sun high; `ffmpeg -i assets-src/video/x-cranes.mp4 -vf signalstats,metadata=print:key=lavfi.signalstats.YAVG -f null - 2>&1 | grep YAVG` stays ≥ ~85 for x-cranes and ≥ ~55 for x-ship (deep blue, never navy-black).
- [ ] x-cranes last frame is pixel-identical to x-ship first frame (both are `0192.png`).
- [ ] x-ship last frame is near-uniform deep blue matching the hand-off colour (3.3).
- [ ] Encoded sizes within budget (`encode-clips.sh` prints no `!!`).

### 3.8 Realtime alternative (fallback only, not default)
Only if Tarun asks for interactive 3D here, or rendering is impossible: an R3F scene using `crane.glb` (animated `trolley`/`spreader` nodes), `truck.glb` and `ship.glb`, driven by the scroll timeline. It must still pass every number in CLAUDE_PROMPT §9; if it doesn't, go back to the rendered clips.

## 4. Model table (GLB exports)
| File name | Used in | Max tris | Textures (before optimize) | Materials | Final size (after optimize) | Required |
|---|---|---|---|---|---|---|
| `tuna.glb` | Products · Marine Fish | 30k | 1× 2048 albedo (+ optional 1024 normal) | 1 PBR: metallic 0.3–0.5 on back, roughness 0.35, silver belly | ≤ 500 KB (hard cap 1.5 MB) | yes |
| `swordfish.glb` | Products · Marine Fish | 30k | 1× 2048 albedo (+ 1024 normal) | 1 PBR, long intact bill, dark back, silver belly | ≤ 500 KB (hard cap 1.5 MB) | yes |
| `shrimp.glb` | Products · Shrimps | 30k | 1× 2048 albedo (+ 1024 normal) | 1 PBR, slightly translucent look via roughness 0.3 (no transmission, too costly) | ≤ 500 KB (hard cap 1.5 MB) | yes |
| `truck.glb` | Reuse: p-intake fallback, OG image, realtime fallback | 15k | 1× 1024 | 1 PBR (white cab/reefer, grey chassis, black tyres via texture) | ≤ 500 KB | yes |
| `reefer.glb` | Reuse: hero prop (realtime fallback, Products/Export backdrop if wanted) | 8k | 1× 1024 | white painted metal, refrigeration unit on the front end, no text/logos | ≤ 500 KB | yes |
| `crane.glb` | Reuse: realtime fallback | 25k | 1× 1024 (or vertex colours, no texture) | 1 PBR; named child nodes `trolley`, `spreader`, `cables` so code can move them | ≤ 500 KB | yes |
| `ship.glb` | Reuse: realtime fallback, OG image | 40k (containers instanced) | 1× 2048 atlas | 1 PBR | ≤ 500 KB | yes |
| `globe.glb` | – | – | – | – | – | **no**: the globe is built in code (last section) |

Common rules: real-world scale in metres, +Y up (exporter default), centred on the origin, facing +X (head/bow/cab to the right), applied transforms, one material, no cameras, no lights, no animation (motion is done in code). Fish/shrimp/reefer/truck/ship: one mesh where possible; crane keeps the named child nodes. Named root node = file name. The logistics GLBs are **not loaded by the default site**, so they add nothing to page weight.

**Optional later:** a "shrimp forms" set (HOSO, HLSO, PUD, PD tail-on…) as `shrimp_forms.glb`; the Products grid works with DOM cards without it.

## 5. Bake and clean-up recipe (every GLB)
1. Apply all transforms (Ctrl+A); join parts that don't move (Ctrl+J); origin to geometry, location 0,0,0.
2. Statistics overlay on; if over budget, Decimate (Collapse) until within the table, watching silhouettes (fins, bill, antennae, boom, ropes).
3. Shade Auto Smooth.
4. Smart UV Project; one new 1024/2048 image `bake_albedo`; Cycles → Bake → Diffuse, Color only (untick Direct/Indirect); for normals bake from the high-poly with Selected to Active.
5. Replace materials with one Principled BSDF using the baked image(s); set metallic/roughness per the table.
6. Render 3 checks (side, 3/4, top), 1200 px, light `#eef5f6` background → `docs/renders/<name>-*.png`.

## 6. p-intake fallback (only if the Higgsfield regen fails)
Trigger: `p-intake` still fails its "Accept if" list after 2 re-rolls, or Tarun says "use Blender for intake".
- Look at `assets-src/anchors/anchor2.png` first and match its truck: if anchor2 shows a rigid box truck rather than tractor + trailer, build a rigid variant in the same white/no-text style (reuse the reefer body and cab).
- `assets-src/blender/intake.blend`: plant loading-bay façade (white insulated panels, open dock door with dock shelter and leveller, bright cool light spilling out), yard asphalt, the truck **reversed rear-first** flush to the dock, **cab facing away from the building into the yard**, rear doors open into the plant. **No people.** Morning daylight (same sky setup).
- Camera: 8 s (192 frames), slow push from the yard toward the open rear of the truck, ending on the lit doorway.
- Render and encode exactly as §3.4–3.6, output `assets-src/video/p-intake.mp4`. Joins become cross-fades on both sides (`anchor2` → p-intake and p-intake → p-proc: `joinNext: 'crossfade'`); generate p-proc without a start_image (keep its end_image). The scene 5 copy is unchanged.

## 7. glTF export settings (every GLB)
File → Export → glTF 2.0, or `bpy.ops.export_scene.gltf(...)`:
- Format **glTF Binary (.glb)**; selected objects only; no cameras, no punctual lights; +Y up.
- Apply modifiers; UVs; normals; vertex colours only if the model uses them (e.g. the kohl fish); materials export.
- Compression **off** (the script adds meshopt; Draco + meshopt together breaks). Animation off.
- Save as `assets-src/models/<name>.glb`, then:
```bash
scripts/optimize-glb.sh <name>                      # assets-src/models -> public/models (meshopt + WebP, 2048 max); warns > 500 KB
TEX=1024 scripts/optimize-glb.sh <name>             # if over 500 KB
npx @gltf-transform/cli@4 inspect public/models/<name>.glb   # tris, texture sizes, bytes, must list EXT_meshopt_compression
```
In R3F: `useGLTF('/models/tuna.glb')` (drei wires the meshopt decoder for `EXT_meshopt_compression`), `useGLTF.preload` when the section is ≤ 1 viewport away, `<Suspense>` with the DOM card as fallback. KTX2 only if `KTX2=1` was used (then wire drei's KTX2 loader with the basis transcoder copied to `/basis/`).
Save every `.blend` source in `assets-src/blender/` (git-ignored; Git LFS only if Tarun wants them versioned).

## The globe: code-built and how routes are drawn
- Mesh: `<sphereGeometry args={[1, 128, 64]} />` + `meshStandardMaterial` with `public/textures/earth_day_4096.webp` (2048 on mobile), roughness 0.85. Texture: NASA Visible Earth "Blue Marble" day image (public domain, https://visibleearth.nasa.gov/collection/1484/blue-marble). Atmosphere: a second sphere at r = 1.025 with a fresnel ShaderMaterial (light sky-blue `#9fd3ff`, additive, back-side). Scene background is light (`#eef5f6` → `#dcebf0` gradient in CSS behind a transparent canvas). Lighting: `<Environment preset="city" />` (or a Poly Haven daylight HDRI at 1k) + one directional light from the upper left, intensity 2.5. The planet must read **bright daytime**. Never use the kohl `globe_routes_from_india.glb` (dark, routes baked in).
- Routes are **never baked**: for each market, convert lat/lon (CONTENT.md table) to a Vector3 on r = 1, build a `QuadraticBezierCurve3` from Visakhapatnam with the control point at the midpoint normalised to r = 1 + 0.25·(arc length), sample 64 points, render with drei `<Line>` (Line2, width 2 px, colour brass `#d7a84f`, `transparent`). Animate draw-on by scrubbing a dash offset or `geometry.setDrawRange(0, n)` from the scroll timeline (no React state per frame). A small brass dot + pulsing ring marks each market when its arc lands; label is DOM (`<Html>` from drei, `occlude`), market names only.
- Camera: starts 1.15 r above the sea off Visakhapatnam (its blue matches x-ship's last frame, see §3.3 hand-off colour), pulls back to 3.2 r while the globe rotates from 83°E to show Europe → East Asia as arcs draw.
