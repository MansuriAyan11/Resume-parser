"""Resume Parser - production-ready resume extraction module."""

from resume_parser.exceptions import (
    EmptyDocumentError,
    ResumeParserError,
    TextExtractionError,
    UnsupportedFormatError,
)
from resume_parser.models.schemas import ParsedResume
from resume_parser.parser import ResumeParser, parse_resume, parse_resume_bytes

__all__ = [
    "ResumeParser",
    "parse_resume",
    "parse_resume_bytes",
    "ParsedResume",
    "ResumeParserError",
    "UnsupportedFormatError",
    "TextExtractionError",
    "EmptyDocumentError",
]

__version__ = "1.0.0"
