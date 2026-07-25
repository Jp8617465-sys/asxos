# Security Classification Snapshot v1

`security-classification-snapshot-v1` is the immutable, point-in-time
classification and trading-rule projection used by S07 portfolio construction
and sizing.

**Machine contract:**
[`security-classification-snapshot-v1.schema.json`](../schemas/security-classification-snapshot-v1.schema.json)

**Complete golden fixture:**
[`security-classification-snapshot-valid.json`](../fixtures/security-classification-snapshot-valid.json)

## Purpose and authority boundary

The snapshot answers one narrow question: for each requested asset, which stable
security, issuer, corporate-group, sector, theme, venue, currency, instrument
kind, board-lot and price-step records were knowable and effective at the
decision cutoff?

It is a content-addressed materialized projection, not a new system of record.
The governed security master remains authoritative for security identity and
classification. Governed theme membership remains authoritative for theme
relationships. The published XASX trading-rule source remains authoritative for
board-lot and tick treatment. This contract stores stable identifiers, effective
intervals and cryptographic references to those authorities; it deliberately
does not copy issuer names, security names, sector labels, theme names,
descriptions or other mutable authority payloads.

The current repository does not yet contain authoritative issuer,
corporate-group or stable sector IDs, nor an effective-dated trading-rule store.
Production data assembled only from the current `universe`,
`rs_security_master` and mutable `theme_holdings` rows therefore MUST be
`INCOMPLETE`. An adapter may emit `COMPLETE` only after all missing authorities
and point-in-time timestamps exist. It MUST NOT slug a label, treat a database
update timestamp as an effective date, or invent a source availability time.

The supplied BHP document is a deterministic golden contract fixture. Its
identity records and hashes are synthetic test evidence, not an assertion about
the current production master.

## Fixed scope

Version 1 is:

- venue `XASX`;
- currency `AUD`;
- position direction `LONG_ONLY`;
- paper-only, immutable, read-only and non-executable; and
- independent of Model A, every predictive score and every generative model.

`us_equity` and `index` are not representable asset kinds in this XASX capital
scope. The allowed lower-case kind tokens preserve the existing governed
security-master vocabulary: `au_equity`, `etf`, `lic`, `reit`, and `hybrid`.
Kind classification does not by itself confer portfolio eligibility; ratified
construction and risk policies remain separate gates.

The artifact contains no account, credential, market session, route or order
instruction. `market_access` is fixed to `ABSENT`.

## Root identity and time

`classification_snapshot_id` identifies one immutable artifact and
`classification_snapshot_version` identifies its domain revision. Reusing an ID
with different bytes or hashes is forbidden. A correction, late source,
classification change, source-hash change or rule change mints a new ID/version
pair and invalidates dependent proposal and sizing lineage.

The three root clocks have distinct meanings:

- `data_as_of` is the market/classification instant the snapshot describes;
- `knowledge_cutoff` is the latest availability instant a source may have; and
- `created_at` is when the immutable projection was produced.

The required ordering is:

```text
data_as_of <= knowledge_cutoff <= created_at
```

For every provenance record:

```text
observed_at <= published_at <= available_at <= knowledge_cutoff
```

Every effective interval is half-open:

```text
effective_from <= data_as_of < effective_to
```

`effective_to: null` means unbounded, not unknown. An unknown interval is
represented by a `null` asset interval, an `INCOMPLETE` status and a typed
missing-data/reason code.

## Asset projection

Assets are ordered by ascending `asset_id` and unique by `asset_id`. The
venue-scoped `asset_id` is the programme wire identity (for example
`XASX:BHP`); `security_id` is the separate source-backed economic security
identity. A complete row contains:

- stable `asset_id`, `security_id`, `issuer_id`, `corporate_group_id` and
  `sector_id`;
- lexicographically sorted, unique `theme_ids`;
- the classification `effective_interval`;
- `venue: XASX`, `currency: AUD` and one supported `security_kind`;
- a positive integer-string `board_lot_quantity`;
- the one effective `tick_rule`;
- complete security-master, theme-membership and trading-rule provenance; and
- `classification_status: COMPLETE`,
  `admissible_for_construction: true`, and empty missing/reason arrays.

An empty `theme_ids` array means “the complete governed membership record proves
no active memberships.” It never means “membership data was unavailable.” A
missing or ambiguous membership source instead requires `INCOMPLETE`, a false
admission flag, `theme_ids` in `missing_fields`, and a reason code.

The snapshot references one aggregate membership record per asset so the hash
covers both present and absent memberships. Theme IDs are portable,
authority-issued identifiers; producers MUST NOT export environment-local
database row numbers unless the authority explicitly namespaces and guarantees
them.

## Trading-rule projection

`tick_rule` carries the effective rule ID/version and an ordered set of
half-open AUD price bands. The semantic validator MUST prove:

1. `band_sequence` is exactly `1..n` with no gaps;
2. the first lower bound is `0.000000`;
3. lower bounds strictly increase;
4. each non-final upper bound equals the next lower bound;
5. every bounded interval has `lower_bound_aud < upper_bound_aud`;
6. only the final band has `upper_bound_aud: null`;
7. every tick is strictly positive; and
8. the rule interval contains `data_as_of`.

