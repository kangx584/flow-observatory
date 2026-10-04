from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scraper"))
from scrape import parse

def test_fixture():
    r = parse((Path(__file__).parent / "fixture_2026-09-21.html").read_text())
    assert r["stated_count"] == 93
    assert len(r["members"]) == 93
    assert r["members"][0] == "Ace Hardware" and r["members"][-1] == "ZIM"
    assert r["page_updated"] == "2026-09-21"

if __name__ == "__main__":
    test_fixture(); print("parse test passed")

def test_markdown_fallback():
    r = parse((Path(__file__).parent / "fixture_2026-09-21.md").read_text())
    h = parse((Path(__file__).parent / "fixture_2026-09-21.html").read_text())
    assert r == h

if __name__ == "__main__":
    test_markdown_fallback(); print("markdown fallback test passed")

def test_wayback_2024_format():
    # Older wording: "FLOW currently has 75 Members:"
    p = Path(__file__).resolve().parent.parent / "data" / "archive" / "20240530093705.html"
    r = parse(p.read_text(encoding="utf-8"))
    assert r["stated_count"] == 75 and len(r["members"]) == 75
    assert r["page_updated"] == "2024-05-20"
    assert "Ralph Lauren" in r["members"] and "Union Pacific" in r["members"]

if __name__ == "__main__":
    test_wayback_2024_format(); print("wayback 2024 test passed")
