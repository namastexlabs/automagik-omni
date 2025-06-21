# Analysis: Multi-Tenancy Architecture

## Overview
- **Feature**: Multi-Tenancy Support with SQLite Persistence
- **Type**: Major architectural enhancement
- **Complexity**: High
- **Estimated Time**: 8-12 hours (across all workflows)

## Requirements Analysis

### Functional Requirements
1. **Multiple WhatsApp instances** served by one FastAPI process
2. **Per-instance routing** of inbound/outbound traffic
3. **Per-instance configuration** override (Evolution API, Agent API credentials)
4. **SQLite persistence** with SQLAlchemy ORM
5. **CRUD API** for instance management
6. **CLI tools** for administration
7. **Backward compatibility** with existing `.env` configuration
8. **Default instance** behavior preservation

### Technical Requirements
- **Database**: SQLite via SQLAlchemy 2.0+ (already in dependencies)
- **New Dependencies**: Alembic (migrations), Typer (CLI)
- **Webhook Routes**: 
  - `/webhook/evolution` (default/legacy)
  - `/webhook/evolution/{instance_name}` (multi-tenant)
- **CRUD Endpoints**: `/instances/*` for management
- **Configuration Model**: `InstanceConfig` with per-instance overrides

## Existing Architecture Analysis

### Current Single-Tenant Pattern
```python
# src/api/app.py - Current webhook endpoint
@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    # Uses global config from src/config.py
    # Single instance handling
```

### Current Configuration Pattern
```python
# src/config.py - Environment-based configuration
class Config(BaseModel):
    agent_api: AgentApiConfig = AgentApiConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    # Global singleton pattern
```

### Current Service Pattern
```python
# src/services/agent_api_client.py - Singleton pattern
class AgentApiClient:
    def __init__(self):
        self.api_url = config.agent_api.url
        self.api_key = config.agent_api.api_key
        # Uses global config
```

## Implementation Plan

### Database Layer (`src/db/`)
```
src/db/
├── __init__.py          # Module exports
├── database.py          # SQLAlchemy engine and session
├── models.py            # InstanceConfig model
└── bootstrap.py         # Default instance seeding
```

#### InstanceConfig Model
```python
class InstanceConfig(Base):
    __tablename__ = "instance_configs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # flashinho_v2
    evolution_url = Column(String, nullable=False)
    evolution_key = Column(String, nullable=False)
    whatsapp_instance = Column(String, nullable=False)
    session_id_prefix = Column(String)
    agent_api_url = Column(String, nullable=False)
    agent_api_key = Column(String, nullable=False)
    default_agent = Column(String, nullable=False)
    agent_timeout = Column(Integer, default=60)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### FastAPI Changes (`src/api/`)
```
src/api/
├── app.py               # Updated with multi-tenant routing
├── deps.py              # Database dependency injection
└── routes/
    └── instances.py     # CRUD API for instance management
```

#### Multi-Tenant Webhook Routing
```python
# Two endpoints sharing core logic
@app.post("/webhook/evolution")
async def evolution_default(request: Request, db: Session = Depends(get_db)):
    cfg = db.query(InstanceConfig).filter_by(is_default=True).first()
    return await _handle_evolution_webhook(cfg, request)

@app.post("/webhook/evolution/{instance_name}")
async def evolution_tenant(instance_name: str, request: Request, db: Session = Depends(get_db)):
    cfg = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Instance not found")
    return await _handle_evolution_webhook(cfg, request)
```

### Service Layer Modifications
```python
# src/services/agent_api_client.py - Runtime configuration injection
class AgentApiClient:
    def __init__(self, config_override: Optional[InstanceConfig] = None):
        if config_override:
            self.api_url = config_override.agent_api_url
            self.api_key = config_override.agent_api_key
            # Use per-instance configuration
        else:
            # Fallback to global config
