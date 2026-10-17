"""Create the SQL views and print a few example queries so the results are easy to inspect."""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "football.db"

EXAMPLES = {
    "Season summary (concentration of staff costs)": "SELECT * FROM v_season_summary",
    "Club-seasons where position beat wage rank by 8+ places": """
        SELECT season, club, wage_rank, position, wage_rank - position AS places_gained
        FROM v_wage_index
        WHERE wage_rank - position >= 8
        ORDER BY places_gained DESC""",
    "Club-seasons where position fell 8+ places below wage rank": """
        SELECT season, club, wage_rank, position, wage_rank - position AS places_gained
        FROM v_wage_index
        WHERE position - wage_rank >= 8
        ORDER BY places_gained""",
}


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript((ROOT / "sql" / "01_views.sql").read_text(encoding="utf-8"))
        for title, query in EXAMPLES.items():
            print(f"\n{title}")
            print(pd.read_sql(query, conn).to_string(index=False))


if __name__ == "__main__":
    main()
