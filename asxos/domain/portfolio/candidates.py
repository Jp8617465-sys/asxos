"""The allocator's candidate source — model-independent seam (manifest A1/A2).

Until mission P1-04 this seam was a ``SELECT … FROM signals WHERE model = $1``
inside :meth:`PortfolioService.build`, i.e. Model A's daily output ranked five
ways. That read is retired. **Nothing was substituted for it**, and the absence
is deliberate:

* packet P1's non-goals bar *"replacing Model A with another ranking model"*, so
  a like-for-like swap is out of scope here by contract; and
* packet P1 required-work item 5 bars fallback assumptions — a synthesised,
  assumed, or last-known candidate set would let the allocator size real
  positions off numbers nobody produced.

So the seam declares itself unavailable, loudly and by a distinct exception type
(CLAUDE.md rule #10 — no ``logger.warning(...); continue`` on a capital path).

**This is not rule #11's enforcement point and must never be mistaken for it.**
The quarantine is enforced one step earlier, by the
``model_versions WHERE is_active AND approved_for_allocation`` gate in
``build.py`` (manifest E1) feeding
:func:`asxos.domain.models.production_gate.resolve_production_model` at
``required=True``. That gate runs *before* this loader is called and still
raises :class:`~asxos.domain.models.production_gate.ModelGateDormant` on zero
approved rows. Deleting this module would not disarm the quarantine; deleting
that gate would. The two hard-fails are independent and both must survive.

Replacing this stub is a separate, governed piece of work, and it is **not** a
one-file swap — claiming otherwise would badly understate it. A real source (the
Tier 2a screening evaluator in ``asxos/domain/screening/``, thesis-driven targets,
or both) returns :class:`AllocationCandidate` rows here, but that type still
carries the retired feed's schema and cannot be populated honestly without three
further changes:

* ``AllocationCandidate`` and ``AllocationTarget`` require ``signal_label`` (the
  five-rung ladder), ``prob_up`` and ``expected_return`` — ``types.py:172-200``.
* ``Profile.score_weights_json`` validates that its only two keys are
  ``prob_up``/``expected_return`` — ``types.py:129,143``.
* ``persist()`` writes all three into ``target_allocations`` — ``build.py``,
  and the columns are a migration.

Retiring those is the real precondition and is out of P1-04's scope. What P1-04
does guarantee is narrower and still worth having: **the read is behind one seam,
and the approval gate sits above it.** Three obligations came here with the seam
and belong to the replacement, not to ``build.py``:

* **60-day vol is required.** A symbol with insufficient price history is
  omitted from the candidate list — an intentional silent omission, documented
  in ``.claude/rules/portfolio-conventions.md``, and the one place in this
  pipeline where dropping a row quietly is correct (it cannot be sized, so it
  cannot be allocated).
* **Universe membership is required.** A candidate absent from ``universe`` has
  no sector and no market cap, so the constraint waterfall cannot bind it.
* **Recency must hard-fail, never warn** (plan H.1 CRITICAL-3). The retired
  feed's ">2 days stale" gate died with the feed; the replacement owes an
  equivalent assertion on its own evidence date, as a raise.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from asxos.domain.portfolio.types import AllocationCandidate


class CandidateSourceUnavailable(RuntimeError):
    """No candidate source is available to the allocator.

    A *distinctly named* subclass for the same reason
    :class:`~asxos.domain.models.production_gate.ModelGateDormant` is one: a
    deliberate, expected unavailability must be distinguishable from a crash, so
    an operator reading a traceback can tell "this is wired to nothing yet" from
    "this broke". It stays a ``RuntimeError`` subclass so every existing
    ``pytest.raises(RuntimeError)`` guard and every caller's error handling keeps
    working unchanged.

    **Known gap — ``JobMonitor`` cannot yet tell it apart.**
    ``asxos/jobs/utils/job_monitor.py`` maps only ``UpstreamBlocked`` and
    ``ModelGateDormant`` to ``job_runs.status='blocked'``; this type is not in
    that tuple, so a job reaching it records ``'failure'`` and pings
    Healthchecks. Latent today — the approval gate above this loader raises
    ``ModelGateDormant`` first while zero models are approved, so the weekly
    ``build_portfolio`` cron never gets here. It goes live the moment any model
    earns ``approved_for_allocation``. Deliberately not fixed in P1-04: that
    mapping is manifest row E4, an ``ENFORCEMENT_KEEP`` site. Add this name to
    the tuple in the same change that wires a real candidate source.
    """


async def load_allocation_candidates(
    conn: Any,
    *,
    approved_model: str,
    build_date: date,
    as_of: date | None = None,
) -> tuple[list[AllocationCandidate], date]:
    """Load the allocator's candidates, or fail loudly with an explicit state.

    Returns ``(candidates, candidates_as_of)`` — the second element is the date
    the candidate evidence is anchored on, which the caller records on the
    rebalance run.

    Today it always raises :class:`CandidateSourceUnavailable`. That is the
    honest state of the system, not a placeholder to be quietly softened: an
    empty list would flow into ``allocator.allocate()`` and surface as the
    generic "empty buy universe" error, and any non-empty stand-in would be
    fabricated.

    **``approved_model`` is for the message, and for nothing else.** It is the
    name ``build.py``'s approval gate resolved, threaded through so the failure
    text can say which approved model the retired feed belonged to. It is *not*
    a filter key. A replacement source that writes ``WHERE model = $1`` against
    it has re-created the Model A candidate query under a new name, which is the
    single most likely way to undo this retirement by accident — a
    model-independent source does not take a model as input, and this parameter
    should disappear from the signature the moment one is wired.
    """
    raise CandidateSourceUnavailable(
        "allocation is unavailable: no model-independent candidate source is "
        "wired. The Model A `signals` feed that supplied allocator candidates "
        "was retired by mission P1-04 (see docs/product/model-a-reference-"
        f"manifest.md, rows A1/A2). Approved-for-allocation model: {approved_model!r}; "
        f"requested candidates as_of="
        f"{as_of.isoformat() if as_of else 'latest'} for build date {build_date}. "
        "No candidate set is synthesised in its place — a fallback or assumed "
        "candidate set would size real positions off numbers nobody produced "
        "(packet P1 required-work item 5), and swapping in another ranking model "
        "is an explicit P1 non-goal. Wire a real model-independent source "
        "(asxos/domain/screening/ and/or thesis-driven targets) into "
        "asxos/domain/portfolio/candidates.py before running the allocator."
    )
