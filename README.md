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

| Date | Source | Page updated | Members listed | Heading count |
|---|---|---|---|---|
| 2024-05-30 | Wayback Machine | 2024-05-20 | 75 | 75 |
| 2024-08-15 | Wayback Machine | 2024-08-06 | 78 | 80 |
| 2024-08-16 | Wayback Machine | 2024-08-06 | 78 | 80 |
| 2024-09-26 | Wayback Machine | 2024-09-19 | 80 | 82 |
| 2024-11-08 | Wayback Machine | 2024-10-24 | 82 | 84 |
| 2024-11-27 | Wayback Machine | 2024-11-15 | 83 | 85 |
| 2024-12-14 | Wayback Machine | 2024-12-05 | 84 | 85 |
| 2024-12-27 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-01-08 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-01-10 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-01-16 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-01-22 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-02-02 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-02-04 | Wayback Machine | 2024-12-17 | 84 | 86 |
| 2025-02-11 | Wayback Machine | 2025-02-07 | 85 | 87 |
| 2025-03-08 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-03-19 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-05-20 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-07-24 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-09-12 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-12-06 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2025-12-24 | Wayback Machine | 2025-03-03 | 85 | 86 |
| 2026-04-16 | Wayback Machine | 2026-01-13 | 86 | 86 |
| 2026-05-08 | Wayback Machine | 2026-04-24 | 87 | 86 |
| 2026-10-04 | Live | 2026-09-21 | 93 | 93 |

The heading count and the listed names don't always match: from August 2024 to March 2025 the heading was 1–2 higher than the names listed, and in May 2026 it was 1 lower. Both numbers are kept; the member lists contain only names that appeared on the page.

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
