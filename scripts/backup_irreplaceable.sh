#!/usr/bin/env bash
#
# asxos daily backup of irreplaceable tables (Part 3.6 + M12).
#
# Dumps four tables that cannot be re-derived from EODHD or the model
# artefacts, gzips the result, and commits it to the private GitHub repo
# named in $BACKUP_REPO.
#
# Tables backed up:
#   - holding_lots     (lot-level positions; CGT history)
#   - decisions        (journal)
#   - screening_rules  (M-future screening rules)
#   - model_versions   (active model registry; pickle artefacts ride in /models/)
#   - profiles         (M13 investment profile — hand-edited, irreplaceable)
#
# Tables NOT backed up (re-derivable from EODHD + the model pickles + inputs):
#   - prices, fundamentals, signals, universe, regulatory_events, job_runs
#   - rebalance_runs, target_allocations, proposed_trades (re-derivable from profile + inputs)
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
pg_dump \
  --no-owner --no-privileges --no-acl \
  --data-only \
  --column-inserts \
  --table=holding_lots \
  --table=decisions \
  --table=screening_rules \
  --table=model_versions \
  --table=profiles \
  "$DATABASE_URL" > "$DUMP"

gzip -9 "$DUMP"
DUMP_GZ="${DUMP}.gz"
BYTES="$(stat -f%z "$DUMP_GZ" 2>/dev/null || stat -c%s "$DUMP_GZ")"
echo "[backup] dump complete: ${DUMP_GZ} (${BYTES} bytes)"

echo "[backup] cloning ${BACKUP_REPO} (depth=1)"
git -C "$WORK" clone --depth=1 \
  "https://x-access-token:${BACKUP_GITHUB_TOKEN}@github.com/${BACKUP_REPO}.git" repo

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
