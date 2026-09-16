"""Tests for asxos/domain/theses/service.py — M-Thesis-1.

Mocks asyncpg connections; no real DB required.
Covers all hard-fail paths and the Decimal serialisation contract.

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.theses import service as svc
from asxos.domain.theses.types import Thesis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=30)


def _make_thesis_row(
    thesis_id: int = 1,
    symbol: str = "CBA.AU",
    status: str = "watching",
    thesis_text: str | None = "Rate cycle play — NIM expansion when RBA cuts",
    entry_band_lower: Decimal | None = Decimal("42.000000"),
    entry_band_upper: Decimal | None = Decimal("45.000000"),
    stop_price: Decimal | None = Decimal("38.000000"),
    target_price: Decimal | None = Decimal("60.000000"),
    timeline_days: int | None = 540,
    actual_entry_price: Decimal | None = None,
    actual_entry_at: datetime | None = None,
    actual_exit_price: Decimal | None = None,
    actual_exit_at: datetime | None = None,
    governance_status: str = "approved",
) -> dict:
    """Return a dict shaped like an asyncpg theses row."""
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "status": status,
        "thesis_text": thesis_text,
        "entry_band_lower": entry_band_lower,
        "entry_band_upper": entry_band_upper,
        "stop_price": stop_price,
        "target_price": target_price,
        "timeline_days": timeline_days,
        "invalidation_conditions": [],
        "themes": [],
        "actual_entry_price": actual_entry_price,
        "actual_entry_at": actual_entry_at,
        "actual_exit_price": actual_exit_price,
        "actual_exit_at": actual_exit_at,
        "last_revisited_at": _NOW,
        "revisit_due_at": _DUE,
        "opened_at": _NOW,
        "closed_at": None,
        "governance_status": governance_status,
    }


def _make_conn(
    fetchrow_returns: list | None = None,
    fetch_returns: list | None = None,
) -> MagicMock:
    """Return a mock asyncpg connection.

    fetchrow_returns: list of values returned on successive fetchrow() calls.
    fetch_returns:    list of values returned on successive fetch() calls.
    """

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.execute = AsyncMock(return_value=None)

    fr_side = iter(fetchrow_returns or [])
    fc_side = iter(fetch_returns or [[]])

    async def _fetchrow(_q, *_args):
        return next(fr_side, None)

    async def _fetch(_q, *_args):
        return next(fc_side, [])

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    return conn


# ---------------------------------------------------------------------------
# 1. open_thesis — happy path
# ---------------------------------------------------------------------------

async def test_open_thesis_happy_path() -> None:
    row = _make_thesis_row(
        thesis_text="Rate cycle play — NIM expansion when RBA cuts"
    )
    conn = _make_conn(fetchrow_returns=[row])

    t = await svc.open_thesis(
        conn, "CBA.AU",
        status="watching",
        thesis_text="Rate cycle play — NIM expansion when RBA cuts",
        stop_price=Decimal("38"),
        target_price=Decimal("60"),
        timeline_days=540,
        reasoning="Opening position on thesis",
    )

    assert isinstance(t, Thesis)
    assert t.symbol == "CBA.AU"
    assert t.status == "watching"
    assert t.thesis_id == 1


async def test_open_thesis_theme_placeholder_born_draft_not_approved() -> None:
    """Phase 2a security-review finding F-2: the system_default placeholder
    INSERT must set governance_status='draft' EXPLICITLY — omitting it lands
    the row at the migration-0035 column DEFAULT 'approved', recreating the
    exact laundered unreviewed-placeholder-as-approved state that migration
    0035's own backfill exists to prevent (and seeding the
    governed_active_theme_holdings read surface with unreviewed exposure)."""
    row = _make_thesis_row()
    theme_row = {"theme_id": 7}
    execute_calls: list[tuple[str, tuple]] = []

    conn = _make_conn(fetchrow_returns=[row, theme_row])

    async def _execute(q, *args):
        execute_calls.append((q, args))

    conn.execute = _execute

    await svc.open_thesis(
        conn, "CBA.AU",
        themes=["big-4-banks"],
        reasoning="Opening with a theme link",
    )

    placeholder_inserts = [
        (q, a) for q, a in execute_calls if "INSERT INTO theme_holdings" in q
    ]
    assert len(placeholder_inserts) == 1
    query = placeholder_inserts[0][0]
    assert "'system_default'" in query
    assert "'draft'" in query, (
        "system_default placeholder INSERT must explicitly set "
        "governance_status='draft' — the column DEFAULT is 'approved'"
    )


# ---------------------------------------------------------------------------
# 2. open_thesis — symbol validation
# ---------------------------------------------------------------------------

async def test_open_thesis_invalid_symbol_no_suffix_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match=r"must end with .AU or .US"):
        await svc.open_thesis(conn, "MIN")


async def test_open_thesis_invalid_suffix_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match=r"must end with .AU or .US"):
        await svc.open_thesis(conn, "MIN.ASX")


async def test_open_thesis_us_symbol_accepted() -> None:
    row = _make_thesis_row(symbol="NVDA.US")
    conn = _make_conn(fetchrow_returns=[row])
    t = await svc.open_thesis(conn, "NVDA.US")
    assert t.symbol == "NVDA.US"


# ---------------------------------------------------------------------------
# 3. enter_thesis — sets active + actual_entry_price
# ---------------------------------------------------------------------------

async def test_enter_thesis_sets_active() -> None:
    existing = _make_thesis_row(status="watching", actual_entry_price=None)
    updated = _make_thesis_row(
        status="active",
        actual_entry_price=Decimal("43.500000"),
        actual_entry_at=_NOW,
    )
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43.50"), qty=100)

    assert t.status == "active"
    assert t.actual_entry_price == Decimal("43.500000")


# ---------------------------------------------------------------------------
# 4. enter_thesis — hard-fail: no thesis_text
# ---------------------------------------------------------------------------

async def test_enter_thesis_no_thesis_text_raises() -> None:
    existing = _make_thesis_row(status="watching", thesis_text=None)
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="thesis_text is empty"):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_empty_thesis_text_raises() -> None:
    existing = _make_thesis_row(status="watching", thesis_text="")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="thesis_text is empty"):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


# ---------------------------------------------------------------------------
# 5. enter_thesis — hard-fail: already active / exited
# ---------------------------------------------------------------------------

async def test_enter_thesis_already_active_raises() -> None:
    existing = _make_thesis_row(status="active")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"status is .active."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_exited_raises() -> None:
    existing = _make_thesis_row(status="exited")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"status is .exited."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


# ---------------------------------------------------------------------------
# 6. revise_thesis — stop_price update + stop_adjusted revision
# ---------------------------------------------------------------------------

async def test_revise_thesis_stop() -> None:
    existing = _make_thesis_row(stop_price=Decimal("38.000000"))
    updated = _make_thesis_row(stop_price=Decimal("36.000000"))
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.revise_thesis(
        conn, thesis_id=1, field="stop_price", value=Decimal("36"), reasoning="Widening stop"
    )

    assert t.stop_price == Decimal("36.000000")


# ---------------------------------------------------------------------------
# 7. revise_thesis — hard-fail: unknown field
# ---------------------------------------------------------------------------

async def test_revise_thesis_invalid_field_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="not revisable"):
        await svc.revise_thesis(
            conn, thesis_id=1,
            field="arbitrary_column_injection",
            value="DROP TABLE theses",
            reasoning="test",
        )


# ---------------------------------------------------------------------------
# 8. revise_thesis — Decimal diff is string-serialised (no float)
# ---------------------------------------------------------------------------

async def test_revise_thesis_writes_decimal_diff_as_string() -> None:
    """diff JSONB must contain str representations, not floats."""
    existing = _make_thesis_row(stop_price=Decimal("38.000000"))
    updated = _make_thesis_row(stop_price=Decimal("36.000000"))
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    await svc.revise_thesis(
        conn, thesis_id=1, field="stop_price", value=Decimal("36"), reasoning="test"
    )

    # Find the INSERT INTO thesis_revisions call
    revision_calls = [(q, a) for q, a in execute_calls if "thesis_revisions" in q]
    assert revision_calls, "No revision INSERT found"

    # The diff arg is the 4th parameter (index 3): thesis_id, revised_at, type, diff, reasoning
    import json
    diff_json = revision_calls[0][1][3]  # 4th positional arg = diff JSON string
    diff = json.loads(diff_json)
    assert "stop_price" in diff
    old_val = diff["stop_price"]["old"]
    new_val = diff["stop_price"]["new"]
    # Must be parseable as Decimal — not float-formatted
    assert Decimal(old_val) == Decimal("38.000000")
    assert Decimal(new_val) == Decimal("36")
    # Must not have float precision artifacts
    assert "e" not in old_val.lower()
    assert "e" not in new_val.lower()


# ---------------------------------------------------------------------------
# 9. review_thesis — no field change; reviewed_no_change revision written
# ---------------------------------------------------------------------------

async def test_review_thesis_no_field_change() -> None:
    existing_id_row = {"thesis_id": 1}
    updated = _make_thesis_row()
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx

    fr_returns = iter([existing_id_row, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    t = await svc.review_thesis(conn, thesis_id=1, reasoning="Thesis intact; waiting for catalyst")

    assert isinstance(t, Thesis)
    # Check revision was written with correct type
    revision_calls = [(q, a) for q, a in execute_calls if "thesis_revisions" in q]
    assert revision_calls
    revision_type = revision_calls[0][1][2]  # 3rd positional arg = revision_type
    assert revision_type == "reviewed_no_change"

    import json
    diff_json = revision_calls[0][1][3]
    diff = json.loads(diff_json)
    assert diff == {}  # empty diff for no-change review


async def test_review_thesis_empty_reasoning_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.review_thesis(conn, thesis_id=1, reasoning="")


async def test_review_thesis_whitespace_reasoning_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.review_thesis(conn, thesis_id=1, reasoning="   ")


# ---------------------------------------------------------------------------
# 10. exit_thesis — sets exited + actual_exit_price + closed_at
# ---------------------------------------------------------------------------

async def test_exit_thesis_sets_exited() -> None:
    existing = _make_thesis_row(status="active", actual_entry_price=Decimal("43"))
    updated = _make_thesis_row(
        status="exited",
        actual_entry_price=Decimal("43"),
        actual_exit_price=Decimal("58.000000"),
        actual_exit_at=_NOW,
    )
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.exit_thesis(
        conn, thesis_id=1, exit_price=Decimal("58"),
        revision_type="exited", reasoning="Target approached, taking profit",
    )

    assert t.status == "exited"
    assert t.actual_exit_price == Decimal("58.000000")


# ---------------------------------------------------------------------------
# 11. exit_thesis — hard-fail: already exited
# ---------------------------------------------------------------------------

async def test_exit_thesis_already_exited_raises() -> None:
    existing = _make_thesis_row(status="exited")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"already .exited."):
        await svc.exit_thesis(conn, thesis_id=1, exit_price=Decimal("58"))


async def test_exit_thesis_already_expired_raises() -> None:
    existing = _make_thesis_row(status="expired")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"already .expired."):
        await svc.exit_thesis(conn, thesis_id=1, exit_price=Decimal("40"))


# ---------------------------------------------------------------------------
# 12. exit_thesis — hard-fail: invalid revision_type
# ---------------------------------------------------------------------------

async def test_exit_thesis_invalid_revision_type_raises() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="revision_type must be one of"):
        await svc.exit_thesis(
            conn, thesis_id=1, exit_price=Decimal("58"),
            revision_type="wrong_type",
        )


# ---------------------------------------------------------------------------
# Migration 0026 — conviction_level + tax_notes
# ---------------------------------------------------------------------------


def test_conviction_and_tax_fields_revisable_and_in_sync():
    """conviction_level + tax_notes (0026) must be revisable and the two
    revision maps must stay in sync (revise_thesis indexes both)."""
    from asxos.domain.theses.types import (
        _REVISION_TYPE_FOR_FIELD,
        REVISABLE_FIELDS,
    )

    for f in ("conviction_level", "tax_notes"):
        assert f in REVISABLE_FIELDS
        assert f in _REVISION_TYPE_FOR_FIELD
    # every revisable field must have a revision type, else revise_thesis KeyErrors
    assert set(REVISABLE_FIELDS) == set(_REVISION_TYPE_FOR_FIELD)


def test_row_to_thesis_maps_conviction_and_tax():
    """The new columns round-trip from a Record-shaped row into the dataclass,
    and default cleanly when absent (older rows)."""
    row = _make_thesis_row()
    row["conviction_level"] = 4
    row["tax_notes"] = "CGT-discount-eligible after 2027-06; fully franked"
    t = svc._row_to_thesis(row)
    assert t.conviction_level == 4
    assert "franked" in t.tax_notes

    # absent columns (pre-0026 row) default to None / "" without error
    t2 = svc._row_to_thesis(_make_thesis_row())
    assert t2.conviction_level is None
    assert t2.tax_notes == ""


# ---------------------------------------------------------------------------
# Migration 0033/0034 — governance_status guard on enter_thesis()
# ---------------------------------------------------------------------------

async def test_enter_thesis_unapproved_governance_status_raises() -> None:
    """A thesis with complete thesis_text/stop/target but governance_status
    != 'approved' must still hard-fail — this is the capital-risk gate
    (design doc Section 4.7 layer 3)."""
    existing = _make_thesis_row(status="watching", governance_status="draft")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"governance_status is .draft."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_pending_review_governance_status_raises() -> None:
    existing = _make_thesis_row(status="watching", governance_status="pending_review")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"governance_status is .pending_review."):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_approved_governance_status_succeeds() -> None:
    """Explicit positive-path test — entry succeeds BECAUSE governance_status
    is 'approved', not merely as an accidental side effect of the fixture
    default. Guards against the default silently changing later without
    this invariant being caught."""
    existing = _make_thesis_row(status="watching", governance_status="approved")
    updated = _make_thesis_row(
        status="active",
        actual_entry_price=Decimal("43.500000"),
        actual_entry_at=_NOW,
        governance_status="approved",
    )
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43.50"), qty=100)

    assert t.status == "active"
    assert t.governance_status == "approved"


# ---------------------------------------------------------------------------
# Migration 0033/0034 — approve_object()
# ---------------------------------------------------------------------------

def _evidence_row(tier: str, retrieved_at: datetime) -> dict:
    return {"tier": tier, "retrieved_at": retrieved_at}


async def test_approve_object_happy_path() -> None:
    existing = _make_thesis_row(governance_status="pending_review")
    updated = _make_thesis_row(governance_status="approved")
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _fetch(_q, *_args):
        # Real "now", not the fixture's fixed historical _NOW — approve_object()
        # computes its own now() via _now_utc() to check staleness against, so
        # "1 day old" must be 1 day before the real clock, not before _NOW.
        return [_evidence_row("verified", datetime.now(tz=UTC) - timedelta(days=1))]

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    conn.execute = _execute

    t = await svc.approve_object(conn, thesis_id=1, reasoning="Evidence checks out")

    assert t.governance_status == "approved"
    gov_calls = [(q, a) for q, a in execute_calls if "governance_events" in q]
    assert len(gov_calls) == 1
    # INSERT params are ($1=object_type, $2=object_id, $3=from_status,
    # $4=to_status, $5=reasoning, $6=actor) — Phase 2a's shared
    # governance.transitions.apply_governance_transition() binds all six
    # (this file's own version previously inlined 'thesis'/'human' as SQL
    # literals; the shared helper serves multiple tables/actors, so both
    # are bind params now).
    assert gov_calls[0][1][4] == "Evidence checks out"  # reasoning param


async def test_approve_object_all_speculative_evidence_raises() -> None:
    """Explicitly named in the Phase 1 done-criteria: 'a thesis with only
    speculative evidence is rejected before pending_review is ever
    reached' (design doc Section 9, verification item 3)."""
    existing = _make_thesis_row(governance_status="pending_review")

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.fetchrow = AsyncMock(return_value=existing)
    conn.fetch = AsyncMock(
        return_value=[_evidence_row("speculative", _NOW - timedelta(days=1))]
    )

    with pytest.raises(ValueError, match="no non-speculative evidence"):
        await svc.approve_object(conn, thesis_id=1, reasoning="test")


