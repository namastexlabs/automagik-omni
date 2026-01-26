"""Seed media processing API key settings

Revision ID: 006_media_settings
Revises: 005_media_content
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = "006_media_settings"
down_revision = "005_media_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed media processing settings in omni_global_settings."""
    # Define the settings to insert
    now = datetime.utcnow()
    settings = [
        {
            "key": "groq_api_key",
            "value": None,  # Empty by default, can be set via UI or env var
            "value_type": "secret",
            "category": "media_processing",
            "description": "Groq API key for Whisper audio transcription (fast, recommended)",
            "is_secret": True,
            "is_required": False,
            "default_value": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "key": "openai_api_key",
            "value": None,
            "value_type": "secret",
            "category": "media_processing",
            "description": "OpenAI API key for Whisper audio transcription (fallback)",
            "is_secret": True,
            "is_required": False,
            "default_value": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "key": "gemini_api_key",
            "value": None,
            "value_type": "secret",
            "category": "media_processing",
            "description": "Google Gemini API key for image description and vision tasks",
            "is_secret": True,
            "is_required": False,
            "default_value": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "key": "media_processing_enabled",
            "value": "true",
            "value_type": "boolean",
            "category": "media_processing",
            "description": "Enable automatic media processing for incoming messages",
            "is_secret": False,
            "is_required": False,
            "default_value": "true",
            "created_at": now,
            "updated_at": now,
        },
        {
            "key": "audio_transcription_language",
            "value": "pt",
            "value_type": "string",
            "category": "media_processing",
            "description": "Default language code for audio transcription (e.g., pt, en, es)",
            "is_secret": False,
            "is_required": False,
            "default_value": "pt",
            "created_at": now,
            "updated_at": now,
        },
    ]

    # Use raw SQL to insert, checking for existing keys
    conn = op.get_bind()
    for setting in settings:
        # Check if setting already exists
        result = conn.execute(
            sa.text("SELECT 1 FROM omni_global_settings WHERE key = :key"),
            {"key": setting["key"]},
        )
        if result.fetchone() is None:
            conn.execute(
                sa.text("""
                    INSERT INTO omni_global_settings
                    (key, value, value_type, category, description, is_secret, is_required, default_value, created_at, updated_at)
                    VALUES (:key, :value, :value_type, :category, :description, :is_secret, :is_required, :default_value, :created_at, :updated_at)
                """),
                setting,
            )


def downgrade() -> None:
    """Remove media processing settings."""
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            DELETE FROM omni_global_settings
            WHERE key IN ('groq_api_key', 'openai_api_key', 'gemini_api_key', 'media_processing_enabled', 'audio_transcription_language')
        """)
    )
