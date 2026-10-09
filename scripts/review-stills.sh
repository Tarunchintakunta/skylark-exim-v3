#!/usr/bin/env bash
# Review stills for a scene PR from its preview frames: docs/renders/<blend>-fNNN.png for the given frames and a
# 3-frame strip (first, middle, last of the .blend's range) docs/renders/<blend>-strip.jpg.
# Usage: scripts/review-stills.sh <blend> <frame> [frame ...]
set -euo pipefail
cd "$(dirname "$0")/.."; source scripts/scenes.sh
b="${1:?blend}"; shift
src="assets-src/render/preview/$b"
read -r F L <<<"$(blend_range "$b")"
for f in "$@"; do cp "$(printf "%s/%04d.png" "$src" "$f")" "$(printf "docs/renders/%s-f%03d.png" "$b" "$f")"; done
M=$(( (F + L) / 2 ))
ffmpeg -v error -y -i "$(printf "%s/%04d.png" "$src" "$F")" -i "$(printf "%s/%04d.png" "$src" "$M")" -i "$(printf "%s/%04d.png" "$src" "$L")" \
  -filter_complex "hstack=inputs=3" -q:v 3 "docs/renders/$b-strip.jpg"
echo "docs/renders/$b-strip.jpg (frames $F, $M, $L)"
