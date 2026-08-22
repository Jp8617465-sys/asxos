"""The one frozen-model base every ``asxos.secondbrain`` schema builds on.

Extracted 2026-08-22 during SB3-01's review loop, after ``context.py`` became
the **fourth** module to declare an identical ``ConfigDict(extra="forbid",
frozen=True)`` -- three as a private ``_FrozenModel`` base (``project_state``,
``execution``, ``context``) and one inline on the model itself
(``contradictions.Contradiction``). Byte-identical every time, and no module
had ever referenced another's.

The justification originally written into ``context.py`` for keeping a local
copy -- that sharing a base would couple a future config change across
independently-versioned freezes -- **is wrong on the mechanics**, and is
recorded here rather than quietly dropped. Pydantic resolves ``model_config``
through the MRO and lets any subclass override it, so a schema that genuinely
needs different config declares its own ``model_config`` and gets it. Sharing
this base costs a schema nothing and buys the package a single place to change
what "frozen" means.

Why that matters more than tidiness: with four copies, a decision to strengthen
the freeze (say, adding ``validate_assignment=True``) has to be applied four
times, and the one that gets missed is a *silently weaker* freeze on a schema
that still claims to be frozen. That is the failure this consolidation removes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    """Closed field set (``extra="forbid"``) + immutable instances (``frozen=True``).

    ``extra="forbid"`` is the mechanical half of every freeze rule in this
    package -- an input carrying a field the schema does not name fails
    validation rather than being silently retained. ``frozen=True`` gives
    snapshot semantics: once constructed, an observation cannot be mutated.

    Deep immutability of nested ``JsonValue`` payloads is NOT enforced --
    convention, not contract.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
