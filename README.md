# FLOW Observatory

Tracks the member list of the U.S. DOT **Freight Logistics Optimization Works (FLOW)** program over time.

Source page: <https://www.transportation.gov/freight-infrastructure-and-policy/flow-members>

A GitHub Actions job runs in the cloud once a day, reads the page, and commits new data **only when the member list changes**. The git history of `data/` is the full record of every change.

## Data

| File | What it holds |
|---|---|
| `data/members.csv` | The current member list (`member`, `as_of`) |
| `data/snapshots/YYYY-MM-DD.csv` | The full list as of each date a change was detected |
| `data/changelog.csv` | One row per member added or removed (`detected_on`, `page_last_updated`, `change`, `member`) |
| `data/meta.json` | Source URL, the page's own "Last updated" date, member counts, last change date |

The first snapshot (2026-10-04) records the 93 members listed on the page as last updated 2026-09-21, so every member appears as `added` on that date.

## How it works

- `scraper/scrape.py` finds the "FLOW has N members" heading, reads the list beneath it, and compares it with `data/members.csv`.
- `.github/workflows/scrape.yml` runs it daily at 13:17 UTC and on demand (**Actions → Check FLOW member list → Run workflow**).
- If the page layout changes and the list can't be found, the run fails (and GitHub emails you) rather than recording bad data.

## Run locally

```bash
pip install -r requirements.txt
python scraper/scrape.py
python tests/test_parse.py
```
