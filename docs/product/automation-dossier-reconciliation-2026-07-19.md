# Automation dossier — reconciliation against live repo state (2026-07-19)

**Status:** analysis (arbi, main-loop). Not authority. Reconciles the ChatGPT "ASXOS / Arbi
Automated Development Loop Dossier" against live repo state + **this session's canary**
(`arbi-canary-2026-07-18-brief-truth.md`), which is a live worked example of the exact inner
loop the dossier theorizes about.
**Owner:** James ratifies any action; arbi drafts only.

---

## 0. Bottom line

The dossier's central diagnosis — **"the inner development loop works; the outer continuity loop
does not"** — is **CONFIRMED** by this session's canary. I just carried a real product mission
(the brief-truth fix, PR #64) end-to-end: arbi select → arbi-red-team gate → backend-architect
design → build → security-engineer + portfolio-invariant-guard review → review-gate marker →
commit → draft PR → CI subscription. Every inner-loop component the dossier calls "proven" fired,
live, on novel work.

But the canary adds **one refinement the dossier misses, and it is load-bearing:** a mission that
looks *green-lane* (a bug fix) surfaced a **governor judgment mid-flight** — James's live
brokerage screenshot revealed the "honest metric" was a *choice* (broker's +19.57% USD return vs
the tax-cost-base +10.3% AUD-incl-FX), not a lookup. A naive "green issue → autonomous build →
draft PR" loop **would have shipped the wrong number** (+10.3%, disagreeing with his broker) and
looked authoritative doing it. **Lane classification must gate on "does this mission embed a
value/policy judgment?", not only "is the final artifact reversible?"** This is the single most
important correction to the dossier.

---

## 1. Agree / already-built / what it gets wrong

**AGREE (confirmed against live state or the canary):**
- Inner loop is real — canary proves it end-to-end on novel work, not just pre-scoped issues.
- Outer continuity loop is missing — no durable controller owned WAIT_CI → REPAIR → GRADE; I
  stood in for it manually (subscribed to PR activity + scheduled a `send_later` check-in).
- `main` = production — **verified**: `render.yaml:45` `autoDeploy: true`, all 29 services
  `branch: main`. Green auto-merge is unsafe until an integration/production split exists.
- Credential/tool exposure is real and incomplete — the 6 discovery/analysis agents still
  reference the write-capable Supabase MCP in frontmatter (agent-RO repoint outstanding).

**ALREADY-BUILT / dossier understates:** the machinery (arbi, guilfoyle, reversible-work-builder,
review-gate, scorecard, handoff, `/arbi-mission`, `send_later`) all exist and composed cleanly
this session. `send_later` (the dossier's "scheduled re-entry") **works** — I used it for the CI
check-in. The attended loop is closer to Level-A-complete than the dossier's "proven components"
framing implies.

**WRONG / needs correction (canary evidence):**
1. **Reversible ≠ safe-to-automate.** The dossier's green lane = "reversible / draft-PR-ceiling."
   The brief-fix was reversible yet embedded an *irreversible-if-wrong* governor judgment. The
   lane model needs a **judgment-surfacing gate**: before autonomous build, detect whether the
   mission encodes a value/metric/policy choice (e.g. "which return do we show?") and route it to
   AMBER (ask once) even though the artifact is reversible.
2. **The local-verification ceiling is underweighted.** An unattended session in THIS sandbox
   **cannot run the async/DB suite** (no asyncpg/pytest-asyncio) — this session verified only
   py_compile + ruff + pure-sync tests + standalone template renders. So "ready" MUST gate on the
   CI `full-check` result, and the loop must *know* it can't self-verify locally (else it
   false-claims "tests pass"). The dossier's Stage-5 CI-repair leg is therefore not optional
   polish — it is the *only* real verification path here.
3. **R16 (permission-stream aborts) is a hard DOA blocker, not "finish the wiring."** This session,
   an **allowlisted** `mcp__supabase-ro__execute_sql` SELECT aborted **4/4** with "Tool permission
   stream closed", and `AskUserQuestion` aborted too. An unattended loop whose first DB read or
   human-gate aborts is dead on arrival. The dossier's Stage-1 "repoint agents to supabase-ro" is
   *useless while supabase-ro itself aborts.* Real Stage 1 = **make read-only access reliable
   (root-cause R16) AND scoped (repoint frontmatter)** — reliability first.

---

## 2. The minimum v1 loop for THIS exact mission (brief-fix trace)

Tracing the brief-truth mission through the dossier's state machine — ✓ exists / ✗ missing:

| State | This mission | Status |
|---|---|---|
| SELECT | arbi engine-first re-rank produced it | ✓ exists |
| RED-TEAM | `arbi-red-team` gate (PASS) | ✓ exists |
| **JUDGMENT SURFACE** | James's brokerage screenshot → metric is a governor choice | ✗ **no mechanism to detect + pause** |
| PLAN/DESIGN | `backend-architect` | ✓ exists |
| BUILD | main-loop / reversible-work edits | ✓ exists |
| TEST_LOCAL | py_compile + ruff + pure tests + render check | ⚠ partial (async suite CI-only) |
| REVIEW | security-engineer + portfolio-invariant-guard | ✓ exists |
| GATE | review-gate marker | ✓ exists (touch must be a *separate* shell call — checked at PreToolUse) |
| PUBLISH_DRAFT_PR | PR #64 | ✓ done |
| WAIT_CI → REPAIR | manual subscribe + `send_later` check-in | ✗ no controller owns it |
| GRADE | self-assessed | ✗ no independent grader ran |

**The minimum loop needs exactly three net-new things** (everything else is reuse): (a) a durable
controller that owns WAIT_CI → REPAIR → GRADE across sessions; (b) a **judgment-surfacing gate**
that pauses for a governor call; (c) explicit awareness of the local-verification ceiling (gate
"ready" on the CI check, never a local green). No new governance framework — a controller loop
over the existing agents.

---

## 3. Strict green / amber / red split

- **GREEN — draftable, reversible, autonomous-capable *after* the loop is built:** ordinary
  code/test/docstring fixes, monitoring logic, governed-view reader fixes, CI-repair that does not
  weaken a gate — **only if the mission encodes no governor judgment** (the new gate). *The
  brief-fix would have been green EXCEPT for the brokerage decision → it was amber-by-content.*
- **AMBER — complete the artifact, ask once:** `.claude/**`, `.github/**`, `CLAUDE.md`,
  `render.yaml`, migrations-as-files, authority/policy docs, dependency changes — **plus any
  mission that surfaces a value/metric/policy judgment** (brief-fix belongs here). Draft PR + one
  governor question.
- **RED — capability absent / per-action only:** merge to main (= production deploy, verified),
  migration apply, Render mutation, secrets read/rotate, branch-protection change, capital/broker
  action, Model A for real capital. The unattended environment should not hold the credential.

---

## 4. One implementation-ready next mission (reuse, no new framework)

**Mission: "Reliable, scoped read-only agent DB access."** The true Stage-1 foundation — nothing
unattended (or Phase 2c discovery) works until agents can *reliably* read.
- **(a) Root-cause R16** — why an allowlisted `mcp__supabase-ro__execute_sql` aborts with
  "permission stream closed" in web/remote sessions (hypothesis: the allow-list matches a literal
  tool-name string while the live MCP connection presents a rotating hash identity — observed
  churning all session). Diagnose; if it's a settings/identity mismatch, draft the fix.
- **(b) Repoint the 6 discovery/analysis agent frontmatter** files `mcp__Supabase__` →
  `mcp__supabase-ro__` (RED-ZONE authority edit → attended, draft PR, James merges).
- **(c) Add a CI policy-test** that fails if any discovery/analysis agent regains the
  write-capable tool (the dossier's deterministic-gate idea, minimally scoped).
- **Owner/flow:** main-loop attended, `security-engineer` in the review loop, review-gate marker,
  **draft PR only.** Reuses everything; builds no new controller yet. This unblocks Phase 2c AND
  is the precondition for any later unattended loop.

*(The fuller CI-repair-to-grade controller — dossier Stage 3/5 — comes after, and only if
throughput becomes the bottleneck. It is a thin `/arbi-mission` extension: poll CI via the GitHub
MCP on a `send_later` cadence, dispatch reversible-work-builder to repair in-scope on failure,
dispatch a fresh-context grader on green, record to the run-ledger. Not this mission.)*

---

## 5. Recommendation: dossier automation vs broker-report Phase C

**Phase C (product) should PRECEDE the dossier's automation build.** Evidence + reasoning:
- The attended loop **already delivers product value today** — the brief-fix shipped to a draft PR
  in one session. I do **not** need the overnight controller to do Phase C; I can do Phase C
  attended, exactly as I just did the brief-fix.
- James's own directive this session: the **absolute focus is better theses / briefs / ideas.**
  The automation dossier, however good, is *dev-loop plumbing* — second-order to the product edge.
  It should not jump ahead of Phase C.
- **Exception (do this small piece now, in parallel):** the deliverable-4 mission (reliable +
  scoped agent-RO reads / R16 fix) is small, contained, and unblocks the Phase 2c *discovery
  agents* that generate investment ideas — so it earns its place *before* Phase C as a quick amber
  mission, independent of the broader automation controller.

**Sequence:** (1) reliable agent-RO reads + R16 fix (small amber mission, unblocks discovery) →
(2) broker-report Phase C (the product edge) → (3) the CI-repair-to-grade controller *only if*
attended throughput becomes the bottleneck. Do not build the full autonomy kernel ahead of the
product it exists to serve.
