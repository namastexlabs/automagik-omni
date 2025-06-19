# Omnihub Multi-Tenancy & Persistence Roadmap

## 0 — Purpose
This document captures **why** and **how** we will extend the current single-tenant Omnihub service into a multi-tenant, database-backed platform while keeping full backward compatibility with the existing `.env` configuration.

Goals:
1. **Multiple WhatsApp instances** served by **one FastAPI process**.
2. Per-instance routing of inbound/outbound traffic, Agent API credentials and timeouts.
3. Persist configuration in **SQLite via SQLAlchemy** for out-of-the-box local development.
4. Expose CRUD & management tooling (REST + CLI).
5. Keep existing behaviour — `.env` continues to bootstrap a *default instance* and the classic `/webhook/evolution` endpoint stays functional.

---
## 1 — Current Architecture (single-tenant)
```
┌──────────────┐   WhatsApp webhook   ┌─────────────────┐
│ Evolution    │ ───────────────────▶ │ /webhook/evolution │
│ API Gateway  │                     │   FastAPI        │
└──────────────┘                     └─────────────────┘
                                            │
                                            ▼
                                  src/services/agent_service
                                            │
                                            ▼
                               src/services/agent_api_client
                                            │
                                            ▼
                                   Automagik Agents API
```
Key files:
* `src/api/app.py` – FastAPI server (single `/webhook/evolution`).
* `src/channels/whatsapp/evolution_api_sender.py` – sends outbound msgs.
* `src/services/agent_api_client.py` – talks to Agents API.
* `src/config.py` – reads global env vars.

### Environment variables in play
| ENV | Code usage | Purpose |
|------|------------|---------|
| `WHATSAPP_INSTANCE` | `WhatsAppConfig.instance` | Outbound instance slug |
| `SESSION_ID_PREFIX` | `WhatsAppConfig.session_id_prefix` | Adds a prefix to session names/id |
| `AGENT_API_URL` / `AGENT_API_KEY` / `DEFAULT_AGENT_NAME` / `AGENT_API_TIMEOUT` | `AgentApiConfig` | Agents API connection |
| `EVOLUTION_TRANSCRIPT_API(_KEY)` & `EVOLUTION_MINIO_URL` | Audio transcription / storage |
| `LOG_*`, `API_HOST`, `API_PORT` | Logging & server setup |

---
## 2 — New Requirements
* Create additional WhatsApp instances dynamically (e.g. `flashinho_v2`).
* Each instance may **override**:
  * Evolution server URL & API-key (outbound).
  * WhatsApp instance slug & session-id prefix.
  * Agents API URL, key, default agent, timeout.
* Provide REST endpoints and a CLI to CRUD those configs.
* Store configs in SQLite with SQLAlchemy (later Postgres).
* Maintain legacy endpoint that uses `.env` to act as the *default* instance.

---
## 3 — High-Level Design
### 3.1 Database layer
File | Description
-----|------------
`src/db/database.py` | Engine, SessionLocal, Base declaration (`sqlite:///./omnihub.db`).
`src/db/models.py` | `InstanceConfig` SQLAlchemy model (see schema below).
`src/db/bootstrap.py` | `ensure_default_instance()` — seeds row from `.env` on first boot.

