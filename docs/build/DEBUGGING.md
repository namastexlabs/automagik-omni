# Debugging Desktop Builds

This guide explains how to debug production builds of the Automagik Omni desktop application.

## 🐛 Common Issues

### Black Screen on Windows

**Symptoms:**
- App installs successfully
- Window opens but shows only black screen
- Omni logo appears in taskbar/title

**Cause:** GPU acceleration was disabled for all Windows builds (originally added for WSL compatibility)

**Fix Applied:** GPU acceleration now only disables in WSL environment, not production Windows

**Verification:**
```bash
# Check the fix in ui/lib/main/main.ts
# GPU is only disabled when isWSL is true
```

---

## 🔍 How to Debug Production Builds

### Method 1: Enable Electron Logging (Windows)

**Option A: Command Line**
```cmd
# Run from Command Prompt
"C:\Program Files\Automagik Omni\Automagik Omni.exe" --enable-logging

# Logs will appear in console
```

**Option B: Environment Variable**
```cmd
# Set environment variable then run app
set ELECTRON_ENABLE_LOGGING=1
"C:\Program Files\Automagik Omni\Automagik Omni.exe"
```

**Option C: Create Debug Shortcut**
1. Right-click app shortcut → Properties
2. In "Target" field, append: ` --enable-logging`
3. Example: `"C:\...\Automagik Omni.exe" --enable-logging`
4. Click OK

### Method 2: View Log Files

**Windows Logs:**
```
%APPDATA%\automagik-omni\logs\
```

**Linux Logs:**
```
~/.config/automagik-omni/logs/
```

**macOS Logs:**
```
~/Library/Logs/automagik-omni/
```

### Method 3: Open DevTools in Production

**Add to app launch:**
```cmd
# Windows
"C:\Program Files\Automagik Omni\Automagik Omni.exe" --remote-debugging-port=9222

# Then open Chrome/Edge to:
chrome://inspect
# Click "Configure" and add localhost:9222
```

**Or use Keyboard Shortcut:**
- **F12** - Toggle DevTools (if enabled in build)
- **Ctrl+Shift+I** (Windows/Linux) - Alternative
- **Cmd+Option+I** (macOS) - Alternative

### Method 4: Check Backend Status

The Python backend runs as a subprocess. To verify it's working:

**Windows:**
```cmd
# Check if backend is running
tasklist | findstr automagik-omni-backend

# Check backend port
netstat -ano | findstr 8882
```

**Linux/macOS:**
```bash
# Check if backend is running
ps aux | grep automagik-omni-backend

# Check backend port
lsof -i :8882
```

---

## 📋 Collecting Debug Information

### Full Debug Report

Create a debug report with:

1. **App Version**
   - Help → About (in app)
   - Or check: `%APPDATA%\automagik-omni\version.txt`

2. **Console Output**
   ```cmd
   "C:\Program Files\Automagik Omni\Automagik Omni.exe" --enable-logging > debug.log 2>&1
   ```

3. **System Information**
   - OS version
   - GPU details (for black screen issues)
   - Antivirus software (may block backend)

4. **Backend Logs**
   ```
   # Backend logs location
   Windows: %APPDATA%\automagik-omni\backend\logs\
   Linux: ~/.config/automagik-omni/backend/logs/
   macOS: ~/Library/Logs/automagik-omni/backend/
   ```

5. **Error Screenshots**
   - Include full window
   - Include any error dialogs

---

## 🔧 Debug Build (Development)

To build with debug symbols and logging enabled:

```bash
cd ui

# Set environment for debug build
export NODE_ENV=development
export ELECTRON_ENABLE_LOGGING=1

# Build with development settings
pnpm run build:unpack

# The unpacked build will be in dist/*-unpacked/
# Run directly without installing:
# Windows: dist/win-unpacked/AutomagikOmni.exe
# Linux: dist/linux-unpacked/automagik-omni
# macOS: open dist/mac/Automagik\ Omni.app
```

### Development vs Production Builds

| Feature | Development | Production |
|---------|-------------|------------|
| DevTools | Auto-open | F12 only |
| Logging | Verbose | Minimal |
| GPU (WSL) | Disabled | Enabled |
| Source Maps | Yes | No |
| Debugging | Easy | Requires flags |

---

## 🔍 Common Debugging Scenarios

### Scenario 1: App Won't Start

