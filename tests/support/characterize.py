"""Characterization-snapshot helper — pin a function's output shape before refactoring.

Before this existed the repo's entire snapshot surface was three brief-HTML files
(``tests/golden/brief/*.html``, byte-compared by ``test_brief_stage0.py``) covering a
22-module domain layer. That is a thin net to refactor against, and thinner still for
a behaviour-preserving change where "the tests pass" is the only evidence offered.

Snapshots here go through ``asxos.serde.canonical.to_canonical``, so Decimals stay
exact strings, dates are ISO, and an unencodable type raises rather than falling back
to ``repr()`` — a ``repr()`` fallback would embed memory addresses and make two runs
over identical data differ, which destroys the only property a snapshot has.

**A snapshot is a change detector, not a correctness proof.** It says the output is
what it was, never that it was right. Snapshot the output of code you believe is
already correct, then refactor. Never record a snapshot to "make the test pass" on
code whose output you have not read.

Usage::

    from tests.support.characterize import assert_matches_snapshot

    def test_allocation_shape():
        assert_matches_snapshot(build_something(...), "allocation/basic")

First run with ``ASXOS_UPDATE_SNAPSHOTS=1`` writes the file; commit it and read the
diff. Later runs compare. A deliberate change means re-recording and reviewing the
diff in the PR — which is the point: the diff is the behaviour change, made visible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from asxos.serde.canonical import to_canonical

GOLDEN_ROOT = Path(__file__).resolve().parent.parent / "golden"
UPDATE_ENV = "ASXOS_UPDATE_SNAPSHOTS"


def canonical_json(value: object) -> str:
    """Stable JSON for ``value`` — sorted keys, 2-space indent, trailing newline.

    ``sort_keys`` is what makes the snapshot independent of dict construction
    order, so an unrelated refactor that reorders field assignment does not
    produce a spurious diff.
    """
    return json.dumps(to_canonical(value, context="snapshot"), indent=2, sort_keys=True) + "\n"


def snapshot_path(name: str) -> Path:
    """Resolve a snapshot name like ``"allocation/basic"`` to a path under tests/golden."""
    return GOLDEN_ROOT / f"{name}.json"


def assert_matches_snapshot(value: object, name: str) -> None:
    """Compare ``value`` against the recorded snapshot ``name``.

    Raises ``AssertionError`` on mismatch, with the recorded and actual JSON in the
    message. With ``ASXOS_UPDATE_SNAPSHOTS=1`` set, records instead of comparing and
    fails loudly so a recording run is never mistaken for a passing one.
    """
    path = snapshot_path(name)
    actual = canonical_json(value)

    if os.environ.get(UPDATE_ENV) == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        raise AssertionError(
            f"{UPDATE_ENV}=1 — recorded {path}. Unset it, review the diff, and re-run."
        )

    if not path.exists():
        raise AssertionError(
            f"no snapshot at {path}. Record it with {UPDATE_ENV}=1, then review the diff "
            f"before committing — never record a snapshot you have not read."
        )

    expected = path.read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(
            f"snapshot mismatch for {name!r} ({path}).\n"
            f"If this change is intended, re-record with {UPDATE_ENV}=1 and justify the "
            f"diff in the PR.\n\n--- recorded ---\n{expected}\n--- actual ---\n{actual}"
        )
