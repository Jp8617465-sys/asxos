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

  1. Job problems banner (rendered only when there are any) — failed runs *and*
     runs stuck in `running`, over the window since the previous successful
     `compose_brief`. It read "the last 24h" until 2026-08-18, describing an
     `as_of = $1` filter that could not match a row on any day; the heading in
     `brief.html.j2` now says what the query covers. See `_job_failures`.
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
  8. Outcome vs benchmark — per-open-lot return since acquisition, the benchmark's
     return over the same window from `portfolio_daily_snapshots.benchmark_tr_level`,
     and alpha. The only production code behind the north star's "benchmark-relative"
     output (`docs/product/north-star.md:40`). Anchored on
     `holding_lots.acquired_at`/`cost_base_normal` and `prices.close` with an explicit
     FX step — **never** on differencing `portfolio_daily_snapshots.capital_aud`
     (why: `asxos/domain/brief/collectors/wealth_state.py:101-108`).
     Sleeve-separated per governor ruling F2 and proxy-vetoed per F1
     (`docs/product/roadmap-state.md:252-254`).
     Model-independent by construction — no `signals`, no `resolve_production_model()`.
     Gated on ASXOS_PERSONAL_USE=1 only (§3 parity), which
     `.github/workflows/daily-brief.yml` already sets; no new flag, and explicitly
     not `ASXOS_V2_BRIEF_ENABLED` (the V2 tree stays dark, deferred to Stage 6).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import jinja2
from dateutil.relativedelta import relativedelta

from asxos.brief.bluf import bluf_sentence
from asxos.brief.deltas import BookDelta, load_book_delta
from asxos.brief.section import (
    SectionResult,
    SectionStatus,
    assemble_sections,
)
from asxos.domain.benchmark.outcome import (
    MAX_ANCHOR_LAG_DAYS,
    BenchmarkAnchor,
    LotInput,
    Observation,
    OutcomeSection,
    Sleeve,
    build_outcome_section,
    sleeve_for,
)
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
    data_sanity_escalation,
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


class JobProblemKind(StrEnum):
    """Which operational state produced a `JobFailure`.

    `StrEnum` for the same reasons as `NewsStatus`: it matches every other status
    vocabulary in this codebase, and Jinja compares and renders members exactly as
    the bare strings, so `brief.html.j2` needs no filter. A closed vocabulary also
    puts the two states under mypy instead of leaving `kind` an open `str`.
    """

    FAILURE = "failure"  # the job ran and raised
    STUCK = "stuck"  # started, never reported — no failure, so nothing alerts


