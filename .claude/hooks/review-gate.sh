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
#
# R13 (2026-07-13): the plain-commit path below inspects the staged diff, which
# only exists if staging happened in an EARLIER, separate command. Two shapes
# stage Python in the SAME command and so raced past the check:
#   (1) compound  `git add X.py && git commit ...`  — the add runs after this
#       hook has already inspected an empty index;
#   (2) auto-stage `git commit -a` / `-am` / `--all` — commit stages tracked
#       modified files itself, again after this hook runs.
# Both are now denied up front (before the staged-diff path) whenever the working
# tree carries uncommitted Python, with a message telling the user to stage the
# Python in its own command and commit through the normal gate. This errs toward
# denying: it can't see the post-stage index, so it treats any pending .py as
# about-to-be-committed. Consistent with the advisory contract — a false deny is
# recoverable by staging separately; it never lets an ungated .py commit through.
# Known limitations (accepted — advisory speed-bump, marker forgeable anyway):
#   - False deny: a plain `git commit -m "... git add ..."` (or "-a") whose MESSAGE
#     contains those tokens trips the heuristic. Safe direction (deny → stage
#     separately); the substring/regex match is kept simple rather than shell-parsing.
#   - Residual bypasses NOT caught (would let ungated .py through — pre-existing, not
#     introduced by R13): the outer `*"git commit"*` filter is an exact-bigram glob, so
#     `git -c KEY=VAL commit …` and multi-whitespace `git  commit` skip the WHOLE hook;
#     `git commit <path.py>` (pathspec commit) stages working-tree content without
#     `git add`/`-a`; and a file created earlier in the same compound
#     (`gen.py > x.py && git add x.py && git commit`) doesn't exist when the hook runs.
#     Robust fixes need real command parsing; deferred as the marker is forgeable and
#     this is single-user. Adversarial bypass is out of scope by design.
set -euo pipefail

# Emit a PreToolUse deny with the given reason, then exit. Shared so both deny
# paths (stages-inline and staged-diff) can't drift in the JSON envelope.
deny() {
  jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')"

# Only gate git commits; let everything else through instantly.
case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}"

# R13 — detect commands that stage Python in the same breath as the commit, so
# the staged-diff check below can't see it. Two shapes:
#   - a compound that runs `git add` (or its `git stage` synonym) before committing
#   - `git commit` with the -a/--all auto-stage flag (but NOT bare --amend)
stages_inline=0
case "$cmd" in
  *"git add"*|*"git stage"*) stages_inline=1 ;;
esac
# -a inside a single-dash short-flag cluster (-a, -am, -am"msg", -sa, …), or --all.
# The [[:space:]]-[[:alpha:]]*a form matches ` -a`/` -am`/` -am"msg"` (no trailing
# anchor, so a message glued to the flag with no space is still caught) but NOT
# ` --amend`/` --author` (the second dash blocks the [[:alpha:]]*a run) and NOT
# ` -m` (no a), so --amend alone falls through to the normal path where it commits
# an already-staged, already-gated diff.
if [[ "$cmd" =~ [[:space:]]-[[:alpha:]]*a ]] \
   || [[ "$cmd" =~ [[:space:]]--all([[:space:]]|=|$) ]]; then
  stages_inline=1
fi

if [ "$stages_inline" -eq 1 ]; then
  # Any uncommitted Python — unstaged tracked, already-staged, or untracked —
  # means this command would carry .py into a commit without the staged-diff
  # gate ever inspecting it. Deny and require separate staging.
  pending_py="$(
    { git diff --name-only -- '*.py' 2>/dev/null || true; } ;
    { git diff --cached --name-only -- '*.py' 2>/dev/null || true; } ;
    { git ls-files --others --exclude-standard -- '*.py' 2>/dev/null || true; }
  )"
  if [ -n "$pending_py" ]; then
    deny "This command stages Python in the same step as the commit (compound 'git add … && git commit', or 'git commit -a/-am/--all'), which slips past the review gate — the gate can only inspect a diff staged in an earlier, separate command. Stage the Python on its own first (e.g. 'git add <files>'), run the subagent review loop on the staged diff (security-engineer if it touches secrets/external input/dependencies/financial-PII data, refactoring-expert, technical-writer), 'touch' the marker the gate then prints, and commit with a plain 'git commit' (no -a/-am/--all, not compounded with git add)."
  fi
fi

# Only gate when Python is staged — the review loop targets code, not docs/config.
staged_py="$(git diff --cached --name-only -- '*.py' 2>/dev/null || true)"
[ -z "$staged_py" ] && exit 0

# Stable hash of the staged diff; the marker is keyed to it so any change re-arms.
sha="$(git diff --cached | git hash-object --stdin | cut -c1-12)"
marker=".claude/.review-passed-${sha}"
[ -f "$marker" ] && exit 0

deny "Staged Python changes require the subagent review loop before commit (CLAUDE.md policy). Run on the staged diff: security-engineer (if it touches secrets, external input, dependencies, or financial/PII data), refactoring-expert, technical-writer. When done, run: touch ${marker}  — then retry the commit. Writing the marker without running the loop is an explicit, visible bypass."
