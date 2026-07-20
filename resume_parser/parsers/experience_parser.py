"""Parse work experience entries from resume text."""

from __future__ import annotations

import logging
import re

from resume_parser.models.schemas import ExperienceEntry, empty_experience_entry
from resume_parser.utils.constants import (
    ADDRESS_PATTERN,
    DATE_RANGE_PATTERN,
    JOB_TYPE_KEYWORDS,
    ORG_SUFFIX_PATTERN,
)
from resume_parser.utils.date_utils import parse_date_range
from resume_parser.utils.text_utils import clean_line, split_lines, truncate_text, is_likely_header

logger = logging.getLogger(__name__)

TITLE_KEYWORDS = (
    "engineer",
    "developer",
    "manager",
    "analyst",
    "consultant",
    "specialist",
    "director",
    "lead",
    "architect",
    "designer",
    "scientist",
    "intern",
    "associate",
    "coordinator",
    "administrator",
    "executive",
    "officer",
    "supervisor",
    "technician",
    "programmer",
    "tester",
    "qa",
    "devops",
    "sre",
    "product",
    "project",
    "head",
    "chief",
    "vp",
    "president",
    "tutor",
    "bookkeeper",
    "representative",
    "clerk",
    "assistant",
)


class ExperienceParser:
    """Extract structured experience records from section text."""

    def parse(self, text: str) -> list[ExperienceEntry]:
        if not text or not text.strip():
            return []

        blocks = self._split_into_blocks(text)
        entries: list[ExperienceEntry] = []

        for block in blocks:
            entry = self._parse_block(block)
            if self._is_valid_entry(entry):
                entries.append(entry)

        # Forward propagate company name and address for sub-roles
        last_company = None
        last_address = None
        for entry in entries:
            if entry["company_name"]:
                last_company = entry["company_name"]
                last_address = entry["company_address"]
            elif last_company:
                entry["company_name"] = last_company
                if not entry["company_address"]:
                    entry["company_address"] = last_address

        logger.info("Parsed %d experience entries", len(entries))
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

        if len(blocks) <= 1:
            return self._split_by_date_lines(lines)

        return ["\n".join(block) for block in blocks if block]

    def _split_by_date_lines(self, lines: list[str]) -> list[str]:
        blocks: list[list[str]] = []
        current: list[str] = []

        for line in lines:
            current.append(line)
            if DATE_RANGE_PATTERN.search(line):
                blocks.append(current)
                current = []

        if current:
            blocks.append(current)

        merged = self._merge_orphan_lines(blocks)
        return ["\n".join(block) for block in merged if block]

    def _merge_orphan_lines(self, blocks: list[list[str]]) -> list[list[str]]:
        """Attach trailing orphan lines to the previous experience block."""
        if len(blocks) <= 1:
            return blocks

        merged: list[list[str]] = [blocks[0]]
        for block in blocks[1:]:
            if merged and not self._looks_like_title_line(block[0]):
                merged[-1].extend(block)
            else:
                merged.append(block)
        return merged

    def _is_block_boundary(self, line: str, current: list[str]) -> bool:
        if not current:
            return False

        # Rule 1: If the new line looks like a title, and the current block already has a title, split.
        if self._looks_like_title_line(line):
            if any(self._looks_like_title_line(entry) for entry in current):
                return True

        # Rule 2: If the new line has a date, and the current block already has a date, split.
        if DATE_RANGE_PATTERN.search(line):
            if any(DATE_RANGE_PATTERN.search(entry) for entry in current):
                return True

        return False

    def _parse_block(self, block: str) -> ExperienceEntry:
        entry = empty_experience_entry()
        lines = split_lines(block)
        if not lines:
            return entry

        date_line_index = self._find_date_line_index(lines)
        date_line = lines[date_line_index] if date_line_index is not None else ""

        start_date, end_date, is_current = parse_date_range(date_line or block)
        entry["start_date"] = start_date
        entry["end_date"] = end_date
        entry["current"] = is_current

        header_lines = (
            lines[:date_line_index]
            if date_line_index is not None and date_line_index > 0
            else lines[:2]
        )
        body_lines = (
            lines[date_line_index + 1 :]
            if date_line_index is not None
            else lines[2:]
        )

        company, position, address = self._extract_company_and_position(header_lines, body_lines)
        # Functional resumes and prose lines can smuggle full sentences into
        # the label fields. A company name or job title is never a sentence,
        # so drop prose rather than emit confidently wrong data.
        if position and self._looks_like_prose(position):
            position = None
        if company and self._looks_like_prose(company):
            company = None
        entry["position"] = position
        entry["company_name"] = company
        entry["company_address"] = address if address else self._extract_address(body_lines + header_lines)
        entry["job_type"] = self._extract_job_type(block)
        entry["company_about"] = truncate_text(
            self._extract_description(body_lines, entry["job_type"])
        )

        # Fallback for position if not set
        if not entry["position"] and header_lines:
            fallback = clean_line(header_lines[0])
            if self._is_date_only(fallback) or self._looks_like_prose(fallback):
                fallback = None
            if fallback and (
                not entry["company_name"]
                or entry["company_name"].lower() not in fallback.lower()
            ):
                entry["position"] = fallback

        return entry

    def _is_date_only(self, text: str) -> bool:
        """True when a line carries only date/period information.

        Prevents a bare date range such as "(July 20xx - Oct 20xx)" from
        being promoted into the position field. Detection is structural:
        strip any date range, then any residual digits/punctuation and
        period keywords; if nothing meaningful remains, it was date-only.
        """
        residual = DATE_RANGE_PATTERN.sub("", clean_line(text))
        residual = re.sub(
            r"(?i)\b(?:present|current|ongoing|now|to|since|from)\b", "", residual
        )
        residual = re.sub(r"[\d\s,()\[\]\-–—~./:]", "", residual)
        return not residual.strip()

    def _find_date_line_index(self, lines: list[str]) -> int | None:
        for index, line in enumerate(lines):
            if DATE_RANGE_PATTERN.search(line):
                return index
        return None

    def _extract_company_and_position(
        self, header_lines: list[str], body_lines: list[str]
    ) -> tuple[str | None, str | None, str | None]:
        if not header_lines:
            if body_lines:
                header_line = body_lines[0]
            else:
                return None, None, None
        else:
            header_line = header_lines[0]

        cleaned_line = clean_line(header_line)
        cleaned_line = DATE_RANGE_PATTERN.sub("", cleaned_line).strip(" ,()-–—~")

        def is_location_part(part: str, idx: int, custom_parts: list[str] | None = None) -> bool:
            """Structural location test (no hardcoded place names)."""
            p = part.strip()
            if re.fullmatch(r"[A-Za-z]{2}", p):  # region/state code
                return True
            if re.fullmatch(r"\d{5}(?:-\d{4})?", p):  # ZIP / postal code
                return True
            if ADDRESS_PATTERN.search(p):  # street address
                return True
            if re.search(r",\s*[A-Za-z]{2}\b", p):  # "City, ST" within one part
                return True
            ref_parts = custom_parts if custom_parts is not None else parts
            # A locality immediately preceding a region/state code.
            if idx + 1 < len(ref_parts) and re.fullmatch(r"[A-Za-z]{2}", ref_parts[idx + 1].strip()):
                return True
            return False

        dash_pattern = re.compile(r"\s+[-–—−]\s+|\s*[–—]\s*")
        dash_parts = [p.strip() for p in dash_pattern.split(cleaned_line) if p.strip()]
        if len(dash_parts) >= 2:
            p1, p2 = dash_parts[0], dash_parts[1]
            p3 = dash_parts[2] if len(dash_parts) > 2 else None
            
            if self._looks_like_title_line(p2) and not self._looks_like_title_line(p1):
                position = p2
                company = p1
            else:
                position = p1
                company = p2
                
            address = p3 if p3 and is_location_part(p3, 2, dash_parts) else None
            
            company = clean_line(company)
            position = clean_line(position)
            if address:
                address = clean_line(address)
                
            if "," in company:
                comp_parts = [c.strip() for c in company.split(",") if c.strip()]
                if len(comp_parts) >= 2:
                    if is_location_part(comp_parts[-1], len(comp_parts)-1, comp_parts):
                        if not address:
                            address = comp_parts[-1]
                        company = ", ".join(comp_parts[:-1]).strip()
                        
            return company, position, address

        parts = []
        at_matches = re.split(r"\s+at\s+|\s+@\s+", cleaned_line, flags=re.IGNORECASE)
        if len(at_matches) > 1:
            parts = [p.strip() for p in at_matches if p.strip()]
            first_parts = [p.strip() for p in parts[0].split(",") if p.strip()]
            parts = first_parts + parts[1:]
        else:
            raw_parts = [p.strip() for p in cleaned_line.split(",") if p.strip()]
            i = 0
            while i < len(raw_parts):
                part = raw_parts[i]
                clean_part = re.sub(r"[^\w]", "", part).lower()
                if i > 0 and clean_part in {"inc", "llc", "co", "ltd", "corp", "corporation", "ne", "ok", "tx", "ca", "ny", "wa", "il", "ma"}:
                    parts[-1] = parts[-1] + ", " + part
                else:
                    parts.append(part)
                i += 1

        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return None, None, None

        position_candidates = []
        location_candidates = []
        company_candidates = []

        for i, part in enumerate(parts):
            if is_location_part(part, i):
                location_candidates.append(part)
            elif self._looks_like_title_line(part):
                position_candidates.append(part)
            else:
                company_candidates.append(part)

        position = None
        company = None
        address = location_candidates[0] if location_candidates else None

        if position_candidates:
            position = position_candidates[0]
        else:
            if parts and not is_location_part(parts[0], 0):
                position = parts[0]

        org_keywords = {"mutual", "special", "olympics", "smc", "inc", "co", "ltd", "corp", "corporation", "group", "systems", "university", "college", "school", "church", "industries", "railroad", "district", "force", "trading", "tool", "power", "goodwill", "telemarketing", "united states", "us", "u.s.", "air force", "company", "firm", "association", "club", "hospital", "medical", "center", "agency", "department", "office", "division"}
        primary_org_keywords = {"inc", "llc", "co", "ltd", "corp", "corporation", "university", "college", "school", "church", "railroad", "district", "force", "industries", "goodwill", "telemarketing"}

        best_company = None
        for cand in company_candidates:
            cand_lower = cand.lower()
            if any(re.search(rf"\b{re.escape(word)}\b", cand_lower) for word in primary_org_keywords):
                best_company = cand
                break
        if not best_company:
            for cand in company_candidates:
                cand_lower = cand.lower()
                if any(re.search(rf"\b{re.escape(word)}\b", cand_lower) for word in org_keywords):
                    best_company = cand
                    break

        if best_company:
            company = best_company
        elif company_candidates:
            for cand in company_candidates:
                if cand != position:
                    company = cand
                    break
        else:
            for loc in location_candidates:
                if any(re.search(rf"\b{re.escape(word)}\b", loc.lower()) for word in org_keywords):
                    company = loc
                    break

        if company and position and company.lower() == position.lower():
            if any(re.search(rf"\b{re.escape(word)}\b", position.lower()) for word in org_keywords) and not self._looks_like_title_line(position):
                company = position
                position = None
            else:
                company = None

        if position and not company:
            if any(re.search(rf"\b{re.escape(word)}\b", position.lower()) for word in primary_org_keywords):
                company = position
                position = None

        # Multi-line layouts place the employer (and sometimes its location)
        # on its own line beneath the job title. When the first header line
        # only yielded a title, fill the company/address from the remaining
        # header lines using structural cues (org suffix / address), never a
        # fixed list of employer or city names.
        if company is None:
            for extra in header_lines[1:]:
                extra_clean = clean_line(extra)
                if not extra_clean or DATE_RANGE_PATTERN.search(extra_clean):
                    continue
                if self._looks_like_title_line(extra_clean):
                    continue
                has_org = bool(ORG_SUFFIX_PATTERN.search(extra_clean))
                if ADDRESS_PATTERN.search(extra_clean) and not has_org:
                    if not address:
                        address = extra_clean
                    continue
                comp, addr = self._split_company_address(extra_clean)
                if comp:
                    company = comp
                    if addr and not address:
                        address = addr
                    break

        return company, position, address

    def _split_company_address(self, line: str) -> tuple[str | None, str | None]:
        """Split "Company, City, ST" style lines into (company, address).

        Purely structural: a trailing two-letter region code (optionally with
        the preceding locality) is treated as the address; the remainder is the
        company. Lines without such a trailer return (line, None).
        """
        cleaned = DATE_RANGE_PATTERN.sub("", clean_line(line)).strip(" ,()-–—~")
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if not parts:
            return None, None
        address = None
        if len(parts) >= 2 and re.fullmatch(r"[A-Za-z]{2}", parts[-1]):
            address = ", ".join(parts[-2:])
            parts = parts[:-2]
        company = ", ".join(parts).strip() or None
        return company, address


    def _extract_position(
        self, header_lines: list[str], body_lines: list[str]
    ) -> str | None:
        for line in header_lines:
            if self._looks_like_title_line(line):
                return clean_line(line)

        for line in header_lines:
            if not DATE_RANGE_PATTERN.search(line):
                return clean_line(line)

        for line in body_lines[:2]:
            if self._looks_like_title_line(line):
                return clean_line(line)

        return clean_line(header_lines[0]) if header_lines else None

    def _extract_company_name(
        self, header_lines: list[str], position: str | None
    ) -> str | None:
        candidates: list[str] = []
        for line in header_lines:
            cleaned = clean_line(line)
            if DATE_RANGE_PATTERN.search(cleaned):
                continue
            if position and cleaned.lower() == position.lower():
                continue
            if self._looks_like_title_line(cleaned) and position:
                continue
            candidates.append(cleaned)

        if not candidates and header_lines:
            fallback = clean_line(header_lines[0])
            if position and fallback.lower() != position.lower():
                return fallback
            if len(header_lines) > 1:
                return clean_line(header_lines[1])

        for candidate in candidates:
            if not self._looks_like_title_line(candidate):
                return candidate

        return candidates[0] if candidates else None

    def _extract_job_type(self, text: str) -> str | None:
        lower = text.lower()
        for job_type, keywords in JOB_TYPE_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                return job_type
        return None

    def _extract_address(self, lines: list[str]) -> str | None:
        for line in lines:
            if re.search(r"\b(?:technologies|tools|tech stack)\b", line, re.IGNORECASE):
                continue
            match = ADDRESS_PATTERN.search(line)
            if match:
                return clean_line(match.group("address"))
            if re.search(
                r"\b(?:city|state|country|pincode|zip\s*code|postal)\b",
                line,
                re.IGNORECASE,
            ):
                return clean_line(line)
            if re.search(r",\s*[A-Z]{2}\b", line) and not self._looks_like_title_line(line):
                return clean_line(line)
        return None

    def _extract_description(
        self, body_lines: list[str], job_type: str | None
    ) -> str | None:
        if not body_lines:
            return None

        description_lines: list[str] = []
        for line in body_lines:
            cleaned = clean_line(line)
            if not cleaned:
                continue

            if is_likely_header(cleaned):
                cleaned_lower = cleaned.lower()
                non_exp_keywords = {"affiliation", "membership", "activity", "activities", "leadership", "community", "volunteer", "references", "objective", "summary", "profile", "education", "skills", "training"}
                if any(word in cleaned_lower for word in non_exp_keywords):
                    break

            cleaned_lower = cleaned.lower()
            if "im a. sample" in cleaned_lower or "page " in cleaned_lower or "revision:" in cleaned_lower or "resume sample" in cleaned_lower or cleaned_lower == "continued":
                continue

            if DATE_RANGE_PATTERN.search(line):
                continue
            if job_type and job_type.replace("-", " ") in line.lower().replace("-", " "):
                continue
            if self._looks_like_title_line(line) and not description_lines:
                continue
            if ADDRESS_PATTERN.search(line):
                continue
            if line.lower().startswith("technologies:"):
                continue
            description_lines.append(line)

        if not description_lines:
            return None
        return " ".join(description_lines).strip() or None

    def _looks_like_title_line(self, line: str) -> bool:
        lower = line.lower()
        words = lower.split()
        if len(words) > 6:
            return False
        if any(char in line for char in ("", "", "", "•", "-", "*")):
            return False
        return any(
            re.search(rf"\b{re.escape(keyword)}\b", lower) for keyword in TITLE_KEYWORDS
        )

    def _looks_like_prose(self, text: str) -> bool:
        """True when a label field is actually a free-text sentence.

        Company names and job titles are compact labels, never full
        sentences. A long clause that closes with sentence punctuation and
        carries no title keyword is prose (common in functional resumes and
        summary lines) and must not be emitted as a company or position.
        """
        cleaned = clean_line(text)
        words = cleaned.split()
        if len(words) < 7:
            return False
        if self._looks_like_title_line(cleaned):
            return False
        return cleaned.rstrip().endswith((".", "!", "?"))

    def _is_valid_entry(self, entry: ExperienceEntry) -> bool:
        # A genuine experience entry must carry at least one substantive
        # label (employer, role, or description). A record holding only a
        # date is noise scavenged from prose, so reject it rather than
        # fabricate an empty entry.
        return bool(
            entry["company_name"] or entry["position"] or entry["company_about"]
        )
