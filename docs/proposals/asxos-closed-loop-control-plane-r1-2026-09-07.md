# asxos closed-loop control plane — executable specification r1

**Status:** execution-ready proposal; not an authority enactment  
**Owner:** James  
**Date:** 2026-09-07  
**Repositories:** `Jp8617465-sys/asxos`, `Jp8617465-sys/asxos-control`  
**Authority ceiling:** reversible I0–I4 only; human merge at every stage

This revision incorporates the owner's rulings after the 2026-09-07 red team.
It does not modify the ACP, ADR, workflows, rulesets, secrets, environments, or
repository variables. Owner-applied changes remain explicit gates.

## 1. Outcome and non-goals

The loop turns a trusted product failure into one governed draft PR:

```text
protected-main probe
  -> Finding artifact
  -> Sentinel Issue
  -> observed admission + control-ledger lease
  -> WIF producer emits unsigned patch
  -> secretless verifier proves the candidate
  -> credential-isolated publishers post a check and open a draft PR
  -> human merge
  -> originating probe proves recovery three times
  -> Sentinel closes the Issue
```

The target outcome is lower detection-to-draft time without giving model output
a GitHub credential, letting a producer grade itself, or weakening the human
merge gate.

Non-goals:

- no automatic merge; S3 auto-merge is **not ruled**, not prohibited forever;
- no direct push to `main`, admin bypass, force-push, migration, production DB
  write, secret creation, capital action, or Model A use;
- no batch worker: one admission, one lease, one issue, one patch per run;
- no use of Issues prose, labels alone, or a checked-in backlog as authority;
- no Render, Vercel, AWS CodeBuild, or new external orchestration platform.

## 2. Decisions and present-state dependencies

### 2.1 Source-of-truth split

- GitHub Issues own work state: open/closed, human labels, discussion, and the
  visible link to a draft PR.
- The control ledger owns admission decisions, compare-and-set leases, attempts,
  stage evaluations, verification evidence, and execution transitions.
- Actions runs and check runs are evidence sources. They are not copied into a
  second mutable backlog.

This is consistent with ADR D10, which names GitHub Issues as the system of
record for actionable work. The former issue snapshot has no reader and is
retired by draft PR #230.

### 2.2 Observer transport dependency

The stable observation broker is merged in Control PR #12 at
`2bc394d888759d90d82c95afbfcbf94bb66b0ac8`. The concrete authenticated and
replay transport is **not merged**. It is Control draft PR #15, pinned for this
design to:

```text
728e7b9c6b1943ce36743012e3f2fec5dfbe9d4d
```

Items labelled **blocked on #15 merge** must not execute against a live GitHub
credential until that exact reviewed content, or a reviewed descendant, merges.
They must pin the merged commit rather than a moving branch. No r1 change may
modify a path owned by #15.

At the time of this document, #15 is not merge-ready: its third residual risk
lacks the required linked Issue, ambient `SSLKEYLOGFILE` can activate TLS key
logging, and a committed stale `build/lib/asxos_control` tree sits outside its
source-only guards. Those are #15-owner fixes, not r1 work.

### 2.3 Existing control primitives to reuse

`asxos-control` already has deterministic contracts for work admission,
append-only transition and lease semantics, producer envelopes, evidence
envelopes, verification results, observation compilation, and live/replay
GitHub projection. The persistence adapter and runtime workflows are absent.
r1 extends these contracts; it does not create a rival state machine.

## 3. Trust architecture