**Check:**
```cmd
# 1. Verify installation
dir "C:\Program Files\Automagik Omni"

# 2. Check for crash dumps
dir "%APPDATA%\automagik-omni\crashes"

# 3. Run with logging
"C:\Program Files\Automagik Omni\Automagik Omni.exe" --enable-logging
```

**Common Causes:**
- Antivirus blocking the app
- Missing VC++ Redistributables
- Corrupted installation
- Port 8882 already in use (backend conflict)

### Scenario 2: Backend Not Starting

**Check:**
```cmd
# 1. Verify backend exists
dir "C:\Program Files\Automagik Omni\resources\backend"

# 2. Test backend manually
cd "C:\Program Files\Automagik Omni\resources\backend"
automagik-omni-backend.exe --help

# 3. Check port availability
netstat -ano | findstr 8882
```

**Common Causes:**
- Backend binary missing (build issue)
- Port 8882 in use by another process
- Antivirus blocking Python execution
- Missing dependencies

### Scenario 3: Black Screen (FIXED)

**Root Cause:**
GPU acceleration was disabled for ALL Windows builds, not just WSL.

**Fix:**
Updated `ui/lib/main/main.ts` to only disable GPU when `isWSL` is true.

**Verify Fix:**
```typescript
// Check this in the source code:
const isWSL = process.env.WSL_DISTRO_NAME || process.env.WSL_INTEROP

if (isWSL) {
  // GPU only disabled in WSL now
  app.commandLine.appendSwitch('disable-gpu')
}
```

**Rebuild Required:**
Yes - this fix requires rebuilding the app to take effect.

### Scenario 4: UI Not Responding

**Check:**
1. Open DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for failed API calls
4. Verify backend is running

**Common Causes:**
- Backend API not responding (check port 8882)
- Network requests blocked by firewall
- React errors in renderer process

---

## 🎯 Quick Troubleshooting Checklist

- [ ] App installed successfully?
- [ ] Run with `--enable-logging` flag
- [ ] Check log files in `%APPDATA%\automagik-omni\logs\`
- [ ] Verify backend running (port 8882)
- [ ] Antivirus not blocking app?
- [ ] Open DevTools (F12) for errors
- [ ] Check GPU acceleration status (System Info)
- [ ] Verify VC++ Redistributables installed
- [ ] Try running as Administrator
- [ ] Check Windows Event Viewer for crashes

---

## 🛠️ Advanced Debugging

### Enable All Chromium Logging

```cmd
# Maximum verbosity
"C:\Program Files\Automagik Omni\Automagik Omni.exe" ^
  --enable-logging ^
  --log-level=0 ^
  --v=1 ^
  --vmodule=*/renderer/*=3
```

### Debug Specific Modules

```cmd
# Debug only IPC communication
--vmodule=*/ipc/*=3

# Debug only GPU
--vmodule=*/gpu/*=3

# Debug backend integration
--vmodule=*/backend/*=3
```

### Remote Debugging

```cmd
# Start with remote debugging
"C:\Program Files\Automagik Omni\Automagik Omni.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="C:\temp\debug-profile"

# Connect Chrome DevTools
# Open: chrome://inspect
# Add localhost:9222
```

---

## 📊 Automated Debugging

The app now includes automatic logging:

**In Development:**
- ✅ Auto-opens DevTools
- ✅ Verbose console logging
- ✅ Renderer error forwarding
- ✅ Stack traces for all errors

**In Production:**
- ❌ DevTools closed (F12 to open)
- ⚠️ Minimal logging
- ✅ Critical errors logged
- ❌ No stack traces (security)

---

## 🚀 Getting Help

When reporting issues, include:

1. **App Version** (Help → About)
2. **OS Version** (Settings → System → About)
3. **Log Files** (from `%APPDATA%\automagik-omni\logs\`)
4. **Steps to Reproduce**
5. **Screenshots** (including DevTools if open)
6. **Console Output** (run with `--enable-logging`)

**Where to Report:**
- GitHub Issues: https://github.com/namastexlabs/automagik-omni/issues
- Include all debug information above

---

## 🔗 Related Documentation

- [Build System](./PYINSTALLER_BUILD.md)
- [Code Signing](./CODE_SIGNING.md)
- [Desktop Distribution](./DESKTOP_DISTRIBUTION.md)
- [Electron Documentation](https://www.electronjs.org/docs/latest/tutorial/debugging-main-process)
