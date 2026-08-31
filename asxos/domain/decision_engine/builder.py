"""Slice 1 builder — one real `DecisionCase` for CBA.AU (`thesis_id=1`).

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
- The `ChallengeResult` is a real, permanent finding, not a placeholder
  fixture: Slice 2.5 (the independent challenger) has not been built, so
  every case this builder produces is mechanically forced to `abstain`
  by `DecisionCase`'s own validators — this is the intended, honest
  Slice 1 outcome (`docs/product/architecture-decision-record.md` SS6),
  not a bug to fix later in this module.

Import-isolation (rule #11): this module never reads `signals`,
`signal_outcomes`, `model_versions.prob_up`/`shap_factors`, or any other
Model A surface — it has no reason to and does not import
`asxos.domain.models.*` at all.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from asxos.domain.decision_engine.calendar import build_forward_weekday_calendar
from asxos.domain.decision_engine.types import (
    UNIVERSAL_CONSTRAINTS,
    ChallengeFinding,
    ChallengeResult,
    ConstraintResult,
    DecisionCase,
    DecisionPacket,
    EvidenceItem,
    EvidencePacket,
    ManifestEntry,
    PortfolioAssessment,
    Scenario,
    SizeRange,
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
from asxos.domain.theses.service import get_thesis

#: Not in pit_db.py's admissible-table SQL constants (it has no "latest
#: period" query) — mirrors its query-construction style: SELECT-only,
#: bound parameters, an admissible table (`rs_financial_statements`).
SQL_LATEST_YEARLY_PERIOD_END: Final[str] = (
    "SELECT MAX(period_end) AS period_end FROM rs_financial_statements "
    "WHERE symbol = $1 AND period_type = 'yearly' AND statement_type = 'income'"
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
    `derive_statement_known_at` rule (G8) rather than re-deriving it."""
    if not isinstance(row, Mapping):
        return None
    report_d = _coerce_date(row.get("report_date"))
    filing_d = _coerce_date(row.get("filing_date"))
    known_at = derive_statement_known_at(period_end, report_d, filing_d, as_of)
    if known_at > cutoff:
        return None
    return known_at


