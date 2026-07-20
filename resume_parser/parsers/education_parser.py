"""Parse education entries from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.models.schemas import EducationEntry, empty_education_entry
from resume_parser.utils.constants import (
    CLASS_NAME_PATTERNS,
    DATE_RANGE_PATTERN,
    DEGREE_PATTERNS,
    EDUCATION_SECTION_HEADERS,
    INSTITUTION_KEYWORD_PATTERN,
)
from resume_parser.utils.date_utils import extract_years, parse_date_range
from resume_parser.utils.text_utils import clean_line, split_lines

logger = logging.getLogger(__name__)


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

        entries = self._merge_fragment_entries(entries)

        logger.info("Parsed %d education entries", len(entries))
        return entries

    def _split_into_blocks(self, text: str) -> list[str]:
        lines = split_lines(text)
        if not lines:
            return []

        cleaned_lines = []
        for line in lines:
            lower = line.lower()
            if (
                "im a. sample" in lower
                or "page " in lower
                or "revision:" in lower
                or "resume sample" in lower
                or lower == "continued"
                or self._is_section_header_line(line)
            ):
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

        if self._has_institution(line):
            if any(self._has_institution(entry) for entry in current):
                return True

        return False

    def _parse_block(self, block: str) -> EducationEntry:
        entry = empty_education_entry()
        lines = [line for line in split_lines(block) if not self._is_section_header_line(line)]
        if not lines:
            return entry

        layout = self._parse_layout(lines)
        if layout:
            entry["degree"] = layout.get("degree")
            entry["school_name"] = layout.get("school_name")
            entry["start_year"] = layout.get("start_year")
            entry["passing_year"] = layout.get("passing_year")
            entry["class_name"] = self._extract_class_name(block)
        else:
            entry["degree"] = self._extract_degree(block)
            entry["school_name"] = self._extract_school_name(lines, entry["degree"])
            entry["class_name"] = self._extract_class_name(block)

            start_date, end_date, is_current = parse_date_range(block)
            years = extract_years(block)

            if start_date:
                entry["start_year"] = start_date[:4] if len(start_date) >= 4 else start_date
            elif years:
                entry["start_year"] = years[0]

            if end_date:
                entry["passing_year"] = end_date[:4] if len(end_date) >= 4 else end_date
            elif years and not is_current:
                entry["passing_year"] = years[-1]
            elif is_current and start_date:
                entry["passing_year"] = None
            elif start_date and not end_date and not is_current:
                entry["passing_year"] = start_date[:4]

        if entry["school_name"] and not self._is_valid_school_name(entry["school_name"]):
            entry["school_name"] = None

        return entry

    def _parse_layout(self, lines: list[str]) -> dict[str, str | None] | None:
        """Handle common stacked layouts: degree/date/school permutations."""
        degree_line = next((line for line in lines if self._contains_degree(line)), None)
        school_line = next((line for line in lines if self._has_institution(line)), None)
        date_line = next((line for line in lines if self._is_date_line(line)), None)

        if not degree_line and not school_line:
            return None

        result: dict[str, str | None] = {
            "degree": None,
            "school_name": None,
            "start_year": None,
            "passing_year": None,
        }

        if degree_line:
            result["degree"] = self._extract_degree(degree_line)

        if school_line:
            result["school_name"] = self._extract_school_name(lines, result["degree"])

        date_text = date_line or "\n".join(lines)
        start_date, end_date, is_current = parse_date_range(date_text)
        years = extract_years(date_text)

        if start_date:
            result["start_year"] = start_date[:4] if len(start_date) >= 4 else start_date
        elif years:
            result["start_year"] = years[0]

        if end_date:
            result["passing_year"] = end_date[:4] if len(end_date) >= 4 else end_date
        elif years and not is_current:
            result["passing_year"] = years[-1]
        elif is_current:
            result["passing_year"] = None
        elif start_date and not is_current:
            result["passing_year"] = start_date[:4]

        if result["degree"] or result["school_name"]:
            return result
        return None

    def _merge_fragment_entries(self, entries: list[EducationEntry]) -> list[EducationEntry]:
        """Merge split fragments such as degree/date in one block and school in the next."""
        if len(entries) < 2:
            return entries

        merged: list[EducationEntry] = []
        index = 0
        while index < len(entries):
            current = entries[index]
            if index + 1 < len(entries):
                nxt = entries[index + 1]
                if self._should_merge_entries(current, nxt):
                    merged.append(self._combine_entries(current, nxt))
                    index += 2
                    continue
            merged.append(current)
            index += 1
        return merged

    def _should_merge_entries(self, left: EducationEntry, right: EducationEntry) -> bool:
        left_degree = bool(left.get("degree"))
        left_school = bool(left.get("school_name"))
        right_degree = bool(right.get("degree"))
        right_school = bool(right.get("school_name"))

        if left_degree and not left_school and right_school and not right_degree:
            return True
        if left_school and not left_degree and right_degree and not right_school:
            return True
        return False

    def _combine_entries(self, left: EducationEntry, right: EducationEntry) -> EducationEntry:
        combined = empty_education_entry()
        for key in ("degree", "school_name", "class_name", "start_year", "passing_year"):
            combined[key] = left.get(key) or right.get(key)
        return combined

    def _extract_degree(self, text: str) -> str | None:
        for line in text.split("\n"):
            cleaned = clean_line(line)
            if self._is_section_header_line(cleaned):
                continue
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
                if self._has_institution(part):
                    cleaned = clean_line(part)
                    if self._is_valid_school_name(cleaned):
                        return cleaned

        for line in lines:
            if self._has_institution(line):
                cleaned = clean_line(line)
                if self._is_valid_school_name(cleaned):
                    return cleaned

        for line in lines:
            cleaned = clean_line(line)
            if self._is_section_header_line(cleaned):
                continue
            if degree and degree.lower() in cleaned.lower():
                continue
            if self._is_date_line(cleaned):
                continue
            if self._contains_degree(cleaned):
                continue
            if any(
                pat in cleaned.lower()
                for pat in (
                    "gpa",
                    "grade",
                    "major",
                    "minor",
                    "expected",
                    "dean",
                    "scholar",
                    "graduated",
                    "distinction",
                    "laude",
                )
            ):
                continue
            if self._is_valid_school_name(cleaned):
                return cleaned

        return None

    def _extract_class_name(self, text: str) -> str | None:
        distinction_match = re.search(
            r"\b(?:first|second|third)\s+class(?:\s+with\s+distinction)?",
            text,
            re.IGNORECASE,
        )
        if distinction_match:
            return clean_line(distinction_match.group(0))

        grade_match = re.search(
            r"\b(c?gpa|grade|percentage|percent)\b[^\d\n]{0,20}?"
            r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?%?)",
            text,
            re.IGNORECASE,
        )
        if grade_match:
            label = grade_match.group(1)
            if label.lower() in {"gpa", "cgpa"}:
                label = label.upper()
            value = grade_match.group(2).strip()
            return clean_line(f"{label}: {value}")

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

    def _has_institution(self, text: str) -> bool:
        return bool(INSTITUTION_KEYWORD_PATTERN.search(text))

    def _is_date_line(self, text: str) -> bool:
        if DATE_RANGE_PATTERN.search(text):
            return True
        stripped = text.strip()
        if re.fullmatch(r"(?:19|20)\d{2}", stripped):
            return True
        if re.search(r"\b(?:present|current|ongoing|now)\b", text, re.IGNORECASE):
            return True
        return False

    def _is_section_header_line(self, line: str) -> bool:
        normalized = clean_line(line).rstrip(":").strip()
        if not normalized:
            return False
        compact = re.sub(r"[^\w\s]", " ", normalized).strip()
        compact_lower = re.sub(r"\s+", " ", compact).lower()
        for pattern in EDUCATION_SECTION_HEADERS:
            if re.fullmatch(pattern, compact_lower, re.IGNORECASE):
                return True
        return False

    def _is_any_section_header(self, line: str) -> bool:
        normalized = clean_line(line).rstrip(":").strip()
        if not normalized:
            return False
        compact = re.sub(r"[^\w\s]", " ", normalized).strip()
        compact_lower = re.sub(r"\s+", " ", compact).lower()
        
        from resume_parser.utils.constants import (
            EDUCATION_SECTION_HEADERS,
            EXPERIENCE_SECTION_HEADERS,
            SKILLS_SECTION_HEADERS,
            LANGUAGES_SECTION_HEADERS,
            OTHER_SECTION_HEADERS,
        )
        for group in (
            EDUCATION_SECTION_HEADERS,
            EXPERIENCE_SECTION_HEADERS,
            SKILLS_SECTION_HEADERS,
            LANGUAGES_SECTION_HEADERS,
            OTHER_SECTION_HEADERS,
        ):
            for pattern in group:
                if re.fullmatch(pattern, compact_lower, re.IGNORECASE):
                    return True
        return False

    def _is_valid_school_name(self, name: str) -> bool:
        if not name:
            return False
        if self._is_any_section_header(name):
            return False
        if self._contains_degree(name):
            return False
        if self._is_date_line(name):
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
            r"\beducation\b",
            r"\bacademic\b",
            r"\bqualifications?\b",
            r"\bemphas(?:is|es)\b",
            r"\bassist(?:s|ed|ing)?\b",
            r"\bdevelop(?:s|ed|ing)?\b",
            r"\bmanage(?:s|ed|ing)?\b",
            r"\bconduct(?:s|ed|ing)?\b",
            r"\bprepare(?:s|ed|ing)?\b",
            r"\bdesign(?:s|ed|ing)?\b",
            r"\bimplement(?:s|ed|ing)?\b",
            r"\bwrite\b",
            r"\bwrote\b",
            r"\bwriting\b",
            r"\bcreate(?:s|ed|ing)?\b",
            r"\bserve(?:s|ed|ing)?\b",
            r"\bwork(?:s|ed|ing)?\b",
            r"\blead(?:s|ing)?\b",
            r"\bled\b",
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
        if school_name and not degree:
            if not self._has_institution(school_name):
                entry["school_name"] = None
                school_name = None
        return bool(school_name or degree)
