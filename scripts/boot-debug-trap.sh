#!/bin/bash
# Boot Debug Trap - Captures PM2 startup sequence after reboot
# Run: This script is triggered by systemd or cron @reboot

LOG_DIR="/home/produser/logs/boot-debug"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/boot-$TIMESTAMP.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S.%3N')] $1" >> "$LOG_FILE"
}

log "=== BOOT DEBUG TRAP STARTED ==="
log "Hostname: $(hostname)"
log "Uptime: $(uptime)"

# Check port 5432 status every second for 60 seconds
log "=== MONITORING PORT 5432 ==="
for i in {1..60}; do
    PORT_STATUS=$(ss -tlnp 2>/dev/null | grep ":5432 " || echo "NOT_LISTENING")
    PM2_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    out=[]
    for p in d:
        out.append(f\"{p['name']}:{p['pm2_env']['status']}(restarts:{p['pm2_env'].get('restart_time',0)})\")
    print(' | '.join(out))
except:
    print('pm2-not-ready')
" 2>/dev/null || echo "pm2-error")

    log "[$i/60] Port5432: $PORT_STATUS | PM2: $PM2_STATUS"

    # Check if Evolution is trying to connect while PGlite is not ready
    if echo "$PM2_STATUS" | grep -q "Omni-Evolution:online" && echo "$PORT_STATUS" | grep -q "NOT_LISTENING"; then
        log "!!! RACE CONDITION DETECTED: Evolution online but port 5432 not listening !!!"
    fi

    sleep 1
done

log "=== PM2 FINAL STATE ==="
pm2 list >> "$LOG_FILE" 2>&1

log "=== RECENT PGLITE LOGS ==="
tail -50 /home/produser/.pm2-logs/pglite/router-out.log >> "$LOG_FILE" 2>&1
tail -20 /home/produser/.pm2-logs/pglite/router-error.log >> "$LOG_FILE" 2>&1

log "=== RECENT EVOLUTION LOGS ==="
tail -50 /home/produser/.pm2-logs/omni/evolution-out.log >> "$LOG_FILE" 2>&1
tail -20 /home/produser/.pm2-logs/omni/evolution-error.log >> "$LOG_FILE" 2>&1

log "=== BOOT DEBUG TRAP FINISHED ==="

echo "Debug log saved to: $LOG_FILE"
