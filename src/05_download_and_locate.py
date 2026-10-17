"""Download the account filings we need and find the staff costs page in each.

Which filings: each filing shows this year and last year. So for a club that was in the
Premier League for all ten seasons, five filings (FY2025, 2023, 2021, 2019, 2017) cover
all ten seasons, and the odd years give a cross-check later. The greedy plan below picks
the fewest filings that cover every season a club was in the league.

Season mapping: a financial year ending in calendar year Y covers season (Y-1)/Y. That
holds for all three year-ends in this data (31 May, 30 June, 31 July) because the
Premier League season finishes in May.

Resumable: PDFs and results are cached, so a rerun carries on where it stopped.
"""
import json
import sqlite3
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values

from ocr_tools import find_staff_pages, save_page_image

ROOT = Path(__file__).resolve().parent.parent
KEY = dotenv_values(ROOT / ".env")["COMPANIES_HOUSE_API_KEY"]
PDF_DIR = ROOT / "data" / "raw" / "accounts"
PAGE_DIR = ROOT / "data" / "processed" / "pages"
RESULT_PATH = ROOT / "data" / "processed" / "staff_pages.json"


def plan_filings():
    clubs = pd.read_csv(ROOT / "data" / "club_companies.csv", dtype=str)
    filings = pd.read_csv(ROOT / "data" / "processed" / "filings.csv", dtype=str).fillna("")
    filings = filings[filings["type"].str.startswith("accounts-with-accounts-type")].copy()
    filings["fy"] = filings["accounts_made_up_to"].str[:4].astype(int)
    table = pd.read_sql("select season, club from league_table", sqlite3.connect(ROOT / "data" / "football.db"))

    plan = []
    for club in clubs.itertuples():
        needed = sorted({int(s[:4]) + 1 for s in table.loc[table["club"] == club.club, "season"]})
        own = filings[filings["company_number"] == club.company_number].sort_values("filed_on")
        by_fy = own.groupby("fy").tail(1).set_index("fy")  # latest filing per year, in case of amendments
        covered = set()
        for fy in sorted(needed, reverse=True):
            if fy in covered:
                continue
            # Prefer the filing for this year; else use next year's, whose comparative column covers it.
            pick = fy if fy in by_fy.index else (fy + 1 if fy + 1 in by_fy.index else None)
            if pick is None:
                plan.append({"club": club.club, "company_number": club.company_number, "fy_needed": fy, "made_up_to": "", "url": ""})
                covered.add(fy)
                continue
            row = by_fy.loc[pick]
            plan.append({"club": club.club, "company_number": club.company_number, "fy_needed": fy,
                         "made_up_to": row["accounts_made_up_to"], "url": row["document_metadata_url"]})
            covered.update({pick, pick - 1})
    return pd.DataFrame(plan).drop_duplicates(["company_number", "made_up_to", "fy_needed"])


def download(url, target):
    for attempt in range(1, 6):
        try:
            r = requests.get(url + "/content", auth=(KEY, ""), headers={"Accept": "application/pdf"}, timeout=120)
            time.sleep(0.6)
            if r.status_code == 429:
                time.sleep(60)
                continue
            r.raise_for_status()
            target.write_bytes(r.content)
            return
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 5:
                raise
            time.sleep(5 * attempt)


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    plan = plan_filings()
    plan.to_csv(ROOT / "data" / "processed" / "filing_plan.csv", index=False)
    print(f"Plan: {len(plan)} filings for {plan['club'].nunique()} clubs", flush=True)

    results = json.loads(RESULT_PATH.read_text()) if RESULT_PATH.exists() else {}
    for row in plan.itertuples():
        if not row.url:
            print(f"{row.club} FY{row.fy_needed}: no filing available", flush=True)
            continue
        key = f"{row.company_number}_{row.made_up_to}"
        if key in results:
            continue
        pdf_path = PDF_DIR / f"{key}.pdf"
        if not pdf_path.exists():
            download(row.url, pdf_path)
        try:
            hits = find_staff_pages(pdf_path)
        except Exception as error:  # a corrupt PDF should not stop the whole run
            hits, note = [], f"error: {error}"
        else:
            note = ""
        for page_number, _ in hits[:2]:
            save_page_image(pdf_path, page_number, PAGE_DIR / f"{key}_p{page_number}.png")
        results[key] = {"club": row.club, "pages": hits, "note": note}
        RESULT_PATH.write_text(json.dumps(results, indent=1))
        print(f"{row.club} {row.made_up_to}: pages {hits[:2]} {note}", flush=True)


if __name__ == "__main__":
    main()
