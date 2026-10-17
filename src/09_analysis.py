"""Analysis and charts: how much of league position do staff costs explain?

Method (kept as simple as the question allows):
  1. wage_index = club staff costs / average of that season's clubs (removes inflation).
  2. OLS: points = a + b * ln(wage_index), standard errors clustered by club because the
     same club appears in several seasons.
  3. Residual = actual points - predicted points. Positive = beat what its wages predict.
  4. R-squared and Spearman rank correlation by season, to see whether the link changed.
  5. Concentration of staff costs among the top six payers (the industrial economics angle).

Outputs: charts/*.png and dashboard/data.js (the data the HTML dashboard reads).
"""
import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "football.db"
CHART_DIR = ROOT / "charts"
DASH_DIR = ROOT / "dashboard"
CHART_DIR.mkdir(exist_ok=True)
DASH_DIR.mkdir(exist_ok=True)

# Palette: dark navy surface, dark-mode steps of the validated categorical palette.
SURFACE, INK, INK2, MUTED, GRID = "#0f1a2e", "#eef1f6", "#c3cad8", "#8a93a6", "#22304a"
BLUE, ORANGE, RED, AQUA = "#3987e5", "#d95926", "#e66767", "#199e70"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans",
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def load():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM v_wage_index", conn)
        seasons = pd.read_sql("SELECT * FROM v_season_summary", conn)
        reported = pd.read_sql("SELECT season, club, staff_costs_reported_k, months FROM v_club_season", conn)
    df = df.merge(reported, on=["season", "club"])
    df["ln_wi"] = np.log(df["wage_index"])
    return df, seasons


def fit(df):
    X = sm.add_constant(df["ln_wi"])
    groups = pd.factorize(df["club"])[0]
    return sm.OLS(df["points"], X).fit(cov_type="cluster", cov_kwds={"groups": groups})


def per_season(df):
    rows = []
    for season, g in df.groupby("season"):
        m = sm.OLS(g["points"], sm.add_constant(g["ln_wi"])).fit()
        rho = g["wage_rank"].corr(g["position"], method="spearman")
        rows.append({"season": season, "r2": m.rsquared, "slope": m.params["ln_wi"], "spearman": rho, "n": len(g)})
    return pd.DataFrame(rows)


def title(ax, text, sub=None):
    ax.set_title(text, loc="left", pad=22 if sub else 8, color=INK)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")


