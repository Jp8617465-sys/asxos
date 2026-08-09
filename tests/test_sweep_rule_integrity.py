"""Tests for jobs/sweep_rule_integrity.py — the R8 weekly sweep (0042, D7).

Pins: fingerprint dedupe (re-runs are quiet), the E05-class tape replay
(missed transitions repaired with source='sweep' + correct price_dates),
PARSE_DRIFT under a simulated cp-2 (baseline never auto-changed; silent
parser_version refresh when the baseline matches), FROZEN_VALUE_DRIFT on the
50d MA, the no-anchor conservatism, the SP stale-tape guard, and the
watching/research live-rule scope (register #22 — the CBA blind spot).
"""
from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest

import jobs.sweep_rule_integrity as sweep

AS_OF = date(2026, 8, 8)


class _RoutedConn:
    """Routes fetch/fetchrow/fetchval/execute by query substring; records an
    ordered call log. Unrouted reads return None/[]; unrouted writes succeed."""

    def __init__(self, routes: list[tuple[str, str, Any]] | None = None):
        self.routes = routes or []
        self.calls: list[tuple[str, str, tuple]] = []

    @asynccontextmanager
    async def transaction(self):
        yield

    def _route(self, method: str, q: str, a: tuple):
        for m, sub, res in self.routes:
            if m == method and sub in q:
                return res(a) if callable(res) else res
        return None

    async def fetchrow(self, q, *a):
        self.calls.append(("fetchrow", q, a))
        return self._route("fetchrow", q, a)

    async def fetchval(self, q, *a):
        self.calls.append(("fetchval", q, a))
        return self._route("fetchval", q, a)

    async def fetch(self, q, *a):
        self.calls.append(("fetch", q, a))
        return self._route("fetch", q, a) or []

    async def execute(self, q, *a):
        self.calls.append(("execute", q, a))
        routed = self._route("execute", q, a)
        if routed is not None:
            return routed
        return "INSERT 0 1" if "INSERT" in q else "UPDATE 1"


def _execs(conn, needle):
    return [(q, a) for m, q, a in conn.calls if m == "execute" and needle in q]


def _thesis(**over) -> dict[str, Any]:
    # Coherent ladder by default (stop < lower < upper < target) so lint
    # writes no flags unless a test constructs an incoherent one on purpose.
    row = {
        "thesis_id": 2,
        "symbol": "HUBS.NYSE",
        # watching by default: active+placeholder would (correctly) fire the
        # UNATTESTED_WITH_CAPITAL flag — pinned in its own test below.
        "status": "watching",
        "attestation": "placeholder",
        "stop_price": Decimal("180.000000"),
        "entry_band_lower": Decimal("185.000000"),
        "entry_band_upper": Decimal("190.000000"),
        "target_price": Decimal("260.000000"),
    }
    row.update(over)
    return row


def _cond(**over) -> dict[str, Any]:
    row = {
        "condition_id": 5,
        "thesis_id": 2,
        "ordinal": 1,
        "condition_text": "Price closes below $230 stop on volume",
        "status": "triggered",
        "enforcement_kind": "price_below",
        "enforcement_threshold": Decimal("230.000000"),
        "parser_version": "cp-1",
    }
    row.update(over)
    return row


# ---------------------------------------------------------------------------
# Fingerprint dedupe — re-runs are quiet
# ---------------------------------------------------------------------------

def test_fingerprint_is_stable_and_16_hex():
    fp1 = sweep._fingerprint({"a": Decimal("1.5"), "b": date(2026, 8, 8)})
    fp2 = sweep._fingerprint({"b": date(2026, 8, 8), "a": Decimal("1.5")})
    assert fp1 == fp2  # sort_keys — insertion order can't change identity
    assert len(fp1) == 16
    assert fp1 != sweep._fingerprint({"a": Decimal("1.6"), "b": date(2026, 8, 8)})


async def test_write_flag_skips_when_newest_flag_has_same_fingerprint():
    detail = {"x": "1"}
    fp = sweep._fingerprint(detail)
    conn = _RoutedConn(routes=[
        ("fetchrow", "integrity_flag",
         {"diff": {"flag": {"code": "BORN_BREACHED", "fingerprint": fp}}}),
    ])
    wrote = await sweep._write_flag(conn, 2, "BORN_BREACHED", detail, "msg")
    assert wrote is False
    assert _execs(conn, "thesis_revisions") == []


async def test_write_flag_writes_when_fingerprint_differs():
    conn = _RoutedConn(routes=[
        ("fetchrow", "integrity_flag",
         {"diff": {"flag": {"code": "BORN_BREACHED", "fingerprint": "deadbeefdeadbeef"}}}),
    ])
    wrote = await sweep._write_flag(conn, 2, "BORN_BREACHED", {"x": "1"}, "msg")
    assert wrote is True
    (_q, args), = _execs(conn, "thesis_revisions")
    assert "integrity_flag" in _q or "integrity_flag" in str(args)


