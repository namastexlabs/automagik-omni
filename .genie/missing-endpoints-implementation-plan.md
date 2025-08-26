# 🧞 Missing API Endpoints Implementation Plan

## 📋 **Current Status Analysis**

From the comprehensive test orchestration, we identified **24 failing tests** in `test_api_endpoints_e2e.py` due to missing endpoints. Here's the implementation plan based on user requirements:

## 🎯 **Implementation Priority**

### **✅ HIGH PRIORITY - Implement These**

#### **1. Instance Operations** 
```bash
POST /api/v1/instances/{instance_name}/restart     # Restart WhatsApp connection  
POST /api/v1/instances/{instance_name}/logout      # Logout from WhatsApp
POST /api/v1/instances/discover                    # Discover available instances
```

**Implementation Location**: `/src/api/routes/instances.py`
**Channel Handler Support**: Already exists in WhatsApp channel handler
**Effort**: Medium (3-5 days)

#### **2. Trace Detail Endpoints**
```bash
GET /api/v1/traces/{trace_id}                      # Get specific trace by ID
GET /api/v1/traces/{trace_id}/payloads             # Get detailed payloads for trace
```

**Implementation Location**: `/src/api/routes/traces.py`
**Database Support**: Already exists in trace models
**Effort**: Low (1-2 days)

#### **3. ✅ Webhook Endpoints - ALREADY EXISTS!**
```bash
POST /webhook/evolution/{instance_name}            # ✅ Already implemented in app.py
```

**Status**: This endpoint already exists and is working!
**Location**: `/src/api/app.py` - `evolution_webhook_tenant()` function
**No Action Needed**: Remove from failing test expectations

#### **4. Authentication Hardening**
**Fix unprotected endpoints that should require auth:**
- Add proper `verify_api_key` dependency to all instance endpoints
- Ensure consistent 401/403 responses for unauthorized access

**Effort**: Low (1 day)

### **❌ REMOVE FROM TESTS - Don't Implement**

#### **Test/Debug Endpoints** (User Request: "should not exist")
```bash
POST /api/v1/test/capture/enable                   # ❌ Remove from tests
POST /api/v1/test/capture/disable                  # ❌ Remove from tests  
GET  /api/v1/test/capture/status                   # ❌ Remove from tests
```

**Action**: Update `test_api_endpoints_e2e.py` to remove these test cases
**Rationale**: Development/testing utilities don't belong in production API

#### **Set Default Endpoint** (User Request: "no set-default")
```bash
POST /api/v1/instances/{instance_name}/set-default # ❌ Don't implement
```

**Action**: Update tests to remove set-default expectations
**Rationale**: Default instance logic handled differently

## 🚀 **Detailed Implementation Plan**

### **Phase 1: Quick Wins (Week 1)**
1. **Remove Test/Debug Endpoints** from `test_api_endpoints_e2e.py`
2. **Authentication Hardening** - Add missing auth requirements
3. **Trace Detail Endpoints** - Complete existing trace API

### **Phase 2: Instance Operations (Week 2)**
1. **POST /instances/{name}/restart**
   - Call `channel_handler.restart_instance()`
   - Return connection status after restart
   - Handle restart failures gracefully

2. **POST /instances/{name}/logout**  
   - Call `channel_handler.logout_instance()`
   - Clear connection state
   - Return logout confirmation

3. **POST /instances/discover**
   - Scan for available Evolution instances
   - Return discovered instance list
   - Support filtering by status/type

### **Phase 3: Test Updates (Week 3)** 
1. **Fix Webhook Test Expectations**
   - Update test to use correct endpoint: `/webhook/evolution/{instance_name}` 
   - The endpoint exists but test might be calling wrong URL
   - Verify webhook functionality is working correctly

### **Phase 4: Test Cleanup (Week 4)**
1. **Update test_api_endpoints_e2e.py**
   - Remove test/debug endpoint tests (3 tests)
   - Remove set-default expectations (1 test)  
   - Update authentication expectations (11 tests)
   - Verify all endpoint implementations (9 tests)

## 📊 **Expected Outcome**

**Current**: 243 PASSED, 24 FAILED
**After Implementation**: ~265 PASSED, ~3 FAILED (edge cases)

**Improvement**: +22 more passing tests, bringing failure rate to ~1%

## 🛠️ **Technical Requirements**

### **Dependencies**
- Evolution API integration (already exists)
- Channel handler interface (already exists)  
- Database trace models (already exists)
- Multi-tenant architecture (already exists)

### **New Files Needed**
- `/src/api/routes/webhooks.py` - New webhook endpoints
- Test updates in `test_api_endpoints_e2e.py`

### **Modified Files**
- `/src/api/routes/instances.py` - Add restart/logout/discover
- `/src/api/routes/traces.py` - Add detail endpoints
- `/src/api/app.py` - Register webhook router

## 🧞 **Genie Recommendation**

This plan will complete the API surface area needed for production deployment while removing unnecessary test/debug endpoints. The implementation follows existing patterns and leverages already-built infrastructure.

**Estimated Total Effort**: 2-3 weeks
**Risk Level**: Low (building on existing foundation)
**Business Value**: High (complete API functionality)

Ready to implement when you give the command! ✨