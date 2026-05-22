#!/bin/bash
# DevMind Web Installer (macOS/Linux)
# Run: curl -fsSL https://aarav7162.github.io/dev-devmind/install.sh | bash

set -e

echo ""
echo "  DevMind Installer"
echo "  ------------------"
echo ""

BASE_URL="https://aarav7162.github.io/dev-devmind/"
INSTALL_DIR="$HOME/.devmind/bin"
BIN_NAME="devmind"

# 1. Create install directory
mkdir -p "$INSTALL_DIR"

# 2. Get the binary
echo -n "  [1/2] Downloading devmind..."
if [ -f "./devmind" ]; then
    cp "./devmind" "$INSTALL_DIR/$BIN_NAME"
    echo " [OK] (Installed from local build)"
elif [ -f "./release/devmind" ]; then
    cp "./release/devmind" "$INSTALL_DIR/$BIN_NAME"
    echo " [OK] (Installed from local build)"
else
    curl -sSL "$BASE_URL$BIN_NAME" -o "$INSTALL_DIR/$BIN_NAME"
    chmod +x "$INSTALL_DIR/$BIN_NAME"
    echo " [OK]"
fi

# 3. Configure PATH
echo -n "  [2/2] Configuring system PATH..."
SHELL_RC=""
if [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "$INSTALL_DIR" "$SHELL_RC"; then
        echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_RC"
        echo " [OK] Added to $SHELL_RC"
    else
        echo " [OK] Already in $SHELL_RC"
    fi
else
    echo " [SKIP] Could not detect shell config. Please add $INSTALL_DIR to your PATH manually."
fi

echo ""
echo "  🚀 Installation Successful!"
echo ""
echo "  To finish setup:"
echo "    1. Restart your terminal (or run: source $SHELL_RC)"
echo "    2. Run: devmind start"
echo ""
