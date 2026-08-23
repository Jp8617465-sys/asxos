# Session handoff — 2026-08-23 (design-bundle placement)

**Status:** current
**Scope:** what landed this session, and what is owed to James
**Read priority:** read first
**Superseded by:** N/A
**Branch:** `claude/file-placement-review-0y5u8b` — **not merged**

---

## STOP — read first

**Rule #11 (Model A quarantine) stands, unchanged.** Resolved 2026-07-11 *against* Model A:
`corr(ml_prob, 21d) = −0.03` on 19,032 matured signals; STRONG_BUY 21d −0.09% vs HOLD +5.07%.
Nothing this session touched it, and the ADR placed below **enforces it further** — D9 records
it as ratified, and `decision_engine/types.py` makes a non-model-independent `DecisionPacket`
unconstructable (`_MODEL_A_RE` in the manifest validator). Do not read `signals` as current.

**Nothing in the placed ADR has been acted on *by this branch*.** D1–D14 are ratified decisions;
Slices 1–5 are unstarted.

**Slice 0 merged mid-session as #163** (`b352eef`), after this branch's records were first
written and while the PR was open — merged into this branch, and the affected claims corrected
below. That satisfies two things the bundle called prerequisites: *"Slice 0 must merge before
Slice 1 starts"* is now **met**, and the audit v2 this branch archived is now correctly archived
rather than prematurely (its README said "active input until Slice 0 merges, then move to
`docs/archive/`").

---

## What shipped

Three commits, **docs and issue forms only — zero lines of application code**. `full-check` and
`targeted-ml-tests` green on every head.

| Commit | Contents |
|---|---|
| `d966e90` | The 23 Aug design bundle: the ADR at `docs/product/architecture-decision-record.md`, two audits into `docs/archive/`, the ticketing research into `docs/research-archive/` |
| `411179e` | Four D11 issue forms under `.github/ISSUE_TEMPLATE/` — pushed via the GitHub API, not the working tree |
| `1e319c8` | One row in `docs/README.md` mapping the ADR — same API route |

Every placed file was byte-compared against its source. The three unmodified docs and all four
YAMLs are MD5-identical to the bundle; the ADR differs only by the two rows named below; the
pushed `docs/README.md` is MD5-identical to a locally-built expected copy (`2b66d175…`).

**Two deviations from the bundle's own README, both authorised by James in-session:** the audit
v2 was committed now rather than left as a chat artifact (its README said "move to
`docs/archive/` after Slice 0 merges" but never placed it in the repo to be moved), and the
work-management research went to `docs/research-archive/`, the destination that README names.

**Not placed, deliberately:** `claude-code-audit-prompt.md` (Slice 0 is in flight; verbatim at
ADR §10.1), the bundle README itself, and everything in the second zip — its four YAMLs are
MD5-identical to the bundle's and its ADR is the **older** copy, missing the §0 correction and
the Slice 1 `EvidencePacket` prerequisite.

---

## What the ADR got wrong about this repo

The bundle asked for contradictions to be found and a fifth corrections-log row added rather
than worked around. Done — §4 row 5 and a §9 change-log row are the only edits to the file.

1. **"`docs/product/` sits in `AUTHORITY_FRAGMENTS`" is false.** `authority-guard.sh:60-76`
   enumerates individual `docs/product/*.md` files plus `docs/product/rubrics/`; there is no
   directory prefix, and the `.claude/settings.json` deny array mirrors that same file list.
   **The ADR is unguarded as committed** — arbi can edit it directly — and it is not in
   CODEOWNERS. The governor-owned property it claims for itself does not exist until James
   adds the path to both lists. *This is the one worth acting on.*
2. **§0 says "Issue templates ×3"; there are four.** `config.yml` is load-bearing
   (`blank_issues_enabled: false`). §10.3 preserves only an abbreviated markdown sketch, not
   the issue-form YAML, so the ADR alone would not have preserved D11's enforcement. §10.3 also
   says `approval_tier` is required on all three, but the shipped forms pin data-infra and
   research to L3 by label and only `product.yml` carries the selector — that matches §5.5;
   §10.3's text is the stale half.
3. **Two competing architecture authorities.** `product/target-architecture.md` declares itself
   CANONICAL (ratified 2026-08-10, PR #79); the ADR's §2 and §6 overlap it, and
   `arbi-authority.md`'s source-of-truth ladder does not know the ADR exists.
4. **D10 vs this repo's queue.** The ADR calls `roadmap-state.md` frozen; `docs/README.md`,
   `roadmap-state.md:4` and `CLAUDE.md` all still call it the single live queue. The map row
   added this session **states the conflict rather than resolving it** — demoting the live
   queue is the governor's call.
5. **Two ADR versions shipped in one upload set.** Suggest §0 name a digest, not a filename.

**Verified correct, so do not re-litigate:** `types.py` 31,409 bytes · **zero INSERT/UPDATE to
`signal_outcomes`** anywhere in `asxos/`, `jobs/`, `scripts/` · D7 executed exactly as §10.2
specifies · `0042` absent, `0025`/`0045` present-unapplied.

⚠️ **Three figures I verified early in this session were overtaken by #163 landing, and the ADR
§3.5 text they came from is now stale.** Re-measured after merging `main`:

| ADR §3.5 / my earlier claim | Now |
|---|---|
| 43 migration files | **45** (`0018` reconstructed, `0046` added) |
| `REQUIRED_MIGRATIONS = 97` at `asxos/api/main.py:14` | **Deleted.** Replaced by `_check_migration_drift()` calling `scripts/check_migration_drift.py` — the name-set diff §10.1 commit 2 specified. The hand-maintained integer is gone |
| `0018` absent from the sequence | **Present** — `migrations/0018_perf_indexes.sql`, reconstructed from live `pg_get_indexdef()` with a provenance header, per §10.1 commit 6 |

**ADR §3.5 should be updated to match** — it still describes the pre-Slice-0 world. That is a
sixth corrections-log row, not written here: §3.5 is a *statement of fact about production* that
Slice 0 deliberately changed, so the correct edit is the governor's call on whether §3.5 gets
rewritten or superseded.

---

## Pending, requiring James

1. **Commit this branch to `main`.** Draft PR opened from
   `claude/file-placement-review-0y5u8b`. A handoff that lives only on a feature branch is a
   process defect (`docs/README.md`).
2. **`gh issue create/list/view/edit` in `permissions.allow`** — D10 does not function without
   them, and the four issue forms are inert until they land. **I could not make this edit.** The
   repo would have allowed it (`.claude/settings.json` is in neither guard list since
   2026-08-22), but the harness's auto-mode classifier refused it, on the same principle ADR
   §10.2 states and for the same reason D7 went through Cursor. I did not route around it via
   the API, because unlike the map row this edit is nothing but self-benefit. The exact diff,
   four lines after `"Bash(gh pr comment:*)"`:
   ```json
         "Bash(gh issue create:*)",
         "Bash(gh issue list:*)",
         "Bash(gh issue view:*)",
         "Bash(gh issue edit:*)",
   ```
   Note `gh` is not installed in the remote container — these take effect in local sessions only.
3. **Decide whether the ADR should actually be guarded** (finding 1). One line in
   `authority-guard.sh`'s array plus one in the settings deny array plus a CODEOWNERS row, or an
   explicit decision that it stays editable.
4. **Rule on D10 vs `roadmap-state.md`** (finding 4). Until then both stand and D10 is
   ratified-but-not-in-force.
5. **D10's required mitigation does not exist.** §5.4 calls a periodic
   `gh issue list --json` export committed to the repo "required, not optional". Without it,
   off-repo issue state reproduces the exact §3.3 failure the ADR documents for
   `signal_outcomes` — evidence the repo cannot reproduce from itself. This is build work.
6. **`EvidencePacket` scoping** — the bundle asked how to scope a minimal first
   `DecisionPacket`. Deliberately **not answered**: it is the Slice 1 contract decision
   (ADR §5.3, delegable to arbi) that the bundle itself warns must not be made mid-build.
   Ask for it and it comes back as a written recommendation, not code.

---

## Boundaries held

No merge, no push to `main`, no migration applied, no DB write, no deploy, no capital action,
no Model A-derived claim. `0042` untouched; `0045` left unapplied. Two `AUTHORITY_FRAGMENTS`
paths (`.github/ISSUE_TEMPLATE/`, `docs/README.md`) were written **via the GitHub API on
James's explicit instruction**, as unmerged draft commits on a feature branch — the drafting
path the constitution permits, not a direct edit. The one change that would have widened arbi's
own capability was refused and left undone.
