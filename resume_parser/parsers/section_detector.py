"""Detect resume sections from extracted plain text."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from resume_parser.utils.constants import (
    EDUCATION_SECTION_HEADERS,
    EXPERIENCE_SECTION_HEADERS,
    LANGUAGES_SECTION_HEADERS,
    OTHER_SECTION_HEADERS,
    SKILLS_SECTION_HEADERS,
)
from resume_parser.utils.text_utils import clean_line, is_likely_header, split_lines

logger = logging.getLogger(__name__)


class SectionType(str, Enum):
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    LANGUAGES = "languages"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectedSection:
    section_type: SectionType
    header: str
    content: str
    start_line: int
    end_line: int


class SectionDetector:
    """Split resume text into logical sections."""

    _HEADER_GROUPS: dict[SectionType, tuple[str, ...]] = {
        SectionType.EXPERIENCE: EXPERIENCE_SECTION_HEADERS,
        SectionType.EDUCATION: EDUCATION_SECTION_HEADERS,
        SectionType.SKILLS: SKILLS_SECTION_HEADERS,
        SectionType.LANGUAGES: LANGUAGES_SECTION_HEADERS,
        SectionType.OTHER: OTHER_SECTION_HEADERS,
    }

    def detect(self, text: str) -> list[DetectedSection]:
        raw_lines = split_lines(text)
        if not raw_lines:
            return []

        header_prefixes = (
            r"computer\s+skills?", r"technical\s+skills?", r"key\s+skills?",
            r"skills?", r"language\s+skills?", r"education",
            r"work\s+experience", r"professional\s+experience", r"work\s+history",
            r"employment\s+history", r"professional\s+affiliations?",
            r"references?", r"objective", r"summary", r"profile", r"added\s+value"
        )
        pattern = rf"^({'|'.join(header_prefixes)})\s*:\s*(.+)$"
        
        lines = []
        for line in raw_lines:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                header_part = match.group(1).strip()
                content_part = match.group(2).strip()
                lines.append(header_part)
                if content_part:
                    lines.append(content_part)
            else:
                lines.append(line)

        header_indices: list[tuple[int, SectionType, str]] = []
        for index, line in enumerate(lines):
            section_type, header = self._classify_header(line)
            if section_type != SectionType.UNKNOWN:
                header_indices.append((index, section_type, header))
                logger.debug("Detected section '%s' at line %d", header, index)

        if not header_indices:
            logger.warning("No explicit sections detected; using full-text fallback")
            return [
                DetectedSection(
                    section_type=SectionType.UNKNOWN,
                    header="",
                    content=text,
                    start_line=0,
                    end_line=len(lines) - 1,
                )
            ]

        sections: list[DetectedSection] = []
        for idx, (start_index, section_type, header) in enumerate(header_indices):
            end_index = (
                header_indices[idx + 1][0] - 1
                if idx + 1 < len(header_indices)
                else len(lines) - 1
            )
            content_lines = lines[start_index + 1 : end_index + 1]
            content = "\n".join(content_lines).strip()
            sections.append(
                DetectedSection(
                    section_type=section_type,
                    header=header,
                    content=content,
                    start_line=start_index,
                    end_line=end_index,
                )
            )

        return sections

    def get_content(self, sections: list[DetectedSection], section_type: SectionType) -> str:
        parts = []
        for section in sections:
            if section.section_type == section_type:
                content = section.content
                if not content or len(content.split()) < 3:
                    content = (section.header + "\n" + content).strip()
                parts.append(content)
        return "\n".join(parts).strip()

    def _classify_header(self, line: str) -> tuple[SectionType, str]:
        normalized = clean_line(line).rstrip(":").strip()
        if not normalized or not normalized[0].isupper():
            return SectionType.UNKNOWN, ""

        compact = re.sub(r"[^\w\s]", " ", normalized).strip()
        compact_lower = re.sub(r"\s+", " ", compact).lower()

        # Explicitly classify as OTHER if it contains any of the non-experience words and is a short line
        non_exp_patterns = (
            r"\bprofessional\s+affiliations?\b",
            r"\bprofessional\s+memberships?\b",
            r"\bhonors?\b",
            r"\bawards?\b",
            r"\bactivities\b",
            r"\bleadership\b",
            r"\bcommunity\s+service\b",
            r"\bvolunteer(?:\s+activities?)?\b",
            r"\breferences?\b",
            r"\bobjective\b",
            r"\bsummary\b",
            r"\bprofile\b",
            r"\baffiliations?\b",
            r"\bmemberships?\b",
            r"\bvolunteer\b",
        )
        if len(compact_lower.split()) <= 6 and any(re.search(pat, compact_lower, re.IGNORECASE) for pat in non_exp_patterns):
            return SectionType.OTHER, normalized

        # Explicitly classify as SKILLS if it is a short line containing "skills", "knowledge", "technologies", "tech"
        if len(compact_lower.split()) <= 6 and any(re.search(rf"\b{word}\b", compact_lower) for word in ("skills", "knowledge", "technologies", "tech")):
            if "language" in compact_lower:
                return SectionType.LANGUAGES, normalized
            return SectionType.SKILLS, normalized

        for section_type, patterns in self._HEADER_GROUPS.items():
            for pattern in patterns:
                regex = rf"^{pattern}$"
                if re.match(regex, compact_lower, re.IGNORECASE):
                    return section_type, normalized

        if is_likely_header(normalized):
            # Prioritize OTHER if it is a generic summary/profile/objective block
            is_experience_summary = any(
                re.search(rf"\b{pat}\b", compact_lower, re.IGNORECASE)
                for pat in (r"career\s+summary", r"experience\s+summary", r"work\s+summary")
            )
            if not is_experience_summary:
                if any(re.search(rf"\b{word}\b", compact_lower, re.IGNORECASE) for word in ("summary", "profile", "objective")):
                    return SectionType.OTHER, normalized

            for section_type, patterns in self._HEADER_GROUPS.items():
                for pattern in patterns:
                    if re.search(rf"\b{pattern}\b", compact_lower, re.IGNORECASE):
                        return section_type, normalized

        return SectionType.UNKNOWN, ""
