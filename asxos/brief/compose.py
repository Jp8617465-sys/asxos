"""
Morning-brief composer.

Pulls sections from Postgres and renders them through a Jinja template.
Keep the prose under 200 words — this brief is consumed daily, so density matters.

**Model-independent by construction (mission P1-04, manifest A3/A4/A6).** This
module reads no ``signals`` / ``shap_factors`` / ``prob_up`` / ``expected_return``
/ ``signals.regime``, and never calls ``resolve_production_model()``. The market
regime line, the overnight signal-label table and the ``model_shelved``
suppression flag were all removed with the engine that produced them — the brief
no longer has a state in which a model can influence it, so it no longer needs a
flag describing whether one does. What replaced the regime headline is a
:class:`~asxos.domain.review.status.ReviewStatus` — ``CLEAR`` / ``ATTENTION`` /
``BLOCKED`` / ``EVIDENCE_THIN`` — derived from the user's own authored theses,
holdings and job health (packet P1 required-work item 4). It is never a
trade instruction.

The template is rendered with ``jinja2.StrictUndefined`` (see :func:`render_html`)
so that removing a ``BriefData`` field fails loudly instead of silently
resurrecting whatever the field used to suppress.

Sections. The numbers are stable identifiers, not positions — plan documents and
`.claude/rules/portfolio-conventions.md` cite sections by number — so a retired
section keeps its slot instead of shifting every later number underneath an
external reference. (Pre-existing, unrelated to P1-04: portfolio-conventions.md
calls the portfolio-adjustments gate "section 6" while this list has always
numbered it 7. Left as found; renumbering here would not fix it.)

  1. Job failures banner (if any in the last 24h)
  2. RETIRED (mission P1-04, manifest A4) — market regime, read from
     `signals.regime`. Replaced by the review status in the header, which is
     derived from the user's own data rather than a model's regime call.
  3. Portfolio discipline (portfolio-team-visibility lane, PR2a/PR2b —
     `docs/proposals/portfolio-team-visibility-2026-07-12.md` §8): revisit-
     overdue, stop/target trajectory, conviction-unset, concentration,
     unrealised return (native, broker-matching), and lots approaching the
     12-month CGT-discount threshold
     within 30 days (spec §5.1) — the last folded here from the former
     standalone "Tax actions" table so the fact lives on one gated surface.
     Model-independent by construction (rule #11) — the loader
     never reads `signals`/`shap_factors` and never calls
     `resolve_production_model()`. Gated on ASXOS_PERSONAL_USE=1 only (not
     ASXOS_PORTFOLIO_BRIEF_ENABLED, which is orthogonal — §4). Quiet when
     every check is clean; a check that errors renders a loud "could not run"
     line rather than vanishing (CLAUDE.md #10).
  4. RETIRED (mission P1-04, manifest A6) — signal label changes on current
     holdings, the Model A five-rung ladder plus its top SHAP driver. Removed
     whole rather than emptied: an empty section header still advertises an
     engine that no longer exists.
  5. Regulatory hits on holdings in the last 24h
  6. Market news on holdings (M14a) — gated by ALL of:
       ASXOS_PERSONAL_USE=1 (Part 0 Q1 regulatory firewall)
       ASXOS_NEWS_BRIEF_ENABLED=1 (paper-trade dark gate, plan M14a)
       the LATEST ingest_news job_run in the window being status='success'
         with a NULL error_message (freshness gate — status alone was
         forgeable, a row count was the overcorrection; see _news_ingest_fresh)
     The two env gates omit the section entirely; the freshness gate does
     NOT — it renders an explicit "unverified" state, because silence there
     would read as "no news today". See `_news_section` for the four states.
  7. Portfolio adjustments (M13.7) — gated by BOTH:
       ASXOS_PERSONAL_USE=1 (Part 0 Q1 regulatory firewall)
       ASXOS_PORTFOLIO_BRIEF_ENABLED=1 (paper-trade validation gate, plan I.6)
     Omitted entirely when either flag is unset, or when no successful
     build_portfolio run exists with as_of >= today - 2 (plan I.7 freshness gate).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import jinja2
from dateutil.relativedelta import relativedelta

from asxos.domain.prices.coverage import latest_complete_trading_day
from asxos.domain.prices.fx import is_foreign_symbol
from asxos.domain.review.status import ReviewOutcome, classify
from asxos.domain.tax.cgt import days_to_eligibility
from asxos.domain.theses.discipline import (
    DisciplineFinding,
    DisciplineLevel,
    HoldingWeight,
    PortfolioDisciplineInput,
    ThesisDisciplineInput,
    evaluate_discipline,
    unrealised_return,
)

if TYPE_CHECKING:
    import asyncpg

# Deferred to avoid pulling pydantic_settings into test collection.
# Tests patch asxos.brief.compose.acquire directly; production collect()
# falls through to the lazy import below.
acquire: Any = None


@dataclass(frozen=True)
class RegulatoryHit:
    symbol: str
    source: str
    title: str
    published_at: date
    kind: str


@dataclass(frozen=True)
class NewsItem:
    """One news article relevant to a current holding (M14a).

    ``symbols`` is the subset of the article's tagged symbols that match
    current holdings (normalised to BHP.AU format).
    ``sentiment`` is "positive" | "negative" | "neutral" | "".
    """

    symbols: list[str]
    title: str
    url: str
    published_at: date
    sentiment: str

    @property
    def source(self) -> str:
        """Publisher host derived from ``url`` — e.g. ``reuters.com``.

        Derived, not stored. ``holding_news`` has no publisher column and the
        vendor does not reliably supply one, so persisting a source would mean
        adding a field we cannot populate honestly. The citation host is the
        strongest publisher claim the data actually supports, and it is always
        available because ``url`` is ``NOT NULL``.

        Why it earns a place in the brief: a reader needs to know *who said it*
        before deciding what a headline is worth. "reuters.com" and an unknown
        aggregator carry very different weight on the same words.

        Returns "" when the URL has no parseable host, so the template omits the
        field rather than printing a fabricated one.

        Scrubbed and bounded, because this is an ATTRIBUTION surface fed by a
        vendor-controlled URL. Jinja's autoescape only neutralises ``< > & " '``;
        Unicode bidi controls are category ``Cf`` and pass through it verbatim.
        An unterminated ``U+202E`` in a hostname renders ``‮moc.sretuer`` as
        "reuters.com" while the href navigates somewhere else entirely — a
        displayed publisher that contradicts the actual link target, on the
        surface James weighs financially. It also bleeds past ``</span>`` and
        reverses the rest of the item.

        ``isprintable()`` drops every ``Cf``/control character; this is the same
        idiom ``asxos/ingestion/news.py`` already applies to vendor tags for the
        log sink, reused rather than reinvented. The 64-char cap matches the
        neighbouring convention of bounding every untrusted string.

        Known residual: this does NOT defeat IDN homographs — Cyrillic
        ``rеuters.com`` is printable and survives. Punycode display is the fix
        and is deliberately out of scope here; recorded, not silently ignored.
        """
        host = (urlparse(self.url).hostname or "").lower()
        host = "".join(c for c in host if c.isprintable())[:64]
        return host[4:] if host.startswith("www.") else host


@dataclass(frozen=True)
class JobFailure:
    job_name: str
    as_of: date
    error_message: str


@dataclass(frozen=True)
class PortfolioTradeSummary:
    """Minimal trade row for the brief's portfolio section."""

    symbol: str
    side: str  # 'buy' or 'sell'
    delta_aud: Decimal


