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
  are frozen together. `session_return` is recomputed, never attested, as
  `index_level / prior_index_level - 1` to six decimals with `ROUND_HALF_EVEN`;
  a mismatched or unavailable prior level makes the snapshot `INCOMPLETE`.
- Cash data records the annualized rate, day-count convention, compounding
  rule, effective interval, and source observation.
- Every observation resolves the same immutable trading calendar used by the
  evaluator. Missing, stale, revised-after-cutoff, or non-finite data makes the
  snapshot `INCOMPLETE`; remembered values and zero fallback are prohibited.
- The canonical hash is computed over RFC 8785 JSON excluding only its own
  payload field. Any correction creates a new snapshot ID or version.

## Where those semantics are enforced

The `session_return` recomputation is enforced by the benchmark service built in
**S10** and by its acceptance evidence (AC-44, benchmark identity/label tests),
alongside AC-36 (provider/series/revision identity and the price-only negative),
which the acceptance matrix locks at **S08**. **Neither is checked by the dossier
harness.** The semantic validator validates this contract against its schema and
resolves its typed references, and `_validate_numeric_wire_shapes` format-checks
`session_return` as a six-place Decimal string because its name ends in
`_return` — but nothing recomputes it from `index_level / prior_index_level - 1`,
and no rounding mode is applied. A snapshot declaring an arbitrary but
well-formed `session_return` validates.
The chronology bullet above is likewise an S10 service obligation: the validator
applies the programme-wide `created_at`/`data_as_of` rule and, where the snapshot
is referenced from an evaluation origin's `BENCHMARK` manifest entry, asserts
`ref.created_at <= knowledge_cutoff` — but it never evaluates this snapshot's own
`observed_at <= published_at <= available_at <= knowledge_cutoff` chain.

This artifact is market evidence only. It is `PAPER_ONLY`, non-executable,
cannot mutate holdings, and cannot elevate an evidence tier.
