# Rebuilding the dashboard in Power BI

Job adverts for data analysts name Power BI far more often than they name hand-written HTML, so this version is worth an evening. It uses the same data as the web dashboard.

I could not run Power BI in the environment this guide was written in. The steps follow Power BI Desktop's standard layout and the button names may differ slightly in your version. If something does not match, tell me what you see on screen and I will adjust the step.

## What you need

Power BI Desktop (free from the Microsoft Store, Windows only). Your laptop is Windows, so that works.

## Step 1. Load the data

Why: Power BI reads a table, and this CSV is the final analysis table from the pipeline.

1. Open Power BI Desktop and close the welcome screen.
2. On the Home ribbon, click Get data, then Text/CSV.
3. Browse to `03_Data-Projects/football-wages/data/processed/club_season_analysis.csv` and click Open.
4. In the preview window click Transform Data (not Load). This opens Power Query.
5. Check the column types in the header row: season and club should be Text; points, position, wage_index and resid should be numbers. If a column shows ABC but should be a number, click the icon on the left of the column name and choose Decimal Number.
6. Click Close & Apply on the Home ribbon.

Power Query is where analysts clean data in a job. Everything you click there is recorded as a step on the right, which is the same idea as the cleaning log.

## Step 2. A scatter chart

Why: it is the headline chart in the project.

1. On the Report page (the chart icon on the left), click an empty area of the canvas.
2. In the Visualizations pane, click the Scatter chart icon (dots on axes).
3. From the Data pane drag `wage_index` to X Axis and `points` to Y Axis.
4. Drag `club` to Values.
5. Drag `season` to Tooltips.
6. Click the X Axis dropdown in the Visualizations pane and tick nothing, then in the Format pane (paint roller icon) open X axis, then Scale type, and choose Log.
7. In the Format pane open Markers and set the size to about 8.

## Step 3. Filters people can click

1. Click empty canvas, then the Slicer icon in the Visualizations pane.
2. Drag `season` into Field. In the Format pane, under Slicer settings, set the style to Between so it becomes a range.
3. Add a second slicer with `club`. Under Slicer settings, tick Multi-select with Ctrl.

## Step 4. R squared as a card

Why: the web dashboard recomputes R squared for the selected seasons. In Power BI this needs a DAX measure, which is the formula language analysts use inside Power BI.

1. In the Data pane, right-click the table name and choose New measure.
2. Paste this and press Enter:

```
R Squared =
VAR t =
    SUMMARIZE (
        club_season_analysis,
        club_season_analysis[season],
        club_season_analysis[club],
        "x", LN ( MAX ( club_season_analysis[wage_index] ) ),
        "y", MAX ( club_season_analysis[points] )
    )
VAR n   = COUNTROWS ( t )
VAR sx  = SUMX ( t, [x] )
VAR sy  = SUMX ( t, [y] )
VAR sxy = SUMX ( t, [x] * [y] )
VAR sxx = SUMX ( t, [x] ^ 2 )
VAR syy = SUMX ( t, [y] ^ 2 )
VAR num = n * sxy - sx * sy
VAR den = ( n * sxx - sx ^ 2 ) * ( n * syy - sy ^ 2 )
RETURN
    DIVIDE ( num ^ 2, den )
```

3. Click empty canvas, choose the Card visual, drag `R Squared` into Fields.
4. In the Format pane, set the display unit to None and the format to Percentage with 0 decimals.
5. With the card selected, change the slicers and watch the number move. For all ten seasons it should read 61%. If it does not, check that the X Axis uses `wage_index` and that no filters are applied.

## Step 5. Over and under performance by club

1. Add a Clustered bar chart. Drag `club` to Y axis and `resid` to X axis.
2. Click the dropdown next to `resid` in the field well and choose Average.
3. In the Filters pane, drag `club` into Filters on this visual, choose Advanced filtering, and leave it. (A minimum-seasons filter is easier in the web version.)
4. In the Format pane open Bars, then Colors, then the fx button, and set a rule: below 0 red, 0 and above blue.
5. Sort by clicking the three dots at the top right of the visual, then Sort axis, then resid, then Sort descending.

## Step 6. Publishing

Power BI Desktop files (`.pbix`) cannot be opened from GitHub. Two options:

- Save the `.pbix` in the repository and add screenshots to the README.
- Publish to the Power BI service (Home, Publish) and use File, Embed report, Publish to web (public). Anything published to the web is visible to anyone with the link, so only do it with this public data.

## Add to the CV

"Built a Power BI dashboard on Premier League wage and results data, including a DAX measure for R-squared that recalculates for any selected seasons."

Only write this once you have built it and can explain the measure.
