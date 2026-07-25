# Model A Archive Restore Evidence v1

`model-a-archive-restore-evidence-v1` is the immutable result of one attended,
read-only restore or reproduction drill against an exact
[`model-a-archive-manifest-v1`](model-a-archive-manifest-v1.md). It runs only in
an isolated non-production environment. It cannot write production data,
change production configuration, mutate the archive, approve decommission, or
revive Model A.

**Machine contract:** [`model-a-archive-restore-evidence-v1.schema.json`](../schemas/model-a-archive-restore-evidence-v1.schema.json)

**Synthetic golden fixture:**
[`model-a-archive-restore-evidence-valid.json`](../fixtures/model-a-archive-restore-evidence-valid.json)

The bundled fixture is `SYNTHETIC_GOLDEN`, points only to the synthetic archive
manifest, and explicitly denies production evidence and retirement approval.
A real attended drill uses `ATTENDED_REPRODUCTION`; the contract shape does not
turn the golden values into observed facts.

## Identity and reference

- `restore_evidence_id` is
  `{archive_id}:restore:{attempt_sequence}`. `attempt_sequence` is a canonical
  positive integer string allocated monotonically within one archive.
- `manifest_ref` contains the exact archive contract name, archive ID, schema
  version, creation time, and canonical root hash. The reference must resolve
  byte-for-byte to the retained manifest; a filename or mutable label is not
  sufficient.
- `started_at <= completed_at <= created_at`. The drill records its isolated
  environment ID, attended operator, tool bundle hash, and runtime-lock hash.

## Reproduction comparison

The drill rebuilds each manifest class with the manifest's export definition
and records:

- observed record, file, and raw-byte counts;
- observed minimum/maximum range;
- observed raw and canonical SHA-256 values;
- count, range, raw-hash, and canonical-hash match booleans; and
- one class result and explicit reason codes.

The comparison array contains exactly the manifest class set in the same
canonical order. A semantic validator resolves `manifest_ref`, joins rows by
`archive_class_id`, and recomputes every match boolean from the expected and
observed fields. Producer-supplied booleans and the producer verdict are never
trusted.

## Fail-closed verdict

`verdict=PASS` is valid only when:

- the manifest reference and root hash resolve;
- the class set is exact;
- every observed count and range equals the manifest;
- every raw and canonical digest matches;
- every class result is `MATCH`;
- the run is attended, isolated, non-production, and read-only;
- neither production nor archive bytes were written or mutated;
- no destructive action or secret material occurred; and
- `reason_codes` is empty.

Any mismatch, missing class, incomplete observation, unsafe environment, tool
failure, archive mutation, or indeterminate comparison returns `NOT_READY` or
`FAIL` with at least one reason code. Restore evidence alone never grants
runtime shutdown, retention, deployment, migration, or capital authority.

## Canonical root hash

`canonical_hash.payload_sha256` is SHA-256 over RFC 8785 canonical JSON for the
complete root object excluding only `/canonical_hash/payload_sha256`. A
correction or retry creates a new attempt and root hash; prior evidence remains
byte-identical.
