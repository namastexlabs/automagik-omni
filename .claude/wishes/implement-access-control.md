# 🔐 Simple Access Control Implementation

## 📋 Overview

Minimal access control that filters messages based on allow/deny rules. Uses in-memory caching to avoid performance impact.

### Core Logic
```
IF no rules exist → ALLOW (open system)
IF user in deny list → BLOCK
IF allow list exists AND user not in it → BLOCK
ELSE → ALLOW
```

## 🎯 Implementation

### 1. Database Schema (Simple)
```sql
CREATE TABLE access_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(10) NOT NULL CHECK(rule_type IN ('allow', 'deny')),
    identifier VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(instance_name, rule_type, identifier)  -- Prevent duplicate rules
);

CREATE INDEX idx_access_instance ON access_rules(instance_name, is_active);
```

### 2. Model
```python
# src/db/models.py (add to existing file)
class AccessRule(Base):
    __tablename__ = "access_rules"

    id = Column(Integer, primary_key=True)
    instance_name = Column(String(100), nullable=False)
    rule_type = Column(String(10), nullable=False)  # 'allow' or 'deny'
    identifier = Column(String(255), nullable=False)  # phone or username
    created_at = Column(DateTime, default=datetime_utcnow)
    is_active = Column(Boolean, default=True)
```

### 3. Access Control Service with Cache
```python
# src/services/access_control.py
from typing import Dict, Set, Tuple
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class AccessControl:
    """Simple in-memory access control with database persistence."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Set[str]]] = {}
        # Structure: {instance_name: {"allow": {identifiers}, "deny": {identifiers}}}

    def load_rules(self, db: Session) -> None:
        """Load all active rules into memory cache."""
        from src.db.models import AccessRule

        self._cache.clear()
        rules = db.query(AccessRule).filter(AccessRule.is_active == True).all()

        for rule in rules:
            if rule.instance_name not in self._cache:
                self._cache[rule.instance_name] = {"allow": set(), "deny": set()}
            self._cache[rule.instance_name][rule.rule_type].add(rule.identifier.lower())

        logger.info(f"Loaded {len(rules)} access rules into cache")

    def check_access(self, instance_name: str, identifier: str) -> Tuple[bool, str]:
        """
        Check if user is allowed. Returns (allowed, reason).
        Uses cached rules - no database query.
        """
        if not identifier:
            return True, "No identifier"

        identifier = identifier.lower()
        instance_rules = self._cache.get(instance_name, {"allow": set(), "deny": set()})

        # Check deny list first (highest priority)
        if identifier in instance_rules["deny"]:
            return False, "User blocked"

        # If allow list exists, user must be in it
        if instance_rules["allow"]:
            if identifier in instance_rules["allow"]:
                return True, "User allowed"
            return False, "Not in whitelist"

        # No restrictions
        return True, "No restrictions"

    def add_rule(self, db: Session, instance_name: str, rule_type: str, identifier: str) -> int:
        """Add a rule and update cache."""
        from src.db.models import AccessRule
        from sqlalchemy.exc import IntegrityError

        # Check if rule already exists
        existing = db.query(AccessRule).filter(
            AccessRule.instance_name == instance_name,
            AccessRule.rule_type == rule_type,
            AccessRule.identifier == identifier,
            AccessRule.is_active == True
        ).first()

        if existing:
            return existing.id  # Return existing rule ID (idempotent)

        try:
            rule = AccessRule(
                instance_name=instance_name,
                rule_type=rule_type,
                identifier=identifier
            )
            db.add(rule)
            db.commit()

            # Update cache
            if instance_name not in self._cache:
                self._cache[instance_name] = {"allow": set(), "deny": set()}
            self._cache[instance_name][rule_type].add(identifier.lower())

            return rule.id
        except IntegrityError:
            db.rollback()
            # Race condition - rule was added by another request
            existing = db.query(AccessRule).filter(
                AccessRule.instance_name == instance_name,
                AccessRule.rule_type == rule_type,
                AccessRule.identifier == identifier
            ).first()
            return existing.id if existing else -1

    def remove_rule(self, db: Session, rule_id: int) -> bool:
        """Remove a rule and update cache."""
        from src.db.models import AccessRule

        rule = db.query(AccessRule).filter(AccessRule.id == rule_id).first()
        if not rule:
            return False

        # Update cache
        if rule.instance_name in self._cache:
            self._cache[rule.instance_name][rule.rule_type].discard(rule.identifier.lower())

        db.delete(rule)
        db.commit()
        return True

# Global singleton
access_control = AccessControl()
```

### 4. MessageRouter Integration (Minimal)
```python
# src/services/message_router.py
# Add at line 55 in route_message method:

from src.services.access_control import access_control

# Extract identifier based on channel
identifier = None
if session_origin == "whatsapp" and user:
    identifier = user.get("phone_number", "")
elif session_origin == "discord" and user:
    identifier = user.get("user_data", {}).get("username", "")

# Check access (fast in-memory lookup)
if identifier and agent_config:
    instance_name = agent_config.get("instance_config", {}).get("name")
    if instance_name:
        allowed, reason = access_control.check_access(instance_name, identifier)
        if not allowed:
            logger.info(f"Access denied: {reason} for {identifier}")
            return {"status": "blocked", "reason": reason}
```

