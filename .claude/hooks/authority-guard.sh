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
#   (b) a symlink whose target resolves (via flag-free realpath with a Python
#       fallback for new paths) to an authority path, presented to
#       Edit/Write/MultiEdit/NotebookEdit under a non-authority alias name — settings-level
#       path matching is textual, not filesystem-realpath-aware, so this hook re-checks the
#       resolved path as a redundant, narrowly-justified second layer.
# Not gated on ARBI_UNATTENDED: this must hold attended too (that is the entire point — the
# `reversible-work-window` skill's own "Known limitation" names exactly this gap and requires
# it closed before an unmonitored window relies on the skill's unscoped Edit/Write).
#
# HONEST LIMITS: Bash is not fully parseable. A Bash command that names only a symlink alias,
# or an obfuscated interpreter payload (a base64-decoded path, `os.rename`, indirect string
# construction), can still defeat the textual regex below. Direct Edit/Write aliases are
# canonicalised; arbitrary shell intent remains an accepted residual, same class as
# unattended-guard.sh's. This hook narrows the gap; it does not close it to zero.
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

# Single source of truth for the authority-path set — mirrors the narrowed `Edit(...)`
# entries in .claude/settings.json's deny array (same set; this hook's job is the residual,
# not a restatement, but it needs its own copy). A fragment ending in "/" is a directory
# prefix; anything else is an exact repo-relative file. Both is_authority_path() (glob/exact
# match on a resolved path) and the Bash-command regex below are generated from this ONE
# array, so the two matching mechanisms (different by necessity — one tests a resolved path,
# the other substring-scans raw command text) can't silently drift apart.
#
# The `.claude/` entries are enumerated EXPLICITLY — settings.local.json plus
# agents/commands/rules/skills — NOT a broad `.claude/` prefix, mirroring the
# narrowed settings.json deny array. settings.json, hooks/, and CLAUDE.md are
# intentionally absent so attended harness edits can land (2026-08-22). Unattended
# runs still treat those three as authority via unattended-guard.sh. A broad
# `.claude/` fragment here would re-create the 2026-07-14 lockout (it treated
# loose `.claude/.review-passed-*` markers as authority). Those loose root-level
# files are INTENTIONALLY absent from this list and MUST remain writable.
AUTHORITY_FRAGMENTS=(
  ".env"
  ".claude/settings.local.json"
  ".claude/agents/" ".claude/commands/" ".claude/rules/" ".claude/skills/"
  ".github/" "docs/product/rubrics/"
  "render.yaml" "docs/README.md"
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
  local frag esc pattern out=""
  for frag in "${AUTHORITY_FRAGMENTS[@]}"; do
    esc="${frag//./\\.}"
    case "$frag" in
      */) pattern="$esc" ;;
      *) pattern="$esc([^A-Za-z0-9_./-]|$)" ;;
    esac
    out="${out:+$out|}$pattern"
  done
  printf '%s' "$out"
}

canonical_path() {
  local raw="$1" resolved

  # Existing paths are the common case. Both BSD/macOS and GNU realpath support
  # the flag-free form, which also resolves an existing symlink leaf.
  if resolved="$(realpath "$raw" 2>/dev/null)"; then
    printf '%s' "$resolved"
    return 0
  fi

  # BSD realpath rejects a path whose final leaf does not exist. Python resolves
  # an existing symlinked parent while retaining the new leaf, without the
  # GNU-only missing-leaf flags whose use caused this guard to fail open.
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$raw" <<'PY'
import os
import sys

spelled = os.path.abspath(sys.argv[1])
parts = spelled.split(os.sep)
current = os.sep

for index, part in enumerate(parts[1:], start=1):
    candidate = os.path.join(current, part)
    if not os.path.lexists(candidate):
        # The filesystem does not resolve this spelling. Keep it exactly as
        # supplied, including case, so Linux's distinct `claude.md` is not
        # confused with `CLAUDE.md`.
        current = os.path.join(current, *parts[index:])
        break

    # On a case-insensitive filesystem lexists() can succeed for `.CLAUDE`
    # while the real directory entry is `.claude`. Recover the entry's stored
    # spelling before resolving symlinks. Case-sensitive filesystems never take
    # this branch for a differently-cased name.
    entries = os.listdir(current)
    if part not in entries:
        folded = [entry for entry in entries if entry.casefold() == part.casefold()]
        if len(folded) == 1:
            part = folded[0]
    current = os.path.realpath(os.path.join(current, part))

print(os.path.normpath(current))
PY
}

