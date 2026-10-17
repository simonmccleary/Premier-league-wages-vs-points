# Cleaning log

Every decision that changed the data, in the order it was made. An employer will ask why a number was dropped or changed, and this is the answer.

## Match results

| Issue | Decision | Reason |
|---|---|---|
| Seasons have different columns (extra betting columns in some) | Keep only date, teams, goals and result | Only those are needed, and they exist in every season |
| Dates arrive as dd/mm/yy and dd/mm/yyyy | Parse with day first and mixed formats | Reading them as month first would scramble dates |
| Club names differ between sources ("Man City", "Nott'm Forest") | One lookup table maps each name to the standard name | A single place to fix names and a clear record of changes |
| Football-data results do not include points deductions | Add Everton -8 and Nottingham Forest -4 for 2023/24 | Matches the official final tables (Everton 40 points, Forest 32) |
| Is the table right? | Assert 380 matches and 20 clubs per season and all ten champions and points | The script stops if anything is off |

## Companies and filings

| Issue | Decision | Reason |
|---|---|---|
| Name searches return fan clubs and foundations | Person chose the right company for each club | Search ranking is not reliable for this |
| Newcastle United Football Club Ltd (the obvious match) is dormant | Use Newcastle United Football Company Ltd | The dormant company has no staff costs |
| Tottenham has a company and a group | Use the club company (Tottenham Hotspur Football & Athletic Co. Ltd) | The group includes the stadium and would distort the comparison |
| Aston Villa Football Club Ltd shows only 8m to 21m of staff costs | Add it to Aston Villa FC Ltd, which employs the players | Players and other staff are in different companies. Aston Villa Ltd has no employees |
| Crystal Palace not found by name | Use CPFC Limited, which employs the players and managers | Verified by the staff note in its accounts |
| Luton's original company was dissolved | Use Luton Town Football Club 2020 Ltd | The only active company with filings in the window |

## Staff costs

| Issue | Decision | Reason |
|---|---|---|
| Most filings are scanned images | OCR to find the page, a person reads the figures | OCR can swap digits, so it is not trusted for numbers |
| Possible misreads | Wages, social security and pension costs must add to the printed total | Caught two misreads and prompted two extra checks, each resolved on a zoomed crop |
| Some clubs file company and group accounts | One basis per club, chosen in club_companies.csv and noted in the data | Mixing bases within a club would create fake jumps. Everton uses company, Liverpool and Leicester use group |
| Basis changes within a club (Liverpool 2017 company, 2018 onward group; Leicester 2019 company, 2021 onward group) | Kept as reported and flagged | The earlier filing does not restate on the new basis |
| Periods of 11, 13 or 14 months | Scale to 12 months (total x 12 / months), with months worked out from the gap between accounts dates | Year-end changes and the 2020 extension. Robustness check shows the result barely moves |
| Exceptional items inside staff costs (termination, redundancy, promotion bonuses) | Keep as reported; Manchester United's exceptional termination costs of 32m (2025) and 3.6m (2024) are excluded because the accounts show them separately | Show the recurring cost where the accounts separate it, and flag where they do not |
| Figures in whole pounds for some clubs | Convert to thousands of pounds | Same unit for every club |
| A season appears twice (current column and next year's comparative) | Keep the current column and record any difference | Six clubs re-read independently matched to the pound |
| Seasons a club was not in the Premier League | Dropped from the analysis | Out of scope |

## Not done

- Staff costs have not been split into player wages and other staff. The accounts do not give a consistent split.
- No adjustment for transfer fees or amortisation.
