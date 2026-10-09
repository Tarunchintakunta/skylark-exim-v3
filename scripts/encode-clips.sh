#!/usr/bin/env bash
# Encode scroll-scrub clips: assets-src/video/<id>.mp4 (1080p master) -> public/media/<id>_{1920,1280,960}.mp4
# Redesign prompt §2.6: H.264 High, GOP 8, no B-frames, faststart, no audio; capped CRF so a clip never exceeds the
# tier budget (<= 2.5 MB / 8 s at 1920, <= 0.9 MB / 8 s at 960): -crf 23 -maxrate R -bufsize R per tier.
# Usage: scripts/encode-clips.sh [id ...]        (no ids = every mp4 in assets-src/video)
# Env:   SRC=assets-src/video OUT=public/media FORCE=1 (re-encode) CRF=23 TIERS="1920 1280 960"
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"; CRF="${CRF:-23}"; TIERS="${TIERS:-1920 1280 960}"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }
mkdir -p "$OUT"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
rate(){ case "$1" in 1920) echo 2500k;; 1280) echo 1500k;; 960) echo 900k;; *) echo 700k;; esac; }
X264="-c:v libx264 -profile:v high -preset slow -g 8 -keyint_min 8 -bf 0 -sc_threshold 0 -pix_fmt yuv420p -movflags +faststart -an"
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id: $in missing"; continue; }
  line="$id"
  for w in $TIERS; do
    o="$OUT/${id}_${w}.mp4"; r=$(rate "$w")
    if [ ! -f "$o" ] || [ "${FORCE:-0}" = 1 ]; then
      ffmpeg -v error -y -i "$in" -vf "scale=$w:-2:flags=lanczos" $X264 -crf "$CRF" -maxrate "$r" -bufsize "$r" "$o"; fi
    line="$line  $w: $(kb "$o") KB"
  done
  echo "$line"
done
