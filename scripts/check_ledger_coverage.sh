#!/usr/bin/env bash
#
# check_ledger_coverage.sh — flag merged claude/** PRs that have no ledger row.
#
# WHY THIS EXISTS (lesson L26, promoted 2026-08-14):
#   Nothing but the closing ritual produces a row in arbi-run-ledger.md. So any
#   campaign structure that merges work without running /arbi-close per unit
#   breaks the audit trail *by construction* — and stacked-successor branches
#   (Amendment A) make it MORE likely, not less, because successors proceed
#   before predecessors merge.
#
#   This has now been rediscovered manually twice:
#     1. 2026-08-11 close — both books ran dry after 2026-07-24; the whole
#        August arc went unrecorded for five sessions before anyone noticed.
#     2. 2026-08-14 promotion — the ledger's stated invariant ("Every arbi run
#        leaves a row here") was false again, with 9+ merged missions owed rows.
#   L26 predicted a third manual rediscovery if no check was built. This is the
#   check. It is deliberately mechanical: a human noticing is not a control.
#
#   Why it matters beyond tidiness: autonomy precondition (3) IS a scorecard
#   track record, and the promotion gate trends `episode_score` over these rows.
#   A holed ledger does not merely lose history — it blocks the promotion path.
#   The 2026-08-14 promotion batch was graded with holdout evals and score trend
#   recorded as NOT RUN for exactly this reason.
#
# WHAT IT DOES NOT DO — and must never do:
#   It never writes a ledger row. Per lesson L18 clause (2), a fabricated or
#   backfilled record is a WORSE defect than an absent one, because it corrupts
#   the series the promotion gate trends over rather than leaving a visible
#   hole. SB0-01 refused to invent an `episode_score` for an unobserved run;
#   that refusal is the standard. This script reports; a human closes.
#
# USAGE
#   scripts/check_ledger_coverage.sh [SINCE_ISO8601]
#     SINCE defaults to the last 30 days.
#   Exit 0 = every merged claude/** PR in the window is cited in the ledger.
#   Exit 1 = one or more are not (the list is printed).
#
# REQUIRES: gh (authenticated), git. Read-only: no writes, no network mutation.

set -euo pipefail

LEDGER="docs/product/arbi-run-ledger.md"
SINCE="${1:-$(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)}"

command -v gh >/dev/null 2>&1 || { echo "[coverage] gh not found — cannot enumerate merged PRs" >&2; exit 2; }
[ -f "$LEDGER" ] || { echo "[coverage] $LEDGER not found — run from the repo root" >&2; exit 2; }

echo "[coverage] window: merged since $SINCE"
echo "[coverage] ledger: $LEDGER"

# Merged PRs whose head branch is a claude/** working branch. Non-claude
# branches (agent/**, hand-authored) are out of scope: the ledger's invariant is
# about arbi runs, not about every commit that ever reached main.
# macOS ships bash 3.2 (no `mapfile`), so this stays a POSIX-shaped read loop
# rather than an array builtin — the script must run on the governor's laptop,
# not only in CI.
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

gh pr list --state merged --limit 100 \
  --json number,mergedAt,headRefName,title \
  --jq ".[] | select(.mergedAt >= \"$SINCE\") | select(.headRefName | startswith(\"claude/\")) | \"\(.number)\t\(.mergedAt[0:10])\t\(.headRefName)\t\(.title)\"" > "$TMP"

total=0
missing=0
while IFS=$'\t' read -r num merged_at head title; do
  [ -n "$num" ] || continue
  total=$((total + 1))
  # A PR is "covered" if the ledger cites it as (#N) or #N anywhere.
  # Deliberately loose: a grouped retrospective row covering several units is
  # legitimate (the close-2026-08-11 precedent) so long as it names each PR.
  if ! grep -qE "\(#${num}\)|#${num}\b" "$LEDGER"; then
    printf '[coverage] MISSING ledger row: #%s\t%s\t%s\t%s\n' "$num" "$merged_at" "$head" "$title"
    missing=$((missing + 1))
  fi
done < "$TMP"

if [ "$total" -eq 0 ]; then
  echo "[coverage] no merged claude/** PRs in window — nothing to check"
  exit 0
fi

covered=$((total - missing))
echo "[coverage] $covered/$total merged claude/** PRs cited in the ledger"

if [ "$missing" -gt 0 ]; then
  cat >&2 <<'REMEDY'

[coverage] FAIL — merged work is missing from the audit trail.

  Fix it FORWARD, never by backfilling invented rows (L18 clause 2):
    - Run /arbi-close for the unit(s) and write what is actually observable
      from artifacts: PR number, CI result, the runtime/user outcome observed.
    - If a session's episode_score was never computed and cannot be observed
      now, record it as NOT SCORED with the reason. Do not estimate it.
      An honest hole is auditable; an invented score corrupts the trend the
      promotion gate reads.
REMEDY
  exit 1
fi

echo "[coverage] PASS"
