# Desktop App API Key Authentication Fix

**Status**: ✅ FIXED
**Date**: 2025-10-24
**Issue**: Windows Electron app making API calls with empty `x-api-key` header, causing 401 errors

---

## Problem Analysis

### Root Cause

The desktop app had **duplicate configuration loading** that caused a mismatch between the backend's expected API key and the UI client's provided API key:

1. **Backend initialization** (`backend-handler.ts`):
   - Read `.env` file to get `AUTOMAGIK_OMNI_API_KEY`
   - Generated a random API key if none was configured
   - Started backend process with this API key

2. **UI client initialization** (`app.ts`):
   - Read `.env` file **SEPARATELY** (duplicate read)
   - Could get a different value due to timing, caching, or parsing differences
   - Initialized HTTP client with potentially different API key

3. **Result**:
   - Backend: "I expect API key X"
   - UI: "I'm sending API key Y" (or empty string)
   - Backend: "401 Unauthorized"

### Evidence from Logs

```
Request headers: {..., 'x-api-key': '', ...}
⚠️ No API key provided in x-api-key header
✓ API Response: 401 - 0.002s
Error: Missing API key
```

The empty `x-api-key` header confirmed that the UI client was not receiving the API key from configuration.

---

## Solution Implementation

### Architecture Changes

Created a **shared configuration loader** that ensures both backend and UI use the SAME API key:

#### New File: `ui/lib/main/config-loader.ts`

- Single source of truth for API configuration
- Caches configuration after first read (prevents duplicate reads)
- Generates default API key if none is configured
- Provides diagnostic logging

Key features:
```typescript
export interface AppConfig {
  apiHost: string
  apiPort: number
  apiKey: string
  apiUrl: string
}

export function loadAppConfig(): AppConfig {
  // Cached config ensures consistency
  if (cachedConfig) return cachedConfig

  // Load from .env file
  // Generate default key if empty
  // Cache and return
}
```

#### Modified Files

1. **`ui/lib/main/app.ts`**:
   - Removed duplicate `loadEnvConfig()` function
   - Imports `loadAppConfig()` from shared config-loader
   - Uses cached config for `initOmniClient()`

2. **`ui/lib/conveyor/handlers/backend-handler.ts`**:
   - Removed duplicate `loadEnvConfig()` function
   - Imports `loadAppConfig()` from shared config-loader
   - Uses cached config for `initBackendManager()`

### Benefits

✅ **Single source of truth**: Config loaded once, used everywhere
✅ **Consistency guaranteed**: Backend and UI always use the same API key
✅ **Automatic fallback**: Generates secure key if `.env` is empty
✅ **Better diagnostics**: Logs API key (masked) for debugging
✅ **No manual setup**: Works out-of-box for fresh installations

---

## Testing Plan

### Phase 1: Fresh Installation Test

**Scenario**: New user installs desktop app, no `.env` customization

**Steps**:
1. Delete or rename `.env` file (simulate fresh install)
2. Start desktop app
3. Verify backend starts successfully
4. Verify UI can list instances (`/api/v1/instances`)
5. Check console logs for generated API key message

**Expected**:
```
🔑 Generated default API key for desktop installation
📋 API Configuration loaded:
  - API URL: http://localhost:8882
  - API Key: desktop-***
```

### Phase 2: Configured `.env` Test

**Scenario**: User has customized `AUTOMAGIK_OMNI_API_KEY` in `.env`

**Steps**:
1. Ensure `.env` contains: `AUTOMAGIK_OMNI_API_KEY=namastex888`
2. Start desktop app
3. Verify backend accepts this API key
4. Verify UI uses this API key for requests
5. Check logs confirm key is loaded from `.env`

**Expected**:
```
📁 Loading configuration from: /path/to/.env
📋 API Configuration loaded:
  - API URL: http://localhost:8882
  - API Key: namastex***
```

### Phase 3: API Request Validation

**Scenario**: Confirm API calls include correct `x-api-key` header

**Steps**:
1. Open DevTools Network tab
2. Trigger API call (e.g., list instances)
3. Inspect request headers
4. Verify `x-api-key` header is NOT empty
5. Verify response is 200 OK (not 401)

**Expected**:
```
Request Headers:
  x-api-key: desktop-abc123xyz... (or namastex888 if configured)
  Content-Type: application/json
  ...

Response:
  Status: 200 OK
  Body: [{"id": "...", "name": "..."}]
```

### Phase 4: Backend Startup Validation

**Scenario**: Backend receives correct API key via environment

