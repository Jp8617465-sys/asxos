"""Decision-case builder — Slice 1 spine, generalised in Slice 2.5/2/3 (Wave 5).

`build_decision_case()` composes one real `DecisionCase` for ANY approved
thesis; `build_cba_decision_case()` is the Slice 1 entry point kept as a thin
wrapper scoped to CBA.AU (`thesis_id=1`). With a `ChallengeContext` the
Slice 2.5 challenger (`decision_engine.challenge`) runs the ratified Layer-1
rules pro-forma and the Slice 2 sizer (`decision_engine.sizer`) derives an
indicative `SizeRange`; a Stage 3 `CandidateSnapshot` contributes its cited
evidence. Without a context the case is an honest `abstain` whose blocking
finding says the register rules did not run.

Slice 1 record, retained:

Composes the full contract chain (`EvidencePacket -> ThesisVersion ->
ChallengeResult -> PortfolioAssessment -> DecisionPacket -> DecisionCase`,
`asxos/domain/decision_engine/types.py`, FROZEN) from real data:

- Fundamentals evidence mirrors `asxos/domain/results_review/pit_db.py`'s
  query construction (its `SQL_INCOME` constant, reused verbatim here) and
  its `known_at` derivation (`derive_statement_known_at`, the same public
  function `pit_db.py` itself calls) — the source hierarchy and
  knowledge-date rule this mission was told not to re-derive. It does NOT
  call `pit_db.fetch_pit_snapshot()`/`build_pit_case()`: those functions'
  `EvidencePacket` expiry depends on a *historical* `prices.dt`-observed
  `TradingSessionCalendar` (G6), which has no sessions to find after a live
  `knowledge_cutoff` (see `calendar.py`'s module docstring) — issuing the
  same bound `SQL_INCOME` query directly while supplying this module's own
  forward calendar for expiry avoids that dependency without re-deriving
  the source hierarchy or the `known_at` rule itself.
- Thesis-narrative evidence comes from the real `theses` row's
  `thesis_text`, `invalidation_conditions`, and price plan
  (`entry_band_lower/upper`, `stop_price`, `target_price`) — there is no
  existing mapping from these columns to `EvidenceItem.evidence_type`, so
  the choice is made and documented at each call site below.
- The trading calendar is `calendar.py`'s forward weekday stand-in — NOT an
  ASX exchange calendar (see that module's docstring); this packet is
  forced into `abstain` regardless, so no action-state deadline ever rests
  on it.
- `TaxAssessmentReference` reuses
  `results_review/contracts.py::unresolved_tax_assessment_reference()`
  rather than calling `tax_view_individual()` directly: that function's
  only real caller today hardcodes empty dividends/realised-gains (G12),
  so calling it here would produce the same unearned-looking `readiness`
  through more code, not a more honest one. `unresolved_tax_assessment_reference`
  is the single producer this codebase already ships for "no real
  dividend/gains feed exists yet, so readiness is honestly unknown, not
  fabricated" — reusing it directly says exactly that with no new surface.
- Before Wave 5 the `ChallengeResult` was a permanent "no challenger exists"
  blocking finding. The challenger now exists; the no-context path keeps an
  equivalent honest finding ("the register rules did not run") so a case can
  never be presented as challenged when it was not.

Import-isolation (rule #11): this module never reads `signals`,
`signal_outcomes`, `model_versions.prob_up`/`shap_factors`, or any other
Model A surface — it has no reason to and does not import
`asxos.domain.models.*` at all.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from pydantic import Field

from asxos.domain.decision_engine.calendar import build_forward_weekday_calendar
from asxos.domain.decision_engine.challenge import (
    ChallengeInput,
    DispositionLog,
    PortfolioState,
    challenge_thesis,
)
from asxos.domain.decision_engine.challenge.rules import PRICE_STALE_MATERIAL_DAYS
from asxos.domain.decision_engine.sizer import (
    ZERO_SIZE,
    ProposedPosition,
    SizingPolicy,
    VolInput,
    headroom_max_pct,
    size_from_challenge,
)
from asxos.domain.decision_engine.types import (
    UNIVERSAL_CONSTRAINTS,
    ChallengeFinding,
    ChallengeResult,
    ConstraintResult,
    Contract,
    DecisionCase,
    DecisionPacket,
    EvidenceItem,
    EvidencePacket,
    ManifestEntry,
    PortfolioAssessment,
    RecommendationState,
    Scenario,
    ThesisVersion,
    UpstreamArtifactHashes,
    default_packet_expiry,
)
from asxos.domain.results_review.contracts import (
    derive_statement_known_at,
    unresolved_tax_assessment_reference,
)
from asxos.domain.results_review.pit_db import (
    SQL_INCOME,
    FetchConn,
    assert_sql_admissible,
    validate_symbol,
)
from asxos.domain.themes.candidates.measures import assert_measure_sql_admissible
from asxos.domain.themes.candidates.types import CandidateSnapshot
from asxos.domain.theses.service import get_thesis

#: Not in pit_db.py's admissible-table SQL constants (it has no "latest
#: period" query) — mirrors its query-construction style: SELECT-only,
#: bound parameters, an admissible table (`rs_financial_statements`).
SQL_YEARLY_INCOME_PERIODS: Final[str] = (
    "SELECT symbol, period_end, period_type, statement_type, filing_date, "
    "report_date, currency, total_revenue, net_income "
    "FROM rs_financial_statements "
    "WHERE symbol = $1 AND period_end <= $2 AND period_type = 'yearly' "
    "AND statement_type = 'income' ORDER BY period_end DESC"
)

_PCT_QUANT: Final[Decimal] = Decimal("0.000001")
_DEFAULT_THESIS_ID: Final[int] = 1
_EXPECTED_SYMBOL: Final[str] = "CBA.AU"


def _pct(value: Decimal) -> Decimal:
    return value.quantize(_PCT_QUANT, rounding=ROUND_HALF_EVEN)


def _coerce_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _income_known_at(
    row: object, *, period_end: date, as_of: date, cutoff: datetime
) -> datetime | None:
    """Mirror of `pit_db.py`'s private `_known_at_for_income` + its post-hoc
    `current_known > cutoff` drop — reuses the same public
    `derive_statement_known_at` rule (G8) rather than re-deriving it.

    The row is accepted on the strength of a callable ``.get``, not on
    ``isinstance(row, Mapping)``. **`asyncpg.Record` is not a `Mapping`** — it
    supports ``.get()`` and item access but is not registered on the ABC — so a
    `Mapping` test rejected every row a real connection returns, and this
    function returned `None` for all of them. The caller reads that as "no
    admissible yearly income row" and `build_decision_case` raised, which is why
    Stage 4 could never run against the live database. Every test fed it `dict`
    fixtures, so CI was green throughout (found by the first live end-to-end run,
    2026-09-07). The duck-typed check keeps the fail-closed intent — an object
    with no ``.get`` is still refused — without coupling this module to asyncpg.
    """
    getter = getattr(row, "get", None)
    if not callable(getter):
        return None
    report_d = _coerce_date(getter("report_date"))
    filing_d = _coerce_date(getter("filing_date"))
    known_at = derive_statement_known_at(period_end, report_d, filing_d, as_of)
    if known_at > cutoff:
        return None
    return known_at


SQL_LAST_CLOSE: Final[str] = (
    "SELECT dt, close FROM prices WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT 1"
)
assert_measure_sql_admissible(SQL_LAST_CLOSE)


class ChallengeContext(Contract):
    """What the challenge layer and the sizer need beyond the thesis row: the
    caller's measured portfolio state and sizing policy, the proposed name's
    annualised vol (and its peers'), and any diagnostics the caller measured.
    Nothing here is inferred; an absent measurement is reported as absent."""

    portfolio_state: PortfolioState
    sizing: SizingPolicy
    proposed_annualised_vol: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    peers: tuple[VolInput, ...] = ()
    proposed_weight_pct: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    pairwise_correlation_max: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"), max_digits=18, decimal_places=6)
    valuation_percentile: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    spread_bps: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=18, decimal_places=6)
    adv_trend_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    base_rate_evidence_ids: tuple[str, ...] = ()
    dispositions: DispositionLog = DispositionLog()


def _candidate_measure(candidate: CandidateSnapshot | None, key: str) -> str | None:
    if candidate is None:
        return None
    value = candidate.measures.get(key)
    return None if value is None else str(value)


async def build_decision_case(
    conn: FetchConn,
    *,
    cutoff: datetime,
    thesis_id: int,
    candidate: CandidateSnapshot | None = None,
    context: ChallengeContext | None = None,
    expected_symbol: str | None = None,
) -> DecisionCase:
    """Compose one real `DecisionCase` for any approved thesis.

    `cutoff` is the caller-supplied `knowledge_cutoff` (UTC, enforced by the
    contracts) — never "now", so the packet stays reproducible.

    `candidate` (Stage 3, `asx candidates build`) contributes its cited
    evidence items and its measured sector / liquidity to the challenge.
    `context` supplies the portfolio state and sizing policy; without it the
    Layer-1 register rules cannot run pro-forma and the case is an honest
    `abstain` with a blocking finding saying exactly that. With it, the
    Slice 2.5 challenger runs and the Slice 2 sizer produces an INDICATIVE
    range — which the packet still carries as zero, because no tax feed
    exists yet (G12) and a non-action state must carry a zero range.
    """
    thesis = await get_thesis(conn, thesis_id)
    if thesis is None:
        raise ValueError(f"no theses row for thesis_id={thesis_id}")
    if expected_symbol is not None and thesis.symbol != expected_symbol:
        raise ValueError(
            f"builder call is scoped to {expected_symbol}; thesis_id={thesis_id} has symbol={thesis.symbol!r}"
        )
    if thesis.governance_status != "approved":
        raise ValueError(
            f"thesis_id={thesis_id} has governance_status={thesis.governance_status!r}, "
            "not 'approved' — refusing to build a decision case on unapproved content"
        )
    if not thesis.thesis_text or not thesis.thesis_text.strip():
        raise ValueError(f"thesis_id={thesis_id} has no thesis_text to build narrative evidence from")

    symbol = validate_symbol(thesis.symbol)
    display_symbol, exchange = symbol.split(".", 1)
    slug = display_symbol.lower()
    as_of = cutoff.date()
    if candidate is not None:
        if candidate.symbol != symbol:
            raise ValueError(f"candidate {candidate.symbol} is not the thesis symbol {symbol}")
        if candidate.knowledge_cutoff > cutoff:
            raise ValueError("candidate snapshot was built after the requested knowledge cutoff")

    narrative_known_at = thesis.last_revisited_at
    if narrative_known_at.tzinfo is None:
        narrative_known_at = narrative_known_at.replace(tzinfo=UTC)
    if narrative_known_at > cutoff:
        raise ValueError(
            f"thesis_id={thesis_id} was last revisited at {narrative_known_at.isoformat()}, "
            f"after the requested knowledge cutoff {cutoff.isoformat()}"
        )
    narrative_observed_at = narrative_known_at.date()

    calendar = build_forward_weekday_calendar(cutoff)
    items: list[EvidenceItem] = []

    # -- Fundamentals: mirrors pit_db.py's query construction and known_at
    # rule (see module docstring); NOT pit_db.build_pit_case() itself.
    assert_sql_admissible(SQL_YEARLY_INCOME_PERIODS)
    assert_sql_admissible(SQL_INCOME)
    period_rows = await conn.fetch(SQL_YEARLY_INCOME_PERIODS, symbol, as_of)
    # Not `Mapping`: a live `asyncpg.Record` is not one (see `_income_known_at`).
    current_row: object | None = None
    period_end: date | None = None
    current_known: datetime | None = None
    for row in period_rows:
        # Duck-typed, not `isinstance(row, Mapping)`: `asyncpg.Record` supports
        # `.get()` but is not a `Mapping`, so a Mapping test refused every live
        # row (see `_income_known_at`). Guard at first access so a row of the
        # wrong shape is skipped rather than raising `AttributeError`.
        row_get = getattr(row, "get", None)
        if not callable(row_get):
            continue
        candidate_end = _coerce_date(row_get("period_end"))
        if candidate_end is None:
            continue
        candidate_known = _income_known_at(
            row, period_end=candidate_end, as_of=as_of, cutoff=cutoff
        )
        if candidate_known is not None:
            current_row = row
            period_end = candidate_end
            current_known = candidate_known
            break
    if current_row is None or period_end is None or current_known is None:
        raise ValueError(
            f"no admissible yearly income row for {symbol} at knowledge cutoff "
            f"{cutoff.isoformat()}"
        )
    items.append(
        EvidenceItem(
            evidence_id=f"{slug}-income-current",
            evidence_type="fundamental_fact",
            title=f"{symbol} yearly income {period_end.isoformat()}",
            claim=(
                f"Research-store yearly income row for {symbol} period_end "
                f"{period_end.isoformat()} (source_class asxos_pit_record; "
                "not an ASX announcement)."
            ),
            source_uri=f"asxos://rs_financial_statements/{symbol}/{period_end.isoformat()}/yearly/income",
            observed_at=period_end,
            known_at=current_known,
            evidence_tier="verified",
            data_mode="real",
        )
    )

    prior_end = date(period_end.year - 1, period_end.month, period_end.day)
    prior_row = await conn.fetchrow(SQL_INCOME, symbol, prior_end, "yearly")
    prior_known = _income_known_at(prior_row, period_end=prior_end, as_of=as_of, cutoff=cutoff)
    if prior_known is not None:
        items.append(
            EvidenceItem(
                evidence_id=f"{slug}-income-prior",
                evidence_type="fundamental_fact",
                title=f"{symbol} yearly income {prior_end.isoformat()}",
                claim=f"Prior-year research-store income row for {symbol} {prior_end.isoformat()}.",
                source_uri=f"asxos://rs_financial_statements/{symbol}/{prior_end.isoformat()}/yearly/income",
                observed_at=prior_end,
                known_at=prior_known,
                evidence_tier="verified",
                data_mode="real",
            )
        )

    # -- Thesis narrative: theme_fact (closest of the five evidence types; no
    # dedicated thesis_fact exists in types.py).
    items.append(
        EvidenceItem(
            evidence_id=f"{slug}-thesis-narrative",
            evidence_type="theme_fact",
            title=f"{symbol} thesis narrative",
            claim=thesis.thesis_text,
            source_uri=f"asxos://theses/{thesis_id}",
            observed_at=narrative_observed_at,
            known_at=narrative_known_at,
            evidence_tier="verified",
            data_mode="real",
        )
    )

    # -- Invalidation conditions: portfolio_fact (review/exit triggers).
    if thesis.invalidation_conditions:
        conditions_claim = "; ".join(
            f"{ic.condition} (status={ic.status})" + (f" — {ic.note}" if ic.note else "")
            for ic in thesis.invalidation_conditions
        )
        items.append(
            EvidenceItem(
                evidence_id=f"{slug}-thesis-invalidation-conditions",
                evidence_type="portfolio_fact",
                title=f"{symbol} thesis invalidation conditions",
                claim=conditions_claim,
                source_uri=f"asxos://theses/{thesis_id}/invalidation_conditions",
                observed_at=narrative_observed_at,
                known_at=narrative_known_at,
                evidence_tier="verified",
                data_mode="real",
            )
        )
        falsifiers = tuple(f"{ic.condition} (status={ic.status})" for ic in thesis.invalidation_conditions)
    else:
        falsifiers = (
            "No invalidation_conditions are on file for this thesis; none can be honestly cited as a falsifier.",
        )

    # -- Price plan: market_fact. Hard-fails if absent rather than inventing
    # scenario numbers with no price plan behind them.
    if (
        thesis.entry_band_lower is None
        or thesis.entry_band_upper is None
        or thesis.stop_price is None
        or thesis.target_price is None
    ) and thesis.actual_entry_price is None:
        raise ValueError(
            f"thesis_id={thesis_id} has no entry/target/stop price plan on file — "
            "cannot honestly derive bull/bear scenario returns"
        )
    reference_price = thesis.actual_entry_price
    if reference_price is None:
        assert thesis.entry_band_lower is not None and thesis.entry_band_upper is not None
        reference_price = (thesis.entry_band_lower + thesis.entry_band_upper) / Decimal("2")
    if thesis.stop_price is None or thesis.target_price is None:
        raise ValueError(
            f"thesis_id={thesis_id} has a reference price but no stop_price/target_price — "
            "cannot honestly derive bull/bear scenario returns"
        )
    items.append(
        EvidenceItem(
            evidence_id=f"{slug}-thesis-price-plan",
            evidence_type="market_fact",
            title=f"{symbol} thesis price plan",
            claim=(
                f"Price plan on file for {symbol}: entry band "
                f"{thesis.entry_band_lower}-{thesis.entry_band_upper}, "
                f"stop {thesis.stop_price}, target {thesis.target_price}, "
                f"actual_entry_price {thesis.actual_entry_price}."
            ),
            source_uri=f"asxos://theses/{thesis_id}/price_plan",
            observed_at=narrative_observed_at,
            known_at=narrative_known_at,
            evidence_tier="verified",
            data_mode="real",
        )
    )

    # -- Stage 3 candidate evidence rides along unchanged (same EvidenceItem contract).
    if candidate is not None:
        present = {item.evidence_id for item in items}
        items.extend(e for e in candidate.evidence if e.evidence_id not in present)

    # -- Last close at the cutoff (only when a challenge is to be run: the
    # legacy no-context path issues no price query).
    last_close: Decimal | None = None
    last_close_dt: date | None = None
    price_evidence_id: str | None = None
    if context is not None:
        # -- The live book itself is evidence. Five register rules cite
        # `x.portfolio.evidence_id` (challenge/rules.py:213,235,254,266,328), and
        # `DecisionCase` refuses a case that "cites evidence outside the frozen
        # packet" (types.py:610). Without this item every `--context` build failed
        # that validator, so the live-book path had never produced a case — the
        # tests supply a context whose state carries an id the fixture packet
        # already contains — hence the membership check, which mirrors the
        # candidate-evidence merge below. Found by the first live run, 2026-09-07.
        pstate = context.portfolio_state
        if pstate.evidence_id not in {item.evidence_id for item in items}:
            items.append(
                EvidenceItem(
                    evidence_id=pstate.evidence_id,
                    evidence_type="portfolio_fact",
                    title=f"Portfolio state at {as_of.isoformat()}",
                    claim=(
                        f"Pre-trade book at {as_of.isoformat()}: capital "
                        f"{pstate.capital_aud} AUD, cash "
                        # #228: an evidence claim states what was observed. "cash None%"
                        # would read as a rendering bug; "not measured" is the fact.
                        f"{'not measured' if pstate.cash_pct is None else f'{pstate.cash_pct}%'}"
                        f", gross exposure "
                        f"{pstate.gross_exposure_pct}%, borrowing {pstate.borrowing_aud} AUD, "
                        f"{len(pstate.position_weights_pct)} position(s) across "
                        f"{len(pstate.sector_weights_pct)} sector(s)."
                    ),
                    source_uri=f"asxos://portfolio_daily_snapshots/{as_of.isoformat()}",
                    observed_at=as_of,
                    known_at=cutoff,
                    evidence_tier="verified",
                    data_mode="real",
                )
            )
        price_row = await conn.fetchrow(SQL_LAST_CLOSE, symbol, as_of)
        if price_row is not None and price_row["close"] is not None:
            last_close = Decimal(str(price_row["close"]))
            last_close_dt = _coerce_date(price_row["dt"])
            price_evidence_id = f"{slug}-last-close"
            assert last_close_dt is not None
            items.append(
                EvidenceItem(
                    evidence_id=price_evidence_id,
                    evidence_type="market_fact",
                    title=f"{symbol} last close {last_close} on {last_close_dt.isoformat()}",
                    claim=f"prices row symbol={symbol} dt={last_close_dt.isoformat()} close={last_close}.",
                    source_uri=f"asxos://prices/{symbol}/{last_close_dt.isoformat()}",
                    observed_at=last_close_dt,
                    known_at=cutoff,
                    evidence_tier="verified",
                    data_mode="real",
                )
            )

    evidence_ids = tuple(item.evidence_id for item in items)
    expires_at = default_packet_expiry(cutoff, "abstain", calendar)
    evidence = EvidencePacket(
        evidence_packet_id=f"evp-{slug}-{thesis_id}-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=expires_at,
        data_mode="real",
        created_at=cutoff,
        items=tuple(items),
    )

    bull_return_pct = _pct((thesis.target_price - reference_price) / reference_price * Decimal("100"))
    bear_return_pct = _pct((thesis.stop_price - reference_price) / reference_price * Decimal("100"))
    plan_id = f"{slug}-thesis-price-plan"
    scenarios = (
        Scenario(label="bull", return_pct=bull_return_pct, probability_pct=Decimal("25"),
                 rationale=f"Reaching the recorded target_price of {thesis.target_price} from a reference price of {reference_price}.",
                 evidence_ids=(plan_id,)),
        Scenario(label="base", return_pct=Decimal("0"), probability_pct=Decimal("50"),
                 rationale="No structured base-case target exists on the theses table; treated as unchanged from the reference price.",
                 evidence_ids=(plan_id,)),
        Scenario(label="bear", return_pct=bear_return_pct, probability_pct=Decimal("25"),
                 rationale=f"Falling to the recorded stop_price of {thesis.stop_price} from a reference price of {reference_price}.",
                 evidence_ids=(plan_id,)),
    )

    if thesis.next_earnings_date is not None:
        catalysts = (f"Next scheduled earnings date on file: {thesis.next_earnings_date.date().isoformat()}.",)
    else:
        catalysts = (
            "No structured catalyst calendar exists on the theses table yet; "
            "see the thesis narrative evidence item for the full articulated view.",
        )

    if thesis.timeline_days is None or thesis.timeline_days <= 0:
        raise ValueError(f"thesis_id={thesis_id} has no timeline_days to derive a horizon from")
    horizon_months = max(1, min(120, (thesis.timeline_days + 15) // 30))  # integer arithmetic; no float op on the path
    theme = ", ".join(thesis.themes) if thesis.themes else "No theme_code attached to this thesis"

    thesis_version = ThesisVersion(
        thesis_version_id=f"thv-{slug}-{thesis_id}-{as_of.isoformat()}",
        security_id=symbol,
        symbol=display_symbol,
        exchange=exchange,
        version=1,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        theme=theme,
        investment_question=f"Does the thesis articulated for {symbol} continue to hold?",
        variant_view=(
            "No structured variant-view field exists on the theses table; the full "
            "articulated thesis is captured verbatim in thesis_summary and the "
            f"{slug}-thesis-narrative evidence item."
        ),
        thesis_summary=thesis.thesis_text,
        catalysts=catalysts,
        falsifiers=falsifiers,
        horizon_months=horizon_months,
        scenarios=scenarios,
        evidence_ids=evidence_ids,
    )

    # -- Slice 2.5 challenge + Slice 2 sizer -------------------------------------
    missing: list[str] = ["Real dividend/realised-gains feed for tax readiness (G12)"]
    indicative_size = ZERO_SIZE
    if context is None:
        challenge = ChallengeResult(
            challenge_result_id=f"chr-{slug}-{thesis_id}-{as_of.isoformat()}",
            thesis_version_id=thesis_version.thesis_version_id,
            evidence_packet_id=evidence.evidence_packet_id,
            as_of=as_of,
            knowledge_cutoff=cutoff,
            created_at=cutoff,
            outcome="abstain",
            strongest_bear_case=(
                "No portfolio state was supplied, so the Layer-1 register rules could not run "
                "pro-forma; presenting the thesis as actionable would let the author's own framing "
                "pass unopposed."
            ),
            findings=(
                ChallengeFinding(
                    severity="blocking",
                    finding="The challenge layer (Slice 2.5) was not run: no portfolio state or sizing policy was supplied.",
                    required_response="Supply a measured ChallengeContext and rebuild the case.",
                    evidence_ids=(f"{slug}-thesis-narrative",),
                ),
            ),
            independent_of_author=True,
        )
        missing.append("Portfolio state and sizing policy (ChallengeContext) — the register rules did not run")
        borrowing = Decimal("0")
        freshness: ConstraintResult = ConstraintResult(
            name="decision_evidence_freshness", status="unknown", blocking=True,
            detail="No price was read at the cutoff; evidence recency is only as fresh as the caller-supplied knowledge_cutoff.",
        )
    else:
        sector = _candidate_measure(candidate, "gics_sector") or _candidate_measure(candidate, "factor_sector")
        adv_raw = _candidate_measure(candidate, "median_dollar_volume_60d")
        proposed_weight = context.proposed_weight_pct
        if proposed_weight is None:
            if context.proposed_annualised_vol is not None:
                proposed_weight = headroom_max_pct(
                    ProposedPosition(symbol=symbol, sector=sector, annualised_vol=context.proposed_annualised_vol),
                    context.peers, context.sizing, context.portfolio_state,
                )
            else:
                proposed_weight = Decimal("0")
                missing.append("Annualised volatility for the proposed name — challenged at zero weight, no size derived")
        if context.portfolio_state.cash_pct is None:
            # #228. types.py forbids an action state while missing_or_uncertain_inputs is
            # non-empty, so declaring the gap here is what stops an unmeasured book
            # producing a recommendation.
            missing.append(
                "Authoritative cash balance for the live book — cash_floor not evaluated, "
                "no size derived (#228)"
            )
        x = ChallengeInput(
            symbol=symbol,
            sector=sector,
            as_of=as_of,
            proposed_weight_pct=proposed_weight,
            position_cap_pct=context.sizing.position_cap_pct,
            portfolio=context.portfolio_state,
            last_close=last_close,
            last_close_dt=last_close_dt,
            price_evidence_id=price_evidence_id,
            fundamentals_as_of=period_end,
            fundamentals_evidence_id=f"{slug}-income-current",
            thesis_evidence_id=f"{slug}-thesis-narrative",
            entry_band_lower=thesis.entry_band_lower,
            entry_band_upper=thesis.entry_band_upper,
            target_price=thesis.target_price,
            reference_price=reference_price,
            horizon_months=horizon_months,
            invalidation_conditions=tuple(ic.condition for ic in thesis.invalidation_conditions),
            last_revisited_at=narrative_observed_at,
            revisit_due_at=thesis.revisit_due_at.date() if thesis.revisit_due_at else None,
            base_rate_evidence_ids=context.base_rate_evidence_ids,
            pairwise_correlation_max=context.pairwise_correlation_max,
            valuation_percentile=context.valuation_percentile,
            adv_aud=Decimal(adv_raw) if adv_raw is not None else None,
            adv_trend_pct=context.adv_trend_pct,
            spread_bps=context.spread_bps,
        )
        challenge = challenge_thesis(
            x,
            thesis_version_id=thesis_version.thesis_version_id,
            evidence_packet_id=evidence.evidence_packet_id,
            knowledge_cutoff=cutoff,
            log=context.dispositions,
        )
        challenge = challenge.model_copy(
            update={"challenge_result_id": f"chr-{slug}-{thesis_id}-{as_of.isoformat()}", "content_hash": ""}
        )
        challenge = ChallengeResult.model_validate(challenge.model_dump())
        if context.proposed_annualised_vol is not None:
            indicative_size = size_from_challenge(
                challenge,
                proposed=ProposedPosition(symbol=symbol, sector=sector, annualised_vol=context.proposed_annualised_vol),
                peers=context.peers,
                policy=context.sizing,
                state=context.portfolio_state,
            )
        borrowing = context.portfolio_state.borrowing_aud
        price_age = (as_of - last_close_dt).days if last_close_dt else None
        freshness = ConstraintResult(
            name="decision_evidence_freshness",
            status="pass" if price_age is not None and price_age <= PRICE_STALE_MATERIAL_DAYS else "fail",
            blocking=True,
            detail=(
                f"Last close is {price_age} day(s) before the cutoff (threshold {PRICE_STALE_MATERIAL_DAYS})."
                if price_age is not None else "No price is knowable at the cutoff."
            ),
        )

    # A passed challenge earns `watch` (non-action: tax readiness is unknown by
    # construction until G12 closes); anything else is `abstain`.
    state: RecommendationState = "watch" if challenge.outcome == "pass" else "abstain"
    zero_size = ZERO_SIZE
    portfolio_snapshot_id = f"live-portfolio-{as_of.isoformat()}"
    constraints = (
        ConstraintResult(
            name="model_a_quarantine", status="pass", blocking=True,
            detail="No Model A / quarantined signal enters this builder's evidence or capital path (rule #11).",
        ),
        ConstraintResult(
            name="no_leverage", status="pass" if borrowing == 0 else "fail", blocking=True,
            detail=f"Borrowing on the measured book: {borrowing} AUD (D2 requires 0).",
        ),
        ConstraintResult(
            name="no_broker_execution", status="pass", blocking=True,
            detail="This builder has no broker credential, order route, or execution adapter; staging is non-executable.",
        ),
        ConstraintResult(
            name="tradeability_and_ownership", status="unknown", blocking=True,
            detail="No live tradeability/ownership check is wired into this builder yet.",
        ),
        freshness,
    )
    assert UNIVERSAL_CONSTRAINTS == {c.name for c in constraints}

    portfolio = PortfolioAssessment(
        portfolio_assessment_id=f"pra-{slug}-{thesis_id}-{as_of.isoformat()}",
        portfolio_snapshot_id=portfolio_snapshot_id,
        thesis_version_id=thesis_version.thesis_version_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        assessment_state=state,
        size_range=zero_size,
        loss_budget_aud=Decimal("0"),
        marginal_risk=(
            f"No new capital risk: the state is {state}. Challenge outcome {challenge.outcome} with "
            f"{len(challenge.findings)} finding(s); indicative size range "
            f"{indicative_size.minimum_pct}-{indicative_size.maximum_pct}% is carried as zero pending tax readiness."
        ),
        opportunity_cost="Capital remains uncommitted to this thesis while the gate chain is unresolved.",
        constraints=constraints,
    )

    tax_reference = unresolved_tax_assessment_reference(
        tax_assessment_id=f"taxref-{slug}-{thesis_id}-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
    )
    manifest = (
        ManifestEntry(component="composition", version="deterministic-python-decision-engine-builder-0.2"),
        ManifestEntry(component="llm", version="none"),
        ManifestEntry(component="market_data", version="asxos-research-store-rs_financial_statements-rs_fundamentals_pit-prices"),
        ManifestEntry(component="code_contract", version="decision-engine-slice2.5-0.2"),
    )
    decision = DecisionPacket(
        decision_packet_id=f"dpk-{slug}-{thesis_id}-{as_of.isoformat()}",
        schema_version="slice2.5-0.2",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        recommendation_state=state,
        trading_calendar=calendar,
        expires_at=default_packet_expiry(cutoff, state, calendar),
        portfolio_snapshot_id=portfolio_snapshot_id,
        evidence_packet_id=evidence.evidence_packet_id,
        thesis_version_id=thesis_version.thesis_version_id,
        challenge_result_id=challenge.challenge_result_id,
        portfolio_assessment_id=portfolio.portfolio_assessment_id,
        upstream_hashes=UpstreamArtifactHashes(
            evidence_packet=evidence.content_hash,
            thesis_version=thesis_version.content_hash,
            challenge_result=challenge.content_hash,
            portfolio_assessment=portfolio.content_hash,
            tax_assessment_reference=tax_reference.content_hash,
        ),
        benchmark_id="xjoai-total-return",
        size_range=zero_size,
        staging_framework=(
            "Slice 3 staging is available (`decision_engine.staging.stage_order`) only from a passed "
            f"challenge and a non-zero size; this packet's challenge outcome is {challenge.outcome} and its "
            f"indicative range {indicative_size.minimum_pct}-{indicative_size.maximum_pct}%. No paper or real action."
        ),
        scenario_summary=(
            f"Bull/base/bear return cases derived from the recorded price plan: "
            f"{bull_return_pct}% / 0% / {bear_return_pct}%."
        ),
        risk_summary=challenge.strongest_bear_case,
        constraints_checked=tuple(c.name for c in constraints),
        missing_or_uncertain_inputs=tuple(missing),
        decision_ask=(
            "Review the challenge findings and record a disposition for each; no trade or paper action is "
            "requested by this packet."
        ),
        model_independence=True,
        model_and_prompt_manifest=manifest,
        tax_assessment_reference=tax_reference,
        created_at=cutoff,
    )
    return DecisionCase(
        case_id=f"{slug}-{thesis_id}-{as_of.isoformat()}",
        label=f"{symbol} — real decision case (challenge {challenge.outcome}, state {state})",
        changed_since_prior="Built from the current thesis row and the supplied context; supersession is the repository's job.",
        evidence=evidence,
        thesis=thesis_version,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )


async def build_cba_decision_case(
    conn: FetchConn,
    *,
    cutoff: datetime,
    thesis_id: int = _DEFAULT_THESIS_ID,
    candidate: CandidateSnapshot | None = None,
    context: ChallengeContext | None = None,
) -> DecisionCase:
    """Slice 1 entry point, kept: the CBA.AU (`thesis_id=1`) case."""
    return await build_decision_case(
        conn, cutoff=cutoff, thesis_id=thesis_id, candidate=candidate, context=context,
        expected_symbol=_EXPECTED_SYMBOL,
    )
