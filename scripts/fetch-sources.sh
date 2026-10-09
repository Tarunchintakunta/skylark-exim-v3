#!/usr/bin/env bash
# Copy the reusable 1080p masters + chain anchors from the skylark repo into assets-src/ (git-ignored; see docs/ASSETS_SPEC.md)
# Usage: scripts/fetch-sources.sh     Env: SRC_REPO=../skylark  (auto-cloned from github.com/Tarunchintakunta/skylark if missing)
set -euo pipefail
SRC_REPO="${SRC_REPO:-../skylark}"
[ -d "$SRC_REPO/assets/video/1080" ] || git clone --depth 1 https://github.com/Tarunchintakunta/skylark "$SRC_REPO"
mkdir -p assets-src/video assets-src/models assets-src/anchors assets-src/blender assets-src/render
cpn(){ [ -f "$2/$(basename "$1")" ] || cp "$1" "$2/"; }
# reused clips (see docs/STORY.md "Source" column)
for id in opening a1 a2 a3 a4 b2 b3; do cpn "$SRC_REPO/assets/video/1080/$id.mp4" assets-src/video; done
# chain anchors used as start_image/end_image for the new Higgsfield clips
for f in "$SRC_REPO"/assets/anchors/*_1080*.png "$SRC_REPO"/assets/stills/*.png; do cpn "$f" assets-src/anchors; done
# a3's first frame = end_image for the new catch clip
[ -f assets-src/anchors/a3_first_1080.png ] || ffmpeg -v error -i assets-src/video/a3.mp4 -frames:v 1 assets-src/anchors/a3_first_1080.png
echo "Reusable masters copied. Higgsfield clips from Tarun go in assets-src/video/ by id (o-catch, p-ponds, p-intake, p-proc, p-freeze); Claude renders x-cranes and x-ship from assets-src/blender/port.blend (docs/BLENDER_GLB_SPEC.md)."
ls assets-src/video
