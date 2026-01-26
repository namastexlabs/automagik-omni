"""Image processor using Google Gemini for description generation."""

import logging
import time
import base64
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult
from ..pricing import calculate_processing_cost

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """
    Image description processor using Google Gemini.

    Uses Gemini's vision capabilities to generate detailed descriptions
    of images, useful for providing context to text-only LLMs.
    """

    SUPPORTED_MIME_TYPES = [
        "image/*",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
    ]

    # Default prompt for image description
    DEFAULT_PROMPT = """Analyze this image and provide a detailed description that would help someone who cannot see it understand what's in it.

Include:
1. Main subject(s) and their appearance
2. Setting/environment
3. Any text visible in the image
4. Notable details, colors, or objects
5. The overall mood or context

Be concise but thorough. If there's text in the image, transcribe it exactly.
Respond in the same language as any text in the image, or in Portuguese if no text is present."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        custom_prompt: Optional[str] = None,
    ):
        super().__init__()
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.prompt = custom_prompt or self.DEFAULT_PROMPT
        self._client = None
        self._model = None

    @property
    def processor_name(self) -> str:
        return "gemini_vision"

    @property
    def supported_mime_types(self) -> list[str]:
        return self.SUPPORTED_MIME_TYPES

    def _get_model(self):
        """Lazy initialization of Gemini model."""
        if self._model is None and self.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.gemini_api_key)
                self._model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini model initialized: {self.model_name}")
            except ImportError:
                logger.warning("google-generativeai not installed. Run: pip install google-generativeai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        return self._model

    async def process(
        self,
        file_path: Path,
        mime_type: str,
        custom_prompt: Optional[str] = None,
        **kwargs,
    ) -> ProcessingResult:
        """
        Generate a description of an image using Gemini.

        Args:
            file_path: Path to the image file
            mime_type: MIME type of the image
            custom_prompt: Optional custom prompt for description

        Returns:
            ProcessingResult with image description
        """
        start_time = time.time()
        prompt = custom_prompt or self.prompt

        model = self._get_model()
        if not model:
            return ProcessingResult(
                success=False,
                error_message="Gemini not configured (missing API key or package)",
            )

        try:
            # Read image file
            with open(file_path, "rb") as f:
                image_data = f.read()

            # Create image part for Gemini

            image_part = {
                "mime_type": mime_type,
                "data": image_data,
            }

            # Generate description
            response = model.generate_content([prompt, image_part])

            # Extract text from response
            if response and response.text:
                description = response.text.strip()
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Extract token usage from response
                input_tokens = None
                output_tokens = None
                total_tokens = None

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = response.usage_metadata
                    input_tokens = getattr(usage, "prompt_token_count", None)
                    output_tokens = getattr(usage, "candidates_token_count", None)
                    total_tokens = getattr(usage, "total_token_count", None)

                # Calculate cost
                cost_info = calculate_processing_cost(
                    processor_name="gemini_vision",
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost_str = f"${float(cost_info['total_cost_usd']):.6f}" if cost_info["total_cost_usd"] else "N/A"
                logger.info(f"Image described in {processing_time_ms}ms, tokens: {total_tokens}, cost: {cost_str}")

                return ProcessingResult(
                    success=True,
                    content=description,
                    content_format="text",
                    processor_name="gemini_vision",
                    processor_model=self.model_name,
                    processing_time_ms=processing_time_ms,
                    confidence_score=90,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_input_usd=cost_info["input_cost_usd"],
                    cost_output_usd=cost_info["output_cost_usd"],
                    cost_total_usd=cost_info["total_cost_usd"],
                    pricing_model=cost_info["pricing_model"],
                    pricing_rate_input=cost_info["pricing_rate_input"],
                    pricing_rate_output=cost_info["pricing_rate_output"],
                )
            else:
                return ProcessingResult(
                    success=False,
                    processor_name="gemini_vision",
                    processor_model=self.model_name,
                    error_message="No response from Gemini",
                )

        except Exception as e:
            logger.error(f"Gemini image processing error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="gemini_vision",
                processor_model=self.model_name,
                error_message=str(e),
            )

    async def process_from_base64(
        self,
        base64_data: str,
        mime_type: str,
        custom_prompt: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Generate description from base64-encoded image data.

        Args:
            base64_data: Base64-encoded image data
            mime_type: MIME type of the image
            custom_prompt: Optional custom prompt

        Returns:
            ProcessingResult with image description
        """
        start_time = time.time()
        prompt = custom_prompt or self.prompt

        model = self._get_model()
        if not model:
            return ProcessingResult(
                success=False,
                error_message="Gemini not configured (missing API key or package)",
            )

        try:
            # Decode base64
            image_data = base64.b64decode(base64_data)

            # Create image part for Gemini
            image_part = {
                "mime_type": mime_type,
                "data": image_data,
            }

            # Generate description
            response = model.generate_content([prompt, image_part])

            if response and response.text:
                description = response.text.strip()
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Extract token usage from response
                input_tokens = None
                output_tokens = None
                total_tokens = None

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = response.usage_metadata
                    input_tokens = getattr(usage, "prompt_token_count", None)
                    output_tokens = getattr(usage, "candidates_token_count", None)
                    total_tokens = getattr(usage, "total_token_count", None)

                # Calculate cost
                cost_info = calculate_processing_cost(
                    processor_name="gemini_vision",
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                return ProcessingResult(
                    success=True,
                    content=description,
                    content_format="text",
                    processor_name="gemini_vision",
                    processor_model=self.model_name,
                    processing_time_ms=processing_time_ms,
                    confidence_score=90,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_input_usd=cost_info["input_cost_usd"],
                    cost_output_usd=cost_info["output_cost_usd"],
                    cost_total_usd=cost_info["total_cost_usd"],
                    pricing_model=cost_info["pricing_model"],
                    pricing_rate_input=cost_info["pricing_rate_input"],
                    pricing_rate_output=cost_info["pricing_rate_output"],
                )
            else:
                return ProcessingResult(
                    success=False,
                    processor_name="gemini_vision",
                    processor_model=self.model_name,
                    error_message="No response from Gemini",
                )

        except Exception as e:
            logger.error(f"Gemini base64 processing error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="gemini_vision",
                processor_model=self.model_name,
                error_message=str(e),
            )
