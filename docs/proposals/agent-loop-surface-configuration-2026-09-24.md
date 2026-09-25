# asxos agent loop — surface configuration, rev 3 (rev 2 adopted with amendments)

**Status:** adopted 2026-09-24 · **Owner:** arbi · **Rulings:** James, 2026-09-24
**Enacted by:** AGENTS.md §8a and the PR set below · **Supersedes:** rev 2 (research input, not enacted)

James pasted rev 2 on 2026-09-24 with one instruction: *"ensure we keep Arbi's automation."*
This document records what arbi found when it checked rev 2 against the repository, what
James ruled on the four points that were his, which parts of rev 2 stand, which are
amended and why, and the PRs that enact it. Rev 2 as received is appended verbatim.

## What the repository actually had (2026-09-24 survey)

Rev 2 mostly described mechanisms that did not exist yet, and had two facts backwards:

- The picker (`asxos/backlog.py`) read `docs/product/backlog.yaml`, not Issues. No code read
  or wrote an issue label. No digest job existed — the only digest was the model-based
  `nightly-steward` Routine on issue #271. No `issues:`-triggered workflow. No SessionStart
  hook; `secrets-guard.sh` was Bash-only, logged nothing and failed open (missing `jq` →
  exit 0; unset `CLAUDE_PROJECT_DIR` → exit 127, non-blocking). A-22 proof 2 was unproven
  and the record contradicted itself. `backlog-roll.yml` had 0 runs (A-20) and a latent bug
  (its `record` job read `needs.verify` / `needs.publish`, jobs that do not exist).
- **Backwards #1:** all four headless agent lanes already mounted a read-write Supabase MCP
  (`.github/runner/mcp.json`, no `--read-only`); rev 2's "migrations via CI only, never MCP"
  would have deleted AGENTS.md §8, the attended sequence arbi applies migrations by.
- **Backwards #2:** Cursor was not "just an IDE": PR #367 had granted a Cursor agent
  `merge_pull_request` and `apply_migration`; Cursor Agent had eight commits on the mandate
  branch and was co-author on five squash merges to `main`, and it raced this session on
  #346 in real time.
- Three places rev 2 narrowed arbi against AGENTS.md §0/§7/§8: the provenance rule (only a
  failing run or a decision-log row — so the loop could never build roadmap work), the
  hard-coded brakes counting *all* open PRs as WIP (arbi merges its own Green/Amber PRs),
  and retiring `daily-product` — the only builder actually landing work — for a lane with
  zero runs.

## James's rulings (2026-09-24)

