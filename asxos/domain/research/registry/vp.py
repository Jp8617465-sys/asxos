"""The sealed pre-registration for the value-to-price predictive test.

WHY THIS EXISTS. The residual-income model went live on 2026-09-16 and has
never been tested against a realised return: `research_runs` and
`strategy_versions` were both empty while the model was already emitting target
prices, entry bands, stops and horizons for 23 named securities. Model A was
quarantined for exactly that shape of claim (rule #11) and Model A had 19,032
matured observations when it died. This one had none.

WHAT THE SEAL IS, AND WHY IT IS STRONGER THAN A FILE HASH. The valuation
pre-registration seals itself with a `content_hash` over a bundled JSON. This
one is sealed by the database: `research_hypotheses` is append-only under
migration 0050's BEFORE UPDATE OR DELETE trigger and its `content_hash` is
UNIQUE, so once the row is registered it cannot be edited, and any change to
the statement below produces a different hash — a NEW hypothesis with its own
id, never a re-seal of this one. Registering it BEFORE the first replay row
exists is what makes the commitment real rather than ceremonial.

THE PRE-COMMITMENT THAT MATTERS. A test whose failure branch is unwritten is a
machine that can only say yes. James ruled the response on 2026-09-16, before
any result existed, and `RESPONSE_RULE` below carries it verbatim. It is
deliberately asymmetric: an underpowered null is NOT treated as disconfirming,
because with ~5 quasi-independent cutoffs it genuinely cannot be.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Final

from asxos.domain.research.registry.types import ResearchHypothesis, StrategyVersion

HYPOTHESIS_ID: Final[str] = "hyp-value-to-price-asx-quarterly-v1"
STRATEGY_ID: Final[str] = "sv-vp-zero-excess-quintile-25bp-v1"

#: The PRIMARY endpoint. One test, fixed before the data was seen. 126 sessions
#: (~6 months) is the middle horizon: at 434 sessions of price history it leaves
#: five quarterly cutoffs with a complete forward window, where 252 sessions
#: leaves three and 63 leaves seven but measures a horizon shorter than the
#: weeks-to-months the theses are held for.
PRIMARY_HORIZON_SESSIONS: Final[int] = 126
PRIMARY_CONVENTION: Final[str] = "zero_excess"

#: Declared secondary reporting — NOT additional primary tests. Reported
#: alongside the primary so the surface examined is visible rather than hidden,
#: and counted in `variants_tried` on the run for exactly that reason.
SECONDARY_HORIZONS_SESSIONS: Final[tuple[int, ...]] = (63, 252)
SECONDARY_CONVENTIONS: Final[tuple[str, ...]] = ("fading_excess_w050", "average_roe")

#: 3 conventions x 3 horizons. Declared here, before the run, so the count in
#: the run's `multiple_testing` block cannot be quietly chosen afterwards.
TOTAL_SURFACE_EXAMINED: Final[int] = 9

#: Ruled by James 2026-09-16, before any result existed. S4 applies this; a test
#: pins this string so the branch cannot be softened after a disappointing read.
RESPONSE_RULE: Final[str] = (
    "NULL (no monotonic value-to-price -> forward-return relation, or a relation "
    "indistinguishable from zero): the model is DEMOTED to a discipline device. It "
    "must still state a falsifiable number per thesis, but stops emitting target "
    "prices, entry bands and ranked 'opportunities'. A null here reads as "
    "UNDERPOWERED, NOT DISCONFIRMING — five quasi-independent cutoffs cannot "
    "detect an effect of the size the literature reports. "
    "NEGATIVE MONOTONIC (conviction inverted at the top, the Model A signature): "
    "full rule-#11-style QUARANTINE. No valuation output feeds a thesis, a packet "
    "or a target until a NEW registered model version passes this same bar. "
    "POSITIVE MONOTONIC: the model keeps its current standing and nothing is "
    "promoted — a pass is not a licence to size, and no research result reaches "
    "capital except by a human writing a governed thesis."
)

#: Stated before the run so it cannot be produced afterwards as an excuse.
POWER_STATEMENT: Final[str] = (
    "prices begin 2025-01-02 (434 sessions to 2026-09-15), so at a 126-session "
    "horizon there are five quarterly cutoffs with a complete forward window. The "
    "power lives in the cross-section (500-1,500 names per cutoff), not the time "
    "series. Detecting a decile spread of the magnitude Frankel-Lee report is not "
    "reliably possible in this sample; that is why a null is underpowered rather "
    "than disconfirming, and why no positive read licences a size."
)


def vp_hypothesis(now: datetime) -> ResearchHypothesis:
    """The falsifiable statement, registered before the first replay row exists."""
    return ResearchHypothesis(
        hypothesis_id=HYPOTHESIS_ID,
        title="Residual-income value-to-price predicts cross-sectional ASX returns",
        statement=(
            "Ranking ASX equities by the registered residual-income value-to-price "
            "ratio, computed point-in-time at a quarterly cutoff using only "
            "fundamentals whose knowledge_date precedes that cutoff, produces a "
            "positive and MONOTONIC relation between value-to-price quintile and "
            "subsequent 126-session total return, net of 25bp per side. Primary "
            "endpoint: the mean across cutoffs of the per-cutoff cross-sectional "
            "Spearman rank correlation between value-to-price and forward return, "
            "under the zero_excess terminal convention. Monotonicity is judged on "
            "the quintile ladder, not on the top quintile alone, because an "
            "inverted ladder with a strong top decile is the failure Model A hid."
        ),
        factor="value_to_price",
        universe_rule=(
            "valuation_runs at the replay cutoff WHERE outcome = 'valued' AND the "
            "symbol has both a cutoff and a forward close in prices; PIT-correct by "
            "construction (knowledge_date <= cutoff, asserted by test). Marked-book "
            "instruments (LICs, LITs, A-REITs) are FLAGGED in the result rather than "
            "excluded, because excluding them after seeing the 2026-09-16 candidate "
            "set would be a choice made on the data."
        ),
        rebalance="quarterly",
        horizon_trading_days=PRIMARY_HORIZON_SESSIONS,
        cost_bps_per_side=Decimal("25"),
        falsifier=(
            f"{RESPONSE_RULE} "
            f"POWER, stated before the run: {POWER_STATEMENT} "
            f"SURFACE: {TOTAL_SURFACE_EXAMINED} combinations "
            f"({PRIMARY_CONVENTION} + {', '.join(SECONDARY_CONVENTIONS)}) x "
            f"({PRIMARY_HORIZON_SESSIONS} + "
            f"{', '.join(str(h) for h in SECONDARY_HORIZONS_SESSIONS)} sessions), "
            "declared here before any was run. The decision rests on the PRIMARY "
            f"({PRIMARY_CONVENTION} at {PRIMARY_HORIZON_SESSIONS} sessions) alone; "
            "the rest are reported as declared secondaries and never re-designated "
            "as primary afterwards."
        ),
        registered_by="arbi, on James's ruling 2026-09-16 (response rule pre-committed)",
        created_at=now,
    )


def vp_strategy(now: datetime) -> StrategyVersion:
    """The concrete parameterisation, bound to the evaluator that runs it."""
    return StrategyVersion(
        strategy_version_id=STRATEGY_ID,
        hypothesis_id=HYPOTHESIS_ID,
        parameters={
            "terminal_convention": PRIMARY_CONVENTION,
            "horizon_trading_days": str(PRIMARY_HORIZON_SESSIONS),
            "cost_bps_per_side": "25",
            "quantiles": "5",
            "min_symbols_per_cutoff": "50",
            "rebalance": "quarterly",
        },
        code_ref="asxos.domain.research.registry.vp_harness:evaluate_value_to_price",
        created_at=now,
    )