@dataclass(frozen=True)
class PortfolioSection:
    """Section 6 of the brief — portfolio adjustments (M13.7).

    Populated only when both ASXOS_PERSONAL_USE=1 and
    ASXOS_PORTFOLIO_BRIEF_ENABLED=1, and a fresh build_portfolio run
    exists (as_of >= brief_date - 2, plan I.7).
    """

    run_id: int
    run_as_of: date
    top_buys: list[PortfolioTradeSummary]
    top_sells: list[PortfolioTradeSummary]
    total_buy_aud: Decimal
    total_sell_aud: Decimal
    turnover_aud: Decimal


class NewsStatus(StrEnum):
    """Which of four states produced the news section's item list.

    An empty `news_items` list is ambiguous on its own — see `_news_section`
    for why the distinction is load-bearing rather than cosmetic.

    `StrEnum` matches every other status vocabulary in this codebase
    (`ReviewStatus`, `DisciplineLevel`, `SectionStatus`, …) and Jinja compares
    and renders members exactly as the bare strings, so the template needs no
    filter or context processor — `brief.html.j2` already does this with
    `DisciplineLevel` and `ReviewStatus`.

    When the news section migrates to the V2 brief, these map onto the existing
    `asxos/domain/brief/types.py::SectionStatus` (ok→ok, quiet→no_data,
    unverified→degraded, disabled→suppressed) rather than porting a fifth
    vocabulary across.
    """

    DISABLED = "disabled"      # a gate is off; the feature is not running
    UNVERIFIED = "unverified"  # ingestion did not pass its freshness gate
    QUIET = "quiet"            # verified fresh, genuinely nothing qualifying
    OK = "ok"                  # qualifying items present


