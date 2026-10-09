#!/usr/bin/env bash
# Full-scroll media weight per story path from public/ (clips + posters + globe texture + product GLBs). JS/CSS/fonts not included.
# Usage: scripts/path-weight.sh            Budgets (ASSETS_SPEC.md): desktop <= 25 MB, mobile <= 12 MB per path incl. ~0.7 MB JS/CSS/fonts.
set -euo pipefail
cd "$(dirname "$0")/.."
OCEAN="opening a1 a2 o-catch-a o-catch-b o-return truck-reverse p-intake p-proc p-freeze x-cranes x-ship"
POND="opening p-ponds b2 p-harvest truck-reverse p-intake p-proc p-freeze x-cranes x-ship"
MODELS="tuna swordfish shrimp carton ice-tray"
TURNTABLES="prod-tuna prod-swordfish prod-shrimp"   # only exist if the Products fallback is used (counted when present)
sz(){ [ -f "$1" ] && (stat -f%z "$1" 2>/dev/null || stat -c%s "$1") || echo 0; }
for path in OCEAN POND; do
  for dev in 1920 960; do
    t=0; miss=""
    for id in ${!path}; do
      c=$(sz "public/media/${id}_${dev}.mp4"); [ "$c" = 0 ] && miss="$miss $id"
      t=$(( t + c + $(sz "public/media/${id}_${dev}.webp") + $(sz "public/media/${id}_end_1920.webp") ))
    done
    tex=public/textures/earth_day_4096.webp; [ $dev = 960 ] && tex=public/textures/earth_day_2048.webp
    t=$(( t + $(sz $tex) )); for m in $MODELS; do t=$(( t + $(sz "public/models/$m.glb") )); done
    for m in $TURNTABLES; do t=$(( t + $(sz "public/media/${m}_${dev}.mp4") + $(sz "public/media/${m}_${dev}.webp") )); done
    t=$(( t + 734003 ))   # ~0.7 MB JS/CSS/fonts allowance
    cap=26214400; [ $dev = 960 ] && cap=12582912
    flag=""; [ $t -gt $cap ] && flag="  !! over budget"
    echo "$path $( [ $dev = 1920 ] && echo desktop || echo mobile ): $(awk "BEGIN{printf \"%.1f\", $t/1048576}") MB of $(( cap/1048576 )) MB$flag${miss:+  (missing:$miss)}"
  done
done