| Question | Ruling |
|---|---|
| Cursor holds merge + migration rights (#367); rev 2 says IDE-only | **IDE-only; revert #367** (PR #379). Narrowing the Cursor GitHub App is James's. |
| Headless lanes mount a read-write Supabase MCP; rev 2 wants unattended surfaces read-only | **Keep read-write everywhere.** The controls stay: the picker's denied `migrations/` path, the auto-mode grant that requires a `backup.yml` success, the prompt rule. |
| `daily-product` (landing work daily) vs `backlog-roll` (0 runs) | **Overlap, then James switches**: arm `backlog-roll`; a routine-doc gate stops both building on one day; after three green scheduled runs James disables the Routine. |
| Who merges the AGENTS.md amendment | **arbi, under §14.** It narrows arbi (a filter arbi cannot override); only `.claude/**` is James's. |

## What stands from rev 2, what is amended

| Rev 2 | Verdict | Why |
|---|---|---|
| Issues are the queue; Layer 1 in code; Layers 2–4; brakes; digest; A-22 canary; `needs-triage` intake from claude.ai | **Stands** | Deterministic, additive, and aligned with AGENTS.md §11 |
| Provenance = failing run id or decision-log row only | **Amended** | Any of `run:<id>`, `decision-log:<date>`, `backlog:<id>`, `roadmap:<id>`, `doc:<path>#<heading>` under `docs/product|proposals/`, `issue:#<n>` by the owner |
| Brakes: 3/day, WIP > 2 PRs "await review" | **Amended** | Repository variables `AUTO_READY` (unset ⇒ off), `AUTO_READY_DAILY_CAP` (3), `AUTO_READY_WIP_LIMIT` (2); WIP = PRs waiting on James |
| Migrations: CI pipeline only, never MCP | **Rejected** | §8 stays; James kept headless read-write |
| Supabase read-only on unattended surfaces | **Not now** | James's ruling; revisit on an incident |
| `backlog-roll` the only builder | **Amended** | Overlap with `daily-product`; a mechanical gate; James switches |
| Digest model-free on a new pinned issue | **Amended** | Model-free job on the existing #271; `nightly-steward` appends `Risks` after it |
| AGENTS.md amendment merged by James | **Amended** | arbi merges (§14) |
| Cursor IDE-only | **Stands** | #379 |
| `backlog-roll` cron `0 16 * * *`; digest `0 21 * * *` | **Amended / stands** | 16:00 collides with `weekly-research` (Sat) and #355's 16:04, and `tests/test_routine_docs.py` forbids a cron within 30 min of any Routine (17:30 `daily-product`) → **`43 16 * * *`**; digest **`0 21 * * *`**; steward moves to `45 22 * * *` |
| Layer 1 author = James or "arbi's identity"; Layer 4 signed comment | **Amended** | There is no separate arbi login. Trust = the owner login; the readiness marker is the audit trail; a `ready` without one is James's by hand |

## The PRs

| # | Branch | Class | Merges | State |
|---|---|---|---|---|
| 1 | `claude/github-client-extract` — one `GitHubClient` | Green | arbi | #376 merged |
| 2 | `claude/issue-eligibility` — Layer 1 + provenance | Green | arbi | #377 merged |
| 3a | `claude/issue-loop-autoready` — Layers 2–3, labels, shims | Green | arbi | #381 merged |
| 3b | `claude/issue-loop-picker` — Layer 4, backlog archived | Green | arbi | #382 |
| 4 | `claude/daily-digest-job` — model-free digest on #271 | Green | arbi | next |
| 5 | `claude/workflow-inventory-untrusted-events` | Green | arbi | #378 merged |
| 6 | `claude/issue-forms-and-agents-md` — forms, §8a, this doc | Green | arbi | this PR |
| 7 | `claude/backlog-roll-issues` — the lane on Issues, unarmed | Amber | arbi | after 3b, 6 |
| 8 | `claude/a22-hooks` — guard fails closed, watches Read, proof line | `.claude/` | **James** | #380 |
| 9 | `claude/a22-proof` — canary + proof step + 3 dispatches | Amber | arbi | after 8 |
| 10 | arm `backlog-roll` `43 16 * * *` + `daily-product` gate (James) | Amber | arbi / James | after 7, 9, `HC_BACKLOG_URL` |
| 11 | `daily-digest.yml` `0 21 * * *` + steward doc (James) | Amber | arbi / James | after 4 |
| 12 | `claude/cursor-ide-only` — revert #367's loosening | Green | arbi | #379 merged |

**James's, and nothing else:** merge #380; create `HC_BACKLOG_URL` (A-20); create the three
`AUTO_READY*` variables if `gh variable set` under the PAT is refused (unset is off, so nothing
arms by accident); move `nightly-steward` to 22:45 UTC; disable `daily-product` after three green
scheduled `backlog-roll` runs; scope down or remove the Cursor GitHub App; optionally wire the
claude.ai custom GitHub connector with `needs-triage` only.

---

## Rev 2 as received (2026-09-24) — research input, not enacted as written

# asxos Agent Loop: Recommended Surface Configuration (September 2026, rev 2)

**Status:** research input, revised to replace the human `ready` gate with arbi automated readiness inside deterministic eligibility rules. Not enacted.

**What changed from rev 1:** the approval gate. Rev 1 had James apply `ready` by hand. Rev 2 has arbi apply it, with a code-level eligibility filter that no model can override, a human-reserved list that never auto-readies, and brakes. Everything else stands.

### TL;DR

- **Build runner:** keep `backlog-roll.yml` (claude-code-action, pinned SHA) as the only autonomous builder. Its deterministic picker selects open Issues carrying a valid `ready` label. Arm a cron with `concurrency: 1` only after A-22 passes.
- **Approval gate:** arbi applies `ready` automatically, but only to issues that first pass a deterministic eligibility check in code. The repo is public, so eligibility never depends on a model reading issue text. Human-reserved classes (capital, mandate, `.claude/`, secrets, spend, north-star) always go to `needs-human`.
- **Planning and issue creation:** plan in the claude.ai Project. Create issues from chat through a custom GitHub MCP connector limited to issue tools, with Zapier as fallback. Issues created this way skip issue-form validation, so the eligibility workflow re-checks Definition of Ready.
- **Return path:** a model-free job posts one digest comment at 07:00 Brisbane covering merged, failed, auto-readied, and needs-human. You review after the fact, not before.
- **Governance:** auto-ready widens arbi's own authority, so the AGENTS.md amendment describing it is merged by James, not arbi.

### Recommended Configuration (one primary tool per job)

| Job | Primary | Fallback | Do not use |
|---|---|---|---|
| Planning and reasoning | claude.ai Project (memory, read-only Supabase MCP, GitHub file sync) | Claude Code in plan mode for code-heavy design | Cowork (GitHub connector unreliable) |
| Issue creation | claude.ai chat via custom GitHub MCP connector, issue tools only, `needs-triage` label only | Zapier "Create Issue"; `gh issue create` from local Claude Code | Claude in Chrome driving the UI; Cursor; Slack |
| **Approval gate** | **arbi auto-ready, after deterministic eligibility passes** | James applies `ready` by hand for anything arbi declines | Any model applying `ready` to an issue that failed eligibility |
| Human-reserved decisions | James, via `needs-human` items in the digest | none | Any automated path |
| Trigger | Scheduled deterministic picker (cron, `concurrency: 1`) | `workflow_dispatch` for manual runs | Label-triggered direct builds; `@cursor`; Slack tagging; routine GitHub triggers |
| Build runner | claude-code-action in `backlog-roll.yml` | `nightly-triage.yml` for failure response | Cursor cloud agents; Claude Code routines; Claude Tag |
| Ad-hoc PR follow-ups | `@claude` comment (write-access users) | Local Claude Code | `@cursor` |
| Database verification | Supabase MCP, `read_only=true`, `project_ref=<asxos>`, `features=database,docs` | SQL editor by hand | Read-write Supabase connector in any autonomous run |
| Database writes and migrations | arbi's CI pipeline only | none | Any MCP connector |
| Return path | Model-free daily digest on a pinned issue, pushed by GitHub Mobile | Read-only daily routine summarising to Slack (optional) | A dashboard; trusting a routine's green status |

### The Automated Ready Design

**Why the eligibility layer must be deterministic.** The repo is public: it clones without credentials. Anyone can open an issue. If readiness depended on arbi reading the issue body, an outsider could write an issue that argues itself into `ready` and gets built with the PAT in the job. The defence is a filter in code that runs before any model sees the issue. The model can only say yes to what the filter already allowed.

**Layer 1: eligibility (code, no model).** Runs on `issues: [opened, edited, labeled]` and again at pickup. An issue is eligible only if all hold: (1) author is `Jp8617465-sys` or arbi's own GitHub identity; (2) Definition of Ready: every required section of the matching form (`product`, `data-infra`, `research`) is present and non-empty; (3) no human-reserved label: `capital`, `mandate`, `needs-human`, `hold`, and any label mapped to AGENTS.md section 2; (4) no reserved scope: the body does not name `.claude/`, secrets, the north-star, or the personal-use invariant; (5) provenance for arbi-authored issues: must cite a failing run ID or a decision-log row. Without one, ineligible. Failures get `needs-info` (missing sections) or `needs-human` (reserved), with a comment naming the rule that failed.

**Layer 2: readiness (arbi's judgement, eligible issues only).** arbi checks: acceptance criteria are testable, scope fits one PR, class estimate is Green or Amber. If yes, it applies `ready` and posts a signed comment with its reasons, the class estimate, and the rule-set version. If no, it comments what is missing and leaves the issue for revision.

**Layer 3: brakes.** Rate: max 3 auto-readies per day. WIP: picker won't start a new issue while more than two PRs await review. Per-issue stop: `hold` label always blocks pickup. Global stop: repo variable `AUTO_READY=off` disables auto-ready entirely. Tamper: if an issue is edited after readying, `ready` is stripped and eligibility re-runs.

**Layer 4: picker verification.** The picker accepts `ready` only when applied by James, or by arbi's identity with a matching signed readiness comment on the issue. It re-runs Layer 1 at pickup time. A `ready` label applied any other way is ignored and removed.

**What stays human:** capital decisions and mandate ratification (AGENTS.md section 2); `.claude/` permissions and secrets (an agent must not edit its own permission surface); spend above the section 2 threshold; north-star and the personal-use invariant; the AGENTS.md amendment enabling auto-ready.

### Key Findings (rev 2, abridged headings — see the original for detail)

1. Claude Code triggers and scheduling: Routines fire on schedule (≥1 h), `/fire`, and PR/release GitHub events only — never issues; cloud sessions cannot push workflow files (#61189, unverified); claude-code-action scheduled runs are attributed to whoever last changed the cron; `show_full_output` must never be enabled on this public repo; hooks fail open and the guard must fail closed on its own.
2. Creating issues from a conversational surface: claude.ai built-in GitHub integration cannot; a custom connector to GitHub's MCP server probably can; Zapier can; API-created issues bypass form validation, so Layer 1 replaces the form's guarantee.
3. Trigger models compared: scheduled picker + auto-ready recommended; label-triggered direct builds, routines, `@cursor`, Slack not.
4. Cursor: keep as an interactive IDE; remove or scope down its GitHub App; branch protection prevents it merging.
5. Supabase access: `read_only=true`, `project_ref`, `features`; prompt injection via row data is documented; disconnect read-write from unattended surfaces.
6. Return path: a model-free job at 21:00 UTC comments on a pinned digest issue — Merged / Failed / Auto-readied / Declined / Needs me.

### Security: risks by path and mitigations (rev 2)

Public issue injection (author filter in code); self-approval loop (provenance, rate cap, digest); label forgery (picker accepts only James or arbi-with-signature, re-runs eligibility); edit after approval (strip and re-evaluate); scope creep into reserved classes (reserved labels and terms fail Layer 1); runaway (`AUTO_READY=off`, `hold`, WIP limit, `concurrency: 1`); injection from comments (issue body only; `include_comments_by_actor`); PAT exposure (prefer the App token; tight Bash allowlist; guard blocks `env`, `printenv`, `/proc/*/environ`, `git config --get`); debug-mode leak (never on this public repo); silent no-ops (structured output, fail if `pr_opened` claimed with no PR).

### Next steps for asxos (rev 2)

1. Close A-22 proof 2 with a fail-closed hook (SessionStart marker, PreToolUse `exit 2` on a missing guard, per-call log line, canary file, `if: always()` proof step, artifact upload; pass = three consecutive dispatched runs).
2. James merges the AGENTS.md amendment enabling auto-ready.
3. arbi builds the auto-ready mechanism (`issue-eligibility.yml`, readiness pass, picker changes, tests).
4. Arm the schedule after 1–3 (cron `0 16 * * *`, `concurrency`, `timeout-minutes`, `--max-turns`; commit the cron change as James).
5. Wire issue creation from claude.ai (custom connector, `needs-triage` only; Zapier fallback).
6. Contain other surfaces (read-only Supabase; remove or scope the Cursor GitHub App; no Slack tagging for builds).
7. Build the digest (cron `0 21 * * *`; merged, failed, auto-readied, declined, needs me).
8. Optional: one read-only morning routine summarising the digest.

### Confidence (rev 2)

High: routine triggers/limits; claude-code-action modes, trigger checks, token behaviour, output defaults, base-branch config restore; cloud-session isolation; hook exit-code semantics; Supabase MCP parameters; Cursor cloud-agent capabilities; the repo being public. Medium: routine caps; cloud sessions unable to push workflow files; Cowork connector reliability; the custom GitHub MCP connector and Zapier paths; the App token replacing the PAT. Unverified: how the action sets `CLAUDE_PROJECT_DIR`; whether the execution log records hook events; whether PreToolUse hooks run in cloud sessions and routines; whether `RUNNER_TEMP` is visible to hook subprocesses.
