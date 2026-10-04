"""FLOW Observatory scraper.

Fetches the U.S. DOT FLOW member list and records it to data files
only when the list of members has changed.

Outputs (all under data/):
  members.csv              current member list (always the latest)
  snapshots/YYYY-MM-DD.csv full list as of each detected change
  changelog.csv            one row per added/removed member per change
  meta.json                last check time, page "last updated" date, count
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.transportation.gov/freight-infrastructure-and-policy/flow-members"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
MEMBERS_CSV = DATA / "members.csv"
CHANGELOG_CSV = DATA / "changelog.csv"
META_JSON = DATA / "meta.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
        "FLOW-Observatory (+https://github.com)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str = URL) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.text


def parse(html: str) -> dict:
    """Return {'members': [...], 'stated_count': int|None, 'page_updated': str|None}."""
    soup = BeautifulSoup(html, "html.parser")

    # The list sits right after a heading like "FLOW has 93 members:".
    heading = None
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        if re.search(r"FLOW has\s+\d+\s+members", tag.get_text(" ", strip=True), re.I):
            heading = tag
            break
    if heading is None:
        raise RuntimeError("Could not find the 'FLOW has N members' heading; page layout may have changed.")

    stated = re.search(r"(\d+)", heading.get_text())
    stated_count = int(stated.group(1)) if stated else None

    ul = heading.find_next("ul")
    if ul is None:
        raise RuntimeError("Found the heading but no member list after it.")
    members = [
        " ".join(li.get_text(" ", strip=True).split())
        for li in ul.find_all("li", recursive=False)
    ]
    members = [m for m in members if m]

    page_updated = None
    m = re.search(r"Last updated:\s*([A-Za-z]+,\s*[A-Za-z]+\s+\d{1,2},\s*\d{4})", soup.get_text(" "))
    if m:
        try:
            page_updated = dt.datetime.strptime(m.group(1), "%A, %B %d, %Y").date().isoformat()
        except ValueError:
            page_updated = m.group(1)

    if len(members) < 10:
        raise RuntimeError(f"Only {len(members)} members parsed; refusing to record a suspicious result.")

    return {"members": members, "stated_count": stated_count, "page_updated": page_updated}


def read_current() -> list[str]:
    if not MEMBERS_CSV.exists():
        return []
    with MEMBERS_CSV.open(newline="", encoding="utf-8") as f:
        return [row["member"] for row in csv.DictReader(f)]


def write_list(path: Path, members: list[str], as_of: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["member", "as_of"])
        for name in members:
            w.writerow([name, as_of])


def append_changelog(rows: list[list[str]]) -> None:
    new_file = not CHANGELOG_CSV.exists()
    with CHANGELOG_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["detected_on", "page_last_updated", "change", "member"])
        w.writerows(rows)


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date().isoformat()

    result = parse(fetch())
    members = result["members"]
    previous = read_current()

    if result["stated_count"] is not None and result["stated_count"] != len(members):
        print(f"Note: page says {result['stated_count']} members but {len(members)} were listed.")

    added = sorted(set(members) - set(previous))
    removed = sorted(set(previous) - set(members))
    changed = bool(added or removed) or not MEMBERS_CSV.exists()

    if changed:
        write_list(MEMBERS_CSV, members, today)
        write_list(SNAPSHOTS / f"{today}.csv", members, today)
        page_upd = result["page_updated"] or ""
        append_changelog(
            [[today, page_upd, "added", n] for n in added]
            + [[today, page_upd, "removed", n] for n in removed]
        )

    meta = {
        "source_url": URL,
        "last_checked_utc": now.replace(microsecond=0).isoformat(),
        "page_last_updated": result["page_updated"],
        "stated_count": result["stated_count"],
        "parsed_count": len(members),
    }
    if changed or not META_JSON.exists():
        meta["last_changed_on"] = today
    else:
        meta["last_changed_on"] = json.loads(META_JSON.read_text()).get("last_changed_on")
    META_JSON.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if changed:
        print(f"CHANGED: {len(members)} members (+{len(added)} / -{len(removed)})")
        for n in added:
            print(f"  + {n}")
        for n in removed:
            print(f"  - {n}")
    else:
        print(f"No change: {len(members)} members.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
