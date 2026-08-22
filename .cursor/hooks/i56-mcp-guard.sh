#!/usr/bin/env bash
set -uo pipefail
payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // .tool // empty' 2>/dev/null || true)"
deny() { jq -cn --arg m "$1" '{permission:"deny",agent_message:$m}'; exit 0; }
printf '%s' "$tool" | grep -Eiq 'apply_migration|enable_pr_auto_merge|merge_pull_request' && deny "I5/I6: $tool blocked"
echo '{"permission":"allow"}'
