# Production sprint — feature F-E2E, contract revision r1 (2026-09-07)

**Status:** **admitted by James 2026-09-07** (cadence and identity rulings in §3/§4) — **not authority, not a second queue.** Every slice
below maps to a `roadmap-state.md` Stage and a `backlog.yaml` id; `roadmap-state.md` wins on
disagreement. **Prompted by:** James, 2026-09-07 — "plan the next sprint of production" in the
frame we discussed: *version control and building out features within those versions to build
the end-to-end process.*
**Frame (already ratified or proposed in-repo):** the ACP plan's work / version-control control
plane — four lanes, WIP 1 each, lifecycle `Inbox → Shaping → Candidate → Admitted → Building →
Verifying → Observing → Done`, and git rules 1–10
(`docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md` §10.2–10.4);
the dream candidate's L-cand-49/50 (#202): *one parent identity per feature, one independently
verifiable vertical slice per sub-item, an append-only contract revision (`r0`, `r1`, …), every
branch from current `main`, `Work-Item` / `Contract-Revision` trailers, and a feature is done when
its promised outcome was observed or honestly missed — not when a PR merged.*
**Baseline:** `main` @ `fd6172c` (#211), 2026-09-07 04:26 UTC. **Every figure measured** unless
marked *inferred*.

---

## 1. The feature and its versions

There is exactly one strategic feature in this repo's definition of done — the reference vertical
(`target-architecture.md` §16):

```
point-in-time evidence → validated opportunity → broker-report-quality thesis → independent
challenge → portfolio-aware size range → immutable DecisionPacket → delivered brief → James
disposition → benchmarked paper outcome → process and financial attribution → learning decision
```

**F-E2E** — *one real, James-visible, non-Model-A paper case completes the reference vertical.*
Its "versions" are **contract revisions** of that one feature, each an independently observable
increment of the end-to-end process. SemVer is not used (git rule 10; no public compatibility
contract exists).

| Revision | Outcome the contract promises | State (2026-09-07) |
|---|---|---|
| **r0** — the vertical exists in code | Stages 1→5 machinery on `main`; every stage identity resolvable **from fixtures**; every `renders:` honestly empty | **merged 2026-09-05** (#192–#198, #201). Stage cells unchanged by rule — code landed, nothing observed |
| **r1 — this sprint** | the vertical runs **against the live database** for one positive-control candidate and reaches **James's disposition**: `DecisionPacket` → identical render → `DeliveryReceipt` → `Disposition` rows exist for a non-CBA `big-4-banks` member; the negative control (CBA.AU) still closes `abstain` | proposed below |
| **r2** — first outcome observed | Stage 5 `t0` recorded and the 21-session horizon observed once; benchmark comparison rendered from a real series | after r1 + ~1 month of sessions (C-8, C-9, E-15) |
| **r3** — online | the same loop fires from a scheduled lane and its observation lands in Healthchecks with no click (A-20 → A-23) | gated on the producer-credential P1 (A-22) |

**r1 acceptance** is the Stage 4 exit gate verbatim (`target-architecture.md:1055-1063`), each
clause mapped to evidence:

| Clause | Evidence that closes it |
|---|---|
| exact evidence, thesis, challenge, portfolio, packet, render, delivery, disposition identities resolve | `asx decision build --persist` then `asx decision dispose` from a pooler-reachable machine → one row each in `decision_packets`, `delivery_receipts`, `decision_dispositions` for the positive control; content hashes cross-resolve (`DecisionCase` validators) |
| missing evidence forces abstention | the CBA.AU packet still closes `abstain` on `price_detached` after r1's calibration is applied (negative control preserved) |
| renderers contain no financial logic | unchanged — pinned by the Stage 4 tests already on `main` |
| no Model A input enters the chain | unchanged — grep-pinned in five test files; `signals` never read |
| the process remains non-executing | unchanged — paper intent only; James's broker is outside the system |

**Reserved James actions in r1 (the contract names them; arbi never plans around them):** C-5
(approve a second `big-4-banks` member), C-13 (rule the P5-01 calibration), D-9 (ratify tax-alpha
§5.5), C-3 / C-4 / C-6 / C-7 (the live CLI runs with `--persist`), B-3 + C-1 (backup deadman +
run ids), the fence patch set (#211, D7), A-24 (issue-snapshot route).

**Rollback:** every slice is a draft PR on `claude/**`; nothing in r1 changes production
scheduling, secrets, or migrations. `0045` and `0042` stay unapplied.

---

## 2. Lanes and slices (WIP 1 per lane, ACP §10.2)

Each slice: one branch from current `main`, one PR, one mutator, commit trailers
`Work-Item: F-E2E/<slice>` · `Contract-Revision: r1` · `Contract-Digest: <git hash-object of this
file at admission>`; the PR body maps every acceptance criterion to a test or evidence item and
names effects, overlays, observation, rollback, dependencies and reserved actions (git rule 7).
Max two active implementation PRs on the feature at once (rule 4). Stack depth ≤ 2, and only when
the child cannot satisfy its contract without the parent (rules 2–3).

### Strategic feature lane — F-E2E r1

| Slice | What | Owner · route | Paths | Depends on | Done when (evidence) | Backlog |
|---|---|---|---|---|---|---|
| **S1** | tax-alpha **§5.5 lot selection** + the `lots.py` partial-draw fix as a proposed diff + numeric TC (the 6,250-vs-5,000 fixture, `session-handoff-2026-09-03.md:110-113`). Defect verified live: `lots.py:93-101, 110-125` — `combinations` keeps input order and `_draw` puts the partial on the last lot, so post-discount gain is not minimised when per-unit gains differ (`audit-2026-06-27.md:104`) | arbi · attended, Tier A, **`tax-spec-conformance` on record** (rule #8) | `docs/foundation/spec/tax-alpha.md`, `asxos/domain/tax/lots.py`, `tests/test_tax_lots.py` | — (A-13 merged) | TC fails on `main`, passes on the branch; `make check` green; merge **contingent on D-9** (James's ratification is the merge) | D-9a → D-9 |
| **S2** | **P5-01 capital/risk calibration proposal** — `docs/proposals/p5-01-risk-calibration-2026-09.md`: loss / drawdown / position-size limits as options with one recommended default each, every number traced to an existing constraint (`portfolio-policy.md`; ADR D1 cash floor 7.5 %, D2 0 % leverage; F4's universal gates `target-architecture.md:1796+`), a worked application to `dpk-cba-1-2026-09-01` showing which gates bind and that the negative control still closes `abstain`, an explicit `model_independence` statement, and a "changes nothing until James merges an edit to `portfolio-policy.md`" clause | arbi · attended, docs-only; **`portfolio-invariant-guard` + `arbi-red-team`** | `docs/proposals/` | — | James rules C-13 (accept / amend values / reject). P5 is draft-only (`arbi-permission-model.md:171`); "closes at abstain" is a **policy** gate (`portfolio-policy.md:35-37`) | C-13a → C-13 |
| **S3a** | **G12 tax-feed design spike** — what a `readiness="pass"` `TaxAssessmentReference` needs for a *new paper position*. Measured inputs today: `rs_corporate_actions` 43,423 rows (dividend events per symbol — the only dividend source), `holding_lots` 1 row (HUBS, US, outside v1 tax scope), no franking source. Output: a one-page design naming the producer (`tax_view_individual`, `TAX_ASSESSMENT_PRODUCERS`), the `Dividend` inputs derivable from corporate actions, realised gains honestly empty for a paper position, and **franking as a James-supplied input** per spec §1 ("trust the share registry statement") or `applicability="uncertain"` | arbi · attended (DB probes), **`backend-architect` + `tax-spec-conformance`** | `docs/proposals/` | — | James accepts the input contract (which fields he supplies) | C-14 (design half) |
| **S3b** | **G12 producer** — build the dividend feed from `rs_corporate_actions` for one symbol and wire `tax_view_individual` into `TaxAssessmentReference` via the named producer; `unknown` stays the default everywhere else | arbi · attended, Tier A capital-adjacent (`asxos/domain/tax/`) — **in-fence only** | `asxos/domain/tax/`, `asxos/domain/results_review/contracts.py`, `asxos/domain/decision_engine/builder.py`, tests | S3a accepted | readiness `pass` for the positive control with real inputs; `unknown` for every fixture; CBA negative control unchanged; `make check` green | C-14 (build half) |
| **S4** | **The live runs** — C-3 `asx research run --dry-run`, C-4 `asx candidates build`, C-6 `asx decision build`, C-7 `asx decision dispose` for the positive control, from a machine that reaches the pooler | **James** (personal-use gated; six recorded sandbox failures) | — | C-5, S2 ruled, S3b merged | the three Stage 4 rows exist (r1 observed) — or an honest miss recorded with the packet's `missing_evidence` | C-3 / C-4 / C-6 / C-7 |
| **S5** | Stage 5 `t0` — `asx decision record-t0 --persist` | **James** | — | S4 | `thesis_outcomes` t0 row (opens r2) | C-8 |

**Sequence inside the lane:** S1 ∥ S2 (independent files) → S3a → S3b; S4/S5 are James's and
follow C-5 + C-13 + D-9. S1 is first by "defensibility wins ties" (code with a verified defect,
capital-facing via `decision_engine/staging.py:110`); S2 is the older deferral (F4, 2026-08-10) and
the Stage 4 policy gate — both land in the first window.

### Reliability lane

| Slice | What | Owner | Done when | Backlog |
|---|---|---|---|---|
| **R1** | apply the fence-integrity patch set staged in #211 (`fence-integrity-all.patch` + `tests-staged/test_fence_integrity.py`) — `rm` / `./` / `jq`-absent / unattended `.github` gaps all measured **ALLOW → deny** | **James** (D7: an agent must not edit its own permission surface) | `tests/test_fence_integrity.py` 25 passed on `main` | new row owed |
| **R2** | `issue-snapshot.yml` archive route (recommend B — unprotected `ops/issue-snapshot` branch); the file on `main` is still `[]` | **James** (`.github/**`) | the next scheduled run green and `git ls-remote origin ops/issue-snapshot` non-empty | A-24 |
| **R3** | backup observed on both: **B-3** deadman secret, **C-1** paste run ids (drill already green 09-06, run 34048829799), **B-2** patch (drill asserts 14 tables; 0048–0052 tables outside it) | **James** | Healthchecks shows the check; A-19 un-xfails | B-2 / B-3 / C-1 → A-19 |
| **R4** | **monitoring truth**: (a) `contradictions.py` still carries a rule for the retired `REQUIRED_MIGRATIONS` constant; (b) the snapshot's `workflow_runs` keeps one row per workflow, which hid three red `pipeline-health` runs — carry last-N conclusions (or a `last_failure`) per scheduled lane; (c) `sync_prices.py:9-11` module docstring still says "through today (UTC)" | arbi · `/build`-sized, Tier A (`asxos/secondbrain/`, `jobs/`) | tests pin both; `check_project_state.py` PASS on a snapshot carrying reds | new row owed |
| **R5** | `check_ledger_coverage.sh` is red on six **pre-existing** close rows (2026-08-20/21/22 and the three 08-22 sub-rows: no or multiple Amendment E fields). The ledger is append-only — annotate or waive is a ruling | **James** | script exit 0 | new row owed |

### Maintenance lane

| Slice | What | Owner | Backlog |
|---|---|---|---|
| **M1** | Dependabot **#214** (`claude-code-action` 1.0.210 → 1.0.216, `.github/**`) and **#215** (python group, 5 updates) — audit against the suppression checks per the #191 pattern, then merge | arbi audit → **James** merge | D-6 pattern |
| **M2** | doc-expiry sweep — 25 dated docs owe an archive decision; inbound-reference grep per file; allowlist the canonical ones | arbi · attended (judgement per file) | E-17 |
| **M3** | `backlog.yaml` hygiene: A-19 names a test that does not exist (`test_backup_workflow_arms_the_deadman`) — write it when B-2 lands or rename the row; C-11's title still says "currently 1-for-1" | arbi · `/build` | A-19, C-11 |
| **M4** | the two Amendment G items and the agent-role repoint (**B-7 / B-8** — the only mechanical rule-#11 control; **B-10 / B-11**) | **James** | B-7 … B-11 |

### Exploration lane — empty this sprint, by design

ACP §16's first Lab work ("one item per lane") is created only **after Phase-1 admission exists**,
and Phase 0's remaining eight gates are James's (#205: Amendment M, `asxos-control` root, Apps,
control-ledger project, secret evacuation, Lab isolation, workload-identity proof, baseline).
Arbi's exploration budget this sprint is zero rather than a speculative probe — the same "not a
parallel queue" rule the plan states.

---

## 3. Windows and gates — RULED 2026-09-07: three attended R2 windows, in-fence

**James, 2026-09-07:** three attended R2 windows, each launched from the repo root so the four hooks
and the real `arbi` / `guilfoyle` / `tax-spec-conformance` agents load; the gates below hold.

Attended R2 windows, **in-fence** (launched from the repo root so the four hooks and the real
`arbi` / `guilfoyle` / `tax-spec-conformance` agents run natively — AW-01's emulation and
mailbox gap should not recur). Each window: wake → red-team gate → ≤3 substantive draft PRs →
close with a ledger row and morning report.

| Window | Builds | Needs from James **before** it | Leaves for James **after** it |
|---|---|---|---|
| **W1** | S1, S2, R4 | nothing (all inputs on `main`) | D-9 ratification (merge S1); C-13 ruling (S2); merge R4; M1 audit verdicts |
| **W2** | S3a, M2, M3 | C-5 (second theme member) so S3a designs against a real candidate; R1 patch applied so W2 runs behind the hardened fence | accept S3a's input contract; supply franking for the candidate (or accept `uncertain`) |
| **W3** | S3b, close of r1's arbi half | S3a accepted | **S4 / S5 — the live runs** (r1 observed), B-3 / C-1, R2 |

"Online" (r3) is not a window — it is A-20 → A-23 and the credential P1, all James's; the plan
adds no `schedule:` trigger anywhere (gate 7 open).

---

## 4. Work identity — RULED 2026-09-07: this file + `backlog.yaml` until B-15

**James, 2026-09-07:** keep the plan file and `backlog.yaml` as the identity until B-15 rules D10 in
force; the trailers are adopted now; the Issue tree cuts over in one batch with D10. The two options
are retained below for the record.

D10 (GitHub Issues as the system of record) is **ratified, not in force** (B-15;
`architecture-decision-record.md` §5.4; `roadmap-state.md` "do not treat GitHub Issues as the live
queue"). Issues #204/#205 already use the parent / sub-issue / `Contract revision: r0` shape for the
ACP programme. Two honest options:

- **(a) Create the tree now** — parent `[Feature] F-E2E — one real paper case completes the
  reference vertical` with the r1 contract as its first comment, and one sub-issue per S/R/M slice
  carrying the `Work-Item` id. Ten `gh issue create` calls; `issues: write` is on the token. This
  pre-empts B-15 in the same way #204/#205 did.
- **(b) Keep this file + `backlog.yaml` as the identity** until B-15 is ruled, adding the owed
  rows (R1, R4, R5) at the next wake, and cut the Issues over in one batch with D10.

Either way the trailers are adopted now, so the commit history carries the identity regardless.

---

## 5. Definition of done for the sprint

r1 is **Done** when `decision_packets`, `delivery_receipts` and `decision_dispositions` each hold
a row for a non-CBA `big-4-banks` member built from live evidence with `readiness="pass"` from a
named producer, and the CBA.AU packet still closes `abstain` — observed, not merged. r1 is an
**honest miss** if any reserved James action stays open at the sprint's end; the close row says
which, and r1 carries over unchanged (no new revision for an unchanged contract).

## 6. What not to do

No `schedule:` trigger (A-22 open) · no edit to `portfolio-policy.md` by arbi (P5 draft-only) ·
no `lots.py` merge ahead of D-9 (rule #8) · no `--persist` CLI run by arbi (C-3…C-8 are James's) ·
no Stage cell flip because a slice merged · no `.github/**` or hook edit by arbi (D7; patches only) ·
no Model A input anywhere · `0042` / `0045` stay unapplied · Issues are not the live queue until B-15.
