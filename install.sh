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

echo "✅ Executables created successfully in $TARGET_DIR!"
echo "  • $BIN_NAME -> $SCRIPT_DIR/multi_search.py"
echo "  • multi_search -> $SCRIPT_DIR/multi_search.py"
echo ""

# Check if TARGET_DIR is in PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo "⚠️  '$TARGET_DIR' is not in your current PATH."
    
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    UPDATED_FILES=()

    # Detect shell config files
    if [[ -f "$HOME/.bashrc" ]] && ! grep -qs 'local/bin' "$HOME/.bashrc"; then
        echo "$PATH_LINE" >> "$HOME/.bashrc"
        UPDATED_FILES+=("~/.bashrc")
    fi

    if [[ -f "$HOME/.zshrc" ]] && ! grep -qs 'local/bin' "$HOME/.zshrc"; then
        echo "$PATH_LINE" >> "$HOME/.zshrc"
        UPDATED_FILES+=("~/.zshrc")
    fi

    if [[ ${#UPDATED_FILES[@]} -eq 0 ]] && [[ -f "$HOME/.profile" ]] && ! grep -qs 'local/bin' "$HOME/.profile"; then
        echo "$PATH_LINE" >> "$HOME/.profile"
        UPDATED_FILES+=("~/.profile")
    fi

    if [[ ${#UPDATED_FILES[@]} -gt 0 ]]; then
        echo "✅ Automatically added '$TARGET_DIR' to PATH in: ${UPDATED_FILES[*]}"
        echo "💡 Run 'source ${UPDATED_FILES[0]}' or restart your terminal to use 'msearch' immediately."
    else
        echo "💡 Add the following line to your shell configuration file (~/.bashrc or ~/.zshrc):"
        echo "   $PATH_LINE"
    fi
else
    echo "✅ '$TARGET_DIR' is already in your PATH."
fi

echo ""
echo "🎉 Installation complete! Run 'msearch --help' to get started."