async def build_cba_decision_case(
    conn: FetchConn,
    *,
    cutoff: datetime,
    thesis_id: int = _DEFAULT_THESIS_ID,
) -> DecisionCase:
    """Compose one real, honest-abstain `DecisionCase` for CBA.AU.

    `cutoff` is the caller-supplied `knowledge_cutoff` (must be UTC,
    enforced by every contract's own validators) — this module does not
    default to "now" so the packet stays reproducible and testable.
    """
    thesis = await get_thesis(conn, thesis_id)
    if thesis is None:
        raise ValueError(f"no theses row for thesis_id={thesis_id}")
    if thesis.symbol != _EXPECTED_SYMBOL:
        raise ValueError(
            f"builder is scoped to {_EXPECTED_SYMBOL} (thesis_id={_DEFAULT_THESIS_ID}); "
            f"thesis_id={thesis_id} has symbol={thesis.symbol!r}"
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
    as_of = cutoff.date()

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
    expires_at = default_packet_expiry(cutoff, "abstain", calendar)

    items: list[EvidenceItem] = []

    # -- Fundamentals: mirrors pit_db.py's query construction and known_at
    # rule (see module docstring); NOT pit_db.build_pit_case() itself.
    assert_sql_admissible(SQL_LATEST_YEARLY_PERIOD_END)
    assert_sql_admissible(SQL_INCOME)
    period_row = await conn.fetchrow(SQL_LATEST_YEARLY_PERIOD_END, symbol)
    period_end = _coerce_date(period_row["period_end"]) if period_row else None
    if period_end is None:
        raise ValueError(f"no yearly income statement found for {symbol} in rs_financial_statements")

    current_row = await conn.fetchrow(SQL_INCOME, symbol, period_end, "yearly")
    current_known = _income_known_at(current_row, period_end=period_end, as_of=as_of, cutoff=cutoff)
    if current_known is None:
        raise ValueError(
            f"no admissible yearly income row for {symbol} period_end={period_end.isoformat()} "
            f"at knowledge cutoff {cutoff.isoformat()}"
        )
    items.append(
        EvidenceItem(
            evidence_id="cba-income-current",
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
                evidence_id="cba-income-prior",
                evidence_type="fundamental_fact",
                title=f"{symbol} yearly income {prior_end.isoformat()}",
                claim=(
                    f"Prior-year research-store income row for {symbol} "
                    f"{prior_end.isoformat()}."
                ),
                source_uri=f"asxos://rs_financial_statements/{symbol}/{prior_end.isoformat()}/yearly/income",
                observed_at=prior_end,
                known_at=prior_known,
                evidence_tier="verified",
                data_mode="real",
            )
        )

    # -- Thesis narrative: theme_fact. This is a qualitative claim about the
    # investment theme/thesis itself, not a financial-statement fact, a
    # market-price fact, a portfolio-state fact, or a source document — of
    # the five `EvidenceItem.evidence_type` values, `theme_fact` is the
    # closest fit (no dedicated "thesis_fact" exists in types.py).
    items.append(
        EvidenceItem(
            evidence_id="cba-thesis-narrative",
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

    # -- Invalidation conditions: portfolio_fact. These describe when this
    # position's portfolio treatment should change (review/exit triggers),
    # not a fact about the underlying theme or the company's fundamentals —
    # picked over theme_fact for that reason.
    if thesis.invalidation_conditions:
        conditions_claim = "; ".join(
            f"{ic.condition} (status={ic.status})" + (f" — {ic.note}" if ic.note else "")
            for ic in thesis.invalidation_conditions
        )
        items.append(
            EvidenceItem(
                evidence_id="cba-thesis-invalidation-conditions",
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
        falsifiers = tuple(
            f"{ic.condition} (status={ic.status})" for ic in thesis.invalidation_conditions
        )
    else:
        falsifiers = (
            "No invalidation_conditions are on file for this thesis; "
            "none can be honestly cited as a falsifier.",
        )

    # -- Price plan: market_fact (a fact about price levels, not the theme
    # or the company's own reported fundamentals). Required to derive real
    # bull/bear scenario returns below — hard-fails if absent rather than
    # inventing scenario numbers with no price plan behind them.
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
            evidence_id="cba-thesis-price-plan",
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

    evidence_ids = tuple(item.evidence_id for item in items)

    evidence = EvidencePacket(
        evidence_packet_id=f"evp-cba-{thesis_id}-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=expires_at,
        data_mode="real",
        created_at=cutoff,
        items=tuple(items),
    )

    bull_return_pct = _pct((thesis.target_price - reference_price) / reference_price * Decimal("100"))
    bear_return_pct = _pct((thesis.stop_price - reference_price) / reference_price * Decimal("100"))
    scenarios = (
        Scenario(
            label="bull",
            return_pct=bull_return_pct,
            probability_pct=Decimal("25"),
            rationale=f"Reaching the recorded target_price of {thesis.target_price} from a reference price of {reference_price}.",
            evidence_ids=("cba-thesis-price-plan",),
        ),
        Scenario(
            label="base",
            return_pct=Decimal("0"),
            probability_pct=Decimal("50"),
            rationale="No structured base-case target exists on the theses table; treated as unchanged from the reference price.",
            evidence_ids=("cba-thesis-price-plan",),
        ),
        Scenario(
            label="bear",
            return_pct=bear_return_pct,
            probability_pct=Decimal("25"),
            rationale=f"Falling to the recorded stop_price of {thesis.stop_price} from a reference price of {reference_price}.",
            evidence_ids=("cba-thesis-price-plan",),
        ),
    )

    if thesis.next_earnings_date is not None:
        catalysts = (
            f"Next scheduled earnings date on file: {thesis.next_earnings_date.date().isoformat()}.",
        )
    else:
        catalysts = (
            "No structured catalyst calendar exists on the theses table yet; "
            "see the thesis narrative evidence item for the full articulated view.",
        )

    if thesis.timeline_days is None or thesis.timeline_days <= 0:
        raise ValueError(f"thesis_id={thesis_id} has no timeline_days to derive a horizon from")
    horizon_months = max(1, min(120, round(thesis.timeline_days / 30)))

    theme = ", ".join(thesis.themes) if thesis.themes else "No theme_code attached to this thesis"

    thesis_version = ThesisVersion(
        thesis_version_id=f"thv-cba-{thesis_id}-{as_of.isoformat()}",
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
            "cba-thesis-narrative evidence item."
        ),
        thesis_summary=thesis.thesis_text,
        catalysts=catalysts,
        falsifiers=falsifiers,
        horizon_months=horizon_months,
        scenarios=scenarios,
        evidence_ids=evidence_ids,
    )

    challenge = ChallengeResult(
        challenge_result_id=f"chr-cba-{thesis_id}-{as_of.isoformat()}",
        thesis_version_id=thesis_version.thesis_version_id,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        outcome="abstain",
        strongest_bear_case=(
            "No independent challenger has stress-tested this thesis; presenting it as "
            "actionable would let the author's own framing pass unopposed."
        ),
        findings=(
            ChallengeFinding(
                severity="blocking",
                finding="No independent challenge mechanism exists yet (Slice 2.5, not yet built).",
                required_response=(
                    "Build and run an independent challenger (Slice 2.5) before this "
                    "thesis can support any action state."
                ),
                evidence_ids=("cba-thesis-narrative",),
            ),
        ),
        independent_of_author=True,
    )

    zero_size = SizeRange(minimum_pct=Decimal("0"), maximum_pct=Decimal("0"))
    portfolio_snapshot_id = f"live-portfolio-{as_of.isoformat()}"
    constraints = (
        ConstraintResult(
            name="model_a_quarantine",
            status="pass",
            blocking=True,
            detail="No Model A / quarantined signal enters this builder's evidence or capital path (rule #11).",
        ),
        ConstraintResult(
            name="no_leverage",
            status="pass",
            blocking=True,
            detail="This is a research-only abstain packet; no leverage is proposed.",
        ),
        ConstraintResult(
            name="no_broker_execution",
            status="pass",
            blocking=True,
            detail="This builder has no broker credential, order route, or execution adapter.",
        ),
        ConstraintResult(
            name="tradeability_and_ownership",
            status="unknown",
            blocking=True,
            detail="No live tradeability/ownership check is wired into this builder yet.",
        ),
        ConstraintResult(
            name="decision_evidence_freshness",
            status="unknown",
            blocking=True,
            detail=(
                "No automated freshness policy is wired into this builder yet; evidence "
                "recency is only as fresh as the caller-supplied knowledge_cutoff."
            ),
        ),
    )
    assert UNIVERSAL_CONSTRAINTS == {c.name for c in constraints}

    portfolio = PortfolioAssessment(
        portfolio_assessment_id=f"pra-cba-{thesis_id}-{as_of.isoformat()}",
        portfolio_snapshot_id=portfolio_snapshot_id,
        thesis_version_id=thesis_version.thesis_version_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        assessment_state="abstain",
        size_range=zero_size,
        loss_budget_aud=Decimal("0"),
        marginal_risk=(
            "No new capital risk: the recommendation state is abstain pending an "
            "independent challenge mechanism (Slice 2.5)."
        ),
        opportunity_cost=(
            "Capital remains uncommitted to this thesis while the challenge gate is unresolved."
        ),
        constraints=constraints,
    )

    tax_reference = unresolved_tax_assessment_reference(
        tax_assessment_id=f"taxref-cba-{thesis_id}-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
    )

    manifest = (
        ManifestEntry(component="composition", version="deterministic-python-decision-engine-builder-0.1"),
        ManifestEntry(component="llm", version="none"),
        ManifestEntry(
            component="market_data",
            version="asxos-research-store-rs_financial_statements-rs_fundamentals_pit",
        ),
        ManifestEntry(component="code_contract", version="decision-engine-slice1-0.1"),
    )

    decision = DecisionPacket(
        decision_packet_id=f"dpk-cba-{thesis_id}-{as_of.isoformat()}",
        schema_version="slice1-0.1",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        recommendation_state="abstain",
        trading_calendar=calendar,
        expires_at=expires_at,
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
            "No paper or real action until an independent challenge mechanism exists (Slice 2.5)."
        ),
        scenario_summary=(
            f"Bull/base/bear return cases derived from the recorded price plan: "
            f"{bull_return_pct}% / 0% / {bear_return_pct}%."
        ),
        risk_summary=(
            "The primary blocker is the absence of an independent challenge process; the "
            "fundamentals and thesis narrative above are informational only pending that gate."
        ),
        constraints_checked=tuple(c.name for c in constraints),
        missing_or_uncertain_inputs=(
            "Independent challenge mechanism (Slice 2.5, not yet built)",
            "Real dividend/realised-gains feed for tax readiness (G12)",
            "Live tradeability/ownership and evidence-freshness checks (not yet wired into this builder)",
        ),
        decision_ask=(
            "Confirm whether an independent challenge mechanism should be built next; no "
            "trade or paper action is requested by this packet."
        ),
        model_independence=True,
        model_and_prompt_manifest=manifest,
        tax_assessment_reference=tax_reference,
        created_at=cutoff,
    )

    return DecisionCase(
        case_id=f"cba-{thesis_id}-{as_of.isoformat()}",
        label="CBA.AU — honest-abstain real decision case (Slice 1)",
        changed_since_prior="Initial real DecisionCase for this thesis; no prior packet exists yet.",
        evidence=evidence,
        thesis=thesis_version,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )
