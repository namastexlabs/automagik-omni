# 🧞 Unified Multi-Channel Endpoints - Implementation Task

**Task ID**: `unified-multichannel-endpoints`  
**Priority**: High  
**Complexity**: Medium-High  
**Estimated Time**: 5-7 days  

## 🎯 Task Overview

Implement unified API endpoints that work seamlessly across WhatsApp and Discord channels, providing a consistent interface while preserving channel-specific functionality through a multi-tenant architecture.

## 📋 Desired Outcomes

### Primary Goals
- **Single API Interface**: One set of endpoints works for all supported channels
- **Multi-Tenant Support**: Each instance maintains complete data isolation
- **Extensible Architecture**: Easy to add new channels (Slack, Telegram, etc.)
- **Backward Compatibility**: Existing WhatsApp endpoints remain functional
- **Performance Optimization**: Sub-500ms response times for standard operations

### Target Endpoints
```
GET /api/v1/instances/{instance_name}/chats
GET /api/v1/instances/{instance_name}/contacts  
GET /api/v1/instances/{instance_name}/channels
GET /api/v1/instances/{instance_name}/messages/{chat_id}
```

## 🏗️ Technical Architecture

### Unified Response Format
```json
{
    "instance_name": "my-bot",
    "channel_type": "whatsapp|discord", 
    "data": [...],
    "metadata": {
        "total_count": 50,
        "last_updated": "2024-08-26T10:00:00Z",
        "has_more": true,
        "pagination": {
            "limit": 25,
            "offset": 0,
            "next_offset": 25
        }
    }
}
```

### Channel Handler Architecture
```python
# Factory Pattern Implementation
class ChannelHandlerFactory:
    @staticmethod
    def get_handler(channel_type: str) -> BaseChannelHandler:
        if channel_type == "whatsapp":
            return WhatsAppChatHandler()
        elif channel_type == "discord": 
            return DiscordChatHandler()
        raise UnsupportedChannelError(f"Channel {channel_type} not supported")

# Base Handler Interface
class BaseChannelHandler(ABC):
    @abstractmethod
    async def get_chats(self, instance_config: InstanceConfig, **params) -> UnifiedResponse
    
    @abstractmethod
    async def get_contacts(self, instance_config: InstanceConfig, **params) -> UnifiedResponse
    
    @abstractmethod  
    async def get_channels(self, instance_config: InstanceConfig, **params) -> UnifiedResponse
```

### Unified Schema Definitions
```python
class UnifiedChatResponse(BaseModel):
    id: str                          # Chat/Channel ID
    name: str                        # Display name
    type: str                        # "private", "group", "channel"
    participant_count: int           # Member count
    last_message: Optional[dict]     # Latest message preview
    last_activity: datetime          # Last activity timestamp
    avatar_url: Optional[str]        # Chat/channel avatar
    channel_specific: dict           # Channel-native data

class UnifiedContactResponse(BaseModel):
    id: str                          # Contact ID
    display_name: str                # Name to display
    username: Optional[str]          # @username (Discord/Slack)
    phone: Optional[str]             # Phone (WhatsApp)
    status: str                      # "online", "offline", "away"
    avatar_url: Optional[str]        # Profile picture
    is_bot: bool                     # Bot account flag
    channel_specific: dict           # Channel-native data
```

## 🔌 API Integration References

### WhatsApp Evolution API Endpoints
```
GET  /chat/findChats/{instance}     - List chats for instance
POST /chat/findMessages/{instance}  - Retrieve messages from chats  
POST /chat/findContacts/{instance}  - List contacts for instance
POST /chat/findStatusMessage/{instance} - Get status messages
```

**Authentication**: Bearer token with Evolution API key  
**Rate Limits**: Varies by Evolution API server configuration  
**Data Format**: WhatsApp-specific JSON structure  

### Discord API Endpoints
```
GET /channels/{channel_id}/messages           - Get channel messages
GET /guilds/{guild_id}/channels               - List guild channels  
GET /users/@me/channels                       - List direct message channels
GET /channels/{channel_id}                    - Get channel info
GET /guilds/{guild_id}/members                - List guild members
```

**Authentication**: Bot token via Authorization header  
**Rate Limits**: 50 requests/second globally, 5 requests/second per channel  
**Data Format**: Discord-specific JSON structure  

## 📁 File Structure Implementation

```
src/api/routes/
├── unified.py              # 🆕 Main unified endpoints
├── whatsapp.py            # Existing WhatsApp specific  
└── discord.py             # 🆕 Discord specific (if needed)

src/channels/
├── base.py                # Base abstractions
├── handlers/              # 🆕 Channel handlers
│   ├── __init__.py
│   ├── base_handler.py    # Abstract base class
│   ├── whatsapp_handler.py # WhatsApp implementation
│   ├── discord_handler.py  # Discord implementation  
│   └── factory.py         # Handler factory
└── schemas/               # 🆕 Unified schemas
    ├── __init__.py
    ├── unified_responses.py # Response models
    └── channel_mappings.py  # Channel-specific mappings

tests/
├── test_unified_endpoints.py      # Unit tests for endpoints
├── test_multichannel_integration.py # Integration tests
├── test_channel_handlers.py       # Handler-specific tests
└── test_e2e_multichannel.py      # End-to-end tests
```

## 🧪 Success Criteria & Validation