# Module-level aliases: the call sites and tests read better unqualified, and
# these keep the diff against the original four constants reviewable.
NEWS_DISABLED = NewsStatus.DISABLED
NEWS_UNVERIFIED = NewsStatus.UNVERIFIED
NEWS_QUIET = NewsStatus.QUIET
NEWS_OK = NewsStatus.OK


@dataclass(frozen=True)
class BriefData:
    as_of: date
    holdings_count: int
    regulatory_hits: list[RegulatoryHit] = field(default_factory=list)
    job_failures: list[JobFailure] = field(default_factory=list)
    news_items: list[NewsItem] = field(default_factory=list)
    # Which of the four news states produced `news_items`. Defaults to
    # NEWS_DISABLED so a BriefData built without news never claims a quiet day.
    news_status: NewsStatus = NEWS_DISABLED
    portfolio_section: PortfolioSection | None = None
    # PR2a: collected, not yet rendered (PR2b adds the brief.html.j2 block).
    discipline_findings: list[DisciplineFinding] = field(default_factory=list)
    latest_price_date: date | None = None
    # Latest *complete* trading day in `prices` (not the calendar as_of). It is a
    # statement about PRICE completeness and nothing else: since the signal and
    # regime queries it used to anchor were retired (manifest A4), every
    # remaining collector takes the calendar `as_of`. Labelling it "evidence as
    # of" would be a fabricated provenance claim — the exact failure item 5 is
    # about — so the template says "Prices complete to". None only when no
    # complete day exists at all.
    data_as_of: date | None = None

    @property
    def has_failures(self) -> bool:
        return bool(self.job_failures)

    @property
    def prices_stale(self) -> bool:
        if self.latest_price_date is None:
            return True
        return (self.as_of - self.latest_price_date).days > 5

    @property
    def review(self) -> ReviewOutcome:
        """The brief's single headline state (packet P1 required-work item 4).

        Derived, never stored, so a caller cannot hand-assemble a ``BriefData``
        whose headline disagrees with its own findings.

        Mapping — deliberately narrow, since every input is the user's own
        authored data or this system's own job health:

        * ``error`` findings and job failures are **blocking**: a check that
          could not run, or a pipeline that failed, means the brief cannot
          claim to have looked. (``DisciplineLevel.error`` is already defined
          as "could not be computed" rather than "bad news".)
        * ``red`` / ``yellow`` findings are **attention**.
        * ``info`` findings never raise the status — but they do not count as
          discipline evidence either. ``_cgt_boundary_findings`` appends
          ``info`` rows into the same list, so testing that list for emptiness
          would let a single CGT-boundary fact make a wholly unchecked portfolio
          read ``CLEAR``. The unknown below is therefore keyed on *non-info*
          findings.
        * Stale prices, and holdings with no discipline evidence at all, are
          **unknowns** — the two ways this brief can look calm while knowing
          nothing (packet P1 required-work item 5).

        A brief with no holdings, no findings and fresh prices is ``CLEAR``:
        there is genuinely nothing to review, which is a different statement from
        "we could not review it". The price condition is load-bearing — with no
        price data at all, ``prices_stale`` is ``True`` and the same brief is
        ``EVIDENCE_THIN``.
        """
        # Equality, not identity, throughout — `DisciplineLevel` is a `StrEnum`
        # and the template filters the same field with Jinja's `equalto`. Using
        # `is` here would let a raw-string level render the "could not run"
        # banner while leaving the headline un-BLOCKED.
        blocking = [
            f.message
            for f in self.discipline_findings
            if f.level == DisciplineLevel.error
        ]
        blocking += [
            f"job {f.job_name} failed on {f.as_of}" for f in self.job_failures
        ]
        attention = [
            f.message
            for f in self.discipline_findings
            if f.level in (DisciplineLevel.red, DisciplineLevel.yellow)
        ]
        unknowns: list[str] = []
        if self.prices_stale:
            unknowns.append(
                "Prices stale — latest price date: "
                f"{self.latest_price_date or 'no data'}"
            )
        checked = any(
            f.level != DisciplineLevel.info for f in self.discipline_findings
        )
        if self.holdings_count and not checked:
            unknowns.append(
                f"{self.holdings_count} holding(s) with no discipline evidence"
            )
        return classify(blocking=blocking, attention=attention, unknowns=unknowns)


