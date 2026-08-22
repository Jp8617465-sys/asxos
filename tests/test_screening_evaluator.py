"""Tests for asxos/domain/screening/evaluator.py — Tier 2a mechanical screen.

Layer 1: pure-function tests (parse_rule, compile_where_clause) — no DB, no
mocks. Layer 2: async tests with a mocked asyncpg.Connection.

The SQL these functions generate was additionally verified against real
Postgres — mocked tests prove the Python call shape is right, not that the
emitted SQL is semantically correct against a real planner (see
.claude/rules/portfolio-conventions.md's "Verification lesson"). Two
generations of that verification: the original evaluator against a
throwaway local Postgres 16 with adversarial seed data; the 2026-08-20 PIT
repoint by capturing the byte-exact emitted coverage + match queries from
the Python (mocked-connection call args) and running them READ-ONLY against
the production database — coverage counts roe=1,819 / debt_to_equity=1,589
/ franking=462 over the 1,872-symbol active universe, 152 matches for the
demo rule, and the 60 future-knowledge_date rows confirmed excluded.

asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.screening import evaluator as ev
from asxos.domain.screening.types import (
    ScreenCondition,
    ScreenGroup,
    ScreeningRule,
)

# ---------------------------------------------------------------------------
# parse_rule
# ---------------------------------------------------------------------------


def test_parse_rule_flat_and() -> None:
    rule_json = {
        "version": 1,
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "pe_ratio", "op": "lte", "value": 15},
                {"field": "market_cap", "op": "gte", "value": 500000000},
            ],
        },
    }
    tree = ev.parse_rule(rule_json)
    assert isinstance(tree, ScreenGroup)
    assert tree.logic == "AND"
    assert len(tree.items) == 2
    assert tree.items[0] == ScreenCondition(field="pe_ratio", op="lte", value=15)


def test_parse_rule_nested_and_or() -> None:
    rule_json = {
        "version": 1,
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "pe_ratio", "op": "lte", "value": 15},
                {
                    "logic": "OR",
                    "items": [
                        {"field": "dividend_yield", "op": "gte", "value": 0.04},
                        {"field": "roe", "op": "gte", "value": 0.15},
                    ],
                },
            ],
        },
    }
    tree = ev.parse_rule(rule_json)
    assert isinstance(tree.items[1], ScreenGroup)
    assert tree.items[1].logic == "OR"
    assert len(tree.items[1].items) == 2


def test_parse_rule_rejects_wrong_version() -> None:
    with pytest.raises(ValueError, match="version"):
        ev.parse_rule({"version": 2, "conditions": {"logic": "AND", "items": []}})


def test_parse_rule_rejects_missing_version() -> None:
    with pytest.raises(ValueError, match="version"):
        ev.parse_rule({"conditions": {"logic": "AND", "items": []}})


def test_parse_rule_rejects_unknown_top_level_key() -> None:
    with pytest.raises(ValueError, match="unknown top-level key"):
        ev.parse_rule({
            "version": 1, "conditions": {"logic": "AND", "items": []},
            "extra_field": "nope",
        })


def test_parse_rule_rejects_missing_conditions() -> None:
    with pytest.raises(ValueError, match="conditions"):
        ev.parse_rule({"version": 1})


def test_parse_rule_rejects_bare_top_level_condition() -> None:
    """The top-level `conditions` must itself be a logic group ({"logic":
    ..., "items": [...]}), not a bare condition — even a single-condition
    rule must wrap it in a one-item group. This is what keeps parse_rule's
    declared return type (ScreenGroup) honest; a bare top-level condition
    would otherwise construct a ScreenCondition where a ScreenGroup was
    promised. Found as a real type-contract gap during implementation
    (caught by mypy --strict, not by a test) — this test closes that gap."""
    rule_json = {
        "version": 1,
        "conditions": {"field": "pe_ratio", "op": "lte", "value": 15},
    }
    with pytest.raises(ValueError, match="logic group"):
        ev.parse_rule(rule_json)


@pytest.mark.parametrize(
    "field",
    [
        "signal_label",           # a Model A / signals field — must never be reachable
        "prob_up",                # Model A field
        "expected_return",        # Model A field
        "shap_factors",           # Model A field
        "pe_ratio; DROP TABLE fundamentals--",  # injection attempt via field name
        "nonexistent_field",
    ],
)
def test_parse_rule_rejects_non_whitelisted_field(field: str) -> None:
    """Every non-whitelisted field is rejected, including every Model A /
    signals field (rule #11 — this evaluator must never be able to reach
    ML-derived data) and SQL-injection attempts via the field name itself."""
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": [{"field": field, "op": "eq", "value": 1}]},
    }
    with pytest.raises(ValueError, match="unknown field"):
        ev.parse_rule(rule_json)


def test_parse_rule_rejects_unknown_op() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "pe_ratio", "op": "'; DELETE FROM screening_rules--", "value": 1}
        ]},
    }
    with pytest.raises(ValueError, match="unknown op"):
        ev.parse_rule(rule_json)


def test_parse_rule_rejects_lt_on_sector_text_field() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "sector", "op": "lt", "value": "Financials"}
        ]},
    }
    with pytest.raises(ValueError, match="not permitted on text field"):
        ev.parse_rule(rule_json)


def test_parse_rule_allows_eq_and_in_on_sector() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "OR", "items": [
            {"field": "sector", "op": "eq", "value": "Financial Services"},
            {"field": "sector", "op": "in", "value": ["Basic Materials", "Energy"]},
        ]},
    }
    tree = ev.parse_rule(rule_json)
    assert len(tree.items) == 2


def test_parse_rule_rejects_in_with_empty_list() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "sector", "op": "in", "value": []}
        ]},
    }
    with pytest.raises(ValueError, match="non-empty list"):
        ev.parse_rule(rule_json)


def test_parse_rule_allows_is_null_without_value() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "pe_ratio", "op": "is_null"}
        ]},
    }
    tree = ev.parse_rule(rule_json)
    assert tree.items[0].op == "is_null"


def test_parse_rule_rejects_group_with_unknown_key() -> None:
    rule_json = {
        "version": 1,
        "conditions": {
            "logic": "AND",
            "items": [{"field": "pe_ratio", "op": "is_null"}],
            "weird": 1,
        },
    }
    with pytest.raises(ValueError, match="unknown key"):
        ev.parse_rule(rule_json)


def test_parse_rule_rejects_empty_items_list() -> None:
    rule_json = {
        "version": 1,
        "conditions": {"logic": "AND", "items": []},
    }
    with pytest.raises(ValueError, match="non-empty list"):
        ev.parse_rule(rule_json)


def test_parse_rule_rejects_invalid_sector_scope_shape() -> None:
    rule_json = {
        "version": 1, "sector_scope": "Financials",  # should be a list, not a str
        "conditions": {"logic": "AND", "items": [{"field": "pe_ratio", "op": "is_null"}]},
    }
    with pytest.raises(ValueError, match="sector_scope must be a list"):
        ev.parse_rule(rule_json)


# ---------------------------------------------------------------------------
# compile_where_clause
# ---------------------------------------------------------------------------


def test_compile_flat_and_default_param_start() -> None:
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="pe_ratio", op="lte", value=15),
        ScreenCondition(field="market_cap", op="gte", value=500000000),
    ))
    sql, params = ev.compile_where_clause(tree)
    assert sql == "(f.pe_ratio <= $1 AND u.market_cap >= $2)"
    assert params == [15, 500000000]


def test_compile_nested_and_or_sequential_numbering() -> None:
    """The bug this test guards against: nested-group param numbering must
    stay sequential across the whole tree, not restart or skip inside a
    nested group. Caught via manual live-Postgres tracing during
    implementation, not by a mocked test alone — this test pins the fix."""
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="pe_ratio", op="lte", value=15),
        ScreenGroup(logic="OR", items=(
            ScreenCondition(field="dividend_yield", op="gte", value=Decimal("0.04")),
            ScreenCondition(field="roe", op="gte", value=Decimal("0.10")),
        )),
    ))
    sql, params = ev.compile_where_clause(tree)
    assert sql == "(f.pe_ratio <= $1 AND (f.dividend_yield >= $2 OR pit.roe >= $3))"
    assert params == [15, Decimal("0.04"), Decimal("0.10")]


def test_compile_with_nonzero_param_start_offsets_correctly() -> None:
    """Mirrors evaluate_rule's sector-scoped case: a sector param occupies
    $1, so the rule's own placeholders must start at $2."""
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="market_cap", op="gte", value=50000000),
    ))
    sql, params = ev.compile_where_clause(tree, param_start=2)
    assert sql == "(u.market_cap >= $2)"
    assert params == [50000000]


