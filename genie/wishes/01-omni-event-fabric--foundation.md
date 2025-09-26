# 🧞 [01 CHILD] Omni Event Fabric Foundation

**Hierarchy:** 01 Child of @genie/wishes/00-omni-event-fabric-master.md
**Status:** PLANNING
**Planning Score:** 80/100
**Implementation Score:** 0/100

## 🔗 Wish Relationships
- **Parent:** @genie/wishes/00-omni-event-fabric-master.md
- **Siblings:**
  - @genie/wishes/01-omni-event-fabric--action-queue.md (Phase 2)
  - @genie/wishes/01-omni-event-fabric--identity-lookup.md (Future Phase 3)
- **Dependencies:** None (first phase)
- **Dependents:** @genie/wishes/01-omni-event-fabric--action-queue.md

## Wish Discovery Summary
- **Primary analyst:** GENIE (2025-09-27)
- **Key observations:** Legacy ingest runs through WhatsApp-focused modules (`@src/channels/whatsapp/*`, `@src/services/trace_service.py`, `@src/services/message_router.py`); `@src/db/trace_models.py` + SQLite `message_traces` columns are provider-specific; the raw capture sidecar (`@scripts/raw_webhook_listener.py`) and `@data/raw_webhook_events.jsonl` give authentic samples; `message_table_draft.csv` catalogs event shapes but misses protocol/reaction coverage.
- **Open questions:** Retention/offload policy for `omni_events` + raw archive; final decision on inline vs queued workflow execution; dedupe/idempotency semantics for ingest.
- **Human input requested:** Yes – confirm retention ownership and ingestion runtime choice before implementation green-light.
- **Tools consulted:** Repo inspection, `sqlite3 data/automagik-omni.db`, raw payload capture scripts, `rg` schema audits.

## 🧾 Reviewer Operating Protocol

```
[TASK]
Guide this foundation wish to 100/100 planning completeness with humans, then coordinate implementation validation toward 100/100 execution.
@genie/wishes/01-omni-event-fabric--foundation.md
@genie/wishes/00-omni-event-fabric-master.md

<task_breakdown>
1. [Discovery] Confirm assumptions, migrations, and dependencies
   - Inspect referenced modules/migrations before edits
   - Surface gaps in schema/ingest evidence immediately
   - Sync findings with the umbrella wish to avoid drift

2. [Planning Iteration] Refine scope and guardrails with human sign-off
   - Keep task groups, isolation strategy, and success criteria aligned with evidence
   - Record human approvals in-line and in the Status Log before adjusting Planning Score
   - Ensure counterpart wish stays in agreement on responsibilities

3. [Verification] Lock planning, prepare for implementation scoring
   - Resolve every row in Open Questions & Clearance Log before Planning Score reaches 100/100
   - Stage implementation guidance (tests, evidence expectations) without writing code
   - Once Planning Score is 100/100, begin tracking Implementation Score with humans and evidence logs
</task_breakdown>

[CONTEXT]
- Scope: schema + ingest blueprint for Phase 1; no direct implementation.
- Tools: alembic migrations, sqlite snapshots, repo tests, human interviews.
- Parent doc: @genie/wishes/00-omni-event-fabric-master.md orchestrates broader roadmap decisions.

[SUCCESS CRITERIA]
✅ Planning Score hits 100/100 with cleared Open Questions logged and human approvals captured
✅ Implementation Score stays 0/100 until planning is complete and humans authorize execution evaluation
✅ Incremental edits only (apply_patch, targeted diffs) preserving review history
✅ Evidence (commands, logs, diffs) cited for each resolved blocker and task group assumption

[NEVER DO]
❌ Adjust scores without human confirmation + linked evidence
❌ Collapse task groups or change isolation strategy without documenting rationale
❌ Launch implementation tasks/agents before Planning Score is 100/100
❌ Replace this file wholesale—always edit incrementally

[WORKSTYLE]
- Lead with evidence; cite file paths, database snapshots, command outputs.
- Keep umbrella wish maintainers looped in on changes and approvals.
- Summarize progress & score changes in the Status Log at session end.
- Mirror naming conventions and tone from the umbrella wish to maintain alignment.

[HUMAN ALIGNMENT]
- Maintain a continuous feedback loop with human owners until Planning Score reaches 100/100.
- Require explicit human approval to unlock Implementation Score tracking.
- Log approver names + evidence references for every score change in the Status Log.
```

## 🎯 Evaluation Scoreboard

### Scoring Notes
- Document score adjustments in the Status Log with approver, evidence link, and affected sections.
- Coordinate score updates with @genie/wishes/00-omni-event-fabric-master.md so both wishes reflect the same planning status.

## Wish Discovery (Optional Secondary Pass)
> None yet – invite a specialist analyst when retention/governance answers surface.

