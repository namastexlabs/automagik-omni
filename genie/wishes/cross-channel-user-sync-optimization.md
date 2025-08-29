# Cross-Channel User Sync & API Optimization

**Wish ID**: CCUS-001  
**Created**: 2025-08-26  
**Priority**: High  
**Status**: Planning Complete  
**Estimated Effort**: 4-6 weeks  

## 🎯 USER REQUEST SUMMARY

**What the user is asking for:**
> "We have a few issues now. We need to optimize the user handling first is by adding some endpoints for user manipulation. Second is that we need a way to map out users. Let's say I'm user X on whatsapp and user Y on discord. We need a way to know that is the "same" user so we can properly notify the user on each channel when possible."

**Key Constraint:**
> "We need to avoid over-engineering this whole verification flow. What we need at the moment is a way to sync the user somehow."

## 🎯 CORE REQUIREMENTS

### Primary Goals
1. **User Manipulation API**: Create RESTful endpoints for user management operations
2. **Simple User Sync**: Basic mechanism to link users across channels (WhatsApp ↔ Discord ↔ Slack)
3. **Cross-Channel Notifications**: Route messages to users across their linked channels

### Anti-Requirements (What NOT to Build)
- ❌ Complex identity verification workflows with SMS/email codes
- ❌ Heavy cryptographic systems for identity linking
- ❌ Enterprise-grade privacy compliance features (GDPR, etc.)
- ❌ Advanced ML-based identity matching
- ❌ Comprehensive audit systems

## 🚀 SUCCESS CRITERIA

### Functional Success Criteria
1. **API Endpoints Work**: Can CRUD users via REST API with proper authentication
2. **Manual User Linking**: Admin can manually link User X (WhatsApp) = User Y (Discord)
3. **Cross-Channel Routing**: Message sent to User X reaches them on all linked channels
4. **Data Integrity**: No duplicate notifications, proper error handling
5. **Backward Compatibility**: Existing system continues working unchanged
6. **Session Context Preservation**: Chat context (group vs DM) preserved across channels

### Non-Functional Success Criteria
1. **Performance**: User lookup operations <200ms
2. **Reliability**: 99.9% uptime for user sync operations
3. **Simplicity**: <5 new database tables, minimal code complexity
4. **Maintainability**: Clear code structure, easy to understand and extend

### Acceptance Criteria
- [ ] Admin can create, read, update, delete users via API
- [ ] Admin can manually link/unlink user accounts across channels
- [ ] System routes messages to all linked channels for a user
- [ ] No breaking changes to existing message flows
- [ ] Documentation covers all new API endpoints
- [ ] Unit tests for all new functionality (>85% coverage)
- [ ] Session context (group/DM) properly handled in cross-channel routing

## 🔍 CODE REVIEW FINDINGS

### Current User Registration Patterns

#### ✅ **WhatsApp User Registration** (Working Well)
**Location**: `src/channels/whatsapp/handlers.py:512-518`
- **Automatic Registration**: Users created when first message arrives
- **Unique Identifier**: `phone_number` + `whatsapp_jid`
- **Instance Isolation**: Users scoped by `instance_name`
- **Session Tracking**: `session_name` format: `{instance}_{phone}`

#### ✅ **Discord User Registration** (Working Well)  
**Location**: `src/channels/discord/channel_handler.py:122-134`
- **Automatic Registration**: Users created on @mention messages  
- **Unique Identifier**: `discord_user_id` + `username`
- **Instance Isolation**: Users scoped by `instance_name`
- **Session Tracking**: `session_name` format: `discord_{guild_id}_{user_id}` (groups) or `discord_dm_{user_id}` (DMs)

#### 🟡 **Current User Model** (Needs Extension)
**Location**: `src/db/models.py:177-224`
- **WhatsApp-Focused**: Only has `phone_number` and `whatsapp_jid` fields
- **Missing Discord Fields**: No Discord user ID storage
- **Single Channel Design**: Assumes one user = one channel identity

### Chat Session Handling & Context

