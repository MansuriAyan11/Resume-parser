# Resume Parser Module

Production-ready Python module for extracting structured data from PDF, DOC, and DOCX resumes. Designed to be integrated into an existing API — no web framework or deployment code included.

## Features

- **Multi-format support**: PDF (PyMuPDF), DOCX (python-docx), DOC (multi-strategy fallback)
- **Flexible section detection**: Recognizes many header variants (Experience, Work History, Employment, etc.)
- **Structured output**: JSON-compatible Python dictionary
- **Production quality**: Type hints, logging, modular architecture, proper exception handling
- **API-ready**: Parse from file path, bytes, or file-like upload objects

## Project Structure

```
Resume_parser/
├── resume_parser/
│   ├── __init__.py              # Public API exports
│   ├── parser.py                # Main ResumeParser orchestrator
│   ├── exceptions.py            # Custom exceptions
│   ├── logging_config.py        # Logging setup
│   ├── extractors/              # PDF, DOC, DOCX text extraction
│   ├── parsers/                 # Section detection & field parsers
│   ├── models/                  # TypedDict output schemas
│   └── utils/                   # Date/text utilities & constants
├── examples/
│   ├── sample_usage.py          # Runnable demo
│   ├── integration_example.py   # API integration patterns
│   └── create_sample_files.py   # Generate test resumes
├── requirements.txt
└── README.md
```

## Installation

### 1. Navigate to the project folder

```bash
cd Resume_parser
```

### 2. Create and activate a virtual environment (recommended)

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate sample files and run the demo

```bash
python examples/create_sample_files.py
python examples/sample_usage.py
```

## Quick Start

```python
from resume_parser import parse_resume, ResumeParser
from resume_parser.logging_config import configure_logging

configure_logging("INFO")

# Option 1: One-liner
result = parse_resume("path/to/resume.pdf")

# Option 2: Reusable parser instance
parser = ResumeParser()
result = parser.parse_file("path/to/resume.docx")

# Option 3: From uploaded bytes (for API integration)
with open("resume.pdf", "rb") as f:
    result = parser.parse_bytes(f.read(), ".pdf")
```

## Output Schema

```json
{
  "experience": [
    {
      "company_name": "Tech Solutions Inc.",
      "position": "Senior Software Engineer",
      "start_date": "2022-01",
      "end_date": null,
      "current": true,
      "job_type": "full-time",
      "company_address": "123 Innovation Drive, San Francisco, CA",
      "company_about": "Led development of microservices platform..."
    }
  ],
  "education": [
    {
      "school_name": "Stanford University",
      "class_name": "CGPA: 3.8",
      "passing_year": "2019",
      "start_year": "2017",
      "degree": "Master of Science in Computer Science"
    }
  ],
  "skills": ["Python", "Java", "SQL", "Machine Learning"],
  "languages": ["English", "Hindi", "Spanish"]
}
```

Unavailable fields return `null` (for object fields) or `[]` (for lists).

## Integration with an Existing API

Copy the entire `resume_parser/` folder into your project, then call it from your API layer.

### FastAPI Example

```python
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from resume_parser import ResumeParser
from resume_parser.exceptions import ResumeParserError, UnsupportedFormatError
from resume_parser.logging_config import configure_logging

configure_logging("INFO")
app = FastAPI()
parser = ResumeParser()


@app.post("/internal/parse-resume")
async def parse_resume_endpoint(file: UploadFile = File(...)):
    try:
        content = await file.read()
        extension = Path(file.filename or "").suffix
        result = parser.parse_bytes(content, extension)
        return {"success": True, "data": result}
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ResumeParserError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
```

### Flask Example

```python
from flask import Flask, request, jsonify
from resume_parser import ResumeParser

app = Flask(__name__)
parser = ResumeParser()


@app.route("/internal/parse-resume", methods=["POST"])
def parse_resume_route():
    upload = request.files.get("file")
    if not upload:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    result = parser.parse_upload(upload.stream, upload.filename)
    return jsonify({"success": True, "data": result})
```

See `examples/integration_example.py` for a complete integration demo with error handling wrappers.

## Public API

| Function / Class | Description |
|---|---|
| `ResumeParser()` | Main parser class |
| `ResumeParser.parse_file(path)` | Parse from file path |
| `ResumeParser.parse_bytes(content, extension)` | Parse from raw bytes |
| `ResumeParser.parse_upload(file_obj, filename)` | Parse from file-like upload |
| `parse_resume(path)` | Convenience function |
| `parse_resume_bytes(content, extension)` | Convenience function |
| `configure_logging(level)` | Enable module logging |

## Exceptions

| Exception | When raised |
|---|---|
| `UnsupportedFormatError` | File extension is not `.pdf`, `.doc`, or `.docx` |
| `TextExtractionError` | Text could not be extracted from the document |
| `EmptyDocumentError` | Document contains no readable text |
| `ResumeParserError` | Base class for all parser errors |

## Supported Section Headers

The parser recognizes common resume section variants:

- **Experience**: Experience, Professional Experience, Work History, Employment History, Employment, Career History, etc.
- **Education**: Education, Academic Background, Qualifications, etc.
- **Skills**: Skills, Technical Skills, Core Competencies, Expertise, etc.
- **Languages**: Languages, Language Proficiency, Language Skills

## Logging

```python
from resume_parser.logging_config import configure_logging

configure_logging("DEBUG")  # DEBUG | INFO | WARNING | ERROR
```

## Example Input / Output

**Input** (excerpt from a DOCX resume):

```
PROFESSIONAL EXPERIENCE
Senior Software Engineer
Tech Solutions Inc.
Jan 2022 - Present

EDUCATION
Master of Science in Computer Science
Stanford University
2017 - 2019

SKILLS
Python, Java, SQL, Machine Learning

LANGUAGES
English (Native), Hindi (Fluent)
```

**Output**:

```python
{
    "experience": [
        {
            "company_name": "Tech Solutions Inc.",
            "position": "Senior Software Engineer",
            "start_date": "2022-01",
            "end_date": None,
            "current": True,
            "job_type": "full-time",
            "company_address": None,
            "company_about": None
        }
    ],
    "education": [
        {
            "school_name": "Stanford University",
            "class_name": "CGPA: 3.8",
            "passing_year": "2019",
            "start_year": "2017",
            "degree": "Master of Science in Computer Science"
        }
    ],
    "skills": ["Python", "Java", "SQL", "Machine Learning", "NLP", "Docker", "Git", "REST APIs", "TensorFlow"],
    "languages": ["English", "Hindi", "Spanish"]
}
```

## Notes on DOC Files

Legacy `.doc` files use multiple extraction strategies:

1. Attempt DOCX parsing (for mislabeled files)
2. Use `antiword` CLI if installed on the system
3. OLE compound document stream extraction
4. Binary text scan fallback

For best `.doc` results on Linux, install antiword: `sudo apt-get install antiword`

## License

Internal internship project — use within your organization.
