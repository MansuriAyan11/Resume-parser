"""Generate sample resume files for local testing."""

from __future__ import annotations

from pathlib import Path

SAMPLE_RESUME_TEXT = """
JOHN DOE
Software Engineer | john.doe@email.com | +1-555-0100

PROFESSIONAL EXPERIENCE

Senior Software Engineer
Tech Solutions Inc.
123 Innovation Drive, San Francisco, CA
Jan 2022 - Present
Full-time
Led development of microservices platform serving 2M+ users.
Implemented CI/CD pipelines and mentored junior developers.

Software Developer
DataCorp LLC, New York, NY
Jun 2019 - Dec 2021
Part-time
Built NLP pipelines for document classification.
Technologies: Python, spaCy, FastAPI.

EDUCATION

Master of Science in Computer Science
Stanford University
2017 - 2019
CGPA: 3.8

Bachelor of Technology in Information Technology
MIT College of Engineering
2013 - 2017
First Class with Distinction

SKILLS
Python, Java, SQL, Machine Learning, NLP, Docker, Git, REST APIs, TensorFlow

LANGUAGES
English (Native), Hindi (Fluent), Spanish (Basic)
"""


def create_sample_docx(output_path: Path) -> Path:
    """Create a sample DOCX resume for testing."""
    from docx import Document

    document = Document()
    for line in SAMPLE_RESUME_TEXT.strip().split("\n"):
        document.add_paragraph(line.strip())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


def create_sample_pdf(output_path: Path) -> Path:
    """Create a sample PDF resume for testing."""
    import fitz

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page()
    text_rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(text_rect, SAMPLE_RESUME_TEXT.strip(), fontsize=10, fontname="helv")
    document.save(str(output_path))
    document.close()
    return output_path


if __name__ == "__main__":
    base = Path(__file__).resolve().parent / "sample_data"
    docx_path = create_sample_docx(base / "sample_resume.docx")
    pdf_path = create_sample_pdf(base / "sample_resume.pdf")
    print(f"Created: {docx_path}")
    print(f"Created: {pdf_path}")