#### ✅ **Discord Context Detection** (Excellent)
**Location**: `src/channels/discord/channel_handler.py:137`
```python
# Smart session naming with context
session_name = f"discord_{message.guild.id}_{message.author.id}" if message.guild else f"discord_dm_{message.author.id}"
```
- **Guild Messages**: `discord_{guild_id}_{user_id}` 
- **Direct Messages**: `discord_dm_{user_id}`
- **Context Preservation**: Guild ID preserves group context

#### ✅ **WhatsApp Context Detection** (Basic but Working)
**Location**: Session names differentiate by instance
- **Format**: `{instance_name}_{phone_number}`
- **Group Context**: Handled via WhatsApp's JID system
- **Instance Separation**: Multiple instances supported

#### 🔴 **Missing Cross-Channel Context Bridge**
- **Problem**: No way to map Discord guild conversations to WhatsApp group conversations
- **Gap**: User in Discord guild ≠ same user in WhatsApp group (even if linked)
- **Impact**: Context lost when routing messages across channels

## 🏗️ SIMPLIFIED TECHNICAL APPROACH

### Database Design (Minimal)
Based on code review findings, extend existing User model instead of complex linking tables:

```sql
-- Extend existing User model with multi-channel support
ALTER TABLE users ADD COLUMN discord_user_id VARCHAR(255);
ALTER TABLE users ADD COLUMN discord_username VARCHAR(255); 
ALTER TABLE users ADD COLUMN slack_user_id VARCHAR(255);
ALTER TABLE users ADD COLUMN channel_type VARCHAR(50) DEFAULT 'whatsapp';

-- Simple user linking table
CREATE TABLE user_channel_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_user_id UUID REFERENCES users(id),
    linked_user_id UUID REFERENCES users(id),  
    channel_type VARCHAR(50),
    linked_by_admin_id VARCHAR(255),
    linked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(primary_user_id, linked_user_id)
);

-- Session context mapping for cross-channel routing
CREATE TABLE session_context_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_session_name VARCHAR(255),
    linked_session_name VARCHAR(255),
    context_type VARCHAR(50), -- 'group', 'dm', 'channel'
    linked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(primary_session_name, linked_session_name)
);
```

### API Endpoints (Essential Only)
```
# User Management
GET    /api/v1/{instance}/users/                    # List users
GET    /api/v1/{instance}/users/{user_id}           # Get user details
PUT    /api/v1/{instance}/users/{user_id}           # Update user
DELETE /api/v1/{instance}/users/{user_id}           # Delete user

# Simple User Linking  
GET    /api/v1/{instance}/users/{user_id}/links     # Get linked accounts
POST   /api/v1/{instance}/users/{user_id}/link      # Link another user
DELETE /api/v1/{instance}/users/{user_id}/link/{linked_user_id}  # Unlink
```

### Message Routing Logic (Basic)
```python
def route_message_to_user(user_id, message):
    # Get primary user and all linked users
    linked_users = get_all_linked_users(user_id)
    
    # Send to all channels
    for user in linked_users:
        send_to_channel(user.channel_type, user.channel_id, message)
```

## 🔧 CRITICAL CODE CHANGES REQUIRED

### 1. **Extend User Model for Multi-Channel Support**
**File**: `src/db/models.py` - Add fields to existing User class:
```python
class User(Base):
    # ... existing fields ...
    
    # Multi-channel identifiers
    discord_user_id = Column(String, nullable=True, index=True)
    discord_username = Column(String, nullable=True) 
    slack_user_id = Column(String, nullable=True, index=True)
    channel_type = Column(String, nullable=False, default='whatsapp')
```

### 2. **Update Discord Handler User Registration**
**File**: `src/channels/discord/channel_handler.py:122-134` - Store Discord ID in User model:
```python
# Current user dict needs to include storage fields
user_dict = {
    "discord_user_id": str(message.author.id),  # ✅ Already exists
    "username": message.author.name,            # ✅ Already exists
    "phone_number": None,                       # 🔧 Need to handle None case
    "whatsapp_jid": None,                       # 🔧 Need to handle None case  
    "channel_type": "discord"                   # 🆕 New field needed
}
```

