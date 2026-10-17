# Data dictionary

## Database tables (`data/football.db`)

### matches
One row per Premier League match, 3,800 rows.

| Column | Meaning |
|---|---|
| season | Season label, for example 2023/24 |
| date | Match date, YYYY-MM-DD |
| home_team, away_team | Club names, standardised across sources |
| home_goals, away_goals | Full-time goals |
| result | H, D or A (full-time result) |

### league_table
One row per club per season, 200 rows. Calculated from matches.

| Column | Meaning |
|---|---|
| season, club | Keys |
| played, won, drawn, lost | Record |
| gf, ga, gd | Goals for, against and difference |
| points_deduction | Points removed by a sanction (Everton -8 and Nottingham Forest -4 in 2023/24) |
| points | 3 x won + drawn + points_deduction |
| position | 1 to 20, ordered by points, goal difference, goals scored |

### staff_costs
One row per club per season, 200 rows. Read from the filed accounts.

| Column | Meaning |
|---|---|
| club, season | Keys |
| company_number | Companies House number (two numbers joined by + where two companies are added together) |
| period_end | End of the accounting period the figure comes from |
| months | Length of the period in months |
| total_staff_costs_k | Wages and salaries, social security and pension costs, in thousands of pounds, as reported |
| staff_costs_annualised_k | total x 12 / months |
| wages_salaries_k | The wages and salaries line, in thousands of pounds |
| column | current (this year's column of the filing) or comparative (last year's column) |
| source_pdf, source_page | Where to find the figure |
| sum_check | ok if the components add to the printed total; rounding 1k for a 1k difference |
| restatement_k | Difference between the comparative and current-year figures where both exist |
| note | Basis (company or group), exceptional items and other caveats |

## Views (`sql/01_views.sql`)

| View | Purpose |
|---|---|
| v_club_season | Results joined to staff costs |
| v_wage_index | Adds wage_index (cost divided by that season's average), wage_rank and the number of clubs |
| v_season_summary | One row per season: mean cost, share paid by the top six, HHI |
| v_club_summary | One row per club: average wage index, position and points |

## Files

| File | Contents |
|---|---|
| data/club_companies.csv | The company chosen for each club and why |
| data/staff_costs.csv | The hand-read figures with page references |
| data/verification_log.csv | Independent re-reads used to check the dataset |
| data/processed/filings.csv | Every account filing found since 2015 and its available formats |
| data/processed/filing_plan.csv | The filings chosen to cover every season |
| data/processed/club_season_analysis.csv | Final analysis table: wage index, fitted points and residual |