@dataclass(frozen=True)
class JobFailure:
    job_name: str
    as_of: date
    error_message: str
    kind: JobProblemKind = JobProblemKind.FAILURE


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

    DISABLED = "disabled"  # a gate is off; the feature is not running
    UNVERIFIED = "unverified"  # ingestion did not pass its freshness gate
    QUIET = "quiet"  # verified fresh, genuinely nothing qualifying
    OK = "ok"  # qualifying items present


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
    # Section 8 — per-open-lot return since acquisition, the benchmark's return
    # over the same window, and alpha. ``None`` when ASXOS_PERSONAL_USE is unset
    # (the section is then absent, not empty). ``outcome_error`` is set instead
    # when the loader raised: the brief says the measurement could not run rather
    # than omitting it, because an absent section and a failed one look identical
    # to a reader and only one of them is honest (CLAUDE.md #10).
    outcome_section: OutcomeSection | None = None
    outcome_error: str | None = None
    latest_price_date: date | None = None
    # Latest *complete* trading day in `prices` (not the calendar as_of). It is a
    # statement about PRICE completeness and nothing else: since the signal and
    # regime queries it used to anchor were retired (manifest A4), every
    # remaining collector takes the calendar `as_of`. Labelling it "evidence as
    # of" would be a fabricated provenance claim — the exact failure item 5 is
    # about — so the template says "Prices complete to". None only when no
    # complete day exists at all.
    data_as_of: date | None = None
    # Stage 0 seam: four-state section artefacts. Empty default keeps every
    # existing BriefData(...) test constructing without `sections` valid;
    # `resolved_sections` synthesises from the payload fields in that case.
    sections: dict[str, SectionResult] = field(default_factory=dict)
    # Stage 1: book-level snapshot delta vs the previous snapshot. None when a
    # test constructs BriefData without collect(); collect() always sets it.
    deltas: BookDelta | None = None

    @property
    def resolved_sections(self) -> dict[str, SectionResult]:
        if self.sections:
            return self.sections
        computed = datetime.now(UTC)
        # `self.prices_stale`, not a third copy of the `> 5` threshold. The
        # property below is the canonical definition; `collect()` carries the
        # only other copy because no BriefData exists yet at that point. Two
        # copies that must agree is already one too many -- a third, here,
        # would let the integrity line and the headline disagree the moment
        # the window is tuned.
        return assemble_sections(
            latest_price_date=self.latest_price_date,
            prices_stale=self.prices_stale,
            job_failures=self.job_failures,
            discipline_findings=self.discipline_findings,
            outcome_section=self.outcome_section,
            outcome_error=self.outcome_error,
            regulatory_hits=self.regulatory_hits,
            news_items=self.news_items,
            news_status=str(self.news_status),
            news_error=None,
            portfolio_section=self.portfolio_section,
            computed_at=computed,
            data_as_of=self.data_as_of,
        )

    @property
    def core_untrusted(self) -> bool:
        """Prices (core) are STALE or MISSING — integrity line is a warning."""
        prices = self.resolved_sections.get("prices")
        if prices is None:
            return self.prices_stale
        return prices.status in {SectionStatus.STALE, SectionStatus.MISSING}

    @property
    def has_failures(self) -> bool:
        """Whether the job-problems banner has anything to render.

        "Failures" is the older, narrower word: since `JobProblemKind` this list
        also carries `stuck` rows, which are by definition *not* failures. Both
        names are kept rather than churned through the template and every test —
        `_job_failures` is where the two kinds are defined.
        """
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
        * ``watchlist_only`` findings do not count as discipline evidence
          either, for the same reason and through the same side door. A
          ``data_sanity_escalation`` red can arise from a ``watching`` thesis —
          a row with no capital behind it — and a finding about an
          uninvested watchlist record says nothing about whether any *holding*
          was examined. Counting it would let one stale watchlist row silence
          the "N holding(s) with no discipline evidence" unknown for a portfolio
          where zero holdings were checked.
        * Stale prices, holdings with no discipline evidence at all, and a
          section 8 that could not run are **unknowns** — the three ways this
          brief can look calm while knowing nothing (packet P1 required-work
          item 5).

        ``outcome_error`` is an **unknown, not blocking**, and the distinction is
        deliberate. Section 8 is a measurement, not a check: its failure means
        "we cannot tell you how the lots did", not "a discipline check could not
        run". ``EVIDENCE_THIN`` is the honest reading of that. What it must not
        do is nothing at all — before this mapping, a brief with
        ``holdings_count == 0``, fresh prices and a crashed outcome loader
        rendered ``CLEAR`` in the header directly above a red "could not run"
        banner. That is precisely the shape
        :mod:`asxos.domain.review.status` exists to close ("an absence of
        evidence presented as evidence of absence"), reappearing through a
        section added after the module was written.

        The two exclusions above and this mapping are the same defect caught
        three times from three directions — an ``info`` row, a watchlist row,
        and a crashed section each dressing "we checked nothing" as "nothing to
        report". Any fourth path into ``discipline_findings`` gets the same
        question asked of it.

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
        blocking = [f.message for f in self.discipline_findings if f.level == DisciplineLevel.error]
        blocking += [f"job {f.job_name} failed on {f.as_of}" for f in self.job_failures]
        attention = [
            f.message
            for f in self.discipline_findings
            if f.level in (DisciplineLevel.red, DisciplineLevel.yellow)
        ]
        unknowns: list[str] = []
        if self.prices_stale:
            unknowns.append(
                f"Prices stale — latest price date: {self.latest_price_date or 'no data'}"
            )
        if self.outcome_error:
            unknowns.append(f"Outcome vs benchmark not measured — {self.outcome_error}")
        checked = any(
            f.level != DisciplineLevel.info and not f.watchlist_only
            for f in self.discipline_findings
        )
        if self.holdings_count and not checked:
            unknowns.append(f"{self.holdings_count} holding(s) with no discipline evidence")
        return classify(blocking=blocking, attention=attention, unknowns=unknowns)

    @property
    def bluf(self) -> str:
        return bluf_sentence(self.review)

    @property
    def exception_findings(self) -> list[DisciplineFinding]:
        return [f for f in self.discipline_findings if f.level != DisciplineLevel.info]


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

        holdings_count = await conn.fetchval("SELECT COUNT(*) FROM current_holdings") or 0

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
        # News is non-core: a collector exception must not block the send
        # (docs/product/daily-brief-v2.md §3.1). Map to MISSING + UNVERIFIED
        # body copy so the template still refuses to claim a quiet day.
        news_error: str | None = None
        try:
            news_items, news_status = await _news_section(conn, as_of)
        except Exception as exc:
            news_items, news_status = [], NEWS_UNVERIFIED
            news_error = f"news section could not run: {exc}"
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

        # Same fail-loud isolation as the two blocks above — with one deliberate
        # difference. Those map their failure to a `DisciplineLevel.error`
        # finding, which `BriefData.review` treats as **blocking** (BLOCKED). A
        # section-8 failure is carried on its own `outcome_error` field and
        # treated as an **unknown** (EVIDENCE_THIN) instead, because section 8 is
        # a measurement rather than a discipline check. Both render loudly; only
        # the headline differs. See `BriefData.review` for the full reasoning —
        # what neither may do is leave the headline untouched.
        outcome_section: OutcomeSection | None = None
        outcome_error: str | None = None
        try:
            outcome_section = await _lot_outcomes(conn, as_of)
        except Exception as exc:
            outcome_error = f"outcome section could not run: {exc}"

        # Sequential on the same connection — never asyncio.gather (asyncpg #56).
        deltas = await load_book_delta(conn, as_of)

    computed_at = datetime.now(UTC)
    # Sequential on one asyncpg connection — never asyncio.gather here
    # (MagicStack/asyncpg #56/#258). See docs/product/daily-brief-v2.md §2.1.
    prices_stale = latest_price_date is None or (as_of - latest_price_date).days > 5
    sections = assemble_sections(
        latest_price_date=latest_price_date,
        prices_stale=prices_stale,
        job_failures=job_failures,
        discipline_findings=discipline_findings,
        outcome_section=outcome_section,
        outcome_error=outcome_error,
        regulatory_hits=regulatory_hits,
        news_items=news_items,
        news_status=str(news_status),
        news_error=news_error,
        portfolio_section=portfolio_section,
        computed_at=computed_at,
        data_as_of=data_as_of,
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
        outcome_section=outcome_section,
        outcome_error=outcome_error,
        latest_price_date=latest_price_date,
        data_as_of=data_as_of,
        sections=sections,
        deltas=deltas,
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


def _problem_message(row: asyncpg.Record) -> str:
    """The human line for one job problem.

    Both kinds are phrased here rather than half in SQL: the query supplies facts
    (``age_hours``) and this layer supplies prose, so reworded copy never means
    editing a query. A failed run's text is the exception the job itself raised,
    bounded because it is free text from an upstream library.

    It is not redacted here, and must not start being. Only two modules write
    ``job_runs.error_message`` — ``JobMonitor`` and ``fallback_email`` — and every
    value they store is either a fixed literal or has already been through
    ``asxos/redaction.py`` (``fallback_email`` since this window began carrying its
    rows out to the email). A credential reaching this string therefore means a
    *writer* was missed, and scrubbing a second time here would hide precisely
    that signal.
    """
    if row["kind"] == JobProblemKind.STUCK:
        # started_at, not as_of. as_of is the job's DATA date — snapshot_portfolio
        # anchors it to the latest complete trading day — so quoting it here
        # produced a start date that contradicted the age beside it.
        started: date = row["started_at"].date()
        return (
            f"started {started.isoformat()} and has never reported "
            f"— running {row['age_hours']}h"
        )
    # Declared, not inferred: asyncpg hands back Any, and the query's COALESCE is
    # the only thing keeping this off None.
    raised: str = row["error_message"]
    return raised[:200]


async def _job_failures(conn: asyncpg.Connection, as_of: date) -> list[JobFailure]:
    """Operational problems this brief must surface.

    Why the filter is a wall-clock window and not ``as_of = $1``. In
    ``.github/workflows/daily-brief.yml`` the "Score macro theses", "Check AU
    positions" and "Check thesis invalidations" steps all run *after* "Compose and
    send brief" — deliberately, so a failure there cannot cost the brief — and
    ``check_cron_health`` runs in the separate 22:00 ``pipeline-health.yml``. Every
    one of those writes a row stamped with that day's ``as_of``, *after* that day's
    brief has already composed. An ``as_of = $1`` filter therefore could not see
    them on any day: today's rows do not exist yet, and tomorrow's brief asks for a
    different ``as_of``. The banner was structurally empty rather than merely quiet.

    Measured 2026-08-18 against production: ``check_cron_health`` failed on 08-16
    and 08-17, both naming a stuck ``sync_financial_statements``, and neither
    reached the email. The watchdog worked; the messenger did not.

    The window is anchored on ``as_of`` rather than ``now()`` so that composing a
    past date replays exactly what that morning should have said.

    Why the lower bound is *derived* and not ``as_of - 1 day``. The brief composes
    Sun–Thu only (``daily-brief.yml``, ``cron: "30 20 * * 0-4"``). A fixed one-day
    lookback therefore covers nothing between Thursday's compose and Saturday
    midnight — a 27-hour hole every week, which silently dropped Friday's
    ``backup_irreplaceable`` failure. That is the pg_dump protecting ``theses``,
    ``holding_lots`` and the tax positions, and a backup that stops quietly is the
    highest-consequence silent failure in this system. So the bound is the previous
    successful ``compose_brief``, floored at seven days: it adapts to the real
    cadence, it makes the banner's heading ("since the previous brief") true rather
    than aspirational, and it stops double-reporting the same failure on two
    consecutive weekdays.

    Two clamps bracket that derivation. Seven days is the far edge, so a long
    compose outage cannot make one morning's banner replay a month of history. And
    when no successful ``compose_brief`` exists at all — a fresh database, or a
    replay of a date before the first send — the ``COALESCE`` falls back to
    ``as_of - 1 day``, the old fixed window, so the degenerate case opens with one
    day of history rather than the seven-day maximum.

    A ``running`` row that never reported is included as a distinct kind: on a
    ``status = 'failure'`` filter it is indistinguishable from a healthy job, and
    it is the more dangerous state — nothing failed, so nothing alerts.

    Every boundary is explicitly ``timestamptz`` at UTC. ``$1::date ± INTERVAL``
    alone yields ``timestamp without time zone``, which Postgres compares to
    ``finished_at`` by converting through the session ``TimeZone`` GUC. Setting
    the database or role timezone to ``Australia/Sydney`` would slide this window
    off the 20:30–22:30 UTC pipeline it exists to cover, with no error and no
    failing test.

    That is now prevented rather than merely documented: ``asxos/db.py::init_pool``
    pins ``server_settings={"timezone": "UTC"}`` on every pooled connection
    (2026-08-23), so this window's premise is enforced at connection time instead
    of resting on nobody having run ``ALTER ROLE ... SET timezone``. If that pin
    is ever removed, this analysis becomes live again.
    """
    rows = await conn.fetch(
        """
        WITH bounds AS (
            SELECT
                (($1::date + INTERVAL '1 day') AT TIME ZONE 'UTC') AS upper_bound,
                GREATEST(
                    COALESCE(
                        (SELECT max(prior.finished_at)
                           FROM job_runs AS prior
                          WHERE prior.job_name = 'compose_brief'
                            AND prior.status   = 'success'
                            AND prior.finished_at
                                < (($1::date + INTERVAL '1 day') AT TIME ZONE 'UTC')),
                        (($1::date - INTERVAL '1 day') AT TIME ZONE 'UTC')
                    ),
                    (($1::date - INTERVAL '7 days') AT TIME ZONE 'UTC')
                ) AS lower_bound
        )
        SELECT * FROM (
            SELECT j.job_name,
                   j.as_of,
                   j.started_at,
                   COALESCE(j.error_message, '') AS error_message,
                   'failure'                     AS kind,
                   NULL::bigint                  AS age_hours
            FROM job_runs AS j, bounds AS b
            WHERE j.status = 'failure'
              AND j.finished_at >= b.lower_bound
              AND j.finished_at <  b.upper_bound

            UNION ALL

            SELECT j.job_name,
                   j.as_of,
                   j.started_at,
                   ''      AS error_message,
                   'stuck' AS kind,
                   -- LEAST(now(), upper_bound): for today's brief the age is
                   -- measured to now, which is ~3h before midnight — the upper
                   -- bound alone overstated every age. For a replayed past date
                   -- now() is later than the bound, so the bound wins and the
                   -- replay stays deterministic.
                   FLOOR(
                       EXTRACT(
                           EPOCH FROM (LEAST(now(), b.upper_bound) - j.started_at)
                       ) / 3600
                   )::bigint AS age_hours
            FROM job_runs AS j, bounds AS b
            WHERE j.status = 'running'
              AND j.finished_at IS NULL
              -- The 2 hours must not be tightened independently: JobMonitor's
              -- stale-row heal (asxos/jobs/utils/job_monitor.py) and
              -- check_cron_health's watchdog use the same window, and a shorter
              -- one here would report rows those two still consider live.
              AND j.started_at < b.upper_bound - INTERVAL '2 hours'
        ) AS problems
        -- DESC so 'stuck' sorts above 'failure'. A job that never reported is
        -- the more dangerous state — nothing failed, so nothing else alerts —
        -- and it should not sit below a list of ordinary failures.
        ORDER BY kind DESC, job_name
        """,
        as_of,
    )
    return [
        JobFailure(
            job_name=r["job_name"],
            as_of=r["as_of"],
            error_message=_problem_message(r),
            kind=JobProblemKind(r["kind"]),
        )
        for r in rows
    ]


async def _news_section(conn: asyncpg.Connection, as_of: date) -> tuple[list[NewsItem], NewsStatus]:
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


async def _portfolio_section(conn: asyncpg.Connection, as_of: date) -> PortfolioSection | None:
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

    ``last_answering_revision_at`` is the scoped per-thesis
    ``MAX(thesis_revisions.revised_at)`` the loader's query derives (NULL when
    the thesis carries no answering revision) — it feeds only the data-sanity
    escalation check.
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
            last_answering_revision_at=(
                r["last_answering_revision_at"].date()
                if r["last_answering_revision_at"] is not None
                else None
            ),
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


async def _discipline_findings(conn: asyncpg.Connection, as_of: date) -> list[DisciplineFinding]:
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

    # `watching` rows are fetched ONLY for the data-sanity escalation pass
    # (James's 2026-07-16 CBA ruling — the live worked example is a `watching`
    # thesis a stale ladder would otherwise never surface for); every other
    # check still runs on active theses only, preserving the PR2a behaviour.
    #
    # `last_answering_revision_at` is the "was this red ever answered?" anchor,
    # derived from the existing append-only log with no schema change. The
    # `revision_type` filter is load-bearing, not tidiness: taking MAX over ALL
    # revisions would let an unrelated edit (`--tax-notes`, `--conviction`, an
    # appended report section) reset the clock without touching the ladder, and
    # for a `watching` row that means total silence — the base data_sanity red
    # never runs there. Restricting to types that plausibly ANSWER a ladder red
    # makes `data_sanity_escalation`'s docstring claim true by construction.
    # `entered` is included because `enter_thesis()` hard-fails without a target
    # (`theses/service.py`), so entering IS an act of looking at the ladder — and
    # it resets `revisit_due_at` to the same 30-day cadence this check is
    # calibrated against. Omitting it made a thesis entered yesterday report
    # "no answering revision for 193d", which is the over-escalation direction.
    #
    # `expired` is DEAD: no code path writes that `revision_type` — `asx thesis
    # revise --status expired` (the verb this message emits) writes
    # `status_change`. Listed only so a future writer of it is already covered.
    # `exited`/`exited_by_stop`/`exited_by_target` cannot appear under the status
    # filter below; all three are listed together so a widened filter stays
    # correct, rather than the earlier set which listed one and omitted two.
    #
    # `governance_status = 'approved'` is a security boundary, not a
    # convenience: without it, agent-authored `pending_review` theses would
    # reach the brief unreviewed. Both filters are pinned by a test on the
    # query text.
    thesis_rows = await conn.fetch(
        """
        SELECT symbol, status, revisit_due_at, opened_at, timeline_days,
               actual_entry_price, target_price, stop_price, conviction_level,
               (SELECT MAX(r.revised_at)
                  FROM thesis_revisions r
                 WHERE r.thesis_id = theses.thesis_id
                   AND r.revision_type IN ('target_adjusted', 'reviewed_no_change',
                                           'status_change', 'entered', 'expired',
                                           'exited', 'exited_by_stop',
                                           'exited_by_target')
               ) AS last_answering_revision_at
        FROM theses
        WHERE status IN ('watching', 'active')
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

    # Two input sets, deliberately different in scope — the names carry that,
    # because a comment would not survive the next refactor. `active_inputs`
    # feeds the full check battery (active theses only, exactly as PR2a);
    # `all_inputs` is watching + active and feeds ONLY the escalation pass.
    # Running the battery over `all_inputs` would emit revisit/timeline/stop
    # findings for uninvested watchlist rows.
    all_inputs = _thesis_discipline_inputs(thesis_rows, prices)
    active_inputs = tuple(
        ti for row, ti in zip(thesis_rows, all_inputs, strict=True) if row["status"] == "active"
    )
    holdings = _holding_weights(holding_rows, prices, fx_rate)

    port_input = PortfolioDisciplineInput(holdings=holdings)
    findings = evaluate_discipline(active_inputs, port_input, as_of)
    # Data-sanity escalation (the 2026-07-16 ruling's unbuilt half): a detached
    # ladder carrying no answering revision past one revisit cadence escalates,
    # naming the exact CLI verbs. Watching + active rows, same loud-error
    # isolation idiom as the unrealised_return loop below.
    #
    # `watchlist_only` is stamped HERE because this is the only place that holds
    # both the finding and the row's status. It keeps an uninvested watchlist
    # row from counting as evidence that a HOLDING was checked
    # (`BriefData.review`) — the finding is still displayed in full.
    for row, ti in zip(thesis_rows, all_inputs, strict=True):
        watchlist_only = row["status"] != "active"
        try:
            esc = data_sanity_escalation(ti, as_of)
        except Exception as exc:  # isolate a malformed thesis, fail loud (#10)
            findings.append(
                DisciplineFinding(
                    check="data_sanity_escalation",
                    level=DisciplineLevel.error,
                    message=(f"⚠ data_sanity_escalation could not run for {ti.symbol}: {exc}"),
                    symbol=ti.symbol,
                    watchlist_only=watchlist_only,
                )
            )
            continue
        if esc is not None:
            findings.append(replace(esc, watchlist_only=watchlist_only))
    # Per-holding unrealised return (native, broker-matching) — appended here as a
    # display fact (like the CGT-boundary line) so evaluate_discipline() stays
    # quiet-by-default. Native entry vs current price only; no cost base, no
    # benchmark, no Model A (R10 / rule #11 safe). Each is isolated with the same
    # loud-error idiom the per-thesis checks use, so a single malformed thesis
    # surfaces one error line rather than collapsing the whole section
    # (security-engineer review, 2026-07-19).
    for ti in active_inputs:
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


def _resolve_anchor(rows: list[asyncpg.Record], target: date) -> BenchmarkAnchor | None:
    """The benchmark level in effect at ``target`` — latest row on or before it.

    ``rows`` must be ascending by ``as_of`` and carry only non-NULL
    ``benchmark_tr_level``. Returns ``None`` when the series does not reach back
    that far, which the outcome layer reports as `unavailable_no_series` rather
    than reaching forward to a later level (that would measure a window the lot
    never had).

    ``is_proxy`` is derived from ``trailing_div_yield_pct`` being non-NULL:
    `jobs/snapshot_portfolio.py:274-290` writes the assumed yield on the
    approximation path and leaves it NULL when `benchmark_tr_level` is the real
    accumulation index. That column is the only record of which path ran, and
    governor ruling F1 turns on exactly that distinction.
    """
    chosen: asyncpg.Record | None = None
    for row in rows:
        if row["as_of"] <= target:
            chosen = row
        else:
            break
    if chosen is None:
        return None
    return BenchmarkAnchor(
        as_of=chosen["as_of"],
        level=Decimal(str(chosen["benchmark_tr_level"])),
        is_proxy=chosen["trailing_div_yield_pct"] is not None,
    )


async def _lot_outcomes(conn: asyncpg.Connection, as_of: date) -> OutcomeSection | None:
    """Section 8 loader — per-open-lot return, benchmark return, alpha.

    This is the first production consumer of `asxos.domain.benchmark.returns`
    and the only code behind the north star's "benchmark-relative" claim
    (`docs/product/north-star.md:40`). All arithmetic lives in
    `asxos.domain.benchmark.outcome`; this function only fetches facts.

    **It never reads `portfolio_daily_snapshots.capital_aud`, and it must never
    start** (why: `asxos/domain/brief/collectors/wealth_state.py:101-108`). The
    portfolio leg is anchored on `holding_lots.acquired_at` / `cost_base_normal`,
    which no deposit or withdrawal can move. `tests/test_brief_outcome.py`
    asserts `capital_aud` appears in no query this path issues, and pins the
    snapshot query's projection so a `SELECT *` cannot re-expose it.

    Currency (R10, `.claude/rules/portfolio-conventions.md` §"`cost_base_normal`
    currency"): `cost_base_normal` is already AUD; the market leg is converted
    forward with an explicit `fx_rates` AUDUSD step. Nothing here divides a cost
    base by a quantity.

    Sleeves (governor ruling F2): benchmark levels are fetched and attached for
    ASX lots only, so a global lot cannot reach the ASX comparison even before
    the outcome layer's own sleeve check refuses it.

    Gated on ``ASXOS_PERSONAL_USE=1`` only — parity with `_discipline_findings`,
    which `.github/workflows/daily-brief.yml` already sets. Deliberately NOT
    gated on ``ASXOS_PORTFOLIO_BRIEF_ENABLED`` (that gates the allocator's trade
    suggestions) and not on ``ASXOS_V2_BRIEF_ENABLED`` (the V2 tree is dark and
    deferred to Stage 6; this section ships on V1 precisely so it does not wait
    on that flag).
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        return None

    # `holding_lots`, not the `current_holdings` view — for an EXPLICIT
    # `disposed_at IS NULL`, matching `jobs/snapshot_portfolio.py`.
    #
    # CORRECTION (2026-08-17): an earlier version of this comment claimed the
    # view "does not expose cost_base_normal". That is FALSE — the view selects
    # it (`migrations/0001_initial.sql`, the `current_holdings` definition), and
    # no later migration redefines it. The claim was copied from a pre-existing
    # wrong comment in `snapshot_portfolio.py` and was pinned into a test name
    # before review caught it. Either source is correct to read; the reason is
    # that the open-lot filter should be visible at the query, not implied by a
    # view definition three migrations away.
    lot_rows = await conn.fetch(
        """
        SELECT id, symbol, quantity, acquired_at, cost_base_normal
        FROM holding_lots
        WHERE disposed_at IS NULL
        ORDER BY acquired_at, symbol, id
        """
    )
    if not lot_rows:
        return build_outcome_section([], as_of)

    # `dt` is selected, not just `close`. Without it the outcome layer cannot tell
    # a close from yesterday from one from three months ago — a halt, a delisting
    # or a per-symbol sync gap would silently produce a lot return measured to an
    # old close against a benchmark measured to `as_of`, i.e. an alpha spanning
    # two different windows. The date is what makes that checkable.
    symbols = sorted({r["symbol"] for r in lot_rows})
    price_rows = await conn.fetch(
        """
        SELECT DISTINCT ON (symbol) symbol, dt, close
        FROM prices
        WHERE symbol = ANY($1) AND dt <= $2
        ORDER BY symbol, dt DESC
        """,
        symbols,
        as_of,
    )
    closes = {
        r["symbol"]: Observation(as_of=r["dt"], value=Decimal(str(r["close"]))) for r in price_rows
    }

    # AUDUSD from `fx_rates` — the primary source `jobs/snapshot_portfolio.py`
    # itself reads, rather than the snapshot's derived copy. Fetched only when a
    # foreign lot is open, so an all-ASX portfolio issues no FX query at all.
    # `dt` again: the rate is daily (sync_prices Phase 3 pulls AUDUSD.FOREX
    # daily), so a rate more than a few days old means the FX feed has stalled,
    # and valuing a USD lot at a stalled rate misstates it in AUD.
    fx_audusd: Observation | None = None
    if any(is_foreign_symbol(s) for s in symbols):
        fx_row = await conn.fetchrow(
            """
            SELECT dt, rate FROM fx_rates
            WHERE pair = 'AUDUSD' AND dt <= $1
            ORDER BY dt DESC
            LIMIT 1
            """,
            as_of,
        )
        if fx_row is not None:
            fx_audusd = Observation(as_of=fx_row["dt"], value=Decimal(str(fx_row["rate"])))

    # Benchmark levels, ASX lots only (F2). The window starts MAX_ANCHOR_LAG_DAYS
    # before the earliest ASX acquisition — the same tolerance the outcome layer
    # applies when deciding whether an anchor still describes the lot's window.
    # NOTE: this SELECT deliberately does not list `capital_aud`. See the
    # docstring; the omission is the fix, not an oversight.
    asx_acquisitions = [r["acquired_at"] for r in lot_rows if sleeve_for(r["symbol"]) is Sleeve.asx]
    benchmark_rows: list[asyncpg.Record] = []
    if asx_acquisitions:
        benchmark_rows = list(
            await conn.fetch(
                """
                SELECT as_of, benchmark_tr_level, trailing_div_yield_pct
                FROM portfolio_daily_snapshots
                WHERE as_of <= $1
                  AND as_of >= $2
                  AND benchmark_tr_level IS NOT NULL
                ORDER BY as_of
                """,
                as_of,
                min(asx_acquisitions) - timedelta(days=MAX_ANCHOR_LAG_DAYS),
            )
        )
    benchmark_end = _resolve_anchor(benchmark_rows, as_of)

    lots: list[LotInput] = []
    for r in lot_rows:
        is_asx = sleeve_for(r["symbol"]) is Sleeve.asx
        lots.append(
            LotInput(
                lot_id=r["id"],
                symbol=r["symbol"],
                quantity=Decimal(str(r["quantity"])),
                acquired_at=r["acquired_at"],
                cost_base_aud=Decimal(str(r["cost_base_normal"])),
                close=closes.get(r["symbol"]),
                fx_audusd=fx_audusd,
                benchmark_start=(
                    _resolve_anchor(benchmark_rows, r["acquired_at"]) if is_asx else None
                ),
                benchmark_end=benchmark_end if is_asx else None,
            )
        )
    return build_outcome_section(lots, as_of)


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


def render_detail_html(data: BriefData) -> str:
    """Render the full-tables detail page. Same StrictUndefined contract as render_html."""
    return brief_env().get_template("brief_detail.html.j2").render(d=data)


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