### 3. **Update UserService for Multi-Channel Creation**
**File**: `src/services/user_service.py` - Add Discord user creation method:
```python
def get_or_create_user_by_discord_id(self, discord_user_id, instance_name, username, session_name, db):
    # New method to create Discord users similar to get_or_create_user_by_phone
```

### 4. **Message Router Integration**
**Files**: Both `src/channels/whatsapp/handlers.py` and `src/channels/discord/channel_handler.py`
- **Current**: Each channel creates users independently  
- **Needed**: Route through unified user service that handles all channel types

### 5. **Session Context Bridge Implementation**
**New Service**: `src/services/session_context_service.py`
- Map Discord guild sessions to WhatsApp group sessions
- Handle DM to DM routing appropriately
- Preserve conversation context across channels

## 📋 IMPLEMENTATION PHASES

### Phase 1: Multi-Channel User Model (Week 1-2)
**Goal**: Extend database and user service for multi-channel support
- Extend User model with Discord/Slack fields  
- Update UserService for Discord user creation
- Create database migration scripts
- Update existing handlers to use new fields

**Deliverables:**
- Updated User model with multi-channel support
- UserService methods for Discord user management
- Database migrations with backward compatibility
- Updated WhatsApp and Discord handlers

### Phase 2: User Linking & API Endpoints (Week 3-4)  
**Goal**: Manual user linking capabilities and CRUD API
- Create user_channel_links table
- Implement user linking service layer
- Create REST API endpoints for user management  
- Add admin endpoints for link management

**Deliverables:**
- Database linking tables
- UserLinkingService for managing relationships
- REST API with proper authentication
- Admin interface for user linking

### Phase 3: Cross-Channel Message Routing (Week 5-6)
**Goal**: Route messages to linked accounts with context preservation
- Create SessionContextService for session mapping
- Integrate cross-channel routing in message handlers
- Add session context linking (guild↔group, DM↔DM)
- Handle message deduplication and formatting

**Deliverables:**
- SessionContextService for context mapping
- Enhanced message routing with cross-channel support
- Session context preservation system
- Message deduplication and delivery tracking

## 🔧 TECHNICAL SPECIFICATIONS

### Data Model
```python
# Extend existing User model with linking capability
class UserChannelLink:
    id: str
    primary_user_id: str      # The "main" user account
    linked_user_id: str       # The linked account
    channel_type: str         # whatsapp, discord, slack
    linked_by_admin: str      # Who created this link
    linked_at: datetime
    is_active: bool = True    # Soft delete capability
```

### API Response Format
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "display_name": "John Doe",
  "channel_type": "whatsapp",
  "instance_name": "my-instance",
  "linked_accounts": [
    {
      "user_id": "660f9511-f30c-42e5-b827-557766551111",
      "channel_type": "discord", 
      "display_name": "JohnD#1234",
      "linked_at": "2024-01-15T10:30:00Z"
    }
  ],
  "created_at": "2024-01-10T09:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Message Routing Configuration
```python
CHANNEL_ROUTING_CONFIG = {
    'max_channels_per_message': 3,  # Prevent spam
    'deduplication_window': 300,    # 5 minutes
    'retry_attempts': 2,
    'fallback_channel': 'whatsapp'  # Primary channel for failures
}
```

## ⚠️ RISK MITIGATION

### Technical Risks
1. **Performance Impact**: User linking lookups could slow message processing
   - **Mitigation**: Add database indexes, implement caching layer
2. **Message Duplication**: Same message sent multiple times
   - **Mitigation**: Deduplication based on message ID + timestamp
3. **Circular References**: User A links to User B who links back to User A
   - **Mitigation**: Detect and prevent circular links during creation

### Business Risks
1. **User Privacy**: Linking accounts without consent
   - **Mitigation**: Admin-only linking, clear logging of who linked what
2. **Spam Multiplication**: Spam messages reach more channels
   - **Mitigation**: Rate limiting, spam detection integration
