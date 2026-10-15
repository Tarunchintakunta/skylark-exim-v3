#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
in="${1:?video.mp4}"; name="${2:-hero}"; nd="${3:-72}"; nm="${4:-60}"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
tmp=$(mktemp -d "${TMPDIR:-/tmp}/frames.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
set_frames() {
  local kind=$1 n=$2 vf=$3 budget=$4 out="public/sequence/$name/$1" q
  mkdir -p "$tmp/$kind" && rm -f "$tmp/$kind"/*.png
  ffmpeg -v error -y -i "$in" -vf "fps=$n/$dur,$vf" -frames:v "$n" "$tmp/$kind/${name}_%03d.png"
  for q in 78 74 70 66 62 58; do
    rm -rf "$out" && mkdir -p "$out"
    for f in "$tmp/$kind"/*.png; do cwebp -quiet -m 6 -q $q "$f" -o "$out/$(basename "${f%.png}").webp"; done
    local total max
    total=$(cat "$out"/*.webp | wc -c); max=$(for f in "$out"/*.webp; do wc -c < "$f"; done | sort -n | tail -1)
    if [ "$total" -le "$budget" ] && [ "$max" -le $((119 * 1024)) ]; then
      echo "$kind: $(ls "$out" | wc -l | tr -d ' ') frames, q $q, $((total / 1024)) KB total, largest $((max / 1024)) KB"
      return 0
    fi
  done
  echo "$kind: over budget even at q 58 ($((total / 1024)) KB)" >&2; return 1
}
set_frames desktop "$nd" "scale=1920:-2:flags=lanczos" $((${DESKTOP_KB:-5000} * 1000))
set_frames mobile "$nm" "crop=ih*9/16:ih,scale=1080:-2:flags=lanczos" $((${MOBILE_KB:-2800} * 1000))
