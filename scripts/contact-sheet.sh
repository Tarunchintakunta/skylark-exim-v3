#!/usr/bin/env bash
# 6-frame self-review contact sheet (3x2, evenly spaced) from a scene's preview frames.
# Usage: scripts/contact-sheet.sh <blend> <out.jpg>      (frames from assets-src/render/preview/<blend>/)
set -euo pipefail
cd "$(dirname "$0")/.."; source scripts/scenes.sh
b="${1:?blend}"; out="${2:?out.jpg}"; src="assets-src/render/preview/$b"
read -r F L <<<"$(blend_range "$b")"
args=(); for k in 0 1 2 3 4 5; do args+=(-i "$(printf "%s/%04d.png" "$src" $(( F + (L - F) * k / 5 )))"); done
ffmpeg -nostdin -v error -y "${args[@]}" \
  -filter_complex "[0][1][2]hstack=3[a];[3][4][5]hstack=3[b];[a][b]vstack,scale=1920:-2" -q:v 3 "$out"
echo "$out (frames $F..$L, 6 evenly spaced)"
