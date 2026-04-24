#!/bin/sh
set -eu

VERSION=${ACDL_VERSION:-"0.1.0"}
WHEEL_URL=${ACDL_WHEEL_URL:-"https://github.com/TengShao/ACDL/releases/download/v$VERSION/acdl-$VERSION-py3-none-any.whl"}

python3 -m pip install --user "$WHEEL_URL"

echo "ACDL installed from: $WHEEL_URL"
echo "Verify with: acdl --help"
