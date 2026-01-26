"""
Media Processing Service - converts media messages to text.

Supports:
- Audio → Transcription (Groq Whisper)
- Image → Description (Gemini/PydanticAI)
- Document → Content extraction (Docling)
"""

from .service import MediaProcessingService, media_processing_service

__all__ = ["MediaProcessingService", "media_processing_service"]
