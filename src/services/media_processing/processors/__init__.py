"""Media processors for different content types."""

from .base import BaseProcessor, ProcessingResult
from .audio import AudioProcessor
from .image import ImageProcessor
from .document import DocumentProcessor

__all__ = ["BaseProcessor", "ProcessingResult", "AudioProcessor", "ImageProcessor", "DocumentProcessor"]
