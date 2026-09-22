#!/usr/bin/env bash
# Script de instalação do utilitário multi_search em ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/bin"
BIN_NAME="msearch"

mkdir -p "$TARGET_DIR"

chmod +x "$SCRIPT_DIR/multi_search.py"

ln -sf "$SCRIPT_DIR/multi_search.py" "$TARGET_DIR/$BIN_NAME"
ln -sf "$SCRIPT_DIR/multi_search.py" "$TARGET_DIR/multi_search"

echo "✅ Instalado com sucesso!"
echo "Comandos disponíveis em $TARGET_DIR:"
echo "  • $BIN_NAME"
echo "  • multi_search"
echo ""
echo "Certifique-se de que '$TARGET_DIR' esteja no seu PATH."
