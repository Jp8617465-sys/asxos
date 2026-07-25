# Benchmark Snapshot v1

`benchmark-snapshot-v1` is the immutable point-in-time market-data observation
used to open an evaluation origin. It carries genuine XJO total-return index
data and the observable cash-rate input without embedding a performance claim.

**Machine contract:** [`benchmark-snapshot-v1.schema.json`](../schemas/benchmark-snapshot-v1.schema.json)

## Required semantics

- `observed_at`, `published_at`, and `available_at` are distinct UTC timestamps.
  A consumer proves `observed_at <= published_at <= available_at <=
  knowledge_cutoff`; unavailable or later-published data cannot enter an origin.
- XJO data is explicitly `GROSS_TOTAL_RETURN_INDEX`,
  `GENUINE_POINT_IN_TIME`, and dividend-reinvesting. A price index cannot
  substitute.
- The current and prior complete-session levels, dates, and source references
  are frozen together. The semantic validator recomputes
  `session_return = index_level / prior_index_level - 1` to six decimals with
  `ROUND_HALF_EVEN`; a mismatched or unavailable prior level makes the snapshot
  `INCOMPLETE`.
- Cash data records the annualized rate, day-count convention, compounding
  rule, effective interval, and source observation.
- Every observation resolves the same immutable trading calendar used by the
  evaluator. Missing, stale, revised-after-cutoff, or non-finite data makes the
  snapshot `INCOMPLETE`; remembered values and zero fallback are prohibited.
- The canonical hash is computed over RFC 8785 JSON excluding only its own
  payload field. Any correction creates a new snapshot ID or version.

This artifact is market evidence only. It is `PAPER_ONLY`, non-executable,
cannot mutate holdings, and cannot elevate an evidence tier.
