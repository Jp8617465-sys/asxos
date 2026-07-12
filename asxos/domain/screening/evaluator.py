"""Tier 2a mechanical screening evaluator.

Turns a `screening_rules.rule_json` (curated_composite only — migration 0038
CHECK constraint) into a parameterized SQL query against `universe` +
latest `fundamentals` + latest `prices.close`, and logs the result to
`screening_runs` for audit. See docs/proposals/thesis-coverage-framework-
2026-07-11.md Tier 2a for the full design.

SQL-injection safety boundary: `parse_rule()` validates every field/op
against the closed whitelists below and raises ValueError on anything not
whitelisted, BEFORE `compile_where_clause()` ever runs. Column identifiers
in the emitted SQL come only from `_FIELD_MAP` (hardcoded Python constants,
never rule_json-controlled strings); rule_json-controlled *values* always
reach the query as bound $N parameters, never string-interpolated. By the
time compile_where_clause() runs, there is no rule_json-controlled string
reaching the SQL text at all.

Decimal-only hazard: `screening_rules.rule_json` (and `screening_runs.
rule_json_snapshot`) come back from asyncpg as a raw JSON string — this
repo registers no asyncpg JSONB codec. Callers MUST decode with
`json.loads(raw, parse_float=Decimal)`, never a bare `json.loads()` — the
same hazard documented in asxos/domain/theses/schemas.py's module docstring
and asxos/domain/macro_theses/service.py:157. A bare json.loads() would
silently turn `{"value": 15}` into a Python float before Decimal ever sees
it, violating CLAUDE.md #5 one call earlier than it looks.

Governed vs ungoverned: screening_runs carries no governance_status and no
agent_runs linkage — it is a re-derivable data-filter cache, the same
category as prices/fundamentals/portfolio_daily_snapshots, not investment
content. Re-running the same rule_json against current data reproduces it.
The governance boundary stays at the NEXT step: a human turning a match
into a theme_holdings/thesis entry via the existing manual CLI commands.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import asyncpg

from asxos.domain.screening.types import (
    ScreenCondition,
    ScreenGroup,
    ScreeningRule,
    ScreenMatch,
    ScreenNode,
    ScreenRunResult,
)

_SCHEMA_VERSION = 1

_ALLOWED_OPS = frozenset(
    {"eq", "neq", "lt", "lte", "gt", "gte", "in", "not_in", "is_null", "is_not_null"}
)
_TEXT_OPS = frozenset({"eq", "neq", "in", "not_in", "is_null", "is_not_null"})
_NUMERIC_OPS = _ALLOWED_OPS  # numeric fields allow the full set


@dataclass(frozen=True)
class _FieldSpec:
    # SQL expression the field resolves to, using the base query's aliases
    # (u = universe, f = latest fundamentals per symbol, p = latest price).
    sql_expr: str
    is_text: bool


# Closed whitelist — the ONLY fields a rule_json condition may reference.
# market_cap/sector read from universe (the propagated, canonical current
# value — see asxos/ingestion/fundamentals.py's propagate_* functions),
# never duplicated from fundamentals. is_active/security_kind are NOT
# whitelisted here — they are hardcoded into the base query, never
# author-controlled (v1 scope is au_equity only; ETF/LIC screening is a
# separate follow-on per the multi-instrument-expansion proposal).
_FIELD_MAP: dict[str, _FieldSpec] = {
    "pe_ratio": _FieldSpec("f.pe_ratio", is_text=False),
    "pb_ratio": _FieldSpec("f.pb_ratio", is_text=False),
    "eps": _FieldSpec("f.eps", is_text=False),
    "dividend_yield": _FieldSpec("f.dividend_yield", is_text=False),
    "franking_pct": _FieldSpec("f.franking_pct", is_text=False),
    "roe": _FieldSpec("f.roe", is_text=False),
    "debt_to_equity": _FieldSpec("f.debt_to_equity", is_text=False),
    "revenue": _FieldSpec("f.revenue", is_text=False),
    "net_income": _FieldSpec("f.net_income", is_text=False),
    "market_cap": _FieldSpec("u.market_cap", is_text=False),
    "sector": _FieldSpec("u.sector", is_text=True),
    "latest_close": _FieldSpec("p.close", is_text=False),
}


def decode_rule_json(raw: str) -> dict[str, Any]:
    """The one correct way to decode rule_json / rule_json_snapshot — public
    because every caller that constructs a ScreeningRule from a raw DB row
    (the CLI, and later any discovery agent) needs it. See module
    docstring's Decimal-only hazard note."""
    decoded: dict[str, Any] = json.loads(raw, parse_float=Decimal)
    return decoded


