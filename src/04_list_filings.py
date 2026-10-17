"""List each candidate company's account filings and which document formats exist.

Output: data/processed/filings.csv, one row per filing. This tells us, before we read a
single page, which filings are machine-readable (xhtml) and which are scanned PDFs, and
where a club has no accounts for a season.

Politeness: 0.6 seconds between requests keeps us under the 600 requests / 5 minutes limit.
"""
import csv
import json
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
KEY = dotenv_values(ROOT / ".env")["COMPANIES_HOUSE_API_KEY"]
AUTH = (KEY, "")
BASE = "https://api.company-information.service.gov.uk"

# club -> list of candidate company numbers. More than one means "check which one holds the football accounts".
CANDIDATES = {
    "AFC Bournemouth": ["06632170"],
    "Arsenal": ["00109244"],
    "Aston Villa": ["03375789", "00046572", "02502822"],
    "Brentford": ["03642327"],
    "Brighton & Hove Albion": ["00081077"],
    "Burnley": ["00054222"],
    "Cardiff City": ["00109065", "04044254"],
    "Chelsea": ["01965149"],
    "Crystal Palace": ["07270793", "07206409"],
    "Everton": ["00036624"],
    "Fulham": ["02114486"],
    "Huddersfield Town": ["01771361"],
    "Hull City": ["04032392"],
    "Ipswich Town": ["00315421"],
    "Leeds United": ["06233875"],
    "Leicester City": ["04593477"],
    "Liverpool": ["00035668"],
    "Luton Town": ["06133975", "04977080"],
    "Manchester City": ["00040946"],
    "Manchester United": ["00095489"],
    "Middlesbrough": ["01947851", "03912084", "05324467"],
    "Newcastle United": ["00031014", "05981582", "02529667"],
    "Norwich City": ["00154044"],
    "Nottingham Forest": ["01630402"],
    "Sheffield United": ["00061564"],
    "Southampton": ["00053301"],
    "Stoke City": ["00099885"],
    "Sunderland": ["00049116"],
    "Swansea City": ["00123414", "04056708"],
    "Tottenham Hotspur": ["00057186", "01706358", "06279984"],
    "Watford": ["00104194"],
    "West Bromwich Albion": ["03295063"],
    "West Ham United": ["00066516"],
    "Wolverhampton Wanderers": ["01989823"],
}

FIRST_YEAR_END = "2015-05-01"  # earliest accounts we need: year ending mid-2016 covers 2015/16, and the one before gives context


def get(url, **params):
    """GET with retries. The API occasionally drops a connection; waiting and trying again fixes it."""
    for attempt in range(1, 6):
        try:
            response = requests.get(url, params=params, auth=AUTH, timeout=30)
            time.sleep(0.6)
            if response.status_code == 429:  # rate limited: back off for a minute
                time.sleep(60)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 5:
                raise
            time.sleep(5 * attempt)


def main():
    out_path = ROOT / "data" / "processed" / "filings.csv"
    cache_dir = ROOT / "data" / "raw" / "filings"  # one JSON per company, so a rerun resumes where it stopped
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for club, numbers in CANDIDATES.items():
        for number in numbers:
            cache_file = cache_dir / f"{number}.json"
            if cache_file.exists():
                company_rows = json.loads(cache_file.read_text(encoding="utf-8"))
            else:
                company = get(f"{BASE}/company/{number}")
                history = get(f"{BASE}/company/{number}/filing-history", category="accounts", items_per_page=40)
                company_rows = []
                for item in history.get("items", []):
                    made_up = item.get("description_values", {}).get("made_up_date", "")
                    if not made_up or made_up < FIRST_YEAR_END:
                        continue
                    meta_url = item.get("links", {}).get("document_metadata")
                    formats = ""
                    if meta_url:
                        formats = "|".join(get(meta_url).get("resources", {}).keys())
                    company_rows.append({
                        "club": club,
                        "company_number": number,
                        "company_name": company["company_name"],
                        "accounts_made_up_to": made_up,
                        "filed_on": item["date"],
                        "type": item.get("description", ""),
                        "formats": formats,
                        "document_metadata_url": meta_url or "",
                    })
                cache_file.write_text(json.dumps(company_rows), encoding="utf-8")
            rows.extend(company_rows)
            print(f"{club} / {number}: {len(company_rows)} filings", flush=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
