# Session handoff — 2026-09-07 (governor-named work, no `/arbi` wake)

**Session shape:** in-fence (repo hooks loaded and exercised — every write target probed through
`authority-guard.sh` before use). No `/arbi` wake: James named the work directly, so there is no
arbi-ranked "one thing" for this session to be scored against. Ledger row `close-2026-09-07`
(3.8 provisional).

Every figure below is **measured** with the command shown, or marked *inferred*. That convention
was adopted mid-session at James's instruction after a wrong inference reached him (see Lessons).

## STOP — read this first: Model A's quarantine (rule #11) stands, untouched

Nothing this session read `signals`, `model_versions`, or any Model A artefact. Both PRs are test
and tooling infrastructure. Rule #11 is standing policy, not up for reinterpretation.

## What this session was

One governor-named mission — *make the product test suite ready for the secretless offline
verifier* (ACP §5.4's Phase-1 clause) — which shipped, plus a follow-on that came out of it, plus
one proposal James rejected on architectural grounds.

**Merged (both by James):**

| PR | Merged | What |
|---|---|---|
| **#209** `e058be3` | 09-06 11:29 UTC | Secretless offline test boundary |
| **#211** `fd6172c` | 09-07 04:26 UTC | Three measured fence gaps closed (staged), PR-head exposure inventory |

**Withdrawn:** a scoped `.github/**` unfence (Option B, then "B-hardened"). James rejected both.
Recorded below because the reasoning is the reusable part.

### #209 — the offline boundary

The ACP clause required identifying tests that call live endpoints and converting them to
fixtures before a trusted verifier can run product tests.

**Audit result: zero conversions needed.** No test in the suite reaches a live endpoint — `httpx`
is patched at the consuming module path in all six modules that touch it, `resend` is stubbed into
`sys.modules`, and `asxos/db.py:51` raising on an uninitialised pool is an effective backstop. The
deliverable was therefore *enforcement*, not conversion: 14 modules asserted "no network" in prose
with nothing mechanising it.

What shipped: `tests/_netguard.py` (socket + `psycopg2.connect` boundary, `AF_UNIX` carved out so
asyncio's self-pipe survives, loopback deliberately blocked), a `network` marker for the one opt-in
integration test, `make test-offline`, and `scripts/offline_test_inventory.py` +
`docs/ops/offline-test-inventory.json`.

**One live defect fixed.** `asxos/config.py:6` points pydantic-settings at
`~/Projects/asxos-secrets/.env.production`, which exists on the dev machine. Measured: **1 of 30
credential fields — `eodhd_api_key` — carried a real production value into every local test run.**
That is the consequential one: it disarms the empty-key guard at `asxos/ingestion/eodhd.py:166`, so
an unmocked `get_client()` would have authenticated against the live vendor instead of raising.
`conftest.py` now points `HOME` at an empty temp dir, making the file unreachable rather than merely
outranked. Measured after: 0 of 30.

**A bug that nearly shipped.** The opt-in lift was first written as an autouse fixture.
Function-scoped fixtures run *after* module-scoped ones, and
`tests/test_price_revision_migration_integration.py` opens its connection in a `scope="module"`
fixture — so the guard would have stayed armed there, **silently breaking the
migration-integration CI lane while every offline run stayed green**. Rewritten as a
`pytest_runtest_protocol` hookwrapper. The live lane confirms it: **51 passed, 0 skipped** against
its `postgres:17` container on #211's branch.

### #211 — fence integrity

Three gaps in the always-on authority guard, found by *probing* it rather than reading it. Its
header (`:22-27`) frames its residual risk as exotic — "a base64-decoded path, `os.rename`,
indirect string construction". The two most ordinary spellings walked straight through.

| Probe | Before | After patch |
|---|---|---|
| `rm .github/workflows/full-check.yml` | **ALLOW** | deny |
| `rm docs/product/arbi-constitution.md` | **ALLOW** | deny |
| `rm .env` | **ALLOW** | deny |
| `echo x > ./.github/workflows/foo.yml` | **ALLOW** | deny |
| `echo x > ./docs/product/arbi-constitution.md` | **ALLOW** | deny |
| authority-guard with `jq` absent | **ALLOW** (fails open) | deny (fails closed) |
| unattended-guard, `.github/`, `ARBI_UNATTENDED=1` | **ALLOW** | deny |

Deletion and the `./` prefix affect **every** authority path, not only `.github/`. The `jq` case
meant the always-on fence silently vanished on a machine without jq, where
`unattended-guard.sh:49` already failed closed.

Per ADR §10.2 D7 — *"an agent must not edit its own permission surface"* — these are **staged, not
applied**, in `docs/proposals/fence-integrity-2026-09-06/`.

### The withdrawn unfence — why it was wrong

I proposed narrowing `.github/**` so the verifier lane could be authored here, then hardening it
with a content-validating hook gate. James rejected both. The reasoning worth keeping:

1. **Hooks are feedback; controllers are enforcement.** A Claude Code hook runs only under Claude
   Code with hooks installed — not for Cursor, Codex, `git apply`, or a human. R17 already
   established the surfaces do not share a fence. ACP §12.3 puts the workflow-content controller in
   `asxos-control` as a deterministic diff check producing a *required status*. Calling a hook "a
   first small implementation of that controller" conflated advisory with load-bearing.
2. **The premise was wrong.** The verifier is a reusable workflow in `asxos-control` with a thin
   caller here — so the artifact is a file James applies, which D7 already permits. The unfence
   bought no capability.
3. **The gate failed on its own terms.** `secrets: inherit`, `toJSON(secrets)`, `secrets['NAME']`
   and `on: workflow_run` all evade a `secrets\.` match, and narrowing to named files would have
   **unfenced `.github/actions/**`**, where a composite action carries arbitrary steps and has no
   SHA to check.

The staged verifier now sits at `docs/proposals/asxos-control/` instead, with no unfence required.

## State at close — all measured

```
main @ fd6172c (#211). Merged since the 09-06 wake snapshot (e058be3): #209, #212, #213, #211.
- tests: 4404 passed / 1 skipped (fresh [dev] venv, no [ml]); ruff + mypy clean.
  09-06 wake measured 4382 (+22: 13 inventory, 4 fence-drift, 5 from #212).
  Skip = MIGRATION_TEST_DATABASE_URL opt-in, unchanged.
- migrations: 51 files on disk, highest 0052_outcome_materialisation.sql, 0042 absent
  (reserved, correct). No migration authored or applied this session.
- open PRs: #202 (dream candidate, draft), #214 + #215 (dependabot, both READY, not draft).
- open issues: #204 (ACP programme), #205 (ACP Phase 0).
- workflow exposure (tools/workflow_inventory.py, shipped in #211):
  16 workflows · 5 PR-head · 2 exposed to an authored PR.
- CI: full-check / targeted-ml-tests / migration-integration green on every push both PRs.
  PR Review Agent skipped while draft on both — the draft gate, observed live.
- No DB write, no migration, no deploy, no dispatch, no push to main this session.
```

## Pending, requiring James

1. **Apply the staged fence patch** — `docs/proposals/fence-integrity-2026-09-06/`. One command:
   `git apply .../fence-integrity-all.patch && cp .../tests-staged/test_fence_integrity.py tests/`.
   ⚠️ The three `authority-guard.sh` diffs are individually clean but **not sequentially
   composable** (W1b shifts the context W1c anchors on) — use the combined patch. **W1b and W1c are
   separable** from the W1 you named; taking W1 + W2 alone is coherent.
2. **Decide W6 (the workflow-content lint).** Optional in the approved work order; not built
   without a yes. It is the artifact that encodes the bypass table at the enforcement-correct
   point — one script, consumed by `asxos-control` as a required status and optionally by the hook
   as feedback.
3. **Two workflows are exposed to an agent-authored PR**, both controlled use while `.github/**`
   holds: `migration-drift.yml` (its `pull_request` paths filter names **its own file**, so a PR
   editing it triggers it at head with `DATABASE_URL`) and `pr-review-agent.yml` (skips on draft,
   runs at head with `OPENAI_API_KEY` + `issues: write` the moment a PR is marked ready). Your
   stated end-state — secrets out of this repo, brokers in `asxos-control` — closes both.
4. **`allowed_actions: "all"`** *(measured via `gh api`)*. You named the repo's allowed-actions list
   as the real control behind a pinned-but-malicious action; it currently restricts nothing.
   `sha_pinning_required: true` and `default_workflow_permissions: read` are both on.
5. **Dependabot #214 / #215 are open and not draft** — they will trigger `pr-review-agent` at head
   with `OPENAI_API_KEY` on every synchronize.
6. **`asxos-control` does not exist.** Everything under `docs/proposals/asxos-control/` waits on it.

## Observation, not shipped

`authority-guard.sh` has no equivalent of `unattended-guard.sh:55-56`, which denies when a payload
arrives but no `tool_name` can be read from it. The authority guard falls through to `exit 0`. Same
fail-open class as W1, but outside the items approved this session, so it is reported rather than
patched.

## Lessons

1. **A grep hit proves a string exists, never what it does.** I claimed "seven workflows trigger on
   push to `claude/**`", inferred from grepping for the branch pattern, and built a security
   argument on it. Reading each `on:` block showed **two**, both secretless — and the framing missed
   both genuinely exposed workflows, which are reachable via `pull_request`, not push. James's
   correction — *the question is any trigger that runs at the PR head with repository secrets
   available* — is now the criterion the inventory computes. Labelling every claim measured or
   inferred is standing practice from here.
2. **Hooks are feedback; controllers are enforcement.** Recorded above; the general form is that a
   control which only exists inside one agent's runtime is not a boundary.
3. **A guard's own account of its residual risk is a hypothesis.** `authority-guard.sh` described
   its gaps as exotic. Three probes found ordinary ones. Probe the guard; do not read it and
   believe it — and probe it by invoking the guard, never by performing the destructive act to see
   whether it is caught.
