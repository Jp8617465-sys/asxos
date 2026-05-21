"""asxos.domain.tax — pure-function tax module.

All math follows docs/foundation/spec/tax-alpha.md. Modules cite spec
section numbers; deviations require a spec amendment.
"""
from asxos.domain.tax.types import (  # noqa: F401
    AccountType,
    CapitalGain,
    Div296Outcome,
    Dividend,
    DividendOutcome,
    HoldingLot,
    IndividualConfig,
    LotSelection,
    NetCapitalGain,
    SMSFConfig,
    TaxView,
)
