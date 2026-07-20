"""Shared constants for resume parsing."""

from __future__ import annotations

import re

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".doc", ".docx"})

EXPERIENCE_SECTION_HEADERS: tuple[str, ...] = (
    r"experience",
    r"professional\s+experience",
    r"work\s+experience",
    r"work\s+history",
    r"employment\s+history",
    r"employment",
    r"career\s+history",
    r"relevant\s+experience",
    r"professional\s+background",
    r"professional\s+history",
    r"job\s+history",
    r"positions?\s+held",
    r"career\s+summary",
)

EDUCATION_SECTION_HEADERS: tuple[str, ...] = (
    r"education",
    r"academic\s+background",
    r"academic\s+history",
    r"qualifications?",
    r"educational\s+background",
    r"education\s+and\s+training",
    r"academics?",
)

SKILLS_SECTION_HEADERS: tuple[str, ...] = (
    r"skills?",
    r"technical\s+skills?",
    r"core\s+competencies?",
    r"key\s+skills?",
    r"professional\s+skills?",
    r"areas?\s+of\s+expertise",
    r"expertise",
    r"technologies?",
    r"tools?\s+and\s+technologies?",
)

LANGUAGES_SECTION_HEADERS: tuple[str, ...] = (
    r"languages?",
    r"language\s+proficiency",
    r"language\s+skills?",
)

OTHER_SECTION_HEADERS: tuple[str, ...] = (
    r"summary",
    r"profile",
    r"objective",
    r"certifications?",
    r"projects?",
    r"awards?",
    r"achievements?",
    r"publications?",
    r"references?",
    r"contact",
    r"personal\s+information",
    r"interests?",
    r"hobbies?",
    r"volunteer",
    r"community\s+service",
    r"professional\s+affiliations?",
    r"professional\s+memberships?",
    r"professional\s+profile",
    r"honors?",
    r"activities",
    r"leadership",
    r"volunteer\s+activities?",
    r"affiliation",
    r"affiliations",
    r"memberships?",
    r"chronological(?:\s+\([\w/]+\))?",
    r"functional(?:\s+\([\w/]+\))?",
)

JOB_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "full-time": ("full-time", "full time", "fulltime", "permanent"),
    "part-time": ("part-time", "part time", "parttime"),
    "contract": ("contract", "contractor", "freelance", "consulting", "consultant"),
    "internship": ("intern", "internship", "trainee", "apprentice"),
    "remote": ("remote", "work from home", "wfh"),
    "temporary": ("temporary", "temp"),
}

DEGREE_PATTERNS: tuple[str, ...] = (
    r"\b(?:ph\.?d\.?|doctor(?:ate)?\s+of\s+philosophy)\b",
    r"\b(?:m\.?s\.?|m\.?sc\.?|master(?:'?s)?(?:\s+of|\s+in)?)\b(?!\s+(?:office|word|excel|powerpoint|access|outlook|project|sql|dos|paint|visio|exchange|windows|dynamics|teams|sharepoint))",
    r"\b(?:m\.?a\.?|master\s+of\s+arts)\b",
    r"\b(?:m\.?b\.?a\.?|master\s+of\s+business\s+administration)\b",
    r"\b(?:b\.?s\.?|b\.?sc\.?|bachelor(?:'?s)?(?:\s+of|\s+in)?)\b",
    r"\b(?:b\.?a\.?|bachelor\s+of\s+arts)\b",
    r"\b(?:b\.?e\.?|b\.?tech\.?|bachelor\s+of\s+(?:engineering|technology))\b",
    r"\b(?:m\.?tech\.?|master\s+of\s+technology)\b",
    r"\b(?:b\.?com\.?|bachelor\s+of\s+commerce)\b",
    r"\b(?:m\.?com\.?|master\s+of\s+commerce)\b",
    r"\b(?:associate(?:'?s)?(?:\s+degree|\s+in)?)\b",
    r"\b(?:diploma|certificate|certification)\b",
    r"\b(?:high\s+school|secondary\s+school|h\.?s\.?c\.?|s\.?s\.?c\.?)\b",
    r"\b(?:intermediate|pre-university|p\.?u\.?c\.?)\b",
)

CLASS_NAME_PATTERNS: tuple[str, ...] = (
    r"\b(?:class(?:es)?|grade|cgpa|gpa|percentage|percent|division|honors?|honours?)\b",
    r"\b(?:first\s+class|second\s+class|distinction|cum\s+laude)\b",
)

CURRENT_KEYWORDS: tuple[str, ...] = (
    "present",
    "current",
    "ongoing",
    "now",
    "till date",
    "to date",
    "till now",
)

_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_DATE_TOKEN = rf"(?:{_MONTH}[\s\.,]*(?:\d{{4}}|\d{{2}}[xX]{{2}})|\d{{1,2}}[\s/\-.](?:\d{{4}}|\d{{2}}[xX]{{2}})|(?:\d{{4}}|\d{{2}}[xX]{{2}}))"

DATE_RANGE_PATTERN = re.compile(
    rf"(?:"
    rf"(?P<start>{_DATE_TOKEN})"
    rf"\s*(?:[-–—~]|to)\s*"
    rf"(?P<end>{_DATE_TOKEN}|present|current|ongoing|now)"
    rf"|"
    rf"(?P<single>{_DATE_TOKEN})"
    rf")",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(r"\b(?:19|20)(?:\d{2}|[xX]{2})\b")

ADDRESS_PATTERN = re.compile(
    r"(?P<address>"
    r"(?:\d+[\s,]+)?[\w\s]+\b(?:street|st\.?|road|rd\.?|avenue|ave\.?|"
    r"boulevard|blvd\.?|lane|ln\.?|drive|dr\.?|way|city|state|country|"
    r"zip|postal)\b[\w\s,\-]*"
    r")",
    re.IGNORECASE,
)

# Generic organization/legal-entity suffixes used to recognize company names
# by structure rather than by a fixed vocabulary of specific employers.
ORG_SUFFIX_PATTERN = re.compile(
    r"\b(?:inc|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|"
    r"gmbh|plc|pvt|pte|llp|lp|s\.a|s\.r\.l|b\.v|ag|nv|oy|ab)\b\.?",
    re.IGNORECASE,
)

# Generic institution keywords for schools/universities (structure, not names).
INSTITUTION_KEYWORD_PATTERN = re.compile(
    r"\b(?:university|college|institute|institution|school|academy|"
    r"polytechnic|seminary|conservatory|iit|nit|bits)\b",
    re.IGNORECASE,
)

COMMON_SKILL_DELIMITERS: tuple[str, ...] = (",", "|", "•", "·", "▪", "◦", "●", ";", "/")

LANGUAGE_PROFICIENCY_KEYWORDS: tuple[str, ...] = (
    "native",
    "fluent",
    "proficient",
    "intermediate",
    "basic",
    "beginner",
    "advanced",
    "conversational",
    "professional",
    "bilingual",
    "mother tongue",
)
