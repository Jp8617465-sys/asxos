"""Closed-loop Finding contract and deterministic classifier tests."""

from __future__ import annotations

from datetime import UTC, datetime

from asxos.control_plane.finding import build_finding


def test_same_failure_has_stable_fingerprint_across_run_metadata() -> None:
    common = {
        "probe": "pipeline_health",
        "failure_class": "data_contract_breach",
        "severity": "L3",
        "title": "sync_prices: NO_EQUITY_DATA (ASX)",
        "identifiers": {
            "job": "sync_prices",
            "contract": "NO_EQUITY_DATA",
            "market": "ASX",
        },
        "file_hints": ("asxos/jobs/sync_prices.py",),
    }

    first = build_finding(
        **common,
        run_url="https://github.com/Jp8617465-sys/asxos/actions/runs/100",
        log_excerpt="first run: zero rows",
        observed_at=datetime(2026, 9, 7, 18, 2, 11, tzinfo=UTC),
    )
    later = build_finding(
        **common,
        run_url="https://github.com/Jp8617465-sys/asxos/actions/runs/101",
        log_excerpt="later run: still zero rows",
        observed_at=datetime(2026, 9, 8, 18, 2, 11, tzinfo=UTC),
    )

    assert first.fingerprint == later.fingerprint
