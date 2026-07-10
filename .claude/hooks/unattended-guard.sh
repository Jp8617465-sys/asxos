#!/usr/bin/env bash
# unattended-guard.sh — PreToolUse guard for UNATTENDED arbi runs (ARBI_UNATTENDED=1).
#
# Mechanically blocks the irreversible infrastructure tiers (I5–I6) when no human is in the loop:
#   - push / merge / deploy to main; force-push; CI/release mutation  (I6)
#   - DB writes / migrations                                          (I5) — reads via mcp__supabase-ro__*
#   - Render mutations                                                (I5/I6)
#   - merging a PR                                                    (I6)
#   - edits to authority/boundary files (constitution self-edit)
#   - secret exposure
#   - write-capable / side-effecting MCP tools (GitHub/Supabase/external) — default-deny
#
# Fail-CLOSED for gated categories: a false deny just stops the run (the harness's own
# "when unsure, stop" behavior); a false allow is an irreversible crossing with no one
# watching. Attended sessions (ARBI_UNATTENDED unset) are a total no-op.
#
# Classification model: LOCAL read tools (Read/Glob/Grep/WebFetch/WebSearch/…) fall through
# to allow; write-capable MCP namespaces (github/supabase/external) DEFAULT-DENY with a small
# read allowlist; any unrecognized mcp__* tool is denied (can't prove it's read-only).
#
# HONEST LIMITS (docs/product/arbi-permission-model.md §Runtime enforcement honesty):
# this is a same-process pre-filter, NOT a boundary. Bash is not fully parseable — string
# indirection (r=main; git push $r), interpreter file writes, and curl-to-API calls cannot
# all be caught in-band; the execute_sql classifier is best-effort and the RO writer-function
# leak (SELECT some_writer_fn()) is only partially blacklisted. The REAL mechanical backstops
# are GitHub branch protection (merge/deploy/push-to-main) and the R2 read-only Postgres role
# (DB writes). This reduces risk R5 (prompt-only enforcement) from total to partial; it does
# not close it.
set -uo pipefail

# --- 1.0 arm only for unattended runs; attended → allow everything, instantly -----------
[ "${ARBI_UNATTENDED:-}" = "1" ] || exit 0

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  fi
  exit 0
}

# jq is required to classify safely; no guard => no unattended execution (fail closed).
command -v jq >/dev/null 2>&1 || deny "unattended-guard: jq unavailable; cannot verify the tool call is safe, so unattended execution is refused. Run attended or install jq in the Routine environment."

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"

# fail-closed: a payload we received but can't read a tool_name from is not proven safe.
[ -n "$payload" ] && [ -z "$tool" ] \
  && deny "unattended-guard: could not read tool_name from the PreToolUse payload; refusing to classify it as safe (fail-closed)."

