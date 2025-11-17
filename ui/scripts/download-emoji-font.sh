#!/bin/bash
# Download Noto Color Emoji font for Electron emoji support
# This font is needed because Electron with GPU disabled (WSL2) cannot access system emoji fonts

FONT_DIR="$(dirname "$0")/../resources/fonts"
FONT_FILE="$FONT_DIR/NotoColorEmoji.ttf"
FONT_URL="https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf"

mkdir -p "$FONT_DIR"

if [ ! -f "$FONT_FILE" ]; then
  echo "Downloading Noto Color Emoji font..."
  curl -L -o "$FONT_FILE" "$FONT_URL"

  if [ $? -eq 0 ]; then
    echo "✓ Noto Color Emoji font downloaded successfully"
  else
    echo "✗ Failed to download emoji font"
    exit 1
  fi
else
  echo "✓ Noto Color Emoji font already exists"
fi