```text
ASXOS PRODUCT REPOSITORY                     ASXOS-CONTROL

[A] protected-main probes
    existing job credentials only
    produce bounded Finding JSONL
              |
              v
[B] Sentinel projector
    GITHUB_TOKEN: issues write,
                  actions/contents read
    no code/PR/check write
              |
              v
       GitHub Issue work state  <------ [C] observer + Intake
                                         reader token only
                                         #15 transport
                                         control-ledger CAS lease
                                                   |
                                                   v
                                         [D] WIF producer
                                         Anthropic WIF only
                                         NO GitHub credential
                                         unsigned patch artifact
                                                   |
                                                   v
                                         [E] secretless verifier
                                         no secret, network disabled
                                         exact base + patch
                                         V1–V10 + evidence digest
                                            |                 |
                         verifier evidence |                 | verified tree manifest
                                            v                 v
                                  [F] check publisher   [G] branch publisher
                                  Verifier App          Publisher App
                                  checks write only     contents/PR write only
                                  no checkout/code      no code execution
                                            |                 |
                                            +--------+--------+
                                                     v
                                            draft PR + required check
                                                     |
                                                     v
                                                HUMAN MERGE
```

The product caller of a reusable Control workflow pins the Control workflow by
full commit SHA. A moving tag or branch is rejected by a test. GitHub's workflow
`GITHUB_TOKEN` is repository-scoped, so a control workflow does not assume it can
mutate the product repository with its own token.

### 3.1 Credential matrix

| Component | Credential | Permitted effects | Mechanically forbidden |
|---|---|---|---|
| Probe | existing job-specific secrets, when already required | read product/provider state; upload Finding artifact | Issues, PRs, checks, git writes |
| Sentinel projector | product `GITHUB_TOKEN` | issue create/comment/label/close; read trusted run metadata | contents write, PR write, checks write |
| Observer/Intake | reduced observer token | bounded GETs defined by #15 | every mutation |
| WIF producer | Anthropic WIF token only | model call; unsigned patch artifact | any GitHub credential or mutation |
| Secretless verifier | none | local checkout/apply/test/diff | network and every external mutation |
| Check publisher | Verifier App `4847298` | create/update the one named check run | checkout, artifact execution, contents/PR/issues write |
| Branch publisher | Publisher App `4847349` | upload verified blobs/tree, create `claude/issue-<n>`, open draft PR | checks/issues/admin/workflows; code execution |

The App IDs above are owner-supplied identifiers. Runtime activation must verify
the installation, repository selection, and effective permission response; an
identifier in this document is not credential proof.

### 3.2 Producer/publisher boundary

The producer receives a canonical task envelope, a credential-free source
archive at an exact base SHA, and bounded issue evidence. It emits:

```json
{
  "schema_version": 1,
  "work_ref": "Jp8617465-sys/asxos#123",
  "base_sha": "<40 lowercase hex>",
  "producer_envelope_digest": "sha256:<64 hex>",
  "patch_sha256": "sha256:<64 hex>",
  "patch": "<bounded unified diff>",
  "diagnosis": "<bounded text>",
  "confidence": 82
}
```

It cannot comment, label, branch, or open a PR. A low-confidence or protected-
path proposal becomes diagnosis evidence only.

The verifier applies the patch to the exact base, calculates the candidate tree
digest, executes the gate, and emits a bounded verified-tree manifest. The
branch publisher never checks out or runs the candidate. It uploads only blobs
named in that manifest through the Git Data API, reconstructs the tree against
the same base, confirms the resulting tree digest, creates exactly
`refs/heads/claude/issue-<n>`, and opens a draft PR. Any mismatch fails closed.

Publisher credentials are not branch-scoped by GitHub App permissions. The
current server-side backstop is that `main` is protected with no bypass actor;
the exact branch/path mutation allowlist is enforced in the publisher adapter.
Compromise of the Publisher App key remains an owner-managed residual risk.

## 4. Finding contract

Every probe emits zero or more canonical JSON Lines records:

