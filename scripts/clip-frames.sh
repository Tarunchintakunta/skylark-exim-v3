#!/usr/bin/env bash
# Frame sequences for the /story clips that play on the canvas instead of a <video> (#hd2, src/config/chapters.ts SEQ):
# fast camera moves macroblock in video at any byte rate a path can afford, a still frame per position does not (the
# Terminal Industries pattern, already used for the hero: src/film/sequence.ts). Every master frame, so the clip keeps
# its exact frame count and timing.
#   scripts/clip-frames.sh <id>...
# -> public/media/<id>-f_1920_NNN.avif, and a WebP set (.webp, q 75) for a browser without AVIF. Every desktop tier
#    draws the 1920 set: a 2560 set (crf 38, 88 KB a frame) cost the five port clips 25.4 MB of the 60 MB desktop path
#    and left the other 17 clips 1.3 MB each at 2560, less than before the HD pass; the 1920 set is 20.8 MB at crf 36 and ~17 MB at crf 39, which leaves room to keep every other clip at least at its old 2560 bytes. Phones keep
#    the clip's video (chapters.ts SEQ_CLIPS). AVIF (SVT-AV1 still) because on an hf-port-4 frame at 2560 crf 34 is
#    96 KB at SSIM 0.985 where WebP needs q 80 and 184 KB for the same SSIM. crf 39; cap per frame 150 KB, a frame
#    over it steps AVIF crf up by 3 (to 47), WebP q down by 5 (to 55).
set -euo pipefail
cd "$(dirname "$0")/.."
for id in "$@"; do
  in="masters/$id/master.mp4"
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/cf.XXXXXX")
  rm -f public/media/"$id"-f_*.webp public/media/"$id"-f_*.avif
  line="$id:"
  for tier in 1920; do
    vf=scale=1920:1080:flags=lanczos; crf="39 42 45 47"; cap=150
    mkdir -p "$tmp/$tier"
    ffmpeg -nostdin -v error -y -i "$in" -vf "$vf" -start_number 0 "$tmp/$tier/%03d.png"
    for ext in avif webp; do
      total=0; max=0; n=0
      for f in "$tmp/$tier"/*.png; do
        out="public/media/$id-f_${tier}_$(basename "${f%.png}").$ext"
        for q in $([ $ext = avif ] && echo $crf || echo 75 70 65 60 55); do
          if [ $ext = avif ]; then
            ffmpeg -nostdin -v error -y -i "$f" -vf format=yuv420p -c:v libsvtav1 -preset 6 -crf $q -frames:v 1 "$out" 2>&1 | grep -v '^Svt' || true
          else cwebp -quiet -m 6 -q $q "$f" -o "$out"; fi
          [ "$(stat -f%z "$out")" -le $((cap * 1024)) ] && break
        done
        s=$(stat -f%z "$out"); total=$((total + s)); [ $s -gt $max ] && max=$s; n=$((n + 1))
      done
      line="$line  $tier.$ext $n frames $((total / 1024)) KB (largest $((max / 1024)))"
    done
  done
  echo "$line"
  rm -rf "$tmp"
done
