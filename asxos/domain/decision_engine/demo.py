"""Deterministic synthetic cases for the target-architecture live slice.

Nothing in this module reads market data or recommends a real security. The
fixtures demonstrate both admissible paths: a current paper-only intent and a
hard abstention caused by unresolved blocking constraints.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from asxos.domain.decision_engine.types import (
    ArchitectureStage,
    ChallengeFinding,
    ChallengeResult,
    ConstraintResult,
    DecisionBrief,
    DecisionCase,
    DecisionPacket,
    EvidenceItem,
    EvidencePacket,
    ManifestEntry,
    PortfolioAssessment,
    Scenario,
    SizeRange,
    TaxAssessmentReference,
    ThesisVersion,
    TradingSessionCalendar,
    UpstreamArtifactHashes,
    default_packet_expiry,
)


def _manifest() -> tuple[ManifestEntry, ...]:
    return (
        ManifestEntry(component="composition", version="deterministic-python"),
        ManifestEntry(component="llm", version="none"),
        ManifestEntry(component="market_data", version="synthetic"),
        ManifestEntry(component="code_contract", version="decision-engine-prototype-0.3"),
    )


def _upstream_hashes(
    evidence: EvidencePacket,
    thesis: ThesisVersion,
    challenge: ChallengeResult,
    portfolio: PortfolioAssessment,
    tax_reference: TaxAssessmentReference,
) -> UpstreamArtifactHashes:
    return UpstreamArtifactHashes(
        evidence_packet=evidence.content_hash,
        thesis_version=thesis.content_hash,
        challenge_result=challenge.content_hash,
        portfolio_assessment=portfolio.content_hash,
        tax_assessment_reference=tax_reference.content_hash,
    )


def _synthetic_trading_calendar(cutoff: datetime) -> TradingSessionCalendar:
    """Build demo-only weekday sessions; never use this as an exchange calendar."""
    sessions: list[datetime] = []
    cursor = cutoff
    while len(sessions) < 21:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            sessions.append(cursor)
    return TradingSessionCalendar(
        calendar_id="synthetic-weekdays-not-an-exchange-calendar",
        calendar_version="demo-2026-08-11",
        sessions=tuple(sessions),
    )


def _ready_case(
    as_of: date,
    cutoff: datetime,
    trading_calendar: TradingSessionCalendar,
) -> DecisionCase:
    expiry = default_packet_expiry(cutoff, "initiate", trading_calendar)
    evidence = EvidencePacket(
        evidence_packet_id=f"evp-grid-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=expiry,
        data_mode="synthetic",
        created_at=cutoff,
        items=(
            EvidenceItem(
                evidence_id="grid-demand-01",
                evidence_type="theme_fact",
                title="Grid connection backlog",
                claim="Synthetic demand series shows a persistent connection-equipment backlog.",
                source_uri="synthetic://theme/grid-demand",
                observed_at=as_of - timedelta(days=2),
                known_at=cutoff - timedelta(days=2),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="grid-fundamental-01",
                evidence_type="fundamental_fact",
                title="Order conversion",
                claim="Synthetic point-in-time accounts show improving order conversion and margins.",
                source_uri="synthetic://fundamentals/GRID.AU",
                observed_at=as_of - timedelta(days=5),
                known_at=cutoff - timedelta(days=4),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="grid-valuation-01",
                evidence_type="fundamental_fact",
                title="Scenario valuation inputs",
                claim="Synthetic cash-flow assumptions support a positively skewed paper payoff range.",
                source_uri="synthetic://valuation/GRID.AU",
                observed_at=as_of - timedelta(days=1),
                known_at=cutoff - timedelta(hours=20),
                evidence_tier="inferred",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="grid-liquidity-01",
                evidence_type="market_fact",
                title="Tradeability check",
                claim="Synthetic liquidity is sufficient for the proposed paper size envelope.",
                source_uri="synthetic://market/GRID.AU",
                observed_at=as_of,
                known_at=cutoff - timedelta(hours=2),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="portfolio-snapshot-01",
                evidence_type="portfolio_fact",
                title="Portfolio concentration snapshot",
                claim="Synthetic portfolio has capacity inside name, sector, and theme limits.",
                source_uri="synthetic://portfolio/snapshot-demo-2026-08-10",
                observed_at=as_of,
                known_at=cutoff - timedelta(hours=1),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
        ),
    )

    thesis = ThesisVersion(
        thesis_version_id="thv-grid-001",
        security_id="sec-synthetic-grid-au",
        symbol="GRID",
        exchange="ASX",
        version=1,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        theme="Grid modernisation picks-and-shovels",
        investment_question="Does the connection backlog create durable earnings upside?",
        variant_view=(
            "The synthetic market view discounts the backlog as temporary while the admitted "
            "evidence supports a multi-period conversion cycle."
        ),
        thesis_summary=(
            "A fictional, ordinary ASX-equity positive control used to show how governed evidence, "
            "challenge, and portfolio constraints become one paper decision."
        ),
        catalysts=(
            "Backlog converts into reported revenue without margin erosion.",
            "New connection awards extend visibility beyond the current cycle.",
        ),
        falsifiers=(
            "Order conversion stalls for two review periods.",
            "Gross margin falls despite backlog conversion.",
        ),
        horizon_months=18,
        scenarios=(
            Scenario(
                label="bull",
                return_pct=Decimal("32"),
                probability_pct=Decimal("25"),
                rationale="Faster conversion and sustained pricing power.",
                evidence_ids=("grid-demand-01", "grid-fundamental-01"),
            ),
            Scenario(
                label="base",
                return_pct=Decimal("14"),
                probability_pct=Decimal("50"),
                rationale="Order book converts near the synthetic base assumptions.",
                evidence_ids=("grid-fundamental-01", "grid-valuation-01"),
            ),
            Scenario(
                label="bear",
                return_pct=Decimal("-18"),
                probability_pct=Decimal("25"),
                rationale="Execution delays and input costs compress the expected payoff.",
                evidence_ids=("grid-demand-01", "grid-valuation-01"),
            ),
        ),
        evidence_ids=(
            "grid-demand-01",
            "grid-fundamental-01",
            "grid-valuation-01",
            "grid-liquidity-01",
        ),
    )

    challenge = ChallengeResult(
        challenge_result_id="chr-grid-001",
        thesis_version_id=thesis.thesis_version_id,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        outcome="pass",
        strongest_bear_case=(
            "The backlog may reflect delayed rather than incremental demand, leaving margins and "
            "working capital worse than the headline growth suggests."
        ),
        findings=(
            ChallengeFinding(
                severity="material",
                finding="Synthetic customer-concentration evidence is still shallow.",
                required_response="Recheck concentration at each paper review; do not widen size.",
                evidence_ids=("grid-fundamental-01",),
            ),
            ChallengeFinding(
                severity="monitor",
                finding="Backlog quality depends on cancellation and conversion behaviour.",
                required_response="Track conversion and cancellation as explicit falsifier measures.",
                evidence_ids=("grid-demand-01",),
            ),
        ),
        independent_of_author=True,
    )

    size_range = SizeRange(minimum_pct=Decimal("2"), maximum_pct=Decimal("4"))
    constraints = (
        ConstraintResult(
            name="tradeability_and_ownership",
            status="pass",
            blocking=True,
            detail="Synthetic liquidity clears the paper-size requirement.",
        ),
        ConstraintResult(
            name="single_name_cap",
            status="pass",
            blocking=True,
            detail="Maximum paper size stays inside the fictional profile cap.",
        ),
        ConstraintResult(
            name="sector_theme_concentration",
            status="pass",
            blocking=True,
            detail="Incremental exposure remains inside the synthetic risk budget.",
        ),
        ConstraintResult(
            name="model_a_quarantine",
            status="pass",
            blocking=True,
            detail="No quarantined model signal enters the evidence or capital path.",
        ),
        ConstraintResult(
            name="no_leverage",
            status="pass",
            blocking=True,
            detail="The synthetic paper case contains no leverage.",
        ),
        ConstraintResult(
            name="decision_evidence_freshness",
            status="pass",
            blocking=True,
            detail="All synthetic decision-critical evidence is current at the packet cutoff.",
        ),
        ConstraintResult(
            name="no_broker_execution",
            status="pass",
            blocking=True,
            detail="The prototype has no broker credential, order route, or execution adapter.",
        ),
    )
    portfolio = PortfolioAssessment(
        portfolio_assessment_id="pra-grid-001",
        portfolio_snapshot_id="portfolio-demo-2026-08-10",
        thesis_version_id=thesis.thesis_version_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        assessment_state="initiate",
        size_range=size_range,
        loss_budget_aud=Decimal("720"),
        marginal_risk="Adds measured industrial and grid-theme exposure; no synthetic cap breach.",
        opportunity_cost="Retains most capital for higher-evidence cases or cash.",
        constraints=constraints,
    )
    tax_reference = TaxAssessmentReference(
        tax_assessment_id="taxref-grid-001",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        applicability="applicable",
        readiness="pass",
    )
    decision = DecisionPacket(
        decision_packet_id="dpk-grid-001",
        schema_version="prototype-0.3",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        recommendation_state="initiate",
        trading_calendar=trading_calendar,
        expires_at=expiry,
        portfolio_snapshot_id=portfolio.portfolio_snapshot_id,
        evidence_packet_id=evidence.evidence_packet_id,
        thesis_version_id=thesis.thesis_version_id,
        challenge_result_id=challenge.challenge_result_id,
        portfolio_assessment_id=portfolio.portfolio_assessment_id,
        upstream_hashes=_upstream_hashes(
            evidence, thesis, challenge, portfolio, tax_reference
        ),
        benchmark_id="synthetic-xjoai-total-return",
        size_range=size_range,
        staging_framework=(
            "Paper only: open half the range after approval; add only after the first catalyst "
            "confirms and no falsifier fires."
        ),
        scenario_summary="Synthetic bull/base/bear return cases: +32% / +14% / -18%.",
        risk_summary="Primary risks are backlog quality, execution, margin, and concentration.",
        constraints_checked=tuple(constraint.name for constraint in constraints),
        missing_or_uncertain_inputs=(),
        decision_ask="Approve or reject a fictional 2-4% paper position; no real trade can be produced.",
        model_independence=True,
        model_and_prompt_manifest=_manifest(),
        tax_assessment_reference=tax_reference,
        created_at=cutoff,
    )
    return DecisionCase(
        case_id="paper-ready",
        label="Positive control - paper decision ready",
        changed_since_prior="New synthetic evidence cleared challenge and portfolio gates.",
        evidence=evidence,
        thesis=thesis,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )


def _blocked_case(
    as_of: date,
    cutoff: datetime,
    trading_calendar: TradingSessionCalendar,
) -> DecisionCase:
    expiry = default_packet_expiry(cutoff, "abstain", trading_calendar)
    evidence = EvidencePacket(
        evidence_packet_id=f"evp-lock-{as_of.isoformat()}",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        expires_at=expiry,
        data_mode="synthetic",
        created_at=cutoff,
        items=(
            EvidenceItem(
                evidence_id="lock-price-01",
                evidence_type="market_fact",
                title="Price condition",
                claim="Synthetic price data places the legacy stop below the current close.",
                source_uri="synthetic://market/LOCK.AU",
                observed_at=as_of,
                known_at=cutoff - timedelta(hours=2),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="lock-terms-01",
                evidence_type="source_document",
                title="Tradeability terms",
                claim="Synthetic plan terms do not yet prove the position can be sold.",
                source_uri="synthetic://documents/LOCK.AU-plan-terms",
                observed_at=as_of - timedelta(days=1),
                known_at=cutoff - timedelta(hours=12),
                evidence_tier="speculative",
                data_mode="synthetic",
            ),
            EvidenceItem(
                evidence_id="portfolio-snapshot-02",
                evidence_type="portfolio_fact",
                title="Employer concentration",
                claim="Synthetic portfolio already exceeds the intended employer-risk envelope.",
                source_uri="synthetic://portfolio/snapshot-demo-2026-08-10",
                observed_at=as_of,
                known_at=cutoff - timedelta(hours=1),
                evidence_tier="verified",
                data_mode="synthetic",
            ),
        ),
    )

    thesis = ThesisVersion(
        thesis_version_id="thv-lock-001",
        security_id="sec-synthetic-lock-au",
        symbol="LOCK",
        exchange="ASX",
        version=1,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        theme="Employer-linked equity",
        investment_question="Can a price rule govern capital that may not be tradeable?",
        variant_view="Tradeability must be established before any price-based action is admissible.",
        thesis_summary=(
            "A fictional negative control showing that valid-looking market thresholds cannot "
            "override an unresolved ownership or sale restriction."
        ),
        catalysts=("Verified sale eligibility and reconciled beneficial ownership.",),
        falsifiers=("The position remains locked or the governing terms remain ambiguous.",),
        horizon_months=12,
        scenarios=(
            Scenario(
                label="bull",
                return_pct=Decimal("25"),
                probability_pct=Decimal("20"),
                rationale="Illustrative upside if restrictions clear and operations improve.",
                evidence_ids=("lock-price-01",),
            ),
            Scenario(
                label="base",
                return_pct=Decimal("5"),
                probability_pct=Decimal("45"),
                rationale="Illustrative drift while tradeability remains unresolved.",
                evidence_ids=("lock-price-01", "lock-terms-01"),
            ),
            Scenario(
                label="bear",
                return_pct=Decimal("-30"),
                probability_pct=Decimal("35"),
                rationale="Concentration and inability to act compound downside.",
                evidence_ids=("lock-terms-01", "portfolio-snapshot-02"),
            ),
        ),
        evidence_ids=("lock-price-01", "lock-terms-01", "portfolio-snapshot-02"),
    )

    challenge = ChallengeResult(
        challenge_result_id="chr-lock-001",
        thesis_version_id=thesis.thesis_version_id,
        evidence_packet_id=evidence.evidence_packet_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        outcome="abstain",
        strongest_bear_case=(
            "The system issues an unenforceable exit instruction, then mistakes failure to act "
            "for user non-compliance instead of an upstream classification defect."
        ),
        findings=(
            ChallengeFinding(
                severity="blocking",
                finding="Sale eligibility is not established.",
                required_response="Verify plan terms and position ownership before authoring any rule.",
                evidence_ids=("lock-terms-01",),
            ),
            ChallengeFinding(
                severity="material",
                finding="Existing concentration exceeds the fictional employer-risk envelope.",
                required_response="Treat this as risk remediation, not a new capital candidate.",
                evidence_ids=("portfolio-snapshot-02",),
            ),
        ),
        independent_of_author=True,
    )

    size_range = SizeRange(minimum_pct=Decimal("0"), maximum_pct=Decimal("0"))
    constraints = (
        ConstraintResult(
            name="tradeability_and_ownership",
            status="fail",
            blocking=True,
            detail="The synthetic plan terms do not establish an executable sale path.",
        ),
        ConstraintResult(
            name="employer_concentration",
            status="fail",
            blocking=True,
            detail="The fictional portfolio is already outside its intended envelope.",
        ),
        ConstraintResult(
            name="rule_enforceability",
            status="unknown",
            blocking=True,
            detail="A price condition cannot be admitted until tradeability is resolved.",
        ),
        ConstraintResult(
            name="model_a_quarantine",
            status="pass",
            blocking=True,
            detail="No quarantined model signal enters the evidence or capital path.",
        ),
        ConstraintResult(
            name="no_leverage",
            status="pass",
            blocking=True,
            detail="The synthetic abstention case contains no leverage.",
        ),
        ConstraintResult(
            name="decision_evidence_freshness",
            status="pass",
            blocking=True,
            detail="Admitted synthetic evidence is current; its substance still blocks action.",
        ),
        ConstraintResult(
            name="no_broker_execution",
            status="pass",
            blocking=True,
            detail="The prototype has no broker credential, order route, or execution adapter.",
        ),
    )
    portfolio = PortfolioAssessment(
        portfolio_assessment_id="pra-lock-001",
        portfolio_snapshot_id="portfolio-demo-2026-08-10",
        thesis_version_id=thesis.thesis_version_id,
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        assessment_state="abstain",
        size_range=size_range,
        loss_budget_aud=Decimal("0"),
        marginal_risk="Existing synthetic concentration is unresolved; no additional capital allowed.",
        opportunity_cost="Research time is better spent verifying the position state first.",
        constraints=constraints,
    )
    tax_reference = TaxAssessmentReference(
        tax_assessment_id="taxref-lock-001",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        created_at=cutoff,
        applicability="uncertain",
        readiness="unknown",
    )
    decision = DecisionPacket(
        decision_packet_id="dpk-lock-001",
        schema_version="prototype-0.3",
        as_of=as_of,
        knowledge_cutoff=cutoff,
        recommendation_state="abstain",
        trading_calendar=trading_calendar,
        expires_at=expiry,
        portfolio_snapshot_id=portfolio.portfolio_snapshot_id,
        evidence_packet_id=evidence.evidence_packet_id,
        thesis_version_id=thesis.thesis_version_id,
        challenge_result_id=challenge.challenge_result_id,
        portfolio_assessment_id=portfolio.portfolio_assessment_id,
        upstream_hashes=_upstream_hashes(
            evidence, thesis, challenge, portfolio, tax_reference
        ),
        benchmark_id="synthetic-xjoai-total-return",
        size_range=size_range,
        staging_framework="No paper or real action until the blocking evidence is resolved.",
        scenario_summary="Scenario values are retained for review but cannot authorise an action.",
        risk_summary="Tradeability and concentration failures dominate price-based analysis.",
        constraints_checked=tuple(constraint.name for constraint in constraints),
        missing_or_uncertain_inputs=(
            "Verified sale eligibility",
            "Reconciled beneficial ownership and lot status",
        ),
        decision_ask="Confirm the position terms; do not approve a price-based instruction.",
        model_independence=True,
        model_and_prompt_manifest=_manifest(),
        tax_assessment_reference=tax_reference,
        created_at=cutoff,
    )
    return DecisionCase(
        case_id="blocked-abstain",
        label="Negative control - system must abstain",
        changed_since_prior="Tradeability and concentration checks now block the price rule.",
        evidence=evidence,
        thesis=thesis,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )


def build_demo_brief(as_of: date = date(2026, 8, 10)) -> DecisionBrief:
    """Build a stable, fully linked demonstration brief without external I/O."""
    cutoff = datetime.combine(as_of, datetime.min.time(), tzinfo=UTC) + timedelta(hours=8)
    trading_calendar = _synthetic_trading_calendar(cutoff)
    return DecisionBrief(
        title="ASXOS research-to-decision cockpit",
        as_of=as_of,
        disclaimer=(
            "Synthetic architecture prototype only. Security identities, evidence, returns, sizes, "
            "tax states, and decisions are fictional. This surface reads no live market or portfolio "
            "data and cannot trade."
        ),
        one_thing=(
            "Judge the decision chain: can every claim, challenge, constraint, and user ask be "
            "resolved to one immutable packet?"
        ),
        architecture_stages=(
            ArchitectureStage(
                name="Evidence",
                status="adapter_needed",
                detail="Contract shown; production adapter will freeze existing PIT data and sources.",
            ),
            ArchitectureStage(
                name="Research & theme",
                status="reused",
                detail="Maps to existing screening, research, macro-thesis, and theme services.",
            ),
            ArchitectureStage(
                name="Thesis",
                status="reused",
                detail="Maps to existing governed thesis proposal and revision structures.",
            ),
            ArchitectureStage(
                name="Independent challenge",
                status="demonstrated",
                detail="Typed challenge can pass, require revision, or force abstention.",
            ),
            ArchitectureStage(
                name="Portfolio & capital",
                status="reused",
                detail="Maps to existing profile, constraints, tax overlay, and paper portfolio.",
            ),
            ArchitectureStage(
                name="Decision packet",
                status="demonstrated",
                detail="One deeply immutable, hash-addressed truth feeds HTML and JSON.",
            ),
            ArchitectureStage(
                name="Disposition & learning",
                status="future",
                detail="Next adapter links James's response to outcomes and benchmark attribution.",
            ),
        ),
        cases=(
            _ready_case(as_of, cutoff, trading_calendar),
            _blocked_case(as_of, cutoff, trading_calendar),
        ),
    )
