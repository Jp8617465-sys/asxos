"""
Parser tests for asxos.ingestion.regulatory. No HTTP — fixture bytes only.
"""
from __future__ import annotations

from datetime import date

from asxos.ingestion.regulatory import (
    RegulatoryEvent,
    classify_kind,
    extract_symbols,
    parse_json_announcements,
    parse_rss,
)

_RSS_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>RBA Media Releases</title>
    <item>
      <title>Statement by the Reserve Bank Board: Monetary Policy Decision</title>
      <link>https://www.rba.gov.au/media-releases/2026/mr-26-12.html</link>
      <description>The Board decided to leave the cash rate target unchanged at 4.35%.</description>
      <pubDate>Tue, 06 May 2026 14:30:00 +1000</pubDate>
    </item>
    <item>
      <title>BHP announcement: Q3 trading update</title>
      <link>https://example.com/bhp-q3</link>
      <description>BHP Group results for the quarter ending 31 March 2026.</description>
      <pubDate>Mon, 05 May 2026 09:00:00 +1000</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_extracts_two_items() -> None:
    events = parse_rss(_RSS_FIXTURE, source="RBA")
    assert len(events) == 2
    assert all(isinstance(e, RegulatoryEvent) for e in events)


def test_parse_rss_assigns_dates() -> None:
    events = parse_rss(_RSS_FIXTURE, source="RBA")
    assert events[0].published_at == date(2026, 5, 6)
    assert events[1].published_at == date(2026, 5, 5)


def test_parse_rss_extracts_symbols_from_title_and_body() -> None:
    events = parse_rss(_RSS_FIXTURE, source="RBA")
    # Second item mentions BHP in title
    assert "BHP.AU" in events[1].symbols


def test_parse_rss_classifies_kind() -> None:
    events = parse_rss(_RSS_FIXTURE, source="RBA")
    assert events[0].kind == "monetary_policy"  # "cash rate" keyword
    assert events[1].kind == "disclosure"        # "announcement" keyword


def test_extract_symbols_skips_common_acronyms() -> None:
    text = "RBA and ASX hold meeting; BHP, CBA, and CSL traded actively."
    syms = extract_symbols(text)
    assert "BHP.AU" in syms
    assert "CBA.AU" in syms
    assert "CSL.AU" in syms
    # Common acronyms must not become tickers
    assert "RBA.AU" not in syms
    assert "ASX.AU" not in syms


def test_extract_symbols_deduplicates() -> None:
    syms = extract_symbols("BHP BHP BHP")
    assert syms == ["BHP.AU"]


def test_classify_kind_falls_back_to_default() -> None:
    assert classify_kind("Some unrelated update", "no keywords here", default="other") == "other"


def test_parse_json_announcements_handles_minimal_payload() -> None:
    payload = [
        {
            "symbol": "BHP",
            "headline": "Quarterly Production Report",
            "url": "https://example.com/p1",
            "releasedOn": "2026-04-30T08:00:00Z",
        }
    ]
    events = parse_json_announcements(payload)
    assert len(events) == 1
    assert events[0].symbols == ["BHP.AU"]
    assert events[0].published_at == date(2026, 4, 30)
    assert events[0].source == "ASX"


def test_parse_json_announcements_drops_invalid_rows() -> None:
    payload = [
        {"symbol": "BHP"},  # no title
        {"headline": "X", "url": ""},  # no url
        {"headline": "Trading Update", "url": "https://x", "releasedOn": "2026-05-01"},
    ]
    events = parse_json_announcements(payload)
    assert len(events) == 1


def test_parse_rss_falls_back_to_today_when_date_missing() -> None:
    fixture = b"""<?xml version="1.0"?>
<rss><channel><item>
<title>Generic</title><link>https://x</link><description>body</description>
</item></channel></rss>"""
    events = parse_rss(fixture, source="X")
    # Falls back to today when pubDate missing
    assert events[0].published_at <= date.today()


def test_parse_rss_skips_items_missing_title_or_link() -> None:
    fixture = b"""<?xml version="1.0"?>
<rss><channel>
<item><link>https://x</link></item>
<item><title>OK</title><link>https://y</link></item>
</channel></rss>"""
    events = parse_rss(fixture, source="X")
    assert len(events) == 1
