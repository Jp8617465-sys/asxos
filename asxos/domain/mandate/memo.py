"""The mandate memo — deterministic HTML over a Mandate. No template engine
(domain purity forbids jinja2 here), no LLM, no directive vocabulary.

The memo does not carry the mandate id: it is rendered before the row exists.
The brief adds the ratification line (`MANDATE approve <id> <reason>`) when
it renders the pending mandate, and the LLM polish (PR-6) reads this body as
its evidence and cites `[mandate:<field>]`.
"""
from __future__ import annotations

from decimal import Decimal
from html import escape

from asxos.domain.mandate.types import Goals, Mandate, Traced

_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("deployable_capital_aud", "Deployable capital (A$)"),
    ("liquidity_reserve_aud", "Liquidity reserve held back (A$)"),
    ("cash_floor_pct", "Cash floor (% of capital)"),
    ("min_position_aud", "Minimum position (A$)"),
    ("n_single_feasible", "Single names the book can hold"),
    ("position_cap_pct", "Per-name cap (%)"),
    ("equal_weight_pct", "Equal weight per name (%)"),
    ("stop_band_pct", "Stop-distance sanity band (%)"),
    ("risk_per_position_pct", "Capital at risk per position (%)"),
    ("portfolio_dd_review_pct", "Portfolio drawdown review level (%)"),
    ("etf_core_pct", "ETF core (% of deployable)"),
    ("turnover_budget_pct_pa", "Turnover budget (% p.a.)"),
)


def _fmt(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    return s if "." not in s else s.rstrip("0").rstrip(".") or "0"


def render_memo(goals: Goals, mandate: Mandate) -> str:
    """Plain, cited HTML: what was stated, what was derived, and why."""
    o = mandate.outputs
    rows = []
    for field, label in _FIELD_LABELS:
        t: Traced = getattr(o, field)
        rows.append(
            f"<tr><td>{escape(label)}</td><td class='num' data-field='{field}'>{_fmt(t.value)}</td>"
            f"<td class='trace'>{escape(t.traced_to)}</td></tr>"
        )
    sleeves = "".join(
        f"<li data-sleeve='{escape(a.sleeve_id)}'>{escape(a.sleeve_id)} — {_fmt(a.weight_pct)} % of deployable</li>"
        for a in o.sleeve_allocations
    ) or "<li>none — ETF-only at this capital</li>"
    structure = {
        "etf_only": "ETF-only: the deployable capital cannot hold enough names to honour the per-name cap at the minimum position size.",
        "etf_core_plus_sleeves": "An ETF core plus single-name sleeves that pick and size on the paper book.",
    }[o.structure]
    needs = "".join(
        f"<li>{escape(n.label)} — A${_fmt(n.amount_aud)} due {n.due.isoformat()}</li>" for n in goals.liquidity_needs
    ) or "<li>none stated</li>"
    return (
        "<section class='mandate'>"
        f"<h2>Mandate — derivation {escape(mandate.derivation_version)}, as of {mandate.as_of.isoformat()}</h2>"
        "<h3>What you stated</h3><ul>"
        f"<li>Investable assets A${_fmt(goals.investable_assets_aud)}; income A${_fmt(goals.income_aud_pa)} p.a.; "
        f"savings A${_fmt(goals.savings_aud_pa)} p.a.</li>"
        f"<li>Target wealth A${_fmt(goals.target_wealth_aud)} over {goals.horizon_years} years</li>"
        f"<li>Drawdown tolerance {_fmt(goals.drawdown_tolerance_pct)} %; emergency reserve {goals.emergency_months} months</li>"
        f"<li>Account {escape(goals.account_type)}; marginal rate {_fmt(goals.marginal_rate_pct)} %; "
        f"brokerage A${_fmt(goals.brokerage_aud_per_side)} per side</li>"
        f"<li>Liquidity calls within three years:<ul>{needs}</ul></li></ul>"
        f"<h3>Structure</h3><p data-field='structure'>{escape(structure)}</p>"
        f"<h3>Sleeve allocations (of deployable)</h3><ul>"
        f"<li data-sleeve='slv-etf-core-v1'>slv-etf-core-v1 — {_fmt(o.etf_core_pct.value)} % of deployable</li>{sleeves}</ul>"
        "<h3>Derived figures, each with its source</h3>"
        "<table><thead><tr><th>Figure</th><th>Value</th><th>Traced to</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"<p class='cadence'>Rebalance {escape(o.rebalance_cadence)} with a {o.hold_band_multiple}N hold-band.</p>"
        f"<p class='hash'>goals {goals.content_hash[:12]}… · mandate {mandate.content_hash[:12]}…</p>"
        "<p class='firewall'>Paper scope. Nothing here is an instruction to transact; every real order is yours.</p>"
        "</section>"
    )


__all__ = ["render_memo"]