async def test_approve_object_zero_evidence_rows_raises() -> None:
    existing = _make_thesis_row(governance_status="pending_review")

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.fetchrow = AsyncMock(return_value=existing)
    conn.fetch = AsyncMock(return_value=[])

    with pytest.raises(ValueError, match="no non-speculative evidence"):
        await svc.approve_object(conn, thesis_id=1, reasoning="test")


async def test_approve_object_stale_evidence_without_override_raises() -> None:
    existing = _make_thesis_row(governance_status="pending_review")

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn.fetchrow = AsyncMock(return_value=existing)
    conn.fetch = AsyncMock(
        return_value=[_evidence_row("verified", _NOW - timedelta(days=20))]
    )

    with pytest.raises(ValueError, match="older than 14 days"):
        await svc.approve_object(conn, thesis_id=1, reasoning="test")


async def test_approve_object_stale_evidence_with_override_succeeds_and_logs_second_event() -> None:
    existing = _make_thesis_row(governance_status="pending_review")
    updated = _make_thesis_row(governance_status="approved")
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _fetch(_q, *_args):
        return [_evidence_row("verified", _NOW - timedelta(days=20))]

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.fetch = _fetch
    conn.execute = _execute

    t = await svc.approve_object(
        conn, thesis_id=1, reasoning="Approving anyway",
        accept_stale_evidence="Macro thesis still intact despite old citation",
    )

    assert t.governance_status == "approved"
    gov_calls = [(q, a) for q, a in execute_calls if "governance_events" in q]
    assert len(gov_calls) == 2  # the approval event AND the override event
    override_call = [
        c for c in gov_calls
        if any("Macro thesis still intact" in str(arg) for arg in c[1])
    ]
    assert override_call, "override reasoning was not logged as its own event"


