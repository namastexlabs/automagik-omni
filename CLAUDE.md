# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working with the Automagik Omni repository.

## Context & Scope

[CONTEXT]
- Root playbook for Automagik Omni. Review this before touching code, then consult topic-specific docs under `docs/` or within `genie/` wishes.
- Automagik Omni is a multi-tenant messaging hub orchestrating WhatsApp, Discord, and future channels through a FastAPI service, background services, and channel-specific handlers.
- Code spans API routes (`src/api`), channel adapters (`src/channels`), orchestration services (`src/services`), CLI entry points (`src/cli`), and SQLAlchemy models (`src/db`).

[SUCCESS CRITERIA]
✅ Behavioral learnings applied before execution; deviations escalated through `automagik-omni-self-learn`.
✅ Changes keep Omni’s multi-tenant channels functional (WhatsApp + Discord today, guardrails for future channels).
✅ Tooling, tests, and documentation reflect Automagik Omni realities—no Hive-era residues in new work.
✅ Evidence (commands, logs, screenshots) captured in wish/Forge artefacts and referenced in Death Testaments.

[NEVER DO]
❌ Assume behavior from the former Hive codebase—validate against Omni modules instead.
❌ Touch documentation or wish files unless explicitly tasked.
❌ Run tooling outside `uv` wrappers or bypass sandbox/approval requirements.
❌ Declare completion without RED→GREEN proof and recorded validation.

## Task Decomposition

```
<task_breakdown>
1. [Discovery]
   - Load the current wish/Forge task plus supporting docs listed above.
   - Inspect relevant Omni modules (`src/api`, `src/channels`, `src/services`, `src/db`, `tests`).
   - Confirm sandbox + approval requirements, active env vars, and MCP availability.

2. [Implementation]
   - Make smallest-possible changes in existing files; keep changes Omni-focused.
   - Follow TDD: tests first via `automagik-omni-tests`, implementation via `automagik-omni-coder`.
   - Propagate configuration/env/schema updates consistently (code + docs + migrations as needed).

3. [Verification]
   - Run targeted `uv run pytest ...` suites, lint/type checks, and channel API smoke tests.
   - Capture outputs, screenshots, or SQL results as evidence.
   - Summarize in the wish Death Testament before handing back to humans.
</task_breakdown>
```

## Behavioral Learnings

[CONTEXT]
- `automagik-omni-self-learn` owns violation records and overrides inconsistent instructions.
- Read latest entries before work; treat them as highest-priority guardrails.

[SUCCESS CRITERIA]
✅ Most recent entry acknowledged explicitly in planning.
✅ Violations against learnings trigger immediate self-learn escalation with evidence.
✅ Corrections validated via observable behavior (tests, logs, approvals).

[ENTRY FIELDS]
- `date` (YYYY-MM-DD) • `violation_type` • `severity`
- `trigger` • `correction` • `validation`

## Global Guardrails

### Fundamental Rules *(CRITICAL)*
- Do exactly what the wish/Forge task requests—no scope creep.
- Edit existing files when possible; create new files only with explicit approval.
- `.claude/commands/prompt.md` defines interaction style; follow it rigorously.
- Respect naming constraints from `AGENTS.md` (no “fixed”, “v2”, etc.).

### Code Quality Standards
- Favor clear, minimal solutions (KISS/YAGNI/DRY); stick to Pythonic patterns used in `src/`.
- Deliver complete implementations—no TODOs, placeholders, or half-finished code paths.
- Prefer built-in or well-known libs already referenced in `pyproject.toml`.
- Compose behavior via functions/modules; avoid unnecessary inheritance.

### File Organization Principles
- Keep modules under 350 LOC when feasible; factor helpers into `src/utils` only if reused.
- Separate API schemas (`src/api/schemas`), services (`src/services`), and models (`src/db`).
- Keep channel-specific logic inside respective handler modules.
- Maintain import hygiene; no circular dependencies or deep relative imports.

## Critical Behavioral Overrides

### Time Estimation Ban *(CRITICAL)*
- Use phase language (“Phase 1”, “Phase 2”)—never human timelines.
- Time estimates trigger `automagik-omni-self-learn` escalation.

### UV Compliance *(CRITICAL)*
- All Python invocations go through `uv`: `uv run python`, `uv run pytest`, `uv run ruff`, etc.
- Never call `python`, `pytest`, `pip`, or `coverage` directly.
- Enforce UV-first tooling across subagents; escalate violations immediately.

### `pyproject.toml` Protection *(CRITICAL)*
- Treat `pyproject.toml` as read-only; dependency changes use `uv add` commands.
- Any manual edit constitutes a critical violation.

