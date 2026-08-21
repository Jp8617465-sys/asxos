#!/usr/bin/env bash
# pr-draft-guard.sh — PreToolUse guard, always-on. Enforces the draft-PR ceiling on the
# GitHub MCP PR-write tools.
#
# ⚠️ WIRING IS THE CONTROL (2026-08-21). This hook's cases match MCP tool names
# (mcp__github__*), so it only fires if `.claude/settings.json` registers it under a
# matcher that MATCHES those names. From R13 until 2026-08-21 it was wired under
# `matcher: "Bash"` only — every case below was dead code, and a PR was un-drafted
# through the MCP server with no deny (found live; independently recorded the same hour
# by session 01YBEYvVFasrq89XhkncMKRD as a fourth R5/R16/R17 instance: the control
# exists and is not applying in this execution context). The fix is the
# `matcher: "mcp__.*"` block in settings.json; `tests/test_pr_draft_guard_mcp.py` pins
# both this hook's verdicts AND that wiring, so neither can silently regress alone.
#
# DENY-ONLY (see push-guard.sh's header for the full correction/rationale — updated
# 2026-07-14): the docs DO confirm permissionDecision:"allow" suppresses the prompt for
# Bash/MCP tools; this hook is deny-only anyway for the asymmetric-risk reason (a
# false-negative on a deny regex just falls through to the existing prompt; a false-negative
# on an allow regex silently executes). It only ever emits `deny` or stays silent (silence =
# normal permission flow, i.e. today's prompt).
#
# The jq `//` trap: `.tool_input.draft // empty` treats BOTH `false` and `null`/absent as
# "missing" — you cannot distinguish "explicitly ready" from "not touching draft," which
# matters for update_pull_request (an edit that doesn't touch draft must not be denied).
# This hook uses `has()` + exact boolean equality instead, so `draft:false`, `draft:null`,
# and absent-draft are each read as their true, distinct state.
set -uo pipefail

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  fi
  exit 0
}

command -v jq >/dev/null 2>&1 || exit 0

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"

# Presence-aware read: yields exactly "true" / "false" / "absent" — never conflates
# false with absent the way `// empty` would.
draft_state() {
  printf '%s' "$payload" | jq -r 'if (.tool_input|has("draft")) then (.tool_input.draft|tostring) else "absent" end'
}
state_field() {
  printf '%s' "$payload" | jq -r 'if (.tool_input|has("state")) then (.tool_input.state|tostring) else "absent" end'
}

case "$tool" in
  *create_pull_request)
    d="$(draft_state)"
    [ "$d" = "true" ] \
      || deny "pr-draft-guard: create_pull_request must be called with draft:true. Every agent-opened PR is draft-only — James marks it ready."
    exit 0
    ;;
  *update_pull_request)
    d="$(draft_state)"
    [ "$d" = "false" ] \
      && deny "pr-draft-guard: update_pull_request with draft:false un-drafts a PR — blocked. Draft PRs are the ceiling; James marks ready."
    s="$(state_field)"
    case "$s" in
      open|closed) deny "pr-draft-guard: update_pull_request with state:$s (close/reopen) is blocked. That lifecycle action is James's." ;;
    esac
    exit 0
    ;;
  *enable_pr_auto_merge)
    # Auto-merge is forbidden in EVERY mode, attended or unattended — it removes the
    # per-PR, James-instructed merge decision this policy exists to preserve. Redundant
    # with the settings.json bare-tool-name deny (which removes the tool from context
    # entirely) — kept here too so a settings edit can't silently re-open auto-merge;
    # a second, independent layer.
    deny "pr-draft-guard: enable_pr_auto_merge is blocked in every mode. Auto-merge removes James's per-PR merge decision."
    ;;
  *merge_pull_request)
    # Attended/unattended split (2026-07-14 follow-up: PR #39 overcorrected by denying
    # merge everywhere, which also removed James-INSTRUCTED merge execution in live
    # attended sessions — re-check green/clean, confirm not draft, James names the PR,
    # agent calls the tool). Policy: agent-INITIATED merge stays forbidden (an
    # instruction-level rule — the agent only calls this when James explicitly named
    # the PR and said merge); unattended merge stays mechanically denied here. In an
    # attended session this falls through SILENTLY — no hook-level allow is emitted,
    # so the normal tool-permission prompt / user-instruction flow still applies.
    [ "${ARBI_UNATTENDED:-0}" = "1" ] \
      && deny "pr-draft-guard: merge_pull_request is blocked in unattended mode (ARBI_UNATTENDED=1). Merges happen only in live attended sessions on James's explicit per-PR instruction."
    exit 0
    ;;
  *create_or_update_file|*push_files|*delete_file)
    # Direct file mutation on a protected ref through the GitHub API — the MCP twin of
    # `git push` to main. push-guard.sh catches the Bash/gh shapes; until 2026-08-21
    # NOTHING caught this surface (not a hook-logic gap — the wiring gap above — but
    # while fixing the wiring, this shape was found to have no owner in any hook).
    # Branch-scoped writes stay silent deliberately: API commits to a claude/** branch
    # are the sanctioned route for DRAFTING authority-path changes into a reviewed PR
    # (authority-guard.sh's contract), and denying them here would close that route.
    # NOTE this hook may be the ONLY effective layer for this shape: main's branch
    # protection has enforce_admins:false, so an admin-scoped token committing via the
    # contents API is not necessarily stopped server-side (CLAUDE.md records this).
    #
    # ABSENT/EMPTY branch is DENIED, not ignored (security-engineer REQUIRED fix,
    # 2026-08-21): the GitHub contents API defaults an omitted branch to the repo's
    # DEFAULT branch — i.e. main. Today the MCP server's schema marks `branch`
    # required, so an omitted branch is rejected upstream — but silence here would
    # make this guard load-bearing on a third-party schema staying strict. There is
    # no legitimate absent-branch call: if the schema requires it the call fails
    # anyway; if it ever stops requiring it, the default is exactly what must be
    # denied. Fail closed (matches unattended-guard's unknown-tool doctrine).
    b="$(printf '%s' "$payload" | jq -r '.tool_input.branch // empty' | tr '[:upper:]' '[:lower:]')"
    [ -z "$b" ] \
      && deny "pr-draft-guard: file mutation with no branch named would land on the repository DEFAULT branch (main) via the GitHub API — blocked. Name a claude/** branch explicitly."
    case "$b" in
      main|master|refs/heads/main|refs/heads/master)
        deny "pr-draft-guard: direct file mutation on '$b' via the GitHub API is blocked — the MCP twin of pushing to main. Commit to a claude/** branch and open a draft PR; merging to main is James's step."
        ;;
    esac
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
