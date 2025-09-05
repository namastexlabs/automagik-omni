# 🎯 Implement Firewall-Style Access Control (NEW FEATURE)

## 📋 Objective
Implement a NEW firewall-style access control system with both allow and deny lists directly in the instance_configs table. **NO MIDDLEWARE FOLDER** - integrate access control into existing service layer. **NO BACKWARD COMPATIBILITY NEEDED** - fresh implementation. **NO API ENDPOINTS** for managing access control - CLI only.

## 🔍 Current State (dev branch)

### Database Structure
- **Current**: No access control exists yet
- **Target**: Add allow_list and deny_list JSON columns to instance_configs table
- **No separate tables**: Everything integrated into instance_configs

### Webhook Behavior (to be implemented)
The webhook API should:
1. Call `AccessControlService` directly from service layer
2. Check `check_access()` to verify if user is allowed
3. If blocked: Return `{"status": "blocked", "reason": reason}`
4. If allowed: Continue to agent service

## 🎨 Target Design

### Database Schema Changes
```python
# In instance_configs table, add:
allow_list = Column(JSON, nullable=True, default=list)  # List of allowed users
deny_list = Column(JSON, nullable=True, default=list)   # List of denied users
# Remove: allowlist_enabled (logic determined by list contents)
# Remove: entire allowed_users table
```

### Firewall Rule Logic (Network Firewall Style)
```
1. If both lists empty/null → ALLOW ALL (*)
2. Check deny_list first (higher priority)
   - If user in deny_list → BLOCK
3. Check allow_list:
   - If allow_list empty → ALLOW (no restrictions)
   - If allow_list has entries → user must be in list to ALLOW
4. Default → BLOCK (if allow_list exists but user not in it)
```

### JSON Structure for Lists
```json
{
  "allow_list": [
    {"channel": "whatsapp", "user_id": "+1234567890"},
    {"channel": "discord", "user_id": "123456789"}
  ],
  "deny_list": [
    {"channel": "whatsapp", "user_id": "+0987654321"}
  ]
}
```

## 🔧 Implementation Steps

### 1. Database Changes
- [ ] Create NEW migration: `add_access_control_lists.py`
  - Add `allow_list` JSON column to instance_configs
  - Add `deny_list` JSON column to instance_configs

### 2. Model Updates
- [ ] Update `InstanceConfig` model in `/src/db/models.py`:
  - Add `allow_list: List[dict] = Field(default_factory=list)`
  - Add `deny_list: List[dict] = Field(default_factory=list)`

### 3. Service Layer (THE SIMPLE SOLUTION)
- [ ] Create `/src/services/access_control_service.py`
- [ ] Implement `AccessControlService` class with:
  ```python
  def check_access(self, instance_config, channel_type, user_id) -> tuple[bool, str]:
      """Check if user has access based on firewall rules"""
      # 1. Check deny list first
      if self._is_in_deny_list(instance_config, channel_type, user_id):
          return False, "User is denied"
      
      # 2. If allow_list is empty, allow all
      if not instance_config.allow_list:
          return True, "No restrictions"
      
      # 3. Check allow list
      if self._is_in_allow_list(instance_config, channel_type, user_id):
          return True, "User is allowed"
      
      # 4. Default deny when allow_list exists
      return False, "User not in allow list"
  ```
- [ ] Add CLI management methods (no API endpoints):
  - `add_to_allow_list()`
  - `add_to_deny_list()`
  - `remove_from_allow_list()`
  - `remove_from_deny_list()`
  - `list_access_rules()`
  - `clear_lists()`

### 4. Webhook Integration (app.py)
- [ ] Add import: `from src.services.access_control_service import AccessControlService`
- [ ] Replace middleware code with direct service call:
  ```python
  # Check access control before processing
  access_service = AccessControlService(db)
  user_id = access_service.extract_user_id(instance_config.channel_type, data)
  should_process, reason = access_service.check_access(
      instance_config, instance_config.channel_type, user_id
  )
  
  if not should_process:
      logger.info(f"🚫 MESSAGE BLOCKED: {reason}")
      return {"status": "blocked", "reason": reason}
  ```

### 5. CLI Implementation
- [ ] Create `/src/cli/access_control_cli.py`
- [ ] Update commands to `access` namespace:
  - `automagik-omni access allow add <instance> <user_id>`
  - `automagik-omni access allow remove <instance> <user_id>`
  - `automagik-omni access deny add <instance> <user_id>`
  - `automagik-omni access deny remove <instance> <user_id>`
  - `automagik-omni access list <instance>`
  - `automagik-omni access clear <instance> [--allow|--deny|--all]`
- [ ] Update `/src/cli/main_cli.py` imports and registration

### 7. API Authentication Update (Automagik Pattern)
- [ ] Change from `Authorization: Bearer <token>` to `x-api-key` header
- [ ] Update `/src/api/deps.py`:
  ```python
  # Remove HTTPBearer imports and usage
  from fastapi import Header
  
  def verify_api_key(x_api_key: str = Header(..., alias="x-api-key")):
      """Verify API key from x-api-key header."""
      if not config.api.api_key:
          logger.info("No API key configured, allowing access")
          return "development"
      
      if x_api_key != config.api.api_key:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid API key"
          )
      return x_api_key
  ```