## Workspace & Wish System

[CONTEXT]
- `/genie/` houses wishes, reports, and knowledge; it is the single source of orchestration truth.
- Wishes evolve in place; Death Testaments close the loop with evidence.

[SUCCESS CRITERIA]
✅ Active work captured in `genie/wishes/<slug>.md` with strategy, phases, agents, and evidence log.
✅ `/wish` command drives planning; no duplicate wish docs.
✅ Every wish closure references Death Testament files in `genie/reports/`.

[NEVER DO]
❌ Create `wish-v2` docs or duplicate wish folders.
❌ Start implementation without an approved orchestration strategy.
❌ Skip Death Testament when reporting success or failure.

## Strategic Orchestration

### Genie → Domain → Execution
- Master Genie coordinates specialists; implementation lives with subagents.
- Domain orchestrators delegate via `.claude/agents/` prompts using claude-mcp.
- If automation is unavailable, manually open the `@<agent>` prompt in `.claude/agents/` and follow it verbatim.

### TDD Pipeline *(Always)*
1. RED – `automagik-omni-tests` authors failing tests that describe desired behavior.
2. GREEN – `automagik-omni-coder` implements minimal code to pass.
3. REFACTOR – Clean up once tests are green; keep coverage intact.

### Forge Workflow *(Delegated Execution)*
- Break approved wishes into forge tasks with complete context (`@` references, evidence requirements).
- Secure explicit human approval before calling `forge-master`.
- Each task runs in its own worktree/branch; no commits unless humans ask for them.

## Project Architecture

### Exploration Command
```bash
# Inspect structure without noise
tree src -L 2 -I '__pycache__'
```

### Architecture Map (Automagik Omni)
```
ROOT
├── AGENTS.md                # Orchestration rules (sync with this playbook)
├── CLAUDE.md                # You are here
├── Makefile                 # Common uv/dev shortcuts
├── README.md                # Product overview & setup
├── docs/                    # Architecture, deployment, QA references
├── genie/                   # Wishes, reports, knowledge base (no duplicates)
├── scripts/                 # Operational helpers (migrations, waiters)
├── update-automagik-omni.sh # Environment bootstrap script
└── src/                     # Application source
    ├── api/                 # FastAPI app + routes (`app.py`, `routes/omni.py`, `routes/instances.py`)
    ├── channels/            # Channel handlers & Omni abstractions (WhatsApp, Discord)
    ├── cli/                 # CLI entrypoint (`cli/main.py`) + commands
    ├── commands/            # CLI sub-commands & utilities
    ├── core/                # Telemetry, tracing, instrumentation
    ├── db/                  # SQLAlchemy setup + models (InstanceConfig, User, AccessRule)
    ├── middleware/          # FastAPI middlewares (auth, logging, request context)
    ├── services/            # Business logic (message routing, hive client, transformers)
    ├── utils/               # Shared helpers (datetime, streaming context)
    └── version.py           # Application versioning metadata

Supporting directories:
- `alembic/`               # Database migrations (keep branch history intact)
- `tests/`                 # Pytest suites (API, channels, services, db models)
- `ecosystem.config.js`    # PM2 process manager configuration
- `logs/`                  # Runtime log captures (respect privacy)
- `data/`                  # Local SQLite storage (dev/testing)
```

## Development Methodology

[CONTEXT]
- Automagik Omni changes must maintain multi-tenant stability and channel parity.
- RED→GREEN→REFACTOR is non-negotiable for features and bug fixes.

[SUCCESS CRITERIA]
✅ New tests fail before implementation; they validate Omni-specific behavior.
✅ Implementations satisfy tests with minimal code; refactors keep tests green.
✅ Acceptance criteria mapped to evidence in the wish.

[NEVER DO]
❌ Spawn `automagik-omni-coder` before failing tests exist.
❌ Skip refactor when design smells remain.
❌ Leave orchestration strategy undocumented.

## Tooling & Commands

### UV Workflow
```bash
uv sync                            # Install/sync dependencies
uv run pytest                      # Entire test suite
uv run pytest tests/test_omni_endpoints.py -k contacts  # Focused API tests
uv run pytest tests/test_omni_models.py                # InstanceConfig & model coverage
uv run pytest tests/test_telemetry.py                  # Telemetry toggles
uv run ruff check src tests --fix                     # Lint + auto-fix
uv run mypy src                                        # Type checking
```

### Makefile Shortcuts
- `make dev`      – Launch FastAPI + background services (uvicorn, Discord bot when configured).
- `make stop`     – Graceful shutdown of dev services.
- `make format`   – Ruff format wrapper.
- `make lint`     – Ruff check wrapper.
- `make test`     – Pytest wrapper (uses uv under the hood).

