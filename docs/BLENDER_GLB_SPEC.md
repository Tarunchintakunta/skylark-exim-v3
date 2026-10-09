# BLENDER_GLB_SPEC.md: 3D models

**This zip contains no .glb files.** Tarun makes or downloads them, saves the raw export to `assets-src/models/<name>.glb`, and Claude runs `scripts/optimize-glb.sh` to produce `public/models/<name>.glb`. Until a model exists, Claude ships a placeholder (see "Placeholders") so the build never blocks on 3D.

## The models (confirmed list and spec)
| File name | Used in | Max tris | Textures (before optimize) | Materials | Final size (after optimize) | Required |
|---|---|---|---|---|---|---|
| `tuna.glb` | Products · Marine Fish | 30k | 1× 2048 albedo (+ optional 1024 normal) | 1 PBR: metallic 0.3–0.5 on back, roughness 0.35, silver belly | ≤ 1.5 MB (aim 0.3–0.8) | yes |
| `swordfish.glb` | Products · Marine Fish | 30k | 1× 2048 albedo (+ 1024 normal) | 1 PBR, long intact bill, dark back, silver belly | ≤ 1.5 MB (aim 0.3–0.8) | yes |
| `shrimp.glb` | Products · Shrimps | 30k | 1× 2048 albedo (+ 1024 normal) | 1 PBR, slightly translucent look via roughness 0.3 (no transmission, too costly) | ≤ 1.5 MB (aim 0.4–0.9) | yes |
| `globe.glb` | The world (scene 11) | 20k (UV sphere 128×64) | 1× 4096 daytime albedo (bright, NOT night lights) | 1 PBR, roughness 0.8, no emissive city lights | ≤ 1.5 MB | optional: recommended route is the **code-built globe** below |
| `reefer.glb` | Optional prop (documentation/port interlude or Products backdrop) | 8k | 1× 1024 | white painted metal, refrigeration unit on one end, no text/logos | ≤ 0.5 MB | optional |
Common rules: real-world scale in metres, +Y up, model centred on the origin, facing +X (head to the right), applied transforms, a single mesh per model where possible, one material, no cameras, no lights, no animation (motion is done in code). Named root node = file name (`tuna`, `swordfish`, `shrimp`, `globe`, `reefer`).

**Optional variant:** a "shrimp forms" set (HOSO, HLSO, PUD, PD tail-on…) can be added later as `shrimp_forms.glb` with one named node per form; the Products grid works with DOM cards without it.

## Option A: free models (fastest, recommended for Day 1)
Allowed licences: **CC0** (no attribution) or **CC-BY** (attribution line goes in the site footer "3D model credits"). Never use "Editorial", "NC" (non-commercial) or "ND" licences; this is a commercial site.
Where to look:
- Sketchfab → search "tuna", "swordfish", "shrimp" → Filters: *Downloadable* + Licence *CC0* or *CC Attribution* → download **glTF** (or .glb).
- Poly Haven (polyhaven.com, all CC0): HDRIs for lighting; few animals.
- NASA Visible Earth "Blue Marble" (public domain) for the globe texture: https://visibleearth.nasa.gov/collection/1484/blue-marble
- Existing drafts: the kohl repo (github.com/Tarunchintakunta/skylark-exim-cinematic) already has Blender-made `public/assets/models/products/tuna_hero.glb` (196 KB), `swordfish_hero.glb` (161 KB), `shrimp_product_forms.glb` (562 KB) and `containers/reefer_container.glb` (248 KB). They're Tarun's own work, so they're free to use as **placeholders** or finals if he likes them. Their globe (`export/globe_routes_from_india.glb`) is stylised/dark and has the routes baked in, so don't use it.
Record each download in `assets-src/models/LICENSES.md` (name, URL, author, licence).

## Option B: AI 3D generators (when no good free model exists)
Meshy, Tripo or Rodin: text or image → 3D. Prompt e.g. "photoreal yellowfin tuna, whole fish, side pose, closed mouth, accurate yellow finlets, PBR textures". Export GLB, then run it through the Blender clean-up steps below (they usually come out 100k–500k tris and need decimating). Check the tool's commercial-use terms on your plan.

## Option C: Blender, step by step (non-expert)
Blender 4.x or 5.x. Each step names the exact menu.
1. **Start clean.** File → New → General. Select the default cube, camera and light (A), press X → Delete.
2. **Import** the downloaded model: File → Import → glTF 2.0 (.glb/.gltf) (or FBX/OBJ for those formats).
3. **Scale and orient.** Press N to open the side panel. Check Dimensions: a tuna is ~1.5–2 m long, a swordfish ~2.5–3 m, a shrimp ~0.15–0.25 m (scale shrimp up ×5 so it reads; size is normalised in code anyway). Rotate so the head points to +X and the back is up. Then Object → Apply → All Transforms (Ctrl+A).
4. **One mesh.** If the model is many pieces: select all (A) → Object → Join (Ctrl+J). Object → Set Origin → Origin to Geometry, then Object → Snap → Selection to World Origin… (simpler: set Location to 0,0,0 in the N panel).
5. **Check triangle count.** Overlays menu (top-right of viewport) → tick *Statistics*. If Triangles > 30,000 (20,000 for the globe):
   Properties (wrench icon) → Add Modifier → Generate → **Decimate** → Collapse → lower *Ratio* until Triangles ≤ 30k (e.g. 0.2). Watch the silhouette (fins, bill, antennae) stays clean. Then click the modifier's ∨ menu → Apply.
