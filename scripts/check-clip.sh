#!/usr/bin/env bash
# Quality gate for an encoded clip: length, keyframe spacing (GOP 8, no B-frames), brightness (never dark), size budget.
# Usage: scripts/check-clip.sh <id> [id ...]   reads assets-src/video/<id>.mp4 and public/media/<id>_{1920,1280,960}.mp4
# Brightness floor (mean luma YAVG of the master): 85 daylight exteriors, 70 interiors, 55 x-ship (deep blue sea).
# Size targets per 8 s (redesign prompt §2.6): 1920 <= 2.5 MB, 960 <= 0.9 MB (scaled by clip length).
set -euo pipefail
cd "$(dirname "$0")/.."
floor(){ case "$1" in x-ship) echo 55;; p-intake|p-proc|p-lab|p-iqf|p-pack|p-store|p-docs) echo 70;; prod-*) echo 140;; *) echo 85;; esac; }
kb(){ echo $(( $(stat -f%z "$1" 2>/dev/null || stat -c%s "$1") / 1024 )); }
rc=0
for id in "$@"; do
  m="assets-src/video/$id.mp4"
  [ -f "$m" ] || { echo "$id: master missing"; rc=1; continue; }
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$m")
  read -r y ymin < <(ffmpeg -v error -i "$m" -vf "scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - | awk -F= '/YAVG/{s+=$2;n++; if(min==""||$2<min)min=$2} END{printf "%.0f %.0f\n", s/n, min}')
  line="$id  ${dur%.*}s  luma avg $y min $ymin (floor $(floor "$id"))"
  [ "$y" -lt "$(floor "$id")" ] && { line="$line  !! too dark"; rc=1; }
  sec=$(awk "BEGIN{x=$dur; if(x<8)x=8; print x}")
  for spec in "1920 2560" "1280 1600" "960 920"; do
    set -- $spec; w=$1; per8=$2; f="public/media/${id}_${w}.mp4"
    [ -f "$f" ] || { line="$line  $w: not encoded"; continue; }
    cap=$(awk "BEGIN{printf \"%d\", $per8*$sec/8}")
    line="$line  $w: $(kb "$f") KB (target $cap)"
    [ "$(kb "$f")" -gt "$cap" ] && line="$line !"
    if [ "$w" = 1920 ]; then
      gop=$(ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -read_intervals "%+#24" -of csv=p=0 "$f" | tr -d ',\n')
      line="$line  frames $gop"
      echo "$gop" | grep -q B && { line="$line  !! B-frames"; rc=1; }
    fi
  done
  echo "$line"
done
exit $rc
