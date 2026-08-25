#!/usr/bin/env bash
# Snapshot GitHub Issues into the repo (ADR §5.4 / D10 mitigation).
#
# Off-repo ticket state without this export is the §3.3 failure: clone the
# repo later and the evidence is gone. This script is the recurring dump
# `signal_outcomes` never got. It writes one canonical JSON file; git history
# is the archive. The caller (issue-snapshot.yml) commits only if the file
# changed — do not stamp an export timestamp into the payload or every run
# would produce a noisy empty commit.
#
# `stateReason` is in the field set deliberately: for a dump whose purpose is
# "clone this in five years and the evidence is here," WHY an issue closed
# (completed vs not planned) is the fact worth having, and it cannot be
# backfilled from a snapshot that never captured it.
#
# Exit codes: 0 wrote a snapshot · 1 gh/jq failed or hit the cap · 2 gh missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/docs/ops/github-issues-snapshot.json"
LIMIT=1000

# `gh` resolves the target repository from the CURRENT DIRECTORY's git remote,
# not from this script's location. Without this cd, running the script from
# another checkout dumps THAT repo's issues into this repo's snapshot file — a
# silent wrong-evidence write, which is worse than a failure for a file whose
# whole job is being the evidence. Harmless in CI (the runner's cwd is already
# the checkout root); load-bearing for a manual run.
cd "${ROOT}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh is not installed" >&2
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is not installed" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT

gh issue list \
  --state all \
  --limit "${LIMIT}" \
  --json number,title,state,stateReason,labels,body,author,createdAt,updatedAt,closedAt,url \
  | jq 'sort_by(.number) | map(.labels |= sort_by(.name))' \
  > "${tmp}"

count="$(jq 'length' "${tmp}")"
if [ "${count}" -ge "${LIMIT}" ]; then
  echo "issue snapshot hit --limit ${LIMIT}; paginate before this is evidence-complete" >&2
  exit 1
fi

mv "${tmp}" "${OUT}"
trap - EXIT
echo "wrote ${count} issues to ${OUT}"