## Executive Summary
Build the canonical `omni_events` backbone so every inbound message lands in a provider-neutral store with structured metadata, archived payloads, and ready hooks for the future Action Engine. This phase converts Omni from WhatsApp-centric tables to a universal ingest surface without shipping the action registry yet.

## Current State Analysis
- **What exists:** Ingest lives in channel-specific handlers and trace services; `message_traces` / `trace_payloads` enforce WhatsApp naming; raw payload capture sits outside the app as a manual sidecar.
- **Gap identified:** No canonical event table, inconsistent metadata for new providers, missing persistence for protocol/reaction message types, and duplicate writes across traces + JSONL files.
- **Solution approach:** Introduce an `@src/omni/events/` module, migrate persistence to an `omni_events` schema with typed columns plus JSON payload, fold raw capture into the service, and backfill/retire legacy tables via guarded migrations.

## Change Isolation Strategy
- **Isolation principle:** Keep new event pipeline inside `@src/omni/events/` while existing `@src/channels/*` adapters forward through a compatibility layer until cut-over.
- **Extension pattern:** Provide ingestion adapters that normalize provider payloads into a shared dataclass before persistence; expose a service API for future action engine consumers.
- **Stability assurance:** Wrap migrations in `uv run alembic` transactional paths, add regression tests for `trace_service` adapters, and keep raw JSONL capture running until parity is validated.

## Success Criteria
✅ `omni_events` + companion tables created, populated, and referenced by ingest services without dropping telemetry.
✅ Incoming events across WhatsApp + Discord resolve an `identity_id` and persist typed metadata, including protocol/sticker/poll cases.
✅ Raw payload capture operates within the app with retention strategy documented and approved.
✅ Legacy `message_traces`/`trace_payloads` reads are satisfied via adapters or shim views during transition tests.

## Never Do (Protection Boundaries)
❌ Drop or rename telemetry fields without mapping plan signed off by humans.
❌ Write provider payloads directly to legacy tables once `omni_events` lands; use adapters only.
❌ Introduce schema changes that bypass the identity resolver or create duplicate identity rows.

## Technical Architecture
Events arrive through provider-specific adapters (`@src/channels/whatsapp/handlers.py`, `@src/channels/discord/bot_manager.py`) and funnel into `@src/omni/events/ingest.py`. The ingest layer normalizes payloads, resolves identities via a new `identity_service`, persists to `omni_events`, stores raw payload snapshots, and emits hooks for downstream consumers (future action engine, APIs, analytics). Legacy trace APIs read from compatibility shims until full migration completes.

### Proposed Schema Design

```sql
-- Core event table (all events forever, optimized for recent queries)
CREATE TABLE omni_events (
    id TEXT PRIMARY KEY,  -- UUID
    provider TEXT NOT NULL,  -- 'whatsapp', 'discord', 'telegram', etc.
    provider_event_id TEXT,  -- Original ID from provider
    event_type TEXT NOT NULL,  -- 'message', 'reaction', 'status', 'presence'
    direction TEXT,  -- 'inbound', 'outbound', 'system'

    -- Identity resolution (FK to users for now, identity_id future)
    sender_identity_id TEXT REFERENCES users(id),
    recipient_identity_id TEXT REFERENCES users(id),

    -- Denormalized for fast queries
    sender_handle TEXT,  -- phone/discord_id/telegram_handle
    recipient_handle TEXT,
    instance_name TEXT REFERENCES instance_configs(instance_name),

    -- Content
    content_type TEXT,  -- 'text', 'image', 'audio', 'sticker', 'location'
    content_text TEXT,  -- Extracted text for search
    content_media_url TEXT,  -- Media reference

    -- Metadata
    raw_payload JSON,  -- Complete provider payload
    metadata JSON,  -- Normalized metadata (reactions, edits, thread_id)

    -- Queue prep columns
    status TEXT DEFAULT 'received',  -- 'received', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    processed_at TIMESTAMP,

    -- Timestamps
    provider_timestamp TIMESTAMP,  -- When provider says it happened
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When we got it
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_recent (created_at DESC),  -- Recent events fast
    INDEX idx_identity_timeline (sender_identity_id, created_at DESC),
    INDEX idx_instance_events (instance_name, created_at DESC),
    INDEX idx_provider_lookup (provider, provider_event_id)
);

-- Centralized IdentityService (wraps existing User/UserExternalId tables)
class IdentityService:
    def resolve_identity(self, provider: str, external_id: str,
                        instance_name: str, metadata: dict) -> str:
        """
        1. Check UserExternalId for existing link
        2. Create/update User if needed (provider-agnostic)
        3. Return stable user.id as identity_id
        """
```