```json
{
  "schema_version": 1,
  "probe": "pipeline_health",
  "failure_class": "data_contract_breach",
  "fingerprint": "sha256:<64 hex>",
  "severity": "L3",
  "title": "sync_prices: NO_EQUITY_DATA (ASX)",
  "identifiers": {
    "job": "sync_prices",
    "contract": "NO_EQUITY_DATA",
    "market": "ASX"
  },
  "evidence": {
    "run_url": "https://github.com/Jp8617465-sys/asxos/actions/runs/<id>",
    "log_excerpt_sha256": "sha256:<64 hex>",
    "log_excerpt": "<at most 2000 redacted characters>"
  },
  "actionable_in_code": false,
  "file_hints": ["asxos/jobs/sync_prices.py"],
  "observed_at": "2026-09-07T18:02:11Z"
}
```

Validation is deny-only: unknown schema version, extra top-level fields,
non-canonical identifiers, excessive text, absolute paths, `..`, malformed URLs,
or residual credential patterns reject the record.

### 4.1 Fingerprint rule

```text
fingerprint = "sha256:" + hex(
  SHA256(UTF8(canonical_json({
    "probe": probe,
    "failure_class": failure_class,
    "identifiers": identifiers
  })))
)
```

Canonical JSON sorts keys, uses UTF-8, has no insignificant whitespace, rejects
floats, and preserves identifier value types. Timestamps, run IDs, row counts,
durations, raw messages, file hints, and excerpts are excluded.

If no stable identity exists, `fingerprint` is `null`. Such a Finding receives a
run-scoped diagnostic Issue and `unfingerprinted`; it is never deduplicated
across runs and never eligible for Intake. The absence of a stable key must not
be hidden behind a title-based pseudo-fingerprint.

### 4.2 Code-actionability rule

`actionable_in_code` is produced by a deterministic classifier, not a model.
Initially it may be `true` only for allowlisted unit-test, lint, type-check, or
pure-code invariant failures that include a parsed failing test/check identity
and a repository-owned non-protected path. Provider outages, rate limits,
timeouts, environment/config failures, data absence, schema drift, migrations,
production data defects, and ambiguous tracebacks are always `false`.

A traceback merely passing through `asxos/` is insufficient evidence. The
classifier emits a reason code, and Intake recomputes the same decision.

### 4.3 Redaction

The verified product redactor is `asxos/redaction.py::redact_secrets`. Probes
redact before hashing or emitting excerpts. `log_excerpt_sha256` hashes the
redacted excerpt. Sentinel scans the complete canonical Finding again. If a
known credential pattern remains, it discards the Finding and emits a bounded
`sentinel_redaction_failure` without the offending text.

No raw log artifact crosses into the credentialed projector. The verifier and
publishers use fixed error messages and sever exception causes at credential
boundaries.

### 4.4 ASX calendar

The repository has no reusable exchange-accurate forward ASX calendar. The
existing decision-engine calendar explicitly says it is naive Monday–Friday,
and price coverage explicitly says it has no holiday calendar. r1 therefore
adds a checked-in, versioned ASX public-holiday table rather than reusing either.

Required record fields are `date`, `market`, `session` (`closed` or
`partial`), `source_url`, `source_year`, and `verified_at`. The source must be an
official ASX calendar. Tests cover a weekend, each checked-in closed holiday, a
normal trading day, a partial session, and a date beyond the table horizon.
Unknown years fail closed to diagnostic/non-actionable. An annual owner Issue is
opened 90 days before the horizon expires; only the owner refreshes the table.

## 5. Sentinel Issue lifecycle

The lifecycle is a pure function over validated Findings, trusted originating-
probe run evidence, open Sentinel Issues, and prior lifecycle projection.

| Rule | Condition | Action |
|---|---|---|
| L1 | Stable fingerprint has no open Issue | Create one Issue and project labels/header. |
| L2 | Stable fingerprint has an open Issue | Add one occurrence comment; do not create another. |
| L3 | Same fingerprint reappears | Reset recovery streak to zero. |
| L4 | Originating probe completes successfully and valid output omits fingerprint | Increment recovery streak once for that probe run ID. |
| L5 | Probe run is missing, failed, cancelled, skipped, duplicated, or has invalid output | Do not increment recovery streak. |
| L6 | Recovery streak reaches three successful originating-probe runs | Sentinel comments with the three run URLs, closes as completed, and records the projection. |
| L7 | Fingerprint reopened more than twice in rolling 30 days | Add `flaky`, remove `arbi-ready`, reset admission eligibility. |
| L8 | Fingerprint is null | Create one run-scoped diagnostic Issue with `unfingerprinted`; never make it eligible. |

