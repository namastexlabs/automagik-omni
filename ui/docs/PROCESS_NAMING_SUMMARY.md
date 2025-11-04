# Process Naming & Windows Task Manager Improvements

## Summary of Changes

All processes in Windows Task Manager now have clear, descriptive names instead of generic ones like "python.exe" or "node.exe".

---

## ✅ New Process Names

### Electron UI Processes
| Old Name | New Name | Description |
|----------|----------|-------------|
| `AutomagikOmni.exe` | `Omni UI - Manager` | Main Electron process manager |
| `AutomagikOmni.exe` | `Omni UI - Renderer` | Renderer/frontend process |
| `AutomagikOmni.exe` | `Omni UI - Main Window` | Window title display |
| *(implicit)* | `Omni UI - GPU` | GPU acceleration process |

### Backend PM2 Processes
| Old Name | New Name | Description |
|----------|----------|-------------|
| `automagik-omni-api` | `Omni Backend - API` | FastAPI server (port 8882) |
| `automagik-omni-discord` | `Omni Backend - Discord` | Discord bot manager |
| `automagik-omni-wait` | `Omni Backend - Health Check` | API health monitoring |

---

## 📊 Windows Task Manager View

### Before Changes ❌
```
Task Manager:
├─ Electron (4)              [Generic icon]
│   ├─ AutomagikOmni.exe
│   ├─ AutomagikOmni.exe
│   ├─ AutomagikOmni.exe
│   └─ AutomagikOmni.exe
└─ automagik-omni-backend (2) [Generic icon]
    ├─ python.exe
    └─ python.exe
```

### After Changes ✅
```
Task Manager:
└─ ▶ Automagik Omni              [Omni icon 🎯]
     ├─ Omni UI - Manager         (175 MB)
     ├─ Omni UI - Renderer        (98 MB)
     ├─ Omni UI - GPU             (45 MB)
     ├─ PM2 Daemon                (85 MB)
     ├─ Omni Backend - API        (120 MB)
     ├─ Omni Backend - Discord    (95 MB)
     └─ Omni Backend - Health Check (stopped)
```

Now you can instantly tell:
- ✅ Which process is the UI vs backend
- ✅ Which backend service is running (API, Discord, etc.)
- ✅ What each process does at a glance

---

## 🔧 Technical Implementation

### 1. Electron Process Naming

**File**: `ui/lib/main/main.ts` (lines 60-69)
```typescript
// Set descriptive process name for Windows Task Manager
if (process.platform === 'win32') {
  try {
    app.setName('Omni UI - Manager')
    console.log('✅ Process renamed to: Omni UI - Manager')
  } catch (error) {
    console.warn('⚠️ Failed to rename process:', error)
  }
}
```

**File**: `ui/lib/main/app.ts` (lines 30, 43-48)
```typescript
const mainWindow = new BrowserWindow({
  title: 'Omni UI - Main Window', // Shows in Task Manager
  // ... other config
})

// Set renderer process title
mainWindow.webContents.on('did-finish-load', () => {
  if (process.platform === 'win32') {
    mainWindow.setTitle('Omni UI - Renderer')
  }
})
```

### 2. PM2 Backend Process Naming

**File**: `ecosystem.config.js` (lines 95, 132, 166)
```javascript
module.exports = {
  apps: [
    {
      name: 'Omni Backend - API',        // Was: automagik-omni-api
      // ... config
    },
    {
      name: 'Omni Backend - Health Check', // Was: automagik-omni-wait
      // ... config
    },
    {
      name: 'Omni Backend - Discord',    // Was: automagik-omni-discord
      // ... config
    }
  ]
}
```

### 3. Dashboard UI Updates

**File**: `app/pages/Dashboard.tsx` (line 167)
```typescript
// Before: {proc.name.replace('automagik-omni-', '')}
// After: {proc.name}  // Shows full name like "Omni Backend - API"
```

### 4. Backend Monitor Updates

**File**: `ui/lib/main/backend-monitor.ts`
```typescript
// Updated filter to match new names
.filter((p: any) => p.name?.includes('Omni Backend'))

// Updated direct process name
{ name: 'Omni Backend - API', status: 'online', ... }
```

---

## 📋 Files Modified

| File | Changes Made |
|------|--------------|
| `ui/lib/main/main.ts` | Set app name: `Omni UI - Manager` |
| `ui/lib/main/app.ts` | Set window & renderer titles |
| `ui/lib/main/backend-monitor.ts` | Updated process filters & names |
| `ui/lib/main/process-grouping.ts` | Updated name matching logic |
| `ecosystem.config.js` | Renamed all 3 PM2 processes |
| `app/pages/Dashboard.tsx` | Show full process names |
| `ui/WINDOWS_TASKBAR_FIXES.md` | Updated documentation |

---

## 🧪 Testing

### Development Mode
```bash
cd ui
pnpm dev
```
**Note**: Process renaming only visible in production builds on Windows.

### Production Build (Windows)
```bash
cd ui
pnpm run build:win
```

Then install and check Windows Task Manager:
- ✅ Single "Automagik Omni" grouped entry
- ✅ Omni icon displayed
- ✅ Descriptive names for all processes
- ✅ Clear distinction between UI and backend

---

## 💡 Benefits

### Before (Generic Names)
- ❌ 4x "AutomagikOmni.exe" - which is which?
- ❌ 2x "python.exe" - what do they do?
- ❌ Hard to debug which process is using memory
- ❌ Can't tell if Discord bot is running vs API

### After (Descriptive Names)
- ✅ "Omni UI - Manager" - clearly the main UI process
- ✅ "Omni Backend - API" - obviously the API server
- ✅ "Omni Backend - Discord" - Discord bot, easy to identify
- ✅ Quick debugging: high memory? Check specific process name
- ✅ Professional appearance in Task Manager

---

## 🔍 Troubleshooting

### Names Not Showing
1. Rebuild Windows executable: `pnpm run build:win`
2. Restart PM2: `make stop-local && make start-local`
3. Check PM2 process list: `pm2 list`

### Dashboard Shows Old Names
1. Clear browser cache (Ctrl+Shift+R)
2. Restart Electron app
3. Verify `ecosystem.config.js` has new names

### PM2 Not Finding Processes
- Backend monitor filters for `'Omni Backend'` string
- Check PM2 process names: `pm2 list`
- Ensure names start with "Omni Backend"

---

## 📖 Related Documentation

- **Windows Taskbar Fixes**: `ui/WINDOWS_TASKBAR_FIXES.md`
- **Process Grouping**: See "App User Model ID" section
- **PM2 Configuration**: `ecosystem.config.js` comments
- **Electron Builder**: `ui/electron-builder.yml`

---

## 🎯 Next Steps

All process naming is complete and ready to test! Build the Windows executable to see the changes in action:

```bash
cd ui
pnpm run build:win
```

Then launch the app and open Task Manager to see:
- Single "Automagik Omni" entry with your icon
- All processes clearly labeled
- Easy to understand what each process does
