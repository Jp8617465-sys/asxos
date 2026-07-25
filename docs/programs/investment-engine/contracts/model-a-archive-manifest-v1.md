# Model A Archive Manifest v1

`model-a-archive-manifest-v1` is the immutable, content-addressed inventory of
the historical Model A evidence retained before runtime retirement. It proves
what was exported and how its bytes can be reproduced. It does not approve a
shutdown, change production configuration, apply a migration, deploy code,
delete evidence, or restore Model A authority.

**Machine contract:** [`model-a-archive-manifest-v1.schema.json`](../schemas/model-a-archive-manifest-v1.schema.json)

**Synthetic golden fixture:**
[`model-a-archive-manifest-valid.json`](../fixtures/model-a-archive-manifest-valid.json)

The bundled fixture uses `evidence_scope=SYNTHETIC_GOLDEN` and a
`synthetic-test` environment. Its counts, hashes and timestamps are invented
contract vectors; they are not production evidence or retirement approval. A
real attended M-A1 record uses `ATTENDED_SOURCE_OBSERVATION`.

## Identity and sealing

- `archive_id` is
  `ma-archive-{environment_slug}-{snapshot_completed_at_compact}`. The
  environment slug is lower-case ASCII and the compact timestamp is UTC
  `YYYYMMDDtHHMMSSz`. The same environment and snapshot completion time must
  produce the same ID; an ID may never be reused for different bytes. The
  validator enforces that rule within `model-a-archive-manifest-v1`; ID
  uniqueness *across* contracts is not yet enforced (see
  [typed capital lineage](../architecture.md#typed-capital-lineage)).
- `source_snapshot_started_at <= source_snapshot_completed_at <= created_at`.
  M-A1 captures the source transaction/read snapshot without mutating it.
- `writer_state_at_snapshot` records the observed source-writer state as
  `ACTIVE`, `DISABLED`, or `UNKNOWN`. `writer_disabled_at` is optional and
  nullable; a non-null value is valid only when the writer was already
  `DISABLED` before the snapshot. M-A1 never disables it.
- `manifest_status=SEALED` requires every expected class, a passing secret scan,
  immutable `READ_ONLY_AUDIT` archive retention, and a valid canonical root
  hash. `SEALED` proves export integrity only; it is not evidence or approval
  of source-writer shutdown. An incomplete export is `NOT_READY`, carries
  reason codes, and cannot be used to approve runtime retirement.
- Corrections append a new archive and manifest. A sealed manifest and its
  payload files are never edited in place.

## Deterministic export bytes

Database-backed classes use one UTF-8 canonical NDJSON export. Each record is
RFC 8785 JSON on one line, columns are projected in the recorded `columns`
order before canonicalization, rows are sorted by every recorded `order_by`
term, JSON null is the only null representation, timestamps are UTC
`YYYY-MM-DDTHH:MM:SSZ`, Decimal values are strings with exactly six fractional
digits, lines are separated by LF, and the file has one final LF. No locale,
platform newline, database default order, exponent notation, negative zero, or
remembered value participates.

File-backed classes use `DETERMINISTIC_FILE_BUNDLE`. Members are ordered by
UTF-8 logical path. The raw bundle digest preimage is, for each member in that
order:

```text
utf8(path_byte_length) ":" utf8(logical_path) LF
utf8(content_byte_length) ":" raw_content_bytes LF
```

The canonical class digest is SHA-256 over the class's RFC 8785 NDJSON metadata
records with LF and a final LF. Raw file hashes remain in those metadata
records, so both exact bytes and canonical inventory are covered.

Every class records:

- a deterministic `archive_class_id = archive_id + ":" + lower(class_name)`;
- logical locator, representation, media type, explicit columns and sort keys;
- record, file, and raw-byte counts as non-negative integer strings;
- the range field plus minimum/maximum UTC value, or an explicit null range for
  classes without a time axis;
- the export-definition hash, exact raw-byte hash, and canonical semantic hash;
  and
- the raw and canonical digest methods.

The v1 class array is sorted by `dataset_or_artifact_class` and contains exactly
one row for each expected class. Cross-record count, range, ordering, class-set,
and digest equality are semantic checks; schema validity alone is not a pass.

## Retention and exclusion

The archive retention class is exactly `READ_ONLY_AUDIT`. Application writers
are denied access to the archive, the sealed archive is immutable, and deletion
requires a separate data-governance decision. This archive access control says
nothing about whether the source runtime writer remains active. The source
snapshot is read-only and transactionally pinned to `data_as_of`.

Credentials, tokens, private keys, environment secret values, and connection
material are excluded before export. A `SEALED` manifest requires a passing
secret scan with zero findings. Locators are logical archive-relative paths,
never signed URLs, connection strings, or secret-bearing locations.

The manifest controls fix `mission_mode=READ_ONLY_ARCHIVE`,
`source_mutation_performed=false`, `runtime_shutdown_claimed=false`, and
`runtime_change_authority=ABSENT`. Scheduler/writer shutdown and its elapsed
no-write observation belong only to a separately approved M-A3 record after
the M-A2 authority amendment.

## Canonical root hash

`canonical_hash.payload_sha256` is SHA-256 over RFC 8785 canonical JSON for the
complete root object excluding only `/canonical_hash/payload_sha256`. The
envelope itself remains in the preimage. The hash identifies the manifest in a
[`model-a-archive-restore-evidence-v1`](model-a-archive-restore-evidence-v1.md)
reference.
