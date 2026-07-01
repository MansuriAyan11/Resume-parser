"""Main resume parser orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

from resume_parser.exceptions import EmptyDocumentError, UnsupportedFormatError
from resume_parser.extractors.factory import TextExtractorFactory
from resume_parser.models.schemas import ParsedResume, empty_parsed_resume, parsed_resume_to_dict
from resume_parser.parsers.education_parser import EducationParser
from resume_parser.parsers.experience_parser import ExperienceParser
from resume_parser.parsers.languages_parser import LanguagesParser
from resume_parser.parsers.section_detector import SectionDetector, SectionType
from resume_parser.parsers.skills_parser import SkillsParser
from resume_parser.utils.constants import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class ResumeParser:
    """
    Production resume parser.

    Accepts PDF, DOC, and DOCX files and returns structured JSON-compatible output.
    """

    def __init__(self) -> None:
        self._section_detector = SectionDetector()
        self._experience_parser = ExperienceParser()
        self._education_parser = EducationParser()
        self._skills_parser = SkillsParser()
        self._languages_parser = LanguagesParser()

    def parse_file(self, file_path: str | Path) -> dict:
        """
        Parse a resume file from disk.

        Args:
            file_path: Path to a PDF, DOC, or DOCX resume.

        Returns:
            JSON-compatible dictionary with experience, education, skills, languages.
        """
        path = Path(file_path)
        logger.info("Parsing resume file: %s", path)

        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {path}")

        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(extension, sorted(SUPPORTED_EXTENSIONS))

        extractor = TextExtractorFactory.get_extractor(extension)
        text = extractor.extract_from_path(path)

        if not text.strip():
            raise EmptyDocumentError()

        result = self._parse_text(text)
        logger.info(
            "Parsing complete: %d experience, %d education, %d skills, %d languages",
            len(result["experience"]),
            len(result["education"]),
            len(result["skills"]),
            len(result["languages"]),
        )
        return parsed_resume_to_dict(result)

    def parse_bytes(self, content: bytes, extension: str) -> dict:
        """
        Parse a resume from raw bytes.

        Args:
            content: Raw file bytes.
            extension: File extension including dot (e.g. '.pdf').

        Returns:
            JSON-compatible dictionary.
        """
        normalized_extension = extension.lower()
        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        if normalized_extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(normalized_extension, sorted(SUPPORTED_EXTENSIONS))

        logger.info("Parsing resume bytes (%d bytes, %s)", len(content), normalized_extension)

        extractor = TextExtractorFactory.get_extractor(normalized_extension)
        text = extractor.extract_from_bytes(content, normalized_extension)

        if not text.strip():
            raise EmptyDocumentError()

        result = self._parse_text(text)
        return parsed_resume_to_dict(result)

    def parse_upload(self, upload: BinaryIO, filename: str) -> dict:
        """
        Parse a resume from a file-like upload object.

        Designed for integration with web frameworks (FastAPI UploadFile, Django File, etc.).

        Args:
            upload: Binary file-like object.
            filename: Original filename used to determine format.

        Returns:
            JSON-compatible dictionary.
        """
        extension = Path(filename).suffix.lower()
        content = upload.read()
        return self.parse_bytes(content, extension)

    def _parse_text(self, text: str) -> ParsedResume:
        sections = self._section_detector.detect(text)

        experience_text = self._section_detector.get_content(sections, SectionType.EXPERIENCE)
        education_text = self._section_detector.get_content(sections, SectionType.EDUCATION)
        skills_text = self._section_detector.get_content(sections, SectionType.SKILLS)
        languages_text = self._section_detector.get_content(sections, SectionType.LANGUAGES)

        if not experience_text and not education_text:
            experience_text, education_text = self._fallback_full_text_parse(text)

        if not skills_text:
            skills_text = self._fallback_section_text(text, ("skills", "technical skills"))

        if not languages_text:
            languages_text = self._fallback_section_text(text, ("language", "languages"))

        result = empty_parsed_resume()
        result["experience"] = self._experience_parser.parse(experience_text)
        result["education"] = self._education_parser.parse(education_text)
        result["skills"] = self._skills_parser.parse(skills_text)
        result["languages"] = self._languages_parser.parse(languages_text)
        return result

    def _fallback_full_text_parse(self, text: str) -> tuple[str, str]:
        """When sections are not detected, attempt keyword-based splitting."""
        lower = text.lower()
        split_keywords = [
            "education",
            "academic",
            "qualification",
            "skills",
            "technical skills",
        ]

        experience_text = text
        education_text = ""

        for keyword in split_keywords:
            index = lower.find(keyword)
            if index > 0:
                experience_text = text[:index]
                education_text = text[index:]
                break

        return experience_text.strip(), education_text.strip()

    def _fallback_section_text(self, text: str, keywords: tuple[str, ...]) -> str:
        """Extract a section by keyword when headers were not detected."""
        lower = text.lower()
        for keyword in keywords:
            start = lower.find(keyword)
            if start < 0:
                continue

            section_start = start + len(keyword)
            while section_start < len(text) and text[section_start] in ": \t":
                section_start += 1

            end = len(text)
            for other in (
                "experience",
                "education",
                "skills",
                "languages",
                "projects",
                "certifications",
                "references",
            ):
                if other == keyword or other.startswith(keyword.split()[0]):
                    continue
                other_index = lower.find(other, section_start)
                if other_index > section_start:
                    end = min(end, other_index)

            return text[section_start:end].strip()
        return ""


def parse_resume(file_path: str | Path) -> dict:
    """Convenience function to parse a resume file."""
    return ResumeParser().parse_file(file_path)


def parse_resume_bytes(content: bytes, extension: str) -> dict:
    """Convenience function to parse resume bytes."""
    return ResumeParser().parse_bytes(content, extension)