def test_compile_in_uses_any() -> None:
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="sector", op="in", value=["Financial Services", "Basic Materials"]),
    ))
    sql, params = ev.compile_where_clause(tree)
    assert sql == "(u.sector = ANY ($1))"
    assert params == [["Financial Services", "Basic Materials"]]


def test_compile_not_in_uses_all() -> None:
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="sector", op="not_in", value=["Utilities"]),
    ))
    sql, _params = ev.compile_where_clause(tree)
    assert sql == "(u.sector != ALL ($1))"


def test_compile_is_null_binds_no_param() -> None:
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="pe_ratio", op="is_null", value=None),
        ScreenCondition(field="market_cap", op="gte", value=1000),
    ))
    sql, params = ev.compile_where_clause(tree)
    # is_null binds nothing, so market_cap correctly gets $1, not $2.
    assert sql == "(f.pe_ratio IS NULL AND u.market_cap >= $1)"
    assert params == [1000]


def test_compile_where_clause_binds_malicious_value_not_interpolated() -> None:
    """SQL-injection safety at the VALUE layer, not just the field/op layer.
    test_parse_rule_rejects_non_whitelisted_field already proves injection
    attempts via the field/op NAME are rejected at parse time. This proves
    the complementary case: a legitimate string-comparison VALUE that
    happens to contain SQL metacharacters is safely BOUND as a parameter,
    never string-interpolated into the emitted SQL text. Flagged as a gap
    by both refactoring-expert and security-engineer review passes on this
    feature (2026-07-11) — both independently verified this held true by
    hand/adversarial probe, but neither was pinned by an actual test."""
    malicious = "'; DROP TABLE fundamentals--"
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="sector", op="eq", value=malicious),
    ))
    sql, params = ev.compile_where_clause(tree)
    assert malicious not in sql
    assert sql == "(u.sector = $1)"
    assert params == [malicious]


