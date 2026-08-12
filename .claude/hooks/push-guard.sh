#!/usr/bin/env bash
# push-guard.sh — PreToolUse(Bash) guard, always-on (not ARBI_UNATTENDED-gated).
#
# DENY-ONLY, DELIBERATELY. Correction (security-engineer, 2026-07-14, verified against a
# raw fetch of code.claude.com/docs/en/hooks — the "PreToolUse decision control" section):
# permissionDecision:"allow" IS documented to skip the permission prompt, with a narrow
# carve-out for tools that require user interaction (AskUserQuestion/ExitPlanMode) — Bash and
# the GitHub MCP write tools are NOT in that carve-out. So an allow-emitting hook for a
# verified-safe shape (a claude/**-scoped push, a draft:true PR create) would in fact have
# suppressed the prompt. (Caveat: this is confirmed for the Claude Code CLI the docs
# describe; this session runs under the Claude Agent SDK harness, where the identical
# mechanism is assumed, not independently re-verified.)
#
# This hook is still deny-only anyway — for a better reason than "unconfirmed docs":
# ASYMMETRIC RISK. A false-negative in a regex meant to ALLOW a safe shape silently executes
# a dangerous action with zero human check. A false-negative in a regex meant to DENY a
# dangerous shape merely falls through to the existing prompt — a human still gets a chance
# to catch it. Given every regex here is admittedly imperfect (see HONEST LIMITS below),
# only the fail-safe direction is acceptable for anything push/merge-adjacent. Push/PR
# creation friction is therefore NOT eliminated by this hook; only the dangerous shapes are
# mechanically hard-blocked regardless of how a human answers the prompt.
#
# Scope: `git push` destined at a protected ref (main/master) with force or delete, any
# repo-wide push (--mirror/--all/--tags), and the `gh` CLI shapes that would let a Bash
# command bypass the MCP-level PR/merge denies (gh pr merge/ready, gh pr create without
# --draft, gh api POST/PUT/PATCH/DELETE to pulls/merge, non-validation gh workflow mutation,
# release mutation). Attended Claude Execute may dispatch only validation-only workflows:
# full-check.yml, targeted-ml-tests.yml, and migration-integration.yml.
#
# HONEST LIMITS (same class as unattended-guard.sh's, see its header): Bash is not fully
# parseable. A non-`git`/`gh` code path — a Python/Node script invoked via a pre-allowed
# test runner (pytest/make check/mypy) calling `subprocess.run(["git","push",...])` or the
# GitHub REST API directly — is invisible to this hook entirely; it never produces a `git
# push` or `gh` command string. The mechanical backstop for THAT path is GitHub branch
# protection on `main` (confirmed NOT configured as of 2026-07-11) — not this hook. Variable
# indirection (`r=main; git push origin HEAD:$r`), git aliases, and exotic quoting can also
# defeat the regexes below; matched shapes are denied, unmatched ones fall through to a
# prompt (safe direction — never a silent allow of something this hook failed to parse).
set -uo pipefail

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  fi
  exit 0
}

# Fail-open on a missing jq: this is a speed-bump layered on top of the real backstop
# (branch protection), not itself the boundary — consistent with review-gate.sh's contract.
command -v jq >/dev/null 2>&1 || exit 0

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"
[ "$tool" = "Bash" ] || exit 0

cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
[ -n "$cmd" ] || exit 0

# --- git push shapes -----------------------------------------------------------------

PUSHSEG='\bgit\b[^|;&]*\bpush\b[^|;&]*'

if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}(--mirror\\b|--all\\b|--tags\\b|--follow-tags\\b)"; then
  deny "push-guard: a repo-wide push (--mirror/--all/--tags) is blocked — it can push every ref including main. Push a single claude/** branch explicitly."
fi
# Wildcard refspec is the flag-free equivalent of --mirror/--all (security-engineer,
# 2026-07-14: `git push origin '+refs/heads/*:refs/heads/*'` pushes every local branch,
# including main if it exists locally, with no --all/--mirror token to catch).
if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}refs/heads/\\*"; then
  deny "push-guard: a wildcard refspec (refs/heads/*) is blocked — same effect as --all/--mirror, push a single claude/** branch explicitly."
fi
# `remote.<name>.push` config (via `git config` or `git -c`) has no legitimate use in
# reversible branch work and can retarget a plain `git push origin` to anything, including a
# wildcard or main — deny outright regardless of the value, rather than try to parse it.
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*(config[^|;&]*remote\.[^|;&]*\.push\b|-c[[:space:]]+remote\.[^|;&]*\.push=)'; then
  deny "push-guard: setting git's remote.*.push config is blocked — it can silently retarget a plain 'git push' to main or every branch. Push with an explicit claude/** refspec instead."
