#!/usr/bin/env bash
#
# asxos daily backup of irreplaceable tables (Part 3.6 + M12).
#
# Dumps four tables that cannot be re-derived from EODHD or the model
# artefacts, gzips the result, and commits it to the private GitHub repo
# named in $BACKUP_REPO.
#
# Tables backed up:
#   - holding_lots       (lot-level positions; CGT history)
#   - decisions          (journal)
#   - screening_rules    (M-future screening rules)
#   - model_versions     (active model registry; pickle artefacts ride in /models/)
#   - profiles           (M13 investment profile — hand-edited, irreplaceable)
#   - themes             (M-Thesis-1: theme definitions and adjacency — irreplaceable)
#   - theses             (M-Thesis-1: investment thesis text and audit record — irreplaceable)
#   - thesis_revisions   (M-Thesis-1: append-only discipline event log — irreplaceable)
#   - theme_holdings     (M-Thesis-1: symbol-level theme exposure — irreplaceable)
#   - macro_theses       (Phase 2b: agent-originated macro theses — irreplaceable)
#   - agent_runs         (governance audit: every discovery-agent invocation)
#   - agent_evidence     (governance audit: cited evidence, replayable snapshots)
#   - governance_events  (governance audit: every governance_status transition —
#                         the record that makes agent-originated approvals
#                         defensible after the fact; losing it loses the audit)
#   - price_revisions    (0043: post-containment record of every destructive price
#                         replacement/deletion; included once the table exists)
#
# Tables NOT backed up (re-derivable from EODHD + inputs):
#   - prices, fundamentals, universe, regulatory_events, job_runs
#   - portfolio_daily_snapshots (re-derivable from prices + holding_lots)
#   - rebalance_runs, target_allocations, proposed_trades (re-derivable from profile + inputs)
#
# Tables NOT backed up and NOT re-derivable — frozen historical evidence
# (2026-08-16). `signals` used to sit in the re-derivable list above; that
# premise died when P1-02 deleted its writer (`generate_signals`) and the
# outcome-maturation job. Deliberately NOT added to this daily pg_dump set:
# frozen data would re-dump identically forever. Instead both tables were
# captured once, by the one-time archive `signal-evidence-2026-08-16/` in the
# $BACKUP_REPO backup repo (local copy: ~/Projects/asxos-archive/
# signal-evidence-2026-08-16/, with MANIFEST.txt):
#   - signals          64,189 rows,
#     sha256 e61ee6a4d1774194b86ff2072c362315142ed31bb1d66db7a2a21b5f30d57828
#   - signal_outcomes  60,072 rows (nowhere else mentioned in this script),
#     sha256 7aef52345d4d93d50e10428a3233b725d677f26873077b2b00e2623a0b7f3b8f
# Why they matter: signal_outcomes is the matured-signals evidence base that
# resolved the Model A dispute (docs/model-a-decay-analysis-2026-07-11.md) —
# CLAUDE.md rule #11's standing quarantine rests on it. Losing these tables
# would leave the quarantine's evidentiary basis unrecoverable.
#
# Required env vars:
#   - DATABASE_URL                       postgres://...
#   - BACKUP_GITHUB_TOKEN                fine-grained PAT, contents:rw on $BACKUP_REPO
#   - BACKUP_REPO                        owner/repo (e.g. "jamespcino/asxos-backups")
#   - HEALTHCHECK_URL_BACKUP_IRREPLACEABLE  optional ping endpoint
#
# Fail-fast: any non-zero exit aborts before the healthcheck ping.
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_GITHUB_TOKEN:?BACKUP_GITHUB_TOKEN is required}"
: "${BACKUP_REPO:?BACKUP_REPO is required (owner/repo)}"

DATE="$(date -u +%Y-%m-%d)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

DUMP="$WORK/asxos-${DATE}.sql"

echo "[backup] pg_dump of irreplaceable tables (date=${DATE})"

# This script must be deployable before migration 0043 is applied. Add the new
# ledger as soon as it exists, while keeping the pre-migration backup green.
OPTIONAL_TABLE_ARGS=()
if [ "$(
  psql "$DATABASE_URL" -X -qAt -v ON_ERROR_STOP=1 \
    -c "SELECT to_regclass('public.price_revisions') IS NOT NULL"
)" = "t" ]; then
  OPTIONAL_TABLE_ARGS+=(--table=price_revisions)
  echo "[backup] price_revisions exists — include append-only price history"
else
  echo "[backup] price_revisions absent — pre-0043 backup compatibility mode"
fi

pg_dump \
  --no-owner --no-privileges --no-acl \
  --data-only \
  --column-inserts \
  --table=holding_lots \
  --table=decisions \
  --table=screening_rules \
  --table=model_versions \
  --table=profiles \
  --table=themes \
  --table=theses \
  --table=thesis_revisions \
  --table=theme_holdings \
  --table=macro_theses \
  --table=agent_runs \
  --table=agent_evidence \
  --table=governance_events \
  "${OPTIONAL_TABLE_ARGS[@]}" \
  "$DATABASE_URL" > "$DUMP"

