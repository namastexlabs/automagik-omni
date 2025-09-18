"""
Access control management API endpoints.

Provides CRUD operations for allow/block rules with in-memory cache updates.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.api.deps import get_database, verify_api_key
from src.db.models import AccessRule, AccessRuleType
from src.services.access_control import access_control_service


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/access", tags=["access"])


class AccessRuleCreate(BaseModel):
    """Request model to create a new access rule."""

    phone_number: str = Field(..., description="E164 format, supports prefix wildcard with trailing *")
    rule_type: AccessRuleType | str = Field(..., description="allow | block")
    instance_name: Optional[str] = Field(default=None, description="Optional scope; omit for global rule")


class AccessRuleOut(BaseModel):
    """Response model for access rules."""

    id: int
    instance_name: Optional[str]
    phone_number: str
    rule_type: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/rules", response_model=List[AccessRuleOut], summary="List access rules")
def list_access_rules(
    instance_name: Optional[str] = Query(None, description="Filter by instance scope"),
    rule_type: Optional[AccessRuleType] = Query(None, description="Filter by rule type"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Return all access rules, optionally filtered by scope and type."""
    query = db.query(AccessRule)
    if instance_name is not None:
        query = query.filter(AccessRule.instance_name == instance_name)
    if rule_type is not None:
        query = query.filter(AccessRule.rule_type == rule_type.value)
    rules = query.order_by(AccessRule.id.desc()).all()
    logger.info("Listing %d access rules (scope=%s, type=%s)", len(rules), instance_name or "any", rule_type or "any")
    return rules


@router.post("/rules", response_model=AccessRuleOut, status_code=status.HTTP_201_CREATED, summary="Create access rule")
def create_access_rule(
    payload: AccessRuleCreate,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Create a new allow/block rule and update cache."""
    try:
        rule = access_control_service.add_rule(
            phone_number=payload.phone_number,
            rule_type=payload.rule_type,
            instance_name=payload.instance_name,
            db=db,
        )
        logger.info(
            "Created access rule id=%s scope=%s phone=%s type=%s",
            rule.id,
            rule.instance_name or "global",
            rule.phone_number,
            rule.rule_type,
        )
        return rule
    except Exception as e:
        logger.error("Failed to create access rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete access rule")
def delete_access_rule(
    rule_id: int,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Delete a rule and update cache."""
    removed = access_control_service.remove_rule(rule_id, db)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    logger.info("Deleted access rule id=%s", rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
