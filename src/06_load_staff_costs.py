"""Load the hand-read staff costs into the database and make them comparable.

Input:  data/staff_costs.csv (one row per figure read off an accounts page, with page reference)
Output: table staff_costs in data/football.db, one row per club-season

Decisions made here, in the order they happen:
1. Rows marked EXCLUDE are dropped (wrong company).
2. Period length is worked out from the gap between a company's accounts dates, because
   some clubs changed year-end and filed 11, 13 or 14 month periods.
3. Each figure is annualised to 12 months: total * 12 / months.
4. If a season appears twice (as the current year in one filing and the comparative in the
   next) the current-year figure is kept and the difference is stored, so restatements show up.
5. Seasons the club was not in the Premier League are dropped.
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "football.db"


def months_between(end, previous_end):
    return round((end - previous_end).days / 30.4375)


def period_months(row, filings):
    """Length in months of the accounting period that ends on row.period_end."""
    company = row["company_number"].split("+")[0]
    own = filings[filings["company_number"] == company]["accounts_made_up_to"].drop_duplicates().sort_values().tolist()
    end = row["period_end"]
    earlier = [d for d in own if d < end]
    if end not in own or not earlier:
        return 12  # first filing in our window or a date we do not recognise: assume a normal year
    return months_between(end, earlier[-1])


def main():
    raw = pd.read_csv(ROOT / "data" / "staff_costs.csv", dtype={"company_number": str})
    raw = raw[raw["sum_check"] != "EXCLUDE"].copy()
    raw["period_end"] = pd.to_datetime(raw["period_end"])

    filings = pd.read_csv(ROOT / "data" / "processed" / "filings.csv", dtype=str)
    filings = filings[filings["type"].str.startswith("accounts-with-accounts-type")].copy()
    filings["accounts_made_up_to"] = pd.to_datetime(filings["accounts_made_up_to"])

    raw["months"] = raw.apply(lambda r: period_months(r, filings), axis=1)
    raw["staff_costs_annualised_k"] = raw["total_staff_costs_k"] * 12 / raw["months"]
    raw["wages_annualised_k"] = pd.to_numeric(raw["wages_salaries_k"], errors="coerce") * 12 / raw["months"]

    table = pd.read_sql("select season, club from league_table", sqlite3.connect(DB_PATH))
    in_league = set(zip(table["club"], table["season"]))
    raw = raw[[(c, s) in in_league for c, s in zip(raw["club"], raw["season"])]]

    current = raw[raw["column"] == "current"].set_index(["club", "season"])
    comparative = raw[raw["column"] == "comparative"].set_index(["club", "season"])
    both = current.index.intersection(comparative.index)
    restated = (comparative.loc[both, "total_staff_costs_k"] - current.loc[both, "total_staff_costs_k"]).rename("restatement_k")

    keep = raw.sort_values("column")  # 'comparative' sorts before 'current', so keep last = current
    keep = keep.drop_duplicates(["club", "season"], keep="last")
    keep = keep.merge(restated.reset_index(), on=["club", "season"], how="left")
    out = keep[["club", "season", "company_number", "period_end", "months", "total_staff_costs_k", "staff_costs_annualised_k",
                "wages_salaries_k", "column", "source_pdf", "source_page", "sum_check", "restatement_k", "note"]].copy()
    out["period_end"] = out["period_end"].dt.strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as conn:
        out.to_sql("staff_costs", conn, if_exists="replace", index=False)
    print(f"Loaded {len(out)} club-seasons of {len(in_league)}")
    odd = out[out["months"] != 12][["club", "season", "months"]]
    print("Non-12-month periods annualised:\n", odd.to_string(index=False))
    flagged = out[out["restatement_k"].abs() > 0][["club", "season", "restatement_k"]]
    print("Comparative differs from the current-year figure:\n", flagged.to_string(index=False))


if __name__ == "__main__":
    main()
