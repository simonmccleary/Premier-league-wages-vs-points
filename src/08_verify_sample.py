"""Independent check: download a second filing for a sample of clubs and locate the staff costs page.

Each figure in staff_costs.csv taken from a comparative column is checked against the
current-year column in the following year's filing. A person then reads the page and
records the result in data/verification_log.csv.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium
import pytesseract
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
KEY = dotenv_values(ROOT / ".env")["COMPANIES_HOUSE_API_KEY"]
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PAGE_DIR = ROOT / "data" / "processed" / "pages"
PDF_DIR = ROOT / "data" / "raw" / "accounts"

# (company number, accounts made up to). Chosen because a comparative-year figure from the
# neighbouring filing is already in staff_costs.csv, and the sample spans group/company and
# year-end changes, where restatements are most likely.
SAMPLE = [
    ("00095489", "2022-06-30"),  # Man Utd: 2021/22 looks high next to its neighbours
    ("00040946", "2022-06-30"),  # Man City
    ("01965149", "2022-06-30"),  # Chelsea
    ("00109244", "2022-05-31"),  # Arsenal
    ("00031014", "2022-06-30"),  # Newcastle
    ("00057186", "2022-06-30"),  # Tottenham
    ("00036624", "2022-06-30"),  # Everton
    ("00035668", "2022-05-31"),  # Liverpool
]

filings = pd.read_csv(ROOT / "data" / "processed" / "filings.csv", dtype=str).fillna("")


def download(url, target):
    for attempt in range(1, 6):
        try:
            r = requests.get(url + "/content", auth=(KEY, ""), headers={"Accept": "application/pdf"}, timeout=180)
            time.sleep(0.6)
            r.raise_for_status()
            target.write_bytes(r.content)
            return
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 5:
                raise
            time.sleep(5 * attempt)


for company, made_up in SAMPLE:
    match = filings[(filings.company_number == company) & (filings.accounts_made_up_to == made_up) & (filings.type.str.startswith("accounts-with"))]
    if match.empty:
        print(company, made_up, "no filing", flush=True)
        continue
    key = f"{company}_{made_up}"
    pdf_path = PDF_DIR / f"{key}.pdf"
    if not pdf_path.exists():
        download(match.iloc[0].document_metadata_url, pdf_path)
    pdf = pdfium.PdfDocument(str(pdf_path))
    best = []
    for i in range(len(pdf)):
        text = pytesseract.image_to_string(pdf[i].render(scale=1.3).to_pil()).lower()
        score = sum(p in text for p in ("wages and salaries", "social security", "staff costs", "employee costs", "payroll"))
        if score >= 2:
            best.append((i + 1, score))
    best.sort(key=lambda x: -x[1])
    print(key, len(pdf), "pages", best[:3], flush=True)
    for page, _ in best[:2]:
        pdf[page - 1].render(scale=1.5).to_pil().save(PAGE_DIR / f"{key}_p{page}.png")
