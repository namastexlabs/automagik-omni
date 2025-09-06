# 🎯 Implement Access Control System

## 📋 Objective
Implement a new access control system with allow and deny lists using a dedicated `access_control` table. Integrate into existing service layer with API endpoints for management.

## 🔍 Current State (dev branch)

### Database Structure
- **Current**: No access control exists yet
- **Target**: Create new `access_control` table for all access control
- **Separate table approach**: Clean separation of concerns

### Message Flow (to be implemented)
All messages flow through MessageRouter which will:
1. Call `AccessControlService` before any processing
2. Check `check_access()` to verify if user is allowed
3. If blocked: Return `{"status": "blocked", "reason": reason}`
4. If allowed: Continue to agent service

## 🎨 Target Design

### Database Schema (New Table)
```sql
CREATE TABLE access_control (
  id INTEGER PRIMARY KEY,
  rule_type VARCHAR NOT NULL,  -- 'allow' or 'deny'
  scope VARCHAR NOT NULL,  -- 'global' or 'instance'
  user_id VARCHAR,  -- For global rules (references users.id)
  instance_name VARCHAR,  -- For instance-specific rules
  identifier VARCHAR,  -- Channel-specific ID (phone/discord username)
  label VARCHAR,  -- Optional description
  created_at DATETIME,
  UNIQUE(rule_type, user_id),  -- Prevent duplicate global rules
  UNIQUE(rule_type, instance_name, identifier)  -- Prevent duplicate instance rules
);
```

### Access Control Logic
```
1. Default: Allow all (if no rules exist)
2. Check deny list first (highest priority):
   - If user/identifier in deny list → Block
3. Check allow list:
   - If allow list is empty → Allow (no whitelist active)
   - If allow list has entries → Implicit deny all others
     - User/identifier must be in allow list → Allow
     - Otherwise → Block
```

**Behavior Summary**:
- Empty allow + Empty deny = Allow all
- Has deny entries only = Block specific ones, allow rest
- Has allow entries = Block all except those in allow list
- Has both = Check deny first, then allow list logic

## 🔧 Implementation Steps

### 1. Database Changes
- [ ] Create model in `/src/db/models.py`:
  ```python
  class AccessControl(Base):
      __tablename__ = "access_control"
      
      id = Column(Integer, primary_key=True)
      rule_type = Column(String, nullable=False)  # 'allow' or 'deny'
      scope = Column(String, nullable=False)  # 'global' or 'instance'
      user_id = Column(String, nullable=True)  # For global rules
      instance_name = Column(String, nullable=True)  # For instance-specific rules
      identifier = Column(String, nullable=True)  # Channel-specific ID
      label = Column(String, nullable=True)  # Optional description
      created_at = Column(DateTime, default=datetime_utcnow)
      
      __table_args__ = (
          UniqueConstraint('rule_type', 'user_id', name='uq_global_rule'),
          UniqueConstraint('rule_type', 'instance_name', 'identifier', name='uq_instance_rule'),
      )
  ```
- [ ] Create migration: `create_access_control_table.py`
  - Use Alembic to generate migration from model
  - No changes to instance_configs table

### 2. Service Layer
- [ ] Create `/src/services/access_control_service.py`
- [ ] Implement `AccessControlService` class with:
  ```python
  def check_access(self, user_id, instance_name, identifier) -> tuple[bool, str]:
      """Check if user has access based on access control rules"""
      # 1. Check deny list first (highest priority)
      if self._is_in_deny_list(user_id, instance_name, identifier):
          return False, "User denied"
      
      # 2. Check if any allow rules exist
      has_allow_rules = self._has_allow_rules(instance_name)
      
      # 3. If no allow rules, default allow
      if not has_allow_rules:
          return True, "No restrictions"
      
      # 4. Allow rules exist = implicit deny all others
      if self._is_in_allow_list(user_id, instance_name, identifier):
          return True, "User allowed"
      
      # 5. Not in allow list when allow rules exist
      return False, "Not in allow list"
  ```

