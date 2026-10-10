#!/usr/bin/env bash
# Single source of truth for the Blender scenes (sourced by the other scripts). Matches SCENES.md.
# Row: clip id | .blend name in assets-src/blender/ | first frame | last frame | render dir in assets-src/render/
# Two-shot blends render one continuous timeline split into two clips that share the boundary frame:
#   o-catch.blend -> o-catch-a (haul, 1-192) + o-catch-b (deck sort + hold, 192-383), frame 192 shared
#   port.blend    -> x-cranes (1-288) + x-ship (288-479), frame 288 shared
SCENES=(
  "opening|opening|1|192|opening"
  "o-catch-a|o-catch|1|192|o-catch"
  "o-catch-b|o-catch|192|383|o-catch"
  "o-return|o-return|1|288|o-return"
  "p-ponds|p-ponds|1|192|p-ponds"
  "p-harvest|p-harvest|1|288|p-harvest"
  "truck-reverse|truck-reverse|1|288|truck-reverse"
  "p-intake|p-intake|1|192|p-intake"
  "p-proc|p-proc|1|288|p-proc"
  "p-freeze|p-freeze|1|288|p-freeze"
  "x-cranes|port|1|288|port"
  "x-ship|port|288|479|port"
  # Products fallback only (PRODUCTS rule in ASSET_LIBRARY.md): 360-degree turntables on the ice bed, used if a photoreal GLB can't stay <= 500 KB
  "prod-tuna|prod-tuna|1|120|prod-tuna"
  "prod-swordfish|prod-swordfish|1|120|prod-swordfish"
  "prod-shrimp|prod-shrimp|1|120|prod-shrimp"
)
# Joins where the boundary frame must be shared (checked by scripts/boundary-check.sh)
SHARED_JOINS=("o-catch-a>o-catch-b" "truck-reverse>p-intake" "p-intake>p-proc" "p-proc>p-freeze" "x-cranes>x-ship")
# Joins the site cross-fades (different places or a reused Higgsfield clip on one side)
CROSSFADE_JOINS=("a2>o-catch-a" "o-catch-b>o-return" "o-return>truck-reverse" "p-ponds>b2" "b2>p-harvest" "p-harvest>truck-reverse" "x-ship>globe")
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
scene_row(){ local r; for r in "${SCENES[@]}"; do [ "${r%%|*}" = "$1" ] && { echo "$r"; return 0; }; done; return 1; }
blend_rows(){ local r i b f l d; for r in "${SCENES[@]}"; do IFS='|' read -r i b f l d <<<"$r"; if [ "$b" = "$1" ]; then echo "$r"; fi; done; return 0; }
blend_range(){ # prints "first last" across all clips of one .blend
  local lo=999999 hi=0 r i b f l d; while read -r r; do IFS='|' read -r i b f l d <<<"$r"; if [ "$f" -lt "$lo" ]; then lo=$f; fi; if [ "$l" -gt "$hi" ]; then hi=$l; fi; done < <(blend_rows "$1"); echo "$lo $hi"; }
