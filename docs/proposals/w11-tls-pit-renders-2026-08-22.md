# W1-1 renders: TLS.AU PIT review (2026-08-22)

**Amendment E field.** Honest abstain against the current research-store
rows. Not Stage 4. Not an ASX announcement.

- Symbol: `TLS.AU` (ordinary ASX equity; HUBS/CBA not used)
- Period: yearly `2024-06-30`; cutoff `2025-08-21T23:59:59+00:00`
- Acquisition: `asxos_pit_db` · data_mode: `real` · outcome: `abstain`
- presentation_sha256: `1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0`
- document_sha256: `133f09bfb617999bdd56639e275698d369a6fa4973c96c94a13cd2b41fb0c780`
- Tables read: `rs_security_master`, `rs_financial_statements`, `rs_fundamentals_pit`, `prices`
- This VM had no `DATABASE_URL`, so `asx results-review show` was not fired here.
  The snapshot was SELECTed from those four tables only, then run through
  `adapt_pit_snapshot` + `present_adapted` — the same functions the CLI calls
  after `fetch_pit_snapshot`.

---

# Results review presented — rrv-pit-TLS.AU-2024-06-30

Analysis only. No rating, price target, trade, position size, portfolio instruction, or thesis mutation appears anywhere in this package.

## Provenance

- Case: pit-TLS.AU-2024-06-30 — PIT snapshot review TLS.AU 2024-06-30 (not Stage 4)
- Data mode: **real** (research-store PIT snapshot; not an ASX announcement)
- Acquisition path: asxos_pit_db
- Document: pit-TLS.AU-2024-06-30 (sha256 133f09bfb617999bdd56639e275698d369a6fa4973c96c94a13cd2b41fb0c780)
- Evidence packet: evp-pit-TLS.AU-2024-06-30
- Knowledge cutoff: 2025-08-21T23:59:59+00:00
- Evaluated at (injected, not read from a clock): 2025-08-21T23:59:59+00:00
- Presentation digest: 1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0
- Frozen artifact digest: d9f85feaaf56345d0703cd6cc1bb39d0e44fbfa5ac2290e838a199faa1efc25b
- Frozen case digest: 0000eaf42b584f48c88756866fd01cb8d5b9c498d08706c1c21627bc2e1dc579

## Verdict

- Verdict: **abstain**
- Derived verdict: abstain
- Challenge ceiling: abstain
- Scope: This verdict addresses the results-review artifact and its analysis only; a revise verdict calls for correction of the artifact, and of nothing else.
- Abstention is a valid, successful outcome, pre-registered by the packet's acceptance criteria; it is not a failure and it is not a could-not-build.

Insufficiencies recorded:

- missing evidence is recorded; the frozen gate forces abstention
- the artifact abstains on its own frozen outcome; an abstention is never upgraded

### Mechanical gates

| Gate | Result | Detail |
|---|---|---|
| integrity_seal | pass | every content seal verifies against canonical artifact content |
| citation_closure | pass | every material claim cites at least one item inside the frozen packet |
| bridge_reconciliation | pass | every bridge reconciles exactly, with no tolerance |
| delta_arithmetic | pass | every metric delta equals the frozen computation exactly |
| cutoff_admissibility | pass | no evidence, and no document, postdates the knowledge cutoff |
| tax_readiness_earned | pass | tax readiness is 'unknown'; a non-pass readiness keeps every downstream state gate closed at the canonical boundary (types.py:512-516), and unknown is a valid, successful outcome |
| outcome_gate_consistency | pass | the artifact outcome respects the frozen outcome gates |
| challenge_binding | pass | the supplied challenge binds to this artifact and its frozen packet |

## Independent challenge

- Challenge outcome: **abstain**
- Independent of author: True

Strongest bear case: The artifact records 1 falsifier statement(s); read against their cited evidence, they are the strongest standing challenge to the analysis. 3 named evidence input(s) are absent from the frozen packet.

| Severity | Finding | Required response |
|---|---|---|
| blocking | The frozen packet lacks 3 named evidence input(s); no completed analysis can rest on it. | Abstention stands until the named evidence enters a frozen packet and a new artifact is produced. |

## The artifact

# Results review rrv-pit-TLS.AU-2024-06-30

Analysis only: no recommendation, no rating, no price target, no trade
or position-size instruction (plan :303). Abstention is a valid,
successful outcome.

- Outcome: **abstain**
- Security: TLS.AU
- Period: 2024-06-30 (yearly)
- Currency / scale: AUD / ones
- Knowledge cutoff: 2025-08-21T23:59:59+00:00
- As of: 2025-08-21
- Document: pit-TLS.AU-2024-06-30 (sha256 133f09bfb617999bdd56639e275698d369a6fa4973c96c94a13cd2b41fb0c780)
- Evidence packet: evp-pit-TLS.AU-2024-06-30
- Tax readiness: unknown
- Model-independent: True
- Artifact content hash: b63b9777b260b93a924d8818c2731adf798a2b6ecfd09b0370f673682facb91f

## Metric deltas

| Metric | Basis | Currency | Scale | Current | Prior | Delta % |
|---|---|---|---|---|---|---|
| Revenue | statutory | AUD | billions | 22.928000000000000 | 22.702000000000000 | 0.995507 |
| NPAT | statutory | AUD | billions | 1.622000000000000 | 1.928000000000000 | -15.871369 |

## Falsifiers

- No ASX announcement was acquired; numeric claims rest only on research-store PIT/statement rows (rank 4). [pit-income-current]

## Missing evidence

- ASX results announcement (asx_announcement) — no acquisition path exists (G2: asx_announcements dropped in migration 0030)
- statutory/underlying bridge (G3) — rs_financial_statements carries a single normalised set, not a statutory/underlying pair
- guidance change (G5) — no guidance store exists in this repo

## Determinism

The presentation digest is byte-identical across independent processes on one interpreter version, given an explicitly injected evaluated_at, because every presented value is first reduced to a single canonical text form — normalised fixed-point Decimal text, explicit-UTC timestamps, sorted mapping keys, ASCII-escaped compact JSON — which makes it invariant to LC_ALL, to PYTHONHASHSEED, to input key order, and to value-equal but text-different Decimal spellings.

- NOT claimed: byte identity across Python versions. A different CPython release may change Decimal, json, or pydantic serialisation behaviour; the pinned digests are valid for one interpreter version at a time.
- NOT claimed: byte identity across platforms or architectures. Only same-interpreter, independent-process identity is instrumented.
- NOT claimed: text-form invariance of the FROZEN layer's own fingerprints. `AdaptedResultsReview.artifact_sha256` and `.case_sha256` hash pydantic's JSON render, which preserves a Decimal's written exponent, so a value-equal but text-different Decimal changes them. The presentation digest normalises first and does not change; both are reported side by side.
- NOT claimed: that the digest proves the frozen content seals. The presentation payload omits every `content_hash` field (it is text-form sensitive for the same reason); the seals are checked by the frozen `integrity_seal` gate, whose result travels inside the hashed payload.
- NOT claimed: anything about persistence. Nothing here is written to disk, and no digest is a storage key.