Only the Sentinel projector closes Sentinel Issues. A PR uses `Tracks #<n>` or
`Related to #<n>`—never `Closes`, `Fixes`, or `Resolves`. A merge cannot close an
Issue and cannot substitute for three successful probe runs.

### 5.1 Machine block

The first line is versioned canonical JSON encoded in an HTML comment:

```text
<!-- sentinel:v1 {"finding_digest":"sha256:...","fingerprint":"sha256:...","probe":"pipeline_health","run_id":"34067363718"} -->
```

Titles, prose, user comments, and labels are untrusted. Intake accepts the block
only when the linked Actions run exists, ran the pinned protected-main workflow,
used `refs/heads/main`, and produced the matching artifact digest. Exact
versioned parsing and the control ledger bind Issue number to finding digest.

### 5.2 Label taxonomy

| Label | Projector | Meaning |
|---|---|---|
| `sentinel` | Sentinel | Validated Sentinel projection. Label alone proves nothing. |
| `probe:<name>` | Sentinel | Originating probe. |
| `sev:L1`, `sev:L2`, `sev:L3` | Sentinel | Derived severity. |
| `arbi-ready` | Sentinel | Stable, actionable L1/L2, non-flaky, non-protected candidate. |
| `flaky` | Sentinel | Reopen threshold fired; excludes admission. |
| `unfingerprinted` | Sentinel | No stable identity; excludes admission. |
| `human-only` | Owner | Absolute Intake exclusion. |
| `arbi-attempted:<n>` | Intake projection | Display of ledger attempt count; ledger wins on disagreement. |
| `arbi-diagnosed` | Intake projection | A producer diagnosis was accepted into evidence. |

The producer applies none of these labels because it has no GitHub credential.

## 6. Intake, admission, and control ledger

An Issue is eligible only if all are true:

1. its trusted machine block and run artifact validate;
2. the control ledger has no unexpired lease and fewer than two attempts;
3. `sentinel` and `arbi-ready` are projected, while `flaky`, `unfingerprinted`,
   and `human-only` are absent;
4. deterministic code-actionability recomputes true;
5. severity is L1 or L2;
6. every file hint and expected path is outside the versioned protected-path
   manifest;
7. no open PR or existing `claude/issue-<n>` branch occupies the work;
8. the observed default-branch SHA, Issue state, PR state, and checks are stable
   across the broker's two-pass read.

Eligible Issues sort by L2 before L1, milestone-blocking first, oldest trusted
`first_seen` next, then lowest Issue number. The pure ranker is stable under
input permutation. Intake selects at most one and acquires a compare-and-set
lease before producing an envelope.

The current `AppendOnlyLedger` is an in-memory reference implementation. The
runtime adapter must be append-only, support idempotency keys and compare-and-set
leases, retain expired lease history, and expose no delete or rewrite operation.
Its storage stays inside existing GitHub infrastructure: immutable run artifacts
plus a control-owned append-only ledger branch or release asset, selected only
after a persistence red team. Issues must not carry authoritative lease state.

## 7. Verifier contract

Verification executes without a secret and with network disabled. It receives
only the exact base tree, unsigned patch, contract, trusted Issue/finding
projection, and pinned toolchain. It produces a deterministic result and
candidate-tree digest.