async def test_approve_object_wrong_governance_status_raises() -> None:
    existing = _make_thesis_row(governance_status="draft")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"governance_status is .draft."):
        await svc.approve_object(conn, thesis_id=1, reasoning="test")


async def test_approve_object_empty_reasoning_raises() -> None:
    existing = _make_thesis_row(governance_status="pending_review")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.approve_object(conn, thesis_id=1, reasoning="")


# ---------------------------------------------------------------------------
# Migration 0033/0034 — reject_object()
# ---------------------------------------------------------------------------

async def test_reject_object_happy_path() -> None:
    existing = _make_thesis_row(governance_status="pending_review")
    updated = _make_thesis_row(governance_status="rejected")
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    t = await svc.reject_object(conn, thesis_id=1, reasoning="Evidence doesn't support catalyst")

    assert t.governance_status == "rejected"
    gov_calls = [(q, a) for q, a in execute_calls if "governance_events" in q]
    assert len(gov_calls) == 1


async def test_reject_object_empty_reasoning_raises() -> None:
    existing = _make_thesis_row(governance_status="pending_review")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.reject_object(conn, thesis_id=1, reasoning="")


async def test_reject_object_already_approved_raises() -> None:
    existing = _make_thesis_row(governance_status="approved")
    conn = _make_conn(fetchrow_returns=[existing])

    with pytest.raises(ValueError, match=r"governance_status is .approved."):
        await svc.reject_object(conn, thesis_id=1, reasoning="test")


