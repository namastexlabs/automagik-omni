# GitHub Actions CI/CD Workflows

This directory contains all GitHub Actions workflows for Automagik Omni.

## 📋 Workflows Overview

### Core CI/CD

#### `desktop-build.yml` - **Desktop Application Build** 🆕
**Purpose:** Build cross-platform desktop installers with native Python backend binaries.

**Triggers:**
- Push to `main`/`dev` branches
- Pull requests to `main`/`dev`
- Tags matching `v*` (releases)
- Manual dispatch

**Jobs:**
1. **build-backend** - Build Python backend with PyInstaller on native runners
   - Linux: Ubuntu Latest
   - Windows: Windows Latest
   - macOS: macOS Latest
   - Artifacts: Platform-specific executables (~51 MB each)

2. **build-electron** - Build Electron UI with bundled backend
   - Linux: AppImage, DEB (amd64, arm64), RPM
   - Windows: NSIS Installer (.exe) for x64 and ARM64
   - macOS: DMG and ZIP for Intel and Apple Silicon
   - Artifacts: Full installers (140-183 MB)

3. **create-release** - Publish GitHub release (tags only)
   - Creates draft release with all platform installers
   - Auto-generates release notes

4. **build-summary** - Summary report
   - Consolidated build status
   - Artifact inventory

**Key Features:**
- ✅ Native compilation (no cross-compilation issues)
- ✅ Uses `uv` for fast Python dependency management
- ✅ Caches dependencies for faster builds
- ✅ Automatic artifact uploads
- ✅ Release automation for tagged versions

**Artifacts Produced:**
```
installers-linux/
  ├── automagik-omni-ui-1.0.0.AppImage (183 MB)
  ├── automagik-omni-ui_1.0.0_amd64.deb (144 MB)
  └── automagik-omni-ui_1.0.0_arm64.deb (139 MB)

installers-windows/
  └── automagik-omni-ui-1.0.0-setup.exe (varies by architecture)

installers-macos/
  ├── automagik-omni-ui-1.0.0.dmg
  └── automagik-omni-ui-1.0.0-mac.zip
```

#### `test-suite.yml` - **Python Test Suite**
**Purpose:** Run comprehensive Python tests with coverage.

**Triggers:**
- Pull requests to `main`/`dev`
- Push to `dev`
- Manual dispatch

**Jobs:**
1. **test** - Run pytest suite (477 tests)
2. **lint** - Code quality with ruff
3. **status** - Overall status check

#### `pr-tests.yml` - **PR Validation**
**Purpose:** Quick tests for pull requests.

**Triggers:**
- Pull requests only

### Python Backend Workflows

#### `coverage-enforcement.yml` - **Coverage Validation**
**Purpose:** Enforce minimum test coverage thresholds.

**Triggers:**
- Pull requests to `main`/`dev`

### Release & Publishing

#### `publish.yml` - **Package Publishing**
**Purpose:** Publish Python package to PyPI.

**Triggers:**
- GitHub releases
- Manual dispatch

#### `pr-auto-release.yml` - **Auto Release on Merge**
**Purpose:** Automatically create releases when PRs are merged.

**Triggers:**
- Pull request closed (merged to main)

### Automation & Bots

#### `genie-pr-feedback.yml` - **Automated PR Reviews**
**Purpose:** AI-powered code review and feedback.

**Triggers:**
- Pull request opened/synchronized

#### `genie-release-notes.yml` - **Release Notes Generation**
**Purpose:** Auto-generate comprehensive release notes.

**Triggers:**
- GitHub releases

#### `validate-pr-source.yml` - **PR Source Validation**
**Purpose:** Validate PR source branch naming and structure.

**Triggers:**
- Pull requests

#### `link-to-roadmap.yml` - **Roadmap Integration**
**Purpose:** Link issues/PRs to project roadmap.

**Triggers:**
- Issues/PRs opened or labeled

#### `auto-close-linked-issues.yml` - **Issue Auto-Close**
**Purpose:** Close linked issues when PRs are merged.

**Triggers:**
- Pull request closed

#### `label-sync.yml` - **Label Management**
**Purpose:** Sync repository labels.

**Triggers:**
- Manual dispatch
- Push to main

## 🚀 Desktop Build Pipeline Details

### How It Works

**Phase 1: Backend Build (Parallel, per platform)**
```
1. Checkout code
2. Set up Python 3.12
3. Install uv package manager
4. Install dependencies with uv sync
5. Build backend with PyInstaller
   └── scripts/build-backend.sh
6. Upload backend artifact
```

