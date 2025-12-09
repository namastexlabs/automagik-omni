"""
localStorage + PostgreSQL sync endpoint for user preferences.

Provides fast localStorage reads (0ms latency) with PostgreSQL persistence
(survives browser cache clear).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict

from src.db.database import get_db
from src.db.models import UserPreference
from src.api.deps import require_api_key

router = APIRouter()


class PreferencesSyncRequest(BaseModel):
    """Request to sync localStorage preferences to PostgreSQL."""

    preferences: Dict[str, str]


def get_user_id_from_api_key(api_key: str = Depends(require_api_key)) -> str:
    """Extract user ID from API key for preference isolation."""
    # For now, use API key itself as user ID
    # In future: Look up actual user_id from API key table
    return api_key


@router.post("/sync")
async def sync_preferences(
    data: PreferencesSyncRequest,
    user_id: str = Depends(get_user_id_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Sync localStorage to PostgreSQL (called on setApiKey, setTheme, etc.).

    Frontend calls this on every preference write to ensure persistence.
    """
    for key, value in data.preferences.items():
        pref = (
            db.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.key == key,
            )
            .first()
        )

        if pref:
            pref.value = value
        else:
            pref = UserPreference(user_id=user_id, key=key, value=value)
            db.add(pref)

    db.commit()
    return {"success": True}


@router.get("/sync")
async def get_synced_preferences(
    user_id: str = Depends(get_user_id_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Get preferences from PostgreSQL (called on app startup for restore).

    Frontend calls this once on app load to restore preferences after cache clear.
    """
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()

    return {"preferences": {p.key: p.value for p in prefs}}
