#!/bin/zsh
# Composition stills at 3840x2160 (#255-#260, #246): one frame per shot from the built scene blends.
# usage: scripts/stills.sh <blends dir> <out dir> [ids...]   (blends from build_all, plus p-intake-fish: SK_FISH=1 plant_chain.py p-intake)
R=${0:A:h:h}; B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}; BL=$1; OUT=$2; shift 2; mkdir -p $OUT
ONLY=("$@")
for spec in truck-reverse:255:232 p-intake:256:150 p-cold:257:280 port_v3.3:258:120 x-sea:259:96 hero-dawn:260:144 p-intake:246:50 p-intake-fish:246f:50; do
  bl=${spec%%:*}; r=${spec#*:}; id=${r%%:*}; f=${r##*:}
  (( $#ONLY )) && (( ${ONLY[(Ie)$id]} == 0 )) && continue
  STILL_ID=$id $B -b $BL/$bl.blend --python $R/blender/still_settings.py -o $OUT/$id- -F PNG -f $f > $OUT/$id.log 2>&1
  mv $OUT/$id-$(printf %04d $f).png $OUT/$id.png
  STILL_ID=$id $B -b $BL/$bl.blend --python $R/blender/still_rules.py -- $id $f $OUT/$id.rules.json 2>&1 | grep '^STILL'
done
python3 $R/scripts/stills_sheet.py $OUT $OUT/out
