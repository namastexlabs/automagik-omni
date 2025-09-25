# Death Testament — Database Migration Branch Analysis (2025-09-25T14:18Z)

## Scope
- Investigated FastAPI startup sequencing around `create_tables()` and `auto_migrate()`.
- Reviewed Alembic migration utilities and environment configuration.
- Catalogued current migration heads under `alembic/versions/` to explain runtime branching errors.

## Evidence & Commands
- `sed -n` / `nl -ba` inspections of `src/api/app.py`, `src/db/migrations.py`, `alembic/env.py`.
- `ls -1 alembic/versions` to list revision files.
- `date -u +%Y%m%d%H%M` for timestamping.

## Key Findings
1. **Startup sequencing leak** — `create_tables()` executes before the migration gate and exceptions from `auto_migrate()` are downgraded to warnings, letting FastAPI boot while migrations fail (`src/api/app.py:156-179`).
2. **Alembic API misuse** — `ScriptDirectory.iterate_revisions("heads")` is invoked without the required `lower` argument, triggering `TypeError` during startup (`src/db/migrations.py:67-72`, `src/db/migrations.py:101-106`).
3. **Unmerged heads** — Script revisions `83e35a661e81` and `c7a94f4da889` terminate separate branches; no merge revision ties them together, so Alembic reports multiple heads even though a merge template file exists only for older branches.

## Risks & Follow-Ups
- Application may operate against partially migrated schema, risking data integrity.
- Repeated startup failures will persist until iterate call is corrected and branches reconciled.
- Recommend coordinating a new merge revision (post-`83e35a661e81`) and enforcing fail-fast startup semantics once human plan approved.

## Next Steps for Specialists
1. Phase 1 diagnostics: instrument lifespan to capture revision state prior to table creation, confirm head list via `uv run alembic heads`.
2. Phase 2 fix: reorder migration gate ahead of table creation, refactor head discovery to use `script_dir.get_revisions(...)` or `walk_revisions`, and author merge revision resolving `83e35a661e81` + `c7a94f4da889`.
3. Phase 3 validation: run `uv run pytest tests/test_api_endpoints_e2e.py::test_startup_auto_migrate` plus targeted startup smoke via `uv run automagik-omni devserver` (or equivalent) capturing before/after logs and exit codes.

## Human Attention Needed
- Approve sequencing plan before coders modify lifespan or migration utilities.
- Decide desired failure behaviour (hard fail vs. maintenance mode) when migrations fail.
- Provide DB snapshot or staging window for merge migration dry run.
