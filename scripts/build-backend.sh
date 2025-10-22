#!/bin/bash
# Build Python backend bundle with PyInstaller

set -euo pipefail

echo "🐍 Building Python backend bundle..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Clean previous builds
echo -e "${BLUE}Cleaning previous builds...${NC}"
rm -rf build/ dist/ dist-python/

# Ensure PyInstaller is installed
echo -e "${BLUE}Checking PyInstaller...${NC}"
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${RED}PyInstaller not found. Installing...${NC}"
    uv pip install pyinstaller
fi

# Build with PyInstaller
echo -e "${BLUE}Running PyInstaller...${NC}"
pyinstaller automagik-omni-backend.spec

# Move output to expected location for Electron builder
echo -e "${BLUE}Organizing build output...${NC}"
mkdir -p dist-python
mv dist/automagik-omni-backend* dist-python/ 2>/dev/null || true

# Show output
echo -e "${GREEN}✅ Backend built successfully!${NC}"
echo ""
echo "Output:"
ls -lh dist-python/

# Test executable
echo ""
echo -e "${BLUE}Testing executable...${NC}"
if [ -f "dist-python/automagik-omni-backend" ]; then
    ./dist-python/automagik-omni-backend --help || true
elif [ -f "dist-python/automagik-omni-backend.exe" ]; then
    ./dist-python/automagik-omni-backend.exe --help || true
fi

echo ""
echo -e "${GREEN}✨ Backend build complete!${NC}"
echo "Backend bundle: $(pwd)/dist-python/"
