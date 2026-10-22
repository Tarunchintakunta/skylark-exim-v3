#!/usr/bin/env bash
# The 960x540 review preview (docs/review/<dir>/preview-960x540.mp4): every /story clip in film order, the farmed path
# then the wild path's own chapters, cut straight from the 960 H.264 tier (no new renders). The documents chapter is
# its still for 2 s; the globe chapter is left out (WebGL, not footage).
#   [CRF=33] scripts/preview-cut.sh <out.mp4>   (crf 33 keeps the full cut under the 6,000 KB file limit)
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:?out.mp4}"; tmp=$(mktemp -d "${TMPDIR:-/tmp}/pv.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
ids=$(node --import tsx --input-type=module -e "
const { POND, OCEAN } = await import('./src/config/chapters.ts')
const seen = new Set(), ids = []
for (const ch of [...POND, ...OCEAN]) for (const m of ch.media) {
  const id = m.kind === 'video' ? m.id : m.kind === 'dom' ? m.poster : null
  if (id && !seen.has(id)) { seen.add(id); ids.push(id) }
}
console.log(ids.join(' '))")
i=0
for id in $ids; do
  f=$(printf '%s/%03d.mp4' "$tmp" $i); i=$((i+1))
  if [ -f "public/media/${id}_960.mp4" ]; then
    ffmpeg -nostdin -v error -y -i "public/media/${id}_960.mp4" -vf "scale=960:540,setsar=1,fps=24" -an -c:v libx264 -crf 20 -pix_fmt yuv420p "$f"
  else
    img=$(ls public/media/${id}*_960.webp 2>/dev/null | head -1)
    [ -n "$img" ] || { echo "skip $id"; continue; }
    ffmpeg -nostdin -v error -y -loop 1 -t 2 -i "$img" -vf "scale=960:540,setsar=1,fps=24" -an -c:v libx264 -crf 20 -pix_fmt yuv420p "$f"
  fi
  echo "file '$f'" >> "$tmp/list.txt"
done
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$tmp/list.txt" -c:v libx264 -crf ${CRF:-33} -preset slow -pix_fmt yuv420p -movflags +faststart "$out"
echo "$out: $(( $(stat -f%z "$out") / 1024 )) KB"
