#!/usr/bin/env bash
# secrets-guard.sh — the one PreToolUse(Bash) hook left in this repo.
#
# Refuses exactly three shapes, all of which leak a secret VALUE into the transcript
# or a log: reading `.env`, expanding a secret-named variable into echo/printf/cat
# output, and dumping the whole environment. It refuses nothing James would ask arbi
# to build. Calling an API with a token in a header is not one of the three — that
# is how tokens are used, and the classifier is not running in bypassPermissions.
#
# Deny-only. A shape it fails to recognise runs normally.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0
payload="$(cat)"
[ "$(printf '%s' "$payload" | jq -r '.tool_name // empty')" = "Bash" ] || exit 0
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
[ -n "$cmd" ] || exit 0

deny() {
  jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

# 1. A bare `.env` token (not `.env.example` or `.env.<suffix>`).
printf '%s' "$cmd" | grep -Eq '(^|[^./[:alnum:]_])\.env([^.[:alnum:]_/]|$)' \
  && deny "secrets-guard: .env holds secret values. Use them through the environment; never read the file."

# 2. A secret-named variable expanded into transcript output.
printf '%s' "$cmd" | grep -Eiq '(^|[;&|`(]|&&|\|\|)[[:space:]]*(echo|printf|cat)[^|;&]*\$\{?[A-Za-z_]*(_?(KEY|TOKEN|SECRET|PASSWORD|PAT)|SUPABASE|RESEND|DATABASE_URL|SERVICE_ROLE|ANON_KEY)' \
  && deny "secrets-guard: that would print a secret value into the transcript. Reference it inside the tool that consumes it."

# 3. Whole-environment dumps.
printf '%s' "$cmd" | grep -Eiq '\bprintenv\b|(^|[;&|`(]|&&|\|\|)[[:space:]]*(env|set)([[:space:]]*($|[;&|]))' \
  && deny "secrets-guard: env/set/printenv dump the environment, which holds secrets. Name the variable you need."

exit 0
