"""Video processor using Google Gemini for video understanding and description."""

import logging
import time
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult
from ..pricing import calculate_processing_cost

logger = logging.getLogger(__name__)


class VideoProcessor(BaseProcessor):
    """
    Video description processor using Google Gemini.

    Uses Gemini's video understanding capabilities to generate detailed
    descriptions of videos, useful for providing context to text-only LLMs.
    """

    SUPPORTED_MIME_TYPES = [
        "video/*",
        "video/mp4",
        "video/mpeg",
        "video/mov",
        "video/avi",
        "video/x-flv",
        "video/mpg",
        "video/webm",
        "video/wmv",
        "video/3gpp",
        "video/quicktime",
    ]

    # Default prompt for video description
    DEFAULT_PROMPT = """Analyze this video and provide a detailed description that would help someone who cannot see it understand what's happening.

Include:
1. Main subject(s) and their actions throughout the video
2. Setting/environment and any changes
3. Any speech, dialogue, or important audio (transcribe if possible)
4. Any text visible in the video
5. Key events or moments in chronological order
6. The overall context, mood, or purpose of the video

Be concise but thorough. If there's speech, transcribe the key parts.
Respond in the same language as any speech in the video, or in Portuguese if no speech is present."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
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
        return "gemini_video"

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
                logger.info(f"Gemini model initialized for video: {self.model_name}")
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
        Generate a description of a video using Gemini.

        Args:
            file_path: Path to the video file
            mime_type: MIME type of the video
            custom_prompt: Optional custom prompt for description

        Returns:
            ProcessingResult with video description
        """
        start_time = time.time()

        model = self._get_model()
        if not model:
            return ProcessingResult(
                success=False,
                error_message="Gemini model not initialized. Check API key.",
            )

        try:
            import google.generativeai as genai

            # Upload video file using File API (required for video)
            logger.info(f"Uploading video to Gemini: {file_path}")
            video_file = genai.upload_file(path=str(file_path), mime_type=mime_type)

            # Wait for file to be processed
            logger.info(f"Waiting for video processing: {video_file.name}")
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                return ProcessingResult(
                    success=False,
                    error_message=f"Video processing failed: {video_file.state.name}",
                )

            prompt = custom_prompt or self.prompt

            # Generate content with the video
            logger.info(f"Generating video description with {self.model_name}")
            response = model.generate_content(
                [video_file, prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=4096,
                ),
            )

            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
                logger.debug(f"Deleted uploaded video file: {video_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete uploaded video file: {e}")

            processing_time = int((time.time() - start_time) * 1000)

            # Extract token usage if available
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata"):
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)

            total_tokens = input_tokens + output_tokens

            # Calculate cost
            cost_info = calculate_processing_cost(
                processor_name="gemini_video",
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            description = response.text if response.text else ""

            cost_str = f"${float(cost_info['total_cost_usd']):.6f}" if cost_info["total_cost_usd"] else "N/A"
            logger.info(f"Video described in {processing_time}ms, tokens: {total_tokens}, cost: {cost_str}")

            return ProcessingResult(
                success=True,
                content=description,
                content_format="text",
                processor_name=self.processor_name,
                processor_model=self.model_name,
                processing_time_ms=processing_time,
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

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error(f"Video description failed: {error_msg}")

            return ProcessingResult(
                success=False,
                error_message=error_msg,
                processing_time_ms=processing_time,
            )
