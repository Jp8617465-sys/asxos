# S3 object store — credentials / Object Lock / lifecycle / restore work order — 2026-08-22

**Work order:** `P3-02` — F6's named prerequisite. F6 rules the object store and then states:
*"No bucket or credential creation is authorised by this Stage 0 PR"*
(`docs/product/target-architecture.md:1809-1814`). This is the work order that must precede any
action.
**Pairs with:** `P3-01`, the Dagster deployment/cost/cutover work order
(`docs/proposals/dagster-deployment-cost-cutover-work-order-2026-08-17.md`, merged #117). Together
they are the two artifacts `P3-03` names as its dependency: *"P3-01..02 approvals"*
(execution plan §7). **`P3-03`, and therefore all of P4/P5/P6/P7/P8, is blocked until both are
approved.**
**Authority chain:** Amendment B execute-to-completion chaining; `/arbi-run` invoked by James
2026-08-22 with the ruling "P3-02 first, then cap SB".
**Status:** DRAFT — a proposal for James. **Nothing in this document has been performed.** No AWS
account was touched, no bucket exists, no credential was created, no IAM policy was applied, no
object was written.

---

## 0. Method and observation discipline

Per the execution plan's §2.3 recency rule: every live claim carries a source and an
`observed_at`; unknowns are marked `unavailable`.

- **Base SHA:** `e4d40ad6e8d5b00abfd0f06ca36f19ca3dd74bce` on
  `claude/product-roadmap-backlog-8k3jz5`, `observed_at=2026-08-22T08:56Z`.
- **Branch note:** the protocol is one `claude/**` branch per work order. This one rides the
  session's designated branch because the operating instruction for this session names that
  branch explicitly. Flagged, not hidden.
- **Repo observations:** read-only, from the working tree at the base SHA.
- **AWS pricing: `unavailable`.** Attempted `https://aws.amazon.com/s3/pricing/`; the network
  egress proxy blocked the domain (`EGRESS_BLOCKED`, `observed_at=2026-08-22T08:55Z`). No rate is
  asserted anywhere below. §4 gives the cost *structure* and the exact quantities to multiply;
  James (or a session with egress) fills the rates. **Do not approve the cost position on this
  document alone.**
- **Database sizing: `unavailable`.** The `pg_total_relation_size` probe required an approval this
  non-interactive session cannot obtain. §4.1 therefore sizes from row counts observed elsewhere
  this session rather than from on-disk bytes, and says so at each figure.

---

## 1. The FROM state — what protects irreplaceable data today

**Mechanism** (`scripts/backup_irreplaceable.sh`, `.github/workflows/backup.yml`): a daily
`pg_dump` of the irreplaceable tables, gzipped, **committed to a private GitHub repository**
(`$BACKUP_REPO`). Cron `30 13 * * *`, 20-minute timeout, `permissions: contents: read`.

**Fourteen tables are dumped:** `holding_lots`, `decisions`, `screening_rules`, `model_versions`,
`profiles`, `themes`, `theses`, `thesis_revisions`, `theme_holdings`, `macro_theses`,
`agent_runs`, `agent_evidence`, `governance_events`, `price_revisions`.

**Deliberately excluded as re-derivable:** `prices`, `fundamentals`, `universe`,
`regulatory_events`, `job_runs`, `portfolio_daily_snapshots`, `rebalance_runs`,
`target_allocations`, `proposed_trades`.

**One frozen-evidence archive sits outside the daily set** — `signal-evidence-2026-08-16/` in the
backup repo, holding `signals` (64,189 rows, sha256 `e61ee6a4…`) and `signal_outcomes` (60,072
rows, sha256 `7aef5234…`). Captured once because both tables are frozen: re-dumping them daily
would write identical bytes forever. This is the rule #11 evidence base and is the single most
irreplaceable artifact the system holds.

**Restore is already drilled.** `backup.yml` carries a `restore_drill` `workflow_dispatch` input
that restores the day's dump into clean ephemeral PostgreSQL 17 and verifies row counts. Run
`31465179375` was observed green — backup *and* restore, with all table counts verified
(`roadmap-state.md` defect #1).

### 1.1 What is actually wrong with it

Not durability — GitHub is durable. Three real defects:

1. **Monotonic growth in git.** Every daily dump is a new blob. A git repository is
   content-addressed and never forgets; the backup repo grows without bound and cannot be pruned
   without rewriting history, which breaks every existing clone.
2. **No immutability guarantee.** Anything holding `BACKUP_GITHUB_TOKEN` can force-push the backup
   repo and destroy the history. That token is a repo-scoped write credential held in Actions
   secrets. This is precisely the property Object Lock exists to remove.
3. **Wrong store for the Stage 1 workload.** §6.1 requires an immutable analytical store for raw
   vendor payloads, announcements, extraction artifacts, partitioned Parquet, research-run
   artifacts and rendered decision packets. None of that belongs in a git repo, and none of it is
   backed up anywhere today because none of it is produced yet.

---

## 2. The decision that cannot be reversed — read before anything else

**S3 Object Lock can only be enabled when the bucket is created.** It requires versioning, and
enabling it on an existing bucket is not a self-service operation. Every other setting in F6
(lifecycle, encryption, credentials, even versioning) can be changed after the fact. This one
cannot.

That makes the bucket-creation call a one-shot decision, and it is why F6 named a work order
before it rather than letting a session create the bucket opportunistically.

**Two consequences James should decide deliberately:**

**(a) Object Lock and a daily full dump are a bad pair.** Governance-mode retention prevents
deletion until the retention date passes, and **a lifecycle policy cannot delete a locked object
early** — lifecycle and Object Lock do not override each other; the lock wins. A daily gzipped
dump under a 7-year retention is ~2,555 immutable objects per 7 years that cannot be pruned even
if they are redundant. The daily dump is *not* the workload Object Lock was ruled for; §6.1's raw
evidence is.

**(b) Governance mode, not compliance mode — and F6 already ruled this correctly.** Governance
mode allows a principal holding `s3:BypassGovernanceRetention` to shorten or remove a retention.
Compliance mode allows nobody, including the root account, until expiry. For a single-user system
where an operator error could otherwise become permanent and unbudgeted, governance is the right
call. Stating the reason so it is not "corrected" later by someone reading compliance mode as
strictly better.

---

## 3. Recommended shape

**Two prefixes, two retention policies, one bucket.** Splitting by prefix rather than by bucket
keeps one set of credentials, one lifecycle document and one restore procedure.

| Prefix | Contents | Object Lock | Lifecycle |
|---|---|---|---|
| `raw/` | §6.1's immutable analytical store — vendor payloads, announcements, extraction artifacts, Parquet, research-run artifacts, rendered decision packets | **retention ON**, governance mode, default retention to be set by James | transition to Standard-IA after 90d; **no expiry** |
| `backup/` | the daily `pg_dump` set + the frozen `signal-evidence-2026-08-16/` archive | **frozen archive: retention ON. Daily dumps: retention OFF** | daily dumps: keep 30 daily, 12 monthly, then expire. Frozen archive: no expiry |

The split is the point. It gives the frozen rule #11 evidence a genuine immutability guarantee —
which it does not have today — without committing every future daily dump to permanent,
unprunable storage.

Key structure for `raw/`, taken verbatim from §6.1:

```
raw/{provider}/{dataset}/ingest_date=YYYY-MM-DD/run_id={uuid}/{content_hash}.{ext}
```

**Credentials — two principals, not one:**

- **Writer** (used by jobs): `s3:PutObject`, `s3:PutObjectRetention` on `raw/*` only.
  **No `s3:DeleteObject`, no `s3:BypassGovernanceRetention`.** An append-only writer cannot
  destroy history even if the credential leaks.
- **Restorer** (used by the drill): `s3:GetObject`, `s3:ListBucket`. Read-only.

`s3:BypassGovernanceRetention` is granted to **no** stored credential. It stays an interactive
root/admin action, which is what makes governance mode meaningfully different from compliance
mode in practice.

**Encryption:** SSE-S3 (SSE-KMS adds per-request KMS charges and a second failure mode for a
single-user system; if James wants KMS, that is a deliberate upgrade, not a default).

---

## 4. Cost structure — quantities here, rates NOT asserted

Every rate below is `unavailable` (§0). These are the quantities to multiply.

### 4.1 Sizing inputs

Sized from row counts observed this session, not on-disk bytes (§0):

| Input | Observed | Source |
|---|---|---|
| Frozen archive | 124,261 rows total (`signals` 64,189 + `signal_outcomes` 60,072) | `backup_irreplaceable.sh` header, with sha256s |
| Daily dump | 14 tables; largest are `agent_evidence`, `governance_events`, `thesis_revisions` — all append-only and small | script header |
| `raw/` steady-state ingest | not yet produced — Stage 1 builds it | — |
| Corporate actions, one weekly run | 31,435 rows (28,641 dividends + 2,794 splits) | run `32099973966`, 2026-08-18 |
| PIT fundamentals, one run | 53,687 rows / 3,360 symbols | same run |

**The honest position: `raw/` is the cost driver and it does not exist yet.** The backup workload
is small — a gzipped dump of 14 append-only tables. Anyone sizing this bucket on today's backup
will under-size it by whatever Stage 1's raw ingestion turns out to be, and that figure is
genuinely unknown until `P3-03` defines what gets landed.

**Recommendation:** approve bucket creation with lifecycle and Object Lock configured as §3, and
set a **billing alarm** rather than trying to forecast `raw/` before it exists.

### 4.2 Rate lines to fill

S3 Standard $/GB-mo · S3 Standard-IA $/GB-mo · PUT/COPY/POST/LIST $/1,000 · GET $/1,000 · data
transfer OUT first tier. Object Lock and versioning carry no separate charge, but **versioning
means every overwrite retains the prior version and each version is billed** — the interaction
that surprises people.

---

## 5. Acceptance — F6's six requirements, mapped

F6 requires: versioning · Object Lock governance mode · encryption · least-privilege credentials ·
lifecycle policy · **a separately observed restore test**.

| # | Requirement | How it is proven |
|---|---|---|
| 1 | Versioning | `get-bucket-versioning` returns `Enabled` |
| 2 | Object Lock, governance | `get-object-lock-configuration` returns governance + the default retention |
| 3 | Encryption | `get-bucket-encryption` returns the SSE algorithm |
| 4 | Least privilege | writer credential's `DeleteObject` on `raw/*` returns `AccessDenied` — **proven by a denied call, not by reading the policy** |
| 5 | Lifecycle | `get-bucket-lifecycle-configuration` returns the §3 rules |
| 6 | **Separately observed restore** | extend `backup.yml`'s existing `restore_drill` to pull from S3 and verify counts; one observed green run, recorded with its run id |

Requirement 4 is the one most likely to be faked by inspection. A policy that *reads* correct and
a call that is actually denied are different claims; only the second is evidence.

---

## 6. Hard stops

Unchanged, and every one is load-bearing here:

- **No AWS account, bucket, credential, IAM policy or KMS key is created by this document.**
  Credential creation is a mandatory stop under every amendment and under F6 explicitly.
- No migration, no destructive DB operation, no production write.
- No scheduler cutover — `backup.yml` is untouched; `.github/` is Edit-denied to the agent, so
  even the restore-drill extension in requirement 6 must be applied by James or through a
  reviewed PR he merges.
- No push to `main`, no self-approval, no merge.
- Rule #11 stands: the frozen `signals`/`signal_outcomes` archive is **evidence to preserve**, not
  a model to revive.

## 7. Decision points for James

| # | Decision | Default if you say nothing |
|---|---|---|
| D1 | Create the bucket at all, in `ap-southeast-2` | not created; Stage 1 stays blocked |
| D2 | The two-prefix split in §3, or Object Lock across everything | §3 split — the alternative makes every daily dump permanent |
| D3 | Default retention period for `raw/` and for the frozen archive | unset; must be chosen before creation |
| D4 | SSE-S3 or SSE-KMS | SSE-S3 |
| D5 | Move the frozen `signal-evidence-2026-08-16/` archive to S3, or leave it in the backup repo | leave it — moving it is a separate, observed operation |
| D6 | Keep the git backup repo running in parallel during transition, and for how long | keep both until one observed S3 restore passes |

## 8. Self-limiting statements

- **The cost position in this document is incomplete by construction** (§0, §4). It must not be
  approved as a cost case.
- **`raw/` is sized at zero because it does not exist.** Every figure in §4.1 describes the
  *backup* workload, which is not the workload F6 was ruled for.
- **The Object Lock create-time constraint (§2) is stated from AWS's documented behaviour, not
  from a probe** — no AWS surface was reachable from this session. It is the one claim here that
  most deserves independent confirmation before D1 is acted on, because the whole
  one-shot-decision framing rests on it.
- This document does not re-litigate F6. It prices and sequences a ruled decision.

## 9. Provenance

Written 2026-08-22 at base SHA `e4d40ad`. Sources: `target-architecture.md:1809-1814` (F6),
`:337-377` (§6.1 dual storage model), `scripts/backup_irreplaceable.sh`,
`.github/workflows/backup.yml`, `docs/product/roadmap-state.md` defect #1 and `:52`,
`docs/proposals/dagster-deployment-cost-cutover-work-order-2026-08-17.md` (the paired `P3-01`),
and the execution plan §7 dependency row for `P3-03`.
