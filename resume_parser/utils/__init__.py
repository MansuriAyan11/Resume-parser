"""Utility helpers for the resume parser."""

from resume_parser.utils.constants import SUPPORTED_EXTENSIONS
from resume_parser.utils.date_utils import (
    extract_years,
    is_current_date_token,
    normalize_date,
    parse_date_range,
)
from resume_parser.utils.text_utils import (
    clean_line,
    deduplicate_preserve_order,
    is_likely_header,
    normalize_whitespace,
    split_lines,
    truncate_text,
)

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "clean_line",
    "deduplicate_preserve_order",
    "extract_years",
    "is_current_date_token",
    "is_likely_header",
    "normalize_date",
    "normalize_whitespace",
    "parse_date_range",
    "split_lines",
    "truncate_text",
]
