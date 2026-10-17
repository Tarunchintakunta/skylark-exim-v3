#!/usr/bin/env bash
# Render one Blender scene headless (never inside an MCP call). Settings live in the .blend; preview overrides them.
# Usage: scripts/render-scene.sh <blend> preview|full [first last]
#   <blend> = o-catch (renders o-catch-a + o-catch-b) o-return p-ponds p-harvest truck-reverse p-intake p-proc p-lab p-iqf p-pack p-store p-docs port (renders x-cranes + x-ship)
#             prod-tuna prod-swordfish prod-shrimp (Products turntable fallback only)
#   preview -> 960x540, 16 samples, no motion blur -> assets-src/render/preview/<blend>/####.png + docs/renders/<blend>-preview.mp4
#   full    -> the .blend's saved settings (1920x1080, 24 fps)  -> assets-src/render/<dir>/####.png
#   first/last (optional) render a chunk only. Full renders skip frames that already exist (resume after a stop);
#   set FORCE=1 to re-render every frame after you changed the scene. Previews always re-render.
# Env: BLENDER=/path/to/Blender  FORCE=1  DRY=1 (print commands only)
set -euo pipefail
cd "$(dirname "$0")/.."; source scripts/scenes.sh
b="${1:?blend name}"; mode="${2:?preview|full}"
file="assets-src/blender/$b.blend"
[ -n "$(blend_rows "$b")" ] || { echo "unknown blend $b"; exit 1; }
read -r F L <<<"$(blend_range "$b")"; F="${3:-$F}"; L="${4:-$L}"
dir=$(blend_rows "$b" | head -1 | cut -d'|' -f5)
run(){ if [ "${DRY:-0}" = 1 ]; then echo "+ $*"; else "$@"; fi; }
[ "${DRY:-0}" = 1 ] || [ -f "$file" ] || { echo "missing $file"; exit 1; }
[ "${DRY:-0}" = 1 ] || [ -x "$BLENDER" ] || { echo "Blender not found at $BLENDER (set BLENDER=...)"; exit 1; }
keep=(); command -v caffeinate >/dev/null && keep=(caffeinate -i)   # macOS: stop the Mac sleeping mid-render
if [ "$mode" = preview ]; then
  out="assets-src/render/preview/$b"; [ $# -lt 3 ] && [ "${DRY:-0}" != 1 ] && rm -rf "$out"; mkdir -p "$out" docs/renders
  py="import bpy; s=bpy.context.scene; s.render.resolution_x=1920; s.render.resolution_y=1080; s.render.resolution_percentage=50; s.eevee.taa_render_samples=16; s.render.use_motion_blur=False; s.render.use_overwrite=True; s.render.image_settings.file_format='PNG'; s.render.filepath='$PWD/$out/'"
  run "${keep[@]}" "$BLENDER" -b "$file" --python-expr "$py" -s "$F" -e "$L" -a
  run ffmpeg -v error -y -framerate 24 -start_number "$F" -i "$out/%04d.png" -c:v libx264 -crf 26 -pix_fmt yuv420p -movflags +faststart "docs/renders/$b-preview.mp4"
  [ "${DRY:-0}" = 1 ] || echo "preview: docs/renders/$b-preview.mp4 ($(( $(stat -f%z "docs/renders/$b-preview.mp4" 2>/dev/null || stat -c%s "docs/renders/$b-preview.mp4") / 1024 )) KB, keep <= 4096 KB)"
elif [ "$mode" = full ]; then
  out="assets-src/render/$dir"; mkdir -p "$out"
  ow=False; [ "${FORCE:-0}" = 1 ] && ow=True
  py="import bpy; s=bpy.context.scene; s.render.use_overwrite=$ow; s.render.filepath='$PWD/$out/'"
  start=$(date +%s)
  run "${keep[@]}" "$BLENDER" -b "$file" --python-expr "$py" -s "$F" -e "$L" -a
  [ "${DRY:-0}" = 1 ] || echo "full render $b frames $F-$L done in $(( ($(date +%s)-start)/60 )) min -> $out"
else echo "mode must be preview or full"; exit 1; fi
