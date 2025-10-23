# 🖥️ Automagik Omni Desktop Distribution Guide

Complete guide for building and distributing the Automagik Omni desktop application.

---

## 📦 What Gets Bundled

The desktop application includes:

1. **Electron UI** (React + TypeScript)
   - Modern desktop interface
   - System tray integration
   - Auto-updates support

2. **Python Backend** (FastAPI)
   - Bundled as standalone executable
   - No Python installation required
   - Includes all dependencies

3. **Discord Bot** (Optional)
   - Automatically starts if configured
   - Managed by backend

4. **Resources**
   - Emoji fonts
   - Icons
   - Configuration templates

---

## 🚀 Quick Start

### Build for Your Platform

```bash
# Build everything (backend + UI)
./scripts/build-desktop.sh

# Platform-specific
./scripts/build-desktop.sh linux    # Linux (AppImage + deb)
./scripts/build-desktop.sh darwin   # macOS (DMG)
./scripts/build-desktop.sh windows  # Windows (NSIS)

# Test build (unpacked, faster)
./scripts/build-desktop.sh dir
```

### Test the Bundle

```bash
./scripts/test-bundle.sh
```

---

## 📋 Prerequisites

### All Platforms

- **Node.js** 20+ with pnpm
- **Python** 3.12+
- **uv** (Python package manager)
- **PyInstaller** (`uv pip install pyinstaller`)

### Platform-Specific

**Linux:**
- `build-essential`
- `libgtk-3-dev`
- `libnotify-dev`

**macOS:**
- Xcode Command Line Tools
- (Optional) Apple Developer certificate for signing

**Windows:**
- Visual Studio Build Tools
- (Optional) Code signing certificate

---

## 🛠️ Build Process

### Step 1: Build Python Backend

```bash
./scripts/build-backend.sh
```

**What it does:**
1. Cleans previous builds
2. Runs PyInstaller with `automagik-omni-backend.spec`
3. Outputs to `dist-python/`
4. Tests the executable

**Output:**
```
dist-python/
└── automagik-omni-backend     # (or .exe on Windows)
```

### Step 2: Build Electron UI

```bash
cd ui
pnpm install
pnpm run vite:build:app
```

**What it does:**
1. Installs UI dependencies
2. Builds React app with Vite
3. Compiles Electron main process
4. Outputs to `ui/out/`

### Step 3: Package Desktop App

```bash
cd ui
pnpm run electron:build:linux   # or :mac, :win
```

**What it does:**
1. Copies Python backend to `resources/backend/`
2. Bundles Electron app with electron-builder
3. Creates platform-specific installers
4. Outputs to `ui/dist/`

---

## 📁 Output Structure

### Unpacked Build (`ui/dist/linux-unpacked/`)

```
linux-unpacked/
├── automagik-omni              # Electron executable
├── resources/
│   ├── app.asar                # UI code (compressed)
│   └── backend/
│       └── automagik-omni-backend  # Python backend
└── [chromium libraries]
```

### Installers (`ui/dist/`)

**Linux:**
- `Automagik-Omni-1.0.0.AppImage` (~115MB) - Portable
- `automagik-omni_1.0.0_amd64.deb` - Debian/Ubuntu
- `automagik-omni-1.0.0.x86_64.rpm` - Fedora/RHEL

**macOS:**
- `Automagik-Omni-1.0.0.dmg` (~130MB) - Installer
- `Automagik-Omni-1.0.0-mac.zip` - Archive

**Windows:**
- `Automagik-Omni-1.0.0-setup.exe` (~120MB) - Installer
- `Automagik-Omni-1.0.0-portable.exe` - Portable

---

## 🔧 Configuration

### Backend Configuration

Backend reads configuration from:
1. `.env` file (if present)
2. Environment variables
3. Default values

**Key variables:**
```bash
AUTOMAGIK_OMNI_API_HOST=127.0.0.1
AUTOMAGIK_OMNI_API_PORT=8882
AUTOMAGIK_OMNI_API_KEY=your-secure-key
AUTOMAGIK_OMNI_DATABASE_URL=sqlite:///./automagik-omni.db
```

