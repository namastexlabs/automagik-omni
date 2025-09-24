# 🧞 Discord Parity Polish WISH

**Status:** READY_FOR_REVIEW

## Executive Summary
Polish Discord-WhatsApp parity implementation to address PR review feedback and achieve production-ready quality.

## Current State Analysis
**What exists:** Discord parity implementation with trace persistence, identity linking, and comprehensive tests
**Gap identified:** Minor issues preventing 100/100 score - accidental test file, migration timestamps, instance-scoped uniqueness, error handling gaps
**Solution approach:** Surgical fixes to address each review concern without disrupting working parity features

## Change Isolation Strategy
- **Isolation principle:** Each fix is independent and can be applied without affecting others
- **Extension pattern:** Enhance existing patterns rather than replacing them
- **Stability assurance:** All existing tests must remain green after changes

## Success Criteria
✅ `test.md` file removed from repository
✅ Migration updated with server-default timestamps
✅ Instance-scoped uniqueness constraint for multi-tenant isolation
✅ Retry logic added to trace persistence operations
✅ Enhanced error handling in Discord bot manager
✅ All existing Discord parity tests remain green
✅ PR achieves 100/100 review score

## Never Do (Protection Boundaries)
❌ Break existing Discord-WhatsApp parity functionality
❌ Modify core parity logic in trace_service or user_service
❌ Change existing migration revision IDs or history
❌ Remove or skip existing test coverage
❌ Introduce new dependencies without approval

## Technical Architecture

### Component Structure
```
Cleanup:
├── test.md                                          # Accidental file to remove
└── .gitignore                                       # Already updated correctly

Migrations:
├── alembic/versions/7f3a2b1c9a01_*.py              # Update with server defaults
└── alembic/versions/new_instance_scoped_unique.py  # New migration for constraint

Services:
├── src/services/trace_service.py                   # Add retry decorator
├── src/channels/discord/bot_manager.py             # Enhance error handling
└── src/db/models.py                                # Update uniqueness constraint

Tests:
└── tests/                                           # Verify all remain green
```

### Naming Conventions
- Migration files: Keep existing timestamp pattern
- Retry decorator: `@retry_on_db_error` following existing patterns
- Error types: Use existing `DatabaseError` from SQLAlchemy

## Task Decomposition

### Dependency Graph
```
A[Quick Fixes] ---> B[Migration Enhancement]
B ---> C[Service Improvements]
C ---> D[Validation]
```

### Group A: Quick Fixes (Parallel Tasks)
Dependencies: None | Execute simultaneously

**A1-remove-test-file**: Remove accidental test.md file
@test.md [context]
Deletes: `test.md`
Success: File no longer in repository

**A2-verify-gitignore**: Confirm .gitignore properly excludes .mcp.json
@.gitignore [context]
Validates: `.mcp.json` entry exists
Success: git status shows .mcp.json as ignored

### Group B: Migration Enhancement (After A)
Dependencies: None

**B1-update-migration-timestamps**: Add server defaults to existing migration
@alembic/versions/7f3a2b1c9a01_create_user_external_ids_table.py [context]
Modifies: Add `server_default=sa.func.now()` to timestamp columns
Success: Migration still applies cleanly

**B2-instance-scoped-constraint**: Create new migration for multi-tenant uniqueness
@src/db/models.py [context]
Creates: New migration file with instance-scoped unique constraint
Modifies: UserExternalId model to reflect new constraint
Success: Multi-tenant isolation enforced at DB level

### Group C: Service Improvements (After B)
Dependencies: B1-update-migration-timestamps, B2-instance-scoped-constraint

**C1-trace-retry-logic**: Add retry decorator to trace persistence
@src/services/trace_service.py [context]
Modifies: Add retry decorator to `create_trace` and `record_outbound_message`
Creates: `@retry_on_db_error` decorator if not exists
Success: Transient DB failures handled gracefully

**C2-discord-error-handling**: Enhance Discord bot manager error handling
@src/channels/discord/bot_manager.py [context]
Modifies: Wrap `resolve_user_by_external` in try/except
Adds: Fallback logic for resolution failures
Success: Discord flow continues even if identity linking fails

### Group D: Validation (After C)
Dependencies: All tasks in A, B, C

**D1-test-regression**: Run full Discord parity test suite
@tests/ [context]
Executes: All Discord-related test files
Success: All tests remain green

**D2-manual-validation**: Verify fixes in local environment
@docs/discord-parity-validation.md [context]
Validates: Each fix works as expected
Success: Manual smoke tests pass

**D3-pr-update**: Update PR with fixes
@.git [context]
Creates: Commit with all fixes
Success: PR review concerns addressed

## Implementation Examples

### Server Default Timestamps Pattern
```python
# alembic/versions/7f3a2b1c9a01_create_user_external_ids_table.py
sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
```

### Retry Decorator Pattern
```python
# src/services/trace_service.py
from functools import wraps
from sqlalchemy.exc import OperationalError
import time

def retry_on_db_error(max_attempts=3, backoff_factor=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(backoff_factor ** attempt)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@retry_on_db_error()
def create_trace(...):
    # existing implementation
```

### Error Handling Pattern
```python
# src/channels/discord/bot_manager.py
try:
    local_user = resolve_user_by_external("discord", str(author.id))
    if local_user:
        message_data["user_id"] = local_user.id
except DatabaseError as e:
    logger.error(f"Failed to resolve Discord user {author.id}: {e}")
    # Continue with message_data["user_id"] = None
```

### Instance-Scoped Uniqueness Pattern
```python
# src/db/models.py
class UserExternalId(Base):
    __tablename__ = "user_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_id", "instance_name",
            name="uq_user_external_provider_instance"
        ),
    )
```

## Testing Protocol
```bash
# Run all Discord parity tests
uv run pytest tests/channels/test_discord_trace_parity.py
uv run pytest tests/test_omni_handlers.py::TestDiscordChatHandler
uv run pytest tests/test_identity_linking.py
uv run pytest tests/channels/discord/test_channel_handler.py
uv run pytest tests/channels/test_message_sender.py

# Verify migration applies
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head

# Manual validation
uv run python -c "from src.services.trace_service import create_trace; print('Retry decorator works')"

# Confirm test.md removed
ls test.md 2>/dev/null && echo "FAIL: test.md still exists" || echo "PASS: test.md removed"
```

## Validation Checklist
- [ ] test.md file removed
- [ ] Migration has server defaults
- [ ] Instance-scoped uniqueness implemented
- [ ] Retry logic handles transient failures
- [ ] Discord error handling is robust
- [ ] All existing tests remain green
- [ ] No new dependencies introduced
- [ ] PR review concerns addressed