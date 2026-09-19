"""The mandate layer (migration 0061).

James's ruling, 2026-09-19: *"the financial agents should decide capital and
structure from my income goals and future ambitions."* A `Goals` contract is
what he states; `derive()` turns it into a `Mandate` — deployable capital,
cash floor, minimum position, feasible name count, per-name cap, stop band,
risk per position, ETF-core share, sleeve allocations — every figure carrying
the register line it traces to; the memo is what he ratifies with one line
from his phone (`MANDATE approve <id> <reason>`).

A ratified mandate is the capital/risk calibration ADR D1 §1.1 records as
"set without (a) drawdown tolerance or (b) liquidity calls being supplied"
and the P5-01 ruling (james-inbox H-32) every Stage 4 packet has closed
`abstain` on. It resolves that by derivation plus one ratification.

Pure Decimal domain code: no DB driver, no template engine, no floats.
"""
from asxos.domain.mandate.derive import DERIVATION_VERSION, derive
from asxos.domain.mandate.types import Goals, LiquidityNeed, Mandate, MandateOutputs, Traced

__all__ = [
    "DERIVATION_VERSION",
    "Goals",
    "LiquidityNeed",
    "Mandate",
    "MandateOutputs",
    "Traced",
    "derive",
]
