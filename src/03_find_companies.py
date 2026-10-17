"""Search Companies House for each club's legal entity and print candidates to review.

Why a human review step: a search for "Arsenal" returns shops and fan clubs as well as the
club. We print the top matches, pick the right company number by hand, and record it in
data/club_companies.csv with a note, so the choice is documented and can be challenged.
"""
import sqlite3
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
KEY = dotenv_values(ROOT / ".env")["COMPANIES_HOUSE_API_KEY"]
BASE = "https://api.company-information.service.gov.uk"

# Legal names often differ from the name on the shirt.
SEARCH_NAMES = {
    "Arsenal": "Arsenal Football Club",
    "Aston Villa": "Aston Villa Football Club",
    "AFC Bournemouth": "AFC Bournemouth",
    "Brentford": "Brentford Football Club",
    "Brighton & Hove Albion": "Brighton & Hove Albion Football Club",
    "Burnley": "Burnley Football Club",
    "Cardiff City": "Cardiff City Football Club",
    "Chelsea": "Chelsea Football Club",
    "Crystal Palace": "Crystal Palace Football Club",
    "Everton": "Everton Football Club Company",
    "Fulham": "Fulham Football Club",
    "Huddersfield Town": "Huddersfield Town Football Club",
    "Hull City": "Hull City Tigers",
    "Ipswich Town": "Ipswich Town Football Club",
    "Leeds United": "Leeds United Football Club",
    "Leicester City": "Leicester City Football Club",
    "Liverpool": "The Liverpool Football Club and Athletic Grounds",
    "Luton Town": "Luton Town Football Club",
    "Manchester City": "Manchester City Football Club",
    "Manchester United": "Manchester United Football Club",
    "Middlesbrough": "Middlesbrough Football Club",
    "Newcastle United": "Newcastle United Football Company",
    "Norwich City": "Norwich City Football Club",
    "Nottingham Forest": "Nottingham Forest Football Club",
    "Sheffield United": "Sheffield United Football Club",
    "Southampton": "Southampton Football Club",
    "Stoke City": "Stoke City Football Club",
    "Sunderland": "Sunderland Association Football Club",
    "Swansea City": "Swansea City Association Football Club",
    "Tottenham Hotspur": "Tottenham Hotspur Football and Athletic",
    "Watford": "Watford Association Football Club",
    "West Bromwich Albion": "West Bromwich Albion Football Club",
    "West Ham United": "West Ham United Football Club",
    "Wolverhampton Wanderers": "Wolverhampton Wanderers Football Club",
}


def main():
    clubs = [r[0] for r in sqlite3.connect(ROOT / "data" / "football.db").execute("select distinct club from league_table order by club")]
    missing = [c for c in clubs if c not in SEARCH_NAMES]
    print(f"{len(clubs)} clubs in database; no search name for: {missing}\n")
    for club in clubs:
        q = SEARCH_NAMES.get(club, club)
        r = requests.get(f"{BASE}/search/companies", params={"q": q, "items_per_page": 4}, auth=(KEY, ""), timeout=30)
        r.raise_for_status()
        print(f"{club}  (searched: {q})")
        for it in r.json().get("items", []):
            print(f"   {it['company_number']} | {it['title']} | {it.get('company_status')}")
        time.sleep(0.7)  # stay well inside the 600 requests / 5 minutes limit


if __name__ == "__main__":
    main()
