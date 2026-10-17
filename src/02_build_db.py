"""Clean the raw match files, build each season's league table, and load SQLite.

Outputs data/football.db with two tables:
  matches       one row per match (3,800 rows for 10 seasons)
  league_table  one row per club per season (200 rows)

Every cleaning decision is recorded in docs/cleaning_log.md by hand; the key ones
are repeated as comments here.
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "football.db"

SEASON_CODES = ["1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]

# Club names differ between sources. This map is the single place we standardise them.
# football-data.co.uk uses short names; accounts at Companies House use legal names.
CLUB_NAME_FIXES = {
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Newcastle": "Newcastle United",
    "Tottenham": "Tottenham Hotspur",
    "West Ham": "West Ham United",
    "Wolves": "Wolverhampton Wanderers",
    "Leicester": "Leicester City",
    "Leeds": "Leeds United",
    "Norwich": "Norwich City",
    "Brighton": "Brighton & Hove Albion",
    "West Brom": "West Bromwich Albion",
    "Nott'm Forest": "Nottingham Forest",
    "Sheffield United": "Sheffield United",
    "Huddersfield": "Huddersfield Town",
    "Cardiff": "Cardiff City",
    "Swansea": "Swansea City",
    "Stoke": "Stoke City",
    "Hull": "Hull City",
    "Bournemouth": "AFC Bournemouth",
    "Ipswich": "Ipswich Town",
    "Luton": "Luton Town",
}

# Points deductions that football-data.co.uk results do not include.
# Source: Premier League announcements. Everton: 6 (Nov 2023, after appeal) + 2 (Apr 2024).
# Nottingham Forest: 4 (Apr 2024). Checked against the official final tables below.
POINT_DEDUCTIONS = {
    ("2023/24", "Everton"): -8,
    ("2023/24", "Nottingham Forest"): -4,
}


def season_label(code):
    return f"20{code[:2]}/{code[2:]}"


def load_matches():
    frames = []
    for code in SEASON_CODES:
        df = pd.read_csv(RAW_DIR / f"E0_{code}.csv", encoding="latin-1")
        # Keep only the columns we need: some seasons have extra betting columns, some don't.
        df = df[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]].dropna(how="any")
        df["season"] = season_label(code)
        frames.append(df)
    matches = pd.concat(frames, ignore_index=True)

    # Dates arrive as dd/mm/yy in some seasons and dd/mm/yyyy in others.
    matches["date"] = pd.to_datetime(matches["Date"], format="mixed", dayfirst=True)
    matches = matches.rename(
        columns={"HomeTeam": "home_team", "AwayTeam": "away_team", "FTHG": "home_goals", "FTAG": "away_goals", "FTR": "result"}
    ).drop(columns="Date")
    matches[["home_goals", "away_goals"]] = matches[["home_goals", "away_goals"]].astype(int)
    for col in ["home_team", "away_team"]:
        matches[col] = matches[col].str.strip().replace(CLUB_NAME_FIXES)
    return matches[["season", "date", "home_team", "away_team", "home_goals", "away_goals", "result"]]


def build_table(matches):
    home = matches.rename(columns={"home_team": "club", "home_goals": "gf", "away_goals": "ga"})[["season", "club", "gf", "ga"]]
    away = matches.rename(columns={"away_team": "club", "away_goals": "gf", "home_goals": "ga"})[["season", "club", "gf", "ga"]]
    long = pd.concat([home, away], ignore_index=True)
    long["won"] = (long["gf"] > long["ga"]).astype(int)
    long["drawn"] = (long["gf"] == long["ga"]).astype(int)
    long["lost"] = (long["gf"] < long["ga"]).astype(int)

    table = long.groupby(["season", "club"], as_index=False).agg(
        played=("gf", "size"), won=("won", "sum"), drawn=("drawn", "sum"), lost=("lost", "sum"), gf=("gf", "sum"), ga=("ga", "sum")
    )
    table["gd"] = table["gf"] - table["ga"]
    table["points"] = table["won"] * 3 + table["drawn"]
    table["points_deduction"] = [POINT_DEDUCTIONS.get((s, c), 0) for s, c in zip(table["season"], table["club"])]
    table["points"] = table["points"] + table["points_deduction"]

    # Premier League tie-break order: points, goal difference, goals scored.
    table = table.sort_values(["season", "points", "gd", "gf"], ascending=[True, False, False, False])
    table["position"] = table.groupby("season").cumcount() + 1
    return table.reset_index(drop=True)


def validate(matches, table):
    """Fail loudly if the data is not what we think it is."""
    per_season = matches.groupby("season").size()
    assert (per_season == 380).all(), f"expected 380 matches a season, got {per_season.to_dict()}"
    assert (table.groupby("season").size() == 20).all(), "expected 20 clubs a season"

    # Known champions and points, from the official final tables.
    champions = {
        "2015/16": ("Leicester City", 81), "2016/17": ("Chelsea", 93), "2017/18": ("Manchester City", 100),
        "2018/19": ("Manchester City", 98), "2019/20": ("Liverpool", 99), "2020/21": ("Manchester City", 86),
        "2021/22": ("Manchester City", 93), "2022/23": ("Manchester City", 89), "2023/24": ("Manchester City", 91),
        "2024/25": ("Liverpool", 84),
    }
    top = table[table["position"] == 1].set_index("season")
    for season, (club, pts) in champions.items():
        got = (top.loc[season, "club"], int(top.loc[season, "points"]))
        assert got == (club, pts), f"{season}: expected {(club, pts)}, got {got}"
    print("Validation passed: 380 matches and 20 clubs per season, and all 10 champions match.")


def main():
    matches = load_matches()
    table = build_table(matches)
    validate(matches, table)

    with sqlite3.connect(DB_PATH) as conn:
        matches.assign(date=matches["date"].dt.strftime("%Y-%m-%d")).to_sql("matches", conn, if_exists="replace", index=False)
        table.to_sql("league_table", conn, if_exists="replace", index=False)
    print(f"Wrote {len(matches)} matches and {len(table)} league table rows to {DB_PATH}")


if __name__ == "__main__":
    main()
