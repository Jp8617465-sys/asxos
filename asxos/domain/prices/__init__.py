"""Price-domain helpers (coverage / completeness).

Read-only utilities. The date-anchor readers are advisory/unwired; the only
production consumer is ``classify_sync_completeness`` (used by ``sync_prices``
for non-gating completeness logging — see ``coverage.py``).
"""
from asxos.domain.prices.coverage import (
    DateCoverage,
    PriceDateStatus,
    SyncCompleteness,
    classify_coverage,
    classify_row_count,
    classify_sync_completeness,
    complete_threshold,
    is_stale,
    latest_complete_trading_day,
    latest_observed_price_date,
    select_latest_complete,
    trailing_median_row_count,
)

__all__ = [
    "DateCoverage",
    "PriceDateStatus",
    "SyncCompleteness",
    "classify_coverage",
    "classify_row_count",
    "classify_sync_completeness",
    "complete_threshold",
    "is_stale",
    "latest_complete_trading_day",
    "latest_observed_price_date",
    "select_latest_complete",
    "trailing_median_row_count",
]