# ---------------------------------------------------------------------------
# retire_object — the complement of reject_object (2026-09-17)
# ---------------------------------------------------------------------------


async def test_retire_object_happy_path_writes_the_event_before_the_update() -> None:
    """The 0034 trigger is BEFORE UPDATE, so the governance_events INSERT must
    already be visible when the UPDATE fires. Pinned by call ORDER, not just count —
    the same shape that caught the Phase 2a bug."""
    existing = _make_thesis_row(governance_status="approved")
    updated = _make_thesis_row(governance_status="retired")
    ordered: list[str] = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(query, *_args):
        if "UPDATE theses" in query:
            ordered.append("update")
        return next(fr_returns, None)

    async def _execute(query, *_args):
        if "governance_events" in query:
            ordered.append("insert")

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    t = await svc.retire_object(conn, thesis_id=1, reasoning="Served out; superseded")

    assert t.governance_status == "retired"
    assert ordered == ["insert", "update"], "INSERT must precede UPDATE (transitions.py)"


async def test_retire_object_records_the_from_status_and_actor() -> None:
    existing = _make_thesis_row(governance_status="approved")
    updated = _make_thesis_row(governance_status="retired")
    calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr = iter([existing, updated])

    async def _fetchrow(_q, *_a):
        return next(fr, None)

    async def _execute(query, *args):
        calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    await svc.retire_object(conn, thesis_id=1, reasoning="Auto-seeded placeholder, never authored")
    (_, args), = [(q, a) for q, a in calls if "governance_events" in q]
    assert args[0] == "thesis" and args[1] == 1
    assert args[2] == "approved" and args[3] == "retired"
    assert args[5] == "human"


