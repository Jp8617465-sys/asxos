"""Tier 2a mechanical screening evaluator.

Turns a `screening_rules.rule_json` (curated_composite only — migration 0038
CHECK constraint) into a parameterized SQL query against `universe` + latest
`fundamentals` + latest usable `rs_fundamentals_pit` + latest `prices.close`
+ a trailing ~90-trading-day `prices` aggregate,
and logs the result to `screening_runs` for audit. See docs/proposals/
thesis-coverage-framework-2026-07-11.md Tier 2a for the full design.

Field sources and vintages (repointed 2026-08-20 — the five fields below were
previously read from `fundamentals` columns that have had NO writer since
migration 0001 and were 100% NULL across all 138,087 rows, PR #142 finding D5;
`asxos/ingestion/fundamentals.py`'s INSERT/UPSERT never names them):

* `roe`, `revenue`, `net_income`, `franking_pct`, `debt_to_equity` come from
  the latest USABLE `rs_fundamentals_pit` row per symbol — statement-vintage
  (yearly), produced weekly by `jobs/derive_fundamentals_pit.py` after
  `sync_financial_statements` + `sync_corporate_actions`. "Usable" means
  `knowledge_date <= CURRENT_DATE`: 60 live rows carry FUTURE knowledge_date
  values (known ingestion defect, session-handoff-2026-08-18), and filtering
  BEFORE the DISTINCT ON pick is load-bearing — a symbol whose newest row is
  future-dated falls back to its newest usable row instead of dropping out.
  Ordering `symbol, as_of DESC, knowledge_date DESC` is deterministic under
  the table's `(symbol, knowledge_date)` PK: current best knowledge of the
  most recent period.
* `pe_ratio`, `pb_ratio`, `eps`, `dividend_yield` stay on latest
  `fundamentals` (daily vendor); `latest_close` on latest `prices` (daily);
  `market_cap`/`sector` on `universe` (propagated canonical values). One
  ScreenMatch therefore mixes vintages — standard for fundamental screens,
  stated here so nobody assumes a single as-of.
* `avg_daily_value_aud_90d` is COMPUTED per run from `prices` over a
  130-calendar-day window (~90 trading days), not stored — see
  _AVG_DAILY_VALUE_SQL. It is the tradeability gate: `market_cap` is a size
  measure and demonstrably not a liquidity proxy. Its NULL means "no priced
  days inside the window", NOT "illiquid" — a symbol that traded with no
  recorded volume scores 0.00, which is a value. The join is a LEFT JOIN and
  NULL fails every comparison, so a `gte` liquidity gate drops
  no-price-history symbols on ABSENT data rather than measured thinness;
  fail-safe for a gate, but it is exclusion by missingness, and `is_null` is
  the only op that surfaces those names.
  Cost: the shared `_BASE_CTES_SQL`/`_BASE_FROM_SQL` force the aggregate on
  EVERY screen run, and _FIELD_MAP membership puts it in every output row —
  two mechanisms, not one. The CTE carries NO is_active/security_kind filter,
  so it scans every symbol in `prices` within the window (inactive names,
  .INDX and US holdings included), not just the screened set. It is served by
  `prices_dt_idx`, NOT the (symbol, dt) PK — a leading-column range scan on
  `dt` cannot use that PK. Measured at production scale: Parallel Index Scan,
  ~174k rows, 61ms, twice per screen (coverage query + match query). Fine for
  an on-demand CLI path; do not drop `prices_dt_idx` assuming the PK covers it.

  Currency caveat: the `_aud` in the field name is true only because
  `_BASE_FROM_SQL` filters `security_kind = 'au_equity'` — a filter in a
  DIFFERENT SQL block. `prices.close` is NATIVE currency and this expression
  has no FX step, so if that filter ever widens (ETF/multi-instrument
  expansion is a planned follow-on) the column silently becomes a currency
  lie. That mistake has already cost this repo once — see the
  cost_base_normal note in portfolio-conventions.

Fail-loud coverage guard (CLAUDE.md #10): a rule referencing any field with
ZERO non-null coverage over the (sector-scoped) candidate universe raises
RuntimeError naming the column(s) — on a fully-NULL column every predicate is
degenerate (`is_null` degenerate-true, everything else degenerate-empty):
that is the data being missing, never the screen answering. A genuine
zero-match on POPULATED data remains a valid, distinguishable result.

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
and asxos/domain/macro_theses/service.py (its decode helper's
parse_float=Decimal call — cite by function, line numbers rot). A bare json.loads() would
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
    # (u = universe, f = latest fundamentals per symbol, pit = latest usable
    # rs_fundamentals_pit row per symbol, p = latest price).
    sql_expr: str
    is_text: bool


# debt_to_equity is a COMPUTED expression, gated on positive equity: a
# negative- or zero-equity company gets NULL, never a negative ratio — a
# negative-equity name matching a low-leverage `lt` screen would be a silent
# wrong answer (it is "most levered" in substance), and a high-leverage `gte`
# screen would symmetrically miss it. net_debt CAN legitimately be negative
# (net cash) with positive equity — that negative D/E is real and kept.
# Consequence, stated deliberately: `is_null` on debt_to_equity means
# "equity missing/non-positive OR net_debt missing" — three NULL sources,
# one answer. (backend-architect ruling, 2026-08-20.)
_DEBT_TO_EQUITY_SQL = "(CASE WHEN pit.total_equity > 0 THEN pit.net_debt / pit.total_equity END)"

# Average daily traded VALUE in AUD over ~90 trading days, computed from the
# `prices` OHLCV rows rather than stored as a column: there is no ingestion
# step to add and no staleness to manage, exactly as _DEBT_TO_EQUITY_SQL is
# computed rather than stored. 130 calendar days is the window that yields
# ~90 ASX trading days (weekends + public holidays removed).
#
# Why value and not share volume: a manual retail investor's constraint is
# dollars he can move without crossing a wide spread, and share count is
# meaningless across a 1c explorer and a $40 industrial. market_cap is NOT a
# substitute — measured against the quality screen's other gates, 2026-08-21.
# (No figure is quoted here deliberately: every distribution number measured
# before this expression shipped used a plain avg() and over-counts how many
# symbols clear a threshold. Re-measure before quoting one.)
#
# Why raw `close`, not `adj_close` — this repo's convention elsewhere: raw
# close x raw volume is the dollars that actually changed hands, and it is
# split-invariant (a 10:1 split multiplies historical volume by 10 and divides
# close by 10). adj_close x volume would systematically understate pre-split
# and pre-dividend days. This is a choice, not an oversight; do not "fix" it.
#
# SUM over a FIXED 90-day denominator, not avg() — two distinct hazards, both
# of which would make the gate admit the LEAST liquid names, the exact inverse
# of its purpose:
#   1. `prices.volume` is NULLable (see the 0001 initial schema; only `close`
#      is NOT NULL) and avg() SKIPS NULLs. A symbol with 89 blank days and one
#      A$1m day would average to A$1m and clear a A$50k gate.
#   2. avg() also divides by rows PRESENT, so a symbol that traded 10 days out
#      of 90 would be scored on those 10 days alone. A name that trades one day
#      in nine is illiquid however busy those days were.
# Both choices deliberately UNDERSTATE liquidity for thin names. For a gate
# whose job is to keep untradeable names out, understating fails safe.
#
# Honest limit: this is still a mean, so a single large crossing inflates it.
# The robustness check is the median daily value, which needs a percentile
# aggregate this expression deliberately does not carry — if a matched name
# looks untradeable in practice, check the median before assuming the gate is
# wrong. And it measures traded VALUE only — not bid/ask spread, not free
# float, not register concentration, which are precisely the properties whose
# absence made market_cap fail as a proxy. It is a floor test, not a
# tradeability score; do not let it acquire a second job by implication.
_AVG_DAILY_VALUE_SQL = "liq.adv_aud"

# Closed whitelist — the ONLY fields a rule_json condition may reference.
# market_cap/sector read from universe (the propagated, canonical current
# value — see asxos/ingestion/fundamentals.py's propagate_* functions),
# never duplicated from fundamentals. is_active/security_kind are NOT
# whitelisted here — they are hardcoded into the base query, never
# author-controlled (v1 scope is au_equity only; ETF/LIC screening is a
# separate follow-on per the multi-instrument-expansion proposal).
# Every sql_expr remains a hardcoded Python constant — both computed
# expressions (D/E and the liquidity aggregate) included — so the injection boundary is unchanged: rule_json
# contributes nothing to SQL text, ever.
_FIELD_MAP: dict[str, _FieldSpec] = {
    "pe_ratio": _FieldSpec("f.pe_ratio", is_text=False),
    "pb_ratio": _FieldSpec("f.pb_ratio", is_text=False),
    "eps": _FieldSpec("f.eps", is_text=False),
    "dividend_yield": _FieldSpec("f.dividend_yield", is_text=False),
    "franking_pct": _FieldSpec("pit.franking_avg_pct", is_text=False),
    "roe": _FieldSpec("pit.roe", is_text=False),
    "debt_to_equity": _FieldSpec(_DEBT_TO_EQUITY_SQL, is_text=False),
    "revenue": _FieldSpec("pit.revenue_ttm", is_text=False),
    "net_income": _FieldSpec("pit.net_income_ttm", is_text=False),
    "market_cap": _FieldSpec("u.market_cap", is_text=False),
    "sector": _FieldSpec("u.sector", is_text=True),
    "latest_close": _FieldSpec("p.close", is_text=False),
    "avg_daily_value_aud_90d": _FieldSpec(_AVG_DAILY_VALUE_SQL, is_text=False),
}

# Shared CTE + FROM/JOIN blocks — used by BOTH the coverage-guard query and
# the match query so their populations can never drift apart (the guard must
# count coverage over exactly the candidate set the match query screens).
# latest_fundamentals is deliberately narrowed to the columns still read from
# it — the five dead columns stop riding along via `*`, and any future
# duplicate-name ambiguity against the pit aliases is structurally impossible.
_BASE_CTES_SQL = """
        WITH latest_fundamentals AS (
            SELECT DISTINCT ON (symbol)
                symbol, pe_ratio, pb_ratio, eps, dividend_yield
            FROM fundamentals
            ORDER BY symbol, as_of DESC
        ),
        latest_pit AS (
            SELECT DISTINCT ON (symbol)
                symbol, roe, revenue_ttm, net_income_ttm, franking_avg_pct,
                net_debt, total_equity
            FROM rs_fundamentals_pit
            WHERE knowledge_date <= CURRENT_DATE
            ORDER BY symbol, as_of DESC, knowledge_date DESC
        ),
        latest_price AS (
            SELECT DISTINCT ON (symbol) symbol, close
            FROM prices
            ORDER BY symbol, dt DESC
        ),
        liquidity_90d AS (
            -- CASE WHEN count(volume) > 0 is load-bearing, not defensive.
            -- close is NOT NULL and COALESCE never yields NULL, so without it
            -- sum(...) can NEVER be NULL and count(liq.adv_aud) is non-zero for
            -- every symbol with any price row -- which makes the zero-coverage
            -- guard unreachable for this field. If prices.volume ever went 100%
            -- NULL (it is NULLable, and some feeds return null volume), every
            -- adv_aud would be 0.00, coverage would read FULL, the guard would
            -- stay silent, and every liquidity gate would return a plausible
            -- zero-match on ABSENT data -- the exact defect the guard exists to
            -- catch. COALESCE is right per-DAY (an unrecorded day traded zero);
            -- it is wrong per-SYMBOL, where "no volume data at all" must stay
            -- unknown, not become zero.
            SELECT symbol,
                   CASE WHEN count(volume) > 0
                        THEN round(sum(close * COALESCE(volume, 0)) / 90.0, 2)
                   END AS adv_aud
            FROM prices
            -- Bounded at BOTH ends. The dt <= CURRENT_DATE half is not
            -- symmetry-for-its-own-sake: the latest_pit CTE above carries the
            -- same guard precisely because live rows arrive future-dated, and
            -- nothing stops prices doing likewise. Measured, one future row
            -- overstated a symbol's ADV by ~524x -- and unlike the two
            -- understatement hazards below, overstatement ADMITS an
            -- untradeable name, the inverse of this gate's purpose.
            WHERE dt > CURRENT_DATE - 130 AND dt <= CURRENT_DATE
            GROUP BY symbol
        )
