"""_infer_security_kind classification.

`universe.security_kind` is NOT NULL with no default (migration 0037) — every
demand-driven universe insert (`_ensure_in_universe`) must classify explicitly.
The classification is suffix-based and must NOT be an unconditional 'au_equity':
that path inserts is_active=TRUE, so a foreign symbol classified au_equity would
pass the ML universe filter and leak a US equity into Model A.
"""
from __future__ import annotations

from asxos.cli.holdings import _infer_security_kind


def test_foreign_symbol_is_us_equity() -> None:
    for s in ("AAPL.US", "HUBS.NYSE", "X.NASDAQ", "Y.AMEX"):
        assert _infer_security_kind(s) == "us_equity"


def test_au_and_bare_symbol_is_au_equity() -> None:
    for s in ("BHP.AU", "CBA.AU", "BHP"):
        assert _infer_security_kind(s) == "au_equity"