async def test_retire_object_refuses_a_row_that_was_never_approved() -> None:
    """pending_review belongs to reject_object. Retire is for a DECIDED row."""
    for status in ("pending_review", "draft", "evidence_complete", "rejected", "retired"):
        conn = _make_conn(fetchrow_returns=[_make_thesis_row(governance_status=status)])
        with pytest.raises(ValueError, match="expected one of"):
            await svc.retire_object(conn, thesis_id=1, reasoning="test")


async def test_retire_object_empty_reasoning_raises() -> None:
    conn = _make_conn(fetchrow_returns=[_make_thesis_row(governance_status="approved")])
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.retire_object(conn, thesis_id=1, reasoning="   ")


async def test_retire_object_missing_thesis_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.retire_object(conn, thesis_id=999, reasoning="test")


async def test_retire_and_reject_source_states_are_disjoint() -> None:
    """The two verbs must not both accept the same state — that would make
    'was this ever accepted?' unanswerable from the audit trail alone."""
    assert not (svc._RETIREABLE_FROM & svc._REJECTABLE_FROM)
    assert svc._RETIREABLE_FROM == {"approved"}


async def test_reject_object_from_draft_succeeds() -> None:
    """draft is a valid source state for rejection, not just pending_review."""
    existing = _make_thesis_row(governance_status="draft")
    updated = _make_thesis_row(governance_status="rejected")
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.reject_object(conn, thesis_id=1, reasoning="Bad proposal")

    assert t.governance_status == "rejected"


# ---------------------------------------------------------------------------
# Migration 0033 — governance_status defaulting / row mapping
# ---------------------------------------------------------------------------

def test_row_to_thesis_defaults_governance_status_when_absent():
    """A pre-0033 row-shaped dict (no governance_status key) round-trips to
    'approved' via .get() fallback, not a KeyError."""
    row = _make_thesis_row()
    del row["governance_status"]
    t = svc._row_to_thesis(row)
    assert t.governance_status == "approved"


def test_row_to_thesis_maps_governance_status_when_present():
    row = _make_thesis_row(governance_status="rejected")
    t = svc._row_to_thesis(row)
    assert t.governance_status == "rejected"


# ---------------------------------------------------------------------------
# Migration 0040 — report_sections (Phase C broker-report thesis)
# ---------------------------------------------------------------------------