async def collect(as_of: date) -> BriefData:
    """Single async DB session, four sections + optional portfolio section.

    No model gate and no ``signals`` read (manifest A3/A4). The gate call that
    used to open this block was ``resolve_production_model(required=False)``,
    whose only job was deciding whether the Model A regime/signal reads below it
    could run; with those reads gone there is nothing left for it to gate, so it
    goes with them. The ``required=False`` overload itself stays on
    ``production_gate.py`` — that is risk-register R9's fix and it belongs to any
    future display consumer, not to this one.
    """
    # Use module-level `acquire` if set (e.g. by tests); otherwise lazy-import
    # from asxos.db to avoid pulling pydantic_settings in at collection time.
    _acquire: Any = globals().get("acquire")
    if _acquire is None:
        from asxos.db import acquire as _acquire
    async with _acquire() as conn:
        # Anchor the brief's evidence on the latest *complete* trading day, not
        # the calendar as_of — EOD data lands ~1 day late. The calendar as_of is
        # still the brief's title/delivery date.
        data_as_of = await latest_complete_trading_day(conn)

        holdings_count = await conn.fetchval(
            "SELECT COUNT(*) FROM current_holdings"
        ) or 0

        latest_price_date: date | None = await conn.fetchval(
            """
            SELECT MAX(p.dt)
            FROM prices p
            JOIN universe u ON u.symbol = p.symbol
            WHERE u.is_active = TRUE
            """
        )

        regulatory_hits = await _regulatory_hits(conn, as_of)
        job_failures = await _job_failures(conn, as_of)
        news_items, news_status = await _news_section(conn, as_of)
        portfolio_section = await _portfolio_section(conn, as_of)

        # Fail-loud isolation (CLAUDE.md #10): a broken discipline query must
        # never take down the rest of the brief. Surface it as a single loud
        # error finding instead — the same "never silently vanish" contract
        # evaluate_discipline() already enforces for its own per-check errors.
        try:
            discipline_findings = await _discipline_findings(conn, as_of)
        except Exception as exc:
            discipline_findings = [
                DisciplineFinding(
                    check="discipline_section",
                    level=DisciplineLevel.error,
                    message=f"⚠ discipline section could not run: {exc}",
                )
            ]
        # CGT-boundary facts are folded into the discipline section (one gated
        # surface, replacing the former standalone "Tax actions" table).
        # Isolated separately so a holdings-query failure surfaces loudly
        # without taking down the thesis findings above.
        try:
            discipline_findings.extend(await _cgt_boundary_findings(conn, as_of))
        except Exception as exc:
            discipline_findings.append(
                DisciplineFinding(
                    check="cgt_discount_boundary",
                    level=DisciplineLevel.error,
                    message=f"⚠ cgt_discount_boundary section could not run: {exc}",
                )
            )

    return BriefData(
        as_of=as_of,
        holdings_count=int(holdings_count),
        regulatory_hits=regulatory_hits,
        job_failures=job_failures,
        news_items=news_items,
        news_status=news_status,
        portfolio_section=portfolio_section,
        discipline_findings=discipline_findings,
        latest_price_date=latest_price_date,
        data_as_of=data_as_of,
    )


