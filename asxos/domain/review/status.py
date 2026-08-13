"""The review-status vocabulary every portfolio/thesis review surface speaks.

Mission P1-04 (``docs/proposals/asxos-outcome-engine-and-arbi-second-brain-\
execution-plan-2026-08-12.md``, P1 required-work items 4 and 5). Two rules, both
mechanical:

**Item 4 — the only valid states are the four below.** ``CLEAR``, ``ATTENTION``,
``BLOCKED``, ``EVIDENCE_THIN``. A review surface reports the *state of the
evidence*, never a synthetic buy/add/trim/exit signal. The retired Model A
surfaces spoke a five-rung ranking ladder (``STRONG_BUY`` … ``STRONG_SELL``);
nothing replaces it, because the replacement of a discredited ranking model with
another ranking model is an explicit P1 non-goal. :func:`directive_terms` makes
the ban testable rather than aspirational.

**Item 5 — a missing input is an explicit unknown, never a fallback.** Every
:class:`ReviewOutcome` carries an ``unknowns`` tuple, and any non-empty
``unknowns`` forbids ``CLEAR``. The failure this closes is the quiet neutral: a
scorer with zero inputs returning "mixed, weighted +0.00%" reads exactly like a
measured neutral result, so an absence of evidence is presented as evidence of
absence. Under this module that same input set produces ``EVIDENCE_THIN`` with
the reason named.

**Model-independent by construction (CLAUDE.md rule #11).** This module imports
nothing from ``asxos.domain.models`` / ``asxos.domain.signals``, reads no
``signals`` / ``shap_factors`` / ``prob_up`` / ``expected_return`` /
``signals.regime``, and never calls ``resolve_production_model()``. It is pure —
no DB, no I/O, no clock. ``tests/test_review_status.py`` asserts the import
contract mechanically, in the style of
``tests/test_thesis_discipline.py::test_module_imports_are_model_independent``.

**s766B firewall** (``.claude/rules/portfolio-conventions.md``). A status is a
statement about *evidence quality*, addressed to the author of the theses being
reviewed. It is not a view on a holding's merit and carries no trade direction.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class ReviewStatus(StrEnum):
    """The complete set of verdicts a review surface may emit.

    ``clear``          — every check ran, nothing needs the governor's attention.
    ``attention``      — a well-evidenced finding the governor should look at.
    ``blocked``        — a check could not run at all; no view is available.
    ``evidence_thin``  — checks ran but the evidence base is too thin to say
                         ``clear`` honestly.
    """

    clear = "CLEAR"
    attention = "ATTENTION"
    blocked = "BLOCKED"
    evidence_thin = "EVIDENCE_THIN"


#: Trade-direction vocabulary that may never appear in a review verdict.
#:
#: FOUR of the five Model A signal labels are covered by construction:
#: ``STRONG_BUY`` / ``BUY`` / ``SELL`` / ``STRONG_SELL`` all reduce to ``buy`` or
#: ``sell`` under :func:`directive_terms`' boundary rule, so a reintroduced
#: ranking label trips the ban without needing its own entry. **``HOLD`` does
#: not match, deliberately**: on its own it carries no trade direction, and
#: banning it would fire on ordinary prose ("holdings", "hold the thesis open").
#: The consequence is worth stating plainly — a surface that reintroduced the
#: ladder and happened to print only ``HOLD`` rows would pass this check. The ban
#: is on directives, not a detector for ranking models.
DIRECTIVE_TERMS: frozenset[str] = frozenset(
    {
        "accumulate",
        "add",
        "buy",
        "divest",
        "exit",
        "liquidate",
        "overweight",
        "reduce",
        "sell",
        "short",
        "trim",
        "underweight",
    }
)

# Boundary rule: a term matches only as a whole word, but `_`, `-` and case
# changes do NOT protect it — `STRONG_BUY`, `strong-sell` and `Trim` all match,
# while `Holdings`, `buyer` and `exited_universe` do not. (`exited` is a
# different word from `exit`; the ban is on the imperative, not on prose about a
# past disposal.)
#
# `re.escape` is a no-op on today's pure-alpha terms and is here so it stays one:
# adding a term like "take profit(s)" or "buy/sell" later would otherwise change
# the pattern's meaning silently.
_DIRECTIVE_RE = re.compile(
    r"(?<![A-Za-z])("
    + "|".join(re.escape(t) for t in sorted(DIRECTIVE_TERMS))
    + r")(?![A-Za-z])",
    re.IGNORECASE,
)


def directive_terms(text: str) -> tuple[str, ...]:
    """Every banned trade-direction term in ``text``, lowercased and deduped.

    Empty tuple means the text is clean. Used by the adversarial tests to prove
    that the review-status surfaces emit no trade instruction.

    **Know what this is before promoting it to a runtime gate.** It is a
    literal-term ban, not a semantic one, and it is trivially evadable:
    "consider trimming", "take profits", "rotate out", "cut the position",
    "increase exposure" and "de-risk now" all come back clean. It also has live
    false positives — "short-term view" matches ``short``, and any three-letter
    ASX code that spells a banned term (``ADD.AU``) matches on the ticker. That
    is fine for tests over copy this repo controls; a runtime gate over
    free-form or externally-sourced text would need a different instrument.
    """
    return tuple(sorted({m.group(1).lower() for m in _DIRECTIVE_RE.finditer(text)}))


@dataclass(frozen=True)
class ReviewOutcome:
    """One review verdict plus the evidence that produced it.

    ``reasons`` and ``unknowns`` are both carried on every outcome regardless of
    ``status`` — collapsing to a single status must never discard the inputs, or
    an ``ATTENTION`` would silently swallow a co-occurring unknown.
    """

    status: ReviewStatus
    reasons: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    @property
    def is_clear(self) -> bool:
        return self.status is ReviewStatus.clear


def classify(
    *,
    blocking: Sequence[str] = (),
    attention: Sequence[str] = (),
    unknowns: Sequence[str] = (),
) -> ReviewOutcome:
    """Reduce three evidence buckets to exactly one :class:`ReviewStatus`.

    Precedence: ``BLOCKED`` > ``ATTENTION`` > ``EVIDENCE_THIN`` > ``CLEAR``.

    ``ATTENTION`` deliberately outranks ``EVIDENCE_THIN``: a finding that *did*
    compute is actionable now, and must not be masked because some unrelated
    input was unavailable. ``EVIDENCE_THIN`` sits directly above ``CLEAR`` for
    the mirror reason — ``CLEAR`` is only reachable when nothing is blocking,
    nothing needs attention, and nothing is unknown. "We did not find a problem"
    and "we could not look" are never the same answer.

    Deterministic and total: the same three sequences always yield the same
    outcome, and every input combination maps to exactly one status.
    """
    blocking_t = tuple(blocking)
    attention_t = tuple(attention)
    unknowns_t = tuple(unknowns)
    reasons = blocking_t + attention_t

    if blocking_t:
        status = ReviewStatus.blocked
    elif attention_t:
        status = ReviewStatus.attention
    elif unknowns_t:
        status = ReviewStatus.evidence_thin
    else:
        status = ReviewStatus.clear

    return ReviewOutcome(status=status, reasons=reasons, unknowns=unknowns_t)
