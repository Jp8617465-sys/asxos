"""Universe ingestion logic — separated from the job script."""
from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from asxos.ingestion.eodhd import EODHDClient


def _to_symbol(code: str, *, exchange: str = "AU") -> str:
    """Append exchange suffix when the raw EODHD code has no dot.

    EODHD bulk endpoints return bare codes (e.g. "BHP", "AAPL") without
    an exchange suffix. For AU calls the default ".AU" is always correct;
    US calls must pass exchange="US" so "AAPL" → "AAPL.US" not "AAPL.AU".
    """
    return code if "." in code else f"{code}.{exchange}"


# EODHD Type -> universe.security_kind (multi-instrument Phase 2). Only these types are
# ingested; anything else (rights, warrants, unclassified) is skipped. REITs and many LICs
# are typed "Common Stock" by EODHD and so land as au_equity. ETF/FUND/hybrid kinds are kept
# OUT of the ML universe by the `security_kind = 'au_equity'` reader filters (migration 0037).
#
# EODHD's "FUND" type is UNLISTED managed funds, not ASX LICs: live, every one of the 11
# `security_kind='lic'` rows carries a `0P0000…` Morningstar identifier (Vanguard, PIMCO,
# Bentham, Janus wholesale funds). Every genuine ASX-listed investment company is typed
# "Common Stock", so `_TYPE_TO_KIND` alone can never classify one. `_CURATED_LIC_SYMBOLS`
# below is the correction.
_TYPE_TO_KIND: dict[str, str] = {
    "Common Stock": "au_equity",
    "ETF": "etf",
    "FUND": "lic",
    "Preferred Stock": "hybrid",
    "Notes": "hybrid",
    "BOND": "hybrid",
}


# ASX-listed investment companies and listed investment trusts (LICs/LITs), which EODHD types
# as "Common Stock". They are reclassified to `lic` so the residual-income sweep and the
# liquidity screen stop treating them as operating companies.
#
# WHY THIS EXISTS, AND WHY IT WAS DEFERRED BEFORE. The comment this replaces called au_equity
# "the safe default that keeps their existing Model A/thesis eligibility", and deferred a
# "curated LIC/REIT reclassification" as a later refinement. **That rationale is void**: PR #144
# deleted Model A and CLAUDE.md rule #11 quarantines its output from capital decisions, so there
# is no Model A eligibility left to preserve — only a cost. Measured 2026-09-18, six of the
# sixteen names the weekly scan surfaced to James (FGG, FGX, HM1, LSF, PGF, WQG) were LICs.
#
# A residual-income model on a LIC is CIRCULAR, not merely imprecise. The model values the
# residual over book of tangible common equity; a LIC's book value *is* a portfolio of
# securities already marked to market, so "value vs price" restates NTA vs price and dresses it
# as an earnings-based valuation. That misrepresents the method, which is why these are excluded
# at the population rather than flagged downstream.
#
# A-REITs are deliberately NOT here. `portfolio/build.py::forced_sell_inactive_symbols` records
# that A-REITs stay au_equity so a genuine delisting is still force-sold, and a REIT's book is
# marked property rather than marked securities, so the circularity argument does not carry.
# Property developers and operators (CWP Cedar Woods, AXI Axiom) are operating companies and
# stay au_equity too.
#
# CURATION BASIS AND LIMITS: assembled by inspecting `universe.name` across the live active
# universe on 2026-09-18. It is a starting set, NOT exhaustive and NOT self-maintaining — a
# newly listed LIC lands as au_equity until it is added here. Name-matching was rejected as the
# mechanism: WQG ("WCM Global Growth Ltd") contains no fund/trust/investment token and would be
# missed, while CWP ("Cedar Woods Properties Ltd") would be wrongly caught.
_CURATED_LIC_SYMBOLS: frozenset[str] = frozenset({
    "ACQ.AU",  # Acorn Capital Investment Fund
    "AFI.AU",  # Australian Foundation Investment Company
    "AIQ.AU",  # Alternative Investment Trust
    "ALI.AU",  # Argo Global Listed Infrastructure
    "ARC.AU",  # ARC Funds
    "ARG.AU",  # Argo Investments
    "AUI.AU",  # Australian United Investment Company
    "BKI.AU",  # BKI Investment Company
    "CD1.AU",  # CD Private Equity Fund I
    "CDO.AU",  # Cadence Opportunities Fund
    "DN1.AU",  # Dominion Income Trust 1
    "FGG.AU",  # Future Generation Global
    "FGX.AU",  # Future Generation Australia
    "FPC.AU",  # Fat Prophets Global Contrarian Fund
    "GCI.AU",  # Gryphon Capital Income Trust
    "GFL.AU",  # Global Masters Fund
    "GLS.AU",  # L1 Global Long Short Fund
    "GVF.AU",  # Staude Capital Global Value Fund
    "HM1.AU",  # Hearts and Minds Investments
    "KIT.AU",  # Kapstream Investment Trust
    "KKC.AU",  # KKR Credit Income Fund
    "LF1.AU",  # La Trobe Private Credit Fund
    "LGF.AU",  # L1 Gold Fund
    "LRT.AU",  # Lowell Resources Fund
    "LSF.AU",  # L1 Long Short Fund
    "MEC.AU",  # Morphic Ethical Equities Fund
    "MOT.AU",  # Metrics Income Opportunities Trust
    "MXT.AU",  # Metrics Master Income Trust
    "OPH.AU",  # Ophir High Conviction Fund
    "PCI.AU",  # Perpetual Credit Income Trust
    "PCX.AU",  # Pengana Global Private Credit Trust
    "PE1.AU",  # Pengana Private Equity Trust
    "PGF.AU",  # PM Capital Global Opportunities Fund
    "PIC.AU",  # Perpetual Equity Investment Company
    "QRI.AU",  # Qualitas Real Estate Income Fund (lends against property; holds loans, not property)
    "RF1.AU",  # Regal Investment Fund
    "WAA.AU",  # WAM Active
    "WAM.AU",  # WAM Capital
    "WAR.AU",  # WAM Strategic Value
    "WAX.AU",  # WAM Research
    "WGB.AU",  # WAM Global
    "WLE.AU",  # WAM Leaders
    "WMA.AU",  # WAM Alternative Assets
    "WMI.AU",  # WAM Microcap
    "WQG.AU",  # WCM Global Growth
})


