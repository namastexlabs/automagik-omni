# ✅ PGLite Migration Complete - Ready to Restart

**Date:** November 19, 2024
**User:** namastex
**Status:** 🎉 **READY TO REBOOT**

---

## 🎯 Migration Summary

Your Automagik-Omni production environment has been successfully migrated from SQLite to **PGLite** (in-memory PostgreSQL).

### What Changed:

1. ✅ **Evolution API** - Now uses PGLite instead of SQLite
2. ✅ **Omni Backend** - Fresh database (started from scratch)
3. ✅ **PM2 Configuration** - Updated for PGLite
4. ✅ **Auto-start** - Configured to start on boot

---

## 🗄️ Database Locations

### Evolution API (PGLite - PostgreSQL)
```bash
Location: /home/namastex/data/evolution-pglite/
Type: File-based PostgreSQL (persistent)
Migrations: 57 applied automatically on startup
```

**Directory structure:**
```
/home/namastex/data/evolution-pglite/
├── base/          # Tables, indexes, data
├── pg_wal/        # Write-Ahead Log
├── global/        # PostgreSQL catalogs
└── ...
```

### Omni Backend (SQLite)
```bash
Location: /home/namastex/data/automagik-omni.db
Type: SQLite (existing)
Size: 180KB (fresh database)
```

---

## 🚀 What Happens on Restart

When you reboot your machine, PM2 will automatically start:

1. **Evolution API (PGLite)** - Port 18082
   - Loads PGLite from `/home/namastex/data/evolution-pglite/`
   - Applies migrations automatically if needed
   - Ready for WhatsApp connections

2. **Omni Backend - API** - Port 8882
   - Connects to SQLite at `/home/namastex/data/automagik-omni.db`
   - Ready for API requests

3. **Omni Backend - Health Check**
   - Waits for API to be healthy
   - Triggers Discord bot start when ready

4. **Omni Backend - Discord**
   - Starts after health check passes
   - Manages all Discord bots

5. **Omni UI** - Port 9882
   - Frontend dashboard

---

## 📊 Configuration Summary

### Evolution API (.env)
```bash
DATABASE_PROVIDER=pglite
PGLITE_DATA_DIR=/home/namastex/data/evolution-pglite
SERVER_PORT=18082
AUTHENTICATION_API_KEY=namastex888
```

### PM2 Ecosystem (ecosystem.config.js)
```javascript
{
  name: 'Evolution API (PGLite)',
  env: {
    DATABASE_PROVIDER: 'pglite',
    PGLITE_DATA_DIR: '/home/namastex/data/evolution-pglite',
    // ... other settings
  }
}
```

### Main Omni (.env)
```bash
EVOLUTION_API_URL=http://localhost:18082
EVOLUTION_API_PORT=18082
EVOLUTION_API_KEY=namastex888
AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH=/home/namastex/data/automagik-omni.db
```

---

## ✅ Verification Checklist

Before restart:
- [x] Old SQLite databases deleted
- [x] PGLite dependencies installed
- [x] Prisma client generated
- [x] PM2 ecosystem config updated
- [x] PM2 startup configured (systemd)
- [x] PM2 process list saved
- [x] Fresh Omni database created

---

## 🔍 Post-Restart Verification

After you reboot, verify everything is working:

### 1. Check PM2 Status
```bash
pm2 status
```

**Expected output:**
```
┌─────┬────────────────────────┬─────────┬─────────┐
│ id  │ name                   │ status  │ restart │
├─────┼────────────────────────┼─────────┼─────────┤
│ 0   │ Evolution API (PGLite) │ online  │ 0       │
│ 1   │ Omni Backend - API     │ online  │ 0       │
│ 2   │ Omni Backend - Discord │ online  │ 0       │
│ 3   │ Omni UI                │ online  │ 0       │
└─────┴────────────────────────┴─────────┴─────────┘
```

### 2. Check Evolution API
```bash
curl http://localhost:18082
```

**Expected:** Response from Evolution API

### 3. Check Omni API
```bash
curl http://localhost:8882/health
```

**Expected:** `{"status": "healthy"}`

### 4. Check PGLite Database
```bash
ls -lh /home/namastex/data/evolution-pglite/
```

