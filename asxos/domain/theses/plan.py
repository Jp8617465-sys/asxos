"""Does a thesis state a price plan? One predicate, two callers, no drift.

`build_decision_case` refuses to build a packet for a thesis with no price plan
(`decision_engine/builder.py`) — without a reference price, a stop and a target
there are no honest bull/bear scenario returns to state, and inventing them is
the failure rule #11 exists about.

`jobs/build_decision_packets.py` needs the *same* question answered *before* it
tries, so it can leave such a thesis out of the nightly set rather than
collecting a failure for it every night. That is not a style preference: the
job's failure note lands in `job_runs.error_message`, which `check_cron_health`
turns into an alert, so a permanently unplanned thesis would page nightly
forever (issue #327 is that exact shape, and migration 0059's eleven rows were
its first instance).

Two copies of this condition would drift, and the drift would be invisible
until a night went red. Hence one function, taking values rather than a
`Thesis`, so the job can call it on a query row without loading the aggregate.
"""
from __future__ import annotations

from decimal import Decimal


def has_price_plan(
    *,
    entry_band_lower: Decimal | None,
    entry_band_upper: Decimal | None,
    stop_price: Decimal | None,
    target_price: Decimal | None,
    actual_entry_price: Decimal | None,
) -> bool:
    """True when the thesis states enough for a scenario return to be derived.

    Mirrors `build_decision_case`'s two guards exactly:

    * a **reference price** — either a complete entry band (the midpoint is
      used) or an `actual_entry_price` on an entered thesis, which substitutes
      for the band;
    * **both** a stop and a target, which are the bear and bull legs. A
      reference price with only one of them is still not a plan.
    """
    reference = actual_entry_price is not None or (
        entry_band_lower is not None and entry_band_upper is not None
    )
    return reference and stop_price is not None and target_price is not None
