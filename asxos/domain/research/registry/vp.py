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
because with four heavily-overlapping cutoffs it genuinely cannot be.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Final

from asxos.domain.research.registry.types import ResearchHypothesis, StrategyVersion

HYPOTHESIS_ID: Final[str] = "hyp-value-to-price-asx-quarterly-v1"
STRATEGY_ID: Final[str] = "sv-vp-zero-excess-quintile-25bp-v1"

#: The PRIMARY endpoint. One test, fixed before the data was seen. 126 sessions
#: (~6 months) is the middle horizon: at 433 sessions of price history it leaves
#: four quarterly cutoffs with a complete forward window, where 252 leaves two
#: and 63 leaves five but measures a horizon shorter than the weeks-to-months
#: the theses are held for.
PRIMARY_HORIZON_SESSIONS: Final[int] = 126
PRIMARY_CONVENTION: Final[str] = "zero_excess"

#: Measured against the live session calendar (433 distinct .AU sessions,
#: 2025-01-02 to 2026-09-15) BEFORE sealing, because an estimate in a sealed
#: document is a number nobody can correct afterwards. Quarter-ends with a
#: complete forward window: FOUR at 126 sessions (2025-03-31, 06-30, 09-30,
#: 12-31), five at 63, two at 252. An earlier draft of this module said "five"
#: at 126; 2026-03-31 has only 117 forward sessions and does not qualify.
QUALIFYING_CUTOFFS_AT_PRIMARY: Final[int] = 4
PRIMARY_CUTOFFS: Final[tuple[str, ...]] = (
    "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31",
)

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
    "UNDERPOWERED, NOT DISCONFIRMING — four overlapping cutoffs cannot detect "
    "an effect of the size the literature reports. "
    "NEGATIVE MONOTONIC (conviction inverted at the top, the Model A signature): "
    "full rule-#11-style QUARANTINE. No valuation output feeds a thesis, a packet "
    "or a target until a NEW registered model version passes this same bar. "
    "POSITIVE MONOTONIC: the model keeps its current standing and nothing is "
    "promoted — a pass is not a licence to size, and no research result reaches "
    "capital except by a human writing a governed thesis."
)

#: DISCLOSURE: the data WAS looked at once before this was sealed, and pretending
#: otherwise would be the exact dishonesty a pre-registration exists to prevent.
#:
#: On 2026-09-16, before registering, arbi ran one exploratory read-only ladder at
#: the 2025-03-31 cutoff and found the specification broken in a way that had
#: nothing to do with the hypothesis: across all 1,782 priced names the mean
#: 126-session return was +632% against a median of +13.9%, with a maximum of
#: +833,230% on a stock trading at A$0.0001. Bucket MEANS are meaningless under
#: that tail. Screening to ADV >= A$250k and close >= A$0.20 gives n=434, mean
#: +22.8%, median +11.8%.
#:
#: WHAT CHANGED AS A RESULT, and why it is an estimator fix rather than a tuned
#: result: (a) the ladder is judged on the MEDIAN forward return per bucket, not
#: the mean, because cross-sectional equity returns are universally right-tailed;
#: (b) a liquidity and minimum-price screen is declared, as every cross-sectional
#: study applies and as this repo's own `quality-liquid-au-equity-v1` screen
#: already does. Neither was chosen from the direction of the result: the probe's
#: ladder was 0.22 / 1.10 / 1.09 / 0.17 / 1.04 — noise with no monotonic pattern.
#:
#: WHAT THE PROBE DID NOT REVEAL: the primary endpoint. The Spearman rank
#: correlation is rank-based and therefore was ALREADY immune to the tail that
#: broke the ladder — it was never recomputed under the corrected screen before
#: sealing. The endpoint that decides the verdict remains unseen.
PRE_SEAL_PROBE: Final[str] = (
    "One exploratory read-only ladder was run at the 2025-03-31 cutoff on "
    "2026-09-16 before sealing. It showed the bucket-mean estimator is destroyed "
    "by sub-cent stocks (all-names mean +632% vs median +13.9%, max +833,230% at "
    "a A$0.0001 close). In response the ladder moved to MEDIAN and a liquidity / "
    "minimum-price screen was declared — both standard practice for a "
    "cross-section, neither chosen from the direction of the result (the probe's "
    "ladder was flat noise). The primary endpoint, the Spearman rank correlation, "
    "is rank-based and was not recomputed under the corrected screen before "
    "sealing: it remains unseen."
)

#: Declared screen. Not a free parameter discovered mid-run: ADV matches the
#: baseline inquiry's liquid cohort and the minimum price removes the sub-cent
#: names whose percentage moves are quotation artefacts, not returns.
MIN_ADV_AUD: Final[int] = 250_000
MIN_CLOSE_AUD: Final[str] = "0.20"

#: Stated before the run so it cannot be produced afterwards as an excuse.
POWER_STATEMENT: Final[str] = (
    "prices begin 2025-01-02 (433 .AU sessions to 2026-09-15), so at a 126-session "
    "horizon there are FOUR quarter-end cutoffs with a complete forward window "
    "(2025-03-31, 06-30, 09-30, 12-31) — counted against the live calendar before "
    "sealing, not estimated. Worse, a 126-session horizon is about six months "
    "while the cutoffs are three months apart, so consecutive forward windows "
    "OVERLAP by roughly half and the four are not four independent observations. "
    "The power therefore lives entirely in the cross-section (1,500-1,800 names "
    "per cutoff), not the time series. Detecting a spread of the magnitude "
    "Frankel-Lee report is not reliably possible here. That is why a null reads "
    "as underpowered rather than disconfirming, and why no positive read "
    "licences a size."
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
            "the quintile ladder by MEDIAN forward return, not on the top quintile "
            "alone and not on bucket means, because an inverted ladder with a strong "
            "top decile is the failure Model A hid and because bucket means in this "
            "cross-section are dominated by sub-cent quotation artefacts."
        ),
        factor="value_to_price",
        universe_rule=(
            "Common stocks TRADING at the cutoff (a close inside the pre-registered "
            "window; rs_security_master.security_type = 'Common Stock') — NOT "
            "universe.is_active, which is current listing status and drops every name "
            "delisted since. Valued by the registered model on point-in-time inputs "
            f"(knowledge_date <= cutoff, asserted by test), then screened to ADV >= "
            f"A${MIN_ADV_AUD:,} and close >= A${MIN_CLOSE_AUD} — see PRE_SEAL_PROBE for "
            "why that screen is declared and on what grounds. Marked-book instruments "
            "(LICs, LITs, A-REITs) are FLAGGED in the result rather than excluded, "
            "because excluding them after seeing the 2026-09-16 candidate set would be "
            "a choice made on the data."
        ),
        rebalance="quarterly",
        horizon_trading_days=PRIMARY_HORIZON_SESSIONS,
        cost_bps_per_side=Decimal("25"),
        falsifier=(
            f"{RESPONSE_RULE} "
            f"POWER, stated before the run: {POWER_STATEMENT} "
            f"PRE-SEAL PROBE (disclosed, not hidden): {PRE_SEAL_PROBE} "
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
            "ladder_statistic": "median",
            "min_adv_aud": str(MIN_ADV_AUD),
            "min_close_aud": MIN_CLOSE_AUD,
            "min_symbols_per_cutoff": "50",
            "rebalance": "quarterly",
        },
        code_ref="asxos.domain.research.registry.vp_harness:evaluate_value_to_price",
        created_at=now,
    )
