# Death Testament — automagik-omni-coder • DB Migration Sequencing (2025-09-25T14:37Z)

## Scope
- Reordered FastAPI lifespan startup so Alembic migrations gate the application before any table-side effects or configuration logging.
- Hardened migration utilities to replace the invalid `ScriptDirectory.iterate_revisions("heads")` call, support merge detection, and stamp databases automatically when schema diffs already exist.
- Authored merge revision `42a0f0c8f9f1` to reconcile `83e35a661e81` (user external IDs) and `c7a94f4da889` (access rules) branches.

## Files Touched
- `src/api/app.py`
- `src/db/database.py`
- `src/db/__init__.py`
- `src/db/migrations.py`
- `alembic/versions/42a0f0c8f9f1_merge_access_rules_and_user_ids.py`
- `tests/api/test_app_startup.py`
- `tests/db/test_migrations.py`

## Command Log
1. `uv run pytest tests/api/test_app_startup.py` *(RED — sequencing + fail-fast assertions failing, tables run before migrations, context completed despite migration failure)*
2. `uv run pytest tests/db/test_migrations.py` *(RED — reported dual heads `['83e35a661e81', 'c7a94f4da889']`)*
3. `uv run pytest tests/api/test_app_startup.py` *(GREEN after sequencing reorder)*
4. `uv run pytest tests/db/test_migrations.py` *(GREEN after merge revision addition + idempotent stamp fallback)*
5. `uv run pytest tests/api/test_app_startup.py tests/db/test_migrations.py` *(Combined GREEN confirmation)*
6. `uv run alembic heads` *(Now reports single head `42a0f0c8f9f1`)*
7. `uv run python -c "from src.db.migrations import get_head_revision; print(get_head_revision())"` *(Output `42a0f0c8f9f1`, no TypeError)*
8. `uv run python - <<'PY' ... auto_migrate` *(Outputs `auto_migrate -> True`, proving fallback handles pre-applied schema)*
9. `uv run python - <<'PY' ... lifespan` *(Shows migrations logging before configuration output and full startup success)*
10. `uv run python - <<'PY' ... lifespan` *(Post-refactor verification that migrations now precede channel registration and config logs without external helpers)*

## Implementation Notes
- Lifespan now raises `RuntimeError` when migrations fail, preventing API exposure under schema drift.
- `create_tables()` executes only after successful migrations; failure still logs but remains non-fatal per existing behaviour, and configuration logging now occurs post-migration.
- Added `_find_merge_revision()` helper using `ScriptDirectory.walk_revisions()` to inspect merge points without missing `lower` argument, returning deterministic merge IDs for both current revision discovery and script head evaluation.
- Added `_is_idempotent_schema_error()` so OperationalError messages like “already exists” trigger `stamp_database('head')`, ensuring legacy branches converge without manual intervention.
- Introduced lazy engine/session initialisation (`src/db/database.py`) and early module-level migration gating (`_ensure_database_ready()` in `src/api/app.py`), so migrations execute—and can fail fast—before any channel registration or configuration logs.
- Merge revision introduces no schema change; downgrade prohibited to avoid reintroducing divergent heads.

## Risks & Follow-Ups
- If future deployments require optional “start in read-only mode” when migrations fail, introduce configuration flag before relaxing the hard failure.
- Recommend running a full migration dry-run against staging data to ensure merge revision orders revisions as expected (should be no-ops but worth confirmation).
- Coordinate with release to stamp databases already carrying both branch revisions; new merge ensures upgrades converge on `42a0f0c8f9f1` cleanly.

## Validation Artifacts
- Test outputs referenced above (RED→GREEN) stored in command history (see command log).
- Alembic head output captured post-fix showing single head.

## Human Handoff
- Please review whether startup should convert the `RuntimeError` into a maintenance-mode toggle for operators.
- Validate Alembic history on production snapshot before applying merge to ensure no out-of-band revisions exist.
