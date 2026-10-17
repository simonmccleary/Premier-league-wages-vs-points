# Build log

Raw material for the walkthrough Simon asked for after the build. One entry per step: what was done, which tool, why.

## 2026-10-11, step 1: match results into a database
- Tool: Python (requests) in `src/01_fetch_results.py`. Why Python: repeatable. Ten files fetched by one loop, one request a second, and anyone can re-run it.
- Source: football-data.co.uk, one CSV per season (E0 = Premier League), 2015/16 to 2024/25. Why this source: free, stable file format, no scraping needed, no login.
- Tool: pandas in `src/02_build_db.py`. Why pandas: it cleans and reshapes tables in a few lines. Cleaning done: kept six columns (seasons differ in extra betting columns), parsed dates that came in two formats, standardised club names (one map, one place), cast goals to integers.
- League tables built from match results (3 points a win, 1 a draw; order by points, then goal difference, then goals scored).
- Points deductions added by hand: Everton 2023/24 (-8), Nottingham Forest 2023/24 (-4). The results files do not include them.
- Validation: asserts 380 matches and 20 clubs per season, and that all ten champions and their points match the official tables. Everton (40) and Forest (32) also match official finals.
- Tool: SQLite, file `data/football.db`. Why SQLite: a full SQL database in one file, no server to install, and it is what the SQL queries will run against.
- Result: 3,800 matches, 200 club-seasons, 34 distinct clubs.

## 2026-10-11, step 2: Companies House test on Manchester City (company 00040946)
- Tool: Companies House REST API (free key in `.env`), Python requests. Why an API and not scraping the website: it is the official, documented route, with a stated rate limit, and returns structured filing lists.
- Finding 1: the API lists 44 account filings back to 1997. Latest is for year ended 30 June 2025, filed 6 March 2026, so 2024/25 accounts exist for at least this club.
- Finding 2: the filed accounts are PDFs made of scanned images. No text layer, so pdfplumber extracts nothing. Automatic text parsing does not work for this club. OCR or reading the page images is needed.
- Finding 3: read by eye from the page images (PDF pages 15 and 29). Year ended 30 June 2025: revenue £694,094k; employee costs £408,403k (wages and salaries £355,384k, social security £51,110k, pensions £1,378k, share-based £531k). 2024: employee costs £412,573k.
- Check used: the four components sum to the total (355,384 + 51,110 + 1,378 + 531 = 408,403).
- Caveat for the README: employee costs cover 670 staff, 252 football staff including players and 418 commercial/admin. So this is club staff costs, not player wages.
- Decision pending: how to scale to ~34 clubs.

## 2026-10-13, step 3: find each club's legal entity
- `src/03_find_companies.py` searches Companies House for all 34 clubs and prints the top four matches each. Why a review step: searches return women's teams, foundations and fan clubs alongside the club. A person picks the right company number.
- Clear matches for most clubs. Uncertain, needing a check of which company holds the football accounts: Newcastle (three candidates), Tottenham (three), Middlesbrough (three), Swansea (two), Cardiff (club vs holdings), Luton (the old company dissolved; a 2020 company replaced it). Crystal Palace not found by name; needs another search.
- SofaScore: declined again on 2026-10-13. Its terms bar scripts and scrapers.
- `src/04_list_filings.py` lists every account filing from 2015 onward for each candidate and records whether a machine-readable (xhtml) version exists. Output `data/processed/filings.csv`.

- Result of `04_list_filings.py` (after adding retries and per-company caching, because the first run crashed on one dropped connection and lost everything): 484 account filings across 41 companies, 2015 onward. Only 45 (9%) have a machine-readable xhtml version. 439 are PDF only, and the ones I opened (Man City) are scans. Most readable ones sit with a few clubs (Newcastle United Football Club Ltd, Swansea City Football Club Ltd, Ipswich, Watford, Hull, Forest, Sunderland, Burnley).
- Lesson for the README: do the cheap inventory first. It told us the plan before any reading was done.
- Year-ends differ: 31 May (Arsenal, Liverpool, West Ham, Stoke, Cardiff), 30 June (most), 31 July (Sunderland, Bournemouth in 2015, Burnley 2025). Each needs a mapping to a season.
- Some clubs file group accounts (107 of 484 filings are group type), so the same club can have a group and a company figure. We must choose one basis per club and say so.

## 2026-10-13, step 4: Tesseract and the page finder
- Installed Tesseract OCR (free, open source) with Simon's OK. `src/ocr_tools.py` OCRs each page of a scanned PDF and scores it on four phrases (wages and salaries, social security, staff/employee costs, average number). On Man City 2025 it found the right page (29 of 39) in 32 seconds.
- Why OCR finds the page but a person reads the figures: OCR can swap digits (6 and 8, 3 and 8). The sum check caught two misreads (Wolves 2021 wages, Leeds 2021 pensions) and prompted two more zoomed checks (Swansea 2018, Everton) where the original reading was right.
- `src/05_download_and_locate.py` plans the fewest filings that cover each club's Premier League seasons (every filing has two years), downloads them, and saves the staff costs page as an image. 114 filings in the plan.
- `src/04_list_filings.py` first crashed on one dropped connection and lost its results. Fixed with retries and per-company caching. Lesson: write results as you go.

## 2026-10-13, step 5: reading the figures
- Every figure was read from a page image and recorded in `data/staff_costs.csv` with the PDF, page number, wages and salaries, and a sum check (components add to the printed total).
- 200 of 200 club-seasons covered.
- Entity problems found and fixed: Aston Villa Football Club Limited holds only about £8m to £21m of staff costs because players are employed by Aston Villa FC Limited. The two are added together. Aston Villa Limited has no employees.
- Comparability limits (all in the CSV `note` column): some clubs report company accounts and some group accounts (Leicester, Liverpool from 2018, Leeds, Brentford, Huddersfield); periods of 11, 13 or 14 months are annualised (total x 12 / months, months worked out from the gap between accounts dates); some figures include exceptional or termination items (noted, kept as reported); Everton uses company basis, Liverpool and Leicester group basis.
- `src/06_load_staff_costs.py` loads the CSV into SQLite as table staff_costs. `sql/01_views.sql` defines views (JOIN, window functions, aggregation).

## Still to do
- Wage bills from Companies House accounts (needs API key in `.env`)
