# Automagik Omni Tech Stack

## Languages

- **Python** – 3.12+ – Primary language for API, channel handlers, and agent integration
- **Shell/Bash** – Scripts for deployment automation and development tooling

## Core Dependencies

### Backend Framework
- **FastAPI** – 0.104.0+ – Modern, async web framework for high-performance API
- **Uvicorn** – 0.23.2+ – ASGI server for production deployment
- **Pydantic** – 2.10.6+ – Data validation and settings management
- **SQLAlchemy** – 2.0.38+ – ORM for database interactions
- **Alembic** – 1.16.2+ – Database migration management

### Database
- **PostgreSQL** – Primary database for production (multi-tenant, ACID guarantees)
- **SQLite** – Development database (quick setup, zero configuration)
- **psycopg2-binary** – 2.9.10+ – PostgreSQL adapter

### Messaging Integration
- **Evolution API** – WhatsApp Business API integration (self-hosted)
- **Discord.py** – 2.4.0+ – Discord bot framework with voice support
- **httpx** – 0.28.0+ – Async HTTP client for external API calls
- **requests** – 2.32.3+ – Synchronous HTTP for simple operations

### Agent Integration
- **Automagik Hive** – v0.1.1b2+ – Agent orchestration backend (self-hosted)
  - **Supported Versions:** v0.1.1b2 and later
  - **Breaking Change:** v0.1.1b2 removed `/playground` prefix from all endpoints
  - **Compatibility:** Hive v0.1.0 and earlier are NOT supported (use Omni v0.5.0 or earlier)
  - **API Endpoints:**
    - Agent runs: `POST /agents/{agent_id}/runs`
    - Team runs: `POST /teams/{team_id}/runs`
    - Continue conversation: `POST /agents/{agent_id}/runs/{run_id}/continue`
  - **Authentication:** Bearer token (X-API-Key header)
  - **Response Format:** Server-Sent Events (SSE) for streaming responses

### CLI & User Experience
- **Typer** – 0.16.0+ – CLI framework with beautiful help messages
- **Rich** – 14.0.0+ – Terminal formatting and progress indicators

### Testing & Quality
- **pytest** – 8.0.0+ – Test framework
- **pytest-asyncio** – 0.21.0+ – Async test support
- **pytest-cov** – 4.0.0+ – Code coverage reporting
- **Black** – 25.1.0+ – Code formatting
- **Ruff** – 0.12.0+ – Fast Python linter
- **mypy** – 1.16.1+ – Static type checking

### Optional Dependencies
- **Discord Voice** – PyNaCl, aiohttp, FFmpeg-python (voice channel support)
- **Discord AI** – OpenAI SDK, SpeechRecognition (voice transcription)

## Development Tools

- **Package Manager:** `uv` (ultra-fast Python package manager) or `pip`
- **Linter/Formatter:** `ruff` (linting), `black` (formatting)
- **Type Checker:** `mypy`
- **Test Framework:** `pytest` with async support
- **Build Tool:** `setuptools` (standard Python packaging)
- **Task Runner:** `make` (Makefile with comprehensive commands)

## Validation Commands

```bash
# Type checking
make typecheck
# or: mypy src

# Linting
make lint
# or: ruff check src

# Code formatting
make format
# or: black src && ruff format src

# Tests (all)
make test
# or: pytest

# Tests (with coverage)
make test-coverage
# or: pytest --cov=src --cov-report=html

# Full check (lint + type + test)
make check
```

## Build & Deployment Commands

```bash
# Install dependencies
make install
# or: uv pip install -e ".[dev]"

# Database migrations
make migrate
# or: alembic upgrade head

# Start development server (hot reload)
make dev
# or: uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8882

# Start production server
make prod
# or: python -m src.api.app

# View logs
make logs
# or: tail -f logs/omnihub.log

# Clean build artifacts
make clean
```

## Environment Requirements

- **Python:** 3.12+ (3.11+ supported)
- **PostgreSQL:** 15+ (optional, for production)
- **Docker:** 20.10+ (optional, for containerized deployment)
- **Node/npm:** Not required (Python-only project)
- **Evolution API:** Latest stable (for WhatsApp integration)
- **Automagik Hive:** v0.1.1b2+ (for agent orchestration)
- **FFmpeg:** Latest (optional, for Discord voice features)

## Architecture Overview

### API Layer
- FastAPI application (`src/api/app.py`)
- Routes organized by domain (`src/api/routes/`)
- Pydantic schemas for validation (`src/api/schemas/`)
- Dependency injection for database sessions (`src/api/deps.py`)

### Channel Handlers
- Base handler interface (`src/channels/base.py`)
- WhatsApp handler with Evolution API client (`src/channels/whatsapp/`)
- Discord handler with bot manager (`src/channels/discord/`)
- Pluggable architecture for new channels

### Services Layer
- Agent service for AI integration (`src/services/agent_service.py`)
- Trace service for message lifecycle tracking (`src/services/trace_service.py`)
- Instance management (`src/services/instance_management.py`)
- Access control (`src/services/access_control.py`)

### Database Layer
- SQLAlchemy models (`src/db/models.py`, `src/db/trace_models.py`)
- Alembic migrations (`alembic/versions/`)
- Database session management (`src/db/database.py`)

### MCP Server
- Instance management tools
- Message sending tools
- Trace analytics tools
- Profile management tools

## Configuration

### Environment Variables (`.env`)
```bash
# Core API
AUTOMAGIK_OMNI_API_HOST=0.0.0.0
AUTOMAGIK_OMNI_API_PORT=8882
AUTOMAGIK_OMNI_API_KEY=your-secret-key

# Database
AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH=./data/automagik-omni.db
# or: AUTOMAGIK_OMNI_DATABASE_URL=postgresql://user:pass@localhost/omni

# Logging
LOG_LEVEL=INFO
LOG_FOLDER=./logs
AUTOMAGIK_TIMEZONE=UTC

# Tracing
AUTOMAGIK_OMNI_ENABLE_TRACING=true
AUTOMAGIK_OMNI_TRACE_RETENTION_DAYS=30
```

---

**Note:** This stack prioritizes developer experience, type safety, and production reliability. All core dependencies are battle-tested and well-maintained.
