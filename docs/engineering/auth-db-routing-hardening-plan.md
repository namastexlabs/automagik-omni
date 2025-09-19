# Auth, DB DI, and Routing Hardening Plan

## Objectives
- Eliminate hidden 404/401s by making router failures explicit and auth predictable in tests.
- Ensure all endpoint code paths use FastAPI dependency injection (DI) for DB access.
- Reduce global import-time side effects that bypass test overrides.
- Normalize routing and improve observability of startup health.

## Problems Observed
- Hidden router import failures cause silent 404s (catch-all around `messages_router`).
- Direct DB access (`SessionLocal()` / `next(get_db())`) bypasses DI and test overrides.
- Auth coupled to API key env; tests expect dev/test mode to bypass, leading to 401s.
- Eager global initialization (config/engine) at import time makes tests brittle.
- Inconsistent route prefixes for message endpoints (`/api/v1/instance` vs `/api/v1/instances`).

## Guiding Principles
- All request paths must use DI (`db: Session = Depends(get_database)`).
- Fail fast on router init errors in non-test environments; surface loudly in logs.
- Test mode must be explicit and predictable (`ENVIRONMENT=test`).
- Prefer late-binding of env/config for testability; avoid module-level DB work in request paths.

## Work Plan

### Phase 1 — Quick, Low-Risk Fixes
1) Auth: explicit test-mode bypass
   - Change `src/api/deps.verify_api_key` to short‑circuit when `ENVIRONMENT=="test"`.
   - Keep existing behavior when `AUTOMAGIK_OMNI_API_KEY` is empty (dev mode).
   - Acceptance: omni auth tests pass without x-api-key; invalid/missing headers don’t 401 in tests.

2) Router inclusion: fail fast and log clearly
   - Remove catch‑all `try/except` around `messages_router` in `src/api/app.py`.
   - If inclusion fails in non-test env, raise; in test env, log error with traceback.
   - Acceptance: if router import breaks, startup logs a clear error and tests surface it (no silent 404s).

3) Optional: honor `TEST_DATABASE_URL`
   - Update `src/db/database.get_database_url()` to prefer `TEST_DATABASE_URL` when set.
   - Document in `tests/README.md`; fixture can set it if needed.
   - Acceptance: local test runs can force a specific DB URL when debugging.

### Phase 2 — DI Refactor (DB session handling)
1) Trace service: remove implicit DB opens
   - `src/services/trace_service.get_trace_context`: accept `db: Session` (or add a new helper `get_trace_context_with_db(db)`), avoid `next(get_db())` inside.
   - `TraceService.cleanup_old_traces`: require `db_session` param; remove default `next(get_db())` fallback.
   - Update all call sites: `src/api/app._handle_evolution_webhook` and any services to pass the request‑scoped `db`.

2) Audit and remove `SessionLocal()` usage in request code paths
   - Search for `SessionLocal(` and `next(get_db())`:
     - `src/services/discord_service.py` (background/CLI). Prefer receiving a session from caller; if not feasible, keep but ensure not used by HTTP request paths.
     - Any other service used by routes must accept `db: Session`.
   - Acceptance: running tests shows all DB access originates from DI sessions.

3) Keep discovery/bootstrapping test-safe
   - Discovery in `app.lifespan` already skipped in `ENVIRONMENT=test`; retain that behavior.

### Phase 3 — Routing Normalization
1) Add plural aliases for messages
   - Keep existing `/api/v1/instance/{instance_name}/...` for backward compatibility.
   - Add aliased routes under `/api/v1/instances/{instance_name}/...` for: send-text, send-media, send-audio, send-contact, send-reaction, fetch-profile.
   - Update docs and mark singular form as deprecated.
   - Acceptance: both prefixes work; future tests/docs use plural form.

### Phase 4 — Hardening & Observability
1) Startup self-check
   - On startup, log included routers and route counts; in non-test env, warn if critical routers are missing (instances, messages, traces, omni).
   - Acceptance: startup logs clearly indicate router registration state.

2) CI guardrails
   - Add a lightweight test job (or marker) that hits key endpoints to ensure router registration/auth modes behave as expected.

## Acceptance Criteria (tests that must pass)
- E2E instance management, message sending, webhook, omni, and session filtering tests report 200/expected codes (no 404/401 surprises).
- Specific suites impacted:
  - `tests/test_api_endpoints_e2e.py` (instance CRUD, message ops, webhook, request validation)
  - `tests/test_omni_endpoints.py` (auth expectations in dev/test)
  - `tests/test_session_filtering.py` and `tests/test_session_filtering_integration.py` (trace filtering)

## Risks & Mitigations
- Changing `verify_api_key` behavior: constrain bypass to `ENVIRONMENT=test` only.
- DI refactor touches multiple call sites: stage behind feature branches and run full test suite.
- Adding alias routes: avoid breaking existing clients by keeping old paths until next minor version.

## Rollout Steps
1. Implement Phase 1, run affected tests (omni + messages + instances).
2. Implement Phase 2 incrementally (trace service first), run trace/session tests.
3. Add alias routes (Phase 3), update docs.
4. Add startup self-check logging (Phase 4) and CI markers.

## Effort Estimate
- Phase 1: ~1–2 hrs
- Phase 2: ~3–5 hrs (depending on call-site breadth)
- Phase 3: ~1 hr
- Phase 4: ~1 hr

