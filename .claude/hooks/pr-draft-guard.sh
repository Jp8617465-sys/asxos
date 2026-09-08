#!/usr/bin/env bash
# pr-draft-guard.sh — PreToolUse guard, always-on. Enforces the attended draft-PR
# ceiling and the standing server-gated PR lifecycle on GitHub MCP write tools.
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

command -v jq >/dev/null 2>&1 \
  || deny "pr-draft-guard: jq unavailable; refusing PR lifecycle classification (fail-closed)."

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"

EXPECTED_REPO="Jp8617465-sys/asxos"

autonomy_is_standing() {
  local root="${CLAUDE_PROJECT_DIR:-}"
  local origin state gh_bin
  [ -n "$root" ] && [ -d "$root" ] || return 1
  origin="$(git -C "$root" remote get-url origin 2>/dev/null || true)"
  case "$origin" in
    https://github.com/Jp8617465-sys/asxos|https://github.com/Jp8617465-sys/asxos.git|git@github.com:Jp8617465-sys/asxos|git@github.com:Jp8617465-sys/asxos.git) ;;
    *) return 1 ;;
  esac
  gh_bin="$(command -v gh 2>/dev/null || true)"
  [ -n "$gh_bin" ] || return 1
  case "$gh_bin" in "$root"/*) return 1 ;; esac
  case "${GH_REPO:-}" in ""|"$EXPECTED_REPO") ;; *) return 1 ;; esac
  state="$("$gh_bin" variable get AUTONOMY --repo "$EXPECTED_REPO" 2>/dev/null || true)"
  [ "$state" = "STANDING" ]
}

pr_payload_targets_asxos() {
  local owner repo
  owner="$(printf '%s' "$payload" | jq -r '.tool_input.owner // .tool_input.repository_owner // empty')"
  repo="$(printf '%s' "$payload" | jq -r '.tool_input.repo // .tool_input.repository // empty')"
  if [ -n "$owner" ] || [ -n "$repo" ]; then
    case "$repo" in
      "$EXPECTED_REPO")
        { [ -z "$owner" ] || [ "$owner" = "Jp8617465-sys" ]; } || return 1
        ;;
      asxos) [ "$owner" = "Jp8617465-sys" ] || return 1 ;;
      *) return 1 ;;
    esac
  fi
  return 0
}

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
    if [ "$d" != "true" ]; then
      pr_payload_targets_asxos && autonomy_is_standing \
        || deny "pr-draft-guard: a non-draft PR requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED PRs require draft:true."
    fi
    exit 0
    ;;
  *update_pull_request)
    d="$(draft_state)"
    if [ "$d" = "false" ]; then
      pr_payload_targets_asxos && autonomy_is_standing \
        || deny "pr-draft-guard: draft:false un-drafts a PR and requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED stops at draft."
    fi
    s="$(state_field)"
    case "$s" in
      open|closed)
        pr_payload_targets_asxos && autonomy_is_standing \
          || deny "pr-draft-guard: PR lifecycle state:$s requires remote AUTONOMY=STANDING for the exact ASXOS origin."
        ;;
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
    # The protected server decides Green versus current-head-approved Amber. The local
    # hook only keeps the pre-activation ceiling fail-closed.
    pr_payload_targets_asxos && autonomy_is_standing \
      || deny "pr-draft-guard: merge_pull_request requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED cannot merge."
    method="$(printf '%s' "$payload" | jq -r '.tool_input.merge_method // .tool_input.mergeMethod // empty' | tr '[:upper:]' '[:lower:]')"
    [ "$method" = "squash" ] \
      || deny "pr-draft-guard: merge_pull_request must explicitly use squash; merge, rebase, or an omitted method is blocked."
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
