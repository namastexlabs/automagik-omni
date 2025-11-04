# Testing Guide for Automagik Omni Desktop UI

## Quick Start

### 1. Start the Backend API

The UI requires the Automagik Omni FastAPI backend to be running.

```bash
# In the root directory (not ui/)
cd /home/cezar/automagik/automagik-omni

# Start backend with PM2
make start-local

# OR start manually (if PM2 not available)
make dev

# Verify backend is running
curl http://localhost:8882/health
# Should return: {"status":"healthy"}
```

### 2. Start the Electron UI

```bash
# In a separate terminal
cd /home/cezar/automagik/automagik-omni/ui

# RECOMMENDED (WSL): Use clean start script
./clean-start.sh

# OR: Start Electron in dev mode
pnpm run dev
```

The app will open automatically and connect to `http://localhost:8882`.

**⚠️ WSL Users:** If the window appears blank or doesn't show:
1. Use `./clean-start.sh` instead of `pnpm run dev`
2. Or restart WSL: `wsl --shutdown` (from PowerShell) then `wsl`
3. See `WSL_ELECTRON_FIX.md` for details

---

## Expected Behavior

### When Backend is Running ✅

- Dashboard shows API status: **Healthy**
- All pages load without errors
- Navigation works smoothly
- API calls succeed

### When Backend is NOT Running ❌

You'll see errors like:
```
IPC Error in omni:instances:list: Error: Not Found
```

This is **expected** - the UI gracefully handles backend unavailability by:
- Showing error messages in red banners
- Displaying "Failed to load" states
- Allowing retry via "Refresh" buttons

---

## Testing Each Page

### 1. Dashboard (Home)

**Route:** `/`

**What to test:**
- API status card shows "Healthy" (green)
- Discord bot status (if configured)
- Process manager shows running services
- Backend control buttons (Start/Stop/Restart)

**Expected when backend is down:**
- API status shows "Stopped" (red)
- Error banner at top
- Backend controls still work (can start backend)

---

### 2. Instances Page

**Route:** `/instances`

**What to test:**

1. **Create Instance:**
   - Click "Create Instance" button
   - Fill out form:
     - Name: `test-whatsapp`
     - Channel Type: WhatsApp
     - Evolution URL: `http://localhost:8080`
     - Evolution Key: `your-key`
     - Agent API URL: `http://localhost:8886`
   - Submit → Should create instance

2. **View QR Code (WhatsApp only):**
   - Click "QR Code" button on WhatsApp instance
   - QR code should display
   - Scan with WhatsApp mobile app

3. **Connection Management:**
   - Click "Connect" to establish connection
   - Click "Disconnect" to stop
   - Click "Restart" to reconnect

4. **Delete Instance:**
   - Click "Delete" button
   - Confirm deletion
   - Instance removed from table

**Expected without backend:**
- Error: "Failed to load instances"
- Red banner at top
- Table empty
- "Refresh" button available

---

### 3. Messages Page

**Route:** `/messages`

**What to test:**

1. **Select Instance:**
   - Dropdown shows all instances
   - Select one

2. **Send Text Message:**
   - Enter phone: `+5511999999999`
   - Type message: "Hello from Omni!"
   - Click "Send"
   - Check recent messages list

3. **Send Media:**
   - Switch to "Media" tab
   - Select type (Image/Video/Document)
   - Enter media URL
   - Add caption (optional)
   - Send

4. **Send Audio:**
   - Switch to "Audio" tab
   - Enter audio URL
   - Send

5. **Send Reaction:**
   - Switch to "Reaction" tab
   - Enter message ID
   - Enter emoji (👍)
   - Send

**Expected without backend:**
- Instances dropdown empty
- Error when trying to send
- Recent messages list empty

---

### 4. Contacts Page

**Route:** `/contacts`

**What to test:**

1. **Select Instance:**
   - Choose instance from dropdown

2. **Search:**
   - Type name in search bar
   - Results filter in real-time

3. **Pagination:**
   - Change page size (10/25/50/100)
   - Navigate pages (Previous/Next)
   - Check page counter updates

4. **View Details:**
   - Click on any contact row
   - Side panel opens
   - Shows contact info

5. **Export CSV:**
   - Click "Export CSV" button
   - File downloads with contacts data

**Expected without backend:**
- Error: "Failed to load contacts"
- Table empty
- Pagination disabled

---

### 5. Chats Page

**Route:** `/chats`

**What to test:**

1. **Select Instance:**
   - Choose instance

2. **Filter by Type:**
   - Click "All" (default)
   - Click "Direct" → Shows only DMs
   - Click "Group" → Shows only groups
   - Click "Channel" → Shows only channels

3. **Pagination:**
   - Same as Contacts page

4. **View Details:**
   - Click chat row
   - Panel shows chat info
   - Displays unread count

**Expected without backend:**
- Error: "Failed to load chats"
- Filters disabled
- Table empty

---

### 6. Traces Page

**Route:** `/traces`

**What to test:**

1. **Apply Filters:**
   - Select instance (optional)
   - Set date range (default: last 7 days)
   - Filter by status (All/Completed/Failed)
   - Filter by message type
   - Click "Refresh"

2. **View Analytics:**
   - 4 cards show metrics:
     - Total messages
     - Success rate (%)
     - Average response time
     - Failed count