gzip -9 "$DUMP"
DUMP_GZ="${DUMP}.gz"
BYTES="$(stat -f%z "$DUMP_GZ" 2>/dev/null || stat -c%s "$DUMP_GZ")"
echo "[backup] dump complete: ${DUMP_GZ} (${BYTES} bytes)"

echo "[backup] cloning ${BACKUP_REPO} (depth=1)"
# The token must NOT ride in the clone URL: git echoes the remote URL verbatim
# in several fatal messages (repository-not-found being the common one), and
# under `set -e` that stderr lands in the runner log — a contents:rw PAT on the
# repo holding holding_lots and theses, in clear (found in the 2026-08 security
# review). A credential-store file keeps the remote URL clean, lives inside
# $WORK so the existing trap removes it, and never appears in `ps` (unlike
# -c http.extraHeader). --config persists the helper into the cloned repo, so
# the later `git push` authenticates the same way.
CRED="$WORK/.git-credentials"
umask 077
printf 'https://x-access-token:%s@github.com\n' "$BACKUP_GITHUB_TOKEN" > "$CRED"
git -C "$WORK" clone --depth=1 \
  --config credential.helper="store --file=$CRED" \
  "https://github.com/${BACKUP_REPO}.git" repo

# --- Frozen-evidence archive: assert it, don't re-dump it --------------------
#
# `signals` and `signal_outcomes` are deliberately absent from the pg_dump set
# above (see the header): they stopped changing when P1-02 deleted their
# writers, so a daily dump would commit ~124k identical rows into this git repo
# forever. They were captured once instead, with recorded checksums.
#
# Until now nothing verified that capture still existed. The header asserted it
# in prose, the restore drill's 14-table list excludes it, and
# `signal_outcomes` is the matured-signals evidence base that resolved the Model
# A dispute -- CLAUDE.md rule #11's standing quarantine rests on it. An
# unverified single copy of that is a hypothesis, exactly like an unverified
# backup.
#
# Confirmed frozen 2026-08-23: last write to signal_outcomes was 2026-08-02,
# terminal signal_date 2026-07-10, and no INSERT/UPDATE to either table survives
# anywhere in asxos/, jobs/ or scripts/. So these digests are expected to hold
# indefinitely -- if one ever changes, either a writer came back (which needs
# investigating) or the archive was altered (which needs investigating more).
#
# Matched by DIGEST, not filename: the check should survive the archive being
# reorganised, and should fail if the bytes change under an unchanged name.
ARCHIVE_DIR="$WORK/repo/signal-evidence-2026-08-16"
SIGNALS_SHA256="e61ee6a4d1774194b86ff2072c362315142ed31bb1d66db7a2a21b5f30d57828"
SIGNAL_OUTCOMES_SHA256="7aef52345d4d93d50e10428a3233b725d677f26873077b2b00e2623a0b7f3b8f"

if [ ! -d "$ARCHIVE_DIR" ]; then
  echo "[backup] FATAL: frozen-evidence archive ${ARCHIVE_DIR#"$WORK/repo/"} is missing from ${BACKUP_REPO}." >&2
  echo "[backup] signals + signal_outcomes exist in no other backup; rule #11's evidence base is unrecoverable if production is lost." >&2
  exit 1
fi

sha256_of() {
  if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

ARCHIVE_DIGESTS="$(find "$ARCHIVE_DIR" -type f -print0 | while IFS= read -r -d '' f; do sha256_of "$f"; done)"

for pair in "signals:$SIGNALS_SHA256" "signal_outcomes:$SIGNAL_OUTCOMES_SHA256"; do
  table="${pair%%:*}"
  want="${pair##*:}"
  if ! printf '%s\n' "$ARCHIVE_DIGESTS" | grep -qx "$want"; then
    echo "[backup] FATAL: no file in the frozen-evidence archive matches the recorded sha256 for ${table}." >&2
    echo "[backup] expected ${want}. Either the archive was altered, or a writer to ${table} came back and the capture is now stale." >&2
    exit 1
  fi
  echo "[backup] frozen-evidence archive verified: ${table} sha256 matches"
done

cp "$DUMP_GZ" "$WORK/repo/"

cd "$WORK/repo"
git config user.email "backup@asxos.local"
git config user.name  "asxos-backup"
git add "asxos-${DATE}.sql.gz"
if git diff --cached --quiet; then
  echo "[backup] no changes to commit (dump identical to last run)"
else
  git commit -m "backup ${DATE} (${BYTES}b)"
  git push origin HEAD
  echo "[backup] pushed asxos-${DATE}.sql.gz to ${BACKUP_REPO}"
fi

if [ -n "${HEALTHCHECK_URL_BACKUP_IRREPLACEABLE:-}" ]; then
  curl -fsS --retry 3 "$HEALTHCHECK_URL_BACKUP_IRREPLACEABLE" > /dev/null || true
fi

echo "[backup] done"
