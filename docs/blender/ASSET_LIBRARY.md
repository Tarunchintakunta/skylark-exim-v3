# ASSET_LIBRARY.md: every model Claude builds, with budgets and where it's reused

Build the library **first**, in `assets-src/blender/asset-library.blend` (git-ignored). Every scene `.blend` **links** from it (`bpy.data.libraries.load(lib, link=True)` with a relative path `//asset-library.blend`, then collection instances). Anything that animates in a scene (people, trucks, boat, net, crane parts, doors) is brought in as a **library override** (`override_hierarchy_create`) or appended, keeping the **same object names**, because shared boundaries match objects by name (`blender/boundary_camera.py`).

Naming: collections `LIB_<Group>_<Name>`, objects `<PREFIX>_<Part>`. Real-world scale in metres, +Z up, origin at the base centre, facing +X. Every material is Principled BSDF, PBR.

## Sources (in this order; log every external asset)
1. Tarun's kohl-draft sources (github.com/Tarunchintakunta/skylark-exim-cinematic: `blender/scripts/_lib.py`, `a02_container_vessel.py`, `a03_reefer_and_transfer.py`, `a04_products.py`) as code starting points only. Their crane and fish are not good enough; rebuild.
2. **Poly Haven** (CC0) through the MCP if offered: HDRIs, textures (concrete, asphalt, painted metal, rust, rubber, plastic, wet deck), and models.
3. **Sketchfab** through the MCP if offered: downloadable **CC0 or CC-BY** only. Never NC, ND, Editorial or "Standard" paid licences.
4. **Hyper3D Rodin** through the MCP if offered: organic shapes (fish, shrimp, people base meshes, net bag), then clean up and retopo.
5. **MPFB2** (MakeHuman for Blender, CC0 output) for people, if Claude can install the extension; otherwise a Rigify-rigged base mesh modelled from primitives with sculpted clothing.
6. Otherwise model in Blender Python (bmesh, curves, modifiers, geometry nodes), with proper bevels and detail.
Log every external asset in `assets-src/models/LICENSES.md` **and** `docs/LICENSES.md` (name, URL, author, licence, which scene). CC-BY credits go in the site footer ("3D assets: …") in the PR that first uses them.

## Realism standard (applies to every asset)
Bevels on every hard edge (Bevel modifier, 2–3 segments, weighted normals); PBR textures at 1k–2k (4k only for hero close-ups); wear: edge wear, rust streaks, grime and water stains via procedural masks or Poly Haven textures; blank decals only (stripes, hazard bands, never letters, numbers or logos); wet materials where the scene is wet (lower roughness, darker albedo, small droplet normals); no perfectly clean, perfectly flat surfaces.

