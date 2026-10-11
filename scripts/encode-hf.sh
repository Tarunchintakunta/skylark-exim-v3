#!/usr/bin/env bash
# Encode a Higgsfield master into the scrub tiers + posters (docs/HIGGSFIELD_STORYBOARD.md).
#   scripts/encode-hf.sh <master.mp4> <id>
# -> public/media/<id>_{1920,1280,960,720}.mp4  H.264 High, two-pass, GOP 6, no B-frames, faststart, no audio, 24 fps
#    public/media/<id>_{1920,1280,960}.webp + <id>_720.webp   first-frame posters (<= 120 KB, cwebp)
#    public/media/<id>_end_1920.webp                          last-frame poster (reverse scroll)
#    public/media/<id>_1920.avif                              first-frame AVIF poster (libsvtav1)
# Size caps per tier (KB): 1920 2200 · 1280 1400 · 960 850 · 720 550 (hard cap 2300 at 1920). The bitrate is derived
# from the cap and the clip length; a tier that still lands over its cap is re-encoded at 90 % until it fits.
set -euo pipefail
cd "$(dirname "$0")/.."
in="$(cd "$(dirname "${1:?master}")" && pwd)/$(basename "$1")"; id="${2:?id}"; OUT="${OUT:-public/media}"; mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
cap(){ case "$1" in 1920) echo 2200;; 1280) echo 1400;; 960) echo 850;; *) echo 550;; esac; }
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
X="-c:v libx264 -profile:v high -preset slower -tune film -g 6 -keyint_min 6 -sc_threshold 0 -bf 0 -pix_fmt yuv420p -r 24 -an"
line="$id"
for w in 1920 1280 960 720; do
  o="$OUT/${id}_${w}.mp4"; c=$(cap "$w"); f=100
  while :; do
    br=$(awk -v c="$c" -v d="$dur" -v f="$f" 'BEGIN{printf "%d", c*8*1.024*0.97*f/100/d}')   # kbit/s, 3 % container headroom
    ( cd "$tmp" && ffmpeg -v error -y -i "$in" -vf "scale=$w:-2:flags=lanczos" $X -b:v ${br}k -pass 1 -f null - &&
      ffmpeg -v error -y -i "$in" -vf "scale=$w:-2:flags=lanczos" $X -b:v ${br}k -maxrate $((br*2))k -bufsize $((br*2))k -pass 2 -movflags +faststart "$o" )
    [ "$(kb "$o")" -le "$c" ] && break; f=$((f-10))
  done
  line="$line  $w: $(kb "$o") KB (${br}k)"
done
ffmpeg -v error -y -i "$in" -frames:v 1 "$tmp/first.png"
ffmpeg -v error -y -sseof -0.1 -i "$in" -update 1 -frames:v 1 "$tmp/last.png"
webp(){ local q; for q in 78 70 62 54 46 38 30; do cwebp -quiet -m 6 -q $q -resize "$3" 0 "$1" -o "$2"; [ "$(kb "$2")" -le 120 ] && return 0; done; echo "  ! $2 over 120 KB"; }
for w in 1920 1280 960 720; do webp "$tmp/first.png" "$OUT/${id}_${w}.webp" $w; done
webp "$tmp/last.png" "$OUT/${id}_end_1920.webp" 1920
ffmpeg -v error -y -i "$tmp/first.png" -vf scale=1920:-2 -c:v libsvtav1 -crf 50 -frames:v 1 "$OUT/${id}_1920.avif" 2> >(grep -v '^Svt' >&2)
echo "$line  webp1920: $(kb "$OUT/${id}_1920.webp") KB  avif: $(kb "$OUT/${id}_1920.avif") KB  end: $(kb "$OUT/${id}_end_1920.webp") KB"
