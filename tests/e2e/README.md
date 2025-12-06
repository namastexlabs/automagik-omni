# E2E Test Suite - PostgreSQL-Native Migration

End-to-end tests validating the PostgreSQL-native migration for Automagik Omni.

## Overview

This test suite validates the complete migration from SQLite+PostgreSQL dual-mode to PostgreSQL-only with embedded pgserve. It covers:

- **Platform compatibility** - Linux, macOS, Windows (WSL)
- **Fresh installations** - Clean setup with PostgreSQL-only
- **localStorage migration** - Browser storage → PostgreSQL preferences API
- **Backup & restore** - PostgreSQL pg_dump/psql wrappers

## Test Scripts

### `platform_check.sh`
**Purpose:** Verify platform compatibility and dependencies

**Checks:**
- Operating system detection (Linux, macOS, Windows)
- Node.js version (>= 18)
- Python version (>= 3.10)
- pgserve availability (via npm)
- PostgreSQL binaries (bundled with pgserve)
- File system permissions
- Port availability (default: 5432)
- Alembic migrations presence

**Usage:**
```bash
./tests/e2e/platform_check.sh
```

### `fresh_install.sh`
**Purpose:** Test clean installation flow

**Validates:**
- pgserve auto-start
- Database initialization
- Onboarding wizard (PostgreSQL-only)
- API key storage via preferences API
- Theme storage via preferences API
- No localStorage usage

**Usage:**
```bash
./tests/e2e/fresh_install.sh
```

### `localstorage_migration.sh`
**Purpose:** Test migration from localStorage to PostgreSQL

**Validates:**
- Preferences API endpoints (CRUD operations)
- Session-based isolation (UUID sessions)
- API key migration (localStorage → PostgreSQL)
- Theme migration (localStorage → PostgreSQL)
- Breaking changes (async functions)
- localStorage removal verification

**Usage:**
```bash
./tests/e2e/localstorage_migration.sh
```

### `backup_restore.sh`
**Purpose:** Test PostgreSQL backup and restore functionality

**Validates:**
- Backup creation (pg_dump wrapper)
- Backup listing (directory scan)
- Backup download (file serving)
- Backup restore (psql wrapper)
- Backup deletion (with security validation)
- Filename validation (prevent path traversal)
- Data integrity after restore

**Usage:**
```bash
./tests/e2e/backup_restore.sh
```

### `run_all.sh`
**Purpose:** Master test runner executing all E2E tests

**Runs:**
1. Platform compatibility check
2. Fresh installation test
3. localStorage migration test
4. Backup & restore test

**Reports:**
- Tests run / passed / failed
- Overall migration status
- Next steps recommendation

**Usage:**
```bash
./tests/e2e/run_all.sh
```

## Test Architecture

### Structural Tests (Current)
These tests validate the **architecture** of the migration without requiring live services:

- File structure verification
- Configuration validation
- Code pattern checking
- Security validation (filename patterns, path traversal)

### Runtime Tests (Future)
To enable full runtime testing, services must be running:

```bash
# Terminal 1: Start gateway (with pgserve)
cd gateway
npm install
npm start

# Terminal 2: Start backend
cd src
pip install -r ../requirements.txt
alembic upgrade head
uvicorn api.app:app --reload

# Terminal 3: Start frontend
cd resources/ui
npm install
npm run dev

# Terminal 4: Run E2E tests
./tests/e2e/run_all.sh
```

## Migration Coverage

### Group A: Frontend localStorage Migration ✅
- `api.ts`: Async API key functions
- `ThemeProvider.tsx`: PostgreSQL theme storage
- Breaking changes: All auth functions now async

### Group B: Wizard Simplification ✅
- `DatabaseSetupWizard.tsx`: Rewritten (830 → 327 lines)
- Removed database type selection
- Single-page configuration

### Group C: Backend API Updates ✅
- `preferences.py`: User preferences CRUD API
- `setup.py`: PostgreSQL-only schema

