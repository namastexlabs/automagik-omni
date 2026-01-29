"""Image processor using Google Gemini for description generation with OpenAI fallback."""

import asyncio
import logging
import time
import base64
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult
from ..pricing import calculate_processing_cost

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 30  # seconds


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
        model_name: str = "gemini-2.5-flash",
        custom_prompt: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-5-nano",  # Cheapest OpenAI model with vision
    ):
        super().__init__()
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.prompt = custom_prompt or self.DEFAULT_PROMPT
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self._client = None
        self._model = None
        self._openai_client = None

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

    def _get_openai_client(self):
        """Lazy initialization of OpenAI client for fallback."""
        if self._openai_client is None and self.openai_api_key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info(f"OpenAI client initialized for fallback: {self.openai_model}")
            except ImportError:
                logger.warning("openai not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
        return self._openai_client

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error (429)."""
        error_str = str(error).lower()
        return "429" in error_str or "resource exhausted" in error_str or "rate limit" in error_str

    async def _process_with_openai(
        self,
        image_data: bytes,
        mime_type: str,
        prompt: str,
        start_time: float,
    ) -> ProcessingResult:
        """Process image using OpenAI Vision as fallback."""
        client = self._get_openai_client()
        if not client:
            return ProcessingResult(
                success=False,
                error_message="OpenAI fallback not configured (missing API key)",
            )

        try:
            # Encode image to base64
            b64_data = base64.b64encode(image_data).decode("utf-8")

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1024,
            )

            if response and response.choices and response.choices[0].message.content:
                description = response.choices[0].message.content.strip()
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Extract token usage
                input_tokens = response.usage.prompt_tokens if response.usage else None
                output_tokens = response.usage.completion_tokens if response.usage else None
                total_tokens = response.usage.total_tokens if response.usage else None

                # Calculate cost
                cost_info = calculate_processing_cost(
                    processor_name="openai_vision",
                    model=self.openai_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost_str = f"${float(cost_info['total_cost_usd']):.6f}" if cost_info["total_cost_usd"] else "N/A"
                logger.info(
                    f"Image described via OpenAI fallback in {processing_time_ms}ms, tokens: {total_tokens}, cost: {cost_str}"
                )

                return ProcessingResult(
                    success=True,
                    content=description,
                    content_format="text",
                    processor_name="openai_vision",
                    processor_model=self.openai_model,
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
                    processor_name="openai_vision",
                    processor_model=self.openai_model,
                    error_message="No response from OpenAI",
                )

        except Exception as e:
            logger.error(f"OpenAI fallback error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="openai_vision",
                processor_model=self.openai_model,
                error_message=f"OpenAI fallback failed: {str(e)}",
            )

    async def process(
        self,
        file_path: Path,
        mime_type: str,
        custom_prompt: Optional[str] = None,
        **kwargs,
    ) -> ProcessingResult:
        """
        Generate a description of an image using Gemini with retry and OpenAI fallback.

        Args:
            file_path: Path to the image file
            mime_type: MIME type of the image
            custom_prompt: Optional custom prompt for description

        Returns:
            ProcessingResult with image description
        """
        start_time = time.time()
        prompt = custom_prompt or self.prompt

        # Read image file once
        with open(file_path, "rb") as f:
            image_data = f.read()

        model = self._get_model()
        if not model:
            # No Gemini, try OpenAI directly
            if self.openai_api_key:
                logger.info("Gemini not configured, using OpenAI fallback")
                return await self._process_with_openai(image_data, mime_type, prompt, start_time)
            return ProcessingResult(
                success=False,
                error_message="No image processor configured (missing Gemini and OpenAI API keys)",
            )

        # Try Gemini with retry logic
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
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
                    last_error = "No response from Gemini"

            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    # Rate limit - retry with exponential backoff
                    retry_delay = min(INITIAL_RETRY_DELAY * (2**attempt), MAX_RETRY_DELAY)
                    logger.warning(
                        f"Gemini rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    # Other error - don't retry, go to fallback
                    logger.error(f"Gemini image processing error: {e}")
                    break

        # All Gemini retries failed - try OpenAI fallback
        if self.openai_api_key:
            logger.warning(
                f"Gemini failed after {MAX_RETRIES} attempts, using OpenAI fallback. Last error: {last_error}"
            )
            return await self._process_with_openai(image_data, mime_type, prompt, start_time)

        # No fallback available
        return ProcessingResult(
            success=False,
            processor_name="gemini_vision",
            processor_model=self.model_name,
            error_message=str(last_error) if last_error else "Processing failed",
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
