#!/usr/bin/env bash
# pr-draft-guard.sh — PreToolUse guard, always-on. Enforces the draft-PR ceiling on the
# GitHub MCP PR-write tools.
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
  *)
    exit 0
    ;;
esac