def test_compile_deeply_nested_three_levels() -> None:
    tree = ScreenGroup(logic="AND", items=(
        ScreenCondition(field="pe_ratio", op="lte", value=20),
        ScreenGroup(logic="OR", items=(
            ScreenCondition(field="roe", op="gte", value=Decimal("0.10")),
            ScreenGroup(logic="AND", items=(
                ScreenCondition(field="dividend_yield", op="gte", value=Decimal("0.03")),
                ScreenCondition(field="franking_pct", op="gte", value=Decimal("0.5")),
            )),
        )),
    ))
    sql, params = ev.compile_where_clause(tree)
    assert sql == (
        "(f.pe_ratio <= $1 AND "
        "(pit.roe >= $2 OR (f.dividend_yield >= $3 AND pit.franking_avg_pct >= $4)))"
    )
    assert params == [20, Decimal("0.10"), Decimal("0.03"), Decimal("0.5")]


# ---------------------------------------------------------------------------
# decode_rule_json
# ---------------------------------------------------------------------------


def test_decode_rule_json_uses_decimal_not_float() -> None:
    raw = '{"version": 1, "conditions": {"logic": "AND", "items": [{"field": "pe_ratio", "op": "lte", "value": 15.5}]}}'
    decoded = ev.decode_rule_json(raw)
    value = decoded["conditions"]["items"][0]["value"]
    assert isinstance(value, Decimal)
    assert value == Decimal("15.5")


# ---------------------------------------------------------------------------
# evaluate_rule — mocked asyncpg.Connection
# ---------------------------------------------------------------------------


def _make_rule(
    id: int = 1,
    name: str = "value-screen",
    source_method: str = "curated_composite",
    rule_json: dict | None = None,
    is_active: bool = True,
) -> ScreeningRule:
    return ScreeningRule(
        id=id, name=name, source_method=source_method,
        rule_json=rule_json or {
            "version": 1,
            "conditions": {"logic": "AND", "items": [
                {"field": "pe_ratio", "op": "lte", "value": 15}
            ]},
        },
        is_active=is_active,
    )


def _full_coverage() -> dict[str, int]:
    """A coverage-guard row where every whitelisted field is populated."""
    return dict.fromkeys(ev._FIELD_MAP, 1)