def test_row_to_thesis_without_report_sections_key_defaults_empty():
    """Backward compatibility: a pre-migration-0040 row (no report_sections
    key at all — _make_thesis_row() is not modified for this test) parses
    to an empty tuple, not an error."""
    row = _make_thesis_row()
    assert "report_sections" not in row
    t = svc._row_to_thesis(row)
    assert t.report_sections == ()


def test_parse_report_sections_none_returns_empty_tuple() -> None:
    assert svc._parse_report_sections(None) == ()


def test_parse_report_sections_roundtrip_preserves_decimal_exactness() -> None:
    """The exact write serializer (model_dump(mode='json') -> json.dumps)
    piped through the exact read parser must not lose Decimal precision —
    this is the regression the brief-truth mission's −75.7% bug (a different
    module, but the same class of silent-precision-loss risk) exists to
    guard against here too."""
    from asxos.domain.theses.schemas import ReportFigure, ReportSection

    section = ReportSection(
        kind="valuation",
        body="DCF-derived fair value.",
        figures=[
            ReportFigure(
                label="Fair value",
                value=Decimal("123456789012.123456"),
                provenance="james_input",
            )
        ],
    )
    import json

    sections_json = json.dumps([section.model_dump(mode="json")])
    result = svc._parse_report_sections(sections_json)

    assert len(result) == 1
    assert result[0].figures[0].value == Decimal("123456789012.123456")


async def test_add_report_section_new_kind_happy_path() -> None:
    existing = _make_thesis_row()
    updated = {
        **_make_thesis_row(),
        "report_sections": [
            {
                "kind": "moat",
                "body": "Durable network effects in the CRM ecosystem.",
                "figures": [],
                "evidence_citation_ids": [],
            }
        ],
    }
    conn = _make_conn(fetchrow_returns=[existing, updated])

    t = await svc.add_report_section(
        conn, thesis_id=1, kind="moat",
        body="Durable network effects in the CRM ecosystem.",
        figures=[],
        reasoning="Initial moat write-up",
    )

    assert len(t.report_sections) == 1
    assert t.report_sections[0].kind == "moat"


async def test_add_report_section_replaces_existing_kind() -> None:
    """Upsert by kind, not append — a second write to the same kind replaces
    it wholesale; the prior content survives only in the revision diff."""
    old_moat = {
        "kind": "moat", "body": "Old moat text.", "figures": [], "evidence_citation_ids": [],
    }
    new_moat_body = "New, sharper moat text."
    existing = {**_make_thesis_row(), "report_sections": [old_moat]}
    updated = {
        **_make_thesis_row(),
        "report_sections": [
            {"kind": "moat", "body": new_moat_body, "figures": [], "evidence_citation_ids": []}
        ],
    }
    execute_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _execute(query, *args):
        execute_calls.append((query, args))

    conn.fetchrow = _fetchrow
    conn.execute = _execute

    t = await svc.add_report_section(
        conn, thesis_id=1, kind="moat", body=new_moat_body, figures=[], reasoning="Sharpened",
    )

    assert len(t.report_sections) == 1
    assert t.report_sections[0].body == new_moat_body

    import json

    revision_calls = [(q, a) for q, a in execute_calls if "thesis_revisions" in q]
    assert revision_calls
    diff = json.loads(revision_calls[0][1][3])
    assert diff["report_sections"]["old"]["body"] == "Old moat text."
    assert diff["report_sections"]["new"]["body"] == new_moat_body


async def test_add_report_section_invalid_kind_raises_value_error() -> None:
    conn = _make_conn()
    with pytest.raises(ValueError, match="not a valid section kind"):
        await svc.add_report_section(conn, thesis_id=1, kind="not_a_real_kind", body="Text.")


async def test_add_report_section_thesis_not_found_raises_value_error() -> None:
    conn = _make_conn()  # empty fetchrow_returns -> first call returns None
    with pytest.raises(ValueError, match="not found"):
        await svc.add_report_section(conn, thesis_id=999, kind="moat", body="Text.")


async def test_add_report_section_reuses_prose_only_guard() -> None:
    """Proves reuse, not reimplementation, of schemas.py's _body_prose_only —
    a capital-relevant number inline in prose must be rejected."""
    conn = _make_conn()
    with pytest.raises(ValueError, match="prose-only"):
        await svc.add_report_section(
            conn, thesis_id=1, kind="valuation", body="Fair value is $130 per share.",
        )