# ---------------------------------------------------------------------------
# Tape replay — the E05 class (register #6)
# ---------------------------------------------------------------------------

_E05_CLOSES = [
    {"dt": date(2026, 7, 20), "close": Decimal("245.00")},  # recapture
    {"dt": date(2026, 7, 21), "close": Decimal("200.00")},  # re-breach
    {"dt": date(2026, 7, 28), "close": Decimal("246.00")},  # recapture
    {"dt": date(2026, 8, 6), "close": Decimal("199.00")},   # re-breach
]


async def test_replay_reconstructs_e05_sequence_with_sweep_provenance():
    conn = _RoutedConn(routes=[
        ("fetchrow", "thesis_condition_events", {"price_date": date(2026, 7, 2)}),
        ("fetch", "FROM prices", _E05_CLOSES),
    ])
    written, missed = await sweep._replay_condition(conn, _cond(), "HUBS.NYSE", AS_OF)

    assert [(m["event_type"], m["price_date"]) for m in missed] == [
        ("re_armed", date(2026, 7, 20)),
        ("triggered", date(2026, 7, 21)),
        ("re_armed", date(2026, 7, 28)),
        ("triggered", date(2026, 8, 6)),
    ]
    assert written == 4
    event_inserts = _execs(conn, "thesis_condition_events")
    assert len(event_inserts) == 4
    assert all("'sweep'" in q for q, _a in event_inserts)
    assert all("ON CONFLICT" in q for q, _a in event_inserts)
    # Final replayed state == stored 'triggered' → no status UPDATE needed.
    assert _execs(conn, "UPDATE thesis_conditions") == []


async def test_replay_repairs_final_status_with_guarded_update():
    conn = _RoutedConn(routes=[
        ("fetchrow", "thesis_condition_events", {"price_date": date(2026, 7, 2)}),
        ("fetch", "FROM prices", [_E05_CLOSES[0]]),  # one recapture only
    ])
    written, missed = await sweep._replay_condition(conn, _cond(), "HUBS.NYSE", AS_OF)
    assert written == 1
    assert missed[0]["event_type"] == "re_armed"
    (q, args), = _execs(conn, "UPDATE thesis_conditions")
    assert args == ("re_armed", 5, "triggered")  # from-status guard in WHERE


async def test_replay_idempotent_rerun_writes_zero_events():
    conn = _RoutedConn(routes=[
        ("fetchrow", "thesis_condition_events", {"price_date": date(2026, 7, 2)}),
        ("fetch", "FROM prices", _E05_CLOSES),
        ("execute", "thesis_condition_events", "INSERT 0 0"),  # all conflict
    ])
    written, missed = await sweep._replay_condition(conn, _cond(), "HUBS.NYSE", AS_OF)
    assert len(missed) == 4  # detected again…
    assert written == 0      # …but 0 duplicate events (UNIQUE)


async def test_replay_without_anchor_event_repairs_nothing():
    """A triggered condition with NO events has no trustworthy anchor — the
    sweep flags it (in _sweep_thesis) rather than guessing a replay start."""
    conn = _RoutedConn(routes=[("fetchrow", "thesis_condition_events", None)])
    written, missed = await sweep._replay_condition(conn, _cond(), "HUBS.NYSE", AS_OF)
    assert (written, missed) == (0, [])


# ---------------------------------------------------------------------------
# _sweep_thesis — parse drift / frozen values / SP guard / lint flags
# ---------------------------------------------------------------------------

def _fresh_close_routes(close="200.00", dt=None):
    return ("fetchrow", "ORDER  BY dt DESC LIMIT 1",
            {"close": Decimal(close), "dt": dt or AS_OF - timedelta(days=1)})


async def test_parse_drift_flagged_and_baseline_never_changed():
    drifted = _cond(
        status="active",
        enforcement_kind="price_above",  # stored disagrees with cp-1's price_below
        parser_version="cp-0",
    )
    conn = _RoutedConn(routes=[
        _fresh_close_routes(),
        ("fetch", "FROM thesis_conditions", [drifted]),
    ])
    n, _notes = await sweep._sweep_thesis(conn, _thesis(), AS_OF)
    assert n >= 1
    flags = _execs(conn, "thesis_revisions")
    assert any("PARSE_DRIFT" in str(a) for _q, a in flags)
    # The stored baseline is NEVER auto-changed on drift.
    assert all("enforcement_kind" not in q for q, _a in _execs(conn, "UPDATE thesis_conditions"))
    assert _execs(conn, "SET parser_version") == []


