#!/usr/bin/env bash
# Image sequence against video, measured on the real masters (#264 step 3). For one clip and tier, extracts frames at
# FPS from masters/<id>/master.mp4, encodes each frame as AVIF (SVT-AV1 crf 25 ≈ libavif q 60) and WebP q 78, and
# prints the sequence's total bytes beside the clip's own AV1 file, so each chapter's decision is a measurement.
#   scripts/seq-bench.sh <out.tsv> <fps> <tier …>        tiers: 810 (phone crop), 1920, 2560
#   IDS="hf-catch hf-store" scripts/seq-bench.sh seq.tsv 12 1920
# Columns: id, tier, fps, frames, avif bytes, webp bytes, av1 clip bytes, avif ÷ clip.
set -uo pipefail
cd "$(dirname "$0")/.."
out="${1:?out.tsv}"; fps="${2:?fps}"; shift 2
tiers=("$@"); [ ${#tiers[@]} -gt 0 ] || tiers=(1920)
ids=${IDS:-$(cd masters && ls -d */ | tr -d /)}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/seqbench.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
: > "$out"
for id in $ids; do
  src="masters/$id/master.mp4"
  [ -f "$src" ] || { echo "! $id: no master" >&2; continue; }
  # the phone crop uses the same centre as the _m clips (src/config/chapters.ts CROP_X)
  cx=$(node --import tsx --input-type=module -e "const { CROP_X } = await import('./src/config/chapters.ts'); console.log(CROP_X['$id'] ?? 0.5)")
  x=$(awk -v c="$cx" 'BEGIN{x=int(c*2560-405); if(x<0)x=0; if(x>1750)x=1750; print x - x%2}')
  for tier in "${tiers[@]}"; do
    d="$tmp/$id-$tier"; rm -rf "$d"; mkdir -p "$d"
    case $tier in 810) vf="crop=810:1440:$x:0";; 2560) vf="null";; *) vf="scale=$tier:-2:flags=lanczos";; esac
    ffmpeg -nostdin -v error -y -i "$src" -vf "fps=$fps,$vf" "$d/%03d.png"
    for f in "$d"/*.png; do
      ffmpeg -nostdin -v error -y -i "$f" -vf format=yuv420p -c:v libsvtav1 -preset 8 -crf 25 -frames:v 1 "${f%.png}.avif"
      cwebp -quiet -q 78 -m 6 "$f" -o "${f%.png}.webp"
    done
    n=$(ls "$d"/*.png | wc -l | tr -d ' ')
    a=$(cat "$d"/*.avif | wc -c | tr -d ' ')
    w=$(cat "$d"/*.webp | wc -c | tr -d ' ')
    clip="public/media/${id}_$([ "$tier" = 810 ] && echo m || echo "$tier").av1.mp4"
    v=$([ -f "$clip" ] && stat -f%z "$clip" || echo 0)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$tier" "$fps" "$n" "$a" "$w" "$v" \
      "$(awk -v a="$a" -v v="$v" 'BEGIN{printf (v?"%.1f":"-"), a/v}')" >> "$out"
    tail -1 "$out"
  done
done