async def test_add_report_section_advances_revisit_due() -> None:
    """Recording a section is a discipline event like revise_thesis()/
    review_thesis() — it computes and writes fresh last_revisited_at/
    revisit_due_at, same as every other thesis-content mutator in this
    module. Inspects the actual UPDATE call args (not just the mocked
    RETURNING row) so this proves the function computed the values, not
    just that _row_to_thesis can map them back."""
    existing = _make_thesis_row()
    updated = {**_make_thesis_row(), "report_sections": []}
    fetchrow_calls: list = []

    @asynccontextmanager
    async def _tx():
        yield

    conn = MagicMock()
    conn.transaction = _tx
    fr_returns = iter([existing, updated])

    async def _fetchrow(query, *args):
        fetchrow_calls.append((query, args))
        return next(fr_returns, None)

    conn.fetchrow = _fetchrow
    conn.execute = AsyncMock(return_value=None)

    await svc.add_report_section(conn, thesis_id=1, kind="moat", body="Text.", figures=[])

    update_calls = [(q, a) for q, a in fetchrow_calls if "UPDATE theses" in q]
    assert update_calls
    # args = (sections_json, now, due, thesis_id) per the UPDATE's $1..$4.
    _sections_json, now, due, _thesis_id = update_calls[0][1]
    assert isinstance(now, datetime)
    assert isinstance(due, datetime)
    assert due - now == timedelta(days=30)  # _REVISIT_INTERVAL_DAYS


async def test_add_report_section_reuses_monitor_only_basis_guard() -> None:
    """Proves reuse, not reimplementation, of schemas.py's
    _check_monitor_placement — a rule #11 Model A monitor_only figure may
    never land in a basis section (moat is one)."""
    from asxos.domain.theses.schemas import ReportFigure

    conn = _make_conn()
    monitor_fig = ReportFigure(
        label="Model A prob_up", value=Decimal("0.6"),
        provenance="james_input", monitor_only=True,
    )
    with pytest.raises(ValueError, match="monitor_only"):
        await svc.add_report_section(
            conn, thesis_id=1, kind="moat", body="Text.", figures=[monitor_fig],
        )


# ---------------------------------------------------------------------------
# Migration 0033/0034 — create_thesis_from_agent_run() documented stub
# ---------------------------------------------------------------------------

async def test_create_thesis_from_agent_run_no_thesis_proposal_schema_raises() -> None:
    """Confirms the documented Phase 1/2 gap fails loudly, not silently.
    See asxos/domain/theses/schemas.py module docstring and
    service.py::create_thesis_from_agent_run()'s docstring."""
    run_row = {
        "run_id": 7,
        "agent_name": "test-agent",
        "acted_on": False,
        "object_type": "thesis",
        "proposed_object": '{"some": "data"}',
    }
    conn = _make_conn(fetchrow_returns=[run_row])

    with pytest.raises(ValueError, match="no ThesisProposal Pydantic schema exists"):
        await svc.create_thesis_from_agent_run(conn, run_id=7, symbol="CBA.AU")


async def test_create_thesis_from_agent_run_not_found_raises() -> None:
    conn = _make_conn(fetchrow_returns=[None])
    with pytest.raises(ValueError, match="not found"):
        await svc.create_thesis_from_agent_run(conn, run_id=999, symbol="CBA.AU")


async def test_create_thesis_from_agent_run_already_acted_on_raises() -> None:
    run_row = {
        "run_id": 7, "agent_name": "test-agent", "acted_on": True,
        "object_type": "thesis", "proposed_object": "{}",
    }
    conn = _make_conn(fetchrow_returns=[run_row])
    with pytest.raises(ValueError, match="already acted on"):
        await svc.create_thesis_from_agent_run(conn, run_id=7, symbol="CBA.AU")


async def test_create_thesis_from_agent_run_wrong_object_type_raises() -> None:
    run_row = {
        "run_id": 7, "agent_name": "test-agent", "acted_on": False,
        "object_type": "macro_thesis", "proposed_object": "{}",
    }
    conn = _make_conn(fetchrow_returns=[run_row])
    with pytest.raises(ValueError, match="only accepts object_type='thesis'"):
        await svc.create_thesis_from_agent_run(conn, run_id=7, symbol="CBA.AU")


# ---------------------------------------------------------------------------
# Phase 1 done-criteria — synthetic end-to-end governance state machine
# (draft -> evidence_complete -> pending_review -> approved -> entered),
# constructed via a manually-inserted pending_review row rather than
# through create_thesis_from_agent_run() (documented stub — see above).
# This satisfies design-doc Section 4.8 stage 2 ("proves the state machine
# is correct end-to-end") without requiring ThesisProposal to exist.
# ---------------------------------------------------------------------------