def classify_kind(symbol: str, eodhd_type: str) -> str:
    """The security_kind for one incoming row: EODHD Type, then the curated LIC override.

    The override runs SECOND and wins, because the defect it corrects is EODHD typing a
    listed investment company as "Common Stock". It cannot invent a row: `refresh_universe`
    filters `incoming` on `Type in _TYPE_TO_KIND` before this is reached, so a symbol whose
    type is skipped (rights, warrants, unclassified) is never classified at all.
    """
    if symbol in _CURATED_LIC_SYMBOLS:
        return "lic"
    return _TYPE_TO_KIND.get(eodhd_type, "au_equity")


async def refresh_universe(client: EODHDClient, conn: asyncpg.Connection) -> dict[str, int]:
    """
    Sync universe from EODHD exchange symbol list.
    Returns counts: added, reactivated, delisted, unchanged, reclassified.

    ``reclassified`` counts curated LICs corrected from a stale ``security_kind`` in place
    (see ``_CURATED_LIC_SYMBOLS``). It is normally 0; a non-zero count on a run after the
    first means either a newly curated symbol or a row written before the curation existed.

    Ingests every `_TYPE_TO_KIND` instrument type (equities + ETFs/LICs/hybrids), tagging
    `security_kind` so funds are held/valued/taxed without entering Model A's universe. The
    delisting sweep is safe across kinds: it only flips an `is_active` symbol absent from the
    (now kind-broad) incoming set, and out-of-band rows (us_equity/index) are already
    is_active=FALSE, so `and is_active` skips them.
    """
    raw = await client.exchange_symbols("AU")
    incoming = {
        _to_symbol(r["Code"]): r
        for r in raw
        if r.get("Type") in _TYPE_TO_KIND
    }

    existing = {
        r["symbol"]: (r["is_active"], r["security_kind"])
        for r in await conn.fetch("SELECT symbol, is_active, security_kind FROM universe")
    }

    counts = {
        "added": 0,
        "reactivated": 0,
        "delisted": 0,
        "unchanged": 0,
        "reclassified": 0,
    }

    for sym, r in incoming.items():
        kind = classify_kind(sym, r.get("Type", ""))
        if sym not in existing:
            await conn.execute(
                # security_kind is NOT NULL with no default (migration 0037) — classify by the
                # EODHD Type via _TYPE_TO_KIND (funds stay out of Model A by kind, not is_active).
                """
                INSERT INTO universe (symbol, name, sector, currency, security_kind)
                VALUES ($1, $2, $3, 'AUD', $4)
                """,
                sym,
                r.get("Name") or "",
                r.get("Sector") or "",
                kind,
            )
            counts["added"] += 1
        else:
            was_active, stored_kind = existing[sym]
            # Reconcile a curated LIC whose stored kind predates the curation. security_kind is
            # otherwise written ONLY on INSERT, so without this a row misclassified at first
            # ingestion stays wrong permanently — which is how six LICs reached the weekly
            # candidate scan. Deliberately narrow: it corrects only TO 'lic' and only for a
            # curated symbol, so it can never rewrite a hand-set kind (us_equity/index) or
            # churn a row EODHD retypes.
            if sym in _CURATED_LIC_SYMBOLS and stored_kind != "lic":
                await conn.execute(
                    "UPDATE universe SET security_kind = 'lic', updated_at = NOW() "
                    "WHERE symbol = $1",
                    sym,
                )
                counts["reclassified"] += 1
            if not was_active:
                await conn.execute(
                    "UPDATE universe SET is_active = TRUE, updated_at = NOW() WHERE symbol = $1",
                    sym,
                )
                counts["reactivated"] += 1
            else:
                counts["unchanged"] += 1

    now = datetime.now(UTC)
    for sym, (is_active, _kind) in existing.items():
        if sym not in incoming and is_active:
            await conn.execute(
                "UPDATE universe SET is_active = FALSE, updated_at = $2 WHERE symbol = $1",
                sym,
                now,
            )
            counts["delisted"] += 1

    return counts