**Phase 2: Electron UI Build (Parallel, per platform)**
```
1. Checkout code
2. Set up Node.js 20
3. Install pnpm
4. Download backend artifact from Phase 1
5. Install UI dependencies (pnpm install)
6. Build Electron app
   ├── Linux: electron-builder --linux
   ├── Windows: electron-builder --win
   └── macOS: electron-builder --mac
7. Upload installer artifacts
```

**Phase 3: Release (Tags only)**
```
1. Download all artifacts
2. Create GitHub draft release
3. Upload all installers
4. Generate release notes
```

### Platform-Specific Details

#### Linux Build
- **Runner:** `ubuntu-latest`
- **Backend:** ELF 64-bit executable
- **Installers:**
  - AppImage (universal, self-contained)
  - DEB packages (amd64, arm64)
  - RPM packages (x64)
- **Dependencies:** rpm package for RPM builds

#### Windows Build
- **Runner:** `windows-latest`
- **Backend:** PE32+ Windows executable
- **Installers:**
  - NSIS installer (x64, ARM64)
- **Features:**
  - Desktop shortcut creation
  - Start menu integration
  - Per-user installation

#### macOS Build
- **Runner:** `macos-latest`
- **Backend:** Mach-O 64-bit executable
- **Installers:**
  - DMG (Intel, Apple Silicon)
  - ZIP archives
- **Features:**
  - Code signing ready (identity: null)
  - Notarization ready (notarize: false)
  - Hardened runtime enabled

### Troubleshooting

#### Wine Verification Failures (Local Builds)
When building on Linux/WSL, you may see:
```
⨯ cannot execute  cause=exit status 1
wine: failed to load ntdll.dll
```

**This is expected and safe to ignore.** The Windows .exe is built correctly, but Wine can't verify it. This doesn't happen in CI because we use native Windows runners.

#### Backend Not Found
If Electron build fails with "backend not found":

1. Verify backend artifacts were uploaded:
   ```bash
   # In GitHub Actions logs, check:
   - build-backend job completed successfully
   - Upload backend artifact step succeeded
   ```

2. Verify download in build-electron job:
   ```bash
   # Check download artifact step
   ls dist-python/
   ```

3. Electron-builder expects backend at:
   ```
   ../dist-python/automagik-omni-backend*
   ```
   (relative to ui/ directory)

#### Artifact Size Limits
GitHub has a 2GB artifact size limit. Current artifacts:
- Backend: ~51 MB ✅
- AppImage: ~183 MB ✅
- DEB: ~140 MB ✅
- Windows: ~290 KB ⚠️ (may vary)

If you hit limits, consider:
- Enabling compression in electron-builder.yml
- Splitting artifacts by platform
- Using external storage for releases

## 📊 Workflow Badges

Add these to your README.md:

```markdown
[![Test Suite](https://github.com/namastexlabs/automagik-omni/actions/workflows/test-suite.yml/badge.svg)](https://github.com/namastexlabs/automagik-omni/actions/workflows/test-suite.yml)
[![Desktop Build](https://github.com/namastexlabs/automagik-omni/actions/workflows/desktop-build.yml/badge.svg)](https://github.com/namastexlabs/automagik-omni/actions/workflows/desktop-build.yml)
[![Coverage](https://github.com/namastexlabs/automagik-omni/actions/workflows/coverage-enforcement.yml/badge.svg)](https://github.com/namastexlabs/automagik-omni/actions/workflows/coverage-enforcement.yml)
```

## 🔧 Local Development

To test builds locally before pushing:

```bash
# Build backend only
./scripts/build-backend.sh

# Build for specific platform
./build-all.sh linux   # Linux packages
./build-all.sh win     # Windows (will fail Wine verification in WSL)
./build-all.sh mac     # macOS (requires macOS)
./build-all.sh all     # All platforms

# Test Electron UI only (without backend)
cd ui
pnpm install
pnpm run build:unpack  # Build without packaging
```

## 🎯 Release Process

### Manual Release

1. **Create tag:**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

2. **Wait for workflow:**
   - Monitor at: https://github.com/namastexlabs/automagik-omni/actions

3. **Edit draft release:**
   - Go to: https://github.com/namastexlabs/automagik-omni/releases
   - Edit draft release
   - Add release notes
   - Publish

### Automated Release (via PR merge)

The `pr-auto-release.yml` workflow automatically creates releases when PRs are merged to main with version bumps.

## 📚 Additional Resources

- [Electron Builder Documentation](https://www.electron.build/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Project Build Documentation](../DESKTOP_BUILD_HANDOFF.md)
