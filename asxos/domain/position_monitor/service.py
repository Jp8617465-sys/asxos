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

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta

from asxos.domain.brief.cross_layer import cross_layer_observations
from asxos.domain.position_monitor.types import (
    LotCgt,
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

async def load_position_context(
    conn: Any, symbol: str, *, account_type: str, as_of: date
) -> dict[str, Any]:
    """Load thesis stop/target + the active-account_type lot ladder for a symbol.

    `account_type` is the ACTIVE PROFILE's account type, resolved by the caller
    (the CLI composition root) and passed in. Lots are filtered to that account
    type and never pooled across types: an individual and their SMSF are separate
    CGT taxpayers (ITAA 1997 s 115-100), so the monitored position is the active
    taxpayer's alone. v2 = dual per-account sub-positions (out of v1 scope); do NOT
    "fix" this filter into a cross-account blend.

    `account_type` is keyword-only and required — a default would silently
    re-introduce the "assume individual" bug. Returns an empty dict if no active
    thesis is found.

    The headline scalars (`cost_usd` = weighted-average cost-per-share, `shares`,
    `cgt_date`) are derived from all matching open lots, and the full per-lot ladder
    is returned under `lots`. `cgt_date` is the earliest-still-ineligible lot's
    eligible date (the next tranche to mature) — None when there are no lots OR when
    every lot is already eligible; `all_eligible` disambiguates those two cases.
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
               agg.total_cost,
               agg.total_qty,
               agg.lots
        FROM   theses t
        LEFT   JOIN LATERAL (
            SELECT SUM(hl.cost_base_normal) AS total_cost,
                   SUM(hl.quantity)         AS total_qty,
                   jsonb_agg(jsonb_build_object(
                       'quantity',         hl.quantity,
                       'acquired_at',      hl.acquired_at,
                       'cost_base_normal', hl.cost_base_normal
                   ) ORDER BY hl.acquired_at, hl.id) AS lots
            FROM   holding_lots hl
            WHERE  hl.symbol = t.symbol
              AND  hl.disposed_at IS NULL
              AND  hl.quantity > 0
              AND  hl.account_type = $2
        ) agg ON TRUE
        WHERE  t.symbol = $1
          AND  t.status  = 'active'
        ORDER  BY t.opened_at DESC
        LIMIT  1
        """,
        symbol,
        account_type,
    )
    if not row:
        return {}

    lots, cost_per_share, total_qty, cgt_date, all_eligible = _build_lot_ladder(
        row["lots"], row["total_cost"], row["total_qty"], as_of,
    )
    return {
        "thesis_id": row["thesis_id"],
        "stop_price": row["stop_price"],
        "target_price": row["target_price"],
        "cost_usd": cost_per_share,
        "shares": total_qty,
        "acquired": lots[0].acquired_at if lots else None,
        "cgt_date": cgt_date,
        "account_type": account_type,
        "lots": lots,
        "all_eligible": all_eligible,
        "analyst_buy_count": row["analyst_buy_count"],
        "analyst_neutral_count": row["analyst_neutral_count"],
        "analyst_sell_count": row["analyst_sell_count"],
        "analyst_consensus_target": row["analyst_consensus_target"],
    }


def _build_lot_ladder(
    lots_raw: Any, total_cost: Decimal | None, total_qty: Decimal | None, as_of: date
) -> tuple[tuple[LotCgt, ...], Decimal | None, Decimal | None, date | None, bool]:
    """Parse the jsonb lot array into a typed CGT ladder + position headline scalars.

    §5.1 calendar arithmetic (acquired + 1yr + 1day) lives here, the single source
    of truth, matching cgt.is_discountable.
    """
    if not lots_raw:
        return (), None, None, None, False
    if isinstance(lots_raw, str):  # asyncpg may hand jsonb back as text
        lots_raw = json.loads(lots_raw)

    ladder: list[LotCgt] = []
    for entry in lots_raw:  # already ordered acquired_at ASC, id ASC
        acquired = date.fromisoformat(str(entry["acquired_at"])[:10])
        eligible = acquired + relativedelta(years=1) + timedelta(days=1)
        ladder.append(LotCgt(
            quantity=Decimal(str(entry["quantity"])),
            acquired_at=acquired,
            cost_base_normal=Decimal(str(entry["cost_base_normal"])),
            cgt_eligible_date=eligible,
            is_eligible=as_of >= eligible,
        ))

    cost_per_share = (total_cost / total_qty) if total_cost is not None and total_qty else None
    ineligible = [lot for lot in ladder if not lot.is_eligible]
    if not ineligible:
        cgt_date, all_eligible = None, True
    else:
        cgt_date = min(lot.cgt_eligible_date for lot in ineligible)
        all_eligible = False
    return tuple(ladder), cost_per_share, total_qty, cgt_date, all_eligible


async def get_last_sentiment_inputs(conn: Any, symbol: str) -> dict[str, Any] | None:
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


async def list_runs(conn: Any, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
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