- [ ] Update OpenAPI schema in `/src/api/app.py`:
  ```python
  # Change security scheme from HTTPBearer to APIKeyHeader
  if "components" not in openapi_schema:
      openapi_schema["components"] = {}
  if "securitySchemes" not in openapi_schema["components"]:
      openapi_schema["components"]["securitySchemes"] = {}
  
  openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
      "type": "apiKey",
      "in": "header",
      "name": "x-api-key",
      "description": "API key for authentication (e.g., 'namastex888')"
  }
  
  # Add global security requirement
  openapi_schema["security"] = [{"ApiKeyAuth": []}]
  ```
- [ ] Update all route files to use new auth (already using verify_api_key dependency)
- [ ] Update curl examples in documentation to use `-H "x-api-key: <key>"`
- [ ] Ensure consistency with other Automagik services (using lowercase `x-api-key`)

### 8. Endpoint Deduplication - Option 2: Separate by Purpose

**Purpose Analysis:**
- **Instances Router**: CRUD operations, instance management, direct Evolution API interaction
- **Omni Router**: Channel abstraction layer, unified interface across different platforms

#### Changes Required:

1. **Fix omni_router mounting** in `/src/api/app.py`:
   ```python
   # Change from:
   app.include_router(omni_router, prefix="/api/v1", tags=["instances"])
   # To:
   app.include_router(omni_router, prefix="/api/v1/omni", tags=["omni"])
   ```
   This moves all omni endpoints from `/api/v1/instances/*` to `/api/v1/omni/*`

2. **Remove omni_router internal prefix** in `/src/api/routes/omni.py`:
   ```python
   # Change from:
   router = APIRouter(prefix="/instances", tags=["omni-instances"])
   # To:
   router = APIRouter(tags=["omni"])
   ```

3. **Remove duplicate endpoints**:
   - DELETE `/src/api/routes/whatsapp.py` entirely (unused router with duplicates)
   - Remove QR endpoint from omni_router if it exists
   - Remove status endpoint from omni_router if it exists

4. **Final endpoint structure** will be:
   ```
   /api/v1/instances/
     GET    /                     # List all instances (CRUD)
     POST   /                     # Create instance
     GET    /{name}               # Get instance details
     PUT    /{name}               # Update instance
     DELETE /{name}               # Delete instance
     GET    /{name}/qr            # Get QR code
     GET    /{name}/status        # Get connection status
     POST   /{name}/connect       # Connect instance
     POST   /{name}/disconnect    # Disconnect instance
     
   /api/v1/omni/
     GET    /                     # List all channels (abstracted view)
     GET    /{name}/contacts      # Get contacts (unified format)
     GET    /{name}/contacts/{id} # Get specific contact
     GET    /{name}/chats         # Get chats (unified format)
     GET    /{name}/chats/{id}    # Get specific chat
   ```

5. **Update OpenAPI tags** for clarity:
   - instances endpoints: tag as "Instance Management"
   - omni endpoints: tag as "Omni Channel Abstraction"

### 9. Remove ALL Deprecated Hive Fields (FULL CLEANUP)

**Decision: COMPLETE REMOVAL - NO BACKWARD COMPATIBILITY**

#### Files to Clean:
1. **Database Model** `/src/db/models.py`:
   - [ ] Remove all hive_ field definitions (lines 65-71)
   - [ ] Remove `has_hive_config()` method (lines 145-156)
   - [ ] Remove `get_hive_config()` method (lines 158-171)

2. **Message Router** `/src/services/message_router.py`:
   - [ ] Remove hive_ field checks (lines 379-394, 454-464)
   - [ ] Remove all legacy fallback code
   - [ ] Use ONLY unified agent fields

3. **Hive Client** `/src/services/automagik_hive_client.py`:
   - [ ] Remove hive_ field fallbacks (lines 70-86)
   - [ ] Use ONLY agent_ fields directly

4. **Migration**:
   - [ ] Create migration to DROP all hive_ columns from instance_configs:
     ```sql
     ALTER TABLE instance_configs 
     DROP COLUMN hive_enabled,
     DROP COLUMN hive_api_url,
     DROP COLUMN hive_api_key,
     DROP COLUMN hive_agent_id,
     DROP COLUMN hive_team_id,
     DROP COLUMN hive_timeout,
     DROP COLUMN hive_stream_mode;
     ```

5. **Other Files to Check/Clean**:
   - [ ] `/src/utils/automagik_hive_validation.py` - Remove if it validates hive_ fields
   - [ ] `/src/api/schemas/automagik_hive.py` - Remove hive_ field schemas

#### Result:
- Clean codebase with ONLY unified agent fields
- No legacy code paths
- No backward compatibility burden
- Simpler, more maintainable code

### 10. Tests
- [ ] Create new tests for AccessControlService
- [ ] Test firewall logic thoroughly

## ✅ Success Criteria
1. Access control integrated as service layer (no middleware)
2. Single migration file adding allow_list and deny_list
3. Firewall-style logic (deny checked first, then allow)
4. CLI-only management (no API endpoints)
5. Clean implementation following existing patterns
6. All additional improvements implemented:
   - x-api-key authentication
   - Endpoint deduplication (Option 2)
   - Complete removal of hive_ fields

## 🚫 What NOT to Do
- Don't create middleware folder/files
- Don't add API endpoints for access control
- Don't maintain backward compatibility
- Don't create separate tables
- Don't over-engineer the solution

## 📝 Key Insight
The simplest solution is to treat this as a service concern, not middleware. The `AccessControlService` will be called directly from the webhook handler, maintaining the existing architectural pattern where services handle business logic.