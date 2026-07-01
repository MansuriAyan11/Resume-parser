import json
import sys
from pathlib import Path

# Add workspace to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from resume_parser import ResumeParser

def main():
    pdf_path = Path("C:/Intership_Task/Learning/resume-sample.pdf")
    output_path = PROJECT_ROOT / "output_validation.json"
    
    print(f"Parsing {pdf_path}...")
    parser = ResumeParser()
    try:
        result = parser.parse_file(pdf_path)
        
        # Write to JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"Success! Output written to {output_path}")
        print(f"Summary:")
        print(f"  Experience entries: {len(result.get('experience', []))}")
        print(f"  Education entries: {len(result.get('education', []))}")
        print(f"  Skills: {len(result.get('skills', []))}")
        print(f"  Languages: {len(result.get('languages', []))}")
    except Exception as e:
        print("Error during parsing:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
