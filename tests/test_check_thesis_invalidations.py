"""Tests for jobs/check_thesis_invalidations.py.

First test file for this job — written alongside the _normalize_conditions
fix after the job's first live run (2026-07-03) crashed with
AttributeError('str' object has no attribute 'get') on thesis #2
(HUBS.NYSE), whose manually seeded invalidation_conditions are bare strings
rather than the service-layer {"condition", "status"} dict contract.
"""
from __future__ import annotations

import json
from decimal import Decimal

from jobs.check_thesis_invalidations import _normalize_conditions, _parse_price_condition

# --- _normalize_conditions — the live-run regression ---


def test_normalize_bare_strings_become_active_dicts():
    raw = ["Price closes below $230 stop on volume", "Macro regime shifts"]
    out = _normalize_conditions(raw)
    assert out == [
        {"condition": "Price closes below $230 stop on volume", "status": "active"},
        {"condition": "Macro regime shifts", "status": "active"},
    ]


def test_normalize_dicts_pass_through_unchanged():
    raw = [
        {"condition": "Price falls below $150", "status": "active"},
        {"condition": "Price above $300", "status": "triggered", "note": "x"},
    ]
    assert _normalize_conditions(raw) == raw


def test_normalize_mixed_shapes():
    # 45.5 (bare JSONB number) pins the str() coercion for non-string scalars.
    raw = [
        "Close under 45.50",
        {"condition": "Price above $300", "status": "resolved"},
        45.5,
    ]
    out = _normalize_conditions(raw)
    assert out[0] == {"condition": "Close under 45.50", "status": "active"}
    assert out[1] == {"condition": "Price above $300", "status": "resolved"}
    assert out[2] == {"condition": "45.5", "status": "active"}


def test_normalize_accepts_json_string_input():
    # asyncpg returns JSONB as a str unless a codec is registered.
    raw = json.dumps(["Price falls below $10"])
    assert _normalize_conditions(raw) == [
        {"condition": "Price falls below $10", "status": "active"}
    ]


def test_normalized_bare_string_survives_the_crash_path():
    # The exact live failure: .get() on each entry must work post-normalize.
    out = _normalize_conditions(["Price closes below $230 stop on volume"])
    for cond in out:
        assert cond.get("status") == "active"
        parsed = _parse_price_condition(cond["condition"])
        assert parsed == ("below", Decimal("230"))


# --- _parse_price_condition — pin the documented patterns ---


def test_parse_below_variants():
    assert _parse_price_condition("Price falls below $150") == ("below", Decimal("150"))
    assert _parse_price_condition("Close under 45.50") == ("below", Decimal("45.50"))


def test_parse_above_variants():
    assert _parse_price_condition("Price above $300") == ("above", Decimal("300"))
    assert _parse_price_condition("Stock rises above 8.20") == ("above", Decimal("8.20"))


def test_parse_unrecognized_returns_none():
    assert _parse_price_condition("Macro regime shifts to risk_off_disorderly") is None
    assert _parse_price_condition("Three sell-side downgrades") is None
