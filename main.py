"""FastAPI wrapper around the Resume Parser library."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

from resume_parser import ResumeParser
from resume_parser.exceptions import ResumeParserError, UnsupportedFormatError, EmptyDocumentError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Resume Parser API",
    description="FastAPI wrapper exposing the Resume Parser library",
    version="1.0.0",
)


@app.post(
    "/parse",
    summary="Parse a resume file",
    description="Upload a PDF, DOC, or DOCX resume to extract structured data.",
    response_description="Parsed resume details in structured JSON format.",
)
async def parse_resume(file: UploadFile = File(...)):
    # 1. Validate file exists and has a filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    # 2. Validate file extension (Input Validation)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".doc", ".docx"):
        logger.warning(f"Unsupported file type upload attempted: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed formats: .pdf, .doc, .docx"
        )

    # 3. Validate empty file (Input Validation)
    content = await file.read(1)
    if not content:
        logger.warning(f"Empty file uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    await file.seek(0)  # Reset stream position

    # 4. Save to temporary file on disk for parsing
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            shutil.copyfileobj(file.file, temp_file)
    except Exception as e:
        logger.exception("Failed to write uploaded file to disk.")
        raise HTTPException(status_code=500, detail=f"Failed to process file upload: {str(e)}")

    # 5. Parse using ResumeParser
    try:
        logger.info(f"Parsing uploaded file {file.filename} (temp path: {temp_path})")
        parser = ResumeParser()
        result = parser.parse_file(temp_path)
        return result
    except UnsupportedFormatError as e:
        logger.warning(f"Parser reported unsupported format: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except EmptyDocumentError as e:
        logger.warning(f"Parser reported empty document: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ResumeParserError as e:
        logger.error(f"Parser exception occurred: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Internal server error during parsing.")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # 6. Always clean up temporary file
        try:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"Cleaned up temporary file: {temp_path}")
        except Exception as cleanup_err:
            logger.error(f"Failed to delete temp file {temp_path}: {cleanup_err}")
