#!/bin/bash
# Build complete desktop application (Backend + Electron UI)

set -euo pipefail

echo "🖥️  Building Automagik Omni Desktop Application..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse arguments
PLATFORM="${1:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
SKIP_BACKEND="${SKIP_BACKEND:-false}"

echo -e "${BLUE}Platform: ${PLATFORM}${NC}"
echo ""

# Step 1: Build Python backend
if [ "$SKIP_BACKEND" != "true" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Step 1/3: Building Python Backend${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    ./scripts/build-backend.sh
    echo ""
else
    echo -e "${YELLOW}⚠️  Skipping backend build (SKIP_BACKEND=true)${NC}"
    echo ""
fi

# Check backend exists
if [ ! -d "dist-python" ] || [ -z "$(ls -A dist-python 2>/dev/null)" ]; then
    echo -e "${RED}❌ Backend not found in dist-python/${NC}"
    echo "Run ./scripts/build-backend.sh first or unset SKIP_BACKEND"
    exit 1
fi

# Step 2: Build Electron UI
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Step 2/3: Building Electron UI${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
cd ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing UI dependencies...${NC}"
    pnpm install
fi

# Build Vite app
echo -e "${BLUE}Building Vite app...${NC}"
pnpm run vite:build:app

echo ""

# Step 3: Package with electron-builder
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Step 3/3: Packaging Desktop App${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

case "$PLATFORM" in
    linux)
        echo -e "${BLUE}Building for Linux (AppImage + deb)...${NC}"
        pnpm run electron:build:linux
        ;;
    darwin|mac|macos)
        echo -e "${BLUE}Building for macOS (DMG)...${NC}"
        pnpm run electron:build:mac
        ;;
    windows|win)
        echo -e "${BLUE}Building for Windows (NSIS)...${NC}"
        pnpm run electron:build:win
        ;;
    dir)
        echo -e "${BLUE}Building unpacked (for testing)...${NC}"
        pnpm run electron:build:dir
        ;;
    *)
        echo -e "${RED}Unknown platform: $PLATFORM${NC}"
        echo "Usage: $0 [linux|darwin|windows|dir]"
        exit 1
        ;;
esac

cd "$PROJECT_ROOT"

# Show results
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✨ Build Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Output directory: ui/dist/"
echo ""
echo "Installers:"
ls -lh ui/dist/*.{exe,dmg,AppImage,deb,rpm} 2>/dev/null || echo "  (no installers found - may have built unpacked)"
echo ""
echo "Unpacked builds:"
ls -d ui/dist/*-unpacked 2>/dev/null || echo "  (no unpacked builds)"
echo ""
echo -e "${YELLOW}📦 Ready for distribution!${NC}"
