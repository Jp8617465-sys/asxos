"""Invalidation-condition parser — single source of truth (0042, D1/R2).

Pure module: Decimal-only, no DB, no I/O. Both the authoring path
(``service.open_thesis`` / ``conditions.add_condition``) and the daily job
(``jobs/check_thesis_invalidations.py``) consume THIS parser — the job's
former private regexes moved here and were deleted there. The daily job
evaluates the STORED baseline (``thesis_conditions.enforcement_kind`` /
``enforcement_threshold``), never re-parsing text at runtime: the baseline is
what was echoed to James at authoring, and that promise is the thing being
enforced. The R8 sweep (``jobs/sweep_rule_integrity.py``) detects
baseline-vs-current-parser drift.

Contract rules (pinned by tests/test_condition_parser.py):
  1. First price-pattern match wins (parity with the pre-0042 job); recognised
     qualifier phrases appearing alongside a matched pattern land in
     ``dropped_qualifiers`` and the echo MUST state the narrowing — the
     register #5 "on volume" silent drop can never recur.
  2. Text containing a comparative keyword + $-amount that does NOT parse →
     ``not_machine_checkable`` with an echo explicitly warning it contains a
     price-like clause that is NOT enforced (HUBS condition #4 class).
  3. $-figures not consumed as the threshold → ``embedded_figures``; an
     ``Nd MA ($X)`` context is recognised as a label so R8 can re-derive it
     from ``prices``. (Bare decimals are captured only when they follow a
     comparative keyword — capturing every bare number would turn "within 2
     weeks" into a phantom figure; conservative reading of rule 3.)
  4. Decimal only; thresholds quantised to 6 dp on storage.

PARSER_VERSION bumps on ANY behaviour change; it is stored per-condition at
authoring so the sweep can tell a stale baseline from a current one.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

PARSER_VERSION = "cp-1"

_SIX_DP = Decimal("0.000001")

Kind = Literal["price_below", "price_above", "not_machine_checkable"]

# Moved verbatim from jobs/check_thesis_invalidations.py (pre-0042) — first
# match wins, below tried before above, parity with the old job's behaviour.
_PRICE_BELOW_RE = re.compile(
    r"(?i)\b(?:price|close|stock)\b.{0,40}(?:below|under|falls?\s+below|<|<=)\s*\$?\s*(\d+(?:\.\d+)?)"
)
_PRICE_ABOVE_RE = re.compile(
    r"(?i)\b(?:price|close|stock)\b.{0,40}(?:above|over|rises?\s+above|>|>=)\s*\$?\s*(\d+(?:\.\d+)?)"
)

# Recognised narrowing qualifiers (contract rule 1). Recorded only when a
# price pattern matched — for unparseable text nothing is being narrowed.
_QUALIFIER_RES = (
    re.compile(r"(?i)\bon volume\b"),
    re.compile(r"(?i)\bwith volume\b"),
    re.compile(r"(?i)\bintraday\b"),
    re.compile(r"(?i)\bon a weekly close\b"),
    re.compile(r"(?i)\bwithin \d+ (?:days?|weeks?)\b"),
)

# "50d MA ($243.61)" — a frozen authored value with a re-derivable label.
_MA_FIGURE_RE = re.compile(r"(?i)\b(\d+)\s*d\s+MA\s*\(\s*\$?(\d+(?:\.\d+)?)\s*\)")

# Any $-amount (contract rule 3).
_DOLLAR_FIGURE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")

# A comparative keyword directly adjacent to an amount — the "price-like
# clause" detector (contract rule 2) and the bare-decimal capture context.
_PRICE_LIKE_RE = re.compile(
    r"(?i)\b(?:below|under|above|over)\s*\$?\s*\d+(?:\.\d+)?|(?:<=?|>=?)\s*\$?\s*\d+(?:\.\d+)?"
)


@dataclass(frozen=True)
class EmbeddedFigure:
    """A frozen authored value the sweep re-derives (e.g. a 50d MA)."""

    label: str  # e.g. "50d MA"; "" if the surrounding context is unrecognised
    value: Decimal


@dataclass(frozen=True)
class ParsedCondition:
    kind: Kind
    threshold: Decimal | None  # NUMERIC(18,6)-safe; None iff not_machine_checkable
    dropped_qualifiers: tuple[str, ...]  # recorded narrowing, never silent
    embedded_figures: tuple[EmbeddedFigure, ...]  # $-figures NOT consumed as the threshold
    echo: str  # the exact human line stored in enforcement_note


def parse_condition(text: str) -> ParsedCondition:
    """Parse one authored condition into its machine-enforcement baseline."""
    threshold_span: tuple[int, int] | None = None
    kind: Kind = "not_machine_checkable"
    threshold: Decimal | None = None

    m = _PRICE_BELOW_RE.search(text)
    if m:
        kind, threshold, threshold_span = "price_below", Decimal(m.group(1)), m.span(1)
    else:
        m = _PRICE_ABOVE_RE.search(text)
        if m:
            kind, threshold, threshold_span = "price_above", Decimal(m.group(1)), m.span(1)

    if threshold is not None:
        threshold = threshold.quantize(_SIX_DP)  # contract rule 4

    # Qualifiers — only alongside a matched pattern (contract rule 1).
    dropped: tuple[str, ...] = ()
    if kind != "not_machine_checkable":
        found = [q.search(text) for q in _QUALIFIER_RES]
        dropped = tuple(
            qm.group(0) for qm in sorted((qm for qm in found if qm), key=lambda qm: qm.start())
        )

    # Embedded figures (contract rule 3). Track consumed spans so the
    # threshold and MA-labelled values are never double-counted.
    figures: list[EmbeddedFigure] = []
    consumed_spans: list[tuple[int, int]] = []
    if threshold_span is not None:
        consumed_spans.append(threshold_span)
    for ma in _MA_FIGURE_RE.finditer(text):
        span = ma.span(2)
        if threshold_span is not None and span == threshold_span:
            continue
        figures.append(EmbeddedFigure(label=f"{int(ma.group(1))}d MA", value=Decimal(ma.group(2))))
        consumed_spans.append(span)

    def _consumed(span: tuple[int, int]) -> bool:
        return any(span[0] < e and s < span[1] for s, e in consumed_spans)

    for dm in _DOLLAR_FIGURE_RE.finditer(text):
        if _consumed(dm.span(1)):
            continue
        figures.append(EmbeddedFigure(label="", value=Decimal(dm.group(1))))
        consumed_spans.append(dm.span(1))

    # Price-like clause (contract rule 2) — only meaningful when unparseable.
    price_like_clause: str | None = None
    if kind == "not_machine_checkable":
        pm = _PRICE_LIKE_RE.search(text)
        if pm:
            price_like_clause = pm.group(0)

    echo = _build_echo(kind, threshold, dropped, tuple(figures), price_like_clause)
    return ParsedCondition(
        kind=kind,
        threshold=threshold,
        dropped_qualifiers=dropped,
        embedded_figures=tuple(figures),
        echo=echo,
    )


def _build_echo(
    kind: Kind,
    threshold: Decimal | None,
    dropped: tuple[str, ...],
    figures: tuple[EmbeddedFigure, ...],
    price_like_clause: str | None,
) -> str:
    """Build the verbatim enforcement_note line. The migration 0042 backfill
    rows are hand-transliterations of this exact output — pinned by
    tests/test_condition_parser.py::test_migration_0042_baselines_match_parser."""
    if kind == "not_machine_checkable":
        echo = "NOT MACHINE-CHECKED — manual review only."
        if price_like_clause is not None:
            echo += f" Contains a price-like clause ('{price_like_clause}') that is NOT enforced."
    else:
        op = "<" if kind == "price_below" else ">"
        echo = f"will enforce: close {op} {threshold}."
        for q in dropped:
            echo += f" Qualifier '{q}' NOT enforced (recorded narrowing)."
    for fig in figures:
        if fig.label:
            echo += (
                f" Contains frozen embedded value '{fig.label} (${fig.value})' "
                "(authoring-time; re-derived by sweep)."
            )
    return echo


def lint_echo(texts: Sequence[str]) -> str:
    """Authoring echo block for a set of conditions, e.g.::

        what I will enforce: [1] close < 230.000000 (qualifier 'on volume' NOT enforced)
        conditions 2-4 NOT machine-checked — manual review only
    """
    enforced_parts: list[str] = []
    unchecked: list[int] = []
    for i, text in enumerate(texts, start=1):
        p = parse_condition(text)
        if p.kind == "not_machine_checkable":
            unchecked.append(i)
            continue
        op = "<" if p.kind == "price_below" else ">"
        part = f"[{i}] close {op} {p.threshold}"
        for q in p.dropped_qualifiers:
            part += f" (qualifier '{q}' NOT enforced)"
        enforced_parts.append(part)

    lines: list[str] = []
    if enforced_parts:
        lines.append("what I will enforce: " + "; ".join(enforced_parts))
    else:
        lines.append("what I will enforce: nothing — no machine-checkable conditions")
    if unchecked:
        lines.append(f"{_condition_ref(unchecked)} NOT machine-checked — manual review only")
    return "\n".join(lines)


def _condition_ref(ordinals: list[int]) -> str:
    """[3] → 'condition 3'; [2,3,4] → 'conditions 2-4'; [2,4] → 'conditions 2, 4'."""
    if len(ordinals) == 1:
        return f"condition {ordinals[0]}"
    runs: list[str] = []
    start = prev = ordinals[0]
    for n in ordinals[1:]:
        if n == prev + 1:
            prev = n
            continue
        runs.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = n
    runs.append(f"{start}-{prev}" if start != prev else str(start))
    return "conditions " + ", ".join(runs)


def evaluate(parsed_kind: str, threshold: Decimal, close: Decimal) -> bool:
    """price_below → close < threshold; price_above → close > threshold.

    Callers must never pass not_machine_checkable — that is a manual-review
    condition and evaluating it mechanically would be exactly the silent-skip
    class register #5 exists to kill. Decimal in, Decimal compared; never
    float (CLAUDE.md #5).
    """
    if parsed_kind == "price_below":
        return close < threshold
    if parsed_kind == "price_above":
        return close > threshold
    raise ValueError(
        f"evaluate() got kind {parsed_kind!r} — only price_below/price_above are "
        "machine-evaluable; not_machine_checkable conditions are manual-review only."
    )