### Electron Configuration

Electron manages backend lifecycle:
- **Development**: Uses `uv run python` (API runs separately)
- **Production**: Spawns bundled backend from `resources/backend/`

**Main process** (`ui/lib/main/backend-manager.ts`):
- Auto-starts backend on app launch
- Health checks via `http://localhost:8882/health`
- Graceful shutdown on app quit
- Auto-restart on crash (max 3 attempts)

---

## 🎯 Distribution

### Linux

**AppImage (Recommended):**
```bash
# Make executable
chmod +x Automagik-Omni-1.0.0.AppImage

# Run
./Automagik-Omni-1.0.0.AppImage
```

**Debian Package:**
```bash
sudo dpkg -i automagik-omni_1.0.0_amd64.deb
automagik-omni
```

### macOS

**DMG:**
1. Open `Automagik-Omni-1.0.0.dmg`
2. Drag app to Applications folder
3. Launch from Applications

**Code Signing:**
```bash
# Sign the app (requires Apple Developer account)
export APPLE_ID="your@email.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="XXXXXXXXXX"

pnpm run electron:build:mac
```

### Windows

**NSIS Installer:**
1. Run `Automagik-Omni-1.0.0-setup.exe`
2. Follow installation wizard
3. Launch from Start Menu or Desktop shortcut

**Silent Install:**
```cmd
Automagik-Omni-1.0.0-setup.exe /S
```

---

## 🔄 Auto-Updates

### Configuration

Auto-updates configured in `electron-builder.yml`:
```yaml
publish:
  provider: github
  owner: namastexlabs
  repo: automagik-omni
  releaseType: release
```

### Release Process

1. **Tag Release:**
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

2. **Build All Platforms:**
   ```bash
   ./scripts/build-desktop.sh linux
   ./scripts/build-desktop.sh darwin
   ./scripts/build-desktop.sh windows
   ```

3. **Create GitHub Release:**
   ```bash
   gh release create v1.0.1 \
     ui/dist/*.AppImage \
     ui/dist/*.deb \
     ui/dist/*.dmg \
     ui/dist/*.exe \
     --title "Version 1.0.1" \
     --notes "Release notes here"
   ```

4. **Auto-Update Triggers:**
   - App checks for updates on startup
   - Downloads in background
   - Prompts user to install
   - Installs on next restart

---

## 🧪 Testing

### Manual Testing

1. **Build unpacked version:**
   ```bash
   ./scripts/build-desktop.sh dir
   ```

2. **Run tests:**
   ```bash
   ./scripts/test-bundle.sh
   ```

3. **Launch app:**
   ```bash
   # Linux
   ./ui/dist/linux-unpacked/automagik-omni

   # macOS
   ./ui/dist/mac/Automagik\ Omni.app/Contents/MacOS/Automagik\ Omni

   # Windows
   ./ui/dist/win-unpacked/AutomagikOmni.exe
   ```

### Automated Testing

```bash
# Test backend bundle
cd dist-python
./automagik-omni-backend --help

# Test backend API
./automagik-omni-backend &
sleep 5
curl http://localhost:8882/health
kill %1

# Test UI bundle
./scripts/test-bundle.sh
```

---

## 🐛 Troubleshooting

### Backend Issues

**Backend fails to start:**
```bash
# Check backend logs in UI
# Logs appear in: ~/Library/Logs/Automagik Omni/ (macOS)
#                 ~/.config/automagik-omni/logs/ (Linux)
#                 %APPDATA%\automagik-omni\logs\ (Windows)

# Test backend manually
./resources/backend/automagik-omni-backend --help
```

**Missing Python dependencies:**
- Rebuild backend: `./scripts/build-backend.sh`
- Check PyInstaller spec file: `automagik-omni-backend.spec`
- Add missing imports to `hiddenimports` list

### Electron Issues

**App won't start:**
```bash
# Run from terminal to see errors
./Automagik-Omni.AppImage --no-sandbox

# Check Electron logs
tail -f ~/.config/automagik-omni/logs/main.log
```

**Backend connection fails:**
- Check if port 8882 is available
- Verify firewall allows localhost connections
- Check backend process is running (Activity Monitor/Task Manager)

