"""Abstract base class for document text extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTextExtractor(ABC):
    """Extract plain text from a resume document."""

    @abstractmethod
    def extract_from_path(self, file_path: Path) -> str:
        """Extract text from a file on disk."""

    @abstractmethod
    def extract_from_bytes(self, content: bytes, extension: str) -> str:
        """Extract text from raw file bytes."""

    def _validate_text(self, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("No text content found")
        return text
