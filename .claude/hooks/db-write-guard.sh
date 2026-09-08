#!/usr/bin/env bash
# db-write-guard.sh — PreToolUse guard, always-on (not ARBI_UNATTENDED-gated).
#
# Two absolute exclusions from the default-allow autonomy model (James, 2026-09-08,
# decided against the item-18/PR-235-followup work): destructive DDL and migration
# application. Both are named because they are the two DB-adjacent actions a `git
# revert` cannot undo — an applied migration or an executed DROP/TRUNCATE/write-
# shaped statement against the read-only connection is real state change, sometimes
# against live data. Everything else DB-adjacent (ordinary reads, and — once
# AUTONOMY=STANDING — ordinary non-destructive production writes through existing
# jobs) is out of this hook's scope and falls through to whatever else governs it.
#
# Migration MERGE authority is deliberately NOT touched here: a merged migration
# file sits unapplied until this repository's own application step runs it
# (measured — no `.github/workflows/*.yml` calls `apply_migration`; the Makefile's
# `migrate:` target says migrations are applied "using
# mcp__supabase__apply_migration", by hand). So merging a migration-bearing PR is
# the revert-able half and stays under ordinary merge authority
# (push-guard.sh / pr-draft-guard.sh's AUTONOMY=STANDING gate, unchanged). Applying
# one is the irreversible half — denied here, unconditionally, regardless of
# AUTONOMY or ARBI_UNATTENDED, until an attested application workflow exists to
# take over the role this hook plays for the interactive/agent identity.
#
# The read-only-server keyword check below is RELOCATED, not new: it used to live
# in unattended-guard.sh's `*execute_sql)` case, gated behind
# `ARBI_UNATTENDED=1` — a total no-op in every attended session, which is every
# session run so far (measured, 2026-09-08). It is a paranoia net for the
# supabase-ro connection specifically: that role should reject writes at the
# database level regardless, so a write-shaped query reaching it client-side is
# either a bug or an attempted bypass either way, and it's named as an always-ask
# exclusion, not an unattended-only one. unattended-guard.sh keeps its own,
# separate, unchanged rule — the write-capable DB server gets no access at all when
# unattended, regardless of query content; that rule is not affected by this file.
#
# HONEST LIMITS (same class as the other hooks): the keyword scan is a lexical
# best-effort — comment/block-comment stripping plus a keyword alternation, not a
# parser. A destructive statement built at runtime from string concatenation, or
# hidden behind a function this list doesn't yet name, is not caught. The real
# backstop is the database role's own privilege grants — this hook is a second
# layer, not the boundary.
set -uo pipefail

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  fi
  exit 0
}

# jq is required to classify safely; no guard => no DB tool call proceeds unclassified.
command -v jq >/dev/null 2>&1 \
  || deny "db-write-guard: jq unavailable; cannot verify the DB call is safe, so it is refused (fail-closed)."

payload="$(cat)"
tool="$(printf '%s' "$payload" | jq -r '.tool_name // empty')"
[ -n "$tool" ] || exit 0

case "$tool" in
  *apply_migration)
    deny "db-write-guard: migration application is reserved to James, unconditionally. Merging a migration-bearing PR is fine — it stays unapplied on merge. Applying one is not this identity's action."
    ;;
  *execute_sql)
    case "$tool" in
      *supabase-ro*|*Supabase-ro*)
        q="$(printf '%s' "$payload" | jq -r '.tool_input.query // empty' | sed -E 's/--[^\n]*//g; s#/\*.*\*/##g')"
        if printf '%s' "$q" | grep -Eiq '\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|TRUNCATE|ALTER|DROP|CREATE|GRANT|REVOKE|REFRESH|COPY|CALL|DO|LOCK|SET[[:space:]]+(ROLE|SESSION)|SELECT\b.*\bINTO\b)\b|\b(approve_object|reject_object|set_active_profile|nextval|setval)\b'; then
          deny "db-write-guard: a write/DDL-shaped query against the read-only DB connection is blocked, always — the connection should reject it regardless, this is the client-side net."
        fi
        ;;
    esac
    ;;
esac
exit 0