### Build Issues

**PyInstaller fails:**
```bash
# Clean build
rm -rf build/ dist/ dist-python/
./scripts/build-backend.sh

# Verbose output
pyinstaller --log-level DEBUG automagik-omni-backend.spec
```

**electron-builder fails:**
```bash
# Clean build
cd ui
rm -rf dist/ out/
pnpm run build:unpack

# Verbose output
DEBUG=electron-builder pnpm run electron:build:dir
```

---

## 📊 Size Optimization

### Current Sizes

| Platform | Installer | Installed |
|----------|-----------|-----------|
| Linux    | ~115 MB   | ~240 MB   |
| macOS    | ~130 MB   | ~270 MB   |
| Windows  | ~120 MB   | ~250 MB   |

### Reduce Size

**Backend:**
```python
# In automagik-omni-backend.spec
excludes=[
    'tkinter',      # GUI library (not needed)
    'matplotlib',   # Plotting (not needed)
    'numpy',        # Heavy math (if not used)
    'pandas',       # Data analysis (if not used)
]
```

**Electron:**
```yaml
# In electron-builder.yml
compression: maximum  # Slower build, smaller output
```

---

## 🔐 Code Signing

### macOS

1. **Get Apple Developer Certificate**
2. **Configure identity:**
   ```bash
   export CSC_LINK="/path/to/certificate.p12"
   export CSC_KEY_PASSWORD="certificate-password"
   ```
3. **Enable signing:**
   ```yaml
   # In electron-builder.yml
   mac:
     identity: "Developer ID Application: Your Name (TEAM_ID)"
     hardenedRuntime: true
   ```
4. **Notarize:**
   ```bash
   export APPLE_ID="your@email.com"
   export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
   pnpm run electron:build:mac
   ```

### Windows

1. **Get Code Signing Certificate** (.pfx file)
2. **Configure certificate:**
   ```bash
   export WIN_CSC_LINK="/path/to/certificate.pfx"
   export WIN_CSC_KEY_PASSWORD="certificate-password"
   ```
3. **Enable signing:**
   ```yaml
   # In electron-builder.yml
   win:
     certificateFile: "${env.WIN_CSC_LINK}"
     certificatePassword: "${env.WIN_CSC_KEY_PASSWORD}"
   ```

---

## 🎓 Best Practices

### Development

1. **Test unpacked builds first** - Much faster iteration
2. **Use separate test database** - Don't corrupt dev data
3. **Check backend logs** - Backend issues are common
4. **Test on clean VM** - Verify no system dependencies

### Production

1. **Always code sign** - Users trust signed apps
2. **Test installers thoroughly** - Fresh installs on each platform
3. **Version bump properly** - Follow semver (1.0.0, 1.0.1, etc.)
4. **Write release notes** - Users appreciate changelogs
5. **Monitor crash reports** - Use error tracking (Sentry, etc.)

### CI/CD

1. **Build on native platforms** - Can't cross-compile
2. **Cache dependencies** - Faster builds (node_modules, .venv)
3. **Parallel builds** - Linux, macOS, Windows simultaneously
4. **Automated testing** - Run test-bundle.sh in CI
5. **Staged rollout** - Release to beta users first

---

## 📚 Additional Resources

### Documentation

- [Electron Builder Docs](https://www.electron.build/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [electron-updater](https://www.electron.build/auto-update)

### Project Files

- `automagik-omni-backend.spec` - PyInstaller configuration
- `ui/electron-builder.yml` - Electron builder configuration
- `ui/lib/main/backend-manager.ts` - Backend process management
- `PYINSTALLER_BUILD.md` - Detailed PyInstaller guide

### Scripts

- `scripts/build-backend.sh` - Build Python backend
- `scripts/build-desktop.sh` - Build complete desktop app
- `scripts/test-bundle.sh` - Test bundled application

---

## 🆘 Support

**Issues?** Open an issue on GitHub with:
- Platform (OS + version)
- Build logs
- Error messages
- Steps to reproduce

**Questions?** Check existing issues or start a discussion.

---

Built with ❤️ by Namastex Labs