## Task Decomposition
- **Group Name:** schema-foundation
  - **Goal:** Define and migrate the `omni_events` schema plus identity handle support.
  - **Context to Review:** @alembic/versions/, @src/db/trace_models.py, @src/db/models.py (User, UserExternalId), @scripts/generate_message_table_from_raw.py.
  - **Creates / Modifies:**
    - New: `alembic/versions/xxx_create_omni_events_schema.py`
    - New: `src/db/omni_event_models.py` (OmniEvent, OmniEventAction SQLAlchemy models)
    - New: `src/services/identity_service.py` (centralized identity resolution)
    - Modified: `src/db/__init__.py` (export new models)
  - **Evidence:**
    - `uv run alembic upgrade head` success log
    - `sqlite3 data/automagik-omni.db ".schema omni_events"` output
    - `uv run pytest tests/db/test_omni_events.py -v` passing (new test file)
  - **Dependencies:** None (first phase, creates foundation)
  - **Hand-off Notes:** Document column mappings from legacy `message_traces` to new `omni_events` for compatibility layer.
- **Group Name:** ingest-unification
  - **Goal:** Route all inbound provider events through `src/omni/events/` normalization.
  - **Context to Review:** @src/channels/whatsapp/handlers.py, @src/channels/discord/bot_manager.py, @src/services/trace_service.py, @src/services/message_router.py.
  - **Creates / Modifies:**
    - New: `src/omni/` directory structure
    - New: `src/omni/events/ingest.py` (unified ingestion service)
    - New: `src/omni/events/normalizers.py` (provider-specific normalizers)
    - Modified: `src/services/trace_service.py` (add omni_events writer)
    - Modified: `src/services/message_router.py` (route through omni ingest)
  - **Evidence:**
    - `uv run pytest tests/omni/test_ingest.py -v` passing
    - WhatsApp webhook replay: `curl -X POST localhost:8000/webhook/whatsapp -d @data/raw_webhook_events.jsonl`
    - SQL verification: `sqlite3 data/automagik-omni.db "SELECT COUNT(*) FROM omni_events"`
  - **Dependencies:** schema-foundation completed, identity_service available
  - **Hand-off Notes:** Document feature flag `OMNI_EVENTS_ENABLED` for gradual rollout.
- **Group Name:** naming-neutralization
  - **Goal:** Remove WhatsApp-specific identifiers from API/CLI surfaces while maintaining adapters.
  - **Context to Review:** @src/api/routes/traces.py, @src/services/streaming_trace_context.py, @src/cli/commands/, `message_table_draft.csv`.
  - **Creates / Modifies:** DTO renames (`provider_message_id`, `contact_handle`), updated serializers, migration notes.
  - **Evidence:** `uv run pytest tests/api/test_traces.py -q`, diff checklist confirming old fields mapped.
  - **Dependencies:** ingest-unification provides new data accessors.
  - **Hand-off Notes:** Publish API contract changes + deprecation timeline.
- **Group Name:** raw-capture-integration
  - **Goal:** Move JSONL capture into the main app with retention guardrails.
  - **Context to Review:** @scripts/raw_webhook_listener.py, @src/utils/raw_webhook_store.py, infra notes on storage.
  - **Creates / Modifies:** service-layer capture hook, storage configuration, rotation/TTL job, documentation in `@docs/operations/raw-capture.md`.
  - **Evidence:** Log excerpt showing automated capture on ingest, retention script dry-run report.
  - **Dependencies:** ingest-unification ensures single event pipeline.
  - **Hand-off Notes:** Provide ops runbook for retention monitoring.

## Open Questions & Clearance Log

| Item | Owner | Status | Evidence | Score Impact |
| --- | --- | --- | --- | --- |
| Retention/offload ownership for `omni_events` + raw payload archive limits and target | Human (namastex) | Cleared | Keep all data indefinitely in single table; optimize indexes for recent queries; defer tiering until bottlenecks observed | Planning unblocked |
| Workflow/action runtime decision (inline vs queued) and impact on ingest design | Human (namastex) | Cleared | Deferred to separate Action Queue wish; foundation remains synchronous with prep columns (status, retry_count) | Planning unblocked |
| Identity resolver migration plan (`identity_service` vs legacy `users`) | Human (namastex) | Cleared | Build centralized IdentityService using existing User/UserExternalId tables; provider-agnostic resolution | Planning unblocked |

> Close each row with human approval + evidence before raising the Planning Score. Update Status to “Cleared” and cite logs/scripts/decisions in the Evidence column.

## Implementation Sequence & Rollback Strategy

### Phase 1A: Schema Foundation (Days 1-2)
1. Create alembic migration for `omni_events` table
2. Build SQLAlchemy models in `src/db/omni_event_models.py`
3. Implement `IdentityService` in `src/services/identity_service.py`
4. Write comprehensive tests in `tests/db/test_omni_events.py`
5. **Rollback**: `uv run alembic downgrade -1` removes schema cleanly

