"""Custom exceptions for the resume parser module."""


class ResumeParserError(Exception):
    """Base exception for all resume parser errors."""


class UnsupportedFormatError(ResumeParserError):
    """Raised when the input file format is not supported."""

    def __init__(self, extension: str, supported: list[str]) -> None:
        self.extension = extension
        self.supported = supported
        super().__init__(
            f"Unsupported file format '{extension}'. "
            f"Supported formats: {', '.join(supported)}"
        )


class TextExtractionError(ResumeParserError):
    """Raised when text cannot be extracted from a document."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        detail = f": {cause}" if cause else ""
        super().__init__(f"Failed to extract text from document{detail}")


class EmptyDocumentError(ResumeParserError):
    """Raised when a document contains no extractable text."""

    def __init__(self) -> None:
        super().__init__("Document contains no extractable text")
