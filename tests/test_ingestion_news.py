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
    - Normalises bare symbol "BHP" → "BHP.AU" (≤5 chars, no dot)
    - Truncates content_snippet to 500 chars

  _parse_sentiment():
    - Tested implicitly via parse_news_response; also directly below.

  _normalise_symbol():
    - Tested implicitly via parse_news_response.
"""
from __future__ import annotations

from datetime import date

import pytest

from asxos.ingestion.news import (
    NewsItem,
    _normalise_symbol,
    _parse_sentiment,
    parse_news_response,
)

_AS_OF = date(2026, 5, 23)
_HOLDINGS = {"BHP.AU", "CBA.AU", "WBC.AU"}


def _item(
    *,
    url: str = "https://example.com/news/1",
    title: str = "BHP Q1 results",
    date_str: str = "2026-05-23T04:30:00+00:00",
    symbols: list = None,
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
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result == []


def test_parse_includes_matching_symbols() -> None:
    """Items with at least one matching symbol are returned."""
    items = [_item(symbols=["BHP.AU", "RIO.AU"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert len(result) == 1
    assert result[0].symbols == ["BHP.AU"]  # only the matched symbol


def test_parse_normalises_date_string() -> None:
    """ISO datetime string with timezone → bare date via [:10] slice."""
    items = [_item(date_str="2026-05-23T04:30:00+00:00")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].published_at == date(2026, 5, 23)


def test_parse_filters_by_staleness() -> None:
    """Items older than 2 days from as_of are dropped."""
    # 3 days before as_of → stale
    stale_date = "2026-05-20T00:00:00+00:00"
    items = [_item(date_str=stale_date)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result == []


def test_parse_includes_items_within_staleness_window() -> None:
    """Items ≥ (as_of - 2 days) are included."""
    # Exactly 2 days before — at the cutoff (cutoff = as_of - 2 = 2026-05-21)
    ok_date = "2026-05-21T00:00:00+00:00"
    items = [_item(date_str=ok_date)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert len(result) == 1


def test_parse_deduplicates_by_url() -> None:
    """Same URL appearing twice in the batch → only one NewsItem returned."""
    dup_items = [
        _item(url="https://example.com/dup", symbols=["BHP.AU"]),
        _item(url="https://example.com/dup", symbols=["CBA.AU"]),
    ]
    result = parse_news_response(dup_items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert len(result) == 1
    assert result[0].url == "https://example.com/dup"


def test_parse_empty_input() -> None:
    """Empty raw list → empty result, no errors."""
    result = parse_news_response([], holdings=_HOLDINGS, as_of=_AS_OF)
    assert result == []


# ---------------------------------------------------------------------------
# parse_news_response — sentiment parsing
# ---------------------------------------------------------------------------


def test_parse_sentiment_dict() -> None:
    """Sentiment as dict {"polarity": "Positive"} → "positive"."""
    items = [_item(sentiment={"polarity": "Positive"})]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].sentiment == "positive"


def test_parse_sentiment_string() -> None:
    """Sentiment as plain string "Negative" → "negative"."""
    items = [_item(sentiment="Negative")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].sentiment == "negative"


def test_parse_sentiment_absent() -> None:
    """Absent sentiment field → empty string."""
    items = [_item()]  # no sentiment key in _item() when None
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].sentiment == ""


def test_parse_sentiment_none_value() -> None:
    """Explicit None sentiment value → empty string."""
    raw = _item()
    raw["sentiment"] = None
    result = parse_news_response([raw], holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].sentiment == ""


# ---------------------------------------------------------------------------
# parse_news_response — symbol normalisation
# ---------------------------------------------------------------------------


def test_parse_normalises_symbol_suffix() -> None:
    """Bare 3-char symbol "BHP" (no dot, ≤5 chars) → "BHP.AU"."""
    items = [_item(symbols=["BHP"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert len(result) == 1
    assert "BHP.AU" in result[0].symbols


def test_parse_does_not_normalise_already_suffixed() -> None:
    """Symbol already carrying a dot (e.g. "BHP.AX") is left unchanged."""
    items = [_item(symbols=["BHP.AX"])]
    # BHP.AX is not in _HOLDINGS (which uses .AU), so no match → filtered out
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result == []


def test_parse_does_not_normalise_long_bare_symbol() -> None:
    """Symbol with >5 chars but no dot is left unchanged (not normalised)."""
    # "BHPBIL" (6 chars) → stays "BHPBIL", not in holdings → filtered out
    items = [_item(symbols=["BHPBILLITON"])]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result == []


# ---------------------------------------------------------------------------
# parse_news_response — content snippet
# ---------------------------------------------------------------------------


def test_parse_content_snippet_truncated() -> None:
    """Content exceeding 500 chars is capped at 500."""
    long_content = "A" * 600
    items = [_item(content=long_content)]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert len(result[0].content_snippet) == 500


def test_parse_content_snippet_short_preserved() -> None:
    """Short content is preserved as-is."""
    items = [_item(content="Short.")]
    result = parse_news_response(items, holdings=_HOLDINGS, as_of=_AS_OF)
    assert result[0].content_snippet == "Short."


def test_parse_content_snippet_absent() -> None:
    """Missing content field → empty string snippet."""
    raw = _item()
    del raw["content"]
    result = parse_news_response([raw], holdings=_HOLDINGS, as_of=_AS_OF)
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
# _normalise_symbol — direct unit tests
# ---------------------------------------------------------------------------


def test_normalise_adds_au_suffix() -> None:
    assert _normalise_symbol("BHP") == "BHP.AU"
    assert _normalise_symbol("CBA") == "CBA.AU"
    assert _normalise_symbol("WBC") == "WBC.AU"


def test_normalise_leaves_suffixed_symbol_unchanged() -> None:
    assert _normalise_symbol("BHP.AU") == "BHP.AU"
    assert _normalise_symbol("BHP.AX") == "BHP.AX"


def test_normalise_leaves_long_symbol_unchanged() -> None:
    # >5 chars without dot — not normalised (would be an unusual ticker anyway)
    assert _normalise_symbol("BHPBILLITON") == "BHPBILLITON"
