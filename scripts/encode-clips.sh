#!/usr/bin/env bash
# Encode scroll-scrub clips: assets-src/video/<id>.mp4 (1080p master) -> public/media/<id>_{1920,1280,960}.mp4
# Tiers and settings per the redesign prompt §2.6: H.264 High, GOP 8, no B-frames, crf 22, faststart, no audio.
# Usage: scripts/encode-clips.sh [id ...]        (no ids = every mp4 in assets-src/video)
# Env:   SRC=assets-src/video OUT=public/media FORCE=1 (re-encode) CRF=22 (all tiers) MCRF=0 (added to the 960 tier only)
#        TIERS="1920 1280 960"
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"; CRF="${CRF:-22}"; TIERS="${TIERS:-1920 1280 960}"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }
mkdir -p "$OUT"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
X264="-c:v libx264 -profile:v high -preset slow -g 8 -keyint_min 8 -bf 0 -sc_threshold 0 -pix_fmt yuv420p -movflags +faststart -an"
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id: $in missing"; continue; }
  line="$id"
  for w in $TIERS; do
    o="$OUT/${id}_${w}.mp4"; crf=$CRF; [ "$w" = 960 ] && crf=$(( CRF + ${MCRF:-0} ))
    if [ ! -f "$o" ] || [ "${FORCE:-0}" = 1 ]; then
      ffmpeg -v error -y -i "$in" -vf "scale=$w:-2:flags=lanczos" $X264 -crf "$crf" "$o"; fi
    line="$line  $w: $(kb "$o") KB"
  done
  echo "$line"
done
