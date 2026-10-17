"""Download Premier League match results, one CSV per season, from football-data.co.uk.

Why this source: it publishes free, stable CSV files for every season, so there is
no need to scrape a page. Being polite: one request per second, one file per season.
"""
import time
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# football-data.co.uk codes a season by its two year-ends: 1516 = 2015/16
SEASONS = ["1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]
URL = "https://football-data.co.uk/mmz4281/{code}/E0.csv"  # E0 = English Premier League


def main():
    for code in SEASONS:
        target = RAW_DIR / f"E0_{code}.csv"
        if target.exists():
            print(f"{code}: already downloaded, skipping")
            continue
        response = requests.get(URL.format(code=code), timeout=30)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"{code}: saved {len(response.content):,} bytes")
        time.sleep(1)


if __name__ == "__main__":
    main()
