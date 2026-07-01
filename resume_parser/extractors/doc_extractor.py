"""Legacy DOC text extraction with multiple fallback strategies."""

from __future__ import annotations

import io
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import olefile

from resume_parser.exceptions import TextExtractionError
from resume_parser.extractors.base import BaseTextExtractor
from resume_parser.extractors.docx_extractor import DocxTextExtractor
from resume_parser.utils.text_utils import normalize_whitespace

logger = logging.getLogger(__name__)


class DocTextExtractor(BaseTextExtractor):
    """Extract text from legacy Microsoft Word .doc files."""

    def __init__(self) -> None:
        self._docx_extractor = DocxTextExtractor()

    def extract_from_path(self, file_path: Path) -> str:
        logger.debug("Extracting text from DOC: %s", file_path)
        content = file_path.read_bytes()
        return self.extract_from_bytes(content, ".doc")

    def extract_from_bytes(self, content: bytes, extension: str) -> str:
        logger.debug("Extracting text from DOC bytes (%d bytes)", len(content))

        strategies = (
            self._try_as_docx,
            self._try_antiword,
            self._try_ole_extraction,
            self._try_binary_text_scan,
        )

        errors: list[str] = []
        for strategy in strategies:
            try:
                text = strategy(content)
                if text and text.strip():
                    return normalize_whitespace(text)
            except Exception as exc:
                message = f"{strategy.__name__}: {exc}"
                logger.debug(message)
                errors.append(message)

        detail = "; ".join(errors) if errors else "all strategies failed"
        raise TextExtractionError(f"Could not extract text from DOC file ({detail})")

    def _try_as_docx(self, content: bytes) -> str:
        """Some .doc files are mislabeled DOCX packages."""
        return self._docx_extractor.extract_from_bytes(content, ".docx")

    def _try_antiword(self, content: bytes) -> str:
        """Use antiword CLI if available on the system."""
        antiword = shutil.which("antiword")
        if not antiword:
            raise TextExtractionError("antiword not installed")

        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)

        try:
            result = subprocess.run(
                [antiword, str(temp_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0 or not result.stdout.strip():
                raise TextExtractionError(
                    f"antiword failed with code {result.returncode}"
                )
            return result.stdout
        finally:
            temp_path.unlink(missing_ok=True)

    def _try_ole_extraction(self, content: bytes) -> str:
        """Extract readable text from OLE WordDocument stream."""
        if not olefile.isOleFile(io.BytesIO(content)):
            raise TextExtractionError("Not a valid OLE compound document")

        ole = olefile.OleFileIO(io.BytesIO(content))
        try:
            if not ole.exists("WordDocument"):
                raise TextExtractionError("WordDocument stream not found")

            word_stream = ole.openstream("WordDocument").read()
            text = self._decode_word_binary_stream(word_stream)
            return self._validate_text(text)
        finally:
            ole.close()

    def _try_binary_text_scan(self, content: bytes) -> str:
        """Last-resort extraction of printable sequences from binary content."""
        utf16_chunks = re.findall(
            r"(?:[\u0020-\u007E\u00A0-\u024F]{4,}(?:\s[\u0020-\u007E\u00A0-\u024F]{2,})*)",
            content.decode("utf-16-le", errors="ignore"),
        )
        ascii_chunks = re.findall(
            rb"[\x20-\x7E]{4,}(?:\s[\x20-\x7E]{2,})*",
            content,
        )
        ascii_text = [chunk.decode("ascii", errors="ignore") for chunk in ascii_chunks]

        combined = "\n".join(utf16_chunks + ascii_text)
        return self._validate_text(combined)

    def _decode_word_binary_stream(self, data: bytes) -> str:
        """Decode text fragments from Word binary stream."""
        candidates: list[str] = []

        ascii_runs = re.findall(rb"[\x09\x0A\x0D\x20-\x7E]{5,}", data)
        candidates.extend(run.decode("ascii", errors="ignore") for run in ascii_runs)

        utf16_runs = re.findall(
            rb"(?:[\x20-\x7E\x00]){10,}",
            data,
        )
        for run in utf16_runs:
            try:
                decoded = run.decode("utf-16-le", errors="ignore")
                if decoded.strip():
                    candidates.append(decoded)
            except UnicodeDecodeError:
                continue

        if not candidates:
            raise TextExtractionError("No readable text in WordDocument stream")

        cleaned = [re.sub(r"\s+", " ", c).strip() for c in candidates if len(c.strip()) > 3]
        return "\n".join(dict.fromkeys(cleaned))
