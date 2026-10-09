#!/usr/bin/env bash
# Optimise Blender exports: assets-src/models/<name>.glb -> public/models/<name>.glb (meshopt + WebP textures)
# Usage: scripts/optimize-glb.sh [name ...]   Env: SRC=assets-src/models OUT=public/models TEX=2048 KTX2=1 (needs toktx)
set -euo pipefail
SRC="${SRC:-assets-src/models}"; OUT="${OUT:-public/models}"; TEX="${TEX:-2048}"
GT="npx --yes @gltf-transform/cli@4"
mkdir -p "$OUT"
names=("$@")
if [ ${#names[@]} -eq 0 ]; then for f in "$SRC"/*.glb; do names+=("$(basename "$f" .glb)"); done; fi
for n in "${names[@]}"; do
  in="$SRC/$n.glb"; o="$OUT/$n.glb"; [ -f "$in" ] || { echo "skip $n"; continue; }
  tc=webp; [ "${KTX2:-0}" = 1 ] && tc=ktx2
  $GT optimize "$in" "$o" --compress meshopt --texture-compress $tc --texture-size "$TEX" >/dev/null
  kb=$(( $(stat -c%s "$o" 2>/dev/null || stat -f%z "$o") / 1024 ))
  flag=""; [ $kb -gt 500 ] && flag="  ! over 500 KB target: re-run with TEX=1024 or decimate in Blender"
  [ $kb -gt 1536 ] && flag="  !! over 1.5 MB hard cap: re-run with TEX=1024 or decimate in Blender"
  echo "$n  $(( $(stat -c%s "$in" 2>/dev/null || stat -f%z "$in") / 1024 )) KB -> ${kb} KB$flag"
done
