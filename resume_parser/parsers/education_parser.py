"""Parse education entries from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.models.schemas import EducationEntry, empty_education_entry
from resume_parser.utils.constants import CLASS_NAME_PATTERNS, DEGREE_PATTERNS, DATE_RANGE_PATTERN
from resume_parser.utils.date_utils import extract_years, parse_date_range
from resume_parser.utils.text_utils import clean_line, split_lines

logger = logging.getLogger(__name__)

INSTITUTION_KEYWORDS = (
    "university",
    "college",
    "institute",
    "school",
    "academy",
    "polytechnic",
    "iit",
    "nit",
    "bits",
)


class EducationParser:
    """Extract structured education records from section text."""

    def parse(self, text: str) -> list[EducationEntry]:
        if not text or not text.strip():
            return []

        blocks = self._split_into_blocks(text)
        entries: list[EducationEntry] = []

        for block in blocks:
            entry = self._parse_block(block)
            if self._is_valid_entry(entry):
                entries.append(entry)

        logger.info("Parsed %d education entries", len(entries))
        return entries

    def _split_into_blocks(self, text: str) -> list[str]:
        lines = split_lines(text)
        if not lines:
            return []

        # Filter out page headers, footer text, and sample labels
        cleaned_lines = []
        for line in lines:
            lower = line.lower()
            if "im a. sample" in lower or "page " in lower or "revision:" in lower or "resume sample" in lower or lower == "continued":
                continue
            cleaned_lines.append(line)
        lines = cleaned_lines

        blocks: list[list[str]] = []
        current: list[str] = []

        for line in lines:
            if self._is_block_boundary(line, current):
                if current:
                    blocks.append(current)
                current = [line]
            else:
                current.append(line)

        if current:
            blocks.append(current)

        if len(blocks) == 1:
            return [text.strip()]

        return ["\n".join(block) for block in blocks if block]

    def _is_block_boundary(self, line: str, current: list[str]) -> bool:
        if not current:
            return False
        if self._contains_degree(line):
            if any(self._contains_degree(entry) for entry in current):
                return True
        if any(keyword in line.lower() for keyword in INSTITUTION_KEYWORDS):
            return len(current) >= 2
        return False

    def _parse_block(self, block: str) -> EducationEntry:
        entry = empty_education_entry()
        lines = split_lines(block)
        if not lines:
            return entry

        entry["degree"] = self._extract_degree(block)
        entry["school_name"] = self._extract_school_name(lines, entry["degree"])
        entry["class_name"] = self._extract_class_name(block)

        start_date, end_date, _ = parse_date_range(block)
        years = extract_years(block)

        if start_date:
            entry["start_year"] = start_date[:4] if len(start_date) >= 4 else start_date
        elif years:
            entry["start_year"] = years[0]

        if end_date:
            entry["passing_year"] = end_date[:4] if len(end_date) >= 4 else end_date
        elif years:
            entry["passing_year"] = years[-1]
        elif start_date and not end_date:
            entry["passing_year"] = start_date[:4]

        # Clean invalid school name from entry fields
        if entry["school_name"] and not self._is_valid_school_name(entry["school_name"]):
            entry["school_name"] = None

        return entry

    def _extract_degree(self, text: str) -> str | None:
        for line in text.split("\n"):
            cleaned = clean_line(line)
            for pattern in DEGREE_PATTERNS:
                match = re.search(pattern, cleaned, re.IGNORECASE)
                if match:
                    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
                    for part in parts:
                        if re.search(pattern, part, re.IGNORECASE):
                            part = DATE_RANGE_PATTERN.sub("", part).strip(" ,()-–—~")
                            return part
                    return DATE_RANGE_PATTERN.sub("", cleaned).strip(" ,()-–—~")
        return None

    def _extract_school_name(
        self, lines: list[str], degree: str | None
    ) -> str | None:
        degree_line = None
        for line in lines:
            if degree and degree.lower() in line.lower():
                degree_line = line
                break

        if degree_line:
            parts = [p.strip() for p in degree_line.split(",") if p.strip()]
            for part in parts:
                if any(keyword in part.lower() for keyword in INSTITUTION_KEYWORDS):
                    cleaned = clean_line(part)
                    if self._is_valid_school_name(cleaned):
                        return cleaned

        for line in lines:
            lower = line.lower()
            if any(keyword in lower for keyword in INSTITUTION_KEYWORDS):
                cleaned = clean_line(line)
                if self._is_valid_school_name(cleaned):
                    return cleaned

        for line in lines:
            cleaned = clean_line(line)
            if degree and degree.lower() in cleaned.lower():
                continue
            if re.search(r"\b(19|20)(?:\d{2}|[xX]{2})\b", cleaned):
                continue
            if self._contains_degree(cleaned):
                continue
            if any(pat in cleaned.lower() for pat in ("gpa", "grade", "major", "minor", "expected", "dean", "scholar", "graduated", "distinction", "laude")):
                continue
            if self._is_valid_school_name(cleaned):
                return cleaned

        if lines:
            fallback = clean_line(lines[0])
            if self._is_valid_school_name(fallback):
                return fallback

        return None

    def _extract_class_name(self, text: str) -> str | None:
        distinction_match = re.search(
            r"\b(?:first|second|third)\s+class(?:\s+with\s+distinction)?",
            text,
            re.IGNORECASE,
        )
        if distinction_match:
            return clean_line(distinction_match.group(0))

        for pattern in CLASS_NAME_PATTERNS:
            match = re.search(
                rf"({pattern}[\s:.-]*[\w\.\%/]+)",
                text,
                re.IGNORECASE,
            )
            if match:
                return clean_line(match.group(1))

        gpa_match = re.search(
            r"(?:cgpa|gpa|grade|percentage|percent)[\s:.-]*[\d\.]+[%]?",
            text,
            re.IGNORECASE,
        )
        if gpa_match:
            return clean_line(gpa_match.group(0))

        return None

    def _contains_degree(self, text: str) -> bool:
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in DEGREE_PATTERNS
        )

    def _is_valid_school_name(self, name: str) -> bool:
        if not name:
            return False
        name_lower = name.lower()
        ignored_patterns = (
            r"\bgpa\b",
            r"\bcgpa\b",
            r"\bgrade\b",
            r"\bpercentage\b",
            r"\bexpected\b",
            r"\bgraduation\b",
            r"\bdean's\b",
            r"\bscholars?\b",
            r"\bhonors?\b",
            r"\bmajor\b",
            r"\bminor\b",
            r"\bcoursework\b",
            r"\bnewspaper\b",
            r"\bstudent\b",
            r"\bactivities\b",
            r"\bcommunity\b",
            r"\bvolunteer\b",
            r"\bclub\b",
            r"\bpresident\b",
            r"\bmember\b",
            r"\bchancellor\b",
            r"\blist\b",
            r"\bstudy\b",
            r"\bgraduated\b",
            r"\bdistinction\b",
            r"\blaude\b",
            r"\bmagna\b",
            r"\bsumma\b",
            r"\bfirst\s+class\b",
            r"\bsecond\s+class\b",
            r"\bcomputer\s+skills\b",
            r"\blanguage\s+skills\b",
            r"\badded\s+value\b",
            r"\bservices?\b",
        )
        if any(re.search(pat, name_lower) for pat in ignored_patterns):
            return False
        if len(name.split()) > 10:
            return False
        return True

    def _is_valid_entry(self, entry: EducationEntry) -> bool:
        school_name = entry.get("school_name")
        degree = entry.get("degree")
        if school_name and not self._is_valid_school_name(school_name):
            entry["school_name"] = None
            school_name = None
        return bool(school_name or degree)