| Check | Rule |
|---|---|
| V1 | Full required product suite passes on the candidate tree. |
| V2 | Coverage on candidate head is not lower than coverage on its merge base. No absolute floor exists until separately ratified. |
| V3 | Diff touches no path in the versioned protected-path manifest. |
| V4 | L1 net change ≤50 lines; L2 ≤400; ≤10 files; binary/submodule changes denied. |
| V5 | PR/evidence uses a valid `worker:v1` block and `Tracks #<n>` bound to the admitted Issue and exact patch/tree digests. Closing keywords are denied. |
| V6 | No test file, test class, test function, parameter case, assertion, or fixture is deleted or weakened. |
| V7 | No new skip, xfail, warning suppression, `noqa`, `type: ignore`, coverage omission, or equivalent suppression is added. |
| V8 | No threshold, floor, cap, policy constant, authority file, portfolio boundary, Model A quarantine, or ratified-value carrier is changed. |
| V9 | The originating probe, Finding/fingerprint classifier, calendar, redactor, Sentinel evaluator, verifier, or its policy manifest is not changed by the candidate. |
| V10 | Publication evidence proves the Publisher created the PR as draft. Current draft state is advisory after owner transition; making a PR ready does not invalidate an otherwise good check. |

V6–V9 are syntax/AST plus manifest checks over both old and new trees; substring
grep alone is insufficient. Each has adversarial fixtures. The protected-path
manifest begins with the mechanical authority set in `.claude/settings.json`
and `.claude/hooks/authority-guard.sh`, plus verifier/probe/redactor/calendar
implementation and the ratified-value carriers it discovers through reviewed
explicit entries. A candidate cannot modify that manifest because V9 protects
it.

The check publisher posts `asxos-control/verifier` to the exact candidate SHA.
It receives only a bounded result digest and summary; it never checks out,
parses, imports, or executes candidate content. Failure reports list V-codes and
fixed reason text, not raw logs.

## 8. Required-check and publication sequence

The current product ruleset is `asxos-main` (`19077432`), targeting the default
branch. It currently requires only App-bound `full-check` from integration
`15368`. `control-main-root` belongs to the Control repository and must never be
used as the product binding target.

Sequence is load-bearing:

1. land verifier core and adversarial tests;
2. owner applies the pinned product caller and credential-isolated check-poster;
3. post at least one green `asxos-control/verifier` check on a disposable draft
   PR and query its exact context, head SHA, and App integration ID;
4. only then may the owner add that exact context/App pair to product ruleset
   `asxos-main`;
5. query the ruleset and prove both `full-check` and the verifier check are
   required before enabling producer publication.

There is no auto-merge at any stage. Every produced PR is draft; the owner may
mark it ready and merge only through the protected branch.

## 9. Stage ladder and deny-only demotion

`ARBI_LOOP_STAGE`, created and changed only by the owner, is a **ceiling**.
Control metrics compute a `permitted_stage`. Every job calculates:

```text
effective_stage = min(owner_ceiling, permitted_stage)
```

If the variable is absent, malformed, or higher than implemented policy, the
ceiling is S0. Metrics can only lower effective stage; no job writes the owner
variable. A computed reduction creates an owner Issue containing the metric
window and evidence digests.

| Stage | Sentinel | Intake/producer | Verification/publication | Merge |
|---|---|---|---|---|
| S0 | Creates/updates Issues | Off | Off | Human |
| S1 | Active | One diagnosis-only lease | Evidence only; no branch | Human |
| S2 | Active | One admitted unsigned patch | Secretless verify; check; draft PR | Human |
| S3 | Reserved; not ruled | Not executable by r1 | Not executable by r1 | Human |

Promotion is owner-only. Suggested evidence gates are proposals until recorded
in the ADR:

- S0→S1: at least 20 stable Findings, false-positive and flaky rates each below
  20%, zero redaction or provenance failures;
- S1→S2: at least 20 diagnoses, at least 70% owner-rated correct root causes,
  verifier has posted a green check, and the required-check binding is live;
