"""Media processors for different content types."""

from .base import BaseProcessor, ProcessingResult
from .audio import AudioProcessor

__all__ = ["BaseProcessor", "ProcessingResult", "AudioProcessor"]
