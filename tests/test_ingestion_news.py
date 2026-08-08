"""
Tests for asxos/ingestion/news.py — pure functions (no I/O, no async).

Coverage:
  parse_news_response():
    - Filters items whose symbols don't intersect current holdings
    - Normalises ISO datetime strings to bare dates ([:10] slice)
    - Drops items older than 2 days from as_of (staleness filter)
    - Deduplicates items by URL within the batch
    - Parses sentiment when shape is a dict {"polarity": "Positive"}
    - Parses sentiment when shape is a plain string "Negative"
    - Returns "" for sentiment when field is absent or None
    - Resolves a bare vendor tag ("BHP", "HUBS") to the HELD symbol via the alias
    - Truncates content_snippet to 500 chars

  build_symbol_alias():
    - Every vendor form of a holding resolves to the HELD project symbol
    - Bare roots are scoped to the requested symbol only (the collision control)
    - Overlapping holdings fan out to a list rather than hard-failing

  parse_news_response_with_stats():
    - ParseStats reports the vendor tags that matched nothing (the diagnostic
      that distinguishes a namespace mismatch from a quiet news day)

  _parse_sentiment() / _extract_polarity():
    - Tested implicitly via parse_news_response; also directly below.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.ingestion.news import (
    _extract_polarity,
    _parse_sentiment,
    build_symbol_alias,
    parse_news_response,
    parse_news_response_with_stats,
)

_AS_OF = date(2026, 5, 23)
_HOLDINGS = {"BHP.AU", "CBA.AU", "WBC.AU"}


def _item(
    *,
    url: str = "https://example.com/news/1",
    title: str = "BHP Q1 results",
    date_str: str = "2026-05-23T04:30:00+00:00",
    symbols: list | None = None,
    sentiment=None,
    content: str = "Short content.",
) -> dict:
    d: dict = {
        "link": url,
        "title": title,
        "date": date_str,
        "symbols": symbols if symbols is not None else ["BHP.AU"],
        "content": content,
    }
    if sentiment is not None:
        d["sentiment"] = sentiment
    return d


# ---------------------------------------------------------------------------
# parse_news_response — filtering
# ---------------------------------------------------------------------------


def test_parse_filters_non_matching_symbols() -> None:
    """Items whose symbols don't intersect current holdings are dropped."""
    items = [_item(symbols=["RIO.AU"])]  # RIO not in holdings
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result == []


