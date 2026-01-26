"""Base processor class for media content extraction."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of media processing."""

    success: bool
    content: Optional[str] = None
    content_format: str = "text"  # text, markdown, json
    processor_name: Optional[str] = None
    processor_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    confidence_score: Optional[int] = None  # 0-100
    error_message: Optional[str] = None


class BaseProcessor(ABC):
    """Abstract base class for media processors."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def processor_name(self) -> str:
        """Return the processor name (e.g., 'groq_whisper')."""
        pass

    @property
    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """Return list of supported MIME types."""
        pass

    @abstractmethod
    async def process(
        self,
        file_path: Path,
        mime_type: str,
        **kwargs,
    ) -> ProcessingResult:
        """
        Process a media file and extract text content.

        Args:
            file_path: Path to the downloaded media file
            mime_type: MIME type of the media
            **kwargs: Additional processor-specific options

        Returns:
            ProcessingResult with extracted content or error
        """
        pass

    def supports_mime_type(self, mime_type: str) -> bool:
        """Check if this processor supports the given MIME type."""
        if not mime_type:
            return False
        # Check exact match or prefix match (e.g., audio/* matches audio/ogg)
        for supported in self.supported_mime_types:
            if supported.endswith("/*"):
                prefix = supported[:-1]  # Remove *
                if mime_type.startswith(prefix):
                    return True
            elif mime_type == supported:
                return True
        return False
