"""
localStorage + PostgreSQL sync endpoint for user preferences.

Provides fast localStorage reads (0ms latency) with PostgreSQL persistence
(survives browser cache clear).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict

from src.db.database import get_db
from src.db.models import UserPreference
from src.api.deps import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


class PreferencesSyncRequest(BaseModel):
    """Request to sync localStorage preferences to PostgreSQL."""

    preferences: Dict[str, str]


def get_session_id_from_api_key(api_key: str = Depends(require_api_key)) -> str:
    """Extract session ID from API key for preference isolation."""
    # For now, use API key itself as session identifier
    # In future: Look up actual user/session mapping from API key table
    return api_key


@router.post("/sync")
async def sync_preferences(
    data: PreferencesSyncRequest,
    session_id: str = Depends(get_session_id_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Sync localStorage to PostgreSQL (called on setApiKey, setTheme, etc.).

    Frontend calls this on every preference write to ensure persistence.
    """
    try:
        for key, value in data.preferences.items():
            pref = (
                db.query(UserPreference)
                .filter(UserPreference.session_id == session_id, UserPreference.key == key)
                .first()
            )

            if pref:
                pref.value = value
            else:
                pref = UserPreference(session_id=session_id, key=key, value=value)
                db.add(pref)

        db.commit()
        return {"success": True}
    except Exception as exc:
        logger.error(f"Failed to sync preferences for session {session_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync preferences",
        )


@router.get("/sync")
async def get_synced_preferences(
    session_id: str = Depends(get_session_id_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Get preferences from PostgreSQL (called on app startup for restore).

    Frontend calls this once on app load to restore preferences after cache clear.
    """
    try:
        prefs = db.query(UserPreference).filter(UserPreference.session_id == session_id).all()
        return {"preferences": {p.key: p.value for p in prefs}}
    except Exception as exc:
        logger.error(f"Failed to load preferences for session {session_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load preferences",
        )
