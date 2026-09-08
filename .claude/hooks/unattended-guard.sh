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
#   - capital/portfolio/tax/model/thesis code edits (security-perf loop carve-out)
#   - unscrubbed pytest / ad-hoc interpreter code-exec (security-perf loop, HIGH-2/MED-5)
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
# all be caught in-band; the execute_sql classifier (now in db-write-guard.sh, always-on —
# see its header) is best-effort and the RO writer-function leak (SELECT some_writer_fn())
# is only partially blacklisted. The REAL mechanical backstops
# are GitHub branch protection (merge/deploy/push-to-main) and the R2 read-only Postgres role
# (DB writes). This reduces risk R5 (prompt-only enforcement) from total to partial; it does
# not close it. The A6 pytest / A7 interpreter checks are belt-only (a wrapper like `make
# check` or string indirection bypasses them) — the durable fix is launching the scheduled
# session with secrets absent from its process env (docs/product/security-perf-mission-loop.md
# §10 item 2).
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

# Resolve the tool call's OWN checkout, then test the target path under every
# guarded root. The previous single-root strip was anchored to $CLAUDE_PROJECT_DIR:
# a path inside a git worktree never stripped, so what reached is_authority_path()
# was still absolute, matched none of its repo-relative patterns, and the guarded
# categories silently failed OPEN — the exact inverse of this hook's fail-closed
# contract. Mirrors authority-guard.sh: protect the active target checkout AND the
# checkout that supplied the loaded controls; an identically named file in an
# unrelated repository is not a guarded surface.
payload_cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty')"

# canonicalise WITHOUT the GNU-only missing-leaf flags. `realpath -m` is not
# portable: BSD/macOS realpath rejects it, the command fails, and the caller then
# compares unresolved literals — a textual prefix match that lets `..` segments and
# alternate root spellings (/tmp vs /private/tmp) slip straight through. That exact
# mistake is what made authority-guard.sh fail open before PR #77; see its
# canonical_path() header. Order here mirrors that fix: flag-free realpath resolves
# any existing path (including a symlinked leaf); a missing leaf falls back to
# resolving the parent and re-attaching the leaf; only a missing parent degrades to
# the literal.
_canon_path() {
  local p="$1" resolved parent leaf
  if resolved="$(realpath "$p" 2>/dev/null)"; then
    printf '%s' "$resolved"
    return 0
  fi
  parent="$(dirname -- "$p")"
  leaf="$(basename -- "$p")"
  if resolved="$(realpath "$parent" 2>/dev/null)"; then
    printf '%s/%s' "$resolved" "$leaf"
    return 0
  fi
  printf '%s' "$p"
}

# The guarded roots, computed once. Kept lazy (the Bash branch never needs them)
# and memoised, because path_matches() is called twice per Edit and each call
# would otherwise re-fork `git rev-parse` plus several `realpath`s.
_guard_roots_cache=""

_ensure_guard_roots() {
  [ -n "$_guard_roots_cache" ] && return 0
  local target_root control_root
  # `:-$(pwd)` not `:-}` — with CLAUDE_PROJECT_DIR unset the control root would
  # otherwise be dropped entirely, losing the guard the old rel_path() still had
  # via the hook's own cwd.
  control_root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  if [ -n "$payload_cwd" ] && [ -d "$payload_cwd" ]; then
    target_root="$(git -C "$payload_cwd" rev-parse --show-toplevel 2>/dev/null \
      || printf '%s' "$payload_cwd")"
  else
    target_root="${control_root:-$(pwd)}"
  fi
  target_root="$(_canon_path "$target_root")"
  _guard_roots_cache="$target_root"
  if [ -n "$control_root" ]; then
    control_root="$(_canon_path "$control_root")"
    if [ "$control_root" != "$target_root" ]; then
      _guard_roots_cache="$_guard_roots_cache
$control_root"
    fi
  fi
  return 0
}

