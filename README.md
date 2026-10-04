# FLOW Observatory

Tracks the member list of the U.S. DOT **Freight Logistics Optimization Works (FLOW)** program over time.

Source page: <https://www.transportation.gov/freight-infrastructure-and-policy/flow-members>

A GitHub Actions job runs in the cloud once a day, reads the page, and commits new data **only when the member list changes**. The git history of `data/` is the full record of every change.

## Data

| File | What it holds |
|---|---|
| `data/members.csv` | The current member list (`member`, `as_of`) |
| `data/snapshots/YYYY-MM-DD.csv` | The full list on each snapshot date |
| `data/snapshots/index.csv` | One row per snapshot: date, source (`live` or `wayback`), source URL, the page's own "Last updated" date, stated and parsed counts |
| `data/changelog.csv` | Rebuilt from all snapshots, oldest first (`detected_on`, `page_last_updated`, `source`, `change`, `member`) |
| `data/archive/` | Raw copies of imported Wayback Machine pages, named by capture timestamp |
| `data/meta.json` | Latest check: page "Last updated" date, counts, last change date |

**Reading the changelog:** `baseline` marks members present in the earliest snapshot (they joined on or before that date). `added` and `removed` mean the change happened **between the previous snapshot and that date**, and `page_last_updated` narrows it further. Gaps between archived snapshots make some dates approximate.

### Snapshots so far

| Date | Source | Members |
|---|---|---|
| 2024-05-30 | Wayback Machine (page updated 2024-05-20) | 75 |
| 2026-10-04 | Live (page updated 2026-09-21) | 93 |

## Adding archived pages

Save a Wayback Machine snapshot of the page ("Webpage, HTML only"), then:

```bash
python scraper/import_archive.py saved-page.html [more.html ...]
```

The capture date is read from the file itself.

## How it works

- `scraper/scrape.py` finds the "FLOW has N members" heading (or the older "FLOW currently has N Members"), reads the list beneath it, and compares it with `data/members.csv`.
- `.github/workflows/scrape.yml` runs it daily at 13:17 UTC and on demand (**Actions → Check FLOW member list → Run workflow**).
- If the page layout changes and the list can't be found, the run fails (and GitHub emails you) rather than recording bad data.

## Run locally

```bash
pip install -r requirements.txt
python scraper/scrape.py
python tests/test_parse.py
```
