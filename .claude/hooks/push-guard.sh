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
# repo-wide push (--mirror/--all/--tags), and the `gh` CLI shapes that would bypass the
# server-gated PR lifecycle. PR create/ready/squash-merge may fall through only when this
# hook resolves the exact ASXOS origin and reads remote repository variable
# `AUTONOMY=STANDING`. Lookup failure is ATTENDED. This state read is feedback, not the
# enforcement boundary: `risk-classify` and branch protection remain authoritative.
# Direct PR API mutation, non-allowlisted workflow mutation, and release mutation remain
# denied. Dispatchable workflows are allowlisted per segment below:
# the validation lanes (full-check.yml, targeted-ml-tests.yml, migration-integration.yml)
# plus — James's 2026-08-12 guard-carveouts decision — backup.yml (reads prod, restores
# into a disposable container) and claude-execute.yml (the governed harness, which
# carries its own tool ceiling). Everything else stays reserved to James.
#
# HONEST LIMITS (same class as unattended-guard.sh's, see its header): Bash is not fully
# parseable. A non-`git`/`gh` code path — a Python/Node script invoked via a pre-allowed
# test runner (pytest/make check/mypy) calling `subprocess.run(["git","push",...])` or the
# GitHub REST API directly — is invisible to this hook entirely; it never produces a `git
# push` or `gh` command string. The mechanical backstop for THAT path is GitHub branch
# protection on `main` — live since 2026-07-17 as two rulesets (PR required, `full-check`
# required, deletion and non-fast-forward blocked) and re-asserted 2026-08-12 as classic
# protection with the same shape. Caveat that matters: `enforce_admins:false`, so a token
# acting as a repo admin bypasses all of it — see the PAT note in claude-execute.yml.
# Not this hook. Variable
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

# PR lifecycle commands are project-allowlisted, so silence can execute without another
# prompt. Payload classification must fail closed when jq is unavailable.
command -v jq >/dev/null 2>&1 \
  || deny "push-guard: jq unavailable; refusing GitHub/push classification (fail-closed)."

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"
[ "$tool" = "Bash" ] || exit 0

cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
[ -n "$cmd" ] || exit 0

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
  state="$("$gh_bin" variable get AUTONOMY --repo "$EXPECTED_REPO" 2>/dev/null || true)"
  [ "$state" = "STANDING" ]
}

