"""Import saved Wayback Machine copies of the FLOW members page.

Usage:
    python scraper/import_archive.py path/to/saved1.html [saved2.html ...]

For each file it reads the capture timestamp embedded in the page's
web.archive.org links, parses the member list, keeps a copy of the raw page
under data/archive/, records a dated snapshot, and rebuilds the changelog.
"""

from __future__ import annotations

import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from scrape import DATA, parse, rebuild, record_snapshot

ARCHIVE = DATA / "archive"
WB_RE = re.compile(r"web\.archive\.org/web/(\d{14})")


def capture_info(html: str) -> tuple[str, str]:
    """Return (14-digit timestamp, wayback URL of the page itself)."""
    stamps = Counter(WB_RE.findall(html))
    if not stamps:
        raise RuntimeError("No web.archive.org timestamp found; is this a saved Wayback page?")
    ts = stamps.most_common(1)[0][0]
    m = re.search(rf"web\.archive\.org/web/{ts}[a-z_]*/(https?://[^\"'\s]*flow-members)", html)
    original = m.group(1) if m else "https://www.transportation.gov/freight-infrastructure-and-policy/flow-members"
    return ts, f"https://web.archive.org/web/{ts}/{original}"


def import_file(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    ts, wb_url = capture_info(html)
    date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    result = parse(html)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, ARCHIVE / f"{ts}.html")
    record_snapshot(date, result["members"], "wayback", wb_url,
                    result["page_updated"], result["stated_count"])
    note = ""
    if result["stated_count"] is not None and result["stated_count"] != len(result["members"]):
        note = f" (page says {result['stated_count']})"
    print(f"{path.name}: captured {date}, page updated {result['page_updated']}, "
          f"{len(result['members'])} members{note}")
    return date


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    for p in argv:
        import_file(Path(p))
    rebuild()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