## Budgets (rendered video, so these are about scene speed and memory, not download size)
| Group | Asset (collection) | Tris per instance | Textures | Reused in |
|---|---|---|---|---|
| **People** | `LIB_People_Base` (male + female base, Rigify or MPFB rig, 4 body variants) | 15–30k | 2k skin/clothes atlas | all scenes with people |
|  | Outfit `PlantWorker`: white apron or coat, **hair cap**, **face mask**, **gloves** (blue or white), white gumboots | +5k | 1k | truck-reverse (dock), p-intake, p-proc, p-freeze |
|  | Outfit `Fisherman`: **orange/yellow oilskin bib trousers and jacket**, cap, rubber gloves, boots | +6k | 1k | o-catch, o-return |
|  | Outfit `FarmWorker`: shirt, rolled trousers or shorts, cap, gloves | +4k | 1k | p-ponds, p-harvest |
|  | Outfit `Driver`: shirt, trousers, **hi-vis vest** | +3k | 1k | o-return, p-harvest, truck-reverse |
|  | Outfit `PortWorker`: coverall, **hi-vis vest**, hard hat, gloves | +4k | 1k | x-cranes |
|  | Outfit `QCTech`: white lab coat, mask, cap, gloves | +4k | 1k | p-freeze |
|  | Outfit `ColdStore`: insulated jacket over PPE | +4k | 1k | p-freeze |
|  | Pose/action library: walk, idle, pull rope, guide load, kneel-sort, shovel ice, pass crate, lift crate, push trolley, sort at table, peel shrimp, weigh, tape carton, drive (seated), step down from cab, place chock | – | – | everywhere |
| **Fishing** | `LIB_Boat_FishingVessel`: steel hull white with blue trim, wheelhouse with windows and railings, mast with lights, **boom/derrick with block and hydraulic ram**, **winch drum** with rope, steel rail, hatch + hold, scuppers, tyres along the hull | 60–120k | 2k atlas + tiling wet deck | o-catch, o-return (+ 12–20 low variants for the harbour, 10–20k each) |
|  | `LIB_Net_Bag`: net mesh (alpha-mapped mesh texture on a cloth-simmable bag) with **yellow floats** along the headline, hook ring, release line | 10–20k | 1k net alpha | o-catch |
|  | `LIB_Net_Drag`: small pond drag net with floats | 5k | 1k | p-harvest |
|  | `LIB_Fish_School`: low-poly proxies for sims: silver mackerel-like (3 sizes), **tuna** (2 sizes), seer, ribbon fish; each with the photoreal texture from the Products bake | 0.5–2k | shared 2k | o-catch (net, deck, crates), o-return |
| **Cold chain props** | `LIB_Crate_Plastic` (blue/red/white, stackable, with handles) + `_Full` variants with fish/shrimp on **crushed ice** | 1–3k | 1k | o-catch, o-return, p-harvest, truck-reverse, p-intake, p-proc |
|  | `LIB_Ice_Crushed` (displaced mesh + translucent material), `LIB_Ice_Flake_Box` | 2–10k | 1k | everywhere |
|  | `LIB_Trolley_Steel` (crate trolley, tray trolley) | 3k | tiling steel | truck-reverse, p-intake, p-proc, p-freeze |
|  | `LIB_Carton_Export` (plain corrugated, blank label area, tape, strap) + `LIB_Pallet` + stretch-wrapped pallet | 0.5–2k | 1k | p-freeze, x-cranes (reefer interior not shown) |
|  | `LIB_Tag_Blank`, `LIB_Basket`, `LIB_Bucket`, `LIB_Shovel`, `LIB_Hose_Reel`, `LIB_Scale_Bench` | <2k each | tiling | everywhere |
| **Vehicles** | `LIB_TRK_RigidReefer`: white rigid reefer truck (cab with interior silhouette, mirrors, blank plates, insulated box, front fridge unit, **twin rear doors** `TRK_DoorL`/`TRK_DoorR` hinged, reverse lights, wheels separate for rotation) | 40–60k | 2k | o-return, p-ponds, p-harvest, truck-reverse, p-intake |
|  | `LIB_TRK_Tractor` + `LIB_TRK_SkeletalTrailer` (3 axles, landing legs) | 40k + 10k | 2k | x-cranes (hero + 4–6 queue variants) |
|  | `LIB_Forklift`, `LIB_PalletTruck`, `LIB_Pickup`, `LIB_Motorbike`, `LIB_TerminalTractor` | 10–25k | 1k | plant, ponds, port |
| **Port** | `LIB_Container_Dry` (corrugated, corner castings, doors with locking bars; per-instance colour attribute) | 3–6k | 1k + colour attr | x-cranes, x-ship (instanced in the thousands) |
|  | `LIB_Container_Reefer` (white, front fridge unit, plug cable) | 6–8k | 1k | x-cranes, x-ship |
|  | `LIB_Crane_STS`: **lattice boom/girder**, A-frame, forestays/backstays, **machinery house**, **operator cab**, **trolley**, **headblock + spreader + 4 wire ropes**, backreach, legs + bogies, stairs/walkways/handrails, **warning lights**, festoon; named child nodes `Crane_N_Trolley`, `_Headblock`, `_Spreader`, `_Cable_1..4` | 120–200k (instanced ×3) | 2k atlas | x-cranes, x-ship |
|  | `LIB_RTG`, `LIB_StraddleCarrier` | 40–60k | 1k | x-cranes |
|  | `LIB_Ship_Container`: hull, bridge/accommodation, funnel, **lashing bridges**, hatch covers, bays for instanced containers, mooring lines | 80–150k (+ instances) | 2k atlas | x-cranes, x-ship |
|  | `LIB_Tug` | 20–40k | 1k | x-cranes, x-ship |
|  | `LIB_Quay_Kit`: bollards, fenders, rails, light masts, lane markings (decals, no text), gatehouse, barriers, reefer plug racks, cones | <10k each | tiling concrete/asphalt | x-cranes; gate/barrier also truck-reverse |
| **Sets** | `SET_PlantExterior`: white insulated-panel building, **4–6 loading bays** with dock shelters, levellers, bumpers, doors; yard, gate, fence, lamp posts, trees | 100–200k | tiling | truck-reverse, p-intake |
|  | `SET_PlantInterior`: dock, intake hall, wash tanks, conveyors, grading machine, stainless tables, lab, plate/blast freezer, glazing belt, packing line, cold store racks; LED panel lights; strip curtains; drains | 300–600k total | tiling stainless/panel/epoxy floor | truck-reverse (dock), p-intake, p-proc, p-freeze |
|  | `SET_Harbour`: breakwater, wharf, sheds, moored boat variants, low buildings, palms, distant hills | 200–400k | tiling | o-return |
|  | `SET_PondGrid`: geometry-nodes pond grid (16–30 ponds), bunds, aerators (rotating, foam), poles, sheds, palms | 200–500k (instanced) | tiling | p-ponds, p-harvest |
| **Nature** | Ocean (Ocean modifier + foam attribute), wake/foam planes, splash/drip particles, gulls, palms, scrub, cloud cards | – | – | sea and exterior scenes |
| **Materials** | `MAT_PaintedMetal` (+ wear), `MAT_Rust`, `MAT_Concrete`, `MAT_Asphalt`, `MAT_Stainless`, `MAT_WetDeck`, `MAT_Rubber`, `MAT_Glass`, `MAT_Oilskin`, `MAT_NitrileGlove`, `MAT_Ice`, `MAT_Water_Harbour`, `MAT_Water_Sea`, `MAT_FishSkin_*` | – | 1–2k | everywhere |
| **World** | 2–3 Poly Haven daylight HDRIs (clear morning, midday with clouds), plus a soft studio HDRI for Products | – | 4k HDR (render only) | everywhere |

