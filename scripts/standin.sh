#!/usr/bin/env bash
# Stand-in clips from an approved-for-review preview (RENDER_PIPELINE.md §2 "Stand-in rule"): the 960x540 preview
# frames of one .blend are split per clip (frame ranges from scripts/scenes.sh) and encoded with the normal
# encode/poster scripts, so the chapter shows the preview until the final render lands. Never used for finals.
# Usage: scripts/standin.sh <blend>      Env: TIERS (default "1920 1280 960", the names the site loads)
set -euo pipefail
cd "$(dirname "$0")/.."; source scripts/scenes.sh
b="${1:?blend}"; src="assets-src/render/preview/$b"; out="assets-src/video/preview"
mkdir -p "$out"
export TIERS="${TIERS:-1920 1280 960}"
ids=()
while read -r row; do
  IFS='|' read -r id _ F Lst _ <<<"$row"; n=$(( Lst - F + 1 ))
  ffmpeg -nostdin -v error -y -framerate 24 -start_number "$F" -i "$src/%04d.png" -frames:v "$n" -c:v libx264 -crf 14 -pix_fmt yuv420p "$out/$id.mp4"
  ids+=("$id")
done < <(blend_rows "$b")
FORCE=1 SRC="$out" scripts/encode-clips.sh "${ids[@]}"
SRC="$out" scripts/make-posters.sh "${ids[@]}"