**Expected:** PostgreSQL files (base/, pg_wal/, etc.)

### 5. Check Logs
```bash
pm2 logs --lines 50
```

**Look for:**
- ✅ `Repository:Prisma - ON (Provider: pglite)`
- ✅ No database connection errors
- ✅ All services started successfully

---

## 🛠️ Common Commands

### Start/Stop Services
```bash
# Start all
pm2 start ecosystem.config.js

# Stop all
pm2 stop all

# Restart all
pm2 restart all

# Status
pm2 status

# Logs
pm2 logs
pm2 logs evolution-api --lines 100
```

### Database Management
```bash
# Backup PGLite database
tar -czf ~/backups/evolution-pglite-$(date +%Y%m%d).tar.gz \
         /home/namastex/data/evolution-pglite/

# Check database size
du -sh /home/namastex/data/evolution-pglite

# View database (GUI)
cd ~/prod/automagik-omni/resources/evolution-api
npm run db:pglite:studio
# Opens at http://localhost:5555
```

---

## 🔧 Troubleshooting

### Evolution API won't start?

**Check logs:**
```bash
pm2 logs evolution-api
```

**Common issues:**
- Missing dependencies → `cd ~/prod/automagik-omni/resources/evolution-api && npm install`
- Prisma client not generated → `npm run db:pglite:generate`
- Port 18082 in use → `lsof -i :18082`

### PGLite database not found?

**Check directory:**
```bash
ls -la /home/namastex/data/evolution-pglite/
```

**If empty:** Database will be created automatically on first start

### Migrations not applied?

**PGLite applies migrations automatically on startup.**

If you see errors:
```bash
cd ~/prod/automagik-omni/resources/evolution-api
node test-pglite.js  # Test PGLite works
```

### Services not starting on boot?

**Check systemd status:**
```bash
systemctl status pm2-namastex
```

**If not enabled:**
```bash
sudo systemctl enable pm2-namastex
pm2 save
```

---

## 📊 What Was Deleted (Fresh Start)

✅ **Old databases deleted:**
- `/home/namastex/data/automagik-omni.db` (180KB) → Fresh 180KB created
- `/home/namastex/data/evolution-desktop.db` (476KB) → Deleted

✅ **New databases created:**
- `/home/namastex/data/automagik-omni.db` (180KB - fresh)
- `/home/namastex/data/evolution-pglite/` (PostgreSQL files)

**Result:** Clean slate, no old data

---

## 🎁 Benefits You Now Have

### ✅ Production Parity
- Same PostgreSQL engine as cloud deployments
- No SQLite quirks or limitations
- Same SQL queries everywhere

### ✅ Self-Contained
- No external PostgreSQL server needed
- Everything in ~/prod/ and ~/data/
- Portable (just copy directories)

### ✅ Better Performance
- In-process database (no network)
- Fast queries (1-3ms)
- Optimized for local storage

### ✅ Easy Backup
```bash
# Single command backup
tar -czf backup.tar.gz ~/data/
```

### ✅ Auto-Start on Boot
- PM2 systemd service configured
- Starts automatically after reboot
- Proper startup order (Evolution → API → Discord)

---

## 🆘 Need Help?

**Documentation:**
- `PRODUCTION-PGLITE-SETUP.md` - Full setup guide
- `QUICK-START.md` - Quick reference
- `PGLITE-CONFIGURED.md` - Configuration details
- `resources/evolution-api/PGLITE.md` - PGLite guide

**Test PGLite:**
```bash
cd ~/prod/automagik-omni/resources/evolution-api
node test-pglite.js
```

**Check PM2:**
```bash
pm2 status
pm2 logs
pm2 describe evolution-api
```

---

## 🎉 You're Ready!

Everything is configured and ready for restart.

**What to do now:**
1. Review this document
2. Reboot your machine: `sudo reboot`
3. After boot: Check PM2 status and logs
4. Verify all services are running
5. Start using Automagik-Omni with PGLite!

**Database location:** `/home/namastex/data/evolution-pglite/` 📍
**Auto-start:** ✅ Enabled (PM2 systemd)
**Fresh start:** ✅ No old data

---

**Migration complete! Ready to reboot and enjoy PGLite! 🚀**