def parse_rule(rule_json: dict[str, Any]) -> ScreenGroup:
    """Validate + parse a decoded rule_json dict into a ScreenGroup tree.

    Pure function — no I/O. Raises ValueError on: wrong/missing version,
    unknown top-level key, unknown field, unknown op, an op not permitted
    for that field's type, a malformed group/condition shape, or a
    top-level `conditions` that isn't itself a logic group (a bare
    single condition at the top level is rejected — every rule_json must
    wrap its condition(s) in an explicit {"logic": ..., "items": [...]},
    even a one-condition rule; this keeps parse_rule's return type an
    honest ScreenGroup, never a bare ScreenCondition). Hard-fail, never a
    silent skip of a bad condition (CLAUDE.md #10).
    """
    if not isinstance(rule_json, dict):
        raise ValueError(f"rule_json must be a dict, got {type(rule_json).__name__}")

    version = rule_json.get("version")
    if version != _SCHEMA_VERSION:
        raise ValueError(
            f"rule_json version must be {_SCHEMA_VERSION}, got {version!r}"
        )

    unknown_keys = set(rule_json) - {"version", "sector_scope", "conditions"}
    if unknown_keys:
        raise ValueError(f"rule_json has unknown top-level key(s): {sorted(unknown_keys)}")

    sector_scope = rule_json.get("sector_scope")
    if sector_scope is not None:
        if not isinstance(sector_scope, list) or not all(isinstance(s, str) for s in sector_scope):
            raise ValueError("sector_scope must be a list of strings or absent")

    conditions = rule_json.get("conditions")
    if conditions is None:
        raise ValueError("rule_json.conditions is required")
    if not isinstance(conditions, dict) or "logic" not in conditions:
        raise ValueError(
            "rule_json.conditions must be a logic group ({'logic': 'AND'|'OR', "
            "'items': [...]}), not a bare condition — wrap even a single "
            "condition in a one-item group"
        )

    node = _parse_node(conditions)
    assert isinstance(node, ScreenGroup)  # guaranteed by the "logic" in conditions check above
    return node


def _parse_node(node: Any) -> ScreenNode:
    if not isinstance(node, dict):
        raise ValueError(f"condition/group must be a dict, got {type(node).__name__}")

    if "logic" in node:
        logic = node.get("logic")
        if logic not in ("AND", "OR"):
            raise ValueError(f"group logic must be 'AND' or 'OR', got {logic!r}")
        items = node.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("group items must be a non-empty list")
        unknown = set(node) - {"logic", "items"}
        if unknown:
            raise ValueError(f"group has unknown key(s): {sorted(unknown)}")
        return ScreenGroup(logic=logic, items=tuple(_parse_node(i) for i in items))

    # Leaf condition.
    unknown = set(node) - {"field", "op", "value"}
    if unknown:
        raise ValueError(f"condition has unknown key(s): {sorted(unknown)}")

    field = node.get("field")
    if field not in _FIELD_MAP:
        raise ValueError(
            f"unknown field {field!r} — must be one of {sorted(_FIELD_MAP)}"
        )
    spec = _FIELD_MAP[field]

    op = node.get("op")
    if op not in _ALLOWED_OPS:
        raise ValueError(f"unknown op {op!r} — must be one of {sorted(_ALLOWED_OPS)}")
    if spec.is_text and op not in _TEXT_OPS:
        raise ValueError(f"op {op!r} is not permitted on text field {field!r}")

    value = node.get("value")
    if op in ("in", "not_in"):
        if not isinstance(value, list) or not value:
            raise ValueError(f"op {op!r} requires a non-empty list value")
    elif op in ("is_null", "is_not_null"):
        pass  # value is ignored
    elif value is None:
        raise ValueError(f"op {op!r} requires a value")

    return ScreenCondition(field=field, op=op, value=value)


