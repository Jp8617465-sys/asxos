# Supabase evidence-store alignment plan — P3-02/P3-03 planning supplement

**Status:** PLANNING ONLY · QUEUED · NOT EXECUTABLE

**Prepared:** 2026-08-13 (Australia/Brisbane)

**Authority:** James directly invoked `/arbi-mission red team and create a plan against north star`

**Canonical identity:** planning supplement to existing `P3-02` and `P3-03`; **not a new work-order ID**

**Primary outcome:** lossless evidence preservation, historical replay, and isolated restore

**Secondary constraint:** reduce avoidable Supabase growth and return the operational database to a sustainable footprint
**Production effect of this document:** none

This plan does not activate Stage 1, change the canonical queue, authorise a database or external
write, or displace the current sequence. It may be considered for execution only after the existing
dependencies and James-only approvals in §9 close.

## 1. Executive ruling requested

The present database is operational, but its storage boundary does not match the ratified target
architecture. Supabase is currently acting both as the operational system of record and as the raw
analytical history store. The largest example, `rs_financial_statements`, is active and useful, but
it occupies about 1,230 MiB and is unconditionally rewritten on conflict each week.

The recommended direction is:

1. keep Supabase as the operational relational source of truth;
2. preserve the exact historical evidence currently held before changing or retiring anything;
3. land future original provider payloads immutably in the already-ruled S3 evidence plane;
4. store analytical history as versioned, checksummed Parquet and query it with DuckDB;
5. retain only justified operational/PIT projections and their provenance in Supabase; and
6. consider deletion or physical compaction only after checksum, replay, isolated restore,
   side-by-side observation, and a separate James approval.

