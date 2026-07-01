"""
Integration example: how an existing API can call the resume parser.

This file demonstrates patterns for FastAPI, Flask, and plain Python services.
The parser module itself has NO web framework dependency.
"""

from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from resume_parser import ResumeParser, parse_resume, parse_resume_bytes
from resume_parser.exceptions import (
    EmptyDocumentError,
    ResumeParserError,
    TextExtractionError,
    UnsupportedFormatError,
)
from resume_parser.logging_config import configure_logging

configure_logging("INFO")

_parser = ResumeParser()


def parse_resume_safe(file_path: str | Path) -> dict[str, Any]:
    """
    Wrapper with standardized error responses for API integration.

    Returns:
        {"success": True, "data": {...}} on success
        {"success": False, "error": "...", "error_type": "..."} on failure
    """
    try:
        data = _parser.parse_file(file_path)
        return {"success": True, "data": data}
    except UnsupportedFormatError as exc:
        return {"success": False, "error": str(exc), "error_type": "unsupported_format"}
    except EmptyDocumentError as exc:
        return {"success": False, "error": str(exc), "error_type": "empty_document"}
    except TextExtractionError as exc:
        return {"success": False, "error": str(exc), "error_type": "extraction_failed"}
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc), "error_type": "file_not_found"}
    except ResumeParserError as exc:
        return {"success": False, "error": str(exc), "error_type": "parser_error"}


# ---------------------------------------------------------------------------
# FastAPI integration pattern (your API team adds this to their codebase)
# ---------------------------------------------------------------------------
#
# from fastapi import FastAPI, UploadFile, File, HTTPException
# from resume_parser import ResumeParser
# from resume_parser.exceptions import ResumeParserError, UnsupportedFormatError
# from resume_parser.logging_config import configure_logging
#
# configure_logging("INFO")
# app = FastAPI()
# parser = ResumeParser()
#
#
# @app.post("/parse-resume")
# async def parse_resume_endpoint(file: UploadFile = File(...)):
#     try:
#         content = await file.read()
#         extension = Path(file.filename or "").suffix
#         result = parser.parse_bytes(content, extension)
#         return {"success": True, "data": result}
#     except UnsupportedFormatError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))
#     except ResumeParserError as exc:
#         raise HTTPException(status_code=422, detail=str(exc))
#
# ---------------------------------------------------------------------------
# Flask integration pattern
# ---------------------------------------------------------------------------
#
# from flask import Flask, request, jsonify
# from resume_parser import ResumeParser
#
# app = Flask(__name__)
# parser = ResumeParser()
#
#
# @app.route("/parse-resume", methods=["POST"])
# def parse_resume_route():
#     if "file" not in request.files:
#         return jsonify({"success": False, "error": "No file uploaded"}), 400
#     upload = request.files["file"]
#     result = parser.parse_upload(upload.stream, upload.filename)
#     return jsonify({"success": True, "data": result})
#
# ---------------------------------------------------------------------------


def demo_integration() -> None:
    """Run a local integration demo without a web server."""
    sample_path = Path(__file__).parent / "sample_data" / "sample_resume.docx"

    if not sample_path.exists():
        from examples.create_sample_files import create_sample_docx

        create_sample_docx(sample_path)

    print("1. Direct function call:")
    result = parse_resume(sample_path)
    print(json.dumps(result, indent=2)[:500], "...\n")

    print("2. Safe wrapper for API layer:")
    response = parse_resume_safe(sample_path)
    print(json.dumps(response, indent=2)[:500], "...\n")

    print("3. Bytes-based parsing (simulates uploaded file):")
    content = sample_path.read_bytes()
    bytes_result = parse_resume_bytes(content, ".docx")
    print(f"   Parsed {len(bytes_result['experience'])} experience entries from bytes")

    print("4. File-like upload simulation:")
    upload = BytesIO(content)
    upload_result = _parser.parse_upload(upload, "candidate_resume.docx")
    print(f"   Skills found: {upload_result['skills']}")


if __name__ == "__main__":
    demo_integration()
