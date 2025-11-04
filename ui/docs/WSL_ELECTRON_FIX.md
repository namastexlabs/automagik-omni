# Electron Display Issue in WSL - Fix Guide

## Problem
Electron window starts but remains invisible/blank in WSL2, even though the browser version works perfectly.

## Quick Solution: Use Browser Version
The easiest solution is to **use the browser version** which has 100% feature parity:

```bash
cd ui && pnpm run dev
```

Then open **http://localhost:5173** in your browser (Chrome/Edge recommended).

---

## Permanent Electron Fix (if needed)

### Option 1: Add Electron Command Line Switches (Recommended)

Edit `ui/lib/main/main.ts` and add these lines BEFORE `app.whenReady()`:

```typescript
// Add at the top of the file, after imports
app.commandLine.appendSwitch('disable-gpu')
app.commandLine.appendSwitch('disable-software-rasterizer')
app.commandLine.appendSwitch('disable-gpu-compositing')
app.commandLine.appendSwitch('no-sandbox')
```

### Option 2: Environment Variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export LIBGL_ALWAYS_SOFTWARE=1
export ELECTRON_DISABLE_GPU=1
export DISPLAY=:0
```

Then reload: `source ~/.bashrc`

### Option 3: Update WSLg

Make sure you're running the latest Windows version with WSLg support:

```powershell
# In PowerShell (Windows side)
wsl --update
wsl --shutdown
```

Then restart WSL.

### Option 4: Use X11 Server (VcXsrv or Xming)

Install VcXsrv on Windows, then in WSL:

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

---

## Verification

After applying any fix, test with:

```bash
cd ui
pkill -9 electron  # Kill any stuck processes
pnpm run dev
```

The window should appear on your Windows desktop.

---

## Notes

- This is a known Electron + WSL2 + GPU issue
- The browser version is production-ready and recommended for WSL development
- All features work identically in both Electron and browser versions