relative_to_root() {
  local candidate="$1" root="$2"
  case "$candidate" in
    "$root"/*) printf '%s' "${candidate#"$root"/}" ;;
    *) return 1 ;;
  esac
}

guard_authority_path() {
  local fp="$1" payload_cwd target_root control_root candidate root rel
  [ -n "$fp" ] || return 0

  payload_cwd="$(printf '%s' "$payload" \
    | jq -er '.cwd | select(type == "string" and length > 0)' 2>/dev/null)" \
    || deny "authority-guard: file-operation payload omitted a valid cwd; refusing an unbound path check."
  control_root="${CLAUDE_PROJECT_DIR:-}"

  # Claude normally invokes the hook at the project root. Avoid a git subprocess
  # on that hot path; use git only when the tool-call cwd and control root differ.
  if [ -n "$control_root" ] && [ "$payload_cwd" = "$control_root" ]; then
    target_root="$(canonical_path "$payload_cwd")" \
      || deny "authority-guard: target checkout could not be canonicalised; refusing the file operation."
    control_root="$target_root"
  else
    target_root="$(git -C "$payload_cwd" rev-parse --show-toplevel 2>/dev/null \
      || printf '%s' "$payload_cwd")"
    target_root="$(canonical_path "$target_root")" \
      || deny "authority-guard: target checkout could not be canonicalised; refusing the file operation."
    control_root="${control_root:-$target_root}"
    control_root="$(canonical_path "$control_root")" \
      || deny "authority-guard: loaded-control checkout could not be canonicalised; refusing the file operation."
  fi

  case "$fp" in
    /*) candidate="$fp" ;;
    *) candidate="$payload_cwd/$fp" ;;
  esac
  candidate="$(canonical_path "$candidate")" \
    || deny "authority-guard: target path could not be canonicalised; refusing the file operation."

  # Protect only the active target checkout and the checkout that supplied the
  # loaded controls. An identically named file in an unrelated repository is not
  # an Arbi authority surface.
  for root in "$target_root" "$control_root"; do
    if rel="$(relative_to_root "$candidate" "$root" 2>/dev/null)" \
       && is_authority_path "$rel"; then
      deny "authority-guard: this canonical path resolves to an authority/boundary file. arbi may only DRAFT changes to these via a reviewed PR for James to merge — never a direct edit, including through a symlink alias."
    fi
  done
}

case "$tool" in
  Edit|Write|MultiEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
    guard_authority_path "$fp"
    exit 0
    ;;
  NotebookEdit)
    fp="$(printf '%s' "$payload" | jq -r '.tool_input.notebook_path // empty')"
    guard_authority_path "$fp"
    exit 0
    ;;
  Bash)
    cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
    [ -n "$cmd" ] || exit 0
    scrub="$(printf '%s' "$cmd" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/(null|stderr)##g')"
    authority_ref="(^|[^A-Za-z0-9_./-])($(_authority_regex_alt))"
    util_verb='(python[0-9.]*[[:space:]]|perl[[:space:]]|ruby[[:space:]]|node[[:space:]]|npx[[:space:]]+node[[:space:]]|tee\b|dd[^|;&]*of=|cp[[:space:]]|mv[[:space:]]|install[[:space:]]|ln[[:space:]]+-sf|awk[^|;&]*inplace|patch\b|truncate\b|sponge\b|(^|[[:space:]])(ed|ex)[[:space:]]|git[[:space:]]+(checkout|restore)[^|;&]*--)'
    if printf '%s' "$scrub" | grep -Eiq "$authority_ref" && printf '%s' "$scrub" | grep -Eiq "$util_verb"; then
      deny "authority-guard: this Bash command references an authority/boundary path alongside a write-capable interpreter/utility — blocked. arbi may only DRAFT authority changes via a reviewed PR."
    fi
    redirect_targets="$(printf '%s' "$scrub" | grep -oE '[^<]>>?[[:space:]]*[^[:space:]|&;<>()]+' || true)"
    while IFS= read -r tok; do
      [ -n "$tok" ] || continue
      target="$(printf '%s' "$tok" | sed -E 's/^[^>]*>>?[[:space:]]*//; s/["'"'"']//g')"
      [ -n "$target" ] || continue
      if printf '%s' "$target" | grep -Eiq "$authority_ref"; then
        deny "authority-guard: this Bash command references an authority/boundary path alongside a write-capable interpreter/utility — blocked. arbi may only DRAFT authority changes via a reviewed PR."
      fi
    done <<< "$redirect_targets"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
