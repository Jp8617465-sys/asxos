"""Theme domain types — M-Thesis-1.

Supersedes the M-Thesis-0 stub. All fields mirror the `themes` and
`theme_holdings` tables in migration 0012_theses_and_themes.sql.

Design decisions:
  - `theme_holdings` PK is (theme_id, symbol) per spec Part 6.3.
    Theme exposure is a property of the stock, not a thesis. Persists across
    thesis lifecycle. Cross-thesis exposure query:
      WHERE symbol IN (SELECT symbol FROM theses WHERE status = 'active')
  - `stage` enum is 6-value per spec Part 6.2 ('early', 'early-institutional',
    'broad-institutional', 'mainstream', 'late-retail', 'mature').
  - `stage_suggested` is written by M-Theme-Stage-Detection (future milestone);
    None if classifier has not run or theme is too new.
  - `adjacent_codes` is user-maintained (D6); bidirectional — see add_adjacency().
  - `retired_at` is a DATE (not a status value). None = active theme.
  - `exposure_strength` is NUMERIC(8,6) in [0, 1] — fraction, not percent.

References:
  spec Part 6.2 (themes schema)
  spec Part 6.3 (theme_holdings schema)
  M-THESIS-1_IMPLEMENTATION_PLAN_V2.md §3.1, §3.4, §4 Phase 2
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Theme:
    """Mirrors the `themes` table (migration 0012).

    conviction_band: user's conviction in the theme thesis.
      'low' | 'medium' | 'high'

    stage: manually confirmed lifecycle position.
      'early' | 'early-institutional' | 'broad-institutional' |
      'mainstream' | 'late-retail' | 'mature'
    Set via `asx theme stage CODE STAGE --note ...`

    stage_suggested: output of M-Theme-Stage-Detection auto-classifier.
    None until classifier runs. User confirms or overrides via set_stage().

    adjacent_codes: related theme_codes (e.g. neighbouring themes).
    Maintained bidirectionally via ThemeService.add_adjacency().

    retired_at: date theme was retired. None = still active and investable.
    """

    theme_id: int
    theme_code: str  # slug: 'ai-infrastructure', 'lithium-oversupply-unwinding'
    name: str
    description: str
    conviction_band: str  # 'low' | 'medium' | 'high'
    stage: str  # 'early' | 'early-institutional' | 'broad-institutional' | 'mainstream' | 'late-retail' | 'mature'
    stage_suggested: str | None  # D8: auto-classifier output (M-Theme-Stage-Detection)
    adjacent_codes: tuple[str, ...]  # D6: user-maintained adjacency list
    started_at: date
    retired_at: date | None  # None = active theme
    last_reviewed_at: datetime
    # Governance provenance/approval fields (migration 0035). Orthogonal to
    # retired_at (investment lifecycle): governance_status answers "is this
    # content trustworthy enough to exist", matching theses.governance_status
    # (migration 0033). DEFAULT 'approved' matches the DB grandfather default.
    macro_thesis_id: int | None = None
    governance_status: str = "approved"
    source_run_id: int | None = None


@dataclass(frozen=True)
class ThemeHolding:
    """One row in theme_holdings — PK is (theme_id, symbol).

    Theme exposure is a property of the stock, not a specific thesis.
    This row persists across thesis lifecycle — it represents the enduring
    relationship between a symbol and a theme.

    exposure_strength: fraction in [0, 1].
      0.65 means ~65% of the thesis on this symbol is driven by the theme.
      DB CHECK: 0 <= exposure_strength <= 1.

    direction: 'positive' (benefits from theme) or 'negative' (hurt by theme).

    mechanism_text: free-text explanation, e.g.
      "CBA benefits from higher rates via wider net interest margin".

    source:
      'user'           — manually set via CLI
      'llm_inferred'   — M-LLM-Thesis-Structuring output (future milestone)
      'system_default' — placeholder when attach_theme called without strength
    """

    theme_id: int
    symbol: str  # no FK to universe; watchlist names may not be in universe
    exposure_strength: Decimal  # fraction in [0, 1]
    direction: str  # 'positive' | 'negative'
    mechanism_text: str
    source: str  # 'user' | 'llm_inferred' | 'system_default'
    last_validated_at: datetime
    note: str | None
    created_at: datetime
    # Governance provenance/approval fields (migration 0035). holding_id is
    # the surrogate key added because the natural PK (theme_id, symbol) is
    # composite and governance_events.object_id needs one BIGINT uniformly.
    # DEFAULT 'approved' matches the DB grandfather default, except
    # source='system_default' rows, which are backfilled to 'draft' —
    # see migration 0035's comment for why.
    holding_id: int | None = None
    governance_status: str = "approved"
    source_run_id: int | None = None
