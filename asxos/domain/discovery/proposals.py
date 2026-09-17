"""Turning a passing screen result into a governance-queue row.

`ranker.passing` says which names cleared the four gates. This module says
which of those become `theses` rows at `pending_review`, what evidence they
carry, and what the row says about itself.

WHAT THIS MAY NOT DO, and why the constraints look odd until you know. The
sealed value-to-price test returned null (#304) and James's pre-committed
`RESPONSE_RULE` (`asxos/domain/research/registry/vp.py`) demotes the
residual-income model so it "stops emitting target prices, entry bands and
ranked 'opportunities'". So a proposal carries no `target_price`, no
`stop_price`, no entry band, and the set is never ordered by anything but
symbol.

That last one is why the volume controls below refuse rather than truncate. To
take the "best" five of sixteen you must rank them, and `ORDER BY symbol` then
take-five is a rank pretending not to be one — it silently drops eleven names
on an alphabetical accident. Both breakers therefore open *nothing* and say so,
which is honest and self-correcting: dispose of what is queued and the flow
resumes.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Final

from asxos.domain.discovery.ranker import (
    FLAG_ROE_AVERAGE_FALLBACK,
    MIN_ADV_AUD,
    MIN_MARKET_CAP_AUD,
)
from asxos.domain.discovery.types import Opportunity

#: How long a rejected or retired name is left alone before it may be proposed
#: again. The inputs move on a reporting cycle — PIT fundamentals refresh
#: quarterly and the quality gate uses a 3-period average ROE — so re-proposing
#: a declined name the following Saturday, on numerically identical evidence, is
#: the machine arguing with a decision rather than reporting a change. One
#: quarter is the shortest interval over which the evidence could honestly have
#: moved.
REPROPOSE_COOLDOWN_DAYS: Final[int] = 90

#: Runaway guard. If a run would open more than this, it opens NOTHING and
#: fails loudly (CLAUDE.md #10). A run trying to open 200 names means a gate
#: broke — a currency flag, a bad Ke, a half-finished fundamentals backfill —
#: and the right response is refusal and inspection, not a queue full of
#: garbage. Measured, not preferred: 16 names cleared every gate on the
#: 2026-09-16 sweep, so this is roughly twice observed flow.
MAX_OPENS_PER_RUN: Final[int] = 30

#: Queue-depth breaker. While at least this many proposals are already awaiting
#: review, a run opens nothing and records that it did. This is the
#: reviewability bound, and it drops the whole week rather than choosing which
#: names to drop. Note the natural half-life that makes it matter:
#: `thesis_evidence.retrieved_at` defaults to now, and `approve_object`
#: requires `accept_stale_evidence` past 14 days — so an unworked queue gets
#: harder to approve, by design.
MAX_OPEN_QUEUE: Final[int] = 25

#: Every symbol in the queue or on the book is suppressed; a declined one is
#: suppressed until the cooling-off passes. `governance_events.event_at` is the
#: only timestamp a rejection leaves — `apply_governance_transition` updates
#: `governance_status` alone and `closed_at` is set only by `exit_thesis`, so a
#: rejected row looks open forever if you test `closed_at` (the predicate this
#: replaces did exactly that, and would have suppressed every declined name
#: permanently and silently).
SQL_SUPPRESSED_SYMBOLS: Final[str] = """
SELECT DISTINCT t.symbol
FROM theses t
WHERE t.symbol = ANY($1::text[])
  AND (
        (t.closed_at IS NULL
         AND t.governance_status IN ('draft', 'evidence_complete', 'pending_review', 'approved'))
     OR (t.closed_at IS NOT NULL
         AND t.closed_at > NOW() - ($2::int * INTERVAL '1 day'))
     OR EXISTS (
          SELECT 1 FROM governance_events g
          WHERE g.object_type = 'thesis'
            AND g.object_id = t.thesis_id
            AND g.to_status IN ('rejected', 'retired')
            AND g.event_at > NOW() - ($2::int * INTERVAL '1 day')
        )
  )