- S2 continuation: at least 20 Worker PRs, merge rate ≥60%, reopen rate <10%,
  closed-unmerged rate <30%, and zero safety-gate failures.

Rolling 30-day merge rate below 40%, reopen rate above 20%, any credential leak,
provenance mismatch, protected-path proposal, or incorrect successful verifier
result lowers `permitted_stage` by at least one. Safety failures force S0. After
three months at S2, if the loop does not close more Issues than it creates, the
owner is asked to shelve it.

Metrics derive from Actions runs, Issues, PRs/check runs, and the control ledger:
time-to-issue, false-positive rate, flaky rate, diagnosis acceptance, draft-PR
rate, verifier pass rate, merge rate, closed-unmerged rate, reopen rate, lease
contention, duplicate-attempt rate, and median human-review time. Issues/PRs
alone cannot calculate Actions or check-run metrics.

## 10. Revised build order

Do not reorder. Each item begins with the named failing test or executable
conformance assertion. Workflow/settings steps are owner-applied.

| # | Deliverable | First failing test | Dependency and gate |
|---|---|---|---|
| 1 | Retire issue snapshot: writer, payload, old tests, inventory, workflow, and CI exclusions | `test_issue_snapshot_runtime_surface_is_absent` | Draft PR #230. Owner applies the isolated workflow commit; stop until targeted tests and no-reader grep pass. |
| 2 | Finding schema, canonical fingerprint, deterministic actionability, redaction adapter, ASX holiday table | `test_same_failure_has_stable_fingerprint_across_run_metadata` | Can proceed after item 1. No workflow change. |
| 3 | Pure Sentinel lifecycle and label projection, including three-success closure | `test_failed_or_missing_probe_runs_do_not_advance_recovery_streak` | Can proceed after item 2. |
| 4 | `nightly-check` and `pipeline-health` adapters producing Finding artifacts | `test_no_equity_data_fixture_yields_one_non_actionable_finding` | Code first; owner applies the minimal protected-main workflow patch. |
| 5 | Verifier V1–V10, relative coverage, protected manifest, adversarial fixtures | `test_v6_rejects_deleting_one_parameterized_test_case` | Must land before producer. No live transport required. |
| 6 | Pinned product caller plus isolated verifier check publisher; first disposable green check | `test_product_caller_pins_control_workflow_to_full_sha` | **Blocked on #15 merge.** Owner binds App secret/workflow. Must post one green before item 7. |
| 7 | Bind exact verifier context/App to product `asxos-main` | `ruleset_has_app_bound_verifier` executable API assertion | Owner-only; after item 6 green. Query must show `full-check` and verifier together. |
| 8 | Persistent append-only control ledger, deterministic Intake, CAS lease, effective-stage calculation | `test_metrics_can_lower_but_never_raise_owner_ceiling` | Pure/replay work can start earlier; live activation waits for #15. |
| 9 | Live two-pass observer and scheduled Intake issuing one producer envelope | `test_live_intake_refuses_snapshot_without_transport_provenance` | **Blocked on #15 merge** and #13 provenance disposition. |
| 10 | WIF producer runner returning only an unsigned patch/diagnosis | `test_producer_runtime_has_no_github_credential_input` | **Blocked on #15 merge** for live admitted work; verifier already live. |
| 11 | Publisher App adapter reconstructing verified tree and opening a draft PR | `test_publisher_rejects_tree_digest_mismatch_before_any_mutation` | **Blocked on #15 merge**; item 7 required; owner binds publisher key. Human merge remains. |
| 12 | Metrics, deny-only demotion, annual calendar-refresh Issue, and D10 cleanup of legacy backlog lanes | `test_effective_stage_demotion_files_owner_issue_without_mutating_ceiling` | After first S1/S2 evidence; workflow deletions owner-applied. |

## 11. Item 1 gate packet

Draft PR #230 contains two agent commits:

