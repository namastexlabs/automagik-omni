#!/bin/bash
# Test Boot Order - Simulates reboot by stopping and starting PM2
# This will confirm if the issue is startup order

echo "=== TEST BOOT ORDER ==="
echo "This simulates a reboot by stopping all PM2 services and restarting"
echo ""

# Stop all
echo "[1/4] Stopping all PM2 services..."
pm2 stop all
sleep 2

# Show current state
echo ""
echo "[2/4] Current PM2 dump order (this is the order they will start):"
pm2 jlist 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for i,p in enumerate(d):
    print(f'  {i}: {p[\"name\"]} (status: {p[\"pm2_env\"][\"status\"]})')
"

echo ""
echo "[3/4] Starting all services (watching port 5432)..."
echo ""

# Start all in background
pm2 start all &

# Monitor port 5432
for i in {1..30}; do
    PORT=$(ss -tlnp 2>/dev/null | grep ":5432 " | head -1)
    EVO_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for p in d:
    if 'Evolution' in p['name']:
        print(f\"{p['pm2_env']['status']} (restarts: {p['pm2_env'].get('restart_time',0)})\")
" 2>/dev/null || echo "unknown")

    PGLITE_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for p in d:
    if 'PGlite' in p['name']:
        print(f\"{p['pm2_env']['status']} (restarts: {p['pm2_env'].get('restart_time',0)})\")
" 2>/dev/null || echo "unknown")

    if [ -z "$PORT" ]; then
        PORT_MSG="NOT LISTENING"
    else
        PORT_MSG="LISTENING"
    fi

    echo "[$i/30] Port 5432: $PORT_MSG | Evolution: $EVO_STATUS | PGlite: $PGLITE_STATUS"

    # Detect race condition
    if [ "$PORT_MSG" = "NOT LISTENING" ] && [[ "$EVO_STATUS" == *"online"* ]]; then
        echo "  >>> RACE CONDITION: Evolution online before PGlite!"
    fi

    sleep 1
done

echo ""
echo "[4/4] Final state:"
pm2 list
