"""Date parsing and normalization utilities."""

from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as date_parser

from resume_parser.utils.constants import CURRENT_KEYWORDS, DATE_RANGE_PATTERN, YEAR_PATTERN


def is_current_date_token(token: str) -> bool:
    """Check if a date token indicates an ongoing role."""
    normalized = token.strip().lower()
    if not normalized:
        return False
    if normalized in CURRENT_KEYWORDS:
        return True
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", normalized)
        for keyword in CURRENT_KEYWORDS
    )


def normalize_date(value: str | None) -> str | None:
    """
    Normalize a date string to ISO-like format (YYYY-MM or YYYY).

    Returns None if parsing fails.
    """
    if not value:
        return None

    cleaned = value.strip()
    if not cleaned or is_current_date_token(cleaned):
        return None

    # Check if a year is present in the input to avoid default-year leakages from date_parser.parse
    year_match = YEAR_PATTERN.search(cleaned)
    if not year_match:
        return None

    # Exact 4-character digit year (or exact 4-character placeholder year e.g. 20xx)
    if len(cleaned) == 4 and (cleaned.isdigit() or re.match(r"^(?:19|20)[xX]{2}$", cleaned)):
        return cleaned

    # Support placeholder year (e.g. 20xx, June 20xx) by temporarily converting it to standard numbers
    placeholder_match = re.search(r"\b(19|20)([xX]{2})\b", cleaned)
    has_placeholder = False
    cleaned_for_parse = cleaned
    if placeholder_match:
        has_placeholder = True
        placeholder_prefix = placeholder_match.group(1)
        placeholder_suffix = placeholder_match.group(2)
        cleaned_for_parse = (
            cleaned[:placeholder_match.start()]
            + placeholder_prefix
            + "00"
            + cleaned[placeholder_match.end():]
        )

    try:
        parsed = date_parser.parse(cleaned_for_parse, fuzzy=True, default=datetime(2000, 1, 1))
        if parsed.year < 1950 or parsed.year > 2035:
            return year_match.group(0)

        has_month = bool(re.search(
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
            cleaned,
            re.IGNORECASE,
        ))

        if has_placeholder:
            year_str = f"{placeholder_prefix}{placeholder_suffix}"
            if has_month:
                return f"{year_str}-{parsed.strftime('%m')}"
            return year_str

        if has_month:
            return parsed.strftime("%Y-%m")
        return str(parsed.year)
    except (ValueError, OverflowError, TypeError):
        return year_match.group(0)


def extract_years(text: str) -> list[str]:
    """Extract all four-digit years from text."""
    return YEAR_PATTERN.findall(text) if text else []


def parse_date_range(text: str) -> tuple[str | None, str | None, bool]:
    """
    Parse a date range from text.

    Returns (start_date, end_date, is_current).
    """
    if not text:
        return None, None, False

    lower = text.lower()
    is_current = is_current_date_token(lower) or any(
        re.search(rf"\b{re.escape(keyword)}\b", lower) for keyword in CURRENT_KEYWORDS
    )

    range_match = DATE_RANGE_PATTERN.search(text)
    if range_match:
        if range_match.group("start"):
            start = normalize_date(range_match.group("start"))
            end_token = range_match.group("end")
            if end_token and is_current_date_token(end_token):
                return start, None, True
            end = normalize_date(end_token) if end_token else None
            return start, end, False

        single = normalize_date(range_match.group("single"))
        if single:
            return single, None, is_current

    years = YEAR_PATTERN.findall(text)
    unique_years = sorted(set(years))
    if len(unique_years) >= 2:
        return unique_years[0], unique_years[-1], is_current
    if len(unique_years) == 1:
        if is_current:
            return unique_years[0], None, True
        return unique_years[0], unique_years[0], False

    single = normalize_date(text)
    if single:
        return single, None, is_current
    return None, None, is_current
