#!/bin/bash
set -e

echo "📦 Bundling Python backend for npm package..."

# Check if .venv exists
if [ ! -d ".venv" ]; then
  echo "❌ Error: .venv not found. Run 'uv sync' first."
  exit 1
fi

# Check if src/ exists
if [ ! -d "src" ]; then
  echo "❌ Error: src/ directory not found."
  exit 1
fi

# Create .bundled directory structure
echo "   Creating .bundled directory..."
rm -rf .bundled
mkdir -p .bundled/python
mkdir -p .bundled/backend

# Copy virtual environment
echo "   Copying Python runtime (.venv -> .bundled/python)..."
echo "   This may take a minute..."
cp -r .venv/* .bundled/python/

# Copy Python source
echo "   Copying Python source (src -> .bundled/backend/src)..."
cp -r src/ .bundled/backend/src/

# Copy Python config files
echo "   Copying Python config files..."
[ -f pyproject.toml ] && cp pyproject.toml .bundled/backend/
[ -f uv.lock ] && cp uv.lock .bundled/backend/

# Clean up unnecessary files from venv to reduce size
echo "   Cleaning up unnecessary files..."

# Remove Python cache files
find .bundled/python -type f -name "*.pyc" -delete
find .bundled/python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove test files
find .bundled/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find .bundled/python -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Remove dist-info directories (metadata we don't need at runtime)
find .bundled/python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Remove .so files debug symbols (Linux only, keep the .so files themselves)
if command -v strip &> /dev/null; then
  echo "   Stripping debug symbols from shared libraries..."
  find .bundled/python -name "*.so" -type f -exec strip --strip-debug {} \; 2>/dev/null || true
fi

# Create .gitkeep to ensure directory structure persists
touch .bundled/.gitkeep

# Calculate final size
BUNDLED_SIZE=$(du -sh .bundled 2>/dev/null | cut -f1)

echo ""
echo "✅ Python backend bundled successfully!"
echo "   Location: .bundled/"
echo "   Size: ${BUNDLED_SIZE}"
echo ""
echo "   Structure:"
echo "   .bundled/"
echo "   ├── python/          # Python venv (~150MB)"
echo "   └── backend/"
echo "       └── src/         # Python source"
echo ""
