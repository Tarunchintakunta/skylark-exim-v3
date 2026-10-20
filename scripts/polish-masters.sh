#!/usr/bin/env bash
# Masters changed in the final polish pass (no new footage, no Higgsfield, no Blender renders), for scripts/encode-hf.sh.
#   scripts/polish-masters.sh            HD=<hd-masters> (default below)
# - hf-arrive, hf-reverse: mirrored. The truck came in left-hand drive; mirrored, the driver sits on the right, as on
#   an Indian road. Neither shot has readable text (no plates, no lettering on the cab or the dock).
# - hf-ship: cropped to the lower right of the frame (1176x662 at 1384,778, scaled back to 2560), below the tug that
#   pushed the ship's bow in every frame: the container ship is the only vessel in shot.
# - hf-unload-shrimp, hf-store: every frame of the photoreal takes showed white plastic crates (unload) or racks of
#   white boxes (cold store), and no carton-free take exists. Their slots take a slow push on the Blender review stills
#   #246 (steel crates out of the truck) and #257 (cold store, steel racks), docs/review/stills/ in git history.
# hf-load (the port's loading-dock opening) is cut from /story instead: wrapped carton pallets on wooden pallets, or
# the carton stack inside the trailer, are in all but its last 8 frames.
set -euo pipefail
cd "$(dirname "$0")/.."
HD="${HD:-$HOME/Desktop/skylark/hd-masters}"
X264=(-c:v libx264 -preset slow -crf 10 -pix_fmt yuv420p -an)
still(){ git show "$(git log --all --format=%h -1 -- "docs/review/stills/$1.jpg"):docs/review/stills/$1.jpg" > "$2"; }
for id in hf-arrive hf-reverse hf-ship hf-unload-shrimp hf-store; do rm -rf "masters/$id"; mkdir -p "masters/$id"; done
ffmpeg -nostdin -v error -y -i "$HD/hf-arrive/master.mp4" -vf hflip "${X264[@]}" masters/hf-arrive/master.mp4
ffmpeg -nostdin -v error -y -i "$HD/hf-reverse/master.mp4" -vf hflip "${X264[@]}" masters/hf-reverse/master.mp4
ffmpeg -nostdin -v error -y -i "$HD/hf-ship/master.mp4" -vf "crop=1176:662:1384:778,scale=2560:1440:flags=lanczos" "${X264[@]}" masters/hf-ship/master.mp4
tmp=$(mktemp -d "${TMPDIR:-/tmp}/pm.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
still 246 "$tmp/246.jpg"; python3 scripts/still-push.py "$tmp/246.jpg" masters/hf-unload-shrimp/master.mp4 0.5 0.55 1.08
still 257 "$tmp/257.jpg"; python3 scripts/still-push.py "$tmp/257.jpg" masters/hf-store/master.mp4 0.5 0.55 1.08
# then, every other clip held at its files:
#   IDS="hf-arrive hf-reverse hf-unload-shrimp hf-store hf-ship"
#   for id in $IDS; do SOLVE="$IDS" POSTERS=only scripts/encode-hf.sh $id; SOLVE="$IDS" POSTERS=no scripts/encode-hf.sh $id; done
# The port film's phone tier, with a top crop so the canopy roof no longer fills a phone screen (as wide as the desktop
# frame shows it), at 190 KB a file (was ~100): both phone paths end at 11.96 / 11.94 MB of 12.
#   for id in hf-port-1 hf-port-2 hf-port-3 hf-port-4 hf-port-5; do
#     CAPS_ID=hf-sail SOLVE=hf-sail M_CROP=608:1080:848:360 M_SCALE=1 TIERS=m CAP_m=194560 POSTERS=no scripts/encode-hf.sh $id
#     CAPS_ID=hf-sail SOLVE=hf-sail M_CROP=608:1080:848:360 M_SCALE=1 POSTERS=only POSTER_2560=1 CAP_KB=60 scripts/encode-hf.sh $id
#   done
