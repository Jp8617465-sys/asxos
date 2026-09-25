#!/usr/bin/env bash
# secrets-guard.sh — the one PreToolUse hook left in this repo (matcher: Read|Bash).
#
# Refuses exactly four shapes, all of which leak a secret VALUE into the transcript
# or a log: reading `.env`, expanding a secret-named variable into echo/printf/cat
# output, dumping the whole environment, and reading a secret-shaped FILE
# (`.env*` other than `.env.example`, `*.secret`, `*.pem`, `*.key`) through Read or
# the shell. It refuses nothing James would ask arbi to build. Calling an API with a
# token in a header is not one of the four — that is how tokens are used, and the
# classifier is not running in bypassPermissions.
#
# Deny-only for shapes: one it fails to recognise runs normally. Fail-CLOSED for its
# own preconditions: no jq is exit 2 (a blocking hook error), never a silent allow.
#
# Proof log (A-22). Every call appends one line to ${RUNNER_TEMP:-/tmp}/a22-hook-proof.log:
#   GUARD tool=<name> decision=allow|BLOCK rule=<id|-> project_dir=set|unset
# That line is how a headless run proves this file actually ran (the action hides the
# agent's output). It never carries the tool input — no command text, no file path.
set -uo pipefail

command -v jq >/dev/null 2>&1 || { echo "secrets-guard: jq is missing; refusing to run open" >&2; exit 2; }
payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"
proof="${RUNNER_TEMP:-/tmp}/a22-hook-proof.log"
project_dir=unset
[ -n "${CLAUDE_PROJECT_DIR:-}" ] && project_dir=set

log() { printf 'GUARD tool=%s decision=%s rule=%s project_dir=%s\n' "${tool:-?}" "$1" "$2" "$project_dir" >> "$proof" 2>/dev/null || true; }
deny() {
  log BLOCK "$1"
  jq -cn --arg r "$2" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}
allow() { log allow -; exit 0; }

# 4. A secret-shaped file: `.env`, `.env.<anything>` (not `.env.example`), `*.secret`,
#    `*.pem`, `*.key`. Read gives a path; the shell gives a command that names one.
SECRET_FILE_RE='(^|/)\.env(\.[^/]*)?$|\.(secret|pem|key)$'
is_secret_file() {
  case "$1" in .env.example|*/.env.example) return 1 ;; esac
  printf '%s' "$1" | grep -Eq "$SECRET_FILE_RE"
}

case "$tool" in
  Read)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
    [ -n "$fp" ] || allow
    is_secret_file "$fp" && deny secret-file "secrets-guard: that is a secret-shaped file. Use its values through the environment; never read the file."
    allow
    ;;
  Bash) ;;
  *) allow ;;
esac

cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
[ -n "$cmd" ] || allow

# 1. A bare `.env` token (not `.env.example` or `.env.<suffix>` — those are shape 4).
printf '%s' "$cmd" | grep -Eq '(^|[^./[:alnum:]_])\.env([^.[:alnum:]_/]|$)' \
  && deny dotenv "secrets-guard: .env holds secret values. Use them through the environment; never read the file."

# 2. A secret-named variable expanded into transcript output.
printf '%s' "$cmd" | grep -Eiq '(^|[;&|`(]|&&|\|\|)[[:space:]]*(echo|printf|cat)[^|;&]*\$\{?[A-Za-z_]*(_?(KEY|TOKEN|SECRET|PASSWORD|PAT)|SUPABASE|RESEND|DATABASE_URL|SERVICE_ROLE|ANON_KEY)' \
  && deny secret-expansion "secrets-guard: that would print a secret value into the transcript. Reference it inside the tool that consumes it."

# 3. Whole-environment dumps.
printf '%s' "$cmd" | grep -Eiq '\bprintenv\b|(^|[;&|`(]|&&|\|\|)[[:space:]]*(env|set)([[:space:]]*($|[;&|]))' \
  && deny env-dump "secrets-guard: env/set/printenv dump the environment, which holds secrets. Name the variable you need."

# 4. (shell form) A secret-shaped file handed to a program that would READ it. Only the
#    first word of each simple command decides: `cat`, `grep`, `python`, `cp`… deny;
#    `git add signing.key` or a commit message that mentions canary.secret do not.
#    Only the text before the first heredoc is inspected — a heredoc body is data, and
#    a read smuggled inside one is a residual shape 1 already shares. `set -f` so a `*`
#    in the command is a token to test, never a glob to expand against the working tree.
READERS='cat|head|tail|less|more|sed|awk|grep|rg|egrep|fgrep|cut|sort|uniq|wc|strings|xxd|od|hexdump|base64|cp|mv|scp|rsync|python|python3|node|ruby|perl|bash|sh|zsh|source|\.|vi|vim|nano'
set -f
printf '%s\n' "${cmd%%<<*}" | tr '|;&' '\n' | while IFS= read -r simple; do
  simple="${simple#"${simple%%[![:space:](]*}"}"
  simple="${simple#sudo }"
  head_word="${simple%%[[:space:]]*}"
  printf '%s' "$head_word" | grep -Eqx "$READERS" || continue
  for word in $(printf '%s' "$simple" | tr -c 'A-Za-z0-9_./-' ' '); do
    if is_secret_file "$word"; then echo BLOCK; break; fi
  done
done | grep -q BLOCK \
  && deny secret-file "secrets-guard: that names a secret-shaped file. Use its values through the environment; never read the file."

allow
