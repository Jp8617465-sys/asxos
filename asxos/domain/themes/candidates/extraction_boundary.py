"""The LLM extraction/synthesis boundary — the only door LLM text comes through.

A discovery agent (`theme-researcher`, `sector-screener`, `macro-economist`)
emits a fenced JSON proposal whose `evidence` list carries claims with a tier
and, for `db_query` claims, the literal `snapshot_data` observed. This module
turns those into `EvidenceItem`s under three rules the agent cannot override:

1. **Tier cap.** An LLM may assert `verified` only for a `db_query` claim that
   carries `snapshot_data`; anything else is capped at `inferred`.
   `speculative` stays `speculative` and is kept, labelled — it is not deleted,
   because deleting is how a proposal starts looking cleaner than it was.
2. **No recommendation verbs.** A claim whose text tells the reader what to do
   (buy/sell/overweight/accumulate/exit/target price…) is refused outright.
   Stage 3 artifacts carry evidence, not advice, and the boundary is where the
   difference is enforced.
3. **No numbers are computed here.** The boundary transcribes; `measures.py`
   computes. An LLM-quoted figure is a claim, not a measure.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Final, Literal

from asxos.domain.decision_engine.types import DataMode, EvidenceItem, EvidenceTier

_RECOMMENDATION_VERBS: Final = re.compile(
    r"\b(buy|sell|accumulate|overweight|underweight|go long|go short|exit|"
    r"take profit|price target|target price|top pick|strong (?:buy|sell))\b",
    re.IGNORECASE,
)
_TIER_ORDER: Final[dict[str, int]] = {"verified": 2, "inferred": 1, "speculative": 0}
EvidenceType = Literal["market_fact", "fundamental_fact", "source_document", "theme_fact", "portfolio_fact"]


class BoundaryError(ValueError):
    """The proposal cannot be admitted as evidence."""


def _cap_tier(claim: dict[str, Any]) -> EvidenceTier:
    asserted = str(claim.get("tier", "speculative")).lower()
    if asserted not in _TIER_ORDER:
        raise BoundaryError(f"unknown evidence tier {asserted!r}")
    if asserted == "verified":
        if claim.get("source_type") == "db_query" and claim.get("snapshot_data"):
            return "verified"
        return "inferred"
    return asserted  # type: ignore[return-value]


def _evidence_type_for(claim: dict[str, Any]) -> EvidenceType:
    table = str(claim.get("source_table", "")).lower()
    if "macro" in table or "theme" in table:
        return "theme_fact"
    if "fundament" in table or "financial" in table or "factor" in table:
        return "fundamental_fact"
    if "price" in table:
        return "market_fact"
    return "source_document"


def evidence_from_proposal(
    proposal: dict[str, Any],
    *,
    known_at: datetime,
    as_of: date,
    data_mode: DataMode = "real",
    id_prefix: str = "agent",
) -> tuple[EvidenceItem, ...]:
    """Admit an agent proposal's `evidence` list as EvidenceItems, or refuse."""
    claims = proposal.get("evidence")
    if not isinstance(claims, list) or not claims:
        raise BoundaryError("proposal carries no evidence list")
    items: list[EvidenceItem] = []
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise BoundaryError(f"evidence[{idx}] is not an object")
        text = str(claim.get("claim", "")).strip()
        if not text:
            raise BoundaryError(f"evidence[{idx}] has an empty claim")
        if _RECOMMENDATION_VERBS.search(text):
            raise BoundaryError(
                f"evidence[{idx}] reads as a recommendation ({_RECOMMENDATION_VERBS.search(text).group(0)!r}); "  # type: ignore[union-attr]
                "the boundary admits facts, not advice"
            )
        observed = claim.get("source_as_of")
        observed_at = date.fromisoformat(str(observed)) if observed else as_of
        if observed_at > as_of:
            raise BoundaryError(f"evidence[{idx}] observed after as_of")
        source_table = str(claim.get("source_table") or "agent_response")
        items.append(
            EvidenceItem(
                evidence_id=f"{id_prefix}:{idx}",
                evidence_type=_evidence_type_for(claim),
                title=text[:120],
                claim=text,
                source_uri=f"agent://{claim.get('source_type', 'llm')}/{source_table}",
                observed_at=observed_at,
                known_at=known_at,
                evidence_tier=_cap_tier(claim),
                data_mode=data_mode,
            )
        )
    return tuple(items)


def proposal_cites_only_admissible_tiers(proposal: dict[str, Any], items: tuple[EvidenceItem, ...]) -> None:
    """A proposal may cite only verified/inferred claims (theme-researcher's own rule)."""
    by_id = {item.evidence_id.split(":", 1)[1]: item for item in items}
    for key in ("theme_proposals", "theme_holding_proposals"):
        for entry in proposal.get(key, []) or []:
            for cid in entry.get("evidence_citation_ids", []) or []:
                local = str(cid).split(":", 1)[-1]
                item = by_id.get(local)
                if item is None:
                    raise BoundaryError(f"{key} cites unknown evidence {cid!r}")
                if item.evidence_tier == "speculative":
                    raise BoundaryError(f"{key} cites speculative evidence {cid!r}")