async def _cgt_boundary_findings(
    conn: asyncpg.Connection, as_of: date, window_days: int = 30
) -> list[DisciplineFinding]:
    """Held lots approaching the 12-month CGT-discount threshold, as evidence-
    only discipline findings (spec §5.1). Folded from the retired standalone
    "Tax actions" table so the fact lives on ONE gated surface.

    Gated on ``ASXOS_PERSONAL_USE=1`` — parity with ``_discipline_findings`` /
    ``_news_section`` / ``_portfolio_section``, closing the gap the old ungated
    ``_tax_actions`` left open (portfolio-team-visibility §7/R12).

    s766B firewall: states the user's own acquisition date + calendar
    arithmetic on it (reusing ``days_to_eligibility``, §5.1 — never day-count) —
    no trade direction, no benefit/discount-rate opinion. Quiet by default; a
    malformed ``acquired_at`` surfaces LOUDLY as an ``error`` finding rather than
    silently dropping the lot (CLAUDE.md #10).
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return []
    rows = await conn.fetch(
        """
        SELECT id, symbol, acquired_at
        FROM current_holdings
        ORDER BY acquired_at
        """
    )
    findings: list[DisciplineFinding] = []
    for r in rows:
        try:
            days = days_to_eligibility(r["acquired_at"], as_of)
            if not (0 < days <= window_days):
                continue
            eligible_at = r["acquired_at"] + relativedelta(years=1) + timedelta(days=1)
            findings.append(
                DisciplineFinding(
                    check="cgt_discount_boundary",
                    level=DisciplineLevel.info,
                    symbol=r["symbol"],
                    message=(
                        f"{r['symbol']}: lot {r['id']} (acquired {r['acquired_at']}) "
                        f"reaches the 12-month CGT-discount threshold on "
                        f"{eligible_at} — {days} day(s) away (s 115-25(1) ITAA 1997)."
                    ),
                )
            )
        except Exception as exc:  # fail-loud: never silently drop a lot (CLAUDE.md #10)
            findings.append(
                DisciplineFinding(
                    check="cgt_discount_boundary",
                    level=DisciplineLevel.error,
                    symbol=r["symbol"],
                    message=f"⚠ cgt_discount_boundary could not run for {r['symbol']}: {exc}",
                )
            )
    return findings


async def _regulatory_hits(
    conn: asyncpg.Connection, as_of: date, lookback_hours: int = 24
) -> list[RegulatoryHit]:
    rows = await conn.fetch(
        """
        SELECT r.source, r.title, r.published_at, r.relevance_tags
        FROM regulatory_events r
        WHERE r.published_at >= $1::date - INTERVAL '2 day'
          AND r.ingested_at >= $1::date - make_interval(hours => $2)
        ORDER BY r.published_at DESC
        """,
        as_of,
        lookback_hours,
    )
    holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
    holdings = {r["symbol"] for r in holdings_rows}

    out: list[RegulatoryHit] = []
    for r in rows:
        tags = r["relevance_tags"] or {}
        if isinstance(tags, str):
            import json
            tags = json.loads(tags)
        symbols = tags.get("symbols") if isinstance(tags, dict) else []
        kind = tags.get("kind", "other") if isinstance(tags, dict) else "other"
        # Match on any holding symbol
        for s in symbols or []:
            if s in holdings:
                out.append(
                    RegulatoryHit(
                        symbol=s,
                        source=r["source"],
                        title=r["title"],
                        published_at=r["published_at"],
                        kind=kind,
                    )
                )
                break
    return out


async def _job_failures(
    conn: asyncpg.Connection, as_of: date
) -> list[JobFailure]:
    rows = await conn.fetch(
        """
        SELECT job_name, as_of, error_message
        FROM job_runs
        WHERE as_of = $1 AND status = 'failure'
        ORDER BY job_name
        """,
        as_of,
    )
    return [
        JobFailure(
            job_name=r["job_name"],
            as_of=r["as_of"],
            error_message=(r["error_message"] or "")[:200],
        )
        for r in rows
    ]


async def _news_section(
    conn: asyncpg.Connection, as_of: date
) -> tuple[list[NewsItem], NewsStatus]:
    """Return ``(items, status)`` for section 6 (M14a).

    Three-layer gating (mirrors M13.7 Amendment C):
      1. ASXOS_PERSONAL_USE=1  (regulatory firewall)
      2. ASXOS_NEWS_BRIEF_ENABLED=1  (paper-trade dark gate; default 0)
      3. the LATEST ingest_news run in the window succeeded with no degraded
         note (freshness gate — see _news_ingest_fresh for why the latest run,
         and why not a row count)

    **Why this returns a status and not a bare list.** An empty list previously
    collapsed four materially different situations into one indistinguishable
    outcome — the section simply vanished from the brief. James could not tell
    "no qualifying news today" from "ingestion has written zero rows for a
    month", and the second is exactly the 2026-08 false-green incident
    (``docs/market-trends-report-2026-08-05.md`` §1). A reader who sees nothing
    reasonably infers nothing happened; here, nothing rendered was equally
    consistent with the pipeline being broken.

    The four states are now distinct and each is rendered honestly:

    ``NEWS_DISABLED``    a gate is off — the feature is not running, section omitted
    ``NEWS_UNVERIFIED``  ingestion did not pass its freshness gate — say so, do
                         NOT imply the absence of news is a finding
    ``NEWS_QUIET``       ingestion verified fresh and genuinely produced nothing
                         qualifying — a real, reportable "no news" answer
    ``NEWS_OK``          qualifying items exist

    Only ``NEWS_QUIET`` licenses the statement "no qualifying news was found".
    ``NEWS_UNVERIFIED`` must never be rendered as if it were quiet.

    The template gates on a positive allowlist of these four values, so a status
    it does not recognise (a typo, or a fifth state added here without a matching
    template arm) omits the section rather than falling through to one of the
    copy blocks above. Adding a state means adding it in both places.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return [], NEWS_DISABLED
    if os.environ.get("ASXOS_NEWS_BRIEF_ENABLED") != "1":
        return [], NEWS_DISABLED
    if not await _news_ingest_fresh(conn, as_of):
        return [], NEWS_UNVERIFIED
    items = await _holding_news(conn, as_of)
    return items, (NEWS_OK if items else NEWS_QUIET)


