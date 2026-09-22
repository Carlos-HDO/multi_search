#!/usr/bin/env bash
# Installation script for multi_search utility in ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/bin"
BIN_NAME="msearch"

mkdir -p "$TARGET_DIR"

chmod +x "$SCRIPT_DIR/multi_search.py"

ln -sf "$SCRIPT_DIR/multi_search.py" "$TARGET_DIR/$BIN_NAME"
ln -sf "$SCRIPT_DIR/multi_search.py" "$TARGET_DIR/multi_search"

echo "✅ Successfully installed!"
echo "Available commands in $TARGET_DIR:"
echo "  • $BIN_NAME"
echo "  • multi_search"
echo ""
echo "Ensure '$TARGET_DIR' is included in your PATH."
