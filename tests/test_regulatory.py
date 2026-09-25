"""
Parser tests for asxos.ingestion.regulatory. No HTTP — fixture bytes only.
"""
from __future__ import annotations

import logging
from datetime import date

import pytest

from asxos import clock
from asxos.ingestion.regulatory import (
    RegulatoryEvent,
    classify_kind,
    extract_symbols,
    parse_json_announcements,
    parse_rss,
    upsert_events,
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


# RSS 1.0/RDF — faithful to the RBA RSS-CB shape: rdf:RDF root, channel and
# item elements in the RSS 1.0 default namespace, dates in dc:date (ISO 8601),
# no pubDate anywhere.
_RDF_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns="http://purl.org/rss/1.0/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel rdf:about="https://www.rba.gov.au/rss/rss-cb-media-releases.xml">
    <title>RBA - Media Releases</title>
    <link>https://www.rba.gov.au/media-releases/</link>
    <description>Media releases from the Reserve Bank of Australia</description>
    <items>
      <rdf:Seq>
        <rdf:li rdf:resource="https://www.rba.gov.au/media-releases/2026/mr-26-15.html"/>
        <rdf:li rdf:resource="https://www.rba.gov.au/media-releases/2026/mr-26-14.html"/>
      </rdf:Seq>
    </items>
  </channel>
  <item rdf:about="https://www.rba.gov.au/media-releases/2026/mr-26-15.html">
    <title>Statement by the Reserve Bank Board: Monetary Policy Decision</title>
    <link>https://www.rba.gov.au/media-releases/2026/mr-26-15.html</link>
    <description>At its meeting today, the Board decided to lower the cash rate target to 3.60 per cent.</description>
    <dc:date>2026-07-01T09:30:00+10:00</dc:date>
  </item>
  <item rdf:about="https://www.rba.gov.au/media-releases/2026/mr-26-14.html">
    <title>BHP announcement noted in quarterly market operations report</title>
    <link>https://www.rba.gov.au/media-releases/2026/mr-26-14.html</link>
    <description>BHP Group activity noted in the June quarter operations report.</description>
    <dc:date>2026-06-30T14:00:00+10:00</dc:date>
  </item>
</rdf:RDF>
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


def test_parse_rss_rdf_regression_not_empty() -> None:
    # Regression lock: before RSS 1.0/RDF support, parse_rss only looked for
    # un-namespaced .//item or Atom entries, so the RBA RSS-CB feed silently
    # parsed to [] on every production run.
    events = parse_rss(_RDF_FIXTURE, source="RBA")
    assert len(events) > 0


def test_parse_rss_rdf_extracts_items_titles_links_source() -> None:
    events = parse_rss(_RDF_FIXTURE, source="RBA")
    assert len(events) == 2
    assert all(isinstance(e, RegulatoryEvent) for e in events)
    assert events[0].title == "Statement by the Reserve Bank Board: Monetary Policy Decision"
    assert events[0].url == "https://www.rba.gov.au/media-releases/2026/mr-26-15.html"
    assert events[1].title == "BHP announcement noted in quarterly market operations report"
    assert events[1].url == "https://www.rba.gov.au/media-releases/2026/mr-26-14.html"
    assert all(e.source == "RBA" for e in events)


def test_parse_rss_rdf_parses_dc_dates() -> None:
    # dc:date is ISO 8601 with a timezone offset, not RSS 2.0 pubDate
    events = parse_rss(_RDF_FIXTURE, source="RBA")
    assert events[0].published_at == date(2026, 7, 1)
    assert events[1].published_at == date(2026, 6, 30)


def test_parse_rss_rdf_extracts_symbols_and_classifies_kind() -> None:
    events = parse_rss(_RDF_FIXTURE, source="RBA")
    assert events[0].kind == "monetary_policy"  # "cash rate" keyword
    assert events[1].kind == "disclosure"        # "announcement" keyword
    assert "BHP.AU" in events[1].symbols


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
    # Falls back to today when pubDate missing (Sydney day, matching parse_rss)
    assert events[0].published_at <= clock.today()


def test_parse_rss_skips_items_missing_title_or_link() -> None:
    fixture = b"""<?xml version="1.0"?>
<rss><channel>
<item><link>https://x</link></item>
<item><title>OK</title><link>https://y</link></item>
</channel></rss>"""
    events = parse_rss(fixture, source="X")
    assert len(events) == 1


# ---------------------------------------------------------------------------
# upsert_events — first coverage, and the reason it needed some (E-20)
#
# `rows_written` for this job came from `upsert_events`, which returned
# len(rows): events PRESENTED to the statement, not rows written. A feed
# re-serving the same item every night therefore reported rows_written=1 every
# night while `regulatory_events` did not grow — measured 2026-09-15: 7 rows
# total, max(ingested_at) 2026-09-03, and a rows_written=1 success row on every
# night from 09-07 to 09-14.
#
# This function had NO tests before this block, which is why swapping
# executemany for a single RETURNING statement broke nothing visible. The
# dedupe below in particular would have shipped unexercised.
# ---------------------------------------------------------------------------


def _event(url: str, *, source: str = "RBA", title: str = "t") -> RegulatoryEvent:
    return RegulatoryEvent(
        source=source,
        title=title,
        url=url,
        published_at=date(2026, 9, 25),
        summary="s",
        symbols=[],
        kind="monetary_policy",
    )


class _FakeConn:
    """Captures the bound arrays and replays a RETURNING result.

    ``inserted_flags`` is what Postgres' ``(xmax = 0)`` would yield, one per row
    the statement touched, in bound order.
    """

    def __init__(self, inserted_flags: list[bool]) -> None:
        self._flags = inserted_flags
        self.sql: str | None = None
        self.args: tuple[object, ...] = ()
        self.calls = 0

    async def fetch(self, sql: str, *args: object) -> list[dict[str, bool]]:
        self.calls += 1
        self.sql = " ".join(sql.split())
        self.args = args
        return [{"inserted": f} for f in self._flags]


@pytest.mark.asyncio
async def test_upsert_counts_new_rows_separately_from_re_touched() -> None:
    """The E-20 fix: two events, one new and one already stored."""
    conn = _FakeConn([True, False])

    counts = await upsert_events(conn, [_event("u1"), _event("u2")])

    assert counts.inserted == 1
    assert counts.updated == 1
    assert counts.presented == 2


@pytest.mark.asyncio
async def test_a_wholly_re_served_feed_reports_zero_new() -> None:
    """The live shape this row was filed on: nothing new, every night.

    The old return value here was 3; `monitor.rows_written = 3` is what a digest
    read as growth.
    """
    conn = _FakeConn([False, False, False])

    counts = await upsert_events(conn, [_event("u1"), _event("u2"), _event("u3")])

    assert counts.inserted == 0
    assert counts.presented == 3


@pytest.mark.asyncio
async def test_no_events_does_not_touch_the_database() -> None:
    conn = _FakeConn([])

    counts = await upsert_events(conn, [])

    assert (counts.inserted, counts.updated) == (0, 0)
    assert conn.calls == 0


@pytest.mark.asyncio
async def test_a_duplicated_url_within_one_batch_is_deduped_last_wins() -> None:
    """One statement cannot touch the same conflict target twice.

    Postgres raises "ON CONFLICT DO UPDATE command cannot affect row a second
    time", where the previous per-row executemany would quietly apply both. A
    feed listing one release under two entries is a feed bug, not a reason to
    fail the run — so the last occurrence wins.
    """
    conn = _FakeConn([True])

    counts = await upsert_events(
        conn, [_event("dup", title="first"), _event("dup", title="second")]
    )

    urls, titles = conn.args[3], conn.args[2]
    assert list(urls) == ["dup"]
    assert list(titles) == ["second"]
    assert counts.presented == 1


@pytest.mark.asyncio
async def test_same_url_from_a_different_source_is_not_deduped() -> None:
    """The conflict target is (source, url), so the dedupe key must be too."""
    conn = _FakeConn([True, True])

    await upsert_events(conn, [_event("u", source="RBA"), _event("u", source="ASX")])

    assert list(conn.args[0]) == ["RBA", "ASX"]


@pytest.mark.asyncio
async def test_the_statement_asks_postgres_which_rows_were_inserted() -> None:
    """Pins the mechanism, because the counts are meaningless without it: a
    statement that stopped RETURNING (xmax = 0) would still return *a* number.
    """
    conn = _FakeConn([True])

    await upsert_events(conn, [_event("u1")])

    assert conn.sql is not None
    assert "RETURNING (xmax = 0) AS inserted" in conn.sql
    assert "ON CONFLICT (source, url) DO UPDATE" in conn.sql


def test_a_dropped_feed_item_says_so(caplog) -> None:
    """The silent skip is what made E-20's second half unanswerable.

    `parse_rss` drops any item missing a title or a link. Whether the live RBA
    feed has such items cannot be answered from a synthetic fixture, and the
    feed is not reachable from an agent session (egress policy denies
    www.rba.gov.au), so the next production run has to answer it.
    """
    xml = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>Has both</title><link>https://example.com/a</link></item>
  <item><link>https://example.com/b</link></item>
  <item><title>No link</title></item>
</channel></rss>"""

    with caplog.at_level(logging.WARNING, logger="asxos.ingestion.regulatory"):
        events = parse_rss(xml, source="RBA")

    assert len(events) == 1
    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(messages) == 2, messages
    assert "no title" in messages[0]
    assert "no link" in messages[1]