"""

_BASE_FROM_SQL = """
        FROM universe u
        LEFT JOIN latest_fundamentals f ON f.symbol = u.symbol
        LEFT JOIN latest_pit pit ON pit.symbol = u.symbol
        LEFT JOIN latest_price p ON p.symbol = u.symbol
        LEFT JOIN liquidity_90d liq ON liq.symbol = u.symbol
        WHERE u.is_active AND u.security_kind = 'au_equity'
"""


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


def _referenced_fields(group: ScreenGroup) -> frozenset[str]:
    """All whitelist field names referenced anywhere in a parsed rule tree.

    Pure function, no I/O — callers pass a tree that already passed
    parse_rule(), so every name is a validated _FIELD_MAP key. Feeds the
    zero-coverage guard in evaluate_rule(); parse_rule guarantees at least
    one leaf condition exists, so the result is never empty.
    """
    fields: set[str] = set()

    def _walk(node: ScreenNode) -> None:
        if isinstance(node, ScreenGroup):
            for item in node.items:
                _walk(item)
        else:
            fields.add(node.field)

    _walk(group)
    return frozenset(fields)


def _remediation_hint(sql_expr: str) -> str:
    """Which job populates the source a dead sql_expr reads from."""
    if "pit." in sql_expr:
        return "jobs/derive_fundamentals_pit.py (weekly, after sync_financial_statements)"
    if sql_expr.startswith("f."):
        return "jobs/sync_fundamentals.py"
    if sql_expr.startswith("u."):
        return "jobs/sync_fundamentals.py (propagate_* into universe)"
    return "jobs/sync_prices.py"


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
    sector_scope and the runtime `sector` param, an empty candidate
    universe before rule filtering, or — the zero-coverage guard — a rule
    referencing any field with ZERO non-null values over the sector-scoped
    candidate universe (see the module docstring's rationale: every
    predicate over a fully-NULL column is degenerate). Mirrors the
    allocator's hard-fail-over-silent-wrong-answer discipline
    (portfolio-conventions.md). A zero-match over POPULATED data is NOT an
    error — it returns a normal result with match_count=0.
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

    # Zero-coverage guard (CLAUDE.md #10). Counts non-null coverage for every
    # field the rule references, over EXACTLY the population the match query
    # screens (same CTEs, same base WHERE incl. sector clause, same params —
    # shared constants make drift structurally impossible). Column
    # identifiers come only from _FIELD_MAP constants and aliases only from
    # parse_rule-validated whitelist keys, so rule_json still contributes
    # nothing to SQL text. Guards ALL ops including is_null: over a
    # fully-NULL column, is_null is degenerate-true and everything else is
    # degenerate-empty — either way the data is missing, the screen did not
    # answer. Partial coverage (e.g. franking_pct on only actual dividend
    # payers) passes; the trip condition is strictly count == 0.
    # `referenced` deliberately draws the CANONICAL _FIELD_MAP key objects
    # (filtered by membership) rather than the rule-supplied equal strings —
    # so the alias interpolated into SQL below is by construction a hardcoded
    # constant, not merely string-equal to one (security-engineer hardening
    # note, 2026-08-20). sorted(_FIELD_MAP) keeps the order deterministic.
    referenced_set = _referenced_fields(tree)
    referenced = [key for key in sorted(_FIELD_MAP) if key in referenced_set]
    coverage_selects = ", ".join(
        f'count({_FIELD_MAP[name].sql_expr}) AS "{name}"' for name in referenced
    )
    coverage_sql = f"""
        {_BASE_CTES_SQL}
        SELECT {coverage_selects}
        {_BASE_FROM_SQL}
        {sector_clause}
    """
    coverage_row = await conn.fetchrow(coverage_sql, *base_params)
    dead_fields = [name for name in referenced if not coverage_row[name]]
    if dead_fields:
        detail = "; ".join(
            f"{name} (source: {_FIELD_MAP[name].sql_expr}; "
            f"populate via {_remediation_hint(_FIELD_MAP[name].sql_expr)})"
            for name in dead_fields
        )
        raise RuntimeError(
            "screen rule references column(s) with ZERO non-null coverage "
            f"over the {universe_size}-symbol candidate universe "
            f"(sector={effective_sector!r}): {detail} — every predicate over "
            "a fully-NULL column is degenerate, so the data is absent over "
            "this scope (an ingestion gap, or a scope where no symbol carries "
            "the metric), not a zero-match answer. A genuine zero-match on "
            "populated data returns normally."
        )

    # The SELECT list is GENERATED from _FIELD_MAP (never hand-duplicated),
    # so alias<->whitelist-key alignment is structural: a field cannot exist
    # in the whitelist yet be misspelled or missing in the output row
    # (refactoring-expert review, 2026-08-20). sector rides along as
    # u.sector for ScreenMatch.sector; symbol likewise.
    select_fields = ", ".join(
        f'{spec.sql_expr} AS "{name}"'
        for name, spec in _FIELD_MAP.items()
        if name != "sector"
    )
    query = f"""
        {_BASE_CTES_SQL}
        SELECT
            u.symbol, u.sector,
            {select_fields}
        {_BASE_FROM_SQL}
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
            # No `if f in r` guard: the SELECT list above is generated from
            # _FIELD_MAP, so every non-sector key is present by construction —
            # a missing key would now be a loud KeyError, not a silent drop.
            values={f: r[f] for f in _FIELD_MAP if f != "sector"},
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
        # Every passing symbol, NOT rows[:limit] -- the audit log must
        # record the whole answer, not the slice that happened to print.
        all_symbols=tuple(r["symbol"] for r in rows),
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
        # all_symbols, never [m.symbol for m in result.matches]: the latter
        # is the display shortlist bounded by `limit`, so logging it wrote
        # the true match_count beside a truncated symbol list.
        list(result.all_symbols),
        json.dumps(rule_json_snapshot, default=str),
        result.duration_ms,
    )
    return int(row["id"])
