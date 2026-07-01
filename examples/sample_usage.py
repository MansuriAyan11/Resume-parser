"""Sample usage script for the resume parser module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from resume_parser import ResumeParser, parse_resume
from resume_parser.exceptions import ResumeParserError
from resume_parser.logging_config import configure_logging


def main() -> int:
    configure_logging("INFO")

    sample_dir = Path(__file__).parent / "sample_data"
    sample_docx = sample_dir / "sample_resume.docx"
    sample_pdf = sample_dir / "sample_resume.pdf"
    sample_doc = sample_dir / "sample_resume.doc"

    if not sample_docx.exists() or not sample_pdf.exists() or not sample_doc.exists():
        print("Sample files not found. Generating sample resumes...")
        from examples.create_sample_files import create_sample_docx, create_sample_pdf
        
        # NOTE: sample_doc is manually created by just copying docx to doc if missing for quick testing, although a real doc is OLE format. Let's just create them if missing.
        create_sample_docx(sample_docx)
        create_sample_pdf(sample_pdf)
        # Create a dummy doc as copy of docx since in the directory it had same size
        import shutil
        shutil.copy2(sample_docx, sample_doc)

    parser = ResumeParser()

    for sample_file in (sample_docx, sample_pdf, sample_doc):
        print(f"\n{'=' * 60}")
        print(f"Parsing: {sample_file.name}")
        print("=" * 60)

        try:
            result = parser.parse_file(sample_file)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except ResumeParserError as exc:
            print(f"Parser error: {exc}")
            return 1
        except FileNotFoundError as exc:
            print(f"File error: {exc}")
            return 1

    print("\nUsing convenience function parse_resume():")
    result = parse_resume(sample_docx)
    print(f"  Experience entries: {len(result['experience'])}")
    print(f"  Education entries: {len(result['education'])}")
    print(f"  Skills: {len(result['skills'])}")
    print(f"  Languages: {len(result['languages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
