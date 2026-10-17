-- Views used by the analysis and the dashboard.
-- Run with:  python src/07_run_sql.py   (it executes this file against data/football.db)
--
-- Why SQL here: joining tables, ranking within a group and comparing a row with its group
-- average are the three things analyst interviews test most. Each view below uses one of them.

DROP VIEW IF EXISTS v_club_season;
DROP VIEW IF EXISTS v_wage_index;
DROP VIEW IF EXISTS v_season_summary;
DROP VIEW IF EXISTS v_club_summary;

-- 1) JOIN: one row per club per season with results and staff costs side by side.
CREATE VIEW v_club_season AS
SELECT
    l.season,
    l.club,
    l.position,
    l.points,
    l.gd,
    l.gf,
    s.staff_costs_annualised_k,
    s.total_staff_costs_k AS staff_costs_reported_k,
    s.months,
    s.source_pdf,
    s.source_page,
    s.note
FROM league_table AS l
JOIN staff_costs  AS s
  ON s.club = l.club AND s.season = l.season;

-- 2) WINDOW FUNCTIONS: compare each club with the rest of its own season.
--    wage_index = club staff costs / average staff costs of the clubs we have for that season.
--    Using an index removes inflation: a club paying twice the league average is "2.0" in any year.
CREATE VIEW v_wage_index AS
SELECT
    season,
    club,
    position,
    points,
    gd,
    staff_costs_annualised_k,
    staff_costs_annualised_k * 1.0 / AVG(staff_costs_annualised_k) OVER (PARTITION BY season) AS wage_index,
    RANK() OVER (PARTITION BY season ORDER BY staff_costs_annualised_k DESC)                   AS wage_rank,
    COUNT(*) OVER (PARTITION BY season)                                                         AS clubs_with_data
FROM v_club_season;

-- 3) AGGREGATION: one row per season, used for the trend charts.
--    top6_share = share of the season's total staff costs paid by the six biggest payers.
--    hhi = Herfindahl-Hirschman index of staff-cost shares (0 to 10,000), the standard
--    concentration measure in industrial economics.
CREATE VIEW v_season_summary AS
WITH ranked AS (
    SELECT
        season,
        staff_costs_annualised_k AS cost,
        SUM(staff_costs_annualised_k) OVER (PARTITION BY season) AS total,
        RANK() OVER (PARTITION BY season ORDER BY staff_costs_annualised_k DESC) AS r
    FROM v_club_season
)
SELECT
    season,
    COUNT(*)                                                    AS clubs,
    ROUND(AVG(cost))                                            AS mean_cost_k,
    ROUND(SUM(CASE WHEN r <= 6 THEN cost ELSE 0 END) * 100.0 / MAX(total), 1) AS top6_share_pct,
    ROUND(SUM((cost * 100.0 / total) * (cost * 100.0 / total)), 0)            AS hhi
FROM ranked
GROUP BY season
ORDER BY season;

-- 4) AGGREGATION by club: average wage index and average league position across seasons.
CREATE VIEW v_club_summary AS
SELECT
    club,
    COUNT(*)                                  AS seasons,
    ROUND(AVG(wage_index), 2)                 AS avg_wage_index,
    ROUND(AVG(position), 1)                   AS avg_position,
    ROUND(AVG(points), 1)                     AS avg_points,
    MIN(wage_rank)                            AS best_wage_rank,
    MAX(wage_rank)                            AS worst_wage_rank
FROM v_wage_index
GROUP BY club;
