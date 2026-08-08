"""
News ingestion from EODHD /news (M14a).

Parse + upsert pattern mirrors asxos/ingestion/regulatory.py.

Pure functions: parse_news_response(), parse_news_response_with_stats(),
                build_symbol_alias(), _parse_sentiment(), _extract_polarity().
Async I/O:      upsert_news().

EODHD /news response shape (per item):
  {
    "date":     "2026-05-23T04:30:00+00:00",   # ISO datetime string — always slice [:10]
    "title":    "BHP Q1 Results ...",
    "link":     "https://...",
    "symbols":  ["HUBS", "BHP.AU"],            # vendor form: bare, .AU, .US, ...
                                               # also tolerated: a JSON-encoded
                                               # string '["HUBS"]' (decoded on read)
    "sentiment": {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}  # numeric dict
    "content":  "Full article text ...",
  }

Gotchas:
  1. date is ISO datetime string → always slice [:10] before fromisoformat()
  2. sentiment shape varies by plan tier — use _parse_sentiment() and _extract_polarity() always
  3. symbols arrive in vendor form (bare "HUBS", or "HUBS.US") and must be resolved
     to the HELD project symbol via build_symbol_alias() — never guessed at. The old
     ".AU" guess is ONE of two candidate causes of the month-long empty holding_news
     table; the other is the request side (the job asked EODHD for "HUBS.NYSE", a
     namespace it does not serve). Both are fixed here; neither is proven — see
     build_symbol_alias() for why the evidence cannot separate them.
  4. content may be absent — use content_snippet = (content or "")[:500]
  5. sentiment_polarity: None means absent (structurally neutral — not zero-sentiment)
     Hard-fail (rule #10) if abs(polarity) > 1.5
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, NamedTuple

import asyncpg

# Stdlib-only module — safe here. jobs/ingest_news.py imports this module
# eagerly and depends on it staying free of httpx/tenacity.
from asxos.ingestion.symbols import eodhd_symbol, symbol_root

_POLARITY_LIMIT = Decimal("1.5")


@dataclass(frozen=True)
class NewsItem:
    url: str
    title: str
    published_at: date
    symbols: list[str]       # HELD project symbols (HUBS.NYSE), never vendor form
    sentiment: str           # "positive" | "negative" | "neutral" | ""
    content_snippet: str
    sentiment_polarity: Decimal | None = field(default=None)  # numeric ∈ [-1.5, +1.5]; None if absent


def _parse_sentiment(raw_item: dict[str, Any]) -> str:
    """Extract text sentiment label from EODHD sentiment field.

    EODHD /news on current plan tiers returns a dict with numeric fields:
      {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}
    Older or lower plan tiers return a string label in the dict: {"polarity": "Positive"}
    or a plain string, or the field may be absent entirely.
    """
    s = raw_item.get("sentiment")
    if isinstance(s, dict):
        pol = s.get("polarity")
        if pol is None:
            return ""
        # Try numeric interpretation first (current plan tier shape).
        try:
            v = float(pol)
            if v > 0.05:
                return "positive"
            if v < -0.05:
                return "negative"
            return "neutral"
        except (TypeError, ValueError):
            # Fallback: string label in dict (older plan tier shape).
            return str(pol).lower()
    return (s or "").lower() if isinstance(s, str) else ""


def _extract_polarity(raw_item: dict[str, Any]) -> Decimal | None:
    """Extract numeric polarity from EODHD sentiment dict.

    EODHD returns: {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}
    Returns None (not 0.0) when polarity is absent or non-numeric (e.g. "Positive").
    Absence is structurally neutral — not zero-sentiment.
    Hard-fails only if the value IS numeric but outside [-1.5, +1.5] (rule #10).
    """
    s = raw_item.get("sentiment")
    if not isinstance(s, dict):
        return None
    v = s.get("polarity")
    if v is None:
        return None
    try:
        pol = Decimal(str(float(v)))
    except (TypeError, ValueError, ArithmeticError):
        # Non-numeric polarity label (e.g. "Positive") — no numeric signal available.
        return None
    if abs(pol) > _POLARITY_LIMIT:
        raise ValueError(
            f"polarity={pol} outside [-1.5, +1.5] — hard-fail per rule #10"
        )
    return pol


def build_symbol_alias(holdings: set[str], requested_symbol: str) -> dict[str, list[str]]:
    """Map every form the vendor might tag an article with -> the HELD symbol(s).

    Replaces the old ``_normalise_symbol``, which appended ``.AU`` to any dotless
    ticker of five characters or fewer. That was a *guess about the vendor's
    namespace*: EODHD tags HubSpot articles ``HUBS``, the guess produced
    ``HUBS.AU``, and the held symbol is ``HUBS.NYSE`` — so neither form EODHD
    actually emits for that listing (``HUBS``, ``HUBS.US``) could match, and any
    such article was discarded with no error raised.

    Whether that is what emptied ``holding_news`` for a month is **not
    established, and cannot be from the logs**. The request side was broken too
    (``jobs/ingest_news.py`` asked EODHD for ``HUBS.NYSE``, which it does not
    address), so articles may never have arrived to be filtered. Both faults
    produce the identical artefact — status='success', zero rows, no exception —
    which is why this pair is fixed together rather than ranked. One live probe
    is what would settle it (docs/market-trends-report-2026-08-05.md §1, §11 #4).

    Three key forms per holding, all resolving to the held project symbol so
    downstream consumers that re-intersect against ``current_holdings``
    (``asxos/brief/compose.py``, ``jobs/ingest_sentiment.py``) still match:

      - the held symbol itself            ``HUBS.NYSE``
      - its vendor form                   ``HUBS.US``
      - the bare root of the REQUESTED symbol only   ``HUBS``

    The bare root is deliberately scoped to ``requested_symbol`` rather than to
    every holding. The fetch is per-symbol, so a bare tag in that response is
    unambiguous — but a global bare-root index is not: ASX three-letter codes
    collide with US tickers, so an article tagged ``SUN`` would be attributed to
    an ASX holding regardless of which security it was about, and flow on into
    ``signal_sentiment``. That is the same silent-wrong class being fixed here.
    A ``requested_symbol`` outside ``holdings`` RAISES rather than quietly
    contributing no bare root: skipping would restore the exact pre-fix
    behaviour, and silence is the whole character of the bug this ends.

    Values are lists so overlapping holdings (both ``HUBS.US`` and ``HUBS.NYSE``)
    fan out losslessly rather than needing a hard-fail on a data-entry quirk.
    """
    if requested_symbol not in holdings:
        # Silent-skip here would restore the exact pre-fix behaviour — no bare-root
        # alias, so every bare vendor tag drops and the table stays empty with no
        # error. That is the failure mode this function exists to end, so it fails
        # loudly instead (rule #10). Production cannot hit this: the job draws both
        # `holdings` and `symbol` from the same current_holdings query.
        raise ValueError(
            f"requested_symbol {requested_symbol!r} is not in holdings "
            f"({sorted(holdings)!r}) — refusing to build an alias index that would "
            "silently drop every bare vendor tag."
        )

    alias: dict[str, list[str]] = {}

    def _add(key: str, held: str) -> None:
        if not key:
            return
        bucket = alias.setdefault(key.upper(), [])
        if held not in bucket:
            bucket.append(held)

    for held in holdings:
        if "." in held:
            _add(held, held)
            _add(eodhd_symbol(held), held)
        elif held == requested_symbol:
            # Suffix-less AND the symbol we asked for: its bare form is scoped
            # by construction, so registering it is safe.
            _add(held, held)
        # A suffix-less holding we did NOT request is deliberately skipped. Its
        # only key would be a bare root, which is precisely the global bare-root
        # index the requested_symbol scoping exists to prevent — a holding stored
        # as "SUN" would otherwise capture any article tagged SUN, whichever
        # security the request was actually for. Nothing enforces that
        # current_holdings.symbol carries a suffix, so this cannot be assumed.

    _add(symbol_root(requested_symbol), requested_symbol)

    return alias


class ParseStats(NamedTuple):
    """Why articles were dropped — surfaced per symbol in the job log.

    A zero-row run is indistinguishable from a quiet news day at the job level,
    so the counts are the only cheap way to tell "the vendor sent nothing" from
    "the vendor sent plenty and we discarded all of it". ``unmatched_tags``
    carries the actual vendor strings (uppercased, de-duplicated, first 10),
    which is what diagnoses a namespace mismatch in one cron cycle instead of a
    month of archaeology.

    Sink: ``jobs/ingest_news.py::_fetch_and_upsert`` logs these at WARNING when
    ``dropped_no_match`` is non-zero. They are **not** persisted — the
    ``job_runs.error_message`` note ``main()`` leaves on a green zero-row run is
    an aggregate ("0 rows written across N symbol(s)") and carries no tags.

    Every drop path must have a counter
    -----------------------------------
    ``dropped_malformed`` and ``dropped_duplicate`` close the two paths that
    previously discarded items while incrementing nothing. That mattered because
    the counts are the *only* diagnostic here: an item that vanishes without a
    counter is arithmetically indistinguishable from one that never arrived.

    Measured on this file before the counters existed: a batch of one malformed
    item reported ``fetched=1`` with every drop counter at zero, and a mixed
    batch of one good plus one malformed reported ``fetched=2, items=1`` with
    every drop counter at zero — two fetched, one written, one gone, nothing
    recording why. Staleness and no-match were already counted, so malformed was
    the sole unexplained loss, which is the exact shape of the 2026-08 incident
    (``docs/market-trends-report-2026-08-05.md`` §1).

    With both counters the identity below holds for every batch, so a reader can
    verify the arithmetic instead of trusting it::

        fetched == len(items) + dropped_stale + dropped_no_match
                   + dropped_malformed + dropped_duplicate
    """

    fetched: int
    dropped_stale: int
    dropped_no_match: int
    unmatched_tags: tuple[str, ...]
    dropped_malformed: int = 0
    dropped_duplicate: int = 0


def parse_news_response(
    raw: list[dict[str, Any]],
    *,
    holdings: set[str],
    as_of: date,
    requested_symbol: str,
) -> list[NewsItem]:
    """Parse EODHD /news response into NewsItem records.

    Thin wrapper over :func:`parse_news_response_with_stats`; see that function
    for the filtering contract.
    """
    items, _stats = parse_news_response_with_stats(
        raw, holdings=holdings, as_of=as_of, requested_symbol=requested_symbol
    )
    return items


def parse_news_response_with_stats(
    raw: list[dict[str, Any]],
    *,
    holdings: set[str],
    as_of: date,
    requested_symbol: str,
) -> tuple[list[NewsItem], ParseStats]:
    """Parse EODHD /news response, and report why anything was dropped.

    Filters to items:
      - published within the last 2 days of as_of (belt-and-suspenders;
        paid tiers honour the ``from`` param but we validate locally)
      - whose symbols resolve, through :func:`build_symbol_alias`, to a symbol
        actually held

    ``NewsItem.symbols`` carries the **held project symbol** (``HUBS.NYSE``),
    never the vendor form (``HUBS.US``). Two downstream readers depend on that,
    in different ways: ``asxos/brief/compose.py::_holding_news`` re-intersects
    the stored array against ``current_holdings`` with exact string equality, so
    a vendor form would populate the table and still render an empty brief
    section; ``jobs/ingest_sentiment.py`` unnests it straight into
    ``signal_sentiment.symbol`` with no intersection at all, so a vendor form
    would create permanently unjoinable sentiment rows (no FK there to catch it).

    Deduplicates by URL within the batch.
    Returns results in input order (caller can sort if needed).
    """
    # Whole-payload shape guard. `news_for_symbol` no longer coerces a non-list
    # HTTP-200 body to []; that coercion is precisely why a real EODHD error
    # envelope — a JSON *object* like {"code": 402, ...} — could never reach the
    # malformed counter. Classify it here, where it is a pure function and every
    # shape is testable without an HTTP mock.
    #
    # Counted as one malformed unit rather than fetched=0, so the reconciliation
    # identity still holds (1 == 0 kept + 1 malformed) and the run is visibly
    # degraded instead of arithmetically identical to a quiet day.
    if not isinstance(raw, list):
        return [], ParseStats(
            fetched=1,
            dropped_stale=0,
            dropped_no_match=0,
            unmatched_tags=(),
            dropped_malformed=1,
            dropped_duplicate=0,
        )

    alias = build_symbol_alias(holdings, requested_symbol)
    cutoff = as_of - timedelta(days=2)
    dropped_stale = 0
    dropped_no_match = 0
    dropped_malformed = 0
    dropped_duplicate = 0
    unmatched: list[str] = []
    seen_urls: set[str] = set()
    out: list[NewsItem] = []

    for item in raw:
        # A non-dict element cannot carry url/title and would raise on .get().
        # Count it as malformed rather than crashing the whole batch: one bad
        # element must not discard the good items alongside it.
        if not isinstance(item, dict):
            dropped_malformed += 1
            continue

        url = (item.get("link") or item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        if not url or not title:
            # Structurally unusable. Previously `continue` with no counter, so a
            # vendor error envelope (`[{"code": 402, ...}]`) was indistinguishable
            # from a quiet day.
            dropped_malformed += 1
            continue

        # Deduplicate within the batch.
        if url in seen_urls:
            dropped_duplicate += 1
            continue
        seen_urls.add(url)

        # Parse published date — EODHD returns ISO datetime strings.
        raw_date = item.get("date") or item.get("published_at") or ""
        try:
            pub_date = date.fromisoformat(str(raw_date)[:10])
        except (ValueError, TypeError):
            pub_date = as_of  # fall back to today rather than drop the item

        # Staleness filter: drop items older than 2 days from as_of.
        if pub_date < cutoff:
            dropped_stale += 1
            continue

        # Resolve vendor symbol tags to held symbols.
        raw_symbols = item.get("symbols") or []
        if isinstance(raw_symbols, str):
            try:
                raw_symbols = json.loads(raw_symbols)
            except (json.JSONDecodeError, ValueError):
                raw_symbols = [raw_symbols] if raw_symbols else []

        # json.loads("123") returns an int, and a vendor can put any scalar in
        # this field directly. Iterating a non-list raised TypeError here and —
        # because the job's except block catches broadly — destroyed the whole
        # batch, discarding every good sibling item. That contradicts the same
        # invariant the isinstance(item, dict) guard above enforces: one bad
        # element must not take down the batch. A junk symbols field is the
        # vendor's schema not being what we parse — malformed, counted, moved on.
        if not isinstance(raw_symbols, list | tuple):
            dropped_malformed += 1
            continue

        tags = [s for s in raw_symbols if isinstance(s, str) and s]
        matched = sorted({held for t in tags for held in alias.get(t.upper(), [])})
        if not matched:
            dropped_no_match += 1
            for t in tags:
                # Cap and scrub before this reaches a log sink. Vendor tags are
                # externally controlled and unbounded; `.upper()` preserves \n,
                # \r and escape sequences, so an embedded newline forges a whole
                # extra log line under the job's "%(asctime)s %(levelname)s
                # %(message)s" format (CWE-117). The repo already caps every
                # other untrusted feed string — regulatory titles at 500,
                # content_snippet at 500 — and this was the one that escaped.
                clean = "".join(c for c in t.upper() if c.isprintable())[:32]
                if clean and clean not in unmatched:
                    unmatched.append(clean)
            continue  # item is not relevant to any current holding

        # Content snippet — capped at 500 chars.
        content = item.get("content") or item.get("summary") or ""
        content_snippet = str(content)[:500]

        out.append(
            NewsItem(
                url=url,
                title=title,
                published_at=pub_date,
                symbols=matched,
                sentiment=_parse_sentiment(item),
                content_snippet=content_snippet,
                sentiment_polarity=_extract_polarity(item),
            )
        )

    stats = ParseStats(
        fetched=len(raw),
        dropped_stale=dropped_stale,
        dropped_no_match=dropped_no_match,
        unmatched_tags=tuple(unmatched[:10]),
        dropped_malformed=dropped_malformed,
        dropped_duplicate=dropped_duplicate,
    )
    return out, stats


async def upsert_news(conn: asyncpg.Connection, items: list[NewsItem]) -> int:
    """UPSERT holding_news rows.  On URL conflict, merges the symbols arrays.

    Returns the number of rows processed (inserted or updated).
    Uses executemany for batch efficiency (mirrors ingest_regulatory pattern).

    The symbols merge SQL is a PostgreSQL JSONB set-union:
      jsonb_agg(DISTINCT sym ORDER BY sym) over the union of old + new symbols.
    """
    if not items:
        return 0

    payload = [
        (
            item.url,
            item.title,
            item.published_at,
            json.dumps(item.symbols),   # passed as JSON string, cast to JSONB via $4::jsonb
            item.sentiment,
            item.content_snippet,
            str(item.sentiment_polarity) if item.sentiment_polarity is not None else None,
        )
        for item in items
    ]

    await conn.executemany(
        """
        INSERT INTO holding_news
            (url, title, published_at, symbols, sentiment, content_snippet, sentiment_polarity)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7::numeric)
        ON CONFLICT (url) DO UPDATE SET
            symbols = (
                SELECT jsonb_agg(DISTINCT sym ORDER BY sym)
                FROM (
                    SELECT jsonb_array_elements_text(holding_news.symbols) AS sym
                    UNION
                    SELECT jsonb_array_elements_text(EXCLUDED.symbols)
                ) merged
            ),
            sentiment          = EXCLUDED.sentiment,
            sentiment_polarity = COALESCE(holding_news.sentiment_polarity, EXCLUDED.sentiment_polarity),
            ingested_at        = NOW()
        """,
        payload,
    )
    return len(payload)