def compile_where_clause(
    group: ScreenGroup, *, param_start: int = 1
) -> tuple[str, list[Any]]:
    """Compile a validated ScreenGroup into a parameterized SQL fragment.

    Pure function. Returns (sql_fragment, ordered_bind_params). Every value
    is bound as $N; column identifiers come only from _FIELD_MAP. Callers
    must only ever pass a ScreenGroup that already passed parse_rule() —
    this function does not re-validate field/op whitelisting.

    param_start is the placeholder NUMBER the first param in this fragment
    should use (not a count of already-used params) — e.g. param_start=1
    (the default) means this fragment's own params start at $1;
    param_start=2 means the caller already bound $1 to something else
    (evaluate_rule uses this when a sector param occupies $1).
    """
    params: list[Any] = []
    sql = _compile_node(group, params, param_start)
    return sql, params


def _compile_node(node: ScreenNode, params: list[Any], param_start: int) -> str:
    if isinstance(node, ScreenGroup):
        parts = [_compile_node(item, params, param_start) for item in node.items]
        joiner = " AND " if node.logic == "AND" else " OR "
        return "(" + joiner.join(parts) + ")"

    spec = _FIELD_MAP[node.field]
    expr = spec.sql_expr

    if node.op == "is_null":
        return f"{expr} IS NULL"
    if node.op == "is_not_null":
        return f"{expr} IS NOT NULL"

    op_sql = {
        "eq": "=", "neq": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">=",
    }
    if node.op in op_sql:
        idx = param_start + len(params)
        params.append(node.value)
        return f"{expr} {op_sql[node.op]} ${idx}"

    if node.op in ("in", "not_in"):
        idx = param_start + len(params)
        # parse_rule() already validated node.value is a non-empty list for
        # in/not_in; this assert documents + enforces that invariant here
        # too (defensive; also narrows the static type for the checker).
        assert isinstance(node.value, list)
        params.append(list(node.value))
        keyword = "= ANY" if node.op == "in" else "!= ALL"
        return f"{expr} {keyword} (${idx})"

    raise AssertionError(f"unreachable: unhandled op {node.op!r}")  # parse_rule already validated


