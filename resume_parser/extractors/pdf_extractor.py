"""PDF text extraction using PyMuPDF."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz

from resume_parser.exceptions import TextExtractionError
from resume_parser.extractors.base import BaseTextExtractor
from resume_parser.utils.text_utils import normalize_whitespace

logger = logging.getLogger(__name__)


class PdfTextExtractor(BaseTextExtractor):
    """Extract text from PDF resume files."""

    def extract_from_path(self, file_path: Path) -> str:
        logger.debug("Extracting text from PDF: %s", file_path)
        try:
            with fitz.open(file_path) as document:
                return self._extract_from_document(document)
        except Exception as exc:
            logger.exception("PDF extraction failed for %s", file_path)
            raise TextExtractionError(
                f"Could not extract text from PDF '{file_path.name}'", cause=exc
            ) from exc

    def extract_from_bytes(self, content: bytes, extension: str) -> str:
        logger.debug("Extracting text from PDF bytes (%d bytes)", len(content))
        try:
            with fitz.open(stream=content, filetype="pdf") as document:
                return self._extract_from_document(document)
        except Exception as exc:
            logger.exception("PDF byte extraction failed")
            raise TextExtractionError("Could not extract text from PDF bytes", cause=exc) from exc

    def _extract_from_document(self, document: fitz.Document) -> str:
        pages: list[str] = []
        for page_index, page in enumerate(document):
            page_text = page.get_text("text")
            if page_text.strip():
                pages.append(page_text)
            logger.debug("Extracted page %d (%d chars)", page_index + 1, len(page_text))

        combined = "\n".join(pages)
        try:
            return normalize_whitespace(self._validate_text(combined))
        except ValueError as exc:
            raise TextExtractionError("PDF contains no extractable text", cause=exc) from exc
