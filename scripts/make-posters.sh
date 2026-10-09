#!/usr/bin/env bash
# First-frame posters per tier (poster -> video handoff is pixel-identical) + a last-frame poster for reverse scroll.
# assets-src/video/<id>.mp4 -> public/media/<id>_{1920,1280,960}.webp + <id>_end_1920.webp, each <= 120 KB
# Usage: scripts/make-posters.sh [id ...]   Env: SRC, OUT, TIERS as in encode-clips.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"; TIERS="${TIERS:-1920 1280 960}"; MAX=120
mkdir -p "$OUT"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
# webp <input args...> -- <out> <width>: lowers quality until the file fits MAX KB
webp(){ local o="${@: -2:1}" w="${@: -1}" q; local args=("${@:1:$#-2}")
  for q in 80 72 64 56 48 40; do
    ffmpeg -v error -y "${args[@]}" -frames:v 1 -vf "scale=$w:-2:flags=lanczos" -c:v libwebp -quality $q "$o"
    [ "$(kb "$o")" -le $MAX ] && return 0
  done; echo "  ! $o still over $MAX KB"; }
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id"; continue; }
  line="$id"
  for w in $TIERS; do webp -i "$in" "$OUT/${id}_${w}.webp" "$w"; line="$line  $w: $(kb "$OUT/${id}_${w}.webp") KB"; done
  webp -sseof -0.1 -i "$in" "$OUT/${id}_end_1920.webp" 1920
  echo "$line  end: $(kb "$OUT/${id}_end_1920.webp") KB"
done