For a candidate order price, consumers select exactly one containing band and
require the price to be an exact Decimal multiple of its tick. Binary floating
point and nearest-tick inference are forbidden. The golden fixture uses the
standard equity price-step bands published by
[ASX cash-market trading guidance](https://www.asx.com.au/markets/trade-our-cash-market/asx-equities-trading);
the fixture source digest remains synthetic.

Board lot and tick rules belong to this effective-dated asset projection.
Construction, risk, staging and sizing policies may prescribe conservative
rounding and limits, but MUST NOT carry a conflicting asset-specific lot or tick
value. During migration, equality with any legacy repeated value is required;
a mismatch fails closed.

## Provenance and source hashes

`source_hashes` contains at most one entry for each fixed source:

1. `governed-security-master`;
2. `governed-theme-membership`; and
3. `xasx-trading-rules`.

A `COMPLETE` root has all three, in lexicographic `source` order. Each asset
provenance reference supplies the upstream snapshot ID, record ID, event and
availability clocks, record digest and upstream snapshot digest. The semantic
validator MUST resolve each provenance `snapshot_sha256` to the root entry with
the same source, and MUST verify each record digest against the pinned upstream
bytes.

Source names, source snapshot IDs and record IDs are unique within their
applicable scope. A source observed after the cutoff is unavailable even if it
corrects an earlier event. No consumer may select a later “latest” row during
replay.

## Completeness and fail-closed admission

The root is `COMPLETE` if and only if all requested assets are complete and
admissible, all three source classes resolve exactly once, and both root
missing/reason arrays are empty.

An asset is `INCOMPLETE` when any required identity, classification, effective
interval, board lot, tick rule, source record or source hash is missing,
conflicting, ambiguous, stale for the requested instant, or unavailable at the
cutoff. The row then MUST have:

```text
classification_status = INCOMPLETE
admissible_for_construction = false
missing_fields = one or more precise paths
reason_codes = one or more stable codes
```

The root becomes `INCOMPLETE`, names at least one missing-data class and carries
at least one reason code. It never substitutes a default sector, empty theme set,
kind, board lot, price step, group identity or open-ended interval.

Consumer behavior is context-sensitive but always fail closed:

- an incomplete prospective candidate is excluded from admission;
- an incomplete currently held asset rejects the whole portfolio proposal,
  because issuer/group/sector/theme and loss constraints cannot be recomputed;
- an incomplete asset in a proposed or sizing line rejects that proposal or
  sizing decision;
- no `portfolio-proposal-v1` target, `sizing-decision-v1` line or paper intent
  may reference an asset absent from the exact snapshot; and
- downstream artifacts retain this snapshot ID and canonical digest, not an
  unversioned “current master” lookup.

`incomplete_asset_action` is fixed to `INADMISSIBLE_NO_INFERENCE`.

## Determinism and canonical hash

All timestamps are explicit UTC `Z` timestamps. Quantities are canonical integer
strings; AUD values are exact six-decimal strings. Producers sort:

1. `source_hashes` by `source`;
2. `assets` by `asset_id`;
3. each `theme_ids` array lexicographically;
4. `missing_data_classes`, `missing_fields` and `reason_codes`
   lexicographically; and
5. tick bands by numeric `band_sequence`.

Schema `uniqueItems` is not sufficient for key-level uniqueness or ordering.
The semantic validator enforces the sort order and rejects duplicate asset IDs,
source names, theme IDs, band sequences, or conflicting stable identities.

`canonical_hash.payload_sha256` is SHA-256 over RFC 8785 canonical JSON after
excluding exactly `/canonical_hash/payload_sha256`. The canonical envelope
itself remains in the preimage. Hash mismatch, non-canonical numeric text or a
non-deterministic input permutation rejects the artifact.

## Required semantic validation

Schema validation is necessary but not sufficient. The dossier validator and
runtime producer MUST additionally test:

- root/provenance chronology and half-open effective containment;
- root status equivalence to every asset status;
- unique, sorted assets, sources, themes, missing fields, reasons and bands;
- exact source-name-to-provenance-key mapping and snapshot-hash resolution;
- no stable security ID mapped to conflicting issuer/group identities at one
  instant;
- complete theme absence versus unavailable membership;
- positive board lots and whole-lot sizing compatibility;
- ordered, contiguous, non-overlapping tick bands and exact tick divisibility;
- canonical root-hash replay and input-permutation byte identity;
- current-holding and proposed-asset coverage;
- missing, ambiguous, future-effective, expired and late-arriving source cases;
  and
- static/perturbation proof that predictive-model output and executable
  market-access dependencies cannot affect the bytes.

## Versioning

Additive optional fields require a new schema version. Any change to identifier
meaning, completeness rules, effective-interval semantics, supported
security-kind vocabulary, tick-band interpretation, source authority, ordering,
hash preimage or fail-closed action requires a new contract major version and a
new evaluator lineage.
