"""The V/P pre-registration is sealed, and its failure branch cannot be softened.

A pre-registration whose response rule can be edited after a disappointing read
is not a pre-registration. These tests pin the two branches James ruled on
2026-09-16 (before any result existed) and the properties that make the seal
mean something: a deterministic content hash, the falsifier actually carrying
the rule, and the examined surface declared up front rather than chosen after.
"""
from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from asxos.domain.research.registry.vp import (
    HYPOTHESIS_ID,
    POWER_STATEMENT,
    PRIMARY_CONVENTION,
    PRIMARY_CUTOFFS,
    PRIMARY_HORIZON_SESSIONS,
    QUALIFYING_CUTOFFS_AT_PRIMARY,
    RESPONSE_RULE,
    SECONDARY_CONVENTIONS,
    SECONDARY_HORIZONS_SESSIONS,
    STRATEGY_ID,
    TOTAL_SURFACE_EXAMINED,
    vp_hypothesis,
    vp_strategy,
)

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def test_response_rule_carries_both_branches_james_ruled() -> None:
    """Null -> demote, negative -> quarantine. Neither may quietly disappear."""
    rule = RESPONSE_RULE.upper()
    assert "NULL" in rule and "DEMOTED" in rule
    assert "NEGATIVE MONOTONIC" in rule and "QUARANTINE" in rule
    # The asymmetry is the whole point: a thin null is not evidence of absence.
    assert "UNDERPOWERED, NOT DISCONFIRMING" in rule
    # A pass must not read as permission to deploy capital.
    assert "not a licence to size" in RESPONSE_RULE


def test_demotion_names_exactly_what_stops_being_emitted() -> None:
    """'Demoted' is only meaningful if it names the output that stops."""
    for surface in ("target prices", "entry bands", "ranked"):
        assert surface in RESPONSE_RULE
    assert "falsifiable number" in RESPONSE_RULE  # what it keeps doing


def test_falsifier_embeds_the_response_rule_and_the_power_statement() -> None:
    """The DB row must carry the rule, not merely a module constant beside it."""
    falsifier = vp_hypothesis(NOW).falsifier
    assert RESPONSE_RULE in falsifier
    assert POWER_STATEMENT in falsifier


def test_examined_surface_is_declared_before_the_run() -> None:
    """3 conventions x 3 horizons, stated up front so it cannot be chosen after."""
    conventions = 1 + len(SECONDARY_CONVENTIONS)
    horizons = 1 + len(SECONDARY_HORIZONS_SESSIONS)
    assert conventions * horizons == TOTAL_SURFACE_EXAMINED == 9
    assert str(TOTAL_SURFACE_EXAMINED) in vp_hypothesis(NOW).falsifier


def test_primary_endpoint_is_singular_and_named() -> None:
    """One primary. Secondaries may never be re-designated as primary later."""
    h = vp_hypothesis(NOW)
    assert h.horizon_trading_days == PRIMARY_HORIZON_SESSIONS == 126
    assert PRIMARY_CONVENTION == "zero_excess"
    assert PRIMARY_CONVENTION not in SECONDARY_CONVENTIONS
    assert PRIMARY_HORIZON_SESSIONS not in SECONDARY_HORIZONS_SESSIONS
    assert "never re-designated as primary" in h.falsifier


def test_monotonicity_not_top_quintile_is_the_criterion() -> None:
    """Model A's failure was an inverted ladder under a strong headline."""
    statement = vp_hypothesis(NOW).statement
    assert "MONOTONIC" in statement
    assert "not on the top quintile alone" in statement


def test_hypothesis_seals_itself_and_the_hash_is_deterministic() -> None:
    first, second = vp_hypothesis(NOW), vp_hypothesis(NOW)
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64
    # Any edit to the sealed statement is a NEW hypothesis, never a re-seal.
    assert first.content_hash != vp_hypothesis(NOW.replace(hour=13)).content_hash


def test_supplied_wrong_hash_is_rejected() -> None:
    h = vp_hypothesis(NOW)
    with pytest.raises(ValueError, match="does not match canonical artifact content"):
        type(h).model_validate({**h.model_dump(mode="json"), "content_hash": "0" * 64})


def test_strategy_binds_to_the_evaluator_that_will_run_it() -> None:
    s = vp_strategy(NOW)
    assert s.hypothesis_id == HYPOTHESIS_ID
    assert s.strategy_version_id == STRATEGY_ID
    assert s.code_ref.endswith(":evaluate_value_to_price")
    assert s.parameters["terminal_convention"] == PRIMARY_CONVENTION
    assert s.parameters["horizon_trading_days"] == str(PRIMARY_HORIZON_SESSIONS)
    # Research cannot self-promote into capital (migration 0050's boundary).
    assert s.promotion_state == "research"


def test_marked_book_names_are_flagged_not_excluded() -> None:
    """Excluding LICs/REITs after seeing the candidate set would be a data choice."""
    rule = vp_hypothesis(NOW).universe_rule
    assert "FLAGGED" in rule and "rather than excluded" in rule


def test_universe_rule_asserts_the_pit_invariant() -> None:
    assert "knowledge_date <= cutoff" in vp_hypothesis(NOW).universe_rule


def test_registration_is_a_separate_command_from_the_run() -> None:
    """A seal applied in the same transaction as its result is not a seal.

    The momentum path saves hypothesis, strategy and run together; V/P must not,
    or the pre-registration would describe what happened rather than commit to
    it in advance. This pins the ordering guard in the CLI itself.
    """
    from asxos.cli import research as cli

    assert hasattr(cli, "research_vp_register")
    source = inspect.getsource(cli._vp_register)
    # It must look for existing runs and refuse, before saving anything.
    assert "list_runs" in source
    assert source.index("list_runs") < source.index("save_hypothesis")
    assert "refusing to register" in source


def test_cutoff_count_is_measured_against_the_real_calendar_not_estimated() -> None:
    """A sealed document's numbers must be counted before sealing, not guessed.

    An earlier draft claimed five qualifying cutoffs at the primary horizon. The
    live .AU session calendar gives four — 2026-03-31 has only 117 forward
    sessions against a 126-session requirement. This pins the corrected count so
    the two cannot drift apart again.
    """
    assert QUALIFYING_CUTOFFS_AT_PRIMARY == 4
    assert len(PRIMARY_CUTOFFS) == QUALIFYING_CUTOFFS_AT_PRIMARY
    assert PRIMARY_CUTOFFS == ("2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31")
    # The power statement must agree with the constant, and must disclose that
    # a 126-session horizon on 3-month spacing overlaps.
    assert "FOUR" in POWER_STATEMENT
    assert "OVERLAP" in POWER_STATEMENT
    for wrong in ("five quarter", "five quasi"):
        assert wrong not in POWER_STATEMENT and wrong not in RESPONSE_RULE
