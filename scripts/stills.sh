#!/bin/zsh
# Composition stills at 3840x2160 (#255-#260, #246): one frame per shot from the built scene blends.
# usage: scripts/stills.sh <blends dir> <out dir>   (blends from build_all: truck-reverse, p-intake, p-cold, port_v3.3, x-sea, hero-dawn)
R=${0:A:h:h}; B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}; BL=$1; OUT=$2; mkdir -p $OUT
for spec in truck-reverse:255:212 p-intake:256:110 p-cold:257:280 port_v3.3:258:120 x-sea:259:96 hero-dawn:260:144 p-intake:246:50; do
  bl=${spec%%:*}; r=${spec#*:}; id=${r%%:*}; f=${r##*:}
  $B -b $BL/$bl.blend --python $R/blender/still_settings.py -o $OUT/$id- -F PNG -f $f > $OUT/$id.log 2>&1
  mv $OUT/$id-$(printf %04d $f).png $OUT/$id.png
  $B -b $BL/$bl.blend --python $R/blender/still_rules.py -- $id $f $OUT/$id.rules.json 2>&1 | grep '^STILL'
done
python3 $R/scripts/stills_sheet.py $OUT $OUT/out
