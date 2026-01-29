"""
Media Processing Pricing Configuration.

Defines pricing rates for each provider and model used in media processing.
Rates are in USD and based on provider documentation (January 2026).

Sources:
- Groq: https://groq.com/pricing
- Google Gemini: https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://openai.com/api/pricing/
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from enum import Enum


class PricingUnit(Enum):
    """Unit of pricing measurement."""

    PER_HOUR = "per_hour"  # Audio transcription (Groq, OpenAI Whisper)
    PER_MINUTE = "per_minute"  # Audio transcription (OpenAI)
    PER_MILLION_TOKENS = "per_million_tokens"  # LLM pricing (Gemini)


@dataclass
class PricingRate:
    """Pricing rate for a specific model."""

    model_id: str
    provider: str
    unit: PricingUnit
    input_rate: Decimal  # Rate for input (or single rate for audio)
    output_rate: Decimal = Decimal("0")  # Rate for output (LLM only)
    description: str = ""

    def calculate_cost(
        self,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_seconds: Optional[int] = None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate cost based on usage.

        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        input_cost = Decimal("0")
        output_cost = Decimal("0")

        if self.unit == PricingUnit.PER_HOUR and duration_seconds is not None:
            # Audio: charged per hour
            hours = Decimal(str(duration_seconds)) / Decimal("3600")
            input_cost = hours * self.input_rate
        elif self.unit == PricingUnit.PER_MINUTE and duration_seconds is not None:
            # Audio: charged per minute
            minutes = Decimal(str(duration_seconds)) / Decimal("60")
            input_cost = minutes * self.input_rate
        elif self.unit == PricingUnit.PER_MILLION_TOKENS:
            # LLM: charged per million tokens
            if input_tokens is not None:
                input_cost = (Decimal(str(input_tokens)) / Decimal("1000000")) * self.input_rate
            if output_tokens is not None:
                output_cost = (Decimal(str(output_tokens)) / Decimal("1000000")) * self.output_rate

        total_cost = input_cost + output_cost
        return input_cost, output_cost, total_cost


# =============================================================================
# GROQ PRICING (January 2026)
# Source: https://groq.com/pricing
# =============================================================================

GROQ_WHISPER_LARGE_V3_TURBO = PricingRate(
    model_id="whisper-large-v3-turbo",
    provider="groq",
    unit=PricingUnit.PER_HOUR,
    input_rate=Decimal("0.04"),  # $0.04 per hour
    description="Groq Whisper Large V3 Turbo - Fast, recommended for most use cases",
)

GROQ_WHISPER_LARGE_V3 = PricingRate(
    model_id="whisper-large-v3",
    provider="groq",
    unit=PricingUnit.PER_HOUR,
    input_rate=Decimal("0.111"),  # $0.111 per hour
    description="Groq Whisper Large V3 - Higher accuracy",
)

GROQ_DISTIL_WHISPER = PricingRate(
    model_id="distil-whisper-large-v3-en",
    provider="groq",
    unit=PricingUnit.PER_HOUR,
    input_rate=Decimal("0.02"),  # $0.02 per hour
    description="Groq Distil-Whisper - English only, fastest",
)


# =============================================================================
# OPENAI PRICING (January 2026)
# Source: https://openai.com/api/pricing/
# =============================================================================

OPENAI_WHISPER = PricingRate(
    model_id="whisper-1",
    provider="openai",
    unit=PricingUnit.PER_MINUTE,
    input_rate=Decimal("0.006"),  # $0.006 per minute ($0.36/hour)
    description="OpenAI Whisper - Standard transcription",
)

OPENAI_GPT4O_TRANSCRIBE = PricingRate(
    model_id="gpt-4o-transcribe",
    provider="openai",
    unit=PricingUnit.PER_MINUTE,
    input_rate=Decimal("0.006"),  # $0.006 per minute
    description="OpenAI GPT-4o Transcribe - Advanced accuracy",
)

OPENAI_GPT4O_MINI_TRANSCRIBE = PricingRate(
    model_id="gpt-4o-mini-transcribe",
    provider="openai",
    unit=PricingUnit.PER_MINUTE,
    input_rate=Decimal("0.003"),  # $0.003 per minute
    description="OpenAI GPT-4o Mini Transcribe - Cost-effective",
)

# OpenAI Vision (for image description fallback)
OPENAI_GPT4O_MINI_VISION = PricingRate(
    model_id="gpt-4o-mini",
    provider="openai",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("0.15"),  # $0.15 per 1M input tokens
    output_rate=Decimal("0.60"),  # $0.60 per 1M output tokens
    description="OpenAI GPT-4o Mini Vision - Cost-effective image analysis",
)

OPENAI_GPT4O_VISION = PricingRate(
    model_id="gpt-4o",
    provider="openai",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("2.50"),  # $2.50 per 1M input tokens
    output_rate=Decimal("10.00"),  # $10.00 per 1M output tokens
    description="OpenAI GPT-4o Vision - High quality image analysis",
)

OPENAI_GPT5_NANO_VISION = PricingRate(
    model_id="gpt-5-nano",
    provider="openai",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("0.05"),  # $0.05 per 1M input tokens
    output_rate=Decimal("0.40"),  # $0.40 per 1M output tokens
    description="OpenAI GPT-5 Nano Vision - Cheapest multimodal model",
)


# =============================================================================
# GOOGLE GEMINI PRICING (January 2026)
# Source: https://ai.google.dev/gemini-api/docs/pricing
# =============================================================================

GEMINI_2_0_FLASH = PricingRate(
    model_id="gemini-2.0-flash",
    provider="google",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("0.10"),  # $0.10 per 1M input tokens
    output_rate=Decimal("0.40"),  # $0.40 per 1M output tokens
    description="Gemini 2.0 Flash - Fast, cost-effective vision",
)

GEMINI_2_5_FLASH = PricingRate(
    model_id="gemini-2.5-flash",
    provider="google",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("0.15"),  # $0.15 per 1M input tokens (thinking disabled)
    output_rate=Decimal("0.60"),  # $0.60 per 1M output tokens
    description="Gemini 2.5 Flash - Enhanced reasoning",
)

GEMINI_FLASH_LITE = PricingRate(
    model_id="gemini-flash-lite",
    provider="google",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("0.10"),  # $0.10 per 1M input tokens
    output_rate=Decimal("0.40"),  # $0.40 per 1M output tokens
    description="Gemini Flash Lite - Lightweight, fast",
)

GEMINI_2_5_PRO = PricingRate(
    model_id="gemini-2.5-pro",
    provider="google",
    unit=PricingUnit.PER_MILLION_TOKENS,
    input_rate=Decimal("1.25"),  # $1.25 per 1M input tokens
    output_rate=Decimal("10.00"),  # $10.00 per 1M output tokens
    description="Gemini 2.5 Pro - Highest quality",
)


# =============================================================================
# PRICING REGISTRY
# =============================================================================

# Map processor_name + model to pricing rate
PRICING_REGISTRY: dict[str, PricingRate] = {
    # Groq Whisper
    "groq_whisper:whisper-large-v3-turbo": GROQ_WHISPER_LARGE_V3_TURBO,
    "groq_whisper:whisper-large-v3": GROQ_WHISPER_LARGE_V3,
    "groq_whisper:distil-whisper-large-v3-en": GROQ_DISTIL_WHISPER,
    # OpenAI Whisper
    "openai_whisper:whisper-1": OPENAI_WHISPER,
    "openai_whisper:gpt-4o-transcribe": OPENAI_GPT4O_TRANSCRIBE,
    "openai_whisper:gpt-4o-mini-transcribe": OPENAI_GPT4O_MINI_TRANSCRIBE,
    # OpenAI Vision (images - fallback)
    "openai_vision:gpt-5-nano": OPENAI_GPT5_NANO_VISION,
    "openai_vision:gpt-4o-mini": OPENAI_GPT4O_MINI_VISION,
    "openai_vision:gpt-4o": OPENAI_GPT4O_VISION,
    # Gemini Vision (images)
    "gemini_vision:gemini-2.0-flash": GEMINI_2_0_FLASH,
    "gemini_vision:gemini-2.0-flash-exp": GEMINI_2_0_FLASH,  # Alias
    "gemini_vision:gemini-2.5-flash": GEMINI_2_5_FLASH,
    "gemini_vision:gemini-flash-lite": GEMINI_FLASH_LITE,
    "gemini_vision:gemini-2.5-pro": GEMINI_2_5_PRO,
    # Gemini Video (same pricing as vision)
    "gemini_video:gemini-2.0-flash": GEMINI_2_0_FLASH,
    "gemini_video:gemini-2.5-flash": GEMINI_2_5_FLASH,
    "gemini_video:gemini-flash-lite": GEMINI_FLASH_LITE,
    "gemini_video:gemini-2.5-pro": GEMINI_2_5_PRO,
    # PyMuPDF (local, no cost)
    "pymupdf:local": PricingRate(
        model_id="local",
        provider="local",
        unit=PricingUnit.PER_HOUR,
        input_rate=Decimal("0"),
        description="PyMuPDF - Local processing, no API cost",
    ),
    # python-docx (local, no cost)
    "python_docx:local": PricingRate(
        model_id="local",
        provider="local",
        unit=PricingUnit.PER_HOUR,
        input_rate=Decimal("0"),
        description="python-docx - Local processing, no API cost",
    ),
    # Text reader (local, no cost)
    "text_reader:local": PricingRate(
        model_id="local",
        provider="local",
        unit=PricingUnit.PER_HOUR,
        input_rate=Decimal("0"),
        description="Text reader - Local processing, no API cost",
    ),
}


def get_pricing_rate(processor_name: str, model: Optional[str] = None) -> Optional[PricingRate]:
    """
    Get pricing rate for a processor/model combination.

    Args:
        processor_name: Name of the processor (e.g., 'groq_whisper', 'gemini_vision')
        model: Model name (e.g., 'whisper-large-v3-turbo', 'gemini-2.0-flash')

    Returns:
        PricingRate if found, None otherwise
    """
    if model:
        key = f"{processor_name}:{model}"
        if key in PRICING_REGISTRY:
            return PRICING_REGISTRY[key]

    # Try without model (for local processors)
    key = f"{processor_name}:local"
    if key in PRICING_REGISTRY:
        return PRICING_REGISTRY[key]

    return None


def calculate_processing_cost(
    processor_name: str,
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    duration_seconds: Optional[int] = None,
) -> dict:
    """
    Calculate processing cost for a media processing operation.

    Args:
        processor_name: Name of the processor
        model: Model name
        input_tokens: Number of input tokens (for LLM)
        output_tokens: Number of output tokens (for LLM)
        duration_seconds: Duration in seconds (for audio)

    Returns:
        Dict with cost breakdown:
        {
            "input_cost_usd": Decimal,
            "output_cost_usd": Decimal,
            "total_cost_usd": Decimal,
            "pricing_model": str,
            "pricing_rate_input": Decimal,
            "pricing_rate_output": Decimal,
        }
    """
    rate = get_pricing_rate(processor_name, model)
    if not rate:
        return {
            "input_cost_usd": Decimal("0"),
            "output_cost_usd": Decimal("0"),
            "total_cost_usd": Decimal("0"),
            "pricing_model": None,
            "pricing_rate_input": Decimal("0"),
            "pricing_rate_output": Decimal("0"),
        }

    input_cost, output_cost, total_cost = rate.calculate_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_seconds=duration_seconds,
    )

    return {
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": total_cost,
        "pricing_model": f"{rate.provider}_{rate.model_id}",
        "pricing_rate_input": rate.input_rate,
        "pricing_rate_output": rate.output_rate,
    }