The North Star outcome is not “a smaller database.” It is a system whose capital-relevant facts
are cited, reproducible, and recoverable. This supports better investment decisions and outcomes
without turning infrastructure work into a substitute for the model-independent product
([North Star](../product/north-star.md#the-reframe-ratified-2026-08-10)).

## 2. Authority, queue, and truth snapshot

### 2.1 Queue position

The canonical sequence remains controlled by
[`roadmap-state.md`](../product/roadmap-state.md#queued-after-the-current-remediation-work-james-2026-08-12).
This plan is nested beneath:

- `P3-02` — write the S3 credential/Object Lock/restore work order; and
- `P3-03` — complete Stage 1 evidence admission and replay.

It does not create a competing queue or activate either item. The governed campaign order is
`P1-01 → P1-02 → P1-03 → P1-04 → P1-05 → SB0-01`; current completion and any remaining
reconciliation must be taken from a fresh queue probe rather than inferred from that historical
sequence. Downstream dependencies include `SB1-02`, `P3-01`, James's approval of `P3-02`, and then
`P3-03` as recorded in the
[execution packet](asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md#7-candidate-execution-backlog).

### 2.2 Git truth at drafting time

- `origin/main` was first observed at `6fa2b21` while this plan was being drafted, then advanced to
  `5c67fe0` before review.
- P1-02 PR #100 is merged at `6fa2b21`, P1-03 PR #101 is merged at `3dbcaee`, and SB0-01 PR #102 is
  merged at `5c67fe0`.
- `be45060` is the P1-02 source-branch commit; it is not the main commit identity.
- P1-03 commit `b180ce9` and SB0-01 commit `58232d3` are source-branch identities, not main commit
  identities. They were branch-only during the first planning snapshot and were superseded as
  current truth by the observed squash merges above.

These identities are observations at drafting time, not permanent truth. Every future mission must
refresh repository and PR state before acting.

### 2.3 North-Star architecture contract

The target architecture requires two complementary evidence stores:

- immutable object storage for original payloads/files, extraction artifacts, canonical Parquet,
  research artifacts, and exact renders; and
- Supabase Postgres for identities, current projections, pipeline/quality state, governance,
  theses, decisions, dispositions, outcomes, and learning metadata.

Postgres must not remain the sole raw archive or sole analytical warehouse
([target architecture §6.1](../product/target-architecture.md#61-dual-storage-model)). The ruled
future object store is AWS S3 in `ap-southeast-2`, with versioning, Object Lock governance mode,
encryption, least-privilege credentials, lifecycle policy, and a separately observed restore test.
No bucket or credential creation is authorised here
([target architecture F6](../product/target-architecture.md#f6--object-store-ruled)).

## 3. Dated live evidence baseline

The following facts were observed through read-only SQL against production Supabase on
2026-08-13 at approximately 15:50–16:00 AEST. The session set
`default_transaction_read_only = on`. No database or external state was changed.

| Surface | Observed size/state | Interpretation |
|---|---:|---|
| Whole Postgres database | 1,640,967,315 bytes · 1,565 MiB | Above the Free database-size allowance; exact billing state remains a dashboard/account fact |
| Supabase object storage | 0 buckets · 0 objects · 0 bytes | The target immutable evidence plane does not exist yet |
| `rs_financial_statements` | 1,289,986,048 bytes · 1,230 MiB | About 79% of the database; active raw/canonical analytical history |
| `signals` | 166,633,472 bytes · 159 MiB | Model A historical/runtime surface; retirement classification depends on completion of P1 |
| `prices` | 106,004,480 bytes · 101 MiB | Active operational/current projection and historical price input |
| `fundamentals` | 18,890,752 bytes · 18 MiB | Active operational screening input |
| `signal_outcomes` | 13,590,528 bytes · 13 MiB | Historical Model A evaluation evidence; preservation required |
| `rs_fundamentals_pit` | 10,346,496 bytes · 9.9 MiB | Active point-in-time serving/research projection |
| `archive_dropped_20260628` | 6,766,592 bytes · 6.5 MiB | Recoverable legacy archive; not the cause of the overage |
| `signals_shap_gin_idx` | 98,492,416 bytes · 94 MiB | Zero observed scans; candidate retirement only after dependency proof |

Additional observations:

- `rs_financial_statements` held approximately 694,015 rows for about 3,359 symbols.
- A 1% sample measured average `line_items` JSON at approximately 1.16 KiB, with no empty JSON
  rows in the sample.
- Postgres statistics reported approximately 1.86 million updates and 88,900 dead tuples on that
  table. Statistics counters have a reset horizon and are operational evidence, not a lifetime
  accounting ledger.
- The table's weekly sync succeeded on 2026-08-08 and reported 436,678 rows written. The downstream
  PIT derivation succeeded on 2026-08-12 with 53,624 rows, proving that the table has an active
  consumer.
- The active PIT derivation currently selects only `period_type = 'yearly'`
  ([fundamentals PIT loader](../../asxos/ingestion/fundamentals_pit.py#L156)). Quarterly rows have
  no proven consumer in that path, but that does not make them disposable.
- Thirty-six PIT rows had a future `knowledge_date` between 2026-08-14 and 2026-09-13. They must be
  excluded by `knowledge_date <= cutoff` in replay. Their existence is a test condition, not by
  itself proof of corrupt data.

The current ingestion uses `ON CONFLICT ... DO UPDATE` without an unchanged-row predicate and
rewrites the complete JSON document
([financial-statement UPSERT](../../asxos/ingestion/financial_statements.py#L190)). The scheduled
weekly chain invokes the sync before PIT derivation
([weekly research workflow](../../.github/workflows/weekly-research.yml#L53)).

## 4. Provenance boundary

Two evidence classes must not be conflated:

1. **Legacy canonical snapshot.** A lossless export of `rs_financial_statements` can preserve the
   exact typed rows and JSON presently held in Postgres. It must be labelled as an
   `asxos_canonical_snapshot`, with database cutoff, schema version, code SHA, and checksums.
2. **Original provider source object.** The current code parses EODHD responses and stores selected
   statement payloads. The database row cannot be relabelled as the original byte-for-byte provider
   response. Future ingestion must capture original response bytes and provider/request metadata
   before parsing, subject to provider retention rights. Request metadata must be generated from an
   allowlist and normalized into a token-free identity. EODHD currently carries `api_token` as a
   query parameter, so raw URLs, query strings, authorization headers, cookies and secret-bearing
   headers are forbidden evidence fields. A pre-write secret scan must hard-fail before an immutable
   or Object-Locked object is created, with tests that inject representative forbidden fields.

This distinction prevents the second brain from manufacturing provenance it does not possess. A
legacy replay can prove equivalence to the evidence ASXOS actually held; only future raw capture can
prove equivalence to the original source bytes.

## 5. KEEP / MOVE / RETIRE classification

`RETIRE` below means a future eligibility decision after preservation and consumer proof. It is not
deletion authority.

| Surface | Class | Current role/consumer | Required destination or condition |
|---|---|---|---|
| `universe`, `rs_security_master` | KEEP | Instrument identity, tradeability, screening and joins | Supabase current identity projection; later add stable `security_id` without losing source symbol history |
| `prices` + `price_revisions` | KEEP + MIRROR | Serving prices, portfolio/thesis monitoring, PIT research; revision evidence | Keep operational projection and revision ledger; add immutable raw/canonical partitions in evidence plane |
| `fundamentals` | KEEP + MIRROR | Current model-independent screening | Keep bounded serving projection; future source objects/canonical history live outside operational Postgres |
| `rs_fundamentals_pit` | KEEP | Point-in-time facts and research input | Keep justified serving projection and source-object lineage; enforce cutoff semantics |
| `rs_factor_scores` | KEEP/PARK | Research output; workflow says current quant lane is retired | Preserve small table and registry lineage until Stage 2 classifies the method; do not use as a capital input |
| `rs_financial_statements` | MOVE, THEN SLIM | Source for yearly PIT derivation; current raw/canonical analytical history | Export every row losslessly to checksummed Parquet; future original payloads to S3; retain only the proven operational projection/cache after replay |
| Quarterly financial statements | MOVE/PRESERVE | No current PIT consumer proven | Preserve in immutable analytical history; future research registry decides use, not a storage cleanup |
| `rs_corporate_actions` | KEEP + MIRROR | PIT dividends/franking and security history | Keep operational/PIT facts; mirror immutable source/canonical partitions |
| `rs_estimates` | KEEP/BUILD + MIRROR | Target/estimate evidence; current source is snapshot-oriented and may be empty/sparse | Preserve any existing rows; future point-in-time estimate assets require immutable source identity and explicit `known_at` |
| `rs_index_membership` | KEEP/BUILD + MIRROR | Index eligibility/history; source gap remains material | Preserve any existing rows; do not claim historical membership until a qualified source and temporal contract exist |
| Announcements and source documents | BUILD/MOVE AT INGEST | Required evidence for thesis/results review; no complete immutable document source exists today | Original bytes and extraction artifacts in S3; cited metadata/current projections in Supabase; unavailable until provenance and rights pass |
| `signals` | RETIRE CANDIDATE | Model A history; active runtime consumers are being removed in P1 | Preserve a versioned historical dataset and consumer manifest; retire only after P1-05 and replay/allowlist proof |
| `signal_outcomes` | MOVE + RETAIN MINIMUM | Evidence that established Model A's failure | Preserve complete immutable historical artifact plus minimal governed evaluation receipt/metadata in Postgres |
| `signals_shap_gin_idx` | RETIRE CANDIDATE | JSON containment/search index; zero scans observed | Fresh query/consumer proof, reviewed migration, separate James approval; table export is not required merely to remove an index |
| `model_versions` | KEEP HISTORICAL | Registry and quarantine/approval evidence | Retain governed history; no Model A revival or capital use |
| Theses, themes, holdings, decisions, profiles | KEEP | North-Star operational investment objects | Supabase; included in irreplaceable backup/restore proof |
| Agent, evidence and governance ledgers | KEEP | Second-brain audit, promotion and provenance | Supabase; append-only/governed semantics and independent backup |
| Job/brief/run state | KEEP WITH RETENTION | Reliability and delivery evidence | Supabase bounded operational history; formal retention policy before pruning |
| `archive_dropped_20260628` | RETIRE CANDIDATE | Legacy recovery copy | Confirm external/full recovery evidence and zero consumers; separate destructive approval |
| Future EODHD payloads and documents | MOVE AT INGEST | Missing immutable source layer | Original bytes in S3 with content hash, request identity, observed/known timestamps and parsing lineage |
| Canonical analytical partitions and research artifacts | MOVE | Replay, backfill and method evaluation | Versioned Parquet in S3, queried through DuckDB; Postgres stores manifests and governed outcomes |

## 6. Execution graph and sequencing

The graph labels below are local plan nodes, not canonical work-order IDs.

```text
Existing queue closes required predecessors
  P1-04 → P1-05 and any post-SB0 reconciliation
       │
       ├── SB1-02 read-only probe adapters
       └── P3-01 scheduler work order
                    │
          James approves P3-02
                    │
     A. Freeze contracts and arrest growth
                    │
     B. Establish immutable evidence plane
                    │
     C. Export legacy canonical evidence
                    │
     D. Replay + isolated restore + side-by-side
                    │
         James reviews P3-03 exit proof
                    │
     E. Cut over consumers/scheduler (separate approval)
                    │
     F. Retire/compact (separate destructive approval)
```

### NOW — this planning artifact only

| Node | Owner | Output | Acceptance evidence |
|---|---|---|---|
| N0 | backend-architect | Dated table/index/job baseline and source-precedence map | Observed facts distinguished from inference and estimates |
| N1 | system-architect | KEEP/MOVE/RETIRE consumer matrix | Every material surface has consumer, successor, preservation condition |
| N2 | performance-engineer | Growth and storage-outcome model | Formulas, uncertainty and logical-vs-physical size distinction |
| N3 | security-engineer | S3/IAM/Object Lock/restore threat model and James stops | No credentials created; all external/destructive operations gated |
| N4 | backend-architect | Lossless export/replay/restore contract | Exact typed reconciliation and failure cases specified |
| N5 | requirements-analyst | Nested P3-02/P3-03 work order | No new queue identity or activation |

### NEXT — only after existing dependencies and individual approvals

| Step | Owner | Prerequisites | Reversible output / stop |
|---|---|---|---|
| A1 Add unchanged-row write guard | backend-architect + performance-engineer | Fresh consumer tests; refresh the merged P1-03 scheduler truth; reviewed code PR | Prevent identical historical rows being rewritten; deploy is `JAMES_NEEDED` |
| A2 Prove SHAP GIN index redundancy | backend-architect | P1 consumer manifest complete; fresh query/index evidence | Migration proposal only; apply/drop is `JAMES_NEEDED` |
| B1 Freeze `SourceObject` and partition manifests | system-architect + backend-architect | SB1-02; P3-02 approved | Versioned schemas and fixtures; migration apply is `JAMES_NEEDED` |
| B2 Verify provider retention rights | tech-stack-researcher + James | EODHD terms/account rights checked | Written permitted-use result or blocked verdict |
| B3 Create immutable store | security-engineer + James | P3-02 approved; B1/B2 pass | Hardened bucket/IAM/KMS/Object Lock/audit/lifecycle controls in §7.7; creation is `JAMES_NEEDED` |
| B4 Add raw-first ingestion | backend-architect | B1-B3; failure semantics and idempotency tests | Draft code and fixtures; external write/deploy is `JAMES_NEEDED` |
| C1 Export legacy canonical snapshot | backend-architect | Manifest format frozen; production export approved | Checksummed Parquet + manifest; production read/export and S3 write are `JAMES_NEEDED` |
| C2 Reconcile export | data/research reviewer | C1 complete | Counts/checksums/types reconcile by table, partition, symbol and statement kind |
| D1 Historical cutoff replay | research/data owner | C2 pass | One decision-date/PIT derivation uses only `known_at <= cutoff` and matches baseline |
| D2 Isolated restore | operations/security owner + James | D1 pass; independent recovery copy and key-recovery path available | Empty destination restores schema, constraints, irreplaceable operational state and evidence without source DB/live-bucket fallback; provisioning/write/execution is `JAMES_NEEDED` |
| D3 Side-by-side observation | performance + operations | D1/D2 pass | Freshness, row identity and consumer outputs match for an agreed observation window |

### LATER — separately authorised cutover and retirement

| Step | Owner | Preconditions | Mandatory stop |
|---|---|---|---|
| E1 Consumer cutover | backend/system architect | D1-D3 pass; rollback rehearsed | Production deploy/write: `JAMES_NEEDED` |
| E2 Scheduler ownership cutover | system architect + James | P3-01 approved; no dual ownership | Scheduler mutation: `JAMES_NEEDED` |
| F1 Retire redundant Model A surfaces | backend-architect | P1 complete; historical evidence replayable | Migration/deletion: `JAMES_NEEDED` |
| F2 Retire legacy raw Postgres rows/table | backend-architect | C/D/E gates pass; external restore observed | Destructive migration: `JAMES_NEEDED` |
| F3 Reclaim physical space | database owner + James | Deletion proven safe; maintenance/rollback window | Table rewrite/swap or `VACUUM FULL`: `JAMES_NEEDED` |
| F4 Measure outcome | arbi read-only | Fresh post-operation catalog + billing-cycle observation | Record actual replay, reliability and size; no victory from estimated size alone |

## 7. Lossless export, replay, and restore contract

No destructive proposal advances unless all gates below pass in order.

### 7.1 Export identity

Each export manifest must contain:

- source project identity without credentials;
- transaction/snapshot cutoff and extraction time;
- repository SHA, schema migration count/version, exporter version and manifest schema version;
- ordered primary-key definition;
- partition key and object key;
- row count, null counts and min/max bounds;
- per-object byte size and SHA-256 checksum;
- aggregate manifest checksum;
- exact Parquet logical types and JSON serialisation rules; and
- evidence class: `legacy_canonical_snapshot` or `provider_raw_object`.

NUMERIC values must round-trip exactly, dates/timestamps must retain timezone semantics, and JSON
must be compared canonically as data while retaining the exported source bytes separately.

### 7.2 Reconciliation denominator

Reconcile at least:

- total rows and distinct primary keys;
- symbol, period type, statement type and date partitions;
- null counts for every column;
- numeric min/max and deterministic aggregate hashes;
- JSON canonical hashes and raw exported bytes;
- duplicate/missing primary keys; and
- expected future-dated `knowledge_date` rows, which must remain unavailable before their cutoff.

### 7.3 Canonical temporal admissibility

The canonical temporal contract has distinct meanings:

- `effective_at` — when the economic fact applies;
- `known_at` — earliest evidenced market availability; and
- `ingested_at` — when ASXOS received or materialised it.

Legacy `period_end`, `filing_date`, `report_date`, `knowledge_date`, retrieval time and ingestion
time are not interchangeable. For the legacy PIT store, `knowledge_date` may map to canonical
`known_at` only when the guarded derivation and retained source fields prove that interpretation
under a versioned mapping rule. The mapping receipt must record its rule/version and the contributing
timestamps. If earliest market availability cannot be established, canonical `known_at` is
`unavailable`; the evidence packet must abstain or mark the fact unavailable. It must never substitute
period end, retrieval time or `ingested_at` merely to make replay pass.

### 7.4 Historical replay

Select one declared historical cutoff and rebuild the PIT output using only evidence satisfying
the canonical temporal rule `known_at <= cutoff`. A legacy `knowledge_date <= cutoff` filter is
admissible only through the versioned mapping in §7.3. Compare:

- eligible source identities;
- derived PIT row count and primary keys;
- every promoted numeric value;
- required downstream feature/research identities; and
- explicit unavailable/abstain states.

Then reconstruct one frozen `EvidencePacket` for the declared historical decision date through the
mandatory chain:

```text
SourceObject/legacy-source receipt
    → temporally admissible canonical facts
    → PIT/current projections used at the cutoff
    → frozen EvidencePacket with citations and unavailable states
```

The packet identity, every cited source-object/manifest identity, values, cutoff, schema/code
versions and deterministic render/hash must match the declared baseline. This is the replay
denominator required for P3-03; a matching PIT table alone is insufficient.

A hash mismatch, row mismatch, future leakage, unavailable object or unclassified difference is a
hard failure—not a warning.

### 7.5 Isolated restore

Restore into an empty destination with credentials that cannot read production Supabase and cannot
fall back to the original live bucket. The restore source must be an independently accessible
recovery copy or recovery account, not merely another key to the live evidence bucket. Its
encryption-key recovery path must also work without the live writer role or a single operator's
credential.

The restore proof has two declared scopes:

- **analytical evidence:** source objects, canonical manifests/Parquet, schemas and replay code; and
- **second-brain operational state:** schema, constraints and every irreplaceable KEEP table,
  including holdings/decisions/profiles, themes/theses/revisions, agent/evidence/governance ledgers,
  model registry history and the price-revision ledger.

Prove recovery from the independent copy, database backup and documented dependencies alone.
Reconcile constraints and row counts in addition to data. Inject failures for a missing object,
corrupt checksum, duplicate partition, stale manifest, wrong schema/code version, unavailable
source and unavailable encryption key. Provisioning the isolated target, writing to it and executing
the restore are external mutations and require a separate `JAMES_NEEDED` approval.

The final restore gate must restore both stores and relink them:

1. restore immutable objects/manifests into the isolated evidence substrate;
2. restore the operational Postgres schema, constraints and irreplaceable tables at the exact
   cutover schema/version;
3. verify every Postgres source-object/manifest foreign identity resolves to the restored object and
   checksum;
4. replay the frozen historical `EvidencePacket` using only the restored stores; and
5. prove no read touches production Supabase, the live evidence bucket or an undeclared fallback.

The existing Postgres restore-drill machinery may be reused, but it must be rerun at the cutover
schema/version and extended to prove the cross-store relink. A historical green database-only drill
does not satisfy this combined gate.

### 7.6 Rollback and side-by-side

Before cutover, document:

- old and new reader endpoints/interfaces;
- rollback trigger and responsible human;
- maximum tolerable observation gap;
- how dual writers are prevented or reconciled;
- how scheduler ownership is proven singular; and
- how current projection freshness is monitored through the observation window.

### 7.7 Object-store security acceptance

Before the first external evidence write, prove all of the following without recording secret
values in repository artifacts:

- account-level and bucket-level S3 Block Public Access enabled;
- bucket-owner-enforced object ownership and ACLs disabled;
- TLS-only bucket policy;
- explicit SSE-KMS encryption, bounded key policy, rotation and independently tested key-recovery
  path;
- short-lived, separate ingestion-writer, replay-reader and restore-operator roles;
- writer restricted to declared append-only prefixes and unable to weaken bucket retention;
- CloudTrail data events or equivalent object-level audit evidence enabled;
- explicit deny or separately approved dual-control path for
  `s3:BypassGovernanceRetention`, object-version deletion and lifecycle-policy weakening;
- retention periods and lifecycle rules compatible with decision/evidence references and provider
  rights; and
- allowlisted token-free request identity, forbidden-metadata rejection and pre-write secret scan
  tests passing before every immutable write.

## 8. Projected storage outcomes

These are catalog arithmetic scenarios, not promises. Physical database size and billed/averaged
usage may not fall until Postgres rewrites or releases space, and replacement projections consume
some of the reclaimed capacity.

| Scenario | Arithmetic from 2026-08-13 baseline | Logical/catalog result before replacement data |
|---|---:|---:|
| Remove unused SHAP GIN index | 1,640,967,315 − 98,492,416 | about 1,471 MiB |
| Move `rs_financial_statements` | 1,640,967,315 − 1,289,986,048 | about 335 MiB |
| Move raw table + remove GIN index | 1,640,967,315 − 1,289,986,048 − 98,492,416 | about 241 MiB |

The “about 335 MiB” scenario is the useful target envelope for a slim operational projection, not
an instruction to drop the table. It creates roughly 165 MiB of headroom below a 500 MiB threshold
before replacement projection growth, but only after safe physical reclamation. The work should be
sized around replay correctness and sustainable growth, not around landing exactly below a billing
line.

## 9. Risk register

Priority uses `(Impact + Risk) × (6 − Effort)`, each scored 1–5. Higher is addressed first.

| Risk | Likelihood / impact | Score | Mitigation and owner | Status |
|---|---|---:|---|---|
| Evidence is deleted before export/restore is proven | Medium / High | 45 | Hard gate: checksums, replay, isolated restore, side-by-side, rollback, then separate James approval. Owner: backend + James | Open |
| Parsed database rows are falsely labelled original provider payloads | High / High | 40 | Separate `legacy_canonical_snapshot` from `provider_raw_object`; preserve source limitations. Owner: system architect | Open |
| Weekly unconditional UPSERT continues write amplification | High / Medium | 40 | Add tested `IS DISTINCT FROM`-style guard as first future code control. Owner: backend/performance | Open |
| Object-store or IAM/KMS misconfiguration exposes or loses evidence | Medium / High | 36 | §7.7 controls: public-access block, TLS-only, bucket-owner-enforced, SSE-KMS recovery, separated short-lived roles, data-event audit and controlled retention bypass. Owner: security + James | Open |
| Secret-bearing URL/header is captured into immutable storage | Medium / High | 36 | Token-free allowlisted request identity, forbidden metadata fields, pre-write scan and hard-fail fixtures before Object Lock. Owner: security/backend | Open |
| Quarterly evidence is discarded because current PIT reads yearly only | Medium / High | 36 | Preserve all quarterly partitions; future research registry decides usefulness. Owner: research/data | Open |
| Provider terms do not permit retained original payloads | Medium / High | 30 | Verify contractual retention/use before raw upload; store only permitted representation. Owner: tech-stack researcher + James | Open |
| Future `knowledge_date` leaks into replay | Medium / High | 30 | Cutoff-blocking tests and explicit 36-row future-date fixture. Owner: backend/research | Open |
| Dual writers or dual schedulers diverge stores | Medium / High | 30 | Single ownership, idempotent partition identity, cutover receipt, rollback and no overlapping schedules. Owner: system architect | Open |
| Type/JSON conversion changes research values | Medium / High | 30 | Explicit Parquet types, Decimal/date tests, canonical JSON and field-by-field replay. Owner: backend/data | Open |
| Logical deletion does not reclaim physical/billed space | High / Medium | 28 | Measure relation/database size; plan governed rewrite/maintenance window only after proof. Owner: database owner | Open |
| Model A retirement erases the evidence that justified quarantine | Low / High | 25 | Preserve signals/outcomes/manifest and decay receipt before runtime retirement. Owner: P1 owner | Open |
| Lifecycle policy expires evidence still referenced by a decision | Low / High | 25 | Reference-aware retention classes, Object Lock minimums and deletion review. Owner: security/governance | Open |
| Migration/table rewrite blocks production | Low / High | 20 | Rehearsal, lock/statement timeouts, maintenance window, rollback and observed health. Owner: backend/operations | Open |
| Branch-only state is recorded as main truth | Medium / Medium | 20 | Fresh SHA/PR probe at every mission; source-precedence checks. Owner: arbi | Open |

## 10. Explicit `JAMES_NEEDED` stops

The following are not authorised by this plan and each requires a separate, exact decision:

1. approve or amend the P3-02 S3 credential/Object Lock/restore work order;
2. resolve any unproven EODHD payload-retention/licensing condition;
3. create or configure the bucket, Object Lock, versioning, encryption, IAM identities, lifecycle
   rules or secrets;
4. apply any migration or DDL, including source-object metadata or index changes;
5. perform any production export, S3 upload, dual-write/backfill, table rewrite or deployment;
6. provision an isolated restore destination, copy recovery data/keys to it, write restored state or
   execute the analytical/operational restore drill;
7. change scheduler ownership or cadence;
8. drop `signals_shap_gin_idx`, rows, tables, archives or historical Model A surfaces;
9. perform `VACUUM FULL`, table swap/rewrite or equivalent physical compaction;
10. mark a PR ready, merge, deploy or accept the Stage 1 production observation; and
11. amend the canonical queue, authority, permissions, capital policy or North Star.

## 11. Acceptance and readiness

This planning artifact is complete for James's review when:

- it remains one proposal and changes no roadmap, authority, migration, workflow or implementation
  file;
- the dated baseline clearly separates live observations, repo facts, estimates and inference;
- every material storage surface has a supported KEEP/MOVE/RETIRE disposition, consumer, successor
  and preservation condition;
- current canonical JSON is not misrepresented as original provider bytes;
- exact replay and isolated restore are the primary outcomes;
- projected size reductions show assumptions and logical-vs-physical caveats;
- destructive actions are ordered after checksums, row counts, replay, restore, side-by-side and
  rollback proof;
- the risk register and James-only stops are complete; and
- independent security and architecture/queue reviews pass.

Future implementation remains **QUEUED / NOT EXECUTABLE**, even when this document passes review.
P1-03's merge dependency was observed satisfied during drafting, but every later mission must still
refresh its scheduler truth. Implementation cannot be `READY` until the remaining undisplaced queue
dependencies close, SB1-02 is complete, P3-01 is complete, James approves P3-02, provider-retention questions are
settled, and every required external/schema/production action is individually authorised.

## 12. Red-team record

The pre-execution `arbi-red-team` review returned **PASS** across all five required challenges.

| Challenge | Verdict | Binding condition |
|---|---|---|
| Recency overfit | PASS | Ground the storage issue in already-ratified Stage 1 replay/restore, not today's bill alone |
| Task switching | PASS — closest challenge | Remain queued; do not displace the active P1/SB0 sequence; refresh branch/main truth |
| Cleanup mistaken for product progress | PASS | Replayable cited evidence is the outcome; database size is secondary |
| Low-trust memory overriding repo truth | PASS | Use dated live audit, migrations and executable readers/writers; label branch-only evidence |
| Perfectionism blocking a shippable build | PASS | No currently ship-ready surface was shown to be displaced; the plan remains bounded and inactive |

## 13. Decision options for James

- **Approve as a queued P3-02/P3-03 planning supplement.** This confirms the preparation contract
  without activating implementation.
- **Amend the classification or gates.** Name the table/surface, desired disposition and risk
  trade-off; the canonical queue remains unchanged.
- **Reject/defer.** Supabase remains operational but growth continues; the existing Stage 1
  requirements remain unresolved.

Approval of this document is not approval to create infrastructure, export data, change production,
apply migrations, cut over schedulers, delete data or compact the database.

## 14. Required source ledger

The plan's claims and future acceptance contracts are grounded in these exact authorities:

- [`north-star.md`](../product/north-star.md) — product outcome, model-independent moat and
  capital/evidence firewall.
- [`roadmap-state.md`](../product/roadmap-state.md) — only live ranked queue and Stage 1 state.
- [`target-architecture.md` §6.1](../product/target-architecture.md#61-dual-storage-model) — dual
  storage boundary and canonical temporal contract.
- [`target-architecture.md` §11](../product/target-architecture.md#11-technology-architecture) —
  Supabase operational role, S3/Parquet/DuckDB analytical role and orchestration disposition.
- [`target-architecture.md` §15](../product/target-architecture.md#15-brownfield-migration-sequence) — Stage 1
  evidence deliverables, historical-decision replay and restore exit gates.
- [`asxos outcome-engine and Arbi second-brain execution plan §6`](asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md#6-unified-delivery-sequence)
  — product/second-brain wave ordering and Stage 1 prerequisites.
- [`asxos outcome-engine and Arbi second-brain execution plan §7`](asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md#7-candidate-execution-backlog)
  — canonical P3-02/P3-03 identities and dependencies.
- [`asxos outcome-engine and Arbi second-brain execution plan §8`](asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md#8-claude-code-execution-contract)
  — bounded mission, red-team, receipt and James-only execution contract.
- [`0027_research_store.sql`](../../migrations/0027_research_store.sql) — current research-store
  tables, keys, temporal fields and JSON payload shape.
- [`0001_initial.sql`](../../migrations/0001_initial.sql) — current Model A signal table and SHAP GIN
  index origin.
- [`financial_statements.py`](../../asxos/ingestion/financial_statements.py) — current EODHD
  transform, unconditional conflict update and weekly write behaviour.
- [`fundamentals_pit.py`](../../asxos/ingestion/fundamentals_pit.py) — current yearly-only PIT reader
  and legacy `knowledge_date` derivation path.
- [`weekly-research.yml`](../../.github/workflows/weekly-research.yml) — current ordered scheduled
  writer/derivation chain at the dated snapshot.
- **Live Supabase read-only audit, 2026-08-13 approximately 15:50–16:00 AEST** — exact catalog,
  row/statistics, index-usage, freshness and Supabase Storage observations recorded in §3. This was
  a transaction-read-only observation, not a durable repository source; it must be refreshed before
  execution.