3. **Channel Conflicts**: Messages that don't work on certain channels
   - **Mitigation**: Channel-specific formatting, graceful degradation

## 📊 MONITORING & METRICS

### Key Metrics to Track
- API response times (target: <200ms average)
- User linking operations per day
- Cross-channel message delivery success rate (target: >95%)
- Error rates for each endpoint (target: <1%)
- Database query performance for user lookups

### Health Checks
- `/health/user-api` - API endpoint availability
- `/health/user-links` - Linking service status  
- `/health/message-routing` - Cross-channel routing health

## 🧪 TESTING STRATEGY

### Unit Testing
- User CRUD operations
- User linking/unlinking logic
- Message routing algorithms
- Error handling scenarios

### Integration Testing
- End-to-end user linking flow
- Cross-channel message delivery
- API authentication and authorization
- Database integrity checks

### Manual Testing Scenarios
1. Link WhatsApp user to Discord user → Send message → Verify both channels receive it
2. Unlink users → Send message → Verify only original channel receives it
3. Try to create circular link → Verify system prevents it
4. Delete user → Verify all links are cleaned up

## 📚 DOCUMENTATION REQUIREMENTS

### API Documentation
- Complete OpenAPI/Swagger specification
- Code examples for each endpoint
- Authentication setup instructions
- Error code reference

### Developer Documentation  
- Database schema documentation
- Message routing flow diagrams
- Configuration options reference
- Troubleshooting guide

### User Documentation
- Admin guide for linking users
- Understanding cross-channel notifications
- Privacy implications of user linking

## 🎯 DEFINITION OF DONE

This wish is considered **COMPLETE** when:

✅ **All API endpoints are functional** and documented  
✅ **Admin can manually link users** across channels via API  
✅ **Messages route to all linked channels** for a user  
✅ **No breaking changes** to existing functionality  
✅ **Unit test coverage >85%** for new code  
✅ **Performance targets met** (<200ms user operations)  
✅ **Documentation complete** (API docs + developer guide)  
✅ **Manual testing scenarios pass** (100% success rate)
✅ **Multi-channel user registration works** (WhatsApp, Discord, Slack)
✅ **Session context preserved** in cross-channel routing (group↔guild, DM↔DM)
✅ **Database migration successful** with zero data loss  

## 🚫 OUT OF SCOPE (For Now)

The following features are explicitly **NOT** included in this wish:

- Automatic identity verification workflows
- SMS/Email verification systems  
- Complex privacy compliance features
- Machine learning identity matching
- Advanced audit and compliance reporting
- Enterprise user management features
- OAuth/SSO integration
- Bulk user import/export tools
- User profile customization beyond basic fields

## 💡 FUTURE ENHANCEMENTS (Parking Lot)

Ideas for future wishes once this foundation is complete:

1. **Smart Identity Suggestions**: ML-based suggestions for potential user links
2. **User-Initiated Linking**: Allow users to link their own accounts with verification
3. **Advanced Notification Preferences**: Per-channel notification settings
4. **Analytics Dashboard**: Usage metrics and user linking insights
5. **Bulk Operations**: Admin tools for bulk user operations
6. **Channel-Specific Features**: Platform-specific message formatting and features

---

## 📝 NOTES FROM PLANNING SESSION

**Key Insights from User:**
- Emphasis on simplicity over comprehensive features
- Focus on basic sync functionality first
- Avoid over-engineering verification flows
- Manual admin linking is sufficient for initial version
- Cross-channel notification is the primary business value

**Technical Decisions Made:**
- Use simple linking table instead of complex identity graph
- Manual admin-only linking (no user self-service)
- Basic message routing without advanced features
- Leverage existing authentication system
- Maintain full backward compatibility

**Success Definition:**
The system successfully allows admins to say "User A on WhatsApp is the same person as User B on Discord" and then messages intended for that person reach them on both channels.

This is a **foundational feature** that enables future enhancements while delivering immediate business value through improved user reachability across channels.