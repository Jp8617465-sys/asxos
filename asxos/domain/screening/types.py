"""Screening domain types — Tier 2a mechanical screen.

Mirrors `themes/types.py`'s shape. All types are frozen dataclasses; no
mutation after construction. See docs/proposals/thesis-coverage-framework-
2026-07-11.md Tier 2a for the design this implements.

Model-independent by construction: `ScreeningRule.source_method` is always
'curated_composite' (migration 0038 CHECK constraint) — hand-authored,
non-ML screening criteria only. There is no field or code path here that
can reach a Model A / SHAP / signal value; CLAUDE.md rule #11 (Model A
quarantine, standing) never applies to this module because it has nothing
to quarantine.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Union

# A leaf condition or a nested AND/OR group. Recursive — see ScreenGroup.
ScreenNode = Union["ScreenCondition", "ScreenGroup"]


@dataclass(frozen=True)
class ScreenCondition:
    """One leaf condition: field OP value.

    field must be a key in evaluator._FIELD_MAP (a closed whitelist — see
    evaluator.py). op must be in evaluator._ALLOWED_OPS, further restricted
    per-field (e.g. 'sector' only allows eq/in/is_null/is_not_null, never
    lt/gt). value is a scalar for eq/neq/lt/lte/gt/gte, a list for in/
    not_in, and unused (but present, ignored) for is_null/is_not_null.
    """

    field: str
    op: str
    value: Decimal | str | list[Decimal | str] | None = None


@dataclass(frozen=True)
class ScreenGroup:
    """A logic group: AND/OR over a tuple of conditions and/or nested groups.

    items is a tuple (not list) to keep ScreenGroup hashable/frozen-safe
    for nested construction.
    """

    logic: Literal["AND", "OR"]
    items: tuple[ScreenNode, ...]


@dataclass(frozen=True)
class ScreeningRule:
    """Mirrors one row of `screening_rules` (migration 0001, tightened by
    migration 0038's CHECK on source_method).

    rule_json is the already-`json.loads(raw, parse_float=Decimal)`-decoded
    dict — never a bare json.loads() result. See evaluator.py's module
    docstring for why (the same hazard theses/schemas.py and
    macro_theses/service.py document).
    """

    id: int
    name: str
    source_method: str  # always 'curated_composite' post-migration-0038
    rule_json: dict[str, Any]
    is_active: bool


@dataclass(frozen=True)
class ScreenMatch:
    """One symbol that passed a rule's conditions.

    values carries EVERY non-`sector` whitelisted field, not only the ones
    the rule referenced — the SELECT list is generated from _FIELD_MAP so
    alias/key alignment is structural. Adding a field to the whitelist
    therefore widens every ScreenMatch and every `asx screen run` table,
    including for rules that never mention it. (Corrected 2026-08-21: this
    previously claimed only evaluated fields were carried, which the
    generated SELECT list has never done.)
    """

    symbol: str
    sector: str | None
    values: dict[str, Decimal | str | None]


@dataclass(frozen=True)
class ScreenRunResult:
    """Result of one evaluate_rule() call.

    match_count is the TRUE total of rule-passing symbols, before the
    `limit` bound; matches is the bounded shortlist actually surfaced. A
    rule matching 1800/1872 names is a no-op, not a triage tool — keeping
    match_count separate from len(matches) preserves that signal even when
    matches is truncated. See screening_runs.match_count's column comment
    in migration 0038.
    """

    rule_id: int
    rule_name: str
    sector_scope: str | None
    universe_size: int
    matches: tuple[ScreenMatch, ...]
    match_count: int
    duration_ms: int
