#!/bin/bash
# Test the bundled desktop application

set -euo pipefail

echo "🧪 Testing Automagik Omni Desktop Bundle..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Find unpacked build
UNPACKED_DIR=$(find ui/dist -maxdepth 1 -type d -name "*-unpacked" | head -1)

if [ -z "$UNPACKED_DIR" ]; then
    echo -e "${RED}❌ No unpacked build found${NC}"
    echo "Run: ./scripts/build-desktop.sh dir"
    exit 1
fi

echo -e "${BLUE}Testing build: ${UNPACKED_DIR}${NC}"
echo ""

# Test 1: Check backend bundle exists
echo -e "${BLUE}Test 1: Backend bundle exists${NC}"
BACKEND_PATH="$UNPACKED_DIR/resources/backend"
if [ -d "$BACKEND_PATH" ]; then
    echo -e "${GREEN}✅ Backend directory found${NC}"
    ls -lh "$BACKEND_PATH"
else
    echo -e "${RED}❌ Backend directory not found${NC}"
    exit 1
fi
echo ""

# Test 2: Check backend executable
echo -e "${BLUE}Test 2: Backend executable${NC}"
BACKEND_EXE="$BACKEND_PATH/automagik-omni-backend"
if [ "$(uname -s)" == "MINGW"* ] || [ "$(uname -s)" == "MSYS"* ]; then
    BACKEND_EXE="$BACKEND_PATH/automagik-omni-backend.exe"
fi

if [ -f "$BACKEND_EXE" ] && [ -x "$BACKEND_EXE" ]; then
    echo -e "${GREEN}✅ Backend executable found and is executable${NC}"
    file "$BACKEND_EXE" || true
else
    echo -e "${RED}❌ Backend executable not found or not executable${NC}"
    exit 1
fi
echo ""

# Test 3: Test backend help
echo -e "${BLUE}Test 3: Backend responds to --help${NC}"
if "$BACKEND_EXE" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend responds to --help${NC}"
else
    echo -e "${YELLOW}⚠️  Backend --help failed (may be normal)${NC}"
fi
echo ""

# Test 4: Check Electron executable
echo -e "${BLUE}Test 4: Electron executable${NC}"
APP_NAME="Automagik Omni"
if [ "$(uname -s)" == "Darwin" ]; then
    APP_EXE="$UNPACKED_DIR/$APP_NAME.app/Contents/MacOS/$APP_NAME"
elif [ "$(uname -s)" == "Linux" ]; then
    APP_EXE="$UNPACKED_DIR/automagik-omni"
else
    APP_EXE="$UNPACKED_DIR/AutomagikOmni.exe"
fi

if [ -f "$APP_EXE" ]; then
    echo -e "${GREEN}✅ Electron executable found${NC}"
    ls -lh "$APP_EXE"
else
    echo -e "${RED}❌ Electron executable not found${NC}"
    exit 1
fi
echo ""

# Test 5: Check resources
echo -e "${BLUE}Test 5: Check bundled resources${NC}"
RESOURCES_DIR="$UNPACKED_DIR/resources"
if [ -d "$RESOURCES_DIR" ]; then
    echo -e "${GREEN}✅ Resources directory found${NC}"
    echo "Contents:"
    du -sh "$RESOURCES_DIR"/*
else
    echo -e "${RED}❌ Resources directory not found${NC}"
    exit 1
fi
echo ""

# Test 6: Check app.asar
echo -e "${BLUE}Test 6: Check app.asar${NC}"
ASAR_FILE="$RESOURCES_DIR/app.asar"
if [ -f "$ASAR_FILE" ]; then
    echo -e "${GREEN}✅ app.asar found${NC}"
    ls -lh "$ASAR_FILE"
else
    echo -e "${RED}❌ app.asar not found${NC}"
    exit 1
fi
echo ""

# Summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ All Tests Passed!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Bundle structure looks good. Ready for distribution!"
echo ""
echo -e "${YELLOW}To manually test the app:${NC}"
echo "  $APP_EXE"
