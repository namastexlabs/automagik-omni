"""Document processor using PyMuPDF with Gemini fallback for scanned PDFs."""

import logging
import time
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessingResult
from ..pricing import calculate_processing_cost

logger = logging.getLogger(__name__)


class DocumentProcessor(BaseProcessor):
    """
    Document content extraction processor.

    Primary: PyMuPDF (fitz) for text-based PDFs - fast and lightweight
    Fallback: Google Gemini for scanned/image PDFs - uses vision capabilities

    Supports: PDF, Word documents (basic), text files
    """

    SUPPORTED_MIME_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]

    # Minimum text length to consider extraction successful
    # If below this, we assume it's a scanned PDF and use Gemini
    MIN_TEXT_LENGTH = 50

    # Gemini prompt for document analysis
    GEMINI_PROMPT = """Extract and transcribe all text content from this document image.

Instructions:
1. Transcribe ALL visible text exactly as written
2. Preserve the document structure (headings, paragraphs, lists)
3. Use markdown formatting for structure
4. If there are tables, format them as markdown tables
5. If there are images with captions, note them as [Image: caption]
6. Maintain the reading order (top to bottom, left to right)

Output the complete text content in markdown format."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.0-flash",
    ):
        super().__init__()
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self._gemini_model = None

    @property
    def processor_name(self) -> str:
        return "pymupdf"

    @property
    def supported_mime_types(self) -> list[str]:
        return self.SUPPORTED_MIME_TYPES

    def _get_gemini_model(self):
        """Lazy initialization of Gemini model for fallback."""
        if self._gemini_model is None and self.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.gemini_api_key)
                self._gemini_model = genai.GenerativeModel(self.gemini_model)
                logger.info(f"Gemini model initialized for document fallback: {self.gemini_model}")
            except ImportError:
                logger.warning("google-generativeai not installed for document fallback")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini for documents: {e}")
        return self._gemini_model

    async def process(
        self,
        file_path: Path,
        mime_type: str,
        use_gemini_fallback: bool = True,
        **kwargs,
    ) -> ProcessingResult:
        """
        Extract text content from a document.

        Args:
            file_path: Path to the document file
            mime_type: MIME type of the document
            use_gemini_fallback: If True, use Gemini for scanned PDFs

        Returns:
            ProcessingResult with extracted text content
        """
        start_time = time.time()

        # Handle text files directly
        if mime_type in ["text/plain", "text/markdown"]:
            return await self._process_text_file(file_path, start_time)

        # Handle PDF files
        if mime_type == "application/pdf":
            return await self._process_pdf(file_path, use_gemini_fallback, start_time)

        # Handle Word documents
        if mime_type in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return await self._process_word(file_path, start_time)

        return ProcessingResult(
            success=False,
            processor_name=self.processor_name,
            error_message=f"Unsupported document type: {mime_type}",
        )

    async def _process_text_file(self, file_path: Path, start_time: float) -> ProcessingResult:
        """Process plain text or markdown files."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Local processing - no cost
            cost_info = calculate_processing_cost("text_reader", "local")

            return ProcessingResult(
                success=True,
                content=content,
                content_format="text" if not file_path.suffix == ".md" else "markdown",
                processor_name="text_reader",
                processing_time_ms=processing_time_ms,
                confidence_score=100,
                cost_input_usd=cost_info["input_cost_usd"],
                cost_output_usd=cost_info["output_cost_usd"],
                cost_total_usd=cost_info["total_cost_usd"],
                pricing_model=cost_info["pricing_model"],
            )
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            return ProcessingResult(
                success=False,
                processor_name="text_reader",
                error_message=str(e),
            )

    async def _process_pdf(self, file_path: Path, use_gemini_fallback: bool, start_time: float) -> ProcessingResult:
        """Process PDF files using PyMuPDF with optional Gemini fallback."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return ProcessingResult(
                success=False,
                processor_name=self.processor_name,
                error_message="PyMuPDF not installed. Run: pip install pymupdf",
            )

        try:
            doc = fitz.open(file_path)
            text_parts = []
            total_pages = len(doc)

            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            doc.close()

            extracted_text = "\n\n".join(text_parts)
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Check if we got meaningful text
            if len(extracted_text.strip()) >= self.MIN_TEXT_LENGTH:
                logger.info(f"PyMuPDF extracted {len(extracted_text)} chars from {total_pages} pages")
                # Local processing - no cost
                cost_info = calculate_processing_cost("pymupdf", "local")
                return ProcessingResult(
                    success=True,
                    content=extracted_text,
                    content_format="text",
                    processor_name="pymupdf",
                    processing_time_ms=processing_time_ms,
                    confidence_score=95,
                    cost_input_usd=cost_info["input_cost_usd"],
                    cost_output_usd=cost_info["output_cost_usd"],
                    cost_total_usd=cost_info["total_cost_usd"],
                    pricing_model=cost_info["pricing_model"],
                )

            # Text extraction yielded little content - likely a scanned PDF
            if use_gemini_fallback:
                logger.info(f"PDF appears to be scanned ({len(extracted_text)} chars), using Gemini fallback")
                return await self._process_pdf_with_gemini(file_path, total_pages, start_time)
            else:
                # Return what we have even if minimal
                cost_info = calculate_processing_cost("pymupdf", "local")
                return ProcessingResult(
                    success=True,
                    content=extracted_text or "[No text content extracted from PDF]",
                    content_format="text",
                    processor_name="pymupdf",
                    processing_time_ms=processing_time_ms,
                    confidence_score=30,  # Low confidence for minimal extraction
                    cost_input_usd=cost_info["input_cost_usd"],
                    cost_output_usd=cost_info["output_cost_usd"],
                    cost_total_usd=cost_info["total_cost_usd"],
                    pricing_model=cost_info["pricing_model"],
                )

        except Exception as e:
            logger.error(f"PyMuPDF error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="pymupdf",
                error_message=str(e),
            )

    async def _process_pdf_with_gemini(self, file_path: Path, total_pages: int, start_time: float) -> ProcessingResult:
        """Process scanned PDF using Gemini vision."""
        model = self._get_gemini_model()
        if not model:
            return ProcessingResult(
                success=False,
                processor_name="gemini_vision",
                error_message="Gemini not configured for scanned PDF processing",
            )

        try:
            import fitz  # PyMuPDF for rendering pages as images

            doc = fitz.open(file_path)
            all_text_parts = []

            # Track cumulative token usage across all pages
            total_input_tokens = 0
            total_output_tokens = 0

            # Process each page as an image
            for page_num in range(min(total_pages, 20)):  # Limit to 20 pages
                page = doc[page_num]

                # Render page to image at 150 DPI (good balance of quality/size)
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")

                # Send to Gemini
                image_part = {
                    "mime_type": "image/png",
                    "data": img_data,
                }

                response = model.generate_content(
                    [
                        f"Page {page_num + 1} of {total_pages}. {self.GEMINI_PROMPT}",
                        image_part,
                    ]
                )

                if response and response.text:
                    all_text_parts.append(f"--- Page {page_num + 1} ---\n{response.text.strip()}")

                    # Accumulate token usage
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        usage = response.usage_metadata
                        total_input_tokens += getattr(usage, "prompt_token_count", 0) or 0
                        total_output_tokens += getattr(usage, "candidates_token_count", 0) or 0

            doc.close()

            if all_text_parts:
                full_text = "\n\n".join(all_text_parts)
                processing_time_ms = int((time.time() - start_time) * 1000)

                # Calculate cost based on accumulated tokens
                cost_info = calculate_processing_cost(
                    processor_name="gemini_vision",
                    model=self.gemini_model,
                    input_tokens=total_input_tokens if total_input_tokens > 0 else None,
                    output_tokens=total_output_tokens if total_output_tokens > 0 else None,
                )

                cost_str = f"${float(cost_info['total_cost_usd']):.6f}" if cost_info["total_cost_usd"] else "N/A"
                logger.info(
                    f"Gemini PDF extraction: {len(all_text_parts)} pages, "
                    f"tokens: {total_input_tokens + total_output_tokens}, cost: {cost_str}"
                )

                return ProcessingResult(
                    success=True,
                    content=full_text,
                    content_format="markdown",
                    processor_name="gemini_vision",
                    processor_model=self.gemini_model,
                    processing_time_ms=processing_time_ms,
                    confidence_score=85,
                    input_tokens=total_input_tokens if total_input_tokens > 0 else None,
                    output_tokens=total_output_tokens if total_output_tokens > 0 else None,
                    total_tokens=(total_input_tokens + total_output_tokens)
                    if (total_input_tokens + total_output_tokens) > 0
                    else None,
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
                    processor_model=self.gemini_model,
                    error_message="No text extracted from scanned PDF pages",
                )

        except Exception as e:
            logger.error(f"Gemini PDF processing error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="gemini_vision",
                processor_model=self.gemini_model,
                error_message=str(e),
            )

    async def _process_word(self, file_path: Path, start_time: float) -> ProcessingResult:
        """Process Word documents using python-docx."""
        try:
            from docx import Document
        except ImportError:
            # Fallback: try to extract with basic approach
            return ProcessingResult(
                success=False,
                processor_name="python_docx",
                error_message="python-docx not installed. Run: pip install python-docx",
            )

        try:
            doc = Document(file_path)
            paragraphs = []

            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)

            content = "\n\n".join(paragraphs)
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Local processing - no cost
            cost_info = calculate_processing_cost("python_docx", "local")

            return ProcessingResult(
                success=True,
                content=content,
                content_format="text",
                processor_name="python_docx",
                processing_time_ms=processing_time_ms,
                confidence_score=90,
                cost_input_usd=cost_info["input_cost_usd"],
                cost_output_usd=cost_info["output_cost_usd"],
                cost_total_usd=cost_info["total_cost_usd"],
                pricing_model=cost_info["pricing_model"],
            )

        except Exception as e:
            logger.error(f"Word document processing error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                processor_name="python_docx",
                error_message=str(e),
            )