fi
# `-C <dir>` / `--git-dir=` / `--work-tree=` redirects git at a different checkout than the
# one this hook can inspect (its branch/refspec checks only ever look at $CLAUDE_PROJECT_DIR)
# — deny any push combined with a repo-redirect flag rather than risk validating the wrong
# tree (security-engineer, 2026-07-14: confirmed a same-branch-is-main check bypass via -C).
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*(-C[[:space:]]|--git-dir=|--work-tree=)[^|;&]*\bpush\b|\bgit\b[^|;&]*\bpush\b[^|;&]*(-C[[:space:]]|--git-dir=|--work-tree=)'; then
  deny "push-guard: a push combined with -C/--git-dir/--work-tree targets a repo this hook cannot verify — blocked. Push from the project directory directly."
fi

# Colon-refspec delete of a protected ref: `:main`, `:refs/heads/main`.
if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}(^|[[:space:]]):[[:space:]]*(refs/heads/)?(main|master)\\b"; then
  deny "push-guard: deleting the remote main/master ref is blocked."
fi
# --delete / -d targeting main/master.
if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}(--delete\\b|[[:space:]]-[A-Za-z]*d([[:space:]]|$))[^|;&]*(refs/heads/)?(main|master)\\b"; then
  deny "push-guard: deleting the remote main/master ref is blocked."
fi

is_force() {
  printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}(--force\\b|--force-with-lease\\b|[[:space:]]-[A-Za-z]*f([[:space:]]|$))"
}

# Positional or colon-refspec destination naming main/master, case-insensitive.
targets_main() {
  printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}(:[[:space:]]*(refs/heads/)?(main|master)\\b|[[:space:]](refs/heads/)?(main|master)([[:space:]:]|\$))"
}

if targets_main; then
  if is_force; then
    deny "push-guard: force-push to main/master is blocked (this is the #29-incident shape — branch reconstruction must never force-push a protected ref)."
  fi
  deny "push-guard: push to main/master is blocked here. Push a claude/** branch and open a draft PR — merging to main is James's step."
fi

# Any push while the checked-out branch IS main/master, regardless of the refspec argument
# (mirrors unattended-guard.sh's A1: distinguishing "bare" from "explicit-but-still-main" is
# not reliably parseable in bash, so this over-denies a rare same-branch-explicit-push case
# rather than risk under-denying — safe direction, matches existing house convention).
if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}"; then
  cur="$(git -C "${CLAUDE_PROJECT_DIR:-.}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  case "$cur" in
    main|master) deny "push-guard: pushing while checked out on $cur risks pushing to main/master. Work on a claude/** branch." ;;
  esac
fi

# --- gh CLI shapes that bypass the MCP-level PR/merge denies -------------------------

if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge'; then
  deny "push-guard: 'gh pr merge' is blocked — merge is James's step, never the agent's, via any surface."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[^|;&]*(--merge\b|--auto\b|--admin\b)'; then
  deny "push-guard: gh pr auto-merge/admin-merge flags are blocked."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+ready'; then
  deny "push-guard: 'gh pr ready' un-drafts a PR — blocked. Draft PRs are the ceiling; James marks ready."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+create' \
   && ! printf '%s' "$cmd" | grep -Eiq -- '--draft\b'; then
  deny "push-guard: 'gh pr create' without --draft is blocked — every agent-opened PR must be draft:true."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+api[^|;&]*(--method|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)[^|;&]*/(pulls|merge)\b'; then
  deny "push-guard: 'gh api' mutating a pulls/merge endpoint directly is blocked — the same PR/merge policy applies regardless of surface."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+workflow[[:space:]]+(enable|disable)'; then
  deny "push-guard: enabling/disabling workflows via gh is blocked (I6), reserved to James."
fi
workflow_run_segments="$(printf '%s' "$cmd" | grep -Eio 'gh[[:space:]]+workflow[[:space:]]+run[^|;&]*' || true)"
if [ -n "$workflow_run_segments" ]; then
  while IFS= read -r workflow_run_segment; do
    [ -n "$workflow_run_segment" ] || continue
    if ! printf '%s' "$workflow_run_segment" | grep -Eiq '^gh[[:space:]]+workflow[[:space:]]+run[[:space:]]+(full-check\.yml|targeted-ml-tests\.yml|migration-integration\.yml)([[:space:]]|$)'; then
      deny "push-guard: workflow_dispatch is allowed only for validation-only workflows (full-check.yml, targeted-ml-tests.yml, migration-integration.yml). Production/secret-bearing workflow runs are reserved to James."
    fi
  done <<EOF
$workflow_run_segments
EOF
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+release[[:space:]]+(create|edit|delete)'; then
  deny "push-guard: release mutation via gh is blocked (I6), reserved to James."
fi

exit 0
