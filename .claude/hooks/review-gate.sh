#!/usr/bin/env bash
# review-gate.sh — PreToolUse(Bash) gate.
#
# Blocks `git commit` when Python files are staged until the subagent review loop
# has run for that exact staged diff. See CLAUDE.md "Subagents — delegation policy
# → Review gate". The gate forces a deliberate step (writing a diff-keyed marker);
# it cannot itself spawn an agent or prove one ran.
#
# Advisory + fail-open by contract: if jq is missing, CLAUDE_PROJECT_DIR points
# outside the repo, or any step errors, the hook exits without a deny and the
# commit proceeds. The marker is intentionally forgeable (`touch`). This is a
# developer-discipline speed-bump, not a security boundary.
set -euo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')"

# Only gate git commits; let everything else through instantly.
case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}"

# Only gate when Python is staged — the review loop targets code, not docs/config.
staged_py="$(git diff --cached --name-only -- '*.py' 2>/dev/null || true)"
[ -z "$staged_py" ] && exit 0

# Stable hash of the staged diff; the marker is keyed to it so any change re-arms.
sha="$(git diff --cached | git hash-object --stdin | cut -c1-12)"
marker=".claude/.review-passed-${sha}"
[ -f "$marker" ] && exit 0

reason="Staged Python changes require the subagent review loop before commit (CLAUDE.md policy). Run on the staged diff: security-engineer (if it touches secrets, external input, dependencies, or financial/PII data), refactoring-expert, technical-writer. When done, run: touch ${marker}  — then retry the commit. Writing the marker without running the loop is an explicit, visible bypass."
jq -cn --arg r "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