#### InstanceConfig Schema
```python
class InstanceConfig(Base):
    __tablename__ = "instance_configs"
    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String, unique=True, index=True)  # flashinho_v2
    evolution_url     = Column(String, nullable=False)
    evolution_key     = Column(String, nullable=False)
    whatsapp_instance = Column(String, nullable=False)
    session_id_prefix = Column(String)
    agent_api_url     = Column(String, nullable=False)
    agent_api_key     = Column(String, nullable=False)
    default_agent     = Column(String, nullable=False)
    agent_timeout     = Column(Integer, default=60)
    is_default        = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3.2 FastAPI Changes
1. **Dependency** `get_db()` provides a session per-request.
2. Two webhook paths share the same core handler:
    ```python
    @app.post("/webhook/evolution")
    async def evolution_default(...):
        cfg = db.query(InstanceConfig).filter_by(is_default=True).first()
        return await _handle_evolution_webhook(cfg, request)

    @app.post("/webhook/evolution/{instance_name}")
    async def evolution_tenant(instance_name: str, ...):
        cfg = db.query(InstanceConfig).filter_by(name=instance_name).first()
        ...
    ```
3. `_handle_evolution_webhook(cfg, request)`:
   * primes `evolution_api_sender` with `cfg.evolution_url`, `cfg.evolution_key`, `cfg.whatsapp_instance`.
   * instantiates an **override** `AgentApiClient` (or passes overrides) using per-instance credentials.
   * calls `agent_service.process_whatsapp_message(data, agent_client)`.

### 3.3 CRUD API
Router: `src/api/routes/instances.py`
| Method | Path | Action |
|--------|------|--------|
| `POST` | `/instances` | create new instance |
| `GET` | `/instances` | list all |
| `GET` | `/instances/{name}` | read one |
| `PUT` | `/instances/{name}` | update |
| `DELETE` | `/instances/{name}` | delete |

### 3.4 CLI Tool
Using **Typer** (optional):
```
omnihub instance add \
  --name flashinho_v2 \
  --evolution-url http://localhost:4040 \
  --evolution-key namastex8888 \
  --whatsapp-instance flashinho_v2 \
  --session-id-prefix dev- \
  --agent-api-url http://localhost:38881 \
  --agent-api-key namastex888 \
  --default-agent flashinho_pro \
  --agent-timeout 600
```

---
## 4 — Implementation Steps
| # | Task | Affected files |
|---|------|----------------|
| 0 | `uv add "sqlalchemy>=2.0" "alembic" "typer[all]"` | – |
| 1 | `db/database.py`, `db/models.py`, `db/bootstrap.py` | new |
| 2 | Call `Base.metadata.create_all()` + `ensure_default_instance()` in `cli/main.py` | `cli/main.py` |
| 3 | `api/deps.py` – `get_db()` | new |
| 4 | Implement CRUD router & mount | `api/routes/instances.py`, `api/app.py` |
| 5 | Refactor webhook logic into shared `_handle_evolution_webhook()` | `api/app.py` |
| 6 | Extend `AgentApiClient` to accept runtime overrides | `services/agent_api_client.py` |
| 7 | Modify `agent_service.process_whatsapp_message(..., agent_client=None)` | `services/agent_service.py` |
| 8 | Add Typer CLI (`src/cli/instance_cli.py`) & register in `pyproject.toml` | new |
| 9 | Unit tests (`tests/`) for CRUD & webhook flow | new |
| 10 | README & docs update | `README.md`, **this file** |

---
## 5 — Backward Compatibility
* `.env` continues to be loaded by `src/config.py`.
* On first boot **only if no rows exist** we seed `InstanceConfig` with the env values **and mark it `is_default=True`**.
* The legacy endpoint `/webhook/evolution` delegates to that default row. Nothing breaks for existing integrations.

---
## 6 — Testing Strategy
1. **Unit**: CRUD operations with an in-memory SQLite DB.
2. **Integration**: Spin up mocked Evolution & Agents APIs, hit webhook endpoint, assert outbound requests.
3. **Regression**: Ensure the default endpoint still works when `.env` only (no extra rows).

---
## 7 — Roll-out Plan
1. Merge DB layer & default seeding (no runtime behaviour change).
2. Introduce new webhook and CRUD endpoints (disabled behind env flag if necessary).
3. Migrate staging to use new endpoint for a second WhatsApp instance.
4. Remove flag / make multi-tenant the default.

---
## 8 — Future Enhancements
* Switch SQLite → Postgres in production (`DATABASE_URL` env).
* Per-instance rate limiting & analytics.
* Web UI for managing instances.
* Secrets vault integration for API keys.

---
> **Document version:** 2025-06-19 