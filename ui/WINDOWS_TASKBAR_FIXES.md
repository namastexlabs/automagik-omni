# Windows Task Manager Icon & Process Grouping Fixes

## Issues Fixed

### Issue 1: Omni Icon Not Showing in Task Manager ❌ → ✅
**Problem**: Windows Task Manager showed generic Electron icon instead of Omni icon

**Root Cause**:
- App User Model ID (AUMID) mismatch between main.ts and electron-builder.yml
- Main process was using `com.automagik.omni`
- Builder config specified `com.namastex.automagik-omni`

**Fix Applied**:
1. **ui/lib/main/main.ts** (line 57-58):
   - Changed AUMID from `com.automagik.omni` to `com.namastex.automagik-omni`
   - Now matches electron-builder.yml appId exactly

2. **ui/lib/main/app.ts** (line 39):
   - Added `affinity: 'main-window'` to webPreferences
   - Ensures proper icon display in Windows

3. **ui/electron-builder.yml** (lines 65-66):
   - Added explicit `publisherName: Namastex Labs`
   - Added `artifactName` configuration for consistent naming

### Issue 2: Multiple Process Entries in Task Manager ❌ → ✅
**Problem**: Task Manager showed separate entries:
- "Electron (4)" - Generic icon
- "automagik-omni-backend (2)" - Generic icon

**Desired Behavior**: Single grouped entry "Automagik Omni" with all child processes

**Fix Applied**:
1. **ui/lib/main/process-grouping.ts** (NEW FILE):
   - Created Windows process grouping utilities
   - Monitors PM2 processes and sets AUMID for child processes
   - Ensures all processes (Electron + backend) share same App User Model ID

2. **ui/lib/main/main.ts** (lines 5, 60-68):
   - Import `initializeProcessGrouping`
   - Initialize process grouping on Windows after app ready
   - Monitors PM2 processes every 30 seconds

3. **ecosystem.config.js** (lines 72-87):
   - Set `ELECTRON_AUMID` environment variable for PM2 processes
   - All spawned children (api, discord, wait) inherit AUMID
   - Processes automatically group in Task Manager

## Technical Details

### App User Model ID (AUMID)
- **Purpose**: Windows uses AUMID to group related processes
- **Value**: `com.namastex.automagik-omni`
- **Scope**: Must be identical across:
  - Electron main process
  - PM2 parent process
  - All PM2 child processes (api, discord, wait)

### How Process Grouping Works
```
┌──────────────────────────────────────────────────┐
│ Automagik Omni (AUMID: com.namastex...)         │
├──────────────────────────────────────────────────┤
│ ▶ Omni UI - Manager (PID: xxxx)                  │
│   ├─ Omni UI - Renderer                         │
│   └─ Omni UI - GPU                              │
│ ▶ PM2 Daemon (PID: yyyy)                        │
│   ├─ Omni Backend - API                         │
│   ├─ Omni Backend - Discord                     │
│   └─ Omni Backend - Health Check (stopped)      │
└──────────────────────────────────────────────────┘
```

### Issue 3: Descriptive Process Names ✅
**Problem**: Processes showed generic names like "python.exe", "node.exe", "AutomagikOmni.exe"

**Fix Applied**:
1. **Electron Processes** (ui/lib/main/main.ts, ui/lib/main/app.ts):
   - Main Process: `Omni UI - Manager`
   - Renderer: `Omni UI - Renderer`
   - Window Title: `Omni UI - Main Window`

2. **PM2 Backend Processes** (ecosystem.config.js):
   - API Server: `Omni Backend - API` (was: automagik-omni-api)
   - Discord Bot: `Omni Backend - Discord` (was: automagik-omni-discord)
   - Health Check: `Omni Backend - Health Check` (was: automagik-omni-wait)

3. **Dashboard UI** (app/pages/Dashboard.tsx):
   - Removed name truncation, shows full descriptive names
   - Clear visibility of what each process does

