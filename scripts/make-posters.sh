#!/usr/bin/env bash
# First-frame posters per tier (poster -> video handoff is pixel-identical) + a last-frame poster for reverse scroll.
# assets-src/video/<id>.mp4 -> public/media/<id>_{1920,1280,960}.webp + <id>_end_1920.webp, each <= 120 KB.
# ffmpeg extracts PNG frames; cwebp encodes (this ffmpeg build has no libwebp), lowering quality until it fits.
# Usage: scripts/make-posters.sh [id ...]   Env: SRC, OUT, TIERS as in encode-clips.sh, END=1920 (end poster width)
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"; TIERS="${TIERS:-1920 1280 960}"; END="${END:-1920}"; MAX=120
command -v cwebp >/dev/null || { echo "cwebp not found (brew install webp)"; exit 1; }
mkdir -p "$OUT"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
webp(){ # webp <png> <out> <width>
  local q
  for q in 78 72 66 60 54 48 42; do
    cwebp -quiet -q $q -resize "$3" 0 "$1" -o "$2"
    [ "$(kb "$2")" -le $MAX ] && return 0
  done; echo "  ! $2 still over $MAX KB"; }
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id"; continue; }
  ffmpeg -v error -y -i "$in" -frames:v 1 "$tmp/first.png"
  ffmpeg -v error -y -sseof -0.1 -i "$in" -update 1 -frames:v 1 "$tmp/last.png"
  line="$id"
  for w in $TIERS; do webp "$tmp/first.png" "$OUT/${id}_${w}.webp" "$w"; line="$line  $w: $(kb "$OUT/${id}_${w}.webp") KB"; done
  webp "$tmp/last.png" "$OUT/${id}_end_$END.webp" "$END"
  echo "$line  end: $(kb "$OUT/${id}_end_$END.webp") KB"
done