3. **Explore Charts:**
   - **Line Chart:** Messages over time
   - **Pie Chart:** Success vs Failed
   - **Bar Chart:** Message types distribution
   - **List:** Top 10 contacts

4. **Browse Traces:**
   - Scroll through traces table
   - Navigate pages
   - Click "View Details" on any trace
   - Modal shows full trace info

5. **Export:**
   - Click "Export CSV"
   - Downloads traces data

**Expected without backend:**
- Error: "Failed to load analytics"
- Charts empty
- Table empty
- Cards show zeros

---

## Troubleshooting

### Issue: Blank/White Window (WSL Only)

**Symptom:** Electron starts in logs but window is blank or doesn't appear.

**Cause:** Zombie Electron processes holding WSLg display resources.

**Fix:**
```bash
# Option 1: Clean start (recommended)
cd ui
./clean-start.sh

# Option 2: Manual cleanup
pkill -9 -f "electron|vite"
sleep 1
pnpm run dev

# Option 3: Restart WSL (from PowerShell)
wsl --shutdown
wsl
```

**Prevention:** Always use Ctrl+C to stop Electron, not `pkill -9`.

See `WSL_ELECTRON_FIX.md` for detailed explanation.

---

### Issue: "Error: Not Found"

**Cause:** Backend API not running

**Fix:**
```bash
cd /home/cezar/automagik/automagik-omni
make start-local
```

---

### Issue: "Connection Refused"

**Cause:** Wrong API URL/port

**Fix:**
1. Check `.env` file in root directory
2. Verify `AUTOMAGIK_OMNI_API_PORT=8882`
3. Restart Electron app

---

### Issue: Schema Validation Errors

**Symptom:** Runtime errors about Zod validation failures.

**Cause:** Schema mismatch between UI and backend API.

**Fix:**
1. Check DevTools console for specific validation error
2. Verify backend is up-to-date (latest API changes)
3. Ensure UI schemas have `.passthrough()` for unknown fields
4. Check field names match OpenAPI spec exactly

**Recent fixes applied:**
- Instance schema: Added 23 missing fields
- Trace schema: `trace_id`, `sender_phone`, `received_at`
- Contact/Chat: Added `instance_name`, `channel_type`
- All schemas: Added `.passthrough()` for backend compatibility

---

### Issue: Dashboard shows API "Stopped"

**Cause:** Backend not running or crashed

**Fix:**
1. Check backend status: `make status`
2. View logs: `make logs`
3. Restart: `make restart`

---

### Issue: No instances in dropdown

**Cause:** No instances created yet

**Fix:**
1. Go to Instances page
2. Click "Create Instance"
3. Fill form and submit

---

### Issue: Charts not rendering

**Cause:** No trace data available

**Fix:**
1. Send some messages first (Messages page)
2. Wait a few seconds
3. Go to Traces page
4. Refresh

---

## Testing Checklist

Use this checklist to verify Phase 2 is working:

- [ ] Backend API started successfully
- [ ] Electron UI opens without errors
- [ ] Dashboard shows "Healthy" status
- [ ] Navigation sidebar works
- [ ] All 6 pages load correctly

**Instances Page:**
- [ ] Can create instance
- [ ] QR code displays (WhatsApp)
- [ ] Can delete instance
- [ ] Status badges show correct state

**Messages Page:**
- [ ] Instance selector populated
- [ ] Phone validation works
- [ ] Can send text message
- [ ] Recent messages update

**Contacts Page:**
- [ ] Contacts load in table
- [ ] Search filters results
- [ ] Pagination works
- [ ] Can export CSV

**Chats Page:**
- [ ] Chats load in table
- [ ] Type filters work
- [ ] Pagination works
- [ ] Details panel opens

**Traces Page:**
- [ ] Analytics cards show data
- [ ] Charts render correctly
- [ ] Filters update results
- [ ] Can view trace details
- [ ] Can export CSV

---

## Performance Notes

### Expected Load Times:
- Dashboard: < 100ms
- Instances: < 500ms (with 10 instances)
- Messages: < 200ms
- Contacts: < 1s (with pagination)
- Chats: < 1s (with pagination)
- Traces: < 2s (with charts + analytics)

### Resource Usage:
- Electron app: ~150-200 MB RAM
- Backend API: ~100-150 MB RAM
- Total: ~300 MB RAM

---

## Known Limitations

1. **File Upload:** Media/audio use URL input (no native file picker yet)
2. **Real-time Updates:** Uses polling (15s interval), not WebSocket
3. **Charts:** Require backend analytics API implementation
4. **QR Code:** Only for WhatsApp (Discord uses token auth)

---

## Next Steps After Testing

If all tests pass:
1. Create PR for Phase 2
2. Merge to main branch
3. Plan Phase 3 features
4. Deploy to production

If issues found:
1. Document the issue
2. Check logs (backend + Electron console)
3. File bug report with steps to reproduce
4. Fix and retest

---

## Support

For issues or questions:
- Check logs: `make logs` (backend) or Electron DevTools (UI)
- Review documentation: `ui/AUTOMAGIK_OMNI_README.md`
- See Phase 2 summary: `ui/PHASE_2_SUMMARY.md`
