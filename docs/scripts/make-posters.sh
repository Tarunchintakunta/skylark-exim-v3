#!/usr/bin/env bash
# First-frame posters (so poster -> video handoff is pixel-identical) + last-frame posters for reverse scroll.
# assets-src/video/<id>.mp4 -> public/media/<id>_1280.webp, <id>_720.webp, <id>_end_1280.webp
# Usage: scripts/make-posters.sh [id ...]   Env: SRC, OUT as in encode-clips.sh
set -euo pipefail
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"
mkdir -p "$OUT"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
size(){ echo $(( $(stat -c%s "$1" 2>/dev/null || stat -f%z "$1") / 1024 )); }
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id"; continue; }
  for spec in "1280 72 80" "720 70 40"; do
    set -- $spec; w=$1; q=$2; max=$3; o="$OUT/${id}_${w}.webp"
    ffmpeg -v error -y -i "$in" -frames:v 1 -vf "scale=$w:-2" -c:v libwebp -quality $q "$o"
    [ "$(size "$o")" -gt $max ] && ffmpeg -v error -y -i "$in" -frames:v 1 -vf "scale=$w:-2" -c:v libwebp -quality 60 "$o"
  done
  # last frame (used when the user scrolls back up into a clip)
  ffmpeg -v error -y -sseof -0.1 -i "$in" -update 1 -frames:v 1 -vf "scale=1280:-2" -c:v libwebp -quality 70 "$OUT/${id}_end_1280.webp"
  echo "$id  poster1280: $(size "$OUT/${id}_1280.webp") KB  poster720: $(size "$OUT/${id}_720.webp") KB  end: $(size "$OUT/${id}_end_1280.webp") KB"
done
