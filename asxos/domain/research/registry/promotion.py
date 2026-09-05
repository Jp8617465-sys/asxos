"""Paper promotion state machine — the Stage 2 capital boundary, in code.

States: research → paper_candidate → paper → retired (retired is reachable
from every state; nothing is reachable from retired).

There is no capital state. Not "gated", not "requires approval" — absent.
`advance()` cannot be asked for one because the type does not admit one, and
the matching CHECK constraints in migration 0050 refuse it at the database.
A strategy that has earned `paper` reaches capital only when a human writes
a governed thesis through the decision engine, which is where rule #11 and
the s766B firewall already live.
"""
from __future__ import annotations

from typing import Final, Literal

PromotionState = Literal["research", "paper_candidate", "paper", "retired"]
PROMOTION_STATES: Final[tuple[PromotionState, ...]] = (
    "research", "paper_candidate", "paper", "retired",
)

# Every legal edge. Anything not listed is refused.
_TRANSITIONS: Final[frozenset[tuple[PromotionState, PromotionState]]] = frozenset(
    {
        ("research", "paper_candidate"),
        ("paper_candidate", "paper"),
        ("paper_candidate", "research"),   # demote: evidence did not hold
        ("paper", "research"),             # demote: live paper behaviour diverged
        ("research", "retired"),
        ("paper_candidate", "retired"),
        ("paper", "retired"),
    }
)

# Named so a grep proves the absence, and a test can assert it.
FORBIDDEN_TARGET_WORDS: Final[tuple[str, ...]] = (
    "capital", "live", "allocat", "approved", "production", "deploy",
)


class PromotionError(ValueError):
    """An illegal transition. Never silently coerced."""


def advance(
    current: PromotionState,
    to: PromotionState,
    *,
    evidence_run_id: str | None,
    reason: str,
) -> PromotionState:
    """Return `to` if the edge is legal; raise otherwise.

    Promotion (toward `paper`) requires an evidence run id — a demotion or a
    retirement does not, because the absence of evidence is itself the reason.
    """
    if current not in PROMOTION_STATES or to not in PROMOTION_STATES:
        raise PromotionError(f"unknown state in transition {current!r} -> {to!r}")
    if any(word in str(to).lower() for word in FORBIDDEN_TARGET_WORDS):
        raise PromotionError(f"{to!r} is not a research state and never will be")
    if (current, to) not in _TRANSITIONS:
        raise PromotionError(f"illegal transition {current!r} -> {to!r}")
    if not reason.strip():
        raise PromotionError("a transition needs a reason")
    promoting = (current, to) in {("research", "paper_candidate"), ("paper_candidate", "paper")}
    if promoting and not evidence_run_id:
        raise PromotionError(f"promotion {current!r} -> {to!r} requires an evidence run id")
    return to