pr_context_is_asxos() {
  local root="${CLAUDE_PROJECT_DIR:-}"
  local call_cwd root_real cwd_real
  [ -n "$root" ] && [ -d "$root" ] || return 1
  root_real="$(realpath "$root" 2>/dev/null || true)"
  call_cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty')"
  [ -n "$call_cwd" ] || call_cwd="$root"
  cwd_real="$(realpath "$call_cwd" 2>/dev/null || true)"
  case "$cwd_real" in "$root_real"|"$root_real"/*) ;; *) return 1 ;; esac
  case "${GH_REPO:-}" in ""|"$EXPECTED_REPO") ;; *) return 1 ;; esac
  # A lifecycle call must resolve from this checkout. Explicit repo/host overrides,
  # URLs and command substitution could redirect the pre-allowed command elsewhere.
  ! printf '%s' "$cmd" | grep -Eiq '(^|[[:space:]])(-R|--repo|--hostname)([=[:space:]]|$)|GH_REPO=|github\.com/|\$\(|`|<\('
}

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
# `-C <dir>` / `--git-dir=` / `--work-tree=` redirects git at a checkout this hook cannot
# inspect. Since 2026-08-20 the branch check below reads every checkout the payload's own
# `.cwd` and $CLAUDE_PROJECT_DIR identify, so an ordinary worktree IS inspected correctly —
# but a redirect FLAG names a THIRD tree that neither root identifies, and the flag's
# argument is not reliably parseable out of a Bash string. Keep denying any push combined
# with a repo-redirect flag rather than risk validating the wrong tree (security-engineer,
# 2026-07-14: confirmed a same-branch-is-main check bypass via -C). The cwd resolution does
# NOT make this deny redundant — do not remove it.
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
  deny "push-guard: direct push to main/master is blocked in every autonomy state. Push an agent branch and use the server-gated PR path."
fi

# Any push while the checked-out branch IS main/master, regardless of the refspec argument
# (mirrors unattended-guard.sh's A1: distinguishing "bare" from "explicit-but-still-main" is
# not reliably parseable in bash, so this over-denies a rare same-branch-explicit-push case
# rather than risk under-denying — safe direction, matches existing house convention).
if printf '%s' "$cmd" | grep -Eiq "${PUSHSEG}"; then
  # Read the branch of EVERY checkout this push could plausibly run in, and deny if
  # ANY of them is main/master. Two roots, because either can be the real one:
  #   - the payload's own cwd — a worktree has its own HEAD, and anchoring only to
  #     $CLAUDE_PROJECT_DIR let a worktree sitting on main slip this check;
  #   - $CLAUDE_PROJECT_DIR — because the command may relocate (`cd <primary> &&
  #     git push`), in which case the payload cwd is NOT where git ends up.
  # Checking only the payload cwd would trade the first hole for the second; testing
  # both strictly widens the guarded set relative to either alone.
  # NOTE the residual: a `cd` into a THIRD checkout that is on main, while neither
  # root is, is still not caught — `cd` is not reliably parseable out of a Bash
  # string, and the explicit-refspec checks above plus branch protection on the
  # server are what bound it. The -C/--git-dir/--work-tree deny above covers only
  # the FLAG form of a redirect; do not read it as covering `cd`.
  push_cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty')"
  [ -n "$push_cwd" ] && [ -d "$push_cwd" ] || push_cwd=""
  for _root in "$push_cwd" "${CLAUDE_PROJECT_DIR:-}"; do
    [ -n "$_root" ] || continue
    cur="$(git -C "$_root" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
    case "$cur" in
      main|master) deny "push-guard: pushing while a relevant checkout ($_root) is on $cur risks pushing to main/master. Work on a claude/** branch." ;;
    esac
  done
fi

# --- gh CLI shapes that bypass the MCP-level PR/merge denies -------------------------

# The target policy is squash-only and forbids auto/admin merge in every state.
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[^|;&]*(--merge\b|--rebase\b|--auto\b|--admin\b)'; then
  deny "push-guard: non-squash, auto, and admin merge modes are blocked in every autonomy state."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge'; then
  printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge[^|;&]*--squash([[:space:]]|$)' \
    || deny "push-guard: 'gh pr merge' requires an explicit --squash flag; the repository default is not trusted."
  pr_context_is_asxos && autonomy_is_standing \
    || deny "push-guard: 'gh pr merge' requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED stops at a draft PR."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+ready'; then
  pr_context_is_asxos && autonomy_is_standing \
    || deny "push-guard: 'gh pr ready' requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED stops at a draft PR."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+create' \
   && ! printf '%s' "$cmd" | grep -Eiq -- '--draft\b'; then
  pr_context_is_asxos && autonomy_is_standing \
    || deny "push-guard: a non-draft PR requires remote AUTONOMY=STANDING for the exact ASXOS origin; ATTENDED PRs must use --draft."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+variable[[:space:]]+(set|delete)[[:space:]]+AUTONOMY\b'; then
  deny "push-guard: direct AUTONOMY mutation is blocked; only the attested State Controller workflow may change it."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+api[^|;&]*(--method|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)[^|;&]*/actions/variables/AUTONOMY\b'; then
  deny "push-guard: direct AUTONOMY API mutation is blocked; only the attested State Controller workflow may change it."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+api[^|;&]*(--method|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)[^|;&]*/(pulls|merge)\b'; then
  deny "push-guard: 'gh api' mutating a pulls/merge endpoint directly is blocked — the same PR/merge policy applies regardless of surface."
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+workflow[[:space:]]+(enable|disable)'; then
  deny "push-guard: enabling/disabling workflows via gh is blocked (I6), reserved to James."
fi
# Per-segment dispatch allowlist, two tiers. Extended 2026-08-12 (James,
# guard-carveouts decision): backup.yml and claude-execute.yml join the
# validation lanes, UNCONDITIONALLY dispatchable regardless of AUTONOMY —
# backup.yml only reads prod (pg_dump) and restores into a disposable CI
# container; claude-execute.yml is the governed harness whose own workflow
# definition carries the tool ceiling, and the action's anti-tamper check
# refuses to run any non-main modification of it.
#
# Extended again 2026-09-08 (James, default-allow inversion): daily-brief.yml,
# us-positions.yml and weekly-research.yml become dispatchable once
# AUTONOMY=STANDING — they write production data, send email, and spend paid
# API quota, so they're a second, narrower tier gated on the same switch that
# gates merge, not folded into the unconditional base tier. This is a
# knowing, named acceptance of a narrow irreversibility (a sent email can't be
# unsent; committed quota spend can't be refunded) — production DB writes
# themselves are the PITR-gated case this PR's own merge requires James to
# confirm. All other dispatches stay denied in every state.
#
# This allowlist is the patch, not the design: it is client-side only (one
# harness of three — Codex and Cursor do not run push-guard.sh), name-based
# (a workflow renamed or added here silently falls outside it, failing safe —
# denied — until this list is updated by hand), and superseded once item 5
# (a `production` GitHub environment with environment-scoped secrets) makes
# credential reachability itself the server-side gate, regardless of who
# dispatches. See the follow-up issue for that replacement design.
# Command substitution is NOT a segment separator, so the loop below would swallow an
# inner dispatch into an allowlisted outer segment — `gh workflow run backup.yml
# $(gh workflow run daily-brief.yml)` fires the DENIED workflow first, and the settings
# allow-rule prefix-matches the whole string so no prompt appears either (security-engineer,
# 2026-08-12, H2 — verified live against this hook). Refuse the combination outright rather
# than attempt to parse it.
if printf '%s' "$cmd" | grep -Eq '\$\(|`|<\(' \
   && printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+workflow[[:space:]]+run'; then
  deny "push-guard: a gh workflow dispatch combined with command substitution cannot be verified per-segment — blocked. Use literal arguments."
fi
# `gh run rerun` re-executes a PRIOR run with all its secrets re-injected — for up to 30
# days, on ANY workflow, including daily-brief (prod DB writes + email), us-positions
# (position alert email) and weekly-research (prod writes + API quota). It is a wider grant
# than the `gh workflow run` allowlist it was briefly bundled with, and it is not
# "read-triggering" in any sense (security-engineer, 2026-08-12, H1). Validation lanes can
# be re-run through the allowlisted `gh workflow run <lane>.yml --ref <branch>` instead.
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+run[[:space:]]+rerun'; then
  deny "push-guard: 'gh run rerun' re-executes a prior run with its secrets re-injected — blocked (I6). Re-dispatch an allowlisted workflow explicitly instead."
fi
workflow_run_segments="$(printf '%s' "$cmd" | grep -Eio 'gh[[:space:]]+workflow[[:space:]]+run[^|;&]*' || true)"
WORKFLOW_BASE_ALLOW='^gh[[:space:]]+workflow[[:space:]]+run[[:space:]]+(full-check\.yml|targeted-ml-tests\.yml|migration-integration\.yml|backup\.yml|claude-execute\.yml)([[:space:]]|$)'
WORKFLOW_STANDING_ALLOW='^gh[[:space:]]+workflow[[:space:]]+run[[:space:]]+(daily-brief\.yml|us-positions\.yml|weekly-research\.yml)([[:space:]]|$)'
if [ -n "$workflow_run_segments" ]; then
  while IFS= read -r workflow_run_segment; do
    [ -n "$workflow_run_segment" ] || continue
    if printf '%s' "$workflow_run_segment" | grep -Eiq "$WORKFLOW_BASE_ALLOW"; then
      : # unconditionally allowed, unchanged
    elif printf '%s' "$workflow_run_segment" | grep -Eiq "$WORKFLOW_STANDING_ALLOW"; then
      pr_context_is_asxos && autonomy_is_standing \
        || deny "push-guard: this workflow writes production data, sends email, or spends paid API quota — it requires remote AUTONOMY=STANDING for the exact ASXOS origin. ATTENDED-without-STANDING stops here."
    else
      deny "push-guard: workflow_dispatch is allowed only for the allowlisted workflows (full-check.yml, targeted-ml-tests.yml, migration-integration.yml, backup.yml, claude-execute.yml unconditionally; daily-brief.yml, us-positions.yml, weekly-research.yml once AUTONOMY=STANDING). Other workflow runs are reserved to James."
    fi
  done <<EOF
$workflow_run_segments
EOF
fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+release[[:space:]]+(create|edit|delete)'; then
  deny "push-guard: release mutation via gh is blocked (I6), reserved to James."
fi

exit 0
