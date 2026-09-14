# Arbi chief of staff and autonomy control plane — final pre-execution plan

- **Status:** final pre-execution proposal; red-team amendments folded in; **not authority**
- **Plan date:** 2026-09-06 (Australia/Brisbane)
- **Live baseline:** `origin/main` at `b4c53a1` after PRs #178–#201 landed
- **Owner / governor:** James
- **Proposed operating owner:** Arbi
- **Primary execution layer:** Claude
- **Optional secondary execution/review:** Cursor and Codex; never required for liveness
- **Infrastructure constraint:** GitHub Actions + Supabase only; no AWS CodeBuild,
  self-hosted-runner fleet, or new compute platform
- **Current runtime truth:** neither Render nor Vercel is active; there is no external
  application deployment target in scope
- **Supersedes as advisory design:** the version of this file at `637d310`
- **Non-scope:** this file does not ratify Amendment M, create infrastructure, bind a
  secret, activate a workflow, merge, apply a migration, write production data,
  change capital policy, or lift the Model A quarantine

> This is the implementation contract to red-team and ratify, not an authority source.
> Current I5/I6 and P5/P6 stops continue to bind until James records an explicit
> amendment. Implementation must not infer permission from the ambition in this plan.

## 1. Executive decision

Build Arbi into the **chief-of-staff control plane** for asxos. Arbi maintains one
truthful work portfolio, admits and routes work, coordinates delivery, manages
exceptions, observes outcomes, and promotes autonomy by capability. Claude is the
normal end-to-end execution layer. Cursor and Codex are optional additional capacity,
not dependencies. Deterministic controllers—not a model process—perform privileged
side effects.

The target is not a more elaborate planning ceremony. It is maximum useful autonomy:

- production code is the default deliverable for an admitted engineering outcome;
- four bounded lanes may work concurrently in Lab from day one;
- low-risk production changes can ultimately land without a founder click;
- workflow activation, scheduled-runtime promotion, additive migrations, and typed
  production writes become autonomous one capability at a time behind mechanical fences;
- James owns secret values and their initial bindings, but an approved controller can
  exercise the bound capability without exposing the value or asking on every run;
- contract migrations may become eligible through an archive-first forward-recovery
  protocol;
- constitutional changes, secret binding, capital execution, and advice-like portfolio
  output remain James-owned.

The design separates cheap, reversible failure from expensive, irreversible failure.
Lab is deliberately permissive. Live is mechanically constrained. A valid red-team
finding strengthens the fence; it does not shrink the intended capability.

## 2. Baseline and truth corrections

This plan re-derives its execution baseline instead of inheriting the obsolete state at
`637d310`:

- `origin/main` is `b4c53a1` (`fix(decision): restore point-in-time and delivery
  integrity (#201)`).
- PRs #178–#201 have landed. The 14-PR merge inventory in the 2026-09-03 handoff is a
  correct dated record, not current state.
- Amendment H's decision chain, Amendment H standing lanes, Amendments I/J/K/L, and
  PR #201's corrective semantics are on `main`.
- Current Amendment H lanes remain owner-dispatched while their producer write-token
  exposure is open. Installed workflow files are not proof that the loop is armed.
- D10 selects GitHub Issues + Projects as the intended work substrate, but operational
  cutover is incomplete. `roadmap-state.md` and `backlog.yaml` still contain stale
  executable state.
- The 2026-09-06 dream is a candidate, not promoted memory or authority.
- Model A remains shelved and mechanically blocked from allocation by the revoked
  approval/production gate as well as `CLAUDE.md` rule #11.
- Render was deleted on 2026-08-12 and Vercel is not active. There is no current external
  application deployment target. Production execution is GitHub Actions jobs plus their
  Supabase/Resend/Healthchecks effects, so merge-to-runtime coupling must be analysed
  through scheduled-workflow reachability. Deployment automation is dormant and out of
  scope until a real target is adopted by a separate decision.

Live GitHub, repository settings, branch rules, Supabase settings, workflow secrets,
and scheduled-runtime reachability must be re-probed at Phase 0. Any count or setting
in prose is evidence dated 2026-09-06, not permanent truth.

## 3. Non-negotiable hard boundaries

Everything outside these boundaries is eligible to be delegated once its controller
and evidence gate exist.

1. **No model process holds a product production credential.** Product database,
   GitHub write, runtime-promotion, send, billing, or broker credentials never enter Claude,
   Cursor, Codex, or repository-code execution. Model-provider authentication is a
   separate bootstrap surface: prefer short-lived workload identity, isolate it by
   environment, and enforce spend caps.
2. **Model-authored and repository-authored code never shares a process with a
   privileged credential.** Repository tests/builds run secretless and offline.
   Secret-bearing jobs run only pinned control code and do not execute a product
   checkout.
3. **Risk class is derived from the candidate change.** Paths, modes, workflow
   permissions/triggers, migrations, dependencies, imports reachable from production
   jobs, database effects, destinations, user-facing output, advice relevance, and
   authority surfaces determine routing. Builder labels are calibration data only.
   Ambiguity fails closed to the highest plausible class.
4. **Ingestion has zero control-plane or repository write authority.** Web pages,
   filings, announcements, news, PR prose, Issue prose, and agent output are untrusted
   data. Ingestion emits typed records only.
5. **Controllers are a separate trust domain.** `asxos-control` owns verification,
   signing, publishing, landing, fuses, spending, and production-effect brokers.
   Product PRs cannot edit the controller evaluating them.
6. **Advice and engineering autonomy are separate.** Anything resembling a personal
   portfolio recommendation remains human-gated. No controller executes capital.
   Model A cannot be used as capital evidence.
7. **Authority cannot self-expand.** Arbi may propose a boundary change; only James can
   ratify the constitution, capability scope, secret binding, or fuse policy.
8. **Every privileged action is attributable and recoverable.** It binds to an admitted
   contract, exact source/artifact identity, controller policy version, ledger event,
   observation, and rollback or forward-recovery path.

## 4. Target operating model

| Actor | Accountable for | May mutate | Must not do |
|---|---|---|---|
| James | Product mandate, risk appetite, secret values/bindings, capital, constitutional changes, root-of-trust exceptions | Authority and explicitly reserved operations | Routine coordination or step-by-step delivery |
| Arbi | Intake, prioritisation, contracts, WIP, lane routing, commitments, exceptions, observation, promotion packets | Protected work state through a scoped controller | Implement product code, certify itself, handle secrets, execute capital |
| Claude | Primary architecture, implementation, tests, remediation, branches, draft PRs, and operational orchestration | One assigned mutable node within its contract | Hold product credentials, certify its own evidence, bypass controllers |
| Cursor / Codex | Optional specialist, overflow, recovery, or independent perspective | Only when explicitly assigned the same typed contract | Become required for system liveness or receive greater authority |
| Fresh reviewer context | Semantic/adversarial review of frozen contract + derived bundle + diff | Findings only | Read mutable PR persuasion as authority; author the implementation under review |
| Deterministic controllers | Verify, sign, publish, mark ready, land, promote scheduled runtime, migrate, write, send, observe | One allowlisted capability | Interpret open-ended work prose or execute product code in a secret-bearing job |

Exactly one model-based mutator owns each mutable node. Overlap is deliberate only for
producer/challenger, implementer/verifier, or independent evidence. The mandatory review
property is a separate context and evidence chain; it is not a dependency on a second
model provider. Cursor/Codex review can be measured and used when available.

```text
James: mandate · secrets · constitution · capital
                         |
                         v
Arbi: contract · priority · lane · WIP · exception
                         |
                         v
Claude: build · test · remediate · propose patch
              | optional specialist/reviewer
              +------ Cursor / Codex / fresh Claude
                         |
                         v
Control: verify · attest · publish · land · operate
                         |
                         v
Runtime + ledger: observe · reconcile · fuse · learn
                         |
                         +------> Arbi advances, reshapes, or escalates
```

## 5. Existing-infrastructure trust architecture

### 5.1 Why the execution plane moves to `asxos-control`

A reusable workflow executes in its caller's context and cannot safely obtain a called
private repository's secrets. A product branch can also change a product workflow. The
autonomous execution plane therefore originates inside `asxos-control`; the product
repository does not dispatch a privileged cross-repository workflow.

`asxos-control` discovers admitted work by either:

1. polling the control ledger with a serialized lease; or
2. receiving a GitHub App webhook through a control Supabase Edge Function and writing
   a typed admission event to that ledger.

