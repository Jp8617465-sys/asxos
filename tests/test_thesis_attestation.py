"""Attestation gates + alert framing (0042: D4/R9, KD-2/KD-3; fixtures BB /
LK / TR / PB from the design's test plan §9).

Service-level attest/enter/revise gates with mocked conns, plus the pure
alert builder. The DB CHECK rejection paths (attestation-gated ladder CHECK,
underwritten-requires-basis) are verified in the rolled-back LIVE replay of
0042 at apply time — mocked conns don't enforce CHECKs (the 0034 trigger
lesson in portfolio-conventions.md).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from asxos.domain.portfolio.locks import LockState
from asxos.domain.theses import service as svc
from asxos.domain.theses.alerts import build_invalidation_alert

_NOW = datetime(2026, 8, 7, tzinfo=UTC)
_DUE = _NOW + timedelta(days=30)


def _thesis_row(**over):
    row = {
        "thesis_id": 1,
        "symbol": "CBA.AU",
        "status": "watching",
        "thesis_text": "Rate cycle play",
        "entry_band_lower": Decimal("42.000000"),
        "entry_band_upper": Decimal("45.000000"),
        "stop_price": Decimal("38.000000"),
        "target_price": Decimal("60.000000"),
        "timeline_days": 540,
        "themes": [],
        "actual_entry_price": None,
        "actual_entry_at": None,
        "actual_exit_price": None,
        "actual_exit_at": None,
        "last_revisited_at": _NOW,
        "revisit_due_at": _DUE,
        "opened_at": _NOW,
        "closed_at": None,
        "governance_status": "approved",
        "attestation": "placeholder",
        "attestation_basis": None,
    }
    row.update(over)
    return row


class _Conn:
    def __init__(self, fetchrow=None, fetch=None):
        self.calls: list[tuple[str, str, tuple]] = []
        self._fetchrow = iter(fetchrow or [])
        self._fetch = iter(fetch or [])

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetchrow(self, q, *a):
        self.calls.append(("fetchrow", q, a))
        return next(self._fetchrow, None)

    async def fetch(self, q, *a):
        self.calls.append(("fetch", q, a))
        return next(self._fetch, [])

    async def execute(self, q, *a):
        self.calls.append(("execute", q, a))
        return "UPDATE 1" if "UPDATE" in q else "INSERT 0 1"


def _execs(conn, needle):
    return [(q, a) for m, q, a in conn.calls if m == "execute" and needle in q]


# ---------------------------------------------------------------------------
# attest_thesis — the underwriting gate
# ---------------------------------------------------------------------------

async def test_attest_happy_path_writes_update_and_revision():
    existing = _thesis_row()
    price = {"close": Decimal("44.00"), "dt": date(2026, 8, 6)}
    updated = _thesis_row(attestation="underwritten", attestation_basis="Q3 report basis")
    conn = _Conn(fetchrow=[existing, price, updated], fetch=[[]])

    t = await svc.attest_thesis(
        conn, 1, to="underwritten", basis="Q3 report basis", reasoning="Underwriting"
    )
    assert t.attestation == "underwritten"
    assert t.attestation_basis == "Q3 report basis"
    _q, args = _execs(conn, "thesis_revisions")[0]
    assert args[2] == "attestation_change"


async def test_attest_born_breached_stop_hard_fails():
    """BB fixture: stop >= latest close → cannot attest."""
    existing = _thesis_row(stop_price=Decimal("38.000000"))
    price = {"close": Decimal("37.50"), "dt": date(2026, 8, 6)}
    conn = _Conn(fetchrow=[existing, price])
    with pytest.raises(ValueError, match="BORN_BREACHED"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_stop_equal_to_close_is_breached():
    existing = _thesis_row(stop_price=Decimal("38.000000"))
    price = {"close": Decimal("38.000000"), "dt": date(2026, 8, 6)}
    conn = _Conn(fetchrow=[existing, price])
    with pytest.raises(ValueError, match="BORN_BREACHED"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_with_stop_but_no_price_history_refuses():
    """Conservative reading: an unverifiable stop cannot be underwritten."""
    existing = _thesis_row()
    conn = _Conn(fetchrow=[existing, None])
    with pytest.raises(ValueError, match="no price history"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_point_band_hard_fails():
    """PB fixture: degenerate lower==upper refused at underwrite (placeholder
    status IS the explicit attestation of 'not a real band' — divergence #4)."""
    existing = _thesis_row(
        entry_band_lower=Decimal("42.000000"), entry_band_upper=Decimal("42.000000")
    )
    conn = _Conn(fetchrow=[existing])
    with pytest.raises(ValueError, match="BAND_DEGENERATE"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_incoherent_ladder_hard_fails():
    # HUBS-shaped: stop above the band.
    existing = _thesis_row(
        stop_price=Decimal("230"), entry_band_lower=Decimal("185"),
        entry_band_upper=Decimal("190"), target_price=Decimal("260"),
    )
    conn = _Conn(fetchrow=[existing])
    with pytest.raises(ValueError, match="LADDER_INCOHERENT"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_requires_basis():
    conn = _Conn(fetchrow=[_thesis_row()])
    with pytest.raises(ValueError, match="basis"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="  ", reasoning="r")


async def test_attest_stale_baseline_drift_hard_fails():
    """A condition whose stored baseline no longer matches the current parser
    cannot ride through an attest — the enforced promise changes only by
    human re-authoring."""
    existing = _thesis_row()
    price = {"close": Decimal("44.00"), "dt": date(2026, 8, 6)}
    drifted_cond = {
        "condition_id": 9, "ordinal": 1,
        "condition_text": "Price closes below $230 stop on volume",
        "enforcement_kind": "price_above",  # stored baseline disagrees with cp-1
        "enforcement_threshold": Decimal("230.000000"),
        "parser_version": "cp-0",
    }
    conn = _Conn(fetchrow=[existing, price], fetch=[[drifted_cond]])
    with pytest.raises(ValueError, match="baseline drifted"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning="r")


async def test_attest_demotion_always_allowed_and_clears_basis():
    existing = _thesis_row(attestation="underwritten", attestation_basis="old basis")
    updated = _thesis_row(attestation="placeholder", attestation_basis=None)
    conn = _Conn(fetchrow=[existing, updated])
    t = await svc.attest_thesis(
        conn, 1, to="placeholder", reasoning="Numbers under review"
    )
    assert t.attestation == "placeholder"
    update_calls = [
        (q, a) for m, q, a in conn.calls if m == "fetchrow" and "SET attestation" in q
    ]
    assert update_calls
    _q, args = update_calls[0]
    assert args[0] == "placeholder"
    assert args[1] is None  # a stale basis must never imply underwriting


async def test_attest_noop_transition_rejected():
    conn = _Conn(fetchrow=[_thesis_row(attestation="placeholder")])
    with pytest.raises(ValueError, match="already"):
        await svc.attest_thesis(conn, 1, to="placeholder", reasoning="r")


async def test_attest_requires_reasoning():
    conn = _Conn()
    with pytest.raises(ValueError, match="reasoning is required"):
        await svc.attest_thesis(conn, 1, to="underwritten", basis="b", reasoning=" ")


# ---------------------------------------------------------------------------
# enter_thesis — capital never deploys against a placeholder (BB fixture)
# ---------------------------------------------------------------------------

async def test_enter_thesis_placeholder_hard_fails_naming_the_cli_path():
    existing = _thesis_row(status="watching", attestation="placeholder")
    conn = _Conn(fetchrow=[existing])
    with pytest.raises(ValueError, match="asx thesis attest"):
        await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43"))


async def test_enter_thesis_underwritten_succeeds():
    existing = _thesis_row(
        status="watching", attestation="underwritten", attestation_basis="b"
    )
    updated = _thesis_row(
        status="active", attestation="underwritten", attestation_basis="b",
        actual_entry_price=Decimal("43.5"), actual_entry_at=_NOW,
    )
    conn = _Conn(fetchrow=[existing, updated])
    t = await svc.enter_thesis(conn, thesis_id=1, entry_price=Decimal("43.5"))
    assert t.status == "active"


# ---------------------------------------------------------------------------
# open_thesis / revise_thesis — placeholders visibly wrong, never blocked
# ---------------------------------------------------------------------------

async def test_open_thesis_placeholder_with_born_breached_stop_succeeds():
    """BB fixture, other half: opening as a placeholder never consults the BB
    gate — the numbers are visibly junk and barred from action surfaces
    instead (the CLI echoes the lint)."""
    row = _thesis_row(stop_price=Decimal("999"))
    conn = _Conn(fetchrow=[row])
    t = await svc.open_thesis(conn, "CBA.AU", stop_price=Decimal("999"))
    assert t.attestation == "placeholder"
    # No prices query was ever issued on the placeholder path.
    assert all("FROM prices" not in q for _m, q, _a in conn.calls)


async def test_revise_ladder_field_on_underwritten_thesis_hard_fails_incoherent():
    existing = _thesis_row(attestation="underwritten", attestation_basis="b")
    conn = _Conn(fetchrow=[existing])
    with pytest.raises(ValueError, match="incoherent"):
        await svc.revise_thesis(
            conn, 1, "stop_price", Decimal("50"), "tightening stop above band"
        )


async def test_revise_ladder_field_on_placeholder_is_not_gated():
    existing = _thesis_row(attestation="placeholder")
    updated = _thesis_row(attestation="placeholder", stop_price=Decimal("50"))
    conn = _Conn(fetchrow=[existing, updated])
    t = await svc.revise_thesis(
        conn, 1, "stop_price", Decimal("50"), "incremental repair step 1"
    )
    assert t.stop_price == Decimal("50")


# ---------------------------------------------------------------------------
# build_invalidation_alert — action framing (BB / LK / TR fixtures)
# ---------------------------------------------------------------------------

_EVENT = {
    "price_date": date(2026, 8, 6),
    "observed_close": Decimal("200.00"),
    "threshold": Decimal("230.000000"),
}


def _alert(attestation="underwritten", semantics="hard_exit", lock=None):
    return build_invalidation_alert(
        thesis={"symbol": "HUBS.NYSE", "thesis_id": 2, "attestation": attestation},
        condition={
            "condition_text": "Price closes below $230 stop on volume",
            "trigger_semantics": semantics,
        },
        event=_EVENT,
        lock=lock,
    )


def test_tr_underwritten_hard_exit_unlocked_is_action_framed():
    a = _alert()
    assert a.action_framed is True
    assert "Run: asx thesis exit HUBS.NYSE" in a.body
    # Price-date provenance on the face and in the subject (never run date).
    assert "2026-08-06" in a.body
    assert a.subject.endswith("2026-08-06")


def test_bb_placeholder_alert_is_review_framed_with_reason_on_face():
    a = _alert(attestation="placeholder")
    assert a.action_framed is False
    assert "asx thesis exit" not in a.body
    assert "PLACEHOLDER — not underwritten" in a.body


def test_lk_locked_indefinitely_demotes_with_lock_on_face():
    lock = LockState(symbol="HUBS.NYSE", lock_end=None, lock_note="ESS trading window locked")
    a = _alert(lock=lock)
    assert a.action_framed is False
    assert "asx thesis exit" not in a.body
    assert "INSTRUMENT LOCKED (end unknown) — review only" in a.body
    assert "ESS trading window locked" in a.body


def test_lk_locked_with_future_end_date_states_the_date():
    lock = LockState(symbol="HUBS.NYSE", lock_end=date(2026, 12, 31), lock_note="ESS window")
    a = _alert(lock=lock)
    assert a.action_framed is False
    assert "INSTRUMENT LOCKED (until 2026-12-31) — review only" in a.body


def test_lk_expired_lock_restores_action_framing():
    """A past-dated lock never reaches the builder — get_disposal_locks
    filters on lock_end >= as_of, so the builder sees lock=None and the
    underwritten hard_exit framing is restored."""
    a = _alert(lock=None)
    assert a.action_framed is True


def test_alert_review_semantics_review_framed_even_underwritten_unlocked():
    a = _alert(semantics="alert_review")
    assert a.action_framed is False
    assert "asx thesis exit" not in a.body
    assert "alert_review semantics — review only" in a.body


def test_alert_body_is_html_escaped():
    a = build_invalidation_alert(
        thesis={"symbol": "HUBS.NYSE", "thesis_id": 2, "attestation": "placeholder"},
        condition={
            "condition_text": "<script>alert(1)</script> below $230",
            "trigger_semantics": "hard_exit",
        },
        event=_EVENT,
        lock=None,
    )
    assert "<script>" not in a.body
    assert "&lt;script&gt;" in a.body


# ---------------------------------------------------------------------------
# _row_to_thesis mapping
# ---------------------------------------------------------------------------

def test_row_to_thesis_maps_attestation_fields():
    t = svc._row_to_thesis(_thesis_row(attestation="underwritten", attestation_basis="b"))
    assert t.attestation == "underwritten"
    assert t.attestation_basis == "b"


def test_row_to_thesis_defaults_attestation_placeholder_when_absent():
    row = _thesis_row()
    del row["attestation"]
    del row["attestation_basis"]
    # dict.get fallback path — mirrors pre-apply rows in synthetic tests.
    row_get = MagicMock()
    row_get.__getitem__ = lambda _self, k: row[k]
    row_get.get = lambda k, default=None: row.get(k, default)
    t = svc._row_to_thesis(row_get)
    assert t.attestation == "placeholder"
    assert t.attestation_basis is None
