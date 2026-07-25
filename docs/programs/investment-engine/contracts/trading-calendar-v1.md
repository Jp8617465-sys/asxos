# Trading Calendar v1

`trading-calendar-v1` is the immutable, UTC-materialized XASX session and
settlement calendar used by origin scheduling, simulated fills, accounting,
NAV, and maturity.

**Machine contract:** [`trading-calendar-v1.schema.json`](../schemas/trading-calendar-v1.schema.json)

## Required semantics

Each session has a stable ID and local trading date, UTC open/close timestamps,
session status, and T+2 settlement date. The artifact pins the source timezone,
timezone-rules hash, exchange-schedule hash, holiday hash, coverage interval,
and settlement convention. Consumers never recalculate historical UTC times
from the machine's current timezone database.

Session IDs and dates are unique and strictly ordered. Open and early-close
sessions require valid UTC bounds and a later settlement date. Closed sessions
carry no tradable bounds. Missing dates, ambiguous timezone conversion, or an
unsupported settlement exception fails closed. Corrections create a new
calendar version and reset evaluator lineage continuity.

The calendar describes permitted simulation times only. It is `PAPER_ONLY`,
read-only, non-executable, and grants no market-access capability.