async def test_phase1_done_criteria_draft_to_entered_end_to_end() -> None:
    """Synthetic agent-originated thesis (manually constructed at
    governance_status='pending_review') advances through approve_object()
    and then enter_thesis() successfully, proving the governance state
    machine mechanics end-to-end per design doc Section 4.8 stage 2 /
    Section 7's Phase 1 done criteria."""
    draft_row = _make_thesis_row(thesis_id=99, governance_status="pending_review")
    approved_row = _make_thesis_row(thesis_id=99, governance_status="approved")
    active_row = _make_thesis_row(
        thesis_id=99, status="active", governance_status="approved",
        actual_entry_price=Decimal("43.500000"), actual_entry_at=_NOW,
    )

    @asynccontextmanager
    async def _tx():
        yield

    approve_conn = MagicMock()
    approve_conn.transaction = _tx
    fr_returns = iter([draft_row, approved_row])

    async def _fetchrow(_q, *_args):
        return next(fr_returns, None)

    async def _fetch(_q, *_args):
        # Real "now", not the fixture's fixed historical _NOW — see the
        # matching comment in test_approve_object_happy_path.
        return [_evidence_row("verified", datetime.now(tz=UTC) - timedelta(days=1))]

    approve_conn.fetchrow = _fetchrow
    approve_conn.fetch = _fetch
    approve_conn.execute = AsyncMock(return_value=None)

    approved = await svc.approve_object(
        approve_conn, thesis_id=99, reasoning="Verified evidence supports thesis"
    )
    assert approved.governance_status == "approved"

    enter_conn = _make_conn(fetchrow_returns=[approved_row, active_row])
    entered = await svc.enter_thesis(
        enter_conn, thesis_id=99, entry_price=Decimal("43.50")
    )
    assert entered.status == "active"
    assert entered.governance_status == "approved"


async def test_phase1_done_criteria_speculative_only_never_reaches_pending_review() -> None:
    """The other half of the Phase 1 done criteria: 'a thesis with only
    speculative evidence is rejected before pending_review is ever
    reached.' Since Phase 1's create_thesis_from_agent_run() stub never
    successfully creates a row (see the dedicated stub test above), the
    only way a speculative-only thesis could reach 'approved' is via
    approve_object() directly — and that is exactly what
    test_approve_object_all_speculative_evidence_raises already proves
    fails. This test is a thin restatement making the done-criteria
    traceability explicit, not new logic."""
    existing = _make_thesis_row(governance_status="pending_review")
    conn = _make_conn(fetchrow_returns=[existing], fetch_returns=[[]])

    with pytest.raises(ValueError, match="no non-speculative evidence"):
        await svc.approve_object(conn, thesis_id=1, reasoning="attempt")


# ---------------------------------------------------------------------------
# Migration 0033 — Decimal-string contract for agent proposal JSONB fields
# ---------------------------------------------------------------------------

def test_theme_holding_proposal_exposure_strength_never_becomes_float() -> None:
    """Decimal fields in agent proposals must never round-trip through
    float — matches the existing _serialise() contract (CLAUDE.md
    non-negotiable #5)."""
    from asxos.domain.theses.schemas import ThemeHoldingProposal

    p = ThemeHoldingProposal(
        theme_code="ai-infrastructure",
        symbol="NVDA.US",
        exposure_strength=Decimal("0.653421"),
        direction="positive",
        mechanism_text="Direct beneficiary of AI datacentre capex cycle",
        evidence_citation_ids=[1],
    )
    dumped = p.model_dump(mode="json")
    assert isinstance(dumped["exposure_strength"], str)  # never float in JSON mode
    assert Decimal(dumped["exposure_strength"]) == Decimal("0.653421")
    assert "e" not in dumped["exposure_strength"].lower()  # no float sci-notation artifacts


def test_theme_holding_proposal_exposure_strength_out_of_range_raises() -> None:
    from pydantic import ValidationError

    from asxos.domain.theses.schemas import ThemeHoldingProposal

    with pytest.raises(ValidationError):
        ThemeHoldingProposal(
            theme_code="test", symbol="NVDA.US",
            exposure_strength=Decimal("1.5"),  # > 1, invalid
            direction="positive", mechanism_text="test",
            evidence_citation_ids=[1],
        )


def test_macro_thesis_proposal_requires_at_least_one_evidence_citation() -> None:
    from pydantic import ValidationError

    from asxos.domain.theses.schemas import MacroThesisProposal

    with pytest.raises(ValidationError):
        MacroThesisProposal(
            title="Test", thesis_text="Test thesis",
            regime_quadrant="rising_growth_rising_inflation",
            horizon_months=12, catalyst="Test catalyst", falsifier="Test falsifier",
            evidence_citation_ids=[],  # empty — must fail min_length=1
        )


def test_theme_proposal_theme_code_pattern_enforced() -> None:
    from pydantic import ValidationError

    from asxos.domain.theses.schemas import ThemeProposal

    with pytest.raises(ValidationError):
        ThemeProposal(
            theme_code="Invalid Theme Code!",  # uppercase + spaces + punctuation, invalid
            name="Test", description="Test", conviction_band="medium",
            stage="early", evidence_citation_ids=[1],
        )
