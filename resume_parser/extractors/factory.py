"""Factory for selecting the appropriate text extractor."""

from __future__ import annotations

from pathlib import Path

from resume_parser.exceptions import UnsupportedFormatError
from resume_parser.extractors.base import BaseTextExtractor
from resume_parser.extractors.doc_extractor import DocTextExtractor
from resume_parser.extractors.docx_extractor import DocxTextExtractor
from resume_parser.extractors.pdf_extractor import PdfTextExtractor
from resume_parser.utils.constants import SUPPORTED_EXTENSIONS


class TextExtractorFactory:
    """Create text extractors based on file extension."""

    _EXTRACTORS: dict[str, type[BaseTextExtractor]] = {
        ".pdf": PdfTextExtractor,
        ".doc": DocTextExtractor,
        ".docx": DocxTextExtractor,
    }

    @classmethod
    def get_extractor(cls, extension: str) -> BaseTextExtractor:
        normalized = extension.lower()
        if not normalized.startswith("."):
            normalized = f".{normalized}"

        extractor_class = cls._EXTRACTORS.get(normalized)
        if extractor_class is None:
            raise UnsupportedFormatError(
                normalized, sorted(SUPPORTED_EXTENSIONS)
            )
        return extractor_class()

    @classmethod
    def resolve_extension(cls, file_path: Path | None, extension: str | None) -> str:
        if extension:
            normalized = extension.lower()
            return normalized if normalized.startswith(".") else f".{normalized}"
        if file_path is None:
            raise UnsupportedFormatError("unknown", sorted(SUPPORTED_EXTENSIONS))
        return file_path.suffix.lower()
