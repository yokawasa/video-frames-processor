#!/bin/sh
set -e -x

cwd=`dirname "$0"`
expr "$0" : "/.*" > /dev/null || cwd=`(cd "$cwd" && pwd)`

WORD2VEC_MODEL="https://yoichikaarchive.blob.core.windows.net/autoss/text8.model"
TARGET_DIR="$cwd/../assets"

if [ ! -d ${TARGET_DIR} ]; then
  mkdir -p ${TARGET_DIR}
fi

curl -o "$TARGET_DIR/text8.model" $WORD2VEC_MODEL