Instancing: use collection instances or geometry nodes for anything repeated (containers, crates, fish, bollards, lights, people extras, ponds, boats). A scene should still open and scrub in the viewport.

## Products (strict standard: Tarun called PRs #73–#75 "the worst")
| File | Used in | Max tris | Textures (before optimise) | Final size |
|---|---|---|---|---|
| `tuna.glb` | Products · Marine Fish | 30k | 2k albedo + 2k normal + 1k roughness | ≤ 500 KB (hard cap 1.5 MB) |
| `swordfish.glb` | Products · Marine Fish | 30k | same | ≤ 500 KB |
| `shrimp.glb` | Products · Shrimps | 30k | same | ≤ 500 KB |
| `carton.glb` | Products stage prop (plain export carton, blank label area) | 2k | 1k | ≤ 150 KB |
| `ice-tray.glb` | Products stage: stainless tray with a **crushed-ice bed** the fish rest on | 20k | 1k albedo + 1k normal | ≤ 300 KB |
- **Photoreal or nothing:** real fin shapes with **fin rays**, **scales/skin detail in normal + roughness maps**, species-accurate colour, **wet specular**, real **eyes** and **gills**. Species looks are in SCENES.md §12. **Never ship procedural blobs, painted stripes or paddle fins.** The swordfish is round-bodied with a proper bill and a bronze back.
- **Method:** Poly Haven / Sketchfab CC0/CC-BY / Hyper3D Rodin via the MCP if available, otherwise a proper sculpt (high-poly sculpt → retopo/decimate → bake normal, AO and albedo onto the low-poly). Check against reference photos the connector can fetch.
- **Look-dev scene `products.blend`:** fish on the crushed-ice bed, soft studio lighting (large softbox key, rim light, light `#eef5f6` background). The same lighting idea goes into the site's R3F stage (Environment + soft key + rim) so the live model looks like the render.
- **Approval:** 3 stills per fish at 1600 px (side, 3/4, head/fin close-up) in `docs/renders/`, Tarun approves in the PR before the GLB replaces anything.
- **Export:** glTF Binary, compression off, then `scripts/optimize-glb.sh <name>` (then `TEX=1024` if needed) and `npx @gltf-transform/cli@4 inspect public/models/<name>.glb`.
- **Fallback (preferred over a weak GLB):** if a fish can't look photoreal within 500 KB, ship the Blender turntable `prod-<name>` (SCENES.md §12) or approved stills instead of the live viewer. **Real looks beat a live 3D viewer.**
- The fish texture work is reused: the same baked skins go on the low-poly fish proxies in `o-catch` and `o-return`.

## Retired GLBs
`truck.glb`, `reefer.glb`, `crane.glb`, `ship.glb` from PRs #76–#79 are not loaded by the site; no need to re-export them unless Tarun asks. The globe stays code-built.