6. **Smooth shading.** Object → Shade Auto Smooth (or Shade Smooth).
7. **Bake textures to one set (only if the model has several materials or procedural shaders).** Easiest: install the free "SimpleBake" add-on and bake Base Color (+ Normal) to one 2048 image. Manual way:
   a. Select the mesh → Edit Mode (Tab) → A → UV → Smart UV Project → Tab back.
   b. Shader Editor: in each material add an *Image Texture* node, click New → 2048×2048, name `bake_albedo`, leave it selected (don't connect it).
   c. Properties → Render → Render Engine: Cycles. Bake panel → Bake Type: Diffuse, untick Direct and Indirect (Color only) → Bake.
   d. Image Editor → Image → Save As → `tuna_albedo.png`.
   e. Delete the old materials, make one new Principled BSDF material, plug `tuna_albedo.png` into Base Color. Set Metallic/Roughness per the table above.
8. **Globe (if making the GLB):** Add → Mesh → UV Sphere (Segments 128, Rings 64, Radius 1). New material → Image Texture → open the NASA Blue Marble day JPG (4096×2048) → Base Color. Roughness 0.8. No clouds layer, no lights texture. Routes are **not** modelled (drawn in code).
9. **Export:** File → Export → glTF 2.0 (.glb/.gltf). Settings:
   - Format: **glTF Binary (.glb)**
   - Include: ☑ Selected Objects only (select your mesh first) · ☐ Cameras · ☐ Punctual Lights
   - Transform: ☑ +Y Up
   - Data → Mesh: ☑ Apply Modifiers · ☑ UVs · ☑ Normals · ☐ Vertex Colors (unless the model uses them, e.g. the kohl fish) · Data → Material: Export
   - Data → Compression: ☐ (leave **off**: Claude's script adds meshopt; Draco + meshopt together breaks)
   - Animation: ☐ off
   - Save as `assets-src/models/tuna.glb` (etc.).
10. **Check it:** drag the .glb onto https://gltf-viewer.donmccurdy.com: it should look right, face +X, sit centred. Then tell Claude it's there.

## What Claude does with them
```bash
scripts/optimize-glb.sh            # all of assets-src/models -> public/models (meshopt + WebP, 2048 max)
TEX=1024 scripts/optimize-glb.sh shrimp   # if over 1.5 MB
npx @gltf-transform/cli@4 inspect public/models/tuna.glb   # tris, texture sizes, bytes
```
In R3F: `useGLTF('/models/tuna.glb')` (drei sets up the meshopt decoder automatically for `EXT_meshopt_compression`), `useGLTF.preload` when the Products section is ≤ 1 viewport away, `<Suspense>` with the DOM card as fallback. KTX2 only if `KTX2=1` was used (then wire drei's KTX2 loader with the basis transcoder copied to `/basis/`).

## The globe: code-built (recommended) and how routes are drawn
- Mesh: `<sphereGeometry args={[1, 128, 64]} />` + `meshStandardMaterial` with `public/textures/earth_day_4096.webp` (2048 on mobile), roughness 0.85. Atmosphere: a second sphere at r = 1.025 with a fresnel ShaderMaterial (light sky-blue `#9fd3ff`, additive, back-side). Scene background is light (`#eef5f6` → `#dcebf0` gradient in CSS behind a transparent canvas). Lighting: `<Environment preset="city" />` (or a Poly Haven daylight HDRI at 1k) + one directional light from the upper left, intensity 2.5. The planet must read **bright daytime**.
- Routes are **never baked**: for each market, convert lat/lon (CONTENT.md table) to a Vector3 on r = 1, build a `QuadraticBezierCurve3` from Visakhapatnam with the control point at the midpoint normalised to r = 1 + 0.25·(arc length), sample 64 points, render with drei `<Line>` (Line2, width 2 px, colour brass `#d7a84f`, `transparent`). Animate draw-on by scrubbing a dash offset or `geometry.setDrawRange(0, n)` from the scroll timeline (no React state per frame). A small brass dot + pulsing ring marks each market when its arc lands; label is DOM (`<Html>` from drei, `occlude`), market names only.
- Camera: starts 1.15 r above the Bay of Bengal (the blue matches x-ship's last frame), pulls back to 3.2 r while the globe rotates from 83°E to show Europe → East Asia as arcs draw.
