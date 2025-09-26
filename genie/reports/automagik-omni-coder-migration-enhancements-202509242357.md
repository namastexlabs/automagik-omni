# Automagik Omni Coder — Migration Enhancements (2025-09-24 23:57 UTC)

## Scope & Outcome
- Added server-side timestamp defaults to the original `user_external_ids` creation migration.
- Introduced a new Alembic revision that converts the uniqueness constraint to include `instance_name`.
- Updated the ORM `UserExternalId` model so SQLAlchemy metadata matches the new constraint.

## Files Touched
- alembic/versions/7f3a2b1c9a01_create_user_external_ids_table.py
- alembic/versions/83e35a661e81_add_instance_scoped_uniqueness_to_user_.py
- src/db/models.py

## Command Log
1. `uv run alembic revision -m "add_instance_scoped_uniqueness_to_user_external_ids"`
   - ❌ Failed: multiple heads detected; reran with `--head 7f3a2b1c9a01`.
2. `uv run alembic revision --head 7f3a2b1c9a01 -m "add_instance_scoped_uniqueness_to_user_external_ids"`
   - ✅ Generated new migration `83e35a661e81`.
3. `uv run alembic upgrade head`
   - ❌ Failed because Alembic requires explicit branch selection when multiple heads exist.
4. `uv run alembic upgrade heads`
   - ❌ First attempt hit SQLite constraint alteration limitation; migration updated to use `batch_alter_table`.
5. `uv run alembic upgrade heads`
   - ✅ Applied all migrations after patching batch mode.
6. `uv run alembic downgrade -1`
   - ⚠️ Succeeded with Alembic warning about multiple heads; constraint reverted as expected.
7. `uv run alembic upgrade heads`
   - ✅ Reapplied migrations to latest head.
8. `uv run python -c "from src.db.models import UserExternalId; print('Model loaded successfully')"`
   - ✅ ORM model imports with the updated table args.

## Validation Evidence
- Final `uv run alembic upgrade heads` exited cleanly with the new constraint in place.
- `uv run python ...` confirmed SQLAlchemy metadata loads without errors.

## Risks & Follow-Ups
- Multiple Alembic heads remain; continue using explicit branch targeting to avoid ambiguity.
- SQLite migrations require batch operations for constraint changes—pattern documented in new revision for reuse.