### Files Modified
1. **ui/lib/main/main.ts**
   - Fixed AUMID to match electron-builder.yml
   - Added process grouping initialization
   - Set app name: `Omni UI - Manager`

2. **ui/lib/main/app.ts**
   - Added webPreferences.affinity for icon display
   - Set window title: `Omni UI - Main Window`
   - Set renderer title: `Omni UI - Renderer`

3. **ui/lib/main/process-grouping.ts** (NEW)
   - Windows process grouping utilities
   - PM2 process monitoring
   - AUMID management

4. **ui/lib/main/backend-monitor.ts**
   - Updated process name filters: `Omni Backend`
   - Direct process name: `Omni Backend - API`

5. **ui/electron-builder.yml**
   - Added publisherName
   - Ensured consistent naming

6. **ecosystem.config.js**
   - Set ELECTRON_AUMID environment variable
   - Renamed all PM2 processes to descriptive names:
     - `Omni Backend - API`
     - `Omni Backend - Discord`
     - `Omni Backend - Health Check`
   - Added PROCESS_TITLE env var for each

7. **app/pages/Dashboard.tsx**
   - Show full process names (removed truncation)

## Testing Instructions

### Development Environment (WSL/Linux)
```bash
cd ui
pnpm dev  # Changes won't be visible on WSL
```

### Windows Build (Required for Testing)
```bash
# Build the Windows executable
cd ui
pnpm run build:win

# Install and run the built executable
# Check Windows Task Manager:
# - Should see single "Automagik Omni" entry with Omni icon
# - Expand to see child processes grouped underneath
```

### Verification Checklist
- [ ] Single "Automagik Omni" entry in Task Manager
- [ ] Omni icon displayed (not generic Electron icon)
- [ ] Child processes grouped under parent (expandable ▶)
- [ ] Backend processes (api, discord) show under same parent
- [ ] Taskbar shows single icon with Omni branding

## Expected Behavior After Fix

### Before (Broken) ❌
```
Task Manager:
├─ Electron (4)              [Generic Electron icon]
└─ automagik-omni-backend (2) [Generic Python/Node icon]
```

### After (Fixed) ✅
```
Task Manager:
└─ ▶ Automagik Omni              [Omni icon]
     ├─ Omni UI - Manager         (main electron process)
     ├─ Omni UI - Renderer        (renderer process)
     ├─ Omni UI - GPU             (gpu process)
     ├─ PM2 Daemon                (pm2 manager)
     ├─ Omni Backend - API        (fastapi server)
     ├─ Omni Backend - Discord    (discord bot)
     └─ Omni Backend - Health Check (health monitor)
```

## Notes

### Why AUMID Matters
- Windows uses AUMID for:
  - Task Manager process grouping
  - Taskbar icon association
  - Jump list management
  - Toast notification attribution

### Development vs Production
- **Development**: Process grouping only works in built executables
- **Production**: Full grouping with icon works out-of-the-box

### PM2 Considerations
- PM2 spawns child processes with inherited environment
- Setting `ELECTRON_AUMID` in ecosystem.config.js ensures inheritance
- All automagik-omni-* processes share same AUMID

## Troubleshooting

### Issue: Icon Still Generic
- Ensure AUMID matches exactly in all files
- Rebuild Windows executable (`pnpm run build:win`)
- Clear Windows icon cache (restart explorer.exe)

### Issue: Processes Not Grouped
- Check PM2 processes have ELECTRON_AUMID set: `pm2 env 0`
- Verify ecosystem.config.js is being used
- Restart PM2: `make stop-local && make start-local`

### Issue: Multiple "Automagik Omni" Entries
- Check for duplicate AUMID registrations
- Ensure only one instance running
- Close all instances and restart

## References
- [Windows App User Model IDs](https://docs.microsoft.com/en-us/windows/win32/shell/appids)
- [Electron Builder Windows Config](https://www.electron.build/configuration/win)
- [PM2 Process Management](https://pm2.keymetrics.io/docs/usage/application-declaration/)
