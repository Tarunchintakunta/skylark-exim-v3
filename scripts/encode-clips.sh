#!/usr/bin/env bash
# Encode scroll-scrub clips: assets-src/video/<id>.mp4 -> public/media/<id>_1280.mp4 + <id>_720.mp4 (+ optional AV1)
# Usage: scripts/encode-clips.sh [id ...]        (no ids = every mp4 in assets-src/video)
# Env:   SRC=assets-src/video OUT=public/media AV1=1 (also write <id>_1280.av1.webm) FORCE=1 (re-encode)
#        BUSY="a1 a2 ..." ids that get crf 30 + light denoise to stay under 1.5 MB
#        TRIM=8 (cap length in seconds; default 0 = keep full length)
set -euo pipefail
SRC="${SRC:-assets-src/video}"; OUT="${OUT:-public/media}"
BUSY=" ${BUSY:-a1 a2 a3 a4 b3 o-catch p-intake p-proc p-freeze x-cranes x-ship} "
TRIM="${TRIM:-0}"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found (brew/apt install ffmpeg)"; exit 1; }
mkdir -p "$OUT"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then for f in "$SRC"/*.mp4; do ids+=("$(basename "$f" .mp4)"); done; fi
X264="-c:v libx264 -preset slow -g 6 -keyint_min 6 -sc_threshold 0 -bf 0 -pix_fmt yuv420p -movflags +faststart"
for id in "${ids[@]}"; do
  in="$SRC/$id.mp4"; [ -f "$in" ] || { echo "skip $id: $in missing"; continue; }
  t=(); [ "$TRIM" != "0" ] && t=(-t "$TRIM")
  if [[ "$BUSY" == *" $id "* ]]; then crf=30; dn=",hqdn3d=1.5:1.5:4:4"; else crf=28; dn=""; fi
  d="$OUT/${id}_1280.mp4"; m="$OUT/${id}_720.mp4"
  if [ ! -f "$d" ] || [ "${FORCE:-0}" = 1 ]; then
    ffmpeg -v error -y -i "$in" "${t[@]}" -an -vf "scale=1280:-2$dn" $X264 -crf $crf "$d"; fi
  if [ ! -f "$m" ] || [ "${FORCE:-0}" = 1 ]; then
    ffmpeg -v error -y -i "$in" "${t[@]}" -an -vf "scale=720:-2$dn" $X264 -crf $crf "$m"; fi
  if [ "${AV1:-0}" = 1 ]; then
    a="$OUT/${id}_1280.av1.webm"
    if [ ! -f "$a" ] || [ "${FORCE:-0}" = 1 ]; then
      ffmpeg -v error -y -i "$in" "${t[@]}" -an -vf "scale=1280:-2$dn" -c:v libsvtav1 -crf 40 -preset 6 -g 6 -pix_fmt yuv420p "$a" 2> >(grep -v "^Svt" >&2); fi
  fi
  ds=$(( $(stat -c%s "$d" 2>/dev/null || stat -f%z "$d") / 1024 )); ms=$(( $(stat -c%s "$m" 2>/dev/null || stat -f%z "$m") / 1024 ))
  # budget scales with length: 1.5 MB desktop / 0.8 MB mobile per 8 s
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$d" | cut -d. -f1); [ -z "$dur" ] && dur=8
  bd=$(( 1536 * (dur>8?dur:8) / 8 )); bm=$(( 820 * (dur>8?dur:8) / 8 ))
  flag=""; [ $ds -gt $bd ] && flag="  !! desktop over ${bd} KB budget: add id to BUSY or TRIM=8"
  [ $ms -gt $bm ] && flag="$flag  !! mobile over ${bm} KB budget"
  echo "$id  crf=$crf  1280: ${ds} KB  720: ${ms} KB$flag"
done