"""

SQL_OPEN_QUEUE_DEPTH: Final[str] = (
    "SELECT count(*) AS n FROM theses "
    "WHERE governance_status = 'pending_review' AND closed_at IS NULL"
)


def evidence_tier_for(opportunity: Opportunity) -> str:
    """`verified` normally; `inferred` when the quality gate had to substitute.

    Every gate is computed from persisted, content-addressed rows — arithmetic,
    not judgement — which is `verified` in the 0033 vocabulary. The one honest
    exception is `roe_average_is_fallback`: there no 3-period average existed
    and trailing ROE stood in for it, which is inference in the strict sense.

    Both tiers are non-speculative, so neither blocks `approve_object`'s
    zero-evidence hard-fail. The distinction is visible to James at approval,
    which is the point.
    """
    return "inferred" if FLAG_ROE_AVERAGE_FALLBACK in opportunity.flags else "verified"


def evidence_citations_for(opportunity: Opportunity) -> list[str]:
    """Locate the evidence and prove it has not changed since.

    Shape follows `decision_engine/writeback.py`'s existing precedent
    (`["decision_packet:<id>", "content_hash:<hash>"]`) — "enough to replay
    exactly what was examined".

    All three, not a choice among them: `run_id` locates the valuation row,
    `content_hash` proves its contents are unchanged (an id alone cannot detect
    a recomputed run; a hash alone cannot find it), and the screening run is
    where gate 1 was actually decided — liquidity is not in the valuation row,
    so omitting it leaves one of the four gates uncited.
    """
    return [
        f"valuation_run:{opportunity.run_id}",
        f"content_hash:{opportunity.run_content_hash}",
        f"screening_run:{opportunity.screening_run_id}",
    ]


def thesis_text_for(opportunity: Opportunity) -> str:
    """What the row says about itself — a fixed template, never an LLM.

    The bar here is higher than "renders nicely". `build_decision_case` copies
    `thesis_text` VERBATIM into a decision packet as a `theme_fact`
    `EvidenceItem` at `evidence_tier="verified"`, so whatever this returns
    becomes a verified claim inside a challenged packet the moment James
    approves the thesis. It must therefore be a statement of what the machine
    did, fully reproducible from the cited run, containing no view.

    The closing sentence is the load-bearing one: it is what the packet's
    evidence claim will say about its own standing.
    """
    o = opportunity
    return (
        f"Cleared the value screen on {o.as_of.isoformat()}: "
        f"3-period average ROE {o.roe_average} above Ke mid {o.ke_mid}"
        f"{' (trailing ROE substituted; no average available)' if o.roe_average_is_fallback else ''}; "
        f"model value {o.value_registered} (registered convention) and "
        f"{o.value_average_roe} (average-ROE sensitivity) both at or above last close "
        f"{o.last_close} ({o.last_close_dt.isoformat()}); "
        f"90-day ADV {o.adv_aud} and market cap {o.market_cap_aud} above the liquidity floor "
        f"(ADV {MIN_ADV_AUD}, cap {MIN_MARKET_CAP_AUD}). "
        "No target, stop, entry band or ranking is stated — the residual-income model is a "
        "discipline device only (#304/#306). "
        "This row is a screen result awaiting review, not a view on the security."
    )


def evidence_rows_for(opportunity: Opportunity) -> list[dict[str, Any]]:
    """The two `thesis_evidence` rows a proposal needs to be approvable at all.

    `approve_object` hard-fails with NO override when a thesis has zero
    non-speculative `thesis_evidence` rows. A proposal carrying only the
    revision's `evidence_citations` would therefore be un-approvable — James
    could not action a single one — so these are not decoration.

    One row per evidence source, because the four gates were decided in two
    different places: the valuation run holds quality and value, the screening
    run holds liquidity.
    """
    o = opportunity
    tier = evidence_tier_for(o)
    return [
        {
            "source_table": "valuation_runs",
            "tier": tier,
            "claim_text": (
                f"{o.symbol}: residual-income value {o.value_registered} (registered) / "
                f"{o.value_average_roe} (average-ROE) against last close {o.last_close}; "
                f"ROE average {o.roe_average}, trailing {o.roe_trailing}, Ke mid {o.ke_mid}."
            ),
            "snapshot_data": {
                "run_id": o.run_id,
                "run_content_hash": o.run_content_hash,
                "as_of": o.as_of,
                "value_registered": o.value_registered,
                "value_average_roe": o.value_average_roe,
                "value_to_price_registered": o.value_to_price_registered,
                "value_to_price_average_roe": o.value_to_price_average_roe,
                "roe_trailing": o.roe_trailing,
                "roe_average": o.roe_average,
                "roe_average_is_fallback": o.roe_average_is_fallback,
                "ke_mid": o.ke_mid,
                "last_close": o.last_close,
                "last_close_dt": o.last_close_dt,
                "flags": list(o.flags),
            },
        },
        {
            "source_table": "screening_runs",
            "tier": "verified",
            "claim_text": (
                f"{o.symbol}: 90-day ADV {o.adv_aud} and market cap {o.market_cap_aud} "
                f"cleared the liquidity floor (ADV >= {MIN_ADV_AUD}, cap >= {MIN_MARKET_CAP_AUD}) "
                f"in screening run {o.screening_run_id}."
            ),
            "snapshot_data": {
                "screening_run_id": o.screening_run_id,
                "adv_aud": o.adv_aud,
                "market_cap_aud": o.market_cap_aud,
                "min_adv_aud": MIN_ADV_AUD,
                "min_market_cap_aud": MIN_MARKET_CAP_AUD,
            },
        },
    ]


def opening_reason_for(opportunity: Opportunity, *, as_of: date) -> str:
    """The `opened` revision's reasoning: the mechanism, not the content.

    `thesis_text` states what was measured; this states who measured it and
    from which rows, so the provenance is recoverable without re-reading the
    thesis prose.
    """
    return (
        f"Opened by jobs/discover_opportunities.py on {as_of.isoformat()} from "
        f"valuation run {opportunity.run_id} and screening run "
        f"{opportunity.screening_run_id}. Deterministic screen, no LLM. "
        "Enters at pending_review for human decision."
    )


class QueueFull(Exception):
    """Raised when the queue-depth breaker trips. Not an error condition."""


class RunawayScreen(RuntimeError):
    """Raised when a run would open implausibly many names. A broken gate."""


def selectable(
    passing: list[Opportunity],
    *,
    suppressed: set[str],
    open_queue_depth: int,
) -> list[Opportunity]:
    """The names this run should open, or an exception saying why none.

    Order is `ranker.passing`'s, which is symbol order. Nothing here reorders
    or truncates: both breakers refuse the whole run rather than choose.
    """
    if open_queue_depth >= MAX_OPEN_QUEUE:
        raise QueueFull(
            f"{open_queue_depth} proposals already awaiting review "
            f"(limit {MAX_OPEN_QUEUE}) — opening none this run"
        )
    fresh = [o for o in passing if o.symbol not in suppressed]
    if len(fresh) > MAX_OPENS_PER_RUN:
        raise RunawayScreen(
            f"{len(fresh)} names would be opened, above the {MAX_OPENS_PER_RUN} "
            "runaway guard — opening none; a gate is probably broken"
        )
    return fresh