def test_parse_includes_matching_symbols() -> None:
    """Items with at least one matching symbol are returned."""
    items = [_item(symbols=["BHP.AU", "RIO.AU"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert len(result) == 1
    assert result[0].symbols == ["BHP.AU"]  # only the matched symbol


def test_parse_normalises_date_string() -> None:
    """ISO datetime string with timezone → bare date via [:10] slice."""
    items = [_item(date_str="2026-05-23T04:30:00+00:00")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].published_at == date(2026, 5, 23)


def test_parse_filters_by_staleness() -> None:
    """Items older than 2 days from as_of are dropped."""
    # 3 days before as_of → stale
    stale_date = "2026-05-20T00:00:00+00:00"
    items = [_item(date_str=stale_date)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result == []


def test_parse_includes_items_within_staleness_window() -> None:
    """Items ≥ (as_of - 2 days) are included."""
    # Exactly 2 days before — at the cutoff (cutoff = as_of - 2 = 2026-05-21)
    ok_date = "2026-05-21T00:00:00+00:00"
    items = [_item(date_str=ok_date)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert len(result) == 1


def test_parse_deduplicates_by_url() -> None:
    """Same URL appearing twice in the batch → only one NewsItem returned."""
    dup_items = [
        _item(url="https://example.com/dup", symbols=["BHP.AU"]),
        _item(url="https://example.com/dup", symbols=["CBA.AU"]),
    ]
    result = parse_news_response(dup_items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert len(result) == 1
    assert result[0].url == "https://example.com/dup"


def test_parse_empty_input() -> None:
    """Empty raw list → empty result, no errors."""
    result = parse_news_response([], holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result == []


# ---------------------------------------------------------------------------
# parse_news_response — sentiment parsing
# ---------------------------------------------------------------------------


def test_parse_sentiment_dict() -> None:
    """Sentiment as dict {"polarity": "Positive"} → "positive"."""
    items = [_item(sentiment={"polarity": "Positive"})]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment == "positive"


def test_parse_sentiment_string() -> None:
    """Sentiment as plain string "Negative" → "negative"."""
    items = [_item(sentiment="Negative")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment == "negative"


def test_parse_sentiment_absent() -> None:
    """Absent sentiment field → empty string."""
    items = [_item()]  # no sentiment key in _item() when None
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment == ""


def test_parse_sentiment_none_value() -> None:
    """Explicit None sentiment value → empty string."""
    raw = _item()
    raw["sentiment"] = None
    result = parse_news_response([raw], holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment == ""


# ---------------------------------------------------------------------------
# parse_news_response — symbol normalisation
# ---------------------------------------------------------------------------


def test_parse_normalises_symbol_suffix() -> None:
    """Bare 3-char symbol "BHP" (no dot, ≤5 chars) → "BHP.AU"."""
    items = [_item(symbols=["BHP"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert len(result) == 1
    assert "BHP.AU" in result[0].symbols


def test_parse_does_not_normalise_already_suffixed() -> None:
    """Symbol already carrying a dot (e.g. "BHP.AX") is left unchanged."""
    items = [_item(symbols=["BHP.AX"])]
    # BHP.AX is not in _HOLDINGS (which uses .AU), so no match → filtered out
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result == []


def test_parse_does_not_normalise_long_bare_symbol() -> None:
    """Symbol with >5 chars but no dot is left unchanged (not normalised)."""
    # "BHPBIL" (6 chars) → stays "BHPBIL", not in holdings → filtered out
    items = [_item(symbols=["BHPBILLITON"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result == []


# ---------------------------------------------------------------------------
# parse_news_response — content snippet
# ---------------------------------------------------------------------------


def test_parse_content_snippet_truncated() -> None:
    """Content exceeding 500 chars is capped at 500."""
    long_content = "A" * 600
    items = [_item(content=long_content)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert len(result[0].content_snippet) == 500


def test_parse_content_snippet_short_preserved() -> None:
    """Short content is preserved as-is."""
    items = [_item(content="Short.")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].content_snippet == "Short."


def test_parse_content_snippet_absent() -> None:
    """Missing content field → empty string snippet."""
    raw = _item()
    del raw["content"]
    result = parse_news_response([raw], holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].content_snippet == ""


# ---------------------------------------------------------------------------
# _parse_sentiment — direct unit tests
# ---------------------------------------------------------------------------


def test_parse_sentiment_unit_dict_polarity() -> None:
    assert _parse_sentiment({"sentiment": {"polarity": "Positive"}}) == "positive"


def test_parse_sentiment_unit_dict_missing_polarity() -> None:
    assert _parse_sentiment({"sentiment": {}}) == ""


def test_parse_sentiment_unit_plain_string() -> None:
    assert _parse_sentiment({"sentiment": "neutral"}) == "neutral"


def test_parse_sentiment_unit_absent() -> None:
    assert _parse_sentiment({}) == ""


# ---------------------------------------------------------------------------
# build_symbol_alias — replaces the old _normalise_symbol .AU guess
#
# The guess appended .AU to any dotless ticker <=5 chars, which silently dropped
# every article for a non-ASX holding: EODHD tags HubSpot news "HUBS", the guess
# produced "HUBS.AU", and the held symbol is "HUBS.NYSE".
# docs/market-trends-report-2026-08-05.md section 1.
# ---------------------------------------------------------------------------


def test_alias_resolves_all_vendor_forms_to_the_held_symbol() -> None:
    alias = build_symbol_alias({"HUBS.NYSE"}, "HUBS.NYSE")
    for tag in ("HUBS", "HUBS.US", "HUBS.NYSE"):
        assert alias[tag] == ["HUBS.NYSE"], f"{tag} must resolve to the HELD symbol"


def test_alias_preserves_asx_behaviour() -> None:
    alias = build_symbol_alias({"BHP.AU"}, "BHP.AU")
    assert alias["BHP"] == ["BHP.AU"]
    assert alias["BHP.AU"] == ["BHP.AU"]


def test_alias_scopes_bare_root_to_the_requested_symbol_only() -> None:
    """The negative control, and the reason this is not a simple root match.

    ASX three-letter codes collide with US tickers. A global bare-root index
    would attribute an article tagged "SUN" to a held SUN.AU regardless of which
    security the request was actually about, and that misattribution would flow
    into signal_sentiment unchecked (no FK there to catch it).
    """
    alias = build_symbol_alias({"SUN.AU", "HUBS.NYSE"}, "HUBS.NYSE")
    assert alias.get("HUBS") == ["HUBS.NYSE"]   # requested -> bare root allowed
    assert "SUN" not in alias                    # not requested -> no bare root
    assert alias["SUN.AU"] == ["SUN.AU"]         # full form still resolves


def test_alias_fans_out_on_overlapping_holdings() -> None:
    alias = build_symbol_alias({"HUBS.NYSE", "HUBS.US"}, "HUBS.NYSE")
    assert sorted(alias["HUBS.US"]) == ["HUBS.NYSE", "HUBS.US"]


def test_parse_keeps_us_article_tagged_with_bare_ticker() -> None:
    """End-to-end regression: this returned [] before the fix."""
    items = [{
        "link": "https://example.com/hubs",
        "title": "HubSpot reports Q2",
        "date": f"{_AS_OF.isoformat()}T05:00:00+00:00",
        "symbols": ["HUBS"],
    }]
    result = parse_news_response(
        items, holdings={"HUBS.NYSE"}, as_of=_AS_OF, requested_symbol="HUBS.NYSE"
    )
    assert len(result) == 1
    assert result[0].symbols == ["HUBS.NYSE"], "must store the HELD form"


def test_parse_stats_report_unmatched_tags() -> None:
    """A zero-row day and a namespace mismatch are only distinguishable by tags."""
    items = [{
        "link": "https://example.com/x",
        "title": "Unrelated",
        "date": f"{_AS_OF.isoformat()}T05:00:00+00:00",
        "symbols": ["TSLA.US"],
    }]
    result, stats = parse_news_response_with_stats(
        items, holdings={"HUBS.NYSE"}, as_of=_AS_OF, requested_symbol="HUBS.NYSE"
    )
    assert result == []
    assert stats.fetched == 1
    assert stats.dropped_no_match == 1
    assert stats.unmatched_tags == ("TSLA.US",)


# ---------------------------------------------------------------------------
# _extract_polarity — direct unit tests (REV-K: numeric polarity from /news)
# ---------------------------------------------------------------------------


def test_extract_polarity_from_numeric_dict() -> None:
    """EODHD numeric dict → Decimal polarity value."""
    item = {"sentiment": {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}}
    result = _extract_polarity(item)
    assert result == Decimal("-0.953")
    assert isinstance(result, Decimal)


def test_extract_polarity_positive() -> None:
    """Positive polarity stored correctly."""
    item = {"sentiment": {"polarity": 0.5}}
    result = _extract_polarity(item)
    assert result == Decimal("0.5")


def test_extract_polarity_absent_returns_none() -> None:
    """No 'sentiment' key → None (structurally neutral, not zero)."""
    assert _extract_polarity({}) is None


def test_extract_polarity_plain_string_sentiment_returns_none() -> None:
    """Top-level plain string sentiment (e.g. 'Positive') → None (not a dict)."""
    item = {"sentiment": "Positive"}
    assert _extract_polarity(item) is None


def test_extract_polarity_string_label_in_dict_returns_none() -> None:
    """String label inside dict (older plan tier: {'polarity': 'Positive'}) → None (non-numeric)."""
    item = {"sentiment": {"polarity": "Positive"}}
    assert _extract_polarity(item) is None


def test_extract_polarity_dict_no_polarity_key_returns_none() -> None:
    """Dict without 'polarity' key → None."""
    item = {"sentiment": {"neg": 0.1, "neu": 0.9}}
    assert _extract_polarity(item) is None


def test_extract_polarity_out_of_range_raises() -> None:
    """abs(polarity) > 1.5 → ValueError (hard-fail per rule #10)."""
    item = {"sentiment": {"polarity": 2.0}}
    with pytest.raises(ValueError, match=r"outside \[-1\.5, \+1\.5\]"):
        _extract_polarity(item)


def test_extract_polarity_negative_out_of_range_raises() -> None:
    """Negative extreme also hard-fails."""
    item = {"sentiment": {"polarity": -1.51}}
    with pytest.raises(ValueError):
        _extract_polarity(item)


def test_extract_polarity_at_limit_passes() -> None:
    """Exactly ±1.5 is permitted (boundary inclusive)."""
    assert _extract_polarity({"sentiment": {"polarity": 1.5}}) == Decimal("1.5")
    assert _extract_polarity({"sentiment": {"polarity": -1.5}}) == Decimal("-1.5")


# ---------------------------------------------------------------------------
# parse_news_response — sentiment_polarity field (REV-K)
# ---------------------------------------------------------------------------


def test_parse_news_populates_polarity_when_present() -> None:
    """Numeric polarity dict → NewsItem.sentiment_polarity populated."""
    items = [_item(sentiment={"polarity": -0.5, "neg": 0.3, "neu": 0.6, "pos": 0.1})]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment_polarity == Decimal("-0.5")


def test_parse_news_polarity_none_when_string_sentiment() -> None:
    """String sentiment ('Positive') → sentiment_polarity is None."""
    items = [_item(sentiment="Positive")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment_polarity is None


def test_parse_news_polarity_none_when_absent() -> None:
    """No sentiment field → sentiment_polarity is None."""
    items = [_item()]  # _item() omits 'sentiment' when None
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")
    assert result[0].sentiment_polarity is None


def test_parse_news_sentiment_label_derived_from_polarity() -> None:
    """When sentiment is a numeric dict, text 'sentiment' field is derived from sign."""
    pos_item = [_item(sentiment={"polarity": 0.8})]
    neg_item = [_item(sentiment={"polarity": -0.3}, url="https://example.com/2")]
    neutral_item = [_item(sentiment={"polarity": 0.02}, url="https://example.com/3")]

    assert parse_news_response(pos_item, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")[0].sentiment == "positive"
    assert parse_news_response(neg_item, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")[0].sentiment == "negative"
    assert parse_news_response(neutral_item, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU")[0].sentiment == "neutral"


def test_alias_raises_when_requested_symbol_is_not_held() -> None:
    """A disposed or unknown requested symbol must fail loudly, not quietly.

    Silently skipping the bare-root alias would reproduce the pre-fix behaviour
    exactly — every bare vendor tag dropped, zero rows, no error — which is the
    failure mode this whole change exists to end (rule #10). Mutation-verified:
    with the guard removed entirely, every other test in this file still passed.
    """
    with pytest.raises(ValueError, match="not in holdings"):
        build_symbol_alias({"BHP.AU"}, "XYZ.AU")


def test_alias_skips_bare_root_for_a_suffixless_holding_not_requested() -> None:
    """A suffix-less HOLDING must not re-open a global bare-root index.

    Nothing enforces that current_holdings.symbol carries an exchange suffix, so
    a holding stored as plain "SUN" would otherwise register the key "SUN"
    globally — precisely the collision the requested_symbol scoping prevents —
    and capture any article tagged SUN whichever security was requested.
    """
    alias = build_symbol_alias({"SUN", "HUBS.NYSE"}, "HUBS.NYSE")
    assert "SUN" not in alias, "a suffix-less non-requested holding must not be a key"
    assert alias["HUBS"] == ["HUBS.NYSE"]


def test_alias_does_not_fan_a_root_across_two_different_securities() -> None:
    """One holding's root equalling another's full symbol must not double-attribute.

    build_symbol_alias({"SUN", "SUN.AU"}, "SUN.AU") previously produced
    alias["SUN"] == ["SUN", "SUN.AU"], so a single article was stored against two
    securities and unnested into two signal_sentiment rows.
    """
    alias = build_symbol_alias({"SUN", "SUN.AU"}, "SUN.AU")
    assert alias["SUN"] == ["SUN.AU"], "the root must resolve to exactly one security"


def test_parse_drops_bare_tag_for_a_holding_that_was_not_requested() -> None:
    """Parse-level twin of the alias negative control.

    The alias-level test asserts on the dict, so it cannot see a global bare-root
    fallback added inside the parse loop that bypasses the alias entirely. This
    closes that hole: "SUN" must not attach to a held SUN.AU when the request was
    for a different security.
    """
    items = [{
        "link": "https://example.com/sun",
        "title": "Something about SUN",
        "date": f"{_AS_OF.isoformat()}T05:00:00+00:00",
        "symbols": ["SUN"],
    }]
    # A suffix-LESS non-requested holding, deliberately: mutation testing showed
    # that with two suffixed holdings this passed even when the suffix branch was
    # deleted, so it was not the twin its docstring claimed to be.
    result = parse_news_response(
        items,
        holdings={"SUN", "HUBS.NYSE"},
        as_of=_AS_OF,
        requested_symbol="HUBS.NYSE",
    )
    assert result == []


def test_unmatched_tags_are_scrubbed_and_truncated() -> None:
    """Vendor tags reaching a log sink must be bounded and free of control chars.

    stats.unmatched_tags is written into a log line under the job's
    "%(asctime)s %(levelname)s %(message)s" format, so an embedded newline forges
    a complete additional log entry (CWE-117), and nothing bounds a vendor
    string's length. Every other untrusted feed string in this repo is already
    capped (regulatory titles at 500, content_snippet at 500); this was the one
    that escaped.

    Mutation-verified gap: before this test, removing the scrub entirely left all
    57 tests green. The only other test touching this path asserts on "TSLA.US",
    which is printable and 7 chars — a fixed point of the scrub, identical with or
    without it.
    """
    hostile = "EVIL\n2026-01-01 CRITICAL forged log line\r\x1b[31m" + "A" * 200
    items = [{
        "link": "https://example.com/x",
        "title": "Unrelated",
        "date": f"{_AS_OF.isoformat()}T05:00:00+00:00",
        "symbols": [hostile],
    }]
    _result, stats = parse_news_response_with_stats(
        items, holdings={"HUBS.NYSE"}, as_of=_AS_OF, requested_symbol="HUBS.NYSE"
    )

    assert len(stats.unmatched_tags) == 1
    tag = stats.unmatched_tags[0]
    assert "\n" not in tag and "\r" not in tag, "a newline would forge a log line"
    assert "\x1b" not in tag, "escape sequences must not reach the log"
    assert len(tag) <= 32, f"unbounded vendor string reached the log sink: {len(tag)}"


# ---------------------------------------------------------------------------
# M0: every drop path must have a counter
#
# `dropped_stale` and `dropped_no_match` already existed. Two paths discarded
# items while incrementing nothing: structurally malformed items (no url/title)
# and intra-batch URL duplicates. Measured on the pre-fix parser, a lone
# malformed item reported fetched=1 with every drop counter at zero, and a
# mixed good+malformed batch reported fetched=2/items=1 with every drop counter
# at zero — two in, one out, one gone, nothing recording why.
#
# The counts are the ONLY diagnostic this parser emits, so an uncounted loss is
# arithmetically indistinguishable from an item that never arrived. That is the
# 2026-08 false-green shape (market-trends-report-2026-08-05.md §1).
# ---------------------------------------------------------------------------


def _reconciles(items, stats) -> bool:
    """fetched must equal what was kept plus every counted drop."""
    return stats.fetched == (
        len(items)
        + stats.dropped_stale
        + stats.dropped_no_match
        + stats.dropped_malformed
        + stats.dropped_duplicate
    )


def test_malformed_only_batch_is_counted_not_silent() -> None:
    """A vendor error envelope must not read as a quiet day."""
    items, stats = parse_news_response_with_stats(
        [{"code": 402, "message": "payment required"}],
        holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert items == []
    assert stats.fetched == 1
    assert stats.dropped_malformed == 1, "the sole drop path that used to count nothing"
    assert _reconciles(items, stats)


def test_mixed_good_and_malformed_keeps_good_and_counts_the_loss() -> None:
    """The case that silently lost an item: 2 fetched, 1 written, 1 unexplained."""
    good = _item(url="https://example.com/news/keep", symbols=["BHP.AU"])
    items, stats = parse_news_response_with_stats(
        [good, {"code": 402}],
        holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert len(items) == 1, "a malformed sibling must not discard the good item"
    assert stats.fetched == 2
    assert stats.dropped_malformed == 1
    assert _reconciles(items, stats)


def test_non_dict_element_is_counted_not_raised() -> None:
    """A non-dict element would raise on .get(); one bad element must not
    destroy the whole batch, and must not vanish either."""
    good = _item(url="https://example.com/news/ok", symbols=["BHP.AU"])
    items, stats = parse_news_response_with_stats(
        [good, "not-a-dict", 42, None],
        holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert len(items) == 1
    assert stats.dropped_malformed == 3
    assert _reconciles(items, stats)


def test_duplicate_urls_are_counted() -> None:
    """Dedup was correct but uncounted, so the arithmetic never reconciled."""
    good = _item(url="https://example.com/news/dup", symbols=["BHP.AU"])
    items, stats = parse_news_response_with_stats(
        [good, dict(good)],
        holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert len(items) == 1
    assert stats.fetched == 2
    assert stats.dropped_duplicate == 1
    assert _reconciles(items, stats)


def test_quiet_day_stays_all_zero() -> None:
    """The negative control: a genuinely empty response must not look degraded."""
    items, stats = parse_news_response_with_stats(
        [], holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert items == []
    assert stats.fetched == 0
    assert stats.dropped_malformed == 0
    assert stats.dropped_duplicate == 0
    assert _reconciles(items, stats)


def test_all_five_drop_paths_reconcile_together() -> None:
    """Stale, unmapped, malformed, duplicate and kept, in one batch."""
    keep = _item(url="https://example.com/news/keep", symbols=["BHP.AU"])
    items, stats = parse_news_response_with_stats(
        [
            keep,
            dict(keep),                                                   # duplicate
            _item(url="https://example.com/news/old", date_str="2026-05-01T00:00:00+00:00", symbols=["BHP.AU"]),
            _item(url="https://example.com/news/other", symbols=["TSLA.US"]),
            {"code": 402},                                                # malformed
        ],
        holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert stats.fetched == 5
    assert len(items) == 1
    assert stats.dropped_duplicate == 1
    assert stats.dropped_stale == 1
    assert stats.dropped_no_match == 1
    assert stats.dropped_malformed == 1
    assert _reconciles(items, stats), f"counts must reconcile: {stats}"


def test_non_list_payload_is_malformed_not_a_quiet_day() -> None:
    """A JSON object error envelope is the shape EODHD actually returns.

    `news_for_symbol` no longer coerces it to []. Previously that coercion made
    this shape unreachable: fetched=0 with every counter zero, arithmetically
    identical to a genuinely quiet day. It is now one malformed unit.
    """
    for payload in ({"code": 402, "message": "payment required"}, {}, "nope", 42, None):
        items, stats = parse_news_response_with_stats(
            payload, holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
        )
        assert items == [], f"no items from {payload!r}"
        assert stats.dropped_malformed == 1, f"must be counted: {payload!r}"
        assert stats.fetched == 1
        assert _reconciles(items, stats), f"identity must hold for {payload!r}"


def test_empty_list_is_still_a_quiet_day_not_malformed() -> None:
    """The negative control that keeps the guard honest.

    `[]` is a real, valid, empty response. If the shape guard treated it as
    malformed, every quiet day would page.
    """
    items, stats = parse_news_response_with_stats(
        [], holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
    )
    assert stats.fetched == 0
    assert stats.dropped_malformed == 0
    assert _reconciles(items, stats)


def test_scalar_symbols_field_cannot_destroy_the_batch() -> None:
    """A junk `symbols` field is one malformed item, not a batch-killer.

    json.loads("123") returns an int, and the vendor can put any scalar in the
    field directly. Iterating a non-list raised TypeError here — and because
    the job catches broadly, the whole batch died and every good sibling was
    discarded. That contradicts the invariant the non-dict guard enforces.
    """
    good = _item(url="https://example.com/news/good", symbols=["BHP.AU"])
    for junk in ("123", 5, 1.5, {"a": 1}, True):
        items, stats = parse_news_response_with_stats(
            [good, dict(good, link="https://example.com/news/junk", symbols=junk)],
            holdings=_HOLDINGS, as_of=_AS_OF, requested_symbol="BHP.AU",
        )
        assert len(items) == 1, f"good sibling must survive symbols={junk!r}"
        assert stats.dropped_malformed == 1, f"junk symbols counted: {junk!r}"
        assert _reconciles(items, stats)