async def _news_ingest_fresh(conn: asyncpg.Connection, as_of: date) -> bool:
    """True when the LATEST ingest_news run in the window was clean.

    "Clean" is ``status='success' AND error_message IS NULL`` — evaluated in
    Python, on the most recent run only. Three prior designs each failed a
    different way, and this docstring records all three so none returns:

    1. ``status='success'`` alone shared one forgeable field with the surface's
       ship condition: 22 consecutive runs reported success over an empty table
       (``docs/market-trends-report-2026-08-05.md`` §1).
    2. The overcorrection added ``rows_written > 0`` — a row count on the WRITER
       as a health signal for the READER. ``holding_news`` keeps 7 days and this
       brief reads a 24h window, so an article ingested yesterday is still
       current today, and a genuinely quiet run this morning would have hidden
       it. The two queries do not share a window.
    3. Any predicate placed in the WHERE clause next to ``LIMIT 1`` asks "did
       ANY qualifying run happen in the window?" — so an older clean run
       satisfied the filter and the latest degraded or failed run was never
       examined. Filtering the evidence of a problem out of the query is the
       incident's own shape, one level up.

    Hence: select the latest run inside a BOTH-SIDED window, then judge it.
    The upper bound matters because ``collect()`` accepts an explicit historical
    ``as_of`` (re-sends, backfills): without it, a run dated after the brief
    would decide whether a past day was fresh. A freshness gate must answer
    from what was knowable on the day it describes.

    ``error_message IS NULL`` is meaningful because ``jobs/ingest_news.py``
    writes a note ONLY on real degradation (fetch failures, malformed payloads,
    unmatched articles) — never on a quiet day. That coupling is load-bearing
    and recorded at the note-writing site.

    The two other consumers of the same job_runs row still read status alone
    (``jobs/ingest_sentiment.py::_upstream_ok`` — soft, WARNING only; and the
    ``asx news signoff`` prerequisite in ``asxos/cli/news.py``). Widen those
    before treating a green ingest_news as evidence of anything.
    """
    cutoff = as_of - timedelta(days=1)
    rows = await conn.fetch(
        """
        SELECT status, error_message FROM job_runs
        WHERE job_name = 'ingest_news' AND as_of >= $1 AND as_of <= $2
        ORDER BY as_of DESC
        LIMIT 1
        """,
        cutoff,
        as_of,
    )
    if not rows:
        return False
    latest = rows[0]
    return latest["status"] == "success" and latest["error_message"] is None


async def _holding_news(
    conn: asyncpg.Connection, as_of: date, lookback_hours: int = 24
) -> list[NewsItem]:
    """Fetch holding_news rows from the last ``lookback_hours`` hours.

    Filters the result to symbols that appear in current_holdings.
    Returns at most 20 items, ordered most-recent first.
    """
    rows = await conn.fetch(
        """
        SELECT url, title, published_at, symbols, sentiment
        FROM holding_news
        WHERE published_at >= $1::date - make_interval(hours => $2)
        ORDER BY published_at DESC
        LIMIT 20
        """,
        as_of,
        lookback_hours,
    )
    holdings_rows = await conn.fetch("SELECT symbol FROM current_holdings")
    holdings = {r["symbol"] for r in holdings_rows}

    out: list[NewsItem] = []
    for r in rows:
        syms = r["symbols"] or []
        if isinstance(syms, str):
            import json
            syms = json.loads(syms)
        matched = [s for s in syms if s in holdings]
        if not matched:
            continue
        out.append(
            NewsItem(
                symbols=matched,
                title=r["title"],
                url=r["url"],
                published_at=r["published_at"],
                sentiment=r["sentiment"] or "",
            )
        )
    return out