is_authority_path() {
  case "$1" in
    CLAUDE.md|.claude/settings.json|.claude/settings.local.json|.claude/agents/arbi.md) return 0 ;;
    .claude/hooks/*) return 0 ;;
    docs/product/north-star.md|docs/product/arbi-constitution.md|docs/product/arbi-authority.md) return 0 ;;
    docs/product/arbi-permission-model.md|docs/product/arbi-scorecard.md|docs/product/arbi-promotion-gate.md) return 0 ;;
    docs/product/memory/approved-lessons.md|docs/product/memory/authority-lessons.md|docs/product/memory/project-facts.md) return 0 ;;
  esac
  return 1
}

rel_path() {
  local p="$1" root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  p="$(realpath -m -- "$p" 2>/dev/null || printf '%s' "$p")"
  root="$(realpath -m -- "$root" 2>/dev/null || printf '%s' "$root")"
  printf '%s' "${p#"$root"/}"
}

case "$tool" in
  Bash)
    cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
    # A1 — push/merge/deploy/CI to main (I6). Loose '\bgit\b … \bpush\b' matching so
    # global options (git -c x=y push, git --no-pager push, git -C . push) can't slip the
    # anchor; then look for force / main / master anywhere in the same command segment.
    printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*(--force|--force-with-lease|[[:space:]]-f([[:space:]]|$))' \
      && deny "unattended-guard: force-push is blocked (I6, never standing autonomy)."
    printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*(\b(main|master)\b|HEAD:(main|master))|:[[:space:]]*(main|master)\b' \
      && deny "unattended-guard: push to main/master = prod deploy (I6), reserved to James. Work on a claude/** branch and open a PR."
    if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b'; then
      cur="$(git -C "${CLAUDE_PROJECT_DIR:-.}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
      case "$cur" in main|master) deny "unattended-guard: bare 'git push' while on $cur = prod deploy (I6). Use a claude/** branch + PR." ;; esac
    fi
    printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge|\bgit\b[^|;&]*\bmerge\b|gh[[:space:]]+pr[^|;&]*(--merge|--auto|--admin)|gh[[:space:]]+workflow[[:space:]]+(run|enable|disable)|gh[[:space:]]+release[[:space:]]+(create|edit|delete)|gh[[:space:]]+api[^|;&]*(--method|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)|(curl|wget)[^|;&]*api\.github\.com[^|;&]*/merge' \
      && deny "unattended-guard: merge / CI / release mutation is blocked (I6), reserved to James."
    # A2 — DB writes via CLI
    printf '%s' "$cmd" | grep -Eiq 'psql[^|;&]*-c[^|;&]*\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|TRUNCATE|GRANT|REVOKE|COPY)\b|supabase[[:space:]]+db[[:space:]]+(push|reset)|PGPASSWORD=' \
      && deny "unattended-guard: DB write via CLI blocked (I5). Reads only, through mcp__supabase-ro__*."
    # A3 — secret exposure. Deny a bare .env token (not .env.<suffix> like .env.example).
    # No whole-command negation: naming .env.example elsewhere can no longer cancel the deny.
    printf '%s' "$cmd" | grep -Eq '(^|[^./[:alnum:]_])\.env([^.[:alnum:]_/]|$)' \
      && deny "unattended-guard: reading .env / secrets is blocked."
    printf '%s' "$cmd" | grep -Eiq '(echo|printf|curl|wget)[^|;&]*\$\{?[A-Za-z_]*(_?(KEY|TOKEN|SECRET|PASSWORD)|SUPABASE|RESEND|RENDER|DATABASE_URL|SERVICE_ROLE|ANON_KEY)' \
      && deny "unattended-guard: secret expansion into output/network is blocked."
    # printenv / bare env / bare set dump environment variables (which hold secrets).
    printf '%s' "$cmd" | grep -Eiq '\bprintenv\b|(^|[;&|`(]|&&|\|\|)[[:space:]]*(env|set)([[:space:]]*($|[;&|]))' \
      && deny "unattended-guard: env/set/printenv can expose secrets held in the environment; blocked."
    # A4 — authority-file writes via Bash (belt for the Edit/Write category). Write verbs now
    # include interpreters (python/perl/ruby/node/ed/ex/sponge) that open a file directly.
    if printf '%s' "$cmd" | grep -Eq 'CLAUDE\.md|\.claude/settings(\.local)?\.json|\.claude/hooks/|\.claude/agents/arbi\.md|docs/product/(north-star|arbi-constitution|arbi-authority|arbi-permission-model|arbi-scorecard|arbi-promotion-gate)\.md|docs/product/memory/(approved-lessons|authority-lessons|project-facts)\.md' \
       && printf '%s' "$cmd" | grep -Eq '(>>?|tee|sed[[:space:]]+-i|perl[[:space:]]|python[0-9.]*[[:space:]]|ruby[[:space:]]|node[[:space:]]|awk[^|;&]*inplace|dd[^|;&]*of=|cp[[:space:]]|mv[[:space:]]|install[[:space:]]|ln[[:space:]]+-sf|patch\b|truncate\b|sponge\b|(^|[[:space:]])(ed|ex)[[:space:]]|git[[:space:]]+(checkout|restore)[^|;&]*--)'; then
      deny "unattended-guard: writing an authority/boundary file via Bash is blocked. arbi may only DRAFT these via a PR for James."
    fi
    exit 0
    ;;
  Edit|Write|MultiEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
    [ -n "$fp" ] && is_authority_path "$(rel_path "$fp")" \
      && deny "unattended-guard: editing an authority/boundary file is blocked for unattended runs. arbi may only DRAFT it via a PR (route through backend-architect + security-engineer for James to merge)."
    exit 0
    ;;
  NotebookEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.notebook_path // empty')"
    [ -n "$fp" ] && is_authority_path "$(rel_path "$fp")" \
      && deny "unattended-guard: editing an authority/boundary file is blocked for unattended runs."
    exit 0
    ;;
  *apply_migration)
    deny "unattended-guard: DB migration is blocked (I5), reserved to James."
    ;;
  *execute_sql)
    q="$(printf '%s' "$payload" | jq -r '.tool_input.query // empty' | sed -E 's/--[^\n]*//g; s#/\*.*\*/##g')"
    case "$tool" in
      *supabase-ro*|*Supabase-ro*)
        printf '%s' "$q" | grep -Eiq '\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|TRUNCATE|ALTER|DROP|CREATE|GRANT|REVOKE|REFRESH|COPY|CALL|DO|LOCK|SET[[:space:]]+(ROLE|SESSION)|SELECT\b.*\bINTO\b)\b|\b(approve_object|reject_object|set_active_profile|nextval|setval)\b' \
          && deny "unattended-guard: write/DDL on the read-only DB server is blocked (I5)."
        exit 0
        ;;
      *)
        deny "unattended-guard: use mcp__supabase-ro__* for reads; the read-write DB server is blocked for unattended runs (I5). Writes/migrations are reserved to James."
        ;;
    esac
    ;;
  mcp__github__merge_pull_request|mcp__github__enable_pr_auto_merge)
    deny "unattended-guard: merging a PR = prod deploy (I6), reserved to James. Open it as a draft instead."
    ;;
  # GitHub MCP: allow the read/search surface; DEFAULT-DENY every write tool
  # (create_or_update_file / push_files / delete_file / create_branch / merge_* / …).
  mcp__github__get_*|mcp__github__list_*|mcp__github__search_*|mcp__github__pull_request_read|mcp__github__issue_read|mcp__github__actions_get|mcp__github__actions_list|mcp__github__get_me)
    exit 0
    ;;
  mcp__github__*)
    deny "unattended-guard: GitHub write (files/PR/branch/CI/release) is I5/I6, reserved to James. Draft via a branch + PR the interactive session opens."
    ;;
  # Read-write Supabase server: any tool that reached here (not execute_sql / apply_migration,
  # handled above) is a deploy/branch/edge-function mutation → deny. Reads go via -ro.
  mcp__supabase__*|mcp__Supabase__*)
    deny "unattended-guard: Supabase write/deploy/branch mutation is I5, reserved to James. Reads go through mcp__supabase-ro__*."
    ;;
  # Read-only Supabase server: list_/get_ reads are safe (execute_sql/apply_migration already
  # handled above with the write/DDL classifier).
  mcp__supabase-ro__*)
    exit 0
    ;;
  mcp__render__list_*|mcp__render__get_*)
    exit 0
    ;;
  mcp__render__*)
    deny "unattended-guard: Render mutation is blocked (I5/I6), reserved to James."
    ;;
  # External side-effecting MCP servers arbi has no business touching unattended.
  mcp__Lovable__*|mcp__ZoomInfo__*|mcp__Slack__*|mcp__Gmail__*|mcp__Google_Calendar__*|mcp__Google_Drive__*)
    deny "unattended-guard: external side-effecting MCP is blocked for unattended runs."
    ;;
  # Any other MCP tool we don't recognize cannot be proven read-only → fail closed.
  mcp__*)
    deny "unattended-guard: unrecognized MCP tool cannot be classified as read-only; blocked for unattended runs (fail-closed)."
    ;;
  # Local read tools (Read/Glob/Grep/WebFetch/WebSearch/Task/TodoWrite/…) fall through to allow.
  *)
    exit 0
    ;;
esac
exit 0