async def evaluate_rule(
    conn: asyncpg.Connection,
    rule: ScreeningRule,
    *,
    sector: str | None = None,
    limit: int = 20,
) -> ScreenRunResult:
    """Evaluate a curated_composite screening rule against current data.

    Read-only — does NOT write screening_runs (see log_run()). Base
    population is always active au_equity universe rows; the rule's
    conditions further narrow it. Hard-fails (RuntimeError) rather than
    silently returning an empty/wrong result on: a non-curated_composite
    rule, an inactive rule, a sector conflict between the rule's own
    sector_scope and the runtime `sector` param, or an empty candidate
    universe before rule filtering — mirrors the allocator's hard-fail-
    over-silent-wrong-answer discipline (portfolio-conventions.md).
    """
    if rule.source_method != "curated_composite":
        raise RuntimeError(
            f"screening rule {rule.id} has source_method={rule.source_method!r}, "
            "expected 'curated_composite' — should be structurally impossible "
            "post-migration-0038; refusing to evaluate."
        )
    if not rule.is_active:
        raise RuntimeError(f"screening rule {rule.id} ({rule.name!r}) is not active")

    started = time.monotonic()

    tree = parse_rule(rule.rule_json)

    rule_sectors = rule.rule_json.get("sector_scope")
    effective_sector = _resolve_sector_scope(rule_sectors, sector)

    base_params: list[Any] = []
    sector_clause = ""
    if effective_sector is not None:
        base_params.append(effective_sector)
        sector_clause = f"AND u.sector = ${len(base_params)}"

    # The rule's own placeholders start right after the base (sector) params.
    where_sql, where_params = compile_where_clause(tree, param_start=len(base_params) + 1)

    universe_count_sql = f"""
        SELECT count(*) AS n
        FROM universe u
        WHERE u.is_active AND u.security_kind = 'au_equity'
        {sector_clause}
    """
    universe_size = await conn.fetchval(universe_count_sql, *base_params)
    if not universe_size:
        raise RuntimeError(
            "screen candidate universe is empty before rule filtering "
            f"(sector={effective_sector!r}) — config bug, not a valid zero-match answer"
        )

    query = f"""
        WITH latest_fundamentals AS (
            SELECT DISTINCT ON (symbol) *
            FROM fundamentals
            ORDER BY symbol, as_of DESC
        ),
        latest_price AS (
            SELECT DISTINCT ON (symbol) symbol, close
            FROM prices
            ORDER BY symbol, dt DESC
        )
        SELECT
            u.symbol, u.sector,
            f.pe_ratio, f.pb_ratio, f.eps, f.dividend_yield, f.franking_pct,
            f.roe, f.debt_to_equity, f.revenue, f.net_income,
            u.market_cap, p.close AS latest_close
        FROM universe u
        LEFT JOIN latest_fundamentals f ON f.symbol = u.symbol
        LEFT JOIN latest_price p ON p.symbol = u.symbol
        WHERE u.is_active AND u.security_kind = 'au_equity'
        {sector_clause}
        AND {where_sql}
        ORDER BY u.symbol
    """
    all_params = base_params + where_params
    rows = await conn.fetch(query, *all_params)

    matches = tuple(
        ScreenMatch(
            symbol=r["symbol"],
            sector=r["sector"],
            values={f: r[f] for f in _FIELD_MAP if f in r and f != "sector"},
        )
        for r in rows[:limit]
    )

    duration_ms = int((time.monotonic() - started) * 1000)

    return ScreenRunResult(
        rule_id=rule.id,
        rule_name=rule.name,
        sector_scope=effective_sector,
        universe_size=universe_size,
        matches=matches,
        match_count=len(rows),
        duration_ms=duration_ms,
    )


def _resolve_sector_scope(rule_sectors: list[str] | None, runtime_sector: str | None) -> str | None:
    """Resolve the rule's own sector_scope against a runtime --sector param.

    Both absent -> None (cross-sector). Only one given -> that one. Both
    given -> RuntimeError unless runtime_sector is IN rule_sectors (never a
    silent empty result on a real conflict); returns runtime_sector since
    it's the more specific single-sector scope.
    """
    if not rule_sectors and runtime_sector is None:
        return None
    if not rule_sectors:
        return runtime_sector
    if runtime_sector is None:
        if len(rule_sectors) == 1:
            return rule_sectors[0]
        raise RuntimeError(
            f"rule sector_scope has {len(rule_sectors)} sectors {rule_sectors} "
            "— pass --sector to pick one"
        )
    if runtime_sector not in rule_sectors:
        raise RuntimeError(
            f"--sector {runtime_sector!r} is not in the rule's own sector_scope "
            f"{rule_sectors} — conflicting scope, refusing to silently return empty"
        )
    return runtime_sector


async def log_run(
    conn: asyncpg.Connection, result: ScreenRunResult, rule_json_snapshot: dict[str, Any]
) -> int:
    """Persist a ScreenRunResult to screening_runs. Returns the new row id.

    Separate from evaluate_rule() so a CLI dry-run (--no-log) or a unit
    test can evaluate without writing. rule_json_snapshot is the rule's
    rule_json AT EVALUATION TIME — screening_rules rows are mutable, so
    this snapshot stops a later rule edit from silently reinterpreting an
    old run's meaning.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO screening_runs
            (rule_id, sector_scope, universe_size, match_count,
             matched_symbols, rule_json_snapshot, duration_ms)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        result.rule_id,
        result.sector_scope,
        result.universe_size,
        result.match_count,
        [m.symbol for m in result.matches],
        json.dumps(rule_json_snapshot, default=str),
        result.duration_ms,
    )
    return int(row["id"])