# path_matches <file_path> <predicate_fn> — true if the path resolves, under ANY
# guarded root, to a repo-relative path the predicate accepts.
path_matches() {
  local fp="$1" pred="$2" abs root rel
  [ -n "$fp" ] || return 1
  # Allowlist the predicate. Every call site passes a hardcoded literal today, but
  # `"$pred"` resolves through PATH when it is not a shell function — so a later
  # call site passing a variable would silently become a command-execution sink.
  case "$pred" in
    is_authority_path|is_capital_path) ;;
    *) deny "unattended-guard: unknown path predicate '$pred'; refusing to classify (fail-closed)." ;;
  esac
  _ensure_guard_roots
  case "$fp" in
    /*) abs="$fp" ;;
    *)
      # A relative file_path is relative to the TOOL CALL's cwd — not to the repo
      # root. Resolving it against the root instead would mis-locate every call
      # made from a subdirectory (cwd=<root>/asxos, fp=domain/tax/positions.py
      # would resolve to <root>/domain/... and match nothing).
      if [ -n "$payload_cwd" ] && [ -d "$payload_cwd" ]; then
        abs="$payload_cwd/$fp"
      else
        # No usable base: nothing can say which directory this spelling is
        # relative to. Fail CLOSED — test it as if it were already repo-relative,
        # which over-denies but can never under-deny.
        "$pred" "$fp" && return 0
        return 1
      fi
      ;;
  esac
  abs="$(_canon_path "$abs")"
  # NOTE: a here-doc, deliberately not a pipe — a pipe runs the loop body in a
  # subshell, where `return 0` cannot propagate out of this function.
  while IFS= read -r root; do
    [ -n "$root" ] || continue
    case "$abs" in
      "$root"/*) rel="${abs#"$root"/}" ;;
      *) continue ;;
    esac
    if "$pred" "$rel"; then
      return 0
    fi
  done <<EOF
$_guard_roots_cache
EOF
  return 1
}

# --- Capital-adjacent carve-out (security-perf-mission-loop.md §1, red-team #1 / LOW-8) ----
# Modeled on authority-guard.sh's is_authority_path/_authority_regex_alt idiom: a fragment
# ending in "/" is a directory prefix; anything else is an exact repo-relative file. The
# security/perf loop is model/tax/portfolio/thesis READ-only — it may read these to log a
# `deferred: capital-adjacent, human-only` finding, never draft a change to them. The three
# named files (allocator/rebalance/tax_overlay) live under asxos/domain/portfolio/, so the
# directory prefixes already cover them.
CAPITAL_FRAGMENTS=(
  "asxos/domain/portfolio/" "asxos/domain/tax/"
  "asxos/domain/models/" "asxos/domain/theses/"
)

is_capital_path() {
  local p="$1" frag
  for frag in "${CAPITAL_FRAGMENTS[@]}"; do
    case "$frag" in
      */) [ "${p#"$frag"}" != "$p" ] && return 0 ;;   # directory-prefix fragment
      *)  [ "$p" = "$frag" ] && return 0 ;;             # exact-file fragment
    esac
  done
  return 1
}

