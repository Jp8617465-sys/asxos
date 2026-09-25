#!/usr/bin/env bash
# Cursor is IDE-only (James, 2026-09-24): it edits and opens draft PRs. Merging, applying
# a migration and enabling auto-merge are arbi's, landed from the Claude lanes and attended
# sessions under AGENTS.md §8 — one lander, one identity, one queue. #367 had loosened this
# to let a Cursor agent merge and migrate; that is the loosening this file reverts.
set -uo pipefail
payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // .tool // empty' 2>/dev/null || true)"
deny() { jq -cn --arg m "$1" '{permission:"deny",agent_message:$m}'; exit 0; }
printf '%s' "$tool" | grep -Eiq 'enable_pr_auto_merge' && deny "Auto-merge remains blocked"
printf '%s' "$tool" | grep -Eiq 'merge_pull_request|apply_migration' \
  && deny "Cursor is IDE-only: merges and migrations are arbi's (AGENTS.md §8; James, 2026-09-24)"
echo '{"permission":"allow"}'
