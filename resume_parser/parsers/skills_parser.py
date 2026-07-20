"""Parse skills from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.utils.constants import ADDRESS_PATTERN, COMMON_SKILL_DELIMITERS, ORG_SUFFIX_PATTERN
from resume_parser.utils.text_utils import clean_line, deduplicate_preserve_order, split_lines

logger = logging.getLogger(__name__)

SKILL_NOISE_PATTERNS = (
    r"^skills?:?$",
    r"^technical\s+skills?:?$",
    r"^key\s+skills?:?$",
    r"^tools?:?$",
    r"^technologies?:?$",
)

CATEGORY_LINE_PATTERN = re.compile(r"^(.+?):\s*(.+)$")

CONTACT_SKILL_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\bwww\.", re.IGNORECASE),
    re.compile(r"\b(?:github|linkedin|gitlab|bitbucket)\.", re.IGNORECASE),
    re.compile(r"[\w\.-]+@[\w\.-]+\.[a-z]{2,}", re.IGNORECASE),
    re.compile(r"\+\d{1,3}[\s.-]?\d{4,}"),
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\(\+\d{1,3}\)"),
)


class SkillsParser:
    """Extract skill tokens from a skills section."""

    def parse(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        skills: list[str] = []
        lines = split_lines(text)

        cleaned_lines = []
        for line in lines:
            lower = line.lower()
            if (
                "im a. sample" in lower
                or "page " in lower
                or "revision:" in lower
                or "resume sample" in lower
                or lower == "continued"
            ):
                continue
            cleaned_lines.append(line)
        lines = cleaned_lines

        for line in lines:
            if self._is_noise_line(line):
                continue

            category_value = self._extract_category_value(line)
            if category_value is not None:
                if category_value:
                    if self._has_delimiters(category_value):
                        skills.extend(self._split_by_delimiters(category_value))
                    else:
                        skills.append(clean_line(category_value))
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

    def _extract_category_value(self, line: str) -> str | None:
        """Return skill payload from a category line, or None if not categorized."""
        match = CATEGORY_LINE_PATTERN.match(line.strip())
        if not match:
            return None

        label = clean_line(match.group(1))
        value = clean_line(match.group(2))
        if not label:
            return None

        if not self._looks_like_category_label(label):
            return None

        return value

    def _looks_like_category_label(self, label: str) -> bool:
        if not label or len(label) > 60:
            return False
        if any(pattern.search(label) for pattern in CONTACT_SKILL_PATTERNS):
            return False
        if re.search(r"[\d@]", label):
            return False

        words = label.split()
        if len(words) > 6:
            return False

        if "&" in label or "/" in label:
            return True

        lower = label.lower()
        category_hints = (
            "language",
            "framework",
            "database",
            "tool",
            "web",
            "cloud",
            "platform",
            "library",
            "technology",
            "skill",
            "api",
            "data",
            "machine",
            "learning",
            "science",
            "devops",
            "stack",
            "software",
            "programming",
        )
        return any(hint in lower for hint in category_hints)

    def _tokenize_line(self, line: str) -> list[str]:
        stripped = re.sub(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]+\s*", "", line)
        category_value = self._extract_category_value(stripped)
        if category_value is not None:
            if not category_value:
                return []
            if self._has_delimiters(category_value):
                return self._split_by_delimiters(category_value)
            return [clean_line(category_value)]
        if self._has_delimiters(stripped):
            return self._split_by_delimiters(stripped)
        return [clean_line(stripped)]

    def _split_by_delimiters(self, line: str) -> list[str]:
        top_parts = self._split_respecting_parens(line)
        result: list[str] = []
        for part in top_parts:
            result.extend(self._expand_parenthetical(part))
        return [clean_line(part) for part in result if clean_line(part)]

    def _split_respecting_parens(self, line: str) -> list[str]:
        """Split on skill delimiters, but never inside (), [] or {}."""
        parts: list[str] = []
        buf: list[str] = []
        depth = 0
        index = 0
        while index < len(line):
            ch = line[index]
            if ch in "([{":
                depth += 1
                buf.append(ch)
            elif ch in ")]}":
                depth = max(0, depth - 1)
                buf.append(ch)
            elif depth == 0 and ch in ",|;/•·▪◦●":
                if ch == "/" and self._is_slash_inside_token(line, index):
                    buf.append(ch)
                else:
                    parts.append("".join(buf))
                    buf = []
            else:
                buf.append(ch)
            index += 1
        if buf:
            parts.append("".join(buf))
        return parts

    def _is_slash_inside_token(self, line: str, index: int) -> bool:
        """Keep slashes that join short tokens such as AI/ML or CI/CD."""
        left = line[:index].rstrip()
        right = line[index + 1 :].lstrip()
        if not left or not right:
            return False
        left_token = re.split(r"[\s,|;/•·▪◦●]+", left)[-1]
        right_token = re.split(r"[\s,|;/•·▪◦●:]+", right)[0]
        if not left_token or not right_token:
            return False
        if len(left_token) <= 4 and len(right_token) <= 4:
            return True
        if left_token.startswith(".") or right_token.startswith("."):
            return True
        return False

    def _expand_parenthetical(self, part: str) -> list[str]:
        """Expand "Group (a, b, c)" into ["Group", "a", "b", "c"]."""
        match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", part.strip())
        if not match:
            return [part]
        head = match.group(1).strip()
        inner = match.group(2).strip()
        if not re.search(r"[,;/|]", inner):
            return [part]
        items = [head] if head else []
        items.extend(p.strip() for p in re.split(r"[,;/|]", inner) if p.strip())
        return items or [part]

    def _has_delimiters(self, line: str) -> bool:
        if CATEGORY_LINE_PATTERN.match(line.strip()):
            return True
        return any(delim in line for delim in COMMON_SKILL_DELIMITERS if delim not in "-")

    def _is_bullet_line(self, line: str) -> bool:
        return bool(re.match(r"^[•\-\*\u2022\u2023\u25E6\u2043>\|]", line.strip()))

    def _is_noise_line(self, line: str) -> bool:
        return any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in SKILL_NOISE_PATTERNS)

    def _normalize_skill(self, skill: str) -> str:
        skill = clean_line(skill)
        skill = re.sub(r"^(?:skills?|technologies?)\s*[:\-]\s*", "", skill, flags=re.IGNORECASE)
        if re.match(r"^\.\w+", skill):
            return skill.rstrip(" .:-")
        return skill.strip(" .:-")

    def _is_valid_skill(self, skill: str) -> bool:
        if not skill or len(skill) < 2:
            return False
        if len(skill) > 50:
            return False

        if any(pattern.search(skill) for pattern in CONTACT_SKILL_PATTERNS):
            return False

        if "@" in skill or re.search(r"[\w\.-]+@[\w\.-]+", skill):
            return False

        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", skill) or re.search(r"\(\d{3}\)", skill):
            return False

        skill_lower = skill.lower()
        if re.search(r",\s*[A-Z]{2}\b", skill) or re.search(r"\b\d{5}(?:-\d{4})?\b", skill):
            return False
        if ADDRESS_PATTERN.search(skill):
            return False

        if ORG_SUFFIX_PATTERN.search(skill):
            return False

        if re.search(r",\s*[A-Za-z]{2,}(?:\s|$)", skill) and len(skill.split()) >= 2:
            return False

        noise_words = {
            "sample",
            "page",
            "street",
            "road",
            "drive",
            "rd",
            "st",
            "avenue",
            "ave",
            "lane",
            "ln",
            "court",
            "ct",
            "way",
            "plaza",
            "suite",
            "ste",
            "apartment",
            "apt",
            "zip",
            "postal",
            "phone",
            "email",
            "address",
            "resume",
            "curriculum",
            "vitae",
            "cv",
            "objective",
            "summary",
            "profile",
            "education",
            "experience",
            "work",
            "history",
            "employment",
            "chronological",
            "functional",
            "continued",
            "present",
            "current",
            "date",
            "graduation",
            "gpa",
            "major",
            "minor",
            "university",
            "college",
            "school",
            "candidate",
            "applicant",
            "name",
            "references",
            "available",
            "upon",
            "request",
            "furnished",
            "letters",
            "transcript",
        }

        for word in noise_words:
            if re.search(rf"\b{re.escape(word)}\b", skill_lower):
                return False

        if re.match(r"^[a-z]{2}$", skill_lower) and skill_lower in {
            "ne",
            "ok",
            "tx",
            "ca",
            "ny",
            "wa",
            "il",
            "ma",
            "ia",
        }:
            return False

        if len(skill.split()) > 4:
            return False

        if any(ch in skill for ch in "•*▪◦●"):
            return False

        if skill_lower in {
            "and",
            "or",
            "etc",
            "including",
            "with",
            "for",
            "the",
            "of",
            "to",
            "in",
            "on",
            "at",
            "by",
            "an",
            "a",
        }:
            return False

        if not any(ch.isalpha() for ch in skill):
            return False

        return True
