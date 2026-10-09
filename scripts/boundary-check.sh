#!/usr/bin/env bash
# Check that chained clips really share their boundary frame (last frame of A == first frame of B).
# Usage: scripts/boundary-check.sh            (all SHARED_JOINS from scenes.sh)
#        scripts/boundary-check.sh A B        (one pair)
# Compares the rendered PNGs (assets-src/render/<dir>/####.png) when they exist, else the 1080p masters.
# Pass = SSIM >= 0.99 on PNGs (0.97 on masters, which carry encode noise) -> the site swaps clips instantly.
# Fail -> fix the camera/objects/lighting of B's first frame (BOUNDARIES in SCENES.md), or set joinNext:'crossfade' and say so in the PR.
set -euo pipefail
cd "$(dirname "$0")/.."; source scripts/scenes.sh
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
pairs=(); if [ $# -eq 2 ]; then pairs=("$1>$2"); else pairs=("${SHARED_JOINS[@]}"); fi
fail=0
for p in "${pairs[@]}"; do
  a="${p%%>*}"; b="${p##*>}"
  ra=$(scene_row "$a") || { echo "unknown id $a"; exit 1; }; rb=$(scene_row "$b") || { echo "unknown id $b"; exit 1; }
  IFS='|' read -r _ ba _ la da <<<"$ra"; IFS='|' read -r _ bb fb _ db <<<"$rb"
  pa=$(printf "assets-src/render/%s/%04d.png" "$da" "$la"); pb=$(printf "assets-src/render/%s/%04d.png" "$db" "$fb")
  if [ -f "$pa" ] && [ -f "$pb" ]; then
    A="$pa"; B="$pb"; min=0.99; src=png
  elif [ -f "assets-src/video/$a.mp4" ] && [ -f "assets-src/video/$b.mp4" ]; then
    ffmpeg -v error -y -sseof -0.5 -i "assets-src/video/$a.mp4" -update 1 "$tmp/a.png"
    ffmpeg -v error -y -i "assets-src/video/$b.mp4" -frames:v 1 "$tmp/b.png"
    A="$tmp/a.png"; B="$tmp/b.png"; min=0.97; src=master
  else echo "skip  $a > $b (frames/masters missing)"; continue; fi
  s=$(ffmpeg -v info -i "$A" -i "$B" -lavfi ssim -f null - 2>&1 | grep -o 'All:[0-9.]*' | cut -d: -f2)
  same=""; [ "$ba" = "$bb" ] && same=" (same .blend, same frame)"
  if awk "BEGIN{exit !($s>=$min)}"; then echo "OK    $a > $b  SSIM $s [$src]$same"; else echo "FAIL  $a > $b  SSIM $s [$src] needs >= $min"; fail=1; fi
done
exit $fail
