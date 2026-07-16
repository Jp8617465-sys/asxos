# Hook-matcher inertness in the web/remote environment — finding + fix

**Status:** proposed (draft PR for James to review + apply)
**Date:** 2026-07-16
**Risk:** R16 (sharpens R5) — `docs/product/risk-register.md`
**Owner:** James applies the `.claude/settings.json` change (authority path, session-denied to arbi)

---

## The finding

Three of the five PreToolUse guards in `.claude/settings.json` use `"matcher": ".*"`
(`authority-guard.sh`, `pr-draft-guard.sh`, `unattended-guard.sh`). **In this web/remote
Claude Code environment they do not fire.** The two that use `"matcher": "Bash"`
(`review-gate.sh`, `push-guard.sh`) fire correctly.

### Evidence (decisive)

1. **Probe:** `python3 -c "print('render.yaml — writes nothing')"` matches BOTH of
   `authority-guard.sh`'s regexes (`render\.yaml` in `authority_ref`, `python3 ` in
   `write_verb`) — if the hook were executing it would emit a `deny`. It **printed instead**.
   A `.*`-matcher hook did not fire on a Bash command that a `"Bash"`-matcher hook (`review-gate`)
   provably fires on. → the discriminator is the **matcher value**, not the tool type.
2. **Natural experiment:** `mcp__github__update_pull_request` with `draft:false` (un-drafting
   PRs #42/#46/#47) **succeeded** this session. `pr-draft-guard.sh` denies exactly that — it
   was not firing.
3. **Counter-case:** `review-gate.sh` denials (its verbatim "stage the Python separately"
   text) fired repeatedly → `"Bash"`-matcher hooks execute.

### Root cause (authoritative — `claude-code-guide`, official docs, 2026-07-16)

- **MCP tools are absent from PreToolUse's documented "Supported Tools" list**
  (Bash, Write, Edit, Read, Glob, Grep, WebFetch, WebSearch, Agent, AskUserQuestion,
  ExitPlanMode). So **no PreToolUse hook can gate an `mcp__*` call**, regardless of matcher —
  this alone explains `pr-draft-guard` never intercepting `update_pull_request`.
- But that does not explain `authority-guard` failing on a **Bash** command (Bash is
  supported). The probe isolates it: **this harness does not honor `.*` as a catch-all**;
  only exact/pipe-delimited matchers fire. So all three `.*` hooks are dark, including the
  Bash/Edit-tool parts that *should* be hookable.
- Docs confirm there is *supposed* to be no local-vs-web hook difference
  ("your repo's `.claude/settings.json` hooks carry over — part of the clone"), so this is a
  matcher-semantics gap in this environment, not hooks-disabled.

---

## What is / isn't at risk

**Still enforced — attended posture holds** (permission-system, not hooks):
- The `deny` RULES (`.claude/**`, `migrations/`, `render.yaml`, memory files, `.env`,
  `enable_pr_auto_merge`) — they blocked `.claude/**` edits this session, citing the rule.
- `review-gate.sh` + `push-guard.sh` (`"Bash"` matcher).
- The auto-mode classifier.

**Dark in this environment:**
- **Draft-PR ceiling** (`pr-draft-guard`, MCP-only) — not mechanically enforced; rests on the
  permission prompt + arbi behavior. Attended, James sees a bad PR; not a hard block.
- **`authority-guard`'s interpreter-write + symlink residual** (the `python3 -c
  "open('CLAUDE.md','w')"` class) — dark. The deny RULES don't cover interpreter subprocess
  writes (documented carve-out) and the hook isn't firing. Blast radius single-user; a commit
  still hits the review gate.
- **`unattended-guard`'s entire mechanical layer** — DB-write / merge / push-to-main / secret
  / MCP-write blocks — **IF scheduled Routines run in this same harness.** This is the
  load-bearing 7b (unattended write authority) gating input. Its own header already concedes
  "the REAL mechanical backstops are GitHub branch protection and the R2 read-only Postgres
  role" — both currently not-in-place (branch protection plan-gated per R5; 0039 RO role
  applied 2026-07-16 but the agent-MCP re-point is pending).

---

## The fix

### 1. Explicit-matcher patch (safe to apply wholesale)

Replace the `".*"` matcher on the PreToolUse group with an explicit tool list:

```
"matcher": ".*"   →   "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash"
```

- **No-regression guarantee:** `.*` already does nothing here, so worst case the new matcher
  is also inert (no change). Best case it revives `authority-guard` fully and
  `unattended-guard`'s hookable (Bash/Edit) parts.
- **No new false-denies attended:** `authority-guard` only denies authority paths (already
  deny-ruled); `unattended-guard` is a no-op unless `ARBI_UNATTENDED=1`; `pr-draft-guard`
  hits its default `exit 0` on Edit/Bash.

The complete proposed `.claude/settings.json` (this matcher fix + the 19→16 allowlist
expansion from the permission-friction work + the `PermissionRequest`/`PermissionDenied`
logging hooks) is attached to this PR as `proposed-settings-v3.json` — jq-validated:
allow=38, deny=39 (unchanged), 5 PreToolUse guards preserved, both logging hooks wired,
zero `.*` matchers remaining.

**Confirm after applying:** re-run the probe
`python3 -c "print('render.yaml')"` — if it now **denies** with the authority-guard message,
the Bash/Edit hooks are revived. (`pr-draft-guard`'s MCP block stays dark regardless — see #2.)

### 2. MCP protections → permission `deny` rules (the officially-recommended mechanism)

MCP tools can't be hooked, so the draft ceiling / merge guards must be `deny` rules, which
*are* enforced here:
- `enable_pr_auto_merge` — already a bare-name `deny`. ✓ pattern to extend.
- Draft ceiling: try the documented param-deny `mcp__github__update_pull_request(draft:false)`
  — blocks un-drafting without breaking attended draft *creation*. (Verify this harness
  honors parameter-value deny syntax; docs flag it as not universal.)
- **Do NOT** bare-deny `mcp__github__merge_pull_request` in the shared (attended) settings —
  that re-breaks the James-instructed attended merge pattern (R15). The unattended merge block
  belongs in the unattended profile (#3), not here.

### 3. 7b (unattended write authority) — do not rely on these hooks

Before enabling any standing unattended write tier, either (a) #1 revives the hooks **in the
Routine's actual runtime** (verify there, not just attended), or (b) the unattended session
launches with a dedicated settings profile whose `deny` array hard-denies the write surface
(merge / push / DB-write MCP / Render / secret), enforced by the permission system rather than
`ARBI_UNATTENDED`-gated hooks — **plus** the real backstops (branch protection, RO-role
re-point) land. This is a design task for the 7b slice, flagged here, not built in this PR.

---

## Scope of this PR

- `docs/product/risk-register.md` — adds **R16** (cross-referenced to R5).
- `docs/proposals/hook-matcher-fix-2026-07-16.md` — this doc.
- **Attached, not committed:** `proposed-settings-v3.json` — the ready-to-paste
  `.claude/settings.json` (arbi is deny-listed from editing `.claude/settings.json` directly;
  applying it is James's step). Items #2 and #3 are recommendations for James to decide, not
  baked into v3.