def _make_conn(
    universe_size: int,
    match_rows: list[dict],
    coverage: dict[str, int] | None = None,
) -> MagicMock:
    """Mocked asyncpg.Connection for evaluate_rule's three round-trips:
    fetchval = universe count, fetchrow = the zero-coverage guard row,
    fetch = match rows. Default coverage is fully populated so existing
    tests exercise their own concern, not the guard."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=universe_size)
    conn.fetch = AsyncMock(return_value=match_rows)
    conn.fetchrow = AsyncMock(return_value=coverage if coverage is not None else _full_coverage())
    return conn


async def test_evaluate_rule_rejects_non_curated_composite() -> None:
    rule = _make_rule(source_method="shap_threshold")
    conn = _make_conn(10, [])
    with pytest.raises(RuntimeError, match="curated_composite"):
        await ev.evaluate_rule(conn, rule)
    conn.fetchval.assert_not_awaited()


async def test_evaluate_rule_rejects_inactive_rule() -> None:
    rule = _make_rule(is_active=False)
    conn = _make_conn(10, [])
    with pytest.raises(RuntimeError, match="not active"):
        await ev.evaluate_rule(conn, rule)
    conn.fetchval.assert_not_awaited()


async def test_evaluate_rule_rejects_empty_universe() -> None:
    rule = _make_rule()
    conn = _make_conn(0, [])
    with pytest.raises(RuntimeError, match="empty"):
        await ev.evaluate_rule(conn, rule)


async def test_evaluate_rule_rejects_sector_conflict() -> None:
    rule = _make_rule(rule_json={
        "version": 1, "sector_scope": ["Financial Services"],
        "conditions": {"logic": "AND", "items": [{"field": "pe_ratio", "op": "is_null"}]},
    })
    conn = _make_conn(10, [])
    with pytest.raises(RuntimeError, match="conflicting scope"):
        await ev.evaluate_rule(conn, rule, sector="Basic Materials")


async def test_evaluate_rule_returns_bounded_matches_with_true_total() -> None:
    rule = _make_rule()
    rows = [
        {"symbol": f"SYM{i}.AU", "sector": "Financial Services",
         "pe_ratio": Decimal("10"), "pb_ratio": None, "eps": None,
         "dividend_yield": None, "franking_pct": None, "roe": None,
         "debt_to_equity": None, "revenue": None, "net_income": None,
         "market_cap": Decimal("1000000"), "latest_close": Decimal("5.00"),
         "avg_daily_value_aud_90d": Decimal("125000.00")}
        for i in range(30)
    ]
    conn = _make_conn(universe_size=100, match_rows=rows)
    result = await ev.evaluate_rule(conn, rule, limit=20)
    assert result.match_count == 30  # true total, unbounded
    assert len(result.matches) == 20  # shortlist, bounded by limit
    assert result.universe_size == 100
    assert result.matches[0].symbol == "SYM0.AU"


async def test_evaluate_rule_no_sector_scope_returns_none() -> None:
    rule = _make_rule()
    conn = _make_conn(10, [])
    result = await ev.evaluate_rule(conn, rule)
    assert result.sector_scope is None


async def test_evaluate_rule_single_rule_sector_used_when_runtime_sector_absent() -> None:
    rule = _make_rule(rule_json={
        "version": 1, "sector_scope": ["Financial Services"],
        "conditions": {"logic": "AND", "items": [{"field": "pe_ratio", "op": "is_null"}]},
    })
    conn = _make_conn(10, [])
    result = await ev.evaluate_rule(conn, rule)
    assert result.sector_scope == "Financial Services"


# ---------------------------------------------------------------------------
# log_run
# ---------------------------------------------------------------------------


async def test_log_run_inserts_snapshot_not_live_rule() -> None:
    from asxos.domain.screening.types import ScreenMatch, ScreenRunResult

    result = ScreenRunResult(
        rule_id=1, rule_name="value-screen", sector_scope=None,
        universe_size=100, matches=(ScreenMatch(symbol="CBA.AU", sector="Financial Services", values={}),),
        match_count=1, duration_ms=42, all_symbols=("CBA.AU",),
    )
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value={"id": 7})
    snapshot = {"version": 1, "conditions": {"logic": "AND", "items": []}}

    run_id = await ev.log_run(conn, result, snapshot)

    assert run_id == 7
    call_args = conn.fetchrow.await_args.args
    # positional: query, rule_id, sector_scope, universe_size, match_count, matched_symbols, rule_json_snapshot, duration_ms
    assert call_args[1] == 1
    assert call_args[4] == 1  # match_count
    assert call_args[5] == ["CBA.AU"]  # matched_symbols from the result, not a live re-fetch


# ---------------------------------------------------------------------------
# _referenced_fields — pure helper feeding the zero-coverage guard
# ---------------------------------------------------------------------------


def test_referenced_fields_flat_and_nested() -> None:
    tree = ScreenGroup(
        logic="AND",
        items=(
            ScreenCondition(field="pe_ratio", op="lte", value=Decimal("15")),
            ScreenGroup(
                logic="OR",
                items=(
                    ScreenCondition(field="roe", op="gte", value=Decimal("0.1")),
                    ScreenCondition(field="pe_ratio", op="is_null", value=None),
                ),
            ),
        ),
    )
    assert ev._referenced_fields(tree) == frozenset({"pe_ratio", "roe"})


# ---------------------------------------------------------------------------
# Zero-coverage guard (CLAUDE.md #10 — no silent zero on a dead column)
# ---------------------------------------------------------------------------


def _rule_on(field: str, op: str = "gte", value: object = 1) -> ScreeningRule:
    item: dict[str, object] = {"field": field, "op": op}
    if op not in ("is_null", "is_not_null"):
        item["value"] = value
    return _make_rule(rule_json={
        "version": 1,
        "conditions": {"logic": "AND", "items": [item]},
    })


async def test_dead_column_raises_named_not_silent_zero() -> None:
    """The mission's core defect: a rule on a 100%-NULL column previously
    returned a silent, plausible zero-match. It must now RAISE, naming the
    column and the universe size."""
    coverage = _full_coverage() | {"roe": 0}
    conn = _make_conn(1872, [], coverage=coverage)
    with pytest.raises(RuntimeError) as exc:
        await ev.evaluate_rule(conn, _rule_on("roe"))
    msg = str(exc.value)
    assert "roe" in msg and "1872" in msg and "ZERO non-null coverage" in msg
    conn.fetch.assert_not_awaited()  # the match query never ran


async def test_dead_column_raises_even_for_is_null_op() -> None:
    """Over a fully-NULL column, is_null is degenerate-true (matches the
    whole universe) — that is missing data, not a screen answer. Guarded."""
    coverage = _full_coverage() | {"franking_pct": 0}
    conn = _make_conn(10, [], coverage=coverage)
    with pytest.raises(RuntimeError, match="franking_pct"):
        await ev.evaluate_rule(conn, _rule_on("franking_pct", op="is_null"))


async def test_all_dead_columns_named_in_one_error() -> None:
    coverage = _full_coverage() | {"roe": 0, "revenue": 0}
    rule = _make_rule(rule_json={
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "roe", "op": "gte", "value": 1},
            {"field": "revenue", "op": "gte", "value": 1},
            {"field": "pe_ratio", "op": "lte", "value": 15},
        ]},
    })
    conn = _make_conn(10, [], coverage=coverage)
    with pytest.raises(RuntimeError) as exc:
        await ev.evaluate_rule(conn, rule)
    msg = str(exc.value)
    assert "roe" in msg and "revenue" in msg and "pe_ratio" not in msg


async def test_partial_coverage_never_trips_the_guard() -> None:
    """franking_pct at 462/1872 is legitimate (only actual dividend payers
    carry franking) — the trip condition is strictly count == 0."""
    coverage = _full_coverage() | {"franking_pct": 462}
    conn = _make_conn(1872, [], coverage=coverage)
    result = await ev.evaluate_rule(conn, _rule_on("franking_pct", op="gte", value=Decimal("0.5")))
    assert result.match_count == 0  # valid zero-match on populated data


async def test_zero_match_on_populated_data_stays_valid() -> None:
    conn = _make_conn(100, [], coverage=_full_coverage())
    result = await ev.evaluate_rule(conn, _make_rule())
    assert result.match_count == 0
    assert result.matches == ()
    assert result.universe_size == 100


async def test_guard_only_queries_referenced_fields() -> None:
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("roe"))
    coverage_sql = conn.fetchrow.await_args.args[0]
    assert 'AS "roe"' in coverage_sql
    assert 'AS "pe_ratio"' not in coverage_sql  # unreferenced — not counted
    # No-sector rule -> the coverage query binds ZERO params. A regression
    # passing where_params here would satisfy any mock but fail on real
    # asyncpg (refactoring-expert review, 2026-08-20).
    assert conn.fetchrow.await_args.args == (coverage_sql,)


# ---------------------------------------------------------------------------
# Emitted-SQL shape — the PIT repoint (backend-architect rulings, 2026-08-20)
# ---------------------------------------------------------------------------


async def test_match_query_reads_pit_with_deterministic_usable_ordering() -> None:
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("roe"))
    query = conn.fetch.await_args.args[0]
    assert "FROM rs_fundamentals_pit" in query
    # Load-bearing: the usability filter sits BEFORE the DISTINCT ON pick,
    # so a future-dated newest row falls back instead of dropping the symbol.
    assert "knowledge_date <= CURRENT_DATE" in query
    # Deterministic under the (symbol, knowledge_date) PK.
    assert "ORDER BY symbol, as_of DESC, knowledge_date DESC" in query
    # Equity-sign-gated D/E — never a negative-equity false match.
    assert "CASE WHEN pit.total_equity > 0" in query
    # The dead columns are gone from the fundamentals CTE entirely.
    assert "DISTINCT ON (symbol) *" not in query


async def test_match_values_carry_all_whitelist_keys_for_repointed_fields() -> None:
    """Alias<->whitelist alignment, tested at BOTH layers: the emitted SQL
    must alias every non-sector whitelist field by its exact key (the SELECT
    list is generated from _FIELD_MAP, so this pins the generation), and the
    resulting ScreenMatch.values must carry the exact key set."""
    row = {
        "symbol": "SYM0.AU", "sector": "Industrials",
        "pe_ratio": Decimal("10"), "pb_ratio": Decimal("1.2"), "eps": Decimal("0.5"),
        "dividend_yield": Decimal("0.04"), "franking_pct": Decimal("100"),
        "roe": Decimal("0.15"), "debt_to_equity": Decimal("0.8"),
        "revenue": Decimal("1000000"), "net_income": Decimal("100000"),
        "market_cap": Decimal("5000000"), "latest_close": Decimal("2.50"),
        "avg_daily_value_aud_90d": Decimal("125000.00"),
    }
    conn = _make_conn(10, [row], coverage=_full_coverage())
    result = await ev.evaluate_rule(conn, _rule_on("roe"))
    expected_keys = set(ev._FIELD_MAP) - {"sector"}
    assert set(result.matches[0].values) == expected_keys
    # The emitted SQL itself must alias every one of those keys — a
    # misspelled alias here is what would have silently dropped a field
    # under the old hand-written SELECT list.
    match_sql = conn.fetch.await_args.args[0]
    for key in expected_keys:
        assert f'AS "{key}"' in match_sql


async def test_coverage_and_match_queries_share_population() -> None:
    """The guard must count over EXACTLY the candidate set the match query
    screens — same base WHERE, same sector param."""
    rule = _make_rule(rule_json={
        "version": 1, "sector_scope": ["Industrials"],
        "conditions": {"logic": "AND", "items": [{"field": "roe", "op": "gte", "value": 1}]},
    })
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, rule)
    coverage_sql = conn.fetchrow.await_args.args[0]
    match_sql = conn.fetch.await_args.args[0]
    for sql in (coverage_sql, match_sql):
        assert "u.is_active AND u.security_kind = 'au_equity'" in sql
        assert "AND u.sector = $1" in sql
    assert conn.fetchrow.await_args.args[1] == "Industrials"


# ---------------------------------------------------------------------------
# Liquidity gate — avg_daily_value_aud_90d (added 2026-08-21)
#
# Why this field exists at all: market_cap was being used as a tradeability
# proxy and measurably is not one. Measured against production on 2026-08-21,
# AT LEAST 10 of the 72 symbols passing the quality screen's other gates traded
# under A$50k/day despite every one of them clearing a A$100m market cap. The
# gate is the difference between a queue of names James can actually enter and
# exit over months and a queue that merely looks investable.
#
# That measurement used a plain avg(close * volume), NOT the expression this
# module tests — see _AVG_DAILY_VALUE_SQL. The shipped formula returns lower
# values for thin names, so 10 is a FLOOR, not a count. Do not propagate it.
# ---------------------------------------------------------------------------


def test_liquidity_field_is_whitelisted_and_numeric() -> None:
    """It must accept the numeric ops a liquidity gate needs — a text-only op
    restriction here would silently make range gating impossible. (Not the
    complete _NUMERIC_OPS set: in/not_in are valid on it but meaningless for a
    continuous money value, so they are not exercised.)"""
    assert "avg_daily_value_aud_90d" in ev._FIELD_MAP
    assert ev._FIELD_MAP["avg_daily_value_aud_90d"].is_text is False
    for op in ("gte", "lt", "gt", "lte", "eq", "neq", "is_null", "is_not_null"):
        tree = ev.parse_rule({
            "version": 1,
            "conditions": {"logic": "AND", "items": [
                {"field": "avg_daily_value_aud_90d", "op": op, "value": 50000}
            ]},
        })
        assert isinstance(tree, ev.ScreenGroup)


def test_liquidity_threshold_binds_as_param_not_interpolated() -> None:
    tree = ev.parse_rule({
        "version": 1,
        "conditions": {"logic": "AND", "items": [
            {"field": "avg_daily_value_aud_90d", "op": "gte", "value": Decimal("50000")}
        ]},
    })
    sql, params = ev.compile_where_clause(tree)
    assert sql == "(liq.adv_aud >= $1)"
    assert params == [Decimal("50000")]


async def test_liquidity_cte_window_and_join_present_in_emitted_sql() -> None:
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    query = conn.fetch.await_args.args[0]
    # 130 CALENDAR days is the window that yields ~90 ASX TRADING days.
    # A literal 90 here would be ~62 trading days — a third short.
    assert "dt > CURRENT_DATE - 130" in query
    assert "GROUP BY symbol" in query
    assert "LEFT JOIN liquidity_90d liq ON liq.symbol = u.symbol" in query
    # Traded VALUE, not share count: share volume is meaningless across a
    # 1c explorer and a $40 industrial.
    assert "close * COALESCE(volume, 0)" in query


async def test_liquidity_is_rounded_to_cents_in_sql() -> None:
    """A bare aggregate returns a high-scale numeric that renders unreadably
    in the CLI table. It is AUD; cents is the honest scale."""
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    assert "round(sum(close * COALESCE(volume, 0)) / 90.0, 2)" in conn.fetch.await_args.args[0]


async def test_liquidity_null_volume_counts_as_zero_not_skipped() -> None:
    """`prices.volume` is NULLable and SQL avg() SKIPS NULLs, so avg() would
    score a symbol on only the days it actually traded — 89 blank days plus one
    A$1m day would read as A$1m ADV and clear a A$50k gate. That inverts the
    gate: the thinnest names would pass most easily. COALESCE(volume, 0) makes
    an unrecorded day count as zero traded value."""
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    query = conn.fetch.await_args.args[0]
    assert "COALESCE(volume, 0)" in query
    # Deliberately NO `"avg(...)" not in query` assertion: it would be brittle
    # (case, spacing and alias variants all slip past) and redundant, since the
    # byte-exact expression test above fails first on any avg()-based
    # regression. A negative string assertion is only durable when the space of
    # wrong answers is small and enumerable; here it is not.


async def test_liquidity_uses_fixed_denominator_not_rows_present() -> None:
    """Second half of the same hazard: avg() divides by rows PRESENT, so a name
    trading 10 days in 90 would be scored on those 10. A stock that trades one
    day in nine is illiquid however busy those days were — the fixed nominal
    90-trading-day denominator says so, and understating liquidity is the safe
    direction of error for a gate that exists to keep names OUT."""
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    query = conn.fetch.await_args.args[0]
    assert "/ 90.0" in query
    assert "sum(close * COALESCE(volume, 0))" in query


async def test_liquidity_dead_column_names_price_job_not_a_fundamentals_job() -> None:
    """Zero coverage on this field means prices are missing, so the
    remediation hint must point at the price job — a fundamentals hint would
    send the reader to the wrong pipeline."""
    conn = _make_conn(10, [], coverage={"avg_daily_value_aud_90d": 0})
    with pytest.raises(RuntimeError, match="avg_daily_value_aud_90d"):
        await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    assert ev._remediation_hint("liq.adv_aud") == "jobs/sync_prices.py"


async def test_liquidity_cte_present_in_both_coverage_and_match_queries() -> None:
    """Population parity: the guard must count liquidity over exactly the
    candidate set the match query screens, or the two can disagree."""
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    for sql in (conn.fetchrow.await_args.args[0], conn.fetch.await_args.args[0]):
        assert "liquidity_90d AS (" in sql
        assert "LEFT JOIN liquidity_90d liq" in sql


async def test_liquidity_null_when_no_volume_data_so_guard_can_see_it() -> None:
    """The zero-coverage guard must stay REACHABLE for this field.

    `close` is NOT NULL and COALESCE never yields NULL, so a bare
    `sum(close * COALESCE(volume, 0))` can never be NULL — which would make
    `count(liq.adv_aud)` non-zero for every symbol with any price row and leave
    the guard unreachable. The failure that hides: if `prices.volume` went 100%
    NULL, every value would be 0.00, coverage would read FULL, and every
    `avg_daily_value_aud_90d >= N` rule would return a plausible zero-match on
    ABSENT data — the exact 'silent, plausible zero-match' the guard exists to
    prevent.

    `CASE WHEN count(volume) > 0` keeps the per-day COALESCE (an unrecorded day
    genuinely traded zero dollars) while letting a symbol with NO recorded
    volume at all stay NULL — unknown, not zero, and visible to the guard.
    """
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    for sql in (conn.fetchrow.await_args.args[0], conn.fetch.await_args.args[0]):
        assert "CASE WHEN count(volume) > 0" in sql
    # Gate semantics are unchanged by this: NULL and 0.00 both fail gte/lt.
    # Only is_null/is_not_null and the guard change, both fail-loud (CLAUDE #10).


async def test_liquidity_window_is_bounded_at_both_ends() -> None:
    """A future-dated `prices` row must not inflate ADV.

    The latest_pit CTE in this same module carries `knowledge_date <=
    CURRENT_DATE` because live rows genuinely arrive future-dated; nothing
    stops `prices` doing the same. Measured against real Postgres, one row at
    CURRENT_DATE + 30 overstated a symbol's ADV by ~524x.

    Direction matters here. The COALESCE and fixed-denominator choices both
    UNDERSTATE liquidity, which fails safe for a gate that exists to keep names
    out. Overstatement is the inverse: it ADMITS an untradeable name into the
    shortlist, which is the one outcome this field exists to prevent.
    """
    conn = _make_conn(10, [], coverage=_full_coverage())
    await ev.evaluate_rule(conn, _rule_on("avg_daily_value_aud_90d"))
    for sql in (conn.fetchrow.await_args.args[0], conn.fetch.await_args.args[0]):
        assert "dt > CURRENT_DATE - 130 AND dt <= CURRENT_DATE" in sql


async def test_log_run_records_every_match_not_just_the_displayed_shortlist() -> None:
    """The audit row must carry the WHOLE answer, not the printed slice.

    `matches` is truncated to `limit` inside evaluate_rule, so logging
    [m.symbol for m in result.matches] wrote the true match_count beside a
    truncated symbol list -- a screening_runs row reading "50 matched, 20
    recorded". That silently destroys the audit trail pre-registration
    depends on, because the unrecorded names are precisely the ones nobody
    looked at and nobody can later check.
    """
    rows = [
        {"symbol": f"SYM{i:03d}.AU", "sector": "Industrials",
         "pe_ratio": None, "pb_ratio": None, "eps": None, "dividend_yield": None,
         "franking_pct": None, "roe": None, "debt_to_equity": None, "revenue": None,
         "net_income": None, "market_cap": None, "latest_close": None,
         "avg_daily_value_aud_90d": None}
        for i in range(50)
    ]
    conn = _make_conn(1872, rows, coverage=_full_coverage())
    result = await ev.evaluate_rule(conn, _rule_on("roe"), limit=20)

    assert result.match_count == 50
    assert len(result.matches) == 20          # display shortlist, bounded
    assert len(result.all_symbols) == 50      # audit set, unbounded
    assert len(result.all_symbols) == result.match_count

    # Reassignment is load-bearing twice over: _make_conn wired fetchrow for
    # the zero-coverage guard (so log_run would KeyError on row["id"]), and it
    # is what makes await_args refer to the INSERT rather than the guard query.
    conn.fetchrow = AsyncMock(return_value={"id": 1})
    await ev.log_run(conn, result, {"version": 1})

    # Exact-sequence, not len() plus a tail check: the latter passes under a
    # dedupe, a re-sort, or a substitution in the middle. This also pins the
    # ORDER BY u.symbol determinism that makes the audit row reproducible.
    logged = conn.fetchrow.await_args.args[5]
    assert logged == [f"SYM{i:03d}.AU" for i in range(50)]


async def test_log_run_refuses_an_internally_inconsistent_row() -> None:
    """log_run is the ONE gate on the output path, and it must hard-fail.

    The input types are deliberately dumb because parse_rule() gates them.
    ScreenRunResult is built from trusted internal data and had no gate at
    all, so a row whose match_count disagrees with its symbol list would have
    reached Postgres silently. On an audit substrate that is the worst
    available failure: a row that looks authoritative and is not.

    The state is reachable, not hypothetical -- pushing LIMIT into SQL and
    taking match_count from a separate COUNT(*) would make the two values come
    from different queries, which is exactly how the truncation bug arose.
    """
    from asxos.domain.screening.types import ScreenMatch, ScreenRunResult

    bad = ScreenRunResult(
        rule_id=1, rule_name="value-screen", sector_scope=None, universe_size=100,
        matches=(ScreenMatch(symbol="AAA.AU", sector="Industrials", values={}),),
        match_count=50,                      # claims 50...
        duration_ms=42, all_symbols=("AAA.AU",),  # ...carries 1
    )
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value={"id": 1})

    with pytest.raises(RuntimeError, match="inconsistent screening_runs row"):
        await ev.log_run(conn, bad, {"version": 1})

    # Nothing was written -- it refused BEFORE the INSERT, not after.
    conn.fetchrow.assert_not_awaited()
