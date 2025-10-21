# Quick Start: Execute UI Implementation

**Status:** Plan ready, awaiting approval
**Full Plan:** See `UI_IMPLEMENTATION_PLAN.md`

---

## 🚀 Quick Execution Commands

### Option 1: Launch All Sub-Agents in Parallel Groups

```bash
# From project root
# This will execute the orchestrated sub-agent plan

# Group 1: Schema & API Fixes (parallel)
@automagik-omni-schema-specialist --task "Fix Zod schemas per Phase 1.1" &
@automagik-omni-api-specialist --task "Fix API client per Phase 1.2 & 1.3" &
wait

# Group 2: Contacts & Chats (parallel)
@automagik-omni-contacts-specialist --task "Fix contacts page per Phase 2.1" &
@automagik-omni-chats-specialist --task "Fix chats page per Phase 2.2" &
wait

# Group 3: Messages (sequential)
@automagik-omni-messages-specialist --task "Fix messages per Phase 3.1 & 3.2"

# Group 4: Traces & Analytics (parallel)
@automagik-omni-traces-specialist --task "Implement traces per Phase 4.1" &
@automagik-omni-analytics-specialist --task "Implement analytics per Phase 4.2" &
wait

# Group 5: Instance Management (sequential)
@automagik-omni-instances-specialist --task "Complete instance management per Phase 5.1 & 5.2"
```

### Option 2: Manual Phase-by-Phase Execution

**Phase 1 (CRITICAL - Do First):**
```bash
# Fix Zod schemas
Task: Fix ui/lib/conveyor/schemas/omni-schema.ts
- Remove z.lazy() from ContactsResponseSchema and ChatsResponseSchema
- Replace with z.array(ContactSchema) and z.array(ChatSchema)
- Update InstanceSchema field names to match backend

# Fix API endpoints
Task: Fix ui/lib/main/omni-api-client.ts and ui/lib/conveyor/handlers/omni-handler.ts
- Change /api/v1/omni/{instance}/send-text → /api/v1/instance/{instance}/send-text
- Change /api/v1/omni/{instance}/contacts → /api/v1/instances/{instance}/contacts
- Change /api/v1/omni/{instance}/chats → /api/v1/instances/{instance}/chats

# Test
cd ui && pnpm run dev
# Check console - should see NO Zod errors
```

**Phase 2:**
```bash
# Fix contacts and chats pages
Task: Update ui/app/pages/Contacts.tsx and ui/app/pages/Chats.tsx
- Fix type imports
- Correct field access (channel_data.phone_number)
- Fix CSV export

# Test
# Navigate to Contacts → should load without errors
# Navigate to Chats → should load without errors
```

**Phase 3:**
```bash
# Fix message sending
Task: Update message components and handlers
- Fix endpoint paths
- Test with +555197285829

# Test
# Send text message → should receive on WhatsApp
```

**Phase 4:**
```bash
# Implement traces and analytics
Task: Build traces page and analytics dashboard
- Implement filtering
- Build charts

# Test
# Navigate to Traces → should see data
```

**Phase 5:**
```bash
# Complete instance management
Task: Implement CRUD operations
- Create instance
- QR code flow
- Status management

# Test
# Create test instance → should work end-to-end
```

---

## 📝 Critical Files to Edit

### Phase 1 (Schema & API)
1. `ui/lib/conveyor/schemas/omni-schema.ts`
   - Lines 155-175: Fix ContactsResponseSchema and ChatsResponseSchema
   - Lines 7-78: Update InstanceSchema field names

2. `ui/lib/main/omni-api-client.ts`
   - Update all endpoint paths
   - Fix response type handling

3. `ui/lib/conveyor/handlers/omni-handler.ts`
   - Fix IPC handler endpoint paths

### Phase 2 (Contacts & Chats)
4. `ui/app/pages/Contacts.tsx`
   - Line 7: Fix type import
   - Line 98: Fix phone_number access

5. `ui/app/pages/Chats.tsx`
   - Fix type import
   - Ensure field names match schema

### Phase 3 (Messages)
6. `ui/app/components/messages/TextMessageForm.tsx`
7. `ui/app/components/messages/MediaMessageForm.tsx`
8. `ui/app/components/messages/AudioMessageForm.tsx`

### Phase 4 (Traces)
9. `ui/app/pages/Traces.tsx`
10. `ui/app/components/traces/TracesTable.tsx`
11. `ui/app/components/traces/AnalyticsCards.tsx`

### Phase 5 (Instances)
12. `ui/app/components/instances/CreateInstanceDialog.tsx`
13. `ui/app/components/instances/QRCodeDialog.tsx`
14. `ui/app/components/instances/InstanceTable.tsx`

---

## 🧪 Quick Test Commands

```bash
# API endpoint tests (use these to verify fixes)

# Test instances
curl -H "x-api-key: namastex888" http://localhost:8882/api/v1/instances | jq '.[0] | {name, channel_type, evolution_status}'

# Test contacts
curl -H "x-api-key: namastex888" "http://localhost:8882/api/v1/instances/testonho/contacts?page=1&page_size=5" | jq '{total_count, contacts: .contacts | length}'

# Test chats
curl -H "x-api-key: namastex888" "http://localhost:8882/api/v1/instances/testonho/chats?page=1&page_size=5" | jq '{total_count, chats: .chats | length}'

# Test send text message
curl -X POST -H "x-api-key: namastex888" -H "Content-Type: application/json" \
  http://localhost:8882/api/v1/instance/testonho/send-text \
  -d '{"phone": "555197285829", "message": "Test from UI"}'

# Test traces
curl -H "x-api-key: namastex888" "http://localhost:8882/api/v1/traces?instance_name=testonho&limit=5" | jq '{total_count, traces: .data | length}'

# Test analytics
curl -H "x-api-key: namastex888" "http://localhost:8882/api/v1/traces/analytics/summary?instance_name=testonho" | jq '.'
```

---

## ✅ Validation Checklist

After each phase, verify:

**Phase 1:**
- [ ] UI starts without Zod errors
- [ ] Console shows no schema validation errors
- [ ] All API calls use correct endpoints

**Phase 2:**
- [ ] Contacts page loads
- [ ] Contact search works
- [ ] CSV export works
- [ ] Chats page loads
- [ ] Chat filtering works

**Phase 3:**
- [ ] Text message sends successfully
- [ ] Message received on +555197285829
- [ ] Media/audio messages work

**Phase 4:**
- [ ] Traces page loads with data
- [ ] Filters work
- [ ] Analytics dashboard populates
- [ ] Charts render

**Phase 5:**
- [ ] Can create instance
- [ ] QR code displays
- [ ] Can connect/disconnect instance
- [ ] Can delete instance

---

## 🎯 Success = All Green

When all checklist items pass:
1. Send notification to +555197285829
2. Commit changes with proper co-author
3. Create summary document
4. Mark task complete

---

**Prepared by:** Automagik Genie 🧞
**Date:** 2025-10-21
**Ready to execute:** ✅
