#!/bin/bash
# Automagik Omni - Complete Build Script
# Builds BOTH backend and frontend into a single installer
# Run this from WSL - it will create Windows/Linux/Mac installers
#
# Usage: ./build-all.sh [PLATFORM]
#   PLATFORM: win, linux, mac, all (default: all)
#
# Examples:
#   ./build-all.sh            # Build for all platforms
#   ./build-all.sh win        # Build Windows installer only
#   ./build-all.sh linux      # Build Linux packages only
#   ./build-all.sh mac        # Build macOS installer only

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Automagik Omni - Complete Build System                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse platform argument
PLATFORM="${1:-all}"
PLATFORM=$(echo "$PLATFORM" | tr '[:upper:]' '[:lower:]')  # Convert to lowercase

# Validate platform
case "$PLATFORM" in
    win|windows)
        PLATFORM="win"
        ;;
    linux)
        PLATFORM="linux"
        ;;
    mac|macos|darwin)
        PLATFORM="mac"
        ;;
    all)
        PLATFORM="all"
        ;;
    *)
        echo -e "${RED}❌ Invalid platform: $PLATFORM${NC}"
        echo ""
        echo "Usage: $0 [PLATFORM]"
        echo "  PLATFORM: win, linux, mac, all (default: all)"
        exit 1
        ;;
esac

echo -e "${YELLOW}Building for platform: ${PLATFORM}${NC}"
echo ""

# ============================================================
# STEP 1: Build Python Backend with PyInstaller
# ============================================================
echo "═══════════════════════════════════════════════════════════"
echo "  Step 1: Building Python Backend"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ ! -f "./scripts/build-backend.sh" ]; then
    echo -e "${RED}❌ Backend build script not found!${NC}"
    echo "Expected: ./scripts/build-backend.sh"
    exit 1
fi

echo -e "${YELLOW}Running PyInstaller to create standalone backend...${NC}"
bash ./scripts/build-backend.sh

if [ ! -d "./dist-python" ]; then
    echo -e "${RED}❌ Backend build failed - dist-python not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend built successfully${NC}"
echo -e "   Location: ./dist-python/"
echo ""

# ============================================================
# STEP 2: Build Electron UI (Vite)
# ============================================================
echo "═══════════════════════════════════════════════════════════"
echo "  Step 2: Building Electron UI"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd ui

echo -e "${YELLOW}Installing UI dependencies...${NC}"
pnpm install

echo -e "${YELLOW}Building React app with Vite...${NC}"
pnpm run vite:build:app

echo -e "${GREEN}✅ UI built successfully${NC}"
echo ""

# ============================================================
# STEP 3: Package Everything with electron-builder
# ============================================================
echo "═══════════════════════════════════════════════════════════"
echo "  Step 3: Creating Installers"
echo "═══════════════════════════════════════════════════════════"
echo ""

case "$PLATFORM" in
    win)
        echo -e "${YELLOW}Building Windows installer...${NC}"
        # Wine verification may fail on Linux/WSL, but the .exe is still created successfully
        # We ignore the exit code and check if the installer exists instead
        pnpm run electron:build:win || true

        # Verify the installer was created
        if [ -f "dist/automagik-omni-ui-1.0.0-setup.exe" ]; then
            echo -e "${GREEN}✅ Windows installer created successfully${NC}"
            echo -e "   (Wine verification skipped - installer works on actual Windows)"
        else
            echo -e "${RED}❌ Windows installer build failed${NC}"
            exit 1
        fi
        ;;
    linux)
        echo -e "${YELLOW}Building Linux packages...${NC}"
        # RPM build may fail without rpmbuild, but AppImage and DEB still succeed
        pnpm run electron:build:linux || true

        # Verify at least AppImage or DEB was created
        if [ -f "dist/automagik-omni-ui-1.0.0.AppImage" ] || [ -f "dist/automagik-omni-ui_1.0.0_amd64.deb" ]; then
            echo -e "${GREEN}✅ Linux packages created successfully${NC}"
        else
            echo -e "${RED}❌ Linux build failed${NC}"
            exit 1
        fi
        ;;
    mac)
        echo -e "${YELLOW}Building macOS installer...${NC}"
        pnpm run electron:build:mac
        ;;
    all)
        echo -e "${YELLOW}Building for all platforms...${NC}"

        # Windows build
        pnpm run electron:build:win || true
        if [ -f "dist/automagik-omni-ui-1.0.0-setup.exe" ]; then
            echo -e "${GREEN}✅ Windows installer created${NC}"
        fi

        # Linux build
        pnpm run electron:build:linux || true
        if [ -f "dist/automagik-omni-ui-1.0.0.AppImage" ] || [ -f "dist/automagik-omni-ui_1.0.0_amd64.deb" ]; then
            echo -e "${GREEN}✅ Linux packages created${NC}"
        fi

        # macOS build
        pnpm run electron:build:mac || true
        if [ -f "dist/automagik-omni-ui-1.0.0.dmg" ]; then
            echo -e "${GREEN}✅ macOS installer created${NC}"
        fi
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✨ Build Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -d "./dist" ]; then
    echo -e "${GREEN}Installers created in:${NC}"
    ls -lh ./dist/*.exe ./dist/*.AppImage ./dist/*.dmg ./dist/*.deb 2>/dev/null || true
    echo ""
    echo "Output directory: $(pwd)/dist"
else
    echo -e "${RED}❌ No installers found in ./dist/${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Done! You can now install and run the app.${NC}"
echo ""
echo "What's included in the installer:"
echo "  • Automagik Omni Desktop UI (Electron)"
echo "  • FastAPI Backend (bundled, no Python needed)"
echo "  • PM2 process manager integration"
echo "  • All dependencies included"
echo ""
echo "Installation:"
echo "  • Windows: Run the .exe installer"
echo "  • Linux: chmod +x *.AppImage && ./automagik-omni-*.AppImage"
echo "  • macOS: Open the .dmg and drag to Applications"