No product-repository credential is needed to start the control run. The control App
reads the exact product SHA. Branch publication and required checks are performed later
by separate Apps/jobs.

### 5.2 End-to-end execution path

```text
admitted immutable contract in control ledger
                 |
                 v
asxos-control execution lease
                 |
                 v
read-only checkout of exact product SHA
token/config scrub before the model starts
                 |
                 v
Claude producer sandbox
  short-lived provider identity only
  no GitHub write
  no product secret
  does not execute product code
                 |
                 v
patch + declared manifest artifact
                 |
                 v
secretless offline verifier
  derives paths/modes/effects from patch
  applies patch to exact base
  runs tests/policy in prebuilt image
                 |
                 v
OIDC-bound signer + append-only evidence
                 |
                 v
deterministic publisher
  validates lease, digest, scope, size, modes
  creates only allowed agent branch/commit
                 |
                 v
control-App required check at exact head
                 |
                 v
ready / landing / runtime controller
                 |
                 v
observation + reconciliation + fuse result
```

### 5.3 Model producer sandbox

Claude needs network access to a model provider, so the model workspace cannot use
`--network none`. It runs as non-root in a read-only container with an egress allowlist
limited to the provider API.

The preferred authentication route is **Anthropic workload identity federation**. The
exact Claude Action commit already pinned in this repository (`a874e9e`) exposes the
federation rule, organisation, service-account, workspace, and audience inputs. A
control-repository job uses GitHub OIDC to exchange its exact workflow identity for a
short-lived Anthropic access token. Federation identifiers are configuration, not
secrets. The producer receives no static `CLAUDE_CODE_OAUTH_TOKEN` or
`ANTHROPIC_API_KEY`, no GitHub write token, and no product credential. The federation
rule binds the control repository, protected workflow/ref, service account, workspace,
and expected audience; the Anthropic workspace carries the hard spend cap.

