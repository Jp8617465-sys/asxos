# Amendment J — the ready-grant escape (drafted for James to apply)

**Status:** drafted, NOT applied · **Author:** arbi · **Date:** 2026-09-05 (Sydney)
**Why it is a draft and not a commit:** arbi is mechanically unable to apply it. See §1.
**Applies to:** `.claude/ready-grant` (new), `.claude/hooks/pr-draft-guard.sh`,
`.claude/hooks/authority-guard.sh`, `tests/test_pr_draft_guard_mcp.py`

---

## 1. What happened, and why this is a draft

James granted a merge train (Amendment I, 2026-09-04) and then said *"I authorise you to
make drafts ready to merge."* That authorisation could not take effect:
`pr-draft-guard.sh:59-62` denies `update_pull_request draft:false` **unconditionally** —
the whole 123-line hook has exactly one env conditional (line 86, `ARBI_UNATTENDED`,
gating merge), and the draft deny is not it. `gh pr ready` and `gh api PATCH .../pulls`
are closed too (`push-guard.sh:161-162`, `:168-169`). **Fifth recorded instance of "an
authorisation changes intent, never capability"** (`decision-log.md` 2026-08-22 logs four).

Asked how to proceed, James chose *"Authorise me to edit the hook"* over clicking Ready.
arbi attempted the edit below and was **denied by the Claude Code auto-mode classifier** —
a layer above both James's grant and the repo's own guard lists.

