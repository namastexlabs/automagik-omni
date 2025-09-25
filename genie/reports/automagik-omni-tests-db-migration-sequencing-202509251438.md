# Death Testament — automagik-omni-tests • DB Migration Sequencing (2025-09-25T14:38Z)

## Scope
- Authored regression tests capturing startup sequencing expectations and Alembic head convergence.

## Files Touched
- `tests/api/test_app_startup.py`
- `tests/db/test_migrations.py`

## Test Evidence
1. `uv run pytest tests/api/test_app_startup.py`
   - **RED**: `call_order == ['create_tables', 'auto_migrate']` and context failed to raise, proving migrations ran late and failures were ignored.
2. `uv run pytest tests/db/test_migrations.py`
   - **RED**: Assertion raised with `['83e35a661e81', 'c7a94f4da889']`, documenting the branching head state.
3. `uv run pytest tests/api/test_app_startup.py`
   - **GREEN**: Sequencing test now records `['auto_migrate', 'create_tables']` and failure path raises `RuntimeError` before table creation.
4. `uv run pytest tests/db/test_migrations.py`
   - **GREEN**: Alembic exposes single head `['42a0f0c8f9f1']` and idempotent DDL raises trigger a stamp-to-head fallback.
5. `uv run pytest tests/api/test_app_startup.py tests/db/test_migrations.py`
   - Combined suite confirming both domains remain GREEN together.

## Coverage Notes
- Startup tests stub dependent services to keep focus on ordering semantics; they guarantee migrations execute before table creation and that failure short-circuits startup.
- Migration test enforces a single head, asserts the specific merge revision ID, and confirms OperationalError “already exists” cases stamp the database instead of failing startup.

## Follow-Ups
- Consider extending coverage with a smoke test that boots the ASGI lifespan under `uvicorn` harness whenever we add new migration flows.
- Document in release playbook that any additional Alembic branch requires an accompanying merge revision test adjustment.
