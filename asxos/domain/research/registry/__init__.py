"""Research registry — Stage 2 (target-architecture.md §15).

Contracts (`types.py`), a reproducible Decimal-only evaluation harness
(`harness.py`), the paper-promotion state machine (`promotion.py`), the
append-only repository (`repository.py`), and the price-panel loader
(`loader.py`).

What this package is NOT: a signal engine, an allocator input, or a path to
capital. `PromotionState` has no capital value by construction, and the
package imports nothing from `asxos.domain.portfolio` or
`asxos.domain.models`. A research result reaches capital only through a
human-written, governed thesis — the path the decision engine gates.
"""
from __future__ import annotations

from asxos.domain.research.registry.harness import EvaluationResult, evaluate_momentum_12_1
from asxos.domain.research.registry.promotion import (
    PROMOTION_STATES,
    PromotionState,
    advance,
)
from asxos.domain.research.registry.types import (
    ResearchHypothesis,
    ResearchRun,
    StrategyVersion,
)

__all__ = [
    "PROMOTION_STATES",
    "EvaluationResult",
    "PromotionState",
    "ResearchHypothesis",
    "ResearchRun",
    "StrategyVersion",
    "advance",
    "evaluate_momentum_12_1",
]
