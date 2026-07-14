#!/usr/bin/env bash
# authority-guard.sh — PreToolUse guard, ALWAYS-ON (not ARBI_UNATTENDED-gated).
#
# Closes the ONE gap `.claude/settings.json`'s `Edit(...)` deny rules explicitly do not cover.
# Per Claude Code's documented behavior (code.claude.com/docs/en/permissions, checked
# 2026-07-14): "Edit rules apply to all built-in tools that edit files" (Edit/Write/MultiEdit/
# NotebookEdit — one `Edit(/path/**)` rule covers all four) "and to file commands Claude Code
# recognizes in Bash, such as cat, head, tail, and sed. They don't apply to arbitrary
# subprocesses that read or write files indirectly, like a Python or Node script that opens
# files itself." So the settings deny array is the primary, mechanical, first-class boundary
# for the direct-tool and recognized-Bash-command paths; this hook exists ONLY for:
#   (a) an interpreter (python/perl/ruby/node/…) invoked via Bash that opens an authority
#       path itself — the exact residual the docs name;
#   (b) a symlink whose target resolves (via realpath) to an authority path, presented to
#       Edit/Write/MultiEdit/NotebookEdit under a non-authority alias name — settings-level
#       path matching is textual, not filesystem-realpath-aware, so this hook re-checks the
#       resolved path as a redundant, narrowly-justified second layer.
# Not gated on ARBI_UNATTENDED: this must hold attended too (that is the entire point — the
# `reversible-work-window` skill's own "Known limitation" names exactly this gap and requires
# it closed before an unmonitored window relies on the skill's unscoped Edit/Write).
#
# HONEST LIMITS: Bash is not fully parseable. A sufficiently obfuscated interpreter payload
# (a base64-decoded path, `os.rename`, indirect string construction) can still defeat the
# regex below. Accepted residual, same class as unattended-guard.sh's — single-user blast
# radius, and any committed result still passes through the review gate. This hook narrows
# the gap; it does not close it to zero.
set -uo pipefail

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  fi
  exit 0
}

command -v jq >/dev/null 2>&1 || exit 0

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"

# Single source of truth for the authority-path set — kept in sync with the `Edit(...)`
# entries in .claude/settings.json's deny array (same set; this hook's job is the residual,
# not a restatement, but it needs its own copy). A fragment ending in "/" is a directory
# prefix; anything else is an exact repo-relative file. Both is_authority_path() (glob/exact
# match on a resolved path) and the Bash-command regex below are generated from this ONE
# array, so the two matching mechanisms (different by necessity — one tests a resolved path,
# the other substring-scans raw command text) can't silently drift apart.
AUTHORITY_FRAGMENTS=(
  ".claude/" ".github/" "migrations/" "docs/product/rubrics/"
  "CLAUDE.md" "render.yaml" "docs/README.md"
  "docs/product/north-star.md" "docs/product/arbi-constitution.md" "docs/product/arbi-authority.md"
  "docs/product/arbi-permission-model.md" "docs/product/arbi-harness.md" "docs/product/arbi-scorecard.md"
  "docs/product/arbi-promotion-gate.md" "docs/product/arbi-memory-policy.md" "docs/product/arbi-dream-policy.md"
  "docs/product/arbi-managed-agent-spec.md" "docs/product/arbi-autonomy-loop.md" "docs/product/arbi-goal-recipes.md"
  "docs/product/arbi-evals.md" "docs/product/guilfoyle-mission-control.md"
  "docs/product/portfolio-manager-charter.md" "docs/product/portfolio-policy.md"
  "docs/product/recommendation-schema.md" "docs/product/data-contracts.md"
  "docs/product/memory/approved-lessons.md" "docs/product/memory/authority-lessons.md"
  "docs/product/memory/project-facts.md" "docs/product/memory/promotion-log.md"
  "docs/product/memory/rejected-candidates.md"
)