### ✅ Core Functionality Achievements
- [ ] **Multi-Channel Unified Response**: Same API structure for WhatsApp and Discord
- [ ] **Multi-Tenant Instance Isolation**: Instances see only their own data
- [ ] **Channel Handler Factory**: Correctly routes requests to appropriate handlers
- [ ] **Backward Compatibility**: Existing WhatsApp endpoints remain functional
- [ ] **Error Handling**: Graceful degradation when APIs unavailable

### ✅ Performance Benchmarks
- [ ] **< 200ms**: Simple chat/contact listing (cached)
- [ ] **< 500ms**: Complex queries with search/filtering  
- [ ] **< 1000ms**: Cross-channel operations
- [ ] **< 2000ms**: Large dataset pagination
- [ ] **< 50MB**: Memory usage per instance handler
- [ ] **100 req/min**: Rate limiting per instance

### ✅ Endpoint-Specific Acceptance Criteria

#### `GET /api/v1/instances/{instance_name}/chats`
- [ ] Returns 200 for valid instances
- [ ] Returns 404 for non-existent instances
- [ ] Unified response format across all channel types
- [ ] Pagination support (`limit`, `offset` parameters)
- [ ] Channel-specific data in `channel_specific` field
- [ ] Search functionality (`?search=query`)

#### `GET /api/v1/instances/{instance_name}/contacts`  
- [ ] Handles WhatsApp contacts (phone numbers + names)
- [ ] Handles Discord users (usernames + display names)
- [ ] Presence status mapped consistently
- [ ] Avatar URLs normalized across channels
- [ ] Bot accounts properly identified

#### `GET /api/v1/instances/{instance_name}/channels`
- [ ] Discord: Returns text/voice channels + categories
- [ ] WhatsApp: Returns groups (mapped as channels)  
- [ ] Permission filtering (only accessible channels)
- [ ] Channel metadata (member counts, descriptions)

### ✅ Testing Strategy

#### Phase 1: Foundation Tests
```python
# test_channel_handlers.py
test_whatsapp_handler_initialization()
test_discord_handler_initialization() 
test_factory_pattern_routing()
test_unified_response_schemas()
test_error_handling_graceful_degradation()
```

#### Phase 2: Endpoint Tests
```python  
# test_unified_endpoints.py
test_chats_endpoint_whatsapp()
test_chats_endpoint_discord()  
test_contacts_endpoint_whatsapp()
test_contacts_endpoint_discord()
test_cross_instance_isolation()
test_pagination_and_search()
```

#### Phase 3: Integration Tests
```python
# test_e2e_multichannel.py
test_full_whatsapp_to_discord_workflow()
test_concurrent_multi_instance_requests()
test_failover_and_error_handling() 
test_real_api_integration()
test_performance_benchmarks()
```

### ✅ Error Resilience Validation
- [ ] **API Unavailable**: Graceful fallback with cached data
- [ ] **Authentication Failure**: Clear error messages with retry guidance
- [ ] **Rate Limit Exceeded**: Proper 429 responses with retry headers
- [ ] **Invalid Instance**: 404 with helpful error details  
- [ ] **Malformed Requests**: 400 with validation error specifics
- [ ] **Timeout Handling**: Circuit breaker pattern implementation

### ✅ Security & Isolation
- [ ] **API Key Authentication**: Proper verification for all endpoints
- [ ] **Instance Data Isolation**: No data leakage between tenants
- [ ] **Input Validation**: Prevents injection attacks
- [ ] **Rate Limiting**: Per-instance and global limits enforced
- [ ] **Audit Logging**: Security events properly logged

## 📈 Implementation Phases

### Phase 1: Foundation (Day 1-2)
1. Create unified response schemas (`unified_responses.py`)
2. Build channel handler factory (`handlers/factory.py`)  
3. Implement base handler interface (`handlers/base_handler.py`)
4. Create foundational unit tests

### Phase 2: Channel Handlers (Day 2-4)
1. Implement WhatsApp handler (wrap existing Evolution client)
2. Create Discord handler (new Discord API client)
3. Add error handling and retry mechanisms
4. Write handler-specific tests

### Phase 3: Unified Endpoints (Day 4-6) 
1. Build unified API endpoints (`routes/unified.py`)
2. Implement pagination and search functionality
3. Add comprehensive validation and error handling
4. Create endpoint integration tests

### Phase 4: Validation & Polish (Day 6-7)
1. Run full test suite and fix issues
2. Performance optimization and benchmarking
3. Security audit and penetration testing
4. Documentation and deployment preparation

## 🚀 Definition of Done

**This task is complete when:**

1. **All unified endpoints** return consistent responses for both WhatsApp and Discord
2. **100% test coverage** with passing unit, integration, and e2e tests  
3. **Performance benchmarks met** (< 500ms response times)
4. **Security validation passed** (no data leakage, proper authentication)
5. **Backward compatibility confirmed** (existing WhatsApp endpoints work)
6. **Documentation complete** (API docs, integration guides)
7. **Production deployment successful** with monitoring in place

## 📚 Reference Links

- **Discord API Documentation**: https://discord.com/developers/docs/
- **Evolution API Documentation**: https://doc.evolution-api.com/v2/api-reference/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **SQLAlchemy Multi-Tenancy**: https://docs.sqlalchemy.org/en/20/orm/examples.html#examples-sharding

---

**Created**: 2024-08-26  
**Last Updated**: 2024-08-26  
**Assigned To**: automagik-omni-genie Development Team  
**Status**: Ready for Implementation 🚀