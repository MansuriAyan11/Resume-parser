"""Typed schemas for resume parser output."""

from __future__ import annotations

from typing import Any, TypedDict


class ExperienceEntry(TypedDict):
    company_name: str | None
    position: str | None
    start_date: str | None
    end_date: str | None
    current: bool
    job_type: str | None
    company_address: str | None
    company_about: str | None


class EducationEntry(TypedDict):
    school_name: str | None
    class_name: str | None
    passing_year: str | None
    start_year: str | None
    degree: str | None


class ParsedResume(TypedDict):
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    skills: list[str]
    languages: list[str]


def empty_experience_entry() -> ExperienceEntry:
    return {
        "company_name": None,
        "position": None,
        "start_date": None,
        "end_date": None,
        "current": False,
        "job_type": None,
        "company_address": None,
        "company_about": None,
    }


def empty_education_entry() -> EducationEntry:
    return {
        "school_name": None,
        "class_name": None,
        "passing_year": None,
        "start_year": None,
        "degree": None,
    }


def empty_parsed_resume() -> ParsedResume:
    return {
        "experience": [],
        "education": [],
        "skills": [],
        "languages": [],
    }


def parsed_resume_to_dict(resume: ParsedResume) -> dict[str, Any]:
    """Return a JSON-serializable dictionary."""
    return {
        "experience": [dict(entry) for entry in resume["experience"]],
        "education": [dict(entry) for entry in resume["education"]],
        "skills": list(resume["skills"]),
        "languages": list(resume["languages"]),
    }
