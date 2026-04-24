#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BIN_DIR=${ACDL_INSTALL_BIN:-"$HOME/.local/bin"}
LAUNCHER="$BIN_DIR/acdl"

mkdir -p "$BIN_DIR"

cat > "$LAUNCHER" <<EOF
#!/bin/sh
PYTHONPATH="$ROOT_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m acdl "\$@"
EOF

chmod +x "$LAUNCHER"

echo "ACDL launcher installed at: $LAUNCHER"
echo "Verify with: acdl --help"
echo "If needed, add this to PATH: export PATH=\"$BIN_DIR:\$PATH\""
