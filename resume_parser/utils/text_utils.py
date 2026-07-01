"""Text normalization and cleaning utilities."""

from __future__ import annotations

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to a consistent form."""
    return unicodedata.normalize("NFKC", text)


def normalize_whitespace(text: str) -> str:
    """Collapse excessive whitespace while preserving line structure."""
    text = normalize_unicode(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_line(line: str) -> str:
    """Clean a single line of text."""
    line = normalize_unicode(line)
    line = re.sub(r"[\t ]+", " ", line)
    line = re.sub(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|\uf0b7\uf0a7\uf0d8]+\s*", "", line)
    return line.strip()


def split_lines(text: str) -> list[str]:
    """Split text into cleaned non-empty lines."""
    return [clean_line(line) for line in text.split("\n") if clean_line(line)]


def is_likely_header(line: str) -> bool:
    """Heuristic check if a line is a section header."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if stripped.endswith(":"):
        return True
    alpha_chars = sum(ch.isalpha() for ch in stripped)
    if alpha_chars == 0:
        return False
    upper_ratio = sum(ch.isupper() for ch in stripped if ch.isalpha()) / alpha_chars
    if upper_ratio > 0.7 and len(stripped.split()) <= 6:
        return True
    if stripped.isupper() and len(stripped.split()) <= 6:
        return True
    return False


def deduplicate_preserve_order(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def truncate_text(text: str | None, max_length: int = 500) -> str | None:
    """Truncate long text fields."""
    if text is None:
        return None
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned or None
    return cleaned[: max_length - 3].rstrip() + "..."