async def test_matching_baseline_under_new_parser_version_silently_refreshes(
    monkeypatch: pytest.MonkeyPatch,
):
    """Simulated cp-2 whose output matches the stored cp-1 baseline → refresh
    parser_version, write no flag."""
    monkeypatch.setattr(sweep, "PARSER_VERSION", "cp-2")
    stale_but_matching = _cond(status="active", parser_version="cp-1")
    conn = _RoutedConn(routes=[
        _fresh_close_routes(),
        ("fetch", "FROM thesis_conditions", [stale_but_matching]),
    ])
    n, _notes = await sweep._sweep_thesis(conn, _thesis(), AS_OF)
    refresh = _execs(conn, "SET parser_version")
    assert len(refresh) == 1
    assert refresh[0][1][0] == "cp-2"
    assert not any("PARSE_DRIFT" in str(a) for _q, a in _execs(conn, "thesis_revisions"))
    assert n == 0


async def test_frozen_value_drift_on_50d_ma():
    ma_cond = _cond(
        condition_id=6, ordinal=2, status="active",
        condition_text="50d MA ($243.61) not recaptured within 2 weeks of breach",
        enforcement_kind="not_machine_checkable", enforcement_threshold=None,
    )
    sma_rows = [{"close": Decimal("300.00")}] * 50  # true 50d MA now 300
    conn = _RoutedConn(routes=[
        _fresh_close_routes(),
        ("fetch", "FROM thesis_conditions", [ma_cond]),
        ("fetch", "LIMIT $3", sma_rows),
    ])
    n, _notes = await sweep._sweep_thesis(conn, _thesis(), AS_OF)
    assert n >= 1
    flags = [a for _q, a in _execs(conn, "thesis_revisions") if "FROZEN_VALUE_DRIFT" in str(a)]
    assert flags, "expected a FROZEN_VALUE_DRIFT flag"
    # Quotes authored vs current on the face.
    assert any("243.61" in str(a) and "300.00" in str(a) for a in flags)


async def test_stale_tape_skips_replay_and_born_breach_with_loud_note():
    """SP fixture, sweep variant: same 5-calendar-day bar as the daily job."""
    stale_dt = AS_OF - timedelta(days=9)
    conn = _RoutedConn(routes=[
        ("fetchrow", "ORDER  BY dt DESC LIMIT 1",
         {"close": Decimal("200.00"), "dt": stale_dt}),
        ("fetch", "FROM thesis_conditions", [_cond(status="triggered")]),
        ("fetchrow", "thesis_condition_events", {"price_date": date(2026, 7, 2)}),
    ])
    _n, notes = await sweep._sweep_thesis(
        conn, _thesis(attestation="underwritten"), AS_OF
    )
    assert any("stale tape" in n for n in notes)
    # No replay range-fetch on stale tape.
    assert all("dt > $2" not in q for _m, q, _a in conn.calls)


async def test_incoherent_placeholder_ladder_is_flagged_not_blocked():
    bad = _thesis(stop_price=Decimal("230"), entry_band_lower=Decimal("185"),
                  entry_band_upper=Decimal("190"), target_price=Decimal("260"))
    conn = _RoutedConn(routes=[_fresh_close_routes()])
    n, _notes = await sweep._sweep_thesis(conn, bad, AS_OF)
    assert n >= 1
    assert any("LADDER_INCOHERENT" in str(a) for _q, a in _execs(conn, "thesis_revisions"))


async def test_capital_against_placeholder_is_flagged():
    """Active + placeholder should be unreachable via enter_thesis() — the
    sweep surfaces the out-of-band state loudly rather than assuming."""
    conn = _RoutedConn(routes=[_fresh_close_routes()])
    n, _notes = await sweep._sweep_thesis(conn, _thesis(status="active"), AS_OF)
    assert n >= 1
    assert any(
        "UNATTESTED_WITH_CAPITAL" in str(a)
        for _q, a in _execs(conn, "thesis_revisions")
    )


async def test_no_anchor_triggered_condition_gets_stale_trigger_flag():
    conn = _RoutedConn(routes=[
        _fresh_close_routes(),
        ("fetch", "FROM thesis_conditions", [_cond(status="triggered")]),
        ("fetchrow", "thesis_condition_events", None),   # no anchor
        ("fetchval", "SELECT EXISTS", False),
    ])
    n, _notes = await sweep._sweep_thesis(conn, _thesis(), AS_OF)
    assert n >= 1
    assert any(
        "STALE_TRIGGER_STATE" in str(a) and "none" in str(a)
        for _q, a in _execs(conn, "thesis_revisions")
    )


# ---------------------------------------------------------------------------
# Scope — the live rule includes watching AND research (register #22)
# ---------------------------------------------------------------------------

def test_live_rule_scope_pins_not_in_exited_expired():
    src = inspect.getsource(sweep._run)
    assert "NOT IN ('exited', 'expired')" in src


def test_scheduling_note_points_at_github_actions_not_render():
    doc = sweep.__doc__ or ""
    assert "weekly-research.yml" in doc
    assert "render.yaml" in doc  # the explicit NOT-render note