Phase 1 must prove tenant availability, exact claim matching, token lifetime/revocation,
egress restriction, and compatibility with the tokenless producer interface. James owns
the one-time Anthropic organisation/service-account/federation binding. The official
[Claude Action setup guide](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md#workload-identity-federation)
is the current primary source; implementation remains pinned to a reviewed commit.

If the Anthropic account cannot enable federation, a **provider-specific
TLS-terminating relay** is the fallback, not an assumed Phase-1 component. It must inject
the upstream key server-side, expose no credential-read or generic CONNECT endpoint,
validate the provider API surface and limits, and issue only an expiring run-bound
handle. A normal HTTPS CONNECT proxy is insufficient. Relay unavailability or failure
to contain the credential returns to James; it never justifies mounting an upstream key
in a model-controlled process.

The model container may read the exact source snapshot and write only its patch/output
directory. It has no Docker socket, host environment, production credential, GitHub
write token, or general outbound route. It does not run project tests, package managers,
build hooks, or repository executables.

### 5.4 Repository-code verifier

Tests, lint, type checks, builds, and preflights execute separately:

- prebuilt dependency image, identified by digest;
- rebuilt only by trusted control code from the lockfile;
- `docker run --network none`;
- no secret, OIDC token, model key, deadman URL, or GitHub write token;
- non-root, read-only root filesystem and source mount where possible;
- dropped Linux capabilities and `no-new-privileges`;
- no Docker socket;
- local Postgres inside the test container where DB tests require it;
- external HTTP replaced by fixtures or a typed fetch artifact.

The Phase-1 inventory must identify tests that currently call live endpoints. Fixture
conversion is part of the verifier exit gate, not an ignored transition cost.

### 5.5 Fetch and effect brokers

Production work uses broker–compute–broker separation:

```text
trusted fetch broker -> bounded typed artifact -> offline compute
offline result -> schema/digest/policy validation -> trusted effect broker
```

Secret-bearing brokers:

- run only as `asxos-control` workflow jobs or control Supabase functions;
- never checkout or execute product repository code;
- use fixed query templates, destinations, recipient classes, stored functions, row
  limits, timeouts, and idempotency keys;
- reject free-form shell, SQL, URL, ref, recipient, or workflow input;
- record capability, caller evidence, result, cost, and recovery identity.

Examples:

- web research: allowlisted fetch -> untrusted content artifact -> offline extraction ->
  typed findings broker;
- database computation: named read -> offline calculation -> allowlisted RPC write;
- email: bounded context -> offline render -> fixed-recipient send broker;
- migration: schema/telemetry snapshot -> offline preflight -> exact-digest migration
  controller;
- publication: verified patch -> Git data/API branch writer without code execution;
- scheduled runtime: exact ref -> canary/health gate -> promotion or revert.

There is no active Render, Vercel, or other application-deployment target. A deployment
broker is not built speculatively. If hosting is adopted later, it requires a separate
architecture decision, production-effect class, controller, and capability promotion.

### 5.6 Credential policy

- James owns and initially binds every secret.
- The product repository ultimately holds **zero production or broker credentials** in
  Actions secrets or variables.
- During migration, no autonomous product-branch workflow may run until current secret
  exposure is inventoried and isolated.
- No workload uses Supabase `service_role`.
- Controllers use per-purpose database roles or stored functions with explicit table,
  operation, and row limits.
- Publisher, reviewer, landing, migration, data, scheduled-runtime, and send identities are
  separate where their capabilities differ.
- Lab and Live use separate GitHub App installations, Supabase projects, and model API
  keys with independent spend caps.
- Secret rotation or rebinding remains James-owned. Invoking an already bound capability
  can become autonomous.

## 6. Control trust domain

Create a private `asxos-control` repository inside the current GitHub provider and a
separate Supabase control organisation. This is logical isolation within existing
infrastructure, not a new compute platform.

`asxos-control` owns:

- admission polling/webhook gateway;
- contract and work-state transaction schemas;
- production-effect classifier;
- review-bundle selection;
- offline verifier definitions;
- evidence envelope and signer;
- branch publisher;
- ready/landing controller;
- workflow, scheduled-runtime, migration, data, fetch, and send brokers;
- capability registry and dependency graph;
- local/dependent/global fuses;
- cost meter and per-lane/month ceilings;
- boundary checksum and immutable eval set;
- reconciliation and recovery tooling.

Phase 1 rules:

- protected `main`, confirmed available for the owning account before creation;
- James merges every control-repository change;
- the product repository consumes an immutable control commit/digest, never a movable
  tag; changing that value is a boundary change;
- the landing broker is mandatory. Native GitHub merge queue is not assumed;
- control workflows are defined at protected control `main`, not supplied by a product
  PR;
- the required verification check is created only by the control App and, where GitHub
  supports it, branch rules bind the required context to that App identity.

After the reviewer/classifier have a pinned released version and self-change tests,
non-boundary controller maintenance may enter its own promotion track. Credential scope,
signer, boundary policy, capability definitions, pinned control version, and root-of-trust
changes remain James-owned.

## 7. Contract and control data model

### 7.1 Canonical ownership

| Information | Canonical source | Projection |
|---|---|---|
| Product mandate and constitutional boundary | James-ratified authority document/control record | Linked from programme Issue |
| Feature intent and current admitted contract | Append-only control-ledger contract row | GitHub Issue summary/comment with digest |
| Lifecycle, lane, WIP, lease, revision | Transactional control ledger | Projects fields and generated Issue receipt |
| Execution facts and controller decisions | Append-only control ledger | Issue/PR evidence comment |
| Code and review boundary | Git branch/commit/PR | Issue links |
| Runtime identity | Workflow/release-ref record | Feature observation receipt |
| Durable architectural decision | ADR | Contract link |
| Explanations/reference/runbooks | Existing canonical docs | Generated index |

GitHub is the founder-facing interface. Postgres is the concurrency and audit authority.
GitHub Issues/Projects APIs do not provide the conditional state transitions the control
plane requires, so leases and compare-and-set occur transactionally in the ledger.
GitHub fields are idempotent projections written after commit. A projection divergence
cannot authorize work.

### 7.2 Minimal contract record — required in Phase 1

```yaml
work_ref: "repo + parent Issue"
revision: r1
previous_revision: null
status: admitted
outcome: "observable result"
appetite: "bounded slices / elapsed time / cost"
no_gos: []
acceptance:
  - id: AC-1
    given: "..."
    when: "..."
    then: "..."
observation:
  metric: "..."
  window: "..."
authority_ceiling:
  infrastructure: I4
  portfolio: P2
production_effect_expectation: []
dependencies: []
author_identity: "verified controller/James identity"
reason: "initial admission"
content_digest: "sha256:..."
created_at: "database time"
```

Each revision is a new row. Update/delete is denied. The Issue comment mirrors the full
human-readable contract and ledger digest but is not authoritative. Verifier, publisher,
reviewer, and landing controller read the ledger row.

Revision rules:

- acceptance freezes at admission;
- builder identity has no revision write path;
- only the product-controller capability proposes a revision;
- tightening is recorded without raising risk;
- loosening/removal raises the contract risk class one step and requires a reason;
- three revisions maximum; `r4` escalates to James;
- outcome, appetite, no-go, authority, or subjective acceptance changes require James
  unless a later explicit amendment delegates that exact field;
- every candidate binds to the exact revision digest.

### 7.3 Event and evidence records

Every state transition contains:

- work/contract identity and expected revision;
- prior and requested state;
- actor and controller identity;
- authority/capability basis;
- idempotency key;
- lease owner and expiry;
- input and output digests;
- decision/result/error;
- cost and elapsed time;
- source, candidate, merge, release, and runtime identities where applicable;
- rollback/forward-recovery identity;
- observation and fuse result.

One serialized mutation queue handles attended and autonomous operations. James override
invalidates an open lease and forces a fresh read.

## 8. Evidence, review, and attestation

### 8.1 Evidence envelope

```yaml
schema_version: 1
work_ref: "..."
contract_revision: r1
contract_digest: "sha256:..."
repository: Jp8617465-sys/asxos
base_sha: "40 hex"
candidate_patch_digest: "sha256:..."
candidate_tree_digest: "sha256:..."
declared_manifest_digest: "sha256:..."
derived_effect_manifest_digest: "sha256:..."
review_bundle_digest: "sha256:..."
toolchain_image_digest: "sha256:..."
control_workflow_ref: "asxos-control/...@immutable-sha"
run_id: "..."
run_attempt: 1
derived_risk_class: "..."
tests: []
overlays: []
reviewer_identity: "..."
review_verdict: READY
capability_requested: "branch.publish"
capability_policy_version: "..."
rollback: "..."
observation: "..."
```

The verifier derives changed paths, file modes, imports, and effects from the patch/tree;
it never trusts the model's manifest for routing. It rejects protected paths, symlinks,
submodules, unexpected binaries, oversized files/diffs, stale bases, unknown encodings,
and contract/artifact mismatch.

### 8.2 Signer authenticity

Use a signed DSSE-style envelope stored in the control ledger as the default design.
Native GitHub artifact attestation may replace only the signing transport after account
availability and equivalent claim binding are proved.

The signer accepts evidence only from the pinned `asxos-control` verifier identity. If
GitHub OIDC is used, it verifies at minimum:

- issuer and audience;
- `repository` / owner;
- protected control workflow identity and immutable ref;
- product repository and exact source SHA carried by the verifier result;
- run ID and attempt;
- environment/ref restrictions;
- freshness and nonce/idempotency binding.

The control App posts the trusted required check only after signature and ledger commit.
An arbitrary product job emitting the same check name or envelope must not satisfy the
gate.

### 8.3 Review bundle and independence

The deterministic control step selects the base-tree files required by the dependency
graph. The builder cannot choose or omit review inputs. Reviewer input is limited to:

- frozen contract and digest;
- derived production-effect manifest;
- diff;
- selected base-tree context;
- test/evidence results.

PR body, Issue prose, code comments, and bundled content are untrusted data, never
authority. The reviewer runs in a separate context from the producer. A fresh Claude
review is sufficient for the required semantic lane because deterministic gates are the
trust substrate. Cursor/Codex or other-provider review is optional measurement. Its
absence never blocks system liveness or silently changes deterministic policy.

## 9. Deterministic production-effect classification

The manifest computes:

- touched paths, file types, modes, binary/symlink/submodule state;
- migrations and expand/contract/destructive classification;
- dependency manifests, lockfiles, registries, package identities, and build hooks;
- `.github/**` triggers, permissions, actions, environments, and secret references;
- imports/call paths reachable from scheduled or production jobs;
- database reads/writes, sensitive tables, stored functions, and row cardinality;
- network destinations and external providers;
- user-facing renders, notifications, emails, CLI output, and advice-like paths;
- tax, portfolio, capital, Model A, authority, controller, and secret surfaces;
- rollout, observation, and recovery mechanisms.

If static reachability cannot resolve a changed symbol, inherit the highest production
effect of every candidate path. The builder's proposed class is recorded only to measure
calibration.

Protected classes include at minimum:

- authority/control-root;
- secret binding;
- advice/capital;
- Model A;
- supply-chain;
- workflow/permission;
- migration expand;
- migration contract/destructive;
- sensitive data read/write;
- send/external effect;
- scheduled-runtime reachable;
- low-risk isolated code/docs.

## 10. Work and version-control control plane

### 10.1 Work identity

- One parent GitHub Issue is the feature/outcome identity.
- One sub-issue is an independently verifiable vertical slice.
- Do not create a second `FTR/BUG/OPS` identifier sequence.
- Carry parent/slice and contract digest through branch, commit, PR, evidence, release,
  runtime, observation, and rollback.

### 10.2 Four operating lanes

| Lane | Purpose | WIP |
|---|---|---:|
| Strategic feature | Direct product-outcome advancement | 1 |
| Reliability | Correctness, security, incidents, data integrity | 1 |
| Maintenance | Dependencies, refactors, operational hygiene | 1 |
| Exploration | Experiments, architecture probes, evidence | 1 |

Arbi admits, sequences, and resolves collisions. James changes the standing mandate or
overrides the selected bet. Lab runs all four immediately. Live authority is granted by
capability, not by lane.

Specialist overlays—security, system/backend architecture, performance, tax, and
portfolio invariants—trigger from the manifest. They never become competing mutators.
Guilfoyle may plan delivery but does not prioritise or certify acceptance.

### 10.3 Lifecycle

```text
Inbox -> Shaping -> Candidate -> Admitted -> Building -> Verifying
                                                     |          |
                                                     v          v
                                                  Blocked    Observing -> Done
                                                     |
                                                Parked/Cancelled
```

The ledger owns lifecycle and lease state; Projects displays it. Feature completion
requires an observed outcome or an honest miss, not merely a merge.

### 10.4 Git rules

1. Default each vertical slice to current `main`.
2. Stack only when the child cannot compile or satisfy its contract without the parent.
3. Default maximum stack depth is two.
4. Maximum two active implementation PRs per feature.
5. One branch and PR per slice; one mutator per node.
6. Conventional Commit intent plus `Work-Item`, `Contract-Revision`, and
   `Contract-Digest` trailers.
7. PR maps every acceptance criterion to a test/evidence item and names effects,
   overlays, observation, rollback, dependencies, and reserved actions.
8. Follow-ups are linked Issues with disposition, never prose-only review debris.
9. Squash/main SHA, runtime/workflow identity, and observation link to the same work.
10. Use SemVer only if a real public compatibility contract exists.

### 10.5 GitHub cutover and document spiral

GitHub is the attention surface; the ledger is the transactional/audit authority.
Markdown and YAML are not live work databases.

Before demoting the current queues, export and reconstruct:

- Issues, state, type, authors, labels, timestamps, and current summary;
- contract mirrors, ledger digests, authors, and permalinks;
- sub-issues and dependencies;
- Project fields and active views;
- admission/authority receipts;
- pagination/completeness metadata and schema version.

Cutover gates:

1. disposable create/read/scoped-update/read through the intended identity;
2. restore simulation reproduces James and Arbi active views;
3. three successful scheduled snapshots plus a deliberately failed alert;
4. degraded mode reads the snapshot but queues no mutations;
5. ledger/GitHub reconciliation catches deliberate divergence.

Then migrate only live items, freeze `roadmap-state.md` as historical/product-stage
reference, and remove queue semantics from `backlog.yaml`. Do not dual-write. Normal Arbi
operation creates no dated proposal or session-handoff document. Durable policy, ADR,
reference, runbook, and postmortem documents remain.

## 11. Lab, Shadow, and Live

### 11.1 Lab

Lab is designed to break safely:

- mirror product repository;
- separate Supabase Lab project, not a preview branch sharing production integrations;
- synthetic/seeded data and fake product secrets;
- separate GitHub App installations;
- separate Anthropic workspace/service account/federation rule and hard spend cap (or
  separately approved relay fallback);
- all four lanes, WIP one each;
- autonomous Issue/contract operation within Lab policy;
- self-modifying non-boundary prompts/routing under immutable holdouts;
- autonomous Lab expand/contract migrations;
- cross-context review on every change and optional cross-model comparison;
- every fence attempt, error, recovery, cost spike, and wrong decision recorded.

Fence attempts in Lab are useful evidence. A successful escape or unlogged privileged
action is disqualifying.

Supabase preview branches may still be used for per-PR migration verification, but they
are not the isolation boundary for the autonomous Lab.

### 11.2 Shadow

Controllers evaluate current real work and log what they would do without acting.
Start with:

1. classifier decisions;
2. publisher eligibility.

Add reviewer, ready, landing, workflow, migration, data, and send decisions
only after those controllers exist. Compare decisions by class with James's actual action,
including warranted escalations.

### 11.3 Live

Capabilities flip independently. A class enters Live only after its fence, tests,
promotion evidence, dependency state, fuse, recovery, and observation exist. One class
failing does not stop unrelated work unless the capability graph says the failure can
contaminate it.

## 12. Proposed Amendment M — capability authority

This section is a proposal for James to ratify. It cannot amend current I5/I6 itself.

| Capability | Proposed destination |
|---|---|
| Read/classify/deduplicate/link work | Standing after low-risk evidence |
| Transactional lifecycle/WIP projection | Standing through work controller |
| Route and dispatch admitted reversible work | Standing; Claude default executor |
| Tokenless agent-branch publication | Standing after publisher qualification |
| PR ready transition | Standing after exact-head pilot |
| Low-risk production landing | New bounded `I6-L` Live pilot |
| CI remediation outside workflow files | Eligible under `I6-L` classification |
| Supply-chain change | Separate capability; never folded into low risk |
| Workflow activation/change | Compiled templates + permission/effect diff controller |
| Additive migration | Autonomous after migration-controller qualification |
| Typed production data operation | Autonomous through named function/row-limit broker |
| Production scheduled-runtime promotion | Exact ref, health gate, observation, automatic revert |
| External application deployment | Dormant/out of scope until an actual hosting target is separately adopted |
| Contract migration | Eligible only through two-window archive-first protocol |
| Send/external communication | Fixed-recipient/schema broker after separate promotion |
| Non-boundary prompt/routing promotion | Autonomous through immutable eval gate |
| Secret value/create/rotate/bind | James |
| Controller root, signer, capability/fuse policy | James |
| Product mandate/constitution | James |
| Advice-like portfolio output | Human gate |
| Capital execution | James permanently; no controller exists |

### 12.1 `I6-L` initial eligibility

Every condition is derived from the manifest:

- no migration;
- no `.github/**` change;
- no dependency manifest, lockfile, build hook, or registry change;
- no new secret reference or external destination;
- no control/authority/policy path;
- no sensitive-table write surface;
- no user-facing portfolio render/notification or advice surface;
- no Model A relevance;
- no unresolved production reachability;
- exact tests, observation, and revert path exist.

Before a scheduled-runtime controller exists, code reachable from a production scheduled
job is excluded. The preferred unlock is to have production workflows checkout a
controller-advanced release ref/digest rather than arbitrary new `main`. Then landing and
runtime activation are separately observable capabilities.

### 12.2 Supply-chain capability

Dependency and lockfile changes require:

- hash-pinned artifacts where the ecosystem supports them;
- allowlisted registry and package identity;
- publisher/provenance and package-age policy;
- vulnerability, licence, name-confusion, and install-script checks;
- Lab bake window;
- separate promotion and fuse evidence;
- no automatic major-version update.

### 12.3 Workflow capability

Workflow changes are compiled from reviewed templates. The controller rejects unapproved
triggers, permissions, secrets, actions, shell interpolation, artifact flow, environment,
or destination changes. Full-SHA action pinning and least job permissions are mandatory.

### 12.4 Migration capability

Additive migrations promote first. Contract migration uses two moves:

1. collect production evidence of zero consumers from database/API telemetry across the
   full observation window;
2. move/copy the object to an archive schema/table with retention and copy-back metadata;
3. observe a second window;
4. drop only after the second gate;
5. recover forward through table-scoped copy-back.

PITR is disaster recovery, not routine rollback: restoring the whole database would lose
writes after the restore point. One migration PR may be open at a time.

### 12.5 Governed release controls

Replace the blanket `CLAUDE.md` feature-flag ban only if James explicitly amends it.
Eligible exposure controls apply to complete code and require owner, expiry, default,
kill path, telemetry, removal Issue, and tests of both states. They cannot conceal an
unfinished feature.

## 13. Promotion, scoring, and fuses

Promotion is per capability—not “full autonomy.” Each class pre-registers scope, false
positive/negative tolerance, evidence, recovery, dependency, cost, and revocation.

Minimum evidence:

- adversarial fixtures and positive controls;
- zero successful boundary escapes and zero unlogged actions;
- stale SHA/state, artifact substitution, contract alteration, and scope escape rejected;
- rollback or forward recovery demonstrated;
- independent-context evaluation;
- cost and intervention telemetry;
- approximately 20 audited decisions may open a narrow low-risk pilot;
- a strong claim of a sub-5% unseen failure rate needs roughly 60 zero-failure eligible
  actions rather than 20;
- higher-risk capabilities run scheduled Live game days through the real queue.

Scoring:

- warranted escalation scores positively;
- only unwarranted escalation counts against autonomy;
- silence is not success;
- measure interventions per accepted outcome, not hours or tokens;
- cross-model disagreement is evidence, not a veto;
- weekly pre-traffic sample: James audits five accepted outcomes, counted as intervention;
- do not reward raw task, PR, agent, or token volume.

Fuse levels:

1. **Local:** suspend one capability after its failure budget is exceeded.
2. **Dependent:** repeated local trips within a window suspend dependent capabilities.
3. **Global:** successful hard-boundary escape, credential exposure, unlogged privileged
   action, signer/publisher integrity failure, advice/capital breach, or Model A breach.

James resets fuses. Reset is logged as an intervention. Revert is a new PR through the
landing controller; no in-place cross-lane rollback.

## 14. Action settings and runtime prerequisites

Before the first autonomous candidate:

- verify repository visibility/account plan and protection support;
- require read-only default `GITHUB_TOKEN` permissions;
- use `permissions: {}` at workflow level and explicit minimal job grants;
- restrict allowed actions to the smallest GitHub/control allowlist;
- require or mechanically validate full-SHA action pinning;
- disable action approval and PR-review permissions on default tokens;
- verify required checks bind to the control App identity where supported;
- inventory every product-repository Actions secret/variable and every workflow that can
  receive it from a branch event;
- move production/broker secrets to control-owned environments/functions;
- inventory every workload using `service_role` and replace it;
- inventory external-network tests and convert them to fixtures/fetch artifacts;
- confirm production scheduled jobs' checkout/ref behaviour;
- confirm Supabase backup/log/`pg_stat_statements` retention needed for migration evidence;
- start nightly GitHub Events-to-ledger reconciliation, acknowledging the Events API
  retention limit until an organisation audit log is available.

## 15. Implementation programme

Sequence by fence readiness. Tracks A and C start together; the control-plane interface
lands as soon as the Phase-1 contract substrate exists.

### Phase 0 — ratification and measured baseline

1. Run a repo-connected Claude final verification against current `origin/main`, live
   GitHub settings, and Supabase settings.
2. Resolve every verified blocker in this plan; mark false premises as such rather than
   retaining them as folklore.
3. James ratifies/rejects Amendment M by capability and records the standing mandate.
4. Start intervention-per-accepted-outcome and cost baselines immediately.
5. Record current secrets, Apps, Actions settings, branch rules, scheduled runtime paths,
   service-role use, and state/queue drift.

**Exit:** one authoritative ruling identifies which capabilities may be built and piloted;
the baseline is derived; no execution permission is inferred from this proposal.

### Phase 1 — root of trust, tokenless publication, and Lab

Critical graph:

```text
P0 verify account/settings/runtime exposure
 ├─ P1 harden product Actions settings
 ├─ P2 create/protect asxos-control
 ├─ P3 create separate control Apps
 ├─ P4 create append-only ledger + minimal contract
 ├─ P5 create webhook/polling admission path
 ├─ P6 prove Anthropic workload federation (relay only as fallback)
 │    └─ P7 tokenless Claude patch producer
 ├─ P8 offline exact-SHA verifier + fixtures
 │    └─ P9 OIDC-bound signer + App-owned check
 │         └─ P10 leased deterministic publisher
 └─ P11 isolated Lab repo/project/Apps/API keys
P12 baseline runs throughout
```

Phase-1 publication exit:

1. an admitted immutable contract is read from the ledger;
2. Claude receives exact source without a write/product credential;
3. Claude produces a patch without executing product code;
4. product code is verified offline;
5. signer rejects evidence from an untrusted workflow/run;
6. publisher independently derives paths/effects and writes only an allowed branch at the
   leased base;
7. forged evidence, changed acceptance, stale base, protected paths, symlinks, unexpected
   binaries, oversize artifacts, and network attempts fail;
8. an artifact substitution between verification and publication fails;
9. the run completes without Cursor or Codex.

### Phase 2 — classification, landing, recovery, and Shadow

- complete production-effect/reachability classifier;
- build deterministic review bundle;
- add independent-context reviewer;
- build ready and landing controllers with exact-head leases;
- build revert-through-queue and post-merge observation;
- make the landing broker the only autonomous landing mechanism;
- start classifier and publisher-eligibility Shadow recording;
- establish per-capability evidence counters and spend fuses.

**Exit:** stale SHA, spoofed check, altered artifact/contract, protected path, ambiguous
risk, lease race, duplicate action, and failing recovery drill are rejected.

### Phase 3 — GitHub work interface and D10 cutover

- add Issue forms and Project fields as projections of canonical ownership;
- implement full contract revision workflow and asymmetric revision rules;
- implement transactional lifecycle/WIP/leases in the ledger;
- implement projection and reconciliation;
- prove export, view reconstruction, failure alerts, and degraded read-only mode;
- migrate only live work;
- demote Markdown/YAML queues in reversible PRs;
- refactor Arbi wake to delta, exceptions, commitments, decisions, and observations.

**Exit:** a pilot runs from intake to observation without a roadmap row, backlog row,
dated plan, or session handoff as live state.

### Phase 4 — first Live capabilities

Promote independently:

1. classify/route/link work;
2. lifecycle/WIP projection;
3. tokenless branch publication;
4. routine secretless CI remediation;
5. PR ready transition;
6. bounded `I6-L` landing;
7. production-ref promotion and automatic revert.

**Exit:** a complete low-risk slice moves from admitted contract to observed production
outcome without James clicks, while every decision and effect is recoverable.

### Phase 5 — production brokers

Order by value per engineering hour and containment:

1. eliminate `service_role` from workloads;
2. per-workload read roles;
3. sensitive writes through constrained functions;
4. public-data fetch broker;
5. workflow template/activation controller;
6. additive migration controller;
7. scheduled-runtime controller expansion;
8. typed data-operation broker;
9. fixed-recipient send broker;
10. archive-first contract migration controller.

Each flips when its own fence and evidence pass; later brokers do not delay earlier safe
capabilities.

### Phase 6 — autonomy optimisation

- promote non-boundary prompts/routing through immutable holdouts;
- measure where specialist, fresh-context, and cross-model review changes outcomes;
- remove review ceremony with no measured value;
- use Cursor/Codex only where they improve quality, capacity, or recovery;
- expand Arbi's control scope without exposing secrets or capital execution;
- continuously reduce James interventions per accepted outcome.

## 16. First Lab work — one item per lane

The programme creates these as contracts after Phase-1 admission exists; these are not a
parallel queue:

| Lane | First Lab outcome |
|---|---|
| Strategic feature | Run one small non-migration product slice through contract -> Claude patch -> verify -> publish -> Lab observation |
| Reliability | Prove stale-SHA, artifact substitution, forged evidence, and dependency-fuse rejection with positive-control attacks |
| Maintenance | Inventory/pin Actions and convert one network-dependent test group to offline fixtures |
| Exploration | Compare fresh-Claude versus optional Cursor/Codex review on the same frozen bundle; measure unique valid findings and cost |

## 17. Metrics

| Outcome | Measure |
|---|---|
| Founder leverage | Interventions per accepted outcome, by capability |
| Escalation quality | Warranted and unwarranted escalation rates separately |
| Delivery | Admitted-to-merged and admitted-to-observed lead time |
| Reliability | Change failure rate and MTTR |
| Safety | Attempted and successful boundary violations; Live success must be zero |
| Landing truth | Exact-head/check/contract mismatches rejected |
| Queue truth | Active work represented in one canonical state model |
| WIP/stack | One per lane; <=2 implementation PRs per feature; stack <=2 |
| Closure | Observation overdue rate and honest-miss rate |
| Recovery | Revert/forward-recovery game-day pass rate |
| Cost | Model/tool/control cost per accepted outcome and per lane |
| Review value | Unique valid findings and prevented failures per review type |
| Automation health | Fires, nothing-cycles, deadman alerts, fuse trips, unlogged mutations |
| Runtime truth | Main, release, workflow, runtime, and observation identity coverage |

## 18. Prioritised risk register

| ID | Description | Likelihood | Impact | Level | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-ACP-01 | Model can use a GitHub/product credential | Medium | High | High | Tokenless producer; control-owned publisher; product secret evacuation | Control plane | Open |
| R-ACP-02 | Repository code exfiltrates a secret | Medium | High | High | Separate job, `--network none`, zero secrets/socket | Control plane | Open |
| R-ACP-03 | Provider identity bootstrap is unavailable, over-broad, or exposes a reusable key | Medium | High | High | Prove Anthropic WIF claim binding first; short lifetime and spend cap; reviewed provider-specific relay only as fallback | Control plane/James | Open |
| R-ACP-04 | Signer accepts forged verifier evidence | Medium | High | High | Immutable control workflow identity, OIDC/nonce/run binding, App-owned check | Control plane | Open |
| R-ACP-05 | Broker becomes a confused deputy | Medium | High | High | Typed fixed operations, schema/digest validation, limits, no product execution | Broker owner | Open |
| R-ACP-06 | Classifier misses production reachability | Medium | High | High | Derived graph, adversarial fixtures, fail-closed highest class | Classifier owner | Open |
| R-ACP-07 | Builder weakens acceptance | Medium | High | High | Ledger contract, separate identity, asymmetric capped revisions | Arbi/controller | Open |
| R-ACP-08 | Controller self-review corrupts root of trust | Low | High | Medium | James merges Phase 1; immutable consumed control digest | James | Open |
| R-ACP-09 | State race dispatches stale work | Medium | High | High | Postgres CAS, leases, serialization, projection after commit | Control plane | Open |
| R-ACP-10 | Landing silently activates scheduled production code | Medium | High | High | Reachability exclusion then controller-advanced production ref | Runtime controller | Open |
| R-ACP-11 | Autonomous dependency bump imports malicious code | Medium | High | High | Separate supply-chain class, hashes, provenance, bake, fuse | Supply-chain controller | Open |
| R-ACP-12 | Contract migration loses later writes on rollback | Low | High | Medium | Archive-first forward recovery; PITR not routine rollback | Migration controller | Open |
| R-ACP-13 | Lab reaches Live resources or exhausts Live quota | Medium | High | High | Separate project, Apps, keys, caps, environment-bound evidence | James/control plane | Open |
| R-ACP-14 | GitHub projection is mistaken for transactional truth | Medium | Medium | Medium | Ledger canonical, reconciler, divergence cannot authorize | Arbi/controller | Open |
| R-ACP-15 | Review depends on Cursor/Codex availability | Low | Medium | Low | Fresh Claude context satisfies required review; others optional | Arbi | Mitigated by design |
| R-ACP-16 | Advice/capital or Model A boundary is crossed | Low | High | Medium | Path/semantic gates, no capital broker, global fuse | James/control plane | Open |
| R-ACP-17 | GitHub-hosted container isolation is overstated | Low | High | Medium | No production secrets in untrusted jobs; record container-escape residual | Control plane | Accepted residual |
| R-ACP-18 | Event history is incomplete on personal account | Medium | Medium | Medium | Nightly Events-to-ledger snapshot; revisit organisation audit log | Control plane | Open |
| R-ACP-19 | Automation creates cost or retry loop | Medium | Medium | Medium | Per-lane/month caps, idempotency, escalating fuses | Arbi/control plane | Open |
| R-ACP-20 | Markdown/YAML becomes a competing queue again | High | Medium | High | Recovery-complete cutover, generated exports, no dual-write | Arbi | Open |

## 19. Red-team disposition folded into this plan

The final external red team ran without repository access and returned ten blockers. The
disposition is part of the audit trail:

| Finding | Disposition in this plan |
|---|---|
| B1 model workspace cannot use `--network none` | Accepted; model and verifier sandboxes split; Anthropic WIF preferred, constrained relay retained only as fallback |
| B2 reusable brokers cannot use called-repo secrets | Accepted; execution originates in `asxos-control`; product repo has no broker secret |
| B3 verifier evidence can be forged by product workflow | Accepted; protected control workflow, signed ledger evidence, App-owned check |
| B4 Actions settings unhardened | Accepted as live preflight; hardening is Phase 0/1 prerequisite |
| B5 native merge queue/account limitations | Partly accepted; custom landing broker mandatory; account protection support re-probed |
| B6 contract mutable and sequenced too late | Accepted; append-only minimal contract moved to Phase 1 |
| B7 merge equals Render/Vercel deploy | Premise rejected as stale; underlying GitHub scheduled-runtime coupling accepted and controlled |
| B8 dependencies misclassified low-risk | Accepted; separate supply-chain capability |
| B9 GitHub has no CAS state transition | Accepted; Postgres ledger is transaction authority, GitHub projection only |
| B10 unavailable second provider must escalate | Rejected; contradicts settled non-dependency rule; fresh-context review + deterministic gates remain mandatory |

Non-blocking residuals retained:

- same-provider semantic correlation;
- injection in previously merged code comments presented to a reviewer;
- container escape in an ephemeral secretless job;
- GitHub Events retention/audit limitations;
- transient database telemetry and log-retention gaps;
- semantic advice classification;
- migration-lane serialization;
- provider/control platform outage.

These are observed, tested, and revisited. None is hidden by claiming a stronger boundary
than the platform provides.

## 20. Phase-0 final verification checklist

Claude must perform this in a fresh repo-connected review context before implementation:

- [ ] Current `origin/main`, open PRs/Issues, branch rules, repository visibility, plan
      tier, Actions permissions, allowed-actions policy, and SHA-pin enforcement re-probed.
- [ ] Current product Actions secrets/variables and every branch-triggered workflow
      enumerated without exposing values.
- [ ] Current scheduled jobs and production checkout/ref reachability mapped.
- [ ] No obsolete Render/Vercel assumption used.
- [ ] Anthropic WIF is available to James's tenant and its exact control-workflow claims,
      lifetime, revocation, spend cap, and producer compatibility are proven; otherwise
      the constrained relay fallback is separately threat-modelled.
- [ ] Cross-repo trigger requires no product credential; polling/webhook path threat-modelled.
- [ ] Control App can post an identity-bound required check supported by branch rules.
- [ ] OIDC claims available in the chosen control job are captured and negative-tested.
- [ ] Control ledger separate-org/project, backup, append-only, signer, and clock assumptions
      verified.
- [ ] Lab has a separate project/integrations/Apps and Anthropic
      workspace/service-account/federation rule with a hard spend cap.
- [ ] Model A production-gate enforcement re-tested; classifier exclusion added, not
      substituted for the existing gate.
- [ ] Personal-advice paths and scheduled-runtime roots enumerated.
- [ ] External-network tests and local-Postgres feasibility inventoried.
- [ ] Amendment M text names every changed current authority clause and enforcement point.

**Verdict format:** `READY` or `NOT READY`; concrete blockers only. A conservative
preference is not a blocker. Every blocker needs a failure sequence, current evidence,
smallest structural correction, and the phase/capability it blocks.

## 21. Execution handoff after READY + ratification

```text
Implement the ratified parts of
docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md.

Read current CLAUDE.md, docs/product/harness-profiles.md, newest merged session
handoff, arbi authority/permission/autonomy/eval/risk documents, the live
Amendment M ruling, and this plan. Re-probe origin/main and GitHub/Supabase state.

Claude is the primary execution layer. Cursor and Codex are optional secondary
capacity and must never be required for liveness. Arbi owns control-plane
priority/routing; one model mutator owns each implementation node; deterministic
controllers own privileged effects.

Execute Phase 0 first. Do not implement a component whose live preflight is
unverified. Then execute Phase 1 in the dependency order shown, with Track A
(fence) and Track C (Lab/evaluation) progressing together. Use one programme
Issue and sub-issues for implementation; do not create another roadmap, backlog,
dated proposal, or session-handoff system.

This plan grants no authority. Current I5/I6/P5/P6 and rule #11 remain binding
except where the live James-ratified Amendment M explicitly and mechanically
changes an action class. No raw secret enters a model process. No product code
runs in a secret-bearing job. No product-repo workflow supplies the trusted
verification definition. No builder controls acceptance or risk routing.

Stop at a named gate for a missing James secret binding, root-of-trust merge,
constitutional decision, capital/advice action, or a live platform fact that
invalidates the design. Do not route around a hook, weaken a test, substitute a
self-report for CI evidence, or turn an unresolved finding into prose acceptance.

Return first with: live-state delta, Amendment M authority diff, Phase-1 task
graph, control App permission matrix, credential migration inventory (names and
scopes only), provider-identity feasibility verdict, and exact first two draft-PR
boundaries. Begin mutation only after those are internally consistent.
```

## 22. Success definition

The programme is complete when:

- Arbi owns one truthful portfolio and founder decision desk;
- Claude executes the normal delivery lifecycle without depending on Cursor or Codex;
- James sees bets, secret bindings, constitutional changes, fuse resets, capital, and
  genuine exceptions rather than routine delivery;
- low-risk production changes move from admitted contract to observed outcome without a
  founder click;
- production capabilities activate independently behind enforced limits and recovery;
- every privileged action binds to a controller, contract, artifact, exact SHA, ledger
  event, observation, and rollback/forward-recovery path;
- no model holds a product production credential;
- no live work state is duplicated in Markdown or YAML;
- code throughput rises without hiding change failures, MTTR, cost, or escalations;
- advice-like output and capital execution remain human-gated;
- Model A remains quarantined until an entirely new model meets the pre-registered bar.

The desired outcome is not an agent that asks less because it has learned to stay quiet.
It is an operating system where the safe autonomous path is the easiest path, dangerous
actions are mechanically bounded, and James's attention is spent only where judgment is
actually irreplaceable.

## 23. ECC-informed harness optimisation delta — 2026-09-08

**Status:** execution delta under this programme; not a second roadmap and not authority.
**Delta baseline:** `origin/main` at `6f59b8e`, re-probed 2026-09-08.
**External reference:** [ECC](https://github.com/affaan-m/ECC), inspected as a design source;
no ECC package or catalogue is adopted.
**Placement:** implementation remains in programme Issue `#204`, Phase-0 Issue `#205`, and
the existing work orders below. Create no parallel Markdown/YAML queue for this delta.
**Sibling policy PR:** draft PR `#235` starts from the same `6f59b8e` baseline and changes
`AGENTS.md`, `docs/README.md`, and `docs/product/autonomy-policy.md`; it does not overlap this
file. Its target contract is inactive unless and until its 17 activation gates, policy attestation,
and `AUTONOMY=STANDING` state all pass.

### 23.1 Placement and decision

Adopt ECC's strongest operating mechanisms as increments to ASXOS's existing control plane:

```text
diagnose -> select bounded context -> execute behind runtime feedback guards
         -> verify outside the product PR -> emit receipts -> evaluate on protected cases
```

This does not displace the admitted F-E2E r1 sprint. At this baseline its negative control is
observed and the positive control is one James-authored thesis away
(`e2e-run-findings-2026-09-07.md`). Finish that r1 unless James explicitly reprioritises. ACP
Phase 0 stays under `#205`; control implementation stays under `#204`. Backlog `A-22` is the
separate branch-scoped producer-credential gate for standing lanes: removing PR-head secrets does
not close it.

The decision is **adapt, not install**. Do not add ECC's 286-skill catalogue, installer/repair
lifecycle, broad MCP defaults, `yolo` profile, transcript-derived memory, IOC feeds, or a second
state store. This delta does not itself change ASXOS's command vocabulary, authority, activation
state, no-auto-merge rule, rule #11, or s766B firewall. The current attended/draft-PR ceiling holds
until the separate target policy in `#235` is both merged and fully activated; after that, its
mechanical Green/Amber/Red classifier and exact-head approval rules govern execution.

PR `#235` is complementary, not a prerequisite for merging this planning delta and not a second
implementation track. If it lands, its activation checklist becomes the parent control contract:

- `P2/P8/P9` implement its `asxos-control` verifier, separated publisher identity, and exact-head
  `risk-classify` required check; do not create a second verifier or required-status vocabulary;
- `P1`, CODEOWNERS drift control, the external check, and the identity proof contribute evidence
  to its activation items 1–7 rather than constituting an alternative activation path;
- a future Codex `ADOPT` must add `.codex/**` to its protected policy/classifier surfaces through a
  James-approved policy change, because `#235` does not currently classify that path; and
- none of this delta's PRs, receipts, or pilots may set `AUTONOMY`, satisfy an unchecked activation
  item by assertion, or infer standing authority from `#235` merely being merged.

### 23.2 Canonical crosswalk

| ECC-derived mechanism | Existing ASXOS destination | Baseline | Next increment |
|---|---|---|---|
| Doctor / drift diagnosis | ACP Phase 0 and `P12` measurement | Project-state, workflow, offline-test, and doc-expiry checks exist separately | One new read-only doctor candidate; create one `#204` sub-issue only if James activates it |
| External verification | ACP `P1`, `P2`, `P8`, `P9`; Issues `#204/#205` | Exact-SHA verifier and caller are staged under `docs/proposals/asxos-control/`; destination repo absent | Treat staged files as the `P8` seed; if `#235` lands, implement its single `risk-classify` verifier/publisher contract as `P9` rather than creating a parallel check |
| Context budget | Existing `SB3-02` and ACP `P12` | `MissionEnvelope`, `MissionReceipt`, and `ContextManifest` v1 are frozen; no compiler exists | Compile/verify manifests and emit a report-only budget without widening v1 |
| Codex roles/config | This plan's optional-provider rule and `R-ACP-15` | At this baseline root `AGENTS.md` is a prompt-only Cursor mirror and `.codex/**` does not exist; draft `#235` proposes native Codex policy wording but no `.codex/**` classification | Required capability proof, then explicit `ADOPT` or `REJECT`; adapter remains optional and never gates liveness |
| Executable evals/receipts | Existing `SB4-01`, `SB4-02`, backlog `E-10`, ACP Lab/control | Five visible Markdown cases exist; real brief trigger and score trend are open | Protect public regression cases; keep withheld cases in control; build deterministic runner and the already-planned SB4-02 eval receipt |
| More hooks | No active work order | Four Claude hooks already exist; current lesson is hooks = feedback, controllers = enforcement | Defer until at least ten receipts show the same preventable miss |

This crosswalk is the work identity. The only genuinely new candidate is the doctor. Give it a
canonical work-item ID only when James activates a `#204` sub-issue; do not pre-create another
ID family here.

### 23.3 Dependency overlay on the existing programme

```text
current F-E2E r1 -> observed or explicitly reprioritised by James

#205 / P0 fresh baseline
├── P1 harden product Actions settings and contain PR-head exposure
├── P2 create/protect asxos-control
│   └── P8 exact-SHA secretless verifier
│       └── P9 OIDC-bound signer + App-owned required check
├── SB3-02 manifest compiler + report-only context budget
├── Codex capability proof
│   └── fence .codex/** [James, only on ADOPT]
│       └── minimal adapter trial [optional]
└── SB4-01 real-case trigger + public regression runner
    └── SB4-02 separate-context eval receipt
        └── protected control execution using withheld cases [after P9]

P8 + P9 + SB3-02 + SB4-02 + Codex ADOPT/REJECT disposition
└── one low-risk observed pilot
```

The staged verifier alone is not the root of trust. `P8` proves secretless exact-SHA execution;
`P9` binds that evidence to an identity a product PR cannot forge and publishes the required
check. Product-side workflow inventories remain diagnostics: the protected controller owns the
parser and policy used for enforcement and never trusts a parser or green result supplied by the
PR being judged.

If `#235` lands, its 17-item activation checklist is the overarching dependency graph. The ACP
work above supplies part of that checklist's evidence; it does not replace the distinct identity,
ruleset, CODEOWNERS, environment, database-role, state-controller, breaker, restore, digest, drill,
and attestation gates that remain open there.

Read-only doctor and Codex capability probes may run while James progresses `P2`. A Codex adapter
cannot be called in-fence until the external check is observed and `.codex/**` is classified as
authority. `SB4-01` remains parked until its existing trigger — one real `/arbi` brief — exists.

### 23.4 Execution contracts

#### Read-only harness doctor — new candidate under `#204`

Build one standard-library bootstrap that composes existing checks rather than reimplementing
them. Proposed product paths: `tools/harness_doctor.py`, `tests/test_harness_doctor.py`, one short
operator runbook, and optionally a `Makefile` target.

Its record is stable JSON with a human rendering from the same data. Findings are
`PASS | WARN | FAIL | UNAVAILABLE`, each with owner, evidence, and remedy. Exit `0` means no
`FAIL`, `1` means at least one `FAIL`, and `2` means bad invocation or an internal doctor defect.
`--strict` may make warnings non-zero. It never installs, repairs, trusts a hook, reads a secret
value, contacts the network, or becomes a source of truth.

Required probes: repository identity/dirty state; Python/dependency readiness; tracked config and
hook presence/digests; effective git-hook path; live-versus-staged fence version; project-state
validity/freshness; workflow effects/exposure; offline-test surface; and external-control state as
`observed`, `staged`, or `unavailable`. The inspected host's default `python3` cannot import
`datetime.UTC` while ASXOS targets Python 3.12; the doctor must report that cleanly before project
imports, not reproduce the current traceback.

Do not make `check_doc_expiry.sh` blocking through the doctor. Four James-owned paths remain and
the last sweep needed 19 standing-doc allowlist entries, so its rule still has calibration debt.

#### `P1` / `P2` / `P8` / `P9` — external root of trust

Move the staged verifier into the protected control repository, build its dependency image, and
replace both placeholders with an immutable control-workflow commit and image digest. Preserve its
network namespace, non-root user, read-only root filesystem, dropped capabilities, no Docker
socket, DNS-negative test, raw-IP TCP-negative test, and no-secrets reusable-workflow contract.

`P1` must ultimately leave zero repository-secret-bearing PR-head workflows. The current two are
`migration-drift.yml` and `pr-review-agent.yml`. A secret-powered job may move to protected control
code, become owner-only/manual, or run trusted code with PR content treated as data. Do not solve
this by switching casually to `pull_request_target` and checking out the PR head. If replacement
is not ready, safe rollback is manual/secretless operation, never the exposed state.

`P9` is complete only when an App-owned, identity-bound required check is observed at the exact
product SHA and rejects forged evidence, stale SHA, changed acceptance, artifact substitution,
mutable actions/images, widened permissions/triggers, local composite actions, Docker tags,
`secrets: inherit`, secret context dumps/bracket access, `workflow_run` confusion, and
self-referential path filters.

#### `SB3-02` — manifest compiler and report-only context budget

Consume the existing `MissionEnvelope v1`; emit and verify the existing `ContextManifest v1`.
Resolve selected files at `baseline_sha`, enforce repository containment, compare SHA-256 digests,
validate line spans and snapshot links, and fail closed on stale/unreachable baselines, sensitive
dotfiles, unresolved compiled views, or broad scope globs. Do not add fields to a frozen v1.

Emit a sidecar record of exact bytes and lines by source kind, always-loaded instruction bytes,
selected/excluded totals, and a clearly labelled token estimate. Start report-only. The full
roadmap, all handoffs, all memory, and whole directories are not default context. Consider a
blocking ceiling only after at least ten representative runs across docs, code, review, and live-
probe missions, with no regression in safety, citation, or dispatch quality.

`ContextManifest` remains an auditable declaration. It does not prove the runtime read nothing
else and must not be described as an enforcement boundary.

#### Codex capability proof and optional adapter

The capability proof is required; adapter adoption is not. It must end in an evidence-backed
`ADOPT` or `REJECT`. `REJECT` is a complete outcome: Claude remains primary, Codex remains
read-only/out-of-fence, and the programme remains live.

Current official OpenAI documentation confirms project-scoped
[`config.toml`](https://learn.chatgpt.com/docs/config-file/config-basic),
[`agents`](https://learn.chatgpt.com/docs/agent-configuration/subagents), and
[`PreToolUse` hooks](https://learn.chatgpt.com/docs/hooks). It also states that CLI overrides outrank
project config, changed hooks require trust review, and some tool paths can escape hooks. Re-check
those facts at implementation time.

On `ADOPT`, James first classifies `.codex/**` in every applicable surface:

- `AGENTS.md` and, if `#235` lands, `docs/product/autonomy-policy.md`;
- `.claude/settings.json` primary path denies;
- `.claude/hooks/authority-guard.sh` attended authority fragments;
- `.claude/hooks/unattended-guard.sh` unattended authority paths;
- `asxos/backlog.py` protected exact/prefix sets;
- `.github/CODEOWNERS` and the protected `asxos-control` classifier registry; and
- `tests/test_authority_fence_drift.py`, `tests/test_authority_guard_hook.py`,
  `tests/test_unattended_guard_secperf.py`, and backlog drift tests.

Only after that fence is observed may the adapter land: project defaults
`approval_policy = "on-request"`, `sandbox_mode = "workspace-write"`, maximum four concurrent
subagent threads, one read-only explorer, one read-only reviewer, and one payload normalizer that
feeds Bash, `apply_patch`, and supported MCP calls into the existing ASXOS policy scripts. Add no
pinned model, default MCP server, secret, global path, permissive profile, or write-capable
specialist. Update `AGENTS.md`'s Cursor-only wording only after the capability proof.

The normalizer must not fork the authority vocabulary. Synthetic Bash, patch, MCP, push, merge,
ready, authority-path, symlink, missing-`jq`, and subdirectory-start cases must produce the same
decision in Claude and Codex adapters. Hook trust missing/changed, CLI bypass, or a parity miss
keeps Codex out-of-fence. The external required check remains enforcement even after `ADOPT`.

#### `SB4-01` / `SB4-02` — regression cases, hidden holdouts, and eval receipts

The five files under `docs/product/evals/**` are visible to the candidate. Treat them as a public
regression set, not genuine hidden holdouts, and protect them from candidate edits through the
same explicit authority surfaces above. Add structured G1–G8 cases, including a real `/arbi`
failure shape only after stripping live numbers, holdings, stops, targets, personal data, and
credentials. A captured real case becomes public regression evidence after use; it is not a
continuing holdout.

Withheld cases and their exact expected answers live only in protected `asxos-control`, where the
product candidate cannot read or modify them. The public offline runner consumes pre-captured
outputs and exercises deterministic hard gates without model credentials or production access.
Known-bad Model A, branch-only, unavailable-probe, capital-request, and boundary cases must fail.
Fixtures never supply arbitrary shell for the runner to invoke.

Implement the already-planned SB4-02 scorecard receipt as a distinct versioned contract; do not
replace or widen `MissionReceipt v1`. Separate two identities:

- `evaluation_content_digest` is stable over candidate/incumbent, cases, instructions, runner,
  policy, deterministic gate outputs, output/evidence digests, and grader-policy digests; and
- `run_id` is unique and carries timestamp, duration, observed usage/cost, and grader observation.

Unknown cost is `unavailable`, never zero. Deterministic replay applies to the hard-gate results
and content digest, not to a qualitative grader's prose. Producer and grader run in separate
contexts. The committed product record is the small receipt and James's
promote/reject/no-change decision, not hidden cases or a raw transcript.

#### Conditional feedback hook

Create no new hook now. After at least ten receipts, a repeated miss may justify a shadow
experiment such as a compact session-start fact pack or a quality-config warning. Its proposal
must name the observed denominator, expected catch rate, false-positive ceiling, added context and
latency, owner, removal rule, and no-regression eval. Delete it if the shadow evidence does not
justify a blocking control.

### 23.5 Evidence matrix

Each activated mission copies its applicable row into `MissionEnvelope.acceptance_checks` before
mutation. Future command names below are interface contracts to implement and test.

| Criterion | Command / test | Artifact | Observer |
|---|---|---|---|
| Fresh setup baseline | `git rev-parse origin/main`; `python tools/harness_doctor.py --format json` | Redacted doctor JSON bound to full SHA | Guilfoyle + security review |
| Doctor survives incomplete setup | system Python run plus `pytest tests/test_harness_doctor.py` | Clean findings for old/missing Python, dependencies, tools, stale state, malformed child output | CI and technical writer |
| No PR-head secret exposure | `python tools/workflow_inventory.py --format json` plus control-owned policy suite | Product diagnostic + protected control verdict, both at exact SHA | Security + James |
| Exact-SHA control check | control attack suite; GitHub check-runs query for tested SHA | `P8` verifier evidence and `P9` App-owned required check | James + branch rules |
| Manifest integrity/budget | `pytest tests/test_mission_context_schema.py` plus new SB3-02 targeted tests and compiler CLI | `ContextManifest v1` + budget sidecar | Guilfoyle + security/performance |
| Codex disposition | adapter validation tests plus recorded instruction/config/hook discovery smoke run | `ADOPT` or `REJECT`, effective sources, parity matrix, context/latency/cost | James + independent reviewer |
| Public eval replay | `python scripts/run_arbi_evals.py` plus known-bad fixtures | Deterministic hard-gate result + content digest | CI + fresh reviewer |
| Hidden comparison | protected control execution against withheld cases | Unique run receipt linked to stable digest; no hidden input in product artifact | App-owned check + James |
| End-to-end outcome | one low-risk mission through envelope -> manifest -> draft PR -> receipts -> exact-SHA check -> observation | `MissionReceipt v1`, eval receipt, observed/honest-miss row | Guilfoyle, external check, James |

### 23.6 PR boundaries and rollback

Use the existing programme Issue and work-order identities:

1. **Doctor candidate, one product PR after activation:** doctor, fixtures, and runbook; draft PR
   ceiling; rollback is branch revert.
2. **`SB3-02`, one product PR:** compiler, verifier, budget record, and targeted tests; report-only;
   rollback retains the frozen schemas.
3. **`P1/P2/P8/P9`, separated by repository boundary:** protected control bootstrap/verifier;
   control policy/signer; then James-applied product caller and secret evacuation. Never stack
   ambiguous trust changes across repositories.
4. **Codex experiment:** capability report first. On `REJECT`, no config PR. On `ADOPT`, one
   James-owned boundary PR precedes one minimal-adapter PR; removing the adapter retains the
   `.codex/**` authority classification.
5. **`SB4-01/SB4-02`, at most two product PRs plus protected control integration:** public
   regression/receipt contract, then offline runner; control-owned hidden execution follows `P9`.
6. **Pilot, one low-risk product PR:** if Codex was rejected, run through Claude only; if adopted,
   compare the same frozen mission through both without making Codex a liveness dependency.

While the pre-activation attended ceiling holds, no product branch starts from a stale base,
becomes ready, merges, or pushes to `main` through an agent. This delta grants no exception. If the
policy proposed by `#235` is later fully activated, branch readiness and merge follow its external
classifier, exact-head evidence, and Green/Amber/Red gates; Red, secrets, capital, protection
bypass, policy self-amendment, and destructive production data remain hard stops. Rollback must
always return to an attested safe state, never the former exposed state.

### 23.7 Completion bar

This delta is complete when:

- the doctor emits deterministic, redacted findings from both a clean and deliberately incomplete
  checkout without mutation or traceback;
- product PR-head workflows receive zero repository secrets;
- the required verification status is published only by protected, pinned `asxos-control` code
  through the `P9` identity at the exact product SHA;
- `SB3-02` produces contained, digest-bound, baseline-bound manifests and measures exact context
  bytes separately from estimated tokens over at least ten representative runs;
- Codex has an explicit `ADOPT` or `REJECT` disposition; an adopted adapter passes the boundary
  parity corpus, while a rejected adapter leaves Claude as the healthy primary path;
- public regression cases are protected, hidden cases remain external, a known-bad candidate
  fails, producer and grader differ, and one real candidate/incumbent decision has a replayable
  SB4-02 receipt;
- one low-risk mission reaches exact envelope -> minimal context -> draft PR -> receipts ->
  external verification -> observed outcome or an honest miss; and
- no new authority, production DB, migration, deploy, automatic merge, capital, Model A, or
  secret-handling capability is granted.

Do not claim completion because files merged, CI was green, Codex started, context bytes fell, or a
qualitative grader returned a higher scalar score.

### 23.8 Recommended activation

Default order:

1. finish F-E2E r1's current observed contract unless James explicitly reprioritises;
2. complete the fresh Phase-0 verdict under `#205`;
3. if ratified, create exactly one new `#204` sub-issue for the read-only doctor and make it the
   first agent-owned harness mission; and
4. in parallel, James advances `P2` creation/protection of `asxos-control`, then `P8 -> P9`.

Next after the doctor is the existing `SB3-02` work order. Codex configuration waits for an
`ADOPT` disposition and its authority fence. Automated promotion waits for protected public cases,
external hidden cases, and `P9`. `A-22` remains open until its separate branch-scoped credential
proof is observed. PR `#235` may land as an inactive target contract in either order; once landed,
record each of these work products against its activation checklist and do not set
`AUTONOMY=STANDING` until all 17 items—not only the overlapping ACP subset—are independently
verified and attested.