_capital_regex_alt() {
  local frag esc out=""
  for frag in "${CAPITAL_FRAGMENTS[@]}"; do
    esc="${frag//./\\.}"
    out="${out:+$out|}$esc"
  done
  printf '%s' "$out"
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
      # Branch of every checkout this push could run in — the payload's own cwd (a
      # worktree has its own HEAD) AND the control checkout (the command may `cd`
      # elsewhere first). Deny if either is main/master; see push-guard.sh's
      # matching block for why testing only one root trades one hole for another.
      ug_push_cwd="${payload_cwd:-}"
      [ -n "$ug_push_cwd" ] && [ -d "$ug_push_cwd" ] || ug_push_cwd=""
      for _ug_root in "$ug_push_cwd" "${CLAUDE_PROJECT_DIR:-}"; do
        [ -n "$_ug_root" ] || continue
        cur="$(git -C "$_ug_root" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
        case "$cur" in main|master) deny "unattended-guard: 'git push' while a relevant checkout ($_ug_root) is on $cur = prod deploy (I6). Use a claude/** branch + PR." ;; esac
      done
    fi
    printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge|\bgit\b[^|;&]*\bmerge\b|gh[[:space:]]+pr[^|;&]*(--merge|--auto|--admin)|gh[[:space:]]+workflow[[:space:]]+(run|enable|disable)|gh[[:space:]]+release[[:space:]]+(create|edit|delete)|gh[[:space:]]+api[^|;&]*(--method|-X)[[:space:]]*(POST|PUT|PATCH|DELETE)|(curl|wget)[^|;&]*api\.github\.com[^|;&]*/merge' \
      && deny "unattended-guard: merge / CI / release mutation is blocked (I6), reserved to James."
    # A1c — Render REST API mutations via curl/wget. There is NO Render MCP; Render is
    # managed through api.render.com. This catches mutating methods/bodies (deploy / job
    # trigger / env-var change / suspend = I5/I6). Note: any Render curl also needs
    # $RENDER_API_KEY in a header, which A3 (secret expansion) already blocks under
    # unattended — so in practice ALL Render curl is refused unattended (fail-closed).
    # Attended runs are a total no-op (the guard is disarmed).
    printf '%s' "$cmd" | grep -Eiq '(curl|wget)[^|;&]*api\.render\.com' \
      && printf '%s' "$cmd" | grep -Eiq '(-X[[:space:]]*(POST|PUT|PATCH|DELETE)|--request[[:space:]]*(POST|PUT|PATCH|DELETE)|--data|--data-[a-z]+|--json|(^|[[:space:]])-d[[:space:]]|(^|[[:space:]])-T[[:space:]]|--upload-file)' \
      && deny "unattended-guard: Render API mutation (deploy / job trigger / env change) is blocked (I5/I6), reserved to James."
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
    # A5 — capital-adjacent writes via Bash (red-team #1 / LOW-8). Same interpreter/redirect
    # write-verb idiom as authority-guard.sh, applied to the §1 capital carve-out subtrees.
    capital_ref="(^|[^A-Za-z0-9_./-])($(_capital_regex_alt))"
    write_verb='(>>?|tee\b|sed[[:space:]]+-i|python[0-9.]*[[:space:]]|perl[[:space:]]|ruby[[:space:]]|node[[:space:]]|npx[[:space:]]+node[[:space:]]|dd[^|;&]*of=|cp[[:space:]]|mv[[:space:]]|install[[:space:]]|ln[[:space:]]+-sf|awk[^|;&]*inplace|patch\b|truncate\b|sponge\b|(^|[[:space:]])(ed|ex)[[:space:]]|git[[:space:]]+(checkout|restore)[^|;&]*--)'
    if printf '%s' "$cmd" | grep -Eiq "$capital_ref" && printf '%s' "$cmd" | grep -Eiq "$write_verb"; then
      deny "unattended-guard: capital/portfolio/tax/model/thesis code is human-only for this loop; draft nothing here."
    fi
    # Command-position preamble (mirrors A3's env/set anchor): start-of-string or a command
    # separator, then any run of VAR=val / env … prefixes. Anchoring here keeps a finder's
    # `grep "pytest" …` / `grep "python -c" …` (token mid-command, not command-position) safe.
    cmd_start='(^|[;&|`(]|&&|\|\|)[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+|env[[:space:]]+([^;&|]*[[:space:]]+)?)*'
    # A6 — pytest is an allowlisted arbitrary-code-execution path (settings.json Bash(pytest:*));
    # unattended it MUST run secret-scrubbed (security HIGH-2 + MED-5). Accept ONLY an `env -i`
    # scrub in front of pytest; deny a pytest reachable at a command boundary or after VAR=val
    # prefixes (bare, `FOO=x pytest`, or a compound `env -i true; pytest`). `env -u` is NOT a
    # complete scrub (can't wildcard *_KEY/*_TOKEN/*_SECRET) and is intentionally not accepted.
    # BELT-ONLY: a wrapper (`make check`, `tox`) bypasses this — the durable fix is a
    # secret-free session env (§10 item 2). `python -m py_compile`, ruff, mypy, `grep pytest`
    # are not matched (no `-m pytest`, not in command position).
    unscrubbed_pytest='(^|[;&|`(]|&&|\|\|)[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*(pytest\b|python[0-9.]*[[:space:]]+-m[[:space:]]+pytest\b)'
    printf '%s' "$cmd" | grep -Eiq "$unscrubbed_pytest" \
      && deny "unattended-guard: pytest must run env-scrubbed unattended (e.g.  env -i PATH=\"\$PATH\" HOME=\"\$HOME\" pytest …); bare or compound pytest is blocked (HIGH-2/MED-5)."
    # A7 — ad-hoc interpreter code-exec that can read secrets or open a network/DB connection
    # outside the guarded surface is forbidden by §1: python -c/- , node -e, perl/ruby -e,
    # bash/sh/dash/zsh/ksh -c, php -r, awk BEGIN. Command-position anchored (cmd_start) so a
    # grep/ruff/mypy that merely NAMES one of these forms as a search string is untouched.
    interp_exec='(python[0-9.]*[[:space:]]+(-c\b|-([[:space:]]|$))|node[[:space:]]+(-e|-p|--eval|--print)\b|perl[[:space:]]+-[eE]\b|ruby[[:space:]]+-e\b|(bash|sh|dash|zsh|ksh)[[:space:]]+[^|;&]*-[A-Za-z]*c\b|php[[:space:]]+-r\b|awk[[:space:]]+[^|;&]*BEGIN)'
    printf '%s' "$cmd" | grep -Eiq "${cmd_start}${interp_exec}" \
      && deny "unattended-guard: ad-hoc interpreter code-exec (python -c/-, node -e, perl/ruby -e, bash/sh -c, php -r, awk BEGIN) is blocked unattended — it can read secrets or reach the network/DB outside the guarded surface (§1 / MED-5)."
    exit 0
    ;;
  Edit|Write|MultiEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
    [ -n "$fp" ] && path_matches "$fp" is_authority_path \
      && deny "unattended-guard: editing an authority/boundary file is blocked for unattended runs. arbi may only DRAFT it via a PR (route through backend-architect + security-engineer for James to merge)."
    [ -n "$fp" ] && path_matches "$fp" is_capital_path \
      && deny "unattended-guard: capital/portfolio/tax/model/thesis code is human-only for this loop; draft nothing here."
    exit 0
    ;;
  NotebookEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.notebook_path // empty')"
    [ -n "$fp" ] && path_matches "$fp" is_authority_path \
      && deny "unattended-guard: editing an authority/boundary file is blocked for unattended runs."
    [ -n "$fp" ] && path_matches "$fp" is_capital_path \
      && deny "unattended-guard: capital/portfolio/tax/model/thesis code is human-only for this loop; draft nothing here."
    exit 0
    ;;
  # apply_migration: the unconditional deny formerly here now lives in
  # db-write-guard.sh, always-on rather than ARBI_UNATTENDED-gated (James,
  # 2026-09-08) — one copy instead of two drifting apart. An unattended
  # apply_migration call still denies: it falls through to the
  # mcp__supabase__*/mcp__Supabase__* catch-all below.
  *execute_sql)
    # The read-only-server keyword paranoia check formerly here also moved to
    # db-write-guard.sh, always-on — it was dead code in every attended session,
    # which was every session run so far (measured, 2026-09-08). This case keeps
    # only the rule that's still unattended-specific: no access to the
    # write-capable server at all, regardless of query content.
    case "$tool" in
      *supabase-ro*|*Supabase-ro*)
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
  # NOTE: there is no Render MCP in this project — Render is the REST API, gated above
  # (A1c) at the Bash/curl layer. These mcp__render__* cases are a harmless belt in case a
  # Render MCP is ever mounted; the live enforcement path is A1c.
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
