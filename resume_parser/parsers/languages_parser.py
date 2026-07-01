"""Parse languages from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.utils.constants import LANGUAGE_PROFICIENCY_KEYWORDS
from resume_parser.utils.text_utils import clean_line, deduplicate_preserve_order, split_lines

logger = logging.getLogger(__name__)

COMMON_LANGUAGES = (
    "english",
    "hindi",
    "spanish",
    "french",
    "german",
    "mandarin",
    "chinese",
    "japanese",
    "korean",
    "arabic",
    "portuguese",
    "russian",
    "italian",
    "bengali",
    "tamil",
    "telugu",
    "marathi",
    "gujarati",
    "kannada",
    "malayalam",
    "punjabi",
    "urdu",
    "dutch",
    "swedish",
    "polish",
    "turkish",
    "vietnamese",
    "thai",
    "indonesian",
)

LANGUAGE_NOISE_PATTERNS = (
    r"^languages?:?$",
    r"^language\s+proficiency$",
    r"^language\s+skills?:?$",
)


class LanguagesParser:
    """Extract spoken/written languages from a languages section."""

    def parse(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        languages: list[str] = []
        lines = split_lines(text)

        for line in lines:
            if self._is_noise_line(line):
                continue

            if self._is_bullet_line(line) or self._has_delimiters(line):
                languages.extend(self._parse_line(line))
            else:
                languages.extend(self._parse_line(line))

        cleaned = deduplicate_preserve_order(
            [lang for lang in (self._normalize_language(l) for l in languages) if lang]
        )

        logger.info("Parsed %d languages", len(cleaned))
        return cleaned

    def _parse_line(self, line: str) -> list[str]:
        stripped = re.sub(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]+\s*", "", line)
        parts = re.split(r"[,|;/•·]+", stripped)
        results: list[str] = []

        for part in parts:
            cleaned = clean_line(part)
            if not cleaned:
                continue

            known = self._match_known_language(cleaned)
            if known:
                results.append(known)
                continue

            generic = self._extract_language_before_proficiency(cleaned)
            if generic:
                results.append(generic)

        return results

    def _match_known_language(self, text: str) -> str | None:
        lower = text.lower()
        for language in COMMON_LANGUAGES:
            if re.search(rf"\b{re.escape(language)}\b", lower):
                return language.title()
        return None

    def _extract_language_before_proficiency(self, text: str) -> str | None:
        lower = text.lower()
        for keyword in LANGUAGE_PROFICIENCY_KEYWORDS:
            if keyword in lower:
                language_part = lower.split(keyword)[0].strip(" :-(")
                language_part = re.sub(
                    r"^(?:language|languages)\s*[:\-]?\s*",
                    "",
                    language_part,
                    flags=re.IGNORECASE,
                )
                if language_part and len(language_part) <= 30:
                    return language_part.title()

        if len(text.split()) <= 3 and text.replace("-", "").isalpha():
            title_text = text.title()
            if title_text.lower() in COMMON_LANGUAGES:
                return title_text
            return None

        return None

    def _normalize_language(self, language: str) -> str | None:
        language = clean_line(language)
        language = re.sub(
            r"^(?:language|languages)\s*[:\-]\s*",
            "",
            language,
            flags=re.IGNORECASE,
        )
        for keyword in LANGUAGE_PROFICIENCY_KEYWORDS:
            language = re.sub(
                rf"\s*[\(\-]?\s*{re.escape(keyword)}\s*[\)]?",
                "",
                language,
                flags=re.IGNORECASE,
            )
        language = language.strip(" .:-")
        if not language or len(language) < 2:
            return None
        return language.title()

    def _is_bullet_line(self, line: str) -> bool:
        return bool(re.match(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]", line.strip()))

    def _has_delimiters(self, line: str) -> bool:
        return bool(re.search(r"[,|;/•·]", line))

    def _is_noise_line(self, line: str) -> bool:
        return any(
            re.match(pattern, line.strip(), re.IGNORECASE)
            for pattern in LANGUAGE_NOISE_PATTERNS
        )
