@AGENTS.md

# Omni Project Guidelines

## Database Schema Updates - CRITICAL

When adding or modifying columns in `omni_*` tables, you MUST update THREE places:

1. **SQLAlchemy Model** (`src/db/models.py`)
   - Add the column definition to the Python model class

2. **Prisma Schema** (`resources/omni-whatsapp-core/prisma/postgresql-schema.prisma`)
   - Add the column to the corresponding Prisma model (e.g., `OmniInstanceConfigs`)
   - Use `@map("column_name")` to map camelCase to snake_case

3. **Alembic Migration** (`alembic/versions/`)
   - Create a new migration file with `alembic revision -m "description"`
   - Run `alembic upgrade head` to apply

**Why this matters:** Evolution API runs `prisma db push` on startup. If columns exist in the database but NOT in the Prisma schema, Prisma will DROP them. This caused hours of debugging when columns kept mysteriously disappearing.

**Example - Adding a column to `omni_instance_configs`:**

```python
# 1. src/db/models.py (SQLAlchemy)
class InstanceConfig(Base):
    my_new_column = Column(Integer, default=0, nullable=False)
```

```prisma
// 2. postgresql-schema.prisma (Prisma)
model OmniInstanceConfigs {
  myNewColumn Int @default(0) @map("my_new_column")
}
```

```python
# 3. alembic/versions/xxx_add_my_new_column.py
def upgrade():
    op.add_column('omni_instance_configs',
        sa.Column('my_new_column', sa.Integer(), nullable=False, server_default='0'))
```
