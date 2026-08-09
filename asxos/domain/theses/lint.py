"""Shared thesis-rule lint — one implementation for every surface (0042, D2/R1).

Consumed by service.open_thesis / service.revise_thesis / service.attest_thesis,
the CLI echo, and the R8 sweep (jobs/sweep_rule_integrity.py). Pure module:
Decimal-only, no DB, no I/O — callers fetch the latest close themselves and
pass it in (born-breached is the one cross-table check, which is exactly why
it cannot be a DB CHECK and lives here + in the sweep instead; KD-4).

The ladder predicates mirror the theses_ladder_coherent_long_v1 CHECK
(migration 0042) exactly — the service raises the readable error, the CHECK
is the backstop. v1 LONG-ONLY: a future short/direction column must make
these direction-aware.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Finding codes — shared vocabulary with the R8 sweep's integrity_flag rows.
LADDER_INCOHERENT = "LADDER_INCOHERENT"
BAND_DEGENERATE = "BAND_DEGENERATE"
BORN_BREACHED = "BORN_BREACHED"
UNATTESTED_WITH_CAPITAL = "UNATTESTED_WITH_CAPITAL"


@dataclass(frozen=True)
class LintFinding:
    code: str
    message: str


def lint_ladder(
    *,
    stop_price: Decimal | None,
    entry_band_lower: Decimal | None,
    entry_band_upper: Decimal | None,
    target_price: Decimal | None,
) -> list[LintFinding]:
    """Pairwise strict ladder coherence (stop < lower < upper < target),
    NULL-tolerant per pair — the exact predicates of the attestation-gated
    DB CHECK. A degenerate point band (lower == upper) gets its own code
    (E02: point bands are a systematic authoring artifact, not intent)."""
    findings: list[LintFinding] = []
    lo, hi = entry_band_lower, entry_band_upper
    if lo is not None and hi is not None:
        if lo == hi:
            findings.append(LintFinding(
                BAND_DEGENERATE,
                f"entry band is a point ({lo}) — a real band needs lower < upper",
            ))
        elif lo > hi:
            findings.append(LintFinding(
                LADDER_INCOHERENT,
                f"entry_band_lower ({lo}) > entry_band_upper ({hi})",
            ))
    if stop_price is not None and lo is not None and not stop_price < lo:
        findings.append(LintFinding(
            LADDER_INCOHERENT,
            f"stop_price ({stop_price}) must be strictly below entry_band_lower ({lo})",
        ))
    if hi is not None and target_price is not None and not hi < target_price:
        findings.append(LintFinding(
            LADDER_INCOHERENT,
            f"entry_band_upper ({hi}) must be strictly below target_price ({target_price})",
        ))
    if stop_price is not None and target_price is not None and not stop_price < target_price:
        findings.append(LintFinding(
            LADDER_INCOHERENT,
            f"stop_price ({stop_price}) must be strictly below target_price ({target_price})",
        ))
    return findings


def lint_born_breached(
    *, stop_price: Decimal | None, latest_close: Decimal | None
) -> LintFinding | None:
    """The BB gate: a stop at/above the latest close is already breached the
    moment it is written (long-only v1). Service-only cross-table check —
    attest_thesis() hard-fails on it; the sweep flags it on underwritten rows."""
    if stop_price is None or latest_close is None:
        return None
    if latest_close <= stop_price:
        return LintFinding(
            BORN_BREACHED,
            f"stop_price ({stop_price}) is at/above the latest close ({latest_close}) "
            "— the stop is already breached as written",
        )
    return None


def lint_unattested_with_capital(*, attestation: str, status: str) -> LintFinding | None:
    """Capital deployed against a placeholder — should be unreachable through
    enter_thesis() (which hard-fails), so a hit means the state was reached
    out-of-band; the sweep surfaces it loudly rather than assuming."""
    if status == "active" and attestation != "underwritten":
        return LintFinding(
            UNATTESTED_WITH_CAPITAL,
            f"status='active' with attestation={attestation!r} — capital is deployed "
            "against an unattested rule set (D4/R9)",
        )
    return None
