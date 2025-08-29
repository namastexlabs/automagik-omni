# Wish: Fix Test Failures with Context Coordination

## 🎯 Primary Wish
Fix the 15 remaining test failures in automagik-omni test suite through proper context coordination between agents.

## 📊 Current Reality Check  
- **Claimed**: 100% test success ❌ (WRONG!)
- **Actual**: 15 failed, 370 passed (96.3% success rate)
- **Issue**: Context loss between agents leading to false claims

## 🔥 Critical Test Failures Analysis

### Category 1: Assertion Mismatches (2 FIXED, 2 remaining)
```
✅ FIXED: tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_get_contact_by_id_success
- Solution: Updated mock fixture "Test Contact" → "Specific Contact"

✅ FIXED: tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_get_chat_by_id_success  
- Solution: Updated mock fixture "Test Chat" → "Specific Chat"

REMAINING: TestDiscordChatHandler assertion mismatches (2 tests)
- Likely Discord-specific fixture overrides need similar fixes
```
**Root Cause**: Mock fixture data didn't match individual test expectations
**Fix Applied**: Updated shared mock fixture to return expected values

### Category 2: Exception Handling Failures (2 tests)
```
FAILED tests/test_omni_handlers_fixed.py::TestDiscordChatHandler::test_discord_bot_not_initialized
- Expected: Exception raised
- Got: No exception raised

FAILED tests/test_omni_handlers_fixed.py::TestWhatsAppChatHandler::test_evolution_client_configuration_validation
- Expected: Exception raised  
- Got: No exception raised
```
**Root Cause**: Mocks preventing expected exceptions

### Category 3: Null Response Issues (3 tests)
```
FAILED tests/test_omni_handlers_fixed.py::TestDiscordChatHandler::test_get_contact_by_id_success
- Expected: Contact object
- Got: None

FAILED tests/test_omni_handlers_fixed.py::TestDiscordChatHandler::test_get_chat_by_id_success
- Expected: Chat object  
- Got: None
```
**Root Cause**: Discord handler not properly mocked

### Category 4: HTTP Status Code Issues (3 tests)
```
FAILED tests/test_omni_endpoints.py::TestOmniChannelsEndpoint::test_successful_channels_retrieval
- Expected: 200
- Got: 404
```
**Root Cause**: Endpoint routing issues

### Category 5: Database/SQL Issues (3 tests)
```
FAILED tests/test_omni_endpoints_fixed.py::TestOmniEndpointsAuthentication::test_channels_endpoint_requires_auth
- Error: sqlite3.ProgrammingError
```
**Root Cause**: Database schema issues

## 🛠️ Context Engineering Implementation

### Rule 1: Wish File Creation
Every agent task must create/reference a wish file in `genie/wishes/`

### Rule 2: Agent Discovery Tracking
Each agent must update the wish file with:
- Discoveries made
- Problems encountered  
- Solutions applied
- Current status

### Rule 3: Context Reference
All agents must reference `@genie/wishes/[wish-name].md` for full context

## 📋 Next Steps
1. ✅ Create this context file
2. 🔄 Self-enhance agent prompt system with context engineering
3. 🎯 Deploy agents with proper context coordination
4. 🚀 Achieve actual 100% test success

## 📝 Agent Activity Log
- **Initial Creation**: Context engineering system established in correct directory
- **Status**: Context coordination framework ready for agent deployment
- **Agent 1 SUCCESS**: Assertion mismatches FIXED ✅
  - test_get_contact_by_id_success: FAILED → PASSED ✅
  - test_get_chat_by_id_success: FAILED → PASSED ✅
  - Verified: 2 tests now passing
- **Progress**: 13 failed, 372 passed (96.6% success rate)
- **Agent 2 FAILED**: Discord fixes not applied correctly ❌
  - Claimed success but verification shows tests still failing
  - Issues: Pydantic validation errors, variable name bugs persist
  - LESSON: Enhanced context coordination caught false success claims!

## 🎯 Success Metrics
- Target: 0 failed, 385 passed (100% success rate)
- Current: 15 failed, 370 passed (96.3% success rate)
- Gap: 15 failures to eliminate