```

### CLI Tools (`src/cli/`)
```
src/cli/
├── __init__.py
├── main.py              # Updated with database bootstrap
└── instance_cli.py      # Typer-based instance management
```

## Risk Assessment

### Complexity Risks
- **Database Integration**: Adding SQLAlchemy layer to existing codebase
- **Configuration Override**: Complex per-instance config injection
- **Backward Compatibility**: Ensuring existing behavior is preserved
- **State Management**: Moving from global singletons to per-instance state

### Dependency Risks
- **SQLAlchemy**: Already included in dependencies ✅
- **Alembic**: Need to add for migrations
- **Typer**: Need to add for CLI tools
- **Database Location**: SQLite file placement and permissions

### API Limitations
- **Performance**: Database queries on every webhook
- **Concurrency**: SQLite limitations under high load
- **Migration**: From single-tenant to multi-tenant data

### Testing Challenges
- **Database Mocking**: In-memory SQLite for tests
- **Configuration Injection**: Mocking per-instance configs
- **Backward Compatibility**: Ensuring legacy behavior works

## Implementation Strategy

### Phase 1: Database Foundation
1. Add Alembic and Typer to dependencies
2. Create database layer (`src/db/`)
3. Implement `InstanceConfig` model
4. Add database bootstrap logic
5. Create initial migration

### Phase 2: API Layer Changes
1. Add database dependency injection
2. Implement CRUD routes for instances
3. Refactor webhook handler for multi-tenancy
4. Add configuration override logic

### Phase 3: Service Layer Updates
1. Modify `AgentApiClient` for runtime config
2. Update `EvolutionApiSender` for per-instance config
3. Add configuration injection throughout service layer

### Phase 4: CLI and Management
1. Implement Typer-based CLI commands
2. Add instance management commands
3. Update application bootstrap

## Testing Strategy

### Unit Tests
- Database model operations
- Configuration override logic
- CRUD API endpoints
- CLI command functionality

### Integration Tests
- End-to-end webhook flow with different instances
- Database persistence and retrieval
- Backward compatibility with `.env` configuration
- Default instance behavior

### Migration Tests
- Bootstrap from clean state
- Default instance creation from `.env`
- Multi-instance scenarios

## Success Criteria

- [ ] Multiple instances can be created and managed
- [ ] Each instance can have different Evolution/Agent API configs
- [ ] Legacy `/webhook/evolution` endpoint continues to work
- [ ] New `/webhook/evolution/{instance}` endpoints route correctly
- [ ] CRUD API allows full instance management
- [ ] CLI tools provide administration capabilities
- [ ] Database persists configuration properly
- [ ] Backward compatibility maintained 100%
- [ ] Performance impact minimal (<100ms overhead)

## Pattern Recommendations

### Configuration Injection Pattern
```python
# Instead of global singletons, use dependency injection
async def handle_message(instance_config: InstanceConfig):
    agent_client = AgentApiClient(config_override=instance_config)
    evolution_sender = EvolutionApiSender(config_override=instance_config)
```

### Repository Pattern
```python
class InstanceRepository:
    async def get_by_name(self, name: str) -> Optional[InstanceConfig]
    async def get_default(self) -> Optional[InstanceConfig]
    async def create(self, instance: InstanceConfig) -> InstanceConfig
```

### Factory Pattern
```python
class ServiceFactory:
    @staticmethod
    def create_agent_client(config: InstanceConfig) -> AgentApiClient
    @staticmethod 
    def create_evolution_sender(config: InstanceConfig) -> EvolutionApiSender
```

## Key Files to Modify

1. `pyproject.toml` - Add Alembic, Typer dependencies
2. `src/api/app.py` - Multi-tenant webhook routing
3. `src/services/agent_api_client.py` - Configuration injection
4. `src/channels/whatsapp/evolution_api_sender.py` - Per-instance config
5. `src/config.py` - Maintain global config for defaults
6. `src/cli/main.py` - Database bootstrap

## Next Steps for BUILDER

1. **Database Layer**: Implement `src/db/` module with models and bootstrap
2. **Dependency Updates**: Add Alembic and Typer to `pyproject.toml`
3. **API Modifications**: Create multi-tenant webhook routing
4. **Service Updates**: Add configuration injection to services
5. **CLI Implementation**: Create Typer-based management commands
6. **Migration Strategy**: Implement database initialization and seeding

The architecture is well-designed and implementable. The main challenge will be cleanly injecting per-instance configuration throughout the existing service layer while maintaining backward compatibility.