1. `c6d625a` — failing-first retirement guard;
2. `03f4bed` — removes the exporter, empty payload, old presence tests, and
   scheduled-lane inventory entry.

No workflow was changed. The owner must add one isolated commit that:

1. deletes `.github/workflows/issue-snapshot.yml`;
2. removes both `docs/ops/github-issues-snapshot.json` exclusions from
   `.github/workflows/full-check.yml`.

Until then, exactly these targeted gates are expected red:

- `test_issue_snapshot_runtime_surface_is_absent`;
- `test_full_check_has_no_snapshot_exclusion`;
- `test_scheduled_lanes_mirror_the_workflows_that_carry_a_schedule_trigger`.

After the owner commit:

```bash
python -m pytest \
  tests/test_issue_snapshot_retirement.py \
  tests/test_secondbrain_contradictions.py -q

git grep -n -I -E \
  'github-issues-snapshot\.json|ops/issue-snapshot' \
  -- ':!docs/**' ':!.github/**' ':!tests/**'
```

The grep must produce no output. The full suite and fresh CI must then pass.

## 12. Resolved verification ledger

Every unresolved assertion in the proposed r0 was re-derived. Commands below
were run against `origin/main` at
`6f59b8e92f49880e95d22e41f9a5bf1e088ae70b` unless stated otherwise.

| Claim resolved | Query/evidence | Result used by r1 |
|---|---|---|
| Observer transport state | `gh pr view 12` and `gh pr view 15 --repo Jp8617465-sys/asxos-control --json state,isDraft,headRefOid,body` | #12 broker merged; #15 transport open/draft at pinned head. |
| Dependency release | PyPI JSON `https://pypi.org/pypi/cryptography/50.0.1/json` | `cryptography 50.0.1`, 46 release files, Python ≥3.9 with two exclusions. |
| Identifier sources | PR #15 body provenance table; `gh api repos/Jp8617465-sys/asxos` | repository/owner measured; App/installation owner-asserted and runtime-verified before use. |
| Residual Issues | `gh issue view 13`, `gh issue view 14`, Issue search for `ObserverGitHubSession` | #13/#14 open; third residual has no Issue. |
| Snapshot consumers | `git grep -n -I -E 'issue-snapshot|github-issues-snapshot|ops/issue-snapshot' origin/main` | writer/workflow/CI exception/tests/inventory/docs only; no payload reader. |
| Probe workflow names | `rg -n 'name:|schedule:' .github/workflows/{nightly-check,pipeline-health}.yml` | `nightly-check` and `pipeline-health`, both scheduled. |
| Data-contract implementation | `rg -n 'FRESHNESS|contract' scripts/product_health.py docs/product/data-contracts.md` | read-only `scripts/product_health.py`; contract table in `docs/product/data-contracts.md`. |
| Calendar utility | `rg -n 'holiday|weekday|calendar' asxos/domain/decision_engine/calendar.py asxos/domain/prices/coverage.py` | both explicitly lack exchange-holiday authority; new checked-in table required. |
| Redactor | `rg -n 'def redact_secrets' asxos/redaction.py tests/test_redaction.py` | existing tested `redact_secrets` reused. |
| Protected-path source | `rg -n 'Edit\(|authority' .claude/settings.json .claude/hooks/authority-guard.sh`; permission model I5/I6 | settings/guard are the current mechanical set; verifier snapshots it into a versioned deny manifest. |
| Coverage floor | `rg -n 'coverage|pytest' .github/workflows/full-check.yml` | no coverage measurement or ratified floor; V2 is relative head ≥ merge base. |
| Product ruleset | `gh api repos/Jp8617465-sys/asxos/rulesets/19077432` | `asxos-main`, default branch, PR required, strict `full-check`, no bypass actors. |
| Incorrect ruleset name | Control live ruleset and product ruleset queries | `control-main-root` is not the product target. |
| Stage variable | `gh api repos/Jp8617465-sys/asxos/actions/variables` | empty; absent variable must fail closed to S0 until owner creates it. |
| Existing agent lanes | `gh run list --workflow nightly-triage.yml`; same for `backlog-roll.yml` | both have zero runs and are manual-only. |
| Current probe evidence | `gh run list` for both scheduled probes | last five nightly-check runs green; latest pipeline-health run `34067363718` failed. |
| Live-object overlap | GraphQL open-PR query including every target path | no open asxos PR touched retirement or r1 paths before #230 was created. |

