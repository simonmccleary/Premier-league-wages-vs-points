"""Find the page of a scanned accounts PDF that holds the staff costs note.

Why OCR here and not for the numbers: OCR reliably spots a heading like "Employees" but
can swap digits (5 for 6, 1 for 7). So OCR locates the page, a person reads the figures,
and the figures are checked (components must sum to the total).
"""
import re
from pathlib import Path

import pdfplumber
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# A staff costs note usually contains these phrases together.
KEYWORDS = [r"wages and salaries", r"social security", r"staff costs|employee costs|payroll costs", r"average (monthly )?number"]


def score_page(text):
    text = text.lower()
    return sum(1 for pattern in KEYWORDS if re.search(pattern, text))


def find_staff_pages(pdf_path, min_score=2, resolution=110):
    """Return [(page_number, score)] for pages that look like the staff costs note, best first."""
    hits = []
    with pdfplumber.open(pdf_path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""  # works for text PDFs, empty for scans
            if len(text.strip()) < 50:
                text = pytesseract.image_to_string(page.to_image(resolution=resolution).original)
            score = score_page(text)
            if score >= min_score:
                hits.append((number, score))
    return sorted(hits, key=lambda h: -h[1])


def save_page_image(pdf_path, page_number, out_path, resolution=110):
    """Render one page to PNG so it can be read by eye."""
    with pdfplumber.open(pdf_path) as pdf:
        pdf.pages[page_number - 1].to_image(resolution=resolution).save(Path(out_path))


if __name__ == "__main__":
    import sys
    print(find_staff_pages(sys.argv[1]))
