"""Media processors for different content types."""

from .base import BaseProcessor, ProcessingResult
from .audio import AudioProcessor
from .image import ImageProcessor

__all__ = ["BaseProcessor", "ProcessingResult", "AudioProcessor", "ImageProcessor"]
