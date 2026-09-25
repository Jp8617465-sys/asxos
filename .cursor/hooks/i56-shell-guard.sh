#!/usr/bin/env bash
# Cursor is IDE-only (James, 2026-09-24): edit, push a cursor/** branch, open a DRAFT PR.
# Landing — `gh pr merge`, marking a PR ready, opening a non-draft PR — is arbi's
# (AGENTS.md §8). #367 had dropped the merge and non-draft-create denies; restored here.
set -uo pipefail
payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)"
deny() { jq -cn --arg m "$1" '{permission:"deny",agent_message:$m}'; exit 0; }
[ -n "$cmd" ] || { echo '{"permission":"allow"}'; exit 0; }
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*([[:space:]]|:)(refs/heads/)?(main|master)\b'; then deny "I6: push to main blocked"; fi
if printf '%s' "$cmd" | grep -Eiq '\bgit\b[^|;&]*\bpush\b[^|;&]*(--force|--force-with-lease)'; then deny "I6: force-push blocked"; fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+merge'; then deny "Cursor is IDE-only: merging is arbi's (AGENTS.md §8)"; fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+ready'; then deny "PR readiness must be explicit"; fi
if printf '%s' "$cmd" | grep -Eiq 'gh[[:space:]]+pr[[:space:]]+create' && ! printf '%s' "$cmd" | grep -Eiq -- '--draft'; then deny "Cursor opens draft PRs only; readiness is arbi's"; fi
if printf '%s' "$cmd" | grep -Eiq 'supabase[[:space:]]+db[[:space:]]+(push|reset)'; then deny "I5: db mutate blocked"; fi
echo '{"permission":"allow"}'
