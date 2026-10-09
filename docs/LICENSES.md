# Third-party assets used in the Blender scenes

Most external assets are **CC0 (public domain)**. The tuna and prawn scans are **CC BY 4.0** and need the credit
line at the end of this file in the site footer.
Files live in the git-ignored `assets-src/cc0/` folder (downloaded with Tarun's approval) and are only baked into the
rendered clips; none of them is shipped as a separate file.

| Asset | Source | Licence | Used in |
|---|---|---|---|
| Human Base Meshes bundle v1.4.1 (`GEO-body_male_realistic`, `GEO-body_female_realistic`) | Blender Foundation, download.blender.org/demo/asset-bundles/human-base-meshes/ | CC0 | every person in every scene (`blender/sklib.py` `person()`) |
| HDRI `kloofendal_48d_partly_cloudy_puresky` (4k) | Poly Haven, polyhaven.com | CC0 | o-catch, port (x-cranes, x-ship), asset-library stills |
| HDRI `qwantani_mid_morning_puresky` (4k) | Poly Haven, polyhaven.com | CC0 | o-return |
| Textures `rubber_tiles`, `concrete_floor_02`, `asphalt_02`, `rust_coarse_01`, `container_side`, `corrugated_iron_02` (2k) | Poly Haven, polyhaven.com | CC0 | shared materials (`textured_overrides()` in `blender/sklib.py`) |
| Textures `Rubber004`, `Metal009`, `PaintedMetal004`, `Fabric030` (2K-JPG) | ambientCG, ambientcg.com | CC0 | shared materials (`textured_overrides()` in `blender/sklib.py`) |
| Texture `aerial_grass_rock` (2k) | Poly Haven, polyhaven.com | CC0 | land in the port top-down end |
| Scan "Yellowfin Tuna, Thunnus albacares" (`tuna-yellowfin-ffish.glb`) | ffish.asia / floraZia.com, https://sketchfab.com/3d-models/yellowfin-tuna-thunnus-albacares-d4eeea976932414d91fc786ce6cec547 | CC BY 4.0 | tuna in o-catch (spill, bag, crates), tuna product turntable (`blender/prep_scans.py`) |
| Scan "Green tiger prawn, Penaeus semisulcatus" (`shrimp-green-tiger-ffish.glb`) | ffish.asia / floraZia.com, https://sketchfab.com/3d-models/green-tiger-prawn-penaeus-semisulcatus-af273265e0324bc4a645ebad96c254df | CC BY 4.0 | prawn product turntable (`blender/prep_scans.py`) |

### CC BY 4.0 (credit required; approved by Tarun with a credit line in the site footer)

| Asset | Author | Source | Licence | Used in |
|---|---|---|---|---|
| "Green tiger prawn, Penaeus semisulcatus" 3D scan | ffish.asia / floraZia.com | sketchfab.com/3d-models/green-tiger-prawn-penaeus-semisulcatus-af273265e0324bc4a645ebad96c254df | CC BY 4.0 | shrimp in the p-harvest crates and net bag and on the plant-chain belts and crates (`blender/skscan.py`, decimated and relit) |
| "Yellowfin tuna, Thunnus albacares" 3D scan | ffish.asia / floraZia.com | sketchfab.com/3d-models/yellowfin-tuna-thunnus-albacares-d4eeea976932414d91fc786ce6cec547 | CC BY 4.0 | whole fish on ice in the p-intake, p-proc and coldchain scenes (`blender/plant_chain.py`, scaled per species and relit) |

No brand names, logos, lettering or numbers from any source appear in the renders.

Footer credit (CC BY 4.0): *Tuna and prawn 3D scans by ffish.asia / floraZia.com, licensed CC BY 4.0.*