### 5. API Endpoints (Minimal CRUD)
```python
# src/api/routes/access.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from src.api.deps import get_database, verify_api_key
from src.services.access_control import access_control

router = APIRouter(prefix="/access", tags=["Access Control"])

class RuleRequest(BaseModel):
    instance_name: str
    rule_type: str  # 'allow' or 'deny'
    identifier: str

@router.post("/rules")
async def add_rule(rule: RuleRequest, db=Depends(get_database), _=Depends(verify_api_key)):
    """Add an access rule."""
    if rule.rule_type not in ["allow", "deny"]:
        raise HTTPException(400, "rule_type must be 'allow' or 'deny'")

    rule_id = access_control.add_rule(db, rule.instance_name, rule.rule_type, rule.identifier)
    return {
        "id": rule_id,
        "status": "created",
        "rule": {
            "instance_name": rule.instance_name,
            "rule_type": rule.rule_type,
            "identifier": rule.identifier
        }
    }

@router.get("/rules")
async def list_all_rules(db=Depends(get_database), _=Depends(verify_api_key)):
    """List all access rules across all instances."""
    from src.db.models import AccessRule

    rules = db.query(AccessRule).filter(AccessRule.is_active == True).all()

    # Group by instance
    by_instance = {}
    for rule in rules:
        if rule.instance_name not in by_instance:
            by_instance[rule.instance_name] = {"allow": [], "deny": []}

        rule_data = {
            "id": rule.id,
            "identifier": rule.identifier,
            "created_at": rule.created_at.isoformat()
        }
        by_instance[rule.instance_name][rule.rule_type].append(rule_data)

    return {
        "instances": by_instance,
        "total": len(rules)
    }

@router.get("/rules/{instance_name}")
async def get_rules(instance_name: str, db=Depends(get_database), _=Depends(verify_api_key)):
    """Get rules for a specific instance."""
    from src.db.models import AccessRule

    rules = db.query(AccessRule).filter(
        AccessRule.instance_name == instance_name,
        AccessRule.is_active == True
    ).all()

    return {
        "instance": instance_name,
        "allow": [
            {"id": r.id, "identifier": r.identifier, "created_at": r.created_at.isoformat()}
            for r in rules if r.rule_type == "allow"
        ],
        "deny": [
            {"id": r.id, "identifier": r.identifier, "created_at": r.created_at.isoformat()}
            for r in rules if r.rule_type == "deny"
        ],
        "total": len(rules)
    }

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db=Depends(get_database), _=Depends(verify_api_key)):
    """Delete a rule."""
    from src.db.models import AccessRule

    # Get rule details before deleting
    rule = db.query(AccessRule).filter(AccessRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")

    rule_info = {
        "id": rule.id,
        "instance_name": rule.instance_name,
        "rule_type": rule.rule_type,
        "identifier": rule.identifier
    }

    if not access_control.remove_rule(db, rule_id):
        raise HTTPException(500, "Failed to delete rule")

    return {"status": "deleted", "rule": rule_info}

@router.post("/reload")
async def reload_rules(db=Depends(get_database), _=Depends(verify_api_key)):
    """Reload all rules from database into cache."""
    access_control.load_rules(db)
    return {"status": "reloaded"}
```

### 6. Startup Cache Loading
```python
# src/main.py (add to startup)
@app.on_event("startup")
async def startup_event():
    """Load access rules on startup."""
    from src.db.database import get_db
    from src.services.access_control import access_control

    with get_db() as db:
        access_control.load_rules(db)
```

### 7. Migration
```python
# alembic/versions/xxx_add_access_rules.py
def upgrade():
    op.create_table('access_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('instance_name', sa.String(100), nullable=False),
        sa.Column('rule_type', sa.String(10), nullable=False),
        sa.Column('identifier', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), server_default='1')
    )
    op.create_index('idx_access_instance', 'access_rules', ['instance_name', 'is_active'])

def downgrade():
    op.drop_index('idx_access_instance')
    op.drop_table('access_rules')
```


## ✅ Success Criteria
- Messages filtered based on rules
- No performance impact (in-memory cache)
- Simple API for rule management
- System open by default (no rules = allow all)

## 🧪 Testing
```bash
# Add allow rule
curl -X POST http://localhost:8882/api/access/rules \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instance_name": "my-whatsapp", "rule_type": "allow", "identifier": "+5511999999999"}'

# Response:
# {
#   "id": 1,
#   "status": "created",
#   "rule": {
#     "instance_name": "my-whatsapp",
#     "rule_type": "allow",
#     "identifier": "+5511999999999"
#   }
# }

# Get rules for instance
curl http://localhost:8882/api/access/rules/my-whatsapp \
  -H "X-API-Key: $API_KEY"

# Response:
# {
#   "instance": "my-whatsapp",
#   "allow": [
#     {"id": 1, "identifier": "+5511999999999", "created_at": "2025-01-18T10:30:00"}
#   ],
#   "deny": [],
#   "total": 1
# }

# List all rules
curl http://localhost:8882/api/access/rules \
  -H "X-API-Key: $API_KEY"

# Response:
# {
#   "instances": {
#     "my-whatsapp": {
#       "allow": [{"id": 1, "identifier": "+5511999999999", "created_at": "2025-01-18T10:30:00"}],
#       "deny": []
#     }
#   },
#   "total": 1
# }

# Delete rule
curl -X DELETE http://localhost:8882/api/access/rules/1 \
  -H "X-API-Key: $API_KEY"

# Response:
# {
#   "status": "deleted",
#   "rule": {
#     "id": 1,
#     "instance_name": "my-whatsapp",
#     "rule_type": "allow",
#     "identifier": "+5511999999999"
#   }
# }
```

## 📝 Implementation Order
1. Create migration and run it
2. Add AccessRule model to models.py
3. Create access_control.py service
4. Add API routes
5. Integrate with MessageRouter
6. Add startup cache loading
7. Test with real messages

## 🎯 Design Principles
- **Simple**: Just allow/deny lists, nothing more
- **Fast**: In-memory cache, no DB queries per message
- **Reliable**: Fail open if cache issues
- **Minimal**: ~200 lines of code total
```