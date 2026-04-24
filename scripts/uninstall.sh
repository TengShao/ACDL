#!/bin/sh
set -eu

BIN_DIR=${ACDL_INSTALL_BIN:-"$HOME/.local/bin"}
LAUNCHER="$BIN_DIR/acdl"

if [ -f "$LAUNCHER" ]; then
  rm "$LAUNCHER"
  echo "Removed $LAUNCHER"
else
  echo "No ACDL launcher found at $LAUNCHER"
fi