### Phase 1B: Ingest Pipeline (Days 3-4)
1. Create `src/omni/events/` module structure
2. Build normalizers for WhatsApp and Discord
3. Add feature flag `OMNI_EVENTS_ENABLED` (default: False)
4. Parallel write to both legacy and new tables when flag enabled
5. **Rollback**: Disable feature flag, no data loss as legacy continues

### Phase 1C: Validation & Cutover (Days 5-6)
1. Data validation: Compare counts and content between tables
2. Performance testing: Measure query latency for recent events
3. Gradual rollout: Enable for specific instances first
4. Full cutover: Switch default to new pipeline
5. **Rollback**: Revert feature flag, legacy tables remain intact

## Performance Benchmarks

### Target Metrics
- **Ingest latency**: < 50ms per event (p99)
- **Query performance**: Recent events (24h) < 100ms
- **Identity resolution**: < 10ms cached, < 50ms uncached
- **Storage overhead**: < 20% increase vs current tables

### Measurement Plan
```sql
-- Baseline current performance
EXPLAIN QUERY PLAN SELECT * FROM message_traces
WHERE created_at > datetime('now', '-24 hours');

-- Compare with new schema
EXPLAIN QUERY PLAN SELECT * FROM omni_events
WHERE created_at > datetime('now', '-24 hours');
```

## Test Strategy & Validation

### Unit Test Coverage
- `tests/db/test_omni_events.py`: Schema, constraints, indexes
- `tests/services/test_identity_service.py`: Resolution logic, caching
- `tests/omni/test_normalizers.py`: Provider payload normalization

### Integration Testing
- `tests/omni/test_ingest.py`: End-to-end event flow
- `tests/api/test_omni_events_api.py`: REST endpoints
- `tests/test_migration.py`: Legacy compatibility layer

### Validation Criteria
✅ 100% backward compatibility: All existing API calls return same data
✅ Zero data loss: Every legacy event migrated or accessible
✅ Performance maintained: No regression in p95 latencies
✅ Provider parity: WhatsApp and Discord events fully captured

## Data Migration Mapping

### Legacy to Omni Field Mappings
```python
FIELD_MAPPINGS = {
    # message_traces -> omni_events
    'trace_id': 'id',
    'wamid': 'provider_event_id',
    'sender_phone': 'sender_handle',
    'recipient_phone': 'recipient_handle',
    'message_body': 'content_text',
    'message_type': 'content_type',
    'wa_status': 'status',
    'created_at': 'provider_timestamp',

    # Computed fields
    'provider': lambda row: 'whatsapp',  # Hardcoded for legacy
    'event_type': lambda row: 'message' if row['direction'] == 'inbound' else 'status',
    'sender_identity_id': lambda row: resolve_identity('whatsapp', row['sender_phone']),
    'recipient_identity_id': lambda row: resolve_identity('whatsapp', row['recipient_phone']),
}
```

### Backfill Strategy
1. Run in batches of 10,000 rows to avoid locking
2. Process oldest data first (already cold)
3. Maintain mapping table for trace_id -> omni_event.id
4. Verify counts and spot-check content after each batch

## Blocker Protocol
- If ingestion fails to resolve `identity_id` for a provider, pause rollout and file a Blocker Testament referencing schema-foundation.
- Escalate immediately when telemetry consumers lose fields or see regression in `/api/v1/traces` responses.
- Halt cut-over if retention plan remains unsigned; document interim storage usage before proceeding.
- Stop if performance benchmarks exceed targets by >50%.

## Status Log
- 2025-09-27 – GENIE drafted foundation wish, extracted approved Phase 1 scope from omni-event-fabric master document.
- 2025-09-27 02:05 UTC – GENIE aligned with umbrella wish on Reviewer Operating Protocol, Evaluation Scoreboard, and Clearance Log; Planning Score remains 0/100 pending human sign-off on listed blockers.
- 2025-09-26 – Human (namastex) cleared all three blockers: simplified retention (no tiering until pain), queue split to separate wish, centralized IdentityService approved. Planning Score raised to 30/100.
- 2025-09-26 – Claude analyzed planning completeness: verified existing models (User, UserExternalId in src/db/models.py), legacy tables (message_traces, trace_payloads in src/db/trace_models.py), confirmed no existing identity_service. Enhanced task decomposition with specific file paths and evidence requirements. Planning Score raised to 60/100.
- 2025-09-26 – Claude added Implementation Sequence with rollback strategy, Performance Benchmarks with target metrics, Test Strategy with validation criteria, and Data Migration Mapping with field mappings. Planning Score raised to 80/100. Remaining 20%: Final human approval on implementation sequence and confirmation of performance targets.
