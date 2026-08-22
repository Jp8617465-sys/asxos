#!/usr/bin/env bash
set -uo pipefail
payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)"
deny() { jq -cn --arg m "$1" '{permission:"deny",agent_message:$m}'; exit 0; }
[ -n "$cmd" ] || { echo '{"permission":"allow"}'; exit 0; }
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*([[:space:]]|:)(refs/heads/)?(main|master)\b'; then deny "I6: push to main blocked"; fi
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*(--force|--force-with-lease)'; then deny "I6: force-push blocked"; fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+(merge|ready)'; then deny "I6: merge/ready blocked"; fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+create' && ! printf '%s' "$cmd" | grep -Eiq -- '--draft\b'; then deny "I6: draft required"; fi
if printf '%s' "$cmd" | grep -Eiq 'supabase[[:space:]]+db[[:space:]]+(push|reset)'; then deny "I5: db mutate blocked"; fi
echo '{"permission":"allow"}'
