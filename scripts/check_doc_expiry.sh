#!/usr/bin/env bash
#
# check_doc_expiry.sh — flag dated docs that were never retired.
#
# WHY THIS EXISTS (measured 2026-08-18):
#   **78 of 167 tracked docs carry a date in the basename.** Nearly half the
#   documentation set is event records — a session handoff, a dry-run, a
#   one-off audit, a proposal written on a Tuesday. Each was true when written
#   and none was ever retired. That is the sprawl mechanism: the repo does not
#   accumulate docs because anyone decided to keep them, it accumulates them
#   because nothing ever asks whether a dated record still has a reader.
#
#   The cost is not disk. It is that a stale dated doc reads exactly like a
#   current one — same tone, same confidence, no expiry marker — so a fresh
#   session loads it as fact. Every doc-truth sweep so far has found the same
#   shape of defect: a claim that was correct on its date and false by the time
#   anyone re-read it. A date in the filename is a promise that the contents
#   are pinned to that date; this check makes the promise enforceable.
#
# WHAT IT DOES
#   Fails when a tracked `docs/**/*.md` whose BASENAME contains YYYY-MM-DD is
#   more than THRESHOLD_DAYS (default 30) past that date and is not already
#   archived. "Archived" means any `archive/` path component, not only
#   `docs/archive/` — the repo has two archive conventions and both are
#   legitimate: the main one at `docs/archive/`, and the pre-existing
#   `docs/product/memory/dream-candidates/archive/` that promoted dream
#   candidates go to. Matching only the first would permanently flag every
#   correctly-archived dream candidate, which trains people to ignore the check.
#
# WHAT IT DOES NOT DO — and must never do:
#   It never moves, deletes, or edits a file. Archiving is a judgement call
#   that requires checking inbound references first; a script that guessed
#   would break links silently and would be far worse than the sprawl. This
#   reports; a human moves. Same contract as check_ledger_coverage.sh, which
#   never writes a ledger row.
#
#   It also does not read the doc. "Still referenced" and "still true" are not
#   things a date check can know. An offender is a doc that OWES A DECISION,
#   not a doc that is wrong.
#
# THE ALLOWLIST
#   Some dated docs are genuinely canonical — the date is part of the record's
#   identity, not a staleness marker, and they are cited as current by CLAUDE.md
#   or by the docs index. Those are listed in ALLOWLIST below by basename.
#   Adding an entry is a deliberate act: it asserts the doc is a standing
#   source of truth that happens to carry a date, not an event record.
#
# USAGE
#   scripts/check_doc_expiry.sh [THRESHOLD_DAYS]
#     THRESHOLD_DAYS defaults to 30.
#   Exit 0 = no expired dated docs outside docs/archive/.
#   Exit 1 = one or more are expired (the list is printed).
#   Exit 2 = the check could not run (wrong directory, git unavailable).
#
# REQUIRES: git. Read-only: no writes, no network.

set -euo pipefail

THRESHOLD_DAYS="${1:-30}"
ARCHIVE_PREFIX="docs/archive/"

# Dated docs that are canonical rather than event records. Basenames only —
# a doc keeps its identity if it moves directory.
ALLOWLIST="
model-a-decay-analysis-2026-07-11.md
scheduler-inventory-2026-08-13.md
finance-capability-matrix-2026-08-13.md
governance-first-architecture-2026-06-30.md
"

command -v git >/dev/null 2>&1 || { echo "[doc-expiry] git not found" >&2; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "[doc-expiry] not inside a git work tree — run from the repo root" >&2; exit 2; }
[ -d docs ] || { echo "[doc-expiry] docs/ not found — run from the repo root" >&2; exit 2; }

# Portable "days between two ISO dates". BSD date (macOS, the governor's
# laptop) and GNU date (CI) disagree on every flag that matters, so both
# spellings are tried. The script must run in both places, like
# check_ledger_coverage.sh's bash-3.2 read loop.
_epoch_of() {
  date -u -j -f '%Y-%m-%d' "$1" '+%s' 2>/dev/null \
    || date -u -d "$1" '+%s' 2>/dev/null \
    || return 1
}

TODAY_EPOCH="$(date -u '+%s')"

echo "[doc-expiry] threshold: ${THRESHOLD_DAYS} days"
echo "[doc-expiry] exempt:    any */archive/* path, and the allowlist ($(printf '%s\n' "$ALLOWLIST" | grep -c '[^[:space:]]') entries)"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# Tracked markdown under docs/ only. Untracked scratch files are not the
# repo's problem, and files outside docs/ are code-adjacent (ADRs in-tree,
# READMEs) with different lifecycles.
git ls-files 'docs/*.md' 'docs/**/*.md' | sort -u > "$TMP"

total=0
dated=0
expired=0

while IFS= read -r path; do
  [ -n "$path" ] || continue
  total=$((total + 1))

  base="${path##*/}"

  # The date must be in the BASENAME, not the directory. docs/2026-08-18/x.md
  # is a dated folder, a different (and rarer) convention this check leaves alone.
  doc_date="$(printf '%s' "$base" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || true)"
  [ -n "$doc_date" ] || continue
  dated=$((dated + 1))

  # Already archived, under either convention (see header).
  case "$path" in
    */archive/*) continue ;;
  esac

  if printf '%s\n' "$ALLOWLIST" | grep -qxF "$base"; then
    continue
  fi

  doc_epoch="$(_epoch_of "$doc_date")" || {
    echo "[doc-expiry] WARN unparseable date '$doc_date' in $path — skipped" >&2
    continue
  }

  age_days=$(( (TODAY_EPOCH - doc_epoch) / 86400 ))
  if [ "$age_days" -gt "$THRESHOLD_DAYS" ]; then
    printf '[doc-expiry] EXPIRED %4sd  %s\n' "$age_days" "$path"
    expired=$((expired + 1))
  fi
done < "$TMP"

echo "[doc-expiry] $dated of $total tracked docs carry a date in the basename"

if [ "$expired" -gt 0 ]; then
  cat >&2 <<REMEDY

[doc-expiry] FAIL — $expired dated doc(s) are more than ${THRESHOLD_DAYS} days past their date
             and are not archived.

  Each one owes a decision. Pick one, per doc:
    - ARCHIVE it: verify it has no inbound reference from outside docs/,
      then 'git mv' it under ${ARCHIVE_PREFIX} preserving its relative
      subpath. Never 'git rm', never a glob, never --force.
    - ALLOWLIST it: if the date is part of a canonical record's identity
      rather than a staleness marker, add the basename to ALLOWLIST in
      this script — and say in the commit why it is canonical.
    - REWRITE it: if it is still the live source of truth for something,
      it should not be carrying a stale date in its name at all.

  Nothing was moved. This check reports; a human decides.
REMEDY
  exit 1
fi

echo "[doc-expiry] PASS"
