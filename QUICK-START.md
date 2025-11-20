# Quick Start - Production Omni

## 🚀 Start Everything

```bash
cd ~/prod/automagik-omni

# Start Evolution API
pm2 start ecosystem.config.js --only evolution-api

# Start Omni API
pm2 start ecosystem.config.js --only automagik-omni

# Check status
pm2 status
```

---

## 📍 Important Paths

```bash
# Main config
~/prod/automagik-omni/.env

# Evolution API config
~/prod/automagik-omni/resources/evolution-api/.env

# PGLite database
/home/namastex/data/evolution-pglite/

# Omni SQLite database
/home/namastex/data/automagik-omni.db
```

---

## 🔍 Check Services

```bash
# Omni API
curl http://localhost:8882/health

# Evolution API
curl http://localhost:18082

# PM2 status
pm2 status

# PM2 logs
pm2 logs
pm2 logs evolution-api
pm2 logs automagik-omni
```

---

## 🛠️ Common Commands

```bash
# Restart services
pm2 restart all
pm2 restart evolution-api
pm2 restart automagik-omni

# Stop services
pm2 stop all

# View database (GUI)
cd ~/prod/automagik-omni/resources/evolution-api
npm run db:pglite:studio
# Opens at: http://localhost:5555

# Backup database
cp -r /home/namastex/data/evolution-pglite \
      ~/backups/evolution-pglite-$(date +%Y%m%d)
```

---

## 🔧 Troubleshooting

```bash
# Check if ports are in use
lsof -i :8882   # Omni
lsof -i :18082  # Evolution

# View logs
pm2 logs --lines 100

# Restart with logs
pm2 restart evolution-api --watch
```

---

## 📖 Full Documentation

- **Setup Guide:** `PRODUCTION-PGLITE-SETUP.md`
- **PGLite Docs:** `resources/evolution-api/PGLITE.md`
- **PGLite Quick Start:** `resources/evolution-api/PGLITE-QUICKSTART.md`

---

## ⚡ Emergency Reset

```bash
# Stop everything
pm2 stop all

# Clear database (WARNING: destroys data!)
rm -rf /home/namastex/data/evolution-pglite

# Recreate & migrate
mkdir -p /home/namastex/data/evolution-pglite
cd ~/prod/automagik-omni/resources/evolution-api
npm run db:pglite:deploy

# Restart
pm2 restart all
```
