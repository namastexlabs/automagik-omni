# Build Documentation

This directory contains documentation for building desktop installers.

## Contents

- `DESKTOP_BUILD_HANDOFF.md` - Complete handoff document with build system details
- `DESKTOP_DISTRIBUTION.md` - Distribution and packaging information
- `PYINSTALLER_BUILD.md` - PyInstaller build process
- `PYINSTALLER_WARNINGS.md` - PyInstaller warnings resolution

## Build System

### Local Builds

```bash
# Build for all platforms
./build-all.sh

# Build specific platform
./build-all.sh linux
./build-all.sh win
./build-all.sh mac
```

### CI/CD Builds

Automated builds run via GitHub Actions:
- Workflow: `.github/workflows/desktop-build.yml`
- Documentation: `.github/workflows/README.md`

## Related Documentation

- Electron docs: `/docs/electron/`
- Backend build script: `/scripts/build-backend.sh`
- PyInstaller spec: `/automagik-omni-backend.spec`
