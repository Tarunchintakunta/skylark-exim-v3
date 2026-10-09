# Third-party assets used in the Blender scenes

All external assets are **CC0 (public domain)**: no attribution is required, no credit line is needed in the site footer.
Files live in the git-ignored `assets-src/cc0/` folder (downloaded with Tarun's approval) and are only baked into the
rendered clips; none of them is shipped as a separate file.

| Asset | Source | Licence | Used in |
|---|---|---|---|
| Human Base Meshes bundle v1.4.1 (`GEO-body_male_realistic`, `GEO-body_female_realistic`) | Blender Foundation, download.blender.org/demo/asset-bundles/human-base-meshes/ | CC0 | every person in every scene (`blender/sklib.py` `person()`) |
| HDRI `kloofendal_48d_partly_cloudy_puresky` (4k) | Poly Haven, polyhaven.com | CC0 | o-catch, port (x-cranes, x-ship), asset-library stills |
| HDRI `qwantani_mid_morning_puresky` (4k) | Poly Haven, polyhaven.com | CC0 | o-return |
| Textures `rubber_tiles`, `concrete_floor_02`, `asphalt_02`, `rust_coarse_01`, `container_side`, `corrugated_iron_02` (2k) | Poly Haven, polyhaven.com | CC0 | shared materials (`textured_overrides()` in `blender/sklib.py`) |
| Textures `Rubber004`, `Metal009`, `PaintedMetal004`, `Fabric030` (2K-JPG) | ambientCG, ambientcg.com | CC0 | shared materials (`textured_overrides()` in `blender/sklib.py`) |

No brand names, logos, lettering or numbers from any source appear in the renders.
