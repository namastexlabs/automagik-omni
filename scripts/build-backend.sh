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
if ! uv run pyinstaller --version &> /dev/null; then
    echo -e "${RED}PyInstaller not found. Installing...${NC}"
    uv pip install pyinstaller
fi

# Build with PyInstaller
echo -e "${BLUE}Running PyInstaller...${NC}"

# Run PyInstaller and filter out known harmless warnings
# These warnings are expected and don't affect functionality:
# - alembic.testing: Test-only module, not needed in production
# - mx.DateTime: Legacy 1990s datetime library, Python 3 uses built-in datetime
# - user32: Windows DLL, expected when building on Linux/WSL
uv run pyinstaller automagik-omni-backend.spec 2>&1 | \
    grep -v "WARNING: Failed to collect submodules for 'alembic.testing'" | \
    grep -v "WARNING: Hidden import \"mx.DateTime\" not found!" | \
    grep -v "WARNING: Library user32 required via ctypes not found" | \
    grep -v "PydanticExperimentalWarning" || true

# Check if build succeeded
if [ ! -f "dist/automagik-omni-backend" ]; then
    echo -e "${RED}❌ Build failed! Check logs above for errors.${NC}"
    exit 1
fi

# Move output to expected location for Electron builder
echo -e "${BLUE}Organizing build output...${NC}"
mkdir -p dist-python
mv dist/automagik-omni-backend* dist-python/ 2>/dev/null || true

# Show output
echo -e "${GREEN}✅ Backend built successfully!${NC}"
echo ""
echo "Output:"
ls -lh dist-python/

# Verify executable exists and is executable
echo ""
echo -e "${BLUE}Verifying executable...${NC}"
if [ -f "dist-python/automagik-omni-backend" ]; then
    chmod +x dist-python/automagik-omni-backend
    echo -e "${GREEN}✓ Linux/macOS executable ready${NC}"
elif [ -f "dist-python/automagik-omni-backend.exe" ]; then
    echo -e "${GREEN}✓ Windows executable ready${NC}"
else
    echo -e "${RED}❌ No executable found!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✨ Backend build complete!${NC}"
echo "Backend bundle: $(pwd)/dist-python/"
