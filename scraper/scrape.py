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

HEADING_RE = re.compile(r"FLOW\s+(?:currently\s+)?has\s+(\d+)\s+members", re.I)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
        "FLOW-Observatory (+https://github.com)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


READER_URL = "https://r.jina.ai/" + URL  # fallback: public reader service, returns Markdown


def fetch(url: str = URL) -> str:
    """Fetch the page directly; if DOT refuses the request, fall back to a reader service."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"::warning::Direct fetch failed ({e}); trying reader fallback.")
    resp = requests.get(READER_URL, headers={"Accept": "text/plain"}, timeout=90)
    resp.raise_for_status()
    return resp.text


def _finish(members: list[str], stated_count, page_updated) -> dict:
    if len(members) < 10:
        raise RuntimeError(f"Only {len(members)} members parsed; refusing to record a suspicious result.")
    return {"members": members, "stated_count": stated_count, "page_updated": page_updated}


def _page_updated(text: str):
    m = re.search(r"Last updated:\s*([A-Za-z]+,\s*[A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
    if not m:
        return None
    try:
        return dt.datetime.strptime(" ".join(m.group(1).split()), "%A, %B %d, %Y").date().isoformat()
    except ValueError:
        return m.group(1)


def parse_markdown(text: str) -> dict:
    """Parse the reader-service Markdown: the heading line, then '- Member' bullet lines."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        h = HEADING_RE.search(line)
        if h:
            members = []
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if not s and not members:
                    continue
                b = re.match(r"^[-*+]\s+(.*)$", s)
                if not b:
                    break
                name = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b.group(1))  # strip links
                name = " ".join(name.replace("**", "").split())
                if name:
                    members.append(name)
            return _finish(members, int(h.group(1)), _page_updated(text))
    raise RuntimeError("Could not find the 'FLOW has N members' heading; page layout may have changed.")


def parse(html: str) -> dict:
    """Return {'members': [...], 'stated_count': int|None, 'page_updated': str|None}."""
    if "<html" not in html[:2000].lower() and "<body" not in html.lower():
        return parse_markdown(html)
    soup = BeautifulSoup(html, "html.parser")

    # The list sits right after a heading like "FLOW has 93 members:".
    heading = None
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        if HEADING_RE.search(tag.get_text(" ", strip=True)):
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

    return _finish(members, stated_count, _page_updated(soup.get_text(" ")))


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


INDEX_CSV = SNAPSHOTS / "index.csv"
INDEX_FIELDS = ["date", "source", "source_url", "page_last_updated", "stated_count", "parsed_count"]


def read_index() -> list[dict]:
    if not INDEX_CSV.exists():
        return []
    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def record_snapshot(date: str, members: list[str], source: str, source_url: str,
                    page_updated, stated_count) -> None:
    """Write snapshots/<date>.csv and upsert its row in snapshots/index.csv."""
    write_list(SNAPSHOTS / f"{date}.csv", members, date)
    rows = [r for r in read_index() if r["date"] != date]
    rows.append({
        "date": date, "source": source, "source_url": source_url,
        "page_last_updated": page_updated or "",
        "stated_count": "" if stated_count is None else stated_count,
        "parsed_count": len(members),
    })
    rows.sort(key=lambda r: r["date"])
    with INDEX_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        w.writeheader()
        w.writerows(rows)


def rebuild() -> None:
    """Rebuild changelog.csv and members.csv from every snapshot, oldest first.

    The earliest snapshot's members are recorded as 'baseline' (we only know
    they were members by then, not when they joined).
    """
    index = read_index()
    out, prev = [], None
    for r in index:
        with (SNAPSHOTS / f"{r['date']}.csv").open(newline="", encoding="utf-8") as f:
            cur = [row["member"] for row in csv.DictReader(f)]
        base = [r["date"], r["page_last_updated"], r["source"]]
        if prev is None:
            out += [base + ["baseline", n] for n in sorted(cur, key=str.lower)]
        else:
            out += [base + ["added", n] for n in sorted(set(cur) - set(prev), key=str.lower)]
            out += [base + ["removed", n] for n in sorted(set(prev) - set(cur), key=str.lower)]
        prev = cur
    with CHANGELOG_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["detected_on", "page_last_updated", "source", "change", "member"])
        w.writerows(out)
    if index:
        write_list(MEMBERS_CSV, prev, index[-1]["date"])


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
        record_snapshot(today, members, "live", URL, result["page_updated"], result["stated_count"])
        rebuild()

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
    try:
        sys.exit(main())
    except Exception as e:  # surface the reason as a GitHub annotation
        print(f"::error title=FLOW scrape failed::{type(e).__name__}: {e}")
        raise