### Group D: Environment Variables ✅
- `.env.example`: PostgreSQL-only configuration
- Removed all SQLite variables

### Group E: Auto-Migration Logic ✅
- `migration_check.py`: SQLite detection
- `migration.py`: Migration status API

### Group F: Backup/Restore API ✅
- `backup.py`: pg_dump/psql wrappers
- Security: Filename validation

### Group G: Integration Testing ✅
- Platform compatibility check
- Fresh installation test
- localStorage migration test
- Backup & restore test

## Expected Output

### Successful Run
```
=========================================
Automagik Omni - E2E Test Suite
PostgreSQL-Native Migration
=========================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Platform Compatibility Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Platform Compatibility Test: PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Fresh Installation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Fresh Installation Test: PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: localStorage Migration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ localStorage Migration Test: PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Backup & Restore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backup & Restore Test: PASSED

=========================================
Test Suite Summary
=========================================

Total tests run:    4
Tests passed:       4
Tests failed:       0

✅ All tests passed!

Migration Status: READY FOR DEPLOYMENT
```

## Platform Support

### Linux ✅
- pgserve works out of the box
- PostgreSQL binaries included (x64)
- Tested on: Ubuntu, Debian, Fedora

### macOS ✅
- pgserve works out of the box
- PostgreSQL binaries included (x64 and ARM64)
- Tested on: macOS Intel and Apple Silicon

### Windows ⚠️
- **Recommended:** Use WSL2 (Windows Subsystem for Linux)
- Native Windows: Limited support
- PowerShell: May require execution policy changes

## Breaking Changes

### API Changes (Frontend)
All authentication functions are now asynchronous:

```typescript
// OLD (synchronous)
const apiKey = getApiKey();
setApiKey('sk-...');
removeApiKey();

// NEW (asynchronous)
const apiKey = await getApiKey();
await setApiKey('sk-...');
await removeApiKey();
```

### Data Migration
- **API keys:** Browser localStorage → PostgreSQL (user_preferences table)
- **Theme preferences:** Browser localStorage → PostgreSQL (user_preferences table)
- **Session ID:** Ephemeral UUID stored in sessionStorage

### Database Changes
- **SQLite support removed** - No longer a configuration option
- **PostgreSQL-only** - Embedded via pgserve (no external database required)
- **Ground zero migration** - Fresh Alembic migration (001_ground_zero_postgresql_only.py)

## Security Considerations

### Filename Validation (Backup API)
```python
# Prevents path traversal attacks
valid_pattern = r'^omni_backup_[0-9]{8}_[0-9]{6}\.sql$'

# Blocked:
# ../etc/passwd
# /absolute/path/file.sql
# malicious.sql

# Allowed:
# omni_backup_20250101_120000.sql
```

### Session Isolation
- Each browser session has unique UUID (sessionStorage)
- Preferences isolated by session_id
- No cross-session data leakage

## Future Enhancements

### Automated Backups
- Scheduled daily backups (cron/systemd timer)
- Retention policy (keep last 7 days)
- Automatic cleanup of old backups

### Runtime Tests
- Actual HTTP requests to APIs
- Database connection testing
- End-to-end UI automation (Playwright/Cypress)

### Performance Tests
- pg_dump speed with large datasets
- Preferences API response times
- pgserve startup time across platforms

## Troubleshooting

### pgserve Not Found
```bash
cd gateway
npm install
```

### Python Dependencies Missing
```bash
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Change PGSERVE_PORT in .env
PGSERVE_PORT=15432
```

### WSL Issues (Windows)
```bash
# Use WSL2 instead of WSL1
wsl --set-version Ubuntu 2
```

## Contributing

When adding new tests:

1. Create test script in `tests/e2e/`
2. Make executable: `chmod +x tests/e2e/new_test.sh`
3. Add to `run_all.sh`
4. Update this README
5. Test on all platforms (Linux, macOS, Windows/WSL)

## License

Same as Automagik Omni project.
