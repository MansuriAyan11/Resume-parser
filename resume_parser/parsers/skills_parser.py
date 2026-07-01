"""Parse skills from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.utils.constants import COMMON_SKILL_DELIMITERS
from resume_parser.utils.text_utils import clean_line, deduplicate_preserve_order, split_lines

logger = logging.getLogger(__name__)

SKILL_NOISE_PATTERNS = (
    r"^skills?:?$",
    r"^technical\s+skills?:?$",
    r"^key\s+skills?:?$",
    r"^tools?:?$",
    r"^technologies?:?$",
)


class SkillsParser:
    """Extract skill tokens from a skills section."""

    def parse(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        skills: list[str] = []
        lines = split_lines(text)

        # Filter out page headers, footer text, and sample labels
        cleaned_lines = []
        for line in lines:
            lower = line.lower()
            if "im a. sample" in lower or "page " in lower or "revision:" in lower or "resume sample" in lower or lower == "continued":
                continue
            cleaned_lines.append(line)
        lines = cleaned_lines

        for line in lines:
            if self._is_noise_line(line):
                continue

            if self._is_bullet_line(line):
                skills.extend(self._tokenize_line(line))
            elif self._has_delimiters(line):
                skills.extend(self._split_by_delimiters(line))
            else:
                skills.append(clean_line(line))

        cleaned = [
            skill
            for skill in deduplicate_preserve_order(
                [self._normalize_skill(s) for s in skills if s]
            )
            if self._is_valid_skill(skill)
        ]

        logger.info("Parsed %d skills", len(cleaned))
        return cleaned

    def _tokenize_line(self, line: str) -> list[str]:
        stripped = re.sub(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]+\s*", "", line)
        if self._has_delimiters(stripped):
            return self._split_by_delimiters(stripped)
        return [clean_line(stripped)]

    def _split_by_delimiters(self, line: str) -> list[str]:
        pattern = r"[,|;/•·▪◦●]+"
        parts = re.split(pattern, line)
        return [clean_line(part) for part in parts if clean_line(part)]

    def _has_delimiters(self, line: str) -> bool:
        return any(delim in line for delim in COMMON_SKILL_DELIMITERS if delim not in "-")

    def _is_bullet_line(self, line: str) -> bool:
        return bool(re.match(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]", line.strip()))

    def _is_noise_line(self, line: str) -> bool:
        return any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in SKILL_NOISE_PATTERNS)

    def _normalize_skill(self, skill: str) -> str:
        skill = clean_line(skill)
        skill = re.sub(r"^(?:skills?|technologies?)\s*[:\-]\s*", "", skill, flags=re.IGNORECASE)
        return skill.strip(" .:-")

    def _is_valid_skill(self, skill: str) -> bool:
        if not skill or len(skill) < 2:
            return False
        if len(skill) > 50:
            return False

        # Filter out emails
        if "@" in skill or re.search(r"[\w\.-]+@[\w\.-]+", skill):
            return False

        # Filter out phone numbers
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", skill) or re.search(r"\(\d{3}\)", skill):
            return False

        # Filter out addresses / locations / dates / page headers
        skill_lower = skill.lower()
        noise_words = {
            "sample", "page", "bellevue", "nebraska", "omaha", "street", "road", "westview",
            "country club", "frederick", "northridge", "south", "north", "drive", "rd", "st",
            "avenue", "ave", "lane", "ln", "court", "ct", "way", "plaza", "suite", "ste",
            "apartment", "apt", "zip", "postal", "phone", "email", "address", "resume",
            "curriculum", "vitae", "cv", "objective", "summary", "profile", "education",
            "experience", "work", "history", "employment", "chronological", "functional",
            "continued", "present", "current", "date", "graduation", "gpa", "major", "minor",
            "university", "college", "school", "candidate", "applicant", "name", "references",
            "available", "upon", "request", "furnished", "letters", "transcript"
        }

        for word in noise_words:
            if re.search(rf"\b{re.escape(word)}\b", skill_lower):
                return False

        # State abbreviations
        if re.match(r"^[a-z]{2}$", skill_lower) and skill_lower in {"ne", "ok", "tx", "ca", "ny", "wa", "il", "ma", "ia"}:
            return False

        # If it has more than 4 words, it's likely a sentence/description
        if len(skill.split()) > 4:
            return False

        # General check for verbs or bullet lists (e.g. starts with lowercase, has bullet characters)
        if any(ch in skill for ch in "•-*▪◦●"):
            return False

        if skill_lower in {"and", "or", "etc", "including", "with", "for", "the", "of", "to", "in", "on", "at", "by", "an", "a"}:
            return False

        # Must contain at least one letter
        if not any(ch.isalpha() for ch in skill):
            return False

        return True
