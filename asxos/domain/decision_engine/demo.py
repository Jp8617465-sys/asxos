"""Deterministic synthetic cases for the target-architecture live slice.

Nothing in this module reads market data or recommends a real security. The
fixtures exist to demonstrate both paths a production engine must support:
capital-ready paper intent and a hard abstention caused by missing/failed
constraints.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel

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
    PortfolioAssessment,
    Scenario,
    SizeRange,
    ThesisVersion,
)

_EMPTY_HASH = "0" * 64


def _digest(model: BaseModel, *, exclude: set[str]) -> str:
    payload = model.model_dump(mode="json", exclude=exclude)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _seal_evidence(packet: EvidencePacket) -> EvidencePacket:
    return packet.model_copy(update={"content_hash": _digest(packet, exclude={"content_hash"})})


def _seal_decision(packet: DecisionPacket) -> DecisionPacket:
    return packet.model_copy(update={"content_hash": _digest(packet, exclude={"content_hash"})})


def verify_content_hash(model: EvidencePacket | DecisionPacket) -> bool:
    """Return whether an immutable packet still matches its canonical payload."""
    return model.content_hash == _digest(model, exclude={"content_hash"})


def _ready_case(as_of: date, cutoff: datetime) -> DecisionCase:
    evidence = _seal_evidence(
        EvidencePacket(
            evidence_packet_id=f"evp-grid-{as_of.isoformat()}",
            as_of=as_of,
            knowledge_cutoff=cutoff,
            expires_at=cutoff + timedelta(days=7),
            items=(
                EvidenceItem(
                    evidence_id="grid-demand-01",
                    evidence_type="theme_fact",
                    title="Grid connection backlog",
                    claim="Synthetic demand series shows a persistent connection-equipment backlog.",
                    source_uri="synthetic://theme/grid-demand",
                    observed_at=as_of - timedelta(days=2),
                    known_at=cutoff - timedelta(days=2),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="grid-fundamental-01",
                    evidence_type="fundamental_fact",
                    title="Order conversion",
                    claim="Synthetic point-in-time accounts show improving order conversion and margins.",
                    source_uri="synthetic://fundamentals/GRID.AU",
                    observed_at=as_of - timedelta(days=5),
                    known_at=cutoff - timedelta(days=4),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="grid-valuation-01",
                    evidence_type="fundamental_fact",
                    title="Scenario valuation inputs",
                    claim="Synthetic cash-flow assumptions support a positively skewed paper payoff range.",
                    source_uri="synthetic://valuation/GRID.AU",
                    observed_at=as_of - timedelta(days=1),
                    known_at=cutoff - timedelta(hours=20),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="grid-liquidity-01",
                    evidence_type="market_fact",
                    title="Tradeability check",
                    claim="Synthetic liquidity is sufficient for the proposed paper size envelope.",
                    source_uri="synthetic://market/GRID.AU",
                    observed_at=as_of,
                    known_at=cutoff - timedelta(hours=2),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="portfolio-snapshot-01",
                    evidence_type="portfolio_fact",
                    title="Portfolio concentration snapshot",
                    claim="Synthetic portfolio has capacity inside name, sector, and theme limits.",
                    source_uri="synthetic://portfolio/snapshot-demo-2026-08-10",
                    observed_at=as_of,
                    known_at=cutoff - timedelta(hours=1),
                    quality="synthetic",
                ),
            ),
            content_hash=_EMPTY_HASH,
        )
    )

    thesis = ThesisVersion(
        thesis_version_id="thv-grid-001",
        symbol="GRID.AU",
        version=1,
        evidence_packet_id=evidence.evidence_packet_id,
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
            name="tradeability",
            status="pass",
            detail="Synthetic liquidity clears the paper-size requirement.",
        ),
        ConstraintResult(
            name="single_name_cap",
            status="pass",
            detail="Maximum paper size stays inside the fictional profile cap.",
        ),
        ConstraintResult(
            name="sector_theme_concentration",
            status="pass",
            detail="Incremental exposure remains inside the synthetic risk budget.",
        ),
        ConstraintResult(
            name="model_a_quarantine",
            status="pass",
            detail="No Model A signal or SHAP value enters the evidence path.",
        ),
    )
    portfolio = PortfolioAssessment(
        portfolio_assessment_id="pra-grid-001",
        portfolio_snapshot_id="portfolio-demo-2026-08-10",
        thesis_version_id=thesis.thesis_version_id,
        assessment_state="initiate",
        size_range=size_range,
        loss_budget_aud=Decimal("720"),
        marginal_risk="Adds measured industrial and grid-theme exposure; no synthetic cap breach.",
        opportunity_cost="Retains most capital for higher-evidence cases or cash.",
        constraints=constraints,
    )

    decision = _seal_decision(
        DecisionPacket(
            decision_packet_id="dpk-grid-001",
            schema_version="prototype-0.1",
            as_of=as_of,
            knowledge_cutoff=cutoff,
            expires_at=cutoff + timedelta(days=7),
            portfolio_snapshot_id=portfolio.portfolio_snapshot_id,
            evidence_packet_id=evidence.evidence_packet_id,
            thesis_version_id=thesis.thesis_version_id,
            challenge_result_id=challenge.challenge_result_id,
            portfolio_assessment_id=portfolio.portfolio_assessment_id,
            benchmark_id="synthetic-asx200-total-return",
            recommendation_state="initiate",
            size_range=size_range,
            staging_framework=(
                "Paper only: open half the range after approval; add only after the first catalyst "
                "confirms and no falsifier fires."
            ),
            scenario_summary="Synthetic bull/base/bear return cases: +32% / +14% / -18%.",
            risk_summary="Primary risks are backlog quality, execution, margin, and concentration.",
            constraints_checked=tuple(constraint.name for constraint in constraints),
            missing_or_uncertain_inputs=(),
            decision_ask=(
                "Approve or reject a fictional 2–4% paper position; no real trade can be produced."
            ),
            model_and_prompt_manifest={
                "composition": "deterministic-python",
                "llm": "none",
                "market_data": "synthetic",
                "code_contract": "decision-engine-prototype-0.1",
            },
            content_hash=_EMPTY_HASH,
            created_at=cutoff,
        )
    )
    return DecisionCase(
        case_id="paper-ready",
        label="Positive control — paper decision ready",
        changed_since_prior="New synthetic evidence cleared challenge and portfolio gates.",
        evidence=evidence,
        thesis=thesis,
        challenge=challenge,
        portfolio=portfolio,
        decision=decision,
    )


def _blocked_case(as_of: date, cutoff: datetime) -> DecisionCase:
    evidence = _seal_evidence(
        EvidencePacket(
            evidence_packet_id=f"evp-lock-{as_of.isoformat()}",
            as_of=as_of,
            knowledge_cutoff=cutoff,
            expires_at=cutoff + timedelta(days=2),
            items=(
                EvidenceItem(
                    evidence_id="lock-price-01",
                    evidence_type="market_fact",
                    title="Price condition",
                    claim="Synthetic price data places the legacy stop below the current close.",
                    source_uri="synthetic://market/LOCK.AU",
                    observed_at=as_of,
                    known_at=cutoff - timedelta(hours=2),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="lock-terms-01",
                    evidence_type="source_document",
                    title="Tradeability terms",
                    claim="Synthetic plan terms do not yet prove the position can be sold.",
                    source_uri="synthetic://documents/LOCK.AU-plan-terms",
                    observed_at=as_of - timedelta(days=1),
                    known_at=cutoff - timedelta(hours=12),
                    quality="synthetic",
                ),
                EvidenceItem(
                    evidence_id="portfolio-snapshot-02",
                    evidence_type="portfolio_fact",
                    title="Employer concentration",
                    claim="Synthetic portfolio already exceeds the intended employer-risk envelope.",
                    source_uri="synthetic://portfolio/snapshot-demo-2026-08-10",
                    observed_at=as_of,
                    known_at=cutoff - timedelta(hours=1),
                    quality="synthetic",
                ),
            ),
            content_hash=_EMPTY_HASH,
        )
    )

    thesis = ThesisVersion(
        thesis_version_id="thv-lock-001",
        symbol="LOCK.AU",
        version=1,
        evidence_packet_id=evidence.evidence_packet_id,
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
            name="tradeability",
            status="fail",
            detail="The synthetic plan terms do not establish an executable sale path.",
        ),
        ConstraintResult(
            name="employer_concentration",
            status="fail",
            detail="The fictional portfolio is already outside its intended envelope.",
        ),
        ConstraintResult(
            name="rule_enforceability",
            status="unknown",
            detail="A price condition cannot be admitted until tradeability is resolved.",
        ),
        ConstraintResult(
            name="model_a_quarantine",
            status="pass",
            detail="No Model A signal or SHAP value enters the evidence path.",
        ),
    )
    portfolio = PortfolioAssessment(
        portfolio_assessment_id="pra-lock-001",
        portfolio_snapshot_id="portfolio-demo-2026-08-10",
        thesis_version_id=thesis.thesis_version_id,
        assessment_state="abstain",
        size_range=size_range,
        loss_budget_aud=Decimal("0"),
        marginal_risk="Existing synthetic concentration is unresolved; no additional capital allowed.",
        opportunity_cost="Research time is better spent verifying the position state first.",
        constraints=constraints,
    )

    decision = _seal_decision(
        DecisionPacket(
            decision_packet_id="dpk-lock-001",
            schema_version="prototype-0.1",
            as_of=as_of,
            knowledge_cutoff=cutoff,
            expires_at=cutoff + timedelta(days=2),
            portfolio_snapshot_id=portfolio.portfolio_snapshot_id,
            evidence_packet_id=evidence.evidence_packet_id,
            thesis_version_id=thesis.thesis_version_id,
            challenge_result_id=challenge.challenge_result_id,
            portfolio_assessment_id=portfolio.portfolio_assessment_id,
            benchmark_id="synthetic-asx200-total-return",
            recommendation_state="abstain",
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
            model_and_prompt_manifest={
                "composition": "deterministic-python",
                "llm": "none",
                "market_data": "synthetic",
                "code_contract": "decision-engine-prototype-0.1",
            },
            content_hash=_EMPTY_HASH,
            created_at=cutoff,
        )
    )
    return DecisionCase(
        case_id="blocked-abstain",
        label="Negative control — system must abstain",
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
    return DecisionBrief(
        title="ASXOS research-to-decision cockpit",
        as_of=as_of,
        disclaimer=(
            "Synthetic architecture prototype only. Symbols, evidence, returns, sizes, and decisions "
            "are fictional. This surface reads no live market or portfolio data and cannot trade."
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
                detail="One append-only, hash-addressed truth feeds HTML and JSON.",
            ),
            ArchitectureStage(
                name="Disposition & learning",
                status="future",
                detail="Next adapter links James's response to outcomes and benchmark attribution.",
            ),
        ),
        cases=(_ready_case(as_of, cutoff), _blocked_case(as_of, cutoff)),
    )