### 3. MessageRouter Integration (Universal Access Control Point)
- [ ] Modify `/src/services/message_router.py`:
  - Import AccessControlService at the top
  - Add access control check at the START of `route_message()`:
  ```python
  def route_message(self, ...):
      """Route a message to the appropriate handler."""
      
      # FIRST: Check access control (before any processing)
      from src.services.access_control_service import AccessControlService
      from src.db.database import get_db
      
      with get_db() as db:
          access_service = AccessControlService(db)
          
          # Extract identifier based on session_origin
          identifier = None
          if session_origin == "whatsapp" and user and user.get("phone_number"):
              # Strip + and @s.whatsapp.net
              identifier = user["phone_number"].lstrip("+").split("@")[0]
          elif session_origin == "discord" and user and user.get("user_data", {}).get("name"):
              identifier = user["user_data"]["name"]  # Discord username
          
          # Check access
          allowed, reason = access_service.check_access(
              user_id=user_id,  # Global user ID if exists
              instance_name=agent_config.get("instance_config", {}).get("name") if agent_config else None,
              identifier=identifier
          )
          
          if not allowed:
              logger.info(f"🚫 ACCESS BLOCKED: {reason} - User: {user_id or identifier}")
              return {"status": "blocked", "reason": reason}
      
      # Continue with normal routing...
  ```

### 4. API Implementation (RESTful Design)

#### API Endpoints:

##### 1. **Add to allow/deny list**
```
POST /api/v1/access-control/{list_type}
```
- Path param: `list_type` = "allow" or "deny"
- Request body:
  ```json
  {
    // Option 1: Global user rule
    "user_id": "uuid-123",
    
    // Option 2: Instance-specific rule for WhatsApp
    "instance_name": "my-whatsapp",
    "identifier": "5511999999999",  // WhatsApp: number without + or @s.whatsapp.net
    
    // Option 2b: Instance-specific rule for Discord
    "instance_name": "my-discord",
    "identifier": "namastex888",  // Discord username
    
    // Optional for both
    "label": "Reason for rule"
  }
  ```
- Response: 201 Created with rule details

##### 2. **Remove from allow/deny list**
```
DELETE /api/v1/access-control/{list_type}
```
- Path param: `list_type` = "allow" or "deny"
- Query params (one of these):
  - `user_id=uuid-123` - Remove global user rule
  - `instance_name=my-whatsapp&identifier=5511999999999` - Remove instance rule
- Response: 204 No Content

##### 3. **List access control rules**
```
GET /api/v1/access-control
```
- Query params (all optional):
  - `list_type=allow|deny|both` (default: both)
  - `scope=global|instance|both` (default: both)
  - `instance_name=my-whatsapp` - Filter by instance
  - `user_id=uuid-123` - Filter by user
- Response:
  ```json
  {
    "allow": [
      {"user_id": "user-123", "scope": "global", "label": "VIP"},
      {"instance_name": "my-whatsapp", "identifier": "5511999999999", "scope": "instance"}
    ],
    "deny": [
      {"user_id": "user-456", "scope": "global", "label": "Banned"},
      {"instance_name": "my-discord", "identifier": "namastex888", "scope": "instance"}
    ],
    "total": 4
  }
  ```

#### Implementation Files:
- [ ] Create `/src/api/routes/access_control.py`:
  - Implement POST endpoint for adding rules
  - Implement DELETE endpoint for removing rules
  - Implement GET endpoint for listing rules
  - Validate user_id exists in database
  - Validate instance_name exists
  - Handle idempotency (adding existing = 200 OK)
  
- [ ] Create `/src/api/schemas/access_control.py`:
  - Define AccessControlRule schema
  - Define request/response models
  
- [ ] Update `/src/api/app.py`:
  - Include access_control router
  - Mount at `/api/v1/access-control`


### 5. API Authentication Update (Automagik Pattern)
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

### 6. Endpoint Deduplication - Separate by Purpose

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

### 7. Remove ALL Deprecated Hive Fields (FULL CLEANUP)

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

### 8. Tests
- [ ] Create new tests for AccessControlService
- [ ] Test access control logic thoroughly

## ✅ Success Criteria
1. Access control integrated in MessageRouter (universal point for all channels)
2. Single migration file creating `access_control` table
3. Proper access control logic (default allow, deny first, implicit deny with allow list)
4. RESTful API for management
5. Clean implementation following existing patterns
6. All additional improvements implemented:
   - x-api-key authentication
   - Endpoint deduplication
   - Complete removal of hive_ fields

## 🚫 What NOT to Do
- Don't create middleware folder/files
- Don't maintain backward compatibility
- Don't modify instance_configs table
- Don't over-engineer the solution
- Don't implement in channel-specific handlers

## 📝 Key Insight
The MessageRouter is the universal entry point for ALL channels (WhatsApp, Discord, future integrations). By implementing access control there, we ensure consistent filtering regardless of how messages arrive (webhook, socket, API, etc.). This is much cleaner than implementing it in each channel handler.