is_authority_path() {
  local p="$1" frag
  for frag in "${AUTHORITY_FRAGMENTS[@]}"; do
    case "$frag" in
      */) [ "${p#"$frag"}" != "$p" ] && return 0 ;;   # directory-prefix fragment
      *)  [ "$p" = "$frag" ] && return 0 ;;             # exact-file fragment
    esac
  done
  return 1
}

# Build the raw-command regex alternation from the same array — escape "." (ERE) per
# fragment, join with "|". Functionally equivalent to (but flatter than) a hand-nested
# alternation; the trade is deliberate — verifiable against one source list beats a more
# compact pattern two people have to keep manually in sync.
_authority_regex_alt() {
  local frag esc out=""
  for frag in "${AUTHORITY_FRAGMENTS[@]}"; do
    esc="${frag//./\\.}"
    out="${out:+$out|}$esc"
  done
  printf '%s' "$out"
}

rel_path() {
  local p="$1" root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  p="$(realpath -m -- "$p" 2>/dev/null || printf '%s' "$p")"
  root="$(realpath -m -- "$root" 2>/dev/null || printf '%s' "$root")"
  printf '%s' "${p#"$root"/}"
}

case "$tool" in
  Edit|Write|MultiEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
    [ -n "$fp" ] && is_authority_path "$(rel_path "$fp")" \
      && deny "authority-guard: this resolves (realpath) to an authority/boundary file. arbi may only DRAFT changes to these via a reviewed PR for James to merge — never a direct edit, including through a symlink alias."
    exit 0
    ;;
  NotebookEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.notebook_path // empty')"
    [ -n "$fp" ] && is_authority_path "$(rel_path "$fp")" \
      && deny "authority-guard: this resolves (realpath) to an authority/boundary path. arbi may only DRAFT changes via a reviewed PR."
    exit 0
    ;;
  Bash)
    cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
    [ -n "$cmd" ] || exit 0
    # Interpreter-based writes (the docs-confirmed gap): python/perl/ruby/node opening a
    # file directly, plus utilities whose "recognized by Claude Code" status is unconfirmed
    # (tee/dd/cp/mv/install/ln -sf/awk-inplace/patch/truncate/sponge/ed/ex/git checkout|
    # restore --) referencing an authority path in the same command. `>>?` is explicitly
    # included (security-engineer, 2026-07-14): a bare shell redirect (`echo x > CLAUDE.md`)
    # names no "recognized file command" at all — echo isn't a file-handling command, the
    # shell's own redirection operator performs the write — so the docs' "cat/head/tail/sed"
    # carve-out for settings-level Edit-deny does NOT extend to it. Mirrors
    # unattended-guard.sh's A4 check, which already includes `>>?`; this hook had dropped it,
    # a real regression this fixes.
    # Boundary is "start-of-string or any non-identifier char" rather than strictly
    # whitespace — a quoted string literal (python's `'.claude/settings.json'`) is preceded
    # by a quote, not whitespace, and must still be caught.
    authority_ref="(^|[^A-Za-z0-9_./-])($(_authority_regex_alt))"
    write_verb='(>>?|python[0-9.]*[[:space:]]|perl[[:space:]]|ruby[[:space:]]|node[[:space:]]|npx[[:space:]]+node[[:space:]]|tee\b|dd[^|;&]*of=|cp[[:space:]]|mv[[:space:]]|install[[:space:]]|ln[[:space:]]+-sf|awk[^|;&]*inplace|patch\b|truncate\b|sponge\b|(^|[[:space:]])(ed|ex)[[:space:]]|git[[:space:]]+(checkout|restore)[^|;&]*--)'
    if printf '%s' "$cmd" | grep -Eiq "$authority_ref" && printf '%s' "$cmd" | grep -Eiq "$write_verb"; then
      deny "authority-guard: this Bash command references an authority/boundary path alongside a write-capable interpreter/utility — blocked. arbi may only DRAFT authority changes via a reviewed PR."
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