def chart_scatter(df, model):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(df["wage_index"], df["points"], s=34, color=BLUE, alpha=0.65, edgecolor=SURFACE, linewidth=1)
    xs = np.linspace(df["wage_index"].min(), df["wage_index"].max(), 100)
    ax.plot(xs, model.params["const"] + model.params["ln_wi"] * np.log(xs), color=INK2, lw=2)
    extremes = pd.concat([df.nlargest(5, "resid"), df.nsmallest(5, "resid")])
    ax.scatter(extremes["wage_index"], extremes["points"], s=46, color=ORANGE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    for r in extremes.itertuples():
        ax.annotate(f"{r.club} {r.season[2:4]}/{r.season[-2:]}", (r.wage_index, r.points), xytext=(6, 5),
                    textcoords="offset points", fontsize=8, color=INK2)
    ax.set_xscale("log")
    ax.set_xticks([0.4, 0.6, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.4x", "0.6x", "1x", "1.5x", "2x", "3x"])
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlim(0.25, 3.3)
    ax.set_xlabel("Staff costs relative to the league average that season (log scale)")
    ax.set_ylabel("League points")
    title(ax, f"Staff costs explain {model.rsquared:.0%} of the variation in league points",
          f"200 club-seasons, Premier League 2015/16 to 2024/25. Orange: the five biggest over- and under-performers.")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "01_wage_vs_points.png", dpi=160)
    plt.close(fig)


def chart_by_season(ps):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(ps))
    ax.plot(x, ps["r2"], color=BLUE, lw=2, marker="o", ms=6, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.plot(x, ps["spearman"] ** 2, color=ORANGE, lw=2, marker="o", ms=6, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels([s[2:] for s in ps["season"]], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Share of variation explained")
    ax.text(x[-1] + 0.15, ps["r2"].iloc[-1] + 0.035, "OLS R-squared", color=INK2, fontsize=9, va="center")
    ax.text(x[-1] + 0.15, (ps["spearman"] ** 2).iloc[-1] - 0.035, "Rank correlation squared", color=INK2, fontsize=9, va="center")
    ax.set_xlim(-0.3, len(ps) + 1.7)
    title(ax, "The wage-to-results link is strong in most seasons but dips sharply in some",
          "Each season fitted separately. Weakest: 2015/16 (Leicester title) and 2022/23. No trend up or down.")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "02_link_by_season.png", dpi=160)
    plt.close(fig)


def chart_residual_by_club(df):
    club = df.groupby("club").agg(seasons=("resid", "size"), avg=("resid", "mean")).query("seasons >= 3").sort_values("avg")
    colors = [BLUE if v >= 0 else RED for v in club["avg"]]
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(club.index, club["avg"], color=colors, height=0.6)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("Average points above (+) or below (-) what the club's staff costs predict")
    ax.grid(axis="y", visible=False)
    for y, (v, n) in enumerate(zip(club["avg"], club["seasons"])):
        ax.text(v + (0.6 if v >= 0 else -0.6), y, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=INK2)
    ax.set_xlim(club["avg"].min() - 4, club["avg"].max() + 4)
    title(ax, "Which clubs beat their wage bill, and which did not",
          "Clubs with at least three Premier League seasons in the window. Blue: above prediction. Red: below.")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "03_over_under_by_club.png", dpi=160)
    plt.close(fig)
    return club


def chart_concentration(seasons):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(seasons))
    ax.plot(x, seasons["top6_share_pct"], color=BLUE, lw=2, marker="o", ms=6, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels([s[2:] for s in seasons["season"]], fontsize=9)
    ax.set_ylim(40, 60)
    ax.set_ylabel("Top six payers, % of league staff costs")
    ax.annotate(f"{seasons['top6_share_pct'].iloc[-1]:.0f}%", (x[-1], seasons["top6_share_pct"].iloc[-1]), xytext=(8, 0),
                textcoords="offset points", color=INK2, fontsize=10, va="center")
    ax.set_xlim(-0.3, len(seasons) - 0.2)
    title(ax, "The six biggest payers account for about half of league staff costs, and that has not grown",
          "Share of the twenty clubs' combined annualised staff costs in each season.")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "04_concentration.png", dpi=160)
    plt.close(fig)


def chart_small_multiples(df):
    clubs = ["Brighton & Hove Albion", "Brentford", "Wolverhampton Wanderers", "AFC Bournemouth", "Leicester City", "Burnley"]
    seasons = sorted(df["season"].unique())
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharex=True, sharey=True)
    for ax, club in zip(axes.flat, clubs):
        g = df[df["club"] == club].set_index("season").reindex(seasons)
        ax.axhline(0, color=MUTED, lw=1)
        ax.plot(range(len(seasons)), g["resid"], color=BLUE, lw=2, marker="o", ms=6, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.set_title(club.replace(" & Hove Albion", "").replace("Wolverhampton Wanderers", "Wolves"), fontsize=10, loc="left", color=INK)
        ax.set_xticks(range(0, len(seasons), 3))
        ax.set_xticklabels([seasons[i][2:] for i in range(0, len(seasons), 3)], fontsize=8)
        ax.set_ylim(-40, 40)
    fig.text(0.01, 0.5, "Points above (+) or below (-) wage prediction", rotation=90, va="center", color=INK2, fontsize=9)
    fig.suptitle("Six clubs against their wage prediction, season by season", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0.03, 0, 1, 0.95))
    fig.savefig(CHART_DIR / "05_small_clubs.png", dpi=160)
    plt.close(fig)


def export_dashboard(df, seasons, ps, model):
    rows = df[["season", "club", "position", "points", "gd", "staff_costs_annualised_k", "staff_costs_reported_k", "months",
               "wage_index", "wage_rank", "fitted", "resid"]].copy()
    rows = rows.round({"staff_costs_annualised_k": 1, "staff_costs_reported_k": 1, "wage_index": 4, "fitted": 2, "resid": 2})
    payload = {
        "rows": rows.to_dict(orient="records"),
        "seasons": seasons.to_dict(orient="records"),
        "perSeason": ps.round(4).to_dict(orient="records"),
        "pooled": {"intercept": model.params["const"], "slope": model.params["ln_wi"], "r2": model.rsquared,
                   "slopeSE": model.bse["ln_wi"], "n": int(model.nobs)},
    }
    (DASH_DIR / "data.js").write_text("window.FOOTBALL_DATA = " + json.dumps(payload, default=float) + ";\n", encoding="utf-8")
    rows.to_csv(ROOT / "data" / "processed" / "club_season_analysis.csv", index=False)


def main():
    df, seasons = load()
    model = fit(df)
    df["fitted"] = model.params["const"] + model.params["ln_wi"] * df["ln_wi"]
    df["resid"] = df["points"] - df["fitted"]
    ps = per_season(df)

    print(model.summary().tables[1])
    print(f"R-squared {model.rsquared:.3f}, n = {int(model.nobs)}")
    print("\nPer season:\n", ps.round(3).to_string(index=False))
    print("\nTop over-performers:\n", df.nlargest(8, "resid")[["season", "club", "points", "fitted", "resid"]].round(1).to_string(index=False))
    print("\nTop under-performers:\n", df.nsmallest(8, "resid")[["season", "club", "points", "fitted", "resid"]].round(1).to_string(index=False))

    chart_scatter(df, model)
    chart_by_season(ps)
    club = chart_residual_by_club(df)
    print("\nClub averages:\n", club.round(1).to_string())
    chart_concentration(seasons)
    chart_small_multiples(df)
    export_dashboard(df, seasons, ps, model)
    print("\nCharts written to", CHART_DIR)


if __name__ == "__main__":
    main()