**This is the 2026-08-23 inversion, repeated and now load-bearing.** That row records the
repo *granting* capability while a different layer withheld it. Here the repo does not even
guard the path — `.claude/hooks/` is in neither `permissions.deny` nor
`AUTHORITY_FRAGMENTS`, only in the advisory-and-inert `.github/CODEOWNERS` — and the
**harness independently enforced §10.2 anyway** ("an agent must not edit its own permission
surface"). Three layers were asked; the only one that held was the one nobody configured.

Two consequences worth keeping:

1. **The `.claude/hooks/` coverage gap is real but not currently agent-exploitable.** It
   should still be closed (§4) — relying on a harness classifier that is outside this
   repo's control is not the same as a control this repo owns.
2. **No workaround was attempted.** Not via `sed`, not via a heredoc, not via the GitHub
   API. Same boundary through a different tool is the same boundary — the standing
   position quoted verbatim in `decision-log.md` 2026-08-25.

---

## 2. Design — and why it is a guarded file, not an env var

**The constraint: an escape arbi can trigger itself is not a control.** Two obvious designs
fail on it and are rejected:

| Rejected | Why |
|---|---|
| `ARBI_READY_GRANT=1` env var, mirroring line 86 | A shell `export` does not survive into the hook's environment, so arbi could not set it even if allowed; and a `settings.json` `env:` entry makes it a **standing** grant — strictly worse than the per-session gate it replaces. |
| A plain sentinel file | arbi could write it. Self-granting is not a gate. |

**Chosen:** the grant lives in `.claude/ready-grant`, added to `AUTHORITY_FRAGMENTS` so
only James can write it. The hook only ever reads it. James writes one line instead of
fifteen clicks, and the key stays in his hands.

**Honest cost/benefit.** This does **not** save James effort on the current train — writing
the grant ≈ clicking Ready fifteen times. It pays off on *future* trains. If he would
rather not carry the machinery, clicking Ready remains strictly simpler and nothing below
needs to exist.

---

## 3. Patch 1 — new file `.claude/ready-grant`

```
# .claude/ready-grant — JAMES ONLY. Guarded by authority-guard.sh; arbi reads, never writes.
#
# Lists the PRs arbi may un-draft (mcp__github__update_pull_request with draft:false).
# Everything not listed stays denied. Absent file, absent expiry, or a past expiry voids
# the whole file. Never honoured under ARBI_UNATTENDED=1.
#
#   expires: YYYY-MM-DD    required, Sydney wall-clock, whole-file scope
#   prs: 185 186 187       space-separated; multiple prs: lines accumulate
#
# Amendment J. Delete the directives (or let the date lapse) to close the window.

expires: 2026-09-06
prs: 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200
```

## 4. Patch 2 — `.claude/hooks/pr-draft-guard.sh`

Insert after `state_field()` (currently line 50):

```bash
pr_number() {
  printf '%s' "$payload" | jq -r '.tool_input.pullNumber // empty'
}

# --- Amendment J (James, 2026-09-04): the ready-grant --------------------------------
#
# THE DESIGN CONSTRAINT, and the reason this is not an env var: an escape the agent can
# trigger itself is not a control. A shell `export` does not survive into this hook's
# environment, and a settings.json `env:` entry would be a STANDING grant. A plain
# sentinel file is worse still — the agent could write it and self-grant.
#
# So the grant lives in `.claude/ready-grant`, which authority-guard.sh lists in
# AUTHORITY_FRAGMENTS. Only James can write it. This hook only ever reads it.
#
# Resolved relative to THIS SCRIPT, not $CLAUDE_PROJECT_DIR or the payload cwd — the
# script's own location is the one path correct under the harness AND under a bare
# `bash .claude/hooks/pr-draft-guard.sh` in a test, with no env setup.
ready_grant_allows() {
  local pr="$1" file expiry today list
  [ -n "$pr" ] || return 1
  file="$(dirname "$0")/../ready-grant"
  [ -f "$file" ] || return 1

  expiry="$(sed -n 's/^[[:space:]]*expires:[[:space:]]*\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\).*/\1/p' "$file" | head -1)"
  [ -n "$expiry" ] || return 1
  # The repo reckons wall-clock dates in Sydney, not on the UTC runner (asxos/clock.py,
  # PR #171). A grant must not outlive its date because the runner is still on yesterday.
  today="$(TZ=Australia/Sydney date +%F 2>/dev/null)" || return 1
  [ "$today" \> "$expiry" ] && return 1   # ISO-8601 compares correctly as strings

  list=" $(sed -n 's/^[[:space:]]*prs:[[:space:]]*//p' "$file" | tr '\n' ' ') "
  case "$list" in
    *" $pr "*) return 0 ;;
  esac
  return 1
}
```

Then replace the `*update_pull_request)` draft deny (currently lines 60-62):

```bash
    d="$(draft_state)"
    if [ "$d" = "false" ]; then
      pr="$(pr_number)"
      # Order matters: unattended is checked FIRST, so no grant can ever authorise an
      # un-draft in a session nobody is watching.
      [ "${ARBI_UNATTENDED:-0}" = "1" ] \
        && deny "pr-draft-guard: un-drafting never happens unattended (ARBI_UNATTENDED=1); the ready-grant is void in this mode."
      ready_grant_allows "$pr" \
        || deny "pr-draft-guard: update_pull_request with draft:false un-drafts a PR — blocked. Draft PRs are the ceiling; James marks ready. PR #${pr:-?} is not in an unexpired .claude/ready-grant (Amendment J)."
    fi
```

The `state: open|closed` deny below it is **unchanged**.

## 5. Patch 3 — `.claude/hooks/authority-guard.sh`

Add two fragments to `AUTHORITY_FRAGMENTS` (currently lines 60-76):

```bash
  ".claude/hooks/" ".claude/ready-grant"
```

The first closes the coverage gap this whole episode exposed; the second is what makes
Patch 2 a control rather than a self-grant. **Apply this patch LAST** — once
`.claude/hooks/` is a guarded fragment, further hook edits are blocked, including a fix to
Patch 2.

Still James's and deliberately not drafted here: the matching `Edit(/.claude/hooks/**)`
line in `settings.json`'s `permissions.deny`. That file is CODEOWNED and is arbi's own
permission surface.

## 6. Patch 4 — `tests/test_pr_draft_guard_mcp.py`

Four behaviours to pin, in the existing `TestPrLifecycle` style (`run_hook` already takes
`unattended=`; these need a `tmp_path`-style fixture that writes a `.claude/ready-grant`
into a copied tree, since the helper resolves the grant relative to the hook):

| Test | Expectation |
|---|---|
| listed PR, attended, unexpired grant | silent (allowed) |
| unlisted PR, same grant | denied, reason contains `ready-grant` |
| listed PR under `ARBI_UNATTENDED=1` | denied, reason contains `unattended` |
| listed PR, `expires:` in the past — and separately, no grant file at all | denied |

The existing `test_undraft_denied` (PR 147) stays valid as-is: 147 is in no grant, so it
must still deny. That is the regression anchor — if it ever goes silent, the gate is off.

---

## 7. What James does

1. Apply Patches 1, 2, 4, then 3 (order matters — §5).
2. Run `pytest tests/test_pr_draft_guard_mcp.py`.
3. Add `Edit(/.claude/hooks/**)` to `settings.json` `permissions.deny`.
4. Tell arbi the grant is live; the train then runs without further clicks.

**Or skip all of it and click Ready on the 15 PRs.** That path needs no new machinery, no
new control surface, and is faster today. Amendment J only wins from the second train on.