There are no unresolved verification markers in this document.

## 13. Anti-patterns and mechanical guards

| Anti-pattern | Named mechanical guard |
|---|---|
| Lower a threshold to make a check green | V8 ratified-value/constant diff guard. |
| Delete or weaken a test | V6 AST test-inventory comparison. |
| Add skip, xfail, ignore, or coverage omission | V7 suppression-token and configuration diff guard. |
| Edit the failing detector | V9 originating-probe and verifier-manifest path lock. |
| Producer grades its own work | WIF producer has no check permission; secretless verifier is a separate job; check publisher receives digest only. |
| Credentialed job executes candidate code | Check publisher has no checkout; branch publisher uses Git Data API and never executes blobs. |
| Prompt injection in Issue prose becomes authority | Exact `sentinel:v1` block, trusted run lookup, two-pass observer, ledger binding; prose ignored. |
| Replay is treated as live | #13 disposition plus required transport provenance and recording digest. |
| Proxy/redirect exfiltrates observer token | #15 fixed-origin `http.client`, exact target allowlist, no redirect following; #15 security gate must pass first. |
| Ambient TLS key logging captures traffic | #15 merge gate must add a test proving `SSLKEYLOGFILE` cannot activate key logging. |
| Secret reaches Finding or error output | Product redactor, residual-pattern rejection, fixed credential-boundary errors. |
| Publisher pushes a different tree | Base SHA + patch + candidate-tree digests; publisher recomputation before ref creation. |
| Direct or forced `main` update | Publisher exact ref allowlist; active no-bypass product rulesets; human PR path. |
| Same Issue is worked twice | Append-only CAS lease and idempotency key. |
| Flapping detector creates daily Issues | Stable fingerprint, one-open-Issue rule, rolling flaky quarantine. |
| Holiday creates false no-data work | Checked-in ASX holiday table and out-of-horizon fail-closed test. |
| Merge closes Issue before recovery | Closing keywords denied by V5; Sentinel-only three-success closure. |
| Agent inflates attempts or edits work state | Control ledger is authority; labels are projections applied by Intake. |
| Metrics promote autonomy | `effective=min(ceiling,permitted)`; metrics only lower and file an owner Issue. |
| Stage 3 silently acquires auto-merge | S3 unimplemented and recorded as not ruled; no auto-merge permission or workflow. |
| Derived backlog drifts from Issues | Snapshot retirement test, D10, and later legacy-backlog no-reader grep. |
| Loop creates more work than it removes | Rolling metrics, deny-only demotion, three-month shelve gate. |

## 14. Reliability, cost, and revisit points

- At one issue per run and a 45-minute producer ceiling, throughput is bounded
  intentionally. Horizontal workers are out of scope until lease and false-
  positive evidence supports them.
- Every network boundary has a byte, page, request, time, and retry budget.
  Retries reuse idempotency keys; ambiguous mutation results are observed before
  retry, never blindly repeated.
- GitHub Actions is the only scheduler. The system tolerates missed cron runs:
  missing runs do not close Issues or raise stage.
- Existing infrastructure keeps monetary cost near current Actions/Anthropic
  usage. Metrics include model tokens and runner minutes per merged fix.
- Revisit after 20 S2 PRs: dedicated reader-only App (#14), durable ledger
  adapter choice, publisher branch confinement, multiple workers, and whether
  S3 deserves a separate owner ruling.

*End of executable r1.*
