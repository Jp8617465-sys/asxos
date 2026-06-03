"""
Position monitor domain service — M-Position-Monitor.

build_monitor_result()        — pure; no DB I/O.
load_position_context()       — loads thesis + lot data from DB.
get_last_sentiment_inputs()   — returns last retail_ratio / news_sentiment for CLI defaults.
save_run()                    — appends MonitorResult to position_monitor_runs.
list_runs()                   — returns recent runs newest-first.

Underlying handling:
  If the symbol has a thesis with attached underlyings in DB → use those.
  Otherwise → use two default macro underlyings (VIX + US HY OAS, negative direction).
  Both paths feed into score_thesis_underlying() identically.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta

from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.position_monitor.types import (
    MonitorInput,
    MonitorResult,
    ScenarioState,
)
from asxos.domain.themes.stage_classifier import (
    ClassifierInput,
    StageThresholds,
    classify_stage,
)
from asxos.domain.underlyings.attribution import score_thesis_underlying
from asxos.domain.underlyings.types import ThesisUnderlying, UnderlyingDirection

_T = StageThresholds()

# Synthetic IDs for default underlyings (no DB row; negative namespace).
_VIX_ID = -1
_HY_OAS_ID = -2

_DEFAULT_UNDERLYINGS: list[ThesisUnderlying] = [
    ThesisUnderlying(
        thesis_id=0, underlying_id=_VIX_ID, code="vix",
        exposure=Decimal("0.50"), direction=UnderlyingDirection.negative,
        last_validated_at=None,
    ),
    ThesisUnderlying(
        thesis_id=0, underlying_id=_HY_OAS_ID, code="us_hy_oas",
        exposure=Decimal("0.50"), direction=UnderlyingDirection.negative,
        last_validated_at=None,
    ),
]


def _above_pct(price: Decimal, ma: Decimal) -> Decimal:
    return Decimal("1.0") if price > ma else Decimal("0.0")


def _moves_for_underlyings(
    underlyings: list[ThesisUnderlying],
    vix_5d: Decimal,
    hy_oas_5d: Decimal,
) -> dict[int, Decimal | None]:
    """Map underlying_id → 5d move. Recognises vix and us_hy_oas by code."""
    moves: dict[int, Decimal | None] = {}
    for tu in underlyings:
        if tu.code == "vix":
            moves[tu.underlying_id] = vix_5d
        elif tu.code == "us_hy_oas":
            moves[tu.underlying_id] = hy_oas_5d
        else:
            moves[tu.underlying_id] = None
    return moves


def _build_scenarios(inputs: MonitorInput) -> tuple[ScenarioState, ...]:
    if inputs.cost_usd is None or inputs.acquired is None:
        return ()

    price = inputs.current_price
    cost = inputs.cost_usd
    unrealised_pct = ((price - cost) / cost * Decimal("100")).quantize(Decimal("0.1"))

    scenarios: list[ScenarioState] = []

    # D — Hold to CGT discount
    if inputs.cgt_date:
        days_to_cgt = (inputs.cgt_date - inputs.as_of).days
        status = "ON TRACK" if days_to_cgt > 0 else "ELIGIBLE NOW"
        stop_note = f" (${inputs.stop_price})" if inputs.stop_price else ""
        scenarios.append(ScenarioState(
            code="D",
            name=f"Hold to CGT discount ({inputs.cgt_date})",
            status=status,
            confirmation=(
                f"{max(0, days_to_cgt)} days remaining. "
                "Best risk-adjusted after-tax outcome."
            ),
            invalidation=f"Stop triggered{stop_note} OR stage flips to EARLY",
        ))

    # B — Stop loss
    if inputs.stop_price:
        pct_buffer = ((price - inputs.stop_price) / price * Decimal("100")).quantize(
            Decimal("0.1")
        )
        stop_status = "active" if price > inputs.stop_price else "TRIGGERED"
        scenarios.append(ScenarioState(
            code="B",
            name=f"Stop at ${inputs.stop_price}",
            status=stop_status,
            confirmation=f"Stop intact — {pct_buffer}% buffer above ${inputs.stop_price}.",
            invalidation=f"Price breaks below ${inputs.stop_price} on volume → exit",
        ))

    # A — Sell now
    sell_status = "confirmed" if unrealised_pct > Decimal("20") else "available"
    scenarios.append(ScenarioState(
        code="A",
        name="Sell Now",
        status=sell_status,
        confirmation=f"Current gain: +{unrealised_pct}%. Valid exit at any time.",
        invalidation=f"Price falls below cost basis (${cost})",
    ))

    return tuple(scenarios)


# ---------------------------------------------------------------------------
# Core pure function
# ---------------------------------------------------------------------------

def build_monitor_result(
    inputs: MonitorInput,
    thesis_underlyings: list[ThesisUnderlying] | None = None,
) -> MonitorResult:
    """Classify stage + score underlyings + cross-layer. No DB I/O."""
    underlyings = thesis_underlyings if thesis_underlyings else _DEFAULT_UNDERLYINGS

    stage_result = classify_stage(
        ClassifierInput(
            price_history_days=252,
            pct_above_50d_ma=_above_pct(inputs.current_price, inputs.ma_50d),
            pct_above_200d_ma=_above_pct(inputs.current_price, inputs.ma_200d),
            avg_weekly_move_pct=inputs.avg_weekly_move,
            news_sentiment=inputs.news_sentiment,
            retail_mention_ratio=inputs.retail_ratio,
        ),
        _T,
    )
    stage_label, conditions = stage_result if stage_result else ("insufficient_data", [])

    moves = _moves_for_underlyings(underlyings, inputs.vix_5d_move, inputs.hy_oas_5d_move)
    score = score_thesis_underlying(underlyings, moves)
    cross_obs = cross_layer_observations(
        inputs.regime_label,
        [(inputs.symbol, "active", score)],
    )

    return MonitorResult(
        inputs=inputs,
        stage_label=stage_label,
        conditions_fired=conditions,
        underlying_label=score.label,
        weighted_movement=score.weighted_movement,
        component_moves=score.component_moves,
        cross_layer_obs=tuple(cross_obs),
        scenarios=_build_scenarios(inputs),
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def load_position_context(conn: Any, symbol: str) -> dict:
    """Load thesis stop/target + lot cost/shares/acquired for a symbol.

    Returns an empty dict if no active thesis is found.
    """
    row = await conn.fetchrow(
        """
        SELECT t.thesis_id,
               t.stop_price,
               t.target_price,
               t.analyst_buy_count,
               t.analyst_neutral_count,
               t.analyst_sell_count,
               t.analyst_consensus_target,
               hl.cost_base_normal,
               hl.quantity,
               hl.acquired_at   AS lot_acquired_at,
               hl.account_type  AS lot_account_type
        FROM   theses t
        LEFT   JOIN holding_lots hl
               ON  hl.symbol = t.symbol
               AND hl.disposed_at IS NULL
        WHERE  t.symbol = $1
          AND  t.status  = 'active'
        ORDER  BY t.opened_at DESC
        LIMIT  1
        """,
        symbol,
    )
    if not row:
        return {}

    acquired = row["lot_acquired_at"]
    cgt_date = (
        acquired + relativedelta(years=1) + timedelta(days=1)
        if acquired is not None
        else None
    )
    cost_per_share = (
        row["cost_base_normal"] / row["quantity"]
        if row["cost_base_normal"] is not None and row["quantity"]
        else None
    )
    return {
        "thesis_id": row["thesis_id"],
        "stop_price": row["stop_price"],
        "target_price": row["target_price"],
        "cost_usd": cost_per_share,
        "shares": row["quantity"],
        "acquired": acquired,
        "cgt_date": cgt_date,
        "account_type": row["lot_account_type"] or "individual",
        "analyst_buy_count": row["analyst_buy_count"],
        "analyst_neutral_count": row["analyst_neutral_count"],
        "analyst_sell_count": row["analyst_sell_count"],
        "analyst_consensus_target": row["analyst_consensus_target"],
    }


async def get_last_sentiment_inputs(conn: Any, symbol: str) -> dict | None:
    """Return the most recent manual inputs for CLI defaults."""
    row = await conn.fetchrow(
        """
        SELECT retail_ratio, news_sentiment, volume_vs_avg_pct, short_interest_pct
        FROM   position_monitor_runs
        WHERE  symbol = $1
        ORDER  BY as_of DESC, created_at DESC
        LIMIT  1
        """,
        symbol,
    )
    return dict(row) if row else None


async def save_run(conn: Any, result: MonitorResult) -> int:
    """Insert a new run row. Returns run_id."""
    i = result.inputs
    run_id: int = await conn.fetchval(
        """
        INSERT INTO position_monitor_runs (
            symbol, as_of, current_price, ma_50d, ma_200d, avg_weekly_move,
            vix_5d_move, hy_oas_5d_move, retail_ratio, news_sentiment,
            stop_price, stage_label, underlying_label, weighted_movement,
            regime_label, price_type, volume_vs_avg_pct, short_interest_pct
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18
        )
        RETURNING run_id
        """,
        i.symbol, i.as_of, i.current_price, i.ma_50d, i.ma_200d,
        i.avg_weekly_move, i.vix_5d_move, i.hy_oas_5d_move,
        i.retail_ratio, i.news_sentiment, i.stop_price,
        result.stage_label, result.underlying_label, result.weighted_movement,
        i.regime_label, i.price_type, i.volume_vs_avg_pct, i.short_interest_pct,
    )
    return int(run_id)


async def list_runs(conn: Any, symbol: str, limit: int = 10) -> list[dict]:
    """Return recent runs for a symbol, newest-first."""
    rows = await conn.fetch(
        """
        SELECT run_id, as_of, current_price, stage_label, underlying_label,
               weighted_movement, retail_ratio, news_sentiment,
               vix_5d_move, hy_oas_5d_move, regime_label, created_at
        FROM   position_monitor_runs
        WHERE  symbol = $1
        ORDER  BY as_of DESC, created_at DESC
        LIMIT  $2
        """,
        symbol,
        limit,
    )
    return [dict(r) for r in rows]
