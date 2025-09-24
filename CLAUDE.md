# CLAUDE.md

This guide keeps Claude Code aligned with the Automagik Omni codebase. Use it as the source of truth when planning work, choosing commands, or understanding how the system is stitched together.

## Essential Commands

### Environment Setup
- `make install` — wraps `uv sync`, ensures `.env` exists, and prints a status banner.

### Development Servers
- `make dev` — run FastAPI (`src.api.app:app`) with uvicorn reload, honouring `.env` overrides for host/port/log level.
- `make start-local` / `make stop-local` — manage the PM2 process group defined in `ecosystem.config.js` (API ➜ health wait ➜ Discord service manager).
- `make logs` — tail combined PM2 output under `logs/`.

## Architecture Overview

### Tech Stack
- **Language & Runtime**: Python ≥ 3.12, Typer CLI entry points, asyncio-friendly FastAPI.
- **Web**: FastAPI + uvicorn, Starlette middleware, custom telemetry decorators (`src.core.telemetry`).
- **Database**: SQLAlchemy ORM + Alembic migrations; default SQLite with optional PostgreSQL (async not required).
- **Messaging Channels**: WhatsApp via Evolution API + AMQP (`pika`), Discord bot integration via `discord.py` IPC bridge.
- **Agent Integrations**: Automagik and Hive agent APIs via synchronous + async HTTPX clients.
- **Tooling**: `uv` package manager, Ruff, Black, mypy, pytest (asyncio mode auto), PM2 for process orchestration.

### Project Layout Essentials
```
src/
├── api/                # FastAPI app, dependencies, and route modules (instances, omni, access, traces)
├── channels/           # Channel adapters (whatsapp, discord) + shared helpers
├── cli/                # Typer command surface (start server, telemetry, instance + Discord management)
├── commands/           # Legacy orchestration scripts (Discord service manager, etc.)
├── core/               # Cross-cutting utilities (telemetry, exceptions)
├── db/                 # SQLAlchemy models, session wiring, bootstrap helpers
├── services/           # Business logic (message router, agent clients, access control, tracing, user services)
└── utils/              # Date utilities, normalisation helpers, etc.
```
Supporting assets include `alembic/` migrations, `scripts/` automation, `docs/` marketing material, and `genie/` context files.

### Runtime Components
- **API server (`src/api/app.py`)** — configures CORS, request logging middleware, telemetry tracking, and registers routers for health, instance CRUD, omni abstractions, and access control.
- **Channel handlers (`src/channels/*`)** — encapsulate provider-specific logic (Evolution API sender/receiver, Discord bot orchestration, media handling, streaming support). Factory registration happens at import time (`ChannelHandlerFactory`).
- **Service layer (`src/services/*`)** — houses agent API clients, message routing, access control, tracing, Discord management, and Automagik/Hive integrations. The router mediates between inbound channel payloads and agent APIs.
- **Database layer (`src/db`)** — SQLAlchemy models for instances, users, access policies, trace records. `SessionLocal` is the sync factory used across API, CLI, and tests.
- **Telemetry & logging** — `src/core/telemetry.TelemetryClient` emits OTLP-compatible spans (auto-disabled in dev/test); `src/logger.setup_logging` normalises log format across services.
- **Process orchestration** — `ecosystem.config.js` defines the PM2 trio: uvicorn API, readiness wait script, and Discord service manager.

## Messaging & Channel Flow
1. Inbound events reach FastAPI routes (see `src/api/routes/messages.py` and channel-specific webhook endpoints) or arrive via Discord IPC bridges; middleware logs and masks sensitive fields before handing off to business logic.
2. Payloads are normalised by channel handlers (`src/channels/whatsapp/handlers.py`, `src/channels/discord/channel_handler.py`).
3. `MessageRouter` consults `access_control_service`, resolves agent routing (`agent_api_client`, Hive streaming), and pushes responses back through channel-specific senders (`evolution_api_sender`, Discord service).
4. Traces are recorded through `trace_service` when `AUTOMAGIK_OMNI_ENABLE_TRACING=true` (default).

## API Surface
- `src/api/routes/instances.py` — REST CRUD for tenant configs, QR provisioning, channel capability introspection.
- `src/api/routes/omni.py` — unified contacts/chats endpoints that wrap channel-specific handlers and return consistent schemas.
- `src/api/routes/access.py` — manage ACL rules, SMS/phone allow lists, and policy evaluation.
- `src/api/routes/messages.py` — outbound message dispatch & template sending helpers.
- `src/api/routes/traces.py` — expose stored trace metadata for debugging.
All routes enforce API-key auth via `verify_api_key` (pulls from config).

## Testing Strategy
- Test suite lives under `tests/` with granular module coverage (router integration, channel mentions, ACL policies, CLI behaviour, telemetry).
- `pytest.ini` enables coverage (`--cov=src`), HTML output at `htmlcov/`, strict markers (`asyncio`, `integration`, `slow`), and auto asyncio mode.
- Async tests rely on FastAPI `TestClient` or HTTPX clients; database fixtures respect `TEST_DATABASE_URL` when set.
- Use `make test-postgres` before shipping migrations touching SQL dialect specifics.

## Configuration & Environment
- `.env.example` enumerates all knobs: API host/port/key, logging, tracing, database URLs (SQLite + Postgres), channel credentials, rate limits, and telemetry toggles.
- Key flags:
  - `AUTOMAGIK_OMNI_API_HOST` / `AUTOMAGIK_OMNI_API_PORT` — bind address used by uvicorn and PM2.
  - `AUTOMAGIK_OMNI_DATABASE_URL` — Postgres connection string; leave blank to default to SQLite path `AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH`.
  - `AUTOMAGIK_OMNI_API_KEY` — required header for all `/api/v1/*` endpoints (`x-api-key`).
  - `AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true` — hard-disable remote telemetry collection.
  - `ENVIRONMENT=test` + `TEST_DATABASE_URL` — used by pytest fixtures for isolation.
- Logging configuration supports rotation via `AUTOMAGIK_OMNI_LOG_ROTATION` etc.; see `src/logger.py` for sink wiring.

## Working Tips
- Always create/update tenant wish context under `genie/wishes/` when a task targets a specific feature area.
- When touching channel handlers, rerun `tests/test_omni_handlers.py`, `tests/test_mentions_integration.py`, and the relevant CLI tests to avoid regressions.
- For PM2 or Discord bot changes, keep `ecosystem.config.js` and `scripts/wait_for_api.py` in sync with any new env requirements.

Automagik Omni is multi-tenant and multi-channel—always think about tenant isolation, message tracing, and agent routing whenever you modify APIs or services.