**Steps**:
1. Check backend logs in Electron console
2. Verify `AUTOMAGIK_OMNI_API_KEY` is set in backend environment
3. Confirm backend accepts requests with matching key

**Expected Backend Environment**:
```
AUTOMAGIK_OMNI_API_HOST=127.0.0.1
AUTOMAGIK_OMNI_API_PORT=8882
AUTOMAGIK_OMNI_API_KEY=desktop-abc123xyz (or namastex888)
```

---

## Code References

### Key Files Modified

1. **`/ui/lib/main/config-loader.ts`** (NEW)
   - Lines 14-24: `generateDefaultApiKey()` - Secure random key generation
   - Lines 31-97: `loadAppConfig()` - Main configuration loader
   - Lines 88-92: Caching logic to ensure consistency

2. **`/ui/lib/main/app.ts`**
   - Line 9: Import shared config loader
   - Line 19-20: Use `loadAppConfig()` instead of local function

3. **`/ui/lib/conveyor/handlers/backend-handler.ts`**
   - Line 4: Import shared config loader
   - Lines 25-35: Use `loadAppConfig()` for backend manager init

### Configuration Flow

```
App Startup (main.ts)
    │
    ├─→ startBackendOnStartup()
    │    └─→ initBackendManager()
    │         └─→ loadAppConfig() ──→ [CACHED CONFIG]
    │              └─→ BackendManager(apiKey: X)
    │
    └─→ createAppWindow()
         └─→ initOmniClient()
              └─→ loadAppConfig() ──→ [CACHED CONFIG] (same instance!)
                   └─→ OmniApiClient(apiKey: X)  ← MATCHES!
```

---

## Rollout Checklist

### Before Merging

- [x] Code changes implemented
- [x] TypeScript compilation verified
- [ ] Manual testing on Windows (user to verify)
- [ ] Manual testing on macOS (if applicable)
- [ ] Check DevTools Network tab for correct headers
- [ ] Verify backend logs show matching API key

### After Merging

- [ ] Update deployment documentation
- [ ] Add troubleshooting section to README
- [ ] Create release notes mentioning fix
- [ ] Test packaged builds (.exe, .dmg)

---

## Troubleshooting Guide

### If API calls still fail with 401

1. **Check console logs for API key**:
   ```
   Look for: "API Key: xxxxxx***"
   ```

2. **Verify `.env` file parsing**:
   ```bash
   # Ensure no extra spaces or quotes
   AUTOMAGIK_OMNI_API_KEY=your-key-here
   # NOT:
   AUTOMAGIK_OMNI_API_KEY= your-key-here  # ← extra space
   ```

3. **Check backend environment**:
   - Open Electron DevTools Console
   - Look for backend startup logs
   - Verify `AUTOMAGIK_OMNI_API_KEY` is set

4. **Force config reload**:
   - Restart desktop app
   - Config cache resets on app restart

### If backend won't start

1. **Check port conflicts**:
   ```bash
   # Windows
   netstat -ano | findstr :8882

   # macOS/Linux
   lsof -i :8882
   ```

2. **Check backend logs**:
   - Look for binding errors
   - Verify Python/backend executable exists

---

## Security Considerations

### Why auto-generate API key is safe for desktop

1. **Localhost only**: Backend binds to `127.0.0.1` (not `0.0.0.0`)
2. **Same machine**: UI and backend run on same computer
3. **Process isolation**: Each user's app has unique generated key
4. **No network exposure**: Desktop app is not a server

### For production deployments

If deploying as a server (not desktop app):
- **MUST** configure strong `AUTOMAGIK_OMNI_API_KEY` in `.env`
- **MUST** use HTTPS/TLS for API endpoints
- **MUST** implement rate limiting
- **MUST** rotate API keys regularly

---

## Future Improvements

1. **Key rotation**: Allow users to regenerate API key from UI
2. **Multi-key support**: Different keys for different services
3. **Key management UI**: Settings panel to view/edit API key
4. **Encrypted storage**: Store generated keys in OS keychain
5. **Audit logging**: Track API key usage and failed auth attempts

---

## Related Issues

- Original issue: Windows desktop app 401 errors
- Related: #XXX - Backend authentication hardening
- Related: #XXX - Desktop app configuration management

---

## Validation Checklist

After applying this fix, confirm:

- [ ] Backend starts without errors
- [ ] UI loads without 401 errors
- [ ] Instance list loads successfully
- [ ] Contacts/chats endpoints return 200 OK
- [ ] Console shows correct API key (masked)
- [ ] Network tab shows `x-api-key` header populated
- [ ] Fresh install works without `.env` customization
- [ ] Configured `.env` is respected