### Evidence Checklist
- Record command output (pytest, curl, scripts) in wish/Forge artefacts.
- Capture screenshots/log excerpts for Omni channel QA when relevant.
- Keep `git status` clean aside from intentional edits before handing off.

## Configuration & Environment

Key environment variables (`src/config.py` + `Makefile`):
- `AUTOMAGIK_OMNI_API_HOST` / `AUTOMAGIK_OMNI_API_PORT` – FastAPI bind host/port.
- `AUTOMAGIK_OMNI_API_KEY` – Required header for `/api/v1/*` endpoints (`x-api-key`).
- `AUTOMAGIK_OMNI_DATABASE_URL` / `AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH` – Database connection; defaults to local SQLite.
- `AUTOMAGIK_OMNI_ENABLE_TRACING` + related `AUTOMAGIK_OMNI_TRACE_*` vars – Telemetry toggles.
- `AUTOMAGIK_OMNI_DISABLE_TELEMETRY` – Explicit opt-out for analytics (honor in CLI logs).
- `LOG_LEVEL`, `LOG_FOLDER` – Logging configuration.
- Channel-specific settings (see `InstanceConfig` fields) set per tenant via DB/API.

Use `update-automagik-omni.sh` or `make dev` to bootstrap `.env`; never hardcode secrets.

## Database & Migrations

- SQLAlchemy models live in `src/db/models.py`; key tables: `instance_configs`, `users`, `access_rules`.
- `alembic/versions/` tracks schema history. Add migrations with Alembic if models change; keep naming consistent.
- Default dev DB is SQLite (`data/automagik-omni.db`). Tests often override via `TEST_DATABASE_URL`.
- When inspecting data, use read-only SQL first (`uv run python - <<'PY' ... PY` or MCP `postgres`).

## Channels & Integrations

- WhatsApp: `src/channels/handlers/whatsapp_chat_handler.py` + Evolution API client.
- Discord: `src/channels/handlers/discord_chat_handler.py` + `src/channels/discord/bot_manager.py`.
- Omni abstractions: `src/channels/omni_base.py` unify pagination/filtering; ensure new channels conform.
- API endpoints: `src/api/routes/omni.py` (contacts, chats) and `src/api/routes/instances.py` (instance CRUD + telemetry).
- Message routing: `src/services/message_router.py` orchestrates Automagik Omni vs legacy Hive API calls.

## Legacy Hive Compatibility

- `src/services/automagik_hive_client.py` and related models preserve backward compatibility. Touch only when required; document risks and ensure Omni paths remain default.
- When removing Hive-era logic, confirm tests and migrations still cover legacy data paths. Coordinate via wish/Forge tasks.

## Logging & Telemetry

- Logging configured via `src/logger.py`; CLI announces telemetry status at startup.
- Tracing managed by `src/core/telemetry.py` with opt-in/out env vars.
- Respect privacy—scrub PII from logs and Death Testaments.

## Testing Playbook

Priority suites:
- `tests/test_omni_endpoints.py` – REST API contract.
- `tests/test_omni_models.py` – InstanceConfig + streaming behaviour.
- `tests/test_omni_handlers.py` – Channel adapters.
- `tests/test_telemetry.py` – Telemetry toggles + CI defaults.
- `tests/test_agent_api_client_hive_detection.py` – Legacy interface.

Run focused tests plus regression suites tied to touched modules. Capture before/after output for TDD traceability.

## Forge Integration Patterns

- Document orchestration plans in `genie/reports/forge-plan-<wish>-<timestamp>.md`.
- One forge task per approved group; include full context, agent assignments, success criteria.
- Complexity ≥7 requires zen tool consultations (`mcp__zen__planner`, `mcp__zen__thinkdeep`, etc.).
- Reference resulting Forge task IDs and Death Testament paths in final responses.

## Verification & Reporting

[SUCCESS CRITERIA]
✅ Every change linked to a wish/Forge plan with evidence.
✅ Tests/commands executed through UV and recorded in Death Testaments.
✅ Behavioral learnings acknowledged; no conflicting guidance remains.
✅ Domain docs updated when root policies shift (and only when asked).

[NEVER DO]
❌ Hand off work without evidence (tests, logs, screenshots).
❌ Modify domain guides without ensuring root + sub-doc alignment.
❌ Ignore failing tests or unresolved warnings—document and escalate.

Stay aligned with this playbook, the active wish strategy, and AGENTS.md. When in doubt, pause, investigate, and ask humans before acting.