async def _portfolio_section(
    conn: asyncpg.Connection, as_of: date
) -> PortfolioSection | None:
    """Return portfolio adjustments for section 6, or None if gated out.

    Gating (plan I.7 + plan I.6 + Part 0 Q1):
    - ASXOS_PERSONAL_USE must be "1" (regulatory firewall).
    - ASXOS_PORTFOLIO_BRIEF_ENABLED must be "1" (paper-trade gate; stays 0
      until 4 weeks of sign-off per M13.8).
    - A successful ``build_portfolio`` job run must exist with
      ``as_of >= as_of - 2`` (freshness gate; plan I.7 standardises on
      24h lookback with a 2-day tolerance for the weekly cron cadence).

    The section is omitted entirely when any gate fails — never partial or
    stale (plan I.7: "If the cron failed: section 6 is omitted entirely").
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return None
    if os.environ.get("ASXOS_PORTFOLIO_BRIEF_ENABLED") != "1":
        return None

    # Freshness gate: most recent successful build_portfolio run within 2 days.
    # Uses as_of date arithmetic (plan H.2 QUICK-WIN-1: filter on as_of, not created_at).
    cutoff = as_of - timedelta(days=2)
    run_row = await conn.fetchrow(
        """
        SELECT r.run_id, r.as_of
        FROM rebalance_runs r
        JOIN job_runs j
          ON j.job_name = 'build_portfolio'
         AND j.as_of = r.as_of
         AND j.status = 'success'
        WHERE r.as_of >= $1
        ORDER BY r.as_of DESC
        LIMIT 1
        """,
        cutoff,
    )
    if run_row is None:
        return None

    run_id = run_row["run_id"]
    run_as_of = run_row["as_of"]

    # Top 3 buys and top 3 sells (by |delta_aud|).
    trade_rows = await conn.fetch(
        """
        SELECT symbol, side, delta_aud
        FROM proposed_trades
        WHERE run_id = $1 AND side IN ('buy', 'sell')
        ORDER BY ABS(delta_aud) DESC
        """,
        run_id,
    )

    # Single pass over trade_rows (07-18 audit: was four passes — two
    # filtered comprehensions + two filtered sums). Rows arrive ordered by
    # |delta_aud| DESC, so appending the first 3 per side preserves the
    # top-3 semantics exactly.
    top_buys: list[PortfolioTradeSummary] = []
    top_sells: list[PortfolioTradeSummary] = []
    total_buy_aud = Decimal("0")
    total_sell_aud = Decimal("0")
    for r in trade_rows:
        delta = Decimal(str(r["delta_aud"]))
        if r["side"] == "buy":
            total_buy_aud += delta
            if len(top_buys) < 3:
                top_buys.append(
                    PortfolioTradeSummary(symbol=r["symbol"], side="buy", delta_aud=delta)
                )
        else:  # side = 'sell' (query filters to buy/sell only)
            total_sell_aud += abs(delta)
            if len(top_sells) < 3:
                top_sells.append(
                    PortfolioTradeSummary(symbol=r["symbol"], side="sell", delta_aud=delta)
                )

    return PortfolioSection(
        run_id=run_id,
        run_as_of=run_as_of,
        top_buys=top_buys,
        top_sells=top_sells,
        total_buy_aud=total_buy_aud,
        total_sell_aud=total_sell_aud,
        turnover_aud=total_buy_aud + total_sell_aud,
    )


def _thesis_discipline_inputs(
    thesis_rows: list[asyncpg.Record], prices: dict[str, Decimal]
) -> tuple[ThesisDisciplineInput, ...]:
    """Build per-thesis inputs, native-currency-against-native throughout.

    Currency safety (R10, `.claude/rules/portfolio-conventions.md`): entry/
    target/stop come straight from `theses` (authored in the holding's own
    native currency) and current comes from `prices.close` (also native) —
    all four legs are native-against-native, no FX step needed here.
    """
    return tuple(
        ThesisDisciplineInput(
            symbol=r["symbol"],
            currency="USD" if is_foreign_symbol(r["symbol"]) else "AUD",
            revisit_due_at=r["revisit_due_at"].date(),
            opened_at=r["opened_at"].date(),
            timeline_days=r["timeline_days"],
            entry_price_native=r["actual_entry_price"],
            current_price_native=prices.get(r["symbol"]),
            target_price_native=r["target_price"],
            stop_price_native=r["stop_price"],
            conviction_level=r["conviction_level"],
        )
        for r in thesis_rows
    )


def _holding_weights(
    holding_rows: list[asyncpg.Record],
    prices: dict[str, Decimal],
    fx_rate: Decimal | None,
) -> tuple[HoldingWeight, ...]:
    """Market value per holding, converted to AUD for the concentration check.

    Foreign (USD) holdings need AUDUSD to convert their native market value
    to AUD (R10) — never divide an AUD figure by quantity to get back to
    native, always convert forward from native. A foreign holding with no
    FX rate available is omitted rather than mis-converted.
    """
    holdings: list[HoldingWeight] = []
    for r in holding_rows:
        close = prices.get(r["symbol"])
        if close is None:
            continue
        mv_native = Decimal(str(r["quantity"])) * close
        if is_foreign_symbol(r["symbol"]):
            if fx_rate is None:
                continue
            mv_aud = mv_native / fx_rate
        else:
            mv_aud = mv_native
        holdings.append(HoldingWeight(symbol=r["symbol"], market_value_aud=mv_aud))
    return tuple(holdings)


async def _discipline_findings(
    conn: asyncpg.Connection, as_of: date
) -> list[DisciplineFinding]:
    """Loader for `asxos.domain.theses.discipline.evaluate_discipline()` (PR2a).

    Fetches thesis/holding/price rows, then delegates the native-currency
    thesis-input build to `_thesis_discipline_inputs`, the AUD holding-weight
    build to `_holding_weights`, and the per-holding native unrealised return
    to `unrealised_return` (R10 currency-safety notes live on those helpers,
    next to the arithmetic they govern).

    Gated on ``ASXOS_PERSONAL_USE=1`` only (proposal §6 acceptance criteria) —
    deliberately not ``ASXOS_PORTFOLIO_BRIEF_ENABLED``, which gates the
    allocator's trade suggestions and is orthogonal to this model-independent
    digest (§4). Matches the same gate `_news_section`/`_portfolio_section`
    already apply to their own display-only data.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return []

    thesis_rows = await conn.fetch(
        """
        SELECT symbol, revisit_due_at, opened_at, timeline_days,
               actual_entry_price, target_price, stop_price, conviction_level
        FROM theses
        WHERE status = 'active'
          AND governance_status = 'approved'
        ORDER BY opened_at
        """
    )
    holding_rows = await conn.fetch("SELECT symbol, quantity FROM current_holdings")

    symbols = sorted({r["symbol"] for r in thesis_rows} | {r["symbol"] for r in holding_rows})
    prices: dict[str, Decimal] = {}
    if symbols:
        price_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (symbol) symbol, close
            FROM prices
            WHERE symbol = ANY($1) AND dt <= $2
            ORDER BY symbol, dt DESC
            """,
            symbols,
            as_of,
        )
        prices = {r["symbol"]: Decimal(str(r["close"])) for r in price_rows}

    # Latest snapshot that actually carries an FX rate (need not be the latest
    # snapshot overall) — converts foreign holdings' native MV to AUD for the
    # concentration check (R10).
    fx_rows = await conn.fetch(
        """
        SELECT fx_rate_audusd
        FROM portfolio_daily_snapshots
        WHERE as_of <= $1 AND fx_rate_audusd IS NOT NULL
        ORDER BY as_of DESC
        LIMIT 1
        """,
        as_of,
    )
    fx_rate = Decimal(str(fx_rows[0]["fx_rate_audusd"])) if fx_rows else None

    thesis_inputs = _thesis_discipline_inputs(thesis_rows, prices)
    holdings = _holding_weights(holding_rows, prices, fx_rate)

    port_input = PortfolioDisciplineInput(holdings=holdings)
    findings = evaluate_discipline(thesis_inputs, port_input, as_of)
    # Per-holding unrealised return (native, broker-matching) — appended here as a
    # display fact (like the CGT-boundary line) so evaluate_discipline() stays
    # quiet-by-default. Native entry vs current price only; no cost base, no
    # benchmark, no Model A (R10 / rule #11 safe). Each is isolated with the same
    # loud-error idiom the per-thesis checks use, so a single malformed thesis
    # surfaces one error line rather than collapsing the whole section
    # (security-engineer review, 2026-07-19).
    for ti in thesis_inputs:
        try:
            pnl = unrealised_return(ti)
        except Exception as exc:  # isolate a malformed thesis, fail loud (#10)
            findings.append(
                DisciplineFinding(
                    check="unrealised_return",
                    level=DisciplineLevel.error,
                    message=f"⚠ unrealised_return could not run for {ti.symbol}: {exc}",
                    symbol=ti.symbol,
                )
            )
            continue
        if pnl is not None:
            findings.append(pnl)
    return findings


def render_html(data: BriefData) -> str:
    """Render the brief template. Any undefined name is a hard failure.

    ``undefined=StrictUndefined`` is load-bearing, not tidiness. Jinja's default
    ``Undefined`` is falsy and renders as an empty string, so a template
    referencing a ``BriefData`` field that no longer exists produces a page that
    looks fine. That is exactly how this brief could have gone wrong during the
    Model A retirement: three of the five ``model_shelved`` references were
    suppression conditions (``{% if not d.model_shelved %}`` gated the whole
    signal section), so deleting the field before the template would have
    silently *un*-suppressed every dead-engine banner and section, with no
    exception, no failing job and no alert. Strict undefined turns that entire
    class of failure into a loud ``UndefinedError``.

    ``asxos/domain/decision_engine/renderer.py`` already renders this way; this
    environment was the outlier.
    """
    return brief_env().get_template("brief.html.j2").render(d=data)


def brief_env() -> jinja2.Environment:
    """The brief's Jinja environment. Exposed so its strictness is testable.

    See :func:`render_html` for why ``StrictUndefined`` is a safety property here
    rather than a style preference.
    """
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
    )
